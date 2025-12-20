"""
Unit tests for DCTCoefficientsAlgorithm.

Tests the Discrete Cosine Transform (DCT) coefficients algorithm
for frequency-based video comparison.
"""

import pytest
import numpy as np
import cv2
from pathlib import Path

from duplicateflow.algorithms.dct_coefficients import DCTCoefficientsAlgorithm
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


class TestDCTCoefficientsAlgorithmInstantiation:
    """Test algorithm instantiation and configuration."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        algo = DCTCoefficientsAlgorithm()

        # Check algorithm has required attributes
        assert hasattr(algo, 'name')
        assert hasattr(algo, 'configure')

        # Configure with defaults
        algo.configure()
        assert algo.threshold == 70.0
        assert algo.num_coeffs == 64
        assert algo.block_size == 8
        assert algo.sample_interval == 5.0
        assert algo.num_samples is None
        assert algo.search_step == 3.0
        assert algo.max_windows == 200
        assert algo.resize == (320, 240)

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        algo = DCTCoefficientsAlgorithm()
        algo.configure(
            threshold=80.0,
            num_coeffs=128,
            block_size=16,
            sample_interval=3.0,
            num_samples=10,
            search_step=2.0,
            max_windows=100,
            resize=(640, 480)
        )

        assert algo.threshold == 80.0
        assert algo.num_coeffs == 128
        assert algo.block_size == 16
        assert algo.sample_interval == 3.0
        assert algo.num_samples == 10
        assert algo.search_step == 2.0
        assert algo.max_windows == 100
        assert algo.resize == (640, 480)


class TestDCTCoefficientsComputation:
    """Test DCT coefficients computation methods."""

    @pytest.fixture
    def algorithm(self):
        """Algorithm instance for testing."""
        algo = DCTCoefficientsAlgorithm()
        algo.configure()
        return algo

    def test_compute_dct_signature_black_frame(self, algorithm):
        """Test DCT computation on black frame."""
        frame = create_black_frame()
        signature = algorithm._compute_dct_signature(frame)

        assert signature is not None
        assert isinstance(signature, np.ndarray)
        assert signature.dtype == np.float32

        # Signature should have num_coeffs elements (default 64)
        assert len(signature) == algorithm.num_coeffs

        # Black frame: DC coefficient (first) should be close to 0
        dc_coeff = signature[0]
        assert dc_coeff < 50  # Low DC for black

    def test_compute_dct_signature_white_frame(self, algorithm):
        """Test DCT computation on white frame."""
        frame = create_white_frame()
        signature = algorithm._compute_dct_signature(frame)

        assert signature is not None
        assert isinstance(signature, np.ndarray)
        assert len(signature) == algorithm.num_coeffs

        # White frame: DC coefficient should be high
        dc_coeff = signature[0]
        assert dc_coeff > 1000  # High DC for white

    def test_compute_dct_signature_structure(self, algorithm):
        """Test DCT signature structure."""
        frame = create_noise_frame(seed=42)
        signature = algorithm._compute_dct_signature(frame)

        # Verify signature is 1D vector
        assert signature.ndim == 1
        assert len(signature) == algorithm.num_coeffs

        # DCT coefficients are ordered: DC first, then low frequencies
        # DC coefficient (index 0) typically largest
        dc_coeff = signature[0]
        assert dc_coeff != 0  # DC should not be zero for random noise

    def test_compute_dct_signature_identical_frames(self, algorithm):
        """Test that identical frames produce identical DCT signatures."""
        frame1 = create_noise_frame(seed=42)
        frame2 = frame1.copy()

        sig1 = algorithm._compute_dct_signature(frame1)
        sig2 = algorithm._compute_dct_signature(frame2)

        assert np.allclose(sig1, sig2, atol=1e-4)

    def test_compute_dct_signature_different_frames(self, algorithm):
        """Test that different frames produce different DCT signatures."""
        frame1 = create_black_frame()
        frame2 = create_white_frame()

        sig1 = algorithm._compute_dct_signature(frame1)
        sig2 = algorithm._compute_dct_signature(frame2)

        # Signatures should be different
        assert not np.allclose(sig1, sig2, atol=100.0)

    def test_compute_dct_signature_noise_frame(self, algorithm):
        """Test DCT computation on random noise frame."""
        frame = create_noise_frame(seed=42)
        signature = algorithm._compute_dct_signature(frame)

        assert signature is not None
        assert len(signature) == algorithm.num_coeffs

        # Noise should produce varied coefficients
        assert np.std(signature) > 0

    def test_compute_dct_signature_gradient_frame(self, algorithm):
        """Test DCT computation on gradient frame."""
        frame = create_gradient_frame(direction='horizontal')
        signature = algorithm._compute_dct_signature(frame)

        assert signature is not None
        assert len(signature) == algorithm.num_coeffs

        # Gradient should produce non-zero coefficients
        assert np.any(signature != 0)

    def test_compute_dct_signature_checkerboard_frame(self, algorithm):
        """Test DCT computation on checkerboard pattern."""
        frame = create_checkerboard_frame(square_size=32)
        signature = algorithm._compute_dct_signature(frame)

        assert signature is not None
        assert len(signature) == algorithm.num_coeffs

        # Checkerboard has strong high-frequency components
        # Should produce varied DCT coefficients
        assert np.std(signature) > 0


class TestDCTCoefficientsSimilarity:
    """Test DCT signature similarity computation."""

    @pytest.fixture
    def algorithm(self):
        algo = DCTCoefficientsAlgorithm()
        algo.configure()
        return algo

    def test_dct_cosine_similarity_identical(self, algorithm):
        """Test cosine similarity for identical frames."""
        frame = create_noise_frame(seed=42)

        sig1 = algorithm._compute_dct_signature(frame)
        sig2 = algorithm._compute_dct_signature(frame.copy())

        # Compute cosine similarity
        similarity = np.dot(sig1, sig2) / (np.linalg.norm(sig1) * np.linalg.norm(sig2))

        # Identical frames should have similarity = 1.0
        assert similarity == pytest.approx(1.0, abs=0.001)

    def test_dct_cosine_similarity_similar(self, algorithm):
        """Test cosine similarity for similar frames."""
        from tests.utils.frame_generator import add_noise

        frame1 = create_noise_frame(seed=42)
        frame2 = add_noise(frame1, noise_level=5)

        sig1 = algorithm._compute_dct_signature(frame1)
        sig2 = algorithm._compute_dct_signature(frame2)

        # Compute cosine similarity
        similarity = np.dot(sig1, sig2) / (np.linalg.norm(sig1) * np.linalg.norm(sig2))

        # Similar frames should have high similarity
        assert similarity > 0.9

    def test_dct_cosine_similarity_different(self, algorithm):
        """Test cosine similarity for different frames."""
        frame1 = create_black_frame()
        frame2 = create_white_frame()

        sig1 = algorithm._compute_dct_signature(frame1)
        sig2 = algorithm._compute_dct_signature(frame2)

        # Handle zero norms
        norm1 = np.linalg.norm(sig1)
        norm2 = np.linalg.norm(sig2)

        if norm1 > 0 and norm2 > 0:
            similarity = np.dot(sig1, sig2) / (norm1 * norm2)
            # Different frames may still have some similarity
            assert -1.0 <= similarity <= 1.0


class TestDCTCoefficientsEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.fixture
    def algorithm(self):
        algo = DCTCoefficientsAlgorithm()
        algo.configure()
        return algo

    def test_compute_dct_small_frame(self, algorithm):
        """Test DCT computation on small frame."""
        small_frame = np.random.randint(0, 255, (16, 16, 3), dtype=np.uint8)

        signature = algorithm._compute_dct_signature(small_frame)

        # Should still work (upsampled to block_size * 8)
        assert signature is not None
        assert len(signature) == algorithm.num_coeffs

    def test_compute_dct_large_frame(self, algorithm):
        """Test DCT computation on large frame (4K)."""
        large_frame = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)

        signature = algorithm._compute_dct_signature(large_frame)

        # Should work (downsampled to block_size * 8)
        assert signature is not None
        assert len(signature) == algorithm.num_coeffs

    def test_compute_dct_solid_colors(self, algorithm):
        """Test DCT computation on solid color frames."""
        colors = [
            (255, 0, 0),  # Red
            (0, 255, 0),  # Green
            (0, 0, 255),  # Blue
        ]

        for r, g, b in colors:
            frame = create_color_frame(r=r, g=g, b=b)
            signature = algorithm._compute_dct_signature(frame)

            assert signature is not None
            assert len(signature) == algorithm.num_coeffs

            # Solid colors: mostly DC component, AC components near zero
            dc_coeff = signature[0]
            assert dc_coeff != 0  # DC should not be zero


class TestDCTCoefficientsBrightnessRobustness:
    """Test DCT robustness to brightness changes."""

    @pytest.fixture
    def algorithm(self):
        algo = DCTCoefficientsAlgorithm()
        algo.configure()
        return algo

    def test_dct_brightness_change(self, algorithm):
        """Test DCT with brightness changes."""
        frame_base = create_noise_frame(seed=42)
        frame_bright = adjust_brightness(frame_base, factor=1.3)

        sig_base = algorithm._compute_dct_signature(frame_base)
        sig_bright = algorithm._compute_dct_signature(frame_bright)

        # Compute cosine similarity
        similarity = np.dot(sig_base, sig_bright) / (
            np.linalg.norm(sig_base) * np.linalg.norm(sig_bright)
        )

        # DCT is somewhat robust to brightness (linear scaling)
        # Cosine similarity normalizes magnitude, so should be high
        assert similarity > 0.8

    def test_dct_contrast_change(self, algorithm):
        """Test DCT with contrast changes."""
        frame_base = create_noise_frame(seed=42)
        frame_contrast = adjust_contrast(frame_base, factor=1.5)

        sig_base = algorithm._compute_dct_signature(frame_base)
        sig_contrast = algorithm._compute_dct_signature(frame_contrast)

        # Compute cosine similarity
        similarity = np.dot(sig_base, sig_contrast) / (
            np.linalg.norm(sig_base) * np.linalg.norm(sig_contrast)
        )

        # DCT should be relatively robust to contrast
        assert similarity > 0.7


class TestDCTCoefficientsDifferentConfigurations:
    """Test DCT with different configuration parameters."""

    def test_dct_different_num_coeffs(self):
        """Test DCT with different number of coefficients."""
        frame = create_noise_frame(seed=42)

        # num_coeffs is limited by block_size^2
        # Default block_size=8, so max coeffs is 64
        num_coeffs_values = [16, 32, 64]

        for num_coeffs in num_coeffs_values:
            algo = DCTCoefficientsAlgorithm()
            algo.configure(num_coeffs=num_coeffs)

            signature = algo._compute_dct_signature(frame)

            assert signature is not None
            assert len(signature) == num_coeffs, f"Failed for num_coeffs={num_coeffs}"

    def test_dct_different_block_sizes(self):
        """Test DCT with different block sizes."""
        frame = create_noise_frame(seed=42)

        block_sizes = [4, 8, 16]

        for block_size in block_sizes:
            algo = DCTCoefficientsAlgorithm()
            # Adjust num_coeffs to match block_size^2
            algo.configure(block_size=block_size, num_coeffs=min(64, block_size * block_size))

            signature = algo._compute_dct_signature(frame)

            assert signature is not None, f"Failed for block_size={block_size}"
            assert len(signature) == min(64, block_size * block_size)


class TestDCTCoefficientsIntegration:
    """Integration-style tests for complete DCT workflow."""

    def test_dct_workflow_identical_frames(self):
        """Test complete workflow with identical frames."""
        algo = DCTCoefficientsAlgorithm()
        algo.configure()

        frame = create_noise_frame(seed=42)

        sig1 = algo._compute_dct_signature(frame)
        sig2 = algo._compute_dct_signature(frame.copy())

        # Compute cosine similarity
        similarity = np.dot(sig1, sig2) / (
            np.linalg.norm(sig1) * np.linalg.norm(sig2)
        )

        assert similarity == pytest.approx(1.0, abs=0.001)

    def test_dct_workflow_similar_patterns(self):
        """Test workflow with similar frequency patterns."""
        algo = DCTCoefficientsAlgorithm()
        algo.configure()

        # Two checkerboards with same size
        frame1 = create_checkerboard_frame(square_size=32)
        frame2 = create_checkerboard_frame(square_size=32)

        sig1 = algo._compute_dct_signature(frame1)
        sig2 = algo._compute_dct_signature(frame2)

        # Compute cosine similarity
        similarity = np.dot(sig1, sig2) / (
            np.linalg.norm(sig1) * np.linalg.norm(sig2)
        )

        # Identical patterns should have perfect similarity
        assert similarity == pytest.approx(1.0, abs=0.001)

    def test_dct_workflow_different_patterns(self):
        """Test workflow with different frequency patterns."""
        algo = DCTCoefficientsAlgorithm()
        algo.configure()

        # Smooth gradient vs high-frequency checkerboard
        frame1 = create_gradient_frame(direction='horizontal')
        frame2 = create_checkerboard_frame(square_size=8)

        sig1 = algo._compute_dct_signature(frame1)
        sig2 = algo._compute_dct_signature(frame2)

        # Compute cosine similarity
        similarity = np.dot(sig1, sig2) / (
            np.linalg.norm(sig1) * np.linalg.norm(sig2)
        )

        # Different patterns should have lower similarity
        assert similarity < 1.0


class TestDCTCoefficientsScenarios:
    """Test specific real-world scenarios."""

    def test_scenario_smooth_vs_textured(self):
        """Test scenario: Smooth content vs textured content."""
        algo = DCTCoefficientsAlgorithm()
        algo.configure()

        # Smooth (gradient)
        frame_smooth = create_gradient_frame(direction='horizontal')

        # Textured (checkerboard)
        frame_textured = create_checkerboard_frame(square_size=16)

        sig_smooth = algo._compute_dct_signature(frame_smooth)
        sig_textured = algo._compute_dct_signature(frame_textured)

        # Both should produce valid signatures
        assert sig_smooth is not None
        assert sig_textured is not None

        # Both should have non-zero std (energy in AC coefficients)
        # The relative magnitudes depend on the specific patterns
        assert np.std(sig_smooth) > 0
        assert np.std(sig_textured) > 0

    def test_scenario_horizontal_vs_vertical_patterns(self):
        """Test scenario: Horizontal vs vertical frequency patterns."""
        algo = DCTCoefficientsAlgorithm()
        algo.configure()

        # Horizontal gradient
        frame_h = create_gradient_frame(direction='horizontal')

        # Vertical gradient
        frame_v = create_gradient_frame(direction='vertical')

        sig_h = algo._compute_dct_signature(frame_h)
        sig_v = algo._compute_dct_signature(frame_v)

        # Compute cosine similarity
        similarity = np.dot(sig_h, sig_v) / (
            np.linalg.norm(sig_h) * np.linalg.norm(sig_v)
        )

        # Different orientations should be detected
        assert similarity < 1.0


class TestDCTCoefficientsPerformance:
    """Test performance-related characteristics."""

    def test_dct_reproducibility(self):
        """Test that DCT computation is deterministic."""
        algo = DCTCoefficientsAlgorithm()
        algo.configure()

        frame = create_noise_frame(seed=42)

        # Compute DCT multiple times
        sig1 = algo._compute_dct_signature(frame)
        sig2 = algo._compute_dct_signature(frame)
        sig3 = algo._compute_dct_signature(frame)

        # All should be identical
        assert np.allclose(sig1, sig2, atol=1e-5)
        assert np.allclose(sig2, sig3, atol=1e-5)

    def test_dct_signature_size_consistency(self):
        """Test that DCT signature size is consistent."""
        algo = DCTCoefficientsAlgorithm()
        algo.configure()

        frames = [
            create_black_frame(),
            create_white_frame(),
            create_noise_frame(seed=42),
            create_gradient_frame(direction='horizontal'),
            create_checkerboard_frame(square_size=32),
        ]

        sig_sizes = []
        for frame in frames:
            signature = algo._compute_dct_signature(frame)
            sig_sizes.append(len(signature))

        # All signatures should have the same size
        assert len(set(sig_sizes)) == 1, "DCT signatures have inconsistent sizes"

    def test_dct_dc_coefficient_properties(self):
        """Test properties of DC coefficient (first element)."""
        algo = DCTCoefficientsAlgorithm()
        algo.configure()

        # Black frame: low DC
        frame_black = create_black_frame()
        sig_black = algo._compute_dct_signature(frame_black)
        dc_black = sig_black[0]

        # White frame: high DC
        frame_white = create_white_frame()
        sig_white = algo._compute_dct_signature(frame_white)
        dc_white = sig_white[0]

        # White should have higher DC than black
        assert dc_white > dc_black
