"""Media Browser widget - Simple file management for Video Editor.

Provides easy access to recent files and quick import.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog,
    QFrame, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap, QImage
from pathlib import Path
from typing import List
import json
import cv2
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.MediaBrowser')


class MediaBrowser(QWidget):
    """Simple media browser for quick file access.

    Shows recent files and provides easy import.
    """

    file_selected = pyqtSignal(str)  # file_path
    import_clicked = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize media browser.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.recent_files = []
        self.setup_ui()
        self.load_recent_files()

    def setup_ui(self):
        """Set up simple and clear UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Header
        header = QLabel("📁 Mes Fichiers")
        header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: white;
                padding: 5px;
            }
        """)
        layout.addWidget(header)

        # Import button (BIG and obvious)
        import_btn = QPushButton("📂 Ouvrir une Vidéo")
        import_btn.setMinimumHeight(50)
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        import_btn.clicked.connect(self.import_clicked.emit)
        layout.addWidget(import_btn)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #444;")
        layout.addWidget(separator)

        # Recent files label
        recent_label = QLabel("Fichiers Récents:")
        recent_label.setStyleSheet("color: #ccc; font-size: 12px; padding: 5px;")
        layout.addWidget(recent_label)

        # Recent files list
        self.recent_list = QListWidget()
        self.recent_list.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 5px;
            }
            QListWidget::item {
                color: white;
                padding: 8px;
                border-radius: 3px;
            }
            QListWidget::item:hover {
                background-color: #353535;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        self.recent_list.setIconSize(QSize(32, 32))
        self.recent_list.itemDoubleClicked.connect(self._on_file_double_clicked)
        layout.addWidget(self.recent_list)

        # Clear history button (small)
        clear_btn = QPushButton("🗑 Effacer l'historique")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888;
                border: none;
                padding: 5px;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #ff4444;
            }
        """)
        clear_btn.clicked.connect(self.clear_recent_files)
        layout.addWidget(clear_btn)

    def add_recent_file(self, file_path: str):
        """Add file to recent files.

        Args:
            file_path: Path to video file
        """
        # Remove if already exists
        self.recent_files = [f for f in self.recent_files if f != file_path]

        # Add to beginning
        self.recent_files.insert(0, file_path)

        # Keep only last 10
        self.recent_files = self.recent_files[:10]

        # Save and refresh
        self.save_recent_files()
        self.refresh_list()

    def refresh_list(self):
        """Refresh the recent files list."""
        self.recent_list.clear()

        for file_path in self.recent_files:
            if not Path(file_path).exists():
                continue

            # Create item
            item = QListWidgetItem()

            # Get file name
            file_name = Path(file_path).name

            # Try to load thumbnail
            icon = self._load_video_icon(file_path)
            if icon:
                item.setIcon(icon)
            else:
                item.setIcon(QIcon())  # Default icon

            # Set text
            item.setText(file_name)
            item.setToolTip(file_path)
            item.setData(Qt.ItemDataRole.UserRole, file_path)

            self.recent_list.addItem(item)

    def _load_video_icon(self, video_path: str) -> QIcon:
        """Load video thumbnail as icon.

        Args:
            video_path: Path to video

        Returns:
            QIcon with thumbnail or None
        """
        try:
            cap = cv2.VideoCapture(video_path)
            ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                # Resize to icon size
                frame = cv2.resize(frame, (32, 32))
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Convert to QImage
                h, w, ch = frame_rgb.shape
                bytes_per_line = ch * w
                qimage = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

                return QIcon(QPixmap.fromImage(qimage))
        except Exception as e:
            logger.debug(f"Could not generate thumbnail for {file_path}: {str(e)}")

        return None

    def _on_file_double_clicked(self, item: QListWidgetItem):
        """Handle file double click.

        Args:
            item: Clicked item
        """
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and Path(file_path).exists():
            self.file_selected.emit(file_path)

    def load_recent_files(self):
        """Load recent files from config."""
        config_dir = Path.home() / ".videoflow"
        recent_file = config_dir / "recent_files.json"

        if recent_file.exists():
            try:
                with open(recent_file, 'r', encoding='utf-8') as f:
                    self.recent_files = json.load(f)
                self.refresh_list()
            except Exception as e:
                logger.warning(f"Could not load recent files: {str(e)}")
                self.recent_files = []

    def save_recent_files(self):
        """Save recent files to config."""
        config_dir = Path.home() / ".videoflow"
        config_dir.mkdir(exist_ok=True)
        recent_file = config_dir / "recent_files.json"

        try:
            with open(recent_file, 'w', encoding='utf-8') as f:
                json.dump(self.recent_files, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save recent files: {str(e)}")

    def clear_recent_files(self):
        """Clear all recent files."""
        self.recent_files = []
        self.save_recent_files()
        self.refresh_list()
