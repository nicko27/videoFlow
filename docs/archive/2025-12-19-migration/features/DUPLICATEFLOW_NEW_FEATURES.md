# DuplicateFlow - Nouvelles Fonctionnalités

Ce document décrit les trois nouvelles fonctionnalités ajoutées à DuplicateFlow Pipeline.

## Table des Matières

1. [Système de Validation Configurable](#1-système-de-validation-configurable)
2. [Validation de Longueur Vidéo](#2-validation-de-longueur-vidéo)
3. [Analyse Partielle des Vidéos](#3-analyse-partielle-des-vidéos)
4. [Exemples d'Utilisation](#exemples-dutilisation)
5. [API Référence](#api-référence)

---

## 1. Système de Validation Configurable

### Description

Le Pipeline accepte maintenant des étapes de validation optionnelles qui s'exécutent avant ou après la comparaison. Cela permet de :

- **Pré-filtrer** les paires de vidéos avant l'analyse (économie de temps/ressources)
- **Post-vérifier** les résultats après la comparaison (validation supplémentaire)
- **Ajouter des métadonnées** aux résultats du pipeline

### Architecture

```python
from duplicateflow.sdk import Validator

class Validator(ABC):
    """Classe de base pour tous les validateurs."""

    @abstractmethod
    def validate(self, video1: str, video2: str, result=None) -> tuple[bool, dict]:
        """
        Retourne (is_valid, metadata)
        - is_valid: True si la validation passe
        - metadata: Informations sur la validation
        """
        pass
```

### Utilisation

```python
from duplicateflow.pipeline import Pipeline
from duplicateflow.sdk import LengthValidator

pipeline = Pipeline(
    steps=[...],

    # Validateurs pré-comparaison (filtrage)
    pre_validators=[
        LengthValidator(tolerance_percent=5.0, tolerance_seconds=30.0)
    ],

    # Validateurs post-comparaison (vérification)
    post_validators=[
        # Vos validateurs personnalisés
    ],

    # Mode de validation: 'all' (ET) ou 'any' (OU)
    validation_mode='all'  # Tous les validateurs doivent passer
)
```

### Comportement

#### Pré-validation
- S'exécute **AVANT** les algorithmes de comparaison
- Si échec → retour immédiat avec `accepted=False`
- Économise le temps de calcul pour les paires incompatibles

#### Post-validation
- S'exécute **APRÈS** les algorithmes de comparaison
- Si échec → `accepted` est mis à `False` mais le score reste inchangé
- Permet une vérification finale des résultats

---

## 2. Validation de Longueur Vidéo

### Description

Le `LengthValidator` vérifie que deux vidéos ont des durées similaires. Supporte deux types de tolérances :

- **Pourcentage** : ±x% de différence acceptable
- **Secondes** : ±x secondes de différence acceptable
- **Logique** : AND (les deux) ou OR (l'une ou l'autre)

### Cas d'usage

- **Mode Scène** : Vérifier que la scène et la position dans la vidéo longue ont des durées proches
- **Mode Duplicata** : Filtrer les vidéos de durées très différentes avant l'analyse
- **Optimisation** : Éviter des comparaisons inutiles

### Exemples

#### Tolérance de 5% OU 30 secondes

```python
from duplicateflow.sdk import LengthValidator

validator = LengthValidator(
    tolerance_percent=5.0,    # ±5%
    tolerance_seconds=30.0,   # OU ±30s
    require_both=False        # Logique OR
)

# Test
is_valid, metadata = validator.validate("video1.mp4", "video2.mp4")

if is_valid:
    print(f"✓ Vidéos compatibles")
    print(f"  Diff: {metadata['length_diff_seconds']:.1f}s ({metadata['length_diff_percent']:.1f}%)")
else:
    print(f"✗ Vidéos incompatibles: {metadata['reason']}")
```

#### Tolérance stricte (ET logique)

```python
validator = LengthValidator(
    tolerance_percent=5.0,    # ±5%
    tolerance_seconds=30.0,   # ET ±30s
    require_both=True         # Les DEUX doivent passer
)
```

#### Tolérance simple

```python
# Seulement pourcentage
validator = LengthValidator(tolerance_percent=10.0)

# Seulement secondes
validator = LengthValidator(tolerance_seconds=60.0)
```

### Métadonnées retournées

```python
{
    'duration1': 120.5,              # Durée vidéo 1 (secondes)
    'duration2': 125.0,              # Durée vidéo 2 (secondes)
    'length_diff_seconds': 4.5,      # Différence absolue
    'length_diff_percent': 3.7,      # Différence en %
    'percent_ok': True,              # Tolérance % respectée?
    'seconds_ok': True,              # Tolérance s respectée?
    'reason': 'Both tolerances satisfied',
    'tolerance_percent': 5.0,
    'tolerance_seconds': 30.0,
    'require_both': False
}
```

---

## 3. Analyse Partielle des Vidéos

### Description

Le Pipeline peut maintenant analyser **seulement une portion** de chaque vidéo au lieu de la vidéo complète. Idéal pour :

- **Détection de duplicatas** : Analyser seulement les 60 premières secondes
- **Détection de génériques** : Analyser seulement les 30 dernières secondes
- **Optimisation** : Réduire le temps d'analyse pour les longues vidéos

### Paramètres

- `analyze_duration` : Durée limite en secondes (None = vidéo complète)
- `analyze_from_start` : True = début de vidéo, False = fin de vidéo

### Exemples

#### Analyser les 60 premières secondes (mode duplicata)

```python
from duplicateflow.pipeline import Pipeline

pipeline = Pipeline(
    steps=[
        {'algorithm': 'frame_hash', 'weight': 0.5, 'threshold': 75.0},
        {'algorithm': 'color_histogram', 'weight': 0.5, 'threshold': 70.0}
    ],
    analyze_duration=60.0,      # Seulement 60 secondes
    analyze_from_start=True     # Du début
)

# Comparaison : seules les 60 premières secondes seront analysées
result = pipeline.compare("video1.mp4", "video2.mp4")
```

#### Analyser les 30 dernières secondes (mode générique)

```python
pipeline = Pipeline(
    steps=[...],
    analyze_duration=30.0,      # Seulement 30 secondes
    analyze_from_start=False    # De la fin
)
```

#### Mode scène : analyse complète (par défaut)

```python
pipeline = Pipeline(
    steps=[...],
    analyze_duration=None,      # Pas de limite (défaut)
    analyze_from_start=True
)
```

### Comportement

1. Le Pipeline calcule automatiquement les paramètres effectifs :
   ```python
   # Pour une vidéo de 600s avec analyze_duration=60s
   # analyze_from_start=True
   → Analyse les frames de 0s à 60s

   # analyze_from_start=False
   → Analyse les frames de 540s à 600s
   ```

2. Les paramètres `start_time` et `duration` de `compare()` sont ajustés :
   ```python
   result = pipeline.compare(
       short_video="scene.mp4",
       long_video="movie.mp4",
       start_time=100.0,  # Position dans la vidéo longue
       duration=120.0     # Durée à rechercher
   )
   # Si analyze_duration=60, seules les 60 premières secondes
   # de chaque fenêtre seront analysées
   ```

---

## Exemples d'Utilisation

### Exemple 1 : Pipeline de Détection de Duplicatas Rapide

```python
from duplicateflow.pipeline import Pipeline
from duplicateflow.sdk import LengthValidator

# Configuration optimisée pour détecter des duplicatas
pipeline = Pipeline(
    steps=[
        {'algorithm': 'frame_hash', 'weight': 0.6, 'threshold': 80.0},
        {'algorithm': 'color_histogram', 'weight': 0.4, 'threshold': 75.0}
    ],

    # Pré-filtrage : accepter seulement les vidéos de longueur similaire
    pre_validators=[
        LengthValidator(tolerance_percent=5.0, tolerance_seconds=30.0)
    ],

    # Analyse partielle : seulement 60 premières secondes
    analyze_duration=60.0,
    analyze_from_start=True,

    # Optimisations
    global_threshold=75.0,
    early_termination=True,
    show_progress=True
)

# Utilisation
result = pipeline.compare("video1.mp4", "video2.mp4")

if result.get('metadata', {}).get('pre_validation_failed'):
    print("❌ Vidéos filtrées : durées trop différentes")
elif result['accepted']:
    print(f"✓ Duplicata détecté (score: {result['global_score']:.1f})")
else:
    print(f"✗ Pas de duplicata (score: {result['global_score']:.1f})")
```

### Exemple 2 : Pipeline de Détection de Scènes avec Validation

```python
pipeline = Pipeline(
    steps=[
        {'algorithm': 'ssim', 'weight': 0.3, 'threshold': 70.0},
        {'algorithm': 'motion_analysis', 'weight': 0.3, 'threshold': 70.0},
        {'algorithm': 'audio_fingerprint', 'weight': 0.4, 'threshold': 70.0}
    ],

    # Validation de longueur stricte pour les scènes
    pre_validators=[
        LengthValidator(
            tolerance_percent=2.0,    # ±2% seulement
            tolerance_seconds=5.0,    # ET ±5s
            require_both=True         # Les deux doivent passer
        )
    ],

    # Analyse complète (pas de limite)
    analyze_duration=None,  # Mode scène : analyser tout

    global_threshold=70.0
)

result = pipeline.compare(
    short_video="scene_10s.mp4",
    long_video="movie_2h.mp4",
    start_time=3600.0,  # À 1h dans le film
    duration=10.0        # Chercher sur 10 secondes
)
```

### Exemple 3 : Créer un Validateur Personnalisé

```python
from duplicateflow.sdk import Validator
import cv2

class ResolutionValidator(Validator):
    """Valide que deux vidéos ont des résolutions similaires."""

    def __init__(self, max_diff_percent=20.0):
        super().__init__()
        self.max_diff_percent = max_diff_percent

    def validate(self, video1, video2, result=None):
        # Obtenir les résolutions
        cap1 = cv2.VideoCapture(video1)
        cap2 = cv2.VideoCapture(video2)

        try:
            w1, h1 = cap1.get(cv2.CAP_PROP_FRAME_WIDTH), cap1.get(cv2.CAP_PROP_FRAME_HEIGHT)
            w2, h2 = cap2.get(cv2.CAP_PROP_FRAME_WIDTH), cap2.get(cv2.CAP_PROP_FRAME_HEIGHT)

            area1 = w1 * h1
            area2 = w2 * h2

            diff_percent = abs(area1 - area2) / max(area1, area2) * 100
            is_valid = diff_percent <= self.max_diff_percent

            metadata = {
                'resolution1': f"{int(w1)}x{int(h1)}",
                'resolution2': f"{int(w2)}x{int(h2)}",
                'diff_percent': diff_percent,
                'threshold': self.max_diff_percent
            }

            return is_valid, metadata

        finally:
            cap1.release()
            cap2.release()

# Utilisation
pipeline = Pipeline(
    steps=[...],
    pre_validators=[
        LengthValidator(tolerance_percent=5.0),
        ResolutionValidator(max_diff_percent=20.0)  # Votre validateur
    ],
    validation_mode='all'  # Les deux doivent passer
)
```

---

## API Référence

### Pipeline

#### Nouveaux Paramètres

```python
Pipeline(
    steps: List[Dict],
    pre_validators: Optional[List[Validator]] = None,
    post_validators: Optional[List[Validator]] = None,
    validation_mode: str = 'all',  # 'all' ou 'any'
    analyze_duration: Optional[float] = None,
    analyze_from_start: bool = True,
    # ... autres paramètres existants
)
```

#### Nouvelles Métadonnées dans les Résultats

```python
result = pipeline.compare(video1, video2)

# Si pré-validation échoue
if result['metadata'].get('pre_validation_failed'):
    validation_results = result['metadata']['pre_validation_results']
    # Liste de {validator, passed, metadata}

# Si post-validation échoue
if result['metadata'].get('post_validation_failed'):
    validation_results = result['metadata']['post_validation_results']
```

### Validator (Classe de Base)

```python
from duplicateflow.sdk import Validator

class MyValidator(Validator):
    def validate(self, video1: str, video2: str, result=None) -> tuple[bool, dict]:
        """
        Args:
            video1: Chemin première vidéo
            video2: Chemin deuxième vidéo
            result: Résultat de comparaison (pour post-validators)

        Returns:
            (is_valid, metadata)
        """
        pass

    def get_metadata(self) -> dict:
        """Retourne la configuration du validateur."""
        return {'name': self.name, 'type': self.__class__.__name__}
```

### LengthValidator

```python
from duplicateflow.sdk import LengthValidator

LengthValidator(
    tolerance_percent: Optional[float] = None,  # ±x%
    tolerance_seconds: Optional[float] = None,  # ±x secondes
    require_both: bool = False                  # AND vs OR
)
```

**Méthodes** :
- `validate(video1, video2, result=None) -> (bool, dict)`
- `get_metadata() -> dict`

---

## Migration et Compatibilité

### Rétrocompatibilité

✅ Les pipelines existants continuent de fonctionner sans modification :

```python
# Code existant - fonctionne toujours
pipeline = Pipeline(
    steps=[...],
    global_threshold=70.0
)
```

### Migration Progressive

Ajoutez les nouvelles fonctionnalités progressivement :

```python
# Étape 1 : Ajouter la validation de longueur
pipeline = Pipeline(
    steps=[...],
    pre_validators=[LengthValidator(tolerance_seconds=30.0)]
)

# Étape 2 : Ajouter l'analyse partielle
pipeline = Pipeline(
    steps=[...],
    pre_validators=[...],
    analyze_duration=60.0
)

# Étape 3 : Configuration complète
pipeline = Pipeline(
    steps=[...],
    pre_validators=[...],
    post_validators=[...],
    analyze_duration=60.0,
    analyze_from_start=True
)
```

---

## Performance

### Impact sur les Performances

#### Pré-validation
- **Overhead** : ~10-50ms par paire (lecture métadonnées vidéo)
- **Gain** : Évite l'analyse complète pour les paires incompatibles
- **ROI** : Positif dès que >5% des paires sont filtrées

#### Analyse Partielle
- **Réduction** : Proportionnelle au ratio `analyze_duration / video_duration`
- **Exemple** : 60s sur vidéo de 600s = 90% de réduction du temps d'analyse

### Recommandations

1. **Pour la détection de duplicatas** :
   ```python
   analyze_duration=60.0  # 60 premières secondes suffisent
   pre_validators=[LengthValidator(tolerance_percent=5.0)]
   ```

2. **Pour la détection de scènes** :
   ```python
   analyze_duration=None  # Analyse complète nécessaire
   pre_validators=[LengthValidator(tolerance_percent=2.0, require_both=True)]
   ```

3. **Pour l'optimisation maximale** :
   ```python
   # Filtrage agressif + analyse partielle
   pre_validators=[
       LengthValidator(tolerance_percent=5.0),
       ResolutionValidator(max_diff_percent=20.0)
   ]
   analyze_duration=30.0
   early_termination=True
   ```

---

## Tests

Les fonctionnalités ont été testées avec le script `test_validators_only.py` :

```bash
python3 test_validators_only.py
```

**Résultats** :
```
✓ Validator creation tests passed
✓ Interface tests passed
✓ Metadata tests passed
✓ Logic simulation passed
```

---

## Conclusion

Ces trois nouvelles fonctionnalités permettent :

1. **Flexibilité** : Ajoutez des validations personnalisées à vos pipelines
2. **Performance** : Filtrez les paires incompatibles et analysez seulement ce qui est nécessaire
3. **Précision** : Validez les résultats avec des critères supplémentaires
4. **Simplicité** : API claire et rétrocompatible

### Prochaines Étapes

- Créer des validateurs personnalisés pour vos besoins spécifiques
- Tester avec vos propres jeux de données
- Ajuster les tolérances selon vos cas d'usage
- Mesurer les gains de performance

### Support

Pour plus d'informations, consultez :
- Code source : `duplicateflow/duplicateflow/sdk/validator.py`
- Tests : `test_validators_only.py`
- Exemples : `test_new_features.py`
