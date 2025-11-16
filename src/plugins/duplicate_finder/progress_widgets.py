"""
Widgets de progression modernes - Version with TEXTE NOIR VISIBLE
"""

import os
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame, QScrollArea, QPushButton, QTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor

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


class HashDebuggerV2(QFrame):
    """Advanced widget for interactive hash debugging with frame selection."""

    def __init__(self, video_hasher=None, parent=None):
        super().__init__(parent)
        self.video_hasher = video_hasher
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
        desc_label = QLabel("Select videos, choose starting frame positions, and calculate 10 consecutive hashes for detailed comparison")
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

        # Calculate button
        self.calculate_btn = QPushButton("⚡ Calculate Hash Table")
        self.calculate_btn.setMinimumHeight(44)
        self.calculate_btn.clicked.connect(self._calculate_hash_table)
        self.calculate_btn.setEnabled(False)
        self.calculate_btn.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 12pt;
            }
            QPushButton:hover:enabled {
                background-color: #2563EB;
            }
            QPushButton:disabled {
                background-color: #CBD5E1;
            }
        """)
        main_layout.addWidget(self.calculate_btn)

        # Results display
        results_header = QLabel("📊 Results Table (copy/paste ready):")
        results_header.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        results_header.setStyleSheet("color: #1E3A8A; border: none;")
        main_layout.addWidget(results_header)

        self.results_table = QTextEdit()
        self.results_table.setReadOnly(True)
        self.results_table.setMinimumHeight(300)
        self.results_table.setPlaceholderText("Hash table will appear here (ready to copy/paste)")
        self.results_table.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 2px solid #94A3B8;
                border-radius: 6px;
                padding: 12px;
                font-family: 'Courier New', monospace;
                font-size: 9pt;
                line-height: 1.4;
            }
        """)
        main_layout.addWidget(self.results_table)

    def set_video_hasher(self, video_hasher):
        """Set the video hasher instance."""
        self.video_hasher = video_hasher

    def _add_video(self):
        """Add a video to the list."""
        from PyQt6.QtWidgets import QFileDialog
        import cv2

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm);;All Files (*.*)"
        )

        if file_path:
            # Open video to get metadata
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                self.results_table.setPlainText(f"ERROR: Cannot open video {file_path}")
                return

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

            self.calculate_btn.setEnabled(True)

    def _create_video_entry(self, file_path, total_frames, fps):
        """Create a widget for a single video entry."""
        from PyQt6.QtWidgets import QSlider

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

        # Frame selection
        frame_layout = QHBoxLayout()

        frame_label = QLabel("Start frame:")
        frame_label.setStyleSheet("color: #475569; border: none;")
        frame_layout.addWidget(frame_label)

        frame_spin = QSpinBox()
        frame_spin.setMinimum(0)
        frame_spin.setMaximum(max(0, total_frames - 10))
        frame_spin.setValue(0)
        frame_spin.setSuffix(f" / {total_frames}")
        frame_spin.setMinimumWidth(150)
        frame_spin.valueChanged.connect(lambda v: self._update_start_frame(file_path, v))
        frame_layout.addWidget(frame_spin)

        # Time display
        time_label = QLabel("(0.00s)")
        time_label.setStyleSheet("color: #64748B; border: none;")
        time_label.setMinimumWidth(80)
        frame_spin.valueChanged.connect(lambda v: time_label.setText(f"({v/fps:.2f}s)"))
        frame_layout.addWidget(time_label)

        frame_layout.addStretch()

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
        frame_layout.addWidget(remove_btn)

        layout.addLayout(frame_layout)

        # Store widgets for later access
        entry_frame.frame_spin = frame_spin
        entry_frame.file_path = file_path

        return entry_frame

    def _update_start_frame(self, file_path, frame_num):
        """Update start frame for a video."""
        for video in self.video_data:
            if video['path'] == file_path:
                video['start_frame'] = frame_num
                break

    def _remove_video(self, file_path, widget):
        """Remove a video from the list."""
        # Remove from data
        self.video_data = [v for v in self.video_data if v['path'] != file_path]

        # Remove widget
        self.video_list_layout.removeWidget(widget)
        widget.deleteLater()

        # Disable calculate if no videos
        if not self.video_data:
            self.calculate_btn.setEnabled(False)

    def _clear_all(self):
        """Clear all videos."""
        # Clear all widgets
        while self.video_list_layout.count() > 1:  # Keep stretch
            item = self.video_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.video_data = []
        self.results_table.clear()
        self.calculate_btn.setEnabled(False)

    def _calculate_hash_table(self):
        """Calculate hash table for all videos."""
        if not self.video_hasher:
            self.results_table.setPlainText("ERROR: No video hasher available")
            return

        if not self.video_data:
            return

        import cv2
        from src.core.logger import Logger
        logger = Logger.get_logger('DuplicateFinder.HashDebuggerV2')

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

            except Exception as e:
                results.append(f"✗ ERROR: {str(e)}")
                logger.error(f"Error processing {file_path}: {e}")

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

        self.results_table.setPlainText("\n".join(results))