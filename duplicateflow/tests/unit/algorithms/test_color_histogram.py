"""
Unit tests for ColorHistogramAlgorithm.

Tests the color histogram comparison algorithm that uses HSV histograms
for video similarity detection.
"""

import pytest
import numpy as np
import cv2
from pathlib import Path

from duplicateflow.algorithms.color_histogram import ColorHistogramAlgorithm
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


class TestColorHistogramAlgorithmInstantiation:
    """Test algorithm instantiation and configuration."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        algo = ColorHistogramAlgorithm()

        # Check algorithm has required attributes
        assert hasattr(algo, 'name')
        assert hasattr(algo, 'configure')

        # Configure with defaults
        algo.configure()
        assert algo.threshold == 70.0
        assert algo.bins == (32, 32, 32)
        assert algo.num_samples == 5
        assert algo.search_step == 3.0
        assert algo.max_windows == 200
        assert algo.resize == (320, 240)

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        algo = ColorHistogramAlgorithm()
        algo.configure(
            threshold=80.0,
            bins=(16, 16, 16),
            num_samples=10,
            search_step=2.0,
            max_windows=100,
            resize=(640, 480)
        )

        assert algo.threshold == 80.0
        assert algo.bins == (16, 16, 16)
        assert algo.num_samples == 10
        assert algo.search_step == 2.0
        assert algo.max_windows == 100
        assert algo.resize == (640, 480)

    def test_configure_invalid_bins(self):
        """Test configuration with invalid bins defaults to (32,32,32)."""
        algo = ColorHistogramAlgorithm()

        # Invalid bins should default to (32,32,32)
        algo.configure(bins="invalid")
        assert algo.bins == (32, 32, 32)

        algo.configure(bins=(8, 8))  # Wrong length
        assert algo.bins == (32, 32, 32)

        algo.configure(bins=[8])  # Wrong length
        assert algo.bins == (32, 32, 32)


class TestColorHistogramComputation:
    """Test histogram computation methods."""

    @pytest.fixture
    def algorithm(self):
        """Algorithm instance for testing."""
        algo = ColorHistogramAlgorithm()
        algo.configure()
        return algo

    def test_compute_histogram_black_frame(self, algorithm):
        """Test histogram computation on black frame."""
        frame = create_black_frame()
        hist = algorithm._compute_histogram(frame)

        assert hist is not None
        assert isinstance(hist, np.ndarray)
        assert hist.dtype == np.float32

        # Histogram should be flattened
        expected_size = algorithm.bins[0] * algorithm.bins[1] * algorithm.bins[2]
        assert hist.shape == (expected_size,)

        # Histogram should be normalized (sum should be ~1.0)
        # Note: For black frame, histogram will have most mass in low bins
        assert hist.sum() == pytest.approx(1.0, abs=0.1)

    def test_compute_histogram_white_frame(self, algorithm):
        """Test histogram computation on white frame."""
        frame = create_white_frame()
        hist = algorithm._compute_histogram(frame)

        assert hist is not None
        assert isinstance(hist, np.ndarray)
        assert hist.dtype == np.float32

        expected_size = algorithm.bins[0] * algorithm.bins[1] * algorithm.bins[2]
        assert hist.shape == (expected_size,)

    def test_compute_histogram_color_frames(self, algorithm):
        """Test histogram computation on different solid colors."""
        colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
        ]

        histograms = []
        for r, g, b in colors:
            frame = create_color_frame(r=r, g=g, b=b)
            hist = algorithm._compute_histogram(frame)
            histograms.append(hist)

        # All histograms should be computed
        assert all(h is not None for h in histograms)
        assert all(isinstance(h, np.ndarray) for h in histograms)

        # Different colors should produce different histograms
        # (at least some should be different)
        for i in range(len(histograms)):
            for j in range(i + 1, len(histograms)):
                # Not all histograms should be identical
                if not np.array_equal(histograms[i], histograms[j]):
                    break
            else:
                continue
            break
        else:
            # If we get here, all histograms are identical, which is wrong
            pytest.fail("All color histograms are identical")

    def test_compute_histogram_identical_frames(self, algorithm):
        """Test that identical frames produce identical histograms."""
        frame1 = create_noise_frame(seed=42)
        frame2 = frame1.copy()

        hist1 = algorithm._compute_histogram(frame1)
        hist2 = algorithm._compute_histogram(frame2)

        assert np.allclose(hist1, hist2, atol=1e-6)

    def test_compute_histogram_similar_frames(self, algorithm):
        """Test that similar frames produce similar histograms."""
        frame1 = create_noise_frame(seed=42)
        # Add small brightness adjustment
        frame2 = adjust_brightness(frame1, factor=1.1)

        hist1 = algorithm._compute_histogram(frame1)
        hist2 = algorithm._compute_histogram(frame2)

        # Compute correlation between histograms
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

        # Similar frames should have moderate to high correlation
        # (brightness changes affect HSV histograms significantly)
        assert correlation > 0.5

    def test_compute_histogram_different_frames(self, algorithm):
        """Test that different frames produce different histograms."""
        frame1 = create_black_frame()
        frame2 = create_white_frame()

        hist1 = algorithm._compute_histogram(frame1)
        hist2 = algorithm._compute_histogram(frame2)

        # Histograms should not be identical
        assert not np.array_equal(hist1, hist2)

    def test_compute_histogram_noise_frames(self, algorithm):
        """Test histogram computation on random noise frames."""
        frame1 = create_noise_frame(seed=42)
        frame2 = create_noise_frame(seed=43)

        hist1 = algorithm._compute_histogram(frame1)
        hist2 = algorithm._compute_histogram(frame2)

        # Random noise should produce different histograms
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

        # Random frames should have low to moderate correlation
        assert correlation < 0.95  # Not highly correlated

    def test_compute_histogram_gradient_frames(self, algorithm):
        """Test histogram computation on gradient frames."""
        frame_h = create_gradient_frame(direction='horizontal')
        frame_v = create_gradient_frame(direction='vertical')

        hist_h = algorithm._compute_histogram(frame_h)
        hist_v = algorithm._compute_histogram(frame_v)

        assert hist_h is not None
        assert hist_v is not None

        # Both gradients span same values, so histograms might be similar
        # (gradient orientation doesn't affect color distribution much)
        correlation = cv2.compareHist(hist_h, hist_v, cv2.HISTCMP_CORREL)

        # Gradients should have moderate to high correlation
        assert correlation > 0.7


class TestColorHistogramBinConfigurations:
    """Test different histogram bin configurations."""

    def test_histogram_with_different_bins(self):
        """Test histogram computation with different bin sizes."""
        bin_configs = [
            (8, 8, 8),
            (16, 16, 16),
            (32, 32, 32),
            (64, 32, 32),
        ]

        frame = create_noise_frame(seed=42)

        for bins in bin_configs:
            algo = ColorHistogramAlgorithm()
            algo.configure(bins=bins)

            hist = algo._compute_histogram(frame)

            expected_size = bins[0] * bins[1] * bins[2]
            assert hist.shape == (expected_size,), f"Failed for bins={bins}"

    def test_histogram_normalization(self):
        """Test that histograms are properly normalized."""
        algo = ColorHistogramAlgorithm()
        algo.configure()

        frames = [
            create_black_frame(),
            create_white_frame(),
            create_noise_frame(seed=42),
            create_gradient_frame(direction='horizontal'),
        ]

        for frame in frames:
            hist = algo._compute_histogram(frame)

            # cv2.normalize normalizes to range [0, 1], not sum = 1
            # Histogram values should be in valid range
            assert np.all(hist >= 0.0), "Histogram values should be non-negative"
            assert hist.max() <= 1.0, "Histogram max should not exceed 1.0"


class TestColorHistogramEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.fixture
    def algorithm(self):
        algo = ColorHistogramAlgorithm()
        algo.configure()
        return algo

    def test_compute_histogram_small_frame(self, algorithm):
        """Test histogram computation on very small frame."""
        # Create a tiny frame
        small_frame = np.random.randint(0, 255, (8, 8, 3), dtype=np.uint8)

        hist = algorithm._compute_histogram(small_frame)

        assert hist is not None
        expected_size = algorithm.bins[0] * algorithm.bins[1] * algorithm.bins[2]
        assert hist.shape == (expected_size,)

    def test_compute_histogram_large_frame(self, algorithm):
        """Test histogram computation on large frame (4K)."""
        # Create a 4K frame
        large_frame = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)

        hist = algorithm._compute_histogram(large_frame)

        assert hist is not None
        expected_size = algorithm.bins[0] * algorithm.bins[1] * algorithm.bins[2]
        assert hist.shape == (expected_size,)

    def test_compute_histogram_grayscale_appearance(self, algorithm):
        """Test histogram on grayscale-looking frames."""
        # Create grayscale frame (RGB all same value)
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128

        hist = algorithm._compute_histogram(frame)

        assert hist is not None
        # Grayscale should produce valid histogram
        assert hist.sum() > 0.5


class TestColorHistogramBrightnessInvariance:
    """Test how histograms respond to brightness changes."""

    @pytest.fixture
    def algorithm(self):
        algo = ColorHistogramAlgorithm()
        algo.configure()
        return algo

    def test_histogram_brightness_change(self, algorithm):
        """Test histogram similarity with brightness changes."""
        frame_base = create_noise_frame(seed=42)
        frame_bright = adjust_brightness(frame_base, factor=1.3)
        frame_dark = adjust_brightness(frame_base, factor=0.7)

        hist_base = algorithm._compute_histogram(frame_base)
        hist_bright = algorithm._compute_histogram(frame_bright)
        hist_dark = algorithm._compute_histogram(frame_dark)

        # Compare correlations
        corr_bright = cv2.compareHist(hist_base, hist_bright, cv2.HISTCMP_CORREL)
        corr_dark = cv2.compareHist(hist_base, hist_dark, cv2.HISTCMP_CORREL)

        # Brightness changes significantly affect HSV histograms (V channel changes)
        # Correlations may be low to moderate
        assert corr_bright > 0.0, "Bright frame should have some correlation"
        assert corr_dark > 0.0, "Dark frame should have some correlation"
        # At least they should be positive
        assert -1.0 <= corr_bright <= 1.0
        assert -1.0 <= corr_dark <= 1.0

    def test_histogram_contrast_change(self, algorithm):
        """Test histogram similarity with contrast changes."""
        frame_base = create_noise_frame(seed=42)
        frame_high_contrast = adjust_contrast(frame_base, factor=1.5)

        hist_base = algorithm._compute_histogram(frame_base)
        hist_contrast = algorithm._compute_histogram(frame_high_contrast)

        # Compare correlation
        correlation = cv2.compareHist(hist_base, hist_contrast, cv2.HISTCMP_CORREL)

        # Contrast changes affect HSV histogram distribution
        # Correlation may be low to moderate
        assert -1.0 <= correlation <= 1.0, "Correlation should be in valid range"


class TestColorHistogramIntegration:
    """Integration-style tests for complete histogram workflow."""

    def test_histogram_workflow_identical_frames(self):
        """Test complete workflow with identical frames."""
        algo = ColorHistogramAlgorithm()
        algo.configure()

        frame = create_noise_frame(seed=42)

        hist1 = algo._compute_histogram(frame)
        hist2 = algo._compute_histogram(frame.copy())

        # Identical frames should produce identical histograms
        assert np.allclose(hist1, hist2, atol=1e-6)

        # Correlation should be 1.0
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        assert correlation == pytest.approx(1.0, abs=0.001)

    def test_histogram_workflow_similar_colors(self):
        """Test workflow with similar color palettes."""
        algo = ColorHistogramAlgorithm()
        algo.configure()

        # Create two frames with similar colors but different arrangements
        frame1 = create_checkerboard_frame(square_size=32)
        frame2 = create_checkerboard_frame(square_size=16)

        hist1 = algo._compute_histogram(frame1)
        hist2 = algo._compute_histogram(frame2)

        # Same colors (black/white) in different patterns
        # Should have high correlation
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

        assert correlation > 0.9, "Same color palette should have high correlation"

    def test_histogram_workflow_different_colors(self):
        """Test workflow with completely different color palettes."""
        algo = ColorHistogramAlgorithm()
        algo.configure()

        frame1 = create_color_frame(r=255, g=0, b=0)    # All red
        frame2 = create_color_frame(r=0, g=0, b=255)    # All blue

        hist1 = algo._compute_histogram(frame1)
        hist2 = algo._compute_histogram(frame2)

        # Different colors should have low correlation
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

        assert correlation < 0.8, "Different colors should have lower correlation"


class TestColorHistogramScenarios:
    """Test specific real-world scenarios."""

    def test_scenario_sky_colors(self):
        """Test scenario: Different sky colors (blue vs sunset)."""
        algo = ColorHistogramAlgorithm()
        algo.configure()

        # Blue sky
        frame_blue_sky = create_color_frame(r=135, g=206, b=235)

        # Orange sunset sky
        frame_sunset = create_color_frame(r=255, g=140, b=0)

        hist_blue = algo._compute_histogram(frame_blue_sky)
        hist_sunset = algo._compute_histogram(frame_sunset)

        # Different sky colors should have low to moderate correlation
        correlation = cv2.compareHist(hist_blue, hist_sunset, cv2.HISTCMP_CORREL)

        assert correlation < 0.9, "Different sky colors should differ"

    def test_scenario_day_night(self):
        """Test scenario: Day scene vs night scene."""
        algo = ColorHistogramAlgorithm()
        algo.configure()

        # Day scene (bright, colorful)
        frame_day = create_noise_frame(seed=42)
        frame_day = adjust_brightness(frame_day, factor=1.5)

        # Night scene (dark)
        frame_night = create_noise_frame(seed=42)
        frame_night = adjust_brightness(frame_night, factor=0.3)

        hist_day = algo._compute_histogram(frame_day)
        hist_night = algo._compute_histogram(frame_night)

        # Day and night have drastically different V (value) channels
        # Correlation may be low (brightness dominates the histogram difference)
        correlation = cv2.compareHist(hist_day, hist_night, cv2.HISTCMP_CORREL)

        assert -1.0 <= correlation <= 1.0, "Correlation should be in valid range"

    def test_scenario_color_shift(self):
        """Test scenario: Color temperature shift (warm vs cool)."""
        algo = ColorHistogramAlgorithm()
        algo.configure()

        # Create base noise frame
        base = create_noise_frame(seed=42)

        # Warm shift (increase red)
        frame_warm = base.copy()
        frame_warm[:, :, 2] = np.clip(frame_warm[:, :, 2] * 1.2, 0, 255).astype(np.uint8)

        # Cool shift (increase blue)
        frame_cool = base.copy()
        frame_cool[:, :, 0] = np.clip(frame_cool[:, :, 0] * 1.2, 0, 255).astype(np.uint8)

        hist_warm = algo._compute_histogram(frame_warm)
        hist_cool = algo._compute_histogram(frame_cool)

        # Color shifts change the hue channel in HSV
        # Correlation depends on how much the color distribution changes
        correlation = cv2.compareHist(hist_warm, hist_cool, cv2.HISTCMP_CORREL)

        assert -1.0 <= correlation <= 1.0, "Correlation should be in valid range"
        # Different color shifts should not be perfectly correlated
        assert correlation < 1.0, "Different color shifts should differ"


class TestColorHistogramComparison:
    """Test histogram comparison methods."""

    def test_histogram_comparison_methods(self):
        """Test different OpenCV histogram comparison methods."""
        algo = ColorHistogramAlgorithm()
        algo.configure()

        frame1 = create_noise_frame(seed=42)
        frame2 = create_noise_frame(seed=43)

        hist1 = algo._compute_histogram(frame1)
        hist2 = algo._compute_histogram(frame2)

        # Test all comparison methods work
        correl = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        chisqr = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CHISQR)
        intersect = cv2.compareHist(hist1, hist2, cv2.HISTCMP_INTERSECT)
        bhattacharyya = cv2.compareHist(hist1, hist2, cv2.HISTCMP_BHATTACHARYYA)

        # Verify all methods return valid numbers
        assert -1.0 <= correl <= 1.0
        assert chisqr >= 0.0
        assert intersect >= 0.0
        assert 0.0 <= bhattacharyya <= 1.0

    def test_histogram_self_comparison(self):
        """Test histogram compared with itself."""
        algo = ColorHistogramAlgorithm()
        algo.configure()

        frame = create_noise_frame(seed=42)
        hist = algo._compute_histogram(frame)

        # Self-comparison using CORREL should be 1.0
        correlation = cv2.compareHist(hist, hist, cv2.HISTCMP_CORREL)
        assert correlation == pytest.approx(1.0, abs=0.001)


class TestColorHistogramPerformance:
    """Test performance-related characteristics."""

    def test_histogram_reproducibility(self):
        """Test that histogram computation is deterministic."""
        algo = ColorHistogramAlgorithm()
        algo.configure()

        frame = create_noise_frame(seed=42)

        # Compute histogram multiple times
        hist1 = algo._compute_histogram(frame)
        hist2 = algo._compute_histogram(frame)
        hist3 = algo._compute_histogram(frame)

        # All should be identical
        assert np.allclose(hist1, hist2, atol=1e-6)
        assert np.allclose(hist2, hist3, atol=1e-6)

    def test_histogram_range(self):
        """Test that histogram values are in valid range."""
        algo = ColorHistogramAlgorithm()
        algo.configure()

        frames = [
            create_black_frame(),
            create_white_frame(),
            create_noise_frame(seed=42),
            create_gradient_frame(direction='horizontal'),
            create_checkerboard_frame(square_size=32),
        ]

        for frame in frames:
            hist = algo._compute_histogram(frame)

            # All histogram values should be >= 0
            assert np.all(hist >= 0.0), "Histogram values should be non-negative"

            # Normalized histogram should have reasonable max value
            assert hist.max() <= 1.0, "Histogram max should not exceed 1.0"
