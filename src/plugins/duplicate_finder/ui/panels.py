"""
UI panel creation utilities for the duplicate finder.

This module provides factory methods for creating UI panels and their components,
separating UI construction from business logic.
"""
from typing import Callable, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox,
    QGridLayout, QDoubleSpinBox, QSpinBox, QFrame, QLabel, QTabWidget,
    QCheckBox, QComboBox, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..progress_widgets import ModernProgressWidget, FileListWidget, StatusIndicator, HashDebuggerV2
from ..themes import get_current_theme
from ..i18n import get_translator


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
        callbacks: Dict[str, Callable]
    ) -> QFrame:
        """
        Create the left configuration panel.

        Args:
            file_list_widget: FileListWidget instance.
            callbacks: Dictionary of callback functions with keys:
                - 'add_files', 'add_folder', 'clear_list', 'clear_cache'
                - 'apply_preset', 'analyze', 'stop'
                - 'show_stats', 'show_pending', 'close'

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
        config_tabs = UIPanels._create_config_tabs(file_list_widget, callbacks)
        layout.addWidget(config_tabs)

        # Action buttons
        action_buttons = UIPanels._create_action_buttons(callbacks)
        layout.addWidget(action_buttons)

        return panel

    @staticmethod
    def _create_config_tabs(
        file_list_widget: FileListWidget,
        callbacks: Dict[str, Callable]
    ) -> QTabWidget:
        """
        Create the configuration tabs widget.

        Args:
            file_list_widget: FileListWidget instance.
            callbacks: Dictionary of callbacks.

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

        # Files tab
        files_tab = UIPanels._create_files_tab(file_list_widget, callbacks)
        tabs.addTab(files_tab, "📁 Fichiers")

        # Parameters tab
        params_tab = UIPanels._create_parameters_tab(callbacks)
        tabs.addTab(params_tab, "⚙️ Paramètres")

        # Debug tab
        debug_tab = UIPanels._create_debug_tab()
        tabs.addTab(debug_tab, "🔬 Débogage")

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
            "Détection avancée de doublons par analyse en 3 niveaux :\n"
            "• Audio + Visual + Confirmation\n\n"
            "Idéal pour détecter scènes extraites et variantes"
        )
        scene_detection_btn.clicked.connect(callbacks.get('run_advanced_mode', lambda: None))
        buttons_layout.addWidget(scene_detection_btn, 3, 0, 1, 2)  # Span both columns

        layout.addLayout(buttons_layout)
        layout.addWidget(file_list_widget)

        return tab

    @staticmethod
    def _create_parameters_tab(callbacks: Dict[str, Callable]) -> QWidget:
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

        Returns:
            Configured QWidget for parameters tab.
        """
        # Get translator instance
        t = get_translator()

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
        layout.setSpacing(15)

        # ═══════════════════════════════════════════════════════════
        # LANGUAGE SELECTOR
        # ═══════════════════════════════════════════════════════════
        language_group = QGroupBox("🌍 Language / Langue")
        language_layout = QHBoxLayout(language_group)
        language_layout.setSpacing(10)

        language_combo = QComboBox()
        available_languages = t.get_available_languages()
        for lang_code, lang_name in available_languages.items():
            language_combo.addItem(lang_name, lang_code)

        # Set current language as selected
        current_lang = t.get_language()
        for i in range(language_combo.count()):
            if language_combo.itemData(i) == current_lang:
                language_combo.setCurrentIndex(i)
                break

        # Connect language change
        def on_language_change(index):
            selected_lang = language_combo.itemData(index)
            t.set_language(selected_lang)
            # Trigger a UI refresh if callback exists
            if 'language_changed' in callbacks:
                callbacks['language_changed'](selected_lang)

        language_combo.currentIndexChanged.connect(on_language_change)
        language_layout.addWidget(QLabel("Select language / Sélectionner la langue :"))
        language_layout.addWidget(language_combo)
        language_layout.addStretch()

        # Store reference for later access
        tab.language_combo = language_combo

        layout.addWidget(language_group)

        # ═══════════════════════════════════════════════════════════
        # PRESETS (En haut pour accès facile)
        # ═══════════════════════════════════════════════════════════
        presets_group = QGroupBox(f"🚀 {t.tr('ui.presets.title')}")
        presets_layout = QGridLayout(presets_group)
        presets_layout.setSpacing(10)

        speed_btn = QPushButton(f"⚡ {t.tr('ui.presets.speed')}")
        speed_btn.setMinimumHeight(35)
        speed_btn.setStyleSheet(UIPanels._get_button_style("#DC3545", "#A71E2A"))
        speed_btn.clicked.connect(lambda: callbacks['apply_preset']("maximum_speed"))
        speed_btn.setToolTip(t.tr('ui.presets.speed_tooltip'))

        balanced_btn = QPushButton(f"⚖️ {t.tr('ui.presets.balanced')}")
        balanced_btn.setMinimumHeight(35)
        balanced_btn.setStyleSheet(UIPanels._get_button_style("#007BFF", "#0056B3"))
        balanced_btn.clicked.connect(lambda: callbacks['apply_preset']("balanced"))
        balanced_btn.setToolTip(t.tr('ui.presets.balanced_tooltip'))

        quality_btn = QPushButton(f"🎯 {t.tr('ui.presets.quality')}")
        quality_btn.setMinimumHeight(35)
        quality_btn.setStyleSheet(UIPanels._get_button_style("#28A745", "#1E7E34"))
        quality_btn.clicked.connect(lambda: callbacks['apply_preset']("maximum_quality"))
        quality_btn.setToolTip(t.tr('ui.presets.quality_tooltip'))

        presets_layout.addWidget(speed_btn, 0, 0)
        presets_layout.addWidget(balanced_btn, 0, 1)
        presets_layout.addWidget(quality_btn, 1, 0, 1, 2)

        layout.addWidget(presets_group)

        # ═══════════════════════════════════════════════════════════
        # EMPREINTE AUDIO (Filtre principal)
        # ═══════════════════════════════════════════════════════════
        audio_group = QGroupBox(f"🎵 {t.tr('ui.audio.title')}")
        audio_layout = QGridLayout(audio_group)
        audio_layout.setSpacing(10)

        # Seuil de similarité audio (paramètre principal)
        audio_layout.addWidget(QLabel(t.tr('ui.audio.threshold')), 0, 0)
        audio_threshold_spin = QDoubleSpinBox()
        audio_threshold_spin.setRange(50.0, 95.0)
        audio_threshold_spin.setValue(70.0)
        audio_threshold_spin.setSuffix(t.tr('ui.common.percent'))
        audio_threshold_spin.setDecimals(1)
        audio_threshold_spin.setToolTip(t.tr('ui.audio.threshold_tooltip'))
        audio_layout.addWidget(audio_threshold_spin, 0, 1)

        # Mode de précision
        audio_layout.addWidget(QLabel(t.tr('ui.audio.precision')), 1, 0)
        audio_precision_combo = QComboBox()
        audio_precision_combo.addItem(f"⚡ {t.tr('ui.audio.precision_fast')}", "fast")
        audio_precision_combo.addItem(f"⚖️ {t.tr('ui.audio.precision_balanced')}", "balanced")
        audio_precision_combo.addItem(f"🎯 {t.tr('ui.audio.precision_maximum')}", "maximum")
        audio_precision_combo.setCurrentIndex(0)  # Par défaut Rapide
        audio_precision_combo.setToolTip(t.tr('ui.audio.precision_tooltip'))
        audio_layout.addWidget(audio_precision_combo, 1, 1)

        # Workers audio
        audio_layout.addWidget(QLabel(t.tr('ui.audio.workers')), 2, 0)
        audio_workers_spin = QSpinBox()
        audio_workers_spin.setRange(1, 16)
        audio_workers_spin.setValue(4)
        audio_workers_spin.setToolTip(t.tr('ui.audio.workers_tooltip'))
        audio_layout.addWidget(audio_workers_spin, 2, 1)

        # Taille du cache audio
        audio_layout.addWidget(QLabel(t.tr('ui.audio.cache_size')), 3, 0)
        audio_cache_size_spin = QSpinBox()
        audio_cache_size_spin.setRange(100, 5000)
        audio_cache_size_spin.setValue(1000)
        audio_cache_size_spin.setSuffix(t.tr('ui.audio.cache_size_suffix'))
        audio_cache_size_spin.setToolTip(t.tr('ui.audio.cache_size_tooltip'))
        audio_layout.addWidget(audio_cache_size_spin, 3, 1)

        # Activer le fallback pour vidéos sans audio
        enable_no_audio_fallback = QCheckBox(t.tr('ui.audio.fallback'))
        enable_no_audio_fallback.setChecked(True)
        enable_no_audio_fallback.setToolTip(t.tr('ui.audio.fallback_tooltip'))
        audio_layout.addWidget(enable_no_audio_fallback, 4, 0, 1, 2)

        # Label d'information
        audio_info = QLabel(f"ℹ️ {t.tr('ui.audio.info')}")
        audio_info.setStyleSheet("QLabel { color: #6C757D; font-size: 9px; padding: 5px; }")
        audio_info.setWordWrap(True)
        audio_layout.addWidget(audio_info, 5, 0, 1, 2)

        layout.addWidget(audio_group)

        # ═══════════════════════════════════════════════════════════
        # LSH (Hachage sensible à la localité)
        # ═══════════════════════════════════════════════════════════
        lsh_group = QGroupBox(f"🔍 {t.tr('ui.lsh.title')}")
        lsh_layout = QGridLayout(lsh_group)
        lsh_layout.setSpacing(10)

        # Activer LSH
        enable_lsh_check = QCheckBox(t.tr('ui.lsh.enable'))
        enable_lsh_check.setChecked(True)
        enable_lsh_check.setStyleSheet("QCheckBox { font-weight: bold; }")
        enable_lsh_check.setToolTip(t.tr('ui.lsh.enable_tooltip'))
        lsh_layout.addWidget(enable_lsh_check, 0, 0, 1, 2)

        # Bandes LSH
        lsh_layout.addWidget(QLabel(t.tr('ui.lsh.bands')), 1, 0)
        lsh_bands_spin = QSpinBox()
        lsh_bands_spin.setRange(10, 50)
        lsh_bands_spin.setValue(20)
        lsh_bands_spin.setToolTip(t.tr('ui.lsh.bands_tooltip'))
        lsh_layout.addWidget(lsh_bands_spin, 1, 1)

        # Lignes par bande
        lsh_layout.addWidget(QLabel(t.tr('ui.lsh.rows')), 2, 0)
        lsh_rows_spin = QSpinBox()
        lsh_rows_spin.setRange(3, 10)
        lsh_rows_spin.setValue(5)
        lsh_rows_spin.setToolTip(t.tr('ui.lsh.rows_tooltip'))
        lsh_layout.addWidget(lsh_rows_spin, 2, 1)

        # LSH pour vidéos sans audio
        enable_lsh_no_audio = QCheckBox(t.tr('ui.lsh.no_audio'))
        enable_lsh_no_audio.setChecked(True)
        enable_lsh_no_audio.setToolTip(t.tr('ui.lsh.no_audio_tooltip'))
        lsh_layout.addWidget(enable_lsh_no_audio, 3, 0, 1, 2)

        # Label d'information
        lsh_info = QLabel(f"ℹ️ {t.tr('ui.lsh.info')}")
        lsh_info.setStyleSheet("QLabel { color: #6C757D; font-size: 9px; padding: 5px; }")
        lsh_info.setWordWrap(True)
        lsh_layout.addWidget(lsh_info, 4, 0, 1, 2)

        layout.addWidget(lsh_group)

        # ═══════════════════════════════════════════════════════════
        # COMPARAISON MULTI-RÉSOLUTION
        # ═══════════════════════════════════════════════════════════
        mr_group = QGroupBox(f"📊 {t.tr('ui.multi_resolution.title')}")
        mr_layout = QGridLayout(mr_group)
        mr_layout.setSpacing(10)

        # Activer multi-résolution
        enable_mr_check = QCheckBox(t.tr('ui.multi_resolution.enable'))
        enable_mr_check.setChecked(True)
        enable_mr_check.setStyleSheet("QCheckBox { font-weight: bold; }")
        enable_mr_check.setToolTip(t.tr('ui.multi_resolution.enable_tooltip'))
        mr_layout.addWidget(enable_mr_check, 0, 0, 1, 2)

        # Paramètres grossiers
        mr_layout.addWidget(QLabel(t.tr('ui.multi_resolution.coarse_duration')), 1, 0)
        mr_coarse_duration_spin = QSpinBox()
        mr_coarse_duration_spin.setRange(10, 60)
        mr_coarse_duration_spin.setValue(30)
        mr_coarse_duration_spin.setSuffix(t.tr('ui.common.sec'))
        mr_coarse_duration_spin.setToolTip(t.tr('ui.multi_resolution.coarse_duration_tooltip'))
        mr_layout.addWidget(mr_coarse_duration_spin, 1, 1)

        mr_layout.addWidget(QLabel(t.tr('ui.multi_resolution.coarse_threshold')), 2, 0)
        mr_coarse_threshold_spin = QDoubleSpinBox()
        mr_coarse_threshold_spin.setRange(50.0, 80.0)
        mr_coarse_threshold_spin.setValue(60.0)
        mr_coarse_threshold_spin.setSuffix(t.tr('ui.common.percent'))
        mr_coarse_threshold_spin.setDecimals(1)
        mr_coarse_threshold_spin.setToolTip(t.tr('ui.multi_resolution.coarse_threshold_tooltip'))
        mr_layout.addWidget(mr_coarse_threshold_spin, 2, 1)

        # Paramètres moyens
        mr_layout.addWidget(QLabel(t.tr('ui.multi_resolution.medium_duration')), 3, 0)
        mr_medium_duration_spin = QSpinBox()
        mr_medium_duration_spin.setRange(60, 300)
        mr_medium_duration_spin.setValue(120)
        mr_medium_duration_spin.setSuffix(t.tr('ui.common.sec'))
        mr_medium_duration_spin.setToolTip(t.tr('ui.multi_resolution.medium_duration_tooltip'))
        mr_layout.addWidget(mr_medium_duration_spin, 3, 1)

        mr_layout.addWidget(QLabel(t.tr('ui.multi_resolution.medium_threshold')), 4, 0)
        mr_medium_threshold_spin = QDoubleSpinBox()
        mr_medium_threshold_spin.setRange(55.0, 85.0)
        mr_medium_threshold_spin.setValue(65.0)
        mr_medium_threshold_spin.setSuffix(t.tr('ui.common.percent'))
        mr_medium_threshold_spin.setDecimals(1)
        mr_medium_threshold_spin.setToolTip(t.tr('ui.multi_resolution.medium_threshold_tooltip'))
        mr_layout.addWidget(mr_medium_threshold_spin, 4, 1)

        # Label d'information
        mr_info = QLabel(f"ℹ️ {t.tr('ui.multi_resolution.info')}")
        mr_info.setStyleSheet("QLabel { color: #6C757D; font-size: 9px; padding: 5px; }")
        mr_info.setWordWrap(True)
        mr_layout.addWidget(mr_info, 5, 0, 1, 2)

        layout.addWidget(mr_group)

        # ═══════════════════════════════════════════════════════════
        # FILTRE MÉTADONNÉES (Optionnel)
        # ═══════════════════════════════════════════════════════════
        metadata_group = QGroupBox(f"📋 {t.tr('ui.metadata.title')}")
        metadata_layout = QGridLayout(metadata_group)
        metadata_layout.setSpacing(10)

        # Activer le filtre métadonnées
        enable_metadata_check = QCheckBox(t.tr('ui.metadata.enable'))
        enable_metadata_check.setChecked(False)  # Désactivé par défaut
        enable_metadata_check.setToolTip(t.tr('ui.metadata.enable_tooltip'))
        enable_metadata_check.setStyleSheet("QCheckBox { color: #DC3545; }")
        metadata_layout.addWidget(enable_metadata_check, 0, 0, 1, 2)

        # Tolérance de durée
        metadata_layout.addWidget(QLabel(t.tr('ui.metadata.duration_tolerance')), 1, 0)
        metadata_duration_tolerance_spin = QDoubleSpinBox()
        metadata_duration_tolerance_spin.setRange(0.01, 0.20)
        metadata_duration_tolerance_spin.setValue(0.05)
        metadata_duration_tolerance_spin.setSuffix(" (5%)")
        metadata_duration_tolerance_spin.setDecimals(2)
        metadata_duration_tolerance_spin.setToolTip(t.tr('ui.metadata.duration_tolerance_tooltip'))
        metadata_layout.addWidget(metadata_duration_tolerance_spin, 1, 1)

        # Ratio de taille minimum
        metadata_layout.addWidget(QLabel(t.tr('ui.metadata.size_ratio')), 2, 0)
        metadata_size_ratio_spin = QDoubleSpinBox()
        metadata_size_ratio_spin.setRange(0.50, 0.99)
        metadata_size_ratio_spin.setValue(0.90)
        metadata_size_ratio_spin.setSuffix(" (90%)")
        metadata_size_ratio_spin.setDecimals(2)
        metadata_size_ratio_spin.setToolTip(t.tr('ui.metadata.size_ratio_tooltip'))
        metadata_layout.addWidget(metadata_size_ratio_spin, 2, 1)

        # Label d'avertissement
        metadata_warning = QLabel(f"⚠️ {t.tr('ui.metadata.warning')}")
        metadata_warning.setStyleSheet("QLabel { color: #DC3545; font-size: 9px; padding: 5px; font-weight: bold; }")
        metadata_warning.setWordWrap(True)
        metadata_layout.addWidget(metadata_warning, 3, 0, 1, 2)

        layout.addWidget(metadata_group)

        # ═══════════════════════════════════════════════════════════
        # HACHAGE VIDÉO
        # ═══════════════════════════════════════════════════════════
        video_hash_group = QGroupBox(f"🎬 {t.tr('ui.video_hash.title')}")
        video_hash_layout = QGridLayout(video_hash_group)
        video_hash_layout.setSpacing(10)

        # Méthode de hash
        video_hash_layout.addWidget(QLabel(t.tr('ui.video_hash.method')), 0, 0)
        hash_method_combo = QComboBox()
        hash_method_combo.addItem(f"🎯 {t.tr('ui.video_hash.method_phash')}", "pHash")
        hash_method_combo.addItem(f"⚖️ {t.tr('ui.video_hash.method_dhash')}", "dHash")
        hash_method_combo.addItem(f"⚡ {t.tr('ui.video_hash.method_ahash')}", "aHash")
        hash_method_combo.setCurrentIndex(0)  # Par défaut pHash
        hash_method_combo.setToolTip(t.tr('ui.video_hash.method_tooltip'))
        video_hash_layout.addWidget(hash_method_combo, 0, 1)

        # Workers hash
        video_hash_layout.addWidget(QLabel(t.tr('ui.video_hash.workers')), 1, 0)
        hash_workers_spin = QSpinBox()
        hash_workers_spin.setRange(1, 16)
        hash_workers_spin.setValue(4)
        hash_workers_spin.setToolTip(t.tr('ui.video_hash.workers_tooltip'))
        video_hash_layout.addWidget(hash_workers_spin, 1, 1)

        # Timeout hash
        video_hash_layout.addWidget(QLabel(t.tr('ui.video_hash.timeout')), 2, 0)
        hash_timeout_spin = QSpinBox()
        hash_timeout_spin.setRange(30, 600)
        hash_timeout_spin.setValue(120)
        hash_timeout_spin.setSuffix(t.tr('ui.common.sec'))
        hash_timeout_spin.setToolTip(t.tr('ui.video_hash.timeout_tooltip'))
        video_hash_layout.addWidget(hash_timeout_spin, 2, 1)

        # Taille du cache vidéo
        video_hash_layout.addWidget(QLabel(t.tr('ui.video_hash.cache_size')), 3, 0)
        video_cache_size_spin = QSpinBox()
        video_cache_size_spin.setRange(500, 10000)
        video_cache_size_spin.setValue(2000)
        video_cache_size_spin.setSuffix(t.tr('ui.video_hash.cache_size_suffix'))
        video_cache_size_spin.setToolTip(t.tr('ui.video_hash.cache_size_tooltip'))
        video_hash_layout.addWidget(video_cache_size_spin, 3, 1)

        # Label d'information
        video_hash_info = QLabel(f"ℹ️ {t.tr('ui.video_hash.info')}")
        video_hash_info.setStyleSheet("QLabel { color: #6C757D; font-size: 9px; padding: 5px; }")
        video_hash_info.setWordWrap(True)
        video_hash_layout.addWidget(video_hash_info, 4, 0, 1, 2)

        layout.addWidget(video_hash_group)

        # ═══════════════════════════════════════════════════════════
        # COMPARAISON VIDÉO
        # ═══════════════════════════════════════════════════════════
        video_comp_group = QGroupBox(f"🔍 {t.tr('ui.video_comparison.title')}")
        video_comp_layout = QGridLayout(video_comp_group)
        video_comp_layout.setSpacing(10)

        # Seuil de similarité vidéo
        video_comp_layout.addWidget(QLabel(t.tr('ui.video_comparison.threshold')), 0, 0)
        video_threshold_spin = QDoubleSpinBox()
        video_threshold_spin.setRange(70.0, 99.0)
        video_threshold_spin.setValue(90.0)
        video_threshold_spin.setSuffix(t.tr('ui.common.percent'))
        video_threshold_spin.setDecimals(1)
        video_threshold_spin.setToolTip(t.tr('ui.video_comparison.threshold_tooltip'))
        video_comp_layout.addWidget(video_threshold_spin, 0, 1)

        # Activer la détection de flip
        enable_flip_detection = QCheckBox(t.tr('ui.video_comparison.flip_detection'))
        enable_flip_detection.setChecked(True)
        enable_flip_detection.setStyleSheet("QCheckBox { font-weight: bold; }")
        enable_flip_detection.setToolTip(t.tr('ui.video_comparison.flip_detection_tooltip'))
        video_comp_layout.addWidget(enable_flip_detection, 1, 0, 1, 2)

        # Workers de comparaison
        video_comp_layout.addWidget(QLabel(t.tr('ui.video_comparison.workers')), 2, 0)
        comparison_workers_spin = QSpinBox()
        comparison_workers_spin.setRange(1, 16)
        comparison_workers_spin.setValue(8)
        comparison_workers_spin.setToolTip(t.tr('ui.video_comparison.workers_tooltip'))
        video_comp_layout.addWidget(comparison_workers_spin, 2, 1)

        # Taille de batch
        video_comp_layout.addWidget(QLabel(t.tr('ui.video_comparison.batch_size')), 3, 0)
        batch_size_spin = QSpinBox()
        batch_size_spin.setRange(10, 500)
        batch_size_spin.setValue(100)
        batch_size_spin.setToolTip(t.tr('ui.video_comparison.batch_size_tooltip'))
        video_comp_layout.addWidget(batch_size_spin, 3, 1)

        # Timeout de comparaison
        video_comp_layout.addWidget(QLabel(t.tr('ui.video_comparison.timeout')), 4, 0)
        comparison_timeout_spin = QSpinBox()
        comparison_timeout_spin.setRange(5, 120)
        comparison_timeout_spin.setValue(30)
        comparison_timeout_spin.setSuffix(t.tr('ui.common.sec'))
        comparison_timeout_spin.setToolTip(t.tr('ui.video_comparison.timeout_tooltip'))
        video_comp_layout.addWidget(comparison_timeout_spin, 4, 1)

        # Taille du cache de comparaison
        video_comp_layout.addWidget(QLabel(t.tr('ui.video_comparison.cache_size')), 5, 0)
        comparison_cache_size_spin = QSpinBox()
        comparison_cache_size_spin.setRange(1000, 50000)
        comparison_cache_size_spin.setValue(10000)
        comparison_cache_size_spin.setSuffix(t.tr('ui.video_comparison.cache_size_suffix'))
        comparison_cache_size_spin.setToolTip(t.tr('ui.video_comparison.cache_size_tooltip'))
        video_comp_layout.addWidget(comparison_cache_size_spin, 5, 1)

        layout.addWidget(video_comp_group)

        # ═══════════════════════════════════════════════════════════
        # DÉTECTION DE SCÈNES
        # ═══════════════════════════════════════════════════════════
        advanced_mode_group = QGroupBox("🎬 Détection de Scènes")
        advanced_mode_layout = QGridLayout(advanced_mode_group)
        advanced_mode_layout.setSpacing(10)

        # Description
        advanced_desc = QLabel(
            "Analyse multi-niveaux pour détecter scènes extraites :\n"
            "• Audio court (filtrage rapide)\n"
            "• Audio long (analyse approfondie)\n"
            "• Visuel (confirmation)\n\n"
            "Plus lent mais très précis"
        )
        advanced_desc.setWordWrap(True)
        advanced_desc.setStyleSheet("QLabel { color: #6C757D; font-size: 10px; }")
        advanced_mode_layout.addWidget(advanced_desc, 0, 0, 1, 2)

        # Activer la détection de scènes
        enable_advanced_mode = QCheckBox("Activer la détection de scènes")
        enable_advanced_mode.setChecked(False)
        enable_advanced_mode.setStyleSheet("QCheckBox { font-weight: bold; color: #1565C0; }")
        enable_advanced_mode.setToolTip(
            "Active l'analyse multi-niveaux pour détecter scènes extraites.\n"
            "Idéal pour gros corpus ou vidéos avec variantes."
        )
        advanced_mode_layout.addWidget(enable_advanced_mode, 1, 0, 1, 2)

        # Niveau 1 : Seuil audio lâche
        advanced_mode_layout.addWidget(QLabel("📊 Niveau 1 - Seuil lâche :"), 2, 0)
        level1_threshold_spin = QDoubleSpinBox()
        level1_threshold_spin.setRange(0.5, 0.9)
        level1_threshold_spin.setValue(0.7)
        level1_threshold_spin.setSingleStep(0.05)
        level1_threshold_spin.setDecimals(2)
        level1_threshold_spin.setToolTip("Similarité minimale pour le filtrage initial (0.7 = 70%)")
        advanced_mode_layout.addWidget(level1_threshold_spin, 2, 1)

        # Niveau 2 : Durée période longue
        advanced_mode_layout.addWidget(QLabel("⏱️ Niveau 2 - Période longue :"), 3, 0)
        level2_duration_spin = QSpinBox()
        level2_duration_spin.setRange(30, 300)
        level2_duration_spin.setValue(120)
        level2_duration_spin.setSuffix(" sec")
        level2_duration_spin.setToolTip("Durée de la fenêtre d'analyse approfondie (120s recommandé)")
        advanced_mode_layout.addWidget(level2_duration_spin, 3, 1)

        # Niveau 2 : Seuil raffiné
        advanced_mode_layout.addWidget(QLabel("🎯 Niveau 2 - Seuil raffiné :"), 4, 0)
        level2_threshold_spin = QDoubleSpinBox()
        level2_threshold_spin.setRange(0.6, 0.95)
        level2_threshold_spin.setValue(0.8)
        level2_threshold_spin.setSingleStep(0.05)
        level2_threshold_spin.setDecimals(2)
        level2_threshold_spin.setToolTip("Similarité minimale sur période longue (0.8 = 80%)")
        advanced_mode_layout.addWidget(level2_threshold_spin, 4, 1)

        # Niveau 3 : Seuil pHash
        advanced_mode_layout.addWidget(QLabel("👁️ Niveau 3 - Seuil pHash :"), 5, 0)
        level3_phash_threshold_spin = QSpinBox()
        level3_phash_threshold_spin.setRange(5, 20)
        level3_phash_threshold_spin.setValue(10)
        level3_phash_threshold_spin.setSuffix(" bits")
        level3_phash_threshold_spin.setToolTip("Distance Hamming max pour pHash (10 bits recommandé)")
        advanced_mode_layout.addWidget(level3_phash_threshold_spin, 5, 1)

        # Taux minimum de frames OK
        advanced_mode_layout.addWidget(QLabel("✅ Niveau 3 - Frames OK :"), 6, 0)
        level3_frame_rate_spin = QDoubleSpinBox()
        level3_frame_rate_spin.setRange(0.6, 0.95)
        level3_frame_rate_spin.setValue(0.8)
        level3_frame_rate_spin.setSingleStep(0.05)
        level3_frame_rate_spin.setDecimals(2)
        level3_frame_rate_spin.setSuffix(" %")
        level3_frame_rate_spin.setToolTip("Pourcentage minimum de frames similaires pour confirmer (0.8 = 80%)")
        advanced_mode_layout.addWidget(level3_frame_rate_spin, 6, 1)

        layout.addWidget(advanced_mode_group)

        # ═══════════════════════════════════════════════════════════
        # VÉRIFICATION DE SOUS-SÉQUENCES (Strategy 3: Scene Cuts Veto)
        # ═══════════════════════════════════════════════════════════
        subseq_verification_group = QGroupBox("🎯 Vérification de Sous-séquences")
        subseq_verification_layout = QGridLayout(subseq_verification_group)
        subseq_verification_layout.setSpacing(10)

        # Description
        subseq_verif_desc = QLabel(
            "Strategy 3 (Scene Cuts Veto) - Résultats de test :\n"
            "• Précision: 100% (zéro faux positifs)\n"
            "• Rappel: 72.7%\n"
            "• F1 Score: 84.2%\n\n"
            "Vérifie les correspondances par détection de transitions\n"
            "et coefficients DCT pour éviter les faux positifs"
        )
        subseq_verif_desc.setWordWrap(True)
        subseq_verif_desc.setStyleSheet("QLabel { color: #6C757D; font-size: 10px; }")
        subseq_verification_layout.addWidget(subseq_verif_desc, 0, 0, 1, 2)

        # Activer la vérification
        enable_subseq_verification = QCheckBox("Activer la vérification de sous-séquences")
        enable_subseq_verification.setChecked(True)  # Activé par défaut
        enable_subseq_verification.setStyleSheet("QCheckBox { font-weight: bold; color: #28A745; }")
        enable_subseq_verification.setToolTip(
            "Active la vérification par Scene Cuts + DCT.\n"
            "Élimine les faux positifs (contenus similaires mais non extraits).\n"
            "Recommandé pour une détection précise."
        )
        subseq_verification_layout.addWidget(enable_subseq_verification, 1, 0, 1, 2)

        # Seuil DCT
        subseq_verification_layout.addWidget(QLabel("🔬 Seuil DCT :"), 2, 0)
        subseq_dct_threshold_spin = QDoubleSpinBox()
        subseq_dct_threshold_spin.setRange(60.0, 95.0)
        subseq_dct_threshold_spin.setValue(75.0)
        subseq_dct_threshold_spin.setSuffix(" %")
        subseq_dct_threshold_spin.setDecimals(1)
        subseq_dct_threshold_spin.setToolTip(
            "Similarité DCT minimale pour accepter une correspondance.\n"
            "75% = Valeur optimale testée (100% précision).\n"
            "Plus bas = Plus permissif (risque de faux positifs)."
        )
        subseq_verification_layout.addWidget(subseq_dct_threshold_spin, 2, 1)

        # Seuil de séquence
        subseq_verification_layout.addWidget(QLabel("🎬 Seuil séquence :"), 3, 0)
        subseq_sequence_threshold_spin = QDoubleSpinBox()
        subseq_sequence_threshold_spin.setRange(85.0, 99.0)
        subseq_sequence_threshold_spin.setValue(95.0)
        subseq_sequence_threshold_spin.setSuffix(" %")
        subseq_sequence_threshold_spin.setDecimals(1)
        subseq_sequence_threshold_spin.setToolTip(
            "Correspondance de séquence minimale requise.\n"
            "95% = Valeur optimale testée.\n"
            "Assure que la séquence d'images correspond très bien."
        )
        subseq_verification_layout.addWidget(subseq_sequence_threshold_spin, 3, 1)

        # Workers de vérification
        subseq_verification_layout.addWidget(QLabel("⚡ Workers vérification :"), 4, 0)
        subseq_verification_workers_spin = QSpinBox()
        subseq_verification_workers_spin.setRange(1, 8)
        subseq_verification_workers_spin.setValue(2)
        subseq_verification_workers_spin.setToolTip(
            "Nombre de threads parallèles pour la vérification.\n"
            "2 = Bon équilibre performance/charge CPU.\n"
            "Plus élevé = Vérification plus rapide mais plus de CPU."
        )
        subseq_verification_layout.addWidget(subseq_verification_workers_spin, 4, 1)

        # Label d'information
        subseq_verif_info = QLabel(
            "ℹ️ La vérification ajoute ~2-5 secondes par correspondance mais élimine "
            "tous les faux positifs selon les tests. Hautement recommandé."
        )
        subseq_verif_info.setStyleSheet("QLabel { color: #28A745; font-size: 9px; padding: 5px; }")
        subseq_verif_info.setWordWrap(True)
        subseq_verification_layout.addWidget(subseq_verif_info, 5, 0, 1, 2)

        layout.addWidget(subseq_verification_group)

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
        tab.video_threshold_spin = video_threshold_spin
        tab.enable_flip_detection = enable_flip_detection
        tab.comparison_workers_spin = comparison_workers_spin
        tab.batch_size_spin = batch_size_spin
        tab.comparison_timeout_spin = comparison_timeout_spin
        tab.comparison_cache_size_spin = comparison_cache_size_spin

        # Advanced 3-level mode
        tab.enable_advanced_mode = enable_advanced_mode
        tab.level1_threshold_spin = level1_threshold_spin
        tab.level2_duration_spin = level2_duration_spin
        tab.level2_threshold_spin = level2_threshold_spin
        tab.level3_phash_threshold_spin = level3_phash_threshold_spin
        tab.level3_frame_rate_spin = level3_frame_rate_spin

        # Subsequence verification (Strategy 3)
        tab.enable_subseq_verification = enable_subseq_verification
        tab.subseq_dct_threshold_spin = subseq_dct_threshold_spin
        tab.subseq_sequence_threshold_spin = subseq_sequence_threshold_spin
        tab.subseq_verification_workers_spin = subseq_verification_workers_spin

        # Set scroll area content and add to tab
        scroll_area.setWidget(content_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)

        return tab

    @staticmethod
    def _create_debug_tab() -> QWidget:
        """
        Create the debug tab with interactive hash debugger and scrollbar.

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
        from ..progress_widgets import AudioFingerprintDebugger
        audio_debugger = AudioFingerprintDebugger()
        layout.addWidget(audio_debugger)

        layout.addStretch()

        # Store references for later access
        tab.hash_debugger_v2 = hash_debugger_v2
        tab.audio_debugger = audio_debugger

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

        stop_btn = QPushButton("⏹️ ARRÊTER")
        stop_btn.setMinimumHeight(40)
        stop_btn.setStyleSheet(UIPanels._get_button_style("#DC3545", "#C82333", font_size=13))
        stop_btn.clicked.connect(callbacks['stop'])

        main_layout.addWidget(analyze_btn)
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
        from ..progress_widgets import StatsCounter
        stats_counter = StatsCounter()
        layout.addWidget(stats_counter)

        # Progress widgets
        audio_progress = ModernProgressWidget("🎵 Audio fingerprinting")
        layout.addWidget(audio_progress)

        file_progress = ModernProgressWidget("📊 File hashing")
        layout.addWidget(file_progress)

        duplicate_progress = ModernProgressWidget("🔍 Duplicate detection")
        layout.addWidget(duplicate_progress)

        # Add stretch
        layout.addStretch(2)

        widgets = {
            'status_indicator': status_indicator,
            'stats_counter': stats_counter,
            'audio_progress': audio_progress,
            'file_progress': file_progress,
            'duplicate_progress': duplicate_progress
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
