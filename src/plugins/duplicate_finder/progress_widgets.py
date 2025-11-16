"""
Widgets de progression modernes - Version with TEXTE NOIR VISIBLE
"""

import os
import numpy as np
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame,
                              QScrollArea, QPushButton, QTextEdit, QSpinBox, QDialog, QSlider,
                              QApplication, QComboBox, QListWidget, QFileDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap, QImage

try:
    from .design_system import Colors, Spacing, Typography, Styles, get_status_colors
    from .themes import get_current_theme
except ImportError:
    from design_system import Colors, Spacing, Typography, Styles, get_status_colors
    from themes import get_current_theme


class ModernProgressWidget(QWidget):
    """Widget de progression moderne with statistics"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.start_time = None
        self.setup_ui()
        
    def setup_ui(self):
        """Configure l'interface"""
        theme = get_current_theme()
        spacing = theme.get_spacing()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(spacing['padding'], spacing['padding'], spacing['padding'], spacing['padding'])
        layout.setSpacing(spacing['gap'])

        # En-tête with titre et statut
        header_layout = QHBoxLayout()

        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_MD, QFont.Weight.Bold))
        self.title_label.setStyleSheet(Styles.label(
            color=Colors.BLACK,
            font_size=Typography.FONT_MD,
            bold=True
        ))

        self.status_label = QLabel("En attente...")
        self.status_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XS))
        self.status_label.setStyleSheet(Styles.label(
            color=Colors.BLACK,
            font_size=Typography.FONT_XS,
            bold=True
        ))

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)

        layout.addLayout(header_layout)

        # Zone de progression avec stats à côté
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(spacing['gap'])

        # Barre de progression (sans texte, propre et clean)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)  # Pas de texte dans la barre
        self.progress_bar.setStyleSheet(theme.get_progress_style())
        progress_layout.addWidget(self.progress_bar, 1)

        # Stats box à côté
        stats_frame = QFrame()
        stats_frame.setMaximumWidth(120)
        stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.GRAY_50};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: {spacing['radius']}px;
                padding: {spacing['gap']}px;
            }}
        """)
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setContentsMargins(spacing['gap'], spacing['gap'], spacing['gap'], spacing['gap'])
        stats_layout.setSpacing(2)

        # Nombre actuel/total
        self.count_label = QLabel("0/0")
        self.count_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_MD, QFont.Weight.Bold))
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setStyleSheet(f"color: {Colors.PRIMARY};")
        stats_layout.addWidget(self.count_label)

        # Pourcentage
        self.percent_label = QLabel("0%")
        self.percent_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XS))
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.percent_label.setStyleSheet(f"color: {Colors.GRAY_600};")
        stats_layout.addWidget(self.percent_label)

        progress_layout.addWidget(stats_frame)
        layout.addLayout(progress_layout)

        # Information détaillées (temps et vitesse)
        details_layout = QHBoxLayout()

        self.time_label = QLabel("⏱️ --:--")
        self.time_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XXS))
        self.time_label.setStyleSheet(Styles.label(
            color=Colors.GRAY_600,
            font_size=Typography.FONT_XXS,
            bold=False
        ))

        self.speed_label = QLabel("⚡ --")
        self.speed_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XXS))
        self.speed_label.setStyleSheet(Styles.label(
            color=Colors.GRAY_600,
            font_size=Typography.FONT_XXS,
            bold=False
        ))

        details_layout.addWidget(self.time_label)
        details_layout.addStretch()
        details_layout.addWidget(self.speed_label)

        layout.addLayout(details_layout)
        
    def update_progress(self, current, maximum, custom_text=None):
        """Met à jour la progression"""
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(current)

        # Mise à jour des stats à côté
        self.count_label.setText(f"{current:,}/{maximum:,}")

        # Calcul et affichage du pourcentage
        if maximum > 0:
            percent = (current / maximum) * 100
            self.percent_label.setText(f"{percent:.0f}%")
        else:
            self.percent_label.setText("0%")
            
    def set_status(self, status, color="black"):
        """Change le statut with couleur"""
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 10px;")
        
    def set_time_remaining(self, seconds):
        """Met à jour le time remaining"""
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
            self.time_label.setText("Time: --:--")
            
    def set_speed(self, items_per_second):
        """Met à jour la speed"""
        if items_per_second > 0:
            if items_per_second >= 1000:
                self.speed_label.setText(f"Speed: {items_per_second/1000:.1f}k/s")
            elif items_per_second >= 10:
                self.speed_label.setText(f"Speed: {items_per_second:.0f}/s")
            elif items_per_second >= 1:
                self.speed_label.setText(f"Speed: {items_per_second:.1f}/s")
            else:
                time_per_item = 1 / items_per_second
                self.speed_label.setText(f"Speed: {time_per_item:.1f}s/item")
        else:
            self.speed_label.setText("Speed: --")


class FileListWidget(QWidget):
    """Widget de liste de files - TEXTE NOIR GARANTI"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.files = []
        self.file_items = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.MD)

        # En-tête
        header_layout = QHBoxLayout()

        title = QLabel("📁 Fichiers vidéo")
        title.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_MD, QFont.Weight.Bold))
        title.setStyleSheet(Styles.label(
            color=Colors.BLACK,
            font_size=Typography.FONT_MD,
            bold=True,
            bg_color=Colors.WHITE
        ) + f"padding: {Spacing.XXS}px;")

        self.file_count_label = QLabel("0 file")
        self.file_count_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XS))
        self.file_count_label.setStyleSheet(Styles.label(
            color=Colors.BLACK,
            font_size=Typography.FONT_XS,
            bold=True,
            bg_color=Colors.WHITE
        ) + f"padding: {Spacing.XXS}px;")

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.file_count_label)

        layout.addLayout(header_layout)

        # Zone scrollable
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(200)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Colors.WHITE};
                border: 1px solid {Colors.BORDER_DEFAULT};
            }}
        """)

        # Widget conteneur
        self.files_widget = QWidget()
        self.files_widget.setStyleSheet(f"background-color: {Colors.WHITE};")

        self.files_layout = QVBoxLayout(self.files_widget)
        self.files_layout.setContentsMargins(Spacing.XS, Spacing.XS, Spacing.XS, Spacing.XS)
        self.files_layout.setSpacing(Spacing.XS)

        # Message par défaut
        self.empty_label = QLabel("Aucun file ajouté")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_MD))
        self.empty_label.setStyleSheet(f"""
            color: {Colors.BLACK};
            background-color: {Colors.GRAY_100};
            padding: {Spacing.XXL}px;
            border: 1px dashed {Colors.BORDER_DEFAULT};
        """)
        self.files_layout.addWidget(self.empty_label)
        self.files_layout.addStretch()

        self.scroll_area.setWidget(self.files_widget)
        layout.addWidget(self.scroll_area)
        
    def add_files(self, file_paths):
        """Adds des files"""
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
        """Crée un item de file with TEXTE NOIR FORCÉ"""
        import os

        # Frame with bordure visible - HAUTEUR PLUS GÉNÉREUSE
        item_frame = QFrame()
        item_frame.setMinimumHeight(Spacing.FILE_ITEM_HEIGHT)
        item_frame.setMaximumHeight(Spacing.FILE_ITEM_HEIGHT)
        item_frame.setStyleSheet(Styles.file_item())

        # Layout horizontal with PLUS DE PADDING
        layout = QHBoxLayout(item_frame)
        layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        layout.setSpacing(Spacing.LG)
        
        # NOM DU FICHIER - NOIR FORCÉ with PLUS DE PLACE
        filename = os.path.basename(file_path)
        if len(filename) > 40:
            filename = filename[:37] + "..."

        name_label = QLabel(filename)
        name_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_SM, QFont.Weight.Bold))
        name_label.setMinimumHeight(Spacing.INPUT_HEIGHT)
        # FORCE la couleur noire with setPalette
        palette = name_label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        name_label.setPalette(palette)
        name_label.setStyleSheet(f"color: {Colors.BLACK}; background-color: transparent; padding: {Spacing.XS}px;")
        name_label.setToolTip(file_path)

        # TAILLE - NOIR FORCÉ with PLUS DE PLACE
        try:
            size = os.path.getsize(file_path)
            size_text = self.format_file_size(size)
        except:
            size_text = "Error"

        size_label = QLabel(size_text)
        size_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XS))
        size_label.setFixedWidth(80)
        size_label.setMinimumHeight(Spacing.INPUT_HEIGHT)
        palette = size_label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        size_label.setPalette(palette)
        size_label.setStyleSheet(f"color: {Colors.BLACK}; background-color: transparent; padding: {Spacing.XS}px;")
        size_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # STATUT - NOIR FORCÉ with PLUS DE PLACE
        status_label = QLabel("⏳ À analyze")
        status_label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XS, QFont.Weight.Bold))
        status_label.setFixedWidth(120)
        status_label.setMinimumHeight(Spacing.INPUT_HEIGHT)
        palette = status_label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        status_label.setPalette(palette)
        status_label.setStyleSheet(f"color: {Colors.BLACK}; background-color: transparent; padding: {Spacing.XS}px;")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        
        # Adds au layout
        layout.addWidget(name_label, 1)
        layout.addWidget(size_label, 0)
        layout.addWidget(status_label, 0)
        
        # Stockage références
        item_frame.file_path = file_path
        item_frame.status_label = status_label
        item_frame.name_label = name_label
        item_frame.size_label = size_label

        # Insertion avant le stretch - with safety check
        try:
            if self.files_layout is not None:
                insert_position = self.files_layout.count() - 1
                self.files_layout.insertWidget(insert_position, item_frame)
        except RuntimeError as e:
            # Layout has been deleted, widget cleanup in progress
            logger.warning(f"Cannot insert file item, layout deleted: {e}")
            return None

        return item_frame
        
    def update_file_status(self, file_path, status):
        """Met à jour le statut with couleur noire forcée"""
        if file_path in self.file_items:
            item_widget = self.file_items[file_path]
            if hasattr(item_widget, 'status_label'):
                item_widget.status_label.setText(status)

                # FORCE la couleur noire with palette
                palette = item_widget.status_label.palette()
                palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
                item_widget.status_label.setPalette(palette)

                # Style selon statut mais TOUJOURS noir - using design system
                if "✅" in status or "cache" in status.lower() or "analysé" in status.lower():
                    colors = get_status_colors('success')
                    item_widget.status_label.setStyleSheet(Styles.status_badge(
                        bg_color=colors['bg'],
                        border_color=colors['border']
                    ))
                elif "❌" in status or "failed" in status.lower():
                    colors = get_status_colors('error')
                    item_widget.status_label.setStyleSheet(Styles.status_badge(
                        bg_color=colors['bg'],
                        border_color=colors['border']
                    ))
                elif "🔄" in status or "cours" in status.lower():
                    colors = get_status_colors('processing')
                    item_widget.status_label.setStyleSheet(Styles.status_badge(
                        bg_color=colors['bg'],
                        border_color=colors['border']
                    ))
                elif "🗑️" in status or "supprimé" in status.lower():
                    colors = get_status_colors('deleted')
                    item_widget.status_label.setStyleSheet(Styles.status_badge(
                        bg_color=colors['bg'],
                        border_color=colors['border']
                    ))
                elif "💾" in status:
                    colors = get_status_colors('cached')
                    item_widget.status_label.setStyleSheet(Styles.status_badge(
                        bg_color=colors['bg'],
                        border_color=colors['border']
                    ))
                else:
                    colors = get_status_colors('warning')
                    item_widget.status_label.setStyleSheet(Styles.status_badge(
                        bg_color=colors['bg'],
                        border_color=colors['border']
                    ))

                item_widget.status_label.update()
                item_widget.update()
                return True

        return False
                    
    def clear_files(self):
        """Vide the list des files"""
        self.files.clear()
        self.file_items.clear()
        
        # Removes tous les items sauf le label vide
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
            self.file_count_label.setText("Aucun file")
        elif count == 1:
            self.file_count_label.setText("1 file")
        else:
            self.file_count_label.setText(f"{count} files")
            
    def get_files(self):
        """Returns the list des files"""
        return self.files.copy()
        
    def format_file_size(self, size_bytes):
        """Formate la size de file"""
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
        self.status_label = QLabel("Ready à analyze")
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


class StatsCounter(QFrame):
    """Widget to display real-time statistics counters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.duplicates_count = 0
        self.subsequences_count = 0
        self.setup_ui()

    def setup_ui(self):
        """Configure the stats counter UI."""
        self.setMinimumHeight(60)
        self.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(20)

        # Title
        title_label = QLabel("📊 Results:")
        title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #424242;")
        layout.addWidget(title_label)

        # Duplicates counter
        dup_container = QWidget()
        dup_layout = QVBoxLayout(dup_container)
        dup_layout.setContentsMargins(0, 0, 0, 0)
        dup_layout.setSpacing(2)

        dup_label = QLabel("Duplicates")
        dup_label.setFont(QFont("Arial", 8))
        dup_label.setStyleSheet("color: #757575;")

        self.dup_value = QLabel("0")
        self.dup_value.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.dup_value.setStyleSheet("color: #FF6B6B;")

        dup_layout.addWidget(dup_label)
        dup_layout.addWidget(self.dup_value)
        layout.addWidget(dup_container)

        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        separator1.setStyleSheet("color: #E0E0E0;")
        layout.addWidget(separator1)

        # Subsequences counter
        subseq_container = QWidget()
        subseq_layout = QVBoxLayout(subseq_container)
        subseq_layout.setContentsMargins(0, 0, 0, 0)
        subseq_layout.setSpacing(2)

        subseq_label = QLabel("Subsequences")
        subseq_label.setFont(QFont("Arial", 8))
        subseq_label.setStyleSheet("color: #757575;")

        self.subseq_value = QLabel("0")
        self.subseq_value.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.subseq_value.setStyleSheet("color: #4ECDC4;")

        subseq_layout.addWidget(subseq_label)
        subseq_layout.addWidget(self.subseq_value)
        layout.addWidget(subseq_container)

        layout.addStretch()

    def update_duplicates(self, count: int):
        """Update duplicates counter."""
        self.duplicates_count = count
        self.dup_value.setText(str(count))

    def update_subsequences(self, count: int):
        """Update subsequences counter."""
        self.subsequences_count = count
        self.subseq_value.setText(str(count))

    def reset(self):
        """Reset all counters to zero."""
        self.update_duplicates(0)
        self.update_subsequences(0)


class HashDebugger(QFrame):
    """Widget for manual hash calculation and debugging."""

    def __init__(self, video_hasher=None, parent=None):
        super().__init__(parent)
        self.video_hasher = video_hasher
        self.selected_files = []
        self.hash_results = {}
        self.setup_ui()

    def setup_ui(self):
        """Configure the hash debugger UI."""
        self.setStyleSheet("""
            QFrame {
                background-color: #FFF8DC;
                border: 2px solid #FFD700;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Title
        title_label = QLabel("🔬 Hash Debugging Tool")
        title_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #B8860B; border: none; padding: 0;")
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel("Manually calculate and compare video hashes for debugging")
        desc_label.setFont(QFont("Arial", 9))
        desc_label.setStyleSheet("color: #666; border: none; padding: 0;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # File selection area
        file_selection_layout = QHBoxLayout()

        self.select_btn = QPushButton("📁 Select Video(s)")
        self.select_btn.setMinimumHeight(32)
        self.select_btn.clicked.connect(self._select_files)
        self.select_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        file_selection_layout.addWidget(self.select_btn)

        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.setMinimumHeight(32)
        self.clear_btn.clicked.connect(self._clear_files)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        file_selection_layout.addWidget(self.clear_btn)

        file_selection_layout.addStretch()
        layout.addLayout(file_selection_layout)

        # Selected files display
        self.files_text = QTextEdit()
        self.files_text.setReadOnly(True)
        self.files_text.setMaximumHeight(80)
        self.files_text.setPlaceholderText("No files selected")
        self.files_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #DDD;
                border-radius: 4px;
                padding: 6px;
                font-family: monospace;
                font-size: 9pt;
            }
        """)
        layout.addWidget(self.files_text)

        # Calculate button
        self.calculate_btn = QPushButton("⚡ Calculate Hashes")
        self.calculate_btn.setMinimumHeight(36)
        self.calculate_btn.clicked.connect(self._calculate_hashes)
        self.calculate_btn.setEnabled(False)
        self.calculate_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover:enabled {
                background-color: #0b7dda;
            }
            QPushButton:disabled {
                background-color: #CCC;
            }
        """)
        layout.addWidget(self.calculate_btn)

        # Results display
        results_label = QLabel("Results:")
        results_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        results_label.setStyleSheet("color: #333; border: none; padding: 0;")
        layout.addWidget(results_label)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMinimumHeight(200)
        self.results_text.setPlaceholderText("Hash results will appear here")
        self.results_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #DDD;
                border-radius: 4px;
                padding: 8px;
                font-family: monospace;
                font-size: 9pt;
            }
        """)
        layout.addWidget(self.results_text)

    def set_video_hasher(self, video_hasher):
        """Set the video hasher instance."""
        self.video_hasher = video_hasher

    def _select_files(self):
        """Open file dialog to select video files."""
        from PyQt6.QtWidgets import QFileDialog

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Video Files (1-2 videos)",
            "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm);;All Files (*.*)"
        )

        if files:
            # Limit to 2 files for comparison
            self.selected_files = files[:2]
            self._update_files_display()
            self.calculate_btn.setEnabled(True)

    def _clear_files(self):
        """Clear selected files and results."""
        self.selected_files = []
        self.hash_results = {}
        self.files_text.clear()
        self.results_text.clear()
        self.calculate_btn.setEnabled(False)

    def _update_files_display(self):
        """Update the files display."""
        if self.selected_files:
            text = "\n".join([f"{i+1}. {os.path.basename(f)}" for i, f in enumerate(self.selected_files)])
            self.files_text.setPlainText(text)
        else:
            self.files_text.clear()

    def _calculate_hashes(self):
        """Calculate hashes for selected files."""
        if not self.video_hasher:
            self.results_text.setPlainText("ERROR: No video hasher available")
            return

        if not self.selected_files:
            return

        from src.core.logger import Logger
        logger = Logger.get_logger('DuplicateFinder.HashDebugger')

        self.results_text.clear()
        self.hash_results = {}
        results = []

        results.append("=" * 70)
        results.append("HASH CALCULATION RESULTS")
        results.append("=" * 70)
        results.append(f"Hash Method: {self.video_hasher.method}")
        results.append("")

        # Calculate hash for each file
        for i, file_path in enumerate(self.selected_files):
            results.append(f"\n{'─' * 70}")
            results.append(f"File {i+1}: {os.path.basename(file_path)}")
            results.append(f"Path: {file_path}")
            results.append(f"{'─' * 70}")

            try:
                # Calculate hash
                import time
                start_time = time.time()
                video_hash, duration = self.video_hasher.compute_video_hash(file_path)
                calc_time = time.time() - start_time

                if video_hash is not None:
                    self.hash_results[file_path] = video_hash

                    results.append(f"✓ Hash calculated successfully")
                    results.append(f"  Duration: {duration:.2f}s")
                    results.append(f"  Calculation time: {calc_time:.3f}s")
                    results.append(f"  Hash shape: {video_hash.shape}")
                    results.append(f"  Hash dtype: {video_hash.dtype}")
                    results.append(f"")
                    results.append(f"  Hash values (first 10 frames):")

                    # Show first 10 frame hashes
                    for j, frame_hash in enumerate(video_hash[:10]):
                        # Convert to binary string for better visualization
                        if hasattr(frame_hash, 'flatten'):
                            flat_hash = frame_hash.flatten()
                            # Show first 64 bits
                            bits = ''.join(['1' if b else '0' for b in flat_hash[:64]])
                            results.append(f"    Frame {j:2d}: {bits[:32]} {bits[32:64]}")
                        else:
                            results.append(f"    Frame {j:2d}: {frame_hash}")
                else:
                    results.append(f"✗ Failed to calculate hash")
                    logger.error(f"Hash calculation failed for {file_path}")

            except Exception as e:
                results.append(f"✗ ERROR: {str(e)}")
                logger.error(f"Error calculating hash for {file_path}: {e}")

        # If we have 2 files, compare them
        if len(self.selected_files) == 2 and len(self.hash_results) == 2:
            results.append(f"\n{'=' * 70}")
            results.append("COMPARISON RESULTS")
            results.append(f"{'=' * 70}")

            try:
                file1, file2 = self.selected_files
                similarity = self.video_hasher.compare_videos(file1, file2)

                results.append(f"")
                results.append(f"File 1: {os.path.basename(file1)}")
                results.append(f"File 2: {os.path.basename(file2)}")
                results.append(f"")
                results.append(f"Similarity: {similarity:.2f}%")
                results.append(f"")

                if similarity >= 90:
                    results.append("🔴 VERY HIGH similarity - Likely duplicates")
                elif similarity >= 70:
                    results.append("🟡 MEDIUM similarity - Possible related content")
                else:
                    results.append("🟢 LOW similarity - Different videos")

                # Frame-by-frame comparison
                hash1 = self.hash_results[file1]
                hash2 = self.hash_results[file2]

                results.append(f"\n{'─' * 70}")
                results.append("FRAME-BY-FRAME COMPARISON (first 10 frames)")
                results.append(f"{'─' * 70}")

                min_frames = min(len(hash1), len(hash2))
                for j in range(min(10, min_frames)):
                    # Calculate hamming distance for this frame
                    frame_diff = np.sum(hash1[j] != hash2[j])
                    frame_total = hash1[j].size
                    frame_similarity = (1 - frame_diff / frame_total) * 100

                    status = "✓" if frame_similarity > 80 else "✗"
                    results.append(f"  Frame {j:2d}: {frame_similarity:5.1f}% similarity {status}")

            except Exception as e:
                results.append(f"✗ ERROR during comparison: {str(e)}")
                logger.error(f"Error comparing videos: {e}")

        results.append(f"\n{'=' * 70}")
        results.append("END OF RESULTS")
        results.append(f"{'=' * 70}")

        self.results_text.setPlainText("\n".join(results))


class FrameSelectorDialog(QDialog):
    """Dialog for visually selecting a starting frame in a video."""

    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.current_frame = 0
        self.selected_frame = 0
        self.is_playing = False
        self.cap = None
        self.total_frames = 0
        self.fps = 0

        self.setWindowTitle(f"Select Starting Frame - {os.path.basename(video_path)}")
        self.setModal(True)
        self.resize(900, 700)

        # Open video
        import cv2
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise Exception(f"Cannot open video: {video_path}")

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)

        self.setup_ui()

        # Timer for playback
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self._next_frame)

        # Load first frame
        self._go_to_frame(0)

    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Video display
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #000000;
                border: 2px solid #4682B4;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.video_label)

        # Frame info
        info_layout = QHBoxLayout()
        self.frame_label = QLabel("Frame: 0")
        self.frame_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.time_label = QLabel("Time: 0.00s")
        self.time_label.setFont(QFont("Arial", 11))
        info_layout.addWidget(self.frame_label)
        info_layout.addWidget(self.time_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Slider
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(max(0, self.total_frames - 1))
        self.frame_slider.setValue(0)
        self.frame_slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.frame_slider)

        # Control buttons
        controls_layout = QHBoxLayout()

        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setMinimumHeight(36)
        self.play_btn.clicked.connect(self._toggle_play)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)

        prev_btn = QPushButton("◀ Previous")
        prev_btn.setMinimumHeight(36)
        prev_btn.clicked.connect(self._prev_frame)
        prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #5A6268;
            }
        """)

        next_btn = QPushButton("Next ▶")
        next_btn.setMinimumHeight(36)
        next_btn.clicked.connect(self._next_frame)
        next_btn.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #5A6268;
            }
        """)

        controls_layout.addWidget(prev_btn)
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(next_btn)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Action buttons
        action_layout = QHBoxLayout()

        confirm_btn = QPushButton("✓ Confirm This Frame")
        confirm_btn.setMinimumHeight(44)
        confirm_btn.clicked.connect(self.accept)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #0056B3;
            }
        """)

        cancel_btn = QPushButton("✗ Cancel")
        cancel_btn.setMinimumHeight(44)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #C82333;
            }
        """)

        action_layout.addWidget(confirm_btn)
        action_layout.addWidget(cancel_btn)
        layout.addLayout(action_layout)

    def _go_to_frame(self, frame_num):
        """Go to specific frame and display it."""
        import cv2

        if frame_num < 0:
            frame_num = 0
        if frame_num >= self.total_frames:
            frame_num = self.total_frames - 1

        self.current_frame = frame_num
        self.selected_frame = frame_num

        # Set frame position
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()

        if ret:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Resize to fit display (keep aspect ratio)
            h, w = frame_rgb.shape[:2]
            max_w, max_h = 640, 480
            scale = min(max_w / w, max_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            frame_resized = cv2.resize(frame_rgb, (new_w, new_h))

            # Convert to QImage and QPixmap
            h, w, ch = frame_resized.shape
            bytes_per_line = ch * w
            q_img = QImage(frame_resized.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)

            self.video_label.setPixmap(pixmap)

        # Update labels
        self.frame_label.setText(f"Frame: {frame_num} / {self.total_frames}")
        time_sec = frame_num / self.fps if self.fps > 0 else 0
        self.time_label.setText(f"Time: {time_sec:.2f}s")

        # Update slider without triggering signal
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(frame_num)
        self.frame_slider.blockSignals(False)

    def _on_slider_changed(self, value):
        """Handle slider value change."""
        if not self.is_playing:
            self._go_to_frame(value)

    def _toggle_play(self):
        """Toggle play/pause."""
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_btn.setText("⏸ Pause")
            interval = int(1000 / self.fps) if self.fps > 0 else 33
            self.play_timer.start(interval)
        else:
            self.play_btn.setText("▶ Play")
            self.play_timer.stop()

    def _next_frame(self):
        """Go to next frame."""
        if self.current_frame < self.total_frames - 1:
            self._go_to_frame(self.current_frame + 1)
        else:
            # Stop at end
            if self.is_playing:
                self._toggle_play()

    def _prev_frame(self):
        """Go to previous frame."""
        if self.current_frame > 0:
            self._go_to_frame(self.current_frame - 1)

    def get_selected_frame(self):
        """Get the selected frame number."""
        return self.selected_frame

    def closeEvent(self, event):
        """Clean up when closing."""
        if self.cap:
            self.cap.release()
        event.accept()


class ResultsDialog(QDialog):
    """Dialog for displaying hash comparison results."""

    def __init__(self, results_text, parent=None):
        super().__init__(parent)
        self.results_text = results_text

        self.setWindowTitle("Hash Debugging Results")
        self.setModal(False)  # Allow interaction with main window
        self.resize(1000, 700)

        self.setup_ui()

    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Title
        title = QLabel("📊 Hash Debugging Results - Ready to Copy/Paste")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #1E3A8A; padding: 8px;")
        layout.addWidget(title)

        # Instructions
        instructions = QLabel("Select all (Ctrl+A) and copy (Ctrl+C) to share these results")
        instructions.setFont(QFont("Arial", 9))
        instructions.setStyleSheet("color: #64748B; padding: 4px;")
        layout.addWidget(instructions)

        # Results display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(False)  # Allow selection
        self.text_display.setPlainText(self.results_text)
        self.text_display.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 2px solid #3B82F6;
                border-radius: 6px;
                padding: 12px;
                font-family: 'Courier New', 'Monaco', monospace;
                font-size: 10pt;
                line-height: 1.5;
            }
        """)
        layout.addWidget(self.text_display)

        # Buttons
        button_layout = QHBoxLayout()

        copy_btn = QPushButton("📋 Copy to Clipboard")
        copy_btn.setMinimumHeight(40)
        copy_btn.clicked.connect(self._copy_to_clipboard)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)

        select_all_btn = QPushButton("✓ Select All")
        select_all_btn.setMinimumHeight(40)
        select_all_btn.clicked.connect(self.text_display.selectAll)
        select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)

        close_btn = QPushButton("✗ Close")
        close_btn.setMinimumHeight(40)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6B7280;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)

        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(copy_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

    def _copy_to_clipboard(self):
        """Copy results to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.results_text)

        # Visual feedback
        self.text_display.selectAll()


class HashDebuggerV2(QFrame):
    """Advanced widget for interactive hash debugging with frame selection."""

    def __init__(self, video_hasher=None, settings_manager=None, parent=None):
        super().__init__(parent)
        self.video_hasher = video_hasher
        self.settings_manager = settings_manager
        self.video_data = []  # List of {path, cap, total_frames, fps, start_frame}
        self.setup_ui()

    def setup_ui(self):
        """Configure the advanced hash debugger UI."""
        self.setStyleSheet("""
            QFrame {
                background-color: #F0F8FF;
                border: 2px solid #4682B4;
                border-radius: 8px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Title
        title_label = QLabel("🎬 Interactive Hash Debugger")
        title_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #1E3A8A; border: none;")
        main_layout.addWidget(title_label)

        # Description
        desc_label = QLabel("Add videos, then start the debug session. You'll visually select the starting frame for each video, and see a comparison table.")
        desc_label.setFont(QFont("Arial", 9))
        desc_label.setStyleSheet("color: #475569; border: none;")
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)

        # Video selection
        select_layout = QHBoxLayout()

        self.add_video_btn = QPushButton("➕ Add Video")
        self.add_video_btn.setMinimumHeight(36)
        self.add_video_btn.clicked.connect(self._add_video)
        self.add_video_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        select_layout.addWidget(self.add_video_btn)

        self.clear_all_btn = QPushButton("🗑️ Clear All")
        self.clear_all_btn.setMinimumHeight(36)
        self.clear_all_btn.clicked.connect(self._clear_all)
        self.clear_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
        """)
        select_layout.addWidget(self.clear_all_btn)

        select_layout.addStretch()
        main_layout.addLayout(select_layout)

        # Video list container (scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(200)
        scroll_area.setMaximumHeight(400)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                background-color: white;
            }
        """)

        self.video_list_widget = QWidget()
        self.video_list_layout = QVBoxLayout(self.video_list_widget)
        self.video_list_layout.setSpacing(12)
        self.video_list_layout.addStretch()

        scroll_area.setWidget(self.video_list_widget)
        main_layout.addWidget(scroll_area)

        # Start Debug Session button
        self.start_btn = QPushButton("🎬 Start Debug Session")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.clicked.connect(self._start_debug_session)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px 28px;
                font-weight: bold;
                font-size: 13pt;
            }
            QPushButton:hover:enabled {
                background-color: #2563EB;
            }
            QPushButton:disabled {
                background-color: #CBD5E1;
            }
        """)
        main_layout.addWidget(self.start_btn)

        # Info label
        info_label = QLabel("💡 Click the button above to start the debug session.\nYou'll select frames visually, then see results in a new window.")
        info_label.setFont(QFont("Arial", 9))
        info_label.setStyleSheet("color: #64748B; border: none; padding: 8px;")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(info_label)

    def set_video_hasher(self, video_hasher):
        """Set the video hasher instance."""
        self.video_hasher = video_hasher

    def _add_video(self):
        """Add one or more videos to the list."""
        from PyQt6.QtWidgets import QFileDialog
        import cv2

        # Get last used folder if settings_manager available
        last_folder = ""
        if self.settings_manager:
            last_folder = self.settings_manager.get_last_folder()

        # Allow multiple selection
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Video File(s) - Multiple selection allowed",
            last_folder,
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm);;All Files (*.*)"
        )

        if not file_paths:
            return

        # Save the folder of the first selected file
        if file_paths and self.settings_manager:
            folder = os.path.dirname(file_paths[0])
            self.settings_manager.save_last_folder(folder)

        # Process each selected video
        for file_path in file_paths:
            # Open video to get metadata
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                self.results_table.setPlainText(f"ERROR: Cannot open video {file_path}")
                continue

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()

            # Create video entry widget
            video_entry = self._create_video_entry(file_path, total_frames, fps)

            # Insert before stretch
            self.video_list_layout.insertWidget(
                self.video_list_layout.count() - 1,
                video_entry
            )

            # Store video data
            self.video_data.append({
                'path': file_path,
                'total_frames': total_frames,
                'fps': fps,
                'start_frame': 0,
                'widget': video_entry
            })

        self.start_btn.setEnabled(True)

    def _create_video_entry(self, file_path, total_frames, fps):
        """Create a widget for a single video entry."""
        entry_frame = QFrame()
        entry_frame.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(entry_frame)
        layout.setSpacing(8)

        # Video name
        name_label = QLabel(f"📹 {os.path.basename(file_path)}")
        name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #1E293B; border: none;")
        layout.addWidget(name_label)

        # Video info
        duration_sec = total_frames / fps if fps > 0 else 0
        info_label = QLabel(f"Total frames: {total_frames} | FPS: {fps:.2f} | Duration: {duration_sec:.2f}s")
        info_label.setFont(QFont("Arial", 8))
        info_label.setStyleSheet("color: #64748B; border: none;")
        layout.addWidget(info_label)

        # Action row
        action_layout = QHBoxLayout()

        # Status label (will be updated after frame selection)
        status_label = QLabel("⏳ Waiting for debug session...")
        status_label.setStyleSheet("color: #F59E0B; border: none; font-weight: bold;")
        action_layout.addWidget(status_label)

        action_layout.addStretch()

        # Remove button
        remove_btn = QPushButton("✖")
        remove_btn.setFixedSize(24, 24)
        remove_btn.clicked.connect(lambda: self._remove_video(file_path, entry_frame))
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
        """)
        action_layout.addWidget(remove_btn)

        layout.addLayout(action_layout)

        # Store widgets for later access
        entry_frame.status_label = status_label
        entry_frame.file_path = file_path

        return entry_frame

    def _remove_video(self, file_path, widget):
        """Remove a video from the list."""
        # Remove from data
        self.video_data = [v for v in self.video_data if v['path'] != file_path]

        # Remove widget
        self.video_list_layout.removeWidget(widget)
        widget.deleteLater()

        # Disable start button if no videos
        if not self.video_data:
            self.start_btn.setEnabled(False)

    def _clear_all(self):
        """Clear all videos."""
        # Clear all widgets
        while self.video_list_layout.count() > 1:  # Keep stretch
            item = self.video_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.video_data = []
        self.start_btn.setEnabled(False)

    def _start_debug_session(self):
        """Start the interactive debug session."""
        if not self.video_hasher:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", "No video hasher available")
            return

        if not self.video_data:
            return

        from src.core.logger import Logger
        logger = Logger.get_logger('DuplicateFinder.HashDebuggerV2')

        # Step 1: For each video, open frame selector dialog
        for idx, video in enumerate(self.video_data, 1):
            file_path = video['path']

            # Update status
            widget = video['widget']
            widget.status_label.setText(f"🎬 Selecting starting frame...")
            widget.status_label.setStyleSheet("color: #3B82F6; border: none; font-weight: bold;")
            QApplication.processEvents()  # Force UI update

            try:
                # Open frame selector dialog
                dialog = FrameSelectorDialog(file_path, self)
                result = dialog.exec()

                if result == QDialog.DialogCode.Accepted:
                    # User confirmed - save the selected frame
                    start_frame = dialog.get_selected_frame()
                    video['start_frame'] = start_frame

                    # Update status
                    widget.status_label.setText(f"✓ Frame {start_frame} selected")
                    widget.status_label.setStyleSheet("color: #10B981; border: none; font-weight: bold;")
                else:
                    # User cancelled - abort the session
                    widget.status_label.setText("✗ Session cancelled")
                    widget.status_label.setStyleSheet("color: #EF4444; border: none; font-weight: bold;")

                    # Reset all previous statuses
                    for i in range(idx - 1):
                        prev_widget = self.video_data[i]['widget']
                        prev_widget.status_label.setText("⏳ Waiting for debug session...")
                        prev_widget.status_label.setStyleSheet("color: #F59E0B; border: none; font-weight: bold;")

                    logger.info("Debug session cancelled by user")
                    return

            except Exception as e:
                logger.error(f"Error opening frame selector for {file_path}: {e}")
                widget.status_label.setText(f"✗ Error: {str(e)}")
                widget.status_label.setStyleSheet("color: #EF4444; border: none; font-weight: bold;")
                return

        # Step 2: All frames selected, now calculate hashes
        import cv2

        results = []
        results.append("=" * 100)
        results.append("HASH DEBUGGING TABLE - COPY/PASTE READY")
        results.append("=" * 100)
        results.append(f"Hash Method: {self.video_hasher.method}")
        results.append(f"Number of videos: {len(self.video_data)}")
        results.append(f"Consecutive hashes per video: 10")
        results.append("")

        all_hashes = {}

        # Calculate hashes for each video
        for idx, video in enumerate(self.video_data, 1):
            file_path = video['path']
            start_frame = video['start_frame']

            # Update status
            widget = video['widget']
            widget.status_label.setText(f"⚡ Calculating hashes...")
            widget.status_label.setStyleSheet("color: #8B5CF6; border: none; font-weight: bold;")
            QApplication.processEvents()

            results.append(f"\n{'─' * 100}")
            results.append(f"VIDEO {idx}: {os.path.basename(file_path)}")
            results.append(f"Path: {file_path}")
            results.append(f"Start frame: {start_frame}")
            results.append(f"{'─' * 100}")

            try:
                cv2.setLogLevel(0)
                cap = cv2.VideoCapture(file_path)

                if not cap.isOpened():
                    results.append("✗ ERROR: Cannot open video")
                    widget.status_label.setText("✗ Error opening video")
                    widget.status_label.setStyleSheet("color: #EF4444; border: none; font-weight: bold;")
                    continue

                # Jump to start frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

                # Calculate 10 consecutive hashes
                hashes = []
                for i in range(10):
                    ret, frame = cap.read()
                    if not ret:
                        results.append(f"✗ ERROR: Could not read frame {start_frame + i}")
                        break

                    frame_hash = self.video_hasher.compute_frame_hash(frame)
                    if frame_hash is not None:
                        hashes.append(frame_hash)
                    else:
                        results.append(f"✗ ERROR: Hash calculation failed for frame {start_frame + i}")
                        break

                cap.release()

                if len(hashes) == 10:
                    all_hashes[f"Video{idx}"] = hashes
                    results.append(f"✓ Successfully calculated 10 hashes")
                    results.append("")

                    # Display hashes in table format
                    results.append("Frame | Hash (first 64 bits)")
                    results.append("------|" + "-" * 66)

                    for i, h in enumerate(hashes):
                        frame_num = start_frame + i
                        flat_hash = h.flatten()
                        bits = ''.join(['1' if b else '0' for b in flat_hash[:64]])
                        # Format in groups of 8 for readability
                        formatted_bits = ' '.join([bits[j:j+8] for j in range(0, 64, 8)])
                        results.append(f"{frame_num:5d} | {formatted_bits}")

                    widget.status_label.setText("✓ Hashes calculated")
                    widget.status_label.setStyleSheet("color: #10B981; border: none; font-weight: bold;")
                else:
                    widget.status_label.setText("✗ Hash calculation incomplete")
                    widget.status_label.setStyleSheet("color: #EF4444; border: none; font-weight: bold;")

            except Exception as e:
                results.append(f"✗ ERROR: {str(e)}")
                logger.error(f"Error processing {file_path}: {e}")
                widget.status_label.setText(f"✗ Error: {str(e)[:30]}")
                widget.status_label.setStyleSheet("color: #EF4444; border: none; font-weight: bold;")

        # Comparison section if we have multiple videos
        if len(all_hashes) >= 2:
            results.append(f"\n{'=' * 100}")
            results.append("FRAME-BY-FRAME COMPARISON MATRIX")
            results.append(f"{'=' * 100}")

            video_names = list(all_hashes.keys())

            # Compare each pair
            for i in range(len(video_names)):
                for j in range(i + 1, len(video_names)):
                    vid1 = video_names[i]
                    vid2 = video_names[j]

                    results.append(f"\n{vid1} vs {vid2}:")
                    results.append("Frame | Similarity | Status")
                    results.append("------|------------|--------")

                    hashes1 = all_hashes[vid1]
                    hashes2 = all_hashes[vid2]

                    for k in range(min(len(hashes1), len(hashes2))):
                        # Calculate similarity for this frame
                        diff = np.sum(hashes1[k] != hashes2[k])
                        total = hashes1[k].size
                        similarity = (1 - diff / total) * 100

                        status = "MATCH" if similarity > 80 else "DIFF "
                        results.append(f"  {k:2d}  | {similarity:6.2f}%   | {status}")

                    # Overall average
                    avg_similarity = np.mean([
                        (1 - np.sum(hashes1[k] != hashes2[k]) / hashes1[k].size) * 100
                        for k in range(min(len(hashes1), len(hashes2)))
                    ])
                    results.append(f"\nAverage similarity: {avg_similarity:.2f}%")

        results.append(f"\n{'=' * 100}")
        results.append("END OF TABLE")
        results.append(f"{'=' * 100}")
        results.append("\nYou can copy/paste this entire table to share for debugging.")

        # Step 3: Open results dialog
        results_text = "\n".join(results)
        dialog = ResultsDialog(results_text, self)
        dialog.show()

        logger.info("Debug session completed successfully")

class AudioFingerprintDebugger(QFrame):
    """Widget for debugging audio fingerprinting / scene detection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene_detector = None
        self.videos = []  # List of {path: str, fingerprint: str, duration: float}
        self.setup_ui()

    def setup_ui(self):
        """Configure the audio fingerprint debugger UI."""
        self.setStyleSheet("""
            QFrame {
                background-color: #FFF7ED;
                border: 2px solid #F97316;
                border-radius: 8px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Title
        title_label = QLabel("🎵 Audio Fingerprint Debugger (Scene Detection)")
        title_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #C2410C; border: none;")
        main_layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "Test audio fingerprinting for scene detection. Add 2+ videos, "
            "extract audio fingerprints, and see similarity scores."
        )
        desc_label.setFont(QFont("Arial", 9))
        desc_label.setStyleSheet("color: #78350F; border: none;")
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)

        # Precision mode selector
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Precision Mode:")
        mode_label.setStyleSheet("border: none; color: #78350F;")
        mode_layout.addWidget(mode_label)

        self.precision_combo = QComboBox()
        self.precision_combo.addItem("🎯 Maximum (99.9%, slowest)", "maximum")
        self.precision_combo.addItem("⚖️ Balanced (99%, recommended)", "balanced")
        self.precision_combo.addItem("⚡ Fast (95%, fastest)", "fast")
        self.precision_combo.setCurrentIndex(1)  # Balanced
        self.precision_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #FDBA74;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: white;
            }
        """)
        mode_layout.addWidget(self.precision_combo)
        mode_layout.addStretch()
        main_layout.addLayout(mode_layout)

        # Video selection
        select_layout = QHBoxLayout()

        self.add_video_btn = QPushButton("➕ Add Video")
        self.add_video_btn.setMinimumHeight(36)
        self.add_video_btn.clicked.connect(self._add_video)
        self.add_video_btn.setStyleSheet("""
            QPushButton {
                background-color: #F97316;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #EA580C;
            }
        """)
        select_layout.addWidget(self.add_video_btn)

        self.clear_btn = QPushButton("🗑️ Clear All")
        self.clear_btn.setMinimumHeight(36)
        self.clear_btn.clicked.connect(self._clear_all)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
        """)
        select_layout.addWidget(self.clear_btn)

        select_layout.addStretch()
        main_layout.addLayout(select_layout)

        # Video list
        self.video_list = QListWidget()
        self.video_list.setMinimumHeight(150)
        self.video_list.setMaximumHeight(250)
        self.video_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #FDBA74;
                border-radius: 6px;
                background-color: white;
                padding: 4px;
            }
        """)
        main_layout.addWidget(self.video_list)

        # Extract fingerprints button
        self.extract_btn = QPushButton("🎵 Extract Audio Fingerprints")
        self.extract_btn.setMinimumHeight(44)
        self.extract_btn.clicked.connect(self._extract_fingerprints)
        self.extract_btn.setEnabled(False)
        self.extract_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 12pt;
            }
            QPushButton:hover:enabled {
                background-color: #1D4ED8;
            }
            QPushButton:disabled {
                background-color: #CBD5E1;
            }
        """)
        main_layout.addWidget(self.extract_btn)

        # Compare button
        self.compare_btn = QPushButton("📊 Compare Fingerprints")
        self.compare_btn.setMinimumHeight(44)
        self.compare_btn.clicked.connect(self._compare_fingerprints)
        self.compare_btn.setEnabled(False)
        self.compare_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 12pt;
            }
            QPushButton:hover:enabled {
                background-color: #059669;
            }
            QPushButton:disabled {
                background-color: #CBD5E1;
            }
        """)
        main_layout.addWidget(self.compare_btn)

        # Info label
        info_label = QLabel(
            "💡 Add 2+ videos → Extract fingerprints → Compare\n"
            "Requires: fpcalc (brew install chromaprint on Mac)"
        )
        info_label.setFont(QFont("Arial", 9))
        info_label.setStyleSheet("color: #78350F; border: none; padding: 8px;")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(info_label)

    def _add_video(self):
        """Add videos to the list."""
        from PyQt6.QtWidgets import QFileDialog

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Video File(s)",
            "",
            "Videos (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.m4v);;All files (*.*)"
        )

        if not file_paths:
            return

        for path in file_paths:
            if path not in [v['path'] for v in self.videos]:
                self.videos.append({'path': path, 'fingerprint': None, 'duration': 0.0})
                import os
                self.video_list.addItem(f"⏳ {os.path.basename(path)}")

        self.extract_btn.setEnabled(len(self.videos) >= 1)
        self.compare_btn.setEnabled(False)

    def _clear_all(self):
        """Clear all videos."""
        self.videos = []
        self.video_list.clear()
        self.extract_btn.setEnabled(False)
        self.compare_btn.setEnabled(False)

    def _extract_fingerprints(self):
        """Extract audio fingerprints from all videos."""
        from PyQt6.QtWidgets import QMessageBox, QProgressDialog
        from ..audio_fingerprinting import AudioFingerprintDetector, PrecisionMode

        # Get precision mode
        precision_mode_name = self.precision_combo.currentData()
        if precision_mode_name == 'maximum':
            precision_mode = PrecisionMode.MAXIMUM
        elif precision_mode_name == 'fast':
            precision_mode = PrecisionMode.FAST
        else:
            precision_mode = PrecisionMode.BALANCED

        # Create detector
        self.scene_detector = AudioFingerprintDetector(precision_mode=precision_mode)

        # Check if fpcalc is available
        if not self.scene_detector.fpcalc_available:
            QMessageBox.critical(
                self,
                "fpcalc Not Found",
                "Cannot extract audio fingerprints!\n\n"
                "Install chromaprint-tools:\n"
                "• macOS: brew install chromaprint\n"
                "• Linux: sudo apt install chromaprint-tools\n"
                "• Windows: choco install chromaprint"
            )
            return

        # Progress dialog
        progress = QProgressDialog("Extracting audio fingerprints...", "Cancel", 0, len(self.videos), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        # Extract fingerprints
        for i, video in enumerate(self.videos):
            if progress.wasCanceled():
                break

            progress.setValue(i)
            progress.setLabelText(f"Extracting: {os.path.basename(video['path'])}")

            fp, duration, raw_fp = self.scene_detector._extract_audio_fingerprint(video['path'])

            if fp:
                video['fingerprint'] = fp
                video['duration'] = duration
                import os
                self.video_list.item(i).setText(
                    f"✅ {os.path.basename(video['path'])} ({duration:.1f}s, {len(fp)} chars)"
                )
            else:
                import os
                self.video_list.item(i).setText(f"❌ {os.path.basename(video['path'])} (failed)")

        progress.setValue(len(self.videos))

        # Enable compare if we have at least 2 fingerprints
        extracted_count = sum(1 for v in self.videos if v['fingerprint'])
        self.compare_btn.setEnabled(extracted_count >= 2)

        QMessageBox.information(
            self,
            "Extraction Complete",
            f"Extracted {extracted_count}/{len(self.videos)} fingerprints"
        )

    def _compare_fingerprints(self):
        """Compare all fingerprints and show results."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
        import os

        # Build comparison table
        results = []
        results.append("=" * 100)
        results.append("AUDIO FINGERPRINT COMPARISON TABLE (Scene Detection)")
        results.append("=" * 100)
        results.append("")

        # List videos
        results.append("VIDEOS:")
        for i, video in enumerate(self.videos):
            if video['fingerprint']:
                results.append(f"  [{i}] {os.path.basename(video['path'])}")
                results.append(f"      Duration: {video['duration']:.1f}s, Fingerprint: {len(video['fingerprint'])} chars")
            else:
                results.append(f"  [{i}] {os.path.basename(video['path'])} - NO FINGERPRINT")
        results.append("")

        # Pairwise comparison
        results.append("PAIRWISE COMPARISONS:")
        results.append(f"{'Video A':<40} | {'Video B':<40} | {'Similarity':>10} | {'Scene?':>8}")
        results.append("-" * 100)

        for i in range(len(self.videos)):
            for j in range(i + 1, len(self.videos)):
                v1 = self.videos[i]
                v2 = self.videos[j]

                if not v1['fingerprint'] or not v2['fingerprint']:
                    continue

                # Compute simple similarity (character match ratio)
                fp1 = v1['fingerprint']
                fp2 = v2['fingerprint']

                # Simple similarity: matching characters at same positions
                min_len = min(len(fp1), len(fp2))
                max_len = max(len(fp1), len(fp2))
                matching = sum(1 for k in range(min_len) if fp1[k] == fp2[k])
                similarity = (matching / max_len) * 100 if max_len > 0 else 0.0

                # Check if it's a potential scene
                # Short video should be at least 20% shorter
                dur1 = v1['duration']
                dur2 = v2['duration']
                is_potential_scene = abs(dur1 - dur2) / max(dur1, dur2) > 0.20 if max(dur1, dur2) > 0 else False

                name1 = os.path.basename(v1['path'])[:38]
                name2 = os.path.basename(v2['path'])[:38]

                scene_str = "YES" if (is_potential_scene and similarity > 85) else "NO"
                results.append(f"{name1:<40} | {name2:<40} | {similarity:9.2f}% | {scene_str:>8}")

        results.append("-" * 100)
        results.append("")
        results.append("LEGEND:")
        results.append("  - Similarity: % of matching characters (simplified, not true audio similarity)")
        results.append("  - Scene?: YES if one video is 20%+ shorter AND similarity > 85%")
        results.append("")
        results.append("NOTE: This is a simplified comparison for debugging purposes.")
        results.append("      Real scene detection uses Chromaprint's advanced algorithm.")
        results.append("=" * 100)

        # Show results dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Audio Fingerprint Comparison Results")
        dialog.setMinimumSize(900, 600)

        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setPlainText("\n".join(results))
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Courier", 10))
        layout.addWidget(text_edit)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec()
