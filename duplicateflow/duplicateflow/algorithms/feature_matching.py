"""
Feature Matching Algorithm.

Compare videos using local feature detectors (ORB, AKAZE, SIFT).
Effective for detecting scenes with distinctive keypoints and structures.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

from duplicateflow.core import register_algorithm
from duplicateflow.sdk import Algorithm
from duplicateflow.algorithms.base import VideoLoader


@register_algorithm(
    name="feature_matching",
    display_name="🎯 Feature Matching",
    short_name="Features",
    description="Compare via détection de features locales (ORB/AKAZE/SIFT)",
    detailed_explanation=(
        "Détecte des points d'intérêt (keypoints) dans les frames à l'aide "
        "de détecteurs comme ORB, AKAZE ou SIFT. Extrait des descripteurs "
        "pour chaque keypoint, puis les apparie entre frames. Calcule le "
        "ratio de correspondances pour mesurer la similarité."
    ),
    category="structural",
    speed="medium",
    default_threshold=30.0,
    default_params={
        'threshold': 30.0,
        'detector': 'ORB',
        'max_features': 500,
        'num_samples': None,
        'sample_interval': 10.0,
        'ratio_test': 0.75,
        'min_matches': 10,
        'search_step': 3.0,
        'max_windows': 100,
        'resize': (640, 360)
    },
    use_case="Scènes avec points d'intérêt distinctifs (objets, textures, structures géométriques)"
)
class FeatureMatchingAlgorithm(Algorithm):
    """
    Feature matching comparison algorithm.

    Uses local feature detectors (ORB, AKAZE, or SIFT) to extract keypoints
    and descriptors, then matches them between videos.

    Algorithm steps:
    1. Select feature detector (ORB, AKAZE, or SIFT)
    2. Extract N frames from short video
    3. Detect keypoints and compute descriptors
    4. Slide window over long video
    5. For each window, match features using BFMatcher
    6. Apply ratio test (Lowe's test)
    7. Calculate match ratio (matches / total keypoints)
    8. Return best matching position

    Parameters:
        threshold: Minimum match ratio (0-100)
        detector: Feature detector ('ORB', 'AKAZE', 'SIFT')
        max_features: Maximum features to detect
        num_samples: Number of frames to sample
        sample_interval: Interval between samples (seconds)
        ratio_test: Lowe's ratio test threshold (0.7-0.8)
        min_matches: Minimum number of matches required
        search_step: Sliding window step (seconds)
        max_windows: Maximum windows to test
        resize: Target frame size
    """

    def configure(self, **params):
        """Configure algorithm parameters."""
        self.threshold = params.get('threshold', 30.0)
        self.detector_name = params.get('detector', 'ORB').upper()
        self.max_features = params.get('max_features', 500)
        self.num_samples = params.get('num_samples', None)
        self.sample_interval = params.get('sample_interval', 10.0)
        self.ratio_test = params.get('ratio_test', 0.75)
        self.min_matches = params.get('min_matches', 10)
        self.search_step = params.get('search_step', 3.0)
        self.max_windows = params.get('max_windows', 100)
        self.resize = params.get('resize', (640, 360))

        # Create detector
        self.detector, self.norm = self._create_detector()

    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: float = 0.0,
        duration: float = None
    ) -> Dict[str, Any]:
        """
        Compare videos using feature matching.

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

        # Extract frames and descriptors from short video
        short_data = self._extract_features(short_video, duration)

        if len(short_data) < 2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Insufficient frames for feature matching',
                    'num_samples': len(short_data)
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

        # Create matcher
        bf = cv2.BFMatcher(self.norm, crossCheck=False)

        # Sliding window search
        best_score = 0.0
        best_matches = 0.0
        best_offset = 0.0

        for window_start in window_starts:
            score, num_matches = self._compare_window(
                long_video,
                window_start,
                short_data,
                bf
            )

            if score > best_score:
                best_score = score
                best_matches = num_matches
                best_offset = window_start

            # Early termination
            if score >= self.threshold + 5 and num_matches >= self.min_matches:
                break

        similarity = best_score / 100.0
        accepted = (best_score >= self.threshold) and (best_matches >= self.min_matches)

        return {
            'similarity': similarity,
            'accepted': accepted,
            'metadata': {
                'best_offset_seconds': best_offset,
                'num_samples': len(short_data),
                'detector': self.detector_name,
                'avg_matches': best_matches,
                'windows_tested': len(window_starts),
                'score_percentage': best_score
            }
        }

    def _create_detector(self) -> Tuple:
        """
        Create feature detector and matcher norm.

        Returns:
            Tuple of (detector, norm)
        """
        if self.detector_name == 'ORB':
            detector = cv2.ORB_create(nfeatures=self.max_features)
            norm = cv2.NORM_HAMMING
        elif self.detector_name == 'AKAZE':
            detector = cv2.AKAZE_create()
            norm = cv2.NORM_HAMMING
        elif self.detector_name == 'SIFT':
            try:
                detector = cv2.SIFT_create(nfeatures=self.max_features)
                norm = cv2.NORM_L2
            except AttributeError:
                # SIFT not available, fallback to ORB
                detector = cv2.ORB_create(nfeatures=self.max_features)
                norm = cv2.NORM_HAMMING
        else:
            # Default to ORB
            detector = cv2.ORB_create(nfeatures=self.max_features)
            norm = cv2.NORM_HAMMING

        return detector, norm

    def _extract_features(
        self,
        video_path: str,
        duration: float
    ) -> List[Tuple[float, np.ndarray, np.ndarray]]:
        """
        Extract features from video.

        Args:
            video_path: Path to video
            duration: Duration to analyze

        Returns:
            List of (offset, keypoints, descriptors)
        """
        # Calculate number of samples
        if self.num_samples is None:
            num_samples = max(3, int(duration / self.sample_interval))
        else:
            num_samples = max(3, self.num_samples)

        features = []

        with VideoLoader(video_path) as loader:
            for i in range(num_samples):
                offset = (i / (num_samples - 1)) * duration if num_samples > 1 else duration / 2

                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Detect and compute
                kp, des = self.detector.detectAndCompute(gray, None)

                if des is not None and len(kp) >= 10:
                    # Convert KeyPoints to serializable format (for caching)
                    # Store only descriptors and count (keypoints themselves are not picklable)
                    features.append((offset, len(kp), des))  # (offset, num_keypoints, descriptors)

        return features

    def _compare_window(
        self,
        long_video: str,
        window_start: float,
        short_data: List[Tuple[float, Any, np.ndarray]],
        bf: cv2.BFMatcher
    ) -> Tuple[float, float]:
        """
        Compare features at a window position.

        Args:
            long_video: Path to long video
            window_start: Window start position
            short_data: Features from short video
            bf: BFMatcher instance

        Returns:
            Tuple of (average_score, average_matches)
        """
        match_ratios = []
        match_counts = []

        with VideoLoader(long_video) as loader:
            for offset, num_kp1, des1 in short_data:
                timestamp = window_start + offset

                # Extract frame
                frame = loader.get_frame(timestamp)
                if frame is None:
                    continue

                # Resize if needed
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Detect and compute
                kp2, des2 = self.detector.detectAndCompute(gray, None)

                if des2 is None or len(kp2) < 10:
                    continue

                # Match features
                if self.ratio_test > 0:
                    # Use ratio test (Lowe's test)
                    raw_matches = bf.knnMatch(des1, des2, k=2)

                    good = []
                    for pair in raw_matches:
                        if len(pair) < 2:
                            continue
                        m, n = pair
                        if m.distance < self.ratio_test * n.distance:
                            good.append(m)

                    matches = good
                else:
                    # Direct matching
                    matches = bf.match(des1, des2)

                # Calculate match ratio (num_kp1 is now an integer)
                if num_kp1 > 0:
                    match_ratio = len(matches) / num_kp1 * 100.0
                    match_ratios.append(match_ratio)
                    match_counts.append(len(matches))

        if not match_ratios:
            return 0.0, 0.0

        return float(np.mean(match_ratios)), float(np.mean(match_counts))

    def extract_features(self, video_path: str) -> List[Tuple[float, Any, np.ndarray]]:
        """
        Extract keypoints and descriptors from entire video.

        Args:
            video_path: Path to video

        Returns:
            List of (offset, keypoints, descriptors) tuples
        """
        with VideoLoader(video_path) as loader:
            duration = loader.duration

        # Extract features from entire video
        features = self._extract_features(video_path, duration)

        return features

    def get_cli_params(self):
        """Return CLI parameters."""
        return [
            {
                'names': ['--feature-detector'],
                'type': 'str',
                'default': 'ORB',
                'help': 'Feature detector (ORB, AKAZE, SIFT)'
            },
            {
                'names': ['--feature-max-features'],
                'type': 'int',
                'default': 500,
                'help': 'Maximum features to detect'
            },
            {
                'names': ['--feature-ratio-test'],
                'type': 'float',
                'default': 0.75,
                'help': "Lowe's ratio test threshold (0.7-0.8)"
            },
            {
                'names': ['--feature-min-matches'],
                'type': 'int',
                'default': 10,
                'help': 'Minimum number of matches required'
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
        features1: List[Tuple[float, Any, np.ndarray]],
        features2: List[Tuple[float, Any, np.ndarray]],
        threshold: float,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Compare two sets of keypoint/descriptor features.

        Args:
            features1: List of (offset, keypoints, descriptors) from first video
            features2: List of (offset, keypoints, descriptors) from second video
            threshold: Minimum match ratio (0-100)
            params: Optional parameters (detector, ratio_test, min_matches)

        Returns:
            Dictionary with similarity, accepted, and metadata
        """
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

        # Get parameters
        detector_name = params.get('detector', 'ORB').upper() if params else 'ORB'
        ratio_test = params.get('ratio_test', 0.75) if params else 0.75
        min_matches = params.get('min_matches', 10) if params else 10

        # Determine norm type based on detector
        if detector_name == 'SIFT':
            norm = cv2.NORM_L2
        else:
            norm = cv2.NORM_HAMMING

        # Create matcher
        bf = cv2.BFMatcher(norm, crossCheck=False)

        # Compare features
        match_ratios = []
        match_counts = []

        for _, num_kp1, des1 in features1:
            for _, num_kp2, des2 in features2:
                # num_kp1 and num_kp2 are integers (number of keypoints)
                if des1 is None or des2 is None or num_kp1 < 10 or num_kp2 < 10:
                    continue

                # Match features
                if ratio_test > 0:
                    # Use ratio test (Lowe's test)
                    try:
                        raw_matches = bf.knnMatch(des1, des2, k=2)

                        good = []
                        for pair in raw_matches:
                            if len(pair) < 2:
                                continue
                            m, n = pair
                            if m.distance < ratio_test * n.distance:
                                good.append(m)

                        matches = good
                    except:
                        matches = []
                else:
                    # Direct matching
                    try:
                        matches = bf.match(des1, des2)
                    except:
                        matches = []

                # Calculate match ratio (num_kp1 is now an integer)
                if num_kp1 > 0:
                    match_ratio = len(matches) / num_kp1 * 100.0
                    match_ratios.append(match_ratio)
                    match_counts.append(len(matches))

        if not match_ratios:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'No valid matches',
                    'num_frames_1': len(features1),
                    'num_frames_2': len(features2)
                }
            }

        # Average similarity
        avg_similarity = float(np.mean(match_ratios))
        avg_matches = float(np.mean(match_counts))

        # Accepted if meets threshold AND min_matches
        accepted = (avg_similarity >= threshold) and (avg_matches >= min_matches)

        return {
            'similarity': avg_similarity,
            'accepted': accepted,
            'metadata': {
                'num_frames_1': len(features1),
                'num_frames_2': len(features2),
                'num_comparisons': len(match_ratios),
                'avg_matches': avg_matches,
                'min_match_ratio': float(np.min(match_ratios)),
                'max_match_ratio': float(np.max(match_ratios)),
                'detector': detector_name
            }
        }
