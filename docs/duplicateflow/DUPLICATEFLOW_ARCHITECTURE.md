# DuplicateFlow - Architecture Complete

## Table des Matieres

1. [Vue d'ensemble](#vue-densemble)
2. [Structure des modules](#structure-des-modules)
3. [Diagramme des dependances](#diagramme-des-dependances)
4. [Points d'entree principaux](#points-dentrée-principaux)
5. [Cycle de vie d'une detection](#cycle-de-vie-dune-détection)
6. [Patterns architecturaux](#patterns-architecturaux)

---

## Vue d'ensemble

DuplicateFlow est une bibliotheque Python modulaire pour la detection de duplicatas video. Elle utilise une architecture en couches avec:

- **49 fichiers Python** dans le module principal
- **14 algorithmes** de detection enregistres dans un registry global
- **12 presets** pre-configures pour differents cas d'usage
- **API unifiee** pour l'integration dans des applications tierces

### Principes de conception

1. **Modularite**: Chaque algorithme est un plugin independant
2. **Extensibilite**: Systeme de registry pour ajouter de nouveaux algorithmes
3. **Performance**: Cache multi-niveaux (features, resultats, LSH)
4. **Scalabilite**: Support du traitement parallele et de l'indexation LSH

---

## Structure des modules

```
duplicateflow/
├── api/                      # API publique unifiee
│   ├── __init__.py
│   └── detection.py          # DetectionEngine (N-to-N, 1-to-1)
│
├── algorithms/               # 14 algorithmes de detection
│   ├── base/                 # Classes de base (VideoLoader, FrameExtractor)
│   ├── frame_hash.py         # pHash/dHash/aHash
│   ├── audio_fingerprint.py  # Shazam-style fingerprinting
│   ├── color_histogram.py    # Histogrammes HSV
│   ├── color_moments.py      # Moments statistiques
│   ├── ssim.py               # Structural Similarity
│   ├── motion_analysis.py    # Analyse de mouvement
│   ├── optical_flow.py       # Flux optique dense
│   ├── dct_coefficients.py   # Coefficients DCT
│   ├── edge_pattern.py       # Patterns de contours
│   ├── feature_matching.py   # SIFT/ORB/AKAZE
│   ├── hog_descriptor.py     # Histogrammes de gradients
│   ├── template_matching.py  # Correspondance de templates
│   ├── audio_spectrum.py     # Spectrogrammes audio
│   └── subsequence_detection.py  # Detection de sous-sequences
│
├── core/                     # Coeur du systeme
│   ├── models.py             # Dataclasses (Match, MatchResult)
│   └── registry.py           # Registry global des algorithmes
│
├── sdk/                      # SDK pour extensibilite
│   ├── algorithm.py          # Classe de base Algorithm
│   └── validator.py          # Validateurs (LengthValidator)
│
├── pipeline/                 # Orchestration multi-algorithmes
│   ├── pipeline.py           # Classe Pipeline (weighted scoring)
│   └── presets.py            # 12 presets pre-configures
│
├── processing/               # Traitement parallele et optimisations
│   ├── batch_processor.py    # Traitement par batch
│   ├── parallel_search.py    # Recherche parallele
│   ├── cascade_filter.py     # Filtrage en cascade
│   ├── fingerprint_index.py  # Index de fingerprints (SQLite)
│   └── lsh_index.py          # LSH pour recherche rapide
│
├── storage/                  # Persistance et cache
│   ├── storage_manager.py    # Gestionnaire de cache
│   ├── feature_cache.py      # Cache de features
│   ├── result_cache.py       # Cache de resultats
│   └── pipeline_store.py     # Stockage de pipelines custom
│
├── cli/                      # Interface ligne de commande
│   ├── main.py               # Point d'entree CLI
│   └── find_duplicates.py    # Commande find-duplicates
│
├── config/                   # Configuration
│   └── __init__.py           # Parametres par defaut
│
└── utils/                    # Utilitaires
    └── hashing.py            # Fonctions de hash
```

### Modules detailles

#### 1. **api/** - API Publique

**detection.py**:
- `DetectionEngine`: Point d'entree principal
  - `find_duplicates()`: Detection N-to-N (tout vs tout)
  - `compare_videos()`: Comparaison 1-to-1 (GUI preview)
- `DetectionMode`: Enum (FINGERPRINT, ALGORITHM, PIPELINE, ONE_TO_ONE)
- `MatchResult`: Dataclass pour les resultats
- `DetectionResult`: Resultats complets avec statistiques

#### 2. **algorithms/** - Bibliotheque d'algorithmes

Chaque algorithme herite de `Algorithm` et implemente:
- `configure(**params)`: Configuration des parametres
- `compare(short_video, long_video, start_time, duration)`: Comparaison
- `extract_features(video_path)`: Extraction de features (optionnel)
- `compare_features(features1, features2, threshold)`: Comparaison de features (optionnel)

**Categorisation**:
- **Perceptual**: frame_hash, ssim
- **Statistical**: color_histogram, color_moments
- **Motion**: motion_analysis, optical_flow
- **Structural**: edge_pattern, hog_descriptor, feature_matching, template_matching
- **Temporal**: dct_coefficients, subsequence_detection
- **Audio**: audio_fingerprint, audio_spectrum

#### 3. **core/** - Coeur du systeme

**registry.py**:
```python
# Registry global pour la decouverte d'algorithmes
_registry = AlgorithmRegistry()  # Singleton

# Enregistrement via decorateur
@register_algorithm(
    name="frame_hash",
    display_name="🔐 Frame Hash",
    category="perceptual",
    speed="fast",
    default_threshold=80.0
)
class FrameHashAlgorithm(Algorithm):
    ...

# Recuperation d'un algorithme
AlgoClass = get_algorithm("frame_hash")
algo = AlgoClass()
```

#### 4. **sdk/** - SDK pour extensions

**algorithm.py**:
- `Algorithm`: Classe abstraite de base
  - Methodes abstraites: `configure()`, `compare()`
  - Helpers: `_validate_video_path()`, `_validate_time_params()`

**validator.py**:
- `Validator`: Classe abstraite pour validation
- `LengthValidator`: Validation de duree (tolerance_percent, tolerance_seconds)

#### 5. **pipeline/** - Orchestration

**pipeline.py**:
```python
# Pipeline = combinaison d'algorithmes avec poids
pipeline = Pipeline([
    {'algorithm': 'frame_hash', 'weight': 0.3, 'threshold': 80},
    {'algorithm': 'color_histogram', 'weight': 0.4, 'threshold': 70},
    {'algorithm': 'motion_analysis', 'weight': 0.3, 'threshold': 70}
], global_threshold=70.0)

# Execution
result = pipeline.compare('short.mp4', 'long.mp4')
# => {'global_score': 75.2, 'accepted': True, ...}
```

**presets.py**:
- 12 presets pre-configures (FAST, BALANCED, THOROUGH, etc.)
- `get_preset(name)`: Recuperer un preset par nom

#### 6. **processing/** - Optimisations

**fingerprint_index.py**:
- `FingerprintIndex`: Index SQLite pour audio fingerprints
- Support de millions de videos avec recherche efficace

**lsh_index.py**:
- `MinHashLSH`: Locality-Sensitive Hashing
- Reduction de complexite: O(N²) → O(N×C)
- `LSHFingerprintIndex`: Wrapper pour FingerprintIndex

#### 7. **storage/** - Persistance

**storage_manager.py**:
- Cache de features par video (SQLite)
- Cache de resultats par paire (SQLite)
- Verification MD5 pour duplicatas exacts

**pipeline_store.py**:
- Sauvegarde/chargement de pipelines custom
- Base SQLite avec metadata (usage_count, timestamps)

---

## Diagramme des dependances

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI / GUI                                │
│                    (Couche Application)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DetectionEngine                              │
│                      (api/detection.py)                          │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐     │
│  │ FINGERPRINT │  ALGORITHM  │  PIPELINE   │ ONE_TO_ONE  │     │
│  └──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┘     │
└─────────┼─────────────┼─────────────┼─────────────┼────────────┘
          │             │             │             │
          ▼             ▼             ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐
│FingerprintIdx│ │  Algorithm   │ │      Pipeline            │
│ + LSH Index  │ │   (single)   │ │ (multi-algo weighted)    │
└──────┬───────┘ └──────┬───────┘ └──────┬───────────────────┘
       │                │                │
       │                └────────┬───────┘
       │                         │
       ▼                         ▼
┌──────────────────────────────────────────────┐
│           AlgorithmRegistry                   │
│         (core/registry.py)                    │
│  ┌────────────────────────────────────────┐  │
│  │  14 Registered Algorithms               │  │
│  │  - frame_hash, color_histogram, ...     │  │
│  └────────────────────────────────────────┘  │
└───────────────────┬──────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────┐
│         Algorithm Base Classes                │
│       (sdk/algorithm.py)                      │
│  - configure()                                │
│  - compare()                                  │
│  - extract_features()                         │
└───────────────────┬──────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────┐
│        VideoLoader / FrameExtractor           │
│      (algorithms/base/)                       │
│  - OpenCV video reading                       │
│  - Frame extraction at timestamps             │
└───────────────────┬──────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────┐
│          Storage & Cache                      │
│       (storage/)                              │
│  - StorageManager (features, results)         │
│  - PipelineStore (custom pipelines)           │
│  - FeatureCache, ResultCache                  │
└──────────────────────────────────────────────┘
```

### Flux de donnees

```
Video Files
    ↓
VideoLoader → Frames
    ↓
Algorithm.extract_features() → Features
    ↓
FeatureCache (SQLite) → Cached Features
    ↓
Algorithm.compare_features() → Similarity
    ↓
ResultCache (SQLite) → Cached Results
    ↓
Pipeline (weighted scoring) → Global Score
    ↓
DetectionEngine → MatchResult
```

---

## Points d'entree principaux

### 1. DetectionEngine (API unifiee)

**Utilisation typique**:
```python
from duplicateflow.api import DetectionEngine, DetectionMode

# N-to-N fingerprint detection
engine = DetectionEngine(mode=DetectionMode.FINGERPRINT)
result = engine.find_duplicates(
    directory="/videos",
    workers=8,
    min_confidence=15.0,
    use_lsh=True
)

# N-to-N pipeline detection
engine = DetectionEngine(mode=DetectionMode.PIPELINE, pipeline='balanced')
result = engine.find_duplicates(
    directory="/videos",
    workers=4,
    min_confidence=60.0
)

# 1-to-1 comparison
engine = DetectionEngine(mode=DetectionMode.ONE_TO_ONE, pipeline='thorough')
match = engine.compare_videos('short.mp4', 'long.mp4')
```

### 2. Pipeline (orchestration multi-algorithmes)

**Creation manuelle**:
```python
from duplicateflow.pipeline import Pipeline

pipeline = Pipeline(
    steps=[
        {
            'algorithm': 'frame_hash',
            'weight': 0.3,
            'threshold': 80,
            'params': {'hash_method': 'pHash', 'num_samples': 8}
        },
        {
            'algorithm': 'color_histogram',
            'weight': 0.7,
            'threshold': 70
        }
    ],
    global_threshold=70.0,
    early_termination=True
)

result = pipeline.compare('video1.mp4', 'video2.mp4')
```

**Depuis preset**:
```python
pipeline = Pipeline.from_preset('balanced')
result = pipeline.compare('video1.mp4', 'video2.mp4')
```

### 3. Algorithm (utilisation directe)

```python
from duplicateflow.core import get_algorithm

# Recuperer l'algorithme
AlgoClass = get_algorithm('frame_hash')
algo = AlgoClass()

# Configurer
algo.configure(
    threshold=80.0,
    hash_method='pHash',
    num_samples=8
)

# Comparer
result = algo.compare('short.mp4', 'long.mp4')
# => {'similarity': 0.85, 'accepted': True, 'metadata': {...}}
```

### 4. CLI (ligne de commande)

```bash
# Detection N-to-N avec fingerprinting
duplicateflow find-duplicates /videos --workers 8

# Pipeline custom
duplicateflow find-duplicates /videos --preset balanced

# Avec LSH
duplicateflow find-duplicates /videos --use-lsh --lsh-threshold 100
```

---

## Cycle de vie d'une detection

### Mode FINGERPRINT (N-to-N scalable)

```
1. Indexation
   ├─ Extraire audio de chaque video
   ├─ Calculer spectrogram (STFT)
   ├─ Detecter pics spectraux
   ├─ Construire landmark hashes
   └─ Stocker dans FingerprintIndex (SQLite)
        ├─ Table: videos (id, path, duration, hash_count)
        └─ Table: fingerprints (hash, timestamp, video_id)

2. Recherche
   ├─ Pour chaque video:
   │   ├─ Recuperer ses fingerprints
   │   ├─ Matcher avec autres videos
   │   └─ Voter sur time offsets
   └─ Filtrer par min_votes et min_confidence

3. LSH (optionnel, si N > 100 videos)
   ├─ Construire MinHash signatures
   ├─ Bander les signatures en buckets
   ├─ Chercher uniquement dans buckets similaires
   └─ Reduction: O(N²) → O(N×C) où C << N
```

### Mode ALGORITHM (single algo, N-to-N)

```
1. Collection
   └─ Scanner directory pour videos (.mp4, .mkv, etc.)

2. Extraction de features (avec cache)
   ├─ Pour chaque video:
   │   ├─ Verifier FeatureCache
   │   ├─ Si absent: algo.extract_features(video)
   │   └─ Stocker dans cache
   └─ Features = representation compacte (hashes, histogrammes, etc.)

3. Comparaison pairwise
   ├─ Pour chaque paire (i, j):
   │   ├─ Verifier ResultCache
   │   ├─ Si absent: algo.compare_features(feat_i, feat_j)
   │   └─ Stocker dans cache
   └─ Parallelisation avec ThreadPoolExecutor

4. Filtrage
   └─ Garder paires avec similarity >= min_confidence
```

### Mode PIPELINE (multi-algo, N-to-N)

```
1. Collection
   └─ Scanner directory pour videos

2. Pre-validation (optionnel)
   ├─ LengthValidator: filtrer paires avec durees differentes
   └─ Skip comparaison si validation echoue

3. Comparaison par pipeline
   ├─ Pour chaque paire (i, j):
   │   ├─ Check MD5 (duplicatas exacts)
   │   ├─ Pour chaque algorithme dans steps:
   │   │   ├─ Verifier ResultCache
   │   │   ├─ Si absent: algo.compare()
   │   │   ├─ Stocker dans cache
   │   │   └─ Accumuler: global_score += similarity × weight
   │   ├─ Early termination si global_score > threshold + margin
   │   └─ Post-validation (optionnel)
   └─ Return: {'global_score': X, 'accepted': bool, 'individual_results': [...]}

4. Filtrage
   └─ Garder paires avec global_score >= global_threshold
```

### Mode ONE_TO_ONE (comparaison unique pour GUI)

```
1. Pre-validation (optionnel)
   └─ LengthValidator, custom validators

2. Partial Analysis (optionnel)
   ├─ analyze_duration = 60.0  # Ne comparer que 60 premieres secondes
   └─ analyze_from_start = True/False  # Depuis debut ou fin

3. Pipeline execution
   ├─ Pour chaque algorithme:
   │   ├─ Extraire features avec limite de duree
   │   ├─ Comparer
   │   └─ Accumuler score pondere
   └─ Return: MatchResult avec similarity, confidence, match_type

4. Classification
   ├─ similarity >= 80%: DUPLICATE
   ├─ similarity >= 60%: SCENE
   ├─ similarity >= 15%: EXTRACT
   └─ similarity < 15%: UNCERTAIN
```

---

## Patterns architecturaux

### 1. Registry Pattern

**Objectif**: Decouverte automatique des algorithmes sans couplage fort.

```python
# Enregistrement (dans algorithm file)
@register_algorithm(name="my_algo", ...)
class MyAlgorithm(Algorithm):
    pass

# Recuperation (n'importe où)
AlgoClass = get_algorithm("my_algo")
```

**Avantages**:
- Pas de imports explicites necessaires
- Extensibilite: ajouter un algorithme = creer une classe + decorateur
- Introspection: `list_algorithms()` pour decouvrir tous les algos

### 2. Strategy Pattern

**Objectif**: Interchanger les algorithmes dynamiquement.

```python
# Choisir la strategie
algo_name = "frame_hash"  # ou "color_histogram", "ssim", etc.

# Instantier
AlgoClass = get_algorithm(algo_name)
algo = AlgoClass()

# Executer
result = algo.compare(video1, video2)
```

### 3. Composite Pattern

**Objectif**: Pipeline = composition d'algorithmes avec scoring pondere.

```python
Pipeline(steps=[
    {'algorithm': 'A', 'weight': 0.3},
    {'algorithm': 'B', 'weight': 0.7}
])

# Execution: global_score = 0.3×similarity_A + 0.7×similarity_B
```

### 4. Cache Pattern

**Objectif**: Eviter recalculs couteux.

**Multi-niveaux**:
```
Level 1: MD5 hash → Duplicatas exacts (O(1))
Level 2: FeatureCache → Features par video (O(1) lookup)
Level 3: ResultCache → Resultats par paire (O(1) lookup)
```

**Implementation** (SQLite):
```python
storage = StorageManager()

# Verifier cache
result = storage.get_cached_result(video1, video2, algo_name, config)

# Si absent, calculer
if result is None:
    result = algo.compare(video1, video2)
    storage.store_result(video1, video2, algo_name, config, result)
```

### 5. LSH (Locality-Sensitive Hashing)

**Objectif**: Reduction de complexite pour grandes collections.

**Sans LSH**:
- O(N²) comparisons
- Exemple: 1000 videos → 499,500 comparisons

**Avec LSH**:
- O(N×C) où C = nombre moyen de candidats
- MinHash + banding → grouper videos similaires
- Exemple: 1000 videos → 10,000-50,000 comparisons (10-50× plus rapide)

### 6. Validator Pattern

**Objectif**: Pre-filtrage et post-verification modulaires.

```python
pipeline = Pipeline(
    steps=[...],
    pre_validators=[
        LengthValidator(tolerance_percent=5.0, tolerance_seconds=30.0)
    ],
    post_validators=[
        # Custom validator
    ]
)

# Execution:
# 1. Pre-validation → Skip si echoue
# 2. Comparison
# 3. Post-validation → Rejeter si echoue
```

---

## Performance & Scalabilite

### Optimisations implementees

1. **Cache multi-niveaux**:
   - MD5: duplicatas exacts (O(1))
   - Features: stockage par video (O(1))
   - Results: stockage par paire (O(1))

2. **Parallelisation**:
   - ThreadPoolExecutor pour comparaisons pairwise
   - workers=N pour traitement parallele

3. **LSH**:
   - MinHash pour similarity estimation
   - Banding pour candidate selection
   - Reduction O(N²) → O(N×C)

4. **Early termination**:
   - Stop pipeline si global_score > threshold + margin
   - Economie: 30-50% des algorithmes

5. **Partial analysis**:
   - analyze_duration=60.0: ne comparer que 60s
   - Utile pour duplicatas (vs scenes completes)

### Benchmarks typiques

| Scenario | Methode | Temps | Comparaisons |
|----------|---------|-------|--------------|
| 100 videos (duplicates) | Fingerprint | 5 min | ~4,950 |
| 100 videos (duplicates) | Pipeline balanced | 15 min | 4,950 |
| 1000 videos (duplicates) | Fingerprint | 30 min | ~499,500 |
| 1000 videos (duplicates) | Fingerprint + LSH | 8 min | ~10,000-50,000 |
| 1000 videos (duplicates) | Pipeline balanced | 6h | 499,500 |
| 1-to-1 (thorough) | Pipeline | 30s | 1 |

---

## Points d'extension

### Ajouter un nouvel algorithme

1. Creer `duplicateflow/algorithms/mon_algo.py`
2. Heriter de `Algorithm`
3. Implementer `configure()` et `compare()`
4. Ajouter decorateur `@register_algorithm(...)`
5. (Optionnel) Implementer `extract_features()` et `compare_features()`

**Exemple**:
```python
from duplicateflow.core import register_algorithm
from duplicateflow.sdk import Algorithm

@register_algorithm(
    name="mon_algo",
    display_name="Mon Algo",
    category="custom",
    speed="fast",
    default_threshold=70.0
)
class MonAlgorithm(Algorithm):
    def configure(self, **params):
        self.threshold = params.get('threshold', 70.0)

    def compare(self, short_video, long_video, start_time, duration):
        # Implementation
        return {
            'similarity': 0.85,
            'accepted': True,
            'metadata': {}
        }
```

### Ajouter un preset

Editer `duplicateflow/pipeline/presets.py`:
```python
MON_PRESET = {
    'steps': [
        {'algorithm': 'frame_hash', 'weight': 0.5, 'threshold': 80},
        {'algorithm': 'mon_algo', 'weight': 0.5, 'threshold': 70}
    ],
    'global_threshold': 70.0
}

PRESETS['mon_preset'] = MON_PRESET
```

### Ajouter un validator

```python
from duplicateflow.sdk.validator import Validator

class MonValidator(Validator):
    def validate(self, video1, video2, result=None):
        # Logic
        is_valid = True
        metadata = {'reason': 'OK'}
        return is_valid, metadata
```

---

## Conclusion

DuplicateFlow offre une architecture:
- **Modulaire**: 14 algorithmes independants + registry
- **Extensible**: SDK pour ajouter algorithmes/validators
- **Performante**: Cache, LSH, parallelisation
- **Scalable**: Support de millions de videos (fingerprinting + LSH)
- **Flexible**: 12 presets + pipelines custom + storage

**Next**: Voir [DUPLICATEFLOW_ALGORITHMS.md](DUPLICATEFLOW_ALGORITHMS.md) pour details sur les 14 algorithmes.
