"""Enhanced preview widget for Video Editor."""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QSlider, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.PreviewWidget')


class PreviewWidget(QWidget):
    """Enhanced video preview widget with integrated controls."""

    # Signals
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    prev_frame_clicked = pyqtSignal()
    next_frame_clicked = pyqtSignal()
    speed_changed = pyqtSignal(float)
    volume_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        """Initialize preview widget."""
        super().__init__(parent)
        self.is_playing = False
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Title
        title = QLabel("📹 Prévisualisation")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # Video preview area
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(720, 405)  # 16:9 aspect ratio
        self.preview_label.setMaximumSize(1280, 720)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: black;
                border: 2px solid #555;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.preview_label)

        # Timecode display
        self.timecode_label = QLabel("00:00:00 / 00:00:00")
        self.timecode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timecode_label.setStyleSheet("font-family: 'Courier New'; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.timecode_label)

        # Playback controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        # Previous frame
        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setToolTip("Frame précédente (Left)")
        self.prev_btn.setMaximumWidth(40)
        self.prev_btn.clicked.connect(self.prev_frame_clicked.emit)
        controls_layout.addWidget(self.prev_btn)

        # Play/Pause
        self.play_pause_btn = QPushButton("▶️")
        self.play_pause_btn.setToolTip("Lecture/Pause (Space)")
        self.play_pause_btn.setMaximumWidth(60)
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                padding: 8px;
                background-color: #28a745;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.play_pause_btn.clicked.connect(self._on_play_pause_clicked)
        controls_layout.addWidget(self.play_pause_btn)

        # Next frame
        self.next_btn = QPushButton("⏭")
        self.next_btn.setToolTip("Frame suivante (Right)")
        self.next_btn.setMaximumWidth(40)
        self.next_btn.clicked.connect(self.next_frame_clicked.emit)
        controls_layout.addWidget(self.next_btn)

        controls_layout.addStretch()

        # Speed control
        controls_layout.addWidget(QLabel("Vitesse:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1x", "1.5x", "2x"])
        self.speed_combo.setCurrentIndex(2)  # 1x by default
        self.speed_combo.setMaximumWidth(80)
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        controls_layout.addWidget(self.speed_combo)

        controls_layout.addStretch()

        # Volume control
        controls_layout.addWidget(QLabel("🔊"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)
        controls_layout.addWidget(self.volume_slider)

        self.volume_label = QLabel("70%")
        self.volume_label.setMinimumWidth(40)
        self.volume_slider.valueChanged.connect(lambda v: self.volume_label.setText(f"{v}%"))
        controls_layout.addWidget(self.volume_label)

        layout.addLayout(controls_layout)

    def set_preview_image(self, pixmap: QPixmap):
        """Set preview image."""
        if pixmap:
            scaled = pixmap.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled)

    def set_timecode(self, current_time: str, total_time: str):
        """Set timecode display."""
        self.timecode_label.setText(f"{current_time} / {total_time}")

    def set_playing(self, is_playing: bool):
        """Update play/pause button state."""
        self.is_playing = is_playing
        if is_playing:
            self.play_pause_btn.setText("⏸️")
            self.play_pause_btn.setStyleSheet("""
                QPushButton {
                    font-size: 16px;
                    padding: 8px;
                    background-color: #ffc107;
                    color: white;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
        else:
            self.play_pause_btn.setText("▶️")
            self.play_pause_btn.setStyleSheet("""
                QPushButton {
                    font-size: 16px;
                    padding: 8px;
                    background-color: #28a745;
                    color: white;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)

    def _on_play_pause_clicked(self):
        """Handle play/pause button click."""
        if self.is_playing:
            self.pause_clicked.emit()
        else:
            self.play_clicked.emit()

    def _on_speed_changed(self, index):
        """Handle speed change."""
        speeds = [0.25, 0.5, 1.0, 1.5, 2.0]
        self.speed_changed.emit(speeds[index])

    def set_enabled_state(self, enabled: bool):
        """Enable/disable controls."""
        self.play_pause_btn.setEnabled(enabled)
        self.prev_btn.setEnabled(enabled)
        self.next_btn.setEnabled(enabled)
        self.speed_combo.setEnabled(enabled)
