"""
DCT Coefficients Algorithm.

Compare videos using Discrete Cosine Transform coefficients.
Fast and effective for detecting scenes with similar frequency patterns.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

from duplicateflow.core import register_algorithm
from duplicateflow.sdk import Algorithm
from duplicateflow.algorithms.base import VideoLoader


@register_algorithm(
    name="dct_coefficients",
    display_name="📊 Coefficients DCT",
    short_name="DCT",
    description="Compare les coefficients DCT (fréquences basses)",
    detailed_explanation=(
        "Applique la Transformée en Cosinus Discrète (DCT) sur les frames "
        "et extrait les coefficients de basses fréquences. Ces coefficients "
        "capturent les caractéristiques visuelles principales. Compare via "
        "similarité cosinus pour trouver les scènes les plus similaires."
    ),
    category="statistical",
    speed="fast",
    default_threshold=70.0,
    default_params={
        'threshold': 70.0,
        'num_coeffs': 64,
        'block_size': 8,
        'sample_interval': 5.0,
        'num_samples': None,
        'search_step': 3.0,
        'max_windows': 200,
        'resize': (320, 240)
    },
    use_case="Scènes avec patterns fréquentiels caractéristiques (textures, motifs répétitifs)"
)
class DCTCoefficientsAlgorithm(Algorithm):
    """
    DCT coefficients comparison algorithm.

    Uses Discrete Cosine Transform to extract low-frequency coefficients
    from frames, then compares them using cosine similarity.

    Algorithm steps:
    1. Extract N frames from short video
    2. Compute DCT for each frame
    3. Extract top-left coefficients (low frequencies)
    4. Slide window over long video
    5. Compare DCT signatures using cosine similarity
    6. Return best matching position

    Parameters:
        threshold: Minimum similarity score (0-100)
        num_coeffs: Number of DCT coefficients to extract
        block_size: DCT block size (frame resized to block_size*8)
        sample_interval: Interval between samples (seconds)
        num_samples: Number of frames (None = auto based on duration)
        search_step: Sliding window step (seconds)
        max_windows: Maximum windows to test
        resize: Target frame size before DCT
    """

    def configure(self, **params):
        """Configure algorithm parameters."""
        self.threshold = params.get('threshold', 70.0)
        self.num_coeffs = params.get('num_coeffs', 64)
        self.block_size = params.get('block_size', 8)
        self.sample_interval = params.get('sample_interval', 5.0)
        self.num_samples = params.get('num_samples', None)
        self.search_step = params.get('search_step', 3.0)
        self.max_windows = params.get('max_windows', 200)
        self.resize = params.get('resize', (320, 240))

    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: float = 0.0,
        duration: float = None
    ) -> Dict[str, Any]:
        """
        Compare videos using DCT coefficients.

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

        # Extract DCT signatures from short video
        short_offsets, short_sigs = self._extract_dct_signatures(
            short_video, duration
        )

        if len(short_sigs) < 3:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Insufficient frames for DCT comparison',
                    'num_samples': len(short_sigs)
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
                short_sigs
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
                'num_samples': len(short_sigs),
                'windows_tested': len(window_starts),
                'score_percentage': best_score,
                'num_coeffs': self.num_coeffs
            }
        }

    def _extract_dct_signatures(
        self,
        video_path: str,
        duration: float
    ) -> Tuple[List[float], List[np.ndarray]]:
        """
        Extract DCT signatures from video.

        Args:
            video_path: Path to video
            duration: Duration to analyze

        Returns:
            Tuple of (offsets, dct_signatures)
        """
        # Calculate number of samples
        if self.num_samples is None:
            num_samples = max(5, int(duration / self.sample_interval))
            num_samples = max(3, min(num_samples, 2000))
        else:
            num_samples = max(3, min(self.num_samples, 2000))

        offsets = np.linspace(0, duration, num_samples)
        signatures = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Compute DCT signature
                sig = self._compute_dct_signature(frame)
                if sig is not None:
                    signatures.append(sig)

        return list(offsets), signatures

    def _compute_dct_signature(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Compute DCT signature for a frame.

        Args:
            frame: Input frame (BGR)

        Returns:
            DCT coefficient vector (low frequencies)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Resize to block size
        target_size = self.block_size * 8
        resized = cv2.resize(gray, (target_size, target_size))

        # Compute DCT
        dct = cv2.dct(np.float32(resized))

        # Extract top-left coefficients (low frequencies)
        signature = []
        for i in range(self.block_size):
            for j in range(self.block_size):
                if len(signature) < self.num_coeffs:
                    signature.append(dct[i, j])

        return np.array(signature, dtype=np.float32)

    def _compare_window(
        self,
        long_video: str,
        window_start: float,
        short_offsets: List[float],
        short_sigs: List[np.ndarray]
    ) -> float:
        """
        Compare DCT signatures at a window position.

        Args:
            long_video: Path to long video
            window_start: Window start position
            short_offsets: Sample offsets
            short_sigs: DCT signatures from short video

        Returns:
            Average similarity score (0-100)
        """
        similarities = []

        with VideoLoader(long_video) as loader:
            for offset, short_sig in zip(short_offsets, short_sigs):
                timestamp = window_start + offset

                # Extract frame
                frame = loader.get_frame(timestamp)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Compute DCT signature
                long_sig = self._compute_dct_signature(frame)
                if long_sig is None:
                    continue

                # Compute cosine similarity
                dot_product = np.dot(short_sig, long_sig)
                norm_short = np.linalg.norm(short_sig)
                norm_long = np.linalg.norm(long_sig)

                if norm_short > 0 and norm_long > 0:
                    similarity = dot_product / (norm_short * norm_long)
                    similarities.append(max(0.0, similarity))

        if not similarities:
            return 0.0

        return np.mean(similarities) * 100.0

    def extract_features(self, video_path: str) -> List[np.ndarray]:
        """
        Extract DCT coefficient features from entire video.

        Args:
            video_path: Path to video

        Returns:
            List of DCT coefficient vectors
        """
        with VideoLoader(video_path) as loader:
            duration = loader.duration

        # Calculate number of samples
        if self.num_samples is None:
            num_samples = max(5, int(duration / self.sample_interval))
            num_samples = max(3, min(num_samples, 2000))
        else:
            num_samples = max(3, min(self.num_samples, 2000))

        offsets = np.linspace(0, duration, num_samples)
        signatures = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Compute DCT signature
                sig = self._compute_dct_signature(frame)
                if sig is not None:
                    signatures.append(sig)

        return signatures

    def get_cli_params(self):
        """Return CLI parameters."""
        return [
            {
                'names': ['--dct-num-coeffs'],
                'type': 'int',
                'default': 64,
                'help': 'Number of DCT coefficients to extract'
            },
            {
                'names': ['--dct-block-size'],
                'type': 'int',
                'default': 8,
                'help': 'DCT block size'
            },
            {
                'names': ['--dct-sample-interval'],
                'type': 'float',
                'default': 5.0,
                'help': 'Interval between samples (seconds)'
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
        Compare two sets of DCT coefficient vectors using cosine similarity.

        Args:
            features1: List of DCT signatures from first video
            features2: List of DCT signatures from second video
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
                    'num_sigs_1': len(features1),
                    'num_sigs_2': len(features2)
                }
            }

        # Compare each DCT signature from features1 with each from features2
        similarities = []

        for sig1 in features1:
            for sig2 in features2:
                # Compute cosine similarity
                dot_product = np.dot(sig1, sig2)
                norm1 = np.linalg.norm(sig1)
                norm2 = np.linalg.norm(sig2)

                if norm1 > 0 and norm2 > 0:
                    similarity = dot_product / (norm1 * norm2)
                    similarities.append(max(0.0, similarity * 100.0))

        if not similarities:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'No valid comparisons',
                    'num_sigs_1': len(features1),
                    'num_sigs_2': len(features2)
                }
            }

        # Average similarity
        avg_similarity = float(np.mean(similarities))

        return {
            'similarity': avg_similarity,
            'accepted': avg_similarity >= threshold,
            'metadata': {
                'num_sigs_1': len(features1),
                'num_sigs_2': len(features2),
                'num_comparisons': len(similarities),
                'min_similarity': float(np.min(similarities)),
                'max_similarity': float(np.max(similarities))
            }
        }
