"""
Widgets de progression modernes - Version with TEXTE NOIR VISIBLE
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame, QScrollArea
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
        
        # Insertion avant le stretch
        insert_position = self.files_layout.count() - 1
        self.files_layout.insertWidget(insert_position, item_frame)
        
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