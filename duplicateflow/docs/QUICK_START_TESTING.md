# Guide Rapide: Tests DuplicateFlow

## 🚀 Lancer les Tests

### Tests Phase 1 (recommandé)
```bash
# Tests complets Phase 1 avec coverage
python3 -m pytest tests/unit/core/interfaces tests/unit/cli/adapters -v \
  --cov=duplicateflow/core/interfaces \
  --cov=duplicateflow/cli/adapters \
  --cov-report=term-missing

# Résultat attendu: 66 tests, 91% coverage
```

### Tests par module
```bash
# Tests core interfaces uniquement (27 tests)
python3 -m pytest tests/unit/core/interfaces -v

# Tests CLI adapters uniquement (39 tests)
python3 -m pytest tests/unit/cli/adapters -v

# Tests d'un fichier spécifique
python3 -m pytest tests/unit/core/interfaces/test_i_progress_reporter.py -v

# Tests d'une fonction spécifique
python3 -m pytest tests/unit/core/interfaces/test_i_progress_reporter.py::TestNullProgressReporter::test_null_progress_reporter_start_phase -v
```

### Tests avec options
```bash
# Tests avec output détaillé
python3 -m pytest tests/unit/ -vv

# Tests avec traceback court
python3 -m pytest tests/unit/ --tb=short

# Tests en mode verbeux avec timing
python3 -m pytest tests/unit/ -v --durations=10

# Tests avec capture d'output
python3 -m pytest tests/unit/ -v -s
```

---

## 📊 Coverage

### Coverage Phase 1 uniquement
```bash
# Coverage HTML interactif
python3 -m pytest tests/unit/core/interfaces tests/unit/cli/adapters \
  --cov=duplicateflow/core/interfaces \
  --cov=duplicateflow/cli/adapters \
  --cov-report=html

# Ouvrir le rapport
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage détaillé
```bash
# Coverage avec lignes manquantes
python3 -m pytest tests/unit/ \
  --cov=duplicateflow/core/interfaces \
  --cov=duplicateflow/cli/adapters \
  --cov-report=term-missing

# Coverage avec branches
python3 -m pytest tests/unit/ \
  --cov=duplicateflow/core/interfaces \
  --cov=duplicateflow/cli/adapters \
  --cov-report=term \
  --cov-branch
```

---

## 🎯 Objectifs Coverage

| Module | Objectif | Actuel | Status |
|--------|----------|--------|--------|
| `core/interfaces/i_progress_reporter.py` | ≥80% | 100%* | ✅ |
| `core/interfaces/i_ui_adapter.py` | ≥80% | 100%* | ✅ |
| `cli/adapters/rich_progress.py` | ≥80% | 100% | ✅ |
| `cli/adapters/rich_ui.py` | ≥80% | 93% | ✅ |
| **Phase 1 Global** | **≥80%** | **91%** | **✅** |

*100% hors abstract methods (normal)

---

## 🧪 Structure Tests

```
tests/
├── __init__.py                    # Package tests
├── conftest.py                    # Fixtures pytest
├── pytest.ini                     # Configuration pytest
└── unit/                          # Tests unitaires
    ├── core/
    │   └── interfaces/
    │       ├── test_i_progress_reporter.py   # 9 tests
    │       └── test_i_ui_adapter.py          # 18 tests
    └── cli/
        └── adapters/
            ├── test_rich_progress.py         # 17 tests
            └── test_rich_ui.py               # 22 tests
```

---

## 🔧 Fixtures Disponibles

### Console Fixtures (dans `conftest.py`)

```python
@pytest.fixture
def console():
    """Console Rich avec capture d'output."""
    # Usage: def test_something(console):
    #           adapter = RichUIAdapter(console)

@pytest.fixture
def null_console():
    """Console Rich silencieuse."""
    # Usage: def test_something(null_console):
    #           reporter = RichProgressReporter(null_console)

@pytest.fixture
def sample_video_files():
    """Liste de fichiers vidéo pour tests."""
    # Returns: [Path("/videos/movie1.mp4"), ...]

@pytest.fixture
def sample_table_data():
    """Données de table pour tests."""
    # Returns: (headers, rows)
```

---

## 📝 Exemples d'utilisation

### Test avec fixture console
```python
def test_display_message(console):
    """Test d'affichage de message."""
    adapter = RichUIAdapter(console)
    adapter.display_message("Test", MessageType.INFO)
    # Pas de vérification output nécessaire
```

### Test avec NullUIAdapter
```python
def test_message_storage():
    """Test de stockage de messages."""
    adapter = NullUIAdapter()
    adapter.display_message("Test", MessageType.INFO)

    # Vérifier stockage
    assert len(adapter.messages) == 1
    assert adapter.messages[0]['message'] == "Test"
    assert adapter.messages[0]['type'] == MessageType.INFO
```

### Test avec NullProgressReporter
```python
def test_progress_workflow():
    """Test workflow complet."""
    reporter = NullProgressReporter()

    reporter.start_phase("test", total=10)
    reporter.update("test", current=5)
    reporter.finish_phase("test")

    # Vérifier pas d'erreur
    assert reporter.elapsed_time() == 0.0
```

---

## 🐛 Debugging Tests

### Tests avec pdb
```bash
# Lancer avec debugger Python
python3 -m pytest tests/unit/ --pdb

# Break sur premier échec
python3 -m pytest tests/unit/ -x --pdb
```

### Tests avec print
```bash
# Voir les print() dans les tests
python3 -m pytest tests/unit/ -v -s
```

### Tests avec warnings
```bash
# Voir tous les warnings
python3 -m pytest tests/unit/ -v -W all
```

---

## 📈 CI/CD

### Commandes CI
```bash
# Commande complète pour CI
python3 -m pytest tests/unit/ -v \
  --cov=duplicateflow \
  --cov-report=xml \
  --cov-report=term \
  --cov-fail-under=80

# Génère coverage.xml pour Codecov/Coveralls
```

### Pre-commit hook
```bash
# Ajouter dans .git/hooks/pre-commit
#!/bin/bash
python3 -m pytest tests/unit/core/interfaces tests/unit/cli/adapters -v
if [ $? -ne 0 ]; then
    echo "Tests échoués. Commit annulé."
    exit 1
fi
```

---

## 🎓 Bonnes Pratiques

### 1. Nommer les tests clairement
```python
# ✅ Bon
def test_null_progress_reporter_start_phase():
    """Test that start_phase does nothing."""

# ❌ Mauvais
def test_1():
    """Test."""
```

### 2. Utiliser fixtures
```python
# ✅ Bon - Utilise fixture
def test_display(console):
    adapter = RichUIAdapter(console)

# ❌ Mauvais - Crée à chaque fois
def test_display():
    console = Console(file=StringIO())
    adapter = RichUIAdapter(console)
```

### 3. Tester edge cases
```python
# ✅ Bon - Teste cas limites
def test_empty_choices():
    adapter = NullUIAdapter()
    answer = adapter.ask_question("Q", choices=[])
    assert answer == ""

def test_empty_message():
    reporter = NullProgressReporter()
    reporter.start_phase("test", total=1, message="")
```

### 4. Un test = un concept
```python
# ✅ Bon - Un test par concept
def test_display_info_message():
    # Test INFO uniquement

def test_display_error_message():
    # Test ERROR uniquement

# ❌ Mauvais - Teste trop de choses
def test_all_messages():
    # Test INFO, ERROR, WARNING, SUCCESS...
```

---

## 📚 Ressources

- [Documentation Pytest](https://docs.pytest.org/)
- [Documentation Coverage.py](https://coverage.readthedocs.io/)
- [Documentation Rich](https://rich.readthedocs.io/)
- [PHASE1_PROGRESS.md](./PHASE1_PROGRESS.md) - Détails Phase 1
- [PHASE1_DAY1_SUMMARY.md](./PHASE1_DAY1_SUMMARY.md) - Résumé Jour 1

---

*Dernière mise à jour: 2025-12-19*
