"""
Color Histogram Algorithm.

Compare color distributions using HSV histograms with sliding window search.
This algorithm is fast and effective for scenes with characteristic color palettes.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple

from duplicateflow.core import register_algorithm
from duplicateflow.sdk import Algorithm
from duplicateflow.algorithms.base import VideoLoader


@register_algorithm(
    name="color_histogram",
    display_name="🎨 Histogramme Couleur",
    short_name="Color Hist",
    description="Compare les distributions de couleur HSV",
    detailed_explanation=(
        "Utilise des histogrammes couleur HSV avec fenêtre glissante. "
        "Extrait plusieurs échantillons de la vidéo courte, calcule leurs "
        "histogrammes HSV, puis cherche la meilleure correspondance dans la "
        "vidéo longue en faisant glisser une fenêtre."
    ),
    category="statistical",
    speed="fast",
    default_threshold=70.0,
    default_params={
        'threshold': 70.0,
        'bins': (32, 32, 32),
        'num_samples': 5,
        'search_step': 3.0,
        'max_windows': 200,
        'resize': (320, 240)
    },
    use_case="Scènes avec palettes de couleurs caractéristiques (ciels, paysages, éclairages)"
)
class ColorHistogramAlgorithm(Algorithm):
    """
    Color histogram comparison algorithm.

    Compares HSV color histograms between videos using a sliding window
    approach to find the best matching position.

    Algorithm steps:
    1. Extract N sample frames uniformly from short video
    2. Compute HSV histogram for each frame
    3. Slide window over long video
    4. For each window position, compare histograms
    5. Return best matching score and position

    Parameters:
        threshold: Minimum similarity score (0-100)
        bins: Histogram bins for HSV channels (H, S, V)
        num_samples: Number of frames to sample from short video
        search_step: Step size for sliding window (seconds)
        max_windows: Maximum number of windows to test
        resize: Target frame size for processing
    """

    def configure(self, **params):
        """Configure algorithm parameters."""
        self.threshold = params.get('threshold', 70.0)
        self.bins = params.get('bins', (32, 32, 32))
        self.num_samples = params.get('num_samples', 5)
        self.search_step = params.get('search_step', 3.0)
        self.max_windows = params.get('max_windows', 200)
        self.resize = params.get('resize', (320, 240))

        # Validate bins
        if not isinstance(self.bins, (list, tuple)) or len(self.bins) != 3:
            self.bins = (32, 32, 32)

    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: float = 0.0,
        duration: float = None
    ) -> Dict[str, Any]:
        """
        Compare videos using color histograms.

        Args:
            short_video: Path to short video (scene to find)
            long_video: Path to long video (where to search)
            start_time: Start position in long video
            duration: Duration to analyze (uses short video duration if None)

        Returns:
            Dictionary with:
            - similarity: Score 0.0-1.0
            - accepted: True if similarity >= threshold
            - metadata: Additional information
        """
        # Validate inputs
        self._validate_video_path(short_video)
        self._validate_video_path(long_video)

        # Get duration from short video if not provided
        if duration is None:
            with VideoLoader(short_video) as loader:
                duration = loader.duration

        self._validate_time_params(start_time, duration)

        # Extract histograms from short video
        short_offsets, short_hists = self._extract_color_signatures(
            short_video, duration
        )

        if len(short_hists) < 2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Insufficient frames for color comparison',
                    'num_samples': len(short_hists)
                }
            }

        # Get long video duration
        with VideoLoader(long_video) as loader:
            long_duration = loader.duration

        # Calculate sliding window positions
        searchable = max(long_duration - duration, 0)

        # Default start_time to 0.0 if None
        if start_time is None:
            start_time = 0.0

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
                short_hists
            )

            if score > best_score:
                best_score = score
                best_offset = window_start

            # Early termination if excellent match
            if score >= self.threshold + 5:
                break

        # Convert to 0-1 range
        similarity = best_score / 100.0

        return {
            'similarity': similarity,
            'accepted': best_score >= self.threshold,
            'metadata': {
                'best_offset_seconds': best_offset,
                'num_samples': len(short_hists),
                'windows_tested': len(window_starts),
                'score_percentage': best_score
            }
        }

    def extract_features(self, video_path: str) -> List[np.ndarray]:
        """
        Extract color histogram features from entire video.

        Args:
            video_path: Path to video

        Returns:
            List of normalized HSV histograms
        """
        with VideoLoader(video_path) as loader:
            duration = loader.duration

        sample_interval = max(1.0, duration / self.num_samples)
        offsets = [i * sample_interval for i in range(self.num_samples)]

        histograms = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Compute histogram
                hist = self._compute_histogram(frame)
                if hist is not None:
                    histograms.append(hist)

        return histograms

    def _extract_color_signatures(
        self,
        video_path: str,
        duration: float
    ) -> Tuple[List[float], List[np.ndarray]]:
        """
        Extract color histograms from video at uniform intervals.

        Args:
            video_path: Path to video
            duration: Duration to analyze

        Returns:
            Tuple of (offsets, histograms)
        """
        sample_interval = max(1.0, duration / self.num_samples)
        offsets = [i * sample_interval for i in range(self.num_samples)]

        histograms = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Compute histogram
                hist = self._compute_histogram(frame)
                if hist is not None:
                    histograms.append(hist)

        return offsets, histograms

    def _compute_histogram(self, frame: np.ndarray) -> np.ndarray:
        """
        Compute normalized HSV histogram for a frame.

        Args:
            frame: Input frame (BGR)

        Returns:
            Normalized flattened histogram
        """
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Calculate histogram
        hist = cv2.calcHist(
            [hsv],
            [0, 1, 2],  # H, S, V channels
            None,
            self.bins,
            [0, 180, 0, 256, 0, 256]  # HSV ranges
        )

        # Normalize and flatten
        hist = cv2.normalize(hist, hist).flatten().astype(np.float32)

        return hist

    def _compare_window(
        self,
        long_video: str,
        window_start: float,
        short_offsets: List[float],
        short_hists: List[np.ndarray]
    ) -> float:
        """
        Compare histograms at a specific window position.

        Args:
            long_video: Path to long video
            window_start: Window start position (seconds)
            short_offsets: Offset times for samples
            short_hists: Histograms from short video

        Returns:
            Average similarity score (0-100)
        """
        similarities = []

        with VideoLoader(long_video) as loader:
            for offset, short_hist in zip(short_offsets, short_hists):
                timestamp = window_start + offset

                # Extract frame
                frame = loader.get_frame(timestamp)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Compute histogram
                long_hist = self._compute_histogram(frame)
                if long_hist is None:
                    continue

                # Compare histograms using correlation
                similarity = cv2.compareHist(
                    short_hist.astype(np.float32),
                    long_hist.astype(np.float32),
                    cv2.HISTCMP_CORREL
                )

                # Correlation ranges from -1 to 1, clamp to 0-1
                similarities.append(max(0.0, similarity))

        if not similarities:
            return 0.0

        # Return average similarity as percentage
        return np.mean(similarities) * 100.0

    def get_cli_params(self):
        """Return CLI parameters for this algorithm."""
        return [
            {
                'names': ['--color-bins'],
                'type': 'str',
                'default': '32,32,32',
                'help': 'Histogram bins for H,S,V (comma-separated)'
            },
            {
                'names': ['--color-samples'],
                'type': 'int',
                'default': 5,
                'help': 'Number of frames to sample'
            },
            {
                'names': ['--color-search-step'],
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
        features1: List[np.ndarray],
        features2: List[np.ndarray],
        threshold: float,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Compare two sets of color histograms.

        Args:
            features1: List of histograms from first video
            features2: List of histograms from second video
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
                    'num_hists_1': len(features1),
                    'num_hists_2': len(features2)
                }
            }

        # Compare each histogram from features1 with each from features2
        # and find the best average match
        similarities = []

        for hist1 in features1:
            for hist2 in features2:
                # Compare histograms using correlation
                sim = cv2.compareHist(
                    hist1.astype(np.float32),
                    hist2.astype(np.float32),
                    cv2.HISTCMP_CORREL
                )
                # Correlation ranges from -1 to 1, clamp to 0-1
                similarities.append(max(0.0, sim))

        if not similarities:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'No valid comparisons',
                    'num_hists_1': len(features1),
                    'num_hists_2': len(features2)
                }
            }

        # Average similarity as percentage
        avg_similarity = np.mean(similarities) * 100.0

        return {
            'similarity': avg_similarity,
            'accepted': avg_similarity >= threshold,
            'metadata': {
                'num_hists_1': len(features1),
                'num_hists_2': len(features2),
                'num_comparisons': len(similarities),
                'min_similarity': np.min(similarities) * 100.0,
                'max_similarity': np.max(similarities) * 100.0
            }
        }
