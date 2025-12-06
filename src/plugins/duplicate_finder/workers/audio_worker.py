"""
Worker for parallel audio fingerprint extraction.

Extracts audio fingerprints from multiple videos in parallel using thread pool.
"""
from PyQt6.QtCore import QThread, pyqtSignal
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Callable, Optional
import numpy as np
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.AudioWorker')


class AudioExtractionWorker(QThread):
    """
    Background worker for audio fingerprint extraction.

    Signals:
        progress: (current, total, video_path) - Emitted for each processed video
        finished: (fingerprints_dict) - Emitted when all extraction is complete
        error: (error_message) - Emitted on error
    """

    progress = pyqtSignal(int, int, str)  # current, total, video_path
    finished = pyqtSignal(dict)  # {video_path: fingerprint}
    error = pyqtSignal(str)

    def __init__(
        self,
        video_files: List[str],
        audio_detector,  # AudioFingerprintDetector instance
        num_workers: int = 4,
        precision_mode: str = 'fast',
        database=None  # VideoDatabase instance for caching
    ):
        """
        Initialize audio extraction worker.

        Args:
            video_files: List of video file paths
            audio_detector: AudioFingerprintDetector instance
            num_workers: Number of parallel workers
            precision_mode: Precision mode ('fast', 'balanced', 'maximum')
            database: VideoDatabase instance for caching (optional)
        """
        super().__init__()
        self.video_files = video_files
        self.audio_detector = audio_detector
        self.num_workers = num_workers
        self.precision_mode = precision_mode
        self.database = database
        self._stop_flag = False
        self._cached_count = 0
        self._extracted_count = 0

        logger.info(f"Worker audio initialisé: {len(video_files)} fichiers, "
                   f"{num_workers} workers, mode={precision_mode}, "
                   f"cache={'activé' if database else 'désactivé'}")

    def run(self):
        """Extract audio fingerprints in parallel."""
        try:
            fingerprints = {}
            total = len(self.video_files)
            processed = 0

            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                # Submit all tasks
                future_to_video = {
                    executor.submit(
                        self._extract_fingerprint,
                        video_path
                    ): video_path
                    for video_path in self.video_files
                }

                # Process completed tasks
                for future in as_completed(future_to_video):
                    if self._stop_flag:
                        logger.info("Extraction audio arrêtée par l'utilisateur")
                        executor.shutdown(wait=False, cancel_futures=True)
                        return

                    video_path = future_to_video[future]
                    processed += 1

                    try:
                        result = future.result()
                        if result is not None:
                            fingerprint, is_cached = result
                            fingerprints[video_path] = fingerprint

                            # Show cached status in progress
                            status = "✓ Cached" if is_cached else "✓ Extrait"
                            display_path = f"{video_path} ({status})"
                        else:
                            display_path = video_path
                            logger.warning(f"Aucune empreinte audio pour: {video_path}")

                        # Emit progress with status
                        self.progress.emit(processed, total, display_path)

                    except Exception as e:
                        logger.error(f"Erreur extraction audio de {video_path}: {e}")
                        # Continue with other files

            logger.info(f"Extraction audio terminée: {len(fingerprints)}/{total} fichiers "
                       f"(En cache: {self._cached_count}, Extraits: {self._extracted_count})")
            self.finished.emit(fingerprints)

        except Exception as e:
            error_msg = f"Erreur dans le worker d'extraction audio: {e}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)

    def _extract_fingerprint(self, video_path: str):
        """
        Extract audio fingerprint from a single video with caching.

        Args:
            video_path: Path to video file

        Returns:
            Tuple (fingerprint, is_cached) or None if extraction failed
        """
        try:
            # Check database cache first if available
            if self.database:
                cached_fingerprint = self.database.get_audio_fingerprint(video_path)
                if cached_fingerprint is not None:
                    self._cached_count += 1
                    logger.debug(f"✓ Audio en cache: {video_path}")
                    return (cached_fingerprint, True)  # Cached

            # Cache miss - extract fingerprint
            fingerprint = self.audio_detector.extract_fingerprint(video_path)

            # Save to database if available
            if fingerprint is not None and self.database:
                self.database.store_audio_fingerprint(video_path, fingerprint)
                self._extracted_count += 1
                logger.debug(f"✓ Audio extrait: {video_path}")
            elif fingerprint is not None:
                self._extracted_count += 1

            return (fingerprint, False) if fingerprint is not None else None

        except Exception as e:
            logger.error(f"Échec extraction audio de {video_path}: {e}")
            return None

    def stop(self):
        """Stop the worker."""
        logger.info("Arrêt du worker d'extraction audio...")
        self._stop_flag = True
