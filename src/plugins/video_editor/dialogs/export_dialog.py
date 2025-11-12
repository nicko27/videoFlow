"""Export dialog for video segments."""

import os
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QMessageBox, QProgressDialog,
    QLineEdit, QGroupBox, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.ExportDialog')


class ExportWorker(QThread):
    """Worker thread for exporting segments."""

    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(bool, str)  # success, message
    error = pyqtSignal(str)

    def __init__(self, video_path, segments, fps, output_dir, file_pattern, codec, quality):
        super().__init__()
        self.video_path = video_path
        self.segments = segments
        self.fps = fps
        self.output_dir = output_dir
        self.file_pattern = file_pattern
        self.codec = codec
        self.quality = quality
        self._stop = False

    def stop(self):
        """Stop the export process."""
        self._stop = True

    def run(self):
        """Export all segments to separate video files."""
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            total_segments = len(self.segments)

            for idx, segment in enumerate(self.segments):
                if self._stop:
                    self.finished.emit(False, "Export annulé par l'utilisateur")
                    return

                # Calculate timestamps
                start_time = segment.start_frame / self.fps
                end_time = segment.end_frame / self.fps
                duration = end_time - start_time

                # Generate output filename
                segment_name = segment.name if segment.name else f"segment_{idx + 1:03d}"
                # Sanitize filename
                segment_name = "".join(c for c in segment_name if c.isalnum() or c in (' ', '-', '_')).strip()
                output_file = os.path.join(
                    self.output_dir,
                    self.file_pattern.format(index=idx + 1, name=segment_name)
                )

                # Build FFmpeg command
                cmd = [
                    'ffmpeg',
                    '-ss', str(start_time),
                    '-i', self.video_path,
                    '-t', str(duration),
                    '-c:v', self.codec,
                ]

                # Add quality settings
                if self.codec == 'libx264':
                    cmd.extend(['-crf', str(self.quality)])
                elif self.codec == 'copy':
                    cmd.extend(['-c:a', 'copy'])
                else:
                    cmd.extend(['-q:v', str(self.quality)])

                cmd.extend([
                    '-c:a', 'aac' if self.codec != 'copy' else 'copy',
                    '-y',  # Overwrite output files
                    output_file
                ])

                logger.info(f"Exporting segment {idx + 1}/{total_segments}: {segment_name}")

                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minutes timeout per segment
                    )

                    if result.returncode != 0:
                        error_msg = f"FFmpeg error for segment {idx + 1}: {result.stderr}"
                        logger.error(error_msg)
                        self.error.emit(error_msg)
                        continue

                    logger.info(f"Segment {idx + 1} exported successfully")

                except subprocess.TimeoutExpired:
                    error_msg = f"Export timeout for segment {idx + 1}"
                    logger.error(error_msg)
                    self.error.emit(error_msg)
                    continue
                except Exception as e:
                    error_msg = f"Error exporting segment {idx + 1}: {str(e)}"
                    logger.error(error_msg)
                    self.error.emit(error_msg)
                    continue

                self.progress.emit(idx + 1, total_segments)

            if not self._stop:
                self.finished.emit(True, f"{total_segments} segments exportés avec succès")

        except Exception as e:
            error_msg = f"Export error: {str(e)}"
            logger.error(error_msg)
            self.finished.emit(False, error_msg)


class ExportDialog(QDialog):
    """Dialog for exporting video segments to separate files."""

    def __init__(self, parent, video_path, segments, fps):
        super().__init__(parent)
        self.video_path = video_path
        self.segments = segments
        self.fps = fps
        self.worker = None

        self.setWindowTitle("Exporter les segments")
        self.setMinimumWidth(500)

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # Info label
        info_label = QLabel(
            f"<b>{len(self.segments)} segment(s)</b> à exporter en fichiers vidéo séparés"
        )
        layout.addWidget(info_label)

        # Output directory selection
        dir_group = QGroupBox("Dossier de destination")
        dir_layout = QVBoxLayout()

        dir_row = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        default_dir = os.path.join(
            os.path.dirname(self.video_path),
            "exported_segments"
        )
        self.output_dir_edit.setText(default_dir)
        dir_row.addWidget(self.output_dir_edit)

        browse_btn = QPushButton("Parcourir...")
        browse_btn.clicked.connect(self.browse_output_dir)
        dir_row.addWidget(browse_btn)

        dir_layout.addLayout(dir_row)
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)

        # Export settings
        settings_group = QGroupBox("Paramètres d'export")
        settings_layout = QVBoxLayout()

        # File pattern
        pattern_row = QHBoxLayout()
        pattern_row.addWidget(QLabel("Nom de fichier:"))
        self.file_pattern_edit = QLineEdit("{name}.mp4")
        self.file_pattern_edit.setToolTip(
            "Utilisez {index} pour le numéro et {name} pour le nom du segment"
        )
        pattern_row.addWidget(self.file_pattern_edit)
        settings_layout.addLayout(pattern_row)

        # Codec selection
        codec_row = QHBoxLayout()
        codec_row.addWidget(QLabel("Codec vidéo:"))
        self.codec_combo = QComboBox()
        self.codec_combo.addItems([
            "libx264 (H.264 - Recommandé)",
            "libx265 (H.265 - Meilleure compression)",
            "copy (Copie directe - Plus rapide)"
        ])
        self.codec_combo.currentIndexChanged.connect(self.on_codec_changed)
        codec_row.addWidget(self.codec_combo)
        settings_layout.addLayout(codec_row)

        # Quality setting
        quality_row = QHBoxLayout()
        quality_row.addWidget(QLabel("Qualité:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            "Très haute (CRF 18)",
            "Haute (CRF 23)",
            "Moyenne (CRF 28)",
            "Basse (CRF 32)"
        ])
        self.quality_combo.setCurrentIndex(1)  # Haute par défaut
        quality_row.addWidget(self.quality_combo)
        settings_layout.addLayout(quality_row)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        export_btn = QPushButton("Exporter")
        export_btn.clicked.connect(self.start_export)
        export_btn.setDefault(True)
        buttons_layout.addWidget(export_btn)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def browse_output_dir(self):
        """Open directory browser."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner le dossier de destination",
            self.output_dir_edit.text()
        )
        if directory:
            self.output_dir_edit.setText(directory)

    def on_codec_changed(self, index):
        """Handle codec selection change."""
        # Disable quality for copy codec
        self.quality_combo.setEnabled(index != 2)

    def get_codec_string(self):
        """Get the FFmpeg codec string."""
        codec_map = {
            0: 'libx264',
            1: 'libx265',
            2: 'copy'
        }
        return codec_map.get(self.codec_combo.currentIndex(), 'libx264')

    def get_quality_value(self):
        """Get the CRF quality value."""
        quality_map = {
            0: 18,  # Très haute
            1: 23,  # Haute
            2: 28,  # Moyenne
            3: 32   # Basse
        }
        return quality_map.get(self.quality_combo.currentIndex(), 23)

    def start_export(self):
        """Start the export process."""
        output_dir = self.output_dir_edit.text().strip()

        if not output_dir:
            QMessageBox.warning(
                self,
                "Dossier requis",
                "Veuillez sélectionner un dossier de destination."
            )
            return

        file_pattern = self.file_pattern_edit.text().strip()
        if not file_pattern:
            file_pattern = "{name}.mp4"

        # Create progress dialog
        progress = QProgressDialog(
            "Export des segments en cours...",
            "Annuler",
            0,
            len(self.segments),
            self
        )
        progress.setWindowTitle("Export en cours")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        # Create and start worker
        self.worker = ExportWorker(
            self.video_path,
            self.segments,
            self.fps,
            output_dir,
            file_pattern,
            self.get_codec_string(),
            self.get_quality_value()
        )

        def on_progress(current, total):
            progress.setValue(current)
            progress.setLabelText(f"Export segment {current}/{total}...")

        def on_finished(success, message):
            progress.close()
            if success:
                QMessageBox.information(self, "Export terminé", message)
                self.accept()
            else:
                QMessageBox.warning(self, "Export échoué", message)

        def on_error(error_msg):
            logger.warning(f"Export error: {error_msg}")

        def on_cancel():
            if self.worker:
                self.worker.stop()

        self.worker.progress.connect(on_progress)
        self.worker.finished.connect(on_finished)
        self.worker.error.connect(on_error)
        progress.canceled.connect(on_cancel)

        self.worker.start()
