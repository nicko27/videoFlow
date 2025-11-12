"""
Workers module for duplicate finder.

This module contains worker threads for parallel processing.
"""

from .hash_worker import ParallelHashWorker
from .comparison_worker import OptimizedComparisonWorker

__all__ = ['ParallelHashWorker', 'OptimizedComparisonWorker']
