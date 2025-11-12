"""Module du plugin de search de doublons"""

from PyQt6.QtGui import QAction
from src.core.plugin_interface import PluginInterface
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.Plugin')

class DuplicateFinderPlugin(PluginInterface):
    def __init__(self):
        super().__init__()
        self.name = "Duplicate Finder"
        self.description = "Trouve les doublons in vos vidéos"
        self.version = "1.0.0"
        self.window = None
        logger.debug("Plugin DuplicateFinder initialisé")
    
    def setup(self, main_window):
        """Configures the plugin"""
        self.main_window = main_window
        
        # Créer l'action in le menu
        self.action = QAction(self.name, self.main_window)
        self.action.triggered.connect(self.show_window)
        
        # Add au menu Plugins
        self.main_window.plugins_menu.addAction(self.action)
        logger.debug("Plugin DuplicateFinder configuré")
    
    def show_window(self):
        """Affiche the window du plugin"""
        if not self.window:
            from .window import DuplicateFinderWindow
            self.window = DuplicateFinderWindow()
            # Connecte le signal de fermeture
            self.window.closed.connect(self.handle_window_closed)
        self.window.show()
        logger.debug("Window DuplicateFinder affichée")
        
    def handle_window_closed(self):
        """Handle window close event.

        Cleans up the window reference when the plugin window is closed,
        allowing it to be recreated on next launch.
        """
        self.window = None
        logger.debug("Window DuplicateFinder fermée")
