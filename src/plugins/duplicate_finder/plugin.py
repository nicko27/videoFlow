"""Duplicate finder plugin module"""

from PyQt6.QtGui import QAction
from src.core.plugin_interface import PluginInterface
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.Plugin')

class DuplicateFinderPlugin(PluginInterface):
    def __init__(self):
        super().__init__()
        self.name = "Duplicate Finder"
        self.description = "Find duplicate videos in your library"
        self.version = "1.0.0"
        self.window = None
        logger.debug("DuplicateFinder plugin initialized")

    def setup(self, main_window):
        """Configure the plugin"""
        self.main_window = main_window

        # Create menu action
        self.action = QAction(self.name, self.main_window)
        self.action.triggered.connect(self.show_window)

        # Add to Plugins menu
        self.main_window.plugins_menu.addAction(self.action)
        logger.debug("DuplicateFinder plugin configured")

    def show_window(self):
        """Show the plugin window"""
        if not self.window:
            from .window import DuplicateFinderWindow
            self.window = DuplicateFinderWindow()
            # Connect close signal
            self.window.closed.connect(self.handle_window_closed)
        self.window.show()
        logger.debug("DuplicateFinder window shown")
        
    def handle_window_closed(self):
        """Handle window close event.

        Cleans up the window reference when the plugin window is closed,
        allowing it to be recreated on next launch.
        """
        self.window = None
        logger.debug("DuplicateFinder window closed")
