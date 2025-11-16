# Détection de Sous-Vidéos (Subsequence Detection)

## Vue d'ensemble

La fonctionnalité de détection de sous-vidéos permet d'identifier quand une vidéo courte est contenue dans une vidéo plus longue. Par exemple :

- **Vidéo A** : Contient les scènes A1, A2, A3 (10 minutes)
- **Vidéo B** : Contient uniquement la scène A2 (3 minutes)
- **Résultat** : Le système détecte que B est une sous-séquence de A avec une position précise

## Caractéristiques

### 🚀 Performance
- **Cache LRU avec limite mémoire** : Protection contre la saturation de la RAM
- **Limite configurable** : Par défaut 500MB, ajustable selon vos besoins
- **Éviction automatique** : Les entrées les moins récemment utilisées sont automatiquement supprimées

### 🎯 Précision
- **Échantillonnage dense** : Par défaut tous les 3 secondes (vs 8 frames fixes pour les doublons)
- **Fenêtre glissante** : Trouve la meilleure correspondance dans la vidéo longue
- **Ratio de correspondance configurable** : Par défaut 80%, ajustable jusqu'à 99%

### 💾 Stockage
- **Base de données intégrée** : Stocke les détections pour révision ultérieure
- **Métadonnées complètes** : Position, ratio de correspondance, confiance
- **Statistiques** : Nombre de détections, ratios moyens, etc.

## Utilisation

### Configuration de base

```python
from src.plugins.duplicate_finder.video_hasher import VideoHasher
from src.plugins.duplicate_finder.subsequence_detector import SubsequenceDetector

# Initialiser le hasher
hasher = VideoHasher(method='pHash')

# Créer le détecteur avec configuration personnalisée
detector = SubsequenceDetector(
    hasher=hasher,
    max_cache_memory_mb=500,        # Limite de cache : 500MB
    sample_interval_seconds=3.0,    # Échantillonner toutes les 3 secondes
    min_match_ratio=0.80            # Nécessite 80% de correspondance
)
```

### Détection simple

```python
# Détecter si video_short est dans video_long
result = detector.find_subsequence(
    short_video="/path/to/short.mp4",
    long_video="/path/to/long.mp4"
)

if result and result['is_subsequence']:
    print(f"Sous-vidéo détectée !")
    print(f"Correspondance : {result['match_ratio']*100:.1f}%")
    print(f"Position : frame {result['start_frame_idx']}")
    print(f"Confiance : {result['confidence']*100:.1f}%")
```

### Détection par lot

```python
# Scanner tous les fichiers vidéo dans une liste
video_files = [...]  # Liste de chemins vidéo

def progress(current, total, message):
    print(f"[{current}/{total}] {message}")

results = detector.detect_all_subsequences(
    video_files,
    progress_callback=progress
)

# Résultats : liste de (short_video, long_video, detection_info)
for short, long, info in results:
    print(f"{short} est dans {long} ({info['match_ratio']*100:.1f}%)")
```

## Paramètres

### Limite de mémoire (`max_cache_memory_mb`)

**Défaut** : 500 MB
**Recommandations** :
- **500-1000 MB** : Usage normal (jusqu'à ~100 vidéos en cache)
- **200-500 MB** : Systèmes avec RAM limitée
- **1000-2000 MB** : Traitement par lots important

**Impact** :
- Cache trop petit → Plus de recalculs, plus lent
- Cache trop grand → Risque de saturation RAM

### Intervalle d'échantillonnage (`sample_interval_seconds`)

**Défaut** : 3.0 secondes
**Recommandations** :
- **1.0-2.0s** : Clips très courts, haute précision requise
- **3.0-5.0s** : Usage normal, bon équilibre
- **5.0-10.0s** : Vidéos très longues, économie de mémoire

**Impact** :
- Intervalle court → Plus de frames, plus précis, plus de mémoire
- Intervalle long → Moins de frames, moins précis, économie mémoire

**Exemple** : Vidéo de 100 secondes
- À 3.0s → ~33 frames → ~264 bytes
- À 1.0s → ~100 frames → ~800 bytes
- À 10.0s → ~10 frames → ~80 bytes

### Ratio minimum de correspondance (`min_match_ratio`)

**Défaut** : 0.80 (80%)
**Recommandations** :
- **0.75-0.80** : Détection permissive, accepte plus de variations
- **0.80-0.90** : Usage normal, bon équilibre
- **0.90-0.95** : Détection stricte, haute confiance requise

**Impact** :
- Ratio bas → Plus de détections, plus de faux positifs
- Ratio haut → Moins de détections, moins de faux positifs

## Gestion de la mémoire

### Protection automatique

Le système protège automatiquement contre la saturation mémoire :

1. **Estimation de taille** : Chaque hash est évalué avant ajout
2. **Éviction LRU** : Les anciennes entrées sont supprimées si nécessaire
3. **Limite stricte** : Le cache ne dépassera jamais `max_cache_memory_mb`

### Surveillance

```python
# Vérifier l'utilisation du cache
stats = detector.get_cache_stats()
print(f"Éléments : {stats['items']}")
print(f"Mémoire : {stats['memory_mb']:.1f} MB")
print(f"Utilisation : {stats['usage_percent']:.1f}%")

# Nettoyer manuellement si nécessaire
detector.clear_cache()
```

### Limites de protection

Pour éviter les vidéos extrêmement longues :
- **Maximum 200 frames** par vidéo (même avec intervalle court)
- Si dépassé, l'échantillonnage est automatiquement élargi
- Exemple : Vidéo de 10000 frames à 1s → réduit automatiquement à 200 frames

## Intégration avec la base de données

### Stockage des détections

```python
# Stocker une détection
detector.db.store_subsequence_detection(
    short_video_path="/path/to/short.mp4",
    long_video_path="/path/to/long.mp4",
    match_ratio=0.87,
    start_frame_idx=450,
    confidence=0.87
)
```

### Récupération des résultats

```python
# Obtenir les détections en attente
pending = detector.db.get_pending_subsequences()
for short, long, match, start, confidence, seq_id in pending:
    print(f"ID {seq_id}: {short} dans {long} ({match*100:.1f}%)")

# Mettre à jour le statut
detector.db.update_subsequence_status(
    subseq_id=seq_id,
    status='processed',
    action='kept_short'
)

# Statistiques
stats = detector.db.get_subsequence_statistics()
print(f"Total : {stats['total']}")
print(f"En attente : {stats['pending']}")
print(f"Ratio moyen : {stats['avg_match_ratio']*100:.1f}%")
```

## Différences avec la détection de doublons

| Aspect | Doublons | Sous-vidéos |
|--------|----------|-------------|
| **Échantillonnage** | 8 positions fixes | Dense (tous les N secondes) |
| **Algorithme** | Comparaison directe | Fenêtre glissante |
| **Mémoire** | Cache simple | Cache LRU limité |
| **Use case** | Même vidéo, encodages différents | Clip extrait d'une vidéo |
| **Seuil typique** | 90-95% | 80-85% |

## Exemples d'utilisation

Voir le fichier `examples/subsequence_detection_example.py` pour des exemples complets :

1. **Détection basique** : Vérifier si B est dans A
2. **Traitement par lots** : Scanner un dossier entier
3. **Paramètres personnalisés** : Ajuster selon vos besoins
4. **Surveillance mémoire** : Vérifier l'utilisation du cache
5. **Intégration base de données** : Stocker et récupérer les résultats

## Performances

### Temps de traitement

Sur un système moderne (i5/i7, 16GB RAM) :
- **Hash dense** : ~2-5 secondes par vidéo (selon longueur)
- **Comparaison** : ~0.1-0.5 secondes par paire
- **Cache hit** : Instantané

### Utilisation mémoire

- **Par vidéo** : ~8 bytes par frame
- **Exemple** : Vidéo de 100s à 3s d'intervalle
  - ~33 frames × 8 bytes × taille hash (8×8) ≈ 2KB
  - Cache de 500MB → ~250,000 vidéos théoriques
  - En pratique : ~500-1000 vidéos (avec overhead)

## Recommandations

### Pour des vidéos courtes (< 5 minutes)
```python
SubsequenceDetector(
    hasher=hasher,
    max_cache_memory_mb=200,
    sample_interval_seconds=2.0,
    min_match_ratio=0.85
)
```

### Pour des vidéos moyennes (5-30 minutes)
```python
SubsequenceDetector(
    hasher=hasher,
    max_cache_memory_mb=500,
    sample_interval_seconds=3.0,
    min_match_ratio=0.80
)
```

### Pour des vidéos longues (> 30 minutes)
```python
SubsequenceDetector(
    hasher=hasher,
    max_cache_memory_mb=1000,
    sample_interval_seconds=5.0,
    min_match_ratio=0.75
)
```

### Pour traitement par lots massif
```python
SubsequenceDetector(
    hasher=hasher,
    max_cache_memory_mb=2000,
    sample_interval_seconds=4.0,
    min_match_ratio=0.80
)
```

## Limitations

1. **Précision limitée** : Ne détecte pas les modifications importantes (recadrage, effets)
2. **Ordre requis** : Les scènes doivent être dans le même ordre
3. **Durée minimale** : Sous-vidéos trop courtes (< 5s) peuvent ne pas être détectées
4. **Mémoire RAM** : Bien que limitée, nécessite quand même de la RAM disponible

## Troubleshooting

### Cache plein rapidement
→ Réduire `max_cache_memory_mb` ou augmenter `sample_interval_seconds`

### Faux négatifs (sous-vidéos non détectées)
→ Réduire `min_match_ratio` ou `sample_interval_seconds`

### Faux positifs (détections incorrectes)
→ Augmenter `min_match_ratio`

### Lenteur excessive
→ Augmenter `sample_interval_seconds` ou utiliser `dHash` au lieu de `pHash`

## Support

Pour toute question ou problème :
1. Vérifiez les exemples dans `examples/`
2. Consultez les logs (niveau DEBUG pour détails)
3. Ajustez les paramètres selon vos besoins
