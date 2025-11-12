"""Time utilities for video frame/time conversions.

This module provides utilities for converting between frames and time,
and formatting time for display.
"""

from typing import Tuple


class TimeCode:
    """Handle timecode conversions and formatting."""

    def __init__(self, fps: float):
        """Initialize TimeCode with frame rate.

        Args:
            fps: Frames per second
        """
        self.fps = fps

    def frames_to_seconds(self, frames: int) -> float:
        """Convert frames to seconds.

        Args:
            frames: Frame number

        Returns:
            Time in seconds
        """
        if self.fps <= 0:
            return 0.0
        return frames / self.fps

    def seconds_to_frames(self, seconds: float) -> int:
        """Convert seconds to frames.

        Args:
            seconds: Time in seconds

        Returns:
            Frame number
        """
        return int(seconds * self.fps)

    def frames_to_timecode(self, frames: int) -> str:
        """Convert frames to timecode string (HH:MM:SS).

        Args:
            frames: Frame number

        Returns:
            Timecode string in format HH:MM:SS
        """
        seconds = self.frames_to_seconds(frames)
        return self.seconds_to_timecode(seconds)

    def seconds_to_timecode(self, seconds: float) -> str:
        """Convert seconds to timecode string (HH:MM:SS).

        Args:
            seconds: Time in seconds

        Returns:
            Timecode string in format HH:MM:SS
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def frames_to_timecode_ms(self, frames: int) -> str:
        """Convert frames to timecode with milliseconds (HH:MM:SS.mmm).

        Args:
            frames: Frame number

        Returns:
            Timecode string in format HH:MM:SS.mmm
        """
        seconds = self.frames_to_seconds(frames)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

    def parse_timecode(self, timecode: str) -> Tuple[int, int, int]:
        """Parse timecode string to hours, minutes, seconds.

        Args:
            timecode: Timecode string in format HH:MM:SS or MM:SS

        Returns:
            Tuple of (hours, minutes, seconds)

        Raises:
            ValueError: If timecode format is invalid
        """
        parts = timecode.split(':')

        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours), int(minutes), int(seconds.split('.')[0])
        elif len(parts) == 2:
            minutes, seconds = parts
            return 0, int(minutes), int(seconds.split('.')[0])
        else:
            raise ValueError(f"Invalid timecode format: {timecode}")

    def timecode_to_frames(self, timecode: str) -> int:
        """Convert timecode string to frame number.

        Args:
            timecode: Timecode string in format HH:MM:SS or MM:SS

        Returns:
            Frame number
        """
        hours, minutes, seconds = self.parse_timecode(timecode)
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return self.seconds_to_frames(total_seconds)


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "1h 23m 45s" or "2m 30s")
    """
    if seconds < 60:
        return f"{int(seconds)}s"

    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    if minutes < 60:
        return f"{minutes}m {secs}s"

    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes}m {secs}s"


def format_frame_count(frames: int) -> str:
    """Format frame count for display.

    Args:
        frames: Number of frames

    Returns:
        Formatted string with thousands separator
    """
    return f"{frames:,}"
