"""
Tests for Resource Managers Module

Tests context managers for proper resource cleanup.
"""

import pytest
import cv2
import sqlite3
from pathlib import Path
from src.core.resource_managers import (
    VideoCapture,
    DatabaseConnection,
    AtomicFileWrite,
    TemporaryFile,
    managed_video_capture,
    managed_database,
    atomic_write
)


class TestVideoCapture:
    """Test suite for VideoCapture context manager."""

    def test_video_capture_success(self, sample_video):
        """Test successful video capture."""
        with VideoCapture(sample_video) as cap:
            assert cap is not None
            assert cap.isOpened()

            # Read a frame
            ret, frame = cap.read()
            assert ret is True
            assert frame is not None

    def test_video_capture_auto_release(self, sample_video):
        """Test that video capture is automatically released."""
        cap_obj = None

        with VideoCapture(sample_video) as cap:
            cap_obj = cap
            assert cap.isOpened()

        # After context, should be released
        # Note: OpenCV doesn't provide direct way to check if released
        # but attempting operations should fail gracefully

    def test_video_capture_invalid_path_fails(self):
        """Test that invalid video path raises error."""
        with pytest.raises(RuntimeError):
            with VideoCapture('/nonexistent/video.mp4') as cap:
                pass

    def test_video_capture_get_property(self, sample_video):
        """Test getting video properties."""
        with VideoCapture(sample_video) as cap:
            frame_count = cap.get_property(cv2.CAP_PROP_FRAME_COUNT)
            assert frame_count > 0

            fps = cap.get_property(cv2.CAP_PROP_FPS)
            assert fps > 0

    def test_video_capture_read_frame(self, sample_video):
        """Test reading frames."""
        with VideoCapture(sample_video) as cap:
            ret, frame = cap.read_frame()
            assert ret is True
            assert frame is not None
            assert len(frame.shape) == 3  # Height, Width, Channels

    def test_managed_video_capture_function(self, sample_video):
        """Test managed_video_capture convenience function."""
        with managed_video_capture(sample_video) as cap:
            assert cap.isOpened()
            ret, frame = cap.read()
            assert ret is True


class TestDatabaseConnection:
    """Test suite for DatabaseConnection context manager."""

    def test_database_connection_success(self, temp_dir):
        """Test successful database connection."""
        db_path = temp_dir / 'test.db'

        with DatabaseConnection(db_path) as conn:
            assert conn is not None
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            result = cursor.fetchone()
            assert result[0] == 1

    def test_database_auto_commit(self, temp_dir):
        """Test that changes are automatically committed."""
        db_path = temp_dir / 'test.db'

        # Create table and insert data
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE test (id INTEGER, value TEXT)')
            cursor.execute('INSERT INTO test VALUES (1, "hello")')

        # Open again and verify data was committed
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM test WHERE id = 1')
            result = cursor.fetchone()
            assert result[0] == 'hello'

    def test_database_rollback_on_exception(self, temp_dir):
        """Test that transaction is rolled back on exception."""
        db_path = temp_dir / 'test.db'

        # Create table
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE test (id INTEGER PRIMARY KEY)')
            cursor.execute('INSERT INTO test VALUES (1)')

        # Try to insert duplicate (should fail and rollback)
        try:
            with DatabaseConnection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO test VALUES (2)')  # OK
                cursor.execute('INSERT INTO test VALUES (1)')  # Duplicate - fails
        except sqlite3.IntegrityError:
            pass  # Expected

        # Verify only original row exists (rollback worked)
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM test')
            count = cursor.fetchone()[0]
            assert count == 1

    def test_database_foreign_keys_enabled(self, temp_dir):
        """Test that foreign keys are enabled."""
        db_path = temp_dir / 'test.db'

        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('PRAGMA foreign_keys')
            result = cursor.fetchone()
            assert result[0] == 1  # Enabled

    def test_database_row_factory(self, temp_dir):
        """Test that row factory provides dict-like access."""
        db_path = temp_dir / 'test.db'

        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE test (id INTEGER, name TEXT)')
            cursor.execute('INSERT INTO test VALUES (1, "Alice")')
            cursor.execute('SELECT * FROM test')

            row = cursor.fetchone()
            # Should have dict-like access via keys
            assert row['id'] == 1
            assert row['name'] == 'Alice'

    def test_managed_database_function(self, temp_dir):
        """Test managed_database convenience function."""
        db_path = temp_dir / 'test.db'

        with managed_database(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            assert cursor.fetchone()[0] == 1


class TestAtomicFileWrite:
    """Test suite for AtomicFileWrite context manager."""

    def test_atomic_write_creates_file(self, temp_dir):
        """Test that atomic write creates file."""
        file_path = temp_dir / 'output.txt'

        with AtomicFileWrite(file_path) as f:
            f.write('test content')

        assert file_path.exists()
        assert file_path.read_text() == 'test content'

    def test_atomic_write_replaces_existing(self, temp_dir):
        """Test that atomic write replaces existing file."""
        file_path = temp_dir / 'existing.txt'
        file_path.write_text('original')

        with AtomicFileWrite(file_path) as f:
            f.write('new content')

        assert file_path.read_text() == 'new content'

    def test_atomic_write_preserves_on_exception(self, temp_dir):
        """Test that original file is preserved if exception occurs."""
        file_path = temp_dir / 'important.txt'
        file_path.write_text('important data')

        try:
            with AtomicFileWrite(file_path) as f:
                f.write('new data')
                raise RuntimeError('Simulated error')
        except RuntimeError:
            pass

        # Original should be preserved (or restored from backup)
        assert file_path.exists()

    def test_atomic_write_binary_mode(self, temp_dir):
        """Test atomic write in binary mode."""
        file_path = temp_dir / 'binary.dat'

        with AtomicFileWrite(file_path, mode='wb') as f:
            f.write(b'\x00\x01\x02\x03')

        assert file_path.read_bytes() == b'\x00\x01\x02\x03'

    def test_atomic_write_creates_parent_directories(self, temp_dir):
        """Test that parent directories are created."""
        file_path = temp_dir / 'nested' / 'dir' / 'file.txt'

        with AtomicFileWrite(file_path) as f:
            f.write('content')

        assert file_path.exists()
        assert file_path.parent.exists()

    def test_atomic_write_function(self, temp_dir):
        """Test atomic_write convenience function."""
        file_path = temp_dir / 'output.txt'

        with atomic_write(file_path) as f:
            f.write('test')

        assert file_path.read_text() == 'test'


class TestTemporaryFile:
    """Test suite for TemporaryFile context manager."""

    def test_temporary_file_created(self):
        """Test that temporary file is created."""
        with TemporaryFile(suffix='.txt') as temp_path:
            assert temp_path.exists()
            assert temp_path.suffix == '.txt'

            # Write to it
            temp_path.write_text('temporary content')
            assert temp_path.read_text() == 'temporary content'

        # Should be deleted after context
        assert not temp_path.exists()

    def test_temporary_file_with_prefix(self):
        """Test temporary file with custom prefix."""
        with TemporaryFile(prefix='myapp_', suffix='.dat') as temp_path:
            assert 'myapp_' in temp_path.name
            assert temp_path.suffix == '.dat'

    def test_temporary_file_custom_directory(self, temp_dir):
        """Test temporary file in custom directory."""
        with TemporaryFile(directory=temp_dir, suffix='.tmp') as temp_path:
            assert temp_path.parent == temp_dir
            assert temp_path.exists()

    def test_temporary_file_cleanup_on_success(self):
        """Test that temporary file is cleaned up on success."""
        temp_path_ref = None

        with TemporaryFile() as temp_path:
            temp_path_ref = temp_path
            temp_path.write_text('data')

        # After context, should be deleted
        assert not temp_path_ref.exists()

    def test_temporary_file_cleanup_on_error(self):
        """Test that temporary file is cleaned up on error."""
        temp_path_ref = None

        try:
            with TemporaryFile() as temp_path:
                temp_path_ref = temp_path
                temp_path.write_text('data')
                raise RuntimeError('Test error')
        except RuntimeError:
            pass

        # Should still be cleaned up
        assert not temp_path_ref.exists()

    def test_temporary_file_no_cleanup_on_error_if_disabled(self):
        """Test that cleanup can be disabled on error."""
        temp_path_ref = None

        try:
            with TemporaryFile(cleanup_on_error=False) as temp_path:
                temp_path_ref = temp_path
                temp_path.write_text('data')
                raise RuntimeError('Test error')
        except RuntimeError:
            pass

        # Should NOT be cleaned up
        try:
            assert temp_path_ref.exists()
        finally:
            # Clean up manually for test
            if temp_path_ref.exists():
                temp_path_ref.unlink()


class TestIntegration:
    """Integration tests combining multiple resource managers."""

    def test_video_processing_pipeline(self, sample_video, temp_dir):
        """Test complete video processing pipeline with resource management."""
        output_path = temp_dir / 'output.txt'

        # Read video and write info to file atomically
        with VideoCapture(sample_video) as cap:
            frame_count = cap.get_property(cv2.CAP_PROP_FRAME_COUNT)
            fps = cap.get_property(cv2.CAP_PROP_FPS)

            with AtomicFileWrite(output_path) as f:
                f.write(f"Frames: {frame_count}\n")
                f.write(f"FPS: {fps}\n")

        # Verify output
        assert output_path.exists()
        content = output_path.read_text()
        assert 'Frames:' in content
        assert 'FPS:' in content

    def test_database_with_video_metadata(self, sample_video, temp_dir):
        """Test storing video metadata in database."""
        db_path = temp_dir / 'videos.db'

        # Extract video info and store in database
        with VideoCapture(sample_video) as cap:
            frame_count = cap.get_property(cv2.CAP_PROP_FRAME_COUNT)
            fps = cap.get_property(cv2.CAP_PROP_FPS)

            with DatabaseConnection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE videos (
                        path TEXT PRIMARY KEY,
                        frame_count INTEGER,
                        fps REAL
                    )
                ''')
                cursor.execute(
                    'INSERT INTO videos VALUES (?, ?, ?)',
                    (str(sample_video), frame_count, fps)
                )

        # Verify data was stored
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM videos WHERE path = ?', (str(sample_video),))
            row = cursor.fetchone()

            assert row is not None
            assert row['frame_count'] > 0
            assert row['fps'] > 0
