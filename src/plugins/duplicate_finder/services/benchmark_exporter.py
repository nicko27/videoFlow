"""
Benchmark JSON Exporter

Exports benchmark results to structured JSON format for CI/CD integration.
Provides PASS/FAIL status based on configurable thresholds.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.BenchmarkExporter')


class BenchmarkJSONExporter:
    """
    Export benchmark results to structured JSON format.

    Features:
        - CI/CD friendly JSON format
        - PASS/FAIL/WARNING status based on thresholds
        - Detailed metrics and per-pair results
        - Configurable quality gates
        - Compatible with common CI tools (Jenkins, GitHub Actions, GitLab CI)

    Example JSON Output:
        {
            "status": "PASS",
            "timestamp": "2025-12-09T10:30:00Z",
            "summary": {
                "f1_score": 0.95,
                "precision": 0.93,
                "recall": 0.97
            },
            "thresholds": {
                "f1_min": 0.80,
                "precision_min": 0.70,
                "recall_min": 0.70
            },
            "details": {...}
        }
    """

    # Default thresholds for PASS/FAIL
    DEFAULT_THRESHOLDS = {
        'f1_min': 0.80,
        'precision_min': 0.70,
        'recall_min': 0.70,
        'accuracy_min': 0.75
    }

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        """
        Initialize exporter.

        Args:
            thresholds: Custom quality gate thresholds (optional)
        """
        self.thresholds = thresholds if thresholds else self.DEFAULT_THRESHOLDS.copy()

    def export_run(self, run_id: int, benchmark_manager, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Export a benchmark run to JSON format.

        Args:
            run_id: Benchmark run ID to export
            benchmark_manager: BenchmarkManager or DatabaseManager instance
            output_path: Optional file path to save JSON (if None, returns dict only)

        Returns:
            Structured benchmark data as dict
        """
        try:
            # Support both BenchmarkManager (with get_run_details) and DatabaseManager (direct DB access)
            if hasattr(benchmark_manager, 'get_run_details'):
                # BenchmarkManager interface
                run = benchmark_manager.get_run_details(run_id)
                if not run:
                    raise ValueError(f"Run ID {run_id} not found")
                results = benchmark_manager.get_benchmark_results(run_id)
            else:
                # DatabaseManager interface - query directly
                run = self._get_run_details_from_db(benchmark_manager, run_id)
                if not run:
                    raise ValueError(f"Run ID {run_id} not found")
                results = self._get_benchmark_results_from_db(benchmark_manager, run_id)

            # Build JSON structure
            export_data = self._build_export_structure(run, results)

            # Save to file if path provided
            if output_path:
                self._save_to_file(export_data, output_path)
                logger.info(f"Exported run {run_id} to {output_path}")

            return export_data

        except Exception as e:
            logger.error(f"Error exporting run {run_id}: {e}", exc_info=True)
            raise

    def _get_run_details_from_db(self, db_manager, run_id: int) -> Optional[Dict]:
        """Get run details directly from database."""
        with db_manager.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, run_label, created_at, completed_at, test_set_name,
                       pipelines_count, total_pairs, status
                FROM benchmark_runs
                WHERE id = ?
            ''', (run_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'id': row[0],
                'label': row[1],  # Map run_label to label for compatibility
                'created_at': row[2],
                'completed_at': row[3],
                'test_set_name': row[4],
                'total_pipelines': row[5],  # Map pipelines_count to total_pipelines
                'total_pairs': row[6],
                'status': row[7]
            }

    def _get_benchmark_results_from_db(self, db_manager, run_id: int) -> List[Dict]:
        """Get benchmark results directly from database."""
        with db_manager.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pipeline_name, pipeline_config_json, tp, tn, fp, fn,
                       precision, recall, f1_score, total_time, per_pair_results_json,
                       accepted, rejected
                FROM benchmark_results
                WHERE benchmark_run_id = ?
            ''', (run_id,))

            results = []
            for row in cursor.fetchall():
                import json
                # Calculate total pairs and accuracy
                tp, tn, fp, fn = row[2], row[3], row[4], row[5]
                total = tp + tn + fp + fn
                accuracy = ((tp + tn) / total * 100) if total > 0 else 0

                results.append({
                    'pipeline_name': row[0],
                    'pipeline_config': json.loads(row[1]) if row[1] else {},
                    'true_positives': tp,
                    'true_negatives': tn,
                    'false_positives': fp,
                    'false_negatives': fn,
                    'precision': row[6],
                    'recall': row[7],
                    'f1_score': row[8],
                    'accuracy': accuracy,
                    'total_pairs': total,
                    'duration': row[9],
                    'per_pair_results': json.loads(row[10]) if row[10] else [],
                    'method_stats': [],  # Not stored in this schema version
                    'accepted': row[11],
                    'rejected': row[12]
                })
            return results

    def _build_export_structure(self, run: Dict, results: List[Dict]) -> Dict[str, Any]:
        """Build the structured JSON export."""
        # Calculate metrics
        metrics = self._calculate_metrics(results)

        # Determine status
        status = self._determine_status(metrics)

        # Build structure
        export_data = {
            "version": "1.0",
            "status": status,
            "timestamp": run.get('timestamp', datetime.now().isoformat()),
            "run_info": {
                "run_id": run['id'],
                "pipeline_name": run.get('pipeline_name') or run.get('run_label'),
                "test_set_name": run['test_set_name'],
                "duration_seconds": run.get('duration_seconds', run.get('duration', 0))
            },
            "summary": {
                "total_pairs": sum(len(r.get('per_pair_results', [])) for r in results),
                "true_positives": metrics['tp'],
                "false_positives": metrics['fp'],
                "true_negatives": metrics['tn'],
                "false_negatives": metrics['fn'],
                "f1_score": round(metrics['f1_score'], 4),
                "precision": round(metrics['precision'], 4),
                "recall": round(metrics['recall'], 4),
                "accuracy": round(metrics['accuracy'], 4)
            },
            "thresholds": self.thresholds,
            "quality_gates": {
                "f1_score": {
                    "value": metrics['f1_score'],
                    "threshold": self.thresholds['f1_min'],
                    "passed": metrics['f1_score'] >= self.thresholds['f1_min']
                },
                "precision": {
                    "value": metrics['precision'],
                    "threshold": self.thresholds['precision_min'],
                    "passed": metrics['precision'] >= self.thresholds['precision_min']
                },
                "recall": {
                    "value": metrics['recall'],
                    "threshold": self.thresholds['recall_min'],
                    "passed": metrics['recall'] >= self.thresholds['recall_min']
                },
                "accuracy": {
                    "value": metrics['accuracy'],
                    "threshold": self.thresholds['accuracy_min'],
                    "passed": metrics['accuracy'] >= self.thresholds['accuracy_min']
                }
            },
            "details": {
                "confusion_matrix": {
                    "TP": metrics['tp'],
                    "FP": metrics['fp'],
                    "TN": metrics['tn'],
                    "FN": metrics['fn']
                },
                "failures": self._extract_failures(results),
                "warnings": self._extract_warnings(results),
                "all_pairs_detailed": self._extract_all_pairs_detailed(results)
            }
        }

        return export_data

    def _calculate_metrics(self, results: List[Dict]) -> Dict[str, float]:
        """Calculate metrics from results."""
        tp = fp = tn = fn = 0

        for pipeline_result in results:
            for pair in pipeline_result.get('per_pair_results', []):
                expected_raw = pair['expected']
                expected = 'duplicate' if expected_raw in ('duplicate', 'positive') else 'not_duplicate'
                predicted = 'duplicate' if (pair.get('is_match') or pair.get('accepted')) else 'not_duplicate'

                if expected == 'duplicate' and predicted == 'duplicate':
                    tp += 1
                elif expected == 'not_duplicate' and predicted == 'duplicate':
                    fp += 1
                elif expected == 'not_duplicate' and predicted == 'not_duplicate':
                    tn += 1
                elif expected == 'duplicate' and predicted == 'not_duplicate':
                    fn += 1

        # Calculate metrics
        total = tp + fp + tn + fn
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (tp + tn) / total if total > 0 else 0

        return {
            'tp': tp,
            'fp': fp,
            'tn': tn,
            'fn': fn,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'accuracy': accuracy
        }

    def _determine_status(self, metrics: Dict[str, float]) -> str:
        """
        Determine overall status based on metrics and thresholds.

        Returns:
            "PASS", "WARNING", or "FAIL"
        """
        # Check critical failures
        if metrics['f1_score'] < self.thresholds['f1_min']:
            return "FAIL"

        # Check warnings (any metric below threshold but F1 still acceptable)
        if (metrics['precision'] < self.thresholds['precision_min'] or
            metrics['recall'] < self.thresholds['recall_min'] or
            metrics['accuracy'] < self.thresholds['accuracy_min']):
            return "WARNING"

        return "PASS"

    def _extract_failures(self, results: List[Dict]) -> List[Dict]:
        """Extract failed test cases (false positives and false negatives)."""
        failures = []

        for pipeline_result in results:
            for result in pipeline_result.get('per_pair_results', []):
                expected_raw = result['expected']
                expected = 'duplicate' if expected_raw in ('duplicate', 'positive') else 'not_duplicate'
                predicted = 'duplicate' if (result.get('is_match') or result.get('accepted')) else 'not_duplicate'

                if expected != predicted:
                    # Handle both formats: video1_path/video2_path or video1/video2
                    video1 = result.get('video1_path') or result.get('video1', 'unknown')
                    video2 = result.get('video2_path') or result.get('video2', 'unknown')
                    failures.append({
                        'video1': Path(video1).name if video1 != 'unknown' else video1,
                        'video2': Path(video2).name if video2 != 'unknown' else video2,
                        'expected': expected,
                        'predicted': predicted,
                        'similarity': result.get('similarity', 0),
                        'type': 'FP' if (expected == 'not_duplicate') else 'FN'
                    })

        return failures

    def _extract_warnings(self, results: List[Dict]) -> List[str]:
        """Extract warnings from results."""
        warnings = []

        # Check for low confidence matches in all pipelines
        for pipeline_result in results:
            for result in pipeline_result.get('per_pair_results', []):
                similarity = result.get('similarity', 0)
                if (result.get('is_match') or result.get('accepted')) and 0.50 <= similarity < 0.60:
                    warnings.append(
                        f"Low confidence match: {Path(result['video1_path']).name} <-> "
                        f"{Path(result['video2_path']).name} (similarity: {similarity:.2f})"
                    )

        return warnings

    def _extract_all_pairs_detailed(self, results: List[Dict]) -> List[Dict]:
        """
        Extract ALL pairs with complete detailed information for analysis.

        This provides the most comprehensive view of benchmark results,
        including:
        - Full paths and expected/predicted labels
        - All pipeline results and method details
        - Timing and performance metrics
        - Confirmation/rejection reasons
        - Cache hit information

        Returns:
            List of dicts with complete per-pair information
        """
        detailed_pairs = []

        for pipeline_result in results:
            pipeline_name = pipeline_result.get('pipeline_name', 'unknown')

            for pair_result in pipeline_result.get('per_pair_results', []):
                # Normalize labels for classification
                expected_raw = pair_result.get('expected', 'unknown')
                expected_normalized = 'positive' if expected_raw in ('duplicate', 'positive', 'scene_found') else \
                                     'negative' if expected_raw in ('not_duplicate', 'negative', 'scene_not_found') else \
                                     'unknown'

                predicted = 'positive' if (pair_result.get('is_match') or pair_result.get('accepted')) else 'negative'

                # Determine result classification
                if expected_normalized == 'unknown':
                    classification = 'unlabeled'
                elif expected_normalized == predicted:
                    classification = 'TP' if predicted == 'positive' else 'TN'
                else:
                    classification = 'FP' if predicted == 'positive' else 'FN'

                # Extract pipeline-specific results
                pipeline_results = pair_result.get('pipeline_results', {})
                method_details = []

                if isinstance(pipeline_results, dict):
                    for method_name, method_result in pipeline_results.items():
                        if isinstance(method_result, dict):
                            method_details.append({
                                'method': method_name,
                                'accepted': method_result.get('accepted', False),
                                'score': method_result.get('score'),
                                'threshold': method_result.get('threshold'),
                                'execution_time': method_result.get('execution_time', 0),
                                'extra_info': method_result.get('extra_info', {})
                            })

                # Build detailed pair info
                detailed_pair = {
                    # Basic identification
                    'pipeline': pipeline_name,
                    'video1_path': pair_result.get('video1', pair_result.get('video1_path', '')),
                    'video2_path': pair_result.get('video2', pair_result.get('video2_path', '')),
                    'video1_name': Path(pair_result.get('video1', pair_result.get('video1_path', ''))).name,
                    'video2_name': Path(pair_result.get('video2', pair_result.get('video2_path', ''))).name,

                    # Expected vs Predicted
                    'expected_label': expected_raw,
                    'expected_normalized': expected_normalized,
                    'predicted': predicted,
                    'classification': classification,
                    'is_correct': expected_normalized == predicted if expected_normalized != 'unknown' else None,

                    # Results
                    'accepted': pair_result.get('accepted', False),
                    'is_match': pair_result.get('is_match', False),
                    'similarity': pair_result.get('similarity'),
                    'weighted_score': pair_result.get('weighted_score'),

                    # Scene/subsequence info
                    'start_time': pair_result.get('start_time'),
                    'duration': pair_result.get('duration'),

                    # Performance
                    'total_time': pair_result.get('total_time', 0),
                    'from_cache': pair_result.get('from_cache', False),

                    # Rejection/confirmation details
                    'rejection_method': pair_result.get('rejection_method'),
                    'confirmation': pair_result.get('confirmation'),
                    'mode': pair_result.get('mode'),

                    # Method-level details
                    'method_results': method_details,

                    # Error info (if any)
                    'error': pair_result.get('error')
                }

                detailed_pairs.append(detailed_pair)

        return detailed_pairs

    def _save_to_file(self, data: Dict, file_path: str):
        """Save JSON data to file."""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def create_ci_friendly_format(export_data: Dict) -> str:
        """
        Create a CI-friendly one-line summary.

        Returns:
            String like "PASS: F1=0.95 Precision=0.93 Recall=0.97"
        """
        summary = export_data['summary']
        status = export_data['status']

        return (
            f"{status}: "
            f"F1={summary['f1_score']:.3f} "
            f"Precision={summary['precision']:.3f} "
            f"Recall={summary['recall']:.3f} "
            f"Accuracy={summary['accuracy']:.3f}"
        )

    @staticmethod
    def get_exit_code(export_data: Dict) -> int:
        """
        Get exit code for CI/CD.

        Returns:
            0 for PASS, 1 for WARNING, 2 for FAIL
        """
        status = export_data['status']
        return {'PASS': 0, 'WARNING': 1, 'FAIL': 2}.get(status, 2)
