"""User interface for VideoConverter plugin.

This module provides the main window for the VideoConverter plugin, coordinating
between UI components, file management, and conversion operations.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QFileDialog, QApplication, QDialog,
    QSystemTrayIcon, QMenu, QStackedWidget, QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QTimer, QMutex, QMutexLocker
from PyQt6.QtGui import QKeySequence, QShortcut, QDragEnterEvent, QDropEvent
from pathlib import Path
from typing import Dict, Set, List, Optional
import time
import shutil
import subprocess

from src.core.logger import Logger
from src.core.i18n import t
from .advanced_settings import AdvancedSettingsDialog
from .utils import format_size, format_duration, is_converted_file, should_add_file
from .conversion_timer import ConversionTimer
from .file_discovery import FastFileDiscoveryWorker
from .ui import ButtonPanelManager, FileTableManager, DialogManager, SimpleCompressorView

logger = Logger.get_logger('VideoConverter.Window')


# Lazy import functions for heavy modules
def lazy_import_converter():
    """Lazy import of converter module."""
    from .converter import ConversionWorker
    return ConversionWorker


def lazy_import_settings():
    """Lazy import of settings module."""
    from .settings import SettingsManager
    return SettingsManager


class VideoConverterWindow(QMainWindow):
    """Main window for VideoConverter plugin.

    Provides a GUI for selecting video files, configuring conversion settings,
    and managing batch video conversions with real-time progress tracking.

    Attributes:
        files_to_convert: Dictionary mapping file paths to conversion info.
        files_mutex: Thread-safe mutex for file dictionary access.
        active_workers: Set of currently active conversion workers.
        conversion_queue: List of files waiting to be converted.
        max_concurrent: Maximum number of concurrent conversions.
    """

    def __init__(self):
        """Initialize the VideoConverter window."""
        super().__init__()
        self.setWindowTitle(t("video_converter.window.title", "🎬 Video Converter Pro"))
        self.setMinimumSize(900, 700)
        self.ready_text = t("video_converter.window.status.ready", "Ready")
        self.updated_text = t("video_converter.window.status.updated", "Settings updated")

        # Thread-safe file management
        self.files_to_convert: Dict[Path, Dict] = {}
        self.files_mutex = QMutex()
        self.active_workers: Set = set()
        self.conversion_queue: List[Path] = []
        self.max_concurrent = 3

        # Timing and progress tracking
        self.conversion_timer = ConversionTimer()
        self.start_time: Optional[float] = None
        self.total_files_to_convert = 0

        # Settings and state
        self.settings = None
        self.settings_manager = None
        self.discovery_worker: Optional[FastFileDiscoveryWorker] = None
        self.paused_after_current = False

        # Discovery state
        self.discovery_in_progress = False
        self.pending_ui_update = False

        # UI managers
        self.button_manager: Optional[ButtonPanelManager] = None
        self.table_manager: Optional[FileTableManager] = None
        self.dialog_manager: Optional[DialogManager] = None

        # Simple/Advanced mode
        self.simple_mode = False
        self.simple_view: Optional[SimpleCompressorView] = None
        self.mode_stack: Optional[QStackedWidget] = None
        self.mode_toggle_btn: Optional[QPushButton] = None

        # Initialize UI
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_drag_drop()
        self._setup_system_tray()
        self._setup_timers()

        logger.debug("VideoConverter window initialized")

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Initialize managers
        self.button_manager = ButtonPanelManager(self)
        self.table_manager = FileTableManager(self)
        self.dialog_manager = DialogManager(self)

        # Setup UI components
        self.button_manager.setup_header(layout)

        # Add mode toggle button
        toggle_layout = QHBoxLayout()
        toggle_layout.addStretch()
        self.mode_toggle_btn = QPushButton(t("video_converter.window.toggle_simple", "🎯 Mode Simple"))
        self.mode_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.mode_toggle_btn.clicked.connect(self.toggle_mode)
        toggle_layout.addWidget(self.mode_toggle_btn)
        toggle_layout.addStretch()
        layout.addLayout(toggle_layout)

        # Create stacked widget for mode switching
        self.mode_stack = QStackedWidget()

        # Advanced mode view (index 0)
        advanced_widget = QWidget()
        advanced_layout = QVBoxLayout(advanced_widget)
        advanced_layout.setContentsMargins(0, 0, 0, 0)

        # Setup advanced UI components
        self.button_manager.setup_main_buttons(advanced_layout)
        self.button_manager.setup_table_controls(advanced_layout)
        self.files_table = self.table_manager.create_table(advanced_layout)
        self.button_manager.setup_action_buttons(advanced_layout)

        self.mode_stack.addWidget(advanced_widget)

        # Simple mode view (index 1)
        settings = self._get_settings()
        self.simple_view = SimpleCompressorView(settings, self)
        self.simple_view.settings_changed.connect(self._on_simple_settings_changed)
        self.mode_stack.addWidget(self.simple_view)

        layout.addWidget(self.mode_stack)

        # Set initial mode to advanced
        self.mode_stack.setCurrentIndex(0)

    def _setup_shortcuts(self) -> None:
        """Configure keyboard shortcuts."""
        # File operations
        QShortcut(QKeySequence.StandardKey.Open, self, self.add_files)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, self.add_folder)
        QShortcut(QKeySequence.StandardKey.SelectAll, self, self.toggle_select_all)

        # Conversion control
        QShortcut(QKeySequence(Qt.Key.Key_F5), self, self.start_conversion)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.stop_conversion)

        # Other shortcuts
        QShortcut(
            QKeySequence.StandardKey.Preferences,
            self,
            self.show_advanced_settings
        )
        QShortcut(QKeySequence.StandardKey.Delete, self, self.remove_selected_files)
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear_files)
        QShortcut(QKeySequence.StandardKey.HelpContents, self, self.show_help)

    def _setup_drag_drop(self) -> None:
        """Configure drag and drop support."""
        self.setAcceptDrops(True)

    def _setup_system_tray(self) -> None:
        """Configure system tray icon."""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setToolTip("Video Converter")

            # Context menu
            tray_menu = QMenu()

            show_action = tray_menu.addAction(t("video_converter.window.tray.show", "Show"))
            show_action.triggered.connect(self.show_and_raise)

            start_action = tray_menu.addAction(t("video_converter.window.tray.start", "Start Conversions"))
            start_action.triggered.connect(self.start_conversion)

            tray_menu.addSeparator()

            quit_action = tray_menu.addAction(t("video_converter.window.tray.quit", "Quit"))
            quit_action.triggered.connect(self.close)

            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self._tray_icon_activated)
            self.tray_icon.show()

    def _setup_timers(self) -> None:
        """Setup periodic timers."""
        # Conversion queue check timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._check_conversion_queue)
        self.update_timer.start(2000)

        # Progress refresh timer
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._refresh_progress_display)
        self.progress_timer.start(1000)

        # UI batch update timer
        self.ui_update_timer = QTimer()
        self.ui_update_timer.timeout.connect(self._batch_update_ui)
        self.ui_update_timer.setSingleShot(True)

        # Time estimation timer
        self.estimation_timer = QTimer()
        self.estimation_timer.timeout.connect(self._update_time_estimation)
        self.estimation_timer.start(5000)

    # ========================================================================
    # Drag and Drop Handling
    # ========================================================================

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            video_exts = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.webm', '.wmv'}
            has_video = False

            for url in event.mimeData().urls():
                path = Path(url.toLocalFile())
                if path.suffix.lower() in video_exts or path.is_dir():
                    has_video = True
                    break

            if has_video:
                event.acceptProposedAction()
                self.status_label.setText(
                    t("video_converter.window.drop_hint", "📁 Drop to add files/folders")
                )
            else:
                event.ignore()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        """Handle drag leave event."""
        if not self.active_workers:
            self.status_label.setText(self.ready_text)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event."""
        files_and_folders = []

        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.exists():
                files_and_folders.append(path)

        if files_and_folders:
            self._add_dropped_files(files_and_folders)
            event.acceptProposedAction()

        self.status_label.setText(self.ready_text)

    def _add_dropped_files(self, paths: List[Path]) -> None:
        """Add dropped files and folders.

        Args:
            paths: List of file/folder paths that were dropped.
        """
        added_files = 0
        added_from_folders = 0

        self.status_label.setText(t("video_converter.window.processing_drop", "💥 Processing dropped files..."))
        QApplication.processEvents()

        settings = self._get_settings()
        suffix = getattr(settings, 'converted_suffix', '_cvt')
        deselect_converted = getattr(settings, 'deselect_converted_files', False)

        for path in paths:
            if path.is_file():
                if should_add_file(path, settings):
                    if self._add_single_file(path, settings, suffix, deselect_converted):
                        added_files += 1

            elif path.is_dir():
                video_extensions = [
                    '*.mp4', '*.avi', '*.mkv', '*.mov',
                    '*.flv', '*.webm', '*.wmv'
                ]

                for ext in video_extensions:
                    for file_path in path.rglob(ext):
                        if file_path.is_file() and should_add_file(file_path, settings):
                            if self._add_single_file(
                                file_path, settings, suffix, deselect_converted
                            ):
                                added_from_folders += 1

        total_added = added_files + added_from_folders
        if total_added > 0:
            self.refresh_table()
            message = t(
                "video_converter.window.files_added",
                f"✅ {total_added} files added",
                count=total_added
            )
            if added_files > 0 and added_from_folders > 0:
                message += t(
                    "video_converter.window.files_added_breakdown",
                    f" ({added_files} individual, {added_from_folders} from folders)",
                    files=added_files,
                    folders=added_from_folders
                )
            self.status_label.setText(message)
        else:
            self.status_label.setText(t("video_converter.window.no_valid_files", "❌ No valid video files found"))

    # ========================================================================
    # File Management
    # ========================================================================

    def add_files(self) -> None:
        """Add files manually via file dialog."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            t("video_converter.window.dialog.select_files", "Select Video Files"),
            "",
            t("video_converter.window.dialog.filter", "Videos (*.mp4 *.avi *.mkv *.mov *.flv *.webm *.wmv);;All Files (*.*)")
        )

        added = 0
        settings = self._get_settings()
        suffix = getattr(settings, 'converted_suffix', '_cvt')
        deselect_converted = getattr(settings, 'deselect_converted_files', False)

        for file_path in files:
            path = Path(file_path)
            if path.exists() and should_add_file(path, settings):
                if self._add_single_file(path, settings, suffix, deselect_converted):
                    added += 1

        if added > 0:
            self.refresh_table()
            self.status_label.setText(
                t(
                    "video_converter.window.files_added",
                    f"✅ {added} files added",
                    count=added
                )
            )

    def add_folder(self) -> None:
        """Add all video files from a folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            t("video_converter.window.dialog.select_folder", "Select Folder")
        )
        if not folder:
            return

        folder_path = Path(folder)
        added = 0
        settings = self._get_settings()

        self.status_label.setText(t("video_converter.window.scanning_folder", "📂 Scanning folder..."))
        QApplication.processEvents()

        video_extensions = [
            '*.mp4', '*.avi', '*.mkv', '*.mov',
            '*.flv', '*.webm', '*.wmv'
        ]

        for ext in video_extensions:
            for file_path in folder_path.rglob(ext):
                if file_path.is_file() and should_add_file(file_path, settings):
                    suffix = getattr(settings, 'converted_suffix', '_cvt')
                    deselect_converted = getattr(
                        settings, 'deselect_converted_files', False
                    )

                    if self._add_single_file(
                        file_path, settings, suffix, deselect_converted
                    ):
                        added += 1

        if added > 0:
            self.refresh_table()
            self.status_label.setText(
                t(
                    "video_converter.window.files_added_from_folder",
                    f"✅ {added} files added from folder",
                    count=added
                )
            )
        else:
            self.status_label.setText(
                t("video_converter.window.no_files_in_folder", "❌ No video files found in folder")
            )

    def _add_single_file(
        self,
        path: Path,
        settings,
        suffix: str,
        deselect_converted: bool
    ) -> bool:
        """Add a single file to the conversion list.

        Args:
            path: File path to add.
            settings: Settings object.
            suffix: Converted file suffix.
            deselect_converted: Whether to deselect converted files.

        Returns:
            True if file was added successfully.
        """
        with QMutexLocker(self.files_mutex):
            if path not in self.files_to_convert:
                try:
                    size = path.stat().st_size
                    is_converted = is_converted_file(path, suffix)

                    default_selected = True
                    if is_converted and deselect_converted:
                        default_selected = False

                    state = t("video_converter.window.state_pending", "Pending")
                    if is_converted:
                        state = t("video_converter.window.state_pending_converted", "Pending (converted)")

                    self.files_to_convert[path] = {
                        'state': state,
                        'selected': default_selected,
                        'size': size,
                        'progress': 0,
                        'worker': None,
                        'attempt': 0,
                        'is_converted': is_converted
                    }
                    return True
                except OSError:
                    return False
        return False

    def clear_files(self) -> None:
        """Clear the file list."""
        # Check if empty and if there are active conversions (thread-safe)
        with QMutexLocker(self.files_mutex):
            if not self.files_to_convert:
                return

            # Check for active conversions
            active_conversions = any(
                info.get('worker') is not None
                for info in self.files_to_convert.values()
            )

        if active_conversions:
            if not self.dialog_manager.confirm_clear_with_active():
                return
            self.stop_conversion()

        with QMutexLocker(self.files_mutex):
            self.files_to_convert.clear()

        # Hide global progress
        self.global_progress.setVisible(False)
        self.time_estimation_label.setText("")

        self.refresh_table()
        self.status_label.setText(
            t("video_converter.window.list_cleared", "🗑️ List cleared")
        )

    def remove_file(self, path: Path) -> None:
        """Remove a single file from the list.

        Args:
            path: Path to remove.
        """
        with QMutexLocker(self.files_mutex):
            if path in self.files_to_convert:
                info = self.files_to_convert[path]
                if info.get('worker'):
                    info['worker'].stop()
                    self.active_workers.discard(info['worker'])
                del self.files_to_convert[path]

        self.refresh_table()
        self.status_label.setText(
            t("video_converter.window.file_removed", "🗑️ File removed")
        )

    def remove_selected_files(self) -> None:
        """Remove selected files from the list."""
        files_to_remove = []

        with QMutexLocker(self.files_mutex):
            for path, info in self.files_to_convert.items():
                if info.get('selected', False):
                    if not info.get('worker'):
                        files_to_remove.append(path)

        if not files_to_remove:
            self.dialog_manager.show_no_files_to_remove_info()
            return

        if not self.dialog_manager.confirm_removal(len(files_to_remove)):
            return

        with QMutexLocker(self.files_mutex):
            for path in files_to_remove:
                if path in self.files_to_convert:
                    del self.files_to_convert[path]

        self.refresh_table()
        removed_count = len(files_to_remove)
        self.status_label.setText(
            t(
                "video_converter.window.files_removed",
                f"🗑️ {removed_count} files removed",
                count=removed_count
            )
        )

    # ========================================================================
    # File Selection
    # ========================================================================

    def toggle_select_all(self) -> None:
        """Toggle selection of all files."""
        with QMutexLocker(self.files_mutex):
            if not self.files_to_convert:
                return

            all_selected = all(
                info.get('selected', True)
                for info in self.files_to_convert.values()
            )
            new_state = not all_selected

            for info in self.files_to_convert.values():
                info['selected'] = new_state

        self.refresh_table()

    def select_only_converted_files(self) -> None:
        """Select only files that are already converted."""
        selected_count = 0

        with QMutexLocker(self.files_mutex):
            for path, info in self.files_to_convert.items():
                is_converted = info.get('is_converted', False)
                if is_converted:
                    info['selected'] = True
                    selected_count += 1
                else:
                    info['selected'] = False

        self.refresh_table()
        self.status_label.setText(
            t(
                "video_converter.window.converted_selected",
                f"🔄 {selected_count} converted files selected",
                count=selected_count
            )
        )

    def select_only_new_files(self) -> None:
        """Select only files that are not converted."""
        selected_count = 0

        with QMutexLocker(self.files_mutex):
            for path, info in self.files_to_convert.items():
                is_converted = info.get('is_converted', False)
                if not is_converted:
                    info['selected'] = True
                    selected_count += 1
                else:
                    info['selected'] = False

        self.refresh_table()
        self.status_label.setText(
            t(
                "video_converter.window.new_selected",
                f"🆕 {selected_count} new files selected",
                count=selected_count
            )
        )

    def update_selection(self, path: Path, state: int) -> None:
        """Update selection state of a file.

        Args:
            path: File path.
            state: Qt check state value.
        """
        with QMutexLocker(self.files_mutex):
            if path in self.files_to_convert:
                self.files_to_convert[path]['selected'] = (
                    state == Qt.CheckState.Checked.value
                )

        QTimer.singleShot(100, self._update_file_count)

    def _update_file_count(self) -> None:
        """Update file count label."""
        with QMutexLocker(self.files_mutex):
            selected_count = sum(
                1 for info in self.files_to_convert.values()
                if info.get('selected', True)
            )
            selected_size = sum(
                info['size'] for info in self.files_to_convert.values()
                if info.get('selected', True)
            )
            total_count = len(self.files_to_convert)

        if hasattr(self, 'file_count_label'):
            self.file_count_label.setText(
                t(
                    "video_converter.window.file_count",
                    f"{total_count} files ({selected_count} selected, {format_size(selected_size)})",
                    total=total_count,
                    selected=selected_count,
                    size=format_size(selected_size)
                )
            )

    # ========================================================================
    # File Discovery
    # ========================================================================

    def start_discovery(self) -> None:
        """Start automatic file discovery."""
        if self.discovery_worker and self.discovery_worker.isRunning():
            self.dialog_manager.show_discovery_in_progress_info()
            return

        result = self.dialog_manager.show_discovery_dialog()
        if result:
            selected_folders, min_size_mb = result
            self._auto_discover_files(selected_folders, min_size_mb)
        else:
            if not result and result is not None:
                self.dialog_manager.show_no_folders_selected_info()

    def _auto_discover_files(
        self,
        folders_to_scan: List[Path],
        min_size_mb: int
    ) -> None:
        """Start background file discovery.

        Args:
            folders_to_scan: List of folders to scan.
            min_size_mb: Minimum file size in MB.
        """
        self.discover_btn.setEnabled(False)
        self.discover_btn.setText(
            t("video_converter.window.searching", "🔍 Searching...")
        )
        self.status_label.setText(
            t("video_converter.window.discovery_in_progress", "Discovery in progress...")
        )
        self.discovery_in_progress = True

        # Create and start worker
        self.discovery_worker = FastFileDiscoveryWorker(
            folders_to_scan,
            min_size_mb
        )
        self.discovery_worker.file_found.connect(self._on_file_discovered)
        self.discovery_worker.progress.connect(self._on_discovery_progress)
        self.discovery_worker.finished.connect(self._on_discovery_finished)
        self.discovery_worker.batch_update.connect(self._on_batch_update)
        self.discovery_worker.start()

    def _on_file_discovered(
        self,
        file_path: str,
        size_bytes: int,
        size_mb: int
    ) -> None:
        """Handle file discovered event.

        Args:
            file_path: Path to discovered file.
            size_bytes: File size in bytes.
            size_mb: File size in MB.
        """
        path = Path(file_path)

        settings = self._get_settings()
        suffix = getattr(settings, 'converted_suffix', '_cvt')
        is_converted = is_converted_file(path, suffix)

        ignore_converted = getattr(settings, 'ignore_converted_files', True)
        deselect_converted = getattr(settings, 'deselect_converted_files', False)

        if is_converted and ignore_converted:
            return

        default_selected = True
        if is_converted and deselect_converted:
            default_selected = False

        with QMutexLocker(self.files_mutex):
            if path not in self.files_to_convert:
                state = t("video_converter.window.state_pending", "Pending")
                if is_converted:
                    state = t("video_converter.window.state_pending_converted", "Pending (converted)")

                self.files_to_convert[path] = {
                    'state': state,
                    'selected': default_selected,
                    'size': size_bytes,
                    'progress': 0,
                    'worker': None,
                    'attempt': 0,
                    'is_converted': is_converted
                }

                self.pending_ui_update = True

    def _on_batch_update(self) -> None:
        """Handle batch update signal from discovery worker."""
        if self.pending_ui_update and self.discovery_in_progress:
            self.pending_ui_update = False
            if not self.ui_update_timer.isActive():
                self.ui_update_timer.start(200)

    def _batch_update_ui(self) -> None:
        """Perform batched UI update during discovery."""
        if self.discovery_in_progress:
            try:
                self.refresh_table()
                with QMutexLocker(self.files_mutex):
                    count = len(self.files_to_convert)
                self.discover_btn.setText(
                    t(
                        "video_converter.window.found_count",
                        f"🔍 Found: {count}",
                        count=count
                    )
                )
            except Exception as e:
                logger.debug(f"Error during batch UI update: {e}")

    def _on_discovery_progress(self, count: int, current_folder: str) -> None:
        """Handle discovery progress update.

        Args:
            count: Number of files discovered so far.
            current_folder: Current folder being scanned.
        """
        self.status_label.setText(
            t(
                "video_converter.window.scan_progress",
                f"Scan: {Path(current_folder).name}... ({count} found)",
                folder=Path(current_folder).name,
                count=count
            )
        )

    def _on_discovery_finished(self, count: int) -> None:
        """Handle discovery completion.

        Args:
            count: Total number of files discovered.
        """
        self.discovery_in_progress = False
        self.pending_ui_update = False

        self.discover_btn.setEnabled(True)
        self.discover_btn.setText(
            t("video_converter.window.auto_discovery", "🔍 Auto-Discovery")
        )

        # Final complete update
        self.refresh_table()

        if count > 0:
            total_size = sum(
                info['size'] for info in self.files_to_convert.values()
            )
            self.status_label.setText(
                t(
                    "video_converter.window.discovery_complete_status",
                    f"✅ Discovery complete: {count} files ({format_size(total_size)})",
                    count=count,
                    size=format_size(total_size)
                )
            )

            # System notification
            if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    t("video_converter.window.discovery_complete_title", "Discovery Complete"),
                    t(
                        "video_converter.window.discovery_complete_body",
                        f"Found {count} video files ({format_size(total_size)})",
                        count=count,
                        size=format_size(total_size)
                    ),
                    QSystemTrayIcon.MessageIcon.Information,
                    3000
                )

            self.dialog_manager.show_discovery_complete(count, total_size)
        else:
            self.status_label.setText(
                t("video_converter.window.no_files_found", "❌ No files found")
            )
            self.dialog_manager.show_discovery_complete(count, 0)

    # ========================================================================
    # Filtering
    # ========================================================================

    def filter_current_list(self) -> None:
        """Apply current filter settings to the file list."""
        files_to_remove = []
        removed_count = 0

        with QMutexLocker(self.files_mutex):
            for path, info in self.files_to_convert.items():
                if info.get('worker'):
                    continue

                settings = self._get_settings()
                if not should_add_file(path, settings):
                    files_to_remove.append(path)

        with QMutexLocker(self.files_mutex):
            for path in files_to_remove:
                if path in self.files_to_convert:
                    del self.files_to_convert[path]
                    removed_count += 1

        self.refresh_table()
        self.status_label.setText(
            t(
                "video_converter.window.filter_applied",
                f"🔍 Filter applied: {removed_count} files removed",
                count=removed_count
            )
        )

    # ========================================================================
    # Conversion Control
    # ========================================================================

    def start_conversion(self) -> None:
        """Start conversion of selected files."""
        selected_files = self._get_selected_files()

        if not selected_files:
            self.dialog_manager.show_no_files_selected_warning()
            return

        # Check FFmpeg
        if not self._check_ffmpeg():
            return

        # Check disk space
        if not self._check_disk_space_for_conversion():
            return

        # Clean previous state
        self.conversion_queue.clear()
        self.active_workers.clear()
        self.conversion_timer = ConversionTimer()

        # Setup conversion queue
        self.conversion_queue.extend(selected_files)
        self.total_files_to_convert = len(selected_files)

        # Resume if paused
        self.paused_after_current = False

        # Update UI
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)

        # Show global progress
        self.global_progress.setVisible(True)
        self.global_progress.setMaximum(self.total_files_to_convert)
        self.global_progress.setValue(0)

        self.start_time = time.time()
        self.status_label.setText(
            t(
                "video_converter.window.starting_conversions",
                f"🚀 Starting {len(selected_files)} conversions...",
                count=len(selected_files)
            )
        )

        # System notification
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                t("video_converter.window.conversion_started_title", "Conversion Started"),
                t(
                    "video_converter.window.conversion_started_body",
                    f"Starting {len(selected_files)} conversions",
                    count=len(selected_files)
                ),
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )

        logger.info(f"=== START: {len(selected_files)} files queued ===")

    def pause_after_current(self) -> None:
        """Pause conversions after current ones complete."""
        self.paused_after_current = True
        self.pause_btn.setEnabled(False)
        self.start_btn.setText(
            t("video_converter.window.resume", "▶️ Resume")
        )
        self.start_btn.setEnabled(True)

        active_count = len(self.active_workers)
        queue_count = len(self.conversion_queue)
        self.status_label.setText(
            t(
                "video_converter.window.paused_status",
                f"⏸️ Paused: {active_count} conversions finishing, {queue_count} pending",
                active=active_count,
                pending=queue_count
            )
        )

        logger.info("⏸️ Pause requested - current conversions will finish")

    def stop_conversion(self) -> None:
        """Stop all conversions immediately."""
        # Clear queue
        self.conversion_queue.clear()
        self.paused_after_current = False

        # Stop all active workers
        for worker in list(self.active_workers):
            worker.stop()

        # Update states
        with QMutexLocker(self.files_mutex):
            for info in self.files_to_convert.values():
                if info.get('worker'):
                    info['worker'] = None
                    if 'In progress' in info.get('state', '') or \
                       'Starting' in info.get('state', ''):
                        info['state'] = 'Stopped'
                    info['progress'] = -1

        # Update UI
        self.start_btn.setEnabled(True)
        self.start_btn.setText(t("video_converter.window.start", "▶️ Start"))
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.paused_after_current = False

        # Hide progress
        self.global_progress.setVisible(False)
        self.time_estimation_label.setText("")

        self.status_label.setText(
            t("video_converter.window.conversions_stopped", "⏹️ Conversions stopped")
        )

        # System notification
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                t("video_converter.window.conversion_stopped_title", "Conversion Stopped"),
                t(
                    "video_converter.window.conversion_stopped_body",
                    "All conversions have been stopped"
                ),
                QSystemTrayIcon.MessageIcon.Warning,
                2000
            )

        self.refresh_table()
        logger.info("⏹️ All conversions stopped")

    def _check_conversion_queue(self) -> None:
        """Check conversion queue and start new conversions."""
        # Clean finished workers
        finished_workers = {
            worker for worker in self.active_workers
            if worker.isFinished()
        }
        for worker in finished_workers:
            self.active_workers.discard(worker)
            worker.deleteLater()

        # Start new conversions
        while (len(self.active_workers) < self.max_concurrent and
               self.conversion_queue and
               self.stop_btn.isEnabled() and
               not self.paused_after_current):

            file_path = self.conversion_queue.pop(0)

            with QMutexLocker(self.files_mutex):
                if file_path not in self.files_to_convert:
                    continue

                info = self.files_to_convert[file_path]
                if info.get('worker'):
                    continue

                # Start timing
                self.conversion_timer.start_conversion(
                    file_path,
                    info.get('size', 0)
                )

            # Create and start worker
            ConversionWorker = lazy_import_converter()
            worker = ConversionWorker(file_path, self._get_settings())

            # Connect signals
            worker.progress.connect(self._update_progress)
            worker.finished.connect(self._conversion_finished)
            worker.error.connect(self._conversion_error)
            worker.attempt_changed.connect(self._update_attempt)

            # Register worker
            with QMutexLocker(self.files_mutex):
                info = self.files_to_convert.get(file_path)
                if info:
                    info['worker'] = worker
                    info['state'] = 'Starting...'
                    info['progress'] = 0
                    info['attempt'] = 1

            self.active_workers.add(worker)
            worker.start()

            logger.debug(f"Worker started for {file_path.name}")

        # Update status
        if self.active_workers or self.conversion_queue:
            active_count = len(self.active_workers)
            queue_count = len(self.conversion_queue)
            status_text = (
                t(
                    "video_converter.window.conversion_status",
                    f"🔄 Conversions: {active_count}/{self.max_concurrent} active, {queue_count} pending",
                    active=active_count,
                    max=self.max_concurrent,
                    pending=queue_count
                )
            )
            if self.paused_after_current:
                status_text += t(
                    "video_converter.window.paused_after_current",
                    " (Paused after current)"
                )
            self.status_label.setText(status_text)

        # Check if all conversions finished
        conversion_in_progress = bool(self.active_workers or self.conversion_queue)
        conversion_was_started = self.stop_btn.isEnabled()

        if conversion_was_started and not conversion_in_progress:
            logger.info("All conversions finished - triggering completion")
            self._all_conversions_finished()

    def _conversion_finished(
        self,
        file_path: str,
        success: bool,
        message: str
    ) -> None:
        """Handle conversion finished event.

        Args:
            file_path: Path to converted file.
            success: Whether conversion succeeded.
            message: Result message.
        """
        path = Path(file_path)

        # Complete timing
        self.conversion_timer.complete_conversion(path, success)

        with QMutexLocker(self.files_mutex):
            if path in self.files_to_convert:
                info = self.files_to_convert[path]
                info['state'] = (
                    f"Completed: {message}" if success else f"Failed: {message}"
                )
                info['progress'] = -1

                # Clean worker reference
                worker = info.get('worker')
                info['worker'] = None

                if worker and worker in self.active_workers:
                    self.active_workers.discard(worker)

                # Update size if replaced
                settings = self._get_settings()
                if success and settings.replace_original and path.exists():
                    try:
                        info['size'] = path.stat().st_size
                    except OSError:
                        pass

        result_text = "completed" if success else "failed"
        logger.info(f"Conversion {result_text} for {path.name}: {message}")

        QTimer.singleShot(100, self.refresh_table)

    def _conversion_error(self, file_path: str, error: str) -> None:
        """Handle conversion error event.

        Args:
            file_path: Path to file that errored.
            error: Error message.
        """
        path = Path(file_path)

        # Complete timing (failure)
        self.conversion_timer.complete_conversion(path, False)

        with QMutexLocker(self.files_mutex):
            if path in self.files_to_convert:
                info = self.files_to_convert[path]
                info['state'] = f"Error: {error}"
                info['progress'] = -1

                # Clean worker reference
                worker = info.get('worker')
                info['worker'] = None

                if worker and worker in self.active_workers:
                    self.active_workers.discard(worker)

        logger.error(f"Conversion error for {path.name}: {error}")
        QTimer.singleShot(100, self.refresh_table)

    def _update_progress(self, file_path: str, progress: int) -> None:
        """Update conversion progress.

        Args:
            file_path: Path to file being converted.
            progress: Progress percentage.
        """
        path = Path(file_path)
        with QMutexLocker(self.files_mutex):
            if path in self.files_to_convert:
                info = self.files_to_convert[path]
                info['progress'] = progress
                if progress > 0:
                    info['state'] = f'In progress ({progress}%)'

    def _update_attempt(self, file_path: str, attempt: int) -> None:
        """Update conversion attempt number.

        Args:
            file_path: Path to file being converted.
            attempt: Attempt number.
        """
        path = Path(file_path)
        with QMutexLocker(self.files_mutex):
            if path in self.files_to_convert:
                info = self.files_to_convert[path]
                info['attempt'] = attempt
                info['state'] = f'Attempt {attempt}'
                info['progress'] = 0

    def _all_conversions_finished(self) -> None:
        """Handle all conversions finished."""
        logger.info("=== START all_conversions_finished ===")

        # Calculate statistics
        with QMutexLocker(self.files_mutex):
            total = len(self.files_to_convert)
            successful = 0
            failed = 0

            for path, info in self.files_to_convert.items():
                state = info.get('state', '')
                if 'Completed:' in state:
                    successful += 1
                elif 'Failed:' in state or 'Error:' in state:
                    failed += 1

            logger.info(
                f"Final stats: {successful} success, {failed} failed "
                f"out of {total} total"
            )

        # Calculate total time
        total_time = ""
        if self.start_time:
            elapsed = time.time() - self.start_time
            total_time = f" in {format_duration(elapsed)}"

        # Update UI
        self.start_btn.setEnabled(True)
        self.start_btn.setText(t("video_converter.window.start", "▶️ Start"))
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.paused_after_current = False

        # Hide progress
        self.global_progress.setVisible(False)
        self.time_estimation_label.setText("")

        # Clean workers
        self.active_workers.clear()
        self.conversion_queue.clear()

        # Status message
        if successful + failed > 0:
            self.status_label.setText(
                t(
                    "video_converter.window.completed_status",
                    f"✅ Completed{total_time}: {successful} success, {failed} failed",
                    time=total_time,
                    success=successful,
                    failed=failed
                )
            )
        else:
            self.status_label.setText(
                t("video_converter.window.conversions_completed", "✅ Conversions completed")
            )

        # System notification
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                t("video_converter.window.conversions_complete_title", "🎬 Conversions Complete"),
                t(
                    "video_converter.window.conversions_complete_body",
                    f"✅ {successful} success, ❌ {failed} failed{total_time}",
                    success=successful,
                    failed=failed,
                    time=total_time
                ),
                QSystemTrayIcon.MessageIcon.Information,
                5000
            )

        self.refresh_table()

        # Show summary
        self.dialog_manager.show_completion_summary(
            successful,
            failed,
            total_time
        )

        logger.info(
            f"=== END all_conversions_finished: "
            f"{successful}/{successful+failed} successful ==="
        )

    # ========================================================================
    # Progress and Display
    # ========================================================================

    def refresh_table(self) -> None:
        """Refresh the file table display."""
        if self.table_manager:
            self.table_manager.refresh_table()

    def _refresh_progress_display(self) -> None:
        """Refresh progress display periodically."""
        if not self.active_workers:
            return

        try:
            self.refresh_table()
        except Exception as e:
            logger.debug(f"Error refreshing progress: {e}")

    def _update_time_estimation(self) -> None:
        """Update time estimation display."""
        if not self.active_workers and not self.conversion_queue:
            self.time_estimation_label.setText("")
            return

        # Collect remaining files info
        remaining_files = []
        with QMutexLocker(self.files_mutex):
            for path, info in self.files_to_convert.items():
                if info.get('worker') or path in self.conversion_queue:
                    remaining_files.append({'size': info.get('size', 0)})

        # Estimate remaining time
        estimated_seconds = self.conversion_timer.estimate_remaining_time(
            remaining_files
        )

        if estimated_seconds:
            remaining_time_str = format_duration(estimated_seconds)

            if hasattr(self, 'total_files_to_convert') and \
               self.total_files_to_convert > 0:
                completed = self.total_files_to_convert - len(remaining_files)
                progress_percent = (
                    (completed / self.total_files_to_convert) * 100
                )

                self.time_estimation_label.setText(
                    t(
                        "video_converter.window.remaining_time",
                        f"⏱️ {remaining_time_str} remaining",
                        time=remaining_time_str
                    )
                )

                if not self.global_progress.isVisible():
                    self.global_progress.setVisible(True)

                self.global_progress.setMaximum(self.total_files_to_convert)
                self.global_progress.setValue(completed)
            else:
                self.time_estimation_label.setText(
                    t(
                        "video_converter.window.approx_time",
                        f"⏱️ ~{remaining_time_str}",
                        time=remaining_time_str
                    )
                )
        else:
            self.time_estimation_label.setText(
                t("video_converter.window.estimating", "⏱️ Estimating...")
            )

    # ========================================================================
    # Settings and Dialogs
    # ========================================================================

    def toggle_mode(self) -> None:
        """Toggle between Simple and Advanced modes."""
        self.simple_mode = not self.simple_mode

        if self.simple_mode:
            # Switch to Simple mode
            self.mode_stack.setCurrentIndex(1)
            self.mode_toggle_btn.setText(
                t("video_converter.window.toggle_advanced", "🔧 Advanced Mode")
            )
            self.mode_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #0b7dda;
                }
            """)
            logger.info("Switched to Simple mode")
        else:
            # Switch to Advanced mode
            self.mode_stack.setCurrentIndex(0)
            self.mode_toggle_btn.setText(
                t("video_converter.window.toggle_simple", "🎯 Simple Mode")
            )
            self.mode_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            logger.info("Switched to Advanced mode")

    def _on_simple_settings_changed(self) -> None:
        """Handle settings changes from simple view."""
        # Reload settings
        self.settings = None
        settings = self._get_settings()

        # Update display
        self.status_label.setText(
            t("video_converter.window.simple_applied", "✅ Simple settings applied")
        )
        QTimer.singleShot(
            3000,
            lambda: self.status_label.setText(self.ready_text)
        )

        logger.info("Simple mode settings applied")

    def _get_settings(self):
        """Get settings with lazy loading.

        Returns:
            Settings object.
        """
        if self.settings is None:
            SettingsManager = lazy_import_settings()
            self.settings_manager = SettingsManager
            self.settings = SettingsManager.load_settings()
            self.max_concurrent = self.settings.max_concurrent_conversions

        return self.settings

    def show_advanced_settings(self) -> None:
        """Show advanced settings dialog."""
        settings = self._get_settings()
        dialog = AdvancedSettingsDialog(self, settings)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._on_settings_updated()

    def _on_settings_updated(self) -> None:
        """Handle settings update."""
        # Force reload
        self.settings = None
        settings = self._get_settings()

        # Update concurrent threads
        self.max_concurrent = settings.max_concurrent_conversions

        # Offer to filter list (thread-safe check)
        has_files = False
        if hasattr(self, 'files_to_convert'):
            with QMutexLocker(self.files_mutex):
                has_files = bool(self.files_to_convert)

        if has_files:
            if self.dialog_manager.confirm_apply_filters():
                self.filter_current_list()

        # Refresh display
        self.refresh_table()
        self.button_manager.update_disk_space_info()

        self.status_label.setText(self.updated_text)
        QTimer.singleShot(
            3000,
            lambda: self.status_label.setText(self.ready_text)
        )

    def show_help(self) -> None:
        """Show help dialog."""
        self.dialog_manager.show_help()

    def show_stats(self) -> None:
        """Show statistics dialog."""
        self.dialog_manager.show_stats()

    # ========================================================================
    # Utilities
    # ========================================================================

    def _get_selected_files(self) -> List[Path]:
        """Get list of selected files.

        Returns:
            List of selected file paths.
        """
        with QMutexLocker(self.files_mutex):
            return [
                path for path, info in self.files_to_convert.items()
                if info.get('selected', False)
            ]

    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available using configured path.

        Returns:
            True if FFmpeg is available.
        """
        try:
            settings = self._get_settings()
            ffmpeg_path = getattr(settings, 'ffmpeg_path', 'ffmpeg')
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            self.dialog_manager.show_no_ffmpeg_error()
            return False

    def _check_disk_space_for_conversion(self) -> bool:
        """Check if there's enough disk space for conversion.

        Returns:
            True if there's enough space or user confirms to continue.
        """
        try:
            # Estimate needed space
            with QMutexLocker(self.files_mutex):
                selected_files = [
                    info for info in self.files_to_convert.values()
                    if info.get('selected', False)
                ]
                total_size = sum(info.get('size', 0) for info in selected_files)

            # Estimate: need 20% extra for temp files
            estimated_space_needed = total_size * 0.2

            home_path = Path.home()
            _, _, free = shutil.disk_usage(home_path)

            if free < estimated_space_needed:
                return self.dialog_manager.confirm_disk_space(
                    estimated_space_needed,
                    free
                )

            return True

        except Exception as e:
            logger.warning(f"Cannot check disk space: {e}")
            return True

    def show_and_raise(self) -> None:
        """Show and raise window to foreground."""
        self.show()
        self.raise_()
        self.activateWindow()

    def _tray_icon_activated(self, reason) -> None:
        """Handle system tray icon activation.

        Args:
            reason: Activation reason.
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_and_raise()

    # ========================================================================
    # Window Events
    # ========================================================================

    def closeEvent(self, event) -> None:
        """Handle window close event.

        Args:
            event: Close event.
        """
        # Stop discovery if running
        if self.discovery_worker and self.discovery_worker.isRunning():
            if not self.dialog_manager.confirm_stop_discovery():
                event.ignore()
                return

            self.discovery_worker.stop()
            self.discovery_worker.wait(3000)

        # Stop conversions if running
        if self.active_workers:
            if not self.dialog_manager.confirm_stop_conversions():
                # Minimize to tray instead of closing
                if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
                    self.hide()
                    self.tray_icon.showMessage(
                        "Video Converter",
                        "Application continues in background.\n"
                        "Double-click the icon to restore.",
                        QSystemTrayIcon.MessageIcon.Information,
                        3000
                    )
                event.ignore()
                return

            self.stop_conversion()
            # Wait for workers to stop
            for _ in range(30):
                if not self.active_workers:
                    break
                QApplication.processEvents()
                time.sleep(0.1)

        event.accept()
