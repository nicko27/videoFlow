# 🟡 PHASE 3 - MEDIUM PRIORITY IMPROVEMENTS

**Date Started:** 2025-12-14
**Estimated Duration:** 1-2 weeks
**Target:** Improve code quality, performance, and user experience

---

## 🎯 OBJECTIVES

Phase 3 focuses on:
- Completing deferred Phase 2 bugs
- Code quality improvements
- Performance optimizations
- User experience enhancements
- Error handling improvements

---

## 📊 PROGRESS OVERVIEW

**Bugs To Fix:** 6 total
**Bugs Fixed:** 0/6 (0%)
**Time Invested:** 0 hours
**Status:** Just started

### Bug Categories
- **Deferred from Phase 2:** 3 bugs (#4, #8, #33)
- **New Phase 3 Bugs:** 3 bugs (from analysis)

---

## 🐛 BUGS TO FIX

### DEFERRED FROM PHASE 2 (3 bugs)

#### 1. ⏳ Bug #33: Semantic inconsistency in progress signals
**Gravité:** 🟡 MOYEN
**Statut:** ⏳ TODO
**Fichier:** [services/benchmark_manager.py](src/plugins/duplicate_finder/services/benchmark_manager.py)
**Temps estimé:** 1-2 hours

**Problème:**
Two signals with different semantics cause confusion:
- `pipeline_progress`: Cumulative progress (total benchmark)
- `pair_progress`: Batch progress (current batch)

**Solution:** Clarify with documentation and consistent naming
```python
# Option 1: Rename signals for clarity
pipeline_progress → pipeline_cumulative_progress
pair_progress → batch_progress

# Option 2: Add comprehensive docstrings
class BenchmarkRunner(QThread):
    """
    Signals:
        pipeline_progress: (current, total, name) - CUMULATIVE progress across all pairs
        pair_progress: (current, total, v1, v2) - BATCH progress within current executor batch
    """
```

**Impact:** Better code clarity, easier to understand signal flow

---

#### 2. ⏳ Bug #4: Incomplete network error handling
**Gravité:** 🟡 MOYEN
**Statut:** ⏳ TODO
**Fichiers:** Multiple network-related files
**Temps estimé:** 1-2 hours

**Problème:**
Network errors not caught consistently, can crash benchmark when network operations fail.

**Solution:** Comprehensive error handling
```python
# Add try/except around all network operations
try:
    # Network operation
    result = network_call()
except (ConnectionError, TimeoutError, OSError) as e:
    logger.error(f"Network error: {e}")
    # Emit error signal or return None
    self.error.emit(f"Network error: {e}")
    return None
```

**Files to audit:**
- Audio fingerprinting (network-based matching)
- Shazam detector
- Any external API calls

---

#### 3. ⏳ Bug #8: User messages not translated
**Gravité:** 🟢 FAIBLE
**Statut:** ⏳ TODO
**Fichiers:** Multiple UI files
**Temps estimé:** 1 hour

**Problème:**
Some user-facing messages still in English, inconsistent with French UI.

**Solution:** Translate remaining English messages
```python
# BEFORE:
QMessageBox.warning(self, "Error", "Pipeline not found")

# AFTER:
QMessageBox.warning(self, "Erreur", "Pipeline introuvable")
```

**Strategy:**
1. Grep for English error messages
2. Translate to French
3. Ensure consistency with existing translations

---

### NEW PHASE 3 BUGS (3 bugs)

#### 4. ⏳ Bug #9: Precompute function too complex
**Gravité:** 🟡 MOYEN
**Statut:** ⏳ TODO
**Fichier:** [services/benchmark_manager.py:253-542](src/plugins/duplicate_finder/services/benchmark_manager.py#L253-L542)
**Temps estimé:** 2-3 hours

**Problème:**
`_precompute_hashes()` is 290 lines with 12 different responsibilities. High cyclomatic complexity makes it hard to test and maintain.

**Solution:** Refactor into strategy pattern
```python
class PrecomputeHashesStrategy:
    """Strategy for precomputing various hash types."""

    def execute(self, progress_callback):
        self._precompute_sha256(progress_callback)
        if self._wants_method('frame_hash'):
            self._precompute_frame_hashes(progress_callback)
        # etc...

    def _precompute_sha256(self, progress_callback):
        # Isolated logic (< 30 lines)

    def _precompute_frame_hashes(self, progress_callback):
        # Isolated logic (< 30 lines)
```

**Impact:** Better testability, maintainability, code clarity

---

#### 5. ⏳ Bug #10: Silent error handling in precompute
**Gravité:** 🟡 MOYEN
**Statut:** ⏳ TODO
**Fichier:** [services/benchmark_manager.py:539-542](src/plugins/duplicate_finder/services/benchmark_manager.py#L539-L542)
**Temps estimé:** 30 minutes

**Problème:**
Errors during hash precomputation are logged but progression shows 100%, misleading users.

**Current code:**
```python
except Exception as e:
    logger.error(f"Precompute failed: {e}")
    # Progression reste à 100% même si échec!
    self.hashing_progress.emit(len(all_video_paths), len(all_video_paths), pipeline_name)
```

**Solution:** Emit accurate progress
```python
except Exception as e:
    logger.error(f"[{pipeline_name}] Precompute hashes failed: {e}", exc_info=True)
    # Émettre progression réelle, pas 100%
    current = sum(1 for _ in completed_hashes if _ is not None)
    self.hashing_progress.emit(current, total, pipeline_name)
    # Optionally emit error signal
    self.error.emit(f"Hash precomputation failed: {e}")
```

---

#### 6. ⏳ Bug #11: Cache invalidation logic missing
**Gravité:** 🟡 MOYEN
**Statut:** ⏳ TODO
**Fichiers:** Cache-related files
**Temps estimé:** 1 hour

**Problème:**
Caches (frame cache, hash cache) don't invalidate when source files change.

**Solution:** Add file modification time checks
```python
def get_cached_hash(video_path, method_name):
    current_mtime = os.path.getmtime(video_path)
    cached_entry = db.get_hash(video_path, method_name)

    if cached_entry and cached_entry['mtime'] == current_mtime:
        return cached_entry['hash']  # Valid cache

    # Cache invalid - recompute
    return None
```

---

## 📈 EXPECTED IMPROVEMENTS

### Code Quality
- **Maintainability:** +30% (refactored complex functions)
- **Testability:** +40% (isolated responsibilities)
- **Error Handling:** +50% (comprehensive coverage)

### User Experience
- **Clarity:** +20% (translated messages, clear signal names)
- **Reliability:** +15% (better error handling, cache invalidation)

### Performance
- **Cache Hit Rate:** +10% (proper invalidation)
- **Debug Efficiency:** +25% (better error messages)

---

## ✅ COMPLETION CRITERIA

Phase 3 is complete when:
- [ ] All 6 bugs fixed or documented
- [ ] Code refactored where needed
- [ ] Error handling comprehensive
- [ ] User messages translated
- [ ] Cache invalidation working
- [ ] Tests created for new code
- [ ] Documentation updated

---

**Phase 3 Started:** 2025-12-14
**Current Status:** Planning (0/6 bugs fixed)
**Estimated Completion:** 1-2 weeks
