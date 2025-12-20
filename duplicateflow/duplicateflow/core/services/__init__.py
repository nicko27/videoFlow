"""
Core services for DuplicateFlow.

This package contains business logic services that use dependency injection:
- ScanService: Directory scanning and video discovery (Phase 1)
- ComparisonService: Video-to-video comparison (Phase 2)
- DuplicateFinderService: N-to-N duplicate detection (Phase 2)
- BenchmarkService: Performance and accuracy benchmarking (Phase 3)
- PipelineManagementService: Pipeline configuration management (Phase 4)
"""

from .scan_service import ScanService, SUPPORTED_VIDEO_EXTENSIONS
from .comparison_service import ComparisonService
from .duplicate_finder_service import DuplicateFinderService
from .benchmark_service import BenchmarkService
from .pipeline_management_service import PipelineManagementService

__all__ = [
    "ScanService",
    "SUPPORTED_VIDEO_EXTENSIONS",
    "ComparisonService",
    "DuplicateFinderService",
    "BenchmarkService",
    "PipelineManagementService",
]
