"""User interface optimisée pour VideoConverter plugin avec améliorations et correction affichage."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QFileDialog, QMessageBox, QHeaderView, QLabel, QSpinBox,
    QProgressBar, QGroupBox, QCheckBox, QApplication, QDialog,
    QDialogButtonBox, QFormLayout, QGridLayout, QLineEdit, QSystemTrayIcon
)

from PyQt6.QtCore import Qt, QTimer, QMutex, QMutexLocker, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QColor, QKeySequence, QShortcut, QIcon, QDragEnterEvent, QDropEvent
from pathlib import Path
from typing import Dict, Set, List, Optional
import os
import threading
import shutil
import time
from datetime import datetime, timedelta
from src.core.logger import Logger
from .advanced_settings import AdvancedSettingsDialog

logger = Logger.get_logger('VideoConverter.Window')

# Import paresseux des modules lourds
def lazy_import_converter():
    """Import paresseux du module converter."""
    from .converter import ConversionWorker
    return ConversionWorker

def lazy_import_settings():
    """Import paresseux du module settings."""
    from .settings import SettingsManager
    return SettingsManager

def lazy_import_metadata():
    """Import paresseux du module metadata."""
    from .metadata import MetadataManager
    return MetadataManager

def lazy_import_stats():
    """Import paresseux du module stats."""
    from .stats import StatsManager
    return StatsManager

def format_size(size: int) -> str:
    """Format optimisé pour la taille des fichiers."""
    if size < 1024:
        return f"{size} B"
    elif size < 1048576:  # 1024^2
        return f"{size/1024:.1f} KB"
    elif size < 1073741824:  # 1024^3
        return f"{size/1048576:.1f} MB"
    else:
        return f"{size/1073741824:.1f} GB"

def format_duration(seconds: float) -> str:
    """Formater une durée en secondes vers un format lisible."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.0f}min"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

class ConversionTimer:
    """Gestionnaire de temps pour estimation de progression."""
    
    def __init__(self):
        self.start_times = {}
        self.completed_conversions = []
        
    def start_conversion(self, file_path: Path, file_size: int):
        """Démarrer le chronométrage d'une conversion."""
        self.start_times[file_path] = {
            'start_time': time.time(),
            'file_size': file_size
        }
    
    def complete_conversion(self, file_path: Path, success: bool):
        """Terminer le chronométrage d'une conversion."""
        if file_path in self.start_times:
            start_info = self.start_times.pop(file_path)
            duration = time.time() - start_info['start_time']
            
            if success and duration > 0:
                self.completed_conversions.append({
                    'size': start_info['file_size'],
                    'duration': duration,
                    'speed': start_info['file_size'] / duration  # bytes/sec
                })
                
                # Garder seulement les 10 dernières conversions pour l'estimation
                if len(self.completed_conversions) > 10:
                    self.completed_conversions.pop(0)
    
    def estimate_remaining_time(self, remaining_files: List[Dict]) -> Optional[float]:
        """Estimer le temps restant basé sur l'historique."""
        if not self.completed_conversions:
            return None
        
        # Calculer la vitesse moyenne (bytes/sec)
        avg_speed = sum(conv['speed'] for conv in self.completed_conversions) / len(self.completed_conversions)
        
        # Calculer la taille totale restante
        total_remaining_size = sum(file_info.get('size', 0) for file_info in remaining_files)
        
        if avg_speed > 0:
            return total_remaining_size / avg_speed
        
        return None

class FastFileDiscoveryWorker(QThread):
    """Worker optimisé pour la découverte rapide de fichiers avec mise à jour temps réel."""
    
    file_found = pyqtSignal(str, int, int)  # file_path, size_bytes, size_mb
    progress = pyqtSignal(int, str)  # discovered_count, current_folder
    finished = pyqtSignal(int)  # total_discovered
    batch_update = pyqtSignal()  # Signal pour mise à jour par batch
    
    def __init__(self, folders: List[Path], min_size_mb: int = 100):
        super().__init__()
        self.folders = folders
        self.min_size_bytes = min_size_mb * 1024 * 1024
        self.is_running = True
        self.discovered_count = 0
        # Extensions vidéo communes uniquement pour performance
        self.video_exts = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.webm', '.wmv'}
        
        # Compteur pour mise à jour par batch
        self.batch_counter = 0
        self.batch_size = 5  # Mettre à jour l'affichage toutes les 5 découvertes
    
    def run(self):
        """Découverte rapide avec filtrage précoce et mise à jour temps réel."""
        try:
            for folder in self.folders:
                if not self.is_running or not folder.exists():
                    continue
                
                self.progress.emit(self.discovered_count, str(folder))
                self._scan_fast(folder, max_depth=4)
                
        except Exception as e:
            logger.error(f"Erreur dans la découverte de fichiers: {e}")
        finally:
            # Dernière mise à jour si nécessaire
            if self.batch_counter > 0:
                self.batch_update.emit()
            self.finished.emit(self.discovered_count)
    
    def _scan_fast(self, directory: Path, max_depth: int, current_depth: int = 0):
        """Scan optimisé avec limites de profondeur."""
        if not self.is_running or current_depth > max_depth:
            return
        
        try:
            # Utiliser scandir pour de meilleures performances que iterdir
            with os.scandir(directory) as entries:
                for entry in entries:
                    if not self.is_running:
                        break
                    
                    try:
                        if entry.is_file():
                            # Vérification rapide de l'extension
                            file_path = Path(entry.path)
                            if file_path.suffix.lower() in self.video_exts:
                                stat_info = entry.stat()
                                if stat_info.st_size >= self.min_size_bytes:
                                    # Vérification du suffixe _cvt rapidement
                                    if not entry.name.endswith('_cvt' + file_path.suffix):
                                        size_mb = int(stat_info.st_size / (1024*1024))
                                        self.file_found.emit(entry.path, stat_info.st_size, size_mb)
                                        self.discovered_count += 1
                                        
                                        # Mise à jour par batch pour éviter la surcharge UI
                                        self.batch_counter += 1
                                        if self.batch_counter >= self.batch_size:
                                            self.batch_update.emit()
                                            self.batch_counter = 0
                                            # Laisser le temps à l'UI de se mettre à jour
                                            self.msleep(10)
                        
                        elif entry.is_dir() and current_depth < max_depth:
                            # Skip des dossiers système et cachés
                            if not entry.name.startswith('.') and entry.name not in {
                                '$RECYCLE.BIN', 'System Volume Information', '__pycache__',
                                'node_modules', '.git', '.svn', 'Thumbs.db'
                            }:
                                self._scan_fast(Path(entry.path), max_depth, current_depth + 1)
                    
                    except (OSError, PermissionError):
                        # Skip les fichiers/dossiers inaccessibles
                        continue
                        
        except (OSError, PermissionError):
            logger.debug(f"Impossible d'accéder au dossier: {directory}")
    
    def stop(self):
        """Arrêter la découverte."""
        self.is_running = False

class VideoConverterWindow(QMainWindow):
    """Fenêtre principale optimisée avec améliorations UX."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎬 Video Converter Pro")
        self.setMinimumSize(900, 700)
        
        # Variables avec thread safety
        self.files_to_convert = {}
        self.files_mutex = QMutex()
        self.active_workers: Set = set()
        self.conversion_queue = []
        self.max_concurrent = 3
        
        # Nouveaux gestionnaires
        self.conversion_timer = ConversionTimer()
        self.start_time = None
        self.total_files_to_convert = 0
        
        # Chargement paresseux des composants
        self.settings = None
        self.settings_manager = None
        self.discovery_worker = None
        self.paused_after_current = False
        
        # Flag pour éviter les mises à jour excessives pendant la découverte
        self.discovery_in_progress = False
        self.pending_ui_update = False
        
        # Interface minimale au démarrage
        self.setup_minimal_ui()
        self.setup_shortcuts()
        self.setup_drag_drop()
        self.setup_system_tray()
        
        # Timers
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.check_conversion_queue)
        self.update_timer.start(2000)
        
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.refresh_progress_display)
        self.progress_timer.start(1000)
        
        self.ui_update_timer = QTimer()
        self.ui_update_timer.timeout.connect(self.batch_update_ui)
        self.ui_update_timer.setSingleShot(True)
        
        # Timer pour estimation du temps
        self.estimation_timer = QTimer()
        self.estimation_timer.timeout.connect(self.update_time_estimation)
        self.estimation_timer.start(5000)  # Toutes les 5 secondes
        
        logger.debug("Fenêtre VideoConverter initialisée avec améliorations")
    
    def setup_shortcuts(self):
        """Configuration des raccourcis clavier."""
        # Ctrl+O : Ajouter fichiers
        QShortcut(QKeySequence.StandardKey.Open, self, self.add_files)
        
        # Ctrl+Shift+O : Ajouter dossier
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, self.add_folder)
        
        # Ctrl+A : Sélectionner tout
        QShortcut(QKeySequence.StandardKey.SelectAll, self, self.toggle_select_all)
        
        # F5 : Démarrer conversion
        QShortcut(QKeySequence(Qt.Key.Key_F5), self, self.start_conversion)
        
        # Escape : Arrêter conversion
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.stop_conversion)
        
        # Ctrl+, : Paramètres
        QShortcut(QKeySequence.StandardKey.Preferences, self, self.show_advanced_settings)
        
        # Suppr : Supprimer sélectionnés
        QShortcut(QKeySequence.StandardKey.Delete, self, self.remove_selected_files)
        
        # Ctrl+L : Vider la liste
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear_files)
        
        # F1 : Aide
        QShortcut(QKeySequence.StandardKey.HelpContents, self, self.show_help)
    
    def setup_drag_drop(self):
        """Configuration du glisser-déposer."""
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Gérer l'entrée du glisser-déposer."""
        if event.mimeData().hasUrls():
            # Vérifier si au moins un fichier est une vidéo
            video_exts = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.webm', '.wmv'}
            has_video = False
            
            for url in event.mimeData().urls():
                path = Path(url.toLocalFile())
                if path.suffix.lower() in video_exts or path.is_dir():
                    has_video = True
                    break
            
            if has_video:
                event.acceptProposedAction()
                self.status_label.setText("📁 Relâchez pour ajouter les fichiers/dossiers")
            else:
                event.ignore()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """Gérer la sortie du glisser-déposer."""
        if not self.active_workers:
            self.status_label.setText("Prêt")
    
    def dropEvent(self, event: QDropEvent):
        """Gérer le dépôt de fichiers."""
        files_and_folders = []
        
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.exists():
                files_and_folders.append(path)
        
        if files_and_folders:
            self.add_dropped_files(files_and_folders)
            event.acceptProposedAction()
        
        self.status_label.setText("Prêt")
    
    def add_dropped_files(self, paths: List[Path]):
        """Ajouter les fichiers/dossiers glissés-déposés."""
        added_files = 0
        added_from_folders = 0
        
        self.status_label.setText("💥 Traitement des fichiers glissés...")
        QApplication.processEvents()
        
        settings = self.get_settings()
        suffix = getattr(settings, 'converted_suffix', '_cvt')
        deselect_converted = getattr(settings, 'deselect_converted_files', False)
        
        for path in paths:
            if path.is_file():
                # Fichier individuel
                if self.should_add_file(path):
                    if self.add_single_file(path, settings, suffix, deselect_converted):
                        added_files += 1
            
            elif path.is_dir():
                # Dossier - scanner récursivement
                video_extensions = ['*.mp4', '*.avi', '*.mkv', '*.mov', '*.flv', '*.webm', '*.wmv']
                
                for ext in video_extensions:
                    for file_path in path.rglob(ext):
                        if file_path.is_file() and self.should_add_file(file_path):
                            if self.add_single_file(file_path, settings, suffix, deselect_converted):
                                added_from_folders += 1
        
        total_added = added_files + added_from_folders
        if total_added > 0:
            self.refresh_table()
            message = f"✅ {total_added} fichiers ajoutés"
            if added_files > 0 and added_from_folders > 0:
                message += f" ({added_files} individuels, {added_from_folders} des dossiers)"
            self.status_label.setText(message)
        else:
            self.status_label.setText("❌ Aucun fichier vidéo valide trouvé")
    
    def add_single_file(self, path: Path, settings, suffix: str, deselect_converted: bool) -> bool:
        """Ajouter un seul fichier à la liste."""
        with QMutexLocker(self.files_mutex):
            if path not in self.files_to_convert:
                try:
                    size = path.stat().st_size
                    is_converted = self._is_converted_file(path, suffix)
                    
                    default_selected = True
                    if is_converted and deselect_converted:
                        default_selected = False
                    
                    state = 'En attente'
                    if is_converted:
                        state = 'En attente (converti)'
                    
                    self.files_to_convert[path] = {
                        'state': state,
                        'selected': default_selected,
                        'size': size,
                        'progress': 0,
                        'worker': None,
                        'attempt': 0,
                        'is_converted': is_converted
                    }
                    return True
                except OSError:
                    return False
        return False
    
    def setup_system_tray(self):
        """Configuration de l'icône système."""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setToolTip("Video Converter")
            
            # Menu contextuel
            from PyQt6.QtWidgets import QMenu
            tray_menu = QMenu()
            
            show_action = tray_menu.addAction("Afficher")
            show_action.triggered.connect(self.show_and_raise)
            
            start_action = tray_menu.addAction("Démarrer conversions")
            start_action.triggered.connect(self.start_conversion)
            
            tray_menu.addSeparator()
            
            quit_action = tray_menu.addAction("Quitter")
            quit_action.triggered.connect(self.close)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)
            
            # Icône par défaut (sera améliorée avec une vraie icône)
            self.tray_icon.show()
    
    def show_and_raise(self):
        """Afficher et mettre au premier plan."""
        self.show()
        self.raise_()
        self.activateWindow()
    
    def tray_icon_activated(self, reason):
        """Gérer les clics sur l'icône système."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_and_raise()
    
    def setup_minimal_ui(self):
        """Interface minimale pour démarrage ultra-rapide."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # En-tête avec info
        header_layout = QHBoxLayout()
        title_label = QLabel("🎬 Video Converter Pro")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2E86AB;")
        header_layout.addWidget(title_label)
        
        # Indicateur de progression globale
        self.global_progress = QProgressBar()
        self.global_progress.setVisible(False)
        self.global_progress.setFormat("Progression globale: %p% (%v/%m)")
        header_layout.addWidget(self.global_progress)
        
        header_layout.addStretch()
        
        # Estimation du temps
        self.time_estimation_label = QLabel("")
        self.time_estimation_label.setStyleSheet("color: #666; font-weight: bold;")
        header_layout.addWidget(self.time_estimation_label)
        
        self.status_label = QLabel("Prêt • Glissez-déposez des fichiers ici")
        self.status_label.setStyleSheet("color: #666;")
        header_layout.addWidget(self.status_label)
        layout.addLayout(header_layout)
        
        # Boutons principaux
        self.setup_main_buttons(layout)
        
        # Table des fichiers simplifiée
        self.setup_file_table(layout)
        
        # Boutons d'action
        self.setup_action_buttons(layout)

    def setup_main_buttons(self, layout):
        """Boutons principaux d'ajout de fichiers."""
        buttons_layout = QHBoxLayout()
        
        self.add_files_btn = QPushButton("📁 Fichiers (Ctrl+O)")
        self.add_files_btn.clicked.connect(self.add_files)
        self.add_files_btn.setToolTip("Sélectionner des fichiers vidéo à convertir")
        buttons_layout.addWidget(self.add_files_btn)
        
        self.add_folder_btn = QPushButton("📂 Dossier (Ctrl+Shift+O)")
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.add_folder_btn.setToolTip("Scanner un dossier pour des fichiers vidéo")
        buttons_layout.addWidget(self.add_folder_btn)
        
        self.discover_btn = QPushButton("🔍 Auto-Découverte")
        self.discover_btn.clicked.connect(self.start_discovery)
        self.discover_btn.setToolTip("Recherche automatique dans les dossiers communs")
        buttons_layout.addWidget(self.discover_btn)
        
        # Bouton pour filtrer la liste actuelle
        self.filter_btn = QPushButton("🔍 Filtrer")
        self.filter_btn.clicked.connect(self.filter_current_list)
        self.filter_btn.setToolTip("Appliquer les filtres actuels à la liste")
        buttons_layout.addWidget(self.filter_btn)
        
        buttons_layout.addStretch()
        
        # Indicateur d'espace disque
        self.disk_space_label = QLabel("")
        self.disk_space_label.setStyleSheet("color: #666; font-size: 11px;")
        buttons_layout.addWidget(self.disk_space_label)
        
        self.clear_btn = QPushButton("🗑️ Vider (Ctrl+L)")
        self.clear_btn.clicked.connect(self.clear_files)
        self.clear_btn.setToolTip("Vider la liste des fichiers")
        buttons_layout.addWidget(self.clear_btn)
        
        layout.addLayout(buttons_layout)
        
        # Mettre à jour l'espace disque
        self.update_disk_space_info()
        
    def setup_file_table(self, layout):
        """Table des fichiers simplifiée pour performance."""
        # Boutons de table
        table_controls = QHBoxLayout()
        
        self.select_all_btn = QPushButton("☑️ Tout (Ctrl+A)")
        self.select_all_btn.clicked.connect(self.toggle_select_all)
        table_controls.addWidget(self.select_all_btn)
        
        # Boutons de gestion des fichiers convertis
        self.select_only_converted_btn = QPushButton("🔄 Convertis")
        self.select_only_converted_btn.clicked.connect(self.select_only_converted_files)
        self.select_only_converted_btn.setToolTip("Sélectionner uniquement les fichiers déjà convertis")
        table_controls.addWidget(self.select_only_converted_btn)
        
        self.select_only_new_btn = QPushButton("🆕 Nouveaux")
        self.select_only_new_btn.clicked.connect(self.select_only_new_files)
        self.select_only_new_btn.setToolTip("Sélectionner uniquement les fichiers non convertis")
        table_controls.addWidget(self.select_only_new_btn)
        
        # Bouton suppression sélection
        self.remove_selected_btn = QPushButton("🗑️ Supprimer sélection (Suppr)")
        self.remove_selected_btn.clicked.connect(self.remove_selected_files)
        self.remove_selected_btn.setToolTip("Supprimer les fichiers sélectionnés de la liste")
        table_controls.addWidget(self.remove_selected_btn)
        
        table_controls.addStretch()
        
        # Compteur de fichiers
        self.file_count_label = QLabel("0 fichiers")
        self.file_count_label.setStyleSheet("color: #666;")
        table_controls.addWidget(self.file_count_label)
        
        layout.addLayout(table_controls)
        
        # Table simplifiée
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        
        headers = ["", "Fichier", "État", "Taille", "Actions"]
        self.files_table.setHorizontalHeaderLabels(headers)
        
        # Configuration améliorée des colonnes
        header = self.files_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        
        self.files_table.setColumnWidth(0, 30)   # Checkbox
        self.files_table.setColumnWidth(2, 280)  # État - Plus large pour les barres de progression
        self.files_table.setColumnWidth(4, 60)   # Actions
        
        # Style de la table
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.files_table.setWordWrap(True)
        
        layout.addWidget(self.files_table)
    
    def setup_action_buttons(self, layout):
        """Boutons d'action principaux."""
        action_layout = QHBoxLayout()
        
        # Bouton paramètres
        self.settings_btn = QPushButton("⚙️ Paramètres (Ctrl+,)")
        self.settings_btn.clicked.connect(self.show_advanced_settings)
        self.settings_btn.setToolTip("Ouvrir les paramètres avancés")
        action_layout.addWidget(self.settings_btn)
        
        # Bouton statistiques
        self.stats_btn = QPushButton("📊 Stats")
        self.stats_btn.clicked.connect(self.show_stats)
        self.stats_btn.setToolTip("Afficher les statistiques")
        action_layout.addWidget(self.stats_btn)
        
        # Bouton aide
        self.help_btn = QPushButton("❓ Aide (F1)")
        self.help_btn.clicked.connect(self.show_help)
        self.help_btn.setToolTip("Afficher l'aide")
        action_layout.addWidget(self.help_btn)
        
        action_layout.addStretch()
        
        # Boutons de conversion
        self.start_btn = QPushButton("▶️ Démarrer (F5)")
        self.start_btn.clicked.connect(self.start_conversion)
        self.start_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        action_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("⏸️ Pause après en cours")
        self.pause_btn.clicked.connect(self.pause_after_current)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; }")
        self.pause_btn.setToolTip("Arrêter les nouvelles conversions mais finir celles en cours")
        action_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹️ Arrêter (Esc)")
        self.stop_btn.clicked.connect(self.stop_conversion)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; }")
        action_layout.addWidget(self.stop_btn)
        
        layout.addLayout(action_layout)
    
    def show_help(self):
        """Afficher l'aide contextuelle."""
        help_text = """
<h2>🎬 Video Converter Pro - Guide rapide</h2>

<h3>📁 Ajouter des fichiers :</h3>
• <b>Ctrl+O</b> : Ajouter des fichiers
• <b>Ctrl+Shift+O</b> : Ajouter un dossier
• <b>Glisser-déposer</b> : Déposez directement dans la fenêtre

<h3>⌨️ Raccourcis utiles :</h3>
• <b>F5</b> : Démarrer la conversion
• <b>Escape</b> : Arrêter la conversion
• <b>Ctrl+A</b> : Sélectionner tous les fichiers
• <b>Suppr</b> : Supprimer la sélection
• <b>Ctrl+L</b> : Vider la liste
• <b>Ctrl+,</b> : Ouvrir les paramètres

<h3>🎯 Filtrage intelligent :</h3>
• Configure la taille minimale dans les paramètres
• Les fichiers déjà convertis (suffixe _cvt) peuvent être ignorés
• Utilise "🔍 Filtrer" pour appliquer les nouveaux filtres

<h3>⚙️ Conversion :</h3>
• Sélectionne les fichiers à convertir
• Configure les paramètres selon tes besoins
• Lance avec F5 ou le bouton "Démarrer"
• Suis la progression en temps réel

<h3>💡 Astuces :</h3>
• L'estimation de temps s'améliore avec l'usage
• Les conversions sont automatiquement pausées si l'espace disque est insuffisant
• Utilise l'icône système pour voir les notifications
        """
        
        QMessageBox.information(self, "Aide - Video Converter Pro", help_text)
    
    def update_disk_space_info(self):
        """Mettre à jour les informations d'espace disque."""
        try:
            # Utiliser le dossier home par défaut
            home_path = Path.home()
            total, used, free = shutil.disk_usage(home_path)
            
            free_gb = free / (1024**3)
            total_gb = total / (1024**3)
            percent_free = (free / total) * 100
            
            if percent_free < 10:
                color = "#d32f2f"  # Rouge
                icon = "⚠️"
            elif percent_free < 20:
                color = "#ff9800"  # Orange
                icon = "⚠️"
            else:
                color = "#4caf50"  # Vert
                icon = "💾"
            
            self.disk_space_label.setText(f"{icon} {free_gb:.1f}GB libre")
            self.disk_space_label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
            
        except Exception as e:
            logger.debug(f"Erreur lecture espace disque: {e}")
            self.disk_space_label.setText("💾 Espace: N/A")
    
    def check_disk_space_for_conversion(self) -> bool:
        """Vérifier l'espace disque avant conversion."""
        try:
            # Estimer l'espace nécessaire (approximation conservative)
            with QMutexLocker(self.files_mutex):
                selected_files = [info for info in self.files_to_convert.values() if info.get('selected', False)]
                total_size = sum(info.get('size', 0) for info in selected_files)
            
            # Estimation : besoin de 20% d'espace supplémentaire pour les fichiers temporaires
            estimated_space_needed = total_size * 0.2
            
            home_path = Path.home()
            _, _, free = shutil.disk_usage(home_path)
            
            if free < estimated_space_needed:
                reply = QMessageBox.warning(
                    self, "⚠️ Espace disque insuffisant",
                    f"Espace libre: {format_size(free)}\n"
                    f"Espace estimé nécessaire: {format_size(estimated_space_needed)}\n\n"
                    f"Voulez-vous continuer quand même ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                return reply == QMessageBox.StandardButton.Yes
            
            return True
            
        except Exception as e:
            logger.warning(f"Impossible de vérifier l'espace disque: {e}")
            return True  # Continuer en cas d'erreur de vérification
    
    def update_time_estimation(self):
        """Mettre à jour l'estimation du temps restant."""
        if not self.active_workers and not self.conversion_queue:
            self.time_estimation_label.setText("")
            return
        
        # Collecter les informations des fichiers restants
        remaining_files = []
        with QMutexLocker(self.files_mutex):
            # Fichiers en cours de conversion
            for path, info in self.files_to_convert.items():
                if info.get('worker') or path in self.conversion_queue:
                    remaining_files.append({'size': info.get('size', 0)})
        
        # Estimer le temps restant
        estimated_seconds = self.conversion_timer.estimate_remaining_time(remaining_files)
        
        if estimated_seconds:
            remaining_time_str = format_duration(estimated_seconds)
            
            # Calculer la progression globale
            if hasattr(self, 'total_files_to_convert') and self.total_files_to_convert > 0:
                completed = self.total_files_to_convert - len(remaining_files)
                progress_percent = (completed / self.total_files_to_convert) * 100
                
                self.time_estimation_label.setText(f"⏱️ {remaining_time_str} restant")
                
                if not self.global_progress.isVisible():
                    self.global_progress.setVisible(True)
                
                self.global_progress.setMaximum(self.total_files_to_convert)
                self.global_progress.setValue(completed)
            else:
                self.time_estimation_label.setText(f"⏱️ ~{remaining_time_str}")
        else:
            self.time_estimation_label.setText("⏱️ Estimation en cours...")
    
    def remove_selected_files(self):
        """Supprimer les fichiers sélectionnés de la liste."""
        files_to_remove = []
        
        with QMutexLocker(self.files_mutex):
            for path, info in self.files_to_convert.items():
                if info.get('selected', False):
                    # Ne pas supprimer les fichiers en cours de conversion
                    if not info.get('worker'):
                        files_to_remove.append(path)
        
        if not files_to_remove:
            QMessageBox.information(self, "Info", "Aucun fichier sélectionné à supprimer\n(Les fichiers en cours de conversion ne peuvent pas être supprimés)")
            return
        
        # Confirmation
        reply = QMessageBox.question(
            self, "Confirmer suppression",
            f"Supprimer {len(files_to_remove)} fichier(s) de la liste ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            with QMutexLocker(self.files_mutex):
                for path in files_to_remove:
                    if path in self.files_to_convert:
                        del self.files_to_convert[path]
            
            self.refresh_table()
            self.status_label.setText(f"🗑️ {len(files_to_remove)} fichiers supprimés")
    
    def filter_current_list(self):
        """Filtrer la liste actuelle selon les paramètres."""
        files_to_remove = []
        removed_count = 0
        
        with QMutexLocker(self.files_mutex):
            for path, info in self.files_to_convert.items():
                # Arrêter le worker s'il existe avant de supprimer
                if info.get('worker'):
                    continue  # Ne pas supprimer les fichiers en cours de conversion
                
                if not self.should_add_file(path):
                    files_to_remove.append(path)
        
        # Supprimer les fichiers qui ne passent plus le filtre
        with QMutexLocker(self.files_mutex):
            for path in files_to_remove:
                if path in self.files_to_convert:
                    del self.files_to_convert[path]
                    removed_count += 1
        
        self.refresh_table()
        self.status_label.setText(f"🔍 Filtrage appliqué: {removed_count} fichiers supprimés")
    
    def get_settings(self):
        """Chargement paresseux des settings."""
        if self.settings is None:
            SettingsManager = lazy_import_settings()
            self.settings_manager = SettingsManager
            self.settings = SettingsManager.load_settings()
            self.max_concurrent = self.settings.max_concurrent_conversions
            
        return self.settings
        
    def show_advanced_settings(self):
        """Afficher le dialogue de paramètres avancés."""
        settings = self.get_settings()
        dialog = AdvancedSettingsDialog(self, settings)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.on_settings_updated()
        
    def on_settings_updated(self):
        """Callback appelé quand les paramètres sont mis à jour."""
        # Forcer le rechargement des paramètres
        self.settings = None
        settings = self.get_settings()
        
        # Mettre à jour le nombre de threads
        self.max_concurrent = settings.max_concurrent_conversions
        
        # Proposer de filtrer automatiquement la liste
        if hasattr(self, 'files_to_convert') and self.files_to_convert:
            reply = QMessageBox.question(
                self, "Filtrer la liste", 
                "Paramètres mis à jour. Voulez-vous appliquer les nouveaux filtres à la liste actuelle ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.filter_current_list()
        
        # Rafraîchir l'affichage
        self.refresh_table()
        self.update_disk_space_info()
        
        self.status_label.setText("✅ Paramètres mis à jour")
        QTimer.singleShot(3000, lambda: self.status_label.setText("Prêt"))

    def select_files_by_suffix(self, suffix: str) -> int:
        """Sélectionner les fichiers avec un suffixe donné."""
        count = 0
        with QMutexLocker(self.files_mutex):
            for path, info in self.files_to_convert.items():
                if path.stem.endswith(suffix):
                    info['selected'] = True
                    count += 1
                else:
                    info['selected'] = False
        
        self.refresh_table()
        return count

    def remove_files_by_suffix(self, suffix: str) -> int:
        """Supprimer les fichiers avec un suffixe donné de la liste."""
        files_to_remove = []
        
        with QMutexLocker(self.files_mutex):
            for path, info in self.files_to_convert.items():
                if path.stem.endswith(suffix):
                    # Arrêter le worker s'il existe
                    if info.get('worker'):
                        info['worker'].stop()
                        self.active_workers.discard(info['worker'])
                    files_to_remove.append(path)
        
        # Supprimer les fichiers
        count = 0
        with QMutexLocker(self.files_mutex):
            for path in files_to_remove:
                if path in self.files_to_convert:
                    del self.files_to_convert[path]
                    count += 1
        
        self.refresh_table()
        return count

    def test_single_conversion(self):
        """Tester la conversion sur un seul fichier sélectionné."""
        selected_files = self.get_selected_files()
        
        if not selected_files:
            QMessageBox.warning(self, "Test", "Veuillez sélectionner au moins un fichier pour le test")
            return
        
        # Prendre le premier fichier sélectionné
        test_file = selected_files[0]
        
        # Démarrer la conversion en mode test (1 seul fichier)
        self.conversion_queue = [test_file]
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        QMessageBox.information(self, "Test", f"Test de conversion lancé sur:\n{test_file.name}")

    def test_specific_attempt(self, attempt_number):
        """Tester une tentative spécifique de compression."""
        selected_files = self.get_selected_files()
        
        if not selected_files:
            QMessageBox.warning(self, "Test", "Veuillez sélectionner au moins un fichier pour le test")
            return
        
        # Prendre le premier fichier sélectionné
        test_file = selected_files[0]
        
        # Créer un worker avec une tentative spécifique
        settings = self.get_settings()
        
        # Modifier temporairement les paramètres pour utiliser seulement cette tentative
        if hasattr(settings, 'attempts') and attempt_number <= len(settings.attempts):
            attempt_config = settings.attempts[attempt_number - 1]
            
            QMessageBox.information(
                self, "Test Tentative", 
                f"Test de la tentative {attempt_number} lancé sur:\n{test_file.name}\n"
                f"Paramètres: CRF={attempt_config.crf}, Preset={attempt_config.preset}"
            )
            
            # Démarrer la conversion avec ces paramètres
            self.conversion_queue = [test_file]
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
        else:
            QMessageBox.warning(self, "Erreur", f"Tentative {attempt_number} non configurée")

    def start_conversion_after_settings(self):
        """Démarrer la conversion après fermeture des paramètres."""
        QTimer.singleShot(100, self.start_conversion)

    def _is_converted_file(self, file_path: Path, suffix: str = None) -> bool:
        """Vérifier si un fichier est marqué comme converti."""
        if suffix is None:
            suffix = getattr(self.get_settings(), 'converted_suffix', '_cvt')
        
        # Vérifier le suffixe dans le nom de fichier
        return file_path.stem.endswith(suffix)
    
    def show_stats(self):
        """Afficher les statistiques avec chargement paresseux."""
        try:
            StatsManager = lazy_import_stats()
            stats_manager = StatsManager()
            summary = stats_manager.get_stats_summary()
            
            # Dialog simple avec les stats
            dialog = QMessageBox(self)
            dialog.setWindowTitle("📊 Statistiques")
            dialog.setIcon(QMessageBox.Icon.Information)
            
            stats_text = f"""
Conversions totales: {summary['total_conversions']}
Réussies: {summary['successful_conversions']}
Échouées: {summary['failed_conversions']}
Taux de réussite: {summary['success_rate']:.1f}%

Espace économisé: {format_size(summary['total_space_saved'])}
Compression moyenne: {summary['average_compression']:.1f}%
Tentatives moyennes: {summary['average_attempts']:.1f}
            """
            
            dialog.setText(stats_text.strip())
            dialog.exec()
            
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Impossible de charger les statistiques: {e}")
    
    def start_discovery(self):
        """Démarrage de la découverte rapide avec dialog."""
        if self.discovery_worker and self.discovery_worker.isRunning():
            QMessageBox.information(self, "Info", "Découverte déjà en cours...")
            return
        
        # Dialog de configuration rapide
        dialog = QDialog(self)
        dialog.setWindowTitle("🔍 Configuration de découverte")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Taille minimale
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Taille minimale:"))
        size_spin = QSpinBox()
        size_spin.setRange(50, 5000)
        size_spin.setValue(500)  # 500MB par défaut
        size_spin.setSuffix(" MB")
        size_layout.addWidget(size_spin)
        size_layout.addStretch()
        layout.addLayout(size_layout)
        
        # Dossiers à scanner
        layout.addWidget(QLabel("Dossiers à scanner:"))
        
        # Dossiers par défaut
        default_folders = [
            (Path.home() / "Videos", "Dossier Vidéos"),
            (Path.home() / "Downloads", "Téléchargements"),
            (Path.home() / "Desktop", "Bureau"),
        ]
        
        checkboxes = []
        for folder_path, description in default_folders:
            if folder_path.exists():
                cb = QCheckBox(f"{description} ({folder_path})")
                cb.setChecked(True)
                cb.folder_path = folder_path
                layout.addWidget(cb)
                checkboxes.append(cb)
        
        # Dossier personnalisé
        custom_layout = QHBoxLayout()
        custom_cb = QCheckBox("Dossier personnalisé:")
        custom_btn = QPushButton("Parcourir...")
        custom_path = None
        
        def browse_custom():
            nonlocal custom_path
            folder = QFileDialog.getExistingDirectory(dialog, "Sélectionner un dossier")
            if folder:
                custom_path = Path(folder)
                custom_cb.setText(f"Personnalisé: {custom_path.name}")
                custom_cb.setChecked(True)
        
        custom_btn.clicked.connect(browse_custom)
        custom_layout.addWidget(custom_cb)
        custom_layout.addWidget(custom_btn)
        layout.addLayout(custom_layout)
        
        # Boutons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Récupérer les dossiers sélectionnés
            selected_folders = []
            for cb in checkboxes:
                if cb.isChecked():
                    selected_folders.append(cb.folder_path)
            
            if custom_cb.isChecked() and custom_path:
                selected_folders.append(custom_path)
            
            if selected_folders:
                min_size_mb = size_spin.value()
                self.auto_discover_files(selected_folders, min_size_mb)
            else:
                QMessageBox.information(self, "Info", "Aucun dossier sélectionné")
    
    def auto_discover_files(self, folders_to_scan: List[Path], min_size_mb: int):
        """Auto-découverte des fichiers en arrière-plan avec mise à jour temps réel."""
        self.discover_btn.setEnabled(False)
        self.discover_btn.setText("🔍 Recherche...")
        self.status_label.setText("Découverte en cours...")
        self.discovery_in_progress = True
        
        # Créer et démarrer le worker
        self.discovery_worker = FastFileDiscoveryWorker(folders_to_scan, min_size_mb)
        self.discovery_worker.file_found.connect(self.on_file_discovered)
        self.discovery_worker.progress.connect(self.on_discovery_progress)
        self.discovery_worker.finished.connect(self.on_discovery_finished)
        self.discovery_worker.batch_update.connect(self.on_batch_update)
        self.discovery_worker.start()
    
    def on_file_discovered(self, file_path: str, size_bytes: int, size_mb: int):
        """Fichier découvert par le worker - ajout immédiat avec gestion des fichiers convertis."""
        path = Path(file_path)
        
        # Vérifier si c'est un fichier déjà converti
        settings = self.get_settings()
        suffix = getattr(settings, 'converted_suffix', '_cvt')
        is_converted = self._is_converted_file(path, suffix)
        
        # Appliquer les règles de gestion des fichiers convertis
        ignore_converted = getattr(settings, 'ignore_converted_files', True)
        deselect_converted = getattr(settings, 'deselect_converted_files', False)
        
        if is_converted and ignore_converted:
            # Ignorer complètement ce fichier
            return
        
        # Déterminer l'état de sélection par défaut
        default_selected = True
        if is_converted and deselect_converted:
            default_selected = False
        
        with QMutexLocker(self.files_mutex):
            if path not in self.files_to_convert:
                state = 'En attente'
                if is_converted:
                    state = 'En attente (converti)'
                
                self.files_to_convert[path] = {
                    'state': state,
                    'selected': default_selected,
                    'size': size_bytes,
                    'progress': 0,
                    'worker': None,
                    'attempt': 0,
                    'is_converted': is_converted
                }
                
                # Marquer qu'une mise à jour UI est nécessaire
                self.pending_ui_update = True
    
    def on_batch_update(self):
        """Mise à jour par batch pour éviter la surcharge de l'UI."""
        if self.pending_ui_update and self.discovery_in_progress:
            self.pending_ui_update = False
            # Programmer une mise à jour UI avec un léger délai pour éviter la surcharge
            if not self.ui_update_timer.isActive():
                self.ui_update_timer.start(200)  # 200ms de délai
    
    def batch_update_ui(self):
        """Mise à jour groupée de l'UI pendant la découverte."""
        if self.discovery_in_progress:
            try:
                self.refresh_table()
                # Mettre à jour le compteur dans le bouton
                with QMutexLocker(self.files_mutex):
                    count = len(self.files_to_convert)
                self.discover_btn.setText(f"🔍 Trouvés: {count}")
            except Exception as e:
                logger.debug(f"Erreur lors de la mise à jour UI batch: {e}")
    
    def on_discovery_progress(self, count: int, current_folder: str):
        """Mise à jour du progrès de découverte."""
        self.status_label.setText(f"Scan: {Path(current_folder).name}... ({count} trouvés)")
    
    def on_discovery_finished(self, count: int):
        """Découverte terminée."""
        self.discovery_in_progress = False
        self.pending_ui_update = False
        
        self.discover_btn.setEnabled(True)
        self.discover_btn.setText("🔍 Auto-Découverte")
        
        # Mise à jour finale complète
        self.refresh_table()
        
        if count > 0:
            total_size = sum(info['size'] for info in self.files_to_convert.values())
            self.status_label.setText(f"✅ Découverte terminée: {count} fichiers ({format_size(total_size)})")
            
            # Notification système si disponible
            if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    "Découverte terminée",
                    f"Trouvé {count} fichiers vidéo ({format_size(total_size)})",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000
                )
            
            QMessageBox.information(
                self, "Découverte terminée", 
                f"Trouvé {count} fichiers volumineux\n"
                f"Taille totale: {format_size(total_size)}\n\n"
                f"Utilisez les paramètres pour ajuster les critères de conversion."
            )
        else:
            self.status_label.setText("❌ Aucun fichier trouvé")
            QMessageBox.information(
                self, "Découverte terminée", 
                "Aucun fichier vidéo volumineux trouvé.\n\n"
                "Essayez de réduire la taille minimale ou de sélectionner d'autres dossiers."
            )
    
    def add_files(self):
        """Ajouter des fichiers manuellement."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Sélectionner des fichiers vidéo", "",
            "Vidéos (*.mp4 *.avi *.mkv *.mov *.flv *.webm *.wmv);;Tous (*.*)"
        )
        
        added = 0
        settings = self.get_settings()
        suffix = getattr(settings, 'converted_suffix', '_cvt')
        deselect_converted = getattr(settings, 'deselect_converted_files', False)
        
        for file_path in files:
            path = Path(file_path)
            if path.exists() and self.should_add_file(path):
                if self.add_single_file(path, settings, suffix, deselect_converted):
                    added += 1
        
        if added > 0:
            self.refresh_table()
            self.status_label.setText(f"✅ {added} fichiers ajoutés")
    
    def add_folder(self):
        """Ajouter un dossier complet."""
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier")
        if not folder:
            return
        
        folder_path = Path(folder)
        added = 0
        settings = self.get_settings()
        
        self.status_label.setText("📂 Scan du dossier...")
        QApplication.processEvents()
        
        # Extensions vidéo supportées
        video_extensions = ['*.mp4', '*.avi', '*.mkv', '*.mov', '*.flv', '*.webm', '*.wmv']
        
        for ext in video_extensions:
            for file_path in folder_path.rglob(ext):
                if file_path.is_file() and self.should_add_file(file_path):
                    settings = self.get_settings()
                    suffix = getattr(settings, 'converted_suffix', '_cvt')
                    deselect_converted = getattr(settings, 'deselect_converted_files', False)
                    
                    if self.add_single_file(file_path, settings, suffix, deselect_converted):
                        added += 1
        
        if added > 0:
            self.refresh_table()
            self.status_label.setText(f"✅ {added} fichiers ajoutés du dossier")
        else:
            self.status_label.setText("❌ Aucun fichier vidéo trouvé dans le dossier")
        
    def should_add_file(self, file_path: Path) -> bool:
        """Vérifier si un fichier doit être ajouté."""
        settings = self.get_settings()
        
        # Vérifier la taille AVANT tout le reste (plus efficace)
        if settings.use_size_threshold:
            try:
                size = file_path.stat().st_size
                if size < settings.size_threshold:
                    return False
            except OSError:
                return False
        
        # Vérifier les suffixes de fichiers traités
        converted_suffix = getattr(settings, 'converted_suffix', '_cvt')
        failed_suffix = getattr(settings, 'failed_suffix', '_nocomp')
        
        # Vérifier si c'est un fichier déjà converti
        if self._is_converted_file(file_path, converted_suffix):
            ignore_converted = getattr(settings, 'ignore_converted_files', True)
            if ignore_converted:
                return False
        
        # Vérifier si c'est un fichier marqué comme non-compressible
        if file_path.stem.endswith(failed_suffix):
            ignore_failed = getattr(settings, 'ignore_non_compressible', False)
            if ignore_failed:
                return False
        
        return True
    
    def clear_files(self):
        """Vider la liste des fichiers."""
        if not self.files_to_convert:
            return
        
        # Vérifier s'il y a des conversions en cours
        active_conversions = any(
            info.get('worker') is not None 
            for info in self.files_to_convert.values()
        )
        
        if active_conversions:
            reply = QMessageBox.question(
                self, "Confirmer", 
                "Des conversions sont en cours. Les arrêter et vider la liste?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
            
            self.stop_conversion()
        
        with QMutexLocker(self.files_mutex):
            self.files_to_convert.clear()
        
        # Cacher la barre de progression globale
        self.global_progress.setVisible(False)
        self.time_estimation_label.setText("")
        
        self.refresh_table()
        self.status_label.setText("🗑️ Liste vidée")
    
    def refresh_progress_display(self):
        """Rafraîchir l'affichage des progressions de façon simple et robuste."""
        if not self.active_workers:
            return  # Pas de conversions actives
        
        # Forcer un rafraîchissement complet de la table pendant les conversions
        try:
            self.refresh_table()
        except Exception as e:
            logger.debug(f"Erreur lors du rafraîchissement des progressions: {e}")
    
    def refresh_table(self):
        """Rafraîchissement optimisé de la table avec gestion robuste des progressions."""
        with QMutexLocker(self.files_mutex):
            files_copy = dict(self.files_to_convert)
        
        self.files_table.setRowCount(len(files_copy))
        
        total_selected = 0
        total_size = 0
        
        for row, (path, info) in enumerate(files_copy.items()):
            # Checkbox de sélection
            checkbox = QCheckBox()
            checkbox.setChecked(info.get('selected', True))
            checkbox.stateChanged.connect(
                lambda state, p=path: self.update_selection(p, state)
            )
            self.files_table.setCellWidget(row, 0, checkbox)
            
            # Nom du fichier avec couleur selon l'état
            name_item = QTableWidgetItem(path.name)
            name_item.setToolTip(str(path))
            
            state = info['state']
            is_converted = info.get('is_converted', False)
            
            # Couleurs selon l'état et le type - CORRECTION: meilleur affichage
            if 'Erreur' in state or 'Échec' in state:
                name_item.setForeground(QColor('#d32f2f'))  # Rouge
                name_item.setText(f"❌ {path.name}")
            elif 'Terminé' in state or 'Succès' in state:
                name_item.setForeground(QColor('#388e3c'))  # Vert
                name_item.setText(f"✅ {path.name}")
            elif 'En cours' in state or info.get('worker'):
                name_item.setForeground(QColor('#1976d2'))  # Bleu
                name_item.setText(f"⚙️ {path.name}")
            elif is_converted:
                name_item.setForeground(QColor('#FF9800'))  # Orange pour les fichiers déjà convertis
                name_item.setText(f"🔄 {path.name}")
            
            self.files_table.setItem(row, 1, name_item)
            
            # Gestion de l'état et des progressions
            progress = info.get('progress', 0)
            attempt = info.get('attempt', 1)
            worker = info.get('worker')
            
            # Si worker actif ET progress != -1, afficher barre de progression
            if worker and progress >= 0 and progress != -1:
                # Toujours créer une nouvelle barre pour éviter les problèmes
                progress_widget = QWidget()
                progress_layout = QHBoxLayout(progress_widget)
                progress_layout.setContentsMargins(2, 2, 2, 2)
                
                progress_bar = QProgressBar()
                progress_bar.setMinimum(0)
                progress_bar.setMaximum(100)
                progress_bar.setValue(max(0, min(100, progress)))
                progress_bar.setTextVisible(True)
                
                # Texte selon l'état
                if progress == 0:
                    progress_text = f"Tentative {attempt} - Démarrage..."
                elif progress >= 100:
                    progress_text = f"Tentative {attempt} - Finalisation..."
                else:
                    progress_text = f"Tentative {attempt} - {progress}%"
                
                progress_bar.setFormat(progress_text)
                
                # Couleur selon la tentative
                if attempt == 1:
                    color = "#4CAF50"  # Vert
                elif attempt == 2:
                    color = "#FF9800"  # Orange
                else:
                    color = "#f44336"  # Rouge
                
                progress_bar.setStyleSheet(f"""
                    QProgressBar {{
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        text-align: center;
                        font-size: 11px;
                        font-weight: bold;
                        height: 22px;
                        min-width: 220px;
                    }}
                    QProgressBar::chunk {{
                        background-color: {color};
                        border-radius: 2px;
                    }}
                """)
                
                progress_layout.addWidget(progress_bar)
                self.files_table.setCellWidget(row, 2, progress_widget)
            else:
                # État textuel normal (pas de conversion active ou terminée)
                state_item = QTableWidgetItem(state)
                
                # CORRECTION: Meilleur affichage des résultats de conversion
                if 'Terminé:' in state:
                    # Extraire le message après "Terminé:"
                    result_msg = state.replace('Terminé:', '').strip()
                    state_item.setForeground(QColor('#388e3c'))  # Vert pour succès
                    state_item.setText(f"✅ {result_msg}")
                elif 'Échec:' in state or 'Erreur' in state:
                    # Extraire le message d'erreur
                    error_msg = state.replace('Échec:', '').replace('Erreur:', '').strip()
                    state_item.setForeground(QColor('#d32f2f'))  # Rouge pour échec
                    state_item.setText(f"❌ {error_msg}")
                elif 'En attente' in state:
                    if is_converted:
                        state_item.setText("⏳ En attente (converti)")
                        state_item.setForeground(QColor('#FF9800'))
                    else:
                        state_item.setText("⏳ En attente")
                        state_item.setForeground(QColor('#666'))
                elif 'Arrêté' in state:
                    state_item.setText("⏹️ Arrêté")
                    state_item.setForeground(QColor('#666'))
                
                self.files_table.setItem(row, 2, state_item)
            
            # Taille
            size = info.get('size', 0)
            size_item = QTableWidgetItem(format_size(size))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.files_table.setItem(row, 3, size_item)
            
            # Actions
            if not worker:
                # Bouton de suppression pour les fichiers inactifs
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(2, 2, 2, 2)
                
                delete_btn = QPushButton("🗑️")
                delete_btn.setMaximumSize(25, 25)
                delete_btn.setToolTip("Supprimer de la liste")
                delete_btn.clicked.connect(lambda checked, p=path: self.remove_file(p))
                action_layout.addWidget(delete_btn)
                
                self.files_table.setCellWidget(row, 4, action_widget)
            else:
                # Indicateur de conversion active
                action_item = QTableWidgetItem("⚙️")
                action_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                action_item.setToolTip(f"Conversion en cours (tentative {attempt})")
                self.files_table.setItem(row, 4, action_item)
            
            # Compter pour les statistiques
            if info.get('selected', True):
                total_selected += 1
                total_size += size
        
        # Mettre à jour les labels
        converted_count = sum(1 for info in files_copy.values() if info.get('is_converted', False))
        
        label_text = f"{len(files_copy)} fichiers ({total_selected} sélectionnés, {format_size(total_size)})"
        if converted_count > 0:
            label_text += f" - {converted_count} déjà convertis"
        
        if hasattr(self, 'file_count_label'):
            self.file_count_label.setText(label_text)
        
        # Mettre à jour le bouton de sélection
        if files_copy and hasattr(self, 'select_all_btn'):
            all_selected = all(info.get('selected', True) for info in files_copy.values())
            self.select_all_btn.setText("☑️ Désél. tout" if all_selected else "☑️ Sél. tout")
    
    def select_only_converted_files(self):
        """Sélectionner uniquement les fichiers déjà convertis."""
        selected_count = 0
        
        with QMutexLocker(self.files_mutex):
            for path, info in self.files_to_convert.items():
                is_converted = info.get('is_converted', False)
                if is_converted:
                    info['selected'] = True
                    selected_count += 1
                else:
                    info['selected'] = False
        
        self.refresh_table()
        self.status_label.setText(f"🔄 {selected_count} fichiers convertis sélectionnés")
    
    def select_only_new_files(self):
        """Sélectionner uniquement les fichiers non convertis."""
        selected_count = 0
        
        with QMutexLocker(self.files_mutex):
            for path, info in self.files_to_convert.items():
                is_converted = info.get('is_converted', False)
                if not is_converted:
                    info['selected'] = True
                    selected_count += 1
                else:
                    info['selected'] = False
        
        self.refresh_table()
        self.status_label.setText(f"🆕 {selected_count} fichiers nouveaux sélectionnés")
    
    def update_selection(self, path: Path, state):
        """Mise à jour de la sélection d'un fichier."""
        with QMutexLocker(self.files_mutex):
            if path in self.files_to_convert:
                self.files_to_convert[path]['selected'] = (state == Qt.CheckState.Checked.value)
        
        # Mettre à jour le compteur
        QTimer.singleShot(100, self.update_file_count)

    def update_file_count(self):
        """Mettre à jour le compteur de fichiers."""
        with QMutexLocker(self.files_mutex):
            selected_count = sum(1 for info in self.files_to_convert.values() if info.get('selected', True))
            selected_size = sum(info['size'] for info in self.files_to_convert.values() if info.get('selected', True))
            total_count = len(self.files_to_convert)
        
        if hasattr(self, 'file_count_label'):
            self.file_count_label.setText(
                f"{total_count} fichiers ({selected_count} sélectionnés, {format_size(selected_size)})"
            )
    
    def remove_file(self, path: Path):
        """Supprimer un fichier de la liste."""
        with QMutexLocker(self.files_mutex):
            if path in self.files_to_convert:
                info = self.files_to_convert[path]
                # Arrêter le worker s'il existe
                if info.get('worker'):
                    info['worker'].stop()
                    self.active_workers.discard(info['worker'])
                del self.files_to_convert[path]
        
        self.refresh_table()
        self.status_label.setText("🗑️ Fichier supprimé")
    
    def toggle_select_all(self):
        """Basculer la sélection de tous les fichiers."""
        with QMutexLocker(self.files_mutex):
            if not self.files_to_convert:
                return
            
            # Vérifier l'état actuel
            all_selected = all(info.get('selected', True) for info in self.files_to_convert.values())
            new_state = not all_selected
            
            # Appliquer le nouvel état
            for info in self.files_to_convert.values():
                info['selected'] = new_state
        
        self.refresh_table()
    
    def get_selected_files(self) -> List[Path]:
        """Obtenir la liste des fichiers sélectionnés."""
        with QMutexLocker(self.files_mutex):
            return [path for path, info in self.files_to_convert.items() 
                   if info.get('selected', False)]
    
    def start_conversion(self):
        """Démarrer la conversion des fichiers sélectionnés."""
        selected_files = self.get_selected_files()
        
        if not selected_files:
            QMessageBox.warning(self, "Attention", "Aucun fichier sélectionné pour la conversion")
            return
        
        # Vérifier ffmpeg
        if not self.check_ffmpeg():
            return
        
        # Vérifier l'espace disque
        if not self.check_disk_space_for_conversion():
            return
        
        # NETTOYER l'état précédent
        self.conversion_queue.clear()
        self.active_workers.clear()
        self.conversion_timer = ConversionTimer()  # Reset du timer
        
        # Ajouter à la file de conversion
        self.conversion_queue.extend(selected_files)
        self.total_files_to_convert = len(selected_files)
        
        # Réactiver la conversion si elle était en pause
        self.paused_after_current = False
        
        # Mettre à jour l'interface AVANT de démarrer
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        # Afficher la barre de progression globale
        self.global_progress.setVisible(True)
        self.global_progress.setMaximum(self.total_files_to_convert)
        self.global_progress.setValue(0)
        
        self.start_time = time.time()
        self.status_label.setText(f"🚀 Démarrage de {len(selected_files)} conversions...")
        
        # Notification système
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "Conversion démarrée",
                f"Démarrage de {len(selected_files)} conversions",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        
        logger.info(f"=== DÉMARRAGE: {len(selected_files)} fichiers en file ===")
    
    def check_ffmpeg(self) -> bool:
        """Vérifier que ffmpeg est disponible."""
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            QMessageBox.critical(
                self, "❌ Erreur", 
                "FFmpeg n'est pas installé ou accessible.\n\n"
                "💡 Solution: Installez FFmpeg depuis https://ffmpeg.org\n"
                "Ou ajoutez-le au PATH système."
            )
            return False
    
    def check_conversion_queue(self):
        """Vérifier la file de conversion et démarrer de nouvelles conversions."""
        # Nettoyer les workers terminés
        finished_workers = {worker for worker in self.active_workers if worker.isFinished()}
        for worker in finished_workers:
            self.active_workers.discard(worker)
            worker.deleteLater()
        
        # Démarrer de nouvelles conversions si possible
        while (len(self.active_workers) < self.max_concurrent and 
               self.conversion_queue and 
               self.stop_btn.isEnabled() and
               not self.paused_after_current):
            
            file_path = self.conversion_queue.pop(0)
            
            # Vérifier que le fichier est encore dans la liste
            with QMutexLocker(self.files_mutex):
                if file_path not in self.files_to_convert:
                    continue
                
                info = self.files_to_convert[file_path]
                if info.get('worker'):  # Déjà un worker actif
                    continue
                
                # Démarrer le chronométrage
                self.conversion_timer.start_conversion(file_path, info.get('size', 0))
            
            # Créer et démarrer le worker
            ConversionWorker = lazy_import_converter()
            worker = ConversionWorker(file_path, self.get_settings())
            
            # Connecter les signaux
            worker.progress.connect(self.update_progress)
            worker.finished.connect(self.conversion_finished)
            worker.error.connect(self.conversion_error)
            worker.attempt_changed.connect(self.update_attempt)
            
            # Enregistrer le worker
            with QMutexLocker(self.files_mutex):
                info = self.files_to_convert.get(file_path)
                if info:
                    info['worker'] = worker
                    info['state'] = 'Démarrage...'
                    info['progress'] = 0
                    info['attempt'] = 1
            
            self.active_workers.add(worker)
            worker.start()
            
            logger.debug(f"Worker démarré pour {file_path.name}")
        
        # Mettre à jour l'affichage
        if self.active_workers or self.conversion_queue:
            active_count = len(self.active_workers)
            queue_count = len(self.conversion_queue)
            status_text = f"🔄 Conversions: {active_count}/{self.max_concurrent} actives, {queue_count} en attente"
            if self.paused_after_current:
                status_text += " (En pause après en cours)"
            self.status_label.setText(status_text)
        
        # CORRECTION: Vérifier si toutes les conversions sont terminées
        conversion_in_progress = bool(self.active_workers or self.conversion_queue)
        conversion_was_started = self.stop_btn.isEnabled()
        
        if conversion_was_started and not conversion_in_progress:
            logger.info("Toutes les conversions sont terminées - déclenchement de all_conversions_finished")
            self.all_conversions_finished()

    def conversion_finished(self, file_path: str, success: bool, message: str):
        """Conversion terminée."""
        path = Path(file_path)
        
        # Terminer le chronométrage
        self.conversion_timer.complete_conversion(path, success)
        
        with QMutexLocker(self.files_mutex):
            if path in self.files_to_convert:
                info = self.files_to_convert[path]
                info['state'] = f"Terminé: {message}" if success else f"Échec: {message}"
                info['progress'] = -1  # Marquer comme terminé
                
                # IMPORTANT: Nettoyer la référence au worker
                worker = info.get('worker')
                info['worker'] = None
                
                # Retirer le worker des actifs
                if worker and worker in self.active_workers:
                    self.active_workers.discard(worker)
                
                # Mettre à jour la taille si remplacement
                settings = self.get_settings()
                if success and settings.replace_original and path.exists():
                    try:
                        info['size'] = path.stat().st_size
                    except OSError:
                        pass
        
        result_text = "terminée" if success else "échouée"
        logger.info(f"Conversion {result_text} pour {path.name}: {message}")
        
        # Forcer un rafraîchissement immédiat pour montrer le résultat
        QTimer.singleShot(100, self.refresh_table)
            
    def conversion_error(self, file_path: str, error: str):
        """Erreur de conversion."""
        path = Path(file_path)
        
        # Terminer le chronométrage (échec)
        self.conversion_timer.complete_conversion(path, False)
        
        with QMutexLocker(self.files_mutex):
            if path in self.files_to_convert:
                info = self.files_to_convert[path]
                info['state'] = f"Erreur: {error}"
                info['progress'] = -1  # IMPORTANT: marquer comme terminé
                
                # IMPORTANT: Nettoyer la référence au worker
                worker = info.get('worker')
                info['worker'] = None
                
                # Retirer le worker des actifs
                if worker and worker in self.active_workers:
                    self.active_workers.discard(worker)
        
        logger.error(f"Erreur de conversion pour {path.name}: {error}")
        
        # Forcer un rafraîchissement immédiat pour montrer l'erreur
        QTimer.singleShot(100, self.refresh_table)
    
    def update_progress(self, file_path: str, progress: int):
        """Mettre à jour le progrès d'une conversion."""
        path = Path(file_path)
        with QMutexLocker(self.files_mutex):
            if path in self.files_to_convert:
                info = self.files_to_convert[path]
                info['progress'] = progress
                if progress > 0:
                    info['state'] = f'En cours ({progress}%)'
    
    def update_attempt(self, file_path: str, attempt: int):
        """Mettre à jour le numéro de tentative."""
        path = Path(file_path)
        with QMutexLocker(self.files_mutex):
            if path in self.files_to_convert:
                info = self.files_to_convert[path]
                info['attempt'] = attempt
                info['state'] = f'Tentative {attempt}'
                info['progress'] = 0  # Reset du progrès pour nouvelle tentative
    
    def pause_after_current(self):
        """Mettre en pause après les conversions en cours."""
        self.paused_after_current = True
        self.pause_btn.setEnabled(False)
        self.start_btn.setText("▶️ Reprendre")
        self.start_btn.setEnabled(True)
        
        # Mettre à jour le statut
        active_count = len(self.active_workers)
        queue_count = len(self.conversion_queue)
        self.status_label.setText(f"⏸️ En pause: {active_count} conversions se terminent, {queue_count} en attente")
        
        logger.info("⏸️ Pause demandée - les conversions en cours vont se terminer")
    
    def stop_conversion(self):
        """Arrêter toutes les conversions immédiatement."""
        # Vider la file d'attente
        self.conversion_queue.clear()
        self.paused_after_current = False
        
        # Arrêter tous les workers actifs
        for worker in list(self.active_workers):
            worker.stop()
        
        # Mettre à jour les états
        with QMutexLocker(self.files_mutex):
            for info in self.files_to_convert.values():
                if info.get('worker'):
                    info['worker'] = None
                    if 'En cours' in info.get('state', '') or 'Démarrage' in info.get('state', ''):
                        info['state'] = 'Arrêté'
                    info['progress'] = -1  # Marquer comme terminé
        
        # Mettre à jour l'interface
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶️ Démarrer")
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.paused_after_current = False
        
        # Cacher la barre de progression globale
        self.global_progress.setVisible(False)
        self.time_estimation_label.setText("")
        
        self.status_label.setText("⏹️ Conversions arrêtées")
        
        # Notification système
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "Conversion arrêtée",
                "Toutes les conversions ont été arrêtées",
                QSystemTrayIcon.MessageIcon.Warning,
                2000
            )
        
        # Forcer un rafraîchissement complet de la table
        self.refresh_table()
        
        logger.info("⏹️ Toutes les conversions arrêtées")
    
    def all_conversions_finished(self):
        """Toutes les conversions sont terminées."""
        logger.info("=== DÉBUT all_conversions_finished ===")
        
        # Calculer les statistiques AVANT de modifier l'interface
        with QMutexLocker(self.files_mutex):
            total = len(self.files_to_convert)
            successful = 0
            failed = 0
            
            for path, info in self.files_to_convert.items():
                state = info.get('state', '')
                if 'Terminé:' in state:
                    successful += 1
                elif 'Échec:' in state or 'Erreur:' in state:
                    failed += 1
            
            logger.info(f"Statistiques finales: {successful} succès, {failed} échecs sur {total} total")
        
        # Calculer le temps total
        total_time = ""
        if self.start_time:
            elapsed = time.time() - self.start_time
            total_time = f" en {format_duration(elapsed)}"
        
        # Mettre à jour l'interface
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶️ Démarrer")
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.paused_after_current = False
        
        # Cacher la barre de progression globale
        self.global_progress.setVisible(False)
        self.time_estimation_label.setText("")
        
        # Nettoyer complètement les workers actifs
        self.active_workers.clear()
        self.conversion_queue.clear()
        
        # Message de statut final
        if successful + failed > 0:
            self.status_label.setText(f"✅ Terminé{total_time}: {successful} succès, {failed} échecs")
        else:
            self.status_label.setText("✅ Conversions terminées")
        
        # Notification système
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "🎬 Conversions terminées",
                f"✅ {successful} succès, ❌ {failed} échecs{total_time}",
                QSystemTrayIcon.MessageIcon.Information,
                5000
            )
        
        # Forcer un rafraîchissement complet de la table
        self.refresh_table()
        
        # Afficher le résumé seulement si il y a eu des conversions
        if successful + failed > 0:
            success_rate = (successful/(successful+failed)*100) if (successful+failed) > 0 else 0
            
            QMessageBox.information(
                self, "🎬 Conversions terminées", 
                f"Toutes les conversions sont terminées{total_time}!\n\n"
                f"📊 Résultats:\n"
                f"• Total traité: {successful + failed}\n"
                f"• ✅ Réussies: {successful}\n"
                f"• ❌ Échouées: {failed}\n"
                f"• 📈 Taux de réussite: {success_rate:.1f}%\n\n"
                f"💡 Consultez les statistiques pour plus de détails."
            )
        
        logger.info(f"=== FIN all_conversions_finished: {successful}/{successful+failed} réussies ===")
    
    def msleep(self, ms):
        """Sleep pour millisecondes."""
        import time
        time.sleep(ms / 1000.0)
    
    def closeEvent(self, event):
        """Gestion de la fermeture de la fenêtre."""
        # Arrêter la découverte si en cours
        if self.discovery_worker and self.discovery_worker.isRunning():
            reply = QMessageBox.question(
                self, "Arrêter la découverte", 
                "La découverte de fichiers est en cours. L'arrêter et fermer?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.discovery_worker.stop()
                self.discovery_worker.wait(3000)  # Attendre jusqu'à 3 secondes
            else:
                event.ignore()
                return
        
        # Arrêter les conversions si en cours
        if self.active_workers:
            reply = QMessageBox.question(
                self, "Arrêter les conversions", 
                "Des conversions sont en cours. Les arrêter et fermer?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_conversion()
                # Attendre un peu que les workers s'arrêtent
                for _ in range(30):  # Attendre jusqu'à 3 secondes
                    if not self.active_workers:
                        break
                    QApplication.processEvents()
                    self.msleep(100)
                event.accept()
            else:
                # Réduire dans la barre système au lieu de fermer
                if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
                    self.hide()
                    self.tray_icon.showMessage(
                        "Video Converter",
                        "L'application continue en arrière-plan.\n"
                        "Double-cliquez sur l'icône pour la restaurer.",
                        QSystemTrayIcon.MessageIcon.Information,
                        3000
                    )
                    event.ignore()
                else:
                    event.ignore()
        else:
            event.accept()