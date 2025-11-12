"""Segment Editor Service - Business logic for segment operations.

This service handles all segment-related operations, independent of the UI layer.
"""

from typing import List, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from ..segment_manager import VideoSegment, SegmentManager
from ..history_manager import HistoryManager, HistoryAction
from ..utils.video_utils import validate_frame_range
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.SegmentEditorService')


class SegmentEditorService(QObject):
    """Service for managing video segment operations.

    This service encapsulates all segment editing logic, making it
    easier to test and maintain.

    Signals:
        segment_created: Emitted when a segment is created (segment)
        segment_deleted: Emitted when a segment is deleted (index)
        segment_updated: Emitted when a segment is updated (index, segment)
        segments_reordered: Emitted when segments are reordered
        in_point_set: Emitted when IN point is set (frame)
        out_point_set: Emitted when OUT point is set (frame)
        cut_cancelled: Emitted when a cut operation is cancelled
        error_occurred: Emitted when an error occurs (error_message)
    """

    segment_created = pyqtSignal(VideoSegment)
    segment_deleted = pyqtSignal(int)
    segment_updated = pyqtSignal(int, VideoSegment)
    segments_reordered = pyqtSignal()
    in_point_set = pyqtSignal(int)
    out_point_set = pyqtSignal(int)
    cut_cancelled = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, segment_manager: SegmentManager, history_manager: HistoryManager):
        """Initialize the segment editor service.

        Args:
            segment_manager: Manager for video segments
            history_manager: Manager for undo/redo history
        """
        super().__init__()

        self._segment_manager = segment_manager
        self._history_manager = history_manager
        self._in_point: Optional[int] = None
        self._out_point: Optional[int] = None
        self._total_frames: int = 0

    @property
    def segments(self) -> List[VideoSegment]:
        """Get all segments."""
        return self._segment_manager.segments

    @property
    def in_point(self) -> Optional[int]:
        """Get current IN point."""
        return self._in_point

    @property
    def out_point(self) -> Optional[int]:
        """Get current OUT point."""
        return self._out_point

    @property
    def has_active_cut(self) -> bool:
        """Check if there's an active cut (IN or OUT point set)."""
        return self._in_point is not None or self._out_point is not None

    def set_total_frames(self, total_frames: int):
        """Set the total number of frames in the video.

        Args:
            total_frames: Total number of frames
        """
        self._total_frames = total_frames

    def set_in_point(self, frame: int) -> bool:
        """Set the IN point for a new segment.

        Args:
            frame: Frame number for IN point

        Returns:
            True if successful, False otherwise
        """
        if frame < 0 or frame >= self._total_frames:
            error_msg = f"Invalid IN point: {frame} (must be 0-{self._total_frames - 1})"
            logger.warning(error_msg)
            self.error_occurred.emit(error_msg)
            return False

        # Check if OUT point exists and is before this IN point
        if self._out_point is not None and frame >= self._out_point:
            error_msg = "IN point must be before OUT point"
            logger.warning(error_msg)
            self.error_occurred.emit(error_msg)
            return False

        self._in_point = frame
        self.in_point_set.emit(frame)
        logger.debug(f"IN point set to frame {frame}")
        return True

    def set_out_point(self, frame: int) -> bool:
        """Set the OUT point for a new segment.

        Args:
            frame: Frame number for OUT point

        Returns:
            True if successful, False otherwise
        """
        if frame < 0 or frame >= self._total_frames:
            error_msg = f"Invalid OUT point: {frame} (must be 0-{self._total_frames - 1})"
            logger.warning(error_msg)
            self.error_occurred.emit(error_msg)
            return False

        # Check if IN point exists and is after this OUT point
        if self._in_point is not None and frame <= self._in_point:
            error_msg = "OUT point must be after IN point"
            logger.warning(error_msg)
            self.error_occurred.emit(error_msg)
            return False

        self._out_point = frame
        self.out_point_set.emit(frame)
        logger.debug(f"OUT point set to frame {frame}")
        return True

    def create_segment(self, name: str = "") -> Optional[VideoSegment]:
        """Create a segment from IN and OUT points.

        Args:
            name: Optional name for the segment

        Returns:
            Created segment, or None if creation failed
        """
        if self._in_point is None or self._out_point is None:
            error_msg = "Both IN and OUT points must be set to create a segment"
            logger.warning(error_msg)
            self.error_occurred.emit(error_msg)
            return None

        # Validate frame range
        is_valid, error = validate_frame_range(
            self._in_point,
            self._out_point,
            self._total_frames
        )

        if not is_valid:
            logger.error(f"Invalid segment range: {error}")
            self.error_occurred.emit(error)
            return None

        # Create segment
        segment = VideoSegment(
            start_frame=self._in_point,
            end_frame=self._out_point,
            name=name if name else f"Segment {len(self._segment_manager.segments) + 1}"
        )

        # Add to manager
        self._segment_manager.add_segment(segment)

        # Add to history
        self._history_manager.record_action(
            HistoryAction(
                action_type='create_segment',
                description=f"Create segment: {segment.name}",
                data={'segment': segment}
            ),
            undo_callback=lambda: self._undo_create_segment(segment),
            redo_callback=lambda: self._redo_create_segment(segment)
        )

        # Clear IN/OUT points
        self._in_point = None
        self._out_point = None

        self.segment_created.emit(segment)
        logger.info(f"Segment created: {segment.name} (frames {segment.start_frame}-{segment.end_frame})")

        return segment

    def delete_segment(self, index: int) -> bool:
        """Delete a segment.

        Args:
            index: Index of segment to delete

        Returns:
            True if successful, False otherwise
        """
        if index < 0 or index >= len(self._segment_manager.segments):
            error_msg = f"Invalid segment index: {index}"
            logger.warning(error_msg)
            self.error_occurred.emit(error_msg)
            return False

        segment = self._segment_manager.segments[index]

        # Remove from manager
        self._segment_manager.remove_segment(index)

        # Add to history
        self._history_manager.record_action(
            HistoryAction(
                action_type='delete_segment',
                description=f"Delete segment: {segment.name}",
                data={'segment': segment, 'index': index}
            ),
            undo_callback=lambda: self._undo_delete_segment(segment, index),
            redo_callback=lambda: self._redo_delete_segment(index)
        )

        self.segment_deleted.emit(index)
        logger.info(f"Segment deleted: {segment.name}")

        return True

    def update_segment(self, index: int, **kwargs) -> bool:
        """Update segment properties.

        Args:
            index: Index of segment to update
            **kwargs: Properties to update (name, start_frame, end_frame, color, etc.)

        Returns:
            True if successful, False otherwise
        """
        if index < 0 or index >= len(self._segment_manager.segments):
            error_msg = f"Invalid segment index: {index}"
            logger.warning(error_msg)
            self.error_occurred.emit(error_msg)
            return False

        segment = self._segment_manager.segments[index]

        # Store old values for undo
        old_values = {}
        for key, value in kwargs.items():
            if hasattr(segment, key):
                old_values[key] = getattr(segment, key)
                setattr(segment, key, value)

        # Add to history
        self._history_manager.record_action(
            HistoryAction(
                action_type='update_segment',
                description=f"Update segment: {segment.name}",
                data={'index': index, 'old_values': old_values, 'new_values': kwargs}
            ),
            undo_callback=lambda: self._undo_update_segment(index, old_values),
            redo_callback=lambda: self._redo_update_segment(index, kwargs)
        )

        self.segment_updated.emit(index, segment)
        logger.debug(f"Segment updated: {segment.name}")

        return True

    def cancel_cut(self):
        """Cancel the current cut operation (clear IN/OUT points)."""
        self._in_point = None
        self._out_point = None
        self.cut_cancelled.emit()
        logger.debug("Cut cancelled")

    def get_segment_at_frame(self, frame: int) -> Optional[VideoSegment]:
        """Get the segment that contains the given frame.

        Args:
            frame: Frame number

        Returns:
            Segment containing the frame, or None if no segment found
        """
        for segment in self._segment_manager.segments:
            if segment.start_frame <= frame <= segment.end_frame:
                return segment
        return None

    # Undo/Redo callbacks

    def _undo_create_segment(self, segment: VideoSegment):
        """Undo segment creation."""
        try:
            index = self._segment_manager.segments.index(segment)
            self._segment_manager.remove_segment(index)
            self.segment_deleted.emit(index)
        except ValueError:
            logger.warning(f"Cannot undo create segment: segment not found")

    def _redo_create_segment(self, segment: VideoSegment):
        """Redo segment creation."""
        self._segment_manager.add_segment(segment)
        self.segment_created.emit(segment)

    def _undo_delete_segment(self, segment: VideoSegment, original_index: int):
        """Undo segment deletion."""
        self._segment_manager.segments.insert(original_index, segment)
        self.segment_created.emit(segment)

    def _redo_delete_segment(self, index: int):
        """Redo segment deletion."""
        if index < len(self._segment_manager.segments):
            self._segment_manager.remove_segment(index)
            self.segment_deleted.emit(index)

    def _undo_update_segment(self, index: int, old_values: dict):
        """Undo segment update."""
        if index < len(self._segment_manager.segments):
            segment = self._segment_manager.segments[index]
            for key, value in old_values.items():
                setattr(segment, key, value)
            self.segment_updated.emit(index, segment)

    def _redo_update_segment(self, index: int, new_values: dict):
        """Redo segment update."""
        if index < len(self._segment_manager.segments):
            segment = self._segment_manager.segments[index]
            for key, value in new_values.items():
                setattr(segment, key, value)
            self.segment_updated.emit(index, segment)
