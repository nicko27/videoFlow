"""Utility functions for VideoConverter plugin.

This module provides common utility functions for formatting sizes, durations,
and other helper functions used throughout the VideoConverter plugin.
"""

from pathlib import Path
from typing import Optional


def format_size(size: int) -> str:
    """Format file size in bytes to human-readable format.

    Args:
        size: Size in bytes.

    Returns:
        Human-readable size string (e.g., "1.5 MB", "2.3 GB").

    Examples:
        >>> format_size(1024)
        '1.0 KB'
        >>> format_size(1048576)
        '1.0 MB'
    """
    if size < 1024:
        return f"{size} B"
    elif size < 1048576:  # 1024^2
        return f"{size/1024:.1f} KB"
    elif size < 1073741824:  # 1024^3
        return f"{size/1048576:.1f} MB"
    else:
        return f"{size/1073741824:.1f} GB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format.

    Args:
        seconds: Duration in seconds.

    Returns:
        Human-readable duration string (e.g., "45s", "5min", "2.5h").

    Examples:
        >>> format_duration(30)
        '30s'
        >>> format_duration(120)
        '2min'
        >>> format_duration(3700)
        '1.0h'
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.0f}min"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def is_converted_file(file_path: Path, suffix: str = '_cvt') -> bool:
    """Check if a file is marked as converted based on filename suffix.

    Args:
        file_path: Path to the file to check.
        suffix: Suffix that marks converted files (default: '_cvt').

    Returns:
        True if the file stem ends with the converted suffix.

    Examples:
        >>> is_converted_file(Path('video_cvt.mp4'))
        True
        >>> is_converted_file(Path('video.mp4'))
        False
    """
    return file_path.stem.endswith(suffix)


def should_add_file(file_path: Path, settings) -> bool:
    """Determine if a file should be added based on settings criteria.

    Args:
        file_path: Path to the file to check.
        settings: Settings object with filtering criteria.

    Returns:
        True if the file passes all filters and should be added.
    """
    # Check size threshold FIRST (most efficient filter)
    if settings.use_size_threshold:
        try:
            size = file_path.stat().st_size
            if size < settings.size_threshold:
                return False
        except OSError:
            return False

    # Check converted file suffix
    converted_suffix = getattr(settings, 'converted_suffix', '_cvt')
    if is_converted_file(file_path, converted_suffix):
        ignore_converted = getattr(settings, 'ignore_converted_files', True)
        if ignore_converted:
            return False

    # Check non-compressible suffix
    failed_suffix = getattr(settings, 'failed_suffix', '_nocomp')
    if file_path.stem.endswith(failed_suffix):
        ignore_failed = getattr(settings, 'ignore_non_compressible', False)
        if ignore_failed:
            return False

    return True
