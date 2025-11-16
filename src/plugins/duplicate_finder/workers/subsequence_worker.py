"""
Subsequence detection worker for finding video subsequences.

This module provides a worker thread that performs subsequence detection
in the background to avoid blocking the UI.
"""
from typing import List, Dict, Any, Callable, Optional
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.SubsequenceWorker')


class SubsequenceDetectionWorker(QThread):
    """
    Worker thread for subsequence detection.

    This worker finds video subsequences (short videos contained within longer ones)
    by comparing all pairs where duration difference suggests a potential match.

    Signals:
        progress (int, int, str): Emits (current, total, message) for progress updates.
        finished (list): Emits list of detected subsequences when complete.
        subsequence_found (str, str, dict): Emits (short_video, long_video, result) for each found.
        error (str): Emits error messages.
        status_update (str): Emits status messages.
    """

    # Signal definitions
    progress = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(list)  # List of subsequences
    subsequence_found = pyqtSignal(str, str, dict)  # short_video, long_video, result
    error = pyqtSignal(str)  # Error message
    status_update = pyqtSignal(str)  # Status message

    def __init__(
        self,
        subsequence_detector,
        files: List[str],
        parent=None
    ) -> None:
        """
        Initialize the subsequence detection worker.

        Args:
            subsequence_detector: SubsequenceDetector instance.
            files: List of video file paths to analyze.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self.subsequence_detector = subsequence_detector
        self.files = files
        self._stop = False

    def run(self) -> None:
        """Execute subsequence detection in background thread."""
        try:
            logger.info(f"Starting subsequence detection on {len(self.files)} files")
            self.status_update.emit(f"Analyzing {len(self.files)} videos...")

            # Progress callback for detector
            def progress_callback(current: int, total: int, message: str):
                """Forward progress updates to UI."""
                if self._stop:
                    # Stop detection if requested
                    self.subsequence_detector.cancel()
                    return

                self.progress.emit(current, total, message)

            # Run detection (can be cancelled via progress_callback)
            subsequences = self.subsequence_detector.detect_all_subsequences(
                self.files,
                progress_callback=progress_callback
            )

            # Check if cancelled
            if self._stop:
                logger.info("Subsequence detection cancelled by user")
                self.status_update.emit("Subsequence detection cancelled")
                self.finished.emit([])
                return

            # Emit each found subsequence
            for short_video, long_video, result in subsequences:
                if self._stop:
                    break
                self.subsequence_found.emit(short_video, long_video, result)

            logger.info(f"Subsequence detection complete: {len(subsequences)} found")
            self.status_update.emit(f"✅ {len(subsequences)} subsequence(s) detected")
            self.finished.emit(subsequences)

        except Exception as e:
            logger.error(f"Error during subsequence detection: {e}", exc_info=True)
            self.error.emit(str(e))
            self.finished.emit([])

    def stop(self) -> None:
        """Request the worker to stop."""
        logger.info("Stopping subsequence detection worker...")
        self._stop = True
        # Also signal the detector to cancel
        self.subsequence_detector.cancel()

    def is_stopped(self) -> bool:
        """Check if worker has been stopped."""
        return self._stop
