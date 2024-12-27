"""
Fenêtre de renommage de fichiers avec patterns prédéfinis
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget,
    QMessageBox, QFileDialog, QTableWidgetItem,
    QLineEdit, QFrame, QProgressDialog,
    QListWidget, QListWidgetItem, QComboBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

import os
import shutil
from pathlib import Path
import re

class ReplacePattern:
    def __init__(self, find="", replace="", description=""):
        self.find = find
        self.replace = replace
        self.description = description

    def apply(self, text):
        try:
            pattern = re.compile(self.find)
            return pattern.sub(self.replace, text)
        except re.error:
            return text.replace(self.find, self.replace)

    @staticmethod
    def get_predefined_patterns():
        return [
            ReplacePattern(r"\s+", "_", "Espaces → _"),
            ReplacePattern(r"[^\w\s-]", "", "Supprimer caractères spéciaux"),
            ReplacePattern(r"^(\d+)", "episode_\\1", "Préfixer numéros avec 'episode_'"),
            ReplacePattern(r"[A-Z]", lambda m: m.group().lower(), "Majuscules → minuscules"),
            ReplacePattern(r"_+", "_", "Multiples _ → un seul"),
            ReplacePattern(r"(\d+)", lambda m: m.group(1).zfill(2), "Padding numéros avec 0"),
        ]

class FileRenameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.files = []
        self.patterns = []
        self.add_predefined_patterns()

    def setup_ui(self):
        self.setWindowTitle("Renommer les fichiers")
        self.resize(1200, 800)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 10px;
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
            QLineEdit, QComboBox {
                padding: 8px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #2196f3;
            }
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QLabel {
                color: #333;
                font-weight: bold;
            }
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
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

        # Tableau des fichiers
        files_frame = QFrame()
        files_layout = QVBoxLayout(files_frame)
        
        # En-têtes des colonnes
        headers_layout = QHBoxLayout()
        headers_layout.addWidget(QLabel("Nom actuel"), 1)
        headers_layout.addWidget(QLabel("Nouveau nom"), 1)
        files_layout.addLayout(headers_layout)
        
        # Tableau
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(2)
        self.files_table.setHorizontalHeaderLabels(["Nom actuel", "Nouveau nom"])
        self.files_table.horizontalHeader().setStretchLastSection(True)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setShowGrid(False)
        files_layout.addWidget(self.files_table)

        # Zone des patterns
        patterns_frame = QFrame()
        patterns_layout = QVBoxLayout(patterns_frame)
        
        # Patterns prédéfinis
        predef_layout = QHBoxLayout()
        predef_layout.addWidget(QLabel("Patterns prédéfinis :"))
        self.predef_combo = QComboBox()
        self.predef_combo.currentIndexChanged.connect(self.on_predefined_selected)
        predef_layout.addWidget(self.predef_combo, 1)
        add_predef_btn = QPushButton("Ajouter")
        add_predef_btn.clicked.connect(self.add_predefined_pattern)
        predef_layout.addWidget(add_predef_btn)
        patterns_layout.addLayout(predef_layout)
        
        # Pattern personnalisé
        custom_layout = QVBoxLayout()
        
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Rechercher :"))
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Expression ou texte à rechercher")
        find_layout.addWidget(self.find_input)
        
        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("Remplacer par :"))
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Texte de remplacement ({n} pour numérotation)")
        replace_layout.addWidget(self.replace_input)
        
        custom_layout.addLayout(find_layout)
        custom_layout.addLayout(replace_layout)
        
        add_custom_btn = QPushButton("Ajouter pattern personnalisé")
        add_custom_btn.clicked.connect(self.add_pattern)
        custom_layout.addWidget(add_custom_btn)
        
        patterns_layout.addLayout(custom_layout)
        
        # Liste des patterns actifs
        patterns_layout.addWidget(QLabel("Patterns actifs :"))
        self.patterns_list = QListWidget()
        self.patterns_list.setAlternatingRowColors(True)
        patterns_layout.addWidget(self.patterns_list)
        
        # Boutons de gestion des patterns
        pattern_buttons = QHBoxLayout()
        remove_pattern_btn = QPushButton("Supprimer")
        remove_pattern_btn.clicked.connect(self.remove_pattern)
        move_up_btn = QPushButton("↑ Monter")
        move_up_btn.clicked.connect(lambda: self.move_pattern(-1))
        move_down_btn = QPushButton("↓ Descendre")
        move_down_btn.clicked.connect(lambda: self.move_pattern(1))
        clear_patterns_btn = QPushButton("Tout effacer")
        clear_patterns_btn.clicked.connect(self.clear_patterns)
        
        pattern_buttons.addWidget(move_up_btn)
        pattern_buttons.addWidget(move_down_btn)
        pattern_buttons.addWidget(remove_pattern_btn)
        pattern_buttons.addWidget(clear_patterns_btn)
        patterns_layout.addLayout(pattern_buttons)

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
        layout.addWidget(files_frame, 1)
        layout.addWidget(patterns_frame)
        layout.addWidget(actions_frame)

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
        """Ajouter le pattern prédéfini sélectionné"""
        index = self.predef_combo.currentIndex()
        if index >= 0:
            pattern = self.predefined_patterns[index]
            self.patterns.append(pattern)
            item = QListWidgetItem(f"{pattern.description} ('{pattern.find}' → '{pattern.replace}')")
            self.patterns_list.addItem(item)
            self.update_preview()

    def move_pattern(self, direction):
        """Déplacer un pattern vers le haut ou le bas"""
        current_row = self.patterns_list.currentRow()
        if current_row < 0:
            return
            
        new_row = current_row + direction
        if 0 <= new_row < self.patterns_list.count():
            # Déplacer dans la liste visuelle
            item = self.patterns_list.takeItem(current_row)
            self.patterns_list.insertItem(new_row, item)
            self.patterns_list.setCurrentRow(new_row)
            
            # Déplacer dans la liste des patterns
            pattern = self.patterns.pop(current_row)
            self.patterns.insert(new_row, pattern)
            
            self.update_preview()

    def add_pattern(self):
        """Ajouter un pattern à la liste"""
        find = self.find_input.text().strip()
        replace = self.replace_input.text().strip()
        
        if find:
            pattern = ReplacePattern(find, replace)
            self.patterns.append(pattern)
            
            # Ajouter à la liste visuelle
            item = QListWidgetItem(f"'{find}' → '{replace}'")
            self.patterns_list.addItem(item)
            
            # Réinitialiser les champs
            self.find_input.clear()
            self.replace_input.clear()
            
            # Mettre à jour la prévisualisation
            self.update_preview()

    def remove_pattern(self):
        """Supprimer le pattern sélectionné"""
        current_row = self.patterns_list.currentRow()
        if current_row >= 0:
            self.patterns_list.takeItem(current_row)
            self.patterns.pop(current_row)
            self.update_preview()

    def clear_patterns(self):
        """Effacer tous les patterns"""
        self.patterns_list.clear()
        self.patterns = []
        self.update_preview()

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
                    new_item.setForeground(Qt.GlobalColor.red)
                    self.files[i] = (path, old_name, "")
                else:
                    new_item = QTableWidgetItem(new_name)
                    new_item.setForeground(Qt.GlobalColor.blue)
                    self.files[i] = (path, old_name, new_name)
            except Exception as e:
                new_item = QTableWidgetItem("⚠️ Erreur")
                new_item.setForeground(Qt.GlobalColor.red)
                self.files[i] = (path, old_name, "")
            
            self.files_table.setItem(i, 1, new_item)
        
        # Ajuster les colonnes
        self.files_table.resizeColumnsToContents()
        
        # Activer/désactiver le bouton de renommage
        has_changes = any(f[2] and f[2] != f[1] for f in self.files)
        self.rename_btn.setEnabled(has_changes)

    def rename_files(self):
        """Renommer les fichiers"""
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
