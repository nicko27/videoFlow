"""
Unified storage management for DuplicateFlow.

This module provides a single interface for all caching operations:
- File hashing (MD5)
- Result caching (algorithm comparisons)
- Statistics and monitoring
"""

from pathlib import Path
from typing import Dict, Any, Optional

from duplicateflow.utils.hashing import FileHashCache, compute_file_md5, compute_file_md5_fast
from duplicateflow.storage.result_cache import ResultCache
from duplicateflow.storage.feature_cache import FeatureCache


class StorageManager:
    """
    Unified interface for all storage operations.

    Combines file hashing and result caching into a single,
    easy-to-use interface with statistics and monitoring.

    Example:
        >>> storage = StorageManager(
        ...     cache_dir="~/.duplicateflow/cache",
        ...     max_memory_items=2000
        ... )
        >>>
        >>> # Get file hash
        >>> hash1 = storage.get_file_hash("/path/to/video.mp4")
        >>>
        >>> # Check for duplicates
        >>> if storage.are_files_identical(file1, file2):
        ...     print("Obvious duplicates!")
        >>>
        >>> # Get cached result
        >>> result = storage.get_cached_result(
        ...     file1, file2, "color_histogram", {'threshold': 70.0}
        ... )
        >>>
        >>> # Store result
        >>> storage.store_result(
        ...     file1, file2, "color_histogram", {'threshold': 70.0},
        ...     {'similarity': 0.85, 'accepted': True}
        ... )
        >>>
        >>> # Get stats
        >>> stats = storage.get_stats()
        >>> print(f"Results cached: {stats['result_cache']['total_entries']}")
    """

    def __init__(
        self,
        cache_dir: str = "~/.duplicateflow/cache",
        max_memory_items: int = 2000
    ):
        """
        Initialize storage manager.

        Args:
            cache_dir: Directory for cache files
            max_memory_items: Maximum items in memory cache
        """
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize hash cache
        self.hash_cache = FileHashCache(max_size=max_memory_items)

        # Initialize result cache
        result_db = self.cache_dir / "results.db"
        self.result_cache = ResultCache(str(result_db))

        # Initialize feature cache
        feature_db = self.cache_dir / "features.db"
        self.feature_cache = FeatureCache(str(feature_db))

        # Statistics
        self._stats = {
            'hash_cache_hits': 0,
            'hash_cache_misses': 0,
            'result_cache_hits': 0,
            'result_cache_misses': 0,
            'feature_cache_hits': 0,
            'feature_cache_misses': 0
        }

    def get_file_hash(
        self,
        file_path: str,
        method: str = "full"
    ) -> str:
        """
        Get MD5 hash of file (with caching).

        Args:
            file_path: Path to file
            method: Hash method ("full" or "fast")

        Returns:
            MD5 hash string

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If method invalid
        """
        try:
            # Try to get from cache
            file_hash = self.hash_cache.get_hash(file_path, method=method)
            self._stats['hash_cache_hits'] += 1
            return file_hash

        except FileNotFoundError:
            raise

        except Exception:
            # Cache miss or error, compute directly
            self._stats['hash_cache_misses'] += 1

            if method == "full":
                return compute_file_md5(file_path)
            else:
                return compute_file_md5_fast(file_path)

    def are_files_identical(
        self,
        file1: str,
        file2: str,
        method: str = "fast"
    ) -> bool:
        """
        Check if two files are identical (same hash).

        Args:
            file1: Path to first file
            file2: Path to second file
            method: Hash method ("full" or "fast")

        Returns:
            True if files have same hash
        """
        hash1 = self.get_file_hash(file1, method=method)
        hash2 = self.get_file_hash(file2, method=method)

        return hash1 == hash2

    def get_cached_result(
        self,
        file1: str,
        file2: str,
        algorithm: str,
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached algorithm result.

        Args:
            file1: Path to first file
            file2: Path to second file
            algorithm: Algorithm name
            params: Algorithm parameters

        Returns:
            Result dictionary or None if not cached
        """
        # Get file hashes
        file1_hash = self.get_file_hash(file1, method="fast")
        file2_hash = self.get_file_hash(file2, method="fast")

        # Query result cache
        result = self.result_cache.get(
            file1_hash, file2_hash, algorithm, params
        )

        if result is not None:
            self._stats['result_cache_hits'] += 1
        else:
            self._stats['result_cache_misses'] += 1

        return result

    def store_result(
        self,
        file1: str,
        file2: str,
        algorithm: str,
        params: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """
        Store algorithm result in cache.

        Args:
            file1: Path to first file
            file2: Path to second file
            algorithm: Algorithm name
            params: Algorithm parameters
            result: Result dictionary
        """
        # Get file hashes
        file1_hash = self.get_file_hash(file1, method="fast")
        file2_hash = self.get_file_hash(file2, method="fast")

        # Store in result cache
        self.result_cache.store(
            file1_hash, file2_hash, algorithm, params, result
        )

    def clear_results(self, algorithm: Optional[str] = None) -> int:
        """
        Clear cached results.

        Args:
            algorithm: Specific algorithm to clear (None = all)

        Returns:
            Number of entries deleted
        """
        if algorithm is None:
            self.result_cache.clear_all()
            return -1  # Unknown count for clear_all
        else:
            return self.result_cache.clear_algorithm(algorithm)

    def clear_old_results(self, days: int) -> int:
        """
        Clear results older than specified days.

        Args:
            days: Number of days

        Returns:
            Number of entries deleted
        """
        return self.result_cache.clear_older_than(days)

    def get_cached_features(
        self,
        file_path: str,
        algorithm: str,
        params: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Get cached extracted features.

        Args:
            file_path: Path to file
            algorithm: Algorithm name
            params: Algorithm parameters

        Returns:
            Cached features or None if not cached
        """
        # Get file hash
        file_hash = self.get_file_hash(file_path, method="fast")

        # Query feature cache
        features = self.feature_cache.get(file_hash, algorithm, params)

        if features is not None:
            self._stats['feature_cache_hits'] += 1
        else:
            self._stats['feature_cache_misses'] += 1

        return features

    def store_features(
        self,
        file_path: str,
        algorithm: str,
        params: Dict[str, Any],
        features: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store extracted features in cache.

        Args:
            file_path: Path to file
            algorithm: Algorithm name
            params: Algorithm parameters
            features: Extracted features
            metadata: Optional metadata
        """
        # Get file hash
        file_hash = self.get_file_hash(file_path, method="fast")

        # Store in feature cache
        self.feature_cache.store(
            file_hash, algorithm, params, features, metadata
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive storage statistics.

        Returns:
            Dictionary with all cache statistics
        """
        result_stats = self.result_cache.get_stats()
        feature_stats = self.feature_cache.get_stats()

        return {
            'hash_cache': {
                'hits': self._stats['hash_cache_hits'],
                'misses': self._stats['hash_cache_misses'],
                'hit_rate': self._calculate_hit_rate(
                    self._stats['hash_cache_hits'],
                    self._stats['hash_cache_misses']
                )
            },
            'result_cache': {
                'hits': self._stats['result_cache_hits'],
                'misses': self._stats['result_cache_misses'],
                'hit_rate': self._calculate_hit_rate(
                    self._stats['result_cache_hits'],
                    self._stats['result_cache_misses']
                ),
                **result_stats
            },
            'feature_cache': {
                'hits': self._stats['feature_cache_hits'],
                'misses': self._stats['feature_cache_misses'],
                'hit_rate': self._calculate_hit_rate(
                    self._stats['feature_cache_hits'],
                    self._stats['feature_cache_misses']
                ),
                **feature_stats
            },
            'cache_dir': str(self.cache_dir)
        }

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage."""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)

    def vacuum(self) -> None:
        """Optimize storage (reclaim space)."""
        self.result_cache.vacuum()

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._stats = {
            'hash_cache_hits': 0,
            'hash_cache_misses': 0,
            'result_cache_hits': 0,
            'result_cache_misses': 0
        }
