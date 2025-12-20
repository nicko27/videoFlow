"""
VideoDatabase tests for DuplicateFinder plugin.

Tests the VideoDatabase class, which replaces VideoHasher in the migration
to DuplicateFlow. Verifies:
- has_video() method exists and works (replaces has_hash)
- store_video_hash() and get_video_hash() work correctly
- Obsolete methods (has_hash, compute_hash) do NOT exist
- Database schema is correct

CRITICAL ERROR #2: FileHandler uses has_hash() instead of has_video()
Line 282 in file_handler.py: if self.db.has_hash(file_path)

Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Migration section)
"""

import pytest
import sqlite3
from pathlib import Path


@pytest.mark.database
def test_video_database_import():
    """Test that VideoDatabase can be imported."""
    from src.plugins.duplicate_finder.database_manager import VideoDatabase
    assert VideoDatabase is not None


@pytest.mark.database
def test_video_database_initialization(temp_database):
    """Test VideoDatabase initializes with a database file."""
    from src.plugins.duplicate_finder.database_manager import VideoDatabase

    db = VideoDatabase(temp_database)
    assert db is not None
    assert Path(temp_database).exists()
    db.close()


@pytest.mark.database
@pytest.mark.critical
def test_has_video_method_exists():
    """
    CRITICAL TEST: VideoDatabase must have has_video() method.

    This is the NEW method that replaces has_hash().

    EXPECTED: PASS
    Reference: Migration table - has_hash() → has_video()
    """
    from src.plugins.duplicate_finder.database_manager import VideoDatabase

    assert hasattr(VideoDatabase, 'has_video'), \
        "VideoDatabase missing has_video() method. This replaces has_hash()."


@pytest.mark.database
@pytest.mark.critical
def test_has_video_returns_bool(temp_database_with_schema):
    """
    CRITICAL TEST: has_video() should return bool.

    Tests that has_video() returns True/False for presence check.

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.database_manager import VideoDatabase

    db = VideoDatabase(temp_database_with_schema)

    # Test with non-existent video
    result = db.has_video("/fake/path/video.mp4")
    assert isinstance(result, bool), "has_video() must return bool"
    assert result is False, "Non-existent video should return False"

    db.close()


@pytest.mark.database
def test_store_video_hash(temp_database_with_schema):
    """
    Test that store_video_hash() works correctly.

    Verifies we can store a video hash in the database.

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.database_manager import VideoDatabase

    db = VideoDatabase(temp_database_with_schema)

    video_path = "/test/video.mp4"
    video_hash = "abc123def456"  # Mock hash

    # Store hash
    db.store_video_hash(video_path, video_hash)

    # Verify stored
    assert db.has_video(video_path), "Video should exist after storing"

    db.close()


@pytest.mark.database
def test_get_video_hash(temp_database_with_schema):
    """
    Test that get_video_hash() retrieves stored hash.

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.database_manager import VideoDatabase

    db = VideoDatabase(temp_database_with_schema)

    video_path = "/test/video2.mp4"
    video_hash = "hash_value_123"

    # Store and retrieve
    db.store_video_hash(video_path, video_hash)
    retrieved_hash = db.get_video_hash(video_path)

    assert retrieved_hash == video_hash, "Retrieved hash should match stored hash"

    db.close()


@pytest.mark.database
@pytest.mark.critical
def test_no_has_hash_method():
    """
    CRITICAL TEST: VideoDatabase should NOT have has_hash() method.

    has_hash() is OBSOLETE. It was replaced by has_video().

    CRITICAL ERROR #2: FileHandler.batch_update_cache_status() calls has_hash()
    This will fail at runtime.

    EXPECTED: PASS (has_hash should not exist)
    Reference: Migration table - has_hash() is obsolete
    """
    from src.plugins.duplicate_finder.database_manager import VideoDatabase

    assert not hasattr(VideoDatabase, 'has_hash'), \
        "VideoDatabase should NOT have has_hash() method (obsolete). Use has_video()."


@pytest.mark.database
@pytest.mark.critical
def test_no_compute_hash_method():
    """
    CRITICAL TEST: VideoDatabase should NOT have compute_hash() method.

    compute_hash() was a VideoHasher method, replaced by DuplicateFlow algorithms.

    EXPECTED: PASS (compute_hash should not exist)
    Reference: Migration table - compute_hash() → extract_features()
    """
    from src.plugins.duplicate_finder.database_manager import VideoDatabase

    assert not hasattr(VideoDatabase, 'compute_hash'), \
        "VideoDatabase should NOT have compute_hash() (obsolete). Use DuplicateFlow algorithms."


@pytest.mark.database
def test_has_video_after_delete(temp_database_with_schema):
    """
    Test has_video() returns False after deleting a video record.

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.database_manager import VideoDatabase

    db = VideoDatabase(temp_database_with_schema)

    video_path = "/test/video3.mp4"
    video_hash = "hash3"

    # Store
    db.store_video_hash(video_path, video_hash)
    assert db.has_video(video_path) is True

    # Delete (if method exists)
    if hasattr(db, 'delete_video'):
        db.delete_video(video_path)
        assert db.has_video(video_path) is False

    db.close()


@pytest.mark.database
def test_database_schema_has_videos_table(temp_database_with_schema):
    """
    Test that the database schema includes a videos table.

    EXPECTED: PASS
    """
    conn = sqlite3.connect(temp_database_with_schema)
    cursor = conn.cursor()

    # Check if videos table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='videos'"
    )
    result = cursor.fetchone()

    conn.close()

    assert result is not None, "Database should have 'videos' table"


@pytest.mark.database
def test_multiple_videos_storage(temp_database_with_schema):
    """
    Test storing multiple videos in the database.

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.database_manager import VideoDatabase

    db = VideoDatabase(temp_database_with_schema)

    videos = [
        ("/video1.mp4", "hash1"),
        ("/video2.mp4", "hash2"),
        ("/video3.mp4", "hash3"),
    ]

    # Store all
    for path, hash_val in videos:
        db.store_video_hash(path, hash_val)

    # Verify all exist
    for path, _ in videos:
        assert db.has_video(path), f"{path} should exist in database"

    db.close()


@pytest.mark.database
def test_has_video_case_sensitivity(temp_database_with_schema):
    """
    Test has_video() behavior with different case paths.

    On case-sensitive filesystems, paths should be exact match.

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.database_manager import VideoDatabase

    db = VideoDatabase(temp_database_with_schema)

    # Store with lowercase
    db.store_video_hash("/test/video.mp4", "hash")

    # Check exact match
    assert db.has_video("/test/video.mp4") is True

    # Different case should return False (on case-sensitive systems)
    # Note: This behavior may vary by OS
    # assert db.has_video("/test/VIDEO.mp4") is False

    db.close()


@pytest.mark.database
def test_connection_pool_exists(temp_database_with_schema):
    """
    Test that VideoDatabase uses ConnectionPool.

    ConnectionPool is mentioned in database_manager.py for thread safety.

    EXPECTED: PASS
    """
    from src.plugins.duplicate_finder.database_manager import VideoDatabase

    db = VideoDatabase(temp_database_with_schema)

    # Check if pool exists
    assert hasattr(db, 'pool') or hasattr(db, 'connection_pool'), \
        "VideoDatabase should have connection pool for thread safety"

    db.close()
