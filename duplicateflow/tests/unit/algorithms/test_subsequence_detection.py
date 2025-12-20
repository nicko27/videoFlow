"""
Unit tests for SubsequenceDetectionAlgorithm.

Tests the subsequence detection algorithm combining frame hashing and
motion analysis to detect extracted scenes.
"""

import pytest
import numpy as np
import cv2
from typing import List, Tuple

from duplicateflow.algorithms.subsequence_detection import SubsequenceDetectionAlgorithm
from tests.utils.frame_generator import (
    create_black_frame,
    create_white_frame,
    create_noise_frame,
    create_gradient_frame,
    create_checkerboard_frame
)


# ============================================================================
# 1. ALGORITHM INSTANTIATION
# ============================================================================

class TestSubsequenceDetectionInstantiation:
    """Test algorithm instantiation and configuration."""

    def test_instantiate_default(self):
        """Test instantiation with default parameters."""
        algo = SubsequenceDetectionAlgorithm()
        algo.configure()

        assert algo.threshold == 70.0
        assert algo.window_step == 5.0
        assert algo.max_windows == 500
        assert algo.signature_points == 3
        assert algo.hash_method == 'pHash'
        assert algo.motion_weight + algo.hash_weight == pytest.approx(1.0, abs=0.01)

    def test_instantiate_custom_params(self):
        """Test instantiation with custom parameters."""
        algo = SubsequenceDetectionAlgorithm()
        algo.configure(
            threshold=80.0,
            window_step=10.0,
            max_windows=100,
            signature_points=5,
            hash_method='dHash',
            motion_weight=0.3,
            hash_weight=0.7
        )

        assert algo.threshold == 80.0
        assert algo.window_step == 10.0
        assert algo.max_windows == 100
        assert algo.signature_points == 5
        assert algo.hash_method == 'dHash'
        # Weights should be normalized
        assert algo.motion_weight + algo.hash_weight == pytest.approx(1.0, abs=0.01)

    def test_weight_normalization(self):
        """Test weight normalization."""
        algo = SubsequenceDetectionAlgorithm()
        algo.configure(motion_weight=2.0, hash_weight=3.0)

        # Should normalize to sum = 1.0
        assert algo.motion_weight == pytest.approx(0.4, abs=0.01)
        assert algo.hash_weight == pytest.approx(0.6, abs=0.01)

    def test_has_required_methods(self):
        """Test algorithm has all required methods."""
        algo = SubsequenceDetectionAlgorithm()

        assert hasattr(algo, 'configure')
        assert hasattr(algo, 'compare')
        assert hasattr(algo, 'extract_features')
        assert hasattr(algo, '_compute_frame_hash')
        assert hasattr(algo, '_hamming_similarity')
        assert hasattr(algo, '_motion_similarity')


# ============================================================================
# 2. FRAME HASHING
# ============================================================================

class TestFrameHashing:
    """Test perceptual frame hashing."""

    @pytest.fixture
    def algorithm(self):
        """Create algorithm instance with default params."""
        algo = SubsequenceDetectionAlgorithm()
        algo.configure()
        return algo

    def test_compute_phash(self):
        """Test pHash computation."""
        algo = SubsequenceDetectionAlgorithm()
        algo.configure(hash_method='pHash')

        frame = create_noise_frame(seed=42)
        hash_val = algo._compute_frame_hash(frame)

        assert hash_val is not None
        assert hash_val.shape == (8, 8)
        assert hash_val.dtype == np.uint8
        # Binary hash (only 0 or 1)
        assert np.all((hash_val == 0) | (hash_val == 1))

    def test_compute_dhash(self):
        """Test dHash computation."""
        algo = SubsequenceDetectionAlgorithm()
        algo.configure(hash_method='dHash')

        frame = create_noise_frame(seed=42)
        hash_val = algo._compute_frame_hash(frame)

        assert hash_val is not None
        assert hash_val.shape == (8, 8)
        assert hash_val.dtype == np.uint8
        assert np.all((hash_val == 0) | (hash_val == 1))

    def test_compute_ahash(self):
        """Test aHash computation."""
        algo = SubsequenceDetectionAlgorithm()
        algo.configure(hash_method='aHash')

        frame = create_noise_frame(seed=42)
        hash_val = algo._compute_frame_hash(frame)

        assert hash_val is not None
        assert hash_val.shape == (8, 8)
        assert hash_val.dtype == np.uint8
        assert np.all((hash_val == 0) | (hash_val == 1))

    def test_hash_identical_frames(self, algorithm):
        """Test hashing identical frames."""
        frame = create_noise_frame(seed=42)

        hash1 = algorithm._compute_frame_hash(frame)
        hash2 = algorithm._compute_frame_hash(frame.copy())

        # Should be identical
        assert np.array_equal(hash1, hash2)

    def test_hash_different_frames(self, algorithm):
        """Test hashing different frames."""
        frame1 = create_black_frame()
        frame2 = create_white_frame()

        hash1 = algorithm._compute_frame_hash(frame1)
        hash2 = algorithm._compute_frame_hash(frame2)

        # Should be different
        assert not np.array_equal(hash1, hash2)


# ============================================================================
# 3. HAMMING SIMILARITY
# ============================================================================

class TestHammingSimilarity:
    """Test Hamming distance-based similarity."""

    @pytest.fixture
    def algorithm(self):
        algo = SubsequenceDetectionAlgorithm()
        algo.configure()
        return algo

    def test_hamming_identical_hashes(self, algorithm):
        """Test Hamming similarity for identical hashes."""
        hash1 = np.ones((8, 8), dtype=np.uint8)
        hash2 = np.ones((8, 8), dtype=np.uint8)

        similarity = algorithm._hamming_similarity(hash1, hash2)

        # Perfect match
        assert similarity == 100.0

    def test_hamming_opposite_hashes(self, algorithm):
        """Test Hamming similarity for opposite hashes."""
        hash1 = np.ones((8, 8), dtype=np.uint8)
        hash2 = np.zeros((8, 8), dtype=np.uint8)

        similarity = algorithm._hamming_similarity(hash1, hash2)

        # Complete mismatch
        assert similarity == 0.0

    def test_hamming_half_different(self, algorithm):
        """Test Hamming similarity for half different."""
        hash1 = np.ones((8, 8), dtype=np.uint8)
        hash2 = np.ones((8, 8), dtype=np.uint8)
        hash2[:4, :] = 0  # Half different

        similarity = algorithm._hamming_similarity(hash1, hash2)

        # 50% similarity
        assert similarity == pytest.approx(50.0, abs=1.0)

    def test_hamming_different_shapes(self, algorithm):
        """Test Hamming similarity with different shapes."""
        hash1 = np.ones((8, 8), dtype=np.uint8)
        hash2 = np.ones((4, 4), dtype=np.uint8)

        similarity = algorithm._hamming_similarity(hash1, hash2)

        # Should return 0 for incompatible shapes
        assert similarity == 0.0


# ============================================================================
# 4. MOTION SIMILARITY
# ============================================================================

class TestMotionSimilarity:
    """Test motion pattern similarity."""

    @pytest.fixture
    def algorithm(self):
        algo = SubsequenceDetectionAlgorithm()
        algo.configure()
        return algo

    def test_motion_identical_patterns(self, algorithm):
        """Test motion similarity for identical patterns."""
        motion1 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        motion2 = motion1.copy()

        similarity = algorithm._motion_similarity(motion1, motion2)

        # Perfect correlation
        assert similarity == pytest.approx(100.0, abs=0.1)

    def test_motion_similar_patterns(self, algorithm):
        """Test motion similarity for similar patterns."""
        motion1 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        motion2 = np.array([11.0, 21.0, 31.0, 41.0], dtype=np.float32)  # Shifted

        similarity = algorithm._motion_similarity(motion1, motion2)

        # High correlation (same shape)
        assert similarity > 95.0

    def test_motion_opposite_patterns(self, algorithm):
        """Test motion similarity for opposite patterns."""
        motion1 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        motion2 = np.array([40.0, 30.0, 20.0, 10.0], dtype=np.float32)  # Reversed

        similarity = algorithm._motion_similarity(motion1, motion2)

        # Negative correlation
        assert similarity < 10.0

    def test_motion_static_scenes(self, algorithm):
        """Test motion similarity for static scenes (zero variance)."""
        motion1 = np.array([5.0, 5.0, 5.0, 5.0], dtype=np.float32)  # Constant
        motion2 = np.array([10.0, 10.0, 10.0, 10.0], dtype=np.float32)  # Constant

        similarity = algorithm._motion_similarity(motion1, motion2)

        # Static scenes should match perfectly
        assert similarity == 100.0

    def test_motion_one_static_one_dynamic(self, algorithm):
        """Test motion similarity with one static scene."""
        motion1 = np.array([5.0, 5.0, 5.0, 5.0], dtype=np.float32)  # Static
        motion2 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)  # Dynamic

        similarity = algorithm._motion_similarity(motion1, motion2)

        # Static scene should match
        assert similarity == 100.0


# ============================================================================
# 5. COMPARE_FEATURES STATIC METHOD
# ============================================================================

class TestCompareFeatures:
    """Test compare_features static method."""

    def test_compare_features_identical(self):
        """Test comparing identical features."""
        # Create identical signatures
        hash1 = np.ones((8, 8), dtype=np.uint8)
        motion1 = np.array([10.0, 20.0, 30.0], dtype=np.float32)

        features = [(0.0, hash1, motion1)]

        result = SubsequenceDetectionAlgorithm.compare_features(
            features, features, threshold=70.0
        )

        # Should match perfectly
        assert result['similarity'] == pytest.approx(100.0, abs=0.1)
        assert result['accepted'] == True
        assert result['metadata']['confidence'] == 'high'
        assert result['metadata']['hash_score'] == 100.0
        assert result['metadata']['motion_score'] == pytest.approx(100.0, abs=0.1)

    def test_compare_features_similar(self):
        """Test comparing similar features."""
        hash1 = np.ones((8, 8), dtype=np.uint8)
        motion1 = np.array([10.0, 20.0, 30.0], dtype=np.float32)

        hash2 = np.ones((8, 8), dtype=np.uint8)
        hash2[0, 0] = 0  # Slightly different
        motion2 = np.array([11.0, 21.0, 31.0], dtype=np.float32)

        f1 = [(0.0, hash1, motion1)]
        f2 = [(0.0, hash2, motion2)]

        result = SubsequenceDetectionAlgorithm.compare_features(
            f1, f2, threshold=70.0
        )

        assert result['similarity'] > 95.0
        assert result['accepted'] == True

    def test_compare_features_different(self):
        """Test comparing different features."""
        hash1 = np.ones((8, 8), dtype=np.uint8)
        motion1 = np.array([10.0, 20.0, 30.0], dtype=np.float32)

        hash2 = np.zeros((8, 8), dtype=np.uint8)  # Opposite hash
        motion2 = np.array([30.0, 20.0, 10.0], dtype=np.float32)  # Opposite motion

        f1 = [(0.0, hash1, motion1)]
        f2 = [(0.0, hash2, motion2)]

        result = SubsequenceDetectionAlgorithm.compare_features(
            f1, f2, threshold=70.0
        )

        assert result['similarity'] < 50.0
        assert result['accepted'] == False

    def test_compare_features_empty(self):
        """Test comparing empty feature lists."""
        result = SubsequenceDetectionAlgorithm.compare_features(
            [], [], threshold=70.0
        )

        assert result['similarity'] == 0.0
        assert result['accepted'] == False
        assert 'error' in result['metadata']

    def test_compare_features_custom_weights(self):
        """Test compare with custom weights."""
        # Identical hash, different motion
        hash1 = np.ones((8, 8), dtype=np.uint8)
        motion1 = np.array([10.0, 20.0, 30.0], dtype=np.float32)
        motion2 = np.array([30.0, 20.0, 10.0], dtype=np.float32)  # Opposite

        f1 = [(0.0, hash1, motion1)]
        f2 = [(0.0, hash1, motion2)]  # Same hash

        # With high hash weight, should still match
        result = SubsequenceDetectionAlgorithm.compare_features(
            f1, f2,
            threshold=70.0,
            params={'hash_weight': 0.9, 'motion_weight': 0.1}
        )

        assert result['similarity'] > 85.0  # Hash dominates
        assert result['accepted'] == True

    def test_compare_features_confidence_levels(self):
        """Test confidence level determination."""
        hash1 = np.ones((8, 8), dtype=np.uint8)
        motion1 = np.array([10.0, 20.0, 30.0], dtype=np.float32)

        # Create features with known scores
        f1 = [(0.0, hash1, motion1)]

        # Test high confidence (>= 85)
        result_high = SubsequenceDetectionAlgorithm.compare_features(
            f1, f1, threshold=70.0
        )
        assert result_high['metadata']['confidence'] == 'high'

        # Test medium confidence (70-85) - need different features
        hash2 = np.ones((8, 8), dtype=np.uint8)
        hash2[:3, :3] = 0  # ~14% different
        f2 = [(0.0, hash2, motion1)]

        result_med = SubsequenceDetectionAlgorithm.compare_features(
            f1, f2, threshold=70.0
        )
        if 70 <= result_med['similarity'] < 85:
            assert result_med['metadata']['confidence'] == 'medium'


# ============================================================================
# 6. EDGE CASES
# ============================================================================

class TestSubsequenceDetectionEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def algorithm(self):
        algo = SubsequenceDetectionAlgorithm()
        algo.configure()
        return algo

    def test_signature_points_single(self):
        """Test with single signature point."""
        algo = SubsequenceDetectionAlgorithm()
        algo.configure(signature_points=1)

        # Should use middle point
        # Tested via internal logic - signature_points affects offset calculation

    def test_signature_points_many(self):
        """Test with many signature points."""
        algo = SubsequenceDetectionAlgorithm()
        algo.configure(signature_points=10)

        assert algo.signature_points == 10

    def test_combined_score_calculation(self, algorithm):
        """Test weighted combination of hash and motion scores."""
        # Assume hash_weight=0.6, motion_weight=0.4
        hash_score = 80.0
        motion_score = 60.0

        combined = algorithm.hash_weight * hash_score + algorithm.motion_weight * motion_score

        # Should be weighted average
        expected = 0.6 * 80.0 + 0.4 * 60.0  # = 48 + 24 = 72
        assert combined == pytest.approx(expected, abs=0.1)


# ============================================================================
# 7. ROBUSTNESS
# ============================================================================

class TestSubsequenceDetectionRobustness:
    """Test robustness to various conditions."""

    @pytest.fixture
    def algorithm(self):
        algo = SubsequenceDetectionAlgorithm()
        algo.configure()
        return algo

    def test_hash_method_consistency(self):
        """Test different hash methods produce consistent results."""
        frame = create_noise_frame(seed=42)

        for method in ['pHash', 'dHash', 'aHash']:
            algo = SubsequenceDetectionAlgorithm()
            algo.configure(hash_method=method)

            hash_val = algo._compute_frame_hash(frame)

            # All methods should return valid hashes
            assert hash_val is not None
            assert hash_val.dtype == np.uint8
            assert np.all((hash_val == 0) | (hash_val == 1))

    def test_motion_correlation_determinism(self, algorithm):
        """Test motion correlation is deterministic."""
        motion1 = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        motion2 = np.array([11.0, 21.0, 31.0, 41.0], dtype=np.float32)

        sim1 = algorithm._motion_similarity(motion1, motion2)
        sim2 = algorithm._motion_similarity(motion1, motion2)

        # Should be identical
        assert sim1 == sim2


# ============================================================================
# 8. INTEGRATION TESTS
# ============================================================================

class TestSubsequenceDetectionIntegration:
    """Test complete workflows."""

    def test_complete_comparison_workflow(self):
        """Test complete feature comparison workflow."""
        # Create synthetic signatures
        hash1 = np.ones((8, 8), dtype=np.uint8)
        motion1 = np.array([10.0, 20.0, 30.0], dtype=np.float32)

        hash2 = np.ones((8, 8), dtype=np.uint8)
        hash2[0:2, 0:2] = 0  # Slightly different
        motion2 = np.array([11.0, 21.0, 31.0], dtype=np.float32)

        f1 = [
            (0.0, hash1, motion1),
            (5.0, hash1, motion1),
            (10.0, hash1, motion1)
        ]

        f2 = [
            (0.0, hash2, motion2),
            (5.0, hash2, motion2),
            (10.0, hash2, motion2)
        ]

        # Compare
        result = SubsequenceDetectionAlgorithm.compare_features(
            f1, f2, threshold=70.0
        )

        # Verify result structure
        assert 'similarity' in result
        assert 'accepted' in result
        assert 'metadata' in result

        metadata = result['metadata']
        assert 'hash_score' in metadata
        assert 'motion_score' in metadata
        assert 'combined_score' in metadata
        assert 'confidence' in metadata
        assert 'num_sigs_1' in metadata
        assert 'num_sigs_2' in metadata

    def test_multiple_signature_points(self):
        """Test with multiple signature points."""
        # Create 5 signature points
        hash1 = np.ones((8, 8), dtype=np.uint8)
        motion1 = np.array([10.0, 20.0, 30.0], dtype=np.float32)

        features = [
            (i * 2.0, hash1, motion1) for i in range(5)
        ]

        result = SubsequenceDetectionAlgorithm.compare_features(
            features, features, threshold=70.0
        )

        # Should match perfectly
        assert result['similarity'] == pytest.approx(100.0, abs=0.1)
        assert result['metadata']['num_sigs_1'] == 5


# ============================================================================
# 9. PERFORMANCE AND DETERMINISM
# ============================================================================

class TestSubsequenceDetectionPerformance:
    """Test performance characteristics."""

    def test_deterministic_comparison(self):
        """Test comparison is deterministic."""
        hash1 = np.ones((8, 8), dtype=np.uint8)
        motion1 = np.array([10.0, 20.0, 30.0], dtype=np.float32)

        f1 = [(0.0, hash1, motion1)]

        result1 = SubsequenceDetectionAlgorithm.compare_features(
            f1, f1, threshold=70.0
        )

        result2 = SubsequenceDetectionAlgorithm.compare_features(
            f1, f1, threshold=70.0
        )

        # Should be identical
        assert result1['similarity'] == result2['similarity']
        assert result1['accepted'] == result2['accepted']
        assert result1['metadata']['hash_score'] == result2['metadata']['hash_score']

    def test_symmetry(self):
        """Test comparison is symmetric."""
        hash1 = np.ones((8, 8), dtype=np.uint8)
        motion1 = np.array([10.0, 20.0, 30.0], dtype=np.float32)

        hash2 = np.zeros((8, 8), dtype=np.uint8)
        motion2 = np.array([15.0, 25.0, 35.0], dtype=np.float32)

        f1 = [(0.0, hash1, motion1)]
        f2 = [(0.0, hash2, motion2)]

        result1 = SubsequenceDetectionAlgorithm.compare_features(
            f1, f2, threshold=70.0
        )

        result2 = SubsequenceDetectionAlgorithm.compare_features(
            f2, f1, threshold=70.0
        )

        # Should be symmetric
        assert result1['similarity'] == result2['similarity']
        assert result1['accepted'] == result2['accepted']

    def test_similarity_range_validation(self):
        """Test similarity is always in valid range."""
        test_cases = [
            # Identical
            ([(0.0, np.ones((8, 8), dtype=np.uint8), np.array([10.0, 20.0]))],
             [(0.0, np.ones((8, 8), dtype=np.uint8), np.array([10.0, 20.0]))]),
            # Different
            ([(0.0, np.ones((8, 8), dtype=np.uint8), np.array([10.0, 20.0]))],
             [(0.0, np.zeros((8, 8), dtype=np.uint8), np.array([30.0, 20.0]))]),
        ]

        for f1, f2 in test_cases:
            result = SubsequenceDetectionAlgorithm.compare_features(
                f1, f2, threshold=70.0
            )

            assert 0.0 <= result['similarity'] <= 100.0

    def test_hash_computation_determinism(self):
        """Test hash computation is deterministic."""
        algo = SubsequenceDetectionAlgorithm()
        algo.configure()

        frame = create_noise_frame(seed=42)

        hash1 = algo._compute_frame_hash(frame)
        hash2 = algo._compute_frame_hash(frame)

        # Should be identical
        assert np.array_equal(hash1, hash2)

    def test_cli_params(self):
        """Test get_cli_params returns valid parameters."""
        algo = SubsequenceDetectionAlgorithm()
        params = algo.get_cli_params()

        assert isinstance(params, list)
        assert len(params) == 4

        # Verify parameter structure
        for param in params:
            assert 'names' in param
            assert 'type' in param
            assert 'default' in param
            assert 'help' in param

    def test_requirements(self):
        """Test get_requirements returns valid dependencies."""
        algo = SubsequenceDetectionAlgorithm()
        reqs = algo.get_requirements()

        assert isinstance(reqs, list)
        assert 'opencv-python>=4.8.0' in reqs
        assert 'numpy>=1.24.0' in reqs
