"""Interface utilisateur du plugin MetaRenamer."""

import logging
from pathlib import Path
import json
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTableWidget, QTableWidgetItem, QCheckBox,
    QFileDialog, QMessageBox, QHeaderView, QLabel
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor
import osxmetadata

logger = logging.getLogger("VideoFlow.MetaRenamer.Window")

class MetaRenamerWindow(QMainWindow):
    """Fenêtre principale du plugin MetaRenamer."""
    
    def __init__(self):
        """Initialise la fenêtre."""
        super().__init__()
        self.setWindowTitle("Meta Renamer")
        self.setMinimumSize(1000, 800)
        
        self.files_to_check = {}  # {Path: metadata_name}
        self.show_only_diff = False
        self.supported_extensions = {'.mp4', '.mov', '.avi', '.mkv'}
        
        self.init_ui()
        
    def init_ui(self):
        """Initialise l'interface utilisateur."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Boutons du haut
        top_buttons = QHBoxLayout()
        
        self.add_files_btn = QPushButton("📁 Ajouter Fichiers")
        self.add_files_btn.clicked.connect(self.add_files)
        top_buttons.addWidget(self.add_files_btn)
        
        self.add_folder_btn = QPushButton("📂 Ajouter Dossier")
        self.add_folder_btn.clicked.connect(self.add_folder)
        top_buttons.addWidget(self.add_folder_btn)
        
        top_buttons.addStretch()
        
        self.show_diff_cb = QCheckBox("Afficher uniquement les différences")
        self.show_diff_cb.stateChanged.connect(self.refresh_files_list)
        top_buttons.addWidget(self.show_diff_cb)
        
        self.sync_all_btn = QPushButton("✨ Synchroniser Tout")
        self.sync_all_btn.clicked.connect(self.sync_all)
        top_buttons.addWidget(self.sync_all_btn)
        
        layout.addLayout(top_buttons)
        
        # Tableau des fichiers
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(4)
        header_items = [
            ("Nom du Fichier", "Nom actuel du fichier"),
            ("Nom Meta", "Nom dans les métadonnées"),
            ("État", "État de la synchronisation"),
            ("Actions", "Actions disponibles")
        ]
        
        for col, (text, tooltip) in enumerate(header_items):
            item = QTableWidgetItem(text)
            item.setToolTip(tooltip)
            self.files_table.setHorizontalHeaderItem(col, item)
        
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.files_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        
        self.files_table.setColumnWidth(2, 100)  # État
        self.files_table.setColumnWidth(3, 100)  # Actions
        
        layout.addWidget(self.files_table)
        
    def add_files(self):
        """Ajoute des fichiers à vérifier."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner les fichiers à vérifier",
            str(Path.home()),
            f"Fichiers vidéo ({' '.join(f'*{ext}' for ext in self.supported_extensions)})"
        )
        
        if files:
            for file in files:
                path = Path(file)
                if path.suffix.lower() in self.supported_extensions:
                    self.files_to_check[path] = self.get_meta_name(path)
            
            self.refresh_files_list()
    
    def add_folder(self):
        """Ajoute un dossier à vérifier."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner le dossier à vérifier",
            str(Path.home())
        )
        
        if folder:
            folder_path = Path(folder)
            for ext in self.supported_extensions:
                for file in folder_path.glob(f"**/*{ext}"):
                    self.files_to_check[file] = self.get_meta_name(file)
            
            self.refresh_files_list()
    
    def get_meta_name(self, file_path):
        """Récupère le nom dans les métadonnées."""
        try:
            meta = osxmetadata.OSXMetaData(str(file_path))
            # Essayer différentes métadonnées dans l'ordre de préférence
            for key in ['kMDItemDisplayName', 'kMDItemTitle']:
                if hasattr(meta, key) and getattr(meta, key):
                    return getattr(meta, key)
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la lecture des métadonnées de {file_path}: {e}")
            return None
    
    def refresh_files_list(self):
        """Rafraîchit la liste des fichiers."""
        self.files_table.setRowCount(0)
        
        for file_path, meta_name in self.files_to_check.items():
            # Si on affiche uniquement les différences, vérifier s'il y en a
            if self.show_diff_cb.isChecked():
                if meta_name is None or file_path.stem == meta_name:
                    continue
            
            row = self.files_table.rowCount()
            self.files_table.insertRow(row)
            
            # Nom du fichier
            file_item = QTableWidgetItem(file_path.name)
            self.files_table.setItem(row, 0, file_item)
            
            # Nom meta
            meta_item = QTableWidgetItem(meta_name if meta_name else "Pas de métadonnées")
            if not meta_name:
                meta_item.setForeground(QColor(128, 128, 128))
            self.files_table.setItem(row, 1, meta_item)
            
            # État
            if meta_name is None:
                status = "Pas de meta"
                color = QColor(128, 128, 128)
            elif file_path.stem == meta_name:
                status = "Synchronisé"
                color = QColor(0, 128, 0)
            else:
                status = "Différent"
                color = QColor(200, 0, 0)
            
            status_item = QTableWidgetItem(status)
            status_item.setForeground(color)
            self.files_table.setItem(row, 2, status_item)
            
            # Bouton de synchronisation
            if meta_name and file_path.stem != meta_name:
                sync_btn = QPushButton("🔄")
                sync_btn.setFixedWidth(30)
                sync_btn.clicked.connect(lambda checked, p=file_path: self.sync_file(p))
                self.files_table.setCellWidget(row, 3, sync_btn)
    
    def sync_file(self, file_path):
        """Synchronise un fichier avec son nom meta."""
        try:
            meta_name = self.files_to_check[file_path]
            if not meta_name:
                return
            
            new_path = file_path.with_stem(meta_name)
            file_path.rename(new_path)
            
            # Mettre à jour le dictionnaire
            self.files_to_check[new_path] = self.files_to_check.pop(file_path)
            
            self.refresh_files_list()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Impossible de renommer {file_path.name}: {str(e)}")
    
    def sync_all(self):
        """Synchronise tous les fichiers avec leurs noms meta."""
        count = 0
        for file_path in list(self.files_to_check.keys()):
            meta_name = self.files_to_check[file_path]
            if meta_name and file_path.stem != meta_name:
                try:
                    new_path = file_path.with_stem(meta_name)
                    file_path.rename(new_path)
                    self.files_to_check[new_path] = self.files_to_check.pop(file_path)
                    count += 1
                except Exception as e:
                    logger.error(f"Erreur lors du renommage de {file_path}: {e}")
        
        self.refresh_files_list()
        if count > 0:
            QMessageBox.information(self, "Succès", f"{count} fichier{'s' if count > 1 else ''} synchronisé{'s' if count > 1 else ''}")
