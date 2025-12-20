"""
Unit tests for benchmark command.

Tests the CLI command that benchmarks pipeline performance and accuracy.
"""

import argparse
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from duplicateflow.cli.commands.benchmark_command import (
    create_benchmark_parser,
    run_benchmark_command
)
from duplicateflow.core.models import PipelineBenchmark, ComparisonBenchmark


class TestBenchmarkCommandParser:
    """Test argument parser creation and parsing."""

    def test_parser_creation(self):
        """Test parser is created successfully."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers()
        parser = create_benchmark_parser(subparsers)

        assert parser is not None
        assert parser.prog.endswith('benchmark')

    def test_parse_basic_args(self):
        """Test parsing basic video arguments."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_benchmark_parser(subparsers)

        args = main_parser.parse_args([
            'benchmark', 'video1.mp4', 'video2.mp4'
        ])

        assert args.command == 'benchmark'
        assert args.video1 == 'video1.mp4'
        assert args.video2 == 'video2.mp4'

    def test_parse_with_preset(self):
        """Test parsing with preset option."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_benchmark_parser(subparsers)

        args = main_parser.parse_args([
            'benchmark', 'v1.mp4', 'v2.mp4', '--preset', 'thorough'
        ])

        assert args.preset == 'thorough'

    def test_parse_with_multiple_presets(self):
        """Test parsing with multiple presets."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_benchmark_parser(subparsers)

        args = main_parser.parse_args([
            'benchmark', 'v1.mp4', 'v2.mp4',
            '--presets', 'fast', 'balanced', 'thorough'
        ])

        assert args.presets == ['fast', 'balanced', 'thorough']

    def test_parse_with_testset(self):
        """Test parsing with testset option."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_benchmark_parser(subparsers)

        args = main_parser.parse_args([
            'benchmark', '--testset', 'testdata.json', '--preset', 'balanced'
        ])

        assert args.testset == 'testdata.json'
        assert args.preset == 'balanced'


class TestBenchmarkCommandExecution:
    """Test command execution logic."""

    @pytest.fixture
    def mock_benchmark_result(self):
        """Create a mock benchmark result."""
        result = Mock(spec=PipelineBenchmark)
        result.pipeline_name = "balanced"
        result.total_time_ms = 250.0
        result.memory_peak_mb = 50.0
        result.global_score = 85.5
        return result

    @patch('duplicateflow.cli.commands.benchmark_command.BenchmarkService')
    @patch('duplicateflow.cli.commands.benchmark_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.benchmark_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.benchmark_command.display_comparison_benchmark')
    @patch('duplicateflow.cli.commands.benchmark_command.Console')
    def test_run_benchmark_single_preset(
        self,
        mock_console_cls,
        mock_display,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls,
        tmp_path,
        mock_benchmark_result
    ):
        """Test benchmarking with single preset."""
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_service = Mock()
        mock_service.benchmark_pipeline.return_value = mock_benchmark_result
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            video1=str(video1),
            video2=str(video2),
            preset='balanced',
            presets=None,
            threshold=70.0,
            testset=None,
            output_json=None,
            output_csv=None
        )

        exit_code = run_benchmark_command(args)

        assert exit_code == 0
        mock_service.benchmark_pipeline.assert_called_once()

    @patch('duplicateflow.cli.commands.benchmark_command.BenchmarkService')
    @patch('duplicateflow.cli.commands.benchmark_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.benchmark_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.benchmark_command.Console')
    def test_run_benchmark_multiple_presets(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls,
        tmp_path
    ):
        """Test benchmarking with multiple presets."""
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_comparison_result = Mock(spec=ComparisonBenchmark)
        mock_comparison_result.pipeline_benchmarks = [Mock(), Mock(), Mock()]

        mock_service = Mock()
        mock_service.compare_pipelines.return_value = mock_comparison_result
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            video1=str(video1),
            video2=str(video2),
            preset=None,
            presets=['fast', 'balanced', 'thorough'],
            threshold=70.0,
            testset=None,
            output_json=None,
            output_csv=None
        )

        exit_code = run_benchmark_command(args)

        assert exit_code == 0
        mock_service.compare_pipelines.assert_called_once()

    @patch('duplicateflow.cli.commands.benchmark_command.Console')
    def test_run_benchmark_video_not_found(self, mock_console_cls, tmp_path):
        """Test error when video doesn't exist."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        args = argparse.Namespace(
            video1='nonexistent1.mp4',
            video2='nonexistent2.mp4',
            preset='balanced',
            presets=None,
            threshold=70.0,
            testset=None,
            output_json=None,
            output_csv=None
        )

        exit_code = run_benchmark_command(args)

        assert exit_code == 1

    @patch('duplicateflow.cli.commands.benchmark_command.BenchmarkService')
    @patch('duplicateflow.cli.commands.benchmark_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.benchmark_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.benchmark_command.Console')
    def test_run_benchmark_with_testset(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls,
        tmp_path
    ):
        """Test benchmarking with test set."""
        testset_file = tmp_path / "testset.json"
        testset_file.write_text('{"pairs": []}')

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_testset_result = Mock()
        mock_testset_result.total_pairs = 10
        mock_testset_result.accuracy_metrics = Mock()

        mock_service = Mock()
        mock_service.benchmark_testset.return_value = mock_testset_result
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            video1=None,
            video2=None,
            preset='balanced',
            presets=None,
            threshold=70.0,
            testset=str(testset_file),
            output_json=None,
            output_csv=None
        )

        exit_code = run_benchmark_command(args)

        assert exit_code == 0
        mock_service.benchmark_testset.assert_called_once()


class TestBenchmarkCommandIntegration:
    """Integration-style tests for complete workflows."""

    @patch('duplicateflow.cli.commands.benchmark_command.BenchmarkService')
    @patch('duplicateflow.cli.commands.benchmark_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.benchmark_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.benchmark_command.display_comparison_benchmark')
    @patch('duplicateflow.cli.commands.benchmark_command.Console')
    def test_full_benchmark_workflow(
        self,
        mock_console_cls,
        mock_display,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls,
        tmp_path
    ):
        """Test complete benchmark workflow."""
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_result = Mock(spec=PipelineBenchmark)
        mock_result.pipeline_name = "thorough"
        mock_result.total_time_ms = 500.0

        mock_service = Mock()
        mock_service.benchmark_pipeline.return_value = mock_result
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            video1=str(video1),
            video2=str(video2),
            preset='thorough',
            presets=None,
            threshold=80.0,
            testset=None,
            output_json=None,
            output_csv=None
        )

        exit_code = run_benchmark_command(args)

        assert exit_code == 0
        mock_service_cls.assert_called_once()
        mock_service.benchmark_pipeline.assert_called_once()
        mock_display.assert_called_once()
