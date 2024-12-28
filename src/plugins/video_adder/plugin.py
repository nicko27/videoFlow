from PyQt6.QtGui import QAction
from src.core.plugin_interface import PluginInterface
from src.core.logger import Logger

logger = Logger.get_logger('VideoAdder.Plugin')

class VideoAdderPlugin(PluginInterface):
    def __init__(self):
        super().__init__()
        self.name = "Video Adder"
        self.description = "Fusionne plusieurs vidéos en une seule"
        self.version = "1.0.0"
        self.window = None
        logger.debug("Plugin VideoAdder initialisé")
    
    def setup(self, main_window):
        """Configure le plugin"""
        self.main_window = main_window
        
        # Créer l'action dans le menu
        self.action = QAction(self.name, self.main_window)
        self.action.triggered.connect(self.show_window)
        
        # Ajouter au menu Plugins
        self.main_window.plugins_menu.addAction(self.action)
        logger.debug("Plugin VideoAdder configuré")
    
    def show_window(self):
        """Affiche la fenêtre du plugin"""
        if not self.window:
            from .window import VideoAdderWindow
            self.window = VideoAdderWindow()
        self.window.show()
        logger.debug("Fenêtre VideoAdder affichée")
