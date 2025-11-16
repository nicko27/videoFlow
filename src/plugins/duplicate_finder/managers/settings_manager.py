"""
Settings management for the duplicate finder application.

This module handles loading, saving, and managing application settings
using Qt's QSettings for persistent storage.
"""
from typing import Dict, Any, Optional
from PyQt6.QtCore import QSettings, QObject, pyqtSignal
from PyQt6.QtWidgets import QSpinBox, QDoubleSpinBox

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.SettingsManager')


class SettingsManager(QObject):
    """
    Manager for application settings persistence.

    This class handles loading and saving user preferences, window geometry,
    and analysis parameters. It provides a centralized interface for settings
    management with automatic saving capabilities.

    Attributes:
        settings_changed (pyqtSignal): Signal emitted when settings are modified.

    Example:
        ```python
        manager = SettingsManager()
        manager.load_settings(widgets)
        # ... user modifies settings ...
        manager.save_settings(widgets)
        ```
    """

    settings_changed = pyqtSignal()

    def __init__(
        self,
        organization: str = "DuplicateFinder",
        application: str = "VideoDeduplicator"
    ) -> None:
        """
        Initialize the settings manager.

        Args:
            organization: Organization name for settings storage.
            application: Application name for settings storage.
        """
        super().__init__()
        self.settings = QSettings(organization, application)
        self._loading = False
        logger.info(f"Settings manager initialized: {organization}/{application}")

    def load_settings(self, widgets: Dict[str, Any], main_window=None) -> None:
        """
        Load saved settings and apply them to widgets.

        This method loads all saved parameters and window geometry,
        applying them to the provided widgets. Signals are blocked during
        loading to prevent triggering save operations.

        Args:
            widgets: Dictionary mapping widget names to widget instances.
                Expected keys: 'threshold_spin', 'hash_workers_spin',
                'comparison_workers_spin', 'batch_size_spin',
                'hash_timeout_spin', 'comparison_timeout_spin'
            main_window: Optional main window instance for geometry restoration.
        """
        try:
            self._loading = True
            self._block_widget_signals(widgets, True)

            # Load parameter settings
            self.settings.beginGroup("parameters")

            self._load_widget_value(
                widgets, 'threshold_spin', 'threshold', 90.0, float
            )

            # Load hash method (combobox)
            if 'hash_method_combo' in widgets and widgets['hash_method_combo'] is not None:
                hash_method = self.settings.value('hash_method', 'pHash', type=str)
                combo = widgets['hash_method_combo']
                # Find and set the index for the saved method
                for i in range(combo.count()):
                    if combo.itemData(i) == hash_method:
                        combo.setCurrentIndex(i)
                        break

            self._load_widget_value(
                widgets, 'hash_workers_spin', 'hash_workers', 2, int
            )
            self._load_widget_value(
                widgets, 'comparison_workers_spin', 'comparison_workers', 4, int
            )
            self._load_widget_value(
                widgets, 'batch_size_spin', 'batch_size', 50, int
            )

            # Load comparison algorithm (combobox)
            if 'comparison_algorithm_combo' in widgets and widgets['comparison_algorithm_combo'] is not None:
                algorithm = self.settings.value('comparison_algorithm', 'balltree', type=str)
                combo = widgets['comparison_algorithm_combo']
                for i in range(combo.count()):
                    if combo.itemData(i) == algorithm:
                        combo.setCurrentIndex(i)
                        break

            self._load_widget_value(
                widgets, 'hash_timeout_spin', 'hash_timeout', 120, int
            )
            self._load_widget_value(
                widgets, 'comparison_timeout_spin', 'comparison_timeout', 30, int
            )

            self.settings.endGroup()

            # Load scene detection settings
            self.settings.beginGroup("scene_detection")

            self._load_widget_value(
                widgets, 'scene_min_match_spin', 'min_match_ratio', 85.0, float
            )
            self._load_widget_value(
                widgets, 'scene_min_duration_spin', 'min_duration', 10, int
            )
            self._load_widget_value(
                widgets, 'scene_cache_size_spin', 'cache_size', 500, int
            )

            # Load precision mode (combobox)
            if 'scene_precision_combo' in widgets and widgets['scene_precision_combo'] is not None:
                precision = self.settings.value('precision_mode', 'balanced', type=str)
                combo = widgets['scene_precision_combo']
                # Find and set the correct index
                for i in range(combo.count()):
                    if combo.itemData(i) == precision:
                        combo.setCurrentIndex(i)
                        break

            # Load checkbox state
            if 'enable_scene_check' in widgets and widgets['enable_scene_check'] is not None:
                enabled = self.settings.value('enabled', False, type=bool)
                widgets['enable_scene_check'].setChecked(enabled)

            self.settings.endGroup()

            # Load window geometry if main window provided
            if main_window:
                self._load_window_geometry(main_window)

            logger.info("Settings loaded successfully")

        except Exception as e:
            logger.error(f"Error loading settings: {e}")
        finally:
            self._block_widget_signals(widgets, False)
            self._loading = False

    def save_settings(self, widgets: Dict[str, Any], main_window=None) -> None:
        """
        Save current settings from widgets.

        Args:
            widgets: Dictionary mapping widget names to widget instances.
            main_window: Optional main window instance for geometry saving.
        """
        try:
            # Parameter settings
            self.settings.beginGroup("parameters")

            self._save_widget_value(widgets, 'threshold_spin', 'threshold')

            # Save hash method (combobox)
            if 'hash_method_combo' in widgets and widgets['hash_method_combo'] is not None:
                combo = widgets['hash_method_combo']
                hash_method = combo.currentData()
                if hash_method:
                    self.settings.setValue('hash_method', hash_method)

            self._save_widget_value(widgets, 'hash_workers_spin', 'hash_workers')
            self._save_widget_value(widgets, 'comparison_workers_spin', 'comparison_workers')
            self._save_widget_value(widgets, 'batch_size_spin', 'batch_size')

            # Save comparison algorithm (combobox)
            if 'comparison_algorithm_combo' in widgets and widgets['comparison_algorithm_combo'] is not None:
                combo = widgets['comparison_algorithm_combo']
                algorithm = combo.currentData()
                if algorithm:
                    self.settings.setValue('comparison_algorithm', algorithm)

            self._save_widget_value(widgets, 'hash_timeout_spin', 'hash_timeout')
            self._save_widget_value(widgets, 'comparison_timeout_spin', 'comparison_timeout')

            self.settings.endGroup()

            # Scene detection settings
            self.settings.beginGroup("scene_detection")

            self._save_widget_value(widgets, 'scene_min_match_spin', 'min_match_ratio')
            self._save_widget_value(widgets, 'scene_min_duration_spin', 'min_duration')
            self._save_widget_value(widgets, 'scene_cache_size_spin', 'cache_size')

            # Save precision mode (combobox)
            if 'scene_precision_combo' in widgets and widgets['scene_precision_combo'] is not None:
                precision = widgets['scene_precision_combo'].currentData()
                self.settings.setValue('precision_mode', precision)

            # Save checkbox state
            if 'enable_scene_check' in widgets and widgets['enable_scene_check'] is not None:
                self.settings.setValue('enabled', widgets['enable_scene_check'].isChecked())

            self.settings.endGroup()

            # Window geometry
            if main_window:
                self._save_window_geometry(main_window)

            # Force synchronization to disk
            self.settings.sync()

            logger.debug("Settings saved successfully")

        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def _load_widget_value(
        self,
        widgets: Dict[str, Any],
        widget_name: str,
        setting_key: str,
        default_value: Any,
        value_type: type
    ) -> None:
        """
        Load a single widget value from settings.

        Args:
            widgets: Widget dictionary.
            widget_name: Name of the widget in the dictionary.
            setting_key: Key for the setting in QSettings.
            default_value: Default value if setting not found.
            value_type: Type to cast the value to (int or float).
        """
        if widget_name in widgets and widgets[widget_name] is not None:
            value = self.settings.value(setting_key, default_value, type=value_type)
            widgets[widget_name].setValue(value)

    def _save_widget_value(
        self,
        widgets: Dict[str, Any],
        widget_name: str,
        setting_key: str
    ) -> None:
        """
        Save a single widget value to settings.

        Args:
            widgets: Widget dictionary.
            widget_name: Name of the widget in the dictionary.
            setting_key: Key for the setting in QSettings.
        """
        if widget_name in widgets and widgets[widget_name] is not None:
            self.settings.setValue(setting_key, widgets[widget_name].value())

    def _load_window_geometry(self, main_window) -> None:
        """
        Restore window geometry and state.

        Args:
            main_window: Main window instance.
        """
        self.settings.beginGroup("window")

        geometry = self.settings.value("geometry")
        if geometry:
            main_window.restoreGeometry(geometry)

        state = self.settings.value("state")
        if state:
            main_window.restoreState(state)

        self.settings.endGroup()

    def _save_window_geometry(self, main_window) -> None:
        """
        Save window geometry and state.

        Args:
            main_window: Main window instance.
        """
        self.settings.beginGroup("window")
        self.settings.setValue("geometry", main_window.saveGeometry())
        self.settings.setValue("state", main_window.saveState())
        self.settings.endGroup()

    def _block_widget_signals(self, widgets: Dict[str, Any], block: bool) -> None:
        """
        Block or unblock signals for all setting widgets.

        This prevents triggering save operations during loading.

        Args:
            widgets: Dictionary of widgets.
            block: True to block signals, False to unblock.
        """
        widget_names = [
            'threshold_spin', 'hash_workers_spin', 'comparison_workers_spin',
            'batch_size_spin', 'hash_timeout_spin', 'comparison_timeout_spin',
            'scene_min_match_spin', 'scene_min_duration_spin',
            'scene_cache_size_spin', 'scene_precision_combo', 'enable_scene_check'
        ]

        for widget_name in widget_names:
            if widget_name in widgets and widgets[widget_name] is not None:
                widgets[widget_name].blockSignals(block)

    def apply_preset(
        self,
        preset_type: str,
        widgets: Dict[str, Any]
    ) -> str:
        """
        Apply a predefined settings preset.

        Args:
            preset_type: Type of preset ('fast', 'balanced', or 'quality').
            widgets: Dictionary of setting widgets.

        Returns:
            Confirmation message describing the applied preset.
        """
        try:
            # Block signals during preset application
            self._block_widget_signals(widgets, True)

            if preset_type == "fast":
                self._set_widget_value(widgets, 'threshold_spin', 85.0)
                self._set_widget_value(widgets, 'hash_workers_spin', 4)
                self._set_widget_value(widgets, 'comparison_workers_spin', 6)
                self._set_widget_value(widgets, 'batch_size_spin', 100)
                self._set_widget_value(widgets, 'hash_timeout_spin', 60)
                self._set_widget_value(widgets, 'comparison_timeout_spin', 15)
                message = "Preset RAPIDE applied and saved"

            elif preset_type == "balanced":
                self._set_widget_value(widgets, 'threshold_spin', 90.0)
                self._set_widget_value(widgets, 'hash_workers_spin', 2)
                self._set_widget_value(widgets, 'comparison_workers_spin', 4)
                self._set_widget_value(widgets, 'batch_size_spin', 50)
                self._set_widget_value(widgets, 'hash_timeout_spin', 120)
                self._set_widget_value(widgets, 'comparison_timeout_spin', 30)
                message = "Preset BALANCED applied and saved"

            elif preset_type == "quality":
                self._set_widget_value(widgets, 'threshold_spin', 95.0)
                self._set_widget_value(widgets, 'hash_workers_spin', 1)
                self._set_widget_value(widgets, 'comparison_workers_spin', 2)
                self._set_widget_value(widgets, 'batch_size_spin', 20)
                self._set_widget_value(widgets, 'hash_timeout_spin', 300)
                self._set_widget_value(widgets, 'comparison_timeout_spin', 60)
                message = "Preset QUALITY applied and saved"
            else:
                message = f"Unknown preset: {preset_type}"

            # Unblock signals
            self._block_widget_signals(widgets, False)

            # Save settings after preset application
            self.save_settings(widgets)

            logger.info(f"Preset '{preset_type}' applied")
            return message

        except Exception as e:
            logger.error(f"Error applying preset {preset_type}: {e}")
            self._block_widget_signals(widgets, False)
            return f"Error applying preset: {e}"

    def _set_widget_value(
        self,
        widgets: Dict[str, Any],
        widget_name: str,
        value: Any
    ) -> None:
        """
        Set a widget value if the widget exists.

        Args:
            widgets: Widget dictionary.
            widget_name: Name of the widget.
            value: Value to set.
        """
        if widget_name in widgets and widgets[widget_name] is not None:
            widgets[widget_name].setValue(value)

    def get_analysis_config(self, widgets: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get current analysis configuration from widgets.

        Args:
            widgets: Dictionary of setting widgets.

        Returns:
            Dictionary with analysis configuration parameters.
        """
        config = {
            'threshold': widgets['threshold_spin'].value(),
            'hash_workers': widgets['hash_workers_spin'].value(),
            'comparison_workers': widgets['comparison_workers_spin'].value(),
            'batch_size': widgets['batch_size_spin'].value(),
            'hash_timeout': widgets['hash_timeout_spin'].value(),
            'comparison_timeout': widgets['comparison_timeout_spin'].value(),
            'comparison_algorithm': 'balltree'  # Default
        }

        # Get comparison algorithm if widget exists
        if 'comparison_algorithm_combo' in widgets and widgets['comparison_algorithm_combo'] is not None:
            algorithm = widgets['comparison_algorithm_combo'].currentData()
            if algorithm:
                config['comparison_algorithm'] = algorithm

        # Add scene detection config if widgets exist
        if 'enable_scene_check' in widgets and widgets['enable_scene_check'] is not None:
            # Get enabled status
            enabled = widgets['enable_scene_check'].isChecked()

            # Get actual widget values (with defaults matching UI)
            min_match_ratio = 0.85  # Default 85% from UI
            min_duration = 10  # Default 10 seconds from UI
            cache_size = 500  # Default from UI
            precision_mode = 'balanced'  # Default from UI

            # Override with actual widget values if available
            if 'scene_min_match_spin' in widgets and widgets['scene_min_match_spin'] is not None:
                min_match_ratio = widgets['scene_min_match_spin'].value() / 100.0  # Convert percentage to ratio

            if 'scene_min_duration_spin' in widgets and widgets['scene_min_duration_spin'] is not None:
                min_duration = widgets['scene_min_duration_spin'].value()

            if 'scene_cache_size_spin' in widgets and widgets['scene_cache_size_spin'] is not None:
                cache_size = widgets['scene_cache_size_spin'].value()

            if 'scene_precision_combo' in widgets and widgets['scene_precision_combo'] is not None:
                precision_mode = widgets['scene_precision_combo'].currentData() or 'balanced'

            config['scene_detection'] = {
                'enabled': enabled,
                'precision_mode': precision_mode,
                'min_match_ratio': min_match_ratio,
                'min_duration': min_duration,
                'cache_size': cache_size
            }

        return config

    def is_loading(self) -> bool:
        """
        Check if settings are currently being loaded.

        Returns:
            True if loading is in progress, False otherwise.
        """
        return self._loading

    def save_last_folder(self, folder_path: str) -> None:
        """
        Save the last opened folder path.

        Args:
            folder_path: Path to the folder to save.
        """
        try:
            self.settings.beginGroup("recent")
            self.settings.setValue("last_folder", folder_path)
            self.settings.endGroup()
            self.settings.sync()
            logger.debug(f"Last folder saved: {folder_path}")
        except Exception as e:
            logger.error(f"Error saving last folder: {e}")

    def get_last_folder(self) -> Optional[str]:
        """
        Get the last opened folder path.

        Returns:
            Path to the last folder, or None if not set.
        """
        try:
            self.settings.beginGroup("recent")
            last_folder = self.settings.value("last_folder", None, type=str)
            self.settings.endGroup()
            return last_folder
        except Exception as e:
            logger.error(f"Error getting last folder: {e}")
            return None

    def save_layout_preference(self, layout_key: str) -> None:
        """
        Save the selected layout preference.

        Args:
            layout_key: Key of the selected layout (e.g., 'classic', 'vertical', 'dashboard').
        """
        try:
            self.settings.beginGroup("ui")
            self.settings.setValue("layout", layout_key)
            self.settings.endGroup()
            self.settings.sync()
            logger.debug(f"Layout preference saved: {layout_key}")
        except Exception as e:
            logger.error(f"Error saving layout preference: {e}")

    def get_layout_preference(self) -> str:
        """
        Get the saved layout preference.

        Returns:
            Layout key string, defaults to 'classic' if not set.
        """
        try:
            self.settings.beginGroup("ui")
            layout = self.settings.value("layout", "classic", type=str)
            self.settings.endGroup()
            return layout
        except Exception as e:
            logger.error(f"Error getting layout preference: {e}")
            return "classic"

    def save_last_folder(self, folder_path: str) -> None:
        """
        Save the last used folder path.

        Args:
            folder_path: Path to the folder to remember.
        """
        try:
            self.settings.beginGroup("ui")
            self.settings.setValue("last_folder", folder_path)
            self.settings.endGroup()
            self.settings.sync()
            logger.debug(f"Last folder saved: {folder_path}")
        except Exception as e:
            logger.error(f"Error saving last folder: {e}")

    def get_last_folder(self) -> str:
        """
        Get the last used folder path.

        Returns:
            Last folder path string, or empty string if not set or doesn't exist.
        """
        try:
            import os
            self.settings.beginGroup("ui")
            folder = self.settings.value("last_folder", "", type=str)
            self.settings.endGroup()

            # Check if folder still exists
            if folder and os.path.exists(folder):
                return folder
            else:
                # Folder doesn't exist anymore, clear it
                if folder:
                    logger.debug(f"Last folder no longer exists: {folder}")
                    self.reset_last_folder()
                return ""
        except Exception as e:
            logger.error(f"Error getting last folder: {e}")
            return ""

    def reset_last_folder(self) -> None:
        """
        Reset (clear) the last used folder path.
        """
        try:
            self.settings.beginGroup("ui")
            self.settings.remove("last_folder")
            self.settings.endGroup()
            self.settings.sync()
            logger.debug("Last folder reset")
        except Exception as e:
            logger.error(f"Error resetting last folder: {e}")
