"""
Widgets de progression modernes - Version avec TEXTE NOIR VISIBLE
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame, QScrollArea
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor


class ModernProgressWidget(QWidget):
    """Widget de progression moderne avec statistiques"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.start_time = None
        self.setup_ui()
        
    def setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # En-tête avec titre et statut
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))  # PLUS PETIT
        self.title_label.setStyleSheet("color: black; font-weight: bold;")
        
        self.status_label = QLabel("En attente...")
        self.status_label.setFont(QFont("Arial", 10))
        self.status_label.setStyleSheet("color: black; font-weight: bold;")
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        
        layout.addLayout(header_layout)
        
        # Barre de progression moderne
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("0/0")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #BDC3C7;
                border-radius: 15px;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
                color: black;
                background-color: #ECF0F1;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #27AE60, stop:1 #2ECC71);
                border-radius: 13px;
                margin: 1px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Informations détaillées
        details_layout = QHBoxLayout()
        
        self.time_label = QLabel("Temps: --:--")
        self.time_label.setFont(QFont("Arial", 9))
        self.time_label.setStyleSheet("color: black; font-weight: bold;")
        
        self.speed_label = QLabel("Vitesse: --")
        self.speed_label.setFont(QFont("Arial", 9))
        self.speed_label.setStyleSheet("color: black; font-weight: bold;")
        
        details_layout.addWidget(self.time_label)
        details_layout.addStretch()
        details_layout.addWidget(self.speed_label)
        
        layout.addLayout(details_layout)
        
    def update_progress(self, current, maximum, custom_text=None):
        """Met à jour la progression"""
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(current)
        
        if custom_text:
            self.progress_bar.setFormat(custom_text)
        else:
            self.progress_bar.setFormat(f"{current:,}/{maximum:,}")
            
    def set_status(self, status, color="black"):
        """Change le statut avec couleur"""
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 10px;")
        
    def set_time_remaining(self, seconds):
        """Met à jour le temps restant"""
        if seconds > 0:
            if seconds < 60:
                self.time_label.setText(f"Restant: {int(seconds)}s")
            elif seconds < 3600:
                minutes = int(seconds // 60)
                secs = int(seconds % 60)
                self.time_label.setText(f"Restant: {minutes}:{secs:02d}")
            else:
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                self.time_label.setText(f"Restant: {hours}h{minutes:02d}")
        else:
            self.time_label.setText("Temps: --:--")
            
    def set_speed(self, items_per_second):
        """Met à jour la vitesse"""
        if items_per_second > 0:
            if items_per_second >= 1000:
                self.speed_label.setText(f"Vitesse: {items_per_second/1000:.1f}k/s")
            elif items_per_second >= 10:
                self.speed_label.setText(f"Vitesse: {items_per_second:.0f}/s")
            elif items_per_second >= 1:
                self.speed_label.setText(f"Vitesse: {items_per_second:.1f}/s")
            else:
                time_per_item = 1 / items_per_second
                self.speed_label.setText(f"Vitesse: {time_per_item:.1f}s/item")
        else:
            self.speed_label.setText("Vitesse: --")


class FileListWidget(QWidget):
    """Widget de liste de fichiers - TEXTE NOIR GARANTI"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.files = []
        self.file_items = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # En-tête PLUS PETIT
        header_layout = QHBoxLayout()
        
        title = QLabel("📁 Fichiers vidéo")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))  # PLUS PETIT
        title.setStyleSheet("color: black; font-weight: bold; background-color: white; padding: 3px;")
        
        self.file_count_label = QLabel("0 fichier")
        self.file_count_label.setFont(QFont("Arial", 10))  # PLUS PETIT
        self.file_count_label.setStyleSheet("color: black; font-weight: bold; background-color: white; padding: 3px;")
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.file_count_label)
        
        layout.addLayout(header_layout)
        
        # Zone scrollable
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(200)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: white;
                border: 1px solid #CCCCCC;
            }
        """)
        
        # Widget conteneur
        self.files_widget = QWidget()
        self.files_widget.setStyleSheet("background-color: white;")
        
        self.files_layout = QVBoxLayout(self.files_widget)
        self.files_layout.setContentsMargins(5, 5, 5, 5)
        self.files_layout.setSpacing(5)  # PLUS D'ESPACE : 3 → 5px
        
        # Message par défaut
        self.empty_label = QLabel("Aucun fichier ajouté")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setFont(QFont("Arial", 12))
        self.empty_label.setStyleSheet("color: black; background-color: #F0F0F0; padding: 20px; border: 1px dashed #CCCCCC;")
        self.files_layout.addWidget(self.empty_label)
        self.files_layout.addStretch()
        
        self.scroll_area.setWidget(self.files_widget)
        layout.addWidget(self.scroll_area)
        
    def add_files(self, file_paths):
        """Ajoute des fichiers"""
        new_count = 0
        for file_path in file_paths:
            if file_path not in self.files:
                self.files.append(file_path)
                item_widget = self.create_file_item(file_path)
                self.file_items[file_path] = item_widget
                new_count += 1
                
        if new_count > 0 and self.empty_label.isVisible():
            self.empty_label.hide()
            
        self.update_file_count()
        self.files_widget.updateGeometry()
        self.update()
        
        return new_count
        
    def create_file_item(self, file_path):
        """Crée un item de fichier avec TEXTE NOIR FORCÉ"""
        import os
        
        # Frame avec bordure visible - HAUTEUR PLUS GÉNÉREUSE
        item_frame = QFrame()
        item_frame.setMinimumHeight(70)  # PLUS HAUT : 50 → 70px
        item_frame.setMaximumHeight(70)  # PLUS HAUT : 50 → 70px
        item_frame.setStyleSheet("""
            QFrame {
                background-color: #F8F8F8;
                border: 1px solid #DDDDDD;
                margin: 2px;
                border-radius: 4px;
            }
            QFrame:hover {
                background-color: #EEEEEE;
            }
        """)
        
        # Layout horizontal avec PLUS DE PADDING
        layout = QHBoxLayout(item_frame)
        layout.setContentsMargins(12, 10, 12, 10)  # PLUS DE PADDING : 8,5 → 12,10
        layout.setSpacing(12)  # PLUS D'ESPACE : 8 → 12
        
        # NOM DU FICHIER - NOIR FORCÉ avec PLUS DE PLACE
        filename = os.path.basename(file_path)
        if len(filename) > 40:
            filename = filename[:37] + "..."
            
        name_label = QLabel(filename)
        name_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))  # PLUS GRAND : 10 → 11
        name_label.setMinimumHeight(30)  # HAUTEUR MINIMALE POUR LE TEXTE
        # FORCE la couleur noire avec setPalette
        palette = name_label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))  # Noir pur
        name_label.setPalette(palette)
        name_label.setStyleSheet("color: black; background-color: transparent; padding: 5px;")  # PADDING AJOUTÉ
        name_label.setToolTip(file_path)
        
        # TAILLE - NOIR FORCÉ avec PLUS DE PLACE
        try:
            size = os.path.getsize(file_path)
            size_text = self.format_file_size(size)
        except:
            size_text = "Erreur"
            
        size_label = QLabel(size_text)
        size_label.setFont(QFont("Arial", 10))  # PLUS GRAND : 9 → 10
        size_label.setFixedWidth(80)  # PLUS LARGE : 70 → 80
        size_label.setMinimumHeight(30)  # HAUTEUR MINIMALE
        palette = size_label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        size_label.setPalette(palette)
        size_label.setStyleSheet("color: black; background-color: transparent; padding: 5px;")  # PADDING AJOUTÉ
        size_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)  # CENTRÉ VERTICALEMENT
        
        # STATUT - NOIR FORCÉ avec PLUS DE PLACE
        status_label = QLabel("⏳ À analyser")
        status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))  # PLUS GRAND : 9 → 10
        status_label.setFixedWidth(120)  # PLUS LARGE : 100 → 120
        status_label.setMinimumHeight(30)  # HAUTEUR MINIMALE
        palette = status_label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        status_label.setPalette(palette)
        status_label.setStyleSheet("color: black; background-color: transparent; padding: 5px;")  # PADDING AJOUTÉ
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)  # CENTRÉ
        
        # Ajoute au layout
        layout.addWidget(name_label, 1)
        layout.addWidget(size_label, 0)
        layout.addWidget(status_label, 0)
        
        # Stockage références
        item_frame.file_path = file_path
        item_frame.status_label = status_label
        item_frame.name_label = name_label
        item_frame.size_label = size_label
        
        # Insertion avant le stretch
        insert_position = self.files_layout.count() - 1
        self.files_layout.insertWidget(insert_position, item_frame)
        
        return item_frame
        
    def update_file_status(self, file_path, status):
        """Met à jour le statut avec couleur noire forcée"""
        if file_path in self.file_items:
            item_widget = self.file_items[file_path]
            if hasattr(item_widget, 'status_label'):
                item_widget.status_label.setText(status)
                
                # FORCE la couleur noire avec palette
                palette = item_widget.status_label.palette()
                palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
                item_widget.status_label.setPalette(palette)
                
                # Style selon statut mais TOUJOURS noir
                if "✅" in status or "cache" in status.lower() or "analysé" in status.lower():
                    item_widget.status_label.setStyleSheet("color: black; background-color: #D4FFDA; border: 1px solid #4CAF50; padding: 2px; border-radius: 2px;")
                elif "❌" in status or "échec" in status.lower():
                    item_widget.status_label.setStyleSheet("color: black; background-color: #FFD4D4; border: 1px solid #F44336; padding: 2px; border-radius: 2px;")
                elif "🔄" in status or "cours" in status.lower():
                    item_widget.status_label.setStyleSheet("color: black; background-color: #D4E6FF; border: 1px solid #2196F3; padding: 2px; border-radius: 2px;")
                elif "🗑️" in status or "supprimé" in status.lower():
                    item_widget.status_label.setStyleSheet("color: black; background-color: #E0E0E0; border: 1px solid #9E9E9E; padding: 2px; border-radius: 2px;")
                elif "💾" in status:
                    item_widget.status_label.setStyleSheet("color: black; background-color: #D4F4FF; border: 1px solid #00BCD4; padding: 2px; border-radius: 2px;")
                else:
                    item_widget.status_label.setStyleSheet("color: black; background-color: #FFF4D4; border: 1px solid #FF9800; padding: 2px; border-radius: 2px;")
                
                item_widget.status_label.update()
                item_widget.update()
                return True
        
        return False
                    
    def clear_files(self):
        """Vide la liste des fichiers"""
        self.files.clear()
        self.file_items.clear()
        
        # Supprime tous les items sauf le label vide
        items_to_remove = []
        for i in range(self.files_layout.count()):
            item = self.files_layout.itemAt(i)
            if item and item.widget() and item.widget() != self.empty_label:
                items_to_remove.append(item.widget())
        
        for widget in items_to_remove:
            self.files_layout.removeWidget(widget)
            widget.deleteLater()
                
        self.empty_label.show()
        self.update_file_count()
        
    def update_file_count(self):
        """Met à jour le compteur"""
        count = len(self.files)
        if count == 0:
            self.file_count_label.setText("Aucun fichier")
        elif count == 1:
            self.file_count_label.setText("1 fichier")
        else:
            self.file_count_label.setText(f"{count} fichiers")
            
    def get_files(self):
        """Retourne la liste des fichiers"""
        return self.files.copy()
        
    def format_file_size(self, size_bytes):
        """Formate la taille de fichier"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


class StatusIndicator(QFrame):
    """Indicateur de statut - TITRE PLUS PETIT"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_status = "ready"
        self.setup_ui()
        
    def setup_ui(self):
        """Configure l'indicateur"""
        self.setMinimumHeight(50)  # PLUS PETIT
        self.setStyleSheet("""
            QFrame {
                background-color: #E3F2FD;
                border: 2px solid #2196F3;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 8)  # PLUS PETIT
        
        # Icône plus petite
        self.icon_label = QLabel("🎯")
        self.icon_label.setFont(QFont("Arial", 20))  # PLUS PETIT
        
        # Texte plus petit
        self.status_label = QLabel("Prêt à analyser")
        self.status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))  # PLUS PETIT
        self.status_label.setStyleSheet("color: black; font-weight: bold;")
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.status_label)
        layout.addStretch()
        
    def update_status(self, icon, text, color="black", bg_color="#E3F2FD", border_color="#2196F3"):
        """Met à jour le statut"""
        self.current_status = {
            'icon': icon,
            'text': text,
            'color': color,
            'bg_color': bg_color,
            'border_color': border_color
        }
        
        self.icon_label.setText(icon)
        self.status_label.setText(text)
        
        # FORCE la couleur noire
        palette = self.status_label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        self.status_label.setPalette(palette)
        self.status_label.setStyleSheet("color: black; font-weight: bold;")
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        
        self.update()
        self.repaint()