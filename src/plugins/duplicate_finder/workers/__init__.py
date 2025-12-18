"""
Workers module for duplicate finder.

This module contains worker threads for parallel processing.
"""

from .hash_worker import ParallelHashWorker
from .duplicateflow_worker import DuplicateFlowWorker
from .scene_worker import SceneDetectionWorker
from .subsequence_worker import SubsequenceDetectionWorker

# Backward compatibility alias
OptimizedComparisonWorker = DuplicateFlowWorker

__all__ = [
    'ParallelHashWorker',
    'DuplicateFlowWorker',
    'OptimizedComparisonWorker',  # Deprecated: use DuplicateFlowWorker
    'SceneDetectionWorker',
    'SubsequenceDetectionWorker'
]
