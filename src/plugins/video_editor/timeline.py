from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.Timeline')

class Segment:
    """Représente un segment de la timeline"""
    def __init__(self, start_frame, end_frame=None):
        self.start_frame = start_frame
        self.end_frame = end_frame

class Timeline(QWidget):
    """Widget de timeline pour l'éditeur vidéo"""
    
    # Signaux
    position_changed = pyqtSignal(int)  # Position du curseur changée
    segment_created = pyqtSignal(object)  # Nouveau segment créé
    segment_deleted = pyqtSignal(int)  # Segment supprimé (index)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration
        self.setMinimumHeight(50)
        self.setMouseTracking(True)
        
        # État
        self.total_frames = 0
        self.current_frame = 0
        self.segments = []
        self.current_segment = None
        self.markers = {}  # frame -> emoji
        self._updating = False  # Pour éviter les boucles infinies
        
        # Style
        self.colors = {
            'background': QColor(40, 40, 40),
            'timeline': QColor(100, 100, 100),
            'cursor': QColor(255, 255, 255),
            'segment': QColor(0, 120, 215, 128),
            'segment_border': QColor(0, 120, 215),
            'marker': QColor(255, 255, 255)
        }
    
    def set_total_frames(self, frames):
        """Définit le nombre total de frames"""
        self.total_frames = frames
        self.update()
    
    def set_current_frame(self, frame):
        """Définit la frame courante"""
        if self._updating or not (0 <= frame <= self.total_frames):
            return
            
        try:
            self._updating = True
            self.current_frame = frame
            self.update()
            self.position_changed.emit(frame)
        finally:
            self._updating = False
    
    def add_marker(self, frame, emoji):
        """Ajoute un marqueur à la position spécifiée"""
        self.markers[frame] = emoji
        self.update()
    
    def remove_marker(self, frame):
        """Supprime un marqueur"""
        if frame in self.markers:
            del self.markers[frame]
            self.update()
    
    def clear_markers(self):
        """Supprime tous les marqueurs"""
        self.markers.clear()
        self.update()
    
    def start_segment(self, frame):
        """Commence un nouveau segment"""
        self.current_segment = Segment(frame)
        self.update()
    
    def end_segment(self, frame):
        """Termine le segment en cours"""
        if self.current_segment and frame > self.current_segment.start_frame:
            self.current_segment.end_frame = frame
            self.segments.append(self.current_segment)
            segment = self.current_segment
            self.current_segment = None
            self.segment_created.emit(segment)
            self.update()
            return segment
        return None
    
    def cancel_current_segment(self):
        """Annule le segment en cours"""
        self.current_segment = None
        self.update()
    
    def remove_segment(self, index):
        """Supprime un segment"""
        if 0 <= index < len(self.segments):
            self.segments.pop(index)
            self.segment_deleted.emit(index)
            self.update()
    
    def clear_segments(self):
        """Supprime tous les segments"""
        self.segments.clear()
        self.current_segment = None
        self.update()
    
    def get_segments(self):
        """Retourne la liste des segments"""
        return self.segments
    
    def mousePressEvent(self, event):
        """Gestion du clic souris"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Calculer la frame correspondante
            frame = self._pixel_to_frame(event.position().x())
            self.set_current_frame(frame)
    
    def mouseMoveEvent(self, event):
        """Gestion du mouvement souris"""
        if event.buttons() & Qt.MouseButton.LeftButton:
            frame = self._pixel_to_frame(event.position().x())
            self.set_current_frame(frame)
    
    def _pixel_to_frame(self, x):
        """Convertit une position en pixels en numéro de frame"""
        if self.total_frames == 0:
            return 0
        return int((x / self.width()) * self.total_frames)
    
    def _frame_to_pixel(self, frame):
        """Convertit un numéro de frame en position en pixels"""
        if self.total_frames == 0:
            return 0
        return int((frame / self.total_frames) * self.width())
    
    def paintEvent(self, event):
        """Dessine la timeline"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fond
        painter.fillRect(self.rect(), self.colors['background'])
        
        # Timeline
        y = self.height() // 2
        painter.setPen(self.colors['timeline'])
        painter.drawLine(0, y, self.width(), y)
        
        # Segments
        for segment in self.segments:
            self._draw_segment(painter, segment)
        
        # Segment en cours
        if self.current_segment:
            self._draw_segment(painter, self.current_segment)
        
        # Marqueurs
        for frame, emoji in self.markers.items():
            x = self._frame_to_pixel(frame)
            painter.setPen(self.colors['marker'])
            painter.drawText(x - 10, 15, 20, 20, Qt.AlignmentFlag.AlignCenter, emoji)
        
        # Curseur
        cursor_x = self._frame_to_pixel(self.current_frame)
        painter.setPen(QPen(self.colors['cursor'], 2))
        painter.drawLine(cursor_x, 0, cursor_x, self.height())
    
    def _draw_segment(self, painter, segment):
        """Dessine un segment"""
        if not segment or not hasattr(segment, 'start_frame'):
            return
            
        x1 = self._frame_to_pixel(segment.start_frame)
        x2 = self._frame_to_pixel(segment.end_frame if segment.end_frame is not None else self.current_frame)
        
        # Rectangle du segment
        painter.fillRect(
            x1, 0,
            x2 - x1, self.height(),
            self.colors['segment']
        )
        
        # Bordure du segment
        painter.setPen(self.colors['segment_border'])
        painter.drawRect(
            x1, 0,
            x2 - x1, self.height() - 1
        )
