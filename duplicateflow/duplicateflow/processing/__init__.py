"""
Processing modules for optimized video analysis.
"""

from duplicateflow.processing.feature_cache import SegmentFeatureCache
from duplicateflow.processing.parallel_search import ParallelWindowSearch

__all__ = ['SegmentFeatureCache', 'ParallelWindowSearch']
