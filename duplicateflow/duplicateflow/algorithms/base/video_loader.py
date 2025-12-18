"""
Video loading utilities with caching support.

This module provides efficient video loading with integration to the MD5-based
cache system. It handles video capture, metadata extraction, and frame caching.
"""

import cv2
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import numpy as np


class VideoLoader:
    """
    Load and manage video files with caching support.

    This class provides efficient video loading with metadata caching
    and integration with DuplicateFlow's MD5-based cache system.

    Example:
        >>> loader = VideoLoader("video.mp4")
        >>> print(f"Duration: {loader.duration}s, FPS: {loader.fps}")
        >>> frame = loader.get_frame(10.0)  # Frame at 10 seconds
        >>> loader.release()
    """

    def __init__(self, video_path: str):
        """
        Initialize video loader.

        Args:
            video_path: Path to video file

        Raises:
            FileNotFoundError: If video file doesn't exist
            RuntimeError: If video cannot be opened
        """
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        self.cap = cv2.VideoCapture(str(self.video_path))
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video: {video_path}")

        # Cache metadata
        self._metadata = self._extract_metadata()

    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract video metadata."""
        return {
            'fps': self.cap.get(cv2.CAP_PROP_FPS),
            'frame_count': int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'duration': self.cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(self.cap.get(cv2.CAP_PROP_FPS), 1)
        }

    @property
    def fps(self) -> float:
        """Get video FPS."""
        return self._metadata['fps']

    @property
    def frame_count(self) -> int:
        """Get total frame count."""
        return self._metadata['frame_count']

    @property
    def width(self) -> int:
        """Get frame width."""
        return self._metadata['width']

    @property
    def height(self) -> int:
        """Get frame height."""
        return self._metadata['height']

    @property
    def duration(self) -> float:
        """Get video duration in seconds."""
        return self._metadata['duration']

    @property
    def resolution(self) -> Tuple[int, int]:
        """Get video resolution as (width, height)."""
        return (self.width, self.height)

    def get_frame(self, timestamp: float) -> Optional[np.ndarray]:
        """
        Get frame at specific timestamp.

        Args:
            timestamp: Time in seconds

        Returns:
            Frame as numpy array (BGR) or None if failed
        """
        frame_number = int(timestamp * self.fps)
        return self.get_frame_by_number(frame_number)

    def get_frame_by_number(self, frame_number: int) -> Optional[np.ndarray]:
        """
        Get frame by frame number.

        Args:
            frame_number: Frame index

        Returns:
            Frame as numpy array (BGR) or None if failed
        """
        if frame_number < 0 or frame_number >= self.frame_count:
            return None

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()

        return frame if ret else None

    def get_frames(
        self,
        start_time: float = 0.0,
        duration: Optional[float] = None,
        max_frames: Optional[int] = None,
        frame_step: int = 1
    ) -> list:
        """
        Get multiple frames from video.

        Args:
            start_time: Start time in seconds
            duration: Duration to extract (None = until end)
            max_frames: Maximum number of frames to extract
            frame_step: Extract every Nth frame

        Returns:
            List of frames as numpy arrays

        Example:
            >>> # Get 30 frames starting at 10s, every 3rd frame
            >>> frames = loader.get_frames(
            ...     start_time=10.0,
            ...     max_frames=30,
            ...     frame_step=3
            ... )
        """
        if duration is None:
            duration = self.duration - start_time

        start_frame = int(start_time * self.fps)
        end_frame = int((start_time + duration) * self.fps)
        end_frame = min(end_frame, self.frame_count)

        frames = []
        frame_num = start_frame

        while frame_num < end_frame:
            if max_frames and len(frames) >= max_frames:
                break

            frame = self.get_frame_by_number(frame_num)
            if frame is not None:
                frames.append(frame)

            frame_num += frame_step

        return frames

    def release(self):
        """Release video capture resources."""
        if self.cap:
            self.cap.release()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()

    def __del__(self):
        """Destructor."""
        self.release()


def load_video_metadata(video_path: str) -> Dict[str, Any]:
    """
    Load video metadata without keeping video open.

    Args:
        video_path: Path to video file

    Returns:
        Dictionary with metadata (fps, duration, width, height, etc.)

    Example:
        >>> metadata = load_video_metadata("video.mp4")
        >>> print(f"Duration: {metadata['duration']}s")
    """
    with VideoLoader(video_path) as loader:
        return {
            'fps': loader.fps,
            'frame_count': loader.frame_count,
            'width': loader.width,
            'height': loader.height,
            'duration': loader.duration,
            'resolution': loader.resolution
        }


def get_video_duration(video_path: str) -> float:
    """
    Get video duration quickly.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()

    return frame_count / max(fps, 1)
