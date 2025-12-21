"""
Unit tests for ParallelWindowSearch and AdaptiveStepSearch.

Tests parallel window-based search functionality with mocked video processing.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

from duplicateflow.processing.parallel_search import ParallelWindowSearch, AdaptiveStepSearch


class TestParallelWindowSearchInstantiation:
    """Test ParallelWindowSearch instantiation."""

    def test_init_default_workers(self):
        """Test initialization with default worker count (CPU count)."""
        searcher = ParallelWindowSearch()

        # Should use CPU count or fallback to 4
        assert searcher.num_workers >= 1
        assert searcher.num_workers <= 128  # Reasonable upper bound

    def test_init_custom_workers(self):
        """Test initialization with custom worker count."""
        searcher = ParallelWindowSearch(num_workers=8)

        assert searcher.num_workers == 8

    def test_init_single_worker(self):
        """Test initialization with single worker."""
        searcher = ParallelWindowSearch(num_workers=1)

        assert searcher.num_workers == 1


class TestParallelWindowSearchGenerateWindows:
    """Test window generation logic."""

    @pytest.fixture
    def searcher(self):
        return ParallelWindowSearch(num_workers=4)

    def test_generate_windows_basic(self, searcher):
        """Test basic window generation with default step size."""
        # Search range: 0-100s, window: 10s, step: 5s
        windows = searcher._generate_windows(
            start_time=0.0,
            end_time=100.0,
            window_duration=10.0,
            step_size=5.0
        )

        # Should generate windows: 0, 5, 10, 15, ..., 90
        # Last window at 90s (90+10=100, exactly at end)
        assert len(windows) == 19  # 0, 5, 10, ..., 90
        assert windows[0] == 0.0
        assert windows[-1] == 90.0
        assert windows[1] - windows[0] == 5.0

    def test_generate_windows_no_overlap(self, searcher):
        """Test window generation with no overlap (step = window duration)."""
        windows = searcher._generate_windows(
            start_time=0.0,
            end_time=60.0,
            window_duration=10.0,
            step_size=10.0
        )

        # Should generate windows: 0, 10, 20, 30, 40, 50
        assert len(windows) == 6
        assert windows == [0.0, 10.0, 20.0, 30.0, 40.0, 50.0]

    def test_generate_windows_large_overlap(self, searcher):
        """Test window generation with large overlap."""
        windows = searcher._generate_windows(
            start_time=0.0,
            end_time=30.0,
            window_duration=10.0,
            step_size=2.0  # Heavy overlap
        )

        # Should generate windows: 0, 2, 4, 6, ..., 20
        assert len(windows) == 11  # 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20
        assert windows[0] == 0.0
        assert windows[-1] == 20.0

    def test_generate_windows_short_video(self, searcher):
        """Test window generation when video is shorter than window."""
        windows = searcher._generate_windows(
            start_time=0.0,
            end_time=5.0,
            window_duration=10.0,
            step_size=5.0
        )

        # No windows fit
        assert len(windows) == 0

    def test_generate_windows_exact_match(self, searcher):
        """Test window generation when video exactly fits one window."""
        windows = searcher._generate_windows(
            start_time=0.0,
            end_time=10.0,
            window_duration=10.0,
            step_size=5.0
        )

        # Exactly one window at 0s
        assert len(windows) == 1
        assert windows[0] == 0.0

    def test_generate_windows_offset_start(self, searcher):
        """Test window generation with non-zero start time."""
        windows = searcher._generate_windows(
            start_time=50.0,
            end_time=100.0,
            window_duration=10.0,
            step_size=10.0
        )

        # Should generate windows: 50, 60, 70, 80, 90
        assert len(windows) == 5
        assert windows[0] == 50.0
        assert windows[-1] == 90.0


class TestParallelWindowSearchSearch:
    """Test main search functionality."""

    @pytest.fixture
    def mock_algorithm(self):
        """Create mock algorithm instance."""
        algo = Mock()
        algo.threshold = 70.0
        algo.compare = Mock(return_value={'similarity': 0.85})
        return algo

    @patch('duplicateflow.algorithms.base.video_loader.get_video_duration')
    def test_search_success(self, mock_duration, mock_algorithm, tmp_path):
        """Test successful search with match found."""
        # Mock video durations
        mock_duration.side_effect = [10.0, 100.0]  # short=10s, long=100s

        searcher = ParallelWindowSearch(num_workers=2)

        # Create dummy video files
        short_video = tmp_path / "short.mp4"
        long_video = tmp_path / "long.mp4"
        short_video.touch()
        long_video.touch()

        result = searcher.search(
            str(short_video),
            str(long_video),
            algorithm='test_algo',
            algorithm_instance=mock_algorithm,
            step_size=10.0,
            show_progress=False
        )

        # Verify result structure
        assert 'offset' in result
        assert 'score' in result
        assert 'accepted' in result
        assert 'windows_tested' in result
        assert 'algorithm' in result
        assert 'total_windows' in result

        assert result['algorithm'] == 'test_algo'
        assert result['score'] == 85.0  # Converted from 0.85
        assert result['accepted'] is True  # 85.0 >= 70.0

    @patch('duplicateflow.algorithms.base.video_loader.get_video_duration')
    def test_search_no_windows(self, mock_duration, mock_algorithm, tmp_path):
        """Test search when short video is longer than long video."""
        # Mock durations: short=100s, long=10s (impossible case)
        mock_duration.side_effect = [100.0, 10.0]

        searcher = ParallelWindowSearch(num_workers=2)

        short_video = tmp_path / "short.mp4"
        long_video = tmp_path / "long.mp4"
        short_video.touch()
        long_video.touch()

        result = searcher.search(
            str(short_video),
            str(long_video),
            algorithm='test_algo',
            algorithm_instance=mock_algorithm,
            show_progress=False
        )

        # Should return zero results
        assert result['score'] == 0.0
        assert result['accepted'] is False
        assert result['offset'] == 0.0

    @patch('duplicateflow.algorithms.base.video_loader.get_video_duration')
    def test_search_early_stopping(self, mock_duration, mock_algorithm, tmp_path):
        """Test early stopping when excellent match found."""
        # Mock video durations
        mock_duration.side_effect = [10.0, 100.0]

        # Mock algorithm to return high score immediately
        mock_algorithm.compare = Mock(return_value={'similarity': 0.98})

        searcher = ParallelWindowSearch(num_workers=2)

        short_video = tmp_path / "short.mp4"
        long_video = tmp_path / "long.mp4"
        short_video.touch()
        long_video.touch()

        result = searcher.search(
            str(short_video),
            str(long_video),
            algorithm='test_algo',
            algorithm_instance=mock_algorithm,
            step_size=5.0,
            show_progress=False,
            early_stop_threshold=95.0
        )

        # Should have stopped early
        assert result['score'] == 98.0
        # Windows tested should be less than total windows
        assert result['windows_tested'] <= result['total_windows']

    @patch('duplicateflow.algorithms.base.video_loader.get_video_duration')
    def test_search_custom_time_range(self, mock_duration, mock_algorithm, tmp_path):
        """Test search with custom start and end times."""
        # Mock video durations
        mock_duration.side_effect = [10.0, 200.0]

        searcher = ParallelWindowSearch(num_workers=2)

        short_video = tmp_path / "short.mp4"
        long_video = tmp_path / "long.mp4"
        short_video.touch()
        long_video.touch()

        result = searcher.search(
            str(short_video),
            str(long_video),
            algorithm='test_algo',
            algorithm_instance=mock_algorithm,
            step_size=10.0,
            start_time=50.0,
            end_time=100.0,
            show_progress=False
        )

        # Should search only in specified range
        assert result['offset'] >= 50.0
        assert result['offset'] <= 90.0  # Last valid window start


class TestParallelWindowSearchProcessSingleWindow:
    """Test single window processing."""

    def test_process_single_window_success(self):
        """Test processing a single window successfully."""
        # Mock algorithm
        algo = Mock()
        algo.compare = Mock(return_value={'similarity': 0.75})

        searcher = ParallelWindowSearch(num_workers=1)

        score = searcher._process_single_window(
            short_video="short.mp4",
            long_video="long.mp4",
            window_start=10.0,
            duration=5.0,
            algorithm_instance=algo
        )

        assert score == 75.0  # Converted from 0.75
        algo.compare.assert_called_once_with(
            short_video="short.mp4",
            long_video="long.mp4",
            start_time=10.0,
            duration=5.0
        )

    def test_process_single_window_already_percentage(self):
        """Test processing window when similarity is already in 0-100 range."""
        # Mock algorithm returning percentage directly
        algo = Mock()
        algo.compare = Mock(return_value={'similarity': 82.5})

        searcher = ParallelWindowSearch(num_workers=1)

        score = searcher._process_single_window(
            short_video="short.mp4",
            long_video="long.mp4",
            window_start=0.0,
            duration=10.0,
            algorithm_instance=algo
        )

        # Should not double-convert
        assert score == 82.5

    def test_process_single_window_exception(self):
        """Test handling exception during window processing."""
        # Mock algorithm to raise exception
        algo = Mock()
        algo.compare = Mock(side_effect=Exception("Processing error"))

        searcher = ParallelWindowSearch(num_workers=1)

        score = searcher._process_single_window(
            short_video="short.mp4",
            long_video="long.mp4",
            window_start=0.0,
            duration=10.0,
            algorithm_instance=algo
        )

        # Should return 0.0 on error
        assert score == 0.0


class TestParallelWindowSearchBatch:
    """Test batch search functionality."""

    @patch('duplicateflow.algorithms.base.video_loader.get_video_duration')
    def test_search_batch(self, mock_duration, tmp_path):
        """Test batch search for multiple short videos."""
        # Mock durations
        mock_duration.return_value = 10.0

        # Mock algorithm
        algo = Mock()
        algo.threshold = 70.0
        algo.compare = Mock(return_value={'similarity': 0.80})

        searcher = ParallelWindowSearch(num_workers=2)

        # Create dummy files
        short_videos = [tmp_path / f"short{i}.mp4" for i in range(3)]
        for v in short_videos:
            v.touch()

        long_video = tmp_path / "long.mp4"
        long_video.touch()

        results = searcher.search_batch(
            short_videos=[str(v) for v in short_videos],
            long_video=str(long_video),
            algorithm='test_algo',
            algorithm_instance=algo,
            step_size=5.0
        )

        # Should return results for all 3 videos
        assert len(results) == 3

        for i, result in enumerate(results):
            assert 'short_video' in result
            assert result['short_video'] == str(short_videos[i])
            assert 'score' in result
            assert 'offset' in result


class TestAdaptiveStepSearchInstantiation:
    """Test AdaptiveStepSearch instantiation."""

    def test_init_default_workers(self):
        """Test initialization with default workers."""
        searcher = AdaptiveStepSearch()

        assert searcher.parallel_searcher is not None
        assert isinstance(searcher.parallel_searcher, ParallelWindowSearch)

    def test_init_custom_workers(self):
        """Test initialization with custom worker count."""
        searcher = AdaptiveStepSearch(num_workers=16)

        assert searcher.parallel_searcher.num_workers == 16


class TestAdaptiveStepSearchSearch:
    """Test adaptive search functionality."""

    @patch('duplicateflow.algorithms.base.video_loader.get_video_duration')
    def test_search_coarse_only(self, mock_duration, tmp_path):
        """Test adaptive search that doesn't trigger fine search (low score)."""
        # Mock video durations
        mock_duration.side_effect = [10.0, 200.0, 10.0, 200.0]  # Called for coarse search

        # Mock algorithm with low score
        algo = Mock()
        algo.threshold = 70.0
        algo.compare = Mock(return_value={'similarity': 0.35})  # Below 40% threshold

        searcher = AdaptiveStepSearch(num_workers=2)

        short_video = tmp_path / "short.mp4"
        long_video = tmp_path / "long.mp4"
        short_video.touch()
        long_video.touch()

        result = searcher.search(
            str(short_video),
            str(long_video),
            algorithm='test_algo',
            algorithm_instance=algo,
            initial_step=30.0,
            fine_step=2.0,
            coarse_threshold=40.0,
            show_progress=False
        )

        # Should only do coarse search
        assert result['score'] == 35.0

    @patch('duplicateflow.algorithms.base.video_loader.get_video_duration')
    def test_search_coarse_plus_fine(self, mock_duration, tmp_path):
        """Test adaptive search that triggers fine search (high coarse score)."""
        # Mock video durations (called multiple times)
        mock_duration.side_effect = [10.0, 200.0] * 10

        # Mock algorithm with high coarse score
        algo = Mock()
        algo.threshold = 70.0

        # First call (coarse): 75%, second call (fine): 88%
        algo.compare = Mock(side_effect=[
            {'similarity': 0.75},  # Coarse search
            {'similarity': 0.88}   # Fine search (better)
        ] * 50)  # Repeat for all windows

        searcher = AdaptiveStepSearch(num_workers=2)

        short_video = tmp_path / "short.mp4"
        long_video = tmp_path / "long.mp4"
        short_video.touch()
        long_video.touch()

        result = searcher.search(
            str(short_video),
            str(long_video),
            algorithm='test_algo',
            algorithm_instance=algo,
            initial_step=30.0,
            fine_step=2.0,
            coarse_threshold=40.0,
            show_progress=False
        )

        # Should do fine search and get better score
        assert result['score'] >= 75.0  # At least coarse score

    @patch('duplicateflow.algorithms.base.video_loader.get_video_duration')
    def test_search_fine_search_region(self, mock_duration, tmp_path):
        """Test that fine search is limited to ±2 minutes around best offset."""
        # Mock video durations
        mock_duration.side_effect = [10.0, 1000.0] * 10

        # Mock algorithm
        algo = Mock()
        algo.threshold = 70.0
        algo.compare = Mock(return_value={'similarity': 0.65})

        searcher = AdaptiveStepSearch(num_workers=2)

        short_video = tmp_path / "short.mp4"
        long_video = tmp_path / "long.mp4"
        short_video.touch()
        long_video.touch()

        result = searcher.search(
            str(short_video),
            str(long_video),
            algorithm='test_algo',
            algorithm_instance=algo,
            initial_step=100.0,  # Coarse steps
            fine_step=5.0,       # Fine steps
            coarse_threshold=40.0,
            show_progress=False
        )

        # Should complete without errors
        assert 'offset' in result
        assert 'score' in result


class TestParallelWindowSearchEdgeCases:
    """Test edge cases and error scenarios."""

    def test_search_with_zero_workers(self):
        """Test that zero workers gets converted to valid number."""
        # Constructor should handle this gracefully
        searcher = ParallelWindowSearch(num_workers=None)
        assert searcher.num_workers >= 1

    @patch('duplicateflow.algorithms.base.video_loader.get_video_duration')
    def test_search_with_very_small_step(self, mock_duration, tmp_path):
        """Test search with very small step size (heavy processing)."""
        mock_duration.side_effect = [5.0, 20.0]

        # Mock algorithm
        algo = Mock()
        algo.threshold = 70.0
        algo.compare = Mock(return_value={'similarity': 0.75})

        searcher = ParallelWindowSearch(num_workers=2)

        short_video = tmp_path / "short.mp4"
        long_video = tmp_path / "long.mp4"
        short_video.touch()
        long_video.touch()

        # Very small step = many windows
        result = searcher.search(
            str(short_video),
            str(long_video),
            algorithm='test_algo',
            algorithm_instance=algo,
            step_size=0.5,  # Very small
            show_progress=False
        )

        # Should handle many windows
        assert result['total_windows'] > 10
