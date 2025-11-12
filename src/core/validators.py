"""
Input Validation and Sanitization Utilities

This module provides validation and sanitization functions to prevent
security vulnerabilities like command injection and path traversal.
"""

import re
from pathlib import Path
from typing import List, Optional, Union, Tuple
from .config import Config


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class PathValidator:
    """
    Validator for file and directory paths.

    Prevents path traversal attacks and validates path constraints.
    """

    @staticmethod
    def validate_path(path: Union[str, Path],
                     must_exist: bool = False,
                     must_be_file: bool = False,
                     must_be_dir: bool = False,
                     allow_symlinks: bool = None) -> Path:
        """
        Validate a file or directory path.

        Args:
            path: Path to validate
            must_exist: If True, path must exist
            must_be_file: If True, path must be a file
            must_be_dir: If True, path must be a directory
            allow_symlinks: If False, reject symlinks (uses config default if None)

        Returns:
            Validated Path object

        Raises:
            ValidationError: If validation fails
        """
        if allow_symlinks is None:
            allow_symlinks = Config.SECURITY['allow_symlinks']

        try:
            path = Path(path).resolve()
        except Exception as e:
            raise ValidationError(f"Invalid path: {e}")

        # Check path length
        if len(str(path)) > Config.SECURITY['max_path_length']:
            raise ValidationError(f"Path too long (max {Config.SECURITY['max_path_length']})")

        # Check for symlinks
        if not allow_symlinks and path.is_symlink():
            raise ValidationError("Symlinks are not allowed")

        # Check existence
        if must_exist and not path.exists():
            raise ValidationError(f"Path does not exist: {path}")

        # Check file/directory type
        if must_be_file and path.exists() and not path.is_file():
            raise ValidationError(f"Path is not a file: {path}")

        if must_be_dir and path.exists() and not path.is_dir():
            raise ValidationError(f"Path is not a directory: {path}")

        return path

    @staticmethod
    def validate_video_file(path: Union[str, Path]) -> Path:
        """
        Validate that a path points to a video file.

        Args:
            path: Path to validate

        Returns:
            Validated Path object

        Raises:
            ValidationError: If validation fails
        """
        path = PathValidator.validate_path(path, must_exist=True, must_be_file=True)

        # Check extension
        if path.suffix.lower() not in Config.VIDEO['supported_extensions']:
            raise ValidationError(
                f"Unsupported video format: {path.suffix}\n"
                f"Supported: {', '.join(Config.VIDEO['supported_extensions'])}"
            )

        return path

    @staticmethod
    def validate_output_path(path: Union[str, Path],
                           overwrite: bool = False) -> Path:
        """
        Validate an output path for writing.

        Args:
            path: Output path to validate
            overwrite: If True, allow overwriting existing files

        Returns:
            Validated Path object

        Raises:
            ValidationError: If validation fails
        """
        path = PathValidator.validate_path(path)

        # Check if parent directory exists
        if not path.parent.exists():
            raise ValidationError(f"Parent directory does not exist: {path.parent}")

        # Check if file exists
        if path.exists() and not overwrite:
            raise ValidationError(f"Output file already exists: {path}")

        # Check write permissions
        if not path.parent.is_dir():
            raise ValidationError(f"Parent is not a directory: {path.parent}")

        return path

    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """
        Check if a filename is safe (no path traversal attempts).

        Args:
            filename: Filename to check

        Returns:
            True if safe, False otherwise
        """
        # Reject path separators and parent directory references
        unsafe_patterns = ['..', '/', '\\', '\x00']
        return not any(pattern in filename for pattern in unsafe_patterns)


class FFmpegValidator:
    """
    Validator for FFmpeg command parameters.

    Prevents command injection vulnerabilities.
    """

    @staticmethod
    def validate_codec(codec: str) -> str:
        """
        Validate codec parameter.

        Args:
            codec: Codec name to validate

        Returns:
            Validated codec name

        Raises:
            ValidationError: If codec is not allowed
        """
        if codec not in Config.FFMPEG['allowed_codecs']:
            raise ValidationError(
                f"Codec '{codec}' is not allowed.\n"
                f"Allowed codecs: {', '.join(Config.FFMPEG['allowed_codecs'])}"
            )
        return codec

    @staticmethod
    def validate_preset(preset: str) -> str:
        """
        Validate preset parameter.

        Args:
            preset: Preset name to validate

        Returns:
            Validated preset name

        Raises:
            ValidationError: If preset is not allowed
        """
        if preset not in Config.FFMPEG['allowed_presets']:
            raise ValidationError(
                f"Preset '{preset}' is not allowed.\n"
                f"Allowed presets: {', '.join(Config.FFMPEG['allowed_presets'])}"
            )
        return preset

    @staticmethod
    def validate_crf(crf: Union[int, str]) -> int:
        """
        Validate CRF (Constant Rate Factor) value.

        Args:
            crf: CRF value to validate

        Returns:
            Validated CRF as integer

        Raises:
            ValidationError: If CRF is out of range
        """
        try:
            crf_int = int(crf)
        except (ValueError, TypeError):
            raise ValidationError(f"CRF must be an integer, got: {crf}")

        if not 0 <= crf_int <= 51:
            raise ValidationError(f"CRF must be between 0 and 51, got: {crf_int}")

        return crf_int

    @staticmethod
    def validate_bitrate(bitrate: str) -> str:
        """
        Validate bitrate parameter.

        Args:
            bitrate: Bitrate string (e.g., '128k', '1M')

        Returns:
            Validated bitrate string

        Raises:
            ValidationError: If bitrate format is invalid
        """
        # Match patterns like: 128k, 1M, 500K, 2m
        pattern = r'^\d+[kKmM]$'
        if not re.match(pattern, bitrate):
            raise ValidationError(
                f"Invalid bitrate format: {bitrate}\n"
                f"Expected format: <number>[k|K|m|M] (e.g., '128k', '1M')"
            )
        return bitrate

    @staticmethod
    def validate_resolution(resolution: str) -> Tuple[int, int]:
        """
        Validate resolution parameter.

        Args:
            resolution: Resolution string (e.g., '1920x1080')

        Returns:
            Tuple of (width, height)

        Raises:
            ValidationError: If resolution format is invalid
        """
        if resolution.lower() == 'original':
            return None

        # Match patterns like: 1920x1080, 1280x720
        pattern = r'^(\d+)x(\d+)$'
        match = re.match(pattern, resolution)

        if not match:
            raise ValidationError(
                f"Invalid resolution format: {resolution}\n"
                f"Expected format: <width>x<height> (e.g., '1920x1080')"
            )

        width, height = int(match.group(1)), int(match.group(2))

        # Validate reasonable ranges
        if not (1 <= width <= 16384 and 1 <= height <= 16384):
            raise ValidationError(
                f"Resolution out of range: {width}x{height}\n"
                f"Width and height must be between 1 and 16384"
            )

        return width, height

    @staticmethod
    def validate_fps(fps: Union[str, int, float]) -> Optional[float]:
        """
        Validate FPS (frames per second) parameter.

        Args:
            fps: FPS value to validate

        Returns:
            Validated FPS as float, or None for 'original'

        Raises:
            ValidationError: If FPS is invalid
        """
        if isinstance(fps, str) and fps.lower() == 'original':
            return None

        try:
            fps_float = float(fps)
        except (ValueError, TypeError):
            raise ValidationError(f"FPS must be a number, got: {fps}")

        if not 1 <= fps_float <= 240:
            raise ValidationError(
                f"FPS out of range: {fps_float}\n"
                f"FPS must be between 1 and 240"
            )

        return fps_float

    @staticmethod
    def sanitize_parameter(param: str) -> str:
        """
        Sanitize a generic FFmpeg parameter.

        Removes potentially dangerous characters.

        Args:
            param: Parameter string to sanitize

        Returns:
            Sanitized parameter string

        Raises:
            ValidationError: If parameter contains disallowed characters
        """
        if not Config.SECURITY['sanitize_ffmpeg_params']:
            return param

        # Check against allowed characters pattern
        allowed_pattern = Config.SECURITY['allowed_param_chars']

        if not re.match(f'^{allowed_pattern}+$', param):
            raise ValidationError(
                f"Parameter contains disallowed characters: {param}\n"
                f"Allowed pattern: {allowed_pattern}"
            )

        # Additional checks for command injection attempts
        dangerous_patterns = [
            ';', '|', '&', '$', '`', '$(', '&&', '||',
            '\n', '\r', '>', '<', '*', '?', '[', ']',
            '{', '}', '~', '!', '^'
        ]

        for pattern in dangerous_patterns:
            if pattern in param:
                raise ValidationError(
                    f"Parameter contains potentially dangerous sequence: {pattern}"
                )

        return param

    @staticmethod
    def build_safe_command(base_command: List[str],
                          input_file: Union[str, Path],
                          output_file: Union[str, Path],
                          codec: Optional[str] = None,
                          preset: Optional[str] = None,
                          crf: Optional[int] = None,
                          additional_params: Optional[List[str]] = None) -> List[str]:
        """
        Build a safe FFmpeg command with validated parameters.

        Args:
            base_command: Base command (e.g., ['ffmpeg'])
            input_file: Input file path
            output_file: Output file path
            codec: Video codec
            preset: Encoding preset
            crf: CRF value
            additional_params: Additional validated parameters

        Returns:
            List of command arguments

        Raises:
            ValidationError: If any parameter is invalid
        """
        # Validate paths
        input_path = PathValidator.validate_path(input_file, must_exist=True, must_be_file=True)
        output_path = PathValidator.validate_output_path(output_file, overwrite=True)

        # Build command
        command = base_command.copy()
        command.extend(['-i', str(input_path)])

        # Add codec
        if codec:
            validated_codec = FFmpegValidator.validate_codec(codec)
            command.extend(['-c:v', validated_codec])

        # Add preset
        if preset:
            validated_preset = FFmpegValidator.validate_preset(preset)
            command.extend(['-preset', validated_preset])

        # Add CRF
        if crf is not None:
            validated_crf = FFmpegValidator.validate_crf(crf)
            command.extend(['-crf', str(validated_crf)])

        # Add additional parameters (must be pre-validated)
        if additional_params:
            command.extend(additional_params)

        # Add output file
        command.append(str(output_path))

        return command


class NumericValidator:
    """Validator for numeric inputs."""

    @staticmethod
    def validate_int(value: Union[int, str],
                    min_value: Optional[int] = None,
                    max_value: Optional[int] = None,
                    name: str = "value") -> int:
        """
        Validate an integer value.

        Args:
            value: Value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            name: Name of the value (for error messages)

        Returns:
            Validated integer

        Raises:
            ValidationError: If validation fails
        """
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{name} must be an integer, got: {value}")

        if min_value is not None and int_value < min_value:
            raise ValidationError(f"{name} must be >= {min_value}, got: {int_value}")

        if max_value is not None and int_value > max_value:
            raise ValidationError(f"{name} must be <= {max_value}, got: {int_value}")

        return int_value

    @staticmethod
    def validate_float(value: Union[float, str],
                      min_value: Optional[float] = None,
                      max_value: Optional[float] = None,
                      name: str = "value") -> float:
        """
        Validate a float value.

        Args:
            value: Value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            name: Name of the value (for error messages)

        Returns:
            Validated float

        Raises:
            ValidationError: If validation fails
        """
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{name} must be a number, got: {value}")

        if min_value is not None and float_value < min_value:
            raise ValidationError(f"{name} must be >= {min_value}, got: {float_value}")

        if max_value is not None and float_value > max_value:
            raise ValidationError(f"{name} must be <= {max_value}, got: {float_value}")

        return float_value

    @staticmethod
    def validate_percentage(value: Union[float, str],
                           name: str = "percentage") -> float:
        """
        Validate a percentage value (0-100).

        Args:
            value: Value to validate
            name: Name of the value (for error messages)

        Returns:
            Validated percentage

        Raises:
            ValidationError: If validation fails
        """
        return NumericValidator.validate_float(value, 0.0, 100.0, name)
