"""
Input validation utilities for duplicate finder.

This module provides centralized validation for user inputs and configuration
parameters to prevent crashes and ensure data integrity.
"""

from typing import Any, Dict, Optional
import os
import multiprocessing

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.Validators')


class ConfigValidator:
    """Validator for configuration parameters."""

    # Default values
    DEFAULT_HASH_WORKERS = 4
    DEFAULT_COMPARISON_WORKERS = 4
    DEFAULT_BATCH_SIZE = 50
    DEFAULT_HASH_TIMEOUT = 120
    DEFAULT_COMPARISON_TIMEOUT = 30
    DEFAULT_SIMILARITY_THRESHOLD = 90.0

    # Limits
    MIN_WORKERS = 1
    MAX_WORKERS = multiprocessing.cpu_count() * 2
    MIN_BATCH_SIZE = 1
    MAX_BATCH_SIZE = 500
    MIN_TIMEOUT = 5
    MAX_TIMEOUT = 600
    MIN_THRESHOLD = 50.0
    MAX_THRESHOLD = 100.0

    @staticmethod
    def validate_workers(value: Any, param_name: str = "workers") -> int:
        """
        Validate worker count parameter.

        Args:
            value: The value to validate
            param_name: Name of the parameter for error messages

        Returns:
            Valid worker count (clamped to safe range)

        Raises:
            ValueError: If value cannot be converted to int
        """
        try:
            workers = int(value)
        except (TypeError, ValueError) as e:
            logger.warning(f"Invalid {param_name} '{value}': {e}. Using default.")
            return ConfigValidator.DEFAULT_HASH_WORKERS

        if workers < ConfigValidator.MIN_WORKERS:
            logger.warning(
                f"{param_name}={workers} too low, using minimum: "
                f"{ConfigValidator.MIN_WORKERS}"
            )
            return ConfigValidator.MIN_WORKERS

        if workers > ConfigValidator.MAX_WORKERS:
            logger.warning(
                f"{param_name}={workers} too high, using maximum: "
                f"{ConfigValidator.MAX_WORKERS}"
            )
            return ConfigValidator.MAX_WORKERS

        return workers

    @staticmethod
    def validate_batch_size(value: Any) -> int:
        """
        Validate batch size parameter.

        Args:
            value: The value to validate

        Returns:
            Valid batch size (clamped to safe range)

        Raises:
            ValueError: If value cannot be converted to int
        """
        try:
            batch_size = int(value)
        except (TypeError, ValueError) as e:
            logger.warning(f"Invalid batch_size '{value}': {e}. Using default.")
            return ConfigValidator.DEFAULT_BATCH_SIZE

        if batch_size < ConfigValidator.MIN_BATCH_SIZE:
            logger.warning(
                f"batch_size={batch_size} too low, using minimum: "
                f"{ConfigValidator.MIN_BATCH_SIZE}"
            )
            return ConfigValidator.MIN_BATCH_SIZE

        if batch_size > ConfigValidator.MAX_BATCH_SIZE:
            logger.warning(
                f"batch_size={batch_size} too high, using maximum: "
                f"{ConfigValidator.MAX_BATCH_SIZE}"
            )
            return ConfigValidator.MAX_BATCH_SIZE

        return batch_size

    @staticmethod
    def validate_timeout(value: Any, param_name: str = "timeout") -> int:
        """
        Validate timeout parameter.

        Args:
            value: The value to validate
            param_name: Name of the parameter for error messages

        Returns:
            Valid timeout in seconds (clamped to safe range)
        """
        try:
            timeout = int(value)
        except (TypeError, ValueError) as e:
            logger.warning(f"Invalid {param_name} '{value}': {e}. Using default.")
            return ConfigValidator.DEFAULT_HASH_TIMEOUT

        if timeout < ConfigValidator.MIN_TIMEOUT:
            logger.warning(
                f"{param_name}={timeout} too low, using minimum: "
                f"{ConfigValidator.MIN_TIMEOUT}"
            )
            return ConfigValidator.MIN_TIMEOUT

        if timeout > ConfigValidator.MAX_TIMEOUT:
            logger.warning(
                f"{param_name}={timeout} too high, using maximum: "
                f"{ConfigValidator.MAX_TIMEOUT}"
            )
            return ConfigValidator.MAX_TIMEOUT

        return timeout

    @staticmethod
    def validate_threshold(value: Any) -> float:
        """
        Validate similarity threshold parameter.

        Args:
            value: The value to validate

        Returns:
            Valid threshold percentage (clamped to 50.0-100.0)
        """
        try:
            threshold = float(value)
        except (TypeError, ValueError) as e:
            logger.warning(f"Invalid threshold '{value}': {e}. Using default.")
            return ConfigValidator.DEFAULT_SIMILARITY_THRESHOLD

        if threshold < ConfigValidator.MIN_THRESHOLD:
            logger.warning(
                f"threshold={threshold} too low, using minimum: "
                f"{ConfigValidator.MIN_THRESHOLD}"
            )
            return ConfigValidator.MIN_THRESHOLD

        if threshold > ConfigValidator.MAX_THRESHOLD:
            logger.warning(
                f"threshold={threshold} too high, using maximum: "
                f"{ConfigValidator.MAX_THRESHOLD}"
            )
            return ConfigValidator.MAX_THRESHOLD

        return threshold

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize a complete configuration dictionary.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Validated configuration with sanitized values
        """
        validated = {}

        # Validate hash workers
        if 'hash_workers' in config:
            validated['hash_workers'] = ConfigValidator.validate_workers(
                config['hash_workers'], 'hash_workers'
            )
        else:
            validated['hash_workers'] = ConfigValidator.DEFAULT_HASH_WORKERS

        # Validate comparison workers
        if 'comparison_workers' in config:
            validated['comparison_workers'] = ConfigValidator.validate_workers(
                config['comparison_workers'], 'comparison_workers'
            )
        else:
            validated['comparison_workers'] = ConfigValidator.DEFAULT_COMPARISON_WORKERS

        # Validate batch size
        if 'batch_size' in config:
            validated['batch_size'] = ConfigValidator.validate_batch_size(
                config['batch_size']
            )
        else:
            validated['batch_size'] = ConfigValidator.DEFAULT_BATCH_SIZE

        # Validate hash timeout
        if 'hash_timeout' in config:
            validated['hash_timeout'] = ConfigValidator.validate_timeout(
                config['hash_timeout'], 'hash_timeout'
            )
        else:
            validated['hash_timeout'] = ConfigValidator.DEFAULT_HASH_TIMEOUT

        # Validate comparison timeout
        if 'comparison_timeout' in config:
            validated['comparison_timeout'] = ConfigValidator.validate_timeout(
                config['comparison_timeout'], 'comparison_timeout'
            )
        else:
            validated['comparison_timeout'] = ConfigValidator.DEFAULT_COMPARISON_TIMEOUT

        # Validate similarity threshold
        if 'similarity_threshold' in config:
            validated['similarity_threshold'] = ConfigValidator.validate_threshold(
                config['similarity_threshold']
            )
        else:
            validated['similarity_threshold'] = ConfigValidator.DEFAULT_SIMILARITY_THRESHOLD

        return validated


class FileValidator:
    """Validator for file paths and file operations."""

    MIN_FILE_SIZE_BYTES = 10240  # 10KB minimum

    @staticmethod
    def validate_file_exists(file_path: str) -> bool:
        """
        Validate that a file exists.

        Args:
            file_path: Path to the file

        Returns:
            True if file exists, False otherwise
        """
        if not file_path:
            logger.warning("Empty file path provided")
            return False

        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return False

        if not os.path.isfile(file_path):
            logger.warning(f"Path is not a file: {file_path}")
            return False

        return True

    @staticmethod
    def validate_file_size(file_path: str, min_size: Optional[int] = None) -> bool:
        """
        Validate that a file meets minimum size requirements.

        Args:
            file_path: Path to the file
            min_size: Minimum file size in bytes (default: 10KB)

        Returns:
            True if file meets size requirement, False otherwise
        """
        if not FileValidator.validate_file_exists(file_path):
            return False

        min_size = min_size or FileValidator.MIN_FILE_SIZE_BYTES

        try:
            file_size = os.path.getsize(file_path)
            if file_size < min_size:
                logger.warning(
                    f"File too small ({file_size} bytes < {min_size} bytes): {file_path}"
                )
                return False
            return True
        except OSError as e:
            logger.error(f"Error getting file size for {file_path}: {e}")
            return False

    @staticmethod
    def validate_readable(file_path: str) -> bool:
        """
        Validate that a file is readable.

        Args:
            file_path: Path to the file

        Returns:
            True if file is readable, False otherwise
        """
        if not FileValidator.validate_file_exists(file_path):
            return False

        if not os.access(file_path, os.R_OK):
            logger.warning(f"File is not readable: {file_path}")
            return False

        return True

    @staticmethod
    def validate_video_file(file_path: str) -> bool:
        """
        Validate that a file is a valid video file.

        Performs all checks: existence, size, readability.

        Args:
            file_path: Path to the video file

        Returns:
            True if file passes all validation, False otherwise
        """
        return (
            FileValidator.validate_file_exists(file_path) and
            FileValidator.validate_file_size(file_path) and
            FileValidator.validate_readable(file_path)
        )
