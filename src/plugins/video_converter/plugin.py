"""Plugin pour convertir les fichiers vidéo avec ffmpeg."""

from PyQt6.QtGui import QAction
from src.core.plugin_interface import PluginInterface
from src.core.logger import Logger

logger = Logger.get_logger('VideoConverter.Plugin')

class VideoConverterPlugin(PluginInterface):
    """Plugin pour la conversion de fichiers vidéo."""
    
    def __init__(self):
        """Initialise le plugin."""
        super().__init__()
        self.name = "Video Converter"
        self.description = "Convertit les fichiers vidéo avec ffmpeg"
        self.version = "1.0.0"
        self.window = None
        self.main_window = None
        logger.debug("Plugin VideoConverter initialisé")
    
    def get_name(self) -> str:
        """Retourne le nom du plugin."""
        logger.debug("get_name() appelé")
        return self.name
    
    def setup(self, main_window):
        """Configure le plugin et crée l'action dans le menu."""
        self.main_window = main_window
        
        # Créer l'action dans le menu
        self.action = QAction(self.name, self.main_window)
        self.action.triggered.connect(self.show_window)
        
        # Ajouter au menu Plugins
        self.main_window.plugins_menu.addAction(self.action)
        logger.debug("Plugin VideoConverter configuré")
    
    def show_window(self):
        """Affiche la fenêtre principale du plugin."""
        if not self.window:
            from .window import VideoConverterWindow
            self.window = VideoConverterWindow()
            # Connecte le signal de fermeture si disponible
            if hasattr(self.window, 'closed'):
                self.window.closed.connect(self.handle_window_closed)
        self.window.show()
        logger.debug("Fenêtre VideoConverter affichée")
        
    def handle_window_closed(self):
        """Gère la fermeture de la fenêtre"""
        self.window = None
        logger.debug("Fenêtre VideoConverter fermée")
