"""
Motion Analysis Algorithm.

Compare motion patterns using frame-to-frame differences with correlation analysis.
Effective for detecting scenes with characteristic motion patterns.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Optional

from duplicateflow.core import register_algorithm
from duplicateflow.sdk import Algorithm
from duplicateflow.algorithms.base import VideoLoader


@register_algorithm(
    name="motion_analysis",
    display_name="🏃 Analyse de Mouvement",
    short_name="Motion",
    description="Compare les patterns de mouvement via différences successives",
    detailed_explanation=(
        "Extrait plusieurs frames de la vidéo courte, calcule les différences "
        "frame-à-frame (absdiff), puis utilise la corrélation pour trouver "
        "le pattern de mouvement le plus similaire dans la vidéo longue. "
        "Efficace pour détecter des scènes avec des motifs de mouvement caractéristiques."
    ),
    category="temporal",
    speed="medium",
    default_threshold=70.0,
    default_params={
        'threshold': 70.0,
        'sample_interval': 3.0,
        'search_step': 3.0,
        'max_windows': 200,
        'min_variance': 0.0,
        'resize': (320, 240)
    },
    use_case="Scènes avec patterns de mouvement caractéristiques (sports, action, déplacements)"
)
class MotionAnalysisAlgorithm(Algorithm):
    """
    Motion analysis comparison algorithm.

    Uses frame-to-frame differences to capture motion patterns, then
    correlates them to find matching scenes.

    Algorithm steps:
    1. Extract N frames from short video at uniform intervals
    2. Compute frame-to-frame differences (grayscale absdiff)
    3. Create motion signature vector from mean differences
    4. Slide window over long video
    5. Compute correlation between motion signatures
    6. Return best correlation score

    Parameters:
        threshold: Minimum correlation score (0-100)
        sample_interval: Interval between samples (seconds)
        search_step: Sliding window step (seconds)
        max_windows: Maximum windows to test
        min_variance: Minimum variance threshold (static scene detection)
        resize: Target frame size for processing
    """

    def configure(self, **params):
        """Configure algorithm parameters."""
        self.threshold = params.get('threshold', 70.0)
        self.sample_interval = params.get('sample_interval', 3.0)
        self.search_step = params.get('search_step', 3.0)
        self.max_windows = params.get('max_windows', 200)
        self.min_variance = params.get('min_variance', 0.0)
        self.resize = params.get('resize', (320, 240))

    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: float = 0.0,
        duration: float = None
    ) -> Dict[str, Any]:
        """
        Compare videos using motion analysis.

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

        # Compute motion signature from short video
        short_motion = self._compute_motion_signature(short_video, duration)

        if short_motion is None or len(short_motion) < 2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Failed to compute motion signature',
                    'num_samples': 0 if short_motion is None else len(short_motion)
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

        # Pre-normalize short motion for correlation
        short_std = short_motion.std()
        if short_std > self.min_variance:
            short_norm = (short_motion - short_motion.mean()) / short_std
        else:
            # Static scene - will match any static scene
            short_norm = None

        # Sliding window search
        best_score = 0.0
        best_offset = 0.0

        for window_start in window_starts:
            # Compute motion signature for this window
            long_motion = self._compute_motion_signature(
                long_video, duration, start_time=window_start
            )

            if long_motion is None:
                continue

            # Handle static scenes
            if short_norm is None or long_motion.std() <= self.min_variance:
                score = 100.0
            else:
                # Normalize and compute correlation
                long_norm = (long_motion - long_motion.mean()) / long_motion.std()

                # Make sure arrays have same length for correlation
                min_len = min(len(short_norm), len(long_norm))
                short_norm_slice = short_norm[:min_len]
                long_norm_slice = long_norm[:min_len]

                if min_len < 2:
                    score = 0.0
                else:
                    correlation = np.corrcoef(short_norm_slice, long_norm_slice)[0, 1]

                    # Handle NaN correlation
                    if np.isnan(correlation):
                        score = 0.0
                    else:
                        score = max(0.0, min(100.0, correlation * 100.0))

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
                'motion_samples': len(short_motion),
                'windows_tested': len(window_starts),
                'score_percentage': best_score,
                'static_scene': short_norm is None
            }
        }

    def _compute_motion_signature(
        self,
        video_path: str,
        duration: float,
        start_time: float = 0.0
    ) -> Optional[np.ndarray]:
        """
        Compute motion signature from video.

        Args:
            video_path: Path to video
            duration: Duration to analyze
            start_time: Start position

        Returns:
            Motion signature vector (frame differences)
        """
        # Calculate number of samples
        num_samples = max(5, int(duration / self.sample_interval))

        # Extract frames at uniform intervals
        frames = []
        with VideoLoader(video_path) as loader:
            for i in range(num_samples):
                offset = (i / (num_samples - 1)) * duration if num_samples > 1 else duration / 2
                timestamp = start_time + offset

                frame = loader.get_frame(timestamp)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                frames.append(frame)

        # Need at least 3 frames to compute differences
        if len(frames) < 3:
            return None

        # Compute frame-to-frame differences
        diffs = []
        for i in range(len(frames) - 1):
            gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)

            # Compute absolute difference
            diff = cv2.absdiff(gray1, gray2)
            diffs.append(np.mean(diff))

        return np.array(diffs, dtype=np.float32)

    def extract_features(self, video_path: str) -> np.ndarray:
        """
        Extract motion signature features from entire video.

        Args:
            video_path: Path to video

        Returns:
            Motion signature vector (frame-to-frame differences)
        """
        with VideoLoader(video_path) as loader:
            duration = loader.duration

        # Compute motion signature for entire video
        motion_signature = self._compute_motion_signature(video_path, duration, start_time=0.0)

        if motion_signature is None:
            return np.array([], dtype=np.float32)

        return motion_signature

    def get_cli_params(self):
        """Return CLI parameters."""
        return [
            {
                'names': ['--motion-sample-interval'],
                'type': 'float',
                'default': 3.0,
                'help': 'Interval between motion samples (seconds)'
            },
            {
                'names': ['--motion-search-step'],
                'type': 'float',
                'default': 3.0,
                'help': 'Sliding window step size (seconds)'
            },
            {
                'names': ['--motion-min-variance'],
                'type': 'float',
                'default': 0.0,
                'help': 'Minimum variance for static scene detection'
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
        features1: np.ndarray,
        features2: np.ndarray,
        threshold: float,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Compare two motion signature vectors using correlation.

        Args:
            features1: Motion signature from first video
            features2: Motion signature from second video
            threshold: Minimum similarity score (0-100)
            params: Optional parameters (min_variance)

        Returns:
            Dictionary with similarity, accepted, and metadata
        """
        if features1 is None or features2 is None or len(features1) == 0 or len(features2) == 0:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Empty feature sets',
                    'len_1': 0 if features1 is None else len(features1),
                    'len_2': 0 if features2 is None else len(features2)
                }
            }

        # Get min_variance parameter
        min_variance = params.get('min_variance', 0.0) if params else 0.0

        # Check if static scenes (low variance)
        std1 = features1.std()
        std2 = features2.std()

        if std1 <= min_variance or std2 <= min_variance:
            # Both static scenes - perfect match
            similarity = 100.0
        else:
            # Normalize both signatures
            norm1 = (features1 - features1.mean()) / std1
            norm2 = (features2 - features2.mean()) / std2

            # Make sure arrays have same length for correlation
            min_len = min(len(norm1), len(norm2))
            norm1_slice = norm1[:min_len]
            norm2_slice = norm2[:min_len]

            if min_len < 2:
                similarity = 0.0
            else:
                # Compute correlation coefficient
                correlation = np.corrcoef(norm1_slice, norm2_slice)[0, 1]

                # Handle NaN correlation
                if np.isnan(correlation):
                    similarity = 0.0
                else:
                    similarity = max(0.0, min(100.0, correlation * 100.0))

        return {
            'similarity': similarity,
            'accepted': similarity >= threshold,
            'metadata': {
                'len_1': len(features1),
                'len_2': len(features2),
                'std_1': float(std1),
                'std_2': float(std2),
                'static_1': std1 <= min_variance,
                'static_2': std2 <= min_variance
            }
        }
