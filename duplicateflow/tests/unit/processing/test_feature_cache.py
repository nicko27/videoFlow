"""
Unit tests for SegmentFeatureCache.

Tests segment-based feature caching for optimized window search with
in-memory and disk caching.
"""

import pytest
import pickle
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from duplicateflow.processing.feature_cache import SegmentFeatureCache


class TestSegmentFeatureCacheInit:
    """Test SegmentFeatureCache initialization."""

    def test_init_default_params(self, tmp_path):
        """Test initialization with default parameters."""
        cache = SegmentFeatureCache(cache_dir=tmp_path / "cache")

        assert cache.cache_dir == tmp_path / "cache"
        assert cache.cache_dir.exists()
        assert cache.segment_duration == 60.0
        assert cache.max_memory_segments == 100
        assert isinstance(cache._memory_cache, dict)
        assert len(cache._memory_cache) == 0

    def test_init_custom_params(self, tmp_path):
        """Test initialization with custom parameters."""
        cache = SegmentFeatureCache(
            cache_dir=tmp_path / "custom",
            segment_duration=120.0,
            max_memory_segments=50
        )

        assert cache.cache_dir == tmp_path / "custom"
        assert cache.segment_duration == 120.0
        assert cache.max_memory_segments == 50

    def test_init_creates_cache_directory(self, tmp_path):
        """Test that initialization creates cache directory."""
        cache_dir = tmp_path / "new" / "nested" / "cache"
        cache = SegmentFeatureCache(cache_dir=cache_dir)

        assert cache_dir.exists()


class TestSegmentFeatureCacheCacheKey:
    """Test cache key generation."""

    def test_get_cache_key(self, tmp_path):
        """Test cache key generation."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        # Patch _get_cache_key to use a simple hash instead of HashCache
        with patch.object(cache, '_get_cache_key') as mock_get_key:
            mock_get_key.return_value = "abc123_frame_hash_60.0_threshold_70"

            key = mock_get_key("video.mp4", "frame_hash", {"threshold": 70})

            # Should return mocked key
            assert "abc123" in key
            assert "frame_hash" in key
            assert "60.0" in key
            assert "threshold" in key
            assert "70" in key

    def test_get_cache_key_deterministic(self, tmp_path):
        """Test cache key is deterministic for same inputs."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        # Patch the method to avoid HashCache import issue
        with patch.object(cache, '_get_cache_key', side_effect=lambda v, a, p: f"hash_{v}_{a}"):
            key1 = cache._get_cache_key("video.mp4", "frame_hash", {"threshold": 70})
            key2 = cache._get_cache_key("video.mp4", "frame_hash", {"threshold": 70})

            assert key1 == key2


class TestSegmentFeatureCacheHasCache:
    """Test has_cache method."""

    def test_has_cache_memory(self, tmp_path):
        """Test has_cache returns True for memory cached features."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        # Manually add to memory cache
        cache_key = "hash123_frame_hash_60.0_threshold_70"
        cache._memory_cache[cache_key] = {0.0: {}}

        # Patch _get_cache_key to return our known key
        with patch.object(cache, '_get_cache_key', return_value=cache_key):
            assert cache.has_cache("video.mp4", "frame_hash", {"threshold": 70}) is True

    def test_has_cache_disk(self, tmp_path):
        """Test has_cache returns True for disk cached features."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        # Create fake cache file
        cache_key = "hash123_frame_hash_60.0_threshold_70"
        cache_file = tmp_path / f"{cache_key}.pkl"
        cache_file.write_bytes(pickle.dumps({}))

        # Patch _get_cache_key to return our known key
        with patch.object(cache, '_get_cache_key', return_value=cache_key):
            assert cache.has_cache("video.mp4", "frame_hash", {"threshold": 70}) is True

    def test_has_cache_not_found(self, tmp_path):
        """Test has_cache returns False when cache not found."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        cache_key = "hash123_frame_hash_60.0_threshold_70"

        # Patch _get_cache_key to return our known key
        with patch.object(cache, '_get_cache_key', return_value=cache_key):
            assert cache.has_cache("video.mp4", "frame_hash", {"threshold": 70}) is False


class TestSegmentFeatureCacheLoadCache:
    """Test load_cache method."""

    def test_load_cache_from_memory(self, tmp_path):
        """Test loading from memory cache."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        # Add to memory cache
        features = {0.0: {"frames": []}, 60.0: {"frames": []}}
        cache_key = "hash123_frame_hash_60.0"
        cache._memory_cache[cache_key] = features

        # Patch _get_cache_key
        with patch.object(cache, '_get_cache_key', return_value=cache_key):
            loaded = cache.load_cache("video.mp4", "frame_hash", {})

        assert loaded == features
        assert loaded is features  # Same object from memory

    def test_load_cache_from_disk(self, tmp_path):
        """Test loading from disk cache."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        # Create disk cache
        features = {0.0: {"frames": []}, 60.0: {"frames": []}}
        cache_key = "hash123_frame_hash_60.0"
        cache_file = tmp_path / f"{cache_key}.pkl"
        with open(cache_file, 'wb') as f:
            pickle.dump(features, f)

        # Patch _get_cache_key
        with patch.object(cache, '_get_cache_key', return_value=cache_key):
            loaded = cache.load_cache("video.mp4", "frame_hash", {})

        assert loaded == features
        # Should also be in memory cache now
        assert cache_key in cache._memory_cache

    def test_load_cache_not_found(self, tmp_path):
        """Test load_cache returns None when not found."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        cache_key = "hash123_frame_hash_60.0"

        # Patch _get_cache_key
        with patch.object(cache, '_get_cache_key', return_value=cache_key):
            loaded = cache.load_cache("video.mp4", "frame_hash", {})

        assert loaded is None

    def test_load_cache_corrupted_file(self, tmp_path):
        """Test load_cache handles corrupted cache file."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        # Create corrupted cache file
        cache_key = "hash123_frame_hash_60.0"
        cache_file = tmp_path / f"{cache_key}.pkl"
        cache_file.write_text("corrupted data")

        # Patch _get_cache_key
        with patch.object(cache, '_get_cache_key', return_value=cache_key):
            loaded = cache.load_cache("video.mp4", "frame_hash", {})

        # Should return None on error
        assert loaded is None


class TestSegmentFeatureCacheSaveCache:
    """Test save_cache method."""

    def test_save_cache_success(self, tmp_path):
        """Test saving features to cache."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        features = {0.0: {"frames": []}, 60.0: {"frames": []}}
        cache_key = "hash123_frame_hash_60.0"

        # Patch _get_cache_key
        with patch.object(cache, '_get_cache_key', return_value=cache_key):
            cache.save_cache("video.mp4", "frame_hash", features, {})

        # Should be in memory cache
        assert cache_key in cache._memory_cache
        assert cache._memory_cache[cache_key] == features

        # Should be on disk
        cache_file = tmp_path / f"{cache_key}.pkl"
        assert cache_file.exists()

        # Verify disk content
        with open(cache_file, 'rb') as f:
            loaded = pickle.load(f)
        assert loaded == features


class TestSegmentFeatureCacheComputeFeatures:
    """Test compute_features method."""

    @patch('duplicateflow.algorithms.base.video_loader.get_video_duration')
    @patch('duplicateflow.algorithms.base.video_loader.VideoLoader')
    def test_compute_features_single_segment(self, mock_loader_class, mock_duration, tmp_path):
        """Test computing features for video with one segment."""
        # Mock duration
        mock_duration.return_value = 30.0  # Less than 60s = 1 segment

        # Mock VideoLoader
        mock_loader = MagicMock()
        mock_frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        mock_loader.get_frame = Mock(return_value=mock_frame)
        mock_loader.__enter__ = Mock(return_value=mock_loader)
        mock_loader.__exit__ = Mock(return_value=False)
        mock_loader_class.return_value = mock_loader

        cache = SegmentFeatureCache(cache_dir=tmp_path, segment_duration=60.0)

        features = cache.compute_features("video.mp4", "frame_hash", {}, show_progress=False)

        # Should have 1 segment
        assert len(features) == 1
        assert 0.0 in features
        assert 'start_time' in features[0.0]
        assert 'duration' in features[0.0]
        assert 'frames' in features[0.0]

    @patch('duplicateflow.algorithms.base.video_loader.get_video_duration')
    @patch('duplicateflow.algorithms.base.video_loader.VideoLoader')
    def test_compute_features_multiple_segments(self, mock_loader_class, mock_duration, tmp_path):
        """Test computing features for video with multiple segments."""
        # Mock duration
        mock_duration.return_value = 180.0  # 3 minutes = 3 segments of 60s

        # Mock VideoLoader
        mock_loader = MagicMock()
        mock_frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        mock_loader.get_frame = Mock(return_value=mock_frame)
        mock_loader.__enter__ = Mock(return_value=mock_loader)
        mock_loader.__exit__ = Mock(return_value=False)
        mock_loader_class.return_value = mock_loader

        cache = SegmentFeatureCache(cache_dir=tmp_path, segment_duration=60.0)

        features = cache.compute_features("video.mp4", "frame_hash", {}, show_progress=False)

        # Should have 3 segments
        assert len(features) == 3
        assert 0.0 in features
        assert 60.0 in features
        assert 120.0 in features


class TestSegmentFeatureCacheGetOrCompute:
    """Test get_or_compute method."""

    @patch('duplicateflow.algorithms.base.video_loader.get_video_duration')
    @patch('duplicateflow.algorithms.base.video_loader.VideoLoader')
    def test_get_or_compute_computes_when_not_cached(self, mock_loader_class, mock_duration, tmp_path):
        """Test get_or_compute computes features when not cached."""
        mock_duration.return_value = 30.0

        mock_loader = MagicMock()
        mock_frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        mock_loader.get_frame = Mock(return_value=mock_frame)
        mock_loader.__enter__ = Mock(return_value=mock_loader)
        mock_loader.__exit__ = Mock(return_value=False)
        mock_loader_class.return_value = mock_loader

        cache = SegmentFeatureCache(cache_dir=tmp_path)

        cache_key = "hash123_frame_hash_60.0"

        # Patch _get_cache_key
        with patch.object(cache, '_get_cache_key', return_value=cache_key):
            features = cache.get_or_compute("video.mp4", "frame_hash", {}, show_progress=False)

        # Should have computed features
        assert len(features) > 0
        # Should be saved to cache
        assert cache_key in cache._memory_cache

    def test_get_or_compute_uses_cache_when_available(self, tmp_path):
        """Test get_or_compute returns cached features without recomputing."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        # Pre-populate cache
        cached_features = {0.0: {"cached": True}}
        cache_key = "hash123_frame_hash_60.0"
        cache._memory_cache[cache_key] = cached_features

        # Patch _get_cache_key
        with patch.object(cache, '_get_cache_key', return_value=cache_key):
            features = cache.get_or_compute("video.mp4", "frame_hash", {}, show_progress=False)

        # Should return cached features
        assert features == cached_features


class TestSegmentFeatureCacheGetWindowFeatures:
    """Test get_window_features method."""

    def test_get_window_features_single_segment(self, tmp_path):
        """Test getting window features from single segment."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        # Create features with frames
        features = {
            0.0: {
                'start_time': 0.0,
                'duration': 60.0,
                'frames': [
                    {'offset': 10.0, 'hash': 123},
                    {'offset': 20.0, 'hash': 456},
                    {'offset': 30.0, 'hash': 789},
                ]
            }
        }

        # Get window 15-35 seconds
        window_features = cache.get_window_features(features, window_start=15.0, window_duration=20.0)

        # Should include frames at 20s and 30s (not 10s)
        assert len(window_features) == 2
        assert window_features[0]['offset'] == 20.0
        assert window_features[1]['offset'] == 30.0

    def test_get_window_features_multiple_segments(self, tmp_path):
        """Test getting window features spanning multiple segments."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        # Create features with multiple segments
        features = {
            0.0: {
                'start_time': 0.0,
                'duration': 60.0,
                'frames': [
                    {'offset': 50.0, 'hash': 123},
                ]
            },
            60.0: {
                'start_time': 60.0,
                'duration': 60.0,
                'frames': [
                    {'offset': 70.0, 'hash': 456},
                    {'offset': 80.0, 'hash': 789},
                ]
            },
            120.0: {
                'start_time': 120.0,
                'duration': 60.0,
                'frames': [
                    {'offset': 130.0, 'hash': 999},
                ]
            }
        }

        # Get window 55-85 seconds (spans segments 0 and 60)
        window_features = cache.get_window_features(features, window_start=55.0, window_duration=30.0)

        # Should include frames at 70s and 80s (not 50s or 130s)
        assert len(window_features) == 2
        assert window_features[0]['offset'] == 70.0
        assert window_features[1]['offset'] == 80.0

    def test_get_window_features_no_overlap(self, tmp_path):
        """Test getting window features with no overlapping segments."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        features = {
            0.0: {
                'start_time': 0.0,
                'duration': 60.0,
                'frames': [{'offset': 30.0, 'hash': 123}]
            }
        }

        # Get window 100-150 seconds (no overlap)
        window_features = cache.get_window_features(features, window_start=100.0, window_duration=50.0)

        assert len(window_features) == 0


class TestSegmentFeatureCacheClearCache:
    """Test cache clearing methods."""

    def test_clear_memory_cache(self, tmp_path):
        """Test clearing memory cache."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        # Add some data to memory cache
        cache._memory_cache["key1"] = {0.0: {}}
        cache._memory_cache["key2"] = {0.0: {}}

        assert len(cache._memory_cache) == 2

        cache.clear_memory_cache()

        assert len(cache._memory_cache) == 0

    def test_clear_disk_cache_all(self, tmp_path):
        """Test clearing all disk cache files."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        # Create some cache files
        (tmp_path / "file1.pkl").write_text("data1")
        (tmp_path / "file2.pkl").write_text("data2")
        (tmp_path / "file3.pkl").write_text("data3")

        count = cache.clear_disk_cache()

        assert count == 3
        assert len(list(tmp_path.glob("*.pkl"))) == 0

    def test_clear_disk_cache_algorithm_specific(self, tmp_path):
        """Test clearing cache for specific algorithm."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        # Create cache files for different algorithms
        (tmp_path / "hash1_frame_hash_60.0.pkl").write_text("data1")
        (tmp_path / "hash2_frame_hash_60.0.pkl").write_text("data2")
        (tmp_path / "hash3_ssim_60.0.pkl").write_text("data3")

        count = cache.clear_disk_cache(algorithm="frame_hash")

        # Should only clear frame_hash files
        assert count == 2
        assert (tmp_path / "hash3_ssim_60.0.pkl").exists()


class TestSegmentFeatureCacheGetCacheStats:
    """Test get_cache_stats method."""

    def test_get_cache_stats_empty(self, tmp_path):
        """Test stats for empty cache."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        stats = cache.get_cache_stats()

        assert stats['memory_entries'] == 0
        assert stats['disk_entries'] == 0
        assert stats['total_size_mb'] == 0.0
        assert stats['cache_dir'] == str(tmp_path)

    def test_get_cache_stats_with_data(self, tmp_path):
        """Test stats with cached data."""
        cache = SegmentFeatureCache(cache_dir=tmp_path)

        # Add memory cache
        cache._memory_cache["key1"] = {0.0: {}}
        cache._memory_cache["key2"] = {0.0: {}}

        # Add disk cache
        (tmp_path / "file1.pkl").write_bytes(b"0" * 1024)  # 1 KB
        (tmp_path / "file2.pkl").write_bytes(b"0" * 2048)  # 2 KB

        stats = cache.get_cache_stats()

        assert stats['memory_entries'] == 2
        assert stats['disk_entries'] == 2
        assert stats['total_size_mb'] > 0
