"""Plugin pour convertir les files vidéo with ffmpeg - Version optimisée."""

from PyQt6.QtGui import QAction
from src.core.plugin_interface import PluginInterface
from src.core.logger import Logger

logger = Logger.get_logger('VideoConverter.Plugin')

class VideoConverterPlugin(PluginInterface):
    """Plugin for the conversion de files vidéo - optimisé pour chargement rapide."""
    
    def __init__(self):
        """Initialise the plugin with chargement minimal."""
        super().__init__()
        self.name = "Video Converter"
        self.description = "Converts les files vidéo with ffmpeg"
        self.version = "1.0.1"
        self.window = None
        self.main_window = None
        # Pas de log debug au chargement pour économiser du time
    
    def get_name(self) -> str:
        """Returns le name du plugin."""
        return self.name
    
    def setup(self, main_window):
        """Configures the plugin with chargement paresseux."""
        self.main_window = main_window
        
        # Créer l'action in le menu
        self.action = QAction(self.name, self.main_window)
        self.action.triggered.connect(self.show_window)
        
        # Add au menu Plugins
        self.main_window.plugins_menu.addAction(self.action)
        logger.debug("Plugin VideoConverter configuré")
    
    def show_window(self):
        """Affiche the window with chargement paresseux."""
        if not self.window:
            # Import paresseux - seulement quand nécessaire
            from .window import VideoConverterWindow
            self.window = VideoConverterWindow()
        
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        logger.debug("Window VideoConverter affichée")