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
        algorithm: str = 'hash_index',
        parent=None
    ) -> None:
        """
        Initialize the scene detection worker.

        Args:
            scene_detector: AudioFingerprintDetector or ShazamSceneDetector instance.
            files: List of video file paths to analyze.
            algorithm: Algorithm to use ('hash_index', 'shazam', 'sliding_window').
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self.scene_detector = scene_detector
        self.files = files
        self.algorithm = algorithm
        self._stop = False

    def run(self) -> None:
        """Execute scene detection in background thread using specified algorithm."""
        try:
            logger.info(f"Starting scene detection on {len(self.files)} files using {self.algorithm}")
            self.status_update.emit(f"Analyzing {len(self.files)} videos ({self.algorithm})...")

            # Progress callback for detector
            def progress_callback(current: int, total: int, message: str):
                """Forward progress updates to UI."""
                if self._stop:
                    # Stop detection if requested
                    self.scene_detector.cancel()
                    return

                self.progress.emit(current, total, message)

            # Run detection with the specified algorithm
            if self.algorithm == 'shazam':
                # Shazam detector has its own interface
                scenes = self._detect_with_algorithm(progress_callback)
            else:
                # For hash_index and sliding_window, use modified detect_all_scenes
                scenes = self._detect_with_algorithm(progress_callback)

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

            logger.info(f"Scene detection complete: {len(scenes)} found using {self.algorithm}")
            self.status_update.emit(f"✅ {len(scenes)} scene(s) detected")
            self.finished.emit(scenes)

        except Exception as e:
            logger.error(f"Error during scene detection: {e}", exc_info=True)
            self.error.emit(str(e))
            self.finished.emit([])

    def _detect_with_algorithm(self, progress_callback) -> List:
        """Detect scenes using the specified algorithm.

        Args:
            progress_callback: Progress callback function

        Returns:
            List of (short_video, long_video, result) tuples
        """
        import os
        results = []

        # First, get durations for all videos
        video_durations = {}
        for video_path in self.files:
            if self._stop:
                logger.info("Scene detection cancelled during duration gathering")
                return results

            # Use detector's method to get duration
            if hasattr(self.scene_detector, '_extract_audio_fingerprint'):
                fp, duration, _ = self.scene_detector._extract_audio_fingerprint(video_path)
                if fp:
                    video_durations[video_path] = duration
            elif hasattr(self.scene_detector, 'fingerprinter'):
                # Shazam detector
                hashes = self.scene_detector.fingerprinter.fingerprint_video(video_path)
                if hashes:
                    # Estimate duration from last timestamp
                    video_durations[video_path] = max([t for _, t in hashes]) if hashes else 0

        # Generate pairs where one video is significantly shorter
        pairs = []
        for i, video1 in enumerate(self.files):
            if video1 not in video_durations:
                continue

            for video2 in self.files[i+1:]:
                if video2 not in video_durations:
                    continue

                dur1 = video_durations[video1]
                dur2 = video_durations[video2]

                # One must be at least 20% shorter
                if dur1 > 0 and dur2 > 0:
                    ratio = min(dur1, dur2) / max(dur1, dur2)
                    if ratio < 0.80:  # At least 20% difference
                        if dur1 < dur2:
                            pairs.append((video1, video2))
                        else:
                            pairs.append((video2, video1))

        logger.info(f"Checking {len(pairs)} potential scene pairs")

        # Check each pair using the appropriate algorithm
        total = len(pairs)
        matches_found = 0

        for idx, (short_video, long_video) in enumerate(pairs):
            if self._stop:
                logger.info(f"Scene detection cancelled after {idx} pairs")
                return results

            if progress_callback:
                progress_callback(
                    idx + 1,
                    total,
                    f"Checking {os.path.basename(short_video)} ({matches_found} found)"
                )

            # Call the appropriate detection method based on algorithm
            result = None

            if self.algorithm == 'long_video':
                # Use long video sampling method (optimized for 1h+ videos)
                if hasattr(self.scene_detector, 'find_scene'):
                    result = self.scene_detector.find_scene(short_video, long_video)

            elif self.algorithm == 'hash_index':
                # Use hash index method
                if hasattr(self.scene_detector, 'find_scene_with_index'):
                    result = self.scene_detector.find_scene_with_index(short_video, long_video)
                else:
                    logger.warning("find_scene_with_index not available, falling back to find_scene")
                    result = self.scene_detector.find_scene(short_video, long_video)

            elif self.algorithm == 'sliding_window':
                # Use standard sliding window method
                if hasattr(self.scene_detector, 'find_scene'):
                    result = self.scene_detector.find_scene(short_video, long_video)

            elif self.algorithm == 'shazam':
                # Use Shazam method
                if hasattr(self.scene_detector, 'find_scene'):
                    result = self.scene_detector.find_scene(short_video, long_video)

            if result and result.get('is_scene'):
                results.append((short_video, long_video, result))
                matches_found += 1
                logger.info(
                    f"✓ Scene detected ({self.algorithm}): {os.path.basename(short_video)} in "
                    f"{os.path.basename(long_video)} ({result.get('match_ratio', 0)*100:.1f}% match)"
                )

        return results

    def stop(self) -> None:
        """Request the worker to stop."""
        logger.info("Stopping scene detection worker...")
        self._stop = True
        # Also signal the detector to cancel
        self.scene_detector.cancel()

    def is_stopped(self) -> bool:
        """Check if worker has been stopped."""
        return self._stop
