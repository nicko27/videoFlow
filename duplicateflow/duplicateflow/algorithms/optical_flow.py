"""
Optical Flow Algorithm.

Compare motion patterns using dense optical flow (Farneback).
Effective for detecting scenes with complex motion characteristics.
"""

import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple

from duplicateflow.core import register_algorithm
from duplicateflow.sdk import Algorithm
from duplicateflow.algorithms.base import VideoLoader


@register_algorithm(
    name="optical_flow",
    display_name="🌊 Flux Optique",
    short_name="Optical Flow",
    description="Compare les patterns de mouvement via flux optique dense",
    detailed_explanation=(
        "Utilise l'algorithme de Farneback pour calculer le flux optique dense "
        "entre frames successives. Extrait magnitude moyenne et variance du flux "
        "pour créer une signature de mouvement. Cherche la position dans la vidéo "
        "longue avec le flux optique le plus similaire."
    ),
    category="temporal",
    speed="slow",
    default_threshold=70.0,
    default_params={
        'threshold': 70.0,
        'max_frames': 20,
        'frame_step': 3,
        'search_step': 3.0,
        'max_windows': 200,
        'min_variance': 0.0
    },
    use_case="Scènes avec mouvements complexes (caméra mobile, foules, effets visuels)"
)
class OpticalFlowAlgorithm(Algorithm):
    """
    Optical flow comparison algorithm.

    Uses Farneback dense optical flow to compute motion patterns,
    then compares magnitude statistics to find matching scenes.

    Algorithm steps:
    1. Extract frames from short video
    2. Compute dense optical flow between consecutive frames
    3. Calculate magnitude mean and variance
    4. Slide window over long video
    5. Compare optical flow statistics
    6. Return best matching position

    Parameters:
        threshold: Minimum similarity score (0-100)
        max_frames: Maximum frames to process
        frame_step: Step between frames
        search_step: Sliding window step (seconds)
        max_windows: Maximum windows to test
        min_variance: Minimum variance for static detection
    """

    def configure(self, **params):
        """Configure algorithm parameters."""
        self.threshold = params.get('threshold', 70.0)
        self.max_frames = params.get('max_frames', 20)
        self.frame_step = params.get('frame_step', 3)
        self.search_step = params.get('search_step', 3.0)
        self.max_windows = params.get('max_windows', 200)
        self.min_variance = params.get('min_variance', 0.0)

    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: float = 0.0,
        duration: float = None
    ) -> Dict[str, Any]:
        """
        Compare videos using optical flow.

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

        # Compute optical flow signature from short video
        mag1, var1 = self._compute_flow_magnitude(short_video, duration)

        if mag1 is None:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Failed to compute optical flow',
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
            # Compute optical flow for this window
            mag2, var2 = self._compute_flow_magnitude(
                long_video, duration, start_time=window_start
            )

            if mag2 is None:
                continue

            # Handle static scenes (low variance)
            if var1 is None or var2 is None or var1 <= self.min_variance or var2 <= self.min_variance:
                score = 100.0
            else:
                # Compare magnitudes
                diff = abs(mag1 - mag2)
                denom = max(mag1, mag2, 1e-6)
                score = max(0.0, 100.0 - (diff / denom * 100.0))

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
                'short_magnitude': float(mag1) if mag1 is not None else None,
                'short_variance': float(var1) if var1 is not None else None,
                'windows_tested': len(window_starts),
                'score_percentage': best_score
            }
        }

    def _compute_flow_magnitude(
        self,
        video_path: str,
        duration: float,
        start_time: float = 0.0
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Compute optical flow magnitude statistics.

        Args:
            video_path: Path to video
            duration: Duration to analyze
            start_time: Start position

        Returns:
            Tuple of (mean_magnitude, variance_magnitude)
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None, None

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 25.0

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 1:
            cap.release()
            return None, None

        # Calculate frame range
        start_frame = int(start_time * fps)
        end_frame = int((start_time + duration) * fps)
        end_frame = min(end_frame, total_frames - 1)

        if end_frame <= start_frame:
            cap.release()
            return None, None

        # Sample frames
        indices = list(range(
            start_frame,
            min(end_frame, start_frame + self.max_frames * self.frame_step),
            self.frame_step
        ))

        prev_gray = None
        magnitudes = []

        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()

            if not ret or frame is None:
                continue

            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if prev_gray is None:
                prev_gray = gray
                continue

            # Compute dense optical flow (Farneback)
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, gray, None,
                pyr_scale=0.5,
                levels=3,
                winsize=15,
                iterations=3,
                poly_n=5,
                poly_sigma=1.2,
                flags=0
            )

            # Convert to magnitude
            mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            magnitudes.append(float(np.mean(mag)))

            prev_gray = gray

        cap.release()

        if not magnitudes:
            return None, None

        return float(np.mean(magnitudes)), float(np.var(magnitudes))

    def extract_features(self, video_path: str) -> Tuple[float, float]:
        """
        Extract optical flow magnitude statistics from entire video.

        Args:
            video_path: Path to video

        Returns:
            Tuple of (mean_magnitude, variance_magnitude)
        """
        with VideoLoader(video_path) as loader:
            duration = loader.duration

        # Compute optical flow for entire video
        mag, var = self._compute_flow_magnitude(video_path, duration, start_time=0.0)

        if mag is None or var is None:
            return (0.0, 0.0)

        return (mag, var)

    def get_cli_params(self):
        """Return CLI parameters."""
        return [
            {
                'names': ['--optflow-max-frames'],
                'type': 'int',
                'default': 20,
                'help': 'Maximum frames to process'
            },
            {
                'names': ['--optflow-frame-step'],
                'type': 'int',
                'default': 3,
                'help': 'Step between frames'
            },
            {
                'names': ['--optflow-search-step'],
                'type': 'float',
                'default': 3.0,
                'help': 'Sliding window step size (seconds)'
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
        features1: Tuple[float, float],
        features2: Tuple[float, float],
        threshold: float,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Compare two optical flow magnitude tuples.

        Args:
            features1: (magnitude, variance) from first video
            features2: (magnitude, variance) from second video
            threshold: Minimum similarity score (0-100)
            params: Optional parameters (min_variance)

        Returns:
            Dictionary with similarity, accepted, and metadata
        """
        if features1 is None or features2 is None:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Empty feature sets'
                }
            }

        mag1, var1 = features1
        mag2, var2 = features2

        # Get min_variance parameter
        min_variance = params.get('min_variance', 0.0) if params else 0.0

        # Handle static scenes (low variance)
        if var1 <= min_variance or var2 <= min_variance:
            # Both static scenes - perfect match
            similarity = 100.0
        else:
            # Compare magnitudes
            diff = abs(mag1 - mag2)
            denom = max(mag1, mag2, 1e-6)
            similarity = max(0.0, 100.0 - (diff / denom * 100.0))

        return {
            'similarity': similarity,
            'accepted': similarity >= threshold,
            'metadata': {
                'magnitude_1': float(mag1),
                'magnitude_2': float(mag2),
                'variance_1': float(var1),
                'variance_2': float(var2),
                'static_1': var1 <= min_variance,
                'static_2': var2 <= min_variance
            }
        }
