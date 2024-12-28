"""Module pour l'affichage de la forme d'onde audio"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen
import numpy as np
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.Waveform')

class WaveformWidget(QWidget):
    """Widget d'affichage de la forme d'onde audio"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.waveform_data = None
        self.current_position = 0
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        self.setMinimumHeight(60)
        self.setMaximumHeight(60)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
    
    def set_waveform_data(self, audio_data):
        """Définit les données de la forme d'onde"""
        if audio_data is None or len(audio_data) == 0:
            self.waveform_data = None
            return
        
        # Normaliser les données audio
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            self.waveform_data = audio_data / max_val
        else:
            self.waveform_data = audio_data
        
        self.update()
    
    def set_position(self, position):
        """Définit la position actuelle dans la forme d'onde"""
        self.current_position = position
        self.update()
    
    def paintEvent(self, event):
        """Dessine la forme d'onde"""
        if self.waveform_data is None:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fond
        painter.fillRect(self.rect(), QColor("#1a1a1a"))
        
        # Forme d'onde
        width = self.width()
        height = self.height()
        center_y = height // 2
        
        # Réduire les données pour correspondre à la largeur
        samples_per_pixel = len(self.waveform_data) // width
        if samples_per_pixel < 1:
            samples_per_pixel = 1
        
        points_pos = []  # Points au-dessus de la ligne centrale
        points_neg = []  # Points en-dessous de la ligne centrale
        
        for x in range(width):
            start_idx = x * samples_per_pixel
            end_idx = start_idx + samples_per_pixel
            if end_idx > len(self.waveform_data):
                break
            
            chunk = self.waveform_data[start_idx:end_idx]
            max_val = np.max(chunk)
            min_val = np.min(chunk)
            
            # Calculer les positions Y
            y_pos = center_y - int(max_val * center_y)
            y_neg = center_y - int(min_val * center_y)
            
            points_pos.append((x, y_pos))
            points_neg.append((x, y_neg))
        
        # Dessiner la forme d'onde
        painter.setPen(QPen(QColor("#4a9eff"), 1))
        
        # Dessiner la partie positive
        for i in range(len(points_pos) - 1):
            x1, y1 = points_pos[i]
            x2, y2 = points_pos[i + 1]
            painter.drawLine(x1, y1, x2, y2)
        
        # Dessiner la partie négative
        for i in range(len(points_neg) - 1):
            x1, y1 = points_neg[i]
            x2, y2 = points_neg[i + 1]
            painter.drawLine(x1, y1, x2, y2)
        
        # Dessiner la position actuelle
        if 0 <= self.current_position <= 1:
            x = int(self.current_position * width)
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.drawLine(x, 0, x, height)
