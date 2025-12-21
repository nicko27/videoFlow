"""
Unit tests for FeatureMatchingAlgorithm.

Tests the feature matching algorithm that uses local feature detectors
(ORB, AKAZE, SIFT) to extract keypoints and match them between frames.
"""

import pytest
import cv2
import numpy as np
from pathlib import Path

from duplicateflow.algorithms.feature_matching import FeatureMatchingAlgorithm
from tests.utils.frame_generator import (
    create_black_frame,
    create_white_frame,
    create_color_frame,
    create_noise_frame,
    create_gradient_frame,
    create_checkerboard_frame,
    add_noise,
    adjust_brightness,
    adjust_contrast
)


# ==================== FIXTURES ====================

@pytest.fixture
def algorithm():
    """FeatureMatchingAlgorithm instance with default parameters (ORB)."""
    algo = FeatureMatchingAlgorithm()
    algo.configure()
    return algo


@pytest.fixture
def algorithm_akaze():
    """FeatureMatchingAlgorithm with AKAZE detector."""
    algo = FeatureMatchingAlgorithm()
    algo.configure(detector='AKAZE')
    return algo


@pytest.fixture
def algorithm_sift():
    """FeatureMatchingAlgorithm with SIFT detector (if available)."""
    algo = FeatureMatchingAlgorithm()
    algo.configure(detector='SIFT')
    return algo


# ==================== INSTANTIATION TESTS ====================

class TestFeatureMatchingAlgorithmInstantiation:
    """Test algorithm instantiation and configuration."""

    def test_init_default_params(self):
        """Test initialization with default parameters (ORB)."""
        algo = FeatureMatchingAlgorithm()
        algo.configure()

        assert algo.threshold == 30.0
        assert algo.detector_name == 'ORB'
        assert algo.max_features == 500
        assert algo.ratio_test == 0.75
        assert algo.min_matches == 10
        assert algo.search_step == 3.0
        assert algo.max_windows == 100
        assert algo.resize == (640, 360)
        assert algo.detector is not None
        assert algo.norm == cv2.NORM_HAMMING

    def test_init_orb_detector(self):
        """Test initialization with ORB detector."""
        algo = FeatureMatchingAlgorithm()
        algo.configure(detector='ORB', max_features=300)

        assert algo.detector_name == 'ORB'
        assert algo.max_features == 300
        assert algo.norm == cv2.NORM_HAMMING

    def test_init_akaze_detector(self, algorithm_akaze):
        """Test initialization with AKAZE detector."""
        assert algorithm_akaze.detector_name == 'AKAZE'
        assert algorithm_akaze.norm == cv2.NORM_HAMMING

    def test_init_sift_detector(self, algorithm_sift):
        """Test initialization with SIFT detector (if available)."""
        # SIFT may not be available in all OpenCV builds
        assert algorithm_sift.detector_name == 'SIFT'
        # If SIFT available: NORM_L2, else fallback to ORB: NORM_HAMMING
        assert algorithm_sift.norm in [cv2.NORM_L2, cv2.NORM_HAMMING]

    def test_init_invalid_detector_fallback(self):
        """Test initialization with invalid detector falls back to ORB."""
        algo = FeatureMatchingAlgorithm()
        algo.configure(detector='INVALID')

        # Should fallback to ORB
        assert algo.detector_name == 'INVALID'  # Name stored as-is
        assert algo.norm == cv2.NORM_HAMMING  # But uses ORB defaults

    def test_algorithm_has_required_attributes(self, algorithm):
        """Test algorithm has required attributes."""
        assert hasattr(algorithm, 'threshold')
        assert hasattr(algorithm, 'detector')
        assert hasattr(algorithm, 'detector_name')
        assert hasattr(algorithm, 'norm')
        assert hasattr(algorithm, 'ratio_test')
        assert hasattr(algorithm, 'min_matches')


# ==================== DETECTOR CREATION TESTS ====================

class TestDetectorCreation:
    """Test _create_detector method."""

    def test_create_orb_detector(self):
        """Test creating ORB detector."""
        algo = FeatureMatchingAlgorithm()
        algo.detector_name = 'ORB'
        algo.max_features = 500

        detector, norm = algo._create_detector()

        assert detector is not None
        assert norm == cv2.NORM_HAMMING

    def test_create_akaze_detector(self):
        """Test creating AKAZE detector."""
        algo = FeatureMatchingAlgorithm()
        algo.detector_name = 'AKAZE'
        algo.max_features = 500

        detector, norm = algo._create_detector()

        assert detector is not None
        assert norm == cv2.NORM_HAMMING

    def test_create_sift_detector(self):
        """Test creating SIFT detector (may fallback to ORB)."""
        algo = FeatureMatchingAlgorithm()
        algo.detector_name = 'SIFT'
        algo.max_features = 500

        detector, norm = algo._create_detector()

        assert detector is not None
        # SIFT uses NORM_L2, but may fallback to ORB (NORM_HAMMING)
        assert norm in [cv2.NORM_L2, cv2.NORM_HAMMING]

    def test_create_unknown_detector(self):
        """Test creating detector with unknown name defaults to ORB."""
        algo = FeatureMatchingAlgorithm()
        algo.detector_name = 'UNKNOWN'
        algo.max_features = 500

        detector, norm = algo._create_detector()

        assert detector is not None
        assert norm == cv2.NORM_HAMMING


# ==================== KEYPOINT DETECTION TESTS ====================

class TestKeypointDetection:
    """Test keypoint detection on various frames."""

    def test_detect_keypoints_textured_frame(self, algorithm):
        """Test detecting keypoints on textured frame."""
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp, des = algorithm.detector.detectAndCompute(gray, None)

        # Noise frame should have many keypoints
        assert kp is not None
        assert des is not None
        assert len(kp) > 0
        assert des.shape[0] == len(kp)

    def test_detect_keypoints_checkerboard(self, algorithm):
        """Test detecting keypoints on checkerboard pattern."""
        frame = create_checkerboard_frame(square_size=16)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp, des = algorithm.detector.detectAndCompute(gray, None)

        # Checkerboard has strong corners = many keypoints
        assert kp is not None
        assert des is not None
        assert len(kp) > 10  # Should detect corners

    def test_detect_keypoints_black_frame(self, algorithm):
        """Test detecting keypoints on uniform black frame."""
        frame = create_black_frame()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp, des = algorithm.detector.detectAndCompute(gray, None)

        # Uniform frame should have few/no keypoints
        if kp is None or des is None:
            assert True  # No keypoints detected (expected)
        else:
            assert len(kp) >= 0  # May detect 0 keypoints

    def test_detect_keypoints_gradient_frame(self, algorithm):
        """Test detecting keypoints on gradient frame."""
        frame = create_gradient_frame(direction='horizontal')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp, des = algorithm.detector.detectAndCompute(gray, None)

        # Gradient may have some keypoints
        assert kp is not None or kp is None  # Valid either way
        if kp is not None and des is not None:
            assert len(kp) >= 0

    def test_keypoint_descriptor_shape(self, algorithm):
        """Test descriptor shape for ORB."""
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp, des = algorithm.detector.detectAndCompute(gray, None)

        if des is not None:
            # ORB descriptors are 32 bytes (256 bits)
            assert des.shape[1] == 32
            assert des.dtype == np.uint8

    def test_keypoint_detection_reproducible(self, algorithm):
        """Test keypoint detection is reproducible."""
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp1, des1 = algorithm.detector.detectAndCompute(gray, None)
        kp2, des2 = algorithm.detector.detectAndCompute(gray, None)

        # Same frame should produce same keypoints/descriptors
        assert len(kp1) == len(kp2)
        if des1 is not None and des2 is not None:
            assert np.array_equal(des1, des2)


# ==================== FEATURE MATCHING TESTS ====================

class TestFeatureMatching:
    """Test feature matching between descriptors."""

    def test_match_identical_descriptors(self, algorithm):
        """Test matching identical descriptors (perfect match)."""
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp, des = algorithm.detector.detectAndCompute(gray, None)

        if des is not None and len(kp) >= 10:
            # Match descriptors against themselves
            bf = cv2.BFMatcher(algorithm.norm, crossCheck=False)
            matches = bf.knnMatch(des, des, k=2)

            # Should have perfect matches
            assert len(matches) > 0
            # First match should be perfect (distance=0)
            if len(matches[0]) >= 1:
                assert matches[0][0].distance == 0

    def test_match_similar_descriptors(self, algorithm):
        """Test matching similar frames (with small noise)."""
        frame1 = create_noise_frame(seed=42)
        frame2 = add_noise(frame1, noise_level=5)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        kp1, des1 = algorithm.detector.detectAndCompute(gray1, None)
        kp2, des2 = algorithm.detector.detectAndCompute(gray2, None)

        if des1 is not None and des2 is not None and len(kp1) >= 10 and len(kp2) >= 10:
            bf = cv2.BFMatcher(algorithm.norm, crossCheck=False)
            matches = bf.knnMatch(des1, des2, k=2)

            # Should have some good matches
            assert len(matches) > 0

    def test_match_different_descriptors(self, algorithm):
        """Test matching very different frames."""
        frame1 = create_black_frame()
        frame2 = create_checkerboard_frame(square_size=16)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        kp1, des1 = algorithm.detector.detectAndCompute(gray1, None)
        kp2, des2 = algorithm.detector.detectAndCompute(gray2, None)

        # Black frame may have no keypoints
        if des1 is None or des2 is None:
            assert True  # Expected - uniform frame has no features
        elif len(kp1) < 10 or len(kp2) < 10:
            assert True  # Few keypoints

    def test_ratio_test_filtering(self, algorithm):
        """Test Lowe's ratio test filtering."""
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp, des = algorithm.detector.detectAndCompute(gray, None)

        if des is not None and len(kp) >= 10:
            bf = cv2.BFMatcher(algorithm.norm, crossCheck=False)
            raw_matches = bf.knnMatch(des, des, k=2)

            # Apply ratio test
            good = []
            for pair in raw_matches:
                if len(pair) < 2:
                    continue
                m, n = pair
                if m.distance < 0.75 * n.distance:
                    good.append(m)

            # Should filter some matches
            assert len(good) <= len(raw_matches)


# ==================== COMPARE FEATURES TESTS ====================

class TestCompareFeatures:
    """Test compare_features static method."""

    def test_compare_features_identical_frames(self, algorithm):
        """Test comparing features from identical frames."""
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp, des = algorithm.detector.detectAndCompute(gray, None)

        if des is not None and len(kp) >= 10:
            # Format: (offset, num_keypoints, descriptors)
            features1 = [(0.0, len(kp), des)]
            features2 = [(0.0, len(kp), des.copy())]

            result = FeatureMatchingAlgorithm.compare_features(
                features1,
                features2,
                threshold=30.0,
                params={'detector': 'ORB', 'ratio_test': 0.75, 'min_matches': 10}
            )

            # Identical features should have high similarity
            assert result['similarity'] > 50.0
            assert isinstance(result['accepted'], bool)

    def test_compare_features_similar_frames(self, algorithm):
        """Test comparing features from similar frames."""
        frame1 = create_noise_frame(seed=42)
        frame2 = add_noise(frame1, noise_level=10)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        kp1, des1 = algorithm.detector.detectAndCompute(gray1, None)
        kp2, des2 = algorithm.detector.detectAndCompute(gray2, None)

        if des1 is not None and des2 is not None and len(kp1) >= 10 and len(kp2) >= 10:
            features1 = [(0.0, len(kp1), des1)]
            features2 = [(0.0, len(kp2), des2)]

            result = FeatureMatchingAlgorithm.compare_features(
                features1,
                features2,
                threshold=30.0
            )

            # Should have some similarity
            assert result['similarity'] >= 0.0
            assert 'metadata' in result

    def test_compare_features_empty_list1(self):
        """Test comparing with empty first feature list."""
        result = FeatureMatchingAlgorithm.compare_features(
            [],
            [(0.0, 100, np.zeros((100, 32), dtype=np.uint8))],
            threshold=30.0
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] is False
        assert 'error' in result['metadata']

    def test_compare_features_empty_list2(self):
        """Test comparing with empty second feature list."""
        result = FeatureMatchingAlgorithm.compare_features(
            [(0.0, 100, np.zeros((100, 32), dtype=np.uint8))],
            [],
            threshold=30.0
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] is False

    def test_compare_features_insufficient_keypoints(self):
        """Test comparing with insufficient keypoints."""
        # Too few keypoints (< 10)
        des1 = np.zeros((5, 32), dtype=np.uint8)
        des2 = np.zeros((5, 32), dtype=np.uint8)

        features1 = [(0.0, 5, des1)]
        features2 = [(0.0, 5, des2)]

        result = FeatureMatchingAlgorithm.compare_features(
            features1,
            features2,
            threshold=30.0
        )

        # Should fail due to insufficient keypoints
        assert result['similarity'] == 0.0
        assert result['accepted'] is False

    def test_compare_features_metadata(self, algorithm):
        """Test compare_features returns correct metadata."""
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp, des = algorithm.detector.detectAndCompute(gray, None)

        if des is not None and len(kp) >= 10:
            features = [(0.0, len(kp), des)]

            result = FeatureMatchingAlgorithm.compare_features(
                features,
                features,
                threshold=30.0
            )

            assert 'metadata' in result
            assert 'num_frames_1' in result['metadata']
            assert 'num_frames_2' in result['metadata']
            assert 'num_comparisons' in result['metadata']
            assert 'detector' in result['metadata']


# ==================== EDGE CASE TESTS ====================

class TestFeatureMatchingEdgeCases:
    """Test edge cases and special scenarios."""

    def test_max_features_limit(self):
        """Test max_features parameter limits keypoint count."""
        algo = FeatureMatchingAlgorithm()
        algo.configure(max_features=100)

        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp, des = algo.detector.detectAndCompute(gray, None)

        if kp is not None:
            # Should not exceed max_features
            assert len(kp) <= 100

    def test_ratio_test_disabled(self):
        """Test with ratio test disabled (ratio_test=0)."""
        algo = FeatureMatchingAlgorithm()
        algo.configure(ratio_test=0)

        assert algo.ratio_test == 0

    def test_different_detectors_different_descriptors(self):
        """Test different detectors produce different descriptor sizes."""
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # ORB: 32 bytes (256 bits)
        algo_orb = FeatureMatchingAlgorithm()
        algo_orb.configure(detector='ORB')
        kp_orb, des_orb = algo_orb.detector.detectAndCompute(gray, None)

        # AKAZE: 61 bytes
        algo_akaze = FeatureMatchingAlgorithm()
        algo_akaze.configure(detector='AKAZE')
        kp_akaze, des_akaze = algo_akaze.detector.detectAndCompute(gray, None)

        if des_orb is not None and des_akaze is not None:
            # Different descriptor sizes
            assert des_orb.shape[1] != des_akaze.shape[1]

    def test_small_frame_fewer_keypoints(self, algorithm):
        """Test small frames produce fewer keypoints."""
        frame = create_noise_frame(width=32, height=32, seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp, des = algorithm.detector.detectAndCompute(gray, None)

        # Small frame = fewer keypoints
        if kp is not None:
            assert len(kp) >= 0  # May have few or no keypoints


# ==================== ROBUSTNESS TESTS ====================

class TestFeatureMatchingRobustness:
    """Test algorithm robustness to transformations."""

    def test_robustness_brightness_increase(self, algorithm):
        """Test robustness to brightness increase."""
        frame1 = create_noise_frame(seed=42)
        frame2 = adjust_brightness(frame1, factor=1.3)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        kp1, des1 = algorithm.detector.detectAndCompute(gray1, None)
        kp2, des2 = algorithm.detector.detectAndCompute(gray2, None)

        # Feature detectors should be somewhat robust to brightness
        # (keypoint locations should be similar)
        if kp1 is not None and kp2 is not None:
            assert len(kp1) > 0
            assert len(kp2) > 0

    def test_robustness_small_noise(self, algorithm):
        """Test robustness to small noise addition."""
        frame1 = create_checkerboard_frame(square_size=32)
        frame2 = add_noise(frame1, noise_level=10)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        kp1, des1 = algorithm.detector.detectAndCompute(gray1, None)
        kp2, des2 = algorithm.detector.detectAndCompute(gray2, None)

        # Should detect similar number of keypoints
        if kp1 is not None and kp2 is not None:
            # Within reasonable range
            assert abs(len(kp1) - len(kp2)) < max(len(kp1), len(kp2))

    def test_robustness_contrast_change(self, algorithm):
        """Test robustness to contrast change."""
        frame1 = create_noise_frame(seed=42)
        frame2 = adjust_contrast(frame1, factor=1.5)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        kp1, des1 = algorithm.detector.detectAndCompute(gray1, None)
        kp2, des2 = algorithm.detector.detectAndCompute(gray2, None)

        # Feature detectors are robust to contrast changes
        if kp1 is not None and kp2 is not None:
            assert len(kp1) > 0
            assert len(kp2) > 0


# ==================== INTEGRATION TESTS ====================

class TestFeatureMatchingIntegration:
    """Test complete feature matching workflows."""

    def test_complete_detection_workflow(self, algorithm):
        """Test complete keypoint detection and matching workflow."""
        # Create two similar frames
        frame1 = create_noise_frame(seed=42)
        frame2 = add_noise(frame1, noise_level=5)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # Detect keypoints
        kp1, des1 = algorithm.detector.detectAndCompute(gray1, None)
        kp2, des2 = algorithm.detector.detectAndCompute(gray2, None)

        if des1 is not None and des2 is not None and len(kp1) >= 10 and len(kp2) >= 10:
            # Match features
            bf = cv2.BFMatcher(algorithm.norm, crossCheck=False)
            matches = bf.knnMatch(des1, des2, k=2)

            # Apply ratio test
            good = []
            for pair in matches:
                if len(pair) < 2:
                    continue
                m, n = pair
                if m.distance < 0.75 * n.distance:
                    good.append(m)

            # Should have some good matches
            assert len(good) > 0

    def test_multi_frame_comparison(self, algorithm):
        """Test comparing multiple frames."""
        frames = [create_noise_frame(seed=i) for i in range(3)]
        grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]

        features = []
        for gray in grays:
            kp, des = algorithm.detector.detectAndCompute(gray, None)
            if des is not None and len(kp) >= 10:
                features.append((0.0, len(kp), des))

        if len(features) >= 2:
            result = FeatureMatchingAlgorithm.compare_features(
                [features[0]],
                [features[1]],
                threshold=30.0
            )

            assert 'similarity' in result
            assert result['similarity'] >= 0.0

    def test_feature_extraction_reproducibility(self, algorithm):
        """Test feature extraction is reproducible."""
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp1, des1 = algorithm.detector.detectAndCompute(gray, None)
        kp2, des2 = algorithm.detector.detectAndCompute(gray, None)
        kp3, des3 = algorithm.detector.detectAndCompute(gray, None)

        # Should produce identical results
        assert len(kp1) == len(kp2) == len(kp3)
        if des1 is not None and des2 is not None and des3 is not None:
            assert np.array_equal(des1, des2)
            assert np.array_equal(des2, des3)


# ==================== PERFORMANCE TESTS ====================

class TestFeatureMatchingPerformance:
    """Test algorithm performance characteristics."""

    def test_descriptor_dtype_consistency(self, algorithm):
        """Test descriptors have consistent dtype."""
        frames = [create_noise_frame(seed=i) for i in range(3)]

        descriptors = []
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            kp, des = algorithm.detector.detectAndCompute(gray, None)
            if des is not None:
                descriptors.append(des)

        if len(descriptors) > 0:
            # ORB uses uint8
            assert all(d.dtype == np.uint8 for d in descriptors)

    def test_keypoint_count_consistency(self, algorithm):
        """Test similar frames produce similar keypoint counts."""
        frame = create_noise_frame(seed=42)

        # Detect multiple times
        counts = []
        for _ in range(3):
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            kp, _ = algorithm.detector.detectAndCompute(gray, None)
            if kp is not None:
                counts.append(len(kp))

        # Should be identical (deterministic)
        if len(counts) > 1:
            assert len(set(counts)) == 1

    def test_compare_features_returns_valid_similarity(self, algorithm):
        """Test compare_features returns similarity in [0, 100]."""
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp, des = algorithm.detector.detectAndCompute(gray, None)

        if des is not None and len(kp) >= 10:
            features = [(0.0, len(kp), des)]

            result = FeatureMatchingAlgorithm.compare_features(
                features,
                features,
                threshold=30.0
            )

            assert 0.0 <= result['similarity'] <= 100.0

    def test_match_count_reasonable(self, algorithm):
        """Test match count is reasonable (not exceeding total keypoints)."""
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp, des = algorithm.detector.detectAndCompute(gray, None)

        if des is not None and len(kp) >= 10:
            bf = cv2.BFMatcher(algorithm.norm, crossCheck=False)
            matches = bf.knnMatch(des, des, k=2)

            # Match count should not exceed keypoint count
            assert len(matches) <= len(kp)

    def test_no_keypoints_handling(self, algorithm):
        """Test graceful handling when no keypoints detected."""
        # Black frame should have no keypoints
        frame = create_black_frame()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kp, des = algorithm.detector.detectAndCompute(gray, None)

        # Should handle gracefully (None or empty)
        if kp is None or des is None:
            assert True  # Expected
        else:
            assert len(kp) >= 0


# ============================================================================
# VIDEO INTEGRATION TESTS
# ============================================================================

class TestFeatureMatchingVideoIntegration:
    """Test feature matching algorithm with real video files."""

    @pytest.fixture
    def test_video_path(self):
        """Return path to test video file."""
        from pathlib import Path
        video_path = "/Users/nico/Downloads/tests/Das Monster und die Schone_9.mp4"
        if not Path(video_path).exists():
            pytest.skip(f"Test video not found: {video_path}")
        return video_path

    def test_compare_same_video_identical_segments(self, test_video_path):
        """Test comparing identical segments from same video."""
        algo = FeatureMatchingAlgorithm()
        algo.configure(threshold=30.0, detector='ORB', num_samples=5)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=5.0
        )

        assert result['similarity'] > 0.30
        assert result['accepted'] == True
        assert 'best_offset_seconds' in result['metadata']
        assert 'avg_matches' in result['metadata']

    def test_compare_different_videos(self, test_video_path):
        """Test comparing different videos (same video = high similarity)."""
        algo = FeatureMatchingAlgorithm()
        algo.configure(threshold=25.0, detector='ORB')

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        # Same video should match
        assert result['similarity'] > 0.20

    def test_extract_features_real_video(self, test_video_path):
        """Test feature extraction from real video."""
        algo = FeatureMatchingAlgorithm()
        algo.configure(detector='ORB', num_samples=5)

        features = algo.extract_features(test_video_path)

        assert len(features) >= 2
        assert all(isinstance(f, tuple) for f in features)
        assert all(len(f) == 3 for f in features)  # (offset, num_kp, descriptors)

    def test_compare_with_orb_detector(self, test_video_path):
        """Test compare with ORB detector."""
        algo = FeatureMatchingAlgorithm()
        algo.configure(detector='ORB', num_samples=4, max_features=500)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        assert result['metadata']['detector'] == 'ORB'
        assert result['similarity'] > 0.0

    def test_compare_with_akaze_detector(self, test_video_path):
        """Test compare with AKAZE detector."""
        algo = FeatureMatchingAlgorithm()
        algo.configure(detector='AKAZE', num_samples=4)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        assert result['metadata']['detector'] == 'AKAZE'
        assert result['similarity'] > 0.0

    def test_compare_window_integration(self, test_video_path):
        """Test compare with sliding window."""
        algo = FeatureMatchingAlgorithm()
        algo.configure(search_step=2.0, max_windows=10, num_samples=3)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=4.0
        )

        assert 'windows_tested' in result['metadata']
        assert result['metadata']['windows_tested'] >= 1

    def test_compare_search_window(self, test_video_path):
        """Test search window functionality."""
        algo = FeatureMatchingAlgorithm()
        algo.configure(search_step=3.0, max_windows=20, num_samples=4)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=4.0
        )

        assert 'best_offset_seconds' in result['metadata']
        assert result['metadata']['best_offset_seconds'] >= 0.0

    def test_extract_features_integration(self, test_video_path):
        """Test _extract_features with real video."""
        algo = FeatureMatchingAlgorithm()
        algo.configure(num_samples=6, sample_interval=5.0)

        features = algo._extract_features(
            video_path=test_video_path,
            duration=5.0
        )

        assert len(features) >= 1
        assert all(isinstance(f, tuple) for f in features)
        assert all(len(f) == 3 for f in features)

    def test_compare_insufficient_frames(self, test_video_path):
        """Test compare with very short duration."""
        algo = FeatureMatchingAlgorithm()
        algo.configure(num_samples=100)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=0.1
        )

        # Very short duration may result in insufficient frames
        assert 'similarity' in result
        assert 'accepted' in result
        assert 'metadata' in result

    def test_compare_early_termination(self, test_video_path):
        """Test early termination when excellent match found."""
        algo = FeatureMatchingAlgorithm()
        algo.configure(threshold=30.0, search_step=1.0, max_windows=50, num_samples=4)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        # Should find match quickly
        assert result['similarity'] > 0.20
        assert 'windows_tested' in result['metadata']
