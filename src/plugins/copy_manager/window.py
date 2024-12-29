import os
import json
import shutil
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                           QFileDialog, QLabel, QProgressBar, QTextEdit,
                           QCheckBox, QMessageBox, QGroupBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from src.core.logger import Logger
from .copy_manager import CopyManager
from send2trash import send2trash

logger = Logger.get_logger('CopyManager')

class CopyManagerWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Copy Manager")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        self.source_path = None
        self.dest_path = None
        self.copy_manager = CopyManager()
        self.settings_file = os.path.join("data", "copy_manager", "settings.json")
        
        # Créer le dossier de données si nécessaire
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        
        self.load_settings()
        self.init_ui()
    
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        layout = QVBoxLayout()
        
        # Sélection des dossiers
        source_layout = QHBoxLayout()
        self.source_label = QLabel("Dossier source : Non sélectionné")
        if self.source_path:
            self.source_label.setText(f"Dossier source : {self.source_path}")
        self.source_button = QPushButton("📁 Sélectionner source")
        self.source_button.clicked.connect(self.select_source)
        source_layout.addWidget(self.source_label)
        source_layout.addWidget(self.source_button)
        
        dest_layout = QHBoxLayout()
        self.dest_label = QLabel("Dossier destination : Non sélectionné")
        if self.dest_path:
            self.dest_label.setText(f"Dossier destination : {self.dest_path}")
        self.dest_button = QPushButton("📁 Sélectionner destination")
        self.dest_button.clicked.connect(self.select_dest)
        dest_layout.addWidget(self.dest_label)
        dest_layout.addWidget(self.dest_button)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        self.copy_files_cb = QCheckBox("Copier les fichiers")
        self.copy_files_cb.setChecked(True)  # Coché par défaut
        
        self.preserve_metadata_cb = QCheckBox("Préserver les métadonnées")
        self.preserve_metadata_cb.setToolTip(
            "Copie les tags, commentaires, couleurs et autres métadonnées macOS"
        )
        self.preserve_metadata_cb.setChecked(True)
        
        self.include_hidden_cb = QCheckBox("Inclure les fichiers cachés")
        self.include_hidden_cb.setToolTip(
            "Inclut les fichiers et dossiers commençant par un point (.)"
        )
        
        self.delete_after_copy = QCheckBox("Supprimer les fichiers après la copie")
        self.delete_after_copy.setToolTip("Les fichiers source seront déplacés dans la corbeille après la copie")
        
        options_layout.addWidget(self.copy_files_cb)
        options_layout.addWidget(self.preserve_metadata_cb)
        options_layout.addWidget(self.include_hidden_cb)
        options_layout.addWidget(self.delete_after_copy)
        
        options_group.setLayout(options_layout)
        layout.addLayout(source_layout)
        layout.addLayout(dest_layout)
        layout.addWidget(options_group)
        
        # Boutons d'action
        buttons_layout = QHBoxLayout()
        
        buttons_layout.addStretch()
        
        self.copy_btn = QPushButton("✨ Copier")
        self.copy_btn.clicked.connect(self.start_copy)
        buttons_layout.addWidget(self.copy_btn)
        
        self.stop_btn = QPushButton("⏹️ Arrêter")
        self.stop_btn.clicked.connect(self.stop_copy)
        self.stop_btn.setEnabled(False)
        buttons_layout.addWidget(self.stop_btn)
        
        self.close_btn = QPushButton("❌ Fermer")
        self.close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Journal des opérations
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        self.setLayout(layout)
    
    def load_settings(self):
        """Charge les paramètres sauvegardés"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.source_path = settings.get('source_path')
                    self.dest_path = settings.get('dest_path')
        except Exception as e:
            logger.error(f"Erreur lors du chargement des paramètres : {str(e)}")
    
    def save_settings(self):
        """Sauvegarde les paramètres"""
        try:
            settings = {
                'source_path': self.source_path,
                'dest_path': self.dest_path
            }
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des paramètres : {str(e)}")
    
    def select_source(self):
        """Sélectionne le dossier source"""
        path = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier source")
        if path:
            self.source_path = path
            self.source_label.setText(f"Dossier source : {path}")
            self.update_copy_button()
            self.save_settings()
    
    def select_dest(self):
        """Sélectionne le dossier destination"""
        path = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier destination")
        if path:
            self.dest_path = path
            self.dest_label.setText(f"Dossier destination : {path}")
            self.update_copy_button()
            self.save_settings()
    
    def update_copy_button(self):
        """Active le bouton copier si les deux dossiers sont sélectionnés"""
        self.copy_btn.setEnabled(bool(self.source_path is not None and self.dest_path is not None))
    
    def log_message(self, message):
        """Ajoute un message au journal"""
        self.log_text.append(message)
    
    def start_copy(self):
        """Démarre la copie des fichiers"""
        if not self.source_path or not self.dest_path:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner les dossiers source et destination")
            return
            
        # Désactiver les contrôles pendant la copie
        self.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Créer et démarrer le thread de copie
        self.copy_thread = CopyThread(
            self.source_path,
            self.dest_path,
            self.copy_files_cb.isChecked(),
            self.preserve_metadata_cb.isChecked(),
            self.include_hidden_cb.isChecked(),
            self.delete_after_copy.isChecked()
        )
        
        # Calculer la taille totale
        total_size = self.copy_thread.copy_manager.calculate_total_size(self.source_path)
        self.log_message(f"Taille totale à copier : {self.format_size(total_size)}")
        
        self.copy_thread.progress.connect(self.update_progress)
        self.copy_thread.message.connect(self.log_message)
        self.copy_thread.finished.connect(self.copy_finished)
        self.copy_thread.start()
    
    def format_size(self, size):
        """Formate une taille en bytes en format lisible"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    
    def update_progress(self, value):
        """Met à jour la barre de progression"""
        self.progress_bar.setValue(value)
    
    def copy_finished(self):
        """Appelé quand la copie est terminée"""
        self.copy_btn.setEnabled(True)
        self.log_message("Copie terminée")
        QMessageBox.information(self, "Terminé", "La copie est terminée")
        self.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def add_files(self):
        pass

    def add_folder(self):
        pass

    def stop_copy(self):
        pass

class CopyThread(QThread):
    progress = pyqtSignal(int)
    message = pyqtSignal(str)
    
    def __init__(self, source, dest, copy_files, preserve_metadata, include_hidden, delete_after_copy):
        super().__init__()
        self.source = source
        self.dest = dest
        self.copy_files = copy_files
        self.preserve_metadata = preserve_metadata
        self.include_hidden = include_hidden
        self.delete_after_copy = delete_after_copy
        self.copy_manager = CopyManager()
    
    def run(self):
        """Exécute la copie en arrière-plan"""
        try:
            total_items = self.copy_manager.count_items(self.source)
            copied_items = 0
            
            for root, dirs, files in os.walk(self.source):
                # Filtrer les fichiers cachés si nécessaire
                if not self.include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    files = [f for f in files if not f.startswith('.')]
                
                # Créer le dossier de destination
                rel_path = os.path.relpath(root, self.source)
                dest_root = os.path.join(self.dest, rel_path)
                
                if not os.path.exists(dest_root):
                    os.makedirs(dest_root)
                    if self.preserve_metadata:
                        self.copy_manager.copy_metadata(root, dest_root)
                    self.message.emit(f"Créé dossier : {dest_root}")
                    copied_items += 1
                    self.progress.emit(int(copied_items * 100 / total_items))
                
                # Copier les fichiers si l'option est activée
                if self.copy_files:
                    for file in files:
                        src_file = os.path.join(root, file)
                        dest_file = os.path.join(dest_root, file)
                        
                        # Vérifier si le fichier existe déjà
                        if os.path.exists(dest_file):
                            dest_file = self.copy_manager.get_unique_name(dest_file)
                        
                        shutil.copy2(src_file, dest_file)
                        if self.preserve_metadata:
                            self.copy_manager.copy_metadata(src_file, dest_file)
                        
                        self.message.emit(f"Copié : {dest_file}")
                        copied_items += 1
                        self.progress.emit(int(copied_items * 100 / total_items))
                        
                        # Supprimer le fichier source si demandé
                        if self.delete_after_copy:
                            send2trash(src_file)
                            self.message.emit(f"Supprimé : {src_file}")
        
        except Exception as e:
            self.message.emit(f"Erreur : {str(e)}")
            logger.error(f"Erreur lors de la copie : {str(e)}")
