"""
Benchmark result models for performance and accuracy analysis.
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


@dataclass(frozen=True)
class AlgorithmBenchmark:
    """
    Performance metrics for a single algorithm execution.

    Attributes:
        algorithm_name: Name of the algorithm
        execution_time_ms: Execution time in milliseconds
        similarity: Similarity score (0-100)
        memory_usage_mb: Memory used in MB
        frames_processed: Number of frames analyzed
        cache_hit_rate: Percentage of cache hits (0-100)

    Example:
        >>> benchmark = AlgorithmBenchmark(
        ...     algorithm_name="frame_hash",
        ...     execution_time_ms=150.5,
        ...     similarity=88.5,
        ...     memory_usage_mb=45.2,
        ...     frames_processed=100,
        ...     cache_hit_rate=75.0
        ... )
        >>> benchmark.algorithm_name
        'frame_hash'
    """
    algorithm_name: str
    execution_time_ms: float
    similarity: float
    memory_usage_mb: float
    frames_processed: int
    cache_hit_rate: float

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert AlgorithmBenchmark to dictionary.

        Returns:
            Dictionary representation

        Example:
            >>> data = benchmark.to_dict()
            >>> data['algorithm_name']
            'frame_hash'
        """
        return {
            'algorithm_name': self.algorithm_name,
            'execution_time_ms': round(self.execution_time_ms, 2),
            'execution_time_seconds': round(self.execution_time_ms / 1000, 2),
            'similarity': round(self.similarity, 2),
            'memory_usage_mb': round(self.memory_usage_mb, 2),
            'frames_processed': self.frames_processed,
            'cache_hit_rate': round(self.cache_hit_rate, 2)
        }


@dataclass(frozen=True)
class PipelineBenchmark:
    """
    Performance metrics for a complete pipeline execution.

    Attributes:
        pipeline_name: Name of the pipeline preset
        total_time_ms: Total execution time in milliseconds
        algorithm_benchmarks: List of per-algorithm benchmarks
        similarity_score: Global similarity score (0-100)
        is_duplicate: Whether videos are duplicates
        memory_peak_mb: Peak memory usage in MB
        cache_statistics: Cache hit/miss statistics
        timestamp: When benchmark was performed

    Example:
        >>> from datetime import datetime
        >>> benchmark = PipelineBenchmark(
        ...     pipeline_name="balanced",
        ...     total_time_ms=2500.0,
        ...     algorithm_benchmarks=[],
        ...     similarity_score=88.5,
        ...     is_duplicate=True,
        ...     memory_peak_mb=128.5,
        ...     cache_statistics={'hits': 10, 'misses': 2},
        ...     timestamp=datetime.now()
        ... )
        >>> benchmark.pipeline_name
        'balanced'
    """
    pipeline_name: str
    total_time_ms: float
    algorithm_benchmarks: List[AlgorithmBenchmark]
    similarity_score: float
    is_duplicate: bool
    memory_peak_mb: float
    cache_statistics: Dict[str, Any]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert PipelineBenchmark to dictionary.

        Returns:
            Dictionary representation

        Example:
            >>> data = benchmark.to_dict()
            >>> data['pipeline_name']
            'balanced'
        """
        return {
            'pipeline_name': self.pipeline_name,
            'total_time_ms': round(self.total_time_ms, 2),
            'total_time_seconds': round(self.total_time_ms / 1000, 2),
            'algorithm_benchmarks': [
                algo.to_dict() for algo in self.algorithm_benchmarks
            ],
            'algorithm_count': len(self.algorithm_benchmarks),
            'similarity_score': round(self.similarity_score, 2),
            'is_duplicate': self.is_duplicate,
            'memory_peak_mb': round(self.memory_peak_mb, 2),
            'cache_statistics': self.cache_statistics,
            'timestamp': self.timestamp.isoformat()
        }

    def get_slowest_algorithm(self) -> Optional[AlgorithmBenchmark]:
        """
        Get the algorithm with longest execution time.

        Returns:
            AlgorithmBenchmark with max execution time, or None if no algorithms

        Example:
            >>> slowest = benchmark.get_slowest_algorithm()
            >>> slowest.algorithm_name if slowest else None
            'optical_flow'
        """
        if not self.algorithm_benchmarks:
            return None
        return max(self.algorithm_benchmarks, key=lambda a: a.execution_time_ms)

    def get_fastest_algorithm(self) -> Optional[AlgorithmBenchmark]:
        """
        Get the algorithm with shortest execution time.

        Returns:
            AlgorithmBenchmark with min execution time, or None if no algorithms

        Example:
            >>> fastest = benchmark.get_fastest_algorithm()
            >>> fastest.algorithm_name if fastest else None
            'frame_hash'
        """
        if not self.algorithm_benchmarks:
            return None
        return min(self.algorithm_benchmarks, key=lambda a: a.execution_time_ms)

    def get_time_breakdown(self) -> Dict[str, float]:
        """
        Get time breakdown by algorithm.

        Returns:
            Dictionary mapping algorithm name to execution time (ms)

        Example:
            >>> breakdown = benchmark.get_time_breakdown()
            >>> 'frame_hash' in breakdown
            True
        """
        return {
            algo.algorithm_name: algo.execution_time_ms
            for algo in self.algorithm_benchmarks
        }


@dataclass(frozen=True)
class ComparisonBenchmark:
    """
    Benchmark comparison of multiple pipelines on the same video pair.

    Attributes:
        video1_path: Path to first video
        video2_path: Path to second video
        pipeline_benchmarks: List of pipeline benchmarks
        ground_truth: True if duplicate, False if not, None if unknown
        timestamp: When comparison was performed

    Example:
        >>> from pathlib import Path
        >>> from datetime import datetime
        >>> benchmark = ComparisonBenchmark(
        ...     video1_path=Path("/v1.mp4"),
        ...     video2_path=Path("/v2.mp4"),
        ...     pipeline_benchmarks=[],
        ...     ground_truth=True,
        ...     timestamp=datetime.now()
        ... )
        >>> benchmark.video1_path.name
        'v1.mp4'
    """
    video1_path: Path
    video2_path: Path
    pipeline_benchmarks: List[PipelineBenchmark]
    ground_truth: Optional[bool]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ComparisonBenchmark to dictionary.

        Returns:
            Dictionary representation

        Example:
            >>> data = benchmark.to_dict()
            >>> data['video1_name']
            'v1.mp4'
        """
        return {
            'video1_path': str(self.video1_path),
            'video1_name': self.video1_path.name,
            'video2_path': str(self.video2_path),
            'video2_name': self.video2_path.name,
            'pipeline_benchmarks': [
                pb.to_dict() for pb in self.pipeline_benchmarks
            ],
            'pipeline_count': len(self.pipeline_benchmarks),
            'ground_truth': self.ground_truth,
            'timestamp': self.timestamp.isoformat()
        }

    def get_fastest_pipeline(self) -> Optional[PipelineBenchmark]:
        """
        Get the pipeline with shortest execution time.

        Returns:
            PipelineBenchmark with minimum total time, or None if no pipelines

        Example:
            >>> fastest = benchmark.get_fastest_pipeline()
            >>> fastest.pipeline_name if fastest else None
            'fast'
        """
        if not self.pipeline_benchmarks:
            return None
        return min(self.pipeline_benchmarks, key=lambda p: p.total_time_ms)

    def get_most_accurate_pipeline(self) -> Optional[PipelineBenchmark]:
        """
        Get the pipeline that matches ground truth (if available).

        Returns:
            PipelineBenchmark that best matches ground truth, or None

        Example:
            >>> accurate = benchmark.get_most_accurate_pipeline()
            >>> accurate.pipeline_name if accurate else None
            'thorough'
        """
        if self.ground_truth is None or not self.pipeline_benchmarks:
            return None

        # Find pipeline whose is_duplicate matches ground_truth
        matching = [
            pb for pb in self.pipeline_benchmarks
            if pb.is_duplicate == self.ground_truth
        ]

        if not matching:
            return None

        # Among matching, return the one with highest confidence (similarity score)
        return max(matching, key=lambda p: p.similarity_score)

    def rank_by_speed(self) -> List[Tuple[str, float]]:
        """
        Rank pipelines by execution time (fastest to slowest).

        Returns:
            List of (pipeline_name, time_ms) tuples sorted by speed

        Example:
            >>> rankings = benchmark.rank_by_speed()
            >>> rankings[0][0]  # Fastest pipeline name
            'fast'
        """
        return [
            (pb.pipeline_name, pb.total_time_ms)
            for pb in sorted(self.pipeline_benchmarks, key=lambda p: p.total_time_ms)
        ]

    def rank_by_accuracy(self) -> List[Tuple[str, float]]:
        """
        Rank pipelines by similarity score (highest to lowest).

        Returns:
            List of (pipeline_name, similarity) tuples sorted by accuracy

        Example:
            >>> rankings = benchmark.rank_by_accuracy()
            >>> rankings[0][0]  # Most accurate pipeline name
            'thorough'
        """
        return [
            (pb.pipeline_name, pb.similarity_score)
            for pb in sorted(self.pipeline_benchmarks, key=lambda p: p.similarity_score, reverse=True)
        ]


@dataclass(frozen=True)
class AccuracyMetrics:
    """
    Classification accuracy metrics based on confusion matrix.

    Attributes:
        true_positives: Duplicates correctly detected
        false_positives: Non-duplicates marked as duplicates
        true_negatives: Non-duplicates correctly rejected
        false_negatives: Duplicates missed

    Example:
        >>> metrics = AccuracyMetrics(
        ...     true_positives=45,
        ...     false_positives=5,
        ...     true_negatives=40,
        ...     false_negatives=10
        ... )
        >>> metrics.accuracy
        0.85
    """
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int

    @property
    def accuracy(self) -> float:
        """
        Overall accuracy: (TP + TN) / Total.

        Returns:
            Accuracy as float (0.0 to 1.0)

        Example:
            >>> metrics.accuracy
            0.85
        """
        total = self.true_positives + self.false_positives + \
                self.true_negatives + self.false_negatives
        if total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / total

    @property
    def precision(self) -> float:
        """
        Precision: TP / (TP + FP).

        Measures how many predicted duplicates are actually duplicates.

        Returns:
            Precision as float (0.0 to 1.0)

        Example:
            >>> metrics.precision
            0.9
        """
        denominator = self.true_positives + self.false_positives
        if denominator == 0:
            return 0.0
        return self.true_positives / denominator

    @property
    def recall(self) -> float:
        """
        Recall (Sensitivity): TP / (TP + FN).

        Measures how many actual duplicates are detected.

        Returns:
            Recall as float (0.0 to 1.0)

        Example:
            >>> metrics.recall
            0.818
        """
        denominator = self.true_positives + self.false_negatives
        if denominator == 0:
            return 0.0
        return self.true_positives / denominator

    @property
    def f1_score(self) -> float:
        """
        F1 Score: 2 * (precision * recall) / (precision + recall).

        Harmonic mean of precision and recall.

        Returns:
            F1 score as float (0.0 to 1.0)

        Example:
            >>> metrics.f1_score
            0.857
        """
        p, r = self.precision, self.recall
        if (p + r) == 0:
            return 0.0
        return 2 * (p * r) / (p + r)

    @property
    def specificity(self) -> float:
        """
        Specificity: TN / (TN + FP).

        Measures how many actual non-duplicates are correctly rejected.

        Returns:
            Specificity as float (0.0 to 1.0)

        Example:
            >>> metrics.specificity
            0.888
        """
        denominator = self.true_negatives + self.false_positives
        if denominator == 0:
            return 0.0
        return self.true_negatives / denominator

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert AccuracyMetrics to dictionary.

        Returns:
            Dictionary with all metrics

        Example:
            >>> data = metrics.to_dict()
            >>> data['accuracy']
            0.85
        """
        return {
            'confusion_matrix': {
                'true_positives': self.true_positives,
                'false_positives': self.false_positives,
                'true_negatives': self.true_negatives,
                'false_negatives': self.false_negatives
            },
            'accuracy': round(self.accuracy, 4),
            'precision': round(self.precision, 4),
            'recall': round(self.recall, 4),
            'f1_score': round(self.f1_score, 4),
            'specificity': round(self.specificity, 4)
        }


@dataclass(frozen=True)
class TestSetBenchmark:
    """
    Benchmark results on a complete test dataset.

    Attributes:
        pipeline_name: Name of pipeline tested
        test_set_name: Name of test set
        total_comparisons: Number of video pairs tested
        accuracy_metrics: Classification metrics
        avg_execution_time_ms: Average time per comparison
        total_time_seconds: Total execution time
        comparison_benchmarks: Individual comparison results
        timestamp: When test was performed

    Example:
        >>> from datetime import datetime
        >>> benchmark = TestSetBenchmark(
        ...     pipeline_name="balanced",
        ...     test_set_name="test_v1",
        ...     total_comparisons=100,
        ...     accuracy_metrics=AccuracyMetrics(45, 5, 40, 10),
        ...     avg_execution_time_ms=2500.0,
        ...     total_time_seconds=250.0,
        ...     comparison_benchmarks=[],
        ...     timestamp=datetime.now()
        ... )
        >>> benchmark.total_comparisons
        100
    """
    pipeline_name: str
    test_set_name: str
    total_comparisons: int
    accuracy_metrics: AccuracyMetrics
    avg_execution_time_ms: float
    total_time_seconds: float
    comparison_benchmarks: List[ComparisonBenchmark]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert TestSetBenchmark to dictionary.

        Returns:
            Dictionary representation

        Example:
            >>> data = benchmark.to_dict()
            >>> data['pipeline_name']
            'balanced'
        """
        return {
            'pipeline_name': self.pipeline_name,
            'test_set_name': self.test_set_name,
            'total_comparisons': self.total_comparisons,
            'accuracy_metrics': self.accuracy_metrics.to_dict(),
            'avg_execution_time_ms': round(self.avg_execution_time_ms, 2),
            'avg_execution_time_seconds': round(self.avg_execution_time_ms / 1000, 2),
            'total_time_seconds': round(self.total_time_seconds, 2),
            'total_time_minutes': round(self.total_time_seconds / 60, 2),
            'comparisons_per_second': round(
                self.total_comparisons / self.total_time_seconds, 2
            ) if self.total_time_seconds > 0 else 0,
            'timestamp': self.timestamp.isoformat()
        }

    def to_json(self, indent: int = 2) -> str:
        """
        Export TestSetBenchmark to JSON string.

        Args:
            indent: Number of spaces for JSON indentation

        Returns:
            JSON string representation

        Example:
            >>> json_str = benchmark.to_json()
            >>> 'pipeline_name' in json_str
            True
        """
        import json
        return json.dumps(self.to_dict(), indent=indent)

    def to_csv_rows(self) -> List[Dict[str, Any]]:
        """
        Convert to CSV-friendly format (one row per comparison).

        Returns:
            List of dictionaries, one per comparison

        Example:
            >>> rows = benchmark.to_csv_rows()
            >>> len(rows) == benchmark.total_comparisons
            True
        """
        rows = []
        for idx, comp_bench in enumerate(self.comparison_benchmarks, 1):
            if comp_bench.pipeline_benchmarks:
                pb = comp_bench.pipeline_benchmarks[0]  # First pipeline
                rows.append({
                    'comparison_id': idx,
                    'video1': comp_bench.video1_path.name,
                    'video2': comp_bench.video2_path.name,
                    'ground_truth': comp_bench.ground_truth,
                    'predicted_duplicate': pb.is_duplicate,
                    'similarity': round(pb.similarity_score, 2),
                    'time_ms': round(pb.total_time_ms, 2),
                    'correct': comp_bench.ground_truth == pb.is_duplicate
                    if comp_bench.ground_truth is not None else None
                })
        return rows

    def generate_confusion_matrix(self) -> List[List[int]]:
        """
        Generate 2x2 confusion matrix as nested list.

        Returns:
            [[TP, FN], [FP, TN]]

        Example:
            >>> matrix = benchmark.generate_confusion_matrix()
            >>> matrix[0][0]  # True positives
            45
        """
        m = self.accuracy_metrics
        return [
            [m.true_positives, m.false_negatives],
            [m.false_positives, m.true_negatives]
        ]
