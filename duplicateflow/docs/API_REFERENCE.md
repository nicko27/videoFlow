# 📘 API Reference - DuplicateFlow

**Version**: 0.1.0 (Phase 1 Complete)
**Dernière mise à jour**: 2025-12-20

---

## Table des Matières

- [Core Interfaces](#core-interfaces)
- [Core Models](#core-models)
- [Core Services](#core-services)
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

- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Developer Guide**: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Phase 1 Complete**: [PHASE1_COMPLETE_SUMMARY.md](PHASE1_COMPLETE_SUMMARY.md)

---

**Dernière mise à jour**: 2025-12-20
**Version**: 0.1.0 (Phase 1 Complete)
