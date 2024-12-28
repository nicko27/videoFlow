"""Interface utilisateur du plugin VideoConverter."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QFileDialog, QMessageBox, QHeaderView, QLabel, QSpinBox,
    QProgressBar, QGroupBox, QFormLayout, QCheckBox, QRadioButton,
    QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from pathlib import Path
from typing import Dict
from .converter import ConversionWorker
from .settings import ConversionSettings, SettingsManager
from .stats import StatsManager
from .metadata import MetadataManager
from src.core.logger import Logger
import os
from PyQt6.QtWidgets import QApplication

logger = Logger.get_logger('VideoConverter.Window')

def format_size(size: int) -> str:
    """Formate une taille en bytes en format lisible."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

class VideoConverterWindow(QMainWindow):
    """Fenêtre principale du plugin VideoConverter."""
    
    def __init__(self):
        """Initialise la fenêtre."""
        super().__init__()
        self.setWindowTitle("Convertisseur Vidéo")
        self.setMinimumSize(800, 600)
        
        # Initialiser les variables
        self.files_to_convert = {}
        self.settings = SettingsManager.load_settings()
        
        # Créer l'interface
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Paramètres de conversion
        settings_group = self.create_settings_group()
        layout.addWidget(settings_group)
        
        # Liste des fichiers
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(6)  # Ajout d'une colonne pour la checkbox
        header_items = [
            ("", "Sélectionner"),  # Colonne de sélection
            ("Nom du fichier", "Nom du fichier à convertir"),
            ("État", "État de la conversion"),
            ("Tentative", "Numéro de la tentative actuelle"),
            ("Taille", "Taille du fichier"),
            ("Actions", "Actions disponibles")
        ]
        
        for col, (text, tooltip) in enumerate(header_items):
            item = QTableWidgetItem(text)
            item.setToolTip(tooltip)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.files_table.setHorizontalHeaderItem(col, item)
        
        # Centrer les en-têtes
        header = self.files_table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.files_table.setColumnWidth(0, 30)  # Largeur de la colonne de sélection
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in range(2, 5):
            self.files_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            self.files_table.setColumnWidth(i, 100)
        self.files_table.setColumnWidth(5, 50)
        
        # Boutons d'action au-dessus de la table
        table_buttons = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Tout sélectionner")
        self.select_all_btn.clicked.connect(self.toggle_select_all)
        table_buttons.addWidget(self.select_all_btn)
        
        table_buttons.addStretch()
        
        layout.addLayout(table_buttons)
        layout.addWidget(self.files_table)
        
        # Boutons d'action
        buttons_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("📁 Ajouter Fichiers")
        self.add_btn.clicked.connect(self.add_files)
        buttons_layout.addWidget(self.add_btn)
        
        self.add_folder_btn = QPushButton("📂 Ajouter Dossier")
        self.add_folder_btn.clicked.connect(self.add_folder)
        buttons_layout.addWidget(self.add_folder_btn)
        
        buttons_layout.addStretch()
        
        self.start_btn = QPushButton("✨ Démarrer")
        self.start_btn.clicked.connect(self.start_conversion)
        buttons_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Arrêter")
        self.stop_btn.clicked.connect(self.stop_conversion)
        self.stop_btn.setEnabled(False)
        buttons_layout.addWidget(self.stop_btn)
        
        self.close_btn = QPushButton("❌ Fermer")
        self.close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)
        
        logger.debug("Fenêtre VideoConverter initialisée")
        
    def create_settings_group(self):
        """Crée le groupe des paramètres."""
        settings_group = QGroupBox("Paramètres")
        layout = QVBoxLayout()
        
        # Mode manuel
        manual_layout = QHBoxLayout()
        self.manual_mode = QCheckBox("Mode manuel")
        self.manual_mode.setChecked(self.settings.manual_mode)
        self.manual_mode.stateChanged.connect(self.toggle_manual_mode)
        manual_layout.addWidget(self.manual_mode)
        
        # Paramètres manuels (initialement cachés)
        self.manual_params = QWidget()
        manual_params_layout = QHBoxLayout()
        
        # CRF
        crf_layout = QHBoxLayout()
        crf_layout.addWidget(QLabel("CRF:"))
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(self.settings.crf)
        crf_layout.addWidget(self.crf_spin)
        manual_params_layout.addLayout(crf_layout)
        
        # Preset
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
        self.preset_combo.setCurrentText(self.settings.preset)
        preset_layout.addWidget(self.preset_combo)
        manual_params_layout.addLayout(preset_layout)
        
        self.manual_params.setLayout(manual_params_layout)
        self.manual_params.setVisible(self.settings.manual_mode)
        manual_layout.addWidget(self.manual_params)
        manual_layout.addStretch()
        layout.addLayout(manual_layout)
        
        # Seuil de taille
        size_layout = QHBoxLayout()
        self.use_threshold = QCheckBox("Utiliser un seuil de taille")
        self.use_threshold.setChecked(self.settings.use_size_threshold)
        size_layout.addWidget(self.use_threshold)
        
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 10000)
        self.size_spin.setValue(int(self.settings.size_threshold / (1024 * 1024)))
        self.size_spin.setSuffix(" MB")
        size_layout.addWidget(self.size_spin)
        size_layout.addStretch()
        layout.addLayout(size_layout)
        
        # Options de conversion
        conversion_layout = QHBoxLayout()
        self.ignore_converted = QCheckBox("Ignorer les fichiers déjà convertis")
        self.ignore_converted.setChecked(self.settings.ignore_converted)
        conversion_layout.addWidget(self.ignore_converted)
        
        self.multiple_attempts = QCheckBox("Faire des essais multiples")
        self.multiple_attempts.setChecked(self.settings.multiple_attempts)
        self.multiple_attempts.stateChanged.connect(self.toggle_attempts_params)
        conversion_layout.addWidget(self.multiple_attempts)
        
        conversion_layout.addStretch()
        layout.addLayout(conversion_layout)
        
        # Paramètres des tentatives
        self.attempts_group = QGroupBox("Paramètres des tentatives")
        attempts_layout = QGridLayout()
        
        # En-têtes
        attempts_layout.addWidget(QLabel("Tentative"), 0, 0)
        attempts_layout.addWidget(QLabel("CRF"), 0, 1)
        attempts_layout.addWidget(QLabel("Preset"), 0, 2)
        
        # Widgets pour chaque tentative
        self.attempt_widgets = []
        for i, attempt in enumerate(self.settings.attempts, 1):
            attempts_layout.addWidget(QLabel(f"{i}"), i, 0)
            
            crf_spin = QSpinBox()
            crf_spin.setRange(0, 51)
            crf_spin.setValue(attempt.crf)
            attempts_layout.addWidget(crf_spin, i, 1)
            
            preset_combo = QComboBox()
            preset_combo.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
            preset_combo.setCurrentText(attempt.preset)
            attempts_layout.addWidget(preset_combo, i, 2)
            
            self.attempt_widgets.append((crf_spin, preset_combo))
        
        self.attempts_group.setLayout(attempts_layout)
        self.attempts_group.setEnabled(self.settings.multiple_attempts)
        layout.addWidget(self.attempts_group)
        
        # Options de suppression
        delete_group = QGroupBox("Options de suppression")
        delete_layout = QVBoxLayout()
        
        self.delete_if_smaller = QCheckBox("Supprimer l'original si le fichier converti est plus petit")
        self.delete_if_smaller.setChecked(self.settings.delete_if_smaller)
        delete_layout.addWidget(self.delete_if_smaller)
        
        self.delete_if_threshold = QCheckBox("Supprimer l'original même si le seuil n'est pas atteint")
        self.delete_if_threshold.setChecked(self.settings.delete_if_threshold)
        delete_layout.addWidget(self.delete_if_threshold)
        
        self.replace_original = QCheckBox("Remplacer le fichier original par le converti")
        self.replace_original.setChecked(self.settings.replace_original)
        delete_layout.addWidget(self.replace_original)
        
        delete_group.setLayout(delete_layout)
        layout.addWidget(delete_group)
        
        settings_group.setLayout(layout)
        return settings_group
        
    def toggle_manual_mode(self, state):
        """Active/désactive les paramètres manuels."""
        self.manual_params.setVisible(state == Qt.CheckState.Checked.value)
        if state == Qt.CheckState.Checked.value:
            self.attempts_group.setEnabled(False)
            self.multiple_attempts.setChecked(False)
        else:
            self.attempts_group.setEnabled(self.multiple_attempts.isChecked())
        
    def toggle_attempts_params(self, state):
        """Active/désactive les paramètres des tentatives."""
        self.attempts_group.setEnabled(state == Qt.CheckState.Checked.value)
        
    def update_settings(self):
        """Met à jour les paramètres depuis l'interface."""
        self.settings.manual_mode = self.manual_mode.isChecked()
        self.settings.crf = self.crf_spin.value()
        self.settings.preset = self.preset_combo.currentText()
        
        self.settings.use_size_threshold = self.use_threshold.isChecked()
        self.settings.size_threshold = self.size_spin.value() * 1024 * 1024
        
        self.settings.ignore_converted = self.ignore_converted.isChecked()
        self.settings.multiple_attempts = self.multiple_attempts.isChecked()
        
        # Mettre à jour les paramètres des tentatives
        for i, (crf_spin, preset_combo) in enumerate(self.attempt_widgets):
            self.settings.attempts[i].crf = crf_spin.value()
            self.settings.attempts[i].preset = preset_combo.currentText()
        
        self.settings.delete_if_smaller = self.delete_if_smaller.isChecked()
        self.settings.delete_if_threshold = self.delete_if_threshold.isChecked()
        self.settings.replace_original = self.replace_original.isChecked()
    
    def add_files(self):
        """Ajoute des fichiers à convertir."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner les fichiers à convertir",
            "",
            "Vidéos (*.mp4 *.avi *.mkv *.mov);;Tous les fichiers (*.*)"
        )
        
        for file_path in files:
            path = Path(file_path)
            if path not in self.files_to_convert:
                # Vérifier si le fichier a déjà été converti
                metadata = MetadataManager.get_metadata(path)
                state = "En attente"
                already_converted = False
                
                if metadata is not None and metadata.compression_ratio > 0:
                    state = f"Déjà converti (-{metadata.compression_ratio:.1f}%)"
                    already_converted = True
                
                # Sélectionner par défaut seulement si :
                # - Le fichier n'est pas déjà converti, ou
                # - L'option "Ignorer les fichiers convertis" est désactivée
                selected = not (already_converted and self.settings.ignore_converted)
                
                self.files_to_convert[path] = {
                    'state': state,
                    'worker': None,
                    'progress': 0,
                    'selected': selected
                }
        
        self.refresh_files_list()
        
    def add_folder(self):
        """Ajoute un dossier à convertir."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner un dossier",
            ""
        )
        
        if folder:
            folder_path = Path(folder)
            count = 0
            
            for ext in ['*.mp4', '*.avi', '*.mkv', '*.mov']:
                for file_path in folder_path.glob(f"**/{ext}"):
                    if file_path not in self.files_to_convert:
                        # Vérifier si le fichier a déjà été converti
                        metadata = MetadataManager.get_metadata(file_path)
                        state = "En attente"
                        already_converted = False
                        
                        if metadata is not None and metadata.compression_ratio > 0:
                            state = f"Déjà converti (-{metadata.compression_ratio:.1f}%)"
                            already_converted = True
                        
                        # Sélectionner par défaut seulement si :
                        # - Le fichier n'est pas déjà converti, ou
                        # - L'option "Ignorer les fichiers convertis" est désactivée
                        selected = not (already_converted and self.settings.ignore_converted)
                        
                        self.files_to_convert[file_path] = {
                            'state': state,
                            'worker': None,
                            'progress': 0,
                            'selected': selected
                        }
                        count += 1
            
            if count > 0:
                self.refresh_files_list()
                logger.debug(f"{count} fichiers ajoutés depuis le dossier {folder}")
    
    def refresh_files_list(self):
        """Rafraîchit la liste des fichiers."""
        self.files_table.setRowCount(len(self.files_to_convert))
        for row, (path, info) in enumerate(self.files_to_convert.items()):
            # Checkbox de sélection
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox = QCheckBox()
            checkbox.setChecked(info.get('selected', True))
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.files_table.setCellWidget(row, 0, checkbox_widget)
            
            # Nom du fichier
            name_item = QTableWidgetItem(path.name)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if info['state'].startswith("Erreur"):
                name_item.setForeground(QColor("red"))
            self.files_table.setItem(row, 1, name_item)
            
            # État et progression
            if info.get('worker') and info.get('progress', 0) > 0:
                progress_widget = QWidget()
                progress_layout = QHBoxLayout(progress_widget)
                progress_bar = QProgressBar()
                progress_bar.setMinimum(0)
                progress_bar.setMaximum(100)
                progress_bar.setValue(info['progress'])
                progress_bar.setFormat(f"{info['progress']}%")
                progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
                progress_layout.addWidget(progress_bar)
                progress_layout.setContentsMargins(5, 2, 5, 2)
                self.files_table.setCellWidget(row, 2, progress_widget)
            else:
                state_item = QTableWidgetItem(info['state'])
                state_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if info['state'].startswith("Erreur"):
                    state_item.setForeground(QColor("red"))
                self.files_table.setItem(row, 2, state_item)
            
            # Tentative
            attempt = info.get('attempt', 0)
            attempt_item = QTableWidgetItem()
            attempt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if attempt > 0:
                attempt_text = f"{attempt}/3" if not self.manual_mode.isChecked() else str(attempt)
                attempt_item.setText(attempt_text)
            self.files_table.setItem(row, 3, attempt_item)
            
            # Taille
            if info['state'] == "Terminé":
                output_path = path.with_name(f"{path.stem}_conv{path.suffix}")
                if output_path.exists():
                    size = output_path.stat().st_size
                else:
                    size = path.stat().st_size
            else:
                size = path.stat().st_size
            size_item = QTableWidgetItem(format_size(size))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.files_table.setItem(row, 4, size_item)
            
            # Actions
            if not info.get('worker'):
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                delete_button = QPushButton("🗑️")
                delete_button.clicked.connect(lambda checked, p=path: self.remove_file(p))
                action_layout.addWidget(delete_button)
                action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                action_layout.setContentsMargins(0, 0, 0, 0)
                self.files_table.setCellWidget(row, 5, action_widget)
            else:
                empty_item = QTableWidgetItem("")
                empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.files_table.setItem(row, 5, empty_item)
    
    def remove_file(self, file_path: Path):
        """Supprime un fichier de la liste."""
        if file_path in self.files_to_convert:
            info = self.files_to_convert[file_path]
            if info.get('worker'):
                info['worker'].stop()
            del self.files_to_convert[file_path]
            self.refresh_files_list()
            logger.debug(f"Fichier {file_path.name} supprimé de la liste")

    def toggle_select_all(self):
        """Inverse la sélection de tous les fichiers."""
        all_selected = True
        for row in range(self.files_table.rowCount()):
            checkbox = self.files_table.cellWidget(row, 0)
            if checkbox and not checkbox.layout().itemAt(0).widget().isChecked():
                all_selected = False
                break
        
        # Inverser l'état actuel
        new_state = not all_selected
        self.select_all_btn.setText("Tout désélectionner" if new_state else "Tout sélectionner")
        
        for row in range(self.files_table.rowCount()):
            checkbox = self.files_table.cellWidget(row, 0)
            if checkbox:
                checkbox.layout().itemAt(0).widget().setChecked(new_state)
                path = list(self.files_to_convert.keys())[row]
                self.files_to_convert[path]['selected'] = new_state
    
    def start_conversion(self):
        """Démarre la conversion des fichiers."""
        # Filtrer les fichiers sélectionnés
        files_to_convert = {}
        for row in range(self.files_table.rowCount()):
            checkbox = self.files_table.cellWidget(row, 0)
            if checkbox and checkbox.layout().itemAt(0).widget().isChecked():
                path = list(self.files_to_convert.keys())[row]
                files_to_convert[path] = self.files_to_convert[path]
        
        if not files_to_convert:
            QMessageBox.warning(self, "Attention", "Aucun fichier sélectionné")
            return
        
        # Sauvegarder les paramètres actuels
        self.update_settings()
        SettingsManager.save_settings(self.settings)
        
        # Mettre à jour les boutons
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Calculer le nombre maximal de threads
        max_threads = min(os.cpu_count() or 1, 4)  
        active_threads = 0
        
        # Créer un worker pour chaque fichier sélectionné
        for path, info in files_to_convert.items():
            if not info.get('worker'):
                # Attendre si on a atteint le nombre maximal de threads
                while active_threads >= max_threads:
                    QApplication.processEvents()  
                    active_threads = sum(1 for i in self.files_to_convert.values() 
                                      if i.get('worker') and i['worker'].isRunning())
                
                worker = ConversionWorker(path, self.settings)
                worker.progress.connect(self.update_progress)
                worker.finished.connect(lambda p=path: self.conversion_finished(p))
                worker.error.connect(self.conversion_error)
                worker.attempt_changed.connect(lambda p, a: self.update_attempt(p, a))
                
                info['worker'] = worker
                info['state'] = ""
                info['progress'] = 0
                info['attempt'] = 1
                worker.start()
                active_threads += 1
        
        self.refresh_files_list()
    
    def update_attempt(self, file_path: str, attempt: int):
        """Met à jour le numéro de tentative."""
        path = Path(file_path)
        if path in self.files_to_convert:
            info = self.files_to_convert[path]
            info['attempt'] = attempt
            info['progress'] = 0  # Réinitialiser la progression
            
            # Trouver la ligne dans la table
            for row in range(self.files_table.rowCount()):
                item = self.files_table.item(row, 1)  # Colonne du nom
                if item and item.text() == path.name:
                    # Mettre à jour la tentative
                    attempt_text = f"{attempt}/3" if not self.manual_mode.isChecked() else str(attempt)
                    attempt_item = QTableWidgetItem(attempt_text)
                    attempt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.files_table.setItem(row, 3, attempt_item)
                    
                    # Réinitialiser la barre de progression
                    progress_widget = self.files_table.cellWidget(row, 2)
                    if progress_widget and isinstance(progress_widget.layout().itemAt(0).widget(), QProgressBar):
                        progress_bar = progress_widget.layout().itemAt(0).widget()
                        progress_bar.setValue(0)
                        progress_bar.setFormat("0%")
                    break
    
    def update_progress(self, file_path: str, progress: int):
        """Met à jour la progression d'un fichier."""
        path = Path(file_path)
        if path in self.files_to_convert:
            info = self.files_to_convert[path]
            info['progress'] = progress
            
            # Trouver la ligne dans la table
            for row in range(self.files_table.rowCount()):
                item = self.files_table.item(row, 1)  # Colonne du nom
                if item and item.text() == path.name:
                    # Créer ou mettre à jour la barre de progression
                    progress_widget = self.files_table.cellWidget(row, 2)
                    if not progress_widget or not isinstance(progress_widget.layout().itemAt(0).widget(), QProgressBar):
                        progress_widget = QWidget()
                        progress_layout = QHBoxLayout(progress_widget)
                        progress_bar = QProgressBar()
                        progress_bar.setMinimum(0)
                        progress_bar.setMaximum(100)
                        progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        progress_layout.addWidget(progress_bar)
                        progress_layout.setContentsMargins(5, 2, 5, 2)
                        self.files_table.setCellWidget(row, 2, progress_widget)
                    
                    # Mettre à jour la valeur et le format
                    progress_bar = progress_widget.layout().itemAt(0).widget()
                    progress_bar.setValue(progress)
                    progress_bar.setFormat(f"{progress}%")
                    break
    
    def stop_conversion(self):
        """Arrête toutes les conversions en cours."""
        for info in self.files_to_convert.values():
            if info.get('worker'):
                info['worker'].stop()
                info['worker'] = None
                info['state'] = "Arrêté"
                info['progress'] = 0
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.refresh_files_list()

    def conversion_finished(self, file_path: str):
        """Appelé quand une conversion est terminée."""
        path = Path(file_path)
        if path in self.files_to_convert:
            info = self.files_to_convert[path]
            info['state'] = "Terminé"
            info['progress'] = 100
            info['worker'] = None
            self.refresh_files_list()
            
            # Vérifier si toutes les conversions sont terminées
            if not any(info.get('worker') for info in self.files_to_convert.values()):
                QMessageBox.information(self, "Terminé", "Toutes les conversions sont terminées !")

    def conversion_error(self, file_path: str, error: str):
        """Appelé quand une erreur survient pendant la conversion."""
        path = Path(file_path)
        if path in self.files_to_convert:
            info = self.files_to_convert[path]
            info['state'] = f"Erreur: {error}"
            info['worker'] = None
            logger.error(f"Erreur de conversion pour {path}: {error}")
            self.refresh_files_list()
            
            # Afficher une boîte de dialogue avec l'erreur
            QMessageBox.critical(
                self,
                "Erreur de conversion",
                f"Erreur lors de la conversion de {path.name}:\n\n{error}"
            )
