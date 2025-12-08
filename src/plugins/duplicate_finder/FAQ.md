# Duplicate Finder - Frequently Asked Questions (FAQ)

## Table of Contents
1. [General Questions](#general-questions)
2. [Getting Started](#getting-started)
3. [Analysis & Detection](#analysis--detection)
4. [Performance & Speed](#performance--speed)
5. [Accuracy & Results](#accuracy--results)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Features](#advanced-features)

---

## General Questions

### What is Duplicate Finder?

Duplicate Finder is a plugin for VideoFlow that helps you identify duplicate videos, similar clips, and subsequences in your video library using advanced computer vision and audio analysis techniques.

### What types of duplicates can it find?

- **Exact duplicates**: Identical files with different names
- **Quality variations**: Same video at different resolutions/bitrates
- **Re-encoded videos**: Videos re-encoded with different codecs
- **Cropped/rotated videos**: Videos with transformations
- **Audio matches**: Different videos with the same audio
- **Subsequences**: Clips that appear within longer videos

### Is it free to use?

Duplicate Finder is included with VideoFlow. Check the main application license for terms.

### What video formats are supported?

All formats supported by FFmpeg/OpenCV:
- MP4, AVI, MKV, MOV, WMV, FLV
- WebM, MPEG, 3GP, OGG
- And many more

### Does it work on Windows/Mac/Linux?

Yes! Duplicate Finder works on all platforms supported by VideoFlow:
- Windows 10/11
- macOS 10.15+
- Linux (Ubuntu 20.04+, Fedora, etc.)

---

## Getting Started

### How do I install Duplicate Finder?

Duplicate Finder is a built-in plugin for VideoFlow:
1. Install VideoFlow
2. Launch VideoFlow
3. Access Duplicate Finder from the Plugins menu

### Do I need any additional software?

Optional dependencies for advanced features:
- **PySceneDetect**: For scene detection (subsequence matching)
- **Chromaprint/fpcalc**: For audio fingerprinting
- **FFmpeg**: For video processing (usually bundled)

### How do I get started quickly?

**3-Step Quick Start**:
1. Click "Add Files" and select videos
2. Click "Analyze" (or press F5)
3. View results in the "Filters" tab

See USER_GUIDE.md for detailed tutorials.

### Where are the analysis results stored?

Results are stored in a SQLite database:
- Location: `src/plugins/duplicate_finder/video_duplicates.db`
- Automatically created on first use
- Can be backed up or deleted to reset

### Can I use it on external drives or network storage?

Yes! You can analyze videos anywhere your system can access them:
- Local drives
- External USB drives
- Network shares (SMB, NFS)
- Cloud storage (if mounted locally)

**Note**: Network storage may be slower for analysis.

---

## Analysis & Detection

### How long does analysis take?

**Approximate times** (on modern hardware):

| Video Count | Small Videos (< 100MB) | Large Videos (> 1GB) |
|-------------|------------------------|----------------------|
| 10 videos   | 10-30 seconds         | 1-3 minutes          |
| 100 videos  | 1-5 minutes           | 10-30 minutes        |
| 1000 videos | 10-30 minutes         | 1-3 hours            |

**Factors affecting speed**:
- Video file size and resolution
- Number of workers (CPU cores)
- Enabled features (audio, LSH, multi-resolution)
- Hardware performance (CPU, RAM, disk speed)

### What's the best threshold to use?

**Recommended thresholds by use case**:

- **Exact duplicates**: 95-100%
- **Different quality/resolution**: 85-95%
- **Similar content (edits, crops)**: 75-85%
- **Loosely similar**: 60-75%

Start with 85% and adjust based on results.

### Which hash method should I choose?

**Hash Method Comparison**:

| Method | Speed | Accuracy | Best For |
|--------|-------|----------|----------|
| **pHash** | Medium | High | General use (recommended) |
| **dHash** | Fast | Medium | Exact duplicates |
| **aHash** | Fastest | Low | Quick scans |
| **wHash** | Slow | Highest | Cropped/rotated videos |

**Recommendation**: Use **pHash** for most cases.

### How does audio fingerprinting work?

Audio fingerprinting analyzes the audio track separately:
- Uses Chromaprint technology (like Shazam)
- Matches audio even if video is different
- Great for finding re-uploads with new graphics
- Useful for music videos, podcasts, interviews

**When to enable**:
- Looking for audio duplicates
- Videos with same audio, different video
- Re-uploads with different editing

### What is LSH optimization?

LSH (Locality-Sensitive Hashing) speeds up large-scale analysis:
- Pre-filters candidates before full comparison
- Only compares likely matches
- Can reduce comparisons by 90%+
- Recommended for 1000+ videos

**Trade-off**: Slight accuracy reduction for major speed increase.

### Can it find partial matches (clips in videos)?

Yes! Enable **Scene Detection**:
- Detects scene boundaries in videos
- Compares individual scenes
- Finds clips within longer videos
- Identifies edited compilations

**Use case**: Find if a 2-minute clip appears in a 1-hour video.

---

## Performance & Speed

### Analysis is very slow, how can I speed it up?

**Speed Optimization Checklist**:

1. ✅ **Increase Workers**: Set to number of CPU cores (4-8)
2. ✅ **Enable LSH**: For 1000+ videos
3. ✅ **Enable Metadata Filters**: Skip obviously different videos
4. ✅ **Use Faster Hash**: Try dHash instead of pHash
5. ✅ **Disable Audio Fingerprinting**: If not needed
6. ✅ **Increase Batch Size**: Set to 500-1000
7. ✅ **Single Resolution**: Disable multi-resolution analysis

### The application is using too much memory, what should I do?

**Memory Reduction Checklist**:

1. ✅ **Reduce Batch Size**: Set to 50-100
2. ✅ **Reduce Workers**: Set to 2-4
3. ✅ **Disable Multi-Resolution**: Single resolution only
4. ✅ **Process in Batches**: Analyze subset of videos at a time
5. ✅ **Clear Cache**: Free up memory
6. ✅ **Close Other Applications**: Free system memory

### How many workers should I use?

**General rule**: Set to number of CPU cores.

Check your CPU:
- **4 cores**: Use 4 workers
- **8 cores**: Use 6-8 workers
- **16+ cores**: Use 8-12 workers

**Don't set too high**: More than CPU cores won't help and may slow down.

### What's the difference between batch size and workers?

- **Workers**: How many videos processed *simultaneously* (parallel)
- **Batch Size**: How many videos in one *group* before database commit

**Example**:
- 4 workers = 4 videos processed at once
- Batch size 100 = Process 100 videos, then commit to database

### Does it use GPU acceleration?

Currently, Duplicate Finder uses CPU only. GPU acceleration may be added in future versions for:
- Deep learning-based matching
- Video encoding/decoding
- Scene detection

---

## Accuracy & Results

### I'm getting too many false positives, what should I do?

**Reduce False Positives**:

1. ✅ **Increase Threshold**: Set to 90-95%
2. ✅ **Enable Multi-Resolution**: More robust matching
3. ✅ **Enable Metadata Filters**: Pre-filter candidates
4. ✅ **Use pHash or wHash**: More accurate methods
5. ✅ **Enable Verification Pipeline**: Multiple validation stages
6. ✅ **Review Results Manually**: Always verify before deleting

### I'm missing some duplicates, what should I do?

**Reduce False Negatives**:

1. ✅ **Decrease Threshold**: Set to 75-85%
2. ✅ **Enable Multi-Resolution**: Catch different quality levels
3. ✅ **Enable Audio Fingerprinting**: Audio-based matching
4. ✅ **Use pHash or wHash**: More sensitive methods
5. ✅ **Disable LSH**: More thorough comparison (slower)

### How accurate is the similarity score?

Similarity scores are **estimates** based on:
- Perceptual hash distance
- Audio fingerprint similarity
- Scene matching results
- Metadata correlation

**Interpretation**:
- **95-100%**: Almost certainly duplicates
- **85-95%**: Very likely duplicates (different quality)
- **75-85%**: Probably similar (verify manually)
- **Below 75%**: May or may not be related

**Always verify manually before taking action!**

### Can it detect videos with watermarks added?

**It depends**:

- **Small watermarks**: Usually detected (85-95% similarity)
- **Large watermarks**: May be detected (75-85% similarity)
- **Full-screen overlays**: May not be detected

**Best settings for watermarked videos**:
- Use pHash or wHash
- Set threshold to 80-85%
- Enable multi-resolution
- May need manual verification

### What about videos with different aspect ratios?

Duplicate Finder handles aspect ratio changes well:
- Videos are normalized before comparison
- wHash is particularly good for crops
- Multi-resolution helps with letterboxing
- Threshold of 80-85% usually works

---

## Configuration

### Where are settings stored?

Settings are stored in:
- **File**: `settings.json` in plugin directory
- **Format**: JSON (human-readable)
- **Scope**: Per-user, per-installation

### Can I save different configuration profiles?

Yes! Use **Import/Export Settings**:

1. Configure settings for a use case
2. Export to JSON file (e.g., `fast_scan.json`)
3. Create different profiles for different needs
4. Import when needed

**Example profiles**:
- `exact_duplicates.json`: High threshold, fast scan
- `quality_variations.json`: Multi-resolution, medium threshold
- `audio_matching.json`: Audio-first mode enabled

### What happens if I clear the cache?

Clearing the cache:
- ✅ Frees up disk space
- ✅ Removes temporary hash data
- ❌ Next analysis will recompute hashes (slower)
- ❌ Does NOT delete analysis results (those are in database)

**When to clear**:
- Low disk space
- Cache corruption
- After major version update

### Can I reset all settings to defaults?

**Two options**:

1. **Delete settings file**: Delete `settings.json` (recreated with defaults)
2. **Factory Reset**: If available in Settings menu

**Note**: This does NOT delete analysis results, only configuration.

---

## Troubleshooting

### The analysis stopped or crashed, what should I do?

**Immediate steps**:
1. Check error message in status bar
2. Review log files (if available)
3. Try reducing batch size
4. Try reducing worker count
5. Run with smaller video set to isolate issue

See TROUBLESHOOTING.md for detailed solutions.

### Some videos are being skipped, why?

Videos may be skipped if:
- **Corrupted file**: File cannot be read
- **Unsupported format**: Codec not supported
- **Timeout exceeded**: Video too large/complex
- **Permission denied**: Cannot access file

Check the error log for specific reasons.

### The similarity score seems wrong for some videos

This can happen due to:
- **Different content**: Videos are actually different
- **Extreme transformations**: Heavy edits, filters, effects
- **Hash collisions**: Rare, but possible
- **Configuration mismatch**: Wrong hash method or threshold

**Solution**: Try different hash method or threshold.

### Audio fingerprinting is not working

**Common causes**:

1. **Chromaprint not installed**: Install fpcalc binary
2. **No audio track**: Video has no audio
3. **Audio codec unsupported**: Rare audio format
4. **Threshold too strict**: Lower audio threshold

**Check**: Run with audio precision set to "Precise" for better results.

### Results database is too large, can I reduce it?

**Database size management**:

1. **Delete old results**: Clear outdated analysis data
2. **Vacuum database**: Run SQLite VACUUM command
3. **Archive and delete**: Export results, delete database
4. **Start fresh**: Delete database file (resets everything)

**Location**: `video_duplicates.db`

---

## Advanced Features

### What are verification pipelines?

Verification pipelines are multi-stage workflows that combine multiple detection methods:

**Example Pipeline** (Filtering mode):
1. **Stage 1**: Metadata filter (fast rejection)
2. **Stage 2**: LSH pre-filtering (candidate selection)
3. **Stage 3**: Visual hash comparison (final verification)

**Benefits**:
- Faster analysis (early rejection)
- Higher accuracy (multiple validations)
- Customizable for different use cases

See USER_GUIDE.md for pipeline creation tutorial.

### How do I benchmark different methods?

Use the **Benchmark** feature:

1. Create a test set with known duplicate pairs
2. Create verification pipelines to test
3. Run benchmarks
4. Compare accuracy metrics (precision, recall, F1 score)
5. Choose best configuration

**Metrics explained**:
- **Accuracy**: Overall correctness
- **Precision**: % of detected duplicates that are true duplicates
- **Recall**: % of true duplicates that were detected
- **F1 Score**: Harmonic mean of precision and recall

### Can I run analysis in the background?

Yes! Use the **Queue** feature:

1. Add analysis jobs to queue
2. Queue processes jobs automatically
3. Continue working in other tabs
4. Check progress in Queue tab
5. Results appear when complete

**Great for**:
- Large video collections
- Overnight processing
- Batch operations

### Can I export duplicate lists?

Yes! Export options:

- **CSV**: Spreadsheet-compatible
- **JSON**: Machine-readable
- **HTML Report**: Human-readable report
- **Text File**: Simple list

**Use cases**:
- Documentation
- Review in Excel
- Scripting/automation
- Reporting

### How do I contribute or report bugs?

**Bug Reports**:
1. Check existing issues on GitHub
2. Gather information (version, OS, steps to reproduce)
3. Create new issue with details
4. Attach logs/screenshots if possible

**Feature Requests**:
1. Check existing feature requests
2. Describe use case and benefit
3. Create new issue with "enhancement" label

**Contributing**:
- See CONTRIBUTING.md for developer guidelines
- Fork repository
- Create feature branch
- Submit pull request

---

## Still Have Questions?

If your question isn't answered here:

1. **Check Documentation**:
   - USER_GUIDE.md - Comprehensive user guide
   - TROUBLESHOOTING.md - Common issues and solutions
   - ARCHITECTURE.md - Technical details (developers)

2. **Search GitHub Issues**:
   - Existing issues and solutions
   - Feature requests and discussions

3. **Create New Issue**:
   - Provide detailed information
   - Include version and system details
   - Attach logs or screenshots

4. **Community**:
   - VideoFlow forums
   - Community discussions

---

**Last Updated**: December 2025
**Version**: 3.0
**Feedback**: Help us improve this FAQ by reporting unclear answers or suggesting new questions!
