"""
Main window for the video duplicate finder application.

This module provides the main application window that coordinates all
duplicate finding operations. It integrates the UI, handlers, and workers
into a cohesive user interface.

The window is organized into:
- Left panel: File management and configuration
- Right panel: Progress tracking and status
- Handlers: Business logic for files, analysis, and duplicates
- Workers: Background threads for hash computation and comparison
"""
import os
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QMessageBox,
    QSplitter, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

# Import local modules
try:
    from .video_hasher import VideoHasher
    from .comparison_dialog import ComparisonDialog
    from .progress_widgets import FileListWidget
    from .ui.panels import UIPanels
    from .managers.settings_manager import SettingsManager
    from .handlers.file_handler import FileHandler
    from .handlers.analysis_handler import AnalysisHandler
    from .handlers.duplicate_handler import DuplicateHandler
except ImportError:
    # Fallback for direct imports
    from video_hasher import VideoHasher
    from comparison_dialog import ComparisonDialog
    from progress_widgets import FileListWidget
    from ui.panels import UIPanels
    from managers.settings_manager import SettingsManager
    from handlers.file_handler import FileHandler
    from handlers.analysis_handler import AnalysisHandler
    from handlers.duplicate_handler import DuplicateHandler

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.MainWindow')


class DuplicateFinderWindow(QMainWindow):
    """
    Main window for the video duplicate finder application.

    This window coordinates all components of the duplicate finder:
    - File management through FileHandler
    - Analysis orchestration through AnalysisHandler
    - Duplicate processing through DuplicateHandler
    - Settings persistence through SettingsManager
    - UI construction through UIPanels

    The window provides a split-panel interface with configuration on the left
    and progress tracking on the right.

    Attributes:
        closed (pyqtSignal): Signal emitted when the window is closed.

    Example:
        ```python
        window = DuplicateFinderWindow()
        window.show()
        ```
    """

    closed = pyqtSignal()

    def __init__(self) -> None:
        """
        Initialize the main window and all components.
        """
        super().__init__()
        self.setWindowTitle("🔍 Video Duplicate Detector")
        self.setMinimumSize(1000, 800)

        # Initialize core components
        self.video_hasher = VideoHasher()

        # Initialize UI components (will be set in setup_ui)
        self.file_list_widget: Optional[FileListWidget] = None
        self.status_indicator = None
        self.file_progress = None
        self.comparison_progress = None
        self.config_tabs = None
        self.analyze_btn = None
        self.stop_btn = None

        # Initialize parameter widgets (will be set in setup_ui)
        self.threshold_spin = None
        self.hash_workers_spin = None
        self.comparison_workers_spin = None
        self.batch_size_spin = None
        self.hash_timeout_spin = None
        self.comparison_timeout_spin = None

        # Initialize managers and handlers
        self.settings_manager = SettingsManager()
        self.file_handler: Optional[FileHandler] = None
        self.analysis_handler: Optional[AnalysisHandler] = None
        self.duplicate_handler: Optional[DuplicateHandler] = None

        # UI update timer
        self.status_update_timer = QTimer()
        self.status_update_timer.timeout.connect(self.force_ui_update)
        self.status_update_timer.setSingleShot(False)

        # Setup UI
        self.setup_ui()

        # Initialize handlers after UI is ready
        self.file_handler = FileHandler(self.file_list_widget)
        self.analysis_handler = AnalysisHandler(self.video_hasher)
        self.duplicate_handler = DuplicateHandler(self.video_hasher, self.file_handler)

        # Connect analysis handler signals
        self._connect_analysis_signals()

        # Load settings
        self._load_settings()

        # Connect settings change signals
        self._connect_settings_signals()

        # Auto cleanup database
        self.auto_cleanup_database()

        logger.info("Main window initialized successfully")

    def setup_ui(self) -> None:
        """
        Configure the user interface.

        This method creates the main layout with a title, split panels,
        and all necessary widgets.
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Title
        title = UIPanels.create_title_label()
        main_layout.addWidget(title)

        # Splitter for panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Create file list widget (needed for both panels)
        self.file_list_widget = FileListWidget()

        # Create panels
        left_panel = self._create_left_panel()
        right_panel, right_widgets = UIPanels.create_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])

        main_layout.addWidget(splitter)

        # Store right panel widgets
        self.status_indicator = right_widgets['status_indicator']
        self.file_progress = right_widgets['file_progress']
        self.comparison_progress = right_widgets['comparison_progress']

        # Initial button states
        self.analyze_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

    def _create_left_panel(self):
        """
        Create the left configuration panel.

        Returns:
            QFrame containing the left panel.
        """
        # Define callbacks
        callbacks = {
            'add_files': self.add_files,
            'add_folder': self.add_folder,
            'clear_list': self.clear_list,
            'clear_cache': self.clear_cache,
            'apply_preset': self.apply_preset,
            'analyze': self.start_analysis,
            'stop': self.stop_analysis,
            'show_stats': self.show_statistics,
            'show_pending': self.show_pending_duplicates,
            'close': self.close
        }

        # Create panel
        panel = UIPanels.create_left_panel(self.file_list_widget, callbacks)

        # Extract references to parameter widgets and buttons
        # The parameters tab is the second tab (index 1)
        self.config_tabs = panel.findChild(QWidget.__class__)
        params_tab = None
        for child in panel.findChildren(QWidget):
            if hasattr(child, 'threshold_spin'):
                params_tab = child
                break

        if params_tab:
            self.threshold_spin = params_tab.threshold_spin
            self.hash_workers_spin = params_tab.hash_workers_spin
            self.comparison_workers_spin = params_tab.comparison_workers_spin
            self.batch_size_spin = params_tab.batch_size_spin
            self.hash_timeout_spin = params_tab.hash_timeout_spin
            self.comparison_timeout_spin = params_tab.comparison_timeout_spin

        # Extract button references
        for child in panel.findChildren(QWidget):
            if hasattr(child, 'analyze_btn'):
                self.analyze_btn = child.analyze_btn
                self.stop_btn = child.stop_btn
                break

        return panel

    def _connect_analysis_signals(self) -> None:
        """
        Connect analysis handler signals to UI update methods.
        """
        if self.analysis_handler:
            self.analysis_handler.hash_finished.connect(self._on_hash_finished)
            self.analysis_handler.comparison_finished.connect(self._on_comparison_finished)
            self.analysis_handler.analysis_error.connect(self.handle_error)

    def _connect_settings_signals(self) -> None:
        """
        Connect parameter widget signals for auto-save.
        """
        widgets = [
            self.threshold_spin, self.hash_workers_spin,
            self.comparison_workers_spin, self.batch_size_spin,
            self.hash_timeout_spin, self.comparison_timeout_spin
        ]

        for widget in widgets:
            if widget:
                widget.valueChanged.connect(self._on_settings_changed)

    def _load_settings(self) -> None:
        """
        Load saved settings.
        """
        widgets = self._get_widget_dict()
        self.settings_manager.load_settings(widgets, self)

    def _get_widget_dict(self) -> Dict[str, Any]:
        """
        Get dictionary of setting widgets.

        Returns:
            Dictionary mapping widget names to widget instances.
        """
        return {
            'threshold_spin': self.threshold_spin,
            'hash_workers_spin': self.hash_workers_spin,
            'comparison_workers_spin': self.comparison_workers_spin,
            'batch_size_spin': self.batch_size_spin,
            'hash_timeout_spin': self.hash_timeout_spin,
            'comparison_timeout_spin': self.comparison_timeout_spin
        }

    def _on_settings_changed(self) -> None:
        """
        Handle settings change - auto-save.
        """
        if self.settings_manager.is_loading():
            return

        widgets = self._get_widget_dict()
        self.settings_manager.save_settings(widgets, self)

        # Show brief confirmation
        self.status_indicator.update_status(
            "💾", "Settings saved",
            "#17A2B8", "#D1ECF1", "#17A2B8"
        )

        # Clear message after 1.5 seconds
        QTimer.singleShot(1500, lambda: self.status_indicator.update_status(
            "🎯", "Ready to analyze",
            "#28A745", "#D4EDDA", "#28A745"
        ))

    # File operations
    def add_files(self) -> None:
        """
        Add video files through file dialog.
        """
        count = self.file_handler.add_files_dialog(self)

        if count > 0:
            # Update cache status for new files
            files = self.file_handler.get_all_files()
            self.file_handler.batch_update_cache_status(files, self.video_hasher)

            # Update UI
            self.force_ui_update()
            self.analyze_btn.setEnabled(self.file_handler.get_file_count() > 1)

            self.status_indicator.update_status(
                "✅", f"{count} file(s) added",
                "#28A745", "#D4EDDA", "#28A745"
            )

    def add_folder(self) -> None:
        """
        Add all video files from a folder.
        """
        count = self.file_handler.add_folder_dialog(self)

        if count > 0:
            # Update cache status
            files = self.file_handler.get_all_files()
            self.file_handler.batch_update_cache_status(files, self.video_hasher)

            # Update UI
            self.force_ui_update()
            self.analyze_btn.setEnabled(self.file_handler.get_file_count() > 1)

            self.status_indicator.update_status(
                "📂", f"{count} file(s) found in folder",
                "#28A745", "#D4EDDA", "#28A745"
            )

    def clear_list(self) -> None:
        """
        Clear the file list.
        """
        self.file_handler.clear_files()
        self.analyze_btn.setEnabled(False)
        self.status_indicator.update_status("🗑️", "List cleared")
        self.force_ui_update()

    def clear_cache(self) -> None:
        """
        Clear the video hash cache.
        """
        try:
            self.video_hasher.clear_cache()

            # Update file statuses
            files = self.file_handler.get_all_files()
            for file_path in files:
                self.file_handler.update_file_status(file_path, "⏳ To analyze")

            self.force_ui_update()

            self.status_indicator.update_status(
                "🧹", "Cache cleared - all files need reanalysis",
                "#FFC107", "#FFF3CD", "#FFC107"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot clear cache: {e}")

    # Configuration
    def apply_preset(self, preset_type: str) -> None:
        """
        Apply a configuration preset.

        Args:
            preset_type: Preset type ('fast', 'balanced', or 'quality').
        """
        widgets = self._get_widget_dict()
        message = self.settings_manager.apply_preset(preset_type, widgets)

        # Show confirmation
        icon = {"fast": "⚡", "balanced": "⚖️", "quality": "🎯"}[preset_type]
        self.status_indicator.update_status(icon, message)

    def get_analysis_config(self) -> Dict[str, Any]:
        """
        Get current analysis configuration.

        Returns:
            Dictionary with analysis parameters.
        """
        widgets = self._get_widget_dict()
        return self.settings_manager.get_analysis_config(widgets)

    # Analysis operations
    def start_analysis(self) -> None:
        """
        Start the duplicate detection analysis.
        """
        file_count = self.file_handler.get_file_count()

        if file_count < 2:
            QMessageBox.warning(
                self, "Warning",
                "At least 2 files are required to detect duplicates"
            )
            return

        # Validate files
        valid_files, invalid_files = self.file_handler.validate_files_for_analysis()

        if len(valid_files) < 2:
            QMessageBox.warning(self, "Error", "Not enough valid files")
            return

        # Set UI to analysis mode
        self.set_analysis_mode(True)
        self.duplicate_handler.processing_stopped = False

        # Start UI updates
        self.start_ui_updates()

        self.status_indicator.update_status(
            "📄", "Analysis in progress...",
            "#007BFF", "#CCE5FF", "#007BFF"
        )

        # Start hash analysis
        config = self.get_analysis_config()
        self.analysis_handler.start_hash_analysis(
            valid_files,
            config,
            progress_callback=self.update_file_progress,
            file_processed_callback=self.update_file_processed,
            current_file_callback=self.update_current_file_display,
            progress_details_callback=self.update_hash_progress_details
        )

        # Initialize progress display
        self.file_progress.update_progress(0, len(valid_files), "Computing hashes...")
        self.file_progress.set_status("Starting", "#FFC107")

    def stop_analysis(self) -> None:
        """
        Stop the current analysis.
        """
        reply = QMessageBox.question(
            self, "Confirmation",
            "Do you really want to stop the current analysis?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.analysis_handler.stop_analysis()
            self.duplicate_handler.stop_processing()
            self.stop_ui_updates()
            self.set_analysis_mode(False)

            self.status_indicator.update_status(
                "⏹️", "Analysis stopped by user",
                "#DC3545", "#F8D7DA", "#DC3545"
            )

    def set_analysis_mode(self, analyzing: bool) -> None:
        """
        Configure UI for analysis/idle mode.

        Args:
            analyzing: True if analysis is in progress, False otherwise.
        """
        self.analyze_btn.setEnabled(
            not analyzing and self.file_handler.get_file_count() > 1
        )
        self.stop_btn.setEnabled(analyzing)

        if self.config_tabs:
            self.config_tabs.setEnabled(not analyzing)

        if analyzing:
            self.repaint()

    def _on_hash_finished(self) -> None:
        """
        Handle hash analysis completion.
        """
        files = self.file_handler.get_all_files()

        # Update file statuses
        for file_path in files:
            if self.video_hasher.has_hash(file_path):
                self.file_handler.update_file_status(file_path, "✅ Analyzed")
            else:
                self.file_handler.update_file_status(file_path, "❌ Failed")

        self.file_progress.set_status("Complete", "#28A745")
        self.force_ui_update()

        # Start comparison analysis
        config = self.get_analysis_config()
        self.analysis_handler.start_comparison_analysis(
            files,
            config,
            duplicate_callback=self._on_duplicate_found,
            progress_callback=self.update_comparison_progress,
            status_callback=self.update_comparison_status,
            total_comparisons_callback=self.set_comparison_total,
            comparison_details_callback=self.update_comparison_details
        )

    def _on_comparison_finished(self) -> None:
        """
        Handle comparison analysis completion.
        """
        self.comparison_progress.set_status("Complete", "#28A745")
        self.stop_ui_updates()

        duplicates_count = self.duplicate_handler.get_duplicate_count()
        elapsed = self.analysis_handler.get_elapsed_time()

        if duplicates_count > 0:
            self.status_indicator.update_status(
                "🎯", f"Analysis complete! {duplicates_count} duplicate(s) found",
                "#28A745", "#D4EDDA", "#28A745"
            )

            # Start processing duplicates
            QTimer.singleShot(1000, lambda: self.duplicate_handler.process_duplicates(
                self, ComparisonDialog
            ))
        else:
            self.status_indicator.update_status(
                "✅", "Analysis complete - No duplicates found",
                "#28A745", "#D4EDDA", "#28A745"
            )

            threshold = self.threshold_spin.value()
            QMessageBox.information(
                self, "Analysis complete",
                f"No duplicates detected with {threshold}% threshold\n\n"
                f"Total time: {elapsed:.1f} seconds"
            )

        self.set_analysis_mode(False)

    def _on_duplicate_found(self, file1: str, file2: str, similarity: float) -> None:
        """
        Handle duplicate detection.

        Args:
            file1: First file path.
            file2: Second file path.
            similarity: Similarity percentage.
        """
        self.duplicate_handler.add_duplicate(file1, file2, similarity)

        count = self.duplicate_handler.get_duplicate_count()
        self.status_indicator.update_status(
            "🔍", f"Analysis in progress... {count} duplicate(s) found"
        )

    # Progress update methods
    def update_file_progress(self, current: int) -> None:
        """
        Update file analysis progress.

        Args:
            current: Current file count.
        """
        max_files = self.file_progress.progress_bar.maximum()
        if max_files > 0:
            self.file_progress.update_progress(current, max_files)

            if current > 0:
                elapsed = self.analysis_handler.get_elapsed_time()
                speed = current / elapsed if elapsed > 0 else 0
                self.file_progress.set_speed(speed)

                if speed > 0 and max_files > current:
                    remaining = (max_files - current) / speed
                    self.file_progress.set_time_remaining(remaining)

    def update_comparison_progress(self, current: int) -> None:
        """
        Update comparison progress.

        Args:
            current: Current comparison count.
        """
        max_comparisons = self.comparison_progress.progress_bar.maximum()
        if max_comparisons > 0:
            self.comparison_progress.update_progress(current, max_comparisons)

    def update_current_file_display(self, file_info: str) -> None:
        """
        Update current file being processed.

        Args:
            file_info: File information string.
        """
        self.file_progress.set_status(file_info, "#007BFF")

    def update_file_processed(self, file_path: str, success: bool) -> None:
        """
        Update status of a processed file.

        Args:
            file_path: Path to the file.
            success: Whether processing succeeded.
        """
        if success:
            self.file_handler.update_file_status(file_path, "✅ Analyzed")
        else:
            self.file_handler.update_file_status(file_path, "❌ Failed")

    def update_comparison_status(self, status: str) -> None:
        """
        Update comparison status message.

        Args:
            status: Status message.
        """
        self.status_indicator.update_status("🔍", status)

    def set_comparison_total(self, total: int) -> None:
        """
        Set total number of comparisons.

        Args:
            total: Total comparison count.
        """
        self.comparison_progress.progress_bar.setMaximum(total)
        self.comparison_progress.update_progress(0, total, "Comparisons in progress...")
        self.comparison_progress.set_status("Comparisons", "#007BFF")

    def update_hash_progress_details(
        self,
        current: int,
        total: int,
        filename: str
    ) -> None:
        """
        Update detailed hash progress.

        Args:
            current: Current file number.
            total: Total files.
            filename: Current filename.
        """
        self.file_progress.update_progress(current, total, f"{current}/{total}")
        short_filename = filename[:30] + "..." if len(filename) > 30 else filename
        self.file_progress.set_status(f"📄 {short_filename}", "#007BFF")

    def update_comparison_details(
        self,
        current: int,
        total: int,
        name1: str,
        name2: str
    ) -> None:
        """
        Update detailed comparison progress.

        Args:
            current: Current comparison number.
            total: Total comparisons.
            name1: First file name.
            name2: Second file name.
        """
        self.comparison_progress.update_progress(current, total, f"{current}/{total}")

        if len(name1) > 15 or len(name2) > 15:
            short_names = f"{name1[:15]}...↔{name2[:15]}..."
        else:
            short_names = f"{name1}↔{name2}"

        self.comparison_progress.set_status(f"🔍 {short_names}", "#007BFF")

    def handle_error(self, error_msg: str) -> None:
        """
        Handle analysis errors.

        Args:
            error_msg: Error message.
        """
        self.stop_ui_updates()
        QMessageBox.critical(self, "Error", f"Error during analysis: {error_msg}")
        self.set_analysis_mode(False)
        self.status_indicator.update_status(
            "❌", "Error during analysis",
            "#DC3545", "#F8D7DA", "#DC3545"
        )

    # UI update utilities
    def force_ui_update(self) -> None:
        """
        Force UI refresh.
        """
        try:
            self.file_list_widget.update()
            self.status_indicator.update()
            self.file_progress.update()
            self.comparison_progress.update()
            QApplication.processEvents()
        except Exception as e:
            logger.error(f"Error forcing UI update: {e}")

    def start_ui_updates(self) -> None:
        """
        Start periodic UI updates.
        """
        self.status_update_timer.start(100)

    def stop_ui_updates(self) -> None:
        """
        Stop periodic UI updates.
        """
        self.status_update_timer.stop()

    # Utility methods
    def auto_cleanup_database(self) -> None:
        """
        Automatically clean up database of missing files.
        """
        try:
            removed = self.video_hasher.db.cleanup_missing_files()
            if removed > 0:
                logger.info(f"Auto cleanup: {removed} missing files removed")
        except Exception as e:
            logger.error(f"Error in auto cleanup: {e}")

    def show_statistics(self) -> None:
        """
        Show statistics dialog.
        """
        try:
            stats = self.video_hasher.get_statistics()
            cache_stats = self.video_hasher.get_cache_stats()

            message = f"""📊 STATISTICS

🎬 ANALYZED FILES
   Total count: {stats.get('files_count', 0):,}
   Database size: {stats.get('db_size_kb', 0):.1f} KB

🔍 COMPARISONS
   Total: {stats.get('comparisons_count', 0):,}
   Ignored pairs: {stats.get('ignored_count', 0):,}

💾 MEMORY CACHE
   Hashes: {cache_stats.get('hash_cache_size', 0):,}
   Comparisons: {cache_stats.get('comparison_cache_size', 0):,}

⏱️ TIME SAVED
   Estimation: {stats.get('time_saved_seconds', 0):.0f} seconds"""

            QMessageBox.information(self, "Statistics", message)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot retrieve statistics: {e}")

    def show_pending_duplicates(self) -> None:
        """
        Show and process pending duplicates.
        """
        try:
            count = self.duplicate_handler.load_pending_duplicates()

            if count == 0:
                QMessageBox.information(self, "No duplicates", "No pending duplicates.")
                return

            reply = QMessageBox.question(
                self, "Pending duplicates",
                f"There are {count} pending duplicates.\n\n"
                f"Do you want to resume processing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.status_indicator.update_status(
                    "📋", f"Resuming {count} pending duplicates"
                )
                self.duplicate_handler.process_duplicates(self, ComparisonDialog)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot retrieve duplicates: {e}")

    def cleanup_resources(self) -> None:
        """
        Clean up all resources.
        """
        try:
            self.stop_ui_updates()
            self.analysis_handler.cleanup()
            logger.info("Resources cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up resources: {e}")

    def closeEvent(self, event) -> None:
        """
        Handle window close event.

        Args:
            event: Close event.
        """
        try:
            # Check for running operations
            if self.analysis_handler.is_analyzing():
                reply = QMessageBox.question(
                    self, "Confirmation",
                    "An analysis is in progress. Do you really want to quit?\n\n"
                    "Already computed results will be kept in cache.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    self.cleanup_resources()
                    widgets = self._get_widget_dict()
                    self.settings_manager.save_settings(widgets, self)
                    event.accept()
                else:
                    event.ignore()
                    return
            else:
                # Save settings before closing
                widgets = self._get_widget_dict()
                self.settings_manager.save_settings(widgets, self)
                event.accept()

            # Emit closed signal
            self.closed.emit()

        except Exception as e:
            logger.error(f"Error closing application: {e}")
            # Try to save settings anyway
            try:
                widgets = self._get_widget_dict()
                self.settings_manager.save_settings(widgets, self)
            except:
                pass
            event.accept()
            self.closed.emit()
