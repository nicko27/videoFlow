"""
Unit tests for compare command.

Tests the CLI command that compares two videos for similarity.
"""

import argparse
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from duplicateflow.cli.commands.compare_command import (
    create_compare_parser,
    run_compare_command
)
from duplicateflow.core.models import ComparisonResult, AlgorithmResult


class TestCompareCommandParser:
    """Test argument parser creation and parsing."""

    @pytest.fixture
    def parser(self):
        """Create parser with compare subcommand."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers()
        return create_compare_parser(subparsers)

    def test_parser_creation(self, parser):
        """Test parser is created successfully."""
        assert parser is not None
        assert parser.prog.endswith('compare')

    def test_parse_basic_args(self):
        """Test parsing basic video arguments."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_compare_parser(subparsers)

        args = main_parser.parse_args(['compare', 'video1.mp4', 'video2.mp4'])

        assert args.command == 'compare'
        assert args.video1 == 'video1.mp4'
        assert args.video2 == 'video2.mp4'
        assert args.preset == 'balanced'  # Default
        assert args.threshold == 70.0  # Default
        assert args.output_json is None
        assert args.show_details is False

    def test_parse_with_preset(self):
        """Test parsing with preset option."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_compare_parser(subparsers)

        args = main_parser.parse_args([
            'compare', 'v1.mp4', 'v2.mp4', '--preset', 'thorough'
        ])

        assert args.preset == 'thorough'

    def test_parse_with_threshold(self):
        """Test parsing with custom threshold."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_compare_parser(subparsers)

        args = main_parser.parse_args([
            'compare', 'v1.mp4', 'v2.mp4', '--threshold', '85.5'
        ])

        assert args.threshold == 85.5

    def test_parse_with_output_json(self):
        """Test parsing with JSON output option."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_compare_parser(subparsers)

        args = main_parser.parse_args([
            'compare', 'v1.mp4', 'v2.mp4', '--output-json', 'result.json'
        ])

        assert args.output_json == 'result.json'

    def test_parse_with_show_details(self):
        """Test parsing with show-details flag."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_compare_parser(subparsers)

        args = main_parser.parse_args([
            'compare', 'v1.mp4', 'v2.mp4', '--show-details'
        ])

        assert args.show_details is True

    def test_parse_all_options(self):
        """Test parsing with all options."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_compare_parser(subparsers)

        args = main_parser.parse_args([
            'compare',
            'video1.mp4',
            'video2.mp4',
            '--preset', 'thorough',
            '--threshold', '80.0',
            '--output-json', 'results.json',
            '--show-details'
        ])

        assert args.video1 == 'video1.mp4'
        assert args.video2 == 'video2.mp4'
        assert args.preset == 'thorough'
        assert args.threshold == 80.0
        assert args.output_json == 'results.json'
        assert args.show_details is True


class TestCompareCommandExecution:
    """Test command execution logic."""

    @pytest.fixture
    def mock_comparison_result(self):
        """Create a mock comparison result."""
        result = Mock(spec=ComparisonResult)
        result.video1_path = Path("video1.mp4")
        result.video2_path = Path("video2.mp4")
        result.similarity_score = 85.5
        result.is_duplicate = True
        result.pipeline_name = "balanced"
        result.algorithm_results = [
            Mock(spec=AlgorithmResult, algorithm_name='frame_hash', similarity=90.0),
            Mock(spec=AlgorithmResult, algorithm_name='ssim', similarity=81.0)
        ]
        result.to_json = Mock(return_value='{"similarity": 85.5}')
        return result

    @patch('duplicateflow.cli.commands.compare_command.Pipeline')
    @patch('duplicateflow.cli.commands.compare_command.ComparisonService')
    @patch('duplicateflow.cli.commands.compare_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.compare_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.compare_command.display_comparison_result')
    @patch('duplicateflow.cli.commands.compare_command.Console')
    def test_run_compare_success_duplicate(
        self,
        mock_console_cls,
        mock_display,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls,
        mock_pipeline_cls,
        tmp_path,
        mock_comparison_result
    ):
        """Test successful comparison that finds duplicate."""
        # Create test video files
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        # Setup mocks
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_pipeline = Mock()
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        mock_service = Mock()
        mock_service.compare_videos.return_value = mock_comparison_result
        mock_service_cls.return_value = mock_service

        # Progress context manager
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        # Create args
        args = argparse.Namespace(
            video1=str(video1),
            video2=str(video2),
            preset='balanced',
            threshold=70.0,
            output_json=None,
            show_details=False
        )

        # Execute
        exit_code = run_compare_command(args)

        # Verify
        assert exit_code == 0  # Duplicate found
        mock_pipeline_cls.from_preset.assert_called_once_with('balanced')
        mock_service.compare_videos.assert_called_once_with(video1, video2, 70.0)
        mock_display.assert_called_once()

    @patch('duplicateflow.cli.commands.compare_command.Pipeline')
    @patch('duplicateflow.cli.commands.compare_command.ComparisonService')
    @patch('duplicateflow.cli.commands.compare_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.compare_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.compare_command.display_comparison_result')
    @patch('duplicateflow.cli.commands.compare_command.Console')
    def test_run_compare_success_not_duplicate(
        self,
        mock_console_cls,
        mock_display,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls,
        mock_pipeline_cls,
        tmp_path
    ):
        """Test successful comparison that finds no duplicate."""
        # Create test video files
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        # Setup mocks
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_pipeline = Mock()
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        # Result: NOT duplicate
        mock_result = Mock(spec=ComparisonResult)
        mock_result.is_duplicate = False
        mock_result.similarity_score = 45.0

        mock_service = Mock()
        mock_service.compare_videos.return_value = mock_result
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        # Create args
        args = argparse.Namespace(
            video1=str(video1),
            video2=str(video2),
            preset='balanced',
            threshold=70.0,
            output_json=None,
            show_details=False
        )

        # Execute
        exit_code = run_compare_command(args)

        # Verify
        assert exit_code == 1  # NOT duplicate

    @patch('duplicateflow.cli.commands.compare_command.Console')
    def test_run_compare_video1_not_found(self, mock_console_cls, tmp_path):
        """Test error when video1 doesn't exist."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        video2 = tmp_path / "video2.mp4"
        video2.touch()

        args = argparse.Namespace(
            video1='nonexistent.mp4',
            video2=str(video2),
            preset='balanced',
            threshold=70.0,
            output_json=None,
            show_details=False
        )

        exit_code = run_compare_command(args)

        assert exit_code == 1
        # Verify error message was printed
        assert any('Error' in str(call) or 'not found' in str(call)
                   for call in mock_console.print.call_args_list)

    @patch('duplicateflow.cli.commands.compare_command.Console')
    def test_run_compare_video2_not_found(self, mock_console_cls, tmp_path):
        """Test error when video2 doesn't exist."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        video1 = tmp_path / "video1.mp4"
        video1.touch()

        args = argparse.Namespace(
            video1=str(video1),
            video2='nonexistent.mp4',
            preset='balanced',
            threshold=70.0,
            output_json=None,
            show_details=False
        )

        exit_code = run_compare_command(args)

        assert exit_code == 1

    @patch('duplicateflow.cli.commands.compare_command.Pipeline')
    @patch('duplicateflow.cli.commands.compare_command.Console')
    def test_run_compare_invalid_preset(self, mock_console_cls, mock_pipeline_cls, tmp_path):
        """Test error when preset loading fails."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        # Pipeline.from_preset raises exception
        mock_pipeline_cls.from_preset.side_effect = ValueError("Invalid preset")

        args = argparse.Namespace(
            video1=str(video1),
            video2=str(video2),
            preset='invalid',
            threshold=70.0,
            output_json=None,
            show_details=False
        )

        exit_code = run_compare_command(args)

        assert exit_code == 1

    @patch('duplicateflow.cli.commands.compare_command.Pipeline')
    @patch('duplicateflow.cli.commands.compare_command.ComparisonService')
    @patch('duplicateflow.cli.commands.compare_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.compare_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.compare_command.display_comparison_result')
    @patch('duplicateflow.cli.commands.compare_command.Console')
    @patch('builtins.open', create=True)
    def test_run_compare_with_json_output(
        self,
        mock_open,
        mock_console_cls,
        mock_display,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls,
        mock_pipeline_cls,
        tmp_path,
        mock_comparison_result
    ):
        """Test JSON export functionality."""
        # Create test video files
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        # Setup mocks
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_pipeline = Mock()
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        mock_service = Mock()
        mock_service.compare_videos.return_value = mock_comparison_result
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        # Mock file handle
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Create args with JSON output
        output_json = tmp_path / "result.json"
        args = argparse.Namespace(
            video1=str(video1),
            video2=str(video2),
            preset='balanced',
            threshold=70.0,
            output_json=str(output_json),
            show_details=False
        )

        # Execute
        exit_code = run_compare_command(args)

        # Verify
        assert exit_code == 0
        mock_open.assert_called_once_with(str(output_json), 'w')
        mock_file.write.assert_called_once()

    @patch('duplicateflow.cli.commands.compare_command.Pipeline')
    @patch('duplicateflow.cli.commands.compare_command.ComparisonService')
    @patch('duplicateflow.cli.commands.compare_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.compare_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.compare_command.Console')
    def test_run_compare_service_exception(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls,
        mock_pipeline_cls,
        tmp_path
    ):
        """Test error handling when service raises exception."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        mock_pipeline = Mock()
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        # Service raises exception
        mock_service = Mock()
        mock_service.compare_videos.side_effect = RuntimeError("Comparison failed")
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            video1=str(video1),
            video2=str(video2),
            preset='balanced',
            threshold=70.0,
            output_json=None,
            show_details=False
        )

        exit_code = run_compare_command(args)

        assert exit_code == 1


class TestCompareCommandIntegration:
    """Integration-style tests for complete workflows."""

    @patch('duplicateflow.cli.commands.compare_command.Pipeline')
    @patch('duplicateflow.cli.commands.compare_command.ComparisonService')
    @patch('duplicateflow.cli.commands.compare_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.compare_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.compare_command.display_comparison_result')
    @patch('duplicateflow.cli.commands.compare_command.Console')
    def test_full_compare_workflow(
        self,
        mock_console_cls,
        mock_display,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls,
        mock_pipeline_cls,
        tmp_path
    ):
        """Test complete compare workflow from args to result."""
        # Create videos
        video1 = tmp_path / "video1.mp4"
        video2 = tmp_path / "video2.mp4"
        video1.touch()
        video2.touch()

        # Setup complete mock chain
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_pipeline = Mock()
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        mock_result = Mock(spec=ComparisonResult)
        mock_result.is_duplicate = True
        mock_result.similarity_score = 92.5

        mock_service = Mock()
        mock_service.compare_videos.return_value = mock_result
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        # Execute
        args = argparse.Namespace(
            video1=str(video1),
            video2=str(video2),
            preset='thorough',
            threshold=80.0,
            output_json=None,
            show_details=True
        )

        exit_code = run_compare_command(args)

        # Verify complete workflow
        assert exit_code == 0
        mock_pipeline_cls.from_preset.assert_called_with('thorough')
        mock_service_cls.assert_called_once()
        mock_service.compare_videos.assert_called_with(video1, video2, 80.0)
        mock_display.assert_called_once()

        # Verify show_details was passed to display
        display_call_args = mock_display.call_args
        assert display_call_args[0][2] is True  # show_details=True
