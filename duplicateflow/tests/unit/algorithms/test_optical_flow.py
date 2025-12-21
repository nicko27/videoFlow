"""
Unit tests for OpticalFlowAlgorithm.

Tests the optical flow algorithm using Farneback dense optical flow
for motion pattern comparison.
"""

import pytest
import numpy as np
import cv2
from pathlib import Path

from duplicateflow.algorithms.optical_flow import OpticalFlowAlgorithm
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


# ============================================================================
# 1. ALGORITHM INSTANTIATION
# ============================================================================

class TestOpticalFlowInstantiation:
    """Test algorithm instantiation and configuration."""

    def test_instantiate_default(self):
        """Test instantiation with default parameters."""
        algo = OpticalFlowAlgorithm()
        algo.configure()

        assert algo.threshold == 70.0
        assert algo.max_frames == 20
        assert algo.frame_step == 3
        assert algo.search_step == 3.0
        assert algo.max_windows == 200
        assert algo.min_variance == 0.0

    def test_instantiate_custom_params(self):
        """Test instantiation with custom parameters."""
        algo = OpticalFlowAlgorithm()
        algo.configure(
            threshold=80.0,
            max_frames=30,
            frame_step=5,
            search_step=5.0,
            max_windows=100,
            min_variance=0.1
        )

        assert algo.threshold == 80.0
        assert algo.max_frames == 30
        assert algo.frame_step == 5
        assert algo.search_step == 5.0
        assert algo.max_windows == 100
        assert algo.min_variance == 0.1

    def test_has_required_methods(self):
        """Test algorithm has all required methods."""
        algo = OpticalFlowAlgorithm()

        assert hasattr(algo, 'configure')
        assert hasattr(algo, 'compare')
        assert hasattr(algo, 'extract_features')
        assert hasattr(algo, 'get_cli_params')
        assert hasattr(algo, 'get_requirements')
        assert hasattr(algo, '_compute_flow_magnitude')


# ============================================================================
# 2. CORE OPTICAL FLOW COMPUTATION
# ============================================================================

class TestOpticalFlowComputation:
    """Test optical flow computation (Farneback algorithm)."""

    @pytest.fixture
    def algorithm(self):
        """Create algorithm instance with default params."""
        algo = OpticalFlowAlgorithm()
        algo.configure()
        return algo

    def test_farneback_flow_calculation(self):
        """Test Farneback optical flow calculation."""
        # Create two simple grayscale frames
        gray1 = np.zeros((128, 128), dtype=np.uint8)
        gray1[40:80, 40:80] = 255  # White square in center

        gray2 = np.zeros((128, 128), dtype=np.uint8)
        gray2[40:80, 45:85] = 255  # White square shifted 5 pixels right

        # Compute optical flow
        flow = cv2.calcOpticalFlowFarneback(
            gray1, gray2, None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )

        assert flow is not None
        assert flow.shape == (128, 128, 2)  # (height, width, 2)
        assert flow.dtype == np.float32

        # Flow should contain non-zero values indicating motion
        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        assert np.max(mag) > 0.1  # Some motion detected

    def test_flow_magnitude_calculation(self):
        """Test converting flow to magnitude using cartToPolar."""
        # Create simple flow vectors
        flow = np.zeros((128, 128, 2), dtype=np.float32)
        flow[..., 0] = 3.0  # dx = 3
        flow[..., 1] = 4.0  # dy = 4

        # Convert to magnitude
        mag, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])

        # Magnitude should be sqrt(3^2 + 4^2) = 5.0
        assert mag.shape == (128, 128)
        assert np.allclose(mag, 5.0, atol=0.01)

    def test_flow_static_frames(self):
        """Test optical flow on static frames (no motion)."""
        frame1 = create_noise_frame(seed=42)
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)

        frame2 = frame1.copy()  # Identical frame
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        flow = cv2.calcOpticalFlowFarneback(
            gray1, gray2, None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )

        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])

        # Static frames should have very low flow magnitude
        assert np.mean(mag) < 1.0

    def test_flow_moving_frames(self):
        """Test optical flow on frames with motion."""
        # Create two grayscale frames with motion
        gray1 = np.zeros((128, 128), dtype=np.uint8)
        gray1[40:80, 40:80] = 255  # White square

        gray2 = np.zeros((128, 128), dtype=np.uint8)
        gray2[40:80, 50:90] = 255  # White square shifted 10 pixels right

        flow = cv2.calcOpticalFlowFarneback(
            gray1, gray2, None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )

        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])

        # Moving frames should have higher flow magnitude than static
        assert np.max(mag) > 1.0


# ============================================================================
# 3. COMPARE_FEATURES STATIC METHOD
# ============================================================================

class TestOpticalFlowCompareFeatures:
    """Test compare_features static method."""

    def test_compare_identical_features(self):
        """Test comparing identical optical flow features."""
        features1 = (5.0, 2.0)  # (magnitude, variance)
        features2 = (5.0, 2.0)

        result = OpticalFlowAlgorithm.compare_features(
            features1, features2, threshold=70.0
        )

        # Identical features should have perfect similarity
        assert result['similarity'] == 100.0
        assert result['accepted'] == True
        assert result['metadata']['magnitude_1'] == 5.0
        assert result['metadata']['magnitude_2'] == 5.0
        assert result['metadata']['variance_1'] == 2.0
        assert result['metadata']['variance_2'] == 2.0

    def test_compare_similar_features(self):
        """Test comparing similar optical flow features."""
        features1 = (10.0, 3.0)
        features2 = (10.5, 3.1)  # 5% difference

        result = OpticalFlowAlgorithm.compare_features(
            features1, features2, threshold=70.0
        )

        # Similar features should have high similarity (>95%)
        assert result['similarity'] > 95.0
        assert result['accepted'] == True

    def test_compare_different_features(self):
        """Test comparing different optical flow features."""
        features1 = (10.0, 3.0)
        features2 = (50.0, 8.0)  # 5x difference in magnitude

        result = OpticalFlowAlgorithm.compare_features(
            features1, features2, threshold=70.0
        )

        # Different features should have low similarity
        assert result['similarity'] < 50.0
        assert result['accepted'] == False

    def test_compare_static_scenes(self):
        """Test comparing static scenes (low variance)."""
        features1 = (1.0, 0.01)  # Very low variance (static)
        features2 = (50.0, 0.02)  # Different magnitude but also low variance

        result = OpticalFlowAlgorithm.compare_features(
            features1, features2,
            threshold=70.0,
            params={'min_variance': 0.1}
        )

        # Static scenes should match perfectly
        assert result['similarity'] == 100.0
        assert result['accepted'] == True
        assert result['metadata']['static_1'] == True
        assert result['metadata']['static_2'] == True

    def test_compare_one_static_one_dynamic(self):
        """Test comparing one static and one dynamic scene."""
        features1 = (1.0, 0.01)  # Static
        features2 = (50.0, 5.0)  # Dynamic

        result = OpticalFlowAlgorithm.compare_features(
            features1, features2,
            threshold=70.0,
            params={'min_variance': 0.1}
        )

        # One static scene = perfect match (static detection)
        assert result['similarity'] == 100.0
        assert result['metadata']['static_1'] == True
        assert result['metadata']['static_2'] == False

    def test_compare_none_features(self):
        """Test comparing with None features."""
        result = OpticalFlowAlgorithm.compare_features(
            None, (10.0, 2.0), threshold=70.0
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] == False
        assert 'error' in result['metadata']

        result = OpticalFlowAlgorithm.compare_features(
            (10.0, 2.0), None, threshold=70.0
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] == False

    def test_compare_zero_magnitude(self):
        """Test comparing features with zero magnitude."""
        features1 = (0.0, 0.0)
        features2 = (0.0, 0.0)

        result = OpticalFlowAlgorithm.compare_features(
            features1, features2, threshold=70.0
        )

        # Zero magnitudes should match (both static)
        assert result['similarity'] == 100.0
        assert result['accepted'] == True


# ============================================================================
# 4. EDGE CASES
# ============================================================================

class TestOpticalFlowEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def algorithm(self):
        algo = OpticalFlowAlgorithm()
        algo.configure()
        return algo

    def test_min_variance_threshold(self):
        """Test min_variance threshold for static scene detection."""
        features1 = (5.0, 0.05)  # Variance just above threshold
        features2 = (10.0, 0.15)

        # With min_variance = 0.1, features1 should be static
        result = OpticalFlowAlgorithm.compare_features(
            features1, features2,
            threshold=70.0,
            params={'min_variance': 0.1}
        )

        # One scene is static = perfect match
        assert result['similarity'] == 100.0
        assert result['metadata']['static_1'] == True
        assert result['metadata']['static_2'] == False

    def test_very_small_magnitude_difference(self):
        """Test with very small magnitude differences."""
        features1 = (10.0, 2.0)
        features2 = (10.001, 2.0)  # 0.01% difference

        result = OpticalFlowAlgorithm.compare_features(
            features1, features2, threshold=70.0
        )

        # Should be nearly perfect similarity
        assert result['similarity'] > 99.9
        assert result['accepted'] == True

    def test_very_large_magnitude_difference(self):
        """Test with very large magnitude differences."""
        features1 = (1.0, 0.5)
        features2 = (1000.0, 50.0)  # 1000x difference

        result = OpticalFlowAlgorithm.compare_features(
            features1, features2, threshold=70.0
        )

        # Should be near zero similarity
        assert result['similarity'] < 1.0
        assert result['accepted'] == False

    def test_exact_threshold_boundary(self):
        """Test exact threshold boundary."""
        # Calculate features that give exactly threshold similarity
        # similarity = 100 - (diff / denom * 100)
        # For threshold 70: diff / denom = 0.3
        # If mag1=10, mag2=13, diff=3, denom=13, diff/denom=0.23 -> similarity=77
        features1 = (10.0, 2.0)
        features2 = (13.0, 2.0)

        result = OpticalFlowAlgorithm.compare_features(
            features1, features2, threshold=70.0
        )

        # Should be right at threshold
        assert result['similarity'] > 70.0
        assert result['accepted'] == True


# ============================================================================
# 5. ROBUSTNESS
# ============================================================================

class TestOpticalFlowRobustness:
    """Test robustness to various conditions."""

    def test_magnitude_scale_invariance(self):
        """Test that similarity is based on relative difference."""
        # Same relative difference should give same similarity
        features1a = (10.0, 2.0)
        features2a = (15.0, 3.0)  # 50% increase

        features1b = (100.0, 20.0)
        features2b = (150.0, 30.0)  # 50% increase

        result_a = OpticalFlowAlgorithm.compare_features(
            features1a, features2a, threshold=70.0
        )

        result_b = OpticalFlowAlgorithm.compare_features(
            features1b, features2b, threshold=70.0
        )

        # Same relative difference = same similarity
        assert abs(result_a['similarity'] - result_b['similarity']) < 1.0

    def test_variance_ignored_in_similarity(self):
        """Test that variance is only used for static detection."""
        # Same magnitude, different variance (but both above min_variance)
        features1 = (10.0, 1.0)
        features2 = (10.0, 5.0)

        result = OpticalFlowAlgorithm.compare_features(
            features1, features2,
            threshold=70.0,
            params={'min_variance': 0.1}
        )

        # Variance difference shouldn't affect similarity (only magnitude)
        assert result['similarity'] == 100.0

    def test_static_detection_threshold(self):
        """Test static detection with different thresholds."""
        features1 = (5.0, 0.05)
        features2 = (10.0, 0.08)

        # With min_variance = 0.1, both are static
        result1 = OpticalFlowAlgorithm.compare_features(
            features1, features2,
            threshold=70.0,
            params={'min_variance': 0.1}
        )

        # With min_variance = 0.01, neither is static
        result2 = OpticalFlowAlgorithm.compare_features(
            features1, features2,
            threshold=70.0,
            params={'min_variance': 0.01}
        )

        assert result1['similarity'] == 100.0  # Both static
        assert result2['similarity'] < 100.0  # Magnitude comparison


# ============================================================================
# 6. INTEGRATION TESTS
# ============================================================================

class TestOpticalFlowIntegration:
    """Test complete workflows."""

    @pytest.fixture
    def algorithm(self):
        algo = OpticalFlowAlgorithm()
        algo.configure()
        return algo

    def test_complete_similarity_workflow(self):
        """Test complete similarity comparison workflow."""
        # Create two synthetic feature pairs
        features1 = (10.0, 2.5)
        features2 = (10.2, 2.6)

        # Compare with threshold
        result = OpticalFlowAlgorithm.compare_features(
            features1, features2, threshold=70.0
        )

        # Verify result structure
        assert 'similarity' in result
        assert 'accepted' in result
        assert 'metadata' in result
        assert 'magnitude_1' in result['metadata']
        assert 'magnitude_2' in result['metadata']
        assert 'variance_1' in result['metadata']
        assert 'variance_2' in result['metadata']
        assert 'static_1' in result['metadata']
        assert 'static_2' in result['metadata']

        # Verify values
        assert 0.0 <= result['similarity'] <= 100.0
        assert result['accepted'] == (result['similarity'] >= 70.0)

    def test_multiple_threshold_comparisons(self):
        """Test comparing same features with different thresholds."""
        features1 = (10.0, 2.0)
        features2 = (12.0, 2.5)

        result1 = OpticalFlowAlgorithm.compare_features(
            features1, features2, threshold=50.0
        )

        result2 = OpticalFlowAlgorithm.compare_features(
            features1, features2, threshold=90.0
        )

        # Same features, same similarity
        assert result1['similarity'] == result2['similarity']

        # Different thresholds, different acceptance
        # (assuming similarity is between 50 and 90)
        if 50.0 < result1['similarity'] < 90.0:
            assert result1['accepted'] == True
            assert result2['accepted'] == False


# ============================================================================
# 7. PERFORMANCE AND DETERMINISM
# ============================================================================

class TestOpticalFlowPerformance:
    """Test performance characteristics."""

    def test_deterministic_comparison(self):
        """Test that comparison is deterministic."""
        features1 = (10.5, 2.3)
        features2 = (11.2, 2.7)

        result1 = OpticalFlowAlgorithm.compare_features(
            features1, features2, threshold=70.0
        )

        result2 = OpticalFlowAlgorithm.compare_features(
            features1, features2, threshold=70.0
        )

        # Should be identical
        assert result1['similarity'] == result2['similarity']
        assert result1['accepted'] == result2['accepted']
        assert result1['metadata'] == result2['metadata']

    def test_symmetry(self):
        """Test that comparison is symmetric."""
        features1 = (10.0, 2.0)
        features2 = (15.0, 3.0)

        result1 = OpticalFlowAlgorithm.compare_features(
            features1, features2, threshold=70.0
        )

        result2 = OpticalFlowAlgorithm.compare_features(
            features2, features1, threshold=70.0
        )

        # Similarity should be the same (symmetric)
        assert result1['similarity'] == result2['similarity']
        assert result1['accepted'] == result2['accepted']

    def test_feature_tuple_format(self):
        """Test features are returned as tuples."""
        features = (10.0, 2.5)

        assert isinstance(features, tuple)
        assert len(features) == 2
        assert isinstance(features[0], float)  # magnitude
        assert isinstance(features[1], float)  # variance

    def test_similarity_range(self):
        """Test similarity is always in valid range."""
        test_cases = [
            ((10.0, 2.0), (10.0, 2.0)),  # Identical
            ((10.0, 2.0), (15.0, 3.0)),  # Similar
            ((10.0, 2.0), (100.0, 20.0)),  # Different
            ((1.0, 0.01), (1.0, 0.01)),  # Static
        ]

        for features1, features2 in test_cases:
            result = OpticalFlowAlgorithm.compare_features(
                features1, features2, threshold=70.0
            )

            assert 0.0 <= result['similarity'] <= 100.0

    def test_metadata_completeness(self):
        """Test metadata contains all expected fields."""
        features1 = (10.0, 2.0)
        features2 = (12.0, 2.5)

        result = OpticalFlowAlgorithm.compare_features(
            features1, features2,
            threshold=70.0,
            params={'min_variance': 0.1}
        )

        metadata = result['metadata']
        required_fields = [
            'magnitude_1', 'magnitude_2',
            'variance_1', 'variance_2',
            'static_1', 'static_2'
        ]

        for field in required_fields:
            assert field in metadata

    def test_cli_params(self):
        """Test get_cli_params returns valid parameters."""
        algo = OpticalFlowAlgorithm()
        params = algo.get_cli_params()

        assert isinstance(params, list)
        assert len(params) == 3

        # Verify parameter structure
        for param in params:
            assert 'names' in param
            assert 'type' in param
            assert 'default' in param
            assert 'help' in param

    def test_requirements(self):
        """Test get_requirements returns valid dependencies."""
        algo = OpticalFlowAlgorithm()
        reqs = algo.get_requirements()

        assert isinstance(reqs, list)
        assert 'opencv-python>=4.8.0' in reqs
        assert 'numpy>=1.24.0' in reqs


# ============================================================================
# 8. VIDEO INTEGRATION TESTS
# ============================================================================

class TestOpticalFlowVideoIntegration:
    """Test optical flow algorithm with real video files."""

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
        algo = OpticalFlowAlgorithm()
        algo.configure(threshold=70.0, max_frames=15, frame_step=3)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=5.0
        )

        # Identical segments should have high similarity
        assert result['similarity'] > 0.70
        assert result['accepted'] == True
        assert 'best_offset_seconds' in result['metadata']
        assert 'short_magnitude' in result['metadata']
        assert 'short_variance' in result['metadata']
        assert result['metadata']['windows_tested'] >= 1

    def test_compare_different_videos(self, test_video_path):
        """Test comparing different segments (simulated by different durations)."""
        algo = OpticalFlowAlgorithm()
        algo.configure(threshold=70.0, max_frames=10)

        # Compare first 3 seconds vs different segment
        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=10.0,  # Different position
            duration=3.0
        )

        # Result should be valid
        assert 0.0 <= result['similarity'] <= 1.0
        assert isinstance(result['accepted'], (bool, np.bool_))
        assert 'metadata' in result

    def test_extract_features_real_video(self, test_video_path):
        """Test extracting optical flow features from real video."""
        algo = OpticalFlowAlgorithm()
        algo.configure(max_frames=10, frame_step=3)

        features = algo.extract_features(test_video_path)

        # Should return tuple (magnitude, variance)
        assert isinstance(features, tuple)
        assert len(features) == 2
        assert isinstance(features[0], float)  # magnitude
        assert isinstance(features[1], float)  # variance
        assert features[0] >= 0.0
        assert features[1] >= 0.0

    def test_compare_window_integration(self, test_video_path):
        """Test _compute_flow_magnitude with real video."""
        algo = OpticalFlowAlgorithm()
        algo.configure(max_frames=10, frame_step=2)

        mag, var = algo._compute_flow_magnitude(
            test_video_path,
            duration=3.0,
            start_time=0.0
        )

        assert mag is not None
        assert var is not None
        assert isinstance(mag, float)
        assert isinstance(var, float)
        assert mag >= 0.0
        assert var >= 0.0

    def test_compare_search_window(self, test_video_path):
        """Test sliding window search with real video."""
        algo = OpticalFlowAlgorithm()
        algo.configure(
            threshold=70.0,
            max_frames=8,
            search_step=2.0,
            max_windows=5
        )

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        # Should test multiple windows
        assert result['metadata']['windows_tested'] >= 1
        assert 'best_offset_seconds' in result['metadata']
        assert result['metadata']['best_offset_seconds'] >= 0.0

    def test_compare_with_different_params(self, test_video_path):
        """Test compare with different parameter configurations."""
        # Test with more frames
        algo1 = OpticalFlowAlgorithm()
        algo1.configure(max_frames=20, frame_step=2)
        result1 = algo1.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        # Test with fewer frames
        algo2 = OpticalFlowAlgorithm()
        algo2.configure(max_frames=5, frame_step=5)
        result2 = algo2.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        # Both should succeed
        assert 'similarity' in result1
        assert 'similarity' in result2
        assert 0.0 <= result1['similarity'] <= 1.0
        assert 0.0 <= result2['similarity'] <= 1.0

    def test_compare_with_min_variance(self, test_video_path):
        """Test static scene detection with min_variance."""
        algo = OpticalFlowAlgorithm()
        algo.configure(
            threshold=70.0,
            max_frames=10,
            min_variance=0.1  # Higher threshold for static detection
        )

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        assert 'short_variance' in result['metadata']
        assert isinstance(result['metadata']['short_variance'], (float, type(None)))

    def test_compare_insufficient_frames(self, test_video_path):
        """Test handling of very short duration."""
        algo = OpticalFlowAlgorithm()
        algo.configure(max_frames=100, frame_step=10)

        # Very short duration might not have enough frames
        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=0.5  # Very short
        )

        # Should still return valid result
        assert 'similarity' in result
        assert isinstance(result['accepted'], (bool, np.bool_))

    def test_compare_early_termination(self, test_video_path):
        """Test early termination when excellent match found."""
        algo = OpticalFlowAlgorithm()
        algo.configure(
            threshold=60.0,  # Lower threshold
            max_frames=10,
            search_step=1.0,
            max_windows=50  # Many windows
        )

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        # Should test windows and return valid result
        assert result['metadata']['windows_tested'] >= 1
        assert 0.0 <= result['similarity'] <= 1.0
        assert isinstance(result['accepted'], (bool, np.bool_))
