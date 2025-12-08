"""Inspector Panel - Simple segment properties editor.

Provides easy access to segment properties and quick actions.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QGroupBox,
    QLineEdit, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from src.core.i18n import t


class InspectorPanel(QWidget):
    """Simple inspector for segment properties.

    Shows selected segment info and provides quick actions.
    """

    transition_clicked = pyqtSignal()
    text_overlay_clicked = pyqtSignal()
    audio_clicked = pyqtSignal()
    delete_clicked = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize inspector panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_segment = None
        self.fps = 30.0  # Default FPS, will be updated when video is loaded
        self.setup_ui()

    def setup_ui(self):
        """Set up simple and clear UI."""
        # Main scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Content widget
        content = QWidget()
        scroll.setWidget(content)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        # Content layout
        layout = QVBoxLayout(content)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Header
        header = QLabel(t("video_editor.inspector.properties", "⚙️ Properties"))
        header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #000;
                padding: 5px;
                background-color: transparent;
            }
        """)
        layout.addWidget(header)

        # Segment info group
        self.info_group = QGroupBox(t("video_editor.inspector.selected_segment", "Selected Segment"))
        self.info_group.setStyleSheet("""
            QGroupBox {
                color: #000;
                background-color: #fff;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        info_layout = QVBoxLayout(self.info_group)
        info_layout.setSpacing(8)

        # Segment name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel(t("video_editor.inspector.name", "Name:")))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(t("video_editor.inspector.unnamed_segment", "Unnamed segment"))
        self.name_edit.setStyleSheet("padding: 5px; background-color: #fff; border: 1px solid #ccc; color: #000;")
        name_layout.addWidget(self.name_edit, 1)
        info_layout.addLayout(name_layout)

        # Start time
        self.start_label = QLabel(t("video_editor.inspector.start", "⏱ Start: --:--:--"))
        self.start_label.setStyleSheet("color: #333; padding: 5px; background-color: transparent;")
        info_layout.addWidget(self.start_label)

        # End time
        self.end_label = QLabel(t("video_editor.inspector.end", "⏱ End: --:--:--"))
        self.end_label.setStyleSheet("color: #333; padding: 5px; background-color: transparent;")
        info_layout.addWidget(self.end_label)

        # Duration
        self.duration_label = QLabel(t("video_editor.inspector.duration", "⏳ Duration: --:--:--"))
        self.duration_label.setStyleSheet("color: #0066cc; font-weight: bold; padding: 5px; background-color: transparent;")
        info_layout.addWidget(self.duration_label)

        layout.addWidget(self.info_group)

        # Quick Actions group
        actions_group = QGroupBox(t("video_editor.inspector.quick_actions", "Quick Actions"))
        actions_group.setStyleSheet("""
            QGroupBox {
                color: #000;
                background-color: #fff;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(5)

        # Transition button
        transition_btn = QPushButton(t("video_editor.inspector.add_transition", "⚡ Add Transition"))
        transition_btn.setMinimumHeight(40)
        transition_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c63ff;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #5a52d5;
            }
            QPushButton:disabled {
                background-color: #444;
                color: #888;
            }
        """)
        transition_btn.clicked.connect(self.transition_clicked.emit)
        actions_layout.addWidget(transition_btn)
        self.transition_btn = transition_btn

        # Text overlay button
        text_btn = QPushButton(t("video_editor.inspector.add_text", "📝 Add Text"))
        text_btn.setMinimumHeight(40)
        text_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #444;
                color: #888;
            }
        """)
        text_btn.clicked.connect(self.text_overlay_clicked.emit)
        actions_layout.addWidget(text_btn)
        self.text_btn = text_btn

        # Audio button
        audio_btn = QPushButton(t("video_editor.inspector.audio_settings", "🎵 Audio Settings"))
        audio_btn.setMinimumHeight(40)
        audio_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
            QPushButton:disabled {
                background-color: #444;
                color: #888;
            }
        """)
        audio_btn.clicked.connect(self.audio_clicked.emit)
        actions_layout.addWidget(audio_btn)
        self.audio_btn = audio_btn

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #ccc; margin: 5px 0;")
        actions_layout.addWidget(separator)

        # Delete button
        delete_btn = QPushButton(t("video_editor.inspector.delete_segment", "🗑 Delete Segment"))
        delete_btn.setMinimumHeight(40)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ff4444;
                border: 1px solid #ff4444;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #ff4444;
                color: white;
            }
            QPushButton:disabled {
                background-color: transparent;
                color: #666;
                border-color: #666;
            }
        """)
        delete_btn.clicked.connect(self.delete_clicked.emit)
        actions_layout.addWidget(delete_btn)
        self.delete_btn = delete_btn

        layout.addWidget(actions_group)

        # Help text
        help_label = QLabel(t("video_editor.inspector.help", "💡 Select a segment\nto view its properties"))
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_label.setWordWrap(True)
        help_label.setStyleSheet("""
            QLabel {
                color: #666;
                background-color: #f8f8f8;
                font-size: 11px;
                padding: 20px;
                border: 1px dashed #ccc;
                border-radius: 5px;
                margin-top: 10px;
            }
        """)
        layout.addWidget(help_label)
        self.help_label = help_label

        layout.addStretch()

        # Initially disable all actions
        self.set_segment(None)

    def set_segment(self, segment):
        """Set current segment and update UI.

        Args:
            segment: VideoSegment or None
        """
        self.current_segment = segment

        if segment is None:
            # No segment selected
            self.info_group.setEnabled(False)
            self.transition_btn.setEnabled(False)
            self.text_btn.setEnabled(False)
            self.audio_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.help_label.show()

            # Clear fields
            self.name_edit.clear()
            self.start_label.setText(t("video_editor.inspector.start", "⏱ Start: --:--:--"))
            self.end_label.setText(t("video_editor.inspector.end", "⏱ End: --:--:--"))
            self.duration_label.setText(t("video_editor.inspector.duration", "⏳ Duration: --:--:--"))

        else:
            # Segment selected
            self.info_group.setEnabled(True)
            self.transition_btn.setEnabled(True)
            self.text_btn.setEnabled(True)
            self.audio_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
            self.help_label.hide()

            # Update fields
            self.name_edit.setText(segment.name if hasattr(segment, 'name') and segment.name else f"Segment")

            # Format times (using stored fps)
            if hasattr(segment, 'start_frame') and segment.start_frame is not None:
                start_time = self._frames_to_timecode(segment.start_frame, self.fps)
                self.start_label.setText(t("video_editor.inspector.start_value", "⏱ Start: {time}", time=start_time))

                if hasattr(segment, 'end_frame') and segment.end_frame is not None:
                    end_time = self._frames_to_timecode(segment.end_frame, self.fps)
                    self.end_label.setText(t("video_editor.inspector.end_value", "⏱ End: {time}", time=end_time))

                    duration_frames = segment.end_frame - segment.start_frame
                    duration_time = self._frames_to_timecode(duration_frames, self.fps)
                    self.duration_label.setText(t("video_editor.inspector.duration_value", "⏳ Duration: {time}", time=duration_time))
                else:
                    self.end_label.setText(t("video_editor.inspector.end_unknown", "⏱ End: -"))
                    self.duration_label.setText(t("video_editor.inspector.duration_unknown", "⏳ Duration: -"))
            else:
                self.start_label.setText(t("video_editor.inspector.start_unknown", "⏱ Start: -"))
                self.end_label.setText(t("video_editor.inspector.end_unknown", "⏱ End: -"))
                self.duration_label.setText(t("video_editor.inspector.duration_unknown", "⏳ Duration: -"))

    def _frames_to_timecode(self, frames: int, fps: float) -> str:
        """Convert frames to timecode.

        Args:
            frames: Frame number
            fps: Frames per second

        Returns:
            Timecode string (HH:MM:SS)
        """
        total_seconds = frames / fps
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def get_segment_name(self) -> str:
        """Get current segment name from editor.

        Returns:
            Segment name
        """
        return self.name_edit.text()
