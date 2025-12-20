"""
Benchmark service for analyzing pipeline performance and accuracy.
"""
import json
import time
import tracemalloc
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from duplicateflow.core.interfaces.i_progress_reporter import IProgressReporter
from duplicateflow.core.interfaces.i_ui_adapter import IUIAdapter
from duplicateflow.core.models.benchmark import (
    AlgorithmBenchmark,
    PipelineBenchmark,
    ComparisonBenchmark,
    AccuracyMetrics,
    TestSetBenchmark,
)
from duplicateflow.pipeline.pipeline import Pipeline


class BenchmarkService:
    """
    Service for benchmarking pipeline performance and accuracy.

    Following Clean Architecture principles:
    - Depends on interfaces (IProgressReporter, IUIAdapter)
    - No dependencies on CLI/GUI
    - Pure business logic
    - Fully testable

    Example:
        >>> from duplicateflow.core.services import BenchmarkService
        >>> from duplicateflow.core.interfaces import NullProgressReporter, NullUIAdapter
        >>> service = BenchmarkService(NullProgressReporter(), NullUIAdapter())
        >>> benchmark = service.benchmark_pipeline(
        ...     Path("/v1.mp4"),
        ...     Path("/v2.mp4"),
        ...     "balanced"
        ... )
    """

    def __init__(
        self,
        progress: IProgressReporter,
        ui: IUIAdapter
    ):
        """
        Initialize BenchmarkService.

        Args:
            progress: Progress reporter for updates
            ui: UI adapter for messages
        """
        self.progress = progress
        self.ui = ui

    def benchmark_pipeline(
        self,
        video1: Path,
        video2: Path,
        pipeline_name: str,
        threshold: float = 70.0
    ) -> PipelineBenchmark:
        """
        Benchmark a single pipeline preset.

        Measures:
        - Total execution time
        - Per-algorithm execution time
        - Peak memory usage
        - Cache statistics
        - Similarity score

        Args:
            video1: First video path
            video2: Second video path
            pipeline_name: Pipeline preset name
            threshold: Similarity threshold (0-100)

        Returns:
            PipelineBenchmark with complete metrics

        Example:
            >>> benchmark = service.benchmark_pipeline(
            ...     Path("/v1.mp4"),
            ...     Path("/v2.mp4"),
            ...     "balanced",
            ...     threshold=70.0
            ... )
            >>> benchmark.pipeline_name
            'balanced'
        """
        from duplicateflow.core.interfaces import MessageType

        self.progress.start_phase(
            "benchmark",
            total=1,
            message=f"Benchmarking {pipeline_name}..."
        )

        # Load pipeline
        try:
            pipeline = Pipeline.from_preset(pipeline_name)
        except Exception as e:
            self.ui.display_message(
                f"Failed to load pipeline '{pipeline_name}': {str(e)}",
                MessageType.ERROR
            )
            raise

        # Start memory profiling
        tracemalloc.start()
        start_time = time.perf_counter()

        # Run comparison
        try:
            result = pipeline.compare(str(video1), str(video2))
        except Exception as e:
            tracemalloc.stop()
            self.ui.display_message(
                f"Comparison failed: {str(e)}",
                MessageType.ERROR
            )
            raise

        # Collect metrics
        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        total_time_ms = (end_time - start_time) * 1000
        memory_peak_mb = peak / 1024 / 1024

        # Extract algorithm benchmarks
        algo_benchmarks = []
        individual_results = result.get('individual_results', [])

        for algo_result in individual_results:
            algo_benchmarks.append(AlgorithmBenchmark(
                algorithm_name=algo_result.get('algorithm', 'unknown'),
                execution_time_ms=algo_result.get('time_ms', 0.0),
                similarity=algo_result.get('similarity', 0.0),
                memory_usage_mb=algo_result.get('memory_mb', 0.0),
                frames_processed=algo_result.get('frames_processed', 0),
                cache_hit_rate=algo_result.get('cache_hit_rate', 0.0)
            ))

        # Build benchmark result
        benchmark = PipelineBenchmark(
            pipeline_name=pipeline_name,
            total_time_ms=total_time_ms,
            algorithm_benchmarks=algo_benchmarks,
            similarity_score=result.get('global_score', 0.0),
            is_duplicate=result.get('accepted', False),
            memory_peak_mb=memory_peak_mb,
            cache_statistics=result.get('cache_stats', {}),
            timestamp=datetime.now()
        )

        self.progress.finish_phase(
            "benchmark",
            message=f"Completed in {benchmark.total_time_ms:.0f}ms"
        )

        return benchmark

    def compare_pipelines(
        self,
        video1: Path,
        video2: Path,
        pipeline_names: List[str],
        threshold: float = 70.0,
        ground_truth: Optional[bool] = None
    ) -> ComparisonBenchmark:
        """
        Compare multiple pipeline presets on the same video pair.

        Args:
            video1: First video path
            video2: Second video path
            pipeline_names: List of pipeline preset names
            threshold: Similarity threshold (0-100)
            ground_truth: True if duplicate, False if not, None if unknown

        Returns:
            ComparisonBenchmark with all pipeline results

        Example:
            >>> benchmark = service.compare_pipelines(
            ...     Path("/v1.mp4"),
            ...     Path("/v2.mp4"),
            ...     ["fast", "balanced", "thorough"],
            ...     threshold=70.0,
            ...     ground_truth=True
            ... )
            >>> len(benchmark.pipeline_benchmarks)
            3
        """
        from duplicateflow.core.interfaces import MessageType

        total = len(pipeline_names)
        self.progress.start_phase(
            "comparison",
            total=total,
            message=f"Comparing {total} pipelines..."
        )

        self.ui.display_message(
            f"Benchmarking {total} pipeline(s): {', '.join(pipeline_names)}",
            MessageType.INFO
        )

        benchmarks = []
        for idx, pipeline_name in enumerate(pipeline_names, 1):
            self.progress.update(
                "comparison",
                current=idx,
                message=f"Testing {pipeline_name}..."
            )

            try:
                benchmark = self.benchmark_pipeline(
                    video1,
                    video2,
                    pipeline_name,
                    threshold
                )
                benchmarks.append(benchmark)

                self.ui.display_message(
                    f"{pipeline_name}: {benchmark.similarity_score:.1f}% "
                    f"in {benchmark.total_time_ms:.0f}ms",
                    MessageType.SUCCESS
                )

            except Exception as e:
                self.ui.display_message(
                    f"Failed to benchmark {pipeline_name}: {str(e)}",
                    MessageType.ERROR
                )
                # Continue with other pipelines

        self.progress.finish_phase(
            "comparison",
            message=f"{len(benchmarks)}/{total} pipelines benchmarked"
        )

        return ComparisonBenchmark(
            video1_path=video1,
            video2_path=video2,
            pipeline_benchmarks=benchmarks,
            ground_truth=ground_truth,
            timestamp=datetime.now()
        )

    def benchmark_testset(
        self,
        testset_path: Path,
        pipeline_name: str,
        threshold: float = 70.0
    ) -> TestSetBenchmark:
        """
        Evaluate a pipeline on a complete test dataset.

        Test set format (JSON):
        {
            "name": "test_set_v1",
            "pairs": [
                {
                    "video1": "/path/to/v1.mp4",
                    "video2": "/path/to/v2.mp4",
                    "is_duplicate": true
                },
                ...
            ]
        }

        Args:
            testset_path: Path to test set JSON file
            pipeline_name: Pipeline preset name
            threshold: Similarity threshold (0-100)

        Returns:
            TestSetBenchmark with accuracy metrics

        Example:
            >>> benchmark = service.benchmark_testset(
            ...     Path("/testdata/ground_truth.json"),
            ...     "balanced",
            ...     threshold=70.0
            ... )
            >>> benchmark.accuracy_metrics.accuracy
            0.92
        """
        from duplicateflow.core.interfaces import MessageType

        # Load test set
        try:
            with open(testset_path, 'r') as f:
                testset = json.load(f)
        except Exception as e:
            self.ui.display_message(
                f"Failed to load test set: {str(e)}",
                MessageType.ERROR
            )
            raise

        test_name = testset.get('name', testset_path.stem)
        pairs = testset.get('pairs', [])

        if not pairs:
            self.ui.display_message(
                "Test set contains no pairs",
                MessageType.WARNING
            )
            return TestSetBenchmark(
                pipeline_name=pipeline_name,
                test_set_name=test_name,
                total_comparisons=0,
                accuracy_metrics=AccuracyMetrics(0, 0, 0, 0),
                avg_execution_time_ms=0.0,
                total_time_seconds=0.0,
                comparison_benchmarks=[],
                timestamp=datetime.now()
            )

        # Run benchmarks
        total = len(pairs)
        self.progress.start_phase(
            "testset",
            total=total,
            message=f"Evaluating {pipeline_name} on {test_name}..."
        )

        self.ui.display_message(
            f"Test set: {test_name} ({total} pairs)",
            MessageType.INFO
        )

        comparison_benchmarks = []
        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0
        total_time_ms = 0.0
        successful_comparisons = 0

        for idx, pair in enumerate(pairs, 1):
            video1 = Path(pair['video1'])
            video2 = Path(pair['video2'])
            ground_truth = pair['is_duplicate']

            self.progress.update(
                "testset",
                current=idx,
                message=f"Testing pair {idx}/{total}..."
            )

            # Validate files exist
            if not video1.exists():
                self.ui.display_message(
                    f"Video not found: {video1}",
                    MessageType.WARNING
                )
                continue

            if not video2.exists():
                self.ui.display_message(
                    f"Video not found: {video2}",
                    MessageType.WARNING
                )
                continue

            # Benchmark
            try:
                benchmark = self.benchmark_pipeline(
                    video1,
                    video2,
                    pipeline_name,
                    threshold
                )

                comparison_benchmarks.append(ComparisonBenchmark(
                    video1_path=video1,
                    video2_path=video2,
                    pipeline_benchmarks=[benchmark],
                    ground_truth=ground_truth,
                    timestamp=datetime.now()
                ))

                # Update confusion matrix
                predicted = benchmark.is_duplicate
                if ground_truth and predicted:
                    true_positives += 1
                elif ground_truth and not predicted:
                    false_negatives += 1
                elif not ground_truth and predicted:
                    false_positives += 1
                else:  # not ground_truth and not predicted
                    true_negatives += 1

                total_time_ms += benchmark.total_time_ms
                successful_comparisons += 1

            except Exception as e:
                self.ui.display_message(
                    f"Failed pair {idx}: {str(e)}",
                    MessageType.WARNING
                )
                # Continue with next pair

        # Calculate metrics
        accuracy_metrics = AccuracyMetrics(
            true_positives=true_positives,
            false_positives=false_positives,
            true_negatives=true_negatives,
            false_negatives=false_negatives
        )

        avg_time_ms = total_time_ms / successful_comparisons if successful_comparisons > 0 else 0.0

        self.progress.finish_phase(
            "testset",
            message=f"Accuracy: {accuracy_metrics.accuracy * 100:.1f}% "
                   f"({successful_comparisons}/{total} successful)"
        )

        self.ui.display_message(
            f"Accuracy: {accuracy_metrics.accuracy * 100:.2f}%, "
            f"Precision: {accuracy_metrics.precision * 100:.2f}%, "
            f"Recall: {accuracy_metrics.recall * 100:.2f}%",
            MessageType.SUCCESS
        )

        return TestSetBenchmark(
            pipeline_name=pipeline_name,
            test_set_name=test_name,
            total_comparisons=successful_comparisons,
            accuracy_metrics=accuracy_metrics,
            avg_execution_time_ms=avg_time_ms,
            total_time_seconds=total_time_ms / 1000,
            comparison_benchmarks=comparison_benchmarks,
            timestamp=datetime.now()
        )

    def profile_algorithms(
        self,
        video1: Path,
        video2: Path,
        pipeline_name: str
    ) -> Dict[str, Any]:
        """
        Profile each algorithm individually for detailed analysis.

        Args:
            video1: First video path
            video2: Second video path
            pipeline_name: Pipeline preset name

        Returns:
            Dictionary with detailed algorithm profiling

        Example:
            >>> profile = service.profile_algorithms(
            ...     Path("/v1.mp4"),
            ...     Path("/v2.mp4"),
            ...     "thorough"
            ... )
            >>> 'slowest_algorithm' in profile
            True
        """
        benchmark = self.benchmark_pipeline(video1, video2, pipeline_name)

        # Time breakdown
        time_breakdown = benchmark.get_time_breakdown()

        # Ranking by time
        algos_by_time = sorted(
            benchmark.algorithm_benchmarks,
            key=lambda a: a.execution_time_ms,
            reverse=True
        )

        return {
            'pipeline': pipeline_name,
            'total_time_ms': benchmark.total_time_ms,
            'time_breakdown': time_breakdown,
            'slowest_algorithm': algos_by_time[0].to_dict() if algos_by_time else None,
            'fastest_algorithm': algos_by_time[-1].to_dict() if algos_by_time else None,
            'algorithm_rankings': [
                {
                    'rank': idx + 1,
                    'algorithm': algo.algorithm_name,
                    'time_ms': algo.execution_time_ms,
                    'percentage': (algo.execution_time_ms / benchmark.total_time_ms) * 100
                    if benchmark.total_time_ms > 0 else 0,
                    'similarity': algo.similarity,
                    'frames_processed': algo.frames_processed
                }
                for idx, algo in enumerate(algos_by_time)
            ]
        }
