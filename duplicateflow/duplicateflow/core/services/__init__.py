"""
Core services for DuplicateFlow.

This package contains business logic services that use dependency injection:
- ScanService: Directory scanning and video discovery
"""

from .scan_service import ScanService, SUPPORTED_VIDEO_EXTENSIONS

__all__ = [
    "ScanService",
    "SUPPORTED_VIDEO_EXTENSIONS",
]
