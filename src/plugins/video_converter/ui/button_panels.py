"""Button panel management for VideoConverter UI.

This module handles the creation and management of all button panels
in the VideoConverter window interface.
"""

from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QProgressBar
)
from typing import TYPE_CHECKING
import shutil
from pathlib import Path

from src.core.logger import Logger

if TYPE_CHECKING:
    from ..window import VideoConverterWindow

logger = Logger.get_logger('VideoConverter.ButtonPanels')


class ButtonPanelManager:
    """Manages button panels for the VideoConverter UI.

    Handles creation and configuration of all button panels including
    main controls, table controls, and action buttons.
    """

    def __init__(self, window: 'VideoConverterWindow'):
        """Initialize the button panel manager.

        Args:
            window: Parent VideoConverterWindow instance.
        """
        self.window = window

    def setup_header(self, layout: QVBoxLayout) -> None:
        """Setup the header with title and progress indicators.

        Args:
            layout: Parent layout to add header to.
        """
        header_layout = QHBoxLayout()

        # Title
        title_label = QLabel("🎬 Video Converter Pro")
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #2E86AB;"
        )
        header_layout.addWidget(title_label)

        # Global progress bar
        self.window.global_progress = QProgressBar()
        self.window.global_progress.setVisible(False)
        self.window.global_progress.setFormat("Overall progress: %p% (%v/%m)")
        header_layout.addWidget(self.window.global_progress)

        header_layout.addStretch()

        # Time estimation
        self.window.time_estimation_label = QLabel("")
        self.window.time_estimation_label.setStyleSheet(
            "color: #666; font-weight: bold;"
        )
        header_layout.addWidget(self.window.time_estimation_label)

        # Status label
        self.window.status_label = QLabel("Ready • Drag and drop files here")
        self.window.status_label.setStyleSheet("color: #666;")
        header_layout.addWidget(self.window.status_label)

        layout.addLayout(header_layout)

    def setup_main_buttons(self, layout: QVBoxLayout) -> None:
        """Setup main file operation buttons.

        Args:
            layout: Parent layout to add buttons to.
        """
        buttons_layout = QHBoxLayout()

        # Add files button
        self.window.add_files_btn = QPushButton("📁 Files (Ctrl+O)")
        self.window.add_files_btn.clicked.connect(self.window.add_files)
        self.window.add_files_btn.setToolTip(
            "Select video files to convert"
        )
        buttons_layout.addWidget(self.window.add_files_btn)

        # Add folder button
        self.window.add_folder_btn = QPushButton("📂 Folder (Ctrl+Shift+O)")
        self.window.add_folder_btn.clicked.connect(self.window.add_folder)
        self.window.add_folder_btn.setToolTip(
            "Scan folder for video files"
        )
        buttons_layout.addWidget(self.window.add_folder_btn)

        # Auto-discovery button
        self.window.discover_btn = QPushButton("🔍 Auto-Discovery")
        self.window.discover_btn.clicked.connect(self.window.start_discovery)
        self.window.discover_btn.setToolTip(
            "Automatic search in common folders"
        )
        buttons_layout.addWidget(self.window.discover_btn)

        # Filter button
        self.window.filter_btn = QPushButton("🔍 Filter")
        self.window.filter_btn.clicked.connect(self.window.filter_current_list)
        self.window.filter_btn.setToolTip("Apply current filters to list")
        buttons_layout.addWidget(self.window.filter_btn)

        buttons_layout.addStretch()

        # Disk space indicator
        self.window.disk_space_label = QLabel("")
        self.window.disk_space_label.setStyleSheet("color: #666; font-size: 11px;")
        buttons_layout.addWidget(self.window.disk_space_label)

        # Clear button
        self.window.clear_btn = QPushButton("🗑️ Clear (Ctrl+L)")
        self.window.clear_btn.clicked.connect(self.window.clear_files)
        self.window.clear_btn.setToolTip("Clear file list")
        buttons_layout.addWidget(self.window.clear_btn)

        layout.addLayout(buttons_layout)

        # Update disk space info
        self.update_disk_space_info()

    def setup_table_controls(self, layout: QVBoxLayout) -> None:
        """Setup table control buttons.

        Args:
            layout: Parent layout to add table controls to.
        """
        table_controls = QHBoxLayout()

        # Select all button
        self.window.select_all_btn = QPushButton("☑️ All (Ctrl+A)")
        self.window.select_all_btn.clicked.connect(self.window.toggle_select_all)
        table_controls.addWidget(self.window.select_all_btn)

        # Select converted button
        self.window.select_only_converted_btn = QPushButton("🔄 Converted")
        self.window.select_only_converted_btn.clicked.connect(
            self.window.select_only_converted_files
        )
        self.window.select_only_converted_btn.setToolTip(
            "Select only already converted files"
        )
        table_controls.addWidget(self.window.select_only_converted_btn)

        # Select new button
        self.window.select_only_new_btn = QPushButton("🆕 New")
        self.window.select_only_new_btn.clicked.connect(
            self.window.select_only_new_files
        )
        self.window.select_only_new_btn.setToolTip(
            "Select only unconverted files"
        )
        table_controls.addWidget(self.window.select_only_new_btn)

        # Remove selected button
        self.window.remove_selected_btn = QPushButton(
            "🗑️ Remove selection (Del)"
        )
        self.window.remove_selected_btn.clicked.connect(
            self.window.remove_selected_files
        )
        self.window.remove_selected_btn.setToolTip(
            "Remove selected files from list"
        )
        table_controls.addWidget(self.window.remove_selected_btn)

        table_controls.addStretch()

        # File count label
        self.window.file_count_label = QLabel("0 files")
        self.window.file_count_label.setStyleSheet("color: #666;")
        table_controls.addWidget(self.window.file_count_label)

        layout.addLayout(table_controls)

    def setup_action_buttons(self, layout: QVBoxLayout) -> None:
        """Setup main action buttons (settings, stats, conversion).

        Args:
            layout: Parent layout to add action buttons to.
        """
        action_layout = QHBoxLayout()

        # Settings button
        self.window.settings_btn = QPushButton("⚙️ Settings (Ctrl+,)")
        self.window.settings_btn.clicked.connect(
            self.window.show_advanced_settings
        )
        self.window.settings_btn.setToolTip("Open advanced settings")
        action_layout.addWidget(self.window.settings_btn)

        # Stats button
        self.window.stats_btn = QPushButton("📊 Stats")
        self.window.stats_btn.clicked.connect(self.window.show_stats)
        self.window.stats_btn.setToolTip("Show statistics")
        action_layout.addWidget(self.window.stats_btn)

        # Help button
        self.window.help_btn = QPushButton("❓ Help (F1)")
        self.window.help_btn.clicked.connect(self.window.show_help)
        self.window.help_btn.setToolTip("Show help")
        action_layout.addWidget(self.window.help_btn)

        action_layout.addStretch()

        # Start button
        self.window.start_btn = QPushButton("▶️ Start (F5)")
        self.window.start_btn.clicked.connect(self.window.start_conversion)
        self.window.start_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "font-weight: bold; }"
        )
        action_layout.addWidget(self.window.start_btn)

        # Pause button
        self.window.pause_btn = QPushButton("⏸️ Pause after current")
        self.window.pause_btn.clicked.connect(self.window.pause_after_current)
        self.window.pause_btn.setEnabled(False)
        self.window.pause_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; "
            "font-weight: bold; }"
        )
        self.window.pause_btn.setToolTip(
            "Stop new conversions but finish current ones"
        )
        action_layout.addWidget(self.window.pause_btn)

        # Stop button
        self.window.stop_btn = QPushButton("⏹️ Stop (Esc)")
        self.window.stop_btn.clicked.connect(self.window.stop_conversion)
        self.window.stop_btn.setEnabled(False)
        self.window.stop_btn.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; "
            "font-weight: bold; }"
        )
        action_layout.addWidget(self.window.stop_btn)

        layout.addLayout(action_layout)

    def update_disk_space_info(self) -> None:
        """Update disk space information display."""
        try:
            home_path = Path.home()
            total, used, free = shutil.disk_usage(home_path)

            free_gb = free / (1024**3)
            total_gb = total / (1024**3)
            percent_free = (free / total) * 100

            if percent_free < 10:
                color = "#d32f2f"  # Red
                icon = "⚠️"
            elif percent_free < 20:
                color = "#ff9800"  # Orange
                icon = "⚠️"
            else:
                color = "#4caf50"  # Green
                icon = "💾"

            self.window.disk_space_label.setText(f"{icon} {free_gb:.1f}GB free")
            self.window.disk_space_label.setStyleSheet(
                f"color: {color}; font-size: 11px; font-weight: bold;"
            )

        except Exception as e:
            logger.debug(f"Error reading disk space: {e}")
            self.window.disk_space_label.setText("💾 Space: N/A")
