"""Video utilities for resolution, aspect ratio, and validation.

This module provides utilities for working with video properties.
"""

import os
from typing import Tuple, Optional
from pathlib import Path


def get_aspect_ratio(width: int, height: int) -> Tuple[int, int]:
    """Calculate aspect ratio from width and height.

    Args:
        width: Video width in pixels
        height: Video height in pixels

    Returns:
        Tuple of (numerator, denominator) representing aspect ratio
    """
    def gcd(a: int, b: int) -> int:
        """Calculate greatest common divisor."""
        while b:
            a, b = b, a % b
        return a

    divisor = gcd(width, height)
    return (width // divisor, height // divisor)


def get_aspect_ratio_string(width: int, height: int) -> str:
    """Get aspect ratio as formatted string.

    Args:
        width: Video width in pixels
        height: Video height in pixels

    Returns:
        Aspect ratio string (e.g., "16:9", "4:3")
    """
    num, denom = get_aspect_ratio(width, height)
    return f"{num}:{denom}"


def is_standard_resolution(width: int, height: int) -> bool:
    """Check if resolution is a standard video resolution.

    Args:
        width: Video width in pixels
        height: Video height in pixels

    Returns:
        True if resolution is standard (720p, 1080p, 4K, etc.)
    """
    standard_resolutions = {
        (1280, 720),   # 720p
        (1920, 1080),  # 1080p
        (2560, 1440),  # 1440p
        (3840, 2160),  # 4K
        (7680, 4320),  # 8K
        (640, 480),    # VGA
        (854, 480),    # WVGA
        (1280, 800),   # WXGA
        (1366, 768),   # WXGA
        (1600, 900),   # HD+
    }
    return (width, height) in standard_resolutions


def get_resolution_name(width: int, height: int) -> str:
    """Get common name for video resolution.

    Args:
        width: Video width in pixels
        height: Video height in pixels

    Returns:
        Resolution name (e.g., "1080p", "4K") or dimension string
    """
    resolution_names = {
        (1280, 720): "720p",
        (1920, 1080): "1080p",
        (2560, 1440): "1440p",
        (3840, 2160): "4K",
        (7680, 4320): "8K",
        (640, 480): "480p",
    }

    if (width, height) in resolution_names:
        return resolution_names[(width, height)]

    return f"{width}x{height}"


def validate_video_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """Validate if a file is a valid video file.

    Args:
        file_path: Path to the video file

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not os.path.exists(file_path):
        return False, "File does not exist"

    if not os.path.isfile(file_path):
        return False, "Path is not a file"

    # Check file extension
    valid_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    ext = Path(file_path).suffix.lower()

    if ext not in valid_extensions:
        return False, f"Unsupported file format: {ext}"

    # Check file size (must be > 0)
    if os.path.getsize(file_path) == 0:
        return False, "File is empty"

    return True, None


def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in MB
    """
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 GB", "234 MB")
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.1f} {units[unit_index]}"


def calculate_bitrate(file_size_bytes: int, duration_seconds: float) -> int:
    """Calculate average bitrate.

    Args:
        file_size_bytes: File size in bytes
        duration_seconds: Duration in seconds

    Returns:
        Bitrate in bits per second
    """
    if duration_seconds <= 0:
        return 0

    return int((file_size_bytes * 8) / duration_seconds)


def format_bitrate(bitrate_bps: int) -> str:
    """Format bitrate in human-readable format.

    Args:
        bitrate_bps: Bitrate in bits per second

    Returns:
        Formatted string (e.g., "5.2 Mbps", "850 Kbps")
    """
    if bitrate_bps >= 1_000_000:
        return f"{bitrate_bps / 1_000_000:.1f} Mbps"
    elif bitrate_bps >= 1_000:
        return f"{bitrate_bps / 1_000:.0f} Kbps"
    else:
        return f"{bitrate_bps} bps"


def validate_frame_range(start_frame: int, end_frame: int, total_frames: int) -> Tuple[bool, Optional[str]]:
    """Validate a frame range.

    Args:
        start_frame: Start frame number
        end_frame: End frame number
        total_frames: Total number of frames in video

    Returns:
        Tuple of (is_valid, error_message)
    """
    if start_frame < 0:
        return False, "Start frame cannot be negative"

    if end_frame < 0:
        return False, "End frame cannot be negative"

    if start_frame >= end_frame:
        return False, "Start frame must be less than end frame"

    if start_frame >= total_frames:
        return False, f"Start frame ({start_frame}) exceeds total frames ({total_frames})"

    if end_frame > total_frames:
        return False, f"End frame ({end_frame}) exceeds total frames ({total_frames})"

    return True, None
