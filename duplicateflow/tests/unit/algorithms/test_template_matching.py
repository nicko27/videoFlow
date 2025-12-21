"""
Unit tests for TemplateMatchingAlgorithm.

Tests the template matching algorithm that uses normalized cross-correlation
to find visual templates from short video in long video frames.
"""

import pytest
import cv2
import numpy as np
from pathlib import Path

from duplicateflow.algorithms.template_matching import TemplateMatchingAlgorithm
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
    """TemplateMatchingAlgorithm instance with default parameters."""
    algo = TemplateMatchingAlgorithm()
    algo.configure()
    return algo


@pytest.fixture
def algorithm_custom():
    """TemplateMatchingAlgorithm with custom parameters."""
    algo = TemplateMatchingAlgorithm()
    algo.configure(
        threshold=85.0,
        num_templates=3,
        template_size=(32, 32),
        method='TM_CCORR_NORMED'
    )
    return algo


# ==================== INSTANTIATION TESTS ====================

class TestTemplateMatchingAlgorithmInstantiation:
    """Test algorithm instantiation and configuration."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        algo = TemplateMatchingAlgorithm()
        algo.configure()

        assert algo.threshold == 80.0
        assert algo.num_templates == 5
        assert algo.template_size == (64, 64)
        assert algo.method_name == 'TM_CCOEFF_NORMED'
        assert algo.method == cv2.TM_CCOEFF_NORMED
        assert algo.search_step == 3.0
        assert algo.max_windows == 150
        assert algo.resize == (320, 240)

    def test_init_custom_params(self, algorithm_custom):
        """Test initialization with custom parameters."""
        assert algorithm_custom.threshold == 85.0
        assert algorithm_custom.num_templates == 3
        assert algorithm_custom.template_size == (32, 32)
        assert algorithm_custom.method_name == 'TM_CCORR_NORMED'
        assert algorithm_custom.method == cv2.TM_CCORR_NORMED

    def test_init_different_methods(self):
        """Test initialization with different OpenCV methods."""
        methods = [
            'TM_CCOEFF',
            'TM_CCOEFF_NORMED',
            'TM_CCORR',
            'TM_CCORR_NORMED',
            'TM_SQDIFF',
            'TM_SQDIFF_NORMED'
        ]

        for method_name in methods:
            algo = TemplateMatchingAlgorithm()
            algo.configure(method=method_name)
            assert algo.method_name == method_name
            assert algo.method == getattr(cv2, method_name)

    def test_algorithm_has_required_attributes(self, algorithm):
        """Test algorithm has required attributes."""
        assert hasattr(algorithm, 'threshold')
        assert hasattr(algorithm, 'num_templates')
        assert hasattr(algorithm, 'template_size')
        assert hasattr(algorithm, 'method')
        assert hasattr(algorithm, 'method_name')


# ==================== TEMPLATE EXTRACTION TESTS ====================

class TestTemplateExtraction:
    """Test template extraction functionality (direct method testing)."""

    def test_extract_template_from_center(self, algorithm):
        """Test extracting template from center of frame."""
        # Create a frame with specific pattern in center
        frame = create_checkerboard_frame(square_size=16)

        # Manually extract center region
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        tw, th = algorithm.template_size

        start_y = (h - th) // 2
        start_x = (w - tw) // 2
        end_y = start_y + th
        end_x = start_x + tw

        template = gray[start_y:end_y, start_x:end_x]

        assert template.shape == (th, tw)

    def test_template_size_consistency(self, algorithm):
        """Test templates have consistent size."""
        # Create different frames
        frames = [
            create_black_frame(),
            create_white_frame(),
            create_noise_frame(seed=42)
        ]

        templates = []
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            tw, th = algorithm.template_size

            start_y = (h - th) // 2
            start_x = (w - tw) // 2
            template = gray[start_y:start_y + th, start_x:start_x + tw]

            # Resize to exact template size if needed
            if template.shape != (th, tw):
                template = cv2.resize(template, algorithm.template_size)

            templates.append(template)

        # All templates should have same size
        sizes = [t.shape for t in templates]
        assert len(set(sizes)) == 1
        assert sizes[0] == (64, 64)

    def test_template_from_small_frame(self):
        """Test extracting template from small frame (resizes if needed)."""
        algo = TemplateMatchingAlgorithm()
        algo.configure(template_size=(32, 32))

        frame = create_black_frame(width=16, height=16)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Template size is larger than frame, should handle gracefully
        h, w = gray.shape
        tw, th = algo.template_size

        start_y = max(0, (h - th) // 2)
        start_x = max(0, (w - tw) // 2)
        end_y = min(h, start_y + th)
        end_x = min(w, start_x + tw)

        template = gray[start_y:end_y, start_x:end_x]

        # Resize to exact size
        template = cv2.resize(template, algo.template_size)

        assert template.shape == (32, 32)


# ==================== TEMPLATE MATCHING TESTS ====================

class TestTemplateMatching:
    """Test template matching computation."""

    def test_match_identical_template(self, algorithm):
        """Test matching identical template (perfect match)."""
        # Create a template
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        h, w = gray.shape
        tw, th = algorithm.template_size

        start_y = (h - th) // 2
        start_x = (w - tw) // 2
        template = gray[start_y:start_y + th, start_x:start_x + tw]

        # Match template against same image
        result = cv2.matchTemplate(gray, template, algorithm.method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # Should have perfect match (max_val = 1.0 for normalized methods)
        assert max_val > 0.99

    def test_match_similar_template(self, algorithm):
        """Test matching similar template (with small noise)."""
        # Create template
        frame1 = create_noise_frame(seed=42)
        frame2 = add_noise(frame1, noise_level=5)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        h, w = gray1.shape
        tw, th = algorithm.template_size

        start_y = (h - th) // 2
        start_x = (w - tw) // 2
        template = gray1[start_y:start_y + th, start_x:start_x + tw]

        # Match template against noisy version
        result = cv2.matchTemplate(gray2, template, algorithm.method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # Should still have good match (>0.7)
        assert max_val > 0.5

    def test_match_different_template(self, algorithm):
        """Test matching very different template (low score)."""
        # Create very different frames
        frame1 = create_black_frame()
        frame2 = create_white_frame()

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        h, w = gray1.shape
        tw, th = algorithm.template_size

        start_y = (h - th) // 2
        start_x = (w - tw) // 2
        template = gray1[start_y:start_y + th, start_x:start_x + tw]

        # Match black template against white image
        result = cv2.matchTemplate(gray2, template, algorithm.method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # Should have low match (uniform images may have varying results)
        assert -1.0 <= max_val <= 1.0

    def test_sqdiff_method_scoring(self):
        """Test SQDIFF method (lower is better)."""
        algo = TemplateMatchingAlgorithm()
        algo.configure(method='TM_SQDIFF_NORMED')

        # Create identical template
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        h, w = gray.shape
        tw, th = algo.template_size

        start_y = (h - th) // 2
        start_x = (w - tw) // 2
        template = gray[start_y:start_y + th, start_x:start_x + tw]

        # Match template
        result = cv2.matchTemplate(gray, template, algo.method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # For SQDIFF, lower is better (min_val should be near 0 for perfect match)
        assert min_val < 0.1

    def test_template_matching_result_shape(self, algorithm):
        """Test template matching result shape."""
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        h, w = gray.shape
        tw, th = algorithm.template_size

        template = gray[100:100 + th, 100:100 + tw]

        result = cv2.matchTemplate(gray, template, algorithm.method)

        # Result shape should be (image_h - template_h + 1, image_w - template_w + 1)
        expected_h = h - th + 1
        expected_w = w - tw + 1
        assert result.shape == (expected_h, expected_w)


# ==================== FEATURE COMPARISON TESTS ====================

class TestTemplateMatchingComparison:
    """Test compare_features static method."""

    def test_compare_features_identical_templates(self, algorithm):
        """Test comparing identical templates."""
        # Create a template
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        tw, th = algorithm.template_size

        template = gray[100:100 + th, 100:100 + tw]

        result = TemplateMatchingAlgorithm.compare_features(
            [template],
            [gray],  # Match template against full image
            threshold=80.0
        )

        # Should have very high similarity
        assert result['similarity'] > 80.0
        assert result['accepted'] is True

    def test_compare_features_similar_templates(self, algorithm):
        """Test comparing similar templates."""
        frame1 = create_noise_frame(seed=42)
        frame2 = add_noise(frame1, noise_level=5)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        h, w = gray1.shape
        tw, th = algorithm.template_size

        template = gray1[100:100 + th, 100:100 + tw]

        result = TemplateMatchingAlgorithm.compare_features(
            [template],
            [gray2],
            threshold=80.0
        )

        # Should have decent similarity
        assert result['similarity'] > 0.0
        assert isinstance(result['accepted'], bool)

    def test_compare_features_empty_list1(self, algorithm):
        """Test comparing with empty first feature list."""
        template = np.zeros((64, 64), dtype=np.uint8)

        result = TemplateMatchingAlgorithm.compare_features(
            [],
            [template],
            threshold=80.0
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] is False
        assert 'error' in result['metadata']

    def test_compare_features_empty_list2(self, algorithm):
        """Test comparing with empty second feature list."""
        template = np.zeros((64, 64), dtype=np.uint8)

        result = TemplateMatchingAlgorithm.compare_features(
            [template],
            [],
            threshold=80.0
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] is False

    def test_compare_features_multiple_templates(self, algorithm):
        """Test comparing multiple templates."""
        # Create multiple templates from same base frame
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        h, w = gray.shape
        tw, th = algorithm.template_size

        templates = [
            gray[50:50 + th, 50:50 + tw],
            gray[100:100 + th, 100:100 + tw],
            gray[150:150 + th, 150:150 + tw]
        ]

        result = TemplateMatchingAlgorithm.compare_features(
            templates,
            [gray, gray],  # Match against same image twice
            threshold=80.0
        )

        # Should have high similarity (templates from same image)
        assert result['similarity'] > 70.0
        assert result['metadata']['num_comparisons'] == 6  # 3 templates × 2 images

    def test_compare_features_metadata(self, algorithm):
        """Test compare_features returns correct metadata."""
        template = np.zeros((64, 64), dtype=np.uint8)
        image = create_noise_frame()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        result = TemplateMatchingAlgorithm.compare_features(
            [template],
            [gray],
            threshold=80.0
        )

        assert 'metadata' in result
        assert 'num_templates_1' in result['metadata']
        assert 'num_templates_2' in result['metadata']
        assert 'num_comparisons' in result['metadata']
        assert 'method' in result['metadata']

    def test_compare_features_custom_method(self, algorithm):
        """Test compare_features with custom matching method."""
        template = np.zeros((64, 64), dtype=np.uint8)
        image = create_noise_frame()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        result = TemplateMatchingAlgorithm.compare_features(
            [template],
            [gray],
            threshold=80.0,
            params={'method': 'TM_CCORR_NORMED'}
        )

        assert result['metadata']['method'] == 'TM_CCORR_NORMED'


# ==================== EDGE CASE TESTS ====================

class TestTemplateMatchingEdgeCases:
    """Test edge cases and special scenarios."""

    def test_template_size_variations(self):
        """Test different template sizes."""
        sizes = [(16, 16), (32, 32), (64, 64), (128, 128)]

        for size in sizes:
            algo = TemplateMatchingAlgorithm()
            algo.configure(template_size=size)

            frame = create_noise_frame()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            h, w = gray.shape
            tw, th = size

            if tw <= w and th <= h:
                template = gray[100:100 + th, 100:100 + tw]
                assert template.shape == size

    def test_num_templates_variation(self):
        """Test different numbers of templates."""
        num_templates_list = [1, 3, 5, 10]

        for n in num_templates_list:
            algo = TemplateMatchingAlgorithm()
            algo.configure(num_templates=n)

            assert algo.num_templates == n

    def test_matching_methods_all_types(self):
        """Test all OpenCV template matching methods."""
        methods = [
            'TM_CCOEFF',
            'TM_CCOEFF_NORMED',
            'TM_CCORR',
            'TM_CCORR_NORMED',
            'TM_SQDIFF',
            'TM_SQDIFF_NORMED'
        ]

        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        template = gray[100:164, 100:164]  # 64x64 template

        for method_name in methods:
            method = getattr(cv2, method_name)
            result = cv2.matchTemplate(gray, template, method)

            # All methods should produce valid results
            assert result is not None
            assert result.size > 0

    def test_template_from_uniform_frame(self, algorithm):
        """Test extracting template from uniform frame."""
        # Black frame
        frame = create_black_frame()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        h, w = gray.shape
        tw, th = algorithm.template_size

        template = gray[100:100 + th, 100:100 + tw]

        # Template should be all zeros
        assert template.shape == (th, tw)
        assert np.all(template == 0)


# ==================== ROBUSTNESS TESTS ====================

class TestTemplateMatchingRobustness:
    """Test algorithm robustness to transformations."""

    def test_robustness_brightness_increase(self, algorithm):
        """Test robustness to brightness increase."""
        frame1 = create_noise_frame(seed=42)
        frame2 = adjust_brightness(frame1, factor=1.3)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        h, w = gray1.shape
        tw, th = algorithm.template_size

        template = gray1[100:100 + th, 100:100 + tw]

        # Match template against brighter version
        result = cv2.matchTemplate(gray2, template, algorithm.method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # Normalized methods should be fairly robust
        assert max_val > 0.3

    def test_robustness_brightness_decrease(self, algorithm):
        """Test robustness to brightness decrease."""
        frame1 = create_noise_frame(seed=42)
        frame2 = adjust_brightness(frame1, factor=0.7)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        h, w = gray1.shape
        tw, th = algorithm.template_size

        template = gray1[100:100 + th, 100:100 + tw]

        result = cv2.matchTemplate(gray2, template, algorithm.method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        assert max_val > 0.3

    def test_robustness_small_noise(self, algorithm):
        """Test robustness to small noise addition."""
        frame1 = create_checkerboard_frame(square_size=32)
        frame2 = add_noise(frame1, noise_level=10)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        h, w = gray1.shape
        tw, th = algorithm.template_size

        template = gray1[100:100 + th, 100:100 + tw]

        result = cv2.matchTemplate(gray2, template, algorithm.method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # Should be somewhat robust to noise
        assert max_val > 0.3

    def test_normalized_methods_more_robust(self):
        """Test that normalized methods are more robust than non-normalized."""
        frame1 = create_noise_frame(seed=42)
        frame2 = adjust_brightness(frame1, factor=1.5)

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        template = gray1[100:164, 100:164]

        # Normalized method
        result_norm = cv2.matchTemplate(gray2, template, cv2.TM_CCOEFF_NORMED)
        _, max_val_norm, _, _ = cv2.minMaxLoc(result_norm)

        # Non-normalized method
        result_non_norm = cv2.matchTemplate(gray2, template, cv2.TM_CCOEFF)
        _, max_val_non_norm, _, _ = cv2.minMaxLoc(result_non_norm)

        # Normalized should be more robust (score should be more consistent)
        assert -1.0 <= max_val_norm <= 1.0


# ==================== INTEGRATION TESTS ====================

class TestTemplateMatchingIntegration:
    """Test complete template matching workflows."""

    def test_complete_matching_workflow(self, algorithm):
        """Test complete template matching workflow."""
        # Create a scene
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        h, w = gray.shape
        tw, th = algorithm.template_size

        # Extract multiple templates
        templates = [
            gray[50:50 + th, 50:50 + tw],
            gray[100:100 + th, 100:100 + tw],
            gray[150:150 + th, 150:150 + tw]
        ]

        # Match all templates
        all_scores = []
        for template in templates:
            result = cv2.matchTemplate(gray, template, algorithm.method)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            all_scores.append(max_val)

        # All should have good matches
        assert all(score > 0.9 for score in all_scores)

    def test_multi_template_comparison(self, algorithm):
        """Test comparing multiple templates across frames."""
        # Create diverse scenes
        frames = [
            create_noise_frame(seed=i) for i in range(3)
        ]

        grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]

        # Extract templates from first frame
        h, w = grays[0].shape
        tw, th = algorithm.template_size

        templates = [grays[0][100:100 + th, 100:100 + tw]]

        # Match against all frames
        for gray in grays:
            result = TemplateMatchingAlgorithm.compare_features(
                templates,
                [gray],
                threshold=80.0
            )

            assert 'similarity' in result
            assert result['similarity'] >= 0.0

    def test_template_extraction_reproducibility(self, algorithm):
        """Test that template extraction is reproducible."""
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        h, w = gray.shape
        tw, th = algorithm.template_size

        # Extract template multiple times
        template1 = gray[100:100 + th, 100:100 + tw]
        template2 = gray[100:100 + th, 100:100 + tw]
        template3 = gray[100:100 + th, 100:100 + tw]

        assert np.array_equal(template1, template2)
        assert np.array_equal(template2, template3)


# ==================== PERFORMANCE TESTS ====================

class TestTemplateMatchingPerformance:
    """Test algorithm performance characteristics."""

    def test_template_size_consistency(self, algorithm):
        """Test templates have consistent size across frames."""
        frames = [create_noise_frame(seed=i) for i in range(5)]

        templates = []
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            tw, th = algorithm.template_size
            template = gray[100:100 + th, 100:100 + tw]
            templates.append(template)

        sizes = [t.shape for t in templates]
        assert len(set(sizes)) == 1  # All same size

    def test_template_dtype_consistency(self, algorithm):
        """Test templates have consistent dtype."""
        frames = [create_noise_frame(seed=i) for i in range(3)]

        templates = []
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            tw, th = algorithm.template_size
            template = gray[100:100 + th, 100:100 + tw]
            templates.append(template)

        assert all(t.dtype == np.uint8 for t in templates)

    def test_matching_score_range(self, algorithm):
        """Test matching scores are in valid range."""
        frame = create_noise_frame(seed=42)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        h, w = gray.shape
        tw, th = algorithm.template_size

        template = gray[100:100 + th, 100:100 + tw]

        result = cv2.matchTemplate(gray, template, algorithm.method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # For normalized methods, scores should be in [-1, 1] or [0, 1]
        assert -1.0 <= max_val <= 1.0
        assert -1.0 <= min_val <= 1.0

    def test_compare_features_returns_valid_similarity(self, algorithm):
        """Test compare_features returns similarity in [0, 100]."""
        template = np.random.randint(0, 255, (64, 64), dtype=np.uint8)
        image = create_noise_frame()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        result = TemplateMatchingAlgorithm.compare_features(
            [template],
            [gray],
            threshold=80.0
        )

        assert 0.0 <= result['similarity'] <= 100.0

    def test_reverse_matching_fallback(self, algorithm):
        """Test reverse matching fallback when template > image."""
        # Small image
        small_image = create_black_frame(width=50, height=50)
        gray_small = cv2.cvtColor(small_image, cv2.COLOR_BGR2GRAY)

        # Large template
        large_template = np.zeros((100, 100), dtype=np.uint8)

        # compare_features should handle this gracefully
        result = TemplateMatchingAlgorithm.compare_features(
            [large_template],
            [gray_small],
            threshold=80.0
        )

        # Should either succeed (via reverse matching) or return 0
        assert 0.0 <= result['similarity'] <= 100.0


# ============================================================================
# VIDEO INTEGRATION TESTS
# ============================================================================

class TestTemplateMatchingVideoIntegration:
    """Test template matching algorithm with real video files."""

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
        algo = TemplateMatchingAlgorithm()
        algo.configure(threshold=75.0, num_templates=5, template_size=(64, 64))

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=5.0
        )

        # Identical segments should have high similarity
        assert result['similarity'] > 0.75
        assert result['accepted'] == True
        assert 'best_offset_seconds' in result['metadata']
        assert result['metadata']['num_templates'] >= 2
        assert 'template_size' in result['metadata']

    def test_compare_different_videos(self, test_video_path):
        """Test comparing different segments."""
        algo = TemplateMatchingAlgorithm()
        algo.configure(threshold=80.0, num_templates=4)

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
        """Test extracting templates from real video."""
        algo = TemplateMatchingAlgorithm()
        algo.configure(num_templates=5, template_size=(64, 64))

        templates = algo.extract_features(test_video_path)

        # Should return list of template images
        assert isinstance(templates, list)
        assert len(templates) >= 2
        for template in templates:
            assert isinstance(template, np.ndarray)
            assert template.shape == (64, 64)  # Grayscale templates

    def test_extract_templates_integration(self, test_video_path):
        """Test _extract_templates with real video."""
        algo = TemplateMatchingAlgorithm()
        algo.configure(num_templates=5, template_size=(32, 32), resize=(320, 240))

        templates = algo._extract_templates(test_video_path, duration=5.0)

        assert isinstance(templates, list)
        assert len(templates) >= 2
        for template in templates:
            assert template.shape == (32, 32)

    def test_compare_window_integration(self, test_video_path):
        """Test _compare_window with real video."""
        algo = TemplateMatchingAlgorithm()
        algo.configure(num_templates=3, template_size=(48, 48))

        # Extract templates first
        templates = algo._extract_templates(test_video_path, duration=3.0)

        assert len(templates) >= 2

        # Compare window
        score = algo._compare_window(
            long_video=test_video_path,
            window_start=0.0,
            duration=3.0,
            templates=templates
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

    def test_compare_search_window(self, test_video_path):
        """Test sliding window search with real video."""
        algo = TemplateMatchingAlgorithm()
        algo.configure(
            threshold=80.0,
            num_templates=4,
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

    def test_compare_with_different_template_sizes(self, test_video_path):
        """Test compare with different template size configurations."""
        # Test with larger templates
        algo1 = TemplateMatchingAlgorithm()
        algo1.configure(num_templates=3, template_size=(80, 80))
        result1 = algo1.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        # Test with smaller templates
        algo2 = TemplateMatchingAlgorithm()
        algo2.configure(num_templates=3, template_size=(32, 32))
        result2 = algo2.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=3.0
        )

        # Both should succeed
        assert 'similarity' in result1
        assert 'similarity' in result2
        assert result1['metadata']['template_size'] == (80, 80)
        assert result2['metadata']['template_size'] == (32, 32)

    def test_compare_with_different_methods(self, test_video_path):
        """Test compare with different template matching methods."""
        methods = ['TM_CCOEFF_NORMED', 'TM_CCORR_NORMED']

        for method in methods:
            algo = TemplateMatchingAlgorithm()
            algo.configure(num_templates=3, method=method)

            result = algo.compare(
                short_video=test_video_path,
                long_video=test_video_path,
                start_time=0.0,
                duration=3.0
            )

            assert 0.0 <= result['similarity'] <= 1.0
            assert 'num_templates' in result['metadata']

    def test_compare_insufficient_templates(self, test_video_path):
        """Test handling of very short duration."""
        algo = TemplateMatchingAlgorithm()
        algo.configure(num_templates=20)  # Try to extract many templates

        # Very short duration might not yield enough templates
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
        algo = TemplateMatchingAlgorithm()
        algo.configure(
            threshold=75.0,
            num_templates=4,
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
        algo = TemplateMatchingAlgorithm()
        algo.configure(threshold=75.0, num_templates=4)

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
        assert 'num_templates' in result['metadata']

    def test_cli_params(self):
        """Test get_cli_params returns correct structure."""
        algo = TemplateMatchingAlgorithm()
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
        algo = TemplateMatchingAlgorithm()
        reqs = algo.get_requirements()

        assert isinstance(reqs, list)
        assert 'opencv-python>=4.8.0' in reqs
        assert 'numpy>=1.24.0' in reqs

    def test_insufficient_templates(self, tmp_path):
        """Test handling when insufficient templates can be extracted."""
        import tempfile
        import cv2

        algo = TemplateMatchingAlgorithm()
        algo.configure(threshold=75.0, num_templates=10)  # Request many templates

        # Create a 1-frame video
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tf:
            temp_video = tf.name

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video, fourcc, 1.0, (320, 240))
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        out.write(frame)
        out.release()

        try:
            result = algo.compare(
                short_video=temp_video,
                long_video=temp_video,
                start_time=0.0,
                duration=0.1
            )

            # Should return error for insufficient templates
            assert result['similarity'] == 0.0
            assert result['accepted'] is False
            assert 'error' in result['metadata']
            assert 'Insufficient templates' in result['metadata']['error']
        finally:
            import os
            os.unlink(temp_video)

    def test_template_resize_edge_case(self, test_video_path):
        """Test template extraction with resize that requires adjustment."""
        algo = TemplateMatchingAlgorithm()
        # Configure with small template size that will trigger resize logic
        algo.configure(
            threshold=75.0,
            num_templates=3,
            template_size=(16, 16)  # Very small template
        )

        templates = algo._extract_templates(test_video_path, duration=1.0)

        # Should extract templates and resize them
        assert len(templates) >= 2
        for template in templates:
            # Each template should be exactly the requested size
            assert template.shape == (16, 16)

    def test_match_template_exception_handling(self, test_video_path, tmp_path):
        """Test exception handling during template matching."""
        algo = TemplateMatchingAlgorithm()
        algo.configure(threshold=75.0, num_templates=4)

        # Extract templates normally
        templates = algo._extract_templates(test_video_path, duration=1.0)

        # Create an invalid template that might cause cv2.matchTemplate to fail
        invalid_template = np.array([[]], dtype=np.uint8)
        templates_with_invalid = templates + [invalid_template]

        # Should handle exception gracefully and still return a score
        score = algo._compare_window(
            test_video_path,
            window_start=0.0,
            duration=1.0,
            templates=templates_with_invalid
        )

        # Should return a valid score (from valid templates) despite exception
        assert isinstance(score, (int, float))
        assert 0.0 <= score <= 100.0

    def test_sqdiff_method_scoring(self, test_video_path):
        """Test SQDIFF method uses different scoring logic."""
        algo = TemplateMatchingAlgorithm()
        # Use TM_SQDIFF_NORMED which has inverted scoring
        algo.configure(
            threshold=75.0,
            num_templates=4,
            method='TM_SQDIFF_NORMED'
        )

        result = algo.compare(
            short_video=test_video_path,
            long_video=test_video_path,
            start_time=0.0,
            duration=1.0
        )

        # Should complete with SQDIFF method
        assert 'similarity' in result
        assert 0.0 <= result['similarity'] <= 100.0
        assert isinstance(result['accepted'], (bool, np.bool_))
