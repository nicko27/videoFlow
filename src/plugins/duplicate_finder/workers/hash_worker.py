"""
Hash computation worker for parallel video hash processing.

This module provides a worker thread that computes video hashes in parallel
using a thread pool executor for improved performance.
"""
import os
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QThread, pyqtSignal, QMutex

from src.core.logger import Logger

try:
    from ..validators import ConfigValidator, FileValidator
except ImportError:
    from validators import ConfigValidator, FileValidator

logger = Logger.get_logger('DuplicateFinder.HashWorker')


class ParallelHashWorker(QThread):
    """
    Worker thread for parallel video hash computation.

    This worker processes multiple video files concurrently using a thread pool,
    computing perceptual hashes for each video. It maintains thread safety using
    QMutex and emits signals for progress tracking and UI updates.

    Attributes:
        progress (pyqtSignal): Signal emitting current progress count (int).
        finished (pyqtSignal): Signal emitted when all processing is complete.
        error (pyqtSignal): Signal emitting error messages (str).
        file_processed (pyqtSignal): Signal emitting file path and success status (str, bool).
        current_file (pyqtSignal): Signal emitting current file being processed (str).
        progress_details (pyqtSignal): Signal emitting detailed progress (current, total, filename).

    Example:
        ```python
        worker = ParallelHashWorker(files, video_hasher, max_workers=4, timeout=120)
        worker.progress.connect(update_progress_callback)
        worker.finished.connect(completion_callback)
        worker.start()
        ```
    """

    # Signal definitions with type information
    progress = pyqtSignal(int)  # Current progress count
    finished = pyqtSignal()  # Processing complete
    error = pyqtSignal(str)  # Error message
    file_processed = pyqtSignal(str, bool)  # File path, success status
    current_file = pyqtSignal(str)  # Current file info
    progress_details = pyqtSignal(int, int, str)  # current, total, filename

    def __init__(
        self,
        files: List[str],
        video_hasher,
        max_workers: int,
        timeout: int = 120,
        subsequence_detector = None
    ) -> None:
        """
        Initialize the hash worker.

        Args:
            files: List of video file paths to process.
            video_hasher: VideoHasher instance for computing hashes.
            max_workers: Maximum number of concurrent worker threads.
            timeout: Timeout in seconds for processing each file (default: 120).
            subsequence_detector: Optional SubsequenceDetector for pre-computing dense hashes.
        """
        super().__init__()
        self.files = files
        self.video_hasher = video_hasher
        self.subsequence_detector = subsequence_detector

        # Validate max_workers
        validated_workers = ConfigValidator.validate_workers(max_workers, 'max_workers')
        # Don't exceed number of files to process
        self.max_workers = min(validated_workers, max(1, len(files)))
        logger.info(f"Hash worker using {self.max_workers} workers for {len(files)} files")

        # Log if dense hash pre-computation is enabled
        if self.subsequence_detector:
            logger.info("Dense hash pre-computation ENABLED - will compute during hashing phase")

        # Validate timeout
        self.timeout = ConfigValidator.validate_timeout(timeout, 'hash_timeout')

        self._stop = False
        self._mutex = QMutex()
        self.processed_count = 0

        # Separate files into cached and to-process lists
        self.files_to_process: List[str] = []
        self.files_cached: List[str] = []

        for file in files:
            if self.video_hasher.has_hash(file):
                self.files_cached.append(file)
            else:
                self.files_to_process.append(file)

        logger.info(
            f"Hash Worker initialized: {len(self.files_to_process)} to process, "
            f"{len(self.files_cached)} cached"
        )

    def process_single_file(self, file_path: str) -> Tuple[str, bool]:
        """
        Process a single video file to compute its hash.

        This method checks if the file is already cached, validates its existence
        and size, then computes the video hash. If subsequence detection is enabled,
        also pre-computes dense hash to avoid reprocessing during subsequence phase.

        Args:
            file_path: Path to the video file.

        Returns:
            Tuple of (file_path, success_status).
        """
        if self.is_stopped():
            return file_path, False

        try:
            # Emit current file information
            filename = os.path.basename(file_path)
            self.current_file.emit(f"📄 {filename}")

            # Check if already cached
            if self.video_hasher.has_hash(file_path):
                # Even if normal hash is cached, compute dense hash if needed
                if self.subsequence_detector:
                    try:
                        self.subsequence_detector.compute_dense_hash(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to pre-compute dense hash for {filename}: {e}")
                return file_path, True

            # Validate file using centralized validator
            if not FileValidator.validate_video_file(file_path):
                return file_path, False

            # Compute the normal hash
            self.video_hasher.compute_video_hash(file_path)

            # Also compute dense hash if subsequence detection is enabled
            # This saves time by avoiding reopening the video later
            if self.subsequence_detector:
                try:
                    self.subsequence_detector.compute_dense_hash(file_path)
                    logger.debug(f"Pre-computed dense hash for {filename}")
                except Exception as e:
                    logger.warning(f"Failed to pre-compute dense hash for {filename}: {e}")

            return file_path, True

        except Exception as e:
            logger.error(f"Error processing {os.path.basename(file_path)}: {e}")
            return file_path, False

    def run(self) -> None:
        """
        Execute the parallel hash computation process.

        This method first processes cached files quickly, then processes new files
        in parallel using a thread pool executor. Progress is reported through signals.
        """
        try:
            # Process cached files first (fast path)
            for file_path in self.files_cached:
                if self.is_stopped():
                    break

                filename = os.path.basename(file_path)
                self.current_file.emit(f"💾 {filename} (cache)")
                self.update_progress(file_path, True)

                # Small delay for UI updates
                self.msleep(50)

            # Process new files in parallel
            if self.files_to_process:
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit all tasks
                    future_to_file = {
                        executor.submit(self.process_single_file, file_path): file_path
                        for file_path in self.files_to_process
                    }

                    # Process results as they complete
                    for future in future_to_file:
                        if self.is_stopped():
                            # Cancel remaining tasks
                            for f in future_to_file:
                                f.cancel()
                            break

                        try:
                            file_path, success = future.result(timeout=self.timeout)
                            self.update_progress(file_path, success)
                        except Exception as e:
                            file_path = future_to_file[future]
                            logger.error(f"Error/timeout processing {os.path.basename(file_path)}: {e}")
                            self.update_progress(file_path, False)

            # Emit finished signal if not stopped
            if not self.is_stopped():
                self.finished.emit()

        except Exception as e:
            logger.error(f"Critical error in hash worker: {e}")
            self.error.emit(str(e))

    def stop(self) -> None:
        """
        Signal the worker to stop processing.

        This method is thread-safe and can be called from any thread.
        """
        self._mutex.lock()
        self._stop = True
        self._mutex.unlock()

    def is_stopped(self) -> bool:
        """
        Check if the worker has been stopped.

        Returns:
            True if stop() has been called, False otherwise.
        """
        self._mutex.lock()
        stopped = self._stop
        self._mutex.unlock()
        return stopped

    def update_progress(self, file_path: str, success: bool) -> None:
        """
        Update progress counters and emit progress signals.

        This method is thread-safe and emits multiple signals for UI updates.

        Args:
            file_path: Path of the processed file.
            success: Whether processing was successful.
        """
        # Thread-safe counter update
        self._mutex.lock()
        self.processed_count += 1
        current_count = self.processed_count
        total_count = len(self.files)
        self._mutex.unlock()

        filename = os.path.basename(file_path)

        # Emit all progress signals
        self.file_processed.emit(file_path, success)
        self.progress.emit(current_count)
        self.progress_details.emit(current_count, total_count, filename)
