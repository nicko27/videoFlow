"""
Gestionnaire de patterns d'expressions régulières
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QInputDialog, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
import json
import os

class PatternManagerDialog(QWidget):
    """Gestionnaire de patterns avec sauvegarde et chargement"""
    
    pattern_selected = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_patterns()

    def setup_ui(self):
        """Configuration de l'interface utilisateur"""
        # Style global
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                margin: 2px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QPushButton {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                background-color: #2196f3;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #1565c0;
            }
            QPushButton[action="danger"] {
                background-color: #f44336;
            }
            QPushButton[action="danger"]:hover {
                background-color: #e53935;
            }
            QPushButton[action="danger"]:pressed {
                background-color: #d32f2f;
            }
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
            }
            QLabel {
                color: #424242;
            }
            QLabel[title="true"] {
                font-size: 16px;
                font-weight: bold;
                color: #1976d2;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # En-tête
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        
        title = QLabel("Patterns sauvegardés")
        title.setProperty("title", "true")
        header_layout.addWidget(title)
        
        self.add_btn = QPushButton("Sauvegarder le pattern actuel")
        self.add_btn.setIcon(QIcon.fromTheme("document-save"))
        self.add_btn.clicked.connect(self.save_current_pattern)
        header_layout.addWidget(self.add_btn)
        
        # Liste des patterns
        patterns_frame = QFrame()
        patterns_layout = QVBoxLayout(patterns_frame)
        
        self.patterns_list = QListWidget()
        self.patterns_list.setAlternatingRowColors(True)
        self.patterns_list.itemDoubleClicked.connect(self.load_pattern)
        
        # Boutons d'action
        actions_layout = QHBoxLayout()
        
        self.rename_btn = QPushButton("Renommer")
        self.rename_btn.setIcon(QIcon.fromTheme("edit"))
        self.rename_btn.clicked.connect(self.rename_pattern)
        self.rename_btn.setEnabled(False)
        
        self.delete_btn = QPushButton("Supprimer")
        self.delete_btn.setProperty("action", "danger")
        self.delete_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.delete_btn.clicked.connect(self.delete_pattern)
        self.delete_btn.setEnabled(False)
        
        actions_layout.addWidget(self.rename_btn)
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addStretch()
        
        patterns_layout.addWidget(self.patterns_list)
        patterns_layout.addLayout(actions_layout)
        
        # Patterns prédéfinis
        presets_frame = QFrame()
        presets_layout = QVBoxLayout(presets_frame)
        
        presets_title = QLabel("Patterns prédéfinis")
        presets_title.setProperty("title", "true")
        
        self.presets_list = QListWidget()
        self.presets_list.setAlternatingRowColors(True)
        self.presets_list.itemDoubleClicked.connect(self.load_preset)
        
        # Ajout des patterns prédéfinis avec descriptions
        presets = [
            ("Supprimer les espaces", {
                'pattern': r'\s+',
                'replace': '_',
                'description': "Remplace tous les espaces par des underscores"
            }),
            ("Nettoyer les caractères spéciaux", {
                'pattern': r'[^a-zA-Z0-9\s\-_\.]',
                'replace': '',
                'description': "Supprime tous les caractères spéciaux"
            }),
            ("Format date (YYYYMMDD)", {
                'pattern': r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})',
                'replace': r'\1\2\3',
                'description': "Normalise le format de date YYYYMMDD"
            }),
            ("Numérotation (01, 02, ...)", {
                'pattern': r'^(\d+)',
                'replace': lambda m: f"{int(m.group(1)):02d}",
                'description': "Ajoute des zéros devant les numéros"
            })
        ]
        
        for name, pattern in presets:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, pattern)
            item.setToolTip(pattern['description'])
            self.presets_list.addItem(item)
        
        presets_layout.addWidget(presets_title)
        presets_layout.addWidget(self.presets_list)
        
        # Assemblage final
        layout.addWidget(header_frame)
        layout.addWidget(patterns_frame)
        layout.addWidget(presets_frame)
        
        # Connexions
        self.patterns_list.itemSelectionChanged.connect(self.update_buttons)

    def load_patterns(self):
        """Charger les patterns sauvegardés"""
        # TODO: Charger depuis un fichier de configuration
        pass

    def save_patterns(self):
        """Sauvegarder les patterns"""
        # TODO: Sauvegarder dans un fichier de configuration
        pass

    def save_current_pattern(self):
        """Sauvegarder le pattern actuel"""
        name, ok = QInputDialog.getText(
            self,
            "Sauvegarder le pattern",
            "Nom du pattern :"
        )
        
        if ok and name:
            # TODO: Sauvegarder le pattern actuel
            pass

    def load_pattern(self, item):
        """Charger un pattern sauvegardé"""
        pattern = item.data(Qt.ItemDataRole.UserRole)
        self.pattern_selected.emit(pattern)

    def load_preset(self, item):
        """Charger un pattern prédéfini"""
        pattern = item.data(Qt.ItemDataRole.UserRole)
        self.pattern_selected.emit(pattern)

    def rename_pattern(self):
        """Renommer un pattern"""
        item = self.patterns_list.currentItem()
        if not item:
            return
            
        old_name = item.text()
        new_name, ok = QInputDialog.getText(
            self,
            "Renommer le pattern",
            "Nouveau nom :",
            text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            item.setText(new_name)
            self.save_patterns()

    def delete_pattern(self):
        """Supprimer un pattern"""
        item = self.patterns_list.currentItem()
        if not item:
            return
            
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Voulez-vous vraiment supprimer le pattern '{item.text()}' ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.patterns_list.takeItem(self.patterns_list.row(item))
            self.save_patterns()

    def update_buttons(self):
        """Mettre à jour l'état des boutons"""
        has_selection = bool(self.patterns_list.currentItem())
        self.rename_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
