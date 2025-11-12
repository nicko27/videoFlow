"""Conversion timing and estimation management.

This module provides timing and estimation functionality for video conversions,
tracking conversion speeds and estimating remaining time.
"""

from pathlib import Path
from typing import Dict, List, Optional
import time


class ConversionTimer:
    """Manages timing for conversions and estimates remaining time.

    Tracks start times for active conversions and maintains history of
    completed conversions to provide accurate time estimates.

    Attributes:
        start_times: Dictionary mapping file paths to start time info.
        completed_conversions: List of completed conversion statistics.
    """

    def __init__(self):
        """Initialize the conversion timer."""
        self.start_times: Dict[Path, Dict] = {}
        self.completed_conversions: List[Dict] = []

    def start_conversion(self, file_path: Path, file_size: int) -> None:
        """Start timing a conversion.

        Args:
            file_path: Path to the file being converted.
            file_size: Size of the file in bytes.
        """
        self.start_times[file_path] = {
            'start_time': time.time(),
            'file_size': file_size
        }

    def complete_conversion(self, file_path: Path, success: bool) -> None:
        """Mark a conversion as complete and record statistics.

        Args:
            file_path: Path to the file that was converted.
            success: Whether the conversion succeeded.
        """
        if file_path in self.start_times:
            start_info = self.start_times.pop(file_path)
            duration = time.time() - start_info['start_time']

            if success and duration > 0:
                self.completed_conversions.append({
                    'size': start_info['file_size'],
                    'duration': duration,
                    'speed': start_info['file_size'] / duration  # bytes/sec
                })

                # Keep only the 10 most recent conversions for estimation
                if len(self.completed_conversions) > 10:
                    self.completed_conversions.pop(0)

    def estimate_remaining_time(self, remaining_files: List[Dict]) -> Optional[float]:
        """Estimate remaining time based on conversion history.

        Args:
            remaining_files: List of dictionaries with 'size' key for remaining files.

        Returns:
            Estimated time in seconds, or None if no history available.
        """
        if not self.completed_conversions:
            return None

        # Calculate average speed (bytes/sec)
        avg_speed = sum(
            conv['speed'] for conv in self.completed_conversions
        ) / len(self.completed_conversions)

        # Calculate total remaining size
        total_remaining_size = sum(
            file_info.get('size', 0) for file_info in remaining_files
        )

        if avg_speed > 0:
            return total_remaining_size / avg_speed

        return None
