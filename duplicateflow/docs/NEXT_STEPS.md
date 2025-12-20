# 🎯 Prochaines étapes - Checklist

**Date**: 2025-12-19
**Pour**: Reprendre le travail sur VideoFlow/DuplicateFlow

---

## ⚡ Actions immédiates (5 min)

### 1. Lire la documentation
```bash
# Dans l'ordre:
cat docs/CURRENT_WORK.md           # État actuel
cat docs/RESUME_CONTEXT.md         # Contexte complet
cat docs/DUPLICATEFLOW_QUICK_REFERENCE.md  # Référence rapide
```

### 2. Vérifier l'état Git
```bash
git status
git log --oneline -10
git branch  # Doit être sur feature/duplicateflow-fusion
```

---

## 🧹 Nettoyage Git (15 min)

### 1. Ajouter fichiers DB à .gitignore
```bash
echo "" >> .gitignore
echo "# SQLite temporary files" >> .gitignore
echo "*.db-wal" >> .gitignore
echo "*.db-shm" >> .gitignore
echo "*.db-journal" >> .gitignore

# Unstage ces fichiers s'ils sont staged
git reset HEAD *.db-wal *.db-shm 2>/dev/null || true
```

### 2. Organiser scripts temporaires
```bash
# Créer dossier pour scripts de debug
mkdir -p scripts/debug

# Déplacer scripts temporaires
mv test_*.py scripts/debug/ 2>/dev/null || true
mv debug_*.py scripts/debug/ 2>/dev/null || true
mv diagnostic_*.py scripts/debug/ 2>/dev/null || true
mv capture_*.py scripts/debug/ 2>/dev/null || true
mv patch_*.py scripts/debug/ 2>/dev/null || true
mv replace_*.py scripts/debug/ 2>/dev/null || true
mv add_*.py scripts/debug/ 2>/dev/null || true
mv update_*.py scripts/debug/ 2>/dev/null || true
mv new_*.py scripts/debug/ 2>/dev/null || true
mv panels_*.py scripts/debug/ 2>/dev/null || true

# Ajouter à gitignore
echo "scripts/debug/" >> .gitignore

# Ou supprimer si pas nécessaires
# rm -rf scripts/debug/
```

### 3. Vérifier les scripts utiles
```bash
# Garder scripts potentiellement utiles dans racine
ls *.py
# Décider lesquels garder:
# - pytest.ini → Garder
# - run_tests.sh → Garder
# Autres → Déplacer ou supprimer
```

---

## ✅ Commits (10 min)

### 1. Commit documentation
```bash
git add docs/
git add NEXT_STEPS.md
git commit -m "docs: Add comprehensive DuplicateFlow documentation

- DUPLICATEFLOW_ARCHITECTURE.md: Complete architecture guide (800+ lines)
- DUPLICATEFLOW_QUICK_REFERENCE.md: Quick reference for developers (600+ lines)
- CURRENT_WORK.md: Current development status
- RESUME_CONTEXT.md: Complete context for resuming work
- NEXT_STEPS.md: Checklist for next session"
```

### 2. Commit gitignore updates
```bash
git add .gitignore
git commit -m "chore: Add SQLite temp files to gitignore"
```

### 3. Commit cleanup scripts
```bash
git add scripts/
git commit -m "chore: Organize debug scripts into scripts/debug/"
# OU si supprimés:
# git commit -m "chore: Remove temporary debug scripts"
```

### 4. Commit Phase 12 changes
```bash
git add duplicateflow/pipeline/
git add duplicateflow/sdk/
git add duplicateflow/storage/
git add src/plugins/duplicate_finder/

git commit -m "feat: Phase 12 - Validators, PipelineStore, Partial Analysis

DuplicateFlow enhancements:
- Add Validator SDK (LengthValidator for pre/post validation)
- Add PipelineStore for pipeline persistence in DB
- Add partial analysis (analyze_duration, analyze_from_start)
- Update presets with validators (fast_duplicates, accurate_scenes)
- Add intro/credits detector presets

duplicate_finder plugin:
- Fix imports after UI cleanup
- Update integration layer
- Cleanup obsolete code

Tests:
- Add validator tests (TODO: complete)
- Add PipelineStore tests (TODO: complete)
- Add partial analysis tests (TODO: complete)"
```

### 5. Commit i18n updates (si nécessaires)
```bash
git add resources/i18n/
git commit -m "i18n: Update translation keys after cleanup"
```

### 6. Vérifier status final
```bash
git status
# Devrait être clean ou seulement fichiers untracked non importants
```

---

## 🧪 Tests (20 min)

### 1. Tests unitaires DuplicateFlow
```bash
# Tous les tests
pytest duplicateflow/tests/ -v

# Tests spécifiques (si créés)
pytest duplicateflow/tests/test_validators.py -v
pytest duplicateflow/tests/test_pipeline_store.py -v
pytest duplicateflow/tests/test_partial_analysis.py -v
```

### 2. Tests intégration UI
```bash
pytest tests/duplicate_finder/ -v
```

### 3. Coverage
```bash
pytest --cov=duplicateflow --cov-report=html
# Ouvrir htmlcov/index.html pour voir détails
```

### 4. Tests manuels
```python
# Test imports
python -c "from duplicateflow.pipeline import Pipeline; print('✓ Pipeline')"
python -c "from duplicateflow.sdk import LengthValidator; print('✓ LengthValidator')"
python -c "from duplicateflow.storage import PipelineStore; print('✓ PipelineStore')"

# Test pipeline
python -c "
from duplicateflow.pipeline import Pipeline
p = Pipeline.from_preset('fast')
print('✓ Preset fast loaded')
"
```

---

## 📝 Tests manquants à créer (1h)

### 1. test_validators.py
```python
# duplicateflow/tests/test_validators.py

from duplicateflow.sdk import LengthValidator

def test_length_validator_percent():
    validator = LengthValidator(tolerance_percent=10.0)
    # Test avec vidéos similaires
    result = validator.validate('video1.mp4', 'video2.mp4')
    assert result['accepted'] == True

def test_length_validator_seconds():
    validator = LengthValidator(tolerance_seconds=5.0)
    # Test avec vidéos similaires
    result = validator.validate('video1.mp4', 'video2.mp4')
    assert result['accepted'] == True

def test_length_validator_reject():
    validator = LengthValidator(tolerance_percent=1.0)
    # Test avec vidéos très différentes
    result = validator.validate('short.mp4', 'long.mp4')
    assert result['accepted'] == False
    assert 'reason' in result
```

### 2. test_pipeline_store.py
```python
# duplicateflow/tests/test_pipeline_store.py

from duplicateflow.storage import PipelineStore

def test_save_load_pipeline():
    store = PipelineStore(':memory:')
    config = {'steps': [], 'threshold': 75.0}
    store.save_pipeline('test', config)
    loaded = store.load_pipeline('test')
    assert loaded == config

def test_list_pipelines():
    store = PipelineStore(':memory:')
    store.save_pipeline('p1', {})
    store.save_pipeline('p2', {})
    pipelines = store.list_pipelines()
    assert len(pipelines) >= 2
```

### 3. test_partial_analysis.py
```python
# duplicateflow/tests/test_partial_analysis.py

from duplicateflow.pipeline import Pipeline

def test_analyze_duration_from_start():
    pipeline = Pipeline(
        steps=[{'algorithm': 'frame_hash', 'weight': 1.0}],
        analyze_duration=10.0,
        analyze_from_start=True
    )
    result = pipeline.compare('video1.mp4', 'video2.mp4')
    # Vérifier que seulement 10s analysées
    assert result.metadata.get('duration_analyzed') <= 10.0

def test_analyze_duration_from_end():
    pipeline = Pipeline(
        steps=[{'algorithm': 'frame_hash', 'weight': 1.0}],
        analyze_duration=10.0,
        analyze_from_start=False
    )
    result = pipeline.compare('video1.mp4', 'video2.mp4')
    # Vérifier que seulement 10s analysées depuis la fin
    assert result.metadata.get('duration_analyzed') <= 10.0
```

---

## 🚀 Merge vers main (après tests OK)

### 1. Vérifier que tout est commité
```bash
git status  # Doit être clean
```

### 2. Pull latest main
```bash
git checkout main
git pull origin main
```

### 3. Merge feature branch
```bash
git merge feature/duplicateflow-fusion

# Si conflits:
git status
# Résoudre conflits
git add .
git commit -m "Merge feature/duplicateflow-fusion into main"
```

### 4. Tests finaux sur main
```bash
pytest duplicateflow/tests/ -v
pytest tests/duplicate_finder/ -v
```

### 5. Push vers remote
```bash
git push origin main
```

### 6. Tag release (optionnel)
```bash
git tag -a v1.0.0 -m "Release 1.0.0 - DuplicateFlow complete with validators, PipelineStore, partial analysis"
git push origin v1.0.0
```

---

## 📚 Documentation supplémentaire (optionnel)

### 1. API Reference (sphinx)
```bash
# Installer sphinx
pip install sphinx sphinx-rtd-theme

# Générer docs
cd docs
sphinx-quickstart
sphinx-apidoc -o api ../duplicateflow
make html
```

### 2. User Guide
Créer `docs/USER_GUIDE.md` avec:
- Installation
- Quick start
- Exemples d'utilisation
- FAQ
- Troubleshooting

### 3. Developer Guide
Créer `docs/DEVELOPER_GUIDE.md` avec:
- Setup développement
- Architecture decisions
- Comment ajouter un algorithme
- Comment ajouter un preset
- Testing guidelines
- Contributing guidelines

---

## 📊 Performance benchmarks (optionnel)

### 1. Créer script benchmark
```python
# scripts/benchmark_presets.py

from duplicateflow.pipeline import Pipeline
from duplicateflow.pipeline.presets import PRESETS
import time

videos = [
    ('short.mp4', 'long.mp4'),
    # ... autres paires
]

results = {}
for preset_name in PRESETS.keys():
    pipeline = Pipeline.from_preset(preset_name)
    times = []
    for v1, v2 in videos:
        start = time.time()
        result = pipeline.compare(v1, v2)
        times.append(time.time() - start)
    results[preset_name] = {
        'avg_time': sum(times) / len(times),
        'min_time': min(times),
        'max_time': max(times)
    }

# Afficher résultats
for name, stats in results.items():
    print(f"{name}: {stats['avg_time']:.2f}s avg")
```

### 2. Exécuter benchmark
```bash
python scripts/benchmark_presets.py > benchmarks.txt
```

### 3. Créer graphiques (optionnel)
```python
import matplotlib.pyplot as plt
# Créer graphiques de performance
```

---

## 🎯 Checklist finale

Avant de considérer Phase 12 terminée:

- [ ] Documentation créée et commitée
- [ ] Git status clean (pas de fichiers temporaires)
- [ ] .gitignore à jour
- [ ] Tous les tests passent
- [ ] Coverage > 80%
- [ ] Tests validators créés
- [ ] Tests PipelineStore créés
- [ ] Tests partial analysis créés
- [ ] Intégration UI testée
- [ ] Code mergé vers main
- [ ] Tag release créé (optionnel)
- [ ] Benchmarks exécutés (optionnel)
- [ ] API Reference générée (optionnel)

---

## 📞 Commandes de diagnostic

Si problème, utiliser ces commandes:

```bash
# Voir état complet
git status
git log --graph --oneline --all -20

# Voir différences
git diff
git diff --cached

# Voir fichiers modifiés
git diff --name-only

# Voir fichiers ignorés
git status --ignored

# Tester imports
python -c "import duplicateflow; print(dir(duplicateflow))"

# Vérifier cache
python -c "
from duplicateflow.storage import StorageManager
s = StorageManager()
print(s.get_statistics())
"

# Lister algorithmes
python -c "
from duplicateflow.algorithms import list_algorithms
algos = list_algorithms()
print(f'{len(algos)} algorithms:')
for a in algos:
    print(f'  - {a.name}')
"

# Lister presets
python -c "
from duplicateflow.pipeline.presets import PRESETS
print(f'{len(PRESETS)} presets:')
for name in PRESETS.keys():
    print(f'  - {name}')
"
```

---

## 🆘 En cas de problème

### Tests qui échouent
1. Lire message d'erreur complet
2. Vérifier imports: `python -c "from duplicateflow.pipeline import Pipeline"`
3. Vérifier fichiers vidéos de test existent
4. Vérifier cache pas corrompu: `rm -rf ~/.duplicateflow/cache`
5. Re-run tests avec `-v` pour détails

### Merge conflicts
1. `git status` pour voir fichiers conflictuels
2. Ouvrir fichiers et chercher `<<<<<<<`
3. Résoudre manuellement
4. `git add <fichier>` pour marquer résolu
5. `git commit` pour finaliser merge

### Import errors
1. Vérifier structure fichiers: `ls duplicateflow/`
2. Vérifier __init__.py existent
3. Vérifier PYTHONPATH: `echo $PYTHONPATH`
4. Réinstaller en mode dev: `pip install -e .`

---

## ✨ Résumé

**Phase 12 accompli**:
- ✅ ~100K lignes supprimées
- ✅ 3 nouvelles features majeures
- ✅ Documentation complète
- ⏳ Tests à finaliser
- ⏳ Merge vers main

**Prochaine session** (~2h):
1. Nettoyer git (15 min)
2. Commiter tout (10 min)
3. Créer tests manquants (1h)
4. Merger vers main (20 min)
5. Célébrer ! 🎉

---

**Bonne continuation !** 🚀

Ce fichier + la documentation dans `docs/` devrait permettre à n'importe quelle session Claude Code de reprendre le travail immédiatement avec contexte complet.
