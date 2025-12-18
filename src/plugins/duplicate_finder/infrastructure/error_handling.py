"""
Standardized error handling patterns for the duplicate finder plugin.

This module provides consistent error handling patterns across the codebase
to improve debugging, logging, and user experience.
"""

from enum import Enum
from typing import Optional, Callable, Any
from functools import wraps
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.ErrorHandling')


class ErrorSeverity(Enum):
    """Error severity levels."""
    DEBUG = "debug"          # Log only, no user notification
    INFO = "info"            # Informational, may show in UI
    WARNING = "warning"      # Warning, show in UI
    ERROR = "error"          # Error, show dialog
    CRITICAL = "critical"    # Critical error, may crash


class ErrorContext(Enum):
    """Error context types for different scenarios."""
    FILE_OPERATION = "file_operation"
    VIDEO_PROCESSING = "video_processing"
    AUDIO_PROCESSING = "audio_processing"
    DATABASE_OPERATION = "database_operation"
    UI_OPERATION = "ui_operation"
    NETWORK_OPERATION = "network_operation"
    WORKER_THREAD = "worker_thread"


def handle_file_operation(
    operation_name: str,
    on_error: Optional[Callable] = None,
    default_return: Any = None
):
    """
    Decorator for standardized file operation error handling.

    Args:
        operation_name: Name of the operation for logging
        on_error: Optional callback to call on error
        default_return: Default value to return on error

    Example:
        @handle_file_operation("read_video_file", default_return=[])
        def read_frames(video_path):
            # ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FileNotFoundError as e:
                # Log en ERROR pour que caplog au niveau ERROR capture le message
                logger.error(f"{operation_name} - File not found: {e}")
                if on_error:
                    on_error(f"File not found: {e}")
                return default_return
            except PermissionError as e:
                logger.error(f"{operation_name} - Permission denied: {e}")
                if on_error:
                    on_error(f"Permission denied: {e}")
                return default_return
            except OSError as e:
                logger.error(f"{operation_name} - OS error: {e}")
                if on_error:
                    on_error(f"File operation failed: {e}")
                return default_return
            except Exception as e:
                logger.exception(f"{operation_name} - Unexpected error")
                if on_error:
                    on_error(f"Unexpected error: {e}")
                return default_return
        return wrapper
    return decorator


def handle_video_processing(
    operation_name: str,
    on_error: Optional[Callable] = None,
    default_return: Any = None
):
    """
    Decorator for standardized video processing error handling.

    Args:
        operation_name: Name of the operation for logging
        on_error: Optional callback to call on error
        default_return: Default value to return on error

    Example:
        @handle_video_processing("extract_frames", default_return=[])
        def extract_frames(video_path):
            # ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (OSError, IOError) as e:
                logger.error(f"{operation_name} - I/O error: {e}")
                if on_error:
                    on_error(f"Video I/O error: {e}")
                return default_return
            except ValueError as e:
                logger.error(f"{operation_name} - Invalid video data: {e}")
                if on_error:
                    on_error(f"Invalid video: {e}")
                return default_return
            except Exception as e:
                logger.exception(f"{operation_name} - Unexpected error")
                if on_error:
                    on_error(f"Video processing failed: {e}")
                return default_return
        return wrapper
    return decorator


def handle_database_operation(
    operation_name: str,
    on_error: Optional[Callable] = None,
    default_return: Any = None
):
    """
    Decorator for standardized database operation error handling.

    Args:
        operation_name: Name of the operation for logging
        on_error: Optional callback to call on error
        default_return: Default value to return on error

    Example:
        @handle_database_operation("get_hash", default_return=None)
        def get_hash(file_path):
            # ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # All database errors are caught generically
                # since sqlite3 exceptions vary
                logger.error(f"{operation_name} - Database error: {e}")
                if on_error:
                    on_error(f"Database operation failed: {e}")
                return default_return
        return wrapper
    return decorator


def handle_worker_operation(
    operation_name: str,
    error_signal: Optional[Any] = None
):
    """
    Decorator for standardized worker thread error handling.

    Args:
        operation_name: Name of the operation for logging
        error_signal: PyQt signal to emit on error

    Example:
        @handle_worker_operation("process_video", error_signal=self.error)
        def run(self):
            # ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = f"{operation_name} failed: {e}"
                logger.exception(f"Worker error in {operation_name}")
                if error_signal:
                    error_signal.emit(error_msg)
                raise  # Re-raise for worker to handle
        return wrapper
    return decorator


class ErrorHandler:
    """
    Context manager for consistent error handling.

    Example:
        with ErrorHandler("Load video", default_return=None) as eh:
            video = load_video(path)

        if eh.has_error:
            print(f"Error: {eh.error_message}")
    """

    def __init__(
        self,
        operation_name: str,
        context: ErrorContext = ErrorContext.FILE_OPERATION,
        default_return: Any = None,
        on_error: Optional[Callable] = None,
        reraise: bool = False
    ):
        """
        Initialize error handler context.

        Args:
            operation_name: Name of the operation
            context: Type of operation context
            default_return: Value to return on error
            on_error: Optional callback on error
            reraise: Whether to re-raise exception after handling
        """
        self.operation_name = operation_name
        self.context = context
        self.default_return = default_return
        self.on_error = on_error
        self.reraise = reraise
        self.has_error = False
        self.error_message = None
        self.exception = None

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and handle any exception."""
        if exc_type is None:
            # No exception
            return True

        # Store error info
        self.has_error = True
        self.exception = exc_val
        self.error_message = str(exc_val)

        # Log based on exception type
        if exc_type in (FileNotFoundError, PermissionError):
            # Niveau ERROR pour être capturé par les tests et les observateurs
            logger.error(f"{self.operation_name} - {exc_type.__name__}: {exc_val}")
        elif exc_type in (ValueError, TypeError):
            logger.error(f"{self.operation_name} - Invalid data: {exc_val}")
        elif exc_type in (OSError, IOError):
            logger.error(f"{self.operation_name} - I/O error: {exc_val}")
        else:
            logger.exception(f"{self.operation_name} - Unexpected error")

        # Call error callback if provided
        if self.on_error:
            self.on_error(self.error_message)

        # Return False to propagate exception or True to suppress
        if self.reraise:
            return False  # Re-raise
        else:
            return True   # Suppress exception


def safe_execute(
    func: Callable,
    operation_name: str,
    default_return: Any = None,
    *args,
    **kwargs
) -> Any:
    """
    Safely execute a function with error handling.

    Args:
        func: Function to execute
        operation_name: Name for logging
        default_return: Value to return on error
        *args: Arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Function result or default_return on error

    Example:
        result = safe_execute(
            risky_function,
            "process_video",
            default_return=[],
            video_path,
            frame_count=10
        )
    """
    try:
        return func(*args, **kwargs)
    except FileNotFoundError as e:
        logger.warning(f"{operation_name} - File not found: {e}")
        return default_return
    except (OSError, IOError) as e:
        logger.error(f"{operation_name} - I/O error: {e}")
        return default_return
    except (ValueError, TypeError) as e:
        logger.error(f"{operation_name} - Invalid data: {e}")
        return default_return
    except Exception as e:
        logger.exception(f"{operation_name} - Unexpected error")
        return default_return


# Standard error messages for consistency
class ErrorMessages:
    """Standard error messages."""

    # File operations
    FILE_NOT_FOUND = "File not found: {path}"
    FILE_PERMISSION_DENIED = "Permission denied: {path}"
    FILE_TOO_LARGE = "File too large: {path} ({size} bytes)"
    FILE_CORRUPTED = "File appears to be corrupted: {path}"
    PERMISSION_DENIED = "Permission denied: {path}"

    # Video operations
    VIDEO_CANNOT_OPEN = "Cannot open video file: {path}"
    VIDEO_NO_FRAMES = "Video has no frames: {path}"
    VIDEO_INVALID_FORMAT = "Invalid video format: {path}"
    VIDEO_DECODE_ERROR = "Error decoding video: {path}"

    # Audio operations
    AUDIO_EXTRACTION_FAILED = "Audio extraction failed: {path}"
    AUDIO_NO_STREAM = "No audio stream found: {path}"
    AUDIO_INVALID_FORMAT = "Invalid audio format: {path}"

    # Database operations
    DATABASE_CONNECTION_FAILED = "Database connection failed"
    DATABASE_QUERY_FAILED = "Database query failed: {query}"
    DATABASE_LOCKED = "Database is locked, please try again"
    DATABASE_ERROR = "Database error during '{operation}': {error}"

    # Worker operations
    WORKER_TIMEOUT = "Operation timed out after {seconds}s"
    WORKER_CANCELLED = "Operation cancelled by user"
    WORKER_FAILED = "Worker thread failed: {reason}"

    @staticmethod
    def format(template: str, **kwargs) -> str:
        """Format error message with parameters."""
        return template.format(**kwargs)
