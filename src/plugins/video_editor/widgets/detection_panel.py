"""Detection panel widget for Video Editor."""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QSpinBox, QDoubleSpinBox,
                            QGroupBox, QSlider, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.DetectionPanel')


class DetectionPanel(QWidget):
    """Panel for automatic detection features."""

    # Signals
    detect_black_frames_clicked = pyqtSignal(int, int)  # threshold, min_duration
    detect_scenes_clicked = pyqtSignal(float, int)  # threshold, min_scene_length
    stop_scene_detection_clicked = pyqtSignal()  # stop scene detection
    split_n_parts_clicked = pyqtSignal()
    split_by_duration_clicked = pyqtSignal()
    merge_all_clicked = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize detection panel."""
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Title
        title = QLabel("🔍 Détection Automatique")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # Black Frames Detection
        black_group = QGroupBox("🖤 Fenêtres Noires")
        black_layout = QVBoxLayout()

        # Threshold
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Seuil luminosité:"))

        self.black_threshold_spin = QSpinBox()
        self.black_threshold_spin.setRange(0, 255)
        self.black_threshold_spin.setValue(20)
        self.black_threshold_spin.setToolTip("0 = noir complet, 255 = blanc")
        threshold_layout.addWidget(self.black_threshold_spin)

        threshold_layout.addStretch()
        black_layout.addLayout(threshold_layout)

        # Min duration
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Durée minimale:"))

        self.black_min_duration = QSpinBox()
        self.black_min_duration.setRange(1, 100)
        self.black_min_duration.setValue(10)
        self.black_min_duration.setSuffix(" frames")
        self.black_min_duration.setToolTip("Nombre minimum de frames noires consécutives")
        duration_layout.addWidget(self.black_min_duration)

        duration_layout.addStretch()
        black_layout.addLayout(duration_layout)

        # Detect button
        detect_black_btn = QPushButton("🔍 Détecter Fenêtres Noires")
        detect_black_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 8px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        detect_black_btn.clicked.connect(self._on_detect_black_clicked)
        black_layout.addWidget(detect_black_btn)

        black_group.setLayout(black_layout)
        layout.addWidget(black_group)

        # Scene Detection
        scene_group = QGroupBox("🎬 Changements de Scènes")
        scene_layout = QVBoxLayout()

        # Sensitivity
        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(QLabel("Sensibilité:"))

        self.scene_threshold_spin = QDoubleSpinBox()
        self.scene_threshold_spin.setRange(1.0, 100.0)
        self.scene_threshold_spin.setValue(30.0)
        self.scene_threshold_spin.setDecimals(1)
        self.scene_threshold_spin.setToolTip("Plus bas = plus sensible (détecte plus de scènes)")
        sensitivity_layout.addWidget(self.scene_threshold_spin)

        sensitivity_layout.addStretch()
        scene_layout.addLayout(sensitivity_layout)

        # Min scene length
        min_scene_layout = QHBoxLayout()
        min_scene_layout.addWidget(QLabel("Longueur minimale:"))

        self.scene_min_length = QSpinBox()
        self.scene_min_length.setRange(1, 300)
        self.scene_min_length.setValue(30)
        self.scene_min_length.setSuffix(" frames")
        self.scene_min_length.setToolTip("Nombre minimum de frames par scène")
        min_scene_layout.addWidget(self.scene_min_length)

        min_scene_layout.addStretch()
        scene_layout.addLayout(min_scene_layout)

        # Detect button and stop button
        buttons_layout = QHBoxLayout()

        detect_scene_btn = QPushButton("🔍 Détecter Scènes")
        detect_scene_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 8px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        detect_scene_btn.clicked.connect(self._on_detect_scenes_clicked)
        buttons_layout.addWidget(detect_scene_btn)
        self.detect_scene_btn = detect_scene_btn

        self.stop_scene_btn = QPushButton("⏹️ Arrêter")
        self.stop_scene_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 8px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.stop_scene_btn.clicked.connect(self.stop_scene_detection_clicked.emit)
        self.stop_scene_btn.hide()  # Hidden by default
        buttons_layout.addWidget(self.stop_scene_btn)

        scene_layout.addLayout(buttons_layout)

        # Progress bar for scene detection
        self.scene_progress = QProgressBar()
        self.scene_progress.setRange(0, 100)
        self.scene_progress.setValue(0)
        self.scene_progress.setTextVisible(True)
        self.scene_progress.setFormat("Analyse: %p%")
        self.scene_progress.hide()  # Hidden by default
        scene_layout.addWidget(self.scene_progress)

        scene_group.setLayout(scene_layout)
        layout.addWidget(scene_group)

        # Quick Actions
        actions_group = QGroupBox("⚡ Actions Rapides")
        actions_layout = QVBoxLayout()

        # Split N parts
        split_n_btn = QPushButton("📊 Diviser en N parties")
        split_n_btn.setToolTip("Diviser la vidéo en N segments égaux")
        split_n_btn.clicked.connect(self.split_n_parts_clicked.emit)
        actions_layout.addWidget(split_n_btn)

        # Split by duration
        split_duration_btn = QPushButton("⏱️ Diviser par durée")
        split_duration_btn.setToolTip("Créer segments de durée fixe")
        split_duration_btn.clicked.connect(self.split_by_duration_clicked.emit)
        actions_layout.addWidget(split_duration_btn)

        # Merge all
        merge_all_btn = QPushButton("🔗 Fusionner tout")
        merge_all_btn.setToolTip("Fusionner tous les segments en un seul")
        merge_all_btn.clicked.connect(self.merge_all_clicked.emit)
        actions_layout.addWidget(merge_all_btn)

        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        layout.addStretch()

    def _on_detect_black_clicked(self):
        """Handle black frames detection click."""
        threshold = self.black_threshold_spin.value()
        min_duration = self.black_min_duration.value()
        self.detect_black_frames_clicked.emit(threshold, min_duration)

    def _on_detect_scenes_clicked(self):
        """Handle scene detection click."""
        threshold = self.scene_threshold_spin.value()
        min_length = self.scene_min_length.value()
        self.detect_scenes_clicked.emit(threshold, min_length)

    def get_black_frame_settings(self):
        """Get black frame detection settings."""
        return {
            'threshold': self.black_threshold_spin.value(),
            'min_duration': self.black_min_duration.value()
        }

    def get_scene_detection_settings(self):
        """Get scene detection settings."""
        return {
            'threshold': self.scene_threshold_spin.value(),
            'min_scene_length': self.scene_min_length.value()
        }

    def set_enabled_state(self, enabled: bool):
        """Enable/disable detection buttons."""
        for widget in self.findChildren(QPushButton):
            widget.setEnabled(enabled)

    def show_scene_progress(self):
        """Show scene detection progress bar and stop button."""
        self.detect_scene_btn.hide()
        self.scene_progress.show()
        self.stop_scene_btn.show()

    def hide_scene_progress(self):
        """Hide scene detection progress bar and stop button."""
        self.scene_progress.hide()
        self.stop_scene_btn.hide()
        self.detect_scene_btn.show()
        self.scene_progress.setValue(0)

    def update_scene_progress(self, value: int):
        """Update scene detection progress bar value."""
        self.scene_progress.setValue(value)
