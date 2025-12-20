"""
Core data models for DuplicateFlow.

This module defines the fundamental data structures used throughout the system:
- VerificationResult: Complete result of a video pair verification
- MethodResult: Result of a single algorithm execution
- VerificationStatus: Enum for verification outcomes
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional


class VerificationStatus(str, Enum):
    """
    Status of a verification operation.

    Attributes:
        CONFIRMED: Videos are duplicates/similar (score above threshold)
        REJECTED: Videos are not duplicates (score below threshold)
        SKIPPED: Verification skipped (error, unsupported format, etc.)
    """
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class MethodResult:
    """
    Result of a single algorithm execution.

    Contains all information about one algorithm's comparison:
    - Score and threshold
    - Execution time
    - Accept/reject decision
    - Algorithm-specific metadata

    Attributes:
        method_name: Unique algorithm name (e.g., "optical_flow")
        score: Similarity score (0-100)
        threshold: Threshold used for this method
        accepted: True if score >= threshold
        execution_time_ms: Execution time in milliseconds
        weight: Weight used in pipeline (for weighting mode)
        metadata: Algorithm-specific data (e.g., frames analyzed, features detected)

    Example:
        >>> result = MethodResult(
        ...     method_name="optical_flow",
        ...     score=85.3,
        ...     threshold=70.0,
        ...     accepted=True,
        ...     execution_time_ms=1234.5,
        ...     weight=0.25,
        ...     metadata={"frames_analyzed": 30, "mean_flow": 0.82}
        ... )
    """
    method_name: str
    score: float
    threshold: float
    accepted: bool
    execution_time_ms: float
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MethodResult':
        """Create MethodResult from dictionary."""
        return cls(**data)


@dataclass(frozen=True)
class VerificationResult:
    """
    Complete result of a video pair verification.

    This is the main output of a pipeline execution, containing:
    - Global verification status and score
    - Individual algorithm results
    - Timing information
    - Metadata about the verification

    Attributes:
        file1: Path to short video (scene)
        file2: Path to long video (movie)
        status: CONFIRMED, REJECTED, or SKIPPED
        global_score: Weighted average score (0-100)
        method_results: List of individual algorithm results
        total_execution_time_ms: Total time in milliseconds
        timestamp: When verification was performed
        pipeline_name: Name of pipeline used
        skip_reason: Reason if status is SKIPPED (optional)
        metadata: Additional information (cache hits, errors, etc.)

    Example:
        >>> result = VerificationResult(
        ...     file1="/path/to/scene.mp4",
        ...     file2="/path/to/movie.mp4",
        ...     status=VerificationStatus.CONFIRMED,
        ...     global_score=87.5,
        ...     method_results=[method_result1, method_result2],
        ...     total_execution_time_ms=5432.1,
        ...     timestamp=datetime.now(),
        ...     pipeline_name="accurate",
        ...     metadata={"cache_hits": 2}
        ... )
    """
    file1: str
    file2: str
    status: VerificationStatus
    global_score: float
    method_results: List[MethodResult]
    total_execution_time_ms: float
    timestamp: datetime
    pipeline_name: str
    skip_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all fields, including nested MethodResults
        """
        result = asdict(self)
        # Convert status enum to string
        result['status'] = self.status.value
        # Convert timestamp to ISO format
        result['timestamp'] = self.timestamp.isoformat()
        # Convert method_results (already dicts thanks to asdict)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VerificationResult':
        """
        Create VerificationResult from dictionary.

        Args:
            data: Dictionary with VerificationResult fields

        Returns:
            VerificationResult instance
        """
        # Convert status string to enum
        data['status'] = VerificationStatus(data['status'])

        # Convert timestamp string to datetime
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])

        # Convert method_results dicts to MethodResult objects
        if 'method_results' in data and data['method_results']:
            data['method_results'] = [
                MethodResult.from_dict(mr) if isinstance(mr, dict) else mr
                for mr in data['method_results']
            ]

        return cls(**data)

    def get_method_result(self, method_name: str) -> Optional[MethodResult]:
        """
        Get result for a specific algorithm.

        Args:
            method_name: Algorithm name to search for

        Returns:
            MethodResult if found, None otherwise
        """
        for mr in self.method_results:
            if mr.method_name == method_name:
                return mr
        return None

    def get_execution_times(self) -> Dict[str, float]:
        """
        Get execution times for all methods.

        Returns:
            Dictionary mapping method_name to execution_time_ms
        """
        return {
            mr.method_name: mr.execution_time_ms
            for mr in self.method_results
        }

    def get_scores(self) -> Dict[str, float]:
        """
        Get scores for all methods.

        Returns:
            Dictionary mapping method_name to score
        """
        return {
            mr.method_name: mr.score
            for mr in self.method_results
        }

    def is_duplicate(self) -> bool:
        """
        Check if videos are duplicates.

        Returns:
            True if status is CONFIRMED
        """
        return self.status == VerificationStatus.CONFIRMED

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"VerificationResult("
            f"status={self.status.value}, "
            f"score={self.global_score:.1f}, "
            f"methods={len(self.method_results)}, "
            f"time={self.total_execution_time_ms/1000:.2f}s"
            f")"
        )
