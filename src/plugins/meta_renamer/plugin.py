"""Plugin pour comparer et synchroniser les noms de fichiers avec leurs métadonnées."""

import logging
from pathlib import Path
from PyQt6.QtWidgets import QAction

from src.plugin_interface import PluginInterface
from .window import MetaRenamerWindow

logger = logging.getLogger("VideoFlow.MetaRenamer.Plugin")

class MetaRenamerPlugin(PluginInterface):
    """Plugin pour gérer la synchronisation des noms de fichiers avec leurs métadonnées."""
    
    def __init__(self):
        """Initialise le plugin."""
        super().__init__()
        self.window = None
        self.action = None
        logger.debug("Plugin MetaRenamer initialisé")
    
    def setup(self, main_window):
        """Configure le plugin et crée l'action dans le menu."""
        self.action = QAction("Meta Renamer", main_window)
        self.action.triggered.connect(self.show_window)
        logger.debug("Plugin MetaRenamer configuré")
        return self.action
    
    def show_window(self):
        """Affiche la fenêtre principale du plugin."""
        if not self.window:
            self.window = MetaRenamerWindow()
        self.window.show()
        logger.debug("Fenêtre MetaRenamer affichée")
