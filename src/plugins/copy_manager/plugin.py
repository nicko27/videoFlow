from PyQt6.QtGui import QAction
from src.core.plugin_interface import PluginInterface
from src.core.logger import Logger

logger = Logger.get_logger('CopyManager.Plugin')

class CopyManagerPlugin(PluginInterface):
    def __init__(self):
        super().__init__()
        self.name = "Copy Manager"
        self.description = "Copie la structure des dossiers avec ou sans les fichiers"
        self.version = "1.0.0"
        self.window = None
        logger.debug("Plugin CopyManager initialisé")
    
    def setup(self, main_window):
        """Configure le plugin"""
        self.main_window = main_window
        
        # Créer l'action dans le menu
        self.action = QAction(self.name, self.main_window)
        self.action.triggered.connect(self.show_window)
        
        # Ajouter au menu Plugins
        self.main_window.plugins_menu.addAction(self.action)
        logger.debug("Plugin CopyManager configuré")
    
    def show_window(self):
        """Affiche la fenêtre du plugin"""
        if not self.window:
            from .window import CopyManagerWindow
            self.window = CopyManagerWindow()
            # Connecte le signal de fermeture si disponible
            if hasattr(self.window, 'closed'):
                self.window.closed.connect(self.handle_window_closed)
        self.window.show()
        logger.debug("Fenêtre CopyManager affichée")
        
    def handle_window_closed(self):
        """Gère la fermeture de la fenêtre"""
        self.window = None
        logger.debug("Fenêtre CopyManager fermée")
