"""
Theme System for Duplicate Finder plugin.

Provides Light and Dark themes with consistent styling across all UI components.
"""

from enum import Enum
from typing import Dict
from dataclasses import dataclass


class ThemeType(Enum):
    """Available theme types."""
    LIGHT = "light"
    DARK = "dark"


@dataclass
class ThemeColors:
    """Color palette for a theme."""
    # Background colors
    background: str
    background_alt: str
    background_hover: str

    # Text colors
    text: str
    text_secondary: str
    text_disabled: str

    # Primary colors (main actions, accents)
    primary: str
    primary_hover: str
    primary_disabled: str

    # Secondary colors (secondary actions)
    secondary: str
    secondary_hover: str

    # Status colors
    success: str
    warning: str
    error: str
    info: str

    # Border and separator colors
    border: str
    border_light: str

    # Widget-specific
    input_background: str
    input_border: str
    button_background: str
    button_hover: str

    # Progress and selection
    selection: str
    progress_chunk: str


class Theme:
    """Theme definition with colors and styles."""

    LIGHT_THEME = ThemeColors(
        # Background
        background="#FFFFFF",
        background_alt="#F5F5F5",
        background_hover="#E8E8E8",

        # Text
        text="#333333",
        text_secondary="#666666",
        text_disabled="#AAAAAA",

        # Primary (blue)
        primary="#2196F3",
        primary_hover="#1976D2",
        primary_disabled="#90CAF9",

        # Secondary (purple)
        secondary="#9C27B0",
        secondary_hover="#7B1FA2",

        # Status
        success="#4CAF50",
        warning="#FF9800",
        error="#F44336",
        info="#2196F3",

        # Borders
        border="#CCCCCC",
        border_light="#E0E0E0",

        # Widgets
        input_background="#FFFFFF",
        input_border="#CCCCCC",
        button_background="#F5F5F5",
        button_hover="#E8E8E8",

        # Selection
        selection="#2196F3",
        progress_chunk="#2196F3"
    )

    DARK_THEME = ThemeColors(
        # Background
        background="#1E1E1E",
        background_alt="#2D2D2D",
        background_hover="#3A3A3A",

        # Text
        text="#E0E0E0",
        text_secondary="#B0B0B0",
        text_disabled="#666666",

        # Primary (blue)
        primary="#42A5F5",
        primary_hover="#1E88E5",
        primary_disabled="#1565C0",

        # Secondary (purple)
        secondary="#AB47BC",
        secondary_hover="#8E24AA",

        # Status
        success="#66BB6A",
        warning="#FFA726",
        error="#EF5350",
        info="#42A5F5",

        # Borders
        border="#404040",
        border_light="#555555",

        # Widgets
        input_background="#2D2D2D",
        input_border="#404040",
        button_background="#3A3A3A",
        button_hover="#4A4A4A",

        # Selection
        selection="#42A5F5",
        progress_chunk="#42A5F5"
    )

    @staticmethod
    def get_stylesheet(theme_type: ThemeType) -> str:
        """Generate Qt stylesheet for the given theme."""
        colors = Theme.LIGHT_THEME if theme_type == ThemeType.LIGHT else Theme.DARK_THEME

        return f"""
        /* Global styles */
        QWidget {{
            background-color: {colors.background};
            color: {colors.text};
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
        }}

        /* Main window */
        QMainWindow {{
            background-color: {colors.background};
        }}

        /* Group boxes */
        QGroupBox {{
            border: 1px solid {colors.border};
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 12px;
            font-weight: bold;
            color: {colors.text};
            background-color: {colors.background_alt};
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            color: {colors.text};
        }}

        /* Buttons */
        QPushButton {{
            background-color: {colors.button_background};
            border: 1px solid {colors.border};
            border-radius: 4px;
            padding: 6px 12px;
            color: {colors.text};
            min-height: 24px;
        }}

        QPushButton:hover {{
            background-color: {colors.button_hover};
            border-color: {colors.primary};
        }}

        QPushButton:pressed {{
            background-color: {colors.background_hover};
        }}

        QPushButton:disabled {{
            background-color: {colors.background_alt};
            color: {colors.text_disabled};
            border-color: {colors.border_light};
        }}

        /* Primary buttons */
        QPushButton[class="primary"] {{
            background-color: {colors.primary};
            color: white;
            font-weight: bold;
            border: none;
        }}

        QPushButton[class="primary"]:hover {{
            background-color: {colors.primary_hover};
        }}

        QPushButton[class="primary"]:disabled {{
            background-color: {colors.primary_disabled};
        }}

        /* Success buttons */
        QPushButton[class="success"] {{
            background-color: {colors.success};
            color: white;
            font-weight: bold;
            border: none;
        }}

        QPushButton[class="success"]:hover {{
            background-color: #45A049;
        }}

        /* Warning buttons */
        QPushButton[class="warning"] {{
            background-color: {colors.warning};
            color: white;
            font-weight: bold;
            border: none;
        }}

        QPushButton[class="warning"]:hover {{
            background-color: #F57C00;
        }}

        /* Danger/Error buttons */
        QPushButton[class="danger"] {{
            background-color: {colors.error};
            color: white;
            font-weight: bold;
            border: none;
        }}

        QPushButton[class="danger"]:hover {{
            background-color: #D32F2F;
        }}

        /* Line edits and text inputs */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {colors.input_background};
            border: 1px solid {colors.input_border};
            border-radius: 4px;
            padding: 4px 8px;
            color: {colors.text};
            selection-background-color: {colors.selection};
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 2px solid {colors.primary};
            padding: 3px 7px;
        }}

        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
            background-color: {colors.background_alt};
            color: {colors.text_disabled};
        }}

        /* Spin boxes */
        QSpinBox, QDoubleSpinBox {{
            background-color: {colors.input_background};
            border: 1px solid {colors.input_border};
            border-radius: 4px;
            padding: 4px 8px;
            color: {colors.text};
        }}

        QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 2px solid {colors.primary};
        }}

        QSpinBox::up-button, QDoubleSpinBox::up-button,
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            background-color: {colors.button_background};
            border: 1px solid {colors.border};
            width: 16px;
        }}

        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: {colors.button_hover};
        }}

        /* Combo boxes */
        QComboBox {{
            background-color: {colors.input_background};
            border: 1px solid {colors.input_border};
            border-radius: 4px;
            padding: 4px 8px;
            color: {colors.text};
            min-height: 24px;
        }}

        QComboBox:focus {{
            border: 2px solid {colors.primary};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}

        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {colors.text};
            margin-right: 5px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {colors.background};
            border: 1px solid {colors.border};
            selection-background-color: {colors.selection};
            selection-color: white;
        }}

        /* Checkboxes and radio buttons */
        QCheckBox, QRadioButton {{
            color: {colors.text};
            spacing: 5px;
        }}

        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {colors.border};
            background-color: {colors.input_background};
        }}

        QCheckBox::indicator {{
            border-radius: 3px;
        }}

        QRadioButton::indicator {{
            border-radius: 8px;
        }}

        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
            background-color: {colors.primary};
            border-color: {colors.primary};
        }}

        QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
            border-color: {colors.primary};
        }}

        /* Sliders */
        QSlider::groove:horizontal {{
            background-color: {colors.background_alt};
            border: 1px solid {colors.border};
            height: 6px;
            border-radius: 3px;
        }}

        QSlider::handle:horizontal {{
            background-color: {colors.primary};
            border: 1px solid {colors.primary};
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}

        QSlider::handle:horizontal:hover {{
            background-color: {colors.primary_hover};
        }}

        /* Progress bars */
        QProgressBar {{
            background-color: {colors.background_alt};
            border: 1px solid {colors.border};
            border-radius: 4px;
            text-align: center;
            color: {colors.text};
        }}

        QProgressBar::chunk {{
            background-color: {colors.progress_chunk};
            border-radius: 3px;
        }}

        /* Tab widgets */
        QTabWidget::pane {{
            border: 1px solid {colors.border};
            border-radius: 4px;
            background-color: {colors.background};
        }}

        QTabBar::tab {{
            background-color: {colors.background_alt};
            border: 1px solid {colors.border};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 8px 16px;
            margin-right: 2px;
            color: {colors.text_secondary};
        }}

        QTabBar::tab:selected {{
            background-color: {colors.background};
            color: {colors.text};
            font-weight: bold;
        }}

        QTabBar::tab:hover:!selected {{
            background-color: {colors.background_hover};
        }}

        /* Tables */
        QTableWidget, QTableView {{
            background-color: {colors.background};
            alternate-background-color: {colors.background_alt};
            gridline-color: {colors.border_light};
            border: 1px solid {colors.border};
            selection-background-color: {colors.selection};
            selection-color: white;
        }}

        QTableWidget::item, QTableView::item {{
            padding: 4px;
            color: {colors.text};
        }}

        QHeaderView::section {{
            background-color: {colors.background_alt};
            color: {colors.text};
            padding: 6px;
            border: none;
            border-right: 1px solid {colors.border_light};
            border-bottom: 1px solid {colors.border};
            font-weight: bold;
        }}

        /* Lists */
        QListWidget, QListView {{
            background-color: {colors.background};
            border: 1px solid {colors.border};
            alternate-background-color: {colors.background_alt};
            selection-background-color: {colors.selection};
            selection-color: white;
        }}

        QListWidget::item, QListView::item {{
            padding: 4px;
            color: {colors.text};
        }}

        /* Tree widgets */
        QTreeWidget, QTreeView {{
            background-color: {colors.background};
            border: 1px solid {colors.border};
            alternate-background-color: {colors.background_alt};
            selection-background-color: {colors.selection};
            selection-color: white;
        }}

        /* Scroll bars */
        QScrollBar:vertical {{
            background-color: {colors.background_alt};
            width: 12px;
            border-radius: 6px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {colors.border};
            border-radius: 6px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {colors.text_secondary};
        }}

        QScrollBar:horizontal {{
            background-color: {colors.background_alt};
            height: 12px;
            border-radius: 6px;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {colors.border};
            border-radius: 6px;
            min-width: 20px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {colors.text_secondary};
        }}

        QScrollBar::add-line, QScrollBar::sub-line {{
            border: none;
            background: none;
        }}

        /* Menu bar */
        QMenuBar {{
            background-color: {colors.background};
            color: {colors.text};
            border-bottom: 1px solid {colors.border};
        }}

        QMenuBar::item {{
            padding: 6px 12px;
            background-color: transparent;
        }}

        QMenuBar::item:selected {{
            background-color: {colors.background_hover};
        }}

        QMenuBar::item:pressed {{
            background-color: {colors.selection};
            color: white;
        }}

        /* Menus */
        QMenu {{
            background-color: {colors.background};
            border: 1px solid {colors.border};
            color: {colors.text};
        }}

        QMenu::item {{
            padding: 6px 24px 6px 12px;
        }}

        QMenu::item:selected {{
            background-color: {colors.selection};
            color: white;
        }}

        QMenu::separator {{
            height: 1px;
            background-color: {colors.border_light};
            margin: 4px 0;
        }}

        /* Tool tips */
        QToolTip {{
            background-color: {colors.info};
            color: white;
            border: 1px solid {colors.border};
            border-radius: 4px;
            padding: 4px 8px;
        }}

        /* Labels */
        QLabel {{
            color: {colors.text};
            background-color: transparent;
        }}

        QLabel[class="secondary"] {{
            color: {colors.text_secondary};
        }}

        QLabel[class="success"] {{
            color: {colors.success};
            font-weight: bold;
        }}

        QLabel[class="warning"] {{
            color: {colors.warning};
            font-weight: bold;
        }}

        QLabel[class="error"] {{
            color: {colors.error};
            font-weight: bold;
        }}
        """

    @staticmethod
    def get_theme_names() -> list:
        """Get list of available theme names."""
        return [theme.value for theme in ThemeType]

    @staticmethod
    def apply_theme(widget, theme_type: ThemeType):
        """Apply theme to a widget and all its children."""
        stylesheet = Theme.get_stylesheet(theme_type)
        widget.setStyleSheet(stylesheet)
