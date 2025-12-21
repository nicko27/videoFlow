"""
Unit tests for BatchProcessor.

Tests batch video processing with parallel execution, checkpointing,
and error handling.
"""

import pytest
import json
import csv
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from duplicateflow.processing.batch_processor import BatchProcessor, BatchResult


class TestBatchResult:
    """Test BatchResult dataclass."""

    def test_batch_result_creation(self):
        """Test creating BatchResult with all fields."""
        result = BatchResult(
            short_video="short.mp4",
            long_video="long.mp4",
            offset=12.5,
            score=85.0,
            accepted=True,
            algorithm="frame_hash",
            duration=2.5,
            error=None,
            timestamp="2025-12-21T10:00:00"
        )

        assert result.short_video == "short.mp4"
        assert result.long_video == "long.mp4"
        assert result.offset == 12.5
        assert result.score == 85.0
        assert result.accepted is True
        assert result.algorithm == "frame_hash"
        assert result.duration == 2.5
        assert result.error is None
        assert result.timestamp == "2025-12-21T10:00:00"

    def test_batch_result_auto_timestamp(self):
        """Test automatic timestamp generation."""
        result = BatchResult(
            short_video="short.mp4",
            long_video="long.mp4",
            offset=0.0,
            score=50.0,
            accepted=False,
            algorithm="test",
            duration=1.0
        )

        # Should have auto-generated timestamp
        assert result.timestamp is not None
        assert isinstance(result.timestamp, str)

    def test_batch_result_with_error(self):
        """Test BatchResult with error."""
        result = BatchResult(
            short_video="short.mp4",
            long_video="long.mp4",
            offset=0.0,
            score=0.0,
            accepted=False,
            algorithm="test",
            duration=0.0,
            error="File not found"
        )

        assert result.error == "File not found"


class TestBatchProcessorInit:
    """Test BatchProcessor initialization."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        processor = BatchProcessor()

        assert processor.num_workers == 4
        assert processor.checkpoint_interval == 10
        assert processor.max_retries == 2
        assert isinstance(processor.results, list)
        assert len(processor.results) == 0
        assert isinstance(processor.failed_videos, list)

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        processor = BatchProcessor(
            num_workers=8,
            checkpoint_interval=20,
            max_retries=5
        )

        assert processor.num_workers == 8
        assert processor.checkpoint_interval == 20
        assert processor.max_retries == 5


class TestBatchProcessorProcessBatch:
    """Test process_batch method."""

    @pytest.fixture
    def processor(self):
        """Create BatchProcessor for testing."""
        return BatchProcessor(num_workers=2, checkpoint_interval=5, max_retries=1)

    @pytest.fixture
    def mock_search(self):
        """Mock ParallelWindowSearch."""
        with patch('duplicateflow.processing.parallel_search.ParallelWindowSearch') as mock:
            # Mock search instance
            search_instance = Mock()
            search_instance.search.return_value = {
                'offset': 10.0,
                'score': 80.0,
                'accepted': True
            }
            mock.return_value = search_instance
            yield mock

    @pytest.fixture
    def mock_algorithm(self):
        """Mock get_algorithm."""
        with patch('duplicateflow.core.get_algorithm') as mock:
            # Create a mock algorithm class
            algo_instance = Mock()
            algo_instance.name = "frame_hash"
            algo_instance.configure = Mock()
            algo_instance.compare.return_value = {
                'similarity': 0.805,  # Will be converted to percentage
                'offset': 10.0,
                'accepted': True
            }

            # Mock the class itself
            algo_class = Mock(return_value=algo_instance)
            mock.return_value = algo_class
            yield mock

    def test_process_batch_single_video(self, processor, mock_search, mock_algorithm, tmp_path):
        """Test processing single video."""
        # Create dummy video files
        short_video = tmp_path / "short.mp4"
        long_video = tmp_path / "long.mp4"
        short_video.touch()
        long_video.touch()

        # Mock get_video_duration to avoid opening video files
        with patch('duplicateflow.algorithms.base.video_loader.get_video_duration') as mock_duration:
            mock_duration.return_value = 30.0

            results = processor.process_batch(
                short_videos=[str(short_video)],
                long_video=str(long_video),
                algorithm='frame_hash',
                show_progress=False,
                strategy='standard'  # Use standard strategy to avoid ParallelWindowSearch
            )

        assert len(results) == 1
        assert results[0].short_video == str(short_video)
        assert results[0].long_video == str(long_video)
        assert results[0].score == 80.5  # 0.805 * 100
        assert results[0].accepted is True

    def test_process_batch_multiple_videos(self, processor, mock_search, mock_algorithm, tmp_path):
        """Test processing multiple videos."""
        # Create dummy video files
        short_videos = []
        for i in range(3):
            video = tmp_path / f"short{i}.mp4"
            video.touch()
            short_videos.append(str(video))

        long_video = tmp_path / "long.mp4"
        long_video.touch()

        with patch('duplicateflow.algorithms.base.video_loader.get_video_duration') as mock_duration:
            mock_duration.return_value = 30.0

            results = processor.process_batch(
                short_videos=short_videos,
                long_video=str(long_video),
                algorithm='frame_hash',
                show_progress=False,
                strategy='standard'
            )

        assert len(results) == 3
        for result in results:
            assert result.long_video == str(long_video)
            assert result.score == 80.5

    def test_process_batch_export_csv(self, processor, mock_search, mock_algorithm, tmp_path):
        """Test exporting results to CSV."""
        short_video = tmp_path / "short.mp4"
        long_video = tmp_path / "long.mp4"
        short_video.touch()
        long_video.touch()

        output_file = tmp_path / "results.csv"

        with patch('duplicateflow.algorithms.base.video_loader.get_video_duration') as mock_duration:
            mock_duration.return_value = 30.0

            results = processor.process_batch(
                short_videos=[str(short_video)],
                long_video=str(long_video),
                algorithm='frame_hash',
                output_file=str(output_file),
                show_progress=False,
                strategy='standard'
            )

        # Verify CSV file created
        assert output_file.exists()

        # Read and verify CSV content
        with open(output_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]['short_video'] == str(short_video)
        assert rows[0]['score'] == '80.5'

    def test_process_batch_export_json(self, processor, mock_search, mock_algorithm, tmp_path):
        """Test exporting results to JSON."""
        short_video = tmp_path / "short.mp4"
        long_video = tmp_path / "long.mp4"
        short_video.touch()
        long_video.touch()

        output_file = tmp_path / "results.json"

        with patch('duplicateflow.algorithms.base.video_loader.get_video_duration') as mock_duration:
            mock_duration.return_value = 30.0

            results = processor.process_batch(
                short_videos=[str(short_video)],
                long_video=str(long_video),
                algorithm='frame_hash',
                output_file=str(output_file),
                show_progress=False,
                strategy='standard'
            )

        # Verify JSON file created
        assert output_file.exists()

        # Read and verify JSON content
        with open(output_file, 'r') as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]['short_video'] == str(short_video)
        assert data[0]['score'] == 80.5


class TestBatchProcessorCheckpointing:
    """Test checkpointing functionality."""

    @pytest.fixture
    def processor(self):
        return BatchProcessor(num_workers=2, checkpoint_interval=2, max_retries=1)

    @pytest.fixture
    def mock_search(self):
        with patch('duplicateflow.processing.parallel_search.ParallelWindowSearch') as mock:
            search_instance = Mock()
            search_instance.search.return_value = {
                'offset': 10.0,
                'score': 75.0,
                'accepted': True
            }
            mock.return_value = search_instance
            yield mock

    @pytest.fixture
    def mock_algorithm(self):
        with patch('duplicateflow.core.get_algorithm') as mock:
            # Create a mock algorithm class
            algo_instance = Mock()
            algo_instance.name = "frame_hash"
            algo_instance.configure = Mock()
            algo_instance.compare.return_value = {
                'similarity': 0.75,  # Will be converted to percentage
                'offset': 10.0,
                'accepted': True
            }

            # Mock the class itself
            algo_class = Mock(return_value=algo_instance)
            mock.return_value = algo_class
            yield mock

    def test_checkpoint_save(self, processor, mock_search, mock_algorithm, tmp_path):
        """Test checkpoint is saved at interval."""
        # Create 3 videos (checkpoint_interval=2)
        short_videos = []
        for i in range(3):
            video = tmp_path / f"short{i}.mp4"
            video.touch()
            short_videos.append(str(video))

        long_video = tmp_path / "long.mp4"
        long_video.touch()

        checkpoint_file = tmp_path / "checkpoint.pkl"

        results = processor.process_batch(
            short_videos=short_videos,
            long_video=str(long_video),
            algorithm='frame_hash',
            checkpoint_file=str(checkpoint_file),
            show_progress=False
        )

        # Checkpoint should have been saved
        assert checkpoint_file.exists()

    def test_checkpoint_resume(self, processor, tmp_path):
        """Test resuming from checkpoint."""
        # Create fake checkpoint file
        checkpoint_file = tmp_path / "checkpoint.pkl"

        # Create fake checkpoint data (BatchResult list)
        import pickle

        result = BatchResult(
            short_video='video1.mp4',
            long_video='long.mp4',
            offset=5.0,
            score=70.0,
            accepted=True,
            algorithm='frame_hash',
            duration=1.0,
            timestamp=datetime.now().isoformat()
        )

        checkpoint_data = {
            'results': [result],
            'next_index': 1  # Next video index to process
        }

        with open(checkpoint_file, 'wb') as f:
            pickle.dump(checkpoint_data, f)

        # Load checkpoint - returns (results, next_index) tuple
        results, next_index = processor._load_checkpoint(str(checkpoint_file))

        assert results is not None
        assert len(results) == 1
        assert results[0].short_video == 'video1.mp4'
        assert next_index == 1


class TestBatchProcessorGetStats:
    """Test get_stats method."""

    def test_get_stats_with_results(self):
        """Test statistics calculation."""
        processor = BatchProcessor()

        results = [
            BatchResult(
                short_video=f"video{i}.mp4",
                long_video="long.mp4",
                offset=10.0 * i,
                score=80.0 + i,
                accepted=True,
                algorithm="frame_hash",
                duration=2.0 + i * 0.5
            )
            for i in range(3)
        ]

        stats = processor.get_stats(results)

        assert stats['total_videos'] == 3
        assert stats['successful'] == 3
        assert stats['failed'] == 0
        assert stats['accepted'] == 3
        assert 'avg_score' in stats
        assert 'avg_duration' in stats
        assert stats['avg_score'] == pytest.approx(81.0, abs=0.1)

    def test_get_stats_empty(self):
        """Test stats with no results."""
        processor = BatchProcessor()
        stats = processor.get_stats([])

        # Empty results return empty dict
        assert stats == {}


class TestBatchProcessorProcessMatrix:
    """Test process_matrix N-to-N comparison."""

    @pytest.fixture
    def processor(self):
        return BatchProcessor(num_workers=2)

    @pytest.fixture
    def mock_search(self):
        with patch('duplicateflow.processing.parallel_search.ParallelWindowSearch') as mock:
            search_instance = Mock()
            search_instance.search.return_value = {
                'offset': 10.0,
                'score': 75.0,
                'accepted': True
            }
            mock.return_value = search_instance
            yield mock

    @pytest.fixture
    def mock_algorithm(self):
        with patch('duplicateflow.core.get_algorithm') as mock:
            # Create a mock algorithm class
            algo_instance = Mock()
            algo_instance.name = "frame_hash"
            algo_instance.configure = Mock()
            algo_instance.compare.return_value = {
                'similarity': 0.75,  # Will be converted to percentage
                'offset': 10.0,
                'accepted': True
            }

            # Mock the class itself
            algo_class = Mock(return_value=algo_instance)
            mock.return_value = algo_class
            yield mock

    def test_process_matrix_two_videos(self, processor, mock_search, mock_algorithm, tmp_path):
        """Test N-to-N comparison with 2 videos."""
        videos = []
        for i in range(2):
            video = tmp_path / f"video{i}.mp4"
            video.touch()
            videos.append(str(video))

        with patch('duplicateflow.algorithms.base.video_loader.get_video_duration') as mock_duration:
            mock_duration.return_value = 30.0

            results = processor.process_matrix(
                video_list=videos,
                algorithm='frame_hash',
                show_progress=False
            )

        # 2 videos = 2x2 matrix
        assert len(results) == 2
        assert len(results[0]) == 2

    def test_process_matrix_export(self, processor, mock_search, mock_algorithm, tmp_path):
        """Test exporting matrix results."""
        videos = []
        for i in range(2):
            video = tmp_path / f"video{i}.mp4"
            video.touch()
            videos.append(str(video))

        output_file = tmp_path / "matrix.csv"

        with patch('duplicateflow.algorithms.base.video_loader.get_video_duration') as mock_duration:
            mock_duration.return_value = 30.0

            results = processor.process_matrix(
                video_list=videos,
                algorithm='frame_hash',
                output_file=str(output_file),
                show_progress=False
            )

        # Should create output file
        assert output_file.exists()
