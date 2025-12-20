"""
Unit tests for ComparisonService.

Tests the video-to-video comparison service that orchestrates
pipeline algorithms to determine similarity scores.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock

from duplicateflow.core.services import ComparisonService
from duplicateflow.core.interfaces import NullProgressReporter, NullUIAdapter, MessageType


class TestComparisonServiceInstantiation:
    """Test service instantiation and dependency injection."""

    def test_init_with_defaults(self):
        """Test initialization with default pipeline."""
        service = ComparisonService(
            NullProgressReporter(),
            NullUIAdapter()
        )
        assert service.progress is not None
        assert service.ui is not None
        assert service.pipeline is not None  # Default pipeline created

    def test_init_with_custom_pipeline(self):
        """Test initialization with custom pipeline."""
        mock_pipeline = Mock()
        service = ComparisonService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipeline=mock_pipeline
        )
        assert service.pipeline == mock_pipeline

    def test_dependency_injection(self):
        """Test that progress and ui adapters are properly injected."""
        progress = NullProgressReporter()
        ui = NullUIAdapter()

        service = ComparisonService(progress, ui)

        assert service.progress is progress
        assert service.ui is ui


class TestComparisonServiceCompareVideos:
    """Test compare_videos method."""

    @pytest.fixture
    def service_with_mock_pipeline(self):
        """Service with mocked pipeline for testing."""
        mock_pipeline = Mock()
        mock_pipeline.compare.return_value = {
            'global_score': 85.5,
            'individual_results': [
                {
                    'algorithm': 'frame_hash',
                    'similarity': 90.0,
                    'accepted': True,
                    'weight': 0.5,
                    'metadata': {}
                },
                {
                    'algorithm': 'ssim',
                    'similarity': 81.0,
                    'accepted': True,
                    'weight': 0.5,
                    'metadata': {}
                }
            ],
            'metadata': {
                'total_time_ms': 150.0
            }
        }

        return ComparisonService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipeline=mock_pipeline
        )

    def test_compare_videos_success(self, service_with_mock_pipeline, tmp_path):
        """Test successful video comparison."""
        # Create dummy video files
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        result = service_with_mock_pipeline.compare_videos(video1, video2, threshold=70.0)

        # Verify result structure
        assert result.video1_path == video1
        assert result.video2_path == video2
        assert result.similarity_score == 85.5
        assert result.is_duplicate is True
        assert result.pipeline_name is not None
        assert len(result.algorithm_results) == 2
        assert result.execution_time_ms > 0

    def test_compare_videos_below_threshold(self, service_with_mock_pipeline, tmp_path):
        """Test comparison where similarity is below threshold."""
        # Mock pipeline to return low score
        service_with_mock_pipeline.pipeline.compare.return_value = {
            'global_score': 50.0,
            'individual_results': [],
            'metadata': {}
        }

        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        result = service_with_mock_pipeline.compare_videos(video1, video2, threshold=70.0)

        assert result.similarity_score == 50.0
        assert result.is_duplicate is False

    def test_compare_videos_at_threshold(self, service_with_mock_pipeline, tmp_path):
        """Test comparison where similarity equals threshold."""
        # Mock pipeline to return score at threshold
        service_with_mock_pipeline.pipeline.compare.return_value = {
            'global_score': 70.0,
            'individual_results': [],
            'metadata': {}
        }

        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        result = service_with_mock_pipeline.compare_videos(video1, video2, threshold=70.0)

        assert result.similarity_score == 70.0
        assert result.is_duplicate is True  # >= threshold

    def test_compare_videos_ui_messages(self, tmp_path):
        """Test UI messages are sent during comparison."""
        ui = NullUIAdapter()
        mock_pipeline = Mock()
        mock_pipeline.compare.return_value = {
            'global_score': 80.0,
            'individual_results': [],
            'metadata': {}
        }

        service = ComparisonService(NullProgressReporter(), ui, mock_pipeline)

        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        service.compare_videos(video1, video2)

        # Verify messages were sent
        assert len(ui.messages) > 0
        messages_text = [m['message'] for m in ui.messages]
        assert any("Comparing" in msg for msg in messages_text)
        assert any("complete" in msg for msg in messages_text)

    def test_compare_videos_nonexistent_video1(self, service_with_mock_pipeline, tmp_path):
        """Test comparing with non-existent first video."""
        video1 = tmp_path / "nonexistent1.mp4"  # Doesn't exist
        video2 = tmp_path / "video2.mp4"
        video2.touch()

        with pytest.raises(FileNotFoundError, match="Video 1 not found"):
            service_with_mock_pipeline.compare_videos(video1, video2)

    def test_compare_videos_nonexistent_video2(self, service_with_mock_pipeline, tmp_path):
        """Test comparing with non-existent second video."""
        video1 = tmp_path / "video1.mp4"
        video1.touch()
        video2 = tmp_path / "nonexistent2.mp4"  # Doesn't exist

        with pytest.raises(FileNotFoundError, match="Video 2 not found"):
            service_with_mock_pipeline.compare_videos(video1, video2)

    def test_compare_videos_invalid_threshold_low(self, service_with_mock_pipeline, tmp_path):
        """Test comparison with threshold below 0."""
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        with pytest.raises(ValueError, match="Threshold must be between 0 and 100"):
            service_with_mock_pipeline.compare_videos(video1, video2, threshold=-5.0)

    def test_compare_videos_invalid_threshold_high(self, service_with_mock_pipeline, tmp_path):
        """Test comparison with threshold above 100."""
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        with pytest.raises(ValueError, match="Threshold must be between 0 and 100"):
            service_with_mock_pipeline.compare_videos(video1, video2, threshold=150.0)

    def test_compare_videos_pipeline_exception(self, tmp_path):
        """Test handling when pipeline.compare() raises exception."""
        mock_pipeline = Mock()
        mock_pipeline.compare.side_effect = RuntimeError("Pipeline error")

        service = ComparisonService(
            NullProgressReporter(),
            NullUIAdapter(),
            mock_pipeline
        )

        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        # Verify exception is propagated
        with pytest.raises(RuntimeError, match="Pipeline error"):
            service.compare_videos(video1, video2)


class TestComparisonServiceAlgorithmResults:
    """Test algorithm result conversion."""

    def test_convert_algorithm_results_single(self):
        """Test converting single algorithm result."""
        mock_pipeline = Mock()
        service = ComparisonService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipeline=mock_pipeline
        )

        pipeline_results = [
            {
                'algorithm': 'frame_hash',
                'similarity': 85.0,
                'accepted': True,
                'weight': 1.0,
                'metadata': {'test': 'data'}
            }
        ]

        results = service._convert_algorithm_results(pipeline_results)

        assert len(results) == 1
        assert results[0].algorithm_name == 'frame_hash'
        assert results[0].similarity == 85.0
        assert results[0].accepted is True
        assert results[0].weight == 1.0
        assert results[0].metadata == {'test': 'data'}

    def test_convert_algorithm_results_multiple(self):
        """Test converting multiple algorithm results."""
        mock_pipeline = Mock()
        service = ComparisonService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipeline=mock_pipeline
        )

        pipeline_results = [
            {
                'algorithm': 'frame_hash',
                'similarity': 90.0,
                'accepted': True,
                'weight': 0.5,
                'metadata': {}
            },
            {
                'algorithm': 'ssim',
                'similarity': 80.0,
                'accepted': True,
                'weight': 0.5,
                'metadata': {}
            }
        ]

        results = service._convert_algorithm_results(pipeline_results)

        assert len(results) == 2
        assert results[0].algorithm_name == 'frame_hash'
        assert results[1].algorithm_name == 'ssim'

    def test_convert_algorithm_results_empty(self):
        """Test converting empty algorithm results."""
        mock_pipeline = Mock()
        service = ComparisonService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipeline=mock_pipeline
        )

        results = service._convert_algorithm_results([])

        assert len(results) == 0


class TestComparisonServiceHelpers:
    """Test helper methods."""

    def test_get_pipeline_name(self):
        """Test getting pipeline name."""
        mock_pipeline = Mock()
        service = ComparisonService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipeline=mock_pipeline
        )

        name = service._get_pipeline_name()

        # Should return some string (currently returns "custom")
        assert isinstance(name, str)
        assert len(name) > 0


class TestComparisonServiceIntegration:
    """Integration-style tests with realistic scenarios."""

    def test_full_comparison_workflow(self, tmp_path):
        """Test complete comparison workflow."""
        # Setup
        ui = NullUIAdapter()
        progress = NullProgressReporter()

        mock_pipeline = Mock()
        mock_pipeline.compare.return_value = {
            'global_score': 92.5,
            'individual_results': [
                {
                    'algorithm': 'frame_hash',
                    'similarity': 95.0,
                    'accepted': True,
                    'weight': 0.6,
                    'metadata': {}
                },
                {
                    'algorithm': 'ssim',
                    'similarity': 88.5,
                    'accepted': True,
                    'weight': 0.4,
                    'metadata': {}
                }
            ],
            'metadata': {'total_time_ms': 200.0}
        }

        service = ComparisonService(progress, ui, mock_pipeline)

        # Create videos
        video1 = tmp_path / "movie1.mp4"
        video2 = tmp_path / "movie2.mp4"
        video1.touch()
        video2.touch()

        # Execute comparison
        result = service.compare_videos(video1, video2, threshold=75.0)

        # Verify complete result
        assert result.similarity_score == 92.5
        assert result.is_duplicate is True
        assert len(result.algorithm_results) == 2
        assert result.timestamp is not None
        assert result.execution_time_ms > 0

        # Verify UI messages were sent
        assert len(ui.messages) >= 2  # At least start and complete messages

        # Verify pipeline was called correctly
        mock_pipeline.compare.assert_called_once()
        call_args = mock_pipeline.compare.call_args
        assert str(video1) in str(call_args)
        assert str(video2) in str(call_args)

    def test_comparison_with_different_thresholds(self, tmp_path):
        """Test same comparison with different thresholds."""
        mock_pipeline = Mock()
        mock_pipeline.compare.return_value = {
            'global_score': 75.0,
            'individual_results': [],
            'metadata': {}
        }

        service = ComparisonService(
            NullProgressReporter(),
            NullUIAdapter(),
            mock_pipeline
        )

        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        # Test with low threshold - should be duplicate
        result1 = service.compare_videos(video1, video2, threshold=70.0)
        assert result1.is_duplicate is True

        # Test with high threshold - should not be duplicate
        result2 = service.compare_videos(video1, video2, threshold=80.0)
        assert result2.is_duplicate is False

        # Both should have same similarity score
        assert result1.similarity_score == result2.similarity_score
