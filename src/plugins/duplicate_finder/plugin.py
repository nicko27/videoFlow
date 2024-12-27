from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtCore import Qt, QSize
from src.core.plugin_interface import PluginInterface
from src.core.logger import Logger
import os

logger = Logger.get_logger('DuplicateFinder.Plugin')

class Plugin(PluginInterface):
    def __init__(self):
        logger.debug("Initialisation du plugin DuplicateFinder")
        super().__init__()  # Appel du constructeur de la classe parente
        self.window = None

    def get_name(self) -> str:
        logger.debug("get_name() appelé")
        return "Duplicate Finder"

    def get_button(self) -> QPushButton:
        logger.debug("Création du bouton DuplicateFinder")
        button = QPushButton()
        
        # Définition de l'icône
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                'resources', 'icons', 'duplicate_finder.svg')
        logger.debug(f"Chemin de l'icône: {icon_path}")
        
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            button.setIcon(icon)
            button.setIconSize(QSize(32, 32))
            logger.debug("Icône ajoutée au bouton")
        else:
            logger.warning(f"Icône non trouvée: {icon_path}")
        
        # Texte du bouton
        button.setText("Recherche\nDoublons")
        
        # Style du bouton
        button.setStyleSheet("""
            QPushButton {
                background-color: #FF6B6B;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 20px;
                font-size: 14px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #FF8787;
            }
            QPushButton:pressed {
                background-color: #FA5252;
            }
        """)
        
        # Connexion du clic
        button.clicked.connect(self.show_window)
        logger.debug("Bouton DuplicateFinder créé et configuré")
        return button

    def show_window(self):
        logger.debug("Ouverture de la fenêtre DuplicateFinder")
        if not self.window:
            # Import ici pour éviter l'importation circulaire
            from src.plugins.duplicate_finder.window import DuplicateFinderWindow
            self.window = DuplicateFinderWindow()
        self.window.show()
