"""
Prévisualisation des changements de nom de fichiers
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel,
    QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon
import os

class RenamePreviewDialog(QWidget):
    """Prévisualisation des changements de nom de fichiers"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Configuration de l'interface utilisateur"""
        # Style global
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                gridline-color: #f5f5f5;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f5f5f5;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-right: 1px solid #e0e0e0;
                border-bottom: 1px solid #e0e0e0;
                font-weight: bold;
                color: #424242;
            }
            QHeaderView::section:last {
                border-right: none;
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
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # En-tête
        header = QFrame()
        header_layout = QVBoxLayout(header)
        
        title = QLabel("Prévisualisation des changements")
        title.setProperty("title", "true")
        header_layout.addWidget(title)
        
        # Tableau de prévisualisation dans un cadre
        preview_frame = QFrame()
        preview_layout = QVBoxLayout(preview_frame)
        
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels([
            "Nom original", "Nouveau nom", "État"
        ])
        
        # Configuration du tableau
        header = self.preview_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setStretchLastSection(True)
        
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setShowGrid(False)
        
        preview_layout.addWidget(self.preview_table)
        
        # Assemblage final
        layout.addWidget(header)
        layout.addWidget(preview_frame)

    def update_preview(self, files, pattern):
        """Mettre à jour la prévisualisation avec les nouveaux noms"""
        self.preview_table.setRowCount(0)
        if not files or not pattern:
            return
            
        regex = pattern['regex']
        replace = pattern['replace']
        
        # Dictionnaire pour détecter les doublons
        new_names = {}
        
        # Définition des styles pour les différents états
        status_styles = {
            "OK": {
                "icon": "",
                "color": "#4caf50",  # Vert
                "background": "#e8f5e9"
            },
            "WARNING": {
                "icon": "",
                "color": "#ff9800",  # Orange
                "background": "#fff3e0"
            },
            "ERROR": {
                "icon": "",
                "color": "#f44336",  # Rouge
                "background": "#ffebee"
            },
            "UNCHANGED": {
                "icon": "",
                "color": "#9e9e9e",  # Gris
                "background": "#f5f5f5"
            }
        }
        
        for file_path in files:
            old_name = os.path.basename(file_path)
            directory = os.path.dirname(file_path)
            
            try:
                # Application du pattern
                new_name = regex.sub(replace, old_name)
                
                # Détermination du statut
                if new_name in new_names:
                    status = "ERROR"
                    status_text = "Doublon"
                elif new_name == old_name:
                    status = "UNCHANGED"
                    status_text = "Inchangé"
                elif os.path.exists(os.path.join(directory, new_name)):
                    status = "ERROR"
                    status_text = "Existe déjà"
                else:
                    status = "OK"
                    status_text = "OK"
                
                new_names[new_name] = True
                
            except Exception as e:
                new_name = str(e)
                status = "ERROR"
                status_text = "Erreur"
            
            # Ajout de la ligne avec style
            row = self.preview_table.rowCount()
            self.preview_table.insertRow(row)
            
            # Nom original
            old_item = QTableWidgetItem(old_name)
            self.preview_table.setItem(row, 0, old_item)
            
            # Nouveau nom
            new_item = QTableWidgetItem(new_name)
            if status == "ERROR":
                new_item.setForeground(QColor(status_styles[status]["color"]))
            self.preview_table.setItem(row, 1, new_item)
            
            # État
            status_style = status_styles[status]
            status_item = QTableWidgetItem(f"{status_style['icon']} {status_text}")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setForeground(QColor(status_style["color"]))
            status_item.setBackground(QColor(status_style["background"]))
            status_item.setToolTip(status_text)
            self.preview_table.setItem(row, 2, status_item)
            
        # Ajuster les colonnes
        self.preview_table.resizeColumnsToContents()
        self.preview_table.setColumnWidth(2, 100)  # Largeur fixe pour la colonne État
        self.preview_table.resizeRowsToContents()
