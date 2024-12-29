import os
import json
import cv2
import numpy as np
from enum import Enum
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTableWidget,
    QTableWidgetItem, QProgressBar, QComboBox,QHeaderView,
    QDoubleSpinBox, QDialog, QGroupBox,QCheckBox,QMessageBox,
    QSlider,QSpinBox, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QPixmap, QImage
import time
from .video_hasher import VideoHasher, HashMethod
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.Window')


class DuplicateComparisonDialog(QDialog):
    """Dialogue de comparaison de deux vidéos"""
    
    def __init__(self, file1: str, file2: str, similarity: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Comparaison de doublons")
        self.setMinimumSize(1200, 800)
        
        self.file1 = file1
        self.file2 = file2
        self.similarity = similarity
        self.parent = parent  # Garde une référence à la fenêtre principale
        
        # Ouvre les vidéos
        self.cap1 = cv2.VideoCapture(file1)
        self.cap2 = cv2.VideoCapture(file2)
        
        # Configure l'interface
        self.setup_ui()
        self.update_file_info()
        
        # Initialise la position
        self.total_frames1 = int(self.cap1.get(cv2.CAP_PROP_FRAME_COUNT))
        self.total_frames2 = int(self.cap2.get(cv2.CAP_PROP_FRAME_COUNT))
        self.position_slider.setMaximum(100)  # On utilise des pourcentages
        self.update_position(0)  # Affiche la première frame

    def update_file_info(self):
        """Met à jour les informations des fichiers"""
        # Calcule les tailles
        size1 = os.path.getsize(self.file1) / (1024*1024)
        size2 = os.path.getsize(self.file2) / (1024*1024)
        
        # Style de base pour les labels
        base_style = "QLabel { font-size: 14px; }"
        green_style = "QLabel { font-size: 14px; color: #4CAF50; }"
        
        # Info fichier gauche
        dirname1 = os.path.dirname(self.file1)
        basename1 = os.path.basename(self.file1)
        size1_text = f"📏 {size1:.1f} Mo"
            
        self.left_info.setText(
            f"📁 {dirname1}\n"
            f"   {basename1}\n"
            f"{size1_text}"
        )
        self.left_info.setStyleSheet(green_style)
        
        # Info fichier droite
        dirname2 = os.path.dirname(self.file2)
        basename2 = os.path.basename(self.file2)
        size2_text = f"📏 {size2:.1f} Mo"
            
        self.right_info.setText(
            f"📁 {dirname2}\n"
            f"   {basename2}\n"
            f"{size2_text}"
        )
        self.right_info.setStyleSheet(base_style)

    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Zone principale avec les vidéos et leurs informations
        main_zone = QHBoxLayout()
        
        # Zone de gauche
        left_zone = QVBoxLayout()
        self.left_info = QLabel()
        self.left_info.setWordWrap(True)
        left_zone.addWidget(self.left_info)
        
        # Conteneur pour la vidéo gauche avec un layout pour centrer
        left_video_container = QWidget()
        left_video_container.setFixedSize(800, 450)
        left_video_container.setStyleSheet("border: 1px solid #ccc; border-radius: 4px; background: transparent;")
        left_video_layout = QHBoxLayout(left_video_container)
        left_video_layout.setContentsMargins(0, 0, 0, 0)
        
        # Label vidéo gauche
        self.left_video = QLabel()
        self.left_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_video_layout.addWidget(self.left_video, 0, Qt.AlignmentFlag.AlignCenter)
        
        left_zone.addWidget(left_video_container)
        left_zone.addStretch()
        main_zone.addLayout(left_zone)
        
        # Zone de droite
        right_zone = QVBoxLayout()
        self.right_info = QLabel()
        self.right_info.setWordWrap(True)
        right_zone.addWidget(self.right_info)
        
        # Conteneur pour la vidéo droite avec un layout pour centrer
        right_video_container = QWidget()
        right_video_container.setFixedSize(800, 450)
        right_video_container.setStyleSheet("border: 1px solid #ccc; border-radius: 4px; background: transparent;")
        right_video_layout = QHBoxLayout(right_video_container)
        right_video_layout.setContentsMargins(0, 0, 0, 0)
        
        # Label vidéo droite
        self.right_video = QLabel()
        self.right_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_video_layout.addWidget(self.right_video, 0, Qt.AlignmentFlag.AlignCenter)
        
        right_zone.addWidget(right_video_container)
        right_zone.addStretch()
        main_zone.addLayout(right_zone)
        
        layout.addLayout(main_zone)
        
        # Similarité en bas
        similarity_layout = QHBoxLayout()
        similarity_layout.addStretch()
        self.similarity_label = QLabel(f"🎯 Similarité: {self.similarity:.1f}%")
        self.similarity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.similarity_label.font()
        font.setPointSize(14)
        self.similarity_label.setFont(font)
        similarity_layout.addWidget(self.similarity_label)
        similarity_layout.addStretch()
        layout.addLayout(similarity_layout)
        
        # Slider de position
        slider_layout = QHBoxLayout()
        self.position_label = QLabel("Position: 0%")
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 100)
        slider_layout.addWidget(self.position_label)
        slider_layout.addWidget(self.position_slider)
        layout.addLayout(slider_layout)
        
        # Boutons d'action en bas
        button_layout = QHBoxLayout()
        
        self.keep_left_btn = QPushButton("⭐ Garder gauche")
        self.keep_right_btn = QPushButton("⭐ Garder droite")
        self.ignore_temp_btn = QPushButton("🤔 Ignorer")
        self.ignore_perm_btn = QPushButton("❌ Ignorer définitivement")
        self.close_btn = QPushButton("🚪 Fermer")
        
        for btn in [self.keep_left_btn, self.ignore_temp_btn, self.ignore_perm_btn, self.close_btn, self.keep_right_btn]:
            button_layout.addWidget(btn)
            
        layout.addLayout(button_layout)
        
        # Connexion des signaux
        self.keep_left_btn.clicked.connect(lambda: self.make_choice("keep_left"))
        self.keep_right_btn.clicked.connect(lambda: self.make_choice("keep_right"))
        self.ignore_temp_btn.clicked.connect(lambda: self.make_choice("ignore_temp"))
        self.ignore_perm_btn.clicked.connect(lambda: self.make_choice("ignore_perm"))
        self.close_btn.clicked.connect(self.close)
        self.position_slider.valueChanged.connect(self.update_position)

    def update_position(self, percent):
        """Met à jour la position des vidéos

        Args:
            percent (int): Position en pourcentage (0-100)
        """
        # Met à jour le label
        self.position_label.setText(f"⏱️ Position: {percent}%")
        
        # Calcule la frame correspondante
        max_frames = min(self.total_frames1, self.total_frames2)
        frame = int((percent / 100.0) * max_frames)
        
        # Met à jour les images
        # Image gauche
        self.cap1.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ret1, frame1 = self.cap1.read()
        if ret1:
            frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
            h, w, ch = frame1.shape
            bytes_per_line = ch * w
            image1 = QImage(frame1.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap1 = QPixmap.fromImage(image1)
            
            # Calcule la taille cible en préservant le ratio
            target_size = QSize(800, 450)
            scaled_pixmap1 = pixmap1.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.left_video.setPixmap(scaled_pixmap1)

        # Image droite
        self.cap2.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ret2, frame2 = self.cap2.read()
        if ret2:
            frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
            h, w, ch = frame2.shape
            bytes_per_line = ch * w
            image2 = QImage(frame2.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap2 = QPixmap.fromImage(image2)
            
            # Calcule la taille cible en préservant le ratio
            target_size = QSize(800, 450)
            scaled_pixmap2 = pixmap2.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.right_video.setPixmap(scaled_pixmap2)

    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre"""
        # Libère les ressources vidéo
        self.cap1.release()
        self.cap2.release()

        # Arrête les comparaisons en cours si c'est une fenêtre principale
        if isinstance(self.parent, DuplicateFinderWindow) and self.parent.worker and self.parent.worker.isRunning():
            self.parent.stop_analysis(show_confirmation=False)
            logger.info("Analyse arrêtée suite à la fermeture de la fenêtre de comparaison")

        # Ferme la fenêtre sans accepter le dialogue
        event.accept()
        self.reject()  # Rejette le dialogue pour arrêter les comparaisons

    def make_choice(self, choice):
        """Gère le choix de l'utilisateur

        Args:
            choice (str): Le choix fait par l'utilisateur
        """
        # Arrête les comparaisons en cours si c'est une fenêtre principale
        if isinstance(self.parent, DuplicateFinderWindow) and self.parent.worker and self.parent.worker.isRunning():
            self.parent.stop_analysis(show_confirmation=False)
            logger.info("Analyse arrêtée suite au choix de l'utilisateur")

        self.result = choice
        self.close()


class DuplicateFinderWindow(QMainWindow):
    """Fenêtre principale du plugin de recherche de doublons"""
    
    closed = pyqtSignal()
    
    def __init__(self):
        """Initialise la fenêtre"""
        super().__init__()
        self.files = []
        self.potential_duplicates = []
        self.ignored_pairs = set()
        self.worker = None
        self.start_time = None
        self.compare_start_time = None
        self.video_hasher = VideoHasher()
        self.hash_method = HashMethod.PHASH
        
        # Configure l'interface
        self.setup_ui()
        
        # Charge les hashs existants
        self.load_existing_hashes()

    def load_ignored_pairs(self):
        """Charge les paires ignorées depuis le fichier"""
        try:
            with open("ignored_pairs.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_ignored_pairs(self):
        """Sauvegarde les paires ignorées"""
        with open("ignored_pairs.json", "w") as f:
            json.dump(self.ignored_pairs, f, indent=4)

    def setup_ui(self):
        """Configure l'interface utilisateur"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Contrôles en haut
        controls_layout = QHBoxLayout()
        
        # Méthode de hachage (uniquement pHash)
        controls_layout.addWidget(QLabel("Méthode de hachage:"))
        self.hash_method_combo = QComboBox()
        self.hash_method_combo.addItem("pHash")
        self.hash_method_combo.setEnabled(False)  # Désactivé car une seule méthode
        controls_layout.addWidget(self.hash_method_combo)
        
        # Seuil de similarité
        controls_layout.addWidget(QLabel("Seuil de similarité (%):"))
        
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(1, 100)
        self.threshold_spin.setValue(90)
        controls_layout.addWidget(self.threshold_spin)
        
        # Durée maximale
        controls_layout.addWidget(QLabel("Durée maximale (min):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 60)  # De 0 à 60 minutes
        self.duration_spin.setValue(0)
        controls_layout.addWidget(self.duration_spin)
        
        main_layout.addLayout(controls_layout)
        
        # Tableau des fichiers
        self.file_list = QTableWidget()
        self.file_list.setColumnCount(2)
        self.file_list.setHorizontalHeaderLabels(["Fichier", "Statut"])
        self.file_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        main_layout.addWidget(self.file_list)
        
        # Labels pour les temps restants
        self.file_time_label = QLabel("Temps restant: --:--")
        self.comparison_time_label = QLabel("Temps restant: --:--")
        
        # Layout pour les barres de progression
        progress_layout = QVBoxLayout()
        
        # Barre de progression pour les fichiers
        file_progress_layout = QHBoxLayout()
        file_progress_layout.addWidget(QLabel("Fichiers:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFormat("%p% - %v/%m fichiers")
        file_progress_layout.addWidget(self.progress_bar)
        file_progress_layout.addWidget(self.file_time_label)
        progress_layout.addLayout(file_progress_layout)
        
        # Barre de progression pour les comparaisons
        comparison_progress_layout = QHBoxLayout()
        comparison_progress_layout.addWidget(QLabel("Comparaisons:"))
        self.compare_progress = QProgressBar()
        self.compare_progress.setVisible(False)
        self.compare_progress.setFormat("%p% - %v/%m comparaisons")
        comparison_progress_layout.addWidget(self.compare_progress)
        comparison_progress_layout.addWidget(self.comparison_time_label)
        progress_layout.addLayout(comparison_progress_layout)
        
        main_layout.addLayout(progress_layout)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        # Boutons d'ajout de fichiers
        buttons_layout.addWidget(QLabel("Fichiers:"))
        self.add_files_btn = QPushButton("📁 Ajouter des fichiers")
        self.add_folder_btn = QPushButton("📁 Ajouter un dossier")
        self.clear_btn = QPushButton("🧹 Vider la liste")
        self.add_files_btn.clicked.connect(self.add_files)
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.clear_btn.clicked.connect(self.clear_list)
        buttons_layout.addWidget(self.add_files_btn)
        buttons_layout.addWidget(self.add_folder_btn)
        buttons_layout.addWidget(self.clear_btn)
        
        # Boutons d'analyse
        analysis_buttons_layout = QHBoxLayout()
        
        self.clear_cache_btn = QPushButton("🧹 Vider le cache")
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        analysis_buttons_layout.addWidget(self.clear_cache_btn)
        
        self.analyze_btn = QPushButton("🔍 Analyser")
        self.analyze_btn.clicked.connect(self.start_analysis)
        self.analyze_btn.setEnabled(True)
        analysis_buttons_layout.addWidget(self.analyze_btn)
        
        self.stop_btn = QPushButton("⏹️ Arrêter")
        self.stop_btn.clicked.connect(self.stop_analysis)
        self.stop_btn.setEnabled(False)
        analysis_buttons_layout.addWidget(self.stop_btn)
        
        buttons_layout.addLayout(analysis_buttons_layout)
        
        # Bouton de fermeture
        close_buttons_layout = QHBoxLayout()
        
        self.close_btn = QPushButton("🚪 Fermer")
        self.close_btn.clicked.connect(self.close)
        close_buttons_layout.addWidget(self.close_btn)
        
        buttons_layout.addLayout(close_buttons_layout)
        
        main_layout.addLayout(buttons_layout)

    def load_existing_hashes(self):
        """Charge les hashs existants dans le tableau"""
        try:
            # Récupère tous les fichiers du cache
            if self.hash_method.value in self.video_hasher.hashes:
                cached_files = list(self.video_hasher.hashes[self.hash_method.value].keys())
                
                # Ajoute chaque fichier qui existe encore au tableau
                for file_path in cached_files:
                    if os.path.exists(file_path):
                        row = self.file_list.rowCount()
                        self.file_list.insertRow(row)
                        self.file_list.setItem(row, 0, QTableWidgetItem(file_path))
                        self.file_list.setItem(row, 1, QTableWidgetItem("✅ Analysé"))
                        self.files.append(file_path)
                
                # Active le bouton d'analyse s'il y a assez de fichiers
                self.analyze_btn.setEnabled(len(self.files) > 1)
                
                logger.info(f"{len(self.files)} fichiers chargés depuis le cache")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des hashs existants: {str(e)}")

    def start_analysis(self):
        """Démarre l'analyse des vidéos"""
        if len(self.files) < 2:
            QMessageBox.warning(
                self,
                "Attention",
                "Il faut au moins 2 fichiers à comparer"
            )
            return

        # Enregistre le temps de début
        self.start_time = time.time()

        # Désactive temporairement les contrôles pendant l'analyse
        self.add_files_btn.setEnabled(False)
        self.add_folder_btn.setEnabled(False)
        self.threshold_spin.setEnabled(False)
        self.duration_spin.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # Configure et affiche la barre de progression
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(self.files))
        self.progress_bar.setFormat("%p% - %v/%m fichiers - Temps restant: --:--")
        
        # Masque la barre de comparaison
        self.compare_progress.setVisible(False)

        # Récupère les paramètres
        threshold = self.threshold_spin.value()
        duration = self.duration_spin.value() * 60  # Conversion minutes en secondes

        # Met à jour la durée maximale dans le hasher
        self.video_hasher.duration = duration

        # Identifie les fichiers qui n'ont pas encore de hash
        files_to_hash = []
        for file_path in self.files:
            if not self.video_hasher.has_hash(file_path):
                files_to_hash.append(file_path)
                self.update_file_status(file_path, False)  # Marque comme absent
            else:
                self.update_file_status(file_path, True)  # Marque comme déjà analysé

        # Si des fichiers doivent être hashés, lance le worker
        if files_to_hash:
            # Crée et configure le worker
            self.worker = DuplicateFinderWorker(
                files_to_hash,
                self.video_hasher,
                threshold,
                self.hash_method.value,
                duration
            )
            
            # Connecte les signaux
            self.worker.progress.connect(self.update_progress)
            self.worker.finished.connect(self.analysis_finished)
            self.worker.error.connect(self.handle_error)
            self.worker.file_processed.connect(self.update_file_status)
            
            # Démarre le worker
            self.worker.start()
            logger.info("Démarrage de l'analyse des fichiers")
        else:
            # Si tous les fichiers sont déjà hashés, lance directement la comparaison
            self.analysis_finished()

    def analysis_finished(self):
        """Appelé quand l'analyse est terminée"""
        # Met à jour les statuts
        for file_path in self.files:
            if self.video_hasher.has_hash(file_path):
                self.update_file_status(file_path, True)
            else:
                self.update_file_status(file_path, False)

        # Lance la comparaison des fichiers
        self.compare_all_files()

    def enable_controls(self):
        """Réactive les contrôles de l'interface"""
        self.analyze_btn.setEnabled(True)
        self.add_files_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)
        self.threshold_spin.setEnabled(True)
        self.duration_spin.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def stop_analysis(self, show_confirmation=True):
        """Arrête l'analyse en cours"""
        if self.worker and self.worker.isRunning():
            if show_confirmation:
                reply = QMessageBox.question(
                    self,
                    "Confirmation",
                    "Voulez-vous vraiment arrêter l'analyse ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.worker.stop()
                    self.worker.wait()
                    self.analysis_finished()
            else:
                self.worker.stop()
                self.worker.wait()
                self.analysis_finished()

    def compare_all_files(self):
        """Compare tous les fichiers entre eux"""
        # Réinitialise la liste des doublons potentiels
        self.potential_duplicates = []
        
        # Configure et affiche la barre de progression pour la comparaison
        total_comparisons = len(self.files) * (len(self.files) - 1) // 2
        
        # Enregistre le temps de début pour la comparaison
        self.compare_start_time = time.time()
        
        self.compare_progress.setVisible(True)
        self.compare_progress.setValue(0)
        self.compare_progress.setMaximum(total_comparisons)
        self.compare_progress.setFormat("%p% - %v/%m comparaisons - Temps restant: --:--")
        
        # Compare chaque paire de fichiers
        current_comparison = 0
        for i, file1 in enumerate(self.files):
            # Vérifie si on doit arrêter
            if self.worker and self.worker._stop:
                logger.info("Arrêt des comparaisons demandé")
                break

            for file2 in self.files[i+1:]:
                # Vérifie si on doit arrêter
                if self.worker and self.worker._stop:
                    logger.info("Arrêt des comparaisons demandé")
                    break

                # Vérifie si la paire n'est pas ignorée
                if frozenset([file1, file2]) not in self.ignored_pairs:
                    # Compare les hashs
                    similarity = self.video_hasher.compare_videos(file1, file2)
                    
                    # Si la similarité dépasse le seuil, ajoute aux doublons potentiels
                    if similarity > self.threshold_spin.value() / 100:
                        self.potential_duplicates.append((file1, file2, similarity))
                
                # Met à jour la progression
                current_comparison += 1
                
                # Met à jour le temps restant pour la comparaison
                if current_comparison > 0:
                    elapsed = time.time() - self.compare_start_time
                    rate = elapsed / current_comparison  # temps par comparaison
                    remaining = rate * (total_comparisons - current_comparison)
                    
                    # Formate le temps restant
                    minutes = int(remaining // 60)
                    seconds = int(remaining % 60)
                    time_str = f"{minutes:02d}:{seconds:02d}"
                    
                    # Met à jour le format
                    self.compare_progress.setFormat(f"%p% - %v/%m comparaisons - Temps restant: {time_str}")
                
                self.compare_progress.setValue(current_comparison)

        # Si on n'a pas été arrêté
        if not (self.worker and self.worker._stop):
            # Trie les doublons par similarité décroissante
            self.potential_duplicates.sort(key=lambda x: x[2], reverse=True)
            
            # Lance la comparaison du premier doublon
            self.compare_next_duplicate()
        else:
            # Réactive les contrôles
            self.enable_controls()
            logger.info("Comparaisons arrêtées")

    def update_progress(self, value):
        """Met à jour la barre de progression"""
        self.progress_bar.setValue(value)
        
        # Calcule le temps restant
        if self.start_time and value > 0:
            elapsed = time.time() - self.start_time
            rate = elapsed / value  # temps par fichier
            remaining = rate * (self.progress_bar.maximum() - value)
            
            # Formate le temps restant
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            # Met à jour le format
            self.progress_bar.setFormat(f"%p% - %v/%m fichiers - Temps restant: {time_str}")

    def handle_error(self, error):
        """Gère les erreurs du worker"""
        QMessageBox.critical(
            self,
            "Erreur",
            f"Une erreur est survenue pendant l'analyse : {error}"
        )
        self.analysis_finished()

    def update_file_status(self, file_path, success):
        """Met à jour le statut d'un fichier"""
        # Trouve l'index du fichier dans la liste
        for i in range(self.file_list.rowCount()):
            if self.file_list.item(i, 0).text() == file_path:
                # Met à jour le statut
                status = "✅ Analysé" if success else "⏳ En attente"
                self.file_list.item(i, 1).setText(status)
                break

    def clear_list(self):
        """Vide la liste des fichiers"""
        self.files.clear()
        self.file_list.setRowCount(0)
        self.analyze_btn.setEnabled(False)

    def add_files(self):
        """Ajoute des fichiers vidéo à analyser"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner des fichiers vidéo",
            "",
            "Vidéos (*.mp4 *.avi *.mkv *.mov);;Tous les fichiers (*.*)"
        )
        
        if files:
            # Ajoute les fichiers à la liste
            for file_path in files:
                if file_path not in self.files:
                    row = self.file_list.rowCount()
                    self.file_list.insertRow(row)
                    self.file_list.setItem(row, 0, QTableWidgetItem(file_path))
                    self.file_list.setItem(row, 1, QTableWidgetItem("❌ Absent"))
                    self.files.append(file_path)
                    
                    # Vérifie si le hash existe déjà
                    if self.video_hasher.has_hash(file_path):
                        self.update_file_status(file_path, True)
                    else:
                        self.update_file_status(file_path, False)
            
            # Active le bouton d'analyse s'il y a assez de fichiers
            self.analyze_btn.setEnabled(len(self.files) > 1)
            
    def add_folder(self):
        """Ajoute un dossier de vidéos à analyser"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner un dossier de vidéos",
            ""
        )
        
        if folder:
            video_extensions = ('.mp4', '.avi', '.mkv', '.mov')
            
            # Parcourt le dossier
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(video_extensions):
                        file_path = os.path.join(root, file)
                        if file_path not in self.files:
                            self.files.append(file_path)
                            row = self.file_list.rowCount()
                            self.file_list.insertRow(row)
                            self.file_list.setItem(row, 0, QTableWidgetItem(os.path.basename(file_path)))
                            self.file_list.setItem(row, 1, QTableWidgetItem("❌ Absent"))
            
            # Active le bouton d'analyse s'il y a assez de fichiers
            self.analyze_btn.setEnabled(len(self.files) > 1)

    def clear_cache(self):
        """Vide le cache des hashs"""
        try:
            # Sauvegarde la liste des fichiers
            files = self.files.copy()
            
            # Vide le cache
            self.video_hasher.clear_cache()
            
            # Restaure la liste des fichiers
            self.files = files
            
            # Met à jour les statuts
            for file in self.files:
                self.update_file_status(file, False)  # Tous les fichiers sont à réanalyser
            
            QMessageBox.information(
                self,
                "Cache vidé",
                "Le cache des hashs a été vidé avec succès"
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de vider le cache : {e}")

    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirmation",
                "Une analyse est en cours. Voulez-vous vraiment quitter ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.stop()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
            
        # Émet le signal de fermeture
        self.closed.emit()

    def compare_next_duplicate(self):
        """Compare le prochain doublon potentiel"""
        if not self.potential_duplicates:
            # Plus de doublons à comparer
            QMessageBox.information(
                self,
                "Analyse terminée",
                "L'analyse des doublons est terminée"
            )
            self.enable_controls()
            return

        # Récupère le prochain doublon à comparer
        file1, file2, similarity = self.potential_duplicates[0]
        
        # Crée et affiche la fenêtre de comparaison
        dialog = DuplicateComparisonDialog(file1, file2, similarity, self)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # Traite le résultat de la comparaison
            if dialog.result == "keep_left":
                try:
                    os.remove(file2)
                    self.update_file_status(file2, False)
                    logger.info(f"Fichier supprimé : {file2}")
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Erreur",
                        f"Impossible de supprimer le fichier : {e}"
                    )
                    logger.error(f"Erreur lors de la suppression de {file2}: {str(e)}")
            elif dialog.result == "keep_right":
                try:
                    os.remove(file1)
                    self.update_file_status(file1, False)
                    logger.info(f"Fichier supprimé : {file1}")
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Erreur",
                        f"Impossible de supprimer le fichier : {e}"
                    )
                    logger.error(f"Erreur lors de la suppression de {file1}: {str(e)}")
            elif dialog.result == "ignore_perm":
                # Ajoute la paire à la liste des paires ignorées
                self.ignored_pairs.add(frozenset([file1, file2]))
                self.save_ignored_pairs()
                logger.info(f"Paire ignorée : {file1} - {file2}")

            # Supprime le doublon traité de la liste
            self.potential_duplicates.pop(0)
            
            # Continue avec le prochain doublon
            self.compare_next_duplicate()
        else:
            # Si la fenêtre a été fermée, on arrête les comparaisons
            logger.info("Comparaisons arrêtées par l'utilisateur")
            self.enable_controls()


class DuplicateFinderWorker(QThread):
    """Worker pour l'analyse des doublons"""
    progress = pyqtSignal(int)  # progression en pourcentage
    finished = pyqtSignal()  # analyse terminée
    error = pyqtSignal(str)  # erreur pendant l'analyse
    file_processed = pyqtSignal(str, bool)  # fichier traité (chemin, succès)
    
    def __init__(self, files, video_hasher, threshold, hash_method, duration):
        """Initialise le worker"""
        super().__init__()
        self.files = files
        self.video_hasher = video_hasher
        self.threshold = threshold
        self.hash_method = hash_method
        self.duration = duration
        self._stop = False
        
    def stop(self):
        """Arrête le worker"""
        self._stop = True
        
    def run(self):
        """Exécute l'analyse"""
        total_files = len(self.files)
        processed_files = 0
        
        for file_path in self.files:
            if self._stop:
                logger.info("Arrêt demandé avant le traitement du fichier")
                break
                
            try:
                # Met à jour le statut en "En cours"
                self.file_processed.emit(file_path, False)
                
                # Vérifie si la vidéo peut être ouverte
                cap = cv2.VideoCapture(file_path)
                if not cap.isOpened():
                    raise Exception("Impossible d'ouvrir la vidéo")
                    
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if total_frames <= 0:
                    raise Exception("Vidéo invalide")
                    
                cap.release()
                
                # Si on arrive ici, la vidéo est valide
                # Vérifie si on doit s'arrêter avant de calculer le hash
                if self._stop:
                    logger.info("Arrêt demandé avant le calcul du hash")
                    break
                    
                self.video_hasher.compute_video_hash(file_path)
                # Émet le signal de succès
                self.file_processed.emit(file_path, True)
                
            except Exception as e:
                # En cas d'erreur, émet le signal d'échec
                self.file_processed.emit(file_path, False)
                logger.error(f"Erreur lors du traitement de {file_path}: {str(e)}")
            
            # Met à jour la progression
            processed_files += 1
            self.progress.emit(processed_files)
            
        self.finished.emit()


class HashMethod(Enum):
    """Méthodes de hachage disponibles"""
    PHASH = "pHash"
