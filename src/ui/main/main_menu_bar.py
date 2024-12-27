"""
Barre de menu principale de l'application
"""

from PyQt6.QtWidgets import QMenuBar, QMenu, QMessageBox
from PyQt6.QtGui import QAction

class MainMenuBar(QMenuBar):
    """Barre de menu principale avec toutes les actions disponibles"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_menus()

    def setup_menus(self):
        """Création de tous les menus"""
        self.create_file_menu()
        self.create_help_menu()

    def create_file_menu(self):
        """Menu Fichier"""
        file_menu = QMenu("&Fichier", self)
        
        # Paramètres
        settings_action = QAction("&Paramètres", self)
        settings_action.triggered.connect(self.parent.on_open_settings)
        file_menu.addAction(settings_action)
        
        # Séparateur
        file_menu.addSeparator()
        
        # Quitter
        quit_action = QAction("&Quitter", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.parent.close)
        file_menu.addAction(quit_action)
            
        self.addMenu(file_menu)

    def create_help_menu(self):
        """Menu Aide"""
        help_menu = QMenu("&Aide", self)
        
        about_action = QAction("À &propos", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        self.addMenu(help_menu)

    def show_about(self):
        """Affiche la boîte de dialogue À propos"""
        QMessageBox.about(
            self.parent,
            "À propos de VideoFlow",
            "VideoFlow\n\n"
            "Application de gestion et traitement de fichiers vidéo\n"
            "Version 0.1.0\n\n"
            " 2024"
        )
