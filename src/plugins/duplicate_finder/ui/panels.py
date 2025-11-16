"""
UI panel creation utilities for the duplicate finder.

This module provides factory methods for creating UI panels and their components,
separating UI construction from business logic.
"""
from typing import Callable, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox,
    QGridLayout, QDoubleSpinBox, QSpinBox, QFrame, QLabel, QTabWidget,
    QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..progress_widgets import ModernProgressWidget, FileListWidget, StatusIndicator, HashDebugger, HashDebuggerV2
from ..themes import get_current_theme


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
        title = QLabel("🔍 Video Duplicate Detector")
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
        tabs.addTab(files_tab, "📁 Files")

        # Parameters tab
        params_tab = UIPanels._create_parameters_tab(callbacks)
        tabs.addTab(params_tab, "⚙️ Settings")

        # Debug tab
        debug_tab = UIPanels._create_debug_tab()
        tabs.addTab(debug_tab, "🔬 Debug")

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
        reload_last_folder_btn = QPushButton("🔄 Reload last folder")
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
        add_files_btn = QPushButton("📄 Add files")
        add_files_btn.setMinimumHeight(40)
        add_files_btn.setStyleSheet(UIPanels._get_button_style("#007BFF", "#0056B3"))
        add_files_btn.clicked.connect(callbacks['add_files'])

        # Add folder button
        add_folder_btn = QPushButton("📂 Add folder")
        add_folder_btn.setMinimumHeight(40)
        add_folder_btn.setStyleSheet(UIPanels._get_button_style("#28A745", "#1E7E34"))
        add_folder_btn.clicked.connect(callbacks['add_folder'])

        # Clear list button
        clear_btn = QPushButton("🗑️ Clear list")
        clear_btn.setMinimumHeight(40)
        clear_btn.setStyleSheet(UIPanels._get_button_style("#FD7E14", "#E55A00"))
        clear_btn.clicked.connect(callbacks['clear_list'])

        # Clear cache button
        clear_cache_btn = QPushButton("💾 Clear cache")
        clear_cache_btn.setMinimumHeight(40)
        clear_cache_btn.setStyleSheet(UIPanels._get_button_style("#6F42C1", "#59359A"))
        clear_cache_btn.clicked.connect(callbacks['clear_cache'])

        buttons_layout.addWidget(add_files_btn, 0, 0)
        buttons_layout.addWidget(add_folder_btn, 0, 1)
        buttons_layout.addWidget(clear_btn, 1, 0)
        buttons_layout.addWidget(clear_cache_btn, 1, 1)

        layout.addLayout(buttons_layout)
        layout.addWidget(file_list_widget)

        return tab

    @staticmethod
    def _create_parameters_tab(callbacks: Dict[str, Callable]) -> QWidget:
        """
        Create the parameters configuration tab.

        Args:
            callbacks: Dictionary of callbacks.

        Returns:
            Tuple of (QWidget, dict of parameter widgets).
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Essential parameters group
        essential_group = QGroupBox("🎯 Essential parameters")
        essential_layout = QGridLayout(essential_group)
        essential_layout.setSpacing(10)

        essential_layout.addWidget(QLabel("Similarity threshold:"), 0, 0)
        threshold_spin = QDoubleSpinBox()
        threshold_spin.setRange(50.0, 100.0)
        threshold_spin.setValue(90.0)
        threshold_spin.setSuffix("%")
        threshold_spin.setDecimals(1)
        essential_layout.addWidget(threshold_spin, 0, 1)

        # Hash method selector
        essential_layout.addWidget(QLabel("Hash method:"), 1, 0)
        hash_method_combo = QComboBox()
        hash_method_combo.addItem("pHash (Precise - Slower)", "pHash")
        hash_method_combo.addItem("dHash (Balanced)", "dHash")
        hash_method_combo.addItem("aHash (Fast - Less Precise)", "aHash")
        hash_method_combo.setToolTip(
            "pHash: Most accurate, slower\n"
            "dHash: Good balance of speed/accuracy\n"
            "aHash: Fastest, less accurate"
        )
        hash_method_combo.setCurrentIndex(0)  # Default to pHash
        essential_layout.addWidget(hash_method_combo, 1, 1)

        layout.addWidget(essential_group)

        # Parallelization group
        workers_group = QGroupBox("🔄 Parallelization")
        workers_layout = QGridLayout(workers_group)
        workers_layout.setSpacing(10)

        workers_layout.addWidget(QLabel("Hash workers:"), 0, 0)
        hash_workers_spin = QSpinBox()
        hash_workers_spin.setRange(1, 8)
        hash_workers_spin.setValue(2)
        workers_layout.addWidget(hash_workers_spin, 0, 1)

        workers_layout.addWidget(QLabel("Comparison workers:"), 1, 0)
        comparison_workers_spin = QSpinBox()
        comparison_workers_spin.setRange(1, 8)
        comparison_workers_spin.setValue(4)
        workers_layout.addWidget(comparison_workers_spin, 1, 1)

        workers_layout.addWidget(QLabel("Batch size:"), 2, 0)
        batch_size_spin = QSpinBox()
        batch_size_spin.setRange(10, 200)
        batch_size_spin.setValue(50)
        workers_layout.addWidget(batch_size_spin, 2, 1)

        layout.addWidget(workers_group)

        # Comparison algorithm group
        algo_group = QGroupBox("🚀 Comparison Algorithm")
        algo_layout = QGridLayout(algo_group)
        algo_layout.setSpacing(10)

        algo_layout.addWidget(QLabel("Algorithm:"), 0, 0)
        comparison_algorithm_combo = QComboBox()
        comparison_algorithm_combo.addItem("Naïve (All pairs - Slow, 100% accurate)", "naive")
        comparison_algorithm_combo.addItem("Ball Tree (Fast, 100% accurate)", "balltree")
        comparison_algorithm_combo.addItem("Annoy (Very fast, ~98% accurate)", "annoy")
        comparison_algorithm_combo.addItem("FAISS (Ultra fast, ~95-99% accurate)", "faiss")
        comparison_algorithm_combo.setCurrentIndex(1)  # Ball Tree by default for good balance
        comparison_algorithm_combo.setToolTip(
            "Naïve: Compare all pairs (slow for 1000+ files)\n"
            "Ball Tree: Good for 100-2000 files, 50x faster\n"
            "Annoy: Best for 1000-10000 files, 200x faster\n"
            "FAISS: Best for 2000+ files, 100-1000x faster\n\n"
            "For 2000+ files, use FAISS or Annoy!"
        )
        algo_layout.addWidget(comparison_algorithm_combo, 0, 1)

        # Info label
        algo_info = QLabel(
            "ℹ️ Faster algorithms use approximate search.\n"
            "Ball Tree is exact. Annoy/FAISS trade tiny precision for huge speed."
        )
        algo_info.setStyleSheet("QLabel { color: #6C757D; font-size: 9px; padding: 5px; }")
        algo_info.setWordWrap(True)
        algo_layout.addWidget(algo_info, 1, 0, 1, 2)

        layout.addWidget(algo_group)

        # Timeouts group
        timeout_group = QGroupBox("⏱️ Timeouts")
        timeout_layout = QGridLayout(timeout_group)
        timeout_layout.setSpacing(10)

        timeout_layout.addWidget(QLabel("Hash timeout:"), 0, 0)
        hash_timeout_spin = QSpinBox()
        hash_timeout_spin.setRange(30, 600)
        hash_timeout_spin.setValue(120)
        hash_timeout_spin.setSuffix(" sec")
        timeout_layout.addWidget(hash_timeout_spin, 0, 1)

        timeout_layout.addWidget(QLabel("Comparison timeout:"), 1, 0)
        comparison_timeout_spin = QSpinBox()
        comparison_timeout_spin.setRange(5, 120)
        comparison_timeout_spin.setValue(30)
        comparison_timeout_spin.setSuffix(" sec")
        timeout_layout.addWidget(comparison_timeout_spin, 1, 1)

        layout.addWidget(timeout_group)

        # Presets group
        presets_group = QGroupBox("🚀 Quick presets")
        presets_layout = QHBoxLayout(presets_group)

        fast_btn = QPushButton("⚡ Fast")
        fast_btn.setStyleSheet(UIPanels._get_button_style("#DC3545", "#A71E2A"))
        fast_btn.clicked.connect(lambda: callbacks['apply_preset']("fast"))

        balanced_btn = QPushButton("⚖️ Balanced")
        balanced_btn.setStyleSheet(UIPanels._get_button_style("#007BFF", "#0056B3"))
        balanced_btn.clicked.connect(lambda: callbacks['apply_preset']("balanced"))

        quality_btn = QPushButton("🎯 Quality")
        quality_btn.setStyleSheet(UIPanels._get_button_style("#28A745", "#1E7E34"))
        quality_btn.clicked.connect(lambda: callbacks['apply_preset']("quality"))

        presets_layout.addWidget(fast_btn)
        presets_layout.addWidget(balanced_btn)
        presets_layout.addWidget(quality_btn)

        layout.addWidget(presets_group)

        # Subsequence detection group
        subsequence_group = QGroupBox("🎬 Subsequence Detection (Optional)")
        subsequence_layout = QGridLayout(subsequence_group)
        subsequence_layout.setSpacing(10)

        # Enable checkbox
        enable_subsequence_check = QCheckBox("Enable subsequence detection")
        enable_subsequence_check.setStyleSheet("QCheckBox { font-weight: bold; }")
        subsequence_layout.addWidget(enable_subsequence_check, 0, 0, 1, 2)

        # Sample interval
        subsequence_layout.addWidget(QLabel("Sample interval:"), 1, 0)
        subsequence_sample_interval_spin = QDoubleSpinBox()
        subsequence_sample_interval_spin.setRange(1.0, 10.0)
        subsequence_sample_interval_spin.setValue(3.0)
        subsequence_sample_interval_spin.setSuffix(" sec")
        subsequence_sample_interval_spin.setDecimals(1)
        subsequence_sample_interval_spin.setToolTip("Interval between sampled frames (default: 3.0s)")
        subsequence_layout.addWidget(subsequence_sample_interval_spin, 1, 1)

        # Min match ratio
        subsequence_layout.addWidget(QLabel("Min match ratio:"), 2, 0)
        subsequence_min_match_spin = QDoubleSpinBox()
        subsequence_min_match_spin.setRange(70.0, 95.0)
        subsequence_min_match_spin.setValue(80.0)
        subsequence_min_match_spin.setSuffix("%")
        subsequence_min_match_spin.setDecimals(1)
        subsequence_min_match_spin.setToolTip("Minimum match ratio to consider a subsequence (default: 80%)")
        subsequence_layout.addWidget(subsequence_min_match_spin, 2, 1)

        # Cache memory limit
        subsequence_layout.addWidget(QLabel("Cache memory limit:"), 3, 0)
        subsequence_cache_memory_spin = QSpinBox()
        subsequence_cache_memory_spin.setRange(100, 2000)
        subsequence_cache_memory_spin.setValue(500)
        subsequence_cache_memory_spin.setSuffix(" MB")
        subsequence_cache_memory_spin.setToolTip("Maximum memory for dense hash cache (default: 500MB)")
        subsequence_layout.addWidget(subsequence_cache_memory_spin, 3, 1)

        # Info label
        info_label = QLabel("ℹ️ Detects when a short video is extracted from a longer video.\n"
                           "Uses more memory but protected by LRU cache with limit above.")
        info_label.setStyleSheet("QLabel { color: #6C757D; font-size: 9px; padding: 5px; }")
        info_label.setWordWrap(True)
        subsequence_layout.addWidget(info_label, 4, 0, 1, 2)

        layout.addWidget(subsequence_group)

        # Hash Debugging Tool
        hash_debugger = HashDebugger()
        layout.addWidget(hash_debugger)

        layout.addStretch()

        # Store widget references in tab for later access
        tab.threshold_spin = threshold_spin
        tab.hash_method_combo = hash_method_combo
        tab.hash_workers_spin = hash_workers_spin
        tab.comparison_workers_spin = comparison_workers_spin
        tab.batch_size_spin = batch_size_spin
        tab.comparison_algorithm_combo = comparison_algorithm_combo
        tab.hash_timeout_spin = hash_timeout_spin
        tab.comparison_timeout_spin = comparison_timeout_spin
        tab.enable_subsequence_check = enable_subsequence_check
        tab.subsequence_sample_interval_spin = subsequence_sample_interval_spin
        tab.subsequence_min_match_spin = subsequence_min_match_spin
        tab.subsequence_cache_memory_spin = subsequence_cache_memory_spin
        tab.hash_debugger = hash_debugger

        return tab

    @staticmethod
    def _create_debug_tab() -> QWidget:
        """
        Create the debug tab with interactive hash debugger.

        Returns:
            Configured QWidget for debug tab.
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Create hash debugger V2
        hash_debugger_v2 = HashDebuggerV2()

        layout.addWidget(hash_debugger_v2)
        layout.addStretch()

        # Store reference for later access
        tab.hash_debugger_v2 = hash_debugger_v2

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

        analyze_btn = QPushButton("🔍 START")
        analyze_btn.setMinimumHeight(40)
        analyze_btn.setStyleSheet(UIPanels._get_button_style("#28A745", "#218838", font_size=13))
        analyze_btn.clicked.connect(callbacks['analyze'])

        stop_btn = QPushButton("⏹️ STOP")
        stop_btn.setMinimumHeight(40)
        stop_btn.setStyleSheet(UIPanels._get_button_style("#DC3545", "#C82333", font_size=13))
        stop_btn.clicked.connect(callbacks['stop'])

        main_layout.addWidget(analyze_btn)
        main_layout.addWidget(stop_btn)
        layout.addLayout(main_layout)

        # Secondary buttons
        secondary_layout = QHBoxLayout()

        stats_btn = QPushButton("📊 Stats")
        stats_btn.setMaximumHeight(30)
        stats_btn.setStyleSheet(UIPanels._get_button_style("#17A2B8", "#138496", font_size=11, padding="5px 8px"))
        stats_btn.clicked.connect(callbacks['show_stats'])

        pending_btn = QPushButton("📋 Duplicates")
        pending_btn.setMaximumHeight(30)
        pending_btn.setStyleSheet(UIPanels._get_button_style("#FD7E14", "#E55A00", font_size=11, padding="5px 8px"))
        pending_btn.clicked.connect(callbacks['show_pending'])

        close_btn = QPushButton("🚪 Close")
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
        file_progress = ModernProgressWidget("📊 File hashing")
        layout.addWidget(file_progress)

        duplicate_progress = ModernProgressWidget("🔍 Duplicate detection")
        layout.addWidget(duplicate_progress)

        subsequence_progress = ModernProgressWidget("🎬 Subsequence detection")
        layout.addWidget(subsequence_progress)

        # Add stretch
        layout.addStretch(2)

        widgets = {
            'status_indicator': status_indicator,
            'stats_counter': stats_counter,
            'file_progress': file_progress,
            'duplicate_progress': duplicate_progress,
            'subsequence_progress': subsequence_progress
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
