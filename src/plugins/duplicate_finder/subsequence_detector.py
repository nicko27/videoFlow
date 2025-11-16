"""Subsequence detection module with memory-safe caching.

This module provides video subsequence detection capabilities with strict memory management.
It can detect when a shorter video is a subset of a longer video.
"""

import cv2
import numpy as np
import os
from collections import OrderedDict
from typing import Optional, Tuple, List, Dict
from .video_hasher import VideoHasher
from .database_manager import VideoDatabase
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.SubsequenceDetector')


class LRUCache:
    """Memory-bounded LRU cache for dense video hashes.

    Automatically evicts least recently used items when memory limit is reached.
    """

    def __init__(self, max_memory_mb: int = 500):
        """Initialize LRU cache with memory limit.

        Args:
            max_memory_mb: Maximum memory usage in MB (default: 500MB)
        """
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_memory = 0
        self.cache = OrderedDict()  # path -> {'hash': array, 'size': bytes, 'duration': float}
        self.max_memory_mb = max_memory_mb

    def _estimate_size(self, hash_array: np.ndarray) -> int:
        """Estimate memory size of a numpy array in bytes."""
        return hash_array.nbytes + 200  # Array + overhead

    def get(self, key: str) -> Optional[Dict]:
        """Get item from cache, moving it to end (most recent)."""
        if key not in self.cache:
            return None
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, hash_array: np.ndarray, duration: float):
        """Add item to cache, evicting old items if necessary."""
        # Remove if already exists
        if key in self.cache:
            old_size = self.cache[key]['size']
            self.current_memory -= old_size
            del self.cache[key]

        # Calculate size
        item_size = self._estimate_size(hash_array)

        # Evict until we have space
        while self.current_memory + item_size > self.max_memory_bytes and self.cache:
            evicted_key, evicted_value = self.cache.popitem(last=False)  # Remove oldest
            self.current_memory -= evicted_value['size']
            logger.debug(f"Evicted {os.path.basename(evicted_key)} from cache (memory limit)")

        # Add new item
        self.cache[key] = {
            'hash': hash_array,
            'duration': duration,
            'size': item_size
        }
        self.current_memory += item_size

    def clear(self):
        """Clear all cache."""
        self.cache.clear()
        self.current_memory = 0

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            'items': len(self.cache),
            'memory_mb': self.current_memory / (1024 * 1024),
            'max_memory_mb': self.max_memory_mb,
            'usage_percent': (self.current_memory / self.max_memory_bytes * 100) if self.max_memory_bytes > 0 else 0
        }


class SubsequenceDetector:
    """Detects video subsequences with memory-safe dense sampling.

    This detector can find when a shorter video is contained within a longer video
    by using dense frame sampling and sliding window comparison.

    Features:
        - Memory-bounded LRU cache to prevent RAM exhaustion
        - Configurable dense sampling interval (default: every 3 seconds)
        - Sliding window algorithm for subsequence matching
        - Database integration for persistent storage

    Attributes:
        hasher: VideoHasher instance for frame hashing
        db: Database instance
        dense_cache: LRU cache for dense hashes
        sample_interval_seconds: Sampling interval in seconds
        min_match_ratio: Minimum ratio of matching frames (0.0-1.0)
    """

    def __init__(
        self,
        hasher: VideoHasher,
        max_cache_memory_mb: int = 500,
        sample_interval_seconds: float = 3.0,
        min_match_ratio: float = 0.80
    ):
        """Initialize subsequence detector.

        Args:
            hasher: VideoHasher instance to use for hashing
            max_cache_memory_mb: Maximum cache memory in MB (default: 500MB)
            sample_interval_seconds: Dense sampling interval (default: 3.0 seconds)
            min_match_ratio: Minimum match ratio to consider a subsequence (default: 0.80)
        """
        self.hasher = hasher
        self.db = hasher.db
        self.dense_cache = LRUCache(max_memory_mb=max_cache_memory_mb)
        self.sample_interval_seconds = sample_interval_seconds
        self.min_match_ratio = min_match_ratio

        logger.info(f"SubsequenceDetector initialized: {sample_interval_seconds}s intervals, "
                   f"{max_cache_memory_mb}MB cache limit, {min_match_ratio*100}% min match")

    def _is_frame_blank(self, frame: np.ndarray, threshold: float = 0.1) -> bool:
        """
        Check if a frame is mostly blank (black or white).

        Args:
            frame: Video frame (numpy array)
            threshold: Maximum mean brightness for black (0-1 scale)

        Returns:
            True if frame is blank, False otherwise
        """
        try:
            # Convert to grayscale
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame

            # Calculate mean brightness (normalized to 0-1)
            mean_brightness = np.mean(gray) / 255.0

            # Check if mostly black (mean < threshold) or mostly white (mean > 1-threshold)
            is_black = mean_brightness < threshold
            is_white = mean_brightness > (1.0 - threshold)

            return is_black or is_white

        except Exception as e:
            logger.error(f"Error checking blank frame: {e}")
            return False

    def compute_dense_hash(self, video_path: str) -> Tuple[Optional[np.ndarray], float]:
        """Compute dense hash for a video with memory-safe caching.

        Samples frames at regular intervals (default: every 3 seconds) for better
        subsequence detection. Results are cached in memory-bounded LRU cache.

        Args:
            video_path: Path to video file

        Returns:
            Tuple of (hash_array, duration) or (None, 0.0) on error
        """
        # Check LRU cache first
        cached = self.dense_cache.get(video_path)
        if cached is not None:
            return cached['hash'], cached['duration']

        try:
            cv2.setLogLevel(0)
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                raise Exception("Cannot open video")

            try:
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps <= 0:
                    fps = 25.0

                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if total_frames <= 0:
                    # Quick estimation
                    count = 0
                    while count < 500 and cap.grab():
                        count += 1
                    total_frames = count * 10
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

                duration = total_frames / fps

                # Calculate frame positions based on time interval
                frame_interval = int(self.sample_interval_seconds * fps)
                positions = list(range(0, total_frames, frame_interval))

                # Limit to reasonable number of frames to prevent memory issues
                max_frames = 200  # Max ~200 frames even for very long videos
                if len(positions) > max_frames:
                    step = len(positions) // max_frames
                    positions = positions[::step]
                    logger.warning(f"Video too long, sampling reduced to {len(positions)} frames")

                # Ensure we have at least a few frames
                if len(positions) < 5:
                    positions = [0, total_frames//4, total_frames//2,
                                3*total_frames//4, total_frames-1]
                    positions = [p for p in positions if p < total_frames]

                hashes = []
                for frame_idx in positions:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()

                    if ret and frame is not None:
                        # Skip blank frames to avoid false positives
                        if not self._is_frame_blank(frame):
                            frame_hash = self.hasher.compute_frame_hash(frame)
                            if frame_hash is not None:
                                hashes.append(frame_hash)
                    else:
                        # Try next frame
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx + 1)
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            # Skip blank frames to avoid false positives
                            if not self._is_frame_blank(frame):
                                frame_hash = self.hasher.compute_frame_hash(frame)
                                if frame_hash is not None:
                                    hashes.append(frame_hash)

                if len(hashes) < 3:
                    raise Exception(f"Only {len(hashes)} frames read")

                final_hash = np.stack(hashes)

                # Store in LRU cache (will auto-evict if memory limit reached)
                self.dense_cache.put(video_path, final_hash, duration)

                logger.info(f"Dense hash computed: {os.path.basename(video_path)} "
                          f"({len(hashes)} frames, ~{self.dense_cache.get_stats()['memory_mb']:.1f}MB cached)")

                return final_hash, duration

            finally:
                cap.release()
                cv2.setLogLevel(1)

        except Exception as e:
            logger.error(f"Error computing dense hash {os.path.basename(video_path)}: {e}")
            return None, 0.0

    def find_subsequence(
        self,
        short_video: str,
        long_video: str,
        min_ratio: Optional[float] = None,
        min_duration_seconds: float = 5.0
    ) -> Optional[Dict]:
        """Find if short_video is a subsequence of long_video using sliding window.

        Uses a sliding window approach to compare consecutive frames from the short
        video against all possible windows in the long video.

        Args:
            short_video: Path to potentially shorter video
            long_video: Path to potentially longer video
            min_ratio: Minimum match ratio (overrides instance default if provided)
            min_duration_seconds: Minimum duration for valid subsequence (default: 5.0s)

        Returns:
            Dict with detection results or None if not a subsequence:
            {
                'is_subsequence': bool,
                'match_ratio': float,
                'start_frame_idx': int,  # Where in long video the match starts
                'confidence': float
            }
        """
        if min_ratio is None:
            min_ratio = self.min_match_ratio

        try:
            # Get dense hashes for both videos
            hash_short, dur_short = self.compute_dense_hash(short_video)
            hash_long, dur_long = self.compute_dense_hash(long_video)

            if hash_short is None or hash_long is None:
                return None

            # Short video must have minimum duration to avoid false positives
            if dur_short < min_duration_seconds:
                logger.debug(f"Short video duration ({dur_short:.1f}s) below minimum ({min_duration_seconds}s)")
                return None

            # If short video has more frames, swap and retry
            if len(hash_short) > len(hash_long):
                logger.debug(f"Videos mislabeled, swapping: {os.path.basename(short_video)} has more frames than {os.path.basename(long_video)}")
                # Recursively call with swapped parameters
                return self.find_subsequence(long_video, short_video, min_ratio, min_duration_seconds)

            # Sliding window comparison
            window_size = len(hash_short)
            best_match_ratio = 0.0
            best_start_idx = -1

            # Slide the window across the long video
            for start_idx in range(len(hash_long) - window_size + 1):
                window = hash_long[start_idx:start_idx + window_size]

                # Vectorized comparison
                matches = np.sum(hash_short == window)
                total = hash_short.size
                match_ratio = matches / total if total > 0 else 0.0

                if match_ratio > best_match_ratio:
                    best_match_ratio = match_ratio
                    best_start_idx = start_idx

            # Check if it's a valid subsequence
            is_subsequence = best_match_ratio >= min_ratio

            if is_subsequence:
                logger.info(f"Subsequence detected: {os.path.basename(short_video)} "
                          f"in {os.path.basename(long_video)} "
                          f"(match: {best_match_ratio*100:.1f}%, frame {best_start_idx})")

            return {
                'is_subsequence': is_subsequence,
                'match_ratio': best_match_ratio,
                'start_frame_idx': best_start_idx,
                'confidence': best_match_ratio,
                'short_duration': dur_short,
                'long_duration': dur_long
            }

        except Exception as e:
            logger.error(f"Error in subsequence detection: {e}")
            return None

    def detect_all_subsequences(
        self,
        video_files: List[str],
        progress_callback=None
    ) -> List[Tuple[str, str, Dict]]:
        """Detect all subsequences in a list of videos.

        Compares all pairs where one video could be a subsequence of another
        based on duration.

        Args:
            video_files: List of video file paths
            progress_callback: Optional callback(current, total, message)

        Returns:
            List of tuples: (short_video, long_video, detection_result)
        """
        results = []

        # First, get durations for all videos (using standard hash which is cached)
        video_durations = {}
        for video_path in video_files:
            try:
                if video_path in self.hasher.hash_cache:
                    video_durations[video_path] = self.hasher.hash_cache[video_path]['duration']
                else:
                    _, duration = self.hasher.compute_video_hash_fast(video_path)
                    video_durations[video_path] = duration
            except:
                continue

        # Generate pairs where short video is at least 30% shorter
        pairs = []
        for i, video1 in enumerate(video_files):
            if video1 not in video_durations:
                continue

            for video2 in video_files[i+1:]:
                if video2 not in video_durations:
                    continue

                dur1 = video_durations[video1]
                dur2 = video_durations[video2]

                # Check if one is significantly shorter (at least 30% difference)
                if dur1 > 0 and dur2 > 0:
                    ratio = min(dur1, dur2) / max(dur1, dur2)
                    if ratio < 0.70:  # One is at least 30% shorter
                        if dur1 < dur2:
                            pairs.append((video1, video2))
                        else:
                            pairs.append((video2, video1))

        logger.info(f"Checking {len(pairs)} potential subsequence pairs")

        # Check each pair
        total = len(pairs)
        matches_found = 0
        for idx, (short_video, long_video) in enumerate(pairs):
            if progress_callback:
                progress_callback(
                    idx + 1,
                    total,
                    f"Checking {os.path.basename(short_video)} ({matches_found} match(es) found)"
                )

            result = self.find_subsequence(short_video, long_video)

            if result and result['is_subsequence']:
                results.append((short_video, long_video, result))
                matches_found += 1
                logger.info(
                    f"✓ Subsequence detected: {os.path.basename(short_video)} in "
                    f"{os.path.basename(long_video)} ({result['match_ratio']*100:.1f}% match)"
                )

            # Periodically log memory usage
            if (idx + 1) % 10 == 0:
                stats = self.dense_cache.get_stats()
                logger.debug(f"Cache: {stats['items']} items, {stats['memory_mb']:.1f}MB "
                           f"({stats['usage_percent']:.1f}% of limit)")

        return results

    def clear_cache(self):
        """Clear dense hash cache to free memory."""
        self.dense_cache.clear()
        logger.info("Dense cache cleared")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return self.dense_cache.get_stats()
