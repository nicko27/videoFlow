"""
Theme system for the duplicate finder plugin.

Provides 4 different visual themes that users can switch between:
1. Compact Modern - Dense, efficient layout with modern colors
2. Minimalist - Clean, simple design with lots of whitespace
3. Material Design - Google Material Design inspired
4. Dashboard - Information-rich dashboard style
"""

from typing import Dict, Any
from .design_system import Colors, Spacing, Typography


class Theme:
    """Base theme configuration."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def get_colors(self) -> Dict[str, str]:
        """Get theme-specific colors."""
        raise NotImplementedError

    def get_spacing(self) -> Dict[str, int]:
        """Get theme-specific spacing values."""
        raise NotImplementedError

    def get_title_style(self) -> str:
        """Get title bar stylesheet."""
        raise NotImplementedError

    def get_progress_style(self) -> str:
        """Get progress bar stylesheet."""
        raise NotImplementedError


class CompactModernTheme(Theme):
    """Compact and modern theme - dense, efficient layout."""

    def __init__(self):
        super().__init__(
            "Compact Modern",
            "Dense, efficient layout with modern colors"
        )

    def get_colors(self) -> Dict[str, str]:
        return {
            'primary': '#2196F3',
            'primary_dark': '#1976D2',
            'bg_main': '#FAFAFA',
            'bg_card': '#FFFFFF',
            'text': Colors.BLACK,
            'border': '#E0E0E0'
        }

    def get_spacing(self) -> Dict[str, int]:
        return {
            'margin': 8,
            'padding': 8,
            'gap': 6,
            'radius': 6,
            'title_height': 45,
            'progress_height': 22,
            'file_item_height': 55
        }

    def get_title_style(self) -> str:
        colors = self.get_colors()
        spacing = self.get_spacing()
        return f"""
            QLabel {{
                color: {colors['primary_dark']};
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.PRIMARY_LIGHTER}, stop:1 {Colors.INFO_LIGHTER});
                border-radius: {spacing['radius']}px;
                padding: {spacing['padding']}px;
                font-size: {Typography.FONT_LG}px;
                font-weight: bold;
                max-height: {spacing['title_height']}px;
            }}
        """

    def get_progress_style(self) -> str:
        colors = self.get_colors()
        spacing = self.get_spacing()
        return f"""
            QProgressBar {{
                border: 1px solid {colors['border']};
                border-radius: {spacing['radius']}px;
                text-align: center;
                font-weight: bold;
                font-size: {Typography.FONT_XS}px;
                color: {Colors.BLACK};
                background-color: {Colors.GRAY_100};
                min-height: {spacing['progress_height']}px;
                max-height: {spacing['progress_height']}px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {colors['primary']}, stop:1 {colors['primary_dark']});
                border-radius: {spacing['radius'] - 1}px;
                margin: 1px;
            }}
        """


class MinimalistTheme(Theme):
    """Minimalist theme - clean and simple."""

    def __init__(self):
        super().__init__(
            "Minimalist",
            "Clean, simple design with lots of whitespace"
        )

    def get_colors(self) -> Dict[str, str]:
        return {
            'primary': '#000000',
            'primary_light': '#757575',
            'bg_main': '#FFFFFF',
            'bg_card': '#FAFAFA',
            'text': Colors.BLACK,
            'border': '#E8E8E8',
            'accent': '#2196F3'
        }

    def get_spacing(self) -> Dict[str, int]:
        return {
            'margin': 20,
            'padding': 15,
            'gap': 12,
            'radius': 2,  # Très peu de rondeur
            'title_height': 40,
            'progress_height': 4,  # Barre très fine
            'file_item_height': 65
        }

    def get_title_style(self) -> str:
        colors = self.get_colors()
        spacing = self.get_spacing()
        return f"""
            QLabel {{
                color: {colors['primary']};
                background-color: transparent;
                border: none;
                border-bottom: 2px solid {colors['primary']};
                padding: {spacing['padding']}px {spacing['padding'] * 2}px;
                font-size: {Typography.FONT_XL}px;
                font-weight: normal;
                letter-spacing: 2px;
                max-height: {spacing['title_height']}px;
            }}
        """

    def get_progress_style(self) -> str:
        colors = self.get_colors()
        spacing = self.get_spacing()
        return f"""
            QProgressBar {{
                border: none;
                border-radius: {spacing['radius']}px;
                background-color: {colors['border']};
                min-height: {spacing['progress_height']}px;
                max-height: {spacing['progress_height']}px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {colors['primary']};
                border-radius: {spacing['radius']}px;
            }}
        """


class MaterialTheme(Theme):
    """Material Design theme - Google Material Design inspired."""

    def __init__(self):
        super().__init__(
            "Material Design",
            "Google Material Design with elevation and cards"
        )

    def get_colors(self) -> Dict[str, str]:
        return {
            'primary': '#1976D2',
            'primary_dark': '#0D47A1',
            'primary_light': '#BBDEFB',
            'secondary': '#F57C00',
            'bg_main': '#FAFAFA',
            'bg_card': '#FFFFFF',
            'text': '#212121',
            'text_secondary': '#757575',
            'border': '#E0E0E0'
        }

    def get_spacing(self) -> Dict[str, int]:
        return {
            'margin': 16,
            'padding': 16,
            'gap': 8,
            'radius': 4,
            'title_height': 64,  # Material toolbar height
            'progress_height': 4,  # Material progress bar
            'file_item_height': 72  # Material list item height
        }

    def get_title_style(self) -> str:
        colors = self.get_colors()
        spacing = self.get_spacing()
        return f"""
            QLabel {{
                color: #FFFFFF;
                background-color: {colors['primary']};
                border-radius: {spacing['radius']}px;
                padding: {spacing['padding']}px {spacing['padding'] * 2}px;
                font-size: {Typography.FONT_XXL}px;
                font-weight: 500;
                max-height: {spacing['title_height']}px;
                /* Material elevation */
                qproperty-shadowColor: rgba(0, 0, 0, 0.2);
            }}
        """

    def get_progress_style(self) -> str:
        colors = self.get_colors()
        spacing = self.get_spacing()
        return f"""
            QProgressBar {{
                border: none;
                border-radius: {spacing['radius']}px;
                background-color: {colors['primary_light']};
                min-height: {spacing['progress_height']}px;
                max-height: {spacing['progress_height']}px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {colors['primary']};
                border-radius: {spacing['radius']}px;
            }}
        """


class DashboardTheme(Theme):
    """Dashboard theme - information-rich with stats and metrics."""

    def __init__(self):
        super().__init__(
            "Dashboard",
            "Information-rich dashboard with stats and metrics"
        )

    def get_colors(self) -> Dict[str, str]:
        return {
            'primary': '#00897B',  # Teal
            'primary_dark': '#00695C',
            'primary_light': '#B2DFDB',
            'accent': '#FF6F00',  # Orange
            'bg_main': '#ECEFF1',
            'bg_card': '#FFFFFF',
            'bg_stat': '#F5F5F5',
            'text': '#263238',
            'text_secondary': '#546E7A',
            'border': '#CFD8DC',
            'success': '#4CAF50',
            'warning': '#FFC107',
            'error': '#F44336'
        }

    def get_spacing(self) -> Dict[str, int]:
        return {
            'margin': 12,
            'padding': 12,
            'gap': 10,
            'radius': 8,
            'title_height': 50,
            'progress_height': 28,
            'file_item_height': 60
        }

    def get_title_style(self) -> str:
        colors = self.get_colors()
        spacing = self.get_spacing()
        return f"""
            QLabel {{
                color: {colors['primary_dark']};
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {colors['bg_card']}, stop:1 {colors['bg_stat']});
                border: 2px solid {colors['primary_light']};
                border-radius: {spacing['radius']}px;
                padding: {spacing['padding']}px {spacing['padding'] * 2}px;
                font-size: {Typography.FONT_XL}px;
                font-weight: bold;
                max-height: {spacing['title_height']}px;
            }}
        """

    def get_progress_style(self) -> str:
        colors = self.get_colors()
        spacing = self.get_spacing()
        return f"""
            QProgressBar {{
                border: 2px solid {colors['border']};
                border-radius: {spacing['radius']}px;
                text-align: center;
                font-weight: bold;
                font-size: {Typography.FONT_MD}px;
                color: {Colors.BLACK};
                background-color: {colors['bg_card']};
                min-height: {spacing['progress_height']}px;
                max-height: {spacing['progress_height']}px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {colors['primary']}, stop:1 {colors['primary_dark']});
                border-radius: {spacing['radius'] - 2}px;
                margin: 2px;
            }}
        """


class ThemeManager:
    """Manages theme selection and application."""

    THEMES = {
        'compact': CompactModernTheme(),
        'minimalist': MinimalistTheme(),
        'material': MaterialTheme(),
        'dashboard': DashboardTheme()
    }

    def __init__(self):
        self._current_theme_key = 'compact'  # Default theme

    def get_current_theme(self) -> Theme:
        """Get the currently active theme."""
        return self.THEMES[self._current_theme_key]

    def set_theme(self, theme_key: str) -> bool:
        """Set the current theme.

        Args:
            theme_key: Theme identifier ('compact', 'minimalist', 'material', 'dashboard')

        Returns:
            True if theme was changed, False if invalid key
        """
        if theme_key in self.THEMES:
            self._current_theme_key = theme_key
            return True
        return False

    def get_theme_names(self) -> Dict[str, str]:
        """Get all available theme names and descriptions.

        Returns:
            Dictionary mapping theme keys to display names
        """
        return {
            key: theme.name
            for key, theme in self.THEMES.items()
        }

    def get_theme_list(self) -> list:
        """Get list of (key, name, description) tuples for all themes."""
        return [
            (key, theme.name, theme.description)
            for key, theme in self.THEMES.items()
        ]


# Global theme manager instance
_theme_manager = ThemeManager()


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    return _theme_manager


def get_current_theme() -> Theme:
    """Convenience function to get current theme."""
    return _theme_manager.get_current_theme()
