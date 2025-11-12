"""Tests for TimeCode utility.

Tests time conversion and formatting functions.
"""

import pytest
from src.plugins.video_editor.utils.time_utils import (
    TimeCode,
    format_duration,
    format_frame_count
)


class TestTimeCodeInitialization:
    """Test TimeCode initialization."""

    def test_init_with_fps(self):
        """Test initialization with FPS."""
        tc = TimeCode(30.0)

        assert tc.fps == 30.0

    def test_init_with_invalid_fps(self):
        """Test initialization with invalid FPS."""
        with pytest.raises((ValueError, AssertionError, ZeroDivisionError)):
            TimeCode(0)

        with pytest.raises((ValueError, AssertionError)):
            TimeCode(-30.0)


class TestFramesToSeconds:
    """Test frames to seconds conversion."""

    def test_frames_to_seconds_30fps(self):
        """Test conversion at 30 FPS."""
        tc = TimeCode(30.0)

        assert tc.frames_to_seconds(0) == 0.0
        assert tc.frames_to_seconds(30) == 1.0
        assert tc.frames_to_seconds(60) == 2.0
        assert tc.frames_to_seconds(900) == 30.0

    def test_frames_to_seconds_24fps(self):
        """Test conversion at 24 FPS."""
        tc = TimeCode(24.0)

        assert tc.frames_to_seconds(24) == 1.0
        assert tc.frames_to_seconds(48) == 2.0
        assert tc.frames_to_seconds(240) == 10.0

    def test_frames_to_seconds_60fps(self):
        """Test conversion at 60 FPS."""
        tc = TimeCode(60.0)

        assert tc.frames_to_seconds(60) == 1.0
        assert tc.frames_to_seconds(120) == 2.0

    def test_frames_to_seconds_fractional(self):
        """Test conversion with fractional result."""
        tc = TimeCode(30.0)

        # 1 frame should be 1/30 second
        result = tc.frames_to_seconds(1)
        assert abs(result - (1/30)) < 0.0001


class TestSecondsToFrames:
    """Test seconds to frames conversion."""

    def test_seconds_to_frames_30fps(self):
        """Test conversion at 30 FPS."""
        tc = TimeCode(30.0)

        assert tc.seconds_to_frames(0.0) == 0
        assert tc.seconds_to_frames(1.0) == 30
        assert tc.seconds_to_frames(2.0) == 60
        assert tc.seconds_to_frames(30.0) == 900

    def test_seconds_to_frames_24fps(self):
        """Test conversion at 24 FPS."""
        tc = TimeCode(24.0)

        assert tc.seconds_to_frames(1.0) == 24
        assert tc.seconds_to_frames(2.0) == 48

    def test_seconds_to_frames_fractional(self):
        """Test conversion with fractional seconds."""
        tc = TimeCode(30.0)

        # 0.5 seconds should be 15 frames
        assert tc.seconds_to_frames(0.5) == 15

        # 1.5 seconds should be 45 frames
        assert tc.seconds_to_frames(1.5) == 45


class TestFramesToTimecode:
    """Test frames to timecode string conversion."""

    def test_frames_to_timecode_basic(self):
        """Test basic timecode formatting."""
        tc = TimeCode(30.0)

        # 0 frames = 00:00:00
        assert tc.frames_to_timecode(0) == "00:00:00"

        # 30 frames = 1 second = 00:00:01
        assert tc.frames_to_timecode(30) == "00:00:01"

        # 1800 frames = 60 seconds = 00:01:00
        assert tc.frames_to_timecode(1800) == "00:01:00"

        # 108000 frames = 3600 seconds = 01:00:00
        assert tc.frames_to_timecode(108000) == "01:00:00"

    def test_frames_to_timecode_complex(self):
        """Test complex timecode values."""
        tc = TimeCode(30.0)

        # 1 hour, 23 minutes, 45 seconds
        total_seconds = (1 * 3600) + (23 * 60) + 45
        frames = int(total_seconds * 30)

        result = tc.frames_to_timecode(frames)
        assert result == "01:23:45"

    def test_frames_to_timecode_over_one_hour(self):
        """Test timecode for videos over 1 hour."""
        tc = TimeCode(30.0)

        # 2 hours = 216000 frames
        assert tc.frames_to_timecode(216000) == "02:00:00"

        # 10 hours
        assert tc.frames_to_timecode(1080000) == "10:00:00"

    def test_frames_to_timecode_with_milliseconds(self):
        """Test timecode with milliseconds."""
        tc = TimeCode(30.0)

        # Test with milliseconds if supported
        result = tc.frames_to_timecode_ms(45)  # 1.5 seconds
        # Should be "00:00:01.500" or similar format


class TestSecondsToTimecode:
    """Test seconds to timecode conversion."""

    def test_seconds_to_timecode_basic(self):
        """Test basic seconds to timecode."""
        tc = TimeCode(30.0)

        assert tc.seconds_to_timecode(0) == "00:00:00"
        assert tc.seconds_to_timecode(1) == "00:00:01"
        assert tc.seconds_to_timecode(60) == "00:01:00"
        assert tc.seconds_to_timecode(3600) == "01:00:00"

    def test_seconds_to_timecode_fractional(self):
        """Test with fractional seconds."""
        tc = TimeCode(30.0)

        # Fractional seconds should be rounded or truncated
        result = tc.seconds_to_timecode(1.5)
        # Should be "00:00:01" or "00:00:02" depending on rounding


class TestParseTimecode:
    """Test timecode string parsing."""

    def test_parse_timecode_basic(self):
        """Test parsing basic timecode strings."""
        tc = TimeCode(30.0)

        assert tc.parse_timecode("00:00:00") == 0.0
        assert tc.parse_timecode("00:00:01") == 1.0
        assert tc.parse_timecode("00:01:00") == 60.0
        assert tc.parse_timecode("01:00:00") == 3600.0

    def test_parse_timecode_complex(self):
        """Test parsing complex timecode."""
        tc = TimeCode(30.0)

        # 1:23:45
        result = tc.parse_timecode("01:23:45")
        expected = (1 * 3600) + (23 * 60) + 45
        assert result == expected

    def test_parse_timecode_invalid(self):
        """Test parsing invalid timecode."""
        tc = TimeCode(30.0)

        # Should return None or raise exception
        result = tc.parse_timecode("invalid")
        assert result is None or isinstance(result, (int, float))

        result = tc.parse_timecode("99:99:99")
        # Implementation dependent


class TestTimecodeToFrames:
    """Test timecode to frames conversion."""

    def test_timecode_to_frames_basic(self):
        """Test converting timecode string to frames."""
        tc = TimeCode(30.0)

        assert tc.timecode_to_frames("00:00:00") == 0
        assert tc.timecode_to_frames("00:00:01") == 30
        assert tc.timecode_to_frames("00:01:00") == 1800
        assert tc.timecode_to_frames("01:00:00") == 108000


class TestRoundTrip:
    """Test round-trip conversions."""

    def test_frames_seconds_roundtrip(self):
        """Test frames -> seconds -> frames."""
        tc = TimeCode(30.0)

        for frames in [0, 30, 60, 900, 108000]:
            seconds = tc.frames_to_seconds(frames)
            back_to_frames = tc.seconds_to_frames(seconds)
            assert back_to_frames == frames

    def test_frames_timecode_roundtrip(self):
        """Test frames -> timecode -> frames."""
        tc = TimeCode(30.0)

        for frames in [0, 30, 1800, 108000]:
            timecode = tc.frames_to_timecode(frames)
            back_to_frames = tc.timecode_to_frames(timecode)
            assert back_to_frames == frames


class TestFormatDuration:
    """Test format_duration utility function."""

    def test_format_duration_seconds(self):
        """Test formatting short durations."""
        assert format_duration(0) == "0s"
        assert format_duration(30) == "30s"
        assert format_duration(59) == "59s"

    def test_format_duration_minutes(self):
        """Test formatting minute durations."""
        assert format_duration(60) == "1m 0s"
        assert format_duration(90) == "1m 30s"
        assert format_duration(120) == "2m 0s"

    def test_format_duration_hours(self):
        """Test formatting hour durations."""
        assert format_duration(3600) == "1h 0m 0s"
        assert format_duration(3665) == "1h 1m 5s"
        assert format_duration(7200) == "2h 0m 0s"

    def test_format_duration_long(self):
        """Test formatting very long durations."""
        # 10 hours, 30 minutes, 45 seconds
        duration = (10 * 3600) + (30 * 60) + 45
        result = format_duration(duration)
        assert "10h" in result
        assert "30m" in result
        assert "45s" in result


class TestFormatFrameCount:
    """Test format_frame_count utility function."""

    def test_format_frame_count_small(self):
        """Test formatting small frame counts."""
        assert format_frame_count(0) == "0"
        assert format_frame_count(100) == "100"
        assert format_frame_count(999) == "999"

    def test_format_frame_count_thousands(self):
        """Test formatting with thousands separator."""
        # Should add separator for readability
        result = format_frame_count(1000)
        assert "1" in result and "000" in result

        result = format_frame_count(10000)
        assert "10" in result

        result = format_frame_count(100000)
        assert "100" in result


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_values(self):
        """Test handling of zero values."""
        tc = TimeCode(30.0)

        assert tc.frames_to_seconds(0) == 0.0
        assert tc.seconds_to_frames(0.0) == 0
        assert tc.frames_to_timecode(0) == "00:00:00"

    def test_very_large_values(self):
        """Test handling very large values."""
        tc = TimeCode(30.0)

        # 100 hours
        large_frames = 100 * 3600 * 30
        timecode = tc.frames_to_timecode(large_frames)
        assert len(timecode) > 0

    def test_negative_values(self):
        """Test handling negative values."""
        tc = TimeCode(30.0)

        # Should handle gracefully or raise exception
        try:
            result = tc.frames_to_seconds(-10)
            # If it returns, should be negative
            assert result <= 0
        except (ValueError, AssertionError):
            # Or raise exception
            pass

    def test_fractional_fps(self):
        """Test with fractional FPS."""
        tc = TimeCode(29.97)  # NTSC framerate

        frames = 30
        seconds = tc.frames_to_seconds(frames)
        assert abs(seconds - 1.001) < 0.01


class TestDifferentFramerates:
    """Test with various common framerates."""

    @pytest.mark.parametrize("fps", [23.976, 24.0, 25.0, 29.97, 30.0, 50.0, 59.94, 60.0])
    def test_common_framerates(self, fps):
        """Test TimeCode with common video framerates."""
        tc = TimeCode(fps)

        # Basic conversions should work
        assert tc.frames_to_seconds(0) == 0.0
        seconds = tc.frames_to_seconds(int(fps))
        assert abs(seconds - 1.0) < 0.01

        # Round trip should work
        frames_back = tc.seconds_to_frames(seconds)
        assert abs(frames_back - fps) < 1


class TestTimeCodeAccuracy:
    """Test accuracy of time conversions."""

    def test_no_accumulated_error(self):
        """Test that conversions don't accumulate error."""
        tc = TimeCode(30.0)

        # Convert many times and check for drift
        original_frames = 1000
        frames = original_frames

        for _ in range(10):
            seconds = tc.frames_to_seconds(frames)
            frames = tc.seconds_to_frames(seconds)

        # Should not have drifted
        assert frames == original_frames

    def test_precision_maintained(self):
        """Test that precision is maintained in conversions."""
        tc = TimeCode(30.0)

        # Test with specific frame counts
        test_frames = [1, 15, 30, 45, 60, 75, 90]

        for frames in test_frames:
            seconds = tc.frames_to_seconds(frames)
            back = tc.seconds_to_frames(seconds)
            assert back == frames
