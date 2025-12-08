# Duplicate Finder - Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Module Organization](#module-organization)
6. [Database Schema](#database-schema)
7. [Core Abstractions](#core-abstractions)
8. [Design Patterns](#design-patterns)
9. [Extension Points](#extension-points)
10. [Performance Considerations](#performance-considerations)
11. [Future Architecture Plans](#future-architecture-plans)

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     VideoFlow Application                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Plugin Interface
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Duplicate Finder Plugin                     │
│                                                               │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────────┐   │
│  │    UI      │  │  Managers  │  │  Analysis Workers   │   │
│  │  Layer     │──│   Layer    │──│     Layer           │   │
│  └────────────┘  └────────────┘  └─────────────────────┘   │
│         │              │                    │                │
│         └──────────────┴────────────────────┘                │
│                        │                                      │
│                        ▼                                      │
│           ┌─────────────────────────┐                        │
│           │   Data Access Layer     │                        │
│           │  (Database Manager)     │                        │
│           └─────────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Language**: Python 3.8+
- **GUI Framework**: PyQt6
- **Computer Vision**: OpenCV (cv2)
- **Numerical Computing**: NumPy
- **Database**: SQLite3
- **Video Processing**: FFmpeg (via subprocess)
- **Audio Fingerprinting**: Chromaprint (optional)
- **Scene Detection**: PySceneDetect (optional)
- **Testing**: pytest
- **Async Operations**: Qt Signals/Slots + QThread

---

## Architecture Principles

### 1. Separation of Concerns
Each module has a single, well-defined responsibility:
- **UI Layer**: User interface and presentation logic only
- **Manager Layer**: Business logic and coordination
- **Worker Layer**: Heavy computation and I/O operations
- **Data Layer**: Persistence and data access

### 2. Modularity
Components are loosely coupled and can be:
- Tested independently
- Replaced or upgraded without affecting others
- Extended with new functionality

### 3. Asynchronous Design
Long-running operations never block the UI:
- Workers run in separate QThreads
- Progress updates via Qt signals
- Cancellable operations

### 4. Configuration-Driven
Behavior controlled by configuration, not code:
- Settings persistence in JSON
- Verification pipelines (configurable workflows)
- Pluggable hash methods and verification strategies

### 5. Data-Oriented Design
Minimize object creation, maximize data processing:
- Batch processing for efficiency
- NumPy arrays for performance
- Database for persistence, not in-memory objects

---

## Component Architecture

### UI Layer

```
ui/
├── main_window.py          # Main application window
├── panels.py               # Configuration panels (tabs)
├── benchmark_widgets.py    # Benchmark UI components
├── widget_registry.py      # Widget registration system
└── pipeline_config_widget.py  # Pipeline configuration UI
```

**Responsibilities:**
- Render user interface
- Capture user input
- Display results
- Progress visualization
- No business logic

**Key Classes:**
- `DuplicateFinderMainWindow`: Main window coordinating all UI
- `AnalysisPanel`: Analysis configuration tab
- `FilterPanel`: Results filtering and display
- `BenchmarkTabWidget`: Benchmark interface

### Manager Layer

```
managers/
├── settings_manager.py           # Settings persistence
├── unified_config_manager.py     # Unified configuration
├── pipeline_manager.py           # Verification pipelines
├── test_set_manager.py          # Test set CRUD
├── benchmark_manager.py         # Benchmark execution
└── progress_manager.py          # Progress coordination
```

**Responsibilities:**
- Business logic orchestration
- Configuration management
- State coordination
- Resource lifecycle management

**Key Classes:**
- `SettingsManager`: Settings save/load/apply
- `UnifiedConfigManager`: Configuration abstraction
- `PipelineManager`: Pipeline CRUD and execution
- `BenchmarkManager`: Benchmark workflows

### Worker Layer

```
workers/
├── hash_worker.py          # Video hash computation
├── audio_worker.py         # Audio fingerprinting
├── scene_worker.py         # Scene detection
├── comparison_worker.py    # Similarity comparison
└── subsequence_worker.py   # Subsequence detection
```

**Responsibilities:**
- CPU-intensive computations
- I/O operations (video reading)
- Parallel processing
- Progress reporting

**Pattern: QThread Workers**
```python
class HashWorker(QThread):
    progress = pyqtSignal(int, int)  # (current, total)
    result = pyqtSignal(dict)        # computation result
    error = pyqtSignal(str)          # error message

    def run(self):
        # Heavy computation in separate thread
        for i, video in enumerate(self.videos):
            if self.is_cancelled:
                break
            hash_value = compute_hash(video)
            self.progress.emit(i+1, len(self.videos))

        self.result.emit(results)
```

### Data Access Layer

```
database_manager.py         # Database operations
```

**Responsibilities:**
- SQLite database operations
- Schema management
- Query optimization
- Data integrity

**Key Class:**
- `DatabaseManager`: All database operations

---

## Data Flow

### Analysis Workflow

```
1. User Input (UI)
   │
   ├─→ Add Files
   │   └─→ File paths stored in FileHandler
   │
   ├─→ Configure Settings
   │   └─→ Settings saved via SettingsManager
   │
   └─→ Start Analysis
       │
       ▼
2. Configuration (Manager Layer)
   │
   ├─→ UnifiedConfigManager.get_config()
   │   └─→ Returns VideoConfig, AudioConfig, etc.
   │
   └─→ PipelineManager.get_active_pipeline()
       └─→ Returns verification pipeline
       │
       ▼
3. Worker Execution (Worker Layer)
   │
   ├─→ HashWorker.compute_hashes()
   │   ├─→ Read video frames (OpenCV)
   │   ├─→ Compute perceptual hash
   │   ├─→ Emit progress signals
   │   └─→ Return hash values
   │
   ├─→ AudioWorker.fingerprint() [if enabled]
   │   ├─→ Extract audio (FFmpeg)
   │   ├─→ Compute fingerprint (Chromaprint)
   │   └─→ Return fingerprints
   │
   └─→ ComparisonWorker.find_duplicates()
       ├─→ Compare all hash pairs
       ├─→ Apply threshold filtering
       └─→ Return duplicate groups
       │
       ▼
4. Data Persistence (Data Layer)
   │
   ├─→ DatabaseManager.add_video_hash()
   │   └─→ INSERT INTO video_hashes
   │
   └─→ DatabaseManager.add_duplicate_pair()
       └─→ INSERT INTO duplicate_pairs
       │
       ▼
5. Results Display (UI)
   │
   └─→ FilterPanel.display_results()
       ├─→ Group by similarity
       ├─→ Apply filters
       └─→ Render in table/list
```

### Benchmark Workflow

```
1. Test Set Creation
   │
   ├─→ TestSetManager.create_test_set(data)
   │   └─→ Store video pairs + expected results
   │
   └─→ PipelineManager.create_pipeline(config)
       └─→ Store verification pipeline
       │
       ▼
2. Benchmark Execution
   │
   ├─→ BenchmarkManager.run_benchmark(test_set, pipeline)
   │   │
   │   ├─→ For each video pair:
   │   │   ├─→ Execute pipeline methods
   │   │   ├─→ Record result (duplicate/unique)
   │   │   └─→ Record execution time
   │   │
   │   └─→ Calculate metrics:
   │       ├─→ True Positives (TP)
   │       ├─→ False Positives (FP)
   │       ├─→ True Negatives (TN)
   │       └─→ False Negatives (FN)
   │
   ▼
3. Metrics Computation
   │
   ├─→ Accuracy = (TP + TN) / (TP + TN + FP + FN)
   ├─→ Precision = TP / (TP + FP)
   ├─→ Recall = TP / (TP + FN)
   └─→ F1 Score = 2 × (Precision × Recall) / (Precision + Recall)
   │
   ▼
4. Results Storage & Display
   │
   └─→ BenchmarkManager.save_results()
       └─→ Display in BenchmarkTabWidget
```

---

## Module Organization

### Directory Structure

```
duplicate_finder/
├── __init__.py                 # Plugin initialization
├── plugin.py                   # Plugin entry point
├── main_window.py              # Main window
│
├── ui/                         # UI Components
│   ├── panels.py
│   ├── benchmark_widgets.py
│   ├── widget_registry.py
│   └── pipeline_config_widget.py
│
├── managers/                   # Business Logic
│   ├── __init__.py
│   ├── settings_manager.py
│   ├── unified_config_manager.py
│   ├── pipeline_manager.py
│   ├── test_set_manager.py
│   ├── benchmark_manager.py
│   └── progress_manager.py
│
├── workers/                    # Async Workers
│   ├── hash_worker.py
│   ├── audio_worker.py
│   ├── scene_worker.py
│   ├── comparison_worker.py
│   └── subsequence_worker.py
│
├── analysis/                   # Analysis Algorithms
│   ├── hash_methods.py
│   ├── audio_fingerprint.py
│   ├── lsh_index.py
│   ├── video_analysis_methods.py
│   └── subsequence_verification.py
│
├── tests/                      # Test Suite
│   ├── __init__.py
│   ├── test_core_managers.py
│   ├── test_integration.py
│   └── README.md
│
├── database_manager.py         # Data Access
├── file_handler.py            # File management
├── verification_pipeline.py   # Pipeline execution
│
└── *.md                       # Documentation
    ├── USER_GUIDE.md
    ├── FAQ.md
    ├── TROUBLESHOOTING.md
    ├── ARCHITECTURE.md
    ├── CONTRIBUTING.md
    └── API_REFERENCE.md
```

### Module Dependencies

```
UI Layer
  ↓ depends on
Manager Layer
  ↓ depends on
Worker Layer
  ↓ depends on
Analysis Algorithms
  ↓ depends on
Data Access Layer
```

**Dependency Rules:**
- Higher layers can depend on lower layers
- Lower layers NEVER depend on higher layers
- Same-layer dependencies minimized
- Cross-cutting concerns (logging, config) available to all

---

## Database Schema

### Tables

#### 1. `video_hashes`
Stores computed perceptual hashes for videos.

```sql
CREATE TABLE video_hashes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    hash_value TEXT NOT NULL,
    hash_method TEXT DEFAULT 'phash',
    duration REAL,
    width INTEGER,
    height INTEGER,
    fps REAL,
    file_size INTEGER,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_file_path (file_path),
    INDEX idx_hash_value (hash_value)
);
```

#### 2. `duplicate_pairs`
Stores detected duplicate relationships.

```sql
CREATE TABLE duplicate_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video1_id INTEGER NOT NULL,
    video2_id INTEGER NOT NULL,
    similarity_score REAL NOT NULL,
    detection_method TEXT DEFAULT 'visual',
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video1_id) REFERENCES video_hashes(id),
    FOREIGN KEY (video2_id) REFERENCES video_hashes(id),
    INDEX idx_similarity (similarity_score),
    UNIQUE (video1_id, video2_id)
);
```

#### 3. `audio_fingerprints`
Stores audio fingerprints (optional).

```sql
CREATE TABLE audio_fingerprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    fingerprint BLOB NOT NULL,
    duration REAL,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES video_hashes(id),
    INDEX idx_video_id (video_id)
);
```

#### 4. `benchmarks`
Stores benchmark results.

```sql
CREATE TABLE benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    test_set_id INTEGER,
    pipeline_id INTEGER,
    accuracy REAL,
    precision REAL,
    recall REAL,
    f1_score REAL,
    execution_time REAL,
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Database Access Pattern

**Repository Pattern:**
```python
class DatabaseManager:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)

    # CRUD operations
    def add_video_hash(self, file_path, hash_value, ...):
        # INSERT

    def get_video_hash(self, file_path):
        # SELECT

    def get_duplicates(self, threshold):
        # Complex query with JOIN

    def delete_video(self, file_path):
        # DELETE + CASCADE
```

---

## Core Abstractions

### 1. Configuration Dataclasses

Immutable configuration objects using Python dataclasses:

```python
@dataclass
class VideoConfig:
    threshold: int = 85
    hash_method: str = 'phash'
    hash_workers: int = 4
    batch_size: int = 100
    hash_timeout: int = 300

@dataclass
class AudioConfig:
    enabled: bool = False
    threshold: float = 0.7
    precision_mode: str = 'balanced'
    workers: int = 2

@dataclass
class UnifiedConfig:
    video: VideoConfig
    audio: AudioConfig
    lsh: LSHConfig
    multi_resolution: MultiResolutionConfig
    metadata: MetadataConfig
```

**Benefits:**
- Type safety
- Immutability
- Easy serialization
- Clear API

### 2. Verification Pipeline

Strategy pattern for configurable verification:

```python
class VerificationPipeline:
    def __init__(self, mode: str, methods: List[VerificationMethod]):
        self.mode = mode  # 'filtering', 'sequential', 'voting', 'weighted'
        self.methods = methods

    def execute(self, video1, video2) -> VerificationResult:
        if self.mode == 'filtering':
            return self._filter_mode(video1, video2)
        elif self.mode == 'sequential':
            return self._sequential_mode(video1, video2)
        # ...
```

**Modes:**
- **Filtering**: Early rejection (fast)
- **Sequential**: Run until match (balanced)
- **Voting**: Majority vote (democratic)
- **Weighted**: Score-based (configurable)

### 3. Hash Method Interface

Strategy pattern for different hash algorithms:

```python
class HashMethod(ABC):
    @abstractmethod
    def compute_hash(self, video_path: str) -> str:
        pass

class PHashMethod(HashMethod):
    def compute_hash(self, video_path: str) -> str:
        # pHash implementation

class DHashMethod(HashMethod):
    def compute_hash(self, video_path: str) -> str:
        # dHash implementation
```

### 4. Worker Base Class

Template method pattern for workers:

```python
class BaseWorker(QThread):
    progress = pyqtSignal(int, int)
    result = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.is_cancelled = False

    def run(self):
        try:
            self.setup()
            result = self.execute()
            self.cleanup()
            self.result.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    @abstractmethod
    def setup(self):
        pass

    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def cleanup(self):
        pass
```

---

## Design Patterns

### 1. Observer Pattern (Qt Signals/Slots)
**Use Case**: UI updates from workers

```python
# Worker emits signals
class HashWorker(QThread):
    progress = pyqtSignal(int, int)

    def run(self):
        self.progress.emit(current, total)

# UI connects to signals
class MainWindow(QMainWindow):
    def __init__(self):
        self.worker = HashWorker()
        self.worker.progress.connect(self.on_progress)

    def on_progress(self, current, total):
        self.progress_bar.setValue(current * 100 // total)
```

### 2. Strategy Pattern
**Use Case**: Hash methods, verification pipelines

```python
class VideoAnalyzer:
    def __init__(self, hash_method: HashMethod):
        self.hash_method = hash_method

    def analyze(self, video):
        return self.hash_method.compute_hash(video)

# Usage
analyzer = VideoAnalyzer(PHashMethod())
# or
analyzer = VideoAnalyzer(DHashMethod())
```

### 3. Repository Pattern
**Use Case**: Database access

```python
class VideoRepository:
    def __init__(self, db_manager):
        self.db = db_manager

    def find_by_hash(self, hash_value):
        return self.db.query("SELECT * FROM video_hashes WHERE hash_value = ?", [hash_value])
```

### 4. Template Method Pattern
**Use Case**: Worker execution

```python
class BaseWorker(QThread):
    def run(self):
        self.setup()      # Hook method
        self.execute()    # Abstract method
        self.cleanup()    # Hook method
```

### 5. Factory Pattern
**Use Case**: Hash method creation

```python
class HashMethodFactory:
    @staticmethod
    def create(method_name: str) -> HashMethod:
        if method_name == 'phash':
            return PHashMethod()
        elif method_name == 'dhash':
            return DHashMethod()
        # ...
```

### 6. Registry Pattern
**Use Case**: Widget management

```python
class WidgetRegistry:
    def __init__(self):
        self.widgets = {}

    def register(self, name: str, widget):
        self.widgets[name] = widget

    def get(self, name: str):
        return self.widgets.get(name)
```

---

## Extension Points

### 1. Custom Hash Methods

Add new hash algorithms:

```python
# 1. Create new hash method class
class MyCustomHash(HashMethod):
    def compute_hash(self, video_path: str) -> str:
        # Your implementation
        pass

# 2. Register in factory
HashMethodFactory.register('custom', MyCustomHash)

# 3. Add to UI dropdown
# (in panels.py)
```

### 2. Custom Verification Methods

Add new verification strategies:

```python
# 1. Create verification method
class CustomVerificationMethod:
    def verify(self, video1, video2) -> VerificationResult:
        # Your verification logic
        pass

# 2. Register in pipeline manager
PipelineManager.register_method('custom', CustomVerificationMethod)
```

### 3. Custom UI Panels

Add new UI tabs:

```python
# 1. Create panel class
class MyCustomPanel(QWidget):
    def __init__(self):
        super().__init__()
        # Your UI setup

# 2. Add to main window
# (in main_window.py)
self.main_tabs.addTab(MyCustomPanel(), "🔧 Custom")
```

### 4. Custom Benchmarks

Add custom benchmark metrics:

```python
# 1. Extend BenchmarkManager
class CustomBenchmarkManager(BenchmarkManager):
    def compute_custom_metric(self, results):
        # Your metric calculation
        pass
```

---

## Performance Considerations

### 1. Batch Processing
Process videos in batches to optimize I/O and memory:

```python
batch_size = 100
for i in range(0, len(videos), batch_size):
    batch = videos[i:i+batch_size]
    process_batch(batch)
    commit_to_database()
```

### 2. Parallel Processing
Use multiprocessing for CPU-bound tasks:

```python
with multiprocessing.Pool(processes=cpu_count()) as pool:
    hashes = pool.map(compute_hash, video_paths)
```

### 3. LSH Optimization
Locality-Sensitive Hashing for large-scale similarity search:

```python
# Pre-filter candidates with LSH
lsh_index = LSHIndex(bands=20, rows=5)
for hash_value in hashes:
    lsh_index.add(hash_value)

# Only compare LSH candidates
candidates = lsh_index.query(target_hash)
for candidate in candidates:
    exact_similarity = compute_exact_similarity(target, candidate)
```

### 4. Database Indexing
Create indexes on frequently queried columns:

```sql
CREATE INDEX idx_hash_value ON video_hashes(hash_value);
CREATE INDEX idx_similarity ON duplicate_pairs(similarity_score);
```

### 5. Caching
Cache computed hashes to avoid recomputation:

```python
class HashCache:
    def __init__(self, max_size_mb=500):
        self.cache = {}
        self.max_size = max_size_mb * 1024 * 1024

    def get(self, video_path):
        return self.cache.get(video_path)

    def set(self, video_path, hash_value):
        if self.size < self.max_size:
            self.cache[video_path] = hash_value
```

---

## Future Architecture Plans

### 1. Microservice Architecture
Separate analysis workers into independent services:
- Hash computation service
- Audio fingerprinting service
- Scene detection service
- Comparison service

**Benefits:**
- Horizontal scaling
- Language flexibility (Rust for performance)
- Independent deployment

### 2. Event-Driven Architecture
Use event bus for component communication:

```python
# Event bus
event_bus.subscribe('video.added', on_video_added)
event_bus.publish('video.added', video_data)

# Loose coupling between components
```

### 3. Plugin System
Allow third-party extensions:

```python
# Plugin interface
class PluginInterface:
    def on_load(self):
        pass

    def on_analysis_complete(self, results):
        pass

# Plugin manager
PluginManager.load_plugin('my_extension.py')
```

### 4. GPU Acceleration
Use GPU for hash computation and comparison:
- CUDA for NVIDIA GPUs
- OpenCL for cross-platform
- PyTorch/TensorFlow for deep learning-based matching

### 5. Distributed Processing
Scale to clusters for large video libraries:
- Apache Spark for distributed processing
- Redis for distributed caching
- PostgreSQL for distributed database

---

## Conclusion

This architecture provides:
- ✅ **Modularity**: Clear separation of concerns
- ✅ **Extensibility**: Easy to add new features
- ✅ **Testability**: Components can be tested independently
- ✅ **Performance**: Optimized for large-scale processing
- ✅ **Maintainability**: Well-documented and organized

For implementation details, see:
- **API_REFERENCE.md**: Detailed API documentation
- **CONTRIBUTING.md**: Development guidelines
- **Code Comments**: Inline documentation

---

**Version**: 3.0
**Last Updated**: December 2025
**Maintainers**: VideoFlow Development Team
