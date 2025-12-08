"""Advanced settings interface with tabs and advanced suffix management"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QComboBox, QFileDialog, QMessageBox, 
    QHeaderView, QLabel, QSpinBox, QProgressBar, QGroupBox, QCheckBox, 
    QApplication, QDialog, QDialogButtonBox, QFormLayout, QGridLayout, 
    QLineEdit, QTabWidget, QSlider, QFrame, QTextEdit, QSplitter, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QMutex, QMutexLocker, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from src.core.i18n import t

class AdvancedSettingsDialog(QDialog):
    """Advanced settings interface with tabs and extended features."""
    
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.settings = settings
        self.parent_window = parent
        
        self.setWindowTitle(t("advanced_settings.window.title", "⚙️ Video Converter Settings - Advanced"))
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        self.setup_ui()
        self.load_settings()
        self.connect_signals()
    
    def setup_ui(self):
        """Main interface configuration with tabs."""
        layout = QVBoxLayout(self)

        # Header with info and quick preset
        self.setup_header(layout)

        # Main tabs
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Tab 1: Detection and Filtering
        self.setup_detection_tab()

        # Tab 2: Quality and Performance
        self.setup_quality_tab()

        # Tab 3: File Management
        self.setup_file_management_tab()

        # Tab 4: Advanced and Debugging
        self.setup_advanced_tab()

        # Validation buttons
        self.setup_buttons(layout)
    
    def setup_header(self, layout):
        """Header with quick preset selection."""
        header_frame = QFrame()
        header_frame.setStyleSheet("QFrame { background-color: #f0f0f0; border-radius: 5px; padding: 10px; }")
        header_layout = QHBoxLayout(header_frame)
        
        # Title
        title_label = QLabel(t("advanced_settings.header.title", "🎬 Video Converter Configuration"))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Quick presets
        preset_label = QLabel(t("advanced_settings.header.quick_preset", "Quick Preset:"))
        header_layout.addWidget(preset_label)
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "🎯 Débutant (Auto)",
            "⚡ Rapide", 
            "⚖️ Équilibré",
            "💾 Compression Max",
            "🎯 Expert (Personnalisé)"
        ])
        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        header_layout.addWidget(self.preset_combo)
        
        layout.addWidget(header_frame)
    
    def setup_detection_tab(self):
        """Tab: File detection and filtering."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # === SECTION: Selection Criteria ===
        selection_group = QGroupBox("🎯 Critères de Sélection des Fichiers")
        selection_layout = QFormLayout()
        
        # Size threshold with slider
        size_widget = QWidget()
        size_layout = QVBoxLayout(size_widget)
        
        size_control_layout = QHBoxLayout()
        self.use_size_threshold = QCheckBox("Traiter seulement les files volumineux")
        size_control_layout.addWidget(self.use_size_threshold)
        size_layout.addLayout(size_control_layout)
        
        # Slider for size
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("50 MB"))
        
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(50)
        self.size_slider.setMaximum(5000)
        self.size_slider.setValue(500)
        self.size_slider.valueChanged.connect(self.update_size_display)
        slider_layout.addWidget(self.size_slider)
        
        slider_layout.addWidget(QLabel("5 GB"))
        size_layout.addLayout(slider_layout)
        
        self.size_display = QLabel("💾 Size minimale: 500 MB")
        self.size_display.setStyleSheet("color: #2E86AB; font-weight: bold;")
        size_layout.addWidget(self.size_display)
        
        selection_layout.addRow("Filtrage par size:", size_widget)
        
        # File extensions
        ext_widget = QWidget()
        ext_layout = QVBoxLayout(ext_widget)
        
        self.video_extensions = QLineEdit()
        self.video_extensions.setPlaceholderText("mp4,avi,mkv,mov,flv,webm,wmv")
        ext_layout.addWidget(self.video_extensions)
        
        ext_info = QLabel("💡 Extensions supportées (séparées par des virgules)")
        ext_info.setStyleSheet("color: #666; font-size: 11px;")
        ext_layout.addWidget(ext_info)
        
        selection_layout.addRow("Extensions vidéo:", ext_widget)
        
        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)
        
        # === SECTION: Processed File Handling ===
        processed_group = QGroupBox("🏷️ Handling des Fichiers Déjà Traités")
        processed_layout = QFormLayout()
        
        # Suffix for successfully converted files
        success_widget = QWidget()
        success_layout = QVBoxLayout(success_widget)
        
        suffix_layout = QHBoxLayout()
        suffix_layout.addWidget(QLabel("Suffixe:"))
        self.success_suffix = QLineEdit()
        self.success_suffix.setPlaceholderText("_cvt")
        self.success_suffix.setMaxLength(20)
        self.success_suffix.setFixedWidth(100)
        suffix_layout.addWidget(self.success_suffix)
        
        suffix_layout.addWidget(QLabel("Exemple: video.mp4 → video_cvt.mp4"))
        suffix_layout.addStretch()
        success_layout.addLayout(suffix_layout)
        
        # Actions for files with success suffix
        self.ignore_converted = QCheckBox("Ignorer complètement ces files")
        success_layout.addWidget(self.ignore_converted)
        
        processed_layout.addRow("✅ Fichiers convertis:", success_widget)
        
        # Suffix for non-compressible files
        failed_widget = QWidget()
        failed_layout = QVBoxLayout(failed_widget)
        
        failed_suffix_layout = QHBoxLayout()
        failed_suffix_layout.addWidget(QLabel("Suffixe:"))
        self.failed_suffix = QLineEdit()
        self.failed_suffix.setPlaceholderText("_nocomp")
        self.failed_suffix.setMaxLength(20)
        self.failed_suffix.setFixedWidth(100)
        failed_suffix_layout.addWidget(self.failed_suffix)
        
        failed_suffix_layout.addWidget(QLabel("Exemple: video.mp4 → video_nocomp.mp4"))
        failed_suffix_layout.addStretch()
        failed_layout.addLayout(failed_suffix_layout)
        
        # Actions for non-compressible files
        failed_action_layout = QHBoxLayout()
        self.mark_non_compressible = QCheckBox("Marquer les files non-compressibles")
        self.mark_non_compressible.setToolTip("Add un suffixe aux files dont aucune tentative n'a réduit la size")
        failed_action_layout.addWidget(self.mark_non_compressible)
        failed_layout.addLayout(failed_action_layout)
        
        self.ignore_non_compressible = QCheckBox("Ignorer les files marqués comme non-compressibles")
        failed_layout.addWidget(self.ignore_non_compressible)
        
        processed_layout.addRow("❌ Non-compressibles:", failed_widget)
        
        processed_group.setLayout(processed_layout)
        layout.addWidget(processed_group)
        
        # === SECTION: Quick Actions ===
        actions_group = QGroupBox("🚀 Actions Rapides")
        actions_layout = QHBoxLayout()
        
        self.select_converted_btn = QPushButton(t("advanced_settings.actions.select_converted", "🔍 Select converted"))
        self.select_converted_btn.clicked.connect(self.select_converted_files)
        actions_layout.addWidget(self.select_converted_btn)
        
        self.select_failed_btn = QPushButton(t("advanced_settings.actions.select_failed", "🚫 Select non-compressible"))
        self.select_failed_btn.clicked.connect(self.select_failed_files)
        actions_layout.addWidget(self.select_failed_btn)
        
        self.remove_converted_btn = QPushButton(t("advanced_settings.actions.remove_converted", "🗑️ Remove converted"))
        self.remove_converted_btn.clicked.connect(self.remove_converted_files)
        actions_layout.addWidget(self.remove_converted_btn)
        
        actions_layout.addStretch()
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, t("advanced_settings.tab.detection", "🎯 Detection"))
    
    def setup_quality_tab(self):
        """Tab: Quality and performance with simple and advanced configuration."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # === SECTION: Configuration Mode ===
        mode_group = QGroupBox("🎯 Mode de Configuration")
        mode_layout = QFormLayout()
        
        # Mode selection
        mode_widget = QWidget()
        mode_widget_layout = QVBoxLayout(mode_widget)
        
        self.simple_mode = QCheckBox("Mode Simple - Une seule configuration")
        self.simple_mode.setToolTip("Utilise les mêmes settings pour toutes les tentatives")
        self.simple_mode.stateChanged.connect(self.toggle_compression_mode)
        mode_widget_layout.addWidget(self.simple_mode)
        
        self.advanced_mode = QCheckBox("Mode Avancé - Configurer les 3 tentatives individuellement")
        self.advanced_mode.setToolTip("Permet de personnaliser chaque tentative de compression")
        self.advanced_mode.stateChanged.connect(self.toggle_compression_mode)
        mode_widget_layout.addWidget(self.advanced_mode)
        
        # Ensure only one mode is selected
        self.simple_mode.stateChanged.connect(
            lambda state: self.advanced_mode.setChecked(False) if state else None
        )
        self.advanced_mode.stateChanged.connect(
            lambda state: self.simple_mode.setChecked(False) if state else None
        )
        
        mode_layout.addRow("Configuration:", mode_widget)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # === SECTION: Simple Configuration ===
        self.simple_config_group = QGroupBox("⚙️ Configuration Simple")
        simple_layout = QFormLayout()
        
        # CRF with slider and visual indicators
        crf_widget = QWidget()
        crf_layout = QVBoxLayout(crf_widget)
        
        crf_control_layout = QHBoxLayout()
        crf_control_layout.addWidget(QLabel("CRF (Qualité):"))
        
        self.crf_display_simple = QLabel("28 - Équilibré")
        self.crf_display_simple.setStyleSheet("font-weight: bold; color: #2E86AB;")
        crf_control_layout.addWidget(self.crf_display_simple)
        crf_control_layout.addStretch()
        crf_layout.addLayout(crf_control_layout)
        
        # CRF Slider
        crf_slider_layout = QHBoxLayout()
        
        quality_labels = QVBoxLayout()
        quality_labels.addWidget(QLabel("🎯 Haute"))
        quality_labels.addWidget(QLabel("Qualité"))
        crf_slider_layout.addLayout(quality_labels)
        
        self.crf_slider_simple = QSlider(Qt.Orientation.Horizontal)
        self.crf_slider_simple.setMinimum(18)
        self.crf_slider_simple.setMaximum(35)
        self.crf_slider_simple.setValue(28)
        self.crf_slider_simple.valueChanged.connect(self.update_simple_crf_display)
        crf_slider_layout.addWidget(self.crf_slider_simple)
        
        compression_labels = QVBoxLayout()
        compression_labels.addWidget(QLabel("💾 Haute"))
        compression_labels.addWidget(QLabel("Compression"))
        crf_slider_layout.addLayout(compression_labels)
        
        crf_layout.addLayout(crf_slider_layout)
        simple_layout.addRow("", crf_widget)
        
        # Preset
        preset_widget = QWidget()
        preset_layout = QHBoxLayout(preset_widget)
        
        self.preset_simple = QComboBox()
        self.preset_simple.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
        self.preset_simple.setCurrentText("fast")
        self.preset_simple.currentTextChanged.connect(self.update_simple_preset_info)
        preset_layout.addWidget(self.preset_simple)
        
        self.preset_info_simple = QLabel("⚡ Rapide, qualité correcte")
        self.preset_info_simple.setStyleSheet("color: #2E86AB; font-weight: bold;")
        preset_layout.addWidget(self.preset_info_simple)
        preset_layout.addStretch()
        
        simple_layout.addRow("Preset:", preset_widget)
        
        self.simple_config_group.setLayout(simple_layout)
        layout.addWidget(self.simple_config_group)
        
        # === SECTION: Advanced Configuration of 3 Attempts ===
        self.advanced_config_group = QGroupBox("🔄 Configuration des 3 Tentatives")
        advanced_layout = QVBoxLayout()
        
        # Explanatory header
        explanation = QLabel(
            "💡 Configurez individuellement chaque tentative de compression.\n"
            "Si la première échoue, la deuxième sera essayée, puis la troisième."
        )
        explanation.setStyleSheet("color: #666; font-style: italic; padding: 10px; background-color: #f9f9f9; border-radius: 5px;")
        explanation.setWordWrap(True)
        advanced_layout.addWidget(explanation)
        
        # Configuration of 3 attempts
        self.attempts_widgets = []
        
        for attempt_num in range(1, 4):
            attempt_group = QGroupBox(f"🎯 Tentative {attempt_num}")
            attempt_layout = QGridLayout()
            
            # Description of each attempt's objective
            objectives = [
                "⚡ Rapide et équilibrée - Premier essai with de bons settings",
                "⚖️ Compression renforcée - Si la première n'a pas assez compressé", 
                "💾 Compression maximale - Dernier recours pour les files difficiles"
            ]
            
            objective_label = QLabel(objectives[attempt_num - 1])
            objective_label.setStyleSheet("color: #666; font-style: italic;")
            attempt_layout.addWidget(objective_label, 0, 0, 1, 4)
            
            # CRF for this attempt
            attempt_layout.addWidget(QLabel("CRF:"), 1, 0)
            
            crf_spin = QSpinBox()
            crf_spin.setRange(18, 35)
            crf_spin.setValue([28, 30, 32][attempt_num - 1])  # Valeurs par défaut
            crf_spin.setToolTip(f"Qualité pour tentative {attempt_num} (18=haute qualité, 35=haute compression)")
            attempt_layout.addWidget(crf_spin, 1, 1)
            
            # Quality level display
            quality_label = QLabel()
            self.update_quality_label(quality_label, crf_spin.value())
            crf_spin.valueChanged.connect(lambda val, label=quality_label: self.update_quality_label(label, val))
            attempt_layout.addWidget(quality_label, 1, 2)
            
            # Preset for this attempt
            attempt_layout.addWidget(QLabel("Preset:"), 2, 0)
            
            preset_combo = QComboBox()
            preset_combo.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
            preset_combo.setCurrentText(["fast", "medium", "slow"][attempt_num - 1])  # Valeurs par défaut
            preset_combo.setToolTip(f"Speed pour tentative {attempt_num}")
            attempt_layout.addWidget(preset_combo, 2, 1)
            
            # Preset info display
            preset_info_label = QLabel()
            self.update_preset_label(preset_info_label, preset_combo.currentText())
            preset_combo.currentTextChanged.connect(lambda text, label=preset_info_label: self.update_preset_label(label, text))
            attempt_layout.addWidget(preset_info_label, 2, 2)
            
            # Relative time estimation
            time_estimate = QLabel()
            self.update_time_estimate(time_estimate, preset_combo.currentText())
            preset_combo.currentTextChanged.connect(lambda text, label=time_estimate: self.update_time_estimate(label, text))
            attempt_layout.addWidget(time_estimate, 2, 3)
            
            # Test button for this configuration
            test_btn = QPushButton(f"🧪 Tester T{attempt_num}")
            test_btn.setToolTip(f"Tester uniquement la configuration of the tentative {attempt_num}")
            test_btn.clicked.connect(lambda checked, num=attempt_num: self.test_single_attempt(num))
            attempt_layout.addWidget(test_btn, 3, 0, 1, 2)
            
            # Copy to other attempts
            copy_btn = QPushButton("📋 Copier")
            copy_menu = QMenu(copy_btn)
            for i in range(1, 4):
                if i != attempt_num:
                    action = copy_menu.addAction(f"→ Vers Tentative {i}")
                    action.triggered.connect(lambda checked, src=attempt_num, dst=i: self.copy_attempt_config(src, dst))
            copy_btn.setMenu(copy_menu)
            attempt_layout.addWidget(copy_btn, 3, 2)
            
            attempt_group.setLayout(attempt_layout)
            advanced_layout.addWidget(attempt_group)
            
            # Store widgets for later retrieval
            self.attempts_widgets.append({
                'crf': crf_spin,
                'preset': preset_combo,
                'quality_label': quality_label,
                'preset_info': preset_info_label,
                'time_estimate': time_estimate
            })
        
        # Quick preset buttons for all 3 attempts
        presets_layout = QHBoxLayout()
        presets_layout.addWidget(QLabel("Presets rapides:"))
        
        conservative_btn = QPushButton("🛡️ Conservateur")
        conservative_btn.setToolTip("T1: CRF26+fast, T2: CRF28+medium, T3: CRF30+slow")
        conservative_btn.clicked.connect(lambda: self.apply_attempts_preset("conservative"))
        presets_layout.addWidget(conservative_btn)
        
        balanced_btn = QPushButton("⚖️ Équilibré")
        balanced_btn.setToolTip("T1: CRF28+fast, T2: CRF30+medium, T3: CRF32+slow")
        balanced_btn.clicked.connect(lambda: self.apply_attempts_preset("balanced"))
        presets_layout.addWidget(balanced_btn)
        
        aggressive_btn = QPushButton("🔥 Agressif")
        aggressive_btn.setToolTip("T1: CRF30+medium, T2: CRF32+slow, T3: CRF34+veryslow")
        aggressive_btn.clicked.connect(lambda: self.apply_attempts_preset("aggressive"))
        presets_layout.addWidget(aggressive_btn)
        
        presets_layout.addStretch()
        advanced_layout.addLayout(presets_layout)
        
        self.advanced_config_group.setLayout(advanced_layout)
        layout.addWidget(self.advanced_config_group)
        
        # === SECTION: Global Options ===
        global_group = QGroupBox("🌍 Options Globales")
        global_layout = QFormLayout()
        
        # Enable multiple attempts
        self.enable_multiple_attempts = QCheckBox("Activer les tentatives multiples")
        self.enable_multiple_attempts.setChecked(True)
        self.enable_multiple_attempts.stateChanged.connect(self.toggle_attempts_availability)
        global_layout.addRow("Tentatives:", self.enable_multiple_attempts)
        
        # Number of threads
        threads_widget = QWidget()
        threads_layout = QHBoxLayout(threads_widget)
        
        self.max_threads = QSpinBox()
        self.max_threads.setRange(1, 8)
        self.max_threads.setValue(3)
        threads_layout.addWidget(self.max_threads)
        
        import os
        cpu_count = os.cpu_count() or 1
        cpu_info = QLabel(f"(CPU: {cpu_count} cœurs détectés)")
        threads_layout.addWidget(cpu_info)
        
        auto_threads_btn = QPushButton("Auto")
        auto_threads_btn.clicked.connect(lambda: self.max_threads.setValue(min(cpu_count, 4)))
        threads_layout.addWidget(auto_threads_btn)
        
        threads_layout.addStretch()
        global_layout.addRow("Conversions simultanées:", threads_widget)
        
        global_group.setLayout(global_layout)
        layout.addWidget(global_group)

        # === SECTION: Iterative Compression with Target Size ===
        target_size_group = QGroupBox("🎯 Compression Itérative avec Taille Cible")
        target_size_layout = QFormLayout()

        # Description
        target_desc = QLabel(
            "💡 Compresse automatiquement jusqu'à atteindre une taille cible spécifique.\n"
            "Le système augmente progressivement le CRF jusqu'à obtenir la taille désirée."
        )
        target_desc.setStyleSheet("color: #666; font-style: italic; padding: 10px; background-color: #f9f9f9; border-radius: 5px;")
        target_desc.setWordWrap(True)
        target_size_layout.addRow(target_desc)

        # Enable target size mode
        self.use_target_size = QCheckBox("Activer la compression avec taille cible")
        self.use_target_size.setToolTip("Active le mode compression itérative pour atteindre une taille précise")
        self.use_target_size.stateChanged.connect(self.toggle_target_size_mode)
        target_size_layout.addRow("Mode:", self.use_target_size)

        # Taille cible avec slider
        target_size_widget = QWidget()
        target_size_widget_layout = QVBoxLayout(target_size_widget)

        target_slider_layout = QHBoxLayout()
        target_slider_layout.addWidget(QLabel("50 MB"))

        self.target_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.target_size_slider.setMinimum(50)
        self.target_size_slider.setMaximum(2000)
        self.target_size_slider.setValue(300)
        self.target_size_slider.valueChanged.connect(self.update_target_size_display)
        target_slider_layout.addWidget(self.target_size_slider)

        target_slider_layout.addWidget(QLabel("2 GB"))
        target_size_widget_layout.addLayout(target_slider_layout)

        self.target_size_display = QLabel("🎯 Taille cible: 300 MB")
        self.target_size_display.setStyleSheet("color: #2E86AB; font-weight: bold;")
        target_size_widget_layout.addWidget(self.target_size_display)

        target_size_layout.addRow("Taille cible:", target_size_widget)

        # Iterative compression parameters
        iterations_widget = QWidget()
        iterations_layout = QGridLayout(iterations_widget)

        # Maximum attempts
        iterations_layout.addWidget(QLabel("Max tentatives:"), 0, 0)
        self.max_compression_attempts = QSpinBox()
        self.max_compression_attempts.setRange(1, 10)
        self.max_compression_attempts.setValue(5)
        self.max_compression_attempts.setToolTip("Nombre maximum d'itérations de compression")
        iterations_layout.addWidget(self.max_compression_attempts, 0, 1)

        # Initial CRF
        iterations_layout.addWidget(QLabel("CRF initial:"), 1, 0)
        self.initial_crf = QSpinBox()
        self.initial_crf.setRange(18, 35)
        self.initial_crf.setValue(28)
        self.initial_crf.setToolTip("CRF de départ pour la première itération")
        iterations_layout.addWidget(self.initial_crf, 1, 1)

        # CRF step
        iterations_layout.addWidget(QLabel("CRF step:"), 2, 0)
        self.crf_step = QSpinBox()
        self.crf_step.setRange(1, 5)
        self.crf_step.setValue(2)
        self.crf_step.setToolTip("Augmentation du CRF à chaque itération")
        iterations_layout.addWidget(self.crf_step, 2, 1)

        # Maximum CRF
        iterations_layout.addWidget(QLabel("CRF max:"), 3, 0)
        self.max_crf = QSpinBox()
        self.max_crf.setRange(18, 51)
        self.max_crf.setValue(40)
        self.max_crf.setToolTip("CRF maximum à ne pas dépasser (limite de qualité)")
        iterations_layout.addWidget(self.max_crf, 3, 1)

        # Operation info
        iterations_info = QLabel(
            "ℹ️ Le système commence au CRF initial et l'augmente progressivement\n"
            "jusqu'à atteindre la taille cible ou le CRF max."
        )
        iterations_info.setStyleSheet("color: #666; font-size: 11px;")
        iterations_layout.addWidget(iterations_info, 4, 0, 1, 2)

        target_size_layout.addRow("Paramètres:", iterations_widget)

        target_size_group.setLayout(target_size_layout)
        layout.addWidget(target_size_group)

        # Initialize in simple mode by default
        self.simple_mode.setChecked(True)
        self.toggle_compression_mode()
        self.toggle_target_size_mode()  # Initialize target size widgets state

        layout.addStretch()
        self.tab_widget.addTab(tab, t("advanced_settings.tab.quality", "⚙️ Quality"))
    
    def setup_file_management_tab(self):
        """Tab: File management."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # === SECTION: Post-Conversion Actions ===
        actions_group = QGroupBox("📂 Actions Après Conversion Réussie")
        actions_layout = QFormLayout()
        
        # File management options
        file_actions_widget = QWidget()
        file_actions_layout = QVBoxLayout(file_actions_widget)
        
        self.keep_both = QCheckBox("Garder l'original et le file converti")
        self.keep_both.setChecked(True)
        file_actions_layout.addWidget(self.keep_both)
        
        self.replace_original = QCheckBox("Remplacer le file original")
        file_actions_layout.addWidget(self.replace_original)
        
        self.delete_if_smaller = QCheckBox("Remove l'original seulement si le nouveau est plus petit")
        file_actions_layout.addWidget(self.delete_if_smaller)
        
        # Connect checkboxes to avoid conflicts
        self.keep_both.stateChanged.connect(self.manage_file_action_conflicts)
        self.replace_original.stateChanged.connect(self.manage_file_action_conflicts)
        self.delete_if_smaller.stateChanged.connect(self.manage_file_action_conflicts)
        
        actions_layout.addRow("Handling des files:", file_actions_widget)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # === SECTION: Statistics and Monitoring ===
        stats_group = QGroupBox("📊 Statistics et Monitoring")
        stats_layout = QFormLayout()
        
        # Statistics display
        self.stats_display = QTextEdit()
        self.stats_display.setMaximumHeight(150)
        self.stats_display.setReadOnly(True)
        
        # Load current statistics
        self.refresh_stats_display()
        
        stats_layout.addRow("Historique:", self.stats_display)
        
        # Stats management buttons
        stats_buttons_widget = QWidget()
        stats_buttons_layout = QHBoxLayout(stats_buttons_widget)
        
        refresh_stats_btn = QPushButton("🔄 Actualiser")
        refresh_stats_btn.clicked.connect(self.refresh_stats)
        stats_buttons_layout.addWidget(refresh_stats_btn)
        
        export_stats_btn = QPushButton("📤 Exporter")
        export_stats_btn.clicked.connect(self.export_stats)
        stats_buttons_layout.addWidget(export_stats_btn)
        
        clear_stats_btn = QPushButton("🗑️ Effacer")
        clear_stats_btn.clicked.connect(self.clear_stats)
        stats_buttons_layout.addWidget(clear_stats_btn)
        
        stats_buttons_layout.addStretch()
        stats_layout.addRow("", stats_buttons_widget)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, t("advanced_settings.tab.files", "📂 Files"))
    
    def setup_advanced_tab(self):
        """Tab: Advanced settings."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # === SECTION: FFmpeg Options ===
        ffmpeg_group = QGroupBox("🔧 Options FFmpeg Avancées")
        ffmpeg_layout = QFormLayout()
        
        # Audio settings
        audio_widget = QWidget()
        audio_layout = QHBoxLayout(audio_widget)
        
        self.audio_copy = QCheckBox("Copier l'audio sans réencodage")
        self.audio_copy.setChecked(True)
        audio_layout.addWidget(self.audio_copy)
        
        audio_layout.addWidget(QLabel("Codec:"))
        self.audio_codec = QComboBox()
        self.audio_codec.addItems(["copy", "aac", "mp3", "ac3"])
        self.audio_codec.setCurrentText("copy")
        audio_layout.addWidget(self.audio_codec)
        
        audio_layout.addStretch()
        ffmpeg_layout.addRow("Audio:", audio_widget)
        
        # Compatibility options
        compat_widget = QWidget()
        compat_layout = QVBoxLayout(compat_widget)
        
        self.faststart = QCheckBox("Optimisation streaming (movflags +faststart)")
        self.faststart.setChecked(True)
        compat_layout.addWidget(self.faststart)
        
        self.avoid_negative_ts = QCheckBox("Corriger les timestamps négatifs")
        self.avoid_negative_ts.setChecked(True)
        compat_layout.addWidget(self.avoid_negative_ts)
        
        ffmpeg_layout.addRow("Compatibilité:", compat_widget)
        
        # Custom settings
        self.custom_params = QLineEdit()
        self.custom_params.setPlaceholderText("Settings FFmpeg additionnels (optionnel)")
        ffmpeg_layout.addRow("Settings custom:", self.custom_params)
        
        ffmpeg_group.setLayout(ffmpeg_layout)
        layout.addWidget(ffmpeg_group)
        
        # === SECTION: Debugging and Logs ===
        debug_group = QGroupBox("🐛 Debugging et Monitoring")
        debug_layout = QFormLayout()
        
        # Log level
        log_widget = QWidget()
        log_layout = QHBoxLayout(log_widget)
        
        log_layout.addWidget(QLabel("Niveau de log:"))
        self.log_level = QComboBox()
        self.log_level.addItems(["ERROR", "WARNING", "INFO", "DEBUG"])
        self.log_level.setCurrentText("INFO")
        log_layout.addWidget(self.log_level)
        
        log_layout.addStretch()
        debug_layout.addRow("Logging:", log_widget)
        
        # Monitoring options
        monitoring_widget = QWidget()
        monitoring_layout = QVBoxLayout(monitoring_widget)
        
        self.save_ffmpeg_output = QCheckBox("Save la sortie FFmpeg")
        monitoring_layout.addWidget(self.save_ffmpeg_output)
        
        self.detailed_progress = QCheckBox("Affichage de progression détaillé")
        self.detailed_progress.setChecked(True)
        monitoring_layout.addWidget(self.detailed_progress)
        
        debug_layout.addRow("Monitoring:", monitoring_widget)
        
        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)
        
        # === SECTION: Import/Export Configuration ===
        config_group = QGroupBox("💾 Saves Configuration")
        config_layout = QHBoxLayout()
        
        export_config_btn = QPushButton("📤 Exporter config")
        export_config_btn.clicked.connect(self.export_config)
        config_layout.addWidget(export_config_btn)
        
        import_config_btn = QPushButton("📥 Importer config")
        import_config_btn.clicked.connect(self.import_config)
        config_layout.addWidget(import_config_btn)
        
        reset_config_btn = QPushButton("🔄 Réinitialiser")
        reset_config_btn.clicked.connect(self.reset_config)
        config_layout.addWidget(reset_config_btn)
        
        config_layout.addStretch()
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, t("advanced_settings.tab.advanced", "🔧 Advanced"))
    
    def setup_buttons(self, layout):
        """Dialog validation buttons."""
        buttons_layout = QHBoxLayout()
        
        # Test button
        test_btn = QPushButton("🧪 Tester on 1 file")
        test_btn.clicked.connect(self.test_settings)
        test_btn.setToolTip("Tester la configuration on un seul file avant conversion de masse")
        buttons_layout.addWidget(test_btn)
        
        buttons_layout.addStretch()
        
        # Standard buttons
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel | 
            QDialogButtonBox.StandardButton.Apply
        )
        
        self.buttons.button(QDialogButtonBox.StandardButton.Apply).setText("Apply")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("OK and Convert")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        
        self.buttons.accepted.connect(self.accept_and_convert)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_settings)
        
        buttons_layout.addWidget(self.buttons)
        layout.addLayout(buttons_layout)
    
    def connect_signals(self):
        """Connect signals for real-time updates."""
        # Connect controls for real-time updates
        self.use_size_threshold.stateChanged.connect(self.update_size_threshold_state)
        self.mark_non_compressible.stateChanged.connect(self.update_failed_options_state)
    
    # === UI UPDATE METHODS ===

    def update_size_display(self, value):
        """Update size display."""
        if value < 1000:
            size_text = f"{value} MB"
        else:
            size_text = f"{value/1000:.1f} GB"

        self.size_display.setText(f"💾 Size minimale: {size_text}")

    def update_target_size_display(self, value):
        """Update target size display."""
        if value < 1000:
            size_text = f"{value} MB"
        else:
            size_text = f"{value/1000:.1f} GB"

        self.target_size_display.setText(f"🎯 Taille cible: {size_text}")

    def toggle_target_size_mode(self):
        """Enable/disable target size widgets based on checkbox."""
        enabled = self.use_target_size.isChecked()

        # Enable/disable all target size section widgets
        self.target_size_slider.setEnabled(enabled)
        self.max_compression_attempts.setEnabled(enabled)
        self.initial_crf.setEnabled(enabled)
        self.crf_step.setEnabled(enabled)
        self.max_crf.setEnabled(enabled)

        # If enabled, disable normal multiple attempts mode
        # (because target size mode manages its own iterations)
        if enabled and hasattr(self, 'enable_multiple_attempts'):
            self.enable_multiple_attempts.setEnabled(False)
            self.simple_config_group.setEnabled(False)
            self.advanced_config_group.setEnabled(False)
        elif hasattr(self, 'enable_multiple_attempts'):
            self.enable_multiple_attempts.setEnabled(True)
            self.simple_config_group.setEnabled(True)
            self.advanced_config_group.setEnabled(True)

    def toggle_compression_mode(self):
        """Toggle between simple and advanced mode."""
        simple_enabled = self.simple_mode.isChecked()
        advanced_enabled = self.advanced_mode.isChecked()
        
        self.simple_config_group.setVisible(simple_enabled)
        self.advanced_config_group.setVisible(advanced_enabled)
        
        # Ensure a mode is always selected
        if not simple_enabled and not advanced_enabled:
            self.simple_mode.setChecked(True)

    def update_simple_crf_display(self, value):
        """Update CRF display in simple mode."""
        quality_text, color = self.get_quality_info(value)
        self.crf_display_simple.setText(f"{value} - {quality_text}")
        self.crf_display_simple.setStyleSheet(f"font-weight: bold; color: {color};")

    def update_simple_preset_info(self, preset):
        """Update preset info in simple mode."""
        text, color = self.get_preset_info(preset)
        self.preset_info_simple.setText(text)
        self.preset_info_simple.setStyleSheet(f"color: {color}; font-weight: bold;")

    def update_quality_label(self, label, crf_value):
        """Update quality label."""
        quality_text, color = self.get_quality_info(crf_value)
        label.setText(quality_text)
        label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def update_preset_label(self, label, preset):
        """Update preset info label."""
        text, color = self.get_preset_info(preset)
        label.setText(text.split(' - ')[0])  # Only take the part before the dash
        label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def update_time_estimate(self, label, preset):
        """Update time estimation."""
        time_multipliers = {
            "ultrafast": "0.5x", "superfast": "0.7x", "veryfast": "0.8x", "faster": "0.9x",
            "fast": "1x", "medium": "1.5x", "slow": "2x", "slower": "3x", "veryslow": "4x"
        }
        
        multiplier = time_multipliers.get(preset, "1x")
        label.setText(f"⏱️ {multiplier}")
        label.setStyleSheet("color: #666; font-size: 11px;")

    def get_quality_info(self, crf):
        """Get quality information for a given CRF."""
        if crf <= 23:
            return "Très Haute Qualité", "#4CAF50"
        elif crf <= 28:
            return "Équilibré", "#2E86AB"
        elif crf <= 32:
            return "Compression Élevée", "#FF9800"
        else:
            return "Compression Maximale", "#f44336"

    def get_preset_info(self, preset):
        """Get information for a given preset."""
        preset_info = {
            "ultrafast": ("⚡⚡⚡ Ultra rapide", "#f44336"),
            "superfast": ("⚡⚡ Très rapide", "#FF9800"),
            "veryfast": ("⚡⚡ Rapide", "#FF9800"),
            "faster": ("⚡ Assez rapide", "#2E86AB"),
            "fast": ("⚡ Rapide", "#4CAF50"),
            "medium": ("⚖️ Équilibré", "#4CAF50"),
            "slow": ("🌀 Lent", "#2E86AB"),
            "slower": ("🌀🌀 Très lent", "#666"),
            "veryslow": ("🌀🌀🌀 Ultra lent", "#666")
        }
        return preset_info.get(preset, ("Inconnu", "#666"))

    def copy_attempt_config(self, source_attempt, target_attempt):
        """Copy configuration from one attempt to another."""
        if 1 <= source_attempt <= 3 and 1 <= target_attempt <= 3:
            source_idx = source_attempt - 1
            target_idx = target_attempt - 1
            
            source_widgets = self.attempts_widgets[source_idx]
            target_widgets = self.attempts_widgets[target_idx]
            
            # Copy CRF
            target_widgets['crf'].setValue(source_widgets['crf'].value())
            
            # Copy Preset
            target_widgets['preset'].setCurrentText(source_widgets['preset'].currentText())
            
            self.show_info_message(f"Configuration copiée de T{source_attempt} vers T{target_attempt}")

    def apply_attempts_preset(self, preset_type):
        """Apply a predefined preset to all 3 attempts."""
        presets = {
            "conservative": [
                (26, "fast"),
                (28, "medium"), 
                (30, "slow")
            ],
            "balanced": [
                (28, "fast"),
                (30, "medium"),
                (32, "slow")
            ],
            "aggressive": [
                (30, "medium"),
                (32, "slow"),
                (34, "veryslow")
            ]
        }
        
        if preset_type in presets:
            for i, (crf, preset) in enumerate(presets[preset_type]):
                self.attempts_widgets[i]['crf'].setValue(crf)
                self.attempts_widgets[i]['preset'].setCurrentText(preset)
            
            self.show_info_message(f"Preset '{preset_type}' appliqué aux 3 tentatives")

    def test_single_attempt(self, attempt_number):
        """Test a single compression attempt."""
        if hasattr(self.parent_window, 'test_specific_attempt'):
            self.parent_window.test_specific_attempt(attempt_number)
        else:
            self.show_info_message(f"Test of the tentative {attempt_number} - Fonctionnalité à implémenter")

    def toggle_attempts_availability(self, state):
        """Enable/disable availability of multiple attempts."""
        enabled = state == Qt.CheckState.Checked.value
        self.simple_config_group.setEnabled(enabled)
        self.advanced_config_group.setEnabled(enabled)
    
    def update_size_threshold_state(self, state):
        """Enable/disable size threshold controls."""
        enabled = state == Qt.CheckState.Checked.value
        self.size_slider.setEnabled(enabled)
        self.size_display.setEnabled(enabled)
    
    def update_failed_options_state(self, state):
        """Enable/disable non-compressible file options."""
        enabled = state == Qt.CheckState.Checked.value
        self.failed_suffix.setEnabled(enabled)
        self.ignore_non_compressible.setEnabled(enabled)
    
    def manage_file_action_conflicts(self):
        """Manage conflicts between file management options."""
        sender = self.sender()
        
        if sender == self.keep_both and self.keep_both.isChecked():
            self.replace_original.setChecked(False)
            self.delete_if_smaller.setChecked(False)
        elif sender == self.replace_original and self.replace_original.isChecked():
            self.keep_both.setChecked(False)
            self.delete_if_smaller.setChecked(False)
        elif sender == self.delete_if_smaller and self.delete_if_smaller.isChecked():
            self.keep_both.setChecked(False)
            self.replace_original.setChecked(False)
    
    def apply_preset(self, preset_name):
        """Apply a predefined preset."""
        if "Débutant" in preset_name:
            # Beginner mode - safe settings
            self.crf_slider_simple.setValue(28)
            self.preset_simple.setCurrentText("fast")
            self.enable_multiple_attempts.setChecked(True)
            self.use_size_threshold.setChecked(True)
            self.size_slider.setValue(500)
            self.keep_both.setChecked(True)
            
        elif "Rapide" in preset_name:
            # Fast mode - speed priority
            self.crf_slider_simple.setValue(30)
            self.preset_simple.setCurrentText("veryfast")
            self.enable_multiple_attempts.setChecked(False)
            self.use_size_threshold.setChecked(True)
            self.size_slider.setValue(200)
            
        elif "Équilibré" in preset_name:
            # Balanced mode - quality/speed compromise
            self.crf_slider_simple.setValue(28)
            self.preset_simple.setCurrentText("medium")
            self.enable_multiple_attempts.setChecked(True)
            self.use_size_threshold.setChecked(True)
            self.size_slider.setValue(500)
            
        elif "Compression Max" in preset_name:
            # Maximum compression mode
            self.crf_slider_simple.setValue(32)
            self.preset_simple.setCurrentText("slow")
            self.enable_multiple_attempts.setChecked(True)
            self.use_size_threshold.setChecked(False)
            
        # Expert = no changes, user configures manually
    
    # === ACTION METHODS ===

    def select_converted_files(self):
        """Select converted files in main window."""
        suffix = self.success_suffix.text().strip() or '_cvt'
        if hasattr(self.parent_window, 'select_files_by_suffix'):
            count = self.parent_window.select_files_by_suffix(suffix)
            self.show_info_message(f"{count} files convertis sélectionnés")
    
    def select_failed_files(self):
        """Select non-compressible files in main window."""
        suffix = self.failed_suffix.text().strip() or '_nocomp'
        if hasattr(self.parent_window, 'select_files_by_suffix'):
            count = self.parent_window.select_files_by_suffix(suffix)
            self.show_info_message(f"{count} files non-compressibles sélectionnés")
    
    def remove_converted_files(self):
        """Remove converted files from list."""
        suffix = self.success_suffix.text().strip() or '_cvt'
        if hasattr(self.parent_window, 'remove_files_by_suffix'):
            count = self.parent_window.remove_files_by_suffix(suffix)
            self.show_info_message(f"{count} files convertis supprimés de the list")
    
    def refresh_stats_display(self):
        """Load and display statistics."""
        try:
            from .stats import StatsManager
            stats_manager = StatsManager()
            summary = stats_manager.get_stats_summary()
            
            stats_text = f"""📈 Statistics de Conversion:
            
Conversions totales: {summary['total_conversions']}
Réussies: {summary['successful_conversions']} (Rate: {summary['success_rate']:.1f}%)
Échouées: {summary['failed_conversions']}

💾 Espace économisé: {self.format_size(summary['total_space_saved'])}
📉 Compression moyenne: {summary['average_compression']:.1f}%
🔄 Tentatives moyennes: {summary['average_attempts']:.1f}
            """
            self.stats_display.setText(stats_text.strip())
        except:
            self.stats_display.setText("📊 Aucune statistique disponible pour le moment.")
    
    def refresh_stats(self):
        """Refresh statistics display."""
        self.refresh_stats_display()
    
    def export_stats(self):
        """Export statistics to file."""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Exporter les statistics", 
                "statistiques_conversion.json", 
                "Fichiers JSON (*.json)"
            )
            
            if file_path:
                from .stats import StatsManager
                from pathlib import Path
                
                stats_manager = StatsManager()
                if stats_manager.export_stats(Path(file_path)):
                    self.show_info_message(f"Statistics exportées vers {file_path}")
                else:
                    self.show_error_message("Error during l'exportation")
                    
        except Exception as e:
            self.show_error_message(f"Error: {e}")
    
    def clear_stats(self):
        """Clear all statistics."""
        reply = QMessageBox.question(
            self, "Confirmer", 
            "Are you one you want effacer toutes les statistics ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from .stats import StatsManager
                stats_manager = StatsManager()
                if stats_manager.clear_stats():
                    self.refresh_stats_display()
                    self.show_info_message("Statistics effacées")
                else:
                    self.show_error_message("Error during l'effacement")
            except Exception as e:
                self.show_error_message(f"Error: {e}")
    
    def test_settings(self):
        """Test configuration on a single file."""
        # Save current settings
        self.apply_settings()
        
        # Ask main window to run a test
        if hasattr(self.parent_window, 'test_single_conversion'):
            self.parent_window.test_single_conversion()
            self.show_info_message("Test lancé - vérifiez la progression in the window principale")
        else:
            self.show_info_message("Fonction de test non disponible")
    
    def export_config(self):
        """Export current configuration."""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Exporter la configuration", 
                "config_video_converter.json", 
                "Fichiers JSON (*.json)"
            )
            
            if file_path:
                # Save current settings first
                self.save_current_settings()
                
                from .settings import SettingsManager
                from pathlib import Path
                
                if SettingsManager.export_settings(Path(file_path), self.settings):
                    self.show_info_message(f"Configuration exportée vers {file_path}")
                else:
                    self.show_error_message("Error during l'exportation")
                    
        except Exception as e:
            self.show_error_message(f"Error: {e}")
    
    def import_config(self):
        """Import configuration from file."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Importer une configuration", 
                "", "Fichiers JSON (*.json)"
            )
            
            if file_path:
                from .settings import SettingsManager
                from pathlib import Path
                
                new_settings = SettingsManager.import_settings(Path(file_path))
                self.settings = new_settings
                self.load_settings()
                self.show_info_message("Configuration importée with success")
                
        except Exception as e:
            self.show_error_message(f"Error during l'importation: {e}")
    
    def reset_config(self):
        """Reset configuration to default values."""
        reply = QMessageBox.question(
            self, "Confirmer", 
            "Réinitialiser tous les settings aux valeurs par défaut ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            from .settings import SettingsManager
            self.settings = SettingsManager.reset_settings()
            self.load_settings()
            self.show_info_message("Configuration réinitialisée")
    
    def accept_and_convert(self):
        """Accept and start conversion directly."""
        self.apply_settings()
        self.accept()
        
        # Signal main window to start conversion
        if hasattr(self.parent_window, 'start_conversion_after_settings'):
            self.parent_window.start_conversion_after_settings()
    
    def apply_settings(self):
        """Apply settings without closing dialog."""
        self.save_current_settings()
        
        from .settings import SettingsManager
        if SettingsManager.save_settings(self.settings):
            self.show_info_message("Settings sauvegardés")
            
            # Notify main window of change
            if hasattr(self.parent_window, 'on_settings_updated'):
                self.parent_window.on_settings_updated()
        else:
            self.show_error_message("Error saving")
    
    # === LOAD/SAVE METHODS ===

    def load_settings(self):
        """Load settings into interface."""
        try:
            # Onglet Détection
            self.use_size_threshold.setChecked(self.settings.use_size_threshold)
            
            size_mb = int(self.settings.size_threshold / (1024 * 1024))
            self.size_slider.setValue(size_mb)
            self.update_size_display(size_mb)
            
            # Video extensions
            extensions = getattr(self.settings, 'video_extensions', 'mp4,avi,mkv,mov,flv,webm,wmv')
            self.video_extensions.setText(extensions)
            
            # Suffixes
            self.success_suffix.setText(getattr(self.settings, 'converted_suffix', '_cvt'))
            self.failed_suffix.setText(getattr(self.settings, 'failed_suffix', '_nocomp'))
            
            # Options de files traités
            self.ignore_converted.setChecked(getattr(self.settings, 'ignore_converted_files', True))
            self.mark_non_compressible.setChecked(getattr(self.settings, 'mark_non_compressible', False))
            self.ignore_non_compressible.setChecked(getattr(self.settings, 'ignore_non_compressible', False))
            
            # Quality tab - Determine mode based on configuration
            if getattr(self.settings, 'manual_mode', False):
                # Mode simple
                self.simple_mode.setChecked(True)
                self.crf_slider_simple.setValue(self.settings.crf)
                self.preset_simple.setCurrentText(self.settings.preset)
                self.update_simple_crf_display(self.settings.crf)
                self.update_simple_preset_info(self.settings.preset)
            else:
                # Mode avancé
                self.advanced_mode.setChecked(True)
                
                # Load each attempt
                for i, widgets in enumerate(self.attempts_widgets):
                    if i < len(self.settings.attempts):
                        attempt = self.settings.attempts[i]
                        widgets['crf'].setValue(attempt.crf)
                        widgets['preset'].setCurrentText(attempt.preset)
            
            self.enable_multiple_attempts.setChecked(self.settings.multiple_attempts)
            self.max_threads.setValue(self.settings.max_concurrent_conversions)

            # Paramètres de taille cible
            self.use_target_size.setChecked(getattr(self.settings, 'use_target_size', False))
            target_size_mb = int(getattr(self.settings, 'target_size', 300 * 1024 * 1024) / (1024 * 1024))
            self.target_size_slider.setValue(target_size_mb)
            self.update_target_size_display(target_size_mb)
            self.max_compression_attempts.setValue(getattr(self.settings, 'max_compression_attempts', 5))
            self.initial_crf.setValue(getattr(self.settings, 'initial_crf', 28))
            self.crf_step.setValue(getattr(self.settings, 'crf_step', 2))
            self.max_crf.setValue(getattr(self.settings, 'max_crf', 40))

            self.toggle_compression_mode()
            self.toggle_target_size_mode()

            # Onglet Fichiers
            self.replace_original.setChecked(self.settings.replace_original)
            self.delete_if_smaller.setChecked(self.settings.delete_if_smaller)
            
            # If no option is checked, check "keep both"
            if not any([self.replace_original.isChecked(), self.delete_if_smaller.isChecked()]):
                self.keep_both.setChecked(True)
            
            # Onglet Avancé
            self.audio_copy.setChecked(getattr(self.settings, 'audio_copy', True))
            self.faststart.setChecked(getattr(self.settings, 'faststart', True))
            self.avoid_negative_ts.setChecked(getattr(self.settings, 'avoid_negative_ts', True))
            
        except Exception as e:
            self.show_error_message(f"Error loading des settings: {e}")
    
    def save_current_settings(self):
        """Save current settings from interface."""
        try:
            # Onglet Détection
            self.settings.use_size_threshold = self.use_size_threshold.isChecked()
            self.settings.size_threshold = self.size_slider.value() * 1024 * 1024
            
            # Extensions and suffixes
            self.settings.video_extensions = self.video_extensions.text().strip()
            self.settings.converted_suffix = self.success_suffix.text().strip() or '_cvt'
            self.settings.failed_suffix = self.failed_suffix.text().strip() or '_nocomp'
            
            # Options de files traités
            self.settings.ignore_converted_files = self.ignore_converted.isChecked()
            self.settings.mark_non_compressible = self.mark_non_compressible.isChecked()
            self.settings.ignore_non_compressible = self.ignore_non_compressible.isChecked()
            
            # Quality tab
            if self.simple_mode.isChecked():
                # Simple mode - use same config for all attempts
                crf = self.crf_slider_simple.value()
                preset = self.preset_simple.currentText()
                
                for attempt in self.settings.attempts:
                    attempt.crf = crf
                    attempt.preset = preset
                    
                self.settings.manual_mode = True
                self.settings.crf = crf
                self.settings.preset = preset
                
            else:
                # Advanced mode - configure each attempt individually
                for i, widgets in enumerate(self.attempts_widgets):
                    if i < len(self.settings.attempts):
                        self.settings.attempts[i].crf = widgets['crf'].value()
                        self.settings.attempts[i].preset = widgets['preset'].currentText()
                
                self.settings.manual_mode = False
            
            self.settings.multiple_attempts = self.enable_multiple_attempts.isChecked()
            self.settings.max_concurrent_conversions = self.max_threads.value()

            # Paramètres de taille cible
            self.settings.use_target_size = self.use_target_size.isChecked()
            self.settings.target_size = self.target_size_slider.value() * 1024 * 1024
            self.settings.max_compression_attempts = self.max_compression_attempts.value()
            self.settings.initial_crf = self.initial_crf.value()
            self.settings.crf_step = self.crf_step.value()
            self.settings.max_crf = self.max_crf.value()

            # Onglet Fichiers
            self.settings.replace_original = self.replace_original.isChecked()
            self.settings.delete_if_smaller = self.delete_if_smaller.isChecked()
            
            # Onglet Avancé
            self.settings.audio_copy = self.audio_copy.isChecked()
            self.settings.faststart = self.faststart.isChecked()
            self.settings.avoid_negative_ts = self.avoid_negative_ts.isChecked()
            
        except Exception as e:
            self.show_error_message(f"Error saving des settings: {e}")
    
    # === UTILITY METHODS ===

    def format_size(self, size: int) -> str:
        """Format file size."""
        if size < 1024:
            return f"{size} B"
        elif size < 1048576:
            return f"{size/1024:.1f} KB"
        elif size < 1073741824:
            return f"{size/1048576:.1f} MB"
        else:
            return f"{size/1073741824:.1f} GB"
    
    def show_info_message(self, message: str):
        """Show information message."""
        QMessageBox.information(self, "Information", message)
    
    def show_error_message(self, message: str):
        """Show error message."""
        QMessageBox.warning(self, "Error", message)
