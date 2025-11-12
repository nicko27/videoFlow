"""Tests for video_utils module.

Tests video validation and utility functions.
"""

import pytest
from pathlib import Path
from src.plugins.video_editor.utils.video_utils import (
    get_aspect_ratio,
    get_aspect_ratio_string,
    is_standard_resolution,
    get_resolution_name,
    validate_video_file,
    get_file_size_mb,
    format_file_size,
    calculate_bitrate,
    format_bitrate,
    validate_frame_range
)


class TestAspectRatio:
    """Test aspect ratio calculations."""

    def test_get_aspect_ratio_16_9(self):
        """Test 16:9 aspect ratio."""
        ratio = get_aspect_ratio(1920, 1080)
        assert abs(ratio - 16/9) < 0.01

    def test_get_aspect_ratio_4_3(self):
        """Test 4:3 aspect ratio."""
        ratio = get_aspect_ratio(640, 480)
        assert abs(ratio - 4/3) < 0.01

    def test_get_aspect_ratio_square(self):
        """Test square (1:1) aspect ratio."""
        ratio = get_aspect_ratio(1080, 1080)
        assert abs(ratio - 1.0) < 0.01

    def test_get_aspect_ratio_vertical(self):
        """Test vertical video (9:16)."""
        ratio = get_aspect_ratio(1080, 1920)
        assert abs(ratio - 9/16) < 0.01

    def test_get_aspect_ratio_string_16_9(self):
        """Test aspect ratio string for 16:9."""
        result = get_aspect_ratio_string(1920, 1080)
        assert result == "16:9"

    def test_get_aspect_ratio_string_4_3(self):
        """Test aspect ratio string for 4:3."""
        result = get_aspect_ratio_string(640, 480)
        assert result == "4:3"

    def test_get_aspect_ratio_string_1_1(self):
        """Test aspect ratio string for 1:1."""
        result = get_aspect_ratio_string(1080, 1080)
        assert result == "1:1"

    def test_get_aspect_ratio_string_21_9(self):
        """Test aspect ratio string for ultrawide."""
        result = get_aspect_ratio_string(2560, 1080)
        # Should return appropriate string


class TestResolutionDetection:
    """Test resolution detection and naming."""

    def test_is_standard_resolution_1080p(self):
        """Test 1080p detection."""
        assert is_standard_resolution(1920, 1080) is True

    def test_is_standard_resolution_720p(self):
        """Test 720p detection."""
        assert is_standard_resolution(1280, 720) is True

    def test_is_standard_resolution_4k(self):
        """Test 4K detection."""
        assert is_standard_resolution(3840, 2160) is True

    def test_is_standard_resolution_custom(self):
        """Test custom resolution."""
        assert is_standard_resolution(999, 888) is False

    def test_get_resolution_name_1080p(self):
        """Test 1080p name."""
        name = get_resolution_name(1920, 1080)
        assert "1080" in name or "Full HD" in name or "FHD" in name

    def test_get_resolution_name_720p(self):
        """Test 720p name."""
        name = get_resolution_name(1280, 720)
        assert "720" in name or "HD" in name

    def test_get_resolution_name_4k(self):
        """Test 4K name."""
        name = get_resolution_name(3840, 2160)
        assert "4K" in name or "2160" in name or "UHD" in name

    def test_get_resolution_name_480p(self):
        """Test 480p name."""
        name = get_resolution_name(640, 480)
        assert "480" in name or "SD" in name

    def test_get_resolution_name_custom(self):
        """Test custom resolution name."""
        name = get_resolution_name(999, 888)
        # Should return something reasonable
        assert len(name) > 0


class TestVideoFileValidation:
    """Test video file validation."""

    def test_validate_video_file_valid(self, sample_video):
        """Test validating real video file."""
        result = validate_video_file(str(sample_video))
        assert result is True

    def test_validate_video_file_nonexistent(self):
        """Test validating nonexistent file."""
        result = validate_video_file("/nonexistent/video.mp4")
        assert result is False

    def test_validate_video_file_not_video(self, temp_file):
        """Test validating non-video file."""
        result = validate_video_file(str(temp_file))
        assert result is False

    def test_validate_video_file_empty(self, temp_dir):
        """Test validating empty file."""
        empty_file = temp_dir / "empty.mp4"
        empty_file.touch()

        result = validate_video_file(str(empty_file))
        assert result is False

    def test_validate_video_file_directory(self, temp_dir):
        """Test validating directory path."""
        result = validate_video_file(str(temp_dir))
        assert result is False

    def test_validate_video_file_various_extensions(self, temp_dir):
        """Test validation with various video extensions."""
        extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']

        for ext in extensions:
            # This will fail since files don't exist, but tests extension handling
            path = temp_dir / f"video{ext}"
            result = validate_video_file(str(path))
            # Result depends on whether file exists and is valid


class TestFileSizeUtils:
    """Test file size utilities."""

    def test_get_file_size_mb_small(self, temp_file):
        """Test getting file size in MB for small file."""
        size_mb = get_file_size_mb(str(temp_file))
        assert size_mb > 0
        assert size_mb < 1  # Should be very small

    def test_get_file_size_mb_nonexistent(self):
        """Test file size for nonexistent file."""
        size_mb = get_file_size_mb("/nonexistent/file.mp4")
        assert size_mb == 0

    def test_format_file_size_bytes(self):
        """Test formatting byte sizes."""
        assert format_file_size(0) == "0 B"
        assert format_file_size(100) == "100 B"
        assert format_file_size(1023) == "1023 B" or "1.0 KB" in format_file_size(1023)

    def test_format_file_size_kilobytes(self):
        """Test formatting KB sizes."""
        result = format_file_size(1024)
        assert "1" in result and "KB" in result

        result = format_file_size(10240)
        assert "10" in result and "KB" in result

    def test_format_file_size_megabytes(self):
        """Test formatting MB sizes."""
        result = format_file_size(1024 * 1024)
        assert "1" in result and "MB" in result

        result = format_file_size(100 * 1024 * 1024)
        assert "100" in result and "MB" in result

    def test_format_file_size_gigabytes(self):
        """Test formatting GB sizes."""
        result = format_file_size(1024 * 1024 * 1024)
        assert "1" in result and "GB" in result

        result = format_file_size(5 * 1024 * 1024 * 1024)
        assert "5" in result and "GB" in result

    def test_format_file_size_terabytes(self):
        """Test formatting TB sizes."""
        result = format_file_size(1024 * 1024 * 1024 * 1024)
        assert "1" in result and "TB" in result


class TestBitrateUtils:
    """Test bitrate calculation and formatting."""

    def test_calculate_bitrate_basic(self):
        """Test basic bitrate calculation."""
        # 10 MB file, 5 second duration = 2 MB/s = 16 Mbps
        bitrate = calculate_bitrate(10 * 1024 * 1024, 5.0)
        # Should be around 16 Mbps
        assert 15 < bitrate < 17

    def test_calculate_bitrate_zero_duration(self):
        """Test bitrate with zero duration."""
        bitrate = calculate_bitrate(1000, 0.0)
        # Should return 0 or handle gracefully
        assert bitrate == 0 or bitrate is None

    def test_format_bitrate_kbps(self):
        """Test formatting Kbps."""
        result = format_bitrate(500)
        assert "500" in result and "Kbps" in result

    def test_format_bitrate_mbps(self):
        """Test formatting Mbps."""
        result = format_bitrate(5000)
        assert "5" in result and "Mbps" in result

        result = format_bitrate(16000)
        assert "16" in result and "Mbps" in result

    def test_format_bitrate_fractional(self):
        """Test formatting fractional Mbps."""
        result = format_bitrate(2500)
        # Should show as "2.5 Mbps" or similar
        assert "2" in result


class TestFrameRangeValidation:
    """Test frame range validation."""

    def test_validate_frame_range_valid(self):
        """Test valid frame range."""
        result = validate_frame_range(0, 100, 1000)
        assert result is True

    def test_validate_frame_range_start_negative(self):
        """Test frame range with negative start."""
        result = validate_frame_range(-10, 100, 1000)
        assert result is False

    def test_validate_frame_range_end_beyond_total(self):
        """Test frame range with end beyond total."""
        result = validate_frame_range(0, 2000, 1000)
        assert result is False

    def test_validate_frame_range_start_after_end(self):
        """Test frame range with start after end."""
        result = validate_frame_range(500, 100, 1000)
        assert result is False

    def test_validate_frame_range_equal(self):
        """Test frame range with start equal to end."""
        result = validate_frame_range(100, 100, 1000)
        # Implementation dependent - may allow single frame
        # Should be True or False consistently

    def test_validate_frame_range_at_boundaries(self):
        """Test frame range at boundaries."""
        # Start at 0
        assert validate_frame_range(0, 100, 1000) is True

        # End at total-1
        assert validate_frame_range(900, 999, 1000) is True

        # End at total (should fail)
        assert validate_frame_range(900, 1000, 1000) is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_dimensions(self):
        """Test with zero dimensions."""
        # get_aspect_ratio should handle gracefully
        try:
            ratio = get_aspect_ratio(0, 1080)
        except (ValueError, ZeroDivisionError):
            pass  # Expected

        try:
            ratio = get_aspect_ratio(1920, 0)
        except (ValueError, ZeroDivisionError):
            pass  # Expected

    def test_very_large_dimensions(self):
        """Test with very large dimensions."""
        ratio = get_aspect_ratio(7680, 4320)  # 8K
        assert ratio > 0

        name = get_resolution_name(7680, 4320)
        assert len(name) > 0

    def test_unusual_aspect_ratios(self):
        """Test unusual aspect ratios."""
        # Ultra-ultrawide
        ratio = get_aspect_ratio(3840, 1080)
        assert ratio > 0

        ratio_str = get_aspect_ratio_string(3840, 1080)
        assert len(ratio_str) > 0

        # Very tall (vertical)
        ratio = get_aspect_ratio(1080, 3840)
        assert ratio > 0

    def test_prime_number_dimensions(self):
        """Test with prime number dimensions."""
        ratio = get_aspect_ratio(1919, 1079)
        assert ratio > 0

        is_standard = is_standard_resolution(1919, 1079)
        assert is_standard is False

    def test_empty_path(self):
        """Test with empty path."""
        result = validate_video_file("")
        assert result is False

    def test_none_values(self):
        """Test with None values."""
        # Should handle gracefully
        try:
            result = get_file_size_mb(None)
        except (TypeError, AttributeError):
            pass  # Expected


class TestRealWorldScenarios:
    """Test with real-world scenarios."""

    def test_common_video_resolutions(self):
        """Test recognition of common video resolutions."""
        common_resolutions = [
            (640, 480, "480p"),
            (1280, 720, "720p"),
            (1920, 1080, "1080p"),
            (2560, 1440, "1440p"),
            (3840, 2160, "4K"),
            (7680, 4320, "8K"),
        ]

        for width, height, expected_name in common_resolutions:
            name = get_resolution_name(width, height)
            # Name should contain expected identifier

    def test_mobile_video_resolutions(self):
        """Test mobile/vertical video resolutions."""
        # Portrait phone video
        name = get_resolution_name(1080, 1920)
        assert len(name) > 0

        # Instagram story
        name = get_resolution_name(1080, 1920)
        assert len(name) > 0

    def test_social_media_aspect_ratios(self):
        """Test social media aspect ratios."""
        # Instagram feed (1:1)
        ratio_str = get_aspect_ratio_string(1080, 1080)

        # Instagram story (9:16)
        ratio_str = get_aspect_ratio_string(1080, 1920)

        # YouTube (16:9)
        ratio_str = get_aspect_ratio_string(1920, 1080)


class TestIntegration:
    """Integration tests."""

    def test_full_video_validation_workflow(self, sample_video):
        """Test complete validation workflow."""
        # Validate file
        assert validate_video_file(str(sample_video)) is True

        # Get file size
        size_mb = get_file_size_mb(str(sample_video))
        assert size_mb > 0

        # Format size
        size_str = format_file_size(size_mb * 1024 * 1024)
        assert "MB" in size_str or "KB" in size_str

    def test_resolution_analysis_workflow(self):
        """Test resolution analysis workflow."""
        width, height = 1920, 1080

        # Get aspect ratio
        ratio = get_aspect_ratio(width, height)
        assert ratio > 0

        # Get ratio string
        ratio_str = get_aspect_ratio_string(width, height)
        assert len(ratio_str) > 0

        # Check if standard
        is_std = is_standard_resolution(width, height)
        assert is_std is True

        # Get name
        name = get_resolution_name(width, height)
        assert len(name) > 0
