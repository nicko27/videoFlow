"""
Storage and caching system for DuplicateFlow.

This module provides:
- File hashing (MD5 full/fast) with caching
- Result caching for algorithm comparisons
- Unified storage management interface

Example:
    >>> from duplicateflow.storage import StorageManager
    >>>
    >>> storage = StorageManager()
    >>>
    >>> # Get file hash
    >>> hash1 = storage.get_file_hash("/path/to/video.mp4")
    >>>
    >>> # Check for duplicates
    >>> if storage.are_files_identical(file1, file2):
    ...     print("Files are identical!")
    >>>
    >>> # Cache algorithm result
    >>> storage.store_result(
    ...     file1, file2, "color_histogram",
    ...     params={'threshold': 70.0},
    ...     result={'similarity': 0.85, 'accepted': True}
    ... )
    >>>
    >>> # Retrieve cached result
    >>> result = storage.get_cached_result(
    ...     file1, file2, "color_histogram",
    ...     params={'threshold': 70.0}
    ... )
"""

from duplicateflow.storage.storage_manager import StorageManager
from duplicateflow.storage.result_cache import ResultCache
from duplicateflow.storage.feature_cache import FeatureCache
from duplicateflow.storage.pipeline_store import PipelineStore

__all__ = [
    'StorageManager',
    'ResultCache',
    'FeatureCache',
    'PipelineStore',
]
