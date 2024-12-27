"""
Fenêtre de renommage de fichiers simplifiée
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget,
    QMessageBox, QFileDialog, QTableWidgetItem,
    QLineEdit, QFrame, QProgressDialog
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

import os
import shutil
from pathlib import Path
import re

class FileRenameDialog(QDialog):
    """Fenêtre simplifiée pour le renommage de fichiers"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.files = []  # Liste des fichiers [(chemin, nom_original, nouveau_nom)]

    def setup_ui(self):
        """Configuration de l'interface utilisateur"""
        self.setWindowTitle("Renommer les fichiers")
        self.resize(800, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
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
            QLineEdit {
                padding: 8px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #2196f3;
            }
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                gridline-color: #f5f5f5;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-right: 1px solid #e0e0e0;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Boutons d'ajout de fichiers
        buttons_frame = QFrame()
        buttons_layout = QHBoxLayout(buttons_frame)
        
        add_files_btn = QPushButton("Ajouter des fichiers")
        add_files_btn.clicked.connect(self.add_files)
        add_folder_btn = QPushButton("Ajouter un dossier")
        add_folder_btn.clicked.connect(self.add_folder)
        
        buttons_layout.addWidget(add_files_btn)
        buttons_layout.addWidget(add_folder_btn)
        buttons_layout.addStretch()

        # Expression de renommage
        pattern_frame = QFrame()
        pattern_layout = QVBoxLayout(pattern_frame)
        
        pattern_label = QLabel("Expression de renommage :")
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("Exemple : episode_{n} → episode_01, episode_02, ...")
        self.pattern_input.textChanged.connect(self.update_preview)
        
        pattern_help = QLabel("Utilisez {n} pour la numérotation automatique")
        pattern_help.setStyleSheet("color: #666;")
        
        pattern_layout.addWidget(pattern_label)
        pattern_layout.addWidget(self.pattern_input)
        pattern_layout.addWidget(pattern_help)

        # Tableau de prévisualisation
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(2)
        self.files_table.setHorizontalHeaderLabels(["Nom actuel", "Nouveau nom"])
        self.files_table.horizontalHeader().setStretchLastSection(True)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setShowGrid(False)

        # Boutons d'action
        actions_frame = QFrame()
        actions_layout = QHBoxLayout(actions_frame)
        
        self.rename_btn = QPushButton("Renommer")
        self.rename_btn.setEnabled(False)
        self.rename_btn.clicked.connect(self.rename_files)
        self.rename_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #43a047;
            }
        """)
        
        cancel_btn = QPushButton("Fermer")
        cancel_btn.clicked.connect(self.close)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
        """)
        
        actions_layout.addStretch()
        actions_layout.addWidget(self.rename_btn)
        actions_layout.addWidget(cancel_btn)

        # Assemblage final
        layout.addWidget(buttons_frame)
        layout.addWidget(pattern_frame)
        layout.addWidget(self.files_table)
        layout.addWidget(actions_frame)

    def add_files(self):
        """Ajouter des fichiers"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner des fichiers vidéo",
            "",
            "Vidéos (*.mp4 *.avi *.mkv *.mov);;Tous les fichiers (*.*)"
        )
        if files:
            self.add_files_to_list(files)

    def add_folder(self):
        """Ajouter un dossier"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner un dossier",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            files = []
            for ext in ['*.mp4', '*.avi', '*.mkv', '*.mov']:
                files.extend([str(f) for f in Path(folder).rglob(ext)])
            if files:
                self.add_files_to_list(files)
            else:
                QMessageBox.information(
                    self,
                    "Aucun fichier trouvé",
                    "Aucun fichier vidéo trouvé dans le dossier sélectionné."
                )

    def add_files_to_list(self, files):
        """Ajouter des fichiers à la liste"""
        self.files = [(f, os.path.basename(f), "") for f in sorted(files)]
        self.update_preview()
        self.rename_btn.setEnabled(bool(self.files))

    def update_preview(self):
        """Mettre à jour la prévisualisation des nouveaux noms"""
        pattern = self.pattern_input.text()
        
        # Mise à jour du tableau
        self.files_table.setRowCount(len(self.files))
        
        for i, (path, old_name, _) in enumerate(self.files):
            # Nom original
            old_item = QTableWidgetItem(old_name)
            old_item.setToolTip(path)
            self.files_table.setItem(i, 0, old_item)
            
            # Nouveau nom
            if pattern:
                try:
                    # Remplacer {n} par le numéro formaté
                    new_name = pattern.replace('{n}', f'{i+1:02d}')
                    
                    # Garder l'extension d'origine
                    _, ext = os.path.splitext(old_name)
                    if not new_name.endswith(ext):
                        new_name += ext
                        
                    # Vérifier les doublons
                    if any(f[2] == new_name for f in self.files[:i]):
                        new_item = QTableWidgetItem("⚠️ Doublon")
                        new_item.setForeground(Qt.GlobalColor.red)
                    else:
                        new_item = QTableWidgetItem(new_name)
                        new_item.setForeground(Qt.GlobalColor.blue)
                    
                    self.files[i] = (path, old_name, new_name)
                    
                except Exception as e:
                    new_item = QTableWidgetItem("⚠️ Erreur")
                    new_item.setForeground(Qt.GlobalColor.red)
                    self.files[i] = (path, old_name, "")
            else:
                new_item = QTableWidgetItem(old_name)
                self.files[i] = (path, old_name, "")
            
            self.files_table.setItem(i, 1, new_item)
        
        # Ajuster les colonnes
        self.files_table.resizeColumnsToContents()
        
        # Activer/désactiver le bouton de renommage
        valid_renames = bool(pattern) and all(f[2] and not f[2].startswith('⚠️') for f in self.files)
        self.rename_btn.setEnabled(valid_renames)

    def rename_files(self):
        """Renommer les fichiers"""
        # Confirmation
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Voulez-vous renommer {len(self.files)} fichier(s) ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        # Barre de progression
        progress = QProgressDialog(
            "Renommage des fichiers...",
            "Annuler",
            0,
            len(self.files),
            self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        # Renommage
        errors = []
        renamed = 0
        
        for i, (old_path, _, new_name) in enumerate(self.files):
            if progress.wasCanceled():
                break
                
            progress.setValue(i)
            
            try:
                new_path = os.path.join(os.path.dirname(old_path), new_name)
                shutil.move(old_path, new_path)
                renamed += 1
            except Exception as e:
                errors.append(f"Erreur pour {old_path}: {str(e)}")
        
        progress.setValue(len(self.files))
        
        # Rapport
        if errors:
            QMessageBox.warning(
                self,
                "Erreurs",
                "Erreurs lors du renommage :\n\n" + "\n".join(errors)
            )
        
        if renamed > 0:
            QMessageBox.information(
                self,
                "Terminé",
                f"{renamed} fichier(s) renommé(s) avec succès."
            )
            
            # Réinitialiser
            self.files = []
            self.files_table.setRowCount(0)
            self.pattern_input.clear()
            self.rename_btn.setEnabled(False)
