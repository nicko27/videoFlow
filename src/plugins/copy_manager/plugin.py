"""Copy Manager plugin implementation.

This module contains the plugin interface implementation for the Copy Manager,
which provides functionality to copy folder structures with flexible options.
"""

from PyQt6.QtGui import QAction
from src.core.plugin_interface import PluginInterface
from src.core.logger import Logger
from src.core.i18n import t

logger = Logger.get_logger('CopyManager.Plugin')

class CopyManagerPlugin(PluginInterface):
    """Copy Manager plugin for VideoFlow.

    Provides functionality to copy folder structures with options to include
    or exclude files, preserve macOS metadata, and handle hidden files.

    Attributes:
        name (str): Display name of the plugin.
        description (str): Short description of plugin functionality.
        version (str): Plugin version number.
        window (CopyManagerWindow): The plugin's main window instance.
        main_window (QMainWindow): Reference to the application's main window.
        action (QAction): Menu action for launching the plugin.
    """

    def __init__(self):
        """Initialize the Copy Manager plugin.

        Sets up the plugin's basic properties and prepares it for integration
        with the main application.
        """
        super().__init__()
        self.name = t("plugin.copy_manager.name", "Copy Manager")
        self.description = t("plugin.copy_manager.description", "Copy folder structure with or without files")
        self.version = "1.0.0"
        self.window = None
        logger.debug("CopyManager plugin initialized")

    def setup(self, main_window):
        """Configure the plugin and integrate it with the main window.

        Creates a menu action and adds it to the main window's plugin menu.

        Args:
            main_window (QMainWindow): The application's main window instance.
        """
        self.main_window = main_window

        # Create menu action
        self.action = QAction(self.name, self.main_window)
        self.action.triggered.connect(self.show_window)

        # Add to Plugins menu
        self.main_window.plugins_menu.addAction(self.action)
        logger.debug("CopyManager plugin configured")

    def show_window(self):
        """Display the plugin window.

        Creates the Copy Manager window if it doesn't exist and displays it.
        Uses lazy loading to only create the window when first needed.
        """
        if not self.window:
            from .window import CopyManagerWindow
            self.window = CopyManagerWindow()
        self.window.show()
        logger.debug("CopyManager window displayed")
