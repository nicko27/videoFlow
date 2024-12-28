"""Widget de frise temporelle pour le plugin Video Editor"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QAction, QLinearGradient, QPolygon
from .segment_manager import SegmentManager, VideoSegment

class Timeline(QWidget):
    """Frise temporelle pour la vidéo"""
    positionChanged = pyqtSignal(int)  # Frame sélectionnée
    segmentCreated = pyqtSignal(VideoSegment)
    segmentDeleted = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.segment_manager = SegmentManager()
        self.total_frames = 0
        self.current_frame = 0
        self.hover_frame = -1
        self.dragging = False
        self.setup_context_menu()
        
        # Style
        self.setMinimumHeight(80)
        self.setMaximumHeight(80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)  # Pour détecter le survol
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
    
    def setup_context_menu(self):
        """Configure le menu contextuel"""
        self.context_menu = QMenu(self)
        self.delete_action = QAction("Supprimer le segment", self)
        self.delete_action.triggered.connect(self.delete_selected_segment)
        self.context_menu.addAction(self.delete_action)
    
    def set_duration(self, total_frames):
        """Définit la durée totale de la vidéo"""
        self.total_frames = total_frames
        self.update()
    
    def set_current_frame(self, frame):
        """Définit la frame actuelle"""
        self.current_frame = min(max(0, frame), self.total_frames)
        self.update()
    
    def frame_to_x(self, frame):
        """Convertit un numéro de frame en position X"""
        if self.total_frames == 0:
            return 0
        return int((frame / self.total_frames) * self.width())
    
    def x_to_frame(self, x):
        """Convertit une position X en numéro de frame"""
        if self.width() == 0:
            return 0
        return int((x / self.width()) * self.total_frames)
    
    def paintEvent(self, event):
        """Dessine la frise"""
        if self.total_frames == 0:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fond
        painter.fillRect(self.rect(), QColor("#1a1a1a"))
        
        # Graduations
        self.draw_graduations(painter)
        
        # Segments
        self.draw_segments(painter)
        
        # Position actuelle
        self.draw_current_position(painter)
        
        # Position survolée
        if self.hover_frame >= 0:
            self.draw_hover_position(painter)
    
    def draw_graduations(self, painter):
        """Dessine les graduations"""
        painter.setPen(QPen(QColor("#3d3d3d"), 1))
        
        # Graduations principales (minutes)
        fps = 30  # À adapter selon la vidéo
        frames_per_minute = fps * 60
        for frame in range(0, self.total_frames, frames_per_minute):
            x = self.frame_to_x(frame)
            painter.drawLine(x, 0, x, self.height())
        
        # Graduations secondaires (10 secondes)
        frames_per_ten_seconds = fps * 10
        painter.setPen(QPen(QColor("#2d2d2d"), 1))
        for frame in range(0, self.total_frames, frames_per_ten_seconds):
            x = self.frame_to_x(frame)
            painter.drawLine(x, self.height() // 2, x, self.height())
    
    def draw_segments(self, painter):
        """Dessine les segments"""
        # Segments complets
        for segment in self.segment_manager.get_all_segments():
            x1 = self.frame_to_x(segment.start_frame)
            x2 = self.frame_to_x(segment.end_frame)
            
            # Fond du segment
            gradient = QLinearGradient(x1, 0, x2, 0)
            color = QColor(segment.color)
            gradient.setColorAt(0, color)
            color.setAlpha(100)
            gradient.setColorAt(1, color)
            painter.fillRect(x1, 0, x2 - x1, self.height(), gradient)
            
            # Bordures
            painter.setPen(QPen(QColor(segment.color), 2))
            painter.drawLine(x1, 0, x1, self.height())
            painter.drawLine(x2, 0, x2, self.height())
        
        # Segment en cours
        current = self.segment_manager.get_current_segment()
        if current:
            x1 = self.frame_to_x(current.start_frame)
            painter.setPen(QPen(QColor(current.color), 2, Qt.PenStyle.DashLine))
            painter.drawLine(x1, 0, x1, self.height())
    
    def draw_current_position(self, painter):
        """Dessine la position actuelle"""
        x = self.frame_to_x(self.current_frame)
        
        # Ligne de position
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(x, 0, x, self.height())
        
        # Marqueur triangulaire
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(Qt.PenStyle.NoPen)
        triangle = QPolygon([
            QPoint(x - 8, 0),
            QPoint(x + 8, 0),
            QPoint(x, 8)
        ])
        painter.drawPolygon(triangle)
    
    def draw_hover_position(self, painter):
        """Dessine la position survolée"""
        x = self.frame_to_x(self.hover_frame)
        painter.setPen(QPen(QColor("#666666"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(x, 0, x, self.height())
    
    def mousePressEvent(self, event):
        """Gère le clic sur la frise"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            frame = self.x_to_frame(event.pos().x())
            self.current_frame = min(max(0, frame), self.total_frames)
            self.positionChanged.emit(self.current_frame)
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            # Vérifier si on clique sur un segment
            frame = self.x_to_frame(event.pos().x())
            for i, segment in enumerate(self.segment_manager.get_all_segments()):
                if segment.start_frame <= frame <= segment.end_frame:
                    self.show_segment_context_menu(i, event.globalPos())
                    break
    
    def mouseMoveEvent(self, event):
        """Gère le déplacement de la souris"""
        frame = self.x_to_frame(event.pos().x())
        self.hover_frame = min(max(0, frame), self.total_frames)
        
        if self.dragging:
            self.current_frame = self.hover_frame
            self.positionChanged.emit(self.current_frame)
        
        self.update()
    
    def mouseReleaseEvent(self, event):
        """Gère le relâchement du clic"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
    
    def show_segment_context_menu(self, segment_index, pos):
        """Affiche le menu contextuel pour un segment"""
        self.context_menu.segment_index = segment_index
        self.context_menu.exec(pos)
    
    def delete_selected_segment(self):
        """Supprime le segment sélectionné"""
        if hasattr(self.context_menu, 'segment_index'):
            index = self.context_menu.segment_index
            self.segment_manager.remove_segment(index)
            self.update()
            self.segmentDeleted.emit(index)
    
    def start_segment(self, frame):
        """Commence un nouveau segment"""
        segment = self.segment_manager.start_segment(frame)
        self.update()
        return segment
    
    def end_segment(self, frame):
        """Termine le segment en cours"""
        segment = self.segment_manager.end_segment(frame)
        if segment:
            self.update()
            self.segmentCreated.emit(segment)
        return segment
    
    def cancel_current_segment(self):
        """Annule le segment en cours"""
        self.segment_manager.cancel_current_segment()
        self.update()
    
    def get_segments(self):
        """Retourne tous les segments"""
        return self.segment_manager.get_all_segments()
    
    def clear_segments(self):
        """Efface tous les segments"""
        self.segment_manager.clear()
        self.update()
