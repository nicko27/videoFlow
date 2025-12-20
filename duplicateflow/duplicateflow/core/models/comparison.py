"""
Comparison result model for video-to-video comparison results.
"""
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from .algorithm_result import AlgorithmResult


@dataclass(frozen=True)
class ComparisonResult:
    """
    Result from comparing two videos using a detection pipeline.

    Attributes:
        video1_path: Path to the first video
        video2_path: Path to the second video
        similarity_score: Global similarity score (0-100)
        is_duplicate: Whether the videos are considered duplicates
        algorithm_results: Results from individual algorithms
        pipeline_name: Name of the pipeline used
        execution_time_ms: Total execution time (milliseconds)
        timestamp: When this comparison was performed
        metadata: Additional comparison metadata

    Example:
        >>> from pathlib import Path
        >>> from datetime import datetime
        >>> result = ComparisonResult(
        ...     video1_path=Path("/videos/movie1.mp4"),
        ...     video2_path=Path("/videos/movie2.mp4"),
        ...     similarity_score=85.5,
        ...     is_duplicate=True,
        ...     algorithm_results=[],
        ...     pipeline_name="balanced",
        ...     execution_time_ms=2500.0,
        ...     timestamp=datetime.now(),
        ...     metadata={}
        ... )
        >>> result.is_duplicate
        True
    """
    video1_path: Path
    video2_path: Path
    similarity_score: float
    is_duplicate: bool
    algorithm_results: List[AlgorithmResult]
    pipeline_name: str
    execution_time_ms: float
    timestamp: datetime
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ComparisonResult to dictionary for serialization.

        Returns:
            Dictionary representation of the comparison result

        Example:
            >>> data = result.to_dict()
            >>> data['similarity_score']
            85.5
        """
        return {
            'video1_path': str(self.video1_path),
            'video2_path': str(self.video2_path),
            'video1_name': self.video1_path.name,
            'video2_name': self.video2_path.name,
            'similarity_score': round(self.similarity_score, 2),
            'is_duplicate': self.is_duplicate,
            'algorithm_results': [
                algo.to_dict() for algo in self.algorithm_results
            ],
            'pipeline_name': self.pipeline_name,
            'execution_time_ms': round(self.execution_time_ms, 2),
            'execution_time_seconds': round(self.execution_time_ms / 1000, 2),
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'statistics': self.get_execution_summary()
        }

    def to_json(self, indent: int = 2) -> str:
        """
        Export ComparisonResult to JSON string.

        Args:
            indent: Number of spaces for JSON indentation (default: 2)

        Returns:
            JSON string representation

        Example:
            >>> json_str = result.to_json(indent=2)
            >>> 'similarity_score' in json_str
            True
        """
        return json.dumps(self.to_dict(), indent=indent)

    def get_best_algorithm(self) -> AlgorithmResult:
        """
        Get the algorithm with the highest similarity score.

        Returns:
            AlgorithmResult with highest similarity

        Raises:
            ValueError: If no algorithm results are available

        Example:
            >>> best = result.get_best_algorithm()
            >>> best.similarity >= 0
            True
        """
        if not self.algorithm_results:
            raise ValueError("No algorithm results available")

        return max(self.algorithm_results, key=lambda x: x.similarity)

    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for the comparison execution.

        Returns:
            Dictionary with execution statistics

        Example:
            >>> summary = result.get_execution_summary()
            >>> 'algorithms_used' in summary
            True
        """
        if not self.algorithm_results:
            return {
                'algorithms_used': 0,
                'algorithms_accepted': 0,
                'avg_similarity': 0.0,
                'total_execution_time_ms': round(self.execution_time_ms, 2)
            }

        accepted_count = sum(1 for algo in self.algorithm_results if algo.accepted)
        avg_similarity = sum(algo.similarity for algo in self.algorithm_results) / len(self.algorithm_results)

        return {
            'algorithms_used': len(self.algorithm_results),
            'algorithms_accepted': accepted_count,
            'avg_similarity': round(avg_similarity, 2),
            'total_execution_time_ms': round(self.execution_time_ms, 2),
            'avg_time_per_algorithm_ms': round(
                self.execution_time_ms / len(self.algorithm_results), 2
            ) if self.algorithm_results else 0
        }
