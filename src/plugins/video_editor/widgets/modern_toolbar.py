"""Modern toolbar widget for Video Editor.

Provides a professional toolbar with icon buttons, tooltips,
and visual feedback similar to Adobe Premiere Pro.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel,
    QFrame, QSizePolicy, QToolButton, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon
from src.core.i18n import t


class ToolbarButton(QPushButton):
    """Modern styled button for toolbar."""

    def __init__(self, icon: str, text: str = "", tooltip: str = "", parent=None):
        """Initialize toolbar button.

        Args:
            icon: Emoji or icon text
            text: Button text (optional)
            tooltip: Tooltip text
            parent: Parent widget
        """
        super().__init__(parent)

        if text:
            self.setText(f"{icon} {text}")
        else:
            self.setText(icon)

        if tooltip:
            self.setToolTip(tooltip)

        self.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #353535;
                border: 1px solid #0078d4;
            }
            QPushButton:pressed {
                background-color: #404040;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #666;
                border: 1px solid #2a2a2a;
            }
        """)

        # Set size
        self.setMinimumHeight(36)


class PrimaryButton(ToolbarButton):
    """Primary action button with accent color."""

    def __init__(self, icon: str, text: str = "", tooltip: str = "", parent=None):
        """Initialize primary button.

        Args:
            icon: Emoji or icon text
            text: Button text
            tooltip: Tooltip text
            parent: Parent widget
        """
        super().__init__(icon, text, tooltip, parent)

        self.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: 1px solid #005a9e;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a9e;
                border: 1px solid #004578;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #666;
                border: 1px solid #2a2a2a;
            }
        """)


class SuccessButton(ToolbarButton):
    """Success/create button with green color."""

    def __init__(self, icon: str, text: str = "", tooltip: str = "", parent=None):
        """Initialize success button.

        Args:
            icon: Emoji or icon text
            text: Button text
            tooltip: Tooltip text
            parent: Parent widget
        """
        super().__init__(icon, text, tooltip, parent)

        self.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: 1px solid #1e7e34;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
                border: 1px solid #1e7e34;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #666;
                border: 1px solid #2a2a2a;
            }
        """)


class WarningButton(ToolbarButton):
    """Warning/export button with yellow/orange color."""

    def __init__(self, icon: str, text: str = "", tooltip: str = "", parent=None):
        """Initialize warning button.

        Args:
            icon: Emoji or icon text
            text: Button text
            tooltip: Tooltip text
            parent: Parent widget
        """
        super().__init__(icon, text, tooltip, parent)

        self.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #000;
                border: 1px solid #e0a800;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0a800;
                border: 1px solid #d39e00;
            }
            QPushButton:pressed {
                background-color: #d39e00;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #666;
                border: 1px solid #2a2a2a;
            }
        """)


class ToolbarSeparator(QFrame):
    """Vertical separator for toolbar."""

    def __init__(self, parent=None):
        """Initialize separator.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setStyleSheet("""
            QFrame {
                color: #3a3a3a;
                margin: 4px 8px;
            }
        """)


class ModernToolbar(QWidget):
    """Modern toolbar widget with grouped actions."""

    # Signals for main actions
    open_video_clicked = pyqtSignal()
    save_project_clicked = pyqtSignal()
    mark_in_clicked = pyqtSignal()
    mark_out_clicked = pyqtSignal()
    create_segment_clicked = pyqtSignal()
    export_clicked = pyqtSignal()
    undo_clicked = pyqtSignal()
    redo_clicked = pyqtSignal()
    cut_at_cursor_clicked = pyqtSignal()
    delete_segment_clicked = pyqtSignal()
    preferences_clicked = pyqtSignal()
    help_clicked = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize modern toolbar.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Set up the toolbar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        # Set background
        self.setStyleSheet("""
            ModernToolbar {
                background-color: #1e1e1e;
                border-bottom: 1px solid #3a3a3a;
            }
        """)

        # File operations group
        self.open_btn = PrimaryButton("📁", t("video_editor.toolbar.open", "Open"), t("video_editor.toolbar.tooltip_open", "Open a video (Ctrl+O)"))
        self.open_btn.clicked.connect(self.open_video_clicked.emit)
        layout.addWidget(self.open_btn)

        self.save_btn = ToolbarButton("💾", t("video_editor.toolbar.save", "Save"), t("video_editor.toolbar.tooltip_save", "Save project (Ctrl+S)"))
        self.save_btn.clicked.connect(self.save_project_clicked.emit)
        self.save_btn.setEnabled(False)
        layout.addWidget(self.save_btn)

        layout.addWidget(ToolbarSeparator())

        # Edit operations group
        self.undo_btn = ToolbarButton("↶", "", t("video_editor.toolbar.tooltip_undo", "Undo (Ctrl+Z)"))
        self.undo_btn.clicked.connect(self.undo_clicked.emit)
        self.undo_btn.setEnabled(False)
        layout.addWidget(self.undo_btn)

        self.redo_btn = ToolbarButton("↷", "", t("video_editor.toolbar.tooltip_redo", "Redo (Ctrl+Y)"))
        self.redo_btn.clicked.connect(self.redo_clicked.emit)
        self.redo_btn.setEnabled(False)
        layout.addWidget(self.redo_btn)

        layout.addWidget(ToolbarSeparator())

        # Marking group
        self.mark_in_btn = ToolbarButton("⬇", "IN", t("video_editor.toolbar.tooltip_mark_in", "Mark start (I)"))
        self.mark_in_btn.clicked.connect(self.mark_in_clicked.emit)
        self.mark_in_btn.setEnabled(False)
        layout.addWidget(self.mark_in_btn)

        self.mark_out_btn = ToolbarButton("⬆", "OUT", t("video_editor.toolbar.tooltip_mark_out", "Mark end (O)"))
        self.mark_out_btn.clicked.connect(self.mark_out_clicked.emit)
        self.mark_out_btn.setEnabled(False)
        layout.addWidget(self.mark_out_btn)

        self.create_segment_btn = SuccessButton("✂", t("video_editor.toolbar.create", "Create"), t("video_editor.toolbar.tooltip_create_segment", "Create segment (C)"))
        self.create_segment_btn.clicked.connect(self.create_segment_clicked.emit)
        self.create_segment_btn.setEnabled(False)
        layout.addWidget(self.create_segment_btn)

        layout.addWidget(ToolbarSeparator())

        # Segment operations
        self.cut_btn = ToolbarButton("🔪", t("video_editor.toolbar.cut", "Cut"), t("video_editor.toolbar.tooltip_cut", "Cut at cursor (X)"))
        self.cut_btn.clicked.connect(self.cut_at_cursor_clicked.emit)
        self.cut_btn.setEnabled(False)
        layout.addWidget(self.cut_btn)

        self.delete_btn = ToolbarButton("🗑", t("video_editor.toolbar.delete", "Delete"), t("video_editor.toolbar.tooltip_delete", "Delete segment (Delete)"))
        self.delete_btn.clicked.connect(self.delete_segment_clicked.emit)
        self.delete_btn.setEnabled(False)
        layout.addWidget(self.delete_btn)

        layout.addStretch()

        # Export and settings
        self.export_btn = WarningButton("💾", t("video_editor.toolbar.export", "Export"), t("video_editor.toolbar.tooltip_export", "Export segments (Ctrl+E)"))
        self.export_btn.clicked.connect(self.export_clicked.emit)
        self.export_btn.setEnabled(False)
        layout.addWidget(self.export_btn)

        layout.addWidget(ToolbarSeparator())

        self.prefs_btn = ToolbarButton("⚙", "", t("video_editor.toolbar.tooltip_prefs", "Preferences (Ctrl+,)"))
        self.prefs_btn.clicked.connect(self.preferences_clicked.emit)
        layout.addWidget(self.prefs_btn)

        self.help_btn = ToolbarButton("❓", "", t("video_editor.toolbar.tooltip_help", "Help (F1)"))
        self.help_btn.clicked.connect(self.help_clicked.emit)
        layout.addWidget(self.help_btn)

    def set_video_loaded(self, loaded: bool):
        """Enable/disable buttons based on video loaded state.

        Args:
            loaded: Whether a video is loaded
        """
        self.save_btn.setEnabled(loaded)
        self.mark_in_btn.setEnabled(loaded)
        self.mark_out_btn.setEnabled(loaded)
        self.cut_btn.setEnabled(loaded)

    def set_segments_exist(self, exist: bool):
        """Enable/disable buttons based on segments existence.

        Args:
            exist: Whether segments exist
        """
        self.export_btn.setEnabled(exist)
        self.delete_btn.setEnabled(exist)

    def set_can_create_segment(self, can_create: bool):
        """Enable/disable create segment button.

        Args:
            can_create: Whether a segment can be created
        """
        self.create_segment_btn.setEnabled(can_create)

    def set_undo_redo_state(self, can_undo: bool, can_redo: bool):
        """Set undo/redo button states.

        Args:
            can_undo: Whether undo is available
            can_redo: Whether redo is available
        """
        self.undo_btn.setEnabled(can_undo)
        self.redo_btn.setEnabled(can_redo)


class StatusBar(QWidget):
    """Modern status bar with indicators."""

    def __init__(self, parent=None):
        """Initialize status bar.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Set up status bar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 3, 10, 3)
        layout.setSpacing(15)

        self.setStyleSheet("""
            StatusBar {
                background-color: #1e1e1e;
                border-top: 1px solid #3a3a3a;
            }
        """)

        # Status message
        self.status_label = QLabel(t("video_editor.toolbar.status_ready", "Ready"))
        self.status_label.setStyleSheet("""
            color: #ccc;
            font-size: 12px;
        """)
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Video info
        self.video_info_label = QLabel("")
        self.video_info_label.setStyleSheet("""
            color: #888;
            font-size: 11px;
        """)
        layout.addWidget(self.video_info_label)

        # Segment count
        self.segment_count_label = QLabel("")
        self.segment_count_label.setStyleSheet("""
            color: #888;
            font-size: 11px;
        """)
        layout.addWidget(self.segment_count_label)

        # FPS indicator
        self.fps_label = QLabel("")
        self.fps_label.setStyleSheet("""
            color: #888;
            font-size: 11px;
        """)
        layout.addWidget(self.fps_label)

    def set_status(self, message: str, duration: int = 0):
        """Set status message.

        Args:
            message: Status message
            duration: Duration in milliseconds (0 = permanent)
        """
        self.status_label.setText(message)
        self.status_label.setStyleSheet("""
            color: #ccc;
            font-size: 12px;
        """)

        if duration > 0:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(duration, lambda: self.status_label.setText(t("video_editor.toolbar.status_ready", "Ready")))

    def set_error(self, message: str, duration: int = 5000):
        """Set error message.

        Args:
            message: Error message
            duration: Duration in milliseconds
        """
        self.status_label.setText(f"❌ {message}")
        self.status_label.setStyleSheet("""
            color: #ff4444;
            font-size: 12px;
            font-weight: bold;
        """)

        if duration > 0:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(duration, lambda: self.status_label.setText(t("video_editor.toolbar.status_ready", "Ready")))

    def set_success(self, message: str, duration: int = 3000):
        """Set success message.

        Args:
            message: Success message
            duration: Duration in milliseconds
        """
        self.status_label.setText(f"✅ {message}")
        self.status_label.setStyleSheet("""
            color: #28a745;
            font-size: 12px;
            font-weight: bold;
        """)

        if duration > 0:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(duration, lambda: self.status_label.setText(t("video_editor.toolbar.status_ready", "Ready")))

    def set_video_info(self, width: int, height: int, fps: float, duration: str):
        """Set video information display.

        Args:
            width: Video width
            height: Video height
            fps: Frame rate
            duration: Duration string
        """
        self.video_info_label.setText(f"📹 {width}x{height}")
        self.fps_label.setText(f"🎞 {fps:.2f} FPS • {duration}")

    def set_segment_count(self, count: int):
        """Set segment count display.

        Args:
            count: Number of segments
        """
        if count > 0:
            self.segment_count_label.setText(f"📋 {count} segment{'s' if count > 1 else ''}")
        else:
            self.segment_count_label.setText("")
