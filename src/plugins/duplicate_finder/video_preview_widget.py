"""
Widget d'aperçu vidéo optimisé pour la comparaison de doublons
"""

import os
import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QFont
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.VideoPreview')


class VideoPreviewWidget(QWidget):
    """Widget d'aperçu vidéo simple et efficace"""
    
    # Signal émis quand une frame est chargée
    frame_loaded = pyqtSignal(int)
    
    def __init__(self, video_path, side_name="Video", parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.side_name = side_name
        self.cap = None
        self.total_frames = 0
        self.fps = 30.0
        self.duration = 0.0
        self.current_frame = 0
        
        self.setup_ui()
        self.load_video_info()
        
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Zone d'aperçu principale PLUS GRANDE
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(350, 280)  # Plus grand : 350x280 au lieu de 400x300
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 2px solid #DDDDDD;
                border-radius: 8px;
                background-color: #000000;
            }
        """)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setText("Chargement...")
        layout.addWidget(self.preview_label)
        
        # Informations compactes PLUS GRANDES
        info_frame = self.create_info_section()
        layout.addWidget(info_frame)
        
    def create_info_section(self):
        """Crée la section d'informations"""
        frame = QFrame()
        frame.setMinimumHeight(65)  # Plus grand pour police 12pt
        frame.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 1px solid #E9ECEF;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)  # Plus d'espace
        layout.setSpacing(4)
        
        # Nom de fichier - POLICE 12PT MINIMUM
        filename = os.path.basename(self.video_path)
        if len(filename) > 60:  # Plus de caractères affichés
            filename = filename[:57] + "..."
            
        self.filename_label = QLabel(filename)
        self.filename_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))  # 12pt minimum
        self.filename_label.setStyleSheet("color: #495057;")
        self.filename_label.setWordWrap(True)  # Permet le retour à la ligne
        layout.addWidget(self.filename_label)
        
        # Infos techniques - POLICE 12PT MINIMUM
        self.info_label = QLabel("Analyse en cours...")
        self.info_label.setFont(QFont("Arial", 12))  # 12pt minimum
        self.info_label.setStyleSheet("color: #6C757D;")
        layout.addWidget(self.info_label)
        
        return frame
        
    def load_video_info(self):
        """Charge les informations de la vidéo et affiche une frame à 10%"""
        try:
            # Informations fichier
            file_size = os.path.getsize(self.video_path)
            size_text = self.format_file_size(file_size)
            
            # Informations vidéo avec OpenCV
            cv2.setLogLevel(0)
            self.cap = cv2.VideoCapture(self.video_path)
            
            if self.cap.isOpened():
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
                self.duration = self.total_frames / self.fps if self.fps > 0 else 0
                
                # Met à jour les infos
                duration_text = self.format_duration(self.duration)
                self.info_label.setText(f"{size_text} • {duration_text}")
                
                # AFFICHE UNE FRAME À 10% DÈS LE DÉPART
                frame_at_10_percent = int(self.total_frames * 0.1) if self.total_frames > 0 else 0
                self.show_frame(frame_at_10_percent)
                
            else:
                self.info_label.setText(f"{size_text} • Erreur lecture")
                self.preview_label.setText("❌ Impossible d'ouvrir")
                
            cv2.setLogLevel(1)
            
        except Exception as e:
            logger.error(f"Erreur chargement {self.video_path}: {e}")
            self.info_label.setText("Erreur")
            self.preview_label.setText("❌ Erreur de chargement")
    
    def show_frame(self, frame_number):
        """Affiche une frame spécifique"""
        if not self.cap or not self.cap.isOpened() or self.total_frames == 0:
            return
            
        try:
            # Limite le numéro de frame
            frame_number = max(0, min(frame_number, self.total_frames - 1))
            self.current_frame = frame_number
            
            # Lit la frame
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = self.cap.read()
            
            if ret and frame is not None:
                # Convertit en QPixmap
                pixmap = self.frame_to_pixmap(frame)
                if pixmap:
                    self.preview_label.setPixmap(pixmap)
                    self.frame_loaded.emit(frame_number)
                else:
                    self.preview_label.setText("Erreur conversion")
            else:
                self.preview_label.setText(f"Frame {frame_number} indisponible")
                
        except Exception as e:
            logger.error(f"Erreur affichage frame {frame_number}: {e}")
            self.preview_label.setText("Erreur affichage")
    
    def seek_to_position(self, position):
        """Va à une position relative (0.0 à 1.0)"""
        if self.total_frames > 0:
            frame_number = int(position * (self.total_frames - 1))
            self.show_frame(frame_number)
    
    def frame_to_pixmap(self, frame):
        """Convertit une frame OpenCV en QPixmap redimensionné"""
        try:
            # Redimensionne en gardant les proportions
            label_size = self.preview_label.size()
            target_width = label_size.width() - 4  # Marge pour bordure
            target_height = label_size.height() - 4
            
            height, width = frame.shape[:2]
            aspect_ratio = width / height
            
            # Calcule les nouvelles dimensions
            if aspect_ratio > target_width / target_height:
                new_width = target_width
                new_height = int(target_width / aspect_ratio)
            else:
                new_height = target_height
                new_width = int(target_height * aspect_ratio)
            
            # Redimensionne
            resized_frame = cv2.resize(frame, (new_width, new_height))
            
            # Convertit BGR vers RGB
            rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            
            # Crée QImage
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            return QPixmap.fromImage(qt_image)
            
        except Exception as e:
            logger.error(f"Erreur conversion frame: {e}")
            return None
    
    def format_file_size(self, size_bytes):
        """Formate la taille de fichier"""
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.0f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.0f}MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"
    
    def format_duration(self, seconds):
        """Formate la durée"""
        if seconds >= 3600:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h{minutes:02d}m"
        else:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}:{secs:02d}"
    
    def get_frame_at_percent(self, percent):
        """Retourne le numéro de frame à un pourcentage donné"""
        if self.total_frames > 0:
            return int((percent / 100.0) * (self.total_frames - 1))
        return 0
    
    def cleanup(self):
        """Libère les ressources"""
        try:
            if self.cap:
                self.cap.release()
                self.cap = None
        except Exception as e:
            logger.error(f"Erreur nettoyage {self.video_path}: {e}")
    
    def __del__(self):
        """Destructeur pour s'assurer du nettoyage"""
        self.cleanup()