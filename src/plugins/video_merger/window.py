import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                           QFileDialog, QLabel, QProgressBar, QTextEdit,
                           QTableWidget, QTableWidgetItem, QMessageBox, QWidget,
                           QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import cv2
from moviepy.editor import VideoFileClip, concatenate_videoclips
from proglog import ProgressBarLogger
import subprocess
import tempfile
from send2trash import send2trash

from src.core.logger import Logger

logger = Logger.get_logger('VideoMerger.Window')

class VideoMergerWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fusionneur de vidéos")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)  # Fenêtre modale
        
        # Liste des vidéos à fusionner
        self.videos = []
        self.merge_thread = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        layout = QVBoxLayout()
        
        # Boutons d'action en haut
        top_buttons = QHBoxLayout()
        
        self.add_btn = QPushButton("📁 Ajouter Fichiers")
        self.add_btn.clicked.connect(self.add_files)
        top_buttons.addWidget(self.add_btn)
        
        self.add_folder_btn = QPushButton("📂 Ajouter Dossier")
        self.add_folder_btn.clicked.connect(self.add_folder)
        top_buttons.addWidget(self.add_folder_btn)
        
        top_buttons.addStretch()
        
        self.merge_btn = QPushButton("✨ Fusionner")
        self.merge_btn.clicked.connect(self.merge_videos)
        self.merge_btn.setEnabled(False)
        top_buttons.addWidget(self.merge_btn)
        
        self.stop_btn = QPushButton("⏹️ Arrêter")
        self.stop_btn.clicked.connect(self.stop_merge)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setVisible(False)
        top_buttons.addWidget(self.stop_btn)
        
        # Checkbox pour la suppression des fichiers originaux
        self.delete_originals_cb = QCheckBox("Supprimer les fichiers originaux après la fusion")
        top_buttons.addWidget(self.delete_originals_cb)
        
        # Bouton Fermer
        self.close_btn = QPushButton("❌ Fermer")
        self.close_btn.clicked.connect(self.close)
        top_buttons.addWidget(self.close_btn)
        
        layout.addLayout(top_buttons)
        
        # Table des vidéos
        self.videos_table = QTableWidget()
        self.videos_table.setColumnCount(7)
        self.videos_table.setHorizontalHeaderLabels([
            "Fichier", "Résolution", "Durée", "État", "Ordre", "Action", "Supprimer"
        ])
        self.videos_table.horizontalHeader().setStretchLastSection(False)
        self.videos_table.setColumnWidth(0, 300)  # Fichier
        self.videos_table.setColumnWidth(1, 100)  # Résolution
        self.videos_table.setColumnWidth(2, 100)  # Durée
        self.videos_table.setColumnWidth(3, 100)  # État
        self.videos_table.setColumnWidth(4, 50)   # Ordre
        self.videos_table.setColumnWidth(5, 80)   # Action
        self.videos_table.setColumnWidth(6, 80)   # Supprimer
        layout.addWidget(self.videos_table)
        
        # Barres de progression
        progress_layout = QVBoxLayout()
        
        # Barre principale
        progress_group = QHBoxLayout()
        self.progress_label = QLabel("Progression totale :")
        progress_group.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_group.addWidget(self.progress_bar)
        progress_layout.addLayout(progress_group)
        
        # Barre MoviePy
        moviepy_group = QHBoxLayout()
        self.moviepy_label = QLabel("Progression de l'encodage :")
        moviepy_group.addWidget(self.moviepy_label)
        
        self.moviepy_progress_bar = QProgressBar()
        self.moviepy_progress_bar.setVisible(False)
        moviepy_group.addWidget(self.moviepy_progress_bar)
        progress_layout.addLayout(moviepy_group)
        
        layout.addLayout(progress_layout)
        
        # Journal
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        self.setLayout(layout)
    
    def add_files(self):
        """Ajoute des fichiers vidéo à la liste"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner les fichiers vidéo",
            "",
            "Vidéos (*.mp4 *.avi *.mkv *.mov);;Tous les fichiers (*.*)"
        )
        
        if files:
            # Trier les fichiers par ordre alphabétique
            files.sort()
            self.add_videos(files)
    
    def add_folder(self):
        """Ajoute tous les fichiers vidéo d'un dossier"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner un dossier contenant des vidéos"
        )
        
        if folder:
            video_files = []
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
                        video_files.append(os.path.join(root, file))
            
            if video_files:
                # Trier les fichiers par ordre alphabétique
                video_files.sort()
                self.add_videos(video_files)
    
    def add_videos(self, files):
        """Ajoute les vidéos à la table"""
        current_row = self.videos_table.rowCount()
        self.videos_table.setRowCount(current_row + len(files))
        
        for i, file in enumerate(files):
            if file not in self.videos:
                self.videos.append(file)
                row = current_row + i
                
                # Nom du fichier
                file_item = QTableWidgetItem(os.path.basename(file))
                self.videos_table.setItem(row, 0, file_item)
                
                try:
                    # Obtenir les informations de la vidéo
                    cap = cv2.VideoCapture(file)
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    duration = frames / fps if fps > 0 else 0
                    cap.release()
                    
                    # Résolution
                    res_item = QTableWidgetItem(f"{width}x{height}")
                    self.videos_table.setItem(row, 1, res_item)
                    
                    # Durée
                    duration_item = QTableWidgetItem(f"{duration:.1f}s")
                    self.videos_table.setItem(row, 2, duration_item)
                    
                    # État
                    status_item = QTableWidgetItem("Prêt")
                    self.videos_table.setItem(row, 3, status_item)
                    
                except Exception as e:
                    logger.error(f"Erreur lors de l'analyse de {file}: {str(e)}")
                    for col in range(1, 3):
                        self.videos_table.setItem(row, col, QTableWidgetItem("Erreur"))
                    status_item = QTableWidgetItem("Erreur")
                    self.videos_table.setItem(row, 3, status_item)
                
                # Ordre
                order_item = QTableWidgetItem(str(row + 1))
                self.videos_table.setItem(row, 4, order_item)
                
                # Ordre et boutons de déplacement
                order_layout = QHBoxLayout()
                order_widget = QWidget()
                
                up_btn = QPushButton("⬆️")
                up_btn.setFixedWidth(30)
                up_btn.clicked.connect(lambda checked, r=row: self.move_video_up(r))
                up_btn.setEnabled(row > 0)
                
                down_btn = QPushButton("⬇️")
                down_btn.setFixedWidth(30)
                down_btn.clicked.connect(lambda checked, r=row: self.move_video_down(r))
                down_btn.setEnabled(row < len(self.videos) - 1)
                
                order_layout.addWidget(up_btn)
                order_layout.addWidget(down_btn)
                order_layout.setContentsMargins(0, 0, 0, 0)
                order_widget.setLayout(order_layout)
                self.videos_table.setCellWidget(row, 5, order_widget)
                
                # Bouton Supprimer
                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedWidth(40)
                delete_btn.clicked.connect(lambda checked, r=row: self.remove_video(r))
                self.videos_table.setCellWidget(row, 6, delete_btn)
        
        self.merge_btn.setEnabled(len(self.videos) > 1)
        self.log_message(f"{len(files)} fichier(s) ajouté(s)")
    
    def remove_video(self, row):
        """Supprime une vidéo de la liste"""
        file = self.videos[row]
        self.videos.pop(row)
        self.videos_table.removeRow(row)
        self.merge_btn.setEnabled(len(self.videos) > 1)
        self.log_message(f"Vidéo supprimée : {os.path.basename(file)}")
    
    def merge_videos(self):
        """Démarre la fusion des vidéos"""
        if len(self.videos) < 2:
            QMessageBox.warning(self, "Erreur", "Il faut au moins 2 vidéos à fusionner")
            return
        
        # Trouver le préfixe commun et l'extension du premier fichier
        common_name = self.find_common_prefix(self.videos)
        _, ext = os.path.splitext(self.videos[0])
        suggested_name = f"{common_name}_merged{ext}"
        
        # Demander où sauvegarder la vidéo finale
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Sauvegarder la vidéo fusionnée",
            suggested_name,  # Utiliser le nom suggéré
            f"Vidéo (*{ext})"
        )
        
        if not output_file:
            return
            
        # Vérifier si les vidéos sont compatibles pour une fusion rapide
        self.log_message("Vérification de la compatibilité des vidéos...")
        try:
            if self.check_video_compatibility(self.videos):
                self.log_message("✅ Les vidéos sont compatibles pour une fusion rapide")
                merge_method = "ffmpeg"
            else:
                self.log_message("⚠️ Les vidéos ne sont pas compatibles pour une fusion rapide")
                self.log_message("Utilisation de MoviePy pour la fusion (plus lent mais plus flexible)")
                merge_method = "moviepy"
        except Exception as e:
            self.log_message(f"❌ Erreur lors de la vérification : {str(e)}")
            self.log_message("Utilisation de MoviePy pour la fusion")
            merge_method = "moviepy"
            
        self.merge_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.stop_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.moviepy_progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.moviepy_progress_bar.setValue(0)
        
        # Lancer la fusion dans un thread séparé
        self.merge_thread = MergeThread(self.videos, output_file)
        self.merge_thread.progress.connect(self.update_progress)
        self.merge_thread.moviepy_progress.connect(self.update_moviepy_progress)
        self.merge_thread.message.connect(self.log_message)
        self.merge_thread.finished.connect(self.merge_finished)
        
        self.merge_thread.start()
    
    def stop_merge(self):
        """Arrête la fusion en cours"""
        if hasattr(self, 'merge_thread') and self.merge_thread.isRunning():
            self.merge_thread.stop()
            self.log_message("Arrêt de la fusion...")
    
    def merge_finished(self):
        """Appelé quand la fusion est terminée"""
        # Supprimer les fichiers originaux si demandé
        if self.delete_originals_cb.isChecked():
            try:
                for video in self.videos:
                    send2trash(video)
                self.log_message("Fichiers originaux déplacés vers la corbeille")
            except Exception as e:
                self.log_message(f"Erreur lors de la suppression des fichiers : {str(e)}")
        
        self.merge_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.moviepy_progress_bar.setVisible(False)
        self.log_message("Fusion terminée")
    
    def update_progress(self, value):
        """Met à jour la barre de progression"""
        self.progress_bar.setValue(value)
    
    def update_moviepy_progress(self, value):
        """Met à jour la barre de progression MoviePy"""
        self.moviepy_progress_bar.setValue(value)
    
    def log_message(self, message):
        """Ajoute un message au journal"""
        self.log_text.append(message)
    
    def move_video_up(self, row):
        """Déplace une vidéo vers le haut"""
        if row > 0:
            # Échanger les vidéos
            self.videos[row], self.videos[row-1] = self.videos[row-1], self.videos[row]
            
            # Mettre à jour les deux lignes affectées
            self.update_table_row(row-1)
            self.update_table_row(row)
            
            # Mettre à jour les boutons de la ligne précédente
            self.update_row_buttons(row-1)
            self.update_row_buttons(row)
            
            self.log_message(f"Vidéo déplacée vers le haut : {os.path.basename(self.videos[row-1])}")
    
    def move_video_down(self, row):
        """Déplace une vidéo vers le bas"""
        if row < len(self.videos) - 1:
            # Échanger les vidéos
            self.videos[row], self.videos[row+1] = self.videos[row+1], self.videos[row]
            
            # Mettre à jour les deux lignes affectées
            self.update_table_row(row)
            self.update_table_row(row+1)
            
            # Mettre à jour les boutons des deux lignes
            self.update_row_buttons(row)
            self.update_row_buttons(row+1)
            
            self.log_message(f"Vidéo déplacée vers le bas : {os.path.basename(self.videos[row+1])}")
    
    def update_table_row(self, row):
        """Met à jour une ligne spécifique du tableau"""
        file = self.videos[row]
        
        # Nom du fichier
        self.videos_table.setItem(row, 0, QTableWidgetItem(os.path.basename(file)))
        
        try:
            # Obtenir les informations de la vidéo
            cap = cv2.VideoCapture(file)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = frames / fps if fps > 0 else 0
            cap.release()
            
            # Résolution
            self.videos_table.setItem(row, 1, QTableWidgetItem(f"{width}x{height}"))
            
            # Durée
            self.videos_table.setItem(row, 2, QTableWidgetItem(f"{duration:.1f}s"))
            
            # État
            self.videos_table.setItem(row, 3, QTableWidgetItem("Prêt"))
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de {file}: {str(e)}")
            for col in range(1, 3):
                self.videos_table.setItem(row, col, QTableWidgetItem("Erreur"))
            self.videos_table.setItem(row, 3, QTableWidgetItem("Erreur"))
        
        # Ordre
        self.videos_table.setItem(row, 4, QTableWidgetItem(str(row + 1)))
    
    def update_row_buttons(self, row):
        """Met à jour les boutons de déplacement d'une ligne"""
        # Créer les boutons de déplacement
        order_layout = QHBoxLayout()
        order_widget = QWidget()
        
        up_btn = QPushButton("⬆️")
        up_btn.setFixedWidth(30)
        up_btn.clicked.connect(lambda checked, r=row: self.move_video_up(r))
        up_btn.setEnabled(row > 0)
        
        down_btn = QPushButton("⬇️")
        down_btn.setFixedWidth(30)
        down_btn.clicked.connect(lambda checked, r=row: self.move_video_down(r))
        down_btn.setEnabled(row < len(self.videos) - 1)
        
        order_layout.addWidget(up_btn)
        order_layout.addWidget(down_btn)
        order_layout.setContentsMargins(0, 0, 0, 0)
        order_widget.setLayout(order_layout)
        
        # Mettre à jour les widgets
        self.videos_table.setCellWidget(row, 5, order_widget)
        
        # Bouton Supprimer
        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedWidth(40)
        delete_btn.clicked.connect(lambda checked, r=row: self.remove_video(r))
        self.videos_table.setCellWidget(row, 6, delete_btn)

    def find_common_prefix(self, filenames):
        """Trouve le préfixe commun entre plusieurs noms de fichiers"""
        if not filenames:
            return ""
        
        # Extraire les noms de base sans extension ni chemin
        basenames = [os.path.splitext(os.path.basename(f))[0] for f in filenames]
        
        # Si un seul fichier, retourner son nom
        if len(basenames) == 1:
            return basenames[0]
        
        # Trouver le préfixe commun
        prefix = os.path.commonprefix(basenames)
        
        # Nettoyer le préfixe (enlever les caractères incomplets à la fin)
        while prefix and not any(name.startswith(prefix) for name in basenames):
            prefix = prefix[:-1]
        
        # Si pas de préfixe commun, utiliser le premier nom
        return prefix if prefix else basenames[0]
    
    def check_video_compatibility(self, videos):
        """Vérifie si les vidéos sont compatibles pour une fusion rapide"""
        if not videos:
            return False
            
        # Récupérer les infos de la première vidéo
        cap = cv2.VideoCapture(videos[0])
        if not cap.isOpened():
            return False
            
        first_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        first_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        first_fps = cap.get(cv2.CAP_PROP_FPS)
        first_fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        cap.release()
        
        # Vérifier que toutes les vidéos ont les mêmes propriétés
        for video in videos[1:]:
            cap = cv2.VideoCapture(video)
            if not cap.isOpened():
                return False
                
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            cap.release()
            
            if (width != first_width or height != first_height or 
                abs(fps - first_fps) > 0.1 or fourcc != first_fourcc):
                return False
        
        return True

class MoviePyLogger(ProgressBarLogger):
    """Classe pour gérer les logs de MoviePy basée sur proglog"""
    def __init__(self, message_signal, progress_signal):
        super().__init__()
        self.message_signal = message_signal
        self.progress_signal = progress_signal
        self.last_progress = 0
        
    def callback(self, **changes):
        # Afficher les messages de progression
        for (parameter, value) in changes.items():
            message = f"{parameter}: {value}"
            self.message_signal.emit(message)
            
            # Gérer la progression
            if parameter == "t":
                try:
                    percent = int(min(value * 100 / self.bars["t"]["total"], 100))
                    if percent != self.last_progress:
                        self.progress_signal.emit(percent)
                        self.last_progress = percent
                except:
                    pass
    
    def bars_callback(self, bar, attr, value, old_value=None):
        super().bars_callback(bar, attr, value, old_value)
        
        # Afficher les messages spéciaux
        if bar == "t":
            if attr == "total":
                self.message_signal.emit("Début de l'encodage...")
            elif attr == "index" and value >= old_value:
                if value >= self.bars["t"]["total"]:
                    self.message_signal.emit("Encodage terminé")

class MergeThread(QThread):
    progress = pyqtSignal(int)
    moviepy_progress = pyqtSignal(int)
    message = pyqtSignal(str)
    
    def __init__(self, videos, output_file):
        super().__init__()
        self.videos = sorted(videos)  # Tri alphabétique par défaut
        self.output_file = output_file
        self._stop = False
    
    def check_video_compatibility(self, videos):
        """Vérifie si les vidéos sont compatibles pour une fusion directe"""
        try:
            if len(videos) < 2:
                return False
                
            # Obtenir les informations de la première vidéo
            cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", 
                  "-show_entries", "stream=width,height,codec_name,r_frame_rate", 
                  "-of", "json", videos[0]]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return False
                
            import json
            base_info = json.loads(result.stdout)
            if not base_info.get("streams"):
                return False
                
            base_stream = base_info["streams"][0]
            base_codec = base_stream.get("codec_name")
            base_width = base_stream.get("width")
            base_height = base_stream.get("height")
            base_fps = base_stream.get("r_frame_rate")
            
            # Vérifier chaque vidéo
            for video in videos[1:]:
                cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
                      "-show_entries", "stream=width,height,codec_name,r_frame_rate",
                      "-of", "json", video]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    return False
                    
                info = json.loads(result.stdout)
                if not info.get("streams"):
                    return False
                    
                stream = info["streams"][0]
                if (stream.get("codec_name") != base_codec or
                    stream.get("width") != base_width or
                    stream.get("height") != base_height or
                    stream.get("r_frame_rate") != base_fps):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de compatibilité : {str(e)}")
            return False
    
    def merge_with_ffmpeg(self, videos, output_file):
        """Fusionne les vidéos directement avec FFmpeg"""
        try:
            # Créer un fichier temporaire pour la liste des vidéos
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for video in videos:
                    f.write(f"file '{video}'\n")
                temp_list = f.name
            
            # Commande FFmpeg pour la concaténation
            cmd = [
                "ffmpeg", "-y",  # Écraser le fichier de sortie si existe
                "-f", "concat",
                "-safe", "0",
                "-i", temp_list,
                "-c", "copy",  # Copier sans réencodage
                output_file
            ]
            
            # Lancer FFmpeg
            self.message.emit("Fusion des vidéos avec FFmpeg...")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Suivre la progression
            duration_total = 0
            for video in videos:
                cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=noprint_wrappers=1:nokey=1", video]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    duration_total += float(result.stdout.strip())
            
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                    
                if "time=" in line:
                    time_str = line.split("time=")[1].split()[0]
                    try:
                        hours, minutes, seconds = map(float, time_str.split(":"))
                        current_time = hours * 3600 + minutes * 60 + seconds
                        progress = min(int(current_time * 100 / duration_total), 100)
                        self.moviepy_progress.emit(progress)
                        self.progress.emit(progress)
                    except:
                        pass
            
            # Nettoyage
            os.unlink(temp_list)
            
            if process.returncode == 0:
                self.message.emit("Fusion terminée avec succès !")
                return True
            else:
                self.message.emit("Erreur lors de la fusion FFmpeg")
                return False
                
        except Exception as e:
            self.message.emit(f"Erreur lors de la fusion FFmpeg : {str(e)}")
            logger.error(f"Erreur lors de la fusion FFmpeg : {str(e)}")
            return False
    
    def run(self):
        """Fusionne les vidéos"""
        try:
            # Vérifier si on peut utiliser FFmpeg directement
            if self.check_video_compatibility(self.videos):
                self.message.emit("Les vidéos sont compatibles pour une fusion rapide...")
                if self.merge_with_ffmpeg(self.videos, self.output_file):
                    return
                self.message.emit("La fusion rapide a échoué, tentative avec MoviePy...")
            
            # Si FFmpeg échoue ou les vidéos sont incompatibles, utiliser MoviePy
            self.message.emit("Fusion avec MoviePy (peut prendre plus de temps)...")
            clips = []
            total_videos = len(self.videos)
            
            for i, video in enumerate(self.videos):
                if self._stop:
                    return
                
                self.message.emit(f"Chargement de {os.path.basename(video)}...")
                clip = VideoFileClip(video)
                clips.append(clip)
                self.progress.emit(int((i + 1) / total_videos * 50))
            
            if self._stop:
                return
            
            # Fusionner les vidéos
            self.message.emit("Fusion des vidéos...")
            final_clip = concatenate_videoclips(clips)
            
            # Créer le logger personnalisé
            moviepy_logger = MoviePyLogger(self.message, self.moviepy_progress)
            
            # Sauvegarder le résultat
            self.message.emit("Encodage de la vidéo finale...")
            final_clip.write_videofile(
                self.output_file,
                codec='libx264',
                audio_codec='aac',
                logger=moviepy_logger
            )
            
            # Nettoyer
            final_clip.close()
            for clip in clips:
                clip.close()
            
            self.progress.emit(100)
            self.moviepy_progress.emit(100)
            self.message.emit("Fusion terminée avec succès !")
            
        except Exception as e:
            self.message.emit(f"Erreur lors de la fusion : {str(e)}")
            logger.error(f"Erreur de fusion : {str(e)}")
    
    def stop(self):
        """Arrête la fusion"""
        self._stop = True
