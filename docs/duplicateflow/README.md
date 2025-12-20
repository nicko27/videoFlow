# DuplicateFlow - Documentation Complete

Base de connaissances exhaustive pour DuplicateFlow.

## Documents disponibles

### Architecture & Algorithmes
1. **[DUPLICATEFLOW_ARCHITECTURE.md](DUPLICATEFLOW_ARCHITECTURE.md)** - Architecture complete du systeme
   - Structure des 49 modules Python
   - Diagramme des dependances
   - Points d'entree (DetectionEngine, Pipeline, Algorithm)
   - Cycle de vie d'une detection
   - Patterns architecturaux (Registry, Strategy, Composite, Cache, LSH)

2. **[DUPLICATEFLOW_ALGORITHMS.md](DUPLICATEFLOW_ALGORITHMS.md)** - Les 14 algorithmes en detail
   - Fiches techniques completes
   - Parametres et configurations
   - Cas d'usage et performance
   - Tableau comparatif complet
   - Guide de selection

### Guides de reference (a venir)
3. **DUPLICATEFLOW_PRESETS.md** - Les 12 presets pre-configures
4. **DUPLICATEFLOW_API_REFERENCE.md** - API complete
5. **DUPLICATEFLOW_INTEGRATION.md** - Integration avec VideoFlow
6. **DUPLICATEFLOW_LSH.md** - Locality-Sensitive Hashing
7. **DUPLICATEFLOW_OPTIMIZATIONS.md** - Validators & Partial Analysis
8. **DUPLICATEFLOW_EXAMPLES.md** - 10 exemples concrets
9. **DUPLICATEFLOW_MIGRATION.md** - Migration depuis VideoHasher
10. **DUPLICATEFLOW_TESTING.md** - Tests & Benchmarks

## Statistiques

- **49 fichiers Python** dans DuplicateFlow
- **14 algorithmes** de detection
- **12 presets** pre-configures
- **6 categories** d'algorithmes (Perceptual, Statistical, Temporal, Structural, Audio, Hybrid)
- **3 modes** de detection (FINGERPRINT, ALGORITHM, PIPELINE, ONE_TO_ONE)
- **Scalabilite**: Millions de videos avec LSH

## Quick Start

### Installation
```bash
cd duplicateflow
pip install -e .
```

### Utilisation basique
```python
from duplicateflow.api import DetectionEngine, DetectionMode

# N-to-N fingerprint detection
engine = DetectionEngine(mode=DetectionMode.FINGERPRINT)
result = engine.find_duplicates(directory="/videos", workers=8)

# 1-to-1 comparison
engine = DetectionEngine(mode=DetectionMode.ONE_TO_ONE, pipeline='balanced')
match = engine.compare_videos('video1.mp4', 'video2.mp4')
```

## Support

Pour toute question, consulter:
1. [DUPLICATEFLOW_ARCHITECTURE.md](DUPLICATEFLOW_ARCHITECTURE.md) pour comprendre le systeme
2. [DUPLICATEFLOW_ALGORITHMS.md](DUPLICATEFLOW_ALGORITHMS.md) pour choisir un algorithme
3. Les autres documents pour des cas d'usage specifiques
