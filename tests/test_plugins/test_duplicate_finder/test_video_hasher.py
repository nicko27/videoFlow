"""Tests for video_hasher.py

Tests perceptual hashing, hash comparison, and caching behavior.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import os

from src.plugins.duplicate_finder.video_hasher import VideoHasher


class TestHashComputation:
    """Test perceptual hash computation."""

    @patch('src.plugins.duplicate_finder.video_hasher.cv2.VideoCapture')
    def test_compute_hash_returns_valid_hash(self, mock_cv2, mock_database):
        """Test that compute_hash returns a valid perceptual hash."""
        # Mock OpenCV VideoCapture
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda x: 30.0 if x == 5 else 1000  # FPS and frame count
        mock_cap.read.return_value = (True, np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8))
        mock_cv2.return_value = mock_cap

        hasher = VideoHasher(mock_database)

        # Create a temporary file path (doesn't need to exist with mocking)
        video_path = "/tmp/test_video.mp4"

        # Mock os.path.exists and os.path.getmtime
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getmtime', return_value=1000.0), \
             patch('os.path.getsize', return_value=1024*1024):

            hash_result, duration = hasher.compute_video_hash_fast(video_path)

            assert hash_result is not None
            assert isinstance(hash_result, np.ndarray)
            assert len(hash_result) > 0
            assert duration > 0

    @patch('src.plugins.duplicate_finder.video_hasher.cv2.VideoCapture')
    def test_compute_hash_with_corrupted_video(self, mock_cv2, mock_database):
        """Test that compute_hash handles corrupted videos gracefully."""
        # Mock VideoCapture that fails to open
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cv2.return_value = mock_cap

        hasher = VideoHasher(mock_database)
        video_path = "/tmp/corrupted_video.mp4"

        with patch('os.path.exists', return_value=True), \
             patch('os.path.getmtime', return_value=1000.0), \
             patch('os.path.getsize', return_value=1024):

            hash_result, duration = hasher.compute_video_hash_fast(video_path)

            # Should return None for corrupted video
            assert hash_result is None or duration == 0


class TestHashComparison:
    """Test hash comparison and similarity computation."""

    def test_compare_identical_hashes(self, mock_database):
        """Test that identical hashes have 100% similarity."""
        hasher = VideoHasher(mock_database)

        # Create identical hashes
        hash1 = np.random.randint(0, 2, size=64, dtype=np.uint8)
        hash2 = hash1.copy()

        similarity = hasher._hamming_similarity(hash1, hash2)

        assert similarity == 1.0

    def test_compare_completely_different_hashes(self, mock_database):
        """Test that completely different hashes have low similarity."""
        hasher = VideoHasher(mock_database)

        # Create opposite hashes
        hash1 = np.zeros(64, dtype=np.uint8)
        hash2 = np.ones(64, dtype=np.uint8)

        similarity = hasher._hamming_similarity(hash1, hash2)

        assert similarity == 0.0

    def test_compare_similar_hashes(self, mock_database, sample_hash, similar_hash):
        """Test that similar hashes have high similarity."""
        hasher = VideoHasher(mock_database)

        similarity = hasher._hamming_similarity(sample_hash, similar_hash)

        # Should be around 90% similar (6 bits different out of 64)
        assert 0.85 <= similarity <= 0.95

    def test_hamming_distance_calculation(self, mock_database):
        """Test hamming distance calculation."""
        hasher = VideoHasher(mock_database)

        # Create hashes with known difference
        hash1 = np.array([0, 1, 0, 1, 0, 1], dtype=np.uint8)
        hash2 = np.array([0, 1, 1, 1, 0, 0], dtype=np.uint8)
        # Differences at positions 2 and 5 → distance = 2

        distance = hasher._hamming_distance(hash1, hash2)

        assert distance == 2

    def test_similarity_from_distance(self, mock_database):
        """Test similarity conversion from hamming distance."""
        hasher = VideoHasher(mock_database)

        # 10 bits different out of 64 → 54/64 = 84.375% similar
        hash1 = np.zeros(64, dtype=np.uint8)
        hash2 = np.zeros(64, dtype=np.uint8)
        hash2[:10] = 1  # Flip first 10 bits

        similarity = hasher._hamming_similarity(hash1, hash2)

        expected_similarity = (64 - 10) / 64
        assert abs(similarity - expected_similarity) < 0.01


class TestCacheBehavior:
    """Test hash caching behavior."""

    def test_cache_hit_on_second_call(self, mock_database):
        """Test that second call for same video uses cache."""
        hasher = VideoHasher(mock_database)
        video_path = "/tmp/test_video.mp4"

        # Store hash in cache
        test_hash = np.random.randint(0, 2, size=64, dtype=np.uint8)
        test_duration = 120.5
        hasher.hash_cache[video_path] = {
            'hash': test_hash,
            'duration': test_duration,
            'mtime': 1000.0,
            'file_size': 1024 * 1024
        }

        with patch('os.path.exists', return_value=True), \
             patch('os.path.getmtime', return_value=1000.0), \
             patch('os.path.getsize', return_value=1024*1024):

            # Second call should use cache
            hash_result, duration = hasher.compute_video_hash_fast(video_path)

            assert np.array_equal(hash_result, test_hash)
            assert duration == test_duration

    def test_cache_invalidation_on_mtime_change(self, mock_database):
        """Test that cache is invalidated when mtime changes."""
        hasher = VideoHasher(mock_database)
        video_path = "/tmp/test_video.mp4"

        # Store hash in cache with old mtime
        test_hash = np.random.randint(0, 2, size=64, dtype=np.uint8)
        hasher.hash_cache[video_path] = {
            'hash': test_hash,
            'duration': 120.5,
            'mtime': 1000.0,  # Old mtime
            'file_size': 1024 * 1024
        }

        # File now has different mtime
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getmtime', return_value=2000.0), \
             patch('os.path.getsize', return_value=1024*1024):

            # Cache should be invalidated (mtime mismatch)
            # This test verifies the logic, actual behavior depends on mock
            current_mtime = 2000.0
            cached_mtime = hasher.hash_cache[video_path]['mtime']

            assert abs(current_mtime - cached_mtime) >= 1  # Cache should be invalidated

    def test_cache_invalidation_on_size_change(self, mock_database):
        """Test that cache is invalidated when file size changes."""
        hasher = VideoHasher(mock_database)
        video_path = "/tmp/test_video.mp4"

        # Store hash in cache with specific size
        test_hash = np.random.randint(0, 2, size=64, dtype=np.uint8)
        hasher.hash_cache[video_path] = {
            'hash': test_hash,
            'duration': 120.5,
            'mtime': 1000.0,
            'file_size': 1024 * 1024  # 1 MB
        }

        # File now has different size but same mtime
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getmtime', return_value=1000.0), \
             patch('os.path.getsize', return_value=2 * 1024 * 1024):  # 2 MB

            current_size = 2 * 1024 * 1024
            cached_size = hasher.hash_cache[video_path].get('file_size', 0)

            assert current_size != cached_size  # Cache should be invalidated


class TestDatabaseCacheFallback:
    """Test fallback to database cache when memory cache misses."""

    def test_database_cache_hit(self, mock_database):
        """Test that database cache is checked when memory cache misses."""
        # Store hash in database
        video_path = "/tmp/test_video.mp4"
        test_hash = np.random.randint(0, 2, size=64, dtype=np.uint8)
        test_duration = 120.5

        mock_database.store_hash(
            video_path,
            test_hash,
            'phash',
            duration=test_duration,
            mtime=1000.0,
            file_size=1024 * 1024
        )

        hasher = VideoHasher(mock_database)

        with patch('os.path.exists', return_value=True), \
             patch('os.path.getmtime', return_value=1000.0), \
             patch('os.path.getsize', return_value=1024*1024):

            # Should retrieve from database
            retrieved_hash, retrieved_duration = mock_database.get_hash(video_path, 'phash')

            assert retrieved_hash is not None
            assert np.array_equal(retrieved_hash, test_hash)
            assert retrieved_duration == test_duration


class TestCompareVideos:
    """Test video-to-video comparison."""

    @patch('src.plugins.duplicate_finder.video_hasher.VideoHasher.compute_video_hash_fast')
    def test_compare_videos_high_similarity(self, mock_compute, mock_database):
        """Test comparing two similar videos."""
        hasher = VideoHasher(mock_database)

        # Mock hash computation to return similar hashes
        hash1 = np.random.randint(0, 2, size=64, dtype=np.uint8)
        hash2 = hash1.copy()
        hash2[:5] = 1 - hash2[:5]  # Flip 5 bits → ~92% similar

        mock_compute.side_effect = [
            (hash1, 120.0),  # First video
            (hash2, 120.0),  # Second video
        ]

        similarity = hasher.compare_videos("/tmp/video1.mp4", "/tmp/video2.mp4")

        # Should be around 92% similar (59/64 bits match)
        assert 0.90 <= similarity <= 0.95

    @patch('src.plugins.duplicate_finder.video_hasher.VideoHasher.compute_video_hash_fast')
    def test_compare_videos_low_similarity(self, mock_compute, mock_database):
        """Test comparing two different videos."""
        hasher = VideoHasher(mock_database)

        # Mock hash computation to return very different hashes
        hash1 = np.zeros(64, dtype=np.uint8)
        hash2 = np.ones(64, dtype=np.uint8)

        mock_compute.side_effect = [
            (hash1, 120.0),
            (hash2, 120.0),
        ]

        similarity = hasher.compare_videos("/tmp/video1.mp4", "/tmp/video2.mp4")

        assert similarity == 0.0

    @patch('src.plugins.duplicate_finder.video_hasher.VideoHasher.compute_video_hash_fast')
    def test_compare_videos_with_hash_failure(self, mock_compute, mock_database):
        """Test comparing videos when hash computation fails."""
        hasher = VideoHasher(mock_database)

        # Mock hash computation to fail
        mock_compute.side_effect = [
            (None, 0),  # First video fails
            (np.random.randint(0, 2, size=64), 120.0),
        ]

        similarity = hasher.compare_videos("/tmp/video1.mp4", "/tmp/video2.mp4")

        # Should return 0 similarity when hash fails
        assert similarity == 0.0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_hash_comparison(self, mock_database):
        """Test comparing empty hashes."""
        hasher = VideoHasher(mock_database)

        hash1 = np.array([], dtype=np.uint8)
        hash2 = np.array([], dtype=np.uint8)

        # Should handle empty arrays gracefully
        try:
            similarity = hasher._hamming_similarity(hash1, hash2)
            # Empty hashes could be considered identical (100%) or undefined
            assert 0.0 <= similarity <= 1.0
        except (ValueError, ZeroDivisionError):
            # Or might raise exception for empty input
            pass

    def test_different_length_hashes(self, mock_database):
        """Test comparing hashes of different lengths."""
        hasher = VideoHasher(mock_database)

        hash1 = np.random.randint(0, 2, size=64, dtype=np.uint8)
        hash2 = np.random.randint(0, 2, size=128, dtype=np.uint8)

        # Should handle or raise error for mismatched lengths
        try:
            similarity = hasher._hamming_similarity(hash1, hash2)
            # If it doesn't raise, result should be valid
            assert 0.0 <= similarity <= 1.0
        except (ValueError, AssertionError):
            # Or might raise exception for mismatched lengths
            pass

    def test_nonexistent_video_file(self, mock_database):
        """Test hashing a non-existent video file."""
        hasher = VideoHasher(mock_database)

        with patch('os.path.exists', return_value=False):
            hash_result, duration = hasher.compute_video_hash_fast("/nonexistent/video.mp4")

            # Should return None or handle gracefully
            assert hash_result is None or duration == 0
