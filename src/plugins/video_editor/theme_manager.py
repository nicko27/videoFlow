"""Theme manager for persisting and applying themes.

This module manages theme selection, persistence, and application
to the Video Editor UI.
"""

import json
import os
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import QApplication

from .themes import Theme, ThemeType, ThemePresets
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.ThemeManager')


class ThemeManager:
    """Manages themes for the Video Editor.

    Handles theme selection, persistence to disk, and application
    to the Qt application.

    Attributes:
        config_dir: Directory for storing theme configuration
        config_file: Path to theme configuration file
        current_theme: Currently active theme
    """

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize theme manager.

        Args:
            config_dir: Optional custom config directory.
                       If None, uses ~/.videoflow/
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".videoflow"

        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "theme_config.json"

        self.current_theme: Optional[Theme] = None
        self._load_theme()

    def _load_theme(self):
        """Load theme from configuration file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)

                # Load theme from saved data
                self.current_theme = Theme.from_dict(data)
                logger.info(f"Loaded theme: {self.current_theme.name}")
            else:
                # Use default light theme
                self.current_theme = ThemePresets.LIGHT_THEME
                logger.info("Using default light theme")

        except Exception as e:
            logger.error(f"Error loading theme: {e}")
            # Fallback to default light theme
            self.current_theme = ThemePresets.LIGHT_THEME

    def save_theme(self, theme: Optional[Theme] = None):
        """Save theme to configuration file.

        Args:
            theme: Theme to save. If None, saves current theme.
        """
        if theme:
            self.current_theme = theme

        if not self.current_theme:
            logger.warning("No theme to save")
            return

        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.current_theme.to_dict(), f, indent=2)

            logger.info(f"Saved theme: {self.current_theme.name}")

        except Exception as e:
            logger.error(f"Error saving theme: {e}")

    def apply_theme(self, theme: Optional[Theme] = None, app: Optional[QApplication] = None):
        """Apply theme to the application.

        Args:
            theme: Theme to apply. If None, applies current theme.
            app: QApplication instance. If None, uses QApplication.instance()
        """
        if theme:
            self.current_theme = theme
            self.save_theme()

        if not self.current_theme:
            logger.warning("No theme to apply")
            return

        # Get QApplication instance
        if not app:
            app = QApplication.instance()

        if not app:
            logger.warning("No QApplication instance found")
            return

        # Generate and apply stylesheet
        stylesheet = self.current_theme.get_stylesheet()
        app.setStyleSheet(stylesheet)

        logger.info(f"Applied theme: {self.current_theme.name}")

    def get_current_theme(self) -> Optional[Theme]:
        """Get the currently active theme.

        Returns:
            Current Theme or None
        """
        return self.current_theme

    def set_theme_by_name(self, theme_name: str, app: Optional[QApplication] = None):
        """Set theme by preset name.

        Args:
            theme_name: Name of the preset theme
            app: QApplication instance

        Returns:
            True if theme was set, False otherwise
        """
        presets = ThemePresets.get_all_presets()

        if theme_name in presets:
            theme = presets[theme_name]
            self.apply_theme(theme, app)
            return True

        logger.warning(f"Theme not found: {theme_name}")
        return False

    def set_theme_by_type(self, theme_type: ThemeType, app: Optional[QApplication] = None):
        """Set theme by type.

        Args:
            theme_type: Type of theme to set
            app: QApplication instance

        Returns:
            True if theme was set, False otherwise
        """
        theme = ThemePresets.get_preset(theme_type)

        if theme:
            self.apply_theme(theme, app)
            return True

        logger.warning(f"Theme type not found: {theme_type}")
        return False

    def create_custom_theme(self, name: str, base_theme: Optional[Theme] = None) -> Theme:
        """Create a custom theme based on an existing theme.

        Args:
            name: Name for the custom theme
            base_theme: Theme to use as base. If None, uses Dark theme.

        Returns:
            New custom Theme object
        """
        if not base_theme:
            base_theme = ThemePresets.DARK_THEME

        # Create a copy with modified type and name
        custom_theme = Theme(
            name=name,
            type=ThemeType.CUSTOM,
            colors=base_theme.colors,
            font_family=base_theme.font_family,
            font_size=base_theme.font_size,
            timeline_height=base_theme.timeline_height,
            description=f"Custom theme based on {base_theme.name}"
        )

        return custom_theme

    def get_available_themes(self) -> list:
        """Get list of available theme names.

        Returns:
            List of theme names
        """
        return ThemePresets.get_preset_names()

    def reset_to_default(self, app: Optional[QApplication] = None):
        """Reset to default dark theme.

        Args:
            app: QApplication instance
        """
        self.apply_theme(ThemePresets.DARK_THEME, app)
        logger.info("Reset to default dark theme")

    def update_timeline_height(self, height: int, app: Optional[QApplication] = None):
        """Update timeline height in current theme.

        Args:
            height: New timeline height in pixels
            app: QApplication instance
        """
        if self.current_theme:
            self.current_theme.timeline_height = height
            self.save_theme()

            # Note: Timeline height is not part of stylesheet,
            # so no need to reapply theme. The window should handle
            # the height change separately.

            logger.info(f"Updated timeline height to {height}px")

    def update_font_size(self, size: int, app: Optional[QApplication] = None):
        """Update font size in current theme.

        Args:
            size: New font size in points
            app: QApplication instance
        """
        if self.current_theme:
            self.current_theme.font_size = size
            self.apply_theme(app=app)  # Reapply to update stylesheet

            logger.info(f"Updated font size to {size}pt")

    def update_accent_color(self, color: str, app: Optional[QApplication] = None):
        """Update primary accent color in current theme.

        Args:
            color: New accent color (hex string)
            app: QApplication instance
        """
        if self.current_theme:
            self.current_theme.colors.primary = color
            self.current_theme.colors.button_bg = color
            self.apply_theme(app=app)  # Reapply to update stylesheet

            logger.info(f"Updated accent color to {color}")
