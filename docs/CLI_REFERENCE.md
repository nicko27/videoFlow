# DuplicateFlow CLI - Reference Complete

**Guide complet des commandes en ligne de commande de DuplicateFlow**

**Date**: 2025-12-19
**Version**: 1.0.0

---

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Installation](#installation)
3. [Commandes principales](#commandes-principales)
4. [Commandes d'indexation](#commandes-dindexation)
5. [Commandes de recherche](#commandes-de-recherche)
6. [Commandes de gestion](#commandes-de-gestion)
7. [Exemples de workflows](#exemples-de-workflows)
8. [Options globales](#options-globales)

---

## Vue d'ensemble

DuplicateFlow CLI permet de:
- **Comparer** des vidéos pour détecter des duplicates/sous-séquences
- **Indexer** des bibliothèques vidéo pour recherche rapide N-to-N
- **Rechercher** des sous-séquences dans de longues vidéos
- **Gérer** le cache et les index de fingerprints

### Architecture

```
Fingerprint Index (SQLite)
    ↓
Inverted Index: hash → [(video_id, timestamp), ...]
    ↓
O(N) matching au lieu de O(N²)
```

---

## Installation

```bash
# Installation
pip install duplicateflow

# Vérifier installation
duplicateflow --version

# Help
duplicateflow --help
```

---

## Commandes principales

### 1. `compare` - Comparer deux vidéos

**Usage**:
```bash
duplicateflow compare <short_video> <long_video> [OPTIONS]
```

**Description**:
Compare deux vidéos en utilisant un preset ou une configuration custom.

**Arguments**:
- `short_video` - Chemin vers la vidéo courte/sous-séquence
- `long_video` - Chemin vers la vidéo longue à analyser

**Options**:
- `--preset NAME` - Preset à utiliser (fast, balanced, thorough, etc.)
- `--threshold FLOAT` - Seuil de similarité global (0-100, défaut: 70.0)
- `--algorithm NAME` - Algorithme unique à utiliser
- `--output PATH` - Fichier JSON pour sauvegarder les résultats
- `--show-details` - Afficher détails de chaque algorithme
- `-v, --verbose` - Mode verbose (répétable: -v, -vv, -vvv)
- `-q, --quiet` - Mode silencieux

**Exemples**:

```bash
# Comparaison simple avec preset balanced
duplicateflow compare intro.mp4 film.mp4 --preset balanced

# Avec threshold custom
duplicateflow compare scene.mp4 episode.mp4 --preset thorough --threshold 80

# Algorithme unique
duplicateflow compare clip.mp4 video.mp4 --algorithm frame_hash

# Sauvegarder résultats
duplicateflow compare short.mp4 long.mp4 --preset fast --output results.json

# Mode verbose pour debugging
duplicateflow compare v1.mp4 v2.mp4 --preset balanced -vvv
```

**Output**:
```
Analyzing videos...
✓ Pre-validation passed

Running algorithms:
  [1/3] frame_hash: 85.2% (✓ accepted)
  [2/3] color_histogram: 78.5% (✓ accepted)
  [3/3] dct_coefficients: 82.1% (✓ accepted)

Results:
  Global score: 82.3%
  Status: CONFIRMED
  Execution time: 45.2s
```

---

### 2. `list-algorithms` - Lister les algorithmes

**Usage**:
```bash
duplicateflow list-algorithms [OPTIONS]
```

**Description**:
Affiche tous les algorithmes disponibles avec métadonnées.

**Options**:
- `--category NAME` - Filtrer par catégorie (perceptual, structural, temporal, statistical)
- `--format FORMAT` - Format d'output (table, json, csv)

**Exemples**:

```bash
# Tous les algorithmes
duplicateflow list-algorithms

# Seulement les rapides
duplicateflow list-algorithms --category perceptual

# Output JSON
duplicateflow list-algorithms --format json > algorithms.json
```

**Output**:
```
Available Algorithms (14 total):

PERCEPTUAL (4):
  • frame_hash           - Perceptual hashing (pHash/dHash)
  • color_histogram      - RGB histogram comparison
  • color_moments        - Color statistical moments
  • dct_coefficients     - DCT frequency analysis

STRUCTURAL (4):
  • feature_matching     - ORB/SIFT keypoint matching
  • edge_pattern         - Canny edge detection
  • hog_descriptor       - Histogram of gradients
  • template_matching    - Cross-correlation

TEMPORAL (3):
  • motion_analysis      - Optical flow magnitude
  • optical_flow         - Dense optical flow
  • subsequence_detection - Hybrid motion+hash

AUDIO (3):
  • audio_spectrum       - Frequency spectrum
  • audio_fingerprint    - Acoustic fingerprinting
  • ssim                 - Structural similarity
```

---

### 3. `list-presets` - Lister les presets

**Usage**:
```bash
duplicateflow list-presets [OPTIONS]
```

**Description**:
Affiche tous les presets avec configuration.

**Options**:
- `--format FORMAT` - Format (table, json)
- `--show-config` - Afficher configuration complète

**Exemples**:

```bash
# Liste simple
duplicateflow list-presets

# Avec configuration
duplicateflow list-presets --show-config

# JSON
duplicateflow list-presets --format json
```

**Output**:
```
Available Presets (12 total):

NAME              SPEED    ALGORITHMS  THRESHOLD  USE CASE
fast              ~30s     3           70.0       Quick scan
balanced          ~2min    4           70.0       General use ⭐
thorough          ~5min    5           75.0       High accuracy
multimodal        ~8min    6           70.0       Visual + audio
structural        ~3min    4           65.0       Geometric similarity
hybrid            ~4min    3           70.0       Subsequence detection
audio_advanced    ~6min    2           65.0       Audio focus
motion_intense    ~7min    4           60.0       Motion analysis
fast_duplicates   ~1min    3           85.0       Exact duplicates
accurate_scenes   ~3min    4           75.0       Scene matching
intro_detector    ~30s     3           75.0       Intro detection
credits_detector  ~30s     3           75.0       Credits detection
```

---

## Commandes d'indexation

### 4. `index` - Indexer une bibliothèque vidéo

**Usage**:
```bash
duplicateflow index <input_dir> [OPTIONS]
```

**Description**:
Construit un index de fingerprints pour recherche rapide N-to-N.
Permet de trouver des matches parmi des millions de vidéos sans comparaison par paires.

**Arguments**:
- `input_dir` - Répertoire contenant les vidéos

**Options**:
- `--algorithm NAME` - Algorithme à utiliser (défaut: audio_fingerprint)
- `--db PATH` - Chemin base de données (défaut: ~/.duplicateflow/fingerprints.db)
- `--recursive / --no-recursive` - Scanner sous-dossiers (défaut: activé)
- `--pattern GLOB` - Pattern de fichiers (défaut: *.mp4, *.mkv, *.avi)
- `--force` - Ré-indexer les vidéos existantes
- `--workers N` - Nombre de workers parallèles (défaut: 4)

**Exemples**:

```bash
# Indexer un dossier avec audio fingerprints
duplicateflow index /videos

# Avec plus de workers pour performance
duplicateflow index /media/library --workers 8

# Seulement fichiers MP4, non récursif
duplicateflow index /videos --pattern "*.mp4" --no-recursive

# Base de données custom
duplicateflow index /videos --db /data/fingerprints.db

# Ré-indexer en forçant
duplicateflow index /videos --force
```

**Output**:
```
Indexing videos in /videos...
Recursive: True, Workers: 4, Pattern: *

Processing videos: 100%|████████████| 1234/1234 [12:34<00:00, 1.6it/s]

Index statistics:
  Videos: 1,234
  Fingerprints: 1,245,789
  Unique hashes: 456,123
  Avg hashes/video: 1,009
  Database size: 145.23 MB
  Database: /home/user/.duplicateflow/fingerprints.db
```

**Architecture de l'index**:
```sql
-- Table videos
CREATE TABLE videos (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE,
    duration REAL,
    hash_count INTEGER,
    indexed_at TIMESTAMP
);

-- Table fingerprints (inverted index)
CREATE TABLE fingerprints (
    video_id INTEGER,
    hash TEXT,
    timestamp REAL,
    FOREIGN KEY(video_id) REFERENCES videos(id)
);

CREATE INDEX idx_fingerprints_hash ON fingerprints(hash, video_id);
```

---

### 5. `stats` - Statistiques de l'index

**Usage**:
```bash
duplicateflow stats [OPTIONS]
```

**Description**:
Affiche les statistiques de l'index de fingerprints.

**Options**:
- `--db PATH` - Chemin base de données

**Exemples**:

```bash
# Stats de l'index par défaut
duplicateflow stats

# Index custom
duplicateflow stats --db /data/fingerprints.db
```

**Output**:
```
======================================================================
  FINGERPRINT INDEX STATISTICS
======================================================================

Database: /home/user/.duplicateflow/fingerprints.db
Database size: 145.23 MB

Videos indexed: 1,234
Total fingerprints: 1,245,789
Unique hashes: 456,123
Avg hashes per video: 1,009
```

---

### 6. `clear` - Vider l'index

**Usage**:
```bash
duplicateflow clear [OPTIONS]
```

**Description**:
Supprime toutes les données de l'index de fingerprints.

**Options**:
- `--db PATH` - Chemin base de données

**Exemples**:

```bash
# Vider l'index (demande confirmation)
duplicateflow clear

# Index custom
duplicateflow clear --db /data/fingerprints.db
```

**Output**:
```
Are you sure you want to clear the entire index? [y/N]: y

✓ Index cleared successfully
  Database: /home/user/.duplicateflow/fingerprints.db
```

---

## Commandes de recherche

### 7. `find-duplicates` - Trouver des duplicates dans une bibliothèque

**Usage**:
```bash
duplicateflow find-duplicates <input_dir> [OPTIONS]
```

**Description**:
Trouve tous les duplicates dans un répertoire en utilisant l'index de fingerprints.

**Arguments**:
- `input_dir` - Répertoire à analyser

**Options**:
- `--db PATH` - Base de données d'index
- `--algorithm NAME` - Algorithme (défaut: audio_fingerprint)
- `--recursive / --no-recursive` - Scanner sous-dossiers
- `--workers N` - Nombre de workers
- `--min-votes N` - Votes minimum pour match (défaut: 5)
- `--min-confidence FLOAT` - Confidence minimum % (défaut: 15.0)
- `--max-pairs N` - Limiter nombre de paires (défaut: 1000)
- `--use-lsh` - Utiliser LSH pour optimisation
- `--lsh-threshold FLOAT` - Seuil LSH (défaut: 0.7)
- `--output PATH` - Sauvegarder résultats JSON

**Modes**:
1. **Fingerprint mode** (défaut) - Utilise l'index existant
2. **LSH mode** (`--use-lsh`) - Utilise LSH pour O(N) matching

**Exemples**:

```bash
# Find duplicates avec index
duplicateflow find-duplicates /videos

# Avec seuils custom
duplicateflow find-duplicates /videos --min-votes 10 --min-confidence 30

# Utiliser LSH
duplicateflow find-duplicates /videos --use-lsh --lsh-threshold 0.8

# Sauvegarder résultats
duplicateflow find-duplicates /videos --output duplicates.json

# Limiter à 100 paires
duplicateflow find-duplicates /videos --max-pairs 100
```

**Output**:
```
Finding duplicates in /videos...
Using fingerprint index: /home/user/.duplicateflow/fingerprints.db

Scanning videos: 100%|████████████| 234/234 [00:12<00:00, 19.2it/s]
Building vote matrix: 100%|█████████| 234/234 [00:03<00:00, 78.1it/s]

Found 42 duplicate pairs:

DUPLICATE (15 pairs):
  ✓ video1.mp4 ↔ video1_copy.mp4 (confidence: 95.2%, offset: 0:00)
  ✓ intro.mp4 ↔ episode_S01E01.mp4 (confidence: 88.5%, offset: 0:15)
  ...

SCENE (18 pairs):
  • scene_cut.mp4 ↔ full_movie.mp4 (confidence: 72.1%, offset: 45:23)
  ...

EXTRACT (9 pairs):
  • clip.mp4 ↔ original.mp4 (confidence: 45.3%, offset: 1:23:45)
  ...

Summary:
  Total pairs: 42
  Duplicates: 15 (exact copies)
  Scenes: 18 (same scene, different position)
  Extracts: 9 (partial matches)
  Uncertain: 0 (low confidence)

Results saved to: duplicates.json
```

**Format JSON output**:
```json
{
  "total_videos": 234,
  "total_pairs": 42,
  "matches": [
    {
      "video1": "/videos/video1.mp4",
      "video2": "/videos/video1_copy.mp4",
      "offset_seconds": 0.5,
      "votes": 152,
      "confidence": 95.2,
      "match_type": "DUPLICATE"
    }
  ]
}
```

---

### 8. `search` - Rechercher une sous-séquence

**Usage**:
```bash
duplicateflow search <short_video> <long_video> [OPTIONS]
```

**Description**:
Recherche optimisée d'une sous-séquence dans une longue vidéo.
Utilise des stratégies de recherche intelligentes pour performance.

**Arguments**:
- `short_video` - Vidéo courte à rechercher
- `long_video` - Vidéo longue où chercher

**Options**:
- `--preset NAME` - Preset à utiliser (défaut: balanced)
- `--strategy NAME` - Stratégie de recherche:
  - `parallel` - Recherche parallèle par fenêtres
  - `cascade` - Filtrage cascade 3 étapes (plus rapide)
  - `adaptive` - Pas adaptatif (balance vitesse/précision)
  - `linear` - Recherche linéaire exhaustive
- `--window-size SECONDS` - Taille fenêtre de recherche (défaut: auto)
- `--step-size SECONDS` - Pas de recherche (défaut: auto)
- `--workers N` - Nombre de workers parallèles
- `--output PATH` - Sauvegarder résultats JSON

**Exemples**:

```bash
# Recherche par défaut (cascade strategy)
duplicateflow search intro.mp4 film.mp4

# Stratégie parallèle avec 8 workers
duplicateflow search scene.mp4 movie.mp4 --strategy parallel --workers 8

# Cascade avec preset thorough
duplicateflow search clip.mp4 video.mp4 --strategy cascade --preset thorough

# Adaptive avec fenêtre custom
duplicateflow search short.mp4 long.mp4 --strategy adaptive --window-size 30

# Linear exhaustif (lent mais complet)
duplicateflow search sub.mp4 main.mp4 --strategy linear
```

**Output (cascade strategy)**:
```
Searching for intro.mp4 in film.mp4...
Strategy: cascade
Preset: balanced

Video analysis:
  Short video: 45.2s
  Long video: 1:34:23 (5,663s)
  Windows to search: 5,618

Cascade filtering:
  Stage 1 (quick hash): 5,618 → 234 windows (95.8% eliminated) [2.3s]
  Stage 2 (histogram): 234 → 12 windows (94.9% eliminated) [1.2s]
  Stage 3 (full analysis): 12 windows [45.6s]

Results:
  ✓ Match found at 0:15:34 (934s)
  Confidence: 87.3%
  Processing time: 49.1s (98% faster than linear)
```

**Stratégies de recherche**:

| Stratégie | Vitesse | Précision | Usage |
|-----------|---------|-----------|-------|
| `cascade` | ⚡⚡⚡ Très rapide | 95% | Défaut, élimine 95-99% rapidement |
| `parallel` | ⚡⚡ Rapide | 100% | Multi-core, exhaustif |
| `adaptive` | ⚡⚡ Rapide | 98% | Balance vitesse/précision |
| `linear` | ⚡ Lent | 100% | Exhaustif, pour référence |

---

## Commandes de gestion

### 9. `pipeline show` - Afficher une pipeline

**Usage**:
```bash
duplicateflow pipeline show <preset_name>
```

**Description**:
Affiche la configuration complète d'un preset.

**Arguments**:
- `preset_name` - Nom du preset

**Exemples**:

```bash
# Voir configuration balanced
duplicateflow pipeline show balanced

# Voir tous les presets
duplicateflow list-presets --show-config
```

**Output**:
```
Preset: balanced
Description: General-purpose preset balancing speed and accuracy

Configuration:
  Global threshold: 70.0
  Early termination: enabled (margin: 10.0)

Algorithms (4):
  1. frame_hash (weight: 0.3, threshold: 80.0)
     - hash_type: phash
     - sample_rate: 1.0

  2. color_histogram (weight: 0.3, threshold: 70.0)
     - bins: 8
     - normalize: True

  3. dct_coefficients (weight: 0.2, threshold: 75.0)
     - block_size: 8

  4. ssim (weight: 0.2, threshold: 70.0)
     - window_size: 11

Validators:
  None

Performance:
  Estimated time: ~2min for 1h video
  Accuracy: ~92%
```

---

### 10. `pipeline list` - Lister les pipelines

**Usage**:
```bash
duplicateflow pipeline list
```

**Description**:
Liste tous les presets disponibles (alias de `list-presets`).

---

### 11. `hash` - Calculer le hash d'un fichier

**Usage**:
```bash
duplicateflow hash <file_path> [OPTIONS]
```

**Description**:
Calcule le hash MD5 d'un fichier vidéo (pour cache/debug).

**Arguments**:
- `file_path` - Chemin du fichier

**Options**:
- `--fast` - Hash rapide (10MB début + 10MB fin)
- `--full` - Hash complet du fichier

**Exemples**:

```bash
# Hash rapide
duplicateflow hash video.mp4 --fast

# Hash complet
duplicateflow hash video.mp4 --full
```

**Output**:
```
File: video.mp4
Size: 1.23 GB

Fast hash: a3f5d8c2...
Full hash: b7e9f1a4...

Computation time:
  Fast: 0.45s
  Full: 12.34s
```

---

### 12. `cache stats` - Statistiques du cache

**Usage**:
```bash
duplicateflow cache stats
```

**Description**:
Affiche les statistiques du cache de résultats et features.

**Exemples**:

```bash
duplicateflow cache stats
```

**Output**:
```
======================================================================
  CACHE STATISTICS
======================================================================

Cache directory: /home/user/.duplicateflow/cache

Result Cache (SQLite):
  Cached comparisons: 1,234
  Database size: 45.6 MB
  Hit rate: 87.2%

Feature Cache (SQLite):
  Cached features: 5,678
  Types: histogram, hash, fingerprint, dct
  Database size: 123.4 MB
  Hit rate: 92.5%

Total cache size: 169.0 MB
```

---

### 13. `cache clear` - Vider le cache

**Usage**:
```bash
duplicateflow cache clear [OPTIONS]
```

**Description**:
Vide le cache de résultats et/ou features.

**Options**:
- `--results` - Vider seulement le cache de résultats
- `--features` - Vider seulement le cache de features
- `--all` - Vider tout (défaut)

**Exemples**:

```bash
# Vider tout le cache (demande confirmation)
duplicateflow cache clear

# Seulement résultats
duplicateflow cache clear --results

# Seulement features
duplicateflow cache clear --features
```

**Output**:
```
Are you sure you want to clear the cache? [y/N]: y

✓ Result cache cleared (45.6 MB freed)
✓ Feature cache cleared (123.4 MB freed)

Total freed: 169.0 MB
```

---

## Options globales

Disponibles pour toutes les commandes:

| Option | Description |
|--------|-------------|
| `--version` | Afficher version |
| `-v, --verbose` | Mode verbose (répétable: -v, -vv, -vvv) |
| `-q, --quiet` | Mode silencieux (erreurs seulement) |
| `--help` | Afficher aide |

**Niveaux de verbosité**:
- (aucun) - Erreurs seulement
- `-v` - Warnings
- `-vv` - Info
- `-vvv` - Debug complet

---

## Exemples de workflows

### Workflow 1: Comparer deux vidéos

```bash
# Simple
duplicateflow compare intro.mp4 film.mp4

# Avec détails
duplicateflow compare intro.mp4 film.mp4 --preset thorough -vv --show-details

# Sauvegarder résultats
duplicateflow compare intro.mp4 film.mp4 --output results.json
```

### Workflow 2: Indexer et trouver duplicates

```bash
# 1. Indexer bibliothèque
duplicateflow index /videos --workers 8

# 2. Voir stats
duplicateflow stats

# 3. Trouver duplicates
duplicateflow find-duplicates /videos --min-confidence 30 --output duplicates.json

# 4. Nettoyer (optionnel)
duplicateflow clear
```

### Workflow 3: Recherche optimisée

```bash
# Recherche rapide avec cascade
duplicateflow search intro.mp4 film.mp4 --strategy cascade

# Recherche exhaustive parallèle
duplicateflow search scene.mp4 movie.mp4 --strategy parallel --workers 8

# Avec preset thorough pour haute précision
duplicateflow search clip.mp4 video.mp4 --strategy cascade --preset thorough
```

### Workflow 4: Gestion du cache

```bash
# Voir stats cache
duplicateflow cache stats

# Comparer (utilise cache si disponible)
duplicateflow compare v1.mp4 v2.mp4

# Vider cache si trop gros
duplicateflow cache clear --features
```

### Workflow 5: Debugging

```bash
# Mode debug complet
duplicateflow compare v1.mp4 v2.mp4 -vvv --show-details

# Vérifier hash
duplicateflow hash v1.mp4 --full

# Voir config preset
duplicateflow pipeline show balanced

# Lister algorithmes disponibles
duplicateflow list-algorithms
```

---

## Performance Tips

### Pour vitesse maximale

```bash
# Utiliser fast preset
duplicateflow compare short.mp4 long.mp4 --preset fast

# Recherche cascade
duplicateflow search short.mp4 long.mp4 --strategy cascade

# Plus de workers
duplicateflow index /videos --workers 16
```

### Pour précision maximale

```bash
# Utiliser thorough preset
duplicateflow compare short.mp4 long.mp4 --preset thorough

# Threshold élevé
duplicateflow find-duplicates /videos --min-confidence 60

# Recherche linéaire exhaustive
duplicateflow search short.mp4 long.mp4 --strategy linear
```

### Pour grande échelle

```bash
# Indexer d'abord
duplicateflow index /huge/library --workers 32

# Puis utiliser index pour O(N) matching
duplicateflow find-duplicates /huge/library --use-lsh

# Limiter résultats
duplicateflow find-duplicates /huge/library --max-pairs 10000
```

---

## Codes de sortie

| Code | Signification |
|------|---------------|
| 0 | Succès |
| 1 | Erreur générale |
| 2 | Arguments invalides |
| 3 | Fichier non trouvé |
| 4 | Erreur de traitement vidéo |

---

## Variables d'environnement

```bash
# Cache directory
export DUPLICATEFLOW_CACHE_DIR=/custom/cache

# Log level
export DUPLICATEFLOW_LOG_LEVEL=DEBUG

# Database path
export DUPLICATEFLOW_DB_PATH=/custom/fingerprints.db
```

---

## Troubleshooting

### Commande lente

```bash
# Utiliser preset plus rapide
--preset fast

# Utiliser cascade strategy
--strategy cascade

# Plus de workers
--workers 16
```

### Résultats inexacts

```bash
# Utiliser preset plus précis
--preset thorough

# Augmenter threshold
--threshold 80

# Recherche exhaustive
--strategy linear
```

### Cache corrompu

```bash
# Vider cache
duplicateflow cache clear

# Réindexer
duplicateflow clear
duplicateflow index /videos
```

---

## Voir aussi

- [DUPLICATEFLOW_ARCHITECTURE.md](DUPLICATEFLOW_ARCHITECTURE.md) - Architecture complète
- [DUPLICATEFLOW_QUICK_REFERENCE.md](DUPLICATEFLOW_QUICK_REFERENCE.md) - Référence Python API
- [PROCESSING_GUIDE.md](PROCESSING_GUIDE.md) - Guide optimisation

---

**Dernière mise à jour**: 2025-12-19
**Auteur**: Claude Code (Sonnet 4.5)
**Statut**: ✅ Documentation complète des 13 commandes CLI
