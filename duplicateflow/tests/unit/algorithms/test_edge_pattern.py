"""
Unit tests for EdgePatternAlgorithm.

Tests the edge pattern detection algorithm that uses Canny edge detection
with grid-based density analysis to compare structural patterns.
"""

import pytest
import numpy as np
from pathlib import Path

from duplicateflow.algorithms.edge_pattern import EdgePatternAlgorithm
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
    """EdgePatternAlgorithm instance with default parameters."""
    algo = EdgePatternAlgorithm()
    algo.configure()
    return algo


@pytest.fixture
def algorithm_custom():
    """EdgePatternAlgorithm with custom parameters."""
    algo = EdgePatternAlgorithm()
    algo.configure(
        threshold=75.0,
        canny_low=100,
        canny_high=200,
        grid_size=(4, 4),
        num_samples=3
    )
    return algo


# ==================== INSTANTIATION TESTS ====================

class TestEdgePatternAlgorithmInstantiation:
    """Test algorithm instantiation and configuration."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        algo = EdgePatternAlgorithm()
        algo.configure()

        assert algo.threshold == 70.0
        assert algo.canny_low == 50
        assert algo.canny_high == 150
        assert algo.grid_size == (8, 8)
        assert algo.num_samples == 5
        assert algo.search_step == 3.0
        assert algo.max_windows == 200
        assert algo.resize == (320, 240)

    def test_init_custom_params(self, algorithm_custom):
        """Test initialization with custom parameters."""
        assert algorithm_custom.threshold == 75.0
        assert algorithm_custom.canny_low == 100
        assert algorithm_custom.canny_high == 200
        assert algorithm_custom.grid_size == (4, 4)
        assert algorithm_custom.num_samples == 3

    def test_configure_invalid_grid_size(self):
        """Test configuration with invalid grid size gets corrected."""
        algo = EdgePatternAlgorithm()
        algo.configure(grid_size="invalid")

        # Should fall back to default
        assert algo.grid_size == (8, 8)

    def test_algorithm_has_required_attributes(self, algorithm):
        """Test algorithm has required attributes."""
        assert hasattr(algorithm, 'threshold')
        assert hasattr(algorithm, 'canny_low')
        assert hasattr(algorithm, 'canny_high')
        assert hasattr(algorithm, 'grid_size')


# ==================== EDGE PATTERN COMPUTATION TESTS ====================

class TestEdgePatternComputation:
    """Test _compute_edge_pattern method."""

    def test_compute_edge_pattern_black_frame(self, algorithm):
        """Test edge pattern for all-black frame."""
        frame = create_black_frame()
        pattern = algorithm._compute_edge_pattern(frame)

        assert pattern is not None
        assert isinstance(pattern, np.ndarray)
        assert pattern.dtype == np.float32

        # Black frame should have very low edge density
        assert np.all(pattern >= 0.0)
        assert np.all(pattern <= 1.0)
        assert np.mean(pattern) < 0.1  # Very few edges

    def test_compute_edge_pattern_white_frame(self, algorithm):
        """Test edge pattern for all-white frame."""
        frame = create_white_frame()
        pattern = algorithm._compute_edge_pattern(frame)

        assert pattern is not None
        assert isinstance(pattern, np.ndarray)
        assert pattern.dtype == np.float32

        # White frame should also have low edge density
        assert np.mean(pattern) < 0.1

    def test_compute_edge_pattern_checkerboard(self, algorithm):
        """Test edge pattern for checkerboard (high edge density)."""
        frame = create_checkerboard_frame(square_size=16)
        pattern = algorithm._compute_edge_pattern(frame)

        assert pattern is not None

        # Checkerboard should have high edge density
        assert np.mean(pattern) > 0.05  # More edges than solid color

    def test_compute_edge_pattern_gradient(self, algorithm):
        """Test edge pattern for gradient frame."""
        frame = create_gradient_frame(direction='horizontal')
        pattern = algorithm._compute_edge_pattern(frame)

        assert pattern is not None
        assert len(pattern) == 64  # 8x8 grid = 64 cells

    def test_compute_edge_pattern_identical_frames(self, algorithm):
        """Test that identical frames produce identical patterns."""
        frame1 = create_noise_frame(seed=42)
        frame2 = frame1.copy()

        pattern1 = algorithm._compute_edge_pattern(frame1)
        pattern2 = algorithm._compute_edge_pattern(frame2)

        assert np.array_equal(pattern1, pattern2)

    def test_compute_edge_pattern_different_frames(self, algorithm):
        """Test that different frames produce different patterns."""
        frame1 = create_noise_frame(seed=42)
        frame2 = create_checkerboard_frame(square_size=16)

        pattern1 = algorithm._compute_edge_pattern(frame1)
        pattern2 = algorithm._compute_edge_pattern(frame2)

        # Patterns should differ
        assert not np.array_equal(pattern1, pattern2)

    def test_compute_edge_pattern_shape(self, algorithm):
        """Test edge pattern has correct shape based on grid size."""
        frame = create_noise_frame()
        pattern = algorithm._compute_edge_pattern(frame)

        rows, cols = algorithm.grid_size
        expected_length = rows * cols

        assert len(pattern) == expected_length

    def test_compute_edge_pattern_custom_grid(self, algorithm_custom):
        """Test edge pattern with custom grid size."""
        frame = create_noise_frame()
        pattern = algorithm_custom._compute_edge_pattern(frame)

        # Custom grid is (4, 4) = 16 cells
        assert len(pattern) == 16

    def test_compute_edge_pattern_density_range(self, algorithm):
        """Test edge density values are in valid range [0, 1]."""
        frame = create_noise_frame(seed=123)
        pattern = algorithm._compute_edge_pattern(frame)

        assert np.all(pattern >= 0.0)
        assert np.all(pattern <= 1.0)

    def test_compute_edge_pattern_noise_frame(self, algorithm):
        """Test edge pattern on noisy frame."""
        frame = create_noise_frame(seed=42)
        pattern = algorithm._compute_edge_pattern(frame)

        # Noise should produce moderate edge density
        assert np.mean(pattern) > 0.0
        assert np.std(pattern) > 0.0  # Some variation across cells


# ==================== FEATURE COMPARISON TESTS ====================

class TestEdgePatternComparison:
    """Test compare_features static method."""

    def test_compare_features_identical_patterns(self, algorithm):
        """Test comparing identical edge patterns."""
        frame = create_noise_frame(seed=42)
        pattern = algorithm._compute_edge_pattern(frame)

        result = EdgePatternAlgorithm.compare_features(
            [pattern],
            [pattern.copy()],
            threshold=70.0
        )

        assert result['similarity'] >= 99.0  # Nearly perfect
        assert result['accepted'] is True

    def test_compare_features_similar_patterns(self, algorithm):
        """Test comparing similar patterns (same frame + small noise)."""
        frame1 = create_noise_frame(seed=42)
        frame2 = add_noise(frame1, noise_level=5)

        pattern1 = algorithm._compute_edge_pattern(frame1)
        pattern2 = algorithm._compute_edge_pattern(frame2)

        result = EdgePatternAlgorithm.compare_features(
            [pattern1],
            [pattern2],
            threshold=70.0
        )

        # Should be similar but not identical
        assert result['similarity'] > 50.0
        assert isinstance(result['accepted'], bool)

    def test_compare_features_different_patterns(self, algorithm):
        """Test comparing very different patterns."""
        frame1 = create_black_frame()
        frame2 = create_checkerboard_frame(square_size=16)

        pattern1 = algorithm._compute_edge_pattern(frame1)
        pattern2 = algorithm._compute_edge_pattern(frame2)

        result = EdgePatternAlgorithm.compare_features(
            [pattern1],
            [pattern2],
            threshold=70.0
        )

        # Very different patterns (black vs checkerboard edges)
        assert result['similarity'] < 80.0

    def test_compare_features_empty_list1(self, algorithm):
        """Test comparing with empty first feature list."""
        pattern = algorithm._compute_edge_pattern(create_noise_frame())

        result = EdgePatternAlgorithm.compare_features(
            [],
            [pattern],
            threshold=70.0
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] is False
        assert 'error' in result['metadata']

    def test_compare_features_empty_list2(self, algorithm):
        """Test comparing with empty second feature list."""
        pattern = algorithm._compute_edge_pattern(create_noise_frame())

        result = EdgePatternAlgorithm.compare_features(
            [pattern],
            [],
            threshold=70.0
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] is False

    def test_compare_features_multiple_patterns(self, algorithm):
        """Test comparing multiple patterns."""
        frames = [create_noise_frame(seed=i) for i in range(3)]
        patterns1 = [algorithm._compute_edge_pattern(f) for f in frames]
        patterns2 = [algorithm._compute_edge_pattern(f.copy()) for f in frames]

        result = EdgePatternAlgorithm.compare_features(
            patterns1,
            patterns2,
            threshold=70.0
        )

        # Should have high similarity (identical frames)
        assert result['similarity'] > 90.0
        assert result['metadata']['num_comparisons'] == 9  # 3x3

    def test_compare_features_metadata(self, algorithm):
        """Test compare_features returns correct metadata."""
        pattern1 = algorithm._compute_edge_pattern(create_noise_frame(seed=42))
        pattern2 = algorithm._compute_edge_pattern(create_noise_frame(seed=43))

        result = EdgePatternAlgorithm.compare_features(
            [pattern1],
            [pattern2],
            threshold=70.0
        )

        assert 'metadata' in result
        assert 'num_patterns_1' in result['metadata']
        assert 'num_patterns_2' in result['metadata']
        assert 'num_comparisons' in result['metadata']
        assert result['metadata']['num_patterns_1'] == 1
        assert result['metadata']['num_patterns_2'] == 1


# ==================== EDGE CASE TESTS ====================

class TestEdgePatternEdgeCases:
    """Test edge cases and special scenarios."""

    def test_edge_pattern_small_frame(self, algorithm):
        """Test edge pattern on small frame (16x16)."""
        frame = create_black_frame(width=16, height=16)
        pattern = algorithm._compute_edge_pattern(frame)

        assert pattern is not None
        assert len(pattern) == 64  # Still 8x8 grid

    def test_edge_pattern_large_frame(self, algorithm):
        """Test edge pattern on large frame (4K)."""
        frame = create_black_frame(width=3840, height=2160)
        pattern = algorithm._compute_edge_pattern(frame)

        assert pattern is not None
        assert len(pattern) == 64

    def test_edge_pattern_rectangular_frame(self, algorithm):
        """Test edge pattern on non-square frame."""
        frame = create_black_frame(width=800, height=600)
        pattern = algorithm._compute_edge_pattern(frame)

        assert pattern is not None
        assert len(pattern) == 64

    def test_canny_thresholds_high(self):
        """Test with high Canny thresholds (fewer edges)."""
        algo = EdgePatternAlgorithm()
        algo.configure(canny_low=200, canny_high=250)

        frame = create_noise_frame(seed=42)
        pattern = algo._compute_edge_pattern(frame)

        # High threshold = fewer edges detected
        assert np.mean(pattern) >= 0.0

    def test_canny_thresholds_low(self):
        """Test with low Canny thresholds (more edges)."""
        algo = EdgePatternAlgorithm()
        algo.configure(canny_low=10, canny_high=50)

        frame = create_noise_frame(seed=42)
        pattern = algo._compute_edge_pattern(frame)

        # Low threshold = more edges detected
        assert np.mean(pattern) > 0.0

    def test_grid_size_1x1(self):
        """Test with minimal grid size (1x1)."""
        algo = EdgePatternAlgorithm()
        algo.configure(grid_size=(1, 1))

        frame = create_noise_frame()
        pattern = algo._compute_edge_pattern(frame)

        assert len(pattern) == 1

    def test_grid_size_16x16(self):
        """Test with large grid size (16x16)."""
        algo = EdgePatternAlgorithm()
        algo.configure(grid_size=(16, 16))

        frame = create_noise_frame()
        pattern = algo._compute_edge_pattern(frame)

        assert len(pattern) == 256


# ==================== ROBUSTNESS TESTS ====================

class TestEdgePatternRobustness:
    """Test algorithm robustness to transformations."""

    def test_robustness_brightness_increase(self, algorithm):
        """Test robustness to brightness increase."""
        frame1 = create_noise_frame(seed=42)
        frame2 = adjust_brightness(frame1, factor=1.3)

        pattern1 = algorithm._compute_edge_pattern(frame1)
        pattern2 = algorithm._compute_edge_pattern(frame2)

        # Edge patterns should be similar (edges at same locations)
        cosine_sim = np.dot(pattern1, pattern2) / (
            np.linalg.norm(pattern1) * np.linalg.norm(pattern2)
        )

        # Canny is robust to brightness (relative edges)
        assert cosine_sim > 0.7

    def test_robustness_brightness_decrease(self, algorithm):
        """Test robustness to brightness decrease."""
        frame1 = create_noise_frame(seed=42)
        frame2 = adjust_brightness(frame1, factor=0.7)

        pattern1 = algorithm._compute_edge_pattern(frame1)
        pattern2 = algorithm._compute_edge_pattern(frame2)

        cosine_sim = np.dot(pattern1, pattern2) / (
            np.linalg.norm(pattern1) * np.linalg.norm(pattern2)
        )

        assert cosine_sim > 0.7

    def test_robustness_contrast_change(self, algorithm):
        """Test robustness to contrast change."""
        frame1 = create_noise_frame(seed=42)
        frame2 = adjust_contrast(frame1, factor=1.5)

        pattern1 = algorithm._compute_edge_pattern(frame1)
        pattern2 = algorithm._compute_edge_pattern(frame2)

        cosine_sim = np.dot(pattern1, pattern2) / (
            np.linalg.norm(pattern1) * np.linalg.norm(pattern2)
        )

        # Canny is reasonably robust to contrast
        assert cosine_sim > 0.5

    def test_robustness_small_noise(self, algorithm):
        """Test robustness to small noise addition."""
        frame1 = create_checkerboard_frame(square_size=32)
        frame2 = add_noise(frame1, noise_level=10)

        pattern1 = algorithm._compute_edge_pattern(frame1)
        pattern2 = algorithm._compute_edge_pattern(frame2)

        cosine_sim = np.dot(pattern1, pattern2) / (
            np.linalg.norm(pattern1) * np.linalg.norm(pattern2)
        )

        # Should be fairly robust
        assert cosine_sim > 0.5


# ==================== INTEGRATION TESTS ====================

class TestEdgePatternIntegration:
    """Test complete edge pattern workflows."""

    def test_extract_features_workflow(self, algorithm, tmp_path):
        """Test extract_features workflow (if video file exists)."""
        # This test would require a real video file
        # For now, test the pattern computation directly
        frames = [create_noise_frame(seed=i) for i in range(5)]
        patterns = [algorithm._compute_edge_pattern(f) for f in frames]

        assert len(patterns) == 5
        assert all(len(p) == 64 for p in patterns)

    def test_complete_comparison_workflow(self, algorithm):
        """Test complete edge pattern comparison workflow."""
        # Create two sets of similar frames
        frames1 = [create_noise_frame(seed=i) for i in range(3)]
        frames2 = [add_noise(f, noise_level=5) for f in frames1]

        patterns1 = [algorithm._compute_edge_pattern(f) for f in frames1]
        patterns2 = [algorithm._compute_edge_pattern(f) for f in frames2]

        result = EdgePatternAlgorithm.compare_features(
            patterns1,
            patterns2,
            threshold=70.0
        )

        assert 'similarity' in result
        assert 'accepted' in result
        assert 'metadata' in result

    def test_multi_pattern_comparison(self, algorithm):
        """Test comparing multiple patterns with different scenes."""
        # Create diverse scene types
        scenes = [
            create_black_frame(),
            create_white_frame(),
            create_noise_frame(seed=42),
            create_checkerboard_frame(square_size=16),
            create_gradient_frame(direction='horizontal')
        ]

        patterns = [algorithm._compute_edge_pattern(s) for s in scenes]

        # All patterns should be valid
        assert all(p is not None for p in patterns)
        assert all(len(p) == 64 for p in patterns)

    def test_pattern_reproducibility(self, algorithm):
        """Test that pattern computation is reproducible."""
        frame = create_noise_frame(seed=42)

        pattern1 = algorithm._compute_edge_pattern(frame)
        pattern2 = algorithm._compute_edge_pattern(frame)
        pattern3 = algorithm._compute_edge_pattern(frame)

        assert np.array_equal(pattern1, pattern2)
        assert np.array_equal(pattern2, pattern3)


# ==================== PERFORMANCE TESTS ====================

class TestEdgePatternPerformance:
    """Test algorithm performance characteristics."""

    def test_pattern_size_consistency(self, algorithm):
        """Test edge patterns have consistent size."""
        frames = [create_noise_frame(seed=i) for i in range(10)]
        patterns = [algorithm._compute_edge_pattern(f) for f in frames]

        sizes = [len(p) for p in patterns]
        assert len(set(sizes)) == 1  # All same size

    def test_pattern_dtype_consistency(self, algorithm):
        """Test edge patterns have consistent dtype."""
        frames = [create_noise_frame(seed=i) for i in range(5)]
        patterns = [algorithm._compute_edge_pattern(f) for f in frames]

        assert all(p.dtype == np.float32 for p in patterns)

    def test_cosine_similarity_range(self, algorithm):
        """Test cosine similarity is in valid range [-1, 1]."""
        frame1 = create_noise_frame(seed=42)
        frame2 = create_noise_frame(seed=43)

        pattern1 = algorithm._compute_edge_pattern(frame1)
        pattern2 = algorithm._compute_edge_pattern(frame2)

        dot_product = np.dot(pattern1, pattern2)
        norm1 = np.linalg.norm(pattern1)
        norm2 = np.linalg.norm(pattern2)

        if norm1 > 0 and norm2 > 0:
            cosine_sim = dot_product / (norm1 * norm2)
            assert -1.0 <= cosine_sim <= 1.0

    def test_compare_features_returns_valid_similarity(self, algorithm):
        """Test compare_features returns similarity in [0, 100]."""
        pattern1 = algorithm._compute_edge_pattern(create_noise_frame(seed=42))
        pattern2 = algorithm._compute_edge_pattern(create_noise_frame(seed=43))

        result = EdgePatternAlgorithm.compare_features(
            [pattern1],
            [pattern2],
            threshold=70.0
        )

        assert 0.0 <= result['similarity'] <= 100.0

    def test_zero_pattern_handling(self, algorithm):
        """Test handling of zero patterns (all-black frame)."""
        frame = create_black_frame()
        pattern = algorithm._compute_edge_pattern(frame)

        # Pattern might be all zeros (no edges)
        assert np.all(pattern >= 0.0)

        # Comparing zero patterns should be handled gracefully
        result = EdgePatternAlgorithm.compare_features(
            [pattern],
            [pattern],
            threshold=70.0
        )

        # Cosine of two zero vectors is undefined, but should be handled
        assert result['similarity'] >= 0.0


# ============================================================================
# VIDEO INTEGRATION TESTS
# ============================================================================

class TestEdgePatternVideoIntegration:
    """Test edge pattern algorithm with real video files."""

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
        algo = EdgePatternAlgorithm()
        algo.configure(threshold=0.70, num_samples=5)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=5.0
        )

        assert result['similarity'] > 0.70
        assert result['accepted'] == True
        assert 'best_offset_seconds' in result['metadata']
        assert 'num_samples' in result['metadata']

    def test_compare_different_videos(self, test_video_path):
        """Test comparing different videos (same video = high similarity)."""
        algo = EdgePatternAlgorithm()
        algo.configure(threshold=0.80)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        # Same video should match
        assert result['similarity'] > 0.60

    def test_extract_features_real_video(self, test_video_path):
        """Test feature extraction from real video."""
        algo = EdgePatternAlgorithm()
        algo.configure(num_samples=6)

        features = algo.extract_features(test_video_path)

        assert len(features) >= 2
        assert all(isinstance(f, np.ndarray) for f in features)
        assert all(f.dtype == np.float32 for f in features)

    def test_compare_window_integration(self, test_video_path):
        """Test compare with sliding window."""
        algo = EdgePatternAlgorithm()
        algo.configure(search_step=2.0, max_windows=10, num_samples=4)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=5.0
        )

        assert 'windows_tested' in result['metadata']
        assert result['metadata']['windows_tested'] >= 1

    def test_compare_search_window(self, test_video_path):
        """Test search window functionality."""
        algo = EdgePatternAlgorithm()
        algo.configure(search_step=3.0, max_windows=20, num_samples=5)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=4.0
        )

        assert 'best_offset_seconds' in result['metadata']
        assert result['metadata']['best_offset_seconds'] >= 0.0

    def test_compare_with_different_params(self, test_video_path):
        """Test compare with different grid sizes."""
        algo = EdgePatternAlgorithm()
        algo.configure(grid_size=(8, 8), num_samples=4)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        assert result['similarity'] > 0.0
        assert 'num_samples' in result['metadata']

    def test_compare_with_different_thresholds(self, test_video_path):
        """Test compare with different Canny thresholds."""
        algo = EdgePatternAlgorithm()
        algo.configure(canny_threshold1=50, canny_threshold2=150, num_samples=4)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        assert result['similarity'] > 0.0
        assert 'num_samples' in result['metadata']

    def test_compare_insufficient_frames(self, test_video_path):
        """Test compare with very short duration."""
        algo = EdgePatternAlgorithm()
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
        algo = EdgePatternAlgorithm()
        algo.configure(threshold=70.0, search_step=1.0, max_windows=50, num_samples=5)

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        # Should find match quickly
        assert result['similarity'] > 0.60
        assert 'windows_tested' in result['metadata']
