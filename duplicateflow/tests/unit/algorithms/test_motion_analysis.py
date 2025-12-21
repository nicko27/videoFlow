"""
Unit tests for MotionAnalysisAlgorithm.

Tests the motion analysis algorithm that uses frame-to-frame differences
to capture motion patterns and correlate them between videos.
"""

import pytest
import cv2
import numpy as np
from pathlib import Path

from duplicateflow.algorithms.motion_analysis import MotionAnalysisAlgorithm
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
    """MotionAnalysisAlgorithm instance with default parameters."""
    algo = MotionAnalysisAlgorithm()
    algo.configure()
    return algo


@pytest.fixture
def algorithm_custom():
    """MotionAnalysisAlgorithm with custom parameters."""
    algo = MotionAnalysisAlgorithm()
    algo.configure(
        threshold=80.0,
        sample_interval=5.0,
        min_variance=1.0
    )
    return algo


# ==================== INSTANTIATION TESTS ====================

class TestMotionAnalysisAlgorithmInstantiation:
    """Test algorithm instantiation and configuration."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        algo = MotionAnalysisAlgorithm()
        algo.configure()

        assert algo.threshold == 70.0
        assert algo.sample_interval == 3.0
        assert algo.search_step == 3.0
        assert algo.max_windows == 200
        assert algo.min_variance == 0.0
        assert algo.resize == (320, 240)

    def test_init_custom_params(self, algorithm_custom):
        """Test initialization with custom parameters."""
        assert algorithm_custom.threshold == 80.0
        assert algorithm_custom.sample_interval == 5.0
        assert algorithm_custom.min_variance == 1.0

    def test_algorithm_has_required_attributes(self, algorithm):
        """Test algorithm has required attributes."""
        assert hasattr(algorithm, 'threshold')
        assert hasattr(algorithm, 'sample_interval')
        assert hasattr(algorithm, 'search_step')
        assert hasattr(algorithm, 'min_variance')


# ==================== FRAME DIFFERENCE COMPUTATION TESTS ====================

class TestFrameDifferenceComputation:
    """Test frame-to-frame difference computation."""

    def test_compute_diff_identical_frames(self):
        """Test difference between identical frames."""
        frame1 = create_noise_frame(seed=42)
        frame2 = frame1.copy()

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(gray1, gray2)
        mean_diff = np.mean(diff)

        # Identical frames should have zero difference
        assert mean_diff == 0.0

    def test_compute_diff_different_frames(self):
        """Test difference between different frames."""
        frame1 = create_black_frame()
        frame2 = create_white_frame()

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(gray1, gray2)
        mean_diff = np.mean(diff)

        # Black vs white should have maximum difference (255)
        assert mean_diff == 255.0

    def test_compute_diff_small_change(self):
        """Test difference with small change."""
        frame1 = create_noise_frame(seed=42)
        frame2 = add_noise(frame1, noise_level=5)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(gray1, gray2)
        mean_diff = np.mean(diff)

        # Small noise should produce small difference
        assert 0.0 < mean_diff < 50.0

    def test_diff_is_symmetric(self):
        """Test that absdiff is symmetric."""
        frame1 = create_noise_frame(seed=42)
        frame2 = create_noise_frame(seed=43)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        diff1 = cv2.absdiff(gray1, gray2)
        diff2 = cv2.absdiff(gray2, gray1)

        # Should be symmetric
        assert np.array_equal(diff1, diff2)

    def test_diff_range(self):
        """Test difference values are in valid range [0, 255]."""
        frame1 = create_noise_frame(seed=42)
        frame2 = create_noise_frame(seed=43)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(gray1, gray2)

        assert np.all(diff >= 0)
        assert np.all(diff <= 255)


# ==================== MOTION SIGNATURE TESTS ====================

class TestMotionSignatureComputation:
    """Test motion signature computation (simulated)."""

    def test_motion_signature_static_frames(self):
        """Test motion signature for static frames (no motion)."""
        # Create identical frames (no motion)
        frames = [create_black_frame() for _ in range(5)]

        # Compute frame-to-frame differences
        diffs = []
        for i in range(len(frames) - 1):
            gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray1, gray2)
            diffs.append(np.mean(diff))

        motion_signature = np.array(diffs, dtype=np.float32)

        # Static frames should have zero motion
        assert len(motion_signature) == 4  # 5 frames = 4 differences
        assert np.all(motion_signature == 0.0)

    def test_motion_signature_changing_frames(self):
        """Test motion signature for changing frames."""
        # Create progressively different frames
        frames = [
            create_black_frame(),
            create_gradient_frame(direction='horizontal'),
            create_checkerboard_frame(square_size=16),
            create_white_frame()
        ]

        # Compute frame-to-frame differences
        diffs = []
        for i in range(len(frames) - 1):
            gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray1, gray2)
            diffs.append(np.mean(diff))

        motion_signature = np.array(diffs, dtype=np.float32)

        # Should have non-zero differences
        assert len(motion_signature) == 3
        assert np.all(motion_signature > 0.0)

    def test_motion_signature_length(self):
        """Test motion signature has correct length."""
        # N frames produce N-1 differences
        for num_frames in [3, 5, 10]:
            frames = [create_noise_frame(seed=i) for i in range(num_frames)]

            diffs = []
            for i in range(len(frames) - 1):
                gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
                gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)
                diff = cv2.absdiff(gray1, gray2)
                diffs.append(np.mean(diff))

            assert len(diffs) == num_frames - 1

    def test_motion_signature_dtype(self):
        """Test motion signature has correct dtype."""
        frames = [create_noise_frame(seed=i) for i in range(3)]

        diffs = []
        for i in range(len(frames) - 1):
            gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray1, gray2)
            diffs.append(np.mean(diff))

        motion_signature = np.array(diffs, dtype=np.float32)

        assert motion_signature.dtype == np.float32


# ==================== CORRELATION TESTS ====================

class TestCorrelationComputation:
    """Test correlation computation between motion signatures."""

    def test_correlation_identical_signatures(self):
        """Test correlation of identical signatures."""
        signature = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)

        # Normalize
        norm = (signature - signature.mean()) / signature.std()

        # Correlate with itself
        correlation = np.corrcoef(norm, norm)[0, 1]

        # Should be perfect correlation (1.0)
        assert correlation == pytest.approx(1.0, abs=0.001)

    def test_correlation_similar_signatures(self):
        """Test correlation of similar signatures."""
        sig1 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        sig2 = np.array([12.0, 22.0, 32.0, 42.0], dtype=np.float32)

        # Normalize both
        norm1 = (sig1 - sig1.mean()) / sig1.std()
        norm2 = (sig2 - sig2.mean()) / sig2.std()

        # Correlate
        correlation = np.corrcoef(norm1, norm2)[0, 1]

        # Linear relationship = high correlation
        assert correlation > 0.99

    def test_correlation_different_signatures(self):
        """Test correlation of different signatures."""
        sig1 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        sig2 = np.array([40.0, 30.0, 20.0, 10.0], dtype=np.float32)

        # Normalize both
        norm1 = (sig1 - sig1.mean()) / sig1.std()
        norm2 = (sig2 - sig2.mean()) / sig2.std()

        # Correlate
        correlation = np.corrcoef(norm1, norm2)[0, 1]

        # Inverse relationship = negative correlation
        assert correlation < -0.99

    def test_correlation_uncorrelated_signatures(self):
        """Test correlation of uncorrelated signatures."""
        sig1 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        sig2 = np.array([25.0, 15.0, 35.0, 20.0], dtype=np.float32)

        # Normalize both
        norm1 = (sig1 - sig1.mean()) / sig1.std()
        norm2 = (sig2 - sig2.mean()) / sig2.std()

        # Correlate
        correlation = np.corrcoef(norm1, norm2)[0, 1]

        # Correlation should be between -1 and 1
        assert -1.0 <= correlation <= 1.0

    def test_correlation_range(self):
        """Test correlation is always in range [-1, 1]."""
        # Test with random signatures
        for _ in range(10):
            sig1 = np.random.rand(10).astype(np.float32)
            sig2 = np.random.rand(10).astype(np.float32)

            if sig1.std() > 0 and sig2.std() > 0:
                norm1 = (sig1 - sig1.mean()) / sig1.std()
                norm2 = (sig2 - sig2.mean()) / sig2.std()

                correlation = np.corrcoef(norm1, norm2)[0, 1]

                assert -1.0 <= correlation <= 1.0


# ==================== COMPARE FEATURES TESTS ====================

class TestCompareFeatures:
    """Test compare_features static method."""

    def test_compare_features_identical_signatures(self):
        """Test comparing identical motion signatures."""
        signature = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)

        result = MotionAnalysisAlgorithm.compare_features(
            signature,
            signature.copy(),
            threshold=70.0
        )

        # Identical signatures should have perfect correlation
        assert result['similarity'] == pytest.approx(100.0, abs=0.1)
        assert result['accepted'] == True

    def test_compare_features_similar_signatures(self):
        """Test comparing similar motion signatures."""
        sig1 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        sig2 = np.array([12.0, 22.0, 32.0, 42.0], dtype=np.float32)

        result = MotionAnalysisAlgorithm.compare_features(
            sig1,
            sig2,
            threshold=70.0
        )

        # Similar (linear) signatures should have high correlation
        assert result['similarity'] > 95.0
        assert result['accepted'] == True

    def test_compare_features_different_signatures(self):
        """Test comparing different motion signatures."""
        sig1 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        sig2 = np.array([40.0, 30.0, 20.0, 10.0], dtype=np.float32)

        result = MotionAnalysisAlgorithm.compare_features(
            sig1,
            sig2,
            threshold=70.0
        )

        # Inverse signatures should have low/negative correlation
        assert result['similarity'] < 10.0
        assert result['accepted'] is False

    def test_compare_features_empty_signature1(self):
        """Test comparing with empty first signature."""
        result = MotionAnalysisAlgorithm.compare_features(
            np.array([], dtype=np.float32),
            np.array([10.0, 20.0], dtype=np.float32),
            threshold=70.0
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] is False
        assert 'error' in result['metadata']

    def test_compare_features_empty_signature2(self):
        """Test comparing with empty second signature."""
        result = MotionAnalysisAlgorithm.compare_features(
            np.array([10.0, 20.0], dtype=np.float32),
            np.array([], dtype=np.float32),
            threshold=70.0
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] is False

    def test_compare_features_static_scenes(self):
        """Test comparing static scenes (zero variance)."""
        # Static scene = all zeros (no motion)
        sig1 = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        sig2 = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)

        result = MotionAnalysisAlgorithm.compare_features(
            sig1,
            sig2,
            threshold=70.0,
            params={'min_variance': 0.0}
        )

        # Static scenes should match perfectly
        assert result['similarity'] == 100.0
        assert result['accepted'] is True

    def test_compare_features_metadata(self):
        """Test compare_features returns correct metadata."""
        sig1 = np.array([10.0, 20.0, 30.0], dtype=np.float32)
        sig2 = np.array([15.0, 25.0, 35.0], dtype=np.float32)

        result = MotionAnalysisAlgorithm.compare_features(
            sig1,
            sig2,
            threshold=70.0
        )

        assert 'metadata' in result
        assert 'len_1' in result['metadata']
        assert 'len_2' in result['metadata']
        assert 'std_1' in result['metadata']
        assert 'std_2' in result['metadata']
        assert result['metadata']['len_1'] == 3
        assert result['metadata']['len_2'] == 3


# ==================== EDGE CASE TESTS ====================

class TestMotionAnalysisEdgeCases:
    """Test edge cases and special scenarios."""

    def test_compare_different_length_signatures(self):
        """Test comparing signatures of different lengths."""
        sig1 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        sig2 = np.array([15.0, 25.0], dtype=np.float32)

        result = MotionAnalysisAlgorithm.compare_features(
            sig1,
            sig2,
            threshold=70.0
        )

        # Should use minimum length for correlation
        assert result['similarity'] >= 0.0

    def test_compare_single_value_signatures(self):
        """Test comparing single-value signatures."""
        sig1 = np.array([10.0], dtype=np.float32)
        sig2 = np.array([20.0], dtype=np.float32)

        result = MotionAnalysisAlgorithm.compare_features(
            sig1,
            sig2,
            threshold=70.0
        )

        # Single values treated as static scenes = perfect match
        assert result['similarity'] == 100.0

    def test_min_variance_threshold(self):
        """Test min_variance parameter for static scene detection."""
        # Low variance (near-static)
        sig1 = np.array([10.0, 10.1, 10.0, 10.1], dtype=np.float32)
        sig2 = np.array([20.0, 20.1, 20.0, 20.1], dtype=np.float32)

        result = MotionAnalysisAlgorithm.compare_features(
            sig1,
            sig2,
            threshold=70.0,
            params={'min_variance': 1.0}  # Set high threshold
        )

        # Should treat as static scenes
        assert result['metadata']['static_1'] == True
        assert result['metadata']['static_2'] == True


# ==================== ROBUSTNESS TESTS ====================

class TestMotionAnalysisRobustness:
    """Test algorithm robustness to transformations."""

    def test_robustness_amplitude_scaling(self):
        """Test robustness to amplitude scaling (normalized correlation)."""
        sig1 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        sig2 = sig1 * 2.0  # Scale by 2

        result = MotionAnalysisAlgorithm.compare_features(
            sig1,
            sig2,
            threshold=70.0
        )

        # Correlation should be invariant to scaling
        assert result['similarity'] > 95.0

    def test_robustness_offset(self):
        """Test robustness to offset (normalized correlation)."""
        sig1 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        sig2 = sig1 + 100.0  # Add offset

        result = MotionAnalysisAlgorithm.compare_features(
            sig1,
            sig2,
            threshold=70.0
        )

        # Correlation should be invariant to offset
        assert result['similarity'] > 95.0

    def test_robustness_small_noise(self):
        """Test robustness to small noise."""
        sig1 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        sig2 = sig1 + np.random.rand(4) * 2.0  # Add small noise

        result = MotionAnalysisAlgorithm.compare_features(
            sig1,
            sig2,
            threshold=70.0
        )

        # Should still have high correlation
        assert result['similarity'] > 50.0


# ==================== INTEGRATION TESTS ====================

class TestMotionAnalysisIntegration:
    """Test complete motion analysis workflows."""

    def test_complete_motion_signature_workflow(self):
        """Test complete motion signature computation workflow."""
        # Create sequence of frames with motion
        frames = [
            create_black_frame(),
            create_gradient_frame(direction='horizontal'),
            create_checkerboard_frame(square_size=16),
            create_white_frame(),
            create_noise_frame(seed=42)
        ]

        # Compute motion signature
        diffs = []
        for i in range(len(frames) - 1):
            gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray1, gray2)
            diffs.append(np.mean(diff))

        motion_signature = np.array(diffs, dtype=np.float32)

        # Should have 4 differences
        assert len(motion_signature) == 4
        assert np.all(motion_signature >= 0.0)

    def test_compare_identical_motion_sequences(self):
        """Test comparing identical motion sequences."""
        # Create same motion sequence
        sig1 = np.array([5.0, 10.0, 15.0, 20.0, 25.0], dtype=np.float32)
        sig2 = sig1.copy()

        result = MotionAnalysisAlgorithm.compare_features(
            sig1,
            sig2,
            threshold=70.0
        )

        assert result['similarity'] > 95.0
        assert result['accepted'] is True

    def test_motion_signature_reproducibility(self):
        """Test motion signature computation is reproducible."""
        frames = [create_noise_frame(seed=i) for i in range(5)]

        # Compute motion signature twice
        diffs1 = []
        for i in range(len(frames) - 1):
            gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray1, gray2)
            diffs1.append(np.mean(diff))

        diffs2 = []
        for i in range(len(frames) - 1):
            gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray1, gray2)
            diffs2.append(np.mean(diff))

        # Should be identical
        assert diffs1 == diffs2


# ==================== PERFORMANCE TESTS ====================

class TestMotionAnalysisPerformance:
    """Test algorithm performance characteristics."""

    def test_signature_dtype_consistency(self):
        """Test motion signatures have consistent dtype."""
        frames = [create_noise_frame(seed=i) for i in range(5)]

        diffs = []
        for i in range(len(frames) - 1):
            gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray1, gray2)
            diffs.append(np.mean(diff))

        motion_signature = np.array(diffs, dtype=np.float32)

        assert motion_signature.dtype == np.float32

    def test_compare_features_returns_valid_similarity(self):
        """Test compare_features returns similarity in [0, 100]."""
        sig1 = np.array([10.0, 20.0, 30.0], dtype=np.float32)
        sig2 = np.array([15.0, 25.0, 35.0], dtype=np.float32)

        result = MotionAnalysisAlgorithm.compare_features(
            sig1,
            sig2,
            threshold=70.0
        )

        assert 0.0 <= result['similarity'] <= 100.0

    def test_correlation_score_conversion(self):
        """Test correlation coefficient conversion to percentage."""
        # Correlation of 1.0 = 100%
        # Correlation of 0.0 = 0%
        # Correlation of -1.0 = 0% (clamped)

        sig1 = np.array([10.0, 20.0, 30.0], dtype=np.float32)

        # Perfect correlation
        result = MotionAnalysisAlgorithm.compare_features(sig1, sig1, threshold=70.0)
        assert result['similarity'] == pytest.approx(100.0, abs=0.1)

    def test_nan_correlation_handling(self):
        """Test graceful handling of NaN correlation."""
        # Constant signature (zero std) would cause NaN
        sig1 = np.array([10.0, 10.0, 10.0], dtype=np.float32)
        sig2 = np.array([20.0, 20.0, 20.0], dtype=np.float32)

        result = MotionAnalysisAlgorithm.compare_features(
            sig1,
            sig2,
            threshold=70.0,
            params={'min_variance': 0.0}
        )

        # Should handle gracefully (static scenes = perfect match)
        assert result['similarity'] == 100.0


# ============================================================================
# VIDEO INTEGRATION TESTS
# ============================================================================

class TestMotionAnalysisVideoIntegration:
    """Test motion analysis algorithm with real video files."""

    @pytest.fixture
    def test_video_path(self):
        """Return path to test video file."""
        from pathlib import Path
        video_path = "/Users/nico/Downloads/tests/Das Monster und die Schone_9.mp4"
        if not Path(video_path).exists():
            pytest.skip(f"Test video not found: {video_path}")
        return video_path

    def test_compare_same_video(self, test_video_path):
        """Test comparing identical segments from same video."""
        algo = MotionAnalysisAlgorithm()
        algo.configure(threshold=0.70)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        assert result['similarity'] > 0.60
        assert 'metadata' in result

    def test_extract_features_real_video(self, test_video_path):
        """Test feature extraction from real video."""
        algo = MotionAnalysisAlgorithm()
        algo.configure()

        features = algo.extract_features(test_video_path)

        assert isinstance(features, np.ndarray)
        assert features.dtype == np.float32

    def test_compare_window_integration(self, test_video_path):
        """Test compare with sliding window."""
        algo = MotionAnalysisAlgorithm()
        algo.configure(search_step=2.0, max_windows=10)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        assert 'metadata' in result
        assert result['similarity'] >= 0.0
