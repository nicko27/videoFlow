# 🎵 Guide du système Audio-First

## 🎯 Comment ça marche

Le système **Audio-First** filtre d'abord par l'audio avant de comparer les vidéos, ce qui accélère considérablement la détection des doublons.

### Workflow complet

```
📥 DÉMARRAGE (188 vidéos)
    ↓
┌─────────────────────────────────────────────┐
│ PHASE 1: Audio Fingerprinting              │
│ ⏱️  ~15-30 secondes                        │
│ 🎵 Extraction de l'empreinte audio         │
│ • 4 workers en parallèle                   │
│ • Mode: fast (2-5s/vidéo)                  │
│ • Tous les 188 fichiers traités           │
└─────────────────────────────────────────────┘
    ↓ 188 empreintes audio extraites
    ↓
┌─────────────────────────────────────────────┐
│ PHASE 2A: LSH Indexing                     │
│ ⏱️  < 1 seconde                            │
│ 🔍 Réduction des comparaisons              │
│ • 17,578 paires → ~1,500 paires (91% ✂️)  │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ PHASE 2B: Audio Comparison                 │
│ ⏱️  ~5-10 secondes                         │
│ 🎵 Comparaison audio multi-résolution      │
│ • Coarse (30s) → rejet rapide             │
│ • Medium (120s) → rejet modéré            │
│ • Fine (full) → candidats finaux          │
│ • Seuil: 70%                               │
└─────────────────────────────────────────────┘
    ↓ Exemple: 4 candidats trouvés (2 paires)
    ↓
┌─────────────────────────────────────────────┐
│ PHASE 3: Hash Vidéo SÉLECTIF               │
│ ⏱️  ~2-4 secondes                          │
│ 📊 Hash UNIQUEMENT des candidats           │
│ • 4 vidéos hashées (au lieu de 188!)      │
│ • Économie: 98% du temps de hash 🚀       │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ PHASE 4: Comparaison Vidéo                 │
│ ⏱️  < 1 seconde                            │
│ 🎬 Comparaison finale avec flip detection  │
│ • Seuil: 90%                               │
│ • 2 paires comparées                       │
└─────────────────────────────────────────────┘
    ↓
📤 RÉSULTAT: 2 doublons détectés
   Total: ~25-45 secondes au lieu de 3-5 minutes
```

## ⚙️ Configuration recommandée

### Pour 100-500 vidéos (optimal)

#### Audio Fingerprinting
- **Threshold**: 70% (bon équilibre)
- **Precision Mode**: `fast` (2-5s/vidéo)
- **Workers**: 4 (parallélisme)
- **Cache Size**: 1000

#### LSH (Locality Sensitive Hashing)
- **Enable**: ✅ OUI (réduction 90%)
- **Bands**: 20
- **Rows per band**: 5
- **Use for no audio**: ✅ OUI

#### Multi-Resolution Comparison
- **Enable**: ✅ OUI (2-3x plus rapide)
- **Coarse duration**: 30s
- **Coarse threshold**: 60%
- **Medium duration**: 120s
- **Medium threshold**: 65%

#### Metadata Filter
- **Enable**: ❌ NON (risque faux négatifs)

#### Video Comparison
- **Threshold**: 90%
- **Flip detection**: ✅ OUI
- **Workers**: 8
- **Batch size**: 100

### Pour 500-2000 vidéos (performance)

- Audio Precision: `fast`
- LSH Bands: 25 (plus de précision)
- Multi-resolution: ✅ activé
- Metadata: ❌ désactivé

### Pour < 50 vidéos (qualité maximale)

- Audio Precision: `maximum`
- LSH: peut être désactivé (peu de fichiers)
- Multi-resolution: peut être désactivé
- Video threshold: 95%

## 🎬 Presets disponibles

### ⚡ Maximum Speed
- Audio: fast, LSH activé, Multi-res activé
- **Pour**: Grosse bibliothèque (>500 vidéos)
- **Temps**: Minimal
- **Précision**: Bonne (~85%)

### ⚖️ Balanced (RECOMMANDÉ)
- Audio: fast, LSH activé, Multi-res activé
- **Pour**: Usage normal (100-500 vidéos)
- **Temps**: Rapide
- **Précision**: Très bonne (~90%)

### 🎯 Maximum Quality
- Audio: maximum, LSH désactivé, Multi-res désactivé
- **Pour**: Petite bibliothèque (<100 vidéos) ou validation finale
- **Temps**: Plus long
- **Précision**: Excellente (~95%)

## 📊 Performance attendue

### Exemple concret: 188 vidéos

#### Ancien système (sans audio-first)
```
Hash toutes les vidéos: 188 × 1s = 188s
Comparaisons: 17,578 paires × 0.01s = 176s
TOTAL: ~364s (6 minutes)
```

#### Nouveau système (audio-first)
```
Audio extraction: 188 × 3s = 564s... MAIS EN PARALLÈLE (÷4)
  → 141s réels
LSH + Audio comparison: ~10s
Hash sélectif: 4 × 1s = 4s
Comparaison finale: 2 × 0.01s = ~0s
TOTAL: ~155s (2.5 minutes)
```

**Gain: 57% plus rapide !** ⚡

### Pour 1000 vidéos

- Ancien: ~100 minutes
- Audio-first: ~45 minutes
- **Gain: 55% plus rapide**

## 🐛 Troubleshooting

### Aucun candidat audio trouvé

**Problème**: "Phase 2 complete: 0 audio candidates found"

**Solutions**:
1. Baisser le seuil audio (70% → 60%)
2. Vérifier que les vidéos ont de l'audio (`ffprobe -i video.mp4`)
3. Augmenter les bands LSH (20 → 30)

### Trop de faux positifs

**Problème**: Trop de vidéos considérées comme doublons

**Solutions**:
1. Augmenter le seuil audio (70% → 80%)
2. Augmenter le seuil vidéo (90% → 95%)
3. Désactiver temporairement LSH pour tester

### Extraction audio lente

**Problème**: Phase 1 prend trop de temps

**Solutions**:
1. Vérifier le mode de précision (`fast` vs `balanced`)
2. Augmenter le nombre de workers (4 → 8)
3. Vérifier l'installation de `fpcalc` (`which fpcalc`)

### Erreur "Could not find parameters tab"

**Problème**: Crash au démarrage de l'analyse

**Solutions**:
1. Vérifier que l'onglet Settings est bien créé
2. Redémarrer l'application
3. Vérifier les logs pour l'erreur exacte

## 📈 Optimisations avancées

### Pour SSD rapide
- Augmenter workers: 8-16
- Cache size: 2000-5000

### Pour HDD lent
- Réduire workers: 2-4
- Activer metadata filter (si pas de réencodage)

### Pour vidéos courtes (<5 min)
- Coarse duration: 15s
- Medium duration: 60s

### Pour vidéos longues (>30 min)
- Coarse duration: 60s
- Medium duration: 300s

## 🎯 Cas d'usage

### Détecter les copies exactes
- Audio threshold: 90%
- Video threshold: 95%
- LSH: activé

### Détecter les réencodages
- Audio threshold: 70%
- Video threshold: 85%
- Metadata filter: désactivé
- Flip detection: activé

### Détecter les extraits (scènes)
- Audio threshold: 60%
- Video threshold: 80%
- Multi-resolution: activé (important!)

## ✅ Checklist avant analyse

- [ ] Au moins 2 vidéos ajoutées
- [ ] Preset sélectionné (ou paramètres configurés)
- [ ] `fpcalc` installé (`brew install chromaprint` sur macOS)
- [ ] Espace disque suffisant pour la base de données
- [ ] Seuils cohérents (audio ≤ video)

## 🚀 C'est parti !

Cliquez sur **START** et observez les 3 barres de progression :
1. 🎵 Audio fingerprinting
2. 📊 File hashing (sélectif)
3. 🔍 Duplicate detection

Les logs vous montreront exactement où en est chaque phase !
