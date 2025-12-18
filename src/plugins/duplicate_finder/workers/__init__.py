"""
Workers module for duplicate finder.

This module contains worker threads for parallel processing.
"""

from .hash_worker import ParallelHashWorker
from .duplicateflow_worker import DuplicateFlowWorker
from .subsequence_worker import SubsequenceDetectionWorker

# Backward compatibility alias
OptimizedComparisonWorker = DuplicateFlowWorker

__all__ = [
    'ParallelHashWorker',
    'DuplicateFlowWorker',
    'OptimizedComparisonWorker',  # Deprecated: use DuplicateFlowWorker
    'SubsequenceDetectionWorker'
]
