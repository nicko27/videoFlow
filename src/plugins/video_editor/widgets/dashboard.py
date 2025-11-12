"""Modern dashboard widget for Video Editor.

Provides a professional welcome screen with recent projects, quick actions,
and tips similar to Adobe Premiere Pro or DaVinci Resolve.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QLinearGradient, QImage
from pathlib import Path
from typing import List, Dict, Optional
import json
from datetime import datetime
import cv2
import numpy as np


class ProjectCard(QFrame):
    """Card widget for a recent project."""

    clicked = pyqtSignal(str)  # project_path

    def __init__(self, project_info: Dict, parent=None):
        """Initialize project card.

        Args:
            project_info: Dict with keys: name, path, last_modified, thumbnail
            parent: Parent widget
        """
        super().__init__(parent)
        self.project_info = project_info
        self.setup_ui()

    def setup_ui(self):
        """Set up the card UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setStyleSheet("""
            ProjectCard {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 10px;
            }
            ProjectCard:hover {
                background-color: #353535;
                border: 1px solid #0078d4;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Thumbnail - try to load real thumbnail, fallback to gradient
        thumbnail = QLabel()
        thumbnail.setFixedSize(200, 112)  # 16:9 ratio
        thumbnail.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 4px;
        """)
        thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Try to load real thumbnail
        pixmap = self._load_video_thumbnail(self.project_info.get('path'))

        if pixmap is None:
            # Create gradient thumbnail as fallback
            pixmap = QPixmap(200, 112)
            painter = QPainter(pixmap)
            gradient = QLinearGradient(0, 0, 200, 112)
            gradient.setColorAt(0.0, QColor(30, 30, 30))
            gradient.setColorAt(1.0, QColor(60, 60, 60))
            painter.fillRect(0, 0, 200, 112, gradient)

            # Draw video icon
            painter.setPen(QColor(120, 120, 120))
            font = QFont()
            font.setPointSize(32)
            painter.setFont(font)
            painter.drawText(0, 0, 200, 112, Qt.AlignmentFlag.AlignCenter, "🎬")
            painter.end()

        thumbnail.setPixmap(pixmap)
        layout.addWidget(thumbnail)

        # Project name
        name_label = QLabel(self.project_info.get('name', 'Untitled'))
        name_label.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-weight: bold;
        """)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        # Last modified
        last_modified = self.project_info.get('last_modified', 'Unknown')
        if isinstance(last_modified, (int, float)):
            dt = datetime.fromtimestamp(last_modified)
            time_str = self._format_time_ago(dt)
        else:
            time_str = last_modified

        time_label = QLabel(f"📅 {time_str}")
        time_label.setStyleSheet("""
            color: #888;
            font-size: 11px;
        """)
        layout.addWidget(time_label)

    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as relative time.

        Args:
            dt: Datetime object

        Returns:
            Formatted string like "2 hours ago"
        """
        now = datetime.now()
        diff = now - dt

        if diff.days > 365:
            years = diff.days // 365
            return f"{years} an{'s' if years > 1 else ''}"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} mois"
        elif diff.days > 0:
            return f"{diff.days} jour{'s' if diff.days > 1 else ''}"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}min"
        else:
            return "À l'instant"

    def _load_video_thumbnail(self, video_path: Optional[str]) -> Optional[QPixmap]:
        """Load thumbnail from video file.

        Args:
            video_path: Path to video file

        Returns:
            QPixmap with thumbnail, or None if failed
        """
        if not video_path or not Path(video_path).exists():
            return None

        try:
            # Open video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None

            # Read first frame
            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                return None

            # Resize to thumbnail size (200x112)
            frame = cv2.resize(frame, (200, 112), interpolation=cv2.INTER_AREA)

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert to QImage
            height, width, channels = frame_rgb.shape
            bytes_per_line = channels * width
            qimage = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)

            # Convert to QPixmap
            pixmap = QPixmap.fromImage(qimage)

            return pixmap

        except Exception:
            return None

    def mousePressEvent(self, event):
        """Handle mouse press to open project."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.project_info.get('path', ''))
        super().mousePressEvent(event)


class QuickActionButton(QPushButton):
    """Styled button for quick actions."""

    def __init__(self, icon: str, title: str, description: str, parent=None):
        """Initialize quick action button.

        Args:
            icon: Emoji or icon text
            title: Action title
            description: Action description
            parent: Parent widget
        """
        super().__init__(parent)
        self.icon = icon
        self.title = title
        self.description = description

        self.setup_ui()

    def setup_ui(self):
        """Set up button UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        # Icon
        icon_label = QLabel(self.icon)
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Title
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-weight: bold;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(self.description)
        desc_label.setStyleSheet("""
            color: #888;
            font-size: 11px;
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        self.setStyleSheet("""
            QuickActionButton {
                background-color: #2a2a2a;
                border: 2px solid #3a3a3a;
                border-radius: 10px;
                padding: 20px;
                min-width: 180px;
                min-height: 160px;
            }
            QuickActionButton:hover {
                background-color: #353535;
                border: 2px solid #0078d4;
            }
            QuickActionButton:pressed {
                background-color: #404040;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class DashboardWidget(QWidget):
    """Modern dashboard widget for Video Editor.

    Displays:
    - Welcome message
    - Recent projects grid
    - Quick action buttons
    - Tips of the day
    """

    open_video_clicked = pyqtSignal()
    open_project_clicked = pyqtSignal(str)  # project_path
    new_project_clicked = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize dashboard widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.recent_projects = []
        self.load_recent_projects()
        self.setup_ui()

    def setup_ui(self):
        """Set up the dashboard UI."""
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
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        # Header
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Quick Actions
        quick_actions_group = self._create_quick_actions()
        layout.addWidget(quick_actions_group)

        # Recent Projects
        if self.recent_projects:
            recent_projects_group = self._create_recent_projects()
            layout.addWidget(recent_projects_group)

        # Tips section
        tips_group = self._create_tips()
        layout.addWidget(tips_group)

        layout.addStretch()

    def _create_header(self) -> QVBoxLayout:
        """Create dashboard header.

        Returns:
            Header layout
        """
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Welcome title
        title = QLabel("🎬 Video Editor Pro")
        title.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            color: #0078d4;
        """)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Éditeur vidéo professionnel pour tous vos projets")
        subtitle.setStyleSheet("""
            font-size: 16px;
            color: #888;
        """)
        layout.addWidget(subtitle)

        return layout

    def _create_quick_actions(self) -> QFrame:
        """Create quick actions section.

        Returns:
            Quick actions frame
        """
        group = QFrame()
        group.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(15)

        # Section title
        title = QLabel("Actions Rapides")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: white;
        """)
        layout.addWidget(title)

        # Buttons grid
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)

        # New Project button
        new_project_btn = QuickActionButton(
            "📹",
            "Nouveau Projet",
            "Commencer un nouveau projet d'édition"
        )
        new_project_btn.clicked.connect(self.new_project_clicked.emit)
        buttons_layout.addWidget(new_project_btn)

        # Open Video button
        open_video_btn = QuickActionButton(
            "📁",
            "Ouvrir Vidéo",
            "Ouvrir une vidéo existante pour édition"
        )
        open_video_btn.clicked.connect(self.open_video_clicked.emit)
        buttons_layout.addWidget(open_video_btn)

        # Import Files button
        import_btn = QuickActionButton(
            "📥",
            "Importer Fichiers",
            "Importer des médias pour votre projet"
        )
        buttons_layout.addWidget(import_btn)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        return group

    def _create_recent_projects(self) -> QFrame:
        """Create recent projects section.

        Returns:
            Recent projects frame
        """
        group = QFrame()
        layout = QVBoxLayout(group)
        layout.setSpacing(15)

        # Section title
        title_layout = QHBoxLayout()
        title = QLabel("Projets Récents")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: white;
        """)
        title_layout.addWidget(title)
        title_layout.addStretch()

        # Clear button
        clear_btn = QPushButton("🗑️ Effacer l'historique")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888;
                border: none;
                padding: 5px 10px;
            }
            QPushButton:hover {
                color: #ff4444;
            }
        """)
        clear_btn.clicked.connect(self.clear_recent_projects)
        title_layout.addWidget(clear_btn)

        layout.addLayout(title_layout)

        # Projects grid
        grid = QGridLayout()
        grid.setSpacing(15)

        for i, project in enumerate(self.recent_projects[:6]):  # Show max 6
            card = ProjectCard(project)
            card.clicked.connect(self.open_project_clicked.emit)
            row = i // 3
            col = i % 3
            grid.addWidget(card, row, col)

        layout.addLayout(grid)

        return group

    def _create_tips(self) -> QFrame:
        """Create tips section.

        Returns:
            Tips frame
        """
        group = QFrame()
        group.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                border-radius: 10px;
                padding: 20px;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Title
        title = QLabel("💡 Astuce du Jour")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #ffc107;
        """)
        layout.addWidget(title)

        # Tip content
        tips = [
            "Utilisez <b>I</b> et <b>O</b> pour marquer les points IN et OUT rapidement.",
            "Appuyez sur <b>Espace</b> pour lire/pause la vidéo.",
            "Utilisez <b>Ctrl+Z</b> pour annuler et <b>Ctrl+Y</b> pour rétablir.",
            "La touche <b>C</b> crée un segment entre les points IN et OUT.",
            "Clic droit sur un segment pour accéder aux options avancées.",
            "Utilisez <b>Ctrl+,</b> pour ouvrir les préférences et changer le thème.",
            "Le bouton <b>📝 Texte</b> permet d'ajouter des titres professionnels.",
            "Le bouton <b>⚡ Transition</b> ajoute des effets entre segments.",
        ]

        import random
        tip_text = random.choice(tips)

        tip = QLabel(tip_text)
        tip.setStyleSheet("""
            font-size: 14px;
            color: #ccc;
        """)
        tip.setWordWrap(True)
        layout.addWidget(tip)

        return group

    def load_recent_projects(self):
        """Load recent projects from config file."""
        config_dir = Path.home() / ".videoflow"
        recent_file = config_dir / "recent_projects.json"

        if recent_file.exists():
            try:
                with open(recent_file, 'r', encoding='utf-8') as f:
                    self.recent_projects = json.load(f)
            except Exception:
                self.recent_projects = []
        else:
            self.recent_projects = []

    def add_recent_project(self, name: str, path: str):
        """Add a project to recent projects.

        Args:
            name: Project name
            path: Project file path
        """
        project_info = {
            'name': name,
            'path': path,
            'last_modified': datetime.now().timestamp()
        }

        # Remove if already exists
        self.recent_projects = [p for p in self.recent_projects if p['path'] != path]

        # Add to beginning
        self.recent_projects.insert(0, project_info)

        # Keep only last 10
        self.recent_projects = self.recent_projects[:10]

        # Save
        self.save_recent_projects()

    def save_recent_projects(self):
        """Save recent projects to config file."""
        config_dir = Path.home() / ".videoflow"
        config_dir.mkdir(exist_ok=True)
        recent_file = config_dir / "recent_projects.json"

        try:
            with open(recent_file, 'w', encoding='utf-8') as f:
                json.dump(self.recent_projects, f, indent=2)
        except Exception:
            pass

    def clear_recent_projects(self):
        """Clear all recent projects."""
        self.recent_projects = []
        self.save_recent_projects()
        # Refresh UI
        self.setup_ui()
