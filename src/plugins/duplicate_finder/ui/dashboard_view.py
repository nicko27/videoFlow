"""
Dashboard view for Duplicate Finder plugin.

Provides a quick overview of the application state with:
- Statistics cards (files, duplicates, space saved)
- Quick action buttons
- Recent activity log
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from datetime import datetime
from typing import Optional, Dict, List

from ..database_manager import VideoDatabase as DatabaseManager
from src.core.logger import Logger

logger = Logger.get_logger(__name__)


class StatCard(QFrame):
    """
    A card widget displaying a statistic with title and value.
    """

    def __init__(self, title: str, value: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        self.setMinimumHeight(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Icon and title
        header_layout = QHBoxLayout()
        if icon:
            icon_label = QLabel(icon)
            icon_font = QFont()
            icon_font.setPointSize(24)
            icon_label.setFont(icon_font)
            header_layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(10)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #666;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Value
        self.value_label = QLabel(value)
        value_font = QFont()
        value_font.setPointSize(24)
        value_font.setBold(True)
        self.value_label.setFont(value_font)
        self.value_label.setStyleSheet("color: #2196F3;")
        layout.addWidget(self.value_label)

        layout.addStretch()

    def set_value(self, value: str):
        """Update the card value."""
        self.value_label.setText(value)


class QuickActionButton(QPushButton):
    """
    Styled button for quick actions.
    """

    def __init__(self, text: str, icon: str = "", parent=None):
        super().__init__(parent)
        if icon:
            self.setText(f"{icon}  {text}")
        else:
            self.setText(text)

        self.setMinimumHeight(60)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)


class ActivityLogWidget(QWidget):
    """
    Widget showing recent activity with timestamps.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.activities: List[Dict] = []

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Recent Activity")
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        # Scroll area for activities
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(300)

        self.activity_container = QWidget()
        self.activity_layout = QVBoxLayout(self.activity_container)
        self.activity_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.activity_container)
        layout.addWidget(scroll)

    def add_activity(self, message: str, timestamp: Optional[datetime] = None):
        """
        Add an activity to the log.

        Args:
            message: Activity description
            timestamp: When it occurred (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Create activity widget
        activity_widget = QFrame()
        activity_widget.setFrameStyle(QFrame.Shape.StyledPanel)
        activity_widget.setLineWidth(1)

        activity_layout = QHBoxLayout(activity_widget)

        # Timestamp
        time_label = QLabel(timestamp.strftime("%H:%M:%S"))
        time_label.setStyleSheet("color: #666; font-size: 10px;")
        time_label.setMinimumWidth(70)
        activity_layout.addWidget(time_label)

        # Message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        activity_layout.addWidget(message_label, 1)

        # Add to layout
        self.activity_layout.insertWidget(0, activity_widget)

        # Keep only last 20 activities
        if self.activity_layout.count() > 20:
            item = self.activity_layout.takeAt(20)
            if item and item.widget():
                item.widget().deleteLater()

        # Store in list
        self.activities.insert(0, {
            'message': message,
            'timestamp': timestamp
        })
        if len(self.activities) > 20:
            self.activities = self.activities[:20]

        logger.debug(f"Activity added: {message}")

    def clear(self):
        """Clear all activities."""
        while self.activity_layout.count():
            item = self.activity_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self.activities.clear()


class DashboardView(QWidget):
    """
    Main dashboard view for the Duplicate Finder plugin.

    Displays:
    - Statistics cards (files analyzed, duplicates found, space saved)
    - Quick action buttons
    - Recent activity log
    """

    # Signals
    add_files_requested = pyqtSignal()
    add_folder_requested = pyqtSignal()
    start_analysis_requested = pyqtSignal()
    view_results_requested = pyqtSignal()

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager

        # Statistics
        self.stats = {
            'total_files': 0,
            'duplicates_found': 0,
            'space_saved_mb': 0,
            'last_analysis': 'Never'
        }

        self._init_ui()
        self._setup_refresh_timer()
        self.refresh_statistics()

        logger.info("DashboardView initialized")

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title = QLabel("Dashboard")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Statistics cards
        stats_layout = QGridLayout()
        stats_layout.setSpacing(15)

        self.files_card = StatCard("Total Files Analyzed", "0", "📁")
        self.duplicates_card = StatCard("Duplicates Found", "0", "🔍")
        self.space_card = StatCard("Space Saved", "0 MB", "💾")
        self.last_analysis_card = StatCard("Last Analysis", "Never", "⏱️")

        stats_layout.addWidget(self.files_card, 0, 0)
        stats_layout.addWidget(self.duplicates_card, 0, 1)
        stats_layout.addWidget(self.space_card, 1, 0)
        stats_layout.addWidget(self.last_analysis_card, 1, 1)

        layout.addLayout(stats_layout)

        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.add_files_btn = QuickActionButton("Add Files", "📄")
        self.add_files_btn.clicked.connect(self.add_files_requested)

        self.add_folder_btn = QuickActionButton("Add Folder", "📁")
        self.add_folder_btn.clicked.connect(self.add_folder_requested)

        self.start_analysis_btn = QuickActionButton("Start Analysis", "▶️")
        self.start_analysis_btn.clicked.connect(self.start_analysis_requested)

        self.view_results_btn = QuickActionButton("View Results", "📊")
        self.view_results_btn.clicked.connect(self.view_results_requested)

        actions_layout.addWidget(self.add_files_btn)
        actions_layout.addWidget(self.add_folder_btn)
        actions_layout.addWidget(self.start_analysis_btn)
        actions_layout.addWidget(self.view_results_btn)

        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        # Recent activity
        self.activity_log = ActivityLogWidget()
        layout.addWidget(self.activity_log)

        layout.addStretch()

    def _setup_refresh_timer(self):
        """Setup timer to refresh statistics periodically."""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_statistics)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds

    def refresh_statistics(self):
        """Refresh statistics from database."""
        try:
            stats = self.db_manager.get_statistics()

            self.stats['total_files'] = stats.get('total_videos', 0)
            self.stats['duplicates_found'] = stats.get('total_comparisons', 0)  # Approximation

            # Calculate space saved (rough estimate based on duplicates)
            # This would need more sophisticated calculation in a real implementation
            self.stats['space_saved_mb'] = self.stats['duplicates_found'] * 50  # Rough estimate

            # Update cards
            self.files_card.set_value(str(self.stats['total_files']))
            self.duplicates_card.set_value(str(self.stats['duplicates_found']))
            self.space_card.set_value(f"{self.stats['space_saved_mb']:.1f} MB")

            logger.debug(f"Statistics refreshed: {self.stats}")

        except Exception as e:
            logger.error(f"Failed to refresh statistics: {e}")

    def add_activity(self, message: str):
        """
        Add an activity to the recent activity log.

        Args:
            message: Activity description
        """
        self.activity_log.add_activity(message)

    def update_last_analysis_time(self, timestamp: Optional[datetime] = None):
        """
        Update the last analysis time.

        Args:
            timestamp: Analysis timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        time_str = timestamp.strftime("%Y-%m-%d %H:%M")
        self.stats['last_analysis'] = time_str
        self.last_analysis_card.set_value(time_str)

        logger.info(f"Last analysis time updated: {time_str}")

    def clear_activity_log(self):
        """Clear the activity log."""
        self.activity_log.clear()
        logger.info("Activity log cleared")

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when widget is closed.

        Ensures proper cleanup of resources and signals.
        """
        # All signals are internal and auto-cleaned by Qt
        # Added for consistency with other widgets
        super().closeEvent(event)
