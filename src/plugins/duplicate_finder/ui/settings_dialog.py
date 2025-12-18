"""
Settings Dialog - Unified settings configuration window.

Provides a tabbed interface for configuring all application settings
using the UnifiedConfigManager.
"""
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QComboBox,
    QCheckBox, QGroupBox, QFormLayout, QMessageBox, QFileDialog, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from src.core.logger import Logger

try:
    from ..orchestration.unified_config_manager import (
        UnifiedConfigManager, UnifiedConfig,
        VideoHashingConfig, ComparisonConfig,
        CacheConfig, SubsequenceConfig
    )
    from ..infrastructure.config.profile_manager import ProfileManager, get_profile_manager
    from ..data import DatabaseManager
except ImportError:
    from ..orchestration.unified_config_manager import (
        UnifiedConfigManager, UnifiedConfig,
        VideoHashingConfig, ComparisonConfig,
        CacheConfig, SubsequenceConfig
    )
    from ..infrastructure.config.profile_manager import ProfileManager, get_profile_manager
    from ..data import DatabaseManager

logger = Logger.get_logger('DuplicateFinder.SettingsDialog')


class SettingsDialog(QDialog):
    """
    Unified settings dialog with tabbed configuration.

    Provides a comprehensive settings interface organized into tabs:
    - Hashing: Video hashing configuration
    - Comparison: Comparison algorithm settings
    - Audio-First: Audio-first analysis settings
    - Cache: Cache size configuration
    - Subsequence: Subsequence detection settings

    Signals:
        settings_changed: Emitted when settings are applied (passes UnifiedConfig)
    """

    settings_changed = pyqtSignal(object)  # UnifiedConfig

    def __init__(self, config_manager: UnifiedConfigManager, parent: Optional[QWidget] = None):
        """
        Initialize settings dialog.

        Args:
            config_manager: UnifiedConfigManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.profile_manager = get_profile_manager()
        self.current_config: Optional[UnifiedConfig] = None

        self.setWindowTitle("Settings")
        self.setMinimumSize(700, 600)
        self.setModal(True)

        self._init_ui()
        self._load_current_config()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Application Settings")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Profile selector group
        profile_group = QGroupBox("Configuration Profiles")
        profile_layout = QHBoxLayout()

        profile_layout.addWidget(QLabel("Load Preset:"))

        self.profile_combo = QComboBox()
        self.profile_combo.addItem("-- Select a profile --", None)
        for profile in self.profile_manager.get_all_profiles():
            icon = "⚙️" if profile.is_builtin else "💾"
            self.profile_combo.addItem(f"{icon} {profile.name}", profile.name)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        profile_layout.addWidget(self.profile_combo, 1)

        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self._load_selected_profile)
        profile_layout.addWidget(load_btn)

        save_btn = QPushButton("Save As...")
        save_btn.clicked.connect(self._save_custom_profile)
        profile_layout.addWidget(save_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_custom_profile)
        profile_layout.addWidget(delete_btn)

        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)

        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create tabs
        self.hashing_tab = self._create_hashing_tab()
        self.comparison_tab = self._create_comparison_tab()
        # Audio-first tab removed - functionality replaced by DuplicateFlow pipelines
        self.cache_tab = self._create_cache_tab()
        self.subsequence_tab = self._create_subsequence_tab()

        self.tabs.addTab(self.hashing_tab, "Hashing")
        self.tabs.addTab(self.comparison_tab, "Comparison")
        # self.tabs.addTab(self.audio_first_tab, "Audio-First")  # Deprecated
        self.tabs.addTab(self.cache_tab, "Cache")
        self.tabs.addTab(self.subsequence_tab, "Subsequence")

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Import/Export buttons
        import_btn = QPushButton("Import...")
        import_btn.clicked.connect(self._import_config)
        button_layout.addWidget(import_btn)

        export_btn = QPushButton("Export...")
        export_btn.clicked.connect(self._export_config)
        button_layout.addWidget(export_btn)

        button_layout.addStretch()

        # Apply/Cancel buttons
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply_settings)
        apply_btn.setDefault(True)
        button_layout.addWidget(apply_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        # Sync slider/combo with current config
        self._sync_threshold_controls()

    def _on_clear_hashes(self):
        """Purge tous les hashs/signatures/caches stockés en base."""
        confirm = QMessageBox.question(
            self,
            "Purge des hashs",
            "Supprimer tous les hashs vidéo, signatures et caches de vérification ?\n"
            "Cette opération peut être longue sur une grosse base.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.clear_hashes_btn.setEnabled(False)
        try:
            db = DatabaseManager()
            db.clear_verification_cache()
            db.clear_method_signatures()
            db.clear_hash_caches()
            db.close()
            QMessageBox.information(
                self,
                "Caches purgés",
                "Tous les hashs, signatures et caches de vérification ont été supprimés."
            )
        except Exception as e:
            logger.error(f"Erreur lors de la purge des hashs: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Erreur",
                f"Echec de la purge des hashs/caches : {e}"
            )
        finally:
            self.clear_hashes_btn.setEnabled(True)

    def _create_hashing_tab(self) -> QWidget:
        """Create the hashing configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Hashing group
        group = QGroupBox("Video Hashing Configuration")
        form = QFormLayout()

        # Hash method
        self.hash_method_combo = QComboBox()
        self.hash_method_combo.addItem("pHash (Perceptual)", "pHash")
        self.hash_method_combo.addItem("dHash (Difference)", "dHash")
        self.hash_method_combo.addItem("aHash (Average)", "aHash")
        self.hash_method_combo.addItem("wHash (Wavelet)", "wHash")
        self.hash_method_combo.setToolTip("Choix du type de hash vidéo (pHash = le plus robuste, aHash = le plus rapide).")
        form.addRow("Hash Method:", self.hash_method_combo)

        # Workers
        self.hash_workers_spin = QSpinBox()
        self.hash_workers_spin.setRange(1, 32)
        self.hash_workers_spin.setSuffix(" workers")
        self.hash_workers_spin.setToolTip("Nombre de workers en parallèle pour le hachage (plus haut = plus rapide, plus de CPU).")
        form.addRow("Parallel Workers:", self.hash_workers_spin)

        # Timeout
        self.hash_timeout_spin = QSpinBox()
        self.hash_timeout_spin.setRange(10, 300)
        self.hash_timeout_spin.setSuffix(" seconds")
        self.hash_timeout_spin.setToolTip("Temps maximal pour le hachage d'une vidéo (secondes).")
        form.addRow("Timeout:", self.hash_timeout_spin)

        # Frame sampling
        self.frame_sampling_spin = QSpinBox()
        self.frame_sampling_spin.setRange(1, 100)
        self.frame_sampling_spin.setSuffix(" frames")
        self.frame_sampling_spin.setToolTip("Échantillonne une frame toutes les N frames (plus petit = plus précis, plus lent).")
        form.addRow("Frame Sampling:", self.frame_sampling_spin)

        # Bouton de purge des caches/hash
        self.clear_hashes_btn = QPushButton("Purger les hashs / caches")
        self.clear_hashes_btn.setToolTip("Supprime les hashs vidéo, signatures et caches de vérification (DB).")
        self.clear_hashes_btn.clicked.connect(self._on_clear_hashes)
        form.addRow(self.clear_hashes_btn)

        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()

        return widget

    def _sync_threshold_controls(self):
        """Synchronise spin/slider/strictness combo."""
        val = self.threshold_spin.value()
        self.threshold_slider.blockSignals(True)
        self.threshold_slider.setValue(int(val * 100))
        self.threshold_slider.blockSignals(False)
        # Try to match preset
        preset_map = {0.55: 0, 0.70: 1, 0.85: 2}
        if val in preset_map:
            self.strictness_combo.setCurrentIndex(preset_map[val])
        else:
            self.strictness_combo.setCurrentIndex(self.strictness_combo.count() - 1)

    def _create_comparison_tab(self) -> QWidget:
        """Create the comparison configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Comparison group
        group = QGroupBox("Comparison Configuration")
        form = QFormLayout()

        # Threshold
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.0, 1.0)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setToolTip("Seuil global de similarité (0-1). Plus haut = plus strict.")
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setSingleStep(1)
        self.threshold_slider.setToolTip("Glissez pour régler rapidement (valeur = pourcentage).")
        self.threshold_slider.valueChanged.connect(self._on_threshold_slider_changed)
        self.threshold_spin.valueChanged.connect(self._on_threshold_spin_changed)
        # Strictness presets
        self.strictness_combo = QComboBox()
        self.strictness_combo.addItem("Rapide (permissif)", 0.55)
        self.strictness_combo.addItem("Équilibré", 0.70)
        self.strictness_combo.addItem("Strict", 0.85)
        self.strictness_combo.addItem("Personnalisé", None)
        self.strictness_combo.currentIndexChanged.connect(self._on_strictness_changed)

        th_layout = QHBoxLayout()
        th_layout.addWidget(self.threshold_spin)
        th_layout.addWidget(self.threshold_slider)
        th_layout.addWidget(self.strictness_combo)
        form.addRow("Similarity Threshold:", th_layout)

        # Workers
        self.comparison_workers_spin = QSpinBox()
        self.comparison_workers_spin.setRange(1, 32)
        self.comparison_workers_spin.setSuffix(" workers")
        self.comparison_workers_spin.setToolTip("Workers en parallèle pour les comparaisons (CPU).")
        form.addRow("Parallel Workers:", self.comparison_workers_spin)

        # Batch size
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(10, 1000)
        self.batch_size_spin.setToolTip("Nombre de paires traitées par lot (mémoire vs vitesse).")
        form.addRow("Batch Size:", self.batch_size_spin)

        # Timeout
        self.comparison_timeout_spin = QSpinBox()
        self.comparison_timeout_spin.setRange(10, 300)
        self.comparison_timeout_spin.setSuffix(" seconds")
        self.comparison_timeout_spin.setToolTip("Timeout maximum pour une comparaison complète (secondes).")
        form.addRow("Timeout:", self.comparison_timeout_spin)

        # Options
        self.enable_metadata_filter = QCheckBox("Enable metadata pre-filtering")
        self.enable_metadata_filter.setToolTip("Filtre rapide par durée/taille pour éviter les comparaisons inutiles.")
        form.addRow("", self.enable_metadata_filter)

        self.enable_flip_detection = QCheckBox("Enable flip/mirror detection")
        self.enable_flip_detection.setToolTip("Détecte les vidéos retournées (miroir). Peut ajouter un léger coût.")
        form.addRow("", self.enable_flip_detection)

        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()

        return widget

    # Audio-first tab removed - functionality replaced by DuplicateFlow pipelines
    # def _create_audio_first_tab(self) -> QWidget:

    def _create_cache_tab(self) -> QWidget:
        """Create the cache configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Cache group
        group = QGroupBox("Cache Configuration")
        form = QFormLayout()

        # Frame cache
        self.frame_cache_size_spin = QSpinBox()
        self.frame_cache_size_spin.setRange(0, 10000)
        self.frame_cache_size_spin.setSuffix(" frames")
        form.addRow("Frame Cache Size:", self.frame_cache_size_spin)

        # Video cache
        self.video_cache_size_spin = QSpinBox()
        self.video_cache_size_spin.setRange(0, 1000)
        self.video_cache_size_spin.setSuffix(" videos")
        form.addRow("Video Cache Size:", self.video_cache_size_spin)

        # Audio cache
        self.audio_cache_size_spin = QSpinBox()
        self.audio_cache_size_spin.setRange(0, 1000)
        self.audio_cache_size_spin.setSuffix(" fingerprints")
        form.addRow("Audio Cache Size:", self.audio_cache_size_spin)

        # Comparison cache
        self.comparison_cache_size_spin = QSpinBox()
        self.comparison_cache_size_spin.setRange(0, 10000)
        self.comparison_cache_size_spin.setSuffix(" results")
        form.addRow("Comparison Cache Size:", self.comparison_cache_size_spin)

        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()

        return widget

    def _create_subsequence_tab(self) -> QWidget:
        """Create the subsequence detection configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Subsequence group
        group = QGroupBox("Subsequence Detection Configuration")
        form = QFormLayout()

        # Enable subsequence detection
        self.enable_subsequence = QCheckBox("Enable subsequence detection")
        form.addRow("", self.enable_subsequence)

        # Min subsequence length
        self.min_subsequence_length_spin = QSpinBox()
        self.min_subsequence_length_spin.setRange(1, 300)
        self.min_subsequence_length_spin.setSuffix(" seconds")
        form.addRow("Minimum Length:", self.min_subsequence_length_spin)

        # Detection threshold
        self.subsequence_threshold_spin = QDoubleSpinBox()
        self.subsequence_threshold_spin.setRange(0.0, 1.0)
        self.subsequence_threshold_spin.setSingleStep(0.05)
        self.subsequence_threshold_spin.setDecimals(2)
        form.addRow("Detection Threshold:", self.subsequence_threshold_spin)

        # Max gap
        self.max_gap_spin = QSpinBox()
        self.max_gap_spin.setRange(0, 60)
        self.max_gap_spin.setSuffix(" seconds")
        form.addRow("Maximum Gap:", self.max_gap_spin)

        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()

        return widget

    def _load_current_config(self):
        """Load current configuration into widgets."""
        try:
            self.current_config = self.config_manager.load()
            self._config_to_widgets(self.current_config)
            logger.info("Loaded current configuration")
            self._sync_threshold_controls()
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            QMessageBox.warning(
                self, "Warning",
                f"Could not load current configuration: {e}\n\nUsing defaults."
            )
            self.current_config = UnifiedConfig()
            self._config_to_widgets(self.current_config)
            self._sync_threshold_controls()

    def _config_to_widgets(self, config: UnifiedConfig):
        """
        Load configuration into widgets.

        Args:
            config: UnifiedConfig to load
        """
        # Hashing
        index = self.hash_method_combo.findData(config.hashing.hash_method)
        if index >= 0:
            self.hash_method_combo.setCurrentIndex(index)
        self.hash_workers_spin.setValue(config.hashing.hash_workers)
        self.hash_timeout_spin.setValue(config.hashing.hash_timeout)
        self.frame_sampling_spin.setValue(config.hashing.frame_sampling_rate)

        # Comparison
        self.threshold_spin.setValue(config.comparison.threshold)
        self.comparison_workers_spin.setValue(config.comparison.comparison_workers)
        self.batch_size_spin.setValue(config.comparison.batch_size)
        self.comparison_timeout_spin.setValue(config.comparison.comparison_timeout)
        self.enable_metadata_filter.setChecked(config.comparison.enable_metadata_filter)
        self.enable_flip_detection.setChecked(config.comparison.enable_flip_detection)

        # Audio-first removed - functionality replaced by DuplicateFlow pipelines

        # Cache
        self.frame_cache_size_spin.setValue(config.cache.frame_cache_size)
        self.video_cache_size_spin.setValue(config.cache.video_cache_size)
        self.audio_cache_size_spin.setValue(config.cache.audio_cache_size)
        self.comparison_cache_size_spin.setValue(config.cache.comparison_cache_size)

        # Subsequence
        self.enable_subsequence.setChecked(config.subsequence.enabled)
        self.min_subsequence_length_spin.setValue(config.subsequence.min_length)
        self.subsequence_threshold_spin.setValue(config.subsequence.threshold)
        self.max_gap_spin.setValue(config.subsequence.max_gap)

    def _widgets_to_config(self) -> UnifiedConfig:
        """
        Extract configuration from widgets.

        Returns:
            UnifiedConfig from widget values
        """
        return UnifiedConfig(
            hashing=VideoHashingConfig(
                hash_method=self.hash_method_combo.currentData(),
                hash_workers=self.hash_workers_spin.value(),
                hash_timeout=self.hash_timeout_spin.value(),
                frame_sampling_rate=self.frame_sampling_spin.value()
            ),
            comparison=ComparisonConfig(
                threshold=self.threshold_spin.value(),
                comparison_workers=self.comparison_workers_spin.value(),
                batch_size=self.batch_size_spin.value(),
                comparison_timeout=self.comparison_timeout_spin.value(),
                enable_metadata_filter=self.enable_metadata_filter.isChecked(),
                enable_flip_detection=self.enable_flip_detection.isChecked()
            ),
            # Audio-first removed - functionality replaced by DuplicateFlow pipelines
            # audio_first=AudioFirstConfig(...),
            cache=CacheConfig(
                frame_cache_size=self.frame_cache_size_spin.value(),
                video_cache_size=self.video_cache_size_spin.value(),
                audio_cache_size=self.audio_cache_size_spin.value(),
                comparison_cache_size=self.comparison_cache_size_spin.value()
            ),
            subsequence=SubsequenceConfig(
                enabled=self.enable_subsequence.isChecked(),
                min_length=self.min_subsequence_length_spin.value(),
                threshold=self.subsequence_threshold_spin.value(),
                max_gap=self.max_gap_spin.value()
            )
        )

    def _apply_settings(self):
        """Apply settings and close dialog."""
        try:
            # Get config from widgets
            new_config = self._widgets_to_config()

            # Save config
            self.config_manager.save(new_config)
            logger.info("Settings saved successfully")

            # Emit signal
            self.settings_changed.emit(new_config)

            # Close dialog
            self.accept()

        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Failed to save settings:\n{e}"
            )

    def _on_threshold_slider_changed(self, value: int):
        """Sync spin when slider moves."""
        self.threshold_spin.blockSignals(True)
        self.threshold_spin.setValue(value / 100.0)
        self.threshold_spin.blockSignals(False)
        # If slider moved manually, set preset to "Custom"
        self.strictness_combo.blockSignals(True)
        self.strictness_combo.setCurrentIndex(self.strictness_combo.count() - 1)
        self.strictness_combo.blockSignals(False)

    def _on_threshold_spin_changed(self, value: float):
        """Sync slider when spin changes."""
        self.threshold_slider.blockSignals(True)
        self.threshold_slider.setValue(int(value * 100))
        self.threshold_slider.blockSignals(False)

    def _on_strictness_changed(self, idx: int):
        """Apply preset threshold."""
        val = self.strictness_combo.currentData()
        if val is None:
            return
        self.threshold_spin.blockSignals(True)
        self.threshold_spin.setValue(val)
        self.threshold_spin.blockSignals(False)
        self.threshold_slider.blockSignals(True)
        self.threshold_slider.setValue(int(val * 100))
        self.threshold_slider.blockSignals(False)

    def _import_config(self):
        """Import configuration from JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Configuration",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            config = self.config_manager.import_json(file_path)
            self._config_to_widgets(config)
            logger.info(f"Imported configuration from: {file_path}")
            QMessageBox.information(
                self, "Success",
                "Configuration imported successfully"
            )
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Failed to import configuration:\n{e}"
            )

    def _export_config(self):
        """Export current configuration to JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Configuration",
            "duplicate_finder_config.json",
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Get current config from widgets
            current_config = self._widgets_to_config()

            # Export to file
            self.config_manager.export_json(current_config, file_path)
            logger.info(f"Exported configuration to: {file_path}")
            QMessageBox.information(
                self, "Success",
                f"Configuration exported to:\n{file_path}"
            )
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Failed to export configuration:\n{e}"
            )

    def _on_profile_selected(self, index: int):
        """Handle profile selection change in combo box."""
        # This just updates the combo box, actual loading happens on Load button
        pass

    def _load_selected_profile(self):
        """Load the selected profile."""
        profile_name = self.profile_combo.currentData()
        if not profile_name:
            QMessageBox.warning(self, "No Profile", "Please select a profile to load.")
            return

        try:
            config = self.profile_manager.load_profile(profile_name)
            if config:
                self._config_to_widgets(config)
                logger.info(f"Loaded profile: {profile_name}")
                QMessageBox.information(
                    self, "Profile Loaded",
                    f"Profile '{profile_name}' loaded successfully.\n\n"
                    f"Review the settings and click Apply to save them."
                )
            else:
                QMessageBox.warning(self, "Error", f"Profile '{profile_name}' not found.")
        except Exception as e:
            logger.error(f"Failed to load profile: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load profile:\n{e}")

    def _save_custom_profile(self):
        """Save current settings as a custom profile."""
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self, "Save Profile",
            "Enter a name for this profile:"
        )

        if not ok or not name:
            return

        # Check if name already exists
        if self.profile_manager.get_profile(name):
            reply = QMessageBox.question(
                self, "Profile Exists",
                f"Profile '{name}' already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        description, ok = QInputDialog.getText(
            self, "Profile Description",
            "Enter a description (optional):",
            text=f"Custom profile: {name}"
        )

        if not ok:
            description = f"Custom profile: {name}"

        try:
            config = self._widgets_to_config()
            success = self.profile_manager.save_profile(name, description, config)

            if success:
                # Refresh combo box
                self.profile_combo.clear()
                self.profile_combo.addItem("-- Select a profile --", None)
                for profile in self.profile_manager.get_all_profiles():
                    icon = "⚙️" if profile.is_builtin else "💾"
                    self.profile_combo.addItem(f"{icon} {profile.name}", profile.name)

                QMessageBox.information(
                    self, "Success",
                    f"Profile '{name}' saved successfully!"
                )
                logger.info(f"Saved custom profile: {name}")
            else:
                QMessageBox.warning(self, "Error", "Failed to save profile.")
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save profile:\n{e}")

    def _delete_custom_profile(self):
        """Delete the selected custom profile."""
        profile_name = self.profile_combo.currentData()
        if not profile_name:
            QMessageBox.warning(self, "No Profile", "Please select a profile to delete.")
            return

        profile = self.profile_manager.get_profile(profile_name)
        if not profile:
            QMessageBox.warning(self, "Not Found", f"Profile '{profile_name}' not found.")
            return

        if profile.is_builtin:
            QMessageBox.warning(
                self, "Cannot Delete",
                "Cannot delete built-in profiles."
            )
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete profile '{profile_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            success = self.profile_manager.delete_profile(profile_name)
            if success:
                # Refresh combo box
                self.profile_combo.clear()
                self.profile_combo.addItem("-- Select a profile --", None)
                for profile in self.profile_manager.get_all_profiles():
                    icon = "⚙️" if profile.is_builtin else "💾"
                    self.profile_combo.addItem(f"{icon} {profile.name}", profile.name)

                QMessageBox.information(
                    self, "Success",
                    f"Profile '{profile_name}' deleted successfully!"
                )
                logger.info(f"Deleted custom profile: {profile_name}")
            else:
                QMessageBox.warning(self, "Error", "Failed to delete profile.")
        except Exception as e:
            logger.error(f"Failed to delete profile: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete profile:\n{e}")

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when dialog is closed.

        Ensures proper cleanup of resources and signals.
        """
        # All signals are internal and auto-cleaned by Qt
        # Added for consistency with other dialogs
        super().closeEvent(event)
