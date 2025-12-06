"""
Level 3: pHash visual confirmation module.

This module provides visual duplicate confirmation using perceptual hashing (pHash).
It extracts key frames from videos and compares them using Hamming distance to
verify visual similarity with high precision.
"""

import cv2
import numpy as np
import os
from typing import List, Tuple, Dict, Optional, Callable
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.PHashComparator')


class PHashComparator:
    """
    Visual duplicate confirmation using perceptual hashing.

    This class implements Level 3 of the advanced 3-level duplicate detection.
    It samples frames at regular intervals and compares their pHash signatures
    to provide final visual confirmation of duplicates.

    Attributes:
        phash_threshold: Maximum Hamming distance for similar frames (default: 10 bits)
        frame_rate_threshold: Minimum ratio of similar frames (default: 0.8 = 80%)
        n_frames: Number of frames to sample per video (default: 10)
    """

    def __init__(
        self,
        phash_threshold: int = 10,
        frame_rate_threshold: float = 0.8,
        n_frames: int = 10
    ):
        """
        Initialize pHash comparator.

        Args:
            phash_threshold: Maximum Hamming distance for frames to be considered similar
            frame_rate_threshold: Minimum ratio of similar frames to confirm duplicate
            n_frames: Number of frames to sample from each video
        """
        self.phash_threshold = phash_threshold
        self.frame_rate_threshold = frame_rate_threshold
        self.n_frames = n_frames

        logger.info(
            f"PHashComparator initialized: threshold={phash_threshold} bits, "
            f"frame_rate={frame_rate_threshold:.0%}, n_frames={n_frames}"
        )

    def extract_frames(self, video_path: str) -> Tuple[List[np.ndarray], List[int]]:
        """
        Extract evenly-spaced frames from a video.

        Samples frames at regular intervals (0%, 10%, 20%, ..., 90% of duration).

        Args:
            video_path: Path to the video file

        Returns:
            Tuple of (frames_list, frame_indices)
            - frames_list: List of extracted frames as numpy arrays
            - frame_indices: List of frame indices where frames were extracted
        """
        frames = []
        frame_indices = []

        try:
            # Disable OpenCV logging
            cv2.setLogLevel(0)

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Cannot open video: {video_path}")
                cv2.setLogLevel(1)
                return [], []

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames == 0:
                logger.error(f"Video has 0 frames: {video_path}")
                cap.release()
                cv2.setLogLevel(1)
                return [], []

            # Calculate frame positions (0%, 10%, 20%, ..., 90%)
            # Avoid the very end (100%) as it might be black/corrupted
            positions = np.linspace(0, 0.9, self.n_frames)
            target_indices = [int(pos * (total_frames - 1)) for pos in positions]

            # Extract frames
            for idx in target_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()

                if ret and frame is not None:
                    frames.append(frame)
                    frame_indices.append(idx)
                else:
                    logger.warning(
                        f"Failed to extract frame {idx} from {os.path.basename(video_path)}"
                    )

            cap.release()
            cv2.setLogLevel(1)

            logger.debug(
                f"Extracted {len(frames)}/{self.n_frames} frames from "
                f"{os.path.basename(video_path)}"
            )

            return frames, frame_indices

        except Exception as e:
            logger.error(f"Error extracting frames from {video_path}: {e}")
            cv2.setLogLevel(1)
            return [], []

    def compute_phash(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Compute perceptual hash (pHash) for a single frame.

        Uses DCT (Discrete Cosine Transform) to create a robust hash that is
        resilient to minor modifications like compression or scaling.

        Args:
            frame: Video frame as numpy array (BGR format)

        Returns:
            Binary hash as numpy array (8x8 = 64 bits), or None on error
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Resize to 32x32 for DCT
            resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)

            # Apply DCT (Discrete Cosine Transform)
            dct = cv2.dct(np.float32(resized))

            # Extract low-frequency 8x8 region (top-left corner)
            dct_low = dct[:8, :8]

            # Calculate average (excluding DC component [0,0])
            avg = (dct_low[1:, :].mean() + dct_low[0, 1:].mean()) / 2

            # Create binary hash: 1 if > average, 0 otherwise
            phash = dct_low > avg

            return phash

        except Exception as e:
            logger.error(f"Error computing pHash: {e}")
            return None

    def hamming_distance(
        self,
        hash1: np.ndarray,
        hash2: np.ndarray
    ) -> int:
        """
        Calculate Hamming distance between two pHash signatures.

        The Hamming distance is the number of bit positions where the two
        hashes differ. Lower distance means more similar images.

        Args:
            hash1: First pHash (binary numpy array)
            hash2: Second pHash (binary numpy array)

        Returns:
            Hamming distance (number of differing bits)
        """
        try:
            # XOR to find differing bits, then count them
            xor = np.bitwise_xor(hash1, hash2)
            distance = np.sum(xor)
            return int(distance)

        except Exception as e:
            logger.error(f"Error computing Hamming distance: {e}")
            return 999  # Return high distance on error

    def compare_frame_pair(
        self,
        frame1: np.ndarray,
        frame2: np.ndarray
    ) -> Tuple[bool, int]:
        """
        Compare two frames using pHash.

        Args:
            frame1: First video frame
            frame2: Second video frame

        Returns:
            Tuple of (is_similar, hamming_distance)
            - is_similar: True if distance <= threshold
            - hamming_distance: The actual Hamming distance
        """
        hash1 = self.compute_phash(frame1)
        hash2 = self.compute_phash(frame2)

        if hash1 is None or hash2 is None:
            return False, 999

        distance = self.hamming_distance(hash1, hash2)
        is_similar = distance <= self.phash_threshold

        return is_similar, distance

    def verify_visual_similarity(
        self,
        video1_path: str,
        video2_path: str
    ) -> Dict:
        """
        Verify visual similarity between two videos.

        Extracts frames from both videos and compares them pairwise using pHash.
        Videos are considered duplicates if enough frames are similar.

        Args:
            video1_path: Path to first video
            video2_path: Path to second video

        Returns:
            Dictionary with:
            - 'is_duplicate': bool - True if videos are duplicates
            - 'frames_compared': int - Number of frame pairs compared
            - 'frames_similar': int - Number of similar frame pairs
            - 'similarity_rate': float - Ratio of similar frames (0.0-1.0)
            - 'avg_distance': float - Average Hamming distance
            - 'max_distance': int - Maximum Hamming distance
            - 'frame_indices': list - Frame indices used for comparison
        """
        # Extract frames from both videos
        frames1, indices1 = self.extract_frames(video1_path)
        frames2, indices2 = self.extract_frames(video2_path)

        # Check if we have enough frames
        if len(frames1) < 3 or len(frames2) < 3:
            logger.warning(
                f"Not enough frames extracted: "
                f"{len(frames1)} from video1, {len(frames2)} from video2"
            )
            return {
                'is_duplicate': False,
                'frames_compared': 0,
                'frames_similar': 0,
                'similarity_rate': 0.0,
                'avg_distance': 999.0,
                'max_distance': 999,
                'frame_indices': []
            }

        # Use minimum number of frames available
        n_compare = min(len(frames1), len(frames2))
        frames1 = frames1[:n_compare]
        frames2 = frames2[:n_compare]

        # Compare frame pairs
        similar_count = 0
        distances = []

        for i, (frame1, frame2) in enumerate(zip(frames1, frames2)):
            is_similar, distance = self.compare_frame_pair(frame1, frame2)
            distances.append(distance)

            if is_similar:
                similar_count += 1

            logger.debug(
                f"Frame {i}: distance={distance} bits, "
                f"similar={is_similar} (threshold={self.phash_threshold})"
            )

        # Calculate statistics
        frames_compared = n_compare
        similarity_rate = similar_count / frames_compared if frames_compared > 0 else 0.0
        avg_distance = np.mean(distances) if distances else 999.0
        max_distance = max(distances) if distances else 999

        # Determine if duplicate based on similarity rate threshold
        is_duplicate = similarity_rate >= self.frame_rate_threshold

        result = {
            'is_duplicate': is_duplicate,
            'frames_compared': frames_compared,
            'frames_similar': similar_count,
            'similarity_rate': similarity_rate,
            'avg_distance': float(avg_distance),
            'max_distance': max_distance,
            'frame_indices': indices1[:n_compare]  # Frame indices used
        }

        logger.info(
            f"Visual comparison: {os.path.basename(video1_path)} vs "
            f"{os.path.basename(video2_path)} - "
            f"{similar_count}/{frames_compared} similar frames ({similarity_rate:.0%}), "
            f"avg_distance={avg_distance:.1f} bits, "
            f"duplicate={is_duplicate}"
        )

        return result

    def confirm_duplicates(
        self,
        candidate_pairs: List[Tuple],
        db_manager,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """
        Confirm duplicates from Level 2 candidates using visual verification.

        Args:
            candidate_pairs: List of tuples from Level 2
                Each tuple: (file1_path, file2_path, level1_score, level2_score)
            db_manager: Database manager instance for storing results
            progress_callback: Optional callback(current, total, status_msg)

        Returns:
            List of confirmed duplicate dictionaries with:
            - 'file1': str - First video path
            - 'file2': str - Second video path
            - 'level1_score': float - LSH score from Level 1
            - 'level2_score': float - Audio score from Level 2
            - 'level3_score': float - Visual similarity rate
            - 'confidence': str - Confidence level ('high', 'medium', 'low')
            - 'phash_distance': float - Average pHash distance
        """
        confirmed = []
        total = len(candidate_pairs)

        logger.info(f"Starting Level 3 visual confirmation on {total} candidate pairs")

        for idx, pair_data in enumerate(candidate_pairs):
            # Handle different tuple formats
            if len(pair_data) >= 4:
                file1, file2, level1_score, level2_score = pair_data[:4]
            else:
                logger.warning(f"Invalid pair data format: {pair_data}")
                continue

            # Update progress
            if progress_callback:
                progress_callback(
                    idx + 1,
                    total,
                    f"Verifying {os.path.basename(file1)} vs {os.path.basename(file2)}"
                )

            # Check if files exist
            if not os.path.exists(file1) or not os.path.exists(file2):
                logger.warning(f"Files no longer exist: {file1} or {file2}")
                continue

            # Verify visual similarity
            result = self.verify_visual_similarity(file1, file2)

            # Store Level 3 result in database
            db_manager.store_level3_result(
                file1,
                file2,
                int(result['avg_distance']),
                result['frames_compared'],
                result['frames_similar'],
                result['frame_indices']
            )

            # Only keep confirmed duplicates
            if result['is_duplicate']:
                # Calculate confidence level
                confidence = self._calculate_confidence(
                    level1_score,
                    level2_score,
                    result['similarity_rate']
                )

                confirmed_duplicate = {
                    'file1': file1,
                    'file2': file2,
                    'level1_score': level1_score,
                    'level2_score': level2_score,
                    'level3_score': result['similarity_rate'],
                    'confidence': confidence,
                    'phash_distance': result['avg_distance']
                }

                confirmed.append(confirmed_duplicate)

                logger.info(
                    f"✓ Duplicate confirmed ({confidence}): "
                    f"{os.path.basename(file1)} <-> {os.path.basename(file2)} "
                    f"(L1={level1_score:.2f}, L2={level2_score:.2f}, "
                    f"L3={result['similarity_rate']:.0%})"
                )

        logger.info(
            f"Level 3 complete: {len(confirmed)}/{total} duplicates confirmed "
            f"({len(confirmed)/total*100:.1f}% confirmation rate)"
        )

        return confirmed

    def _calculate_confidence(
        self,
        level1_score: float,
        level2_score: float,
        level3_score: float
    ) -> str:
        """
        Calculate confidence level based on all three levels.

        Args:
            level1_score: LSH similarity score (0.0-1.0)
            level2_score: Long audio similarity score (0.0-1.0)
            level3_score: Visual similarity rate (0.0-1.0)

        Returns:
            Confidence level: 'high', 'medium', or 'low'
        """
        # High confidence: Excellent on all levels
        if level3_score >= 0.95 and level2_score >= 0.9 and level1_score >= 0.85:
            return 'high'

        # Medium confidence: Good visual + good audio, or perfect visual
        elif level3_score >= 0.95 or (level3_score >= 0.85 and level2_score >= 0.8):
            return 'medium'

        # Low confidence: Passes thresholds but not strong
        else:
            return 'low'
