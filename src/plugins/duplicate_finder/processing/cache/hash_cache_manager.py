"""
Hash Cache Manager - Unified hash caching system.

Provides persistent file-based caching for ALL video hashes (pHash, dHash, aHash)
with automatic invalidation based on file modification time.
"""

import os
import pickle
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.HashCacheManager')


class HashCacheManager:
    """
    Unified hash cache manager using pickle files.

    Replaces database storage for video hashes with persistent file cache.
    Each video's hash is stored in a separate pickle file for efficient
    access and automatic invalidation.

    Features:
        - Persistent cache across restarts
        - Automatic invalidation on file modification
        - Support for multiple hash methods (pHash, dHash, aHash)
        - Parameter-aware caching (different params = different cache)
        - Thread-safe operations
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize hash cache manager.

        Args:
            cache_dir: Cache directory (default: ~/.duplicate_finder/cache/hashes)
        """
        if cache_dir is None:
            cache_dir = Path.home() / '.duplicate_finder' / 'cache' / 'hashes'

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"HashCacheManager initialized: {self.cache_dir}")

    def _compute_cache_key(
        self,
        video_path: str,
        method: str = 'phash',
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Compute cache key for a video hash.

        The cache key includes:
        - Video file SHA256 (first 16 chars)
        - Hash method name
        - Parameters hash (if provided)

        This ensures different parameters create different cache entries.

        Args:
            video_path: Path to video file
            method: Hash method ('phash', 'dhash', 'ahash')
            parameters: Optional parameters dict

        Returns:
            Cache filename (e.g., "video_abc123_phash_def456.pkl")
        """
        # Compute video file hash (for cache key)
        try:
            with open(video_path, 'rb') as f:
                # Read first 1MB for hash (fast enough, unique enough)
                video_hash = hashlib.sha256(f.read(1024 * 1024)).hexdigest()[:16]
        except Exception:
            # Fallback: use absolute path hash
            video_hash = hashlib.sha256(video_path.encode()).hexdigest()[:16]

        # Compute parameters hash if provided
        if parameters:
            import json
            params_str = json.dumps(parameters, sort_keys=True)
            params_hash = hashlib.sha1(params_str.encode()).hexdigest()[:8]
            cache_key = f"video_{video_hash}_{method}_{params_hash}.pkl"
        else:
            cache_key = f"video_{video_hash}_{method}_default.pkl"

        return cache_key

    def get_hash(
        self,
        video_path: str,
        method: str = 'phash',
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[Tuple[Any, float]]:
        """
        Get cached hash for a video.

        Automatically invalidates cache if file has been modified.

        Args:
            video_path: Path to video file
            method: Hash method
            parameters: Optional parameters

        Returns:
            Tuple of (hash_array, duration) if cached and valid, None otherwise
        """
        cache_key = self._compute_cache_key(video_path, method, parameters)
        cache_file = self.cache_dir / cache_key

        if not cache_file.exists():
            return None

        try:
            # Load cache entry
            with open(cache_file, 'rb') as f:
                cache_entry = pickle.load(f)

            # Validate file hasn't changed
            current_mtime = os.path.getmtime(video_path)
            current_size = os.path.getsize(video_path)

            cached_mtime = cache_entry.get('mtime', 0)
            cached_size = cache_entry.get('file_size', 0)

            # Check if file modified (mtime OR size changed)
            if abs(current_mtime - cached_mtime) >= 1 or current_size != cached_size:
                logger.debug(f"Cache invalidated (file modified): {os.path.basename(video_path)}")
                cache_file.unlink()  # Delete invalid cache
                return None

            # Cache hit!
            logger.debug(f"Cache hit: {os.path.basename(video_path)} ({method})")
            return cache_entry['hash'], cache_entry['duration']

        except Exception as e:
            logger.warning(f"Failed to load cache for {video_path}: {e}")
            # Delete corrupted cache file
            if cache_file.exists():
                cache_file.unlink()
            return None

    def store_hash(
        self,
        video_path: str,
        hash_array: Any,
        duration: float,
        method: str = 'phash',
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Store hash in cache.

        Args:
            video_path: Path to video file
            hash_array: Computed hash (numpy array)
            duration: Video duration in seconds
            method: Hash method
            parameters: Optional parameters
        """
        cache_key = self._compute_cache_key(video_path, method, parameters)
        cache_file = self.cache_dir / cache_key

        try:
            # Get file metadata
            mtime = os.path.getmtime(video_path)
            file_size = os.path.getsize(video_path)

            # Create cache entry
            cache_entry = {
                'hash': hash_array,
                'duration': duration,
                'mtime': mtime,
                'file_size': file_size,
                'method': method,
                'parameters': parameters or {},
                'video_path': video_path,  # For debugging
            }

            # Save to pickle file
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_entry, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.debug(f"Hash cached: {os.path.basename(video_path)} ({method})")

        except Exception as e:
            logger.warning(f"Failed to cache hash for {video_path}: {e}")

    def invalidate(self, video_path: str, method: str = 'phash', parameters: Optional[Dict[str, Any]] = None):
        """
        Invalidate cache for a specific video/method/params combination.

        Args:
            video_path: Path to video file
            method: Hash method
            parameters: Optional parameters
        """
        cache_key = self._compute_cache_key(video_path, method, parameters)
        cache_file = self.cache_dir / cache_key

        if cache_file.exists():
            cache_file.unlink()
            logger.debug(f"Cache invalidated: {os.path.basename(video_path)} ({method})")

    def clear_all(self):
        """Clear all cached hashes."""
        count = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink()
            count += 1
        logger.info(f"Cleared {count} cached hashes")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache statistics (count, total_size, etc.)
        """
        cache_files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in cache_files)

        return {
            'cache_dir': str(self.cache_dir),
            'count': len(cache_files),
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'total_size_bytes': total_size,
        }
