"""
Unit tests for DuplicateFinderService.

Tests the N-to-N duplicate detection service that identifies
groups of similar videos.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock

from duplicateflow.core.services import DuplicateFinderService, ComparisonService
from duplicateflow.core.interfaces import NullProgressReporter, NullUIAdapter
from duplicateflow.core.models import ComparisonResult


class TestDuplicateFinderServiceInstantiation:
    """Test service instantiation."""

    def test_init_with_defaults(self):
        """Test initialization with default comparison service."""
        service = DuplicateFinderService(
            NullProgressReporter(),
            NullUIAdapter()
        )
        assert service.comparison_service is not None
        assert isinstance(service.comparison_service, ComparisonService)

    def test_init_with_custom_comparison_service(self):
        """Test initialization with custom comparison service."""
        mock_comparison = Mock(spec=ComparisonService)
        service = DuplicateFinderService(
            NullProgressReporter(),
            NullUIAdapter(),
            comparison_service=mock_comparison
        )
        assert service.comparison_service == mock_comparison

    def test_dependency_injection(self):
        """Test that progress and ui adapters are properly injected."""
        progress = NullProgressReporter()
        ui = NullUIAdapter()

        service = DuplicateFinderService(progress, ui)

        assert service.progress is progress
        assert service.ui is ui


class TestDuplicateFinderServiceFindDuplicates:
    """Test find_duplicates method."""

    @pytest.fixture
    def service_with_mock_comparison(self):
        """Service with mocked comparison service."""
        mock_comparison = Mock(spec=ComparisonService)
        mock_comparison._get_pipeline_name.return_value = "test_pipeline"

        return DuplicateFinderService(
            NullProgressReporter(),
            NullUIAdapter(),
            comparison_service=mock_comparison
        )

    def test_find_duplicates_less_than_two_videos(self, service_with_mock_comparison):
        """Test with fewer than 2 videos raises ValueError."""
        with pytest.raises(ValueError, match="Need at least 2 videos"):
            service_with_mock_comparison.find_duplicates([], threshold=70.0)

        with pytest.raises(ValueError, match="Need at least 2 videos"):
            service_with_mock_comparison.find_duplicates([Path("/video.mp4")], threshold=70.0)

    def test_find_duplicates_invalid_threshold_low(self, service_with_mock_comparison, tmp_path):
        """Test with threshold below 0."""
        videos = [tmp_path / "v1.mp4", tmp_path / "v2.mp4"]
        for v in videos:
            v.touch()

        with pytest.raises(ValueError, match="Threshold must be between 0 and 100"):
            service_with_mock_comparison.find_duplicates(videos, threshold=-5.0)

    def test_find_duplicates_invalid_threshold_high(self, service_with_mock_comparison, tmp_path):
        """Test with threshold above 100."""
        videos = [tmp_path / "v1.mp4", tmp_path / "v2.mp4"]
        for v in videos:
            v.touch()

        with pytest.raises(ValueError, match="Threshold must be between 0 and 100"):
            service_with_mock_comparison.find_duplicates(videos, threshold=150.0)

    def test_find_duplicates_two_videos_no_match(self, service_with_mock_comparison, tmp_path):
        """Test with two videos that are not duplicates."""
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        # Mock comparison to return no match
        mock_result = Mock(spec=ComparisonResult)
        mock_result.is_duplicate = False
        mock_result.similarity_score = 50.0

        service_with_mock_comparison.comparison_service.compare_videos.return_value = mock_result

        result = service_with_mock_comparison.find_duplicates([video1, video2], threshold=70.0)

        assert result.total_videos_scanned == 2
        assert result.total_comparisons == 1
        assert len(result.duplicate_groups) == 0
        assert result.duplicates_found == 0

    def test_find_duplicates_two_videos_match(self, service_with_mock_comparison, tmp_path):
        """Test with two videos that are duplicates."""
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        # Create files with some content for size calculation
        video1.write_bytes(b"0" * 1024 * 1024)  # 1 MB
        video2.write_bytes(b"0" * 1024 * 1024)  # 1 MB

        # Mock comparison to return duplicate match
        mock_result = Mock(spec=ComparisonResult)
        mock_result.is_duplicate = True
        mock_result.similarity_score = 85.0
        mock_result.video1_path = video1
        mock_result.video2_path = video2

        service_with_mock_comparison.comparison_service.compare_videos.return_value = mock_result

        result = service_with_mock_comparison.find_duplicates([video1, video2], threshold=70.0)

        assert result.total_videos_scanned == 2
        assert result.total_comparisons == 1
        assert len(result.duplicate_groups) == 1
        assert result.duplicates_found == 1
        assert len(result.duplicate_groups[0].videos) == 2

    def test_find_duplicates_three_videos_all_match(self, service_with_mock_comparison, tmp_path):
        """Test clustering: A=B, B=C should form single group A,B,C."""
        videoA = tmp_path / "videoA.mp4"
        videoB = tmp_path / "videoB.mp4"
        videoC = tmp_path / "videoC.mp4"
        # Create files with content
        for v in [videoA, videoB, videoC]:
            v.write_bytes(b"0" * 1024 * 1024)

        # Mock comparison service to return matches for all pairs
        def mock_compare(v1, v2, threshold):
            result = Mock(spec=ComparisonResult)
            result.video1_path = v1
            result.video2_path = v2
            result.is_duplicate = True
            result.similarity_score = 85.0
            return result

        service_with_mock_comparison.comparison_service.compare_videos.side_effect = mock_compare

        result = service_with_mock_comparison.find_duplicates([videoA, videoB, videoC], threshold=70.0)

        # Should form 1 group with all 3 videos
        assert len(result.duplicate_groups) == 1
        assert len(result.duplicate_groups[0].videos) == 3
        assert result.duplicates_found == 2  # 2 duplicates (keeping 1 as representative)
        assert result.total_comparisons == 3  # 3 pairs: A-B, A-C, B-C

    def test_find_duplicates_three_videos_partial_match(self, service_with_mock_comparison, tmp_path):
        """Test with partial matches: A=B but not C."""
        videoA = tmp_path / "videoA.mp4"
        videoB = tmp_path / "videoB.mp4"
        videoC = tmp_path / "videoC.mp4"
        for v in [videoA, videoB, videoC]:
            v.write_bytes(b"0" * 1024 * 1024)

        # Mock comparison: A=B, but C is different
        def mock_compare(v1, v2, threshold):
            result = Mock(spec=ComparisonResult)
            result.video1_path = v1
            result.video2_path = v2

            if (v1, v2) in [(videoA, videoB), (videoB, videoA)]:
                result.is_duplicate = True
                result.similarity_score = 85.0
            else:
                result.is_duplicate = False
                result.similarity_score = 50.0

            return result

        service_with_mock_comparison.comparison_service.compare_videos.side_effect = mock_compare

        result = service_with_mock_comparison.find_duplicates([videoA, videoB, videoC], threshold=70.0)

        # Should form 1 group with A and B
        assert len(result.duplicate_groups) == 1
        assert len(result.duplicate_groups[0].videos) == 2
        assert result.duplicates_found == 1

    def test_find_duplicates_max_comparisons_limit(self, service_with_mock_comparison, tmp_path):
        """Test max_comparisons parameter limits total comparisons."""
        # Create 10 videos (would be 45 comparisons without limit)
        videos = [tmp_path / f"video{i}.mp4" for i in range(10)]
        for v in videos:
            v.touch()

        mock_result = Mock(spec=ComparisonResult)
        mock_result.is_duplicate = False
        mock_result.similarity_score = 50.0
        service_with_mock_comparison.comparison_service.compare_videos.return_value = mock_result

        # Limit to 20 comparisons
        result = service_with_mock_comparison.find_duplicates(
            videos,
            threshold=70.0,
            max_comparisons=20
        )

        assert result.total_comparisons == 20
        assert result.total_comparisons < 45

    def test_find_duplicates_ui_messages(self, tmp_path):
        """Test UI messages during detection."""
        ui = NullUIAdapter()
        mock_comparison = Mock(spec=ComparisonService)
        mock_comparison._get_pipeline_name.return_value = "test"
        mock_result = Mock(spec=ComparisonResult)
        mock_result.is_duplicate = False
        mock_result.similarity_score = 50.0
        mock_comparison.compare_videos.return_value = mock_result

        service = DuplicateFinderService(
            NullProgressReporter(),
            ui,
            comparison_service=mock_comparison
        )

        videos = [tmp_path / f"video{i}.mp4" for i in range(3)]
        for v in videos:
            v.touch()

        service.find_duplicates(videos, threshold=70.0)

        # Verify messages were sent
        assert len(ui.messages) > 0
        messages_text = [m['message'] for m in ui.messages]
        assert any("Starting duplicate detection" in msg for msg in messages_text)
        assert any("Detection complete" in msg for msg in messages_text)

    def test_find_duplicates_comparison_error_handling(self, service_with_mock_comparison, tmp_path):
        """Test handling of comparison errors."""
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        # Mock comparison to raise exception
        service_with_mock_comparison.comparison_service.compare_videos.side_effect = RuntimeError("Comparison failed")

        # Should not raise, but should handle error gracefully
        result = service_with_mock_comparison.find_duplicates([video1, video2], threshold=70.0)

        # Should still return result (with no duplicates found)
        assert result.total_videos_scanned == 2
        assert result.total_comparisons == 1
        assert len(result.duplicate_groups) == 0


class TestDuplicateFinderServiceGroupBuilding:
    """Test duplicate group building logic."""

    def test_build_duplicate_groups_single_pair(self, tmp_path):
        """Test building groups from single duplicate pair."""
        service = DuplicateFinderService(
            NullProgressReporter(),
            NullUIAdapter()
        )

        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.write_bytes(b"0" * 1024 * 1024)  # 1 MB
        video2.write_bytes(b"0" * 1024 * 1024)  # 1 MB

        duplicate_pairs = [(0, 1, 85.0)]
        all_videos = [video1, video2]

        groups = service._build_duplicate_groups(duplicate_pairs, all_videos)

        assert len(groups) == 1
        assert len(groups[0].videos) == 2
        assert groups[0].avg_similarity == 85.0
        assert groups[0].total_size_mb > 0
        assert groups[0].representative in [video1, video2]

    def test_build_duplicate_groups_transitive(self, tmp_path):
        """Test transitive closure: A=B, B=C creates group {A,B,C}."""
        service = DuplicateFinderService(
            NullProgressReporter(),
            NullUIAdapter()
        )

        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video3 = tmp_path / "video3.mp4"
        for v in [video1, video2, video3]:
            v.write_bytes(b"0" * 1024 * 1024)

        # A=B (0=1), B=C (1=2)
        duplicate_pairs = [(0, 1, 85.0), (1, 2, 90.0)]
        all_videos = [video1, video2, video3]

        groups = service._build_duplicate_groups(duplicate_pairs, all_videos)

        assert len(groups) == 1
        assert len(groups[0].videos) == 3

    def test_build_duplicate_groups_multiple_groups(self, tmp_path):
        """Test multiple separate groups."""
        service = DuplicateFinderService(
            NullProgressReporter(),
            NullUIAdapter()
        )

        videos = [tmp_path / f"video{i}.mp4" for i in range(6)]
        for v in videos:
            v.write_bytes(b"0" * 1024 * 1024)

        # Group 1: {0, 1, 2}  Group 2: {3, 4}  Singleton: {5}
        duplicate_pairs = [
            (0, 1, 85.0), (1, 2, 90.0),  # Group 1
            (3, 4, 80.0)                  # Group 2
        ]

        groups = service._build_duplicate_groups(duplicate_pairs, videos)

        # Should have 2 groups (singletons excluded)
        assert len(groups) == 2

        # Check group sizes
        group_sizes = sorted([len(g.videos) for g in groups])
        assert group_sizes == [2, 3]

    def test_build_duplicate_groups_empty(self, tmp_path):
        """Test with no duplicate pairs."""
        mock_comparison = Mock()
        service = DuplicateFinderService(
            NullProgressReporter(),
            NullUIAdapter(),
            comparison_service=mock_comparison
        )

        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        duplicate_pairs = []
        all_videos = [video1, video2]

        groups = service._build_duplicate_groups(duplicate_pairs, all_videos)

        assert len(groups) == 0  # No groups (all singletons)


class TestDuplicateFinderServiceHelpers:
    """Test helper methods."""

    def test_calculate_avg_similarity_single_pair(self):
        """Test calculating average similarity for a pair."""
        mock_comparison = Mock()
        service = DuplicateFinderService(
            NullProgressReporter(),
            NullUIAdapter(),
            comparison_service=mock_comparison
        )

        indices = [0, 1]
        similarity_matrix = {(0, 1): 85.0}

        avg = service._calculate_avg_similarity(indices, similarity_matrix)

        assert avg == 85.0

    def test_calculate_avg_similarity_multiple_pairs(self):
        """Test calculating average similarity for multiple pairs."""
        mock_comparison = Mock()
        service = DuplicateFinderService(
            NullProgressReporter(),
            NullUIAdapter(),
            comparison_service=mock_comparison
        )

        indices = [0, 1, 2]
        similarity_matrix = {
            (0, 1): 80.0,
            (1, 2): 90.0,
            (0, 2): 85.0
        }

        avg = service._calculate_avg_similarity(indices, similarity_matrix)

        # Average of 80, 90, 85 = 85.0
        assert avg == pytest.approx(85.0, abs=0.1)

    def test_calculate_avg_similarity_empty(self):
        """Test calculating average similarity with no data."""
        mock_comparison = Mock()
        service = DuplicateFinderService(
            NullProgressReporter(),
            NullUIAdapter(),
            comparison_service=mock_comparison
        )

        indices = [0, 1]
        similarity_matrix = {}

        avg = service._calculate_avg_similarity(indices, similarity_matrix)

        assert avg == 100.0  # Default when no data

    def test_calculate_reclaimable_space(self, tmp_path):
        """Test calculating reclaimable space."""
        mock_comparison = Mock()
        service = DuplicateFinderService(
            NullProgressReporter(),
            NullUIAdapter(),
            comparison_service=mock_comparison
        )

        # Create test files with known sizes
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video3 = tmp_path / "video3.mp4"

        video1.write_bytes(b"0" * (2 * 1024 * 1024))  # 2 MB (representative)
        video2.write_bytes(b"0" * (1 * 1024 * 1024))  # 1 MB (duplicate)
        video3.write_bytes(b"0" * (1 * 1024 * 1024))  # 1 MB (duplicate)

        from duplicateflow.core.models import DuplicateGroup

        groups = [
            DuplicateGroup(
                videos=[video1, video2, video3],
                representative=video1,
                avg_similarity=85.0,
                total_size_mb=4.0
            )
        ]

        space = service._calculate_reclaimable_space(groups)

        # Should be 2 MB (video2 + video3)
        assert space == pytest.approx(2.0, abs=0.1)

    def test_calculate_reclaimable_space_multiple_groups(self, tmp_path):
        """Test calculating reclaimable space across multiple groups."""
        service = DuplicateFinderService(
            NullProgressReporter(),
            NullUIAdapter()
        )

        # Group 1
        v1 = tmp_path / "v1.mp4"
        v2 = tmp_path / "v2.mp4"
        v1.write_bytes(b"0" * (3 * 1024 * 1024))  # 3 MB (representative)
        v2.write_bytes(b"0" * (2 * 1024 * 1024))  # 2 MB (duplicate)

        # Group 2
        v3 = tmp_path / "v3.mp4"
        v4 = tmp_path / "v4.mp4"
        v3.write_bytes(b"0" * (1 * 1024 * 1024))  # 1 MB (representative)
        v4.write_bytes(b"0" * (1 * 1024 * 1024))  # 1 MB (duplicate)

        from duplicateflow.core.models import DuplicateGroup

        groups = [
            DuplicateGroup(
                videos=[v1, v2],
                representative=v1,
                avg_similarity=85.0,
                total_size_mb=5.0
            ),
            DuplicateGroup(
                videos=[v3, v4],
                representative=v3,
                avg_similarity=90.0,
                total_size_mb=2.0
            )
        ]

        space = service._calculate_reclaimable_space(groups)

        # Should be 3 MB (v2 + v4)
        assert space == pytest.approx(3.0, abs=0.1)


class TestDuplicateFinderServiceIntegration:
    """Integration-style tests."""

    def test_full_detection_workflow(self, tmp_path):
        """Test complete duplicate detection workflow."""
        ui = NullUIAdapter()
        progress = NullProgressReporter()

        # Setup mock comparison service
        mock_comparison = Mock(spec=ComparisonService)
        mock_comparison._get_pipeline_name.return_value = "balanced"

        def mock_compare(v1, v2, threshold):
            result = Mock(spec=ComparisonResult)
            result.video1_path = v1
            result.video2_path = v2

            # v1=v2, v3=v4, v5 is unique
            pairs = [
                (tmp_path / "v1.mp4", tmp_path / "v2.mp4"),
                (tmp_path / "v2.mp4", tmp_path / "v1.mp4"),
                (tmp_path / "v3.mp4", tmp_path / "v4.mp4"),
                (tmp_path / "v4.mp4", tmp_path / "v3.mp4"),
            ]

            if (v1, v2) in pairs or (v2, v1) in pairs:
                result.is_duplicate = True
                result.similarity_score = 85.0
            else:
                result.is_duplicate = False
                result.similarity_score = 50.0

            return result

        mock_comparison.compare_videos.side_effect = mock_compare

        service = DuplicateFinderService(progress, ui, mock_comparison)

        # Create 5 videos: v1=v2, v3=v4, v5 unique
        videos = [tmp_path / f"v{i}.mp4" for i in range(1, 6)]
        for v in videos:
            v.write_bytes(b"0" * 1024 * 1024)  # 1 MB each

        # Execute detection
        result = service.find_duplicates(videos, threshold=70.0)

        # Verify result
        assert result.total_videos_scanned == 5
        assert len(result.duplicate_groups) == 2  # 2 groups
        assert result.duplicates_found == 2  # 2 duplicates total
        assert result.execution_time_seconds > 0
        assert result.timestamp is not None

        # Verify UI messages
        assert len(ui.messages) > 0
