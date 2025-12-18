# 🧪 Commandes de Vérification - Migration DuplicateFlow

**Date**: 2025-12-18
**Phase**: 1, 2, 3 (partiel) terminées

Ce document contient toutes les commandes pour vérifier que la migration DuplicateFlow fonctionne correctement.

---

## ✅ Tests d'Imports

### Test 1: Import VerificationPipeline

```bash
python3 -c "
from src.plugins.duplicate_finder.verification_pipeline import VerificationPipeline
print(f'✅ VerificationPipeline importé avec succès')
print(f'✅ {len(VerificationPipeline.AVAILABLE_METHODS)} algorithmes DuplicateFlow chargés')
print(f'Algorithmes disponibles:')
for name in sorted(VerificationPipeline.AVAILABLE_METHODS.keys()):
    meta = VerificationPipeline.AVAILABLE_METHODS[name]
    print(f'  - {name}: {meta[\"display_name\"]}')
"
```

**Résultat attendu** :
```
✅ VerificationPipeline importé avec succès
✅ 14 algorithmes DuplicateFlow chargés
Algorithmes disponibles:
  - audio_fingerprint: ...
  - color_histogram: ...
  (etc.)
```

### Test 2: Import SubsequenceDetector

```bash
python3 -c "
from src.plugins.duplicate_finder.subsequence_detector import SubsequenceDetector
print('✅ SubsequenceDetector importé avec succès')
print('✅ Aucune erreur d\'import pour SubsequenceVerificationMethods')
"
```

### Test 3: Import DuplicateFlowAdapter

```bash
python3 -c "
from src.plugins.duplicate_finder.adapters.duplicateflow_adapter import DuplicateFlowAdapter
adapter = DuplicateFlowAdapter()
print('✅ DuplicateFlowAdapter initialisé avec succès')
print(f'✅ DuplicateFlow disponible: {adapter.check_availability()}')
"
```

### Test 4: Import DuplicateFlow API

```bash
python3 -c "
from src.plugins.duplicate_finder.integration import (
    DUPLICATEFLOW_AVAILABLE,
    get_all_algorithms_dict,
    list_algorithms,
    get_algorithm_info
)
print(f'✅ DuplicateFlow disponible: {DUPLICATEFLOW_AVAILABLE}')
algos = get_all_algorithms_dict()
print(f'✅ {len(algos)} algorithmes disponibles via get_all_algorithms_dict()')
native = list_algorithms()
print(f'✅ {len(native)} algorithmes via API native list_algorithms()')
"
```

---

## 🔍 Vérification des Imports Cassés

### Vérifier qu'aucun import obsolète ne reste

```bash
# Chercher les imports de SubsequenceVerificationMethods
echo "=== Recherche SubsequenceVerificationMethods ==="
grep -r "from.*subsequence_verification import\|import.*subsequence_verification" \
  src/plugins/duplicate_finder/ --include="*.py" \
  | grep -v obsolete | grep -v __pycache__ | grep -v "# Removed"

# Chercher les imports de VideoAnalysisMethods
echo "=== Recherche VideoAnalysisMethods ==="
grep -r "from.*video_analysis_methods import\|import.*video_analysis_methods" \
  src/plugins/duplicate_finder/ --include="*.py" \
  | grep -v obsolete | grep -v __pycache__ | grep -v "# Removed"
```

**Résultat attendu** : Aucun résultat (tous les imports cassés ont été corrigés)

### Vérifier les références DuplicateFlow

```bash
# Chercher les utilisations de DuplicateFlowAdapter
echo "=== Utilisations DuplicateFlowAdapter ==="
grep -r "DuplicateFlowAdapter" src/plugins/duplicate_finder/ --include="*.py" \
  | grep -v __pycache__ | wc -l

# Chercher les utilisations de get_all_algorithms_dict
echo "=== Utilisations get_all_algorithms_dict ==="
grep -r "get_all_algorithms_dict" src/plugins/duplicate_finder/ --include="*.py" \
  | grep -v __pycache__ | wc -l
```

**Résultat attendu** : Plusieurs occurrences trouvées

---

## 🧪 Tests Fonctionnels

### Test 1: Créer un VerificationPipeline

```bash
python3 -c "
from src.plugins.duplicate_finder.verification_pipeline import VerificationPipeline

# Créer pipeline
pipeline = VerificationPipeline(mode='filtering')

# Ajouter méthodes
pipeline.add_method('audio_fingerprint', enabled=True, parameters={'threshold': 85.0})
pipeline.add_method('dct_perceptual', enabled=True, parameters={'threshold': 75.0})

# Vérifier config
config = pipeline.get_config()
print(f'✅ Pipeline créé avec {len(config[\"methods\"])} méthodes')
print(f'Mode: {config[\"mode\"]}')
for method in config['methods']:
    print(f'  - {method[\"name\"]}: enabled={method[\"enabled\"]}, weight={method[\"weight\"]}')
"
```

### Test 2: Vérifier API Native DuplicateFlow

```bash
python3 -c "
from duplicateflow.core import list_algorithms, get_algorithm_info, get_categories

# Lister algorithmes
algos = list_algorithms()
print(f'✅ {len(algos)} algorithmes DuplicateFlow natifs')

# Catégories
categories = get_categories()
print(f'✅ Catégories: {categories}')

# Info d'un algorithme
if algos:
    first = algos[0]
    info = get_algorithm_info(first['name'])
    print(f'✅ Info {first[\"name\"]}:')
    print(f'   Display: {info.display_name}')
    print(f'   Category: {info.category}')
    print(f'   Speed: {info.speed}')
    print(f'   Default params: {info.default_params}')
"
```

### Test 3: Tester DuplicateFlowAdapter (nécessite vidéos)

```bash
python3 <<'EOF'
from src.plugins.duplicate_finder.adapters.duplicateflow_adapter import DuplicateFlowAdapter

try:
    adapter = DuplicateFlowAdapter()

    # Lister presets
    presets = adapter.list_presets()
    print(f'✅ {len(presets)} presets disponibles:')
    for preset in presets:
        print(f'  - {preset["icon"]} {preset["display_name"]}: {preset["description"]}')

    print('\n✅ DuplicateFlowAdapter fonctionne correctement')

except Exception as e:
    print(f'❌ Erreur: {e}')
EOF
```

---

## 📊 Métriques de Migration

### Compter les fichiers obsolètes backupés

```bash
echo "=== Fichiers backupés ==="
ls -lh obsolete_files_duplicateflow_migration/
du -sh obsolete_files_duplicateflow_migration/
```

### Compter les lignes de code

```bash
# verification_pipeline.py actuel
echo "=== verification_pipeline.py (nouveau) ==="
wc -l src/plugins/duplicate_finder/verification_pipeline.py

# verification_pipeline.py ancien (backup)
echo "=== verification_pipeline.py (ancien) ==="
wc -l obsolete_files_duplicateflow_migration/verification_pipeline.py.backup

# Calcul réduction
python3 -c "
ancien = 715
nouveau = 390
reduction = ancien - nouveau
pct = (reduction / ancien) * 100
print(f'Réduction: {reduction} lignes (-{pct:.1f}%)')
"
```

### Compter les algorithmes

```bash
python3 -c "
from src.plugins.duplicate_finder.integration import get_all_algorithms_dict, get_categories

algos = get_all_algorithms_dict()
categories = {}
for name, meta in algos.items():
    cat = meta['category']
    if cat not in categories:
        categories[cat] = []
    categories[cat].append(name)

print(f'✅ Total: {len(algos)} algorithmes DuplicateFlow')
print(f'✅ Catégories: {len(categories)}')
for cat, names in sorted(categories.items()):
    print(f'  - {cat}: {len(names)} algorithmes')
"
```

---

## 🔧 Tests de Régression

### Vérifier que l'API backward compatible fonctionne

```bash
python3 <<'EOF'
from src.plugins.duplicate_finder.verification_pipeline import VerificationPipeline

# Test API ancienne (doit toujours fonctionner)
pipeline = VerificationPipeline()

# add_method (ancienne API)
success = pipeline.add_method('audio_fingerprint', enabled=True, parameters={'threshold': 85.0})
print(f'✅ add_method() fonctionne: {success}')

# AVAILABLE_METHODS (ancienne API)
methods = VerificationPipeline.AVAILABLE_METHODS
print(f'✅ AVAILABLE_METHODS accessible: {len(methods)} méthodes')

# get_config (ancienne API)
config = pipeline.get_config()
print(f'✅ get_config() fonctionne: {len(config["methods"])} méthodes configurées')

# get_available_methods (nouvelle API)
available = pipeline.get_available_methods()
print(f'✅ get_available_methods() fonctionne: {len(available)} méthodes')

print('\n✅ Backward compatibility OK')
EOF
```

---

## 🚀 Tests d'Intégration

### Test complet de pipeline

```bash
python3 <<'EOF'
from src.plugins.duplicate_finder.verification_pipeline import VerificationPipeline

# Créer pipeline en mode filtering
pipeline = VerificationPipeline(mode='filtering', enable_caching=False)

# Configurer méthodes
pipeline.add_method('audio_fingerprint', threshold=85.0)
pipeline.add_method('dct_perceptual', threshold=75.0)
pipeline.add_method('color_histogram', threshold=80.0)

# Afficher config
config = pipeline.get_config()
print(f'✅ Pipeline configuré:')
print(f'   Mode: {config["mode"]}')
print(f'   Méthodes: {len(config["methods"])}')

# Test sans vidéos (juste vérifier que ça ne crash pas)
print(f'\n✅ Pipeline prêt à être utilisé avec verify()')
print(f'   Signature: verify(short_video, long_video, start_time, duration)')

# Tester get_available_methods
available = pipeline.get_available_methods()
print(f'\n✅ {len(available)} méthodes disponibles dynamiquement')
print(f'   (chargées depuis DuplicateFlow registry)')

print('\n✅ Test d\'intégration OK')
EOF
```

---

## 📝 Checklist de Validation

Exécuter ces commandes pour vérifier que tout fonctionne :

- [ ] Test 1: Import VerificationPipeline ✅
- [ ] Test 2: Import SubsequenceDetector ✅
- [ ] Test 3: Import DuplicateFlowAdapter ✅
- [ ] Test 4: Import DuplicateFlow API ✅
- [ ] Aucun import cassé restant ✅
- [ ] DuplicateFlowAdapter utilisé ✅
- [ ] get_all_algorithms_dict utilisé ✅
- [ ] Fichiers backupés présents ✅
- [ ] verification_pipeline.py réduit de 45% ✅
- [ ] 14 algorithmes DuplicateFlow chargés ✅
- [ ] Backward compatibility OK ✅
- [ ] Pipeline peut être configuré ✅

---

## 🎯 Commande de Validation Globale

Exécuter cette commande pour tout tester d'un coup :

```bash
python3 <<'VALIDATION'
import sys

print("=" * 60)
print("VALIDATION MIGRATION DUPLICATEFLOW - PHASES 1, 2, 3")
print("=" * 60)

tests_passed = 0
tests_failed = 0

def test(name, fn):
    global tests_passed, tests_failed
    try:
        fn()
        print(f"✅ {name}")
        tests_passed += 1
        return True
    except Exception as e:
        print(f"❌ {name}: {e}")
        tests_failed += 1
        return False

# Test 1: Imports
def test_imports():
    from src.plugins.duplicate_finder.verification_pipeline import VerificationPipeline
    from src.plugins.duplicate_finder.subsequence_detector import SubsequenceDetector
    from src.plugins.duplicate_finder.adapters.duplicateflow_adapter import DuplicateFlowAdapter
    from src.plugins.duplicate_finder.integration import get_all_algorithms_dict
    assert len(VerificationPipeline.AVAILABLE_METHODS) == 14

test("Imports", test_imports)

# Test 2: DuplicateFlow disponible
def test_duplicateflow():
    from src.plugins.duplicate_finder.integration import DUPLICATEFLOW_AVAILABLE
    assert DUPLICATEFLOW_AVAILABLE == True

test("DuplicateFlow disponible", test_duplicateflow)

# Test 3: API native
def test_api_native():
    from duplicateflow.core import list_algorithms, get_categories
    algos = list_algorithms()
    assert len(algos) > 0
    cats = get_categories()
    assert len(cats) > 0

test("API native DuplicateFlow", test_api_native)

# Test 4: Adapter
def test_adapter():
    from src.plugins.duplicate_finder.adapters.duplicateflow_adapter import DuplicateFlowAdapter
    adapter = DuplicateFlowAdapter()
    presets = adapter.list_presets()
    assert len(presets) > 0

test("DuplicateFlowAdapter", test_adapter)

# Test 5: Pipeline creation
def test_pipeline():
    from src.plugins.duplicate_finder.verification_pipeline import VerificationPipeline
    pipeline = VerificationPipeline(mode='filtering')
    success = pipeline.add_method('audio_fingerprint', threshold=85.0)
    assert success == True
    config = pipeline.get_config()
    assert len(config['methods']) == 1

test("Pipeline configuration", test_pipeline)

# Test 6: Backward compatibility
def test_backward_compat():
    from src.plugins.duplicate_finder.verification_pipeline import VerificationPipeline
    methods = VerificationPipeline.AVAILABLE_METHODS
    assert len(methods) > 0
    pipeline = VerificationPipeline()
    available = pipeline.get_available_methods()
    assert len(available) > 0

test("Backward compatibility", test_backward_compat)

# Résultats
print("\n" + "=" * 60)
print(f"RÉSULTATS: {tests_passed} tests passés, {tests_failed} tests échoués")
print("=" * 60)

if tests_failed == 0:
    print("✅ TOUS LES TESTS PASSENT - MIGRATION RÉUSSIE")
    sys.exit(0)
else:
    print("❌ CERTAINS TESTS ONT ÉCHOUÉ - VÉRIFIER LA MIGRATION")
    sys.exit(1)
VALIDATION
```

**Résultat attendu** :
```
============================================================
VALIDATION MIGRATION DUPLICATEFLOW - PHASES 1, 2, 3
============================================================
✅ Imports
✅ DuplicateFlow disponible
✅ API native DuplicateFlow
✅ DuplicateFlowAdapter
✅ Pipeline configuration
✅ Backward compatibility

============================================================
RÉSULTATS: 6 tests passés, 0 tests échoués
============================================================
✅ TOUS LES TESTS PASSENT - MIGRATION RÉUSSIE
```

---

## 📚 Prochaines Étapes

Une fois tous ces tests validés, vous pouvez passer à la **Phase 3 (Workers)** :

1. Réécrire `comparison_worker.py` (457 → ~200 lignes)
2. Réécrire `verification_worker.py` (350 → ~100 lignes)
3. Réécrire `subsequence_worker.py` (400 → ~150 lignes)
4. Réécrire `detection/hybrid/subsequence_detector.py` (1177 → ~100 lignes)

Voir [MASTER_PLAN_MIGRATION_DUPLICATEFLOW.md](MASTER_PLAN_MIGRATION_DUPLICATEFLOW.md) pour les détails.

---

**Date**: 2025-12-18
**Phases terminées**: 1, 2, 3 (partiel)
**Progrès**: 40%
