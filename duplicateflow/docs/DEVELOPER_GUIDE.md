# 🔧 Guide Développeur DuplicateFlow

**Version**: 0.7.0 (Phases 1-7 Complete)
**Dernière mise à jour**: 2025-12-20

---

## 🎯 Vue d'ensemble

Ce guide explique l'architecture de DuplicateFlow, comment elle fonctionne, et comment contribuer au projet.

---

## 🏗️ Architecture

DuplicateFlow utilise une **Clean Architecture** avec séparation stricte des couches.

### Structure Globale

```
duplicateflow/
├── duplicateflow/           # Code source
│   ├── core/               # ✅ LOGIQUE MÉTIER PURE
│   ├── cli/                # ✅ INTERFACE CLI
│   ├── gui/                # ⏳ INTERFACE GUI (future)
│   ├── pipeline/           # Pipelines de détection
│   ├── processing/         # Algorithmes
│   └── storage/            # Persistance
│
└── tests/                  # Tests
    └── unit/
        ├── core/           # Tests core
        └── cli/            # Tests CLI
```

### Principes Architecturaux

#### 1. Séparation des Couches

```
┌─────────────────────────────────────┐
│         Presentation Layer          │
│  (CLI, GUI - Rich, Qt, Web, etc.)  │
└──────────────┬──────────────────────┘
               │ (depends on)
┌──────────────▼──────────────────────┐
│         Business Layer              │
│  (Core - Models, Services, Logic)  │
└──────────────┬──────────────────────┘
               │ (uses)
┌──────────────▼──────────────────────┐
│         Infrastructure              │
│  (Storage, External APIs, etc.)    │
└─────────────────────────────────────┘
```

**Règle d'or**: Le `core` ne dépend JAMAIS de `cli` ou `gui`.

#### 2. Dependency Injection

Toutes les dépendances sont injectées via des interfaces ABC.

**Exemple**:

```python
# ❌ MAUVAIS - Dépendance hard-codée
class ScanService:
    def __init__(self):
        self.progress = RichProgressBar()  # Couplage à Rich!

# ✅ BON - Injection via interface
class ScanService:
    def __init__(
        self,
        progress: IProgressReporter,  # Interface ABC
        ui: IUIAdapter                # Interface ABC
    ):
        self.progress = progress
        self.ui = ui
```

**Avantages**:
- Tests sans dépendances lourdes (Rich, Qt, etc.)
- Changement facile d'implémentation
- Core totalement découplé

---

## 📦 Modules Core

### `core/interfaces/`

Définit les contrats (interfaces ABC) que les implémentations doivent respecter.

#### `IProgressReporter`

Interface pour rapporter la progression.

```python
from abc import ABC, abstractmethod

class IProgressReporter(ABC):
    """Interface pour rapporter la progression d'une tâche."""

    @abstractmethod
    def start_phase(
        self,
        phase_id: str,
        total: int,
        message: str = ""
    ) -> None:
        """Démarre une phase de progression."""
        pass

    @abstractmethod
    def update(
        self,
        phase_id: str,
        current: int,
        message: str = ""
    ) -> None:
        """Met à jour la progression."""
        pass

    @abstractmethod
    def finish_phase(
        self,
        phase_id: str,
        message: str = ""
    ) -> None:
        """Termine une phase."""
        pass
```

**Implémentations**:
- `NullProgressReporter` - Ne fait rien (pour les tests)
- `RichProgressReporter` - Utilise Rich (pour le CLI)
- `QtProgressReporter` - Utilise Qt (future GUI)

#### `IUIAdapter`

Interface pour les interactions UI.

```python
class IUIAdapter(ABC):
    """Interface pour l'interaction UI."""

    @abstractmethod
    def display_message(
        self,
        message: str,
        message_type: MessageType = MessageType.INFO
    ) -> None:
        """Affiche un message."""
        pass

    @abstractmethod
    def ask_question(
        self,
        question: str,
        choices: list[str]
    ) -> str:
        """Pose une question avec choix multiples."""
        pass

    @abstractmethod
    def confirm(self, question: str) -> bool:
        """Demande une confirmation oui/non."""
        pass
```

### `core/models/`

Modèles de données (dataclasses) représentant les entités du domaine.

#### `VideoFormat`

Enum des formats vidéo supportés.

```python
from enum import Enum

class VideoFormat(str, Enum):
    """Formats vidéo supportés."""
    MP4 = "mp4"
    MKV = "mkv"
    AVI = "avi"
    MOV = "mov"
    # ... autres formats

    @staticmethod
    def from_extension(ext: str) -> 'VideoFormat':
        """Convertit une extension en VideoFormat."""
        ext_clean = ext.lower().lstrip('.')
        try:
            return VideoFormat(ext_clean)
        except ValueError:
            return VideoFormat.UNKNOWN
```

#### `VideoFile`

Représentation d'un fichier vidéo.

```python
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

@dataclass
class VideoFile:
    """Représentation d'un fichier vidéo."""

    path: Path
    size_bytes: int
    format: VideoFormat
    created_at: datetime
    modified_at: datetime

    # Propriétés vidéo optionnelles
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    codec: Optional[str] = None

    metadata: dict = field(default_factory=dict)

    @property
    def filename(self) -> str:
        """Nom du fichier."""
        return self.path.name

    @property
    def size_mb(self) -> float:
        """Taille en MB."""
        return self.size_bytes / (1024 * 1024)

    @property
    def resolution(self) -> Optional[str]:
        """Résolution (e.g., '1920x1080')."""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return None

    @classmethod
    def from_path(cls, path: Path) -> 'VideoFile':
        """Crée un VideoFile depuis un chemin."""
        stat = path.stat()
        return cls(
            path=path,
            size_bytes=stat.st_size,
            format=VideoFormat.from_extension(path.suffix),
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime)
        )
```

#### `ScanResult`

Résultat d'un scan de répertoire.

```python
@dataclass
class ScanResult:
    """Résultat d'un scan de répertoire."""

    videos: list[VideoFile]
    root_path: Path
    timestamp: datetime
    scan_duration_seconds: float
    directories_scanned: int
    total_files_checked: int
    errors: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def video_count(self) -> int:
        """Nombre de vidéos trouvées."""
        return len(self.videos)

    @property
    def total_size_gb(self) -> float:
        """Taille totale en GB."""
        return sum(v.size_bytes for v in self.videos) / (1024**3)

    def get_format_counts(self) -> dict[str, int]:
        """Compte les vidéos par format."""
        from collections import Counter
        return dict(Counter(v.format.value for v in self.videos))

    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour export."""
        return {
            'root_path': str(self.root_path),
            'timestamp': self.timestamp.isoformat(),
            'scan_duration_seconds': self.scan_duration_seconds,
            'statistics': {
                'video_count': self.video_count,
                'total_size_gb': round(self.total_size_gb, 2),
                'format_counts': self.get_format_counts()
            },
            'videos': [
                {
                    'path': str(v.path),
                    'filename': v.filename,
                    'size_mb': round(v.size_mb, 2),
                    'format': v.format.value
                }
                for v in self.videos
            ],
            'errors': self.errors
        }

    def to_json(self, indent: int = 2) -> str:
        """Export en JSON."""
        import json
        return json.dumps(self.to_dict(), indent=indent)
```

### `core/services/`

Services métier purs (logique business).

#### `ScanService`

Service de scan de répertoires.

```python
class ScanService:
    """Service de scan de répertoires pour vidéos."""

    SUPPORTED_VIDEO_EXTENSIONS = {
        '.mp4', '.mkv', '.avi', '.mov', '.wmv',
        '.flv', '.webm', '.m4v', '.mpg', '.mpeg'
    }

    def __init__(
        self,
        progress: IProgressReporter,
        ui: IUIAdapter
    ):
        """
        Initialise le service.

        Args:
            progress: Reporter de progression
            ui: Adaptateur UI
        """
        self.progress = progress
        self.ui = ui

    def scan_directory(
        self,
        root_path: Path,
        recursive: bool = True,
        follow_symlinks: bool = False
    ) -> ScanResult:
        """
        Scanne un répertoire pour les vidéos.

        Args:
            root_path: Répertoire à scanner
            recursive: Scanner récursivement
            follow_symlinks: Suivre les liens symboliques

        Returns:
            ScanResult contenant les vidéos trouvées

        Raises:
            ValueError: Si root_path n'existe pas ou n'est pas un répertoire
        """
        import time

        # Validation
        if not root_path.exists():
            raise ValueError(f"Directory does not exist: {root_path}")
        if not root_path.is_dir():
            raise ValueError(f"Not a directory: {root_path}")

        start_time = time.time()
        videos = []
        errors = []
        directories_scanned = 0
        total_files_checked = 0

        # Collecter répertoires à scanner
        directories = self._collect_directories(
            root_path, recursive, follow_symlinks
        )

        # Scanner chaque répertoire
        self.progress.start_phase(
            "discovery",
            total=len(directories),
            message="Searching for videos..."
        )

        for i, directory in enumerate(directories):
            try:
                dir_videos = self._scan_single_directory(directory)
                videos.extend(dir_videos)
                total_files_checked += len(list(directory.iterdir()))
                directories_scanned += 1

                self.progress.update(
                    "discovery",
                    current=i + 1,
                    message=f"Found {len(videos)} videos..."
                )
            except Exception as e:
                errors.append(f"Error scanning {directory}: {str(e)}")

        self.progress.finish_phase(
            "discovery",
            message=f"Found {len(videos)} videos"
        )

        scan_duration = time.time() - start_time

        return ScanResult(
            videos=videos,
            root_path=root_path,
            timestamp=datetime.now(),
            scan_duration_seconds=scan_duration,
            directories_scanned=directories_scanned,
            total_files_checked=total_files_checked,
            errors=errors
        )

    def filter_by_format(
        self,
        result: ScanResult,
        formats: list[VideoFormat]
    ) -> list[VideoFile]:
        """Filtre les vidéos par format."""
        return [v for v in result.videos if v.format in formats]

    def filter_by_size(
        self,
        result: ScanResult,
        min_mb: Optional[float] = None,
        max_mb: Optional[float] = None
    ) -> list[VideoFile]:
        """Filtre les vidéos par taille."""
        videos = result.videos

        if min_mb is not None:
            videos = [v for v in videos if v.size_mb >= min_mb]

        if max_mb is not None:
            videos = [v for v in videos if v.size_mb <= max_mb]

        return videos

    def _is_video_file(self, path: Path) -> bool:
        """Vérifie si un fichier est une vidéo."""
        return path.suffix.lower() in self.SUPPORTED_VIDEO_EXTENSIONS
```

---

## 🖥️ Modules CLI

### `cli/adapters/`

Adaptateurs pour Rich (bibliothèque terminal).

#### `RichProgressReporter`

```python
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

class RichProgressReporter(IProgressReporter):
    """Implémentation Rich de IProgressReporter."""

    def __init__(self, console: Console):
        self.console = console
        self.progress = None
        self.tasks = {}

    def __enter__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        )
        self.progress.start()
        return self

    def start_phase(self, phase_id: str, total: int, message: str = ""):
        task_id = self.progress.add_task(message, total=total)
        self.tasks[phase_id] = task_id

    def update(self, phase_id: str, current: int, message: str = ""):
        if phase_id in self.tasks:
            self.progress.update(
                self.tasks[phase_id],
                completed=current,
                description=message
            )
```

### `cli/commands/`

Commandes CLI utilisant argparse.

#### Structure d'une Commande

```python
def create_scan_parser(subparsers) -> ArgumentParser:
    """Crée le parser pour la commande scan."""

    parser = subparsers.add_parser(
        'scan',
        help='Scan directory for video files',
        epilog="Examples: ..."
    )

    # Arguments positionnels
    parser.add_argument('directory', help='Directory to scan')

    # Options
    parser.add_argument('--recursive', action='store_true', default=True)
    parser.add_argument('--formats', nargs='+', type=str)

    return parser


def run_scan_command(args) -> int:
    """Exécute la commande scan."""

    console = Console()

    # Validation
    if not validate_arguments(args, console):
        return 1

    # Créer service avec Rich adapters
    with RichProgressReporter(console) as progress:
        ui = RichUIAdapter(console)
        service = ScanService(progress=progress, ui=ui)

        try:
            # Exécuter scan
            result = service.scan_directory(
                Path(args.directory),
                recursive=args.recursive
            )

            # Afficher résultats
            display_results(console, result, args)

            # Export si demandé
            if args.output_json:
                export_json(result, args.output_json)

            return 0

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            return 1
```

---

## 🧪 Tests

### Stratégie de Test

1. **Tests Unitaires** - Chaque fonction/méthode
2. **Tests d'Intégration** - Modules ensemble
3. **Null Object Pattern** - Tests rapides sans UI

### Structure Tests

```
tests/
└── unit/
    ├── core/
    │   ├── interfaces/
    │   │   ├── test_i_progress_reporter.py
    │   │   └── test_i_ui_adapter.py
    │   ├── models/
    │   │   └── test_scan.py
    │   └── services/
    │       └── test_scan_service.py
    └── cli/
        ├── adapters/
        │   ├── test_rich_progress.py
        │   └── test_rich_ui.py
        └── commands/
            └── test_scan_command.py
```

### Exemple de Test

```python
import pytest
from pathlib import Path
from duplicateflow.core.services import ScanService
from duplicateflow.core.interfaces import NullProgressReporter, NullUIAdapter

@pytest.fixture
def temp_video_dir(tmp_path):
    """Crée un répertoire temporaire avec des vidéos."""
    # Créer fichiers
    (tmp_path / "movie1.mp4").write_text("fake video")
    (tmp_path / "movie2.mkv").write_text("fake video")
    (tmp_path / "document.txt").write_text("not a video")

    return tmp_path


def test_scan_directory_basic(temp_video_dir):
    """Test scan basique."""
    # Arrange
    service = ScanService(
        progress=NullProgressReporter(),
        ui=NullUIAdapter()
    )

    # Act
    result = service.scan_directory(temp_video_dir)

    # Assert
    assert result.video_count == 2
    assert len(result.videos) == 2
    assert result.errors == []


def test_scan_directory_recursive(temp_video_dir):
    """Test scan récursif."""
    # Créer sous-répertoire
    subdir = temp_video_dir / "subfolder"
    subdir.mkdir()
    (subdir / "movie3.avi").write_text("fake video")

    # Scan récursif
    service = ScanService(
        progress=NullProgressReporter(),
        ui=NullUIAdapter()
    )
    result = service.scan_directory(temp_video_dir, recursive=True)

    assert result.video_count == 3

    # Scan non-récursif
    result_non_recursive = service.scan_directory(
        temp_video_dir,
        recursive=False
    )

    assert result_non_recursive.video_count == 2
```

### Fixtures Pytest

```python
# tests/conftest.py

import pytest
from duplicateflow.core.interfaces import NullProgressReporter, NullUIAdapter

@pytest.fixture
def null_progress():
    """Progress reporter null."""
    return NullProgressReporter()

@pytest.fixture
def null_ui():
    """UI adapter null."""
    return NullUIAdapter()

@pytest.fixture
def temp_video_dir(tmp_path):
    """Répertoire temporaire avec vidéos."""
    # Créer structure
    (tmp_path / "movie1.mp4").write_bytes(b"fake" * 1000)
    (tmp_path / "movie2.mkv").write_bytes(b"fake" * 2000)

    subfolder = tmp_path / "subfolder"
    subfolder.mkdir()
    (subfolder / "movie3.avi").write_bytes(b"fake" * 500)

    return tmp_path
```

---

## 🔧 Développement

### Setup Environnement

```bash
# Clone
git clone https://github.com/yourusername/duplicateflow
cd duplicateflow

# Virtual env
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Dépendances
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Vérifier
python -m pytest tests/unit/ -v
```

### Workflow de Développement

1. **Créer une branche**
   ```bash
   git checkout -b feature/ma-fonctionnalite
   ```

2. **Écrire les tests d'abord (TDD)**
   ```python
   # tests/unit/core/services/test_ma_feature.py
   def test_ma_nouvelle_feature():
       # Arrange
       service = MonService()

       # Act
       result = service.ma_feature()

       # Assert
       assert result == expected
   ```

3. **Implémenter la fonctionnalité**
   ```python
   # duplicateflow/core/services/mon_service.py
   class MonService:
       def ma_feature(self):
           # Implementation
           pass
   ```

4. **Lancer les tests**
   ```bash
   pytest tests/unit/ -v
   ```

5. **Vérifier le coverage**
   ```bash
   pytest tests/unit/ --cov=duplicateflow --cov-report=html
   open htmlcov/index.html
   ```

6. **Commit et push**
   ```bash
   git add .
   git commit -m "feat: Add ma nouvelle feature"
   git push origin feature/ma-fonctionnalite
   ```

### Conventions de Code

#### Style

- **PEP 8** pour Python
- **Type hints** partout
- **Docstrings** Google style

```python
def ma_fonction(param1: str, param2: int = 0) -> bool:
    """
    Description courte de la fonction.

    Description plus détaillée si nécessaire.

    Args:
        param1: Description du paramètre 1
        param2: Description du paramètre 2 (default: 0)

    Returns:
        Description du retour

    Raises:
        ValueError: Quand param1 est vide

    Example:
        >>> ma_fonction("test", 5)
        True
    """
    if not param1:
        raise ValueError("param1 cannot be empty")

    return True
```

#### Nommage

- **Classes**: `PascalCase`
- **Fonctions/méthodes**: `snake_case`
- **Constantes**: `UPPER_SNAKE_CASE`
- **Privé**: Préfixe `_`

```python
class VideoScanner:  # PascalCase
    MAX_VIDEOS = 10000  # UPPER_SNAKE_CASE

    def scan_directory(self):  # snake_case
        pass

    def _internal_method(self):  # Privé
        pass
```

---

## 🚀 Ajouter une Nouvelle Fonctionnalité

### Exemple: Ajouter Support WebM

#### 1. Modifier l'Enum

```python
# duplicateflow/core/models/scan.py

class VideoFormat(str, Enum):
    # ... formats existants
    WEBM = "webm"  # ✅ Ajouter
```

#### 2. Ajouter Extension

```python
# duplicateflow/core/services/scan_service.py

class ScanService:
    SUPPORTED_VIDEO_EXTENSIONS = {
        '.mp4', '.mkv', '.avi',
        '.webm',  # ✅ Ajouter
    }
```

#### 3. Écrire Tests

```python
# tests/unit/core/models/test_scan.py

def test_video_format_webm():
    """Test format WebM."""
    fmt = VideoFormat.from_extension(".webm")
    assert fmt == VideoFormat.WEBM
    assert fmt.value == "webm"
```

#### 4. Vérifier

```bash
pytest tests/unit/core/models/test_scan.py::test_video_format_webm -v
```

---

## 📚 Ressources

### Documentation Technique
- **API Reference**: [API_REFERENCE.md](API_REFERENCE.md)
- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Documentation Index**: [INDEX.md](INDEX.md) - Navigation complète

### Phases de Testing (1-7)
- **Phase 1**: [PHASE1_COMPLETE_SUMMARY.md](PHASE1_COMPLETE_SUMMARY.md) - Architecture Clean (160 tests, 92%)
- **Phase 4**: [PHASE4_COMPLETE_SUMMARY.md](PHASE4_COMPLETE_SUMMARY.md) - Pipeline Management (41 tests, 94%)
- **Phase 5**: [PHASE5_SERVICE_LAYER_TESTING_COMPLETE.md](PHASE5_SERVICE_LAYER_TESTING_COMPLETE.md) - Services (80 tests, 92-100%)
- **Phase 6**: [PHASE6_CLI_TESTING_SUMMARY.md](PHASE6_CLI_TESTING_SUMMARY.md) - CLI (89 tests, 82.2%)
- **Phase 7**: [PHASE7_COMPLETE_SUMMARY.md](PHASE7_COMPLETE_SUMMARY.md) - Algorithms (471 tests, 60%+)

### Statistiques Globales
- ✅ **841+ tests** créés
- ✅ **Coverage**: Models 94%+, Services 92-100%, CLI 82.2%, Algorithms 60%+

---

**Dernière mise à jour**: 2025-12-20
**Version**: 0.7.0 (Phases 1-7 Complete)
