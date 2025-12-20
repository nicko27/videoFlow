"""
Unit tests for ComparisonResult model.
"""
import json
import pytest
from datetime import datetime
from pathlib import Path

from duplicateflow.core.models.comparison import ComparisonResult
from duplicateflow.core.models.algorithm_result import AlgorithmResult


class TestComparisonResult:
    """Tests for ComparisonResult model."""

    @pytest.fixture
    def sample_algorithm_results(self):
        """Create sample algorithm results for testing."""
        return [
            AlgorithmResult(
                algorithm_name="frame_hash",
                similarity=85.0,
                accepted=True,
                weight=0.4,
                execution_time_ms=100.0,
                metadata={}
            ),
            AlgorithmResult(
                algorithm_name="color_histogram",
                similarity=90.0,
                accepted=True,
                weight=0.3,
                execution_time_ms=80.0,
                metadata={}
            ),
            AlgorithmResult(
                algorithm_name="ssim",
                similarity=75.0,
                accepted=False,
                weight=0.3,
                execution_time_ms=120.0,
                metadata={}
            ),
        ]

    @pytest.fixture
    def sample_comparison_result(self, sample_algorithm_results):
        """Create sample ComparisonResult for testing."""
        return ComparisonResult(
            video1_path=Path("/videos/movie1.mp4"),
            video2_path=Path("/videos/movie2.mp4"),
            similarity_score=85.5,
            is_duplicate=True,
            algorithm_results=sample_algorithm_results,
            pipeline_name="balanced",
            execution_time_ms=2500.0,
            timestamp=datetime(2025, 12, 20, 12, 0, 0),
            metadata={"early_exit": False}
        )

    def test_comparison_result_creation(self, sample_comparison_result):
        """Test creating ComparisonResult instance."""
        result = sample_comparison_result

        assert result.video1_path == Path("/videos/movie1.mp4")
        assert result.video2_path == Path("/videos/movie2.mp4")
        assert result.similarity_score == 85.5
        assert result.is_duplicate is True
        assert len(result.algorithm_results) == 3
        assert result.pipeline_name == "balanced"
        assert result.execution_time_ms == 2500.0

    def test_comparison_result_immutable(self, sample_comparison_result):
        """Test that ComparisonResult is immutable (frozen)."""
        with pytest.raises(AttributeError):
            sample_comparison_result.similarity_score = 90.0

    def test_to_dict(self, sample_comparison_result):
        """Test converting ComparisonResult to dictionary."""
        data = sample_comparison_result.to_dict()

        assert data["video1_path"] == "/videos/movie1.mp4"
        assert data["video2_path"] == "/videos/movie2.mp4"
        assert data["video1_name"] == "movie1.mp4"
        assert data["video2_name"] == "movie2.mp4"
        assert data["similarity_score"] == 85.5
        assert data["is_duplicate"] is True
        assert data["pipeline_name"] == "balanced"
        assert data["execution_time_ms"] == 2500.0
        assert data["execution_time_seconds"] == 2.5
        assert len(data["algorithm_results"]) == 3
        assert "statistics" in data

    def test_to_json(self, sample_comparison_result):
        """Test converting ComparisonResult to JSON string."""
        json_str = sample_comparison_result.to_json(indent=2)

        # Parse back to verify
        data = json.loads(json_str)
        assert data["similarity_score"] == 85.5
        assert data["is_duplicate"] is True
        assert len(data["algorithm_results"]) == 3

    def test_to_json_default_indent(self, sample_comparison_result):
        """Test to_json with default indentation."""
        json_str = sample_comparison_result.to_json()
        assert isinstance(json_str, str)
        assert "similarity_score" in json_str

    def test_get_best_algorithm(self, sample_comparison_result):
        """Test getting algorithm with highest similarity."""
        best = sample_comparison_result.get_best_algorithm()

        assert best.algorithm_name == "color_histogram"
        assert best.similarity == 90.0

    def test_get_best_algorithm_empty_results(self):
        """Test get_best_algorithm with no algorithm results."""
        result = ComparisonResult(
            video1_path=Path("/v1.mp4"),
            video2_path=Path("/v2.mp4"),
            similarity_score=0.0,
            is_duplicate=False,
            algorithm_results=[],
            pipeline_name="test",
            execution_time_ms=100.0,
            timestamp=datetime.now(),
            metadata={}
        )

        with pytest.raises(ValueError, match="No algorithm results available"):
            result.get_best_algorithm()

    def test_get_execution_summary(self, sample_comparison_result):
        """Test getting execution summary statistics."""
        summary = sample_comparison_result.get_execution_summary()

        assert summary["algorithms_used"] == 3
        assert summary["algorithms_accepted"] == 2  # frame_hash and color_histogram
        assert summary["avg_similarity"] == 83.33  # (85 + 90 + 75) / 3
        assert summary["total_execution_time_ms"] == 2500.0
        assert summary["avg_time_per_algorithm_ms"] == 833.33  # 2500 / 3

    def test_get_execution_summary_empty(self):
        """Test execution summary with no algorithm results."""
        result = ComparisonResult(
            video1_path=Path("/v1.mp4"),
            video2_path=Path("/v2.mp4"),
            similarity_score=100.0,
            is_duplicate=True,
            algorithm_results=[],
            pipeline_name="test",
            execution_time_ms=50.0,
            timestamp=datetime.now(),
            metadata={"early_exit": True, "reason": "identical_files"}
        )

        summary = result.get_execution_summary()

        assert summary["algorithms_used"] == 0
        assert summary["algorithms_accepted"] == 0
        assert summary["avg_similarity"] == 0.0
        assert summary["total_execution_time_ms"] == 50.0

    def test_timestamp_serialization(self, sample_comparison_result):
        """Test that timestamp is properly serialized to ISO format."""
        data = sample_comparison_result.to_dict()

        assert data["timestamp"] == "2025-12-20T12:00:00"
        assert isinstance(data["timestamp"], str)

    def test_paths_serialization(self):
        """Test that Path objects are serialized to strings."""
        result = ComparisonResult(
            video1_path=Path("/home/user/videos/test.mp4"),
            video2_path=Path("/home/user/videos/test2.mkv"),
            similarity_score=75.0,
            is_duplicate=True,
            algorithm_results=[],
            pipeline_name="fast",
            execution_time_ms=1000.0,
            timestamp=datetime.now(),
            metadata={}
        )

        data = result.to_dict()

        assert data["video1_path"] == "/home/user/videos/test.mp4"
        assert data["video2_path"] == "/home/user/videos/test2.mkv"
        assert data["video1_name"] == "test.mp4"
        assert data["video2_name"] == "test2.mkv"

    def test_metadata_preserved(self, sample_comparison_result):
        """Test that metadata is preserved in serialization."""
        data = sample_comparison_result.to_dict()

        assert data["metadata"] == {"early_exit": False}

    def test_algorithm_results_serialization(self, sample_comparison_result):
        """Test that algorithm results are properly serialized."""
        data = sample_comparison_result.to_dict()

        algo_results = data["algorithm_results"]
        assert len(algo_results) == 3
        assert algo_results[0]["algorithm_name"] == "frame_hash"
        assert algo_results[1]["algorithm_name"] == "color_histogram"
        assert algo_results[2]["algorithm_name"] == "ssim"
