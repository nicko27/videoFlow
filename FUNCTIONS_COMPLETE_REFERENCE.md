# FUNCTIONS COMPLETE REFERENCE - Duplicate Finder Plugin

**Date de mise à jour**: 2025-12-07
**Version**: Système de Benchmark v1.0

Ce document référence toutes les fonctions publiques des composants du système de duplicate finder, incluant le nouveau système de benchmark.

---

## 📦 MANAGERS

### PipelineManager (`managers/pipeline_manager.py`)

Gestionnaire pour les pipelines de vérification sauvegardés.

#### `__init__(db_manager)`
**Paramètres:**
- `db_manager` (VideoDatabase): Instance de la base de données

**Returns:** None

---

#### `save_pipeline(name, description, mode, methods)`
Sauvegarde un pipeline utilisateur.

**Paramètres:**
- `name` (str): Nom unique du pipeline
- `description` (str): Description du pipeline
- `mode` (str): 'filtering', 'weighting', ou 'hybrid'
- `methods` (List[Dict]): Liste de dicts avec {name, enabled, parameters, weight}

**Returns:** `int` - ID du pipeline créé

**Raises:**
- `ValueError`: Si le nom existe déjà ou mode invalide

**Exemple:**
```python
pipeline_id = manager.save_pipeline(
    name="Mon Pipeline",
    description="Pipeline personnalisé",
    mode="filtering",
    methods=[
        {'name': 'dct_coefficients', 'enabled': True, 'parameters': {'threshold': 75.0}, 'weight': 1.0}
    ]
)
```

---

#### `update_pipeline(pipeline_id, name=None, description=None, mode=None, methods=None)`
Met à jour un pipeline existant.

**Paramètres:**
- `pipeline_id` (int): ID du pipeline à modifier
- `name` (str, optional): Nouveau nom
- `description` (str, optional): Nouvelle description
- `mode` (str, optional): Nouveau mode
- `methods` (List[Dict], optional): Nouvelles méthodes

**Returns:** `bool` - True si mise à jour réussie

---

#### `delete_pipeline(pipeline_id)`
Supprime un pipeline.

**Paramètres:**
- `pipeline_id` (int): ID du pipeline

**Returns:** `bool` - True si suppression réussie

---

#### `get_pipeline(pipeline_id)`
Récupère un pipeline par ID.

**Paramètres:**
- `pipeline_id` (int): ID du pipeline

**Returns:** `Optional[Dict]` - Dict avec {id, name, description, mode, methods, created_at, last_used_at, use_count} ou None

---

#### `get_pipeline_by_name(name)`
Récupère un pipeline par nom.

**Paramètres:**
- `name` (str): Nom du pipeline

**Returns:** `Optional[Dict]` - Pipeline ou None

---

#### `list_pipelines(include_defaults=True)`
Liste tous les pipelines disponibles.

**Paramètres:**
- `include_defaults` (bool): Si True, inclut les 10 protocoles prédéfinis (défaut: True)

**Returns:** `List[Dict]` - Liste de pipelines avec {id, name, description, mode, is_default, protocol_id, ...}

---

#### `increment_use_count(pipeline_id)`
Incrémente le compteur d'utilisation.

**Paramètres:**
- `pipeline_id` (int): ID du pipeline

**Returns:** None

---

#### `get_protocol_config(protocol_id)`
Récupère la configuration d'un protocole prédéfini.

**Paramètres:**
- `protocol_id` (str): 'anti_fp', 'balanced', 'high_precision', 'fast', 'dct_only', 'motion_only', 'weighted_consensus', 're_encoded_specialist', 'ultra_permissive', 'hybrid_conservative'

**Returns:** `Optional[Dict]` - Config avec {name, description, mode, methods} ou None

---

#### `create_verification_pipeline(pipeline_config)`
Crée une instance VerificationPipeline depuis une config.

**Paramètres:**
- `pipeline_config` (Dict): Dict avec {mode, methods}

**Returns:** `VerificationPipeline` - Instance configurée

---

#### `export_to_json(pipeline_id, file_path)`
Exporte un pipeline vers un fichier JSON.

**Paramètres:**
- `pipeline_id` (int): ID du pipeline
- `file_path` (str): Chemin de destination

**Returns:** None

**Raises:**
- `ValueError`: Si pipeline non trouvé

---

#### `import_from_json(file_path, name=None)`
Importe un pipeline depuis un fichier JSON.

**Paramètres:**
- `file_path` (str): Chemin du fichier JSON
- `name` (str, optional): Nom pour le pipeline importé

**Returns:** `int` - ID du pipeline créé

---

### TestSetManager (`managers/test_set_manager.py`)

Gestionnaire pour les paires de test (ground truth).

#### `__init__(db_manager)`
**Paramètres:**
- `db_manager` (VideoDatabase): Instance de la base de données

**Returns:** None

---

#### `add_test_pair(video1_path, video2_path, expected, test_set_name='default', start_time=0.0, duration=None, sequence_score=100.0, notes=None)`
Ajoute une paire de test.

**Paramètres:**
- `video1_path` (str): Chemin vidéo 1
- `video2_path` (str): Chemin vidéo 2
- `expected` (str): 'positive', 'negative', ou 'unknown'
- `test_set_name` (str): Nom du test set (défaut: 'default')
- `start_time` (float): Temps de début en secondes (défaut: 0.0)
- `duration` (float, optional): Durée en secondes (auto-détectée si None)
- `sequence_score` (float): Score attendu (défaut: 100.0)
- `notes` (str, optional): Notes

**Returns:** `int` - ID de la paire créée

**Raises:**
- `ValueError`: Si expected invalide

**Exemple:**
```python
pair_id = manager.add_test_pair(
    video1_path="/path/to/video1.mp4",
    video2_path="/path/to/video2.mp4",
    expected="positive",
    test_set_name="test_reencoded"
)
```

---

#### `update_test_pair(pair_id, expected=None, start_time=None, duration=None, sequence_score=None, notes=None)`
Met à jour une paire de test.

**Paramètres:**
- `pair_id` (int): ID de la paire
- `expected` (str, optional): Nouvelle valeur expected
- `start_time` (float, optional): Nouveau start_time
- `duration` (float, optional): Nouvelle durée
- `sequence_score` (float, optional): Nouveau score
- `notes` (str, optional): Nouvelles notes

**Returns:** `bool` - True si mise à jour réussie

---

#### `delete_test_pair(pair_id)`
Supprime une paire de test.

**Paramètres:**
- `pair_id` (int): ID de la paire

**Returns:** `bool` - True si suppression réussie

---

#### `get_test_set(test_set_name='default')`
Récupère toutes les paires d'un test set.

**Paramètres:**
- `test_set_name` (str): Nom du test set (défaut: 'default')

**Returns:** `List[Dict]` - Liste de paires avec {id, video1_path, video2_path, expected, start_time, duration, sequence_score, notes, created_at}

---

#### `list_test_sets()`
Liste tous les test sets disponibles.

**Paramètres:** Aucun

**Returns:** `List[Dict]` - Liste avec {name, count, positives, negatives, unknowns}

---

#### `delete_test_set(test_set_name)`
Supprime toutes les paires d'un test set.

**Paramètres:**
- `test_set_name` (str): Nom du test set

**Returns:** `int` - Nombre de paires supprimées

---

#### `generate_from_file_list(file_paths, test_set_name='generated', expected='unknown')`
Génère toutes les paires possibles depuis une liste de fichiers.

**Paramètres:**
- `file_paths` (List[str]): Liste de chemins vidéo
- `test_set_name` (str): Nom du test set (défaut: 'generated')
- `expected` (str): Valeur expected par défaut (défaut: 'unknown')

**Returns:** `int` - Nombre de paires créées

**Exemple:**
```python
count = manager.generate_from_file_list(
    file_paths=["/path/video1.mp4", "/path/video2.mp4", "/path/video3.mp4"],
    test_set_name="auto_generated",
    expected="unknown"
)
# Génère 3 paires: (v1,v2), (v1,v3), (v2,v3)
```

---

#### `import_from_pairs_json(json_path, test_set_name=None)`
Importe des paires depuis un fichier pairs.json (format legacy).

**Paramètres:**
- `json_path` (str): Chemin du fichier pairs.json
- `test_set_name` (str, optional): Nom du test set (utilise nom fichier si None)

**Returns:** `int` - Nombre de paires importées

**Format JSON attendu:**
```json
[
    {
        "short": "/path/to/video1.mp4",
        "long": "/path/to/video2.mp4",
        "expected": "positive",
        "start": 45.0,
        "duration": 120.0,
        "sequence_score": 95.0,
        "preference": "notes optionnelles"
    }
]
```

---

#### `export_to_pairs_json(test_set_name, json_path)`
Exporte un test set vers un fichier pairs.json.

**Paramètres:**
- `test_set_name` (str): Nom du test set
- `json_path` (str): Chemin de destination

**Returns:** None

---

#### `get_stats(test_set_name='default')`
Statistiques sur un test set.

**Paramètres:**
- `test_set_name` (str): Nom du test set (défaut: 'default')

**Returns:** `Dict` - {total, positives, negatives, unknowns}

---

### BenchmarkManager (`managers/benchmark_manager.py`)

Gestionnaire pour les benchmarks et leurs résultats.

#### `__init__(db_manager)`
**Paramètres:**
- `db_manager` (VideoDatabase): Instance de la base de données

**Returns:** None

---

#### `get_benchmark_run(run_id)`
Récupère les informations d'un run.

**Paramètres:**
- `run_id` (int): ID du run

**Returns:** `Optional[Dict]` - {id, run_label, test_set_name, total_pairs, pipelines_count, created_at, completed_at, status} ou None

---

#### `get_benchmark_results(run_id)`
Récupère tous les résultats d'un run.

**Paramètres:**
- `run_id` (int): ID du run

**Returns:** `List[Dict]` - Liste de résultats par pipeline, triés par f1_score DESC

**Structure du résultat:**
```python
{
    'pipeline_name': str,
    'pipeline_config': Dict,
    'tp': int,              # True Positives
    'fp': int,              # False Positives
    'tn': int,              # True Negatives
    'fn': int,              # False Negatives
    'precision': float,     # En %
    'recall': float,        # En %
    'f1_score': float,      # En %
    'total_time': float,    # En secondes
    'per_pair_results': List[Dict]
}
```

---

#### `list_benchmark_runs(limit=20)`
Liste les runs récents.

**Paramètres:**
- `limit` (int): Nombre maximum de runs à retourner (défaut: 20)

**Returns:** `List[Dict]` - Liste de runs triés par date DESC

---

#### `delete_benchmark_run(run_id)`
Supprime un run (et tous ses résultats via CASCADE).

**Paramètres:**
- `run_id` (int): ID du run

**Returns:** `bool` - True si suppression réussie

---

### BenchmarkRunner (`managers/benchmark_manager.py`)

Worker thread pour exécuter un benchmark batch (hérite de QThread).

#### Signals

- `pipeline_progress(int, int, str)`: (current_pipeline, total_pipelines, pipeline_name)
- `pair_progress(int, int, str, str)`: (current_pair, total_pairs, video1, video2)
- `pipeline_completed(str, dict)`: (pipeline_name, results_dict)
- `finished(int)`: (benchmark_run_id)
- `error(str)`: (error_msg)

---

#### `__init__(db_manager, test_pairs, pipeline_configs, run_label)`
**Paramètres:**
- `db_manager` (VideoDatabase): Instance de la base de données
- `test_pairs` (List[Dict]): Liste de paires de test
- `pipeline_configs` (List[Dict]): Liste de configs pipeline
- `run_label` (str): Label du run

**Returns:** None

**Exemple:**
```python
runner = BenchmarkRunner(
    db_manager=db,
    test_pairs=test_set_manager.get_test_set("mon_test_set"),
    pipeline_configs=[
        pipeline_manager.get_protocol_config("balanced"),
        pipeline_manager.get_protocol_config("high_precision")
    ],
    run_label="Comparaison balanced vs high_precision"
)
runner.pipeline_progress.connect(on_pipeline_progress)
runner.finished.connect(on_finished)
runner.start()
```

---

#### `stop()`
Arrête le benchmark.

**Paramètres:** Aucun

**Returns:** None

---

#### `run()`
Exécute le benchmark batch (méthode QThread, ne pas appeler directement).

**Paramètres:** Aucun

**Returns:** None

---

## 🖼️ UI WIDGETS

### PipelineEditorWidget (`ui/benchmark_widgets.py`)

Widget pour créer et éditer des pipelines.

#### Signals

- `pipeline_saved(str)`: Émis quand un pipeline est sauvegardé (pipeline_name)

---

#### `__init__(pipeline_manager)`
**Paramètres:**
- `pipeline_manager` (PipelineManager): Instance du gestionnaire

**Returns:** None

---

### TestSetEditorWidget (`ui/benchmark_widgets.py`)

Widget pour gérer les test sets.

#### Signals

- `test_set_changed(str)`: Émis quand le test set change (test_set_name)

---

#### `__init__(test_set_manager)`
**Paramètres:**
- `test_set_manager` (TestSetManager): Instance du gestionnaire

**Returns:** None

---

### BenchmarkBatchWidget (`ui/benchmark_widgets.py`)

Widget pour exécuter des benchmarks batch.

#### Signals

- `benchmark_finished(int)`: Émis quand le benchmark est terminé (run_id)

---

#### `__init__(benchmark_manager, pipeline_manager, test_set_manager, db_manager)`
**Paramètres:**
- `benchmark_manager` (BenchmarkManager): Instance du gestionnaire
- `pipeline_manager` (PipelineManager): Instance du gestionnaire
- `test_set_manager` (TestSetManager): Instance du gestionnaire
- `db_manager` (VideoDatabase): Instance de la base de données

**Returns:** None

---

### BenchmarkResultsWidget (`ui/benchmark_widgets.py`)

Widget pour afficher les résultats comparatifs.

#### `__init__(benchmark_manager)`
**Paramètres:**
- `benchmark_manager` (BenchmarkManager): Instance du gestionnaire

**Returns:** None

---

### BenchmarkTabWidget (`ui/benchmark_widgets.py`)

Widget principal contenant tous les widgets de benchmark dans des onglets.

#### `__init__(db_manager)`
**Paramètres:**
- `db_manager` (VideoDatabase): Instance de la base de données

**Returns:** None

**Exemple d'utilisation:**
```python
# Dans main_window.py ou panels.py
benchmark_tab = BenchmarkTabWidget(self.db)
layout.addWidget(benchmark_tab)

# Accès aux widgets individuels
benchmark_tab.pipeline_widget  # PipelineEditorWidget
benchmark_tab.test_set_widget  # TestSetEditorWidget
benchmark_tab.benchmark_widget # BenchmarkBatchWidget
benchmark_tab.results_widget   # BenchmarkResultsWidget
```

---

## 💾 BASE DE DONNÉES

### Tables du Système de Benchmark

#### `saved_pipelines`
```sql
CREATE TABLE saved_pipelines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    mode TEXT NOT NULL,                -- 'filtering', 'weighting', 'hybrid'
    methods_json TEXT NOT NULL,        -- JSON array des méthodes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    use_count INTEGER DEFAULT 0
)
```

---

#### `test_pairs`
```sql
CREATE TABLE test_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video1_path TEXT NOT NULL,
    video2_path TEXT NOT NULL,
    expected TEXT NOT NULL CHECK(expected IN ('positive', 'negative', 'unknown')),
    start_time REAL DEFAULT 0.0,
    duration REAL,
    sequence_score REAL DEFAULT 100.0,
    notes TEXT,
    test_set_name TEXT DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(video1_path, video2_path, test_set_name)
)
```

---

#### `benchmark_runs`
```sql
CREATE TABLE benchmark_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_label TEXT NOT NULL,
    test_set_name TEXT NOT NULL,
    total_pairs INTEGER NOT NULL,
    pipelines_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'running'      -- 'running', 'completed'
)
```

---

#### `benchmark_results`
```sql
CREATE TABLE benchmark_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    benchmark_run_id INTEGER NOT NULL,
    pipeline_name TEXT NOT NULL,
    pipeline_config_json TEXT NOT NULL,
    tp INTEGER DEFAULT 0,              -- True Positives
    fp INTEGER DEFAULT 0,              -- False Positives
    tn INTEGER DEFAULT 0,              -- True Negatives
    fn INTEGER DEFAULT 0,              -- False Negatives
    precision REAL,                    -- En %
    recall REAL,                       -- En %
    f1_score REAL,                     -- En %
    total_time REAL,                   -- En secondes
    per_pair_results_json TEXT,        -- JSON détaillé par paire
    FOREIGN KEY (benchmark_run_id) REFERENCES benchmark_runs(id) ON DELETE CASCADE
)
```

---

## 📊 PROTOCOLES PRÉDÉFINIS

### Liste des Protocoles

1. **anti_fp** - Anti-Faux Positifs
   - Mode: filtering
   - Seuils: 92-97%
   - Méthodes: color_histogram, motion_analysis, dct_coefficients, strategy3

2. **balanced** - Équilibré
   - Mode: filtering
   - Seuils: 85-90%
   - Méthodes: color_histogram, motion_analysis, dct_coefficients, strategy3

3. **high_precision** - Haute Précision
   - Mode: hybrid
   - Seuils: 90-98%
   - Méthodes: color_histogram, edge_pattern, motion_analysis, dct_coefficients, ssim, strategy3

4. **fast** - Rapide
   - Mode: filtering
   - Seuils: 75-85%
   - Méthodes: color_histogram, dct_coefficients, strategy3

5. **dct_only** - DCT Seulement
   - Mode: filtering
   - Méthodes: dct_coefficients uniquement

6. **motion_only** - Motion Seulement
   - Mode: filtering
   - Méthodes: motion_analysis uniquement

7. **weighted_consensus** - Consensus Pondéré
   - Mode: weighting
   - Méthodes: color_histogram, edge_pattern, motion_analysis, dct_coefficients, ssim

8. **re_encoded_specialist** - Spécialiste Réencodage
   - Mode: filtering
   - Seuils: 68-88%
   - Méthodes: dct_coefficients, motion_analysis, strategy3

9. **ultra_permissive** - Ultra Permissif
   - Mode: weighting
   - Seuils: 60-70%
   - Méthodes: color_histogram, motion_analysis, dct_coefficients

10. **hybrid_conservative** - Hybride Conservateur
    - Mode: hybrid
    - Seuils: 80-85%
    - Méthodes: color_histogram, motion_analysis, dct_coefficients, strategy3

---

## 📈 MÉTRIQUES DE BENCHMARK

### Calcul des Métriques

```python
# True Positive (TP): Paire positive correctement détectée
if expected == 'positive' and accepted:
    tp += 1

# False Negative (FN): Paire positive manquée
if expected == 'positive' and not accepted:
    fn += 1

# False Positive (FP): Paire négative incorrectement détectée
if expected == 'negative' and accepted:
    fp += 1

# True Negative (TN): Paire négative correctement rejetée
if expected == 'negative' and not accepted:
    tn += 1

# Precision = TP / (TP + FP) * 100
precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0.0

# Recall = TP / (TP + FN) * 100
recall = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0.0

# F1-Score = 2 * (Precision * Recall) / (Precision + Recall)
f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
```

---

## 🔧 EXEMPLES D'UTILISATION COMPLÈTE

### Créer un Benchmark Complet

```python
from src.plugins.duplicate_finder.managers import (
    PipelineManager, TestSetManager, BenchmarkManager, BenchmarkRunner
)

# Initialiser les managers
pipeline_mgr = PipelineManager(db_manager)
test_set_mgr = TestSetManager(db_manager)
benchmark_mgr = BenchmarkManager(db_manager)

# 1. Créer un test set
test_set_mgr.import_from_pairs_json("my_pairs.json", "mon_test_set")

# Ou générer depuis une liste de fichiers
files = ["/path/video1.mp4", "/path/video2.mp4", "/path/video3.mp4"]
test_set_mgr.generate_from_file_list(files, "auto_test_set")

# 2. Sélectionner des pipelines à tester
pipelines = [
    pipeline_mgr.get_protocol_config("balanced"),
    pipeline_mgr.get_protocol_config("high_precision"),
    pipeline_mgr.get_protocol_config("dct_only")
]

# 3. Exécuter le benchmark
test_pairs = test_set_mgr.get_test_set("mon_test_set")

runner = BenchmarkRunner(
    db_manager=db_manager,
    test_pairs=test_pairs,
    pipeline_configs=pipelines,
    run_label="Test comparatif v1.0"
)

# Connecter les signaux
runner.pipeline_progress.connect(
    lambda curr, total, name: print(f"Pipeline {curr}/{total}: {name}")
)

runner.finished.connect(
    lambda run_id: print(f"Benchmark terminé! Run ID: {run_id}")
)

# Démarrer
runner.start()

# 4. Récupérer les résultats
# (après que runner.finished soit émis)
results = benchmark_mgr.get_benchmark_results(run_id)
for result in results:
    print(f"{result['pipeline_name']}: F1={result['f1_score']:.2f}%")
```

---

## 🔄 FLUX DE TRAVAIL TYPIQUE

1. **Préparation**:
   - Importer ou créer un test set avec `TestSetManager`
   - Marquer les paires comme positive/negative selon la ground truth

2. **Configuration**:
   - Choisir les pipelines à tester (protocoles prédéfinis ou personnalisés)
   - Optionnel: créer des pipelines custom avec `PipelineManager`

3. **Exécution**:
   - Créer un `BenchmarkRunner` avec les test pairs et pipelines
   - Connecter les signaux pour suivre la progression
   - Lancer avec `runner.start()`

4. **Analyse**:
   - Récupérer les résultats avec `BenchmarkManager.get_benchmark_results()`
   - Comparer les métriques (Precision, Recall, F1, Temps)
   - Exporter les résultats si nécessaire

5. **Itération**:
   - Ajuster les pipelines selon les résultats
   - Re-tester avec de nouveaux test sets
   - Historique conservé dans la DB

---

**Fin du document - Version 2025-12-07**
