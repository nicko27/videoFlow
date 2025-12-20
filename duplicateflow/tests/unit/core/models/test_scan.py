"""
Unit tests for scan models (VideoFile, ScanResult, DuplicateGroup).

Tests verify that the scan models work correctly.
"""

import pytest
from pathlib import Path
from datetime import datetime
from duplicateflow.core.models.scan import (
    VideoFile,
    ScanResult,
    DuplicateGroup,
    VideoFormat,
)


class TestVideoFormat:
    """Tests for VideoFormat enum."""

    def test_video_format_from_extension_with_dot(self):
        """Test from_extension with dot prefix."""
        assert VideoFormat.from_extension(".mp4") == VideoFormat.MP4
        assert VideoFormat.from_extension(".mkv") == VideoFormat.MKV
        assert VideoFormat.from_extension(".avi") == VideoFormat.AVI

    def test_video_format_from_extension_without_dot(self):
        """Test from_extension without dot prefix."""
        assert VideoFormat.from_extension("mp4") == VideoFormat.MP4
        assert VideoFormat.from_extension("mkv") == VideoFormat.MKV
        assert VideoFormat.from_extension("avi") == VideoFormat.AVI

    def test_video_format_from_extension_case_insensitive(self):
        """Test from_extension is case-insensitive."""
        assert VideoFormat.from_extension(".MP4") == VideoFormat.MP4
        assert VideoFormat.from_extension("MKV") == VideoFormat.MKV
        assert VideoFormat.from_extension(".AVI") == VideoFormat.AVI

    def test_video_format_from_extension_unknown(self):
        """Test from_extension returns UNKNOWN for unsupported formats."""
        assert VideoFormat.from_extension(".xyz") == VideoFormat.UNKNOWN
        assert VideoFormat.from_extension("unknown") == VideoFormat.UNKNOWN

    def test_video_format_all_supported_formats(self):
        """Test all supported video formats."""
        formats = ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "mpg", "mpeg"]
        for fmt in formats:
            result = VideoFormat.from_extension(fmt)
            assert result != VideoFormat.UNKNOWN
            assert result.value == fmt


class TestVideoFile:
    """Tests for VideoFile model."""

    def test_video_file_creation(self):
        """Test VideoFile creation with basic info."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024 * 1024 * 500,  # 500 MB
            format=VideoFormat.MP4,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            modified_at=datetime(2025, 1, 2, 12, 0, 0),
        )

        assert video.path == Path("/videos/movie.mp4")
        assert video.size_bytes == 1024 * 1024 * 500
        assert video.format == VideoFormat.MP4
        assert video.created_at == datetime(2025, 1, 1, 12, 0, 0)
        assert video.modified_at == datetime(2025, 1, 2, 12, 0, 0)

    def test_video_file_creation_with_video_properties(self):
        """Test VideoFile creation with video properties."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024 * 1024 * 500,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            duration_seconds=3600.0,  # 1 hour
            width=1920,
            height=1080,
            codec="h264",
        )

        assert video.duration_seconds == 3600.0
        assert video.width == 1920
        assert video.height == 1080
        assert video.codec == "h264"

    def test_video_file_filename_property(self):
        """Test filename property."""
        video = VideoFile(
            path=Path("/videos/subfolder/movie.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        assert video.filename == "movie.mp4"

    def test_video_file_extension_property(self):
        """Test extension property."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        assert video.extension == ".mp4"

    def test_video_file_size_mb_property(self):
        """Test size_mb property."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024 * 1024 * 500,  # 500 MB
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        assert video.size_mb == 500.0

    def test_video_file_size_gb_property(self):
        """Test size_gb property."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024 * 1024 * 1024 * 2,  # 2 GB
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        assert video.size_gb == 2.0

    def test_video_file_has_video_properties_true(self):
        """Test has_video_properties when all properties are set."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            duration_seconds=3600.0,
            width=1920,
            height=1080,
        )

        assert video.has_video_properties is True

    def test_video_file_has_video_properties_false(self):
        """Test has_video_properties when properties are missing."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        assert video.has_video_properties is False

    def test_video_file_resolution_property(self):
        """Test resolution property."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            width=1920,
            height=1080,
        )

        assert video.resolution == "1920x1080"

    def test_video_file_resolution_property_none(self):
        """Test resolution property when dimensions not set."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        assert video.resolution is None

    def test_video_file_str_representation(self):
        """Test string representation."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024 * 1024 * 500,  # 500 MB
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        str_repr = str(video)
        assert "movie.mp4" in str_repr
        assert "500.0MB" in str_repr
        assert "mp4" in str_repr

    def test_video_file_repr_representation(self):
        """Test repr representation."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024 * 1024 * 500,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        repr_str = repr(video)
        assert "/videos/movie.mp4" in repr_str
        assert "500.0MB" in repr_str

    def test_video_file_metadata_default(self):
        """Test metadata defaults to empty dict."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        assert video.metadata == {}

    def test_video_file_metadata_custom(self):
        """Test custom metadata."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            metadata={"bitrate": 5000, "fps": 30},
        )

        assert video.metadata["bitrate"] == 5000
        assert video.metadata["fps"] == 30


class TestScanResult:
    """Tests for ScanResult model."""

    def test_scan_result_creation(self):
        """Test ScanResult creation."""
        video1 = VideoFile(
            path=Path("/videos/movie1.mp4"),
            size_bytes=1024 * 1024 * 100,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video2 = VideoFile(
            path=Path("/videos/movie2.mkv"),
            size_bytes=1024 * 1024 * 200,
            format=VideoFormat.MKV,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        result = ScanResult(
            videos=[video1, video2],
            directories_scanned=5,
            total_files_checked=150,
            scan_duration_seconds=2.5,
            timestamp=datetime.now(),
            root_path=Path("/videos"),
        )

        assert len(result.videos) == 2
        assert result.directories_scanned == 5
        assert result.total_files_checked == 150
        assert result.scan_duration_seconds == 2.5
        assert result.root_path == Path("/videos")

    def test_scan_result_video_count_property(self):
        """Test video_count property."""
        result = ScanResult(
            videos=[],
            directories_scanned=1,
            total_files_checked=10,
            scan_duration_seconds=1.0,
            timestamp=datetime.now(),
            root_path=Path("/videos"),
        )

        assert result.video_count == 0

    def test_scan_result_total_size_bytes(self):
        """Test total_size_bytes property."""
        video1 = VideoFile(
            path=Path("/videos/movie1.mp4"),
            size_bytes=1024 * 1024 * 100,  # 100 MB
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video2 = VideoFile(
            path=Path("/videos/movie2.mp4"),
            size_bytes=1024 * 1024 * 200,  # 200 MB
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        result = ScanResult(
            videos=[video1, video2],
            directories_scanned=1,
            total_files_checked=10,
            scan_duration_seconds=1.0,
            timestamp=datetime.now(),
            root_path=Path("/videos"),
        )

        assert result.total_size_bytes == 1024 * 1024 * 300  # 300 MB

    def test_scan_result_total_size_mb(self):
        """Test total_size_mb property."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024 * 1024 * 500,  # 500 MB
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        result = ScanResult(
            videos=[video],
            directories_scanned=1,
            total_files_checked=10,
            scan_duration_seconds=1.0,
            timestamp=datetime.now(),
            root_path=Path("/videos"),
        )

        assert result.total_size_mb == 500.0

    def test_scan_result_total_size_gb(self):
        """Test total_size_gb property."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024 * 1024 * 1024 * 2,  # 2 GB
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        result = ScanResult(
            videos=[video],
            directories_scanned=1,
            total_files_checked=10,
            scan_duration_seconds=1.0,
            timestamp=datetime.now(),
            root_path=Path("/videos"),
        )

        assert result.total_size_gb == 2.0

    def test_scan_result_has_errors_false(self):
        """Test has_errors when no errors."""
        result = ScanResult(
            videos=[],
            directories_scanned=1,
            total_files_checked=10,
            scan_duration_seconds=1.0,
            timestamp=datetime.now(),
            root_path=Path("/videos"),
        )

        assert result.has_errors is False

    def test_scan_result_has_errors_true(self):
        """Test has_errors when errors present."""
        result = ScanResult(
            videos=[],
            directories_scanned=1,
            total_files_checked=10,
            scan_duration_seconds=1.0,
            timestamp=datetime.now(),
            root_path=Path("/videos"),
            errors=["Permission denied: /protected/video.mp4"],
        )

        assert result.has_errors is True

    def test_scan_result_videos_by_format(self):
        """Test videos_by_format property."""
        video1 = VideoFile(
            path=Path("/videos/movie1.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video2 = VideoFile(
            path=Path("/videos/movie2.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video3 = VideoFile(
            path=Path("/videos/movie3.mkv"),
            size_bytes=1024,
            format=VideoFormat.MKV,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        result = ScanResult(
            videos=[video1, video2, video3],
            directories_scanned=1,
            total_files_checked=10,
            scan_duration_seconds=1.0,
            timestamp=datetime.now(),
            root_path=Path("/videos"),
        )

        by_format = result.videos_by_format
        assert len(by_format[VideoFormat.MP4]) == 2
        assert len(by_format[VideoFormat.MKV]) == 1

    def test_scan_result_get_format_counts(self):
        """Test get_format_counts method."""
        video1 = VideoFile(
            path=Path("/videos/movie1.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video2 = VideoFile(
            path=Path("/videos/movie2.mkv"),
            size_bytes=1024,
            format=VideoFormat.MKV,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video3 = VideoFile(
            path=Path("/videos/movie3.mkv"),
            size_bytes=1024,
            format=VideoFormat.MKV,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        result = ScanResult(
            videos=[video1, video2, video3],
            directories_scanned=1,
            total_files_checked=10,
            scan_duration_seconds=1.0,
            timestamp=datetime.now(),
            root_path=Path("/videos"),
        )

        counts = result.get_format_counts()
        assert counts["mp4"] == 1
        assert counts["mkv"] == 2

    def test_scan_result_str_representation(self):
        """Test string representation."""
        result = ScanResult(
            videos=[],
            directories_scanned=5,
            total_files_checked=150,
            scan_duration_seconds=2.5,
            timestamp=datetime.now(),
            root_path=Path("/videos"),
        )

        str_repr = str(result)
        assert "0 videos" in str_repr
        assert "2.50s" in str_repr


class TestDuplicateGroup:
    """Tests for DuplicateGroup model."""

    def test_duplicate_group_creation(self):
        """Test DuplicateGroup creation."""
        video1 = VideoFile(
            path=Path("/videos/movie1.mp4"),
            size_bytes=1024 * 1024 * 100,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video2 = VideoFile(
            path=Path("/videos/movie2.mp4"),
            size_bytes=1024 * 1024 * 100,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        group = DuplicateGroup(
            videos=[video1, video2],
            similarity_score=95.5,
            algorithm="optical_flow",
        )

        assert len(group.videos) == 2
        assert group.similarity_score == 95.5
        assert group.algorithm == "optical_flow"

    def test_duplicate_group_size_property(self):
        """Test size property."""
        video1 = VideoFile(
            path=Path("/videos/movie1.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video2 = VideoFile(
            path=Path("/videos/movie2.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video3 = VideoFile(
            path=Path("/videos/movie3.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        group = DuplicateGroup(
            videos=[video1, video2, video3],
            similarity_score=90.0,
            algorithm="optical_flow",
        )

        assert group.size == 3

    def test_duplicate_group_total_size_bytes(self):
        """Test total_size_bytes property."""
        video1 = VideoFile(
            path=Path("/videos/movie1.mp4"),
            size_bytes=1024 * 1024 * 100,  # 100 MB
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video2 = VideoFile(
            path=Path("/videos/movie2.mp4"),
            size_bytes=1024 * 1024 * 150,  # 150 MB
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        group = DuplicateGroup(
            videos=[video1, video2],
            similarity_score=95.0,
            algorithm="optical_flow",
        )

        assert group.total_size_bytes == 1024 * 1024 * 250  # 250 MB

    def test_duplicate_group_total_size_mb(self):
        """Test total_size_mb property."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024 * 1024 * 500,  # 500 MB
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        group = DuplicateGroup(
            videos=[video],
            similarity_score=100.0,
            algorithm="optical_flow",
        )

        assert group.total_size_mb == 500.0

    def test_duplicate_group_potential_savings_bytes(self):
        """Test potential_savings_bytes property."""
        video1 = VideoFile(
            path=Path("/videos/movie1.mp4"),
            size_bytes=1024 * 1024 * 100,  # 100 MB (keep)
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video2 = VideoFile(
            path=Path("/videos/movie2.mp4"),
            size_bytes=1024 * 1024 * 150,  # 150 MB (delete)
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video3 = VideoFile(
            path=Path("/videos/movie3.mp4"),
            size_bytes=1024 * 1024 * 200,  # 200 MB (delete)
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        group = DuplicateGroup(
            videos=[video1, video2, video3],
            similarity_score=95.0,
            algorithm="optical_flow",
        )

        # Savings = 150 MB + 200 MB = 350 MB
        assert group.potential_savings_bytes == 1024 * 1024 * 350

    def test_duplicate_group_potential_savings_single_video(self):
        """Test potential_savings when only one video."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024 * 1024 * 500,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        group = DuplicateGroup(
            videos=[video],
            similarity_score=100.0,
            algorithm="optical_flow",
        )

        assert group.potential_savings_bytes == 0

    def test_duplicate_group_potential_savings_mb(self):
        """Test potential_savings_mb property."""
        video1 = VideoFile(
            path=Path("/videos/movie1.mp4"),
            size_bytes=1024 * 1024 * 100,  # Keep
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video2 = VideoFile(
            path=Path("/videos/movie2.mp4"),
            size_bytes=1024 * 1024 * 300,  # Delete
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        group = DuplicateGroup(
            videos=[video1, video2],
            similarity_score=95.0,
            algorithm="optical_flow",
        )

        assert group.potential_savings_mb == 300.0

    def test_duplicate_group_potential_savings_gb(self):
        """Test potential_savings_gb property."""
        video1 = VideoFile(
            path=Path("/videos/movie1.mp4"),
            size_bytes=1024 * 1024 * 1024 * 1,  # 1 GB (keep)
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video2 = VideoFile(
            path=Path("/videos/movie2.mp4"),
            size_bytes=1024 * 1024 * 1024 * 2,  # 2 GB (delete)
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        group = DuplicateGroup(
            videos=[video1, video2],
            similarity_score=95.0,
            algorithm="optical_flow",
        )

        assert group.potential_savings_gb == 2.0

    def test_duplicate_group_str_representation(self):
        """Test string representation."""
        video1 = VideoFile(
            path=Path("/videos/movie1.mp4"),
            size_bytes=1024 * 1024 * 100,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        video2 = VideoFile(
            path=Path("/videos/movie2.mp4"),
            size_bytes=1024 * 1024 * 100,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        group = DuplicateGroup(
            videos=[video1, video2],
            similarity_score=95.5,
            algorithm="optical_flow",
        )

        str_repr = str(group)
        assert "2 videos" in str_repr
        assert "score=95.5" in str_repr
        assert "100.0MB" in str_repr

    def test_duplicate_group_metadata_default(self):
        """Test metadata defaults to empty dict."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        group = DuplicateGroup(
            videos=[video],
            similarity_score=100.0,
            algorithm="optical_flow",
        )

        assert group.metadata == {}

    def test_duplicate_group_metadata_custom(self):
        """Test custom metadata."""
        video = VideoFile(
            path=Path("/videos/movie.mp4"),
            size_bytes=1024,
            format=VideoFormat.MP4,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        group = DuplicateGroup(
            videos=[video],
            similarity_score=95.0,
            algorithm="optical_flow",
            metadata={"pairwise_scores": {(0, 1): 95.0}},
        )

        assert "pairwise_scores" in group.metadata
