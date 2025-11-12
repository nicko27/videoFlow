"""
Enhanced UI additions for Batch Renamer.

This file contains additional UI methods to be added to BatchRenamerWindow.
Copy these methods into window.py after the existing methods.
"""

# ============================================================================
# DRAG AND DROP SUPPORT
# ============================================================================

def dragEnterEvent(self, event: QDragEnterEvent):
    """Handle drag enter event."""
    if event.mimeData().hasUrls():
        event.acceptProposedAction()

def dropEvent(self, event: QDropEvent):
    """Handle drop event."""
    files = []
    for url in event.mimeData().urls():
        file_path = url.toLocalFile()
        path_obj = Path(file_path)

        if path_obj.is_file():
            # Check if it's a video file
            video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm', '.m4v'}
            if path_obj.suffix.lower() in video_extensions:
                files.append(str(path_obj))
        elif path_obj.is_dir():
            # Add all videos from directory
            video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm', '.m4v'}
            if self.include_subfolders_check.isChecked():
                video_files = [
                    str(f) for f in path_obj.rglob('*')
                    if f.suffix.lower() in video_extensions
                ]
            else:
                video_files = [
                    str(f) for f in path_obj.glob('*')
                    if f.suffix.lower() in video_extensions
                ]
            files.extend(video_files)

    if files:
        self.add_file_list(files)
        logger.info(f"Added {len(files)} files via drag & drop")


# ============================================================================
# THREADED METADATA EXTRACTION
# ============================================================================

def extract_metadata_batch_threaded(self):
    """Extract metadata using worker thread with progress bar."""
    files_to_process = [f for f in self.files if f not in self.metadata_cache]

    if not files_to_process:
        return

    # Create and show progress bar
    if not hasattr(self, 'progress_bar'):
        self.progress_bar = QProgressBar()
        # Insert progress bar after file table
        layout = self.centralWidget().layout()
        layout.insertWidget(3, self.progress_bar)

    self.progress_bar.setVisible(True)
    self.progress_bar.setValue(0)
    self.progress_bar.setFormat("Extracting metadata: %p% (%v/%m)")

    # Create worker
    self.metadata_worker = MetadataExtractionWorker(files_to_process)
    self.metadata_worker.progress.connect(self.on_metadata_progress)
    self.metadata_worker.finished.connect(self.on_metadata_finished)
    self.metadata_worker.error.connect(self.on_metadata_error)
    self.metadata_worker.start()

    logger.info(f"Started threaded metadata extraction for {len(files_to_process)} files")


def on_metadata_progress(self, current: int, total: int, filename: str):
    """Handle metadata extraction progress."""
    self.progress_bar.setMaximum(total)
    self.progress_bar.setValue(current)
    self.progress_bar.setFormat(f"Extracting metadata: {current}/{total} - {filename[:30]}...")


def on_metadata_finished(self, metadata: dict):
    """Handle metadata extraction completion."""
    self.metadata_cache.update(metadata)
    self.progress_bar.setVisible(False)
    self.update_preview()
    logger.info("Metadata extraction completed")


def on_metadata_error(self, error_msg: str):
    """Handle metadata extraction error."""
    self.progress_bar.setVisible(False)
    QMessageBox.warning(self, "Metadata Error", f"Error during metadata extraction: {error_msg}")


# ============================================================================
# DRY-RUN MODE
# ============================================================================

def show_dry_run_dialog(self):
    """Show dry-run simulation results."""
    if not self.files:
        QMessageBox.information(self, "No Files", "No files loaded")
        return

    # Build rename list
    rename_list = []
    for index in range(self.files_table.rowCount()):
        old_path = self.files[index]
        new_name_item = self.files_table.item(index, 1)
        if new_name_item:
            new_name = new_name_item.text()
            rename_list.append((old_path, new_name))

    # Run dry-run
    successful, failed = self.active_renamer.rename_batch(rename_list, dry_run=True)

    # Show results
    dialog = QDialog(self)
    dialog.setWindowTitle("Dry Run Results")
    dialog.setMinimumSize(600, 400)

    layout = QVBoxLayout(dialog)

    # Summary
    summary = QLabel(f"<b>Simulation Results:</b><br>"
                    f"✅ Would succeed: {successful}<br>"
                    f"❌ Would fail: {len(failed)}")
    layout.addWidget(summary)

    # Results table
    if failed:
        results_text = QTextEdit()
        results_text.setReadOnly(True)
        text = "Files that would fail:\n\n"
        for path, error in failed:
            text += f"❌ {Path(path).name}\n   Error: {error}\n\n"
        results_text.setPlainText(text)
        layout.addWidget(results_text)

    # Buttons
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)

    dialog.exec()


# ============================================================================
# REDO SUPPORT
# ============================================================================

def redo_last(self):
    """Redo the last undone operation."""
    if hasattr(self.active_renamer, 'redo'):
        success, message = self.active_renamer.redo()

        if success:
            QMessageBox.information(self, "Redo Complete", message)
            self.update_undo_redo_buttons()
        else:
            QMessageBox.warning(self, "Redo Failed", message)
    else:
        QMessageBox.information(self, "Not Available", "Redo not available with current renamer")


def update_undo_redo_buttons(self):
    """Update undo/redo button states."""
    if hasattr(self, 'undo_btn'):
        can_undo = self.active_renamer.can_undo() if hasattr(self.active_renamer, 'can_undo') else False
        self.undo_btn.setEnabled(can_undo)

    if hasattr(self, 'redo_btn'):
        can_redo = self.active_renamer.can_redo() if hasattr(self.active_renamer, 'can_redo') else False
        self.redo_btn.setEnabled(can_redo)


# ============================================================================
# HISTORY VIEWER
# ============================================================================

def show_history_dialog(self):
    """Show transaction history."""
    if not hasattr(self.active_renamer, 'get_history'):
        QMessageBox.information(self, "Not Available", "History not available with current renamer")
        return

    history = self.active_renamer.get_history(limit=100)

    if not history:
        QMessageBox.information(self, "No History", "No rename operations in history")
        return

    # Create dialog
    dialog = QDialog(self)
    dialog.setWindowTitle("Rename History")
    dialog.setMinimumSize(800, 600)

    layout = QVBoxLayout(dialog)

    # Info
    info = QLabel(f"<b>Transaction History</b><br>Showing last {len(history)} operations")
    layout.addWidget(info)

    # History table
    history_table = QTableWidget()
    history_table.setColumnCount(4)
    history_table.setHorizontalHeaderLabels(["Timestamp", "Old Name", "New Name", "Status"])
    history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

    for trans in reversed(history):  # Most recent first
        row = history_table.rowCount()
        history_table.insertRow(row)

        # Timestamp
        timestamp = trans.get('timestamp', '')[:19]  # Remove milliseconds
        history_table.setItem(row, 0, QTableWidgetItem(timestamp))

        # Old name
        old_name = trans.get('old_name', '')
        history_table.setItem(row, 1, QTableWidgetItem(old_name))

        # New name
        new_name = trans.get('new_name', '')
        history_table.setItem(row, 2, QTableWidgetItem(new_name))

        # Status
        status = "✅ Success" if trans.get('success', True) else "❌ Failed"
        history_table.setItem(row, 3, QTableWidgetItem(status))

    layout.addWidget(history_table)

    # Buttons
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    dialog.exec()


# ============================================================================
# ADVANCED PATTERN HELP
# ============================================================================

def show_advanced_pattern_help(self):
    """Show help dialog for advanced patterns."""
    dialog = QDialog(self)
    dialog.setWindowTitle("Advanced Pattern Help")
    dialog.setMinimumSize(700, 600)

    layout = QVBoxLayout(dialog)

    # Title
    title = QLabel("<h2>Advanced Pattern Features</h2>")
    layout.addWidget(title)

    # Create tabs
    tabs = QTabWidget()

    # Tab 1: Basic Variables
    basic_tab = QWidget()
    basic_layout = QVBoxLayout(basic_tab)
    basic_text = QTextEdit()
    basic_text.setReadOnly(True)
    basic_text.setPlainText("""
BASIC VARIABLES:
================
{name}          - Original filename without extension
{ext}           - File extension
{date}          - File modification date (YYYY-MM-DD)
{time}          - File modification time (HH-MM-SS)
{resolution}    - Video resolution (e.g., 1920x1080)
{width}         - Video width in pixels
{height}        - Video height in pixels
{fps}           - Frames per second
{duration}      - Duration in seconds
{size}          - File size in MB
{codec}         - Video codec
{#}             - Index (1, 2, 3...)
{##}            - Index with 2 digits (01, 02, 03...)
{###}           - Index with 3 digits (001, 002, 003...)
{####}          - Index with 4 digits (0001, 0002, 0003...)

EXAMPLES:
=========
{name}_{date}                    → Movie_2024-11-09
{##}_{name}_{resolution}         → 01_Movie_1920x1080
Video_{###}                      → Video_001
    """)
    basic_layout.addWidget(basic_text)
    tabs.addTab(basic_tab, "Basic")

    # Tab 2: Advanced Features
    advanced_tab = QWidget()
    advanced_layout = QVBoxLayout(advanced_tab)
    advanced_text = QTextEdit()
    advanced_text.setReadOnly(True)
    advanced_text.setPlainText("""
TRANSFORMATIONS:
================
{name:upper}               - UPPERCASE
{name:lower}               - lowercase
{name:title}               - Title Case
{name:capitalize}          - Capitalize first letter
{name:trim:20}             - First 20 characters
{date:format:DD-MM-YYYY}   - Custom date format (09-11-2024)
{date:format:YYYYMMDD}     - Date without separators (20241109)
{name:replace:old:new}     - Replace text in name
{name:substr:0:10}         - Substring from index 0 to 10

CONDITIONALS:
=============
{if:fps>30}HFR{endif}                - Show "HFR" if fps > 30
{if:width>=1920}FullHD{endif}        - Show "FullHD" if width >= 1920
{if:codec==h265}HEVC{endif}          - Show "HEVC" if codec is h265
{if:duration>3600}LongMovie{endif}   - Show "LongMovie" if > 1 hour

Operators: >, <, >=, <=, ==, !=, contains

REGEX CAPTURE:
==============
{regex:Season (\\d+):1}              - Extract season number
{regex:\\[(.*?)\\]:1}                - Extract text in brackets
{regex:(\\d{4}):1}                   - Extract 4-digit year

EXAMPLES:
=========
{name:upper}_{if:fps>30}60FPS{endif}
→ MOVIE_NAME_60FPS (if fps > 30)

{##}_{name:trim:30}_{date:format:YYYYMMDD}
→ 01_Movie_Name_20241109

{regex:S(\\d+)E(\\d+):1}x{regex:S(\\d+)E(\\d+):2}
→ Extract "1x05" from "S01E05"
    """)
    advanced_layout.addWidget(advanced_text)
    tabs.addTab(advanced_tab, "Advanced")

    layout.addWidget(tabs)

    # Close button
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    dialog.exec()


# ============================================================================
# TABLE SORTING
# ============================================================================

def setup_table_sorting(self):
    """Enable sorting on file table."""
    if hasattr(self, 'files_table'):
        self.files_table.setSortingEnabled(True)
