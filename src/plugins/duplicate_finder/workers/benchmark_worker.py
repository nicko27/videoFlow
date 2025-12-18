"""
Benchmark worker for running test sets with custom pipelines.

This worker runs benchmark comparisons using pipeline configurations
from the database, exactly like the CLI run_testset.py.
"""
import json
import time
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import QThread, pyqtSignal, QMutex

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.BenchmarkWorker')


class BenchmarkWorker(QThread):
    """
    Worker thread for benchmark testing with custom pipelines.

    This worker executes test set comparisons using pipeline configurations
    stored in the database, allowing testing of custom algorithm combinations.

    Signals:
        progress (int): Current comparison count
        finished (): Processing complete
        result_ready (dict): Single comparison result
        error (str): Error message
        status_update (str): Status message
        comparison_details (int, int, str, str): current, total, file1, file2
    """

    # Signal definitions
    progress = pyqtSignal(int)  # Current progress count
    finished = pyqtSignal()  # Processing complete
    result_ready = pyqtSignal(dict)  # Individual result
    error = pyqtSignal(str)  # Error message
    status_update = pyqtSignal(str)  # Status message
    comparison_details = pyqtSignal(int, int, str, str)  # current, total, file1, file2

    def __init__(
        self,
        pairs: List[Dict[str, Any]],
        pipeline_config: Dict[str, Any],
        threshold: float = 70.0,
        export_json_path: Optional[str] = None
    ) -> None:
        """
        Initialize the benchmark worker.

        Args:
            pairs: List of test pairs, each with:
                - video1_path: Path to first video
                - video2_path: Path to second video
                - expected: Expected result ('positive', 'negative', 'scene_found')
                - pair_id: Optional pair ID
            pipeline_config: Pipeline configuration from database:
                - mode: Pipeline mode
                - methods: List of algorithm configs
                - global_threshold: Global threshold
            threshold: Similarity threshold percentage (0-100)
            export_json_path: Optional path to export results as JSON
        """
        super().__init__()
        self.pairs = pairs
        self.pipeline_config = pipeline_config
        self.threshold = threshold
        self.export_json_path = export_json_path

        self._stop = False
        self._mutex = QMutex()
        self.processed_count = 0
        self.total_comparisons = len(pairs)

        # Initialize adapter
        self.adapter = None

        # Store all results for JSON export
        self.all_results = []

        logger.info(
            f"BenchmarkWorker initialized: "
            f"{self.total_comparisons} pairs, mode='{pipeline_config.get('mode', 'unknown')}'"
        )

    def run(self) -> None:
        """Execute the benchmark workflow."""
        try:
            # Lazy import to avoid circular dependencies
            try:
                from ..adapters.duplicateflow_adapter import DuplicateFlowAdapter, DUPLICATEFLOW_AVAILABLE
            except ImportError:
                from adapters.duplicateflow_adapter import DuplicateFlowAdapter, DUPLICATEFLOW_AVAILABLE

            if not DUPLICATEFLOW_AVAILABLE:
                self.error.emit("DuplicateFlow is not available")
                self.finished.emit()
                return

            # Initialize adapter
            self.adapter = DuplicateFlowAdapter()

            if self.total_comparisons == 0:
                logger.info("No pairs to compare")
                self.status_update.emit("No video pairs to compare")
                self.finished.emit()
                return

            mode = self.pipeline_config.get('mode', 'unknown')
            num_algos = len(self.pipeline_config.get('methods', []))

            logger.info(
                f"Starting benchmark: {self.total_comparisons} pairs, "
                f"mode={mode}, algorithms={num_algos}"
            )
            self.status_update.emit(
                f"Comparing {self.total_comparisons} pairs (mode: {mode})..."
            )

            # Compare each pair
            start_time = time.time()

            for i, pair in enumerate(self.pairs):
                # Check for cancellation
                if self._stop:
                    logger.info("Benchmark cancelled by user")
                    self.status_update.emit("Benchmark cancelled")
                    break

                video1 = pair['video1_path']
                video2 = pair['video2_path']
                expected = pair.get('expected', 'unknown')
                pair_id = pair.get('pair_id', i)

                # Emit comparison details
                self.comparison_details.emit(
                    i + 1,
                    self.total_comparisons,
                    Path(video1).name,
                    Path(video2).name
                )

                # Compare videos using custom pipeline
                try:
                    pair_start = time.time()

                    result = self.adapter.compare_videos_with_pipeline(
                        video1,
                        video2,
                        pipeline_config=self.pipeline_config
                    )

                    pair_time = time.time() - pair_start

                    # Determine classification
                    similarity = result['similarity']
                    is_duplicate = result['accepted'] and similarity >= self.threshold

                    # Classify result (TP/FP/TN/FN)
                    if expected in ['positive', 'duplicate', 'scene_found']:
                        classification = 'tp' if is_duplicate else 'fn'
                    elif expected == 'negative':
                        classification = 'tn' if not is_duplicate else 'fp'
                    else:
                        classification = 'unknown'

                    # Build result dict
                    comparison_result = {
                        'pair_id': pair_id,
                        'video1': video1,
                        'video2': video2,
                        'expected': expected,
                        'score': similarity,
                        'is_duplicate': is_duplicate,
                        'classification': classification,
                        'time_seconds': pair_time,
                        'status': 'success',
                        'metadata': result.get('metadata', {})
                    }

                    # Store result for JSON export
                    self.all_results.append(comparison_result)

                    # Emit result
                    self.result_ready.emit(comparison_result)

                    # Update processed count
                    self.processed_count += 1
                    self.progress.emit(self.processed_count)

                    logger.debug(
                        f"[{i+1}/{self.total_comparisons}] {Path(video1).name} <-> {Path(video2).name}: "
                        f"{similarity:.1f}% ({classification.upper()})"
                    )

                except Exception as e:
                    logger.error(f"Comparison failed for pair {pair_id}: {e}")

                    # Emit error result
                    error_result = {
                        'pair_id': pair_id,
                        'video1': video1,
                        'video2': video2,
                        'expected': expected,
                        'score': 0.0,
                        'is_duplicate': False,
                        'classification': 'unknown',
                        'time_seconds': 0.0,
                        'status': 'error',
                        'error': str(e)
                    }

                    # Store error result for JSON export
                    self.all_results.append(error_result)

                    self.result_ready.emit(error_result)

                    # Continue with next pair
                    self.processed_count += 1
                    self.progress.emit(self.processed_count)

            # Calculate elapsed time
            elapsed = time.time() - start_time
            avg_time = elapsed / max(self.processed_count, 1)

            logger.info(
                f"Benchmark complete: {self.processed_count}/{self.total_comparisons} pairs "
                f"in {elapsed:.1f}s (avg: {avg_time:.1f}s/pair)"
            )

            self.status_update.emit(
                f"Benchmark complete: {self.processed_count} pairs in {elapsed:.1f}s"
            )

            # Export results to JSON if requested
            if self.export_json_path and self.all_results:
                try:
                    self._export_to_json(elapsed, avg_time)
                except Exception as e:
                    logger.error(f"Failed to export JSON: {e}", exc_info=True)
                    self.error.emit(f"JSON export error: {str(e)}")

        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            self.error.emit(f"Benchmark error: {str(e)}")

        finally:
            self.finished.emit()

    def _export_to_json(self, total_time: float, avg_time: float) -> None:
        """
        Export benchmark results to JSON file.

        Args:
            total_time: Total execution time in seconds
            avg_time: Average time per comparison in seconds
        """
        # Calculate statistics
        tp_count = sum(1 for r in self.all_results if r['classification'] == 'tp')
        fp_count = sum(1 for r in self.all_results if r['classification'] == 'fp')
        tn_count = sum(1 for r in self.all_results if r['classification'] == 'tn')
        fn_count = sum(1 for r in self.all_results if r['classification'] == 'fn')
        error_count = sum(1 for r in self.all_results if r['status'] == 'error')

        # Calculate metrics
        total_positives = tp_count + fn_count
        total_negatives = tn_count + fp_count
        precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 0.0
        recall = tp_count / (tp_count + fn_count) if (tp_count + fn_count) > 0 else 0.0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp_count + tn_count) / len(self.all_results) if self.all_results else 0.0

        # Build export data
        export_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'pipeline_name': self.pipeline_config.get('name', 'unnamed'),
                'pipeline_mode': self.pipeline_config.get('mode', 'unknown'),
                'threshold': self.threshold,
                'total_pairs': self.total_comparisons,
                'processed_pairs': self.processed_count,
                'total_time_seconds': round(total_time, 2),
                'avg_time_seconds': round(avg_time, 2)
            },
            'pipeline_config': {
                'mode': self.pipeline_config.get('mode', 'unknown'),
                'methods': self.pipeline_config.get('methods', []),
                'stages': self.pipeline_config.get('stages', []),
                'global_threshold': self.pipeline_config.get('global_threshold', 70.0),
                'confirmation': self.pipeline_config.get('confirmation', {})
            },
            'summary': {
                'confusion_matrix': {
                    'tp': tp_count,
                    'fp': fp_count,
                    'tn': tn_count,
                    'fn': fn_count
                },
                'metrics': {
                    'precision': round(precision, 4),
                    'recall': round(recall, 4),
                    'f1_score': round(f1_score, 4),
                    'accuracy': round(accuracy, 4)
                },
                'counts': {
                    'total_positives': total_positives,
                    'total_negatives': total_negatives,
                    'errors': error_count
                }
            },
            'results': self.all_results
        }

        # Write to JSON file
        output_path = Path(self.export_json_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(
            f"Benchmark results exported to {output_path} - "
            f"TP={tp_count} FP={fp_count} TN={tn_count} FN={fn_count}, "
            f"Precision={precision:.2%} Recall={recall:.2%} F1={f1_score:.2%}"
        )

        self.status_update.emit(f"Results exported to {output_path.name}")

    def stop(self) -> None:
        """Stop the worker gracefully."""
        self._mutex.lock()
        self._stop = True
        self._mutex.unlock()
        logger.info("Stop requested for benchmark worker")

    def is_stopped(self) -> bool:
        """Check if worker has been stopped."""
        self._mutex.lock()
        stopped = self._stop
        self._mutex.unlock()
        return stopped
