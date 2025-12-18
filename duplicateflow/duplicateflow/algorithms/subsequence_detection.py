"""
Subsequence Detection Algorithm.

Detects if a short video is an extracted scene from a longer video.
Uses multiple methods (frame hash + motion analysis) with sliding window.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

from duplicateflow.core import register_algorithm
from duplicateflow.sdk import Algorithm
from duplicateflow.algorithms.base import VideoLoader


@register_algorithm(
    name="subsequence_detection",
    display_name="🎬 Détection Sous-Séquence",
    short_name="Subsequence",
    description="Détecte si une vidéo courte est extraite d'une longue",
    detailed_explanation=(
        "Combine plusieurs méthodes (hash de frames + analyse de mouvement) "
        "pour détecter si la vidéo courte est une sous-séquence de la longue. "
        "Extrait des signatures du début, milieu et fin de la vidéo courte, "
        "puis cherche ces signatures dans la vidéo longue avec fenêtre glissante."
    ),
    category="hybrid",
    speed="slow",
    default_threshold=70.0,
    default_params={
        'threshold': 70.0,
        'window_step': 5.0,
        'max_windows': 500,
        'signature_points': 3,
        'hash_method': 'pHash',
        'motion_weight': 0.4,
        'hash_weight': 0.6
    },
    use_case="Détection précise d'extraits de scènes (20min-1h) dans longues vidéos"
)
class SubsequenceDetectionAlgorithm(Algorithm):
    """
    Subsequence detection algorithm.

    Combines frame hashing and motion analysis to detect if short video
    is an extracted scene from long video.

    Algorithm steps:
    1. Extract N signature points from short video (start, middle, end)
    2. For each signature point, compute:
       - Perceptual frame hash
       - Motion pattern (frame differences)
    3. Slide window through long video
    4. At each position, extract and compare signatures
    5. Combine hash similarity and motion similarity
    6. Return best matching position

    Parameters:
        threshold: Minimum similarity score (0-100)
        window_step: Sliding window step (seconds)
        max_windows: Maximum windows to test
        signature_points: Number of signature points to extract
        hash_method: Hash method for frames ('pHash', 'dHash', 'aHash')
        motion_weight: Weight for motion similarity (0-1)
        hash_weight: Weight for hash similarity (0-1)
    """

    def configure(self, **params):
        """Configure algorithm parameters."""
        self.threshold = params.get('threshold', 70.0)
        self.window_step = params.get('window_step', 5.0)
        self.max_windows = params.get('max_windows', 500)
        self.signature_points = params.get('signature_points', 3)
        self.hash_method = params.get('hash_method', 'pHash')
        self.motion_weight = params.get('motion_weight', 0.4)
        self.hash_weight = params.get('hash_weight', 0.6)

        # Normalize weights
        total_weight = self.motion_weight + self.hash_weight
        if total_weight > 0:
            self.motion_weight /= total_weight
            self.hash_weight /= total_weight

    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: float = 0.0,
        duration: float = None
    ) -> Dict[str, Any]:
        """
        Compare videos using subsequence detection.

        Args:
            short_video: Path to short video
            long_video: Path to long video
            start_time: Start position in long video
            duration: Duration to analyze

        Returns:
            Dictionary with similarity, accepted, metadata
        """
        # Validate inputs
        self._validate_video_path(short_video)
        self._validate_video_path(long_video)

        # Get duration from short video if not provided
        if duration is None:
            with VideoLoader(short_video) as loader:
                duration = loader.duration

        self._validate_time_params(start_time, duration)

        # Extract signatures from short video
        signatures = self._extract_signatures(short_video, duration)

        if len(signatures) < 2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Insufficient signature points',
                    'num_signatures': len(signatures)
                }
            }

        # Get long video duration
        with VideoLoader(long_video) as loader:
            long_duration = loader.duration

        # Calculate window positions
        searchable = max(long_duration - duration, 0)

        if searchable <= 0:
            window_starts = [start_time]
        else:
            step = max(
                self.window_step,
                searchable / self.max_windows
            ) if self.max_windows else self.window_step
            window_starts = np.arange(start_time, start_time + searchable + 1e-6, step)

        # Sliding window search
        best_score = 0.0
        best_offset = 0.0
        best_hash_score = 0.0
        best_motion_score = 0.0

        for window_start in window_starts:
            hash_score, motion_score = self._compare_window(
                long_video,
                window_start,
                signatures
            )

            # Weighted combination
            combined_score = (
                self.hash_weight * hash_score +
                self.motion_weight * motion_score
            )

            if combined_score > best_score:
                best_score = combined_score
                best_offset = window_start
                best_hash_score = hash_score
                best_motion_score = motion_score

            # Early termination
            if combined_score >= self.threshold + 5:
                break

        similarity = best_score / 100.0

        # Determine confidence
        if best_score >= 85:
            confidence = 'high'
        elif best_score >= 70:
            confidence = 'medium'
        elif best_score >= self.threshold:
            confidence = 'low'
        else:
            confidence = 'none'

        return {
            'similarity': similarity,
            'accepted': best_score >= self.threshold,
            'metadata': {
                'best_offset_seconds': best_offset,
                'num_signatures': len(signatures),
                'hash_score': best_hash_score,
                'motion_score': best_motion_score,
                'combined_score': best_score,
                'confidence': confidence,
                'windows_tested': len(window_starts)
            }
        }

    def _extract_signatures(
        self,
        video_path: str,
        duration: float
    ) -> List[Tuple[float, np.ndarray, np.ndarray]]:
        """
        Extract signature points from video.

        Args:
            video_path: Path to video
            duration: Duration to analyze

        Returns:
            List of (offset, frame_hash, motion_pattern)
        """
        # Calculate signature positions
        if self.signature_points <= 1:
            offsets = [duration / 2]
        else:
            offsets = [i * duration / (self.signature_points - 1) for i in range(self.signature_points)]

        signatures = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                # Extract frame for hash
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Compute frame hash
                frame_hash = self._compute_frame_hash(frame)
                if frame_hash is None:
                    continue

                # Extract motion pattern around this point
                motion_pattern = self._extract_motion_pattern(
                    loader, offset, duration
                )

                if motion_pattern is not None:
                    signatures.append((offset, frame_hash, motion_pattern))

        return signatures

    def _compute_frame_hash(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Compute perceptual hash for a frame.

        Args:
            frame: Input frame (BGR)

        Returns:
            Binary hash array
        """
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if self.hash_method == 'pHash':
                resized = cv2.resize(gray, (32, 32))
                dct = cv2.dct(np.float32(resized))
                dct_low = dct[:8, :8]
                avg = (dct_low[1:, :].mean() + dct_low[0, 1:].mean()) / 2
                return (dct_low > avg).astype(np.uint8)

            elif self.hash_method == 'dHash':
                resized = cv2.resize(gray, (9, 8))
                diff = resized[:, 1:] > resized[:, :-1]
                return diff.astype(np.uint8)

            else:  # aHash
                resized = cv2.resize(gray, (8, 8))
                avg = resized.mean()
                return (resized > avg).astype(np.uint8)

        except Exception:
            return None

    def _extract_motion_pattern(
        self,
        loader: VideoLoader,
        offset: float,
        duration: float
    ) -> Optional[np.ndarray]:
        """
        Extract motion pattern around a time point.

        Args:
            loader: VideoLoader instance
            offset: Time offset
            duration: Total duration

        Returns:
            Motion pattern vector
        """
        # Extract 5 frames around this offset
        num_frames = 5
        window = 2.0  # +/- 2 seconds

        start = max(0, offset - window)
        end = min(duration, offset + window)

        frame_offsets = np.linspace(start, end, num_frames)

        frames = []
        for frame_offset in frame_offsets:
            frame = loader.get_frame(frame_offset)
            if frame is None:
                continue

            # Resize for efficiency
            frame = cv2.resize(frame, (160, 120))
            frames.append(frame)

        if len(frames) < 3:
            return None

        # Compute frame-to-frame differences
        diffs = []
        for i in range(len(frames) - 1):
            gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray1, gray2)
            diffs.append(np.mean(diff))

        return np.array(diffs, dtype=np.float32)

    def _compare_window(
        self,
        long_video: str,
        window_start: float,
        signatures: List[Tuple[float, np.ndarray, np.ndarray]]
    ) -> Tuple[float, float]:
        """
        Compare signatures at a window position.

        Args:
            long_video: Path to long video
            window_start: Window start position
            signatures: Signatures from short video

        Returns:
            Tuple of (hash_score, motion_score)
        """
        hash_similarities = []
        motion_similarities = []

        with VideoLoader(long_video) as loader:
            for offset, short_hash, short_motion in signatures:
                timestamp = window_start + offset

                # Extract frame
                frame = loader.get_frame(timestamp)
                if frame is None:
                    continue

                # Compare hash
                long_hash = self._compute_frame_hash(frame)
                if long_hash is not None:
                    hash_sim = self._hamming_similarity(short_hash, long_hash)
                    hash_similarities.append(hash_sim)

                # Extract and compare motion
                long_motion = self._extract_motion_pattern(
                    loader, timestamp, loader.duration
                )
                if long_motion is not None and len(long_motion) == len(short_motion):
                    motion_sim = self._motion_similarity(short_motion, long_motion)
                    motion_similarities.append(motion_sim)

        hash_score = float(np.mean(hash_similarities)) if hash_similarities else 0.0
        motion_score = float(np.mean(motion_similarities)) if motion_similarities else 0.0

        return hash_score, motion_score

    def _hamming_similarity(self, hash1: np.ndarray, hash2: np.ndarray) -> float:
        """
        Compute Hamming similarity between hashes.

        Args:
            hash1: First hash
            hash2: Second hash

        Returns:
            Similarity (0-100)
        """
        if hash1.shape != hash2.shape:
            return 0.0

        distance = np.sum(hash1 != hash2)
        total_bits = hash1.size
        similarity = (1.0 - distance / total_bits) * 100.0

        return float(similarity)

    def _motion_similarity(self, motion1: np.ndarray, motion2: np.ndarray) -> float:
        """
        Compute motion pattern similarity.

        Args:
            motion1: First motion pattern
            motion2: Second motion pattern

        Returns:
            Similarity (0-100)
        """
        # Normalize patterns
        std1 = motion1.std()
        std2 = motion2.std()

        if std1 < 1e-6 or std2 < 1e-6:
            # Static scenes
            return 100.0

        norm1 = (motion1 - motion1.mean()) / std1
        norm2 = (motion2 - motion2.mean()) / std2

        # Compute correlation
        correlation = np.corrcoef(norm1, norm2)[0, 1]

        if np.isnan(correlation):
            return 0.0

        similarity = max(0.0, min(100.0, correlation * 100.0))
        return float(similarity)

    def extract_features(self, video_path: str) -> List[Tuple[float, np.ndarray, np.ndarray]]:
        """
        Extract signature features from entire video.

        Args:
            video_path: Path to video

        Returns:
            List of (offset, frame_hash, motion_pattern) tuples
        """
        with VideoLoader(video_path) as loader:
            duration = loader.duration

        # Extract signatures from entire video
        signatures = self._extract_signatures(video_path, duration)

        return signatures

    def get_cli_params(self):
        """Return CLI parameters."""
        return [
            {
                'names': ['--subseq-signature-points'],
                'type': 'int',
                'default': 3,
                'help': 'Number of signature points (start, middle, end)'
            },
            {
                'names': ['--subseq-hash-method'],
                'type': 'str',
                'default': 'pHash',
                'help': 'Hash method (pHash, dHash, aHash)'
            },
            {
                'names': ['--subseq-motion-weight'],
                'type': 'float',
                'default': 0.4,
                'help': 'Weight for motion similarity (0-1)'
            },
            {
                'names': ['--subseq-hash-weight'],
                'type': 'float',
                'default': 0.6,
                'help': 'Weight for hash similarity (0-1)'
            }
        ]

    def get_requirements(self):
        """Return package requirements."""
        return [
            'opencv-python>=4.8.0',
            'numpy>=1.24.0'
        ]

    @staticmethod
    def compare_features(
        features1: List[Tuple[float, np.ndarray, np.ndarray]],
        features2: List[Tuple[float, np.ndarray, np.ndarray]],
        threshold: float,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Compare two sets of signature features (hash + motion).

        Args:
            features1: List of (offset, hash, motion) from first video
            features2: List of (offset, hash, motion) from second video
            threshold: Minimum similarity score (0-100)
            params: Optional parameters (motion_weight, hash_weight)

        Returns:
            Dictionary with similarity, accepted, and metadata
        """
        if not features1 or not features2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Empty feature sets',
                    'num_sigs_1': len(features1),
                    'num_sigs_2': len(features2)
                }
            }

        # Get weights
        motion_weight = params.get('motion_weight', 0.4) if params else 0.4
        hash_weight = params.get('hash_weight', 0.6) if params else 0.6

        # Normalize weights
        total_weight = motion_weight + hash_weight
        if total_weight > 0:
            motion_weight /= total_weight
            hash_weight /= total_weight

        # Compare signatures
        hash_similarities = []
        motion_similarities = []

        for _, hash1, motion1 in features1:
            for _, hash2, motion2 in features2:
                # Compare hashes
                if hash1.shape == hash2.shape:
                    distance = np.sum(hash1 != hash2)
                    total_bits = hash1.size
                    hash_sim = (1.0 - distance / total_bits) * 100.0
                    hash_similarities.append(float(hash_sim))

                # Compare motion patterns
                if len(motion1) == len(motion2):
                    std1 = motion1.std()
                    std2 = motion2.std()

                    if std1 < 1e-6 or std2 < 1e-6:
                        # Static scenes
                        motion_sim = 100.0
                    else:
                        # Normalize and correlate
                        norm1 = (motion1 - motion1.mean()) / std1
                        norm2 = (motion2 - motion2.mean()) / std2
                        correlation = np.corrcoef(norm1, norm2)[0, 1]

                        if np.isnan(correlation):
                            motion_sim = 0.0
                        else:
                            motion_sim = max(0.0, min(100.0, correlation * 100.0))

                    motion_similarities.append(float(motion_sim))

        if not hash_similarities and not motion_similarities:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'No valid comparisons',
                    'num_sigs_1': len(features1),
                    'num_sigs_2': len(features2)
                }
            }

        # Calculate weighted average
        hash_score = float(np.mean(hash_similarities)) if hash_similarities else 0.0
        motion_score = float(np.mean(motion_similarities)) if motion_similarities else 0.0

        combined_score = hash_weight * hash_score + motion_weight * motion_score

        # Determine confidence
        if combined_score >= 85:
            confidence = 'high'
        elif combined_score >= 70:
            confidence = 'medium'
        elif combined_score >= threshold:
            confidence = 'low'
        else:
            confidence = 'none'

        return {
            'similarity': combined_score,
            'accepted': combined_score >= threshold,
            'metadata': {
                'num_sigs_1': len(features1),
                'num_sigs_2': len(features2),
                'hash_score': hash_score,
                'motion_score': motion_score,
                'combined_score': combined_score,
                'confidence': confidence,
                'num_hash_comparisons': len(hash_similarities),
                'num_motion_comparisons': len(motion_similarities)
            }
        }
