"""
Unit tests for FeatureCache.

Tests the persistent feature caching system that stores extracted
algorithm features (fingerprints, histograms, etc.) in SQLite with
in-memory caching.
"""

import pytest
import json
import pickle
from pathlib import Path

from duplicateflow.storage.feature_cache import FeatureCache


class TestFeatureCacheInit:
    """Test FeatureCache initialization."""

    def test_init_default_path(self):
        """Test initialization with default database path."""
        cache = FeatureCache()

        assert cache.db_path.exists()
        assert cache.db_path.name == "features.db"
        assert isinstance(cache._memory_cache, dict)
        assert cache._max_memory_items == 100

    def test_init_custom_path(self, tmp_path):
        """Test initialization with custom database path."""
        db_path = tmp_path / "custom" / "features.db"
        cache = FeatureCache(str(db_path))

        assert cache.db_path == db_path
        assert db_path.exists()
        assert db_path.parent.exists()

    def test_init_creates_schema(self, tmp_path):
        """Test that initialization creates database schema."""
        db_path = tmp_path / "test.db"
        cache = FeatureCache(str(db_path))

        # Verify schema exists
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Check table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='features'")
            assert cursor.fetchone() is not None

            # Check indices exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indices = [row[0] for row in cursor.fetchall()]
            assert 'idx_file_hash' in indices
            assert 'idx_algorithm' in indices
            assert 'idx_file_algo' in indices
            assert 'idx_created' in indices


class TestFeatureCacheComputeParamsHash:
    """Test parameter hash computation."""

    def test_compute_params_hash_deterministic(self, tmp_path):
        """Test that same params produce same hash."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        params = {'sr': 11025, 'n_fft': 4096}
        hash1 = cache._compute_params_hash(params)
        hash2 = cache._compute_params_hash(params)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 32  # MD5 hex digest

    def test_compute_params_hash_order_independent(self, tmp_path):
        """Test that parameter order doesn't affect hash."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        params1 = {'sr': 11025, 'n_fft': 4096}
        params2 = {'n_fft': 4096, 'sr': 11025}

        hash1 = cache._compute_params_hash(params1)
        hash2 = cache._compute_params_hash(params2)

        assert hash1 == hash2

    def test_compute_params_hash_different_values(self, tmp_path):
        """Test that different params produce different hashes."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        params1 = {'sr': 11025}
        params2 = {'sr': 22050}

        hash1 = cache._compute_params_hash(params1)
        hash2 = cache._compute_params_hash(params2)

        assert hash1 != hash2


class TestFeatureCacheMakeCacheKey:
    """Test memory cache key generation."""

    def test_make_cache_key_format(self, tmp_path):
        """Test cache key format."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        key = cache._make_cache_key("abc123", "audio_fingerprint", "xyz789")

        assert ":" in key
        assert "abc123" in key
        assert "audio_fingerprint" in key
        assert "xyz789" in key


class TestFeatureCacheStore:
    """Test store method."""

    def test_store_simple_features(self, tmp_path):
        """Test storing simple features."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        features = {'hashes': {123: [1, 2, 3]}, 'num_hashes': 150}
        cache.store(
            file_hash="abc123",
            algorithm="audio_fingerprint",
            params={'sr': 11025, 'n_fft': 4096},
            features=features
        )

        # Verify stored in memory cache
        assert len(cache._memory_cache) == 1

        # Verify stored in database
        import sqlite3
        with sqlite3.connect(tmp_path / "test.db") as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM features')
            assert cursor.fetchone()[0] == 1

    def test_store_with_metadata(self, tmp_path):
        """Test storing features with metadata."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        features = {'hashes': {}, 'num_hashes': 0}
        metadata = {
            'extraction_time_ms': 250.5,
            'num_features': 100
        }

        cache.store(
            file_hash="abc",
            algorithm="test",
            params={},
            features=features,
            metadata=metadata
        )

        # Verify metadata stored
        import sqlite3
        with sqlite3.connect(tmp_path / "test.db") as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT metadata FROM features WHERE file_hash = ?', ("abc",))
            metadata_json = cursor.fetchone()[0]
            stored_metadata = json.loads(metadata_json)
            assert stored_metadata == metadata

    def test_store_update_existing(self, tmp_path):
        """Test that storing again updates existing entry."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        # Store initial
        cache.store("a", "algo", {}, {'hashes': {1: [1, 2]}})

        # Update with different features
        cache.store("a", "algo", {}, {'hashes': {2: [3, 4]}})

        # Should have only 1 entry
        import sqlite3
        with sqlite3.connect(tmp_path / "test.db") as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM features')
            assert cursor.fetchone()[0] == 1

        # Should return updated value
        result = cache.get("a", "algo", {})
        assert result == {'hashes': {2: [3, 4]}}

    def test_store_complex_features(self, tmp_path):
        """Test storing complex nested features."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        complex_features = {
            'histograms': [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            'fingerprints': {
                'hash_1': [1, 2, 3, 4, 5],
                'hash_2': [6, 7, 8, 9, 10]
            },
            'metadata': {
                'duration': 120.5,
                'sample_rate': 44100
            }
        }

        cache.store("file1", "complex_algo", {'param': 'value'}, complex_features)

        # Verify round-trip
        retrieved = cache.get("file1", "complex_algo", {'param': 'value'})
        assert retrieved == complex_features


class TestFeatureCacheGet:
    """Test get method."""

    def test_get_existing_features(self, tmp_path):
        """Test retrieving existing features."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        # Store
        features = {'hashes': {123: [1, 2, 3]}}
        cache.store("a", "algo", {'p': 1}, features)

        # Get
        result = cache.get("a", "algo", {'p': 1})

        assert result is not None
        assert result == features

    def test_get_nonexistent_features(self, tmp_path):
        """Test retrieving non-existent features returns None."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        result = cache.get("nonexist1", "algo", {})

        assert result is None

    def test_get_from_memory_cache(self, tmp_path):
        """Test that get uses memory cache."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        # Store (populates memory cache)
        features = {'data': [1, 2, 3]}
        cache.store("a", "algo", {}, features)

        # Clear database but keep memory cache
        import sqlite3
        with sqlite3.connect(tmp_path / "test.db") as conn:
            conn.execute('DELETE FROM features')
            conn.commit()

        # Should still get from memory cache
        result = cache.get("a", "algo", {})
        assert result is not None
        assert result == features

    def test_get_populates_memory_cache(self, tmp_path):
        """Test that get populates memory cache from database."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        # Store
        features = {'data': 'test'}
        cache.store("a", "algo", {}, features)

        # Clear memory cache
        cache._memory_cache.clear()
        assert len(cache._memory_cache) == 0

        # Get from database
        result = cache.get("a", "algo", {})

        # Should now be in memory cache
        assert len(cache._memory_cache) == 1
        assert result is not None

    def test_get_respects_memory_limit(self, tmp_path):
        """Test that get respects max_memory_items when populating from disk."""
        cache = FeatureCache(str(tmp_path / "test.db"))
        cache._max_memory_items = 2

        # Store 3 features
        for i in range(3):
            cache.store(f"file{i}", "algo", {}, {'data': i})

        # Clear memory cache
        cache._memory_cache.clear()

        # Retrieve all 3
        cache.get("file0", "algo", {})
        cache.get("file1", "algo", {})
        cache.get("file2", "algo", {})

        # Memory cache should not exceed limit
        assert len(cache._memory_cache) <= cache._max_memory_items


class TestFeatureCacheHas:
    """Test has method."""

    def test_has_in_memory_cache(self, tmp_path):
        """Test has returns True when in memory cache."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        cache.store("a", "algo", {}, {'data': 1})

        assert cache.has("a", "algo", {}) is True

    def test_has_in_database_only(self, tmp_path):
        """Test has returns True when in database but not memory."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        cache.store("a", "algo", {}, {'data': 1})

        # Clear memory cache
        cache._memory_cache.clear()

        # Should still find in database
        assert cache.has("a", "algo", {}) is True

    def test_has_not_found(self, tmp_path):
        """Test has returns False when not cached."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        assert cache.has("nonexistent", "algo", {}) is False


class TestFeatureCacheDeleteForFile:
    """Test delete_for_file method."""

    def test_delete_for_file_single(self, tmp_path):
        """Test deleting features for specific file."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        # Store features for different files
        cache.store("file1", "algo1", {}, {'data': 1})
        cache.store("file1", "algo2", {}, {'data': 2})
        cache.store("file2", "algo1", {}, {'data': 3})

        # Delete file1
        deleted = cache.delete_for_file("file1")

        assert deleted == 2

        # Verify file1 gone, file2 still there
        assert cache.get("file1", "algo1", {}) is None
        assert cache.get("file1", "algo2", {}) is None
        assert cache.get("file2", "algo1", {}) is not None

    def test_delete_for_file_clears_memory_cache(self, tmp_path):
        """Test that delete_for_file also clears memory cache."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        cache.store("file1", "algo", {}, {'data': 1})

        # Verify in memory cache
        assert len(cache._memory_cache) == 1

        cache.delete_for_file("file1")

        # Should be cleared from memory too
        assert len(cache._memory_cache) == 0

    def test_delete_for_file_nonexistent(self, tmp_path):
        """Test deleting for file that doesn't exist."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        deleted = cache.delete_for_file("nonexistent")

        assert deleted == 0


class TestFeatureCacheClear:
    """Test clear method."""

    def test_clear_database(self, tmp_path):
        """Test clearing all features from database."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        # Store multiple features
        for i in range(5):
            cache.store(f"file{i}", "algo", {}, {'data': i})

        count = cache.clear()

        assert count == 5

        # Verify database empty
        import sqlite3
        with sqlite3.connect(tmp_path / "test.db") as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM features')
            assert cursor.fetchone()[0] == 0

    def test_clear_memory_cache(self, tmp_path):
        """Test clearing all features from memory cache."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        cache.store("a", "algo", {}, {'data': 1})
        cache.store("b", "algo", {}, {'data': 2})

        assert len(cache._memory_cache) == 2

        cache.clear()

        assert len(cache._memory_cache) == 0


class TestFeatureCacheGetStats:
    """Test get_stats method."""

    def test_get_stats_empty(self, tmp_path):
        """Test stats for empty cache."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        stats = cache.get_stats()

        assert stats['total_entries'] == 0
        assert stats['by_algorithm'] == {}
        assert stats['memory_cache_size'] == 0
        assert 'db_size_bytes' in stats
        assert 'db_size_mb' in stats

    def test_get_stats_with_data(self, tmp_path):
        """Test stats with cached data."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        # Store features for different algorithms
        cache.store("a", "algo1", {}, {'data': 1})
        cache.store("b", "algo1", {}, {'data': 2})
        cache.store("c", "algo2", {}, {'data': 3})

        stats = cache.get_stats()

        assert stats['total_entries'] == 3
        assert stats['by_algorithm']['algo1'] == 2
        assert stats['by_algorithm']['algo2'] == 1
        assert stats['memory_cache_size'] == 3

    def test_get_stats_algorithm_counts(self, tmp_path):
        """Test that stats correctly count by algorithm."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        # Store 5 features for audio, 3 for video
        for i in range(5):
            cache.store(f"a{i}", "audio_fingerprint", {}, {'data': i})

        for i in range(3):
            cache.store(f"v{i}", "video_hash", {}, {'data': i})

        stats = cache.get_stats()

        assert stats['by_algorithm']['audio_fingerprint'] == 5
        assert stats['by_algorithm']['video_hash'] == 3

    def test_get_stats_db_size(self, tmp_path):
        """Test that stats include database size."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        # Store some data
        cache.store("file1", "algo", {}, {'data': [1, 2, 3, 4, 5]})

        stats = cache.get_stats()

        assert stats['db_size_bytes'] > 0
        assert stats['db_size_mb'] == stats['db_size_bytes'] / (1024 * 1024)


class TestFeatureCachePickleSerialization:
    """Test pickle serialization of complex features."""

    def test_pickle_nested_dict(self, tmp_path):
        """Test pickling nested dictionaries."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        nested = {
            'level1': {
                'level2': {
                    'level3': [1, 2, 3, 4, 5]
                }
            }
        }

        cache.store("file", "algo", {}, nested)
        retrieved = cache.get("file", "algo", {})

        assert retrieved == nested

    def test_pickle_mixed_types(self, tmp_path):
        """Test pickling mixed data types."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        mixed = {
            'int': 42,
            'float': 3.14,
            'string': 'test',
            'list': [1, 2, 3],
            'tuple': (4, 5, 6),
            'dict': {'nested': True},
            'bool': True,
            'none': None
        }

        cache.store("file", "algo", {}, mixed)
        retrieved = cache.get("file", "algo", {})

        assert retrieved == mixed
        assert isinstance(retrieved['tuple'], tuple)  # Verify tuple preserved

    def test_pickle_numpy_like_data(self, tmp_path):
        """Test pickling lists that simulate numpy arrays."""
        cache = FeatureCache(str(tmp_path / "test.db"))

        # Simulate numpy array structure
        array_like = {
            'shape': [100, 50],
            'dtype': 'float32',
            'data': [[0.1, 0.2, 0.3]] * 50
        }

        cache.store("file", "algo", {}, array_like)
        retrieved = cache.get("file", "algo", {})

        assert retrieved == array_like
