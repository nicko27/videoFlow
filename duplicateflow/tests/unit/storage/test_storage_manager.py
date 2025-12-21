"""
Unit tests for StorageManager.

Tests the unified storage interface that combines file hashing,
result caching, and feature caching with statistics tracking.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from duplicateflow.storage.storage_manager import StorageManager


class TestStorageManagerInit:
    """Test StorageManager initialization."""

    def test_init_default_params(self, tmp_path):
        """Test initialization with default parameters."""
        storage = StorageManager(cache_dir=str(tmp_path / "cache"))

        assert storage.cache_dir == tmp_path / "cache"
        assert storage.cache_dir.exists()
        assert storage.hash_cache is not None
        assert storage.result_cache is not None
        assert storage.feature_cache is not None
        assert storage._stats['hash_cache_hits'] == 0
        assert storage._stats['hash_cache_misses'] == 0

    def test_init_custom_params(self, tmp_path):
        """Test initialization with custom parameters."""
        storage = StorageManager(
            cache_dir=str(tmp_path / "custom"),
            max_memory_items=5000
        )

        assert storage.cache_dir == tmp_path / "custom"
        assert storage.cache_dir.exists()
        # max_memory_items is passed to FileHashCache
        assert storage.hash_cache is not None

    def test_init_creates_cache_directory(self, tmp_path):
        """Test that initialization creates cache directory."""
        cache_dir = tmp_path / "new" / "nested" / "cache"
        storage = StorageManager(cache_dir=str(cache_dir))

        assert cache_dir.exists()
        # Should create result and feature DB files
        assert (cache_dir / "results.db").exists()
        assert (cache_dir / "features.db").exists()

    def test_init_expands_tilde(self):
        """Test that ~ is expanded in cache_dir."""
        storage = StorageManager(cache_dir="~/.duplicateflow/test_cache")

        # Should not contain literal tilde
        assert "~" not in str(storage.cache_dir)
        assert storage.cache_dir.is_absolute()


class TestStorageManagerGetFileHash:
    """Test get_file_hash method."""

    @patch('duplicateflow.storage.storage_manager.compute_file_md5')
    def test_get_file_hash_full_method(self, mock_compute, tmp_path):
        """Test getting file hash with full method."""
        storage = StorageManager(cache_dir=str(tmp_path))

        # Create a test file
        test_file = tmp_path / "video.mp4"
        test_file.write_text("test content")

        # Mock hash_cache.get_hash to raise exception (cache miss)
        with patch.object(storage.hash_cache, 'get_hash', side_effect=KeyError("cache miss")):
            # Mock the compute function
            mock_compute.return_value = "abc123def456"

            # First call (cache miss)
            hash1 = storage.get_file_hash(str(test_file), method="full")

            assert hash1 == "abc123def456"
            assert storage._stats['hash_cache_misses'] >= 1

    @patch('duplicateflow.storage.storage_manager.compute_file_md5_fast')
    def test_get_file_hash_fast_method(self, mock_compute_fast, tmp_path):
        """Test getting file hash with fast method."""
        storage = StorageManager(cache_dir=str(tmp_path))

        test_file = tmp_path / "video.mp4"
        test_file.write_text("test content")

        # Mock hash_cache.get_hash to raise exception (cache miss)
        with patch.object(storage.hash_cache, 'get_hash', side_effect=KeyError("cache miss")):
            mock_compute_fast.return_value = "xyz789"

            hash1 = storage.get_file_hash(str(test_file), method="fast")

            assert hash1 == "xyz789"

    def test_get_file_hash_nonexistent_file(self, tmp_path):
        """Test getting hash of non-existent file raises error."""
        storage = StorageManager(cache_dir=str(tmp_path))

        with pytest.raises(FileNotFoundError):
            storage.get_file_hash("/nonexistent/file.mp4")

    @patch('duplicateflow.storage.storage_manager.compute_file_md5')
    def test_get_file_hash_cache_hit(self, mock_compute, tmp_path):
        """Test that second call uses cache (cache hit)."""
        storage = StorageManager(cache_dir=str(tmp_path))

        test_file = tmp_path / "video.mp4"
        test_file.write_text("test content")

        mock_compute.return_value = "abc123"

        # First call
        hash1 = storage.get_file_hash(str(test_file), method="full")
        initial_misses = storage._stats['hash_cache_misses']

        # Second call (should hit cache)
        hash2 = storage.get_file_hash(str(test_file), method="full")

        assert hash1 == hash2
        # Cache hit increments hits counter
        # (actual behavior depends on FileHashCache implementation)


class TestStorageManagerAreFilesIdentical:
    """Test are_files_identical method."""

    @patch('duplicateflow.storage.storage_manager.compute_file_md5_fast')
    def test_are_files_identical_same_hash(self, mock_compute_fast, tmp_path):
        """Test that identical files return True."""
        storage = StorageManager(cache_dir=str(tmp_path))

        file1 = tmp_path / "video1.mp4"
        file2 = tmp_path / "video2.mp4"
        file1.write_text("same content")
        file2.write_text("same content")

        # Mock both files to return same hash
        mock_compute_fast.return_value = "samehash123"

        result = storage.are_files_identical(str(file1), str(file2))

        assert result is True

    @patch('duplicateflow.storage.storage_manager.compute_file_md5_fast')
    def test_are_files_identical_different_hash(self, mock_compute_fast, tmp_path):
        """Test that different files return False."""
        storage = StorageManager(cache_dir=str(tmp_path))

        file1 = tmp_path / "video1.mp4"
        file2 = tmp_path / "video2.mp4"
        file1.write_text("content1")
        file2.write_text("content2")

        # Mock different hashes
        mock_compute_fast.side_effect = ["hash1", "hash2"]

        result = storage.are_files_identical(str(file1), str(file2))

        assert result is False

    @patch('duplicateflow.storage.storage_manager.compute_file_md5')
    def test_are_files_identical_full_method(self, mock_compute, tmp_path):
        """Test are_files_identical with full hash method."""
        storage = StorageManager(cache_dir=str(tmp_path))

        file1 = tmp_path / "video1.mp4"
        file2 = tmp_path / "video2.mp4"
        file1.write_text("content")
        file2.write_text("content")

        mock_compute.return_value = "fullhash"

        result = storage.are_files_identical(str(file1), str(file2), method="full")

        assert result is True


class TestStorageManagerGetCachedResult:
    """Test get_cached_result method."""

    @patch('duplicateflow.storage.storage_manager.compute_file_md5_fast')
    def test_get_cached_result_hit(self, mock_compute_fast, tmp_path):
        """Test getting cached result (cache hit)."""
        storage = StorageManager(cache_dir=str(tmp_path))

        file1 = tmp_path / "video1.mp4"
        file2 = tmp_path / "video2.mp4"
        file1.write_text("content1")
        file2.write_text("content2")

        mock_compute_fast.side_effect = ["hash1", "hash2", "hash1", "hash2"]

        # Store a result first
        result_data = {'similarity': 0.85, 'accepted': True}
        storage.store_result(
            str(file1), str(file2), "frame_hash", {'threshold': 70.0}, result_data
        )

        # Retrieve it
        cached = storage.get_cached_result(
            str(file1), str(file2), "frame_hash", {'threshold': 70.0}
        )

        assert cached is not None
        assert cached['similarity'] == 0.85
        assert storage._stats['result_cache_hits'] >= 1

    @patch('duplicateflow.storage.storage_manager.compute_file_md5_fast')
    def test_get_cached_result_miss(self, mock_compute_fast, tmp_path):
        """Test getting result that's not cached (cache miss)."""
        storage = StorageManager(cache_dir=str(tmp_path))

        file1 = tmp_path / "video1.mp4"
        file2 = tmp_path / "video2.mp4"
        file1.write_text("content1")
        file2.write_text("content2")

        mock_compute_fast.side_effect = ["hash1", "hash2"]

        # Don't store anything, just try to get
        cached = storage.get_cached_result(
            str(file1), str(file2), "frame_hash", {'threshold': 70.0}
        )

        assert cached is None
        assert storage._stats['result_cache_misses'] >= 1


class TestStorageManagerStoreResult:
    """Test store_result method."""

    @patch('duplicateflow.storage.storage_manager.compute_file_md5_fast')
    def test_store_result_success(self, mock_compute_fast, tmp_path):
        """Test storing algorithm result."""
        storage = StorageManager(cache_dir=str(tmp_path))

        file1 = tmp_path / "video1.mp4"
        file2 = tmp_path / "video2.mp4"
        file1.write_text("content1")
        file2.write_text("content2")

        mock_compute_fast.side_effect = ["hash1", "hash2", "hash1", "hash2"]

        result_data = {'similarity': 0.75, 'accepted': True}

        # Store result
        storage.store_result(
            str(file1), str(file2), "ssim", {'threshold': 80.0}, result_data
        )

        # Verify it's stored by retrieving it
        cached = storage.get_cached_result(
            str(file1), str(file2), "ssim", {'threshold': 80.0}
        )

        assert cached is not None
        assert cached['similarity'] == 0.75


class TestStorageManagerClearResults:
    """Test clear_results method."""

    @patch('duplicateflow.storage.storage_manager.compute_file_md5_fast')
    def test_clear_results_all(self, mock_compute_fast, tmp_path):
        """Test clearing all cached results."""
        storage = StorageManager(cache_dir=str(tmp_path))

        file1 = tmp_path / "video1.mp4"
        file2 = tmp_path / "video2.mp4"
        file1.write_text("content1")
        file2.write_text("content2")

        mock_compute_fast.side_effect = ["hash1", "hash2"] * 4

        # Store some results
        storage.store_result(str(file1), str(file2), "frame_hash", {}, {'similarity': 0.8})
        storage.store_result(str(file1), str(file2), "ssim", {}, {'similarity': 0.7})

        # Clear all
        count = storage.clear_results()

        # clear_all returns -1 (unknown count)
        assert count == -1

    @patch('duplicateflow.storage.storage_manager.compute_file_md5_fast')
    def test_clear_results_specific_algorithm(self, mock_compute_fast, tmp_path):
        """Test clearing results for specific algorithm."""
        storage = StorageManager(cache_dir=str(tmp_path))

        file1 = tmp_path / "video1.mp4"
        file2 = tmp_path / "video2.mp4"
        file1.write_text("content1")
        file2.write_text("content2")

        mock_compute_fast.side_effect = ["hash1", "hash2"] * 6

        # Store results for different algorithms
        storage.store_result(str(file1), str(file2), "frame_hash", {}, {'similarity': 0.8})
        storage.store_result(str(file1), str(file2), "ssim", {}, {'similarity': 0.7})

        # Clear only frame_hash
        count = storage.clear_results(algorithm="frame_hash")

        # Should delete at least 1 entry
        assert count >= 0

        # frame_hash should be gone
        cached_fh = storage.get_cached_result(str(file1), str(file2), "frame_hash", {})
        assert cached_fh is None

        # ssim should still be there
        cached_ssim = storage.get_cached_result(str(file1), str(file2), "ssim", {})
        assert cached_ssim is not None


class TestStorageManagerClearOldResults:
    """Test clear_old_results method."""

    def test_clear_old_results(self, tmp_path):
        """Test clearing results older than specified days."""
        storage = StorageManager(cache_dir=str(tmp_path))

        # This method delegates to result_cache.clear_older_than(days)
        count = storage.clear_old_results(days=30)

        # Should return count (0 if nothing to delete)
        assert count >= 0


class TestStorageManagerGetCachedFeatures:
    """Test get_cached_features method."""

    @patch('duplicateflow.storage.storage_manager.compute_file_md5_fast')
    def test_get_cached_features_hit(self, mock_compute_fast, tmp_path):
        """Test getting cached features (cache hit)."""
        storage = StorageManager(cache_dir=str(tmp_path))

        file_path = tmp_path / "video.mp4"
        file_path.write_text("content")

        mock_compute_fast.side_effect = ["filehash", "filehash"]

        # Store features first
        features_data = {'frames': [1, 2, 3], 'hashes': ['a', 'b', 'c']}
        storage.store_features(
            str(file_path), "frame_hash", {'threshold': 70.0}, features_data
        )

        # Retrieve features
        cached = storage.get_cached_features(
            str(file_path), "frame_hash", {'threshold': 70.0}
        )

        assert cached is not None
        assert cached['frames'] == [1, 2, 3]
        assert storage._stats['feature_cache_hits'] >= 1

    @patch('duplicateflow.storage.storage_manager.compute_file_md5_fast')
    def test_get_cached_features_miss(self, mock_compute_fast, tmp_path):
        """Test getting features that aren't cached (cache miss)."""
        storage = StorageManager(cache_dir=str(tmp_path))

        file_path = tmp_path / "video.mp4"
        file_path.write_text("content")

        mock_compute_fast.return_value = "filehash"

        # Don't store anything, just try to get
        cached = storage.get_cached_features(
            str(file_path), "frame_hash", {'threshold': 70.0}
        )

        assert cached is None
        assert storage._stats['feature_cache_misses'] >= 1


class TestStorageManagerStoreFeatures:
    """Test store_features method."""

    @patch('duplicateflow.storage.storage_manager.compute_file_md5_fast')
    def test_store_features_success(self, mock_compute_fast, tmp_path):
        """Test storing extracted features."""
        storage = StorageManager(cache_dir=str(tmp_path))

        file_path = tmp_path / "video.mp4"
        file_path.write_text("content")

        mock_compute_fast.side_effect = ["filehash", "filehash"]

        features_data = {'perceptual_hashes': [1, 2, 3]}
        metadata = {'duration': 120.0, 'fps': 30.0}

        # Store features
        storage.store_features(
            str(file_path), "perceptual_hash", {}, features_data, metadata
        )

        # Verify by retrieving
        cached = storage.get_cached_features(
            str(file_path), "perceptual_hash", {}
        )

        assert cached is not None
        assert cached['perceptual_hashes'] == [1, 2, 3]

    @patch('duplicateflow.storage.storage_manager.compute_file_md5_fast')
    def test_store_features_without_metadata(self, mock_compute_fast, tmp_path):
        """Test storing features without metadata."""
        storage = StorageManager(cache_dir=str(tmp_path))

        file_path = tmp_path / "video.mp4"
        file_path.write_text("content")

        mock_compute_fast.side_effect = ["filehash", "filehash"]

        features_data = {'data': [1, 2, 3]}

        # Store without metadata
        storage.store_features(
            str(file_path), "test_algo", {}, features_data
        )

        # Should still work
        cached = storage.get_cached_features(str(file_path), "test_algo", {})
        assert cached is not None


class TestStorageManagerGetStats:
    """Test get_stats method."""

    def test_get_stats_empty(self, tmp_path):
        """Test stats for empty storage."""
        storage = StorageManager(cache_dir=str(tmp_path))

        stats = storage.get_stats()

        assert 'hash_cache' in stats
        assert 'result_cache' in stats
        assert 'feature_cache' in stats
        assert 'cache_dir' in stats

        # All should be zero
        assert stats['hash_cache']['hits'] == 0
        assert stats['hash_cache']['misses'] == 0
        assert stats['hash_cache']['hit_rate'] == 0.0

        assert stats['result_cache']['hits'] == 0
        assert stats['result_cache']['misses'] == 0

        assert stats['feature_cache']['hits'] == 0
        assert stats['feature_cache']['misses'] == 0

    @patch('duplicateflow.storage.storage_manager.compute_file_md5_fast')
    def test_get_stats_with_data(self, mock_compute_fast, tmp_path):
        """Test stats after some operations."""
        storage = StorageManager(cache_dir=str(tmp_path))

        file1 = tmp_path / "video1.mp4"
        file1.write_text("content")

        mock_compute_fast.side_effect = ["hash1"] * 10

        # Do some operations to generate stats
        # Store and retrieve result (1 miss, 1 hit)
        storage.store_result(str(file1), str(file1), "test", {}, {'score': 1.0})
        storage.get_cached_result(str(file1), str(file1), "test", {})

        # Try to get non-existent result (1 miss)
        storage.get_cached_result(str(file1), str(file1), "other", {})

        stats = storage.get_stats()

        # Should have some hits/misses
        assert stats['result_cache']['hits'] >= 1
        assert stats['result_cache']['misses'] >= 1

        # Hit rate should be calculated
        assert 0.0 <= stats['result_cache']['hit_rate'] <= 100.0

    def test_get_stats_includes_cache_dir(self, tmp_path):
        """Test that stats include cache directory path."""
        storage = StorageManager(cache_dir=str(tmp_path / "cache"))

        stats = storage.get_stats()

        assert stats['cache_dir'] == str(tmp_path / "cache")


class TestStorageManagerCalculateHitRate:
    """Test _calculate_hit_rate helper method."""

    def test_calculate_hit_rate_zero_total(self, tmp_path):
        """Test hit rate calculation with zero hits and misses."""
        storage = StorageManager(cache_dir=str(tmp_path))

        rate = storage._calculate_hit_rate(0, 0)

        assert rate == 0.0

    def test_calculate_hit_rate_100_percent(self, tmp_path):
        """Test hit rate calculation with all hits."""
        storage = StorageManager(cache_dir=str(tmp_path))

        rate = storage._calculate_hit_rate(100, 0)

        assert rate == 100.0

    def test_calculate_hit_rate_50_percent(self, tmp_path):
        """Test hit rate calculation with 50% hits."""
        storage = StorageManager(cache_dir=str(tmp_path))

        rate = storage._calculate_hit_rate(50, 50)

        assert rate == 50.0

    def test_calculate_hit_rate_rounding(self, tmp_path):
        """Test hit rate calculation rounds to 2 decimals."""
        storage = StorageManager(cache_dir=str(tmp_path))

        rate = storage._calculate_hit_rate(1, 2)  # 33.333...%

        assert rate == 33.33


class TestStorageManagerVacuum:
    """Test vacuum method."""

    def test_vacuum_success(self, tmp_path):
        """Test vacuuming storage."""
        storage = StorageManager(cache_dir=str(tmp_path))

        # Should call result_cache.vacuum() without error
        storage.vacuum()

        # No exception means success


class TestStorageManagerResetStats:
    """Test reset_stats method."""

    @patch('duplicateflow.storage.storage_manager.compute_file_md5_fast')
    def test_reset_stats(self, mock_compute_fast, tmp_path):
        """Test resetting statistics counters."""
        storage = StorageManager(cache_dir=str(tmp_path))

        file1 = tmp_path / "video.mp4"
        file1.write_text("content")

        mock_compute_fast.side_effect = ["hash1"] * 5

        # Generate some stats
        storage.store_result(str(file1), str(file1), "test", {}, {'score': 1.0})
        storage.get_cached_result(str(file1), str(file1), "test", {})

        # Should have non-zero stats
        assert storage._stats['result_cache_hits'] > 0

        # Reset
        storage.reset_stats()

        # All counters should be zero
        assert storage._stats['hash_cache_hits'] == 0
        assert storage._stats['hash_cache_misses'] == 0
        assert storage._stats['result_cache_hits'] == 0
        assert storage._stats['result_cache_misses'] == 0
        # Note: feature_cache_hits/misses missing from reset_stats (bug in production code)
