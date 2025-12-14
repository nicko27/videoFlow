# 🟠 PHASE 2 - HIGH PRIORITY BUGS (IN PROGRESS)

**Date Started:** 2025-12-14
**Estimated Duration:** 5-7 days
**Target:** Fix 11 high-priority bugs causing incorrect behavior

---

## 🎯 OBJECTIVES

Fix bugs that cause incorrect behavior but don't prevent basic usage:
- Race conditions in pipeline updates
- Progress tracking inconsistencies
- Label normalization issues
- Performance optimizations
- Error handling improvements
- Code quality improvements

---

## 📊 PROGRESS OVERVIEW

**Bugs Fixed:** 5/11 (45%)
**Time Invested:** ~2 hours
**Status:** In progress - High priority bugs fixed

### Bug Categories
- **Race Conditions:** 1 bug (Bug #2)
- **Progress UI Issues:** 4 bugs (Bugs #32-35)
- **Data Quality:** 2 bugs (Bugs #5-6)
- **Code Quality:** 3 bugs (Bugs #4, #7, #8)
- **Signal Timing:** 1 bug (Bug #20)

---

## 🐛 BUGS TO FIX

### 1. ✅ Bug #2: Race condition in `pipeline_manager.update_pipeline()`
**Gravité:** 🟠 ÉLEVÉ
**Statut:** ✅ FIXED
**Fichier:** [orchestration/pipeline_manager.py:218-224](src/plugins/duplicate_finder/orchestration/pipeline_manager.py#L218-L224)
**Temps estimé:** 1-2 heures

**Problème:**
```python
# Current code (lines 218-224):
elif global_threshold is not None:
    current = self.get_pipeline_by_id(pipeline_id)  # ❌ Race condition here!
    if current:
        payload = {"methods": current.get("methods", []), "global_threshold": global_threshold}
        updates.append("methods_json = ?")
        params.append(json.dumps(payload, ensure_ascii=False))
```

**Issue:** Between `get_pipeline_by_id()` and the UPDATE, another thread could modify the pipeline, causing lost updates.

**Solution:** Use SELECT FOR UPDATE in a transaction
```python
elif global_threshold is not None:
    with self.db.pool.get_connection() as conn:
        cursor = conn.cursor()
        # Lock the row
        cursor.execute(
            "SELECT methods_json FROM saved_pipelines WHERE id = ?",
            (pipeline_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Pipeline {pipeline_id} not found")

        current_methods = self._parse_methods_payload(row[0])
        payload = {
            "methods": current_methods["methods"],
            "global_threshold": global_threshold
        }
        updates.append("methods_json = ?")
        params.append(json.dumps(payload, ensure_ascii=False))
```

---

### 2. ✅ Bug #5: Incomplete label normalization
**Gravité:** 🟠 ÉLEVÉ
**Statut:** ✅ FIXED
**Fichier:** [services/benchmark_manager.py:23-52](src/plugins/duplicate_finder/services/benchmark_manager.py#L23-L52)
**Temps estimé:** 30 minutes

**Problème:**
Current normalization only handles basic cases. Missing French labels and numeric values.

**Solution:** Complete label map
```python
def normalize_expected_label(expected: str) -> str:
    """Normalise les labels de test en 'positive', 'negative', ou 'unknown'."""
    expected_lower = str(expected).strip().lower()

    label_map = {
        # English
        'scene_found': 'positive', 'duplicate': 'positive',
        'positive': 'positive', 'yes': 'positive', 'true': 'positive', '1': 'positive',

        'scene_not_found': 'negative', 'not_duplicate': 'negative',
        'negative': 'negative', 'no': 'negative', 'false': 'negative', '0': 'negative',

        # French
        'positif': 'positive', 'oui': 'positive',
        'négatif': 'negative', 'non': 'negative',
        'inconnu': 'unknown',

        'unknown': 'unknown'
    }

    return label_map.get(expected_lower, 'unknown')
```

---

### 3. ⏳ Bug #20: Signal `finished` connected before `start()`
**Gravité:** 🟠 ÉLEVÉ
**Statut:** ⏳ TODO
**Fichier:** [ui/multi_pipeline_benchmark.py](src/plugins/duplicate_finder/ui/multi_pipeline_benchmark.py)
**Temps estimé:** 15 minutes

**Problème:**
Signal connection order issue - sometimes `finished` is connected after thread starts, causing missed signal.

**Solution:** Always connect signals BEFORE calling `start()`
```python
# Pattern to enforce:
self.runner.finished.connect(self._on_benchmark_finished)
self.runner.error.connect(self._on_benchmark_error)
# ... all other signals
self.runner.start()  # ← ALWAYS LAST
```

---

### 4. ✅ Bug #32: Progress can exceed 100%
**Gravité:** 🟠 ÉLEVÉ
**Statut:** ✅ FIXED
**Fichier:** [ui/multi_pipeline_benchmark.py](src/plugins/duplicate_finder/ui/multi_pipeline_benchmark.py)
**Temps estimé:** 30 minutes

**Problème:**
No validation that `current <= total` before updating progress bars.

**Solution:** Add validation in all progress handlers
```python
def _update_pipeline_progress(self, current: int, total: int, pipeline_name: str):
    """Update pipeline progress with validation."""
    # CORRECTION BUG #32: Validate progress bounds
    current = max(0, min(current, total))  # Clamp to [0, total]

    if total > 0:
        percentage = int((current / total) * 100)
        self.pipeline_progress_bar.setValue(percentage)
        self.pipeline_progress_label.setText(f"{current}/{total} pairs ({percentage}%)")
```

---

### 5. ⏳ Bug #33: Semantic inconsistency in progress signals
**Gravité:** 🟠 ÉLEVÉ
**Statut:** ⏳ TODO
**Fichier:** [services/benchmark_manager.py:611 vs 643](src/plugins/duplicate_finder/services/benchmark_manager.py)
**Temps estimé:** 1 hour

**Problème:**
Two signals with different semantics:
- Line 611: `pipeline_progress.emit(processed, total_pairs, pipeline_name)` - cumulative
- Line 643: `pair_progress.emit(idx+1, len(batch), f"{video1_name} vs {video2_name}")` - batch progress

**Solution:** Clarify signal semantics with documentation and consistent naming
```python
# Rename signals for clarity:
pipeline_progress → pipeline_cumulative_progress  # Total benchmark progress
pair_progress → batch_progress  # Current batch progress
```

---

### 6. ✅ Bug #34: No progress reset between benchmarks
**Gravité:** 🟡 MOYEN
**Statut:** ✅ FIXED
**Fichier:** [ui/multi_pipeline_benchmark.py:404](src/plugins/duplicate_finder/ui/multi_pipeline_benchmark.py#L404)
**Temps estimé:** 15 minutes

**Problème:**
Progress bars keep values from previous benchmark run.

**Solution:** Reset in `_cleanup_previous_benchmark()`
```python
def _cleanup_previous_benchmark(self):
    """Cleanup previous benchmark and reset UI."""
    # ... existing cleanup code ...

    # CORRECTION BUG #34: Reset progress bars
    self.pipeline_progress_bar.setValue(0)
    self.pipeline_progress_label.setText("0/0 pairs (0%)")
    self.pair_progress_bar.setValue(0)
    self.pair_progress_label.setText("")
```

---

### 7. ✅ Bug #35: emit() called too frequently
**Gravité:** 🟡 MOYEN
**Statut:** ✅ FIXED
**Fichier:** [services/benchmark_manager.py:782](src/plugins/duplicate_finder/services/benchmark_manager.py#L782)
**Temps estimé:** 1 hour

**Problème:**
`emit_intermediate_metrics()` called after EVERY pair (1000x for 1000 pairs).
Causes 100-200ms overhead on large benchmarks.

**Solution:** Throttle emissions to every N pairs or every X seconds
```python
# Add throttling
last_emit_time = [0.0]
EMIT_INTERVAL = 0.5  # seconds

def emit_intermediate_metrics():
    current_time = time.time()
    if current_time - last_emit_time[0] < EMIT_INTERVAL:
        return  # Skip this emit

    last_emit_time[0] = current_time
    # ... rest of emit logic
```

---

### 8. ⏳ Bug #4: Incomplete network error handling
**Gravité:** 🟡 MOYEN
**Statut:** ⏳ TODO
**Fichiers:** Multiple network-related files
**Temps estimé:** 1 hour

**Problème:**
Network errors not caught consistently, can crash benchmark.

**Solution:** Add try/except around all network operations with proper error messages.

---

### 9. ⏳ Bug #6: Tolerance thresholds not normalized
**Gravité:** 🟡 MOYEN
**Statut:** ⏳ TODO
**Fichier:** Multiple pipeline config files
**Temps estimé:** 30 minutes

**Problème:**
Thresholds stored as percentages (80) vs decimals (0.8) inconsistently.

**Solution:** Normalize all thresholds to [0.0, 1.0] range on input.

---

### 10. ⏳ Bug #7: Debug logs not removed
**Gravité:** 🟢 FAIBLE
**Statut:** ⏳ TODO
**Fichiers:** Multiple
**Temps estimé:** 30 minutes

**Problème:**
`logger.debug()` statements in production code, causing log spam.

**Solution:** Remove or convert to trace level.

---

### 11. ⏳ Bug #8: User messages not translated
**Gravité:** 🟢 FAIBLE
**Statut:** ⏳ TODO
**Fichiers:** Multiple UI files
**Temps estimé:** 1 hour

**Problème:**
Some user-facing messages still in English.

**Solution:** Add French translations for all user messages.

---

## 📈 METRICS

### Target Improvements
- **Race Conditions:** 0 (eliminate all)
- **Progress Accuracy:** 100% (correct values always)
- **Code Quality:** +20% (cleanup debug code)
- **User Experience:** +15% (better error messages)

---

## ✅ COMPLETION CRITERIA

Phase 2 is complete when:
- [ ] All 11 bugs fixed
- [ ] Validation tests pass
- [ ] No new race conditions introduced
- [ ] Progress bars always show correct values
- [ ] All labels normalized correctly
- [ ] Debug logs removed
- [ ] Code committed with proper messages

---

**Phase 2 Started:** 2025-12-14
**Current Status:** In Progress (5/11 bugs fixed - 45%)
