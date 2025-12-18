"""
SSIM Algorithm.

Compare videos using Structural Similarity Index (SSIM).
Effective for detecting perceptually similar scenes.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple

from duplicateflow.core import register_algorithm
from duplicateflow.sdk import Algorithm
from duplicateflow.algorithms.base import VideoLoader

# Import SSIM from scikit-image
try:
    from skimage.metrics import structural_similarity as compute_ssim_skimage
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False


@register_algorithm(
    name="ssim",
    display_name="🔍 SSIM",
    short_name="SSIM",
    description="Compare via Structural Similarity Index (SSIM)",
    detailed_explanation=(
        "Utilise l'indice de similarité structurelle (SSIM) pour comparer "
        "la similarité perceptuelle entre frames. SSIM considère la luminance, "
        "le contraste et la structure. Extrait plusieurs frames de référence "
        "et cherche la position avec le meilleur score SSIM moyen."
    ),
    category="perceptual",
    speed="medium",
    default_threshold=0.70,
    default_params={
        'threshold': 0.70,
        'sample_interval': 5.0,
        'num_samples': None,
        'search_step': 3.0,
        'max_windows': 200,
        'resize': (320, 240)
    },
    use_case="Scènes visuellement similaires (même éclairage, angle de caméra, composition)"
)
class SSIMAlgorithm(Algorithm):
    """
    SSIM (Structural Similarity Index) comparison algorithm.

    Uses SSIM to compare perceptual similarity between frames.
    SSIM considers luminance, contrast, and structure.

    Algorithm steps:
    1. Extract N frames from short video
    2. Slide window over long video
    3. For each window, extract corresponding frames
    4. Compute SSIM between frame pairs
    5. Return average SSIM score
    6. Return best matching position

    Parameters:
        threshold: Minimum SSIM score (0-1, typically 0.6-0.9)
        sample_interval: Interval between samples (seconds)
        num_samples: Number of frames (None = auto based on duration)
        search_step: Sliding window step (seconds)
        max_windows: Maximum windows to test
        resize: Target frame size for SSIM computation
    """

    def configure(self, **params):
        """Configure algorithm parameters."""
        self.threshold = params.get('threshold', 0.70)
        self.sample_interval = params.get('sample_interval', 5.0)
        self.num_samples = params.get('num_samples', None)
        self.search_step = params.get('search_step', 3.0)
        self.max_windows = params.get('max_windows', 200)
        self.resize = params.get('resize', (320, 240))

        # Validate threshold (SSIM is 0-1, not 0-100)
        if self.threshold > 1.0:
            self.threshold = self.threshold / 100.0

    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: float = 0.0,
        duration: float = None
    ) -> Dict[str, Any]:
        """
        Compare videos using SSIM.

        Args:
            short_video: Path to short video
            long_video: Path to long video
            start_time: Start position in long video
            duration: Duration to analyze

        Returns:
            Dictionary with similarity, accepted, metadata
        """
        # Check if scikit-image is available
        if not SKIMAGE_AVAILABLE:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'scikit-image not installed (required for SSIM)',
                    'install': 'pip install scikit-image'
                }
            }

        # Validate inputs
        self._validate_video_path(short_video)
        self._validate_video_path(long_video)

        # Get duration from short video if not provided
        if duration is None:
            with VideoLoader(short_video) as loader:
                duration = loader.duration

        self._validate_time_params(start_time, duration)

        # Extract reference frames from short video
        short_offsets, short_frames = self._extract_reference_frames(
            short_video, duration
        )

        if len(short_frames) < 3:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Insufficient frames for SSIM comparison',
                    'num_samples': len(short_frames)
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
                short_frames
            )

            if score > best_score:
                best_score = score
                best_offset = window_start

            # Early termination (SSIM threshold is 0-1, convert to 0-100 for comparison)
            if score >= (self.threshold * 100.0) + 5:
                break

        # Convert score to 0-1 range
        similarity = best_score / 100.0

        return {
            'similarity': similarity,
            'accepted': similarity >= self.threshold,
            'metadata': {
                'best_offset_seconds': best_offset,
                'num_samples': len(short_frames),
                'windows_tested': len(window_starts),
                'score_percentage': best_score
            }
        }

    def _extract_reference_frames(
        self,
        video_path: str,
        duration: float
    ) -> Tuple[List[float], List[np.ndarray]]:
        """
        Extract reference frames from video.

        Args:
            video_path: Path to video
            duration: Duration to analyze

        Returns:
            Tuple of (offsets, frames)
        """
        # Calculate number of samples
        if self.num_samples is None:
            num_samples = max(5, int(duration / self.sample_interval))
            num_samples = max(3, min(num_samples, 150))
        else:
            num_samples = max(3, min(self.num_samples, 150))

        offsets = np.linspace(0, duration, num_samples)
        frames = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                frames.append(frame)

        return list(offsets), frames

    def _compare_window(
        self,
        long_video: str,
        window_start: float,
        short_offsets: List[float],
        short_frames: List[np.ndarray]
    ) -> float:
        """
        Compare SSIM at a window position.

        Args:
            long_video: Path to long video
            window_start: Window start position
            short_offsets: Sample offsets
            short_frames: Reference frames from short video

        Returns:
            Average SSIM score (0-100)
        """
        scores = []

        with VideoLoader(long_video) as loader:
            for offset, short_frame in zip(short_offsets, short_frames):
                timestamp = window_start + offset

                # Extract frame
                long_frame = loader.get_frame(timestamp)
                if long_frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    long_frame = cv2.resize(long_frame, self.resize)

                # Compute SSIM
                ssim_score = self._compute_ssim(short_frame, long_frame)
                scores.append(ssim_score)

        if not scores:
            return 0.0

        # Return average score as percentage
        return float(np.mean(scores)) * 100.0

    def _compute_ssim(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """
        Compute SSIM between two frames.

        Args:
            frame1: First frame (BGR)
            frame2: Second frame (BGR)

        Returns:
            SSIM score (0-1)
        """
        # Convert to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # Compute SSIM using scikit-image
        ssim_score = compute_ssim_skimage(gray1, gray2)

        return float(ssim_score)

    def extract_features(self, video_path: str) -> List[np.ndarray]:
        """
        Extract frame features from entire video for SSIM comparison.

        Args:
            video_path: Path to video

        Returns:
            List of frames (as numpy arrays)
        """
        if not SKIMAGE_AVAILABLE:
            return []

        with VideoLoader(video_path) as loader:
            duration = loader.duration

        # Calculate number of samples
        if self.num_samples is None:
            num_samples = max(5, int(duration / self.sample_interval))
            num_samples = max(3, min(num_samples, 150))
        else:
            num_samples = max(3, min(self.num_samples, 150))

        offsets = np.linspace(0, duration, num_samples)
        frames = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                frames.append(frame)

        return frames

    def get_cli_params(self):
        """Return CLI parameters."""
        return [
            {
                'names': ['--ssim-threshold'],
                'type': 'float',
                'default': 0.70,
                'help': 'SSIM threshold (0-1, typically 0.6-0.9)'
            },
            {
                'names': ['--ssim-sample-interval'],
                'type': 'float',
                'default': 5.0,
                'help': 'Interval between samples (seconds)'
            },
            {
                'names': ['--ssim-num-samples'],
                'type': 'int',
                'default': None,
                'help': 'Number of samples (None = auto)'
            }
        ]

    def get_requirements(self):
        """Return package requirements."""
        return [
            'opencv-python>=4.8.0',
            'numpy>=1.24.0',
            'scikit-image>=0.21.0'
        ]

    @staticmethod
    def compare_features(
        features1: List[np.ndarray],
        features2: List[np.ndarray],
        threshold: float,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Compare two sets of frames using SSIM.

        Args:
            features1: List of frames from first video
            features2: List of frames from second video
            threshold: Minimum SSIM score (0-1 typically, or 0-100)
            params: Optional parameters (not used)

        Returns:
            Dictionary with similarity, accepted, and metadata
        """
        if not SKIMAGE_AVAILABLE:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'scikit-image not installed',
                    'install': 'pip install scikit-image'
                }
            }

        if not features1 or not features2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Empty feature sets',
                    'num_frames_1': len(features1),
                    'num_frames_2': len(features2)
                }
            }

        # Normalize threshold (SSIM is 0-1, but threshold might be 0-100)
        normalized_threshold = threshold / 100.0 if threshold > 1.0 else threshold

        # Compare each frame from features1 with each from features2
        scores = []

        for frame1 in features1:
            for frame2 in features2:
                # Convert to grayscale
                gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY) if len(frame1.shape) == 3 else frame1
                gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY) if len(frame2.shape) == 3 else frame2

                # Ensure same shape
                if gray1.shape != gray2.shape:
                    # Resize to match
                    h, w = min(gray1.shape[0], gray2.shape[0]), min(gray1.shape[1], gray2.shape[1])
                    gray1_resized = cv2.resize(gray1, (w, h))
                    gray2_resized = cv2.resize(gray2, (w, h))
                else:
                    gray1_resized = gray1
                    gray2_resized = gray2

                # Compute SSIM
                ssim_score = compute_ssim_skimage(gray1_resized, gray2_resized)
                scores.append(float(ssim_score))

        if not scores:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'No valid comparisons',
                    'num_frames_1': len(features1),
                    'num_frames_2': len(features2)
                }
            }

        # Average similarity (0-1 range)
        avg_similarity = float(np.mean(scores))

        return {
            'similarity': avg_similarity,
            'accepted': avg_similarity >= normalized_threshold,
            'metadata': {
                'num_frames_1': len(features1),
                'num_frames_2': len(features2),
                'num_comparisons': len(scores),
                'min_similarity': float(np.min(scores)),
                'max_similarity': float(np.max(scores)),
                'avg_similarity_percent': avg_similarity * 100.0
            }
        }
