"""Détecteur de fenêtres noires pour découpe automatique."""

import cv2
import numpy as np
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QGroupBox, QFormLayout, QSpinBox, QTableWidget,
                             QTableWidgetItem, QProgressBar, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.BlackFrameDetector')


class BlackFrameDetector(QThread):
    """Thread de détection de frames noires."""

    # Signaux
    progress = pyqtSignal(int)  # 0-100
    black_range_found = pyqtSignal(int, int)  # start_frame, end_frame
    finished = pyqtSignal(list)  # Liste de (start, end) tuples

    def __init__(self, video_path, threshold=20, min_duration=10):
        """
        Initialize black frame detector.

        Args:
            video_path: Path to the video file
            threshold: Brightness threshold (0-255, default 20)
            min_duration: Minimum duration in frames (default 10)
        """
        super().__init__()
        self.video_path = video_path
        self.threshold = threshold
        self.min_duration = min_duration
        self._stop = False

    def run(self):
        """Detect black frame ranges."""
        black_ranges = []

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video: {self.video_path}")
            self.finished.emit([])
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        current_black_start = None
        frame_number = 0

        try:
            while not self._stop:
                ret, frame = cap.read()
                if not ret:
                    break

                # Calculate average brightness
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                mean_brightness = np.mean(gray)

                is_black = mean_brightness < self.threshold

                if is_black:
                    if current_black_start is None:
                        current_black_start = frame_number
                else:
                    if current_black_start is not None:
                        duration = frame_number - current_black_start
                        if duration >= self.min_duration:
                            black_ranges.append((current_black_start, frame_number - 1))
                            self.black_range_found.emit(current_black_start, frame_number - 1)
                        current_black_start = None

                # Progress update
                frame_number += 1
                if frame_number % 30 == 0:  # Update every 30 frames
                    progress = int((frame_number / total_frames) * 100)
                    self.progress.emit(progress)

            # Handle last black range if ongoing
            if current_black_start is not None:
                duration = frame_number - current_black_start
                if duration >= self.min_duration:
                    black_ranges.append((current_black_start, frame_number - 1))

        finally:
            cap.release()

        logger.info(f"Detected {len(black_ranges)} black ranges")
        self.finished.emit(black_ranges)

    def stop(self):
        """Stop detection."""
        self._stop = True


class BlackFrameDetectorDialog(QDialog):
    """Dialog for black frame detection."""

    def __init__(self, video_path, fps, total_frames, parent=None):
        """Initialize dialog."""
        super().__init__(parent)
        self.video_path = video_path
        self.fps = fps
        self.total_frames = total_frames
        self.black_ranges = []
        self.detector = None

        self.setWindowTitle("Détection de Fenêtres Noires")
        self.setMinimumSize(700, 500)
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)

        # === Parameters ===
        params_group = QGroupBox("Paramètres de Détection")
        params_layout = QFormLayout()

        # Brightness threshold
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 255)
        self.threshold_spin.setValue(20)
        self.threshold_spin.setToolTip(
            "Seuil de luminosité moyenne (0-255)\n"
            "Plus bas = détection plus stricte\n"
            "Recommandé: 10-30"
        )
        params_layout.addRow("Seuil de luminosité:", self.threshold_spin)

        # Minimum duration
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 300)
        self.duration_spin.setValue(10)
        self.duration_spin.setSuffix(" frames")
        self.duration_spin.setToolTip(
            "Durée minimale d'une plage noire\n"
            "Évite les faux positifs sur frames isolées"
        )
        params_layout.addRow("Durée minimale:", self.duration_spin)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # === Results ===
        results_group = QGroupBox("Plages Noires Détectées")
        results_layout = QVBoxLayout()

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels([
            "Début (frame)", "Fin (frame)", "Durée", "Timecode"
        ])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        results_layout.addWidget(self.results_table)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        # === Progress ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # === Buttons ===
        buttons_layout = QHBoxLayout()

        self.detect_btn = QPushButton("🔍 Détecter")
        self.detect_btn.clicked.connect(self.start_detection)
        buttons_layout.addWidget(self.detect_btn)

        self.create_segments_btn = QPushButton("✂️ Créer Segments entre les Noirs")
        self.create_segments_btn.clicked.connect(self.accept)
        self.create_segments_btn.setEnabled(False)
        buttons_layout.addWidget(self.create_segments_btn)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

    def start_detection(self):
        """Start detection."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.detect_btn.setEnabled(False)
        self.results_table.setRowCount(0)

        # Create detector
        threshold = self.threshold_spin.value()
        min_duration = self.duration_spin.value()

        self.detector = BlackFrameDetector(
            self.video_path,
            threshold=threshold,
            min_duration=min_duration
        )

        # Connect signals
        self.detector.progress.connect(self.progress_bar.setValue)
        self.detector.black_range_found.connect(self.add_black_range)
        self.detector.finished.connect(self.on_detection_finished)

        self.detector.start()

    def add_black_range(self, start_frame, end_frame):
        """Add black range to table."""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)

        duration = end_frame - start_frame + 1
        start_time = start_frame / self.fps
        end_time = end_frame / self.fps

        self.results_table.setItem(row, 0, QTableWidgetItem(str(start_frame)))
        self.results_table.setItem(row, 1, QTableWidgetItem(str(end_frame)))
        self.results_table.setItem(row, 2, QTableWidgetItem(f"{duration} frames"))
        self.results_table.setItem(row, 3,
            QTableWidgetItem(f"{self.format_time(start_time)} → {self.format_time(end_time)}")
        )

    def on_detection_finished(self, black_ranges):
        """Called when detection is finished."""
        self.black_ranges = black_ranges
        self.progress_bar.setVisible(False)
        self.detect_btn.setEnabled(True)

        if black_ranges:
            self.create_segments_btn.setEnabled(True)
            QMessageBox.information(
                self,
                "Détection terminée",
                f"{len(black_ranges)} plage(s) noire(s) détectée(s)"
            )
        else:
            QMessageBox.information(
                self,
                "Aucune plage noire",
                "Aucune fenêtre noire détectée.\nEssayez d'augmenter le seuil."
            )

    def format_time(self, seconds):
        """Format time using TimeCode utility."""
        timecode = TimeCode(self.fps)
        return timecode.seconds_to_timecode(seconds)

    def get_segments_between_blacks(self):
        """Return segments to create between black ranges."""
        if not self.black_ranges:
            return []

        segments = []

        # First segment (before first black range)
        if self.black_ranges[0][0] > 0:
            segments.append((0, self.black_ranges[0][0] - 1))

        # Segments between black ranges
        for i in range(len(self.black_ranges) - 1):
            start = self.black_ranges[i][1] + 1
            end = self.black_ranges[i + 1][0] - 1
            if end > start:
                segments.append((start, end))

        # Last segment (after last black range)
        if self.black_ranges[-1][1] < self.total_frames - 1:
            segments.append((self.black_ranges[-1][1] + 1, self.total_frames - 1))

        return segments
