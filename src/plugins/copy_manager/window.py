"""Copy Manager window module.

This module contains the main window and worker thread for the Copy Manager plugin,
providing the user interface for copying folder structures with various options.
"""

import os
import json
import shutil
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                           QFileDialog, QLabel, QProgressBar, QTextEdit,
                           QCheckBox, QMessageBox, QGroupBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from src.core.logger import Logger
from src.core.i18n import t
from .copy_manager import CopyManager
from send2trash import send2trash

logger = Logger.get_logger('CopyManager')

class CopyManagerWindow(QDialog):
    """Main window for the Copy Manager plugin.

    Provides a user interface for copying folder structures with options to
    include/exclude files, preserve metadata, handle hidden files, and
    optionally delete source files after copying.

    Attributes:
        source_path (str): Path to the source folder to copy.
        dest_path (str): Path to the destination folder.
        copy_manager (CopyManager): Instance for handling copy operations.
        settings_file (str): Path to the JSON settings file.
        copy_thread (CopyThread): Worker thread for background copying.
    """

    def __init__(self):
        """Initialize the Copy Manager window.

        Sets up the UI, loads saved settings, and prepares the copy manager.
        """
        super().__init__()
        self.setWindowTitle(t("copy_manager.window.title", "Copy Manager"))
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        self.source_path = None
        self.dest_path = None
        self.copy_manager = CopyManager()
        self.settings_file = os.path.join("data", "copy_manager", "settings.json")

        # Create data folder if necessary
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        
        self.load_settings()
        self.init_ui()
    
    def init_ui(self):
        """Initialize user interface"""
        layout = QVBoxLayout()

        # Folder selection
        source_layout = QHBoxLayout()
        self.source_label = QLabel(t("copy_manager.window.source_unselected", "Source folder: Not selected"))
        if self.source_path:
            self.source_label.setText(
                t("copy_manager.window.source_selected", "Source folder: {path}", path=self.source_path)
            )
        self.source_button = QPushButton(t("copy_manager.window.select_source", "📁 Select source"))
        self.source_button.clicked.connect(self.select_source)
        source_layout.addWidget(self.source_label)
        source_layout.addWidget(self.source_button)

        dest_layout = QHBoxLayout()
        self.dest_label = QLabel(t("copy_manager.window.dest_unselected", "Destination folder: Not selected"))
        if self.dest_path:
            self.dest_label.setText(
                t("copy_manager.window.dest_selected", "Destination folder: {path}", path=self.dest_path)
            )
        self.dest_button = QPushButton(t("copy_manager.window.select_dest", "📁 Select destination"))
        self.dest_button.clicked.connect(self.select_dest)
        dest_layout.addWidget(self.dest_label)
        dest_layout.addWidget(self.dest_button)

        # Options
        options_group = QGroupBox(t("copy_manager.window.options", "Options"))
        options_layout = QVBoxLayout()

        self.copy_files_cb = QCheckBox(t("copy_manager.window.copy_files", "Copy files"))
        self.copy_files_cb.setChecked(True)  # Checked by default

        self.preserve_metadata_cb = QCheckBox(t("copy_manager.window.preserve_metadata", "Preserve metadata"))
        self.preserve_metadata_cb.setToolTip(
            t("copy_manager.window.preserve_metadata_tooltip", "Copy tags, comments, colors and other macOS metadata")
        )
        self.preserve_metadata_cb.setChecked(True)

        self.include_hidden_cb = QCheckBox(t("copy_manager.window.include_hidden", "Include hidden files"))
        self.include_hidden_cb.setToolTip(
            t("copy_manager.window.include_hidden_tooltip", "Include files and folders starting with a dot (.)")
        )

        self.delete_after_copy = QCheckBox(t("copy_manager.window.delete_after_copy", "Delete files after copy"))
        self.delete_after_copy.setToolTip(
            t("copy_manager.window.delete_after_copy_tooltip", "Source files will be moved to trash after copying")
        )
        
        options_layout.addWidget(self.copy_files_cb)
        options_layout.addWidget(self.preserve_metadata_cb)
        options_layout.addWidget(self.include_hidden_cb)
        options_layout.addWidget(self.delete_after_copy)
        
        options_group.setLayout(options_layout)
        layout.addLayout(source_layout)
        layout.addLayout(dest_layout)
        layout.addWidget(options_group)

        # Action buttons
        buttons_layout = QHBoxLayout()

        buttons_layout.addStretch()

        self.copy_btn = QPushButton(t("copy_manager.window.copy_action", "✨ Copy"))
        self.copy_btn.clicked.connect(self.start_copy)
        buttons_layout.addWidget(self.copy_btn)

        self.stop_btn = QPushButton(t("copy_manager.window.stop", "⏹️ Stop"))
        self.stop_btn.clicked.connect(self.stop_copy)
        self.stop_btn.setEnabled(False)
        buttons_layout.addWidget(self.stop_btn)

        self.close_btn = QPushButton(t("copy_manager.window.close", "❌ Close"))
        self.close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_btn)

        layout.addLayout(buttons_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Operations log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        self.setLayout(layout)

    def load_settings(self):
        """Load saved settings"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.source_path = settings.get('source_path')
                    self.dest_path = settings.get('dest_path')
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")

    def save_settings(self):
        """Save settings"""
        try:
            settings = {
                'source_path': self.source_path,
                'dest_path': self.dest_path
            }
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")

    def select_source(self):
        """Select source folder"""
        path = QFileDialog.getExistingDirectory(
            self,
            t("copy_manager.dialog.select_source", "Select source folder")
        )
        if path:
            self.source_path = path
            self.source_label.setText(
                t("copy_manager.window.source_selected", "Source folder: {path}", path=path)
            )
            self.update_copy_button()
            self.save_settings()

    def select_dest(self):
        """Select destination folder"""
        path = QFileDialog.getExistingDirectory(
            self,
            t("copy_manager.dialog.select_dest", "Select destination folder")
        )
        if path:
            self.dest_path = path
            self.dest_label.setText(
                t("copy_manager.window.dest_selected", "Destination folder: {path}", path=path)
            )
            self.update_copy_button()
            self.save_settings()

    def update_copy_button(self):
        """Enable copy button if both folders are selected"""
        self.copy_btn.setEnabled(bool(self.source_path is not None and self.dest_path is not None))

    def log_message(self, message):
        """Add a message to the operation log.

        Args:
            message (str): Message to display in the log text area.
        """
        self.log_text.append(message)

    def start_copy(self):
        """Start copying files"""
        if not self.source_path or not self.dest_path:
            QMessageBox.warning(
                self,
                t("copy_manager.dialog.error_title", "Error"),
                t("copy_manager.dialog.select_both", "Please select source and destination folders")
            )
            return

        # Disable controls during copy
        self.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Create and start copy thread
        self.copy_thread = CopyThread(
            self.source_path,
            self.dest_path,
            self.copy_files_cb.isChecked(),
            self.preserve_metadata_cb.isChecked(),
            self.include_hidden_cb.isChecked(),
            self.delete_after_copy.isChecked()
        )

        # Calculate total size
        total_size = self.copy_thread.copy_manager.calculate_total_size(self.source_path)
        self.log_message(
            t(
                "copy_manager.log.total_size",
                f"Total size to copy: {self.format_size(total_size)}",
                size=self.format_size(total_size)
            )
        )
        
        self.copy_thread.progress.connect(self.update_progress)
        self.copy_thread.message.connect(self.log_message)
        self.copy_thread.finished.connect(self.copy_finished)
        self.copy_thread.start()

    def format_size(self, size):
        """Format size in bytes to human-readable format.

        Args:
            size (int): Size in bytes to format.

        Returns:
            str: Formatted size string (e.g., "1.5 GB", "256.0 MB").
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def update_progress(self, value):
        """Update the progress bar.

        Args:
            value (int): Progress value (0-100).
        """
        self.progress_bar.setValue(value)

    def copy_finished(self):
        """Called when copy is finished"""
        self.copy_btn.setEnabled(True)
        self.log_message(t("copy_manager.log.copy_completed", "Copy completed"))
        QMessageBox.information(
            self,
            t("copy_manager.dialog.completed_title", "Completed"),
            t("copy_manager.dialog.copy_completed", "Copy completed")
        )
        self.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def add_files(self):
        pass

    def add_folder(self):
        pass

    def stop_copy(self):
        """Stop the ongoing copy operation."""
        if hasattr(self, 'copy_thread') and self.copy_thread and self.copy_thread.isRunning():
            self.copy_thread.stop()
            self.log_message(t("copy_manager.log.stopping", "Stopping copy operation..."))
        else:
            self.log_message(t("copy_manager.log.none_running", "No copy operation is currently running"))

class CopyThread(QThread):
    """Worker thread for background copy operations.

    Performs folder copying in a separate thread to keep the UI responsive.
    Emits signals for progress updates and log messages.

    Signals:
        progress (int): Emitted with progress percentage (0-100).
        message (str): Emitted with log messages to display.

    Attributes:
        source (str): Source folder path.
        dest (str): Destination folder path.
        copy_files (bool): Whether to copy files or just folder structure.
        preserve_metadata (bool): Whether to preserve macOS metadata.
        include_hidden (bool): Whether to include hidden files.
        delete_after_copy (bool): Whether to move source files to trash after copying.
        copy_manager (CopyManager): Instance for handling copy operations.
    """
    progress = pyqtSignal(int)
    message = pyqtSignal(str)

    def __init__(self, source, dest, copy_files, preserve_metadata, include_hidden, delete_after_copy):
        """Initialize the copy thread.

        Args:
            source (str): Source folder path.
            dest (str): Destination folder path.
            copy_files (bool): Whether to copy files.
            preserve_metadata (bool): Whether to preserve metadata.
            include_hidden (bool): Whether to include hidden files.
            delete_after_copy (bool): Whether to delete source files after copying.
        """
        super().__init__()
        self.source = source
        self.dest = dest
        self.copy_files = copy_files
        self.preserve_metadata = preserve_metadata
        self.include_hidden = include_hidden
        self.delete_after_copy = delete_after_copy
        self.copy_manager = CopyManager()
        self._stop_requested = False
    
    def run(self):
        """Execute the copy operation in the background.

        Walks through the source directory tree, creates the folder structure,
        and optionally copies files. Emits progress and message signals
        throughout the operation.
        """
        try:
            total_items = self.copy_manager.count_items(self.source)
            copied_items = 0

            for root, dirs, files in os.walk(self.source):
                # Check if stop was requested
                if self._stop_requested:
                    self.message.emit(
                        t("copy_manager.log.cancelled", "Copy operation cancelled by user")
                    )
                    return

                # Filter hidden files if necessary
                if not self.include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    files = [f for f in files if not f.startswith('.')]

                # Create destination folder
                rel_path = os.path.relpath(root, self.source)
                dest_root = os.path.join(self.dest, rel_path)

                if not os.path.exists(dest_root):
                    os.makedirs(dest_root)
                    if self.preserve_metadata:
                        self.copy_manager.copy_metadata(root, dest_root)
                    self.message.emit(
                        t("copy_manager.log.created_folder", f"Created folder: {dest_root}", path=dest_root)
                    )
                    copied_items += 1
                    self.progress.emit(int(copied_items * 100 / total_items))

                # Copy files if option is enabled
                if self.copy_files:
                    for file in files:
                        # Check if stop was requested
                        if self._stop_requested:
                            self.message.emit(
                                t("copy_manager.log.cancelled", "Copy operation cancelled by user")
                            )
                            return

                        src_file = os.path.join(root, file)
                        dest_file = os.path.join(dest_root, file)

                        # Check if file already exists
                        if os.path.exists(dest_file):
                            dest_file = self.copy_manager.get_unique_name(dest_file)

                        shutil.copy2(src_file, dest_file)
                        if self.preserve_metadata:
                            self.copy_manager.copy_metadata(src_file, dest_file)

                        self.message.emit(
                            t("copy_manager.log.copied_file", f"Copied: {dest_file}", path=dest_file)
                        )
                        copied_items += 1
                        self.progress.emit(int(copied_items * 100 / total_items))

                        # Delete source file if requested
                        if self.delete_after_copy:
                            send2trash(src_file)
                            self.message.emit(
                                t("copy_manager.log.deleted_file", f"Deleted: {src_file}", path=src_file)
                            )

        except Exception as e:
            self.message.emit(
                t("copy_manager.log.error", f"Error: {str(e)}", error=e)
            )
            logger.error(f"Error during copy: {str(e)}")

    def stop(self):
        """Request the copy operation to stop."""
        self._stop_requested = True
