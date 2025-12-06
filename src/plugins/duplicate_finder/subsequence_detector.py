"""Subsequence detection module with memory-safe caching.

This module provides video subsequence detection capabilities with strict memory management.
It can detect when a shorter video is a subset of a longer video.
"""

import cv2
import numpy as np
import os
from typing import Optional, Tuple, List, Dict
from .video_hasher import VideoHasher
from .database_manager import VideoDatabase
from .lru_cache import MemoryBoundedLRUCache
from .analysis.subsequence_verification import SubsequenceVerificationMethods
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.SubsequenceDetector')


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
        sample_interval_seconds: float = 0.75,
        min_match_ratio: float = 0.70,
        temporal_window_frames: int = 5,
        sliding_window_tolerance: int = 3,
        enable_adaptive_refinement: bool = False,  # DISABLED by default - can be VERY slow
        enable_verification: bool = True,  # NEW: Enable Strategy 3 verification
        verification_dct_threshold: float = 75.0,  # NEW: DCT threshold for verification
        verification_sequence_threshold: float = 95.0,  # NEW: Sequence threshold for verification
        verification_workers: int = 2  # NEW: Workers for parallel verification
    ):
        """Initialize subsequence detector with temporal desynchronization handling.

        Args:
            hasher: VideoHasher instance to use for hashing
            max_cache_memory_mb: Maximum cache memory in MB (default: 500MB)
            sample_interval_seconds: Dense sampling interval (default: 0.75 seconds) - REDUCED from 1.5s
            min_match_ratio: Minimum match ratio to consider a subsequence (default: 0.70)
            temporal_window_frames: Number of frames for temporal averaging (default: 5) - SOLUTION 4
            sliding_window_tolerance: Frame tolerance for sliding window (default: 3) - SOLUTION 1
            enable_adaptive_refinement: Enable adaptive refinement (default: False) - SOLUTION 5
            enable_verification: Enable Strategy 3 verification (default: True)
            verification_dct_threshold: DCT threshold for verification (default: 75.0%)
            verification_sequence_threshold: Sequence threshold for verification (default: 95.0%)
            verification_workers: Number of workers for parallel verification (default: 2)
        """
        self.hasher = hasher
        self.db = hasher.db
        self.dense_cache = MemoryBoundedLRUCache(max_memory_mb=max_cache_memory_mb)
        self.sample_interval_seconds = sample_interval_seconds
        self.min_match_ratio = min_match_ratio
        self.temporal_window_frames = temporal_window_frames
        self.sliding_window_tolerance = sliding_window_tolerance
        self.enable_adaptive_refinement = enable_adaptive_refinement
        self.enable_verification = enable_verification
        self._cancelled = False  # Cancellation flag

        # Initialize verification methods (Strategy 3: Scene Cuts Veto)
        if enable_verification:
            self.verifier = SubsequenceVerificationMethods(
                dct_threshold=verification_dct_threshold,
                sequence_threshold=verification_sequence_threshold,
                max_workers=verification_workers
            )
        else:
            self.verifier = None

        logger.info(f"SubsequenceDetector initialized: {sample_interval_seconds}s intervals, "
                   f"{max_cache_memory_mb}MB cache limit, {min_match_ratio*100}% min match, "
                   f"temporal_window={temporal_window_frames}, tolerance=±{sliding_window_tolerance}, "
                   f"adaptive_refinement={enable_adaptive_refinement}, "
                   f"verification={enable_verification} (dct={verification_dct_threshold}%, seq={verification_sequence_threshold}%)")

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

    def _compute_temporal_averaged_hash(self, hashes: List[np.ndarray], center_idx: int) -> np.ndarray:
        """
        Compute temporally averaged hash using majority voting across N consecutive frames.

        SOLUTION 4: Temporal hash averaging reduces sensitivity to minor temporal offsets
        by creating a consensus hash from multiple consecutive frames.

        Args:
            hashes: List of frame hashes
            center_idx: Center frame index for averaging window

        Returns:
            Averaged hash using majority voting
        """
        try:
            # Determine window bounds
            half_window = self.temporal_window_frames // 2
            start_idx = max(0, center_idx - half_window)
            end_idx = min(len(hashes), center_idx + half_window + 1)

            # Extract window of hashes
            window_hashes = hashes[start_idx:end_idx]

            if len(window_hashes) == 0:
                return hashes[center_idx]

            # Stack hashes for vectorized majority voting
            stacked = np.stack(window_hashes)

            # Majority vote: for each bit position, use the most common value
            # Sum across frames (True=1, False=0), then threshold at half
            averaged_hash = np.sum(stacked, axis=0) > (len(window_hashes) / 2)

            return averaged_hash

        except Exception as e:
            logger.error(f"Error in temporal averaging: {e}")
            # Fallback to center frame
            return hashes[center_idx]

    def compute_dense_hash(self, video_path: str, progress_callback=None) -> Tuple[Optional[np.ndarray], float]:
        """Compute dense hash for a video with memory-safe caching and progress feedback.

        Samples frames at regular intervals (default: every 3 seconds) for better
        subsequence detection. Results are cached in memory-bounded LRU cache.

        Args:
            video_path: Path to video file
            progress_callback: Optional callback(current, total, message) for progress updates

        Returns:
            Tuple of (hash_array, duration) or (None, 0.0) on error
        """
        # Check LRU cache first
        cached = self.dense_cache.get(video_path)
        if cached is not None:
            if progress_callback:
                progress_callback(1, 1, "Loaded from cache")
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
                max_frames = 400  # Max ~400 frames even for very long videos (increased for better detection)
                if len(positions) > max_frames:
                    step = len(positions) // max_frames
                    positions = positions[::step]
                    logger.debug(f"Long video: sampling {len(positions)} frames (interval: {self.sample_interval_seconds}s)")

                # Ensure we have at least a few frames
                if len(positions) < 5:
                    positions = [0, total_frames//4, total_frames//2,
                                3*total_frames//4, total_frames-1]
                    positions = [p for p in positions if p < total_frames]

                hashes = []
                total_positions = len(positions)
                for idx, frame_idx in enumerate(positions):
                    # Progress callback every 10 frames or on first/last frame
                    if progress_callback and (idx % 10 == 0 or idx == 0 or idx == total_positions - 1):
                        progress_callback(idx + 1, total_positions, f"Sampling frame {idx + 1}/{total_positions}")

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

    def _compare_with_temporal_tolerance(
        self,
        hash_short: np.ndarray,
        hash_long: np.ndarray,
        start_idx: int
    ) -> float:
        """
        Compare short video hash with long video using sliding window tolerance.

        SOLUTION 1: For each frame in short video, find the best match within a window
        of ±N frames in the long video to handle temporal desynchronization.

        Args:
            hash_short: Short video hash array
            hash_long: Long video hash array
            start_idx: Starting index in long video

        Returns:
            Match ratio (0.0-1.0)
        """
        window_size = len(hash_short)
        tolerance = self.sliding_window_tolerance
        total_matches = 0
        total_bits = 0

        # For each frame in short video
        for i in range(window_size):
            long_idx = start_idx + i

            # Define search window in long video (±tolerance frames)
            search_start = max(0, long_idx - tolerance)
            search_end = min(len(hash_long), long_idx + tolerance + 1)

            # Find best match within window
            best_frame_match = 0
            for j in range(search_start, search_end):
                # Compare this frame
                matches = np.sum(hash_short[i] == hash_long[j])
                if matches > best_frame_match:
                    best_frame_match = matches

            total_matches += best_frame_match
            total_bits += hash_short[i].size

        return total_matches / total_bits if total_bits > 0 else 0.0

    def _adaptive_refinement(
        self,
        short_video: str,
        long_video: str,
        coarse_start_idx: int,
        coarse_duration_short: float,
        fps_long: float
    ) -> Tuple[int, float]:
        """
        Perform adaptive refinement by re-sampling at finer granularity.

        SOLUTION 5: When a partial match is detected, re-sample that specific region
        at higher frequency (0.2s intervals) to find the precise alignment.

        Args:
            short_video: Path to short video
            long_video: Path to long video
            coarse_start_idx: Approximate start index from coarse search
            coarse_duration_short: Duration of short video in seconds
            fps_long: FPS of long video

        Returns:
            Tuple of (refined_start_idx, refined_match_ratio)
        """
        try:
            logger.debug(f"Adaptive refinement: re-sampling region around frame {coarse_start_idx}")

            # Calculate time range to re-sample
            time_start = max(0, (coarse_start_idx * self.sample_interval_seconds) - 2.0)  # 2s buffer before
            time_end = time_start + coarse_duration_short + 4.0  # 2s buffer after

            # Fine sampling interval: 0.2 seconds
            fine_interval = 0.2
            fine_positions_short = []
            fine_positions_long = []

            cv2.setLogLevel(0)
            cap_short = cv2.VideoCapture(short_video)
            cap_long = cv2.VideoCapture(long_video)

            if not cap_short.isOpened() or not cap_long.isOpened():
                cap_short.release()
                cap_long.release()
                return coarse_start_idx, 0.0

            try:
                fps_short = cap_short.get(cv2.CAP_PROP_FPS)
                if fps_short <= 0:
                    fps_short = 25.0

                total_frames_short = int(cap_short.get(cv2.CAP_PROP_FRAME_COUNT))
                total_frames_long = int(cap_long.get(cv2.CAP_PROP_FRAME_COUNT))

                # Sample short video with fine interval
                short_hashes = []
                time = 0
                while time < coarse_duration_short:
                    frame_idx = int(time * fps_short)
                    if frame_idx >= total_frames_short:
                        break

                    cap_short.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap_short.read()
                    if ret and frame is not None:
                        hash_val = self.hasher.compute_frame_hash(frame)
                        if hash_val is not None:
                            short_hashes.append(hash_val)

                    time += fine_interval

                # Sample long video region with fine interval
                long_hashes = []
                time = time_start
                while time < time_end:
                    frame_idx = int(time * fps_long)
                    if frame_idx >= total_frames_long:
                        break

                    cap_long.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap_long.read()
                    if ret and frame is not None:
                        hash_val = self.hasher.compute_frame_hash(frame)
                        if hash_val is not None:
                            long_hashes.append(hash_val)

                    time += fine_interval

                if len(short_hashes) < 3 or len(long_hashes) < len(short_hashes):
                    return coarse_start_idx, 0.0

                # Sliding window search in refined region
                short_arr = np.stack(short_hashes)
                long_arr = np.stack(long_hashes)

                best_ratio = 0.0
                best_idx = 0

                for i in range(len(long_arr) - len(short_arr) + 1):
                    window = long_arr[i:i + len(short_arr)]
                    matches = np.sum(short_arr == window)
                    ratio = matches / short_arr.size if short_arr.size > 0 else 0.0

                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_idx = i

                # Convert fine index back to coarse index
                refined_start_idx = int(best_idx * fine_interval / self.sample_interval_seconds)

                logger.debug(f"Adaptive refinement complete: ratio {best_ratio*100:.1f}%, refined_idx={refined_start_idx}")
                return refined_start_idx, best_ratio

            finally:
                cap_short.release()
                cap_long.release()
                cv2.setLogLevel(1)

        except Exception as e:
            logger.error(f"Error in adaptive refinement: {e}")
            return coarse_start_idx, 0.0

    def find_subsequence(
        self,
        short_video: str,
        long_video: str,
        min_ratio: Optional[float] = None,
        min_duration_seconds: float = 5.0
    ) -> Optional[Dict]:
        """Find if short_video is a subsequence of long_video with temporal tolerance.

        IMPROVED ALGORITHM with 4 solutions:
        - Solution 1: Sliding window with ±N frame tolerance
        - Solution 3: More frequent sampling (0.75s instead of 1.5s)
        - Solution 4: Temporal hash averaging
        - Solution 5: Adaptive refinement at finer granularity

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
                'start_frame_idx': int,
                'confidence': float,
                'refined': bool  # Whether adaptive refinement was used
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
                return self.find_subsequence(long_video, short_video, min_ratio, min_duration_seconds)

            # PHASE 1: Coarse sliding window search with temporal tolerance
            window_size = len(hash_short)
            best_match_ratio = 0.0
            best_start_idx = -1

            for start_idx in range(len(hash_long) - window_size + 1):
                # Use temporal tolerance comparison (SOLUTION 1)
                match_ratio = self._compare_with_temporal_tolerance(
                    hash_short, hash_long, start_idx
                )

                if match_ratio > best_match_ratio:
                    best_match_ratio = match_ratio
                    best_start_idx = start_idx

            # PHASE 2: Adaptive refinement if partial match found (SOLUTION 5)
            refined = False
            if self.enable_adaptive_refinement and best_match_ratio > 0.80 and best_match_ratio < 0.95:
                import time
                logger.warning(f"⚠️  Partial match {best_match_ratio*100:.1f}% - triggering SLOW adaptive refinement...")
                refinement_start = time.time()

                # Get FPS for refinement
                cv2.setLogLevel(0)
                cap = cv2.VideoCapture(long_video)
                fps_long = cap.get(cv2.CAP_PROP_FPS) if cap.isOpened() else 25.0
                cap.release()
                cv2.setLogLevel(1)

                refined_idx, refined_ratio = self._adaptive_refinement(
                    short_video, long_video, best_start_idx, dur_short, fps_long
                )

                refinement_time = time.time() - refinement_start
                logger.warning(f"⏱️  Adaptive refinement took {refinement_time:.1f}s")

                if refined_ratio > best_match_ratio:
                    best_match_ratio = refined_ratio
                    best_start_idx = refined_idx
                    refined = True
                    logger.info(f"Adaptive refinement improved match: {best_match_ratio*100:.1f}%")
                else:
                    logger.info(f"Adaptive refinement did not improve match (stayed at {best_match_ratio*100:.1f}%)")

            # Check if it's a valid subsequence (initial threshold)
            is_subsequence = best_match_ratio >= min_ratio

            if not is_subsequence:
                return {
                    'is_subsequence': False,
                    'match_ratio': best_match_ratio,
                    'start_frame_idx': best_start_idx,
                    'confidence': best_match_ratio,
                    'short_duration': dur_short,
                    'long_duration': dur_long,
                    'refined': refined,
                    'verified': False,
                    'verification_result': None
                }

            # PHASE 3: Strategy 3 Verification (Scene Cuts Veto + DCT)
            verification_result = None
            if self.enable_verification and self.verifier is not None:
                logger.info(f"Initial match {best_match_ratio*100:.1f}% - running Strategy 3 verification...")

                # Calculate start time in long video
                # Convert frame index to time using sampling interval
                start_time = best_start_idx * self.sample_interval_seconds

                verification_result = self.verifier.verify_with_strategy3(
                    short_video=short_video,
                    long_video=long_video,
                    start_time=start_time,
                    duration=dur_short,
                    sequence_score=best_match_ratio * 100.0  # Convert to percentage
                )

                # Update is_subsequence based on verification
                is_subsequence = verification_result['accepted']

                if is_subsequence:
                    logger.info(f"✅ Subsequence VERIFIED: {os.path.basename(short_video)} "
                              f"in {os.path.basename(long_video)} "
                              f"(seq: {best_match_ratio*100:.1f}%, "
                              f"scene: {verification_result['scene_cuts_score']:.1f}%, "
                              f"dct: {verification_result['dct_score']:.1f}%, "
                              f"frame {best_start_idx}, refined={refined})")
                else:
                    logger.info(f"❌ Subsequence REJECTED by verification: {verification_result['rejection_reason']}")
            else:
                # No verification - trust initial match
                if is_subsequence:
                    logger.info(f"Subsequence detected (no verification): {os.path.basename(short_video)} "
                              f"in {os.path.basename(long_video)} "
                              f"(match: {best_match_ratio*100:.1f}%, frame {best_start_idx}, refined={refined})")

            return {
                'is_subsequence': is_subsequence,
                'match_ratio': best_match_ratio,
                'start_frame_idx': best_start_idx,
                'confidence': best_match_ratio,
                'short_duration': dur_short,
                'long_duration': dur_long,
                'refined': refined,
                'verified': self.enable_verification,
                'verification_result': verification_result
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
        based on duration. Can be cancelled by calling cancel().

        Args:
            video_files: List of video file paths
            progress_callback: Optional callback(current, total, message)

        Returns:
            List of tuples: (short_video, long_video, detection_result)
            Empty list if cancelled
        """
        results = []
        self._cancelled = False  # Reset cancellation flag

        # First, get durations for all videos (using standard hash which is cached)
        video_durations = {}
        for video_path in video_files:
            # Check for cancellation
            if self._cancelled:
                logger.info("Subsequence detection cancelled during duration gathering")
                return results

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
            # Check for cancellation
            if self._cancelled:
                logger.info(f"Subsequence detection cancelled after {idx} of {total} pairs checked")
                return results

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

    def cancel(self):
        """Cancel the ongoing subsequence detection.

        Sets the cancellation flag which will be checked during the next
        iteration of detect_all_subsequences(). Safe to call from any thread.
        """
        self._cancelled = True
        logger.info("Subsequence detection cancellation requested")

    def is_cancelled(self) -> bool:
        """
        Check if detection has been cancelled.

        Returns:
            True if cancelled, False otherwise
        """
        return self._cancelled

    def clear_cache(self):
        """Clear dense hash cache to free memory."""
        self.dense_cache.clear()
        logger.info("Dense cache cleared")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return self.dense_cache.get_stats()
