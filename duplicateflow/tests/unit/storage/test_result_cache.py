"""
Unit tests for ResultCache.

Tests the persistent result caching system that stores algorithm
comparison results in SQLite with in-memory caching.
"""

import pytest
import json
from pathlib import Path

from duplicateflow.storage.result_cache import ResultCache


class TestResultCacheInit:
    """Test ResultCache initialization."""

    def test_init_default_path(self):
        """Test initialization with default database path."""
        cache = ResultCache()

        assert cache.db_path.exists()
        assert cache.db_path.name == "results.db"
        assert isinstance(cache._memory_cache, dict)
        assert cache._max_memory_items == 500

    def test_init_custom_path(self, tmp_path):
        """Test initialization with custom database path."""
        db_path = tmp_path / "custom" / "results.db"
        cache = ResultCache(str(db_path))

        assert cache.db_path == db_path
        assert db_path.exists()
        assert db_path.parent.exists()

    def test_init_creates_schema(self, tmp_path):
        """Test that initialization creates database schema."""
        db_path = tmp_path / "test.db"
        cache = ResultCache(str(db_path))

        # Verify schema exists
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Check table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='results'")
            assert cursor.fetchone() is not None

            # Check indices exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indices = [row[0] for row in cursor.fetchall()]
            assert 'idx_files' in indices
            assert 'idx_algorithm' in indices
            assert 'idx_created' in indices


class TestResultCacheComputeParamsHash:
    """Test parameter hash computation."""

    def test_compute_params_hash_deterministic(self, tmp_path):
        """Test that same params produce same hash."""
        cache = ResultCache(str(tmp_path / "test.db"))

        params = {'threshold': 70.0, 'window_size': 10}
        hash1 = cache._compute_params_hash(params)
        hash2 = cache._compute_params_hash(params)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 32  # MD5 hex digest

    def test_compute_params_hash_order_independent(self, tmp_path):
        """Test that parameter order doesn't affect hash."""
        cache = ResultCache(str(tmp_path / "test.db"))

        params1 = {'threshold': 70.0, 'window_size': 10}
        params2 = {'window_size': 10, 'threshold': 70.0}

        hash1 = cache._compute_params_hash(params1)
        hash2 = cache._compute_params_hash(params2)

        assert hash1 == hash2

    def test_compute_params_hash_different_values(self, tmp_path):
        """Test that different params produce different hashes."""
        cache = ResultCache(str(tmp_path / "test.db"))

        params1 = {'threshold': 70.0}
        params2 = {'threshold': 80.0}

        hash1 = cache._compute_params_hash(params1)
        hash2 = cache._compute_params_hash(params2)

        assert hash1 != hash2


class TestResultCacheMakeCacheKey:
    """Test memory cache key generation."""

    def test_make_cache_key_ordering(self, tmp_path):
        """Test that file hashes are consistently ordered."""
        cache = ResultCache(str(tmp_path / "test.db"))

        # Create keys with different ordering
        key1 = cache._make_cache_key("abc", "xyz", "algo", "params")
        key2 = cache._make_cache_key("xyz", "abc", "algo", "params")

        # Should be identical (lexicographically sorted)
        assert key1 == key2

    def test_make_cache_key_format(self, tmp_path):
        """Test cache key format."""
        cache = ResultCache(str(tmp_path / "test.db"))

        key = cache._make_cache_key("hash1", "hash2", "frame_hash", "abc123")

        assert ":" in key
        assert "hash1" in key
        assert "hash2" in key
        assert "frame_hash" in key
        assert "abc123" in key


class TestResultCacheStore:
    """Test store method."""

    def test_store_simple_result(self, tmp_path):
        """Test storing a simple result."""
        cache = ResultCache(str(tmp_path / "test.db"))

        cache.store(
            file1_hash="abc123",
            file2_hash="def456",
            algorithm="frame_hash",
            params={'threshold': 70.0},
            result={'similarity': 0.85, 'accepted': True, 'metadata': {}}
        )

        # Verify stored in memory cache
        assert len(cache._memory_cache) == 1

        # Verify stored in database
        import sqlite3
        with sqlite3.connect(tmp_path / "test.db") as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM results')
            assert cursor.fetchone()[0] == 1

    def test_store_ordering_normalization(self, tmp_path):
        """Test that store normalizes file hash ordering."""
        cache = ResultCache(str(tmp_path / "test.db"))

        # Store with hashes in different order
        cache.store(
            file1_hash="xyz",
            file2_hash="abc",
            algorithm="ssim",
            params={},
            result={'similarity': 0.75, 'accepted': True, 'metadata': {}}
        )

        # Retrieve with opposite ordering
        result = cache.get(
            file1_hash="abc",
            file2_hash="xyz",
            algorithm="ssim",
            params={}
        )

        assert result is not None
        assert result['similarity'] == 0.75

    def test_store_with_metadata(self, tmp_path):
        """Test storing result with metadata."""
        cache = ResultCache(str(tmp_path / "test.db"))

        metadata = {
            'duration': 120.5,
            'frames_compared': 100,
            'offset': 10.5
        }

        cache.store(
            file1_hash="abc",
            file2_hash="def",
            algorithm="test",
            params={},
            result={'similarity': 0.9, 'accepted': True, 'metadata': metadata}
        )

        result = cache.get("abc", "def", "test", {})

        assert result['metadata'] == metadata

    def test_store_update_existing(self, tmp_path):
        """Test that storing again updates existing entry."""
        cache = ResultCache(str(tmp_path / "test.db"))

        # Store initial
        cache.store("a", "b", "algo", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})

        # Update with different result
        cache.store("a", "b", "algo", {}, {'similarity': 0.9, 'accepted': True, 'metadata': {}})

        # Should have only 1 entry
        import sqlite3
        with sqlite3.connect(tmp_path / "test.db") as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM results')
            assert cursor.fetchone()[0] == 1

        # Should return updated value
        result = cache.get("a", "b", "algo", {})
        assert result['similarity'] == 0.9

    def test_store_memory_cache_eviction(self, tmp_path):
        """Test that memory cache evicts old entries when full."""
        cache = ResultCache(str(tmp_path / "test.db"))
        cache._max_memory_items = 10  # Small cache for testing

        # Store 15 results (exceeds max)
        for i in range(15):
            cache.store(
                f"file{i}",
                f"file{i+1}",
                "test",
                {},
                {'similarity': 0.5, 'accepted': False, 'metadata': {}}
            )

        # Memory cache should not exceed max
        assert len(cache._memory_cache) <= cache._max_memory_items


class TestResultCacheGet:
    """Test get method."""

    def test_get_existing_result(self, tmp_path):
        """Test retrieving existing result."""
        cache = ResultCache(str(tmp_path / "test.db"))

        # Store
        cache.store("a", "b", "algo", {'p': 1}, {'similarity': 0.7, 'accepted': True, 'metadata': {}})

        # Get
        result = cache.get("a", "b", "algo", {'p': 1})

        assert result is not None
        assert result['similarity'] == 0.7
        assert result['accepted'] is True

    def test_get_nonexistent_result(self, tmp_path):
        """Test retrieving non-existent result returns None."""
        cache = ResultCache(str(tmp_path / "test.db"))

        result = cache.get("nonexist1", "nonexist2", "algo", {})

        assert result is None

    def test_get_from_memory_cache(self, tmp_path):
        """Test that get uses memory cache."""
        cache = ResultCache(str(tmp_path / "test.db"))

        # Store (populates memory cache)
        cache.store("a", "b", "algo", {}, {'similarity': 0.8, 'accepted': True, 'metadata': {}})

        # Clear database but keep memory cache
        import sqlite3
        with sqlite3.connect(tmp_path / "test.db") as conn:
            conn.execute('DELETE FROM results')
            conn.commit()

        # Should still get from memory cache
        result = cache.get("a", "b", "algo", {})
        assert result is not None
        assert result['similarity'] == 0.8

    def test_get_populates_memory_cache(self, tmp_path):
        """Test that get populates memory cache from database."""
        cache = ResultCache(str(tmp_path / "test.db"))

        # Store
        cache.store("a", "b", "algo", {}, {'similarity': 0.6, 'accepted': False, 'metadata': {}})

        # Clear memory cache
        cache._memory_cache.clear()
        assert len(cache._memory_cache) == 0

        # Get from database
        result = cache.get("a", "b", "algo", {})

        # Should now be in memory cache
        assert len(cache._memory_cache) == 1
        assert result is not None

    def test_get_boolean_conversion(self, tmp_path):
        """Test that accepted is properly converted to boolean."""
        cache = ResultCache(str(tmp_path / "test.db"))

        cache.store("a", "b", "algo", {}, {'similarity': 0.5, 'accepted': True, 'metadata': {}})
        result = cache.get("a", "b", "algo", {})

        assert isinstance(result['accepted'], bool)
        assert result['accepted'] is True


class TestResultCacheClearAlgorithm:
    """Test clear_algorithm method."""

    def test_clear_algorithm_single(self, tmp_path):
        """Test clearing results for specific algorithm."""
        cache = ResultCache(str(tmp_path / "test.db"))

        # Store results for different algorithms
        cache.store("a", "b", "algo1", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})
        cache.store("a", "b", "algo2", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})
        cache.store("c", "d", "algo1", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})

        # Clear algo1
        deleted = cache.clear_algorithm("algo1")

        assert deleted == 2

        # Verify algo1 gone, algo2 still there
        assert cache.get("a", "b", "algo1", {}) is None
        assert cache.get("a", "b", "algo2", {}) is not None

    def test_clear_algorithm_clears_memory_cache(self, tmp_path):
        """Test that clear_algorithm also clears memory cache."""
        cache = ResultCache(str(tmp_path / "test.db"))

        cache.store("a", "b", "test_algo", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})

        # Verify in memory cache
        assert len(cache._memory_cache) == 1

        cache.clear_algorithm("test_algo")

        # Should be cleared from memory too
        assert len(cache._memory_cache) == 0


class TestResultCacheClearOlderThan:
    """Test clear_older_than method."""

    def test_clear_older_than(self, tmp_path):
        """Test clearing old results."""
        cache = ResultCache(str(tmp_path / "test.db"))

        # Store some results
        cache.store("a", "b", "algo", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})
        cache.store("c", "d", "algo", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})

        # Clear entries older than 30 days (should delete nothing for fresh entries)
        deleted = cache.clear_older_than(30)

        # Fresh entries should still be there
        assert deleted == 0

    def test_clear_older_than_clears_memory(self, tmp_path):
        """Test that clear_older_than clears memory cache."""
        cache = ResultCache(str(tmp_path / "test.db"))

        cache.store("a", "b", "algo", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})

        assert len(cache._memory_cache) == 1

        cache.clear_older_than(0)

        # Memory cache should be cleared
        assert len(cache._memory_cache) == 0


class TestResultCacheClearAll:
    """Test clear_all method."""

    def test_clear_all_database(self, tmp_path):
        """Test clearing all results from database."""
        cache = ResultCache(str(tmp_path / "test.db"))

        # Store multiple results
        for i in range(5):
            cache.store(f"file{i}", f"file{i+1}", "algo", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})

        cache.clear_all()

        # Verify database empty
        import sqlite3
        with sqlite3.connect(tmp_path / "test.db") as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM results')
            assert cursor.fetchone()[0] == 0

    def test_clear_all_memory_cache(self, tmp_path):
        """Test clearing all results from memory cache."""
        cache = ResultCache(str(tmp_path / "test.db"))

        cache.store("a", "b", "algo", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})
        cache.store("c", "d", "algo", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})

        assert len(cache._memory_cache) == 2

        cache.clear_all()

        assert len(cache._memory_cache) == 0


class TestResultCacheGetStats:
    """Test get_stats method."""

    def test_get_stats_empty(self, tmp_path):
        """Test stats for empty cache."""
        cache = ResultCache(str(tmp_path / "test.db"))

        stats = cache.get_stats()

        assert stats['total_entries'] == 0
        assert stats['by_algorithm'] == {}
        assert stats['memory_cache_size'] == 0
        assert 'database_size_mb' in stats

    def test_get_stats_with_data(self, tmp_path):
        """Test stats with cached data."""
        cache = ResultCache(str(tmp_path / "test.db"))

        # Store results for different algorithms
        cache.store("a", "b", "algo1", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})
        cache.store("c", "d", "algo1", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})
        cache.store("e", "f", "algo2", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})

        stats = cache.get_stats()

        assert stats['total_entries'] == 3
        assert stats['by_algorithm']['algo1'] == 2
        assert stats['by_algorithm']['algo2'] == 1
        assert stats['memory_cache_size'] == 3

    def test_get_stats_algorithm_counts(self, tmp_path):
        """Test that stats correctly count by algorithm."""
        cache = ResultCache(str(tmp_path / "test.db"))

        # Store 5 results for frame_hash, 3 for ssim
        for i in range(5):
            cache.store(f"a{i}", f"b{i}", "frame_hash", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})

        for i in range(3):
            cache.store(f"c{i}", f"d{i}", "ssim", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})

        stats = cache.get_stats()

        assert stats['by_algorithm']['frame_hash'] == 5
        assert stats['by_algorithm']['ssim'] == 3


class TestResultCacheVacuum:
    """Test vacuum method."""

    def test_vacuum_success(self, tmp_path):
        """Test vacuum operation."""
        cache = ResultCache(str(tmp_path / "test.db"))

        # Store and delete to create fragmentation
        for i in range(10):
            cache.store(f"a{i}", f"b{i}", "algo", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})

        cache.clear_all()

        # Vacuum should succeed without error
        cache.vacuum()

        # Database should still work
        cache.store("test1", "test2", "algo", {}, {'similarity': 0.5, 'accepted': False, 'metadata': {}})
        result = cache.get("test1", "test2", "algo", {})
        assert result is not None
