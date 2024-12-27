"""
Fenêtre principale de renommage de fichiers
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QListWidget, QWidget,
    QMessageBox, QFileDialog, QTabWidget, QStyle,
    QListWidgetItem, QFrame, QProgressDialog
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QColor, QPalette

import os
import shutil
from pathlib import Path

from .regex_editor_dialog import RegexEditorDialog
from .pattern_manager_dialog import PatternManagerDialog
from .rename_preview_dialog import RenamePreviewDialog

class FileRenameDialog(QDialog):
    """Fenêtre principale pour le renommage de fichiers"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.selected_files = []
        self.current_pattern = None
        self.rename_operations = []

    def setup_ui(self):
        """Configuration de l'interface utilisateur"""
        self.setWindowTitle("Renommer les fichiers")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 600)

        # Style global
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QSplitter::handle {
                background-color: #e0e0e0;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                margin: 2px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #f0f0f0;
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
            QPushButton:disabled {
                background-color: #bdbdbd;
            }
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                background-color: white;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 4px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                background-color: #f5f5f5;
            }
            QTabBar::tab:selected {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-bottom: none;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e0e0e0;
            }
            QLabel {
                color: #424242;
            }
        """)

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Splitter horizontal principal
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Partie gauche : Liste des fichiers
        files_widget = QWidget()
        files_layout = QVBoxLayout(files_widget)
        files_layout.setSpacing(10)
        
        # En-tête avec titre et boutons
        files_header = QWidget()
        files_header.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
            }
        """)
        header_layout = QVBoxLayout(files_header)
        
        title_layout = QHBoxLayout()
        files_label = QLabel("Fichiers sélectionnés")
        files_label.setStyleSheet("font-size: 16px; font-weight: bold; border: none;")
        title_layout.addWidget(files_label)
        
        buttons_layout = QHBoxLayout()
        add_files_btn = QPushButton("Ajouter des fichiers")
        add_files_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        add_files_btn.clicked.connect(self.add_files)
        
        add_folder_btn = QPushButton("Ajouter un dossier")
        add_folder_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        add_folder_btn.clicked.connect(self.add_folder)
        
        buttons_layout.addWidget(add_files_btn)
        buttons_layout.addWidget(add_folder_btn)
        
        header_layout.addLayout(title_layout)
        header_layout.addLayout(buttons_layout)
        
        # Liste des fichiers
        self.files_list = QListWidget()
        self.files_list.setAlternatingRowColors(True)
        
        files_layout.addWidget(files_header)
        files_layout.addWidget(self.files_list)
        
        # Partie droite : Onglets
        tabs_widget = QTabWidget()
        
        # Onglet 1 : Éditeur Regex
        self.regex_editor = RegexEditorDialog()
        tabs_widget.addTab(self.regex_editor, "Éditeur d'expressions")
        
        # Onglet 2 : Gestionnaire de patterns
        self.pattern_manager = PatternManagerDialog()
        tabs_widget.addTab(self.pattern_manager, "Patterns sauvegardés")
        
        # Onglet 3 : Prévisualisation
        self.preview = RenamePreviewDialog()
        tabs_widget.addTab(self.preview, "Prévisualisation")
        
        # Ajout des widgets au splitter
        main_splitter.addWidget(files_widget)
        main_splitter.addWidget(tabs_widget)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        
        # Boutons d'action dans un cadre
        actions_frame = QFrame()
        actions_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
            }
        """)
        actions_layout = QHBoxLayout(actions_frame)
        actions_layout.setContentsMargins(20, 10, 20, 10)
        
        self.rename_btn = QPushButton("Renommer")
        self.rename_btn.setEnabled(False)
        self.rename_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #43a047;
            }
            QPushButton:pressed {
                background-color: #388e3c;
            }
        """)
        self.rename_btn.clicked.connect(self.rename_files)
        
        cancel_btn = QPushButton("Fermer")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
        """)
        cancel_btn.clicked.connect(self.close)
        
        actions_layout.addStretch()
        actions_layout.addWidget(self.rename_btn)
        actions_layout.addWidget(cancel_btn)
        
        # Assemblage final
        main_layout.addWidget(main_splitter)
        main_layout.addWidget(actions_frame)
        
        # Connexions des signaux
        self.regex_editor.pattern_changed.connect(self.on_pattern_changed)
        self.pattern_manager.pattern_selected.connect(self.regex_editor.set_pattern)
        self.files_list.itemSelectionChanged.connect(self.update_preview)

    def add_files(self):
        """Ajouter des fichiers via une boîte de dialogue"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner des fichiers vidéo",
            "",
            "Vidéos (*.mp4 *.avi *.mkv *.mov);;Tous les fichiers (*.*)"
        )
        if files:
            self.selected_files = files
            self.files_list.clear()
            for file in files:
                item = QListWidgetItem(os.path.basename(file))
                item.setToolTip(file)
                self.files_list.addItem(item)
            self.update_rename_button()
            self.update_preview()

    def add_folder(self):
        """Ajouter tous les fichiers d'un dossier"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner un dossier",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            video_files = []
            for ext in ['*.mp4', '*.avi', '*.mkv', '*.mov']:
                video_files.extend(Path(folder).rglob(ext))
            
            if video_files:
                self.selected_files = [str(f) for f in video_files]
                self.files_list.clear()
                for file in self.selected_files:
                    item = QListWidgetItem(os.path.basename(file))
                    item.setToolTip(file)
                    self.files_list.addItem(item)
                self.update_rename_button()
                self.update_preview()
            else:
                QMessageBox.information(
                    self,
                    "Aucun fichier trouvé",
                    "Aucun fichier vidéo trouvé dans le dossier sélectionné."
                )

    def validate_rename_operations(self):
        """Valider les opérations de renommage"""
        if not self.selected_files or not self.current_pattern:
            return False
            
        regex = self.current_pattern['regex']
        replace = self.current_pattern['replace']
        
        # Réinitialiser les opérations
        self.rename_operations = []
        new_names = set()
        errors = []
        
        for file_path in self.selected_files:
            old_name = os.path.basename(file_path)
            directory = os.path.dirname(file_path)
            
            try:
                # Application du pattern
                new_name = regex.sub(replace, old_name)
                new_path = os.path.join(directory, new_name)
                
                # Vérifications
                if new_name in new_names:
                    errors.append(f"Doublon détecté : {new_name}")
                elif new_name == old_name:
                    continue  # Ignorer les fichiers inchangés
                elif os.path.exists(new_path) and new_path != file_path:
                    errors.append(f"Le fichier existe déjà : {new_name}")
                else:
                    new_names.add(new_name)
                    self.rename_operations.append((file_path, new_path))
                    
            except Exception as e:
                errors.append(f"Erreur pour {old_name}: {str(e)}")
        
        if errors:
            error_msg = "Impossible de renommer les fichiers :\n\n" + "\n".join(errors)
            QMessageBox.warning(self, "Erreurs de validation", error_msg)
            return False
            
        return bool(self.rename_operations)

    def rename_files(self):
        """Renommer les fichiers sélectionnés"""
        if not self.validate_rename_operations():
            return
        
        # Confirmation
        msg = (f"Voulez-vous renommer {len(self.rename_operations)} fichier(s) ?\n\n"
               "Cette opération ne peut pas être annulée.")
        reply = QMessageBox.question(
            self,
            "Confirmation",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Création de la boîte de dialogue de progression
        progress = QProgressDialog(
            "Renommage des fichiers...",
            "Annuler",
            0,
            len(self.rename_operations),
            self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle("Progression")
        
        # Renommage des fichiers
        errors = []
        renamed_count = 0
        
        for i, (old_path, new_path) in enumerate(self.rename_operations):
            if progress.wasCanceled():
                break
                
            progress.setValue(i)
            try:
                # Créer le dossier de destination si nécessaire
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                
                # Renommer le fichier
                shutil.move(old_path, new_path)
                renamed_count += 1
                
            except Exception as e:
                errors.append(f"Erreur lors du renommage de {old_path}: {str(e)}")
        
        progress.setValue(len(self.rename_operations))
        
        # Afficher le résultat
        if errors:
            error_msg = "Erreurs lors du renommage :\n\n" + "\n".join(errors)
            QMessageBox.warning(self, "Erreurs de renommage", error_msg)
        
        if renamed_count > 0:
            success_msg = f"{renamed_count} fichier(s) renommé(s) avec succès."
            if errors:
                success_msg += f"\n{len(errors)} erreur(s) rencontrée(s)."
            QMessageBox.information(self, "Renommage terminé", success_msg)
            
            # Mettre à jour l'interface
            self.files_list.clear()
            self.selected_files = []
            self.rename_operations = []
            self.update_rename_button()
            self.update_preview()

    def on_pattern_changed(self, pattern):
        """Appelé quand le pattern regex change"""
        self.current_pattern = pattern
        self.update_preview()
        self.update_rename_button()

    def update_preview(self):
        """Mettre à jour la prévisualisation"""
        if self.current_pattern and self.selected_files:
            # TODO: Mettre à jour la prévisualisation avec le pattern actuel
            self.preview.update_preview(self.selected_files, self.current_pattern)

    def update_rename_button(self):
        """Activer/désactiver le bouton de renommage"""
        self.rename_btn.setEnabled(
            bool(self.selected_files) and bool(self.current_pattern)
        )
