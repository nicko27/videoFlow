"""
Workers module for duplicate finder.

This module contains worker threads for parallel processing.
"""

from .hash_worker import ParallelHashWorker
from .comparison_worker import OptimizedComparisonWorker
from .scene_worker import SceneDetectionWorker
from .subsequence_worker import SubsequenceDetectionWorker

__all__ = [
    'ParallelHashWorker',
    'OptimizedComparisonWorker',
    'SceneDetectionWorker',
    'SubsequenceDetectionWorker'
]
