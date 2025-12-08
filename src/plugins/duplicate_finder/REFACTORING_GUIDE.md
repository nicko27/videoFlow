# Refactoring Guide - Code Duplication Reduction

## Overview

This guide documents the code duplication patterns identified in the duplicate_finder plugin and how to refactor them using the new abstractions (ProgressManager, WidgetRegistry, WorkflowController).

**Status**: Phase 4 abstractions created and integrated. This document provides guidance for ongoing refactoring.

---

## 1. Progress Update Patterns

### Current Pattern (DUPLICATED 6+ times)

```python
# Manual progress widget management
self.file_progress.setVisible(True)
self.file_progress.setMaximum(total)
self.file_progress.setValue(current)
self.file_progress.set_title("Hashing...")

# Later: hide manually
self.file_progress.setVisible(False)
```

### Refactored Pattern (Using ProgressManager)

```python
# Start progress
self.progress_manager.start('file_progress', title="Hashing...")

# Update progress
self.progress_manager.update('file_progress', current, total, message="Processing file 5/10")

# Finish progress (auto-hides)
self.progress_manager.finish('file_progress')
```

### Locations to Refactor

- `main_window.py`: Lines ~896, ~1050, ~1150 (manual progress.setVisible)
- `analysis_handler.py`: Progress updates for hashing
- `duplicate_handler.py`: Progress updates for duplicate processing
- `audio_first_handler.py`: Progress updates for audio extraction
- `workers/*.py`: Worker progress updates

**Benefit**: Centralized management, automatic show/hide, consistent behavior

---

## 2. Widget Access Patterns

### Current Pattern (DUPLICATED 30+ times)

```python
# Manual getattr() calls with fallbacks
self.threshold_spin = getattr(params_tab, 'threshold_spin', None)
self.hash_method_combo = getattr(params_tab, 'hash_method_combo', None)
# ... 28 more similar lines

# Later: Manual validation
if self.threshold_spin is None:
    logger.error("threshold_spin not found")
    return None
```

### Refactored Pattern (Using WidgetRegistry)

```python
# Automatic registration (already done in TASK 4.4)
self.widget_registry.register_from_tab(params_tab, group="params")

# Access widgets anywhere
threshold_spin = self.widget_registry.get('threshold_spin')
value = self.widget_registry.get_widget_value('threshold_spin', default=0.85)

# Validation
required = ['threshold_spin', 'hash_method_combo', 'hash_workers_spin']
self.widget_registry.set_required(*required)
if not self.widget_registry.validate():
    missing = self.widget_registry.get_missing()
    logger.error(f"Missing widgets: {missing}")
```

### Locations to Refactor

- `main_window.py`: Lines 389-428 (manual getattr extraction)
- `main_window.py`: `_get_widget_dict()` method (lines 452-468) - can be removed
- `settings_manager.py`: Widget access in save/load methods
- `audio_config.py`: `from_ui_widgets()` method

**Benefit**: No more manual getattr, automatic validation, type-safe access

---

## 3. State Management Patterns

### Current Pattern (SCATTERED boolean flags)

```python
# Scattered state booleans
self.is_analyzing = False
self.is_hashing = False
self.is_comparing = False
self.processing_stopped = False

# Manual state checks
if self.is_analyzing and not self.processing_stopped:
    # Do something
```

### Refactored Pattern (Using WorkflowController)

```python
# State transitions (already started in TASK 4.4)
self.workflow_controller.transition_to(WorkflowState.HASHING)

# Later transitions
self.workflow_controller.transition_to(WorkflowState.COMPARING)
self.workflow_controller.transition_to(WorkflowState.COMPLETED)

# State queries
if self.workflow_controller.is_active():
    # Analysis is running

if self.workflow_controller.get_state() == WorkflowState.HASHING:
    # Currently hashing

# Error handling
self.workflow_controller.error("Failed to hash video")

# Cancel
self.workflow_controller.cancel()
```

### Locations to Refactor

- `main_window.py`: Remove boolean state flags
- `analysis_handler.py`: Use workflow states instead of internal flags
- `duplicate_handler.py`: Use workflow states for processing state
- `audio_first_handler.py`: Use workflow states for audio extraction

**Benefit**: Enforced state transitions, no invalid states, clearer logic

---

## 4. Signal Connection Patterns

### Current Pattern (VERBOSE repetition)

```python
# Repeated signal connection patterns
self.analysis_handler.hash_started.connect(self._on_hash_started)
self.analysis_handler.hash_progress.connect(self._on_hash_progress)
self.analysis_handler.hash_completed.connect(self._on_hash_completed)
# ... many more similar connections
```

### Refactored Pattern (Helper method)

```python
def _connect_signals_bulk(self, source, signal_map):
    """Connect multiple signals at once."""
    for signal_name, slot in signal_map.items():
        signal = getattr(source, signal_name, None)
        if signal:
            signal.connect(slot)
        else:
            logger.warning(f"Signal {signal_name} not found on {source}")

# Usage
self._connect_signals_bulk(self.analysis_handler, {
    'hash_started': self._on_hash_started,
    'hash_progress': self._on_hash_progress,
    'hash_completed': self._on_hash_completed,
    'comparison_started': self._on_comparison_started,
    'comparison_progress': self._on_comparison_progress,
    'comparison_completed': self._on_comparison_completed,
})
```

### Locations to Refactor

- `main_window.py`: Lines 176-186 (analysis signals)
- `main_window.py`: Lines 180 (duplicate handler signals)
- `main_window.py`: Lines 183 (audio-first signals)
- `main_window.py`: Lines 186 (settings signals)

**Benefit**: Less boilerplate, easier to maintain, consistent error handling

---

## 5. Configuration Loading Patterns

### Current Pattern (Manual extraction)

```python
# Manual config extraction from widgets
config = {
    'threshold': self.threshold_spin.value() if self.threshold_spin else 0.85,
    'hash_method': self.hash_method_combo.currentData() if self.hash_method_combo else 'pHash',
    'workers': self.hash_workers_spin.value() if self.hash_workers_spin else 4,
    # ... 20 more similar lines
}
```

### Refactored Pattern (Using WidgetRegistry + UnifiedConfigManager)

```python
# Bulk value extraction
config_values = {
    'threshold': self.widget_registry.get_widget_value('threshold_spin', 0.85),
    'hash_method': self.widget_registry.get_widget_value('hash_method_combo', 'pHash'),
    'workers': self.widget_registry.get_widget_value('hash_workers_spin', 4),
}

# Or use UnifiedConfigManager (already exists from PHASE 2)
config = self.unified_config_manager.load_from_ui(self.widget_registry)
```

### Locations to Refactor

- `main_window.py`: `get_analysis_config()` method
- `settings_manager.py`: All load/save methods
- `audio_config.py`: `from_ui_widgets()` method

**Benefit**: Less boilerplate, consistent defaults, easier validation

---

## 6. Progress Bar Show/Hide Logic

### Current Pattern (DUPLICATED in multiple places)

```python
# Manual visibility management
def _show_progress_bars_for_workflow(self, workflow_type):
    if workflow_type == 'full_analysis':
        self.file_progress.setVisible(True)
        self.duplicate_progress.setVisible(True)
        self.audio_progress.setVisible(False)
        self.verification_progress.setVisible(False)
    elif workflow_type == 'audio_first':
        self.file_progress.setVisible(False)
        self.duplicate_progress.setVisible(False)
        self.audio_progress.setVisible(True)
        self.verification_progress.setVisible(False)
    # ... more elif branches
```

### Refactored Pattern (Using ProgressManager)

```python
# Hide all first
self.progress_manager.hide_all()

# Show only what's needed - ProgressManager handles the rest
# (when start() is called, it auto-shows and hides others)
```

### Locations to Refactor

- `main_window.py`: `_show_progress_bars_for_workflow()` method (lines ~896)
- Can be significantly simplified or removed

**Benefit**: Automatic management, no manual show/hide logic needed

---

## 7. Error Handling Patterns

### Current Pattern (Inconsistent)

```python
# Different error handling styles
try:
    # Do something
except Exception as e:
    logger.error(f"Error: {e}")
    QMessageBox.critical(self, "Error", str(e))
    self.set_analysis_mode(False)
    self.file_progress.setVisible(False)
    # Manual cleanup
```

### Refactored Pattern (Using WorkflowController)

```python
try:
    # Do something
except Exception as e:
    logger.error(f"Error: {e}")
    QMessageBox.critical(self, "Error", str(e))

    # Single call handles state transition and cleanup
    self.workflow_controller.error(str(e), {'exception_type': type(e).__name__})

    # Connect workflow_error signal to cleanup handler
    # self.workflow_controller.workflow_error.connect(self._on_workflow_error)
```

**Benefit**: Consistent error handling, automatic cleanup, centralized error state

---

## Migration Priority

### High Priority (Most Impact)
1. **Progress Update Patterns** - Replace all manual progress updates with ProgressManager
2. **Widget Access Patterns** - Remove manual getattr() calls, use WidgetRegistry
3. **State Management** - Replace boolean flags with WorkflowController

### Medium Priority
4. **Signal Connection Patterns** - Create bulk connection helper
5. **Configuration Loading** - Use WidgetRegistry for bulk value extraction

### Low Priority (Nice to Have)
6. **Progress Bar Logic** - Simplify show/hide logic using ProgressManager
7. **Error Handling** - Standardize with WorkflowController

---

## Next Steps

1. **Incremental Refactoring**: Refactor one pattern at a time
2. **Test After Each Change**: Run the app after each refactoring
3. **Use Abstractions**: Always prefer ProgressManager/WidgetRegistry/WorkflowController over manual patterns
4. **Document Changes**: Update this guide as refactoring progresses

---

## Summary

**Before Phase 4**:
- 30+ manual `getattr()` calls
- 6+ duplicate progress update patterns
- Scattered boolean state flags
- Verbose signal connections
- Manual show/hide logic

**After Phase 4 (Current State)**:
- ✅ Abstractions created: ProgressManager, WidgetRegistry, WorkflowController
- ✅ Basic integration in main_window.py
- 📋 Refactoring guide created (this document)
- 🔄 Ongoing: Replace all manual patterns with abstractions

**Expected Benefits**:
- 50% reduction in boilerplate code
- Centralized management = easier maintenance
- Consistent behavior across the app
- Better error handling and validation
- Clearer code structure
