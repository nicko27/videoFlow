"""
Fenêtre de renommage de fichiers avec patterns prédéfinis
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTableWidget,
    QMessageBox, QFileDialog, QTableWidgetItem,
    QLineEdit, QFrame, QProgressDialog,
    QListWidget, QListWidgetItem, QComboBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QColor

import os
import json
import shutil
from pathlib import Path
import re

from src.utils.replace_pattern import ReplacePattern

class FileRenameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.files = []
        self.patterns = []
        self.patterns_file = os.path.join(os.path.dirname(__file__), "saved_patterns.json")
        self.load_patterns()
        self.add_predefined_patterns()
        self.restore_patterns()

    def setup_ui(self):
        self.setWindowTitle("Renommer les fichiers")
        self.resize(1000, 700)  # Taille réduite
        
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QPushButton {
                padding: 5px 15px;
                border-radius: 5px;
                background-color: #f0f0f0;
                border: 1px solid #ddd;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QTableWidget {
                border: 1px solid #ddd;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        buttons_frame = QFrame()
        buttons_frame.setMaximumHeight(60)
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(10, 5, 10, 5)
        
        add_files_btn = QPushButton("Ajouter des fichiers")
        add_files_btn.clicked.connect(self.add_files)
        add_folder_btn = QPushButton("Ajouter un dossier")
        add_folder_btn.clicked.connect(self.add_folder)
        
        buttons_layout.addWidget(add_files_btn)
        buttons_layout.addWidget(add_folder_btn)
        buttons_layout.addStretch()

        files_frame = QFrame()
        files_layout = QVBoxLayout(files_frame)
        files_layout.setContentsMargins(10, 5, 10, 5)
        
        headers_layout = QHBoxLayout()
        headers_layout.setSpacing(5)
        headers_layout.addWidget(QLabel("Nom actuel"), 1)
        headers_layout.addWidget(QLabel("Nouveau nom"), 1)
        files_layout.addLayout(headers_layout)
        
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(2)
        self.files_table.setHorizontalHeaderLabels(["Nom actuel", "Nouveau nom"])
        self.files_table.horizontalHeader().setStretchLastSection(True)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setShowGrid(False)
        self.files_table.verticalHeader().setDefaultSectionSize(24)
        self.files_table.setMinimumHeight(300)
        files_layout.addWidget(self.files_table)

        patterns_frame = QFrame()
        patterns_frame.setMinimumHeight(400)  # Hauteur minimum garantie
        patterns_layout = QVBoxLayout(patterns_frame)
        patterns_layout.setContentsMargins(10, 5, 10, 5)
        patterns_layout.setSpacing(10)  # Plus d'espace entre les éléments
        
        predef_layout = QHBoxLayout()
        predef_layout.setSpacing(5)
        predef_label = QLabel("Patterns prédéfinis :")
        predef_label.setMinimumWidth(100)
        predef_layout.addWidget(predef_label)
        self.predef_combo = QComboBox()
        self.predef_combo.currentIndexChanged.connect(self.on_predefined_selected)
        predef_layout.addWidget(self.predef_combo, 1)
        add_predef_btn = QPushButton("Ajouter")
        add_predef_btn.clicked.connect(self.add_predefined_pattern)
        predef_layout.addWidget(add_predef_btn)
        patterns_layout.addLayout(predef_layout)
        
        custom_layout = QGridLayout()
        custom_layout.setSpacing(5)
        
        find_label = QLabel("Rechercher :")
        find_label.setMinimumWidth(100)
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Expression ou texte à rechercher")
        
        replace_label = QLabel("Remplacer par :")
        replace_label.setMinimumWidth(100)
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Texte de remplacement ({n} pour numérotation)")
        
        custom_layout.addWidget(find_label, 0, 0)
        custom_layout.addWidget(self.find_input, 0, 1)
        custom_layout.addWidget(replace_label, 1, 0)
        custom_layout.addWidget(self.replace_input, 1, 1)
        
        add_custom_btn = QPushButton("Ajouter pattern personnalisé")
        add_custom_btn.clicked.connect(self.add_pattern)
        custom_layout.addWidget(add_custom_btn, 2, 0, 1, 2)
        
        patterns_layout.addLayout(custom_layout)
        
        active_label = QLabel("Patterns actifs :")
        active_label.setMinimumWidth(100)
        patterns_layout.addWidget(active_label)
        
        self.patterns_list = QListWidget()
        self.patterns_list.setAlternatingRowColors(True)
        self.patterns_list.setMinimumHeight(200)  # Plus de hauteur pour la liste
        patterns_layout.addWidget(self.patterns_list)
        
        pattern_buttons = QHBoxLayout()
        pattern_buttons.setSpacing(5)
        
        move_up_btn = QPushButton("↑ Monter")
        move_up_btn.clicked.connect(lambda: self.move_pattern(-1))
        move_down_btn = QPushButton("↓ Descendre")
        move_down_btn.clicked.connect(lambda: self.move_pattern(1))
        remove_pattern_btn = QPushButton("Supprimer")
        remove_pattern_btn.clicked.connect(self.remove_pattern)
        clear_patterns_btn = QPushButton("Tout effacer")
        clear_patterns_btn.clicked.connect(self.clear_patterns)
        
        pattern_buttons.addWidget(move_up_btn)
        pattern_buttons.addWidget(move_down_btn)
        pattern_buttons.addWidget(remove_pattern_btn)
        pattern_buttons.addWidget(clear_patterns_btn)
        patterns_layout.addLayout(pattern_buttons)

        actions_frame = QFrame()
        actions_frame.setMinimumHeight(50)  # Hauteur minimale réduite
        actions_layout = QHBoxLayout(actions_frame)
        actions_layout.setContentsMargins(10, 5, 10, 5)
        
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

        layout.addWidget(buttons_frame)
        layout.addWidget(files_frame, 1)  # Ratio 1
        layout.addWidget(patterns_frame, 1)  # Ratio 1
        layout.addWidget(actions_frame)

    def load_patterns(self):
        """Charge les patterns sauvegardés depuis le fichier JSON"""
        try:
            if os.path.exists(self.patterns_file):
                with open(self.patterns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.patterns = [ReplacePattern(p["find"], p["replace"], p["is_regex"]) 
                                   for p in data]
        except Exception as e:
            print(f"Erreur lors du chargement des patterns : {e}")
            self.patterns = []

    def save_patterns(self):
        """Sauvegarde les patterns dans le fichier JSON"""
        try:
            data = [{"find": p.find, "replace": p.replace, "is_regex": p.is_regex} 
                    for p in self.patterns]
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des patterns : {e}")

    def restore_patterns(self):
        """Restaure les patterns sauvegardés dans la liste"""
        self.patterns_list.clear()
        for pattern in self.patterns:
            item = QListWidgetItem(f"{pattern.find} → {pattern.replace}")
            self.patterns_list.addItem(item)
        self.update_preview()

    def add_predefined_patterns(self):
        """Ajouter les patterns prédéfinis à la combobox"""
        self.predefined_patterns = ReplacePattern.get_predefined_patterns()
        for pattern in self.predefined_patterns:
            self.predef_combo.addItem(pattern.description)

    def on_predefined_selected(self, index):
        """Quand un pattern prédéfini est sélectionné"""
        if index >= 0:
            pattern = self.predefined_patterns[index]
            self.find_input.setText(pattern.find)
            self.replace_input.setText(pattern.replace)

    def add_predefined_pattern(self):
        """Ajoute le pattern prédéfini sélectionné"""
        index = self.predef_combo.currentIndex()
        if index >= 0:
            pattern = self.predefined_patterns[index]
            self.patterns.append(pattern)
            item = QListWidgetItem(f"{pattern.description} ('{pattern.find}' → '{pattern.replace}')")
            self.patterns_list.addItem(item)
            self.save_patterns()
            self.update_preview()

    def move_pattern(self, direction):
        """Déplace le pattern sélectionné vers le haut ou le bas"""
        current_row = self.patterns_list.currentRow()
        if current_row < 0:
            return
            
        new_row = current_row + direction
        if 0 <= new_row < self.patterns_list.count():
            # Déplace dans la liste visuelle
            item = self.patterns_list.takeItem(current_row)
            self.patterns_list.insertItem(new_row, item)
            self.patterns_list.setCurrentRow(new_row)
            
            # Déplace dans la liste des patterns
            pattern = self.patterns.pop(current_row)
            self.patterns.insert(new_row, pattern)
            
            self.save_patterns()
            self.update_preview()

    def add_pattern(self):
        """Ajoute un pattern personnalisé à la liste"""
        find = self.find_input.text().strip()
        replace = self.replace_input.text().strip()
        
        if not find:
            return
            
        pattern = ReplacePattern(find, replace)
        self.patterns.append(pattern)
        
        item = QListWidgetItem(f"{find} → {replace}")
        self.patterns_list.addItem(item)
        
        self.find_input.clear()
        self.replace_input.clear()
        
        self.save_patterns()
        self.update_preview()

    def remove_pattern(self):
        """Supprime le pattern sélectionné"""
        current_row = self.patterns_list.currentRow()
        if current_row >= 0:
            self.patterns_list.takeItem(current_row)
            self.patterns.pop(current_row)
            self.save_patterns()
            self.update_preview()

    def clear_patterns(self):
        """Supprime tous les patterns"""
        self.patterns_list.clear()
        self.patterns.clear()
        self.save_patterns()
        self.update_preview()

    def add_files(self):
        """Ajoute des fichiers"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner des fichiers vidéo",
            "",
            "Fichiers vidéo (*.mp4 *.mkv *.avi *.mov *.wmv);;Tous les fichiers (*.*)"
        )
        
        if files:
            # Ajoute les nouveaux fichiers à ceux existants
            existing_paths = {path for path, _, _ in self.files}
            new_files = [(f, os.path.basename(f), "") for f in sorted(files) 
                        if f not in existing_paths]
            self.files.extend(new_files)
            self.update_preview()
            self.rename_btn.setEnabled(bool(self.files))

    def add_folder(self):
        """Ajoute un dossier"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner un dossier",
            ""
        )
        
        if folder:
            # Récupère tous les fichiers vidéo du dossier
            video_files = []
            for ext in ['*.mp4', '*.mkv', '*.avi', '*.mov', '*.wmv']:
                video_files.extend(
                    str(p) for p in Path(folder).rglob(ext)
                )
            
            # Ajoute les nouveaux fichiers à ceux existants
            existing_paths = {path for path, _, _ in self.files}
            new_files = [(f, os.path.basename(f), "") for f in sorted(video_files) 
                        if f not in existing_paths]
            self.files.extend(new_files)
            self.update_preview()
            self.rename_btn.setEnabled(bool(self.files))

    def add_files_to_list(self, files):
        """Ajoute des fichiers à la liste"""
        self.files = [(f, os.path.basename(f), "") for f in sorted(files)]
        self.update_preview()
        self.rename_btn.setEnabled(bool(self.files))

    def update_preview(self):
        """Met à jour la prévisualisation des nouveaux noms"""
        self.files_table.setRowCount(len(self.files))
        
        for i, (path, old_name, _) in enumerate(self.files):
            # Nom original
            old_item = QTableWidgetItem(old_name)
            old_item.setToolTip(path)
            self.files_table.setItem(i, 0, old_item)
            
            # Nouveau nom
            new_name = old_name
            try:
                # Appliquer chaque pattern dans l'ordre
                for pattern in self.patterns:
                    new_name = pattern.apply(new_name)
                    
                # Remplacer {n} par le numéro formaté
                new_name = new_name.replace('{n}', f'{i+1:02d}')
                
                # Vérifier les doublons
                if any(f[2] == new_name for f in self.files[:i]):
                    new_item = QTableWidgetItem("⚠️ Doublon")
                    new_item.setForeground(QColor(255, 0, 0))
                    self.files[i] = (path, old_name, "")
                else:
                    new_item = QTableWidgetItem(new_name)
                    new_item.setForeground(QColor(0, 0, 255))
                    self.files[i] = (path, old_name, new_name)
            except Exception as e:
                new_item = QTableWidgetItem("⚠️ Erreur")
                new_item.setForeground(QColor(255, 0, 0))
                self.files[i] = (path, old_name, "")
            
            self.files_table.setItem(i, 1, new_item)
        
        # Ajuster les colonnes
        self.files_table.resizeColumnsToContents()
        
        # Activer/désactiver le bouton de renommage
        has_changes = any(f[2] and f[2] != f[1] for f in self.files)
        self.rename_btn.setEnabled(has_changes)

    def rename_files(self):
        """Renomme les fichiers"""
        # Filtrer les fichiers à renommer
        files_to_rename = [(old, new) for old, _, new in self.files if new and new != os.path.basename(old)]
        
        if not files_to_rename:
            return
            
        # Confirmation
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Voulez-vous renommer {len(files_to_rename)} fichier(s) ?",
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
            len(files_to_rename),
            self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        # Renommage
        errors = []
        renamed = 0
        
        for i, (old_path, new_name) in enumerate(files_to_rename):
            if progress.wasCanceled():
                break
                
            progress.setValue(i)
            
            try:
                new_path = os.path.join(os.path.dirname(old_path), new_name)
                shutil.move(old_path, new_path)
                renamed += 1
            except Exception as e:
                errors.append(f"Erreur pour {old_path}: {str(e)}")
        
        progress.setValue(len(files_to_rename))
        
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
            self.rename_btn.setEnabled(False)
