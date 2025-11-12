"""Theme system for Video Editor.

This module provides a comprehensive theming system with multiple
built-in themes and customization options.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Optional
from enum import Enum
import json


class ThemeType(Enum):
    """Available theme types."""
    DARK = "dark"
    LIGHT = "light"
    PREMIERE_PRO = "premiere_pro"
    CUSTOM = "custom"


@dataclass
class ColorScheme:
    """Color scheme for a theme.

    Attributes:
        background: Main background color
        background_alt: Alternative background (panels, etc.)
        foreground: Main text color
        foreground_alt: Secondary text color
        primary: Primary accent color
        secondary: Secondary accent color
        border: Border color
        hover: Hover state color
        selection: Selection color
        timeline_bg: Timeline background
        timeline_cursor: Timeline cursor/playhead
        timeline_segment: Timeline segment color
        timeline_marker: Timeline marker color
        button_bg: Button background
        button_hover: Button hover state
        button_text: Button text color
        success: Success message color
        warning: Warning message color
        error: Error message color
        info: Info message color
    """

    # Base colors
    background: str = "#1e1e1e"
    background_alt: str = "#252526"
    foreground: str = "#cccccc"
    foreground_alt: str = "#888888"

    # Accent colors
    primary: str = "#007acc"
    secondary: str = "#68217a"

    # UI elements
    border: str = "#3e3e42"
    hover: str = "#2a2d2e"
    selection: str = "#264f78"

    # Timeline colors
    timeline_bg: str = "#282828"
    timeline_cursor: str = "#ffffff"
    timeline_segment: str = "#0078d4"
    timeline_marker: str = "#ffff00"

    # Button colors
    button_bg: str = "#0e639c"
    button_hover: str = "#1177bb"
    button_text: str = "#ffffff"

    # Status colors
    success: str = "#4ec9b0"
    warning: str = "#dcdcaa"
    error: str = "#f48771"
    info: str = "#3794ff"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ColorScheme':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Theme:
    """Complete theme configuration.

    Attributes:
        name: Theme display name
        type: Theme type
        colors: Color scheme
        font_family: Font family for UI
        font_size: Base font size
        timeline_height: Default timeline height in pixels
        description: Theme description
    """

    name: str
    type: ThemeType
    colors: ColorScheme
    font_family: str = "Segoe UI, Arial, sans-serif"
    font_size: int = 10
    timeline_height: int = 80
    description: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'type': self.type.value,
            'colors': self.colors.to_dict(),
            'font_family': self.font_family,
            'font_size': self.font_size,
            'timeline_height': self.timeline_height,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Theme':
        """Create from dictionary."""
        return cls(
            name=data['name'],
            type=ThemeType(data['type']),
            colors=ColorScheme.from_dict(data['colors']),
            font_family=data.get('font_family', "Segoe UI, Arial, sans-serif"),
            font_size=data.get('font_size', 10),
            timeline_height=data.get('timeline_height', 80),
            description=data.get('description', '')
        )

    def get_stylesheet(self) -> str:
        """Generate Qt stylesheet from theme.

        Returns:
            Complete Qt stylesheet string
        """
        c = self.colors

        return f"""
        /* Main Window */
        QMainWindow {{
            background-color: {c.background};
            color: {c.foreground};
            font-family: {self.font_family};
            font-size: {self.font_size}pt;
        }}

        /* Widgets */
        QWidget {{
            background-color: {c.background};
            color: {c.foreground};
        }}

        /* Panels and Group Boxes */
        QGroupBox {{
            background-color: {c.background_alt};
            border: 1px solid {c.border};
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
            font-weight: bold;
        }}

        QGroupBox::title {{
            color: {c.foreground};
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
        }}

        /* Buttons */
        QPushButton {{
            background-color: {c.button_bg};
            color: {c.button_text};
            border: 1px solid {c.border};
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: bold;
        }}

        QPushButton:hover {{
            background-color: {c.button_hover};
        }}

        QPushButton:pressed {{
            background-color: {c.primary};
        }}

        QPushButton:disabled {{
            background-color: {c.background_alt};
            color: {c.foreground_alt};
        }}

        /* Tables */
        QTableWidget {{
            background-color: {c.background_alt};
            alternate-background-color: {c.background};
            gridline-color: {c.border};
            color: {c.foreground};
            border: 1px solid {c.border};
        }}

        QTableWidget::item:selected {{
            background-color: {c.selection};
        }}

        QTableWidget::item:hover {{
            background-color: {c.hover};
        }}

        QHeaderView::section {{
            background-color: {c.background_alt};
            color: {c.foreground};
            padding: 6px;
            border: 1px solid {c.border};
            font-weight: bold;
        }}

        /* Sliders */
        QSlider::groove:horizontal {{
            background: {c.background_alt};
            height: 6px;
            border-radius: 3px;
        }}

        QSlider::handle:horizontal {{
            background: {c.primary};
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}

        QSlider::handle:horizontal:hover {{
            background: {c.button_hover};
        }}

        /* Progress Bars */
        QProgressBar {{
            background-color: {c.background_alt};
            border: 1px solid {c.border};
            border-radius: 4px;
            text-align: center;
            color: {c.foreground};
        }}

        QProgressBar::chunk {{
            background-color: {c.primary};
            border-radius: 3px;
        }}

        /* Labels */
        QLabel {{
            color: {c.foreground};
            background-color: transparent;
        }}

        /* Line Edits */
        QLineEdit {{
            background-color: {c.background_alt};
            color: {c.foreground};
            border: 1px solid {c.border};
            border-radius: 4px;
            padding: 4px;
        }}

        QLineEdit:focus {{
            border: 1px solid {c.primary};
        }}

        /* Combo Boxes */
        QComboBox {{
            background-color: {c.background_alt};
            color: {c.foreground};
            border: 1px solid {c.border};
            border-radius: 4px;
            padding: 4px;
        }}

        QComboBox:hover {{
            background-color: {c.hover};
        }}

        QComboBox::drop-down {{
            border: none;
        }}

        QComboBox QAbstractItemView {{
            background-color: {c.background_alt};
            color: {c.foreground};
            selection-background-color: {c.selection};
            border: 1px solid {c.border};
        }}

        /* Spin Boxes */
        QSpinBox, QDoubleSpinBox {{
            background-color: {c.background_alt};
            color: {c.foreground};
            border: 1px solid {c.border};
            border-radius: 4px;
            padding: 4px;
        }}

        /* Tab Widget */
        QTabWidget::pane {{
            background-color: {c.background_alt};
            border: 1px solid {c.border};
        }}

        QTabBar::tab {{
            background-color: {c.background};
            color: {c.foreground_alt};
            border: 1px solid {c.border};
            padding: 8px 16px;
            margin-right: 2px;
        }}

        QTabBar::tab:selected {{
            background-color: {c.background_alt};
            color: {c.foreground};
            border-bottom: 2px solid {c.primary};
        }}

        QTabBar::tab:hover {{
            background-color: {c.hover};
            color: {c.foreground};
        }}

        /* Menus */
        QMenuBar {{
            background-color: {c.background_alt};
            color: {c.foreground};
            border-bottom: 1px solid {c.border};
        }}

        QMenuBar::item:selected {{
            background-color: {c.hover};
        }}

        QMenu {{
            background-color: {c.background_alt};
            color: {c.foreground};
            border: 1px solid {c.border};
        }}

        QMenu::item:selected {{
            background-color: {c.selection};
        }}

        /* Scrollbars */
        QScrollBar:vertical {{
            background: {c.background_alt};
            width: 12px;
            border: none;
        }}

        QScrollBar::handle:vertical {{
            background: {c.border};
            min-height: 20px;
            border-radius: 6px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {c.primary};
        }}

        QScrollBar:horizontal {{
            background: {c.background_alt};
            height: 12px;
            border: none;
        }}

        QScrollBar::handle:horizontal {{
            background: {c.border};
            min-width: 20px;
            border-radius: 6px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background: {c.primary};
        }}

        /* Text Edits */
        QTextEdit {{
            background-color: {c.background_alt};
            color: {c.foreground};
            border: 1px solid {c.border};
            border-radius: 4px;
        }}

        /* Status Bar */
        QStatusBar {{
            background-color: {c.background_alt};
            color: {c.foreground};
            border-top: 1px solid {c.border};
        }}

        /* Splitter */
        QSplitter::handle {{
            background-color: {c.border};
        }}

        QSplitter::handle:hover {{
            background-color: {c.primary};
        }}
        """


class ThemePresets:
    """Predefined theme presets."""

    DARK_THEME = Theme(
        name="Dark Mode",
        type=ThemeType.DARK,
        colors=ColorScheme(
            background="#1e1e1e",
            background_alt="#252526",
            foreground="#cccccc",
            foreground_alt="#888888",
            primary="#007acc",
            secondary="#68217a",
            border="#3e3e42",
            hover="#2a2d2e",
            selection="#264f78",
            timeline_bg="#282828",
            timeline_cursor="#ffffff",
            timeline_segment="#0078d4",
            timeline_marker="#ffff00",
            button_bg="#0e639c",
            button_hover="#1177bb",
            button_text="#ffffff",
            success="#4ec9b0",
            warning="#dcdcaa",
            error="#f48771",
            info="#3794ff"
        ),
        timeline_height=80,
        description="Default dark theme, easy on the eyes"
    )

    LIGHT_THEME = Theme(
        name="Light Mode",
        type=ThemeType.LIGHT,
        colors=ColorScheme(
            background="#ffffff",
            background_alt="#f3f3f3",
            foreground="#000000",
            foreground_alt="#6a6a6a",
            primary="#0066cc",
            secondary="#8e44ad",
            border="#cccccc",
            hover="#e5e5e5",
            selection="#cce8ff",
            timeline_bg="#f8f8f8",
            timeline_cursor="#000000",
            timeline_segment="#0066cc",
            timeline_marker="#ff8800",
            button_bg="#0066cc",
            button_hover="#0052a3",
            button_text="#ffffff",
            success="#27ae60",
            warning="#f39c12",
            error="#e74c3c",
            info="#3498db"
        ),
        timeline_height=80,
        description="Clean light theme for well-lit environments"
    )

    PREMIERE_PRO_THEME = Theme(
        name="Premiere Pro",
        type=ThemeType.PREMIERE_PRO,
        colors=ColorScheme(
            background="#1a1a1a",
            background_alt="#232323",
            foreground="#d4d4d4",
            foreground_alt="#707070",
            primary="#0085ff",
            secondary="#ff6b00",
            border="#2e2e2e",
            hover="#2a2a2a",
            selection="#0085ff33",
            timeline_bg="#1f1f1f",
            timeline_cursor="#0085ff",
            timeline_segment="#408bd1",
            timeline_marker="#ff6b00",
            button_bg="#444444",
            button_hover="#555555",
            button_text="#d4d4d4",
            success="#62ce9a",
            warning="#f5a623",
            error="#ff6666",
            info="#0085ff"
        ),
        timeline_height=100,
        description="Adobe Premiere Pro inspired theme"
    )

    @classmethod
    def get_preset(cls, theme_type: ThemeType) -> Optional[Theme]:
        """Get a theme preset by type.

        Args:
            theme_type: Type of theme to get

        Returns:
            Theme object or None if not found
        """
        presets = {
            ThemeType.DARK: cls.DARK_THEME,
            ThemeType.LIGHT: cls.LIGHT_THEME,
            ThemeType.PREMIERE_PRO: cls.PREMIERE_PRO_THEME
        }
        return presets.get(theme_type)

    @classmethod
    def get_all_presets(cls) -> Dict[str, Theme]:
        """Get all available theme presets.

        Returns:
            Dictionary of theme name to Theme object
        """
        return {
            "Dark Mode": cls.DARK_THEME,
            "Light Mode": cls.LIGHT_THEME,
            "Premiere Pro": cls.PREMIERE_PRO_THEME
        }

    @classmethod
    def get_preset_names(cls) -> list:
        """Get list of all preset names.

        Returns:
            List of theme names
        """
        return list(cls.get_all_presets().keys())
