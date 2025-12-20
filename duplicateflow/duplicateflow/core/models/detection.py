"""
Detection result models for duplicate group detection.
"""
import json
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


@dataclass(frozen=True)
class DuplicateGroup:
    """
    Group of duplicate videos detected together.

    Attributes:
        videos: List of video paths in this group
        representative: The "main" video (usually largest or highest quality)
        avg_similarity: Average similarity score within the group
        total_size_mb: Combined size of all videos in the group

    Example:
        >>> from pathlib import Path
        >>> group = DuplicateGroup(
        ...     videos=[Path("/v1.mp4"), Path("/v2.mp4")],
        ...     representative=Path("/v1.mp4"),
        ...     avg_similarity=88.5,
        ...     total_size_mb=350.0
        ... )
        >>> len(group.videos)
        2
    """
    videos: List[Path]
    representative: Path
    avg_similarity: float
    total_size_mb: float

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert DuplicateGroup to dictionary for serialization.

        Returns:
            Dictionary representation of the duplicate group

        Example:
            >>> data = group.to_dict()
            >>> 'video_count' in data
            True
        """
        return {
            'videos': [str(v) for v in self.videos],
            'video_names': [v.name for v in self.videos],
            'video_count': len(self.videos),
            'representative': str(self.representative),
            'representative_name': self.representative.name,
            'avg_similarity': round(self.avg_similarity, 2),
            'total_size_mb': round(self.total_size_mb, 2),
            'total_size_gb': round(self.total_size_mb / 1024, 2)
        }


@dataclass(frozen=True)
class DetectionResult:
    """
    Result from detecting duplicates across multiple videos.

    Attributes:
        duplicate_groups: List of detected duplicate groups
        total_videos_scanned: Total number of videos analyzed
        total_comparisons: Number of pairwise comparisons performed
        duplicates_found: Total number of duplicate videos found
        space_reclaimable_mb: Potential space that could be reclaimed
        execution_time_seconds: Total execution time (seconds)
        timestamp: When this detection was performed
        pipeline_used: Name of the pipeline used for detection

    Example:
        >>> from datetime import datetime
        >>> result = DetectionResult(
        ...     duplicate_groups=[],
        ...     total_videos_scanned=10,
        ...     total_comparisons=45,
        ...     duplicates_found=0,
        ...     space_reclaimable_mb=0.0,
        ...     execution_time_seconds=120.5,
        ...     timestamp=datetime.now(),
        ...     pipeline_used="balanced"
        ... )
        >>> result.total_videos_scanned
        10
    """
    duplicate_groups: List[DuplicateGroup]
    total_videos_scanned: int
    total_comparisons: int
    duplicates_found: int
    space_reclaimable_mb: float
    execution_time_seconds: float
    timestamp: datetime
    pipeline_used: str

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert DetectionResult to dictionary for serialization.

        Returns:
            Dictionary representation of the detection result

        Example:
            >>> data = result.to_dict()
            >>> data['total_videos_scanned']
            10
        """
        return {
            'duplicate_groups': [
                group.to_dict() for group in self.duplicate_groups
            ],
            'total_videos_scanned': self.total_videos_scanned,
            'total_comparisons': self.total_comparisons,
            'duplicates_found': self.duplicates_found,
            'space_reclaimable_mb': round(self.space_reclaimable_mb, 2),
            'space_reclaimable_gb': round(self.space_reclaimable_mb / 1024, 2),
            'execution_time_seconds': round(self.execution_time_seconds, 2),
            'execution_time_minutes': round(self.execution_time_seconds / 60, 2),
            'timestamp': self.timestamp.isoformat(),
            'pipeline_used': self.pipeline_used,
            'statistics': self.get_statistics()
        }

    def to_json(self, indent: int = 2) -> str:
        """
        Export DetectionResult to JSON string.

        Args:
            indent: Number of spaces for JSON indentation (default: 2)

        Returns:
            JSON string representation

        Example:
            >>> json_str = result.to_json(indent=2)
            >>> 'duplicate_groups' in json_str
            True
        """
        return json.dumps(self.to_dict(), indent=indent)

    def to_csv_rows(self) -> List[Dict[str, Any]]:
        """
        Convert DetectionResult to CSV rows (one per duplicate group).

        Returns:
            List of dictionaries, one per duplicate group

        Example:
            >>> rows = result.to_csv_rows()
            >>> len(rows) == len(result.duplicate_groups)
            True
        """
        rows = []
        for idx, group in enumerate(self.duplicate_groups, 1):
            rows.append({
                'group_id': idx,
                'video_count': len(group.videos),
                'videos': '; '.join(v.name for v in group.videos),
                'representative': group.representative.name,
                'avg_similarity': round(group.avg_similarity, 2),
                'total_size_mb': round(group.total_size_mb, 2),
                'total_size_gb': round(group.total_size_mb / 1024, 2)
            })
        return rows

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics for the detection result.

        Returns:
            Dictionary with detection statistics

        Example:
            >>> stats = result.get_statistics()
            >>> 'groups_found' in stats
            True
        """
        if not self.duplicate_groups:
            return {
                'groups_found': 0,
                'avg_group_size': 0.0,
                'largest_group_size': 0,
                'avg_similarity': 0.0,
                'duplicate_percentage': 0.0,
                'comparisons_per_second': round(
                    self.total_comparisons / self.execution_time_seconds, 1
                ) if self.execution_time_seconds > 0 else 0
            }

        group_sizes = [len(g.videos) for g in self.duplicate_groups]
        avg_similarity = sum(g.avg_similarity for g in self.duplicate_groups) / len(self.duplicate_groups)

        duplicate_percentage = 0.0
        if self.total_videos_scanned > 0:
            duplicate_percentage = (self.duplicates_found / self.total_videos_scanned) * 100

        return {
            'groups_found': len(self.duplicate_groups),
            'avg_group_size': round(sum(group_sizes) / len(group_sizes), 1),
            'largest_group_size': max(group_sizes),
            'avg_similarity': round(avg_similarity, 2),
            'duplicate_percentage': round(duplicate_percentage, 1),
            'comparisons_per_second': round(
                self.total_comparisons / self.execution_time_seconds, 1
            ) if self.execution_time_seconds > 0 else 0
        }
