# Duplicate Finder - Corrections et Améliorations Complètes

**Date**: 2025-12-07
**Version**: 1.0
**Statut**: Propositions complètes avec priorités

---

## 📋 TABLE DES MATIÈRES

1. [Corrections Critiques (URGENT)](#1-corrections-critiques-urgent)
2. [Refonte de la Gestion des Paramètres](#2-refonte-de-la-gestion-des-paramètres)
3. [Améliorations du Système de Benchmark](#3-améliorations-du-système-de-benchmark)
4. [Architecture et Abstractions](#4-architecture-et-abstractions)
5. [Interface Utilisateur](#5-interface-utilisateur)
6. [Nouvelles Fonctionnalités](#6-nouvelles-fonctionnalités)
7. [Plan d'Implémentation](#7-plan-dimplémentation)

---

## 1. CORRECTIONS CRITIQUES (URGENT)

### 🔴 Priorité 1 - Bloque la Fonctionnalité

#### 1.1 Incohérence de Nommage des Widgets

**Problème**:
- `main_window.py:359` crée `self.threshold_spin` depuis `params_tab.video_threshold_spin`
- `settings_manager.py:400` attend `widgets['threshold_spin']` → **KeyError**

**Impact**: L'analyse ne peut pas démarrer car la configuration ne peut pas être lue.

**Solution 1 (Quick Fix)**:
```python
# main_window.py ligne 452-468
def _get_widget_dict(self):
    """Get dictionary of all parameter widgets."""
    return {
        'threshold_spin': self.threshold_spin,  # Renommer la clé
        'video_threshold_spin': self.threshold_spin,  # Alias pour compatibilité
        'hash_method_combo': self.hash_method_combo,
        # ... etc
    }
```

**Solution 2 (Meilleure)**: Standardiser tous les noms
```python
# ui/panels.py - Renommer tous les widgets
tab.threshold_spin = video_threshold_spin  # Au lieu de video_threshold_spin
tab.hash_method_combo = hash_method_combo
# Supprime le préfixe "video_" partout
```

**Recommandation**: Solution 2 + migration script

---

#### 1.2 Widgets Manquants dans get_widget_dict()

**Problème**: 20+ widgets audio-first non inclus → paramètres non sauvegardés/chargés

**Liste des widgets manquants**:
```python
# Audio-First Parameters
'audio_threshold_spin'
'audio_precision_combo'
'audio_workers_spin'
'audio_cache_size_spin'
'enable_no_audio_fallback'

# LSH Configuration
'enable_lsh_check'
'lsh_bands_spin'
'lsh_rows_spin'
'enable_lsh_no_audio'

# Multi-Resolution
'enable_mr_check'
'mr_coarse_duration_spin'
'mr_coarse_threshold_spin'
'mr_medium_duration_spin'
'mr_medium_threshold_spin'

# Metadata Filters
'enable_metadata_check'
'metadata_duration_tolerance_spin'
'metadata_size_ratio_spin'

# Cache Settings
'video_cache_size_spin'
'comparison_cache_size_spin'

# Detection Options
'enable_flip_detection'
```

**Solution**:
```python
# main_window.py:452-468 - VERSION COMPLÈTE
def _get_widget_dict(self):
    """Get complete dictionary of all parameter widgets."""
    # Validation: vérifier que tous les widgets existent
    required_widgets = [
        'threshold_spin', 'hash_method_combo', 'hash_workers_spin',
        'comparison_workers_spin', 'batch_size_spin', 'hash_timeout_spin',
        'comparison_timeout_spin', 'comparison_algorithm_combo',
        # Audio-first (20+ widgets)
        'audio_threshold_spin', 'audio_precision_combo', ...
    ]

    widgets = {}
    missing = []

    for name in required_widgets:
        widget = getattr(self, name, None)
        if widget is None:
            missing.append(name)
        else:
            widgets[name] = widget

    if missing:
        logger.warning(f"Missing widgets: {missing}")

    return widgets
```

---

#### 1.3 Duplication de BenchmarkRunner

**Problème**:
- `managers/benchmark_manager.py:16` - QThread runner
- `benchmark_runner.py:12` - Function runner

**Solution**: Supprimer `benchmark_runner.py` (l'ancien)
```bash
rm src/plugins/duplicate_finder/benchmark_runner.py
```

---

### 🟡 Priorité 2 - Dette Technique

#### 2.1 Indices de Tabs Hardcodés

**Problème**:
```python
params_tab = config_tabs.widget(1)  # Fragile !
debug_tab = config_tabs.widget(2)
```

**Solution**: Utiliser des noms de tabs
```python
# ui/panels.py - Ajouter objectName aux tabs
def _create_config_tabs(...):
    tabs = QTabWidget()

    params_tab = QWidget()
    params_tab.setObjectName("params_tab")
    tabs.addTab(params_tab, "⚙️ Paramètres")

    debug_tab = QWidget()
    debug_tab.setObjectName("debug_tab")
    tabs.addTab(debug_tab, "🔧 Débogage")

    return tabs

# main_window.py - Trouver par nom
def _get_params_tab(self):
    if not self.config_tabs:
        return None
    for i in range(self.config_tabs.count()):
        widget = self.config_tabs.widget(i)
        if widget.objectName() == "params_tab":
            return widget
    return None
```

---

## 2. REFONTE DE LA GESTION DES PARAMÈTRES

### 🎯 Problème Actuel

**Trois systèmes incompatibles**:
1. **SettingsManager** (ancien) - 6 paramètres via QSettings
2. **AudioFirstConfig** (nouveau) - 20 paramètres via dataclass
3. **PipelineConfig** (récent) - JSON pour vérification

**Aucune intégration** entre ces systèmes.

---

### ✨ Solution Proposée: Fenêtre de Paramètres Dédiée

#### Architecture Unifiée

```python
# managers/unified_config_manager.py

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from PyQt6.QtCore import QSettings

@dataclass
class VideoHashingConfig:
    """Configuration for video hashing."""
    hash_method: str = 'pHash'
    threshold: float = 85.0
    hash_workers: int = 4
    hash_timeout: int = 120
    sample_interval: int = 500

@dataclass
class ComparisonConfig:
    """Configuration for video comparison."""
    algorithm: str = 'optimized'
    workers: int = 2
    batch_size: int = 50
    timeout: int = 300
    early_exit: bool = True

@dataclass
class AudioFirstConfig:
    """Configuration for audio-first workflow."""
    enabled: bool = False
    threshold: float = 80.0
    precision: str = 'medium'
    workers: int = 2
    cache_size_mb: int = 500

    # LSH
    lsh_enabled: bool = True
    lsh_bands: int = 20
    lsh_rows: int = 5
    lsh_no_audio_fallback: bool = True

    # Multi-Resolution
    mr_enabled: bool = True
    mr_coarse_duration: float = 10.0
    mr_coarse_threshold: float = 70.0
    mr_medium_duration: float = 3.0
    mr_medium_threshold: float = 80.0

    # Metadata
    metadata_check: bool = True
    metadata_duration_tolerance: float = 5.0
    metadata_size_ratio: float = 0.9

    # Detection
    flip_detection: bool = False

@dataclass
class CacheConfig:
    """Configuration for caching."""
    video_cache_size: int = 2000
    comparison_cache_size: int = 10000
    frame_cache_size: int = 100
    audio_cache_mb: int = 500
    dense_hash_cache_mb: int = 500

@dataclass
class SubsequenceConfig:
    """Configuration for subsequence detection."""
    enabled: bool = False
    phase1_method: str = 'dense_hash'
    phase2_enabled: bool = True
    phase2_method: str = 'strategy3'
    sample_interval: float = 0.75
    min_match_ratio: float = 0.70
    temporal_window: int = 5
    dct_threshold: float = 75.0
    sequence_threshold: float = 95.0
    workers: int = 2

@dataclass
class UnifiedConfig:
    """Complete unified configuration."""
    video_hashing: VideoHashingConfig = field(default_factory=VideoHashingConfig)
    comparison: ComparisonConfig = field(default_factory=ComparisonConfig)
    audio_first: AudioFirstConfig = field(default_factory=AudioFirstConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    subsequence: SubsequenceConfig = field(default_factory=SubsequenceConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'video_hashing': self.video_hashing.__dict__,
            'comparison': self.comparison.__dict__,
            'audio_first': self.audio_first.__dict__,
            'cache': self.cache.__dict__,
            'subsequence': self.subsequence.__dict__,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedConfig':
        """Create from dictionary."""
        return cls(
            video_hashing=VideoHashingConfig(**data.get('video_hashing', {})),
            comparison=ComparisonConfig(**data.get('comparison', {})),
            audio_first=AudioFirstConfig(**data.get('audio_first', {})),
            cache=CacheConfig(**data.get('cache', {})),
            subsequence=SubsequenceConfig(**data.get('subsequence', {})),
        )

    def save(self, settings: QSettings):
        """Save to QSettings."""
        for category, config_obj in [
            ('video_hashing', self.video_hashing),
            ('comparison', self.comparison),
            ('audio_first', self.audio_first),
            ('cache', self.cache),
            ('subsequence', self.subsequence),
        ]:
            settings.beginGroup(category)
            for key, value in config_obj.__dict__.items():
                settings.setValue(key, value)
            settings.endGroup()

    @classmethod
    def load(cls, settings: QSettings) -> 'UnifiedConfig':
        """Load from QSettings."""
        config = cls()

        for category, config_obj in [
            ('video_hashing', config.video_hashing),
            ('comparison', config.comparison),
            ('audio_first', config.audio_first),
            ('cache', config.cache),
            ('subsequence', config.subsequence),
        ]:
            settings.beginGroup(category)
            for key in config_obj.__dict__.keys():
                value = settings.value(key)
                if value is not None:
                    # Type conversion
                    current = getattr(config_obj, key)
                    if isinstance(current, bool):
                        value = value in ['true', 'True', True, 1, '1']
                    elif isinstance(current, int):
                        value = int(value)
                    elif isinstance(current, float):
                        value = float(value)
                    setattr(config_obj, key, value)
            settings.endGroup()

        return config


class UnifiedConfigManager:
    """Manages all configuration with persistence."""

    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.config = UnifiedConfig()

    def load_from_ui(self, main_window) -> UnifiedConfig:
        """Extract configuration from UI widgets."""
        # Video Hashing
        self.config.video_hashing.hash_method = main_window.hash_method_combo.currentData()
        self.config.video_hashing.threshold = main_window.threshold_spin.value()
        self.config.video_hashing.hash_workers = main_window.hash_workers_spin.value()
        # ... tous les autres widgets

        return self.config

    def apply_to_ui(self, main_window):
        """Apply configuration to UI widgets."""
        # Bloquer les signaux pendant l'application
        main_window.hash_method_combo.setCurrentText(self.config.video_hashing.hash_method)
        main_window.threshold_spin.setValue(self.config.video_hashing.threshold)
        # ... tous les autres widgets

    def save(self):
        """Save to persistent storage."""
        self.config.save(self.settings_manager.settings)

    def load(self):
        """Load from persistent storage."""
        self.config = UnifiedConfig.load(self.settings_manager.settings)

    def export_json(self, file_path: str):
        """Export to JSON file."""
        import json
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.config.to_dict(), f, indent=2)

    def import_json(self, file_path: str):
        """Import from JSON file."""
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.config = UnifiedConfig.from_dict(data)
```

---

#### Fenêtre de Paramètres Dédiée

```python
# ui/settings_dialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QGroupBox, QLabel, QSpinBox, QDoubleSpinBox,
    QComboBox, QCheckBox, QPushButton, QFormLayout,
    QDialogButtonBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

class SettingsDialog(QDialog):
    """Fenêtre dédiée aux paramètres du plugin."""

    settings_changed = pyqtSignal()

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("⚙️ Paramètres - Duplicate Finder")
        self.setMinimumSize(800, 600)
        self.setModal(True)

        self._init_ui()
        self._load_config()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)

        # Tabs pour organiser les catégories
        tabs = QTabWidget()

        # 1. Hashing
        tabs.addTab(self._create_hashing_tab(), "🔢 Hashing")

        # 2. Comparison
        tabs.addTab(self._create_comparison_tab(), "🔍 Comparaison")

        # 3. Audio-First
        tabs.addTab(self._create_audio_tab(), "🎵 Audio-First")

        # 4. Cache
        tabs.addTab(self._create_cache_tab(), "💾 Cache")

        # 5. Subsequence
        tabs.addTab(self._create_subsequence_tab(), "📹 Sous-séquences")

        layout.addWidget(tabs)

        # Boutons Import/Export/Reset
        toolbar = QHBoxLayout()

        import_btn = QPushButton("📥 Importer JSON")
        import_btn.clicked.connect(self._import_json)
        toolbar.addWidget(import_btn)

        export_btn = QPushButton("📤 Exporter JSON")
        export_btn.clicked.connect(self._export_json)
        toolbar.addWidget(export_btn)

        toolbar.addStretch()

        reset_btn = QPushButton("🔄 Réinitialiser")
        reset_btn.clicked.connect(self._reset_defaults)
        toolbar.addWidget(reset_btn)

        layout.addLayout(toolbar)

        # Boutons OK/Cancel/Apply
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        buttons.accepted.connect(self._save_and_close)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply)

        layout.addWidget(buttons)

    def _create_hashing_tab(self):
        """Create hashing configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Méthode de hash
        method_group = QGroupBox("Méthode de Hash")
        method_layout = QFormLayout()

        self.hash_method_combo = QComboBox()
        self.hash_method_combo.addItem("pHash (Précis)", "pHash")
        self.hash_method_combo.addItem("dHash (Rapide)", "dHash")
        self.hash_method_combo.addItem("aHash (Très rapide)", "aHash")
        method_layout.addRow("Méthode:", self.hash_method_combo)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0, 100)
        self.threshold_spin.setValue(85.0)
        self.threshold_spin.setSuffix(" %")
        method_layout.addRow("Seuil de similarité:", self.threshold_spin)

        method_group.setLayout(method_layout)
        layout.addWidget(method_group)

        # Performance
        perf_group = QGroupBox("Performance")
        perf_layout = QFormLayout()

        self.hash_workers_spin = QSpinBox()
        self.hash_workers_spin.setRange(1, 16)
        self.hash_workers_spin.setValue(4)
        perf_layout.addRow("Workers parallèles:", self.hash_workers_spin)

        self.hash_timeout_spin = QSpinBox()
        self.hash_timeout_spin.setRange(10, 600)
        self.hash_timeout_spin.setValue(120)
        self.hash_timeout_spin.setSuffix(" s")
        perf_layout.addRow("Timeout par vidéo:", self.hash_timeout_spin)

        self.sample_interval_spin = QSpinBox()
        self.sample_interval_spin.setRange(100, 2000)
        self.sample_interval_spin.setValue(500)
        self.sample_interval_spin.setSuffix(" ms")
        perf_layout.addRow("Intervalle d'échantillonnage:", self.sample_interval_spin)

        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)

        layout.addStretch()
        return widget

    def _create_comparison_tab(self):
        """Create comparison configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Algorithme
        algo_group = QGroupBox("Algorithme de Comparaison")
        algo_layout = QFormLayout()

        self.comparison_algorithm_combo = QComboBox()
        self.comparison_algorithm_combo.addItem("Optimisé (Recommandé)", "optimized")
        self.comparison_algorithm_combo.addItem("Standard", "standard")
        algo_layout.addRow("Algorithme:", self.comparison_algorithm_combo)

        self.early_exit_check = QCheckBox("Activer early exit (métadonnées)")
        self.early_exit_check.setChecked(True)
        algo_layout.addRow("", self.early_exit_check)

        algo_group.setLayout(algo_layout)
        layout.addWidget(algo_group)

        # Performance
        perf_group = QGroupBox("Performance")
        perf_layout = QFormLayout()

        self.comparison_workers_spin = QSpinBox()
        self.comparison_workers_spin.setRange(1, 16)
        self.comparison_workers_spin.setValue(2)
        perf_layout.addRow("Workers parallèles:", self.comparison_workers_spin)

        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(10, 500)
        self.batch_size_spin.setValue(50)
        perf_layout.addRow("Taille des batchs:", self.batch_size_spin)

        self.comparison_timeout_spin = QSpinBox()
        self.comparison_timeout_spin.setRange(10, 600)
        self.comparison_timeout_spin.setValue(300)
        self.comparison_timeout_spin.setSuffix(" s")
        perf_layout.addRow("Timeout par comparaison:", self.comparison_timeout_spin)

        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)

        layout.addStretch()
        return widget

    def _create_audio_tab(self):
        """Create audio-first configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Général
        general_group = QGroupBox("Audio-First")
        general_layout = QFormLayout()

        self.audio_enabled_check = QCheckBox("Activer le workflow audio-first")
        general_layout.addRow("", self.audio_enabled_check)

        self.audio_threshold_spin = QDoubleSpinBox()
        self.audio_threshold_spin.setRange(0, 100)
        self.audio_threshold_spin.setValue(80.0)
        self.audio_threshold_spin.setSuffix(" %")
        general_layout.addRow("Seuil audio:", self.audio_threshold_spin)

        self.audio_precision_combo = QComboBox()
        self.audio_precision_combo.addItem("Haute", "high")
        self.audio_precision_combo.addItem("Moyenne", "medium")
        self.audio_precision_combo.addItem("Basse (Rapide)", "low")
        general_layout.addRow("Précision:", self.audio_precision_combo)

        self.audio_workers_spin = QSpinBox()
        self.audio_workers_spin.setRange(1, 16)
        self.audio_workers_spin.setValue(2)
        general_layout.addRow("Workers:", self.audio_workers_spin)

        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        # LSH
        lsh_group = QGroupBox("LSH (Locality-Sensitive Hashing)")
        lsh_layout = QFormLayout()

        self.lsh_enabled_check = QCheckBox("Activer LSH")
        self.lsh_enabled_check.setChecked(True)
        lsh_layout.addRow("", self.lsh_enabled_check)

        self.lsh_bands_spin = QSpinBox()
        self.lsh_bands_spin.setRange(5, 50)
        self.lsh_bands_spin.setValue(20)
        lsh_layout.addRow("Bands:", self.lsh_bands_spin)

        self.lsh_rows_spin = QSpinBox()
        self.lsh_rows_spin.setRange(2, 20)
        self.lsh_rows_spin.setValue(5)
        lsh_layout.addRow("Rows par band:", self.lsh_rows_spin)

        self.lsh_no_audio_check = QCheckBox("Fallback si pas d'audio")
        self.lsh_no_audio_check.setChecked(True)
        lsh_layout.addRow("", self.lsh_no_audio_check)

        lsh_group.setLayout(lsh_layout)
        layout.addWidget(lsh_group)

        # Multi-Resolution
        mr_group = QGroupBox("Multi-Résolution")
        mr_layout = QFormLayout()

        self.mr_enabled_check = QCheckBox("Activer multi-résolution")
        self.mr_enabled_check.setChecked(True)
        mr_layout.addRow("", self.mr_enabled_check)

        self.mr_coarse_duration_spin = QDoubleSpinBox()
        self.mr_coarse_duration_spin.setRange(5, 60)
        self.mr_coarse_duration_spin.setValue(10.0)
        self.mr_coarse_duration_spin.setSuffix(" s")
        mr_layout.addRow("Durée coarse:", self.mr_coarse_duration_spin)

        self.mr_coarse_threshold_spin = QDoubleSpinBox()
        self.mr_coarse_threshold_spin.setRange(0, 100)
        self.mr_coarse_threshold_spin.setValue(70.0)
        self.mr_coarse_threshold_spin.setSuffix(" %")
        mr_layout.addRow("Seuil coarse:", self.mr_coarse_threshold_spin)

        mr_group.setLayout(mr_layout)
        layout.addWidget(mr_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        self.metadata_check = QCheckBox("Filtrage par métadonnées")
        self.metadata_check.setChecked(True)
        options_layout.addWidget(self.metadata_check)

        self.flip_detection_check = QCheckBox("Détection de vidéos inversées")
        options_layout.addWidget(self.flip_detection_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        layout.addStretch()
        return widget

    def _create_cache_tab(self):
        """Create cache configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        cache_group = QGroupBox("Configuration des Caches")
        cache_layout = QFormLayout()

        self.video_cache_spin = QSpinBox()
        self.video_cache_spin.setRange(100, 10000)
        self.video_cache_spin.setValue(2000)
        cache_layout.addRow("Cache vidéo (entrées):", self.video_cache_spin)

        self.comparison_cache_spin = QSpinBox()
        self.comparison_cache_spin.setRange(1000, 100000)
        self.comparison_cache_spin.setValue(10000)
        cache_layout.addRow("Cache comparaisons (entrées):", self.comparison_cache_spin)

        self.frame_cache_spin = QSpinBox()
        self.frame_cache_spin.setRange(10, 1000)
        self.frame_cache_spin.setValue(100)
        cache_layout.addRow("Cache frames (vidéos):", self.frame_cache_spin)

        self.audio_cache_spin = QSpinBox()
        self.audio_cache_spin.setRange(100, 5000)
        self.audio_cache_spin.setValue(500)
        self.audio_cache_spin.setSuffix(" MB")
        cache_layout.addRow("Cache audio (MB):", self.audio_cache_spin)

        self.dense_hash_cache_spin = QSpinBox()
        self.dense_hash_cache_spin.setRange(100, 5000)
        self.dense_hash_cache_spin.setValue(500)
        self.dense_hash_cache_spin.setSuffix(" MB")
        cache_layout.addRow("Cache dense hash (MB):", self.dense_hash_cache_spin)

        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)

        # Info
        info_label = QLabel(
            "💡 <b>Conseil</b>: Augmentez les tailles de cache si vous avez "
            "beaucoup de RAM disponible pour améliorer les performances."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addStretch()
        return widget

    def _create_subsequence_tab(self):
        """Create subsequence detection configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Général
        general_group = QGroupBox("Détection de Sous-séquences")
        general_layout = QFormLayout()

        self.subseq_enabled_check = QCheckBox("Activer la détection")
        general_layout.addRow("", self.subseq_enabled_check)

        self.phase1_method_combo = QComboBox()
        self.phase1_method_combo.addItem("Dense Hash (Recommandé)", "dense_hash")
        self.phase1_method_combo.addItem("Signature Adaptive", "signature_adaptive")
        self.phase1_method_combo.addItem("Fast Scan", "fast_scan")
        general_layout.addRow("Méthode Phase 1:", self.phase1_method_combo)

        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        # Phase 2
        phase2_group = QGroupBox("Phase 2 - Vérification")
        phase2_layout = QFormLayout()

        self.phase2_enabled_check = QCheckBox("Activer Phase 2 (lent mais précis)")
        phase2_layout.addRow("", self.phase2_enabled_check)

        self.phase2_method_combo = QComboBox()
        self.phase2_method_combo.addItem("Strategy3 (100% précision)", "strategy3")
        self.phase2_method_combo.addItem("DCT Only", "dct_only")
        self.phase2_method_combo.addItem("Frame Diff", "frame_diff")
        phase2_layout.addRow("Méthode Phase 2:", self.phase2_method_combo)

        self.dct_threshold_spin = QDoubleSpinBox()
        self.dct_threshold_spin.setRange(0, 100)
        self.dct_threshold_spin.setValue(75.0)
        self.dct_threshold_spin.setSuffix(" %")
        phase2_layout.addRow("Seuil DCT:", self.dct_threshold_spin)

        self.sequence_threshold_spin = QDoubleSpinBox()
        self.sequence_threshold_spin.setRange(0, 100)
        self.sequence_threshold_spin.setValue(95.0)
        self.sequence_threshold_spin.setSuffix(" %")
        phase2_layout.addRow("Seuil séquence:", self.sequence_threshold_spin)

        phase2_group.setLayout(phase2_layout)
        layout.addWidget(phase2_group)

        # Paramètres avancés
        advanced_group = QGroupBox("Paramètres Avancés")
        advanced_layout = QFormLayout()

        self.sample_interval_subseq_spin = QDoubleSpinBox()
        self.sample_interval_subseq_spin.setRange(0.1, 5.0)
        self.sample_interval_subseq_spin.setValue(0.75)
        self.sample_interval_subseq_spin.setSuffix(" s")
        advanced_layout.addRow("Intervalle échantillonnage:", self.sample_interval_subseq_spin)

        self.min_match_ratio_spin = QDoubleSpinBox()
        self.min_match_ratio_spin.setRange(0.1, 1.0)
        self.min_match_ratio_spin.setValue(0.70)
        advanced_layout.addRow("Ratio de match minimum:", self.min_match_ratio_spin)

        self.temporal_window_spin = QSpinBox()
        self.temporal_window_spin.setRange(1, 20)
        self.temporal_window_spin.setValue(5)
        advanced_layout.addRow("Fenêtre temporelle:", self.temporal_window_spin)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        layout.addStretch()
        return widget

    def _load_config(self):
        """Load configuration into UI."""
        config = self.config_manager.config

        # Video Hashing
        self.hash_method_combo.setCurrentText(config.video_hashing.hash_method)
        self.threshold_spin.setValue(config.video_hashing.threshold)
        self.hash_workers_spin.setValue(config.video_hashing.hash_workers)
        self.hash_timeout_spin.setValue(config.video_hashing.hash_timeout)

        # Comparison
        self.comparison_algorithm_combo.setCurrentText(config.comparison.algorithm)
        self.comparison_workers_spin.setValue(config.comparison.workers)
        self.batch_size_spin.setValue(config.comparison.batch_size)
        self.comparison_timeout_spin.setValue(config.comparison.timeout)
        self.early_exit_check.setChecked(config.comparison.early_exit)

        # Audio-First
        self.audio_enabled_check.setChecked(config.audio_first.enabled)
        self.audio_threshold_spin.setValue(config.audio_first.threshold)
        self.audio_precision_combo.setCurrentText(config.audio_first.precision)
        self.audio_workers_spin.setValue(config.audio_first.workers)
        self.lsh_enabled_check.setChecked(config.audio_first.lsh_enabled)
        self.lsh_bands_spin.setValue(config.audio_first.lsh_bands)
        self.lsh_rows_spin.setValue(config.audio_first.lsh_rows)
        # ... etc

        # Cache
        self.video_cache_spin.setValue(config.cache.video_cache_size)
        self.comparison_cache_spin.setValue(config.cache.comparison_cache_size)
        self.frame_cache_spin.setValue(config.cache.frame_cache_size)
        self.audio_cache_spin.setValue(config.cache.audio_cache_mb)

        # Subsequence
        self.subseq_enabled_check.setChecked(config.subsequence.enabled)
        self.phase1_method_combo.setCurrentText(config.subsequence.phase1_method)
        self.phase2_enabled_check.setChecked(config.subsequence.phase2_enabled)
        # ... etc

    def _save_config(self):
        """Save UI values to configuration."""
        config = self.config_manager.config

        # Video Hashing
        config.video_hashing.hash_method = self.hash_method_combo.currentData()
        config.video_hashing.threshold = self.threshold_spin.value()
        config.video_hashing.hash_workers = self.hash_workers_spin.value()
        config.video_hashing.hash_timeout = self.hash_timeout_spin.value()

        # Comparison
        config.comparison.algorithm = self.comparison_algorithm_combo.currentData()
        config.comparison.workers = self.comparison_workers_spin.value()
        config.comparison.batch_size = self.batch_size_spin.value()
        config.comparison.timeout = self.comparison_timeout_spin.value()
        config.comparison.early_exit = self.early_exit_check.isChecked()

        # Audio-First
        config.audio_first.enabled = self.audio_enabled_check.isChecked()
        config.audio_first.threshold = self.audio_threshold_spin.value()
        config.audio_first.precision = self.audio_precision_combo.currentData()
        config.audio_first.workers = self.audio_workers_spin.value()
        config.audio_first.lsh_enabled = self.lsh_enabled_check.isChecked()
        # ... etc

        # Cache
        config.cache.video_cache_size = self.video_cache_spin.value()
        config.cache.comparison_cache_size = self.comparison_cache_spin.value()
        # ... etc

        # Subsequence
        config.subsequence.enabled = self.subseq_enabled_check.isChecked()
        # ... etc

        self.config_manager.save()

    def _apply(self):
        """Apply settings without closing."""
        self._save_config()
        self.settings_changed.emit()
        QMessageBox.information(self, "Paramètres", "Paramètres appliqués avec succès !")

    def _save_and_close(self):
        """Save and close dialog."""
        self._save_config()
        self.settings_changed.emit()
        self.accept()

    def _reset_defaults(self):
        """Reset to default configuration."""
        reply = QMessageBox.question(
            self,
            "Réinitialiser",
            "Voulez-vous vraiment restaurer les paramètres par défaut ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.config_manager.config = UnifiedConfig()
            self._load_config()
            QMessageBox.information(self, "Réinitialiser", "Paramètres restaurés !")

    def _import_json(self):
        """Import configuration from JSON."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importer Configuration",
            "",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                self.config_manager.import_json(file_path)
                self._load_config()
                QMessageBox.information(self, "Import", "Configuration importée avec succès !")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'import:\n{e}")

    def _export_json(self):
        """Export configuration to JSON."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter Configuration",
            "duplicate_finder_config.json",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                self._save_config()
                self.config_manager.export_json(file_path)
                QMessageBox.information(self, "Export", "Configuration exportée avec succès !")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export:\n{e}")
```

#### Intégration dans main_window.py

```python
# main_window.py - Ajout d'un bouton Settings dans la barre de menu

def _create_menu_bar(self):
    """Create menu bar."""
    menubar = self.menuBar()

    # Menu Fichier
    file_menu = menubar.addMenu("📁 Fichier")

    open_action = file_menu.addAction("Ouvrir Vidéos...")
    open_action.triggered.connect(self.file_handler.add_files_dialog)

    open_folder_action = file_menu.addAction("Ouvrir Dossier...")
    open_folder_action.triggered.connect(self.file_handler.add_folder_dialog)

    file_menu.addSeparator()

    quit_action = file_menu.addAction("Quitter")
    quit_action.triggered.connect(self.close)

    # Menu Édition
    edit_menu = menubar.addMenu("✏️ Édition")

    settings_action = edit_menu.addAction("⚙️ Paramètres...")
    settings_action.setShortcut("Ctrl+,")
    settings_action.triggered.connect(self._show_settings_dialog)

    # Menu Outils
    tools_menu = menubar.addMenu("🔧 Outils")

    cleanup_action = tools_menu.addAction("🗑️ Nettoyer la base de données")
    cleanup_action.triggered.connect(self.auto_cleanup_database)

    # Menu Aide
    help_menu = menubar.addMenu("❓ Aide")

    about_action = help_menu.addAction("À propos...")
    about_action.triggered.connect(self._show_about)

def _show_settings_dialog(self):
    """Show settings dialog."""
    dialog = SettingsDialog(self.config_manager, self)
    dialog.settings_changed.connect(self._on_settings_changed_external)
    dialog.exec()

def _on_settings_changed_external(self):
    """Handle settings changed from dialog."""
    # Appliquer la configuration à l'UI
    self.config_manager.apply_to_ui(self)
    # Recréer le video hasher si la méthode a changé
    if self.video_hasher.method != self.config_manager.config.video_hashing.hash_method:
        self.video_hasher = VideoHasher(
            method=self.config_manager.config.video_hashing.hash_method
        )
```

---

## 3. AMÉLIORATIONS DU SYSTÈME DE BENCHMARK

### 🎯 Problèmes Actuels

1. **Duplication d'UI**: Benchmark simple dans Debug tab + BenchmarkTabWidget avancé
2. **Pas de ground truth**: Génération de paires avec `expected='unknown'`
3. **Confusion protocoles/pipelines**: Deux systèmes parallèles sans intégration

---

### ✨ Solutions Proposées

#### 3.1 Onglet Benchmark Dédié (Niveau Principal)

```python
# main_window.py - Créer un onglet principal pour les benchmarks

def setup_ui(self):
    """Setup UI with main tabs."""
    # Au lieu d'avoir tout dans la fenêtre principale,
    # créer un QTabWidget principal

    main_tabs = QTabWidget()
    main_tabs.setDocumentMode(True)

    # Tab 1: Analysis (contenu actuel)
    analysis_tab = self._create_analysis_tab()
    main_tabs.addTab(analysis_tab, "🔍 Analyse")

    # Tab 2: Benchmarks (nouveau)
    benchmark_tab = self._create_benchmark_tab()
    main_tabs.addTab(benchmark_tab, "📊 Benchmarks")

    # Tab 3: Settings (déplacé)
    settings_tab = self._create_settings_tab()
    main_tabs.addTab(settings_tab, "⚙️ Paramètres")

    self.setCentralWidget(main_tabs)

def _create_benchmark_tab(self):
    """Create comprehensive benchmark tab."""
    from .ui.benchmark_widgets import BenchmarkTabWidget
    return BenchmarkTabWidget(self.video_hasher.db)
```

#### 3.2 Amélioration de BenchmarkTabWidget

```python
# ui/benchmark_widgets.py - Améliorations

class BenchmarkTabWidget(QWidget):
    """Enhanced benchmark system."""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager

        # Managers
        self.pipeline_manager = PipelineManager(db_manager)
        self.test_set_manager = TestSetManager(db_manager)
        self.benchmark_manager = BenchmarkManager(db_manager)

        self._init_ui()

        # Auto-load default protocols
        self._ensure_default_protocols()

    def _init_ui(self):
        """Initialize enhanced UI."""
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Tabs
        tabs = QTabWidget()

        # 1. Test Sets (plus important en premier)
        tabs.addTab(self._create_test_sets_tab(), "📹 Test Sets")

        # 2. Pipelines
        tabs.addTab(self._create_pipelines_tab(), "🔧 Pipelines")

        # 3. Run Benchmark
        tabs.addTab(self._create_run_tab(), "▶️ Exécuter")

        # 4. Results
        tabs.addTab(self._create_results_tab(), "📊 Résultats")

        # 5. History
        tabs.addTab(self._create_history_tab(), "📜 Historique")

        layout.addWidget(tabs)

    def _create_toolbar(self):
        """Create main toolbar."""
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)

        # Quick actions
        quick_benchmark_btn = QPushButton("⚡ Quick Benchmark")
        quick_benchmark_btn.setToolTip("Run benchmark with default protocol")
        quick_benchmark_btn.clicked.connect(self._quick_benchmark)
        layout.addWidget(quick_benchmark_btn)

        layout.addStretch()

        # Import/Export
        import_btn = QPushButton("📥 Import")
        import_menu = QMenu()
        import_menu.addAction("Import Test Set (JSON)")
        import_menu.addAction("Import Pipeline (JSON)")
        import_btn.setMenu(import_menu)
        layout.addWidget(import_btn)

        export_btn = QPushButton("📤 Export")
        export_menu = QMenu()
        export_menu.addAction("Export Results (CSV)")
        export_menu.addAction("Export Results (JSON)")
        export_menu.addAction("Export Report (PDF)")
        export_btn.setMenu(export_menu)
        layout.addWidget(export_btn)

        return toolbar

    def _create_test_sets_tab(self):
        """Enhanced test sets management."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Toolbar
        toolbar = QHBoxLayout()

        new_btn = QPushButton("➕ Nouveau Set")
        new_btn.clicked.connect(self._create_new_test_set)
        toolbar.addWidget(new_btn)

        import_btn = QPushButton("📥 Importer JSON")
        import_btn.clicked.connect(self._import_test_set)
        toolbar.addWidget(import_btn)

        generate_btn = QPushButton("🎲 Générer Automatiquement")
        generate_btn.clicked.connect(self._generate_test_set)
        toolbar.addWidget(generate_btn)

        toolbar.addStretch()

        delete_btn = QPushButton("🗑️ Supprimer")
        delete_btn.clicked.connect(self._delete_test_set)
        toolbar.addWidget(delete_btn)

        layout.addLayout(toolbar)

        # List of test sets
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Test sets list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        left_layout.addWidget(QLabel("<b>Test Sets</b>"))

        self.test_sets_list = QListWidget()
        self.test_sets_list.currentItemChanged.connect(self._on_test_set_selected)
        left_layout.addWidget(self.test_sets_list)

        splitter.addWidget(left_panel)

        # Right: Test set details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        right_layout.addWidget(QLabel("<b>Paires de Test</b>"))

        # Table of test pairs
        self.pairs_table = QTableWidget()
        self.pairs_table.setColumnCount(5)
        self.pairs_table.setHorizontalHeaderLabels([
            "Vidéo 1", "Vidéo 2", "Attendu", "Notes", "Actions"
        ])
        self.pairs_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.pairs_table)

        # Stats
        self.stats_label = QLabel()
        right_layout.addWidget(self.stats_label)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        # Load test sets
        self._refresh_test_sets()

        return widget

    def _generate_test_set(self):
        """Generate test set with guided wizard."""
        from .test_set_wizard import TestSetWizard

        wizard = TestSetWizard(self.test_set_manager, self)
        if wizard.exec():
            self._refresh_test_sets()

    def _create_pipelines_tab(self):
        """Enhanced pipelines management."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Toolbar
        toolbar = QHBoxLayout()

        new_btn = QPushButton("➕ Nouveau Pipeline")
        new_btn.clicked.connect(self._create_new_pipeline)
        toolbar.addWidget(new_btn)

        duplicate_btn = QPushButton("📋 Dupliquer")
        duplicate_btn.clicked.connect(self._duplicate_pipeline)
        toolbar.addWidget(duplicate_btn)

        toolbar.addStretch()

        # Preset dropdown
        preset_label = QLabel("Préconfigurations:")
        toolbar.addWidget(preset_label)

        self.preset_combo = QComboBox()
        for name in self.pipeline_manager.DEFAULT_PROTOCOLS.keys():
            self.preset_combo.addItem(name.replace('_', ' ').title(), name)
        toolbar.addWidget(self.preset_combo)

        load_preset_btn = QPushButton("⬇️ Charger")
        load_preset_btn.clicked.connect(self._load_preset)
        toolbar.addWidget(load_preset_btn)

        delete_btn = QPushButton("🗑️ Supprimer")
        delete_btn.clicked.connect(self._delete_pipeline)
        toolbar.addWidget(delete_btn)

        layout.addLayout(toolbar)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Pipelines list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        left_layout.addWidget(QLabel("<b>Pipelines Sauvegardés</b>"))

        self.pipelines_list = QListWidget()
        self.pipelines_list.currentItemChanged.connect(self._on_pipeline_selected)
        left_layout.addWidget(self.pipelines_list)

        splitter.addWidget(left_panel)

        # Right: Pipeline editor
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        from .pipeline_editor_widget import PipelineEditorWidget
        self.pipeline_editor = PipelineEditorWidget(self.pipeline_manager)
        self.pipeline_editor.pipeline_saved.connect(self._refresh_pipelines)
        right_layout.addWidget(self.pipeline_editor)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        # Load pipelines
        self._refresh_pipelines()

        return widget

    def _create_run_tab(self):
        """Enhanced benchmark execution tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Configuration
        config_group = QGroupBox("Configuration du Benchmark")
        config_layout = QVBoxLayout()

        # Test set selection
        test_set_layout = QHBoxLayout()
        test_set_layout.addWidget(QLabel("Test Set:"))
        self.run_test_set_combo = QComboBox()
        test_set_layout.addWidget(self.run_test_set_combo)
        config_layout.addLayout(test_set_layout)

        # Pipelines selection
        config_layout.addWidget(QLabel("<b>Sélection des Pipelines:</b>"))

        # Quick select buttons
        quick_select = QHBoxLayout()
        select_all_btn = QPushButton("✓ Tout")
        select_all_btn.clicked.connect(lambda: self._select_all_pipelines(True))
        quick_select.addWidget(select_all_btn)

        select_none_btn = QPushButton("✗ Aucun")
        select_none_btn.clicked.connect(lambda: self._select_all_pipelines(False))
        quick_select.addWidget(select_none_btn)

        select_defaults_btn = QPushButton("⭐ Défauts")
        select_defaults_btn.clicked.connect(self._select_default_pipelines)
        quick_select.addWidget(select_defaults_btn)

        quick_select.addStretch()
        config_layout.addLayout(quick_select)

        # Pipelines list with checkboxes
        self.run_pipelines_list = QListWidget()
        self.run_pipelines_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        config_layout.addWidget(self.run_pipelines_list)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Progress
        progress_group = QGroupBox("Progression")
        progress_layout = QVBoxLayout()

        self.run_overall_progress = ModernProgressWidget("🔧 Progression Globale")
        progress_layout.addWidget(self.run_overall_progress)

        self.run_current_progress = ModernProgressWidget("📹 Pipeline Actuel")
        progress_layout.addWidget(self.run_current_progress)

        self.run_status_label = QLabel()
        progress_layout.addWidget(self.run_status_label)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Controls
        controls_layout = QHBoxLayout()

        self.run_start_btn = QPushButton("▶️ Lancer le Benchmark")
        self.run_start_btn.clicked.connect(self._start_benchmark)
        controls_layout.addWidget(self.run_start_btn)

        self.run_stop_btn = QPushButton("⏹️ Arrêter")
        self.run_stop_btn.setEnabled(False)
        self.run_stop_btn.clicked.connect(self._stop_benchmark)
        controls_layout.addWidget(self.run_stop_btn)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        layout.addStretch()

        return widget

    def _create_results_tab(self):
        """Enhanced results visualization."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Toolbar
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("Afficher:"))

        self.results_run_combo = QComboBox()
        self.results_run_combo.currentIndexChanged.connect(self._load_results)
        toolbar.addWidget(self.results_run_combo)

        toolbar.addStretch()

        export_csv_btn = QPushButton("📊 Exporter CSV")
        export_csv_btn.clicked.connect(self._export_results_csv)
        toolbar.addWidget(export_csv_btn)

        export_report_btn = QPushButton("📄 Rapport PDF")
        export_report_btn.clicked.connect(self._export_report_pdf)
        toolbar.addWidget(export_report_btn)

        layout.addLayout(toolbar)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(10)
        self.results_table.setHorizontalHeaderLabels([
            "Pipeline", "TP", "FP", "TN", "FN",
            "Précision", "Rappel", "F1-Score", "Temps", "Détails"
        ])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.results_table)

        # Visualization
        viz_group = QGroupBox("Visualisation")
        viz_layout = QVBoxLayout()

        # Tabs for different visualizations
        viz_tabs = QTabWidget()

        # Bar chart comparison
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
        from matplotlib.figure import Figure

        self.precision_canvas = FigureCanvasQTAgg(Figure(figsize=(8, 4)))
        viz_tabs.addTab(self.precision_canvas, "📊 Précision")

        self.recall_canvas = FigureCanvasQTAgg(Figure(figsize=(8, 4)))
        viz_tabs.addTab(self.recall_canvas, "📊 Rappel")

        self.f1_canvas = FigureCanvasQTAgg(Figure(figsize=(8, 4)))
        viz_tabs.addTab(self.f1_canvas, "📊 F1-Score")

        self.time_canvas = FigureCanvasQTAgg(Figure(figsize=(8, 4)))
        viz_tabs.addTab(self.time_canvas, "⏱️ Temps")

        viz_layout.addWidget(viz_tabs)
        viz_group.setLayout(viz_layout)
        layout.addWidget(viz_group)

        return widget

    def _create_history_tab(self):
        """Benchmark history and comparison."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Toolbar
        toolbar = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Rafraîchir")
        refresh_btn.clicked.connect(self._refresh_history)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        compare_btn = QPushButton("⚖️ Comparer")
        compare_btn.clicked.connect(self._compare_runs)
        toolbar.addWidget(compare_btn)

        delete_btn = QPushButton("🗑️ Supprimer")
        delete_btn.clicked.connect(self._delete_run)
        toolbar.addWidget(delete_btn)

        layout.addLayout(toolbar)

        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "ID", "Date", "Test Set", "Pipelines", "Statut", "Actions"
        ])
        layout.addWidget(self.history_table)

        return widget
```

#### 3.3 Assistant de Création de Test Set

```python
# ui/test_set_wizard.py

class TestSetWizard(QDialog):
    """Wizard to create test sets easily."""

    def __init__(self, test_set_manager, parent=None):
        super().__init__(parent)
        self.test_set_manager = test_set_manager
        self.setWindowTitle("🧙 Assistant de Création de Test Set")
        self.setMinimumSize(700, 500)

        self._init_ui()

    def _init_ui(self):
        """Initialize wizard UI."""
        layout = QVBoxLayout(self)

        # Tabs for different methods
        tabs = QTabWidget()

        # Method 1: From file list
        tabs.addTab(self._create_file_list_tab(), "📁 À partir de fichiers")

        # Method 2: Manual pairs
        tabs.addTab(self._create_manual_tab(), "✍️ Paires manuelles")

        # Method 3: Import JSON
        tabs.addTab(self._create_import_tab(), "📥 Importer JSON")

        # Method 4: From detection results
        tabs.addTab(self._create_results_tab(), "🔍 Depuis résultats")

        layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._create_test_set)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_file_list_tab(self):
        """Create tab for generating from file list."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Info
        info = QLabel(
            "💡 Génère automatiquement des paires de test en comparant tous les fichiers.\n"
            "Vous devrez ensuite valider manuellement quelles paires sont des doublons."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # File selection
        file_group = QGroupBox("Sélection des Fichiers")
        file_layout = QVBoxLayout()

        add_files_btn = QPushButton("➕ Ajouter Fichiers")
        add_files_btn.clicked.connect(self._add_files)
        file_layout.addWidget(add_files_btn)

        add_folder_btn = QPushButton("📁 Ajouter Dossier")
        add_folder_btn.clicked.connect(self._add_folder)
        file_layout.addWidget(add_folder_btn)

        self.files_list = QListWidget()
        file_layout.addWidget(self.files_list)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QFormLayout()

        self.test_set_name_edit = QLineEdit()
        self.test_set_name_edit.setPlaceholderText("Nom du test set...")
        options_layout.addRow("Nom:", self.test_set_name_edit)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem("Toutes les paires (N²)", "all")
        self.strategy_combo.addItem("Pairs aléatoires", "random")
        self.strategy_combo.addItem("Similarity-based sampling", "similarity")
        options_layout.addRow("Stratégie:", self.strategy_combo)

        self.max_pairs_spin = QSpinBox()
        self.max_pairs_spin.setRange(10, 10000)
        self.max_pairs_spin.setValue(100)
        options_layout.addRow("Max paires:", self.max_pairs_spin)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        layout.addStretch()
        return widget

    def _create_manual_tab(self):
        """Create tab for manual pair entry."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Info
        info = QLabel(
            "✍️ Ajoutez manuellement des paires de vidéos avec leur vérité terrain."
        )
        layout.addWidget(info)

        # Test set name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nom du test set:"))
        self.manual_name_edit = QLineEdit()
        name_layout.addWidget(self.manual_name_edit)
        layout.addLayout(name_layout)

        # Add pair button
        add_pair_btn = QPushButton("➕ Ajouter une paire")
        add_pair_btn.clicked.connect(self._add_manual_pair)
        layout.addWidget(add_pair_btn)

        # Pairs table
        self.manual_pairs_table = QTableWidget()
        self.manual_pairs_table.setColumnCount(4)
        self.manual_pairs_table.setHorizontalHeaderLabels([
            "Vidéo 1", "Vidéo 2", "Type", "Actions"
        ])
        layout.addWidget(self.manual_pairs_table)

        return widget

    def _add_manual_pair(self):
        """Add manual test pair."""
        from PyQt6.QtWidgets import QFileDialog

        video1, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner Vidéo 1",
            "", "Videos (*.mp4 *.avi *.mkv *.mov)"
        )
        if not video1:
            return

        video2, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner Vidéo 2",
            "", "Videos (*.mp4 *.avi *.mkv *.mov)"
        )
        if not video2:
            return

        # Ask for type
        type_dialog = QDialog(self)
        type_dialog.setWindowTitle("Type de paire")
        layout = QVBoxLayout(type_dialog)

        layout.addWidget(QLabel("Ces deux vidéos sont-elles des doublons ?"))

        buttons = QDialogButtonBox()
        yes_btn = buttons.addButton("✓ Oui (Positive)", QDialogButtonBox.ButtonRole.YesRole)
        no_btn = buttons.addButton("✗ Non (Negative)", QDialogButtonBox.ButtonRole.NoRole)
        unknown_btn = buttons.addButton("? Inconnu", QDialogButtonBox.ButtonRole.RejectRole)

        buttons.clicked.connect(type_dialog.accept)
        layout.addWidget(buttons)

        type_dialog.exec()

        clicked = buttons.clickedButton()
        if clicked == yes_btn:
            expected = "positive"
        elif clicked == no_btn:
            expected = "negative"
        else:
            expected = "unknown"

        # Add to table
        row = self.manual_pairs_table.rowCount()
        self.manual_pairs_table.insertRow(row)
        self.manual_pairs_table.setItem(row, 0, QTableWidgetItem(video1))
        self.manual_pairs_table.setItem(row, 1, QTableWidgetItem(video2))
        self.manual_pairs_table.setItem(row, 2, QTableWidgetItem(expected))

        delete_btn = QPushButton("🗑️")
        delete_btn.clicked.connect(lambda: self.manual_pairs_table.removeRow(row))
        self.manual_pairs_table.setCellWidget(row, 3, delete_btn)
```

---

## 4. ARCHITECTURE ET ABSTRACTIONS

### ✨ Nouvelles Abstractions Proposées

#### 4.1 ProgressManager

```python
# managers/progress_manager.py

from typing import Dict, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal

class ProgressManager(QObject):
    """Manages all progress widgets centrally."""

    # Signals
    progress_updated = pyqtSignal(str, int, int)  # category, current, total
    status_updated = pyqtSignal(str, str, str)  # category, message, color

    def __init__(self):
        super().__init__()
        self.widgets: Dict[str, Any] = {}
        self.states: Dict[str, str] = {}  # category -> state

    def register_widget(self, category: str, widget):
        """Register a progress widget."""
        self.widgets[category] = widget
        self.states[category] = 'idle'

    def start(self, category: str, total: int = 0):
        """Start progress for a category."""
        if category not in self.widgets:
            return

        widget = self.widgets[category]
        widget.setVisible(True)
        widget.reset()
        if total > 0:
            widget.set_total(total)

        self.states[category] = 'running'

    def update(self, category: str, current: int, total: Optional[int] = None, message: str = ""):
        """Update progress."""
        if category not in self.widgets:
            return

        widget = self.widgets[category]
        widget.update_progress(current, total or widget.total)
        if message:
            widget.set_status(message)

        self.progress_updated.emit(category, current, total or 0)

    def finish(self, category: str, message: str = "Terminé", success: bool = True):
        """Finish progress."""
        if category not in self.widgets:
            return

        widget = self.widgets[category]
        color = 'green' if success else 'red'
        widget.set_status(message, color)

        self.states[category] = 'done' if success else 'error'

        # Auto-hide after 2s
        QTimer.singleShot(2000, lambda: widget.setVisible(False))

    def error(self, category: str, message: str):
        """Mark as error."""
        self.finish(category, f"Erreur: {message}", success=False)

    def hide_all(self):
        """Hide all progress widgets."""
        for widget in self.widgets.values():
            widget.setVisible(False)

    def is_running(self, category: Optional[str] = None) -> bool:
        """Check if any/specific category is running."""
        if category:
            return self.states.get(category) == 'running'
        return any(state == 'running' for state in self.states.values())
```

#### 4.2 WidgetRegistry

```python
# ui/widget_registry.py

from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import QWidget

class WidgetRegistry:
    """Central registry for all parameter widgets."""

    # Required widgets for basic functionality
    REQUIRED_WIDGETS = [
        'threshold_spin',
        'hash_method_combo',
        'hash_workers_spin',
        'comparison_workers_spin',
    ]

    # Optional widgets
    OPTIONAL_WIDGETS = [
        'batch_size_spin',
        'hash_timeout_spin',
        'comparison_timeout_spin',
        'comparison_algorithm_combo',
        # ... tous les autres
    ]

    # Widget groups
    WIDGET_GROUPS = {
        'hashing': [
            'threshold_spin', 'hash_method_combo', 'hash_workers_spin',
            'hash_timeout_spin',
        ],
        'comparison': [
            'comparison_workers_spin', 'batch_size_spin',
            'comparison_timeout_spin', 'comparison_algorithm_combo',
        ],
        'audio': [
            'audio_threshold_spin', 'audio_precision_combo',
            'audio_workers_spin', 'audio_cache_size_spin',
        ],
        # ... etc
    }

    def __init__(self):
        self.widgets: Dict[str, QWidget] = {}
        self.missing: List[str] = []

    def register_from_tab(self, tab: QWidget) -> bool:
        """
        Register all widgets from a tab.
        Returns True if all required widgets found.
        """
        self.widgets.clear()
        self.missing.clear()

        all_widgets = self.REQUIRED_WIDGETS + self.OPTIONAL_WIDGETS

        for name in all_widgets:
            widget = getattr(tab, name, None)
            if widget:
                self.widgets[name] = widget
            elif name in self.REQUIRED_WIDGETS:
                self.missing.append(name)

        return len(self.missing) == 0

    def get(self, name: str, default=None) -> Optional[QWidget]:
        """Get widget by name."""
        return self.widgets.get(name, default)

    def get_group(self, group: str) -> Dict[str, QWidget]:
        """Get all widgets from a group."""
        if group not in self.WIDGET_GROUPS:
            return {}

        return {
            name: self.widgets[name]
            for name in self.WIDGET_GROUPS[group]
            if name in self.widgets
        }

    def get_all(self) -> Dict[str, QWidget]:
        """Get all registered widgets."""
        return self.widgets.copy()

    def validate(self) -> bool:
        """Validate that all required widgets are present."""
        return len(self.missing) == 0

    def get_missing(self) -> List[str]:
        """Get list of missing required widgets."""
        return self.missing.copy()
```

#### 4.3 WorkflowController

```python
# controllers/workflow_controller.py

from enum import Enum, auto
from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal

class WorkflowState(Enum):
    """Analysis workflow states."""
    IDLE = auto()
    AUDIO_EXTRACTION = auto()
    AUDIO_COMPARISON = auto()
    VIDEO_HASHING = auto()
    VIDEO_COMPARISON = auto()
    SCENE_DETECTION = auto()
    SUBSEQUENCE_DETECTION = auto()
    VERIFICATION = auto()
    PROCESSING_DUPLICATES = auto()
    PROCESSING_SUBSEQUENCES = auto()
    COMPLETED = auto()
    ERROR = auto()

class WorkflowController(QObject):
    """Controls analysis workflow state machine."""

    # Signals
    state_changed = pyqtSignal(WorkflowState)
    workflow_completed = pyqtSignal()
    workflow_error = pyqtSignal(str)

    def __init__(self, progress_manager):
        super().__init__()
        self.progress_manager = progress_manager
        self.current_state = WorkflowState.IDLE
        self.previous_state = None

        # State → Progress category mapping
        self.state_progress_map = {
            WorkflowState.AUDIO_EXTRACTION: 'audio',
            WorkflowState.AUDIO_COMPARISON: 'audio_comparison',
            WorkflowState.VIDEO_HASHING: 'hash',
            WorkflowState.VIDEO_COMPARISON: 'comparison',
            WorkflowState.SCENE_DETECTION: 'scene',
            WorkflowState.SUBSEQUENCE_DETECTION: 'subsequence',
            WorkflowState.VERIFICATION: 'verification',
        }

    def transition_to(self, new_state: WorkflowState):
        """Transition to new state."""
        if new_state == self.current_state:
            return

        self.previous_state = self.current_state
        self.current_state = new_state

        # Hide previous progress
        if self.previous_state in self.state_progress_map:
            category = self.state_progress_map[self.previous_state]
            # Don't hide, let it finish naturally

        # Show new progress
        if new_state in self.state_progress_map:
            category = self.state_progress_map[new_state]
            self.progress_manager.start(category)

        # Emit signal
        self.state_changed.emit(new_state)

        # Handle special states
        if new_state == WorkflowState.COMPLETED:
            self.workflow_completed.emit()
            self.progress_manager.hide_all()
        elif new_state == WorkflowState.ERROR:
            self.progress_manager.hide_all()

    def update_progress(self, current: int, total: int, message: str = ""):
        """Update progress for current state."""
        if self.current_state in self.state_progress_map:
            category = self.state_progress_map[self.current_state]
            self.progress_manager.update(category, current, total, message)

    def error(self, message: str):
        """Handle error."""
        if self.current_state in self.state_progress_map:
            category = self.state_progress_map[self.current_state]
            self.progress_manager.error(category, message)

        self.transition_to(WorkflowState.ERROR)
        self.workflow_error.emit(message)

    def reset(self):
        """Reset to idle state."""
        self.progress_manager.hide_all()
        self.transition_to(WorkflowState.IDLE)

    def is_active(self) -> bool:
        """Check if workflow is active."""
        return self.current_state not in [
            WorkflowState.IDLE,
            WorkflowState.COMPLETED,
            WorkflowState.ERROR
        ]
```

---

## 5. INTERFACE UTILISATEUR

### ✨ Améliorations UI Proposées

#### 5.1 Réorganisation des Tabs Principaux

**Actuellement**: Tout dans une seule fenêtre avec left/right panels

**Proposition**: Tabs principaux au niveau racine

```
┌─────────────────────────────────────────────────────────┐
│ [🔍 Analyse] [📊 Benchmarks] [⚙️ Paramètres]          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Contenu de l'onglet actif                             │
│                                                          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Avantages**:
- Séparation claire des fonctionnalités
- Plus d'espace pour chaque section
- Navigation plus intuitive

#### 5.2 Dashboard Vue (Nouvelle)

```python
# ui/dashboard_view.py

class DashboardView(QWidget):
    """Overview dashboard for quick stats and actions."""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self._init_ui()

    def _init_ui(self):
        """Initialize dashboard."""
        layout = QVBoxLayout(self)

        # Welcome
        welcome = QLabel("<h1>🔍 Duplicate Finder</h1>")
        layout.addWidget(welcome)

        # Quick stats
        stats_layout = QHBoxLayout()

        # Stat card 1: Videos
        videos_card = self._create_stat_card(
            "📹 Vidéos",
            self._get_video_count(),
            "Hashées dans la DB"
        )
        stats_layout.addWidget(videos_card)

        # Stat card 2: Comparisons
        comparisons_card = self._create_stat_card(
            "🔍 Comparaisons",
            self._get_comparison_count(),
            "En cache"
        )
        stats_layout.addWidget(comparisons_card)

        # Stat card 3: Duplicates
        duplicates_card = self._create_stat_card(
            "📂 Doublons",
            self._get_pending_duplicates(),
            "En attente"
        )
        stats_layout.addWidget(duplicates_card)

        # Stat card 4: DB Size
        db_card = self._create_stat_card(
            "💾 Base de données",
            f"{self._get_db_size():.1f} MB",
            ""
        )
        stats_layout.addWidget(db_card)

        layout.addLayout(stats_layout)

        # Quick actions
        actions_group = QGroupBox("Actions Rapides")
        actions_layout = QGridLayout()

        # Row 1
        analyze_btn = self._create_action_button(
            "🔍 Analyser des vidéos",
            "Détecter les doublons",
            self._start_analysis
        )
        actions_layout.addWidget(analyze_btn, 0, 0)

        benchmark_btn = self._create_action_button(
            "📊 Lancer un benchmark",
            "Tester les pipelines",
            self._start_benchmark
        )
        actions_layout.addWidget(benchmark_btn, 0, 1)

        # Row 2
        settings_btn = self._create_action_button(
            "⚙️ Paramètres",
            "Configurer le plugin",
            self._open_settings
        )
        actions_layout.addWidget(settings_btn, 1, 0)

        cleanup_btn = self._create_action_button(
            "🗑️ Nettoyage",
            "Nettoyer la base",
            self._cleanup_database
        )
        actions_layout.addWidget(cleanup_btn, 1, 1)

        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        # Recent activity
        recent_group = QGroupBox("Activité Récente")
        recent_layout = QVBoxLayout()

        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(150)
        recent_layout.addWidget(self.recent_list)

        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)

        layout.addStretch()

        # Load data
        self._refresh_dashboard()

    def _create_stat_card(self, title: str, value: str, subtitle: str):
        """Create a stat card widget."""
        card = QGroupBox()
        card.setStyleSheet("""
            QGroupBox {
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                background: white;
            }
        """)

        layout = QVBoxLayout(card)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(title_label)

        value_label = QLabel(str(value))
        value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        layout.addWidget(value_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet("font-size: 10px; color: #999;")
            layout.addWidget(subtitle_label)

        return card

    def _create_action_button(self, title: str, description: str, callback):
        """Create an action button."""
        btn = QPushButton()
        btn.setMinimumHeight(80)
        btn.clicked.connect(callback)

        layout = QVBoxLayout(btn)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 11px; color: #666;")
        layout.addWidget(desc_label)

        return btn
```

#### 5.3 Themes et Apparence

```python
# ui/themes.py

class Theme:
    """Theme configuration."""

    # Colors
    PRIMARY = "#2196F3"
    SUCCESS = "#4CAF50"
    WARNING = "#FF9800"
    ERROR = "#F44336"
    INFO = "#00BCD4"

    # Styles
    BUTTON_STYLE = """
        QPushButton {
            background-color: {bg};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: {bg_hover};
        }
        QPushButton:pressed {
            background-color: {bg_pressed};
        }
        QPushButton:disabled {
            background-color: #ccc;
            color: #666;
        }
    """

    @classmethod
    def apply_to_app(cls, app):
        """Apply theme to application."""
        app.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 3px solid #2196F3;
            }
        """)
```

---

## 6. NOUVELLES FONCTIONNALITÉS

### ✨ Propositions de Fonctionnalités

#### 6.1 Profils de Configuration

```python
# managers/profile_manager.py

class ConfigProfile:
    """Configuration profile."""
    def __init__(self, name: str, config: UnifiedConfig):
        self.name = name
        self.config = config
        self.created_at = datetime.now()

class ProfileManager:
    """Manages configuration profiles."""

    PRESETS = {
        'quick': "Analyse rapide (moins précis)",
        'balanced': "Équilibré (recommandé)",
        'accurate': "Précis (plus lent)",
        'reencoded': "Spécialiste ré-encodage",
        'subsequence': "Détection sous-séquences",
    }

    def __init__(self, db_manager):
        self.db = db_manager
        self._create_table()
        self._ensure_presets()

    def save_profile(self, name: str, config: UnifiedConfig):
        """Save configuration as profile."""
        # Save to database
        pass

    def load_profile(self, name: str) -> Optional[UnifiedConfig]:
        """Load profile by name."""
        pass

    def list_profiles(self) -> List[str]:
        """List all saved profiles."""
        pass

    def delete_profile(self, name: str):
        """Delete a profile."""
        pass
```

#### 6.2 Batch Processing Queue

```python
# controllers/batch_controller.py

class BatchJob:
    """Batch processing job."""
    def __init__(self, job_id: str, files: List[str], config: UnifiedConfig):
        self.job_id = job_id
        self.files = files
        self.config = config
        self.status = 'pending'
        self.progress = 0
        self.created_at = datetime.now()

class BatchController(QObject):
    """Controls batch processing queue."""

    job_started = pyqtSignal(str)  # job_id
    job_progress = pyqtSignal(str, int, int)  # job_id, current, total
    job_completed = pyqtSignal(str)  # job_id

    def __init__(self):
        super().__init__()
        self.queue: List[BatchJob] = []
        self.current_job: Optional[BatchJob] = None

    def add_job(self, files: List[str], config: UnifiedConfig) -> str:
        """Add job to queue."""
        job_id = str(uuid.uuid4())
        job = BatchJob(job_id, files, config)
        self.queue.append(job)
        return job_id

    def process_queue(self):
        """Process all jobs in queue."""
        while self.queue:
            job = self.queue.pop(0)
            self._process_job(job)

    def _process_job(self, job: BatchJob):
        """Process single job."""
        self.current_job = job
        self.job_started.emit(job.job_id)
        # ... process
        self.job_completed.emit(job.job_id)
        self.current_job = None
```

#### 6.3 Duplicate Clusters

```python
# analysis/cluster_detector.py

class DuplicateCluster:
    """Group of related duplicates."""
    def __init__(self, files: List[str]):
        self.files = files
        self.representative = files[0]  # Fichier de référence
        self.total_size = sum(get_file_size(f) for f in files)
        self.potential_savings = self.total_size - get_file_size(self.representative)

class ClusterDetector:
    """Detects clusters of duplicates."""

    def __init__(self, db_manager):
        self.db = db_manager

    def find_clusters(self, threshold: float = 85.0) -> List[DuplicateCluster]:
        """
        Find clusters of duplicates using graph theory.

        Each video is a node, similarities above threshold are edges.
        Connected components = clusters.
        """
        # Build similarity graph
        graph = networkx.Graph()

        # Get all comparisons above threshold
        comparisons = self.db.get_comparisons_above_threshold(threshold)

        for file1, file2, similarity in comparisons:
            graph.add_edge(file1, file2, weight=similarity)

        # Find connected components
        clusters = []
        for component in networkx.connected_components(graph):
            files = list(component)
            if len(files) > 1:
                clusters.append(DuplicateCluster(files))

        # Sort by potential savings
        clusters.sort(key=lambda c: c.potential_savings, reverse=True)

        return clusters
```

#### 6.4 Export Reports

```python
# reports/report_generator.py

class ReportGenerator:
    """Generates analysis reports in various formats."""

    def __init__(self, db_manager):
        self.db = db_manager

    def generate_pdf(self, output_path: str):
        """Generate PDF report with charts."""
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet

        # ... generate PDF
        pass

    def generate_html(self, output_path: str):
        """Generate interactive HTML report."""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Duplicate Finder Report</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <h1>Duplicate Analysis Report</h1>

            <div id="chart1"></div>

            <script>
                // Interactive charts with Plotly
            </script>
        </body>
        </html>
        """
        pass

    def generate_csv(self, output_path: str):
        """Generate CSV with all duplicates."""
        import csv

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['File 1', 'File 2', 'Similarity', 'Size 1', 'Size 2', 'Status'])

            duplicates = self.db.get_all_duplicates()
            for dup in duplicates:
                writer.writerow([
                    dup['file1'],
                    dup['file2'],
                    f"{dup['similarity']:.2f}%",
                    format_size(dup['size1']),
                    format_size(dup['size2']),
                    dup['status']
                ])
```

#### 6.5 Smart Filters

```python
# ui/smart_filters.py

class SmartFilterDialog(QDialog):
    """Advanced filtering for duplicates."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Filtres Intelligents")
        self._init_ui()

    def _init_ui(self):
        """Initialize filter UI."""
        layout = QVBoxLayout(self)

        # Similarity range
        sim_group = QGroupBox("Plage de Similarité")
        sim_layout = QHBoxLayout()

        self.sim_min_spin = QDoubleSpinBox()
        self.sim_min_spin.setRange(0, 100)
        self.sim_min_spin.setValue(85)
        self.sim_min_spin.setSuffix("%")
        sim_layout.addWidget(QLabel("Min:"))
        sim_layout.addWidget(self.sim_min_spin)

        self.sim_max_spin = QDoubleSpinBox()
        self.sim_max_spin.setRange(0, 100)
        self.sim_max_spin.setValue(100)
        self.sim_max_spin.setSuffix("%")
        sim_layout.addWidget(QLabel("Max:"))
        sim_layout.addWidget(self.sim_max_spin)

        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)

        # File size difference
        size_group = QGroupBox("Différence de Taille")
        size_layout = QFormLayout()

        self.max_size_diff_spin = QDoubleSpinBox()
        self.max_size_diff_spin.setRange(0, 100)
        self.max_size_diff_spin.setValue(10)
        self.max_size_diff_spin.setSuffix("%")
        size_layout.addRow("Max différence:", self.max_size_diff_spin)

        size_group.setLayout(size_layout)
        layout.addWidget(size_group)

        # Duration difference
        duration_group = QGroupBox("Différence de Durée")
        duration_layout = QFormLayout()

        self.max_duration_diff_spin = QDoubleSpinBox()
        self.max_duration_diff_spin.setRange(0, 60)
        self.max_duration_diff_spin.setValue(5)
        self.max_duration_diff_spin.setSuffix(" s")
        duration_layout.addRow("Max différence:", self.max_duration_diff_spin)

        duration_group.setLayout(duration_layout)
        layout.addWidget(duration_group)

        # File path patterns
        path_group = QGroupBox("Filtres de Chemin")
        path_layout = QVBoxLayout()

        self.include_pattern_edit = QLineEdit()
        self.include_pattern_edit.setPlaceholderText("Inclure (regex)...")
        path_layout.addWidget(QLabel("Inclure:"))
        path_layout.addWidget(self.include_pattern_edit)

        self.exclude_pattern_edit = QLineEdit()
        self.exclude_pattern_edit.setPlaceholderText("Exclure (regex)...")
        path_layout.addWidget(QLabel("Exclure:"))
        path_layout.addWidget(self.exclude_pattern_edit)

        path_group.setLayout(path_layout)
        layout.addWidget(path_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_filters(self) -> Dict[str, Any]:
        """Get filter configuration."""
        return {
            'similarity_min': self.sim_min_spin.value(),
            'similarity_max': self.sim_max_spin.value(),
            'max_size_diff': self.max_size_diff_spin.value(),
            'max_duration_diff': self.max_duration_diff_spin.value(),
            'include_pattern': self.include_pattern_edit.text(),
            'exclude_pattern': self.exclude_pattern_edit.text(),
        }
```

---

## 7. PLAN D'IMPLÉMENTATION

### 📅 Phase 1 - Corrections Critiques (1-2 jours)

**Objectif**: Faire fonctionner le plugin sans erreurs

- [ ] 1.1 Corriger nommage des widgets (threshold_spin vs video_threshold_spin)
- [ ] 1.2 Compléter get_widget_dict() avec tous les widgets
- [ ] 1.3 Supprimer duplicate benchmark_runner.py
- [ ] 1.4 Remplacer indices de tabs hardcodés par objectName
- [ ] 1.5 Tester que l'analyse fonctionne de bout en bout

**Tests**:
- Lancer analyse standard
- Lancer analyse audio-first
- Sauvegarder/charger paramètres
- Lancer benchmark simple

---

### 📅 Phase 2 - Configuration Unifiée (2-3 jours)

**Objectif**: Simplifier la gestion des paramètres

- [ ] 2.1 Créer UnifiedConfig avec dataclasses
- [ ] 2.2 Créer UnifiedConfigManager
- [ ] 2.3 Créer SettingsDialog (fenêtre dédiée)
- [ ] 2.4 Intégrer dans main_window avec menu
- [ ] 2.5 Migrer ancien SettingsManager
- [ ] 2.6 Import/Export JSON

**Tests**:
- Ouvrir Settings Dialog
- Modifier tous les paramètres
- Sauvegarder et vérifier persistence
- Import/Export JSON

---

### 📅 Phase 3 - Benchmark Avancé (3-4 jours)

**Objectif**: Système de benchmark professionnel

- [ ] 3.1 Améliorer BenchmarkTabWidget
- [ ] 3.2 Créer TestSetWizard
- [ ] 3.3 Améliorer PipelineEditorWidget
- [ ] 3.4 Ajouter visualisations (matplotlib)
- [ ] 3.5 Historique et comparaison de runs
- [ ] 3.6 Export CSV/JSON/PDF

**Tests**:
- Créer test set manuel
- Créer test set automatique
- Lancer benchmark avec 5 pipelines
- Visualiser résultats
- Exporter rapport

---

### 📅 Phase 4 - Abstractions (2-3 jours)

**Objectif**: Code plus maintenable

- [ ] 4.1 Créer ProgressManager
- [ ] 4.2 Créer WidgetRegistry
- [ ] 4.3 Créer WorkflowController
- [ ] 4.4 Refactorer main_window pour utiliser ces abstractions
- [ ] 4.5 Réduire duplication de code

**Tests**:
- Lancer toutes les analyses
- Vérifier progress bars
- Tester workflow states

---

### 📅 Phase 5 - Nouvelles Features (3-5 jours)

**Objectif**: Fonctionnalités avancées

- [ ] 5.1 Dashboard vue
- [ ] 5.2 Profils de configuration
- [ ] 5.3 Batch processing queue
- [ ] 5.4 Cluster detection
- [ ] 5.5 Smart filters
- [ ] 5.6 Report generator

**Tests**:
- Chaque fonctionnalité individuellement

---

### 📅 Phase 6 - UI/UX (2-3 jours)

**Objectif**: Interface moderne et intuitive

- [ ] 6.1 Réorganiser tabs principaux
- [ ] 6.2 Appliquer theme
- [ ] 6.3 Améliorer tooltips et aide
- [ ] 6.4 Keyboard shortcuts
- [ ] 6.5 Polish général

---

### 📅 Phase 7 - Tests et Documentation (2-3 jours)

**Objectif**: Qualité et maintenabilité

- [ ] 7.1 Tests unitaires pour managers
- [ ] 7.2 Tests d'intégration
- [ ] 7.3 Documentation utilisateur
- [ ] 7.4 Documentation développeur
- [ ] 7.5 Vidéo tutoriel

---

## 📊 RÉCAPITULATIF

### Corrections à faire immédiatement

1. ✅ Renommer `video_threshold_spin` → `threshold_spin`
2. ✅ Compléter `_get_widget_dict()` avec 20+ widgets manquants
3. ✅ Supprimer `benchmark_runner.py` (doublon)
4. ✅ Remplacer indices hardcodés par objectName

### Améliorations majeures proposées

1. **Configuration unifiée** avec fenêtre dédiée
2. **Système de benchmark** professionnel
3. **Abstractions** (ProgressManager, WidgetRegistry, WorkflowController)
4. **Dashboard** pour vue d'ensemble
5. **Nouvelles features** (profils, batch, clusters, reports, filters)

### Impact attendu

- **Maintenabilité**: +200% (code mieux structuré)
- **User Experience**: +150% (UI plus claire, workflow simplifié)
- **Fonctionnalités**: +300% (beaucoup de nouvelles features)
- **Fiabilité**: +100% (moins de bugs, meilleurs tests)

---

**Prêt pour implémentation ?** 🚀
