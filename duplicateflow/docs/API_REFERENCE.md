# 📘 API Reference - DuplicateFlow

**Version**: 0.9.2 (Phases 1-10D Complete)
**Dernière mise à jour**: 2025-12-21

---

## Table des Matières

- [Core Interfaces](#core-interfaces)
- [Core Models](#core-models)
- [Core Services](#core-services)
- [Processing Modules](#processing-modules)
- [Storage Modules](#storage-modules)
- [CLI Adapters](#cli-adapters)
- [CLI Commands](#cli-commands)

---

## Core Interfaces

### `IProgressReporter`

Interface pour rapporter la progression d'une tâche.

**Module**: `duplicateflow.core.interfaces.i_progress_reporter`

#### Méthodes

##### `start_phase(phase_id, total, message="")`

Démarre une nouvelle phase de progression.

**Paramètres**:
- `phase_id` (str): Identifiant unique de la phase
- `total` (int): Nombre total d'éléments
- `message` (str, optional): Message à afficher

**Exemple**:
```python
progress.start_phase("scan", total=100, message="Scanning videos...")
```

##### `update(phase_id, current, message="")`

Met à jour la progression.

**Paramètres**:
- `phase_id` (str): Identifiant de la phase
- `current` (int): Progression actuelle
- `message` (str, optional): Message à afficher

**Exemple**:
```python
progress.update("scan", current=50, message="Found 50 videos...")
```

##### `finish_phase(phase_id, message="")`

Termine une phase.

**Paramètres**:
- `phase_id` (str): Identifiant de la phase
- `message` (str, optional): Message final

**Exemple**:
```python
progress.finish_phase("scan", message="Scan complete!")
```

#### Implémentations

- `NullProgressReporter` - Ne fait rien (tests)
- `RichProgressReporter` - Affichage Rich terminal (CLI)

---

### `IUIAdapter`

Interface pour les interactions utilisateur.

**Module**: `duplicateflow.core.interfaces.i_ui_adapter`

#### Méthodes

##### `display_message(message, message_type=MessageType.INFO)`

Affiche un message à l'utilisateur.

**Paramètres**:
- `message` (str): Message à afficher
- `message_type` (MessageType): Type de message

**Types de messages**:
- `MessageType.INFO` - Information
- `MessageType.SUCCESS` - Succès
- `MessageType.WARNING` - Avertissement
- `MessageType.ERROR` - Erreur

**Exemple**:
```python
ui.display_message("Scan complete!", MessageType.SUCCESS)
ui.display_message("Warning: File not found", MessageType.WARNING)
```

##### `ask_question(question, choices)`

Pose une question avec choix multiples.

**Paramètres**:
- `question` (str): Question à poser
- `choices` (list[str]): Liste des choix possibles

**Retourne**: `str` - Choix sélectionné

**Exemple**:
```python
pipeline = ui.ask_question(
    "Choose pipeline:",
    choices=["fast", "balanced", "thorough"]
)
```

##### `confirm(question)`

Demande une confirmation oui/non.

**Paramètres**:
- `question` (str): Question à poser

**Retourne**: `bool` - True si oui, False si non

**Exemple**:
```python
if ui.confirm("Delete duplicates?"):
    delete_videos()
```

#### Implémentations

- `NullUIAdapter` - Réponses par défaut (tests)
- `RichUIAdapter` - Prompts Rich terminal (CLI)

---

## Core Models

### `VideoFormat`

Enum des formats vidéo supportés.

**Module**: `duplicateflow.core.models.scan`

#### Valeurs

```python
class VideoFormat(str, Enum):
    MP4 = "mp4"
    MKV = "mkv"
    AVI = "avi"
    MOV = "mov"
    WMV = "wmv"
    FLV = "flv"
    WEBM = "webm"
    M4V = "m4v"
    MPG = "mpg"
    MPEG = "mpeg"
    UNKNOWN = "unknown"
```

#### Méthodes

##### `from_extension(ext)`

Convertit une extension en VideoFormat.

**Paramètres**:
- `ext` (str): Extension (avec ou sans le point)

**Retourne**: `VideoFormat`

**Exemple**:
```python
fmt = VideoFormat.from_extension(".mp4")  # VideoFormat.MP4
fmt = VideoFormat.from_extension("MKV")   # VideoFormat.MKV
fmt = VideoFormat.from_extension(".xyz")  # VideoFormat.UNKNOWN
```

---

### `VideoFile`

Représentation d'un fichier vidéo.

**Module**: `duplicateflow.core.models.scan`

#### Attributs

| Attribut | Type | Description |
|----------|------|-------------|
| `path` | Path | Chemin complet du fichier |
| `size_bytes` | int | Taille en bytes |
| `format` | VideoFormat | Format vidéo |
| `created_at` | datetime | Date de création |
| `modified_at` | datetime | Date de modification |
| `duration_seconds` | float, optional | Durée en secondes |
| `width` | int, optional | Largeur en pixels |
| `height` | int, optional | Hauteur en pixels |
| `codec` | str, optional | Codec vidéo |
| `metadata` | dict | Métadonnées additionnelles |

#### Propriétés

##### `filename`

Nom du fichier.

**Type**: `str`

**Exemple**:
```python
video.filename  # "movie.mp4"
```

##### `extension`

Extension du fichier.

**Type**: `str`

**Exemple**:
```python
video.extension  # ".mp4"
```

##### `size_mb`

Taille en megabytes.

**Type**: `float`

**Exemple**:
```python
video.size_mb  # 150.25
```

##### `size_gb`

Taille en gigabytes.

**Type**: `float`

**Exemple**:
```python
video.size_gb  # 0.15
```

##### `resolution`

Résolution (largeur x hauteur).

**Type**: `str | None`

**Exemple**:
```python
video.resolution  # "1920x1080" ou None
```

##### `has_video_properties`

Vérifie si les propriétés vidéo sont disponibles.

**Type**: `bool`

**Exemple**:
```python
if video.has_video_properties:
    print(f"Duration: {video.duration_seconds}s")
```

#### Méthodes

##### `from_path(path)`

Crée un VideoFile depuis un chemin de fichier.

**Paramètres**:
- `path` (Path): Chemin du fichier

**Retourne**: `VideoFile`

**Exemple**:
```python
from pathlib import Path

video = VideoFile.from_path(Path("/videos/movie.mp4"))
print(f"{video.filename}: {video.size_mb:.2f} MB")
```

---

### `ScanResult`

Résultat d'un scan de répertoire.

**Module**: `duplicateflow.core.models.scan`

#### Attributs

| Attribut | Type | Description |
|----------|------|-------------|
| `videos` | list[VideoFile] | Vidéos trouvées |
| `root_path` | Path | Répertoire scanné |
| `timestamp` | datetime | Date/heure du scan |
| `scan_duration_seconds` | float | Durée du scan |
| `directories_scanned` | int | Nombre de répertoires scannés |
| `total_files_checked` | int | Nombre total de fichiers vérifiés |
| `errors` | list[str] | Erreurs rencontrées |
| `metadata` | dict | Métadonnées additionnelles |

#### Propriétés

##### `video_count`

Nombre de vidéos trouvées.

**Type**: `int`

##### `total_size_bytes`

Taille totale en bytes.

**Type**: `int`

##### `total_size_mb`

Taille totale en megabytes.

**Type**: `float`

##### `total_size_gb`

Taille totale en gigabytes.

**Type**: `float`

##### `has_errors`

Indique si des erreurs sont survenues.

**Type**: `bool`

##### `videos_by_format`

Vidéos groupées par format.

**Type**: `dict[VideoFormat, list[VideoFile]]`

**Exemple**:
```python
for fmt, videos in result.videos_by_format.items():
    print(f"{fmt}: {len(videos)} videos")
```

#### Méthodes

##### `get_format_counts()`

Compte les vidéos par format.

**Retourne**: `dict[str, int]` - Format → Count

**Exemple**:
```python
counts = result.get_format_counts()
# {'mp4': 25, 'mkv': 12, 'avi': 5}
```

##### `to_dict()`

Convertit en dictionnaire pour export.

**Retourne**: `dict`

**Exemple**:
```python
data = result.to_dict()
print(data['statistics']['video_count'])
```

##### `to_json(indent=2)`

Export en format JSON.

**Paramètres**:
- `indent` (int, optional): Indentation (default: 2)

**Retourne**: `str` - JSON string

**Exemple**:
```python
json_str = result.to_json()
with open('results.json', 'w') as f:
    f.write(json_str)
```

##### `to_csv_rows()`

Export en format CSV (lignes).

**Retourne**: `list[dict]` - Liste de dictionnaires (une vidéo par ligne)

**Exemple**:
```python
import csv

rows = result.to_csv_rows()
with open('results.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
```

---

### `DuplicateGroup`

Groupe de vidéos dupliquées/similaires.

**Module**: `duplicateflow.core.models.scan`

#### Attributs

| Attribut | Type | Description |
|----------|------|-------------|
| `videos` | list[VideoFile] | Vidéos du groupe |
| `similarity_score` | float | Score de similarité (0-100) |
| `algorithm` | str | Algorithme utilisé |
| `metadata` | dict | Métadonnées additionnelles |

#### Propriétés

##### `size`

Nombre de vidéos dans le groupe.

**Type**: `int`

##### `total_size_bytes`

Taille totale du groupe en bytes.

**Type**: `int`

##### `total_size_mb`

Taille totale du groupe en megabytes.

**Type**: `float`

##### `potential_savings_bytes`

Espace récupérable en gardant 1 vidéo.

**Type**: `int`

**Exemple**:
```python
group = DuplicateGroup(videos=[v1, v2, v3], ...)
print(f"Savings: {group.potential_savings_gb:.2f} GB")
```

---

## Core Services

### `ScanService`

Service de scan de répertoires pour fichiers vidéo.

**Module**: `duplicateflow.core.services.scan_service`

#### Constantes

##### `SUPPORTED_VIDEO_EXTENSIONS`

Extensions vidéo supportées.

**Type**: `set[str]`

**Valeur**:
```python
{'.mp4', '.mkv', '.avi', '.mov', '.wmv',
 '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}
```

#### Constructeur

```python
ScanService(progress: IProgressReporter, ui: IUIAdapter)
```

**Paramètres**:
- `progress`: Reporter de progression
- `ui`: Adaptateur UI

**Exemple**:
```python
from duplicateflow.core.services import ScanService
from duplicateflow.core.interfaces import NullProgressReporter, NullUIAdapter

service = ScanService(
    progress=NullProgressReporter(),
    ui=NullUIAdapter()
)
```

#### Méthodes

##### `scan_directory(root_path, recursive=True, follow_symlinks=False)`

Scanne un répertoire pour les vidéos.

**Paramètres**:
- `root_path` (Path): Répertoire à scanner
- `recursive` (bool, optional): Scanner récursivement (default: True)
- `follow_symlinks` (bool, optional): Suivre les liens symboliques (default: False)

**Retourne**: `ScanResult`

**Exceptions**:
- `ValueError`: Si root_path n'existe pas ou n'est pas un répertoire

**Exemple**:
```python
from pathlib import Path

result = service.scan_directory(
    Path("/videos"),
    recursive=True,
    follow_symlinks=False
)

print(f"Found {result.video_count} videos")
```

##### `filter_by_format(result, formats)`

Filtre les vidéos par format.

**Paramètres**:
- `result` (ScanResult): Résultat du scan
- `formats` (list[VideoFormat]): Formats à garder

**Retourne**: `list[VideoFile]`

**Exemple**:
```python
# Garder seulement MP4 et MKV
videos = service.filter_by_format(
    result,
    [VideoFormat.MP4, VideoFormat.MKV]
)
```

##### `filter_by_size(result, min_mb=None, max_mb=None)`

Filtre les vidéos par taille.

**Paramètres**:
- `result` (ScanResult): Résultat du scan
- `min_mb` (float, optional): Taille minimale en MB
- `max_mb` (float, optional): Taille maximale en MB

**Retourne**: `list[VideoFile]`

**Exemple**:
```python
# Vidéos entre 100 MB et 5 GB
videos = service.filter_by_size(result, min_mb=100, max_mb=5000)

# Vidéos >1 GB
big_videos = service.filter_by_size(result, min_mb=1000)

# Vidéos <100 MB
small_videos = service.filter_by_size(result, max_mb=100)
```

##### `get_statistics(result)`

Calcule les statistiques détaillées.

**Paramètres**:
- `result` (ScanResult): Résultat du scan

**Retourne**: `dict` - Statistiques

**Exemple**:
```python
stats = service.get_statistics(result)

print(f"Total videos: {stats['total_videos']}")
print(f"Total size: {stats['total_size_gb']:.2f} GB")
print(f"By format: {stats['format_counts']}")
```

**Structure du retour**:
```python
{
    'total_videos': int,
    'total_size_mb': float,
    'total_size_gb': float,
    'directories_scanned': int,
    'files_checked': int,
    'scan_duration_seconds': float,
    'errors': int,
    'format_counts': dict[str, int]
}
```

---

## Processing Modules

### `ParallelWindowSearch`

Recherche parallèle par fenêtres temporelles pour détecter des sous-séquences similaires.

**Module**: `duplicateflow.processing.parallel_search`
**Tests**: 26 tests, 95% coverage

#### Constructeur

```python
ParallelWindowSearch(
    algorithm: BaseAlgorithm,
    window_seconds: float = 30.0,
    step_seconds: float = 10.0,
    threshold: float = 70.0,
    max_workers: int = 4
)
```

**Paramètres**:
- `algorithm`: Algorithme de comparaison
- `window_seconds`: Taille de fenêtre temporelle (défaut: 30s)
- `step_seconds`: Pas de déplacement (défaut: 10s)
- `threshold`: Seuil de similarité (défaut: 70.0)
- `max_workers`: Nombre de workers parallèles (défaut: 4)

**Exemple**:
```python
from duplicateflow.processing import ParallelWindowSearch
from duplicateflow.algorithms import FrameHashAlgorithm

algo = FrameHashAlgorithm()
search = ParallelWindowSearch(
    algorithm=algo,
    window_seconds=30.0,
    step_seconds=10.0,
    threshold=75.0
)

result = search.search(
    reference_video="video1.mp4",
    query_video="video2.mp4"
)
```

---

### `CascadeFilter`

Filtrage en cascade multi-étapes pour rejet précoce des paires non-similaires.

**Module**: `duplicateflow.processing.cascade_filter`
**Tests**: 24 tests, 95% coverage

#### Constructeur

```python
CascadeFilter(
    stages: list[dict],
    global_threshold: float = 70.0
)
```

**Paramètres**:
- `stages`: Liste des étapes de filtrage avec algorithmes
- `global_threshold`: Seuil global final

**Exemple**:
```python
from duplicateflow.processing import CascadeFilter

cascade = CascadeFilter(
    stages=[
        {'algorithm': 'frame_hash', 'threshold': 80.0, 'fast': True},
        {'algorithm': 'color_histogram', 'threshold': 75.0},
        {'algorithm': 'ssim', 'threshold': 70.0}
    ],
    global_threshold=75.0
)

# Rejette rapidement si frame_hash < 80%
# Continue avec color_histogram si passé
# Validation finale avec SSIM
```

---

### `BatchProcessor`

Traitement par lots avec parallélisation et checkpointing.

**Module**: `duplicateflow.processing.batch_processor`
**Tests**: 15 tests, 92% coverage

#### Méthodes

##### `process_batch(videos, strategy='standard')`

Traite un lot de vidéos.

**Paramètres**:
- `videos` (list[str]): Liste de chemins vidéo
- `strategy` (str): Stratégie de traitement ('standard' ou 'parallel')

**Retourne**: `list[BatchResult]`

**Exemple**:
```python
from duplicateflow.processing import BatchProcessor

processor = BatchProcessor(max_workers=4)

videos = ["video1.mp4", "video2.mp4", "video3.mp4"]
results = processor.process_batch(videos)

# Export CSV
processor.export_csv(results, "results.csv")
```

---

## Storage Modules

### `StorageManager`

Interface unifiée pour toutes les opérations de stockage et cache.

**Module**: `duplicateflow.storage.storage_manager`
**Tests**: 30 tests, **100% coverage** ✨

#### Constructeur

```python
StorageManager(
    cache_dir: str = "~/.duplicateflow/cache",
    max_memory_items: int = 2000
)
```

**Exemple**:
```python
from duplicateflow.storage import StorageManager

storage = StorageManager(
    cache_dir="~/.duplicateflow/cache",
    max_memory_items=2000
)

# Hash de fichier (avec cache)
hash1 = storage.get_file_hash("/path/to/video.mp4")

# Vérifier si fichiers identiques
if storage.are_files_identical(file1, file2):
    print("Obvious duplicates!")

# Résultat de comparaison en cache
result = storage.get_cached_result(
    file1, file2, "frame_hash", {'threshold': 70.0}
)

if result is None:
    # Calculer et stocker
    result = algorithm.compare(file1, file2)
    storage.store_result(
        file1, file2, "frame_hash",
        {'threshold': 70.0}, result
    )

# Statistiques
stats = storage.get_stats()
print(f"Hit rate: {stats['result_cache']['hit_rate']:.1f}%")
```

---

### `ResultCache`

Cache persistant (SQLite + mémoire) pour résultats de comparaison d'algorithmes.

**Module**: `duplicateflow.storage.result_cache`
**Tests**: 28 tests, 98% coverage

#### Constructeur

```python
ResultCache(db_path: str = "~/.duplicateflow/results.db")
```

#### Méthodes

##### `store(file1_hash, file2_hash, algorithm, params, result)`

Stocke un résultat de comparaison.

**Paramètres**:
- `file1_hash` (str): Hash MD5 du premier fichier
- `file2_hash` (str): Hash MD5 du second fichier
- `algorithm` (str): Nom de l'algorithme
- `params` (dict): Paramètres de l'algorithme
- `result` (dict): Résultat de comparaison

**Exemple**:
```python
from duplicateflow.storage import ResultCache

cache = ResultCache()

cache.store(
    file1_hash="abc123",
    file2_hash="def456",
    algorithm="frame_hash",
    params={'threshold': 70.0},
    result={
        'similarity': 0.85,
        'accepted': True,
        'metadata': {'frames_compared': 100}
    }
)

# Récupération (ordre des fichiers n'a pas d'importance)
result = cache.get("def456", "abc123", "frame_hash", {'threshold': 70.0})
```

---

### `FeatureCache`

Cache persistant pour features extraites (fingerprints, histogrammes, etc.).

**Module**: `duplicateflow.storage.feature_cache`
**Tests**: 31 tests, **100% coverage** ✨

#### Constructeur

```python
FeatureCache(db_path: str = "~/.duplicateflow/features.db")
```

#### Méthodes

##### `store(file_hash, algorithm, params, features, metadata=None)`

Stocke des features extraites.

**Paramètres**:
- `file_hash` (str): Hash MD5 du fichier
- `algorithm` (str): Nom de l'algorithme
- `params` (dict): Paramètres d'extraction
- `features` (Any): Features (sérialisées avec pickle)
- `metadata` (dict, optional): Métadonnées (stockées en JSON)

**Exemple**:
```python
from duplicateflow.storage import FeatureCache

cache = FeatureCache()

# Stocker features complexes
features = {
    'fingerprints': {
        'hash_1': [1, 2, 3, 4, 5],
        'hash_2': [6, 7, 8, 9, 10]
    },
    'histograms': [[0.1, 0.2], [0.3, 0.4]]
}

cache.store(
    file_hash="abc123",
    algorithm="audio_fingerprint",
    params={'sr': 11025, 'n_fft': 4096},
    features=features,
    metadata={'extraction_time_ms': 250.5}
)

# Récupération
cached = cache.get("abc123", "audio_fingerprint", {'sr': 11025, 'n_fft': 4096})
```

---

### `PipelineStore`

Stockage persistant de configurations de pipelines personnalisés.

**Module**: `duplicateflow.storage.pipeline_store`
**Tests**: 35 tests, **100% coverage** ✨

#### Constructeur

```python
PipelineStore(db_path: str = "~/.duplicateflow/pipelines.db")
```

#### Méthodes

##### `save(name, config, description="", category="custom", overwrite=False)`

Sauvegarde une configuration de pipeline.

**Paramètres**:
- `name` (str): Nom unique du pipeline
- `config` (dict): Configuration complète
- `description` (str): Description
- `category` (str): Catégorie (custom, duplicates, scenes, etc.)
- `overwrite` (bool): Écraser si existe

**Retourne**: `int` - ID du pipeline

**Exemple**:
```python
from duplicateflow.storage import PipelineStore

store = PipelineStore()

config = {
    'steps': [
        {'algorithm': 'frame_hash', 'weight': 0.6, 'threshold': 80},
        {'algorithm': 'color_histogram', 'weight': 0.4, 'threshold': 75}
    ],
    'global_threshold': 75.0,
    'pre_validators': [
        {
            'type': 'LengthValidator',
            'config': {'tolerance_percent': 5.0}
        }
    ]
}

# Sauvegarder
pipeline_id = store.save(
    name="my_fast_pipeline",
    config=config,
    description="Pipeline rapide pour duplicatas",
    category="duplicates"
)

# Charger
loaded_config = store.load("my_fast_pipeline")

# Lister
pipelines = store.list(category="duplicates")

# Statistiques d'usage
stats = store.get_stats("my_fast_pipeline")
print(f"Used {stats['usage_count']} times")

# Export/Import
store.export_preset("my_fast_pipeline", "presets/custom.json")
store.import_preset("presets/other.json", name="imported")
```

---

## CLI Adapters

### `RichProgressReporter`

Implémentation Rich de IProgressReporter.

**Module**: `duplicateflow.cli.adapters.rich_progress`

#### Constructeur

```python
RichProgressReporter(console: Console)
```

**Paramètres**:
- `console`: Instance de Rich Console

**Exemple**:
```python
from rich.console import Console
from duplicateflow.cli.adapters import RichProgressReporter

console = Console()
with RichProgressReporter(console) as progress:
    progress.start_phase("scan", 100, "Scanning...")
    # ... work
    progress.finish_phase("scan", "Done!")
```

**Note**: Utilise un context manager (`with`) pour gérer le lifecycle.

---

### `RichUIAdapter`

Implémentation Rich de IUIAdapter.

**Module**: `duplicateflow.cli.adapters.rich_ui`

#### Constructeur

```python
RichUIAdapter(console: Console)
```

**Paramètres**:
- `console`: Instance de Rich Console

**Exemple**:
```python
from rich.console import Console
from duplicateflow.cli.adapters import RichUIAdapter
from duplicateflow.core.interfaces import MessageType

console = Console()
ui = RichUIAdapter(console)

ui.display_message("Processing...", MessageType.INFO)
ui.display_message("Success!", MessageType.SUCCESS)

if ui.confirm("Continue?"):
    print("User confirmed")
```

---

## CLI Commands

### `scan`

Commande de scan de répertoires.

**Module**: `duplicateflow.cli.commands.scan_command`

#### Fonctions

##### `create_scan_parser(subparsers)`

Crée le parser argparse pour la commande scan.

**Paramètres**:
- `subparsers`: Subparsers d'argparse

**Retourne**: `ArgumentParser`

##### `run_scan_command(args)`

Exécute la commande scan.

**Paramètres**:
- `args`: Arguments parsés (Namespace)

**Retourne**: `int` - Exit code (0 = success, 1 = error, 130 = cancelled)

**Exit codes**:
- `0` - Succès
- `1` - Erreur
- `130` - Annulé par l'utilisateur (Ctrl+C)

---

## Exemples d'Utilisation

### Scan Simple

```python
from pathlib import Path
from duplicateflow.core.services import ScanService
from duplicateflow.core.interfaces import NullProgressReporter, NullUIAdapter

# Créer service
service = ScanService(
    progress=NullProgressReporter(),
    ui=NullUIAdapter()
)

# Scanner
result = service.scan_directory(Path("/videos"))

# Résultats
print(f"Found {result.video_count} videos")
print(f"Total size: {result.total_size_gb:.2f} GB")
```

### Scan avec Rich UI

```python
from pathlib import Path
from rich.console import Console
from duplicateflow.core.services import ScanService
from duplicateflow.cli.adapters import RichProgressReporter, RichUIAdapter

console = Console()

with RichProgressReporter(console) as progress:
    ui = RichUIAdapter(console)
    service = ScanService(progress=progress, ui=ui)

    result = service.scan_directory(Path("/videos"))

    ui.display_message(
        f"Found {result.video_count} videos!",
        MessageType.SUCCESS
    )
```

### Filtrage et Export

```python
from pathlib import Path
from duplicateflow.core.services import ScanService
from duplicateflow.core.models import VideoFormat
from duplicateflow.core.interfaces import NullProgressReporter, NullUIAdapter

service = ScanService(
    progress=NullProgressReporter(),
    ui=NullUIAdapter()
)

# Scan
result = service.scan_directory(Path("/videos"))

# Filtrer MP4 et MKV
videos = service.filter_by_format(
    result,
    [VideoFormat.MP4, VideoFormat.MKV]
)

# Filtrer par taille (>100 MB)
big_videos = service.filter_by_size(result, min_mb=100)

# Export JSON
json_str = result.to_json()
Path("results.json").write_text(json_str)

# Export CSV
import csv
rows = result.to_csv_rows()
with open("results.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
```

---

## Types

### `MessageType`

Types de messages pour UI.

**Module**: `duplicateflow.core.interfaces.i_ui_adapter`

```python
from enum import Enum

class MessageType(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
```

---

## Ressources

### Guides Utilisateur
- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Developer Guide**: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Documentation Index**: [INDEX.md](INDEX.md) - Navigation complète

### Phases de Testing (1-10)
- **Phase 1**: [PHASE1_COMPLETE_SUMMARY.md](PHASE1_COMPLETE_SUMMARY.md) - Architecture Clean + CLI scan (160 tests, 92%)
- **Phase 2**: [PHASE2_COMPLETE_SUMMARY.md](PHASE2_COMPLETE_SUMMARY.md) - Tests modèles (95%+)
- **Phase 3**: [PHASE3_COMPLETE_SUMMARY.md](PHASE3_COMPLETE_SUMMARY.md) - Tests d'intégration
- **Phase 4**: [PHASE4_COMPLETE_SUMMARY.md](PHASE4_COMPLETE_SUMMARY.md) - Pipeline Management (41 tests, 94%)
- **Phase 5**: [PHASE5_SERVICE_LAYER_TESTING_COMPLETE.md](PHASE5_SERVICE_LAYER_TESTING_COMPLETE.md) - Service Layer (80 tests, 92-100%)
- **Phase 6**: [PHASE6_CLI_TESTING_SUMMARY.md](PHASE6_CLI_TESTING_SUMMARY.md) - CLI Commands (89 tests, 82.2%)
- **Phase 7**: [PHASE7_COMPLETE_SUMMARY.md](PHASE7_COMPLETE_SUMMARY.md) - Algorithms (471 tests, 60%+)
- **Phase 8**: [PHASE8_COMPLETE_SUMMARY.md](PHASE8_COMPLETE_SUMMARY.md) - Processing & Storage (269 tests, **95% avg, 3 at 100%**)
- **Phase 10**: [PHASE10_FINAL_SUMMARY.md](PHASE10_FINAL_SUMMARY.md) - 🎉 **Algorithms Enhancement Complete (11 algorithms à 67-92%)**
  - **Phase 10A**: [PHASE10_SSIM_ENHANCEMENT.md](PHASE10_SSIM_ENHANCEMENT.md) - SSIM 24% → 92%, frame_hash 36% → 92%
  - **Phase 10B**: [PHASE10B_CONTINUATION_SUMMARY.md](PHASE10B_CONTINUATION_SUMMARY.md) - color_histogram 25% → 89%, color_moments 26% → 91%, dct_coefficients 26% → 91%
  - **Phase 10C**: [PHASE10C_FINAL_SUMMARY.md](PHASE10C_FINAL_SUMMARY.md) - audio_fingerprint 78% → 92%, subsequence_detection 49% → 91%, audio_spectrum 45% → 83%
  - **Phase 10D**: [PHASE10D_FINAL_SUMMARY.md](PHASE10D_FINAL_SUMMARY.md) - feature_matching 43% → 87%, edge_pattern 42% → 92%, motion_analysis 34% → 67%

### Statistiques Globales (Phases 1-10D)
- ✅ **1,320+ tests** créés (+210 depuis Phase 8)
- ✅ **~18,600+ lignes** de code de tests (+2,100 lignes)
- ✅ **Coverage Globale**: ~68% (Models 94%+, Services 92-100%, CLI 82.2%, Processing 93%, Storage 98%, **11 algorithmes à 67-92%**)
- ✅ **11 algorithmes à 67%+** (SSIM 92%, frame_hash 92%, edge_pattern 92%, audio_fingerprint 92%, color_moments 91%, dct 91%, subsequence 91%, color_hist 89%, feature_matching 87%, audio_spectrum 83%, motion_analysis 67%)
- ✅ **6 algorithmes à 90%+**, **10 algorithmes à 83%+**
- ✅ **5 modules storage à 90%+** (3 à 100% parfait: StorageManager, FeatureCache, PipelineStore)
- 🏆 **Phase 10 Complete: 11 algorithmes améliorés, +175 tests vidéo, +49% coverage moyen**

---

**Dernière mise à jour**: 2025-12-21
**Version**: 0.9.2 (Phases 1-10D Complete)
