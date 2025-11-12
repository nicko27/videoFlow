"""Multi-track timeline widget for Video Editor.

Provides visual timeline with multiple tracks for complex video composition.
"""

from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from typing import Optional, List, Tuple
from .multi_track_data import (
    Track, TrackSegment, TrackType, MultiTrackProject
)


class TrackHeaderWidget(QFrame):
    """Header widget for a single track.

    Shows track name, mute/solo buttons, and controls.
    """

    track_enabled_changed = pyqtSignal(str, bool)  # track_id, enabled
    track_muted_changed = pyqtSignal(str, bool)  # track_id, muted
    track_solo_changed = pyqtSignal(str, bool)  # track_id, solo
    track_delete_clicked = pyqtSignal(str)  # track_id

    def __init__(self, track: Track, parent=None):
        """Initialize track header.

        Args:
            track: Track instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.track = track
        self.setup_ui()

    def setup_ui(self):
        """Set up header UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            TrackHeaderWidget {{
                background-color: #2a2a2a;
                border-right: 1px solid #444;
            }}
        """)
        self.setFixedWidth(150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # Track name
        name_label = QLabel(self.track.name)
        name_label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(name_label)

        # Track type
        type_label = QLabel(f"({self.track.track_type.value})")
        type_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(type_label)

        # Buttons row
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(2)

        # Mute button
        self.mute_btn = QPushButton("M")
        self.mute_btn.setCheckable(True)
        self.mute_btn.setChecked(self.track.muted)
        self.mute_btn.setFixedSize(25, 20)
        self.mute_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                border: none;
                font-size: 10px;
            }
            QPushButton:checked {
                background-color: #ff4444;
            }
        """)
        self.mute_btn.clicked.connect(
            lambda: self.track_muted_changed.emit(self.track.track_id, self.mute_btn.isChecked())
        )
        buttons_layout.addWidget(self.mute_btn)

        # Solo button
        self.solo_btn = QPushButton("S")
        self.solo_btn.setCheckable(True)
        self.solo_btn.setChecked(self.track.solo)
        self.solo_btn.setFixedSize(25, 20)
        self.solo_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                border: none;
                font-size: 10px;
            }
            QPushButton:checked {
                background-color: #ffc107;
                color: black;
            }
        """)
        self.solo_btn.clicked.connect(
            lambda: self.track_solo_changed.emit(self.track.track_id, self.solo_btn.isChecked())
        )
        buttons_layout.addWidget(self.solo_btn)

        # Delete button
        delete_btn = QPushButton("🗑")
        delete_btn.setFixedSize(25, 20)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                border: none;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #ff4444;
            }
        """)
        delete_btn.clicked.connect(
            lambda: self.track_delete_clicked.emit(self.track.track_id)
        )
        buttons_layout.addWidget(delete_btn)

        layout.addLayout(buttons_layout)
        layout.addStretch()


class TrackWidget(QWidget):
    """Widget displaying a single track with its segments."""

    segment_clicked = pyqtSignal(str, str)  # track_id, segment_id
    segment_moved = pyqtSignal(str, str, int)  # track_id, segment_id, new_frame

    def __init__(self, track: Track, total_frames: int, parent=None):
        """Initialize track widget.

        Args:
            track: Track instance
            total_frames: Total timeline frames
            parent: Parent widget
        """
        super().__init__(parent)
        self.track = track
        self.total_frames = total_frames
        self.dragging_segment = None
        self.drag_offset = 0

        self.setMinimumHeight(track.height)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        """Draw track and segments."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        bg_color = QColor("#3a3a3a") if self.track.enabled else QColor("#2a2a2a")
        painter.fillRect(self.rect(), bg_color)

        # Grid lines
        painter.setPen(QPen(QColor("#444"), 1, Qt.PenStyle.DotLine))
        for i in range(0, self.width(), 50):
            painter.drawLine(i, 0, i, self.height())

        # Segments
        for segment in self.track.segments:
            self._draw_segment(painter, segment)

    def _draw_segment(self, painter: QPainter, segment: TrackSegment):
        """Draw a segment.

        Args:
            painter: QPainter instance
            segment: Segment to draw
        """
        x1 = self._frame_to_pixel(segment.start_frame)
        x2 = self._frame_to_pixel(segment.end_frame)
        width = max(x2 - x1, 5)  # Minimum 5 pixels

        # Segment color
        color = QColor(self.track.color)
        if not segment.enabled:
            color.setAlpha(100)

        # Draw segment rectangle
        painter.fillRect(x1, 5, width, self.height() - 10, color)

        # Border
        border_color = QColor(self.track.color).lighter(150)
        painter.setPen(QPen(border_color, 2))
        painter.drawRect(x1, 5, width, self.height() - 10)

        # Segment info text
        if width > 40:
            painter.setPen(QColor("white"))
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            text = f"Seg {segment.segment_id[:4]}"
            painter.drawText(x1 + 5, 20, text)

    def _frame_to_pixel(self, frame: int) -> int:
        """Convert frame to pixel position.

        Args:
            frame: Frame number

        Returns:
            Pixel position
        """
        if self.total_frames == 0:
            return 0
        return int((frame / self.total_frames) * self.width())

    def _pixel_to_frame(self, x: int) -> int:
        """Convert pixel position to frame.

        Args:
            x: Pixel position

        Returns:
            Frame number
        """
        if self.total_frames == 0:
            return 0
        return int((x / self.width()) * self.total_frames)

    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            frame = self._pixel_to_frame(event.position().x())
            segment = self.track.get_segment_at_frame(frame)
            if segment:
                self.segment_clicked.emit(self.track.track_id, segment.segment_id)
                self.dragging_segment = segment
                self.drag_offset = frame - segment.start_frame

    def mouseMoveEvent(self, event):
        """Handle mouse move (drag)."""
        if self.dragging_segment and event.buttons() & Qt.MouseButton.LeftButton:
            frame = self._pixel_to_frame(event.position().x())
            new_start = frame - self.drag_offset
            # Emit move signal
            self.segment_moved.emit(
                self.track.track_id,
                self.dragging_segment.segment_id,
                new_start
            )

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_segment = None


class MultiTrackTimeline(QWidget):
    """Multi-track timeline widget.

    Provides timeline with multiple tracks for complex compositions.
    """

    position_changed = pyqtSignal(int)  # current_frame
    segment_clicked = pyqtSignal(str, str)  # track_id, segment_id
    track_added = pyqtSignal(str)  # track_id
    track_removed = pyqtSignal(str)  # track_id

    def __init__(self, parent=None):
        """Initialize multi-track timeline.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.project = MultiTrackProject()
        self.current_frame = 0
        self.zoom_level = 1.0

        self.track_widgets = {}  # track_id -> TrackWidget
        self.track_headers = {}  # track_id -> TrackHeaderWidget

        self.setup_ui()

    def setup_ui(self):
        """Set up timeline UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Top toolbar
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)

        # Timeline area
        timeline_layout = QHBoxLayout()
        timeline_layout.setSpacing(0)

        # Track headers (left side)
        self.headers_layout = QVBoxLayout()
        self.headers_layout.setSpacing(0)
        headers_container = QWidget()
        headers_container.setLayout(self.headers_layout)

        # Tracks area (right side - scrollable)
        self.tracks_layout = QVBoxLayout()
        self.tracks_layout.setSpacing(0)
        self.tracks_layout.setContentsMargins(0, 0, 0, 0)

        tracks_container = QWidget()
        tracks_container.setLayout(self.tracks_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidget(tracks_container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        timeline_layout.addWidget(headers_container)
        timeline_layout.addWidget(scroll_area, 1)

        main_layout.addLayout(timeline_layout, 1)

    def _create_toolbar(self) -> QWidget:
        """Create timeline toolbar.

        Returns:
            Toolbar widget
        """
        toolbar = QWidget()
        toolbar.setStyleSheet("background-color: #2a2a2a; padding: 5px;")

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 2, 5, 2)

        # Add track button
        add_video_btn = QPushButton("➕ Video Track")
        add_video_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        add_video_btn.clicked.connect(lambda: self.add_track("Video Track", TrackType.VIDEO))
        layout.addWidget(add_video_btn)

        # Add audio track button
        add_audio_btn = QPushButton("➕ Audio Track")
        add_audio_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        add_audio_btn.clicked.connect(lambda: self.add_track("Audio Track", TrackType.AUDIO))
        layout.addWidget(add_audio_btn)

        # Add overlay track button
        add_overlay_btn = QPushButton("➕ Overlay Track")
        add_overlay_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        add_overlay_btn.clicked.connect(lambda: self.add_track("Overlay Track", TrackType.OVERLAY))
        layout.addWidget(add_overlay_btn)

        layout.addStretch()

        # Zoom controls
        zoom_label = QLabel("Zoom:")
        zoom_label.setStyleSheet("color: white;")
        layout.addWidget(zoom_label)

        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setFixedSize(25, 25)
        zoom_out_btn.clicked.connect(self.zoom_out)
        layout.addWidget(zoom_out_btn)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(25, 25)
        zoom_in_btn.clicked.connect(self.zoom_in)
        layout.addWidget(zoom_in_btn)

        return toolbar

    def add_track(self, name: str, track_type: TrackType):
        """Add new track.

        Args:
            name: Track name
            track_type: Type of track
        """
        track = self.project.add_track(name, track_type)

        # Create header widget
        header = TrackHeaderWidget(track)
        header.track_muted_changed.connect(self._on_track_muted)
        header.track_solo_changed.connect(self._on_track_solo)
        header.track_delete_clicked.connect(self.remove_track)
        self.headers_layout.addWidget(header)
        self.track_headers[track.track_id] = header

        # Create track widget
        track_widget = TrackWidget(track, self.project.total_frames)
        track_widget.segment_clicked.connect(self.segment_clicked.emit)
        self.tracks_layout.addWidget(track_widget)
        self.track_widgets[track.track_id] = track_widget

        self.track_added.emit(track.track_id)

    def remove_track(self, track_id: str):
        """Remove track.

        Args:
            track_id: Track ID to remove
        """
        if track_id in self.track_widgets:
            # Remove widgets
            self.track_widgets[track_id].deleteLater()
            del self.track_widgets[track_id]

            self.track_headers[track_id].deleteLater()
            del self.track_headers[track_id]

            # Remove from project
            self.project.remove_track(track_id)

            self.track_removed.emit(track_id)

    def _on_track_muted(self, track_id: str, muted: bool):
        """Handle track mute change."""
        track = self.project.get_track_by_id(track_id)
        if track:
            track.muted = muted

    def _on_track_solo(self, track_id: str, solo: bool):
        """Handle track solo change."""
        track = self.project.get_track_by_id(track_id)
        if track:
            track.solo = solo

    def set_project(self, project: MultiTrackProject):
        """Set multi-track project.

        Args:
            project: Project to load
        """
        # Clear existing tracks
        for track_id in list(self.track_widgets.keys()):
            self.remove_track(track_id)

        self.project = project

        # Create widgets for each track
        for track in project.tracks:
            self.add_track(track.name, track.track_type)

    def zoom_in(self):
        """Zoom in timeline."""
        self.zoom_level = min(self.zoom_level * 1.2, 10.0)
        self.update()

    def zoom_out(self):
        """Zoom out timeline."""
        self.zoom_level = max(self.zoom_level / 1.2, 0.1)
        self.update()

    def set_total_frames(self, frames: int):
        """Set total timeline frames.

        Args:
            frames: Total frames
        """
        self.project.total_frames = frames
        for widget in self.track_widgets.values():
            widget.total_frames = frames
            widget.update()
