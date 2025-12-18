"""
HOG Descriptor Algorithm.

Compare videos using Histogram of Oriented Gradients.
Effective for detecting scenes with similar structural and shape patterns.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

from duplicateflow.core import register_algorithm
from duplicateflow.sdk import Algorithm
from duplicateflow.algorithms.base import VideoLoader


@register_algorithm(
    name="hog_descriptor",
    display_name="🔲 HOG Descriptor",
    short_name="HOG",
    description="Compare via Histogram of Oriented Gradients",
    detailed_explanation=(
        "Utilise HOG (Histogram of Oriented Gradients) pour capturer les "
        "patterns de gradients et la structure des scènes. Divise l'image "
        "en cellules, calcule les gradients d'orientation dans chaque cellule, "
        "puis compare les descripteurs HOG via corrélation."
    ),
    category="structural",
    speed="medium",
    default_threshold=70.0,
    default_params={
        'threshold': 70.0,
        'num_samples': 5,
        'cell_size': (8, 8),
        'block_size': (2, 2),
        'nbins': 9,
        'search_step': 3.0,
        'max_windows': 200,
        'resize': (128, 128)
    },
    use_case="Scènes avec structures et formes caractéristiques (silhouettes, objets)"
)
class HOGDescriptorAlgorithm(Algorithm):
    """
    HOG (Histogram of Oriented Gradients) comparison algorithm.

    Uses HOG descriptors to capture structural patterns and shapes,
    then compares them using correlation.

    Algorithm steps:
    1. Extract N frames from short video
    2. Resize to fixed size for HOG
    3. Compute HOG descriptor for each frame
    4. Slide window over long video
    5. Compare HOG descriptors using cosine similarity

    Parameters:
        threshold: Minimum similarity score (0-100)
        num_samples: Number of frames to sample
        cell_size: Size of HOG cells (pixels)
        block_size: Size of blocks in cells
        nbins: Number of orientation bins
        search_step: Sliding window step (seconds)
        max_windows: Maximum windows to test
        resize: Target frame size for HOG
    """

    def configure(self, **params):
        """Configure algorithm parameters."""
        self.threshold = params.get('threshold', 70.0)
        self.num_samples = params.get('num_samples', 5)
        self.cell_size = params.get('cell_size', (8, 8))
        self.block_size = params.get('block_size', (2, 2))
        self.nbins = params.get('nbins', 9)
        self.search_step = params.get('search_step', 3.0)
        self.max_windows = params.get('max_windows', 200)
        self.resize = params.get('resize', (128, 128))

        # Create HOG descriptor
        win_size = self.resize
        block_size_px = (self.cell_size[0] * self.block_size[0],
                        self.cell_size[1] * self.block_size[1])
        block_stride = self.cell_size
        cell_size = self.cell_size

        self.hog = cv2.HOGDescriptor(
            win_size,
            block_size_px,
            block_stride,
            cell_size,
            self.nbins
        )

    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: float = 0.0,
        duration: float = None
    ) -> Dict[str, Any]:
        """
        Compare videos using HOG descriptors.

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

        # Extract HOG descriptors from short video
        short_offsets, short_hogs = self._extract_hog_descriptors(
            short_video, duration
        )

        if len(short_hogs) < 2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Insufficient frames for HOG comparison',
                    'num_samples': len(short_hogs)
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
                short_hogs
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
                'num_samples': len(short_hogs),
                'windows_tested': len(window_starts),
                'score_percentage': best_score,
                'hog_params': {
                    'cell_size': self.cell_size,
                    'nbins': self.nbins
                }
            }
        }

    def _extract_hog_descriptors(
        self,
        video_path: str,
        duration: float
    ) -> Tuple[List[float], List[np.ndarray]]:
        """
        Extract HOG descriptors from video.

        Args:
            video_path: Path to video
            duration: Duration to analyze

        Returns:
            Tuple of (offsets, hog_descriptors)
        """
        sample_interval = max(1.0, duration / self.num_samples)
        offsets = [i * sample_interval for i in range(self.num_samples)]

        hog_descriptors = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Compute HOG descriptor
                hog_desc = self._compute_hog(frame)
                if hog_desc is not None:
                    hog_descriptors.append(hog_desc)

        return offsets, hog_descriptors

    def _compute_hog(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Compute HOG descriptor for a frame.

        Args:
            frame: Input frame (BGR)

        Returns:
            HOG descriptor vector
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Resize to HOG window size
            resized = cv2.resize(gray, self.resize)

            # Compute HOG descriptor
            hog_desc = self.hog.compute(resized)

            if hog_desc is not None:
                return hog_desc.flatten().astype(np.float32)

        except Exception:
            pass

        return None

    def _compare_window(
        self,
        long_video: str,
        window_start: float,
        short_offsets: List[float],
        short_hogs: List[np.ndarray]
    ) -> float:
        """
        Compare HOG descriptors at a window position.

        Args:
            long_video: Path to long video
            window_start: Window start position
            short_offsets: Sample offsets
            short_hogs: HOG descriptors from short video

        Returns:
            Average similarity score (0-100)
        """
        similarities = []

        with VideoLoader(long_video) as loader:
            for offset, short_hog in zip(short_offsets, short_hogs):
                timestamp = window_start + offset

                # Extract frame
                frame = loader.get_frame(timestamp)
                if frame is None:
                    continue

                # Compute HOG
                long_hog = self._compute_hog(frame)
                if long_hog is None:
                    continue

                # Compute cosine similarity
                dot_product = np.dot(short_hog, long_hog)
                norm_short = np.linalg.norm(short_hog)
                norm_long = np.linalg.norm(long_hog)

                if norm_short > 0 and norm_long > 0:
                    similarity = dot_product / (norm_short * norm_long)
                    similarities.append(max(0.0, similarity))

        if not similarities:
            return 0.0

        return float(np.mean(similarities) * 100.0)

    def extract_features(self, video_path: str) -> List[np.ndarray]:
        """
        Extract HOG descriptors from entire video.

        Args:
            video_path: Path to video

        Returns:
            List of HOG descriptor vectors
        """
        with VideoLoader(video_path) as loader:
            duration = loader.duration

        # Extract HOG descriptors from entire video
        _, hog_descriptors = self._extract_hog_descriptors(video_path, duration)

        return hog_descriptors

    def get_cli_params(self):
        """Return CLI parameters."""
        return [
            {
                'names': ['--hog-cell-size'],
                'type': 'str',
                'default': '8,8',
                'help': 'HOG cell size (width,height)'
            },
            {
                'names': ['--hog-nbins'],
                'type': 'int',
                'default': 9,
                'help': 'Number of orientation bins'
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
        Compare two sets of HOG descriptors using cosine similarity.

        Args:
            features1: List of HOG descriptors from first video
            features2: List of HOG descriptors from second video
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
                    'num_hogs_1': len(features1),
                    'num_hogs_2': len(features2)
                }
            }

        # Compare each HOG descriptor from features1 with each from features2
        similarities = []

        for hog1 in features1:
            for hog2 in features2:
                # Compute cosine similarity
                dot_product = np.dot(hog1, hog2)
                norm1 = np.linalg.norm(hog1)
                norm2 = np.linalg.norm(hog2)

                if norm1 > 0 and norm2 > 0:
                    similarity = dot_product / (norm1 * norm2)
                    similarities.append(max(0.0, similarity * 100.0))

        if not similarities:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'No valid comparisons',
                    'num_hogs_1': len(features1),
                    'num_hogs_2': len(features2)
                }
            }

        # Average similarity
        avg_similarity = float(np.mean(similarities))

        return {
            'similarity': avg_similarity,
            'accepted': avg_similarity >= threshold,
            'metadata': {
                'num_hogs_1': len(features1),
                'num_hogs_2': len(features2),
                'num_comparisons': len(similarities),
                'min_similarity': float(np.min(similarities)),
                'max_similarity': float(np.max(similarities))
            }
        }
