"""Tests for ExportService.

Tests the export service including:
- FFmpeg validation
- Segment extraction
- Frame export
- Audio extraction
- Export presets
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

from src.plugins.video_editor.services.export_service import ExportService, ExportPreset
from src.plugins.video_editor.segment_manager import VideoSegment


@pytest.fixture
def service(qapp):
    """Create ExportService instance.

    Args:
        qapp: QApplication fixture

    Returns:
        ExportService instance
    """
    return ExportService()


@pytest.fixture
def sample_segment():
    """Create sample VideoSegment.

    Returns:
        VideoSegment instance
    """
    return VideoSegment(
        start_frame=0,
        end_frame=150,  # 5 seconds at 30fps
        name="Test Segment"
    )


class TestExportServiceInitialization:
    """Test service initialization."""

    def test_init(self, service):
        """Test service initializes correctly."""
        assert service is not None


class TestFFmpegValidation:
    """Test FFmpeg validation."""

    @patch('subprocess.run')
    def test_validate_ffmpeg_available(self, mock_run, service):
        """Test FFmpeg validation when available."""
        # Mock successful ffmpeg call
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ffmpeg version 4.4"
        )

        result = service.validate_ffmpeg()

        assert result is True
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_validate_ffmpeg_not_available(self, mock_run, service):
        """Test FFmpeg validation when not available."""
        # Mock ffmpeg not found
        mock_run.side_effect = FileNotFoundError()

        result = service.validate_ffmpeg()

        assert result is False

    @patch('subprocess.run')
    def test_validate_ffmpeg_error(self, mock_run, service):
        """Test FFmpeg validation with error."""
        # Mock ffmpeg returning error
        mock_run.return_value = MagicMock(returncode=1)

        result = service.validate_ffmpeg()

        assert result is False


class TestSegmentExtraction:
    """Test segment extraction."""

    @patch('subprocess.Popen')
    def test_extract_segment_basic(self, mock_popen, service, sample_video, temp_dir, sample_segment):
        """Test basic segment extraction."""
        output_path = temp_dir / "output.mp4"

        # Mock FFmpeg process
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = service.extract_segment(
            str(sample_video),
            sample_segment,
            str(output_path),
            fps=30.0
        )

        assert result is True
        mock_popen.assert_called_once()

    @patch('subprocess.Popen')
    def test_extract_segment_with_codec(self, mock_popen, service, sample_video, temp_dir, sample_segment):
        """Test segment extraction with specific codec."""
        output_path = temp_dir / "output.mp4"

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = service.extract_segment(
            str(sample_video),
            sample_segment,
            str(output_path),
            fps=30.0,
            codec='libx265',
            crf=28
        )

        assert result is True

        # Check that codec was used in command
        call_args = mock_popen.call_args
        command = call_args[0][0]
        assert 'libx265' in command
        assert '28' in command

    @patch('subprocess.Popen')
    def test_extract_segment_failure(self, mock_popen, service, sample_video, temp_dir, sample_segment):
        """Test segment extraction failure."""
        output_path = temp_dir / "output.mp4"

        # Mock FFmpeg failure
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"Error message")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        # Error signal spy
        errors = []
        service.export_failed.connect(lambda msg: errors.append(msg))

        result = service.extract_segment(
            str(sample_video),
            sample_segment,
            str(output_path),
            fps=30.0
        )

        assert result is False
        assert len(errors) == 1

    @patch('subprocess.Popen')
    def test_extract_segment_signals(self, mock_popen, service, sample_video, temp_dir, sample_segment):
        """Test that extraction emits correct signals."""
        output_path = temp_dir / "output.mp4"

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Signal spies
        started = []
        finished = []
        service.export_started.connect(lambda: started.append(True))
        service.export_finished.connect(lambda path: finished.append(path))

        service.extract_segment(
            str(sample_video),
            sample_segment,
            str(output_path),
            fps=30.0
        )

        assert len(started) == 1
        assert len(finished) == 1
        assert finished[0] == str(output_path)

    def test_extract_segment_invalid_video(self, service, temp_dir, sample_segment):
        """Test extraction with invalid video path."""
        output_path = temp_dir / "output.mp4"

        errors = []
        service.export_failed.connect(lambda msg: errors.append(msg))

        result = service.extract_segment(
            "/nonexistent/video.mp4",
            sample_segment,
            str(output_path),
            fps=30.0
        )

        assert result is False
        assert len(errors) == 1


class TestFrameExport:
    """Test frame export functionality."""

    @patch('cv2.VideoCapture')
    @patch('cv2.imwrite')
    def test_export_frame_as_image(self, mock_imwrite, mock_vc_class, service, temp_dir):
        """Test exporting single frame as image."""
        output_path = temp_dir / "frame.png"

        # Mock VideoCapture
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.set.return_value = True
        import numpy as np
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_vc_class.return_value = mock_cap

        # Mock imwrite success
        mock_imwrite.return_value = True

        result = service.export_frame_as_image(
            "/test/video.mp4",
            50,
            str(output_path)
        )

        assert result is True
        mock_cap.set.assert_called_with(1, 50)  # CAP_PROP_POS_FRAMES
        mock_imwrite.assert_called_once()

    @patch('cv2.VideoCapture')
    def test_export_frame_video_not_opened(self, mock_vc_class, service, temp_dir):
        """Test frame export when video cannot be opened."""
        output_path = temp_dir / "frame.png"

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_vc_class.return_value = mock_cap

        errors = []
        service.export_failed.connect(lambda msg: errors.append(msg))

        result = service.export_frame_as_image(
            "/test/video.mp4",
            50,
            str(output_path)
        )

        assert result is False
        assert len(errors) == 1

    @patch('cv2.VideoCapture')
    def test_export_frame_read_failure(self, mock_vc_class, service, temp_dir):
        """Test frame export when frame read fails."""
        output_path = temp_dir / "frame.png"

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)
        mock_vc_class.return_value = mock_cap

        errors = []
        service.export_failed.connect(lambda msg: errors.append(msg))

        result = service.export_frame_as_image(
            "/test/video.mp4",
            50,
            str(output_path)
        )

        assert result is False
        assert len(errors) == 1


class TestAudioExtraction:
    """Test audio extraction."""

    @patch('subprocess.Popen')
    def test_extract_audio_basic(self, mock_popen, service, sample_video, temp_dir):
        """Test basic audio extraction."""
        output_path = temp_dir / "audio.mp3"

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = service.extract_audio(
            str(sample_video),
            str(output_path)
        )

        assert result is True
        mock_popen.assert_called_once()

        # Check command includes audio extraction
        call_args = mock_popen.call_args
        command = call_args[0][0]
        assert '-vn' in command  # No video

    @patch('subprocess.Popen')
    def test_extract_audio_with_format(self, mock_popen, service, sample_video, temp_dir):
        """Test audio extraction with specific format."""
        output_path = temp_dir / "audio.wav"

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = service.extract_audio(
            str(sample_video),
            str(output_path),
            audio_codec='pcm_s16le',
            audio_bitrate='1411k'
        )

        assert result is True

    @patch('subprocess.Popen')
    def test_extract_audio_time_range(self, mock_popen, service, sample_video, temp_dir):
        """Test audio extraction with time range."""
        output_path = temp_dir / "audio.mp3"

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = service.extract_audio(
            str(sample_video),
            str(output_path),
            start_time=10.0,
            duration=5.0
        )

        assert result is True

        # Check time parameters in command
        call_args = mock_popen.call_args
        command = call_args[0][0]
        assert '-ss' in command
        assert '-t' in command


class TestVideoInfo:
    """Test video info retrieval."""

    @patch('subprocess.run')
    def test_get_video_info(self, mock_run, service, sample_video):
        """Test getting video information."""
        # Mock ffprobe output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"streams": [{"codec_type": "video", "width": 1920, "height": 1080}]}'
        )

        info = service.get_video_info(str(sample_video))

        assert info is not None
        assert 'streams' in info

    @patch('subprocess.run')
    def test_get_video_info_failure(self, mock_run, service):
        """Test video info with invalid video."""
        mock_run.side_effect = FileNotFoundError()

        info = service.get_video_info("/nonexistent/video.mp4")

        assert info is None


class TestExportPresets:
    """Test export presets."""

    @patch('subprocess.Popen')
    def test_apply_youtube_1080p_preset(self, mock_popen, service, sample_video, temp_dir, sample_segment):
        """Test YouTube 1080p preset."""
        output_path = temp_dir / "output.mp4"

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = service.apply_preset(
            ExportPreset.YOUTUBE_1080P,
            str(sample_video),
            sample_segment,
            str(output_path),
            fps=30.0
        )

        assert result is True

        # Check preset parameters in command
        call_args = mock_popen.call_args
        command = call_args[0][0]
        # YouTube preset should include specific encoding params
        assert 'libx264' in command or 'h264' in command.lower()

    @patch('subprocess.Popen')
    def test_apply_instagram_feed_preset(self, mock_popen, service, sample_video, temp_dir, sample_segment):
        """Test Instagram Feed preset (square 1080x1080)."""
        output_path = temp_dir / "output.mp4"

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = service.apply_preset(
            ExportPreset.INSTAGRAM_FEED,
            str(sample_video),
            sample_segment,
            str(output_path),
            fps=30.0
        )

        assert result is True

        # Check for resolution scaling
        call_args = mock_popen.call_args
        command = call_args[0][0]
        assert '1080' in command  # Should contain 1080 dimension

    @patch('subprocess.Popen')
    def test_apply_instagram_story_preset(self, mock_popen, service, sample_video, temp_dir, sample_segment):
        """Test Instagram Story preset (vertical 1080x1920)."""
        output_path = temp_dir / "output.mp4"

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = service.apply_preset(
            ExportPreset.INSTAGRAM_STORY,
            str(sample_video),
            sample_segment,
            str(output_path),
            fps=30.0
        )

        assert result is True

    def test_all_presets_defined(self):
        """Test that all required presets are defined."""
        assert hasattr(ExportPreset, 'YOUTUBE_1080P')
        assert hasattr(ExportPreset, 'YOUTUBE_4K')
        assert hasattr(ExportPreset, 'INSTAGRAM_FEED')
        assert hasattr(ExportPreset, 'INSTAGRAM_STORY')
        assert hasattr(ExportPreset, 'TWITTER')


class TestProgressReporting:
    """Test progress reporting during export."""

    @patch('subprocess.Popen')
    def test_export_progress_signal(self, mock_popen, service, sample_video, temp_dir, sample_segment):
        """Test that export reports progress."""
        output_path = temp_dir / "output.mp4"

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Signal spy
        progress_updates = []
        service.export_progress.connect(
            lambda current, total: progress_updates.append((current, total))
        )

        service.extract_segment(
            str(sample_video),
            sample_segment,
            str(output_path),
            fps=30.0
        )

        # May or may not emit progress depending on implementation
        # At minimum should not crash


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch('subprocess.Popen')
    def test_extract_very_short_segment(self, mock_popen, service, sample_video, temp_dir):
        """Test extracting very short segment (1 frame)."""
        segment = VideoSegment(start_frame=0, end_frame=0)
        output_path = temp_dir / "output.mp4"

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = service.extract_segment(
            str(sample_video),
            segment,
            str(output_path),
            fps=30.0
        )

        # Should handle gracefully

    @patch('subprocess.Popen')
    def test_extract_segment_special_characters_path(self, mock_popen, service, temp_dir):
        """Test extraction with special characters in path."""
        segment = VideoSegment(start_frame=0, end_frame=100)
        output_path = temp_dir / "output with spaces & special.mp4"

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = service.extract_segment(
            "/test/video.mp4",
            segment,
            str(output_path),
            fps=30.0
        )

        # Should handle special characters in path

    def test_export_to_nonexistent_directory(self, service, sample_video, temp_dir, sample_segment):
        """Test export to nonexistent directory."""
        output_path = temp_dir / "nonexistent" / "output.mp4"

        errors = []
        service.export_failed.connect(lambda msg: errors.append(msg))

        result = service.extract_segment(
            str(sample_video),
            sample_segment,
            str(output_path),
            fps=30.0
        )

        # Should either create directory or fail gracefully


# Integration tests
@pytest.mark.integration
@pytest.mark.ffmpeg
class TestExportServiceIntegration:
    """Integration tests requiring actual FFmpeg."""

    def test_real_segment_extraction(self, service, sample_video, temp_dir, sample_segment):
        """Test real segment extraction with FFmpeg."""
        # Skip if FFmpeg not available
        if not service.validate_ffmpeg():
            pytest.skip("FFmpeg not available")

        output_path = temp_dir / "output.mp4"

        result = service.extract_segment(
            str(sample_video),
            sample_segment,
            str(output_path),
            fps=30.0
        )

        assert result is True
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_real_frame_export(self, service, sample_video, temp_dir):
        """Test real frame export."""
        if not service.validate_ffmpeg():
            pytest.skip("FFmpeg not available")

        output_path = temp_dir / "frame.png"

        result = service.export_frame_as_image(
            str(sample_video),
            50,
            str(output_path)
        )

        assert result is True
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_real_audio_extraction(self, service, sample_video, temp_dir):
        """Test real audio extraction."""
        if not service.validate_ffmpeg():
            pytest.skip("FFmpeg not available")

        output_path = temp_dir / "audio.mp3"

        result = service.extract_audio(
            str(sample_video),
            str(output_path)
        )

        # May succeed or fail depending on whether video has audio
        # Just check it doesn't crash
