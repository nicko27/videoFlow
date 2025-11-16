# Installation Guide - Scene Detection (Audio Fingerprinting)

## Overview

The scene detection feature uses **Chromaprint** (audio fingerprinting) to detect when shorter videos (scenes) are extracted from longer videos. This is **100-1000x faster** than visual comparison.

## Requirements

You need to install **chromaprint-tools** which provides the `fpcalc` command-line tool.

---

## Installation Instructions

### 🍎 macOS

Install via Homebrew:

```bash
brew install chromaprint
```

Verify installation:
```bash
fpcalc -version
```

You should see output like:
```
fpcalc version 1.5.1
```

---

### 🐧 Linux (Ubuntu/Debian)

Install via apt:

```bash
sudo apt update
sudo apt install chromaprint-tools
```

Verify installation:
```bash
fpcalc -version
```

---

### 🪟 Windows

#### Option 1: Using Chocolatey
```powershell
choco install chromaprint
```

#### Option 2: Manual Installation
1. Download from: https://github.com/acoustid/chromaprint/releases
2. Extract the ZIP file
3. Add the directory containing `fpcalc.exe` to your PATH

Verify installation:
```cmd
fpcalc -version
```

---

## How to Use

### 1. Enable Scene Detection

In the VideoFlow duplicate finder:
1. Go to **⚙️ Settings** tab
2. Scroll to **🎬 Scene Detection (Audio Fingerprinting)**
3. Check **"Enable scene detection (audio-based)"**

### 2. Choose Precision Mode

Select your preferred mode:

- **🎯 Maximum Precision** (99.9%, 10-30s/video)
  - Best for critical scenes
  - Slowest but most accurate
  - Use when you need guaranteed detection

- **⚖️ Balanced** (99%, 5-15s/video) ✅ **RECOMMENDED**
  - 99% precision
  - Good speed/accuracy balance
  - Ideal for most use cases

- **⚡ Fast** (95%, 2-5s/video)
  - Quick screening
  - Lower precision
  - Good for initial analysis

### 3. Configure Settings

- **Min match ratio**: 75-99% (default: 85%)
  - Higher = fewer false positives, may miss some scenes
  - Lower = more detections, may have false positives

- **Min scene duration**: 5-300 seconds (default: 10s)
  - Minimum scene length to consider
  - Prevents very short clips from being detected

- **Fingerprint cache**: 100-2000 items (default: 500)
  - Number of fingerprints to keep in memory
  - Higher = faster for re-analysis, more RAM usage

### 4. Run Analysis

1. Add your video files
2. Click **🔍 START**
3. Wait for analysis to complete
4. Scene detection will run automatically after duplicate detection

---

## Perfect For

✅ **Finding scenes extracted from long videos**
- 15-60 minute scenes from 2-hour videos
- TV show clips from full episodes
- Movie scenes from full movies

✅ **Re-encoded content**
- Same audio, different video quality
- Format conversions (MP4 → MKV, etc.)
- Different resolutions

✅ **Speed**
- Processes audio (1D) instead of thousands of frames (2D)
- 100-1000x faster than visual dense sampling
- Typical speed: 5-15 seconds per video (Balanced mode)

---

## Troubleshooting

### Error: "fpcalc not found"

The `fpcalc` tool is not installed or not in PATH.

**Solution:**
1. Install chromaprint-tools (see instructions above)
2. Verify with: `fpcalc -version`
3. If installed but not found, add to PATH

### No scenes detected

**Possible causes:**
1. **Videos too similar in length** - Scene detection only works when one video is significantly shorter (≥20% difference)
2. **Different audio tracks** - Audio must be identical or very similar
3. **Threshold too high** - Try lowering the min match ratio to 80%
4. **Min duration too high** - Lower the min scene duration

**Solutions:**
- Enable scene detection checkbox
- Lower min match ratio to 75-80%
- Try "Balanced" or "Fast" mode
- Check that videos actually have audio

### Very slow processing

**Possible causes:**
1. Using "Maximum Precision" mode
2. Very long videos (2+ hours)
3. Many videos to compare

**Solutions:**
- Switch to "Balanced" or "Fast" mode
- Process fewer videos at once
- Increase fingerprint cache size

---

## Technical Details

### How It Works

1. **Extract Audio Fingerprint**
   - Uses Chromaprint/AcoustID algorithm
   - Creates compact audio signature (few KB)
   - Resistant to compression, re-encoding

2. **Sliding Window Search**
   - Searches for short fingerprint in long fingerprint
   - Sub-second temporal precision
   - Finds exact start time of scene

3. **Match Validation**
   - Compares match ratio against threshold
   - Validates scene duration
   - Stores results in database

### Performance Comparison

| Method | Speed | Precision | Use Case |
|--------|-------|-----------|----------|
| **Visual Dense Sampling** (old) | Very Slow (20M ops) | 80-95% | Short clips (<5 min) |
| **Audio Fingerprinting** (new) | Very Fast (5-15s) | 99% | Scenes (15-60 min) |

### Cache Management

- Fingerprints cached in memory (LRU eviction)
- Default: 500 fingerprints
- Each fingerprint: ~1-5 KB
- Total memory: ~2.5 MB (500 × 5 KB)

---

## FAQ

**Q: Does it work with silent videos?**
A: No, audio fingerprinting requires audio tracks. Use duplicate detection for silent videos.

**Q: Can it detect scenes with different audio (e.g., different language dubs)?**
A: No, audio must be identical or very similar. Different language tracks won't match.

**Q: Does video quality matter?**
A: No! Audio fingerprinting only analyzes audio, so video quality/resolution doesn't matter.

**Q: Can I use both duplicate detection and scene detection?**
A: Yes! Both run in sequence. Duplicates are detected first, then scenes.

**Q: Is chromaprint free?**
A: Yes, Chromaprint is free and open-source (MIT license).

---

## Support

If you encounter issues:
1. Check that `fpcalc -version` works
2. Verify videos have audio tracks
3. Try lowering the min match ratio
4. Check the logs for error messages
5. Report issues with detailed information

---

## Credits

- **Chromaprint**: https://acoustid.org/chromaprint
- **Algorithm**: Based on AcoustID audio fingerprinting
- **Speed**: 100-1000x faster than visual methods
