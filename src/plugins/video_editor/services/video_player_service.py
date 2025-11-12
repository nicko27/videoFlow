"""Video Player Service - Business logic for video playback.

This service handles all video playback operations, independent of the UI layer.
It manages video capture, frame navigation, and playback control.
"""

import cv2
import numpy as np
from typing import Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.VideoPlayerService')


class VideoPlayerService(QObject):
    """Service for managing video playback operations.

    This service encapsulates all video playback logic, making it
    easier to test and reuse across different UI components.

    Signals:
        frame_changed: Emitted when current frame changes (frame_num, frame_data)
        playback_started: Emitted when playback starts
        playback_stopped: Emitted when playback stops
        video_loaded: Emitted when a video is loaded (fps, total_frames, width, height)
        video_closed: Emitted when video is closed
        error_occurred: Emitted when an error occurs (error_message)
    """

    frame_changed = pyqtSignal(int, np.ndarray)  # frame_num, frame_data
    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    video_loaded = pyqtSignal(float, int, int, int)  # fps, total_frames, width, height
    video_closed = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self):
        """Initialize the video player service."""
        super().__init__()

        self._cap: Optional[cv2.VideoCapture] = None
        self._current_frame: int = 0
        self._total_frames: int = 0
        self._fps: float = 0.0
        self._width: int = 0
        self._height: int = 0
        self._is_playing: bool = False
        self._video_path: Optional[str] = None

        # Playback timer
        self._play_timer = QTimer()
        self._play_timer.timeout.connect(self._on_play_timer)

    @property
    def is_loaded(self) -> bool:
        """Check if a video is currently loaded."""
        return self._cap is not None and self._cap.isOpened()

    @property
    def is_playing(self) -> bool:
        """Check if video is currently playing."""
        return self._is_playing

    @property
    def current_frame(self) -> int:
        """Get current frame number."""
        return self._current_frame

    @property
    def total_frames(self) -> int:
        """Get total number of frames."""
        return self._total_frames

    @property
    def fps(self) -> float:
        """Get frames per second."""
        return self._fps

    @property
    def width(self) -> int:
        """Get video width."""
        return self._width

    @property
    def height(self) -> int:
        """Get video height."""
        return self._height

    @property
    def video_path(self) -> Optional[str]:
        """Get current video path."""
        return self._video_path

    def load_video(self, file_path: str) -> bool:
        """Load a video file.

        Args:
            file_path: Path to the video file

        Returns:
            True if video loaded successfully, False otherwise
        """
        # Close existing video if any
        if self.is_loaded:
            self.close_video()

        try:
            self._cap = cv2.VideoCapture(file_path)

            if not self._cap.isOpened():
                error_msg = f"Could not open video file: {file_path}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return False

            # Get video properties
            self._fps = self._cap.get(cv2.CAP_PROP_FPS)
            self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self._video_path = file_path
            self._current_frame = 0

            logger.info(
                f"Video loaded: {file_path} "
                f"({self._width}x{self._height}, "
                f"{self._fps:.2f} fps, "
                f"{self._total_frames} frames)"
            )

            # Emit signal with video info
            self.video_loaded.emit(self._fps, self._total_frames, self._width, self._height)

            # Load and show first frame
            self.seek_to_frame(0)

            return True

        except Exception as e:
            error_msg = f"Error loading video: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def close_video(self):
        """Close the current video and release resources."""
        if self._is_playing:
            self.stop_playback()

        if self._cap is not None:
            try:
                self._cap.release()
            except Exception as e:
                logger.warning(f"Error releasing video capture: {str(e)}")

        self._cap = None
        self._current_frame = 0
        self._total_frames = 0
        self._fps = 0.0
        self._width = 0
        self._height = 0
        self._video_path = None

        self.video_closed.emit()
        logger.info("Video closed")

    def seek_to_frame(self, frame_num: int) -> bool:
        """Seek to a specific frame.

        Args:
            frame_num: Frame number to seek to

        Returns:
            True if seek was successful, False otherwise
        """
        if not self.is_loaded:
            return False

        # Clamp frame number to valid range
        frame_num = max(0, min(frame_num, self._total_frames - 1))

        try:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = self._cap.read()

            if not ret:
                logger.warning(f"Could not read frame {frame_num}")
                return False

            self._current_frame = frame_num
            self.frame_changed.emit(frame_num, frame)

            return True

        except Exception as e:
            error_msg = f"Error seeking to frame {frame_num}: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def next_frame(self) -> bool:
        """Move to the next frame.

        Returns:
            True if successful, False if at end of video
        """
        if not self.is_loaded:
            return False

        if self._current_frame >= self._total_frames - 1:
            return False

        return self.seek_to_frame(self._current_frame + 1)

    def previous_frame(self) -> bool:
        """Move to the previous frame.

        Returns:
            True if successful, False if at beginning of video
        """
        if not self.is_loaded:
            return False

        if self._current_frame <= 0:
            return False

        return self.seek_to_frame(self._current_frame - 1)

    def start_playback(self):
        """Start video playback."""
        if not self.is_loaded or self._is_playing:
            return

        if self._fps <= 0:
            logger.warning("Cannot start playback: invalid FPS")
            return

        # Calculate timer interval (milliseconds per frame)
        interval_ms = int(1000 / self._fps)
        self._play_timer.start(interval_ms)
        self._is_playing = True

        self.playback_started.emit()
        logger.debug("Playback started")

    def stop_playback(self):
        """Stop video playback."""
        if not self._is_playing:
            return

        self._play_timer.stop()
        self._is_playing = False

        self.playback_stopped.emit()
        logger.debug("Playback stopped")

    def toggle_playback(self):
        """Toggle between play and pause."""
        if self._is_playing:
            self.stop_playback()
        else:
            self.start_playback()

    def _on_play_timer(self):
        """Called by timer during playback to advance to next frame."""
        if not self.next_frame():
            # Reached end of video, stop playback
            self.stop_playback()

    def get_current_frame_data(self) -> Optional[np.ndarray]:
        """Get the current frame data.

        Returns:
            Frame data as numpy array, or None if not available
        """
        if not self.is_loaded:
            return None

        try:
            # Save current position
            current_pos = self._cap.get(cv2.CAP_PROP_POS_FRAMES)

            # Seek to current frame and read
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame)
            ret, frame = self._cap.read()

            # Restore position
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)

            if ret:
                return frame
            return None

        except Exception as e:
            logger.error(f"Error getting current frame data: {str(e)}")
            return None

    def get_frame_at(self, frame_num: int) -> Optional[np.ndarray]:
        """Get frame data at specific frame number without changing current position.

        Args:
            frame_num: Frame number to retrieve

        Returns:
            Frame data as numpy array, or None if not available
        """
        if not self.is_loaded:
            return None

        if frame_num < 0 or frame_num >= self._total_frames:
            return None

        try:
            # Save current position
            current_pos = self._cap.get(cv2.CAP_PROP_POS_FRAMES)

            # Seek to requested frame and read
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = self._cap.read()

            # Restore position
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)

            if ret:
                return frame
            return None

        except Exception as e:
            logger.error(f"Error getting frame at {frame_num}: {str(e)}")
            return None
