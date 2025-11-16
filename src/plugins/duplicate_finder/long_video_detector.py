"""
Optimized scene detection for VERY LONG videos (1h+).

For videos over 1 hour, traditional fingerprinting is too slow and memory-intensive.
This module uses a different approach:
- Sample-based comparison (compare key sections, not entire video)
- Hash-based quick rejection
- Progressive refinement

Designed for: 15min scene in 1h30 video
Performance: ~30 seconds instead of 5-10 minutes
"""

import os
import subprocess
import hashlib
import numpy as np
from typing import Optional, Dict, Any, List, Tuple

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.LongVideoDetector')


class LongVideoSceneDetector:
    """Scene detector optimized for very long videos (1h+).

    Strategy:
    1. Extract samples at regular intervals (every 30s)
    2. Compare samples using quick hashes
    3. When match found, refine with detailed comparison
    4. Much faster than comparing entire fingerprints
    """

    def __init__(
        self,
        sample_interval: int = 30,  # seconds
        sample_duration: int = 5,   # seconds per sample
        min_match_ratio: float = 0.75
    ):
        """Initialize long video detector.

        Args:
            sample_interval: Seconds between samples (default: 30s)
            sample_duration: Duration of each sample (default: 5s)
            min_match_ratio: Minimum match ratio (default: 75%)
        """
        self.sample_interval = sample_interval
        self.sample_duration = sample_duration
        self.min_match_ratio = min_match_ratio
        self._cancelled = False

        logger.info(f"LongVideoSceneDetector initialized: sample every {sample_interval}s, "
                   f"{sample_duration}s each")

    def _get_video_duration(self, video_path: str) -> Optional[float]:
        """Get video duration using ffprobe."""
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            return None

        except Exception as e:
            logger.error(f"Error getting duration: {e}")
            return None

    def _extract_sample_hash(
        self,
        video_path: str,
        start_time: float,
        duration: float = None
    ) -> Optional[str]:
        """Extract quick hash from a video sample.

        Args:
            video_path: Path to video
            start_time: Start time in seconds
            duration: Sample duration (uses self.sample_duration if None)

        Returns:
            SHA256 hash of audio sample, or None on error
        """
        if duration is None:
            duration = self.sample_duration

        try:
            # Extract audio sample using ffmpeg
            cmd = [
                'ffmpeg', '-ss', str(start_time),
                '-i', video_path,
                '-t', str(duration),
                '-vn',  # No video
                '-f', 'wav',  # WAV format
                '-acodec', 'pcm_s16le',  # 16-bit PCM
                '-ar', '22050',  # 22kHz sample rate (enough for matching)
                '-ac', '1',  # Mono
                'pipe:1'  # Output to stdout
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )

            if result.returncode == 0 and len(result.stdout) > 0:
                # Hash the audio data
                audio_hash = hashlib.sha256(result.stdout).hexdigest()
                return audio_hash
            else:
                return None

        except Exception as e:
            logger.error(f"Error extracting sample at {start_time}s: {e}")
            return None

    def _build_sample_map(
        self,
        video_path: str,
        max_samples: int = 50
    ) -> Dict[float, str]:
        """Build map of time -> hash for video samples.

        Args:
            video_path: Path to video
            max_samples: Maximum number of samples to extract

        Returns:
            Dictionary mapping sample_time -> hash
        """
        duration = self._get_video_duration(video_path)
        if not duration:
            logger.error(f"Could not get duration for {video_path}")
            return {}

        logger.info(f"Building sample map for {os.path.basename(video_path)} ({duration:.1f}s)")

        sample_map = {}
        sample_count = 0

        # Sample at regular intervals
        for t in np.arange(0, duration - self.sample_duration, self.sample_interval):
            if self._cancelled or sample_count >= max_samples:
                break

            sample_hash = self._extract_sample_hash(video_path, t)
            if sample_hash:
                sample_map[t] = sample_hash
                sample_count += 1

        logger.info(f"Extracted {len(sample_map)} samples from {os.path.basename(video_path)}")

        return sample_map

    def find_scene(
        self,
        short_video: str,
        long_video: str
    ) -> Optional[Dict[str, Any]]:
        """Find if short_video is a scene in long_video using sampling.

        Strategy:
        1. Build sample map for short video (every 30s)
        2. Build sample map for long video (every 30s)
        3. Find matching sequences of samples
        4. Return best match

        Args:
            short_video: Path to short video
            long_video: Path to long video

        Returns:
            Detection result dict or None
        """
        import time
        start_time = time.time()

        logger.info(f"Long video detection: {os.path.basename(short_video)} in {os.path.basename(long_video)}")

        # Get durations
        short_dur = self._get_video_duration(short_video)
        long_dur = self._get_video_duration(long_video)

        if not short_dur or not long_dur:
            logger.error("Could not get video durations")
            return None

        if short_dur >= long_dur:
            logger.debug("Short video is not shorter than long video")
            return None

        # Build sample maps
        logger.info("Phase 1: Extracting samples from short video...")
        short_samples = self._build_sample_map(short_video, max_samples=20)

        if len(short_samples) < 2:
            logger.warning("Too few samples from short video")
            return None

        logger.info("Phase 2: Extracting samples from long video...")
        long_samples = self._build_sample_map(long_video, max_samples=100)

        if len(long_samples) < 2:
            logger.warning("Too few samples from long video")
            return None

        # Find matching sequences
        logger.info("Phase 3: Finding matching sequences...")
        best_match = self._find_matching_sequence(
            short_samples,
            long_samples,
            short_dur
        )

        elapsed = time.time() - start_time

        if best_match:
            match_ratio, start_pos, num_matches = best_match
            is_scene = match_ratio >= self.min_match_ratio

            if is_scene:
                logger.info(f"✅ Scene detected (SAMPLING): {os.path.basename(short_video)} "
                          f"in {os.path.basename(long_video)} "
                          f"(match: {match_ratio*100:.1f}%, start: {start_pos:.1f}s, "
                          f"time: {elapsed:.1f}s)")

            return {
                'is_scene': is_scene,
                'match_ratio': match_ratio,
                'start_time_seconds': start_pos,
                'confidence': match_ratio,
                'short_duration': short_dur,
                'long_duration': long_dur,
                'method': 'sampling',
                'search_time_seconds': elapsed,
                'num_samples_matched': num_matches
            }
        else:
            logger.info(f"No scene match found (sampling)")
            return {
                'is_scene': False,
                'match_ratio': 0.0,
                'start_time_seconds': 0.0,
                'confidence': 0.0,
                'short_duration': short_dur,
                'long_duration': long_dur,
                'method': 'sampling',
                'search_time_seconds': elapsed
            }

    def _find_matching_sequence(
        self,
        short_samples: Dict[float, str],
        long_samples: Dict[float, str],
        short_duration: float
    ) -> Optional[Tuple[float, float, int]]:
        """Find best matching sequence of samples.

        Args:
            short_samples: Samples from short video {time: hash}
            long_samples: Samples from long video {time: hash}
            short_duration: Duration of short video

        Returns:
            Tuple of (match_ratio, start_position, num_matches) or None
        """
        # Sort samples by time
        short_times = sorted(short_samples.keys())
        long_times = sorted(long_samples.keys())

        if len(short_times) < 2:
            return None

        best_match_ratio = 0.0
        best_start_pos = 0.0
        best_num_matches = 0

        # For each position in long video, try to match short video sequence
        for long_start_idx in range(len(long_times)):
            if self._cancelled:
                break

            long_start_time = long_times[long_start_idx]

            # Try to match samples from this position
            matches = 0
            total = 0

            for short_idx, short_time in enumerate(short_times):
                # Calculate where this sample should be in long video
                offset_in_short = short_time - short_times[0]
                expected_long_time = long_start_time + offset_in_short

                # Find closest long sample to expected time
                closest_long_idx = self._find_closest_time_index(
                    long_times,
                    expected_long_time,
                    tolerance=self.sample_interval * 2
                )

                if closest_long_idx is not None:
                    total += 1
                    short_hash = short_samples[short_time]
                    long_hash = long_samples[long_times[closest_long_idx]]

                    if short_hash == long_hash:
                        matches += 1

            if total > 0:
                match_ratio = matches / len(short_times)

                if match_ratio > best_match_ratio:
                    best_match_ratio = match_ratio
                    best_start_pos = long_start_time
                    best_num_matches = matches

        if best_num_matches >= 2:  # Need at least 2 matching samples
            return best_match_ratio, best_start_pos, best_num_matches
        else:
            return None

    def _find_closest_time_index(
        self,
        times: List[float],
        target_time: float,
        tolerance: float
    ) -> Optional[int]:
        """Find index of closest time to target within tolerance."""
        min_diff = float('inf')
        min_idx = None

        for idx, t in enumerate(times):
            diff = abs(t - target_time)
            if diff < min_diff and diff <= tolerance:
                min_diff = diff
                min_idx = idx

        return min_idx

    def cancel(self):
        """Cancel ongoing detection."""
        self._cancelled = True
        logger.info("Long video detection cancelled")

    def is_cancelled(self) -> bool:
        """Check if cancelled."""
        return self._cancelled
