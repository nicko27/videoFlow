"""Module de conversion vidéo optimisé avec correction gestion des échecs."""

from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
import subprocess
import tempfile
import shutil
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime
from src.core.logger import Logger

logger = Logger.get_logger('VideoConverter.Converter')

def format_size(size: int) -> str:
    """Format optimisé pour la taille des fichiers."""
    if size < 1024:
        return f"{size} B"
    elif size < 1048576:  # 1024^2
        return f"{size/1024:.1f} KB"
    elif size < 1073741824:  # 1024^3
        return f"{size/1048576:.1f} MB"
    else:
        return f"{size/1073741824:.1f} GB"

class ConversionWorker(QThread):
    """Worker de conversion vidéo optimisé pour performance et stabilité."""
    
    progress = pyqtSignal(str, int)  # file_path, progress_percentage
    finished = pyqtSignal(str, bool, str)  # file_path, success, message
    error = pyqtSignal(str, str)  # file_path, error_message
    attempt_changed = pyqtSignal(str, int)  # file_path, attempt_number
    
    def __init__(self, input_file: Path, settings):
        super().__init__()
        self.input_file = input_file
        self.settings = settings
        self.is_running = True
        self.current_attempt = 1
        self.max_attempts = 3 if settings.multiple_attempts else 1
        self.process = None
        self.mutex = QMutex()
        
        # Paramètres optimisés pour différentes tentatives
        self.attempt_params = [
            {'crf': 28, 'preset': 'fast'},      # Tentative 1: rapide et équilibré
            {'crf': 30, 'preset': 'medium'},    # Tentative 2: compression plus forte
            {'crf': 32, 'preset': 'slow'}       # Tentative 3: compression maximale
        ]
    
    def should_convert(self) -> Tuple[bool, str]:
        """Vérifications rapides avant conversion."""
        if not self.input_file.exists():
            return False, "Fichier inexistant"
        
        if not self.input_file.is_file():
            return False, "Pas un fichier"
        
        # Vérifier suffixe _cvt
        if self.input_file.stem.endswith('_cvt'):
            return False, "Déjà converti (suffixe _cvt)"
        
        # Vérifier taille si seuil activé
        if self.settings.use_size_threshold:
            try:
                size = self.input_file.stat().st_size
                if size <= self.settings.size_threshold:
                    return False, f"Taille déjà sous le seuil ({format_size(size)})"
            except OSError as e:
                return False, f"Erreur lecture taille: {e}"
        
        # Vérifier métadonnées si option activée
        if self.settings.ignore_converted:
            try:
                # Import paresseux pour éviter les dépendances au chargement
                from .metadata import MetadataManager
                metadata = MetadataManager.get_metadata(self.input_file)
                if metadata and metadata.compression_ratio > 0:
                    return False, f"Déjà converti (-{metadata.compression_ratio:.1f}%)"
            except Exception as e:
                logger.warning(f"Erreur vérification métadonnées: {e}")
        
        return True, ""
    
    def get_output_path(self) -> Path:
        """Déterminer le chemin de sortie dans le même dossier que l'original."""
        if self.settings.replace_original:
            # Fichier temporaire dans le même dossier que l'original pour éviter cross-device
            parent_dir = self.input_file.parent
            temp_name = f"temp_conv_{self.input_file.stem}_{datetime.now().strftime('%H%M%S')}{self.input_file.suffix}"
            return parent_dir / temp_name
        else:
            # Ajouter suffixe _cvt dans le même dossier
            stem = self.input_file.stem
            if not stem.endswith('_cvt'):
                stem += '_cvt'
            return self.input_file.with_name(f"{stem}{self.input_file.suffix}")
    
    def get_duration(self) -> float:
        """Obtenir la durée de la vidéo."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(self.input_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except (subprocess.TimeoutExpired, ValueError, OSError) as e:
            logger.warning(f"Impossible d'obtenir la durée: {e}")
        
        return 0.0
    
    def get_attempt_params(self, attempt: int) -> dict:
        """Obtenir les paramètres pour une tentative donnée."""
        if self.settings.manual_mode:
            return {
                'crf': self.settings.crf,
                'preset': self.settings.preset
            }
        else:
            # Utiliser les paramètres prédéfinis ou ceux de la configuration
            if hasattr(self.settings, 'attempts') and attempt <= len(self.settings.attempts):
                attempt_config = self.settings.attempts[attempt - 1]
                return {
                    'crf': attempt_config.crf,
                    'preset': attempt_config.preset
                }
            elif attempt <= len(self.attempt_params):
                return self.attempt_params[attempt - 1]
            else:
                # Paramètres de fallback
                return {'crf': 32, 'preset': 'slow'}
    
    def cleanup_temp_files(self, temp_path: Path):
        """Nettoyage sécurisé des fichiers temporaires - seulement si c'est vraiment temporaire."""
        try:
            if temp_path and temp_path.exists():
                # Vérifier si c'est vraiment un fichier temporaire
                # (commence par temp_conv_ ou est dans /tmp ou /var/folders)
                is_temp = (
                    temp_path.name.startswith('temp_conv_') or
                    str(temp_path).startswith('/tmp/') or
                    str(temp_path).startswith('/var/folders/') or
                    'videoconv_' in temp_path.name
                )
                
                if is_temp:
                    temp_path.unlink()
                    logger.debug(f"Fichier temporaire nettoyé: {temp_path}")
                else:
                    logger.debug(f"Fichier conservé (pas temporaire): {temp_path}")
        except Exception as e:
            logger.warning(f"Impossible de nettoyer {temp_path}: {e}")
    
    def convert_file(self, attempt: int) -> Tuple[bool, str, Optional[Path]]:
        """Convertir le fichier avec les paramètres de la tentative."""
        output_path = None
        
        try:
            with QMutexLocker(self.mutex):
                if not self.is_running:
                    return False, "Conversion arrêtée", None
            
            # Obtenir les paramètres
            params = self.get_attempt_params(attempt)
            output_path = self.get_output_path()
            
            # Obtenir la durée pour le suivi du progrès
            duration = self.get_duration()
            if duration <= 0:
                logger.warning("Durée inconnue, suivi du progrès limité")
                duration = 1  # Éviter division par zéro
            
            # Réinitialiser le progrès
            self.progress.emit(str(self.input_file), 0)
            
            # Commande ffmpeg optimisée
            cmd = [
                'ffmpeg',
                '-i', str(self.input_file),
                '-c:v', 'libx264',
                '-crf', str(params['crf']),
                '-preset', params['preset'],
                '-c:a', 'copy',  # Copier audio sans réencodage
                '-avoid_negative_ts', 'make_zero',  # Éviter les timestamps négatifs
                '-movflags', '+faststart',  # Optimisation pour streaming
                '-y',  # Écraser la sortie
                str(output_path)
            ]
            
            logger.info(f"Tentative {attempt} pour {self.input_file.name} (CRF={params['crf']}, preset={params['preset']})")
            logger.debug(f"Commande: {' '.join(cmd)}")
            
            # Démarrer le processus
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Pattern pour extraire le temps
            time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
            last_progress = 0
            
            # Lire stderr pour le progrès
            while self.is_running and self.process.poll() is None:
                try:
                    line = self.process.stderr.readline()
                    if not line:
                        break
                    
                    # Chercher le temps dans la ligne
                    match = time_pattern.search(line)
                    if match:
                        h, m, s, cs = map(int, match.groups())
                        current_time = h * 3600 + m * 60 + s + cs / 100
                        progress = min(int((current_time / duration) * 100), 99)
                        
                        # Émettre seulement si le progrès a changé significativement
                        if progress > last_progress + 2:  # Réduire la fréquence
                            self.progress.emit(str(self.input_file), progress)
                            last_progress = progress
                
                except Exception as e:
                    logger.debug(f"Erreur lecture progrès: {e}")
                    break
            
            # Attendre la fin du processus
            if self.is_running:
                return_code = self.process.wait()
            else:
                # Arrêt demandé
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
                return False, "Conversion arrêtée", output_path
            
            # Vérifier le code de retour
            if return_code != 0:
                stderr_output = ""
                try:
                    stderr_output = self.process.stderr.read()
                except:
                    pass
                return False, f"Erreur ffmpeg (code {return_code}): {stderr_output[:200]}", output_path
            
            # Vérifier que le fichier de sortie existe et n'est pas vide
            if not output_path.exists():
                return False, "Fichier de sortie non créé", output_path
            
            output_size = output_path.stat().st_size
            if output_size == 0:
                return False, "Fichier de sortie vide", output_path
            
            # Comparer les tailles
            original_size = self.input_file.stat().st_size
            
            if output_size >= original_size:
                compression_ratio = ((output_size - original_size) / original_size) * 100
                return False, f"Fichier plus grand (+{compression_ratio:.1f}%)", output_path
            
            # Calculer la compression
            compression_ratio = ((original_size - output_size) / original_size) * 100
            
            # Vérifier si le seuil de taille est respecté
            threshold_met = True
            if self.settings.use_size_threshold:
                threshold_met = output_size <= self.settings.size_threshold
            
            if threshold_met:
                return True, f"Succès (-{compression_ratio:.1f}%, {format_size(output_size)})", output_path
            else:
                return False, f"Réduit (-{compression_ratio:.1f}%) mais au-dessus du seuil", output_path
        
        except Exception as e:
            logger.error(f"Erreur pendant la conversion: {e}")
            return False, str(e), output_path
    
    def finalize_conversion(self, output_path: Path, params: dict) -> bool:
        """Finaliser une conversion réussie avec gestion d'erreur robuste."""
        try:
            original_size = self.input_file.stat().st_size
            converted_size = output_path.stat().st_size
            
            # Vérifier que le fichier converti existe et n'est pas vide
            if not output_path.exists() or converted_size == 0:
                logger.error(f"Fichier converti inexistant ou vide: {output_path}")
                return False
            
            # Gestion du fichier original selon les paramètres
            if self.settings.replace_original:
                # Remplacer l'original avec le fichier temporaire
                try:
                    # Créer une sauvegarde si demandé
                    backup_path = None
                    if not self.settings.delete_if_smaller:
                        backup_path = self.input_file.with_suffix('.bak' + self.input_file.suffix)
                        shutil.copy2(str(self.input_file), str(backup_path))
                        logger.debug(f"Sauvegarde créée: {backup_path}")
                    
                    # Supprimer l'original puis renommer le fichier converti
                    self.input_file.unlink()
                    output_path.rename(self.input_file)
                    
                    logger.debug(f"Original remplacé: {self.input_file}")
                    
                    # Mettre à jour output_path pour les métadonnées
                    output_path = self.input_file
                    
                except Exception as e:
                    logger.error(f"Erreur lors du remplacement de l'original: {e}")
                    # Restaurer la sauvegarde si possible
                    if backup_path and backup_path.exists():
                        try:
                            backup_path.rename(self.input_file)
                            logger.info(f"Sauvegarde restaurée: {self.input_file}")
                        except:
                            pass
                    return False
            
            else:
                # Garder les deux fichiers, supprimer l'original si demandé
                should_delete = (
                    self.settings.delete_if_smaller and
                    converted_size < original_size
                )
                
                if should_delete:
                    try:
                        self.input_file.unlink()
                        logger.debug(f"Original supprimé: {self.input_file}")
                    except Exception as e:
                        logger.warning(f"Impossible de supprimer l'original: {e}")
                        # Ce n'est pas une erreur critique, continuer
            
            # Essayer d'enregistrer les métadonnées (non critique)
            try:
                from .metadata import MetadataManager
                MetadataManager.mark_as_converted(
                    self.input_file,
                    output_path,
                    params
                )
                logger.debug(f"Métadonnées enregistrées pour {output_path}")
            except Exception as e:
                logger.warning(f"Impossible d'enregistrer les métadonnées: {e}")
                # Ce n'est pas une erreur critique, continuer
            
            # Enregistrer les statistiques (non critique)
            try:
                from .stats import StatsManager, ConversionStats
                stats = ConversionStats(
                    input_size=original_size,
                    output_size=converted_size,
                    duration=0.0,
                    attempt_count=self.current_attempt,
                    params_used=params,
                    success=True,
                    input_file=str(self.input_file),
                    output_file=str(output_path)
                )
                StatsManager().add_stat(stats)
                logger.debug(f"Statistiques enregistrées pour {output_path}")
            except Exception as e:
                logger.warning(f"Impossible d'enregistrer les statistiques: {e}")
                # Ce n'est pas une erreur critique, continuer
            
            return True
        
        except Exception as e:
            logger.error(f"Erreur critique lors de la finalisation: {e}")
            return False
    
    def run(self):
        """Exécuter la conversion avec gestion des tentatives multiples."""
        output_path = None
        all_attempts_failed = False
        last_error_message = ""
        
        try:
            # Vérifications préliminaires
            should_convert, reason = self.should_convert()
            if not should_convert:
                self.error.emit(str(self.input_file), reason)
                return
            
            # Boucle des tentatives
            while self.current_attempt <= self.max_attempts and self.is_running:
                self.attempt_changed.emit(str(self.input_file), self.current_attempt)
                
                success, message, output_path = self.convert_file(self.current_attempt)
                
                if success:
                    # Finaliser la conversion réussie
                    params = self.get_attempt_params(self.current_attempt)
                    if self.finalize_conversion(output_path, params):
                        self.progress.emit(str(self.input_file), 100)
                        self.finished.emit(str(self.input_file), True, message)
                        return
                    else:
                        # La finalisation a échoué, nettoyer et signaler l'erreur
                        if output_path:
                            self.cleanup_temp_files(output_path)
                        self.error.emit(str(self.input_file), "Échec de la finalisation")
                        return
                
                # Tentative échouée - sauvegarder le message d'erreur
                last_error_message = message
                
                # Nettoyer le fichier temporaire de cette tentative échouée
                if output_path:
                    self.cleanup_temp_files(output_path)
                    output_path = None
                
                if self.current_attempt < self.max_attempts and self.is_running:
                    logger.info(f"Tentative {self.current_attempt} échouée pour {self.input_file.name}: {message}")
                    self.current_attempt += 1
                else:
                    # Toutes les tentatives échouées
                    all_attempts_failed = True
                    break
            
            # Gestion des fichiers non-compressibles si toutes les tentatives ont échoué
            if all_attempts_failed and self.is_running:
                settings = self.settings
                if getattr(settings, 'mark_non_compressible', False):
                    self.mark_as_non_compressible()
                
                if self.is_running:
                    # Enregistrer l'échec dans les statistiques
                    try:
                        from .stats import StatsManager, ConversionStats
                        original_size = self.input_file.stat().st_size if self.input_file.exists() else 0
                        params = self.get_attempt_params(self.current_attempt)
                        
                        stats = ConversionStats(
                            input_size=original_size,
                            output_size=0,
                            duration=0.0,
                            attempt_count=self.current_attempt,
                            params_used=params,
                            success=False,
                            input_file=str(self.input_file),
                            output_file=""
                        )
                        StatsManager().add_stat(stats)
                    except Exception as e:
                        logger.warning(f"Impossible d'enregistrer l'échec: {e}")
                    
                    # Utiliser le dernier message d'erreur
                    final_message = f"Toutes les tentatives échouées. Dernière erreur: {last_error_message}"
                    self.error.emit(str(self.input_file), final_message)
                else:
                    self.error.emit(str(self.input_file), "Conversion arrêtée")
        
        except Exception as e:
            logger.error(f"Erreur critique dans le worker: {e}")
            # Nettoyer tout fichier temporaire restant
            if output_path:
                self.cleanup_temp_files(output_path)
            self.error.emit(str(self.input_file), f"Erreur critique: {e}")
        
        finally:
            self.is_running = False
            if self.process:
                try:
                    if self.process.poll() is None:
                        self.process.terminate()
                        self.process.wait(timeout=5)
                except:
                    try:
                        if self.process.poll() is None:
                            self.process.kill()
                    except:
                        pass
    
    def mark_as_non_compressible(self):
        """Marquer un fichier comme non-compressible en ajoutant un suffixe."""
        try:
            settings = self.settings
            failed_suffix = getattr(settings, 'failed_suffix', '_nocomp')
            
            # Construire le nouveau nom avec suffixe
            new_stem = self.input_file.stem
            if not new_stem.endswith(failed_suffix):
                new_stem += failed_suffix
            
            new_path = self.input_file.with_name(f"{new_stem}{self.input_file.suffix}")
            
            # Renommer le fichier
            if not new_path.exists():
                self.input_file.rename(new_path)
                logger.info(f"Fichier marqué comme non-compressible: {new_path.name}")
            
        except Exception as e:
            logger.warning(f"Impossible de marquer le fichier comme non-compressible: {e}")

    def stop(self):
        """Arrêter la conversion en cours."""
        with QMutexLocker(self.mutex):
            self.is_running = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    self.process.kill()
                    self.process.wait(timeout=2)
                except:
                    pass
            except:
                pass