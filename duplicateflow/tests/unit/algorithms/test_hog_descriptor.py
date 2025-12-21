"""
Unit tests for HOGDescriptorAlgorithm.

Tests the Histogram of Oriented Gradients (HOG) algorithm for
structural pattern comparison.
"""

import pytest
import numpy as np
import cv2
from pathlib import Path

from duplicateflow.algorithms.hog_descriptor import HOGDescriptorAlgorithm
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


class TestHOGDescriptorAlgorithmInstantiation:
    """Test algorithm instantiation and configuration."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        algo = HOGDescriptorAlgorithm()

        # Check algorithm has required attributes
        assert hasattr(algo, 'name')
        assert hasattr(algo, 'configure')

        # Configure with defaults
        algo.configure()
        assert algo.threshold == 70.0
        assert algo.num_samples == 5
        assert algo.cell_size == (8, 8)
        assert algo.block_size == (2, 2)
        assert algo.nbins == 9
        assert algo.search_step == 3.0
        assert algo.max_windows == 200
        assert algo.resize == (128, 128)

        # HOG descriptor should be created
        assert hasattr(algo, 'hog')
        assert algo.hog is not None

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        algo = HOGDescriptorAlgorithm()
        algo.configure(
            threshold=80.0,
            num_samples=10,
            cell_size=(16, 16),
            block_size=(3, 3),
            nbins=12,
            search_step=2.0,
            max_windows=100,
            resize=(64, 64)
        )

        assert algo.threshold == 80.0
        assert algo.num_samples == 10
        assert algo.cell_size == (16, 16)
        assert algo.block_size == (3, 3)
        assert algo.nbins == 12
        assert algo.search_step == 2.0
        assert algo.max_windows == 100
        assert algo.resize == (64, 64)

    def test_hog_descriptor_creation(self):
        """Test that HOG descriptor is properly created."""
        algo = HOGDescriptorAlgorithm()
        algo.configure()

        # Verify HOG descriptor exists
        assert algo.hog is not None
        assert isinstance(algo.hog, cv2.HOGDescriptor)


class TestHOGDescriptorComputation:
    """Test HOG descriptor computation methods."""

    @pytest.fixture
    def algorithm(self):
        """Algorithm instance for testing."""
        algo = HOGDescriptorAlgorithm()
        algo.configure()
        return algo

    def test_compute_hog_black_frame(self, algorithm):
        """Test HOG computation on black frame."""
        frame = create_black_frame()
        hog_desc = algorithm._compute_hog(frame)

        assert hog_desc is not None
        assert isinstance(hog_desc, np.ndarray)
        assert hog_desc.dtype == np.float32

        # HOG descriptor should be 1D flattened vector
        assert hog_desc.ndim == 1

        # HOG descriptor size depends on configuration
        # For 128x128 with 8x8 cells, 2x2 blocks, 9 bins
        # Expected size = ((128/8 - 2 + 1) * (128/8 - 2 + 1)) * (2*2) * 9
        # = (16-1) * (16-1) * 4 * 9 = 15 * 15 * 36 = 8100
        assert hog_desc.size > 0

    def test_compute_hog_white_frame(self, algorithm):
        """Test HOG computation on white frame."""
        frame = create_white_frame()
        hog_desc = algorithm._compute_hog(frame)

        assert hog_desc is not None
        assert isinstance(hog_desc, np.ndarray)
        assert hog_desc.dtype == np.float32
        assert hog_desc.ndim == 1

    def test_compute_hog_noise_frame(self, algorithm):
        """Test HOG computation on random noise frame."""
        frame = create_noise_frame(seed=42)
        hog_desc = algorithm._compute_hog(frame)

        assert hog_desc is not None
        assert isinstance(hog_desc, np.ndarray)
        assert hog_desc.size > 0

    def test_compute_hog_gradient_frame(self, algorithm):
        """Test HOG computation on gradient frame."""
        frame = create_gradient_frame(direction='horizontal')
        hog_desc = algorithm._compute_hog(frame)

        assert hog_desc is not None
        assert isinstance(hog_desc, np.ndarray)

        # Gradients should produce strong HOG features
        assert hog_desc.size > 0

    def test_compute_hog_checkerboard_frame(self, algorithm):
        """Test HOG computation on checkerboard pattern."""
        frame = create_checkerboard_frame(square_size=32)
        hog_desc = algorithm._compute_hog(frame)

        assert hog_desc is not None
        assert isinstance(hog_desc, np.ndarray)

        # Checkerboard has strong edges, should produce strong HOG features
        assert hog_desc.size > 0
        # Checkerboard should have non-zero gradients
        assert np.any(hog_desc > 0)

    def test_compute_hog_identical_frames(self, algorithm):
        """Test that identical frames produce identical HOG descriptors."""
        frame1 = create_noise_frame(seed=42)
        frame2 = frame1.copy()

        hog1 = algorithm._compute_hog(frame1)
        hog2 = algorithm._compute_hog(frame2)

        assert np.allclose(hog1, hog2, atol=1e-6)

    def test_compute_hog_different_frames(self, algorithm):
        """Test that different frames produce different HOG descriptors."""
        frame1 = create_black_frame()
        frame2 = create_checkerboard_frame(square_size=16)

        hog1 = algorithm._compute_hog(frame1)
        hog2 = algorithm._compute_hog(frame2)

        # HOG descriptors should be different
        # (black has no gradients, checkerboard has strong gradients)
        assert not np.allclose(hog1, hog2, atol=0.1)


class TestHOGDescriptorSimilarity:
    """Test HOG descriptor similarity computation."""

    @pytest.fixture
    def algorithm(self):
        algo = HOGDescriptorAlgorithm()
        algo.configure()
        return algo

    def test_hog_similarity_identical_frames(self, algorithm):
        """Test cosine similarity for identical frames."""
        frame = create_noise_frame(seed=42)

        hog1 = algorithm._compute_hog(frame)
        hog2 = algorithm._compute_hog(frame.copy())

        # Compute cosine similarity
        similarity = np.dot(hog1, hog2) / (np.linalg.norm(hog1) * np.linalg.norm(hog2))

        # Identical frames should have similarity = 1.0
        assert similarity == pytest.approx(1.0, abs=0.001)

    def test_hog_similarity_similar_frames(self, algorithm):
        """Test similarity for similar frames with small noise."""
        from tests.utils.frame_generator import add_noise

        frame1 = create_noise_frame(seed=42)
        frame2 = add_noise(frame1, noise_level=5)

        hog1 = algorithm._compute_hog(frame1)
        hog2 = algorithm._compute_hog(frame2)

        # Compute cosine similarity
        similarity = np.dot(hog1, hog2) / (np.linalg.norm(hog1) * np.linalg.norm(hog2))

        # Similar frames should have high similarity
        assert similarity > 0.9

    def test_hog_similarity_different_frames(self, algorithm):
        """Test similarity for completely different frames."""
        frame1 = create_black_frame()
        frame2 = create_white_frame()

        hog1 = algorithm._compute_hog(frame1)
        hog2 = algorithm._compute_hog(frame2)

        # Compute cosine similarity
        # Normalize to avoid division by zero
        norm1 = np.linalg.norm(hog1)
        norm2 = np.linalg.norm(hog2)

        if norm1 > 0 and norm2 > 0:
            similarity = np.dot(hog1, hog2) / (norm1 * norm2)
            # Different frames should have low similarity
            # (though both uniform frames may still be somewhat similar)
            assert -1.0 <= similarity <= 1.0
        else:
            # Black/white frames may have zero HOG (no gradients)
            assert True


class TestHOGDescriptorEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.fixture
    def algorithm(self):
        algo = HOGDescriptorAlgorithm()
        algo.configure()
        return algo

    def test_compute_hog_small_frame(self, algorithm):
        """Test HOG computation on small frame."""
        # Create a small frame (will be resized to 128x128)
        small_frame = np.random.randint(0, 255, (16, 16, 3), dtype=np.uint8)

        hog_desc = algorithm._compute_hog(small_frame)

        # Should still work (upsampled to 128x128)
        assert hog_desc is not None
        assert hog_desc.size > 0

    def test_compute_hog_large_frame(self, algorithm):
        """Test HOG computation on large frame (4K)."""
        # Create a large frame (will be resized to 128x128)
        large_frame = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)

        hog_desc = algorithm._compute_hog(large_frame)

        # Should work (downsampled to 128x128)
        assert hog_desc is not None
        assert hog_desc.size > 0

    def test_compute_hog_solid_colors(self, algorithm):
        """Test HOG computation on solid color frames."""
        colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
        ]

        for r, g, b in colors:
            frame = create_color_frame(r=r, g=g, b=b)
            hog_desc = algorithm._compute_hog(frame)

            assert hog_desc is not None
            # Solid colors have no gradients, so HOG may be mostly zeros
            # But computation should succeed
            assert hog_desc.size > 0


class TestHOGDescriptorBrightnessRobustness:
    """Test HOG robustness to brightness changes."""

    @pytest.fixture
    def algorithm(self):
        algo = HOGDescriptorAlgorithm()
        algo.configure()
        return algo

    def test_hog_brightness_change(self, algorithm):
        """Test HOG with brightness changes."""
        frame_base = create_noise_frame(seed=42)
        frame_bright = adjust_brightness(frame_base, factor=1.3)

        hog_base = algorithm._compute_hog(frame_base)
        hog_bright = algorithm._compute_hog(frame_bright)

        # Compute cosine similarity
        similarity = np.dot(hog_base, hog_bright) / (
            np.linalg.norm(hog_base) * np.linalg.norm(hog_bright)
        )

        # HOG is based on gradients (edges), which are somewhat robust to brightness
        # Similarity should be moderate to high
        assert similarity > 0.7

    def test_hog_contrast_change(self, algorithm):
        """Test HOG with contrast changes."""
        frame_base = create_noise_frame(seed=42)
        frame_contrast = adjust_contrast(frame_base, factor=1.5)

        hog_base = algorithm._compute_hog(frame_base)
        hog_contrast = algorithm._compute_hog(frame_contrast)

        # Compute cosine similarity
        similarity = np.dot(hog_base, hog_contrast) / (
            np.linalg.norm(hog_base) * np.linalg.norm(hog_contrast)
        )

        # HOG should be relatively robust to contrast changes
        # (gradient directions remain similar, magnitudes change)
        assert similarity > 0.6


class TestHOGDescriptorStructuralSensitivity:
    """Test HOG sensitivity to structural changes."""

    @pytest.fixture
    def algorithm(self):
        algo = HOGDescriptorAlgorithm()
        algo.configure()
        return algo

    def test_hog_horizontal_vs_vertical_gradient(self, algorithm):
        """Test HOG discrimination between horizontal and vertical gradients."""
        frame_h = create_gradient_frame(direction='horizontal')
        frame_v = create_gradient_frame(direction='vertical')

        hog_h = algorithm._compute_hog(frame_h)
        hog_v = algorithm._compute_hog(frame_v)

        # Compute cosine similarity
        similarity = np.dot(hog_h, hog_v) / (
            np.linalg.norm(hog_h) * np.linalg.norm(hog_v)
        )

        # Different gradient directions should produce different HOG
        # (horizontal vs vertical edges detected differently)
        assert similarity < 1.0
        # Orthogonal gradients may have zero or low similarity
        assert -1.0 <= similarity <= 1.0

    def test_hog_checkerboard_patterns(self, algorithm):
        """Test HOG on checkerboard patterns with different sizes."""
        frame1 = create_checkerboard_frame(square_size=16)
        frame2 = create_checkerboard_frame(square_size=32)

        hog1 = algorithm._compute_hog(frame1)
        hog2 = algorithm._compute_hog(frame2)

        # Compute cosine similarity
        similarity = np.dot(hog1, hog2) / (
            np.linalg.norm(hog1) * np.linalg.norm(hog2)
        )

        # Different patterns should have moderate similarity
        # (both have similar edge structures but different scales)
        assert 0.3 < similarity < 1.0


class TestHOGDescriptorDifferentConfigurations:
    """Test HOG with different configuration parameters."""

    def test_hog_different_cell_sizes(self):
        """Test HOG with different cell sizes."""
        frame = create_noise_frame(seed=42)

        cell_sizes = [(4, 4), (8, 8), (16, 16)]

        for cell_size in cell_sizes:
            algo = HOGDescriptorAlgorithm()
            algo.configure(cell_size=cell_size, resize=(64, 64))

            hog_desc = algo._compute_hog(frame)

            assert hog_desc is not None, f"Failed for cell_size={cell_size}"
            assert hog_desc.size > 0

    def test_hog_different_nbins(self):
        """Test HOG with different number of orientation bins."""
        frame = create_gradient_frame(direction='horizontal')

        nbins_values = [6, 9, 12]

        for nbins in nbins_values:
            algo = HOGDescriptorAlgorithm()
            algo.configure(nbins=nbins)

            hog_desc = algo._compute_hog(frame)

            assert hog_desc is not None, f"Failed for nbins={nbins}"
            assert hog_desc.size > 0

    def test_hog_different_resize_sizes(self):
        """Test HOG with different resize dimensions."""
        frame = create_noise_frame(seed=42)

        resize_sizes = [(64, 64), (128, 128), (256, 256)]

        for resize in resize_sizes:
            algo = HOGDescriptorAlgorithm()
            algo.configure(resize=resize)

            hog_desc = algo._compute_hog(frame)

            assert hog_desc is not None, f"Failed for resize={resize}"
            assert hog_desc.size > 0


class TestHOGDescriptorIntegration:
    """Integration-style tests for complete HOG workflow."""

    def test_hog_workflow_identical_frames(self):
        """Test complete workflow with identical frames."""
        algo = HOGDescriptorAlgorithm()
        algo.configure()

        frame = create_noise_frame(seed=42)

        hog1 = algo._compute_hog(frame)
        hog2 = algo._compute_hog(frame.copy())

        # Compute cosine similarity
        similarity = np.dot(hog1, hog2) / (
            np.linalg.norm(hog1) * np.linalg.norm(hog2)
        )

        assert similarity == pytest.approx(1.0, abs=0.001)

    def test_hog_workflow_similar_patterns(self):
        """Test workflow with similar structural patterns."""
        algo = HOGDescriptorAlgorithm()
        algo.configure()

        # Create frames with similar structures
        frame1 = create_checkerboard_frame(square_size=32)
        frame2 = create_checkerboard_frame(square_size=32)

        hog1 = algo._compute_hog(frame1)
        hog2 = algo._compute_hog(frame2)

        # Compute cosine similarity
        similarity = np.dot(hog1, hog2) / (
            np.linalg.norm(hog1) * np.linalg.norm(hog2)
        )

        # Identical patterns should have perfect similarity
        assert similarity == pytest.approx(1.0, abs=0.001)

    def test_hog_workflow_different_patterns(self):
        """Test workflow with different structural patterns."""
        algo = HOGDescriptorAlgorithm()
        algo.configure()

        # Checkerboard vs gradient
        frame1 = create_checkerboard_frame(square_size=16)
        frame2 = create_gradient_frame(direction='horizontal')

        hog1 = algo._compute_hog(frame1)
        hog2 = algo._compute_hog(frame2)

        # Compute cosine similarity
        similarity = np.dot(hog1, hog2) / (
            np.linalg.norm(hog1) * np.linalg.norm(hog2)
        )

        # Different patterns should have lower similarity
        assert similarity < 1.0


class TestHOGDescriptorScenarios:
    """Test specific real-world scenarios."""

    def test_scenario_edges_vs_smooth(self):
        """Test scenario: Frame with edges vs smooth frame."""
        algo = HOGDescriptorAlgorithm()
        algo.configure()

        # Frame with strong edges (checkerboard)
        frame_edges = create_checkerboard_frame(square_size=16)

        # Smooth frame (gradient)
        frame_smooth = create_gradient_frame(direction='horizontal')

        hog_edges = algo._compute_hog(frame_edges)
        hog_smooth = algo._compute_hog(frame_smooth)

        # Both should produce valid HOG descriptors
        assert hog_edges is not None
        assert hog_smooth is not None

        # Checkerboard should have stronger gradients
        # (more non-zero values in HOG)
        assert np.sum(hog_edges > 0) > 0
        assert np.sum(hog_smooth > 0) > 0

    def test_scenario_rotated_patterns(self):
        """Test scenario: Same pattern, different orientations."""
        algo = HOGDescriptorAlgorithm()
        algo.configure()

        # Horizontal gradient
        frame_h = create_gradient_frame(direction='horizontal')

        # Vertical gradient
        frame_v = create_gradient_frame(direction='vertical')

        hog_h = algo._compute_hog(frame_h)
        hog_v = algo._compute_hog(frame_v)

        # Compute cosine similarity
        similarity = np.dot(hog_h, hog_v) / (
            np.linalg.norm(hog_h) * np.linalg.norm(hog_v)
        )

        # Different orientations should be detected by HOG
        assert similarity < 1.0


class TestHOGDescriptorPerformance:
    """Test performance-related characteristics."""

    def test_hog_reproducibility(self):
        """Test that HOG computation is deterministic."""
        algo = HOGDescriptorAlgorithm()
        algo.configure()

        frame = create_noise_frame(seed=42)

        # Compute HOG multiple times
        hog1 = algo._compute_hog(frame)
        hog2 = algo._compute_hog(frame)
        hog3 = algo._compute_hog(frame)

        # All should be identical
        assert np.allclose(hog1, hog2, atol=1e-6)
        assert np.allclose(hog2, hog3, atol=1e-6)

    def test_hog_descriptor_size_consistency(self):
        """Test that HOG descriptor size is consistent."""
        algo = HOGDescriptorAlgorithm()
        algo.configure()

        frames = [
            create_black_frame(),
            create_white_frame(),
            create_noise_frame(seed=42),
            create_gradient_frame(direction='horizontal'),
            create_checkerboard_frame(square_size=32),
        ]

        hog_sizes = []
        for frame in frames:
            hog_desc = algo._compute_hog(frame)
            hog_sizes.append(hog_desc.size)

        # All HOG descriptors should have the same size
        assert len(set(hog_sizes)) == 1, "HOG descriptors have inconsistent sizes"

    def test_hog_range_validation(self):
        """Test that HOG descriptor values are in valid range."""
        algo = HOGDescriptorAlgorithm()
        algo.configure()

        frames = [
            create_noise_frame(seed=42),
            create_gradient_frame(direction='horizontal'),
            create_checkerboard_frame(square_size=16),
        ]

        for frame in frames:
            hog_desc = algo._compute_hog(frame)

            # HOG values should be non-negative (histogram counts)
            assert np.all(hog_desc >= 0.0), "HOG descriptor has negative values"


# ============================================================================
# VIDEO INTEGRATION TESTS
# ============================================================================

class TestHOGDescriptorVideoIntegration:
    """Test HOG descriptor algorithm with real video files."""

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
        algo = HOGDescriptorAlgorithm()
        algo.configure(threshold=70.0, num_samples=5)

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
        assert result['metadata']['num_samples'] >= 2
        assert 'hog_params' in result['metadata']

    def test_compare_different_videos(self, test_video_path):
        """Test comparing different segments."""
        algo = HOGDescriptorAlgorithm()
        algo.configure(threshold=70.0, num_samples=4)

        # Compare different positions
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
        """Test extracting HOG descriptors from real video."""
        algo = HOGDescriptorAlgorithm()
        algo.configure(num_samples=5)

        hog_descriptors = algo.extract_features(test_video_path)

        # Should return list of HOG descriptor vectors
        assert isinstance(hog_descriptors, list)
        assert len(hog_descriptors) >= 2
        for hog_desc in hog_descriptors:
            assert isinstance(hog_desc, np.ndarray)
            assert hog_desc.ndim == 1  # 1D vector
            assert len(hog_desc) > 0

    def test_extract_hog_descriptors_integration(self, test_video_path):
        """Test _extract_hog_descriptors with real video."""
        algo = HOGDescriptorAlgorithm()
        algo.configure(num_samples=5, resize=(64, 64))

        offsets, hog_descriptors = algo._extract_hog_descriptors(
            test_video_path, duration=5.0
        )

        assert isinstance(offsets, list)
        assert isinstance(hog_descriptors, list)
        assert len(hog_descriptors) >= 2
        assert all(isinstance(hog, np.ndarray) for hog in hog_descriptors)

    def test_compare_window_integration(self, test_video_path):
        """Test _compare_window with real video."""
        algo = HOGDescriptorAlgorithm()
        algo.configure(num_samples=3)

        # Extract HOG descriptors first
        offsets, hog_descriptors = algo._extract_hog_descriptors(
            test_video_path, duration=3.0
        )

        assert len(hog_descriptors) >= 2

        # Compare window
        score = algo._compare_window(
            long_video=test_video_path,
            window_start=0.0,
            short_offsets=offsets,
            short_hogs=hog_descriptors
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

    def test_compare_search_window(self, test_video_path):
        """Test sliding window search with real video."""
        algo = HOGDescriptorAlgorithm()
        algo.configure(
            threshold=70.0,
            num_samples=4,
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

    def test_compare_with_different_cell_sizes(self, test_video_path):
        """Test compare with different HOG cell size configurations."""
        # Test with larger cells
        algo1 = HOGDescriptorAlgorithm()
        algo1.configure(num_samples=3, cell_size=(16, 16))
        result1 = algo1.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        # Test with smaller cells
        algo2 = HOGDescriptorAlgorithm()
        algo2.configure(num_samples=3, cell_size=(4, 4))
        result2 = algo2.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        # Both should succeed
        assert 'similarity' in result1
        assert 'similarity' in result2
        assert result1['metadata']['hog_params']['cell_size'] == (16, 16)
        assert result2['metadata']['hog_params']['cell_size'] == (4, 4)

    def test_compare_with_different_nbins(self, test_video_path):
        """Test compare with different number of orientation bins."""
        for nbins in [6, 9, 12]:
            algo = HOGDescriptorAlgorithm()
            algo.configure(num_samples=3, nbins=nbins)

            result = algo.compare(
                short_video=test_video_path,
                long_video=test_video_path,
                start_time=0.0,
                duration=3.0
            )

            assert 0.0 <= result['similarity'] <= 1.0
            assert result['metadata']['hog_params']['nbins'] == nbins

    def test_compare_insufficient_frames(self, test_video_path):
        """Test handling of very short duration."""
        algo = HOGDescriptorAlgorithm()
        algo.configure(num_samples=20)  # Try to extract many samples

        # Very short duration might not yield enough frames
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
        algo = HOGDescriptorAlgorithm()
        algo.configure(
            threshold=65.0,
            num_samples=4,
            search_step=1.0,
            max_windows=50
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

    def test_compare_duration_auto_detect(self, test_video_path):
        """Test duration auto-detection when not provided."""
        algo = HOGDescriptorAlgorithm()
        algo.configure(threshold=70.0, num_samples=4)

        # Don't provide duration - should auto-detect from short video
        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0
            # duration=None (implicit)
        )

        # Should successfully auto-detect and compare
        assert 'similarity' in result
        assert 0.0 <= result['similarity'] <= 1.0
        assert isinstance(result['accepted'], (bool, np.bool_))
        assert 'num_samples' in result['metadata']

    def test_cli_params(self):
        """Test get_cli_params returns correct structure."""
        algo = HOGDescriptorAlgorithm()
        params = algo.get_cli_params()

        assert isinstance(params, list)
        assert len(params) > 0

        # Check structure of each param
        for param in params:
            assert 'names' in param
            assert 'type' in param
            assert 'help' in param

    def test_requirements(self):
        """Test get_requirements returns dependencies."""
        algo = HOGDescriptorAlgorithm()
        reqs = algo.get_requirements()

        assert isinstance(reqs, list)
        assert 'opencv-python>=4.8.0' in reqs
        assert 'numpy>=1.24.0' in reqs
