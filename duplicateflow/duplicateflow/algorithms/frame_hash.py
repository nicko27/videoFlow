"""
Frame Hash Algorithm.

Compare videos using perceptual frame hashing (pHash, dHash, aHash).
Fast and effective for detecting visually similar scenes.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

from duplicateflow.core import register_algorithm
from duplicateflow.sdk import Algorithm
from duplicateflow.algorithms.base import VideoLoader


@register_algorithm(
    name="frame_hash",
    display_name="🔐 Frame Hash",
    short_name="pHash",
    description="Compare via hashes perceptuels de frames (pHash/dHash/aHash)",
    detailed_explanation=(
        "Extrait plusieurs frames de la vidéo et calcule leur hash perceptuel "
        "(pHash, dHash ou aHash). Ces hash capturent l'essence visuelle d'une "
        "frame de manière compacte. Compare les hash via distance de Hamming "
        "pour mesurer la similarité."
    ),
    category="perceptual",
    speed="fast",
    default_threshold=80.0,
    default_params={
        'threshold': 80.0,
        'hash_method': 'pHash',
        'num_samples': 8,
        'sample_positions': [1, 5, 10, 20, 30, 50, 70, 100],
        'search_step': 3.0,
        'max_windows': 200
    },
    use_case="Détection rapide de scènes visuellement similaires (avec variations mineures)"
)
class FrameHashAlgorithm(Algorithm):
    """
    Frame hash comparison algorithm.

    Uses perceptual hashing to create compact representations of frames,
    then compares them using Hamming distance.

    Algorithm steps:
    1. Select hash method (pHash, dHash, or aHash)
    2. Extract frames at fixed positions from short video
    3. Compute perceptual hash for each frame
    4. Slide window over long video
    5. For each window, extract and hash frames
    6. Compute Hamming distance between hashes
    7. Return best matching position

    Hash Methods:
        - pHash: Perceptual hash using DCT (most accurate, slower)
        - dHash: Difference hash using gradient (fast, good accuracy)
        - aHash: Average hash (fastest, least accurate)

    Parameters:
        threshold: Minimum similarity score (0-100)
        hash_method: Hash method ('pHash', 'dHash', 'aHash')
        num_samples: Number of frames to sample
        sample_positions: Fixed sample positions (seconds)
        search_step: Sliding window step (seconds)
        max_windows: Maximum windows to test
    """

    def configure(self, **params):
        """Configure algorithm parameters."""
        self.threshold = params.get('threshold', 80.0)
        self.hash_method = params.get('hash_method', 'pHash')
        self.num_samples = params.get('num_samples', 8)
        self.sample_positions = params.get('sample_positions', [1, 5, 10, 20, 30, 50, 70, 100])
        self.search_step = params.get('search_step', 3.0)
        self.max_windows = params.get('max_windows', 200)

    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: float = 0.0,
        duration: float = None
    ) -> Dict[str, Any]:
        """
        Compare videos using frame hashes.

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

        # Extract frame hashes from short video
        short_offsets, short_hashes = self._extract_frame_hashes(
            short_video, duration
        )

        if len(short_hashes) < 2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Insufficient frames for hash comparison',
                    'num_samples': len(short_hashes)
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
                self.search_step,
                searchable / self.max_windows
            ) if self.max_windows else self.search_step
            window_starts = np.arange(start_time, start_time + searchable + 1e-6, step)

        # Sliding window search
        best_score = 0.0
        best_offset = 0.0

        for window_start in window_starts:
            score = self._compare_window(
                long_video,
                window_start,
                short_offsets,
                short_hashes
            )

            if score > best_score:
                best_score = score
                best_offset = window_start

            # Early termination
            if score >= self.threshold + 5:
                break

        similarity = best_score / 100.0

        return {
            'similarity': similarity,
            'accepted': best_score >= self.threshold,
            'metadata': {
                'best_offset_seconds': best_offset,
                'num_samples': len(short_hashes),
                'hash_method': self.hash_method,
                'windows_tested': len(window_starts),
                'score_percentage': best_score
            }
        }

    def extract_features(self, video_path: str) -> List[np.ndarray]:
        """
        Extract perceptual hash features from entire video.

        Args:
            video_path: Path to video

        Returns:
            List of perceptual hashes
        """
        with VideoLoader(video_path) as loader:
            duration = loader.duration

        # Use fixed sample positions or generate uniform samples
        if self.sample_positions:
            # Use fixed positions (limited by duration)
            offsets = [pos for pos in self.sample_positions if pos < duration]
            if len(offsets) < 2:
                # Not enough samples, use uniform distribution
                offsets = list(np.linspace(0, duration, self.num_samples))
        else:
            # Generate uniform samples
            offsets = list(np.linspace(0, duration, self.num_samples))

        hashes = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Compute frame hash
                frame_hash = self._compute_frame_hash(frame)
                if frame_hash is not None:
                    hashes.append(frame_hash)

        return hashes

    def _extract_frame_hashes(
        self,
        video_path: str,
        duration: float
    ) -> Tuple[List[float], List[np.ndarray]]:
        """
        Extract frame hashes from video.

        Args:
            video_path: Path to video
            duration: Duration to analyze

        Returns:
            Tuple of (offsets, frame_hashes)
        """
        # Use fixed sample positions or generate uniform samples
        if self.sample_positions:
            # Use fixed positions (limited by duration)
            offsets = [pos for pos in self.sample_positions if pos < duration]
            if len(offsets) < 2:
                # Not enough samples, use uniform distribution
                offsets = list(np.linspace(0, duration, self.num_samples))
        else:
            # Generate uniform samples
            offsets = list(np.linspace(0, duration, self.num_samples))

        hashes = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Compute frame hash
                frame_hash = self._compute_frame_hash(frame)
                if frame_hash is not None:
                    hashes.append(frame_hash)

        return offsets, hashes

    def _compute_frame_hash(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Compute perceptual hash for a frame.

        Args:
            frame: Input frame (BGR)

        Returns:
            Binary hash array
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if self.hash_method == 'pHash':
                # Perceptual Hash using DCT
                resized = cv2.resize(gray, (32, 32))
                dct = cv2.dct(np.float32(resized))
                dct_low = dct[:8, :8]
                avg = (dct_low[1:, :].mean() + dct_low[0, 1:].mean()) / 2
                return (dct_low > avg).astype(np.uint8)

            elif self.hash_method == 'dHash':
                # Difference Hash
                resized = cv2.resize(gray, (9, 8))
                diff = resized[:, 1:] > resized[:, :-1]
                return diff.astype(np.uint8)

            elif self.hash_method == 'aHash':
                # Average Hash
                resized = cv2.resize(gray, (8, 8))
                avg = resized.mean()
                return (resized > avg).astype(np.uint8)

            else:
                # Default to pHash
                resized = cv2.resize(gray, (32, 32))
                dct = cv2.dct(np.float32(resized))
                dct_low = dct[:8, :8]
                avg = (dct_low[1:, :].mean() + dct_low[0, 1:].mean()) / 2
                return (dct_low > avg).astype(np.uint8)

        except Exception as e:
            return None

    def _compare_window(
        self,
        long_video: str,
        window_start: float,
        short_offsets: List[float],
        short_hashes: List[np.ndarray]
    ) -> float:
        """
        Compare frame hashes at a window position.

        Args:
            long_video: Path to long video
            window_start: Window start position
            short_offsets: Sample offsets
            short_hashes: Frame hashes from short video

        Returns:
            Average similarity score (0-100)
        """
        similarities = []

        with VideoLoader(long_video) as loader:
            for offset, short_hash in zip(short_offsets, short_hashes):
                timestamp = window_start + offset

                # Extract frame
                frame = loader.get_frame(timestamp)
                if frame is None:
                    continue

                # Compute hash
                long_hash = self._compute_frame_hash(frame)
                if long_hash is None:
                    continue

                # Compute Hamming distance
                similarity = self._hamming_similarity(short_hash, long_hash)
                similarities.append(similarity)

        if not similarities:
            return 0.0

        return float(np.mean(similarities))

    def _hamming_similarity(self, hash1: np.ndarray, hash2: np.ndarray) -> float:
        """
        Compute similarity based on Hamming distance.

        Args:
            hash1: First hash
            hash2: Second hash

        Returns:
            Similarity score (0-100)
        """
        # Ensure same shape
        if hash1.shape != hash2.shape:
            return 0.0

        # Compute Hamming distance (number of differing bits)
        distance = np.sum(hash1 != hash2)
        total_bits = hash1.size

        # Convert to similarity percentage
        similarity = (1.0 - distance / total_bits) * 100.0

        return float(similarity)

    def get_cli_params(self):
        """Return CLI parameters."""
        return [
            {
                'names': ['--hash-method'],
                'type': 'str',
                'default': 'pHash',
                'help': 'Hash method (pHash, dHash, aHash)'
            },
            {
                'names': ['--hash-num-samples'],
                'type': 'int',
                'default': 8,
                'help': 'Number of frames to sample'
            },
            {
                'names': ['--hash-sample-positions'],
                'type': 'str',
                'default': '1,5,10,20,30,50,70,100',
                'help': 'Fixed sample positions in seconds (comma-separated)'
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
        features1: List[np.ndarray],
        features2: List[np.ndarray],
        threshold: float,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Compare two sets of perceptual hashes using Hamming distance.

        Args:
            features1: List of hashes from first video
            features2: List of hashes from second video
            threshold: Minimum similarity score (0-100)
            params: Optional parameters (not used)

        Returns:
            Dictionary with similarity, accepted, and metadata
        """
        if not features1 or not features2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Empty feature sets',
                    'num_hashes_1': len(features1),
                    'num_hashes_2': len(features2)
                }
            }

        # Compare each hash from features1 with each from features2
        similarities = []

        for hash1 in features1:
            for hash2 in features2:
                # Ensure same shape
                if hash1.shape != hash2.shape:
                    continue

                # Compute Hamming distance (number of differing bits)
                distance = np.sum(hash1 != hash2)
                total_bits = hash1.size

                # Convert to similarity percentage
                similarity = (1.0 - distance / total_bits) * 100.0
                similarities.append(float(similarity))

        if not similarities:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'No valid comparisons',
                    'num_hashes_1': len(features1),
                    'num_hashes_2': len(features2)
                }
            }

        # Average similarity
        avg_similarity = float(np.mean(similarities))

        return {
            'similarity': avg_similarity,
            'accepted': avg_similarity >= threshold,
            'metadata': {
                'num_hashes_1': len(features1),
                'num_hashes_2': len(features2),
                'num_comparisons': len(similarities),
                'min_similarity': float(np.min(similarities)),
                'max_similarity': float(np.max(similarities))
            }
        }
