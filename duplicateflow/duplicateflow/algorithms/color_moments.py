"""
Color Moments Algorithm.

Compare color distributions using statistical moments (mean, std, skewness).
Fast and effective for scenes with characteristic color distributions.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple

from duplicateflow.core import register_algorithm
from duplicateflow.sdk import Algorithm
from duplicateflow.algorithms.base import VideoLoader


@register_algorithm(
    name="color_moments",
    display_name="📐 Moments Couleur",
    short_name="Color Moments",
    description="Compare les distributions couleur via moments statistiques",
    detailed_explanation=(
        "Calcule les moments statistiques (moyenne, écart-type, skewness) "
        "pour chaque canal couleur (H, S, V). Ces moments capturent la "
        "distribution globale des couleurs. Plus rapide que les histogrammes "
        "car il ne nécessite que 9 valeurs (3 moments × 3 canaux)."
    ),
    category="statistical",
    speed="fast",
    default_threshold=75.0,
    default_params={
        'threshold': 75.0,
        'num_samples': 5,
        'search_step': 3.0,
        'max_windows': 200,
        'resize': (320, 240)
    },
    use_case="Scènes avec distributions couleur caractéristiques (rapide, léger)"
)
class ColorMomentsAlgorithm(Algorithm):
    """
    Color moments comparison algorithm.

    Uses statistical moments (mean, standard deviation, skewness) of
    color channels to create compact color signatures.

    Algorithm steps:
    1. Extract N frames from short video
    2. Convert to HSV
    3. Compute 3 moments for each of 3 channels (9 values total)
    4. Slide window over long video
    5. Compare moment vectors using Euclidean distance

    Parameters:
        threshold: Minimum similarity score (0-100)
        num_samples: Number of frames to sample
        search_step: Sliding window step (seconds)
        max_windows: Maximum windows to test
        resize: Target frame size
    """

    def configure(self, **params):
        """Configure algorithm parameters."""
        self.threshold = params.get('threshold', 75.0)
        self.num_samples = params.get('num_samples', 5)
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
        Compare videos using color moments.

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

        # Get duration
        if duration is None:
            with VideoLoader(short_video) as loader:
                duration = loader.duration

        self._validate_time_params(start_time, duration)

        # Extract color moments from short video
        short_offsets, short_moments = self._extract_color_moments(
            short_video, duration
        )

        if len(short_moments) < 2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Insufficient frames for color moments',
                    'num_samples': len(short_moments)
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
                short_moments
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
                'num_samples': len(short_moments),
                'windows_tested': len(window_starts),
                'score_percentage': best_score
            }
        }

    def extract_features(self, video_path: str) -> List[np.ndarray]:
        """
        Extract color moment features from entire video.

        Args:
            video_path: Path to video

        Returns:
            List of color moment vectors (9D each)
        """
        with VideoLoader(video_path) as loader:
            duration = loader.duration

        sample_interval = max(1.0, duration / self.num_samples)
        offsets = [i * sample_interval for i in range(self.num_samples)]

        moments_list = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Compute color moments
                moments = self._compute_moments(frame)
                if moments is not None:
                    moments_list.append(moments)

        return moments_list

    def _extract_color_moments(
        self,
        video_path: str,
        duration: float
    ) -> Tuple[List[float], List[np.ndarray]]:
        """
        Extract color moments from video.

        Args:
            video_path: Path to video
            duration: Duration to analyze

        Returns:
            Tuple of (offsets, color_moments)
        """
        sample_interval = max(1.0, duration / self.num_samples)
        offsets = [i * sample_interval for i in range(self.num_samples)]

        moments_list = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Compute color moments
                moments = self._compute_moments(frame)
                if moments is not None:
                    moments_list.append(moments)

        return offsets, moments_list

    def _compute_moments(self, frame: np.ndarray) -> np.ndarray:
        """
        Compute color moments for a frame.

        Args:
            frame: Input frame (BGR)

        Returns:
            9D moment vector: [H_mean, H_std, H_skew, S_mean, S_std, S_skew, V_mean, V_std, V_skew]
        """
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        moments = []

        # For each channel (H, S, V)
        for channel in range(3):
            channel_data = hsv[:, :, channel].flatten().astype(np.float32)

            # Moment 1: Mean
            mean = np.mean(channel_data)

            # Moment 2: Standard deviation
            std = np.std(channel_data)

            # Moment 3: Skewness
            if std > 0:
                skewness = np.mean(((channel_data - mean) / std) ** 3)
            else:
                skewness = 0.0

            moments.extend([mean, std, skewness])

        return np.array(moments, dtype=np.float32)

    def _compare_window(
        self,
        long_video: str,
        window_start: float,
        short_offsets: List[float],
        short_moments: List[np.ndarray]
    ) -> float:
        """
        Compare color moments at a window position.

        Args:
            long_video: Path to long video
            window_start: Window start position
            short_offsets: Sample offsets
            short_moments: Color moments from short video

        Returns:
            Average similarity score (0-100)
        """
        similarities = []

        with VideoLoader(long_video) as loader:
            for offset, short_moment in zip(short_offsets, short_moments):
                timestamp = window_start + offset

                # Extract frame
                frame = loader.get_frame(timestamp)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Compute moments
                long_moment = self._compute_moments(frame)
                if long_moment is None:
                    continue

                # Compute similarity using inverse Euclidean distance
                # Normalize each dimension first
                normalized_short = short_moment / (np.abs(short_moment) + 1e-6)
                normalized_long = long_moment / (np.abs(long_moment) + 1e-6)

                distance = np.linalg.norm(normalized_short - normalized_long)

                # Convert distance to similarity (0 distance = 100% similarity)
                # Max expected distance is ~sqrt(9*4) = 6 for normalized values
                max_distance = 6.0
                similarity = max(0.0, 100.0 * (1.0 - min(distance / max_distance, 1.0)))

                similarities.append(similarity)

        if not similarities:
            return 0.0

        return float(np.mean(similarities))

    def get_cli_params(self):
        """Return CLI parameters."""
        return [
            {
                'names': ['--moments-num-samples'],
                'type': 'int',
                'default': 5,
                'help': 'Number of frames to sample'
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
        Compare two sets of color moment vectors.

        Args:
            features1: List of moment vectors from first video
            features2: List of moment vectors from second video
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
                    'num_moments_1': len(features1),
                    'num_moments_2': len(features2)
                }
            }

        # Compare each moment vector from features1 with each from features2
        similarities = []

        for moment1 in features1:
            for moment2 in features2:
                # Normalize vectors
                norm1 = moment1 / (np.abs(moment1) + 1e-6)
                norm2 = moment2 / (np.abs(moment2) + 1e-6)

                # Euclidean distance
                distance = np.linalg.norm(norm1 - norm2)

                # Convert to similarity (0 distance = 100%)
                max_distance = 6.0  # Max expected distance for normalized 9D vectors
                similarity = max(0.0, 100.0 * (1.0 - min(distance / max_distance, 1.0)))

                similarities.append(similarity)

        if not similarities:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'No valid comparisons',
                    'num_moments_1': len(features1),
                    'num_moments_2': len(features2)
                }
            }

        # Average similarity
        avg_similarity = float(np.mean(similarities))

        return {
            'similarity': avg_similarity,
            'accepted': avg_similarity >= threshold,
            'metadata': {
                'num_moments_1': len(features1),
                'num_moments_2': len(features2),
                'num_comparisons': len(similarities),
                'min_similarity': float(np.min(similarities)),
                'max_similarity': float(np.max(similarities))
            }
        }
