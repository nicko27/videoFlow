"""
Pipeline system for orchestrating multiple algorithms.

This module provides pipeline configuration and execution:
- Pipeline: Multi-algorithm orchestration with weighted scoring
- Presets: Pre-configured pipelines (fast, balanced, thorough, multimodal)
"""

from duplicateflow.pipeline.pipeline import Pipeline
from duplicateflow.pipeline.presets import (
    FAST_PRESET,
    BALANCED_PRESET,
    THOROUGH_PRESET,
    MULTIMODAL_PRESET,
    STRUCTURAL_PRESET,
    HYBRID_PRESET,
    get_preset,
    list_presets
)

__all__ = [
    'Pipeline',
    'FAST_PRESET',
    'BALANCED_PRESET',
    'THOROUGH_PRESET',
    'MULTIMODAL_PRESET',
    'STRUCTURAL_PRESET',
    'HYBRID_PRESET',
    'get_preset',
    'list_presets',
]
