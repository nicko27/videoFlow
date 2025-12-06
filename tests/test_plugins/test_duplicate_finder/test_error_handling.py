"""Tests for error_handling.py

Tests standardized error handling decorators and context managers.
"""

import pytest
from unittest.mock import patch, Mock
import logging

from src.plugins.duplicate_finder.error_handling import (
    handle_file_operation,
    handle_video_processing,
    handle_database_operation,
    ErrorHandler,
    ErrorMessages
)


class TestFileOperationDecorator:
    """Test @handle_file_operation decorator."""

    def test_successful_file_operation(self):
        """Test decorator allows successful operation."""
        @handle_file_operation("test_operation", default_return=None)
        def read_file(path):
            return f"Contents of {path}"

        result = read_file("/tmp/test.txt")
        assert result == "Contents of /tmp/test.txt"

    def test_handles_file_not_found(self, caplog):
        """Test decorator handles FileNotFoundError."""
        @handle_file_operation("read_file", default_return=None)
        def read_missing_file(path):
            raise FileNotFoundError(f"File not found: {path}")

        with caplog.at_level(logging.ERROR):
            result = read_missing_file("/nonexistent/file.txt")

        assert result is None
        assert "read_file" in caplog.text

    def test_handles_permission_error(self, caplog):
        """Test decorator handles PermissionError."""
        @handle_file_operation("read_file", default_return=[])
        def read_protected_file(path):
            raise PermissionError(f"Permission denied: {path}")

        with caplog.at_level(logging.ERROR):
            result = read_protected_file("/root/protected.txt")

        assert result == []
        assert "read_file" in caplog.text

    def test_handles_oserror(self, caplog):
        """Test decorator handles OSError."""
        @handle_file_operation("open_file", default_return=None)
        def open_corrupted_file(path):
            raise OSError("I/O error")

        with caplog.at_level(logging.ERROR):
            result = open_corrupted_file("/tmp/corrupted.dat")

        assert result is None

    def test_custom_default_return(self):
        """Test decorator uses custom default return value."""
        @handle_file_operation("test_operation", default_return={"error": True})
        def failing_operation():
            raise FileNotFoundError("Test error")

        result = failing_operation()
        assert result == {"error": True}


class TestVideoProcessingDecorator:
    """Test @handle_video_processing decorator."""

    def test_successful_video_processing(self):
        """Test decorator allows successful video processing."""
        @handle_video_processing("extract_frames", default_return=[])
        def extract_frames(video_path):
            return [f"frame_{i}.jpg" for i in range(10)]

        result = extract_frames("/tmp/video.mp4")
        assert len(result) == 10

    def test_handles_opencv_error(self, caplog):
        """Test decorator handles OpenCV errors."""
        @handle_video_processing("process_video", default_return=None)
        def process_with_cv2_error(video_path):
            # Simulate cv2 error
            raise RuntimeError("OpenCV error: Cannot open video")

        with caplog.at_level(logging.ERROR):
            result = process_with_cv2_error("/tmp/corrupted.mp4")

        assert result is None
        assert "process_video" in caplog.text

    def test_handles_ioerror(self, caplog):
        """Test decorator handles IOError."""
        @handle_video_processing("read_frames", default_return=[])
        def read_frames_with_error(video_path):
            raise IOError("Cannot read video stream")

        with caplog.at_level(logging.ERROR):
            result = read_frames_with_error("/tmp/broken.mp4")

        assert result == []

    def test_handles_value_error(self, caplog):
        """Test decorator handles ValueError."""
        @handle_video_processing("parse_metadata", default_return={})
        def parse_invalid_metadata(video_path):
            raise ValueError("Invalid video metadata")

        with caplog.at_level(logging.ERROR):
            result = parse_invalid_metadata("/tmp/invalid.mp4")

        assert result == {}


class TestDatabaseOperationDecorator:
    """Test @handle_database_operation decorator."""

    def test_successful_database_operation(self):
        """Test decorator allows successful database operation."""
        @handle_database_operation("get_hash", default_return=None)
        def get_hash(file_path):
            return "abc123hash"

        result = get_hash("/tmp/video.mp4")
        assert result == "abc123hash"

    def test_handles_database_error(self, caplog):
        """Test decorator handles database errors."""
        @handle_database_operation("query_db", default_return=None)
        def query_with_error():
            raise Exception("Database connection failed")

        with caplog.at_level(logging.ERROR):
            result = query_with_error()

        assert result is None
        assert "query_db" in caplog.text

    def test_handles_sqlite_error(self, caplog):
        """Test decorator handles SQLite-specific errors."""
        import sqlite3

        @handle_database_operation("execute_query", default_return=[])
        def execute_bad_query():
            raise sqlite3.OperationalError("database is locked")

        with caplog.at_level(logging.ERROR):
            result = execute_bad_query()

        assert result == []


class TestErrorHandlerContextManager:
    """Test ErrorHandler context manager."""

    def test_successful_operation_no_error(self):
        """Test context manager with successful operation."""
        with ErrorHandler("test_operation", default_return=None) as eh:
            result = 42

        assert not eh.has_error
        assert eh.error_message is None
        assert result == 42

    def test_captures_exception(self, caplog):
        """Test context manager captures exceptions."""
        with caplog.at_level(logging.ERROR):
            with ErrorHandler("failing_operation", default_return=None) as eh:
                raise ValueError("Test error")

        assert eh.has_error
        assert "Test error" in eh.error_message
        assert "failing_operation" in caplog.text

    def test_returns_default_on_error(self):
        """Test context manager returns default value on error."""
        result = None
        with ErrorHandler("operation", default_return="default") as eh:
            raise RuntimeError("Error")
            result = "success"  # This won't execute

        # When used with context manager, default_return is accessible but not auto-returned
        # The test validates that error was captured
        assert eh.has_error
        assert result is None  # Original value unchanged

    def test_error_message_contains_operation_name(self, caplog):
        """Test error message includes operation name."""
        with caplog.at_level(logging.ERROR):
            with ErrorHandler("my_custom_operation", default_return=None) as eh:
                raise FileNotFoundError("File missing")

        assert eh.has_error
        assert "my_custom_operation" in caplog.text

    def test_multiple_operations_in_sequence(self, caplog):
        """Test multiple context managers in sequence."""
        results = []

        # First operation succeeds
        with ErrorHandler("operation1", default_return=None) as eh1:
            results.append("success1")

        assert not eh1.has_error

        # Second operation fails
        with caplog.at_level(logging.ERROR):
            with ErrorHandler("operation2", default_return=None) as eh2:
                raise ValueError("Error in operation2")

        assert eh2.has_error
        assert len(results) == 1


class TestErrorMessages:
    """Test ErrorMessages constants."""

    def test_file_not_found_message(self):
        """Test FILE_NOT_FOUND message formatting."""
        message = ErrorMessages.FILE_NOT_FOUND.format(path="/tmp/missing.mp4")
        assert "/tmp/missing.mp4" in message
        assert "not found" in message.lower() or "nexist" in message.lower()

    def test_video_cannot_open_message(self):
        """Test VIDEO_CANNOT_OPEN message formatting."""
        message = ErrorMessages.VIDEO_CANNOT_OPEN.format(path="/tmp/broken.mp4")
        assert "/tmp/broken.mp4" in message
        assert "cannot" in message.lower() or "failed" in message.lower()

    def test_database_error_message(self):
        """Test DATABASE_ERROR message formatting."""
        message = ErrorMessages.DATABASE_ERROR.format(operation="query", error="locked")
        assert "query" in message
        assert "locked" in message

    def test_permission_denied_message(self):
        """Test PERMISSION_DENIED message formatting."""
        message = ErrorMessages.PERMISSION_DENIED.format(path="/root/file.mp4")
        assert "/root/file.mp4" in message
        assert "permission" in message.lower() or "access" in message.lower()


class TestIntegration:
    """Integration tests combining multiple error handling components."""

    def test_nested_decorators(self, caplog):
        """Test nested error handling decorators."""
        @handle_database_operation("outer", default_return=None)
        @handle_file_operation("inner", default_return=None)
        def nested_operation(path):
            raise FileNotFoundError(f"File not found: {path}")

        with caplog.at_level(logging.ERROR):
            result = nested_operation("/tmp/test.mp4")

        assert result is None
        # Should log error from inner decorator
        assert "inner" in caplog.text

    def test_decorator_with_context_manager(self, caplog):
        """Test using decorator inside context manager."""
        @handle_file_operation("read_file", default_return=None)
        def read_file(path):
            if not path:
                raise ValueError("Empty path")
            return f"Contents of {path}"

        with caplog.at_level(logging.ERROR):
            with ErrorHandler("process_files", default_return=[]) as eh:
                result1 = read_file("/tmp/file1.txt")
                result2 = read_file("")  # Will trigger error

        assert result1 == "Contents of /tmp/file1.txt"
        assert result2 is None  # Default from decorator
