"""
Unit tests for AlgorithmResult model.
"""
import pytest
from duplicateflow.core.models.algorithm_result import AlgorithmResult


class TestAlgorithmResult:
    """Tests for AlgorithmResult model."""

    def test_algorithm_result_creation(self):
        """Test creating AlgorithmResult instance."""
        result = AlgorithmResult(
            algorithm_name="frame_hash",
            similarity=85.5,
            accepted=True,
            weight=0.4,
            execution_time_ms=150.5,
            metadata={"frames_compared": 100}
        )

        assert result.algorithm_name == "frame_hash"
        assert result.similarity == 85.5
        assert result.accepted is True
        assert result.weight == 0.4
        assert result.execution_time_ms == 150.5
        assert result.metadata == {"frames_compared": 100}

    def test_algorithm_result_immutable(self):
        """Test that AlgorithmResult is immutable (frozen)."""
        result = AlgorithmResult(
            algorithm_name="ssim",
            similarity=90.0,
            accepted=True,
            weight=0.5,
            execution_time_ms=200.0,
            metadata={}
        )

        with pytest.raises(AttributeError):
            result.similarity = 95.0

    def test_to_dict(self):
        """Test converting AlgorithmResult to dictionary."""
        result = AlgorithmResult(
            algorithm_name="color_histogram",
            similarity=75.123,
            accepted=False,
            weight=0.333,
            execution_time_ms=125.678,
            metadata={"bins": 256}
        )

        data = result.to_dict()

        assert data["algorithm_name"] == "color_histogram"
        assert data["similarity"] == 75.12  # Rounded to 2 decimals
        assert data["accepted"] is False
        assert data["weight"] == 0.333  # Rounded to 3 decimals
        assert data["execution_time_ms"] == 125.68  # Rounded to 2 decimals
        assert data["metadata"] == {"bins": 256}

    def test_to_dict_rounding(self):
        """Test that to_dict rounds numbers correctly."""
        result = AlgorithmResult(
            algorithm_name="test",
            similarity=85.555555,
            accepted=True,
            weight=0.4444444,
            execution_time_ms=150.999999,
            metadata={}
        )

        data = result.to_dict()

        # Check rounding
        assert data["similarity"] == 85.56  # 2 decimals
        assert data["weight"] == 0.444  # 3 decimals
        assert data["execution_time_ms"] == 151.0  # 2 decimals

    def test_with_empty_metadata(self):
        """Test AlgorithmResult with empty metadata."""
        result = AlgorithmResult(
            algorithm_name="edge_pattern",
            similarity=80.0,
            accepted=True,
            weight=0.3,
            execution_time_ms=100.0,
            metadata={}
        )

        data = result.to_dict()
        assert data["metadata"] == {}

    def test_with_complex_metadata(self):
        """Test AlgorithmResult with complex metadata."""
        metadata = {
            "frames": 120,
            "skipped": 5,
            "settings": {
                "threshold": 80,
                "method": "pHash"
            }
        }

        result = AlgorithmResult(
            algorithm_name="frame_hash",
            similarity=88.0,
            accepted=True,
            weight=0.4,
            execution_time_ms=200.0,
            metadata=metadata
        )

        data = result.to_dict()
        assert data["metadata"] == metadata
