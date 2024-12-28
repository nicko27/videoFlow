"""Widget de prévisualisation des frames vidéo"""

from PyQt6.QtWidgets import (QWidget, QScrollArea, QHBoxLayout, QLabel, QProgressBar,
                           QVBoxLayout, QMenu)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, QObject, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QImage, QAction
import cv2
import numpy as np
from .segment_manager import SegmentManager, VideoSegment

class ThumbnailWidget(QLabel):
    """Widget pour afficher une miniature de frame"""
    clicked = pyqtSignal(int, Qt.MouseButton)  # Modifié pour inclure le bouton
    
    def __init__(self, frame_index, parent=None):
        super().__init__(parent)
        self.frame_index = frame_index
        self.setFixedSize(QSize(160, 90))
        self.setStyleSheet("""
            QLabel {
                border: 1px solid #3d3d3d;
                background-color: #1a1a1a;
            }
            QLabel:hover {
                border: 1px solid #0078d4;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selected = False
        self.is_segment_start = False
        self.is_segment_end = False
        self.segment_color = None
    
    def set_segment_marker(self, is_start=False, is_end=False, color=None):
        """Définit les marqueurs de segment"""
        self.is_segment_start = is_start
        self.is_segment_end = is_end
        self.segment_color = color
        self.update()
    
    def paintEvent(self, event):
        """Dessine la miniature avec les marqueurs"""
        super().paintEvent(event)
        
        if self.is_segment_start or self.is_segment_end:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            if self.segment_color:
                color = QColor(self.segment_color)
            else:
                color = QColor("#0078d4")
            
            pen = QPen(color, 3)
            painter.setPen(pen)
            
            if self.is_segment_start:
                painter.drawLine(0, 0, 0, self.height())
                painter.drawLine(0, 0, 10, 0)
                painter.drawLine(0, self.height(), 10, self.height())
            
            if self.is_segment_end:
                painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
                painter.drawLine(self.width() - 11, 0, self.width() - 1, 0)
                painter.drawLine(self.width() - 11, self.height(), self.width() - 1, self.height())
    
    def mousePressEvent(self, event):
        """Gère le clic sur la miniature"""
        self.clicked.emit(self.frame_index, event.button())

class ThumbnailLoader(QObject):
    """Chargeur asynchrone de miniatures"""
    thumbnailReady = pyqtSignal(int, QPixmap)
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, video_path, frame_interval):
        super().__init__()
        self.video_path = video_path
        self.frame_interval = frame_interval
        self.running = True

    def load(self):
        """Charge les miniatures en arrière-plan"""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.finished.emit()
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count = 0
        processed = 0

        while frame_count < total_frames and self.running:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
            ret, frame = cap.read()
            if not ret:
                break

            # Créer la miniature
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            thumbnail = cv2.resize(frame_rgb, (160, 90))

            # Convertir en QPixmap
            height, width = thumbnail.shape[:2]
            bytes_per_line = 3 * width
            q_img = QImage(thumbnail.data, width, height, bytes_per_line,
                          QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)

            # Émettre la miniature
            self.thumbnailReady.emit(frame_count, pixmap)
            
            # Mettre à jour la progression
            processed += 1
            progress = int((processed / (total_frames / self.frame_interval)) * 100)
            self.progress.emit(progress)

            frame_count += self.frame_interval

        cap.release()
        self.finished.emit()

    def stop(self):
        """Arrête le chargement"""
        self.running = False

class ThumbnailStrip(QWidget):
    """Frise de prévisualisation des frames vidéo"""
    frameSelected = pyqtSignal(int)
    segmentCreated = pyqtSignal(VideoSegment)
    segmentDeleted = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.thumbnails = {}
        self.current_frame = 0
        self.frames_per_thumbnail = 60
        self.loader_thread = None
        self.loader = None
        self.segment_manager = SegmentManager()
        self.context_menu = None
        self.setup_context_menu()
    
    def setup_context_menu(self):
        """Configure le menu contextuel"""
        self.context_menu = QMenu(self)
        self.delete_action = QAction("Supprimer le segment", self)
        self.delete_action.triggered.connect(self.delete_selected_segment)
        self.context_menu.addAction(self.delete_action)
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        self.setMinimumHeight(150)
        self.setMaximumHeight(170)
        
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Zone de défilement
        scroll_container = QWidget()
        scroll_layout = QHBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(4, 4, 4, 4)
        scroll_layout.setSpacing(4)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1a1a1a;
            }
            QScrollBar:horizontal {
                height: 12px;
                background: #1a1a1a;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background: #3d3d3d;
                min-width: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #4d4d4d;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        
        # Container pour les miniatures
        self.container = QWidget()
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(4, 4, 4, 4)
        self.container_layout.setSpacing(4)
        self.container_layout.addStretch()
        
        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(2)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #1a1a1a;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
            }
        """)
        layout.addWidget(self.progress_bar)
    
    def load_video(self, video_path):
        """Charge les miniatures depuis une vidéo"""
        # Arrêter le chargeur précédent si existant
        self.stop_loader()
        
        # Nettoyer les miniatures existantes
        self.clear_thumbnails()
        
        # Créer et démarrer le nouveau chargeur
        self.loader = ThumbnailLoader(video_path, self.frames_per_thumbnail)
        self.loader_thread = QThread()
        
        self.loader.moveToThread(self.loader_thread)
        self.loader_thread.started.connect(self.loader.load)
        self.loader.thumbnailReady.connect(self.add_thumbnail)
        self.loader.progress.connect(self.progress_bar.setValue)
        self.loader.finished.connect(self.on_loading_finished)
        
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.loader_thread.start()
    
    def stop_loader(self):
        """Arrête le chargeur de miniatures"""
        if self.loader:
            self.loader.stop()
        if self.loader_thread:
            self.loader_thread.quit()
            self.loader_thread.wait()
    
    def add_thumbnail(self, frame_index, pixmap):
        """Ajoute une nouvelle miniature"""
        thumb_widget = ThumbnailWidget(frame_index)
        thumb_widget.setPixmap(pixmap)
        thumb_widget.clicked.connect(self.on_thumbnail_clicked)
        
        # Ajouter au layout dans l'ordre
        self.thumbnails[frame_index] = thumb_widget
        
        # Réorganiser les widgets
        self.reorganize_thumbnails()
        
        # Mettre à jour les marqueurs de segment
        self.update_segment_markers()
    
    def reorganize_thumbnails(self):
        """Réorganise les miniatures dans l'ordre"""
        while self.container_layout.count() > 0:
            self.container_layout.takeAt(0)
        
        for idx in sorted(self.thumbnails.keys()):
            self.container_layout.addWidget(self.thumbnails[idx])
        
        self.container_layout.addStretch()
    
    def update_segment_markers(self):
        """Met à jour les marqueurs de segment sur les miniatures"""
        # Réinitialiser tous les marqueurs
        for thumb in self.thumbnails.values():
            thumb.set_segment_marker()
        
        # Ajouter les marqueurs pour les segments complets
        for segment in self.segment_manager.get_all_segments():
            start_thumb = self.get_thumbnail_for_frame(segment.start_frame)
            if start_thumb:
                start_thumb.set_segment_marker(is_start=True, color=segment.color)
            
            end_thumb = self.get_thumbnail_for_frame(segment.end_frame)
            if end_thumb:
                end_thumb.set_segment_marker(is_end=True, color=segment.color)
        
        # Ajouter le marqueur pour le segment en cours
        current = self.segment_manager.get_current_segment()
        if current:
            start_thumb = self.get_thumbnail_for_frame(current.start_frame)
            if start_thumb:
                start_thumb.set_segment_marker(is_start=True, color=current.color)
    
    def get_thumbnail_for_frame(self, frame):
        """Trouve la miniature correspondant à une frame"""
        if not frame:
            return None
        
        # Trouver la miniature la plus proche
        thumb_frame = frame - (frame % self.frames_per_thumbnail)
        return self.thumbnails.get(thumb_frame)
    
    def on_loading_finished(self):
        """Appelé quand le chargement est terminé"""
        self.progress_bar.hide()
        self.loader_thread.quit()
        self.loader_thread.wait()
    
    def clear_thumbnails(self):
        """Supprime toutes les miniatures"""
        for thumb in self.thumbnails.values():
            self.container_layout.removeWidget(thumb)
            thumb.deleteLater()
        self.thumbnails.clear()
        
    def set_current_frame(self, frame_index):
        """Met à jour la frame sélectionnée"""
        self.current_frame = frame_index
        thumb_index = frame_index - (frame_index % self.frames_per_thumbnail)
        
        # Mettre à jour la sélection
        for idx, thumb in self.thumbnails.items():
            thumb.set_selected(idx == thumb_index)
        
        # Faire défiler jusqu'à la miniature si nécessaire
        if thumb_index in self.thumbnails:
            thumb = self.thumbnails[thumb_index]
            self.scroll_area.ensureWidgetVisible(thumb)
    
    def on_thumbnail_clicked(self, frame_index, button):
        """Gère le clic sur une miniature"""
        if button == Qt.MouseButton.LeftButton:
            self.frameSelected.emit(frame_index)
            self.set_current_frame(frame_index)
        elif button == Qt.MouseButton.RightButton:
            # Vérifier si on clique sur un segment existant
            for i, segment in enumerate(self.segment_manager.get_all_segments()):
                if segment.start_frame <= frame_index <= segment.end_frame:
                    self.show_segment_context_menu(i, QCursor.pos())
                    return
    
    def show_segment_context_menu(self, segment_index, pos):
        """Affiche le menu contextuel pour un segment"""
        self.context_menu.segment_index = segment_index
        self.context_menu.exec(pos)
    
    def delete_selected_segment(self):
        """Supprime le segment sélectionné"""
        if hasattr(self.context_menu, 'segment_index'):
            index = self.context_menu.segment_index
            self.segment_manager.remove_segment(index)
            self.update_segment_markers()
            self.segmentDeleted.emit(index)
    
    def start_segment(self, frame):
        """Commence un nouveau segment"""
        segment = self.segment_manager.start_segment(frame)
        self.update_segment_markers()
        return segment
    
    def end_segment(self, frame):
        """Termine le segment en cours"""
        segment = self.segment_manager.end_segment(frame)
        if segment:
            self.update_segment_markers()
            self.segmentCreated.emit(segment)
        return segment
    
    def cancel_current_segment(self):
        """Annule le segment en cours"""
        self.segment_manager.cancel_current_segment()
        self.update_segment_markers()
    
    def get_segments(self):
        """Retourne tous les segments"""
        return self.segment_manager.get_all_segments()
    
    def clear_segments(self):
        """Efface tous les segments"""
        self.segment_manager.clear()
        self.update_segment_markers()
