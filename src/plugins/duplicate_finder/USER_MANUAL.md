# DUPLICATE FINDER - Manuel Utilisateur

**Version**: 1.0
**Date**: 2025-12-06
**Application**: Duplicate Finder Plugin pour VideoFlow

---

## Table des Matières

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Démarrage Rapide](#démarrage-rapide)
4. [Guide des Fonctionnalités](#guide-des-fonctionnalités)
5. [Modes d'Analyse](#modes-danalyse)
6. [Configuration Avancée](#configuration-avancée)
7. [Résolution de Problèmes](#résolution-de-problèmes)
8. [FAQ](#faq)
9. [Conseils et Astuces](#conseils-et-astuces)

---

## Introduction

### Qu'est-ce que Duplicate Finder?

Duplicate Finder est un outil puissant pour détecter les vidéos en double dans vos collections. Il utilise des algorithmes avancés pour:

- **Détecter les duplicatas exacts** - Même avec des noms de fichiers différents
- **Détecter les duplicatas similaires** - Vidéos légèrement modifiées (compression, recadrage)
- **Trouver des extraits** - Détecter quand une vidéo courte existe dans une vidéo plus longue
- **Comparer intelligemment** - Audio-first mode pour des analyses 10x plus rapides

### Cas d'Utilisation

✅ **Nettoyage de bibliothèque** - Supprimer les copies inutiles
✅ **Organisation** - Identifier les fichiers redondants avant archivage
✅ **Optimisation d'espace** - Libérer de l'espace disque
✅ **Détection d'extraits** - Trouver des clips dans des vidéos complètes

---

## Installation

### Prérequis

**Système d'exploitation**:
- ✅ macOS 10.15+
- ✅ Linux (Ubuntu 20.04+, Fedora 35+)
- ✅ Windows 10/11

**Python**: Version 3.8 ou supérieure

**Espace disque**: 500 MB pour l'application + cache

### Installation des Dépendances

```bash
# Naviguer vers le répertoire du projet
cd /path/to/videoFlow

# Installer les dépendances Python
pip install -r requirements.txt

# Dépendances spécifiques au plugin
pip install opencv-python>=4.8.0
pip install librosa>=0.10.0
pip install soundfile>=0.12.1
pip install datasketch>=1.6.0
pip install numpy>=1.24.0
pip install imagehash>=4.3.1
pip install PyQt6>=6.5.0
```

### Vérification de l'Installation

```bash
# Lancer l'application
python main.py

# Vérifier que le plugin apparaît dans le menu
# Menu → Plugins → Duplicate Finder
```

---

## Démarrage Rapide

### Première Utilisation (5 minutes)

#### 1. Ajouter des Fichiers

**Option A: Ajouter des fichiers individuels**
```
1. Cliquer sur "📄 Ajouter des fichiers"
2. Sélectionner vos vidéos (Ctrl/Cmd+Click pour plusieurs)
3. Cliquer "Ouvrir"
```

**Option B: Ajouter un dossier complet**
```
1. Cliquer sur "📂 Ajouter un dossier"
2. Sélectionner le dossier contenant vos vidéos
3. Les vidéos seront scannées récursivement
```

#### 2. Configurer l'Analyse (Optionnel)

**Paramètres recommandés pour débuter**:
- **Seuil de similarité**: 85% (par défaut)
- **Mode**: Simple (pour < 100 vidéos)
- **Workers**: 4 threads (par défaut)

#### 3. Lancer l'Analyse

```
1. Cliquer sur "▶️ Démarrer l'analyse"
2. Attendre la fin de l'analyse (barre de progression)
3. Les duplicatas apparaîtront dans la liste
```

#### 4. Gérer les Duplicatas

```
1. Double-cliquer sur une paire de duplicatas
2. Comparer les vidéos côte à côte
3. Choisir l'action:
   - "Conserver le premier" (Touche: 1)
   - "Conserver le second" (Touche: 2)
   - "Conserver les deux" (Touche: 3 ou Échap)
```

#### 5. Supprimer les Duplicatas

```
1. Après avoir marqué tous les duplicatas
2. Cliquer sur "🗑️ Supprimer les duplicatas marqués"
3. Confirmer la suppression
4. Les fichiers seront déplacés vers la corbeille
```

---

## Guide des Fonctionnalités

### Interface Principale

```
┌─────────────────────────────────────────────────┐
│  📂 Ajouter fichiers/dossier    ⚙️ Paramètres   │
├─────────────────────────────────────────────────┤
│  Liste des fichiers                             │
│  ┌─────────────────────────────────────────┐   │
│  │ ✅ video1.mp4              (1.2 GB)     │   │
│  │ ✅ video2.mp4              (850 MB)     │   │
│  │ ✅ video3.mp4              (2.1 GB)     │   │
│  └─────────────────────────────────────────┘   │
├─────────────────────────────────────────────────┤
│  ▶️ Démarrer      🗑️ Effacer      🔄 Actualiser │
├─────────────────────────────────────────────────┤
│  Résultats des duplicatas                       │
│  ┌─────────────────────────────────────────┐   │
│  │ 📊 Similarité: 98.5%                    │   │
│  │ 📂 video1.mp4 ↔ video1_copy.mp4         │   │
│  │ 📊 Similarité: 95.2%                    │   │
│  │ 📂 video2.mp4 ↔ video2_compressed.mp4   │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### Dialogue de Comparaison

Lors du double-clic sur un duplicata:

```
┌──────────────────────────────────────────────────────┐
│  Comparaison de Vidéos - Similarité: 95.5%          │
├──────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐        │
│  │                 │    │                 │        │
│  │   Vidéo 1       │    │   Vidéo 2       │        │
│  │   1.2 GB        │    │   850 MB        │        │
│  │   1920x1080     │    │   1920x1080     │        │
│  │                 │    │                 │        │
│  └─────────────────┘    └─────────────────┘        │
├──────────────────────────────────────────────────────┤
│  ▶️ Lecture    ⏸️ Pause    ⏮️ Début    ⏭️ Fin      │
│  ────────────────○─────────────── 00:45 / 02:30    │
├──────────────────────────────────────────────────────┤
│  [Conserver 1]  [Conserver 2]  [Les deux]  [Fermer]│
│      (1)            (2)            (3)      (Échap) │
└──────────────────────────────────────────────────────┘
```

**Raccourcis clavier**:
- `1` : Conserver la vidéo de gauche
- `2` : Conserver la vidéo de droite
- `3` ou `Échap` : Conserver les deux
- `Espace` : Lecture/Pause
- `←` `→` : Reculer/Avancer de 5 secondes
- `Home` : Début de la vidéo
- `End` : Fin de la vidéo

---

## Modes d'Analyse

### Mode Simple

**Recommandé pour**: < 100 vidéos

**Fonctionnement**:
1. Calcul des hashes pour chaque vidéo
2. Comparaison N² de toutes les paires
3. Résultats triés par similarité

**Avantages**:
- Simple et direct
- Résultats complets
- Pas de configuration

**Temps estimé**:
- 10 vidéos: ~30 secondes
- 50 vidéos: ~3 minutes
- 100 vidéos: ~10 minutes

---

### Mode Audio-First (Recommandé)

**Recommandé pour**: > 50 vidéos

**Fonctionnement**:
1. ✅ **Phase 1**: Extraction audio (rapide)
2. ✅ **Phase 2**: Comparaison audio (ultra-rapide)
3. ✅ **Phase 3**: Comparaison vidéo des candidats uniquement

**Avantages**:
- ⚡ 10x plus rapide que le mode simple
- 🎯 Précision identique
- 💾 Utilise moins de mémoire

**Exemple de gain**:
```
100 vidéos:
- Mode simple: 4,950 comparaisons vidéo → 10 minutes
- Mode audio-first: 15 candidats → 1 minute
→ Gain: 10x plus rapide!
```

**Configuration**:
```
Paramètres Audio-First:
- Seuil audio: 0.60 (60% de similarité)
- Durée échantillon: 10 secondes
- Offset: 30 secondes (ignorer intro/générique)
```

---

### Mode Avancé 3-Level

**Recommandé pour**: > 500 vidéos (collections massives)

**Fonctionnement**:
1. **Level 1 - LSH (Locality-Sensitive Hashing)**
   - Filtre ultra-rapide
   - Élimine 95% des non-duplicatas
   - Temps: millisecondes

2. **Level 2 - Audio Fingerprinting**
   - Comparaison audio des candidats
   - Précision: 90%
   - Temps: secondes

3. **Level 3 - Video Hash Comparison**
   - Comparaison vidéo finale
   - Précision: 99%
   - Temps: minutes

**Avantages**:
- ⚡⚡⚡ Jusqu'à 100x plus rapide
- 📊 Optimisé pour grandes collections
- 🎯 Précision maximale

**Temps estimé**:
- 500 vidéos: ~5 minutes (vs 2 heures en mode simple)
- 1000 vidéos: ~12 minutes (vs 8 heures en mode simple)
- 5000 vidéos: ~1 heure (vs 10+ jours en mode simple)

---

### Mode Détection de Scènes

**Recommandé pour**: Trouver des extraits dans des vidéos longues

**Fonctionnement**:
1. Sélectionner une vidéo courte (l'extrait recherché)
2. Sélectionner des vidéos longues (où chercher)
3. L'algorithme trouve où l'extrait apparaît

**Algorithmes disponibles**:

**Option A: Audio Fingerprinting (Rapide)**
- Basé sur l'audio (comme Shazam)
- Très rapide: ~1 minute pour 10 vidéos longues
- Précision: 85-90%
- Robuste aux modifications (compression, recadrage)

**Option B: Strategy 3 Verification (Précis)**
- Analyse DCT + détection de coupures
- Plus lent: ~5 minutes pour 10 vidéos
- Précision: 99.9% (presque aucun faux positif)
- Parfait pour validation finale

**Cas d'usage**:
- Trouver des clips dans des vidéos complètes
- Identifier des extraits piratés
- Vérifier l'origine de clips courts

**Exemple**:
```
Vidéo courte: "extrait_drole.mp4" (30 secondes)
Vidéos longues: "film_complet.mp4" (2 heures)

Résultat:
✅ Trouvé à 01:23:45 dans "film_complet.mp4"
   Confiance: 98.5%
```

---

## Configuration Avancée

### Paramètres Principaux

#### Seuil de Similarité

**Valeur**: 0-100% (défaut: 85%)

```
95-100% : Duplicatas quasi-identiques uniquement
85-94%  : Recommandé (détecte compression légère)
75-84%  : Détecte recadrages et modifications
< 75%   : Risque élevé de faux positifs
```

**Recommandations par cas d'usage**:
- **Duplicatas exacts**: 95%
- **Usage général**: 85% ⭐ (recommandé)
- **Vidéos modifiées**: 75%

#### Workers (Threads Parallèles)

**Hash Workers**: Threads pour calculer les hashes
- Défaut: 4
- Recommandé: Nombre de cœurs CPU
- Plus = plus rapide, mais plus de CPU

**Comparison Workers**: Threads pour comparer les vidéos
- Défaut: 8
- Recommandé: 2x nombre de cœurs CPU
- Plus = plus rapide, mais plus de mémoire

**Exemples**:
```
CPU 4 cœurs:
- Hash workers: 4
- Comparison workers: 8

CPU 8 cœurs:
- Hash workers: 8
- Comparison workers: 16
```

#### Timeouts

**Hash Timeout**: Temps max pour hasher une vidéo
- Défaut: 120 secondes
- Augmenter pour très grandes vidéos (> 5 GB)
- Diminuer pour ignorer vidéos corrompues plus vite

**Comparison Timeout**: Temps max pour comparer
- Défaut: 300 secondes (5 minutes)
- Pour vidéos 4K+ : 600 secondes

---

### Paramètres Audio-First

**Accessible via**: Menu Paramètres → Audio-First Configuration

#### Seuil Audio (audio_threshold)

**Valeur**: 0.0-1.0 (défaut: 0.60)

```
0.70-1.00 : Très strict (peu de candidats, très fiables)
0.60-0.69 : Recommandé ⭐ (bon équilibre)
0.50-0.59 : Permissif (plus de candidats, plus de bruit)
```

#### Durée d'Échantillon (sample_duration)

**Valeur**: 5-30 secondes (défaut: 10s)

```
5s  : Plus rapide, moins précis
10s : Recommandé ⭐ (bon équilibre)
20s : Plus lent, plus précis
30s : Maximum de précision
```

#### Offset de Début (start_offset)

**Valeur**: 0-120 secondes (défaut: 30s)

**Pourquoi?**: Ignorer les génériques/intros différents

```
0s  : Commence au début (risque si générique différent)
30s : Recommandé ⭐ (ignore génériques courts)
60s : Pour génériques longs
```

#### Nombre de Segments (num_segments)

**Valeur**: 1-10 (défaut: 3)

**Plus de segments** = plus précis mais plus lent

```
1 segment  : Ultra-rapide, moins fiable
3 segments : Recommandé ⭐
5 segments : Maximum de précision
```

---

### Paramètres Avancés 3-Level

**Accessible via**: Menu Paramètres → Advanced Configuration

#### Level 1 - LSH

**LSH Bands**: 10-30 (défaut: 20)
- Plus = plus strict (moins de candidats)
- Moins = plus permissif (plus de candidats)

**LSH Rows**: 3-10 (défaut: 5)
- Plus = plus strict
- Moins = plus permissif

#### Level 2 - Audio

**Audio Sample Rate**: 11025-44100 Hz (défaut: 22050)
- Plus haut = plus précis mais plus lent
- Plus bas = plus rapide mais moins précis

**Fingerprint Size**: 128-512 (défaut: 256)
- Plus grand = plus précis
- Plus petit = plus rapide

#### Level 3 - Video

**Frame Sample Count**: 10-100 (défaut: 30)
- Plus = plus précis mais plus lent
- Moins = plus rapide mais moins précis

---

## Résolution de Problèmes

### "Aucun duplicata trouvé" mais je sais qu'il y en a

**Solutions**:

1. **Baisser le seuil**
   ```
   Paramètres → Seuil de similarité → 75%
   ```

2. **Essayer le mode Audio-First**
   ```
   Mode → Audio-First
   Seuil audio → 0.50
   ```

3. **Vérifier les vidéos manuellement**
   - Les vidéos sont-elles vraiment similaires?
   - Même résolution? Même codec?
   - Utiliser le dialogue de comparaison manuel

4. **Activer les logs détaillés**
   ```python
   # Dans la console Python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

---

### L'analyse est très lente

**Solutions**:

1. **Utiliser le mode Audio-First**
   - 10x plus rapide pour > 50 vidéos

2. **Réduire les workers si RAM insuffisante**
   ```
   Paramètres → Hash Workers → 2
   Paramètres → Comparison Workers → 4
   ```

3. **Augmenter les workers si CPU disponible**
   ```
   Paramètres → Hash Workers → 8 (nombre de cœurs)
   Paramètres → Comparison Workers → 16 (2x cœurs)
   ```

4. **Activer l'optimisation "Early Exit"**
   ```
   Paramètres → Optimisations → Early Exit ✅
   ```

5. **Réduire le nombre de frames analysées**
   ```
   Paramètres → Frame Count → 20 (au lieu de 30)
   ```

---

### L'application plante pendant l'analyse

**Diagnostics**:

1. **Vérifier les logs**
   ```bash
   # Localisation des logs
   ~/.duplicate_finder/logs/duplicate_finder.log

   # macOS/Linux
   tail -f ~/.duplicate_finder/logs/duplicate_finder.log

   # Windows
   type %USERPROFILE%\.duplicate_finder\logs\duplicate_finder.log
   ```

2. **Vérifier les vidéos corrompues**
   ```bash
   # Tester avec ffmpeg
   ffmpeg -v error -i video.mp4 -f null - 2>error.log
   ```

3. **Réduire la charge mémoire**
   - Fermer autres applications
   - Réduire les workers: Hash=2, Comparison=4
   - Analyser par petits lots (20-30 vidéos)

4. **Vérifier l'espace disque**
   ```bash
   # Le cache peut prendre beaucoup d'espace
   du -sh ~/.duplicate_finder/cache/

   # Nettoyer le cache si nécessaire
   rm -rf ~/.duplicate_finder/cache/*
   ```

---

### Erreur "LSH Level 1 returns 0 candidates"

**Cause**: La librairie `datasketch` n'est pas installée

**Solution**:
```bash
pip install datasketch>=1.6.0

# Vérifier l'installation
python -c "import datasketch; print(datasketch.__version__)"
```

---

### Erreur "Cannot extract audio"

**Causes possibles**:
1. Fichier vidéo sans piste audio
2. Codec audio non supporté
3. Fichier corrompu

**Solutions**:

1. **Vérifier la piste audio**
   ```bash
   ffprobe -v error -select_streams a:0 -show_entries stream=codec_name video.mp4
   ```

2. **Réencoder l'audio**
   ```bash
   ffmpeg -i video.mp4 -c:v copy -c:a aac output.mp4
   ```

3. **Utiliser le mode simple** (sans audio)
   ```
   Mode → Simple (évite l'extraction audio)
   ```

---

### Timeout pendant la détection de scènes

**Solution**:
```
Paramètres → Detection Timeout → 600 (10 minutes)
```

Pour vidéos très longues (> 2 heures):
```
Paramètres → Detection Timeout → 1800 (30 minutes)
```

---

### Fichiers non supprimés après marquage

**Vérifications**:

1. **Permissions de fichiers**
   ```bash
   # Vérifier les permissions
   ls -la /path/to/video.mp4

   # Corriger si nécessaire
   chmod 644 /path/to/video.mp4
   ```

2. **Fichier en cours d'utilisation**
   - Fermer les lecteurs vidéo
   - Fermer les dialogues de comparaison
   - Redémarrer l'application

3. **Vérifier la corbeille du système**
   - macOS: ~/.Trash/
   - Linux: ~/.local/share/Trash/
   - Windows: Corbeille (Recycle Bin)

---

## FAQ

### Q: Puis-je récupérer les fichiers supprimés?

**R**: Oui! Les fichiers sont déplacés vers la corbeille système, pas supprimés définitivement.

- **macOS**: Finder → Corbeille
- **Linux**: Fichiers → Corbeille
- **Windows**: Corbeille (Recycle Bin)

Vous pouvez les restaurer à tout moment.

---

### Q: Quelle est la différence entre les modes?

**R**:

| Mode | Vitesse | Précision | Cas d'usage |
|------|---------|-----------|-------------|
| Simple | Moyen | 99% | < 100 vidéos |
| Audio-First | Rapide ⚡ | 99% | > 50 vidéos |
| Advanced 3-Level | Ultra-rapide ⚡⚡⚡ | 99% | > 500 vidéos |
| Scene Detection | Variable | 85-99% | Trouver extraits |

**Recommandation**: Audio-First pour usage général

---

### Q: L'application fonctionne-t-elle hors ligne?

**R**: Oui! Duplicate Finder fonctionne 100% hors ligne. Aucune connexion Internet requise.

---

### Q: Quels formats vidéo sont supportés?

**R**: Tous les formats supportés par FFmpeg:

✅ **Populaires**: MP4, AVI, MKV, MOV, WMV, FLV, WEBM
✅ **Professionnels**: ProRes, DNxHD, AVCHD
✅ **Anciens**: MPEG, VOB, 3GP, ASF

Si FFmpeg peut le lire, Duplicate Finder peut l'analyser!

---

### Q: Combien d'espace disque est nécessaire pour le cache?

**R**: Approximativement:

```
Cache par vidéo:
- Hash: ~10 KB
- Audio fingerprint: ~50 KB
- Frames extraites: ~500 KB

Exemple pour 1000 vidéos:
- Hashes: 10 MB
- Audio: 50 MB
- Frames: 500 MB
→ Total: ~560 MB
```

**Nettoyage du cache**:
```
Paramètres → Cache → Nettoyer le cache
```

---

### Q: Puis-je analyser des vidéos sur un disque externe?

**R**: Oui! Mais considérez:

- **USB 2.0**: Lent (10-20 MB/s) → Analyse 3-5x plus lente
- **USB 3.0**: Rapide (100-200 MB/s) → Performance normale
- **Thunderbolt**: Très rapide (500+ MB/s) → Performance optimale

**Recommandation**: Copier les vidéos sur le disque interne pour meilleure performance.

---

### Q: L'application utilise-t-elle l'accélération GPU?

**R**: Partiellement.

- ✅ **Décodage vidéo**: Utilise le GPU si disponible (via FFmpeg/OpenCV)
- ❌ **Calculs de hash**: CPU uniquement
- ❌ **Comparaisons**: CPU uniquement

**Performance**: GPU peut accélérer de 20-30% le décodage vidéo.

---

### Q: Peut-on annuler une analyse en cours?

**R**: Oui!

```
Cliquer sur ⏹️ Arrêter l'analyse
```

L'arrêt est gracieux:
- Complète l'opération en cours
- Sauvegarde les résultats partiels
- Ferme proprement les fichiers
- Temps d'arrêt: < 5 secondes

---

### Q: Les métadonnées sont-elles prises en compte?

**R**: Non. La détection est basée uniquement sur le contenu audio/vidéo, pas sur:
- ❌ Nom de fichier
- ❌ Date de création
- ❌ Tags/métadonnées
- ❌ Taille de fichier

**Avantage**: Détecte les duplicatas même avec des noms/dates différents!

---

## Conseils et Astuces

### 🚀 Optimisation des Performances

#### 1. Pré-trier vos vidéos

**Regrouper par similarité de durée**:
```
Court/  (< 5 min)
Moyen/  (5-30 min)
Long/   (> 30 min)
```

**Pourquoi**: Les duplicatas ont généralement des durées similaires.

#### 2. Utiliser le cache intelligemment

**Ne pas nettoyer le cache** si:
- Vous analysez souvent les mêmes vidéos
- Vous testez différents seuils
- Vous comparez différents modes

**Nettoyer le cache** si:
- Cache > 5 GB
- Vidéos supprimées/déplacées
- Espace disque faible

#### 3. Optimiser les workers

**Formule recommandée**:
```python
Hash Workers = CPU_CORES
Comparison Workers = CPU_CORES * 2

# Exemples:
# 4 cœurs → 4 hash, 8 comparison
# 8 cœurs → 8 hash, 16 comparison
# 16 cœurs → 16 hash, 32 comparison
```

**Si RAM limitée** (< 8 GB):
```python
Hash Workers = 2
Comparison Workers = 4
```

---

### 🎯 Améliorer la Précision

#### 1. Ajuster le seuil progressivement

**Stratégie en escalier**:
```
1. Commencer à 95% → Duplicatas exacts
2. Baisser à 85% → Duplicatas compressés
3. Baisser à 75% → Duplicatas modifiés
4. Vérifier manuellement les résultats < 80%
```

#### 2. Utiliser la comparaison visuelle

**Pour chaque paire < 90% de similarité**:
1. Double-cliquer pour comparer
2. Vérifier visuellement (jouer les deux vidéos)
3. Décider manuellement

**Pourquoi**: Évite les faux positifs

#### 3. Combiner plusieurs modes

**Workflow optimal**:
```
1. Mode Audio-First (seuil 0.60) → Candidats
2. Vérifier chaque candidat visuellement
3. Mode Strategy 3 pour confirmation finale
```

---

### 💡 Astuces Avancées

#### 1. Traitement par lots pour grandes collections

**Pour 1000+ vidéos**:
```
1. Diviser en lots de 200 vidéos
2. Analyser chaque lot séparément
3. Combiner les résultats

Avantages:
- Plus stable
- Peut reprendre si crash
- Utilise moins de RAM
```

#### 2. Utiliser les raccourcis clavier

**Dans le dialogue de comparaison**:
```
1 = Garder gauche (fichier le plus propre)
2 = Garder droite
3 = Les deux
Espace = Lecture/Pause
← → = Navigation rapide
Home/End = Début/Fin
```

**Productivité**: Traiter 1 paire toutes les 5 secondes au lieu de 15!

#### 3. Ordre de priorité des fichiers

**Le système place automatiquement à gauche**:
1. Fichier sans "(1)", "(2)", "_copy" dans le nom
2. Fichier plus petit (meilleure compression)
3. Ordre alphabétique

**Astuce**: La plupart du temps, appuyer sur "1" est le bon choix!

#### 4. Analyse différentielle

**Pour nouvelles vidéos uniquement**:
```
1. Analyser collection existante → Sauvegarder résultats
2. Ajouter nouvelles vidéos
3. Analyser uniquement les nouvelles vs existantes
4. Gain de temps: 10-50x plus rapide
```

#### 5. Utiliser les filtres de métadonnées

**Workflow**:
```
1. Trier par taille de fichier
2. Analyser par groupes de tailles similaires
3. Les duplicatas ont souvent des tailles proches (±10%)
```

---

### 🔧 Maintenance et Nettoyage

#### Cache Management

**Localisation du cache**:
```
~/.duplicate_finder/cache/
├── hashes/           # Hashes vidéo (~10 KB/vidéo)
├── audio/            # Fingerprints audio (~50 KB/vidéo)
└── frames/           # Frames extraites (~500 KB/vidéo)
```

**Commandes de nettoyage**:
```bash
# Nettoyer tout le cache
rm -rf ~/.duplicate_finder/cache/*

# Nettoyer uniquement les frames (plus gros)
rm -rf ~/.duplicate_finder/cache/frames/*

# Nettoyer cache > 30 jours
find ~/.duplicate_finder/cache/ -mtime +30 -delete
```

#### Logs Management

**Vérifier la taille des logs**:
```bash
du -sh ~/.duplicate_finder/logs/
```

**Nettoyer les vieux logs**:
```bash
# Garder uniquement les 7 derniers jours
find ~/.duplicate_finder/logs/ -mtime +7 -delete
```

#### Base de Données

**Optimisation de la base de données**:
```sql
-- Ouvrir la DB avec sqlite3
sqlite3 ~/.duplicate_finder/data/duplicates.db

-- Optimiser
VACUUM;
ANALYZE;
```

---

### 📊 Comprendre les Résultats

#### Score de Similarité

**Interprétation**:
```
99-100% : Identique ou quasi-identique
95-98%  : Même source, légère compression différente
90-94%  : Même source, compression ou recadrage
85-89%  : Probablement même source, modifications notables
80-84%  : Peut-être duplicata, vérification manuelle recommandée
< 80%   : Probablement pas un duplicata
```

#### Types de Duplicatas Détectés

**1. Duplicata Exact** (100%)
```
video.mp4 = video_copy.mp4
→ Même fichier, nom différent
```

**2. Duplicata Réencodé** (95-99%)
```
video_1080p.mp4 ≈ video_720p.mp4
→ Même source, résolutions différentes
```

**3. Duplicata Modifié** (85-94%)
```
video_original.mp4 ≈ video_recadre.mp4
→ Même source, recadrage ou effet
```

**4. Extrait** (détection de scène)
```
clip_30s.mp4 ⊂ film_2h.mp4
→ Clip trouvé dans film complet
```

---

### 🎓 Scénarios d'Utilisation Réels

#### Scénario 1: Nettoyage de Téléchargements

**Situation**: 500 vidéos téléchargées avec beaucoup de doublons

**Workflow**:
```
1. Mode: Audio-First
2. Seuil: 85%
3. Audio threshold: 0.60
4. Analyser → ~2-3 minutes
5. Trouver ~50 duplicatas
6. Comparer visuellement les paires < 90%
7. Supprimer → Libérer ~20 GB
```

**Temps total**: 15-20 minutes
**Résultat**: 450 vidéos uniques

---

#### Scénario 2: Organisation Bibliothèque Familiale

**Situation**: 2000 vidéos familiales sur 10 ans, beaucoup de copies

**Workflow**:
```
1. Pré-trier par année (200 vidéos/lot)
2. Mode: Audio-First
3. Seuil: 90% (éviter faux positifs sur vidéos similaires)
4. Analyser chaque lot → 10 lots × 1 min = 10 min
5. Vérifier manuellement toutes les paires
6. Garder meilleure qualité (fichier plus gros)
```

**Temps total**: 1-2 heures
**Résultat**: 1600 vidéos uniques, bien organisées

---

#### Scénario 3: Détection d'Extraits Piratés

**Situation**: Trouver clips extraits de vos vidéos originales

**Workflow**:
```
1. Mode: Scene Detection
2. Algorithme: Audio Fingerprinting
3. Vidéo courte: clip suspect
4. Vidéos longues: vos vidéos originales
5. Lancer détection
6. Si trouvé: Vérifier avec Strategy 3 (99% précision)
```

**Temps**: 1-2 minutes par clip
**Résultat**: Position exacte du clip dans l'original

---

#### Scénario 4: Archivage Professionnel

**Situation**: 5000+ vidéos professionnelles, éliminer doublons avant archivage

**Workflow**:
```
1. Mode: Advanced 3-Level
2. Configuration:
   - LSH bands: 20
   - Audio threshold: 0.65
   - Video threshold: 90%
3. Analyser → ~30-45 minutes
4. Trouver ~200 duplicatas
5. Vérifier manuellement paires < 95%
6. Archiver uniquement les originaux
```

**Temps total**: 2-3 heures
**Résultat**: 4800 vidéos uniques archivées
**Gain d'espace**: 15-20% de stockage économisé

---

## Support et Ressources

### Documentation Technique

- **Architecture**: `ARCHITECTURE.md` - Design et structure du code
- **API Reference**: `FUNCTIONS_COMPLETE_REFERENCE.md` - Référence complète des fonctions
- **Error Report**: `ERRORS_AND_PROBLEMS_COMPLETE_REPORT.md` - Problèmes connus et solutions

### Rapporter un Bug

**Avant de rapporter**:
1. Vérifier les logs: `~/.duplicate_finder/logs/duplicate_finder.log`
2. Reproduire le problème
3. Noter la version de l'application

**Informations à inclure**:
```
- Système d'exploitation (macOS/Linux/Windows + version)
- Python version
- Message d'erreur complet
- Étapes pour reproduire
- Logs pertinents
```

**Où rapporter**: GitHub Issues ou contact développeur

### Contribuer

Le projet est open-source! Contributions bienvenues:

- 🐛 Rapporter des bugs
- 💡 Suggérer des fonctionnalités
- 📝 Améliorer la documentation
- 🔧 Proposer du code

---

## Glossaire

**Hash**: Empreinte numérique unique d'une vidéo
**LSH**: Locality-Sensitive Hashing - Technique de filtrage rapide
**Fingerprint**: Signature audio pour comparaison rapide
**DCT**: Discrete Cosine Transform - Analyse de fréquences
**N²**: Nombre de comparaisons (N×N/2 pour N fichiers)
**Worker**: Thread d'exécution parallèle
**Threshold**: Seuil de similarité minimum
**Scene Detection**: Détection d'extraits dans vidéos longues
**Strategy 3**: Algorithme de vérification haute précision

---

## Licence et Crédits

**Duplicate Finder** - VideoFlow Plugin
**Version**: 1.0
**Date**: 2025-12-06

**Technologies utilisées**:
- Python 3.8+
- PyQt6 (Interface graphique)
- OpenCV (Traitement vidéo)
- Librosa (Analyse audio)
- FFmpeg (Extraction audio/vidéo)
- datasketch (LSH)
- imagehash (Hashing d'images)

**Remerciements**:
- FFmpeg project
- OpenCV community
- Librosa developers
- PyQt6 team

---

**Fin du Manuel Utilisateur**

Pour plus d'informations, consulter la documentation technique dans le répertoire du projet.
