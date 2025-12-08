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
    QSplitter, QApplication, QLabel, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QShortcut, QKeySequence

# Import local modules
try:
    from .video_hasher import VideoHasher
    from .comparison_dialog import ComparisonDialog
    from .subsequence_comparison_dialog import SubsequenceComparisonDialog
    from .progress_widgets import FileListWidget
    from .ui.panels import UIPanels
    from .ui.widget_registry import WidgetRegistry, get_widget_registry
    from .ui.settings_dialog import SettingsDialog
    from .ui.dashboard_view import DashboardView
    from .ui.batch_queue_widget import BatchQueueWidget
    from .ui.cluster_view_dialog import ClusterViewDialog
    from .ui.smart_filters import SmartFiltersWidget
    from .ui.report_dialog import ReportDialog
    from .ui.themes import Theme, ThemeType
    from .controllers.batch_controller import BatchController, get_batch_controller
    from .analysis.cluster_detector import detect_clusters_from_db
    from .managers.settings_manager import SettingsManager
    from .managers.unified_config_manager import UnifiedConfigManager
    from .managers.progress_manager import ProgressManager, get_progress_manager
    from .controllers.workflow_controller import WorkflowController, WorkflowState, get_workflow_controller
    from .handlers.file_handler import FileHandler
    from .handlers.analysis_handler import AnalysisHandler
    from .handlers.duplicate_handler import DuplicateHandler
    from .handlers.audio_first_handler import AudioFirstHandler
    from .audio_config import AudioFirstConfig
    from .design_system import get_current_theme
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
    from ui.widget_registry import WidgetRegistry, get_widget_registry
    from ui.settings_dialog import SettingsDialog
    from ui.dashboard_view import DashboardView
    from ui.batch_queue_widget import BatchQueueWidget
    from ui.cluster_view_dialog import ClusterViewDialog
    from ui.smart_filters import SmartFiltersWidget
    from ui.report_dialog import ReportDialog
    from controllers.batch_controller import BatchController, get_batch_controller
    from analysis.cluster_detector import detect_clusters_from_db
    from managers.settings_manager import SettingsManager
    from managers.unified_config_manager import UnifiedConfigManager
    from managers.progress_manager import ProgressManager, get_progress_manager
    from controllers.workflow_controller import WorkflowController, WorkflowState, get_workflow_controller
    from handlers.file_handler import FileHandler
    from handlers.analysis_handler import AnalysisHandler
    from handlers.duplicate_handler import DuplicateHandler
    from handlers.audio_first_handler import AudioFirstHandler
    from audio_config import AudioFirstConfig
    from design_system import get_current_theme
    from layouts import LayoutManager, LayoutType
    from audio_fingerprinting import AudioFingerprintDetector, PrecisionMode
    from advanced_progress_dialog import AdvancedProgressDialog
    from analysis import AdvancedDuplicatePipeline

from src.core.logger import Logger
from src.core.i18n import t

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
        self.setWindowTitle(
            t("duplicate_finder.window.title", "🔍 Détecteur de doublons vidéo")
        )
        self.setMinimumSize(1000, 800)

        # Initialize core components (video_hasher will be created after settings load)
        self.video_hasher = None
        self.current_verification_pipeline = None  # Pipeline configured from UI
        self.current_theme = ThemeType.LIGHT  # Default theme

        # Initialize UI components (will be set in setup_ui)
        self.file_list_widget: Optional[FileListWidget] = None
        self.status_indicator = None
        self.stats_counter = None
        self.file_progress = None
        self.duplicate_progress = None
        self.verification_progress = None
        self.audio_progress = None
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
        self.hash_debugger_v2 = None

        # Initialize managers and handlers
        self.settings_manager = SettingsManager()
        self.unified_config_manager = UnifiedConfigManager(self.settings_manager)

        # Initialize new abstraction managers
        self.widget_registry = WidgetRegistry()
        self.progress_manager = ProgressManager()
        self.workflow_controller = WorkflowController()
        self.batch_controller = BatchController()

        self.file_handler: Optional[FileHandler] = None
        self.analysis_handler: Optional[AnalysisHandler] = None
        self.duplicate_handler: Optional[DuplicateHandler] = None
        self.scene_detector = None  # Audio fingerprint detector for scene detection
        self.scene_worker = None  # Worker for background scene detection
        self.verification_worker = None  # Worker for subsequence verification
        self._pending_scenes = []  # Scenes waiting for verification

        # Layout manager (Dashboard View only)
        self.layout_manager = LayoutManager()
        self.current_layout = LayoutType.DASHBOARD

        # UI update timer
        self.status_update_timer = QTimer()
        self.status_update_timer.timeout.connect(self.force_ui_update)
        self.status_update_timer.setSingleShot(False)

        # Create video hasher early (needed for db access in UI setup)
        # Will be recreated after loading settings if hash method differs
        self.video_hasher = VideoHasher(method='pHash')

        # Setup UI
        self.setup_ui()

        # Load settings first (to get hash method)
        self._load_settings()

        # Recreate video hasher with selected method if different
        hash_method = self.hash_method_combo.currentData() if self.hash_method_combo else 'pHash'
        if hash_method != self.video_hasher.method:
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

        # Load and apply theme
        saved_theme = self.settings_manager.settings.value("ui/theme", "light")
        try:
            self.current_theme = ThemeType(saved_theme)
        except ValueError:
            self.current_theme = ThemeType.LIGHT

        self._apply_theme(self.current_theme)

        # Setup keyboard shortcuts
        self._setup_shortcuts()

        logger.info("Main window initialized successfully")

    def setup_ui(self) -> None:
        """
        Configure the user interface.

        This method creates the main layout with a title, split panels,
        and all necessary widgets.
        """
        # Create menu bar
        self._create_menu_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create title bar at the very top
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)

        # Create main tab widget
        self.main_tabs = QTabWidget()
        self.main_tabs.setObjectName("main_tabs")

        # ===== DASHBOARD TAB =====
        self.dashboard_view = DashboardView(self.video_hasher.db)
        self.dashboard_view.add_files_requested.connect(self.add_files)
        self.dashboard_view.add_folder_requested.connect(self.add_folder)
        self.dashboard_view.start_analysis_requested.connect(self.start_analysis)
        self.dashboard_view.view_results_requested.connect(self._show_results_tab)
        self.main_tabs.addTab(self.dashboard_view, "📊 Dashboard")

        # ===== ANALYSIS TAB =====
        analysis_widget = QWidget()
        analysis_layout = QVBoxLayout(analysis_widget)
        analysis_layout.setContentsMargins(0, 0, 0, 0)
        analysis_layout.setSpacing(0)

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
        self.verification_progress = right_widgets.get('verification_progress')  # Subsequence verification progress

        # Register progress widgets with ProgressManager
        self.progress_manager.register_widget('file_progress', self.file_progress)
        self.progress_manager.register_widget('duplicate_progress', self.duplicate_progress)
        if self.audio_progress:
            self.progress_manager.register_widget('audio_progress', self.audio_progress)
        if self.verification_progress:
            self.progress_manager.register_widget('verification_progress', self.verification_progress)

        # Use LayoutManager to create the Dashboard layout
        layout_container = self.layout_manager.create_layout(
            self.current_layout,
            left_panel,
            right_panel,
            None  # No header widget needed
        )

        analysis_layout.addWidget(layout_container)
        self.main_tabs.addTab(analysis_widget, "🔍 Analysis")

        # ===== FILTERS TAB =====
        self.smart_filters_widget = SmartFiltersWidget()
        self.smart_filters_widget.filter_changed.connect(self._on_filter_changed)
        self.main_tabs.addTab(self.smart_filters_widget, "🔍 Filters")

        # ===== BATCH QUEUE TAB =====
        self.batch_queue_widget = BatchQueueWidget(
            batch_controller=self.batch_controller,
            config_manager=self.unified_config_manager
        )
        self.batch_queue_widget.execute_job_requested.connect(self._execute_batch_job)
        self.main_tabs.addTab(self.batch_queue_widget, "📋 Batch Queue")

        main_layout.addWidget(self.main_tabs)
        # CRITIQUE: Définir le stretch factor pour que le container s'étende et remplisse tout l'espace disponible
        main_layout.setStretch(1, 1)  # Index 1 = layout_container (index 0 = title_bar)

        # Initial button states
        if self.analyze_btn:
            self.analyze_btn.setEnabled(False)
        if self.stop_btn:
            self.stop_btn.setEnabled(False)

        # Apply initial theme
        self.apply_theme()

    def _create_menu_bar(self):
        """Create the menu bar with File, View, and other menus."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        # Settings action (Ctrl+,)
        settings_action = file_menu.addAction("&Settings...")
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._show_settings_dialog)

        # Separator
        file_menu.addSeparator()

        # Exit action
        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        # View menu
        view_menu = menubar.addMenu("&View")

        # Clusters action
        clusters_action = view_menu.addAction("🔗 &Clusters...")
        clusters_action.setShortcut("Ctrl+L")
        clusters_action.triggered.connect(self._show_clusters)

        # Separator
        view_menu.addSeparator()

        # Theme submenu
        theme_menu = view_menu.addMenu("🎨 &Theme")

        # Light theme action
        light_action = theme_menu.addAction("☀️ Light")
        light_action.triggered.connect(lambda: self._apply_theme(ThemeType.LIGHT))

        # Dark theme action
        dark_action = theme_menu.addAction("🌙 Dark")
        dark_action.triggered.connect(lambda: self._apply_theme(ThemeType.DARK))

        # ===== TOOLS MENU =====
        tools_menu = menubar.addMenu("&Tools")

        # Generate Report action
        report_action = tools_menu.addAction("📄 Generate &Report...")
        report_action.setShortcut("Ctrl+R")
        report_action.triggered.connect(self._generate_report)

        # ===== HELP MENU =====
        help_menu = menubar.addMenu("&Help")

        # Keyboard Shortcuts action
        shortcuts_action = help_menu.addAction("⌨️ &Keyboard Shortcuts")
        shortcuts_action.setShortcut("F1")
        shortcuts_action.triggered.connect(self._show_shortcuts_help)

        logger.debug("Menu bar created")

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

        title = QLabel(t("duplicate_finder.window.title", "🔍 Détecteur de doublons vidéo"))
        title.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_style = theme.get_title_style()
        # Suppression complète du padding vertical et limitation stricte de la hauteur
        title.setStyleSheet(title_style + " QLabel { padding: 0px 5px; margin: 0px; max-height: 18px; line-height: 18px; }")
        title_layout.addWidget(title)

        return title_widget

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

        if hasattr(self, 'verification_progress') and self.verification_progress:
            self.verification_progress.progress_bar.setStyleSheet(theme.get_progress_style())

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

    def _find_tab_by_name(self, tab_widget: QTabWidget, object_name: str) -> Optional[QWidget]:
        """
        Find a tab by its objectName (safer than hardcoded indices).

        Args:
            tab_widget: QTabWidget to search in
            object_name: objectName of the tab to find

        Returns:
            Tab widget if found, None otherwise
        """
        for i in range(tab_widget.count()):
            widget = tab_widget.widget(i)
            if widget and widget.objectName() == object_name:
                return widget
        logger.warning(f"Tab with objectName '{object_name}' not found")
        return None

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
            'start_scene_detection': self.start_scene_detection_mode,
            'run_advanced_mode': self.run_advanced_mode,
            'close': self.close
        }

        # Create panel
        panel = UIPanels.create_left_panel(self.file_list_widget, callbacks, self.video_hasher.db)

        # Extract references to parameter widgets and buttons
        # Find the QTabWidget first
        from PyQt6.QtWidgets import QTabWidget
        config_tabs = panel.findChild(QTabWidget)
        self.config_tabs = config_tabs

        # Get tabs by objectName (safer than hardcoded indices)
        params_tab = None
        debug_tab = None
        if config_tabs:
            params_tab = self._find_tab_by_name(config_tabs, "params_tab")
            debug_tab = self._find_tab_by_name(config_tabs, "debug_tab")

        # Register all widgets with WidgetRegistry
        if params_tab:
            self.widget_registry.register_from_tab(params_tab, group="params")
        if debug_tab:
            self.widget_registry.register_from_tab(debug_tab, group="debug")

        if params_tab:
            # Debug: log available attributes
            logger.debug(f"params_tab attributes: {[attr for attr in dir(params_tab) if not attr.startswith('_')]}")

            # Video comparison widgets (standardized naming)
            self.threshold_spin = getattr(params_tab, 'threshold_spin', None)
            self.hash_method_combo = getattr(params_tab, 'hash_method_combo', None)
            self.hash_workers_spin = getattr(params_tab, 'hash_workers_spin', None)
            self.comparison_workers_spin = getattr(params_tab, 'comparison_workers_spin', None)
            self.batch_size_spin = getattr(params_tab, 'batch_size_spin', None)
            self.comparison_algorithm_combo = None  # Removed in new version
            self.hash_timeout_spin = getattr(params_tab, 'hash_timeout_spin', None)
            self.comparison_timeout_spin = getattr(params_tab, 'comparison_timeout_spin', None)

            # Audio-First widgets
            self.audio_threshold_spin = getattr(params_tab, 'audio_threshold_spin', None)
            self.audio_precision_combo = getattr(params_tab, 'audio_precision_combo', None)
            self.audio_workers_spin = getattr(params_tab, 'audio_workers_spin', None)
            self.audio_cache_size_spin = getattr(params_tab, 'audio_cache_size_spin', None)
            self.enable_no_audio_fallback = getattr(params_tab, 'enable_no_audio_fallback', None)

            # LSH widgets
            self.enable_lsh_check = getattr(params_tab, 'enable_lsh_check', None)
            self.lsh_bands_spin = getattr(params_tab, 'lsh_bands_spin', None)
            self.lsh_rows_spin = getattr(params_tab, 'lsh_rows_spin', None)
            self.enable_lsh_no_audio = getattr(params_tab, 'enable_lsh_no_audio', None)

            # Multi-Resolution widgets
            self.enable_mr_check = getattr(params_tab, 'enable_mr_check', None)
            self.mr_coarse_duration_spin = getattr(params_tab, 'mr_coarse_duration_spin', None)
            self.mr_coarse_threshold_spin = getattr(params_tab, 'mr_coarse_threshold_spin', None)
            self.mr_medium_duration_spin = getattr(params_tab, 'mr_medium_duration_spin', None)
            self.mr_medium_threshold_spin = getattr(params_tab, 'mr_medium_threshold_spin', None)

            # Metadata filter widgets
            self.enable_metadata_check = getattr(params_tab, 'enable_metadata_check', None)
            self.metadata_duration_tolerance_spin = getattr(params_tab, 'metadata_duration_tolerance_spin', None)
            self.metadata_size_ratio_spin = getattr(params_tab, 'metadata_size_ratio_spin', None)

            # Cache widgets
            self.video_cache_size_spin = getattr(params_tab, 'video_cache_size_spin', None)
            self.comparison_cache_size_spin = getattr(params_tab, 'comparison_cache_size_spin', None)

            # Detection options
            self.enable_flip_detection = getattr(params_tab, 'enable_flip_detection', None)

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
            self.hash_timeout_spin, self.comparison_timeout_spin
        ]

        for widget in widgets:
            if widget:
                widget.valueChanged.connect(self._on_settings_changed)

        # Connect combobox separately (uses different signal)
        if self.hash_method_combo:
            self.hash_method_combo.currentIndexChanged.connect(self._on_settings_changed)

        if self.comparison_algorithm_combo:
            self.comparison_algorithm_combo.currentIndexChanged.connect(self._on_settings_changed)

    def _load_settings(self) -> None:
        """
        Load saved settings.
        """
        widgets = self._get_widget_dict()
        self.settings_manager.load_settings(widgets, self)

    def _get_widget_dict(self) -> Dict[str, Any]:
        """
        Get dictionary of ALL setting widgets (complete version).

        Returns:
            Dictionary mapping widget names to widget instances.
        """
        return {
            # Video comparison (basic)
            'threshold_spin': self.threshold_spin,
            'hash_method_combo': self.hash_method_combo,
            'hash_workers_spin': self.hash_workers_spin,
            'comparison_workers_spin': self.comparison_workers_spin,
            'batch_size_spin': self.batch_size_spin,
            'comparison_algorithm_combo': self.comparison_algorithm_combo,
            'hash_timeout_spin': self.hash_timeout_spin,
            'comparison_timeout_spin': self.comparison_timeout_spin,

            # Audio-First
            'audio_threshold_spin': getattr(self, 'audio_threshold_spin', None),
            'audio_precision_combo': getattr(self, 'audio_precision_combo', None),
            'audio_workers_spin': getattr(self, 'audio_workers_spin', None),
            'audio_cache_size_spin': getattr(self, 'audio_cache_size_spin', None),
            'enable_no_audio_fallback': getattr(self, 'enable_no_audio_fallback', None),

            # LSH
            'enable_lsh_check': getattr(self, 'enable_lsh_check', None),
            'lsh_bands_spin': getattr(self, 'lsh_bands_spin', None),
            'lsh_rows_spin': getattr(self, 'lsh_rows_spin', None),
            'enable_lsh_no_audio': getattr(self, 'enable_lsh_no_audio', None),

            # Multi-Resolution
            'enable_mr_check': getattr(self, 'enable_mr_check', None),
            'mr_coarse_duration_spin': getattr(self, 'mr_coarse_duration_spin', None),
            'mr_coarse_threshold_spin': getattr(self, 'mr_coarse_threshold_spin', None),
            'mr_medium_duration_spin': getattr(self, 'mr_medium_duration_spin', None),
            'mr_medium_threshold_spin': getattr(self, 'mr_medium_threshold_spin', None),

            # Metadata filters
            'enable_metadata_check': getattr(self, 'enable_metadata_check', None),
            'metadata_duration_tolerance_spin': getattr(self, 'metadata_duration_tolerance_spin', None),
            'metadata_size_ratio_spin': getattr(self, 'metadata_size_ratio_spin', None),

            # Cache
            'video_cache_size_spin': getattr(self, 'video_cache_size_spin', None),
            'comparison_cache_size_spin': getattr(self, 'comparison_cache_size_spin', None),

            # Detection options
            'enable_flip_detection': getattr(self, 'enable_flip_detection', None),
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
            "💾", t("duplicate_finder.status.settings_saved", "Settings saved"),
            "#17A2B8", "#D1ECF1", "#17A2B8"
        )

        # Clear message after 1.5 seconds
        QTimer.singleShot(1500, lambda: self.status_indicator.update_status(
            "🎯", t("duplicate_finder.status.ready", "Ready to analyze"),
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
            t("duplicate_finder.dialog.select_files_title", "Select video files"),
            last_folder,
            t("duplicate_finder.dialog.select_files_filter", "Videos (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.m4v);;All files (*.*)")
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
                "✅",
                t("duplicate_finder.status.files_added", f"{count} file(s) added", count=count),
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
            folder_path = QFileDialog.getExistingDirectory(
                self,
                t("duplicate_finder.dialog.select_folder_title", "Select folder"),
                last_folder
            )

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
                "📂",
                t("duplicate_finder.status.folder_files", f"{count} file(s) found in folder", count=count),
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
                t("duplicate_finder.dialog.folder_missing_title", "Folder not found"),
                t(
                    "duplicate_finder.dialog.folder_missing_body",
                    f"Le dernier dossier n'existe plus :\n{last_folder}",
                    path=last_folder
                )
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
            self.reload_last_folder_btn.setToolTip(
                t(
                    "duplicate_finder.tooltip.reload_last",
                    f"Reload last folder:\n{last_folder}",
                    path=last_folder
                )
            )
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
        self.status_indicator.update_status(
            "🗑️",
            t("duplicate_finder.status.list_cleared", "List cleared")
        )
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
                self.file_handler.update_file_status(
                    file_path,
                    t("duplicate_finder.status.to_analyze", "⏳ To analyze")
                )

            self.force_ui_update()

            self.status_indicator.update_status(
                "🧹",
                t("duplicate_finder.status.cache_cleared", "Cache cleared - all files need reanalysis"),
                "#FFC107", "#FFF3CD", "#FFC107"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                t("duplicate_finder.dialog.cache_error_title", "Erreur"),
                t("duplicate_finder.dialog.cache_error_body", f"Impossible de vider le cache : {e}", error=e)
            )

    def reset_folder(self) -> None:
        """
        Reset the last used folder path.
        """
        self.settings_manager.reset_last_folder()
        self.status_indicator.update_status(
            "🔄",
            t("duplicate_finder.status.folder_reset", "Folder path reset"),
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

    def _show_progress_bars_for_workflow(self, workflow: str) -> None:
        """
        Show only the progress bars needed for the specified workflow.

        Args:
            workflow: Either 'full_analysis' or 'scene_detection'
        """
        # Hide all bars first
        self._hide_all_progress_bars()

        if workflow == 'full_analysis':
            # Full analysis workflow: audio → video hash → comparison → scenes (optional)
            if self.audio_progress:
                self.audio_progress.show()
            if self.file_progress:
                self.file_progress.show()
            if self.duplicate_progress:
                self.duplicate_progress.show()

            # Show verification bar if scene detection is enabled
            config = self.get_analysis_config()
            scene_config = config.get('scene_detection', {})
            if scene_config.get('enabled', False) and self.verification_progress:
                self.verification_progress.show()

            logger.debug("Showing progress bars for full analysis")

        elif workflow == 'scene_detection':
            # Scene detection only: frame extraction → comparison
            if self.file_progress:
                self.file_progress.show()
            if self.duplicate_progress:
                self.duplicate_progress.show()

            logger.debug("Showing progress bars for scene detection")

    def _hide_all_progress_bars(self) -> None:
        """Hide all progress bars."""
        if self.audio_progress:
            self.audio_progress.hide()
        if self.file_progress:
            self.file_progress.hide()
        if self.duplicate_progress:
            self.duplicate_progress.hide()
        if self.verification_progress:
            self.verification_progress.hide()

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

        # Transition workflow to HASHING state
        try:
            self.workflow_controller.transition_to(WorkflowState.HASHING, {
                'file_count': file_count,
                'valid_files': len(valid_files)
            })
        except ValueError as e:
            logger.warning(f"Workflow transition warning: {e}")
            # Reset workflow if in invalid state
            self.workflow_controller.reset()
            self.workflow_controller.transition_to(WorkflowState.HASHING, {
                'file_count': file_count,
                'valid_files': len(valid_files)
            })

        # Reset stats counters
        self.stats_counter.reset()

        # Show progress bars for full analysis workflow
        self._show_progress_bars_for_workflow('full_analysis')

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

        # Create verification pipeline from UI configuration
        verification_pipeline = None
        if hasattr(params_tab, 'pipeline_config_widget'):
            try:
                full_config = params_tab.pipeline_config_widget.get_pipeline_config()
                mode = full_config.get('mode', 'filtering')
                methods_config = full_config.get('methods', [])

                if methods_config:  # Only create pipeline if methods are configured
                    from .verification_pipeline import VerificationPipeline
                    verification_pipeline = VerificationPipeline(
                        db_manager=self.video_hasher.db,
                        max_workers=8,
                        enable_caching=True,
                        mode=mode
                    )
                    verification_pipeline.load_config(methods_config)
                    logger.info(f"Pipeline configuré pour audio-first: mode={mode}, {len(methods_config)} méthodes")
            except Exception as e:
                logger.warning(f"Impossible de charger le pipeline configuré: {e}")

        # Store pipeline for use in comparison
        self.current_verification_pipeline = verification_pipeline

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
            self.duplicate_handler.processing_stopped = True

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

            # Stop verification worker
            if self.verification_worker and self.verification_worker.isRunning():
                logger.info("Stopping verification worker...")
                self.verification_worker.stop()
                # Wait with timeout to prevent indefinite blocking
                if not self.verification_worker.wait(5000):  # 5 second timeout
                    logger.warning("Verification worker did not stop gracefully, forcing termination")
                    self.verification_worker.terminate()
                self.verification_worker = None

            # Stop duplicate processing
            self.duplicate_handler.stop_processing()

            self.stop_ui_updates()

            # Hide all progress bars when stopped
            self._hide_all_progress_bars()
            self._reset_progress_widgets()

            self.set_analysis_mode(False)
            if self.analyze_btn:
                self.analyze_btn.setEnabled(True)
            if self.stop_btn:
                self.stop_btn.setEnabled(False)

            self.status_indicator.update_status(
                "⏹️", "Analysis stopped by user",
                "#DC3545", "#F8D7DA", "#DC3545"
            )

    def start_scene_detection_mode(self) -> None:
        """
        Start DIRECT scene detection (visual only, no audio-first workflow).

        This mode uses SubsequenceDetector with Strategy 3 for visual comparison.
        """
        # Check file count
        file_count = self.file_handler.get_file_count()

        if file_count < 2:
            QMessageBox.warning(
                self, "Attention",
                "Au moins 2 fichiers sont requis pour détecter les scènes"
            )
            return

        # Validate files
        valid_files, invalid_files = self.file_handler.validate_files_for_analysis()

        if len(valid_files) < 2:
            QMessageBox.warning(self, "Erreur", "Pas assez de fichiers valides")
            return

        # Show confirmation dialog
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Détection de Scènes")
        msg.setText(
            f"🎬 Analyse de {len(valid_files)} vidéos\n\n"
            f"Cette détection utilise :\n"
            f"• Comparaison visuelle (DCT coefficients)\n"
            f"• Détection de transitions (Scene Cuts)\n"
            f"• Vérification Strategy 3 (100% précision)\n\n"
            f"La progression s'affichera dans les barres de progression."
        )
        msg.setInformativeText("Lancer la détection de scènes ?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)

        if msg.exec() != QMessageBox.StandardButton.Yes:
            return

        # Set UI to analysis mode
        self.set_analysis_mode(True)
        self.duplicate_handler.processing_stopped = False

        # Reset stats counters
        self.stats_counter.reset()

        # Show progress bars for scene detection workflow ONLY
        self._show_progress_bars_for_workflow('scene_detection')

        # Start UI updates
        self.start_ui_updates()

        logger.info("Starting DIRECT scene detection (visual only, no audio workflow)")

        # Call scene detection directly (skip audio-first workflow)
        self._start_scene_detection()

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

                # Load duplicates from database
                duplicates = self.video_hasher.db.get_pending_duplicates()
                self.duplicate_handler.clear_duplicates()
                for file1, file2, similarity in duplicates:
                    self.duplicate_handler.add_duplicate(file1, file2, similarity)

                # Show success message
                duplicate_count = len(duplicates)
                QMessageBox.information(
                    self, "Analyse Terminée",
                    f"✅ Détection de scènes terminée !\n\n"
                    f"Doublons trouvés: {duplicate_count}\n\n"
                    "Les résultats sont disponibles dans l'onglet Résultats."
                )

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

    def _reset_progress_widgets(self) -> None:
        """Reset progress widgets to an idle state."""
        progress_widgets = [
            getattr(self, 'audio_progress', None),
            getattr(self, 'file_progress', None),
            getattr(self, 'duplicate_progress', None),
            getattr(self, 'verification_progress', None)
        ]

        for widget in progress_widgets:
            if not widget:
                continue
            # Reset bars and stats
            widget.update_progress(0, widget.progress_bar.maximum() or 1)
            widget.set_status(t("duplicate_finder.progress.waiting", "Waiting..."))
            if hasattr(widget, "set_time_remaining"):
                widget.set_time_remaining(0)
            if hasattr(widget, "set_speed"):
                widget.set_speed(0)

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
        # Check if scene detection is enabled
        config = self.get_analysis_config()
        scene_config = config.get('scene_detection', {})
        is_enabled = scene_config.get('enabled', False)

        logger.info(f"Scene detection enabled: {is_enabled}")

        if is_enabled:
            # Scene detection will follow - mark as "video comparison complete" but not finished
            self.duplicate_progress.set_status(
                t('duplicate_finder.ui.progress.video_comparison_complete', 'Video comparison complete'),
                "#17A2B8"
            )

            logger.info(f"Scene detection parameters: precision={scene_config.get('precision_mode', 'balanced')}, "
                       f"min_match_ratio={scene_config.get('min_match_ratio', 0)*100:.1f}%")
            # Start scene detection
            self._start_scene_detection()
        else:
            # No scene detection - mark as complete and finish
            self.duplicate_progress.set_status(
                t('duplicate_finder.ui.progress.analysis_complete', 'Analysis complete'),
                "#28A745"
            )
            logger.info("Scene detection skipped (not enabled)")
            # No scene detection, finish analysis
            self._finish_analysis()

    def _start_scene_detection(self) -> None:
        """
        Start scene detection using SubsequenceDetector with Strategy 3 (DCT + Scene Cuts).

        Uses visual comparison (not audio fingerprinting) for accurate subsequence detection.
        This is the same approach used in the test scripts for maximum effectiveness.
        """
        try:
            from .workers.subsequence_worker import SubsequenceDetectionWorker
            from .subsequence_detector import SubsequenceDetector
            from .verification_pipeline import VerificationPipeline

            # Get parameters tab with all configuration widgets
            params_tab = self._get_params_tab()

            if not params_tab:
                logger.error("Failed to get parameters tab")
                return

            # Default values for subsequence detection
            sample_interval = 0.75
            min_match_ratio = 0.70
            temporal_window = 5
            cache_size = 1000
            sliding_window_tolerance = 3
            enable_adaptive_refinement = False

            # Create verification pipeline from widget configuration
            verification_pipeline = None
            if hasattr(params_tab, 'pipeline_config_widget'):
                # Get pipeline configuration from widget (includes mode and methods)
                full_config = params_tab.pipeline_config_widget.get_pipeline_config()

                mode = full_config.get('mode', 'filtering')
                methods_config = full_config.get('methods', [])
                pipeline_debug_flag = full_config.get('debug_flag', False)
                pipeline_run_label = full_config.get('run_label')

                # Create VerificationPipeline instance with mode
                verification_pipeline = VerificationPipeline(
                    db_manager=self.video_hasher.db,
                    max_workers=8,
                    enable_caching=True,
                    mode=mode
                )

                # Load methods configuration into pipeline
                if methods_config:
                    verification_pipeline.load_config(methods_config)
                    mode_str = {'filtering': 'Filtering', 'weighting': 'Weighting', 'hybrid': 'Hybrid'}.get(mode, mode)
                    logger.info(f"Verification pipeline configured: mode={mode_str}, "
                               f"{len(methods_config)} methods (each method proposes its threshold)")
                else:
                    # No methods configured - use default balanced preset
                    logger.info("No methods configured, using balanced preset")
                    verification_pipeline.add_method('color_histogram', enabled=True, parameters={'threshold': 85.0}, weight=1.0)
                    verification_pipeline.add_method('motion_analysis', enabled=True, parameters={'correlation_threshold': 85.0}, weight=1.0)
                    verification_pipeline.add_method('dct_coefficients', enabled=True, parameters={'threshold': 75.0}, weight=1.0)
            else:
                logger.warning("Pipeline configuration widget not found, verification disabled")

            # Create SubsequenceDetector with pipeline
            self.subsequence_detector = SubsequenceDetector(
                hasher=self.video_hasher,
                max_cache_memory_mb=cache_size,
                sample_interval_seconds=sample_interval,
                min_match_ratio=min_match_ratio,
                temporal_window_frames=temporal_window,
                sliding_window_tolerance=sliding_window_tolerance,
                enable_adaptive_refinement=enable_adaptive_refinement,
                verification_pipeline=verification_pipeline,
                pipeline_run_label=pipeline_run_label,
                pipeline_debug_flag=pipeline_debug_flag
            )

            if verification_pipeline:
                methods_str = ', '.join([m['name'] for m in verification_pipeline.get_config() if m['enabled']])
                logger.info(f"SubsequenceDetector initialized with pipeline: {methods_str}, "
                           f"{sample_interval}s intervals, min_ratio={min_match_ratio*100:.1f}%, cache={cache_size}MB")
            else:
                logger.info(f"SubsequenceDetector initialized (no verification): "
                           f"{sample_interval}s intervals, min_ratio={min_match_ratio*100:.1f}%, cache={cache_size}MB")

            # Update UI - status indicator
            self.status_indicator.update_status(
                "🎬",
                t('duplicate_finder.ui.scene_detection.status_detecting', 'Detecting scenes (Strategy 3: DCT + Scene Cuts)...'),
                "#17A2B8", "#D1ECF1", "#17A2B8"
            )

            # Initialize progress bars
            # file_progress: will show hashing/frame extraction status
            # duplicate_progress: will show comparison progress
            if self.file_progress:
                self.file_progress.update_progress(0, 100, t('duplicate_finder.ui.scene_detection.hashing_progress', '📊 Extraction {current}/{total}', current=0, total=0))
                self.file_progress.set_status(t('duplicate_finder.ui.scene_detection.status_hashing', 'Extracting video frames...'), "#17A2B8")

            # Get all files
            files = self.file_handler.get_all_files()

            # Stop any existing scene worker
            if self.scene_worker and self.scene_worker.isRunning():
                logger.info("Stopping existing scene worker...")
                self.scene_worker.stop()
                self.scene_worker.wait()

            # Create and configure worker
            logger.info(f"Starting subsequence detection on {len(files)} files")
            self.scene_worker = SubsequenceDetectionWorker(
                subsequence_detector=self.subsequence_detector,
                files=files
            )

            # Track matches for progress display
            self._scene_matches_found = 0

            # Connect signals
            def on_hash_progress(current: int, total: int, message: str):
                """Update frame extraction progress (PHASE 1: file_progress)."""
                if self.file_progress:
                    self.file_progress.update_progress(
                        current, total,
                        t('duplicate_finder.ui.scene_detection.hashing_progress', '📊 Extraction {current}/{total}', current=current, total=total)
                    )
                    self.file_progress.set_status(
                        t('duplicate_finder.ui.scene_detection.status_hashing', 'Extracting video frames...'),
                        "#007BFF"
                    )
                self.force_ui_update()

            def on_progress(current: int, total: int, message: str):
                """Update comparison progress (PHASE 2: duplicate_progress)."""
                # Mark file_progress as complete when comparison starts
                if current == 1 and self.file_progress:
                    self.file_progress.set_status(t('duplicate_finder.ui.progress.video_hashing_complete', 'Hashing complete'), "#28A745")

                # Update duplicate_progress with comparison progress
                if self.duplicate_progress:
                    self.duplicate_progress.update_progress(
                        current, total,
                        t('duplicate_finder.ui.scene_detection.comparing_progress', '🔍 Comparison {current}/{total}', current=current, total=total)
                    )
                    self.duplicate_progress.set_status(
                        t('duplicate_finder.ui.scene_detection.comparing_status', 'Verifying scene ({matches} found)', matches=self._scene_matches_found),
                        "#007BFF"
                    )
                self.force_ui_update()

            def on_subsequence_found(short_video: str, long_video: str, result: dict):
                """Handle each found subsequence (already verified by Strategy 3)."""
                # SubsequenceDetector with enable_verification=True already applies Strategy 3
                # So these subsequences are already verified - just add them
                match_ratio = result.get('match_ratio', 0.0)
                start_frame_idx = result.get('start_frame_idx', 0)
                confidence = result.get('confidence', 0.0)

                # Increment match counter
                self._scene_matches_found += 1

                # Log with translation
                logger.info(t(
                    'duplicate_finder.ui.scene_detection.subsequence_verified',
                    'Scene verified: {short} in {long} ({match}% match)',
                    short=os.path.basename(short_video),
                    long=os.path.basename(long_video),
                    match=f"{match_ratio*100:.1f}"
                ))

                # Store in database
                self.video_hasher.db.store_subsequence_detection(
                    short_video,
                    long_video,
                    match_ratio,
                    start_frame_idx,
                    confidence
                )

                # Add to duplicate handler
                self.duplicate_handler.add_subsequence(
                    short_video,
                    long_video,
                    result
                )

            def on_status_update(message: str):
                """Handle status updates."""
                logger.info(f"Subsequence detection: {message}")

            def on_finished(scenes: list):
                """Handle completion of subsequence detection."""
                logger.info(f"Subsequence detection complete: {len(scenes)} scenes found")

                # Update progress bars to show completion
                if self.duplicate_progress:
                    self.duplicate_progress.set_status(
                        t('duplicate_finder.ui.scene_detection.complete', '✅ {count} scene(s) detected', count=len(scenes)),
                        "#28A745"
                    )

                # Clean up
                self.scene_worker = None
                self._scene_matches_found = 0

                # Finish analysis
                self._finish_analysis()

            def on_error(error_msg: str):
                """Handle error in subsequence detection."""
                logger.error(f"Error during subsequence detection: {error_msg}")
                QMessageBox.warning(
                    self,
                    t('duplicate_finder.ui.scene_detection.error_title', 'Scene Detection Error'),
                    t('duplicate_finder.ui.scene_detection.error_message', 'An error occurred during scene detection:\n{error}\n\nContinuing with duplicate results...', error=error_msg)
                )

                # Clean up worker reference
                self.scene_worker = None
                self._scene_matches_found = 0

                # Finish analysis anyway
                self._finish_analysis()

            self.scene_worker.hash_progress.connect(on_hash_progress)  # Frame extraction → file_progress
            self.scene_worker.progress.connect(on_progress)          # Comparison → duplicate_progress
            self.scene_worker.subsequence_found.connect(on_subsequence_found)
            self.scene_worker.status_update.connect(on_status_update)
            self.scene_worker.finished.connect(on_finished)
            self.scene_worker.error.connect(on_error)

            # Start worker
            self.scene_worker.start()

        except Exception as e:
            logger.error(f"Error setting up scene detection: {e}")
            QMessageBox.warning(
                self,
                t('duplicate_finder.ui.scene_detection.error_title', 'Scene Detection Error'),
                t('duplicate_finder.ui.scene_detection.error_setup', 'An error occurred during scene detection setup:\n{error}\n\nContinuing with duplicate results...', error=str(e))
            )
            self._finish_analysis()

    def _start_scene_verification(self, scenes: list) -> None:
        """
        Start verification of detected scenes using Strategy 3.

        Args:
            scenes: List of scene detection results to verify
        """
        try:
            from .workers.verification_worker import VerificationWorker
            from .analysis.subsequence_verification import SubsequenceVerificationMethods

            # Get verification parameters from config
            config = self.get_analysis_config()
            dct_threshold = config.get('subseq_dct_threshold', 75.0)
            sequence_threshold = config.get('subseq_sequence_threshold', 95.0)
            workers = config.get('subseq_verification_workers', 2)

            # Create verifier
            verifier = SubsequenceVerificationMethods(
                dct_threshold=dct_threshold,
                sequence_threshold=sequence_threshold,
                max_workers=workers
            )

            # Create worker
            self.verification_worker = VerificationWorker(
                verifier=verifier,
                matches=scenes,
                db=self.video_hasher.db
            )

            # Connect signals
            def on_verification_progress(current: int, total: int, message: str):
                """Update verification progress bar."""
                if self.verification_progress:
                    self.verification_progress.update_progress(current, total, message)
                    self.verification_progress.set_status(f"Verifying {current}/{total}", "#17A2B8")
                self.force_ui_update()

            def on_verification_complete(match_data: dict, result: dict):
                """Handle single verification result."""
                self._add_verified_scene(match_data, result['accepted'], result.get('from_cache', False))

            def on_all_complete(results: list):
                """Handle completion of all verifications."""
                accepted = sum(1 for r in results if r['result']['accepted'])
                rejected = len(results) - accepted
                cache_hits = sum(1 for r in results if r.get('from_cache', False))

                logger.info(f"Verification complete: {accepted} accepted, {rejected} rejected ({cache_hits} cached)")

                if self.verification_progress:
                    self.verification_progress.set_status(
                        f"✓ Complete: {accepted} verified ({cache_hits} cached)",
                        "#28A745"
                    )

                # Clean up
                self.scene_worker = None
                self.verification_worker = None
                self._pending_scenes = []

                # Finish analysis
                self._finish_analysis()

            def on_verification_error(error_msg: str):
                """Handle verification error."""
                logger.error(f"Verification error: {error_msg}")
                if self.verification_progress:
                    self.verification_progress.set_status(f"Error: {error_msg}", "#DC3545")

                # Fall back to adding all scenes without verification
                logger.warning("Verification failed, adding scenes without verification")
                for scene_data in scenes:
                    self._add_verified_scene(scene_data, accepted=True, from_cache=False)

                # Clean up and finish
                self.verification_worker = None
                self._pending_scenes = []
                self._finish_analysis()

            # Connect signals
            self.verification_worker.progress.connect(on_verification_progress)
            self.verification_worker.verification_complete.connect(on_verification_complete)
            self.verification_worker.all_complete.connect(on_all_complete)
            self.verification_worker.error.connect(on_verification_error)

            # Start verification
            logger.info(f"Starting VerificationWorker with {len(scenes)} scenes")
            self.verification_worker.start()

        except Exception as e:
            logger.error(f"Error starting verification: {e}", exc_info=True)
            # Fall back to adding all scenes
            for scene_data in scenes:
                self._add_verified_scene(scene_data, accepted=True, from_cache=False)
            self._finish_analysis()

    def _add_verified_scene(self, scene_data: dict, accepted: bool, from_cache: bool = False):
        """
        Add a verified scene to duplicate handler.

        Args:
            scene_data: Scene detection data
            accepted: Whether verification accepted the scene
            from_cache: Whether result came from cache
        """
        if not accepted:
            logger.info(f"Scene rejected by verification: {os.path.basename(scene_data['short_video'])}")
            return

        # Store in database
        start_frame_idx = int(scene_data['start_time'] * 25)  # Assume 25fps

        self.video_hasher.db.store_subsequence_detection(
            scene_data['short_video'],
            scene_data['long_video'],
            scene_data['result']['match_ratio'],
            start_frame_idx,
            scene_data['result']['confidence']
        )

        # Add to duplicate handler for UI processing
        self.duplicate_handler.add_subsequence(
            scene_data['short_video'],
            scene_data['long_video'],
            scene_data['result']
        )

        cache_msg = " (cached)" if from_cache else ""
        logger.debug(f"Scene accepted{cache_msg}: {os.path.basename(scene_data['short_video'])}")

    def _finish_analysis(self) -> None:
        """
        Complete the analysis and show results.
        """
        self.stop_ui_updates()

        # Hide all progress bars when analysis is complete
        self._hide_all_progress_bars()

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
            self.audio_progress.set_status(
                t('duplicate_finder.ui.progress.audio_complete', 'Audio extraction complete'),
                "#28A745"
            )
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
            self.duplicate_progress.set_status(
                t('duplicate_finder.ui.progress.audio_comparison', 'Audio comparison... {percent}%', percent=f"{pct:.0f}"),
                "#007BFF"
            )

    def _on_audio_comparison_finished(self, matches: list) -> None:
        """Handle audio comparison completion."""
        logger.info(f"Phase 2 complete: {len(matches)} audio candidates found")
        if self.duplicate_progress:
            self.duplicate_progress.set_status(
                t('duplicate_finder.ui.progress.audio_matches_found', 'Audio candidates found'),
                "#17A2B8"
            )

    def _on_video_hash_progress(self, current: int, total: int) -> None:
        """Update video hash progress."""
        if self.file_progress:
            # Initialiser le maximum une seule fois
            if self.file_progress.progress_bar.maximum() != total:
                self.file_progress.progress_bar.setMaximum(total)

            self.file_progress.update_progress(current, total, f"📊 {current}/{total}")

            # Feedback textuel
            self.file_progress.set_status(
                t('duplicate_finder.ui.progress.video_hashing', 'Hash {current}/{total} videos', current=current, total=total),
                "#007BFF"
            )

    def _on_video_hash_finished(self) -> None:
        """Handle selective video hashing completion."""
        logger.info("Phase 3 complete: Selective video hashing finished")
        if self.file_progress:
            self.file_progress.set_status(
                t('duplicate_finder.ui.progress.video_hashing_complete', 'Hashing complete'),
                "#28A745"
            )
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

        # Use existing comparison logic with SPECIFIC PAIRS (audio-first optimization)
        config = self.get_analysis_config()
        self.analysis_handler.start_comparison_analysis(
            list(unique_videos),
            config,
            duplicate_callback=self._on_duplicate_found,
            progress_callback=self.update_duplicate_progress,
            status_callback=self.update_comparison_status,
            total_comparisons_callback=self.set_comparison_total,
            comparison_details_callback=self.update_comparison_details,
            specific_pairs=candidates  # FIXED: Pass audio candidates to avoid N² comparison
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
        self.duplicate_progress.update_progress(
            0, total,
            t('duplicate_finder.ui.progress.video_comparison', 'Comparisons in progress...')
        )
        self.duplicate_progress.set_status(
            t('duplicate_finder.ui.progress.video_comparison', 'Comparisons in progress...'),
            "#007BFF"
        )

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

    def _show_settings_dialog(self):
        """Show the unified settings dialog."""
        try:
            dialog = SettingsDialog(self.unified_config_manager, self)
            dialog.settings_changed.connect(self._on_settings_changed)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                logger.info("Settings dialog accepted")
            else:
                logger.info("Settings dialog cancelled")

        except Exception as e:
            logger.error(f"Error showing settings dialog: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Failed to open settings dialog:\n{e}"
            )

    def _on_settings_changed(self, config):
        """
        Handle settings change from dialog.

        Args:
            config: UnifiedConfig with new settings
        """
        try:
            logger.info("Settings changed, applying new configuration")

            # Apply settings to UI (if needed)
            # For now, settings are saved by the dialog itself
            # Future: apply changes to running components

            QMessageBox.information(
                self, "Settings Applied",
                "Settings have been saved successfully.\n\n"
                "Some changes may require restarting the application."
            )

        except Exception as e:
            logger.error(f"Error applying settings: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Failed to apply settings:\n{e}"
            )

    def _show_clusters(self):
        """Show duplicate clusters dialog."""
        try:
            # Detect clusters from database
            logger.info("Detecting clusters...")
            detector = detect_clusters_from_db(self.video_hasher.db, min_similarity=0.85)

            if not detector.clusters:
                QMessageBox.information(
                    self, "No Clusters",
                    "No duplicate clusters found.\n\n"
                    "Make sure you have run duplicate detection first."
                )
                return

            # Show clusters dialog
            dialog = ClusterViewDialog(detector, self)
            dialog.files_deleted.connect(self._on_cluster_files_deleted)
            dialog.exec()

        except Exception as e:
            logger.error(f"Error showing clusters: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Failed to detect clusters:\n{e}"
            )

    def _on_cluster_files_deleted(self, deleted_paths: list):
        """
        Handle files deleted from cluster view.

        Args:
            deleted_paths: List of deleted file paths
        """
        logger.info(f"Cluster view deleted {len(deleted_paths)} files")

        # Refresh file list
        if self.file_handler:
            for path in deleted_paths:
                # Remove from file handler
                # Note: You'd need to implement this in file_handler
                pass

        # Show notification
        QMessageBox.information(
            self, "Files Deleted",
            f"Deleted {len(deleted_paths)} file(s) from clusters.\n\n"
            "The file list will be refreshed."
        )

    def _show_results_tab(self):
        """Switch to the Analysis tab to view results."""
        self.main_tabs.setCurrentIndex(1)  # Index 1 = Analysis tab
        logger.info("Switched to Analysis tab")

    def _on_filter_changed(self, criteria):
        """
        Handle filter criteria changes from SmartFiltersWidget.

        Args:
            criteria: FilterCriteria object with current filter settings

        Note:
            This method is called when the user applies a filter.
            In the future, this could trigger:
            - Re-filtering of displayed duplicate results
            - Updating result counts
            - Highlighting filtered items in the UI
        """
        from .managers.filter_manager import FilterCriteria

        logger.info(f"Filter changed: enabled={criteria.enabled}, "
                   f"similarity={criteria.min_similarity:.0f}-{criteria.max_similarity:.0f}%")

        # TODO: Apply filter to displayed results
        # For now, just log the filter change
        # Future implementation:
        # - Get current duplicate results
        # - Apply filter using filter_manager.apply_filter()
        # - Update results display
        # - Update status/counts

        status_msg = "Filter applied" if criteria.enabled else "Filter disabled"
        if hasattr(self, 'status_indicator'):
            # Update status indicator if available
            pass

    def _generate_report(self):
        """
        Show report generation dialog.

        Collects duplicate data from database and opens ReportDialog.
        """
        try:
            # Collect duplicate data from database
            duplicate_data = self._collect_duplicate_data()

            if not duplicate_data or duplicate_data.get('total_duplicate_groups', 0) == 0:
                QMessageBox.warning(
                    self, "No Duplicates",
                    "No duplicate data available. Please run duplicate detection first."
                )
                return

            # Show report dialog
            dialog = ReportDialog(duplicate_data, self)
            dialog.exec()

            logger.info("Report dialog opened")

        except Exception as e:
            logger.error(f"Failed to open report dialog: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Failed to open report dialog:\n{e}"
            )

    def _collect_duplicate_data(self) -> Dict[str, Any]:
        """
        Collect duplicate data from database for reporting.

        Returns:
            Dictionary with duplicate data
        """
        try:
            db = self.video_hasher.db

            # Get all duplicates from database
            duplicates = db.get_all_duplicates()

            # Group duplicates by similarity
            groups = {}
            for dup in duplicates:
                file1_path = dup.get('file1_path', '')
                file2_path = dup.get('file2_path', '')
                similarity = dup.get('similarity', 0)

                # Create a group key (use file1 as group leader)
                group_key = file1_path

                if group_key not in groups:
                    # Get file info
                    file1_info = db.get_video_by_path(file1_path)
                    groups[group_key] = {
                        'files': [{
                            'path': file1_path,
                            'size': file1_info.get('file_size', 0) if file1_info else 0,
                            'similarity': 100.0,
                            'hash': file1_info.get('hash', '') if file1_info else ''
                        }]
                    }

                # Add file2 to group
                file2_info = db.get_video_by_path(file2_path)
                groups[group_key]['files'].append({
                    'path': file2_path,
                    'size': file2_info.get('file_size', 0) if file2_info else 0,
                    'similarity': similarity,
                    'hash': file2_info.get('hash', '') if file2_info else ''
                })

            # Calculate statistics
            total_files = db.get_total_hashed()
            total_duplicates = len(duplicates)
            total_groups = len(groups)

            # Calculate space wasted
            total_space_wasted = 0
            for group in groups.values():
                files = group['files']
                if len(files) > 1:
                    # Keep the first file, sum the rest
                    total_space_wasted += sum(f['size'] for f in files[1:])

            # Build result dictionary
            result = {
                'total_files_scanned': total_files,
                'total_duplicates_found': total_duplicates,
                'total_duplicate_groups': total_groups,
                'total_space_wasted': total_space_wasted,
                'potential_space_savings': total_space_wasted,
                'duplicate_groups': list(groups.values()),
                'hash_method': 'perceptual_hash',  # or get from config
                'similarity_threshold': 85.0,  # or get from config
                'scan_duration': None  # Could track this if needed
            }

            logger.info(f"Collected duplicate data: {total_groups} groups, {total_duplicates} duplicates")
            return result

        except Exception as e:
            logger.error(f"Failed to collect duplicate data: {e}")
            return {}

    def _execute_batch_job(self, job_id: str):
        """
        Execute a batch analysis job.

        Args:
            job_id: ID of the job to execute
        """
        job = self.batch_controller.get_job(job_id)
        if not job:
            logger.error(f"Job not found: {job_id}")
            return

        logger.info(f"Executing batch job: {job.name} ({job.job_type.value})")

        try:
            # Apply job configuration if provided
            if job.config:
                self.unified_config_manager.set_current_config(job.config)
                self.unified_config_manager.apply_to_ui(self._get_widget_dict())

            # Load files based on target type
            if job.target_type == 'folder':
                # Add folder
                self.file_handler.add_folder(str(job.target))
                self.batch_controller.update_job_progress(job_id, 10, "Loaded folder")
            else:  # files
                # Add files
                file_paths = [str(p) for p in job.target]
                for file_path in file_paths:
                    self.file_handler.add_file(file_path)
                self.batch_controller.update_job_progress(job_id, 10, "Loaded files")

            # Start analysis based on job type
            from .controllers.batch_controller import JobType

            if job.job_type == JobType.AUDIO_FIRST_ANALYSIS:
                # Start audio-first analysis
                self.start_audio_first_analysis()
            elif job.job_type == JobType.SUBSEQUENCE_DETECTION:
                # Start with subsequence detection enabled
                # Note: This would require enabling subsequence detection in config
                self.start_analysis()
            else:  # STANDARD_ANALYSIS or CUSTOM
                # Start standard analysis
                self.start_analysis()

            # Connect to analysis completion to mark job as complete
            # Note: In a real implementation, you'd need to track when analysis finishes
            # and call batch_controller.complete_job(job_id, result) or fail_job(job_id, error)

            # For now, we'll mark it as started
            self.batch_controller.update_job_progress(job_id, 20, "Analysis started")

            logger.info(f"Batch job started: {job.name}")

        except Exception as e:
            logger.error(f"Error executing batch job {job_id}: {e}")
            self.batch_controller.fail_job(job_id, str(e))

    def _setup_shortcuts(self):
        """Setup global keyboard shortcuts for the application."""
        # File operations
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.add_files)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self).activated.connect(self.add_folder)

        # Analysis operations
        QShortcut(QKeySequence("F5"), self).activated.connect(self.start_analysis)
        QShortcut(QKeySequence("Ctrl+P"), self).activated.connect(self.start_analysis)  # Alternative
        QShortcut(QKeySequence("Escape"), self).activated.connect(self.stop_analysis)
        QShortcut(QKeySequence("Ctrl+."), self).activated.connect(self.stop_analysis)  # Alternative

        # Tab navigation
        QShortcut(QKeySequence("Ctrl+1"), self).activated.connect(lambda: self.main_tabs.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self).activated.connect(lambda: self.main_tabs.setCurrentIndex(1))
        QShortcut(QKeySequence("Ctrl+3"), self).activated.connect(lambda: self.main_tabs.setCurrentIndex(2))
        QShortcut(QKeySequence("Ctrl+4"), self).activated.connect(lambda: self.main_tabs.setCurrentIndex(3))

        # Quick actions
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(lambda: self.main_tabs.setCurrentIndex(0))  # Dashboard
        QShortcut(QKeySequence("F1"), self).activated.connect(self._show_shortcuts_help)

        logger.info("Keyboard shortcuts configured")

    def _show_shortcuts_help(self):
        """Show keyboard shortcuts help dialog."""
        shortcuts_text = """
        <h2>🎹 Keyboard Shortcuts</h2>

        <h3>📁 File Operations</h3>
        <table>
        <tr><td><b>Ctrl+O</b></td><td>Add files</td></tr>
        <tr><td><b>Ctrl+Shift+O</b></td><td>Add folder</td></tr>
        </table>

        <h3>▶️ Analysis Operations</h3>
        <table>
        <tr><td><b>F5 or Ctrl+P</b></td><td>Start analysis</td></tr>
        <tr><td><b>Escape or Ctrl+.</b></td><td>Stop analysis</td></tr>
        </table>

        <h3>📑 Navigation</h3>
        <table>
        <tr><td><b>Ctrl+1</b></td><td>Dashboard tab</td></tr>
        <tr><td><b>Ctrl+2</b></td><td>Analysis tab</td></tr>
        <tr><td><b>Ctrl+3</b></td><td>Filters tab</td></tr>
        <tr><td><b>Ctrl+4</b></td><td>Batch Queue tab</td></tr>
        <tr><td><b>Ctrl+D</b></td><td>Go to Dashboard</td></tr>
        </table>

        <h3>🎨 View & Settings</h3>
        <table>
        <tr><td><b>Ctrl+,</b></td><td>Open Settings</td></tr>
        <tr><td><b>Ctrl+L</b></td><td>View Clusters</td></tr>
        <tr><td><b>Ctrl+R</b></td><td>Generate Report</td></tr>
        <tr><td><b>Ctrl+Q</b></td><td>Exit application</td></tr>
        </table>

        <h3>❓ Help</h3>
        <table>
        <tr><td><b>F1</b></td><td>Show this help</td></tr>
        </table>
        """

        QMessageBox.information(self, "Keyboard Shortcuts", shortcuts_text)

    def _apply_theme(self, theme_type: ThemeType):
        """
        Apply the selected theme to the application.

        Args:
            theme_type: The theme type to apply (LIGHT or DARK).
        """
        try:
            # Apply theme stylesheet
            Theme.apply_theme(self, theme_type)

            # Update current theme
            self.current_theme = theme_type

            # Save theme preference
            self.settings_manager.settings.setValue("ui/theme", theme_type.value)

            logger.info(f"Theme changed to: {theme_type.value}")

        except Exception as e:
            logger.error(f"Error applying theme: {e}")
            QMessageBox.warning(
                self,
                "Theme Error",
                f"Failed to apply theme: {e}"
            )

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
