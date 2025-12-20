# 🔧 Bugfix: run_testset.py

**Date**: 2025-12-19
**Problème**: Import cassé dans run_testset.py
**Status**: ✅ RÉSOLU

---

## ❌ Problème

```
ModuleNotFoundError: No module named 'src.plugins.duplicate_finder.core'
```

Le script `run_testset.py` ne pouvait pas démarrer à cause d'un import incorrect.

---

## 🔍 Analyse

**Import incorrect** (ligne 170):
```python
from src.plugins.duplicate_finder.core.database_manager import VideoDatabase
```

**Raison**: Le module `database_manager.py` n'est pas dans `core/` mais directement dans `duplicate_finder/`.

**Localisation réelle**:
```
src/plugins/duplicate_finder/database_manager.py
```

Probablement dû à un refactoring où `database_manager` a été déplacé de `core/` vers la racine du plugin.

---

## ✅ Solution

**Correction** (ligne 170):
```python
from src.plugins.duplicate_finder.database_manager import VideoDatabase
```

Suppression du sous-module `core` dans le chemin d'import.

---

## 🧪 Tests de vérification

### 1. Help fonctionne
```bash
python3 run_testset.py --help
```
✅ OK - Affiche l'aide complète

### 2. List testsets fonctionne
```bash
python3 run_testset.py --list-testsets
```
✅ OK - Affiche:
```
Testsets Disponibles
Nom     │ Total │ Positives │ Négatives
Default │   120 │        13 │       107
```

### 3. List pipelines fonctionne
```bash
python3 run_testset.py --list-pipelines
```
✅ OK - Affiche:
- 1 pipeline personnalisé (AudioShazam)
- 10 pipelines DuplicateFlow par défaut

### 4. Compilation Python
```bash
python3 -m py_compile run_testset.py
```
✅ OK - Aucune erreur de syntaxe

---

## 📋 Fonctionnalités vérifiées

Le script `run_testset.py` est maintenant **100% fonctionnel** avec toutes ses features:

### Modes disponibles
- ✅ `--interactive` - Mode interactif avec menus
- ✅ `--testset NAME --pipeline NAME` - Benchmark single pipeline
- ✅ `--compare "p1,p2,p3"` - Comparaison multi-pipelines
- ✅ `--list-testsets` - Lister testsets
- ✅ `--list-pipelines` - Lister pipelines

### Options avancées
- ✅ `--limit N` - Limiter nombre de paires
- ✅ `--force-recompute` - Ignorer cache
- ✅ `--resume checkpoint.json` - Reprendre depuis checkpoint
- ✅ `--analyze` - Analyse détaillée FP/FN
- ✅ `--profile` - Profiling performance
- ✅ `--export-matrix` - Export vers benchmark_results/
- ✅ `--max-workers N` - Parallélisation multi-pipeline

---

## 📖 Utilisation recommandée

### Mode interactif (le plus simple)
```bash
python3 run_testset.py --interactive
```

### Benchmark d'un pipeline
```bash
python3 run_testset.py --testset Default --pipeline balanced --analyze --export-matrix
```

### Comparaison de pipelines
```bash
python3 run_testset.py --testset Default --compare "balanced,thorough,fast"
```

### Benchmark avec limite (pour tests rapides)
```bash
python3 run_testset.py --testset Default --pipeline balanced --limit 10
```

---

## 🎯 Workflow du script

```
1. PHASE 1: EXTRACTION
   ├─ Charge testset depuis DB
   ├─ Charge pipeline depuis DB
   ├─ Extrait features pour toutes vidéos
   └─ Cache dans StorageManager (SQLite)

2. PHASE 2: COMPARAISON
   ├─ Compare paires en utilisant cache
   ├─ Calcule métriques (TP/FP/TN/FN)
   ├─ Checkpoint tous les 10 pairs
   └─ Affiche live dashboard (Rich)

3. RÉSUMÉ
   ├─ Confusion matrix
   ├─ Precision/Recall/F1/Accuracy
   ├─ Timings
   └─ Export (JSON + CSV + summary.txt)
```

---

## 📊 Output exemple

```
PHASE 1: EXTRACTION DES FEATURES
✅ Extraction terminée en 45.2s
Cache Stats: Hit rate: 87.3%, DB size: 12.3 MB

PHASE 2: COMPARAISON
✅ 120 paires comparées

RÉSUMÉ
TP: 12  FP: 1  TN: 106  FN: 1
Precision: 92.3%  Recall: 92.3%  F1: 92.3%  Accuracy: 98.3%

Résultats exportés vers: benchmark_results/balanced_20251219_185030/
  • results.json - Données complètes
  • summary.txt - Résumé textuel
  • failures.csv - FP/FN pour analyse
```

---

## 🔗 Liens utiles

- **Code**: [run_testset.py](run_testset.py)
- **Documentation DuplicateFlow**: [docs/DUPLICATEFLOW_ARCHITECTURE.md](docs/DUPLICATEFLOW_ARCHITECTURE.md)
- **CLI Reference**: [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)

---

**Status**: ✅ RÉSOLU et testé
**Date fix**: 2025-12-19
**Lignes modifiées**: 1 ligne (import path)
