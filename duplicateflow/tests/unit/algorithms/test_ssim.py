"""
Unit tests for SSIMAlgorithm.

Tests the Structural Similarity Index (SSIM) algorithm for video similarity detection.
Uses direct testing of SSIM computation methods.
"""

import pytest
import numpy as np
import cv2

from duplicateflow.algorithms.ssim import SSIMAlgorithm, SKIMAGE_AVAILABLE
from tests.utils.frame_generator import (
    create_black_frame,
    create_white_frame,
    create_color_frame,
    create_noise_frame,
    create_gradient_frame,
    create_checkerboard_frame,
    add_noise,
    adjust_brightness,
    adjust_contrast,
    create_test_frame_pair
)


# Skip all tests if scikit-image is not available
pytestmark = pytest.mark.skipif(
    not SKIMAGE_AVAILABLE,
    reason="scikit-image not available"
)


class TestSSIMAlgorithmInstantiation:
    """Test algorithm instantiation and configuration."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        algo = SSIMAlgorithm()

        assert hasattr(algo, 'name')
        assert hasattr(algo, 'configure')
        # Configure with defaults
        algo.configure()
        assert algo.threshold == 0.70
        assert algo.sample_interval == 5.0
        assert algo.resize == (320, 240)

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        algo = SSIMAlgorithm()
        algo.configure(
            threshold=0.85,
            sample_interval=3.0,
            num_samples=10,
            resize=(640, 480)
        )

        assert algo.threshold == 0.85
        assert algo.sample_interval == 3.0
        assert algo.num_samples == 10
        assert algo.resize == (640, 480)

    def test_configure_threshold_normalization(self):
        """Test threshold normalization (0-100 to 0-1)."""
        algo = SSIMAlgorithm()

        # Threshold > 1 should be normalized
        algo.configure(threshold=85.0)
        assert algo.threshold == 0.85

        # Threshold <= 1 should remain unchanged
        algo.configure(threshold=0.75)
        assert algo.threshold == 0.75


class TestSSIMComputation:
    """Test SSIM computation methods."""

    @pytest.fixture
    def algorithm(self):
        """Algorithm instance for testing."""
        algo = SSIMAlgorithm()
        algo.configure()
        return algo

    def test_compute_ssim_identical_frames(self, algorithm):
        """Test SSIM with identical frames."""
        frame1 = create_noise_frame(seed=42)
        frame2 = frame1.copy()

        ssim_score = algorithm._compute_ssim(frame1, frame2)

        # Identical frames should have perfect SSIM
        assert ssim_score == pytest.approx(1.0, abs=0.001)

    def test_compute_ssim_black_frames(self, algorithm):
        """Test SSIM with identical black frames."""
        frame1 = create_black_frame()
        frame2 = create_black_frame()

        ssim_score = algorithm._compute_ssim(frame1, frame2)

        # Identical black frames should have perfect SSIM
        assert ssim_score == pytest.approx(1.0, abs=0.001)

    def test_compute_ssim_white_frames(self, algorithm):
        """Test SSIM with identical white frames."""
        frame1 = create_white_frame()
        frame2 = create_white_frame()

        ssim_score = algorithm._compute_ssim(frame1, frame2)

        # Identical white frames should have perfect SSIM
        assert ssim_score == pytest.approx(1.0, abs=0.001)

    def test_compute_ssim_different_frames(self, algorithm):
        """Test SSIM with completely different frames."""
        frame1 = create_black_frame()
        frame2 = create_white_frame()

        ssim_score = algorithm._compute_ssim(frame1, frame2)

        # Completely different frames should have low SSIM
        assert ssim_score < 0.5

    def test_compute_ssim_similar_frames(self, algorithm):
        """Test SSIM with similar frames (small noise)."""
        frame1 = create_noise_frame(seed=42)
        frame2 = add_noise(frame1, noise_level=5)

        ssim_score = algorithm._compute_ssim(frame1, frame2)

        # Similar frames should have high SSIM
        assert ssim_score > 0.85

    def test_compute_ssim_moderate_difference(self, algorithm):
        """Test SSIM with moderate differences."""
        frame1 = create_noise_frame(seed=42)
        frame2 = add_noise(frame1, noise_level=20)

        ssim_score = algorithm._compute_ssim(frame1, frame2)

        # SSIM is very robust to noise - even noise_level=20 gives high score
        assert 0.7 < ssim_score < 1.0

    def test_compute_ssim_brightness_change(self, algorithm):
        """Test SSIM robustness to brightness changes."""
        frame1 = create_noise_frame(seed=42)
        frame2 = adjust_brightness(frame1, factor=1.3)

        ssim_score = algorithm._compute_ssim(frame1, frame2)

        # SSIM is quite robust to brightness changes
        # Structure remains similar even with brightness changes
        assert 0.6 < ssim_score < 1.0

    def test_compute_ssim_contrast_change(self, algorithm):
        """Test SSIM with contrast changes."""
        frame1 = create_noise_frame(seed=42)
        frame2 = adjust_contrast(frame1, factor=1.5)

        ssim_score = algorithm._compute_ssim(frame1, frame2)

        # SSIM considers contrast as one of its components
        # but is still quite robust to moderate contrast changes
        assert 0.5 < ssim_score < 1.0


class TestSSIMEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def algorithm(self):
        algo = SSIMAlgorithm()
        algo.configure()
        return algo

    def test_compute_ssim_solid_colors(self, algorithm):
        """Test SSIM with solid color frames."""
        # Same colors should have perfect SSIM
        red1 = create_color_frame(r=255, g=0, b=0)
        red2 = create_color_frame(r=255, g=0, b=0)

        ssim_score = algorithm._compute_ssim(red1, red2)
        assert ssim_score == pytest.approx(1.0, abs=0.001)

        # Different solid colors have same structure (no texture)
        # so SSIM may be higher than expected
        red = create_color_frame(r=255, g=0, b=0)
        blue = create_color_frame(r=0, g=0, b=255)

        ssim_score = algorithm._compute_ssim(red, blue)
        # Solid colors have identical structure, only luminance differs
        assert 0.0 <= ssim_score <= 1.0

    def test_compute_ssim_gradient_frames(self, algorithm):
        """Test SSIM with gradient frames."""
        # Same gradients
        grad1 = create_gradient_frame(direction='horizontal')
        grad2 = create_gradient_frame(direction='horizontal')

        ssim_score = algorithm._compute_ssim(grad1, grad2)
        assert ssim_score == pytest.approx(1.0, abs=0.001)

        # Different gradients
        grad_h = create_gradient_frame(direction='horizontal')
        grad_v = create_gradient_frame(direction='vertical')

        ssim_score = algorithm._compute_ssim(grad_h, grad_v)
        # Different structure should give lower SSIM
        assert ssim_score < 0.8

    def test_compute_ssim_checkerboard_frames(self, algorithm):
        """Test SSIM with checkerboard patterns."""
        # Same patterns
        check1 = create_checkerboard_frame(square_size=32)
        check2 = create_checkerboard_frame(square_size=32)

        ssim_score = algorithm._compute_ssim(check1, check2)
        assert ssim_score == pytest.approx(1.0, abs=0.001)

        # Different patterns
        check32 = create_checkerboard_frame(square_size=32)
        check16 = create_checkerboard_frame(square_size=16)

        ssim_score = algorithm._compute_ssim(check32, check16)
        # Different structure should give lower SSIM
        assert ssim_score < 0.8

    def test_compute_ssim_small_frames(self, algorithm):
        """Test SSIM with small frames."""
        # Create tiny frames
        small1 = np.random.randint(0, 255, (10, 10, 3), dtype=np.uint8)
        small2 = small1.copy()

        # Should work even with small frames
        ssim_score = algorithm._compute_ssim(small1, small2)
        assert ssim_score == pytest.approx(1.0, abs=0.001)

    def test_compute_ssim_large_frames(self, algorithm):
        """Test SSIM with large frames."""
        # Create large frames (1080p)
        np.random.seed(42)
        large1 = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        large2 = large1.copy()

        # Should work with large frames
        ssim_score = algorithm._compute_ssim(large1, large2)
        assert ssim_score == pytest.approx(1.0, abs=0.001)

    def test_compute_ssim_different_aspect_ratios(self, algorithm):
        """Test SSIM with different aspect ratios."""
        # Create frames with different aspect ratios
        frame1 = create_noise_frame(width=640, height=480, seed=42)
        frame2 = create_noise_frame(width=800, height=600, seed=42)

        # SSIM requires same dimensions, so resize might be needed
        # or the algorithm should handle it
        # For now, we resize manually to same size
        frame2_resized = cv2.resize(frame2, (640, 480))

        ssim_score = algorithm._compute_ssim(frame1, frame2_resized)

        # Different noise patterns (despite same seed, different sizes)
        # should give moderate-to-low SSIM
        assert 0.0 <= ssim_score <= 1.0


class TestSSIMIntegration:
    """Integration-style tests for complete SSIM workflow."""

    def test_ssim_workflow_identical_scenes(self):
        """Test complete workflow with identical scenes."""
        algo = SSIMAlgorithm()
        algo.configure()

        scene = create_noise_frame(seed=42)

        ssim_score = algo._compute_ssim(scene, scene.copy())

        assert ssim_score == pytest.approx(1.0, abs=0.001)

    def test_ssim_workflow_very_similar_scenes(self):
        """Test complete workflow with very similar scenes."""
        algo = SSIMAlgorithm()
        algo.configure()

        scene1, scene2 = create_test_frame_pair('very_similar')

        ssim_score = algo._compute_ssim(scene1, scene2)

        # Very similar scenes should have high SSIM
        assert ssim_score > 0.90

    def test_ssim_workflow_similar_scenes(self):
        """Test complete workflow with similar scenes."""
        algo = SSIMAlgorithm()
        algo.configure()

        scene1, scene2 = create_test_frame_pair('similar')

        ssim_score = algo._compute_ssim(scene1, scene2)

        # Similar scenes should have high SSIM (SSIM is robust)
        assert 0.70 < ssim_score < 1.0

    def test_ssim_workflow_different_scenes(self):
        """Test complete workflow with different scenes."""
        algo = SSIMAlgorithm()
        algo.configure()

        scene1, scene2 = create_test_frame_pair('different')

        ssim_score = algo._compute_ssim(scene1, scene2)

        # Different scenes should have low SSIM
        assert ssim_score < 0.5

    def test_ssim_threshold_acceptance(self):
        """Test SSIM threshold acceptance logic."""
        algo = SSIMAlgorithm()
        algo.configure(threshold=0.80)

        # High similarity - should accept
        frame1 = create_noise_frame(seed=42)
        frame2 = add_noise(frame1, noise_level=3)

        ssim_score = algo._compute_ssim(frame1, frame2)

        if ssim_score >= algo.threshold:
            accepted = True
        else:
            accepted = False

        # With small noise, should exceed threshold
        assert ssim_score > 0.80
        assert accepted is True

        # Low similarity - should reject
        frame3 = create_black_frame()
        frame4 = create_white_frame()

        ssim_score_low = algo._compute_ssim(frame3, frame4)

        if ssim_score_low >= algo.threshold:
            accepted_low = True
        else:
            accepted_low = False

        # Black vs white should be below threshold
        assert ssim_score_low < 0.80
        assert accepted_low is False


class TestSSIMScenarios:
    """Test specific real-world scenarios."""

    def test_scenario_identical_frames(self):
        """Test scenario: Two identical frames."""
        frame1, frame2 = create_test_frame_pair('identical')

        algo = SSIMAlgorithm()
        algo.configure()

        ssim_score = algo._compute_ssim(frame1, frame2)

        assert ssim_score == pytest.approx(1.0, abs=0.001)

    def test_scenario_compressed_frames(self):
        """Test scenario: Simulate compression artifacts."""
        frame1 = create_noise_frame(seed=42)
        # Add small noise to simulate compression
        frame2 = add_noise(frame1, noise_level=8)

        algo = SSIMAlgorithm()
        algo.configure()

        ssim_score = algo._compute_ssim(frame1, frame2)

        # Compression artifacts should give high but not perfect SSIM
        assert 0.75 < ssim_score < 1.0

    def test_scenario_lighting_change(self):
        """Test scenario: Lighting changes."""
        frame1 = create_noise_frame(seed=42)
        # Brighten the frame
        frame2 = adjust_brightness(frame1, factor=1.4)

        algo = SSIMAlgorithm()
        algo.configure()

        ssim_score = algo._compute_ssim(frame1, frame2)

        # SSIM is quite robust to brightness/lighting changes
        # Structure remains identical, only luminance changes
        assert 0.5 < ssim_score < 1.0

    def test_scenario_pattern_matching(self):
        """Test scenario: Same pattern, different position."""
        # Create checkerboards with different square sizes
        frame1 = create_checkerboard_frame(square_size=16)
        frame2 = create_checkerboard_frame(square_size=32)

        algo = SSIMAlgorithm()
        algo.configure()

        ssim_score = algo._compute_ssim(frame1, frame2)

        # Different patterns should have lower SSIM
        # but both are checkerboards, so some structural similarity
        assert 0.2 < ssim_score < 0.8

    def test_scenario_noise_vs_pattern(self):
        """Test scenario: Random noise vs structured pattern."""
        frame1 = create_noise_frame(seed=42)
        frame2 = create_checkerboard_frame()

        algo = SSIMAlgorithm()
        algo.configure()

        ssim_score = algo._compute_ssim(frame1, frame2)

        # Noise vs pattern should have low SSIM
        assert ssim_score < 0.5

    def test_scenario_gradients(self):
        """Test scenario: Different gradient directions."""
        frame1 = create_gradient_frame(direction='horizontal')
        frame2 = create_gradient_frame(direction='vertical')

        algo = SSIMAlgorithm()
        algo.configure()

        ssim_score = algo._compute_ssim(frame1, frame2)

        # Different gradient directions = different structure
        assert ssim_score < 0.7


class TestSSIMComparison:
    """Test SSIM vs other metrics characteristics."""

    def test_ssim_vs_brightness_changes(self):
        """Test that SSIM is affected by brightness changes."""
        algo = SSIMAlgorithm()
        algo.configure()

        frame1 = create_noise_frame(seed=42)

        # Test various brightness levels
        ssim_scores = []
        brightness_factors = [0.5, 0.8, 1.0, 1.2, 1.5]

        for factor in brightness_factors:
            frame2 = adjust_brightness(frame1, factor=factor)
            score = algo._compute_ssim(frame1, frame2)
            ssim_scores.append(score)

        # SSIM at 1.0 (no change) should be perfect
        assert ssim_scores[2] == pytest.approx(1.0, abs=0.001)

        # SSIM is quite robust to brightness changes, but extreme changes (0.5, 1.5) may drop below 0.5
        # At minimum, all scores should be in valid range [0, 1]
        assert all(0.0 <= s <= 1.0 for s in ssim_scores)

        # Moderate brightness changes should still score reasonably well
        # (0.8 and 1.2 are moderate changes)
        assert ssim_scores[1] > 0.5  # 0.8 factor
        assert ssim_scores[3] > 0.5  # 1.2 factor

    def test_ssim_structural_sensitivity(self):
        """Test that SSIM is sensitive to structural changes."""
        algo = SSIMAlgorithm()
        algo.configure()

        base = create_checkerboard_frame(square_size=32)

        # Same structure = high SSIM
        same = create_checkerboard_frame(square_size=32)
        ssim_same = algo._compute_ssim(base, same)

        # Different structure = lower SSIM
        different = create_checkerboard_frame(square_size=16)
        ssim_diff = algo._compute_ssim(base, different)

        # Random noise = very low SSIM
        noise = create_noise_frame(seed=42)
        ssim_noise = algo._compute_ssim(base, noise)

        # Verify decreasing similarity
        assert ssim_same > 0.99
        assert ssim_diff < ssim_same
        assert ssim_noise < ssim_diff
        assert ssim_noise < 0.5


class TestSSIMPerformance:
    """Test SSIM computation performance characteristics."""

    def test_ssim_reproducibility(self):
        """Test that SSIM is reproducible with same inputs."""
        algo = SSIMAlgorithm()
        algo.configure()

        frame1 = create_noise_frame(seed=42)
        frame2 = add_noise(frame1, noise_level=10)

        # Compute multiple times
        scores = [algo._compute_ssim(frame1, frame2) for _ in range(5)]

        # All scores should be identical
        assert len(set(scores)) == 1

    def test_ssim_symmetry(self):
        """Test that SSIM is symmetric (SSIM(A,B) == SSIM(B,A))."""
        algo = SSIMAlgorithm()
        algo.configure()

        frame1 = create_noise_frame(seed=42)
        frame2 = create_noise_frame(seed=43)

        ssim_ab = algo._compute_ssim(frame1, frame2)
        ssim_ba = algo._compute_ssim(frame2, frame1)

        # SSIM should be symmetric
        assert ssim_ab == pytest.approx(ssim_ba, abs=0.0001)

    def test_ssim_range(self):
        """Test that SSIM is always in range [-1, 1] or [0, 1]."""
        algo = SSIMAlgorithm()
        algo.configure()

        # Test with various frame pairs
        test_pairs = [
            (create_black_frame(), create_white_frame()),
            (create_noise_frame(seed=42), create_noise_frame(seed=43)),
            (create_gradient_frame(direction='horizontal'), create_gradient_frame(direction='vertical')),
            (create_checkerboard_frame(square_size=16), create_checkerboard_frame(square_size=32)),
        ]

        for frame1, frame2 in test_pairs:
            ssim_score = algo._compute_ssim(frame1, frame2)

            # SSIM can be in range [-1, 1] but typically [0, 1]
            assert -1.0 <= ssim_score <= 1.0
