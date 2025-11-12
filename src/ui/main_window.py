"""Main window module for the VideoFlow application.

This module contains the main application window and plugin button components
that provide the primary user interface for VideoFlow.

Classes:
    PluginButton: Custom QPushButton for displaying plugin cards
    MainWindow: Main application window with plugin grid layout
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QMenuBar,
                           QMenu, QLabel, QGridLayout, QPushButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor
from src.core.plugin_manager import PluginManager
from src.core.logger import Logger
import os

logger = Logger.get_logger('MainWindow')

class PluginButton(QPushButton):
    """Custom button widget for displaying plugin cards.

    A visually appealing button that displays a plugin with an icon, name,
    and description in a colored card format. Features hover effects and
    automatic color darkening on interaction.

    Attributes:
        ICONS (dict): Mapping of plugin names to Unicode icons.
    """
    # Dictionary of Unicode icons for each plugin
    ICONS = {
        "Copy Manager": "📋",              # Clipboard
        "Duplicate Finder": "🔍",          # Magnifying glass
        "Video Adder": "🎬",              # Clapperboard
        "Video Converter": "🔄",           # Conversion arrows
        "Regex Renamer": "✏️",             # Pencil
        "Video Editor": "✂️",              # Scissors
        "Video Compressor": "🗜️",         # Compression clamp
        "Batch Renamer": "🏷️",            # Label tag
        "Audio Extractor": "🎵",           # Musical note
        "Smart Video Trimmer": "✂️",       # Scissors
        "Scene Detector": "🎬",            # Clapperboard
    }
    
    def __init__(self, name, description, color, parent=None):
        """Initialize a plugin button.

        Args:
            name (str): Plugin name to display.
            description (str): Short description of the plugin.
            color (str): Background color in hex format (e.g., '#2ecc71').
            parent (QWidget, optional): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.setMinimumSize(200, 150)
        self.setMaximumSize(300, 200)
        
        # Style configuration
        darker_color = self._darken_color(color)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 10px;
                padding: 20px;
                color: white;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {darker_color};
                border: 2px solid white;
            }}
        """)
        
        # Vertical layout for icon and text
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)  # Spacing between elements
        self.setLayout(layout)

        # Icon (Unicode character)
        icon_label = QLabel(self.ICONS.get(name, "◈"))  # Default icon if not found
        icon_font = QFont()
        icon_font.setPointSize(48)  # Larger size for icon
        icon_label.setFont(icon_font)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("color: white; background-color: transparent;")
        layout.addWidget(icon_label)

        # Plugin name
        name_label = QLabel(name)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        name_label.setFont(font)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("color: white; background-color: transparent;")
        layout.addWidget(name_label)
        
        # Description
        desc_label = QLabel(description)
        desc_font = QFont()
        desc_font.setPointSize(10)
        desc_label.setFont(desc_font)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: white; background-color: transparent;")
        layout.addWidget(desc_label)
        
        # Add stretch at the end to center vertically
        layout.addStretch()
    
    def _darken_color(self, color, factor=50):
        """Darken a color for hover effect.

        Args:
            color (str): Color in hex format to darken.
            factor (int, optional): Amount to darken (0-255). Defaults to 50.

        Returns:
            str: Darkened color in hex format.
        """
        color = QColor(color)
        h, s, l, a = color.getHsl()
        darker_color = QColor.fromHsl(h, s, max(0, l - factor), a)
        return darker_color.name()

class MainWindow(QMainWindow):
    """Main application window for VideoFlow.

    This window serves as the primary interface, displaying all available plugins
    in a grid layout with color-coded cards. Users can click on plugin cards to
    launch the corresponding plugin windows.

    Attributes:
        menubar (QMenuBar): Main application menu bar.
        plugins_menu (QMenu): Menu containing plugin actions.
        plugins_grid (QGridLayout): Grid layout for plugin buttons.
        plugin_manager (PluginManager): Manager for loading and configuring plugins.
    """

    def __init__(self):
        """Initialize the main window.

        Sets up the window layout, menu bar, plugin grid, and loads all
        available plugins through the PluginManager.
        """
        super().__init__()
        logger.info("Initializing main window")

        # Basic configuration
        self.setWindowTitle("VideoFlow")
        self.setMinimumSize(800, 600)

        # Main menu
        self.menubar = self.menuBar()

        # File menu
        file_menu = self.menubar.addMenu("File")
        file_menu.addAction("Quit", self.close)

        # Plugins menu (kept as alternative)
        self.plugins_menu = self.menubar.addMenu("Plugins")

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Title
        title_label = QLabel("VideoFlow")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("Select a plugin to get started")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle_label)

        # Plugins grid
        plugins_container = QWidget()
        self.plugins_grid = QGridLayout()
        self.plugins_grid.setSpacing(20)
        plugins_container.setLayout(self.plugins_grid)
        main_layout.addWidget(plugins_container)
        main_layout.addStretch()

        # Load and configure plugins
        self.plugin_manager = PluginManager()
        self.setup_plugins()

    def setup_plugins(self):
        """Configure plugins and create their buttons.

        Loads all available plugins through the PluginManager and creates
        corresponding PluginButton widgets arranged in a 2-column grid.
        Each button is color-coded and connected to the plugin's show_window method.
        """
        # Colors for plugins
        colors = ["#2ecc71", "#3498db", "#e74c3c", "#f1c40f", "#9b59b6", "#1abc9c"]
        color_index = 0

        # Load plugins
        self.plugin_manager.setup_plugins(self)
        plugins = self.plugin_manager.get_plugins()

        # Create buttons
        row = 0
        col = 0
        max_cols = 2

        for plugin in plugins:
            # Create button
            color = colors[color_index % len(colors)]
            button = PluginButton(plugin.name, plugin.description, color)
            button.clicked.connect(plugin.show_window)

            # Add to grid
            self.plugins_grid.addWidget(button, row, col)

            # Update indices
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
            
            color_index += 1
