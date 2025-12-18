"""
Template Matching Algorithm.

Compare videos using template matching with normalized cross-correlation.
Effective for detecting exact or near-exact visual matches.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple

from duplicateflow.core import register_algorithm
from duplicateflow.sdk import Algorithm
from duplicateflow.algorithms.base import VideoLoader


@register_algorithm(
    name="template_matching",
    display_name="🎯 Template Matching",
    short_name="Template",
    description="Compare via template matching et corrélation normalisée",
    detailed_explanation=(
        "Utilise le template matching avec corrélation croisée normalisée. "
        "Extrait plusieurs templates de la vidéo courte, puis cherche ces "
        "templates dans la vidéo longue. Très efficace pour détecter des "
        "correspondances visuelles exactes ou quasi-exactes."
    ),
    category="structural",
    speed="medium",
    default_threshold=80.0,
    default_params={
        'threshold': 80.0,
        'num_templates': 5,
        'template_size': (64, 64),
        'method': 'TM_CCOEFF_NORMED',
        'search_step': 3.0,
        'max_windows': 150,
        'resize': (320, 240)
    },
    use_case="Scènes avec correspondances visuelles exactes (logos, UI, cadrage identique)"
)
class TemplateMatchingAlgorithm(Algorithm):
    """
    Template matching comparison algorithm.

    Uses normalized cross-correlation to find visual templates from
    short video in long video.

    Algorithm steps:
    1. Extract N templates from short video
    2. For each template, perform template matching in long video frames
    3. Compute matching score (peak correlation)
    4. Average scores across all templates

    Parameters:
        threshold: Minimum similarity score (0-100)
        num_templates: Number of templates to extract
        template_size: Size of templates (width, height)
        method: OpenCV matching method
        search_step: Sliding window step (seconds)
        max_windows: Maximum windows to test
        resize: Target frame size
    """

    def configure(self, **params):
        """Configure algorithm parameters."""
        self.threshold = params.get('threshold', 80.0)
        self.num_templates = params.get('num_templates', 5)
        self.template_size = params.get('template_size', (64, 64))
        self.method_name = params.get('method', 'TM_CCOEFF_NORMED')
        self.search_step = params.get('search_step', 3.0)
        self.max_windows = params.get('max_windows', 150)
        self.resize = params.get('resize', (320, 240))

        # Get OpenCV method constant
        self.method = getattr(cv2, self.method_name, cv2.TM_CCOEFF_NORMED)

    def compare(
        self,
        short_video: str,
        long_video: str,
        start_time: float = 0.0,
        duration: float = None
    ) -> Dict[str, Any]:
        """
        Compare videos using template matching.

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

        # Extract templates from short video
        templates = self._extract_templates(short_video, duration)

        if len(templates) < 2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Insufficient templates',
                    'num_templates': len(templates)
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
                duration,
                templates
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
                'num_templates': len(templates),
                'windows_tested': len(window_starts),
                'score_percentage': best_score,
                'template_size': self.template_size
            }
        }

    def _extract_templates(
        self,
        video_path: str,
        duration: float
    ) -> List[np.ndarray]:
        """
        Extract templates from video.

        Args:
            video_path: Path to video
            duration: Duration to analyze

        Returns:
            List of template images
        """
        sample_interval = max(1.0, duration / self.num_templates)
        offsets = [i * sample_interval for i in range(self.num_templates)]

        templates = []

        with VideoLoader(video_path) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Resize frame
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Extract template from center
                h, w = gray.shape
                tw, th = self.template_size

                # Calculate center crop
                start_y = max(0, (h - th) // 2)
                start_x = max(0, (w - tw) // 2)
                end_y = min(h, start_y + th)
                end_x = min(w, start_x + tw)

                template = gray[start_y:end_y, start_x:end_x]

                # Resize to exact template size if needed
                if template.shape != (th, tw):
                    template = cv2.resize(template, self.template_size)

                templates.append(template)

        return templates

    def _compare_window(
        self,
        long_video: str,
        window_start: float,
        duration: float,
        templates: List[np.ndarray]
    ) -> float:
        """
        Compare templates at a window position.

        Args:
            long_video: Path to long video
            window_start: Window start position
            duration: Window duration
            templates: Templates from short video

        Returns:
            Average matching score (0-100)
        """
        # Sample 10 frames from this window
        num_frames = 10
        sample_interval = duration / num_frames
        offsets = [window_start + i * sample_interval for i in range(num_frames)]

        all_scores = []

        with VideoLoader(long_video) as loader:
            for offset in offsets:
                frame = loader.get_frame(offset)
                if frame is None:
                    continue

                # Resize frame
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Match each template
                for template in templates:
                    try:
                        # Perform template matching
                        result = cv2.matchTemplate(gray, template, self.method)

                        # Get best match score
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                        # Normalize score to 0-1
                        if self.method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                            # For these methods, lower is better
                            score = 1.0 - min_val
                        else:
                            # For other methods, higher is better
                            score = max_val

                        all_scores.append(max(0.0, min(1.0, score)))

                    except Exception:
                        continue

        if not all_scores:
            return 0.0

        return float(np.mean(all_scores) * 100.0)

    def extract_features(self, video_path: str) -> List[np.ndarray]:
        """
        Extract template images from entire video.

        Args:
            video_path: Path to video

        Returns:
            List of template images
        """
        with VideoLoader(video_path) as loader:
            duration = loader.duration

        # Extract templates from entire video
        templates = self._extract_templates(video_path, duration)

        return templates

    def get_cli_params(self):
        """Return CLI parameters."""
        return [
            {
                'names': ['--template-num-templates'],
                'type': 'int',
                'default': 5,
                'help': 'Number of templates to extract'
            },
            {
                'names': ['--template-size'],
                'type': 'str',
                'default': '64,64',
                'help': 'Template size (width,height)'
            },
            {
                'names': ['--template-method'],
                'type': 'str',
                'default': 'TM_CCOEFF_NORMED',
                'help': 'OpenCV matching method'
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
        Compare two sets of template images using template matching.

        Args:
            features1: List of templates from first video
            features2: List of templates from second video
            threshold: Minimum similarity score (0-100)
            params: Optional parameters (method)

        Returns:
            Dictionary with similarity, accepted, and metadata
        """
        if not features1 or not features2:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'Empty feature sets',
                    'num_templates_1': len(features1),
                    'num_templates_2': len(features2)
                }
            }

        # Get matching method
        method_name = params.get('method', 'TM_CCOEFF_NORMED') if params else 'TM_CCOEFF_NORMED'
        method = getattr(cv2, method_name, cv2.TM_CCOEFF_NORMED)

        # Compare each template from features1 with each image from features2
        all_scores = []

        for template in features1:
            for image in features2:
                try:
                    # Perform template matching
                    result = cv2.matchTemplate(image, template, method)

                    # Get best match score
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                    # Normalize score to 0-1
                    if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                        # For these methods, lower is better
                        score = 1.0 - min_val
                    else:
                        # For other methods, higher is better
                        score = max_val

                    all_scores.append(max(0.0, min(1.0, score)) * 100.0)

                except Exception:
                    # If template matching fails (size issues), try reverse
                    try:
                        result = cv2.matchTemplate(template, image, method)
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                        if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                            score = 1.0 - min_val
                        else:
                            score = max_val

                        all_scores.append(max(0.0, min(1.0, score)) * 100.0)
                    except:
                        continue

        if not all_scores:
            return {
                'similarity': 0.0,
                'accepted': False,
                'metadata': {
                    'error': 'No valid comparisons',
                    'num_templates_1': len(features1),
                    'num_templates_2': len(features2)
                }
            }

        # Average similarity
        avg_similarity = float(np.mean(all_scores))

        return {
            'similarity': avg_similarity,
            'accepted': avg_similarity >= threshold,
            'metadata': {
                'num_templates_1': len(features1),
                'num_templates_2': len(features2),
                'num_comparisons': len(all_scores),
                'min_similarity': float(np.min(all_scores)),
                'max_similarity': float(np.max(all_scores)),
                'method': method_name
            }
        }
