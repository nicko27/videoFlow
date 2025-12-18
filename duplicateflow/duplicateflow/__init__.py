"""
DuplicateFlow - Video Duplicate Detection CLI

A powerful CLI tool for detecting video subsequences (20min-1h) in longer videos
(several hours) using 13 free algorithms.

Features:
- MD5-based caching for fast duplicate detection
- 13 algorithms (statistical, structural, temporal, perceptual, audio, hybrid)
- Pipeline system with weighted scoring
- 6 presets (fast, balanced, thorough, multimodal, structural, hybrid)
- 100% free and open-source

Usage:
    from duplicateflow.pipeline import Pipeline

    pipeline = Pipeline.from_preset('balanced')
    result = pipeline.compare('short.mp4', 'long.mp4')
    print(f"Score: {result['global_score']:.1f}%")

Architecture:
- core: Models, registry, algorithm base
- sdk: Base classes for algorithm plugins
- algorithms: 13 built-in free algorithms
- storage: MD5 cache + SQLite result cache
- pipeline: Multi-algorithm orchestration
- utils: Hashing, video utilities
"""

__version__ = "1.0.0"
__author__ = "DuplicateFlow Team"
__license__ = "MIT"

from duplicateflow.core.models import (
    VerificationResult,
    MethodResult,
    VerificationStatus,
)
from duplicateflow.pipeline import Pipeline, get_preset, list_presets
from duplicateflow.storage import StorageManager

__all__ = [
    "__version__",
    "VerificationResult",
    "MethodResult",
    "VerificationStatus",
    "Pipeline",
    "get_preset",
    "list_presets",
    "StorageManager",
]
