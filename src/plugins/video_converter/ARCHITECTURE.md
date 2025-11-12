# VideoConverter Architecture

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     VideoConverterWindow                        │
│                    (Main Coordination Layer)                    │
│                                                                 │
│  • File Management (add, remove, select)                       │
│  • Conversion Control (start, stop, pause)                     │
│  • Event Handling (drag-drop, shortcuts)                       │
│  • State Management (files_to_convert, active_workers)         │
└─────────────┬───────────────────┬───────────────────┬──────────┘
              │                   │                   │
              ▼                   ▼                   ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │   UI Package    │ │  Core Modules   │ │ Background      │
    │                 │ │                 │ │ Workers         │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
              │                   │                   │
    ┌─────────┴─────────┐        │         ┌─────────┴─────────┐
    ▼         ▼         ▼        ▼         ▼                   ▼
┌────────┐┌────────┐┌────────┐┌──────┐┌────────────┐   ┌──────────────┐
│ Button ││ Table  ││ Dialog ││Utils ││Conversion  │   │  Discovery   │
│Panels  ││Widget  ││Manager ││      ││Timer       │   │  Worker      │
└────────┘└────────┘└────────┘└──────┘└────────────┘   └──────────────┘
    │         │         │         │         │                   │
    └─────────┴─────────┴─────────┴─────────┴───────────────────┘
                             │
                             ▼
                   ┌──────────────────┐
                   │  External Deps   │
                   ├──────────────────┤
                   │ • Settings       │
                   │ • Converter      │
                   │ • Stats          │
                   │ • Metadata       │
                   └──────────────────┘
```

## Data Flow

### File Addition Flow
```
User Action (Add Files/Folder/Drop)
    │
    ▼
VideoConverterWindow.add_files()
    │
    ├─► utils.should_add_file() ─► Filter by settings
    │
    ├─► window._add_single_file() ─► Add to files_to_convert
    │
    └─► FileTableManager.refresh_table() ─► Update UI
```

### File Discovery Flow
```
User Action (Auto-Discovery)
    │
    ▼
DialogManager.show_discovery_dialog() ─► Get user config
    │
    ▼
FastFileDiscoveryWorker.start() ─► Background scan
    │
    ├─► file_found signal ─► _on_file_discovered()
    ├─► progress signal ─► _on_discovery_progress()
    ├─► batch_update signal ─► _batch_update_ui()
    └─► finished signal ─► _on_discovery_finished()
```

### Conversion Flow
```
User Action (Start Conversion)
    │
    ▼
VideoConverterWindow.start_conversion()
    │
    ├─► Check FFmpeg (utils)
    ├─► Check disk space (utils)
    ├─► Create conversion_queue
    │
    └─► Timer: _check_conversion_queue()
            │
            ├─► ConversionWorker.start() ─► For each file
            │       │
            │       ├─► progress signal ─► _update_progress()
            │       ├─► attempt_changed ─► _update_attempt()
            │       ├─► finished signal ─► _conversion_finished()
            │       └─► error signal ─► _conversion_error()
            │
            ├─► ConversionTimer.start_conversion()
            │
            └─► FileTableManager.refresh_table()
```

## Module Responsibilities

### Main Window (window.py)
**Role**: Orchestrator and coordinator

**Responsibilities**:
- Initialize all managers and workers
- Manage application state
- Handle user interactions
- Coordinate between components
- Manage file list (files_to_convert)
- Control conversion workflow
- Handle drag-and-drop
- Setup keyboard shortcuts

**Does NOT**:
- Create UI widgets directly (delegates to managers)
- Show dialogs directly (delegates to DialogManager)
- Format data (delegates to utils)

### UI Package

#### ButtonPanelManager
**Role**: Button creation and layout

**Responsibilities**:
- Create all button panels
- Configure button properties
- Set up button connections
- Update disk space display
- Maintain consistent styling

#### FileTableManager
**Role**: Table rendering and updates

**Responsibilities**:
- Create and configure table widget
- Render table rows
- Update progress bars
- Format state displays
- Handle color coding
- Update file count labels

#### DialogManager
**Role**: Dialog presentation

**Responsibilities**:
- Show information dialogs
- Show confirmation dialogs
- Show configuration dialogs
- Handle dialog results
- Maintain consistent dialog styling

### Core Modules

#### utils.py
**Role**: Utility functions

**Responsibilities**:
- Format sizes and durations
- Check file properties
- Apply filters
- Pure, stateless functions

#### conversion_timer.py
**Role**: Timing and estimation

**Responsibilities**:
- Track conversion start times
- Record completion statistics
- Estimate remaining time
- Maintain conversion history

#### file_discovery.py
**Role**: Background file scanning

**Responsibilities**:
- Scan directories for video files
- Filter by size and extension
- Emit progress signals
- Batch UI updates
- Handle scan interruption

## Design Principles Applied

### 1. Single Responsibility Principle (SRP)
Each module has one clear purpose:
- ButtonPanelManager → Button creation
- FileTableManager → Table rendering
- DialogManager → Dialog display
- utils → Utility functions

### 2. Separation of Concerns
- UI separated from business logic
- Data formatting separated from data management
- Background tasks isolated in workers

### 3. Dependency Injection
Managers receive window instance:
```python
self.button_manager = ButtonPanelManager(self)
self.table_manager = FileTableManager(self)
self.dialog_manager = DialogManager(self)
```

### 4. Interface Segregation
Each manager exposes only necessary methods:
```python
# ButtonPanelManager
setup_header(layout)
setup_main_buttons(layout)
setup_table_controls(layout)
setup_action_buttons(layout)
update_disk_space_info()

# FileTableManager
create_table(layout) → QTableWidget
refresh_table()

# DialogManager
show_help()
show_stats()
show_discovery_dialog() → Optional[Tuple]
confirm_*(args) → bool
```

### 5. Don't Repeat Yourself (DRY)
Common logic extracted:
- Formatting → utils.py
- Dialog creation → DialogManager
- Button creation → ButtonPanelManager

## Thread Safety

### Protected Resources
```python
# Main window maintains thread-safe file dictionary
self.files_mutex = QMutex()
self.files_to_convert = {}

# All access wrapped in mutex
with QMutexLocker(self.files_mutex):
    # Safe access to files_to_convert
```

### Signal/Slot Communication
Workers communicate via Qt signals:
```python
# FastFileDiscoveryWorker
file_found = pyqtSignal(str, int, int)
progress = pyqtSignal(int, str)
finished = pyqtSignal(int)
batch_update = pyqtSignal()

# ConversionWorker
progress = pyqtSignal(str, int)
finished = pyqtSignal(str, bool, str)
error = pyqtSignal(str, str)
attempt_changed = pyqtSignal(str, int)
```

## Extension Points

### Adding New Features

#### New UI Component
1. Create new manager in `ui/` package
2. Initialize in `window._setup_ui()`
3. Call setup methods
4. Update `ui/__init__.py`

#### New Utility Function
1. Add to `utils.py` with docstring
2. Import in window or other modules
3. Use throughout codebase

#### New Dialog
1. Add method to `DialogManager`
2. Follow existing pattern
3. Return appropriate value
4. Call from window methods

#### New Worker
1. Create new QThread subclass
2. Define signals
3. Implement run() method
4. Connect signals in window
5. Start/stop management

## Testing Strategy

### Unit Tests

**utils.py**:
```python
def test_format_size():
    assert format_size(1024) == "1.0 KB"
    assert format_size(1048576) == "1.0 MB"

def test_format_duration():
    assert format_duration(30) == "30s"
    assert format_duration(120) == "2min"
```

**conversion_timer.py**:
```python
def test_conversion_timing():
    timer = ConversionTimer()
    timer.start_conversion(Path("test.mp4"), 1000000)
    # ... simulate conversion
    timer.complete_conversion(Path("test.mp4"), True)
    # Assert history updated
```

### Integration Tests

**File Addition**:
```python
def test_add_files_workflow():
    window = VideoConverterWindow()
    # Mock file dialog
    # Add files
    # Assert files_to_convert updated
    # Assert table refreshed
```

**Conversion Workflow**:
```python
def test_conversion_workflow():
    window = VideoConverterWindow()
    # Add test files
    # Mock converter
    # Start conversion
    # Assert workers created
    # Simulate completion
    # Assert results recorded
```

## Performance Considerations

### Optimizations Implemented

1. **Lazy Loading**: Heavy modules loaded only when needed
2. **Batch Updates**: UI updates batched during discovery
3. **Efficient Scanning**: os.scandir instead of iterdir
4. **Throttled Refreshes**: Progress updates limited to 1/sec
5. **Mutex Locking**: Minimal critical sections

### Bottlenecks to Monitor

1. **Table Refresh**: With 1000+ files, consider virtual scrolling
2. **Disk Space Check**: Cache results, update periodically
3. **File Discovery**: Already optimized, but monitor large drives
4. **Progress Updates**: Already throttled appropriately

## Conclusion

This architecture provides:
- ✅ Clear separation of concerns
- ✅ Maintainable, testable code
- ✅ Easy to extend and modify
- ✅ Professional code organization
- ✅ Good performance characteristics
- ✅ Thread-safe operations
- ✅ Comprehensive documentation

The refactoring transforms a monolithic file into a well-structured, modular application following industry best practices.
