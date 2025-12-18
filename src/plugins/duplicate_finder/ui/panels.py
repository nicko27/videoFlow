"""
UI panel creation utilities for the duplicate finder.

This module provides factory methods for creating UI panels and their components,
separating UI construction from business logic.
"""
from typing import Callable, Dict
import json
import os
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox,
    QGridLayout, QDoubleSpinBox, QSpinBox, QFrame, QLabel, QTabWidget,
    QCheckBox, QComboBox, QScrollArea, QFileDialog, QLineEdit, QTextEdit,
    QListWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .widgets.progress_widgets import ModernProgressWidget, FileListWidget, StatusIndicator, HashDebuggerV2, AudioFingerprintDebugger
from ..infrastructure.config.design_system import get_current_theme
from ..validators import ConfigValidator
from src.core.i18n import t
import cv2
from ..verification_pipeline import VerificationPipeline
from ..data import DatabaseManager
from .benchmark_widgets import BenchmarkTabWidget


class UIPanels:
    """
    Factory class for creating UI panels and components.

    This class provides static methods for creating various UI elements
    used in the duplicate finder main window. It encapsulates all UI
    construction logic in one place.

    Example:
        ```python
        panels = UIPanels()
        left_panel = panels.create_left_panel(callbacks)
        right_panel = panels.create_right_panel()
        ```
    """

    @staticmethod
    def create_title_label() -> QLabel:
        """
        Create the main title label.

        Returns:
            Configured QLabel for the window title.
        """
        theme = get_current_theme()
        title = QLabel("🔍 Détecteur de doublons vidéo")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(theme.get_title_style())
        return title

    @staticmethod
    def create_left_panel(
        file_list_widget: FileListWidget,
        callbacks: Dict[str, Callable],
        db_manager = None
    ) -> QFrame:
        """
        Create the left configuration panel.

        Args:
            file_list_widget: FileListWidget instance.
            callbacks: Dictionary of callback functions with keys:
                - 'add_files', 'add_folder', 'clear_list', 'clear_cache'
                - 'apply_preset', 'analyze', 'stop'
                - 'show_stats', 'show_pending', 'close'
            db_manager: Optional DatabaseManager instance for benchmark system.

        Returns:
            Configured QFrame containing the left panel.
        """
        theme = get_current_theme()
        colors = theme.get_colors()
        spacing = theme.get_spacing()

        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['bg_card']};
                border: 1px solid {colors['border']};
                border-radius: {spacing['radius']}px;
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(spacing['padding'], spacing['padding'],
                                   spacing['padding'], spacing['padding'])
        layout.setSpacing(spacing['gap'])

        # Configuration tabs
        config_tabs = UIPanels._create_config_tabs(file_list_widget, callbacks, db_manager)
        layout.addWidget(config_tabs)

        # Action buttons (only for analysis, not for benchmark/batch)
        action_buttons = UIPanels._create_action_buttons(callbacks)
        layout.addWidget(action_buttons)

        # Hide action buttons when benchmark or batch queue tab is active
        def on_tab_changed(index):
            tab_widget = config_tabs.widget(index)
            if tab_widget and hasattr(tab_widget, 'objectName'):
                tab_name = tab_widget.objectName()
                # Show buttons only for files and params tabs
                should_show = tab_name in ['files_tab', 'params_tab']
                action_buttons.setVisible(should_show)

        # Connect signal
        config_tabs.currentChanged.connect(on_tab_changed)

        # Set initial visibility (files tab is usually first)
        on_tab_changed(config_tabs.currentIndex())

        return panel

    @staticmethod
    def _create_config_tabs(
        file_list_widget: FileListWidget,
        callbacks: Dict[str, Callable],
        db_manager = None
    ) -> QTabWidget:
        """
        Create the configuration tabs widget.

        Args:
            file_list_widget: FileListWidget instance.
            callbacks: Dictionary of callbacks.
            db_manager: Optional DatabaseManager instance for benchmark system.

        Returns:
            Configured QTabWidget.
        """
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                background-color: #FAFAFA;
            }
            QTabBar::tab {
                background: #F8F9FA;
                border: 1px solid #DEE2E6;
                padding: 8px 16px;
                margin-right: 2px;
                border-radius: 4px 4px 0px 0px;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                border-bottom: 1px solid #FFFFFF;
            }
        """)

        # Utiliser un seul PipelineManager partagé pour tous les onglets
        pipeline_manager = None
        if db_manager:
            from ..orchestration.pipeline_manager import PipelineManager
            pipeline_manager = PipelineManager(db_manager)

        # Files tab
        files_tab = UIPanels._create_files_tab(file_list_widget, callbacks)
        files_tab.setObjectName("files_tab")
        tabs.addTab(files_tab, "📁 Fichiers")

        # Parameters tab
        params_tab = UIPanels._create_parameters_tab(callbacks, db_manager, pipeline_manager)
        params_tab.setObjectName("params_tab")
        tabs.addTab(params_tab, "⚙️ Paramètres")

        # Benchmark tab (Multi-Pipeline Comparison)
        if db_manager:
            from .multi_pipeline_benchmark import MultiPipelineBenchmarkWidget
            from ..services.benchmark_manager import BenchmarkManager
            from ..services.test_set_manager import TestSetManager
            
            benchmark_tab = MultiPipelineBenchmarkWidget(
                BenchmarkManager(db_manager),
                pipeline_manager,
                TestSetManager(db_manager),
                db_manager,
                file_list_widget
            )
            benchmark_tab.setObjectName("benchmark_tab")
            tabs.addTab(benchmark_tab, "📊 Benchmark")

            # Store reference to benchmark widget for signal connection in main window
            tabs.benchmark_widget = benchmark_tab
        else:
            tabs.benchmark_widget = None

        # Batch Queue tab
        from .batch_queue_widget import BatchQueueWidget
        from ..controllers.batch_controller import get_batch_controller
        batch_queue_tab = BatchQueueWidget(
            batch_controller=get_batch_controller(),
            config_manager=None  # Will be set by main_window
        )
        batch_queue_tab.setObjectName("batch_queue_tab")
        tabs.addTab(batch_queue_tab, "📋 Batch Queue")

        return tabs

    @staticmethod
    def _create_files_tab(
        file_list_widget: FileListWidget,
        callbacks: Dict[str, Callable]
    ) -> QWidget:
        """
        Create the files management tab.

        Args:
            file_list_widget: FileListWidget instance.
            callbacks: Dictionary of callbacks.

        Returns:
            Configured QWidget for files tab.
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Reload last folder button (optional, hidden by default)
        reload_last_folder_btn = QPushButton("🔄 Recharger le dernier dossier")
        reload_last_folder_btn.setMinimumHeight(35)
        reload_last_folder_btn.setStyleSheet(UIPanels._get_button_style("#17A2B8", "#138496"))
        reload_last_folder_btn.clicked.connect(callbacks.get('reload_last_folder', lambda: None))
        reload_last_folder_btn.setVisible(False)  # Hidden by default
        layout.addWidget(reload_last_folder_btn)

        # Store reference for later access
        tab.reload_last_folder_btn = reload_last_folder_btn

        # Button grid
        buttons_layout = QGridLayout()
        buttons_layout.setSpacing(10)

        # Add files button
        add_files_btn = QPushButton("📄 Ajouter des fichiers")
        add_files_btn.setMinimumHeight(40)
        add_files_btn.setStyleSheet(UIPanels._get_button_style("#007BFF", "#0056B3"))
        add_files_btn.clicked.connect(callbacks['add_files'])

        # Add folder button
        add_folder_btn = QPushButton("📂 Ajouter un dossier")
        add_folder_btn.setMinimumHeight(40)
        add_folder_btn.setStyleSheet(UIPanels._get_button_style("#28A745", "#1E7E34"))
        add_folder_btn.clicked.connect(callbacks['add_folder'])

        # Clear list button
        clear_btn = QPushButton("🗑️ Effacer la liste")
        clear_btn.setMinimumHeight(40)
        clear_btn.setStyleSheet(UIPanels._get_button_style("#FD7E14", "#E55A00"))
        clear_btn.clicked.connect(callbacks['clear_list'])

        # Clear cache button
        clear_cache_btn = QPushButton("💾 Effacer le cache")
        clear_cache_btn.setMinimumHeight(40)
        clear_cache_btn.setStyleSheet(UIPanels._get_button_style("#6F42C1", "#59359A"))
        clear_cache_btn.clicked.connect(callbacks['clear_cache'])

        # Reset folder button
        reset_folder_btn = QPushButton("🔄 Réinitialiser le dossier")
        reset_folder_btn.setMinimumHeight(40)
        reset_folder_btn.setStyleSheet(UIPanels._get_button_style("#DC3545", "#C82333"))
        reset_folder_btn.clicked.connect(callbacks.get('reset_folder', lambda: None))

        buttons_layout.addWidget(add_files_btn, 0, 0)
        buttons_layout.addWidget(add_folder_btn, 0, 1)
        buttons_layout.addWidget(clear_btn, 1, 0)
        buttons_layout.addWidget(clear_cache_btn, 1, 1)
        buttons_layout.addWidget(reset_folder_btn, 2, 0, 1, 2)  # Span both columns

        # Scene detection button
        scene_detection_btn = QPushButton("🎬 Détection de Scènes")
        scene_detection_btn.setMinimumHeight(40)
        scene_detection_btn.setStyleSheet(UIPanels._get_button_style("#1565C0", "#0D47A1"))  # Blue
        scene_detection_btn.setToolTip(
            "Détection de scènes utilisant empreintes audio et vérification visuelle.\n"
            "• Empreintes audio (rapide)\n"
            "• Vérification DCT + Scene Cuts\n\n"
            "La progression s'affiche dans les barres principales"
        )
        scene_detection_btn.clicked.connect(callbacks.get('start_scene_detection', lambda: None))
        buttons_layout.addWidget(scene_detection_btn, 3, 0, 1, 2)  # Span both columns

        layout.addLayout(buttons_layout)
        layout.addWidget(file_list_widget)

        return tab

    @staticmethod
    def _create_parameters_tab(callbacks: Dict[str, Callable], db_manager=None, pipeline_manager=None) -> QWidget:
        """
        Create the parameters configuration tab with scrollbar.

        Includes all optimization parameters:
        - Audio fingerprinting (primary filter)
        - LSH (Locality Sensitive Hashing)
        - Multi-resolution comparison
        - Video hashing & comparison
        - Flip detection
        - Presets

        Args:
            callbacks: Dictionary of callbacks.
            db_manager: Database manager for saving pipelines.

        Returns:
            Configured QWidget for parameters tab.
        """
        tab = QWidget()

        # Initialize PipelineManager if not provided but db_manager available
        if pipeline_manager is None and db_manager:
            from ..orchestration.pipeline_manager import PipelineManager
            pipeline_manager = PipelineManager(db_manager)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # Create content widget for scrollable content
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # ═══════════════════════════════════════════════════════════
        # LANGUAGE SELECTOR
        # ═══════════════════════════════════════════════════════════
        # NOTE: Language selection is now controlled by central i18n system
        # The language combo has been removed as it's managed globally
        # If needed, add a global language selector in the main app settings

        # ═══════════════════════════════════════════════════════════
        # PRESETS (En haut pour accès facile)
        # ═══════════════════════════════════════════════════════════
        presets_group = QGroupBox(f"🚀 {t('duplicate_finder.ui.presets.title', 'Quick Presets')}")
        presets_layout = QGridLayout(presets_group)
        presets_layout.setSpacing(10)

        speed_btn = QPushButton(f"⚡ {t('duplicate_finder.ui.presets.speed', 'Maximum Speed')}")
        speed_btn.setMinimumHeight(35)
        speed_btn.setStyleSheet(UIPanels._get_button_style("#DC3545", "#A71E2A"))
        speed_btn.clicked.connect(lambda: callbacks['apply_preset']("maximum_speed"))
        speed_btn.setToolTip(t('duplicate_finder.ui.presets.speed_tooltip', 'All optimizations enabled, fastest speed\n(May have slight precision trade-offs)'))

        balanced_btn = QPushButton(f"⚖️ {t('duplicate_finder.ui.presets.balanced', 'Balanced (Recommended)')}")
        balanced_btn.setMinimumHeight(35)
        balanced_btn.setStyleSheet(UIPanels._get_button_style("#007BFF", "#0056B3"))
        balanced_btn.clicked.connect(lambda: callbacks['apply_preset']("balanced"))
        balanced_btn.setToolTip(t('duplicate_finder.ui.presets.balanced_tooltip', 'Best balance of speed and accuracy\n(Recommended for most users)'))

        quality_btn = QPushButton(f"🎯 {t('duplicate_finder.ui.presets.quality', 'Maximum Quality')}")
        quality_btn.setMinimumHeight(35)
        quality_btn.setStyleSheet(UIPanels._get_button_style("#28A745", "#1E7E34"))
        quality_btn.clicked.connect(lambda: callbacks['apply_preset']("maximum_quality"))
        quality_btn.setToolTip(t('duplicate_finder.ui.presets.quality_tooltip', 'All comparisons, maximum precision\n(Slower but 100% accurate)'))

        presets_layout.addWidget(speed_btn, 0, 0)
        presets_layout.addWidget(balanced_btn, 0, 1)
        presets_layout.addWidget(quality_btn, 1, 0, 1, 2)

        layout.addWidget(presets_group)

        # ═══════════════════════════════════════════════════════════
        # EMPREINTE AUDIO (Filtre principal)
        # ═══════════════════════════════════════════════════════════
        audio_group = QGroupBox(f"🎵 {t('duplicate_finder.ui.audio.title', 'Audio Fingerprinting (Primary Filter)')}")
        audio_layout = QGridLayout(audio_group)
        audio_layout.setSpacing(10)

        # Seuil de similarité audio (paramètre principal)
        audio_layout.addWidget(QLabel(t('duplicate_finder.ui.audio.threshold', 'Audio similarity threshold:')), 0, 0)
        audio_threshold_spin = QDoubleSpinBox()
        audio_threshold_spin.setRange(50.0, 95.0)
        audio_threshold_spin.setValue(70.0)
        audio_threshold_spin.setSuffix(t('duplicate_finder.ui.common.percent', '%'))
        audio_threshold_spin.setDecimals(1)
        audio_threshold_spin.setToolTip(t('duplicate_finder.ui.audio.threshold_tooltip', 'Videos with audio similarity below this threshold are rejected\nLower = More candidates (slower but catches more)\nHigher = Fewer candidates (faster but may miss some)\nRecommended: 70%'))
        audio_layout.addWidget(audio_threshold_spin, 0, 1)

        # Mode de précision
        audio_layout.addWidget(QLabel(t('duplicate_finder.ui.audio.precision', 'Precision mode:')), 1, 0)
        audio_precision_combo = QComboBox()
        audio_precision_combo.addItem(f"⚡ {t('duplicate_finder.ui.audio.precision_fast', 'Fast (2-5s/video, 95%)')}", "fast")
        audio_precision_combo.addItem(f"⚖️ {t('duplicate_finder.ui.audio.precision_balanced', 'Balanced (5-15s/video, 99%)')}", "balanced")
        audio_precision_combo.addItem(f"🎯 {t('duplicate_finder.ui.audio.precision_maximum', 'Maximum (10-30s/video, 99.9%)')}", "maximum")
        audio_precision_combo.setCurrentIndex(0)  # Par défaut Rapide
        audio_precision_combo.setToolTip(t('duplicate_finder.ui.audio.precision_tooltip', 'Fast: Quick extraction, good for most cases\nBalanced: Better precision, moderate speed\nMaximum: Best precision, slower'))
        audio_layout.addWidget(audio_precision_combo, 1, 1)

        # Workers audio
        audio_layout.addWidget(QLabel(t('duplicate_finder.ui.audio.workers', 'Audio workers:')), 2, 0)
        audio_workers_spin = QSpinBox()
        audio_workers_spin.setRange(1, 16)
        audio_workers_spin.setValue(4)
        audio_workers_spin.setToolTip(t('duplicate_finder.ui.audio.workers_tooltip', 'Number of parallel workers for audio extraction'))
        audio_layout.addWidget(audio_workers_spin, 2, 1)

        # Taille du cache audio
        audio_layout.addWidget(QLabel(t('duplicate_finder.ui.audio.cache_size', 'Audio cache size:')), 3, 0)
        audio_cache_size_spin = QSpinBox()
        audio_cache_size_spin.setRange(100, 5000)
        audio_cache_size_spin.setValue(1000)
        audio_cache_size_spin.setSuffix(t('duplicate_finder.ui.audio.cache_size_suffix', ' items'))
        audio_cache_size_spin.setToolTip(t('duplicate_finder.ui.audio.cache_size_tooltip', 'Maximum audio fingerprints to cache in memory'))
        audio_layout.addWidget(audio_cache_size_spin, 3, 1)

        # Activer le fallback pour vidéos sans audio
        enable_no_audio_fallback = QCheckBox(t('duplicate_finder.ui.audio.fallback', 'Enable fallback for videos without audio'))
        enable_no_audio_fallback.setChecked(True)
        enable_no_audio_fallback.setToolTip(t('duplicate_finder.ui.audio.fallback_tooltip', 'If enabled, videos without audio will be compared using video hashing only\nIf disabled, videos without audio will be skipped'))
        audio_layout.addWidget(enable_no_audio_fallback, 4, 0, 1, 2)

        # Label d'information
        audio_info = QLabel(f"ℹ️ {t('duplicate_finder.ui.audio.info', 'Audio fingerprinting filters 85-90% of video pairs before video comparison. Requires fpcalc (chromaprint): brew install chromaprint (macOS) or apt install chromaprint-tools (Linux)')}")
        audio_info.setStyleSheet("QLabel { color: #6C757D; font-size: 9px; padding: 5px; }")
        audio_info.setWordWrap(True)
        audio_layout.addWidget(audio_info, 5, 0, 1, 2)

        layout.addWidget(audio_group)

        # ═══════════════════════════════════════════════════════════
        # LSH (Hachage sensible à la localité)
        # ═══════════════════════════════════════════════════════════
        lsh_group = QGroupBox(f"🔍 {t('duplicate_finder.ui.lsh.title', 'LSH (Locality Sensitive Hashing)')}")
        lsh_layout = QGridLayout(lsh_group)
        lsh_layout.setSpacing(10)

        # Activer LSH
        enable_lsh_check = QCheckBox(t('duplicate_finder.ui.lsh.enable', 'Enable LSH (Recommended for 500+ videos)'))
        enable_lsh_check.setChecked(True)
        enable_lsh_check.setStyleSheet("QCheckBox { font-weight: bold; }")
        enable_lsh_check.setToolTip(t('duplicate_finder.ui.lsh.enable_tooltip', 'LSH reduces O(N²) comparisons to O(N·k) by grouping similar items\nProvides 20-50x speedup on large datasets'))
        lsh_layout.addWidget(enable_lsh_check, 0, 0, 1, 2)

        # Bandes LSH
        lsh_layout.addWidget(QLabel(t('duplicate_finder.ui.lsh.bands', 'LSH bands:')), 1, 0)
        lsh_bands_spin = QSpinBox()
        lsh_bands_spin.setRange(10, 50)
        lsh_bands_spin.setValue(20)
        lsh_bands_spin.setToolTip(t('duplicate_finder.ui.lsh.bands_tooltip', 'More bands = More buckets = Better precision but slower'))
        lsh_layout.addWidget(lsh_bands_spin, 1, 1)

        # Lignes par bande
        lsh_layout.addWidget(QLabel(t('duplicate_finder.ui.lsh.rows', 'Rows per band:')), 2, 0)
        lsh_rows_spin = QSpinBox()
        lsh_rows_spin.setRange(3, 10)
        lsh_rows_spin.setValue(5)
        lsh_rows_spin.setToolTip(t('duplicate_finder.ui.lsh.rows_tooltip', 'More rows = Stricter matching = Fewer false positives'))
        lsh_layout.addWidget(lsh_rows_spin, 2, 1)

        # LSH pour vidéos sans audio
        enable_lsh_no_audio = QCheckBox(t('duplicate_finder.ui.lsh.no_audio', 'Use LSH for no-audio videos'))
        enable_lsh_no_audio.setChecked(True)
        enable_lsh_no_audio.setToolTip(t('duplicate_finder.ui.lsh.no_audio_tooltip', 'Apply LSH optimization to videos without audio'))
        lsh_layout.addWidget(enable_lsh_no_audio, 3, 0, 1, 2)

        # Label d'information
        lsh_info = QLabel(f"ℹ️ {t('duplicate_finder.ui.lsh.info', 'LSH groups similar fingerprints into buckets, comparing only within buckets. Example: 1000 videos → 499,500 pairs reduced to ~40,000 pairs (90% reduction)')}")
        lsh_info.setStyleSheet("QLabel { color: #6C757D; font-size: 9px; padding: 5px; }")
        lsh_info.setWordWrap(True)
        lsh_layout.addWidget(lsh_info, 4, 0, 1, 2)

        layout.addWidget(lsh_group)

        # ═══════════════════════════════════════════════════════════
        # COMPARAISON MULTI-RÉSOLUTION
        # ═══════════════════════════════════════════════════════════
        mr_group = QGroupBox(f"📊 {t('duplicate_finder.ui.multi_resolution.title', 'Multi-Resolution Comparison')}")
        mr_layout = QGridLayout(mr_group)
        mr_layout.setSpacing(10)

        # Activer multi-résolution
        enable_mr_check = QCheckBox(t('duplicate_finder.ui.multi_resolution.enable', 'Enable multi-resolution (Coarse → Medium → Fine)'))
        enable_mr_check.setChecked(True)
        enable_mr_check.setStyleSheet("QCheckBox { font-weight: bold; }")
        enable_mr_check.setToolTip(t('duplicate_finder.ui.multi_resolution.enable_tooltip', 'Compare audio progressively: short sample → medium → full\nProvides 2-3x speedup by rejecting early'))
        mr_layout.addWidget(enable_mr_check, 0, 0, 1, 2)

        # Paramètres grossiers
        mr_layout.addWidget(QLabel(t('duplicate_finder.ui.multi_resolution.coarse_duration', 'Coarse duration:')), 1, 0)
        mr_coarse_duration_spin = QSpinBox()
        mr_coarse_duration_spin.setRange(10, 60)
        mr_coarse_duration_spin.setValue(30)
        mr_coarse_duration_spin.setSuffix(t('duplicate_finder.ui.common.sec', ' sec'))
        mr_coarse_duration_spin.setToolTip(t('duplicate_finder.ui.multi_resolution.coarse_duration_tooltip', 'Duration of quick test sample'))
        mr_layout.addWidget(mr_coarse_duration_spin, 1, 1)

        mr_layout.addWidget(QLabel(t('duplicate_finder.ui.multi_resolution.coarse_threshold', 'Coarse threshold:')), 2, 0)
        mr_coarse_threshold_spin = QDoubleSpinBox()
        mr_coarse_threshold_spin.setRange(50.0, 80.0)
        mr_coarse_threshold_spin.setValue(60.0)
        mr_coarse_threshold_spin.setSuffix(t('duplicate_finder.ui.common.percent', '%'))
        mr_coarse_threshold_spin.setDecimals(1)
        mr_coarse_threshold_spin.setToolTip(t('duplicate_finder.ui.multi_resolution.coarse_threshold_tooltip', 'Reject if quick test is below this threshold'))
        mr_layout.addWidget(mr_coarse_threshold_spin, 2, 1)

        # Paramètres moyens
        mr_layout.addWidget(QLabel(t('duplicate_finder.ui.multi_resolution.medium_duration', 'Medium duration:')), 3, 0)
        mr_medium_duration_spin = QSpinBox()
        mr_medium_duration_spin.setRange(60, 300)
        mr_medium_duration_spin.setValue(120)
        mr_medium_duration_spin.setSuffix(t('duplicate_finder.ui.common.sec', ' sec'))
        mr_medium_duration_spin.setToolTip(t('duplicate_finder.ui.multi_resolution.medium_duration_tooltip', 'Duration of medium test sample'))
        mr_layout.addWidget(mr_medium_duration_spin, 3, 1)

        mr_layout.addWidget(QLabel(t('duplicate_finder.ui.multi_resolution.medium_threshold', 'Medium threshold:')), 4, 0)
        mr_medium_threshold_spin = QDoubleSpinBox()
        mr_medium_threshold_spin.setRange(55.0, 85.0)
        mr_medium_threshold_spin.setValue(65.0)
        mr_medium_threshold_spin.setSuffix(t('duplicate_finder.ui.common.percent', '%'))
        mr_medium_threshold_spin.setDecimals(1)
        mr_medium_threshold_spin.setToolTip(t('duplicate_finder.ui.multi_resolution.medium_threshold_tooltip', 'Reject if medium test is below this threshold'))
        mr_layout.addWidget(mr_medium_threshold_spin, 4, 1)

        # Label d'information
        mr_info = QLabel(f"ℹ️ {t('duplicate_finder.ui.multi_resolution.info', 'Progressive filtering: Most pairs rejected in coarse phase (fastest), fewer reach medium phase, only best candidates get full comparison.')}")
        mr_info.setStyleSheet("QLabel { color: #6C757D; font-size: 9px; padding: 5px; }")
        mr_info.setWordWrap(True)
        mr_layout.addWidget(mr_info, 5, 0, 1, 2)

        layout.addWidget(mr_group)

        # ═══════════════════════════════════════════════════════════
        # FILTRE MÉTADONNÉES (Optionnel)
        # ═══════════════════════════════════════════════════════════
        metadata_group = QGroupBox(f"📋 {t('duplicate_finder.ui.metadata.title', 'Metadata Quick Filter (Optional)')}")
        metadata_layout = QGridLayout(metadata_group)
        metadata_layout.setSpacing(10)

        # Activer le filtre métadonnées
        enable_metadata_check = QCheckBox(t('duplicate_finder.ui.metadata.enable', 'Enable metadata pre-filter'))
        enable_metadata_check.setChecked(False)  # Désactivé par défaut
        enable_metadata_check.setToolTip(t('duplicate_finder.ui.metadata.enable_tooltip', '⚠️ WARNING: May create false negatives if videos are re-encoded!\nFilters by duration and file size before audio comparison.\nOnly enable if you\'re sure videos have not been re-encoded.'))
        enable_metadata_check.setStyleSheet("QCheckBox { color: #DC3545; }")
        metadata_layout.addWidget(enable_metadata_check, 0, 0, 1, 2)

        # Tolérance de durée
        metadata_layout.addWidget(QLabel(t('duplicate_finder.ui.metadata.duration_tolerance', 'Duration tolerance:')), 1, 0)
        metadata_duration_tolerance_spin = QDoubleSpinBox()
        metadata_duration_tolerance_spin.setRange(0.01, 0.20)
        metadata_duration_tolerance_spin.setValue(0.05)
        metadata_duration_tolerance_spin.setSuffix(" (5%)")
        metadata_duration_tolerance_spin.setDecimals(2)
        metadata_duration_tolerance_spin.setToolTip(t('duplicate_finder.ui.metadata.duration_tolerance_tooltip', 'Reject if duration difference > this percentage'))
        metadata_layout.addWidget(metadata_duration_tolerance_spin, 1, 1)

        # Ratio de taille minimum
        metadata_layout.addWidget(QLabel(t('duplicate_finder.ui.metadata.size_ratio', 'Min size ratio:')), 2, 0)
        metadata_size_ratio_spin = QDoubleSpinBox()
        metadata_size_ratio_spin.setRange(0.50, 0.99)
        metadata_size_ratio_spin.setValue(0.90)
        metadata_size_ratio_spin.setSuffix(" (90%)")
        metadata_size_ratio_spin.setDecimals(2)
        metadata_size_ratio_spin.setToolTip(t('duplicate_finder.ui.metadata.size_ratio_tooltip', 'Reject if size ratio < this value'))
        metadata_layout.addWidget(metadata_size_ratio_spin, 2, 1)

        # Label d'avertissement
        metadata_warning = QLabel(f"⚠️ {t('duplicate_finder.ui.metadata.warning', '⚠️ Metadata filter can miss re-encoded duplicates with different sizes/durations. Only enable if you need maximum speed and are sure videos are identical copies.')}")
        metadata_warning.setStyleSheet("QLabel { color: #DC3545; font-size: 9px; padding: 5px; font-weight: bold; }")
        metadata_warning.setWordWrap(True)
        metadata_layout.addWidget(metadata_warning, 3, 0, 1, 2)

        layout.addWidget(metadata_group)

        # ═══════════════════════════════════════════════════════════
        # HACHAGE VIDÉO
        # ═══════════════════════════════════════════════════════════
        video_hash_group = QGroupBox(f"🎬 {t('duplicate_finder.ui.video_hash.title', 'Video Hashing (Selective)')}")
        video_hash_layout = QGridLayout(video_hash_group)
        video_hash_layout.setSpacing(10)

        # Méthode de hash
        video_hash_layout.addWidget(QLabel(t('duplicate_finder.ui.video_hash.method', 'Hash method:')), 0, 0)
        hash_method_combo = QComboBox()
        hash_method_combo.addItem(f"🎯 {t('duplicate_finder.ui.video_hash.method_phash', 'pHash (Precise, slower)')}", "pHash")
        hash_method_combo.addItem(f"⚖️ {t('duplicate_finder.ui.video_hash.method_dhash', 'dHash (Balanced)')}", "dHash")
        hash_method_combo.addItem(f"⚡ {t('duplicate_finder.ui.video_hash.method_ahash', 'aHash (Fast, less precise)')}", "aHash")
        hash_method_combo.setCurrentIndex(0)  # Par défaut pHash
        hash_method_combo.setToolTip(t(
            'duplicate_finder.ui.video_hash.method_tooltip',
            'pHash: Most accurate (DCT-based), ~1s per video\n'
            'dHash: Good balance (gradient-based), ~0.5s per video\n'
            'aHash: Fastest (average-based), ~0.2s per video'
        ))
        video_hash_layout.addWidget(hash_method_combo, 0, 1)

        # Workers hash
        video_hash_layout.addWidget(QLabel(t('duplicate_finder.ui.video_hash.workers', 'Hash workers:')), 1, 0)
        hash_workers_spin = QSpinBox()
        hash_workers_spin.setRange(
            ConfigValidator.MIN_WORKERS,
            ConfigValidator.MAX_WORKERS
        )
        hash_workers_spin.setValue(ConfigValidator.DEFAULT_HASH_WORKERS)
        hash_workers_spin.setToolTip(t(
            'duplicate_finder.ui.video_hash.workers_tooltip',
            'Number of parallel threads for video hashing\n'
            'More = Faster (uses more CPU/RAM)\n'
            'Recommended: 60-100% of your CPUs\n'
            'Auto-optimized: Detected based on your CPU'
        ))
        video_hash_layout.addWidget(hash_workers_spin, 1, 1)

        # Timeout hash
        video_hash_layout.addWidget(QLabel(t('duplicate_finder.ui.video_hash.timeout', 'Hash timeout:')), 2, 0)
        hash_timeout_spin = QSpinBox()
        hash_timeout_spin.setRange(30, 600)
        hash_timeout_spin.setValue(120)
        hash_timeout_spin.setSuffix(t('duplicate_finder.ui.common.sec', ' sec'))
        hash_timeout_spin.setToolTip(t('duplicate_finder.ui.video_hash.timeout_tooltip', 'Timeout per video for hash computation'))
        video_hash_layout.addWidget(hash_timeout_spin, 2, 1)

        # Taille du cache vidéo
        video_hash_layout.addWidget(QLabel(t('duplicate_finder.ui.video_hash.cache_size', 'Video cache size:')), 3, 0)
        video_cache_size_spin = QSpinBox()
        video_cache_size_spin.setRange(500, 10000)
        video_cache_size_spin.setValue(2000)
        video_cache_size_spin.setSuffix(t('duplicate_finder.ui.video_hash.cache_size_suffix', ' items'))
        video_cache_size_spin.setToolTip(t('duplicate_finder.ui.video_hash.cache_size_tooltip', 'Maximum video hashes to cache in memory'))
        video_hash_layout.addWidget(video_cache_size_spin, 3, 1)

        # Label d'information
        video_hash_info = QLabel(f"ℹ️ {t('duplicate_finder.ui.video_hash.info', 'Videos are hashed ONLY if their audio similarity is above threshold. Selective hashing saves 70-90% of video processing time!')}")
        video_hash_info.setStyleSheet("QLabel { color: #6C757D; font-size: 9px; padding: 5px; }")
        video_hash_info.setWordWrap(True)
        video_hash_layout.addWidget(video_hash_info, 4, 0, 1, 2)

        layout.addWidget(video_hash_group)

        # ═══════════════════════════════════════════════════════════
        # COMPARAISON VIDÉO
        # ═══════════════════════════════════════════════════════════
        video_comp_group = QGroupBox(f"🔍 {t('duplicate_finder.ui.video_comparison.title', 'Video Comparison')}")
        video_comp_layout = QGridLayout(video_comp_group)
        video_comp_layout.setSpacing(10)

        # Seuil de similarité vidéo
        video_comp_layout.addWidget(QLabel(t('duplicate_finder.ui.video_comparison.threshold', 'Video similarity threshold:')), 0, 0)
        video_threshold_spin = QDoubleSpinBox()
        video_threshold_spin.setRange(70.0, 99.0)
        video_threshold_spin.setValue(90.0)
        video_threshold_spin.setSuffix(t('duplicate_finder.ui.common.percent', '%'))
        video_threshold_spin.setDecimals(1)
        video_threshold_spin.setToolTip(t('duplicate_finder.ui.video_comparison.threshold_tooltip', 'Videos with similarity above this threshold are marked as duplicates\nRecommended: 90%'))
        video_comp_layout.addWidget(video_threshold_spin, 0, 1)

        # Activer la détection de flip
        enable_flip_detection = QCheckBox(t('duplicate_finder.ui.video_comparison.flip_detection', 'Enable flip detection (mirror/horizontal flip)'))
        enable_flip_detection.setChecked(True)
        enable_flip_detection.setStyleSheet("QCheckBox { font-weight: bold; }")
        enable_flip_detection.setToolTip(t('duplicate_finder.ui.video_comparison.flip_detection_tooltip', 'Detect videos that are horizontally flipped (mirrored)\nCommon on social media to avoid copyright detection'))
        video_comp_layout.addWidget(enable_flip_detection, 1, 0, 1, 2)

        # Workers de comparaison
        video_comp_layout.addWidget(QLabel(t('duplicate_finder.ui.video_comparison.workers', 'Comparison workers:')), 2, 0)
        comparison_workers_spin = QSpinBox()
        comparison_workers_spin.setRange(
            ConfigValidator.MIN_WORKERS,
            ConfigValidator.MAX_WORKERS
        )
        comparison_workers_spin.setValue(ConfigValidator.DEFAULT_COMPARISON_WORKERS)
        comparison_workers_spin.setToolTip(t(
            'duplicate_finder.ui.video_comparison.workers_tooltip',
            'Number of parallel threads for video comparison\n'
            'More = Much faster (uses more CPU)\n'
            'Recommended: 100% of your CPUs\n'
            'Auto-optimized: Detected based on your CPU'
        ))
        video_comp_layout.addWidget(comparison_workers_spin, 2, 1)

        # Taille de batch
        video_comp_layout.addWidget(QLabel(t('duplicate_finder.ui.video_comparison.batch_size', 'Batch size:')), 3, 0)
        batch_size_spin = QSpinBox()
        batch_size_spin.setRange(10, 500)
        batch_size_spin.setValue(100)
        batch_size_spin.setToolTip(t('duplicate_finder.ui.video_comparison.batch_size_tooltip', 'Number of comparisons per batch'))
        video_comp_layout.addWidget(batch_size_spin, 3, 1)

        # Timeout de comparaison
        video_comp_layout.addWidget(QLabel(t('duplicate_finder.ui.video_comparison.timeout', 'Comparison timeout:')), 4, 0)
        comparison_timeout_spin = QSpinBox()
        comparison_timeout_spin.setRange(5, 120)
        comparison_timeout_spin.setValue(30)
        comparison_timeout_spin.setSuffix(t('duplicate_finder.ui.common.sec', ' sec'))
        comparison_timeout_spin.setToolTip(t('duplicate_finder.ui.video_comparison.timeout_tooltip', 'Timeout per comparison'))
        video_comp_layout.addWidget(comparison_timeout_spin, 4, 1)

        # Taille du cache de comparaison
        video_comp_layout.addWidget(QLabel(t('duplicate_finder.ui.video_comparison.cache_size', 'Comparison cache:')), 5, 0)
        comparison_cache_size_spin = QSpinBox()
        comparison_cache_size_spin.setRange(1000, 50000)
        comparison_cache_size_spin.setValue(10000)
        comparison_cache_size_spin.setSuffix(t('duplicate_finder.ui.video_comparison.cache_size_suffix', ' items'))
        comparison_cache_size_spin.setToolTip(t('duplicate_finder.ui.video_comparison.cache_size_tooltip', 'Maximum comparisons to cache'))
        video_comp_layout.addWidget(comparison_cache_size_spin, 5, 1)

        layout.addWidget(video_comp_group)

        # ═══════════════════════════════════════════════════════════
        # DÉTECTION DE SOUS-SÉQUENCES - PIPELINE DE VÉRIFICATION
        # ═══════════════════════════════════════════════════════════
        subseq_detection_group = QGroupBox("🎯 Pipeline de Vérification (Multi-Méthodes)")
        subseq_detection_layout = QVBoxLayout(subseq_detection_group)
        subseq_detection_layout.setSpacing(15)

        # Description du système
        pipeline_desc = QLabel(
            "Configurez un pipeline de vérification avec plusieurs méthodes exécutées dans l'ordre.\n"
            "Le pipeline s'arrête dès qu'une méthode rejette (short-circuit).\n"
            "Tous les résultats sont cachés en base de données."
        )
        pipeline_desc.setWordWrap(True)
        pipeline_desc.setStyleSheet("QLabel { color: #6C757D; font-size: 10px; padding: 5px; background-color: #F8F9FA; border-radius: 4px; }")
        subseq_detection_layout.addWidget(pipeline_desc)

        # ────────────────────────────────────────────────────────────
        # WIDGET DE CONFIGURATION DU PIPELINE
        # ────────────────────────────────────────────────────────────
        from .pipeline_config_widget import PipelineConfigWidget

        pipeline_config_widget = PipelineConfigWidget()
        subseq_detection_layout.addWidget(pipeline_config_widget)

        # Pipeline save/load buttons
        pipeline_actions_layout = QHBoxLayout()
        pipeline_actions_layout.setSpacing(8)

        save_pipeline_btn = QPushButton("💾 Sauvegarder ce pipeline")
        save_pipeline_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)

        load_pipeline_btn = QPushButton("📂 Charger un pipeline")
        load_pipeline_btn.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)

        manage_pipelines_btn = QPushButton("📚 Gérer les Pipelines")
        manage_pipelines_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
        """)

        def save_pipeline():
            """Save current pipeline configuration to database."""
            from PyQt6.QtWidgets import QMessageBox, QInputDialog

            if not pipeline_manager:
                QMessageBox.warning(None, "Erreur", "Base de données non disponible")
                return

            try:
                config = pipeline_config_widget.get_pipeline_config()

                # Demander un nom pour le pipeline
                name, ok = QInputDialog.getText(
                    None,
                    "Nom du pipeline",
                    "Entrez un nom pour ce pipeline:",
                    text="Mon Pipeline"
                )

                if not ok or not name.strip():
                    return

                # Demander une description
                description, ok = QInputDialog.getText(
                    None,
                    "Description",
                    "Entrez une description (optionnel):",
                    text=""
                )

                if not ok:
                    description = ""

                # Sauvegarder dans la DB
                pipeline_id = pipeline_manager.save_pipeline(
                    name=name.strip(),
                    description=description.strip(),
                    mode=config['mode'],
                    methods=config['methods'],
                    confirmation=config.get('confirmation'),
                    global_threshold=config.get('global_threshold')
                )

                QMessageBox.information(
                    None,
                    "Succès",
                    f"✅ Pipeline '{name}' sauvegardé dans la base de données (ID: {pipeline_id})"
                )
            except ValueError as e:
                QMessageBox.warning(None, "Erreur", str(e))
            except Exception as e:
                QMessageBox.critical(None, "Erreur", f"Erreur de sauvegarde: {e}")

        def load_pipeline():
            """Load pipeline configuration from JSON file."""
            from PyQt6.QtWidgets import QMessageBox
            try:
                file_path, _ = QFileDialog.getOpenFileName(
                    None,
                    "Charger un pipeline",
                    "",
                    "JSON Files (*.json)"
                )
                if file_path:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    pipeline_config_widget.load_pipeline_config(config)
                    QMessageBox.information(
                        None,
                        "Succès",
                        f"Pipeline chargé:\n{file_path}"
                    )
            except Exception as e:
                QMessageBox.critical(None, "Erreur", f"Erreur de chargement: {e}")

        def manage_pipelines():
            """Open pipeline library dialog."""
            from PyQt6.QtWidgets import QMessageBox
            from .pipeline_library_dialog import PipelineLibraryDialog

            if not pipeline_manager:
                QMessageBox.warning(None, "Erreur", "Base de données non disponible")
                return

            # Get main window (traverse up the parent hierarchy)
            import sys
            from PyQt6.QtWidgets import QApplication
            main_window = None
            for widget in QApplication.topLevelWidgets():
                if widget.__class__.__name__ == 'MainWindow':
                    main_window = widget
                    break

            dialog = PipelineLibraryDialog(pipeline_manager, db_manager, parent=main_window)
            dialog.exec()

        save_pipeline_btn.clicked.connect(save_pipeline)
        load_pipeline_btn.clicked.connect(load_pipeline)
        manage_pipelines_btn.clicked.connect(manage_pipelines)

        pipeline_actions_layout.addWidget(save_pipeline_btn)
        pipeline_actions_layout.addWidget(load_pipeline_btn)
        pipeline_actions_layout.addWidget(manage_pipelines_btn)
        pipeline_actions_layout.addStretch()

        subseq_detection_layout.addLayout(pipeline_actions_layout)

        # Store pipeline widget reference
        tab.pipeline_config_widget = pipeline_config_widget

        layout.addWidget(subseq_detection_group)

        layout.addStretch()

        # ═══════════════════════════════════════════════════════════
        # Store all widget references
        # ═══════════════════════════════════════════════════════════

        # Audio fingerprinting
        tab.audio_threshold_spin = audio_threshold_spin
        tab.audio_precision_combo = audio_precision_combo
        tab.audio_workers_spin = audio_workers_spin
        tab.audio_cache_size_spin = audio_cache_size_spin
        tab.enable_no_audio_fallback = enable_no_audio_fallback

        # LSH
        tab.enable_lsh_check = enable_lsh_check
        tab.lsh_bands_spin = lsh_bands_spin
        tab.lsh_rows_spin = lsh_rows_spin
        tab.enable_lsh_no_audio = enable_lsh_no_audio

        # Multi-resolution
        tab.enable_mr_check = enable_mr_check
        tab.mr_coarse_duration_spin = mr_coarse_duration_spin
        tab.mr_coarse_threshold_spin = mr_coarse_threshold_spin
        tab.mr_medium_duration_spin = mr_medium_duration_spin
        tab.mr_medium_threshold_spin = mr_medium_threshold_spin

        # Metadata filter
        tab.enable_metadata_check = enable_metadata_check
        tab.metadata_duration_tolerance_spin = metadata_duration_tolerance_spin
        tab.metadata_size_ratio_spin = metadata_size_ratio_spin

        # Video hashing
        tab.hash_method_combo = hash_method_combo
        tab.hash_workers_spin = hash_workers_spin
        tab.hash_timeout_spin = hash_timeout_spin
        tab.video_cache_size_spin = video_cache_size_spin

        # Video comparison
        tab.threshold_spin = video_threshold_spin  # Renamed for consistency with settings_manager
        tab.video_threshold_spin = video_threshold_spin  # Alias for backward compatibility
        tab.enable_flip_detection = enable_flip_detection
        tab.comparison_workers_spin = comparison_workers_spin
        tab.batch_size_spin = batch_size_spin
        tab.comparison_timeout_spin = comparison_timeout_spin
        tab.comparison_cache_size_spin = comparison_cache_size_spin

        # Subsequence detection - Pipeline configuration
        # Pipeline widget reference is already stored above (tab.pipeline_config_widget)

        # Set scroll area content and add to tab
        scroll_area.setWidget(content_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)

        return tab

    @staticmethod
    def _create_debug_tab(file_list_widget: FileListWidget = None, db_manager = None) -> QWidget:
        """
        Create the debug tab with interactive hash debugger and scrollbar.

        Args:
            file_list_widget: Optional FileListWidget to access main file list.
            db_manager: Optional DatabaseManager instance for benchmark system.

        Returns:
            Configured QWidget for debug tab.
        """
        tab = QWidget()

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # Create content widget for scrollable content
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)

        # Create hash debugger V2 (visual hashing)
        hash_debugger_v2 = HashDebuggerV2()
        layout.addWidget(hash_debugger_v2)

        # Create audio fingerprint debugger (scene detection)
        audio_debugger = AudioFingerprintDebugger()
        layout.addWidget(audio_debugger)

        # ═══════════════════════════════════════════════════════════
        # MAIN FILE LIST DISPLAY
        # ═══════════════════════════════════════════════════════════
        files_display_group = QGroupBox("📋 Fichiers de la Liste Principale")
        files_display_layout = QVBoxLayout(files_display_group)
        files_display_layout.setSpacing(5)

        # File count label
        file_count_label = QLabel("Aucun fichier chargé")
        file_count_label.setStyleSheet("QLabel { font-weight: bold; color: #495057; }")
        files_display_layout.addWidget(file_count_label)

        # File list widget (read-only display)
        files_list_display = QListWidget()
        files_list_display.setMaximumHeight(150)
        files_list_display.setStyleSheet("""
            QListWidget {
                background-color: #F8F9FA;
                border: 1px solid #DEE2E6;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #E9ECEF;
            }
        """)
        files_display_layout.addWidget(files_list_display)

        # Refresh button
        refresh_files_btn = QPushButton("🔄 Actualiser depuis l'onglet principal")
        refresh_files_btn.setMaximumHeight(30)
        refresh_files_btn.setStyleSheet("""
            QPushButton {
                background-color: #17A2B8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)

        def update_file_list_display():
            """Update the file list display from main widget."""
            if not file_list_widget:
                files_list_display.clear()
                file_count_label.setText("❌ Liste principale non disponible")
                return

            files = file_list_widget.get_files()
            files_list_display.clear()

            if not files:
                file_count_label.setText("📂 Aucun fichier chargé")
            else:
                file_count_label.setText(f"📂 {len(files)} fichier(s) - {len(files) * (len(files) - 1) // 2} paires possibles")
                for file_path in files:
                    files_list_display.addItem(f"  {os.path.basename(file_path)}")

        refresh_files_btn.clicked.connect(update_file_list_display)
        files_display_layout.addWidget(refresh_files_btn)

        # Auto-update on creation
        update_file_list_display()

        layout.addWidget(files_display_group)

        # ═══════════════════════════════════════════════════════════
        # TEST PROTOCOLS (TEMPLATES)
        # ═══════════════════════════════════════════════════════════
        protocols_group = QGroupBox("🔬 Protocoles de Tests")
        protocols_layout = QVBoxLayout(protocols_group)
        protocols_layout.setSpacing(8)

        # Protocol selector
        protocol_selector_layout = QHBoxLayout()
        protocol_selector_layout.addWidget(QLabel("Protocole:"))

        protocol_combo = QComboBox()
        protocol_combo.addItem("🎯 Anti-Faux Positifs (Stricte)", "anti_fp")
        protocol_combo.addItem("⚖️ Équilibré (Recommandé)", "balanced")
        protocol_combo.addItem("🔍 Haute Précision (100%)", "high_precision")
        protocol_combo.addItem("⚡ Rapide (Compromis vitesse)", "fast")
        protocol_combo.addItem("📐 DCT Seulement (Réencodage)", "dct_only")
        protocol_combo.addItem("🎬 Motion Seulement (Recadrage)", "motion_only")
        protocol_combo.addItem("🧮 Consensus Pondéré (Weighting)", "weighted_consensus")
        protocol_combo.addItem("🔄 Spécialiste Réencodage", "re_encoded_specialist")
        protocol_combo.addItem("🌊 Ultra Permissif (Max Rappel)", "ultra_permissive")
        protocol_combo.addItem("🛡️ Hybride Conservateur", "hybrid_conservative")
        protocol_combo.addItem("➕ Personnalisé...", "custom")
        protocol_combo.setCurrentIndex(0)  # Default: Anti-FP
        protocol_selector_layout.addWidget(protocol_combo, 1)

        protocols_layout.addLayout(protocol_selector_layout)

        # Protocol description
        protocol_desc = QLabel()
        protocol_desc.setWordWrap(True)
        protocol_desc.setStyleSheet("""
            QLabel {
                background-color: #F8F9FA;
                border: 1px solid #DEE2E6;
                border-radius: 4px;
                padding: 8px;
                color: #495057;
                font-size: 10px;
            }
        """)
        protocols_layout.addWidget(protocol_desc)

        # Protocol definitions
        TEST_PROTOCOLS = {
            'anti_fp': {
                'name': 'Anti-Faux Positifs',
                'description': 'Seuils très stricts (92-97%) pour éliminer tous les faux positifs. Peut manquer certains vrais doublons.',
                'mode': 'filtering',
                'methods': [
                    {'name': 'color_histogram', 'enabled': True, 'parameters': {'threshold': 92.0}, 'weight': 1.5},
                    {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 90.0, 'sample_interval': 3}, 'weight': 1.5},
                    {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 85.0, 'num_coeffs': 15}, 'weight': 2.0},
                    {'name': 'strategy3', 'enabled': True, 'parameters': {'scene_threshold': 60.0, 'dct_threshold': 85.0, 'sequence_threshold': 97.0, 'num_samples': 15, 'warmup_seconds': 0.0, 'max_workers': 8}, 'weight': 3.0}
                ]
            },
            'balanced': {
                'name': 'Équilibré',
                'description': 'Bon compromis entre précision et rappel (seuils 85-90%). Recommandé pour la plupart des cas.',
                'mode': 'filtering',
                'methods': [
                    {'name': 'color_histogram', 'enabled': True, 'parameters': {'threshold': 85.0}, 'weight': 1.0},
                    {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 85.0, 'sample_interval': 3}, 'weight': 1.0},
                    {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 75.0, 'num_coeffs': 15}, 'weight': 1.5},
                    {'name': 'strategy3', 'enabled': True, 'parameters': {'scene_threshold': 50.0, 'dct_threshold': 75.0, 'sequence_threshold': 95.0, 'num_samples': 10, 'warmup_seconds': 0.0, 'max_workers': 8}, 'weight': 2.0}
                ]
            },
            'high_precision': {
                'name': 'Haute Précision',
                'description': 'Tous les tests activés avec seuils très élevés (90-98%). Maximum de fiabilité, lent.',
                'mode': 'hybrid',
                'methods': [
                    {'name': 'color_histogram', 'enabled': True, 'parameters': {'threshold': 90.0}, 'weight': 1.0},
                    {'name': 'edge_pattern', 'enabled': True, 'parameters': {'threshold': 85.0}, 'weight': 1.0},
                    {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 90.0, 'sample_interval': 2}, 'weight': 1.5},
                    {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 85.0, 'num_coeffs': 20}, 'weight': 2.0},
                    {'name': 'ssim', 'enabled': True, 'parameters': {'threshold': 0.90}, 'weight': 1.5},
                    {'name': 'strategy3', 'enabled': True, 'parameters': {'scene_threshold': 60.0, 'dct_threshold': 88.0, 'sequence_threshold': 98.0, 'num_samples': 20, 'warmup_seconds': 0.0, 'max_workers': 8}, 'weight': 3.0}
                ]
            },
            'fast': {
                'name': 'Rapide',
                'description': 'Seuils plus bas (75-85%) et moins de méthodes pour une exécution rapide.',
                'mode': 'filtering',
                'methods': [
                    {'name': 'color_histogram', 'enabled': True, 'parameters': {'threshold': 80.0}, 'weight': 1.0},
                    {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 70.0, 'num_coeffs': 10}, 'weight': 1.0},
                    {'name': 'strategy3', 'enabled': True, 'parameters': {'scene_threshold': 45.0, 'dct_threshold': 70.0, 'sequence_threshold': 90.0, 'num_samples': 8, 'warmup_seconds': 0.0, 'max_workers': 8}, 'weight': 1.5}
                ]
            },
            'dct_only': {
                'name': 'DCT Seulement',
                'description': 'Uniquement DCT coefficients. Parfait pour détecter les vidéos réencodées avec différents codecs/bitrates.',
                'mode': 'filtering',
                'methods': [
                    {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 70.0, 'num_coeffs': 20}, 'weight': 1.0}
                ]
            },
            'motion_only': {
                'name': 'Motion Seulement',
                'description': 'Uniquement motion analysis. Idéal pour détecter les vidéos recadrées, rotées ou avec bordures ajoutées.',
                'mode': 'filtering',
                'methods': [
                    {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 80.0, 'sample_interval': 2}, 'weight': 1.0}
                ]
            },
            'weighted_consensus': {
                'name': 'Consensus Pondéré',
                'description': 'Mode weighting: combine tous les tests avec poids. Score global = moyenne pondérée de toutes les méthodes.',
                'mode': 'weighting',
                'methods': [
                    {'name': 'color_histogram', 'enabled': True, 'parameters': {'threshold': 80.0}, 'weight': 1.0},
                    {'name': 'edge_pattern', 'enabled': True, 'parameters': {'threshold': 75.0}, 'weight': 0.8},
                    {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 80.0, 'sample_interval': 3}, 'weight': 1.5},
                    {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 70.0, 'num_coeffs': 15}, 'weight': 2.0},
                    {'name': 'ssim', 'enabled': True, 'parameters': {'threshold': 0.80}, 'weight': 1.2}
                ]
            },
            're_encoded_specialist': {
                'name': 'Spécialiste Réencodage',
                'description': 'Optimisé pour vidéos réencodées: DCT + Motion avec seuils adaptés. Ignore les différences de couleur/compression.',
                'mode': 'filtering',
                'methods': [
                    {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 68.0, 'num_coeffs': 20}, 'weight': 2.0},
                    {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 75.0, 'sample_interval': 2}, 'weight': 1.5},
                    {'name': 'strategy3', 'enabled': True, 'parameters': {'scene_threshold': 40.0, 'dct_threshold': 68.0, 'sequence_threshold': 88.0, 'num_samples': 12, 'warmup_seconds': 0.0, 'max_workers': 8}, 'weight': 2.5}
                ]
            },
            'ultra_permissive': {
                'name': 'Ultra Permissif',
                'description': 'Seuils très bas (60-70%) pour maximiser le rappel. Risque de faux positifs mais trouve TOUS les doublons potentiels.',
                'mode': 'weighting',
                'methods': [
                    {'name': 'color_histogram', 'enabled': True, 'parameters': {'threshold': 65.0}, 'weight': 1.0},
                    {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 70.0, 'sample_interval': 4}, 'weight': 1.0},
                    {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 60.0, 'num_coeffs': 12}, 'weight': 1.0}
                ]
            },
            'hybrid_conservative': {
                'name': 'Hybride Conservateur',
                'description': 'Mode hybrid: moyenne pondérée + seuils individuels. Seuils modérés (80-85%) pour bon équilibre.',
                'mode': 'hybrid',
                'methods': [
                    {'name': 'color_histogram', 'enabled': True, 'parameters': {'threshold': 82.0}, 'weight': 1.0},
                    {'name': 'motion_analysis', 'enabled': True, 'parameters': {'correlation_threshold': 82.0, 'sample_interval': 3}, 'weight': 1.2},
                    {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 72.0, 'num_coeffs': 15}, 'weight': 1.8},
                    {'name': 'strategy3', 'enabled': True, 'parameters': {'scene_threshold': 48.0, 'dct_threshold': 75.0, 'sequence_threshold': 92.0, 'num_samples': 12, 'warmup_seconds': 0.0, 'max_workers': 8}, 'weight': 2.0}
                ]
            }
        }

        def update_protocol_description():
            """Update protocol description based on selection."""
            protocol_id = protocol_combo.currentData()
            if protocol_id == 'custom':
                protocol_desc.setText("💡 Configuration personnalisée : modifiez les paramètres dans Pipeline JSON")
            elif protocol_id in TEST_PROTOCOLS:
                info = TEST_PROTOCOLS[protocol_id]
                protocol_desc.setText(f"📝 {info['description']}\n\n🔧 Mode: {info['mode']}\n📊 Méthodes: {len(info['methods'])}")

        protocol_combo.currentIndexChanged.connect(update_protocol_description)
        update_protocol_description()  # Initial update

        # Save protocol button
        save_protocol_layout = QHBoxLayout()
        save_protocol_btn = QPushButton("💾 Exporter le protocole en JSON")
        save_protocol_btn.setMaximumHeight(30)
        save_protocol_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)

        def save_protocol_to_file():
            """Save selected protocol to JSON file."""
            protocol_id = protocol_combo.currentData()
            if protocol_id == 'custom':
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(None, "Info", "Sélectionnez d'abord un protocole prédéfini à exporter")
                return

            if protocol_id not in TEST_PROTOCOLS:
                return

            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "Sauvegarder le protocole",
                f"protocol_{protocol_id}.json",
                "JSON Files (*.json)"
            )

            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(TEST_PROTOCOLS[protocol_id], f, indent=2, ensure_ascii=False)
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(None, "Succès", f"Protocole exporté:\n{file_path}")
                except Exception as e:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.critical(None, "Erreur", f"Erreur d'export: {e}")

        save_protocol_btn.clicked.connect(save_protocol_to_file)
        save_protocol_layout.addWidget(save_protocol_btn)
        protocols_layout.addLayout(save_protocol_layout)

        layout.addWidget(protocols_group)

        # Store references for later access
        tab.files_list_display = files_list_display
        tab.file_count_label = file_count_label
        tab.update_file_list_display = update_file_list_display
        tab.protocol_combo = protocol_combo
        tab.TEST_PROTOCOLS = TEST_PROTOCOLS

        # Benchmark/Debug runner (UI)
        bench_group = QGroupBox("🧪 Benchmarks pipeline")
        bench_layout = QVBoxLayout(bench_group)
        bench_layout.setSpacing(8)

        # Info label about optimization strategy
        info_label = QLabel(
            "ℹ️ Pipeline par défaut optimisé pour ZÉRO FAUX POSITIF\n"
            "Seuils stricts (92-97%) : préfère manquer des doublons plutôt que créer de fausses alarmes"
        )
        info_label.setStyleSheet("""
            QLabel {
                background-color: #E7F3FF;
                border: 1px solid #2196F3;
                border-radius: 4px;
                padding: 8px;
                color: #1565C0;
                font-size: 10px;
            }
        """)
        info_label.setWordWrap(True)
        bench_layout.addWidget(info_label)

        # File pickers
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Pairs JSON:"))
        pairs_edit = QLineEdit()
        pairs_btn = QPushButton("…")

        def pick_pairs():
            path, _ = QFileDialog.getOpenFileName(None, "Choisir pairs.json", "", "JSON (*.json)")
            if path:
                pairs_edit.setText(path)
        pairs_btn.clicked.connect(pick_pairs)

        file_layout.addWidget(pairs_edit)
        file_layout.addWidget(pairs_btn)

        file2_layout = QHBoxLayout()
        file2_layout.addWidget(QLabel("Pipeline JSON (optionnel):"))
        pipeline_edit = QLineEdit()
        pipeline_btn = QPushButton("…")

        def pick_pipeline():
            path, _ = QFileDialog.getOpenFileName(None, "Choisir pipeline.json", "", "JSON (*.json)")
            if path:
                pipeline_edit.setText(path)
        pipeline_btn.clicked.connect(pick_pipeline)

        file2_layout.addWidget(pipeline_edit)
        file2_layout.addWidget(pipeline_btn)

        bench_layout.addLayout(file_layout)
        bench_layout.addLayout(file2_layout)

        # Use main file list option
        use_main_files_check = QCheckBox("📋 Utiliser les fichiers de la liste principale")
        use_main_files_check.setToolTip(
            "Si coché, génère automatiquement des paires à partir des fichiers\n"
            "ajoutés dans l'onglet Fichiers (ignore le Pairs JSON)"
        )
        use_main_files_check.setStyleSheet("QCheckBox { font-weight: bold; color: #007BFF; }")

        def on_use_main_files_changed(state):
            """Enable/disable pairs JSON input based on checkbox state."""
            enabled = not use_main_files_check.isChecked()
            pairs_edit.setEnabled(enabled)
            pairs_btn.setEnabled(enabled)
            if not enabled:
                pairs_edit.setPlaceholderText("Fichiers de la liste principale seront utilisés")
            else:
                pairs_edit.setPlaceholderText("")

        use_main_files_check.stateChanged.connect(on_use_main_files_changed)
        bench_layout.addWidget(use_main_files_check)

        # Options
        options_layout = QHBoxLayout()
        debug_check = QCheckBox("Mode debug")
        nocache_check = QCheckBox("Sans cache")
        options_layout.addWidget(debug_check)
        options_layout.addWidget(nocache_check)
        options_layout.addStretch()
        bench_layout.addLayout(options_layout)

        # Label
        label_layout = QHBoxLayout()
        label_layout.addWidget(QLabel("Label:"))
        run_label_edit = QLineEdit()
        run_label_edit.setPlaceholderText("bench_v1")
        label_layout.addWidget(run_label_edit)
        bench_layout.addLayout(label_layout)

        # Output
        output = QTextEdit()
        output.setReadOnly(True)
        output.setStyleSheet("QTextEdit { background:#F8F9FA; }")
        bench_layout.addWidget(output)

        # Run button
        run_btn = QPushButton("Lancer benchmark")
        bench_layout.addWidget(run_btn)

        def append(msg: str):
            output.append(msg)
            output.ensureCursorVisible()

        def run_benchmark_ui():
            pipeline_path = pipeline_edit.text().strip()
            run_label = run_label_edit.text().strip() or "benchmark"
            debug_flag = debug_check.isChecked()
            use_cache = not nocache_check.isChecked()
            use_main_files = use_main_files_check.isChecked()

            # Get pairs from either main file list or JSON file
            pairs = []
            if use_main_files:
                # Generate pairs from main file list
                if not file_list_widget:
                    append("❌ Liste de fichiers principale non disponible")
                    return

                files = file_list_widget.get_files()
                if len(files) < 2:
                    append("❌ Au moins 2 fichiers requis dans la liste principale")
                    return

                append(f"📋 Génération de paires depuis {len(files)} fichiers...")

                # Generate all possible pairs (for exhaustive testing)
                # User should mark expected results manually or provide them
                for i, file1 in enumerate(files):
                    for file2 in files[i+1:]:
                        pairs.append({
                            'short': file1,
                            'long': file2,
                            'expected': 'unknown',  # User must verify manually
                            'start': 0.0,
                            'duration': None,  # Will be auto-detected
                            'sequence_score': 100.0
                        })

                append(f"✓ {len(pairs)} paires générées")
            else:
                # Load from JSON file
                pairs_path = pairs_edit.text().strip()
                if not pairs_path or not os.path.exists(pairs_path):
                    append("❌ Pairs JSON invalide")
                    return

                try:
                    with open(pairs_path, 'r', encoding='utf-8') as f:
                        pairs = json.load(f)
                except Exception as e:
                    append(f"❌ Erreur lecture pairs: {e}")
                    return

            try:
                db = DatabaseManager()
            except Exception as e:
                append(f"❌ Erreur connexion BDD: {e}")
                return

            # Construire pipeline
            if pipeline_path and os.path.exists(pipeline_path):
                try:
                    with open(pipeline_path, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)

                    # Validate mode
                    mode = cfg.get('mode', 'filtering')
                    if mode not in ['filtering', 'weighting', 'hybrid']:
                        append(f"⚠️ Mode invalide '{mode}', utilisation de 'filtering'")
                        mode = 'filtering'

                    pipeline = VerificationPipeline(
                        db_manager=db,
                        max_workers=8,
                        enable_caching=use_cache,
                        mode=mode
                    )

                    # Load and validate methods
                    methods_config = cfg.get('methods', [])
                    if methods_config:
                        pipeline.load_config(methods_config)
                        # Verify loaded methods
                        loaded_count = len(pipeline.get_config())
                        if loaded_count != len(methods_config):
                            append(f"⚠️ {len(methods_config) - loaded_count} méthode(s) invalide(s) ignorée(s)")
                except Exception as e:
                    append(f"❌ Erreur pipeline.json: {e}")
                    return
            else:
                # Use selected test protocol
                protocol_id = protocol_combo.currentData()

                if protocol_id == 'custom':
                    append("⚠️ Protocole personnalisé sélectionné mais aucun Pipeline JSON fourni")
                    append("ℹ️ Utilisation du protocole Anti-Faux Positifs par défaut")
                    protocol_id = 'anti_fp'

                if protocol_id in TEST_PROTOCOLS:
                    protocol_config = TEST_PROTOCOLS[protocol_id]
                    append(f"📋 Utilisation du protocole: {protocol_config['name']}")

                    pipeline = VerificationPipeline(
                        db_manager=db,
                        max_workers=8,
                        enable_caching=use_cache,
                        mode=protocol_config['mode']
                    )

                    # Add all methods from protocol
                    for method_config in protocol_config['methods']:
                        pipeline.add_method(
                            method_config['name'],
                            enabled=method_config.get('enabled', True),
                            parameters=method_config.get('parameters', {}),
                            weight=method_config.get('weight', 1.0)
                        )
                else:
                    # Fallback: Anti-FP protocol
                    append("⚠️ Protocole inconnu, utilisation de Anti-Faux Positifs")
                    pipeline = VerificationPipeline(db_manager=db, max_workers=8, enable_caching=use_cache, mode='filtering')
                    pipeline.add_method('color_histogram', enabled=True, parameters={'threshold': 92.0}, weight=1.5)
                    pipeline.add_method('motion_analysis', enabled=True, parameters={'correlation_threshold': 90.0, 'sample_interval': 3}, weight=1.5)
                    pipeline.add_method('dct_coefficients', enabled=True, parameters={'threshold': 85.0, 'num_coeffs': 15}, weight=2.0)
                    pipeline.add_method('strategy3', enabled=True, parameters={'scene_threshold': 60.0, 'dct_threshold': 85.0, 'sequence_threshold': 97.0, 'num_samples': 15, 'warmup_seconds': 0.0, 'max_workers': 8}, weight=3.0)

            metrics = {'tp': 0, 'fp': 0, 'tn': 0, 'fn': 0}
            human_rows = []

            def duration_from_video(path: str) -> float:
                if not os.path.exists(path):
                    return 0.0
                cap = cv2.VideoCapture(path)
                if not cap.isOpened():
                    return 0.0
                fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
                cap.release()
                if fps <= 0 or total <= 0:
                    return 0.0
                return float(total / fps)

            for item in pairs:
                short = item['short']
                long = item['long']

                # Validate video paths
                if not os.path.exists(short):
                    append(f"❌ Fichier court introuvable: {os.path.basename(short)}")
                    continue
                if not os.path.exists(long):
                    append(f"❌ Fichier long introuvable: {os.path.basename(long)}")
                    continue

                expected = item.get('expected', 'positive').lower()
                start = float(item.get('start', 0.0))
                duration = item.get('duration')
                if duration is None:
                    duration = float(item.get('estimated_duration', 0.0) or duration_from_video(short))
                sequence_score = float(item.get('sequence_score', 100.0))

                try:
                    db.upsert_debug_label(short, long, expected, notes=item.get('preference'))
                except Exception as label_err:
                    logger.debug(f"Impossible d'enregistrer le debug_label: {label_err}")

                t0 = time.time()
                try:
                    res = pipeline.verify(
                        short_video=short,
                        long_video=long,
                        start_time=start,
                        duration=duration,
                        sequence_score=sequence_score,
                        run_label=run_label,
                        debug_flag=debug_flag
                    )
                except Exception as e:
                    append(f"❌ Erreur run {short} vs {long}: {e}")
                    continue
                elapsed = time.time() - t0
                predicted = bool(res.get('accepted'))

                if expected == 'positive':
                    metrics['tp' if predicted else 'fn'] += 1
                else:
                    metrics['tn' if not predicted else 'fp'] += 1

                human_rows.append(
                    f"{os.path.basename(short)} → {os.path.basename(long)} | attendu={expected} | résultat={'ACCEPT' if predicted else 'REJECT'} | temps={elapsed:.2f}s"
                )

            # Affichage lisible
            append("\n=== Détails ===")
            for row in human_rows:
                append(row)

            total = sum(metrics.values()) or 1
            append("\n=== Synthèse ===")
            append(f"TP={metrics['tp']} | FP={metrics['fp']} | TN={metrics['tn']} | FN={metrics['fn']} | total={total}")
            precision = metrics['tp'] / max(1, (metrics['tp'] + metrics['fp']))
            recall = metrics['tp'] / max(1, (metrics['tp'] + metrics['fn']))
            append(f"Précision={precision*100:.1f}% | Rappel={recall*100:.1f}%")

        run_btn.clicked.connect(run_benchmark_ui)

        layout.addWidget(bench_group)

        # ═══════════════════════════════════════════════════════════
        # SYSTÈME DE BENCHMARK AVANCÉ
        # ═══════════════════════════════════════════════════════════
        if db_manager is not None:
            benchmark_tab_widget = BenchmarkTabWidget(db_manager)
            layout.addWidget(benchmark_tab_widget)
            tab.benchmark_tab_widget = benchmark_tab_widget

        layout.addStretch()

        # Store references for later access
        tab.hash_debugger_v2 = hash_debugger_v2
        tab.audio_debugger = audio_debugger
        tab.benchmark_pairs_edit = pairs_edit
        tab.benchmark_pipeline_edit = pipeline_edit
        tab.benchmark_run_label = run_label_edit
        tab.benchmark_debug_check = debug_check
        tab.benchmark_nocache_check = nocache_check
        tab.benchmark_output = output

        # Set scroll area content and add to tab
        scroll_area.setWidget(content_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)

        return tab

    @staticmethod
    def _create_action_buttons(callbacks: Dict[str, Callable]) -> QFrame:
        """
        Create the action buttons group.

        Args:
            callbacks: Dictionary of callbacks.

        Returns:
            Tuple of (QFrame, dict of button widgets).
        """
        group = QFrame()
        group.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 1px solid #DEE2E6;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Main action buttons
        main_layout = QHBoxLayout()

        analyze_btn = QPushButton("🔍 DÉMARRER")
        analyze_btn.setMinimumHeight(40)
        analyze_btn.setStyleSheet(UIPanels._get_button_style("#28A745", "#218838", font_size=13))
        analyze_btn.clicked.connect(callbacks['analyze'])
        analyze_btn.setToolTip("Démarrer l'analyse complète avec audio-first workflow")

        scene_detection_btn = QPushButton("🎬 SCÈNES")
        scene_detection_btn.setMinimumHeight(40)
        scene_detection_btn.setStyleSheet(UIPanels._get_button_style("#1565C0", "#0D47A1", font_size=13))
        scene_detection_btn.clicked.connect(callbacks.get('start_scene_detection', lambda: None))
        scene_detection_btn.setToolTip(
            "Détection de scènes (mode direct)\n"
            "• Empreintes audio (rapide)\n"
            "• Vérification DCT + Scene Cuts"
        )

        stop_btn = QPushButton("⏹️ ARRÊTER")
        stop_btn.setMinimumHeight(40)
        stop_btn.setStyleSheet(UIPanels._get_button_style("#DC3545", "#C82333", font_size=13))
        stop_btn.clicked.connect(callbacks['stop'])

        main_layout.addWidget(analyze_btn)
        main_layout.addWidget(scene_detection_btn)
        main_layout.addWidget(stop_btn)
        layout.addLayout(main_layout)

        # Secondary buttons
        secondary_layout = QHBoxLayout()

        stats_btn = QPushButton("📊 Statistiques")
        stats_btn.setMaximumHeight(30)
        stats_btn.setStyleSheet(UIPanels._get_button_style("#17A2B8", "#138496", font_size=11, padding="5px 8px"))
        stats_btn.clicked.connect(callbacks['show_stats'])

        pending_btn = QPushButton("📋 Doublons")
        pending_btn.setMaximumHeight(30)
        pending_btn.setStyleSheet(UIPanels._get_button_style("#FD7E14", "#E55A00", font_size=11, padding="5px 8px"))
        pending_btn.clicked.connect(callbacks['show_pending'])

        close_btn = QPushButton("🚪 Fermer")
        close_btn.setMaximumHeight(30)
        close_btn.setStyleSheet(UIPanels._get_button_style("#6C757D", "#545B62", font_size=11, padding="5px 8px"))
        close_btn.clicked.connect(callbacks['close'])

        secondary_layout.addWidget(stats_btn)
        secondary_layout.addWidget(pending_btn)
        secondary_layout.addWidget(close_btn)
        layout.addLayout(secondary_layout)

        # Store button references
        group.analyze_btn = analyze_btn
        group.scene_detection_btn = scene_detection_btn
        group.stop_btn = stop_btn
        group.stats_btn = stats_btn
        group.pending_btn = pending_btn
        group.close_btn = close_btn

        return group

    @staticmethod
    def create_right_panel() -> tuple:
        """
        Create the right progress panel.

        Returns:
            Tuple of (QFrame, dict of widgets).
        """
        theme = get_current_theme()
        colors = theme.get_colors()
        spacing = theme.get_spacing()

        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['bg_card']};
                border: 1px solid {colors['border']};
                border-radius: {spacing['radius']}px;
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(spacing['padding'], spacing['padding'],
                                   spacing['padding'], spacing['padding'])
        layout.setSpacing(spacing['gap'])

        # Status indicator
        status_indicator = StatusIndicator()
        layout.addWidget(status_indicator)

        # Stats counter (duplicates, subsequences, etc.)
        from .widgets.progress_widgets import StatsCounter
        stats_counter = StatsCounter()
        layout.addWidget(stats_counter)

        # Progress widgets (hidden by default, shown based on workflow)
        audio_progress = ModernProgressWidget("🎵 Audio fingerprinting")
        audio_progress.hide()
        layout.addWidget(audio_progress)

        file_progress = ModernProgressWidget("📊 File hashing")
        file_progress.hide()
        layout.addWidget(file_progress)

        duplicate_progress = ModernProgressWidget("🔍 Duplicate detection")
        duplicate_progress.hide()
        layout.addWidget(duplicate_progress)

        verification_progress = ModernProgressWidget("🎯 Subsequence verification")
        verification_progress.hide()
        layout.addWidget(verification_progress)

        # Live benchmark comparison widget (shown during benchmark execution)
        from PyQt6.QtWidgets import QTableWidget, QGroupBox
        benchmark_live_group = QGroupBox("⚡ Comparaison en Temps Réel - Benchmarks")
        benchmark_live_layout = QVBoxLayout(benchmark_live_group)

        benchmark_live_table = QTableWidget()
        benchmark_live_table.setMinimumHeight(250)
        benchmark_live_table.setStyleSheet("""
            QTableWidget {
                border: 2px solid #2196F3;
                border-radius: 5px;
                background-color: #f0f8ff;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        benchmark_live_layout.addWidget(benchmark_live_table)

        benchmark_live_group.setVisible(False)  # Hidden until benchmark starts
        layout.addWidget(benchmark_live_group)

        # Benchmark results widget (hidden by default)
        benchmark_results_group = QGroupBox("📊 Résultats Comparatifs - Benchmark")
        benchmark_results_layout = QVBoxLayout(benchmark_results_group)

        benchmark_results_table = QTableWidget()
        benchmark_results_table.setMinimumHeight(250)
        benchmark_results_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        benchmark_results_layout.addWidget(benchmark_results_table)

        benchmark_results_group.setVisible(False)  # Hidden until benchmark completes
        layout.addWidget(benchmark_results_group)

        # Add stretch
        layout.addStretch(2)

        widgets = {
            'status_indicator': status_indicator,
            'stats_counter': stats_counter,
            'audio_progress': audio_progress,
            'file_progress': file_progress,
            'duplicate_progress': duplicate_progress,
            'verification_progress': verification_progress,
            'benchmark_live_group': benchmark_live_group,
            'benchmark_live_table': benchmark_live_table,
            'benchmark_results_group': benchmark_results_group,
            'benchmark_results_table': benchmark_results_table
        }

        return panel, widgets

    @staticmethod
    def _get_button_style(
        bg_color: str,
        hover_color: str,
        font_size: int = 11,
        padding: str = None
    ) -> str:
        """
        Generate button stylesheet.

        Args:
            bg_color: Background color.
            hover_color: Hover state color.
            font_size: Font size in pixels.
            padding: Optional padding value.

        Returns:
            CSS stylesheet string.
        """
        padding_str = f"padding: {padding};" if padding else ""
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: {font_size}px;
                {padding_str}
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: #CCCCCC;
            }}
        """

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when widget is closed.

        Ensures proper cleanup of resources and signals.
        """
        # All signals are internal and auto-cleaned by Qt
        # Added for consistency with other widgets
        super().closeEvent(event)
