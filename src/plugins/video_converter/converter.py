"""Optimized video conversion module with corrected failure handling."""

from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker, QTimer
import subprocess
import tempfile
import shutil
import re
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime
from src.core.logger import Logger

logger = Logger.get_logger('VideoConverter.Converter')

# Subprocess timeout configuration
FFPROBE_TIMEOUT = 10  # seconds for ffprobe operations
FFMPEG_BASE_TIMEOUT = 300  # 5 minutes base timeout for ffmpeg
FFMPEG_TIMEOUT_PER_MB = 0.5  # 0.5 seconds per MB of input file

# Disk space monitoring
DISK_SPACE_CHECK_INTERVAL = 30  # Check disk space every 30 seconds
MIN_FREE_SPACE_MB = 500  # Minimum 500MB free space required

def format_size(size: int) -> str:
    """Optimized formatting for file sizes."""
    if size < 1024:
        return f"{size} B"
    elif size < 1048576:  # 1024^2
        return f"{size/1024:.1f} KB"
    elif size < 1073741824:  # 1024^3
        return f"{size/1048576:.1f} MB"
    else:
        return f"{size/1073741824:.1f} GB"

def get_video_resolution(video_path: Path, ffprobe_path: str = 'ffprobe') -> Tuple[int, int]:
    """
    Get video resolution (width, height).

    Args:
        video_path: Path to video file
        ffprobe_path: Path to ffprobe executable

    Returns:
        Tuple of (width, height)
    """
    try:
        cmd = [
            ffprobe_path,
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0',
            str(video_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT)
        if result.returncode == 0 and result.stdout.strip():
            width, height = map(int, result.stdout.strip().split(','))
            return width, height
    except Exception as e:
        logger.warning(f"Unable to get resolution: {e}")

    return 1920, 1080  # Default resolution

def calculate_balanced_crf(video_path: Path, quality_factor: float = 1.0, ffprobe_path: str = 'ffprobe') -> int:
    """
    Calculate optimal CRF based on video resolution.

    Strategy:
    - 4K (3840x2160+): CRF 18-24 (high quality needed)
    - QHD (2560x1440+): CRF 20-26
    - FHD (1920x1080+): CRF 23-28 (standard)
    - HD (1280x720+): CRF 26-30
    - SD (<1280x720): CRF 28-32 (stronger compression)

    Args:
        video_path: Path to the video
        quality_factor: Quality factor (0.5-2.0, 1.0=neutral)
                       < 1.0 = better quality (lower CRF)
                       > 1.0 = more compression (higher CRF)
        ffprobe_path: Path to ffprobe executable

    Returns:
        int: Calculated CRF value (18-35)
    """
    width, height = get_video_resolution(video_path, ffprobe_path)
    pixels = width * height

    # Base CRF based on resolution
    if pixels >= 8294400:  # 4K (3840x2160)
        base_crf = 21
    elif pixels >= 3686400:  # QHD (2560x1440)
        base_crf = 23
    elif pixels >= 2073600:  # FHD (1920x1080)
        base_crf = 25
    elif pixels >= 921600:   # HD (1280x720)
        base_crf = 28
    else:  # SD
        base_crf = 30

    # Adjust with quality factor
    # quality_factor < 1.0 => lower CRF (better quality)
    # quality_factor > 1.0 => higher CRF (more compression)
    adjustment = int((quality_factor - 1.0) * 5)
    final_crf = base_crf + adjustment

    # Limit between 18 and 35
    return max(18, min(35, final_crf))

class ConversionWorker(QThread):
    """Video conversion worker optimized for performance and stability."""

    progress = pyqtSignal(str, int)  # file_path, progress_percentage
    finished = pyqtSignal(str, bool, str)  # file_path, success, message
    error = pyqtSignal(str, str)  # file_path, error_message
    attempt_changed = pyqtSignal(str, int)  # file_path, attempt_number
    iteration_changed = pyqtSignal(str, int, int)  # file_path, iteration_number, crf_value

    def __init__(self, input_file: Path, settings):
        super().__init__()
        self.input_file = input_file
        self.settings = settings
        self.is_running = True
        self.current_attempt = 1
        self.max_attempts = 3 if settings.multiple_attempts else 1
        self.process = None
        self.mutex = QMutex()
        self.process_start_time = None
        self.process_timeout = None
        self.last_disk_check = 0.0

        # Iterative compression
        self.current_iteration = 0
        self.current_crf = settings.initial_crf if settings.use_target_size else 28

        # Get FFmpeg paths from settings
        self.ffmpeg_path = getattr(settings, 'ffmpeg_path', 'ffmpeg')
        self.ffprobe_path = getattr(settings, 'ffprobe_path', 'ffprobe')

        # Balanced mode: calculate CRF automatically based on resolution
        if getattr(settings, 'balanced_auto_crf', False):
            quality_factor = getattr(settings, 'balanced_quality_factor', 1.0)
            calculated_crf = calculate_balanced_crf(input_file, quality_factor, self.ffprobe_path)
            settings.crf = calculated_crf
            logger.info(f"Balanced Mode: Auto-calculated CRF = {calculated_crf} (quality factor: {quality_factor})")

        # Optimized settings for different attempts
        self.attempt_params = [
            {'crf': 28, 'preset': 'fast'},      # Attempt 1: fast and balanced
            {'crf': 30, 'preset': 'medium'},    # Attempt 2: stronger compression
            {'crf': 32, 'preset': 'slow'}       # Attempt 3: maximum compression
        ]
    
    def calculate_timeout(self) -> int:
        """
        Calculate appropriate timeout for FFmpeg based on file size.

        Returns:
            Timeout in seconds
        """
        try:
            file_size_mb = self.input_file.stat().st_size / (1024 * 1024)
            timeout = int(FFMPEG_BASE_TIMEOUT + (file_size_mb * FFMPEG_TIMEOUT_PER_MB))
            # Cap timeout at 2 hours to prevent infinite hangs
            return min(timeout, 7200)
        except Exception as e:
            logger.warning(f"Error calculating timeout: {e}")
            return FFMPEG_BASE_TIMEOUT

    def check_disk_space(self) -> Tuple[bool, str]:
        """
        Check if there's enough disk space to continue conversion.

        Returns:
            Tuple[bool, str]: (has_space, error_message)
        """
        try:
            # Get output directory (where temp files will be created)
            output_dir = self.input_file.parent
            _, _, free = shutil.disk_usage(output_dir)

            free_mb = free / (1024 * 1024)

            if free_mb < MIN_FREE_SPACE_MB:
                msg = f"Insufficient disk space: {free_mb:.0f}MB < {MIN_FREE_SPACE_MB}MB required"
                logger.error(msg)
                return False, msg

            return True, ""

        except Exception as e:
            logger.warning(f"Error checking disk space: {e}")
            # If we can't check, assume there's space (fail-safe)
            return True, ""

    def should_convert(self) -> Tuple[bool, str]:
        """Quick checks before conversion."""
        if not self.input_file.exists():
            return False, "File does not exist"

        if not self.input_file.is_file():
            return False, "Not a file"

        # Check for _cvt suffix
        if self.input_file.stem.endswith('_cvt'):
            return False, "Already converted (_cvt suffix)"

        # Check size if threshold enabled
        if self.settings.use_size_threshold:
            try:
                size = self.input_file.stat().st_size
                if size <= self.settings.size_threshold:
                    return False, f"Size already below threshold ({format_size(size)})"
            except OSError as e:
                return False, f"Error reading size: {e}"

        # Check metadata if option enabled
        if self.settings.ignore_converted:
            try:
                # Lazy import to avoid dependencies at load time
                from .metadata import MetadataManager
                metadata = MetadataManager.get_metadata(self.input_file)
                if metadata and metadata.compression_ratio > 0:
                    return False, f"Already converted (-{metadata.compression_ratio:.1f}%)"
            except Exception as e:
                logger.warning(f"Error checking metadata: {e}")

        return True, ""
    
    def get_output_path(self) -> Path:
        """Determine output path in the same folder as the original."""
        if self.settings.replace_original:
            # Temporary file in the same folder as the original to avoid cross-device issues
            parent_dir = self.input_file.parent
            temp_name = f"temp_conv_{self.input_file.stem}_{datetime.now().strftime('%H%M%S')}{self.input_file.suffix}"
            return parent_dir / temp_name
        else:
            # Add _cvt suffix in the same folder
            stem = self.input_file.stem
            if not stem.endswith('_cvt'):
                stem += '_cvt'
            return self.input_file.with_name(f"{stem}{self.input_file.suffix}")
    
    def get_duration(self) -> float:
        """Get video duration using configured ffprobe path."""
        try:
            cmd = [
                self.ffprobe_path,
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(self.input_file)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT)
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except (subprocess.TimeoutExpired, ValueError, OSError) as e:
            logger.warning(f"Unable to get duration: {e}")

        return 0.0
    
    def get_attempt_params(self, attempt: int, custom_crf: int = None) -> dict:
        """Get settings for a given attempt."""
        if custom_crf is not None:
            # Iterative compression mode with custom CRF
            return {
                'crf': custom_crf,
                'preset': self.settings.preset if self.settings.manual_mode else 'medium'
            }
        elif self.settings.manual_mode:
            return {
                'crf': self.settings.crf,
                'preset': self.settings.preset
            }
        else:
            # Use predefined settings or those from the configuration
            if hasattr(self.settings, 'attempts') and attempt <= len(self.settings.attempts):
                attempt_config = self.settings.attempts[attempt - 1]
                return {
                    'crf': attempt_config.crf,
                    'preset': attempt_config.preset
                }
            elif attempt <= len(self.attempt_params):
                return self.attempt_params[attempt - 1]
            else:
                # Fallback settings
                return {'crf': 32, 'preset': 'slow'}
    
    def cleanup_temp_files(self, temp_path: Path):
        """Safe cleanup of temporary files - only if truly temporary."""
        try:
            if temp_path and temp_path.exists():
                # Check if it's really a temporary file
                # (starts with temp_conv_ or is in /tmp or /var/folders)
                is_temp = (
                    temp_path.name.startswith('temp_conv_') or
                    str(temp_path).startswith('/tmp/') or
                    str(temp_path).startswith('/var/folders/') or
                    'videoconv_' in temp_path.name
                )

                if is_temp:
                    temp_path.unlink()
                    logger.debug(f"Temporary file cleaned up: {temp_path}")
                else:
                    logger.debug(f"File preserved (not temporary): {temp_path}")
        except Exception as e:
            logger.warning(f"Cannot clean {temp_path}: {e}")
    
    def convert_file(self, attempt: int, custom_crf: int = None) -> Tuple[bool, str, Optional[Path]]:
        """Convert file with the attempt's settings."""
        output_path = None

        try:
            with QMutexLocker(self.mutex):
                if not self.is_running:
                    return False, "Conversion stopped", None

            # Get settings (with custom CRF if iterative mode)
            params = self.get_attempt_params(attempt, custom_crf)
            output_path = self.get_output_path()

            # Get duration for progress tracking
            duration = self.get_duration()
            if duration <= 0:
                logger.warning("Unknown duration, limited progress tracking")
                duration = 1  # Avoid division by zero

            # Reset progress
            self.progress.emit(str(self.input_file), 0)
            
            # Optimized ffmpeg command using configured path
            cmd = [
                self.ffmpeg_path,
                '-i', str(self.input_file),
                '-c:v', 'libx264',
                '-crf', str(params['crf']),
                '-preset', params['preset'],
                '-c:a', 'copy',  # Copy audio without re-encoding
                '-avoid_negative_ts', 'make_zero',  # Avoid negative timestamps
                '-movflags', '+faststart',  # Optimization for streaming
                '-y',  # Overwrite output
                str(output_path)
            ]
            
            logger.info(f"Attempt {attempt} for {self.input_file.name} (CRF={params['crf']}, preset={params['preset']})")
            logger.debug(f"Command: {' '.join(cmd)}")

            # Calculate timeout for this conversion
            self.process_timeout = self.calculate_timeout()
            self.process_start_time = time.time()
            logger.debug(f"Process timeout set to {self.process_timeout}s")

            # Start the process with limited buffer size to prevent memory issues
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=8192  # 8KB buffer to prevent excessive memory usage
            )

            # Pattern to extract time
            time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
            last_progress = 0
            last_output_time = time.time()

            # Read stderr for progress with timeout monitoring
            while self.is_running and self.process.poll() is None:
                try:
                    current_time = time.time()

                    # Check for timeout
                    elapsed = current_time - self.process_start_time
                    if elapsed > self.process_timeout:
                        logger.warning(f"Process timeout exceeded ({elapsed:.0f}s > {self.process_timeout}s)")
                        self.process.terminate()
                        try:
                            self.process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            self.process.kill()
                            self.process.wait()
                        return False, f"Timeout exceeded ({elapsed:.0f}s)", output_path

                    # Periodic disk space check (every 30 seconds)
                    if current_time - self.last_disk_check > DISK_SPACE_CHECK_INTERVAL:
                        has_space, space_error = self.check_disk_space()
                        self.last_disk_check = current_time

                        if not has_space:
                            logger.error(f"Disk space check failed: {space_error}")
                            self.process.terminate()
                            try:
                                self.process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                self.process.kill()
                                self.process.wait()
                            return False, space_error, output_path

                    # Read line with timeout to prevent blocking
                    line = self.process.stderr.readline()
                    if not line:
                        # Check if process is still producing output
                        if current_time - last_output_time > 30:
                            logger.warning("No output for 30s, process may be frozen")
                            self.process.terminate()
                            try:
                                self.process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                self.process.kill()
                                self.process.wait()
                            return False, "Process frozen (no output)", output_path
                        time.sleep(0.1)
                        continue

                    last_output_time = current_time

                    # Search for time in the line
                    match = time_pattern.search(line)
                    if match and duration > 0:
                        h, m, s, cs = map(int, match.groups())
                        current_time = h * 3600 + m * 60 + s + cs / 100
                        progress = min(int((current_time / duration) * 100), 99)

                        # Emit only if progress changed significantly
                        if progress > last_progress + 2:  # Reduce frequency
                            self.progress.emit(str(self.input_file), progress)
                            last_progress = progress

                except Exception as e:
                    logger.debug(f"Error reading progress: {e}")
                    break

            # Wait for process completion with timeout
            if self.is_running:
                try:
                    return_code = self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning("Process did not terminate gracefully")
                    self.process.kill()
                    return_code = self.process.wait()
            else:
                # Stop requested
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
                return False, "Conversion stopped", output_path
            
            # Check return code
            if return_code != 0:
                stderr_output = ""
                try:
                    stderr_output = self.process.stderr.read()
                except Exception as e:
                    logger.debug(f"Could not read stderr: {e}")
                return False, f"ffmpeg error (code {return_code}): {stderr_output[:200]}", output_path

            # Check that output file exists and is not empty
            if not output_path.exists():
                return False, "Output file not created", output_path

            output_size = output_path.stat().st_size
            if output_size == 0:
                return False, "Output file empty", output_path

            # Compare sizes
            original_size = self.input_file.stat().st_size

            if output_size >= original_size:
                compression_ratio = ((output_size - original_size) / original_size) * 100
                return False, f"File larger (+{compression_ratio:.1f}%)", output_path

            # Calculate compression
            compression_ratio = ((original_size - output_size) / original_size) * 100

            # Check if size threshold is met
            threshold_met = True
            if self.settings.use_size_threshold:
                threshold_met = output_size <= self.settings.size_threshold

            if threshold_met:
                return True, f"Success (-{compression_ratio:.1f}%, {format_size(output_size)})", output_path
            else:
                return False, f"Reduced (-{compression_ratio:.1f}%) but above threshold", output_path

        except Exception as e:
            logger.error(f"Error during conversion: {e}")
            return False, str(e), output_path
    
    def convert_with_target_size(self) -> Tuple[bool, str, Optional[Path]]:
        """
        Iterative compression until target size is reached.

        Tries to compress the file by progressively increasing CRF
        until output size is <= target_size.

        Returns:
            Tuple[bool, str, Optional[Path]]: (success, message, output path)
        """
        if not self.settings.use_target_size:
            # Normal mode without target size
            return self.convert_file(self.current_attempt)

        # Check that input file is large enough to require compression
        original_size = self.input_file.stat().st_size
        target_size = self.settings.target_size

        if original_size <= target_size:
            return False, f"File already below target size ({format_size(original_size)})", None

        logger.info(f"Iterative compression mode: target={format_size(target_size)}, original={format_size(original_size)}")

        # Iterative compression parameters
        current_crf = self.settings.initial_crf
        crf_step = self.settings.crf_step
        max_crf = self.settings.max_crf
        max_iterations = self.settings.max_compression_attempts

        iteration = 0
        last_output_path = None
        best_output_path = None
        best_size = original_size
        best_crf = None

        while iteration < max_iterations and self.is_running:
            iteration += 1
            self.current_iteration = iteration

            # Emit iteration change signal
            self.iteration_changed.emit(str(self.input_file), iteration, current_crf)

            logger.info(f"Iteration {iteration}/{max_iterations}: CRF={current_crf}")

            # Clean up file from previous attempt
            if last_output_path and last_output_path.exists():
                self.cleanup_temp_files(last_output_path)

            # Attempt conversion with current CRF
            self.current_crf = current_crf
            success, message, output_path = self.convert_file(self.current_attempt, custom_crf=current_crf)

            if not success or not output_path or not output_path.exists():
                logger.warning(f"Iteration {iteration} failed: {message}")

                # If failed and we have a better previous result, use it
                if best_output_path and best_output_path.exists():
                    logger.info(f"Using best previous result ({format_size(best_size)})")
                    if best_size <= target_size:
                        self.current_crf = best_crf if best_crf is not None else self.current_crf
                        return True, f"Target size reached after {iteration-1} iterations", best_output_path
                    else:
                        self.current_crf = best_crf if best_crf is not None else self.current_crf
                        return False, f"Target size not reached (best: {format_size(best_size)})", best_output_path

                # Increase CRF and retry
                current_crf += crf_step
                if current_crf > max_crf:
                    return False, f"Max CRF reached ({max_crf}), aborting", None
                continue

            # Check output file size
            output_size = output_path.stat().st_size
            compression_ratio = ((original_size - output_size) / original_size) * 100

            logger.info(f"Iteration {iteration} result: {format_size(output_size)} (-{compression_ratio:.1f}%)")

            # Keep track of best result
            if output_size < best_size:
                if best_output_path and best_output_path != output_path:
                    self.cleanup_temp_files(best_output_path)
                best_output_path = output_path
                best_size = output_size
                best_crf = current_crf

            # Check if target size is reached
            if output_size <= target_size:
                logger.info(f"✓ Target size reached: {format_size(output_size)} <= {format_size(target_size)}")
                self.current_crf = current_crf
                return True, f"Target size reached after {iteration} iteration(s) (-{compression_ratio:.1f}%)", output_path

            # Size is still too large
            logger.info(f"✗ Size still too large: {format_size(output_size)} > {format_size(target_size)}")

            # Calculate next CRF
            # Heuristic: if far from target, increase CRF more
            size_ratio = output_size / target_size
            if size_ratio > 1.5:
                # Very far from target, increase more rapidly
                next_crf_step = crf_step * 2
            elif size_ratio > 1.2:
                # Fairly far, normal increase
                next_crf_step = crf_step
            else:
                # Close to target, fine-tuned increase
                next_crf_step = max(1, crf_step // 2)

            current_crf += next_crf_step
            last_output_path = output_path

            # Check if we exceeded max CRF
            if current_crf > max_crf:
                logger.warning(f"Max CRF reached ({max_crf}), stopping iterations")
                # Keep the best result obtained
                if best_size < original_size:
                    reduction = ((original_size - best_size) / original_size) * 100
                    self.current_crf = best_crf if best_crf is not None else current_crf
                    return False, f"Max CRF reached. Best result: {format_size(best_size)} (-{reduction:.1f}%)", best_output_path
                else:
                    return False, f"Max CRF reached without size reduction", None

        # Max iterations reached
        if iteration >= max_iterations:
            logger.warning(f"Maximum iterations reached ({max_iterations})")
            if best_output_path and best_size < original_size:
                reduction = ((original_size - best_size) / original_size) * 100
                if best_size <= target_size:
                    self.current_crf = best_crf if best_crf is not None else current_crf
                    return True, f"Target size reached ({format_size(best_size)})", best_output_path
                else:
                    self.current_crf = best_crf if best_crf is not None else current_crf
                    return False, f"Max iterations reached. Best: {format_size(best_size)} (-{reduction:.1f}%)", best_output_path

        return False, "Conversion stopped", None

    def finalize_conversion(self, output_path: Path, params: dict) -> bool:
        """Finalize a successful conversion with robust error handling."""
        try:
            original_size = self.input_file.stat().st_size
            converted_size = output_path.stat().st_size

            # Check that converted file exists and is not empty
            if not output_path.exists() or converted_size == 0:
                logger.error(f"Converted file does not exist or is empty: {output_path}")
                return False

            # Handle original file according to settings
            if self.settings.replace_original:
                # Replace original with temporary file
                try:
                    # Create backup if requested
                    backup_path = None
                    if not self.settings.delete_if_smaller:
                        backup_path = self.input_file.with_suffix('.bak' + self.input_file.suffix)
                        shutil.copy2(str(self.input_file), str(backup_path))
                        logger.debug(f"Backup created: {backup_path}")

                    # Remove original then rename converted file
                    self.input_file.unlink()
                    output_path.rename(self.input_file)

                    logger.debug(f"Original replaced: {self.input_file}")

                    # Update output_path for metadata
                    output_path = self.input_file

                except Exception as e:
                    logger.error(f"Error replacing original: {e}")
                    # Restore backup if possible
                    if backup_path and backup_path.exists():
                        try:
                            backup_path.rename(self.input_file)
                            logger.info(f"Backup restored: {self.input_file}")
                        except Exception as e:
                            logger.error(f"Failed to restore backup: {e}")
                    return False

            else:
                # Keep both files, remove original if requested
                should_delete = (
                    self.settings.delete_if_smaller and
                    converted_size < original_size
                )

                if should_delete:
                    try:
                        self.input_file.unlink()
                        logger.debug(f"Original deleted: {self.input_file}")
                    except Exception as e:
                        logger.warning(f"Cannot delete original: {e}")
                        # This is not a critical error, continue

            # Try to save metadata (non-critical)
            try:
                from .metadata import MetadataManager
                MetadataManager.mark_as_converted(
                    self.input_file,
                    output_path,
                    params
                )
                logger.debug(f"Metadata saved for {output_path}")
            except Exception as e:
                logger.warning(f"Cannot save metadata: {e}")
                # This is not a critical error, continue

            # Save statistics (non-critical)
            try:
                from .stats import StatsManager, ConversionStats
                stats = ConversionStats(
                    input_size=original_size,
                    output_size=converted_size,
                    duration=0.0,
                    attempt_count=self.current_attempt,
                    params_used=params,
                    success=True,
                    input_file=str(self.input_file),
                    output_file=str(output_path)
                )
                StatsManager().add_stat(stats)
                logger.debug(f"Statistics saved for {output_path}")
            except Exception as e:
                logger.warning(f"Cannot save statistics: {e}")
                # This is not a critical error, continue

            return True

        except Exception as e:
            logger.error(f"Critical error during finalization: {e}")
            return False
    
    def run(self):
        """Execute conversion with multiple attempt handling."""
        output_path = None
        all_attempts_failed = False
        last_error_message = ""

        try:
            # Preliminary checks
            should_convert, reason = self.should_convert()
            if not should_convert:
                self.error.emit(str(self.input_file), reason)
                return

            # Iterative compression mode with target size
            if self.settings.use_target_size:
                logger.info(f"Starting iterative compression for {self.input_file.name}")
                success, message, output_path = self.convert_with_target_size()

                if success and output_path:
                    # Finalize successful conversion
                    params = self.get_attempt_params(self.current_attempt, custom_crf=self.current_crf)
                    if self.finalize_conversion(output_path, params):
                        self.progress.emit(str(self.input_file), 100)
                        self.finished.emit(str(self.input_file), True, message)
                        return
                    else:
                        # Finalization failed, clean up and report error
                        if output_path:
                            self.cleanup_temp_files(output_path)
                        self.error.emit(str(self.input_file), "Finalization failed")
                        return
                else:
                    # Iterative compression failed
                    if output_path:
                        self.cleanup_temp_files(output_path)
                    self.error.emit(str(self.input_file), message)
                    return

            # Attempt loop (normal mode)
            while self.current_attempt <= self.max_attempts and self.is_running:
                self.attempt_changed.emit(str(self.input_file), self.current_attempt)

                success, message, output_path = self.convert_file(self.current_attempt)

                if success:
                    # Finalize successful conversion
                    params = self.get_attempt_params(self.current_attempt)
                    if self.finalize_conversion(output_path, params):
                        self.progress.emit(str(self.input_file), 100)
                        self.finished.emit(str(self.input_file), True, message)
                        return
                    else:
                        # Finalization failed, clean up and report error
                        if output_path:
                            self.cleanup_temp_files(output_path)
                        self.error.emit(str(self.input_file), "Finalization failed")
                        return

                # Attempt failed - save error message
                last_error_message = message

                # Clean up temporary file from this failed attempt
                if output_path:
                    self.cleanup_temp_files(output_path)
                    output_path = None

                if self.current_attempt < self.max_attempts and self.is_running:
                    logger.info(f"Attempt {self.current_attempt} failed for {self.input_file.name}: {message}")
                    self.current_attempt += 1
                else:
                    # All attempts failed
                    all_attempts_failed = True
                    break

            # Handle non-compressible files if all attempts failed
            if all_attempts_failed and self.is_running:
                settings = self.settings
                if getattr(settings, 'mark_non_compressible', False):
                    self.mark_as_non_compressible()

                if self.is_running:
                    # Record failure in statistics
                    try:
                        from .stats import StatsManager, ConversionStats
                        original_size = self.input_file.stat().st_size if self.input_file.exists() else 0
                        params = self.get_attempt_params(self.current_attempt)

                        stats = ConversionStats(
                            input_size=original_size,
                            output_size=0,
                            duration=0.0,
                            attempt_count=self.current_attempt,
                            params_used=params,
                            success=False,
                            input_file=str(self.input_file),
                            output_file=""
                        )
                        StatsManager().add_stat(stats)
                    except Exception as e:
                        logger.warning(f"Cannot save failure: {e}")

                    # Use the last error message
                    final_message = f"All attempts failed. Last error: {last_error_message}"
                    self.error.emit(str(self.input_file), final_message)
                else:
                    self.error.emit(str(self.input_file), "Conversion stopped")

        except Exception as e:
            logger.error(f"Critical error in worker: {e}")
            # Clean up any remaining temporary files
            if output_path:
                self.cleanup_temp_files(output_path)
            self.error.emit(str(self.input_file), f"Critical error: {e}")

        finally:
            self.is_running = False
            if self.process:
                try:
                    if self.process.poll() is None:
                        self.process.terminate()
                        self.process.wait(timeout=5)
                except Exception as e:
                    logger.debug(f"Terminate failed, trying kill: {e}")
                    try:
                        if self.process.poll() is None:
                            self.process.kill()
                    except Exception as e:
                        logger.debug(f"Kill also failed: {e}")
    
    def mark_as_non_compressible(self):
        """Mark a file as non-compressible by adding a suffix."""
        try:
            settings = self.settings
            failed_suffix = getattr(settings, 'failed_suffix', '_nocomp')

            # Build new name with suffix
            new_stem = self.input_file.stem
            if not new_stem.endswith(failed_suffix):
                new_stem += failed_suffix

            new_path = self.input_file.with_name(f"{new_stem}{self.input_file.suffix}")

            # Rename the file
            if not new_path.exists():
                self.input_file.rename(new_path)
                logger.info(f"File marked as non-compressible: {new_path.name}")

        except Exception as e:
            logger.warning(f"Cannot mark file as non-compressible: {e}")

    def stop(self):
        """Stop conversion in progress."""
        with QMutexLocker(self.mutex):
            self.is_running = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    self.process.kill()
                    self.process.wait(timeout=2)
                except Exception as e:
                    logger.debug(f"Kill failed: {e}")
            except Exception as e:
                logger.debug(f"Error stopping process: {e}")
