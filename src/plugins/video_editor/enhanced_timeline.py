"""Enhanced Timeline - Larger, clearer timeline with thumbnails.

Provides professional timeline with better visibility and usability.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QImage, QPolygon
from typing import Optional, List
import cv2
import numpy as np
from src.core.i18n import t
from .utils.time_utils import TimeCode
from .segment_manager import SegmentManager


class EnhancedTimeline(QWidget):
    """Enhanced timeline with better visibility.

    Features:
    - Larger height (150px minimum)
    - Segment thumbnails
    - Clear markers
    - Zoom controls
    - Better visual feedback
    """

    position_changed = pyqtSignal(int)  # frame
    segment_created = pyqtSignal(object)  # segment
    segment_deleted = pyqtSignal(int)  # index
    segment_selected = pyqtSignal(int)  # index

    def __init__(self, parent=None, segment_manager=None):
        """Initialize enhanced timeline.

        Args:
            parent: Parent widget
            segment_manager: Optional SegmentManager instance (creates new if None)
        """
        super().__init__(parent)

        # State
        self.total_frames = 0
        self.current_frame = 0
        self.current_segment = None
        self.selected_segment_index = -1
        self.markers = {}
        self._updating = False

        # Segment Manager (manages segments list)
        self.segment_manager = segment_manager if segment_manager is not None else SegmentManager()
        # Keep segments as property for backward compatibility
        self.segments = self.segment_manager.segments

        # IN/OUT points
        self.in_point = None
        self.out_point = None

        # Zoom
        self.zoom_level = 1.0

        # Thumbnails cache
        self.thumbnails = {}  # segment_index -> QPixmap

        # TimeCode utility for formatting
        self.timecode = TimeCode(30.0)  # Default, will be updated

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        """Set up timeline UI."""
        # Override global stylesheet to use light theme for timeline
        self.setStyleSheet("""
            EnhancedTimeline {
                background-color: #f5f5f5;
            }
            QLabel {
                background-color: transparent;
                color: #333;
            }
            QPushButton {
                background-color: #0066cc;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        # Top controls bar
        controls = QHBoxLayout()
        controls.setSpacing(10)

        # Zoom controls
        controls.addWidget(QLabel("🔍"))

        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setFixedSize(30, 30)
        zoom_out_btn.setToolTip(t("video_editor.timeline.tooltip_zoom_out", "Zoom out"))
        zoom_out_btn.clicked.connect(self.zoom_out)
        controls.addWidget(zoom_out_btn)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.zoom_label.font()
        font.setBold(True)
        self.zoom_label.setFont(font)
        controls.addWidget(self.zoom_label)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(30, 30)
        zoom_in_btn.setToolTip(t("video_editor.timeline.tooltip_zoom_in", "Zoom in"))
        zoom_in_btn.clicked.connect(self.zoom_in)
        controls.addWidget(zoom_in_btn)

        controls.addStretch()

        # Info label
        self.info_label = QLabel(t("video_editor.timeline.label_no_video", "No video"))
        font = self.info_label.font()
        font.setPointSize(11)
        self.info_label.setFont(font)
        controls.addWidget(self.info_label)

        main_layout.addLayout(controls)

        # Timeline canvas
        # Note: Height is now controlled by setMaximumHeight in window.py to prevent overflow
        self.setMouseTracking(True)

        # Colors (Light theme)
        self.colors = {
            'background': QColor(245, 245, 245),  # Fond clair
            'timeline': QColor(220, 220, 220),  # Gris clair pour la timeline
            'cursor': QColor(255, 0, 0),  # Rouge pour le curseur (plus visible)
            'segment': QColor(100, 180, 255, 180),  # Bleu clair
            'segment_selected': QColor(0, 120, 215, 220),  # Bleu plus foncé quand sélectionné
            'segment_border': QColor(0, 100, 200),  # Bordure bleue
            'in_marker': QColor(0, 200, 0),  # Vert
            'out_marker': QColor(255, 0, 0),  # Rouge
            'marker': QColor(50, 50, 50)  # Texte gris foncé
        }

    def set_total_frames(self, frames: int):
        """Set total frames and update info.

        Args:
            frames: Total number of frames
        """
        self.total_frames = frames
        self.update_info_label()
        self.update()

    def set_current_frame(self, frame: int):
        """Set current frame.

        Args:
            frame: Frame number
        """
        if self._updating or not (0 <= frame <= self.total_frames):
            return

        try:
            self._updating = True
            self.current_frame = frame
            self.update()
            self.position_changed.emit(frame)
        finally:
            self._updating = False

    def zoom_in(self):
        """Zoom in timeline."""
        self.zoom_level = min(self.zoom_level * 1.5, 10.0)
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
        self.update()

    def zoom_out(self):
        """Zoom out timeline."""
        self.zoom_level = max(self.zoom_level / 1.5, 0.1)
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
        self.update()

    def set_in_point(self, frame: int):
        """Mark IN point."""
        self.in_point = frame
        self.update()

    def set_out_point(self, frame: int):
        """Mark OUT point."""
        self.out_point = frame
        self.update()

    def clear_in_out_points(self):
        """Clear IN/OUT points."""
        self.in_point = None
        self.out_point = None
        self.update()

    def add_segment(self, segment):
        """Add segment to timeline.

        Args:
            segment: VideoSegment
        """
        self.segments.append(segment)
        self.update_info_label()
        self.update()

    def select_segment(self, index: int):
        """Select segment.

        Args:
            index: Segment index
        """
        self.selected_segment_index = index
        self.segment_selected.emit(index)
        self.update()

    def get_segments(self) -> List:
        """Get all segments.

        Returns:
            List of segments
        """
        return self.segments

    def clear_segments(self):
        """Clear all segments."""
        self.segments = []
        self.selected_segment_index = -1
        self.thumbnails = {}
        self.update_info_label()
        self.update()

    def update_info_label(self):
        """Update info label."""
        if self.total_frames > 0:
            total_secs = self.total_frames / 30.0  # Assuming 30fps
            segments_count = len(self.segments)
            self.info_label.setText(
                t("video_editor.timeline.label_info", "Segments: {count} │ Duration: {duration}",
                  count=segments_count, duration=self._format_time(total_secs))
            )
        else:
            self.info_label.setText(t("video_editor.timeline.label_no_video", "No video"))

    def _format_time(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS using TimeCode utility.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string
        """
        return self.timecode.seconds_to_timecode(seconds)

    def _frame_to_pixel(self, frame: int) -> int:
        """Convert frame to pixel position.

        Args:
            frame: Frame number

        Returns:
            Pixel x position
        """
        if self.total_frames == 0:
            return 0
        return int((frame / self.total_frames) * self.width() * self.zoom_level)

    def _pixel_to_frame(self, x: int) -> int:
        """Convert pixel to frame number.

        Args:
            x: Pixel x position

        Returns:
            Frame number
        """
        if self.total_frames == 0:
            return 0
        return int((x / (self.width() * self.zoom_level)) * self.total_frames)

    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            frame = self._pixel_to_frame(event.position().x())
            frame = max(0, min(frame, self.total_frames))

            # Check if clicked on segment
            for i, segment in enumerate(self.segments):
                x1 = self._frame_to_pixel(segment.start_frame)
                x2 = self._frame_to_pixel(segment.end_frame if segment.end_frame else self.current_frame)

                if x1 <= event.position().x() <= x2:
                    self.select_segment(i)
                    return

            # Clicked on empty area - seek
            self.set_current_frame(frame)

    def paintEvent(self, event):
        """Paint timeline."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), self.colors['background'])

        # Time ruler
        self._draw_time_ruler(painter)

        # IN/OUT zone
        if self.in_point is not None and self.out_point is not None:
            x1 = self._frame_to_pixel(self.in_point)
            x2 = self._frame_to_pixel(self.out_point)
            painter.fillRect(x1, 60, x2 - x1, self.height() - 60, QColor(255, 255, 0, 30))

        # Segments (larger with thumbnails)
        for i, segment in enumerate(self.segments):
            self._draw_segment(painter, segment, i)

        # Current segment in progress
        if self.current_segment:
            self._draw_segment(painter, self.current_segment, -1, in_progress=True)

        # IN marker
        if self.in_point is not None:
            x = self._frame_to_pixel(self.in_point)
            painter.setPen(QPen(self.colors['in_marker'], 3))
            painter.drawLine(x, 60, x, self.height())
            # Label
            painter.setPen(self.colors['in_marker'])
            font = painter.font()
            font.setBold(True)
            font.setPointSize(13)  # Augmenté pour meilleure lisibilité
            painter.setFont(font)
            painter.drawText(x + 5, 75, "IN")

        # OUT marker
        if self.out_point is not None:
            x = self._frame_to_pixel(self.out_point)
            painter.setPen(QPen(self.colors['out_marker'], 3))
            painter.drawLine(x, 60, x, self.height())
            # Label
            painter.setPen(self.colors['out_marker'])
            font = painter.font()
            font.setBold(True)
            font.setPointSize(13)  # Augmenté pour meilleure lisibilité
            painter.setFont(font)
            painter.drawText(x + 5, 75, "OUT")

        # Cursor (playhead)
        cursor_x = self._frame_to_pixel(self.current_frame)
        painter.setPen(QPen(self.colors['cursor'], 2))
        painter.drawLine(cursor_x, 50, cursor_x, self.height())

        # Playhead triangle
        painter.setBrush(self.colors['cursor'])
        triangle = QPolygon([
            QPoint(cursor_x - 5, 50),
            QPoint(cursor_x + 5, 50),
            QPoint(cursor_x, 60)
        ])
        painter.drawPolygon(triangle)

    def _draw_time_ruler(self, painter: QPainter):
        """Draw time ruler at top.

        Args:
            painter: QPainter instance
        """
        painter.setPen(QColor(100, 100, 100))  # Gris plus foncé pour fond clair
        painter.drawLine(0, 50, self.width(), 50)

        # Time markers every 5 seconds (assuming 30fps)
        if self.total_frames > 0:
            fps = 30.0
            interval_frames = int(5 * fps)  # 5 seconds

            for frame in range(0, self.total_frames, interval_frames):
                x = self._frame_to_pixel(frame)
                if 0 <= x <= self.width():
                    # Tick
                    painter.drawLine(x, 45, x, 55)

                    # Time label
                    seconds = frame / fps
                    time_str = self._format_time(seconds)
                    # Use larger font for better readability
                    font = painter.font()
                    font.setPointSize(11)
                    painter.setFont(font)
                    painter.drawText(x + 2, 43, time_str)

    def _draw_segment(self, painter: QPainter, segment, index: int, in_progress: bool = False):
        """Draw segment with thumbnail.

        Args:
            painter: QPainter
            segment: VideoSegment
            index: Segment index (-1 for in-progress)
            in_progress: Is segment being created
        """
        x1 = self._frame_to_pixel(segment.start_frame)
        x2 = self._frame_to_pixel(segment.end_frame if segment.end_frame else self.current_frame)
        width = max(x2 - x1, 10)

        y = 65
        height = self.height() - 70

        # Color
        if index == self.selected_segment_index:
            color = self.colors['segment_selected']
        else:
            color = self.colors['segment']

        if in_progress:
            color.setAlpha(150)

        # Segment rectangle
        painter.fillRect(int(x1), y, int(width), height, color)

        # Border
        painter.setPen(QPen(self.colors['segment_border'], 2))
        painter.drawRect(int(x1), y, int(width), height)

        # Segment label
        if width > 50:
            painter.setPen(QColor(255, 255, 255))  # Texte blanc pour meilleure visibilité sur segment bleu
            font = painter.font()
            font.setBold(True)
            font.setPointSize(12)  # Augmenté de 10 à 12 pour meilleure lisibilité
            painter.setFont(font)

            text = f"Seg {index + 1}" if index >= 0 else "En cours..."
            painter.drawText(int(x1) + 5, y + 20, text)

            # Markers (transition, text)
            marker_y = y + height - 15
            if hasattr(segment, 'has_transition_out') and segment.has_transition_out():
                painter.drawText(int(x1) + 5, marker_y, "⚡")

            if hasattr(segment, 'has_text_overlays') and segment.has_text_overlays():
                painter.drawText(int(x1) + 25, marker_y, "📝")
