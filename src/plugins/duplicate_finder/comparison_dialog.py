"""
Duplicate comparison dialog - Clean and professional version
"""

import os
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# Import video widget
try:
    from .video_preview_widget import VideoPreviewWidget
    from .design_system import Colors, Spacing, Typography, Styles
    from .keyboard_shortcuts import KeyboardShortcuts
except ImportError:
    from video_preview_widget import VideoPreviewWidget
    from design_system import Colors, Spacing, Typography, Styles
    from keyboard_shortcuts import KeyboardShortcuts

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

        # Keyboard shortcuts help (small banner at top)
        help_label = QLabel("💡 Shortcuts: 1=Keep A | 2=Keep B | 3=Both | S=Skip | I=Ignore | Esc=Quit | ←→=Navigate | Q/H/T=25%/50%/75% | P=Play Both | R=Re-sync")
        help_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XXS))
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_label.setStyleSheet(f"""
            background-color: {Colors.INFO_LIGHTER};
            color: {Colors.BLACK};
            padding: {Spacing.XS}px;
            border-radius: {Spacing.RADIUS_SM}px;
            border: 1px solid {Colors.INFO};
        """)
        layout.addWidget(help_label)

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

        # Synchronization controls
        sync_controls = self.create_sync_controls()
        layout.addWidget(sync_controls)

        # Action buttons
        action_buttons = self.create_action_buttons()
        layout.addWidget(action_buttons)

    def create_similarity_indicator(self):
        """Create the similarity indicator"""
        frame = QFrame()
        frame.setFixedHeight(60)

        # Color according to level
        if self.similarity >= 95:
            bg_color, bar_color, text_color = Colors.SUCCESS_LIGHTER, Colors.GREEN, Colors.GREEN_DARK
            level = "VERY HIGH"
        elif self.similarity >= 85:
            bg_color, bar_color, text_color = Colors.WARNING_LIGHTER, Colors.ORANGE, Colors.ORANGE_DARKER
            level = "HIGH"
        else:
            bg_color, bar_color, text_color = Colors.DANGER_LIGHTER, Colors.DANGER, Colors.DANGER_DARKER
            level = "MODERATE"

        frame.setStyleSheet(Styles.frame(
            bg_color=bg_color,
            border_color=bar_color,
            border_width=2,
            radius=Spacing.RADIUS_MD
        ))

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(Spacing.XXL, Spacing.MD, Spacing.XXL, Spacing.MD)

        # Similarity text
        similarity_text = QLabel(f"Similarity: {self.similarity:.1f}% ({level})")
        similarity_text.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XL, QFont.Weight.Bold))
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
                background-color: {Colors.GRAY_100};
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
        container.setStyleSheet(Styles.video_frame(color))

        layout = QVBoxLayout(container)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.LG)

        # Title
        title = QLabel(f"VIDEO {label}")
        title.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_LG, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {color}; padding: {Spacing.SM}px;")
        title.setMaximumHeight(35)
        layout.addWidget(title)

        # Video widget
        video_widget = VideoPreviewWidget(video_path, f"Video {label}")
        layout.addWidget(video_widget)

        # Selection button - determine hover/pressed colors
        if label == "A":
            hover_color = Colors.GREEN_DARK
            pressed_color = hover_color
            select_btn = QPushButton(f"✅ CHOOSE {label}")
            select_btn.clicked.connect(lambda: self.make_choice("keep_left"))
        else:
            hover_color = Colors.ORANGE_DARK
            pressed_color = Colors.ORANGE_DARKER
            select_btn = QPushButton(f"✅ CHOOSE {label}")
            select_btn.clicked.connect(lambda: self.make_choice("keep_right"))

        select_btn.setMinimumHeight(Spacing.BUTTON_HEIGHT_LG)
        select_btn.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_LG, QFont.Weight.Bold))
        select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: {Spacing.RADIUS_LG}px;
                padding: {Spacing.LG}px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
        """)

        layout.addWidget(select_btn)

        return container, video_widget

    def create_sync_controls(self):
        """Create video synchronization controls"""
        frame = QFrame()
        frame.setMaximumHeight(70)
        frame.setStyleSheet(Styles.frame(
            bg_color=Colors.PRIMARY_LIGHT,
            border_color=Colors.PRIMARY,
            border_width=2,
            radius=Spacing.RADIUS_MD
        ))

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(Spacing.XL, Spacing.MD, Spacing.XL, Spacing.MD)
        layout.setSpacing(Spacing.LG)

        # Sync info label
        sync_label = QLabel("🔄 Video Synchronization:")
        sync_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_MD, QFont.Weight.Bold))
        sync_label.setStyleSheet(f"color: {Colors.PRIMARY_DARKER};")
        layout.addWidget(sync_label)

        # Play both button
        play_both_btn = QPushButton("▶️ Play Both")
        play_both_btn.setMinimumWidth(140)
        play_both_btn.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_MD))
        play_both_btn.clicked.connect(self.play_both_videos)
        play_both_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                border-radius: {Spacing.RADIUS_MD}px;
                padding: {Spacing.MD}px {Spacing.LG}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.SUCCESS_DARK};
            }}
        """)
        layout.addWidget(play_both_btn)

        # Pause both button
        pause_both_btn = QPushButton("⏸️ Pause Both")
        pause_both_btn.setMinimumWidth(140)
        pause_both_btn.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_MD))
        pause_both_btn.clicked.connect(self.pause_both_videos)
        pause_both_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.WARNING};
                color: white;
                border: none;
                border-radius: {Spacing.RADIUS_MD}px;
                padding: {Spacing.MD}px {Spacing.LG}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.WARNING_DARK};
            }}
        """)
        layout.addWidget(pause_both_btn)

        # Sync position button
        sync_btn = QPushButton("🔄 Re-sync Position")
        sync_btn.setMinimumWidth(160)
        sync_btn.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_MD))
        sync_btn.clicked.connect(lambda: self.sync_video_position(self.position_slider.value() / 1000.0))
        sync_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.INFO};
                color: white;
                border: none;
                border-radius: {Spacing.RADIUS_MD}px;
                padding: {Spacing.MD}px {Spacing.LG}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.INFO_DARK};
            }}
        """)
        layout.addWidget(sync_btn)

        layout.addStretch()

        return frame

    def create_navigation_controls(self):
        """Create navigation controls"""
        frame = QFrame()
        frame.setMaximumHeight(110)
        frame.setStyleSheet(Styles.frame(
            bg_color=Colors.GRAY_50,
            border_color=Colors.BORDER_LIGHT,
            border_width=2,
            radius=Spacing.RADIUS_LG
        ))

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(Spacing.XXL, Spacing.LG, Spacing.XXL, Spacing.LG)
        layout.setSpacing(Spacing.LG)

        # Title
        title = QLabel("🎹 Synchronized Navigation")
        title.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_LG, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Slider with time zones
        slider_layout = QHBoxLayout()

        # Start time zone
        self.time_label = QLabel("0:00")
        self.time_label.setFixedWidth(70)
        self.time_label.setMinimumHeight(Spacing.INPUT_HEIGHT)
        self.time_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_MD))
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet(Styles.frame(
            bg_color=Colors.WHITE,
            border_color=Colors.BORDER_LIGHT,
            border_width=1,
            radius=Spacing.RADIUS_SM,
            padding=Spacing.XS
        ))

        # Slider
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 1000)
        self.position_slider.setValue(0)
        self.position_slider.setMinimumHeight(Spacing.INPUT_HEIGHT)
        self.position_slider.setStyleSheet(Styles.slider())
        self.position_slider.valueChanged.connect(self.on_slider_changed)

        # End time zone
        self.duration_label = QLabel("0:00")
        self.duration_label.setFixedWidth(70)
        self.duration_label.setMinimumHeight(Spacing.INPUT_HEIGHT)
        self.duration_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_MD))
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.duration_label.setStyleSheet(Styles.frame(
            bg_color=Colors.WHITE,
            border_color=Colors.BORDER_LIGHT,
            border_width=1,
            radius=Spacing.RADIUS_SM,
            padding=Spacing.XS
        ))

        slider_layout.addWidget(self.time_label)
        slider_layout.addWidget(self.position_slider)
        slider_layout.addWidget(self.duration_label)
        layout.addLayout(slider_layout)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(Spacing.LG)

        for label, pos in [("⏮️", 0), ("25%", 0.25), ("50%", 0.5), ("75%", 0.75), ("⏭️", 1.0)]:
            btn = QPushButton(label)
            btn.setFixedSize(70, 35)
            btn.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_MD))
            btn.setStyleSheet(Styles.button(
                bg_color=Colors.PRIMARY,
                hover_color=Colors.PRIMARY_DARK,
                pressed_color=Colors.PRIMARY_DARKER,
                height=35,
                radius=Spacing.RADIUS_SM
            ))
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
        frame.setStyleSheet(Styles.frame(
            bg_color=Colors.WHITE,
            border_color=Colors.BORDER_LIGHT,
            border_width=2,
            radius=Spacing.RADIUS_LG,
            padding=Spacing.XL
        ))

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(Spacing.XXL, Spacing.XL, Spacing.XXL, Spacing.XL)
        layout.setSpacing(Spacing.XL)

        # Keep A button - Green
        keep_a_btn = QPushButton("✅ KEEP A")
        keep_a_btn.setMinimumHeight(Spacing.BUTTON_HEIGHT_LG)
        keep_a_btn.setMinimumWidth(160)
        keep_a_btn.setStyleSheet(Styles.action_button(
            bg_color=Colors.SUCCESS,
            hover_color=Colors.SUCCESS_DARK,
            pressed_color=Colors.SUCCESS_DARKER
        ))
        keep_a_btn.clicked.connect(lambda: self.make_choice("keep_left"))

        # Keep B button - Orange
        keep_b_btn = QPushButton("✅ KEEP B")
        keep_b_btn.setMinimumHeight(Spacing.BUTTON_HEIGHT_LG)
        keep_b_btn.setMinimumWidth(160)
        keep_b_btn.setStyleSheet(Styles.action_button(
            bg_color=Colors.ORANGE,
            hover_color=Colors.ORANGE_DARK,
            pressed_color=Colors.ORANGE_DARKER
        ))
        keep_b_btn.clicked.connect(lambda: self.make_choice("keep_right"))

        # Skip button - Blue
        skip_btn = QPushButton("⏭️ SKIP")
        skip_btn.setMinimumHeight(Spacing.BUTTON_HEIGHT_LG)
        skip_btn.setMinimumWidth(160)
        skip_btn.setStyleSheet(Styles.action_button(
            bg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_DARK,
            pressed_color=Colors.PRIMARY_DARKER
        ))
        skip_btn.clicked.connect(lambda: self.make_choice("ignore_temp"))

        # Ignore permanently button - Red
        ignore_btn = QPushButton("❌ IGNORE")
        ignore_btn.setMinimumHeight(Spacing.BUTTON_HEIGHT_LG)
        ignore_btn.setMinimumWidth(160)
        ignore_btn.setStyleSheet(Styles.action_button(
            bg_color=Colors.DANGER,
            hover_color=Colors.DANGER_DARK,
            pressed_color=Colors.DANGER_DARKER
        ))
        ignore_btn.clicked.connect(lambda: self.make_choice("ignore_perm"))

        # Quit button - Dark gray
        quit_btn = QPushButton("🚪 QUIT")
        quit_btn.setMinimumHeight(Spacing.BUTTON_HEIGHT_LG)
        quit_btn.setMinimumWidth(160)
        quit_btn.setStyleSheet(Styles.action_button(
            bg_color=Colors.SECONDARY,
            hover_color=Colors.SECONDARY_DARK,
            pressed_color=Colors.SECONDARY_DARKER
        ))
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

    def play_both_videos(self):
        """Play both videos simultaneously"""
        try:
            # Sync position first to ensure they start at same point
            current_position = self.position_slider.value() / 1000.0
            self.sync_video_position(current_position)

            # Start playback on both (if VideoPreviewWidget has a play method)
            # Note: This is a placeholder - actual implementation depends on VideoPreviewWidget API
            logger.info("Play both videos requested (synchronization active)")

        except Exception as e:
            logger.error(f"Error playing both videos: {e}")

    def pause_both_videos(self):
        """Pause both videos simultaneously"""
        try:
            # Note: This is a placeholder - actual implementation depends on VideoPreviewWidget API
            logger.info("Pause both videos requested")

        except Exception as e:
            logger.error(f"Error pausing both videos: {e}")

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
            self.left_video.parentWidget().setStyleSheet(Styles.frame(
                bg_color=Colors.SUCCESS_LIGHT,
                border_color=Colors.SUCCESS,
                border_width=4,
                radius=Spacing.RADIUS_XL
            ))
        elif choice == "keep_right":
            self.right_video.parentWidget().setStyleSheet(Styles.frame(
                bg_color=Colors.ORANGE_LIGHTER,
                border_color=Colors.ORANGE,
                border_width=4,
                radius=Spacing.RADIUS_XL
            ))
        elif choice == "ignore_temp":
            # Blue animation for skip
            style = Styles.frame(
                bg_color=Colors.PRIMARY_LIGHT,
                border_color=Colors.PRIMARY,
                border_width=4,
                radius=Spacing.RADIUS_XL
            )
            self.left_video.parentWidget().setStyleSheet(style)
            self.right_video.parentWidget().setStyleSheet(style)
        elif choice == "ignore_perm":
            # Red animation for ignore
            style = Styles.frame(
                bg_color=Colors.DANGER_LIGHT,
                border_color=Colors.DANGER,
                border_width=4,
                radius=Spacing.RADIUS_XL
            )
            self.left_video.parentWidget().setStyleSheet(style)
            self.right_video.parentWidget().setStyleSheet(style)
        elif choice == "quit":
            # Quit immediately without animation
            self.reject()
            return

        # Shorter delay for other actions
        QTimer.singleShot(200, self.accept)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        key = event.key()

        # Action shortcuts
        if key == KeyboardShortcuts.COMPARISON_KEEP_LEFT:
            self.make_choice("keep_left")
        elif key == KeyboardShortcuts.COMPARISON_KEEP_RIGHT:
            self.make_choice("keep_right")
        elif key == KeyboardShortcuts.COMPARISON_KEEP_BOTH:
            self.make_choice("ignore_temp")  # Keep both = skip
        elif key == KeyboardShortcuts.COMPARISON_SKIP:
            self.make_choice("ignore_temp")
        elif key == KeyboardShortcuts.COMPARISON_IGNORE:
            self.make_choice("ignore_perm")
        elif key == KeyboardShortcuts.COMPARISON_QUIT:
            self.make_choice("quit")

        # Navigation shortcuts
        elif key == KeyboardShortcuts.NAV_START:
            self.seek_to_position(0.0)
        elif key == KeyboardShortcuts.NAV_END:
            self.seek_to_position(1.0)
        elif key == KeyboardShortcuts.NAV_QUARTER:
            self.seek_to_position(0.25)
        elif key == KeyboardShortcuts.NAV_HALF:
            self.seek_to_position(0.5)
        elif key == KeyboardShortcuts.NAV_THREE_QUARTERS:
            self.seek_to_position(0.75)
        elif key == KeyboardShortcuts.NAV_PREV:
            # Move back 5%
            current = self.position_slider.value() / 1000.0
            self.seek_to_position(max(0.0, current - 0.05))
        elif key == KeyboardShortcuts.NAV_NEXT:
            # Move forward 5%
            current = self.position_slider.value() / 1000.0
            self.seek_to_position(min(1.0, current + 0.05))

        # Synchronization shortcuts
        elif key == KeyboardShortcuts.SYNC_PLAY_BOTH:
            self.play_both_videos()
        elif key == KeyboardShortcuts.SYNC_PAUSE_BOTH:
            self.pause_both_videos()
        elif key == KeyboardShortcuts.SYNC_RESYNC:
            current_position = self.position_slider.value() / 1000.0
            self.sync_video_position(current_position)

        else:
            # Let parent handle other keys
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Clean up resources"""
        try:
            self.left_video.cleanup()
            self.right_video.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")
        super().closeEvent(event)
