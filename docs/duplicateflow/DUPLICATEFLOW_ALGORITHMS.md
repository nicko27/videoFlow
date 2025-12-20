# DuplicateFlow - Les 14 Algorithmes

## Table des Matieres

1. [Vue d'ensemble](#vue-densemble)
2. [Tableau comparatif complet](#tableau-comparatif-complet)
3. [Algorithmes par categorie](#algorithmes-par-catégorie)
4. [Fiches detaillees](#fiches-détaillées)
5. [Guide de selection](#guide-de-sélection)

---

## Vue d'ensemble

DuplicateFlow integre **14 algorithmes** de detection video, chacun specialise dans un type specifique de similarite:

### Categories

| Categorie | Algorithmes | Focus |
|-----------|-------------|-------|
| **Perceptual** | frame_hash, ssim | Similarite visuelle perceptuelle |
| **Statistical** | color_histogram, color_moments, dct_coefficients | Distributions statistiques |
| **Temporal** | motion_analysis, optical_flow | Patterns de mouvement |
| **Structural** | edge_pattern, hog_descriptor, feature_matching, template_matching | Structure geometrique |
| **Audio** | audio_fingerprint, audio_spectrum | Analyse audio |
| **Hybrid** | subsequence_detection | Multi-modal (video + audio) |

### Modes de fonctionnement

Chaque algorithme peut fonctionner en 2 modes:

1. **Mode Fingerprint** (extraction/indexation):
   - `extract_features(video_path)` → features compactes
   - `compare_features(feat1, feat2)` → similarity rapide
   - Ideal pour N-to-N avec cache

2. **Mode Direct** (comparaison immediate):
   - `compare(video1, video2)` → similarity directe
   - Avec sliding window pour trouver best match
   - Ideal pour 1-to-1 ou petits datasets

---

## Tableau comparatif complet

| Algorithme | Categorie | Vitesse | Threshold | Parametres cles | Cas d'usage |
|------------|-----------|---------|-----------|-----------------|-------------|
| **frame_hash** | Perceptual | Fast | 80 | hash_method (pHash/dHash/aHash), num_samples | Duplicatas visuels avec variations mineures |
| **color_histogram** | Statistical | Fast | 70 | bins (32,32,32), num_samples | Scenes avec palettes couleur caracteristiques |
| **color_moments** | Statistical | Fast | 75 | num_samples | Distribution globale des couleurs (rapide) |
| **ssim** | Perceptual | Medium | 0.70 | sample_interval, num_samples | Similarite perceptuelle (luminance/contraste) |
| **motion_analysis** | Temporal | Medium | 70 | num_samples | Patterns de mouvement caracteristiques |
| **optical_flow** | Temporal | Slow | 70 | method (farneback), num_samples | Mouvement dense et complexe |
| **dct_coefficients** | Statistical | Fast | 70 | num_coeffs | Caracteristiques frequentielles basses |
| **edge_pattern** | Structural | Fast | 70 | canny_low, canny_high, grid_size | Motifs structurels (contours) |
| **hog_descriptor** | Structural | Medium | 70 | cell_size, block_size, nbins | Gradients et structure des scenes |
| **feature_matching** | Structural | Medium | 30 | detector (ORB/AKAZE/SIFT), max_features | Points d'interet geometriques |
| **template_matching** | Structural | Medium | 80 | num_templates, template_size | Correspondances visuelles exactes |
| **audio_fingerprint** | Audio | Fast | 200 | sr, n_fft, hop, fanout | Fingerprinting Shazam-style (scalable millions) |
| **audio_spectrum** | Audio | Medium | 70 | num_samples, sample_duration, n_fft | Caracteristiques spectrales audio |
| **subsequence_detection** | Hybrid | Slow | 70 | signature_points, hash_weight, motion_weight | Detection d'extraits video |

### Legende

**Vitesse**:
- **Fast**: < 5s pour 1min de video
- **Medium**: 5-15s pour 1min de video
- **Slow**: > 15s pour 1min de video

**Threshold**:
- Valeur par defaut recommandee
- Pour audio_fingerprint: nombre de votes (pas percentage)
- Pour ssim: echelle 0-1 (pas 0-100)

---

## Algorithmes par categorie

### 1. Perceptual (Similarite visuelle)

#### frame_hash
- **Principe**: Hash perceptuels compacts (pHash, dHash, aHash)
- **Robustesse**: Resilient aux variations mineures (compression, resize, brightness)
- **Performance**: Tres rapide (hash = 64 bits)

#### ssim
- **Principe**: Structural Similarity Index
- **Robustesse**: Considere luminance + contraste + structure
- **Performance**: Moyen (calcul sur pixels)

### 2. Statistical (Distributions)

#### color_histogram
- **Principe**: Histogrammes HSV 3D
- **Robustesse**: Invariant a la position, sensible aux couleurs
- **Performance**: Rapide (histogramme = vecteur compact)

#### color_moments
- **Principe**: Moments statistiques (moyenne, std, skewness)
- **Robustesse**: Distribution globale tres compacte (9 valeurs)
- **Performance**: Tres rapide

#### dct_coefficients
- **Principe**: Transformee en Cosinus Discrete (DCT)
- **Robustesse**: Capture frequences basses (essence visuelle)
- **Performance**: Rapide

### 3. Temporal (Mouvement)

#### motion_analysis
- **Principe**: Differences frame-a-frame (absdiff)
- **Robustesse**: Capture patterns de mouvement simples
- **Performance**: Moyen

#### optical_flow
- **Principe**: Flux optique dense (Farneback)
- **Robustesse**: Analyse mouvement pixel-par-pixel
- **Performance**: Lent mais precis

### 4. Structural (Geometrie)

#### edge_pattern
- **Principe**: Detection de contours Canny + grille
- **Robustesse**: Patterns structurels (formes, objets)
- **Performance**: Rapide

#### hog_descriptor
- **Principe**: Histogrammes de gradients orientes
- **Robustesse**: Structure geometrique robuste
- **Performance**: Moyen

#### feature_matching
- **Principe**: Keypoints + descripteurs (ORB/AKAZE/SIFT)
- **Robustesse**: Invariant rotation/echelle/perspective
- **Performance**: Moyen

#### template_matching
- **Principe**: Correlation croisee normalisee
- **Robustesse**: Detection de templates exacts
- **Performance**: Moyen

### 5. Audio

#### audio_fingerprint
- **Principe**: Acoustic fingerprinting Shazam-style
- **Robustesse**: Scalable a millions de videos (LSH)
- **Performance**: Rapide (hashing)

#### audio_spectrum
- **Principe**: Spectrogrammes FFT multi-bandes
- **Robustesse**: Caracteristiques frequentielles audio
- **Performance**: Moyen

### 6. Hybrid

#### subsequence_detection
- **Principe**: Combine frame_hash + motion_analysis
- **Robustesse**: Detection d'extraits (intro/credits/scenes)
- **Performance**: Lent (multi-modal)

---

## Fiches detaillees

### 1. frame_hash

**Nom complet**: Frame Hash (pHash/dHash/aHash)
**Categorie**: Perceptual
**Vitesse**: Fast
**Threshold par defaut**: 80.0

#### Description technique

Calcule des hash perceptuels compacts pour chaque frame:
- **pHash** (Perceptual Hash): DCT 8×8 + seuillage (le plus precis)
- **dHash** (Difference Hash): Gradient horizontal (rapide, precis)
- **aHash** (Average Hash): Seuillage par moyenne (le plus rapide)

#### Parametres

```python
{
    'threshold': 80.0,           # Seuil de similarite (0-100)
    'hash_method': 'pHash',      # pHash | dHash | aHash
    'num_samples': 8,            # Nombre de frames a hasher
    'sample_positions': [1, 5, 10, 20, 30, 50, 70, 100],  # Positions fixes (secondes)
    'search_step': 3.0,          # Pas de fenetre glissante
    'max_windows': 200           # Nombre max de fenetres
}
```

#### Algorithme

1. Extraire N frames de la video courte (positions fixes ou uniformes)
2. Pour chaque frame:
   - Convertir en grayscale
   - Appliquer hash method (pHash/dHash/aHash)
   - Obtenir hash binaire (64 bits pour pHash)
3. Fenetre glissante sur video longue:
   - Extraire frames aux memes offsets relatifs
   - Hasher chaque frame
   - Calculer distance de Hamming avec frames courtes
   - Moyenner les distances
4. Retourner best match (plus petite distance)

#### Complexite

- **Extraction**: O(N × W × H) où N = nombre de frames
- **Comparaison**: O(hash_size) = O(64) per frame pair
- **Total**: O(N × windows) ~ O(N × video_duration / search_step)

#### Cas d'usage

- Duplicatas visuels exacts ou quasi-exacts
- Videos re-encodees (compression, resize)
- Videos avec ajustements legers (brightness, contrast)

**Exemple**:
```python
algo = get_algorithm('frame_hash')
algo.configure(
    threshold=80.0,
    hash_method='pHash',
    num_samples=8
)
result = algo.compare('short.mp4', 'long.mp4')
# => similarity: 0.92, accepted: True
```

---

### 2. audio_fingerprint

**Nom complet**: Audio Fingerprint (Shazam-style)
**Categorie**: Audio
**Vitesse**: Fast (indexation + recherche)
**Threshold par defaut**: 200 (votes)

#### Description technique

Acoustic fingerprinting inspire de Shazam pour matching audio scalable:

1. **Spectrogram**: STFT pour obtenir representation temps-frequence
2. **Peak detection**: Detecter pics spectraux (local maxima)
3. **Landmark hashing**: Construire paires de pics (anchor + target)
4. **Hash format**: (freq1, freq2, time_delta) → 32-bit hash
5. **Matching**: Voter sur time offsets pour trouver correspondances

#### Parametres

```python
{
    'threshold': 200,            # Minimum de votes pour accepter match
    'sr': 11025,                 # Sample rate audio (Hz)
    'n_fft': 4096,               # Taille FFT
    'hop': 512,                  # Hop length pour STFT
    'freq_max_hz': 5000.0,       # Frequence max a considerer
    'neighborhood_time': 12,     # Voisinage temporel pour peaks
    'neighborhood_freq': 8,      # Voisinage frequentiel pour peaks
    'amp_percentile': 75.0,      # Percentile amplitude pour peaks
    'max_peaks_per_second': 25,  # Densite max de peaks
    'fanout': 8,                 # Nombre de paires par anchor peak
    'dt_min': 0.5,               # Delta temps min pour paires (s)
    'dt_max': 3.0,               # Delta temps max pour paires (s)
    'freq_bin_quant': 2,         # Quantization bins de frequence
    'time_quant': 20             # Quantization temps (ms)
}
```

#### Algorithme

**Phase 1: Extraction** (pour chaque video)
```
1. Extraire audio mono via ffmpeg
2. Normaliser amplitude
3. Calculer STFT (spectrogram)
4. Detecter peaks spectraux:
   - Local maxima dans voisinage temps-frequence
   - Filtrer par amplitude (percentile)
   - Limiter densite (max_peaks_per_second)
5. Construire landmark hashes:
   - Pour chaque anchor peak:
     - Pairer avec 'fanout' peaks suivants dans [dt_min, dt_max]
     - Hash = (freq1_quantized, freq2_quantized, dt_quantized)
     - Stocker: hash → liste de timestamps
6. Retourner dict: {hash: [t1, t2, ...]}
```

**Phase 2: Matching** (comparer 2 videos)
```
1. Recuperer fingerprints des 2 videos
2. Trouver hashes communs
3. Pour chaque hash commun:
   - Pour chaque paire de timestamps (t1 dans video1, t2 dans video2):
     - Voter pour offset: offset = t2 - t1
4. Compter votes par offset
5. Best match = offset avec le plus de votes
6. Retourner: (best_offset, votes, top_offsets)
```

#### Complexite

- **Extraction**: O(audio_duration × sr)
- **Peak detection**: O(spec_size × neighborhood)
- **Hashing**: O(num_peaks × fanout)
- **Matching**: O(|common_hashes| × |timestamps_per_hash|²)
  - Avec limitation: O(|common_hashes| × 50²) max

#### Scalabilite

**Sans LSH** (brute force):
- O(N²) comparisons
- Exemple: 1000 videos → 499,500 comparisons
- Temps: ~30 min (avec cache)

**Avec LSH** (Locality-Sensitive Hashing):
- O(N × C) où C = candidats moyens (~10-50)
- Exemple: 1000 videos → ~10,000-50,000 comparisons
- Temps: ~8 min (10-50× acceleration)

#### Cas d'usage

- **N-to-N detection** a grande echelle (millions de videos)
- Duplicatas audio meme avec video differente
- Videos re-encodees avec audio preserve
- Detection robuste au bruit

**Exemple**:
```python
algo = get_algorithm('audio_fingerprint')
algo.configure(threshold=200, sr=11025)

# Mode 1: Compare directement
result = algo.compare('video1.mp4', 'video2.mp4')
# => similarity: 450 (votes), accepted: True

# Mode 2: Avec indexation pour N-to-N
from duplicateflow.processing import FingerprintIndex

index = FingerprintIndex()
index.index_directory('/videos', algorithm=algo, workers=8)
matches = index.find_all_matches(min_votes=200)
```

---

### 3. color_histogram

**Nom complet**: Color Histogram (HSV)
**Categorie**: Statistical
**Vitesse**: Fast
**Threshold par defaut**: 70.0

#### Description technique

Compare distributions de couleur via histogrammes HSV 3D:
- **H** (Hue): Teinte (0-180 degrees)
- **S** (Saturation): Saturation (0-255)
- **V** (Value): Luminosite (0-255)

#### Parametres

```python
{
    'threshold': 70.0,           # Seuil de similarite (0-100)
    'bins': (32, 32, 32),        # Bins pour H, S, V
    'num_samples': 5,            # Nombre de frames a echantillonner
    'search_step': 3.0,          # Pas de fenetre glissante
    'max_windows': 200,          # Nombre max de fenetres
    'resize': (320, 240)         # Taille de resize pour calcul
}
```

#### Algorithme

1. Extraire N frames de la video courte
2. Pour chaque frame:
   - Convertir BGR → HSV
   - Calculer histogramme 3D (bins H×S×V)
   - Normaliser l'histogramme
3. Fenetre glissante sur video longue:
   - Extraire frames aux memes offsets
   - Calculer histogrammes
   - Comparer avec correlation (cv2.compareHist)
4. Retourner best match

#### Methodes de comparaison

OpenCV offre plusieurs metriques:
- **CORREL** (utilise ici): Correlation [-1, 1]
- **CHISQR**: Chi-square
- **INTERSECT**: Intersection
- **BHATTACHARYYA**: Distance de Bhattacharyya

#### Cas d'usage

- Scenes avec palettes couleur caracteristiques (ciels, paysages, eclairages)
- Invariant a la position des objets
- Sensible aux changements de couleur

**Exemple**:
```python
algo = get_algorithm('color_histogram')
algo.configure(
    threshold=70.0,
    bins=(32, 32, 32),
    num_samples=5
)
result = algo.compare('short.mp4', 'long.mp4')
```

---

### 4. ssim

**Nom complet**: Structural Similarity Index
**Categorie**: Perceptual
**Vitesse**: Medium
**Threshold par defaut**: 0.70 (echelle 0-1)

#### Description technique

SSIM mesure similarite perceptuelle en considerant 3 aspects:
- **Luminance**: Moyenne des pixels
- **Contraste**: Variance des pixels
- **Structure**: Correlation des pixels

Formule: SSIM(x, y) = [l(x,y)]^α × [c(x,y)]^β × [s(x,y)]^γ

Typiquement: α = β = γ = 1

#### Parametres

```python
{
    'threshold': 0.70,           # Seuil SSIM (0-1, pas 0-100!)
    'sample_interval': 5.0,      # Intervalle entre samples (s)
    'num_samples': None,         # Nombre de samples (None = auto)
    'search_step': 3.0,          # Pas de fenetre glissante
    'max_windows': 200,          # Nombre max de fenetres
    'resize': (320, 240)         # Taille de resize
}
```

#### Algorithme

1. Calculer num_samples automatiquement:
   - num_samples = duration / sample_interval
   - Clamp entre 3 et 150 samples
2. Extraire frames aux positions calculees
3. Fenetre glissante sur video longue:
   - Pour chaque position:
     - Extraire frames
     - Calculer SSIM (via scikit-image)
     - Moyenner les SSIM scores
4. Retourner best match

#### Interpretation SSIM

| SSIM | Interpretation |
|------|----------------|
| 1.0 | Identique |
| 0.9-1.0 | Tres similaire |
| 0.7-0.9 | Similaire |
| 0.5-0.7 | Moderement similaire |
| < 0.5 | Different |

#### Cas d'usage

- Similarite perceptuelle (humain-like)
- Videos avec meme luminance/contraste
- Detection de scenes visuellement similaires

**Dependances**: `scikit-image>=0.21.0`

**Exemple**:
```python
algo = get_algorithm('ssim')
algo.configure(
    threshold=0.70,              # Note: 0-1, pas 0-100!
    sample_interval=5.0
)
result = algo.compare('short.mp4', 'long.mp4')
# => similarity: 0.85 (0-1 scale)
```

---

### 5. motion_analysis

**Nom complet**: Motion Analysis (Frame Differences)
**Categorie**: Temporal
**Vitesse**: Medium
**Threshold par defaut**: 70.0

#### Description technique

Analyse patterns de mouvement via differences frame-a-frame:
- Calculer absdiff entre frames consecutives
- Comparer patterns via correlation

#### Parametres

```python
{
    'threshold': 70.0,
    'num_samples': 5,
    'search_step': 3.0,
    'max_windows': 200
}
```

#### Cas d'usage

- Scenes avec mouvements caracteristiques (danse, sport, action)
- Complement aux methodes visuelles pures

---

### 6. optical_flow

**Nom complet**: Optical Flow (Farneback)
**Categorie**: Temporal
**Vitesse**: Slow
**Threshold par defaut**: 70.0

#### Description technique

Calcule flux optique dense entre frames avec algorithme de Farneback:
- Flux optique = vecteur de mouvement pour chaque pixel
- Extraction: magnitude moyenne + variance

#### Parametres

```python
{
    'threshold': 70.0,
    'num_samples': 5,
    'method': 'farneback'        # Seule methode supportee
}
```

#### Cas d'usage

- Mouvements complexes et denses
- Analyse fine de trajectoires
- Complement a motion_analysis (plus precis mais plus lent)

---

### 7. dct_coefficients

**Nom complet**: DCT Coefficients
**Categorie**: Statistical
**Vitesse**: Fast
**Threshold par defaut**: 70.0

#### Description technique

Transformee en Cosinus Discrete (DCT) pour capturer frequences basses:
- DCT 2D sur frame grayscale
- Extraire coefficients basses frequences (essence visuelle)
- Comparer via similarite cosinus

#### Parametres

```python
{
    'threshold': 70.0,
    'num_coeffs': 64             # Nombre de coefficients a garder
}
```

#### Cas d'usage

- Caracteristiques frequentielles
- Complement a frame_hash
- Rapide et compact

---

### 8. edge_pattern

**Nom complet**: Edge Pattern (Canny + Grid)
**Categorie**: Structural
**Vitesse**: Fast
**Threshold par defaut**: 70.0

#### Description technique

Detection de contours Canny + analyse par grille:
- Canny edge detection (low/high thresholds)
- Division en grille NxN
- Densite de contours par cellule

#### Parametres

```python
{
    'threshold': 70.0,
    'canny_low': 50,
    'canny_high': 150,
    'grid_size': (8, 8),
    'num_samples': 5
}
```

#### Cas d'usage

- Patterns structurels (formes, objets)
- Scenes avec contours caracteristiques

---

### 9. hog_descriptor

**Nom complet**: Histogram of Oriented Gradients
**Categorie**: Structural
**Vitesse**: Medium
**Threshold par defaut**: 70.0

#### Description technique

HOG capture gradients orientes:
- Division en cellules
- Histogramme de gradients par cellule
- Normalisation par blocs

#### Parametres

```python
{
    'threshold': 70.0,
    'cell_size': (8, 8),
    'block_size': (2, 2),
    'nbins': 9
}
```

#### Cas d'usage

- Structure geometrique robuste
- Detection d'objets/formes

---

### 10. feature_matching

**Nom complet**: Feature Matching (ORB/AKAZE/SIFT)
**Categorie**: Structural
**Vitesse**: Medium
**Threshold par defaut**: 30.0

#### Description technique

Detection de keypoints + matching:
- Detecteurs: ORB (rapide), AKAZE (equilibre), SIFT (precis)
- Descripteurs par keypoint
- Matching avec BFMatcher ou FLANN

#### Parametres

```python
{
    'threshold': 30.0,           # % de matches requis
    'detector': 'ORB',           # ORB | AKAZE | SIFT
    'max_features': 500
}
```

#### Cas d'usage

- Invariant rotation/echelle/perspective
- Correspondances geometriques robustes

---

### 11. template_matching

**Nom complet**: Template Matching (Normalized Cross-Correlation)
**Categorie**: Structural
**Vitesse**: Medium
**Threshold par defaut**: 80.0

#### Description technique

Correlation croisee normalisee:
- Extraction de templates de la video courte
- Recherche dans video longue via cv2.matchTemplate

#### Parametres

```python
{
    'threshold': 80.0,
    'num_templates': 5,
    'template_size': (64, 64)
}
```

#### Cas d'usage

- Detection de templates exacts
- Logos, watermarks, UI elements

---

### 12. audio_spectrum

**Nom complet**: Audio Spectrum (FFT)
**Categorie**: Audio
**Vitesse**: Medium
**Threshold par defaut**: 70.0

#### Description technique

Analyse spectrale audio via FFT:
- Extraction de samples audio
- FFT pour obtenir spectre frequentiel
- Comparison via correlation

#### Parametres

```python
{
    'threshold': 70.0,
    'num_samples': 10,
    'sample_duration': 2.0,
    'n_fft': 2048
}
```

#### Cas d'usage

- Caracteristiques spectrales audio
- Complement a audio_fingerprint (plus simple)

---

### 13. color_moments

**Nom complet**: Color Moments
**Categorie**: Statistical
**Vitesse**: Fast
**Threshold par defaut**: 75.0

#### Description technique

Moments statistiques des canaux couleur:
- Moyenne, ecart-type, skewness pour H, S, V
- 9 valeurs totales (3 moments × 3 canaux)

#### Parametres

```python
{
    'threshold': 75.0,
    'num_samples': 5
}
```

#### Cas d'usage

- Distribution globale compacte
- Plus rapide que histogrammes complets

---

### 14. subsequence_detection

**Nom complet**: Subsequence Detection
**Categorie**: Hybrid
**Vitesse**: Slow
**Threshold par defaut**: 70.0

#### Description technique

Combine frame_hash + motion_analysis:
- Signatures de debut/milieu/fin
- Recherche multi-modal

#### Parametres

```python
{
    'threshold': 70.0,
    'signature_points': 3,
    'hash_weight': 0.6,
    'motion_weight': 0.4
}
```

#### Cas d'usage

- Detection d'extraits (intro/credits)
- Videos courtes dans videos longues

---

## Guide de selection

### Par cas d'usage

| Besoin | Algorithmes recommandes |
|--------|-------------------------|
| **Duplicatas exacts** | frame_hash (pHash), color_histogram |
| **Duplicatas re-encodes** | frame_hash, audio_fingerprint |
| **Scenes similaires** | ssim, color_histogram, dct_coefficients |
| **Mouvements caracteristiques** | motion_analysis, optical_flow |
| **Structure geometrique** | hog_descriptor, feature_matching, edge_pattern |
| **Audio matching** | audio_fingerprint (scalable), audio_spectrum |
| **Extraits/sous-sequences** | subsequence_detection |
| **N-to-N grande echelle** | audio_fingerprint + LSH |

### Par contrainte de vitesse

**Fast** (< 5s/min):
- frame_hash
- color_histogram
- color_moments
- dct_coefficients
- edge_pattern
- audio_fingerprint (avec index)

**Medium** (5-15s/min):
- ssim
- motion_analysis
- hog_descriptor
- feature_matching
- template_matching
- audio_spectrum

**Slow** (> 15s/min):
- optical_flow
- subsequence_detection

### Par precision

**Tres haute precision** (> 90%):
- ssim (0.90+ = tres similaire)
- frame_hash (pHash) (90+)
- audio_fingerprint (avec LSH, votes > 500)

**Haute precision** (80-90%):
- color_histogram
- hog_descriptor
- template_matching

**Precision moderee** (70-80%):
- color_moments
- dct_coefficients
- motion_analysis
- feature_matching

---

## Conclusion

Les 14 algorithmes de DuplicateFlow offrent:
- **Diversite**: 6 categories (perceptual, statistical, temporal, structural, audio, hybrid)
- **Flexibilite**: Mode fingerprint ou direct
- **Performance**: Fast → Slow selon precision requise
- **Scalabilite**: audio_fingerprint + LSH pour millions de videos

**Next**: Voir [DUPLICATEFLOW_PRESETS.md](DUPLICATEFLOW_PRESETS.md) pour les 12 presets pre-configures.
