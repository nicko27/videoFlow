"""
Edge Pattern Algorithm.

Compare edge patterns using Canny edge detection with grid-based density analysis.
Effective for scenes with distinctive structural features.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple

from duplicateflow.core import register_algorithm
from duplicateflow.sdk import Algorithm
from duplicateflow.algorithms.base import VideoLoader


@register_algorithm(
    name="edge_pattern",
    display_name="📐 Motif de Contours",
    short_name="Edge Pattern",
    description="Compare les motifs de contours via Canny et grille",
    detailed_explanation=(
        "Utilise la détection de contours Canny avec une grille pour analyser "
        "la densité des contours par région. Compare les patterns structurels "
        "entre les vidéos avec une fenêtre glissante."
    ),
    category="structural",
    speed="fast",
    default_threshold=70.0,
    default_params={
        'threshold': 70.0,
        'canny_low': 50,
        'canny_high': 150,
        'grid_size': (8, 8),
        'num_samples': 5,
        'search_step': 3.0,
        'max_windows': 200,
        'resize': (320, 240)
    },
    use_case="Scènes avec structures visuelles distinctives (bâtiments, objets, textures)"
)
class EdgePatternAlgorithm(Algorithm):
    """
    Edge pattern comparison algorithm.

    Uses Canny edge detection with grid-based density analysis to compare
    structural patterns between videos.

    Algorithm steps:
    1. Extract N sample frames from short video
    2. Apply Canny edge detection
    3. Divide into grid and calculate edge density per cell
    4. Slide window over long video
    5. Compare edge patterns using cosine similarity

    Parameters:
        threshold: Minimum similarity score (0-100)
        canny_low: Canny lower threshold
        canny_high: Canny upper threshold
        grid_size: Grid dimensions (rows, cols)
        num_samples: Number of frames to sample
        search_step: Sliding window step (seconds)
        max_windows: Maximum windows to test
        resize: Target frame size
    """

    def configure(self, **params):
        """Configure algorithm parameters."""
        self.threshold = params.get('threshold', 70.0)
        self.canny_low = params.get('canny_low', 50)
        self.canny_high = params.get('canny_high', 150)
        self.grid_size = params.get('grid_size', (8, 8))
        self.num_samples = params.get('num_samples', 5)
        self.search_step = params.get('search_step', 3.0)
        self.max_windows = params.get('max_windows', 200)
        self.resize = params.get('resize', (320, 240))

        # Validate grid size
        if not isinstance(self.grid_size, (list, tuple)) or len(self.grid_size) != 2:
            self.grid_size = (8, 8)

    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: float = 0.0,
        duration: float = None
    ) -> Dict[str, Any]:
        """
        Compare videos using edge patterns.

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

        # Extract edge patterns from short video
        short_offsets, short_patterns = self._extract_edge_signatures(
            short_video, duration
        )

        if len(short_patterns) < 2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Insufficient frames for edge comparison',
                    'num_samples': len(short_patterns)
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
                short_patterns
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
                'num_samples': len(short_patterns),
                'windows_tested': len(window_starts),
                'score_percentage': best_score,
                'grid_size': self.grid_size
            }
        }

    def extract_features(self, video_path: str) -> List[np.ndarray]:
        """
        Extract edge pattern features from entire video.

        Args:
            video_path: Path to video

        Returns:
            List of edge density patterns (flattened grids)
        """
        with VideoLoader(video_path) as loader:
            duration = loader.duration

        sample_interval = max(1.0, duration / self.num_samples)
        offsets = [i * sample_interval for i in range(self.num_samples)]

        patterns = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Compute edge pattern
                pattern = self._compute_edge_pattern(frame)
                if pattern is not None:
                    patterns.append(pattern)

        return patterns

    def _extract_edge_signatures(
        self,
        video_path: str,
        duration: float
    ) -> Tuple[List[float], List[np.ndarray]]:
        """
        Extract edge patterns from video.

        Args:
            video_path: Path to video
            duration: Duration to analyze

        Returns:
            Tuple of (offsets, edge_patterns)
        """
        sample_interval = max(1.0, duration / self.num_samples)
        offsets = [i * sample_interval for i in range(self.num_samples)]

        patterns = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Compute edge pattern
                pattern = self._compute_edge_pattern(frame)
                if pattern is not None:
                    patterns.append(pattern)

        return offsets, patterns

    def _compute_edge_pattern(self, frame: np.ndarray) -> np.ndarray:
        """
        Compute edge density pattern using Canny + grid.

        Args:
            frame: Input frame (BGR)

        Returns:
            Edge density vector (flattened grid)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Canny edge detection
        edges = cv2.Canny(blurred, self.canny_low, self.canny_high)

        # Divide into grid and calculate density
        h, w = edges.shape
        rows, cols = self.grid_size
        cell_h = h // rows
        cell_w = w // cols

        edge_pattern = []

        for i in range(rows):
            for j in range(cols):
                # Extract cell
                cell = edges[
                    i * cell_h:(i + 1) * cell_h,
                    j * cell_w:(j + 1) * cell_w
                ]

                # Calculate edge density (percentage of edge pixels)
                density = np.sum(cell > 0) / cell.size
                edge_pattern.append(density)

        return np.array(edge_pattern, dtype=np.float32)

    def _compare_window(
        self,
        long_video: str,
        window_start: float,
        short_offsets: List[float],
        short_patterns: List[np.ndarray]
    ) -> float:
        """
        Compare edge patterns at a window position.

        Args:
            long_video: Path to long video
            window_start: Window start position
            short_offsets: Sample offsets
            short_patterns: Edge patterns from short video

        Returns:
            Average similarity score (0-100)
        """
        similarities = []

        with VideoLoader(long_video) as loader:
            for offset, short_pattern in zip(short_offsets, short_patterns):
                timestamp = window_start + offset

                # Extract frame
                frame = loader.get_frame(timestamp)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Compute edge pattern
                long_pattern = self._compute_edge_pattern(frame)
                if long_pattern is None:
                    continue

                # Compute cosine similarity
                dot_product = np.dot(short_pattern, long_pattern)
                norm_short = np.linalg.norm(short_pattern)
                norm_long = np.linalg.norm(long_pattern)

                if norm_short > 0 and norm_long > 0:
                    similarity = dot_product / (norm_short * norm_long)
                    similarities.append(max(0.0, similarity))

        if not similarities:
            return 0.0

        return np.mean(similarities) * 100.0

    def get_cli_params(self):
        """Return CLI parameters."""
        return [
            {
                'names': ['--edge-canny-low'],
                'type': 'int',
                'default': 50,
                'help': 'Canny lower threshold'
            },
            {
                'names': ['--edge-canny-high'],
                'type': 'int',
                'default': 150,
                'help': 'Canny upper threshold'
            },
            {
                'names': ['--edge-grid'],
                'type': 'str',
                'default': '8,8',
                'help': 'Grid size (rows,cols)'
            },
            {
                'names': ['--edge-samples'],
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
        Compare two sets of edge patterns using cosine similarity.

        Args:
            features1: List of edge patterns from first video
            features2: List of edge patterns from second video
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
                    'num_patterns_1': len(features1),
                    'num_patterns_2': len(features2)
                }
            }

        # Compare each pattern from features1 with each from features2
        similarities = []

        for pattern1 in features1:
            for pattern2 in features2:
                # Compute cosine similarity
                dot_product = np.dot(pattern1, pattern2)
                norm1 = np.linalg.norm(pattern1)
                norm2 = np.linalg.norm(pattern2)

                if norm1 > 0 and norm2 > 0:
                    similarity = dot_product / (norm1 * norm2)
                    similarities.append(max(0.0, similarity * 100.0))

        if not similarities:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'No valid comparisons',
                    'num_patterns_1': len(features1),
                    'num_patterns_2': len(features2)
                }
            }

        # Average similarity
        avg_similarity = float(np.mean(similarities))

        return {
            'similarity': avg_similarity,
            'accepted': avg_similarity >= threshold,
            'metadata': {
                'num_patterns_1': len(features1),
                'num_patterns_2': len(features2),
                'num_comparisons': len(similarities),
                'min_similarity': float(np.min(similarities)),
                'max_similarity': float(np.max(similarities))
            }
        }
