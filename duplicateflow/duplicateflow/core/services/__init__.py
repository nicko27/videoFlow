"""
Core services for DuplicateFlow.

This package contains business logic services that use dependency injection:
- ScanService: Directory scanning and video discovery (Phase 1)
- ComparisonService: Video-to-video comparison (Phase 2)
- DuplicateFinderService: N-to-N duplicate detection (Phase 2)
"""

from .scan_service import ScanService, SUPPORTED_VIDEO_EXTENSIONS
from .comparison_service import ComparisonService
from .duplicate_finder_service import DuplicateFinderService

__all__ = [
    "ScanService",
    "SUPPORTED_VIDEO_EXTENSIONS",
    "ComparisonService",
    "DuplicateFinderService",
]
