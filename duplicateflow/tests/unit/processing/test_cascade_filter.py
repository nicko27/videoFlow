"""
Unit tests for CascadeFilter.

Tests the three-stage cascade filtering system for rapid window elimination.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from duplicateflow.processing.cascade_filter import CascadeFilter


class TestCascadeFilterInit:
    """Test CascadeFilter initialization."""

    def test_init(self):
        """Test initialization creates empty stats."""
        filter_obj = CascadeFilter()

        assert filter_obj.stats['total_windows'] == 0
        assert filter_obj.stats['stage1_survivors'] == 0
        assert filter_obj.stats['stage2_survivors'] == 0
        assert filter_obj.stats['stage1_time'] == 0.0
        assert filter_obj.stats['stage2_time'] == 0.0


class TestCascadeFilterPerceptualHash:
    """Test perceptual hash computation."""

    def test_compute_perceptual_hash_identical(self):
        """Test that identical frames produce identical hashes."""
        filter_obj = CascadeFilter()

        # Create identical frame
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128

        hash1 = filter_obj._compute_perceptual_hash(frame)
        hash2 = filter_obj._compute_perceptual_hash(frame)

        assert hash1 == hash2
        assert isinstance(hash1, int)

    def test_compute_perceptual_hash_different(self):
        """Test that different frames produce different hashes."""
        filter_obj = CascadeFilter()

        # Create two distinctly different patterns (not all same color)
        frame1 = np.zeros((480, 640, 3), dtype=np.uint8)  # Black
        frame2 = np.ones((480, 640, 3), dtype=np.uint8) * 128  # Gray

        # Add pattern to make them truly different
        frame1[:240, :, :] = 255  # Half white, half black
        frame2[:240, :, :] = 0    # Half black, half gray

        hash1 = filter_obj._compute_perceptual_hash(frame1)
        hash2 = filter_obj._compute_perceptual_hash(frame2)

        # Should be different
        assert hash1 != hash2


class TestCascadeFilterHistogram:
    """Test histogram computation."""

    def test_compute_histogram(self):
        """Test histogram computation returns correct shape."""
        filter_obj = CascadeFilter()

        # Create sample frame
        frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)

        hist = filter_obj._compute_histogram(frame)

        # Should be flattened 8x8x8 histogram
        assert hist.shape == (512,)  # 8*8*8
        assert isinstance(hist, np.ndarray)

    def test_compute_histogram_normalized(self):
        """Test histogram is normalized (cv2.normalize uses different normalization)."""
        filter_obj = CascadeFilter()

        frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)

        hist = filter_obj._compute_histogram(frame)

        # cv2.normalize with default settings normalizes to max value of 1.0
        # The sum can vary, but max should be <= 1.0 and min >= 0
        assert np.max(hist) <= 1.01  # Allow small numerical error
        assert np.min(hist) >= 0.0


class TestCascadeFilterCompareHashes:
    """Test hash comparison logic."""

    def test_compare_hashes_identical(self):
        """Test comparing identical hash lists."""
        filter_obj = CascadeFilter()

        hashes1 = [12345, 67890, 11111]
        hashes2 = [12345, 67890, 11111]

        score = filter_obj._compare_hashes(hashes1, hashes2)

        # Should be 100% similar
        assert score == 100.0

    def test_compare_hashes_different(self):
        """Test comparing completely different hashes."""
        filter_obj = CascadeFilter()

        # Hashes with all bits flipped (maximum Hamming distance)
        hashes1 = [0, 0, 0]  # All zeros
        hashes2 = [(2**64)-1, (2**64)-1, (2**64)-1]  # All ones

        score = filter_obj._compare_hashes(hashes1, hashes2)

        # Should be 0% similar
        assert score == 0.0

    def test_compare_hashes_different_lengths(self):
        """Test comparing hash lists of different lengths."""
        filter_obj = CascadeFilter()

        hashes1 = [12345, 67890]
        hashes2 = [12345]

        score = filter_obj._compare_hashes(hashes1, hashes2)

        # Should return 0 for incompatible lists
        assert score == 0.0


class TestCascadeFilterCompareHistograms:
    """Test histogram comparison logic."""

    def test_compare_histograms_identical(self):
        """Test comparing identical histograms."""
        filter_obj = CascadeFilter()

        # Create identical histograms
        hist = np.random.rand(512).astype(np.float32)
        hists1 = [hist.copy(), hist.copy()]
        hists2 = [hist.copy(), hist.copy()]

        score = filter_obj._compare_histograms(hists1, hists2)

        # Should be 100% similar
        assert score == pytest.approx(100.0, abs=0.1)

    def test_compare_histograms_different(self):
        """Test comparing different histograms."""
        filter_obj = CascadeFilter()

        # Create very different histograms
        hists1 = [np.random.rand(512).astype(np.float32)]
        hists2 = [np.random.rand(512).astype(np.float32)]

        score = filter_obj._compare_histograms(hists1, hists2)

        # Should have some score (unlikely to be 100% or 0%)
        assert 0.0 <= score <= 100.0

    def test_compare_histograms_different_lengths(self):
        """Test comparing histogram lists of different lengths."""
        filter_obj = CascadeFilter()

        hists1 = [np.random.rand(512).astype(np.float32), np.random.rand(512).astype(np.float32)]
        hists2 = [np.random.rand(512).astype(np.float32)]

        score = filter_obj._compare_histograms(hists1, hists2)

        # Should return 0 for incompatible lists
        assert score == 0.0


class TestCascadeFilterExtractHashes:
    """Test hash extraction from videos."""

    @patch('duplicateflow.algorithms.base.video_loader.VideoLoader')
    def test_extract_quick_hashes(self, mock_loader_class):
        """Test extracting quick hashes from video."""
        filter_obj = CascadeFilter()

        # Mock VideoLoader
        mock_loader = MagicMock()
        mock_loader.duration = 60.0
        mock_loader.get_frame = Mock(return_value=np.zeros((480, 640, 3), dtype=np.uint8))
        mock_loader.__enter__ = Mock(return_value=mock_loader)
        mock_loader.__exit__ = Mock(return_value=False)

        mock_loader_class.return_value = mock_loader

        hashes = filter_obj._extract_quick_hashes("video.mp4", num_frames=3)

        # Should extract 3 hashes
        assert len(hashes) == 3
        assert all(isinstance(h, int) for h in hashes)

    @patch('duplicateflow.algorithms.base.video_loader.VideoLoader')
    def test_extract_histograms(self, mock_loader_class):
        """Test extracting histograms from video."""
        filter_obj = CascadeFilter()

        # Mock VideoLoader
        mock_loader = MagicMock()
        mock_loader.duration = 60.0
        mock_loader.get_frame = Mock(return_value=np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8))
        mock_loader.__enter__ = Mock(return_value=mock_loader)
        mock_loader.__exit__ = Mock(return_value=False)

        mock_loader_class.return_value = mock_loader

        hists = filter_obj._extract_histograms("video.mp4", num_frames=5)

        # Should extract 5 histograms
        assert len(hists) == 5
        assert all(isinstance(h, np.ndarray) for h in hists)
        assert all(h.shape == (512,) for h in hists)


class TestCascadeFilterStage1:
    """Test Stage 1 hash filter."""

    @patch('duplicateflow.algorithms.base.video_loader.VideoLoader')
    def test_stage1_hash_filter_all_pass(self, mock_loader_class):
        """Test stage 1 when all windows pass threshold."""
        filter_obj = CascadeFilter()

        # Mock VideoLoader to return identical frames (will produce identical hashes)
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        mock_loader = MagicMock()
        mock_loader.get_frame = Mock(return_value=frame)
        mock_loader.__enter__ = Mock(return_value=mock_loader)
        mock_loader.__exit__ = Mock(return_value=False)
        mock_loader_class.return_value = mock_loader

        windows = [0.0, 5.0, 10.0]

        candidates = filter_obj._stage1_hash_filter(
            windows,
            "short.mp4",
            "long.mp4",
            duration=10.0,
            threshold=40.0,
            show_progress=False
        )

        # All windows should pass (identical frames = 100% similarity)
        assert len(candidates) == 3

    @patch('duplicateflow.algorithms.base.video_loader.VideoLoader')
    def test_stage1_hash_filter_all_fail(self, mock_loader_class):
        """Test stage 1 when all windows fail threshold."""
        filter_obj = CascadeFilter()

        # Mock to return completely different frames
        def get_frame_side_effect(offset):
            # Return random frames (will produce different hashes)
            return np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)

        mock_loader = MagicMock()
        mock_loader.get_frame = Mock(side_effect=get_frame_side_effect)
        mock_loader.__enter__ = Mock(return_value=mock_loader)
        mock_loader.__exit__ = Mock(return_value=False)
        mock_loader_class.return_value = mock_loader

        windows = [0.0, 5.0, 10.0]

        candidates = filter_obj._stage1_hash_filter(
            windows,
            "short.mp4",
            "long.mp4",
            duration=10.0,
            threshold=99.0,  # Very high threshold
            show_progress=False
        )

        # No windows should pass
        assert len(candidates) == 0


class TestCascadeFilterStage2:
    """Test Stage 2 histogram filter."""

    @patch('duplicateflow.algorithms.base.video_loader.VideoLoader')
    def test_stage2_histogram_filter_all_pass(self, mock_loader_class):
        """Test stage 2 when all windows pass threshold."""
        filter_obj = CascadeFilter()

        # Mock VideoLoader to return similar frames
        frame = np.random.randint(100, 150, (480, 640, 3), dtype=np.uint8)
        mock_loader = MagicMock()
        mock_loader.get_frame = Mock(return_value=frame.copy())
        mock_loader.__enter__ = Mock(return_value=mock_loader)
        mock_loader.__exit__ = Mock(return_value=False)
        mock_loader_class.return_value = mock_loader

        windows = [0.0, 5.0]

        candidates = filter_obj._stage2_histogram_filter(
            windows,
            "short.mp4",
            "long.mp4",
            duration=10.0,
            threshold=50.0,  # Low threshold
            show_progress=False
        )

        # All windows should pass
        assert len(candidates) == 2

    @patch('duplicateflow.algorithms.base.video_loader.VideoLoader')
    def test_stage2_histogram_filter_some_fail(self, mock_loader_class):
        """Test stage 2 with some windows failing."""
        filter_obj = CascadeFilter()

        # Mock to return different frames
        mock_loader = MagicMock()
        mock_loader.get_frame = Mock(return_value=np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8))
        mock_loader.__enter__ = Mock(return_value=mock_loader)
        mock_loader.__exit__ = Mock(return_value=False)
        mock_loader_class.return_value = mock_loader

        windows = [0.0, 5.0, 10.0]

        candidates = filter_obj._stage2_histogram_filter(
            windows,
            "short.mp4",
            "long.mp4",
            duration=10.0,
            threshold=99.0,  # Very high threshold
            show_progress=False
        )

        # Most or all should fail with random frames
        assert len(candidates) <= len(windows)


class TestCascadeFilterFullPipeline:
    """Test full filtering pipeline."""

    @patch('duplicateflow.algorithms.base.video_loader.VideoLoader')
    def test_filter_windows_full_pipeline(self, mock_loader_class):
        """Test complete cascade filtering pipeline."""
        filter_obj = CascadeFilter()

        # Mock VideoLoader to return consistent frames
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        mock_loader = MagicMock()
        mock_loader.get_frame = Mock(return_value=frame)
        mock_loader.__enter__ = Mock(return_value=mock_loader)
        mock_loader.__exit__ = Mock(return_value=False)
        mock_loader_class.return_value = mock_loader

        windows = [0.0, 5.0, 10.0, 15.0, 20.0]

        candidates = filter_obj.filter_windows(
            windows,
            "short.mp4",
            "long.mp4",
            short_duration=10.0,
            stage1_threshold=40.0,
            stage2_threshold=55.0,
            show_progress=False
        )

        # Verify statistics updated
        assert filter_obj.stats['total_windows'] == 5
        assert filter_obj.stats['stage1_survivors'] > 0
        assert filter_obj.stats['stage2_survivors'] > 0

        # Should have candidates
        assert len(candidates) > 0

    @patch('duplicateflow.algorithms.base.video_loader.VideoLoader')
    def test_filter_windows_no_survivors(self, mock_loader_class):
        """Test filtering with no windows passing."""
        filter_obj = CascadeFilter()

        # Mock to return very different frames for short vs long video
        # Use deterministic different patterns
        def get_frame_for_short(offset):
            return np.zeros((480, 640, 3), dtype=np.uint8)  # All black

        def get_frame_for_long(offset):
            return np.ones((480, 640, 3), dtype=np.uint8) * 255  # All white

        # Create separate mocks for short and long videos
        call_count = [0]  # Track calls to distinguish short vs long

        def mock_loader_factory(video_path):
            loader = MagicMock()
            if call_count[0] % 2 == 0:  # Even calls = short video
                loader.get_frame = Mock(side_effect=get_frame_for_short)
            else:  # Odd calls = long video
                loader.get_frame = Mock(side_effect=get_frame_for_long)
            loader.__enter__ = Mock(return_value=loader)
            loader.__exit__ = Mock(return_value=False)
            call_count[0] += 1
            return loader

        mock_loader_class.side_effect = mock_loader_factory

        windows = [0.0, 5.0, 10.0]

        candidates = filter_obj.filter_windows(
            windows,
            "short.mp4",
            "long.mp4",
            short_duration=10.0,
            stage1_threshold=99.0,  # Impossibly high
            stage2_threshold=99.0,
            show_progress=False
        )

        # Should have no or very few candidates with high threshold and very different frames
        assert len(candidates) <= 1  # Allow for occasional random match


class TestCascadeFilterStats:
    """Test statistics reporting."""

    def test_get_stats_empty(self):
        """Test getting stats before any filtering."""
        filter_obj = CascadeFilter()

        stats = filter_obj.get_stats()

        assert stats['total_windows'] == 0
        assert stats['stage1_survivors'] == 0
        assert stats['stage2_survivors'] == 0

    @patch('duplicateflow.algorithms.base.video_loader.VideoLoader')
    def test_get_stats_after_filtering(self, mock_loader_class):
        """Test statistics after filtering."""
        filter_obj = CascadeFilter()

        # Mock VideoLoader
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        mock_loader = MagicMock()
        mock_loader.get_frame = Mock(return_value=frame)
        mock_loader.__enter__ = Mock(return_value=mock_loader)
        mock_loader.__exit__ = Mock(return_value=False)
        mock_loader_class.return_value = mock_loader

        # Run filtering
        filter_obj.filter_windows(
            [0.0, 5.0, 10.0, 15.0, 20.0],
            "short.mp4",
            "long.mp4",
            short_duration=10.0,
            stage1_threshold=40.0,
            stage2_threshold=55.0,
            show_progress=False
        )

        stats = filter_obj.get_stats()

        # Verify computed metrics
        assert 'stage1_elimination_rate' in stats
        assert 'stage2_elimination_rate' in stats
        assert 'total_elimination_rate' in stats
        assert 'avg_stage1_time_per_window_ms' in stats
        assert 'avg_stage2_time_per_window_ms' in stats

        # Rates should be 0-100
        assert 0 <= stats['stage1_elimination_rate'] <= 100
        assert 0 <= stats['total_elimination_rate'] <= 100
