"""
Base utilities for video algorithms.

This module provides common utilities used by all algorithms:
- VideoLoader: Load videos and extract metadata
- FrameExtractor: Extract and preprocess frames
"""

from duplicateflow.algorithms.base.video_loader import (
    VideoLoader,
    load_video_metadata,
    get_video_duration,
)

from duplicateflow.algorithms.base.frame_extractor import (
    FrameExtractor,
    extract_frames_uniform,
    extract_frames_adaptive,
    calculate_frame_difference,
)

__all__ = [
    "VideoLoader",
    "load_video_metadata",
    "get_video_duration",
    "FrameExtractor",
    "extract_frames_uniform",
    "extract_frames_adaptive",
    "calculate_frame_difference",
]
