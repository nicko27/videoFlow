"""
Dialogue de comparaison pour sous-séquences vidéo.

Affiche deux vidéos avec leurs timecodes et permet de naviguer
dans la partie identique détectée.
"""

import os
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QProgressBar, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

try:
    from .video_preview_widget import VideoPreviewWidget
    from .design_system import Colors, Spacing, Typography, Styles
    from .keyboard_shortcuts import KeyboardShortcuts
except ImportError:
    from video_preview_widget import VideoPreviewWidget
    from design_system import Colors, Spacing, Typography, Styles
    from keyboard_shortcuts import KeyboardShortcuts

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.SubsequenceComparisonDialog')


class SubsequenceComparisonDialog(QDialog):
    """
    Dialogue spécialisé pour comparer des sous-séquences vidéo.

    Affiche la vidéo courte et la section correspondante de la vidéo longue,
    avec navigation synchronisée dans la partie identique.
    """

    def __init__(self, short_video: str, long_video: str, match_info: dict, parent=None):
        """
        Initialize the subsequence comparison dialog.

        Args:
            short_video: Path to the shorter video (extracted)
            long_video: Path to the longer video (source)
            match_info: Dictionary with 'match_ratio', 'start_frame_idx', 'confidence'
            parent: Parent widget
        """
        super().__init__(parent)
        self.short_video = short_video
        self.long_video = long_video
        self.match_info = match_info
        self.result = None

        # Video properties
        self.short_fps = 0
        self.long_fps = 0
        self.short_total_frames = 0
        self.long_total_frames = 0
        self.start_frame_idx = match_info.get('start_frame_idx', 0)

        # Load video properties
        self._load_video_properties()

        self.setWindowTitle(f"Subsequence Comparison - Match: {match_info.get('match_ratio', 0)*100:.1f}%")
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.setModal(True)

        self.setup_ui()

        # Show initial synchronized position
        QTimer.singleShot(500, self.show_initial_position)

    def _load_video_properties(self):
        """Load FPS and frame count for both videos."""
        try:
            # Short video
            cap_short = cv2.VideoCapture(self.short_video)
            self.short_fps = cap_short.get(cv2.CAP_PROP_FPS) or 25.0
            self.short_total_frames = int(cap_short.get(cv2.CAP_PROP_FRAME_COUNT))
            cap_short.release()

            # Long video
            cap_long = cv2.VideoCapture(self.long_video)
            self.long_fps = cap_long.get(cv2.CAP_PROP_FPS) or 25.0
            self.long_total_frames = int(cap_long.get(cv2.CAP_PROP_FRAME_COUNT))
            cap_long.release()

        except Exception as e:
            logger.error(f"Error loading video properties: {e}")
            self.short_fps = self.long_fps = 25.0
            self.short_total_frames = self.long_total_frames = 1000

    def setup_ui(self):
        """Configure the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Match info header
        info_frame = self.create_match_info_header()
        layout.addWidget(info_frame)

        # Video comparison area
        comparison_layout = QHBoxLayout()
        comparison_layout.setSpacing(30)

        # Short video (left)
        left_frame = self.create_video_frame(
            "Short Video (Extracted)",
            self.short_video,
            "#2196F3"
        )
        self.short_video_widget = left_frame[1]
        comparison_layout.addWidget(left_frame[0])

        # Long video (right)
        right_frame = self.create_video_frame(
            "Long Video (Matched Section)",
            self.long_video,
            "#FF9800"
        )
        self.long_video_widget = right_frame[1]
        comparison_layout.addWidget(right_frame[0])

        layout.addLayout(comparison_layout)

        # Navigation controls
        nav_controls = self.create_navigation_controls()
        layout.addWidget(nav_controls)

        # Action buttons
        action_buttons = self.create_action_buttons()
        layout.addWidget(action_buttons)

    def create_match_info_header(self) -> QFrame:
        """Create header with match information."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #E3F2FD;
                border: 2px solid #2196F3;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        layout = QGridLayout(frame)
        layout.setSpacing(10)

        # Title
        title = QLabel("🎬 Subsequence Detected")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #1976D2; background: transparent; border: none;")
        layout.addWidget(title, 0, 0, 1, 3)

        # Match ratio
        match_label = QLabel(f"Match: {self.match_info.get('match_ratio', 0)*100:.1f}%")
        match_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        match_label.setStyleSheet("color: #4CAF50; background: transparent; border: none;")
        layout.addWidget(match_label, 1, 0)

        # Start position in long video
        start_time = self.start_frame_idx / self.long_fps if self.long_fps > 0 else 0
        position_label = QLabel(f"Starts at: {self._format_time(start_time)} in long video")
        position_label.setStyleSheet("color: #666; background: transparent; border: none;")
        layout.addWidget(position_label, 1, 1)

        # Confidence
        confidence_label = QLabel(f"Confidence: {self.match_info.get('confidence', 0)*100:.1f}%")
        confidence_label.setStyleSheet("color: #666; background: transparent; border: none;")
        layout.addWidget(confidence_label, 1, 2)

        return frame

    def create_video_frame(self, title: str, video_path: str, color: str) -> tuple:
        """Create a video display frame with title and timecode."""
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 10px;
                padding: 15px;
            }}
        """)

        layout = QVBoxLayout(container)
        layout.setSpacing(10)

        # Header with title and timecode
        header_layout = QHBoxLayout()

        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Timecode label (will be updated)
        timecode_label = QLabel("00:00:00")
        timecode_label.setFont(QFont("Courier", 11, QFont.Weight.Bold))
        timecode_label.setStyleSheet("color: #333; background: transparent; border: none;")
        header_layout.addWidget(timecode_label)

        layout.addLayout(header_layout)

        # Video preview
        video_widget = VideoPreviewWidget(video_path)
        layout.addWidget(video_widget)

        # File info
        filename = os.path.basename(video_path)
        info_label = QLabel(filename)
        info_label.setStyleSheet("color: #666; font-size: 10px; background: transparent; border: none;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Store timecode label reference
        if "Short" in title:
            self.short_timecode_label = timecode_label
        else:
            self.long_timecode_label = timecode_label

        return container, video_widget

    def create_navigation_controls(self) -> QFrame:
        """Create navigation slider and controls."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-radius: 8px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(10)

        # Label
        label = QLabel("🔍 Navigate in matched section:")
        label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(label)

        # Slider for navigation within matched section
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setMinimum(0)
        self.position_slider.setMaximum(100)
        self.position_slider.setValue(0)
        self.position_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.position_slider.setTickInterval(10)
        self.position_slider.valueChanged.connect(self.on_slider_changed)
        layout.addWidget(self.position_slider)

        # Position info
        self.position_info_label = QLabel("Position: 0%")
        self.position_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.position_info_label)

        return frame

    def create_action_buttons(self) -> QFrame:
        """Create action buttons."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        layout = QHBoxLayout(frame)
        layout.setSpacing(15)

        # Keep short button
        keep_short_btn = QPushButton("✅ Keep Short (Delete Long)")
        keep_short_btn.setMinimumHeight(45)
        keep_short_btn.setStyleSheet(self._get_button_style("#4CAF50", "#45A049"))
        keep_short_btn.clicked.connect(lambda: self.set_result("keep_short"))

        # Keep long button
        keep_long_btn = QPushButton("✅ Keep Long (Delete Short)")
        keep_long_btn.setMinimumHeight(45)
        keep_long_btn.setStyleSheet(self._get_button_style("#2196F3", "#1976D2"))
        keep_long_btn.clicked.connect(lambda: self.set_result("keep_long"))

        # Keep both button
        keep_both_btn = QPushButton("📂 Keep Both")
        keep_both_btn.setMinimumHeight(45)
        keep_both_btn.setStyleSheet(self._get_button_style("#FF9800", "#F57C00"))
        keep_both_btn.clicked.connect(lambda: self.set_result("keep_both"))

        # Skip button
        skip_btn = QPushButton("⏭️ Skip")
        skip_btn.setMinimumHeight(45)
        skip_btn.setStyleSheet(self._get_button_style("#9E9E9E", "#757575"))
        skip_btn.clicked.connect(lambda: self.set_result("skip"))

        layout.addWidget(keep_short_btn)
        layout.addWidget(keep_long_btn)
        layout.addWidget(keep_both_btn)
        layout.addWidget(skip_btn)

        return frame

    def show_initial_position(self):
        """Show initial synchronized position (start of match)."""
        self.on_slider_changed(0)

    def on_slider_changed(self, value: int):
        """Handle slider position change - synchronize both videos."""
        try:
            # Calculate position in short video (0-100%)
            short_position = value / 100.0
            short_frame = int(short_position * self.short_total_frames)

            # Calculate corresponding frame in long video
            # The match starts at start_frame_idx in long video
            long_frame = self.start_frame_idx + short_frame

            # Update videos
            self.short_video_widget.seek_to_position(short_position)

            # Calculate position in long video (as percentage)
            long_position = long_frame / self.long_total_frames if self.long_total_frames > 0 else 0
            self.long_video_widget.seek_to_position(long_position)

            # Update timecodes
            short_time = short_frame / self.short_fps if self.short_fps > 0 else 0
            long_time = long_frame / self.long_fps if self.long_fps > 0 else 0

            self.short_timecode_label.setText(self._format_time(short_time))
            self.long_timecode_label.setText(self._format_time(long_time))

            # Update position info
            self.position_info_label.setText(f"Position: {value}% in matched section")

        except Exception as e:
            logger.error(f"Error updating slider position: {e}")

    def _format_time(self, seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _get_button_style(self, bg_color: str, hover_color: str) -> str:
        """Get button stylesheet."""
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {hover_color};
                padding-top: 10px;
                padding-bottom: 6px;
            }}
        """

    def set_result(self, action: str):
        """Set the user's decision and close dialog."""
        self.result = action
        self.accept()

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        key = event.key()

        # Action shortcuts
        if key == KeyboardShortcuts.COMPARISON_KEEP_LEFT:
            self.set_result("keep_short")
        elif key == KeyboardShortcuts.COMPARISON_KEEP_RIGHT:
            self.set_result("keep_long")
        elif key == KeyboardShortcuts.COMPARISON_KEEP_BOTH:
            self.set_result("keep_both")
        elif key == KeyboardShortcuts.COMPARISON_QUIT:
            self.set_result("skip")

        # Navigation shortcuts - position in short video
        elif key == KeyboardShortcuts.NAV_START:
            self.position_slider.setValue(0)
        elif key == KeyboardShortcuts.NAV_END:
            self.position_slider.setValue(100)
        elif key == KeyboardShortcuts.NAV_QUARTER:
            self.position_slider.setValue(25)
        elif key == KeyboardShortcuts.NAV_HALF:
            self.position_slider.setValue(50)
        elif key == KeyboardShortcuts.NAV_THREE_QUARTERS:
            self.position_slider.setValue(75)
        elif key == KeyboardShortcuts.NAV_PREV:
            # Move back 5%
            new_value = max(0, self.position_slider.value() - 5)
            self.position_slider.setValue(new_value)
        elif key == KeyboardShortcuts.NAV_NEXT:
            # Move forward 5%
            new_value = min(100, self.position_slider.value() + 5)
            self.position_slider.setValue(new_value)
        else:
            super().keyPressEvent(event)
