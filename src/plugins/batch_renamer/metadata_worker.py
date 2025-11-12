"""Worker thread for metadata extraction with progress reporting."""

import cv2
from pathlib import Path
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from src.core.logger import Logger

logger = Logger.get_logger('BatchRenamer.MetadataWorker')


class MetadataExtractionWorker(QThread):
    """
    Worker thread for extracting metadata from video files.

    Signals:
        progress: Emitted with (current, total, filename) for each file processed
        finished: Emitted with metadata dictionary when complete
        error: Emitted with error message if extraction fails
    """

    progress = pyqtSignal(int, int, str)  # current, total, filename
    finished = pyqtSignal(dict)  # metadata_cache
    error = pyqtSignal(str)  # error_message

    def __init__(self, file_paths: list):
        """
        Initialize metadata extraction worker.

        Args:
            file_paths: List of video file paths to process
        """
        super().__init__()
        self.file_paths = file_paths
        self.metadata_cache = {}
        self._is_running = True

    def run(self):
        """Extract metadata from all files."""
        total = len(self.file_paths)

        logger.info(f"Starting metadata extraction for {total} files")

        for index, file_path in enumerate(self.file_paths):
            if not self._is_running:
                logger.info("Metadata extraction cancelled")
                break

            try:
                filename = Path(file_path).name
                self.progress.emit(index + 1, total, filename)

                metadata = self._extract_metadata(file_path)
                self.metadata_cache[file_path] = metadata

            except Exception as e:
                logger.error(f"Error extracting metadata from {file_path}: {e}")
                self.metadata_cache[file_path] = {}

        self.finished.emit(self.metadata_cache)
        logger.info(f"Metadata extraction completed: {len(self.metadata_cache)} files")

    def stop(self):
        """Stop the worker."""
        self._is_running = False

    def _extract_metadata(self, file_path: str) -> dict:
        """
        Extract metadata from a video file.

        Args:
            file_path: Video file path

        Returns:
            dict: Metadata dictionary
        """
        try:
            cap = cv2.VideoCapture(file_path)
            try:
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
            finally:
                cap.release()

            # File info
            file_stat = Path(file_path).stat()
            mtime = file_stat.st_mtime
            size_mb = file_stat.st_size / (1024 * 1024)

            metadata = {
                'width': width,
                'height': height,
                'resolution': f"{width}x{height}",
                'fps': int(fps),
                'duration': int(duration),
                'size': f"{size_mb:.1f}MB",
                'date': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d'),
                'time': datetime.fromtimestamp(mtime).strftime('%H-%M-%S'),
                'codec': 'unknown',  # Would need FFprobe for accurate codec
            }

            return metadata

        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            return {}


class PatternDetectionWorker(QThread):
    """
    Worker thread for detecting patterns in filenames.

    Signals:
        finished: Emitted with detected patterns when complete
        error: Emitted with error message if detection fails
    """

    finished = pyqtSignal(list)  # List of (pattern, count, position) tuples
    error = pyqtSignal(str)  # error_message

    def __init__(self, pattern_manager, filenames: list, min_frequency: int, min_length: int):
        """
        Initialize pattern detection worker.

        Args:
            pattern_manager: PatternManager instance
            filenames: List of filenames to analyze
            min_frequency: Minimum occurrences
            min_length: Minimum pattern length
        """
        super().__init__()
        self.pattern_manager = pattern_manager
        self.filenames = filenames
        self.min_frequency = min_frequency
        self.min_length = min_length

    def run(self):
        """Detect patterns in filenames."""
        try:
            logger.info(f"Starting pattern detection for {len(self.filenames)} files")

            detected = self.pattern_manager.detect_patterns(
                self.filenames,
                min_frequency=self.min_frequency,
                min_length=self.min_length
            )

            self.finished.emit(detected)
            logger.info(f"Pattern detection completed: {len(detected)} patterns found")

        except Exception as e:
            logger.error(f"Error during pattern detection: {e}")
            self.error.emit(str(e))
