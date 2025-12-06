"""
Subsequence verification methods for video duplicate detection.

This module implements multiple verification algorithms to confirm or reject
potential subsequence matches found by the initial sequence matching algorithm.

Key verification methods:
- Scene Cuts Alignment: Detects transitions and scene boundaries
- DCT Coefficients: Frequency domain comparison for robust verification
- Strategy 3 (Scene Cuts Veto): Best precision (100%) with 84.2% F1 score
"""

import cv2
import numpy as np
from typing import Dict, Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.SubsequenceVerification')


class SubsequenceVerificationMethods:
    """
    Advanced verification methods for subsequence detection.

    Implements multiple algorithms to verify video subsequence matches:
    - Scene Cuts Alignment (temporal transition detection)
    - DCT Coefficients (frequency domain comparison)
    - Combined Strategy 3 (Scene Cuts Veto + DCT)

    Strategy 3 achieved the best performance in testing:
    - Precision: 100.0%
    - Recall: 72.7%
    - F1 Score: 84.2%
    """

    def __init__(
        self,
        scene_cuts_threshold: float = 50.0,
        dct_threshold: float = 75.0,
        sequence_threshold: float = 95.0,
        max_workers: int = 2
    ):
        """
        Initialize verification methods.

        Args:
            scene_cuts_threshold: Threshold for scene cut detection (default: 50.0)
            dct_threshold: DCT similarity threshold (default: 75.0%)
            sequence_threshold: Sequence match threshold (default: 95.0%)
            max_workers: Maximum parallel workers for verification (default: 2)
        """
        self.scene_cuts_threshold = scene_cuts_threshold
        self.dct_threshold = dct_threshold
        self.sequence_threshold = sequence_threshold
        self.max_workers = max_workers

        logger.info(f"Subsequence verification initialized: "
                   f"scene_threshold={scene_cuts_threshold}, "
                   f"dct_threshold={dct_threshold}%, "
                   f"seq_threshold={sequence_threshold}%, "
                   f"workers={max_workers}")

    def _detect_scene_cuts(
        self,
        video_path: str,
        start_time: float = 0.0,
        duration: float = None,
        sample_rate: float = 1.0
    ) -> float:
        """
        Detect scene cuts/transitions in a video segment.

        Uses frame difference analysis to detect cuts, fades, and transitions.
        Returns a percentage indicating how well scene boundaries align.

        Args:
            video_path: Path to video file
            start_time: Start time in seconds (default: 0.0)
            duration: Duration to analyze in seconds (None = entire video)
            sample_rate: Sampling rate in seconds (default: 1.0 - every second)

        Returns:
            Scene cuts score (0-100%), where:
            - 100% = clear scene transitions detected
            - 0% = no scene transitions (likely false positive)
        """
        try:
            cv2.setLogLevel(0)
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                logger.error(f"Cannot open video: {video_path}")
                return 0.0

            try:
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps <= 0:
                    fps = 25.0

                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                start_frame = int(start_time * fps)

                if duration:
                    end_frame = min(start_frame + int(duration * fps), total_frames)
                else:
                    end_frame = total_frames

                # Sample frames at regular intervals
                frame_interval = int(sample_rate * fps)
                if frame_interval < 1:
                    frame_interval = 1

                prev_frame = None
                scene_changes = 0
                frames_compared = 0
                differences = []

                for frame_pos in range(start_frame, end_frame, frame_interval):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
                    ret, frame = cap.read()

                    if not ret or frame is None:
                        continue

                    # Convert to grayscale and resize for faster processing
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    gray = cv2.resize(gray, (128, 72))  # Reduced resolution

                    if prev_frame is not None:
                        # Calculate frame difference
                        diff = cv2.absdiff(prev_frame, gray)
                        mean_diff = np.mean(diff)
                        differences.append(mean_diff)
                        frames_compared += 1

                        # Detect scene cut (large sudden change)
                        if mean_diff > self.scene_cuts_threshold:
                            scene_changes += 1
                            logger.debug(f"Scene cut detected at frame {frame_pos}: diff={mean_diff:.1f}")

                    prev_frame = gray

                # Calculate score based on presence of scene cuts
                if frames_compared == 0:
                    return 0.0

                # Score: 0% if no scene cuts, 100% if scene cuts detected
                # This is a binary indicator - presence of scene cuts suggests
                # this is a real extract (with beginning/end transitions)
                if scene_changes > 0:
                    # At least one scene cut detected - likely real extract
                    return 100.0
                else:
                    # No scene cuts - likely false positive (similar content)
                    return 0.0

            finally:
                cap.release()
                cv2.setLogLevel(1)

        except Exception as e:
            logger.error(f"Error detecting scene cuts: {e}")
            return 0.0

    def _compute_dct_similarity(
        self,
        video1_path: str,
        video2_path: str,
        start_time1: float = 0.0,
        start_time2: float = 0.0,
        duration: float = None,
        num_samples: int = 10
    ) -> float:
        """
        Compare two video segments using DCT (Discrete Cosine Transform) coefficients.

        DCT comparison is robust to:
        - Codec changes (mp4 -> mkv)
        - Slight quality differences
        - Minor color grading adjustments

        Args:
            video1_path: Path to first video
            video2_path: Path to second video
            start_time1: Start time in video1 (seconds)
            start_time2: Start time in video2 (seconds)
            duration: Duration to compare (None = shortest video)
            num_samples: Number of frames to sample (default: 10)

        Returns:
            DCT similarity score (0-100%)
        """
        try:
            cv2.setLogLevel(0)
            cap1 = cv2.VideoCapture(video1_path)
            cap2 = cv2.VideoCapture(video2_path)

            if not cap1.isOpened() or not cap2.isOpened():
                logger.error("Cannot open one or both videos for DCT comparison")
                return 0.0

            try:
                fps1 = cap1.get(cv2.CAP_PROP_FPS) or 25.0
                fps2 = cap2.get(cv2.CAP_PROP_FPS) or 25.0

                total_frames1 = int(cap1.get(cv2.CAP_PROP_FRAME_COUNT))
                total_frames2 = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))

                # Determine analysis duration
                if duration is None:
                    duration1 = total_frames1 / fps1 - start_time1
                    duration2 = total_frames2 / fps2 - start_time2
                    duration = min(duration1, duration2)

                # Calculate frame positions to sample
                positions1 = []
                positions2 = []

                for i in range(num_samples):
                    # Evenly spaced samples across duration
                    time_offset = (duration / num_samples) * i
                    frame1 = int((start_time1 + time_offset) * fps1)
                    frame2 = int((start_time2 + time_offset) * fps2)

                    if frame1 < total_frames1 and frame2 < total_frames2:
                        positions1.append(frame1)
                        positions2.append(frame2)

                if len(positions1) < 3:
                    logger.warning("Not enough frames for DCT comparison")
                    return 0.0

                # Extract and compare DCT coefficients
                similarities = []

                for pos1, pos2 in zip(positions1, positions2):
                    cap1.set(cv2.CAP_PROP_POS_FRAMES, pos1)
                    cap2.set(cv2.CAP_PROP_POS_FRAMES, pos2)

                    ret1, frame1 = cap1.read()
                    ret2, frame2 = cap2.read()

                    if not (ret1 and ret2 and frame1 is not None and frame2 is not None):
                        continue

                    # Compute DCT similarity for this frame pair
                    sim = self._compare_frames_dct(frame1, frame2)
                    similarities.append(sim)

                if not similarities:
                    return 0.0

                # Return average similarity
                avg_similarity = np.mean(similarities) * 100.0
                logger.debug(f"DCT similarity: {avg_similarity:.1f}% ({len(similarities)} frames)")

                return float(avg_similarity)

            finally:
                cap1.release()
                cap2.release()
                cv2.setLogLevel(1)

        except Exception as e:
            logger.error(f"Error computing DCT similarity: {e}")
            return 0.0

    def _compare_frames_dct(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """
        Compare two frames using DCT coefficients.

        Args:
            frame1: First frame (numpy array)
            frame2: Second frame (numpy array)

        Returns:
            Similarity score (0.0-1.0)
        """
        try:
            # Convert to grayscale and resize
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

            # Resize to standard size for comparison
            size = (64, 64)
            gray1 = cv2.resize(gray1, size)
            gray2 = cv2.resize(gray2, size)

            # Compute DCT for both frames
            dct1 = cv2.dct(np.float32(gray1))
            dct2 = cv2.dct(np.float32(gray2))

            # Use only low-frequency coefficients (top-left 8x8 block)
            # These are most robust to compression/encoding changes
            dct1_lf = dct1[:8, :8]
            dct2_lf = dct2[:8, :8]

            # Flatten and normalize
            dct1_flat = dct1_lf.flatten()
            dct2_flat = dct2_lf.flatten()

            # Compute cosine similarity
            dot_product = np.dot(dct1_flat, dct2_flat)
            norm1 = np.linalg.norm(dct1_flat)
            norm2 = np.linalg.norm(dct2_flat)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # Convert from [-1, 1] to [0, 1]
            similarity = (similarity + 1.0) / 2.0

            return max(0.0, min(1.0, similarity))

        except Exception as e:
            logger.error(f"Error in DCT frame comparison: {e}")
            return 0.0

    def verify_with_strategy3(
        self,
        short_video: str,
        long_video: str,
        start_time: float,
        duration: float,
        sequence_score: float
    ) -> Dict:
        """
        Verify subsequence match using Strategy 3 (Scene Cuts Veto).

        This is the best-performing strategy from testing:
        - Precision: 100.0% (zero false positives)
        - Recall: 72.7%
        - F1 Score: 84.2%

        Algorithm:
        1. Check scene cuts in short video
        2. If scene_cuts = 0%: REJECT (likely false positive)
        3. If scene_cuts > 0% AND dct >= 75% AND sequence >= 95%: ACCEPT

        Args:
            short_video: Path to short video
            long_video: Path to long video
            start_time: Start position in long video (seconds)
            duration: Duration of match (seconds)
            sequence_score: Sequence match score (0-100%)

        Returns:
            Dictionary with verification results:
            {
                'accepted': bool,
                'scene_cuts_score': float,
                'dct_score': float,
                'sequence_score': float,
                'rejection_reason': str (if rejected)
            }
        """
        start = time.time()

        logger.info(f"Verifying with Strategy 3: {short_video} @ {start_time:.1f}s (seq={sequence_score:.1f}%)")

        # Step 1: Detect scene cuts in short video
        scene_score = self._detect_scene_cuts(short_video, 0.0, duration)

        # Step 2: Scene cuts veto - reject if no scene cuts
        if scene_score == 0.0:
            elapsed = time.time() - start
            logger.info(f"❌ REJECTED (no scene cuts) in {elapsed:.2f}s")
            return {
                'accepted': False,
                'scene_cuts_score': scene_score,
                'dct_score': 0.0,
                'sequence_score': sequence_score,
                'rejection_reason': 'No scene cuts detected (likely similar content, not extract)'
            }

        # Step 3: Compute DCT similarity
        dct_score = self._compute_dct_similarity(
            short_video, long_video,
            start_time1=0.0,
            start_time2=start_time,
            duration=duration,
            num_samples=10
        )

        # Step 4: Apply thresholds
        accepted = (
            scene_score > 0.0 and
            dct_score >= self.dct_threshold and
            sequence_score >= self.sequence_threshold
        )

        elapsed = time.time() - start

        if accepted:
            logger.info(f"✅ ACCEPTED: scene={scene_score:.1f}% dct={dct_score:.1f}% "
                       f"seq={sequence_score:.1f}% in {elapsed:.2f}s")
        else:
            reason = []
            if dct_score < self.dct_threshold:
                reason.append(f"DCT too low ({dct_score:.1f}% < {self.dct_threshold}%)")
            if sequence_score < self.sequence_threshold:
                reason.append(f"Sequence too low ({sequence_score:.1f}% < {self.sequence_threshold}%)")

            rejection_reason = "; ".join(reason) if reason else "Unknown"
            logger.info(f"❌ REJECTED: {rejection_reason} in {elapsed:.2f}s")

            return {
                'accepted': False,
                'scene_cuts_score': scene_score,
                'dct_score': dct_score,
                'sequence_score': sequence_score,
                'rejection_reason': rejection_reason
            }

        return {
            'accepted': True,
            'scene_cuts_score': scene_score,
            'dct_score': dct_score,
            'sequence_score': sequence_score,
            'rejection_reason': None
        }

    def verify_batch(
        self,
        matches: List[Dict]
    ) -> List[Dict]:
        """
        Verify multiple matches in parallel using multi-threading.

        Args:
            matches: List of match dictionaries, each containing:
                - short_video: str
                - long_video: str
                - start_time: float
                - duration: float
                - sequence_score: float

        Returns:
            List of verification results (same order as input)
        """
        if not matches:
            return []

        logger.info(f"Verifying {len(matches)} matches with {self.max_workers} workers...")

        results = [None] * len(matches)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all verification tasks
            future_to_idx = {}
            for idx, match in enumerate(matches):
                future = executor.submit(
                    self.verify_with_strategy3,
                    match['short_video'],
                    match['long_video'],
                    match['start_time'],
                    match['duration'],
                    match['sequence_score']
                )
                future_to_idx[future] = idx

            # Collect results as they complete
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    result = future.result()
                    results[idx] = result
                except Exception as e:
                    logger.error(f"Verification failed for match {idx}: {e}")
                    results[idx] = {
                        'accepted': False,
                        'scene_cuts_score': 0.0,
                        'dct_score': 0.0,
                        'sequence_score': matches[idx].get('sequence_score', 0.0),
                        'rejection_reason': f'Verification error: {str(e)}'
                    }

        accepted_count = sum(1 for r in results if r and r['accepted'])
        logger.info(f"Verification complete: {accepted_count}/{len(matches)} accepted")

        return results
