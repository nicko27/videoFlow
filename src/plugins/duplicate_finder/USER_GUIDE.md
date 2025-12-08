# Duplicate Finder - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Main Features](#main-features)
4. [User Interface Overview](#user-interface-overview)
5. [Basic Workflow](#basic-workflow)
6. [Advanced Features](#advanced-features)
7. [Configuration Options](#configuration-options)
8. [Tips & Best Practices](#tips--best-practices)
9. [Keyboard Shortcuts](#keyboard-shortcuts)

---

## Introduction

Welcome to **Duplicate Finder**, a powerful video duplicate detection tool integrated into VideoFlow. This plugin helps you identify duplicate videos, similar clips, and subsequences across your video library using advanced perceptual hashing, audio fingerprinting, and machine learning techniques.

### What Can It Do?

- **Find Exact Duplicates**: Identify identical videos even with different file names
- **Detect Similar Videos**: Find videos with similar content at different resolutions or quality levels
- **Locate Subsequences**: Discover clips that appear within longer videos
- **Audio Matching**: Match videos by audio content using fingerprinting
- **Smart Filtering**: Use metadata filters to speed up analysis
- **Batch Processing**: Queue multiple analysis jobs for processing
- **Benchmarking**: Test and compare different detection methods

---

## Getting Started

### First Launch

When you first open Duplicate Finder, you'll see the Dashboard tab showing:
- Quick statistics (0 videos analyzed initially)
- Recent activity panel
- Quick action buttons

### Quick Start Tutorial

**5-Minute Quick Start:**

1. **Add Videos**
   - Click "Add Files" button or press `Ctrl+O`
   - Select one or more video files
   - Or drag & drop videos onto the file list

2. **Run Analysis**
   - Click "Analyze" button or press `F5`
   - Wait for analysis to complete
   - Progress bars show current status

3. **View Results**
   - Switch to "Filters" tab
   - See detected duplicate groups
   - Review and manage duplicates

---

## Main Features

### 1. Video Hash Comparison
Uses perceptual hashing to compare videos visually:
- **pHash (Perceptual Hash)**: Best for most use cases, resistant to minor changes
- **dHash (Difference Hash)**: Faster, good for exact matches
- **aHash (Average Hash)**: Fastest, less accurate
- **wHash (Wavelet Hash)**: Best for videos with transformations (rotation, cropping)

### 2. Audio Fingerprinting
Matches videos by audio content:
- **Precision Modes**: Fast, Balanced, or Precise
- **Threshold Control**: Adjust sensitivity (0.0-1.0)
- **Chromaprint Technology**: Industry-standard audio fingerprinting

### 3. LSH Optimization
Locality-Sensitive Hashing speeds up large-scale comparisons:
- **Automatic Candidate Selection**: Only compare likely matches
- **Configurable Bands/Rows**: Trade speed vs. accuracy
- **Recommended for 1000+ videos**

### 4. Multi-Resolution Analysis
Compare videos at multiple quality levels:
- **Robust to Quality Changes**: Find duplicates at different resolutions
- **Configurable Resolutions**: Choose which resolutions to analyze
- **Weighted Scoring**: Combine results intelligently

### 5. Metadata Filtering
Pre-filter candidates using video metadata:
- **Duration Tolerance**: Skip videos with very different lengths
- **File Size Ratio**: Ignore files with extreme size differences
- **Resolution Constraints**: Filter by video dimensions
- **Faster Analysis**: Reduce unnecessary comparisons

### 6. Scene Detection
Detect duplicates within longer videos:
- **PySceneDetect Integration**: Accurate scene boundary detection
- **Adaptive Thresholds**: Automatic sensitivity adjustment
- **Subsequence Matching**: Find clips within full-length videos

---

## User Interface Overview

### Dashboard Tab
- **Statistics Cards**: Videos analyzed, duplicates found, disk space
- **Recent Activity**: Latest analysis results
- **Quick Actions**: Start analysis, view results
- **System Status**: Cache size, database info

### Analysis Tab
Main analysis configuration and execution:

**File Management Section:**
- Add/remove video files
- File list with details (path, size, duration)
- Drag & drop support

**Video Comparison Parameters:**
- Similarity threshold (0-100%)
- Hash method selection (pHash, dHash, aHash, wHash)
- Worker count (parallel processing)
- Batch size and timeout settings

**Audio-First Mode:**
- Enable/disable audio fingerprinting
- Precision mode (Fast/Balanced/Precise)
- Audio threshold (0.0-1.0)
- Worker configuration

**LSH Optimization:**
- Enable/disable LSH
- Bands and rows configuration
- Min hash size setting

**Multi-Resolution Analysis:**
- Enable/disable multi-resolution
- Resolution selection (720p, 480p, 360p, 240p)
- Score weighting

**Metadata Filters:**
- Enable/disable filtering
- Duration tolerance (seconds)
- File size ratio (min/max)

**Cache Settings:**
- Enable/disable caching
- Cache size limit (MB)
- Clear cache button

**Detection Options:**
- Enable scene detection
- PySceneDetect threshold

### Filters Tab
Review and manage detected duplicates:

**Filter Controls:**
- Minimum similarity threshold
- File size filters
- Duration filters
- Resolution filters

**Results View:**
- Duplicate groups
- Similarity scores
- File details
- Preview thumbnails (if available)

**Actions:**
- Mark for deletion
- Keep best quality
- Export results
- Generate report

### Queue Tab
Batch processing management:

**Queue List:**
- Pending jobs
- Running jobs
- Completed jobs

**Job Controls:**
- Add to queue
- Pause/resume
- Cancel job
- View job details

**Queue Settings:**
- Max concurrent jobs
- Auto-start next job
- Priority ordering

---

## Basic Workflow

### Workflow 1: Find Exact Duplicates

**Goal**: Identify identical video files with different names.

**Steps**:
1. Add videos to analyze (Ctrl+O)
2. Set threshold to 95-100% (strict matching)
3. Use pHash or dHash method
4. Click "Analyze" (F5)
5. Review results in Filters tab
6. Select duplicates to delete or move

**Expected Time**: 1-5 minutes per 100 videos

### Workflow 2: Find Similar Videos

**Goal**: Locate videos with similar content at different qualities.

**Steps**:
1. Add videos to analyze
2. Enable Multi-Resolution Analysis
3. Set threshold to 80-90%
4. Use pHash method
5. Enable LSH if analyzing 1000+ videos
6. Run analysis
7. Review similarity groups

**Expected Time**: 3-10 minutes per 100 videos

### Workflow 3: Find Audio Duplicates

**Goal**: Match videos by audio content (different video, same audio).

**Steps**:
1. Add videos to analyze
2. Enable Audio-First Mode
3. Set precision to "Balanced" or "Precise"
4. Set audio threshold to 0.7-0.8
5. Run analysis
6. Review audio matches

**Expected Time**: 2-8 minutes per 100 videos

### Workflow 4: Find Clips in Full Videos

**Goal**: Detect short clips that appear within longer videos.

**Steps**:
1. Add videos (both clips and full videos)
2. Enable Scene Detection
3. Set PySceneDetect threshold (27.0 default)
4. Set video threshold to 85-95%
5. Run analysis
6. Review subsequence matches

**Expected Time**: 5-15 minutes per 100 videos

---

## Advanced Features

### Verification Pipelines

Create custom multi-stage verification workflows:

**Pipeline Modes**:
- **Filtering**: Early rejection to speed up analysis
- **Sequential**: Run methods in order, stop on match
- **Voting**: Combine results from multiple methods
- **Weighted**: Score-based combination

**Available Methods**:
- Metadata Filter
- Visual Hash (pHash, dHash, etc.)
- Audio Fingerprint
- Scene Detection
- Multi-Resolution
- LSH Pre-filtering

**Creating a Pipeline**:
1. Go to Settings or Advanced Configuration
2. Click "New Pipeline"
3. Select pipeline mode
4. Add verification methods
5. Configure method parameters
6. Save pipeline
7. Select pipeline for analysis

### Benchmark Testing

Test detection accuracy on known duplicate sets:

**Creating a Test Set**:
1. Go to Benchmark tab
2. Click "New Test Set"
3. Add video pairs
4. Mark expected results (duplicate/unique)
5. Save test set

**Running a Benchmark**:
1. Select test set
2. Select verification pipeline
3. Click "Run Benchmark"
4. View results:
   - Accuracy
   - Precision
   - Recall
   - F1 Score
   - Execution time

**Use Cases**:
- Compare different hash methods
- Optimize threshold values
- Test pipeline configurations
- Validate before large-scale analysis

### Import/Export

Share configurations across systems:

**Export Settings**:
1. Configure your analysis parameters
2. Go to Settings menu
3. Click "Export Settings"
4. Save JSON file

**Import Settings**:
1. Go to Settings menu
2. Click "Import Settings"
3. Select JSON file
4. Apply imported configuration

**Export Pipelines**:
- Save custom verification pipelines
- Share with team members
- Version control for configurations

**Export Results**:
- Export duplicate groups to CSV
- Generate HTML reports
- Save analysis statistics

---

## Configuration Options

### Video Comparison Parameters

**Similarity Threshold** (0-100%):
- **95-100%**: Exact duplicates only
- **85-95%**: Very similar (different quality/resolution)
- **75-85%**: Similar content (edits, crops, filters)
- **60-75%**: Loosely similar (same scene, different angle)

**Hash Method**:
- **pHash**: Default, best balance of speed/accuracy
- **dHash**: Faster, good for exact matches
- **aHash**: Fastest, less accurate
- **wHash**: Best for transformed videos

**Hash Workers** (1-16):
- Set to number of CPU cores
- More workers = faster (up to CPU limit)
- Recommended: 4-8 for most systems

**Batch Size** (10-1000):
- Number of videos processed per batch
- Larger = more memory, faster processing
- Smaller = less memory, slower processing
- Recommended: 100-500

**Hash Timeout** (30-600 seconds):
- Max time per video
- Increase for very large files
- Default: 300s (5 minutes)

### Audio-First Mode

**When to Enable**:
- Matching videos by audio content
- Videos with different visuals but same audio
- Music video duplicates
- Podcast/interview duplicates

**Precision Modes**:
- **Fast**: Quick analysis, less accurate
- **Balanced**: Good speed/accuracy trade-off (recommended)
- **Precise**: Slower, most accurate

**Audio Threshold** (0.0-1.0):
- **0.9-1.0**: Very strict, exact audio matches
- **0.7-0.9**: Similar audio (different bitrates)
- **0.5-0.7**: Loosely similar audio
- **Below 0.5**: Not recommended (too many false positives)

### LSH Optimization

**When to Enable**:
- Analyzing 1000+ videos
- Large video libraries
- Need faster results

**Bands** (10-30):
- More bands = faster, less accurate
- Fewer bands = slower, more accurate
- Recommended: 20

**Rows** (3-10):
- More rows = more accurate, slower
- Fewer rows = faster, less accurate
- Recommended: 5

**Formula**: `bands × rows = total hash bits`

### Multi-Resolution Analysis

**When to Enable**:
- Videos at different resolutions
- Different quality levels
- Different encodings

**Resolutions**:
- **720p**: HD quality
- **480p**: SD quality
- **360p**: Low quality
- **240p**: Very low quality

**Score Weighting**:
- Higher weight to higher resolutions
- Automatic weighted averaging
- More robust duplicate detection

### Metadata Filtering

**Duration Tolerance** (0-60 seconds):
- Skip videos with very different lengths
- Reduce false positives
- Speed up analysis
- Recommended: 5-10 seconds

**File Size Ratio** (0.1-10.0):
- Minimum ratio: 0.5 (half the size)
- Maximum ratio: 2.0 (double the size)
- Ignore extreme size differences

**When to Enable**:
- Large video collections
- Known similar file sizes
- Speed optimization needed

---

## Tips & Best Practices

### Performance Optimization

**For Small Collections (< 100 videos)**:
- Disable LSH optimization
- Use higher worker count
- Single-resolution analysis
- Disable metadata filters

**For Medium Collections (100-1000 videos)**:
- Consider LSH if needed
- Enable metadata filters
- Use batch size 200-500
- 4-8 workers

**For Large Collections (1000+ videos)**:
- Enable LSH optimization
- Enable metadata filters
- Use batch size 500-1000
- Max out workers (CPU cores)
- Enable caching

### Accuracy Optimization

**For Best Accuracy**:
- Use pHash or wHash
- Enable multi-resolution
- Set threshold to 80-85%
- Enable audio fingerprinting
- Use verification pipelines with voting mode

**For Speed Over Accuracy**:
- Use dHash or aHash
- Single resolution
- Set threshold to 90-95%
- Disable audio fingerprinting
- Enable LSH with more bands

### Memory Management

**If Running Out of Memory**:
- Reduce batch size
- Reduce worker count
- Disable multi-resolution
- Process in smaller groups
- Clear cache regularly

**Recommended Memory**:
- Small collections: 2-4 GB
- Medium collections: 4-8 GB
- Large collections: 8-16 GB

### Storage Management

**Cache Management**:
- Set cache size limit (MB)
- Clear cache periodically
- Cache speeds up re-analysis
- Stored in plugin directory

**Database Management**:
- SQLite database stores results
- Location: `video_duplicates.db`
- Backup regularly
- Can be deleted to reset

---

## Keyboard Shortcuts

### Global Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Add Files |
| `Ctrl+P` or `F5` | Start Analysis |
| `Ctrl+.` or `Escape` | Stop Analysis |
| `Ctrl+R` | Reload Settings |
| `Ctrl+S` | Save Settings |
| `Ctrl+Q` | Quit Plugin |

### Analysis Tab

| Shortcut | Action |
|----------|--------|
| `Ctrl+A` | Select All Files |
| `Delete` | Remove Selected Files |
| `Ctrl+Delete` | Clear All Files |

### Filters Tab

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` | Focus Search |
| `Space` | Toggle Selection |
| `Ctrl+E` | Export Results |

### Navigation

| Shortcut | Action |
|----------|--------|
| `Tab` | Next Tab |
| `Shift+Tab` | Previous Tab |
| `Ctrl+1-4` | Jump to Tab (1=Dashboard, 2=Analysis, 3=Filters, 4=Queue) |

---

## Getting Help

### Resources

- **FAQ**: See `FAQ.md` for common questions
- **Troubleshooting**: See `TROUBLESHOOTING.md` for common issues
- **API Reference**: See `API_REFERENCE.md` for developers
- **GitHub**: Report issues and feature requests

### Support

If you encounter issues:
1. Check TROUBLESHOOTING.md
2. Review FAQ.md
3. Check GitHub issues
4. Create new issue with:
   - Plugin version
   - Operating system
   - Steps to reproduce
   - Error messages
   - Log files (if available)

---

## Version Information

**Current Version**: 3.0
**Last Updated**: December 2025
**Compatibility**: VideoFlow 2.0+

---

## License

This plugin is part of VideoFlow.
See main application license for details.

---

**Happy Duplicate Finding!** 🎬
