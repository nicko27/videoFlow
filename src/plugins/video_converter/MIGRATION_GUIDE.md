# Migration Guide: Window.py Refactoring

## For Developers Working with VideoConverter

This guide helps you understand the refactoring changes and how to work with the new modular architecture.

## What Changed?

### Before (1988 lines - window.py)
```
window.py
  ├─ format_size(), format_duration() (utility functions)
  ├─ ConversionTimer class
  ├─ FastFileDiscoveryWorker class
  └─ VideoConverterWindow class
      ├─ UI setup (buttons, table, dialogs)
      ├─ File management
      ├─ Conversion control
      └─ Event handlers
```

### After (Modular Structure)
```
video_converter/
├── window.py (1362 lines) ← Main coordination
├── utils.py ← Utility functions
├── conversion_timer.py ← Timing logic
├── file_discovery.py ← Discovery worker
└── ui/
    ├── __init__.py
    ├── button_panels.py ← Button creation
    ├── table_widget.py ← Table rendering
    └── dialogs.py ← Dialog management
```

## Breaking Changes

### ❌ None!

All public APIs remain the same. The `VideoConverterWindow` class maintains the same interface:
- All public methods unchanged
- All signals unchanged
- Constructor signature unchanged

## Import Updates

### If You Were Importing Utilities

**Before:**
```python
# This would have been an internal import (not recommended)
from src.plugins.video_converter.window import format_size, format_duration
```

**After:**
```python
# Now officially supported for external use
from src.plugins.video_converter.utils import format_size, format_duration
```

### Window Class Import (Unchanged)

```python
# Still works the same way
from src.plugins.video_converter.window import VideoConverterWindow

# Or through plugin
from src.plugins.video_converter.plugin import VideoConverterPlugin
```

## Working with the New Structure

### Adding New Buttons

**Before:** Edit `setup_minimal_ui()` in window.py

**After:** Edit `ButtonPanelManager` in `ui/button_panels.py`

```python
# In ui/button_panels.py
class ButtonPanelManager:
    def setup_main_buttons(self, layout: QVBoxLayout) -> None:
        # Add your new button here
        new_btn = QPushButton("🆕 New Feature")
        new_btn.clicked.connect(self.window.your_new_method)
        buttons_layout.addWidget(new_btn)
```

### Adding New Dialogs

**Before:** Create dialog directly in window method

**After:** Add method to `DialogManager` in `ui/dialogs.py`

```python
# In ui/dialogs.py
class DialogManager:
    def show_your_new_dialog(self) -> Optional[YourReturnType]:
        """Show your new dialog.

        Returns:
            Result or None if cancelled.
        """
        dialog = QDialog(self.window)
        # Setup dialog...

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return result
        return None

# In window.py
def your_feature_method(self):
    result = self.dialog_manager.show_your_new_dialog()
    if result:
        # Process result
```

### Adding New Utility Functions

**Before:** Add to window.py (not ideal)

**After:** Add to `utils.py`

```python
# In utils.py
def your_new_utility(param: Type) -> ReturnType:
    """Your utility function description.

    Args:
        param: Parameter description.

    Returns:
        Return value description.
    """
    # Implementation
    return result

# Use anywhere
from src.plugins.video_converter.utils import your_new_utility
result = your_new_utility(value)
```

### Customizing Table Rendering

**Before:** Edit `refresh_table()` in window.py

**After:** Edit `FileTableManager` in `ui/table_widget.py`

```python
# In ui/table_widget.py
class FileTableManager:
    def _render_row(self, row: int, path: Path, info: dict) -> None:
        # Customize row rendering here
        # Add new columns
        # Change colors
        # Modify display format
```

## Understanding the Architecture

### Manager Pattern

The UI is now split into "managers" that handle specific aspects:

```python
# In VideoConverterWindow.__init__()
self.button_manager = ButtonPanelManager(self)
self.table_manager = FileTableManager(self)
self.dialog_manager = DialogManager(self)
```

Each manager:
- Receives the window instance
- Creates and manages its UI components
- Calls back to window for business logic

### Accessing Managers

```python
# From window methods
self.button_manager.update_disk_space_info()
self.table_manager.refresh_table()
self.dialog_manager.show_help()
```

### Component Communication

```python
# Window → Manager (common)
self.dialog_manager.show_help()

# Manager → Window (for business logic)
# In manager:
self.window.add_files()  # Call window method

# Manager → Manager (avoid, go through window)
# ❌ DON'T: self.table_manager.refresh()
# ✅ DO: self.window.refresh_table()
```

## Testing Your Changes

### Unit Test a Utility Function

```python
# tests/test_utils.py
from src.plugins.video_converter.utils import format_size

def test_format_size():
    assert format_size(1024) == "1.0 KB"
    assert format_size(1048576) == "1.0 MB"
    assert format_size(1073741824) == "1.0 GB"
```

### Unit Test a Manager

```python
# tests/ui/test_button_panels.py
from unittest.mock import Mock
from src.plugins.video_converter.ui import ButtonPanelManager

def test_button_manager_creation():
    mock_window = Mock()
    manager = ButtonPanelManager(mock_window)
    assert manager.window == mock_window
```

### Integration Test

```python
# tests/test_window_integration.py
from src.plugins.video_converter.window import VideoConverterWindow
from PyQt6.QtWidgets import QApplication

def test_window_initialization():
    app = QApplication([])
    window = VideoConverterWindow()

    # Verify managers created
    assert window.button_manager is not None
    assert window.table_manager is not None
    assert window.dialog_manager is not None

    # Verify UI created
    assert window.files_table is not None
    assert window.start_btn is not None
```

## Common Tasks

### Task 1: Add a New Button

1. Open `ui/button_panels.py`
2. Find the appropriate setup method (`setup_main_buttons`, etc.)
3. Add your button:
```python
self.your_btn = QPushButton("Your Label")
self.your_btn.clicked.connect(self.window.your_method)
buttons_layout.addWidget(self.your_btn)
```
4. Add method to `window.py`:
```python
def your_method(self):
    """Handle your button click."""
    # Implementation
```

### Task 2: Add a New Table Column

1. Open `ui/table_widget.py`
2. Update `create_table()` to add column
3. Update `_render_row()` to populate new column
4. Adjust column widths/resize modes

### Task 3: Add a New Confirmation Dialog

1. Open `ui/dialogs.py`
2. Add method:
```python
def confirm_your_action(self, details: str) -> bool:
    """Confirm your action."""
    reply = QMessageBox.question(
        self.window,
        "Confirm Your Action",
        f"{details}\n\nAre you sure?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    return reply == QMessageBox.StandardButton.Yes
```
3. Use in window:
```python
if self.dialog_manager.confirm_your_action("Details here"):
    # Proceed with action
```

### Task 4: Add a New Worker

1. Create new file (e.g., `your_worker.py`)
2. Create QThread subclass with signals
3. Implement `run()` method
4. In window, create and connect:
```python
def start_your_task(self):
    worker = YourWorker(params)
    worker.finished.connect(self._on_your_task_finished)
    worker.start()
```

## Debugging Tips

### Finding Where Things Are

**Button not working?**
→ Check `ui/button_panels.py` for button creation
→ Check `window.py` for handler method

**Dialog not showing?**
→ Check `ui/dialogs.py` for dialog method
→ Check `window.py` for dialog call

**Table not updating?**
→ Check `ui/table_widget.py` for rendering logic
→ Check `window.py` for `refresh_table()` calls

**Utility function needed?**
→ Check `utils.py` for existing functions
→ Add new ones there if needed

### Common Issues

**Import Error:**
```python
# ❌ Wrong
from src.plugins.video_converter.window import format_size

# ✅ Right
from src.plugins.video_converter.utils import format_size
```

**Manager Not Found:**
```python
# Make sure managers are initialized in _setup_ui()
def _setup_ui(self):
    self.button_manager = ButtonPanelManager(self)
    self.table_manager = FileTableManager(self)
    self.dialog_manager = DialogManager(self)
```

**Widget Not Accessible:**
```python
# Widgets are created by managers, but stored on window
# ✅ Access via window instance
self.window.start_btn.setEnabled(False)

# Or use window reference in managers
self.window.files_table.setRowCount(10)
```

## Best Practices

### DO ✅

- Add utility functions to `utils.py`
- Add dialog methods to `DialogManager`
- Add button setup to `ButtonPanelManager`
- Keep business logic in `window.py`
- Use type hints and docstrings
- Follow Google-style docstring format
- Write unit tests for new utilities
- Use managers for UI creation

### DON'T ❌

- Create UI widgets directly in window methods
- Add utility functions to window.py
- Create dialogs directly without DialogManager
- Put business logic in managers
- Skip docstrings
- Bypass managers to create UI
- Mix UI code with business logic

## Getting Help

### File Structure Quick Reference

```
Need to...                          → Edit file...
─────────────────────────────────────────────────────────────
Add utility function                → utils.py
Add button                          → ui/button_panels.py
Add dialog                          → ui/dialogs.py
Modify table rendering              → ui/table_widget.py
Add business logic                  → window.py
Add worker thread                   → Create new file
Modify conversion timing            → conversion_timer.py
Modify file discovery               → file_discovery.py
```

### Architecture Documentation

- See `ARCHITECTURE.md` for detailed architecture
- See `REFACTORING_SUMMARY.md` for refactoring details
- Read module docstrings for API documentation

## FAQ

**Q: Will existing code break?**
A: No, all public APIs remain unchanged.

**Q: Do I need to update my imports?**
A: Only if you were importing utilities from window.py (which was internal anyway).

**Q: Can I still modify window.py?**
A: Yes! Add business logic there. Delegate UI creation to managers.

**Q: How do I add a new feature?**
A:
1. Add UI components via managers
2. Add business logic to window.py
3. Add utilities to utils.py
4. Add workers as separate files

**Q: Where do I put tests?**
A: Mirror the structure:
```
tests/
├── test_utils.py
├── test_conversion_timer.py
├── test_file_discovery.py
├── ui/
│   ├── test_button_panels.py
│   ├── test_table_widget.py
│   └── test_dialogs.py
└── test_window.py
```

**Q: Can I modify the managers?**
A: Yes! They're designed to be extended. Just maintain the interface.

**Q: What if I need manager-to-manager communication?**
A: Go through the window. Managers shouldn't know about each other.

## Summary

The refactoring makes the codebase:
- ✅ More maintainable (smaller, focused files)
- ✅ More testable (isolated components)
- ✅ More readable (clear responsibilities)
- ✅ More extensible (easy to add features)
- ✅ More professional (industry best practices)

**The key principle:**
- Managers handle UI creation
- Window handles business logic and coordination
- Utils provide reusable functions
- Workers handle background tasks

Happy coding! 🎉
