"""Module de conversion vidéo optimisé with correction gestion des échecs."""

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
    """Format optimisé for the size des files."""
    if size < 1024:
        return f"{size} B"
    elif size < 1048576:  # 1024^2
        return f"{size/1024:.1f} KB"
    elif size < 1073741824:  # 1024^3
        return f"{size/1048576:.1f} MB"
    else:
        return f"{size/1073741824:.1f} GB"

def get_video_resolution(video_path: Path) -> Tuple[int, int]:
    """Obtenir la résolution d'une vidéo (largeur, hauteur)."""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0',
            str(video_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            width, height = map(int, result.stdout.strip().split(','))
            return width, height
    except Exception as e:
        logger.warning(f"Impossible d'obtenir la résolution: {e}")

    return 1920, 1080  # Résolution par défaut

def calculate_balanced_crf(video_path: Path, quality_factor: float = 1.0) -> int:
    """
    Calculer un CRF optimal basé sur la résolution de la vidéo.

    Stratégie:
    - 4K (3840x2160+): CRF 18-24 (haute qualité nécessaire)
    - QHD (2560x1440+): CRF 20-26
    - FHD (1920x1080+): CRF 23-28 (standard)
    - HD (1280x720+): CRF 26-30
    - SD (<1280x720): CRF 28-32 (compression plus forte)

    Args:
        video_path: Chemin vers la vidéo
        quality_factor: Facteur de qualité (0.5-2.0, 1.0=neutre)
                       < 1.0 = meilleure qualité (CRF plus bas)
                       > 1.0 = plus de compression (CRF plus haut)

    Returns:
        int: Valeur CRF calculée (18-35)
    """
    width, height = get_video_resolution(video_path)
    pixels = width * height

    # CRF de base selon résolution
    if pixels >= 8294400:  # 4K (3840x2160)
        base_crf = 21
    elif pixels >= 3686400:  # QHD (2560x1440)
        base_crf = 23
    elif pixels >= 2073600:  # FHD (1920x1080)
        base_crf = 25
    elif pixels >= 921600:   # HD (1280x720)
        base_crf = 28
    else:  # SD
        base_crf = 30

    # Ajuster avec le facteur qualité
    # quality_factor < 1.0 => CRF plus bas (meilleure qualité)
    # quality_factor > 1.0 => CRF plus haut (plus de compression)
    adjustment = int((quality_factor - 1.0) * 5)
    final_crf = base_crf + adjustment

    # Limiter entre 18 et 35
    return max(18, min(35, final_crf))

class ConversionWorker(QThread):
    """Worker de conversion vidéo optimisé pour performance et stabilité."""

    progress = pyqtSignal(str, int)  # file_path, progress_percentage
    finished = pyqtSignal(str, bool, str)  # file_path, success, message
    error = pyqtSignal(str, str)  # file_path, error_message
    attempt_changed = pyqtSignal(str, int)  # file_path, attempt_number
    iteration_changed = pyqtSignal(str, int, int)  # file_path, iteration_number, crf_value
    
    def __init__(self, input_file: Path, settings):
        super().__init__()
        self.input_file = input_file
        self.settings = settings
        self.is_running = True
        self.current_attempt = 1
        self.max_attempts = 3 if settings.multiple_attempts else 1
        self.process = None
        self.mutex = QMutex()

        # Compression itérative
        self.current_iteration = 0
        self.current_crf = settings.initial_crf if settings.use_target_size else 28

        # Mode balanced: calculer CRF automatiquement selon résolution
        if getattr(settings, 'balanced_auto_crf', False):
            quality_factor = getattr(settings, 'balanced_quality_factor', 1.0)
            calculated_crf = calculate_balanced_crf(input_file, quality_factor)
            settings.crf = calculated_crf
            logger.info(f"Mode Balanced: CRF auto-calculé = {calculated_crf} (facteur qualité: {quality_factor})")

        # Settings optimisés pour différentes tentatives
        self.attempt_params = [
            {'crf': 28, 'preset': 'fast'},      # Tentative 1: rapide et équilibré
            {'crf': 30, 'preset': 'medium'},    # Tentative 2: compression plus forte
            {'crf': 32, 'preset': 'slow'}       # Tentative 3: compression maximale
        ]
    
    def should_convert(self) -> Tuple[bool, str]:
        """Vérifications rapides avant conversion."""
        if not self.input_file.exists():
            return False, "File inexistant"
        
        if not self.input_file.is_file():
            return False, "Pas un file"
        
        # Checksr suffixe _cvt
        if self.input_file.stem.endswith('_cvt'):
            return False, "Déjà converti (suffixe _cvt)"
        
        # Checksr size si seuil activé
        if self.settings.use_size_threshold:
            try:
                size = self.input_file.stat().st_size
                if size <= self.settings.size_threshold:
                    return False, f"Size déjà sous le seuil ({format_size(size)})"
            except OSError as e:
                return False, f"Error lecture size: {e}"
        
        # Checksr métadonnées si option activée
        if self.settings.ignore_converted:
            try:
                # Import paresseux pour éviter les dépendances au chargement
                from .metadata import MetadataManager
                metadata = MetadataManager.get_metadata(self.input_file)
                if metadata and metadata.compression_ratio > 0:
                    return False, f"Déjà converti (-{metadata.compression_ratio:.1f}%)"
            except Exception as e:
                logger.warning(f"Error vérification métadonnées: {e}")
        
        return True, ""
    
    def get_output_path(self) -> Path:
        """Déterminer le path de sortie in le même folder que l'original."""
        if self.settings.replace_original:
            # File temporaire in le même folder que l'original pour éviter cross-device
            parent_dir = self.input_file.parent
            temp_name = f"temp_conv_{self.input_file.stem}_{datetime.now().strftime('%H%M%S')}{self.input_file.suffix}"
            return parent_dir / temp_name
        else:
            # Add suffixe _cvt in le même folder
            stem = self.input_file.stem
            if not stem.endswith('_cvt'):
                stem += '_cvt'
            return self.input_file.with_name(f"{stem}{self.input_file.suffix}")
    
    def get_duration(self) -> float:
        """Obtenir la duration de the video."""
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
            logger.warning(f"Impossible d'obtenir la duration: {e}")
        
        return 0.0
    
    def get_attempt_params(self, attempt: int, custom_crf: int = None) -> dict:
        """Obtenir les settings pour une tentative donnée."""
        if custom_crf is not None:
            # Mode compression itérative avec CRF personnalisé
            return {
                'crf': custom_crf,
                'preset': self.settings.preset if self.settings.manual_mode else 'medium'
            }
        elif self.settings.manual_mode:
            return {
                'crf': self.settings.crf,
                'preset': self.settings.preset
            }
        else:
            # Utiliser les settings prédéfinis ou ceux of the configuration
            if hasattr(self.settings, 'attempts') and attempt <= len(self.settings.attempts):
                attempt_config = self.settings.attempts[attempt - 1]
                return {
                    'crf': attempt_config.crf,
                    'preset': attempt_config.preset
                }
            elif attempt <= len(self.attempt_params):
                return self.attempt_params[attempt - 1]
            else:
                # Settings de fallback
                return {'crf': 32, 'preset': 'slow'}
    
    def cleanup_temp_files(self, temp_path: Path):
        """Nettoyage sécurisé des files temporaires - seulement si c'est vraiment temporaire."""
        try:
            if temp_path and temp_path.exists():
                # Checksr si c'est vraiment un file temporaire
                # (commence par temp_conv_ ou est in /tmp ou /var/folders)
                is_temp = (
                    temp_path.name.startswith('temp_conv_') or
                    str(temp_path).startswith('/tmp/') or
                    str(temp_path).startswith('/var/folders/') or
                    'videoconv_' in temp_path.name
                )
                
                if is_temp:
                    temp_path.unlink()
                    logger.debug(f"File temporaire nettoyé: {temp_path}")
                else:
                    logger.debug(f"File conservé (pas temporaire): {temp_path}")
        except Exception as e:
            logger.warning(f"Cannot nettoyer {temp_path}: {e}")
    
    def convert_file(self, attempt: int, custom_crf: int = None) -> Tuple[bool, str, Optional[Path]]:
        """Convertir le file with les settings of the tentative."""
        output_path = None

        try:
            with QMutexLocker(self.mutex):
                if not self.is_running:
                    return False, "Conversion arrêtée", None

            # Obtenir les settings (avec CRF personnalisé si mode itératif)
            params = self.get_attempt_params(attempt, custom_crf)
            output_path = self.get_output_path()
            
            # Obtenir la duration pour le suivi du progrès
            duration = self.get_duration()
            if duration <= 0:
                logger.warning("Duration inconnue, suivi du progrès limité")
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
            
            # Start le processus
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Pattern pour extraire le time
            time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
            last_progress = 0
            
            # Lire stderr pour le progrès
            while self.is_running and self.process.poll() is None:
                try:
                    line = self.process.stderr.readline()
                    if not line:
                        break
                    
                    # Chercher le time in la ligne
                    match = time_pattern.search(line)
                    if match and duration > 0:
                        h, m, s, cs = map(int, match.groups())
                        current_time = h * 3600 + m * 60 + s + cs / 100
                        progress = min(int((current_time / duration) * 100), 99)
                        
                        # Émettre seulement si le progrès a changé significativement
                        if progress > last_progress + 2:  # Réduire la fréquence
                            self.progress.emit(str(self.input_file), progress)
                            last_progress = progress
                
                except Exception as e:
                    logger.debug(f"Error lecture progrès: {e}")
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
            
            # Checksr le code de retour
            if return_code != 0:
                stderr_output = ""
                try:
                    stderr_output = self.process.stderr.read()
                except Exception as e:
                    logger.debug(f"Could not read stderr: {e}")
                return False, f"Error ffmpeg (code {return_code}): {stderr_output[:200]}", output_path
            
            # Checksr que le file de sortie existe et n'est pas vide
            if not output_path.exists():
                return False, "File de sortie non créé", output_path
            
            output_size = output_path.stat().st_size
            if output_size == 0:
                return False, "File de sortie vide", output_path
            
            # Comparer les tailles
            original_size = self.input_file.stat().st_size
            
            if output_size >= original_size:
                compression_ratio = ((output_size - original_size) / original_size) * 100
                return False, f"File plus grand (+{compression_ratio:.1f}%)", output_path
            
            # Calculatesr la compression
            compression_ratio = ((original_size - output_size) / original_size) * 100
            
            # Checksr si le seuil de size est respecté
            threshold_met = True
            if self.settings.use_size_threshold:
                threshold_met = output_size <= self.settings.size_threshold
            
            if threshold_met:
                return True, f"Success (-{compression_ratio:.1f}%, {format_size(output_size)})", output_path
            else:
                return False, f"Réduit (-{compression_ratio:.1f}%) mais au-dessus du seuil", output_path
        
        except Exception as e:
            logger.error(f"Error pendant la conversion: {e}")
            return False, str(e), output_path
    
    def convert_with_target_size(self) -> Tuple[bool, str, Optional[Path]]:
        """
        Compression itérative jusqu'à atteindre la taille cible.

        Essaie de compresser le fichier en augmentant progressivement le CRF
        jusqu'à ce que la taille de sortie soit <= target_size.

        Returns:
            Tuple[bool, str, Optional[Path]]: (succès, message, chemin de sortie)
        """
        if not self.settings.use_target_size:
            # Mode normal sans taille cible
            return self.convert_file(self.current_attempt)

        # Vérifier que le fichier d'entrée est assez grand pour nécessiter une compression
        original_size = self.input_file.stat().st_size
        target_size = self.settings.target_size

        if original_size <= target_size:
            return False, f"Fichier déjà sous la taille cible ({format_size(original_size)})", None

        logger.info(f"Mode compression itérative: cible={format_size(target_size)}, original={format_size(original_size)}")

        # Paramètres de compression itérative
        current_crf = self.settings.initial_crf
        crf_step = self.settings.crf_step
        max_crf = self.settings.max_crf
        max_iterations = self.settings.max_compression_attempts

        iteration = 0
        last_output_path = None
        best_output_path = None
        best_size = original_size

        while iteration < max_iterations and self.is_running:
            iteration += 1
            self.current_iteration = iteration

            # Émettre signal de changement d'itération
            self.iteration_changed.emit(str(self.input_file), iteration, current_crf)

            logger.info(f"Itération {iteration}/{max_iterations}: CRF={current_crf}")

            # Nettoyer le fichier de la tentative précédente
            if last_output_path and last_output_path.exists():
                self.cleanup_temp_files(last_output_path)

            # Tenter la conversion avec le CRF actuel
            success, message, output_path = self.convert_file(self.current_attempt, custom_crf=current_crf)

            if not success or not output_path or not output_path.exists():
                logger.warning(f"Itération {iteration} échouée: {message}")

                # Si échec et on a un meilleur résultat précédent, on l'utilise
                if best_output_path and best_output_path.exists():
                    logger.info(f"Utilisation du meilleur résultat précédent ({format_size(best_size)})")
                    if best_size <= target_size:
                        return True, f"Taille cible atteinte après {iteration-1} itérations", best_output_path
                    else:
                        return False, f"Taille cible non atteinte (meilleur: {format_size(best_size)})", best_output_path

                # Augmenter CRF et réessayer
                current_crf += crf_step
                if current_crf > max_crf:
                    return False, f"CRF max atteint ({max_crf}), abandon", None
                continue

            # Vérifier la taille du fichier de sortie
            output_size = output_path.stat().st_size
            compression_ratio = ((original_size - output_size) / original_size) * 100

            logger.info(f"Résultat itération {iteration}: {format_size(output_size)} (-{compression_ratio:.1f}%)")

            # Garder trace du meilleur résultat
            if output_size < best_size:
                if best_output_path and best_output_path != output_path:
                    self.cleanup_temp_files(best_output_path)
                best_output_path = output_path
                best_size = output_size

            # Vérifier si la taille cible est atteinte
            if output_size <= target_size:
                logger.info(f"✓ Taille cible atteinte: {format_size(output_size)} <= {format_size(target_size)}")
                return True, f"Taille cible atteinte après {iteration} itération(s) (-{compression_ratio:.1f}%)", output_path

            # La taille est encore trop grande
            logger.info(f"✗ Taille encore trop grande: {format_size(output_size)} > {format_size(target_size)}")

            # Calculer le prochain CRF
            # Heuristique: si on est loin de la cible, augmenter plus le CRF
            size_ratio = output_size / target_size
            if size_ratio > 1.5:
                # Très loin de la cible, augmenter plus rapidement
                next_crf_step = crf_step * 2
            elif size_ratio > 1.2:
                # Assez loin, augmentation normale
                next_crf_step = crf_step
            else:
                # Proche de la cible, augmentation fine
                next_crf_step = max(1, crf_step // 2)

            current_crf += next_crf_step
            last_output_path = output_path

            # Vérifier si on a dépassé le CRF max
            if current_crf > max_crf:
                logger.warning(f"CRF max atteint ({max_crf}), arrêt des itérations")
                # Garder le meilleur résultat obtenu
                if best_size < original_size:
                    reduction = ((original_size - best_size) / original_size) * 100
                    return False, f"CRF max atteint. Meilleur résultat: {format_size(best_size)} (-{reduction:.1f}%)", best_output_path
                else:
                    return False, f"CRF max atteint sans réduction de taille", None

        # Max itérations atteint
        if iteration >= max_iterations:
            logger.warning(f"Nombre max d'itérations atteint ({max_iterations})")
            if best_output_path and best_size < original_size:
                reduction = ((original_size - best_size) / original_size) * 100
                if best_size <= target_size:
                    return True, f"Taille cible atteinte ({format_size(best_size)})", best_output_path
                else:
                    return False, f"Max itérations atteint. Meilleur: {format_size(best_size)} (-{reduction:.1f}%)", best_output_path

        return False, "Conversion arrêtée", None

    def finalize_conversion(self, output_path: Path, params: dict) -> bool:
        """Finaliser une conversion réussie with gestion d'error robuste."""
        try:
            original_size = self.input_file.stat().st_size
            converted_size = output_path.stat().st_size
            
            # Checksr que le file converti existe et n'est pas vide
            if not output_path.exists() or converted_size == 0:
                logger.error(f"File converti inexistant ou vide: {output_path}")
                return False
            
            # Handling du file original selon les settings
            if self.settings.replace_original:
                # Remplacer l'original with le file temporaire
                try:
                    # Créer une sauvegarde si demandé
                    backup_path = None
                    if not self.settings.delete_if_smaller:
                        backup_path = self.input_file.with_suffix('.bak' + self.input_file.suffix)
                        shutil.copy2(str(self.input_file), str(backup_path))
                        logger.debug(f"Saves créée: {backup_path}")
                    
                    # Remove l'original puis renommer le file converti
                    self.input_file.unlink()
                    output_path.rename(self.input_file)
                    
                    logger.debug(f"Original remplacé: {self.input_file}")
                    
                    # Mettre à jour output_path pour les métadonnées
                    output_path = self.input_file
                    
                except Exception as e:
                    logger.error(f"Error during remplacement de l'original: {e}")
                    # Restaurer la sauvegarde si possible
                    if backup_path and backup_path.exists():
                        try:
                            backup_path.rename(self.input_file)
                            logger.info(f"Saves restaurée: {self.input_file}")
                        except Exception as e:
                            logger.error(f"Failed to restore backup: {e}")
                    return False
            
            else:
                # Garder les deux files, remove l'original si demandé
                should_delete = (
                    self.settings.delete_if_smaller and
                    converted_size < original_size
                )
                
                if should_delete:
                    try:
                        self.input_file.unlink()
                        logger.debug(f"Original supprimé: {self.input_file}")
                    except Exception as e:
                        logger.warning(f"Cannot remove l'original: {e}")
                        # Ce n'est pas une error critique, continuer
            
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
                # Ce n'est pas une error critique, continuer
            
            # Enregistrer les statistics (non critique)
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
                logger.debug(f"Statistics enregistrées pour {output_path}")
            except Exception as e:
                logger.warning(f"Impossible d'enregistrer les statistics: {e}")
                # Ce n'est pas une error critique, continuer
            
            return True
        
        except Exception as e:
            logger.error(f"Error critique lors of the finalisation: {e}")
            return False
    
    def run(self):
        """Exécuter la conversion with gestion des tentatives multiples."""
        output_path = None
        all_attempts_failed = False
        last_error_message = ""

        try:
            # Vérifications préliminaires
            should_convert, reason = self.should_convert()
            if not should_convert:
                self.error.emit(str(self.input_file), reason)
                return

            # Mode compression itérative avec taille cible
            if self.settings.use_target_size:
                logger.info(f"Démarrage compression itérative pour {self.input_file.name}")
                success, message, output_path = self.convert_with_target_size()

                if success and output_path:
                    # Finaliser la conversion réussie
                    params = self.get_attempt_params(self.current_attempt, custom_crf=self.current_crf)
                    if self.finalize_conversion(output_path, params):
                        self.progress.emit(str(self.input_file), 100)
                        self.finished.emit(str(self.input_file), True, message)
                        return
                    else:
                        # La finalisation a failed, nettoyer et signaler l'error
                        if output_path:
                            self.cleanup_temp_files(output_path)
                        self.error.emit(str(self.input_file), "Échec de la finalisation")
                        return
                else:
                    # Échec de la compression itérative
                    if output_path:
                        self.cleanup_temp_files(output_path)
                    self.error.emit(str(self.input_file), message)
                    return

            # Boucle des tentatives (mode normal)
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
                        # La finalisation a failed, nettoyer et signaler l'error
                        if output_path:
                            self.cleanup_temp_files(output_path)
                        self.error.emit(str(self.input_file), "Failed of the finalisation")
                        return
                
                # Tentative échouée - save le message d'error
                last_error_message = message
                
                # Nettoyer le file temporaire de cette tentative échouée
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
            
            # Handling des files non-compressibles si toutes les tentatives ont failed
            if all_attempts_failed and self.is_running:
                settings = self.settings
                if getattr(settings, 'mark_non_compressible', False):
                    self.mark_as_non_compressible()
                
                if self.is_running:
                    # Enregistrer l'failed in les statistics
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
                        logger.warning(f"Impossible d'enregistrer l'failed: {e}")
                    
                    # Utiliser le last message d'error
                    final_message = f"Toutes les tentatives échouées. Dernière error: {last_error_message}"
                    self.error.emit(str(self.input_file), final_message)
                else:
                    self.error.emit(str(self.input_file), "Conversion arrêtée")
        
        except Exception as e:
            logger.error(f"Error critique in le worker: {e}")
            # Nettoyer tout file temporaire remaining
            if output_path:
                self.cleanup_temp_files(output_path)
            self.error.emit(str(self.input_file), f"Error critique: {e}")
        
        finally:
            self.is_running = False
            if self.process:
                try:
                    if self.process.poll() is None:
                        self.process.terminate()
                        self.process.wait(timeout=5)
                except Exception as e:
                    logger.debug(f"Terminate failed, trying kill: {e}")
                    try:
                        if self.process.poll() is None:
                            self.process.kill()
                    except Exception as e:
                        logger.debug(f"Kill also failed: {e}")
    
    def mark_as_non_compressible(self):
        """Marquer un file comme non-compressible en ajoutant un suffixe."""
        try:
            settings = self.settings
            failed_suffix = getattr(settings, 'failed_suffix', '_nocomp')
            
            # Construire le nouveau name with suffixe
            new_stem = self.input_file.stem
            if not new_stem.endswith(failed_suffix):
                new_stem += failed_suffix
            
            new_path = self.input_file.with_name(f"{new_stem}{self.input_file.suffix}")
            
            # Renommer le file
            if not new_path.exists():
                self.input_file.rename(new_path)
                logger.info(f"File marqué comme non-compressible: {new_path.name}")
            
        except Exception as e:
            logger.warning(f"Cannot marquer le file comme non-compressible: {e}")

    def stop(self):
        """Stop la conversion in progress."""
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
                except Exception as e:
                    logger.debug(f"Kill failed: {e}")
            except Exception as e:
                logger.debug(f"Error stopping process: {e}")