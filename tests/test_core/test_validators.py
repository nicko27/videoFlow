"""
Tests for Validators Module

Tests input validation and sanitization utilities.
"""

import pytest
from pathlib import Path
from src.core.validators import (
    ValidationError,
    PathValidator,
    FFmpegValidator,
    NumericValidator
)


class TestPathValidator:
    """Test suite for PathValidator."""

    def test_validate_existing_path(self, temp_file):
        """Test validation of existing path."""
        validated = PathValidator.validate_path(temp_file, must_exist=True)
        assert validated == temp_file

    def test_validate_nonexistent_path_fails(self, temp_dir):
        """Test that nonexistent path fails when must_exist=True."""
        nonexistent = temp_dir / 'nonexistent.txt'

        with pytest.raises(ValidationError):
            PathValidator.validate_path(nonexistent, must_exist=True)

    def test_validate_file_type(self, temp_file):
        """Test file type validation."""
        # Should pass - is a file
        PathValidator.validate_path(temp_file, must_be_file=True)

        # Should fail - not a directory
        with pytest.raises(ValidationError):
            PathValidator.validate_path(temp_file, must_be_dir=True)

    def test_validate_directory_type(self, temp_dir):
        """Test directory type validation."""
        # Should pass - is a directory
        PathValidator.validate_path(temp_dir, must_be_dir=True)

        # Should fail - not a file
        with pytest.raises(ValidationError):
            PathValidator.validate_path(temp_dir, must_be_file=True)

    def test_validate_path_too_long_fails(self):
        """Test that extremely long paths fail."""
        # Create path longer than allowed
        from src.core.config import Config
        max_length = Config.SECURITY['max_path_length']

        long_path = 'a' * (max_length + 100)

        with pytest.raises(ValidationError):
            PathValidator.validate_path(long_path)

    def test_validate_video_file(self, temp_dir):
        """Test video file validation."""
        # Create fake video file
        video_path = temp_dir / 'test.mp4'
        video_path.write_text('fake video')

        validated = PathValidator.validate_video_file(video_path)
        assert validated == video_path

    def test_validate_video_file_wrong_extension_fails(self, temp_dir):
        """Test that non-video extension fails."""
        wrong_path = temp_dir / 'test.txt'
        wrong_path.write_text('not a video')

        with pytest.raises(ValidationError):
            PathValidator.validate_video_file(wrong_path)

    def test_validate_output_path(self, temp_dir):
        """Test output path validation."""
        output_path = temp_dir / 'output.mp4'

        # Should pass - parent exists
        validated = PathValidator.validate_output_path(output_path)
        assert validated == output_path

    def test_validate_output_path_no_parent_fails(self, temp_dir):
        """Test output path fails if parent doesn't exist."""
        output_path = temp_dir / 'nonexistent_dir' / 'output.mp4'

        with pytest.raises(ValidationError):
            PathValidator.validate_output_path(output_path)

    def test_validate_output_path_exists_no_overwrite_fails(self, temp_file):
        """Test that existing file fails without overwrite flag."""
        with pytest.raises(ValidationError):
            PathValidator.validate_output_path(temp_file, overwrite=False)

    def test_validate_output_path_exists_with_overwrite(self, temp_file):
        """Test that existing file passes with overwrite flag."""
        validated = PathValidator.validate_output_path(temp_file, overwrite=True)
        assert validated == temp_file

    def test_is_safe_filename(self):
        """Test safe filename checking."""
        # Safe filenames
        assert PathValidator.is_safe_filename('video.mp4')
        assert PathValidator.is_safe_filename('my_video-2024.mp4')

        # Unsafe filenames (path traversal attempts)
        assert not PathValidator.is_safe_filename('../etc/passwd')
        assert not PathValidator.is_safe_filename('..\\windows\\system32')
        assert not PathValidator.is_safe_filename('video/../../file.mp4')
        assert not PathValidator.is_safe_filename('file\x00.mp4')


class TestFFmpegValidator:
    """Test suite for FFmpegValidator."""

    def test_validate_allowed_codec(self):
        """Test validation of allowed codecs."""
        assert FFmpegValidator.validate_codec('libx264') == 'libx264'
        assert FFmpegValidator.validate_codec('libx265') == 'libx265'

    def test_validate_disallowed_codec_fails(self):
        """Test that disallowed codec fails."""
        with pytest.raises(ValidationError):
            FFmpegValidator.validate_codec('invalid_codec')

    def test_validate_allowed_preset(self):
        """Test validation of allowed presets."""
        assert FFmpegValidator.validate_preset('medium') == 'medium'
        assert FFmpegValidator.validate_preset('fast') == 'fast'

    def test_validate_disallowed_preset_fails(self):
        """Test that disallowed preset fails."""
        with pytest.raises(ValidationError):
            FFmpegValidator.validate_preset('invalid_preset')

    def test_validate_crf_valid_range(self):
        """Test CRF validation in valid range."""
        assert FFmpegValidator.validate_crf(0) == 0
        assert FFmpegValidator.validate_crf(23) == 23
        assert FFmpegValidator.validate_crf(51) == 51
        assert FFmpegValidator.validate_crf('23') == 23

    def test_validate_crf_out_of_range_fails(self):
        """Test that CRF out of range fails."""
        with pytest.raises(ValidationError):
            FFmpegValidator.validate_crf(-1)

        with pytest.raises(ValidationError):
            FFmpegValidator.validate_crf(52)

    def test_validate_crf_invalid_type_fails(self):
        """Test that invalid CRF type fails."""
        with pytest.raises(ValidationError):
            FFmpegValidator.validate_crf('not_a_number')

    def test_validate_bitrate(self):
        """Test bitrate validation."""
        assert FFmpegValidator.validate_bitrate('128k') == '128k'
        assert FFmpegValidator.validate_bitrate('1M') == '1M'
        assert FFmpegValidator.validate_bitrate('500K') == '500K'

    def test_validate_bitrate_invalid_format_fails(self):
        """Test that invalid bitrate format fails."""
        with pytest.raises(ValidationError):
            FFmpegValidator.validate_bitrate('128')  # Missing unit

        with pytest.raises(ValidationError):
            FFmpegValidator.validate_bitrate('k128')  # Wrong order

        with pytest.raises(ValidationError):
            FFmpegValidator.validate_bitrate('abc')  # Not a number

    def test_validate_resolution(self):
        """Test resolution validation."""
        width, height = FFmpegValidator.validate_resolution('1920x1080')
        assert width == 1920
        assert height == 1080

        width, height = FFmpegValidator.validate_resolution('1280x720')
        assert width == 1280
        assert height == 720

    def test_validate_resolution_original(self):
        """Test 'original' resolution returns None."""
        result = FFmpegValidator.validate_resolution('original')
        assert result is None

    def test_validate_resolution_invalid_format_fails(self):
        """Test that invalid resolution format fails."""
        with pytest.raises(ValidationError):
            FFmpegValidator.validate_resolution('1920-1080')  # Wrong separator

        with pytest.raises(ValidationError):
            FFmpegValidator.validate_resolution('1920')  # Missing height

        with pytest.raises(ValidationError):
            FFmpegValidator.validate_resolution('abc')  # Not numbers

    def test_validate_resolution_out_of_range_fails(self):
        """Test that unreasonable resolutions fail."""
        with pytest.raises(ValidationError):
            FFmpegValidator.validate_resolution('0x0')

        with pytest.raises(ValidationError):
            FFmpegValidator.validate_resolution('99999x99999')

    def test_validate_fps(self):
        """Test FPS validation."""
        assert FFmpegValidator.validate_fps(30) == 30.0
        assert FFmpegValidator.validate_fps(60) == 60.0
        assert FFmpegValidator.validate_fps('24') == 24.0
        assert FFmpegValidator.validate_fps(23.976) == pytest.approx(23.976)

    def test_validate_fps_original(self):
        """Test 'original' FPS returns None."""
        assert FFmpegValidator.validate_fps('original') is None

    def test_validate_fps_out_of_range_fails(self):
        """Test that FPS out of range fails."""
        with pytest.raises(ValidationError):
            FFmpegValidator.validate_fps(0)

        with pytest.raises(ValidationError):
            FFmpegValidator.validate_fps(1000)

    def test_validate_fps_invalid_type_fails(self):
        """Test that invalid FPS type fails."""
        with pytest.raises(ValidationError):
            FFmpegValidator.validate_fps('not_a_number')

    def test_sanitize_parameter_valid(self):
        """Test sanitization of valid parameters."""
        param = 'libx264'
        assert FFmpegValidator.sanitize_parameter(param) == param

        param = 'value-with_dots.and:colons'
        assert FFmpegValidator.sanitize_parameter(param) == param

    def test_sanitize_parameter_dangerous_chars_fails(self):
        """Test that dangerous characters fail."""
        dangerous_params = [
            'command; rm -rf /',  # Command injection
            'value && echo hacked',  # Command chaining
            'value | cat /etc/passwd',  # Pipe
            'value > output.txt',  # Redirection
            'value $(whoami)',  # Command substitution
            'value `whoami`',  # Backtick substitution
        ]

        for param in dangerous_params:
            with pytest.raises(ValidationError):
                FFmpegValidator.sanitize_parameter(param)

    def test_build_safe_command(self, temp_dir):
        """Test building safe FFmpeg command."""
        input_file = temp_dir / 'input.mp4'
        input_file.write_text('fake video')

        output_file = temp_dir / 'output.mp4'

        command = FFmpegValidator.build_safe_command(
            ['ffmpeg', '-y'],
            input_file=input_file,
            output_file=output_file,
            codec='libx264',
            preset='medium',
            crf=23
        )

        assert 'ffmpeg' in command
        assert '-i' in command
        assert str(input_file) in command
        assert str(output_file) in command
        assert '-c:v' in command
        assert 'libx264' in command
        assert '-preset' in command
        assert 'medium' in command
        assert '-crf' in command
        assert '23' in command


class TestNumericValidator:
    """Test suite for NumericValidator."""

    def test_validate_int(self):
        """Test integer validation."""
        assert NumericValidator.validate_int(42) == 42
        assert NumericValidator.validate_int('42') == 42

    def test_validate_int_with_range(self):
        """Test integer validation with min/max."""
        assert NumericValidator.validate_int(5, min_value=0, max_value=10) == 5

    def test_validate_int_below_min_fails(self):
        """Test that value below minimum fails."""
        with pytest.raises(ValidationError):
            NumericValidator.validate_int(5, min_value=10)

    def test_validate_int_above_max_fails(self):
        """Test that value above maximum fails."""
        with pytest.raises(ValidationError):
            NumericValidator.validate_int(15, max_value=10)

    def test_validate_int_invalid_type_fails(self):
        """Test that invalid type fails."""
        with pytest.raises(ValidationError):
            NumericValidator.validate_int('not_a_number')

    def test_validate_float(self):
        """Test float validation."""
        assert NumericValidator.validate_float(3.14) == pytest.approx(3.14)
        assert NumericValidator.validate_float('3.14') == pytest.approx(3.14)

    def test_validate_float_with_range(self):
        """Test float validation with min/max."""
        result = NumericValidator.validate_float(
            0.5,
            min_value=0.0,
            max_value=1.0
        )
        assert result == pytest.approx(0.5)

    def test_validate_float_out_of_range_fails(self):
        """Test that float out of range fails."""
        with pytest.raises(ValidationError):
            NumericValidator.validate_float(1.5, max_value=1.0)

    def test_validate_percentage(self):
        """Test percentage validation."""
        assert NumericValidator.validate_percentage(50) == 50.0
        assert NumericValidator.validate_percentage(0) == 0.0
        assert NumericValidator.validate_percentage(100) == 100.0

    def test_validate_percentage_out_of_range_fails(self):
        """Test that percentage out of range fails."""
        with pytest.raises(ValidationError):
            NumericValidator.validate_percentage(-1)

        with pytest.raises(ValidationError):
            NumericValidator.validate_percentage(101)
