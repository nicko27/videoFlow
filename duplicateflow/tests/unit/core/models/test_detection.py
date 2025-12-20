"""
Unit tests for DetectionResult and DuplicateGroup models.
"""
import json
import pytest
from datetime import datetime
from pathlib import Path

from duplicateflow.core.models.detection import DetectionResult, DuplicateGroup


class TestDuplicateGroup:
    """Tests for DuplicateGroup model."""

    def test_duplicate_group_creation(self):
        """Test creating DuplicateGroup instance."""
        videos = [Path("/v1.mp4"), Path("/v2.mp4"), Path("/v3.mp4")]
        group = DuplicateGroup(
            videos=videos,
            representative=Path("/v1.mp4"),
            avg_similarity=88.5,
            total_size_mb=350.0
        )

        assert len(group.videos) == 3
        assert group.representative == Path("/v1.mp4")
        assert group.avg_similarity == 88.5
        assert group.total_size_mb == 350.0

    def test_duplicate_group_immutable(self):
        """Test that DuplicateGroup is immutable (frozen)."""
        group = DuplicateGroup(
            videos=[Path("/v1.mp4")],
            representative=Path("/v1.mp4"),
            avg_similarity=100.0,
            total_size_mb=200.0
        )

        with pytest.raises(AttributeError):
            group.avg_similarity = 95.0

    def test_to_dict(self):
        """Test converting DuplicateGroup to dictionary."""
        videos = [
            Path("/videos/movie1.mp4"),
            Path("/videos/movie2.mkv"),
            Path("/videos/movie3.avi")
        ]
        group = DuplicateGroup(
            videos=videos,
            representative=Path("/videos/movie1.mp4"),
            avg_similarity=92.123,
            total_size_mb=1024.567
        )

        data = group.to_dict()

        assert len(data["videos"]) == 3
        assert data["videos"][0] == "/videos/movie1.mp4"
        assert len(data["video_names"]) == 3
        assert data["video_names"][0] == "movie1.mp4"
        assert data["video_count"] == 3
        assert data["representative"] == "/videos/movie1.mp4"
        assert data["representative_name"] == "movie1.mp4"
        assert data["avg_similarity"] == 92.12  # Rounded
        assert data["total_size_mb"] == 1024.57  # Rounded
        assert data["total_size_gb"] == 1.00  # 1024.567 / 1024


class TestDetectionResult:
    """Tests for DetectionResult model."""

    @pytest.fixture
    def sample_groups(self):
        """Create sample duplicate groups for testing."""
        return [
            DuplicateGroup(
                videos=[Path("/v1.mp4"), Path("/v2.mp4")],
                representative=Path("/v1.mp4"),
                avg_similarity=90.0,
                total_size_mb=400.0
            ),
            DuplicateGroup(
                videos=[Path("/v3.mp4"), Path("/v4.mp4"), Path("/v5.mp4")],
                representative=Path("/v3.mp4"),
                avg_similarity=85.0,
                total_size_mb=600.0
            ),
        ]

    @pytest.fixture
    def sample_detection_result(self, sample_groups):
        """Create sample DetectionResult for testing."""
        return DetectionResult(
            duplicate_groups=sample_groups,
            total_videos_scanned=10,
            total_comparisons=45,
            duplicates_found=4,  # 2 in first group + 3 in second - 2 representatives
            space_reclaimable_mb=500.0,
            execution_time_seconds=120.5,
            timestamp=datetime(2025, 12, 20, 12, 0, 0),
            pipeline_used="balanced"
        )

    def test_detection_result_creation(self, sample_detection_result):
        """Test creating DetectionResult instance."""
        result = sample_detection_result

        assert len(result.duplicate_groups) == 2
        assert result.total_videos_scanned == 10
        assert result.total_comparisons == 45
        assert result.duplicates_found == 4
        assert result.space_reclaimable_mb == 500.0
        assert result.execution_time_seconds == 120.5
        assert result.pipeline_used == "balanced"

    def test_detection_result_immutable(self, sample_detection_result):
        """Test that DetectionResult is immutable (frozen)."""
        with pytest.raises(AttributeError):
            sample_detection_result.duplicates_found = 10

    def test_to_dict(self, sample_detection_result):
        """Test converting DetectionResult to dictionary."""
        data = sample_detection_result.to_dict()

        assert len(data["duplicate_groups"]) == 2
        assert data["total_videos_scanned"] == 10
        assert data["total_comparisons"] == 45
        assert data["duplicates_found"] == 4
        assert data["space_reclaimable_mb"] == 500.0
        assert data["space_reclaimable_gb"] == 0.49  # 500 / 1024
        assert data["execution_time_seconds"] == 120.5
        assert data["execution_time_minutes"] == 2.01  # 120.5 / 60
        assert data["pipeline_used"] == "balanced"
        assert "statistics" in data

    def test_to_json(self, sample_detection_result):
        """Test converting DetectionResult to JSON string."""
        json_str = sample_detection_result.to_json(indent=2)

        # Parse back to verify
        data = json.loads(json_str)
        assert data["total_videos_scanned"] == 10
        assert data["duplicates_found"] == 4
        assert len(data["duplicate_groups"]) == 2

    def test_to_csv_rows(self, sample_detection_result):
        """Test converting DetectionResult to CSV rows."""
        rows = sample_detection_result.to_csv_rows()

        assert len(rows) == 2  # One row per group

        # Check first group
        assert rows[0]["group_id"] == 1
        assert rows[0]["video_count"] == 2
        assert "v1.mp4" in rows[0]["videos"]
        assert rows[0]["representative"] == "v1.mp4"
        assert rows[0]["avg_similarity"] == 90.0
        assert rows[0]["total_size_mb"] == 400.0

        # Check second group
        assert rows[1]["group_id"] == 2
        assert rows[1]["video_count"] == 3
        assert rows[1]["representative"] == "v3.mp4"

    def test_to_csv_rows_empty(self):
        """Test to_csv_rows with no duplicate groups."""
        result = DetectionResult(
            duplicate_groups=[],
            total_videos_scanned=5,
            total_comparisons=10,
            duplicates_found=0,
            space_reclaimable_mb=0.0,
            execution_time_seconds=30.0,
            timestamp=datetime.now(),
            pipeline_used="fast"
        )

        rows = result.to_csv_rows()
        assert rows == []

    def test_get_statistics(self, sample_detection_result):
        """Test getting detection statistics."""
        stats = sample_detection_result.get_statistics()

        assert stats["groups_found"] == 2
        assert stats["avg_group_size"] == 2.5  # (2 + 3) / 2
        assert stats["largest_group_size"] == 3
        assert stats["avg_similarity"] == 87.5  # (90 + 85) / 2
        assert stats["duplicate_percentage"] == 40.0  # 4 / 10 * 100
        assert stats["comparisons_per_second"] == 0.4  # 45 / 120.5 rounded

    def test_get_statistics_empty(self):
        """Test statistics with no duplicate groups."""
        result = DetectionResult(
            duplicate_groups=[],
            total_videos_scanned=10,
            total_comparisons=45,
            duplicates_found=0,
            space_reclaimable_mb=0.0,
            execution_time_seconds=60.0,
            timestamp=datetime.now(),
            pipeline_used="fast"
        )

        stats = result.get_statistics()

        assert stats["groups_found"] == 0
        assert stats["avg_group_size"] == 0.0
        assert stats["largest_group_size"] == 0
        assert stats["avg_similarity"] == 0.0
        assert stats["duplicate_percentage"] == 0.0
        assert stats["comparisons_per_second"] == 0.8  # 45 / 60

    def test_timestamp_serialization(self, sample_detection_result):
        """Test that timestamp is properly serialized."""
        data = sample_detection_result.to_dict()

        assert data["timestamp"] == "2025-12-20T12:00:00"
        assert isinstance(data["timestamp"], str)

    def test_groups_serialization(self, sample_detection_result):
        """Test that duplicate groups are properly serialized."""
        data = sample_detection_result.to_dict()

        groups = data["duplicate_groups"]
        assert len(groups) == 2
        assert groups[0]["video_count"] == 2
        assert groups[1]["video_count"] == 3

    def test_zero_execution_time_stats(self):
        """Test statistics calculation with zero execution time."""
        result = DetectionResult(
            duplicate_groups=[],
            total_videos_scanned=5,
            total_comparisons=10,
            duplicates_found=0,
            space_reclaimable_mb=0.0,
            execution_time_seconds=0.0,  # Zero execution time
            timestamp=datetime.now(),
            pipeline_used="fast"
        )

        stats = result.get_statistics()
        assert stats["comparisons_per_second"] == 0  # Should not divide by zero

    def test_csv_rows_video_names(self, sample_groups):
        """Test that CSV rows contain video names separated by semicolons."""
        result = DetectionResult(
            duplicate_groups=sample_groups,
            total_videos_scanned=5,
            total_comparisons=10,
            duplicates_found=4,
            space_reclaimable_mb=200.0,
            execution_time_seconds=60.0,
            timestamp=datetime.now(),
            pipeline_used="balanced"
        )

        rows = result.to_csv_rows()

        # First group has 2 videos
        assert "v1.mp4; v2.mp4" in rows[0]["videos"]

        # Second group has 3 videos
        assert "v3.mp4; v4.mp4; v5.mp4" in rows[1]["videos"]
