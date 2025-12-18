"""
MD5 hashing utilities for video files.

This module provides efficient MD5 hashing for video files:
- compute_file_md5: Full MD5 hash by chunks
- compute_file_md5_fast: Fast MD5 hash from samples (beginning, middle, end)
- FileHashCache: In-memory LRU cache for hash results

The MD5 hash is used as the primary key for:
- Cache storage (frames, results)
- Duplicate detection
- Cross-session file identification
"""

import hashlib
from pathlib import Path
from typing import Optional, Dict, Tuple
from functools import lru_cache


def compute_file_md5(file_path: str, chunk_size: int = 8192) -> str:
    """
    Compute full MD5 hash of a file by reading chunks.

    This method reads the entire file sequentially in chunks to avoid
    loading large files into memory. Suitable for definitive hashing.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read (bytes, default 8KB)

    Returns:
        MD5 hash as hexadecimal string (32 characters)

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read

    Example:
        >>> md5 = compute_file_md5("/path/to/video.mp4")
        >>> print(md5)
        'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'

    Performance:
        - Speed: ~500 MB/s (depends on disk)
        - For 5GB file: ~10 seconds
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    md5 = hashlib.md5()

    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            md5.update(chunk)

    return md5.hexdigest()


def compute_file_md5_fast(
    file_path: str,
    sample_size: int = 1024 * 1024  # 1MB
) -> str:
    """
    Compute fast MD5 hash by sampling beginning, middle, and end.

    This method reads only 3 samples from the file (beginning, middle, end)
    plus the file size, making it much faster for large files. Suitable for
    quick duplicate detection and pre-filtering.

    ⚠️  Warning: Less robust than full MD5. Two different files could
    theoretically have the same fast hash if they differ only in un-sampled
    regions. Use full MD5 for confirmation.

    Args:
        file_path: Path to the file
        sample_size: Size of each sample (bytes, default 1MB)

    Returns:
        MD5 hash as hexadecimal string (32 characters)

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read

    Example:
        >>> md5_fast = compute_file_md5_fast("/path/to/large_video.mp4")
        >>> print(md5_fast)
        'x1y2z3a4b5c6d7e8f9g0h1i2j3k4l5m6'

    Performance:
        - Speed: ~5 GB/s (reads only 3MB total)
        - For 5GB file: ~0.001 seconds (3MB read)

    Use cases:
        1. Quick duplicate scan of large directory
        2. Pre-filtering before full MD5
        3. Cache key generation when speed matters
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = file_path.stat().st_size
    md5 = hashlib.md5()

    with open(file_path, 'rb') as f:
        # Sample 1: Beginning
        f.seek(0)
        md5.update(f.read(sample_size))

        # Sample 2: Middle
        if file_size > sample_size * 2:
            f.seek(file_size // 2)
            md5.update(f.read(sample_size))

        # Sample 3: End
        if file_size > sample_size * 3:
            f.seek(max(0, file_size - sample_size))
            md5.update(f.read(sample_size))

    # Include file size to differentiate files with similar content
    md5.update(str(file_size).encode())

    return md5.hexdigest()


class FileHashCache:
    """
    In-memory LRU cache for file MD5 hashes.

    This cache stores MD5 hashes keyed by (file_path, mtime, size, method)
    to avoid recomputing hashes for unchanged files. Uses LRU eviction
    when max_size is reached.

    Attributes:
        max_size: Maximum number of cached hashes (default 1000)

    Example:
        >>> cache = FileHashCache(max_size=1000)
        >>>
        >>> # First call: computes hash
        >>> hash1 = cache.get_hash("/path/to/video.mp4", method="full")
        >>>
        >>> # Second call: returns from cache (instant)
        >>> hash2 = cache.get_hash("/path/to/video.mp4", method="full")
        >>> assert hash1 == hash2
        >>>
        >>> # File modified: recomputes hash
        >>> # (detected via mtime change)
        >>> hash3 = cache.get_hash("/path/to/video.mp4", method="full")
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize the hash cache.

        Args:
            max_size: Maximum number of cached entries
        """
        self.max_size = max_size
        self._cache: Dict[Tuple, str] = {}
        self._access_order: list = []

    def get_hash(
        self,
        file_path: str,
        method: str = "full"
    ) -> str:
        """
        Get MD5 hash of a file (with caching).

        The cache key includes file path, modification time, size, and method.
        If the file hasn't changed (same mtime and size), returns cached hash.

        Args:
            file_path: Path to the file
            method: Hash method ("full" or "fast")

        Returns:
            MD5 hash as hexadecimal string

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If method is invalid
        """
        if method not in ("full", "fast"):
            raise ValueError(f"Invalid method: {method}. Use 'full' or 'fast'")

        # Build cache key: (path, mtime, size, method)
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = file_path_obj.stat()
        cache_key = (str(file_path), stat.st_mtime, stat.st_size, method)

        # Check cache
        if cache_key in self._cache:
            # Move to end (LRU)
            self._access_order.remove(cache_key)
            self._access_order.append(cache_key)
            return self._cache[cache_key]

        # Compute hash
        if method == "full":
            hash_value = compute_file_md5(file_path)
        else:  # fast
            hash_value = compute_file_md5_fast(file_path)

        # Store in cache
        self._cache[cache_key] = hash_value
        self._access_order.append(cache_key)

        # Evict oldest if cache full
        if len(self._cache) > self.max_size:
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]

        return hash_value

    def clear(self) -> None:
        """Clear all cached hashes."""
        self._cache.clear()
        self._access_order.clear()

    def size(self) -> int:
        """Get number of cached entries."""
        return len(self._cache)

    def stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats:
            - size: Current number of entries
            - max_size: Maximum capacity
            - hit_rate: Not tracked (would require instrumentation)
        """
        return {
            'size': len(self._cache),
            'max_size': self.max_size
        }


@lru_cache(maxsize=1000)
def get_video_hash_cached(file_path: str, method: str = "full") -> str:
    """
    Get video hash with automatic caching via @lru_cache.

    This is a simpler alternative to FileHashCache that uses Python's
    built-in LRU cache. However, it doesn't check for file modifications.

    Warning: This cache doesn't invalidate when files change. Use
    FileHashCache if files may be modified.

    Args:
        file_path: Path to video file
        method: Hash method ("full" or "fast")

    Returns:
        MD5 hash

    Example:
        >>> hash1 = get_video_hash_cached("/path/to/video.mp4")
        >>> hash2 = get_video_hash_cached("/path/to/video.mp4")  # From cache
    """
    if method == "full":
        return compute_file_md5(file_path)
    elif method == "fast":
        return compute_file_md5_fast(file_path)
    else:
        raise ValueError(f"Invalid method: {method}")


def compute_pair_hash(
    file1_md5: str,
    file2_md5: str,
    pipeline_name: str
) -> str:
    """
    Compute hash for a verification pair.

    This hash uniquely identifies a verification operation for caching.
    Format: MD5(file1_md5 + file2_md5 + pipeline_name)

    Args:
        file1_md5: MD5 of first video
        file2_md5: MD5 of second video
        pipeline_name: Name of pipeline used

    Returns:
        MD5 hash as hexadecimal string

    Example:
        >>> pair_hash = compute_pair_hash(
        ...     "a1b2c3d4...",
        ...     "x1y2z3a4...",
        ...     "accurate"
        ... )
        >>> print(pair_hash)
        'f5e4d3c2b1a9...'
    """
    key = f"{file1_md5}:{file2_md5}:{pipeline_name}"
    return hashlib.md5(key.encode()).hexdigest()


def verify_file_hash(file_path: str, expected_md5: str) -> bool:
    """
    Verify that a file matches an expected MD5 hash.

    Args:
        file_path: Path to file
        expected_md5: Expected MD5 hash

    Returns:
        True if hash matches, False otherwise

    Example:
        >>> is_valid = verify_file_hash(
        ...     "/path/to/video.mp4",
        ...     "a1b2c3d4e5f6..."
        ... )
        >>> if is_valid:
        ...     print("File integrity verified")
    """
    actual_md5 = compute_file_md5(file_path)
    return actual_md5.lower() == expected_md5.lower()
