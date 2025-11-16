"""
LRU (Least Recently Used) Cache implementation for duplicate finder.

Provides an efficient cache with automatic eviction of least recently used items
when the cache reaches its maximum size.
"""

from collections import OrderedDict
from typing import Any, Optional, Tuple
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.LRUCache')


class LRUCache:
    """
    Least Recently Used (LRU) Cache implementation.

    This cache automatically evicts the least recently used items when
    the maximum size is reached. Uses OrderedDict for O(1) operations.

    Attributes:
        max_size: Maximum number of items to store in cache
        cache: OrderedDict storing the cached items
        hits: Number of cache hits (for statistics)
        misses: Number of cache misses (for statistics)

    Example:
        ```python
        cache = LRUCache(max_size=1000)
        cache.set('key1', 'value1')
        value = cache.get('key1')  # Returns 'value1'
        ```
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize the LRU cache.

        Args:
            max_size: Maximum number of items to store (default: 1000)

        Raises:
            ValueError: If max_size is less than 1
        """
        if max_size < 1:
            raise ValueError(f"max_size must be at least 1, got {max_size}")

        self.max_size = max_size
        self.cache = OrderedDict()
        self.hits = 0
        self.misses = 0

        logger.debug(f"LRUCache initialized with max_size={max_size}")

    def get(self, key: Any) -> Optional[Any]:
        """
        Get an item from the cache.

        If the key exists, move it to the end (mark as recently used).

        Args:
            key: The key to look up

        Returns:
            The cached value if found, None otherwise
        """
        if key in self.cache:
            # Move to end (mark as recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]

        self.misses += 1
        return None

    def set(self, key: Any, value: Any) -> None:
        """
        Add or update an item in the cache.

        If the key already exists, update it and move to end.
        If cache is full, evict the least recently used item.

        Args:
            key: The key to store
            value: The value to cache
        """
        if key in self.cache:
            # Update existing key and move to end
            self.cache.move_to_end(key)
            self.cache[key] = value
        else:
            # Add new key
            self.cache[key] = value

            # Evict oldest if cache is full
            if len(self.cache) > self.max_size:
                evicted_key = next(iter(self.cache))
                self.cache.pop(evicted_key)
                logger.debug(f"Evicted LRU item: {evicted_key}")

    def __contains__(self, key: Any) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: The key to check

        Returns:
            True if key exists, False otherwise
        """
        return key in self.cache

    def __len__(self) -> int:
        """
        Get the current number of items in the cache.

        Returns:
            Number of cached items
        """
        return len(self.cache)

    def clear(self) -> None:
        """
        Clear all items from the cache.

        Also resets hit/miss statistics.
        """
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.debug("LRU cache cleared")

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary containing cache statistics:
            - size: Current number of items
            - max_size: Maximum capacity
            - hits: Number of cache hits
            - misses: Number of cache misses
            - hit_rate: Hit rate percentage (0-100)
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate
        }

    def resize(self, new_max_size: int) -> None:
        """
        Resize the cache to a new maximum size.

        If the new size is smaller than current size, evicts oldest items.

        Args:
            new_max_size: New maximum size for the cache

        Raises:
            ValueError: If new_max_size is less than 1
        """
        if new_max_size < 1:
            raise ValueError(f"new_max_size must be at least 1, got {new_max_size}")

        self.max_size = new_max_size

        # Evict items if cache is now too large
        while len(self.cache) > self.max_size:
            evicted_key = next(iter(self.cache))
            self.cache.pop(evicted_key)
            logger.debug(f"Evicted item during resize: {evicted_key}")

        logger.info(f"Cache resized to max_size={new_max_size}, current size={len(self.cache)}")

    def keys(self):
        """
        Get all keys in the cache (most recent last).

        Returns:
            View of cache keys
        """
        return self.cache.keys()

    def values(self):
        """
        Get all values in the cache (most recent last).

        Returns:
            View of cache values
        """
        return self.cache.values()

    def items(self):
        """
        Get all key-value pairs in the cache (most recent last).

        Returns:
            View of cache items
        """
        return self.cache.items()
