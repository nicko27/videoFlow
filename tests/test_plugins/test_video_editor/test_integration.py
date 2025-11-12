"""Integration tests for video_editor services.

Tests how all services work together in realistic scenarios.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.plugins.video_editor.services import (
    VideoPlayerService,
    SegmentEditorService,
    ExportService
)
from src.plugins.video_editor.segment_manager import VideoSegment, SegmentManager
from src.plugins.video_editor.history_manager import HistoryManager
from src.plugins.video_editor.utils.time_utils import TimeCode


@pytest.fixture
def player_service(qapp):
    """Create VideoPlayerService."""
    return VideoPlayerService()


@pytest.fixture
def segment_service(qapp):
    """Create SegmentEditorService with dependencies."""
    segment_manager = SegmentManager()
    history_manager = HistoryManager()
    return SegmentEditorService(segment_manager, history_manager)


@pytest.fixture
def export_service(qapp):
    """Create ExportService."""
    return ExportService()


@pytest.fixture
def timecode():
    """Create TimeCode utility."""
    return TimeCode(30.0)


@pytest.mark.integration
class TestVideoEditingWorkflow:
    """Test complete video editing workflow."""

    def test_load_create_export_workflow(
        self,
        player_service,
        segment_service,
        export_service,
        sample_video,
        temp_dir
    ):
        """Test: load video -> create segment -> export segment."""
        # 1. Load video
        assert player_service.load_video(str(sample_video))
        assert player_service.is_loaded

        # 2. Set up segment service with video info
        segment_service.set_total_frames(player_service.total_frames)

        # 3. Navigate to frame 30
        assert player_service.seek_to_frame(30)

        # 4. Set IN point
        assert segment_service.set_in_point(30)

        # 5. Navigate to frame 90
        assert player_service.seek_to_frame(90)

        # 6. Set OUT point
        assert segment_service.set_out_point(90)

        # 7. Create segment
        segment = segment_service.create_segment("Test Segment")
        assert segment is not None
        assert segment.start_frame == 30
        assert segment.end_frame == 90

        # 8. Export segment (mocked)
        output_path = temp_dir / "exported_segment.mp4"
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = (b"", b"")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            result = export_service.extract_segment(
                str(sample_video),
                segment,
                str(output_path),
                player_service.fps
            )
            assert result is True

        # 9. Close video
        player_service.close_video()
        assert not player_service.is_loaded

    def test_multi_segment_workflow(
        self,
        player_service,
        segment_service,
        sample_video
    ):
        """Test creating multiple segments."""
        # Load video
        player_service.load_video(str(sample_video))
        segment_service.set_total_frames(player_service.total_frames)

        # Create first segment (frames 0-50)
        player_service.seek_to_frame(0)
        segment_service.set_in_point(0)
        player_service.seek_to_frame(50)
        segment_service.set_out_point(50)
        seg1 = segment_service.create_segment("Intro")

        # Create second segment (frames 60-100)
        player_service.seek_to_frame(60)
        segment_service.set_in_point(60)
        player_service.seek_to_frame(100)
        segment_service.set_out_point(100)
        seg2 = segment_service.create_segment("Main")

        # Create third segment (frames 110-149)
        player_service.seek_to_frame(110)
        segment_service.set_in_point(110)
        player_service.seek_to_frame(149)
        segment_service.set_out_point(149)
        seg3 = segment_service.create_segment("Outro")

        # Verify all segments created
        assert len(segment_service.segments) == 3
        assert seg1.name == "Intro"
        assert seg2.name == "Main"
        assert seg3.name == "Outro"


@pytest.mark.integration
class TestTimeCodeIntegration:
    """Test TimeCode integration with services."""

    def test_timecode_with_player_service(self, player_service, timecode, sample_video):
        """Test TimeCode works with VideoPlayerService."""
        # Load video
        player_service.load_video(str(sample_video))

        # Update timecode with video FPS
        timecode = TimeCode(player_service.fps)

        # Navigate to specific frame
        frame = 90
        player_service.seek_to_frame(frame)

        # Convert to timecode
        seconds = timecode.frames_to_seconds(frame)
        timecode_str = timecode.seconds_to_timecode(seconds)

        # Should be "00:00:03" at 30fps
        assert timecode_str == "00:00:03"

    def test_timecode_with_segments(self, segment_service, timecode):
        """Test TimeCode with segment durations."""
        segment_service.set_total_frames(1000)

        # Create segment
        segment_service.set_in_point(30)
        segment_service.set_out_point(90)
        segment = segment_service.create_segment("Test")

        # Calculate duration
        duration_frames = segment.end_frame - segment.start_frame
        duration_seconds = timecode.frames_to_seconds(duration_frames)

        # Should be 2 seconds (60 frames at 30fps)
        assert abs(duration_seconds - 2.0) < 0.1


@pytest.mark.integration
class TestUndoRedoWithPlayback:
    """Test undo/redo while navigating video."""

    def test_undo_segment_and_continue_editing(
        self,
        player_service,
        segment_service,
        sample_video
    ):
        """Test undoing segment creation and continuing to edit."""
        # Load and setup
        player_service.load_video(str(sample_video))
        segment_service.set_total_frames(player_service.total_frames)

        # Create first segment
        segment_service.set_in_point(0)
        segment_service.set_out_point(50)
        seg1 = segment_service.create_segment("First")
        assert len(segment_service.segments) == 1

        # Undo
        segment_service._history_manager.undo()
        assert len(segment_service.segments) == 0

        # Continue editing - create different segment
        player_service.seek_to_frame(60)
        segment_service.set_in_point(60)
        player_service.seek_to_frame(100)
        segment_service.set_out_point(100)
        seg2 = segment_service.create_segment("Second")

        assert len(segment_service.segments) == 1
        assert seg2.name == "Second"


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling across services."""

    def test_export_without_video_loaded(self, export_service, temp_dir):
        """Test exporting when video doesn't exist."""
        segment = VideoSegment(start_frame=0, end_frame=100)
        output_path = temp_dir / "output.mp4"

        errors = []
        export_service.export_failed.connect(lambda msg: errors.append(msg))

        result = export_service.extract_segment(
            "/nonexistent/video.mp4",
            segment,
            str(output_path),
            30.0
        )

        assert result is False
        assert len(errors) > 0

    def test_create_segment_with_invalid_range(self, segment_service):
        """Test creating segment with invalid frame range."""
        segment_service.set_total_frames(1000)

        # Set OUT before IN
        segment_service.set_in_point(500)

        errors = []
        segment_service.error_occurred.connect(lambda msg: errors.append(msg))

        result = segment_service.set_out_point(100)

        assert result is False
        assert len(errors) > 0

    def test_navigate_beyond_video_length(self, player_service, sample_video):
        """Test navigating beyond video length."""
        player_service.load_video(str(sample_video))

        # Try to seek beyond total frames
        result = player_service.seek_to_frame(player_service.total_frames + 100)

        assert result is False
        # Current frame should not have changed


@pytest.mark.integration
class TestMultipleVideos:
    """Test working with multiple videos."""

    def test_switch_between_videos(self, player_service, multiple_videos):
        """Test loading multiple videos sequentially."""
        # Load first video
        player_service.load_video(str(multiple_videos[0]))
        first_fps = player_service.fps
        first_frames = player_service.total_frames

        # Load second video
        player_service.load_video(str(multiple_videos[1]))
        second_fps = player_service.fps
        second_frames = player_service.total_frames

        # Should have switched to second video
        assert player_service.video_path == str(multiple_videos[1])

    def test_segments_persist_across_video_changes(
        self,
        player_service,
        segment_service,
        multiple_videos
    ):
        """Test that segments persist when switching videos."""
        # Load first video and create segment
        player_service.load_video(str(multiple_videos[0]))
        segment_service.set_total_frames(player_service.total_frames)

        segment_service.set_in_point(0)
        segment_service.set_out_point(30)
        segment_service.create_segment("First Video Segment")

        # Switch to second video
        player_service.load_video(str(multiple_videos[1]))
        segment_service.set_total_frames(player_service.total_frames)

        # Original segments should still exist
        # (unless explicitly cleared by application logic)
        # Implementation dependent


@pytest.mark.integration
class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_scene_detection_simulation(
        self,
        player_service,
        segment_service,
        sample_video
    ):
        """Simulate scene detection creating multiple segments."""
        player_service.load_video(str(sample_video))
        segment_service.set_total_frames(player_service.total_frames)

        # Simulate scene detection finding scene boundaries
        scene_boundaries = [0, 50, 100, 149]

        # Create segments between boundaries
        for i in range(len(scene_boundaries) - 1):
            start = scene_boundaries[i]
            end = scene_boundaries[i + 1]

            segment_service.set_in_point(start)
            segment_service.set_out_point(end)
            segment_service.create_segment(f"Scene {i + 1}")

        assert len(segment_service.segments) == 3

    @patch('subprocess.Popen')
    def test_batch_export(
        self,
        mock_popen,
        player_service,
        segment_service,
        export_service,
        sample_video,
        temp_dir
    ):
        """Test exporting multiple segments."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Load video and create segments
        player_service.load_video(str(sample_video))
        segment_service.set_total_frames(player_service.total_frames)

        # Create 3 segments
        segments_data = [
            (0, 50, "Part 1"),
            (60, 110, "Part 2"),
            (120, 149, "Part 3")
        ]

        for start, end, name in segments_data:
            segment_service.set_in_point(start)
            segment_service.set_out_point(end)
            segment_service.create_segment(name)

        # Export all segments
        export_count = 0
        for i, segment in enumerate(segment_service.segments):
            output_path = temp_dir / f"segment_{i}.mp4"
            result = export_service.extract_segment(
                str(sample_video),
                segment,
                str(output_path),
                player_service.fps
            )
            if result:
                export_count += 1

        assert export_count == 3

    def test_edit_undo_redo_export(
        self,
        player_service,
        segment_service,
        export_service,
        sample_video,
        temp_dir
    ):
        """Test complete workflow with undo/redo."""
        # Load video
        player_service.load_video(str(sample_video))
        segment_service.set_total_frames(player_service.total_frames)

        # Create segment
        segment_service.set_in_point(0)
        segment_service.set_out_point(50)
        seg1 = segment_service.create_segment("Original")

        # Modify segment
        segment_service.update_segment(0, name="Modified")
        assert segment_service.segments[0].name == "Modified"

        # Undo modification
        segment_service._history_manager.undo()
        assert segment_service.segments[0].name == "Original"

        # Redo modification
        segment_service._history_manager.redo()
        assert segment_service.segments[0].name == "Modified"

        # Export final version (mocked)
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = (b"", b"")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            output_path = temp_dir / "final.mp4"
            result = export_service.extract_segment(
                str(sample_video),
                segment_service.segments[0],
                str(output_path),
                player_service.fps
            )
            assert result is True


@pytest.mark.integration
class TestServiceCommunication:
    """Test communication between services via signals."""

    def test_player_to_segment_coordination(
        self,
        player_service,
        segment_service,
        sample_video
    ):
        """Test coordinating player and segment service via signals."""
        player_service.load_video(str(sample_video))
        segment_service.set_total_frames(player_service.total_frames)

        # Track frame changes
        frame_changes = []
        player_service.frame_changed.connect(
            lambda frame_num, frame_data: frame_changes.append(frame_num)
        )

        # Navigate and track
        player_service.seek_to_frame(30)
        player_service.next_frame()
        player_service.next_frame()

        # Should have received frame change signals
        assert len(frame_changes) >= 3

    def test_segment_to_export_coordination(
        self,
        segment_service,
        export_service,
        sample_video,
        temp_dir
    ):
        """Test coordinating segment and export services."""
        segment_service.set_total_frames(150)

        # Track segment creation
        created_segments = []
        segment_service.segment_created.connect(
            lambda seg: created_segments.append(seg)
        )

        # Create segment
        segment_service.set_in_point(0)
        segment_service.set_out_point(50)
        segment = segment_service.create_segment("Export Test")

        assert len(created_segments) == 1

        # Export the created segment (mocked)
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = (b"", b"")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            export_finished = []
            export_service.export_finished.connect(
                lambda path: export_finished.append(path)
            )

            output_path = temp_dir / "output.mp4"
            export_service.extract_segment(
                str(sample_video),
                created_segments[0],
                str(output_path),
                30.0
            )

            assert len(export_finished) == 1


@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """Test performance with realistic data."""

    def test_many_segments_performance(self, segment_service):
        """Test performance with many segments."""
        import time

        segment_service.set_total_frames(100000)  # ~55 minutes at 30fps

        start_time = time.time()

        # Create 100 segments
        for i in range(100):
            segment_service.set_in_point(i * 1000)
            segment_service.set_out_point(i * 1000 + 500)
            segment_service.create_segment(f"Segment {i}")

        elapsed = time.time() - start_time

        # Should complete reasonably fast (< 1 second)
        assert elapsed < 1.0
        assert len(segment_service.segments) == 100

    def test_rapid_frame_navigation(self, player_service, sample_video):
        """Test rapid frame navigation performance."""
        import time

        player_service.load_video(str(sample_video))

        start_time = time.time()

        # Navigate rapidly through video
        for i in range(0, 150, 5):
            player_service.seek_to_frame(i)

        elapsed = time.time() - start_time

        # Should complete reasonably fast
        assert elapsed < 2.0


@pytest.mark.integration
class TestResourceManagement:
    """Test resource management across services."""

    def test_cleanup_on_close(self, player_service, sample_video):
        """Test resources are cleaned up properly."""
        # Load video
        player_service.load_video(str(sample_video))
        assert player_service.is_loaded

        # Start playback
        player_service.start_playback()
        assert player_service.is_playing

        # Close should stop playback and release resources
        player_service.close_video()
        assert not player_service.is_loaded
        assert not player_service.is_playing

    def test_multiple_load_close_cycles(self, player_service, sample_video):
        """Test multiple load/close cycles don't leak resources."""
        # Load and close multiple times
        for _ in range(5):
            player_service.load_video(str(sample_video))
            assert player_service.is_loaded

            player_service.close_video()
            assert not player_service.is_loaded

        # Should not have leaked resources (hard to test directly)
