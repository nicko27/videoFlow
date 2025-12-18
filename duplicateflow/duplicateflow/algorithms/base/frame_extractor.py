"""
Frame extraction utilities with caching and preprocessing.

This module provides efficient frame extraction with optional preprocessing:
- Resizing
- Grayscale conversion
- Normalization
- Caching support
"""

import cv2
import numpy as np
from typing import List, Optional, Tuple
from duplicateflow.algorithms.base.video_loader import VideoLoader


class FrameExtractor:
    """
    Extract and preprocess frames from videos.

    This class handles frame extraction with optional preprocessing steps
    like resizing, grayscale conversion, and normalization.

    Example:
        >>> extractor = FrameExtractor(
        ...     resize=(224, 224),
        ...     grayscale=True
        ... )
        >>> frames = extractor.extract(
        ...     "video.mp4",
        ...     start_time=10.0,
        ...     max_frames=30
        ... )
    """

    def __init__(
        self,
        resize: Optional[Tuple[int, int]] = None,
        grayscale: bool = False,
        normalize: bool = False
    ):
        """
        Initialize frame extractor.

        Args:
            resize: Target size as (width, height), None = no resize
            grayscale: Convert to grayscale
            normalize: Normalize pixel values to 0-1
        """
        self.resize = resize
        self.grayscale = grayscale
        self.normalize = normalize

    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess a single frame.

        Args:
            frame: Input frame (BGR)

        Returns:
            Preprocessed frame
        """
        # Grayscale conversion
        if self.grayscale:
            if len(frame.shape) == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Resize
        if self.resize:
            frame = cv2.resize(frame, self.resize)

        # Normalize
        if self.normalize:
            frame = frame.astype(np.float32) / 255.0

        return frame

    def extract(
        self,
        video_path: str,
        start_time: float = 0.0,
        duration: Optional[float] = None,
        max_frames: Optional[int] = None,
        frame_step: int = 1
    ) -> List[np.ndarray]:
        """
        Extract frames from video with preprocessing.

        Args:
            video_path: Path to video file
            start_time: Start time in seconds
            duration: Duration to extract
            max_frames: Maximum number of frames
            frame_step: Extract every Nth frame

        Returns:
            List of preprocessed frames

        Example:
            >>> frames = extractor.extract(
            ...     "video.mp4",
            ...     start_time=10.0,
            ...     max_frames=30,
            ...     frame_step=3
            ... )
            >>> print(f"Extracted {len(frames)} frames")
        """
        with VideoLoader(video_path) as loader:
            raw_frames = loader.get_frames(
                start_time=start_time,
                duration=duration,
                max_frames=max_frames,
                frame_step=frame_step
            )

        # Preprocess all frames
        processed_frames = [
            self.preprocess_frame(frame)
            for frame in raw_frames
        ]

        return processed_frames

    def extract_single(
        self,
        video_path: str,
        timestamp: float
    ) -> Optional[np.ndarray]:
        """
        Extract and preprocess a single frame.

        Args:
            video_path: Path to video file
            timestamp: Time in seconds

        Returns:
            Preprocessed frame or None if failed
        """
        with VideoLoader(video_path) as loader:
            frame = loader.get_frame(timestamp)

        if frame is None:
            return None

        return self.preprocess_frame(frame)


def extract_frames_uniform(
    video_path: str,
    num_frames: int,
    start_time: float = 0.0,
    duration: Optional[float] = None,
    **preprocess_kwargs
) -> List[np.ndarray]:
    """
    Extract frames uniformly spaced over a time interval.

    This function extracts exactly `num_frames` frames uniformly distributed
    over the specified time interval.

    Args:
        video_path: Path to video file
        num_frames: Number of frames to extract
        start_time: Start time in seconds
        duration: Duration to cover (None = until end)
        **preprocess_kwargs: Preprocessing options (resize, grayscale, normalize)

    Returns:
        List of exactly `num_frames` frames

    Example:
        >>> # Extract 10 frames uniformly from 0s to 60s
        >>> frames = extract_frames_uniform(
        ...     "video.mp4",
        ...     num_frames=10,
        ...     duration=60.0,
        ...     resize=(224, 224)
        ... )
    """
    with VideoLoader(video_path) as loader:
        if duration is None:
            duration = loader.duration - start_time

        # Calculate uniform timestamps
        timestamps = np.linspace(start_time, start_time + duration, num_frames)

        # Extract frames
        extractor = FrameExtractor(**preprocess_kwargs)
        frames = []

        for ts in timestamps:
            frame = loader.get_frame(ts)
            if frame is not None:
                frame = extractor.preprocess_frame(frame)
                frames.append(frame)

    return frames


def extract_frames_adaptive(
    video_path: str,
    target_frames: int,
    min_variance: float = 0.0,
    **preprocess_kwargs
) -> List[np.ndarray]:
    """
    Extract frames adaptively based on scene changes.

    This function extracts frames, prioritizing scenes with high variance
    (more visual changes). Useful for getting representative frames.

    Args:
        video_path: Path to video file
        target_frames: Target number of frames
        min_variance: Minimum variance threshold
        **preprocess_kwargs: Preprocessing options

    Returns:
        List of frames with high scene variance

    Example:
        >>> # Extract 30 frames with high visual variance
        >>> frames = extract_frames_adaptive(
        ...     "video.mp4",
        ...     target_frames=30,
        ...     min_variance=10.0
        ... )
    """
    extractor = FrameExtractor(**preprocess_kwargs)

    with VideoLoader(video_path) as loader:
        # Sample more frames than needed
        sample_size = target_frames * 3
        frame_step = max(1, loader.frame_count // sample_size)

        raw_frames = loader.get_frames(
            frame_step=frame_step,
            max_frames=sample_size
        )

    # Calculate variance for each frame
    variances = []
    processed_frames = []

    for frame in raw_frames:
        processed = extractor.preprocess_frame(frame)
        variance = np.var(processed)

        if variance >= min_variance:
            variances.append(variance)
            processed_frames.append(processed)

    # Select top frames by variance
    if len(processed_frames) > target_frames:
        indices = np.argsort(variances)[-target_frames:]
        selected_frames = [processed_frames[i] for i in sorted(indices)]
    else:
        selected_frames = processed_frames

    return selected_frames


def calculate_frame_difference(frame1: np.ndarray, frame2: np.ndarray) -> float:
    """
    Calculate visual difference between two frames.

    Args:
        frame1: First frame
        frame2: Second frame

    Returns:
        Difference score (0 = identical, higher = more different)

    Example:
        >>> diff = calculate_frame_difference(frame1, frame2)
        >>> print(f"Difference: {diff:.2f}")
    """
    # Ensure same size
    if frame1.shape != frame2.shape:
        frame2 = cv2.resize(frame2, (frame1.shape[1], frame1.shape[0]))

    # Convert to grayscale if needed
    if len(frame1.shape) == 3:
        frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    # Calculate absolute difference
    diff = cv2.absdiff(frame1, frame2)

    return np.mean(diff)
