"""
Scan and discovery models for DuplicateFlow.

This module defines data structures for file scanning and discovery:
- VideoFile: Represents a video file with metadata
- ScanResult: Result of a directory scan operation
- DuplicateGroup: Group of duplicate/similar videos
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum


class VideoFormat(str, Enum):
    """
    Supported video formats.

    Common video container formats that can be processed.
    """
    MP4 = "mp4"
    MKV = "mkv"
    AVI = "avi"
    MOV = "mov"
    WMV = "wmv"
    FLV = "flv"
    WEBM = "webm"
    M4V = "m4v"
    MPG = "mpg"
    MPEG = "mpeg"
    UNKNOWN = "unknown"

    @classmethod
    def from_extension(cls, ext: str) -> 'VideoFormat':
        """
        Get VideoFormat from file extension.

        Args:
            ext: File extension (with or without dot)

        Returns:
            VideoFormat enum value

        Example:
            >>> VideoFormat.from_extension(".mp4")
            VideoFormat.MP4
            >>> VideoFormat.from_extension("mkv")
            VideoFormat.MKV
        """
        # Remove leading dot if present
        ext = ext.lower().lstrip('.')

        try:
            return cls(ext)
        except ValueError:
            return cls.UNKNOWN


@dataclass
class VideoFile:
    """
    Represents a video file with metadata.

    Contains all information about a video file discovered during scan:
    - File path and basic info (size, creation time)
    - Video properties (duration, resolution, codec)
    - Computed hash for deduplication

    Attributes:
        path: Absolute path to video file
        size_bytes: File size in bytes
        format: Video container format (MP4, MKV, etc.)
        created_at: File creation timestamp
        modified_at: File modification timestamp
        duration_seconds: Video duration in seconds (None if not yet computed)
        width: Video width in pixels (None if not yet computed)
        height: Video height in pixels (None if not yet computed)
        codec: Video codec (h264, hevc, etc.) (None if not yet computed)
        file_hash: SHA256 hash of file (None if not yet computed)
        metadata: Additional metadata (bitrate, fps, etc.)

    Example:
        >>> video = VideoFile(
        ...     path=Path("/videos/movie.mp4"),
        ...     size_bytes=1024*1024*500,  # 500 MB
        ...     format=VideoFormat.MP4,
        ...     created_at=datetime.now(),
        ...     modified_at=datetime.now(),
        ...     duration_seconds=3600.0,  # 1 hour
        ...     width=1920,
        ...     height=1080,
        ...     codec="h264"
        ... )
    """
    path: Path
    size_bytes: int
    format: VideoFormat
    created_at: datetime
    modified_at: datetime
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    codec: Optional[str] = None
    file_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_path(cls, path: Path) -> 'VideoFile':
        """
        Create VideoFile from a file path.

        Reads basic file information (size, timestamps) from filesystem.
        Video properties (duration, resolution) are not computed yet.

        Args:
            path: Path to video file

        Returns:
            VideoFile instance with basic info

        Raises:
            FileNotFoundError: If file doesn't exist

        Example:
            >>> video = VideoFile.from_path(Path("/videos/movie.mp4"))
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        stat = path.stat()

        return cls(
            path=path.absolute(),
            size_bytes=stat.st_size,
            format=VideoFormat.from_extension(path.suffix),
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
        )

    @property
    def filename(self) -> str:
        """Get filename without directory."""
        return self.path.name

    @property
    def extension(self) -> str:
        """Get file extension (with dot)."""
        return self.path.suffix

    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    @property
    def size_gb(self) -> float:
        """Get file size in gigabytes."""
        return self.size_bytes / (1024 * 1024 * 1024)

    @property
    def has_video_properties(self) -> bool:
        """Check if video properties (duration, resolution) are available."""
        return (
            self.duration_seconds is not None
            and self.width is not None
            and self.height is not None
        )

    @property
    def resolution(self) -> Optional[str]:
        """
        Get resolution as string (e.g., "1920x1080").

        Returns:
            Resolution string or None if not available
        """
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return None

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"VideoFile('{self.filename}', "
            f"{self.size_mb:.1f}MB, "
            f"{self.format.value})"
        )

    def __repr__(self) -> str:
        """Developer-friendly string representation."""
        return (
            f"VideoFile(path={self.path}, "
            f"size={self.size_mb:.1f}MB, "
            f"format={self.format.value})"
        )


@dataclass
class ScanResult:
    """
    Result of a directory scan operation.

    Contains all videos discovered during a scan:
    - List of video files found
    - Statistics about the scan
    - Timing information

    Attributes:
        videos: List of VideoFile objects discovered
        directories_scanned: Number of directories scanned
        total_files_checked: Total number of files examined
        scan_duration_seconds: Time taken to scan
        errors: List of error messages encountered
        timestamp: When scan was performed
        root_path: Root directory that was scanned
        metadata: Additional scan information

    Example:
        >>> result = ScanResult(
        ...     videos=[video1, video2, video3],
        ...     directories_scanned=5,
        ...     total_files_checked=150,
        ...     scan_duration_seconds=2.5,
        ...     timestamp=datetime.now(),
        ...     root_path=Path("/videos")
        ... )
    """
    videos: List[VideoFile]
    directories_scanned: int
    total_files_checked: int
    scan_duration_seconds: float
    timestamp: datetime
    root_path: Path
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def video_count(self) -> int:
        """Get number of videos found."""
        return len(self.videos)

    @property
    def total_size_bytes(self) -> int:
        """Get total size of all videos in bytes."""
        return sum(v.size_bytes for v in self.videos)

    @property
    def total_size_mb(self) -> float:
        """Get total size of all videos in megabytes."""
        return self.total_size_bytes / (1024 * 1024)

    @property
    def total_size_gb(self) -> float:
        """Get total size of all videos in gigabytes."""
        return self.total_size_bytes / (1024 * 1024 * 1024)

    @property
    def has_errors(self) -> bool:
        """Check if scan encountered any errors."""
        return len(self.errors) > 0

    @property
    def videos_by_format(self) -> Dict[VideoFormat, List[VideoFile]]:
        """
        Group videos by format.

        Returns:
            Dictionary mapping VideoFormat to list of videos
        """
        result: Dict[VideoFormat, List[VideoFile]] = {}
        for video in self.videos:
            if video.format not in result:
                result[video.format] = []
            result[video.format].append(video)
        return result

    def get_format_counts(self) -> Dict[str, int]:
        """
        Get count of videos by format.

        Returns:
            Dictionary mapping format name to count
        """
        counts: Dict[str, int] = {}
        for video in self.videos:
            format_name = video.format.value
            counts[format_name] = counts.get(format_name, 0) + 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ScanResult to dictionary for export.

        Returns:
            Dictionary with all scan data

        Example:
            >>> result.to_dict()
            {
                'root_path': '/videos',
                'timestamp': '2025-12-20T12:00:00',
                'videos': [...],
                'statistics': {...}
            }
        """
        return {
            'root_path': str(self.root_path),
            'timestamp': self.timestamp.isoformat(),
            'scan_duration_seconds': self.scan_duration_seconds,
            'directories_scanned': self.directories_scanned,
            'total_files_checked': self.total_files_checked,
            'statistics': {
                'video_count': self.video_count,
                'total_size_bytes': self.total_size_bytes,
                'total_size_mb': round(self.total_size_mb, 2),
                'total_size_gb': round(self.total_size_gb, 2),
                'format_counts': self.get_format_counts(),
                'has_errors': self.has_errors,
                'error_count': len(self.errors),
            },
            'videos': [
                {
                    'path': str(video.path),
                    'filename': video.filename,
                    'size_bytes': video.size_bytes,
                    'size_mb': round(video.size_mb, 2),
                    'format': video.format.value,
                    'created_at': video.created_at.isoformat(),
                    'modified_at': video.modified_at.isoformat(),
                    'duration_seconds': video.duration_seconds,
                    'resolution': video.resolution,
                    'codec': video.codec,
                }
                for video in self.videos
            ],
            'errors': self.errors,
            'metadata': self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """
        Export ScanResult to JSON string.

        Args:
            indent: Indentation level for pretty printing (default: 2)

        Returns:
            JSON string

        Example:
            >>> json_str = result.to_json()
            >>> with open('scan_results.json', 'w') as f:
            ...     f.write(json_str)
        """
        import json
        return json.dumps(self.to_dict(), indent=indent)

    def to_csv_rows(self) -> List[Dict[str, Any]]:
        """
        Convert ScanResult to CSV rows (one per video).

        Returns:
            List of dictionaries, one per video

        Example:
            >>> rows = result.to_csv_rows()
            >>> import csv
            >>> with open('scan_results.csv', 'w') as f:
            ...     writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            ...     writer.writeheader()
            ...     writer.writerows(rows)
        """
        return [
            {
                'path': str(video.path),
                'filename': video.filename,
                'size_mb': round(video.size_mb, 2),
                'size_gb': round(video.size_gb, 4),
                'format': video.format.value,
                'created_at': video.created_at.isoformat(),
                'modified_at': video.modified_at.isoformat(),
                'duration_seconds': video.duration_seconds or '',
                'resolution': video.resolution or '',
                'codec': video.codec or '',
            }
            for video in self.videos
        ]

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"ScanResult("
            f"{self.video_count} videos, "
            f"{self.total_size_gb:.2f}GB, "
            f"{self.scan_duration_seconds:.2f}s"
            f")"
        )


@dataclass
class DuplicateGroup:
    """
    Group of duplicate or similar videos.

    Represents a cluster of videos that are considered duplicates
    based on similarity scores.

    Attributes:
        videos: List of VideoFile objects in this group
        similarity_score: Average similarity score (0-100)
        algorithm: Algorithm used to detect duplicates
        metadata: Additional information (pairwise scores, etc.)

    Example:
        >>> group = DuplicateGroup(
        ...     videos=[video1, video2, video3],
        ...     similarity_score=95.5,
        ...     algorithm="optical_flow",
        ...     metadata={"pairwise_scores": {...}}
        ... )
    """
    videos: List[VideoFile]
    similarity_score: float
    algorithm: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def size(self) -> int:
        """Get number of videos in group."""
        return len(self.videos)

    @property
    def total_size_bytes(self) -> int:
        """Get total size of all videos in bytes."""
        return sum(v.size_bytes for v in self.videos)

    @property
    def total_size_mb(self) -> float:
        """Get total size of all videos in megabytes."""
        return self.total_size_bytes / (1024 * 1024)

    @property
    def potential_savings_bytes(self) -> int:
        """
        Get potential space savings if keeping only one video.

        Assumes we'd keep the first video and delete the rest.
        """
        if len(self.videos) <= 1:
            return 0
        return sum(v.size_bytes for v in self.videos[1:])

    @property
    def potential_savings_mb(self) -> float:
        """Get potential space savings in megabytes."""
        return self.potential_savings_bytes / (1024 * 1024)

    @property
    def potential_savings_gb(self) -> float:
        """Get potential space savings in gigabytes."""
        return self.potential_savings_bytes / (1024 * 1024 * 1024)

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"DuplicateGroup("
            f"{self.size} videos, "
            f"score={self.similarity_score:.1f}, "
            f"savings={self.potential_savings_mb:.1f}MB"
            f")"
        )
