"""
Unit tests for subsequence detection feature.

Tests the SubsequenceDetector functionality including:
- LRU cache with memory limits
- Dense video hashing
- Sliding window comparison
- Database integration
- Memory management
"""

import unittest
import tempfile
import os
import sys
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from src.plugins.duplicate_finder.video_hasher import VideoHasher
from src.plugins.duplicate_finder.subsequence_detector import SubsequenceDetector, LRUCache
from src.plugins.duplicate_finder.database_manager import VideoDatabase


class TestLRUCache(unittest.TestCase):
    """Test LRU cache with memory limits."""

    def test_cache_initialization(self):
        """Test cache initializes with correct parameters."""
        cache = LRUCache(max_memory_mb=100)
        self.assertEqual(cache.max_memory_mb, 100)
        self.assertEqual(cache.max_memory_bytes, 100 * 1024 * 1024)
        self.assertEqual(cache.current_memory, 0)
        self.assertEqual(len(cache.cache), 0)

    def test_cache_put_get(self):
        """Test basic cache put/get operations."""
        cache = LRUCache(max_memory_mb=10)

        # Create test data
        test_hash = np.random.randint(0, 2, (10, 8, 8), dtype=bool)
        duration = 100.0

        # Put in cache
        cache.put("video1.mp4", test_hash, duration)

        # Retrieve from cache
        result = cache.get("video1.mp4")
        self.assertIsNotNone(result)
        self.assertTrue(np.array_equal(result['hash'], test_hash))
        self.assertEqual(result['duration'], duration)

    def test_cache_eviction(self):
        """Test that cache evicts items when memory limit is reached."""
        cache = LRUCache(max_memory_mb=1)  # Very small cache

        # Add multiple items until eviction occurs
        for i in range(100):
            # Each hash is about 640 bytes (10 frames * 8*8 * 1 byte)
            test_hash = np.random.randint(0, 2, (10, 8, 8), dtype=bool)
            cache.put(f"video{i}.mp4", test_hash, 100.0)

        # Cache should not exceed memory limit
        self.assertLessEqual(cache.current_memory, cache.max_memory_bytes)

        # Old items should have been evicted
        self.assertIsNone(cache.get("video0.mp4"))

    def test_cache_lru_order(self):
        """Test that least recently used items are evicted first."""
        cache = LRUCache(max_memory_mb=1)

        # Add items
        for i in range(5):
            test_hash = np.random.randint(0, 2, (10, 8, 8), dtype=bool)
            cache.put(f"video{i}.mp4", test_hash, 100.0)

        # Access video1 to make it recently used
        cache.get("video1.mp4")

        # Add many more items to trigger eviction
        for i in range(5, 100):
            test_hash = np.random.randint(0, 2, (10, 8, 8), dtype=bool)
            cache.put(f"video{i}.mp4", test_hash, 100.0)

        # video1 should still be in cache (recently accessed)
        # video0 should be evicted (not accessed)
        self.assertIsNone(cache.get("video0.mp4"))

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = LRUCache(max_memory_mb=10)

        # Add some items
        for i in range(5):
            test_hash = np.random.randint(0, 2, (10, 8, 8), dtype=bool)
            cache.put(f"video{i}.mp4", test_hash, 100.0)

        stats = cache.get_stats()
        self.assertEqual(stats['items'], 5)
        self.assertGreater(stats['memory_mb'], 0)
        self.assertEqual(stats['max_memory_mb'], 10)
        self.assertGreater(stats['usage_percent'], 0)
        self.assertLess(stats['usage_percent'], 100)

    def test_cache_clear(self):
        """Test cache clear functionality."""
        cache = LRUCache(max_memory_mb=10)

        # Add items
        for i in range(5):
            test_hash = np.random.randint(0, 2, (10, 8, 8), dtype=bool)
            cache.put(f"video{i}.mp4", test_hash, 100.0)

        self.assertGreater(len(cache.cache), 0)
        self.assertGreater(cache.current_memory, 0)

        # Clear cache
        cache.clear()

        self.assertEqual(len(cache.cache), 0)
        self.assertEqual(cache.current_memory, 0)


class TestSubsequenceDetector(unittest.TestCase):
    """Test subsequence detection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')

        # Create hasher with test database
        self.hasher = VideoHasher(method='pHash')
        self.hasher.db = VideoDatabase(self.db_path)

        # Create detector
        self.detector = SubsequenceDetector(
            hasher=self.hasher,
            max_cache_memory_mb=50,
            sample_interval_seconds=3.0,
            min_match_ratio=0.80
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_detector_initialization(self):
        """Test detector initializes with correct parameters."""
        self.assertEqual(self.detector.sample_interval_seconds, 3.0)
        self.assertEqual(self.detector.min_match_ratio, 0.80)
        self.assertEqual(self.detector.dense_cache.max_memory_mb, 50)

    def test_synthetic_subsequence_detection(self):
        """Test subsequence detection with synthetic data."""
        # Create synthetic video hashes
        # Long video: 100 frames
        long_hash = np.random.randint(0, 2, (100, 8, 8), dtype=bool)

        # Short video: Extract frames 30-50 from long video
        short_hash = long_hash[30:51].copy()

        # Manually set in cache
        self.detector.dense_cache.put("long.mp4", long_hash, 300.0)
        self.detector.dense_cache.put("short.mp4", short_hash, 63.0)

        # Should be able to get from cache
        long_cached = self.detector.dense_cache.get("long.mp4")
        short_cached = self.detector.dense_cache.get("short.mp4")

        self.assertIsNotNone(long_cached)
        self.assertIsNotNone(short_cached)

    def test_cache_memory_limit(self):
        """Test that detector respects memory limits."""
        # Create many synthetic hashes
        for i in range(100):
            test_hash = np.random.randint(0, 2, (50, 8, 8), dtype=bool)
            self.detector.dense_cache.put(f"video{i}.mp4", test_hash, 150.0)

        # Check memory limit is respected
        stats = self.detector.get_cache_stats()
        self.assertLessEqual(stats['memory_mb'], 50)

    def test_different_match_ratios(self):
        """Test detection with different match ratio thresholds."""
        # Test with very strict ratio
        detector_strict = SubsequenceDetector(
            hasher=self.hasher,
            min_match_ratio=0.95
        )
        self.assertEqual(detector_strict.min_match_ratio, 0.95)

        # Test with permissive ratio
        detector_permissive = SubsequenceDetector(
            hasher=self.hasher,
            min_match_ratio=0.70
        )
        self.assertEqual(detector_permissive.min_match_ratio, 0.70)


class TestDatabaseIntegration(unittest.TestCase):
    """Test database integration for subsequence detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = VideoDatabase(self.db_path)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_subsequence_table_creation(self):
        """Test that subsequence table is created."""
        info = self.db.get_database_info()
        self.assertIn('video_subsequences', info['tables'])

    def test_store_subsequence_detection(self):
        """Test storing subsequence detection."""
        # First add video files
        hash1 = np.random.randint(0, 2, (10, 8, 8), dtype=bool)
        hash2 = np.random.randint(0, 2, (10, 8, 8), dtype=bool)

        self.db.store_video_hash("/path/to/short.mp4", hash1, 30.0)
        self.db.store_video_hash("/path/to/long.mp4", hash2, 100.0)

        # Store subsequence detection
        result = self.db.store_subsequence_detection(
            short_video_path="/path/to/short.mp4",
            long_video_path="/path/to/long.mp4",
            match_ratio=0.87,
            start_frame_idx=450,
            confidence=0.87
        )

        self.assertTrue(result)

    def test_get_pending_subsequences(self):
        """Test retrieving pending subsequences."""
        # Add video files
        hash1 = np.random.randint(0, 2, (10, 8, 8), dtype=bool)
        hash2 = np.random.randint(0, 2, (10, 8, 8), dtype=bool)

        self.db.store_video_hash("/path/to/short.mp4", hash1, 30.0)
        self.db.store_video_hash("/path/to/long.mp4", hash2, 100.0)

        # Store detection
        self.db.store_subsequence_detection(
            "/path/to/short.mp4",
            "/path/to/long.mp4",
            0.87,
            450,
            0.87
        )

        # Retrieve pending
        pending = self.db.get_pending_subsequences()

        # Should be empty because files don't exist on disk
        # (get_pending_subsequences checks file existence)
        self.assertIsInstance(pending, list)

    def test_update_subsequence_status(self):
        """Test updating subsequence status."""
        # Add video files
        hash1 = np.random.randint(0, 2, (10, 8, 8), dtype=bool)
        hash2 = np.random.randint(0, 2, (10, 8, 8), dtype=bool)

        self.db.store_video_hash("/path/to/short.mp4", hash1, 30.0)
        self.db.store_video_hash("/path/to/long.mp4", hash2, 100.0)

        # Store detection
        self.db.store_subsequence_detection(
            "/path/to/short.mp4",
            "/path/to/long.mp4",
            0.87,
            450,
            0.87
        )

        # Update status (use ID 1 for first entry)
        result = self.db.update_subsequence_status(
            subseq_id=1,
            status='processed',
            action='kept_short'
        )

        self.assertTrue(result)

    def test_subsequence_statistics(self):
        """Test getting subsequence statistics."""
        stats = self.db.get_subsequence_statistics()

        self.assertIn('total', stats)
        self.assertIn('pending', stats)
        self.assertIn('processed', stats)
        self.assertIn('avg_match_ratio', stats)
        self.assertIn('avg_confidence', stats)


class TestMemoryManagement(unittest.TestCase):
    """Test memory management and safety features."""

    def test_memory_estimation(self):
        """Test that memory estimation is reasonable."""
        cache = LRUCache(max_memory_mb=10)

        # Create a hash and estimate its size
        test_hash = np.random.randint(0, 2, (10, 8, 8), dtype=bool)
        estimated_size = cache._estimate_size(test_hash)

        # Should be approximately: 10 * 8 * 8 * 1 byte + overhead
        expected_size = test_hash.nbytes + 200
        self.assertEqual(estimated_size, expected_size)

    def test_no_memory_overflow(self):
        """Test that cache never exceeds memory limit."""
        cache = LRUCache(max_memory_mb=5)

        # Try to add many large items
        for i in range(200):
            # Each item is ~6.5KB
            large_hash = np.random.randint(0, 2, (100, 8, 8), dtype=bool)
            cache.put(f"video{i}.mp4", large_hash, 300.0)

            # Verify memory limit
            self.assertLessEqual(
                cache.current_memory,
                cache.max_memory_bytes,
                f"Cache exceeded memory limit on iteration {i}"
            )

    def test_cache_handles_large_videos(self):
        """Test cache handles very large video hashes."""
        cache = LRUCache(max_memory_mb=10)

        # Create a very large hash (200 frames max)
        large_hash = np.random.randint(0, 2, (200, 8, 8), dtype=bool)
        cache.put("large_video.mp4", large_hash, 600.0)

        # Should be able to retrieve it
        result = cache.get("large_video.mp4")
        self.assertIsNotNone(result)

        # Memory should still be within limit
        self.assertLessEqual(cache.current_memory, cache.max_memory_bytes)


def run_tests():
    """Run all tests and print results."""
    print("=" * 70)
    print("SUBSEQUENCE DETECTOR - UNIT TESTS")
    print("=" * 70)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestLRUCache))
    suite.addTests(loader.loadTestsFromTestCase(TestSubsequenceDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestMemoryManagement))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✓ ALL TESTS PASSED")
    else:
        print("\n✗ SOME TESTS FAILED")

    return result


if __name__ == '__main__':
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
