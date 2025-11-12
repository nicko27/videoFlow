"""Tests for VideoPlayerService.

Tests the video playback service including:
- Video loading and properties
- Frame navigation
- Playback control
- Error handling
"""

import pytest
import cv2
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QTimer

from src.plugins.video_editor.services.video_player_service import VideoPlayerService


@pytest.fixture
def service(qapp):
    """Create VideoPlayerService instance.

    Args:
        qapp: QApplication fixture

    Returns:
        VideoPlayerService instance
    """
    return VideoPlayerService()


@pytest.fixture
def mock_cap():
    """Create mock VideoCapture.

    Returns:
        Mock VideoCapture object
    """
    mock = MagicMock()
    mock.isOpened.return_value = True
    mock.get.side_effect = lambda prop: {
        cv2.CAP_PROP_FPS: 30.0,
        cv2.CAP_PROP_FRAME_COUNT: 150,
        cv2.CAP_PROP_FRAME_WIDTH: 1920,
        cv2.CAP_PROP_FRAME_HEIGHT: 1080,
        cv2.CAP_PROP_POS_FRAMES: 0,
    }.get(prop, 0)

    # Mock read() to return test frame
    test_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    mock.read.return_value = (True, test_frame)

    return mock


class TestVideoPlayerServiceInitialization:
    """Test service initialization."""

    def test_init(self, service):
        """Test service initializes correctly."""
        assert service is not None
        assert not service.is_loaded
        assert not service.is_playing
        assert service.current_frame == 0
        assert service.total_frames == 0
        assert service.fps == 0.0
        assert service.width == 0
        assert service.height == 0
        assert service.video_path is None

    def test_timer_exists(self, service):
        """Test playback timer is created."""
        assert hasattr(service, '_play_timer')
        assert isinstance(service._play_timer, QTimer)


class TestVideoLoading:
    """Test video loading functionality."""

    def test_load_video_success(self, service, sample_video):
        """Test loading a valid video file."""
        # Load video
        result = service.load_video(str(sample_video))

        assert result is True
        assert service.is_loaded
        assert service.video_path == str(sample_video)
        assert service.fps == 30.0
        assert service.total_frames == 150
        assert service.width == 640
        assert service.height == 480
        assert service.current_frame == 0

    def test_load_video_invalid_path(self, service):
        """Test loading with invalid path."""
        result = service.load_video("/nonexistent/video.mp4")

        assert result is False
        assert not service.is_loaded
        assert service.video_path is None

    def test_load_video_emits_signal(self, service, sample_video):
        """Test that loading emits video_loaded signal."""
        # Connect signal spy
        signal_data = []
        service.video_loaded.connect(
            lambda fps, frames, w, h: signal_data.append((fps, frames, w, h))
        )

        service.load_video(str(sample_video))

        assert len(signal_data) == 1
        fps, frames, width, height = signal_data[0]
        assert fps == 30.0
        assert frames == 150
        assert width == 640
        assert height == 480

    def test_load_video_closes_previous(self, service, sample_video, temp_dir):
        """Test that loading new video closes previous one."""
        # Load first video
        service.load_video(str(sample_video))
        first_path = service.video_path

        # Create second video
        from tests.conftest import create_test_video
        second_video = temp_dir / "video2.mp4"
        create_test_video(second_video)

        # Load second video
        service.load_video(str(second_video))

        assert service.video_path == str(second_video)
        assert service.video_path != first_path

    @patch('cv2.VideoCapture')
    def test_load_video_exception(self, mock_vc_class, service):
        """Test exception handling during load."""
        # Make VideoCapture raise exception
        mock_vc_class.side_effect = Exception("Test error")

        # Connect error signal
        errors = []
        service.error_occurred.connect(lambda msg: errors.append(msg))

        result = service.load_video("/test/video.mp4")

        assert result is False
        assert len(errors) == 1
        assert "Test error" in errors[0]


class TestVideoClosing:
    """Test video closing functionality."""

    def test_close_video(self, service, sample_video):
        """Test closing video."""
        service.load_video(str(sample_video))
        assert service.is_loaded

        # Close signal spy
        closed_signals = []
        service.video_closed.connect(lambda: closed_signals.append(True))

        service.close_video()

        assert not service.is_loaded
        assert service.video_path is None
        assert len(closed_signals) == 1

    def test_close_video_stops_playback(self, service, sample_video):
        """Test that closing stops playback."""
        service.load_video(str(sample_video))
        service.start_playback()
        assert service.is_playing

        service.close_video()

        assert not service.is_playing

    def test_close_video_when_not_loaded(self, service):
        """Test closing when no video loaded."""
        # Should not raise exception
        service.close_video()
        assert not service.is_loaded


class TestFrameNavigation:
    """Test frame navigation functionality."""

    def test_seek_to_frame(self, service, sample_video):
        """Test seeking to specific frame."""
        service.load_video(str(sample_video))

        # Seek to frame 50
        result = service.seek_to_frame(50)

        assert result is True
        assert service.current_frame == 50

    def test_seek_to_frame_emits_signal(self, service, sample_video):
        """Test seek emits frame_changed signal."""
        service.load_video(str(sample_video))

        # Signal spy
        signals = []
        service.frame_changed.connect(
            lambda frame_num, frame_data: signals.append((frame_num, frame_data))
        )

        service.seek_to_frame(50)

        assert len(signals) == 2  # One from load (frame 0), one from seek
        frame_num, frame_data = signals[1]
        assert frame_num == 50
        assert frame_data is not None
        assert isinstance(frame_data, np.ndarray)

    def test_seek_to_invalid_frame(self, service, sample_video):
        """Test seeking to invalid frame."""
        service.load_video(str(sample_video))

        # Try to seek beyond total frames
        result = service.seek_to_frame(200)

        assert result is False

    def test_seek_to_negative_frame(self, service, sample_video):
        """Test seeking to negative frame."""
        service.load_video(str(sample_video))

        result = service.seek_to_frame(-10)

        assert result is False

    def test_seek_without_video(self, service):
        """Test seeking when no video loaded."""
        result = service.seek_to_frame(10)

        assert result is False

    def test_next_frame(self, service, sample_video):
        """Test advancing to next frame."""
        service.load_video(str(sample_video))
        service.seek_to_frame(10)

        result = service.next_frame()

        assert result is True
        assert service.current_frame == 11

    def test_next_frame_at_end(self, service, sample_video):
        """Test next_frame at end of video."""
        service.load_video(str(sample_video))
        service.seek_to_frame(149)  # Last frame

        result = service.next_frame()

        # Should wrap to beginning or return False
        assert result is False or service.current_frame == 0

    def test_previous_frame(self, service, sample_video):
        """Test going to previous frame."""
        service.load_video(str(sample_video))
        service.seek_to_frame(10)

        result = service.previous_frame()

        assert result is True
        assert service.current_frame == 9

    def test_previous_frame_at_start(self, service, sample_video):
        """Test previous_frame at start of video."""
        service.load_video(str(sample_video))
        service.seek_to_frame(0)

        result = service.previous_frame()

        # Should stay at 0 or wrap
        assert result is False or service.current_frame == service.total_frames - 1


class TestPlaybackControl:
    """Test playback control functionality."""

    def test_start_playback(self, service, sample_video):
        """Test starting playback."""
        service.load_video(str(sample_video))

        # Signal spy
        started_signals = []
        service.playback_started.connect(lambda: started_signals.append(True))

        service.start_playback()

        assert service.is_playing
        assert len(started_signals) == 1

    def test_start_playback_without_video(self, service):
        """Test starting playback without video."""
        service.start_playback()

        # Should not crash, but should not be playing
        assert not service.is_playing

    def test_stop_playback(self, service, sample_video):
        """Test stopping playback."""
        service.load_video(str(sample_video))
        service.start_playback()

        # Signal spy
        stopped_signals = []
        service.playback_stopped.connect(lambda: stopped_signals.append(True))

        service.stop_playback()

        assert not service.is_playing
        assert len(stopped_signals) == 1

    def test_toggle_playback(self, service, sample_video):
        """Test toggling playback."""
        service.load_video(str(sample_video))

        # Toggle to playing
        service.toggle_playback()
        assert service.is_playing

        # Toggle to stopped
        service.toggle_playback()
        assert not service.is_playing

    def test_playback_timer_interval(self, service, sample_video):
        """Test that playback timer uses correct interval."""
        service.load_video(str(sample_video))
        service.start_playback()

        # Timer interval should be based on FPS
        expected_interval = int(1000 / service.fps)  # milliseconds
        actual_interval = service._play_timer.interval()

        # Allow small tolerance
        assert abs(actual_interval - expected_interval) <= 1


class TestFrameRetrieval:
    """Test frame retrieval functionality."""

    def test_get_frame_at(self, service, sample_video):
        """Test getting frame without changing position."""
        service.load_video(str(sample_video))
        current_pos = service.current_frame

        # Get frame at different position
        frame = service.get_frame_at(50)

        assert frame is not None
        assert isinstance(frame, np.ndarray)
        # Position should not change
        assert service.current_frame == current_pos

    def test_get_frame_at_invalid(self, service, sample_video):
        """Test getting frame at invalid position."""
        service.load_video(str(sample_video))

        frame = service.get_frame_at(200)

        assert frame is None


class TestProperties:
    """Test service properties."""

    def test_is_loaded_property(self, service, sample_video):
        """Test is_loaded property."""
        assert not service.is_loaded

        service.load_video(str(sample_video))
        assert service.is_loaded

        service.close_video()
        assert not service.is_loaded

    def test_is_playing_property(self, service, sample_video):
        """Test is_playing property."""
        service.load_video(str(sample_video))

        assert not service.is_playing

        service.start_playback()
        assert service.is_playing

        service.stop_playback()
        assert not service.is_playing

    def test_video_properties(self, service, sample_video):
        """Test video property accessors."""
        service.load_video(str(sample_video))

        assert service.current_frame == 0
        assert service.total_frames == 150
        assert service.fps == 30.0
        assert service.width == 640
        assert service.height == 480
        assert service.video_path == str(sample_video)


class TestErrorHandling:
    """Test error handling."""

    @patch('cv2.VideoCapture')
    def test_read_failure(self, mock_vc_class, service):
        """Test handling of frame read failure."""
        # Setup mock to fail on read
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.return_value = 30.0
        mock_cap.read.return_value = (False, None)  # Read fails
        mock_vc_class.return_value = mock_cap

        errors = []
        service.error_occurred.connect(lambda msg: errors.append(msg))

        service.load_video("/test/video.mp4")
        result = service.seek_to_frame(10)

        assert result is False

    def test_operations_without_video(self, service):
        """Test that operations without video don't crash."""
        # These should all fail gracefully
        assert service.seek_to_frame(10) is False
        assert service.next_frame() is False
        assert service.previous_frame() is False
        assert service.get_frame_at(10) is None

        # These should do nothing
        service.start_playback()  # Should not crash
        service.stop_playback()   # Should not crash
        service.close_video()     # Should not crash


# Integration tests with real video files
@pytest.mark.video
class TestVideoPlayerServiceIntegration:
    """Integration tests with real video files."""

    def test_full_workflow(self, service, sample_video):
        """Test complete workflow: load, seek, play, stop, close."""
        # Load
        assert service.load_video(str(sample_video))
        assert service.is_loaded

        # Seek
        assert service.seek_to_frame(50)
        assert service.current_frame == 50

        # Navigate
        assert service.next_frame()
        assert service.current_frame == 51

        assert service.previous_frame()
        assert service.current_frame == 50

        # Play
        service.start_playback()
        assert service.is_playing

        # Stop
        service.stop_playback()
        assert not service.is_playing

        # Close
        service.close_video()
        assert not service.is_loaded

    def test_multiple_videos(self, service, multiple_videos):
        """Test loading multiple videos sequentially."""
        for video_path in multiple_videos:
            result = service.load_video(str(video_path))
            assert result is True
            assert service.is_loaded
            assert service.video_path == str(video_path)
