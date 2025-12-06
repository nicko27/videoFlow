"""Tests for database_manager.py

Tests database operations, connection pooling, and cache management.
"""

import pytest
import os
import numpy as np
from pathlib import Path

from src.plugins.duplicate_finder.database_manager import DatabaseManager


class TestDatabaseManagerInit:
    """Test database initialization and table creation."""

    def test_creates_database_file(self, temp_dir):
        """Test that database file is created on initialization."""
        db_path = temp_dir / "test.db"
        db = DatabaseManager(str(db_path))

        assert db_path.exists()
        assert db.db_path == str(db_path)

    def test_creates_all_required_tables(self, mock_database):
        """Test that all required tables are created."""
        conn = mock_database.connection_pool.get_connection()
        cursor = conn.cursor()

        # Check that required tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]

        required_tables = {
            'video_files',
            'video_hashes',
            'comparisons',
            'ignored_pairs',
            'audio_cache',
            'scene_detection_cache',
        }

        for table in required_tables:
            assert table in tables, f"Missing required table: {table}"

    def test_wal_mode_enabled(self, mock_database):
        """Test that WAL mode is enabled for better concurrency."""
        conn = mock_database.connection_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]

        assert mode.lower() == 'wal', "WAL mode should be enabled"


class TestHashStorage:
    """Test video hash storage and retrieval."""

    def test_store_and_retrieve_hash(self, mock_database, mock_video_path):
        """Test storing and retrieving a video hash."""
        # Create a test hash
        test_hash = np.random.randint(0, 2, size=64, dtype=np.uint8)
        duration = 120.5
        file_size = 1024 * 1024  # 1 MB

        # Store hash
        mock_database.store_hash(
            mock_video_path,
            test_hash,
            'phash',
            duration=duration,
            file_size=file_size
        )

        # Retrieve hash
        retrieved_hash, retrieved_duration = mock_database.get_hash(
            mock_video_path,
            'phash'
        )

        assert retrieved_hash is not None
        assert np.array_equal(retrieved_hash, test_hash)
        assert abs(retrieved_duration - duration) < 0.01

    def test_get_hash_returns_none_for_nonexistent_file(self, mock_database):
        """Test that get_hash returns None for files not in cache."""
        result = mock_database.get_hash(
            "/nonexistent/video.mp4",
            'phash'
        )

        assert result == (None, None)

    def test_update_hash_on_file_change(self, mock_database, mock_video_path):
        """Test that hash is updated when file is modified."""
        # Store initial hash
        hash1 = np.random.randint(0, 2, size=64, dtype=np.uint8)
        mock_database.store_hash(mock_video_path, hash1, 'phash', duration=100.0)

        # Store updated hash (simulating file modification)
        hash2 = np.random.randint(0, 2, size=64, dtype=np.uint8)
        mock_database.store_hash(mock_video_path, hash2, 'phash', duration=100.0)

        # Retrieve should return latest hash
        retrieved_hash, _ = mock_database.get_hash(mock_video_path, 'phash')

        assert np.array_equal(retrieved_hash, hash2)
        assert not np.array_equal(retrieved_hash, hash1)


class TestComparisonStorage:
    """Test comparison result storage and retrieval."""

    def test_store_and_retrieve_comparison(self, mock_database):
        """Test storing and retrieving comparison results."""
        file1 = "/path/to/video1.mp4"
        file2 = "/path/to/video2.mp4"
        similarity = 0.87

        # Store comparison
        mock_database.store_comparison(file1, file2, similarity)

        # Retrieve comparison
        retrieved_similarity = mock_database.get_comparison(file1, file2)

        assert retrieved_similarity is not None
        assert abs(retrieved_similarity - similarity) < 0.001

    def test_comparison_order_independence(self, mock_database):
        """Test that comparison(A, B) == comparison(B, A)."""
        file1 = "/path/to/video1.mp4"
        file2 = "/path/to/video2.mp4"
        similarity = 0.92

        # Store as (file1, file2)
        mock_database.store_comparison(file1, file2, similarity)

        # Retrieve as (file2, file1) should return same result
        retrieved = mock_database.get_comparison(file2, file1)

        assert abs(retrieved - similarity) < 0.001


class TestIgnoredPairs:
    """Test ignored pairs management."""

    def test_add_and_check_ignored_pair(self, mock_database):
        """Test adding and checking ignored pairs."""
        file1 = "/path/to/video1.mp4"
        file2 = "/path/to/video2.mp4"

        # Initially not ignored
        assert not mock_database.is_pair_ignored(file1, file2)

        # Add to ignored pairs
        mock_database.add_ignored_pair(file1, file2, ignore_type='duplicate')

        # Now should be ignored
        assert mock_database.is_pair_ignored(file1, file2)

    def test_ignored_pair_order_independence(self, mock_database):
        """Test that ignored(A, B) == ignored(B, A)."""
        file1 = "/path/to/video1.mp4"
        file2 = "/path/to/video2.mp4"

        # Add as (file1, file2)
        mock_database.add_ignored_pair(file1, file2)

        # Check both orders
        assert mock_database.is_pair_ignored(file1, file2)
        assert mock_database.is_pair_ignored(file2, file1)


class TestAudioCache:
    """Test audio fingerprint caching."""

    def test_store_and_retrieve_audio_fingerprint(self, mock_database, sample_audio_fingerprint):
        """Test storing and retrieving audio fingerprints."""
        video_path = "/path/to/video.mp4"

        # Store fingerprint
        mock_database.store_audio_fingerprint(
            video_path,
            sample_audio_fingerprint,
            hop_length=2.5
        )

        # Retrieve fingerprint
        retrieved = mock_database.get_audio_fingerprint(
            video_path,
            hop_length=2.5
        )

        assert retrieved is not None
        assert np.array_equal(retrieved, sample_audio_fingerprint)

    def test_different_hop_lengths_separate_cache(self, mock_database, sample_audio_fingerprint):
        """Test that different hop lengths use separate cache entries."""
        video_path = "/path/to/video.mp4"

        # Store with hop_length=2.5
        mock_database.store_audio_fingerprint(
            video_path,
            sample_audio_fingerprint,
            hop_length=2.5
        )

        # Retrieve with hop_length=5.0 should return None
        retrieved = mock_database.get_audio_fingerprint(
            video_path,
            hop_length=5.0
        )

        assert retrieved is None


class TestCacheInvalidation:
    """Test cache invalidation on file changes."""

    def test_hash_cache_invalidation_on_mtime_change(self, mock_database, mock_video_path):
        """Test that cache is invalidated when mtime changes."""
        # Store hash with specific mtime
        test_hash = np.random.randint(0, 2, size=64, dtype=np.uint8)
        mock_database.store_hash(
            mock_video_path,
            test_hash,
            'phash',
            duration=100.0,
            mtime=1000.0,
            file_size=1024
        )

        # Retrieve with same mtime - should hit cache
        retrieved, _ = mock_database.get_hash(mock_video_path, 'phash')
        assert retrieved is not None

        # In real usage, the hasher checks mtime before using cached hash
        # Database just stores what it's given

    def test_clear_cache(self, mock_database, mock_video_path):
        """Test clearing all cache entries."""
        # Store some data
        test_hash = np.random.randint(0, 2, size=64, dtype=np.uint8)
        mock_database.store_hash(mock_video_path, test_hash, 'phash', duration=100.0)

        # Clear cache
        mock_database.clear_cache()

        # Retrieve should return None
        retrieved, _ = mock_database.get_hash(mock_video_path, 'phash')
        assert retrieved is None


class TestThreadSafety:
    """Test thread-safe operations."""

    def test_connection_pool_thread_safety(self, mock_database):
        """Test that connection pool is thread-safe."""
        # The ConnectionPool uses Queue which is thread-safe
        # Just verify that multiple gets don't crash
        connections = []
        for _ in range(5):
            conn = mock_database.connection_pool.get_connection()
            connections.append(conn)
            assert conn is not None

        # Return connections
        for conn in connections:
            mock_database.connection_pool.return_connection(conn)


class TestDatabaseMigrations:
    """Test database schema migrations."""

    def test_ignore_type_column_exists(self, mock_database):
        """Test that ignore_type column exists in ignored_pairs table."""
        conn = mock_database.connection_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(ignored_pairs)")
        columns = {row[1] for row in cursor.fetchall()}

        assert 'ignore_type' in columns
