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
]
