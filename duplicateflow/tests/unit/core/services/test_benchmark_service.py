"""
Unit tests for BenchmarkService.

Tests the benchmarking service that measures pipeline performance
and accuracy.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import json

from duplicateflow.core.services import BenchmarkService
from duplicateflow.core.interfaces import NullProgressReporter, NullUIAdapter


class TestBenchmarkServiceInstantiation:
    """Test service instantiation."""

    def test_init(self):
        """Test basic initialization."""
        service = BenchmarkService(
            NullProgressReporter(),
            NullUIAdapter()
        )
        assert service.progress is not None
        assert service.ui is not None

    def test_dependency_injection(self):
        """Test that progress and ui adapters are properly injected."""
        progress = NullProgressReporter()
        ui = NullUIAdapter()

        service = BenchmarkService(progress, ui)

        assert service.progress is progress
        assert service.ui is ui


class TestBenchmarkServiceBenchmarkPipeline:
    """Test benchmark_pipeline method."""

    @pytest.fixture
    def service(self):
        return BenchmarkService(
            NullProgressReporter(),
            NullUIAdapter()
        )

    @patch('duplicateflow.core.services.benchmark_service.Pipeline')
    @patch('duplicateflow.core.services.benchmark_service.tracemalloc')
    @patch('duplicateflow.core.services.benchmark_service.time')
    def test_benchmark_pipeline_success(self, mock_time, mock_tracemalloc, mock_pipeline_cls, service, tmp_path):
        """Test successful pipeline benchmarking."""
        # Setup files
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        # Mock time
        mock_time.perf_counter.side_effect = [0.0, 0.5]  # 500ms

        # Mock tracemalloc
        mock_tracemalloc.get_traced_memory.return_value = (10 * 1024 * 1024, 20 * 1024 * 1024)  # 10MB current, 20MB peak

        # Mock pipeline
        mock_pipeline = Mock()
        mock_pipeline.compare.return_value = {
            'global_score': 85.5,
            'accepted': True,
            'individual_results': [
                {
                    'algorithm': 'frame_hash',
                    'time_ms': 200.0,
                    'similarity': 90.0,
                    'memory_mb': 5.0,
                    'frames_processed': 100,
                    'cache_hit_rate': 0.5
                },
                {
                    'algorithm': 'ssim',
                    'time_ms': 300.0,
                    'similarity': 81.0,
                    'memory_mb': 10.0,
                    'frames_processed': 100,
                    'cache_hit_rate': 0.3
                }
            ],
            'cache_stats': {'hits': 10, 'misses': 5}
        }
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        # Execute
        benchmark = service.benchmark_pipeline(video1, video2, "balanced", threshold=70.0)

        # Verify
        assert benchmark.pipeline_name == "balanced"
        assert benchmark.total_time_ms == 500.0
        assert benchmark.similarity_score == 85.5
        assert benchmark.is_duplicate is True
        assert benchmark.memory_peak_mb == 20.0
        assert len(benchmark.algorithm_benchmarks) == 2

        # Verify algorithm benchmarks
        assert benchmark.algorithm_benchmarks[0].algorithm_name == 'frame_hash'
        assert benchmark.algorithm_benchmarks[0].execution_time_ms == 200.0
        assert benchmark.algorithm_benchmarks[1].algorithm_name == 'ssim'

    @patch('duplicateflow.core.services.benchmark_service.Pipeline')
    def test_benchmark_pipeline_invalid_preset(self, mock_pipeline_cls, service, tmp_path):
        """Test benchmarking with invalid pipeline preset."""
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        mock_pipeline_cls.from_preset.side_effect = ValueError("Unknown preset")

        with pytest.raises(ValueError, match="Unknown preset"):
            service.benchmark_pipeline(video1, video2, "nonexistent")

    @patch('duplicateflow.core.services.benchmark_service.Pipeline')
    @patch('duplicateflow.core.services.benchmark_service.tracemalloc')
    def test_benchmark_pipeline_comparison_fails(self, mock_tracemalloc, mock_pipeline_cls, service, tmp_path):
        """Test handling when pipeline comparison fails."""
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        mock_pipeline = Mock()
        mock_pipeline.compare.side_effect = RuntimeError("Comparison error")
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        with pytest.raises(RuntimeError, match="Comparison error"):
            service.benchmark_pipeline(video1, video2, "balanced")

        # Verify tracemalloc was properly stopped
        mock_tracemalloc.stop.assert_called()

    @patch('duplicateflow.core.services.benchmark_service.Pipeline')
    @patch('duplicateflow.core.services.benchmark_service.tracemalloc')
    @patch('duplicateflow.core.services.benchmark_service.time')
    def test_benchmark_pipeline_ui_messages(self, mock_time, mock_tracemalloc, mock_pipeline_cls, tmp_path):
        """Test UI messages during benchmarking."""
        ui = NullUIAdapter()
        service = BenchmarkService(NullProgressReporter(), ui)

        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        # Mock everything
        mock_time.perf_counter.side_effect = [0.0, 0.1]
        mock_tracemalloc.get_traced_memory.return_value = (10 * 1024 * 1024, 20 * 1024 * 1024)

        mock_pipeline = Mock()
        mock_pipeline.compare.return_value = {
            'global_score': 80.0,
            'accepted': True,
            'individual_results': [],
            'cache_stats': {}
        }
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        service.benchmark_pipeline(video1, video2, "balanced")

        # No UI messages in successful case (only progress tracking)
        # Error cases would show messages
        assert isinstance(ui.messages, list)


class TestBenchmarkServiceComparePipelines:
    """Test compare_pipelines method."""

    @pytest.fixture
    def service(self):
        return BenchmarkService(
            NullProgressReporter(),
            NullUIAdapter()
        )

    @patch('duplicateflow.core.services.benchmark_service.Pipeline')
    @patch('duplicateflow.core.services.benchmark_service.tracemalloc')
    @patch('duplicateflow.core.services.benchmark_service.time')
    def test_compare_pipelines_success(self, mock_time, mock_tracemalloc, mock_pipeline_cls, service, tmp_path):
        """Test comparing multiple pipelines."""
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        # Mock time (3 calls, 3 pipelines)
        mock_time.perf_counter.side_effect = [
            0.0, 0.1,  # fast
            0.0, 0.2,  # balanced
            0.0, 0.5   # thorough
        ]

        # Mock tracemalloc
        mock_tracemalloc.get_traced_memory.return_value = (10 * 1024 * 1024, 20 * 1024 * 1024)

        # Mock pipeline
        mock_pipeline = Mock()
        mock_pipeline.compare.return_value = {
            'global_score': 80.0,
            'accepted': True,
            'individual_results': [],
            'cache_stats': {}
        }
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        # Execute
        result = service.compare_pipelines(
            video1,
            video2,
            ["fast", "balanced", "thorough"],
            threshold=70.0,
            ground_truth=True
        )

        # Verify
        assert len(result.pipeline_benchmarks) == 3
        assert result.video1_path == video1
        assert result.video2_path == video2
        assert result.ground_truth is True

    @patch('duplicateflow.core.services.benchmark_service.Pipeline')
    @patch('duplicateflow.core.services.benchmark_service.tracemalloc')
    @patch('duplicateflow.core.services.benchmark_service.time')
    def test_compare_pipelines_partial_failure(self, mock_time, mock_tracemalloc, mock_pipeline_cls, service, tmp_path):
        """Test comparing pipelines with one failing."""
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        # Mock time for successful benchmarks
        mock_time.perf_counter.side_effect = [
            0.0, 0.1,  # fast - success
            # balanced - will fail, no time calls
            0.0, 0.5   # thorough - success
        ]

        mock_tracemalloc.get_traced_memory.return_value = (10 * 1024 * 1024, 20 * 1024 * 1024)

        # Mock pipeline - fail on second preset
        call_count = [0]

        def mock_from_preset(name):
            call_count[0] += 1
            if call_count[0] == 2:  # Second call (balanced)
                raise ValueError("Invalid preset")
            mock_pipeline = Mock()
            mock_pipeline.compare.return_value = {
                'global_score': 80.0,
                'accepted': True,
                'individual_results': [],
                'cache_stats': {}
            }
            return mock_pipeline

        mock_pipeline_cls.from_preset.side_effect = mock_from_preset

        # Execute - should continue despite failure
        result = service.compare_pipelines(
            video1,
            video2,
            ["fast", "balanced", "thorough"],
            threshold=70.0
        )

        # Should have 2 successful benchmarks (fast and thorough)
        assert len(result.pipeline_benchmarks) == 2


class TestBenchmarkServiceBenchmarkTestset:
    """Test benchmark_testset method."""

    @pytest.fixture
    def service(self):
        return BenchmarkService(
            NullProgressReporter(),
            NullUIAdapter()
        )

    @patch('duplicateflow.core.services.benchmark_service.Pipeline')
    @patch('duplicateflow.core.services.benchmark_service.tracemalloc')
    @patch('duplicateflow.core.services.benchmark_service.time')
    @patch('builtins.open', new_callable=mock_open)
    def test_benchmark_testset_success(self, mock_file, mock_time, mock_tracemalloc, mock_pipeline_cls, service, tmp_path):
        """Test benchmarking on a test set."""
        # Create test videos
        v1 = tmp_path / "v1.mp4"
        v2 = tmp_path / "v2.mp4"
        v3 = tmp_path / "v3.mp4"
        v4 = tmp_path / "v4.mp4"
        for v in [v1, v2, v3, v4]:
            v.touch()

        # Mock test set
        testset = {
            'name': 'test_set_v1',
            'pairs': [
                {'video1': str(v1), 'video2': str(v2), 'is_duplicate': True},
                {'video1': str(v3), 'video2': str(v4), 'is_duplicate': False}
            ]
        }
        mock_file.return_value.read.return_value = json.dumps(testset)
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(testset)

        # Mock json.load
        with patch('json.load', return_value=testset):
            # Mock time (2 pairs)
            mock_time.perf_counter.side_effect = [
                0.0, 0.1,  # pair 1
                0.0, 0.2   # pair 2
            ]

            mock_tracemalloc.get_traced_memory.return_value = (10 * 1024 * 1024, 20 * 1024 * 1024)

            # Mock pipeline - first returns duplicate, second doesn't
            call_count = [0]

            def mock_compare(v1_str, v2_str):
                call_count[0] += 1
                return {
                    'global_score': 85.0 if call_count[0] == 1 else 50.0,
                    'accepted': call_count[0] == 1,
                    'individual_results': [],
                    'cache_stats': {}
                }

            mock_pipeline = Mock()
            mock_pipeline.compare.side_effect = mock_compare
            mock_pipeline_cls.from_preset.return_value = mock_pipeline

            # Execute
            result = service.benchmark_testset(
                Path("/testdata/test.json"),
                "balanced",
                threshold=70.0
            )

            # Verify
            assert result.pipeline_name == "balanced"
            assert result.test_set_name == "test_set_v1"
            assert result.total_comparisons == 2

            # Check accuracy metrics (both correct predictions)
            metrics = result.accuracy_metrics
            assert metrics.true_positives == 1  # Pair 1 correctly identified as duplicate
            assert metrics.true_negatives == 1  # Pair 2 correctly identified as non-duplicate
            assert metrics.false_positives == 0
            assert metrics.false_negatives == 0
            assert metrics.accuracy == 1.0  # 100% accurate

    @patch('builtins.open', new_callable=mock_open)
    def test_benchmark_testset_empty(self, mock_file, service):
        """Test benchmarking on empty test set."""
        testset = {
            'name': 'empty_set',
            'pairs': []
        }

        with patch('json.load', return_value=testset):
            result = service.benchmark_testset(
                Path("/testdata/empty.json"),
                "balanced",
                threshold=70.0
            )

            assert result.total_comparisons == 0
            assert result.avg_execution_time_ms == 0.0

    @patch('builtins.open', side_effect=FileNotFoundError("File not found"))
    def test_benchmark_testset_file_not_found(self, mock_file, service):
        """Test benchmarking with missing test set file."""
        with pytest.raises(FileNotFoundError):
            service.benchmark_testset(
                Path("/testdata/nonexistent.json"),
                "balanced"
            )


class TestBenchmarkServiceProfileAlgorithms:
    """Test profile_algorithms method."""

    @pytest.fixture
    def service(self):
        return BenchmarkService(
            NullProgressReporter(),
            NullUIAdapter()
        )

    @patch('duplicateflow.core.services.benchmark_service.Pipeline')
    @patch('duplicateflow.core.services.benchmark_service.tracemalloc')
    @patch('duplicateflow.core.services.benchmark_service.time')
    def test_profile_algorithms(self, mock_time, mock_tracemalloc, mock_pipeline_cls, service, tmp_path):
        """Test profiling individual algorithms."""
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        mock_time.perf_counter.side_effect = [0.0, 0.5]
        mock_tracemalloc.get_traced_memory.return_value = (10 * 1024 * 1024, 20 * 1024 * 1024)

        mock_pipeline = Mock()
        mock_pipeline.compare.return_value = {
            'global_score': 85.0,
            'accepted': True,
            'individual_results': [
                {
                    'algorithm': 'fast_algo',
                    'time_ms': 100.0,
                    'similarity': 90.0,
                    'memory_mb': 5.0,
                    'frames_processed': 100,
                    'cache_hit_rate': 0.5
                },
                {
                    'algorithm': 'slow_algo',
                    'time_ms': 400.0,
                    'similarity': 80.0,
                    'memory_mb': 15.0,
                    'frames_processed': 100,
                    'cache_hit_rate': 0.3
                }
            ],
            'cache_stats': {}
        }
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        profile = service.profile_algorithms(video1, video2, "thorough")

        # Verify profile structure
        assert profile['pipeline'] == "thorough"
        assert profile['total_time_ms'] == 500.0
        assert 'slowest_algorithm' in profile
        assert 'fastest_algorithm' in profile
        assert 'algorithm_rankings' in profile

        # Verify slowest is slow_algo
        assert profile['slowest_algorithm']['algorithm_name'] == 'slow_algo'

        # Verify fastest is fast_algo
        assert profile['fastest_algorithm']['algorithm_name'] == 'fast_algo'

        # Verify rankings
        rankings = profile['algorithm_rankings']
        assert len(rankings) == 2
        assert rankings[0]['algorithm'] == 'slow_algo'  # Ranked by time (slowest first)
        assert rankings[1]['algorithm'] == 'fast_algo'


class TestBenchmarkServiceIntegration:
    """Integration-style tests."""

    @patch('duplicateflow.core.services.benchmark_service.Pipeline')
    @patch('duplicateflow.core.services.benchmark_service.tracemalloc')
    @patch('duplicateflow.core.services.benchmark_service.time')
    def test_full_benchmark_workflow(self, mock_time, mock_tracemalloc, mock_pipeline_cls, tmp_path):
        """Test complete benchmarking workflow."""
        ui = NullUIAdapter()
        progress = NullProgressReporter()
        service = BenchmarkService(progress, ui)

        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        # Mock time
        mock_time.perf_counter.side_effect = [0.0, 0.3]

        # Mock tracemalloc
        mock_tracemalloc.get_traced_memory.return_value = (15 * 1024 * 1024, 25 * 1024 * 1024)

        # Mock pipeline
        mock_pipeline = Mock()
        mock_pipeline.compare.return_value = {
            'global_score': 92.5,
            'accepted': True,
            'individual_results': [
                {
                    'algorithm': 'frame_hash',
                    'time_ms': 150.0,
                    'similarity': 95.0,
                    'memory_mb': 8.0,
                    'frames_processed': 120,
                    'cache_hit_rate': 0.6
                },
                {
                    'algorithm': 'ssim',
                    'time_ms': 150.0,
                    'similarity': 90.0,
                    'memory_mb': 12.0,
                    'frames_processed': 120,
                    'cache_hit_rate': 0.4
                }
            ],
            'cache_stats': {'hits': 15, 'misses': 10}
        }
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        # Execute
        benchmark = service.benchmark_pipeline(video1, video2, "balanced", threshold=75.0)

        # Verify complete result
        assert benchmark.pipeline_name == "balanced"
        assert benchmark.total_time_ms == 300.0
        assert benchmark.similarity_score == 92.5
        assert benchmark.is_duplicate is True
        assert benchmark.memory_peak_mb == 25.0
        assert len(benchmark.algorithm_benchmarks) == 2
        assert benchmark.timestamp is not None

        # Verify algorithm details
        assert benchmark.algorithm_benchmarks[0].algorithm_name == 'frame_hash'
        assert benchmark.algorithm_benchmarks[0].similarity == 95.0
        assert benchmark.algorithm_benchmarks[1].algorithm_name == 'ssim'

        # Verify cache stats
        assert benchmark.cache_statistics == {'hits': 15, 'misses': 10}
