# Duplicate Finder - Troubleshooting Guide

## Table of Contents
1. [Installation & Setup Issues](#installation--setup-issues)
2. [Analysis Errors](#analysis-errors)
3. [Performance Problems](#performance-problems)
4. [Accuracy Issues](#accuracy-issues)
5. [UI & Display Issues](#ui--display-issues)
6. [Database & Storage Issues](#database--storage-issues)
7. [Import/Export Issues](#importexport-issues)
8. [Advanced Troubleshooting](#advanced-troubleshooting)

---

## Installation & Setup Issues

### Plugin doesn't appear in VideoFlow

**Symptoms**: Duplicate Finder not listed in Plugins menu

**Possible Causes & Solutions**:

1. **Plugin not installed properly**
   ```bash
   # Check if plugin directory exists
   ls /path/to/videoFlow/src/plugins/duplicate_finder/
   ```
   - **Fix**: Reinstall VideoFlow or verify plugin files

2. **Import errors**
   - Check Python console for error messages
   - **Fix**: Install missing dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. **Incompatible VideoFlow version**
   - Check VideoFlow version (needs 2.0+)
   - **Fix**: Update VideoFlow

### Missing Dependencies Error

**Symptoms**: Error messages about missing modules

**Common Missing Modules**:

1. **OpenCV**: `ModuleNotFoundError: No module named 'cv2'`
   ```bash
   pip install opencv-python
   ```

2. **NumPy**: `ModuleNotFoundError: No module named 'numpy'`
   ```bash
   pip install numpy
   ```

3. **PyQt6**: `ModuleNotFoundError: No module named 'PyQt6'`
   ```bash
   pip install PyQt6
   ```

4. **Optional - PySceneDetect**: For scene detection
   ```bash
   pip install scenedetect[opencv]
   ```

5. **Optional - Chromaprint**: For audio fingerprinting
   - **Ubuntu/Debian**: `sudo apt-get install libchromaprint-tools`
   - **macOS**: `brew install chromaprint`
   - **Windows**: Download fpcalc.exe from AcoustID website

### Database Initialization Failed

**Symptoms**: Error on first launch about database creation

**Solution**:
```bash
# Remove corrupted database
rm /path/to/videoFlow/src/plugins/duplicate_finder/video_duplicates.db
rm /path/to/videoFlow/src/plugins/duplicate_finder/video_duplicates.db-shm
rm /path/to/videoFlow/src/plugins/duplicate_finder/video_duplicates.db-wal

# Restart VideoFlow (database will be recreated)
```

**Check permissions**:
```bash
# Ensure write permissions
chmod 755 /path/to/videoFlow/src/plugins/duplicate_finder/
```

---

## Analysis Errors

### "Analysis Failed" Error

**Symptoms**: Analysis stops with generic error message

**Diagnostic Steps**:

1. **Check error details in status bar**
2. **Review log output** (if available)
3. **Try with single video** to isolate issue

**Common Causes**:

#### 1. Video File Corruption

**Symptoms**: Specific videos cause crash

**Solution**:
```bash
# Test video with FFmpeg
ffmpeg -v error -i problem_video.mp4 -f null -

# If errors appear, video is corrupted
# Try re-encoding:
ffmpeg -i problem_video.mp4 -c:v libx264 -c:a aac fixed_video.mp4
```

#### 2. Unsupported Codec

**Symptoms**: "Could not read video" error

**Solution**:
- Install full FFmpeg build with all codecs
- Convert video to standard format (H.264/AAC)

#### 3. Memory Exhausted

**Symptoms**: Application freezes or crashes during analysis

**Solution**:
- Reduce batch size to 50
- Reduce workers to 2-4
- Process fewer videos at once
- Close other applications

#### 4. Timeout Exceeded

**Symptoms**: "Hash computation timed out" error

**Solution**:
```python
# Increase timeout in settings
Hash Timeout: 600 seconds (instead of 300)
```
- Or process large videos separately

### Videos Being Skipped

**Symptoms**: Some videos not analyzed, "X videos skipped" message

**Check Log for Reasons**:

1. **Permission Denied**
   ```bash
   # Fix file permissions
   chmod 644 video_file.mp4
   ```

2. **File Not Found**
   - Video moved or deleted
   - Network path unavailable
   - **Fix**: Verify file locations

3. **Unsupported Format**
   - Check codec: `ffprobe video_file.mp4`
   - **Fix**: Convert to supported format

4. **Zero Duration**
   - Corrupted or invalid video file
   - **Fix**: Re-download or repair file

### "Database Lock" Error

**Symptoms**: "Database is locked" during analysis

**Causes**:
- Multiple instances running
- Previous crash left lock
- Antivirus scanning database

**Solutions**:

1. **Close other instances**
   ```bash
   # Check for running instances
   ps aux | grep videoFlow
   # Kill if necessary
   kill <pid>
   ```

2. **Remove lock files**
   ```bash
   rm video_duplicates.db-shm
   rm video_duplicates.db-wal
   ```

3. **Disable antivirus scan** for plugin directory temporarily

---

## Performance Problems

### Analysis is Extremely Slow

**Symptoms**: Taking hours for small collections

**Optimization Checklist**:

1. ✅ **Check Worker Count**
   - Current: ___
   - Recommended: Number of CPU cores (4-8)
   - **Fix**: Increase workers to match CPU cores

2. ✅ **Check Batch Size**
   - Current: ___
   - Recommended: 200-500 for medium collections
   - **Fix**: Increase batch size

3. ✅ **Disable Unnecessary Features**
   - ❌ Audio fingerprinting (if not needed)
   - ❌ Multi-resolution (if not needed)
   - ❌ Scene detection (if not needed)

4. ✅ **Enable Speed Optimizations**
   - ✅ LSH (for 1000+ videos)
   - ✅ Metadata filters
   - ✅ Caching

5. ✅ **Check Disk Speed**
   ```bash
   # Test disk read speed
   hdparm -t /dev/sdX  # Linux
   diskutil info disk0  # macOS
   ```
   - **Slow network drive?** Copy videos locally

6. ✅ **Use Faster Hash Method**
   - Change from wHash → pHash → dHash → aHash
   - Trade accuracy for speed

### High CPU Usage

**Symptoms**: CPU at 100%, system slow

**This is Normal During Analysis!**

Duplicate Finder is CPU-intensive by design. However:

**If CPU stays at 100% when idle**:
1. Check for runaway worker processes
2. Restart application
3. Reduce worker count

**If system becomes unusable**:
1. Reduce worker count (set to 50% of CPU cores)
2. Lower process priority:
   ```bash
   # Linux/macOS
   renice -n 10 -p <pid>
   ```
3. Run analysis during off-hours

### High Memory Usage

**Symptoms**: RAM usage very high, system swapping

**Diagnostic**:
```bash
# Check memory usage
top  # Linux/macOS
taskmgr  # Windows
```

**Solutions by Severity**:

**Level 1 - Reduce Batch Size**:
```
Current: 500 → New: 100
```

**Level 2 - Reduce Workers**:
```
Current: 8 → New: 4
```

**Level 3 - Disable Multi-Resolution**:
```
Single resolution only
```

**Level 4 - Process in Smaller Groups**:
```
Analyze 100 videos at a time instead of 1000
```

**Level 5 - Clear Cache**:
```
Cache Settings → Clear Cache
```

### Disk Space Running Out

**Symptoms**: "Disk full" errors, cache growing large

**Check Space Usage**:
```bash
# Check plugin directory size
du -sh /path/to/duplicate_finder/

# Check cache size
du -sh /path/to/duplicate_finder/cache/
```

**Solutions**:

1. **Clear Cache**
   - Cache Settings → Clear Cache
   - Safe to delete, will be rebuilt

2. **Set Cache Limit**
   - Cache Settings → Max Size: 500 MB
   - Prevents unlimited growth

3. **Vacuum Database**
   ```bash
   sqlite3 video_duplicates.db "VACUUM;"
   ```

4. **Archive Old Results**
   - Export results to CSV
   - Delete old analysis data
   - Start fresh if needed

---

## Accuracy Issues

### Too Many False Positives

**Symptoms**: Unrelated videos marked as duplicates

**Solutions (in order of impact)**:

1. **Increase Threshold**
   ```
   Current: 75% → New: 85-90%
   ```

2. **Enable Metadata Filters**
   ```
   Duration Tolerance: 5 seconds
   File Size Ratio: 0.5-2.0
   ```

3. **Use More Accurate Hash**
   ```
   Current: dHash → New: pHash or wHash
   ```

4. **Enable Multi-Resolution**
   ```
   Resolutions: 720p, 480p, 360p
   ```

5. **Use Verification Pipeline**
   ```
   Mode: Voting or Weighted
   Methods: Metadata + Visual + Audio
   ```

### Missing Obvious Duplicates

**Symptoms**: Known duplicates not detected

**Solutions (in order of impact)**:

1. **Decrease Threshold**
   ```
   Current: 95% → New: 80-85%
   ```

2. **Enable Multi-Resolution**
   ```
   If videos at different quality levels
   ```

3. **Enable Audio Fingerprinting**
   ```
   Audio-First Mode: Enabled
   Precision: Balanced or Precise
   Threshold: 0.7-0.8
   ```

4. **Disable LSH Temporarily**
   ```
   May filter out some matches
   ```

5. **Try Different Hash Method**
   ```
   pHash → wHash (slower but more robust)
   ```

### Inconsistent Results

**Symptoms**: Running again gives different results

**Possible Causes**:

1. **Cache Issues**
   - **Fix**: Clear cache and re-run

2. **Database Corruption**
   ```bash
   # Check database integrity
   sqlite3 video_duplicates.db "PRAGMA integrity_check;"

   # If corrupted, backup and recreate
   mv video_duplicates.db video_duplicates.db.backup
   ```

3. **Concurrent Modifications**
   - Files changed between runs
   - **Fix**: Ensure files unchanged during analysis

4. **Random Initialization** (audio fingerprinting)
   - Some variability is normal
   - **Fix**: Run multiple times and average

---

## UI & Display Issues

### Window Too Small or Layout Broken

**Symptoms**: UI elements overlap or cut off

**Solutions**:

1. **Reset Window Size**
   - Close and reopen plugin
   - Default: 1400x900

2. **Increase Window Size**
   - Drag window corners
   - Minimum: 1000x800

3. **Check Display Scaling**
   - High DPI displays may cause issues
   - Try 100% scaling temporarily

4. **Delete Settings File**
   ```bash
   rm settings.json
   # Restart (will recreate with defaults)
   ```

### Progress Bar Stuck or Not Updating

**Symptoms**: Progress bar doesn't move, but analysis running

**This is Usually Normal**:
- Progress updates every few seconds
- Large videos may take time per file

**If Genuinely Stuck**:
1. Check CPU usage (should be high if running)
2. Wait 5 minutes
3. If no change, click Stop and restart

### Tooltips Not Showing

**Symptoms**: Hovering over controls shows no help text

**Causes**:
- Qt configuration issue
- Display scaling issue

**Solutions**:
1. Restart application
2. Check Qt settings
3. Update PyQt6: `pip install --upgrade PyQt6`

### Status Bar Not Updating

**Symptoms**: Status bar shows old messages

**Solution**:
- This is usually a display refresh issue
- Resize window slightly to force refresh
- Or restart application

---

## Database & Storage Issues

### Database Corruption

**Symptoms**: "Database disk image is malformed" error

**Recovery Steps**:

1. **Backup Current Database**
   ```bash
   cp video_duplicates.db video_duplicates.db.backup
   ```

2. **Try Repair**
   ```bash
   sqlite3 video_duplicates.db
   .mode insert
   .output dump.sql
   .dump
   .exit

   rm video_duplicates.db
   sqlite3 video_duplicates.db < dump.sql
   ```

3. **If Repair Fails**
   ```bash
   # Start fresh (loses analysis data)
   rm video_duplicates.db*
   # Restart application
   ```

### Cannot Write to Database

**Symptoms**: "Unable to write to database" error

**Check Permissions**:
```bash
# Check current permissions
ls -la video_duplicates.db

# Fix permissions
chmod 644 video_duplicates.db
chmod 755 /path/to/duplicate_finder/
```

**Check Disk Space**:
```bash
df -h
```

**Check File System**:
- Read-only mount? Remount as read-write
- Network share permissions? Check share settings

### Database Growing Too Large

**Symptoms**: Database file is many GB

**Normal Size**: 10-100 MB for 10,000 videos

**If Abnormally Large**:

1. **Vacuum Database**
   ```bash
   sqlite3 video_duplicates.db "VACUUM;"
   ```

2. **Delete Old Results**
   - Export needed data
   - Clear old analysis results
   - Or start fresh

3. **Check for Corruption**
   ```bash
   sqlite3 video_duplicates.db "PRAGMA integrity_check;"
   ```

---

## Import/Export Issues

### Cannot Import Settings

**Symptoms**: "Invalid settings file" or import fails

**Verify JSON Format**:
```bash
# Check if valid JSON
python3 -m json.tool settings.json
```

**Common Issues**:
- Trailing comma in JSON
- Missing quotes
- Wrong file format

**Solution**:
1. Re-export from working installation
2. Or manually fix JSON syntax
3. Validate with JSON validator

### Export Results Fails

**Symptoms**: Export button does nothing or errors

**Check**:
1. Write permissions in export directory
2. Disk space available
3. File not already open in another program

**Try**:
- Export to different location
- Export smaller subset
- Different format (CSV vs JSON)

### Pipeline Import/Export Not Working

**Symptoms**: Pipelines not importing correctly

**Verify Pipeline Structure**:
```json
{
  "name": "My Pipeline",
  "mode": "filtering",
  "methods": [
    {
      "name": "metadata_filter",
      "enabled": true,
      "params": {}
    }
  ]
}
```

**Common Errors**:
- Missing required fields
- Invalid mode value
- Unknown method names

**Fix**:
1. Export working pipeline as template
2. Copy structure
3. Modify carefully

---

## Advanced Troubleshooting

### Enable Debug Logging

**For Detailed Error Information**:

```python
# Add to plugin initialization (if available)
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Or** set environment variable:
```bash
export PYTHONVERBOSE=1
export OPENCV_LOG_LEVEL=DEBUG
python3 main.py
```

### Check System Resources

**Monitor During Analysis**:

```bash
# CPU, memory, processes
top

# Disk I/O
iotop  # Linux
iostat  # macOS

# Network (if files on network)
iftop
```

**Identify Bottleneck**:
- **CPU at 100%**: Normal during analysis
- **Disk I/O at 100%**: Slow storage or network
- **Memory swapping**: Reduce batch size/workers

### Test with Known Good Files

**Create Test Set**:
```bash
# Create small test videos
ffmpeg -f lavfi -i testsrc=duration=10:size=1280x720:rate=30 test1.mp4
cp test1.mp4 test2.mp4  # Exact duplicate
```

**Run Analysis**:
- Should detect 100% similarity
- If not, indicates configuration or installation issue

### Verify FFmpeg Installation

**Test FFmpeg**:
```bash
ffmpeg -version
ffprobe -version

# Test video reading
ffprobe test_video.mp4
```

**Reinstall if Issues**:
```bash
# Ubuntu/Debian
sudo apt-get install --reinstall ffmpeg

# macOS
brew reinstall ffmpeg

# Or use static builds from ffmpeg.org
```

### Check Python Dependencies Versions

**List Installed Versions**:
```bash
pip list | grep -E "opencv|numpy|PyQt6|chromaprint"
```

**Known Compatible Versions**:
- OpenCV: 4.5.0+
- NumPy: 1.20.0+
- PyQt6: 6.0.0+
- scenedetect: 0.6.0+ (optional)

**Update if Needed**:
```bash
pip install --upgrade opencv-python numpy PyQt6
```

### Collect Diagnostic Information

**For Bug Reports**, gather:

1. **System Info**:
   ```bash
   python3 --version
   uname -a  # Linux/macOS
   systeminfo  # Windows
   ```

2. **Plugin Version**:
   - Check `__init__.py` or About dialog

3. **Error Messages**:
   - Full error text from status bar
   - Stack traces from console

4. **Settings**:
   - Export current settings
   - Include with report

5. **Test Case**:
   - Steps to reproduce
   - Sample files (if possible)

### Reset to Factory Defaults

**Complete Reset**:

```bash
# Backup first!
cp -r /path/to/duplicate_finder /path/to/duplicate_finder.backup

# Delete all user data
rm video_duplicates.db*
rm settings.json
rm -rf cache/

# Restart VideoFlow
# Plugin will reinitialize with defaults
```

**Caution**: This deletes all analysis results!

---

## Still Having Issues?

If none of these solutions work:

### 1. Check Documentation
- USER_GUIDE.md - Usage instructions
- FAQ.md - Common questions
- ARCHITECTURE.md - Technical details

### 2. Search Existing Issues
- GitHub Issues
- Known bugs and workarounds

### 3. Create Bug Report

Include:
- **System**: OS, Python version, VideoFlow version
- **Problem**: Clear description
- **Steps**: How to reproduce
- **Expected**: What should happen
- **Actual**: What actually happens
- **Logs**: Error messages, stack traces
- **Settings**: Configuration (export as JSON)

### 4. Community Help
- VideoFlow forums
- User community discussions

---

## Quick Reference - Common Fixes

| Problem | Quick Fix |
|---------|-----------|
| Analysis crashes | Reduce batch size + workers |
| Out of memory | Reduce batch size to 50 |
| Too slow | Increase workers, enable LSH |
| False positives | Increase threshold to 90% |
| Missing duplicates | Decrease threshold to 80% |
| Database locked | Close other instances |
| Import fails | Validate JSON syntax |
| Videos skipped | Check file permissions |
| High CPU | Normal during analysis |
| High memory | Reduce workers + batch size |

---

**Last Updated**: December 2025
**Version**: 3.0
**Found a solution not listed here?** Please contribute to this guide!
