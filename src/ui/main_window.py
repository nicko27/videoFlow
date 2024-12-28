from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QMenuBar, 
                           QMenu, QLabel, QGridLayout, QPushButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor
from src.core.plugin_manager import PluginManager
from src.core.logger import Logger
import os

logger = Logger.get_logger('MainWindow')

class PluginButton(QPushButton):
    # Dictionnaire des icônes Unicode pour chaque plugin
    ICONS = {
        "Copy Manager": "📋",      # Presse-papiers
        "Duplicate Finder": "🔍",  # Loupe
        "Video Adder": "🎬",      # Clap de cinéma
        "Video Converter": "🔄",   # Flèches de conversion
        "Regex Renamer": "✏️",     # Crayon
        "Video Editor": "✂️",      # Ciseaux
    }
    
    def __init__(self, name, description, color, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 150)
        self.setMaximumSize(300, 200)
        
        # Configuration du style
        darker_color = self._darken_color(color)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 10px;
                padding: 20px;
                color: white;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {darker_color};
                border: 2px solid white;
            }}
        """)
        
        # Layout vertical pour l'icône et le texte
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)  # Espacement entre les éléments
        self.setLayout(layout)
        
        # Icône (caractère Unicode)
        icon_label = QLabel(self.ICONS.get(name, "◈"))  # Icône par défaut si non trouvée
        icon_font = QFont()
        icon_font.setPointSize(48)  # Plus grande taille pour l'icône
        icon_label.setFont(icon_font)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("color: white; background-color: transparent;")
        layout.addWidget(icon_label)
        
        # Nom du plugin
        name_label = QLabel(name)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        name_label.setFont(font)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("color: white; background-color: transparent;")
        layout.addWidget(name_label)
        
        # Description
        desc_label = QLabel(description)
        desc_font = QFont()
        desc_font.setPointSize(10)
        desc_label.setFont(desc_font)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: white; background-color: transparent;")
        layout.addWidget(desc_label)
        
        # Ajouter un stretch à la fin pour centrer verticalement
        layout.addStretch()
    
    def _darken_color(self, color, factor=50):
        """Assombrit une couleur pour l'effet hover"""
        color = QColor(color)
        h, s, l, a = color.getHsl()
        darker_color = QColor.fromHsl(h, s, max(0, l - factor), a)
        return darker_color.name()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.info("Initialisation de la fenêtre principale")
        
        # Configuration de base
        self.setWindowTitle("VideoFlow")
        self.setMinimumSize(800, 600)
        
        # Menu principal
        self.menubar = self.menuBar()
        
        # Menu Fichier
        file_menu = self.menubar.addMenu("Fichier")
        file_menu.addAction("Quitter", self.close)
        
        # Menu Plugins (gardé comme alternative)
        self.plugins_menu = self.menubar.addMenu("Plugins")
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Titre
        title_label = QLabel("VideoFlow")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Sous-titre
        subtitle_label = QLabel("Sélectionnez un plugin pour commencer")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle_label)
        
        # Grille de plugins
        plugins_container = QWidget()
        self.plugins_grid = QGridLayout()
        self.plugins_grid.setSpacing(20)
        plugins_container.setLayout(self.plugins_grid)
        main_layout.addWidget(plugins_container)
        main_layout.addStretch()
        
        # Charger et configurer les plugins
        self.plugin_manager = PluginManager()
        self.setup_plugins()
    
    def setup_plugins(self):
        """Configure les plugins et crée leurs boutons"""
        # Couleurs pour les plugins
        colors = ["#2ecc71", "#3498db", "#e74c3c", "#f1c40f", "#9b59b6", "#1abc9c"]
        color_index = 0
        
        # Charger les plugins
        self.plugin_manager.setup_plugins(self)
        plugins = self.plugin_manager.get_plugins()
        
        # Créer les boutons
        row = 0
        col = 0
        max_cols = 2
        
        for plugin in plugins:
            # Créer le bouton
            color = colors[color_index % len(colors)]
            button = PluginButton(plugin.name, plugin.description, color)
            button.clicked.connect(plugin.show_window)
            
            # Ajouter à la grille
            self.plugins_grid.addWidget(button, row, col)
            
            # Mise à jour des indices
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
            
            color_index += 1
