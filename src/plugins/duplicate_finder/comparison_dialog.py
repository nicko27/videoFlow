"""
Dialogue de comparison de doublons - Version interface corrigée
Corrections: titre réduit, zone du bas optimisée, boutons colorés
"""

import os
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QSlider, QProgressBar, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QScreen

# Import du widget vidéo
try:
    from .video_preview_widget import VideoPreviewWidget
except ImportError:
    from video_preview_widget import VideoPreviewWidget

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.ComparisonDialog')


class ComparisonDialog(QDialog):
    """Dialogue de comparison optimisé - Version interface corrigée"""
    
    def __init__(self, file1: str, file2: str, similarity: float, parent=None):
        super().__init__(parent)
        self.file1 = file1
        self.file2 = file2
        self.similarity = similarity
        self.result = None
        
        # Arrange les files intelligemment
        self.arrange_files_by_name()
        
        self.setWindowTitle(f"Comparison de doublons - Similarité: {self.similarity:.1f}%")
        
        # OUVRE EN PLEIN ÉCRAN
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.setModal(True)
        
        self.setup_ui()
        
        # Affiche à 10% après un délai
        QTimer.singleShot(500, self.show_initial_position)
        
    def arrange_files_by_name(self):
        """Place le file sans numérotation à gauche"""
        try:
            file1_name = os.path.basename(self.file1)
            file2_name = os.path.basename(self.file2)
            
            # Patterns de numérotation/copy
            patterns = [r'\(\d+\)', r'_\d+', r' - Copy', r' - Copy', r'Copy of ', r'Copy de ']
            
            file1_has_pattern = any(re.search(pattern, file1_name) for pattern in patterns)
            file2_has_pattern = any(re.search(pattern, file2_name) for pattern in patterns)
            
            # Si seul file1 a un pattern, on inverse
            if file1_has_pattern and not file2_has_pattern:
                self.file1, self.file2 = self.file2, self.file1
            elif not file1_has_pattern and not file2_has_pattern:
                # Ordre alphabétique si aucun pattern
                if file1_name > file2_name:
                    self.file1, self.file2 = self.file2, self.file1
                    
        except Exception as e:
            logger.error(f"Error arrangement files: {e}")
        
    def setup_ui(self):
        """Configure l'interface - VERSION CORRIGÉE"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)  # RÉDUIT: 20 → 15
        layout.setSpacing(15)  # RÉDUIT: 20 → 15
        
        # INDICATEUR DE SIMILARITÉ RÉDUIT
        similarity_frame = self.create_similarity_indicator()
        layout.addWidget(similarity_frame)
        
        # Zone de comparison principale
        comparison_layout = QHBoxLayout()
        comparison_layout.setSpacing(30)
        
        # Vidéo A (gauche) - Plus large
        left_frame = self.create_video_frame("A", self.file1, "#4CAF50")
        self.left_video = left_frame[1]
        comparison_layout.addWidget(left_frame[0])
        
        # Vidéo B (droite) - Plus large
        right_frame = self.create_video_frame("B", self.file2, "#FF9800")
        self.right_video = right_frame[1]
        comparison_layout.addWidget(right_frame[0])
        
        layout.addLayout(comparison_layout)
        
        # Contrôles de navigation RÉDUITS
        nav_controls = self.create_navigation_controls()
        layout.addWidget(nav_controls)
        
        # Boutons d'action CORRIGÉS ET RÉDUITS
        action_buttons = self.create_action_buttons()
        layout.addWidget(action_buttons)
        
    def create_similarity_indicator(self):
        """Crée l'indicateur de similarité - VERSION RÉDUITE"""
        frame = QFrame()
        frame.setFixedHeight(60)  # RÉDUIT: 80 → 60
        
        # Couleur selon le niveau
        if self.similarity >= 95:
            bg_color, bar_color, text_color = "#E8F5E8", "#4CAF50", "#2E7D32"
            level = "TRÈS ÉLEVÉE"
        elif self.similarity >= 85:
            bg_color, bar_color, text_color = "#FFF8E1", "#FF9800", "#E65100"
            level = "ÉLEVÉE"
        else:
            bg_color, bar_color, text_color = "#FFEBEE", "#F44336", "#C62828"
            level = "MODÉRÉE"
            
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {bar_color};
                border-radius: 8px;
            }}
        """)  # RÉDUIT: border-radius 12 → 8
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 10, 20, 10)  # RÉDUIT: 25,15,25,15 → 20,10,20,10
        
        # Texte RÉDUIT
        similarity_text = QLabel(f"Similarité: {self.similarity:.1f}% ({level})")
        similarity_text.setFont(QFont("Arial", 16, QFont.Weight.Bold))  # RÉDUIT: 20 → 16
        similarity_text.setStyleSheet(f"color: {text_color};")
        
        # Barre de progression RÉDUITE
        progress_bar = QProgressBar()
        progress_bar.setMaximumWidth(250)  # RÉDUIT: 300 → 250
        progress_bar.setMaximumHeight(28)  # RÉDUIT: 35 → 28
        progress_bar.setValue(int(self.similarity))
        progress_bar.setTextVisible(False)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {bar_color};
                border-radius: 14px;
                background-color: #F5F5F5;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 12px;
            }}
        """)  # RÉDUIT: border-radius 17 → 14, chunk 14 → 12
        
        layout.addWidget(similarity_text)
        layout.addStretch()
        layout.addWidget(progress_bar)
        
        return frame
        
    def create_video_frame(self, label, video_path, color):
        """Crée un cadre pour une vidéo - Hauteur réduite"""
        container = QFrame()
        # HAUTEUR RÉDUITE pour plein écran
        container.setMinimumSize(600, 650)  # RÉDUIT: 700 → 650
        container.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 3px solid {color};
                border-radius: 15px;
            }}
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Titre RÉDUIT
        title = QLabel(f"VIDÉO {label}")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))  # RÉDUIT: 16 → 14
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {color}; padding: 6px;")  # RÉDUIT: 8px → 6px
        title.setMaximumHeight(35)  # RÉDUIT: 40 → 35
        layout.addWidget(title)
        
        # Widget vidéo
        video_widget = VideoPreviewWidget(video_path, f"Vidéo {label}")
        layout.addWidget(video_widget)
        
        # Bouton de sélection RÉDUIT
        select_btn = QPushButton(f"✅ CHOISIR {label}")
        select_btn.setMinimumHeight(60)  # RÉDUIT: 70 → 60
        select_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))  # RÉDUIT: 16 → 14
        select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
                transform: scale(1.02);
            }}
        """)  # RÉDUIT: padding 15px → 12px
        
        if label == "A":
            select_btn.clicked.connect(lambda: self.make_choice("keep_left"))
        else:
            select_btn.clicked.connect(lambda: self.make_choice("keep_right"))
            
        layout.addWidget(select_btn)
        
        return container, video_widget
        
    def create_navigation_controls(self):
        """Crée les contrôles de navigation - VERSION CORRIGÉE with zones time plus hautes"""
        frame = QFrame()
        frame.setMaximumHeight(110)  # AUGMENTÉ: 100 → 110 pour plus d'espace
        frame.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 2px solid #DEE2E6;
                border-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)
        
        # Titre RÉDUIT
        title = QLabel("🎹 Navigation synchronisée")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Slider with zones de time CORRIGÉES
        slider_layout = QHBoxLayout()
        
        # ZONE TEMPS DÉBUT - HAUTEUR CORRIGÉE
        self.time_label = QLabel("0:00")
        self.time_label.setFixedWidth(70)
        self.time_label.setMinimumHeight(30)  # NOUVEAU: hauteur minimale pour affichage correct
        self.time_label.setFont(QFont("Arial", 12))
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # CENTRÉ verticalement
        self.time_label.setStyleSheet("""
            QLabel {
                background-color: #FFFFFF;
                border: 1px solid #DDDDDD;
                border-radius: 5px;
                padding: 5px;
            }
        """)  # AJOUTÉ: fond et bordure pour visibilité
        
        # SLIDER AVEC HAUTEUR CORRIGÉE
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 1000)
        self.position_slider.setValue(0)
        self.position_slider.setMinimumHeight(30)  # AUGMENTÉ: 25 → 30
        self.position_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #CCCCCC;
                height: 8px;
                background: #F0F0F0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #007BFF;
                border: 1px solid #0056B3;
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: #0056B3;
            }
        """)
        self.position_slider.valueChanged.connect(self.on_slider_changed)
        
        # ZONE TEMPS FIN - HAUTEUR CORRIGÉE
        self.duration_label = QLabel("0:00")
        self.duration_label.setFixedWidth(70)
        self.duration_label.setMinimumHeight(30)  # NOUVEAU: hauteur minimale pour affichage correct
        self.duration_label.setFont(QFont("Arial", 12))
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # CENTRÉ
        self.duration_label.setStyleSheet("""
            QLabel {
                background-color: #FFFFFF;
                border: 1px solid #DDDDDD;
                border-radius: 5px;
                padding: 5px;
            }
        """)  # AJOUTÉ: fond et bordure pour visibilité
        
        slider_layout.addWidget(self.time_label)
        slider_layout.addWidget(self.position_slider)
        slider_layout.addWidget(self.duration_label)
        layout.addLayout(slider_layout)
        
        # Boutons de navigation with hauteur corrigée
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(12)
        
        for label, pos in [("⏮️", 0), ("25%", 0.25), ("50%", 0.5), ("75%", 0.75), ("⏭️", 1.0)]:
            btn = QPushButton(label)
            btn.setFixedSize(70, 35)
            btn.setFont(QFont("Arial", 12))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #007BFF;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0056B3;
                }
                QPushButton:pressed {
                    background-color: #004085;
                }
            """)  # AJOUTÉ: couleurs pour les boutons de navigation
            btn.clicked.connect(lambda checked, p=pos: self.seek_to_position(p))
            nav_layout.addWidget(btn)
        
        nav_layout.insertStretch(0)
        nav_layout.addStretch()
        layout.addLayout(nav_layout)
        
        return frame
        
    def create_action_buttons(self):
        """Crée les 5 boutons d'action - VERSION CORRIGÉE with VRAIES couleurs"""
        frame = QFrame()
        frame.setMaximumHeight(120)  # NOUVEAU: Limite la hauteur pour réduire l'espace
        # FOND BLANC AU LIEU DU GRIS DÉGUEULASSE
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 2px solid #DDDDDD;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 15, 20, 15)  # RÉDUIT: 25,20,25,20 → 20,15,20,15
        layout.setSpacing(15)  # RÉDUIT: 20 → 15
        
        # BOUTON GARDER A - VERT VRAI
        keep_a_btn = QPushButton("✅ GARDER A")
        keep_a_btn.setMinimumHeight(60)
        keep_a_btn.setMinimumWidth(160)
        keep_a_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745 !important;
                color: white !important;
                font-size: 14px;
                font-weight: bold;
                padding: 15px 20px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #218838 !important;
            }
            QPushButton:pressed {
                background-color: #1E7E34 !important;
            }
        """)
        keep_a_btn.clicked.connect(lambda: self.make_choice("keep_left"))
        
        # BOUTON GARDER B - ORANGE VRAI
        keep_b_btn = QPushButton("✅ GARDER B")
        keep_b_btn.setMinimumHeight(60)
        keep_b_btn.setMinimumWidth(160)
        keep_b_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800 !important;
                color: white !important;
                font-size: 14px;
                font-weight: bold;
                padding: 15px 20px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #F57C00 !important;
            }
            QPushButton:pressed {
                background-color: #EF6C00 !important;
            }
        """)
        keep_b_btn.clicked.connect(lambda: self.make_choice("keep_right"))
        
        # BOUTON PASSER - BLEU VRAI
        skip_btn = QPushButton("⏭️ PASSER")
        skip_btn.setMinimumHeight(60)
        skip_btn.setMinimumWidth(160)
        skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #007BFF !important;
                color: white !important;
                font-size: 14px;
                font-weight: bold;
                padding: 15px 20px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0056B3 !important;
            }
            QPushButton:pressed {
                background-color: #004085 !important;
            }
        """)
        skip_btn.clicked.connect(lambda: self.make_choice("ignore_temp"))
        
        # BOUTON IGNORER DÉFINITIVEMENT - ROUGE VRAI
        ignore_btn = QPushButton("❌ IGNORER")
        ignore_btn.setMinimumHeight(60)
        ignore_btn.setMinimumWidth(160)
        ignore_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC3545 !important;
                color: white !important;
                font-size: 14px;
                font-weight: bold;
                padding: 15px 20px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #C82333 !important;
            }
            QPushButton:pressed {
                background-color: #A71E2A !important;
            }
        """)
        ignore_btn.clicked.connect(lambda: self.make_choice("ignore_perm"))
        
        # BOUTON QUITTER - GRIS FONCÉ VRAI
        quit_btn = QPushButton("🚪 QUITTER")
        quit_btn.setMinimumHeight(60)
        quit_btn.setMinimumWidth(160)
        quit_btn.setStyleSheet("""
            QPushButton {
                background-color: #6C757D !important;
                color: white !important;
                font-size: 14px;
                font-weight: bold;
                padding: 15px 20px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #545B62 !important;
            }
            QPushButton:pressed {
                background-color: #454D55 !important;
            }
        """)
        quit_btn.clicked.connect(lambda: self.make_choice("quit"))
        
        layout.addWidget(keep_a_btn)
        layout.addWidget(keep_b_btn)
        layout.addWidget(skip_btn)
        layout.addWidget(ignore_btn)
        layout.addWidget(quit_btn)
        
        return frame
        
    def show_initial_position(self):
        """Affiche the videos à 10%"""
        try:
            self.seek_to_position(0.1)
            logger.info("Position initiale fixée à 10%")
        except Exception as e:
            logger.error(f"Error position initiale: {e}")
            
    def on_slider_changed(self, value):
        """Gère le changement de slider"""
        position = value / 1000.0
        self.sync_video_position(position)
        
    def seek_to_position(self, position):
        """Va à une position spécifique"""
        self.position_slider.setValue(int(position * 1000))
        self.sync_video_position(position)
        
    def sync_video_position(self, position):
        """Synchronise les deux vidéos"""
        try:
            self.left_video.seek_to_position(position)
            self.right_video.seek_to_position(position)
            
            # Met à jour l'affichage du time
            duration_a = getattr(self.left_video, 'duration', 0)
            duration_b = getattr(self.right_video, 'duration', 0)
            max_duration = max(duration_a, duration_b)
            
            current_time = position * max_duration
            self.update_time_display(current_time, max_duration)
            
        except Exception as e:
            logger.error(f"Error synchronisation: {e}")
            
    def update_time_display(self, current_seconds, total_seconds):
        """Met à jour l'affichage du time"""
        self.time_label.setText(self.format_time(current_seconds))
        self.duration_label.setText(self.format_time(total_seconds))
        
    def format_time(self, seconds):
        """Formate le time"""
        if seconds >= 3600:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}:{secs:02d}"
            
    def make_choice(self, choice):
        """Enregistre le choix"""
        self.result = choice
        
        # Animation rapide selon le choix AVEC COULEURS
        if choice == "keep_left":
            self.left_video.parentWidget().setStyleSheet("""
                QFrame {
                    background-color: #D4EDDA;
                    border: 4px solid #28A745;
                    border-radius: 15px;
                }
            """)
        elif choice == "keep_right":
            self.right_video.parentWidget().setStyleSheet("""
                QFrame {
                    background-color: #FFF3E0;
                    border: 4px solid #FF9800;
                    border-radius: 15px;
                }
            """)
        elif choice == "ignore_temp":
            # Animation bleue pour passer
            self.left_video.parentWidget().setStyleSheet("""
                QFrame {
                    background-color: #CCE5FF;
                    border: 4px solid #007BFF;
                    border-radius: 15px;
                }
            """)
            self.right_video.parentWidget().setStyleSheet("""
                QFrame {
                    background-color: #CCE5FF;
                    border: 4px solid #007BFF;
                    border-radius: 15px;
                }
            """)
        elif choice == "ignore_perm":
            # Animation rouge pour ignorer
            self.left_video.parentWidget().setStyleSheet("""
                QFrame {
                    background-color: #F8D7DA;
                    border: 4px solid #DC3545;
                    border-radius: 15px;
                }
            """)
            self.right_video.parentWidget().setStyleSheet("""
                QFrame {
                    background-color: #F8D7DA;
                    border: 4px solid #DC3545;
                    border-radius: 15px;
                }
            """)
        elif choice == "quit":
            # Quitte immédiatement sans animation
            self.reject()
            return
        
        # Délai plus court pour les autres actions
        QTimer.singleShot(200, self.accept)
        
    def closeEvent(self, event):
        """Nettoie les ressources"""
        try:
            self.left_video.cleanup()
            self.right_video.cleanup()
        except Exception as e:
            logger.error(f"Error nettoyage: {e}")
        super().closeEvent(event)