"""
Unit tests for benchmark models.
"""
import pytest
from datetime import datetime
from pathlib import Path

from duplicateflow.core.models.benchmark import (
    AlgorithmBenchmark,
    PipelineBenchmark,
    ComparisonBenchmark,
    AccuracyMetrics,
    TestSetBenchmark,
)


class TestAlgorithmBenchmark:
    """Tests for AlgorithmBenchmark model."""

    def test_algorithm_benchmark_creation(self):
        """Test creating AlgorithmBenchmark instance."""
        benchmark = AlgorithmBenchmark(
            algorithm_name="frame_hash",
            execution_time_ms=150.5,
            similarity=88.5,
            memory_usage_mb=45.2,
            frames_processed=100,
            cache_hit_rate=75.0
        )

        assert benchmark.algorithm_name == "frame_hash"
        assert benchmark.execution_time_ms == 150.5
        assert benchmark.similarity == 88.5
        assert benchmark.memory_usage_mb == 45.2
        assert benchmark.frames_processed == 100
        assert benchmark.cache_hit_rate == 75.0

    def test_algorithm_benchmark_immutable(self):
        """Test that AlgorithmBenchmark is immutable (frozen)."""
        benchmark = AlgorithmBenchmark(
            algorithm_name="ssim",
            execution_time_ms=200.0,
            similarity=90.0,
            memory_usage_mb=50.0,
            frames_processed=120,
            cache_hit_rate=80.0
        )

        with pytest.raises(AttributeError):
            benchmark.similarity = 95.0

    def test_to_dict(self):
        """Test converting AlgorithmBenchmark to dictionary."""
        benchmark = AlgorithmBenchmark(
            algorithm_name="color_histogram",
            execution_time_ms=125.678,
            similarity=75.123,
            memory_usage_mb=30.456,
            frames_processed=80,
            cache_hit_rate=65.789
        )

        data = benchmark.to_dict()

        assert data["algorithm_name"] == "color_histogram"
        assert data["execution_time_ms"] == 125.68  # Rounded to 2 decimals
        assert data["execution_time_seconds"] == 0.13  # 125.678 / 1000
        assert data["similarity"] == 75.12  # Rounded
        assert data["memory_usage_mb"] == 30.46  # Rounded
        assert data["frames_processed"] == 80
        assert data["cache_hit_rate"] == 65.79  # Rounded


class TestPipelineBenchmark:
    """Tests for PipelineBenchmark model."""

    @pytest.fixture
    def sample_algorithm_benchmarks(self):
        """Create sample algorithm benchmarks."""
        return [
            AlgorithmBenchmark(
                algorithm_name="frame_hash",
                execution_time_ms=150.0,
                similarity=85.0,
                memory_usage_mb=40.0,
                frames_processed=100,
                cache_hit_rate=70.0
            ),
            AlgorithmBenchmark(
                algorithm_name="optical_flow",
                execution_time_ms=300.0,
                similarity=90.0,
                memory_usage_mb=60.0,
                frames_processed=100,
                cache_hit_rate=75.0
            ),
            AlgorithmBenchmark(
                algorithm_name="color_histogram",
                execution_time_ms=100.0,
                similarity=80.0,
                memory_usage_mb=30.0,
                frames_processed=100,
                cache_hit_rate=80.0
            ),
        ]

    @pytest.fixture
    def sample_pipeline_benchmark(self, sample_algorithm_benchmarks):
        """Create sample PipelineBenchmark."""
        return PipelineBenchmark(
            pipeline_name="balanced",
            total_time_ms=2500.0,
            algorithm_benchmarks=sample_algorithm_benchmarks,
            similarity_score=88.5,
            is_duplicate=True,
            memory_peak_mb=128.5,
            cache_statistics={'hits': 10, 'misses': 2},
            timestamp=datetime(2025, 12, 20, 12, 0, 0)
        )

    def test_pipeline_benchmark_creation(self, sample_pipeline_benchmark):
        """Test creating PipelineBenchmark instance."""
        benchmark = sample_pipeline_benchmark

        assert benchmark.pipeline_name == "balanced"
        assert benchmark.total_time_ms == 2500.0
        assert len(benchmark.algorithm_benchmarks) == 3
        assert benchmark.similarity_score == 88.5
        assert benchmark.is_duplicate is True
        assert benchmark.memory_peak_mb == 128.5

    def test_pipeline_benchmark_immutable(self, sample_pipeline_benchmark):
        """Test that PipelineBenchmark is immutable (frozen)."""
        with pytest.raises(AttributeError):
            sample_pipeline_benchmark.similarity_score = 95.0

    def test_to_dict(self, sample_pipeline_benchmark):
        """Test converting PipelineBenchmark to dictionary."""
        data = sample_pipeline_benchmark.to_dict()

        assert data["pipeline_name"] == "balanced"
        assert data["total_time_ms"] == 2500.0
        assert data["total_time_seconds"] == 2.5
        assert data["algorithm_count"] == 3
        assert data["similarity_score"] == 88.5
        assert data["is_duplicate"] is True
        assert data["memory_peak_mb"] == 128.5
        assert data["timestamp"] == "2025-12-20T12:00:00"
        assert len(data["algorithm_benchmarks"]) == 3

    def test_get_slowest_algorithm(self, sample_pipeline_benchmark):
        """Test getting slowest algorithm."""
        slowest = sample_pipeline_benchmark.get_slowest_algorithm()

        assert slowest is not None
        assert slowest.algorithm_name == "optical_flow"
        assert slowest.execution_time_ms == 300.0

    def test_get_fastest_algorithm(self, sample_pipeline_benchmark):
        """Test getting fastest algorithm."""
        fastest = sample_pipeline_benchmark.get_fastest_algorithm()

        assert fastest is not None
        assert fastest.algorithm_name == "color_histogram"
        assert fastest.execution_time_ms == 100.0

    def test_get_slowest_algorithm_empty(self):
        """Test get_slowest_algorithm with no algorithms."""
        benchmark = PipelineBenchmark(
            pipeline_name="empty",
            total_time_ms=0.0,
            algorithm_benchmarks=[],
            similarity_score=0.0,
            is_duplicate=False,
            memory_peak_mb=0.0,
            cache_statistics={},
            timestamp=datetime.now()
        )

        assert benchmark.get_slowest_algorithm() is None
        assert benchmark.get_fastest_algorithm() is None

    def test_get_time_breakdown(self, sample_pipeline_benchmark):
        """Test getting time breakdown by algorithm."""
        breakdown = sample_pipeline_benchmark.get_time_breakdown()

        assert len(breakdown) == 3
        assert breakdown["frame_hash"] == 150.0
        assert breakdown["optical_flow"] == 300.0
        assert breakdown["color_histogram"] == 100.0


class TestComparisonBenchmark:
    """Tests for ComparisonBenchmark model."""

    @pytest.fixture
    def sample_pipeline_benchmarks(self):
        """Create sample pipeline benchmarks."""
        return [
            PipelineBenchmark(
                pipeline_name="fast",
                total_time_ms=1000.0,
                algorithm_benchmarks=[],
                similarity_score=82.0,
                is_duplicate=True,
                memory_peak_mb=80.0,
                cache_statistics={},
                timestamp=datetime.now()
            ),
            PipelineBenchmark(
                pipeline_name="balanced",
                total_time_ms=2500.0,
                algorithm_benchmarks=[],
                similarity_score=88.5,
                is_duplicate=True,
                memory_peak_mb=128.0,
                cache_statistics={},
                timestamp=datetime.now()
            ),
            PipelineBenchmark(
                pipeline_name="thorough",
                total_time_ms=5000.0,
                algorithm_benchmarks=[],
                similarity_score=92.0,
                is_duplicate=True,
                memory_peak_mb=200.0,
                cache_statistics={},
                timestamp=datetime.now()
            ),
        ]

    @pytest.fixture
    def sample_comparison_benchmark(self, sample_pipeline_benchmarks):
        """Create sample ComparisonBenchmark."""
        return ComparisonBenchmark(
            video1_path=Path("/videos/movie1.mp4"),
            video2_path=Path("/videos/movie2.mp4"),
            pipeline_benchmarks=sample_pipeline_benchmarks,
            ground_truth=True,
            timestamp=datetime(2025, 12, 20, 12, 0, 0)
        )

    def test_comparison_benchmark_creation(self, sample_comparison_benchmark):
        """Test creating ComparisonBenchmark instance."""
        benchmark = sample_comparison_benchmark

        assert benchmark.video1_path == Path("/videos/movie1.mp4")
        assert benchmark.video2_path == Path("/videos/movie2.mp4")
        assert len(benchmark.pipeline_benchmarks) == 3
        assert benchmark.ground_truth is True

    def test_comparison_benchmark_immutable(self, sample_comparison_benchmark):
        """Test that ComparisonBenchmark is immutable (frozen)."""
        with pytest.raises(AttributeError):
            sample_comparison_benchmark.ground_truth = False

    def test_to_dict(self, sample_comparison_benchmark):
        """Test converting ComparisonBenchmark to dictionary."""
        data = sample_comparison_benchmark.to_dict()

        assert data["video1_path"] == "/videos/movie1.mp4"
        assert data["video1_name"] == "movie1.mp4"
        assert data["video2_path"] == "/videos/movie2.mp4"
        assert data["video2_name"] == "movie2.mp4"
        assert data["pipeline_count"] == 3
        assert data["ground_truth"] is True
        assert data["timestamp"] == "2025-12-20T12:00:00"
        assert len(data["pipeline_benchmarks"]) == 3

    def test_get_fastest_pipeline(self, sample_comparison_benchmark):
        """Test getting fastest pipeline."""
        fastest = sample_comparison_benchmark.get_fastest_pipeline()

        assert fastest is not None
        assert fastest.pipeline_name == "fast"
        assert fastest.total_time_ms == 1000.0

    def test_get_most_accurate_pipeline(self, sample_comparison_benchmark):
        """Test getting most accurate pipeline."""
        accurate = sample_comparison_benchmark.get_most_accurate_pipeline()

        assert accurate is not None
        assert accurate.pipeline_name == "thorough"
        assert accurate.similarity_score == 92.0

    def test_get_most_accurate_pipeline_no_ground_truth(self, sample_pipeline_benchmarks):
        """Test get_most_accurate_pipeline with no ground truth."""
        benchmark = ComparisonBenchmark(
            video1_path=Path("/v1.mp4"),
            video2_path=Path("/v2.mp4"),
            pipeline_benchmarks=sample_pipeline_benchmarks,
            ground_truth=None,
            timestamp=datetime.now()
        )

        assert benchmark.get_most_accurate_pipeline() is None

    def test_rank_by_speed(self, sample_comparison_benchmark):
        """Test ranking pipelines by speed."""
        rankings = sample_comparison_benchmark.rank_by_speed()

        assert len(rankings) == 3
        assert rankings[0] == ("fast", 1000.0)
        assert rankings[1] == ("balanced", 2500.0)
        assert rankings[2] == ("thorough", 5000.0)

    def test_rank_by_accuracy(self, sample_comparison_benchmark):
        """Test ranking pipelines by accuracy."""
        rankings = sample_comparison_benchmark.rank_by_accuracy()

        assert len(rankings) == 3
        assert rankings[0] == ("thorough", 92.0)
        assert rankings[1] == ("balanced", 88.5)
        assert rankings[2] == ("fast", 82.0)


class TestAccuracyMetrics:
    """Tests for AccuracyMetrics model."""

    def test_accuracy_metrics_creation(self):
        """Test creating AccuracyMetrics instance."""
        metrics = AccuracyMetrics(
            true_positives=45,
            false_positives=5,
            true_negatives=40,
            false_negatives=10
        )

        assert metrics.true_positives == 45
        assert metrics.false_positives == 5
        assert metrics.true_negatives == 40
        assert metrics.false_negatives == 10

    def test_accuracy_metrics_immutable(self):
        """Test that AccuracyMetrics is immutable (frozen)."""
        metrics = AccuracyMetrics(
            true_positives=50,
            false_positives=0,
            true_negatives=50,
            false_negatives=0
        )

        with pytest.raises(AttributeError):
            metrics.true_positives = 100

    def test_accuracy_property(self):
        """Test accuracy calculation."""
        metrics = AccuracyMetrics(
            true_positives=45,
            false_positives=5,
            true_negatives=40,
            false_negatives=10
        )

        # Accuracy = (TP + TN) / Total = (45 + 40) / 100 = 0.85
        assert metrics.accuracy == 0.85

    def test_precision_property(self):
        """Test precision calculation."""
        metrics = AccuracyMetrics(
            true_positives=45,
            false_positives=5,
            true_negatives=40,
            false_negatives=10
        )

        # Precision = TP / (TP + FP) = 45 / (45 + 5) = 0.9
        assert metrics.precision == 0.9

    def test_recall_property(self):
        """Test recall calculation."""
        metrics = AccuracyMetrics(
            true_positives=45,
            false_positives=5,
            true_negatives=40,
            false_negatives=10
        )

        # Recall = TP / (TP + FN) = 45 / (45 + 10) ≈ 0.818
        assert abs(metrics.recall - 0.8181818181818182) < 0.0001

    def test_f1_score_property(self):
        """Test F1 score calculation."""
        metrics = AccuracyMetrics(
            true_positives=45,
            false_positives=5,
            true_negatives=40,
            false_negatives=10
        )

        # F1 = 2 * (precision * recall) / (precision + recall)
        precision = 0.9
        recall = 45 / 55  # 0.8181...
        expected_f1 = 2 * (precision * recall) / (precision + recall)

        assert abs(metrics.f1_score - expected_f1) < 0.0001

    def test_specificity_property(self):
        """Test specificity calculation."""
        metrics = AccuracyMetrics(
            true_positives=45,
            false_positives=5,
            true_negatives=40,
            false_negatives=10
        )

        # Specificity = TN / (TN + FP) = 40 / (40 + 5) ≈ 0.888
        assert abs(metrics.specificity - 0.8888888888888888) < 0.0001

    def test_accuracy_metrics_zero_division(self):
        """Test metrics with zero denominator edge cases."""
        metrics = AccuracyMetrics(
            true_positives=0,
            false_positives=0,
            true_negatives=0,
            false_negatives=0
        )

        # All metrics should be 0.0 when there's no data
        assert metrics.accuracy == 0.0
        assert metrics.precision == 0.0
        assert metrics.recall == 0.0
        assert metrics.f1_score == 0.0
        assert metrics.specificity == 0.0

    def test_to_dict(self):
        """Test converting AccuracyMetrics to dictionary."""
        metrics = AccuracyMetrics(
            true_positives=45,
            false_positives=5,
            true_negatives=40,
            false_negatives=10
        )

        data = metrics.to_dict()

        assert data["confusion_matrix"]["true_positives"] == 45
        assert data["confusion_matrix"]["false_positives"] == 5
        assert data["confusion_matrix"]["true_negatives"] == 40
        assert data["confusion_matrix"]["false_negatives"] == 10
        assert data["accuracy"] == 0.85
        assert data["precision"] == 0.9
        assert "recall" in data
        assert "f1_score" in data
        assert "specificity" in data


class TestTestSetBenchmark:
    """Tests for TestSetBenchmark model."""

    @pytest.fixture
    def sample_accuracy_metrics(self):
        """Create sample accuracy metrics."""
        return AccuracyMetrics(
            true_positives=45,
            false_positives=5,
            true_negatives=40,
            false_negatives=10
        )

    @pytest.fixture
    def sample_testset_benchmark(self, sample_accuracy_metrics):
        """Create sample TestSetBenchmark."""
        return TestSetBenchmark(
            pipeline_name="balanced",
            test_set_name="test_v1",
            total_comparisons=100,
            accuracy_metrics=sample_accuracy_metrics,
            avg_execution_time_ms=2500.0,
            total_time_seconds=250.0,
            comparison_benchmarks=[],
            timestamp=datetime(2025, 12, 20, 12, 0, 0)
        )

    def test_testset_benchmark_creation(self, sample_testset_benchmark):
        """Test creating TestSetBenchmark instance."""
        benchmark = sample_testset_benchmark

        assert benchmark.pipeline_name == "balanced"
        assert benchmark.test_set_name == "test_v1"
        assert benchmark.total_comparisons == 100
        assert benchmark.avg_execution_time_ms == 2500.0
        assert benchmark.total_time_seconds == 250.0

    def test_testset_benchmark_immutable(self, sample_testset_benchmark):
        """Test that TestSetBenchmark is immutable (frozen)."""
        with pytest.raises(AttributeError):
            sample_testset_benchmark.total_comparisons = 200

    def test_to_dict(self, sample_testset_benchmark):
        """Test converting TestSetBenchmark to dictionary."""
        data = sample_testset_benchmark.to_dict()

        assert data["pipeline_name"] == "balanced"
        assert data["test_set_name"] == "test_v1"
        assert data["total_comparisons"] == 100
        assert data["avg_execution_time_ms"] == 2500.0
        assert data["avg_execution_time_seconds"] == 2.5
        assert data["total_time_seconds"] == 250.0
        assert data["total_time_minutes"] == 4.17  # 250 / 60
        assert data["comparisons_per_second"] == 0.4  # 100 / 250
        assert data["timestamp"] == "2025-12-20T12:00:00"
        assert "accuracy_metrics" in data

    def test_to_json(self, sample_testset_benchmark):
        """Test converting TestSetBenchmark to JSON."""
        json_str = sample_testset_benchmark.to_json(indent=2)

        assert isinstance(json_str, str)
        assert "pipeline_name" in json_str
        assert "test_set_name" in json_str
        assert "balanced" in json_str

    def test_to_csv_rows_empty(self, sample_accuracy_metrics):
        """Test to_csv_rows with no comparison benchmarks."""
        benchmark = TestSetBenchmark(
            pipeline_name="fast",
            test_set_name="test_v2",
            total_comparisons=0,
            accuracy_metrics=sample_accuracy_metrics,
            avg_execution_time_ms=0.0,
            total_time_seconds=0.0,
            comparison_benchmarks=[],
            timestamp=datetime.now()
        )

        rows = benchmark.to_csv_rows()
        assert rows == []

    def test_generate_confusion_matrix(self, sample_testset_benchmark):
        """Test generating confusion matrix."""
        matrix = sample_testset_benchmark.generate_confusion_matrix()

        assert len(matrix) == 2
        assert len(matrix[0]) == 2
        assert matrix[0][0] == 45  # TP
        assert matrix[0][1] == 10  # FN
        assert matrix[1][0] == 5   # FP
        assert matrix[1][1] == 40  # TN
