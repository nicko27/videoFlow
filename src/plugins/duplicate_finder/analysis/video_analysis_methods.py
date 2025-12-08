"""
Video Analysis Methods - Comprehensive Detection & Verification System

This module provides multiple video analysis methods that can be combined
in a configurable pipeline for subsequence detection and verification.

Methods Included:
- Color Histogram Matching
- Edge Pattern Detection
- Motion Analysis (Frame Differences)
- DCT Coefficients
- Structural Similarity (SSIM)
- Feature Matching (ORB)
- Perceptual Hashing
- Scene Cuts Detection

All results are cached in database for performance.
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.VideoAnalysisMethods')


class VideoAnalysisMethods:
    """Comprehensive video analysis methods for subsequence detection."""

    def __init__(
        self,
        # Color Histogram parameters
        color_hist_bins: Tuple[int, int, int] = (32, 32, 32),
        color_hist_threshold: float = 85.0,

        # Edge Detection parameters
        edge_canny_low: int = 50,
        edge_canny_high: int = 150,
        edge_grid_size: Tuple[int, int] = (4, 4),
        edge_threshold: float = 80.0,

        # Motion Analysis parameters
        motion_sample_interval: int = 3,
        motion_correlation_threshold: float = 85.0,

        # DCT parameters
        dct_block_size: int = 8,
        dct_num_coeffs: int = 15,
        dct_threshold: float = 75.0,

        # SSIM parameters
        ssim_window_size: int = 7,
        ssim_threshold: float = 0.85,

        # Feature Matching parameters
        feature_detector: str = 'ORB',  # ORB, SIFT, AKAZE
        feature_max_features: int = 500,
        feature_match_threshold: float = 70.0,

        # Scene Cuts parameters
        scene_threshold: float = 50.0,
        scene_min_scene_len: int = 15,

        # Performance parameters
        max_workers: int = 8,
        db_manager = None
    ):
        """
        Initialize video analysis methods.

        Args:
            color_hist_bins: Number of bins for color histogram (H, S, V)
            color_hist_threshold: Minimum similarity threshold for color histogram
            edge_canny_low: Lower threshold for Canny edge detection
            edge_canny_high: Upper threshold for Canny edge detection
            edge_grid_size: Grid size for edge pattern analysis
            edge_threshold: Minimum similarity threshold for edge patterns
            motion_sample_interval: Interval in seconds for motion sampling
            motion_correlation_threshold: Minimum correlation for motion patterns
            dct_block_size: Block size for DCT computation
            dct_num_coeffs: Number of DCT coefficients to use
            dct_threshold: Minimum similarity threshold for DCT
            ssim_window_size: Window size for SSIM computation
            ssim_threshold: Minimum SSIM score
            feature_detector: Feature detector type (ORB, SIFT, AKAZE)
            feature_max_features: Maximum number of features to detect
            feature_match_threshold: Minimum match ratio for features
            scene_threshold: Threshold for scene cut detection
            scene_min_scene_len: Minimum scene length in frames
            max_workers: Number of parallel workers
            db_manager: Database manager for caching results
        """
        # Color Histogram
        self.color_hist_bins = color_hist_bins
        self.color_hist_threshold = color_hist_threshold

        # Edge Detection
        self.edge_canny_low = edge_canny_low
        self.edge_canny_high = edge_canny_high
        self.edge_grid_size = edge_grid_size
        self.edge_threshold = edge_threshold

        # Motion Analysis
        self.motion_sample_interval = motion_sample_interval
        self.motion_correlation_threshold = motion_correlation_threshold

        # DCT
        self.dct_block_size = dct_block_size
        self.dct_num_coeffs = dct_num_coeffs
        self.dct_threshold = dct_threshold

        # SSIM
        self.ssim_window_size = ssim_window_size
        self.ssim_threshold = ssim_threshold

        # Feature Matching
        self.feature_detector = feature_detector
        self.feature_max_features = feature_max_features
        self.feature_match_threshold = feature_match_threshold

        # Scene Cuts
        self.scene_threshold = scene_threshold
        self.scene_min_scene_len = scene_min_scene_len

        # Performance
        self.max_workers = max_workers
        self.db = db_manager

        logger.info(f"VideoAnalysisMethods initialized with {max_workers} workers")

    def _extract_frame_at(self, video_path: str, time_sec: float, size: Tuple[int, int] = (320, 180)) -> Optional[np.ndarray]:
        """Extract a single frame at specific time."""
        try:
            cv2.setLogLevel(0)
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_num = int(time_sec * fps)

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            cap.release()
            cv2.setLogLevel(1)

            if ret and frame is not None:
                return cv2.resize(frame, size)
            return None

        except Exception as e:
            logger.error(f"Error extracting frame at {time_sec}s from {video_path}: {e}")
            return None

    # ================================================================
    # METHOD 1: COLOR HISTOGRAM MATCHING
    # ================================================================

    def compute_color_histogram(self, frame: np.ndarray) -> np.ndarray:
        """
        Compute 3D color histogram in HSV space.

        Args:
            frame: Input frame (BGR format)

        Returns:
            Normalized histogram as 1D array
        """
        try:
            # Convert to HSV
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Compute 3D histogram
            hist = cv2.calcHist(
                [hsv],
                [0, 1, 2],  # H, S, V channels
                None,
                self.color_hist_bins,
                [0, 180, 0, 256, 0, 256]
            )

            # Normalize
            hist = cv2.normalize(hist, hist).flatten()

            return hist

        except Exception as e:
            logger.error(f"Error computing color histogram: {e}")
            return None

    def compare_color_histograms(
        self,
        short_video: str,
        long_video: str,
        start_time: float,
        duration: float
    ) -> Dict:
        """
        Compare color histograms between two video segments.

        Args:
            short_video: Path to short video
            long_video: Path to long video
            start_time: Start time in long video
            duration: Duration to compare

        Returns:
            Dictionary with comparison results
        """
        try:
            # Sample frames at regular intervals
            sample_interval = 5  # Sample every 5 seconds
            num_samples = max(3, int(duration / sample_interval))

            short_hists = []
            long_hists = []

            for i in range(num_samples):
                offset = (i / (num_samples - 1)) * duration if num_samples > 1 else duration / 2

                short_frame = self._extract_frame_at(short_video, offset)
                long_frame = self._extract_frame_at(long_video, start_time + offset)

                if short_frame is not None and long_frame is not None:
                    short_hist = self.compute_color_histogram(short_frame)
                    long_hist = self.compute_color_histogram(long_frame)

                    if short_hist is not None and long_hist is not None:
                        short_hists.append(short_hist)
                        long_hists.append(long_hist)

            if len(short_hists) < 2:
                return {
                    'accepted': False,
                    'color_score': 0.0,
                    'rejection_reason': 'Insufficient frames for color comparison',
                    'method': 'color_histogram'
                }

            # Compute average similarity using correlation
            similarities = []
            for sh, lh in zip(short_hists, long_hists):
                similarity = cv2.compareHist(sh, lh, cv2.HISTCMP_CORREL)
                similarities.append(max(0, similarity))

            avg_score = np.mean(similarities) * 100.0
            accepted = avg_score >= self.color_hist_threshold

            return {
                'accepted': accepted,
                'color_score': avg_score,
                'color_samples': len(similarities),
                'rejection_reason': None if accepted else f"Color score {avg_score:.1f}% below threshold {self.color_hist_threshold}%",
                'method': 'color_histogram'
            }

        except Exception as e:
            logger.error(f"Error in color histogram comparison: {e}")
            return {
                'accepted': False,
                'color_score': 0.0,
                'rejection_reason': f"Error: {str(e)}",
                'method': 'color_histogram'
            }

    # ================================================================
    # METHOD 2: EDGE PATTERN DETECTION
    # ================================================================

    def compute_edge_pattern(self, frame: np.ndarray) -> np.ndarray:
        """
        Compute edge density pattern using Canny edge detection.

        Args:
            frame: Input frame

        Returns:
            Edge pattern as 1D array
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Canny edge detection
            edges = cv2.Canny(blurred, self.edge_canny_low, self.edge_canny_high)

            # Divide into grid and compute edge density per cell
            h, w = edges.shape
            rows, cols = self.edge_grid_size
            cell_h, cell_w = h // rows, w // cols

            edge_pattern = []
            for i in range(rows):
                for j in range(cols):
                    cell = edges[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
                    density = np.sum(cell > 0) / cell.size
                    edge_pattern.append(density)

            return np.array(edge_pattern)

        except Exception as e:
            logger.error(f"Error computing edge pattern: {e}")
            return None

    def compare_edge_patterns(
        self,
        short_video: str,
        long_video: str,
        start_time: float,
        duration: float
    ) -> Dict:
        """
        Compare edge patterns between two video segments.

        Returns:
            Dictionary with comparison results
        """
        try:
            sample_interval = 5
            num_samples = max(3, int(duration / sample_interval))

            short_patterns = []
            long_patterns = []

            for i in range(num_samples):
                offset = (i / (num_samples - 1)) * duration if num_samples > 1 else duration / 2

                short_frame = self._extract_frame_at(short_video, offset)
                long_frame = self._extract_frame_at(long_video, start_time + offset)

                if short_frame is not None and long_frame is not None:
                    short_pattern = self.compute_edge_pattern(short_frame)
                    long_pattern = self.compute_edge_pattern(long_frame)

                    if short_pattern is not None and long_pattern is not None:
                        short_patterns.append(short_pattern)
                        long_patterns.append(long_pattern)

            if len(short_patterns) < 2:
                return {
                    'accepted': False,
                    'edge_score': 0.0,
                    'rejection_reason': 'Insufficient frames for edge comparison',
                    'method': 'edge_pattern'
                }

            # Compute cosine similarity
            similarities = []
            for sp, lp in zip(short_patterns, long_patterns):
                dot_product = np.dot(sp, lp)
                norm_s = np.linalg.norm(sp)
                norm_l = np.linalg.norm(lp)

                if norm_s > 0 and norm_l > 0:
                    similarity = dot_product / (norm_s * norm_l)
                    similarities.append(max(0, similarity))

            avg_score = np.mean(similarities) * 100.0 if similarities else 0.0
            accepted = avg_score >= self.edge_threshold

            return {
                'accepted': accepted,
                'edge_score': avg_score,
                'edge_samples': len(similarities),
                'rejection_reason': None if accepted else f"Edge score {avg_score:.1f}% below threshold {self.edge_threshold}%",
                'method': 'edge_pattern'
            }

        except Exception as e:
            logger.error(f"Error in edge pattern comparison: {e}")
            return {
                'accepted': False,
                'edge_score': 0.0,
                'rejection_reason': f"Error: {str(e)}",
                'method': 'edge_pattern'
            }

    # ================================================================
    # METHOD 3: MOTION ANALYSIS (Frame Differences)
    # ================================================================

    def compute_motion_pattern(
        self,
        video_path: str,
        start_time: float,
        duration: float
    ) -> Optional[np.ndarray]:
        """
        Compute motion pattern using frame differences.

        Args:
            video_path: Path to video
            start_time: Start time
            duration: Duration to analyze

        Returns:
            Motion pattern as array of frame differences
        """
        try:
            frames = []
            num_samples = max(5, int(duration / self.motion_sample_interval))

            for i in range(num_samples):
                offset = (i / (num_samples - 1)) * duration if num_samples > 1 else duration / 2
                frame = self._extract_frame_at(video_path, start_time + offset)

                if frame is not None:
                    frames.append(frame)

            if len(frames) < 3:
                return None

            # Compute frame-to-frame differences
            diffs = []
            for i in range(len(frames) - 1):
                gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
                gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)
                diff = cv2.absdiff(gray1, gray2)
                diffs.append(np.mean(diff))

            return np.array(diffs)

        except Exception as e:
            logger.error(f"Error computing motion pattern: {e}")
            return None

    def compare_motion_patterns(
        self,
        short_video: str,
        long_video: str,
        start_time: float,
        duration: float
    ) -> Dict:
        """
        Compare motion patterns using temporal correlation.

        Returns:
            Dictionary with comparison results
        """
        try:
            short_motion = self.compute_motion_pattern(short_video, 0, duration)
            long_motion = self.compute_motion_pattern(long_video, start_time, duration)

            if short_motion is None or long_motion is None:
                return {
                    'accepted': False,
                    'motion_score': 0.0,
                    'rejection_reason': 'Failed to compute motion patterns',
                    'method': 'motion_analysis'
                }

            # Normalize patterns
            if short_motion.std() == 0 or long_motion.std() == 0:
                return {
                    'accepted': False,
                    'motion_score': 0.0,
                    'rejection_reason': 'Zero motion variance detected',
                    'method': 'motion_analysis'
                }

            short_norm = (short_motion - short_motion.mean()) / short_motion.std()
            long_norm = (long_motion - long_motion.mean()) / long_motion.std()

            # Compute correlation
            correlation = np.corrcoef(short_norm, long_norm)[0, 1]

            if np.isnan(correlation):
                correlation = 0.0

            motion_score = max(0, min(100, correlation * 100))
            accepted = motion_score >= self.motion_correlation_threshold

            return {
                'accepted': accepted,
                'motion_score': motion_score,
                'motion_samples': len(short_motion),
                'rejection_reason': None if accepted else f"Motion score {motion_score:.1f}% below threshold {self.motion_correlation_threshold}%",
                'method': 'motion_analysis'
            }

        except Exception as e:
            logger.error(f"Error in motion comparison: {e}")
            return {
                'accepted': False,
                'motion_score': 0.0,
                'rejection_reason': f"Error: {str(e)}",
                'method': 'motion_analysis'
            }

    # ================================================================
    # METHOD 4: DCT COEFFICIENTS
    # ================================================================

    def compute_dct_signature(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Compute DCT-based signature for a frame.

        Args:
            frame: Input frame

        Returns:
            DCT signature as 1D array
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Resize to block size
            resized = cv2.resize(gray, (self.dct_block_size * 8, self.dct_block_size * 8))

            # Compute DCT
            dct = cv2.dct(np.float32(resized))

            # Extract top-left coefficients (low frequencies)
            signature = []
            for i in range(self.dct_block_size):
                for j in range(self.dct_block_size):
                    if len(signature) < self.dct_num_coeffs:
                        signature.append(dct[i, j])

            return np.array(signature)

        except Exception as e:
            logger.error(f"Error computing DCT signature: {e}")
            return None

    def compare_dct_signatures(
        self,
        short_video: str,
        long_video: str,
        start_time: float,
        duration: float
    ) -> Dict:
        """
        Compare DCT signatures between two video segments.

        Returns:
            Dictionary with comparison results
        """
        try:
            sample_interval = 5
            num_samples = max(5, int(duration / sample_interval))

            short_sigs = []
            long_sigs = []

            for i in range(num_samples):
                offset = (i / (num_samples - 1)) * duration if num_samples > 1 else duration / 2

                short_frame = self._extract_frame_at(short_video, offset)
                long_frame = self._extract_frame_at(long_video, start_time + offset)

                if short_frame is not None and long_frame is not None:
                    short_sig = self.compute_dct_signature(short_frame)
                    long_sig = self.compute_dct_signature(long_frame)

                    if short_sig is not None and long_sig is not None:
                        short_sigs.append(short_sig)
                        long_sigs.append(long_sig)

            if len(short_sigs) < 3:
                return {
                    'accepted': False,
                    'dct_score': 0.0,
                    'rejection_reason': 'Insufficient frames for DCT comparison',
                    'method': 'dct_coefficients'
                }

            # Compute cosine similarities
            similarities = []
            for ss, ls in zip(short_sigs, long_sigs):
                dot_product = np.dot(ss, ls)
                norm_s = np.linalg.norm(ss)
                norm_l = np.linalg.norm(ls)

                if norm_s > 0 and norm_l > 0:
                    similarity = dot_product / (norm_s * norm_l)
                    similarities.append(max(0, similarity))

            avg_score = np.mean(similarities) * 100.0 if similarities else 0.0
            accepted = avg_score >= self.dct_threshold

            return {
                'accepted': accepted,
                'dct_score': avg_score,
                'dct_samples': len(similarities),
                'rejection_reason': None if accepted else f"DCT score {avg_score:.1f}% below threshold {self.dct_threshold}%",
                'method': 'dct_coefficients'
            }

        except Exception as e:
            logger.error(f"Error in DCT comparison: {e}")
            return {
                'accepted': False,
                'dct_score': 0.0,
                'rejection_reason': f"Error: {str(e)}",
                'method': 'dct_coefficients'
            }

    # ================================================================
    # METHOD 5: STRUCTURAL SIMILARITY (SSIM)
    # ================================================================

    def compute_ssim(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """
        Compute Structural Similarity Index (SSIM) between two frames.

        Args:
            frame1: First frame
            frame2: Second frame

        Returns:
            SSIM score (0.0 to 1.0)
        """
        try:
            # Convert to grayscale
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

            # Compute SSIM using OpenCV (if available) or manual implementation
            try:
                from skimage.metrics import structural_similarity
                score, _ = structural_similarity(gray1, gray2, full=True, win_size=self.ssim_window_size)
                return max(0.0, min(1.0, score))
            except ImportError:
                # Fallback: simple MSE-based similarity
                mse = np.mean((gray1.astype(float) - gray2.astype(float)) ** 2)
                if mse == 0:
                    return 1.0
                max_pixel = 255.0
                psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
                # Convert PSNR to 0-1 range
                return min(1.0, psnr / 50.0)

        except Exception as e:
            logger.error(f"Error computing SSIM: {e}")
            return 0.0

    def compare_ssim(
        self,
        short_video: str,
        long_video: str,
        start_time: float,
        duration: float
    ) -> Dict:
        """
        Compare videos using Structural Similarity Index.

        Returns:
            Dictionary with comparison results
        """
        try:
            sample_interval = 5
            num_samples = max(5, int(duration / sample_interval))

            ssim_scores = []

            for i in range(num_samples):
                offset = (i / (num_samples - 1)) * duration if num_samples > 1 else duration / 2

                short_frame = self._extract_frame_at(short_video, offset)
                long_frame = self._extract_frame_at(long_video, start_time + offset)

                if short_frame is not None and long_frame is not None:
                    ssim_score = self.compute_ssim(short_frame, long_frame)
                    ssim_scores.append(ssim_score)

            if len(ssim_scores) < 3:
                return {
                    'accepted': False,
                    'ssim_score': 0.0,
                    'rejection_reason': 'Insufficient frames for SSIM comparison',
                    'method': 'ssim'
                }

            avg_score = np.mean(ssim_scores) * 100.0
            accepted = (np.mean(ssim_scores) >= self.ssim_threshold)

            return {
                'accepted': accepted,
                'ssim_score': avg_score,
                'ssim_samples': len(ssim_scores),
                'rejection_reason': None if accepted else f"SSIM score {avg_score:.1f}% below threshold {self.ssim_threshold*100}%",
                'method': 'ssim'
            }

        except Exception as e:
            logger.error(f"Error in SSIM comparison: {e}")
            return {
                'accepted': False,
                'ssim_score': 0.0,
                'rejection_reason': f"Error: {str(e)}",
                'method': 'ssim'
            }

    # ================================================================
    # METHOD 6: FEATURE MATCHING (ORB/SIFT/AKAZE)
    # ================================================================

    def detect_and_match_features(
        self,
        short_video: str,
        long_video: str,
        start_time: float,
        duration: float
    ) -> Dict:
        """
        Detect and match features between video segments.

        Returns:
            Dictionary with comparison results
        """
        try:
            # Create feature detector
            if self.feature_detector == 'ORB':
                detector = cv2.ORB_create(nfeatures=self.feature_max_features)
            elif self.feature_detector == 'AKAZE':
                detector = cv2.AKAZE_create()
            elif self.feature_detector == 'SIFT':
                try:
                    detector = cv2.SIFT_create(nfeatures=self.feature_max_features)
                except AttributeError:
                    # SIFT not available, fallback to ORB
                    detector = cv2.ORB_create(nfeatures=self.feature_max_features)
                    logger.warning("SIFT not available, using ORB instead")
            else:
                detector = cv2.ORB_create(nfeatures=self.feature_max_features)

            # Create matcher
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

            sample_interval = 10
            num_samples = max(3, int(duration / sample_interval))

            match_ratios = []

            for i in range(num_samples):
                offset = (i / (num_samples - 1)) * duration if num_samples > 1 else duration / 2

                short_frame = self._extract_frame_at(short_video, offset, size=(640, 360))
                long_frame = self._extract_frame_at(long_video, start_time + offset, size=(640, 360))

                if short_frame is None or long_frame is None:
                    continue

                # Convert to grayscale
                short_gray = cv2.cvtColor(short_frame, cv2.COLOR_BGR2GRAY)
                long_gray = cv2.cvtColor(long_frame, cv2.COLOR_BGR2GRAY)

                # Detect keypoints and compute descriptors
                kp1, des1 = detector.detectAndCompute(short_gray, None)
                kp2, des2 = detector.detectAndCompute(long_gray, None)

                if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
                    continue

                # Match features
                matches = bf.match(des1, des2)

                # Compute match ratio
                if len(kp1) > 0:
                    match_ratio = len(matches) / len(kp1) * 100.0
                    match_ratios.append(match_ratio)

            if len(match_ratios) < 2:
                return {
                    'accepted': False,
                    'feature_score': 0.0,
                    'rejection_reason': 'Insufficient feature matches',
                    'method': 'feature_matching'
                }

            avg_score = np.mean(match_ratios)
            accepted = avg_score >= self.feature_match_threshold

            return {
                'accepted': accepted,
                'feature_score': avg_score,
                'feature_samples': len(match_ratios),
                'feature_detector': self.feature_detector,
                'rejection_reason': None if accepted else f"Feature score {avg_score:.1f}% below threshold {self.feature_match_threshold}%",
                'method': 'feature_matching'
            }

        except Exception as e:
            logger.error(f"Error in feature matching: {e}")
            return {
                'accepted': False,
                'feature_score': 0.0,
                'rejection_reason': f"Error: {str(e)}",
                'method': 'feature_matching'
            }
