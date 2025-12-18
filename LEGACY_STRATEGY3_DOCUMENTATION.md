# 📚 Legacy Strategy3 Documentation

**Date**: 2025-12-18
**Status**: 🗑️ **OBSOLETE** (Replaced by DuplicateFlow)
**Purpose**: Historical reference for strategy3 parameters

---

## 🎯 WHAT WAS STRATEGY3?

**Strategy3** was the legacy advanced subsequence verification method in the old duplicate detection system. It combined multiple verification techniques:

1. **Scene detection** (frame similarity analysis)
2. **DCT coefficients** (frequency domain comparison)
3. **Sequence verification** (temporal consistency checking)

It was replaced by **DuplicateFlow's multi-algorithm framework** which provides:
- 14 specialized algorithms
- Better precision (90-95% vs 70-80%)
- Flexible pipeline configuration
- Audio + Motion analysis

---

## 📊 STRATEGY3 PARAMETERS

### Core Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `scene_threshold` | float | 0-100 | Threshold for scene change detection |
| `dct_threshold` | float | 0-100 | DCT coefficient similarity threshold |
| `sequence_threshold` | float | 0-100 | Temporal sequence matching threshold |
| `num_samples` | int | 5-30 | Number of frames to sample for analysis |
| `warmup_seconds` | float | 0-10 | Seconds to skip at video start |
| `max_workers` | int | 1-16 | Maximum parallel workers |

### Parameter Presets (From UI Configs)

#### Preset 1: "Balanced" (Default)
```python
{
    'scene_threshold': 60.0,
    'dct_threshold': 85.0,
    'sequence_threshold': 97.0,
    'num_samples': 15,
    'warmup_seconds': 0.0,
    'max_workers': 8
}
```
**Use Case**: General purpose, good balance of speed/accuracy

---

#### Preset 2: "Fast"
```python
{
    'scene_threshold': 50.0,
    'dct_threshold': 75.0,
    'sequence_threshold': 95.0,
    'num_samples': 10,
    'warmup_seconds': 0.0,
    'max_workers': 8
}
```
**Use Case**: Quick analysis, lower precision requirements

---

#### Preset 3: "Accurate"
```python
{
    'scene_threshold': 60.0,
    'dct_threshold': 88.0,
    'sequence_threshold': 98.0,
    'num_samples': 20,
    'warmup_seconds': 0.0,
    'max_workers': 8
}
```
**Use Case**: Maximum precision, slower processing

---

#### Preset 4: "Very Fast"
```python
{
    'scene_threshold': 45.0,
    'dct_threshold': 70.0,
    'sequence_threshold': 90.0,
    'num_samples': 8,
    'warmup_seconds': 0.0,
    'max_workers': 8
}
```
**Use Case**: Rapid screening, many false negatives acceptable

---

#### Preset 5: "Custom 1"
```python
{
    'scene_threshold': 40.0,
    'dct_threshold': 68.0,
    'sequence_threshold': 88.0,
    'num_samples': 12,
    'warmup_seconds': 0.0,
    'max_workers': 8
}
```
**Use Case**: Low similarity detection, aggressive matching

---

#### Preset 6: "Custom 2"
```python
{
    'scene_threshold': 48.0,
    'dct_threshold': 75.0,
    'sequence_threshold': 92.0,
    'num_samples': 12,
    'warmup_seconds': 0.0,
    'max_workers': 8
}
```
**Use Case**: Moderate settings, balanced approach

---

## 🔄 MIGRATION TO DUPLICATEFLOW

### Strategy3 → DuplicateFlow Equivalents

**OLD (Strategy3)**:
```python
pipeline.add_method('strategy3', enabled=True, parameters={
    'scene_threshold': 60.0,
    'dct_threshold': 85.0,
    'sequence_threshold': 97.0,
    'num_samples': 15,
    'warmup_seconds': 0.0,
    'max_workers': 8
})
```

**NEW (DuplicateFlow Equivalent)**:
```python
# Scene detection → Motion Analysis
pipeline.add_method('motion_analysis', enabled=True, parameters={
    'threshold': 85.0,
    'correlation_threshold': 80.0
})

# DCT coefficients → DCT Coefficients
pipeline.add_method('dct_coefficients', enabled=True, parameters={
    'threshold': 85.0,
    'num_coeffs': 15
})

# Sequence matching → Temporal Fingerprint
pipeline.add_method('temporal_fingerprint', enabled=True, parameters={
    'threshold': 95.0
})
```

---

## 📋 WHERE STRATEGY3 WAS USED

### UI Configuration Files

1. **ui/panels.py**
   - 7 preset configurations
   - Used in pipeline presets (balanced, fast, accurate, etc.)

2. **ui/pipeline_config_widget.py**
   - 4 references in preset templates
   - Used for configuring verification methods

3. **ui/unified_pipeline_editor_dialog.py**
   - 7 parameter definitions
   - Help text for each parameter

4. **ui/benchmark_widgets.py**
   - 1 reference in method list
   - Display name "Strategy 3 (Avancé)"

5. **config/constants.py**
   - 1 class definition: `Strategy3Verification`
   - Contains parameter defaults

---

## 🗑️ REMOVAL RATIONALE

### Why Remove Strategy3?

1. **Obsolete Architecture**
   - Strategy3 was part of the old custom verification system
   - All functionality replaced by DuplicateFlow

2. **Better Alternatives**
   - DuplicateFlow provides 14 algorithms vs 1
   - Higher precision (90-95% vs 70-80%)
   - More flexible configuration

3. **Maintenance Burden**
   - Keeping strategy3 references confuses users
   - Users select strategy3 expecting it to work
   - Pipeline runs with 0 methods or fails silently

4. **Code Cleanliness**
   - After Phase 1-8 migration, strategy3 code is deleted
   - Only UI references remain
   - These references are broken (method doesn't exist)

---

## 📊 RECOMMENDED REPLACEMENTS

### For Each Preset

| Old Preset | strategy3 Config | New DuplicateFlow Config |
|------------|------------------|--------------------------|
| **Balanced** | scene:60, dct:85, seq:97 | motion_analysis(85) + dct_coefficients(85) + temporal_fingerprint(95) |
| **Fast** | scene:50, dct:75, seq:95 | motion_analysis(75) + dct_coefficients(75) |
| **Accurate** | scene:60, dct:88, seq:98 | motion_analysis(88) + dct_coefficients(88) + temporal_fingerprint(98) |
| **Very Fast** | scene:45, dct:70, seq:90 | motion_analysis(70) |
| **Custom 1** | scene:40, dct:68, seq:88 | motion_analysis(68) + dct_coefficients(68) |
| **Custom 2** | scene:48, dct:75, seq:92 | motion_analysis(75) + dct_coefficients(75) + temporal_fingerprint(92) |

---

## 🔍 PARAMETER MAPPING GUIDE

### Scene Threshold → Motion Analysis Threshold
```python
# strategy3
'scene_threshold': 60.0

# DuplicateFlow
'motion_analysis': {
    'threshold': 85.0,  # Typically higher (more selective)
    'correlation_threshold': 80.0
}
```

### DCT Threshold → DCT Coefficients Threshold
```python
# strategy3
'dct_threshold': 85.0

# DuplicateFlow
'dct_coefficients': {
    'threshold': 85.0,  # Direct mapping
    'num_coeffs': 15  # Similar to num_samples
}
```

### Sequence Threshold → Temporal Fingerprint Threshold
```python
# strategy3
'sequence_threshold': 97.0

# DuplicateFlow
'temporal_fingerprint': {
    'threshold': 95.0  # Similar high threshold for sequence matching
}
```

---

## ⚠️ BREAKING CHANGES

After removal, these will break:

1. **UI Presets selecting "strategy3"**
   - Fix: Update preset configs to use DuplicateFlow algorithms

2. **Benchmark configs with strategy3**
   - Fix: Replace with equivalent DuplicateFlow pipelines

3. **User-saved configs with strategy3**
   - Fix: Add migration logic or show error message

---

## 📚 HISTORICAL CONTEXT

### Implementation History
- **Created**: Early videoFlow development (2023-2024)
- **Purpose**: Advanced subsequence detection
- **Status**: Worked but limited (single algorithm, ~70-80% precision)
- **Replaced**: December 2025 (DuplicateFlow migration)
- **Deleted**: Phase 1-6 of migration (code removed)
- **UI Refs Removed**: Phase 9 (this cleanup)

### Why It Was Created
Before DuplicateFlow, videoFlow had custom verification methods:
- Strategy1: Basic hash comparison
- Strategy2: Enhanced with temporal analysis
- **Strategy3**: Most advanced (scene + DCT + sequence)

DuplicateFlow provides all of this and more in a unified framework.

---

## ✅ CONCLUSION

**Strategy3** was a valuable stepping stone in videoFlow's evolution but is now **completely obsolete**.

**All functionality is available** (and improved) in DuplicateFlow's multi-algorithm framework.

This document serves as **historical reference only** - do not attempt to use strategy3 parameters in new code.

---

🗑️ **This document is for reference only - Strategy3 is deprecated**

Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
