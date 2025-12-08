# Duplicate Finder - API Reference

## Table of Contents
1. [Overview](#overview)
2. [Manager Classes](#manager-classes)
3. [Worker Classes](#worker-classes)
4. [UI Components](#ui-components)
5. [Analysis Modules](#analysis-modules)
6. [Database Manager](#database-manager)
7. [Utility Classes](#utility-classes)
8. [Data Classes](#data-classes)
9. [Constants and Enums](#constants-and-enums)

---

## Overview

This document provides a complete API reference for the Duplicate Finder plugin. For architectural context, see [ARCHITECTURE.md](ARCHITECTURE.md).

### Import Conventions

```python
# Managers
from managers.settings_manager import SettingsManager
from managers.unified_config_manager import UnifiedConfigManager, UnifiedConfig
from managers.pipeline_manager import PipelineManager

# Workers
from workers.hash_worker import HashWorker
from workers.audio_worker import AudioWorker

# Database
from database_manager import DatabaseManager

# Analysis
from analysis.hash_methods import compute_phash, compute_dhash
from analysis.lsh_index import LSHIndex
```

---

## Manager Classes

### SettingsManager

**File**: `managers/settings_manager.py`

Manages application settings persistence and retrieval.

#### Class Definition

```python
class SettingsManager(QObject):
    """
    Manages settings persistence using JSON file storage.

    Signals:
        settingChanged(str, object): Emitted when a setting value changes
    """
```

#### Methods

##### `__init__(self, settings_file: Optional[str] = None)`

Initialize settings manager.

**Args:**
- `settings_file` (str, optional): Path to settings JSON file. Defaults to 'settings.json'.

**Example:**
```python
settings = SettingsManager()
# or with custom file
settings = SettingsManager('/path/to/custom_settings.json')
```

##### `get(self, key: str, default: Any = None) -> Any`

Get a setting value.

**Args:**
- `key` (str): Setting key
- `default` (Any): Default value if key doesn't exist

**Returns:**
- Any: Setting value or default

**Example:**
```python
threshold = settings.get('video_threshold', default=85)
hash_method = settings.get('hash_method', default='phash')
```

##### `set(self, key: str, value: Any) -> None`

Set a setting value.

**Args:**
- `key` (str): Setting key
- `value` (Any): Setting value

**Raises:**
- `ValueError`: If key is empty

**Emits:**
- `settingChanged(key, value)`: When value changes

**Example:**
```python
settings.set('video_threshold', 90)
settings.set('hash_method', 'dhash')
```

##### `save(self) -> bool`

Save settings to file.

**Returns:**
- bool: True if successful, False otherwise

**Example:**
```python
if settings.save():
    print("Settings saved successfully")
```

##### `load(self) -> bool`

Load settings from file.

**Returns:**
- bool: True if successful, False otherwise

**Example:**
```python
if settings.load():
    print("Settings loaded successfully")
```

##### `reset(self) -> None`

Reset all settings to defaults.

**Example:**
```python
settings.reset()
```

##### `get_all(self) -> Dict[str, Any]`

Get all settings as dictionary.

**Returns:**
- Dict[str, Any]: All settings

**Example:**
```python
all_settings = settings.get_all()
for key, value in all_settings.items():
    print(f"{key}: {value}")
```

---

### UnifiedConfigManager

**File**: `managers/unified_config_manager.py`

Provides unified access to all configuration settings through dataclass objects.

#### Class Definition

```python
class UnifiedConfigManager:
    """
    Unified configuration manager using dataclass abstractions.

    Attributes:
        settings_manager: SettingsManager instance
        video_config: VideoConfig dataclass
        audio_config: AudioConfig dataclass
        lsh_config: LSHConfig dataclass
        multi_resolution_config: MultiResolutionConfig dataclass
        metadata_config: MetadataConfig dataclass
    """
```

#### Methods

##### `__init__(self, settings_manager: SettingsManager)`

Initialize unified config manager.

**Args:**
- `settings_manager` (SettingsManager): Settings manager instance

**Example:**
```python
settings = SettingsManager()
config = UnifiedConfigManager(settings)
```

##### `get_unified_config(self) -> UnifiedConfig`

Get complete unified configuration.

**Returns:**
- UnifiedConfig: Unified configuration object

**Example:**
```python
config_obj = config.get_unified_config()
print(f"Video threshold: {config_obj.video.threshold}")
print(f"Audio enabled: {config_obj.audio.enabled}")
```

##### `update_video_config(self, **kwargs) -> None`

Update video configuration.

**Args:**
- `**kwargs`: Video configuration parameters

**Example:**
```python
config.update_video_config(
    threshold=90,
    hash_method='phash',
    hash_workers=8
)
```

##### `update_audio_config(self, **kwargs) -> None`

Update audio configuration.

**Args:**
- `**kwargs`: Audio configuration parameters

**Example:**
```python
config.update_audio_config(
    enabled=True,
    threshold=0.8,
    precision_mode='precise'
)
```

---

### PipelineManager

**File**: `managers/pipeline_manager.py`

Manages verification pipeline CRUD operations.

#### Class Definition

```python
class PipelineManager:
    """
    Manages verification pipelines for duplicate detection.

    A pipeline is a configurable workflow that defines how videos
    are verified as duplicates.
    """
```

#### Methods

##### `get_all_pipelines(self) -> List[Dict[str, Any]]`

Get all verification pipelines.

**Returns:**
- List[Dict]: List of pipeline dictionaries

**Example:**
```python
pm = PipelineManager()
pipelines = pm.get_all_pipelines()
for pipeline in pipelines:
    print(f"{pipeline['name']}: {pipeline['mode']}")
```

##### `get_pipeline(self, pipeline_id: str) -> Optional[Dict[str, Any]]`

Get pipeline by ID.

**Args:**
- `pipeline_id` (str): Pipeline ID

**Returns:**
- Dict or None: Pipeline data or None if not found

**Example:**
```python
pipeline = pm.get_pipeline('default_pipeline')
if pipeline:
    print(f"Methods: {pipeline['methods']}")
```

##### `create_pipeline(self, pipeline_data: Dict[str, Any]) -> str`

Create new verification pipeline.

**Args:**
- `pipeline_data` (Dict): Pipeline configuration
  - `name` (str): Pipeline name
  - `mode` (str): Execution mode ('filtering', 'sequential', 'voting', 'weighted')
  - `methods` (List[Dict]): Verification methods

**Returns:**
- str: New pipeline ID

**Example:**
```python
new_pipeline = {
    'name': 'My Custom Pipeline',
    'mode': 'filtering',
    'methods': [
        {'name': 'metadata_filter', 'enabled': True},
        {'name': 'visual_hash', 'enabled': True, 'threshold': 85}
    ]
}
pipeline_id = pm.create_pipeline(new_pipeline)
```

##### `update_pipeline(self, pipeline_id: str, pipeline_data: Dict[str, Any]) -> bool`

Update existing pipeline.

**Args:**
- `pipeline_id` (str): Pipeline ID
- `pipeline_data` (Dict): Updated pipeline data

**Returns:**
- bool: True if successful

**Example:**
```python
updated = pm.update_pipeline('my_pipeline', {
    'name': 'Updated Name',
    'mode': 'sequential'
})
```

##### `delete_pipeline(self, pipeline_id: str) -> bool`

Delete pipeline.

**Args:**
- `pipeline_id` (str): Pipeline ID

**Returns:**
- bool: True if successful

**Example:**
```python
if pm.delete_pipeline('old_pipeline'):
    print("Pipeline deleted")
```

---

## Worker Classes

### HashWorker

**File**: `workers/hash_worker.py`

Computes perceptual hashes for videos in a separate thread.

#### Class Definition

```python
class HashWorker(QThread):
    """
    Worker thread for computing video hashes.

    Signals:
        progress(int, int): (current, total) progress updates
        hash_computed(str, str): (video_path, hash_value) for each video
        finished(dict): All results when complete
        error(str): Error message
    """
```

#### Signals

- `progress = pyqtSignal(int, int)`: Progress updates (current, total)
- `hash_computed = pyqtSignal(str, str)`: Hash computed (path, hash_value)
- `finished = pyqtSignal(dict)`: All results
- `error = pyqtSignal(str)`: Error message

#### Methods

##### `__init__(self, video_paths: List[str], config: VideoConfig)`

Initialize hash worker.

**Args:**
- `video_paths` (List[str]): Paths to videos
- `config` (VideoConfig): Video configuration

**Example:**
```python
worker = HashWorker(
    video_paths=['/path/to/video1.mp4', '/path/to/video2.mp4'],
    config=video_config
)
worker.progress.connect(on_progress)
worker.finished.connect(on_finished)
worker.start()
```

##### `run(self) -> None`

Execute hash computation (runs in thread).

**Note:** Called automatically by QThread, don't call directly.

##### `cancel(self) -> None`

Cancel the operation.

**Example:**
```python
worker.cancel()  # Stop processing
```

---

### AudioWorker

**File**: `workers/audio_worker.py`

Computes audio fingerprints for videos.

#### Class Definition

```python
class AudioWorker(QThread):
    """
    Worker thread for audio fingerprinting.

    Signals:
        progress(int, int): Progress updates
        fingerprint_computed(str, bytes): (path, fingerprint)
        finished(dict): All results
        error(str): Error message
    """
```

#### Methods

##### `__init__(self, video_paths: List[str], config: AudioConfig)`

Initialize audio worker.

**Args:**
- `video_paths` (List[str]): Paths to videos
- `config` (AudioConfig): Audio configuration

**Example:**
```python
worker = AudioWorker(video_paths, audio_config)
worker.progress.connect(on_progress)
worker.finished.connect(on_finished)
worker.start()
```

---

### SceneWorker

**File**: `workers/scene_worker.py`

Detects scene boundaries in videos.

#### Class Definition

```python
class SceneWorker(QThread):
    """
    Worker thread for scene detection.

    Signals:
        progress(int, int): Progress updates
        scenes_detected(str, List[Tuple]): (path, [(start_time, end_time)])
        finished(dict): All results
        error(str): Error message
    """
```

#### Methods

##### `__init__(self, video_paths: List[str], threshold: float = 27.0)`

Initialize scene worker.

**Args:**
- `video_paths` (List[str]): Video paths
- `threshold` (float): PySceneDetect threshold

**Example:**
```python
worker = SceneWorker(video_paths, threshold=30.0)
worker.scenes_detected.connect(on_scenes_detected)
worker.start()
```

---

## UI Components

### DuplicateFinderMainWindow

**File**: `main_window.py`

Main application window.

#### Class Definition

```python
class DuplicateFinderMainWindow(QMainWindow):
    """
    Main window for Duplicate Finder plugin.

    Manages all UI tabs and coordinates between components.
    """
```

#### Methods

##### `__init__(self, parent=None)`

Initialize main window.

**Args:**
- `parent` (QWidget, optional): Parent widget

**Example:**
```python
window = DuplicateFinderMainWindow()
window.show()
```

##### `add_files(self, file_paths: List[str]) -> None`

Add files to analysis list.

**Args:**
- `file_paths` (List[str]): Paths to video files

**Example:**
```python
window.add_files(['/path/to/video1.mp4', '/path/to/video2.mp4'])
```

##### `start_analysis(self) -> None`

Start duplicate analysis.

**Example:**
```python
window.start_analysis()
```

##### `stop_analysis(self) -> None`

Stop ongoing analysis.

**Example:**
```python
window.stop_analysis()
```

---

### AnalysisPanel

**File**: `ui/panels.py`

Analysis configuration panel.

#### Class Definition

```python
class AnalysisPanel(QWidget):
    """
    Panel for configuring and running analysis.

    Contains all configuration widgets for:
    - Video comparison parameters
    - Audio fingerprinting
    - LSH optimization
    - Multi-resolution analysis
    - Metadata filtering
    """
```

#### Methods

##### `get_configuration(self) -> Dict[str, Any]`

Get current configuration from UI widgets.

**Returns:**
- Dict: Configuration dictionary

**Example:**
```python
config = panel.get_configuration()
print(f"Threshold: {config['video_threshold']}")
```

##### `set_configuration(self, config: Dict[str, Any]) -> None`

Set configuration in UI widgets.

**Args:**
- `config` (Dict): Configuration dictionary

**Example:**
```python
panel.set_configuration({
    'video_threshold': 90,
    'hash_method': 'phash'
})
```

---

## Analysis Modules

### Hash Methods

**File**: `analysis/hash_methods.py`

Perceptual hash computation functions.

#### Functions

##### `compute_phash(video_path: str, size: int = 8) -> str`

Compute perceptual hash (pHash).

**Args:**
- `video_path` (str): Path to video file
- `size` (int): Hash size. Defaults to 8 (64-bit hash).

**Returns:**
- str: Hexadecimal hash string

**Raises:**
- `IOError`: If video cannot be read
- `ValueError`: If video has no frames

**Example:**
```python
from analysis.hash_methods import compute_phash

hash_value = compute_phash('/path/to/video.mp4')
print(f"Hash: {hash_value}")
```

##### `compute_dhash(video_path: str, size: int = 8) -> str`

Compute difference hash (dHash).

**Args:**
- `video_path` (str): Path to video file
- `size` (int): Hash size

**Returns:**
- str: Hexadecimal hash string

**Example:**
```python
from analysis.hash_methods import compute_dhash

hash_value = compute_dhash('/path/to/video.mp4', size=16)
```

##### `compute_ahash(video_path: str, size: int = 8) -> str`

Compute average hash (aHash).

**Args:**
- `video_path` (str): Path to video file
- `size` (int): Hash size

**Returns:**
- str: Hexadecimal hash string

**Example:**
```python
from analysis.hash_methods import compute_ahash

hash_value = compute_ahash('/path/to/video.mp4')
```

##### `compute_whash(video_path: str, size: int = 8) -> str`

Compute wavelet hash (wHash).

**Args:**
- `video_path` (str): Path to video file
- `size` (int): Hash size

**Returns:**
- str: Hexadecimal hash string

**Example:**
```python
from analysis.hash_methods import compute_whash

hash_value = compute_whash('/path/to/video.mp4')
```

##### `hamming_distance(hash1: str, hash2: str) -> int`

Calculate Hamming distance between two hashes.

**Args:**
- `hash1` (str): First hash (hex string)
- `hash2` (str): Second hash (hex string)

**Returns:**
- int: Hamming distance (number of differing bits)

**Example:**
```python
from analysis.hash_methods import hamming_distance

dist = hamming_distance('a9b8c7d6', 'a9b8c7d7')
similarity = 100 * (1 - dist / 64)  # For 64-bit hash
print(f"Similarity: {similarity}%")
```

---

### LSH Index

**File**: `analysis/lsh_index.py`

Locality-Sensitive Hashing for fast similarity search.

#### Class Definition

```python
class LSHIndex:
    """
    LSH index for fast approximate similarity search.

    Uses MinHash and banding technique to find candidate pairs
    without comparing all pairs.
    """
```

#### Methods

##### `__init__(self, bands: int = 20, rows: int = 5)`

Initialize LSH index.

**Args:**
- `bands` (int): Number of bands (more = faster, less accurate)
- `rows` (int): Rows per band (more = slower, more accurate)

**Formula:** `bands × rows = hash size`

**Example:**
```python
from analysis.lsh_index import LSHIndex

lsh = LSHIndex(bands=20, rows=5)  # For 100-bit hashes
```

##### `add(self, video_id: str, hash_value: str) -> None`

Add hash to index.

**Args:**
- `video_id` (str): Video identifier
- `hash_value` (str): Perceptual hash (hex string)

**Example:**
```python
lsh.add('video1', 'a9b8c7d6e5f4')
lsh.add('video2', 'a9b8c7d6e5f5')
```

##### `query(self, hash_value: str, threshold: float = 0.8) -> List[str]`

Find candidate similar videos.

**Args:**
- `hash_value` (str): Query hash
- `threshold` (float): Similarity threshold (0.0-1.0)

**Returns:**
- List[str]: List of candidate video IDs

**Example:**
```python
candidates = lsh.query('a9b8c7d6e5f4', threshold=0.85)
for video_id in candidates:
    print(f"Candidate: {video_id}")
```

##### `get_all_candidates(self) -> List[Tuple[str, str]]`

Get all candidate pairs.

**Returns:**
- List[Tuple[str, str]]: List of (video_id1, video_id2) pairs

**Example:**
```python
pairs = lsh.get_all_candidates()
print(f"Need to compare {len(pairs)} pairs (instead of {n*(n-1)//2})")
```

---

## Database Manager

**File**: `database_manager.py`

Manages all database operations.

#### Class Definition

```python
class DatabaseManager:
    """
    SQLite database manager for storing analysis results.

    Handles:
    - Video hashes
    - Duplicate pairs
    - Audio fingerprints
    - Benchmark results
    """
```

#### Methods

##### `__init__(self, db_path: str)`

Initialize database manager.

**Args:**
- `db_path` (str): Path to SQLite database file

**Example:**
```python
from database_manager import DatabaseManager

db = DatabaseManager('video_duplicates.db')
```

##### `add_video_hash(self, file_path: str, hash_value: str, **metadata) -> int`

Add video hash to database.

**Args:**
- `file_path` (str): Path to video file
- `hash_value` (str): Perceptual hash
- `**metadata`: Additional metadata (duration, width, height, fps, file_size)

**Returns:**
- int: Video ID

**Example:**
```python
video_id = db.add_video_hash(
    file_path='/path/to/video.mp4',
    hash_value='a9b8c7d6',
    duration=120.5,
    width=1920,
    height=1080,
    fps=30.0,
    file_size=52428800  # bytes
)
```

##### `get_video_hash(self, file_path: str) -> Optional[Dict[str, Any]]`

Get video hash by file path.

**Args:**
- `file_path` (str): Path to video file

**Returns:**
- Dict or None: Video data or None if not found

**Example:**
```python
video = db.get_video_hash('/path/to/video.mp4')
if video:
    print(f"Hash: {video['hash_value']}")
    print(f"Duration: {video['duration']}s")
```

##### `get_duplicates(self, threshold: float = 85.0) -> List[Dict[str, Any]]`

Get duplicate pairs above threshold.

**Args:**
- `threshold` (float): Minimum similarity (0-100)

**Returns:**
- List[Dict]: List of duplicate pair dictionaries

**Example:**
```python
duplicates = db.get_duplicates(threshold=90.0)
for dup in duplicates:
    print(f"{dup['video1_path']} <-> {dup['video2_path']}: {dup['similarity']}%")
```

##### `add_duplicate_pair(self, video1_id: int, video2_id: int, similarity: float) -> int`

Add duplicate pair to database.

**Args:**
- `video1_id` (int): First video ID
- `video2_id` (int): Second video ID
- `similarity` (float): Similarity score (0-100)

**Returns:**
- int: Pair ID

**Example:**
```python
pair_id = db.add_duplicate_pair(
    video1_id=1,
    video2_id=2,
    similarity=92.5
)
```

##### `delete_video(self, file_path: str) -> bool`

Delete video and associated data.

**Args:**
- `file_path` (str): Path to video file

**Returns:**
- bool: True if successful

**Example:**
```python
if db.delete_video('/path/to/video.mp4'):
    print("Video deleted from database")
```

##### `close(self) -> None`

Close database connection.

**Example:**
```python
db.close()
```

---

## Data Classes

### VideoConfig

**File**: `managers/unified_config_manager.py`

Configuration for video comparison.

```python
@dataclass
class VideoConfig:
    threshold: int = 85
    hash_method: str = 'phash'
    hash_workers: int = 4
    batch_size: int = 100
    hash_timeout: int = 300
```

**Example:**
```python
config = VideoConfig(
    threshold=90,
    hash_method='dhash',
    hash_workers=8
)
```

### AudioConfig

```python
@dataclass
class AudioConfig:
    enabled: bool = False
    threshold: float = 0.7
    precision_mode: str = 'balanced'  # 'fast', 'balanced', 'precise'
    workers: int = 2
```

### LSHConfig

```python
@dataclass
class LSHConfig:
    enabled: bool = False
    bands: int = 20
    rows: int = 5
    min_hash_size: int = 100
```

### MetadataConfig

```python
@dataclass
class MetadataConfig:
    enabled: bool = False
    duration_tolerance: int = 5  # seconds
    size_ratio_min: float = 0.5
    size_ratio_max: float = 2.0
```

---

## Constants and Enums

### Hash Methods

```python
HASH_METHODS = ['phash', 'dhash', 'ahash', 'whash']
DEFAULT_HASH_METHOD = 'phash'
```

### Precision Modes

```python
PRECISION_MODES = ['fast', 'balanced', 'precise']
DEFAULT_PRECISION_MODE = 'balanced'
```

### Pipeline Modes

```python
PIPELINE_MODES = ['filtering', 'sequential', 'voting', 'weighted']
```

### Thresholds

```python
DEFAULT_VIDEO_THRESHOLD = 85  # 0-100
DEFAULT_AUDIO_THRESHOLD = 0.7  # 0.0-1.0
```

---

## Usage Examples

### Complete Analysis Example

```python
from managers.settings_manager import SettingsManager
from managers.unified_config_manager import UnifiedConfigManager
from workers.hash_worker import HashWorker
from database_manager import DatabaseManager
from PyQt6.QtCore import QCoreApplication
import sys

# Initialize Qt application
app = QCoreApplication(sys.argv)

# Setup managers
settings = SettingsManager()
config_manager = UnifiedConfigManager(settings)
db = DatabaseManager('duplicates.db')

# Configure analysis
config_manager.update_video_config(
    threshold=90,
    hash_method='phash',
    hash_workers=8
)

# Prepare video list
video_paths = ['/path/to/video1.mp4', '/path/to/video2.mp4']

# Create worker
worker = HashWorker(video_paths, config_manager.video_config)

# Connect signals
def on_progress(current, total):
    print(f"Progress: {current}/{total}")

def on_finished(results):
    print("Analysis complete!")
    for path, hash_value in results.items():
        db.add_video_hash(path, hash_value)
    app.quit()

worker.progress.connect(on_progress)
worker.finished.connect(on_finished)

# Start analysis
worker.start()

# Run event loop
sys.exit(app.exec())
```

### Benchmark Example

```python
from managers.pipeline_manager import PipelineManager
from managers.test_set_manager import TestSetManager
from managers.benchmark_manager import BenchmarkManager

# Create managers
pm = PipelineManager()
tsm = TestSetManager()
bm = BenchmarkManager()

# Create test set
test_set_data = {
    'name': 'Test Set 1',
    'pairs': [
        {'video1': 'a.mp4', 'video2': 'b.mp4', 'expected': 'duplicate'},
        {'video1': 'c.mp4', 'video2': 'd.mp4', 'expected': 'unique'}
    ]
}
test_set_id = tsm.create_test_set(test_set_data)

# Create pipeline
pipeline_data = {
    'name': 'Test Pipeline',
    'mode': 'sequential',
    'methods': [
        {'name': 'visual_hash', 'enabled': True}
    ]
}
pipeline_id = pm.create_pipeline(pipeline_data)

# Run benchmark
results = bm.run_benchmark(test_set_id, pipeline_id)
print(f"Accuracy: {results['accuracy']}")
print(f"Precision: {results['precision']}")
print(f"Recall: {results['recall']}")
```

---

## Error Handling

### Common Exceptions

```python
try:
    hash_value = compute_phash('/path/to/video.mp4')
except IOError as e:
    print(f"Cannot read video: {e}")
except ValueError as e:
    print(f"Invalid video: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Database Errors

```python
try:
    db.add_video_hash(path, hash_value)
except sqlite3.IntegrityError:
    print("Video already exists in database")
except sqlite3.OperationalError as e:
    print(f"Database error: {e}")
```

---

## Best Practices

### 1. Always use context managers when possible

```python
# Good
db = DatabaseManager('duplicates.db')
try:
    db.add_video_hash(path, hash_value)
finally:
    db.close()
```

### 2. Connect signals before starting workers

```python
# Good
worker = HashWorker(videos, config)
worker.progress.connect(on_progress)
worker.finished.connect(on_finished)
worker.start()

# Bad - signals may be missed
worker = HashWorker(videos, config)
worker.start()
worker.progress.connect(on_progress)  # Too late!
```

### 3. Always handle worker errors

```python
worker = HashWorker(videos, config)
worker.error.connect(lambda msg: print(f"Error: {msg}"))
worker.finished.connect(on_success)
worker.start()
```

### 4. Use type hints

```python
from typing import List, Dict, Optional

def process_videos(paths: List[str], threshold: int = 85) -> Dict[str, str]:
    """Process videos with type safety."""
    pass
```

---

## Version Compatibility

This API reference is for **version 3.0** of Duplicate Finder.

### Breaking Changes from 2.x

- `SettingsManager.get()` now returns `None` instead of raising `KeyError` when key doesn't exist
- `UnifiedConfigManager` replaces multiple separate config classes
- `PipelineManager` API changed to use string IDs instead of integer IDs

### Deprecations

- `old_hash_method()` - Use `compute_phash()` instead (removed in 4.0)
- `legacy_config` - Use `UnifiedConfig` dataclasses (removed in 4.0)

---

## See Also

- **ARCHITECTURE.md**: System architecture and design patterns
- **CONTRIBUTING.md**: Development guidelines
- **USER_GUIDE.md**: User-facing documentation
- **Source Code**: Inline documentation in source files

---

**Version**: 3.0
**Last Updated**: December 2025
**API Stability**: Stable (semantic versioning)
