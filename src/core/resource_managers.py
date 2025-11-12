"""
Resource Management Context Managers

This module provides context managers for proper resource cleanup,
preventing resource leaks and enoning graceful handling of video captures,
database connections, and file operations.
"""

import cv2
import sqlite3
from pathlib import Path
from typing import Optional, Union, Any
from contextlib import contextmanager


class VideoCapture:
    """
    Context manager for OpenCV VideoCapture.

    Enones proper release of video capture resources.
    """

    def __init__(self, video_path: Union[str, Path]):
        """
        Initialize video capture context manager.

        Args:
            video_path: Path to video file
        """
        self.video_path = str(video_path)
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_opened = False

    def __enter__(self) -> cv2.VideoCapture:
        """
        Open video capture.

        Returns:
            OpenCV VideoCapture object

        Raises:
            RuntimeError: If video cannot be opened
        """
        self.cap = cv2.VideoCapture(self.video_path)
        self.is_opened = self.cap.isOpened()

        if not self.is_opened:
            self.cap.release()
            raise RuntimeError(f"Failed to open video: {self.video_path}")

        return self.cap

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Release video capture resources.
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.is_opened = False

    def get_property(self, prop_id: int) -> float:
        """
        Safely get video property.

        Args:
            prop_id: OpenCV property ID (e.g., cv2.CAP_PROP_FRAME_COUNT)

        Returns:
            Property value

        Raises:
            RuntimeError: If capture is not opened
        """
        if not self.is_opened or self.cap is None:
            raise RuntimeError("Video capture is not opened")
        return self.cap.get(prop_id)

    def read_frame(self):
        """
        Safely read a frame.

        Returns:
            Tuple of (success, frame)

        Raises:
            RuntimeError: If capture is not opened
        """
        if not self.is_opened or self.cap is None:
            raise RuntimeError("Video capture is not opened")
        return self.cap.read()


class DatabaseConnection:
    """
    Context manager for SQLite database connections.

    Enones proper connection close and transaction handling.
    """

    def __init__(self,
                 db_path: Union[str, Path],
                 timeout: float = 30.0,
                 isolation_level: Optional[str] = None,
                 check_same_thread: bool = False):
        """
        Initialize database connection context manager.

        Args:
            db_path: Path to SQLite database
            timeout: Connection timeout in seconds
            isolation_level: Transaction isolation level
            check_same_thread: Whether to check thread safety
        """
        self.db_path = str(db_path)
        self.timeout = timeout
        self.isolation_level = isolation_level
        self.check_same_thread = check_same_thread
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def __enter__(self) -> sqlite3.Connection:
        """
        Open database connection.

        Returns:
            SQLite connection object
        """
        self.conn = sqlite3.connect(
            self.db_path,
            timeout=self.timeout,
            isolation_level=self.isolation_level,
            check_same_thread=self.check_same_thread
        )

        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")

        # Set row factory for dict-like access
        self.conn.row_factory = sqlite3.Row

        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Close database connection, committing or rolling back as appropriate.
        """
        if self.conn is not None:
            try:
                if exc_type is None:
                    # No exception - commit transaction
                    self.conn.commit()
                else:
                    # Exception occurred - rollback
                    self.conn.rollback()
            finally:
                self.conn.close()
                self.conn = None


class AtomicFileWrite:
    """
    Context manager for atomic file writes.

    Writes to a temporary file first, then atomically replaces the target.
    This prevents file corruption if writing fails.
    """

    def __init__(self,
                 target_path: Union[str, Path],
                 mode: str = 'w',
                 encoding: str = 'utf-8',
                 create_backup: bool = True):
        """
        Initialize atomic file write context manager.

        Args:
            target_path: Target file path
            mode: File open mode ('w', 'wb', etc.)
            encoding: Text encoding (for text mode)
            create_backup: Whether to create backup of existing file
        """
        self.target_path = Path(target_path)
        self.mode = mode
        self.encoding = encoding if 'b' not in mode else None
        self.create_backup = create_backup

        # Create temp and backup paths
        self.temp_path = self.target_path.with_suffix(self.target_path.suffix + '.tmp')
        self.backup_path = self.target_path.with_suffix(self.target_path.suffix + '.bak')

        self.file_handle = None
        self.success = False

    def __enter__(self):
        """
        Open temporary file for writing.

        Returns:
            File handle
        """
        # Enone parent directory exists
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

        # Open temporary file
        if self.encoding:
            self.file_handle = open(self.temp_path, self.mode, encoding=self.encoding)
        else:
            self.file_handle = open(self.temp_path, self.mode)

        return self.file_handle

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Close file and atomically replace target if successful.
        """
        # Close file handle
        if self.file_handle is not None:
            self.file_handle.close()
            self.file_handle = None

        if exc_type is None:
            # No exception - proceed with atomic replacement
            try:
                # Create backup if requested and target exists
                if self.create_backup and self.target_path.exists():
                    import shutil
                    shutil.copy2(self.target_path, self.backup_path)

                # Atomically replace target with temp file
                self.temp_path.replace(self.target_path)
                self.success = True

                # Remove backup on success
                if self.backup_path.exists():
                    self.backup_path.unlink()

            except Exception as e:
                # Failed to replace - restore from backup if available
                if self.backup_path.exists():
                    self.backup_path.replace(self.target_path)
                raise RuntimeError(f"Failed to atomically write file: {e}")
        else:
            # Exception occurred - clean up temp file
            if self.temp_path.exists():
                self.temp_path.unlink()


class TemporaryFile:
    """
    Context manager for temporary files with automatic cleanup.
    """

    def __init__(self,
                 suffix: str = '',
                 prefix: str = 'tmp',
                 directory: Optional[Union[str, Path]] = None,
                 cleanup_on_error: bool = True):
        """
        Initialize temporary file context manager.

        Args:
            suffix: File suffix (e.g., '.mp4')
            prefix: File prefix
            directory: Directory for temp file (None = system temp)
            cleanup_on_error: Whether to delete file if error occurs
        """
        import tempfile

        self.suffix = suffix
        self.prefix = prefix
        self.directory = directory
        self.cleanup_on_error = cleanup_on_error
        self.path: Optional[Path] = None
        self._fd = None

    def __enter__(self) -> Path:
        """
        Create temporary file.

        Returns:
            Path to temporary file
        """
        import tempfile

        # Create temporary file
        self._fd, temp_path = tempfile.mkstemp(
            suffix=self.suffix,
            prefix=self.prefix,
            dir=self.directory
        )

        self.path = Path(temp_path)
        return self.path

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Close and optionally delete temporary file.
        """
        import os

        # Close file descriptor
        if self._fd is not None:
            try:
                os.close(self._fd)
            except:
                pass
            self._fd = None

        # Delete file if appropriate
        should_delete = (exc_type is None) or self.cleanup_on_error

        if should_delete and self.path and self.path.exists():
            try:
                self.path.unlink()
            except:
                pass


@contextmanager
def managed_video_capture(video_path: Union[str, Path]):
    """
    Context manager function for video capture.

    Usage:
        with managed_video_capture('video.mp4') as cap:
            ret, frame = cap.read()

    Args:
        video_path: Path to video file

    Yields:
        OpenCV VideoCapture object
    """
    with VideoCapture(video_path) as cap:
        yield cap


@contextmanager
def managed_database(db_path: Union[str, Path], **kwargs):
    """
    Context manager function for database connection.

    Usage:
        with managed_database('data.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM table')

    Args:
        db_path: Path to database
        **kwargs: Additional arguments for DatabaseConnection

    Yields:
        SQLite connection object
    """
    with DatabaseConnection(db_path, **kwargs) as conn:
        yield conn


@contextmanager
def atomic_write(target_path: Union[str, Path], **kwargs):
    """
    Context manager function for atomic file writing.

    Usage:
        with atomic_write('output.txt') as f:
            f.write('data')

    Args:
        target_path: Target file path
        **kwargs: Additional arguments for AtomicFileWrite

    Yields:
        File handle
    """
    with AtomicFileWrite(target_path, **kwargs) as f:
        yield f


class ResourcePool:
    """
    Simple resource pool for reusable resources.

    This is useful for expensive-to-create resources like database connections.
    """

    def __init__(self, factory, max_size: int = 5):
        """
        Initialize resource pool.

        Args:
            factory: Callable that creates new resources
            max_size: Maximum pool size
        """
        self.factory = factory
        self.max_size = max_size
        self._available = []
        self._in_use = set()

    def acquire(self) -> Any:
        """
        Acquire a resource from the pool.

        Returns:
            Resource object
        """
        if self._available:
            resource = self._available.pop()
        else:
            resource = self.factory()

        self._in_use.add(id(resource))
        return resource

    def release(self, resource: Any):
        """
        Release a resource back to the pool.

        Args:
            resource: Resource to release
        """
        resource_id = id(resource)

        if resource_id not in self._in_use:
            raise ValueError("Resource not acquired from this pool")

        self._in_use.remove(resource_id)

        if len(self._available) < self.max_size:
            self._available.append(resource)
        else:
            # Pool is full - discard resource
            if hasattr(resource, 'close'):
                resource.close()

    @contextmanager
    def get_resource(self):
        """
        Context manager for pool resources.

        Usage:
            with pool.get_resource() as resource:
                # use resource

        Yields:
            Resource from pool
        """
        resource = self.acquire()
        try:
            yield resource
        finally:
            self.release(resource)

    def clear(self):
        """Close and clear all pooled resources."""
        for resource in self._available:
            if hasattr(resource, 'close'):
                try:
                    resource.close()
                except:
                    pass

        self._available.clear()
        self._in_use.clear()

    def __del__(self):
        """Cleanup on deletion."""
        self.clear()
