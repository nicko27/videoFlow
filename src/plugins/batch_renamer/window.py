"""Main window for Batch Renamer plugin with enhanced features."""

import os
import cv2
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QTableWidget, QTableWidgetItem, QComboBox,
    QLineEdit, QCheckBox, QGroupBox, QMessageBox, QHeaderView,
    QTextEdit, QProgressBar, QDialog, QDialogButtonBox, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QColor
from src.core.logger import Logger
from src.core.i18n import t
from .pattern_parser import PatternParser, FindReplaceProcessor
from .advanced_pattern_parser import AdvancedPatternParser
from .renamer import RenameEngine
from .enhanced_renamer import EnhancedRenameEngine
from .pattern_manager import PatternManager
from .pattern_dialog import PatternManagementDialog
from .metadata_worker import MetadataExtractionWorker, PatternDetectionWorker

logger = Logger.get_logger('BatchRenamer.Window')


class BatchRenamerWindow(QMainWindow):
    """
    Enhanced Batch Renamer window.

    New Features:
    - Drag & drop support
    - Advanced pattern parser with conditions
    - Multi-threaded metadata extraction
    - Undo/Redo support
    - Dry-run mode
    - Progress bars
    - Transaction logging
    """

    closed = pyqtSignal()

    def __init__(self):
        """Initialize the Batch Renamer window."""
        super().__init__()
        self.setWindowTitle(t("batch_renamer.window.title", "🏷️ Batch Renamer - Enhanced"))
        self.setMinimumSize(1200, 800)

        # Enable drag and drop
        self.setAcceptDrops(True)

        # File list
        self.files = []
        self.metadata_cache = {}

        # Engines
        self.pattern_parser = PatternParser()  # Basic parser
        self.advanced_parser = AdvancedPatternParser()  # Advanced parser
        self.renamer = RenameEngine()  # Basic renamer
        self.enhanced_renamer = EnhancedRenameEngine()  # Enhanced renamer with redo
        self.pattern_manager = PatternManager()

        # Use advanced engines by default
        self.use_advanced_patterns = True
        self.active_renamer = self.enhanced_renamer

        # Worker thread
        self.metadata_worker = None

        self.init_ui()
        logger.info("Batch Renamer window initialized")

    def init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Title
        title = QLabel(t("batch_renamer.window.header", "Batch Renamer"))
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title)

        # File management buttons
        file_buttons = QHBoxLayout()

        add_files_btn = QPushButton(t("batch_renamer.window.add_files", "📁 Add Files"))
        add_files_btn.clicked.connect(self.add_files)
        file_buttons.addWidget(add_files_btn)

        add_folder_btn = QPushButton(t("batch_renamer.window.add_folder", "📂 Add Folder"))
        add_folder_btn.clicked.connect(self.add_folder)
        file_buttons.addWidget(add_folder_btn)

        # Include subfolders checkbox
        self.include_subfolders_check = QCheckBox(
            t("batch_renamer.window.include_subfolders", "Include Subfolders")
        )
        self.include_subfolders_check.setChecked(True)
        self.include_subfolders_check.setToolTip(
            t(
                "batch_renamer.window.include_subfolders_tooltip",
                "When adding a folder, also include all videos in subfolders"
            )
        )
        file_buttons.addWidget(self.include_subfolders_check)

        clear_btn = QPushButton(t("batch_renamer.window.clear_list", "🗑️ Clear List"))
        clear_btn.clicked.connect(self.clear_list)
        file_buttons.addWidget(clear_btn)

        # Pattern management button
        patterns_btn = QPushButton(t("batch_renamer.window.manage_patterns", "🏷️ Manage Patterns"))
        patterns_btn.clicked.connect(self.open_pattern_manager)
        patterns_btn.setToolTip(
            t(
                "batch_renamer.window.manage_patterns_tooltip",
                "Manage removal patterns (x264, YIFY, etc.)"
            )
        )
        patterns_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        file_buttons.addWidget(patterns_btn)

        file_buttons.addStretch()
        main_layout.addLayout(file_buttons)

        # File table
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(3)
        self.files_table.setHorizontalHeaderLabels([
            t("batch_renamer.table.original", "Original Name"),
            t("batch_renamer.table.removed", "Patterns Removed"),
            t("batch_renamer.table.new", "New Name")
        ])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.files_table)

        # Renaming options
        options_group = QGroupBox(t("batch_renamer.window.options", "Renaming Options"))
        options_layout = QVBoxLayout()

        # Pattern input
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel(t("batch_renamer.window.pattern_label", "Pattern:")))
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText(
            t("batch_renamer.window.pattern_placeholder", "{name}_{date}_{resolution}")
        )
        self.pattern_input.textChanged.connect(self.update_preview)
        pattern_layout.addWidget(self.pattern_input)

        update_btn = QPushButton(t("batch_renamer.window.update_preview", "🔄 Update Preview"))
        update_btn.clicked.connect(self.update_preview)
        pattern_layout.addWidget(update_btn)

        options_layout.addLayout(pattern_layout)

        # Variables help
        variables_label = QLabel(
            t(
                "batch_renamer.window.variables",
                "Variables: {name} {ext} {date} {time} {resolution} {width} {height} {codec} {duration} {size} {fps} {#} {##} {###}"
            )
        )
        variables_label.setStyleSheet("color: gray; font-size: 10px;")
        variables_label.setWordWrap(True)
        options_layout.addWidget(variables_label)

        # Find/Replace section
        find_replace_layout = QHBoxLayout()

        find_replace_layout.addWidget(QLabel(t("batch_renamer.window.find", "Find:")))
        self.find_input = QLineEdit()
        self.find_input.textChanged.connect(self.update_preview)
        find_replace_layout.addWidget(self.find_input)

        find_replace_layout.addWidget(QLabel(t("batch_renamer.window.replace", "Replace:")))
        self.replace_input = QLineEdit()
        self.replace_input.textChanged.connect(self.update_preview)
        find_replace_layout.addWidget(self.replace_input)

        self.regex_check = QCheckBox(t("batch_renamer.window.regex", "Regex"))
        self.regex_check.stateChanged.connect(self.update_preview)
        find_replace_layout.addWidget(self.regex_check)

        self.case_check = QCheckBox(t("batch_renamer.window.case_sensitive", "Case Sensitive"))
        self.case_check.setChecked(True)
        self.case_check.stateChanged.connect(self.update_preview)
        find_replace_layout.addWidget(self.case_check)

        options_layout.addLayout(find_replace_layout)

        # Case conversion
        case_layout = QHBoxLayout()
        case_layout.addWidget(QLabel(t("batch_renamer.window.case_label", "Case:")))

        self.case_combo = QComboBox()
        self.case_combo.addItems([
            t("batch_renamer.window.case_none", "No Change"),
            t("batch_renamer.window.case_lower", "lowercase"),
            t("batch_renamer.window.case_upper", "UPPERCASE"),
            t("batch_renamer.window.case_title", "Title Case"),
            t("batch_renamer.window.case_sentence", "Sentence case")
        ])
        self.case_combo.currentIndexChanged.connect(self.update_preview)
        case_layout.addWidget(self.case_combo)

        case_layout.addStretch()
        options_layout.addLayout(case_layout)

        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        # Action buttons
        action_layout = QHBoxLayout()

        self.rename_btn = QPushButton(t("batch_renamer.window.rename_all", "✏️ Rename All"))
        self.rename_btn.setEnabled(False)
        self.rename_btn.clicked.connect(self.rename_all)
        self.rename_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        action_layout.addWidget(self.rename_btn)

        self.undo_btn = QPushButton(t("batch_renamer.window.undo_last", "↶ Undo Last"))
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.undo_last)
        action_layout.addWidget(self.undo_btn)

        action_layout.addStretch()

        close_btn = QPushButton(t("batch_renamer.window.close", "✖ Close"))
        close_btn.clicked.connect(self.close)
        action_layout.addWidget(close_btn)

        main_layout.addLayout(action_layout)

    def add_files(self):
        """Add files through file dialog."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            t("batch_renamer.dialog.select_files", "Select Files"),
            "",
            t(
                "batch_renamer.dialog.file_filter",
                "Video Files (*.mp4 *.avi *.mkv *.mov *.flv *.wmv *.webm *.m4v);;All Files (*)"
            )
        )

        if files:
            self.add_file_list(files)

    def add_folder(self):
        """Add all videos from a folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            t("batch_renamer.dialog.select_folder", "Select Folder")
        )

        if folder:
            video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm', '.m4v'}
            folder_path = Path(folder)

            # Use rglob for recursive or glob for single level
            if self.include_subfolders_check.isChecked():
                video_files = [
                    str(f) for f in folder_path.rglob('*')
                    if f.suffix.lower() in video_extensions
                ]
            else:
                video_files = [
                    str(f) for f in folder_path.glob('*')
                    if f.suffix.lower() in video_extensions
                ]

            if video_files:
                self.add_file_list(video_files)
                logger.info(f"Added {len(video_files)} files from folder (subfolders: {self.include_subfolders_check.isChecked()})")
            else:
                QMessageBox.information(
                    self,
                    t("batch_renamer.dialog.no_videos_title", "No Videos"),
                    t("batch_renamer.dialog.no_videos_body", "No video files found in selected folder")
                )

    def add_file_list(self, files):
        """
        Add files to the table.

        Args:
            files (list): List of file paths.
        """
        added_count = 0

        for file in files:
            if file not in self.files:
                self.files.append(file)
                added_count += 1

        if added_count > 0:
            self.extract_metadata_batch()
            self.update_preview()
            self.rename_btn.setEnabled(True)
            logger.info(f"Added {added_count} files")

    def extract_metadata_batch(self):
        """Extract metadata for all files."""
        for file_path in self.files:
            if file_path not in self.metadata_cache:
                self.metadata_cache[file_path] = self.extract_metadata(file_path)

    def extract_metadata(self, file_path):
        """
        Extract metadata from a video file.

        Args:
            file_path (str): Video file path.

        Returns:
            dict: Metadata dictionary.
        """
        try:
            cap = cv2.VideoCapture(file_path)
            try:
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
            finally:
                cap.release()

            # File info
            mtime = Path(file_path).stat().st_mtime
            size_mb = Path(file_path).stat().st_size / (1024 * 1024)

            metadata = {
                'width': width,
                'height': height,
                'resolution': f"{width}x{height}",
                'fps': int(fps),
                'duration': int(duration),
                'size': f"{size_mb:.1f}MB",
                'date': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d'),
                'time': datetime.fromtimestamp(mtime).strftime('%H-%M-%S'),
                'codec': 'unknown',  # Would need FFprobe for accurate codec
            }

            return metadata

        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            return {}

    def update_preview(self):
        """Update the preview table with new filenames."""
        self.files_table.setRowCount(0)

        pattern = self.pattern_input.text()
        find_text = self.find_input.text()
        replace_text = self.replace_input.text()
        use_regex = self.regex_check.isChecked()
        case_sensitive = self.case_check.isChecked()
        case_mode_index = self.case_combo.currentIndex()
        case_modes = ['none', 'lower', 'upper', 'title', 'sentence']
        case_mode = case_modes[case_mode_index]

        for index, file_path in enumerate(self.files):
            row = self.files_table.rowCount()
            self.files_table.insertRow(row)

            # Original name
            original_name = Path(file_path).name
            self.files_table.setItem(row, 0, QTableWidgetItem(original_name))

            # Generate new name
            new_name = original_name

            # Apply pattern if provided
            if pattern:
                metadata = self.metadata_cache.get(file_path, {})
                base_name = self.pattern_parser.parse(pattern, file_path, metadata, index)
                extension = Path(file_path).suffix
                new_name = f"{base_name}{extension}"

            # Apply pattern removal (from pattern manager) and track what was removed
            name_without_ext = Path(new_name).stem
            extension = Path(new_name).suffix
            name_before_patterns = name_without_ext
            cleaned_name = self.pattern_manager.apply_patterns(name_without_ext)
            new_name = f"{cleaned_name}{extension}"

            # Detect removed patterns
            removed_patterns = self._detect_removed_patterns(name_before_patterns, cleaned_name)

            # Apply find/replace
            if find_text:
                new_name = FindReplaceProcessor.find_replace(
                    new_name, find_text, replace_text, use_regex, case_sensitive
                )

            # Apply case conversion
            if case_mode != 'none':
                name_part = Path(new_name).stem
                ext_part = Path(new_name).suffix
                name_part = FindReplaceProcessor.change_case(name_part, case_mode)
                new_name = f"{name_part}{ext_part}"

            # Show removed patterns (column 1)
            if removed_patterns:
                removed_text = ", ".join(removed_patterns)
                removed_item = QTableWidgetItem(removed_text)
                removed_item.setForeground(QColor(200, 50, 50))  # Red color
                removed_item.setToolTip(
                    t(
                        "batch_renamer.tooltip.patterns_removed",
                        f"Patterns removed: {removed_text}",
                        patterns=removed_text
                    )
                )
                self.files_table.setItem(row, 1, removed_item)
            else:
                self.files_table.setItem(row, 1, QTableWidgetItem("—"))

            # Show new name (column 2)
            self.files_table.setItem(row, 2, QTableWidgetItem(new_name))

    def _detect_removed_patterns(self, original: str, cleaned: str) -> list:
        """
        Detect which patterns were removed between original and cleaned name.

        Args:
            original: Original name before pattern removal
            cleaned: Name after pattern removal

        Returns:
            List of removed patterns
        """
        if original == cleaned:
            return []

        removed = []

        # Check each enabled pattern
        for pattern_dict in self.pattern_manager.get_enabled_patterns():
            pattern = pattern_dict['pattern']
            is_regex = pattern_dict.get('is_regex', False)

            if is_regex:
                # Check if regex pattern was in original but not in cleaned
                import re
                if re.search(pattern, original, re.IGNORECASE) and not re.search(pattern, cleaned, re.IGNORECASE):
                    removed.append(f"[{pattern}]")
            else:
                # Simple string check (case-insensitive)
                if pattern.lower() in original.lower() and pattern.lower() not in cleaned.lower():
                    removed.append(pattern)

        return removed

    def clear_list(self):
        """Clear the file list."""
        self.files.clear()
        self.metadata_cache.clear()
        self.files_table.setRowCount(0)
        self.rename_btn.setEnabled(False)
        logger.info("File list cleared")

    def rename_all(self):
        """Rename all files."""
        if not self.files:
            return

        # Confirm with user
        reply = QMessageBox.question(
            self,
            t("batch_renamer.dialog.confirm_rename_title", "Confirm Rename"),
            t(
                "batch_renamer.dialog.confirm_rename_body",
                f"Rename {len(self.files)} file(s)?",
                count=len(self.files)
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Build rename list
        rename_list = []
        for index in range(self.files_table.rowCount()):
            old_path = self.files[index]
            new_name_item = self.files_table.item(index, 2)  # Column 2 has the new name now
            if new_name_item:
                new_name = new_name_item.text()
                rename_list.append((old_path, new_name))

        # Perform rename
        successful, failed = self.renamer.rename_batch(rename_list)

        # Update file paths for successfully renamed files
        if successful > 0:
            # Update internal file list
            new_files = []
            for old_path, new_name in rename_list:
                new_path = str(Path(old_path).parent / new_name)
                new_files.append(new_path)
            self.files = new_files

        # Show result
        if failed:
            error_msg = f"Successfully renamed {successful} file(s).\n\nFailed:\n"
            for path, error in failed[:5]:  # Show first 5 errors
                error_msg += f"• {Path(path).name}: {error}\n"
            if len(failed) > 5:
                error_msg += f"...and {len(failed) - 5} more"

            QMessageBox.warning(
                self,
                t("batch_renamer.dialog.rename_errors_title", "Rename Complete with Errors"),
                t(
                    "batch_renamer.dialog.rename_errors_body",
                    error_msg,
                    success=successful
                )
            )
        else:
            QMessageBox.information(
                self,
                t("batch_renamer.dialog.rename_complete_title", "Rename Complete"),
                t(
                    "batch_renamer.dialog.rename_complete_body",
                    f"Successfully renamed {successful} file(s)!",
                    count=successful
                )
            )

        # Enable undo
        self.undo_btn.setEnabled(self.renamer.can_undo())

        # Update preview
        self.update_preview()

        logger.info(f"Batch rename: {successful} successful, {len(failed)} failed")

    def undo_last(self):
        """Undo the last rename operation."""
        success, error = self.renamer.undo_last()

        if success:
            QMessageBox.information(
                self,
                t("batch_renamer.dialog.undo_complete_title", "Undo Complete"),
                t("batch_renamer.dialog.undo_complete_body", "Last rename operation undone")
            )
            self.undo_btn.setEnabled(self.renamer.can_undo())
            # Note: File list might be out of sync after undo
        else:
            QMessageBox.critical(
                self,
                t("batch_renamer.dialog.undo_failed_title", "Undo Failed"),
                t("batch_renamer.dialog.undo_failed_body", f"Could not undo: {error}", error=error)
            )

    def open_pattern_manager(self):
        """Open the pattern management dialog."""
        dialog = PatternManagementDialog(
            pattern_manager=self.pattern_manager,
            current_files=self.files,
            parent=self
        )

        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            # Patterns were modified, reload and update preview
            self.pattern_manager.load_patterns()
            self.update_preview()
            logger.info("Pattern manager closed, preview updated")

    def closeEvent(self, event):
        """
        Handle window close event.

        Args:
            event: Close event.
        """
        event.accept()
        self.closed.emit()
