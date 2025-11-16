"""
Duplicate comparison dialog - Clean and professional version
"""

import os
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QProgressBar, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QScreen

# Import video widget
try:
    from .video_preview_widget import VideoPreviewWidget
except ImportError:
    from video_preview_widget import VideoPreviewWidget

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.ComparisonDialog')


class ComparisonDialog(QDialog):
    """Optimized duplicate comparison dialog"""

    def __init__(self, file1: str, file2: str, similarity: float, parent=None):
        super().__init__(parent)
        self.file1 = file1
        self.file2 = file2
        self.similarity = similarity
        self.result = None

        # Arrange files intelligently
        self.arrange_files_by_name()

        self.setWindowTitle(f"Duplicate Comparison - Similarity: {self.similarity:.1f}%")

        # Open maximized
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.setModal(True)

        self.setup_ui()

        # Show at 10% after a delay
        QTimer.singleShot(500, self.show_initial_position)

    def arrange_files_by_name(self):
        """Place file without numbering on the left"""
        try:
            file1_name = os.path.basename(self.file1)
            file2_name = os.path.basename(self.file2)

            # Numbering/copy patterns
            patterns = [r'\(\d+\)', r'_\d+', r' - Copy', r'Copy of ', r'Copy de ']

            file1_has_pattern = any(re.search(pattern, file1_name) for pattern in patterns)
            file2_has_pattern = any(re.search(pattern, file2_name) for pattern in patterns)

            # If only file1 has a pattern, swap
            if file1_has_pattern and not file2_has_pattern:
                self.file1, self.file2 = self.file2, self.file1
            elif not file1_has_pattern and not file2_has_pattern:
                # Alphabetical order if no pattern
                if file1_name > file2_name:
                    self.file1, self.file2 = self.file2, self.file1

        except Exception as e:
            logger.error(f"Error arranging files: {e}")

    def setup_ui(self):
        """Configure the interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Similarity indicator
        similarity_frame = self.create_similarity_indicator()
        layout.addWidget(similarity_frame)

        # Main comparison area
        comparison_layout = QHBoxLayout()
        comparison_layout.setSpacing(30)

        # Video A (left)
        left_frame = self.create_video_frame("A", self.file1, "#4CAF50")
        self.left_video = left_frame[1]
        comparison_layout.addWidget(left_frame[0])

        # Video B (right)
        right_frame = self.create_video_frame("B", self.file2, "#FF9800")
        self.right_video = right_frame[1]
        comparison_layout.addWidget(right_frame[0])

        layout.addLayout(comparison_layout)

        # Navigation controls
        nav_controls = self.create_navigation_controls()
        layout.addWidget(nav_controls)

        # Action buttons
        action_buttons = self.create_action_buttons()
        layout.addWidget(action_buttons)

    def create_similarity_indicator(self):
        """Create the similarity indicator"""
        frame = QFrame()
        frame.setFixedHeight(60)

        # Color according to level
        if self.similarity >= 95:
            bg_color, bar_color, text_color = "#E8F5E8", "#4CAF50", "#2E7D32"
            level = "VERY HIGH"
        elif self.similarity >= 85:
            bg_color, bar_color, text_color = "#FFF8E1", "#FF9800", "#E65100"
            level = "HIGH"
        else:
            bg_color, bar_color, text_color = "#FFEBEE", "#F44336", "#C62828"
            level = "MODERATE"

        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {bar_color};
                border-radius: 8px;
            }}
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 10, 20, 10)

        # Similarity text
        similarity_text = QLabel(f"Similarity: {self.similarity:.1f}% ({level})")
        similarity_text.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        similarity_text.setStyleSheet(f"color: {text_color};")

        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setMaximumWidth(250)
        progress_bar.setMaximumHeight(28)
        progress_bar.setValue(int(self.similarity))
        progress_bar.setTextVisible(False)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {bar_color};
                border-radius: 14px;
                background-color: #F5F5F5;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 11px;
                margin: 2px;
            }}
        """)

        layout.addWidget(similarity_text)
        layout.addStretch()
        layout.addWidget(progress_bar)

        return frame

    def create_video_frame(self, label, video_path, color):
        """Create a frame for a video"""
        container = QFrame()
        container.setMinimumSize(600, 650)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 3px solid {color};
                border-radius: 15px;
            }}
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Title
        title = QLabel(f"VIDEO {label}")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {color}; padding: 6px;")
        title.setMaximumHeight(35)
        layout.addWidget(title)

        # Video widget
        video_widget = VideoPreviewWidget(video_path, f"Video {label}")
        layout.addWidget(video_widget)

        # Selection button
        select_btn = QPushButton(f"✅ CHOOSE {label}")
        select_btn.setMinimumHeight(60)
        select_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
                transform: scale(1.02);
            }}
        """)

        if label == "A":
            select_btn.clicked.connect(lambda: self.make_choice("keep_left"))
        else:
            select_btn.clicked.connect(lambda: self.make_choice("keep_right"))

        layout.addWidget(select_btn)

        return container, video_widget

    def create_navigation_controls(self):
        """Create navigation controls"""
        frame = QFrame()
        frame.setMaximumHeight(110)
        frame.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 2px solid #DEE2E6;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)

        # Title
        title = QLabel("🎹 Synchronized Navigation")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Slider with time zones
        slider_layout = QHBoxLayout()

        # Start time zone
        self.time_label = QLabel("0:00")
        self.time_label.setFixedWidth(70)
        self.time_label.setMinimumHeight(30)
        self.time_label.setFont(QFont("Arial", 12))
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("""
            QLabel {
                background-color: #FFFFFF;
                border: 1px solid #DDDDDD;
                border-radius: 5px;
                padding: 5px;
            }
        """)

        # Slider
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 1000)
        self.position_slider.setValue(0)
        self.position_slider.setMinimumHeight(30)
        self.position_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #CCCCCC;
                height: 8px;
                background: #F0F0F0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #007BFF;
                border: 1px solid #0056B3;
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: #0056B3;
            }
        """)
        self.position_slider.valueChanged.connect(self.on_slider_changed)

        # End time zone
        self.duration_label = QLabel("0:00")
        self.duration_label.setFixedWidth(70)
        self.duration_label.setMinimumHeight(30)
        self.duration_label.setFont(QFont("Arial", 12))
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.duration_label.setStyleSheet("""
            QLabel {
                background-color: #FFFFFF;
                border: 1px solid #DDDDDD;
                border-radius: 5px;
                padding: 5px;
            }
        """)

        slider_layout.addWidget(self.time_label)
        slider_layout.addWidget(self.position_slider)
        slider_layout.addWidget(self.duration_label)
        layout.addLayout(slider_layout)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(12)

        for label, pos in [("⏮️", 0), ("25%", 0.25), ("50%", 0.5), ("75%", 0.75), ("⏭️", 1.0)]:
            btn = QPushButton(label)
            btn.setFixedSize(70, 35)
            btn.setFont(QFont("Arial", 12))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #007BFF;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0056B3;
                }
                QPushButton:pressed {
                    background-color: #004085;
                }
            """)
            btn.clicked.connect(lambda checked, p=pos: self.seek_to_position(p))
            nav_layout.addWidget(btn)

        nav_layout.insertStretch(0)
        nav_layout.addStretch()
        layout.addLayout(nav_layout)

        return frame

    def create_action_buttons(self):
        """Create the 5 action buttons"""
        frame = QFrame()
        frame.setMaximumHeight(120)
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 2px solid #DDDDDD;
                border-radius: 10px;
                padding: 15px;
            }
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        # Keep A button - Green
        keep_a_btn = QPushButton("✅ KEEP A")
        keep_a_btn.setMinimumHeight(60)
        keep_a_btn.setMinimumWidth(160)
        keep_a_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745 !important;
                color: white !important;
                font-size: 14px;
                font-weight: bold;
                padding: 15px 20px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #218838 !important;
            }
            QPushButton:pressed {
                background-color: #1E7E34 !important;
            }
        """)
        keep_a_btn.clicked.connect(lambda: self.make_choice("keep_left"))

        # Keep B button - Orange
        keep_b_btn = QPushButton("✅ KEEP B")
        keep_b_btn.setMinimumHeight(60)
        keep_b_btn.setMinimumWidth(160)
        keep_b_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800 !important;
                color: white !important;
                font-size: 14px;
                font-weight: bold;
                padding: 15px 20px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #F57C00 !important;
            }
            QPushButton:pressed {
                background-color: #EF6C00 !important;
            }
        """)
        keep_b_btn.clicked.connect(lambda: self.make_choice("keep_right"))

        # Skip button - Blue
        skip_btn = QPushButton("⏭️ SKIP")
        skip_btn.setMinimumHeight(60)
        skip_btn.setMinimumWidth(160)
        skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #007BFF !important;
                color: white !important;
                font-size: 14px;
                font-weight: bold;
                padding: 15px 20px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0056B3 !important;
            }
            QPushButton:pressed {
                background-color: #004085 !important;
            }
        """)
        skip_btn.clicked.connect(lambda: self.make_choice("ignore_temp"))

        # Ignore permanently button - Red
        ignore_btn = QPushButton("❌ IGNORE")
        ignore_btn.setMinimumHeight(60)
        ignore_btn.setMinimumWidth(160)
        ignore_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC3545 !important;
                color: white !important;
                font-size: 14px;
                font-weight: bold;
                padding: 15px 20px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #C82333 !important;
            }
            QPushButton:pressed {
                background-color: #A71E2A !important;
            }
        """)
        ignore_btn.clicked.connect(lambda: self.make_choice("ignore_perm"))

        # Quit button - Dark gray
        quit_btn = QPushButton("🚪 QUIT")
        quit_btn.setMinimumHeight(60)
        quit_btn.setMinimumWidth(160)
        quit_btn.setStyleSheet("""
            QPushButton {
                background-color: #6C757D !important;
                color: white !important;
                font-size: 14px;
                font-weight: bold;
                padding: 15px 20px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #545B62 !important;
            }
            QPushButton:pressed {
                background-color: #454D55 !important;
            }
        """)
        quit_btn.clicked.connect(lambda: self.make_choice("quit"))

        layout.addWidget(keep_a_btn)
        layout.addWidget(keep_b_btn)
        layout.addWidget(skip_btn)
        layout.addWidget(ignore_btn)
        layout.addWidget(quit_btn)

        return frame

    def show_initial_position(self):
        """Show videos at 10%"""
        try:
            self.seek_to_position(0.1)
            logger.info("Initial position set to 10%")
        except Exception as e:
            logger.error(f"Error setting initial position: {e}")

    def on_slider_changed(self, value):
        """Handle slider change"""
        position = value / 1000.0
        self.sync_video_position(position)

    def seek_to_position(self, position):
        """Seek to a specific position"""
        self.position_slider.setValue(int(position * 1000))
        self.sync_video_position(position)

    def sync_video_position(self, position):
        """Synchronize both videos"""
        try:
            self.left_video.seek_to_position(position)
            self.right_video.seek_to_position(position)

            # Update time display
            duration_a = getattr(self.left_video, 'duration', 0)
            duration_b = getattr(self.right_video, 'duration', 0)
            max_duration = max(duration_a, duration_b)

            current_time = position * max_duration
            self.update_time_display(current_time, max_duration)

        except Exception as e:
            logger.error(f"Error synchronizing: {e}")

    def update_time_display(self, current_seconds, total_seconds):
        """Update time display"""
        self.time_label.setText(self.format_time(current_seconds))
        self.duration_label.setText(self.format_time(total_seconds))

    def format_time(self, seconds):
        """Format time"""
        if seconds >= 3600:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}:{secs:02d}"

    def make_choice(self, choice):
        """Record the choice"""
        self.result = choice

        # Quick animation according to choice with colors
        if choice == "keep_left":
            self.left_video.parentWidget().setStyleSheet("""
                QFrame {
                    background-color: #D4EDDA;
                    border: 4px solid #28A745;
                    border-radius: 15px;
                }
            """)
        elif choice == "keep_right":
            self.right_video.parentWidget().setStyleSheet("""
                QFrame {
                    background-color: #FFF3E0;
                    border: 4px solid #FF9800;
                    border-radius: 15px;
                }
            """)
        elif choice == "ignore_temp":
            # Blue animation for skip
            self.left_video.parentWidget().setStyleSheet("""
                QFrame {
                    background-color: #CCE5FF;
                    border: 4px solid #007BFF;
                    border-radius: 15px;
                }
            """)
            self.right_video.parentWidget().setStyleSheet("""
                QFrame {
                    background-color: #CCE5FF;
                    border: 4px solid #007BFF;
                    border-radius: 15px;
                }
            """)
        elif choice == "ignore_perm":
            # Red animation for ignore
            self.left_video.parentWidget().setStyleSheet("""
                QFrame {
                    background-color: #F8D7DA;
                    border: 4px solid #DC3545;
                    border-radius: 15px;
                }
            """)
            self.right_video.parentWidget().setStyleSheet("""
                QFrame {
                    background-color: #F8D7DA;
                    border: 4px solid #DC3545;
                    border-radius: 15px;
                }
            """)
        elif choice == "quit":
            # Quit immediately without animation
            self.reject()
            return

        # Shorter delay for other actions
        QTimer.singleShot(200, self.accept)

    def closeEvent(self, event):
        """Clean up resources"""
        try:
            self.left_video.cleanup()
            self.right_video.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")
        super().closeEvent(event)
