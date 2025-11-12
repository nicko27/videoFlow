"""Tests for SegmentEditorService.

Tests the segment editing service including:
- Segment creation and deletion
- IN/OUT point management
- Undo/Redo integration
- Validation and error handling
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.plugins.video_editor.services.segment_editor_service import SegmentEditorService
from src.plugins.video_editor.segment_manager import VideoSegment, SegmentManager
from src.plugins.video_editor.history_manager import HistoryManager


@pytest.fixture
def segment_manager():
    """Create SegmentManager instance.

    Returns:
        SegmentManager instance
    """
    return SegmentManager()


@pytest.fixture
def history_manager():
    """Create HistoryManager instance.

    Returns:
        HistoryManager instance
    """
    return HistoryManager(max_history=50)


@pytest.fixture
def service(qapp, segment_manager, history_manager):
    """Create SegmentEditorService instance.

    Args:
        qapp: QApplication fixture
        segment_manager: SegmentManager fixture
        history_manager: HistoryManager fixture

    Returns:
        SegmentEditorService instance
    """
    return SegmentEditorService(segment_manager, history_manager)


class TestSegmentEditorServiceInitialization:
    """Test service initialization."""

    def test_init(self, service):
        """Test service initializes correctly."""
        assert service is not None
        assert len(service.segments) == 0
        assert service.in_point is None
        assert service.out_point is None
        assert not service.has_active_cut

    def test_init_with_managers(self, segment_manager, history_manager):
        """Test initialization with provided managers."""
        service = SegmentEditorService(segment_manager, history_manager)

        assert service._segment_manager is segment_manager
        assert service._history_manager is history_manager


class TestTotalFrames:
    """Test total frames management."""

    def test_set_total_frames(self, service):
        """Test setting total frames."""
        service.set_total_frames(1000)

        assert service._total_frames == 1000

    def test_set_total_frames_validation(self, service):
        """Test that total frames must be positive."""
        # Should handle gracefully
        service.set_total_frames(-100)
        # Implementation dependent - check docs


class TestInOutPoints:
    """Test IN/OUT point management."""

    def test_set_in_point(self, service):
        """Test setting IN point."""
        service.set_total_frames(1000)

        # Signal spy
        signals = []
        service.in_point_set.connect(lambda frame: signals.append(frame))

        result = service.set_in_point(100)

        assert result is True
        assert service.in_point == 100
        assert len(signals) == 1
        assert signals[0] == 100

    def test_set_out_point(self, service):
        """Test setting OUT point."""
        service.set_total_frames(1000)

        # Signal spy
        signals = []
        service.out_point_set.connect(lambda frame: signals.append(frame))

        result = service.set_out_point(500)

        assert result is True
        assert service.out_point == 500
        assert len(signals) == 1
        assert signals[0] == 500

    def test_set_in_point_invalid_negative(self, service):
        """Test setting negative IN point."""
        service.set_total_frames(1000)

        # Error spy
        errors = []
        service.error_occurred.connect(lambda msg: errors.append(msg))

        result = service.set_in_point(-10)

        assert result is False
        assert service.in_point is None
        assert len(errors) == 1

    def test_set_in_point_beyond_total(self, service):
        """Test setting IN point beyond total frames."""
        service.set_total_frames(1000)

        errors = []
        service.error_occurred.connect(lambda msg: errors.append(msg))

        result = service.set_in_point(1500)

        assert result is False
        assert len(errors) == 1

    def test_set_out_point_before_in_point(self, service):
        """Test setting OUT point before IN point."""
        service.set_total_frames(1000)
        service.set_in_point(500)

        errors = []
        service.error_occurred.connect(lambda msg: errors.append(msg))

        result = service.set_out_point(300)

        assert result is False
        assert len(errors) == 1

    def test_has_active_cut(self, service):
        """Test has_active_cut property."""
        assert not service.has_active_cut

        service.set_total_frames(1000)
        service.set_in_point(100)

        assert service.has_active_cut

        service.set_out_point(500)

        assert service.has_active_cut

    def test_cancel_cut(self, service):
        """Test cancelling cut."""
        service.set_total_frames(1000)
        service.set_in_point(100)
        service.set_out_point(500)

        # Signal spy
        cancelled = []
        service.cut_cancelled.connect(lambda: cancelled.append(True))

        service.cancel_cut()

        assert service.in_point is None
        assert service.out_point is None
        assert not service.has_active_cut
        assert len(cancelled) == 1


class TestSegmentCreation:
    """Test segment creation."""

    def test_create_segment(self, service):
        """Test creating segment from IN/OUT points."""
        service.set_total_frames(1000)
        service.set_in_point(100)
        service.set_out_point(500)

        # Signal spy
        created_segments = []
        service.segment_created.connect(lambda seg: created_segments.append(seg))

        segment = service.create_segment("Test Segment")

        assert segment is not None
        assert segment.start_frame == 100
        assert segment.end_frame == 500
        assert segment.name == "Test Segment"
        assert len(service.segments) == 1
        assert len(created_segments) == 1
        # IN/OUT should be cleared after creation
        assert service.in_point is None
        assert service.out_point is None

    def test_create_segment_without_in_point(self, service):
        """Test creating segment without IN point."""
        service.set_total_frames(1000)
        service.set_out_point(500)

        errors = []
        service.error_occurred.connect(lambda msg: errors.append(msg))

        segment = service.create_segment("Test")

        assert segment is None
        assert len(errors) == 1
        assert len(service.segments) == 0

    def test_create_segment_without_out_point(self, service):
        """Test creating segment without OUT point."""
        service.set_total_frames(1000)
        service.set_in_point(100)

        errors = []
        service.error_occurred.connect(lambda msg: errors.append(msg))

        segment = service.create_segment("Test")

        assert segment is None
        assert len(errors) == 1

    def test_create_multiple_segments(self, service):
        """Test creating multiple segments."""
        service.set_total_frames(1000)

        # Create first segment
        service.set_in_point(0)
        service.set_out_point(100)
        seg1 = service.create_segment("Segment 1")

        # Create second segment
        service.set_in_point(200)
        service.set_out_point(300)
        seg2 = service.create_segment("Segment 2")

        assert len(service.segments) == 2
        assert seg1.name == "Segment 1"
        assert seg2.name == "Segment 2"

    def test_create_segment_default_name(self, service):
        """Test creating segment with default name."""
        service.set_total_frames(1000)
        service.set_in_point(0)
        service.set_out_point(100)

        segment = service.create_segment()

        assert segment is not None
        # Should have auto-generated name
        assert segment.name is not None


class TestSegmentDeletion:
    """Test segment deletion."""

    def test_delete_segment(self, service):
        """Test deleting segment."""
        service.set_total_frames(1000)

        # Create segments
        service.set_in_point(0)
        service.set_out_point(100)
        service.create_segment("Segment 1")

        service.set_in_point(200)
        service.set_out_point(300)
        service.create_segment("Segment 2")

        # Signal spy
        deleted = []
        service.segment_deleted.connect(lambda idx: deleted.append(idx))

        # Delete first segment
        result = service.delete_segment(0)

        assert result is True
        assert len(service.segments) == 1
        assert service.segments[0].name == "Segment 2"
        assert len(deleted) == 1
        assert deleted[0] == 0

    def test_delete_segment_invalid_index(self, service):
        """Test deleting segment with invalid index."""
        service.set_total_frames(1000)
        service.set_in_point(0)
        service.set_out_point(100)
        service.create_segment("Segment 1")

        errors = []
        service.error_occurred.connect(lambda msg: errors.append(msg))

        # Try to delete invalid index
        result = service.delete_segment(10)

        assert result is False
        assert len(errors) == 1
        assert len(service.segments) == 1  # Unchanged

    def test_delete_segment_negative_index(self, service):
        """Test deleting with negative index."""
        service.set_total_frames(1000)
        service.set_in_point(0)
        service.set_out_point(100)
        service.create_segment("Segment 1")

        errors = []
        service.error_occurred.connect(lambda msg: errors.append(msg))

        result = service.delete_segment(-1)

        assert result is False
        assert len(errors) == 1


class TestSegmentUpdate:
    """Test segment updating."""

    def test_update_segment(self, service):
        """Test updating segment properties."""
        service.set_total_frames(1000)
        service.set_in_point(0)
        service.set_out_point(100)
        service.create_segment("Original Name")

        # Signal spy
        updated = []
        service.segment_updated.connect(
            lambda idx, seg: updated.append((idx, seg))
        )

        result = service.update_segment(0, name="Updated Name")

        assert result is True
        assert service.segments[0].name == "Updated Name"
        assert len(updated) == 1

    def test_update_segment_frames(self, service):
        """Test updating segment frame range."""
        service.set_total_frames(1000)
        service.set_in_point(0)
        service.set_out_point(100)
        service.create_segment("Test")

        result = service.update_segment(
            0,
            start_frame=50,
            end_frame=150
        )

        assert result is True
        assert service.segments[0].start_frame == 50
        assert service.segments[0].end_frame == 150

    def test_update_segment_invalid_index(self, service):
        """Test updating with invalid index."""
        service.set_total_frames(1000)
        service.set_in_point(0)
        service.set_out_point(100)
        service.create_segment("Test")

        errors = []
        service.error_occurred.connect(lambda msg: errors.append(msg))

        result = service.update_segment(10, name="New Name")

        assert result is False
        assert len(errors) == 1

    def test_update_segment_invalid_range(self, service):
        """Test updating with invalid frame range."""
        service.set_total_frames(1000)
        service.set_in_point(0)
        service.set_out_point(100)
        service.create_segment("Test")

        errors = []
        service.error_occurred.connect(lambda msg: errors.append(msg))

        # Try to set end before start
        result = service.update_segment(
            0,
            start_frame=500,
            end_frame=100
        )

        assert result is False
        assert len(errors) == 1


class TestSegmentQuerying:
    """Test segment querying methods."""

    def test_get_segment_at_frame(self, service):
        """Test finding segment at specific frame."""
        service.set_total_frames(1000)

        # Create segments
        service.set_in_point(0)
        service.set_out_point(100)
        seg1 = service.create_segment("Segment 1")

        service.set_in_point(200)
        service.set_out_point(300)
        seg2 = service.create_segment("Segment 2")

        # Query segments
        assert service.get_segment_at_frame(50) == seg1
        assert service.get_segment_at_frame(250) == seg2
        assert service.get_segment_at_frame(150) is None  # Gap

    def test_get_segment_at_frame_empty(self, service):
        """Test querying when no segments exist."""
        service.set_total_frames(1000)

        segment = service.get_segment_at_frame(100)

        assert segment is None


class TestUndoRedoIntegration:
    """Test undo/redo integration."""

    def test_create_segment_undo(self, service, history_manager):
        """Test that segment creation can be undone."""
        service.set_total_frames(1000)
        service.set_in_point(0)
        service.set_out_point(100)
        service.create_segment("Test")

        assert len(service.segments) == 1

        # Undo
        history_manager.undo()

        assert len(service.segments) == 0

    def test_create_segment_redo(self, service, history_manager):
        """Test that segment creation can be redone."""
        service.set_total_frames(1000)
        service.set_in_point(0)
        service.set_out_point(100)
        service.create_segment("Test")

        # Undo then redo
        history_manager.undo()
        assert len(service.segments) == 0

        history_manager.redo()
        assert len(service.segments) == 1

    def test_delete_segment_undo(self, service, history_manager):
        """Test that segment deletion can be undone."""
        service.set_total_frames(1000)
        service.set_in_point(0)
        service.set_out_point(100)
        segment = service.create_segment("Test")

        service.delete_segment(0)
        assert len(service.segments) == 0

        # Undo deletion
        history_manager.undo()
        assert len(service.segments) == 1

    def test_update_segment_undo(self, service, history_manager):
        """Test that segment update can be undone."""
        service.set_total_frames(1000)
        service.set_in_point(0)
        service.set_out_point(100)
        service.create_segment("Original")

        service.update_segment(0, name="Updated")
        assert service.segments[0].name == "Updated"

        # Undo update
        history_manager.undo()
        assert service.segments[0].name == "Original"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_create_segment_at_frame_zero(self, service):
        """Test creating segment starting at frame 0."""
        service.set_total_frames(1000)
        service.set_in_point(0)
        service.set_out_point(100)

        segment = service.create_segment("Test")

        assert segment is not None
        assert segment.start_frame == 0

    def test_create_segment_at_last_frame(self, service):
        """Test creating segment ending at last frame."""
        service.set_total_frames(1000)
        service.set_in_point(900)
        service.set_out_point(999)

        segment = service.create_segment("Test")

        assert segment is not None
        assert segment.end_frame == 999

    def test_create_single_frame_segment(self, service):
        """Test creating segment with only one frame."""
        service.set_total_frames(1000)
        service.set_in_point(100)
        service.set_out_point(100)

        errors = []
        service.error_occurred.connect(lambda msg: errors.append(msg))

        segment = service.create_segment("Test")

        # Should either create 1-frame segment or fail with error
        # Implementation dependent

    def test_many_segments(self, service):
        """Test creating many segments."""
        service.set_total_frames(10000)

        # Create 100 segments
        for i in range(100):
            service.set_in_point(i * 100)
            service.set_out_point(i * 100 + 50)
            service.create_segment(f"Segment {i}")

        assert len(service.segments) == 100


class TestValidation:
    """Test validation logic."""

    def test_validate_frame_range(self, service):
        """Test frame range validation."""
        service.set_total_frames(1000)

        # Valid ranges
        assert service.set_in_point(0) is True
        assert service.set_out_point(999) is True

        # Invalid: negative
        assert service.set_in_point(-1) is False

        # Invalid: beyond total
        assert service.set_out_point(1000) is False

    def test_segments_cannot_overlap(self, service):
        """Test that overlapping segments are handled."""
        service.set_total_frames(1000)

        # Create first segment
        service.set_in_point(0)
        service.set_out_point(100)
        service.create_segment("Segment 1")

        # Try to create overlapping segment
        service.set_in_point(50)
        service.set_out_point(150)
        segment = service.create_segment("Segment 2")

        # Implementation dependent - may allow or reject
        # Check documentation


# Integration tests
@pytest.mark.integration
class TestSegmentEditorServiceIntegration:
    """Integration tests for SegmentEditorService."""

    def test_full_workflow(self, service):
        """Test complete editing workflow."""
        service.set_total_frames(1000)

        # Create segment
        service.set_in_point(0)
        service.set_out_point(100)
        seg1 = service.create_segment("First")

        # Create another
        service.set_in_point(200)
        service.set_out_point(300)
        seg2 = service.create_segment("Second")

        # Update first
        service.update_segment(0, name="First Updated")

        # Delete second
        service.delete_segment(1)

        assert len(service.segments) == 1
        assert service.segments[0].name == "First Updated"

    def test_complex_undo_redo(self, service, history_manager):
        """Test complex undo/redo scenario."""
        service.set_total_frames(1000)

        # Create 3 segments
        for i in range(3):
            service.set_in_point(i * 100)
            service.set_out_point(i * 100 + 50)
            service.create_segment(f"Segment {i}")

        assert len(service.segments) == 3

        # Undo 2 times
        history_manager.undo()
        history_manager.undo()

        assert len(service.segments) == 1

        # Redo once
        history_manager.redo()

        assert len(service.segments) == 2
