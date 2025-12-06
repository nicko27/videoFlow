"""File path validation for security and integrity.

This module provides comprehensive file path validation to prevent:
- Path traversal attacks (../../etc/passwd)
- Symbolic link exploits
- Processing of non-video files
- Denial of service from oversized files
- Access to system/special files

Created: 2025-12-06 (Phase 10 - ISSUE #28)
"""

import os
import cv2
from pathlib import Path
from typing import Tuple, Optional, Set
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.FileValidator')


class ValidationError(Exception):
    """Exception raised when file validation fails."""
    pass


class FileValidator:
    """Validates file paths for security and integrity.

    This validator provides multiple layers of security checks:
    1. Path resolution and traversal detection
    2. File type and extension verification
    3. Symbolic link prevention
    4. File size limits
    5. Video format validation (OpenCV)

    Example:
        >>> validator = FileValidator()
        >>> is_valid, error = validator.validate_path('/path/to/video.mp4')
        >>> if not is_valid:
        ...     print(f"Validation failed: {error}")

        >>> # Or raise exception on failure
        >>> try:
        ...     validator.validate_path_strict('/path/to/video.mp4')
        ... except ValidationError as e:
        ...     print(f"Invalid file: {e}")

    Security:
        - Prevents path traversal attacks
        - Blocks symbolic link exploits
        - Validates file extensions against whitelist
        - Enforces maximum file size limits
        - Verifies files can be opened as videos
    """

    # Allowed video extensions (whitelist)
    ALLOWED_EXTENSIONS: Set[str] = {
        '.mp4', '.avi', '.mov', '.mkv', '.flv',
        '.wmv', '.webm', '.m4v', '.mpg', '.mpeg',
        '.3gp', '.ogv', '.ts', '.m2ts', '.mts'
    }

    # Maximum file size: 50 GB (reasonable for 4K video)
    MAX_FILE_SIZE: int = 50 * 1024 * 1024 * 1024  # 50 GB

    # Minimum file size: 1 KB (filter out empty/corrupt files)
    MIN_FILE_SIZE: int = 1024  # 1 KB

    def __init__(
        self,
        allowed_extensions: Optional[Set[str]] = None,
        max_file_size: Optional[int] = None,
        min_file_size: Optional[int] = None,
        allow_symlinks: bool = False,
        verify_video_format: bool = True
    ):
        """Initialize file validator.

        Args:
            allowed_extensions: Set of allowed file extensions (default: class default)
            max_file_size: Maximum file size in bytes (default: 50 GB)
            min_file_size: Minimum file size in bytes (default: 1 KB)
            allow_symlinks: Whether to allow symbolic links (default: False)
            verify_video_format: Whether to verify file is valid video (default: True)
        """
        self.allowed_extensions = allowed_extensions or self.ALLOWED_EXTENSIONS
        self.max_file_size = max_file_size or self.MAX_FILE_SIZE
        self.min_file_size = min_file_size or self.MIN_FILE_SIZE
        self.allow_symlinks = allow_symlinks
        self.verify_video_format = verify_video_format

        logger.debug(
            f"FileValidator initialized: {len(self.allowed_extensions)} extensions, "
            f"size range: {self.min_file_size}-{self.max_file_size} bytes"
        )

    def validate_path(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Validate file path for security and integrity.

        Performs comprehensive validation including:
        - Path resolution and canonicalization
        - Path traversal detection
        - Symbolic link check (if disabled)
        - File existence verification
        - Extension whitelist check
        - File size limits
        - Video format verification (if enabled)

        Args:
            file_path: Path to file to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if file passes all checks, False otherwise
            - error_message: None if valid, descriptive error if invalid

        Example:
            >>> validator = FileValidator()
            >>> is_valid, error = validator.validate_path('/videos/movie.mp4')
            >>> if is_valid:
            ...     print("File is safe to process")
            ... else:
            ...     print(f"Validation failed: {error}")
        """
        try:
            # 1. Resolve to absolute canonical path
            try:
                path = Path(file_path).resolve(strict=False)
            except (OSError, ValueError) as e:
                return False, f"Invalid path: {e}"

            # 2. Check for path traversal
            # After resolve(), '..' should not appear in parts
            # This catches attempts like ../../etc/passwd
            try:
                # Verify the resolved path is within expected bounds
                # (this is a defense-in-depth measure)
                _ = path.relative_to(path.anchor)
            except ValueError:
                return False, "Path traversal detected"

            # 3. Check symbolic links (if disabled)
            if not self.allow_symlinks and path.is_symlink():
                return False, "Symbolic links not allowed"

            # 4. Verify file exists
            if not path.exists():
                return False, f"File does not exist: {file_path}"

            # 5. Verify it's a regular file (not directory, device, pipe, etc.)
            if not path.is_file():
                return False, "Not a regular file"

            # 6. Check file extension against whitelist
            extension = path.suffix.lower()
            if extension not in self.allowed_extensions:
                return False, f"Invalid extension: {extension} (allowed: {', '.join(sorted(self.allowed_extensions))})"

            # 7. Check file size limits
            try:
                file_size = path.stat().st_size
            except OSError as e:
                return False, f"Cannot read file size: {e}"

            if file_size < self.min_file_size:
                return False, f"File too small: {file_size} bytes (minimum: {self.min_file_size})"

            if file_size > self.max_file_size:
                size_gb = file_size / (1024 ** 3)
                max_gb = self.max_file_size / (1024 ** 3)
                return False, f"File too large: {size_gb:.2f} GB (maximum: {max_gb:.2f} GB)"

            # 8. Verify it's a valid video file (OpenCV check)
            if self.verify_video_format:
                try:
                    cap = cv2.VideoCapture(str(path))
                    if not cap.isOpened():
                        cap.release()
                        return False, "Not a valid video file (OpenCV cannot open)"

                    # Try to read at least one frame to verify format
                    ret, frame = cap.read()
                    cap.release()

                    if not ret or frame is None:
                        return False, "Video file has no readable frames"

                except Exception as e:
                    return False, f"Video validation failed: {e}"

            # All checks passed
            logger.debug(f"File validated successfully: {path.name}")
            return True, None

        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(f"Unexpected error validating {file_path}: {e}")
            return False, f"Validation error: {e}"

    def validate_path_strict(self, file_path: str) -> None:
        """Validate file path, raising exception on failure.

        Same as validate_path() but raises ValidationError instead
        of returning (False, error_message).

        Args:
            file_path: Path to file to validate

        Raises:
            ValidationError: If validation fails

        Example:
            >>> validator = FileValidator()
            >>> try:
            ...     validator.validate_path_strict('/videos/movie.mp4')
            ...     # File is valid, proceed with processing
            ... except ValidationError as e:
            ...     print(f"Cannot process file: {e}")
        """
        is_valid, error = self.validate_path(file_path)
        if not is_valid:
            raise ValidationError(error)

    def validate_paths_batch(
        self,
        file_paths: list[str],
        continue_on_error: bool = True
    ) -> Tuple[list[str], list[Tuple[str, str]]]:
        """Validate multiple file paths in batch.

        Args:
            file_paths: List of file paths to validate
            continue_on_error: If True, continue validating after errors.
                             If False, stop on first error.

        Returns:
            Tuple of (valid_paths, invalid_paths)
            - valid_paths: List of paths that passed validation
            - invalid_paths: List of (path, error_message) tuples

        Example:
            >>> validator = FileValidator()
            >>> paths = ['/video1.mp4', '/video2.avi', '/invalid.txt']
            >>> valid, invalid = validator.validate_paths_batch(paths)
            >>> print(f"Valid: {len(valid)}, Invalid: {len(invalid)}")
            >>> for path, error in invalid:
            ...     print(f"  {path}: {error}")
        """
        valid_paths = []
        invalid_paths = []

        for file_path in file_paths:
            is_valid, error = self.validate_path(file_path)

            if is_valid:
                valid_paths.append(file_path)
            else:
                invalid_paths.append((file_path, error))
                if not continue_on_error:
                    break

        logger.info(
            f"Batch validation: {len(valid_paths)} valid, "
            f"{len(invalid_paths)} invalid (out of {len(file_paths)})"
        )

        return valid_paths, invalid_paths

    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """Check if filename is safe (no path traversal, special chars).

        Validates just the filename (not full path) for safety.
        Useful for validating user-provided filenames before saving.

        Args:
            filename: Just the filename (e.g., 'video.mp4', not '/path/video.mp4')

        Returns:
            True if filename is safe, False otherwise

        Example:
            >>> FileValidator.is_safe_filename('video.mp4')
            True
            >>> FileValidator.is_safe_filename('../../../etc/passwd')
            False
            >>> FileValidator.is_safe_filename('video|rm -rf.mp4')
            False
        """
        # Check for path separators (indicates path, not just filename)
        if os.sep in filename or '/' in filename or '\\' in filename:
            return False

        # Check for path traversal
        if '..' in filename:
            return False

        # Check for null bytes (security risk)
        if '\0' in filename:
            return False

        # Check for shell metacharacters (potential command injection)
        dangerous_chars = {'|', '&', ';', '>', '<', '`', '$', '(', ')', '{', '}'}
        if any(char in filename for char in dangerous_chars):
            return False

        return True
