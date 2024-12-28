from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QFileDialog, QProgressBar, QTableWidget, QTableWidgetItem,
                             QLabel, QHeaderView, QMessageBox, QComboBox, QWidget,
                             QSlider)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QImage, QPixmap, QColor
from .video_hasher import VideoHasher
from .data_manager import DataManager
import os
import cv2
from typing import Dict, List, Set, Tuple
from send2trash import send2trash
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.Window')

class DuplicateSelectionDialog(QDialog):
    def __init__(self, duplicate_group: Set[str], parent=None):
        super().__init__(parent)
        self.duplicate_group = duplicate_group
        self.selected_file = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Sélectionner le fichier à conserver")
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout()
        
        # Label explicatif
        label = QLabel("Plusieurs fichiers similaires ont été trouvés. Veuillez sélectionner celui que vous souhaitez conserver :")
        label.setWordWrap(True)
        layout.addWidget(label)
        
        # ComboBox pour la sélection
        self.combo = QComboBox()
        for file_path in sorted(self.duplicate_group):
            self.combo.addItem(file_path)
        layout.addWidget(self.combo)
        
        # Boutons
        buttons = QHBoxLayout()
        
        keep_button = QPushButton("Conserver")
        keep_button.clicked.connect(self.accept)
        buttons.addWidget(keep_button)
        
        cancel_button = QPushButton("Annuler")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button)
        
        layout.addLayout(buttons)
        self.setLayout(layout)
    
    def get_selected_file(self):
        return self.combo.currentText()

class DuplicateComparisonDialog(QDialog):
    def __init__(self, file1: str, file2: str, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.file1 = file1
        self.file2 = file2
        self.data_manager = data_manager
        self.cap1 = cv2.VideoCapture(file1)
        self.cap2 = cv2.VideoCapture(file2)
        self.current_frame = 0
        self.max_frame = min(int(self.cap1.get(cv2.CAP_PROP_FRAME_COUNT)),
                           int(self.cap2.get(cv2.CAP_PROP_FRAME_COUNT)))
        self.result = None
        self.init_ui()
        self.update_frame()

    def init_ui(self):
        self.setWindowTitle("Comparaison de Vidéos")
        self.setMinimumWidth(1200)
        self.setMinimumHeight(600)
        
        layout = QVBoxLayout()
        
        # Informations des fichiers
        info_layout = QHBoxLayout()
        
        # Info fichier 1
        info1 = QVBoxLayout()
        info1.addWidget(QLabel(f"Fichier 1: {os.path.basename(self.file1)}"))
        info1.addWidget(QLabel(f"Taille: {os.path.getsize(self.file1) / (1024*1024):.2f} MB"))
        info1.addWidget(QLabel(f"Chemin: {self.file1}"))
        info_layout.addLayout(info1)
        
        # Info fichier 2
        info2 = QVBoxLayout()
        info2.addWidget(QLabel(f"Fichier 2: {os.path.basename(self.file2)}"))
        info2.addWidget(QLabel(f"Taille: {os.path.getsize(self.file2) / (1024*1024):.2f} MB"))
        info2.addWidget(QLabel(f"Chemin: {self.file2}"))
        info_layout.addLayout(info2)
        
        layout.addLayout(info_layout)
        
        # Images
        images_layout = QHBoxLayout()
        self.image_label1 = QLabel()
        self.image_label2 = QLabel()
        images_layout.addWidget(self.image_label1)
        images_layout.addWidget(self.image_label2)
        layout.addLayout(images_layout)
        
        # Contrôles de navigation
        nav_layout = QHBoxLayout()
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(self.max_frame - 1)
        self.frame_slider.valueChanged.connect(self.slider_changed)
        nav_layout.addWidget(self.frame_slider)
        layout.addLayout(nav_layout)
        
        # Boutons d'action
        buttons_layout = QHBoxLayout()
        
        keep1_btn = QPushButton("📁 Garder Fichier 1")
        keep1_btn.clicked.connect(lambda: self.make_choice('keep1'))
        buttons_layout.addWidget(keep1_btn)
        
        keep2_btn = QPushButton("📁 Garder Fichier 2")
        keep2_btn.clicked.connect(lambda: self.make_choice('keep2'))
        buttons_layout.addWidget(keep2_btn)
        
        keep_both_btn = QPushButton("📁 Garder les Deux")
        keep_both_btn.clicked.connect(lambda: self.make_choice('keep_both'))
        buttons_layout.addWidget(keep_both_btn)
        
        ignore_temp_btn = QPushButton("⏳ Ignorer Temporairement")
        ignore_temp_btn.clicked.connect(lambda: self.make_choice('ignore_temp'))
        buttons_layout.addWidget(ignore_temp_btn)
        
        ignore_perm_btn = QPushButton("🚫 Ignorer Définitivement")
        ignore_perm_btn.clicked.connect(lambda: self.make_choice('ignore_perm'))
        buttons_layout.addWidget(ignore_perm_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def slider_changed(self, value):
        self.current_frame = value
        self.update_frame()

    def update_frame(self):
        # Positionner les captures sur la frame actuelle
        self.cap1.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        self.cap2.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        
        # Lire les frames
        ret1, frame1 = self.cap1.read()
        ret2, frame2 = self.cap2.read()
        
        if ret1 and ret2:
            # Redimensionner les frames pour l'affichage
            height = 400
            for frame, label in [(frame1, self.image_label1), (frame2, self.image_label2)]:
                width = int(frame.shape[1] * (height / frame.shape[0]))
                frame = cv2.resize(frame, (width, height))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = QImage(frame.data, frame.shape[1], frame.shape[0], 
                             frame.shape[1] * 3, QImage.Format.Format_RGB888)
                label.setPixmap(QPixmap.fromImage(image))

    def make_choice(self, choice):
        self.result = choice
        if choice == 'keep1':
            try:
                send2trash(self.file2)
            except Exception as e:
                logger.error(f"Erreur lors de la suppression de {self.file2}: {e}")
        elif choice == 'keep2':
            try:
                send2trash(self.file1)
            except Exception as e:
                logger.error(f"Erreur lors de la suppression de {self.file1}: {e}")
        elif choice == 'ignore_perm':
            self.data_manager.add_ignored_pair(self.file1, self.file2, permanent=True)
        elif choice == 'ignore_temp':
            self.data_manager.add_ignored_pair(self.file1, self.file2, permanent=False)
        
        self.close()

    def closeEvent(self, event):
        self.cap1.release()
        self.cap2.release()
        super().closeEvent(event)

class DuplicateFinderThread(QThread):
    progress = pyqtSignal(int)
    file_analyzed = pyqtSignal(str)
    finished = pyqtSignal(dict)
    
    def __init__(self, files_to_analyze, data_manager, hasher):
        super().__init__()
        self.files_to_analyze = files_to_analyze
        self.data_manager = data_manager
        self.hasher = hasher
        self.total_files = len(files_to_analyze)
        self.current_progress = 0
    
    def run(self):
        """Analyse les fichiers en arrière-plan"""
        results = {}
        analyzed_files = self.data_manager.get_analyzed_files()
        
        # Calculer d'abord tous les hashs
        current_hashes = {}
        for i, file_path in enumerate(self.files_to_analyze, 1):
            try:
                # Calculer l'empreinte du fichier
                file_hash = self.hasher.compute_video_hash(file_path)
                if file_hash is not None:
                    current_hashes[file_path] = file_hash
                    # Stocker l'empreinte
                    self.data_manager.add_analyzed_file(file_path, file_hash)
                    # Sauvegarder après chaque fichier
                    self.data_manager.save_data()
                
                # Mettre à jour la progression
                progress = int((i / self.total_files) * 50)  # Première moitié
                self.progress.emit(progress)
                self.file_analyzed.emit(file_path)
            
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse de {file_path}: {e}")
        
        # Ensuite, comparer tous les hashs entre eux
        all_files = {**current_hashes, **analyzed_files}  # Fusionner les hashs actuels et existants
        total_comparisons = len(all_files) * (len(all_files) - 1) // 2
        comparison_count = 0
        
        for file1, hash1 in all_files.items():
            for file2, hash2 in all_files.items():
                if file1 < file2:  # Évite les comparaisons en double
                    comparison_count += 1
                    if not self.data_manager.is_pair_ignored(file1, file2):
                        if self.hasher.are_similar(hash1, hash2):
                            if file1 not in results:
                                results[file1] = []
                            results[file1].append(file2)
            
            # Mettre à jour la progression pour la deuxième moitié
            progress = 50 + int((comparison_count / total_comparisons) * 50)
            self.progress.emit(progress)
        
        self.finished.emit(results)

class DuplicateFinderWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Recherche de doublons")
        self.setMinimumWidth(1200)
        self.setMinimumHeight(600)
        self.data_manager = DataManager()
        
        # Initialiser avec le niveau de précision élevé (3)
        self.hasher = VideoHasher(precision_level=3)
        
        self.init_ui()
        self.load_analyzed_files()

    def init_ui(self):
        """Initialise l'interface utilisateur"""
        layout = QVBoxLayout()
        
        # Groupe de boutons
        button_group = QHBoxLayout()
        
        # Bouton pour ajouter des fichiers
        self.add_files_button = QPushButton("📁 Ajouter Fichiers")
        self.add_files_button.clicked.connect(self.select_files)
        button_group.addWidget(self.add_files_button)
        
        # Bouton pour ajouter un dossier
        self.add_folder_button = QPushButton("📂 Ajouter Dossier")
        self.add_folder_button.clicked.connect(self.select_folder)
        button_group.addWidget(self.add_folder_button)
        
        # Bouton pour lancer l'analyse
        self.analyze_button = QPushButton("🔍 Scanner")
        self.analyze_button.clicked.connect(self.start_analysis)
        button_group.addWidget(self.analyze_button)
        
        # Bouton pour effacer les empreintes
        self.clear_button = QPushButton("🧹 Effacer les empreintes")
        self.clear_button.clicked.connect(self.clear_data)
        button_group.addWidget(self.clear_button)
        
        # Bouton pour supprimer la sélection
        self.remove_button = QPushButton("🗑️ Supprimer la sélection")
        self.remove_button.clicked.connect(self.remove_selected)
        button_group.addWidget(self.remove_button)
        
        # Bouton pour fermer la fenêtre
        self.close_button = QPushButton("❌ Fermer")
        self.close_button.clicked.connect(self.close)
        button_group.addWidget(self.close_button)
        
        # Niveau de précision
        precision_layout = QHBoxLayout()
        precision_label = QLabel("Précision:")
        self.precision_slider = QSlider(Qt.Orientation.Horizontal)
        self.precision_slider.setMinimum(1)
        self.precision_slider.setMaximum(3)
        self.precision_slider.setValue(3)
        self.precision_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.precision_slider.setTickInterval(1)
        self.precision_slider.valueChanged.connect(self.update_precision)
        precision_layout.addWidget(precision_label)
        precision_layout.addWidget(self.precision_slider)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # Table des fichiers
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(2)
        self.files_table.setHorizontalHeaderLabels(["Fichier", "État"])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.files_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.files_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        # Ajouter les widgets au layout principal
        layout.addLayout(button_group)
        layout.addLayout(precision_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.files_table)
        
        self.setLayout(layout)

    def update_progress(self, value):
        """Met à jour la barre de progression"""
        self.progress_bar.setValue(value)

    def start_analysis(self):
        """Lance l'analyse et affiche la fenêtre de gestion des doublons"""
        files_to_analyze = []
        
        for i in range(self.files_table.rowCount()):
            status_item = self.files_table.item(i, 1)
            file_item = self.files_table.item(i, 0)
            
            if status_item and file_item and status_item.text() == "En attente":
                files_to_analyze.append(file_item.text())
        
        if not files_to_analyze:
            QMessageBox.information(self, "Information", 
                                  "Aucun nouveau fichier à analyser.")
            return

        self.progress_bar.setVisible(True)
        self.add_files_button.setEnabled(False)
        self.add_folder_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        
        self.thread = DuplicateFinderThread(files_to_analyze, self.data_manager, self.hasher)
        self.thread.progress.connect(self.update_progress)
        self.thread.file_analyzed.connect(self.update_file_status)
        self.thread.finished.connect(self.analysis_finished)
        self.thread.start()

    def update_file_status(self, file_path: str):
        """Met à jour le statut d'un fichier dans la table"""
        for i in range(self.files_table.rowCount()):
            if self.files_table.item(i, 0).text() == file_path:
                status_item = QTableWidgetItem("Analysé")
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.files_table.setItem(i, 1, status_item)
                break

    def analysis_finished(self, results: Dict[str, List[str]]):
        """Appelé quand l'analyse est terminée"""
        # Réactiver les boutons
        self.progress_bar.setVisible(False)
        self.add_files_button.setEnabled(True)
        self.add_folder_button.setEnabled(True)
        self.analyze_button.setEnabled(True)

        # Afficher la fenêtre de gestion des doublons
        if results:
            self.show_duplicates_manager(results)
        else:
            QMessageBox.information(self, "Analyse terminée", 
                                  "Aucun doublon n'a été trouvé.")

    def show_duplicates_manager(self, duplicates):
        """Affiche la fenêtre de gestion des doublons"""
        # Créer une liste de paires uniques de doublons
        shown_pairs = set()
        for file1, duplicate_files in duplicates.items():
            for file2 in duplicate_files:
                # Créer une paire triée pour éviter les doublons
                pair = tuple(sorted([file1, file2]))
                if pair not in shown_pairs and not self.data_manager.is_pair_ignored(pair[0], pair[1]):
                    shown_pairs.add(pair)
                    dialog = DuplicateComparisonDialog(pair[0], pair[1], 
                                                     self.data_manager, self)
                    dialog.exec()
        
        # Sauvegarder les changements
        self.data_manager.save_data()

    def update_precision(self, level_text: str):
        """Change le niveau de précision de l'analyse"""
        level_map = {
            "Faible": 1,
            "Moyen": 2,
            "Élevé": 3
        }
        level = level_map.get(level_text, 3)  # Par défaut niveau élevé
        self.hasher = VideoHasher(precision_level=level)

    def delete_duplicate(self, file_path: str):
        """Déplace un fichier dupliqué vers la corbeille"""
        try:
            send2trash(file_path)  # Utiliser send2trash au lieu de os.remove
            # Supprimer le fichier de la base de données
            self.data_manager.analyzed_files.pop(file_path, None)
            self.data_manager.save_data()
            # Mettre à jour l'affichage
            self.show_analyzed_files()
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de {file_path}: {e}")
            QMessageBox.warning(self, "Erreur", 
                              f"Impossible de déplacer le fichier vers la corbeille : {str(e)}")

    def clear_data(self):
        """Efface toutes les empreintes"""
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Êtes-vous sûr de vouloir effacer toutes les empreintes ?\nCette action effacera aussi la liste des doublons ignorés.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.data_manager.clear_data()
            
            # Mettre à jour le statut des fichiers à "En attente"
            for i in range(self.files_table.rowCount()):
                status_item = self.files_table.item(i, 1)
                if status_item and status_item.text() == "Analysé":
                    status_item = QTableWidgetItem("En attente")
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.files_table.setItem(i, 1, status_item)
            
            logger.info("Toutes les empreintes ont été effacées")
            QMessageBox.information(self, "Succès", "Toutes les empreintes ont été effacées.")

    def load_analyzed_files(self):
        """Charge les fichiers analysés sans afficher les doublons"""
        self.show_analyzed_files()

    def select_folder(self):
        """Ouvre une boîte de dialogue pour sélectionner un dossier"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner un dossier"
        )
        
        if folder:
            self.files_table.setSortingEnabled(False)  # Désactiver le tri pendant la mise à jour
            
            # Récupérer les fichiers vidéo du dossier
            video_files = []
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.wmv')):
                        video_files.append(os.path.join(root, file))
            
            if not video_files:
                QMessageBox.information(self, "Information", 
                                      "Aucun fichier vidéo trouvé dans ce dossier.")
                return
            
            # Filtrer les fichiers déjà analysés
            new_files = [f for f in video_files if f not in self.data_manager.get_analyzed_files()]
            
            if not new_files:
                QMessageBox.information(self, "Information", 
                                      "Tous les fichiers de ce dossier ont déjà été analysés.")
                return
            
            # Ajouter les fichiers à la table
            current_row = self.files_table.rowCount()
            self.files_table.setRowCount(current_row + len(new_files))
            
            for i, file_path in enumerate(sorted(new_files, key=str.lower)):
                # Fichier
                file_item = QTableWidgetItem(file_path)
                self.files_table.setItem(current_row + i, 0, file_item)
                
                # État
                status_item = QTableWidgetItem("En attente")
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.files_table.setItem(current_row + i, 1, status_item)
            
            self.files_table.setSortingEnabled(True)  # Réactiver le tri

    def select_files(self):
        """Ouvre une boîte de dialogue pour sélectionner des fichiers"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner des fichiers vidéo",
            "",
            "Fichiers vidéo (*.mp4 *.avi *.mkv *.mov *.wmv);;Tous les fichiers (*.*)"
        )
        
        if files:
            self.files_table.setSortingEnabled(False)  # Désactiver le tri pendant la mise à jour
            
            # Filtrer les fichiers déjà analysés
            new_files = [f for f in files if f not in self.data_manager.get_analyzed_files()]
            
            if not new_files:
                QMessageBox.information(self, "Information", 
                                      "Tous les fichiers sélectionnés ont déjà été analysés.")
                return
            
            current_row = self.files_table.rowCount()
            self.files_table.setRowCount(current_row + len(new_files))
            
            for i, file_path in enumerate(sorted(new_files, key=str.lower)):
                # Fichier
                file_item = QTableWidgetItem(file_path)
                self.files_table.setItem(current_row + i, 0, file_item)
                
                # État
                status_item = QTableWidgetItem("En attente")
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.files_table.setItem(current_row + i, 1, status_item)
            
            self.files_table.setSortingEnabled(True)  # Réactiver le tri

    def remove_selected(self):
        """Supprime les fichiers sélectionnés de la liste"""
        selected_rows = sorted([item.row() for item in self.files_table.selectedItems()], reverse=True)
        if not selected_rows:
            return
        
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Êtes-vous sûr de vouloir supprimer {len(set(selected_rows))} fichier(s) de la liste ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Supprimer les lignes sélectionnées
            for row in selected_rows:
                self.files_table.removeRow(row)
            
            logger.info(f"{len(set(selected_rows))} fichier(s) supprimé(s) de la liste")

    def show_analyzed_files(self):
        """Affiche uniquement la liste des fichiers analysés"""
        self.files_table.setSortingEnabled(False)  # Désactiver le tri pendant la mise à jour
        
        # Sauvegarder les fichiers actuellement en attente
        pending_files = []
        for i in range(self.files_table.rowCount()):
            file_item = self.files_table.item(i, 0)
            status_item = self.files_table.item(i, 1)
            if file_item and status_item and status_item.text() == "En attente":
                pending_files.append(file_item.text())
        
        self.files_table.setRowCount(0)
        
        # Ajouter d'abord les fichiers analysés
        analyzed_files = self.data_manager.get_analyzed_files()
        sorted_files = sorted(analyzed_files.items(), key=lambda x: x[0].lower())
        
        current_row = 0
        for file_path, _ in sorted_files:
            # Vérifier si le fichier existe toujours
            file_exists = os.path.exists(file_path)
            
            # Fichier
            file_item = QTableWidgetItem(file_path)
            if not file_exists:
                file_item.setForeground(QColor(255, 0, 0))
                self.data_manager.analyzed_files.pop(file_path, None)
            self.files_table.insertRow(current_row)
            self.files_table.setItem(current_row, 0, file_item)
            
            # État
            status = "Introuvable" if not file_exists else "Analysé"
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if not file_exists:
                status_item.setForeground(QColor(255, 0, 0))
            self.files_table.setItem(current_row, 1, status_item)
            current_row += 1
        
        # Ajouter ensuite les fichiers en attente
        for file_path in sorted(pending_files, key=str.lower):
            self.files_table.insertRow(current_row)
            
            # Fichier
            file_item = QTableWidgetItem(file_path)
            self.files_table.setItem(current_row, 0, file_item)
            
            # État
            status_item = QTableWidgetItem("En attente")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.files_table.setItem(current_row, 1, status_item)
            current_row += 1
        
        # Sauvegarder les changements si des fichiers ont été supprimés
        self.data_manager.save_data()
        self.files_table.setSortingEnabled(True)  # Réactiver le tri
