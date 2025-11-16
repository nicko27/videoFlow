"""
Scene detection worker for finding video scenes using audio fingerprinting.

This module provides a worker thread that performs scene detection
in the background using audio fingerprinting to avoid blocking the UI.
"""
from typing import List, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.SceneWorker')


class SceneDetectionWorker(QThread):
    """
    Worker thread for scene detection using audio fingerprinting.

    This worker finds video scenes (short videos contained within longer ones)
    by analyzing audio fingerprints. Much faster than visual comparison.

    Signals:
        progress (int, int, str): Emits (current, total, message) for progress updates.
        finished (list): Emits list of detected scenes when complete.
        scene_found (str, str, dict): Emits (short_video, long_video, result) for each found.
        error (str): Emits error messages.
        status_update (str): Emits status messages.
    """

    # Signal definitions
    progress = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(list)  # List of scenes
    scene_found = pyqtSignal(str, str, dict)  # short_video, long_video, result
    error = pyqtSignal(str)  # Error message
    status_update = pyqtSignal(str)  # Status message

    def __init__(
        self,
        scene_detector,
        files: List[str],
        parent=None
    ) -> None:
        """
        Initialize the scene detection worker.

        Args:
            scene_detector: AudioFingerprintDetector instance.
            files: List of video file paths to analyze.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self.scene_detector = scene_detector
        self.files = files
        self._stop = False

    def run(self) -> None:
        """Execute scene detection in background thread."""
        try:
            logger.info(f"Starting scene detection on {len(self.files)} files (audio fingerprinting)")
            self.status_update.emit(f"Analyzing {len(self.files)} videos (audio)...")

            # Progress callback for detector
            def progress_callback(current: int, total: int, message: str):
                """Forward progress updates to UI."""
                if self._stop:
                    # Stop detection if requested
                    self.scene_detector.cancel()
                    return

                self.progress.emit(current, total, message)

            # Run detection (can be cancelled via progress_callback)
            scenes = self.scene_detector.detect_all_scenes(
                self.files,
                progress_callback=progress_callback
            )

            # Check if cancelled
            if self._stop:
                logger.info("Scene detection cancelled by user")
                self.status_update.emit("Scene detection cancelled")
                self.finished.emit([])
                return

            # Emit each found scene
            for short_video, long_video, result in scenes:
                if self._stop:
                    break
                self.scene_found.emit(short_video, long_video, result)

            logger.info(f"Scene detection complete: {len(scenes)} found")
            self.status_update.emit(f"✅ {len(scenes)} scene(s) detected")
            self.finished.emit(scenes)

        except Exception as e:
            logger.error(f"Error during scene detection: {e}", exc_info=True)
            self.error.emit(str(e))
            self.finished.emit([])

    def stop(self) -> None:
        """Request the worker to stop."""
        logger.info("Stopping scene detection worker...")
        self._stop = True
        # Also signal the detector to cancel
        self.scene_detector.cancel()

    def is_stopped(self) -> bool:
        """Check if worker has been stopped."""
        return self._stop
