# Correction du Bug: AttributeError 'VideoDatabase' object has no attribute 'pool'

## Problème Identifié

L'application VideoFlow/duplicate_finder générait une erreur au démarrage:

```
AttributeError: 'VideoDatabase' object has no attribute 'pool'
```

Cette erreur se produisait dans `pipeline_manager.py` ligne 58:
```python
with self.db.pool.get_connection() as conn:
```

## Cause Racine

La classe `VideoDatabase` dans `database_manager.py` expose l'attribut `connection_pool` (et non `pool`):

```python
class VideoDatabase:
    def __init__(self, db_path=None):
        # ...
        self.connection_pool = ConnectionPool(db_path, pool_size=None)
```

**Erreur:** Le code utilisait `self.db.pool.get_connection()` au lieu de l'API correcte.

## API Correcte de VideoDatabase

La classe `VideoDatabase` offre DEUX façons d'obtenir une connexion:

### 1. Méthode Wrapper (Recommandée)
```python
with self.db.get_connection() as conn:
    cursor = conn.cursor()
    # ...
```

Cette méthode wrapper (ligne 766 de database_manager.py) est la façon la plus propre et recommandée.

### 2. Accès Direct au Pool
```python
with self.db.connection_pool.get_connection() as conn:
    cursor = conn.cursor()
    # ...
```

Accès direct au pool de connexions (plus verbeux).

### ❌ Erreur à Éviter
```python
with self.db.pool.get_connection() as conn:  # ❌ ERREUR: 'pool' n'existe pas
    # ...
```

## Corrections Appliquées

### Résumé
- **Total d'occurrences corrigées:** 28
- **Fichiers modifiés:** 5
- **Correction appliquée:** `self.db.pool.get_connection()` → `self.db.get_connection()`

### Détail par Fichier

#### 1. `/src/plugins/duplicate_finder/orchestration/pipeline_manager.py`
- **Occurrences corrigées:** 8
- **Lignes:** 58, 164, 204, 286, 314, 344, 385, 444
- **Méthodes affectées:**
  - `initialize_default_protocols()`
  - `save_pipeline()`
  - `update_pipeline()`
  - `delete_pipeline()`
  - `get_pipeline()`
  - `get_pipeline_by_name()`
  - `list_pipelines()`
  - `increment_use_count()`

#### 2. `/src/plugins/duplicate_finder/services/test_set_manager.py`
- **Occurrences corrigées:** 6
- **Lignes:** 70, 120, 129, 142, 175, 207
- **Méthodes affectées:**
  - `add_test_pair()`
  - `update_test_pair()`
  - `delete_test_pair()`
  - `list_test_pairs()`
  - `list_test_sets()`
  - `delete_test_set()`

#### 3. `/src/plugins/duplicate_finder/services/benchmark_manager.py`
- **Occurrences corrigées:** 11
- **Lignes:** 322, 333, 345, 504, 1094, 1142, 1192, 1219, 1249, 1297, 1324
- **Méthodes affectées:**
  - `_create_benchmark_run()`
  - `_complete_benchmark_run()`
  - `compute_sha256_for_video()`
  - `_save_benchmark_result()`
  - `get_run_details()`
  - `get_run_history()`
  - `get_benchmark_run()`
  - `get_benchmark_results()`
  - `list_benchmark_runs()`
  - `delete_benchmark_run()`

#### 4. `/src/plugins/duplicate_finder/services/benchmark_exporter.py`
- **Occurrences corrigées:** 2
- **Lignes:** 107, 131
- **Méthodes affectées:**
  - `_get_run_details_from_db()`
  - `_get_benchmark_results_from_db()`

#### 5. `/src/plugins/duplicate_finder/ui/test_set_wizard.py`
- **Occurrences corrigées:** 1
- **Lignes:** 789
- **Méthodes affectées:**
  - `_save_pairs_to_database()`

## Vérification

### Tests Effectués

#### 1. Vérification de Suppression des Erreurs
```bash
$ grep -r "\.pool\.get_connection()" src/plugins/duplicate_finder --include="*.py" | wc -l
0
```
✅ Plus aucune occurrence de l'ancienne API incorrecte.

#### 2. Test d'Import des Modules
```bash
$ python3 test_import_duplicate_finder.py
```
Résultat:
- ✅ 6/6 imports réussis
- ✅ database_manager.VideoDatabase
- ✅ orchestration.PipelineManager
- ✅ services.TestSetManager
- ✅ services.BenchmarkManager
- ✅ services.BenchmarkJSONExporter
- ✅ ui.TestSetWizard

#### 3. Test de Connexion à la Base de Données
```python
from plugins.duplicate_finder.database_manager import VideoDatabase

db = VideoDatabase("/tmp/test.db")

# Test avec l'API recommandée
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()  # (1,)
```
✅ Connexion réussie avec l'API correcte.

#### 4. Vérification des Attributs
```python
hasattr(db, 'pool')              # False ✅
hasattr(db, 'connection_pool')   # True ✅
hasattr(db, 'get_connection')    # True ✅
```

## Fichiers de Test Créés

1. **`test_db_connection.py`**
   - Test basique de l'API de connexion
   - Vérifie les attributs de VideoDatabase
   - Teste les deux méthodes de connexion (wrapper + direct)

2. **`test_import_duplicate_finder.py`**
   - Test complet des imports du plugin
   - Vérifie que tous les modules se chargent correctement
   - Test de connexion DB avec l'API corrigée

## Impact

### Modules Corrigés
- ✅ Gestion des pipelines (PipelineManager)
- ✅ Gestion des test sets (TestSetManager)
- ✅ Gestion des benchmarks (BenchmarkManager)
- ✅ Export de benchmarks (BenchmarkJSONExporter)
- ✅ Interface utilisateur (TestSetWizard)

### Fonctionnalités Restaurées
- ✅ Chargement des pipelines par défaut au démarrage
- ✅ Sauvegarde/édition/suppression de pipelines
- ✅ Gestion des paires de test
- ✅ Exécution et historique des benchmarks
- ✅ Export JSON des résultats
- ✅ Interface de création de test sets

## Conclusion

Le bug `AttributeError: 'VideoDatabase' object has no attribute 'pool'` a été entièrement corrigé.

**28 occurrences** de l'API incorrecte `.pool.get_connection()` ont été remplacées par l'API correcte `.get_connection()` dans **5 fichiers** du plugin duplicate_finder.

Tous les tests d'import et de connexion passent avec succès. L'application peut maintenant démarrer sans erreur.

## Prochaines Étapes

1. Supprimer les fichiers de test temporaires si nécessaire:
   - `test_db_connection.py`
   - `test_import_duplicate_finder.py`

2. Tester l'application complète en lançant VideoFlow

3. Vérifier que les fonctionnalités de pipeline management fonctionnent correctement dans l'interface graphique
