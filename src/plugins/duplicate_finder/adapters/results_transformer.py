"""
Transform duplicateFlow results to duplicate_finder GUI format.

duplicateFlow uses VerificationResult dataclass with specific structure.
duplicate_finder GUI expects results in a different format optimized
for display in tables, lists, and charts.

This module handles the transformation between these formats.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import asdict

# Import models from local core module
from ..core.models import (
    VerificationResult,
    MethodResult,
    VerificationStatus
)

MODELS_AVAILABLE = True


class ResultsTransformer:
    """
    Transform duplicateFlow results to GUI-friendly format.

    This class provides various transformation methods for different
    parts of the GUI:
    - Table display format
    - Chart/visualization format
    - Export format (CSV, JSON)
    - Summary statistics

    Example:
        >>> transformer = ResultsTransformer()
        >>> gui_result = transformer.to_gui_format(verification_result)
        >>> print(f"Similarity: {gui_result['similarity']}%")
    """

    @staticmethod
    def to_gui_format(
        result: VerificationResult,
        video1_path: str = "",
        video2_path: str = ""
    ) -> Dict[str, Any]:
        """
        Transform VerificationResult to GUI display format.

        Args:
            result: VerificationResult from duplicateFlow
            video1_path: Path to first video (for display)
            video2_path: Path to second video (for display)

        Returns:
            {
                'video1': str,
                'video2': str,
                'similarity': float (0-100),
                'accepted': bool,
                'confidence': str,
                'status': str,
                'methods': [...],
                'metadata': {...}
            }
        """
        if not MODELS_AVAILABLE:
            return ResultsTransformer._fallback_format(
                video1_path,
                video2_path
            )

        # Extract global score
        global_score = result.global_score

        # Determine acceptance
        accepted = global_score >= 60.0

        # Determine confidence level
        confidence = ResultsTransformer._calculate_confidence(global_score)

        # Transform method results
        methods = []
        for method_result in result.method_results:
            methods.append({
                'name': method_result.method_name,
                'score': method_result.score,
                'accepted': method_result.accepted,
                'weight': method_result.weight,
                'metadata': method_result.metadata
            })

        return {
            'video1': video1_path,
            'video2': video2_path,
            'similarity': round(global_score, 2),
            'accepted': accepted,
            'confidence': confidence,
            'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
            'methods': methods,
            'metadata': {
                'execution_time': result.metadata.get('execution_time', 0),
                'method_count': len(methods),
                'accepted_methods': sum(1 for m in methods if m['accepted']),
                **result.metadata
            }
        }

    @staticmethod
    def to_table_row(
        result: VerificationResult,
        video1_path: str,
        video2_path: str
    ) -> Dict[str, Any]:
        """
        Transform result to table row format.

        Optimized for display in QTableWidget or similar table views.

        Args:
            result: VerificationResult
            video1_path: Path to first video
            video2_path: Path to second video

        Returns:
            {
                'Video 1': str,
                'Video 2': str,
                'Similarity': str,
                'Status': str,
                'Confidence': str,
                'Methods': str,
                'Time': str
            }
        """
        gui_result = ResultsTransformer.to_gui_format(
            result,
            video1_path,
            video2_path
        )

        # Format for table display
        return {
            'Video 1': Path(video1_path).name,
            'Video 2': Path(video2_path).name,
            'Similarity': f"{gui_result['similarity']:.1f}%",
            'Status': '✅ Match' if gui_result['accepted'] else '❌ No match',
            'Confidence': ResultsTransformer._confidence_icon(gui_result['confidence']),
            'Methods': f"{gui_result['metadata']['accepted_methods']}/{gui_result['metadata']['method_count']}",
            'Time': f"{gui_result['metadata']['execution_time']:.1f}s"
        }

    @staticmethod
    def to_chart_data(
        results: List[VerificationResult],
        video_paths: List[tuple]
    ) -> Dict[str, Any]:
        """
        Transform results to chart/visualization format.

        Args:
            results: List of VerificationResults
            video_paths: List of (video1, video2) tuples

        Returns:
            {
                'labels': [...],
                'scores': [...],
                'methods': {...},
                'statistics': {...}
            }
        """
        if not results:
            return {
                'labels': [],
                'scores': [],
                'methods': {},
                'statistics': {}
            }

        labels = []
        scores = []
        method_scores = {}

        for result, (v1, v2) in zip(results, video_paths):
            label = f"{Path(v1).stem} vs {Path(v2).stem}"
            labels.append(label)
            scores.append(result.global_score)

            # Aggregate method scores
            for method_result in result.method_results:
                method_name = method_result.method_name
                if method_name not in method_scores:
                    method_scores[method_name] = []
                method_scores[method_name].append(method_result.score)

        # Calculate statistics
        statistics = {
            'count': len(results),
            'mean_score': sum(scores) / len(scores) if scores else 0,
            'min_score': min(scores) if scores else 0,
            'max_score': max(scores) if scores else 0,
            'accepted_count': sum(1 for s in scores if s >= 60.0),
            'rejected_count': sum(1 for s in scores if s < 60.0)
        }

        return {
            'labels': labels,
            'scores': scores,
            'methods': method_scores,
            'statistics': statistics
        }

    @staticmethod
    def to_export_format(
        result: VerificationResult,
        video1_path: str,
        video2_path: str,
        format: str = 'dict'
    ) -> Any:
        """
        Transform result to export format (CSV, JSON, etc.).

        Args:
            result: VerificationResult
            video1_path: Path to first video
            video2_path: Path to second video
            format: Export format ('dict', 'flat', 'json_str')

        Returns:
            Formatted data for export
        """
        gui_result = ResultsTransformer.to_gui_format(
            result,
            video1_path,
            video2_path
        )

        if format == 'flat':
            # Flat structure for CSV export
            flat = {
                'video1': video1_path,
                'video2': video2_path,
                'similarity': gui_result['similarity'],
                'accepted': gui_result['accepted'],
                'confidence': gui_result['confidence'],
                'status': gui_result['status'],
                'execution_time': gui_result['metadata']['execution_time']
            }

            # Add method scores
            for method in gui_result['methods']:
                flat[f"method_{method['name']}_score"] = method['score']
                flat[f"method_{method['name']}_accepted"] = method['accepted']

            return flat

        elif format == 'json_str':
            import json
            return json.dumps(gui_result, indent=2)

        else:  # format == 'dict'
            return gui_result

    # ================================================================
    # HELPER METHODS
    # ================================================================

    @staticmethod
    def _calculate_confidence(score: float) -> str:
        """
        Calculate confidence level from score.

        Args:
            score: Similarity score (0-100)

        Returns:
            'high', 'medium', 'low', or 'none'
        """
        if score >= 85:
            return 'high'
        elif score >= 70:
            return 'medium'
        elif score >= 50:
            return 'low'
        else:
            return 'none'

    @staticmethod
    def _confidence_icon(confidence: str) -> str:
        """Get icon for confidence level."""
        icons = {
            'high': '🟢 High',
            'medium': '🟡 Medium',
            'low': '🟠 Low',
            'none': '🔴 None'
        }
        return icons.get(confidence, '❓ Unknown')

    @staticmethod
    def _fallback_format(video1: str, video2: str) -> Dict[str, Any]:
        """Fallback format when models not available."""
        return {
            'video1': video1,
            'video2': video2,
            'similarity': 0.0,
            'accepted': False,
            'confidence': 'none',
            'status': 'error',
            'methods': [],
            'metadata': {
                'error': 'duplicateFlow models not available'
            }
        }

    # ================================================================
    # BATCH OPERATIONS
    # ================================================================

    @staticmethod
    def transform_batch(
        results: List[VerificationResult],
        video_pairs: List[tuple],
        format: str = 'gui'
    ) -> List[Dict[str, Any]]:
        """
        Transform multiple results in batch.

        Args:
            results: List of VerificationResults
            video_pairs: List of (video1, video2) tuples
            format: Output format ('gui', 'table', 'export')

        Returns:
            List of transformed results
        """
        transformed = []

        for result, (v1, v2) in zip(results, video_pairs):
            if format == 'gui':
                t = ResultsTransformer.to_gui_format(result, v1, v2)
            elif format == 'table':
                t = ResultsTransformer.to_table_row(result, v1, v2)
            elif format == 'export':
                t = ResultsTransformer.to_export_format(result, v1, v2, 'flat')
            else:
                t = ResultsTransformer.to_gui_format(result, v1, v2)

            transformed.append(t)

        return transformed

    @staticmethod
    def create_summary(
        results: List[VerificationResult]
    ) -> Dict[str, Any]:
        """
        Create summary statistics from multiple results.

        Args:
            results: List of VerificationResults

        Returns:
            Summary statistics dict
        """
        if not results:
            return {
                'total': 0,
                'accepted': 0,
                'rejected': 0,
                'mean_score': 0.0,
                'median_score': 0.0
            }

        scores = [r.global_score for r in results]
        accepted_count = sum(1 for s in scores if s >= 60.0)

        # Calculate median
        sorted_scores = sorted(scores)
        n = len(sorted_scores)
        median = (
            sorted_scores[n // 2]
            if n % 2 == 1
            else (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
        )

        return {
            'total': len(results),
            'accepted': accepted_count,
            'rejected': len(results) - accepted_count,
            'mean_score': sum(scores) / len(scores),
            'median_score': median,
            'min_score': min(scores),
            'max_score': max(scores),
            'std_dev': ResultsTransformer._std_dev(scores)
        }

    @staticmethod
    def _std_dev(values: List[float]) -> float:
        """Calculate standard deviation."""
        if not values:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5


if __name__ == "__main__":
    # Quick test
    print("Testing ResultsTransformer...")
    print(f"Models available: {MODELS_AVAILABLE}")

    if MODELS_AVAILABLE:
        # Create mock result for testing
        print("\n✅ Transformer ready for use")
    else:
        print("\n⚠️  duplicateFlow models not available")
        print("    Fallback mode will be used")
