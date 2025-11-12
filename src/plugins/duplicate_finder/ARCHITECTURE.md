# Duplicate Finder Architecture Documentation

## System Architecture

### High-Level Overview

The duplicate finder is organized as a layered architecture with clear separation between UI, business logic, and data access:

```
┌─────────────────────────────────────────────────────────────┐
│                     Main Window Layer                        │
│         (Coordination, UI Updates, Event Handling)           │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐       ┌───────▼────────┐
│  UI Components │       │    Managers     │
│    (Panels)    │       │   (Settings)    │
└────────────────┘       └─────────────────┘
        │
        │
┌───────▼──────────────────────────────────────────────┐
│              Business Logic Layer                     │
│         (Handlers: File, Analysis, Duplicate)         │
└──────────────────────┬────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐           ┌────────▼────────┐
│    Workers     │           │   Data Access    │
│ (Hash, Compare)│           │  (VideoHasher)   │
└────────────────┘           └──────────────────┘
```

## Component Details

### 1. Main Window Layer

**File:** `main_window.py`

**Responsibilities:**
- Application lifecycle management
- Component initialization and coordination
- UI event handling and routing
- Progress update aggregation
- Signal/slot connections

**Key Methods:**
- `setup_ui()`: Constructs the user interface
- `start_analysis()`: Initiates duplicate detection
- `_on_hash_finished()`: Handles hash completion
- `_on_comparison_finished()`: Handles comparison completion

**Dependencies:**
- UI Components (panels)
- All handlers
- Settings manager
- Workers (indirect via handlers)

### 2. UI Components Layer

**File:** `ui/panels.py`

**Responsibilities:**
- UI widget creation
- Layout management
- Style application
- Callback wiring

**Key Methods:**
- `create_left_panel()`: Configuration panel
- `create_right_panel()`: Progress panel
- `_create_parameters_tab()`: Settings widgets
- `_get_button_style()`: Consistent styling

**Dependencies:**
- Progress widgets module
- PyQt6 widgets

### 3. Settings Manager

**File:** `managers/settings_manager.py`

**Responsibilities:**
- QSettings persistence
- Widget value loading/saving
- Preset management
- Window geometry persistence

**Key Methods:**
- `load_settings()`: Restore saved settings
- `save_settings()`: Persist current settings
- `apply_preset()`: Apply configuration preset
- `get_analysis_config()`: Extract current configuration

**Dependencies:**
- PyQt6.QtCore.QSettings
- Widget instances (passed as parameters)

### 4. Business Logic Layer (Handlers)

#### 4.1 File Handler

**File:** `handlers/file_handler.py`

**Responsibilities:**
- File selection dialogs
- Folder scanning
- File validation
- Status updates

**Key Methods:**
- `add_files_dialog()`: Show file picker
- `add_folder_dialog()`: Show folder picker
- `validate_files_for_analysis()`: Check file validity
- `batch_update_cache_status()`: Update multiple file statuses

**Dependencies:**
- FileListWidget
- QFileDialog

#### 4.2 Analysis Handler

**File:** `handlers/analysis_handler.py`

**Responsibilities:**
- Worker thread orchestration
- Progress tracking
- Callback management
- Time tracking

**Key Methods:**
- `start_hash_analysis()`: Begin hash computation
- `start_comparison_analysis()`: Begin comparisons
- `stop_analysis()`: Gracefully stop workers
- `is_analyzing()`: Check if operations are running

**Dependencies:**
- Workers (hash, comparison)
- VideoHasher

#### 4.3 Duplicate Handler

**File:** `handlers/duplicate_handler.py`

**Responsibilities:**
- Duplicate queue management
- User decision processing
- File operations (deletion)
- Pair ignoring

**Key Methods:**
- `add_duplicate()`: Add detected duplicate
- `process_duplicates()`: Show comparison dialogs
- `handle_duplicate_choice()`: Execute user decision
- `load_pending_duplicates()`: Resume from database

**Dependencies:**
- VideoHasher
- FileHandler
- ComparisonDialog
- send2trash

### 5. Worker Layer

#### 5.1 Hash Worker

**File:** `workers/hash_worker.py`

**Responsibilities:**
- Parallel hash computation
- Thread pool management
- Progress reporting
- File validation

**Key Methods:**
- `process_single_file()`: Compute hash for one file
- `run()`: Main worker thread execution
- `stop()`: Graceful shutdown
- `update_progress()`: Thread-safe progress updates

**Thread Safety:**
- Uses QMutex for shared state
- Emits signals for cross-thread communication

#### 5.2 Comparison Worker

**File:** `workers/comparison_worker.py`

**Responsibilities:**
- Parallel video comparison
- Pair generation and filtering
- Cache optimization
- Batch processing

**Key Methods:**
- `generate_pairs()`: Create comparison pairs
- `compare_pair()`: Compare two videos
- `run()`: Main worker thread execution
- `update_progress()`: Thread-safe progress updates

**Thread Safety:**
- Uses QMutex for shared state
- Emits signals for cross-thread communication

## Data Flow

### Analysis Workflow

```
User clicks "START"
        ↓
Main Window validates files
        ↓
Main Window → Analysis Handler: start_hash_analysis()
        ↓
Analysis Handler → Hash Worker: create and start
        ↓
Hash Worker processes files in parallel
        ↓
Hash Worker emits progress signals
        ↓
Main Window updates UI
        ↓
Hash Worker finishes
        ↓
Main Window → Analysis Handler: start_comparison_analysis()
        ↓
Analysis Handler → Comparison Worker: create and start
        ↓
Comparison Worker generates pairs
        ↓
Comparison Worker processes pairs in batches
        ↓
Comparison Worker emits duplicate_found signals
        ↓
Main Window → Duplicate Handler: add_duplicate()
        ↓
Comparison Worker finishes
        ↓
Main Window → Duplicate Handler: process_duplicates()
        ↓
Duplicate Handler shows comparison dialogs
        ↓
User makes decisions
        ↓
Duplicate Handler executes actions (delete/ignore)
        ↓
Complete
```

### Settings Workflow

```
Application starts
        ↓
Main Window → Settings Manager: load_settings()
        ↓
Settings Manager reads QSettings
        ↓
Settings Manager updates widgets
        ↓
User modifies parameter
        ↓
Widget emits valueChanged signal
        ↓
Main Window → Settings Manager: save_settings()
        ↓
Settings Manager writes QSettings
        ↓
Settings persisted
```

## Signal/Slot Architecture

### Hash Worker Signals

```python
progress(int)                          # Current count
finished()                             # Processing complete
error(str)                             # Error occurred
file_processed(str, bool)              # File path, success
current_file(str)                      # Current file info
progress_details(int, int, str)        # current, total, filename
```

### Comparison Worker Signals

```python
progress(int)                          # Current count
finished()                             # Processing complete
duplicate_found(str, str, float)       # file1, file2, similarity
error(str)                             # Error occurred
status_update(str)                     # Status message
total_comparisons_signal(int)          # Total count
comparison_details(int, int, str, str) # current, total, name1, name2
```

### Analysis Handler Signals

```python
hash_progress(int)                     # Hash progress
hash_finished()                        # Hash complete
comparison_progress(int)               # Comparison progress
comparison_finished()                  # Comparison complete
analysis_error(str)                    # Error occurred
status_update(str)                     # Status message
```

## Thread Safety

### Mutex Usage

All workers use QMutex to protect shared state:

```python
def update_progress(self, ...):
    self._mutex.lock()
    self.processed_count += 1
    current = self.processed_count
    self._mutex.unlock()

    self.progress.emit(current)
```

### Signal/Slot Communication

Cross-thread communication uses Qt's signal/slot mechanism:
- Workers emit signals from worker threads
- Main window receives signals in main thread
- Qt handles thread safety automatically

## Error Handling Strategy

### Layered Error Handling

1. **Worker Level**: Catch and log errors, emit error signals
2. **Handler Level**: Catch errors, provide fallback behavior
3. **Main Window Level**: Display user-friendly error dialogs

### Example

```python
# Worker level
try:
    hash = compute_hash(file)
except Exception as e:
    logger.error(f"Hash error: {e}")
    return file, False

# Handler level
try:
    worker.start()
except Exception as e:
    logger.error(f"Worker start failed: {e}")
    self.error.emit(str(e))

# Main window level
def handle_error(self, error_msg):
    QMessageBox.critical(self, "Error", f"Analysis failed: {error_msg}")
```

## Configuration Management

### Parameter Storage

Settings are stored in platform-specific locations via QSettings:
- **macOS**: `~/Library/Preferences/com.DuplicateFinder.VideoDeduplicator.plist`
- **Windows**: Registry under `HKEY_CURRENT_USER\Software\DuplicateFinder\VideoDeduplicator`
- **Linux**: `~/.config/DuplicateFinder/VideoDeduplicator.conf`

### Preset Configurations

Three presets are available:

| Preset | Threshold | Hash Workers | Comparison Workers | Batch Size |
|--------|-----------|--------------|-------------------|------------|
| Fast   | 85%       | 4            | 6                 | 100        |
| Balanced | 90%     | 2            | 4                 | 50         |
| Quality | 95%      | 1            | 2                 | 20         |

## Extension Points

### Adding New Features

1. **New Worker Type**: Subclass `QThread`, implement `run()`, emit progress signals
2. **New Handler**: Create in `handlers/`, follow single responsibility principle
3. **New UI Panel**: Add static method to `UIPanels` class
4. **New Setting**: Update `SettingsManager` and add widget to parameters tab

### Example: Adding a New Worker

```python
# workers/my_worker.py
class MyWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, ...):
        super().__init__()
        # Initialize

    def run(self):
        # Process work
        self.progress.emit(current)
        self.finished.emit()

# handlers/my_handler.py
class MyHandler(QObject):
    def start_processing(self, ...):
        worker = MyWorker(...)
        worker.progress.connect(self._on_progress)
        worker.start()
```

## Performance Considerations

### Parallelization

- Hash computation: Configurable workers (1-8 threads)
- Comparison: Configurable workers (1-8 threads)
- Batch processing: Reduces thread spawn overhead

### Caching

- Hash results cached in SQLite database
- Comparison results cached in memory
- Cache-aware pair generation skips redundant work

### Memory Management

- Workers process in batches to limit memory usage
- File list widgets use Qt's model/view for large lists
- Database uses WAL mode for concurrent access

## Testing Recommendations

### Unit Testing

Each module can be tested independently:

```python
# Test file handler
def test_add_files():
    handler = FileHandler(mock_widget)
    count = handler.add_files(['/path/to/file.mp4'])
    assert count == 1

# Test analysis handler
def test_start_hash_analysis():
    handler = AnalysisHandler(mock_hasher)
    handler.start_hash_analysis(files, config)
    assert handler.is_analyzing()

# Test settings manager
def test_save_load_settings():
    manager = SettingsManager()
    manager.save_settings(widgets)
    manager.load_settings(widgets)
    # Verify values match
```

### Integration Testing

Test component interactions:

```python
def test_analysis_workflow():
    window = DuplicateFinderWindow()
    window.add_files()
    window.start_analysis()
    # Wait for completion
    assert window.analysis_handler.get_elapsed_time() > 0
```

## Debugging Guide

### Logging

All modules use the logger:

```python
from src.core.logger import Logger
logger = Logger.get_logger('DuplicateFinder.ModuleName')
```

Log levels:
- `DEBUG`: Detailed information for diagnosis
- `INFO`: Confirmation of expected behavior
- `WARNING`: Unexpected but handled situations
- `ERROR`: Errors that prevent operation

### Common Issues

1. **Worker not starting**: Check `is_analyzing()` before starting new analysis
2. **UI not updating**: Ensure `force_ui_update()` is called
3. **Settings not saving**: Verify widget references are correct
4. **Signals not received**: Check signal/slot connections in `_connect_*` methods

## Future Architecture Improvements

1. **Dependency Injection**: Pass dependencies to constructors for better testability
2. **Event Bus**: Decouple components with central event dispatcher
3. **State Machine**: Formalize application states (idle, hashing, comparing, etc.)
4. **Plugin System**: Allow third-party extensions
5. **Async/Await**: Consider asyncio for better async coordination

## Conclusion

The refactored architecture provides:
- Clear separation of concerns
- Excellent testability
- Easy maintenance
- Good performance
- Thread safety
- Type safety
- Comprehensive documentation

Each component has a single, well-defined responsibility and communicates through clean interfaces.
