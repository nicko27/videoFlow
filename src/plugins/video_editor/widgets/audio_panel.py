"""Audio extraction panel widget for Video Editor."""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QSpinBox, QComboBox, QGroupBox,
                            QCheckBox, QRadioButton, QButtonGroup)
from PyQt6.QtCore import pyqtSignal
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.AudioPanel')


class AudioPanel(QWidget):
    """Panel for audio extraction features."""

    # Signals
    extract_full_audio_clicked = pyqtSignal(str, int, bool)  # format, bitrate, normalize
    extract_segment_audio_clicked = pyqtSignal(int, str, int, bool)  # segment_index, format, bitrate, normalize
    extract_all_segments_audio_clicked = pyqtSignal(str, int, bool)  # format, bitrate, normalize

    def __init__(self, parent=None):
        """Initialize audio panel."""
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Title
        title = QLabel("🎵 Extraction Audio")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # Extraction mode
        mode_group = QGroupBox("Mode d'extraction")
        mode_layout = QVBoxLayout()

        self.mode_group = QButtonGroup()

        self.full_video_radio = QRadioButton("Vidéo complète")
        self.full_video_radio.setChecked(True)
        self.full_video_radio.setToolTip("Extraire l'audio de toute la vidéo")
        self.mode_group.addButton(self.full_video_radio, 0)
        mode_layout.addWidget(self.full_video_radio)

        self.current_segment_radio = QRadioButton("Segment sélectionné")
        self.current_segment_radio.setToolTip("Extraire l'audio du segment actuellement sélectionné")
        self.mode_group.addButton(self.current_segment_radio, 1)
        mode_layout.addWidget(self.current_segment_radio)

        self.all_segments_radio = QRadioButton("Tous les segments")
        self.all_segments_radio.setToolTip("Extraire l'audio de chaque segment (fichiers séparés)")
        self.mode_group.addButton(self.all_segments_radio, 2)
        mode_layout.addWidget(self.all_segments_radio)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Format settings
        format_group = QGroupBox("Paramètres Audio")
        format_layout = QVBoxLayout()

        # Format selection
        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("Format:"))

        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP3", "AAC", "WAV", "FLAC", "OGG"])
        self.format_combo.setCurrentText("MP3")
        self.format_combo.setToolTip("Format de sortie audio")
        format_row.addWidget(self.format_combo)

        format_row.addStretch()
        format_layout.addLayout(format_row)

        # Bitrate selection
        bitrate_row = QHBoxLayout()
        bitrate_row.addWidget(QLabel("Qualité (bitrate):"))

        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems(["128 kbps", "192 kbps", "256 kbps", "320 kbps"])
        self.bitrate_combo.setCurrentIndex(1)  # 192 kbps default
        self.bitrate_combo.setToolTip("Qualité audio - Plus élevé = meilleure qualité")
        bitrate_row.addWidget(self.bitrate_combo)

        bitrate_row.addStretch()
        format_layout.addLayout(bitrate_row)

        # Normalize checkbox
        self.normalize_check = QCheckBox("Normaliser le volume")
        self.normalize_check.setToolTip("Ajuster automatiquement le volume audio")
        self.normalize_check.setChecked(False)
        format_layout.addWidget(self.normalize_check)

        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # Info about formats
        info_group = QGroupBox("ℹ️ Info Formats")
        info_layout = QVBoxLayout()
        info_text = QLabel("""
        <b>MP3</b>: Universel, compatible partout<br>
        <b>AAC</b>: Meilleure qualité que MP3 (Apple)<br>
        <b>WAV</b>: Non compressé, très haute qualité<br>
        <b>FLAC</b>: Compressé sans perte<br>
        <b>OGG</b>: Open source, bonne qualité
        """)
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: gray; font-size: 11px; padding: 5px;")
        info_layout.addWidget(info_text)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Extract button
        self.extract_btn = QPushButton("🎵 Extraire Audio")
        self.extract_btn.setEnabled(False)
        self.extract_btn.setStyleSheet("""
            QPushButton {
                padding: 12px;
                font-weight: bold;
                font-size: 13px;
                background-color: #dc3545;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.extract_btn.clicked.connect(self._on_extract_clicked)
        layout.addWidget(self.extract_btn)

        layout.addStretch()

    def _on_extract_clicked(self):
        """Handle extract button click."""
        audio_format = self.format_combo.currentText()
        bitrate_text = self.bitrate_combo.currentText()
        bitrate = int(bitrate_text.split()[0])  # Extract number from "192 kbps"
        normalize = self.normalize_check.isChecked()

        mode = self.mode_group.checkedId()

        if mode == 0:  # Full video
            self.extract_full_audio_clicked.emit(audio_format, bitrate, normalize)
        elif mode == 1:  # Current segment
            # This will be handled with segment index from parent
            self.extract_segment_audio_clicked.emit(0, audio_format, bitrate, normalize)
        elif mode == 2:  # All segments
            self.extract_all_segments_audio_clicked.emit(audio_format, bitrate, normalize)

    def set_enabled_state(self, enabled: bool):
        """Enable/disable extraction button."""
        self.extract_btn.setEnabled(enabled)

    def get_extraction_settings(self):
        """Get current extraction settings."""
        bitrate_text = self.bitrate_combo.currentText()
        bitrate = int(bitrate_text.split()[0])

        return {
            'format': self.format_combo.currentText(),
            'bitrate': bitrate,
            'normalize': self.normalize_check.isChecked(),
            'mode': self.mode_group.checkedId()
        }

    def update_mode_availability(self, has_segments: bool, has_selection: bool):
        """Update which modes are available based on state."""
        self.current_segment_radio.setEnabled(has_selection)
        self.all_segments_radio.setEnabled(has_segments)

        # If current mode becomes unavailable, switch to full video
        if not has_selection and self.current_segment_radio.isChecked():
            self.full_video_radio.setChecked(True)
        if not has_segments and self.all_segments_radio.isChecked():
            self.full_video_radio.setChecked(True)
