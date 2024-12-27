"""
Fenêtre principale de l'application
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStatusBar, QGridLayout, QGraphicsDropShadowEffect,
    QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut, QColor

from .main_menu_bar import MainMenuBar
from src.ui.dialogs.renamer.file_rename_dialog import FileRenameDialog

class MainWindow(QMainWindow):
    """Fenêtre principale de VideoFlow"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VideoFlow")
        self.setup_ui()
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """Configuration des raccourcis clavier"""
        shortcuts = [
            (QKeySequence("Ctrl+D"), self.on_find_duplicates),
            (QKeySequence("Ctrl+C"), self.on_convert_videos),
            (QKeySequence("Ctrl+M"), self.on_merge_videos),
            (QKeySequence("Ctrl+E"), self.on_extract_segment),
            (QKeySequence("Ctrl+R"), self.on_rename_files),
            (QKeySequence("Ctrl+,"), self.on_open_settings),
        ]
        
        for key, slot in shortcuts:
            shortcut = QShortcut(key, self)
            shortcut.activated.connect(slot)

    def setup_ui(self):
        """Configuration de l'interface utilisateur"""
        
        # Configuration de la fenêtre
        self.resize(800, 600)
        self.setMinimumSize(600, 400)
        
        # Configuration du fond de la fenêtre
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
        """)
        
        # Menu principal
        self.setMenuBar(MainMenuBar(self))
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setSpacing(40)
        main_layout.setContentsMargins(50, 50, 50, 50)
        
        # Grid pour les boutons
        button_grid = QGridLayout()
        button_grid.setSpacing(30)
        
        # Style de base des boutons
        base_style = """
            QPushButton {{
                font-size: 14px;
                padding: 20px;
                min-width: 200px;
                min-height: 100px;
                border: none;
                text-align: center;
                border-radius: 15px;
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {light_color}, stop:1 {bg_color});
                color: {text_color};
                text-align: center;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {light_color}, stop:1 {hover_color});
            }}
            
            QPushButton:pressed {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {bg_color}, stop:1 {pressed_color});
                padding-top: 23px;
                padding-bottom: 17px;
            }}
        """
        
        # Chemin des icônes
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                               "resources", "icons")
        
        # Création des boutons avec leurs couleurs spécifiques
        buttons = [
            ("Rechercher les doublons\nCtrl+D", self.on_find_duplicates, 
             "Identifier et gérer les vidéos en double", 
             os.path.join(icon_path, "duplicates.svg"), 0, 0,
             "#2196F3", "#64B5F6", "#1976D2", "#1565C0", "white"),  # Bleu
            
            ("Convertir les vidéos\nCtrl+C", self.on_convert_videos, 
             "Convertir les vidéos volumineuses", 
             os.path.join(icon_path, "convert.svg"), 0, 1,
             "#4CAF50", "#81C784", "#388E3C", "#2E7D32", "white"),  # Vert
            
            ("Fusionner des vidéos\nCtrl+M", self.on_merge_videos, 
             "Combiner plusieurs vidéos en une seule", 
             os.path.join(icon_path, "merge.svg"), 1, 0,
             "#FF9800", "#FFB74D", "#F57C00", "#EF6C00", "white"),  # Orange
            
            ("Extraire un segment\nCtrl+E", self.on_extract_segment, 
             "Extraire une partie d'une vidéo", 
             os.path.join(icon_path, "extract.svg"), 1, 1,
             "#E91E63", "#F06292", "#C2185B", "#AD1457", "white"),  # Rose
            
            ("Renommer les fichiers\nCtrl+R", self.on_rename_files, 
             "Nettoyer et organiser les noms de fichiers", 
             os.path.join(icon_path, "rename.svg"), 2, 0,
             "#9C27B0", "#BA68C8", "#7B1FA2", "#6A1B9A", "white"),  # Violet
            
            ("Paramètres\nCtrl+,", self.on_open_settings, 
             "Configurer l'application", 
             os.path.join(icon_path, "settings.svg"), 2, 1,
             "#607D8B", "#90A4AE", "#455A64", "#37474F", "white"),  # Gris-bleu
        ]
        
        for text, slot, tooltip, icon_file, row, col, bg_color, light_color, hover_color, pressed_color, text_color in buttons:
            btn = QPushButton(text)
            
            # Application du style avec les couleurs spécifiques
            btn.setStyleSheet(base_style.format(
                bg_color=bg_color,
                light_color=light_color,
                hover_color=hover_color,
                pressed_color=pressed_color,
                text_color=text_color
            ))
            
            # Ajout de l'ombre
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(15)
            shadow.setXOffset(0)
            shadow.setYOffset(5)
            shadow.setColor(QColor(0, 0, 0, 80))
            btn.setGraphicsEffect(shadow)
            
            btn.setToolTip(tooltip)
            
            # Ajout de l'icône
            icon = QIcon(icon_file)
            btn.setIcon(icon)
            btn.setIconSize(QSize(48, 48))
            
            btn.clicked.connect(slot)
            button_grid.addWidget(btn, row, col)
        
        # Ajout de la grille au layout principal
        main_layout.addLayout(button_grid)
        
        # Barre de statut avec style
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #ffffff;
                color: #333333;
                padding: 5px;
                font-weight: bold;
            }
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Prêt")

    def on_find_duplicates(self):
        """Ouvre la fenêtre de recherche de doublons"""
        self.status_bar.showMessage("Ouverture de la recherche de doublons...")
        # TODO: Implémenter la fenêtre de recherche de doublons

    def on_convert_videos(self):
        """Ouvre la fenêtre de conversion"""
        self.status_bar.showMessage("Ouverture de la conversion...")
        # TODO: Implémenter la fenêtre de conversion

    def on_merge_videos(self):
        """Ouvre la fenêtre de fusion"""
        self.status_bar.showMessage("Ouverture de la fusion...")
        # TODO: Implémenter la fenêtre de fusion

    def on_extract_segment(self):
        """Ouvre la fenêtre d'extraction"""
        self.status_bar.showMessage("Ouverture de l'extraction...")
        # TODO: Implémenter la fenêtre d'extraction

    def on_rename_files(self):
        """Ouvrir la fenêtre de renommage de fichiers"""
        dialog = FileRenameDialog(self)
        dialog.exec()

    def on_open_settings(self):
        """Ouvre la fenêtre des paramètres"""
        self.status_bar.showMessage("Ouverture des paramètres...")
        # TODO: Implémenter la fenêtre des paramètres

    def closeEvent(self, event):
        """Gestion de la fermeture de l'application"""
        reply = QMessageBox.question(
            self,
            'Confirmation',
            'Voulez-vous vraiment quitter ?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
