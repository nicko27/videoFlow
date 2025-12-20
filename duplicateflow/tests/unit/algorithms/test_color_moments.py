"""
Unit tests for ColorMomentsAlgorithm.

Tests the color moments algorithm that uses statistical moments
(mean, std, skewness) for color distribution comparison.
"""

import pytest
import numpy as np
import cv2
from pathlib import Path

from duplicateflow.algorithms.color_moments import ColorMomentsAlgorithm
from tests.utils.frame_generator import (
    create_black_frame,
    create_white_frame,
    create_color_frame,
    create_noise_frame,
    create_gradient_frame,
    create_checkerboard_frame,
    adjust_brightness,
    adjust_contrast,
    create_test_frame_pair
)


class TestColorMomentsAlgorithmInstantiation:
    """Test algorithm instantiation and configuration."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        algo = ColorMomentsAlgorithm()

        # Check algorithm has required attributes
        assert hasattr(algo, 'name')
        assert hasattr(algo, 'configure')

        # Configure with defaults
        algo.configure()
        assert algo.threshold == 75.0
        assert algo.num_samples == 5
        assert algo.search_step == 3.0
        assert algo.max_windows == 200
        assert algo.resize == (320, 240)

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        algo = ColorMomentsAlgorithm()
        algo.configure(
            threshold=80.0,
            num_samples=10,
            search_step=2.0,
            max_windows=100,
            resize=(640, 480)
        )

        assert algo.threshold == 80.0
        assert algo.num_samples == 10
        assert algo.search_step == 2.0
        assert algo.max_windows == 100
        assert algo.resize == (640, 480)


class TestColorMomentsComputation:
    """Test color moments computation methods."""

    @pytest.fixture
    def algorithm(self):
        """Algorithm instance for testing."""
        algo = ColorMomentsAlgorithm()
        algo.configure()
        return algo

    def test_compute_moments_black_frame(self, algorithm):
        """Test moments computation on black frame."""
        frame = create_black_frame()
        moments = algorithm._compute_moments(frame)

        assert moments is not None
        assert isinstance(moments, np.ndarray)
        assert moments.dtype == np.float32

        # Moments vector should be 9D (3 moments × 3 channels)
        assert moments.shape == (9,)

        # Black frame: low mean, low std, skewness varies
        # H mean can be anything (undefined for black)
        # S mean should be low (no saturation)
        # V mean should be low (no value/brightness)
        assert moments[6] < 50  # V_mean should be low for black

    def test_compute_moments_white_frame(self, algorithm):
        """Test moments computation on white frame."""
        frame = create_white_frame()
        moments = algorithm._compute_moments(frame)

        assert moments is not None
        assert isinstance(moments, np.ndarray)
        assert moments.shape == (9,)

        # White frame: S low (no saturation), V high (bright)
        assert moments[6] > 200  # V_mean should be high for white

    def test_compute_moments_structure(self, algorithm):
        """Test moments vector structure."""
        frame = create_noise_frame(seed=42)
        moments = algorithm._compute_moments(frame)

        # Verify structure: [H_mean, H_std, H_skew, S_mean, S_std, S_skew, V_mean, V_std, V_skew]
        assert len(moments) == 9

        # Extract moments for verification
        h_mean, h_std, h_skew = moments[0:3]
        s_mean, s_std, s_skew = moments[3:6]
        v_mean, v_std, v_skew = moments[6:9]

        # Mean should be in valid range
        assert 0 <= h_mean <= 180  # Hue range 0-180 in OpenCV
        assert 0 <= s_mean <= 255  # Saturation 0-255
        assert 0 <= v_mean <= 255  # Value 0-255

        # Std should be non-negative
        assert h_std >= 0
        assert s_std >= 0
        assert v_std >= 0

        # Skewness can be any value
        assert -10 <= h_skew <= 10  # Reasonable range
        assert -10 <= s_skew <= 10
        assert -10 <= v_skew <= 10

    def test_compute_moments_identical_frames(self, algorithm):
        """Test that identical frames produce identical moments."""
        frame1 = create_noise_frame(seed=42)
        frame2 = frame1.copy()

        moments1 = algorithm._compute_moments(frame1)
        moments2 = algorithm._compute_moments(frame2)

        assert np.allclose(moments1, moments2, atol=1e-5)

    def test_compute_moments_different_frames(self, algorithm):
        """Test that different frames produce different moments."""
        frame1 = create_black_frame()
        frame2 = create_white_frame()

        moments1 = algorithm._compute_moments(frame1)
        moments2 = algorithm._compute_moments(frame2)

        # Moments should be different (especially V_mean)
        assert not np.allclose(moments1, moments2, atol=10.0)

    def test_compute_moments_solid_colors(self, algorithm):
        """Test moments on solid color frames."""
        colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
        ]

        moments_list = []
        for r, g, b in colors:
            frame = create_color_frame(r=r, g=g, b=b)
            moments = algorithm._compute_moments(frame)
            moments_list.append(moments)

        # All moments should be computed
        assert all(m is not None for m in moments_list)

        # Solid colors should have zero std (uniform)
        for moments in moments_list:
            h_std = moments[1]
            s_std = moments[4]
            v_std = moments[7]

            # Std should be very close to zero for uniform frames
            assert h_std < 1.0, "Uniform frame should have low H std"
            assert s_std < 1.0, "Uniform frame should have low S std"
            assert v_std < 1.0, "Uniform frame should have low V std"

    def test_compute_moments_noise_frame(self, algorithm):
        """Test moments on random noise frame."""
        frame = create_noise_frame(seed=42)
        moments = algorithm._compute_moments(frame)

        assert moments is not None
        assert moments.shape == (9,)

        # Noise frame should have non-zero std
        h_std, s_std, v_std = moments[1], moments[4], moments[7]

        assert h_std > 0, "Noise frame should have positive H std"
        assert s_std > 0, "Noise frame should have positive S std"
        assert v_std > 0, "Noise frame should have positive V std"

    def test_compute_moments_gradient_frame(self, algorithm):
        """Test moments on gradient frame."""
        frame = create_gradient_frame(direction='horizontal')
        moments = algorithm._compute_moments(frame)

        assert moments is not None
        assert moments.shape == (9,)

        # Gradient should have non-zero std
        v_std = moments[7]
        assert v_std > 0, "Gradient should have positive V std"


class TestColorMomentsSimilarity:
    """Test color moments similarity computation."""

    @pytest.fixture
    def algorithm(self):
        algo = ColorMomentsAlgorithm()
        algo.configure()
        return algo

    def test_moments_euclidean_distance_identical(self, algorithm):
        """Test Euclidean distance for identical frames."""
        frame = create_noise_frame(seed=42)

        moments1 = algorithm._compute_moments(frame)
        moments2 = algorithm._compute_moments(frame.copy())

        # Compute Euclidean distance
        distance = np.linalg.norm(moments1 - moments2)

        # Identical frames should have zero distance
        assert distance == pytest.approx(0.0, abs=1e-5)

    def test_moments_euclidean_distance_similar(self, algorithm):
        """Test Euclidean distance for similar frames."""
        from tests.utils.frame_generator import add_noise

        frame1 = create_noise_frame(seed=42)
        frame2 = add_noise(frame1, noise_level=5)

        moments1 = algorithm._compute_moments(frame1)
        moments2 = algorithm._compute_moments(frame2)

        # Compute Euclidean distance
        distance = np.linalg.norm(moments1 - moments2)

        # Similar frames should have small distance
        assert distance < 20.0

    def test_moments_euclidean_distance_different(self, algorithm):
        """Test Euclidean distance for different frames."""
        frame1 = create_black_frame()
        frame2 = create_white_frame()

        moments1 = algorithm._compute_moments(frame1)
        moments2 = algorithm._compute_moments(frame2)

        # Compute Euclidean distance
        distance = np.linalg.norm(moments1 - moments2)

        # Different frames should have larger distance
        assert distance > 50.0


class TestColorMomentsEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.fixture
    def algorithm(self):
        algo = ColorMomentsAlgorithm()
        algo.configure()
        return algo

    def test_compute_moments_small_frame(self, algorithm):
        """Test moments computation on small frame."""
        small_frame = np.random.randint(0, 255, (16, 16, 3), dtype=np.uint8)

        moments = algorithm._compute_moments(small_frame)

        assert moments is not None
        assert moments.shape == (9,)

    def test_compute_moments_large_frame(self, algorithm):
        """Test moments computation on large frame (4K)."""
        large_frame = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)

        moments = algorithm._compute_moments(large_frame)

        assert moments is not None
        assert moments.shape == (9,)

    def test_compute_moments_zero_std_channels(self, algorithm):
        """Test moments with zero std (uniform channel)."""
        # Create frame with uniform color
        frame = create_color_frame(r=128, g=128, b=128)

        moments = algorithm._compute_moments(frame)

        # When std is zero, skewness should be 0
        h_skew = moments[2]
        s_skew = moments[5]
        v_skew = moments[8]

        # Skewness should be zero or very small for uniform frames
        assert abs(h_skew) < 1.0
        assert abs(s_skew) < 1.0
        assert abs(v_skew) < 1.0


class TestColorMomentsBrightnessRobustness:
    """Test color moments robustness to brightness changes."""

    @pytest.fixture
    def algorithm(self):
        algo = ColorMomentsAlgorithm()
        algo.configure()
        return algo

    def test_moments_brightness_change(self, algorithm):
        """Test moments with brightness changes."""
        frame_base = create_noise_frame(seed=42)
        frame_bright = adjust_brightness(frame_base, factor=1.3)

        moments_base = algorithm._compute_moments(frame_base)
        moments_bright = algorithm._compute_moments(frame_bright)

        # Brightness changes affect V channel mean
        # But H and S channels should be somewhat preserved
        v_mean_base = moments_base[6]
        v_mean_bright = moments_bright[6]

        # V mean should increase with brightness
        assert v_mean_bright > v_mean_base

        # Euclidean distance
        distance = np.linalg.norm(moments_base - moments_bright)

        # Distance should be moderate (not zero, but not huge)
        assert distance > 0.0
        assert distance < 100.0

    def test_moments_contrast_change(self, algorithm):
        """Test moments with contrast changes."""
        frame_base = create_noise_frame(seed=42)
        frame_contrast = adjust_contrast(frame_base, factor=1.5)

        moments_base = algorithm._compute_moments(frame_base)
        moments_contrast = algorithm._compute_moments(frame_contrast)

        # Contrast changes affect std
        v_std_base = moments_base[7]
        v_std_contrast = moments_contrast[7]

        # Higher contrast should increase std
        assert v_std_contrast > v_std_base * 0.8  # At least 80% of expected increase

        # Euclidean distance
        distance = np.linalg.norm(moments_base - moments_contrast)

        # Distance should be present
        assert distance > 0.0


class TestColorMomentsColorInvariance:
    """Test color moments behavior with color changes."""

    @pytest.fixture
    def algorithm(self):
        algo = ColorMomentsAlgorithm()
        algo.configure()
        return algo

    def test_moments_hue_sensitivity(self, algorithm):
        """Test that moments are sensitive to hue changes."""
        frame_red = create_color_frame(r=255, g=0, b=0)
        frame_blue = create_color_frame(r=0, g=0, b=255)

        moments_red = algorithm._compute_moments(frame_red)
        moments_blue = algorithm._compute_moments(frame_blue)

        # Hue means should be different
        h_mean_red = moments_red[0]
        h_mean_blue = moments_blue[0]

        # Different hues should produce different H means
        assert abs(h_mean_red - h_mean_blue) > 10.0

    def test_moments_saturation_sensitivity(self, algorithm):
        """Test that moments are sensitive to saturation changes."""
        # High saturation (pure color)
        frame_saturated = create_color_frame(r=255, g=0, b=0)

        # Low saturation (grayish)
        frame_desaturated = create_color_frame(r=150, g=100, b=100)

        moments_sat = algorithm._compute_moments(frame_saturated)
        moments_desat = algorithm._compute_moments(frame_desaturated)

        # Saturation means should be different
        s_mean_sat = moments_sat[3]
        s_mean_desat = moments_desat[3]

        # Saturated frame should have higher S mean
        assert s_mean_sat > s_mean_desat


class TestColorMomentsIntegration:
    """Integration-style tests for complete moments workflow."""

    def test_moments_workflow_identical_frames(self):
        """Test complete workflow with identical frames."""
        algo = ColorMomentsAlgorithm()
        algo.configure()

        frame = create_noise_frame(seed=42)

        moments1 = algo._compute_moments(frame)
        moments2 = algo._compute_moments(frame.copy())

        # Compute Euclidean distance
        distance = np.linalg.norm(moments1 - moments2)

        assert distance == pytest.approx(0.0, abs=1e-5)

    def test_moments_workflow_similar_colors(self):
        """Test workflow with similar color distributions."""
        algo = ColorMomentsAlgorithm()
        algo.configure()

        # Two noise frames with same seed have same distribution
        frame1 = create_noise_frame(seed=42)
        frame2 = create_noise_frame(seed=42)

        moments1 = algo._compute_moments(frame1)
        moments2 = algo._compute_moments(frame2)

        # Should be identical
        assert np.allclose(moments1, moments2, atol=1e-5)

    def test_moments_workflow_different_colors(self):
        """Test workflow with different color distributions."""
        algo = ColorMomentsAlgorithm()
        algo.configure()

        # Red vs blue
        frame1 = create_color_frame(r=255, g=0, b=0)
        frame2 = create_color_frame(r=0, g=0, b=255)

        moments1 = algo._compute_moments(frame1)
        moments2 = algo._compute_moments(frame2)

        # Compute Euclidean distance
        distance = np.linalg.norm(moments1 - moments2)

        # Different colors should have significant distance
        assert distance > 10.0


class TestColorMomentsScenarios:
    """Test specific real-world scenarios."""

    def test_scenario_sky_colors(self):
        """Test scenario: Different sky colors."""
        algo = ColorMomentsAlgorithm()
        algo.configure()

        # Blue sky
        frame_blue = create_color_frame(r=135, g=206, b=235)

        # Sunset sky (orange)
        frame_sunset = create_color_frame(r=255, g=140, b=0)

        moments_blue = algo._compute_moments(frame_blue)
        moments_sunset = algo._compute_moments(frame_sunset)

        # Different sky colors should have different H means
        h_mean_blue = moments_blue[0]
        h_mean_sunset = moments_sunset[0]

        assert abs(h_mean_blue - h_mean_sunset) > 10.0

    def test_scenario_day_night(self):
        """Test scenario: Day scene vs night scene."""
        algo = ColorMomentsAlgorithm()
        algo.configure()

        # Day scene (bright)
        frame_day = create_noise_frame(seed=42)
        frame_day = adjust_brightness(frame_day, factor=1.5)

        # Night scene (dark)
        frame_night = create_noise_frame(seed=42)
        frame_night = adjust_brightness(frame_night, factor=0.3)

        moments_day = algo._compute_moments(frame_day)
        moments_night = algo._compute_moments(frame_night)

        # V means should be different
        v_mean_day = moments_day[6]
        v_mean_night = moments_night[6]

        assert v_mean_day > v_mean_night

    def test_scenario_colorful_vs_grayscale(self):
        """Test scenario: Colorful vs grayscale content."""
        algo = ColorMomentsAlgorithm()
        algo.configure()

        # Colorful frame (noise with color)
        frame_color = create_noise_frame(seed=42)

        # Grayscale frame (low saturation)
        frame_gray = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        # Make it grayscale (all channels same)
        gray_value = frame_gray[:, :, 0]
        frame_gray[:, :, 0] = gray_value
        frame_gray[:, :, 1] = gray_value
        frame_gray[:, :, 2] = gray_value

        moments_color = algo._compute_moments(frame_color)
        moments_gray = algo._compute_moments(frame_gray)

        # Saturation means should differ
        s_mean_color = moments_color[3]
        s_mean_gray = moments_gray[3]

        # Colorful should have higher saturation
        assert s_mean_color > s_mean_gray


class TestColorMomentsPerformance:
    """Test performance-related characteristics."""

    def test_moments_reproducibility(self):
        """Test that moments computation is deterministic."""
        algo = ColorMomentsAlgorithm()
        algo.configure()

        frame = create_noise_frame(seed=42)

        # Compute moments multiple times
        moments1 = algo._compute_moments(frame)
        moments2 = algo._compute_moments(frame)
        moments3 = algo._compute_moments(frame)

        # All should be identical
        assert np.allclose(moments1, moments2, atol=1e-6)
        assert np.allclose(moments2, moments3, atol=1e-6)

    def test_moments_vector_size_consistency(self):
        """Test that moments vector is always 9D."""
        algo = ColorMomentsAlgorithm()
        algo.configure()

        frames = [
            create_black_frame(),
            create_white_frame(),
            create_noise_frame(seed=42),
            create_gradient_frame(direction='horizontal'),
            create_checkerboard_frame(square_size=32),
        ]

        for frame in frames:
            moments = algo._compute_moments(frame)
            assert moments.shape == (9,), f"Moments should be 9D for all frames"

    def test_moments_range_validation(self):
        """Test that moments are in reasonable ranges."""
        algo = ColorMomentsAlgorithm()
        algo.configure()

        frames = [
            create_noise_frame(seed=42),
            create_gradient_frame(direction='horizontal'),
            create_checkerboard_frame(square_size=16),
        ]

        for frame in frames:
            moments = algo._compute_moments(frame)

            # Extract components
            h_mean, h_std, h_skew = moments[0:3]
            s_mean, s_std, s_skew = moments[3:6]
            v_mean, v_std, v_skew = moments[6:9]

            # Validate ranges
            assert 0 <= h_mean <= 180, "H mean out of range"
            assert h_std >= 0, "H std should be non-negative"

            assert 0 <= s_mean <= 255, "S mean out of range"
            assert s_std >= 0, "S std should be non-negative"

            assert 0 <= v_mean <= 255, "V mean out of range"
            assert v_std >= 0, "V std should be non-negative"

            # Skewness can be any value but should be reasonable
            assert -10 <= h_skew <= 10, "H skewness unreasonable"
            assert -10 <= s_skew <= 10, "S skewness unreasonable"
            assert -10 <= v_skew <= 10, "V skewness unreasonable"
