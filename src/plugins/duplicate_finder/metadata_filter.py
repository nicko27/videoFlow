"""
Metadata-based pre-filtering for video pairs.

⚠️ WARNING: Can create false negatives if videos are re-encoded!

Filters video pairs by duration and file size before expensive audio comparison.
Only use if you're sure videos haven't been re-encoded.
"""
import os
from typing import Tuple, Set
from pathlib import Path
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.MetadataFilter')


class MetadataFilter:
    """
    Fast metadata-based filtering for video pairs.

    Rejects pairs based on duration and file size differences.

    WARNING: This filter can miss re-encoded duplicates!

    Example:
        ```python
        filter = MetadataFilter(
            duration_tolerance=0.05,  # 5%
            min_size_ratio=0.90        # 90%
        )

        # Get video metadata
        metadata = {}
        for video in videos:
            metadata[video] = filter.get_metadata(video)

        # Filter pairs
        pairs = [(v1, v2) for v1 in videos for v2 in videos if v1 < v2]
        filtered_pairs = filter.filter_pairs(pairs, metadata)
        ```
    """

    def __init__(
        self,
        duration_tolerance: float = 0.05,
        min_size_ratio: float = 0.90
    ):
        """
        Initialize metadata filter.

        Args:
            duration_tolerance: Maximum duration difference (as fraction, e.g., 0.05 = 5%)
            min_size_ratio: Minimum file size ratio (smaller/larger)
        """
        self.duration_tolerance = duration_tolerance
        self.min_size_ratio = min_size_ratio

        self.stats = {
            'total_pairs': 0,
            'rejected_duration': 0,
            'rejected_size': 0,
            'passed': 0
        }

        logger.warning(f"Metadata filter initialized with duration_tolerance={duration_tolerance:.1%}, "
                      f"min_size_ratio={min_size_ratio:.1%}")
        logger.warning("⚠️ Metadata filter may miss re-encoded duplicates!")

    def get_metadata(self, video_path: str) -> dict:
        """
        Get metadata for a video file.

        Args:
            video_path: Path to video file

        Returns:
            Dictionary with 'duration' and 'size'
        """
        try:
            # Get file size
            file_size = os.path.getsize(video_path)

            # Get duration using ffprobe
            import subprocess
            result = subprocess.run([
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ], capture_output=True, text=True, timeout=10)

            duration = float(result.stdout.strip()) if result.returncode == 0 else 0.0

            return {
                'duration': duration,
                'size': file_size,
                'path': video_path
            }

        except Exception as e:
            logger.error(f"Error getting metadata for {video_path}: {e}")
            return {
                'duration': 0.0,
                'size': 0,
                'path': video_path
            }

    def should_compare(
        self,
        metadata1: dict,
        metadata2: dict
    ) -> Tuple[bool, str]:
        """
        Check if two videos should be compared based on metadata.

        Args:
            metadata1: Metadata for first video
            metadata2: Metadata for second video

        Returns:
            Tuple of (should_compare, reason)
        """
        dur1 = metadata1.get('duration', 0.0)
        dur2 = metadata2.get('duration', 0.0)
        size1 = metadata1.get('size', 0)
        size2 = metadata2.get('size', 0)

        # Check duration difference
        if dur1 > 0 and dur2 > 0:
            max_dur = max(dur1, dur2)
            dur_diff = abs(dur1 - dur2)
            if dur_diff / max_dur > self.duration_tolerance:
                return False, f"Duration difference too large: {dur_diff:.1f}s ({dur_diff/max_dur:.1%})"

        # Check size ratio
        if size1 > 0 and size2 > 0:
            size_ratio = min(size1, size2) / max(size1, size2)
            if size_ratio < self.min_size_ratio:
                return False, f"Size ratio too small: {size_ratio:.1%}"

        return True, "Passed metadata filter"

    def filter_pairs(
        self,
        pairs: Set[Tuple[str, str]],
        metadata_cache: dict
    ) -> Set[Tuple[str, str]]:
        """
        Filter video pairs based on metadata.

        Args:
            pairs: Set of (video1, video2) tuples
            metadata_cache: Dictionary mapping video_path -> metadata

        Returns:
            Filtered set of pairs
        """
        filtered_pairs = set()

        for video1, video2 in pairs:
            self.stats['total_pairs'] += 1

            meta1 = metadata_cache.get(video1)
            meta2 = metadata_cache.get(video2)

            if not meta1 or not meta2:
                # No metadata, keep pair
                filtered_pairs.add((video1, video2))
                self.stats['passed'] += 1
                continue

            should_compare, reason = self.should_compare(meta1, meta2)

            if should_compare:
                filtered_pairs.add((video1, video2))
                self.stats['passed'] += 1
            else:
                if 'Duration' in reason:
                    self.stats['rejected_duration'] += 1
                elif 'Size' in reason:
                    self.stats['rejected_size'] += 1

        total = self.stats['total_pairs']
        rejected = self.stats['rejected_duration'] + self.stats['rejected_size']
        reduction = (rejected / total) * 100 if total > 0 else 0

        logger.info(f"Metadata filter: {len(filtered_pairs)}/{len(pairs)} pairs passed "
                   f"(reduction: {reduction:.1f}%)")

        return filtered_pairs

    def get_stats(self) -> dict:
        """Get filter statistics."""
        total = self.stats['total_pairs']
        if total == 0:
            return self.stats

        return {
            'total_pairs': total,
            'rejected_duration': self.stats['rejected_duration'],
            'rejected_duration_pct': (self.stats['rejected_duration'] / total) * 100,
            'rejected_size': self.stats['rejected_size'],
            'rejected_size_pct': (self.stats['rejected_size'] / total) * 100,
            'passed': self.stats['passed'],
            'passed_pct': (self.stats['passed'] / total) * 100
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = {
            'total_pairs': 0,
            'rejected_duration': 0,
            'rejected_size': 0,
            'passed': 0
        }
