"""Duplicate comparison dialog for side-by-side video comparison.

This module provides a maximized dialog for comparing two potentially duplicate videos
with synchronized playback, keyboard shortcuts, and intelligent file ordering.
"""

import os
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, QEvent
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
    """Side-by-side video comparison dialog with synchronized playback.

    Displays two videos side-by-side for visual comparison with:
    - Synchronized playback controls
    - Similarity indicator
    - Keyboard shortcuts for quick decisions
    - Intelligent file ordering (best file on left)
    - Video navigation (seek, play/pause)

    The dialog opens maximized and is modal to focus user attention.

    Attributes:
        file1: Path to first video file (left side)
        file2: Path to second video file (right side)
        similarity: Similarity percentage (0-100)
        result: User's choice ("keep_left", "keep_right", "keep_both", or None)
        left_video: VideoPreviewWidget for left video
        right_video: VideoPreviewWidget for right video

    Example:
        >>> dialog = ComparisonDialog('/path/video1.mp4', '/path/video2.mp4', 95.5)
        >>> result = dialog.exec()
        >>> if result == QDialog.DialogCode.Accepted:
        ...     choice = dialog.result  # "keep_left", "keep_right", or "keep_both"
    """

    def __init__(self, file1: str, file2: str, similarity: float, parent=None):
        """Initialize comparison dialog with two videos.

        Args:
            file1: Path to first video file
            file2: Path to second video file
            similarity: Similarity percentage (0-100)
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.file1 = file1
        self.file2 = file2
        self.similarity = similarity
        self.result = None

        # Arrange files intelligently
        self.arrange_files_by_name()

        self.setWindowTitle(f"Comparaison de doublons - Similarité : {self.similarity:.1f}%")

        # Open maximized
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.setModal(True)

        # Install event filter to intercept arrow keys before child widgets
        self.installEventFilter(self)

        self.setup_ui()

        # Show at 10% after a delay
        QTimer.singleShot(500, self.show_initial_position)

    def arrange_files_by_name(self):
        """Intelligently arrange files to place the smallest file on the left.

        Uses a priority system to determine file arrangement:
        1. Smaller file size on the left (PRIMARY - always wins)
        2. File without numbering/copy patterns (if sizes equal)
        3. Alphabetical order (as tie-breaker)

        The smallest file is placed on the left side.

        Note:
            Modifies self.file1 and self.file2 in place by swapping if needed.
        """
        try:
            file1_name = os.path.basename(self.file1)
            file2_name = os.path.basename(self.file2)

            # Get file sizes
            try:
                file1_size = os.path.getsize(self.file1)
                file2_size = os.path.getsize(self.file2)
            except (OSError, FileNotFoundError) as e:
                logger.warning(f"Impossible d'obtenir la taille des fichiers: {e}")
                file1_size = file2_size = 0

            # Priority 1: SMALLEST file on the left (if sizes are different)
            if file1_size > 0 and file2_size > 0 and file1_size != file2_size:
                if file1_size > file2_size:
                    self.file1, self.file2 = self.file2, self.file1
                    logger.info(f"Swapped: smaller file now on left")
            else:
                # Only use pattern/name logic if sizes are equal or unavailable
                # Numbering/copy patterns
                patterns = [r'\(\d+\)', r'_\d+', r' - Copy', r'Copy of ', r'Copy de ', r'copie']

                file1_has_pattern = any(re.search(pattern, file1_name, re.IGNORECASE) for pattern in patterns)
                file2_has_pattern = any(re.search(pattern, file2_name, re.IGNORECASE) for pattern in patterns)

                # Priority 2: File without numbering/copy pattern on the left
                if file1_has_pattern and not file2_has_pattern:
                    self.file1, self.file2 = self.file2, self.file1
                elif file1_has_pattern == file2_has_pattern:
                    # Priority 3: Alphabetical order
                    if file1_name > file2_name:
                        self.file1, self.file2 = self.file2, self.file1

            logger.info(f"Files arranged: LEFT={os.path.basename(self.file1)} ({file1_size/1024/1024:.1f}MB), "
                       f"RIGHT={os.path.basename(self.file2)} ({file2_size/1024/1024:.1f}MB)")

        except Exception as e:
            logger.error(f"Error arranging files: {e}")

    def setup_ui(self):
        """Configure the comparison dialog user interface.

        Creates the complete UI layout with:
        - Similarity indicator at the top
        - Side-by-side video frames (left and right)
        - Navigation controls (slider, time display)
        - Action buttons (Keep Left, Keep Right, Keep Both, Cancel)

        Videos are displayed with colored borders (green for left, orange for right).
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Marges supprimées
        layout.setSpacing(5)  # Espacement minimal

        # Zone 1 supprimée - plus de bannière d'aide

        # Similarity indicator
        similarity_frame = self.create_similarity_indicator()
        layout.addWidget(similarity_frame)

        # Main comparison area
        comparison_layout = QHBoxLayout()
        comparison_layout.setContentsMargins(15, 0, 15, 0)  # Marges gauche/droite pour zones 3 et 4
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

        # Synchronization controls - SUPPRIMÉ (zone 12 inutile)
        # sync_controls = self.create_sync_controls()
        # layout.addWidget(sync_controls)

        # Action buttons
        action_buttons = self.create_action_buttons()
        layout.addWidget(action_buttons)

    def create_similarity_indicator(self):
        """Create the similarity indicator"""
        frame = QFrame()
        frame.setFixedHeight(20)  # Divisé par 3 (60 -> 20)

        # Color according to level
        if self.similarity >= 95:
            text_color = Colors.GREEN_DARK
            level = "TRÈS ÉLEVÉE"
        elif self.similarity >= 85:
            text_color = Colors.ORANGE_DARKER
            level = "ÉLEVÉE"
        else:
            text_color = Colors.DANGER_DARKER
            level = "MODÉRÉE"

        # Pas de style de frame - juste un container transparent
        frame.setStyleSheet("background: transparent; border: none;")

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        # Similarity text - TEXTE SIMPLE SANS OVALE/CADRE
        similarity_text = QLabel(f"Similarité : {self.similarity:.1f}% ({level})")
        similarity_text.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XL, QFont.Weight.Bold))
        similarity_text.setStyleSheet(f"""
            color: {text_color};
            background: transparent;
            padding: 0px;
            margin: 0px;
            border: none;
        """)
        similarity_text.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(similarity_text)

        return frame

    def create_video_frame(self, label, video_path, color):
        """Create a frame for a video"""
        container = QFrame()
        container.setMinimumSize(600, 700)  # Augmenté de 50px pour vidéo (650 → 700)
        container.setMaximumHeight(700)  # Force la hauteur maximale
        # Bordure colorée autour de la zone comme demandé
        container.setStyleSheet(Styles.video_frame(color))

        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)  # Marges forcées autour du contenu
        layout.setSpacing(5)  # Petit espacement entre éléments

        # Video label (Video A / Video B) - Centré
        import os
        video_label = QLabel(f"Vidéo {label}")
        video_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_LG + 2, QFont.Weight.Bold))  # +2px
        video_label.setMaximumHeight(14)  # Augmenté pour le texte plus grand
        video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Centré
        video_label.setStyleSheet(f"""
            color: {Colors.BLACK};
            background: transparent;
            padding: 0px;
            margin: 0px;
            border: none;
            border-radius: 0px;
        """)
        layout.addWidget(video_label)

        # Video path - Centré, taille +4px, multi-lignes si long
        path_label = QLabel(video_path)
        path_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_SM + 4))  # +4px (était +2)
        path_label.setMaximumHeight(45)  # Augmenté pour texte plus grand
        path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Centré
        path_label.setStyleSheet(f"""
            color: {Colors.GRAY_600};
            background: transparent;
            padding: 0px;
            margin: 0px;
            border: none;
            border-radius: 0px;
        """)
        path_label.setWordWrap(True)  # Permet le retour à la ligne
        layout.addWidget(path_label)

        # Video size - Hauteur réduite, AUCUN ovale
        try:
            size_bytes = os.path.getsize(video_path)
            if size_bytes >= 1_000_000_000:
                size_str = f"{size_bytes / 1_000_000_000:.2f} GB"
            else:
                size_str = f"{size_bytes / 1_000_000:.2f} MB"
        except (OSError, FileNotFoundError) as e:
            logger.warning(f"Cannot get file size for {video_path}: {e}")
            size_str = "Taille inconnue"

        size_label = QLabel(f"Taille : {size_str}")
        size_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_SM + 4))  # +4px (était +2)
        size_label.setMaximumHeight(14)  # Augmenté pour texte plus grand
        size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Centré
        size_label.setStyleSheet(f"""
            color: {Colors.GRAY_600};
            background: transparent;
            padding: 0px;
            margin: 0px;
            border: none;
            border-radius: 0px;
        """)
        layout.addWidget(size_label)

        # Video widget
        video_widget = VideoPreviewWidget(video_path, f"Video {label}")
        layout.addWidget(video_widget)

        # Pas de bouton de sélection sous la vidéo - supprimé comme demandé

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
        sync_label = QLabel("🔄 Synchronisation vidéo :")
        sync_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_MD, QFont.Weight.Bold))
        sync_label.setStyleSheet(f"color: {Colors.PRIMARY_DARKER};")
        layout.addWidget(sync_label)

        # Play both button
        play_both_btn = QPushButton("▶️ Lire les deux")
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
        pause_both_btn = QPushButton("⏸️ Pause les deux")
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
        sync_btn = QPushButton("🔄 Re-synchroniser")
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
        frame.setMaximumHeight(80)  # Réduit car pas de titre
        # Pas de bordure/ovale - transparent
        frame.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        # Titre supprimé comme demandé

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
            btn.setFixedSize(50, 28)  # Réduit de 70x35 à 50x28
            btn.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_SM))  # Police plus petite
            btn.setStyleSheet(Styles.button(
                bg_color=Colors.PRIMARY,
                hover_color=Colors.PRIMARY_DARK,
                pressed_color=Colors.PRIMARY_DARKER,
                height=28,
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
        frame.setMaximumHeight(140)  # Augmenté pour voir boutons avec marges (110 -> 140)
        frame.setStyleSheet(Styles.frame(
            bg_color=Colors.WHITE,
            border_color=Colors.BORDER_LIGHT,
            border_width=2,
            radius=Spacing.RADIUS_LG,
            padding=Spacing.SM
        ))

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)  # Marges forcées entre boutons et cadre
        layout.setSpacing(10)  # Espacement entre boutons

        # Keep A button - Green
        keep_a_btn = QPushButton("✅ CONSERVER A (1 ou ←)")
        keep_a_btn.setMinimumHeight(45)  # Augmenté proportionnellement
        keep_a_btn.setMinimumWidth(180)  # Plus large pour le raccourci
        keep_a_btn.setStyleSheet(Styles.action_button(
            bg_color=Colors.SUCCESS,
            hover_color=Colors.SUCCESS_DARK,
            pressed_color=Colors.SUCCESS_DARKER
        ))
        keep_a_btn.clicked.connect(lambda: self.make_choice("keep_left"))

        # Keep B button - Orange
        keep_b_btn = QPushButton("✅ CONSERVER B (2 ou →)")
        keep_b_btn.setMinimumHeight(45)  # Augmenté proportionnellement
        keep_b_btn.setMinimumWidth(180)  # Plus large pour le raccourci
        keep_b_btn.setStyleSheet(Styles.action_button(
            bg_color=Colors.ORANGE,
            hover_color=Colors.ORANGE_DARK,
            pressed_color=Colors.ORANGE_DARKER
        ))
        keep_b_btn.clicked.connect(lambda: self.make_choice("keep_right"))

        # Skip button - Blue
        skip_btn = QPushButton("⏭️ PASSER (S)")
        skip_btn.setMinimumHeight(45)  # Augmenté proportionnellement
        skip_btn.setMinimumWidth(130)
        skip_btn.setStyleSheet(Styles.action_button(
            bg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_DARK,
            pressed_color=Colors.PRIMARY_DARKER
        ))
        skip_btn.clicked.connect(lambda: self.make_choice("ignore_temp"))

        # Ignore permanently button - Red
        ignore_btn = QPushButton("❌ IGNORER (I)")
        ignore_btn.setMinimumHeight(45)  # Augmenté proportionnellement
        ignore_btn.setMinimumWidth(130)
        ignore_btn.setStyleSheet(Styles.action_button(
            bg_color=Colors.DANGER,
            hover_color=Colors.DANGER_DARK,
            pressed_color=Colors.DANGER_DARKER
        ))
        ignore_btn.clicked.connect(lambda: self.make_choice("ignore_perm"))

        # Quit button - Dark gray
        quit_btn = QPushButton("🚪 QUITTER (Esc)")
        quit_btn.setMinimumHeight(45)  # Augmenté proportionnellement
        quit_btn.setMinimumWidth(140)
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
        """Show both videos at 10% position for initial comparison.

        Called after a 500ms delay to allow UI to fully render.
        Shows videos at 10% rather than 0% to avoid black frames at start.
        """
        try:
            self.seek_to_position(0.1)
            logger.info("Initial position set to 10%")
        except Exception as e:
            logger.error(f"Error setting initial position: {e}")

    def on_slider_changed(self, value):
        """Handle position slider value change event.

        Args:
            value: Slider value (0-1000, representing 0-100% position)

        Note:
            Converts slider value to 0.0-1.0 range and syncs both videos.
        """
        position = value / 1000.0
        self.sync_video_position(position)

    def seek_to_position(self, position):
        """Seek both videos to a specific relative position.

        Args:
            position: Relative position (0.0 = start, 1.0 = end)

        Note:
            Updates slider and calls sync_video_position() to move both videos.
        """
        self.position_slider.setValue(int(position * 1000))
        self.sync_video_position(position)

    def sync_video_position(self, position):
        """Synchronize both videos to the same relative position.

        Seeks both left and right videos to the specified position and updates
        the time display. Uses the longest video duration for time calculation.

        Args:
            position: Relative position (0.0 = start, 1.0 = end)

        Example:
            >>> dialog.sync_video_position(0.5)  # Seek to 50% position
        """
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
        """Play both videos simultaneously from current position.

        Synchronizes position before starting playback to ensure both videos
        start at exactly the same point.

        Note:
            Actual playback depends on VideoPreviewWidget API support.
        """
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
        """Pause both videos simultaneously.

        Note:
            Actual pause depends on VideoPreviewWidget API support.
        """
        try:
            # Note: This is a placeholder - actual implementation depends on VideoPreviewWidget API
            logger.info("Pause both videos requested")

        except Exception as e:
            logger.error(f"Error pausing both videos: {e}")

    def update_time_display(self, current_seconds, total_seconds):
        """Update the time and duration labels.

        Args:
            current_seconds: Current playback time in seconds
            total_seconds: Total video duration in seconds
        """
        self.time_label.setText(self.format_time(current_seconds))
        self.duration_label.setText(self.format_time(total_seconds))

    def format_time(self, seconds):
        """Format seconds as human-readable time string.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string (MM:SS or H:MM:SS if >= 1 hour)

        Example:
            >>> format_time(65)
            "1:05"
            >>> format_time(3665)
            "1:01:05"
        """
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
        """Record user's decision about which video(s) to keep.

        Args:
            choice: User's decision ("keep_left", "keep_right", or "keep_both")

        Note:
            Sets self.result and closes the dialog with Accepted code.
        """
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

    def eventFilter(self, obj, event):
        """Filter events to intercept arrow keys before child widgets"""
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()

            # Intercept bare arrow keys for Tinder-style choosing
            if modifiers == Qt.KeyboardModifier.NoModifier:
                if key == Qt.Key.Key_Left:
                    self.make_choice("keep_left")
                    return True  # Event handled, don't propagate
                elif key == Qt.Key.Key_Right:
                    self.make_choice("keep_right")
                    return True  # Event handled, don't propagate

            # Let Ctrl+Arrow keys pass through to keyPressEvent for navigation

        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        key = event.key()
        modifiers = event.modifiers()

        # Number keys for choosing
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

        # Navigation shortcuts (with Ctrl modifier for arrow keys)
        elif key == Qt.Key.Key_Left and modifiers == Qt.KeyboardModifier.ControlModifier:
            # Move back 5% with Ctrl+Left
            current = self.position_slider.value() / 1000.0
            self.seek_to_position(max(0.0, current - 0.05))
        elif key == Qt.Key.Key_Right and modifiers == Qt.KeyboardModifier.ControlModifier:
            # Move forward 5% with Ctrl+Right
            current = self.position_slider.value() / 1000.0
            self.seek_to_position(min(1.0, current + 0.05))
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
