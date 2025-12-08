# Duplicate Finder - Interactive Tutorial

## Welcome! 👋

This interactive tutorial will guide you through using Duplicate Finder, from your first analysis to advanced features. Follow along at your own pace!

## Table of Contents
1. [Tutorial 1: Your First Analysis (5 minutes)](#tutorial-1-your-first-analysis)
2. [Tutorial 2: Finding Similar Videos (10 minutes)](#tutorial-2-finding-similar-videos)
3. [Tutorial 3: Audio-Based Matching (10 minutes)](#tutorial-3-audio-based-matching)
4. [Tutorial 4: Advanced Configuration (15 minutes)](#tutorial-4-advanced-configuration)
5. [Tutorial 5: Benchmarking & Optimization (20 minutes)](#tutorial-5-benchmarking--optimization)
6. [Tips & Tricks](#tips--tricks)
7. [Common Scenarios](#common-scenarios)
8. [Video Tutorial Script](#video-tutorial-script)

---

## Tutorial 1: Your First Analysis

**Goal**: Find exact duplicate videos in a small collection

**Time**: 5 minutes

**What you'll learn**:
- Adding videos to analyze
- Running your first analysis
- Viewing and understanding results

### Step 1: Launch Duplicate Finder

1. Open VideoFlow
2. Go to **Plugins** → **Duplicate Finder**
3. The main window opens showing 4 tabs: Dashboard, Analysis, Filters, Queue

**What you see**:
- Dashboard shows "0 videos analyzed" (initial state)
- Recent activity panel is empty
- Quick action buttons are available

### Step 2: Add Videos

1. Click on the **Analysis** tab
2. Click the **"Add Files"** button (or press `Ctrl+O`)
3. Navigate to a folder with videos
4. Select 5-10 video files
5. Click **Open**

**What happens**:
- Selected videos appear in the file list
- Each row shows: filename, path, size, duration
- Status bar shows: "✅ 5 file(s) added - Total: 5 files"

**Tip**: You can also drag & drop videos directly onto the file list!

### Step 3: Check Default Settings

Look at the **Video Comparison Parameters** section:

```
✓ Similarity Threshold: 85%
✓ Hash Method: pHash (recommended)
✓ Hash Workers: 4 (auto-detected from CPU)
✓ Batch Size: 100
```

**For your first analysis, these defaults are perfect!** ✨

### Step 4: Start Analysis

1. Click the **"Analyze"** button (or press `F5`)
2. Watch the progress bars update in real-time

**What happens**:
```
🔄 Starting analysis of 5 files...
Progress: [████████░░░░░░░░░░░░] 40% (2/5)
Hash Computation: [███████████████░░░░] 75%
```

**Estimated time**: 10-30 seconds for 5 small videos

### Step 5: View Results

1. When analysis completes, switch to the **Filters** tab
2. You see duplicate groups (if any found)

**Example result**:
```
┌─ Duplicate Group 1 (Similarity: 100%)
│  📹 vacation_2024.mp4     (1.2 GB)
│  📹 vacation_2024_copy.mp4 (1.2 GB)
└─────────────────────────────────────

┌─ Duplicate Group 2 (Similarity: 95%)
│  📹 birthday_hd.mp4       (850 MB)
│  📹 birthday_720p.mp4     (320 MB)
└─────────────────────────────────────
```

### Step 6: Take Action

For each duplicate group, you can:
- ✅ **Keep Best**: Automatically keep highest quality
- ❌ **Delete Duplicates**: Remove lower quality copies
- 📋 **Review Manually**: Inspect before deciding
- 📤 **Export List**: Save results to CSV

**Congratulations!** 🎉 You've completed your first analysis!

---

## Tutorial 2: Finding Similar Videos

**Goal**: Find videos that are similar but not identical (different quality, edited, etc.)

**Time**: 10 minutes

**What you'll learn**:
- Multi-resolution analysis
- Adjusting similarity threshold
- Handling quality variations

### Scenario

You have:
- Same video at different resolutions (1080p, 720p, 480p)
- Videos with slight edits (intro/outro added)
- Re-encoded versions

### Step 1: Prepare Your Collection

Add videos that might be similar:
- Original: `movie_1080p.mp4`
- Lower quality: `movie_720p.mp4`
- Re-encoded: `movie_compressed.mp4`
- Edited version: `movie_with_intro.mp4`

### Step 2: Enable Multi-Resolution Analysis

1. Go to **Analysis** tab
2. Scroll to **Multi-Resolution Analysis** section
3. Check **"Enable multi-resolution"**
4. Select resolutions to analyze:
   - ✅ 720p (recommended)
   - ✅ 480p
   - ✅ 360p

**Why?** This makes detection robust to quality changes!

### Step 3: Adjust Threshold

1. In **Video Comparison Parameters**
2. Set **Similarity Threshold** to **80%** (less strict)

**Threshold guide**:
- **95-100%**: Exact duplicates only
- **85-95%**: Very similar (different quality)
- **75-85%**: Similar content (edits, crops)
- **60-75%**: Loosely similar

For quality variations, **80-85%** works well!

### Step 4: Configure Hash Method

Keep **pHash** (default) - it's best for quality variations.

**Hash method comparison**:
| Method | Speed | Accuracy | Best For |
|--------|-------|----------|----------|
| pHash  | ⭐⭐⭐ | ⭐⭐⭐⭐ | Quality variations ✓ |
| dHash  | ⭐⭐⭐⭐ | ⭐⭐⭐ | Exact duplicates |
| aHash  | ⭐⭐⭐⭐⭐ | ⭐⭐ | Quick scans |
| wHash  | ⭐⭐ | ⭐⭐⭐⭐⭐ | Cropped/rotated |

### Step 5: Run Analysis

1. Click **"Analyze"** (`F5`)
2. Watch progress - multi-resolution takes a bit longer
3. Wait for completion

### Step 6: Review Results

In **Filters** tab, you'll see groups with lower similarity:

```
┌─ Group 1 (Similarity: 92%)
│  📹 movie_1080p.mp4        (4.5 GB, 1920x1080)
│  📹 movie_720p.mp4         (1.8 GB, 1280x720)
│  📹 movie_compressed.mp4   (850 MB, 1920x1080)
└──────────────────────────────────────────────

┌─ Group 2 (Similarity: 78%)
│  📹 movie_1080p.mp4        (4.5 GB)
│  📹 movie_with_intro.mp4   (4.7 GB)
└──────────────────────────────────────────────
```

### Step 7: Smart Filtering

Use the filter controls:
- **Min Similarity**: 75%
- **File Size Range**: Any
- **Resolution**: Any

**Result**: See all matches above 75% similarity!

### Success! 🎯

You can now find:
- ✅ Videos at different resolutions
- ✅ Re-encoded versions
- ✅ Slightly edited videos

---

## Tutorial 3: Audio-Based Matching

**Goal**: Find videos with same audio but different visuals

**Time**: 10 minutes

**What you'll learn**:
- Audio fingerprinting
- Matching by audio content
- Finding re-uploads with different graphics

### Scenario

You have:
- Music video with original visuals
- Same music video with fan-made visuals
- Podcast with different background videos
- Same interview with different camera angles

### Step 1: Enable Audio-First Mode

1. Go to **Analysis** tab
2. Find **Audio-First Mode** section
3. Check **"Enable audio fingerprinting"**

**What happens**: Videos will be matched by audio content!

### Step 2: Configure Audio Settings

```
✓ Audio Threshold: 0.7 (70% similarity)
✓ Precision Mode: Balanced (recommended)
✓ Workers: 2
```

**Precision modes**:
- **Fast**: Quick scan, less accurate
- **Balanced**: Good speed/accuracy ⭐ (recommended)
- **Precise**: Slower, most accurate

### Step 3: Set Audio Threshold

**Threshold guide** (0.0 - 1.0):
- **0.9-1.0**: Exact audio match
- **0.7-0.9**: Very similar audio ⭐ (recommended)
- **0.5-0.7**: Somewhat similar
- **< 0.5**: Too many false positives

Start with **0.7** and adjust if needed!

### Step 4: Add Audio-Heavy Videos

Add videos where audio is important:
- Music videos
- Podcasts
- Interviews
- Presentations with voiceover

### Step 5: Run Analysis

1. Click **"Analyze"** (`F5`)
2. Progress shows two phases:
   ```
   Phase 1: Audio fingerprinting...
   Phase 2: Visual comparison...
   ```
3. Wait for completion

**Note**: Audio fingerprinting requires `chromaprint` (fpcalc)

### Step 6: Review Audio Matches

Results show audio similarity:

```
┌─ Audio Match (Audio: 95%, Visual: 45%)
│  🎵 music_video_original.mp4
│  🎵 music_video_fanmade.mp4
└──────────────────────────────────────

┌─ Audio Match (Audio: 88%, Visual: 92%)
│  🎵 interview_cam1.mp4
│  🎵 interview_cam2.mp4
└──────────────────────────────────────
```

**Notice**: First group has same audio but different video!

### Step 7: Use Cases

Audio matching is perfect for:
- 🎵 Finding music video re-uploads
- 🎙️ Detecting podcast duplicates
- 📺 Finding same content with different graphics
- 🎬 Identifying interviews from different angles

### Pro Tip! 💡

Combine audio + visual for best results:
```
✓ Enable audio fingerprinting
✓ Enable multi-resolution
✓ Threshold: Video 80%, Audio 0.7
```

This catches both visual AND audio duplicates!

---

## Tutorial 4: Advanced Configuration

**Goal**: Optimize for large collections and specific use cases

**Time**: 15 minutes

**What you'll learn**:
- LSH optimization for speed
- Metadata filtering
- Cache management
- Custom verification pipelines

### Part A: LSH Optimization (Large Collections)

**When**: You have 1000+ videos

**What**: LSH = Locality-Sensitive Hashing (fast candidate selection)

#### Steps:

1. **Enable LSH**:
   ```
   ✓ Enable LSH optimization
   ```

2. **Configure LSH**:
   ```
   Bands: 20 (default)
   Rows: 5 (default)
   Min hash size: 100
   ```

3. **How it works**:
   ```
   Without LSH: Compare ALL pairs = 10,000 videos = 50 million comparisons
   With LSH: Pre-filter candidates = 10,000 videos = ~100,000 comparisons

   Result: 500x faster! ⚡
   ```

4. **Trade-off**:
   - ✅ Much faster (90% reduction)
   - ⚠️ Slight accuracy loss (~5%)
   - ✅ Worth it for large collections!

### Part B: Metadata Filtering (Smart Pre-filtering)

**When**: Videos have very different metadata

**What**: Skip obviously different videos before analysis

#### Steps:

1. **Enable Metadata Filters**:
   ```
   ✓ Enable metadata filtering
   ```

2. **Configure Filters**:
   ```
   Duration Tolerance: 5 seconds
   File Size Ratio: 0.5 - 2.0 (min - max)
   ```

3. **How it works**:
   ```
   Video A: 120 seconds, 500 MB
   Video B: 180 seconds, 50 MB

   Duration diff: 60s > 5s ✗
   Size ratio: 0.1 < 0.5 ✗

   Result: SKIP comparison (obviously different)
   ```

4. **Benefits**:
   - ⚡ Faster analysis
   - ✅ Fewer false positives
   - 💾 Less resource usage

### Part C: Cache Management

**What**: Store computed hashes to avoid recomputation

#### Steps:

1. **Enable Cache**:
   ```
   ✓ Enable caching
   Cache Size: 500 MB
   ```

2. **How it works**:
   ```
   First analysis: Compute hash → Save to cache
   Second analysis: Load hash from cache ⚡

   Result: 10x faster for repeated analysis!
   ```

3. **Clear Cache**:
   - Click **"Clear Cache"** button
   - Frees disk space
   - Next analysis will recompute

### Part D: Custom Verification Pipelines

**What**: Multi-stage verification workflows

**When**: You want custom detection logic

#### Creating a Pipeline:

1. **Open Pipeline Configuration** (Advanced Settings)

2. **Create New Pipeline**:
   ```
   Name: "My Custom Pipeline"
   Mode: Filtering (fast rejection)
   ```

3. **Add Methods** (in order):
   ```
   Stage 1: Metadata Filter (quick reject)
     ↓ (keep only similar metadata)
   Stage 2: LSH Pre-filter (candidate selection)
     ↓ (keep only LSH candidates)
   Stage 3: Visual Hash (final verification)
     ↓ (confirm duplicates)
   Result: Fast + Accurate! ✨
   ```

4. **Pipeline Modes**:
   - **Filtering**: Stop at first rejection (fastest)
   - **Sequential**: Run all, stop at first match
   - **Voting**: Majority vote from all methods
   - **Weighted**: Score-based combination

### Part E: Performance Tuning

**Optimize for your hardware**:

```python
# For 8-core CPU:
Hash Workers: 6-8
Batch Size: 500
Timeout: 300s

# For 4-core CPU:
Hash Workers: 3-4
Batch Size: 200
Timeout: 300s

# Low memory system:
Hash Workers: 2
Batch Size: 50
Disable multi-resolution
```

**Monitor resources** while analyzing!

---

## Tutorial 5: Benchmarking & Optimization

**Goal**: Test and optimize detection accuracy

**Time**: 20 minutes

**What you'll learn**:
- Creating test sets
- Running benchmarks
- Interpreting metrics
- Optimizing configuration

### Part A: Creating a Test Set

**Purpose**: Known duplicate pairs for testing

#### Steps:

1. **Go to Benchmark Tab**

2. **Click "New Test Set"**

3. **Add Pairs**:
   ```
   Pair 1:
     Video 1: original_1080p.mp4
     Video 2: copy_1080p.mp4
     Expected: DUPLICATE ✓

   Pair 2:
     Video 1: original_1080p.mp4
     Video 2: different_video.mp4
     Expected: UNIQUE ✗

   Pair 3:
     Video 1: original_1080p.mp4
     Video 2: original_720p.mp4
     Expected: DUPLICATE ✓
   ```

4. **Save Test Set**: "Quality Variations Test"

**Best practices**:
- Include exact duplicates
- Include quality variations
- Include unique videos
- Include edge cases

### Part B: Creating a Benchmark Pipeline

1. **Click "New Pipeline"**

2. **Configure**:
   ```
   Name: "pHash Balanced"
   Mode: Sequential
   Methods:
     - Visual Hash (pHash, threshold 85%)
     - Multi-resolution (720p, 480p)
   ```

3. **Save Pipeline**

### Part C: Running the Benchmark

1. **Select Test Set**: "Quality Variations Test"
2. **Select Pipeline**: "pHash Balanced"
3. **Click "Run Benchmark"**

#### What happens:

```
🔄 Running benchmark...
Testing pair 1/10...
Testing pair 2/10...
...
✅ Benchmark complete!
```

### Part D: Understanding Results

**Metrics explained**:

```
Accuracy: 92%
  → Overall correctness (TP + TN) / Total

Precision: 95%
  → Of detected duplicates, how many are real?
  → TP / (TP + FP)
  → High precision = Few false positives

Recall: 88%
  → Of real duplicates, how many were found?
  → TP / (TP + FN)
  → High recall = Few missed duplicates

F1 Score: 91%
  → Harmonic mean of precision and recall
  → Balanced measure (higher is better)

Execution Time: 45.2s
  → Total processing time
```

**Visual explanation**:

```
Test Set: 10 pairs (6 duplicates, 4 unique)

Results:
  ✅ True Positives (TP): 5 (correctly identified duplicates)
  ❌ False Positives (FP): 1 (incorrectly marked as duplicate)
  ✅ True Negatives (TN): 3 (correctly identified as unique)
  ❌ False Negatives (FN): 1 (missed duplicate)

Precision = 5 / (5+1) = 83%
Recall = 5 / (5+1) = 83%
F1 = 2 × (83×83) / (83+83) = 83%
```

### Part E: Optimization Workflow

**Goal**: Find best configuration

#### Experiment 1: Hash Methods

Test different hash methods:

```
Benchmark A: pHash
  F1 Score: 91%
  Time: 45s

Benchmark B: dHash
  F1 Score: 88%
  Time: 30s ⚡

Benchmark C: wHash
  F1 Score: 94% ⭐
  Time: 60s
```

**Decision**: Use wHash for best accuracy!

#### Experiment 2: Thresholds

Test different thresholds:

```
Threshold 95%:
  Precision: 98% ⭐
  Recall: 75%

Threshold 85%:
  Precision: 92%
  Recall: 88%

Threshold 75%:
  Precision: 78%
  Recall: 95% ⭐
```

**Decision**:
- Need high precision? → 95%
- Need balanced? → 85% ⭐
- Need high recall? → 75%

#### Experiment 3: Multi-Resolution

```
Single resolution:
  F1 Score: 85%

Multi-resolution (720p, 480p):
  F1 Score: 92% ⭐ (+7%)
  Time: +20%
```

**Decision**: Multi-resolution worth the cost!

### Part F: Your Optimal Configuration

Based on benchmarks, create your optimal config:

```
✓ Hash Method: wHash (best accuracy)
✓ Threshold: 85% (balanced)
✓ Multi-resolution: Enabled (720p, 480p)
✓ LSH: Enabled (for speed on large sets)
✓ Audio: Enabled (catch audio matches)

Expected Performance:
  Accuracy: 94%
  Speed: Fast (with LSH)
  Use case: General duplicate detection
```

**Save this as a preset!** 💾

---

## Tips & Tricks

### Performance Tips

**🚀 Speed up analysis:**
```
1. Enable LSH for 1000+ videos
2. Enable metadata filtering
3. Use faster hash (dHash instead of pHash)
4. Disable audio if not needed
5. Single resolution instead of multi
6. Increase batch size (500-1000)
7. Max out workers (= CPU cores)
```

**💾 Reduce memory usage:**
```
1. Reduce batch size (50-100)
2. Reduce workers (2-4)
3. Disable multi-resolution
4. Process in smaller groups
5. Clear cache before analysis
```

**🎯 Improve accuracy:**
```
1. Use pHash or wHash
2. Enable multi-resolution
3. Lower threshold (75-80%)
4. Enable audio fingerprinting
5. Use verification pipelines (voting mode)
```

### Keyboard Shortcuts

**Master these for efficiency:**

```
Ctrl+O    → Add Files (quick add)
F5        → Start Analysis (instant start)
Escape    → Stop Analysis (quick cancel)
Ctrl+R    → Reload Settings (reset to saved)
Ctrl+S    → Save Settings (quick save)

Ctrl+F    → Focus search in Filters tab
Ctrl+E    → Export results (quick export)

Ctrl+1-4  → Jump between tabs
Tab       → Next tab
Shift+Tab → Previous tab
```

### Common Mistakes to Avoid

**❌ Don't:**
- Set threshold too low (< 70%) → Too many false positives
- Use aHash for quality variations → Inaccurate
- Enable all features for small collections → Overkill
- Forget to clear cache before fresh analysis → Stale data
- Delete duplicates without reviewing → Dangerous!

**✅ Do:**
- Start with defaults → Adjust based on results
- Test with small sample → Then scale up
- Create backups before deleting → Safety first
- Use benchmarks → Validate configuration
- Review results manually → Verify before action

---

## Common Scenarios

### Scenario 1: Cleaning Up Phone Videos

**Problem**: Many duplicate photos/videos from phone backup

**Solution**:
```
1. Add all phone videos
2. Settings:
   - Threshold: 95% (exact or near-exact)
   - Hash: dHash (fast)
   - Multi-resolution: Disabled
3. Analyze
4. Review results
5. Keep best quality, delete rest
```

**Time**: 5-10 minutes for 100 videos

### Scenario 2: Video Archive Deduplication

**Problem**: Large video archive with many duplicates at different qualities

**Solution**:
```
1. Add archive videos (thousands)
2. Settings:
   - Threshold: 85% (quality variations)
   - Hash: pHash
   - Multi-resolution: Enabled
   - LSH: Enabled (for speed)
3. Analyze (may take hours)
4. Filter: Min similarity 90%
5. Export results to CSV
6. Review and delete in batches
```

**Time**: 1-4 hours for 10,000 videos

### Scenario 3: Finding Re-uploaded Content

**Problem**: Find if your videos were re-uploaded elsewhere

**Solution**:
```
1. Add your original videos + suspicious videos
2. Settings:
   - Threshold: 75% (allow edits)
   - Hash: wHash (robust to crops)
   - Multi-resolution: Enabled
   - Audio: Enabled (catch audio theft)
3. Analyze
4. Review matches with your originals
```

**Detects**:
- Re-uploads with watermarks
- Cropped/edited versions
- Different quality re-uploads

### Scenario 4: Music Video Collection

**Problem**: Music videos with multiple versions (official, live, cover)

**Solution**:
```
1. Add all music videos
2. Settings:
   - Audio: Enabled + Precise mode
   - Audio threshold: 0.8
   - Video threshold: 70% (allow different visuals)
3. Analyze
4. Group by audio similarity
```

**Finds**:
- Same song, different performances
- Official vs live versions
- Covers of same song

---

## Video Tutorial Script

**This script can be used to create a video tutorial**

### Video 1: Getting Started (3 minutes)

```
[INTRO - 10 seconds]
Title: "Duplicate Finder - Getting Started"

[STEP 1 - 20 seconds]
Voice: "Welcome to Duplicate Finder! Let's find your first duplicates."
Screen: Show VideoFlow main window
Action: Navigate to Plugins → Duplicate Finder

[STEP 2 - 30 seconds]
Voice: "First, add some videos to analyze."
Screen: Show Analysis tab
Action: Click Add Files
Action: Select 5 videos
Voice: "You can also drag and drop videos directly."
Action: Drag & drop demonstration

[STEP 3 - 20 seconds]
Voice: "Check the default settings - they're perfect for getting started!"
Screen: Highlight Video Comparison Parameters
Voice: "85% threshold, pHash method, 4 workers"

[STEP 4 - 40 seconds]
Voice: "Now click Analyze and watch the magic happen!"
Screen: Click Analyze button
Action: Show progress bars filling
Voice: "The progress bars show real-time status."
Screen: Analysis completes

[STEP 5 - 30 seconds]
Voice: "Switch to Filters tab to see your results."
Screen: Show duplicate groups
Voice: "Here are your duplicates! You can keep best quality or delete copies."
Action: Show action buttons

[OUTRO - 10 seconds]
Voice: "That's it! You've found your first duplicates. Check out the advanced tutorials for more!"
```

### Video 2: Advanced Features (5 minutes)

```
[INTRO - 10 seconds]
Title: "Duplicate Finder - Advanced Features"

[SEGMENT 1: Multi-Resolution - 60 seconds]
Voice: "Find duplicates at different quality levels..."
Action: Enable multi-resolution
Action: Run analysis
Result: Show quality variation matches

[SEGMENT 2: Audio Matching - 60 seconds]
Voice: "Match videos by audio content..."
Action: Enable audio fingerprinting
Action: Configure settings
Result: Show audio-based matches

[SEGMENT 3: LSH Optimization - 60 seconds]
Voice: "Speed up large collections with LSH..."
Action: Enable LSH
Action: Show before/after performance

[SEGMENT 4: Benchmarking - 90 seconds]
Voice: "Test and optimize your configuration..."
Action: Create test set
Action: Run benchmark
Result: Show metrics explanation

[OUTRO - 30 seconds]
Voice: "Now you're a power user! Explore more in the documentation."
```

### Video 3: Real-World Scenarios (7 minutes)

```
[Each scenario: 90 seconds]

1. Phone Video Cleanup
2. Archive Deduplication
3. Re-upload Detection
4. Music Video Organization

[Structure per scenario]
- Problem introduction (15s)
- Configuration walkthrough (45s)
- Results demonstration (30s)
```

---

## Practice Exercises

### Exercise 1: Basic Duplicate Detection

**Task**: Find exact duplicates in a test folder

**Steps**:
1. Create folder with 10 videos (include 2 duplicate pairs)
2. Analyze with defaults
3. Verify results match expectations

**Expected time**: 5 minutes

### Exercise 2: Quality Variation Detection

**Task**: Find same video at different resolutions

**Setup**:
1. Take one video
2. Create 720p, 480p, 360p versions
3. Analyze with multi-resolution enabled

**Challenge**: All versions should match!

**Expected time**: 10 minutes

### Exercise 3: Benchmark Creation

**Task**: Create and run your first benchmark

**Steps**:
1. Create test set with 5 pairs
2. Create custom pipeline
3. Run benchmark
4. Achieve >80% F1 score

**Expected time**: 15 minutes

### Exercise 4: Optimization Challenge

**Task**: Find fastest configuration for 1000 videos

**Constraints**:
- Must maintain >85% accuracy
- Minimize processing time

**Hint**: LSH + metadata filtering + dHash

**Expected time**: 20 minutes

---

## Next Steps

**You've completed the tutorial! 🎉**

### Continue Learning:

1. **Read Documentation**:
   - USER_GUIDE.md (comprehensive reference)
   - FAQ.md (common questions)
   - TROUBLESHOOTING.md (problem solving)

2. **Explore Advanced Features**:
   - Custom verification pipelines
   - Benchmark optimization
   - Import/export configurations

3. **Join Community**:
   - GitHub Discussions
   - Report bugs
   - Suggest features

### Quick Reference Card

```
┌─────────────────────────────────────────┐
│        Duplicate Finder Cheatsheet      │
├─────────────────────────────────────────┤
│                                         │
│ QUICK START:                            │
│   1. Add files (Ctrl+O)                 │
│   2. Keep defaults                      │
│   3. Analyze (F5)                       │
│   4. View results (Filters tab)         │
│                                         │
│ QUALITY VARIATIONS:                     │
│   - Enable Multi-Resolution             │
│   - Threshold: 80-85%                   │
│   - Hash: pHash or wHash                │
│                                         │
│ LARGE COLLECTIONS:                      │
│   - Enable LSH                          │
│   - Enable Metadata Filters             │
│   - Increase Batch Size                 │
│                                         │
│ AUDIO MATCHING:                         │
│   - Enable Audio-First Mode             │
│   - Threshold: 0.7                      │
│   - Mode: Balanced                      │
│                                         │
│ SHORTCUTS:                              │
│   F5: Analyze   Esc: Stop               │
│   Ctrl+O: Add   Ctrl+S: Save            │
│                                         │
└─────────────────────────────────────────┘
```

---

## Feedback

**How was this tutorial?**

Help us improve:
- What was confusing?
- What was helpful?
- What's missing?
- Suggestions?

**Report issues**: GitHub Issues
**Ask questions**: GitHub Discussions

---

**Happy Duplicate Finding!** 🎬✨

**Version**: 1.0
**Last Updated**: December 2025
**Video Tutorial Status**: Script ready for recording
