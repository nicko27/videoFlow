# 🔬 Hash Debugging Tool

**Date:** 2025-11-16
**Purpose:** Manual hash calculation and comparison for debugging subsequence detection issues

---

## 🎯 Problem Addressed

Users reported false positive detections in subsequence detection, particularly when videos contain large black areas. To help debug this issue, we needed a way to manually:

1. Calculate hashes for specific test videos
2. Visualize hash values to understand what's being detected
3. Compare hashes between videos to see why they're being marked as similar
4. Analyze frame-by-frame differences

**User Request:**
> "La détection semble se tromper elle prend des images identiques quand elle voit des grandes zones noires. Pourrais tu me rajouter via l'interface un outil manuel qui permettrait de calculer les hash afin que je t'aide à dépanner. Je sais quoi comparer vu que j'ai créé des vidéos de tests"

---

## ✨ Features

### **1. Manual Video Selection**
- Select 1-2 videos from file system
- File filter for common video formats (mp4, avi, mkv, mov, wmv, flv, webm)
- Display selected files with clear names

### **2. Hash Calculation**
- Uses the same `VideoHasher` instance as main analysis
- Calculates hashes using the currently selected hash method (pHash, dHash, or aHash)
- Displays:
  - Video duration
  - Calculation time
  - Hash shape and data type
  - Binary visualization of first 10 frame hashes

### **3. Two-Video Comparison**
- Automatic comparison when 2 videos are selected
- Shows overall similarity percentage
- Color-coded similarity assessment:
  - 🔴 **VERY HIGH** (≥90%) - Likely duplicates
  - 🟡 **MEDIUM** (70-89%) - Possible related content
  - 🟢 **LOW** (<70%) - Different videos

### **4. Frame-by-Frame Analysis**
- Detailed comparison of first 10 frames
- Individual similarity scores per frame
- Visual indicators (✓/✗) for each frame
- Helps identify which frames cause false positives

---

## 🏗️ Architecture

### **HashDebugger Widget** (`progress_widgets.py:617-912`)

```python
class HashDebugger(QFrame):
    """Widget for manual hash calculation and debugging."""

    def __init__(self, video_hasher=None, parent=None):
        self.video_hasher = video_hasher
        self.selected_files = []
        self.hash_results = {}

    def set_video_hasher(self, video_hasher):
        """Set the video hasher instance."""

    def _select_files(self):
        """Open file dialog to select video files."""

    def _calculate_hashes(self):
        """Calculate hashes for selected files."""

    def _clear_files(self):
        """Clear selected files and results."""
```

**Key Methods:**
- `set_video_hasher()` - Injects the VideoHasher instance
- `_select_files()` - Opens file dialog (limit 2 videos)
- `_calculate_hashes()` - Computes and displays hash results
- `_clear_files()` - Resets the widget state

---

## 🎨 UI Design

### **Visual Appearance:**
- **Background:** Light cream (#FFF8DC) to distinguish from main UI
- **Border:** Gold (#FFD700) to indicate debugging/special tool
- **Buttons:**
  - 📁 Select Video(s) - Green (#4CAF50)
  - 🗑️ Clear - Red (#f44336)
  - ⚡ Calculate Hashes - Blue (#2196F3)

### **Layout:**
```
┌─────────────────────────────────────────────────────┐
│ 🔬 Hash Debugging Tool                              │
│ Manually calculate and compare video hashes...      │
├─────────────────────────────────────────────────────┤
│ [📁 Select Video(s)]  [🗑️ Clear]                    │
├─────────────────────────────────────────────────────┤
│ Selected Files:                                     │
│ 1. video1.mp4                                       │
│ 2. video2.mp4                                       │
├─────────────────────────────────────────────────────┤
│ [⚡ Calculate Hashes]                                │
├─────────────────────────────────────────────────────┤
│ Results:                                            │
│                                                     │
│ ======================================              │
│ HASH CALCULATION RESULTS                            │
│ ======================================              │
│ Hash Method: pHash                                  │
│                                                     │
│ ──────────────────────────────────                 │
│ File 1: video1.mp4                                  │
│ ──────────────────────────────────                 │
│ ✓ Hash calculated successfully                     │
│   Duration: 10.5s                                   │
│   Calculation time: 0.234s                          │
│   Hash shape: (8, 8, 8)                            │
│                                                     │
│   Hash values (first 10 frames):                    │
│     Frame  0: 10101010... 01010101...              │
│     Frame  1: 11001100... 00110011...              │
│     ...                                             │
│                                                     │
│ ======================================              │
│ COMPARISON RESULTS                                  │
│ ======================================              │
│                                                     │
│ File 1: video1.mp4                                  │
│ File 2: video2.mp4                                  │
│                                                     │
│ Similarity: 85.32%                                  │
│                                                     │
│ 🟡 MEDIUM similarity - Possible related content     │
│                                                     │
│ ──────────────────────────────────                 │
│ FRAME-BY-FRAME COMPARISON (first 10 frames)         │
│ ──────────────────────────────────                 │
│   Frame  0:  92.5% similarity ✓                     │
│   Frame  1:  87.3% similarity ✓                     │
│   Frame  2:  78.1% similarity ✗                     │
│   ...                                               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### **Location in UI:**
The Hash Debugger appears in the **Settings tab** (⚙️), at the bottom of the panel, after the "Subsequence Detection" section.

---

## 🔌 Integration

### **1. Widget Creation** (`ui/panels.py:404-405`)
```python
# Hash Debugging Tool
hash_debugger = HashDebugger()
layout.addWidget(hash_debugger)
```

### **2. Widget Reference Storage** (`ui/panels.py:422`)
```python
tab.hash_debugger = hash_debugger
```

### **3. Main Window Integration** (`main_window.py`)

**Declaration (line 120):**
```python
self.hash_debugger = None
```

**Extraction from params_tab (line 450):**
```python
self.hash_debugger = params_tab.hash_debugger
```

**VideoHasher Injection (lines 155-157):**
```python
# Set video hasher on hash debugger widget
if self.hash_debugger:
    self.hash_debugger.set_video_hasher(self.video_hasher)
```

---

## 📊 Output Format

### **Single Video Hash Output:**
```
======================================================================
HASH CALCULATION RESULTS
======================================================================
Hash Method: pHash

──────────────────────────────────────────────────────────────────────
File 1: test_video.mp4
Path: /home/user/videos/test_video.mp4
──────────────────────────────────────────────────────────────────────
✓ Hash calculated successfully
  Duration: 15.23s
  Calculation time: 0.456s
  Hash shape: (8, 8, 8)
  Hash dtype: bool

  Hash values (first 10 frames):
    Frame  0: 10101010101010101010101010101010 01010101010101010101010101010101
    Frame  1: 11001100110011001100110011001100 00110011001100110011001100110011
    Frame  2: 11110000111100001111000011110000 00001111000011110000111100001111
    ...
```

### **Two Video Comparison Output:**
```
======================================================================
COMPARISON RESULTS
======================================================================

File 1: video1.mp4
File 2: video2.mp4

Similarity: 92.45%

🔴 VERY HIGH similarity - Likely duplicates

──────────────────────────────────────────────────────────────────────
FRAME-BY-FRAME COMPARISON (first 10 frames)
──────────────────────────────────────────────────────────────────────
  Frame  0:  95.2% similarity ✓
  Frame  1:  93.8% similarity ✓
  Frame  2:  91.1% similarity ✓
  Frame  3:  89.7% similarity ✓
  Frame  4:  94.3% similarity ✓
  Frame  5:  96.1% similarity ✓
  Frame  6:  90.5% similarity ✓
  Frame  7:  92.9% similarity ✓
  Frame  8:  88.4% similarity ✓
  Frame  9:  93.6% similarity ✓
```

---

## 🔍 Debugging Black Area False Positives

### **Problem:**
Videos with large black areas (e.g., letterbox bars, fade to black, credits) may produce similar hashes even if content is different.

### **How to Use the Tool to Debug:**

1. **Create Test Videos:**
   - Video A: Original content
   - Video B: Different content with black areas

2. **Calculate Hashes:**
   - Select both videos in the debugger
   - Click "⚡ Calculate Hashes"

3. **Analyze Results:**
   - Check overall similarity score
   - Look at frame-by-frame comparison
   - Identify which frames have high similarity (likely the black frames)

4. **Binary Hash Visualization:**
   - Black frames typically produce hashes with many zeros
   - Compare the binary patterns of frames
   - Frames showing all zeros or repetitive patterns indicate solid black

### **Example Analysis:**
```
Frame  0:  95.2% similarity ✓  <- Black frame in both videos
Frame  1:  93.8% similarity ✓  <- Black frame in both videos
Frame  2:  45.3% similarity ✗  <- Different content (good!)
Frame  3:  48.7% similarity ✗  <- Different content (good!)
Frame  4:  92.1% similarity ✓  <- Black frame again
```

If many frames show high similarity but you know the videos are different, this indicates the black areas are dominating the hash comparison.

### **Potential Solutions:**
1. **Preprocessing:** Skip frames that are mostly black before hashing
2. **Hash Weighting:** Give less weight to frames with low variance (solid colors)
3. **Dynamic Frame Selection:** Sample frames from content-rich regions
4. **Threshold Adjustment:** Increase minimum match ratio to reduce false positives

---

## 🎯 Use Cases

### **1. Investigating False Positives**
- User reports two different videos marked as duplicates
- Use debugger to see why they're similar
- Check frame-by-frame to find problematic frames

### **2. Testing Hash Methods**
- Compare pHash vs dHash vs aHash on same videos
- See which method gives more accurate results for specific content types
- Understand binary hash patterns for different methods

### **3. Validating Fixes**
- After implementing black frame filtering
- Verify that previously matching videos now show lower similarity
- Ensure legitimate duplicates still match

### **4. Understanding Hash Behavior**
- Learn how perceptual hashing works
- See actual hash values for different video types
- Understand why certain videos produce similar hashes

---

## 💡 Tips for Users

1. **Select Representative Videos:**
   - Choose videos that exhibit the problem (e.g., black areas)
   - Include known duplicates and known different videos

2. **Use Frame-by-Frame Analysis:**
   - Look for patterns in which frames match
   - Identify if black/solid color frames are the issue

3. **Compare Hash Methods:**
   - Try different hash methods (pHash, dHash, aHash)
   - See if one method handles your content better

4. **Binary Visualization:**
   - All zeros/ones = solid color frame
   - Repetitive patterns = simple content
   - Random patterns = complex/detailed frames

5. **Document Findings:**
   - Copy results to report issues
   - Share hash patterns to help improve algorithm

---

## 📝 Files Modified

### **Created/Modified:**
1. **`progress_widgets.py`** (+307 lines)
   - Added `HashDebugger` class (lines 617-912)
   - Added imports for `os`, `numpy`, `QPushButton`, `QTextEdit`

2. **`ui/panels.py`** (+4 lines)
   - Import `HashDebugger` (line 16)
   - Create and add widget to Settings tab (lines 404-405)
   - Store widget reference (line 422)

3. **`main_window.py`** (+5 lines)
   - Declaration of `hash_debugger` (line 120)
   - Extract from params_tab (line 450)
   - Set video_hasher (lines 155-157)

---

## ✅ Testing Checklist

- ✅ Widget appears in Settings tab
- ✅ File selection dialog works
- ✅ Can select 1-2 videos (limit enforced)
- ✅ Calculate button enables when files selected
- ✅ Hash calculation completes successfully
- ✅ Results display in monospace font
- ✅ Binary hash visualization shows first 64 bits
- ✅ Two-video comparison shows similarity score
- ✅ Frame-by-frame comparison displays correctly
- ✅ Clear button resets widget state
- ✅ Uses same VideoHasher as main analysis
- ✅ Respects currently selected hash method

---

## 🚀 Future Enhancements

### **Potential Improvements:**
1. **More Frame Analysis:**
   - Show all frames, not just first 10
   - Scrollable frame list
   - Highlight frames with high/low similarity

2. **Export Results:**
   - Save results to text file
   - Export hash data for external analysis
   - Generate comparison reports

3. **Visual Hash Representation:**
   - Display frame thumbnails
   - Show hash as image (8x8 grid)
   - Overlay similarity heatmap

4. **Batch Comparison:**
   - Compare multiple videos at once
   - Generate similarity matrix
   - Identify clusters of similar videos

5. **Black Frame Detection:**
   - Automatically identify solid color frames
   - Show percentage of black/solid frames
   - Option to exclude from comparison

6. **Advanced Metrics:**
   - Histogram comparison
   - Color distribution analysis
   - Motion detection metrics

---

**Status:** ✅ **IMPLEMENTED AND COMMITTED**

**Commit:** `84ccb02` - "Add manual hash calculation debugging tool"
**Branch:** `claude/lit-duplicate-finder-018F2Fwua7gEjWbQdktfS1K5`
