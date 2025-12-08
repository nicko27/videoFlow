# Architecture Existante du Plugin Duplicate Finder

**Date**: 2025-12-07
**But**: Documentation complète de l'existant pour reprendre le développement après compactage

---

## 📁 STRUCTURE DES FICHIERS

```
src/plugins/duplicate_finder/
├── __init__.py
├── plugin.py                          # Point d'entrée du plugin
├── window.py                          # Fenêtre principale (legacy)
├── main_window.py                     # Fenêtre principale (2087 lignes)
├── database_manager.py                # Gestionnaire DB (2766 lignes)
├── verification_pipeline.py           # Pipeline multi-méthodes (814 lignes)
├── subsequence_detector.py            # Détection sous-séquences
├── video_hasher.py                    # Hash perceptuel vidéos
├── audio_config.py                    # Config audio-first
├── audio_fingerprinting.py            # Empreintes audio
├── lsh_index.py                       # LSH pour audio
├── multi_resolution_comparator.py     # Comparaison multi-résolution
├── metadata_filter.py                 # Filtre métadonnées
│
├── handlers/                          # Logique métier
│   ├── __init__.py
│   ├── file_handler.py                # Gestion fichiers
│   ├── analysis_handler.py            # Orchestration analyse
│   ├── duplicate_handler.py           # Gestion doublons
│   └── audio_first_handler.py         # Workflow audio-first
│
├── managers/                          # Gestionnaires d'état
│   ├── __init__.py
│   └── settings_manager.py            # Paramètres utilisateur
│
├── workers/                           # Threads PyQt6
│   ├── hash_worker.py                 # Calcul hash parallèle
│   ├── comparison_worker.py           # Comparaison parallèle
│   ├── scene_worker.py                # Détection scènes
│   ├── subsequence_worker.py          # Détection sous-séquences
│   ├── audio_worker.py                # Extraction audio
│   └── audio_comparison_worker.py     # Comparaison audio
│
├── ui/                                # Interfaces utilisateur
│   ├── panels.py                      # Création panels UI (1500+ lignes)
│   └── pipeline_config_widget.py      # Config pipeline (si existe)
│
├── analysis/                          # Méthodes d'analyse
│   ├── video_analysis_methods.py      # Méthodes de comparaison vidéo
│   └── subsequence_verification.py    # Vérification sous-séquences
│
├── progress_widgets.py                # Widgets de progression (2200+ lignes)
├── comparison_dialog.py               # Dialogue comparaison
├── subsequence_comparison_dialog.py   # Dialogue sous-séquences
└── advanced_progress_dialog.py        # Dialogue progression avancé
```

---

## 🗄️ ARCHITECTURE BASE DE DONNÉES

### Connection Pool Pattern

**Fichier**: `database_manager.py`

```python
# La DB utilise un pool de connexions pour le multi-threading
class ConnectionPool:
    """Pool de connexions SQLite thread-safe"""

class VideoDatabase:
    def __init__(self, db_path='video_duplicates.db'):
        self.db_path = db_path
        self.connection_pool = ConnectionPool(db_path, pool_size=None)  # Auto-sized

    # Pattern d'utilisation:
    def some_method(self):
        with self.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")
            results = cursor.fetchall()
            conn.commit()  # Si modification
        return results
```

### Tables Principales Existantes

```sql
-- Fichiers vidéo
video_files (
    id, file_path UNIQUE, file_name, file_size, modification_time,
    duration, width, height, hash_method, hash_data BLOB,
    frames_indices, audio_fingerprint BLOB,
    created_at, updated_at
)

-- Comparaisons effectuées (cache)
comparisons (
    id, file1_id FK, file2_id FK, similarity,
    comparison_method, is_early_exit, computation_time,
    created_at, UNIQUE(file1_id, file2_id)
)

-- Paires ignorées par l'utilisateur
ignored_pairs (
    id, file1_id FK, file2_id FK, reason,
    ignore_type ('permanent'/'session'/'temporary'),
    created_at, UNIQUE(file1_id, file2_id)
)

-- Doublons détectés
found_duplicates (
    id, file1_id FK, file2_id FK, similarity,
    status ('pending'/'confirmed'/'rejected'),
    action_taken, detected_at, processed_at
)

-- Sous-séquences détectées
video_subsequences (
    id, short_video_id FK, long_video_id FK, match_ratio,
    start_frame_idx, confidence,
    status, action_taken, detected_at
)

-- Hash denses (frame-by-frame pour sous-séquences)
dense_hashes (
    id, video_id FK UNIQUE, dense_hash BLOB,
    sample_interval, duration, num_frames,
    modification_time, file_size,
    params_hash, params_json, computed_at
)

-- Empreintes LSH audio (Level 1)
lsh_fingerprints (
    id, video_id FK UNIQUE, fingerprint BLOB,
    signature_bands, n_bands, n_rows,
    params_hash, params_json, computed_at, fingerprint_version
)

-- Cache vérification (Strategy 3)
verification_cache (
    id, short_video_id FK, long_video_id FK,
    short_mtime, long_mtime, short_size, long_size,
    start_time, duration, sequence_score,
    config_hash, num_samples, warmup_seconds, execution_time,
    accepted BOOLEAN, scene_cuts_score, dct_score,
    rejection_reason, verification_date,
    UNIQUE(short_video_id, long_video_id, start_time)
)

-- Configurations de pipeline
pipeline_configs (
    id, config_hash UNIQUE, mode, config_json, created_at
)

-- Configurations de méthodes
method_configs (
    id, method_name, params_hash, params_json,
    created_at, UNIQUE(method_name, params_hash)
)

-- Exécutions de vérification (runs individuels)
verification_runs (
    id, pipeline_config_id FK, short_video_id FK, long_video_id FK,
    start_time, duration, sequence_score,
    accepted BOOLEAN, total_time, run_label, debug_flag,
    created_at
)

-- Résultats par méthode
verification_method_results (
    id, run_id FK, method_config_id FK, method_name,
    accepted, primary_score, threshold, execution_time,
    extra_json
)

-- Labels de debug (ground truth)
debug_labels (
    id, short_video_id FK, long_video_id FK,
    label ('positive'/'negative'), notes,
    created_at, UNIQUE(short_video_id, long_video_id, label)
)

-- Hash vidéo (cache général)
video_hashes (
    id, video_id FK, method_name, params_hash, params_json,
    hash_blob BLOB, modification_time, file_size,
    computed_at, UNIQUE(video_id, method_name, params_hash)
)
```

### Méthodes DB Utiles Existantes

```python
class VideoDatabase:

    # ═══════════════════════════════════════════════════════════
    # GESTION FICHIERS
    # ═══════════════════════════════════════════════════════════

    def add_file(self, file_path: str, metadata: Dict) -> int:
        """Ajoute un fichier à la DB, retourne file_id"""

    def get_file_id(self, file_path: str) -> Optional[int]:
        """Récupère l'ID d'un fichier par son chemin"""

    def get_or_create_file_id(self, file_path: str) -> int:
        """Récupère ou crée un file_id"""

    # ═══════════════════════════════════════════════════════════
    # CACHE COMPARAISONS
    # ═══════════════════════════════════════════════════════════

    def get_cached_comparison(self, file1_id: int, file2_id: int) -> Optional[float]:
        """Récupère une comparaison cachée"""

    def cache_comparison(self, file1_id: int, file2_id: int, similarity: float):
        """Cache une comparaison"""

    # ═══════════════════════════════════════════════════════════
    # VERIFICATION CACHE (Pipeline)
    # ═══════════════════════════════════════════════════════════

    def get_cached_verification(
        self,
        short_video: str,
        long_video: str,
        start_time: float,
        config_hash: str = None
    ) -> Optional[Dict]:
        """Récupère résultat de vérification caché"""

    def store_verification_result(
        self,
        short_video: str,
        long_video: str,
        start_time: float,
        duration: float,
        sequence_score: float,
        result: Dict
    ):
        """Stocke un résultat de vérification"""

    # ═══════════════════════════════════════════════════════════
    # PIPELINE CONFIGS
    # ═══════════════════════════════════════════════════════════

    def upsert_pipeline_config(
        self,
        config_hash: str,
        mode: str,
        config_json: str
    ) -> int:
        """Insert ou update une config pipeline, retourne ID"""

    def upsert_method_config(
        self,
        method_name: str,
        params_hash: str,
        params_json: str
    ) -> int:
        """Insert ou update une config méthode, retourne ID"""

    def store_verification_run(
        self,
        pipeline_config_id: int,
        short_video_path: str,
        long_video_path: str,
        start_time: float,
        duration: float,
        sequence_score: float,
        accepted: bool,
        total_time: float,
        run_label: str = None,
        debug_flag: bool = False
    ) -> int:
        """Stocke un run de vérification, retourne run_id"""

    def store_verification_method_result(
        self,
        run_id: int,
        method_name: str,
        accepted: bool,
        primary_score: float,
        threshold: float,
        execution_time: float,
        rejection_reason: str = None,
        extra_json: str = None,
        method_config_id: int = None
    ):
        """Stocke le résultat d'une méthode"""

    # ═══════════════════════════════════════════════════════════
    # DEBUG LABELS
    # ═══════════════════════════════════════════════════════════

    def upsert_debug_label(
        self,
        short_video: str,
        long_video: str,
        label: str,
        notes: str = None
    ):
        """Ajoute ou met à jour un label de debug (ground truth)"""

    # ═══════════════════════════════════════════════════════════
    # IGNORED PAIRS
    # ═══════════════════════════════════════════════════════════

    def add_ignored_pair(
        self,
        file1_path: str,
        file2_path: str,
        ignore_type: str = 'permanent',
        reason: str = 'user_choice'
    ):
        """Ajoute une paire à ignorer"""

    def is_pair_ignored(self, file1_path: str, file2_path: str) -> bool:
        """Vérifie si une paire est ignorée"""
```

---

## 🎨 ARCHITECTURE UI (PyQt6)

### Pattern de Création de Widgets

**Fichier**: `ui/panels.py`

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QGroupBox, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QTextEdit, QListWidget, QFileDialog, QLineEdit,
    QScrollArea, QFrame, QTabWidget, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

# Pattern standard pour créer un panel:
class UIPanels:
    """Classe statique pour créer les panels UI"""

    @staticmethod
    def create_some_tab(callbacks: Dict) -> QWidget:
        """
        Crée un onglet.

        Args:
            callbacks: Dict avec les callbacks {'button_name': fonction}

        Returns:
            QWidget configuré
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Créer un groupe
        group = QGroupBox("Titre du Groupe")
        group_layout = QVBoxLayout(group)

        # Ajouter des widgets
        button = QPushButton("Action")
        button.clicked.connect(callbacks.get('action', lambda: None))
        group_layout.addWidget(button)

        layout.addWidget(group)
        layout.addStretch()

        # Stocker références si besoin
        tab.some_widget = button

        return tab
```

### Barres de Progression Existantes

**Fichier**: `progress_widgets.py`

```python
class ModernProgressWidget(QFrame):
    """
    Barre de progression moderne avec pourcentage et temps.

    Méthodes principales:
        update_progress(current: int, total: int, label: str = None)
        set_status(status: str, color: str)
        set_speed(speed: float)  # fichiers/sec
        set_time_remaining(seconds: float)
        reset()

    Attributs:
        progress_bar: QProgressBar
        percentage_label: QLabel
        status_label: QLabel
        speed_label: QLabel
        time_label: QLabel
    """

    def __init__(self, title: str = "Progression", parent=None):
        super().__init__(parent)
        # ... setup UI

    def update_progress(self, current: int, total: int, label: str = None):
        """
        Met à jour la progression.

        Args:
            current: Valeur actuelle
            total: Valeur totale
            label: Label optionnel à afficher
        """
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.percentage_label.setText(f"{percentage}%")

            if label:
                self.status_label.setText(label)

    def set_status(self, status: str, color: str):
        """Change le status et sa couleur"""
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"color: {color};")

    def reset(self):
        """Réinitialise la barre"""
        self.progress_bar.setValue(0)
        self.percentage_label.setText("0%")


class StatusIndicator(QFrame):
    """
    Indicateur de status coloré avec icône.

    Méthodes:
        update_status(icon: str, text: str, color: str, bg_color: str, border_color: str)
    """

    def update_status(self, icon: str, text: str, color: str, bg_color: str, border_color: str):
        """
        Met à jour le status.

        Args:
            icon: Emoji ou symbole (ex: "🎵", "✓", "⚠️")
            text: Texte du status
            color: Couleur du texte (hex)
            bg_color: Couleur de fond (hex)
            border_color: Couleur de bordure (hex)
        """


class FileListWidget(QFrame):
    """
    Liste de fichiers avec compteur.

    Méthodes:
        add_file(file_path: str)
        remove_file(file_path: str)
        clear_files()
        get_files() -> List[str]
        get_file_count() -> int
    """

    def add_file(self, file_path: str):
        """Ajoute un fichier à la liste"""

    def get_files(self) -> List[str]:
        """Retourne la liste des fichiers"""
```

### Pattern de QThread pour Workers

**Fichier**: `workers/comparison_worker.py` (exemple)

```python
from PyQt6.QtCore import QThread, pyqtSignal

class SomeWorker(QThread):
    """
    Worker thread pour opération longue.

    Signals:
        progress: pyqtSignal(int, int)  # current, total
        finished: pyqtSignal()
        error: pyqtSignal(str)
        result_ready: pyqtSignal(object)  # résultat
    """

    # Déclarer les signaux au niveau de la classe
    progress = pyqtSignal(int, int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result_ready = pyqtSignal(object)

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self._stop = False

    def stop(self):
        """Arrête le worker proprement"""
        self._stop = True

    def run(self):
        """Méthode exécutée dans le thread"""
        try:
            total = len(self.data)

            for i, item in enumerate(self.data):
                if self._stop:
                    break

                # Traitement
                result = self.process_item(item)

                # Émettre progression
                self.progress.emit(i + 1, total)

            # Émettre fin
            if not self._stop:
                self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))

    def process_item(self, item):
        """Traite un élément"""
        # ... logique
        return result


# Utilisation dans le code UI:
class SomeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None

    def start_processing(self):
        """Lance le traitement"""
        # Créer le worker
        self.worker = SomeWorker(data=self.data)

        # Connecter les signaux
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)

        # Démarrer
        self.worker.start()

    def stop_processing(self):
        """Arrête le traitement"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()  # Attendre que le thread se termine

    def on_progress(self, current, total):
        """Callback progression"""
        self.progress_bar.update_progress(current, total)

    def on_finished(self):
        """Callback fin"""
        print("Terminé!")

    def on_error(self, error_msg):
        """Callback erreur"""
        print(f"Erreur: {error_msg}")
```

---

## 🔧 VERIFICATION PIPELINE (Existant)

### Utilisation du VerificationPipeline

**Fichier**: `verification_pipeline.py`

```python
from .verification_pipeline import VerificationPipeline

# Créer un pipeline
pipeline = VerificationPipeline(
    db_manager=db,           # Instance VideoDatabase
    max_workers=8,           # Threads parallèles
    enable_caching=True,     # Cache dans DB
    mode='filtering'         # 'filtering' | 'weighting' | 'hybrid'
)

# Ajouter des méthodes (dans l'ordre)
pipeline.add_method(
    'color_histogram',
    enabled=True,
    parameters={'threshold': 85.0, 'bins': (32, 32, 32)},
    weight=1.0  # Utilisé en mode weighting/hybrid
)

pipeline.add_method(
    'dct_coefficients',
    enabled=True,
    parameters={'threshold': 75.0, 'num_coeffs': 15},
    weight=2.0
)

pipeline.add_method(
    'strategy3',
    enabled=True,
    parameters={
        'scene_threshold': 50.0,
        'dct_threshold': 75.0,
        'sequence_threshold': 95.0,
        'num_samples': 10,
        'warmup_seconds': 0.0,
        'max_workers': 8
    },
    weight=3.0
)

# Vérifier une paire
result = pipeline.verify(
    short_video='/path/to/short.mp4',
    long_video='/path/to/long.mp4',
    start_time=0.0,      # Temps de début dans long_video
    duration=120.0,      # Durée à vérifier
    sequence_score=100.0,
    run_label='test_run',
    debug_flag=False
)

# Résultat retourné:
{
    'accepted': True/False,                    # Verdict final
    'pipeline_results': [                      # Résultats par méthode
        {
            'method_name': 'color_histogram',
            'accepted': True,
            'threshold': 85.0,
            'weight': 1.0,
            'execution_time': 0.5,
            'color_hist_score': 92.3,
            # ... autres scores
        },
        # ...
    ],
    'total_time': 3.2,                         # Temps total
    'methods_executed': 3,                     # Nombre de méthodes exécutées
    'rejection_method': None,                  # Méthode qui a rejeté (ou None)
    'final_scores': {                          # Tous les scores
        'sequence_score': 100.0,
        'color_hist_score': 92.3,
        'dct_score': 87.1,
        # ...
    },
    'mode': 'filtering',
    'weighted_score': None,                    # Score pondéré (weighting/hybrid)
    'config_hash': 'abc123...',
    'run_label': 'test_run',
    'debug_flag': False
}

# Obtenir la config actuelle
config = pipeline.get_config()
# Retourne: [{'name': 'color_histogram', 'enabled': True, ...}, ...]

# Charger une config
pipeline.load_config([
    {'name': 'color_histogram', 'enabled': True, 'parameters': {...}, 'weight': 1.0},
    # ...
])
```

### Méthodes Disponibles

```python
# 7 méthodes disponibles:

# 1. color_histogram - Histogramme de couleurs HSV
{
    'name': 'color_histogram',
    'parameters': {
        'bins': (32, 32, 32),  # Bins H, S, V
        'threshold': 85.0       # Seuil %
    }
}

# 2. edge_pattern - Détection de contours Canny
{
    'name': 'edge_pattern',
    'parameters': {
        'canny_low': 50,
        'canny_high': 150,
        'grid_size': (4, 4),
        'threshold': 80.0
    }
}

# 3. motion_analysis - Corrélation de mouvement
{
    'name': 'motion_analysis',
    'parameters': {
        'sample_interval': 3,           # Frames entre échantillons
        'correlation_threshold': 85.0   # Seuil corrélation %
    }
}

# 4. dct_coefficients - Coefficients fréquentiels
{
    'name': 'dct_coefficients',
    'parameters': {
        'block_size': 8,
        'num_coeffs': 15,      # Nombre de coefficients
        'threshold': 75.0
    }
}

# 5. ssim - Similarité structurelle
{
    'name': 'ssim',
    'parameters': {
        'window_size': 7,
        'threshold': 0.85      # Entre 0 et 1
    }
}

# 6. feature_matching - Correspondance de points clés
{
    'name': 'feature_matching',
    'parameters': {
        'detector': 'ORB',     # 'ORB', 'SIFT', ou 'AKAZE'
        'max_features': 500,
        'threshold': 70.0
    }
}

# 7. strategy3 - Scene cuts + DCT (le plus puissant)
{
    'name': 'strategy3',
    'parameters': {
        'scene_threshold': 50.0,
        'dct_threshold': 75.0,
        'sequence_threshold': 95.0,
        'num_samples': 10,
        'warmup_seconds': 0.0,
        'max_workers': 8
    }
}
```

---

## 🎯 MAIN WINDOW (Points d'Intégration)

### Structure de main_window.py

```python
class DuplicateFinderWindow(QMainWindow):
    """Fenêtre principale du plugin (2087 lignes)"""

    def __init__(self, parent_window, video_hasher, file_list, plugin):
        super().__init__()

        # Composants principaux
        self.video_hasher = video_hasher          # VideoHasher instance
        self.file_list = file_list                # Liste des fichiers
        self.plugin = plugin                      # Plugin instance

        # Handlers
        self.file_handler = FileHandler(...)
        self.analysis_handler = AnalysisHandler(video_hasher)
        self.duplicate_handler = DuplicateHandler(...)
        self.audio_first_handler = AudioFirstHandler(video_hasher, analysis_handler)

        # Widgets de progression (déjà créés!)
        self.file_progress = None           # ModernProgressWidget
        self.duplicate_progress = None      # ModernProgressWidget
        self.audio_progress = None          # ModernProgressWidget
        self.status_indicator = None        # StatusIndicator

        # SubsequenceDetector
        self.subsequence_detector = None

        # Setup UI
        self._create_ui()

    def _create_ui(self):
        """Crée l'interface utilisateur"""
        # Créer un widget central avec tabs
        central = QWidget()
        layout = QVBoxLayout(central)

        # Créer les tabs
        self.tabs = QTabWidget()

        # Tab Fichiers
        files_tab = self._create_files_tab()
        self.tabs.addTab(files_tab, "📁 Fichiers")

        # Tab Paramètres
        params_tab = self._create_params_tab()
        self.tabs.addTab(params_tab, "⚙️ Paramètres")

        # Tab Doublons
        duplicates_tab = self._create_duplicates_tab()
        self.tabs.addTab(duplicates_tab, "🔍 Doublons")

        # Tab Debug
        debug_tab = self._create_debug_tab()
        self.tabs.addTab(debug_tab, "🐛 Debug")

        layout.addWidget(self.tabs)
        self.setCentralWidget(central)

    def _create_debug_tab(self) -> QWidget:
        """
        Crée l'onglet debug (ACTUEL - à remplacer).

        EMPLACEMENT: C'est ICI qu'il faut intégrer le nouveau système!

        Actuellement créé par: UIPanels.create_debug_tab(...)
        Localisation: ui/panels.py ligne ~850
        """
        from .ui.panels import UIPanels

        callbacks = {
            # ... callbacks actuels
        }

        return UIPanels.create_debug_tab(
            callbacks=callbacks,
            file_list_widget=self.file_list
        )
```

### Où Insérer le Nouveau Système

**Fichier à modifier**: `ui/panels.py`

**Méthode à modifier**: `UIPanels.create_debug_tab()` (ligne ~850)

**Structure actuelle**:
```python
@staticmethod
def create_debug_tab(callbacks: Dict, file_list_widget=None) -> QWidget:
    """Crée l'onglet debug"""

    tab = QWidget()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)

    content_widget = QWidget()
    layout = QVBoxLayout(content_widget)

    # ═══════════════════════════════════════════════════════════
    # SECTION 1: Hash Debugger V2
    # ═══════════════════════════════════════════════════════════
    hash_debugger_v2 = HashDebuggerV2()
    layout.addWidget(hash_debugger_v2)

    # ═══════════════════════════════════════════════════════════
    # SECTION 2: Audio Fingerprint Debugger
    # ═══════════════════════════════════════════════════════════
    audio_debugger = AudioFingerprintDebugger()
    layout.addWidget(audio_debugger)

    # ═══════════════════════════════════════════════════════════
    # SECTION 3: File List Display
    # ═══════════════════════════════════════════════════════════
    # ... affichage liste fichiers ...

    # ═══════════════════════════════════════════════════════════
    # SECTION 4: TEST PROTOCOLS
    # ═══════════════════════════════════════════════════════════
    # ... protocoles de test ...
    TEST_PROTOCOLS = {
        'anti_fp': {...},
        'balanced': {...},
        # ... 10 protocoles
    }

    # ═══════════════════════════════════════════════════════════
    # SECTION 5: BENCHMARK (ancien système)
    # ═══════════════════════════════════════════════════════════
    # ... ancien système de benchmark à remplacer ...

    scroll.setWidget(content_widget)

    main_layout = QVBoxLayout(tab)
    main_layout.addWidget(scroll)

    return tab
```

**REMPLACER LA SECTION 5** par le nouveau système avec:
- PipelineEditorWidget
- TestSetEditorWidget
- BenchmarkBatchWidget
- BenchmarkResultsWidget

---

## 📦 IMPORTS STANDARDS

### Imports PyQt6

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QTextEdit, QListWidget, QListWidgetItem, QFileDialog,
    QLineEdit, QScrollArea, QFrame, QTabWidget, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont, QColor
```

### Imports Internes

```python
# Depuis duplicate_finder
from ..database_manager import VideoDatabase
from ..verification_pipeline import VerificationPipeline
from ..progress_widgets import ModernProgressWidget, StatusIndicator, FileListWidget
from ..managers.pipeline_manager import PipelineManager
from ..managers.test_set_manager import TestSetManager
from ..managers.benchmark_manager import BenchmarkManager, BenchmarkRunner
from src.core.logger import Logger
from src.core.i18n import t  # Traductions (optionnel)

# Autres
import json
import os
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
```

---

## 🎨 STYLES CSS (Theme)

### Couleurs Standard du Plugin

```python
# Boutons
BUTTON_PRIMARY = "#28A745"      # Vert (Démarrer)
BUTTON_PRIMARY_HOVER = "#218838"

BUTTON_DANGER = "#DC3545"       # Rouge (Arrêter)
BUTTON_DANGER_HOVER = "#C82333"

BUTTON_INFO = "#17A2B8"         # Bleu (Info)
BUTTON_INFO_HOVER = "#138496"

BUTTON_WARNING = "#FFC107"      # Jaune (Warning)
BUTTON_SCENE = "#1565C0"        # Bleu foncé (Scènes)
BUTTON_SCENE_HOVER = "#0D47A1"

# Backgrounds
BG_LIGHT = "#F8F9FA"
BG_WHITE = "#FFFFFF"
BG_BORDER = "#DEE2E6"

# Status
STATUS_SUCCESS = "#28A745"
STATUS_ERROR = "#DC3545"
STATUS_INFO = "#007BFF"
STATUS_WARNING = "#FFC107"

# Text
TEXT_DARK = "#495057"
TEXT_LIGHT = "#6C757D"
```

### Style de Bouton Standard

```python
def get_button_style(bg_color: str, hover_color: str, font_size: int = 12) -> str:
    """Retourne le style CSS pour un bouton"""
    return f"""
        QPushButton {{
            background-color: {bg_color};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            font-size: {font_size}pt;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
        QPushButton:disabled {{
            background-color: #CBD5E1;
            color: #94A3B8;
        }}
    """
```

---

## 📝 LOGGER

### Utilisation du Logger

```python
from src.core.logger import Logger

# Dans chaque fichier, créer un logger
logger = Logger.get_logger('DuplicateFinder.MonModule')

# Utilisation
logger.debug("Message de debug")
logger.info("Information")
logger.warning("Avertissement")
logger.error("Erreur", exc_info=True)  # exc_info pour la stack trace
```

---

## 🔑 POINTS CLÉS POUR INTÉGRATION

### 1. Accès à la DB

```python
# Depuis main_window:
db = self.video_hasher.db  # Instance de VideoDatabase

# Depuis un widget:
def __init__(self, db_manager, parent=None):
    super().__init__(parent)
    self.db = db_manager  # Stocker la référence
```

### 2. Afficher/Masquer Barres de Progression

```python
# Lors du démarrage d'une opération
self.progress_bar.setVisible(True)
self.progress_bar.reset()
self.progress_bar.update_progress(0, total, "Démarrage...")

# Pendant l'opération
self.progress_bar.update_progress(current, total)

# À la fin
self.progress_bar.set_status("Terminé!", STATUS_SUCCESS)
QTimer.singleShot(2000, lambda: self.progress_bar.setVisible(False))  # Masquer après 2s
```

### 3. Connexion Signaux/Slots

```python
# Créer worker
self.worker = BenchmarkRunner(...)

# Connecter signaux
self.worker.pipeline_progress.connect(self._on_pipeline_progress)
self.worker.pair_progress.connect(self._on_pair_progress)
self.worker.finished.connect(self._on_finished)
self.worker.error.connect(self._on_error)

# Démarrer
self.worker.start()

# Callbacks
def _on_pipeline_progress(self, current, total, name):
    self.pipeline_bar.update_progress(current, total, name)

def _on_pair_progress(self, current, total, video1, video2):
    self.pair_bar.update_progress(current, total, f"{os.path.basename(video1)} vs {os.path.basename(video2)}")
```

### 4. Gestion Erreurs

```python
try:
    # Opération risquée
    result = do_something()
except ValueError as e:
    QMessageBox.warning(self, "Erreur", str(e))
    logger.warning(f"Erreur: {e}")
except Exception as e:
    QMessageBox.critical(self, "Erreur Critique", f"Une erreur est survenue:\n{e}")
    logger.error(f"Erreur critique: {e}", exc_info=True)
```

---

*Ce fichier documente l'architecture existante pour permettre la reprise du développement après compactage.*
