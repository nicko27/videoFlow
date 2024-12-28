from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QLabel, QSlider, QFileDialog, QTableWidget,
                           QProgressBar, QTableWidgetItem, QMenu, QInputDialog,
                           QMessageBox, QApplication)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QColor, QPainter, QPen
import cv2
from moviepy.editor import VideoFileClip
from .video_analyzer import VideoAnalyzer
from .data_manager import DataManager
from .timeline import Timeline
from .waveform import WaveformWidget
from src.core.logger import Logger
import tempfile
import os
import numpy as np
import subprocess

logger = Logger.get_logger('VideoEditor.Window')

class VideoEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Éditeur de Vidéos")
        self.setMinimumSize(1200, 800)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        # Variables d'état
        self.video_path = None
        self.cap = None
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 0
        self.playing = False
        self.analyzer = None
        self.data_manager = None
        
        # Timer pour la lecture
        self.play_timer = QTimer()
        self.play_timer.timeout.connect(self.next_frame)
        
        self.init_ui()
        logger.debug("Fenêtre VideoEditor initialisée")
    
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Boutons d'action en haut
        top_buttons = QHBoxLayout()
        
        self.open_btn = QPushButton("📁 Ouvrir")
        self.open_btn.clicked.connect(self.open_video_dialog)
        top_buttons.addWidget(self.open_btn)
        
        self.play_btn = QPushButton("▶️ Lecture")
        self.play_btn.clicked.connect(self.toggle_play)
        self.play_btn.setEnabled(False)
        top_buttons.addWidget(self.play_btn)
        
        top_buttons.addStretch()
        
        self.export_btn = QPushButton("✂️ Effectuer les découpes")
        self.export_btn.clicked.connect(self.export_segments)
        self.export_btn.setEnabled(False)
        top_buttons.addWidget(self.export_btn)
        
        layout.addLayout(top_buttons)
        
        # Boutons de découpe
        cut_layout = QHBoxLayout()
        
        self.start_cut_btn = QPushButton("Début ✂️")
        self.start_cut_btn.clicked.connect(self.start_cut)
        self.start_cut_btn.setEnabled(False)
        cut_layout.addWidget(self.start_cut_btn)
        
        self.end_cut_btn = QPushButton("Fin ✂️")
        self.end_cut_btn.clicked.connect(self.end_cut)
        self.end_cut_btn.setEnabled(False)
        cut_layout.addWidget(self.end_cut_btn)
        
        self.cancel_cut_btn = QPushButton("Annuler ❌")
        self.cancel_cut_btn.clicked.connect(self.cancel_cut)
        self.cancel_cut_btn.setEnabled(False)
        cut_layout.addWidget(self.cancel_cut_btn)
        
        layout.addLayout(cut_layout)
        
        # Zone de prévisualisation
        self.preview = QLabel()
        self.preview.setMinimumSize(640, 360)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet("background-color: black;")
        layout.addWidget(self.preview)
        
        # Timeline
        self.timeline = Timeline()
        self.timeline.positionChanged.connect(self.on_timeline_position_changed)
        self.timeline.segmentCreated.connect(self.on_segment_created)
        self.timeline.segmentDeleted.connect(self.on_segment_deleted)
        layout.addWidget(self.timeline)
        
        # Contrôles de lecture
        controls_layout = QHBoxLayout()
        
        self.prev_frame_btn = QPushButton("⏮️")
        self.prev_frame_btn.clicked.connect(self.prev_frame)
        self.prev_frame_btn.setEnabled(False)
        controls_layout.addWidget(self.prev_frame_btn)
        
        self.next_frame_btn = QPushButton("⏭️")
        self.next_frame_btn.clicked.connect(self.next_frame)
        self.next_frame_btn.setEnabled(False)
        controls_layout.addWidget(self.next_frame_btn)
        
        self.time_label = QLabel("00:00 / 00:00")
        controls_layout.addWidget(self.time_label)
        
        layout.addLayout(controls_layout)
        
        # Tableau des segments
        self.segments_table = QTableWidget()
        self.segments_table.setColumnCount(5)
        self.segments_table.setHorizontalHeaderLabels(["Statut", "Début", "Fin", "Durée", "Actions"])
        self.segments_table.horizontalHeader().setStretchLastSection(True)
        self.segments_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.segments_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.segments_table)
        
        # Forme d'onde audio
        self.waveform_widget = WaveformWidget()
        layout.addWidget(self.waveform_widget)
        
        logger.debug("Interface VideoEditor initialisée")
    
    def open_video_dialog(self):
        """Ouvre une boîte de dialogue pour sélectionner une vidéo"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir une vidéo",
            "",
            "Vidéos (*.mp4 *.avi *.mov *.mkv);;Tous les fichiers (*.*)"
        )
        
        if file_path:
            self.open_video(file_path)
    
    def open_video(self, file_path):
        """Ouvre une vidéo"""
        # Fermer la vidéo précédente
        if self.cap is not None:
            self.cap.release()
        
        # Ouvrir la nouvelle vidéo
        self.cap = cv2.VideoCapture(file_path)
        if not self.cap.isOpened():
            return
        
        self.video_path = file_path
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Configurer la timeline
        self.timeline.set_duration(self.total_frames)
        
        # Activer les contrôles
        self.play_btn.setEnabled(True)
        self.prev_frame_btn.setEnabled(True)
        self.next_frame_btn.setEnabled(True)
        self.start_cut_btn.setEnabled(True)
        
        # Extraire la forme d'onde
        self.extract_waveform()
        
        # Afficher la première frame
        self.show_frame(0)
        
        # Charger les segments existants
        self.load_segments()
        
        logger.debug(f"Vidéo ouverte : {file_path}")
    
    def extract_waveform(self):
        """Extrait la forme d'onde audio de la vidéo"""
        if not self.video_path:
            return
            
        try:
            logger.debug("Extraction de la forme d'onde audio...")
            video = VideoFileClip(self.video_path)
            
            if video.audio is not None:
                # Extraire l'audio
                audio = video.audio.to_soundarray()
                
                # Si stéréo, convertir en mono
                if len(audio.shape) > 1:
                    audio = np.mean(audio, axis=1)
                
                # Envoyer à la waveform
                self.waveform_widget.set_waveform_data(audio)
                logger.debug("Forme d'onde extraite avec succès")
            else:
                logger.warning("Pas de piste audio dans la vidéo")
            
            video.close()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de la forme d'onde : {e}")
    
    def update_waveform_position(self, frame):
        """Met à jour la position dans la forme d'onde"""
        if self.total_frames > 0:
            position = frame / self.total_frames
            self.waveform_widget.set_position(position)

    def detect_scenes(self):
        """Détecte les changements de scène"""
        if not self.analyzer:
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Mode indéterminé
        
        # Détecter les scènes
        scenes = self.analyzer.detect_scenes()
        
        # Ajouter les scènes comme segments
        for start_frame, end_frame in scenes:
            start_time = start_frame / self.fps
            end_time = end_frame / self.fps
            self.data_manager.add_segment(
                start_time,
                end_time,
                f"Scène {len(self.data_manager.get_segments()) + 1}"
            )
        
        # Recharger les segments
        self.load_segments()
        
        self.progress_bar.setVisible(False)
        logger.debug(f"Détection des scènes terminée : {len(scenes)} scènes trouvées")
    
    def add_marker(self):
        """Ajoute un marqueur à la position actuelle"""
        if not self.data_manager:
            return
            
        current_time = self.current_frame / self.fps
        
        # Demander le nom du marqueur
        name, ok = QInputDialog.getText(
            self,
            "Ajouter un marqueur",
            "Nom du marqueur :"
        )
        
        if ok and name:
            self.data_manager.add_marker(current_time, name)
            logger.debug(f"Marqueur ajouté : {name} à {self.format_time(current_time)}")
    
    def cut_segment(self):
        """Marque un point de découpe"""
        if not self.data_manager:
            return
            
        current_time = self.current_frame / self.fps
        
        # Si c'est le premier point de découpe
        if not hasattr(self, 'cut_start_time'):
            self.cut_start_time = current_time
            self.cut_btn.setText("✂️ Fin Découpe")
            logger.debug(f"Début de découpe à {self.format_time(current_time)}")
        else:
            # C'est le point de fin
            if current_time > self.cut_start_time:
                name, ok = QInputDialog.getText(
                    self,
                    "Nommer le segment",
                    "Nom du segment :"
                )
                
                if ok:
                    self.data_manager.add_segment(
                        self.cut_start_time,
                        current_time,
                        name or None
                    )
                    logger.debug(f"Segment ajouté : {self.format_time(self.cut_start_time)} - {self.format_time(current_time)}")
            
            # Réinitialiser
            delattr(self, 'cut_start_time')
            self.cut_btn.setText("✂️ Découper")
            self.load_segments()
    
    def load_segments(self):
        """Charge les segments dans la table"""
        if not self.data_manager:
            return
            
        segments = self.data_manager.get_segments()
        self.segments_table.setRowCount(len(segments))
        
        for i, segment in enumerate(segments):
            # Nom
            self.segments_table.setItem(
                i, 0,
                QTableWidgetItem(segment['name'])
            )
            
            # Début
            self.segments_table.setItem(
                i, 1,
                QTableWidgetItem(self.format_time(segment['start']))
            )
            
            # Fin
            self.segments_table.setItem(
                i, 2,
                QTableWidgetItem(self.format_time(segment['end']))
            )
            
            # Boutons d'action
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            preview_btn = QPushButton("👁️")
            preview_btn.clicked.connect(lambda x, s=i: self.preview_segment(s))
            actions_layout.addWidget(preview_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.clicked.connect(lambda x, s=i: self.delete_segment(s))
            actions_layout.addWidget(delete_btn)
            
            self.segments_table.setCellWidget(i, 4, actions_widget)
        
        self.segments_table.resizeColumnsToContents()
    
    def preview_segment(self, segment_index):
        """Prévisualise un segment"""
        if not self.data_manager:
            return
            
        segments = self.data_manager.get_segments()
        if 0 <= segment_index < len(segments):
            segment = segments[segment_index]
            start_frame = int(segment['start'] * self.fps)
            self.current_frame = start_frame
            self.time_slider.setValue(start_frame)
            self.show_frame(start_frame)
    
    def delete_segment(self, segment_index):
        """Supprime un segment"""
        if not self.data_manager:
            return
            
        reply = QMessageBox.question(
            self,
            "Supprimer le segment",
            "Êtes-vous sûr de vouloir supprimer ce segment ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.data_manager.remove_segment(segment_index)
            self.load_segments()
            logger.debug(f"Segment {segment_index} supprimé")
    
    def save_video(self):
        """Sauvegarde la vidéo éditée"""
        if not self.data_manager or not self.video_path:
            return
            
        segments = self.data_manager.get_segments()
        if not segments:
            QMessageBox.warning(
                self,
                "Erreur",
                "Aucun segment à sauvegarder"
            )
            return
            
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Sauvegarder la vidéo",
            "",
            "Vidéo MP4 (*.mp4)"
        )
        
        if output_file:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, len(segments))
            self.progress_bar.setValue(0)
            
            try:
                # Créer un dossier temporaire pour les segments
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Extraire chaque segment
                    segment_files = []
                    video = VideoFileClip(self.video_path)
                    
                    for i, segment in enumerate(segments):
                        start_time = segment['start']
                        end_time = segment['end']
                        
                        # Extraire le segment
                        segment_clip = video.subclip(start_time, end_time)
                        segment_file = os.path.join(temp_dir, f"segment_{i}.mp4")
                        segment_clip.write_videofile(
                            segment_file,
                            codec='libx264',
                            audio_codec='aac'
                        )
                        segment_files.append(segment_file)
                        
                        self.progress_bar.setValue(i + 1)
                    
                    # Concaténer tous les segments
                    final_clip = VideoFileClip(segment_files[0])
                    clips = [VideoFileClip(f) for f in segment_files[1:]]
                    final_clip = final_clip.concatenate_videoclips(clips)
                    
                    # Sauvegarder la vidéo finale
                    final_clip.write_videofile(
                        output_file,
                        codec='libx264',
                        audio_codec='aac'
                    )
                    
                    # Fermer tous les clips
                    final_clip.close()
                    for clip in clips:
                        clip.close()
                    video.close()
                
                QMessageBox.information(
                    self,
                    "Succès",
                    "Vidéo sauvegardée avec succès !"
                )
                logger.debug(f"Vidéo sauvegardée : {output_file}")
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Erreur lors de la sauvegarde : {str(e)}"
                )
                logger.error(f"Erreur lors de la sauvegarde : {str(e)}")
            
            finally:
                self.progress_bar.setVisible(False)
    
    def show_frame(self, frame_num):
        """Affiche une frame spécifique"""
        if self.cap is None:
            return
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()
        if ret:
            # Convertir la frame en QPixmap
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(image)
            
            # Redimensionner pour la prévisualisation
            scaled_pixmap = pixmap.scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview.setPixmap(scaled_pixmap)
            
            # Mettre à jour la timeline
            self.timeline.set_current_frame(frame_num)
            
            # Mettre à jour la forme d'onde
            self.update_waveform_position(frame_num)
            
            # Mettre à jour le temps
            current_time = frame_num / self.fps
            total_time = self.cap.get(cv2.CAP_PROP_FRAME_COUNT) / self.fps
            self.time_label.setText(
                f"{self.format_time(current_time)} / {self.format_time(total_time)}"
            )
    
    def format_time(self, seconds):
        """Formate un temps en secondes en MM:SS"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def toggle_play(self):
        """Démarre ou arrête la lecture"""
        if self.playing:
            self.play_timer.stop()
            self.play_btn.setText("▶️ Lecture")
        else:
            self.play_timer.start(int(1000 / self.fps))
            self.play_btn.setText("⏸️ Pause")
        self.playing = not self.playing
    
    def next_frame(self):
        """Passe à la frame suivante"""
        if self.cap is None:
            return
        
        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if current_frame < total_frames - 1:
            self.show_frame(current_frame + 1)
        else:
            self.play_timer.stop()
            self.playing = False
            self.play_btn.setText("▶️ Lecture")
    
    def prev_frame(self):
        """Revient à la frame précédente"""
        if self.cap is None:
            return
        
        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        if current_frame > 0:
            self.show_frame(current_frame - 1)
    
    def on_timeline_position_changed(self, frame):
        """Appelé quand la position dans la timeline change"""
        self.show_frame(frame)
    
    def start_cut(self):
        """Commence une découpe"""
        if not self.cap:
            return
        
        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        self.timeline.start_segment(current_frame)
        
        # Ajouter une ligne dans le tableau
        row = self.segments_table.rowCount()
        self.segments_table.insertRow(row)
        
        # Calculer le timestamp
        start_time = current_frame / self.fps
        
        # Ajouter les informations
        status_item = QTableWidgetItem("🔴 En cours")
        status_item.setBackground(QColor("#ffebee"))  # Rouge très clair
        self.segments_table.setItem(row, 0, status_item)
        self.segments_table.setItem(row, 1, QTableWidgetItem(self.format_time(start_time)))
        self.segments_table.setItem(row, 2, QTableWidgetItem("--:--"))
        self.segments_table.setItem(row, 3, QTableWidgetItem("--:--"))
        
        # Désactiver les boutons pendant la découpe
        self.start_cut_btn.setEnabled(False)
        self.end_cut_btn.setEnabled(True)
        self.cancel_cut_btn.setEnabled(True)
        self.export_btn.setEnabled(False)

    def end_cut(self):
        """Termine une découpe"""
        if not self.cap:
            return
        
        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        segment = self.timeline.end_segment(current_frame)
        
        if segment:
            row = self.segments_table.rowCount() - 1
            
            # Calculer les timestamps
            start_time = segment.start_frame / self.fps
            end_time = segment.end_frame / self.fps
            duration = end_time - start_time
            
            # Mettre à jour les informations
            status_item = QTableWidgetItem("✅ Terminé")
            status_item.setBackground(QColor("#e8f5e9"))  # Vert très clair
            self.segments_table.setItem(row, 0, status_item)
            self.segments_table.setItem(row, 2, QTableWidgetItem(self.format_time(end_time)))
            self.segments_table.setItem(row, 3, QTableWidgetItem(self.format_time(duration)))
            
            # Ajouter le bouton de suppression
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setToolTip("Supprimer le segment")
            delete_btn.clicked.connect(lambda: self.delete_segment(row))
            actions_layout.addWidget(delete_btn)
            
            self.segments_table.setCellWidget(row, 4, actions_widget)
            
            # Réactiver les boutons
            self.start_cut_btn.setEnabled(True)
            self.end_cut_btn.setEnabled(False)
            self.cancel_cut_btn.setEnabled(False)
            self.export_btn.setEnabled(True)
    
    def cancel_cut(self):
        """Annule la découpe en cours"""
        self.timeline.cancel_current_segment()
        
        # Supprimer la dernière ligne du tableau
        row = self.segments_table.rowCount() - 1
        if row >= 0:
            self.segments_table.removeRow(row)
        
        # Réactiver les boutons
        self.start_cut_btn.setEnabled(True)
        self.end_cut_btn.setEnabled(False)
        self.cancel_cut_btn.setEnabled(False)
        self.export_btn.setEnabled(self.segments_table.rowCount() > 0)
    
    def export_segments(self):
        """Exporte les segments en fichiers vidéo séparés en utilisant ffmpeg"""
        if not self.video_path or self.segments_table.rowCount() == 0:
            return
        
        try:
            # Désactiver les contrôles pendant l'export
            self.setEnabled(False)
            QApplication.processEvents()
            
            # Obtenir le dossier et le nom de la vidéo
            video_dir = os.path.dirname(self.video_path)
            video_name = os.path.splitext(os.path.basename(self.video_path))[0]
            
            # Exporter chaque segment
            for i, segment in enumerate(self.timeline.get_segments()):
                # Calculer les temps
                start_time = segment.start_frame / self.fps
                duration = (segment.end_frame - segment.start_frame) / self.fps
                
                # Nom du fichier de sortie
                output_path = os.path.join(video_dir, f"{video_name}_{i+1}.mp4")
                
                # Commande ffmpeg pour extraire le segment
                command = [
                    "ffmpeg", "-y",
                    "-i", self.video_path,
                    "-ss", str(start_time),
                    "-t", str(duration),
                    "-c", "copy",  # Copie sans réencodage pour la vitesse
                    output_path
                ]
                
                # Exécuter ffmpeg
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                process.wait()
                
                if process.returncode != 0:
                    raise Exception(f"Erreur ffmpeg : {process.stderr.read().decode()}")
            
            # Afficher un message de succès
            QMessageBox.information(
                self,
                "Export terminé",
                f"Les segments ont été exportés dans :\n{video_dir}"
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export des segments : {e}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Une erreur est survenue lors de l'export :\n{str(e)}"
            )
        
        finally:
            # Réactiver les contrôles
            self.setEnabled(True)

    def delete_segment(self, row):
        """Supprime un segment"""
        self.segments_table.removeRow(row)
        self.timeline.segment_manager.remove_segment(row)
        
        # Désactiver le bouton d'export s'il n'y a plus de segments
        if self.segments_table.rowCount() == 0:
            self.export_btn.setEnabled(False)
    
    def closeEvent(self, event):
        """Appelé quand la fenêtre est fermée"""
        if self.cap is not None:
            self.cap.release()
        super().closeEvent(event)
    
    def on_segment_created(self, segment):
        """Appelé quand un segment est créé"""
        row = self.segments_table.rowCount()
        self.segments_table.insertRow(row)
        
        # Calculer les timestamps
        start_time = segment.start_frame / self.fps
        end_time = segment.end_frame / self.fps
        duration = end_time - start_time
        
        # Ajouter les informations
        status_item = QTableWidgetItem("✅ Terminé")
        status_item.setBackground(QColor("#e8f5e9"))  # Vert très clair
        self.segments_table.setItem(row, 0, status_item)
        self.segments_table.setItem(row, 1, QTableWidgetItem(self.format_time(start_time)))
        self.segments_table.setItem(row, 2, QTableWidgetItem(self.format_time(end_time)))
        self.segments_table.setItem(row, 3, QTableWidgetItem(self.format_time(duration)))
        
        # Bouton de suppression
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        delete_btn = QPushButton("🗑️")
        delete_btn.setToolTip("Supprimer le segment")
        delete_btn.clicked.connect(lambda: self.delete_segment(row))
        actions_layout.addWidget(delete_btn)
        
        self.segments_table.setCellWidget(row, 4, actions_widget)
        
        # Activer le bouton d'export s'il y a des segments
        self.export_btn.setEnabled(True)

    def on_segment_deleted(self, index):
        """Appelé quand un segment est supprimé depuis la timeline"""
        # Supprimer la ligne correspondante dans le tableau
        self.segments_table.removeRow(index)
        
        # Désactiver le bouton d'export s'il n'y a plus de segments
        if self.segments_table.rowCount() == 0:
            self.export_btn.setEnabled(False)
