# DuplicateFlow - Quick Reference

**Référence rapide pour reprendre le développement**

---

## 🚀 Démarrage rapide

### Import de base
```python
from duplicateflow.pipeline import Pipeline
from duplicateflow.pipeline.presets import PRESETS
from duplicateflow.sdk import Validator, LengthValidator
from duplicateflow.storage import StorageManager, PipelineStore
from duplicateflow.algorithms import list_algorithms, get_algorithm
```

### Utilisation simple
```python
# Via preset
pipeline = Pipeline.from_preset('balanced')
result = pipeline.compare('video1.mp4', 'video2.mp4')

# Custom pipeline
pipeline = Pipeline(
    steps=[
        {'algorithm': 'frame_hash', 'weight': 0.5, 'threshold': 80},
        {'algorithm': 'color_histogram', 'weight': 0.5, 'threshold': 70}
    ],
    global_threshold=75.0
)
result = pipeline.compare('video1.mp4', 'video2.mp4')
```

---

## 📚 Les 12 Presets

| Nom | Durée | Usage | Seuil |
|-----|-------|-------|-------|
| `fast` | ~30s | Scan rapide | 70.0 |
| `balanced` | ~2min | Usage général | 70.0 |
| `thorough` | ~5min | Haute précision | 75.0 |
| `multimodal` | ~8min | Visual + audio | 70.0 |
| `structural` | ~3min | Similarité géométrique | 65.0 |
| `hybrid` | ~4min | Sous-séquences | 70.0 |
| `audio_advanced` | ~6min | Focus audio | 65.0 |
| `motion_intense` | ~7min | Analyse mouvement | 60.0 |
| `fast_duplicates` | ~1min | Duplicates exacts | 85.0 |
| `accurate_scenes` | ~3min | Scènes similaires | 75.0 |
| `intro_detector` | ~30s | Détection intros | 75.0 |
| `credits_detector` | ~30s | Détection génériques | 75.0 |

### Accès aux presets
```python
from duplicateflow.pipeline.presets import (
    FAST_PRESET,
    BALANCED_PRESET,
    THOROUGH_PRESET,
    FAST_DUPLICATES_PRESET,
    # ...
)

# Ou dynamiquement
from duplicateflow.pipeline.presets import PRESETS
config = PRESETS['balanced']
```

---

## 🎯 Les 16 Algorithmes

### Par catégorie

**Statistical (Fast)**
- `frame_hash` - Perceptual hashing (pHash/dHash/aHash)
- `color_histogram` - RGB histogram comparison
- `color_moments` - Color statistical moments
- `ssim` - Structural Similarity Index

**Perceptual (Fast-Medium)**
- `dct_coefficients` - Discrete Cosine Transform
- `audio_spectrum` - Frequency spectrum analysis
- `audio_fingerprint` - Acoustic fingerprinting

**Structural (Medium)**
- `feature_matching` - ORB/SIFT keypoint matching
- `edge_pattern` - Canny edge detection
- `hog_descriptor` - Histogram of Oriented Gradients
- `template_matching` - Cross-correlation matching

**Temporal (Medium-Slow)**
- `motion_analysis` - Optical flow magnitude
- `optical_flow` - Dense optical flow
- `subsequence_detection` - Hybrid motion+hash

### Lister les algorithmes
```python
from duplicateflow.algorithms import list_algorithms, get_algorithm

# Tous les algorithmes
all_algos = list_algorithms()

# Par catégorie
perceptual = list_algorithms(category='perceptual')
structural = list_algorithms(category='structural')

# Obtenir un algorithme
algo = get_algorithm('frame_hash')
algo.configure(hash_type='phash', sample_rate=1.0)
result = algo.compare('video1.mp4', 'video2.mp4', start_time=0, duration=None)
```

---

## 🛠️ Fonctionnalités avancées

### 1. Pre/Post Validators (NEW)

```python
from duplicateflow.sdk import LengthValidator

# Pre-validation: filtre AVANT comparaison
pipeline = Pipeline(
    steps=[...],
    pre_validators=[
        LengthValidator(
            tolerance_percent=5.0,   # Max 5% différence
            tolerance_seconds=2.0,   # OU max 2s différence
            mode='any'  # 'any' (OR) ou 'all' (AND)
        )
    ]
)

# Si vidéos trop différentes en durée, retourne SKIPPED
result = pipeline.compare('short.mp4', 'long.mp4')
if result.status == VerificationStatus.SKIPPED:
    print(f"Skipped: {result.metadata['skip_reason']}")

# Post-validation: filtre APRÈS comparaison
class MinScoreValidator(Validator):
    """Require minimum score on specific algorithm"""
    def __init__(self, algorithm, min_score):
        self.algorithm = algorithm
        self.min_score = min_score

    def validate(self, short_video, long_video, result):
        # result contient les résultats de tous les algorithmes
        for method in result.individual_results:
            if method.algorithm == self.algorithm:
                if method.similarity < self.min_score:
                    return {
                        'accepted': False,
                        'reason': f'{self.algorithm} score too low: {method.similarity:.1f}%',
                        'metadata': {}
                    }
        return {'accepted': True, 'reason': 'OK', 'metadata': {}}

pipeline = Pipeline(
    steps=[...],
    post_validators=[
        MinScoreValidator('frame_hash', min_score=85.0)
    ]
)
# Si frame_hash < 85%, result.accepted = False
```

### 2. Partial Analysis (NEW)

```python
# Analyse seulement les 60 premières secondes
pipeline = Pipeline(
    steps=[...],
    analyze_duration=60.0,      # 60 secondes
    analyze_from_start=True     # Depuis le début
)

# Analyse seulement les 30 dernières secondes
pipeline = Pipeline(
    steps=[...],
    analyze_duration=30.0,      # 30 secondes
    analyze_from_start=False    # Depuis la fin
)
```

### 3. Early Termination

```python
# Arrête dès que score > threshold + margin
pipeline = Pipeline(
    steps=[...],
    global_threshold=70.0,
    early_termination=True,
    early_termination_margin=10.0  # Stop si score > 80
)
```

### 4. Storage & Caching

```python
from duplicateflow.storage import StorageManager

# Initialisation
storage = StorageManager(cache_dir="~/.duplicateflow/cache")

# File hashing
hash1 = storage.get_file_hash('video1.mp4')  # Auto-cached
hash2 = storage.get_file_hash('video2.mp4', fast=True)  # Fast hash

# Result caching (automatique dans Pipeline)
cached = storage.get_cached_result(
    'video1.mp4', 'video2.mp4',
    'frame_hash',
    {'hash_type': 'phash'}
)

# Feature caching
features = storage.get_cached_features(hash1, 'histogram')
if not features:
    features = extract_features(...)
    storage.cache_features(hash1, 'histogram', features)

# Statistics
stats = storage.get_statistics()
print(f"Cache hit rate: {stats['hit_rate']}%")
```

### 5. Pipeline Storage (NEW)

```python
from duplicateflow.storage import PipelineStore

# Initialisation
store = PipelineStore(db_path="pipelines.db")

# Sauvegarder une pipeline
config = {
    'steps': [...],
    'global_threshold': 75.0,
    'pre_validators': [...]
}
store.save_pipeline("my_custom_pipeline", config, is_default=False)

# Charger une pipeline
loaded_config = store.load_pipeline("my_custom_pipeline")
pipeline = Pipeline(**loaded_config)

# Lister toutes les pipelines
all_pipelines = store.list_pipelines()
default_only = store.list_pipelines(defaults_only=True)

# Supprimer une pipeline
store.delete_pipeline("my_custom_pipeline")
```

---

## 📊 Format des résultats

### VerificationResult
```python
@dataclass
class VerificationResult:
    global_score: float           # 0-100
    accepted: bool                # True si score > threshold
    status: VerificationStatus    # CONFIRMED/REJECTED/SKIPPED
    individual_results: List[MethodResult]
    metadata: Dict                # Infos supplémentaires

# Utilisation
result = pipeline.compare('video1.mp4', 'video2.mp4')
print(f"Score: {result.global_score:.2f}%")
print(f"Accepted: {result.accepted}")
print(f"Status: {result.status}")

for method in result.individual_results:
    print(f"  {method.algorithm}: {method.similarity:.2f}%")
```

### MethodResult
```python
@dataclass
class MethodResult:
    algorithm: str        # Nom de l'algorithme
    similarity: float     # 0-100
    accepted: bool        # True si > threshold
    threshold: float      # Seuil utilisé
    weight: float         # Poids (0.0-1.0)
    metadata: Dict        # frames_analyzed, execution_time_ms, etc.
```

---

## 🔧 Créer un algorithme custom

```python
from duplicateflow.sdk import Algorithm
from duplicateflow.core.registry import register_algorithm

@register_algorithm(
    name="my_custom_algo",
    display_name="🎨 My Custom Algorithm",
    category="perceptual",
    speed="medium",
    default_threshold=70.0,
    default_params={
        'param1': 'default_value',
        'param2': 42
    },
    use_case="What my algorithm is good for"
)
class MyCustomAlgorithm(Algorithm):
    def configure(self, **params):
        self.param1 = params.get('param1', 'default_value')
        self.param2 = params.get('param2', 42)
        # Initialize any resources

    def compare(self, short_video, long_video, start_time, duration):
        try:
            # 1. Extract features
            features1 = self._extract_features(short_video)
            features2 = self._extract_features(long_video, start_time, duration)

            # 2. Compare
            similarity = self._compute_similarity(features1, features2)

            # 3. Return standardized format
            return {
                'similarity': similarity,  # 0-100
                'accepted': similarity >= self.threshold,
                'metadata': {
                    'frames_analyzed': len(features1),
                    'execution_time_ms': execution_time,
                    'custom_info': 'any additional info'
                }
            }
        except Exception as e:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': str(e),
                    'frames_analyzed': 0,
                    'execution_time_ms': 0.0
                }
            }

    def _extract_features(self, video_path, start=0, duration=None):
        # Your feature extraction logic
        pass

    def _compute_similarity(self, features1, features2):
        # Your similarity computation
        pass
```

---

## 🔧 Créer un validator custom

```python
from duplicateflow.sdk import Validator

class MyCustomValidator(Validator):
    def __init__(self, min_resolution=None, max_size_mb=None):
        self.min_resolution = min_resolution
        self.max_size_mb = max_size_mb

    def validate(self, short_video, long_video, result=None):
        """
        Args:
            short_video: Path to short video
            long_video: Path to long video
            result: VerificationResult (None for pre-validation)

        Returns:
            {
                'accepted': bool,
                'reason': str,
                'metadata': dict
            }
        """
        try:
            # Check resolution
            if self.min_resolution:
                res1 = get_resolution(short_video)
                res2 = get_resolution(long_video)
                if res1[0] < self.min_resolution[0] or res1[1] < self.min_resolution[1]:
                    return {
                        'accepted': False,
                        'reason': f'Short video resolution too low: {res1}',
                        'metadata': {'resolution': res1}
                    }

            # All checks passed
            return {
                'accepted': True,
                'reason': 'All validation checks passed',
                'metadata': {}
            }
        except Exception as e:
            return {
                'accepted': False,
                'reason': f'Validation error: {str(e)}',
                'metadata': {'error': str(e)}
            }

# Utilisation
pipeline = Pipeline(
    steps=[...],
    pre_validators=[
        MyCustomValidator(min_resolution=(1280, 720), max_size_mb=500)
    ]
)
```

---

## 🧪 Testing

### Tests unitaires
```bash
# Tous les tests
pytest duplicateflow/tests/

# Tests spécifiques
pytest duplicateflow/tests/test_pipeline.py
pytest duplicateflow/tests/test_validators.py
pytest duplicateflow/tests/test_algorithms.py
pytest duplicateflow/tests/test_storage.py

# Avec coverage
pytest --cov=duplicateflow duplicateflow/tests/
```

### Tests manuels
```python
# Test d'un algorithme
from duplicateflow.algorithms import get_algorithm

algo = get_algorithm('frame_hash')
algo.configure(hash_type='phash')
result = algo.compare('test1.mp4', 'test2.mp4', 0, None)
print(result)

# Test d'une pipeline
from duplicateflow.pipeline import Pipeline

pipeline = Pipeline.from_preset('fast')
result = pipeline.compare('test1.mp4', 'test2.mp4')
print(f"Score: {result.global_score:.2f}%")
```

---

## 🐛 Debugging

### Activer les logs
```python
import logging

# DuplicateFlow logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('duplicateflow')
logger.setLevel(logging.DEBUG)

# Pipeline execution
pipeline = Pipeline.from_preset('balanced')
result = pipeline.compare('v1.mp4', 'v2.mp4')
# Verra tous les logs de chaque algorithme
```

### Vérifier le cache
```python
from duplicateflow.storage import StorageManager

storage = StorageManager()
stats = storage.get_statistics()
print(f"Results cached: {stats['results_cached']}")
print(f"Features cached: {stats['features_cached']}")
print(f"Cache hit rate: {stats['hit_rate']}%")

# Clear cache si besoin
storage.clear_cache()
```

### Analyser les performances
```python
import time

start = time.time()
result = pipeline.compare('v1.mp4', 'v2.mp4')
duration = time.time() - start

print(f"Total time: {duration:.2f}s")
for method in result.individual_results:
    exec_time = method.metadata.get('execution_time_ms', 0) / 1000
    print(f"  {method.algorithm}: {exec_time:.2f}s")
```

---

## 📁 Structure des fichiers importants

```
duplicateflow/
├── pipeline/
│   ├── pipeline.py         # ⭐ Pipeline class (MODIFIÉ)
│   └── presets.py          # ⭐ 12 presets (MODIFIÉ)
│
├── sdk/
│   ├── __init__.py         # ⭐ Exports (MODIFIÉ)
│   ├── algorithm.py        # Base class pour algorithmes
│   └── validator.py        # ⭐ NEW: Validators
│
├── storage/
│   ├── __init__.py         # ⭐ Exports (MODIFIÉ)
│   ├── storage_manager.py  # Interface unifiée
│   └── pipeline_store.py   # ⭐ NEW: Pipeline persistence
│
├── algorithms/
│   ├── __init__.py         # Auto-discovery
│   └── [16 algorithm files]
│
└── core/
    ├── registry.py         # Algorithm registry
    └── models.py           # VerificationResult, etc.
```

---

## 🔗 Intégration avec duplicate_finder

### Charger les presets dans l'UI
```python
# src/plugins/duplicate_finder/orchestration/pipeline_manager.py

from duplicateflow.integration import DuplicateFlowAPI

class PipelineManager:
    def load_default_protocols(self):
        """Load DuplicateFlow presets"""
        protocols = DuplicateFlowAPI.get_default_protocols()

        for name, config in protocols.items():
            if not self.store.pipeline_exists(name):
                self.store.save_pipeline(name, config, is_default=True)
```

### Exécuter une pipeline
```python
from duplicateflow.pipeline import Pipeline

def execute_pipeline(self, pipeline_name, short_video, long_video):
    # Load config
    config = self.store.load_pipeline(pipeline_name)

    # Create pipeline
    pipeline = Pipeline(**config)

    # Execute
    result = pipeline.compare(short_video, long_video)

    return result
```

### Lister les algorithmes disponibles
```python
from duplicateflow.algorithms import list_algorithms

def get_available_methods(self):
    """Get all algorithms from DuplicateFlow"""
    algos = list_algorithms()

    return [
        {
            'name': algo.name,
            'display_name': algo.display_name,
            'category': algo.category,
            'speed': algo.speed,
            'threshold': algo.default_threshold
        }
        for algo in algos
    ]
```

---

## 🚨 Points d'attention

### 1. Validators vs Thresholds
- **Validators**: Filtrent AVANT comparaison (pre) ou APRÈS (post)
- **Thresholds**: Critères PENDANT comparaison (chaque algorithme)

### 2. Weights doivent sommer à 1.0
```python
# ❌ INCORRECT
steps = [
    {'algorithm': 'A', 'weight': 30, ...},  # Entier
    {'algorithm': 'B', 'weight': 70, ...}
]

# ✅ CORRECT
steps = [
    {'algorithm': 'A', 'weight': 0.3, ...},  # Décimal
    {'algorithm': 'B', 'weight': 0.7, ...}   # Total = 1.0
]
```

### 3. Cache invalidation
Le cache utilise MD5 du fichier + config. Si fichier modifié, nouveau hash = nouveau cache.

### 4. analyze_duration vs duration parameter
- `analyze_duration` (Pipeline): Limite globale pour TOUS les algorithmes
- `duration` (compare()): Limite pour UNE comparaison spécifique

### 5. Pre-validators peuvent skip toute la comparaison
Si un pre-validator rejette, la pipeline retourne SKIPPED sans exécuter d'algorithmes.

---

## 📝 Checklist pour reprise de développement

- [ ] Lire `DUPLICATEFLOW_ARCHITECTURE.md` pour vue d'ensemble
- [ ] Vérifier état du git: `git status`, `git log -5`
- [ ] Tester imports: `python -c "from duplicateflow.pipeline import Pipeline"`
- [ ] Vérifier tests: `pytest duplicateflow/tests/ -v`
- [ ] Vérifier intégration UI: tests dans `tests/duplicate_finder/`
- [ ] Consulter `CURRENT_WORK.md` pour tâches en cours
- [ ] Vérifier issues GitHub pour bugs/features
- [ ] Revoir derniers commits pour contexte

---

## 🖥️ CLI Reference

DuplicateFlow propose une interface en ligne de commande complète. Voir [CLI_REFERENCE.md](CLI_REFERENCE.md) pour documentation détaillée.

### Commandes principales

```bash
# Comparer deux vidéos
duplicateflow compare short.mp4 long.mp4 --preset balanced

# Indexer une bibliothèque
duplicateflow index /videos --workers 8

# Trouver duplicates
duplicateflow find-duplicates /videos --min-confidence 30

# Recherche optimisée
duplicateflow search intro.mp4 film.mp4 --strategy cascade

# Lister algorithmes
duplicateflow list-algorithms

# Lister presets
duplicateflow list-presets

# Voir stats index
duplicateflow stats

# Voir stats cache
duplicateflow cache stats
```

### Modes de find-duplicates

**1. Audio Fingerprinting (O(N))**:
```bash
duplicateflow find-duplicates /videos
# Utilise l'index de fingerprints pour matching rapide
```

**2. Single Algorithm (O(N²))**:
```bash
duplicateflow find-duplicates /videos --algorithm frame_hash --threshold 85
# Comparaison par paires avec un seul algorithme
```

**3. Pipeline (O(N²) avec multi-algorithmes)**:
```bash
duplicateflow find-duplicates /videos --pipeline thorough
# Scoring pondéré avec plusieurs algorithmes
```

### Stratégies de recherche

```bash
# Cascade (rapide, 95% précision)
duplicateflow search scene.mp4 movie.mp4 --strategy cascade

# Parallel (exhaustif, multi-core)
duplicateflow search scene.mp4 movie.mp4 --strategy parallel --workers 8

# Adaptive (balance vitesse/précision)
duplicateflow search scene.mp4 movie.mp4 --strategy adaptive

# Linear (exhaustif, lent)
duplicateflow search scene.mp4 movie.mp4 --strategy linear
```

### Batch processing

```bash
# Traiter tous contre une référence
duplicateflow batch /videos reference.mp4 --output results.csv

# Matrice N-to-N
duplicateflow matrix /videos --output similarity.csv
```

---

## 📞 Ressources

- **Architecture complète**: [DUPLICATEFLOW_ARCHITECTURE.md](DUPLICATEFLOW_ARCHITECTURE.md)
- **CLI Reference**: [CLI_REFERENCE.md](CLI_REFERENCE.md)
- **Processing Guide**: [PROCESSING_GUIDE.md](PROCESSING_GUIDE.md)
- **État actuel**: [CURRENT_WORK.md](CURRENT_WORK.md)
- **Tests**: `duplicateflow/tests/`
- **CLI help**: `duplicateflow --help`

---

**Dernière mise à jour**: 2025-12-19
**Branch**: feature/duplicateflow-fusion
**Phase**: 12 - Post-cleanup
**Coverage**: 100% fonctionnalités + CLI + Processing
