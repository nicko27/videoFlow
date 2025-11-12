"""Video merger pour fusionner plusieurs vidéos dans la timeline."""

import os
import tempfile
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QLabel, QProgressBar, QMessageBox,
                             QFileDialog)
from PyQt6.QtCore import QThread, pyqtSignal
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.VideoMerger')


class VideoMergeWorker(QThread):
    """Worker thread for merging multiple videos."""

    progress = pyqtSignal(int)  # 0-100
    status_message = pyqtSignal(str)
    finished = pyqtSignal(str)  # output_path
    error = pyqtSignal(str)

    def __init__(self, video_paths, output_path):
        """Initialize video merge worker."""
        super().__init__()
        self.video_paths = video_paths
        self.output_path = output_path
        self._stop = False

    def run(self):
        """Merge videos."""
        try:
            # Create temporary file list for FFmpeg
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for video_path in self.video_paths:
                    # Escape special characters
                    escaped_path = video_path.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
                temp_list = f.name

            try:
                self.status_message.emit("Fusion en cours...")

                # Use FFmpeg concat demuxer
                cmd = [
                    'ffmpeg', '-y',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', temp_list,
                    '-c', 'copy',
                    self.output_path
                ]

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                # Monitor progress (simplified)
                while process.poll() is None:
                    if self._stop:
                        process.terminate()
                        self.error.emit("Fusion annulée")
                        return

                if process.returncode == 0:
                    self.status_message.emit("Fusion réussie!")
                    self.finished.emit(self.output_path)
                else:
                    stderr = process.stderr.read()
                    logger.error(f"FFmpeg error: {stderr}")
                    self.error.emit(f"Erreur FFmpeg: {stderr[:200]}")

            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_list)
                except:
                    pass

        except Exception as e:
            logger.error(f"Error merging videos: {e}")
            self.error.emit(str(e))

    def stop(self):
        """Stop merge operation."""
        self._stop = True


class VideoMergerDialog(QDialog):
    """Dialog for merging multiple videos."""

    def __init__(self, parent=None):
        """Initialize dialog."""
        super().__init__(parent)
        self.video_paths = []
        self.merge_worker = None

        self.setWindowTitle("Fusionner Plusieurs Vidéos")
        self.setMinimumSize(600, 400)
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Sélectionnez les vidéos à fusionner (dans l'ordre)")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # Video list
        self.video_list = QListWidget()
        layout.addWidget(self.video_list)

        # Buttons for managing list
        list_buttons = QHBoxLayout()

        add_btn = QPushButton("➕ Ajouter vidéos")
        add_btn.clicked.connect(self.add_videos)
        list_buttons.addWidget(add_btn)

        move_up_btn = QPushButton("⬆️ Monter")
        move_up_btn.clicked.connect(self.move_up)
        list_buttons.addWidget(move_up_btn)

        move_down_btn = QPushButton("⬇️ Descendre")
        move_down_btn.clicked.connect(self.move_down)
        list_buttons.addWidget(move_down_btn)

        remove_btn = QPushButton("🗑️ Retirer")
        remove_btn.clicked.connect(self.remove_selected)
        list_buttons.addWidget(remove_btn)

        layout.addLayout(list_buttons)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Action buttons
        action_buttons = QHBoxLayout()

        self.merge_btn = QPushButton("🔗 Fusionner")
        self.merge_btn.clicked.connect(self.start_merge)
        self.merge_btn.setEnabled(False)
        action_buttons.addWidget(self.merge_btn)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        action_buttons.addWidget(cancel_btn)

        layout.addLayout(action_buttons)

    def add_videos(self):
        """Add videos to list."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner les vidéos",
            "",
            "Vidéos (*.mp4 *.avi *.mkv *.mov);;Tous les fichiers (*.*)"
        )

        if files:
            for file in files:
                if file not in self.video_paths:
                    self.video_paths.append(file)
                    self.video_list.addItem(os.path.basename(file))

            self.merge_btn.setEnabled(len(self.video_paths) >= 2)

    def move_up(self):
        """Move selected item up."""
        current_row = self.video_list.currentRow()
        if current_row > 0:
            # Swap in list
            self.video_paths[current_row], self.video_paths[current_row - 1] = \
                self.video_paths[current_row - 1], self.video_paths[current_row]

            # Update UI
            item = self.video_list.takeItem(current_row)
            self.video_list.insertItem(current_row - 1, item)
            self.video_list.setCurrentRow(current_row - 1)

    def move_down(self):
        """Move selected item down."""
        current_row = self.video_list.currentRow()
        if current_row < len(self.video_paths) - 1:
            # Swap in list
            self.video_paths[current_row], self.video_paths[current_row + 1] = \
                self.video_paths[current_row + 1], self.video_paths[current_row]

            # Update UI
            item = self.video_list.takeItem(current_row)
            self.video_list.insertItem(current_row + 1, item)
            self.video_list.setCurrentRow(current_row + 1)

    def remove_selected(self):
        """Remove selected item."""
        current_row = self.video_list.currentRow()
        if current_row >= 0:
            self.video_paths.pop(current_row)
            self.video_list.takeItem(current_row)
            self.merge_btn.setEnabled(len(self.video_paths) >= 2)

    def start_merge(self):
        """Start merging videos."""
        if len(self.video_paths) < 2:
            QMessageBox.warning(self, "Erreur", "Il faut au moins 2 vidéos")
            return

        # Ask for output location
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Sauvegarder vidéo fusionnée",
            "merged_video.mp4",
            "Vidéo MP4 (*.mp4)"
        )

        if not output_path:
            return

        # Start merge
        self.progress_bar.setVisible(True)
        self.merge_btn.setEnabled(False)

        self.merge_worker = VideoMergeWorker(self.video_paths, output_path)
        self.merge_worker.progress.connect(self.progress_bar.setValue)
        self.merge_worker.status_message.connect(self.status_label.setText)
        self.merge_worker.finished.connect(self.on_merge_finished)
        self.merge_worker.error.connect(self.on_merge_error)

        self.merge_worker.start()

    def on_merge_finished(self, output_path):
        """Called when merge is finished."""
        self.progress_bar.setVisible(False)
        self.merge_btn.setEnabled(True)

        reply = QMessageBox.question(
            self,
            "Fusion réussie",
            f"Vidéo fusionnée enregistrée:\n{output_path}\n\nOuvrir dans l'éditeur?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.merged_video_path = output_path
            self.accept()
        else:
            self.merged_video_path = None
            self.reject()

    def on_merge_error(self, error_msg):
        """Called when merge error occurs."""
        self.progress_bar.setVisible(False)
        self.merge_btn.setEnabled(True)
        QMessageBox.critical(self, "Erreur", f"Erreur lors de la fusion:\n{error_msg}")

    def get_merged_video_path(self):
        """Return path of merged video if user wants to open it."""
        return getattr(self, 'merged_video_path', None)
