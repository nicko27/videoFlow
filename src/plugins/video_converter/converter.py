
import threading
from contextlib import contextmanager

class ThreadSafeWorkerManager:
    """Gestionnaire sécurisé pour les workers"""
    
    def __init__(self):
        self._workers = {}
        self._lock = threading.RLock()
    
    @contextmanager
    def get_worker(self, worker_id, worker_class, *args, **kwargs):
        """Gestionnaire de contexte pour les workers"""
        worker = None
        try:
            with self._lock:
                worker = worker_class(*args, **kwargs)
                self._workers[worker_id] = worker
            yield worker
        finally:
            if worker:
                try:
                    if hasattr(worker, 'stop'):
                        worker.stop()
                    if hasattr(worker, 'wait'):
                        worker.wait(5000)  # Timeout de 5 secondes
                    if hasattr(worker, 'deleteLater'):
                        worker.deleteLater()
                except Exception as e:
                    logger.error(f"Erreur nettoyage worker {worker_id}: {e}")
                finally:
                    with self._lock:
                        self._workers.pop(worker_id, None)
    
    def cleanup_all(self):
        """Nettoie tous les workers"""
        with self._lock:
            for worker_id, worker in self._workers.items():
                try:
                    if hasattr(worker, 'stop'):
                        worker.stop()
                    if hasattr(worker, 'wait'):
                        worker.wait(1000)
                except Exception as e:
                    logger.error(f"Erreur nettoyage worker {worker_id}: {e}")
            self._workers.clear()

# Instance globale du gestionnaire
worker_manager = ThreadSafeWorkerManager()

"""Gestion de la conversion vidéo."""

from PyQt6.QtCore import QThread, pyqtSignal
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime
from .metadata import MetadataManager, ConversionMetadata
from .settings import ConversionSettings
from .stats import ConversionStats, StatsManager
from src.core.logger import Logger
import re
import threading
import tempfile
import shutil

logger = Logger.get_logger('VideoConverter.Converter')

def format_size(size: int) -> str:
    """Formate une taille en bytes en format lisible."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

class ConversionWorker(QThread):
    """Thread de conversion vidéo."""
    progress = pyqtSignal(str, int)  # file_path, progress
    finished = pyqtSignal(str)  # file_path
    error = pyqtSignal(str, str)  # file_path, error_message
    attempt_changed = pyqtSignal(str, int)  # file_path, attempt_number
    
    def __init__(self, input_file: Path, settings: ConversionSettings):
        super().__init__()
        self.input_file = input_file
        self.settings = settings
        self.is_running = True
        self.current_attempt = 1
        self.current_params = None
        
    def should_convert(self) -> Tuple[bool, str]:
        """Vérifie si le fichier doit être converti."""
        if not self.input_file.exists():
            return False, "Le fichier n'existe pas"
        
        if not self.input_file.is_file():
            return False, "Ce n'est pas un fichier"
        
        # Vérifier si le fichier est déjà converti
        if self.settings.ignore_converted:
            metadata = MetadataManager.get_metadata(self.input_file)
            if metadata is not None and metadata.compression_ratio > 0:
                return False, f"Déjà converti (-{metadata.compression_ratio:.1f}%)"
        
        # Vérifier la taille du fichier
        if self.settings.use_size_threshold:
            size = self.input_file.stat().st_size
            if size <= self.settings.size_threshold:
                return False, f"Taille déjà inférieure au seuil ({format_size(size)})"
        
        return True, ""
    
    def get_output_path(self, attempt: int) -> Path:
        """Retourne le chemin du fichier de sortie."""
        if self.settings.replace_original:
            # Créer un fichier temporaire pour la conversion
            temp_dir = Path(tempfile.gettempdir())
            return temp_dir / f"{self.input_file.stem}_temp_{attempt}{self.input_file.suffix}"
        else:
            return self.input_file.with_name(f"{self.input_file.stem}_conv{self.input_file.suffix}")
            
    def get_duration(self) -> float:
        """Obtient la durée de la vidéo en secondes."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(self.input_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Erreur lors de la lecture de la durée : {e}")
        
        return 0.0
        
    def get_attempt_params(self, attempt: int) -> dict:
        """Retourne les paramètres pour une tentative donnée."""
        if self.settings.manual_mode:
            return {
                'codec': 'libx264',
                'crf': self.settings.crf,
                'preset': self.settings.preset
            }
        else:
            # Utiliser les paramètres de la tentative configurée
            attempt_params = self.settings.attempts[attempt - 1]
            return {
                'codec': 'libx264',
                'crf': attempt_params.crf,
                'preset': attempt_params.preset
            }
            
    def convert_file(self, attempt: int) -> None:
        """Convertit le fichier avec les paramètres donnés."""
        try:
            # Obtenir les paramètres pour cette tentative
            params = self.get_attempt_params(attempt)
            output_path = self.get_output_path(attempt)
            
            # Obtenir la durée avant de commencer
            duration = self.get_duration()
            if duration <= 0:
                raise Exception("Impossible de lire la durée de la vidéo")
            
            # Réinitialiser la progression
            self.progress.emit(str(self.input_file), 0)
            
            # Préparer la commande ffmpeg
            cmd = [
                'ffmpeg',
                '-i', str(self.input_file),
                '-c:v', params['codec'],
                '-crf', str(params['crf']),
                '-preset', params['preset'],
                '-y',  # Écraser le fichier de sortie si existant
                str(output_path)
            ]
            
            # Lancer la conversion
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Pattern pour extraire le temps
            time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.\d{2}")
            
            # Lire stderr en continu pour la progression
            while self.is_running:
                line = process.stderr.readline()
                if not line:
                    break
                
                # Chercher le temps dans la ligne
                match = time_pattern.search(line)
                if match:
                    h, m, s = map(int, match.groups())
                    current_time = h * 3600 + m * 60 + s
                    progress = min(int((current_time / duration) * 100), 100)
                    self.progress.emit(str(self.input_file), progress)
            
            # Attendre la fin du processus
            process.wait()
            
            # Vérifier si la conversion a réussi
            if process.returncode != 0:
                error_output = process.stderr.read()
                raise Exception(f"Erreur ffmpeg : {error_output}")
            
            # Vérifier la taille du fichier
            if output_path.exists():
                original_size = self.input_file.stat().st_size
                converted_size = output_path.stat().st_size
                
                # Calculer le ratio de compression
                ratio = ((original_size - converted_size) / original_size) * 100
                
                # Vérifier si on a atteint l'objectif de taille
                threshold_ok = True
                if self.settings.use_size_threshold:
                    threshold_ok = converted_size <= self.settings.size_threshold
                
                if converted_size < original_size and (threshold_ok or not self.settings.multiple_attempts or self.current_attempt >= 3):
                    # Mettre à jour les métadonnées
                    MetadataManager.mark_as_converted(
                        self.input_file,
                        output_path,
                        self.get_attempt_params(self.current_attempt)
                    )
                    
                    # Gérer le remplacement/suppression du fichier original
                    if self.settings.replace_original:
                        self.input_file.unlink()
                        shutil.move(str(output_path), str(self.input_file))
                        logger.debug(f"Fichier original remplacé : {self.input_file}")
                    else:
                        should_delete = (self.settings.delete_if_smaller and 
                                      (threshold_ok or self.settings.delete_if_threshold))
                        if should_delete:
                            self.input_file.unlink()
                            logger.debug(f"Fichier original supprimé : {self.input_file}")
                    
                    success_msg = "Succès (-{:.1f}%)".format(ratio)
                    if not threshold_ok:
                        success_msg = f"Réduit (-{ratio:.1f}%) mais > seuil"
                    
                    self.finished.emit(str(self.input_file))
                    logger.info(f"Conversion terminée pour {self.input_file}: {success_msg}")
                else:
                    # Fichier plus grand ou seuil non atteint
                    output_path.unlink()
                    if self.settings.multiple_attempts and self.current_attempt < 3:
                        logger.info(f"Tentative {self.current_attempt} : fichier plus grand ou seuil non atteint, passage à la tentative suivante")
                        self.current_attempt += 1
                        self.attempt_changed.emit(str(self.input_file), self.current_attempt)
                        self.convert_file(self.current_attempt)
                    else:
                        if converted_size >= original_size:
                            self.error.emit(str(self.input_file), f"Échec: taille finale +{-ratio:.1f}%")
                        else:
                            self.error.emit(str(self.input_file), f"Échec: taille finale (-{ratio:.1f}%) > seuil")
            
        except Exception as e:
            logger.error(f"Erreur lors de la conversion : {e}")
            if self.settings.multiple_attempts and self.current_attempt < 3:
                self.current_attempt += 1
                self.attempt_changed.emit(str(self.input_file), self.current_attempt)
                self.convert_file(self.current_attempt)
            else:
                self.error.emit(str(self.input_file), str(e))
            
    def conversion_finished(self):
        """Appelé quand la conversion est terminée."""
        try:
            output_path = self.get_output_path(self.current_attempt)
            if output_path.exists():
                # Vérifier la taille du fichier converti
                original_size = self.input_file.stat().st_size
                converted_size = output_path.stat().st_size
                
                # Calculer le ratio de compression
                ratio = (original_size - converted_size) / original_size * 100
                
                # Vérifier si on a atteint l'objectif de taille
                threshold_ok = True
                if self.settings.use_size_threshold:
                    threshold_ok = converted_size <= self.settings.size_threshold
                
                if converted_size < original_size and (threshold_ok or self.current_attempt >= 3):
                    # Mettre à jour les métadonnées
                    MetadataManager.mark_as_converted(
                        self.input_file,
                        output_path,
                        self.get_attempt_params(self.current_attempt)
                    )
                    
                    # Gérer le remplacement/suppression du fichier original
                    if self.settings.replace_original:
                        self.input_file.unlink()
                        shutil.move(str(output_path), str(self.input_file))
                        logger.debug(f"Fichier original remplacé : {self.input_file}")
                    else:
                        should_delete = (self.settings.delete_if_smaller and 
                                      (threshold_ok or self.settings.delete_if_threshold))
                        if should_delete:
                            self.input_file.unlink()
                            logger.debug(f"Fichier original supprimé : {self.input_file}")
                    
                    success_msg = "Succès (-{:.1f}%)".format(ratio)
                    if not threshold_ok:
                        success_msg = f"Réduit (-{ratio:.1f}%) mais > seuil"
                    
                    self.finished.emit(str(self.input_file))
                    logger.info(f"Conversion terminée pour {self.input_file}: {success_msg}")
                else:
                    # Fichier plus grand ou seuil non atteint
                    output_path.unlink()
                    if self.current_attempt < 3:
                        logger.info(f"Tentative {self.current_attempt} : fichier plus grand ou seuil non atteint, passage à la tentative suivante")
                        self.current_attempt += 1
                        self.attempt_changed.emit(str(self.input_file), self.current_attempt)
                        self.convert_file(self.current_attempt)
                    else:
                        if converted_size >= original_size:
                            self.error.emit(str(self.input_file), f"Échec: taille finale +{-ratio:.1f}%")
                        else:
                            self.error.emit(str(self.input_file), f"Échec: taille finale (-{ratio:.1f}%) > seuil")
            else:
                raise FileNotFoundError("Le fichier de sortie n'existe pas")
                
        except Exception as e:
            logger.error(f"Erreur lors de la finalisation de la conversion : {e}")
            self.error.emit(str(self.input_file), str(e))
            
    def run(self):
        """Exécute la conversion."""
        try:
            # Vérifier si le fichier doit être converti
            should_convert, reason = self.should_convert()
            if not should_convert:
                self.error.emit(str(self.input_file), reason)
                return
            
            # Obtenir la durée de la vidéo
            duration = self.get_duration()
            if duration <= 0:
                self.error.emit(str(self.input_file), "Impossible de lire la durée de la vidéo")
                return
            
            # Démarrer la première tentative
            self.convert_file(self.current_attempt)
            
        except Exception as e:
            logger.error(f"Erreur lors de la conversion : {e}")
            self.error.emit(str(self.input_file), str(e))
        finally:
            self.is_running = False

    def stop(self):
        """Arrête la conversion."""
        self.is_running = False
