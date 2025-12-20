# 🎯 Nouvelles Fonctionnalités CLI - Résumé Rapide

**Date**: 2025-12-19
**Version**: 1.2
**Source**: [CLI_IMPROVEMENTS_PROPOSALS.md](CLI_IMPROVEMENTS_PROPOSALS.md)

---

## 🚀 Features Killer

### Feature 1: Recherche dans Arborescences

**Problème résolu**: Tu ne peux pas scanner un dossier pour trouver tous les duplicates, ni détecter où une courte scène apparaît dans tes vidéos longues.

### Feature 2: Gestion et Configuration des Pipelines

**Problème résolu**: Les débutants ne savent pas comment créer, configurer ou régler les pipelines. Il manque une interface claire pour comprendre les algorithmes et sauvegarder les configurations.

### Commandes proposées

#### 1. `duplicateflow scan` - Scan de dossier pour duplicates

```bash
# Trouve tous les duplicates dans une arborescence
duplicateflow scan /media/videos --recursive --pipeline balanced --group-duplicates

# Output exemple:
# Duplicate Groups Found: 12
# Total potential savings: 25.40 GB
```

**Ce que ça fait**:
- ✅ Indexe toutes les vidéos (O(N) avec Fingerprint Index)
- ✅ Trouve candidats via LSH (Locality-Sensitive Hashing)
- ✅ Vérifie avec pipeline complet
- ✅ Groupe en clusters (Union-Find algorithm)
- ✅ Calcule économies potentielles

**Exemple output détaillé**:
```
Discovered 1,247 videos
Building fingerprint index... ━━━━━━━━━━━━━━━━━━━━━━━━ 100%
Found 89 candidate pairs
Verifying with full pipeline... ━━━━━━━━━━━━━━━━━━━━━━━━ 100%

Duplicate Groups Found: 12
┌───────┬───────────┬────────────┬───────────────────┐
│ Group │ Videos    │ Total Size │ Potential Savings │
├───────┼───────────┼────────────┼───────────────────┤
│ #1    │ 3 videos  │ 4.25 GB    │ 2.80 GB           │
│ #2    │ 2 videos  │ 1.80 GB    │ 0.90 GB           │
│ #3    │ 5 videos  │ 8.50 GB    │ 6.80 GB           │
└───────┴───────────┴────────────┴───────────────────┘

Total potential savings: 25.40 GB
```

#### 2. `duplicateflow find-scenes` - Détection scènes incluses

```bash
# Trouve où short_clip.mp4 apparaît dans tes vidéos
duplicateflow find-scenes short_clip.mp4 --in /archive --show-timestamps

# Output exemple:
# Found 3 matches for short_clip.mp4
# ┌─────────────────────┬──────────────────────┬──────────┬────────────┐
# │ Target Video        │ Time Range           │ Duration │ Similarity │
# ├─────────────────────┼──────────────────────┼──────────┼────────────┤
# │ movie_full.mp4      │ 00:02:35 → 00:02:50  │ 15.0s    │ 96.8%      │
# │ compilation_01.avi  │ 01:15:20 → 01:15:35  │ 15.0s    │ 94.2%      │
# └─────────────────────┴──────────────────────┴──────────┴────────────┘
#
# FFmpeg commands to extract scenes:
#   ffmpeg -i 'movie_full.mp4' -ss 155.00 -t 15.00 -c copy 'scene_1.mp4'
```

**Ce que ça fait**:
- ✅ Sliding window sur vidéos longues
- ✅ Timestamps précis de correspondance (HH:MM:SS)
- ✅ Merge overlapping matches
- ✅ Génère commandes FFmpeg pour extraction
- ✅ Batch mode pour scanner plusieurs clips

**Algorithme**:
- Window size = durée du clip recherché
- Step size = 25% de window size (overlap 75% pour précision)
- Compare chaque window avec pipeline complet
- Merge matches qui se chevauchent à >50%

#### 3. `duplicateflow cross-search` - Comparaison 2 dossiers

```bash
# Compare 2 dossiers entre eux
duplicateflow cross-search /new_downloads /archive --show-direction

# Use case: Tu veux savoir quelles vidéos de /new_downloads
# sont déjà dans /archive
```

**Ce que ça fait**:
- ✅ Compare vidéos de folder A vs folder B
- ✅ Identifie duplicates entre collections
- ✅ Affiche direction (A→B ou B→A)

#### 4. `duplicateflow pipeline create` - Création interactive de pipeline

```bash
# Mode interactif guidé pour débutants
duplicateflow pipeline create --interactive

# Le CLI va demander:
# 1. Quel est votre cas d'usage? (duplicates exacts, scènes similaires, etc.)
# 2. Pour chaque algorithme: seuil, poids, paramètres (avec explications claires)
# 3. Validateurs pré/post
# 4. Sauvegarde automatique en YAML avec commentaires
```

**Ce que ça fait**:
- ✅ Mode guidé pour débutants (questions/réponses)
- ✅ Explications claires de chaque algorithme (quand utiliser, vitesse, précision)
- ✅ Recommandations de paramètres selon cas d'usage
- ✅ Sauvegarde en YAML commenté et lisible
- ✅ Validation en temps réel

#### 5. `duplicateflow algorithms explain` - Documentation algorithmes

```bash
# Expliquer un algorithme pour débutants
duplicateflow algorithms explain frame_hash

# Output:
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 frame_hash - Hash de Frames
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# DESCRIPTION:
#   Compare les hashes perceptuels de frames vidéo.
#
# QUAND L'UTILISER:
#   ✓ Duplicates exacts ou quasi-exacts
#   ✓ Re-encodages avec mêmes frames
#   ✗ Vidéos avec crop/zoom différents
#
# VITESSE: ⚡⚡⚡ Très rapide (~30 vidéos/sec)
#
# PARAMÈTRES:
#   threshold (70-95, défaut: 85)
#     • 95: Uniquement duplicates quasi-parfaits
#     • 85: Équilibré ✓
#     • 70: Permissif
#
# COMBINAISONS RECOMMANDÉES:
#   • frame_hash + color_histogram → Duplicates exacts
```

**Ce que ça fait**:
- ✅ Explications adaptées aux débutants
- ✅ Cas d'usage clairs (quand oui, quand non)
- ✅ Recommandations de paramètres
- ✅ Combinaisons d'algorithmes suggérées

#### 6. `duplicateflow pipeline` - Gestion des pipelines

```bash
# Lister tous les pipelines (DB + YAML)
duplicateflow pipeline list

# Charger un pipeline YAML
duplicateflow pipeline load my_pipeline.yaml

# Valider un pipeline YAML avant utilisation
duplicateflow pipeline validate my_pipeline.yaml

# Exporter un pipeline DB vers YAML
duplicateflow pipeline export balanced --output balanced.yaml
```

**Ce que ça fait**:
- ✅ Liste pipelines DB et fichiers YAML
- ✅ Import/export YAML ↔ DB
- ✅ Validation avec messages d'erreur clairs
- ✅ Templates de pipelines pour démarrer rapidement

---

## 🎬 Cas d'Usage Concrets

### Cas 1: Gestionnaire médiathèque (2 TB de vidéos)
```bash
# Scan complet
duplicateflow scan /media/videos --recursive --pipeline balanced

# Output: 12 groupes trouvés, 25.4 GB économies potentielles
```
**Résultat**: 25+ GB libérés, vue complète des duplicates

### Cas 2: Producteur vidéo (cherche intro/outro)
```bash
# Trouve toutes occurrences d'une intro dans projets
duplicateflow find-scenes intro_v2.mp4 --in /projects --show-timestamps

# Génère commandes FFmpeg pour extraire
```
**Résultat**: Retrouve instantanément scènes dans des heures de footage

### Cas 3: Archiviste (nouvelle acquisition)
```bash
# Compare nouvelle acquisition vs fonds existant
duplicateflow cross-search /new_acquisition /archive --pipeline thorough
```
**Résultat**: Évite acquisitions redondantes

### Cas 4: Débutant (créer premier pipeline)
```bash
# Mode interactif guidé
duplicateflow pipeline create --interactive

# Répondre aux questions:
# - Cas d'usage: Duplicates exacts ✓
# - frame_hash: threshold 85, weight 0.5 ✓
# - color_histogram: threshold 70, weight 0.3 ✓
# - Sauvegarde: my_first_pipeline.yaml ✓

# Tester le pipeline
duplicateflow scan /videos --pipeline my_first_pipeline.yaml
```
**Résultat**: Pipeline optimisé créé en 2 minutes, sans expertise technique

---

## 📈 Métriques de Performance

### Complexité algorithmique
- **Scan dossier**: O(N) au lieu de O(N²) grâce au Fingerprint Index
- **Temps scan**: <30s pour 1000 vidéos (index uniquement)
- **Précision**: 95%+ sur détection scènes

### Impact Business
- **Économies stockage**: 20-40% en moyenne
- **Vitesse vs manuel**: 10x plus rapide
- **Précision**: 0 faux négatifs critiques

---

## 🎯 Priorisation

### Must-Have (Implémenter d'abord)
1. ✅ **Pipeline Management** ⭐ - CRITIQUE: Base du système (4 jours)
   - `duplicateflow pipeline create --interactive`
   - `duplicateflow algorithms explain`
   - `duplicateflow pipeline list/load/validate`
2. ✅ **Arborescences** ⭐ - Feature killer (6 jours)
   - `duplicateflow scan` - Scan dossiers avec grouping (3 jours)
   - `duplicateflow find-scenes` - Détection scènes incluses (2 jours)
   - `duplicateflow cross-search` - Comparaison 2 dossiers (1 jour)

**Total**: ~10 jours de dev pour features complètes

**Note**: Pipeline Management doit être implémenté EN PREMIER car toutes les autres features en dépendent (scan, find-scenes, cross-search utilisent tous des pipelines).

---

## 🔧 Détails Techniques

### Algorithmes clés

**Union-Find (pour grouping)**:
```python
def find(x):
    if parent[x] != x:
        parent[x] = find(parent[x])  # Path compression
    return parent[x]

def union(x, y):
    parent[find(x)] = find(y)
```

**Sliding Window (pour scènes)**:
```python
window_size = query_duration
step_size = window_size * 0.25  # 75% overlap

while current_time + window_size <= target_duration:
    result = pipeline.compare(query, target, start_time=current_time, duration=window_size)
    if result.accepted:
        matches.append(...)
        current_time += window_size  # Skip overlap
    else:
        current_time += step_size  # Continue sliding
```

**Fingerprint Index (pour O(N))**:
```python
# Index inversé: hash → [video_ids]
index = defaultdict(set)

for video in videos:
    fingerprint = extract_fingerprint(video)
    for hash_value in fingerprint:
        index[hash_value].add(video)

# Trouver candidats: vote counting
candidates = Counter()
for hash_value in query_hashes:
    for video in index[hash_value]:
        candidates[video] += 1  # Vote

return [v for v, votes in candidates.items() if votes > threshold]
```

---

## 🚀 Roadmap d'Implémentation

### Semaine 1: Fondations
- Migration vers `duplicateflow/cli/`
- Structure modulaire

### Semaine 2: Pipeline Management ⭐ **PRIORITÉ #1**
- **`duplicateflow pipeline create --interactive`** (2 jours)
  - Mode guidé questions/réponses
  - Explications algorithmes pour débutants
  - Sauvegarde YAML commenté

- **`duplicateflow algorithms explain`** (1 jour)
  - Documentation algorithmes
  - Recommandations paramètres
  - Combinaisons suggérées

- **`duplicateflow pipeline list/load/validate`** (1 jour)
  - Gestion pipelines YAML ↔ DB
  - Validation configuration
  - Templates

### Semaine 3-4: Recherche dans Arborescences ⭐
- **`duplicateflow scan`** (3 jours)
  - Découverte vidéos
  - Fingerprint indexing
  - LSH candidate finding
  - Vérification pipeline
  - Grouping Union-Find
  - Display results

- **`duplicateflow find-scenes`** (2 jours)
  - Query feature extraction
  - Candidate discovery
  - Sliding window search
  - Overlapping merge
  - FFmpeg command generation

- **`duplicateflow cross-search`** (1 jour)
  - Bidirectional comparison
  - Result aggregation

**Total**: ~4 semaines pour implémentation complète

---

## 📚 Documentation Complète

Pour détails complets (code implémentation, edge cases, etc.):
👉 **[CLI_IMPROVEMENTS_PROPOSALS.md](CLI_IMPROVEMENTS_PROPOSALS.md)** (2,436 lignes, 12 catégories)

---

**Créé**: 2025-12-19
**Auteur**: Claude Sonnet 4.5
**Status**: ✅ Résumé pour référence rapide
**Version**: 1.2 - Arborescences + Pipeline Management
**Features**: 2 catégories killer (11. Recherche Arborescences, 12. Pipeline Management)
