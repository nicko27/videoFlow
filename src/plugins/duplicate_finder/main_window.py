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
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox,
    QSplitter, QApplication, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

# Import local modules
try:
    from .video_hasher import VideoHasher
    from .comparison_dialog import ComparisonDialog
    from .subsequence_comparison_dialog import SubsequenceComparisonDialog
    from .progress_widgets import FileListWidget
    from .ui.panels import UIPanels
    from .managers.settings_manager import SettingsManager
    from .handlers.file_handler import FileHandler
    from .handlers.analysis_handler import AnalysisHandler
    from .handlers.duplicate_handler import DuplicateHandler
    from .handlers.audio_first_handler import AudioFirstHandler
    from .audio_config import AudioFirstConfig
    from .themes import get_current_theme
    from .layouts import LayoutManager, LayoutType
    from .audio_fingerprinting import AudioFingerprintDetector, PrecisionMode
    from .advanced_progress_dialog import AdvancedProgressDialog
    from .analysis import AdvancedDuplicatePipeline
except ImportError:
    # Fallback for direct imports
    from video_hasher import VideoHasher
    from comparison_dialog import ComparisonDialog
    from subsequence_comparison_dialog import SubsequenceComparisonDialog
    from progress_widgets import FileListWidget
    from ui.panels import UIPanels
    from managers.settings_manager import SettingsManager
    from handlers.file_handler import FileHandler
    from handlers.analysis_handler import AnalysisHandler
    from handlers.duplicate_handler import DuplicateHandler
    from handlers.audio_first_handler import AudioFirstHandler
    from audio_config import AudioFirstConfig
    from themes import get_current_theme
    from layouts import LayoutManager, LayoutType
    from audio_fingerprinting import AudioFingerprintDetector, PrecisionMode
    from advanced_progress_dialog import AdvancedProgressDialog
    from analysis import AdvancedDuplicatePipeline

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
        self.setWindowTitle("🔍 Détecteur de doublons vidéo")
        self.setMinimumSize(1000, 800)

        # Initialize core components (video_hasher will be created after settings load)
        self.video_hasher = None

        # Initialize UI components (will be set in setup_ui)
        self.file_list_widget: Optional[FileListWidget] = None
        self.status_indicator = None
        self.stats_counter = None
        self.file_progress = None
        self.duplicate_progress = None
        self.config_tabs = None
        self.analyze_btn = None
        self.stop_btn = None
        self.reload_last_folder_btn = None

        # Initialize parameter widgets (will be set in setup_ui)
        self.threshold_spin = None
        self.hash_method_combo = None
        self.hash_workers_spin = None
        self.comparison_workers_spin = None
        self.batch_size_spin = None
        self.comparison_algorithm_combo = None
        self.hash_timeout_spin = None
        self.comparison_timeout_spin = None
        self.enable_scene_check = None
        self.scene_precision_combo = None
        self.scene_algorithm_combo = None
        self.scene_min_match_spin = None
        self.scene_min_duration_spin = None
        self.scene_cache_size_spin = None
        self.hash_debugger_v2 = None

        # Initialize managers and handlers
        self.settings_manager = SettingsManager()
        self.file_handler: Optional[FileHandler] = None
        self.analysis_handler: Optional[AnalysisHandler] = None
        self.duplicate_handler: Optional[DuplicateHandler] = None
        self.scene_detector = None  # Audio fingerprint detector for scene detection
        self.scene_worker = None  # Worker for background scene detection

        # Layout manager
        self.layout_manager = LayoutManager()
        # Load saved layout preference (defaults to classic)
        saved_layout = self.settings_manager.get_layout_preference()
        try:
            self.current_layout = LayoutType(saved_layout)
        except ValueError:
            logger.warning(f"Invalid saved layout '{saved_layout}', using classic")
            self.current_layout = LayoutType.CLASSIC
        self.layout_selector = None

        # UI update timer
        self.status_update_timer = QTimer()
        self.status_update_timer.timeout.connect(self.force_ui_update)
        self.status_update_timer.setSingleShot(False)

        # Setup UI
        self.setup_ui()

        # Load settings first (to get hash method)
        self._load_settings()

        # Create video hasher with selected method
        hash_method = self.hash_method_combo.currentData() if self.hash_method_combo else 'pHash'
        self.video_hasher = VideoHasher(method=hash_method)

        # Set video hasher on hash debugger widget
        if self.hash_debugger_v2:
            self.hash_debugger_v2.set_video_hasher(self.video_hasher)
            self.hash_debugger_v2.settings_manager = self.settings_manager

        # Initialize handlers after video_hasher is created
        self.file_handler = FileHandler(self.file_list_widget)
        self.analysis_handler = AnalysisHandler(self.video_hasher)
        self.duplicate_handler = DuplicateHandler(self.video_hasher, self.file_handler)
        self.audio_first_handler = AudioFirstHandler(self.video_hasher, self.analysis_handler)

        # Connect analysis handler signals
        self._connect_analysis_signals()

        # Connect duplicate handler signals
        self._connect_duplicate_handler_signals()

        # Connect audio-first handler signals
        self._connect_audio_first_signals()

        # Connect settings change signals
        self._connect_settings_signals()

        # Auto cleanup database
        self.auto_cleanup_database()

        # Check and show last folder button if available
        self.check_and_show_last_folder_button()

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
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create title bar at the very top
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)

        # Create file list widget (needed for both panels)
        self.file_list_widget = FileListWidget()

        # Create panels
        left_panel = self._create_left_panel()
        right_panel, right_widgets = UIPanels.create_right_panel()

        # Store right panel widgets
        self.status_indicator = right_widgets['status_indicator']
        self.stats_counter = right_widgets['stats_counter']
        self.file_progress = right_widgets['file_progress']
        self.duplicate_progress = right_widgets['duplicate_progress']
        self.audio_progress = right_widgets.get('audio_progress')  # New audio hash progress

        # Create layout selector widget (no longer in header)
        layout_selector_widget = self._create_layout_selector()

        # Use LayoutManager to create the layout (without header)
        layout_container = self.layout_manager.create_layout(
            self.current_layout,
            left_panel,
            right_panel,
            layout_selector_widget
        )

        main_layout.addWidget(layout_container)
        # CRITIQUE: Définir le stretch factor pour que le container s'étende et remplisse tout l'espace disponible
        main_layout.setStretch(1, 1)  # Index 1 = layout_container (index 0 = title_bar)

        # Initial button states
        if self.analyze_btn:
            self.analyze_btn.setEnabled(False)
        if self.stop_btn:
            self.stop_btn.setEnabled(False)

        # Apply initial theme
        self.apply_theme()

    def _create_title_bar(self) -> QWidget:
        """
        Create compact title bar at the very top.

        Returns:
            QWidget containing just the title.
        """
        theme = get_current_theme()

        title_widget = QWidget()
        title_widget.setMaximumHeight(18)  # Limite stricte de la hauteur totale
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(5, 0, 5, 0)  # Aucune marge verticale
        title_layout.setSpacing(0)

        title = QLabel("🔍 Détecteur de doublons vidéo")
        title.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_style = theme.get_title_style()
        # Suppression complète du padding vertical et limitation stricte de la hauteur
        title.setStyleSheet(title_style + " QLabel { padding: 0px 5px; margin: 0px; max-height: 18px; line-height: 18px; }")
        title_layout.addWidget(title)

        return title_widget

    def _create_layout_selector(self) -> QWidget:
        """
        Create layout selector widget (separate from title).

        Returns:
            QWidget containing the layout selector.
        """
        from PyQt6.QtWidgets import QHBoxLayout, QComboBox
        from .design_system import Colors, Spacing, Typography

        selector_widget = QWidget()
        selector_layout = QHBoxLayout(selector_widget)
        selector_layout.setContentsMargins(5, 5, 5, 5)
        selector_layout.setSpacing(10)

        # Layout selector label
        layout_label = QLabel("📐 Disposition:")
        layout_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XS))
        layout_label.setStyleSheet(f"color: {Colors.GRAY_700};")
        selector_layout.addWidget(layout_label)

        # Layout selector combo
        self.layout_selector = QComboBox()
        self.layout_selector.setMinimumWidth(180)
        self.layout_selector.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XS))
        self.layout_selector.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_SM}px;
                padding: {Spacing.XS}px {Spacing.SM}px;
                background-color: {Colors.WHITE};
                color: {Colors.BLACK};
            }}
            QComboBox:hover {{
                border-color: {Colors.PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: {Spacing.XS}px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {Colors.BORDER_DEFAULT};
                background-color: {Colors.WHITE};
                selection-background-color: {Colors.PRIMARY_LIGHT};
                selection-color: {Colors.BLACK};
            }}
        """)

        # Populate layouts
        layout_names = self.layout_manager.get_layout_names()
        for key, name in layout_names.items():
            self.layout_selector.addItem(name, key)

        # Set current layout in selector
        for i in range(self.layout_selector.count()):
            if self.layout_selector.itemData(i) == self.current_layout.value:
                self.layout_selector.setCurrentIndex(i)
                break

        self.layout_selector.currentIndexChanged.connect(self.on_layout_changed)
        selector_layout.addWidget(self.layout_selector)
        selector_layout.addStretch()

        return selector_widget

    def apply_theme(self) -> None:
        """
        Apply current theme to all UI components.
        """
        theme = get_current_theme()

        # Update main window background
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme.get_colors()['bg_main']};
            }}
        """)

        # Update progress widgets if they exist
        if hasattr(self, 'file_progress') and self.file_progress:
            self.file_progress.progress_bar.setStyleSheet(theme.get_progress_style())

        if hasattr(self, 'duplicate_progress') and self.duplicate_progress:
            self.duplicate_progress.progress_bar.setStyleSheet(theme.get_progress_style())

        # Force UI refresh
        if hasattr(self, 'centralWidget') and self.centralWidget():
            self.centralWidget().update()

    def on_theme_changed(self, theme_key: str) -> None:
        """
        Handle theme change event.

        Args:
            theme_key: Key of the new theme.
        """
        logger.info(f"Theme changed to: {theme_key}")
        self.apply_theme()

        # Recreate UI with new theme
        # Store current state
        files = []
        if self.file_list_widget:
            files = self.file_list_widget.get_files()

        # Recreate UI
        self.setup_ui()

        # ALWAYS recreate file_handler with new widget reference
        if self.file_list_widget:
            self.file_handler = FileHandler(self.file_list_widget)

        # Restore files if any
        if files and self.file_handler:
            self.file_handler.add_files(files)

    def on_layout_changed(self, index: int) -> None:
        """
        Handle layout change event.

        Args:
            index: Index of the selected layout in the combo box.
        """
        if not self.layout_selector:
            return

        layout_key = self.layout_selector.currentData()
        if not layout_key:
            return

        # Convert string key to LayoutType enum
        try:
            new_layout = LayoutType(layout_key)
        except ValueError:
            logger.error(f"Invalid layout key: {layout_key}")
            return

        if new_layout == self.current_layout:
            return  # No change

        logger.info(f"Layout changed to: {layout_key}")
        self.current_layout = new_layout

        # Store current state
        files = []
        if self.file_list_widget:
            files = self.file_list_widget.get_files()

        # Recreate UI with new layout
        self.setup_ui()

        # ALWAYS recreate file_handler with new widget reference
        if self.file_list_widget:
            self.file_handler = FileHandler(self.file_list_widget)

        # Restore files if any
        if files and self.file_handler:
            self.file_handler.add_files(files)

        # Save layout preference
        self.settings_manager.save_layout_preference(layout_key)

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
            'reload_last_folder': self.reload_last_folder,
            'clear_list': self.clear_list,
            'clear_cache': self.clear_cache,
            'reset_folder': self.reset_folder,
            'apply_preset': self.apply_preset,
            'analyze': self.start_analysis,
            'stop': self.stop_analysis,
            'show_stats': self.show_statistics,
            'show_pending': self.show_pending_duplicates,
            'run_advanced_mode': self.run_advanced_mode,
            'close': self.close
        }

        # Create panel
        panel = UIPanels.create_left_panel(self.file_list_widget, callbacks)

        # Extract references to parameter widgets and buttons
        # Find the QTabWidget first
        from PyQt6.QtWidgets import QTabWidget
        config_tabs = panel.findChild(QTabWidget)
        self.config_tabs = config_tabs

        # Get tabs by index (Files=0, Settings=1, Debug=2)
        params_tab = None
        debug_tab = None
        if config_tabs:
            params_tab = config_tabs.widget(1)  # Settings tab
            debug_tab = config_tabs.widget(2)   # Debug tab

        if params_tab:
            # Debug: log available attributes
            logger.debug(f"params_tab attributes: {[attr for attr in dir(params_tab) if not attr.startswith('_')]}")

            # Video comparison widgets (renamed in new version)
            self.threshold_spin = getattr(params_tab, 'video_threshold_spin', None)
            self.hash_method_combo = getattr(params_tab, 'hash_method_combo', None)
            self.hash_workers_spin = getattr(params_tab, 'hash_workers_spin', None)
            self.comparison_workers_spin = getattr(params_tab, 'comparison_workers_spin', None)
            self.batch_size_spin = getattr(params_tab, 'batch_size_spin', None)
            self.comparison_algorithm_combo = None  # Removed in new version
            self.hash_timeout_spin = getattr(params_tab, 'hash_timeout_spin', None)
            self.comparison_timeout_spin = getattr(params_tab, 'comparison_timeout_spin', None)

            # Scene detection widgets (may not exist in new version)
            self.enable_scene_check = getattr(params_tab, 'enable_scene_check', None)
            self.scene_precision_combo = getattr(params_tab, 'scene_precision_combo', None)
            self.scene_algorithm_combo = getattr(params_tab, 'scene_algorithm_combo', None)
            self.scene_min_match_spin = getattr(params_tab, 'scene_min_match_spin', None)
            self.scene_min_duration_spin = getattr(params_tab, 'scene_min_duration_spin', None)
            self.scene_cache_size_spin = getattr(params_tab, 'scene_cache_size_spin', None)

            # Log which widgets were found
            logger.debug(f"threshold_spin: {self.threshold_spin}")
            logger.debug(f"hash_method_combo: {self.hash_method_combo}")
        else:
            logger.error("params_tab is None! Cannot extract widget references")

        if debug_tab:
            self.hash_debugger_v2 = debug_tab.hash_debugger_v2

        # Extract button references
        for child in panel.findChildren(QWidget):
            if hasattr(child, 'analyze_btn'):
                self.analyze_btn = child.analyze_btn
                self.stop_btn = child.stop_btn
                break
            if hasattr(child, 'reload_last_folder_btn'):
                self.reload_last_folder_btn = child.reload_last_folder_btn

        return panel

    def _connect_analysis_signals(self) -> None:
        """
        Connect analysis handler signals to UI update methods.
        """
        if self.analysis_handler:
            self.analysis_handler.hash_finished.connect(self._on_hash_finished)
            self.analysis_handler.comparison_finished.connect(self._on_comparison_finished)
            self.analysis_handler.analysis_error.connect(self.handle_error)

    def _connect_duplicate_handler_signals(self) -> None:
        """
        Connect duplicate handler signals for processing workflow.
        """
        if self.duplicate_handler:
            self.duplicate_handler.all_duplicates_processed.connect(self._on_all_duplicates_processed)
            self.duplicate_handler.all_subsequences_processed.connect(self._on_all_subsequences_processed)

    def _connect_audio_first_signals(self) -> None:
        """Connect audio-first handler signals to UI updates."""
        if self.audio_first_handler:
            # Phase 1: Audio extraction
            self.audio_first_handler.audio_progress.connect(self._on_audio_extraction_progress)
            self.audio_first_handler.audio_finished.connect(self._on_audio_extraction_finished)

            # Phase 2: Audio comparison
            self.audio_first_handler.audio_comparison_progress.connect(self._on_audio_comparison_progress)
            self.audio_first_handler.audio_comparison_finished.connect(self._on_audio_comparison_finished)

            # Phase 3: Video hashing
            self.audio_first_handler.video_hash_progress.connect(self._on_video_hash_progress)
            self.audio_first_handler.video_hash_finished.connect(self._on_video_hash_finished)

            # Errors and status
            self.audio_first_handler.analysis_error.connect(self.handle_error)
            self.audio_first_handler.status_update.connect(self._on_status_update)

    def _connect_settings_signals(self) -> None:
        """
        Connect parameter widget signals for auto-save.
        """
        widgets = [
            self.threshold_spin, self.hash_workers_spin,
            self.comparison_workers_spin, self.batch_size_spin,
            self.hash_timeout_spin, self.comparison_timeout_spin,
            self.scene_min_match_spin, self.scene_min_duration_spin,
            self.scene_cache_size_spin
        ]

        for widget in widgets:
            if widget:
                widget.valueChanged.connect(self._on_settings_changed)

        # Connect checkboxes separately (uses different signal)
        if self.enable_scene_check:
            self.enable_scene_check.stateChanged.connect(self._on_settings_changed)

        # Connect combobox separately (uses different signal)
        if self.hash_method_combo:
            self.hash_method_combo.currentIndexChanged.connect(self._on_settings_changed)

        if self.comparison_algorithm_combo:
            self.comparison_algorithm_combo.currentIndexChanged.connect(self._on_settings_changed)

        if self.scene_precision_combo:
            self.scene_precision_combo.currentIndexChanged.connect(self._on_settings_changed)

        if self.scene_algorithm_combo:
            self.scene_algorithm_combo.currentIndexChanged.connect(self._on_settings_changed)

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
            'hash_method_combo': self.hash_method_combo,
            'hash_workers_spin': self.hash_workers_spin,
            'comparison_workers_spin': self.comparison_workers_spin,
            'batch_size_spin': self.batch_size_spin,
            'comparison_algorithm_combo': self.comparison_algorithm_combo,
            'hash_timeout_spin': self.hash_timeout_spin,
            'comparison_timeout_spin': self.comparison_timeout_spin,
            'enable_scene_check': self.enable_scene_check,
            'scene_precision_combo': self.scene_precision_combo,
            'scene_algorithm_combo': self.scene_algorithm_combo,
            'scene_min_match_spin': self.scene_min_match_spin,
            'scene_min_duration_spin': self.scene_min_duration_spin,
            'scene_cache_size_spin': self.scene_cache_size_spin
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
        from PyQt6.QtWidgets import QFileDialog
        import os

        # Get last used folder
        last_folder = self.settings_manager.get_last_folder()

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select video files",
            last_folder,
            "Videos (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.m4v);;All files (*.*)"
        )

        if not files:
            return

        # Save the folder of the first selected file
        if files:
            folder = os.path.dirname(files[0])
            self.settings_manager.save_last_folder(folder)

        count = self.file_handler.add_files(files)

        if count > 0:
            # Update cache status for new files
            all_files = self.file_handler.get_all_files()
            self.file_handler.batch_update_cache_status(all_files, self.video_hasher)

            # Update UI
            self.force_ui_update()
            self.analyze_btn.setEnabled(self.file_handler.get_file_count() > 1)

            self.status_indicator.update_status(
                "✅", f"{count} file(s) added",
                "#28A745", "#D4EDDA", "#28A745"
            )

    def add_folder(self, folder_path: str = None) -> None:
        """
        Add all video files from a folder.

        Args:
            folder_path: Path to folder. If None, shows dialog.
        """
        from PyQt6.QtWidgets import QFileDialog

        # Ignore button checked state (boolean from clicked signal)
        # Only use folder_path if it's actually a string path
        if not isinstance(folder_path, str):
            # Get last used folder
            last_folder = self.settings_manager.get_last_folder()
            folder_path = QFileDialog.getExistingDirectory(self, "Select folder", last_folder)

        if not folder_path:
            return

        count = self.file_handler.add_folder(folder_path)

        if count > 0:
            # Save last folder
            self.settings_manager.save_last_folder(folder_path)

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

    def reload_last_folder(self) -> None:
        """
        Reload the last opened folder.
        """
        last_folder = self.settings_manager.get_last_folder()

        if last_folder and os.path.exists(last_folder):
            self.add_folder(last_folder)
            # Hide the reload button after use
            if self.reload_last_folder_btn:
                self.reload_last_folder_btn.setVisible(False)
        else:
            QMessageBox.warning(
                self,
                "Dossier introuvable",
                f"Le dernier dossier n'existe plus :\n{last_folder}"
            )
            # Clear invalid last folder
            self.settings_manager.save_last_folder("")
            if self.reload_last_folder_btn:
                self.reload_last_folder_btn.setVisible(False)

    def check_and_show_last_folder_button(self) -> None:
        """
        Check if there's a last folder and show reload button if it exists.
        """
        last_folder = self.settings_manager.get_last_folder()

        if last_folder and os.path.exists(last_folder) and self.reload_last_folder_btn:
            # Update button text with folder name
            folder_name = os.path.basename(last_folder)
            if len(folder_name) > 25:
                folder_name = folder_name[:22] + "..."
            self.reload_last_folder_btn.setText(f"🔄 Reload: {folder_name}")
            self.reload_last_folder_btn.setToolTip(f"Reload last folder:\n{last_folder}")
            self.reload_last_folder_btn.setVisible(True)
            logger.info(f"Last folder available: {last_folder}")
        elif self.reload_last_folder_btn:
            self.reload_last_folder_btn.setVisible(False)

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
            QMessageBox.critical(self, "Erreur", f"Impossible de vider le cache : {e}")

    def reset_folder(self) -> None:
        """
        Reset the last used folder path.
        """
        self.settings_manager.reset_last_folder()
        self.status_indicator.update_status(
            "🔄", "Folder path reset",
            "#17A2B8", "#D1ECF1", "#17A2B8"
        )
        logger.info("Last folder path has been reset")

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
        icon = {
            "maximum_speed": "⚡",
            "balanced": "⚖️",
            "maximum_quality": "🎯"
        }[preset_type]
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
                self, "Attention",
                "Au moins 2 fichiers sont requis pour détecter les doublons"
            )
            return

        # Validate files
        valid_files, invalid_files = self.file_handler.validate_files_for_analysis()

        if len(valid_files) < 2:
            QMessageBox.warning(self, "Erreur", "Pas assez de fichiers valides")
            return

        # Set UI to analysis mode
        self.set_analysis_mode(True)
        self.duplicate_handler.processing_stopped = False

        # Reset stats counters
        self.stats_counter.reset()

        # Start UI updates
        self.start_ui_updates()

        self.status_indicator.update_status(
            "📄", "Analysis in progress...",
            "#007BFF", "#CCE5FF", "#007BFF"
        )

        # Get analysis configuration
        config = self.get_analysis_config()

        # Get configuration from UI for audio-first analysis
        params_tab = self._get_params_tab()
        if params_tab is None:
            logger.error("Could not find parameters tab")
            QMessageBox.critical(self, "Erreur", "Impossible de charger les paramètres d'analyse")
            self.set_analysis_mode(False)
            return

        audio_config = AudioFirstConfig.from_ui_widgets(params_tab)

        # Start audio-first analysis
        logger.info("Starting audio-first workflow")
        self.audio_first_handler.start_analysis(
            valid_files,
            audio_config,
            progress_callbacks={
                'audio_progress': self._on_audio_extraction_progress
            }
        )

        # Initialize progress displays
        if self.audio_progress:
            self.audio_progress.update_progress(0, len(valid_files), "Starting audio extraction...")
            self.audio_progress.set_status("Starting", "#FFC107")

    def stop_analysis(self) -> None:
        """
        Stop the current analysis.
        """
        reply = QMessageBox.question(
            self, "Confirmation",
            "Voulez-vous vraiment arrêter l'analyse en cours ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Stop hash and comparison workers
            self.analysis_handler.stop_analysis()

            # Stop audio-first handler
            if self.audio_first_handler:
                self.audio_first_handler.stop_analysis()

            # Stop scene detection worker
            if self.scene_worker and self.scene_worker.isRunning():
                logger.info("Stopping scene detection worker...")
                self.scene_worker.stop()
                # Wait with timeout to prevent indefinite blocking
                if not self.scene_worker.wait(5000):  # 5 second timeout
                    logger.warning("Scene worker did not stop gracefully, forcing termination")
                    self.scene_worker.terminate()
                self.scene_worker = None

            # Stop duplicate processing
            self.duplicate_handler.stop_processing()

            self.stop_ui_updates()
            self.set_analysis_mode(False)

            self.status_indicator.update_status(
                "⏹️", "Analysis stopped by user",
                "#DC3545", "#F8D7DA", "#DC3545"
            )

    def run_advanced_mode(self) -> None:
        """
        Run the advanced 3-level duplicate detection analysis.

        This mode performs a thorough 3-level analysis:
        - Level 1: LSH audio fingerprinting (loose filtering)
        - Level 2: Long-period audio comparison (refined filtering)
        - Level 3: pHash visual confirmation (final validation)
        """
        # Check file count
        file_count = self.file_handler.get_file_count()

        if file_count < 2:
            QMessageBox.warning(
                self, "Attention",
                "Au moins 2 fichiers sont requis pour détecter les doublons"
            )
            return

        # Get configuration
        config = self.get_analysis_config()

        # Check if advanced mode is enabled in settings
        if 'advanced_mode' not in config or not config['advanced_mode'].get('enabled', False):
            reply = QMessageBox.warning(
                self, "Détection de Scènes",
                "La détection de scènes n'est pas activée.\n\n"
                "Activer maintenant ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                return

            # Enable advanced mode in settings
            params_tab = self._get_params_tab()
            if params_tab and hasattr(params_tab, 'enable_advanced_mode'):
                params_tab.enable_advanced_mode.setChecked(True)
                # Save settings
                widgets = self._get_widget_dict()
                self.settings_manager.save_settings(widgets, self)
                config = self.get_analysis_config()

        # Get advanced mode configuration
        advanced_config = config.get('advanced_mode', {})

        # Show confirmation dialog
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Détection de Scènes")
        msg.setText(
            f"🎬 Analyse de {file_count} vidéos\n\n"
            f"Cette détection utilise :\n"
            f"• Audio (empreintes courtes et longues)\n"
            f"• Analyse visuelle (frames)\n"
            f"• Confirmation multi-critères\n\n"
            f"Cela peut prendre plusieurs minutes."
        )
        msg.setInformativeText("Lancer l'analyse ?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)

        if msg.exec() != QMessageBox.StandardButton.Yes:
            return

        # Get valid files for analysis
        valid_files, invalid_files = self.file_handler.validate_files_for_analysis()

        if not valid_files:
            QMessageBox.warning(
                self, "Aucun fichier valide",
                "Aucun fichier valide n'a été trouvé pour l'analyse.\n\n"
                f"Fichiers invalides : {len(invalid_files)}"
            )
            return

        logger.info(f"Starting advanced 3-level mode with {len(valid_files)} valid files")
        logger.info(f"Advanced config: {advanced_config}")

        try:
            # Create the advanced pipeline
            pipeline = AdvancedDuplicatePipeline(
                config=advanced_config,
                db_manager=self.video_hasher.db
            )

            # Create and show progress dialog
            progress_dialog = AdvancedProgressDialog(self)
            progress_dialog.start_analysis(pipeline, valid_files)

            # Execute dialog (blocks until analysis completes or is cancelled)
            result = progress_dialog.exec()

            if result == progress_dialog.DialogCode.Accepted:
                # Analysis completed successfully
                logger.info("Advanced 3-level analysis completed successfully")

                # Show success message
                QMessageBox.information(
                    self, "Analyse Terminée",
                    "✅ Détection de scènes terminée !\n\n"
                    "Les doublons détectés sont disponibles dans l'onglet Résultats."
                )

                # Refresh duplicate handler to load new results
                self.duplicate_handler.load_duplicates()

            else:
                # Analysis was cancelled
                logger.info("Advanced 3-level analysis was cancelled by user")

        except ImportError as e:
            logger.error(f"Missing dependencies for advanced mode: {e}")
            QMessageBox.critical(
                self, "Dépendances Manquantes",
                "❌ Bibliothèques requises manquantes.\n\n"
                f"Erreur : {e}\n\n"
                "Installation :\n"
                "pip install datasketch librosa soundfile scipy"
            )
        except Exception as e:
            logger.error(f"Error starting advanced mode: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Erreur",
                f"❌ Une erreur s'est produite lors du démarrage de l'analyse :\n\n{e}"
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
            progress_callback=self.update_duplicate_progress,
            status_callback=self.update_comparison_status,
            total_comparisons_callback=self.set_comparison_total,
            comparison_details_callback=self.update_comparison_details
        )

    def _on_comparison_finished(self) -> None:
        """
        Handle comparison analysis completion.
        """
        self.duplicate_progress.set_status("Complete", "#28A745")

        # Check if scene detection is enabled
        config = self.get_analysis_config()
        scene_config = config.get('scene_detection', {})
        is_enabled = scene_config.get('enabled', False)

        logger.info(f"Scene detection enabled: {is_enabled}")
        if is_enabled:
            logger.info(f"Scene detection parameters: precision={scene_config.get('precision_mode', 'balanced')}, "
                       f"min_match_ratio={scene_config.get('min_match_ratio', 0)*100:.1f}%")
            # Start scene detection
            self._start_scene_detection()
        else:
            logger.info("Scene detection skipped (not enabled)")
            # No scene detection, finish analysis
            self._finish_analysis()

    def _start_scene_detection(self) -> None:
        """
        Start scene detection analysis using audio fingerprinting.
        Supports 3 algorithms: hash_index (fast), shazam (ultra-fast), sliding_window (classic).
        """
        try:
            from .workers.scene_worker import SceneDetectionWorker

            config = self.get_analysis_config()
            scene_config = config.get('scene_detection', {})

            # Get algorithm choice
            algorithm = scene_config.get('algorithm', 'hash_index')

            # Get precision mode (for Chromaprint-based methods)
            precision_mode_name = scene_config.get('precision_mode', 'balanced')
            if precision_mode_name == 'maximum':
                precision_mode = PrecisionMode.MAXIMUM
            elif precision_mode_name == 'fast':
                precision_mode = PrecisionMode.FAST
            else:
                precision_mode = PrecisionMode.BALANCED

            # Create detector based on algorithm choice
            if algorithm == 'shazam':
                # Use Shazam algorithm (ultra-fast, experimental)
                try:
                    from .shazam_detector import ShazamSceneDetector
                    self.scene_detector = ShazamSceneDetector(
                        sample_rate=11025,
                        min_match_ratio=scene_config.get('min_match_ratio', 0.85),
                        min_cluster_size=10
                    )
                    algorithm_name = "Shazam (ultra-fast)"
                    logger.info("Using Shazam algorithm for scene detection")
                except ImportError as e:
                    logger.warning(f"Shazam detector not available: {e}, falling back to hash index")
                    algorithm = 'hash_index'

            if algorithm in ['hash_index', 'sliding_window']:
                # Use Chromaprint-based detector (hash_index or sliding_window)
                if self.scene_detector is None or not isinstance(self.scene_detector, AudioFingerprintDetector):
                    self.scene_detector = AudioFingerprintDetector(
                        precision_mode=precision_mode,
                        min_match_ratio=scene_config.get('min_match_ratio', 0.85),
                        max_cache_items=scene_config.get('cache_size', 500)
                    )

                if algorithm == 'hash_index':
                    algorithm_name = "Hash Index (10-100x faster)"
                    logger.info("Using Hash Index algorithm for scene detection")
                else:
                    algorithm_name = "Sliding Window (improved)"
                    logger.info("Using improved Sliding Window algorithm for scene detection")

            # Update UI
            self.status_indicator.update_status(
                "🎬", f"Detecting scenes ({algorithm_name})...",
                "#17A2B8", "#D1ECF1", "#17A2B8"
            )

            # Get all files
            files = self.file_handler.get_all_files()

            # Stop any existing scene worker
            if self.scene_worker and self.scene_worker.isRunning():
                logger.info("Stopping existing scene worker...")
                self.scene_worker.stop()
                self.scene_worker.wait()

            # Create and configure worker with algorithm choice
            logger.info(f"Starting scene detection on {len(files)} files using {algorithm_name}")
            self.scene_worker = SceneDetectionWorker(
                self.scene_detector,
                files,
                algorithm=algorithm  # Pass algorithm choice to worker
            )

            # Connect signals
            def on_progress(current: int, total: int, message: str):
                """Update progress display."""
                if self.duplicate_progress:
                    self.duplicate_progress.update_progress(current, total, message)
                self.force_ui_update()

            def on_scene_found(short_video: str, long_video: str, result: dict):
                """Handle each found scene."""
                # Store in database (scenes use same table as subsequences)
                # Convert start_time_seconds to frame index (approximate)
                start_frame_idx = int(result.get('start_time_seconds', 0) * 25)  # Assume 25fps

                self.video_hasher.db.store_subsequence_detection(
                    short_video,
                    long_video,
                    result['match_ratio'],
                    start_frame_idx,
                    result['confidence']
                )

                # Add to duplicate handler for processing (scenes are shown like subsequences)
                self.duplicate_handler.add_subsequence(short_video, long_video, result)

            def on_finished(scenes: list):
                """Handle completion of scene detection."""
                logger.info(f"Scene detection complete: {len(scenes)} found")

                # Clean up worker reference
                self.scene_worker = None

                # Finish analysis (will process scenes after duplicates)
                self._finish_analysis()

            def on_error(error_msg: str):
                """Handle error in scene detection."""
                logger.error(f"Error during scene detection: {error_msg}")
                QMessageBox.warning(
                    self,
                    "Erreur de détection de scènes",
                    f"Une erreur s'est produite lors de la détection de scènes :\n{error_msg}\n\n"
                    f"Poursuite avec les résultats de doublons..."
                )

                # Clean up worker reference
                self.scene_worker = None

                # Finish analysis anyway
                self._finish_analysis()

            self.scene_worker.progress.connect(on_progress)
            self.scene_worker.scene_found.connect(on_scene_found)
            self.scene_worker.finished.connect(on_finished)
            self.scene_worker.error.connect(on_error)

            # Start worker
            self.scene_worker.start()

        except Exception as e:
            logger.error(f"Error setting up scene detection: {e}")
            QMessageBox.warning(
                self,
                "Erreur de détection de scènes",
                f"Une erreur s'est produite lors de la configuration de la détection de scènes :\n{str(e)}\n\n"
                f"Poursuite avec les résultats de doublons..."
            )
            self._finish_analysis()

    def _finish_analysis(self) -> None:
        """
        Complete the analysis and show results.
        """
        self.stop_ui_updates()

        duplicates_count = self.duplicate_handler.get_duplicate_count()
        subsequence_count = self.duplicate_handler.get_subsequence_count()
        elapsed = self.analysis_handler.get_elapsed_time()

        # Update stats counter
        self.stats_counter.update_duplicates(duplicates_count)
        self.stats_counter.update_subsequences(subsequence_count)

        if duplicates_count > 0:
            self.status_indicator.update_status(
                "🎯", f"Analysis complete! {duplicates_count} duplicate(s) found",
                "#28A745", "#D4EDDA", "#28A745"
            )

            # Start processing duplicates (subsequences will be processed after)
            QTimer.singleShot(1000, lambda: self.duplicate_handler.process_duplicates(
                self, ComparisonDialog
            ))
        elif subsequence_count > 0:
            # No duplicates but have subsequences
            self.status_indicator.update_status(
                "🎬", f"Analysis complete! {subsequence_count} subsequence(s) found",
                "#17A2B8", "#D1ECF1", "#17A2B8"
            )

            # Start processing subsequences directly
            QTimer.singleShot(1000, lambda: self.duplicate_handler.process_subsequences(
                self, SubsequenceComparisonDialog
            ))
        else:
            # No duplicates or subsequences
            self.status_indicator.update_status(
                "✅", "Analysis complete - No duplicates found",
                "#28A745", "#D4EDDA", "#28A745"
            )

            threshold_duplicates = self.threshold_spin.value() if self.threshold_spin else 90.0
            QMessageBox.information(
                self, "Analyse terminée",
                f"Aucun doublon détecté\n\n"
                f"Seuil de similarité : {threshold_duplicates}%\n"
                f"Fichiers analysés : {len(self.file_handler.get_all_files())}\n"
                f"Temps total : {elapsed:.1f} secondes"
            )

        self.set_analysis_mode(False)

    def _on_all_duplicates_processed(self) -> None:
        """
        Called when all duplicates have been processed.
        Show final completion message.
        """
        logger.info("All duplicates processed")
        # Show final completion message
        self._show_final_completion_message()

    def _on_all_subsequences_processed(self) -> None:
        """
        Called when all subsequences have been processed.
        Show final completion message.
        """
        logger.info("All subsequences processed")
        self._show_final_completion_message()

    def _show_final_completion_message(self) -> None:
        """
        Show final completion message after all processing is done.
        """
        elapsed = self.analysis_handler.get_elapsed_time()

        self.status_indicator.update_status(
            "✅", "All processing complete!",
            "#28A745", "#D4EDDA", "#28A745"
        )

        duplicate_count = self.duplicate_handler.get_duplicate_count()
        QMessageBox.information(
            self, "Traitement terminé",
            f"Traitement de tous les doublons terminé !\n\n"
            f"Doublons trouvés : {duplicate_count}\n"
            f"Temps total : {elapsed:.1f} secondes"
        )

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
            "🔍", f"Analyse en cours... {count} doublon(s) trouvé(s)"
        )

        # CRITIQUE: Mettre à jour le compteur EN TEMPS RÉEL
        if self.stats_counter:
            self.stats_counter.update_duplicates(count)

    # Audio-first callbacks
    def _on_audio_extraction_progress(self, current: int, total: int, video_path: str) -> None:
        """Update audio extraction progress."""
        if self.audio_progress:
            self.audio_progress.update_progress(current, total, f"🎵 {current}/{total}")
            short_name = os.path.basename(video_path)[:30]
            if len(short_name) < len(os.path.basename(video_path)):
                short_name += "..."
            self.audio_progress.set_status(f"🎵 {short_name}", "#17A2B8")

    def _on_audio_extraction_finished(self) -> None:
        """Handle audio extraction completion."""
        if self.audio_progress:
            self.audio_progress.set_status("Complete", "#28A745")
        logger.info("Phase 1 complete: Audio extraction finished")

    def _on_audio_comparison_progress(self, current: int, total: int) -> None:
        """Update audio comparison progress."""
        if self.duplicate_progress:
            # Initialiser le maximum une seule fois
            if self.duplicate_progress.progress_bar.maximum() != total:
                self.duplicate_progress.progress_bar.setMaximum(total)

            self.duplicate_progress.update_progress(current, total, f"🔍 {current}/{total}")

            # Feedback textuel avec pourcentage
            pct = (current / total * 100) if total > 0 else 0
            self.duplicate_progress.set_status(f"Comparaison audio... {pct:.0f}%", "#007BFF")

    def _on_audio_comparison_finished(self, matches: list) -> None:
        """Handle audio comparison completion."""
        logger.info(f"Phase 2 complete: {len(matches)} audio candidates found")
        if self.duplicate_progress:
            self.duplicate_progress.set_status("Audio matches found", "#17A2B8")

    def _on_video_hash_progress(self, current: int, total: int) -> None:
        """Update video hash progress."""
        if self.file_progress:
            # Initialiser le maximum une seule fois
            if self.file_progress.progress_bar.maximum() != total:
                self.file_progress.progress_bar.setMaximum(total)

            self.file_progress.update_progress(current, total, f"📊 {current}/{total}")

            # Feedback textuel
            self.file_progress.set_status(f"Hash {current}/{total} vidéos", "#007BFF")

    def _on_video_hash_finished(self) -> None:
        """Handle selective video hashing completion."""
        logger.info("Phase 3 complete: Selective video hashing finished")
        if self.file_progress:
            self.file_progress.set_status("Complete", "#28A745")
        # Now start video comparison on candidates
        self._start_video_comparison_on_candidates()

    def _on_status_update(self, status: str) -> None:
        """Handle status updates from audio-first handler."""
        if self.status_indicator:
            self.status_indicator.update_status("🎵", status, "#17A2B8", "#D1ECF1", "#17A2B8")

    def _start_video_comparison_on_candidates(self) -> None:
        """Start video comparison on audio candidates."""
        candidates = self.audio_first_handler.audio_candidates

        if not candidates:
            logger.info("No audio candidates, finishing analysis")
            self._finish_analysis()
            return

        logger.info(f"Phase 4: Starting video comparison on {len(candidates)} candidate pairs")

        # Extract unique videos that need comparison
        unique_videos = set()
        for v1, v2, _ in candidates:
            unique_videos.add(v1)
            unique_videos.add(v2)

        # Use existing comparison logic
        config = self.get_analysis_config()
        self.analysis_handler.start_comparison_analysis(
            list(unique_videos),
            config,
            duplicate_callback=self._on_duplicate_found,
            progress_callback=self.update_duplicate_progress,
            status_callback=self.update_comparison_status,
            total_comparisons_callback=self.set_comparison_total,
            comparison_details_callback=self.update_comparison_details
        )

    def _get_params_tab(self):
        """Get parameters tab widget with all the audio-first parameters."""
        # Find the params tab from config tabs
        for child in self.findChildren(QWidget):
            if hasattr(child, 'audio_threshold_spin'):
                return child
        return None

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

    def update_duplicate_progress(self, current: int) -> None:
        """
        Update comparison progress.

        Args:
            current: Current comparison count.
        """
        max_comparisons = self.duplicate_progress.progress_bar.maximum()
        if max_comparisons > 0:
            self.duplicate_progress.update_progress(current, max_comparisons)

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
        self.duplicate_progress.progress_bar.setMaximum(total)
        self.duplicate_progress.update_progress(0, total, "Comparaisons en cours...")
        self.duplicate_progress.set_status("Comparaisons", "#007BFF")

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
        self.duplicate_progress.update_progress(current, total, f"{current}/{total}")

        if len(name1) > 15 or len(name2) > 15:
            short_names = f"{name1[:15]}...↔{name2[:15]}..."
        else:
            short_names = f"{name1}↔{name2}"

        self.duplicate_progress.set_status(f"🔍 {short_names}", "#007BFF")

    def handle_error(self, error_msg: str) -> None:
        """
        Handle analysis errors.

        Args:
            error_msg: Error message.
        """
        self.stop_ui_updates()
        QMessageBox.critical(self, "Erreur", f"Erreur durant l'analyse : {error_msg}")
        self.set_analysis_mode(False)
        self.status_indicator.update_status(
            "❌", "Erreur durant l'analyse",
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
            self.duplicate_progress.update()
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
   Early exits: {stats.get('early_exits', 0):,} ({stats.get('early_exit_percentage', 0):.1f}%)
   Ignored pairs: {stats.get('ignored_count', 0):,}

💾 MEMORY CACHE
   Hashes: {cache_stats.get('hash_cache_size', 0):,}
   Comparisons: {cache_stats.get('comparison_cache_size', 0):,}

⏱️ TIME SAVED
   Estimation: {stats.get('time_saved_seconds', 0):.0f} seconds"""

            QMessageBox.information(self, "Statistiques", message)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de récupérer les statistiques : {e}")

    def show_pending_duplicates(self) -> None:
        """
        Show and process pending duplicates.
        """
        try:
            count = self.duplicate_handler.load_pending_duplicates()

            if count == 0:
                QMessageBox.information(self, "Aucun doublon", "Aucun doublon en attente.")
                return

            reply = QMessageBox.question(
                self, "Doublons en attente",
                f"Il y a {count} doublon(s) en attente.\n\n"
                f"Voulez-vous reprendre le traitement ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.status_indicator.update_status(
                    "📋", f"Resuming {count} pending duplicates"
                )
                self.duplicate_handler.process_duplicates(self, ComparisonDialog)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de récupérer les doublons : {e}")

    def cleanup_resources(self) -> None:
        """
        Clean up all resources before closing.
        Stops all workers, closes database connections, and frees memory.
        """
        try:
            # Stop UI updates
            self.stop_ui_updates()

            # Stop scene worker if running
            if self.scene_worker and self.scene_worker.isRunning():
                logger.info("Stopping scene worker...")
                self.scene_worker.stop()
                self.scene_worker.wait(5000)  # Wait max 5 seconds

            # Stop subsequence worker if running
            if hasattr(self, 'subsequence_worker') and self.subsequence_worker:
                if self.subsequence_worker.isRunning():
                    logger.info("Stopping subsequence worker...")
                    self.subsequence_worker.stop()
                    self.subsequence_worker.wait(5000)

            # Cleanup analysis handler (stops hash/comparison workers)
            if self.analysis_handler:
                self.analysis_handler.cleanup()

            # Cleanup audio-first handler
            if self.audio_first_handler:
                self.audio_first_handler.stop_analysis()

            # Close database connections
            if self.video_hasher and self.video_hasher.db:
                logger.info("Closing database connections...")
                self.video_hasher.db.close()

            # Clear caches
            if self.scene_detector and hasattr(self.scene_detector, 'clear_cache'):
                logger.info("Clearing scene detection cache...")
                self.scene_detector.clear_cache()

            logger.info("Resources cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up resources: {e}", exc_info=True)

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
                    "Une analyse est en cours. Voulez-vous vraiment quitter ?\n\n"
                    "Les résultats déjà calculés seront conservés en cache.",
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
            except Exception as save_error:
                logger.error(f"Cannot save settings on close: {save_error}")
            event.accept()
            self.closed.emit()
