"""
Core data models for DuplicateFlow.

This package contains all data structures used by the core business logic:

From models.py (existing):
- VerificationResult: Result of video pair verification
- MethodResult: Result of single algorithm execution
- VerificationStatus: Enum for verification status

From scan.py (new - Day 2):
- VideoFile: Video file with metadata
- ScanResult: Result of directory scan
- DuplicateGroup: Group of duplicate videos
- VideoFormat: Enum for video formats
"""

# Import existing models from verification.py
from .verification import (
    VerificationResult,
    MethodResult,
    VerificationStatus,
)

# Import new scan models
from .scan import (
    VideoFile,
    ScanResult,
    DuplicateGroup,
    VideoFormat,
)

# Import Phase 2 models
from .algorithm_result import AlgorithmResult
from .comparison import ComparisonResult
from .detection import DetectionResult, DuplicateGroup as DetectionDuplicateGroup

# Import Phase 3 models
from .benchmark import (
    AlgorithmBenchmark,
    PipelineBenchmark,
    ComparisonBenchmark,
    AccuracyMetrics,
    TestSetBenchmark,
)

__all__ = [
    # Existing models
    "VerificationResult",
    "MethodResult",
    "VerificationStatus",
    # New scan models
    "VideoFile",
    "ScanResult",
    "DuplicateGroup",
    "VideoFormat",
    # Phase 2 models
    "AlgorithmResult",
    "ComparisonResult",
    "DetectionResult",
    "DetectionDuplicateGroup",
    # Phase 3 models
    "AlgorithmBenchmark",
    "PipelineBenchmark",
    "ComparisonBenchmark",
    "AccuracyMetrics",
    "TestSetBenchmark",
]
