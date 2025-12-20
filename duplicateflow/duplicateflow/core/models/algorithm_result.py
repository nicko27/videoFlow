"""
Algorithm result model for individual algorithm comparison results.
"""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class AlgorithmResult:
    """
    Result from a single algorithm in a comparison pipeline.

    Attributes:
        algorithm_name: Name of the algorithm that produced this result
        similarity: Similarity score (0-100)
        accepted: Whether this result passed the algorithm's threshold
        weight: Weight assigned to this algorithm in the pipeline
        execution_time_ms: Time taken to execute this algorithm (milliseconds)
        metadata: Additional algorithm-specific metadata

    Example:
        >>> result = AlgorithmResult(
        ...     algorithm_name="frame_hash",
        ...     similarity=85.5,
        ...     accepted=True,
        ...     weight=0.4,
        ...     execution_time_ms=150.5,
        ...     metadata={"frames_compared": 100}
        ... )
        >>> result.similarity
        85.5
    """
    algorithm_name: str
    similarity: float
    accepted: bool
    weight: float
    execution_time_ms: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert AlgorithmResult to dictionary for serialization.

        Returns:
            Dictionary representation of the algorithm result

        Example:
            >>> result.to_dict()
            {
                'algorithm_name': 'frame_hash',
                'similarity': 85.5,
                'accepted': True,
                'weight': 0.4,
                'execution_time_ms': 150.5,
                'metadata': {'frames_compared': 100}
            }
        """
        return {
            'algorithm_name': self.algorithm_name,
            'similarity': round(self.similarity, 2),
            'accepted': self.accepted,
            'weight': round(self.weight, 3),
            'execution_time_ms': round(self.execution_time_ms, 2),
            'metadata': self.metadata
        }
