# DuplicateFlow - Reference Rapide Complete

Documentation consolidee des aspects essentiels de DuplicateFlow.

## Table des Matieres

1. [12 Presets](#12-presets)
2. [API Reference](#api-reference)
3. [Integration VideoFlow](#integration-videoflow)
4. [LSH (Locality-Sensitive Hashing)](#lsh)
5. [Optimisations (Validators & Partial Analysis)](#optimisations)
6. [Exemples d'utilisation](#exemples)
7. [Migration depuis VideoHasher](#migration)
8. [Tests & Benchmarks](#tests)

---

## 12 Presets

### Vue d'ensemble

| Preset | Type | Vitesse | Threshold | Algorithmes | Cas d'usage |
|--------|------|---------|-----------|-------------|-------------|
| **fast** | Performance | 30s/1h | 75 | frame_hash, color_histogram, color_moments | Detection rapide basique |
| **balanced** | Equilibre | 2min/1h | 70 | frame_hash, color_histogram, motion_analysis, dct | Balance vitesse/precision |
| **thorough** | Precision | 5min/1h | 70 | frame_hash, color_histogram, motion_analysis, dct, ssim | Maximum de precision |
| **multimodal** | Video+Audio | 8min/1h | 70 | frame_hash, color_histogram, motion_analysis, feature_matching, ssim, audio_spectrum | Analyse complete |
| **structural** | Geometrie | 2min/1h | 70 | edge_pattern, feature_matching, hog_descriptor, template_matching | Focus structure |
| **hybrid** | Sous-sequences | 4min/1h | 70 | subsequence_detection, ssim | Detection d'extraits |
| **audio_advanced** | Audio | 3min/1h | 70 | audio_fingerprint, audio_spectrum, frame_hash | Fingerprinting audio |
| **motion_intense** | Mouvement | 6min/1h | 70 | optical_flow, motion_analysis, dct, ssim | Analyse mouvement dense |
| **fast_duplicates** | Duplicates + Validation | 30s/1h | 75 | frame_hash, color_histogram + LengthValidator + Partial(60s) | Duplicatas rapides |
| **accurate_scenes** | Scenes precises | 5min/1h | 70 | ssim, motion_analysis, audio_spectrum + LengthValidator strict | Detection scenes |
| **intro_detector** | Intros | 10s/1h | 85 | frame_hash, color_histogram + Partial(45s from start) | Detecter intros |
| **credits_detector** | Credits | 10s/1h | 85 | frame_hash, color_histogram + Partial(30s from end) | Detecter credits |

### Details des presets

#### 1. FAST_PRESET
```python
{
    'steps': [
        {'algorithm': 'frame_hash', 'weight': 0.3, 'threshold': 85, 'params': {'hash_method': 'pHash', 'num_samples': 8}},
        {'algorithm': 'color_histogram', 'weight': 0.35, 'threshold': 70, 'params': {'num_samples': 5, 'bins': (32,32,32)}},
        {'algorithm': 'color_moments', 'weight': 0.35, 'threshold': 75, 'params': {'num_samples': 5}}
    ],
    'global_threshold': 75.0,
    'early_termination': True,
    'early_termination_margin': 10.0
}
```

#### 2. BALANCED_PRESET  
```python
{
    'steps': [
        {'algorithm': 'frame_hash', 'weight': 0.2, 'threshold': 80},
        {'algorithm': 'color_histogram', 'weight': 0.25, 'threshold': 70},
        {'algorithm': 'motion_analysis', 'weight': 0.25, 'threshold': 70},
        {'algorithm': 'dct_coefficients', 'weight': 0.3, 'threshold': 70}
    ],
    'global_threshold': 70.0,
    'early_termination': True
}
```

#### 9. FAST_DUPLICATES_PRESET (avec validators)
```python
{
    'steps': [
        {'algorithm': 'frame_hash', 'weight': 0.6, 'threshold': 80},
        {'algorithm': 'color_histogram', 'weight': 0.4, 'threshold': 75}
    ],
    'global_threshold': 75.0,
    'early_termination': True,
    # Validators
    'pre_validators': [
        {
            'type': 'LengthValidator',
            'config': {
                'tolerance_percent': 5.0,
                'tolerance_seconds': 30.0,
                'require_both': False  # OR logic
            }
        }
    ],
    # Partial Analysis
    'analyze_duration': 60.0,    # Only first 60 seconds
    'analyze_from_start': True
}
```

#### 11. INTRO_DETECTOR_PRESET
```python
{
    'steps': [
        {'algorithm': 'frame_hash', 'weight': 0.6, 'threshold': 85},
        {'algorithm': 'color_histogram', 'weight': 0.4, 'threshold': 80}
    ],
    'global_threshold': 85.0,
    'early_termination': True,
    # Analyze only first 45 seconds
    'analyze_duration': 45.0,
    'analyze_from_start': True
}
```

### Utilisation

```python
from duplicateflow.pipeline import Pipeline

# Methode 1: Depuis preset
pipeline = Pipeline.from_preset('balanced')
result = pipeline.compare('short.mp4', 'long.mp4')

# Methode 2: Charger config
from duplicateflow.pipeline.presets import get_preset
config = get_preset('thorough')
pipeline = Pipeline(**config)
```

---

## API Reference

### DetectionEngine

**Point d'entree principal** pour toutes les operations.

```python
from duplicateflow.api import DetectionEngine, DetectionMode

engine = DetectionEngine(
    mode=DetectionMode.FINGERPRINT,  # FINGERPRINT | ALGORITHM | PIPELINE | ONE_TO_ONE
    algorithm=None,                   # Nom algo si mode=ALGORITHM
    pipeline=None,                    # Nom preset si mode=PIPELINE|ONE_TO_ONE
    db_path=None,                     # Path DB pour fingerprints
    use_cache=True,                   # Activer cache
    progress_callback=None            # Callback(message, progress 0-100)
)
```

#### Methodes principales

**1. find_duplicates()** - Detection N-to-N
```python
result = engine.find_duplicates(
    directory="/videos",
    recursive=True,
    workers=4,
    min_confidence=15.0,         # Seuil confidence (0-100)
    min_votes=200,               # Votes min (fingerprint mode)
    max_pairs=10000,
    threshold=None,              # Override threshold
    use_lsh=True,                # Activer LSH
    lsh_threshold=100,           # Active LSH si N >= 100
    lsh_num_perm=128,            # MinHash permutations
    lsh_num_bands=16             # LSH bands
)

# Result: DetectionResult
print(f"Matches: {len(result.matches)}")
print(f"Videos: {result.total_videos}")
print(f"Time: {result.processing_time}s")
for match in result.matches:
    print(f"{match.video1_path} <-> {match.video2_path}")
    print(f"  Similarity: {match.similarity:.1f}%")
    print(f"  Type: {match.match_type}")
```

**2. compare_videos()** - Comparaison 1-to-1
```python
match = engine.compare_videos(
    video1="/path/to/short.mp4",
    video2="/path/to/long.mp4",
    strategy="adaptive",          # linear | parallel | cascade | adaptive
    workers=4
)

# Result: MatchResult
print(f"Similarity: {match.similarity:.1f}%")
print(f"Type: {match.match_type}")  # DUPLICATE | SCENE | EXTRACT | UNCERTAIN
print(f"Confidence: {match.confidence:.1f}%")
```

### Pipeline

**Orchestration multi-algorithmes** avec weighted scoring.

```python
from duplicateflow.pipeline import Pipeline
from duplicateflow.sdk.validator import LengthValidator

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
    storage=None,                    # StorageManager pour cache
    global_threshold=70.0,
    early_termination=True,
    early_termination_margin=10.0,
    show_progress=False,
    # Validators
    pre_validators=[
        LengthValidator(tolerance_percent=5.0, tolerance_seconds=30.0)
    ],
    post_validators=[],
    validation_mode='all',           # all | any
    # Partial Analysis
    analyze_duration=None,           # Limit duration (seconds)
    analyze_from_start=True          # True = from start, False = from end
)

result = pipeline.compare('video1.mp4', 'video2.mp4', use_cache=True)
```

### Algorithm (utilisation directe)

```python
from duplicateflow.core import get_algorithm

# Get algorithm
AlgoClass = get_algorithm('frame_hash')
algo = AlgoClass()

# Configure
algo.configure(
    threshold=80.0,
    hash_method='pHash',
    num_samples=8
)

# Compare
result = algo.compare(
    short_video='/path/to/short.mp4',
    long_video='/path/to/long.mp4',
    start_time=0.0,
    duration=None
)

# Result: {'similarity': 0.85, 'accepted': True, 'metadata': {...}}
print(f"Similarity: {result['similarity']:.2f}")
print(f"Accepted: {result['accepted']}")
```

### PipelineStore

**Sauvegarde de pipelines custom**.

```python
from duplicateflow.storage import PipelineStore

store = PipelineStore()  # Default: ~/.duplicateflow/pipelines.db

# Save custom pipeline
store.save(
    name="my_custom",
    config={
        'steps': [...],
        'global_threshold': 70.0,
        'pre_validators': [...]
    },
    description="My custom pipeline",
    category="custom",
    overwrite=False
)

# Load pipeline
config = store.load("my_custom")
pipeline = Pipeline(**config)

# List pipelines
pipelines = store.list(category="custom", active_only=True)
for p in pipelines:
    print(f"{p['name']}: {p['description']}")

# Get stats
stats = store.get_stats("my_custom")
print(f"Used {stats['usage_count']} times")

# Export/Import
store.export_preset("my_custom", "my_preset.json")
store.import_preset("my_preset.json", name="imported")
```

---

## Integration VideoFlow

DuplicateFlow est integre dans VideoFlow via le plugin `duplicate_finder`.

### Architecture integration

```
VideoFlow (src/plugins/duplicate_finder/)
├── duplicateflow_api.py          # Wrapper DuplicateFlow
├── verification_pipeline.py       # Pipeline custom VideoFlow
├── orchestration/
│   └── pipeline_manager.py       # Gestionnaire de pipelines
├── database_manager.py            # Interface DB VideoFlow
└── ui/
    ├── main_window.py             # UI principale
    ├── unified_pipeline_editor_dialog.py  # Editeur pipeline
    └── widgets/
        ├── validator_config_widget.py     # Config validators
        └── partial_analysis_widget.py     # Config partial analysis
```

### Fichiers cles

**1. duplicateflow_api.py**
```python
class DuplicateFlowAPI:
    """Wrapper pour DuplicateFlow dans VideoFlow."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.storage = StorageManager()
    
    def compare_videos(self, video1, video2, pipeline_config):
        """Compare 2 videos avec pipeline config."""
        pipeline = Pipeline(**pipeline_config)
        result = pipeline.compare(video1, video2)
        return self._convert_result(result)
    
    def _convert_result(self, df_result):
        """Convert DuplicateFlow result to VideoFlow format."""
        return {
            'score': df_result['global_score'],
            'accepted': df_result['accepted'],
            'algorithms': df_result['individual_results']
        }
```

**2. verification_pipeline.py**
```python
class VerificationPipeline:
    """Pipeline de verification VideoFlow."""
    
    def __init__(self, config):
        self.df_api = DuplicateFlowAPI(config['db_path'])
        self.pipeline_config = config['pipeline']
    
    def verify_pair(self, video1_path, video2_path):
        """Verifier une paire de videos."""
        result = self.df_api.compare_videos(
            video1_path,
            video2_path,
            self.pipeline_config
        )
        return result
```

### Conversion des formats

**DuplicateFlow → VideoFlow**:
```python
def df_to_vf_result(df_result):
    return {
        'video1': df_result['video1_path'],
        'video2': df_result['video2_path'],
        'score': df_result['global_score'],
        'accepted': df_result['accepted'],
        'algorithms': [
            {
                'name': algo['algorithm'],
                'score': algo['similarity'],
                'weight': algo['weight']
            }
            for algo in df_result['individual_results']
        ]
    }
```

**VideoFlow → DuplicateFlow**:
```python
def vf_to_df_config(vf_config):
    return {
        'steps': [
            {
                'algorithm': step['name'],
                'weight': step['weight'],
                'threshold': step['threshold'],
                'params': step.get('params', {})
            }
            for step in vf_config['algorithms']
        ],
        'global_threshold': vf_config['global_threshold']
    }
```

---

## LSH (Locality-Sensitive Hashing)

### Principe

**Probleme**: Comparer N videos = O(N²) comparisons
- 100 videos → 4,950 comparisons
- 1000 videos → 499,500 comparisons
- 10000 videos → 49,995,000 comparisons

**Solution LSH**: Reduction O(N²) → O(N×C) où C = candidats moyens
- 1000 videos → ~10,000-50,000 comparisons (10-50× plus rapide)

### Algorithme MinHash LSH

```
1. MinHash Signature
   Pour chaque video:
   - Extraire ensemble de hashes (fingerprints)
   - Appliquer 128 permutations hash
   - Garder min value par permutation
   → Signature = array de 128 valeurs

2. LSH Banding
   - Diviser signature en 16 bands de 8 rows
   - Hasher chaque band
   - Videos dans meme bucket = candidates

3. Query
   - Pour video query:
     - Trouver buckets dans 16 bands
     - Collecter tous candidats
     - Comparer uniquement avec candidats
```

### Parametres LSH

```python
lsh = MinHashLSH(
    num_perm=128,      # Nombre de permutations (plus = plus precis, plus lent)
    num_bands=16,      # Nombre de bands (plus = plus sensible, plus faux positifs)
    threshold=0.3      # Seuil Jaccard similarity
)
```

**Trade-off num_perm vs num_bands**:

| num_perm | num_bands | rows/band | Detection @0.5 | False positives |
|----------|-----------|-----------|----------------|-----------------|
| 64 | 8 | 8 | ~95% | ~2% |
| 128 | 16 | 8 | ~99% | ~1% |
| 256 | 32 | 8 | ~99.9% | ~0.5% |

### Utilisation

```python
from duplicateflow.processing.lsh_index import LSHFingerprintIndex
from duplicateflow.processing.fingerprint_index import FingerprintIndex
from duplicateflow.algorithms import get_algorithm

# 1. Create fingerprint index
index = FingerprintIndex(db_path="/path/to/fingerprints.db")

# 2. Index directory
algo = get_algorithm('audio_fingerprint')()
algo.configure()
index.index_directory("/videos", algorithm=algo, workers=8)

# 3. Build LSH index
lsh_index = LSHFingerprintIndex(
    fingerprint_index=index,
    num_perm=128,
    num_bands=16
)

# 4. Find matches (fast)
matches = lsh_index.find_matches_fast(
    video_path="/videos/video1.mp4",
    min_votes=200,
    max_matches=100
)

print(f"Found {len(matches)} matches")
```

### Benchmarks

| Dataset | Mode | Temps | Comparisons |
|---------|------|-------|-------------|
| 100 videos | Brute force | 5 min | 4,950 |
| 100 videos | LSH | 5 min | 4,950 (pas d'acceleration) |
| 1000 videos | Brute force | 30 min | 499,500 |
| 1000 videos | LSH | 8 min | ~20,000 (3.75× acceleration) |
| 10000 videos | Brute force | 50h | 49,995,000 |
| 10000 videos | LSH | 2h | ~200,000 (25× acceleration) |

**Conclusion**: LSH rentable a partir de ~100 videos.

---

## Optimisations

### 1. Validators

**Pre-validators**: Filtrer AVANT comparison
**Post-validators**: Verifier APRES comparison

#### LengthValidator

```python
from duplicateflow.sdk.validator import LengthValidator

validator = LengthValidator(
    tolerance_percent=5.0,      # Tolerance en % (ex: 5%)
    tolerance_seconds=30.0,     # Tolerance en secondes (ex: 30s)
    require_both=False          # False = OR, True = AND
)

# Usage dans pipeline
pipeline = Pipeline(
    steps=[...],
    pre_validators=[validator],
    validation_mode='all'       # all | any
)
```

**Exemple**: Videos de 60s et 65s
- Diff = 5s = 8.3%
- tolerance_percent=5.0 → FAIL (8.3 > 5)
- tolerance_seconds=30.0 → PASS (5 < 30)
- require_both=False (OR) → PASS
- require_both=True (AND) → FAIL

#### Custom Validator

```python
from duplicateflow.sdk.validator import Validator

class ResolutionValidator(Validator):
    def __init__(self, max_diff_percent=20.0):
        super().__init__()
        self.max_diff_percent = max_diff_percent
    
    def validate(self, video1, video2, result=None):
        import cv2
        
        cap1 = cv2.VideoCapture(video1)
        w1, h1 = cap1.get(3), cap1.get(4)
        cap1.release()
        
        cap2 = cv2.VideoCapture(video2)
        w2, h2 = cap2.get(3), cap2.get(4)
        cap2.release()
        
        area1 = w1 * h1
        area2 = w2 * h2
        diff_percent = abs(area1 - area2) / max(area1, area2) * 100
        
        is_valid = diff_percent <= self.max_diff_percent
        
        metadata = {
            'resolution1': f"{int(w1)}x{int(h1)}",
            'resolution2': f"{int(w2)}x{int(h2)}",
            'diff_percent': diff_percent,
            'reason': 'OK' if is_valid else f'Diff {diff_percent:.1f}% > {self.max_diff_percent}%'
        }
        
        return is_valid, metadata
```

### 2. Partial Analysis

**Principe**: Analyser seulement N premieres (ou dernieres) secondes.

**Use case**:
- **Duplicates**: Comparer 60 premieres secondes suffit (plus rapide)
- **Scenes**: Comparer video entiere (plus precis)
- **Intros**: Comparer 45 premieres secondes
- **Credits**: Comparer 30 dernieres secondes

```python
pipeline = Pipeline(
    steps=[...],
    analyze_duration=60.0,      # Analyser 60 secondes max
    analyze_from_start=True     # True = debut, False = fin
)
```

**Exemple**: Video de 120s avec analyze_duration=60s
- analyze_from_start=True → Analyser [0s, 60s]
- analyze_from_start=False → Analyser [60s, 120s]

**Impact performance**:
- Full analysis (120s) → 30s traitement
- Partial (60s) → 15s traitement (2× plus rapide)
- Partial (30s) → 7.5s traitement (4× plus rapide)

### 3. Cache multi-niveaux

**Level 1: MD5 check** (duplicatas exacts)
```python
storage = StorageManager()
if storage.are_files_identical(video1, video2, method='fast'):
    return {'global_score': 100.0, 'accepted': True}
```

**Level 2: Feature cache** (par video)
```python
# Verifier cache
features = storage.get_cached_features(video_path, algo_name, config)

# Si absent, extraire
if features is None:
    features = algo.extract_features(video_path)
    storage.store_features(video_path, algo_name, config, features)
```

**Level 3: Result cache** (par paire)
```python
# Verifier cache
result = storage.get_cached_result(video1, video2, algo_name, config)

# Si absent, comparer
if result is None:
    result = algo.compare(video1, video2)
    storage.store_result(video1, video2, algo_name, config, result)
```

---

## Exemples

### 1. Detection basique de duplicatas

```python
from duplicateflow.api import DetectionEngine, DetectionMode

engine = DetectionEngine(mode=DetectionMode.FINGERPRINT)
result = engine.find_duplicates(
    directory="/videos",
    workers=8,
    min_confidence=15.0,
    use_lsh=True
)

print(f"Found {len(result.matches)} duplicates")
for match in result.matches:
    print(f"{match.video1_path} <-> {match.video2_path} ({match.similarity:.1f}%)")
```

### 2. Detection de scenes (intro/credits)

```python
engine = DetectionEngine(mode=DetectionMode.PIPELINE, pipeline='intro_detector')
result = engine.find_duplicates(
    directory="/series/season1",
    workers=4,
    min_confidence=85.0
)
```

### 3. Configuration avec validators

```python
from duplicateflow.pipeline import Pipeline
from duplicateflow.sdk.validator import LengthValidator

pipeline = Pipeline(
    steps=[
        {'algorithm': 'frame_hash', 'weight': 0.6, 'threshold': 80},
        {'algorithm': 'color_histogram', 'weight': 0.4, 'threshold': 75}
    ],
    global_threshold=75.0,
    pre_validators=[
        LengthValidator(tolerance_percent=5.0, tolerance_seconds=30.0)
    ],
    analyze_duration=60.0,
    analyze_from_start=True
)

result = pipeline.compare('video1.mp4', 'video2.mp4')
```

### 4. Pipeline custom

```python
my_pipeline = Pipeline(
    steps=[
        {'algorithm': 'audio_fingerprint', 'weight': 0.5, 'threshold': 200},
        {'algorithm': 'frame_hash', 'weight': 0.3, 'threshold': 80},
        {'algorithm': 'ssim', 'weight': 0.2, 'threshold': 0.70}
    ],
    global_threshold=70.0
)

result = my_pipeline.compare('short.mp4', 'long.mp4')
```

### 5. Utilisation de LSH

```python
from duplicateflow.processing import FingerprintIndex, LSHFingerprintIndex
from duplicateflow.algorithms import get_algorithm

# Index directory
index = FingerprintIndex()
algo = get_algorithm('audio_fingerprint')()
algo.configure()
index.index_directory("/videos", algorithm=algo, workers=8)

# Build LSH
lsh_index = LSHFingerprintIndex(index, num_perm=128, num_bands=16)

# Find matches (fast)
for video_path in video_paths:
    matches = lsh_index.find_matches_fast(video_path, min_votes=200)
    print(f"{video_path}: {len(matches)} matches")
```

---

## Migration

### VideoHasher → DuplicateFlow

#### Table de correspondance

| VideoHasher | DuplicateFlow |
|-------------|---------------|
| `VideoHasher.compute_hash()` | `algo.extract_features()` |
| `VideoHasher.compare_hashes()` | `algo.compare_features()` |
| `video_hasher.has_hash(path)` | `db.has_video(path)` |
| `video_hasher.get_hash(path)` | `db.get_features(path)` |
| `video_hasher.store_hash(path, hash)` | `db.store_features(path, features)` |

#### Ancien code (VideoHasher)

```python
from video_hasher import VideoHasher

hasher = VideoHasher(method='pHash')

# Compute hash
hash1 = hasher.compute_hash('video1.mp4')
hash2 = hasher.compute_hash('video2.mp4')

# Compare
similarity = hasher.compare_hashes(hash1, hash2)
```

#### Nouveau code (DuplicateFlow)

```python
from duplicateflow.core import get_algorithm

algo = get_algorithm('frame_hash')
algo.configure(hash_method='pHash')

# Extract features
features1 = algo.extract_features('video1.mp4')
features2 = algo.extract_features('video2.mp4')

# Compare
result = algo.compare_features(
    features1,
    features2,
    threshold=80.0
)
similarity = result['similarity']
```

### Checklist de migration

- [ ] Remplacer imports `video_hasher` par `duplicateflow`
- [ ] Remplacer `VideoHasher` par `get_algorithm('frame_hash')`
- [ ] Remplacer `compute_hash()` par `extract_features()`
- [ ] Remplacer `compare_hashes()` par `compare_features()`
- [ ] Adapter storage: `has_hash()` → `has_video()`, etc.
- [ ] Utiliser Pipeline pour multi-algorithmes
- [ ] Ajouter validators si necessaire
- [ ] Activer cache avec StorageManager
- [ ] Considerer LSH pour grandes collections

---

## Tests & Benchmarks

### Structure des tests

```
duplicateflow/tests/
├── test_algorithms.py          # Tests unitaires algorithmes
├── test_pipeline.py            # Tests pipeline
├── test_validators.py          # Tests validators
└── benchmarks/
    ├── test_performance.py     # Benchmarks performance
    └── test_datasets/
        ├── duplicates/         # Paires duplicates
        ├── scenes/             # Paires scenes
        └── negatives/          # Paires non-similaires
```

### Format test pairs

```python
test_pairs = [
    {
        'video1': '/path/to/original.mp4',
        'video2': '/path/to/duplicate.mp4',
        'expected': 'DUPLICATE',
        'min_similarity': 80.0
    },
    {
        'video1': '/path/to/scene1.mp4',
        'video2': '/path/to/scene2.mp4',
        'expected': 'SCENE',
        'min_similarity': 60.0
    }
]
```

### Metriques de performance

**Precision/Recall**:
```python
from sklearn.metrics import precision_recall_fscore_support

# Ground truth
y_true = [1, 1, 0, 1, 0]  # 1 = duplicate, 0 = not duplicate

# Predictions
y_pred = [1, 1, 0, 0, 0]

precision, recall, f1, _ = precision_recall_fscore_support(
    y_true, y_pred, average='binary'
)

print(f"Precision: {precision:.2f}")
print(f"Recall: {recall:.2f}")
print(f"F1-score: {f1:.2f}")
```

**Temps d'execution**:
```python
import time

start = time.time()
result = algo.compare(video1, video2)
elapsed = time.time() - start

print(f"Time: {elapsed:.2f}s")
```

### Benchmarks typiques

| Algorithme | Video (1min) | Video (10min) | Video (60min) |
|------------|--------------|---------------|---------------|
| frame_hash | 0.5s | 2s | 5s |
| color_histogram | 0.8s | 3s | 8s |
| ssim | 2s | 10s | 45s |
| motion_analysis | 1.5s | 8s | 35s |
| optical_flow | 5s | 30s | 150s |
| audio_fingerprint | 1s | 5s | 20s |

---

## Conclusion

Cette documentation couvre les aspects essentiels de DuplicateFlow:

1. **12 Presets** pour demarrer rapidement
2. **API complete** pour toutes les operations
3. **Integration VideoFlow** pour les utilisateurs VideoFlow
4. **LSH** pour scalabilite
5. **Optimisations** (validators, partial analysis, cache)
6. **Exemples** concrets d'utilisation
7. **Migration** depuis VideoHasher
8. **Tests** et benchmarks

Pour plus de details, consulter:
- [DUPLICATEFLOW_ARCHITECTURE.md](DUPLICATEFLOW_ARCHITECTURE.md)
- [DUPLICATEFLOW_ALGORITHMS.md](DUPLICATEFLOW_ALGORITHMS.md)
