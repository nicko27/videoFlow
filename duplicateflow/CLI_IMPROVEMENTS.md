# CLI Improvements Summary

## 🎯 LATEST UPDATE: Multi-Algorithm Support (December 2025)

### `find-duplicates` now supports 3 modes:

**BEFORE:** Only audio fingerprinting
```bash
duplicateflow find-duplicates ~/Videos  # Audio fingerprinting only
```

**AFTER:** Audio fingerprinting + ANY algorithm + ANY pipeline
```bash
# Mode 1: Audio Fingerprinting (default, scalable to millions)
duplicateflow find-duplicates ~/Videos

# Mode 2: Single Algorithm (pairwise N-to-N)
duplicateflow find-duplicates ~/Videos --algorithm frame_hash
duplicateflow find-duplicates ~/Videos --algorithm color_histogram --threshold 75

# Mode 3: Pipeline (multi-algorithm weighted scoring)
duplicateflow find-duplicates ~/Videos --pipeline balanced
duplicateflow find-duplicates ~/Videos --pipeline thorough
```

**Benefits:**
- ✅ **Unified interface**: One command for all N-to-N detection scenarios
- ✅ **Flexible**: Choose between speed (fingerprinting) and accuracy (pipelines)
- ✅ **Consistent**: Same output format, filtering, and export across all modes
- ✅ **Cached**: Results are cached for algorithm/pipeline modes
- ✅ **Parallel**: All modes support `--workers` for parallel processing

**Technical Details:**
- Audio fingerprinting uses inverted index (O(N×H) where H = hash count)
- Algorithm/pipeline modes use pairwise comparison (O(N²) but cached)
- Database persistence: Fingerprint index in SQLite, algorithm results in cache
- Match classification: Automatic DUPLICATE/SCENE/EXTRACT/UNCERTAIN for all modes

---

## ✅ Previous Improvements (Implemented)

### 1. **Suppression des Commandes Redondantes**

**AVANT:**
```bash
duplicateflow find-matches <video>     # Redondant
duplicateflow find-all-matches         # Redondant
duplicateflow find-duplicates <dir>    # Principal
duplicateflow index-stats              # Mal nommé
```

**APRÈS:**
```bash
duplicateflow find-duplicates <dir>    # Commande all-in-one (RECOMMANDÉE)
duplicateflow stats                    # Renommé (plus court)
duplicateflow clear                    # Nouvelle commande
```

### 2. **Indexation Récursive**

Ajout du paramètre `--recursive / --no-recursive` (défaut: activé):

```bash
# Scan récursif (défaut)
duplicateflow index ~/Videos

# Scan non-récursif (dossier courant uniquement)
duplicateflow index ~/Videos --no-recursive

# find-duplicates supporte aussi
duplicateflow find-duplicates ~/Videos --recursive
```

### 3. **Parallélisation Configurable**

Ajout du paramètre `--workers` partout:

```bash
# Utiliser 8 workers pour l'indexation
duplicateflow index ~/Videos --workers 8

# Utiliser 16 workers pour find-duplicates
duplicateflow find-duplicates ~/Videos --workers 16 --min-confidence 15.0
```

### 4. **Normalisation des Offsets**

- ✅ **Offsets toujours positifs** (échange video1/video2 si nécessaire)
- ✅ **Format h:m:s** au lieu de secondes brutes
- ✅ **Explication claire** ("video2 starts at 1:23:45 in video1")

**AVANT:**
```
Offset: -2482.5s
```

**APRÈS:**
```
Video 2: Rocco's Initiations 5_milieu.avi (starts at 41:22 in video 1)
```

### 5. **Classification des Matches**

Ajout de 4 types de matches avec icônes visuelles:

| Type | Icon | Critère | Exemple |
|------|------|---------|---------|
| **DUPLICATE** | 🔁 | Confidence ≥80% ET offset ≈0 | Copie exacte |
| **SCENE** | 🎬 | Confidence ≥60% | Même scène à position différente |
| **EXTRACT** | ✂️ | Confidence 15-60% | Extrait/sous-séquence |
| **UNCERTAIN** | ❓ | Confidence <15% | Faux positif probable |

### 6. **Export JSON/CSV Amélioré**

Les exports incluent maintenant:
- `match_type` (DUPLICATE/SCENE/EXTRACT/UNCERTAIN)
- `offset_seconds` (toujours positif)
- Meilleure organisation des données

### 7. **Commande `clear`**

Nouvelle commande pour nettoyer la base:

```bash
# Vider l'index complet (avec confirmation)
duplicateflow clear

# Utiliser une DB personnalisée
duplicateflow clear --db /path/to/custom.db
```

---

## 📋 Structure CLI Finale

### **Commandes Audio Fingerprinting (N-to-N)**

```bash
# 🎯 Commande principale (RECOMMANDÉE)
duplicateflow find-duplicates <directory> [OPTIONS]
  -r, --recursive / --no-recursive  # Scan récursif (défaut: activé)
  -w, --workers INTEGER            # Workers parallèles (défaut: 4)
  --min-votes INTEGER              # Votes minimum (défaut: 200)
  --min-confidence FLOAT           # Confidence min % (défaut: 15.0)
  --use-lsh / --no-lsh             # Activer LSH (auto si >100 vidéos)
  -o, --output PATH                # Export JSON/CSV
  --show-all                       # Afficher tous les résultats
  --db PATH                        # DB personnalisée

# Indexation avancée
duplicateflow index <directory> [OPTIONS]
  -r, --recursive / --no-recursive  # Scan récursif
  -w, --workers INTEGER            # Workers parallèles
  --force                          # Réindexer même si déjà fait
  --pattern TEXT                   # Pattern de fichiers
  --db PATH                        # DB personnalisée

# Utilitaires
duplicateflow stats [--db PATH]   # Statistiques de l'index
duplicateflow clear [--db PATH]   # Vider l'index
```

### **Commandes Pipeline (1-to-1)**

```bash
# Comparaison simple
duplicateflow compare <short> <long> [OPTIONS]

# Recherche optimisée
duplicateflow search <short> <long> [OPTIONS]
  --strategy [linear|parallel|cascade|adaptive]
  -w, --workers INTEGER

# Batch processing
duplicateflow batch <dir> <ref> -o <output> [OPTIONS]
  -w, --workers INTEGER

duplicateflow matrix <dir> -o <output> [OPTIONS]
  -w, --workers INTEGER
```

### **Commandes Info**

```bash
duplicateflow list-algorithms
duplicateflow list-presets
duplicateflow info
duplicateflow cache stats
duplicateflow cache clear
```

---

## 🚀 Exemples d'Utilisation

### Cas d'usage simple (recommandé)

```bash
# Trouver tous les duplicats dans un dossier
duplicateflow find-duplicates ~/Videos

# Avec plus de workers et récursif
duplicateflow find-duplicates ~/Videos --workers 8

# Augmenter la confidence pour réduire faux positifs
duplicateflow find-duplicates ~/Videos --min-confidence 20.0

# Exporter les résultats
duplicateflow find-duplicates ~/Videos -o results.json
```

### Cas d'usage avancé

```bash
# Indexer d'abord (optionnel)
duplicateflow index ~/Videos --workers 16 --recursive

# Puis chercher les duplicats
duplicateflow find-duplicates ~/Videos --min-confidence 15.0 -o matches.csv --format csv

# Voir les stats
duplicateflow stats

# Nettoyer
duplicateflow clear
```

### Scan non-récursif (dossier courant uniquement)

```bash
duplicateflow find-duplicates ~/Downloads/tests --no-recursive
```

---

## 📊 Output Example

```
======================================================================
  DUPLICATEFLOW - Audio Fingerprint Duplicate Detection
======================================================================

Processing: /Users/nico/Downloads/tests
Database:   /Users/nico/.duplicateflow/fingerprints.db

======================================================================
STEP 1/3: Indexing new videos
======================================================================

✓ All videos already indexed (20 total)

======================================================================
STEP 2/3: Finding matching pairs
======================================================================

✓ Found 12 matching pairs (after filtering)!

======================================================================
STEP 3/3: Results
======================================================================

  1. 🔁 ✓✓✓ DUPLICATE (confidence: 94.2%)
     Video 1: Rocco's Initiations 5.avi
     Video 2: Rocco's Initiations 5_debut.avi (starts at 0:00 in video 1)
     Votes: 408503

  2. 🎬 ✓✓  SCENE (confidence: 52.8%)
     Video 1: Das Monster und die Schone.avi
     Video 2: Das Monster und die Schone_7.mp4 (starts at 59:59 in video 1)
     Votes: 55384

  3. ✂️  ✓   EXTRACT (confidence: 31.8%)
     Video 1: Rocco's Initiations 5.avi
     Video 2: Rocco's Initiations 5_milieu.avi (starts at 41:22 in video 1)
     Votes: 162757

======================================================================
SUMMARY
======================================================================
Total videos processed: 20
Matching pairs found:   12

By Match Type:
  🔁 DUPLICATE (exact copies):     2
  🎬 SCENE (same scene/extract):   3
  ✂️  EXTRACT (partial match):      7
  ❓ UNCERTAIN (low confidence):   0

By Confidence:
  High confidence (≥80%):   2
  Medium confidence (≥60%): 3
  Low confidence (<60%):    7

✓ Done!
```

---

## 🔧 Améliorations Techniques

1. **Parallélisation intelligente**
   - ThreadPoolExecutor pour l'indexation
   - Configurable via `--workers`
   - Défaut: 4 workers (optimal pour la plupart des cas)

2. **Scan récursif optimisé**
   - Support de `**/*.ext` pour glob récursif
   - Support de `*.ext` pour scan non-récursif
   - Extensions supportées: mp4, mkv, avi, mov, webm, flv, wmv, m4v

3. **Classification automatique**
   - Basée sur confidence + offset
   - Logique claire et documentée
   - Exportée dans JSON/CSV

4. **Format offset lisible**
   - Conversion automatique en h:m:s
   - Format adaptatif (affiche heures seulement si >1h)
   - Toujours positif (inversion automatique)

---

## ✅ Tests Réalisés

- [x] Suppression commandes redondantes
- [x] Ajout --workers
- [x] Ajout --recursive
- [x] Normalisation offsets (toujours positifs)
- [x] Format h:m:s pour offsets
- [x] Classification DUPLICATE/SCENE/EXTRACT/UNCERTAIN
- [x] Export JSON/CSV avec match_type
- [x] Commande `stats` renommée
- [x] Commande `clear` ajoutée
- [ ] Test complet sur dataset réel

---

## 🎯 Prochaines Étapes (Optionnel)

1. **Gestion des pipelines**
   - Créer/éditer/supprimer des pipelines personnalisés
   - Commandes: `pipeline create`, `pipeline edit`, `pipeline list`, `pipeline delete`

2. **Filtres avancés**
   - Filtrer par durée minimale
   - Filtrer par type de match
   - Exclure certains dossiers

3. **Rapport HTML**
   - Générer un rapport visuel interactif
   - Inclure thumbnails des vidéos
   - Timeline des matches

4. **Mode interactif**
   - TUI (Text User Interface) pour parcourir les résultats
   - Prévisualisation vidéo
   - Actions (supprimer, déplacer, renommer)
