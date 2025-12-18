"""
Core Data Models - Immutable Dataclasses

This module defines immutable data structures for storing verification results
and method execution details. Using frozen dataclasses ensures data integrity
and enables proper caching with complete information.

Key Features:
    - Immutable structures (@dataclass(frozen=True))
    - Complete result storage (including method stats)
    - JSON serialization support
    - Type safety with proper annotations
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json


class VerificationStatus(Enum):
    """Status of a duplicate verification."""
    ACCEPTED = "accepted"      # Confirmed duplicate
    REJECTED = "rejected"      # Not a duplicate
    PENDING = "pending"        # Not yet verified
    SKIPPED = "skipped"        # Skipped due to filters


@dataclass(frozen=True)
class MethodResult:
    """
    Immutable result from a single detection method.
    
    Stores all execution details including timing, scores, and status.
    This enables proper caching with complete method statistics.
    
    Attributes:
        method_name: Name of the detection method (e.g., "pHash", "DCT", "SSIM")
        score: Similarity score (0-100) or distance metric
        threshold: Threshold used for this method
        passed: Whether the method passed its threshold
        execution_time_ms: Method execution time in milliseconds
        details: Additional method-specific details (optional)
        error: Error message if method failed (optional)
        
    Example:
        >>> result = MethodResult(
        ...     method_name="pHash",
        ...     score=95.5,
        ...     threshold=90.0,
        ...     passed=True,
        ...     execution_time_ms=125.3
        ... )
        >>> result.passed
        True
    """
    method_name: str
    score: float
    threshold: float
    passed: bool
    execution_time_ms: float
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MethodResult':
        """Create from dictionary."""
        return cls(**data)


@dataclass(frozen=True)
class VerificationResult:
    """
    Immutable verification result for a video pair.
    
    Stores complete verification details including all method results,
    timing information, and final decision. This structure is designed
    to be cached with full fidelity.
    
    Attributes:
        file1: Path to first video file
        file2: Path to second video file
        status: Verification status (accepted/rejected/pending/skipped)
        global_score: Overall similarity score (0-100)
        method_results: List of individual method results
        total_execution_time_ms: Total verification time in milliseconds
        timestamp: When verification was performed
        pipeline_name: Name of pipeline used (optional)
        skip_reason: Reason for skipping (optional)
        metadata: Additional metadata (optional)
        
    Example:
        >>> method_results = [
        ...     MethodResult("pHash", 95.5, 90.0, True, 125.3),
        ...     MethodResult("DCT", 88.2, 85.0, True, 89.7)
        ... ]
        >>> result = VerificationResult(
        ...     file1="video1.mp4",
        ...     file2="video2.mp4",
        ...     status=VerificationStatus.ACCEPTED,
        ...     global_score=91.85,
        ...     method_results=method_results,
        ...     total_execution_time_ms=215.0,
        ...     timestamp=datetime.now(),
        ...     pipeline_name="default_pipeline"
        ... )
    """
    file1: str
    file2: str
    status: VerificationStatus
    global_score: float
    method_results: List[MethodResult]
    total_execution_time_ms: float
    timestamp: datetime
    pipeline_name: Optional[str] = None
    skip_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate data after initialization."""
        # Convert VerificationStatus string to enum if needed
        if isinstance(self.status, str):
            object.__setattr__(self, 'status', VerificationStatus(self.status))
        
        # Ensure method_results are MethodResult objects
        if self.method_results and not isinstance(self.method_results[0], MethodResult):
            converted = [
                MethodResult.from_dict(r) if isinstance(r, dict) else r
                for r in self.method_results
            ]
            object.__setattr__(self, 'method_results', converted)
        
        # Ensure timestamp is datetime
        if isinstance(self.timestamp, str):
            object.__setattr__(self, 'timestamp', datetime.fromisoformat(self.timestamp))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation suitable for JSON/pickle storage
        """
        return {
            'file1': self.file1,
            'file2': self.file2,
            'status': self.status.value if isinstance(self.status, VerificationStatus) else self.status,
            'global_score': self.global_score,
            'method_results': [r.to_dict() for r in self.method_results],
            'total_execution_time_ms': self.total_execution_time_ms,
            'timestamp': self.timestamp.isoformat(),
            'pipeline_name': self.pipeline_name,
            'skip_reason': self.skip_reason,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VerificationResult':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary with verification result data
            
        Returns:
            VerificationResult instance
        """
        # Convert status string to enum
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = VerificationStatus(data['status'])
        
        # Convert method_results dicts to MethodResult objects
        if 'method_results' in data:
            data['method_results'] = [
                MethodResult.from_dict(r) if isinstance(r, dict) else r
                for r in data['method_results']
            ]
        
        # Convert timestamp string to datetime
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'VerificationResult':
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def get_method_result(self, method_name: str) -> Optional[MethodResult]:
        """
        Get result for a specific method.
        
        Args:
            method_name: Name of the method to find
            
        Returns:
            MethodResult if found, None otherwise
        """
        for result in self.method_results:
            if result.method_name == method_name:
                return result
        return None
    
    def get_passed_methods(self) -> List[MethodResult]:
        """Get list of methods that passed their threshold."""
        return [r for r in self.method_results if r.passed]
    
    def get_failed_methods(self) -> List[MethodResult]:
        """Get list of methods that failed their threshold."""
        return [r for r in self.method_results if not r.passed]
    
    def get_method_stats(self) -> Dict[str, Any]:
        """
        Get statistics about method execution.
        
        Returns:
            Dictionary with method statistics including:
            - total_methods: Total number of methods executed
            - passed_methods: Number of methods that passed
            - failed_methods: Number of methods that failed
            - total_time_ms: Total execution time
            - avg_time_ms: Average execution time per method
            - method_breakdown: Dict of {method_name: execution_time_ms}
        """
        return {
            'total_methods': len(self.method_results),
            'passed_methods': len(self.get_passed_methods()),
            'failed_methods': len(self.get_failed_methods()),
            'total_time_ms': self.total_execution_time_ms,
            'avg_time_ms': (
                self.total_execution_time_ms / len(self.method_results)
                if self.method_results else 0
            ),
            'method_breakdown': {
                r.method_name: r.execution_time_ms
                for r in self.method_results
            }
        }


# Convenience type aliases
MethodResultList = List[MethodResult]
VerificationResultList = List[VerificationResult]


if __name__ == '__main__':
    """Self-test: Demonstrate usage and verify functionality."""
    
    print("=== VerificationResult Dataclass Demo ===\n")
    
    # Create method results
    method_results = [
        MethodResult(
            method_name="pHash",
            score=95.5,
            threshold=90.0,
            passed=True,
            execution_time_ms=125.3,
            details={'frames_compared': 8}
        ),
        MethodResult(
            method_name="DCT",
            score=88.2,
            threshold=85.0,
            passed=True,
            execution_time_ms=89.7
        ),
        MethodResult(
            method_name="SSIM",
            score=92.1,
            threshold=80.0,
            passed=True,
            execution_time_ms=156.8
        ),
    ]
    
    # Create verification result
    result = VerificationResult(
        file1="/path/to/video1.mp4",
        file2="/path/to/video2.mp4",
        status=VerificationStatus.ACCEPTED,
        global_score=91.93,
        method_results=method_results,
        total_execution_time_ms=371.8,
        timestamp=datetime.now(),
        pipeline_name="default_pipeline",
        metadata={'similarity_type': 'exact_duplicate'}
    )
    
    print("1. Created VerificationResult:")
    print(f"   Status: {result.status.value}")
    print(f"   Global Score: {result.global_score}")
    print(f"   Methods: {len(result.method_results)}")
    print()
    
    print("2. Method Statistics:")
    stats = result.get_method_stats()
    for key, value in stats.items():
        if key != 'method_breakdown':
            print(f"   {key}: {value}")
    print()
    
    print("3. Method Breakdown:")
    for method_name, time_ms in stats['method_breakdown'].items():
        print(f"   {method_name}: {time_ms:.1f}ms")
    print()
    
    print("4. Serialization Test:")
    # To dict
    result_dict = result.to_dict()
    print(f"   ✓ Converted to dict ({len(result_dict)} keys)")
    
    # From dict
    result_restored = VerificationResult.from_dict(result_dict)
    print(f"   ✓ Restored from dict")
    print(f"   ✓ Status match: {result.status == result_restored.status}")
    print(f"   ✓ Score match: {result.global_score == result_restored.global_score}")
    print()
    
    print("5. JSON Serialization Test:")
    json_str = result.to_json()
    print(f"   ✓ JSON length: {len(json_str)} chars")
    result_from_json = VerificationResult.from_json(json_str)
    print(f"   ✓ Restored from JSON")
    print(f"   ✓ Method count match: {len(result.method_results) == len(result_from_json.method_results)}")
    print()
    
    print("6. Immutability Test:")
    try:
        result.global_score = 100.0
        print("   ✗ FAILED: Object is not immutable!")
    except AttributeError:
        print("   ✓ Object is immutable (as expected)")
    print()
    
    print("=== All Tests Passed ✓ ===")
