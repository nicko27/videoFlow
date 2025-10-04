"""
Fenêtre principale du détecteur de doublons - Version corrigée interface + sauvegarde paramètres
Corrections: titre plus petit, zone du bas optimisée, boutons colorés, paramètres sauvegardés
"""
import os
import time
from send2trash import send2trash
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QFileDialog, QMessageBox, QTabWidget, QGroupBox, QGridLayout,
    QDoubleSpinBox, QSpinBox, QFrame, QSplitter, QLabel, QDialog, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QTimer, QSettings
from PyQt6.QtGui import QFont

# Import conditionnel pour éviter les erreurs d'import
try:
    from .video_hasher import VideoHasher
    from .comparison_dialog import ComparisonDialog
    from .progress_widgets import ModernProgressWidget, FileListWidget, StatusIndicator
except ImportError:
    # Fallback pour les imports directs
    from video_hasher import VideoHasher
    from comparison_dialog import ComparisonDialog
    from progress_widgets import ModernProgressWidget, FileListWidget, StatusIndicator

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.MainWindow')


class ParallelHashWorker(QThread):
    """Worker pour le calcul des hashs en parallèle - Version corrigée"""
    
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    file_processed = pyqtSignal(str, bool)
    current_file = pyqtSignal(str)
    # NOUVEAU: Signal pour mise à jour en temps réel
    progress_details = pyqtSignal(int, int, str)  # current, total, filename
    
    def __init__(self, files, video_hasher, max_workers, timeout=120):
        super().__init__()
        self.files = files
        self.video_hasher = video_hasher
        self.max_workers = min(max_workers, len(files))
        self.timeout = timeout
        self._stop = False
        self._mutex = QMutex()
        self.processed_count = 0
        
        # Filtre les fichiers à traiter
        self.files_to_process = []
        self.files_cached = []
        
        for file in files:
            if self.video_hasher.has_hash(file):
                self.files_cached.append(file)
            else:
                self.files_to_process.append(file)
                
        logger.info(f"Hash Worker: {len(self.files_to_process)} à traiter, {len(self.files_cached)} en cache")

    def process_single_file(self, file_path):
        """Traite un seul fichier"""
        if self.is_stopped():
            return file_path, False
            
        try:
            # SIGNAL AMÉLIORÉ avec nom de fichier
            filename = os.path.basename(file_path)
            self.current_file.emit(f"📄 {filename}")
            
            if self.video_hasher.has_hash(file_path):
                return file_path, True
            
            if not os.path.exists(file_path):
                return file_path, False
            
            file_size = os.path.getsize(file_path)
            if file_size < 10240:  # < 10KB
                return file_path, False
            
            self.video_hasher.compute_video_hash(file_path)
            return file_path, True
            
        except Exception as e:
            logger.error(f"Erreur hash {os.path.basename(file_path)}: {e}")
            return file_path, False
    
    def run(self):
        """Exécute le traitement parallèle - Version corrigée"""
        try:
            total_files = len(self.files)
            
            # Traite d'abord les fichiers en cache
            for file_path in self.files_cached:
                if self.is_stopped():
                    break
                filename = os.path.basename(file_path)
                self.current_file.emit(f"💾 {filename} (cache)")
                self.update_progress(file_path, True)
                # Délai pour voir l'affichage
                self.msleep(50)
            
            # Traite les nouveaux fichiers en parallèle
            if self.files_to_process:
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_file = {
                        executor.submit(self.process_single_file, file_path): file_path 
                        for file_path in self.files_to_process
                    }
                    
                    for future in future_to_file:
                        if self.is_stopped():
                            for f in future_to_file:
                                f.cancel()
                            break
                        
                        try:
                            file_path, success = future.result(timeout=self.timeout)
                            self.update_progress(file_path, success)
                        except Exception as e:
                            file_path = future_to_file[future]
                            logger.error(f"Erreur/timeout {os.path.basename(file_path)}: {e}")
                            self.update_progress(file_path, False)
            
            if not self.is_stopped():
                self.finished.emit()
                
        except Exception as e:
            self.error.emit(str(e))
    
    def stop(self):
        self._mutex.lock()
        self._stop = True
        self._mutex.unlock()
    
    def is_stopped(self):
        self._mutex.lock()
        stopped = self._stop
        self._mutex.unlock()
        return stopped
    
    def update_progress(self, file_path, success):
        self._mutex.lock()
        self.processed_count += 1
        current_count = self.processed_count
        total_count = len(self.files)
        self._mutex.unlock()
        
        filename = os.path.basename(file_path)
        
        # SIGNAUX AMÉLIORÉS
        self.file_processed.emit(file_path, success)
        self.progress.emit(current_count)
        self.progress_details.emit(current_count, total_count, filename)


class OptimizedComparisonWorker(QThread):
    """Worker pour les comparaisons optimisées - Version corrigée"""
    
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    duplicate_found = pyqtSignal(str, str, float)
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)
    total_comparisons_signal = pyqtSignal(int)
    # NOUVEAU: Signaux détaillés
    comparison_details = pyqtSignal(int, int, str, str)  # current, total, file1, file2
    
    def __init__(self, files, video_hasher, threshold, config):
        super().__init__()
        self.files = files
        self.video_hasher = video_hasher
        self.threshold = threshold
        self.config = config
        self._stop = False
        self._mutex = QMutex()
        self.processed_count = 0
        
    def generate_pairs(self, files):
        """Génère les paires à comparer"""
        self.status_update.emit("🔍 Préparation des comparaisons...")
        
        pairs = []
        cached_pairs = []
        skipped_cache = 0
        skipped_ignored = 0
        
        all_possible_pairs = []
        for i, file1 in enumerate(files):
            for file2 in files[i+1:]:
                all_possible_pairs.append((file1, file2))
        
        total_pairs = len(all_possible_pairs)

        for file1, file2 in all_possible_pairs:
            if self.is_stopped():
                break
            
            if self.video_hasher.is_pair_ignored(file1, file2):
                skipped_ignored += 1
                continue
            
            cached_result = self.video_hasher.get_cached_comparison(file1, file2)
            if cached_result is not None:
                skipped_cache += 1
                if cached_result > self.threshold:
                    cached_pairs.append((file1, file2, cached_result))
                    self.duplicate_found.emit(file1, file2, cached_result)
                continue
            
            pairs.append((file1, file2))
        
        self.cached_pairs = cached_pairs
        self.total_comparisons = len(pairs) + len(cached_pairs)
        self.total_comparisons_signal.emit(self.total_comparisons)
        
        status = f"Paires: {len(pairs)} à comparer"
        if skipped_cache > 0:
            status += f", {skipped_cache} en cache"
        if skipped_ignored > 0:
            status += f", {skipped_ignored} ignorées"
        
        logger.info(status)
        self.status_update.emit(status)
        
        return pairs
    
    def run(self):
        """Exécute les comparaisons - Version corrigée"""
        try:
            pairs = self.generate_pairs(self.files)
            
            if not pairs:
                self.status_update.emit("✅ Toutes les comparaisons en cache!")
                self.finished.emit()
                return
            
            self.status_update.emit(f"🚀 {len(pairs)} comparaisons à traiter")
            
            with ThreadPoolExecutor(max_workers=self.config['comparison_workers']) as executor:
                batch_size = self.config['batch_size']
                
                for i in range(0, len(pairs), batch_size):
                    if self.is_stopped():
                        break
                    
                    batch = pairs[i:i + batch_size]
                    
                    futures = []
                    for pair in batch:
                        future = executor.submit(self.compare_pair, pair)
                        futures.append((future, pair))
                    
                    for future, pair in futures:
                        if self.is_stopped():
                            break
                        
                        try:
                            result = future.result(timeout=self.config['comparison_timeout'])
                            self.update_progress(result, pair)
                        except Exception as e:
                            logger.error(f"Erreur comparaison: {e}")
                            self.update_progress((pair[0], pair[1], 0.0), pair)
            
            if not self.is_stopped():
                self.status_update.emit("✅ Comparaisons terminées!")
                self.finished.emit()
                
        except Exception as e:
            logger.error(f"Erreur worker comparaison: {e}")
            self.error.emit(str(e))
    
    def compare_pair(self, pair):
        """Compare une paire de vidéos"""
        file1, file2 = pair
        
        if self.is_stopped():
            return None
        
        try:
            similarity = self.video_hasher.compare_videos(file1, file2)
            return (file1, file2, similarity)
        except Exception as e:
            logger.error(f"Erreur comparaison {os.path.basename(file1)} vs {os.path.basename(file2)}: {e}")
            return (file1, file2, 0.0)
    
    def update_progress(self, result, pair):
        """Met à jour la progression - Version corrigée"""
        if result is None:
            return
            
        file1, file2, similarity = result
        
        self._mutex.lock()
        self.processed_count += 1
        current_count = self.processed_count
        total_count = self.total_comparisons
        self._mutex.unlock()
        
        # SIGNAUX AMÉLIORÉS avec noms de fichiers
        name1 = os.path.basename(file1)
        name2 = os.path.basename(file2)
        self.comparison_details.emit(current_count, total_count, name1, name2)
        
        if similarity > self.threshold:
            self.duplicate_found.emit(file1, file2, similarity)
        
        self.progress.emit(current_count)
    
    def stop(self):
        self._mutex.lock()
        self._stop = True
        self._mutex.unlock()
        
    def is_stopped(self):
        self._mutex.lock()
        stopped = self._stop
        self._mutex.unlock()
        return stopped


class DuplicateFinderWindow(QMainWindow):
    """Fenêtre principale redesignée - Version interface corrigée + sauvegarde paramètres"""
    
    closed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔍 Détecteur de Doublons Vidéo")
        self.setMinimumSize(1000, 800)
        
        # NOUVEAU: Gestionnaire de paramètres
        self.settings = QSettings("DuplicateFinder", "VideoDeduplicator")
        
        # Variables
        self.potential_duplicates = []
        self.failed_files = []
        self.hash_worker = None
        self.comparison_worker = None
        self.start_time = None
        self.video_hasher = VideoHasher()
        self.duplicate_processing_stopped = False
        
        # NOUVEAU: Timers pour synchronisation affichage
        self.status_update_timer = QTimer()
        self.status_update_timer.timeout.connect(self.force_ui_update)
        self.status_update_timer.setSingleShot(False)
        
        self.setup_ui()
        
        # NOUVEAU: Charge les paramètres sauvegardés APRÈS setup_ui
        self.load_settings()
        
        # NOUVEAU: Marque le chargement comme terminé
        self._settings_loaded = True
        
        # NOUVEAU: Connecte les signaux de changement pour sauvegarde automatique
        self.connect_settings_signals()
        
        self.auto_cleanup_database()

    def setup_ui(self):
        """Configure l'interface utilisateur - VERSION CORRIGÉE"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal avec splitter
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)  # RÉDUIT: 15 → 10
        
        # TITRE RÉDUIT - Plus petit et moins de padding
        title = QLabel("🔍 Détecteur de Doublons Vidéo")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))  # RÉDUIT: 20 → 16
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #1976D2;
                background-color: #E3F2FD;
                border-radius: 8px;
                padding: 8px;
                margin: 5px 0px;
            }
        """)  # RÉDUIT: border-radius 12→8, padding 15→8, margin 10→5
        main_layout.addWidget(title)
        
        # Splitter horizontal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        
        # Panneau gauche - Configuration
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Panneau droit - Progression
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Proportions 40/60
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)

    def create_left_panel(self):
        """Crée le panneau de gauche"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #DEE2E6;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Onglets de configuration
        self.config_tabs = QTabWidget()
        self.config_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                background-color: #FAFAFA;
            }
            QTabBar::tab {
                background: #F8F9FA;
                border: 1px solid #DEE2E6;
                padding: 8px 16px;
                margin-right: 2px;
                border-radius: 4px 4px 0px 0px;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                border-bottom: 1px solid #FFFFFF;
            }
        """)
        
        # Onglet fichiers
        files_tab = self.create_files_tab()
        self.config_tabs.addTab(files_tab, "📁 Fichiers")
        
        # Onglet paramètres
        params_tab = self.create_parameters_tab()
        self.config_tabs.addTab(params_tab, "⚙️ Paramètres")
        
        layout.addWidget(self.config_tabs)
        
        # Boutons d'action - CORRIGÉS
        actions_group = self.create_action_buttons()
        layout.addWidget(actions_group)
        
        return panel

    def create_files_tab(self):
        """Crée l'onglet de gestion des fichiers"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Boutons d'ajout - AVEC COULEURS
        buttons_layout = QGridLayout()
        buttons_layout.setSpacing(10)
        
        # BOUTON AJOUTER FICHIERS - BLEU
        self.add_files_btn = QPushButton("📄 Ajouter fichiers")
        self.add_files_btn.setMinimumHeight(40)
        self.add_files_btn.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0056B3;
            }
        """)
        self.add_files_btn.clicked.connect(self.add_files)
        
        # BOUTON AJOUTER DOSSIER - VERT
        self.add_folder_btn = QPushButton("📂 Ajouter dossier")
        self.add_folder_btn.setMinimumHeight(40)
        self.add_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1E7E34;
            }
        """)
        self.add_folder_btn.clicked.connect(self.add_folder)
        
        # BOUTON VIDER LISTE - ORANGE
        self.clear_btn = QPushButton("🗑️ Vider liste")
        self.clear_btn.setMinimumHeight(40)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #FD7E14;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #E55A00;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_list)
        
        # BOUTON VIDER CACHE - VIOLET
        self.clear_cache_btn = QPushButton("💾 Vider cache")
        self.clear_cache_btn.setMinimumHeight(40)
        self.clear_cache_btn.setStyleSheet("""
            QPushButton {
                background-color: #6F42C1;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #59359A;
            }
        """)
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        
        buttons_layout.addWidget(self.add_files_btn, 0, 0)
        buttons_layout.addWidget(self.add_folder_btn, 0, 1)
        buttons_layout.addWidget(self.clear_btn, 1, 0)
        buttons_layout.addWidget(self.clear_cache_btn, 1, 1)
        
        layout.addLayout(buttons_layout)
        
        # Liste des fichiers
        self.file_list_widget = FileListWidget()
        layout.addWidget(self.file_list_widget)
        
        return tab

    def create_parameters_tab(self):
        """Crée l'onglet des paramètres"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Paramètres essentiels
        essential_group = QGroupBox("🎯 Paramètres essentiels")
        essential_layout = QGridLayout(essential_group)
        essential_layout.setSpacing(10)
        
        # Seuil de similarité
        essential_layout.addWidget(QLabel("Seuil de similarité:"), 0, 0)
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(50.0, 100.0)
        self.threshold_spin.setValue(90.0)
        self.threshold_spin.setSuffix("%")
        self.threshold_spin.setDecimals(1)
        essential_layout.addWidget(self.threshold_spin, 0, 1)
        
        layout.addWidget(essential_group)
        
        # Parallélisation
        workers_group = QGroupBox("🔄 Parallélisation")
        workers_layout = QGridLayout(workers_group)
        workers_layout.setSpacing(10)
        
        workers_layout.addWidget(QLabel("Workers hashs:"), 0, 0)
        self.hash_workers_spin = QSpinBox()
        self.hash_workers_spin.setRange(1, 8)
        self.hash_workers_spin.setValue(2)
        workers_layout.addWidget(self.hash_workers_spin, 0, 1)
        
        workers_layout.addWidget(QLabel("Workers comparaisons:"), 1, 0)
        self.comparison_workers_spin = QSpinBox()
        self.comparison_workers_spin.setRange(1, 8)
        self.comparison_workers_spin.setValue(4)
        workers_layout.addWidget(self.comparison_workers_spin, 1, 1)
        
        workers_layout.addWidget(QLabel("Taille batch:"), 2, 0)
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(10, 200)
        self.batch_size_spin.setValue(50)
        workers_layout.addWidget(self.batch_size_spin, 2, 1)
        
        layout.addWidget(workers_group)
        
        # Timeouts
        timeout_group = QGroupBox("⏱️ Timeouts")
        timeout_layout = QGridLayout(timeout_group)
        timeout_layout.setSpacing(10)
        
        timeout_layout.addWidget(QLabel("Timeout hash:"), 0, 0)
        self.hash_timeout_spin = QSpinBox()
        self.hash_timeout_spin.setRange(30, 600)
        self.hash_timeout_spin.setValue(120)
        self.hash_timeout_spin.setSuffix(" sec")
        timeout_layout.addWidget(self.hash_timeout_spin, 0, 1)
        
        timeout_layout.addWidget(QLabel("Timeout comparaison:"), 1, 0)
        self.comparison_timeout_spin = QSpinBox()
        self.comparison_timeout_spin.setRange(5, 120)
        self.comparison_timeout_spin.setValue(30)
        self.comparison_timeout_spin.setSuffix(" sec")
        timeout_layout.addWidget(self.comparison_timeout_spin, 1, 1)
        
        layout.addWidget(timeout_group)
        
        # Presets - AVEC COULEURS
        presets_group = QGroupBox("🚀 Presets rapides")
        presets_layout = QHBoxLayout(presets_group)
        
        # PRESET RAPIDE - ROUGE
        fast_btn = QPushButton("⚡ Rapide")
        fast_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #A71E2A;
            }
        """)
        fast_btn.clicked.connect(lambda: self.apply_preset("fast"))
        
        # PRESET ÉQUILIBRÉ - BLEU
        balanced_btn = QPushButton("⚖️ Équilibré")
        balanced_btn.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #0056B3;
            }
        """)
        balanced_btn.clicked.connect(lambda: self.apply_preset("balanced"))
        
        # PRESET QUALITÉ - VERT
        quality_btn = QPushButton("🎯 Qualité")
        quality_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #1E7E34;
            }
        """)
        quality_btn.clicked.connect(lambda: self.apply_preset("quality"))
        
        presets_layout.addWidget(fast_btn)
        presets_layout.addWidget(balanced_btn)
        presets_layout.addWidget(quality_btn)
        
        layout.addWidget(presets_group)
        layout.addStretch()
        
        return tab

    # NOUVEAU: Méthodes de gestion des paramètres - VERSION CORRIGÉE
    def load_settings(self):
        """Charge les paramètres sauvegardés - AVEC BLOCAGE DES SIGNAUX"""
        try:
            # BLOQUE TOUS LES SIGNAUX pendant le chargement pour éviter la boucle
            self.block_settings_signals(True)
            
            # Groupe paramètres essentiels
            self.settings.beginGroup("parameters")
            
            # Seuil de similarité - VÉRIFICATION WIDGET
            if hasattr(self, 'threshold_spin'):
                threshold = self.settings.value("threshold", 90.0, type=float)
                self.threshold_spin.setValue(threshold)
            
            # Workers - VÉRIFICATION WIDGETS
            if hasattr(self, 'hash_workers_spin'):
                hash_workers = self.settings.value("hash_workers", 2, type=int)
                self.hash_workers_spin.setValue(hash_workers)
            
            if hasattr(self, 'comparison_workers_spin'):
                comparison_workers = self.settings.value("comparison_workers", 4, type=int)
                self.comparison_workers_spin.setValue(comparison_workers)
            
            # Batch size - VÉRIFICATION WIDGET
            if hasattr(self, 'batch_size_spin'):
                batch_size = self.settings.value("batch_size", 50, type=int)
                self.batch_size_spin.setValue(batch_size)
            
            # Timeouts - VÉRIFICATION WIDGETS
            if hasattr(self, 'hash_timeout_spin'):
                hash_timeout = self.settings.value("hash_timeout", 120, type=int)
                self.hash_timeout_spin.setValue(hash_timeout)
            
            if hasattr(self, 'comparison_timeout_spin'):
                comparison_timeout = self.settings.value("comparison_timeout", 30, type=int)
                self.comparison_timeout_spin.setValue(comparison_timeout)
            
            self.settings.endGroup()
            
            # Géométrie de la fenêtre
            self.settings.beginGroup("window")
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
            
            state = self.settings.value("state")
            if state:
                self.restoreState(state)
            self.settings.endGroup()
            
            logger.info("Paramètres chargés avec succès")
            
        except Exception as e:
            logger.error(f"Erreur chargement paramètres: {e}")
        finally:
            # RÉACTIVE LES SIGNAUX après le chargement
            self.block_settings_signals(False)
            
    def save_settings(self):
        """Sauvegarde les paramètres actuels - AVEC VÉRIFICATIONS"""
        try:
            # Groupe paramètres essentiels
            self.settings.beginGroup("parameters")
            
            # VÉRIFICATION EXISTENCE des widgets avant sauvegarde
            if hasattr(self, 'threshold_spin'):
                self.settings.setValue("threshold", self.threshold_spin.value())
            if hasattr(self, 'hash_workers_spin'):
                self.settings.setValue("hash_workers", self.hash_workers_spin.value())
            if hasattr(self, 'comparison_workers_spin'):
                self.settings.setValue("comparison_workers", self.comparison_workers_spin.value())
            if hasattr(self, 'batch_size_spin'):
                self.settings.setValue("batch_size", self.batch_size_spin.value())
            if hasattr(self, 'hash_timeout_spin'):
                self.settings.setValue("hash_timeout", self.hash_timeout_spin.value())
            if hasattr(self, 'comparison_timeout_spin'):
                self.settings.setValue("comparison_timeout", self.comparison_timeout_spin.value())
            
            self.settings.endGroup()
            
            # Géométrie de la fenêtre
            self.settings.beginGroup("window")
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("state", self.saveState())
            self.settings.endGroup()
            
            # Force la synchronisation
            self.settings.sync()
            
            logger.debug("Paramètres sauvegardés")
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde paramètres: {e}")
    
    def block_settings_signals(self, block):
        """Bloque/débloque les signaux des widgets de paramètres"""
        try:
            widgets = [
                'threshold_spin', 'hash_workers_spin', 'comparison_workers_spin',
                'batch_size_spin', 'hash_timeout_spin', 'comparison_timeout_spin'
            ]
            
            for widget_name in widgets:
                if hasattr(self, widget_name):
                    widget = getattr(self, widget_name)
                    widget.blockSignals(block)
                    
        except Exception as e:
            logger.error(f"Erreur blocage signaux: {e}")
            
    def connect_settings_signals(self):
        """Connecte les signaux pour sauvegarde automatique - AVEC VÉRIFICATIONS"""
        try:
            # VÉRIFICATION EXISTENCE avant connexion
            if hasattr(self, 'threshold_spin'):
                self.threshold_spin.valueChanged.connect(self.on_settings_changed)
            if hasattr(self, 'hash_workers_spin'):
                self.hash_workers_spin.valueChanged.connect(self.on_settings_changed)
            if hasattr(self, 'comparison_workers_spin'):
                self.comparison_workers_spin.valueChanged.connect(self.on_settings_changed)
            if hasattr(self, 'batch_size_spin'):
                self.batch_size_spin.valueChanged.connect(self.on_settings_changed)
            if hasattr(self, 'hash_timeout_spin'):
                self.hash_timeout_spin.valueChanged.connect(self.on_settings_changed)
            if hasattr(self, 'comparison_timeout_spin'):
                self.comparison_timeout_spin.valueChanged.connect(self.on_settings_changed)
            
            logger.debug("Signaux de paramètres connectés")
            
        except Exception as e:
            logger.error(f"Erreur connexion signaux paramètres: {e}")
    
    def on_settings_changed(self):
        """Appelé quand un paramètre change - sauvegarde automatique AVEC PROTECTION"""
        try:
            # ÉVITE les sauvegardes pendant le chargement initial
            if not hasattr(self, '_settings_loaded'):
                return
                
            self.save_settings()
            
            # Met à jour le status pour confirmer la sauvegarde (SANS bloquer)
            if hasattr(self, 'status_indicator'):
                self.status_indicator.update_status(
                    "💾", "Paramètres sauvegardés",
                    "#17A2B8", "#D1ECF1", "#17A2B8"
                )
                
                # Timer pour effacer le message après 1.5 secondes (plus court)
                QTimer.singleShot(1500, lambda: self.status_indicator.update_status(
                    "🎯", "Prêt à analyser",
                    "#28A745", "#D4EDDA", "#28A745"
                ))
                
        except Exception as e:
            logger.error(f"Erreur on_settings_changed: {e}")

    def create_action_buttons(self):
        """Crée les boutons d'action - VERSION CORRIGÉE avec couleurs et taille réduite"""
        group = QFrame()
        group.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 1px solid #DEE2E6;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 10, 12, 10)  # RÉDUIT: 15,15,15,15 → 12,10,12,10
        layout.setSpacing(8)  # RÉDUIT: 10 → 8
        
        # Boutons principaux - RÉDUITS et COLORÉS
        main_buttons_layout = QHBoxLayout()
        
        # BOUTON DÉMARRER - VERT FONCÉ
        self.analyze_btn = QPushButton("🔍 DÉMARRER")
        self.analyze_btn.setMinimumHeight(40)  # RÉDUIT: 50 → 40
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.analyze_btn.clicked.connect(self.start_analysis)
        
        # BOUTON ARRÊTER - ROUGE
        self.stop_btn = QPushButton("⏹️ ARRÊTER")
        self.stop_btn.setMinimumHeight(40)  # RÉDUIT: 50 → 40
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C82333;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_analysis)
        
        main_buttons_layout.addWidget(self.analyze_btn)
        main_buttons_layout.addWidget(self.stop_btn)
        layout.addLayout(main_buttons_layout)
        
        # Boutons secondaires - PLUS PETITS et COLORÉS
        secondary_layout = QHBoxLayout()
        
        # BOUTON STATISTIQUES - CYAN
        self.stats_btn = QPushButton("📊 Stats")
        self.stats_btn.setMaximumHeight(30)  # RÉDUIT
        self.stats_btn.setStyleSheet("""
            QPushButton {
                background-color: #17A2B8;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 11px;
                font-weight: bold;
                padding: 5px 8px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        self.stats_btn.clicked.connect(self.show_statistics)
        
        # BOUTON DOUBLONS EN ATTENTE - ORANGE
        self.pending_btn = QPushButton("📋 Doublons")
        self.pending_btn.setMaximumHeight(30)  # RÉDUIT
        self.pending_btn.setStyleSheet("""
            QPushButton {
                background-color: #FD7E14;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 11px;
                font-weight: bold;
                padding: 5px 8px;
            }
            QPushButton:hover {
                background-color: #E55A00;
            }
        """)
        self.pending_btn.clicked.connect(self.show_pending_duplicates)
        
        # BOUTON FERMER - GRIS FONCÉ
        self.close_btn = QPushButton("🚪 Fermer")
        self.close_btn.setMaximumHeight(30)  # RÉDUIT
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 11px;
                font-weight: bold;
                padding: 5px 8px;
            }
            QPushButton:hover {
                background-color: #545B62;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        
        secondary_layout.addWidget(self.stats_btn)
        secondary_layout.addWidget(self.pending_btn)
        secondary_layout.addWidget(self.close_btn)
        layout.addLayout(secondary_layout)
        
        # État initial
        self.analyze_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        return group

    def create_right_panel(self):
        """Crée le panneau de droite - VERSION OPTIMISÉE"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #DEE2E6;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)  # RÉDUIT: 15 → 12
        layout.setSpacing(10)  # RÉDUIT: 15 → 10
        
        # Indicateur de statut - PLUS PETIT
        self.status_indicator = StatusIndicator()
        layout.addWidget(self.status_indicator)
        
        # Progressions AMÉLIORÉES - PLUS COMPACTES
        self.file_progress = ModernProgressWidget("📊 Analyse des fichiers")
        layout.addWidget(self.file_progress)
        
        self.comparison_progress = ModernProgressWidget("🔍 Comparaisons")
        layout.addWidget(self.comparison_progress)
        
        # PLUS D'ESPACE pour le stretch pour équilibrer
        layout.addStretch(2)  # AJOUTÉ: facteur de stretch plus important
        
        return panel

    # NOUVELLES Méthodes pour synchronisation affichage
    def force_ui_update(self):
        """Force la mise à jour de l'interface utilisateur"""
        try:
            # Force le rafraîchissement de tous les widgets
            self.file_list_widget.update()
            self.status_indicator.update()
            self.file_progress.update()
            self.comparison_progress.update()
            
            # Process events pour éviter le gel
            QApplication.processEvents()
            
        except Exception as e:
            logger.error(f"Erreur force UI update: {e}")
    
    def start_ui_updates(self):
        """Démarre les mises à jour périodiques de l'UI"""
        self.status_update_timer.start(100)  # 10 FPS pour fluidité
    
    def stop_ui_updates(self):
        """Arrête les mises à jour périodiques de l'UI"""
        self.status_update_timer.stop()

    # Méthodes de gestion des fichiers - CORRIGÉES
    def add_files(self):
        """Ajoute des fichiers vidéo - VERSION CORRIGÉE"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner des fichiers vidéo",
            "",
            "Vidéos (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.m4v);;Tous (*.*)"
        )
        
        if files:
            existing_files = self.file_list_widget.get_files()
            new_files = [f for f in files if f not in existing_files]
            
            if new_files:
                # CORRECTION: Force la mise à jour immédiate
                count = self.file_list_widget.add_files(new_files)
                self.analyze_btn.setEnabled(len(self.file_list_widget.get_files()) > 1)
                
                # Met à jour les statuts selon le cache IMMÉDIATEMENT
                for file_path in new_files:
                    if self.video_hasher.has_hash(file_path):
                        status_updated = self.file_list_widget.update_file_status(file_path, "✅ En cache")
                        print(f"Statut cache mis à jour pour {os.path.basename(file_path)}: {status_updated}")
                    else:
                        status_updated = self.file_list_widget.update_file_status(file_path, "⏳ À analyser")
                        print(f"Statut à analyser mis à jour pour {os.path.basename(file_path)}: {status_updated}")
                
                # FORCE la mise à jour de l'affichage
                self.force_ui_update()
                
                self.status_indicator.update_status(
                    "✅", f"{count} fichier(s) ajouté(s)", 
                    "#28A745", "#D4EDDA", "#28A745"
                )

    def add_folder(self):
        """Ajoute un dossier de vidéos - VERSION CORRIGÉE"""
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier")
        
        if folder:
            video_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.m4v')
            existing_files = self.file_list_widget.get_files()
            
            found_files = []
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(video_extensions):
                        file_path = os.path.join(root, file)
                        if file_path not in existing_files:
                            found_files.append(file_path)
            
            if found_files:
                count = self.file_list_widget.add_files(found_files)
                self.analyze_btn.setEnabled(len(self.file_list_widget.get_files()) > 1)
                
                # Met à jour les statuts IMMÉDIATEMENT
                for file_path in found_files:
                    if self.video_hasher.has_hash(file_path):
                        self.file_list_widget.update_file_status(file_path, "✅ En cache")
                    else:
                        self.file_list_widget.update_file_status(file_path, "⏳ À analyser")
                
                # FORCE la mise à jour
                self.force_ui_update()
                
                self.status_indicator.update_status(
                    "📂", f"{count} fichier(s) trouvé(s) dans le dossier",
                    "#28A745", "#D4EDDA", "#28A745"
                )

    def clear_list(self):
        """Vide la liste des fichiers"""
        self.file_list_widget.clear_files()
        self.analyze_btn.setEnabled(False)
        self.status_indicator.update_status("🗑️", "Liste vidée")
        self.force_ui_update()

    def clear_cache(self):
        """Vide le cache"""
        try:
            self.video_hasher.clear_cache()
            
            # Met à jour les statuts
            files = self.file_list_widget.get_files()
            for file_path in files:
                self.file_list_widget.update_file_status(file_path, "⏳ À analyser")
            
            self.force_ui_update()
            
            self.status_indicator.update_status(
                "🧹", "Cache vidé - tous les fichiers à réanalyser",
                "#FFC107", "#FFF3CD", "#FFC107"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de vider le cache: {e}")

    # Méthodes de configuration
    def apply_preset(self, preset_type):
        """Applique un preset de configuration - AVEC SAUVEGARDE ET BLOCAGE"""
        try:
            # BLOQUE les signaux pour éviter les sauvegardes répétées
            self.block_settings_signals(True)
            
            if preset_type == "fast":
                if hasattr(self, 'threshold_spin'): self.threshold_spin.setValue(85.0)
                if hasattr(self, 'hash_workers_spin'): self.hash_workers_spin.setValue(4)
                if hasattr(self, 'comparison_workers_spin'): self.comparison_workers_spin.setValue(6)
                if hasattr(self, 'batch_size_spin'): self.batch_size_spin.setValue(100)
                if hasattr(self, 'hash_timeout_spin'): self.hash_timeout_spin.setValue(60)
                if hasattr(self, 'comparison_timeout_spin'): self.comparison_timeout_spin.setValue(15)
                message = "Preset RAPIDE appliqué et sauvegardé"
                
            elif preset_type == "balanced":
                if hasattr(self, 'threshold_spin'): self.threshold_spin.setValue(90.0)
                if hasattr(self, 'hash_workers_spin'): self.hash_workers_spin.setValue(2)
                if hasattr(self, 'comparison_workers_spin'): self.comparison_workers_spin.setValue(4)
                if hasattr(self, 'batch_size_spin'): self.batch_size_spin.setValue(50)
                if hasattr(self, 'hash_timeout_spin'): self.hash_timeout_spin.setValue(120)
                if hasattr(self, 'comparison_timeout_spin'): self.comparison_timeout_spin.setValue(30)
                message = "Preset ÉQUILIBRÉ appliqué et sauvegardé"
                
            elif preset_type == "quality":
                if hasattr(self, 'threshold_spin'): self.threshold_spin.setValue(95.0)
                if hasattr(self, 'hash_workers_spin'): self.hash_workers_spin.setValue(1)
                if hasattr(self, 'comparison_workers_spin'): self.comparison_workers_spin.setValue(2)
                if hasattr(self, 'batch_size_spin'): self.batch_size_spin.setValue(20)
                if hasattr(self, 'hash_timeout_spin'): self.hash_timeout_spin.setValue(300)
                if hasattr(self, 'comparison_timeout_spin'): self.comparison_timeout_spin.setValue(60)
                message = "Preset QUALITÉ appliqué et sauvegardé"
            
            # RÉACTIVE les signaux
            self.block_settings_signals(False)
            
            # SAUVEGARDE UNE SEULE FOIS après tout le preset
            self.save_settings()
            
            # Message de confirmation
            if hasattr(self, 'status_indicator'):
                icon = {"fast": "⚡", "balanced": "⚖️", "quality": "🎯"}[preset_type]
                self.status_indicator.update_status(icon, message)
                
        except Exception as e:
            logger.error(f"Erreur application preset {preset_type}: {e}")
            # Réactive les signaux même en cas d'erreur
            self.block_settings_signals(False)

    def get_analysis_config(self):
        """Retourne la configuration actuelle"""
        return {
            'threshold': self.threshold_spin.value(),
            'hash_workers': self.hash_workers_spin.value(),
            'comparison_workers': self.comparison_workers_spin.value(),
            'batch_size': self.batch_size_spin.value(),
            'hash_timeout': self.hash_timeout_spin.value(),
            'comparison_timeout': self.comparison_timeout_spin.value()
        }

    # Méthodes d'analyse - CORRIGÉES
    def start_analysis(self):
        """Démarre l'analyse - VERSION CORRIGÉE"""
        files = self.file_list_widget.get_files()
        
        if len(files) < 2:
            QMessageBox.warning(self, "Attention", "Il faut au moins 2 fichiers pour détecter des doublons")
            return

        valid_files = [f for f in files if os.path.exists(f)]
        if len(valid_files) < 2:
            QMessageBox.warning(self, "Erreur", "Pas assez de fichiers valides")
            return

        self.start_time = time.time()
        self.set_analysis_mode(True)
        self.duplicate_processing_stopped = False
        
        # DÉMARRE les mises à jour UI
        self.start_ui_updates()
        
        self.status_indicator.update_status(
            "📄", "Analyse en cours...",
            "#007BFF", "#CCE5FF", "#007BFF"
        )
        
        # Identifie les fichiers à traiter
        files_to_hash = [f for f in valid_files if not self.video_hasher.has_hash(f)]
        
        if files_to_hash:
            self.start_hash_analysis(files_to_hash, valid_files)
        else:
            QTimer.singleShot(100, lambda: self.start_comparison_analysis(valid_files))

    def start_hash_analysis(self, files_to_hash, all_files):
        """Démarre l'analyse des hashs - VERSION CORRIGÉE"""
        config = self.get_analysis_config()
        
        # AFFICHAGE CORRECT dès le début
        self.file_progress.update_progress(0, len(all_files), "Calcul des empreintes...")
        self.file_progress.set_status("Démarrage", "#FFC107")
        
        # Met à jour les statuts pour les nouveaux fichiers
        for file_path in files_to_hash:
            self.file_list_widget.update_file_status(file_path, "📄 En cours...")
        
        self.hash_worker = ParallelHashWorker(
            all_files, self.video_hasher, config['hash_workers'], config['hash_timeout']
        )
        
        # CONNEXIONS AMÉLIORÉES avec logs
        self.hash_worker.progress.connect(self.update_file_progress)
        self.hash_worker.finished.connect(lambda: self.hash_analysis_finished(all_files))
        self.hash_worker.error.connect(self.handle_error)
        self.hash_worker.file_processed.connect(self.update_file_processed)
        self.hash_worker.current_file.connect(self.update_current_file_display)
        self.hash_worker.progress_details.connect(self.update_hash_progress_details)
        
        logger.info(f"Démarrage analyse hash: {len(all_files)} fichiers total, {len(files_to_hash)} à traiter")
        self.hash_worker.start()

    def start_comparison_analysis(self, files):
        """Démarre l'analyse des comparaisons"""
        config = self.get_analysis_config()
        self.potential_duplicates = []
        
        total_possible_pairs = len(files) * (len(files) - 1) // 2
        self.status_indicator.update_status(
            "🔍", f"Préparation de {total_possible_pairs:,} comparaisons possibles..."
        )
        
        # AFFICHAGE CORRECT dès le début
        self.comparison_progress.update_progress(0, total_possible_pairs, "Préparation...")
        self.comparison_progress.set_status("Préparation", "#FFC107")
        
        self.comparison_worker = OptimizedComparisonWorker(files, self.video_hasher, config['threshold'], config)
        
        # CONNEXIONS AMÉLIORÉES
        self.comparison_worker.progress.connect(self.update_comparison_progress)
        self.comparison_worker.finished.connect(self.comparison_finished)
        self.comparison_worker.duplicate_found.connect(self.add_duplicate)
        self.comparison_worker.error.connect(self.handle_error)
        self.comparison_worker.status_update.connect(self.update_comparison_status)
        self.comparison_worker.total_comparisons_signal.connect(self.set_comparison_total)
        self.comparison_worker.comparison_details.connect(self.update_comparison_details)
        
        self.comparison_worker.start()

    def hash_analysis_finished(self, all_files):
        """Appelé quand l'analyse des hashs est terminée"""
        failed_files = []
        
        for file_path in all_files:
            if self.video_hasher.has_hash(file_path):
                self.file_list_widget.update_file_status(file_path, "✅ Analysé")
            else:
                self.file_list_widget.update_file_status(file_path, "❌ Échec")
                failed_files.append(file_path)
        
        self.file_progress.set_status("Terminé", "#28A745")
        self.failed_files = failed_files
        
        # Force la mise à jour de l'affichage
        self.force_ui_update()
        
        self.start_comparison_analysis(all_files)

    def comparison_finished(self):
        """Appelé quand toutes les comparaisons sont terminées"""
        total_time = time.time() - self.start_time
        
        self.comparison_progress.set_status("Terminé", "#28A745")
        
        # ARRÊTE les mises à jour UI
        self.stop_ui_updates()
        
        failed_files = getattr(self, 'failed_files', [])
        duplicates_count = len(self.potential_duplicates)
        
        if duplicates_count > 0:
            self.status_indicator.update_status(
                "🎯", f"Analyse terminée! {duplicates_count} doublon(s) détecté(s)",
                "#28A745", "#D4EDDA", "#28A745"
            )
            
            self.potential_duplicates.sort(key=lambda x: x[2], reverse=True)
            QTimer.singleShot(1000, self.show_next_duplicate)  # Délai pour voir le message
        else:
            self.status_indicator.update_status(
                "✅", f"Analyse terminée - Aucun doublon détecté",
                "#28A745", "#D4EDDA", "#28A745"
            )
            QMessageBox.information(
                self, "Analyse terminée",
                f"Aucun doublon détecté avec un seuil de {self.threshold_spin.value()}%\n\n"
                f"Temps total: {total_time:.1f} secondes"
            )
        
        self.set_analysis_mode(False)

    def stop_analysis(self):
        """Arrête l'analyse en cours"""
        reply = QMessageBox.question(
            self, "Confirmation", 
            "Voulez-vous vraiment arrêter l'analyse en cours ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.hash_worker and self.hash_worker.isRunning():
                self.hash_worker.stop()
                self.hash_worker.wait()
                
            if self.comparison_worker and self.comparison_worker.isRunning():
                self.comparison_worker.stop()
                self.comparison_worker.wait()
            
            # Arrête aussi le traitement des doublons et les mises à jour UI
            self.duplicate_processing_stopped = True
            self.stop_ui_updates()
            
            self.set_analysis_mode(False)
            self.status_indicator.update_status(
                "⏹️", "Analyse arrêtée par l'utilisateur",
                "#DC3545", "#F8D7DA", "#DC3545"
            )

    def set_analysis_mode(self, analyzing):
        """Configure l'interface selon le mode d'analyse"""
        self.analyze_btn.setEnabled(not analyzing and len(self.file_list_widget.get_files()) > 1)
        self.stop_btn.setEnabled(analyzing)
        self.config_tabs.setEnabled(not analyzing)
        
        if analyzing:
            self.repaint()

    # Méthodes de gestion des doublons - CORRIGÉES
    def show_next_duplicate(self):
        """Affiche le prochain doublon à traiter - Version corrigée"""
        if not self.potential_duplicates or self.duplicate_processing_stopped:
            if not self.duplicate_processing_stopped:
                self.status_indicator.update_status(
                    "✅", "Tous les doublons ont été traités",
                    "#28A745", "#D4EDDA", "#28A745"
                )
            return

        duplicate_data = self.potential_duplicates[0]
        
        if len(duplicate_data) == 4:
            file1, file2, similarity, dup_id = duplicate_data
        else:
            file1, file2, similarity = duplicate_data
            dup_id = None
        
        # Vérifie que les fichiers existent
        if not os.path.exists(file1) or not os.path.exists(file2):
            self.potential_duplicates.pop(0)
            self.show_next_duplicate()
            return
        
        # Met à jour le statut pour indiquer qu'on traite les doublons
        remaining = len(self.potential_duplicates)
        self.status_indicator.update_status(
            "🔍", f"Traitement doublon {remaining} - Similarité: {similarity:.1f}%",
            "#FF9800", "#FFF3E0", "#FF9800"
        )
        
        # Affiche le dialogue de comparaison
        dialog = ComparisonDialog(file1, file2, similarity, self)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted and dialog.result:
            self.handle_duplicate_choice(dialog.result, file1, file2, dup_id)
        elif result == QDialog.DialogCode.Rejected or dialog.result == "quit":
            # L'utilisateur a choisi de quitter
            self.duplicate_processing_stopped = True
            self.status_indicator.update_status(
                "⏹️", "Traitement des doublons arrêté",
                "#DC3545", "#F8D7DA", "#DC3545"
            )
            return
        
        self.potential_duplicates.pop(0)
        
        # Vérifie si on doit continuer
        if not self.duplicate_processing_stopped:
            self.show_next_duplicate()

    def handle_duplicate_choice(self, choice, file1, file2, dup_id=None):
        """Gère le choix de l'utilisateur pour un doublon - Version corrigée"""
        try:
            if choice == "keep_left":
                send2trash(file2)
                self.file_list_widget.update_file_status(file2, "🗑️ Supprimé")
                logger.info(f"Fichier supprimé: {os.path.basename(file2)}")
                
            elif choice == "keep_right":
                send2trash(file1)
                self.file_list_widget.update_file_status(file1, "🗑️ Supprimé")
                logger.info(f"Fichier supprimé: {os.path.basename(file1)}")
                
            elif choice == "ignore_perm":
                # CORRECTION: Enregistre bien la paire comme ignorée DÉFINITIVEMENT
                self.video_hasher.add_ignored_pair(file1, file2)
                logger.info(f"Paire ignorée définitivement: {os.path.basename(file1)} <-> {os.path.basename(file2)}")
                
            elif choice == "ignore_temp":
                # Ignore temporairement (ne fait rien, juste passe au suivant)
                logger.info(f"Paire ignorée temporairement: {os.path.basename(file1)} <-> {os.path.basename(file2)}")
                
            # Met à jour le statut dans la DB si dup_id existe
            if dup_id:
                action_map = {
                    "keep_left": "kept_left",
                    "keep_right": "kept_right", 
                    "ignore_perm": "ignored_permanently",
                    "ignore_temp": "ignored_temporarily"
                }
                self.video_hasher.db.update_duplicate_status(dup_id, "processed", action_map.get(choice, choice))
            
            # Force la mise à jour de l'affichage
            self.force_ui_update()
                
        except Exception as e:
            logger.error(f"Erreur action doublon: {e}")
            QMessageBox.critical(self, "Erreur", f"Erreur lors du traitement: {e}")

    def add_duplicate(self, file1, file2, similarity):
        """Ajoute un doublon détecté"""
        self.potential_duplicates.append((file1, file2, similarity))
        self.video_hasher.db.store_found_duplicate(file1, file2, similarity)
        
        current_count = len(self.potential_duplicates)
        self.status_indicator.update_status(
            "🔍", f"Analyse en cours... {current_count} doublon(s) trouvé(s)"
        )

    # NOUVELLES Méthodes de mise à jour de l'interface - CORRIGÉES
    def update_file_progress(self, current):
        """Met à jour la progression des fichiers - VERSION CORRIGÉE"""
        try:
            max_files = self.file_progress.progress_bar.maximum()
            if max_files > 0:
                self.file_progress.update_progress(current, max_files)
                
                if self.start_time and current > 0:
                    elapsed = time.time() - self.start_time
                    speed = current / elapsed if elapsed > 0 else 0
                    self.file_progress.set_speed(speed)
                    
                    if speed > 0 and max_files > current:
                        remaining = (max_files - current) / speed
                        self.file_progress.set_time_remaining(remaining)
                        
                print(f"File progress: {current}/{max_files}")
        except Exception as e:
            logger.error(f"Erreur update_file_progress: {e}")

    def update_comparison_progress(self, current):
        """Met à jour la progression des comparaisons - VERSION CORRIGÉE"""
        try:
            max_comparisons = self.comparison_progress.progress_bar.maximum()
            if max_comparisons > 0:
                self.comparison_progress.update_progress(current, max_comparisons)
                print(f"Comparison progress: {current}/{max_comparisons}")
        except Exception as e:
            logger.error(f"Erreur update_comparison_progress: {e}")

    def update_current_file_display(self, file_info):
        """Met à jour l'affichage du fichier en cours - VERSION CORRIGÉE"""
        try:
            self.file_progress.set_status(f"{file_info}", "#007BFF")
            print(f"Current file: {file_info}")
        except Exception as e:
            logger.error(f"Erreur update_current_file_display: {e}")

    def update_file_processed(self, file_path, success):
        """Met à jour le statut d'un fichier traité - VERSION CORRIGÉE"""
        try:
            if success:
                updated = self.file_list_widget.update_file_status(file_path, "✅ Analysé")
            else:
                updated = self.file_list_widget.update_file_status(file_path, "❌ Échec")
            
            print(f"File processed: {os.path.basename(file_path)} - Success: {success} - Updated: {updated}")
        except Exception as e:
            logger.error(f"Erreur update_file_processed: {e}")

    def update_comparison_status(self, status):
        """Met à jour le statut des comparaisons"""
        try:
            self.status_indicator.update_status("🔍", status)
            print(f"Comparison status: {status}")
        except Exception as e:
            logger.error(f"Erreur update_comparison_status: {e}")

    def set_comparison_total(self, total):
        """Met à jour le nombre total de comparaisons - VERSION CORRIGÉE"""
        try:
            self.comparison_progress.progress_bar.setMaximum(total)
            self.comparison_progress.update_progress(0, total, "Comparaisons en cours...")
            self.comparison_progress.set_status("Comparaisons", "#007BFF")
            print(f"Comparison total set: {total}")
        except Exception as e:
            logger.error(f"Erreur set_comparison_total: {e}")

    def update_hash_progress_details(self, current, total, filename):
        """Met à jour les détails de progression du hachage - VERSION CORRIGÉE"""
        try:
            self.file_progress.update_progress(current, total, f"{current}/{total}")
            short_filename = filename[:30] + "..." if len(filename) > 30 else filename
            self.file_progress.set_status(f"📄 {short_filename}", "#007BFF")
            print(f"Hash progress: {current}/{total} - {filename}")
        except Exception as e:
            logger.error(f"Erreur update_hash_progress_details: {e}")

    def update_comparison_details(self, current, total, name1, name2):
        """Met à jour les détails de progression des comparaisons - VERSION CORRIGÉE"""
        try:
            self.comparison_progress.update_progress(current, total, f"{current}/{total}")
            short_names = f"{name1[:15]}...↔{name2[:15]}..." if len(name1) > 15 or len(name2) > 15 else f"{name1}↔{name2}"
            self.comparison_progress.set_status(f"🔍 {short_names}", "#007BFF")
            print(f"Comparison details: {current}/{total} - {name1} vs {name2}")
        except Exception as e:
            logger.error(f"Erreur update_comparison_details: {e}")

    def handle_error(self, error_msg):
        """Gère les erreurs"""
        self.stop_ui_updates()
        QMessageBox.critical(self, "Erreur", f"Erreur pendant l'analyse: {error_msg}")
        self.set_analysis_mode(False)
        self.status_indicator.update_status(
            "❌", "Erreur pendant l'analyse",
            "#DC3545", "#F8D7DA", "#DC3545"
        )

    # Méthodes utilitaires
    def auto_cleanup_database(self):
        """Nettoie automatiquement la base de données"""
        try:
            removed = self.video_hasher.db.cleanup_missing_files()
            if removed > 0:
                logger.info(f"Nettoyage automatique: {removed} fichiers manquants supprimés")
        except Exception as e:
            logger.error(f"Erreur nettoyage automatique: {e}")

    def show_statistics(self):
        """Affiche les statistiques"""
        try:
            stats = self.video_hasher.get_statistics()
            cache_stats = self.video_hasher.get_cache_stats()
            
            message = f"""📊 STATISTIQUES

🎬 FICHIERS ANALYSÉS
   Nombre total: {stats.get('files_count', 0):,}
   Taille base: {stats.get('db_size_kb', 0):.1f} KB

🔍 COMPARAISONS
   Total: {stats.get('comparisons_count', 0):,}
   Paires ignorées: {stats.get('ignored_count', 0):,}

💾 CACHE MÉMOIRE
   Hashs: {cache_stats.get('hash_cache_size', 0):,}
   Comparaisons: {cache_stats.get('comparison_cache_size', 0):,}

⏱️ TEMPS ÉCONOMISÉ
   Estimation: {stats.get('time_saved_seconds', 0):.0f} secondes"""
            
            QMessageBox.information(self, "Statistiques", message)
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de récupérer les statistiques: {e}")

    def show_pending_duplicates(self):
        """Affiche les doublons en attente"""
        try:
            pending = self.video_hasher.db.get_pending_duplicates()
            
            if not pending:
                QMessageBox.information(self, "Aucun doublon", "Aucun doublon en attente.")
                return
            
            reply = QMessageBox.question(
                self, "Doublons en attente",
                f"Il y a {len(pending)} doublons en attente.\n\n"
                f"Voulez-vous reprendre le traitement ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.potential_duplicates = list(pending)
                self.duplicate_processing_stopped = False  # Reset du flag
                self.status_indicator.update_status(
                    "📋", f"Reprise de {len(pending)} doublons en attente"
                )
                self.show_next_duplicate()
                
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de récupérer les doublons: {e}")

    def cleanup_resources(self):
        """Nettoie toutes les ressources utilisées"""
        try:
            # Arrête les timers
            self.stop_ui_updates()
            
            # Arrête les workers s'ils tournent
            if self.hash_worker and self.hash_worker.isRunning():
                self.hash_worker.stop()
                self.hash_worker.wait()
                self.hash_worker = None
                
            if self.comparison_worker and self.comparison_worker.isRunning():
                self.comparison_worker.stop()
                self.comparison_worker.wait()
                self.comparison_worker = None
            
            logger.info("Ressources nettoyées avec succès")
            
        except Exception as e:
            logger.error(f"Erreur nettoyage ressources: {e}")

    def closeEvent(self, event):
        """Gère la fermeture de l'application - AVEC SAUVEGARDE"""
        try:
            # Vérifie s'il y a des workers en cours
            if ((self.hash_worker and self.hash_worker.isRunning()) or 
                (self.comparison_worker and self.comparison_worker.isRunning())):
                
                reply = QMessageBox.question(
                    self, "Confirmation",
                    "Une analyse est en cours. Voulez-vous vraiment quitter ?\n\n"
                    "Les résultats déjà calculés seront conservés en cache.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Arrête proprement les workers
                    self.cleanup_resources()
                    # NOUVEAU: Sauvegarde les paramètres avant de fermer
                    self.save_settings()
                    event.accept()
                else:
                    event.ignore()
                    return
            else:
                # NOUVEAU: Sauvegarde les paramètres avant de fermer
                self.save_settings()
                event.accept()
            
            # Émet le signal de fermeture
            self.closed.emit()
            
        except Exception as e:
            logger.error(f"Erreur fermeture application: {e}")
            # Force la fermeture même en cas d'erreur
            # NOUVEAU: Essaie de sauvegarder même en cas d'erreur
            try:
                self.save_settings()
            except:
                pass
            event.accept()
            self.closed.emit()