"""Widgets personnalisés pour le plugin Video Editor"""

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                           QPushButton, QSlider, QStyle, QStyleOption)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient

class WaveformWidget(QWidget):
    """Widget amélioré pour afficher la forme d'onde audio"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.waveform = None
        self.setMinimumHeight(50)
        self.setMaximumHeight(100)
        self.gradient = self._create_gradient()
    
    def _create_gradient(self):
        """Crée un dégradé pour la forme d'onde"""
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(0, 255, 127))
        gradient.setColorAt(0.5, QColor(0, 255, 255))
        gradient.setColorAt(1, QColor(0, 127, 255))
        return gradient
    
    def set_waveform(self, waveform):
        """Définit les données de la forme d'onde"""
        self.waveform = waveform
        self.update()
    
    def paintEvent(self, event):
        """Dessine la forme d'onde avec un style amélioré"""
        if self.waveform is None:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fond
        painter.fillRect(self.rect(), QColor(26, 26, 26))
        
        # Grille
        painter.setPen(QPen(QColor(40, 40, 40), 1))
        step = self.height() / 4
        for i in range(1, 4):
            y = i * step
            painter.drawLine(0, y, self.width(), y)
        
        # Forme d'onde avec dégradé
        painter.setPen(Qt.PenStyle.NoPen)
        step = len(self.waveform) / self.width()
        path_top = []
        path_bottom = []
        center_y = self.height() / 2
        
        for x in range(self.width()):
            idx = int(x * step)
            if idx < len(self.waveform):
                value = self.waveform[idx]
                y_top = center_y - (value * center_y)
                y_bottom = center_y + (value * center_y)
                path_top.append((x, y_top))
                path_bottom.append((x, y_bottom))
        
        # Dessiner le remplissage avec dégradé
        for i in range(len(path_top) - 1):
            x1, y1 = path_top[i]
            x2, y2 = path_top[i + 1]
            painter.setBrush(self.gradient)
            painter.drawRect(x1, y1, 1, path_bottom[i][1] - y1)

class TimelineWidget(QWidget):
    """Widget personnalisé pour la timeline"""
    positionChanged = pyqtSignal(float)  # Position en pourcentage (0-1)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(50)
        self.position = 0  # Position actuelle (0-1)
        self.markers = []  # Liste des marqueurs [(position, couleur), ...]
        self.segments = []  # Liste des segments [(début, fin, couleur), ...]
    
    def set_position(self, pos):
        """Définit la position actuelle"""
        self.position = max(0, min(1, pos))
        self.update()
    
    def set_markers(self, markers):
        """Définit les marqueurs"""
        self.markers = markers
        self.update()
    
    def set_segments(self, segments):
        """Définit les segments"""
        self.segments = segments
        self.update()
    
    def mousePressEvent(self, event):
        """Gère le clic sur la timeline"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos().x() / self.width()
            self.position = max(0, min(1, pos))
            self.positionChanged.emit(self.position)
            self.update()
    
    def paintEvent(self, event):
        """Dessine la timeline"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fond
        painter.fillRect(self.rect(), QColor(26, 26, 26))
        
        # Segments
        for start, end, color in self.segments:
            x1 = int(start * self.width())
            x2 = int(end * self.width())
            painter.fillRect(x1, 0, x2 - x1, self.height(), QColor(color))
        
        # Marqueurs
        for pos, color in self.markers:
            x = int(pos * self.width())
            painter.setPen(QPen(QColor(color), 2))
            painter.drawLine(x, 0, x, self.height())
        
        # Position actuelle
        x = int(self.position * self.width())
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawLine(x, 0, x, self.height())

class VideoControls(QWidget):
    """Widget pour les contrôles de lecture vidéo"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Boutons de contrôle
        self.play_btn = QPushButton("▶️")
        self.play_btn.setFixedSize(QSize(40, 40))
        layout.addWidget(self.play_btn)
        
        self.prev_frame_btn = QPushButton("⏮️")
        self.prev_frame_btn.setFixedSize(QSize(40, 40))
        layout.addWidget(self.prev_frame_btn)
        
        self.next_frame_btn = QPushButton("⏭️")
        self.next_frame_btn.setFixedSize(QSize(40, 40))
        layout.addWidget(self.next_frame_btn)
        
        # Slider de position
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        layout.addWidget(self.position_slider)
        
        # Label de temps
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setFixedWidth(100)
        layout.addWidget(self.time_label)
