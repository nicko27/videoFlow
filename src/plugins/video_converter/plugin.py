"""Plugin pour convertir les fichiers vidéo avec ffmpeg - Version optimisée."""

from PyQt6.QtGui import QAction
from src.core.plugin_interface import PluginInterface
from src.core.logger import Logger

logger = Logger.get_logger('VideoConverter.Plugin')

class VideoConverterPlugin(PluginInterface):
    """Plugin pour la conversion de fichiers vidéo - optimisé pour chargement rapide."""
    
    def __init__(self):
        """Initialise le plugin avec chargement minimal."""
        super().__init__()
        self.name = "Video Converter"
        self.description = "Convertit les fichiers vidéo avec ffmpeg"
        self.version = "1.0.1"
        self.window = None
        self.main_window = None
        # Pas de log debug au chargement pour économiser du temps
    
    def get_name(self) -> str:
        """Retourne le nom du plugin."""
        return self.name
    
    def setup(self, main_window):
        """Configure le plugin avec chargement paresseux."""
        self.main_window = main_window
        
        # Créer l'action dans le menu
        self.action = QAction(self.name, self.main_window)
        self.action.triggered.connect(self.show_window)
        
        # Ajouter au menu Plugins
        self.main_window.plugins_menu.addAction(self.action)
        logger.debug("Plugin VideoConverter configuré")
    
    def show_window(self):
        """Affiche la fenêtre avec chargement paresseux."""
        if not self.window:
            # Import paresseux - seulement quand nécessaire
            from .window import VideoConverterWindow
            self.window = VideoConverterWindow()
        
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        logger.debug("Fenêtre VideoConverter affichée")