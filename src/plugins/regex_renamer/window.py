from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QSplitter, QTextEdit, QMenu, QMenuBar,
    QStatusBar, QToolBar, QFileDialog, QMessageBox, QTableWidgetItem,
    QCheckBox, QHeaderView, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QColor, QPalette, QAction
import os
from pathlib import Path
from typing import List, Dict, Optional
import json
import re
import subprocess

class RegexRenamerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Regex Renamer")
        self.setMinimumSize(1000, 800)
        
        self.files_to_rename = {}
        self.show_hidden = False
        self.ignored_extensions = {'.part', '.crdownload', '.download', '.tmp'}
        self.patterns_file = Path.home() / '.regex_renamer_patterns.json'
        self.file_extensions = set()  # Extensions trouvées
        self.selected_extensions = set()  # Extensions sélectionnées
        
        self.init_ui()
        self.load_patterns()

    def save_patterns(self):
        """Sauvegarde tous les patterns (prédéfinis et personnalisés)."""
        patterns = []
        for row in range(self.patterns_table.rowCount()):
            pattern_info = self.get_pattern_info(row, check_active=False)
            if pattern_info:
                pattern_item = self.patterns_table.item(row, 1)
                patterns.append({
                    'pattern': pattern_info['pattern'],
                    'replace': pattern_info['replace'],
                    'case_sensitive': pattern_info['case_sensitive'],
                    'word': pattern_info['word'],
                    'start': pattern_info['start'],
                    'end': pattern_info['end'],
                    'description': pattern_item.toolTip() if pattern_item.toolTip() else '',
                    'is_active': self.patterns_table.cellWidget(row, 0).isChecked()
                })
        
        try:
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(patterns, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Impossible de sauvegarder les patterns : {str(e)}")

    def get_predefined_patterns(self):
        """Retourne la liste des patterns prédéfinis."""
        return [
            {
                'pattern': r"\([^)]*\)",
                'replace': "",
                'case_sensitive': False,
                'word': False,
                'start': False,
                'end': False,
                'description': "Supprime tout texte entre parenthèses",
                'is_active': True
            },
            {
                'pattern': r"\s+",
                'replace': "",
                'case_sensitive': True,
                'word': True,
                'start': True,
                'end': True,
                'description': "Supprime tous les espaces dans le nom",
                'is_active': True
            },
            {
                'pattern': r"[0-9]+",
                'replace': "",
                'case_sensitive': False,
                'word': False,
                'start': False,
                'end': False,
                'description': "Supprime tous les chiffres du nom",
                'is_active': True
            },
            {
                'pattern': r"(?:^|(?<= ))#\w+(?= |$)",
                'replace': "",
                'case_sensitive': False,
                'word': False,
                'start': False,
                'end': False,
                'description': "Supprime les mots commençant par # (hashtags)",
                'is_active': True
            },
            {
                'pattern': r"^[0-9]+[-_ ]",
                'replace': "",
                'case_sensitive': False,
                'word': False,
                'start': True,
                'end': False,
                'description': "Supprime les numéros au début du nom",
                'is_active': True
            },
            {
                'pattern': r"[.](?![^.]*$)",
                'replace': " ",
                'case_sensitive': False,
                'word': False,
                'start': False,
                'end': False,
                'description': "Remplace les points par des espaces (préserve l'extension)",
                'is_active': True
            },
            {
                'pattern': r"\s+",
                'replace': "_",
                'case_sensitive': False,
                'word': False,
                'start': False,
                'end': False,
                'description': "Remplace tous les espaces par des tirets bas (_) ",
                'is_active': True
            },
            {
                'pattern': r"_+",
                'replace': " ",
                'case_sensitive': False,
                'word': False,
                'start': False,
                'end': False,
                'description': "Remplace tous les tirets bas par des espaces",
                'is_active': True
            }
        ]

    def load_patterns(self):
        """Charge les patterns prédéfinis et personnalisés."""
        # Charger les patterns sauvegardés
        saved_patterns = []
        try:
            if self.patterns_file.exists():
                with open(self.patterns_file, 'r', encoding='utf-8') as f:
                    saved_patterns = json.load(f)
        except Exception:
            # En cas d'erreur, utiliser les patterns prédéfinis
            saved_patterns = self.get_predefined_patterns()
        
        # Si aucun pattern n'est sauvegardé, utiliser les prédéfinis
        if not saved_patterns:
            saved_patterns = self.get_predefined_patterns()
        
        # Ajouter les patterns à la table
        self.patterns_table.setRowCount(0)
        for pattern in saved_patterns:
            self.add_pattern_to_table(
                pattern['pattern'],
                pattern['replace'],
                pattern.get('case_sensitive', False),
                pattern.get('word', False),
                pattern.get('start', False),
                pattern.get('end', False),
                pattern.get('description', ''),
                pattern.get('is_active', True)
            )

    def add_pattern_to_table(self, pattern, replace="", case=False, word=False, start=False, end=False, description="", is_active=True):
        """Ajoute un pattern à la table avec les options spécifiées."""
        row = self.patterns_table.rowCount()
        self.patterns_table.insertRow(row)
        
        # Case à cocher "Utiliser"
        checkbox = QCheckBox()
        checkbox.setChecked(is_active)
        self.patterns_table.setCellWidget(row, 0, checkbox)
        checkbox.stateChanged.connect(self.update_preview)
        
        # Pattern et remplacement
        pattern_item = QTableWidgetItem(pattern)
        if description:
            pattern_item.setToolTip(description)
        self.patterns_table.setItem(row, 1, pattern_item)
        self.patterns_table.setItem(row, 2, QTableWidgetItem(replace))
        
        # Case à cocher "Respecter Maj/Min"
        case_checkbox = QCheckBox()
        case_checkbox.setChecked(case)
        self.patterns_table.setCellWidget(row, 3, case_checkbox)
        case_checkbox.stateChanged.connect(self.update_preview)
        
        # Widget de position
        pos_widget = QWidget()
        pos_layout = QHBoxLayout(pos_widget)
        pos_layout.setContentsMargins(2, 2, 2, 2)
        word_cb = QCheckBox("Mot complet")
        word_cb.setToolTip("Ne remplacer que si le texte forme un mot complet\n(pas une partie d'un mot plus long)")
        start_cb = QCheckBox("Début")
        start_cb.setToolTip("Chercher au début du nom")
        end_cb = QCheckBox("Fin")
        end_cb.setToolTip("Chercher à la fin du nom")
        
        word_cb.setChecked(word)
        start_cb.setChecked(start)
        end_cb.setChecked(end)
        
        pos_layout.addWidget(word_cb)
        pos_layout.addWidget(start_cb)
        pos_layout.addWidget(end_cb)
        self.patterns_table.setCellWidget(row, 4, pos_widget)
        
        # Connecter les changements d'état
        for cb in (word_cb, start_cb, end_cb):
            cb.stateChanged.connect(self.update_preview)
        
        # Bouton de suppression
        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedWidth(30)
        delete_btn.clicked.connect(lambda: self.delete_pattern(self.patterns_table.indexAt(delete_btn.pos()).row()))
        self.patterns_table.setCellWidget(row, 5, delete_btn)

    def delete_pattern(self, row):
        """Supprime un pattern de la table."""
        if row >= 0 and row < self.patterns_table.rowCount():
            self.patterns_table.removeRow(row)
            self.save_patterns()
            self.update_preview()

    def add_pattern(self):
        """Ajoute un nouveau pattern vide."""
        self.add_pattern_to_table("")
        self.save_patterns()

    def apply_pattern(self, text, pattern_info):
        """Applique un pattern avec les options spécifiées."""
        pattern = pattern_info["pattern"]
        if not pattern:
            return text
            
        # Construire le pattern final selon les options
        if pattern_info["word"]:
            pattern = fr"\b{pattern}\b"
        if pattern_info["start"]:
            pattern = f"^{pattern}"
        if pattern_info["end"]:
            pattern = f"{pattern}$"
            
        try:
            flags = 0 if pattern_info["case_sensitive"] else re.IGNORECASE
            return re.sub(pattern, pattern_info["replace"], text, flags=flags)
        except re.error:
            return text

    def update_preview(self):
        """Met à jour la prévisualisation des nouveaux noms."""
        for row in range(self.files_table.rowCount()):
            original_name = self.files_table.item(row, 0).text()
            
            # Séparer le nom et l'extension
            name_parts = original_name.rsplit('.', 1)
            base_name = name_parts[0]
            extension = name_parts[1] if len(name_parts) > 1 else ""
            
            # Récupérer tous les patterns actifs et les trier par impact
            active_patterns = []
            for pattern_row in range(self.patterns_table.rowCount()):
                pattern_info = self.get_pattern_info(pattern_row)
                if pattern_info:
                    impact = self.estimate_pattern_impact(pattern_info, base_name)
                    active_patterns.append((impact, pattern_row, pattern_info))
            
            # Trier les patterns par impact décroissant
            active_patterns.sort(key=lambda x: x[0], reverse=True)
            
            # Appliquer les patterns jusqu'à ce qu'il n'y ait plus de changement
            new_name = base_name
            changed = True
            while changed:
                changed = False
                previous_name = new_name
                
                # Appliquer les patterns dans l'ordre d'impact
                for _, _, pattern_info in active_patterns:
                    result = self.apply_pattern(new_name, pattern_info)
                    if result != new_name:
                        new_name = result
                        changed = True
                
                # Éviter une boucle infinie si les patterns se neutralisent
                if new_name == previous_name:
                    changed = False
            
            # Reconstruire le nom complet avec l'extension
            final_name = new_name + ('.' + extension if extension else '')
            
            # Mettre à jour le nouveau nom
            new_name_item = QTableWidgetItem(final_name)
            if final_name != original_name:
                new_name_item.setForeground(QColor(0, 128, 0))
            if len(final_name) > 40:
                new_name_item.setToolTip(final_name)
            self.files_table.setItem(row, 1, new_name_item)

    def estimate_pattern_impact(self, pattern_info, sample_text):
        """Estime l'impact d'un pattern en comptant les caractères supprimés."""
        try:
            # Appliquer le pattern
            result = self.apply_pattern(sample_text, pattern_info)
            # Retourner la différence de longueur
            return len(sample_text) - len(result)
        except Exception:
            return 0

    def init_ui(self):
        """Initialise l'interface utilisateur."""
        # Créer le widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Boutons du haut
        top_buttons = QHBoxLayout()
        
        # Boutons de gauche
        add_files_btn = QPushButton("📁 Ajouter Fichiers")
        add_files_btn.clicked.connect(self.add_files)
        add_folder_btn = QPushButton("📂 Ajouter Dossier")
        add_folder_btn.clicked.connect(self.add_folder)
        add_pattern_btn = QPushButton("➕ Nouveau Pattern")
        add_pattern_btn.clicked.connect(self.add_pattern)
        
        top_buttons.addWidget(add_files_btn)
        top_buttons.addWidget(add_folder_btn)
        top_buttons.addWidget(add_pattern_btn)
        top_buttons.addStretch()
        
        # Boutons de droite
        rename_selected_btn = QPushButton("✨ Renommer Sélection")
        rename_selected_btn.clicked.connect(lambda: self.rename_files(True))
        rename_btn = QPushButton("✨ Renommer Tout")
        rename_btn.clicked.connect(lambda: self.rename_files(False))
        close_btn = QPushButton("❌ Fermer")
        close_btn.clicked.connect(self.close)
        
        top_buttons.addWidget(rename_selected_btn)
        top_buttons.addWidget(rename_btn)
        top_buttons.addWidget(close_btn)
        
        layout.addLayout(top_buttons)
        
        # Tableau des patterns (partie haute)
        self.patterns_table = QTableWidget()
        self.patterns_table.setColumnCount(6)
        self.patterns_table.setHorizontalHeaderLabels([
            "Utiliser", "Chercher", "Remplacer par", "Respecter\nMaj/Min", "Position", "Actions"
        ])
        
        # Ajuster les largeurs des colonnes
        self.patterns_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.patterns_table.setColumnWidth(0, 50)  # Utiliser
        self.patterns_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Chercher
        self.patterns_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Remplacer par
        self.patterns_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.patterns_table.setColumnWidth(3, 80)  # Respecter Maj/Min
        self.patterns_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.patterns_table.setColumnWidth(4, 300)  # Position (encore plus large)
        self.patterns_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.patterns_table.setColumnWidth(5, 60)  # Actions
        
        self.patterns_table.setAlternatingRowColors(True)
        layout.addWidget(self.patterns_table)
        
        # Séparateur
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Options des fichiers
        files_options = QHBoxLayout()
        
        # Checkbox fichiers cachés
        self.show_hidden_cb = QCheckBox("Inclure les fichiers cachés")
        self.show_hidden_cb.setChecked(False)
        self.show_hidden_cb.stateChanged.connect(self.toggle_hidden_files)
        files_options.addWidget(self.show_hidden_cb)
        
        # Filtre par extension
        files_options.addWidget(QLabel("Types de fichiers :"))
        self.extension_combo = QComboBox()
        self.extension_combo.addItem("Tous les types")
        self.extension_combo.currentTextChanged.connect(self.filter_by_extension)
        files_options.addWidget(self.extension_combo)
        
        files_options.addStretch()
        layout.addLayout(files_options)
        
        # Tableau des fichiers (partie basse)
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(2)
        header_item0 = QTableWidgetItem("Nom Original")
        header_item0.setToolTip("Cliquer pour trier par ordre alphabétique")
        header_item1 = QTableWidgetItem("Nouveau Nom")
        header_item1.setToolTip("Cliquer pour trier par modification ou ordre alphabétique")
        
        self.files_table.setHorizontalHeaderItem(0, header_item0)
        self.files_table.setHorizontalHeaderItem(1, header_item1)
        
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSortingEnabled(True)
        self.files_table.horizontalHeader().setSortIndicatorShown(True)
        self.files_table.horizontalHeader().sectionClicked.connect(self.handle_sort)
        
        layout.addWidget(self.files_table)
        
        # Définir les proportions (40% patterns, 60% fichiers)
        layout.setStretch(2, 4)  # patterns_table
        layout.setStretch(5, 6)  # files_table

    def get_pattern_info(self, row, check_active=True):
        """Récupère les informations d'un pattern."""
        # Vérifier si le pattern est actif
        checkbox = self.patterns_table.cellWidget(row, 0)
        if not checkbox or (check_active and not checkbox.isChecked()):
            return None
            
        # Récupérer le pattern et le remplacement depuis les QTableWidgetItem
        pattern_item = self.patterns_table.item(row, 1)
        replace_item = self.patterns_table.item(row, 2)
        if not pattern_item or not pattern_item.text():
            return None
            
        # Récupérer les options
        case_checkbox = self.patterns_table.cellWidget(row, 3)
        pos_widget = self.patterns_table.cellWidget(row, 4)
        
        if not case_checkbox or not pos_widget:
            return None
            
        case_sensitive = case_checkbox.isChecked()
        checkboxes = pos_widget.findChildren(QCheckBox)
        if len(checkboxes) < 3:
            return None
            
        word = checkboxes[0].isChecked()
        start = checkboxes[1].isChecked()
        end = checkboxes[2].isChecked()
        
        return {
            "pattern": pattern_item.text(),
            "replace": replace_item.text() if replace_item else "",
            "case_sensitive": case_sensitive,
            "word": word,
            "start": start,
            "end": end
        }

    def is_hidden(self, path):
        """Vérifie si un fichier est caché ou à ignorer."""
        # Vérifier si c'est un fichier caché
        if path.name.startswith('.') or any(p.name.startswith('.') for p in path.parents):
            return True
            
        # Vérifier si c'est une extension à ignorer
        if path.suffix.lower() in self.ignored_extensions:
            return True
            
        return False

    def add_table_item(self, row, col, text, original_text=None):
        """Ajoute un item dans le tableau avec infobulle et formatage."""
        item = QTableWidgetItem(text)
        
        # Ajouter une infobulle si le texte est long
        if len(text) > 40:
            item.setToolTip(text)
        
        # Si c'est la colonne du nouveau nom et qu'il est différent de l'original
        if col == 1 and original_text is not None and text != original_text:
            item.setForeground(QColor(0, 128, 0))
            # Ajouter une infobulle montrant le changement
            item.setToolTip(f"Original : {original_text}\nNouveau : {text}")
        
        self.files_table.setItem(row, col, item)
        return item

    def toggle_hidden_files(self):
        """Active/désactive l'affichage des fichiers cachés."""
        self.show_hidden = self.show_hidden_cb.isChecked()
        self.refresh_files_list()

    def update_extensions(self):
        """Met à jour la liste des extensions disponibles."""
        old_extensions = self.file_extensions.copy()
        self.file_extensions = {p.suffix.lower() for p in self.files_to_rename.keys() if p.suffix}
        
        if self.file_extensions != old_extensions:
            current_text = self.extension_combo.currentText()
            self.extension_combo.clear()
            self.extension_combo.addItem("Tous les types")
            for ext in sorted(self.file_extensions):
                self.extension_combo.addItem(ext)
            
            # Restaurer la sélection précédente si possible
            index = self.extension_combo.findText(current_text)
            if index >= 0:
                self.extension_combo.setCurrentIndex(index)

    def filter_by_extension(self, extension):
        """Filtre les fichiers par extension."""
        if extension == "Tous les types":
            self.selected_extensions.clear()
        else:
            self.selected_extensions = {extension}
        self.refresh_files_list()

    def should_show_file(self, path):
        """Détermine si un fichier doit être affiché."""
        # Vérifier les fichiers cachés
        if not self.show_hidden and self.is_hidden(path):
            return False
            
        # Vérifier l'extension
        if self.selected_extensions and path.suffix.lower() not in self.selected_extensions:
            return False
            
        return True

    def refresh_files_list(self):
        """Rafraîchit la liste des fichiers selon les options."""
        # Sauvegarder l'état de tri actuel
        sort_column = self.files_table.horizontalHeader().sortIndicatorSection()
        sort_order = self.files_table.horizontalHeader().sortIndicatorOrder()
        
        self.files_table.setSortingEnabled(False)  # Désactiver le tri pendant la mise à jour
        self.files_table.setRowCount(0)
        
        for file_path in self.files_to_rename.keys():
            if not self.should_show_file(file_path):
                continue
                
            row = self.files_table.rowCount()
            self.files_table.insertRow(row)
            
            # Afficher le nom du fichier
            self.add_table_item(row, 0, file_path.name)
            
            # Nouveau nom (initialement identique)
            self.add_table_item(row, 1, file_path.name, file_path.name)
        
        self.files_table.setSortingEnabled(True)  # Réactiver le tri
        
        # Restaurer l'état de tri
        self.files_table.horizontalHeader().setSortIndicator(sort_column, sort_order)
        
        self.update_preview()

    def handle_sort(self, logical_index):
        """Gère le tri personnalisé des colonnes."""
        if logical_index == 1:  # Colonne "Nouveau Nom"
            # Récupérer l'ordre de tri actuel
            order = self.files_table.horizontalHeader().sortIndicatorOrder()
            is_ascending = order == Qt.SortOrder.AscendingOrder
            
            # Créer une liste de tuples (row, is_modified, name) pour le tri
            items = []
            for row in range(self.files_table.rowCount()):
                original = self.files_table.item(row, 0).text()
                new_name = self.files_table.item(row, 1).text()
                is_modified = original != new_name
                items.append((row, is_modified, new_name))
            
            # Trier d'abord par modification, puis par nom
            items.sort(key=lambda x: (x[1], x[2]), reverse=not is_ascending)
            
            # Réorganiser les lignes
            for new_row, (old_row, _, _) in enumerate(items):
                self.move_table_row(old_row, new_row)
        
        # Pour la colonne 0, le tri par défaut (alphabétique) est utilisé

    def move_table_row(self, old_row, new_row):
        """Déplace une ligne du tableau vers une nouvelle position."""
        if old_row == new_row:
            return
            
        # Sauvegarder les items de la ligne
        items = []
        for col in range(self.files_table.columnCount()):
            items.append(self.files_table.takeItem(old_row, col))
        
        # Supprimer l'ancienne ligne
        self.files_table.removeRow(old_row)
        
        # Insérer la nouvelle ligne
        self.files_table.insertRow(new_row)
        
        # Restaurer les items
        for col, item in enumerate(items):
            self.files_table.setItem(new_row, col, item)

    def add_files(self):
        """Ajoute des fichiers à renommer."""
        files, _ = QFileDialog.getOpenFileNames(self, "Ajouter des fichiers")
        for file in files:
            path = Path(file)
            self.files_to_rename[path] = path.name
        
        self.update_extensions()
        self.refresh_files_list()

    def add_folder(self):
        """Ajoute tous les fichiers d'un dossier."""
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier")
        if folder:
            folder_path = Path(folder)
            files = [f for f in folder_path.rglob("*") if f.is_file()]
            
            for file in files:
                self.files_to_rename[file] = file.name
            
            self.update_extensions()
            self.refresh_files_list()

    def rename_files(self, selected_only=False):
        """Renomme les fichiers selon les patterns appliqués."""
        if not self.files_to_rename:
            QMessageBox.warning(self, "Attention", "Aucun fichier à renommer")
            return
        
        # Si on renomme la sélection, vérifier qu'il y a des fichiers sélectionnés
        if selected_only:
            selected_rows = {item.row() for item in self.files_table.selectedItems()}
            if not selected_rows:
                QMessageBox.warning(self, "Attention", "Aucun fichier sélectionné")
                return
        
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Voulez-vous renommer ces fichiers ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for file_path in list(self.files_to_rename.keys()):
                if not self.should_show_file(file_path):
                    continue
                
                # Si on renomme la sélection, vérifier que le fichier est sélectionné
                file_row = None
                for row in range(self.files_table.rowCount()):
                    if self.files_table.item(row, 0).text() == file_path.name:
                        file_row = row
                        break
                
                if file_row is None or (selected_only and file_row not in selected_rows):
                    continue
                
                new_name = self.files_table.item(file_row, 1).text()
                if new_name and new_name != file_path.name:
                    try:
                        new_path = file_path.parent / new_name
                        
                        # Utiliser mv pour préserver les tags macOS
                        subprocess.run(['mv', str(file_path), str(new_path)], check=True)
                        del self.files_to_rename[file_path]
                    except Exception as e:
                        QMessageBox.warning(
                            self,
                            "Erreur",
                            f"Erreur lors du renommage de {file_path.name}: {str(e)}"
                        )
            
            self.refresh_files_list()
            if not self.files_to_rename:
                QMessageBox.information(self, "Succès", "Fichiers renommés avec succès")

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = RegexRenamerWindow()
    window.show()
    sys.exit(app.exec())
