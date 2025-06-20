
"""
Gestionnaires de contexte pour les ressources VideoFlow
"""

import os
import tempfile
import shutil
import cv2
import threading
import time
from contextlib import contextmanager, ExitStack
from pathlib import Path
from typing import Optional, Generator, Any, Dict, List, Union
from PyQt6.QtCore import QThread, QMutex, QMutexLocker

@contextmanager
def temporary_directory(prefix: str = "videoflow_", cleanup: bool = True):
    """Gestionnaire de contexte pour répertoire temporaire"""
    temp_dir = None
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        yield temp_dir
    finally:
        if temp_dir and cleanup and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.error(f"Erreur suppression répertoire temporaire {temp_dir}: {e}")

@contextmanager
def temporary_file(suffix: str = ".tmp", prefix: str = "videoflow_", 
                  dir: Optional[Path] = None, cleanup: bool = True):
    """Gestionnaire de contexte pour fichier temporaire"""
    temp_file = None
    try:
        fd, temp_file = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
        os.close(fd)  # Fermer le descripteur
        yield Path(temp_file)
    finally:
        if temp_file and cleanup and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception as e:
                logger.error(f"Erreur suppression fichier temporaire {temp_file}: {e}")

@contextmanager
def safe_video_capture(video_path: Union[str, Path], timeout: int = 30):
    """Gestionnaire de contexte sécurisé pour VideoCapture"""
    cap = None
    start_time = time.time()
    
    try:
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            raise VideoFlowError(
                f"Impossible d'ouvrir la vidéo: {video_path}",
                ErrorType.OPENCV,
                ErrorSeverity.HIGH
            )
        
        # Vérifier la validité avec timeout
        ret, frame = cap.read()
        if not ret:
            raise VideoFlowError(
                f"Impossible de lire la première frame: {video_path}",
                ErrorType.OPENCV,
                ErrorSeverity.HIGH
            )
        
        # Remettre au début
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        yield cap
        
    except Exception as e:
        if isinstance(e, VideoFlowError):
            raise
        raise VideoFlowError(
            f"Erreur VideoCapture {video_path}: {e}",
            ErrorType.OPENCV,
            ErrorSeverity.HIGH
        )
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception as e:
                logger.error(f"Erreur libération VideoCapture: {e}")

@contextmanager
def thread_pool_manager(max_workers: int = 4):
    """Gestionnaire de contexte pour pool de threads"""
    from concurrent.futures import ThreadPoolExecutor
    
    executor = None
    try:
        executor = ThreadPoolExecutor(max_workers=max_workers)
        yield executor
    finally:
        if executor:
            try:
                executor.shutdown(wait=True, timeout=30)
            except Exception as e:
                logger.error(f"Erreur arrêt thread pool: {e}")

@contextmanager
def resource_monitor(resource_name: str, max_memory_mb: int = 1000):
    """Monitore l'utilisation des ressources"""
    import psutil
    
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024
    
    try:
        yield
    finally:
        try:
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_diff = final_memory - initial_memory
            
            logger.info(f"Ressource {resource_name}: {memory_diff:+.1f}MB "
                       f"(total: {final_memory:.1f}MB)")
            
            if memory_diff > max_memory_mb:
                logger.warning(f"Fuite mémoire détectée dans {resource_name}: "
                             f"{memory_diff:.1f}MB")
        except Exception as e:
            logger.error(f"Erreur monitoring ressource {resource_name}: {e}")

class ThreadSafeResource:
    """Gestionnaire de ressource thread-safe"""
    
    def __init__(self, resource_factory, cleanup_func=None):
        self._resource_factory = resource_factory
        self._cleanup_func = cleanup_func
        self._resource = None
        self._mutex = QMutex()
        self._ref_count = 0
    
    @contextmanager
    def acquire(self):
        """Acquiert la ressource de manière thread-safe"""
        with QMutexLocker(self._mutex):
            if self._resource is None:
                self._resource = self._resource_factory()
            self._ref_count += 1
        
        try:
            yield self._resource
        finally:
            with QMutexLocker(self._mutex):
                self._ref_count -= 1
                if self._ref_count == 0 and self._cleanup_func:
                    try:
                        self._cleanup_func(self._resource)
                    except Exception as e:
                        logger.error(f"Erreur nettoyage ressource: {e}")
                    finally:
                        self._resource = None

class BatchProcessor:
    """Processeur par lot avec gestion d'erreurs"""
    
    def __init__(self, max_workers: int = 4, timeout: int = 300):
        self.max_workers = max_workers
        self.timeout = timeout
    
    @contextmanager
    def process_batch(self, items: List[Any], process_func: callable):
        """Traite un lot d'éléments avec gestion d'erreurs"""
        from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
        
        results = []
        errors = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Soumettre tous les jobs
            future_to_item = {
                executor.submit(process_func, item): item 
                for item in items
            }
            
            try:
                # Collecter les résultats avec timeout
                for future in as_completed(future_to_item, timeout=self.timeout):
                    item = future_to_item[future]
                    try:
                        result = future.result()
                        results.append((item, result))
                    except Exception as e:
                        errors.append((item, e))
                        logger.error(f"Erreur traitement {item}: {e}")
                
                yield results, errors
                
            except TimeoutError:
                logger.error(f"Timeout lors du traitement par lot ({self.timeout}s)")
                # Annuler les tâches restantes
                for future in future_to_item:
                    future.cancel()
                yield results, errors

@contextmanager
def file_lock(file_path: Union[str, Path], timeout: int = 30):
    """Verrou de fichier cross-platform"""
    import fcntl if os.name != 'nt' else None
    import msvcrt if os.name == 'nt' else None
    
    file_path = Path(file_path)
    lock_file = file_path.with_suffix(file_path.suffix + '.lock')
    
    lock_fd = None
    try:
        # Créer le fichier de verrouillage
        lock_fd = open(lock_file, 'w')
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if os.name != 'nt':
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except (IOError, OSError):
                time.sleep(0.1)
        else:
            raise VideoFlowError(
                f"Impossible d'acquérir le verrou sur {file_path}",
                ErrorType.FILE_IO,
                ErrorSeverity.MEDIUM
            )
        
        yield file_path
        
    finally:
        if lock_fd:
            try:
                if os.name != 'nt':
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                else:
                    msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
                lock_fd.close()
                if lock_file.exists():
                    lock_file.unlink()
            except Exception as e:
                logger.error(f"Erreur libération verrou {file_path}: {e}")

@contextmanager
def progress_tracker(total: int, description: str = "Processing"):
    """Gestionnaire de contexte pour le suivi de progression"""
    
    class ProgressTracker:
        def __init__(self, total: int, description: str):
            self.total = total
            self.current = 0
            self.description = description
            self.start_time = time.time()
        
        def update(self, increment: int = 1):
            self.current += increment
            if self.current % max(1, self.total // 20) == 0:  # Log tous les 5%
                percent = (self.current / self.total) * 100
                elapsed = time.time() - self.start_time
                if self.current > 0:
                    eta = (elapsed / self.current) * (self.total - self.current)
                    logger.info(f"{self.description}: {percent:.1f}% "
                               f"({self.current}/{self.total}) ETA: {eta:.1f}s")
        
        def finish(self):
            elapsed = time.time() - self.start_time
            logger.info(f"{self.description} completed in {elapsed:.1f}s")
    
    tracker = ProgressTracker(total, description)
    try:
        yield tracker
    finally:
        tracker.finish()
