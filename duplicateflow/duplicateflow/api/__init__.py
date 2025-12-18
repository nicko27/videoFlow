"""
Unified API for DuplicateFlow - Used by both CLI and GUI.

This module provides a clean, stable API for video duplicate detection
that can be used by:
- CLI commands (duplicateflow/cli/main.py)
- GUI application (src/plugins/duplicate_finder)
- External integrations
"""

from .detection import (
    DetectionEngine,
    DetectionMode,
    DetectionResult,
    MatchResult
)
from .algorithms import AlgorithmRegistry
from .pipelines import PipelineRegistry

__all__ = [
    'DetectionEngine',
    'DetectionMode',
    'DetectionResult',
    'MatchResult',
    'AlgorithmRegistry',
    'PipelineRegistry'
]
