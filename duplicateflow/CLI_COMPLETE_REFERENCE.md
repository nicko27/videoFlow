# DuplicateFlow CLI - Référence Complète

## 📚 Table des Matières

1. [Audio Fingerprinting (N-to-N)](#audio-fingerprinting-n-to-n)
2. [Pipeline Comparison (1-to-1)](#pipeline-comparison-1-to-1)
3. [Batch Processing](#batch-processing)
4. [Pipeline Management](#pipeline-management)
5. [Information Commands](#information-commands)
6. [Cache Management](#cache-management)

---

## 🎵 N-to-N Duplicate Detection

### `find-duplicates` - Commande Tout-en-Un ⭐ (RECOMMANDÉE)

Trouve tous les duplicats/extraits dans un dossier. **Supporte 3 modes:**

1. **Audio Fingerprinting** (défaut, scalable millions) - N-to-N via index inversé
2. **Single Algorithm** - N-to-N pairwise avec un seul algorithme
3. **Pipeline** - N-to-N pairwise avec scoring pondéré multi-algorithmes

```bash
duplicateflow find-duplicates <directory> [OPTIONS]
```

**Options:**
```
-o, --output PATH                Output file (JSON/CSV)
--db PATH                        Database path (audio_fingerprint only, default: ~/.duplicateflow/fingerprints.db)
-a, --algorithm TEXT             Single algorithm (default: audio_fingerprint). Mutually exclusive with --pipeline
-p, --pipeline TEXT              Pipeline preset (fast/balanced/thorough/multimodal/structural/hybrid). Mutually exclusive with --algorithm
-r, --recursive / --no-recursive Scan subdirectories (default: enabled)
-w, --workers INTEGER            Parallel workers (default: 4)
-t, --threshold FLOAT            Detection threshold (algorithm-specific, overrides default)
--min-votes INTEGER              Minimum votes (audio_fingerprint only, default: 200)
--min-confidence FLOAT           Minimum confidence % (default: 15.0)
--max-pairs INTEGER              Maximum pairs (default: 10000)
--format [json|csv]              Output format (default: json)
--use-lsh / --no-lsh             Use LSH acceleration (audio_fingerprint only, default: auto)
--lsh-threshold INTEGER          LSH activation threshold (audio_fingerprint only, default: 100 videos)
--show-all                       Show all matches (not just top 10)
--cache / --no-cache             Use result caching (algorithm/pipeline modes, default: enabled)
```

**Exemples:**

**Mode 1: Audio Fingerprinting (défaut, le plus rapide)**
```bash
# Simple - Trouver tous les duplicats (audio fingerprinting)
duplicateflow find-duplicates ~/Videos

# Avec export JSON
duplicateflow find-duplicates ~/Videos -o results.json

# Haute confidence + parallélisation
duplicateflow find-duplicates ~/Videos --min-confidence 20 --workers 16

# Non-récursif (dossier courant uniquement)
duplicateflow find-duplicates ~/Videos --no-recursive

# Avec LSH pour grande collection
duplicateflow find-duplicates ~/Videos --use-lsh --workers 8
```

**Mode 2: Single Algorithm (pairwise N-to-N)**
```bash
# Utiliser frame_hash avec seuil personnalisé
duplicateflow find-duplicates ~/Videos --algorithm frame_hash --threshold 85

# Utiliser color_histogram
duplicateflow find-duplicates ~/Videos --algorithm color_histogram --threshold 75 --workers 8

# Avec cache désactivé
duplicateflow find-duplicates ~/Videos --algorithm motion_analysis --no-cache
```

**Mode 3: Pipeline (multi-algorithmes pondérés)**
```bash
# Pipeline balanced (défaut pour compare)
duplicateflow find-duplicates ~/Videos --pipeline balanced

# Pipeline thorough (plus précis, plus lent)
duplicateflow find-duplicates ~/Videos --pipeline thorough --workers 8

# Pipeline fast avec seuil global personnalisé
duplicateflow find-duplicates ~/Videos --pipeline fast --threshold 80

# Pipeline multimodal (audio + vidéo)
duplicateflow find-duplicates ~/Videos --pipeline multimodal -o results.json
```

**Output:**
```
  1. 🔁 ✓✓✓ DUPLICATE (confidence: 94.2%)
     Video 1: Rocco's Initiations 5.avi
     Video 2: Rocco's Initiations 5_debut.avi (starts at 0:00 in video 1)
     Votes: 408503

  2. 🎬 ✓✓  SCENE (confidence: 52.8%)
     Video 1: Das Monster.avi
     Video 2: Das Monster_7.mp4 (starts at 59:59 in video 1)
     Votes: 55384
```

---

### `index` - Indexer des Vidéos

Indexe des vidéos dans la base de données (étape optionnelle).

```bash
duplicateflow index <directory> [OPTIONS]
```

**Options:**
```
-a, --algorithm TEXT             Algorithm (default: audio_fingerprint)
--db PATH                        Database path
-r, --recursive / --no-recursive Scan subdirectories (default: enabled)
--pattern TEXT                   File pattern (default: *)
--force                          Re-index existing videos
-w, --workers INTEGER            Parallel workers (default: 4)
```

**Exemples:**
```bash
# Indexer avec 16 workers
duplicateflow index ~/Videos --workers 16

# Indexer uniquement MP4
duplicateflow index ~/Videos --pattern "*.mp4"

# Forcer réindexation
duplicateflow index ~/Videos --force
```

---

### `stats` - Statistiques de l'Index

Affiche les statistiques de la base de données.

```bash
duplicateflow stats [--db PATH]
```

**Exemple:**
```bash
duplicateflow stats
```

**Output:**
```
======================================================================
  FINGERPRINT INDEX STATISTICS
======================================================================

Database: /Users/nico/.duplicateflow/fingerprints.db
Database size: 348.71 MB

Videos indexed: 20
Total fingerprints: 7,546,191
Unique hashes: 3,642,384
Avg hashes per video: 332,973
```

---

### `clear` - Nettoyer l'Index

Supprime toutes les données de la base (demande confirmation).

```bash
duplicateflow clear [--db PATH]
```

**Exemple:**
```bash
duplicateflow clear
# Confirmation: Are you sure you want to clear the entire index? [y/N]:
```

---

## 🔍 Pipeline Comparison (1-to-1)

### `compare` - Comparer Deux Vidéos

Compare une courte vidéo avec une longue vidéo.

```bash
duplicateflow compare <short_video> <long_video> [OPTIONS]
```

**Options:**
```
-p, --preset TEXT                Pipeline preset (default: balanced)
-a, --algorithm TEXT             Single algorithm (overrides preset)
-t, --threshold FLOAT            Detection threshold
-o, --output [text|json]         Output format (default: text)
--cache / --no-cache             Use caching (default: enabled)
--progress / --no-progress       Show progress bar (default: enabled)
```

**Exemples:**
```bash
# Comparaison simple
duplicateflow compare scene.mp4 movie.mp4

# Utiliser preset thorough
duplicateflow compare scene.mp4 movie.mp4 --preset thorough

# Utiliser un seul algorithme
duplicateflow compare scene.mp4 movie.mp4 --algorithm frame_hash --threshold 85

# Export JSON
duplicateflow compare scene.mp4 movie.mp4 --output json > result.json
```

---

### `search` - Recherche Optimisée

Recherche optimisée pour trouver une scène dans une longue vidéo (plus rapide que `compare`).

```bash
duplicateflow search <short_video> <long_video> [OPTIONS]
```

**Options:**
```
-a, --algorithm TEXT             Algorithm (default: frame_hash)
-t, --threshold FLOAT            Detection threshold
--strategy [linear|parallel|cascade|adaptive]  Search strategy (default: cascade)
-w, --workers INTEGER            Parallel workers (auto if not specified)
--step FLOAT                     Step size in seconds (default: 5.0)
-o, --output [text|json]         Output format (default: text)
```

**Exemples:**
```bash
# Recherche avec cascade (le plus rapide)
duplicateflow search scene.mp4 movie.mp4

# Recherche parallèle avec 16 workers
duplicateflow search scene.mp4 movie.mp4 --strategy parallel --workers 16

# Recherche adaptative (ajuste le step automatiquement)
duplicateflow search scene.mp4 movie.mp4 --strategy adaptive

# Avec algorithme différent
duplicateflow search scene.mp4 movie.mp4 --algorithm color_histogram --step 2.0
```

---

## 📦 Batch Processing

### `batch` - Traiter Plusieurs Vidéos

Compare plusieurs vidéos contre une référence.

```bash
duplicateflow batch <input_dir> <reference_video> -o <output> [OPTIONS]
```

**Options:**
```
-a, --algorithm TEXT             Algorithm (default: frame_hash)
-t, --threshold FLOAT            Detection threshold
--strategy [parallel|standard]   Search strategy (default: parallel)
-w, --workers INTEGER            Parallel workers (default: 4)
--step FLOAT                     Step size in seconds (default: 5.0)
-o, --output PATH                Output file (.csv or .json) [REQUIRED]
--checkpoint PATH                Checkpoint file for resume
--pattern TEXT                   File pattern (default: *.mp4)
```

**Exemples:**
```bash
# Batch simple
duplicateflow batch ~/clips reference.mp4 -o results.csv

# Avec 16 workers et checkpoint
duplicateflow batch ~/clips reference.mp4 -o results.json --workers 16 --checkpoint chk.pkl
```

---

### `matrix` - Matrice N-to-N

Calcule la matrice de similarité complète (tous vs tous).

```bash
duplicateflow matrix <input_dir> -o <output> [OPTIONS]
```

**Options:**
```
-a, --algorithm TEXT             Algorithm (default: frame_hash)
-t, --threshold FLOAT            Detection threshold
-w, --workers INTEGER            Parallel workers (default: 4)
-o, --output PATH                Output CSV file [REQUIRED]
--pattern TEXT                   File pattern (default: *.mp4)
```

**Exemples:**
```bash
# Matrice complète
duplicateflow matrix ~/videos -o similarity_matrix.csv

# Avec algorithme spécifique
duplicateflow matrix ~/videos -o matrix.csv --algorithm color_histogram
```

---

## 🔧 Pipeline Management

### `pipeline list` - Lister les Pipelines

Liste tous les presets de pipelines disponibles.

```bash
duplicateflow pipeline list [OPTIONS]
```

**Options:**
```
-o, --output [text|json]         Output format (default: text)
```

**Exemples:**
```bash
# Liste textuelle
duplicateflow pipeline list

# Export JSON
duplicateflow pipeline list --output json > pipelines.json
```

**Output:**
```
======================================================================
  AVAILABLE PIPELINE PRESETS
======================================================================

Total presets: 6

📋 fast
   Algorithms: 3
   Threshold: 75.0
   Early termination: Yes
   Pipeline: frame_hash, color_histogram, color_moments

📋 balanced
   Algorithms: 4
   Threshold: 70.0
   Early termination: Yes
   Pipeline: frame_hash, color_histogram, motion_analysis, dct_coefficients

📋 thorough
   Algorithms: 5
   Threshold: 70.0
   Early termination: No
   Pipeline: frame_hash, color_histogram, motion_analysis, dct_coefficients, ssim
```

---

### `pipeline show` - Détails d'un Pipeline

Affiche les détails complets d'un pipeline.

```bash
duplicateflow pipeline show <preset_name> [OPTIONS]
```

**Options:**
```
-o, --output [text|json]         Output format (default: text)
```

**Exemples:**
```bash
# Afficher le pipeline balanced
duplicateflow pipeline show balanced

# Export JSON
duplicateflow pipeline show thorough --output json
```

**Output:**
```
======================================================================
  PIPELINE PRESET: balanced
======================================================================

Global threshold: 70.0
Early termination: Enabled

Algorithms (4 total):

  1. frame_hash
     Threshold: 80
     Weight: 0.2
     Params: {'hash_method': 'pHash', 'num_samples': 8}

  2. color_histogram
     Threshold: 70
     Weight: 0.25
     Params: {'num_samples': 5, 'bins': (32, 32, 32)}
```

---

## ℹ️ Information Commands

### `list-algorithms` - Lister les Algorithmes

Liste tous les algorithmes disponibles.

```bash
duplicateflow list-algorithms [OPTIONS]
```

**Options:**
```
-c, --category TEXT              Filter by category
-s, --speed TEXT                 Filter by speed (fast/medium/slow)
-o, --output [text|json]         Output format (default: text)
```

**Exemples:**
```bash
# Tous les algorithmes
duplicateflow list-algorithms

# Seulement audio
duplicateflow list-algorithms --category audio

# Seulement rapides
duplicateflow list-algorithms --speed fast

# Export JSON
duplicateflow list-algorithms --output json
```

**Output:**
```
Total algorithms: 14

🎵 Audio Fingerprint (Shazam-style)
  Name: audio_fingerprint
  Category: audio
  Speed: fast
  Threshold: 200
  Use case: N-to-N matching for millions of videos

🎵 Spectre Audio
  Name: audio_spectrum
  Category: audio
  Speed: medium
  Threshold: 70.0
  Use case: Scènes avec audio caractéristique (musique, dialogues, ambiance)
```

---

### `list-presets` - Lister les Presets

Liste tous les presets de pipelines (alias de `pipeline list`).

```bash
duplicateflow list-presets [--output [text|json]]
```

---

### `info` - Informations du Projet

Affiche les informations générales sur DuplicateFlow.

```bash
duplicateflow info
```

**Output:**
```
DuplicateFlow v1.0.0

Algorithms:
  Total: 14
  - audio: 2
  - statistical: 3
  - structural: 4
  - perceptual: 2
  - temporal: 2
  - hybrid: 1

Pipeline Presets:
  Total: 6
  Available: fast, balanced, thorough, multimodal, structural, hybrid

Features:
  - 100% free and open-source
  - MD5-based caching
  - SQLite result cache
  - Weighted scoring
  - Early termination
  - Parallel window search
  - Cascade filtering
```

---

## 💾 Cache Management

### `cache stats` - Statistiques du Cache

Affiche les statistiques du cache de résultats.

```bash
duplicateflow cache stats [--output [text|json]]
```

**Output:**
```
Cache Statistics:

Hash Cache:
  Hits: 1234
  Misses: 567
  Hit rate: 68.50%

Result Cache:
  Hits: 890
  Misses: 234
  Hit rate: 79.18%
  Total entries: 1124
  Memory cache size: 45

Cache directory: /Users/nico/.duplicateflow/cache
```

---

### `cache clear` - Nettoyer le Cache

Supprime les résultats en cache.

```bash
duplicateflow cache clear [OPTIONS]
```

**Options:**
```
-a, --algorithm TEXT             Clear for specific algorithm
-d, --days INTEGER               Clear older than N days
--all                            Clear all cached results
```

**Exemples:**
```bash
# Tout nettoyer (demande confirmation)
duplicateflow cache clear --all

# Nettoyer un algorithme spécifique
duplicateflow cache clear --algorithm frame_hash

# Nettoyer vieux résultats
duplicateflow cache clear --days 30
```

---

## 🔄 Match Types

DuplicateFlow classifie automatiquement les matches en 4 types:

| Type | Icône | Critère | Signification |
|------|-------|---------|---------------|
| **DUPLICATE** | 🔁 | Confidence ≥80% ET offset ≈0s | Copie exacte ou quasi-identique |
| **SCENE** | 🎬 | Confidence ≥60% | Même scène à position différente |
| **EXTRACT** | ✂️ | Confidence 15-60% | Extrait ou sous-séquence |
| **UNCERTAIN** | ❓ | Confidence <15% | Potentiel faux positif |

---

## 📊 Formats d'Export

### JSON
```json
[
  {
    "video1": "/path/to/video1.mp4",
    "video2": "/path/to/video2.mp4",
    "offset_seconds": 3599.28,
    "votes": 55384,
    "confidence": 52.79,
    "match_type": "SCENE"
  }
]
```

### CSV
```csv
video1,video2,offset_seconds,votes,confidence,match_type
/path/to/video1.mp4,/path/to/video2.mp4,3599.280,55384,52.80,SCENE
```

---

## 🎯 Cas d'Usage Typiques

### 1. Trouver des Duplicats dans une Collection

```bash
# Simple et rapide
duplicateflow find-duplicates ~/Videos

# Avec haute précision
duplicateflow find-duplicates ~/Videos --min-confidence 20 -o duplicates.json
```

### 2. Chercher une Scène dans un Film

```bash
# Méthode 1: Recherche optimisée (RAPIDE)
duplicateflow search scene.mp4 movie.mp4 --strategy cascade

# Méthode 2: Pipeline thorough (PRÉCIS)
duplicateflow compare scene.mp4 movie.mp4 --preset thorough
```

### 3. Traiter une Grande Collection (>100 vidéos)

```bash
# Avec LSH et parallélisation maximale
duplicateflow find-duplicates ~/BigCollection \
  --workers 16 \
  --use-lsh \
  --min-confidence 15 \
  -o results.json
```

### 4. Batch Processing de Clips

```bash
# Comparer tous les clips contre une référence
duplicateflow batch ~/clips reference_movie.mp4 \
  -o results.csv \
  --workers 8 \
  --checkpoint checkpoint.pkl
```

### 5. Matrice de Similarité

```bash
# Calculer similarité tous vs tous
duplicateflow matrix ~/test_videos \
  -o similarity_matrix.csv \
  --algorithm color_histogram
```

---

## 🚀 Optimisation Performance

### Indexation Rapide
```bash
# Maximiser les workers
duplicateflow index ~/Videos --workers 16
```

### Recherche Rapide
```bash
# Utiliser cascade filter (50-100x plus rapide)
duplicateflow search scene.mp4 long_movie.mp4 --strategy cascade --workers 8
```

### Matching Rapide (N-to-N)
```bash
# LSH activé automatiquement si >100 vidéos
duplicateflow find-duplicates ~/BigCollection --workers 16 --use-lsh
```

---

## 📖 Voir Aussi

- [CLI_IMPROVEMENTS.md](CLI_IMPROVEMENTS.md) - Détails des améliorations CLI
- [DUPLICATEFLOW_USAGE.md](DUPLICATEFLOW_USAGE.md) - Guide d'utilisation complet
- [architecture.json](architecture.json) - Architecture du projet

---

## 🆘 Aide et Support

```bash
# Aide générale
duplicateflow --help

# Aide pour une commande spécifique
duplicateflow find-duplicates --help
duplicateflow pipeline --help
duplicateflow search --help
```

**Verbosité:**
```bash
# Mode silencieux (erreurs seulement)
duplicateflow -q find-duplicates ~/Videos

# Mode verbeux
duplicateflow -v find-duplicates ~/Videos

# Mode très verbeux (debug)
duplicateflow -vv find-duplicates ~/Videos
```
