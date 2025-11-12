"""Utilities module for Video Editor.

This module contains reusable utility functions and classes
used across the video editor plugin.
"""

from .time_utils import TimeCode, format_duration, format_frame_count
from .video_utils import (
    get_aspect_ratio,
    get_aspect_ratio_string,
    is_standard_resolution,
    get_resolution_name,
    validate_video_file,
    get_file_size_mb,
    format_file_size,
    calculate_bitrate,
    format_bitrate,
    validate_frame_range
)

__all__ = [
    'TimeCode',
    'format_duration',
    'format_frame_count',
    'get_aspect_ratio',
    'get_aspect_ratio_string',
    'is_standard_resolution',
    'get_resolution_name',
    'validate_video_file',
    'get_file_size_mb',
    'format_file_size',
    'calculate_bitrate',
    'format_bitrate',
    'validate_frame_range'
]
