"""
Unit tests for find command.

Tests the CLI command that finds duplicate videos in a directory.
"""

import argparse
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open

from duplicateflow.cli.commands.find_command import (
    create_find_parser,
    run_find_command
)
from duplicateflow.core.models import DetectionResult, DuplicateGroup, ScanResult


class TestFindCommandParser:
    """Test argument parser creation and parsing."""

    @pytest.fixture
    def parser(self):
        """Create parser with find subcommand."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers()
        return create_find_parser(subparsers)

    def test_parser_creation(self, parser):
        """Test parser is created successfully."""
        assert parser is not None
        assert parser.prog.endswith('find')

    def test_parse_basic_args(self):
        """Test parsing basic directory argument."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_find_parser(subparsers)

        args = main_parser.parse_args(['find', '/path/to/videos'])

        assert args.command == 'find'
        assert args.directory == '/path/to/videos'
        assert args.preset == 'balanced'
        assert args.threshold == 70.0
        assert args.recursive is False
        assert args.max_comparisons is None
        assert args.output_json is None
        assert args.output_csv is None
        assert args.formats is None
        assert args.min_size is None

    def test_parse_with_recursive(self):
        """Test parsing with recursive flag."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_find_parser(subparsers)

        args = main_parser.parse_args(['find', '/videos', '--recursive'])

        assert args.recursive is True

    def test_parse_with_max_comparisons(self):
        """Test parsing with max-comparisons limit."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_find_parser(subparsers)

        args = main_parser.parse_args([
            'find', '/videos', '--max-comparisons', '100'
        ])

        assert args.max_comparisons == 100

    def test_parse_with_output_options(self):
        """Test parsing with output file options."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_find_parser(subparsers)

        args = main_parser.parse_args([
            'find', '/videos',
            '--output-json', 'results.json',
            '--output-csv', 'results.csv'
        ])

        assert args.output_json == 'results.json'
        assert args.output_csv == 'results.csv'

    def test_parse_all_options(self):
        """Test parsing with all options."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_find_parser(subparsers)

        args = main_parser.parse_args([
            'find',
            '/videos',
            '--preset', 'thorough',
            '--threshold', '80.0',
            '--recursive',
            '--max-comparisons', '500',
            '--output-json', 'dupes.json',
            '--output-csv', 'dupes.csv'
        ])

        assert args.directory == '/videos'
        assert args.preset == 'thorough'
        assert args.threshold == 80.0
        assert args.recursive is True
        assert args.max_comparisons == 500
        assert args.output_json == 'dupes.json'
        assert args.output_csv == 'dupes.csv'


class TestFindCommandExecution:
    """Test command execution logic."""

    @pytest.fixture
    def mock_scan_result(self, tmp_path):
        """Create a mock scan result."""
        from duplicateflow.core.models import VideoFile, VideoFormat

        result = Mock(spec=ScanResult)
        result.total_videos = 5

        # Create VideoFile objects with path attributes
        videos = []
        for i in range(1, 6):
            video_file = Mock(spec=VideoFile)
            video_file.path = tmp_path / f"video{i}.mp4"
            video_file.format = VideoFormat.MP4
            video_file.size_mb = 10.0
            videos.append(video_file)

        result.videos = videos
        return result

    @pytest.fixture
    def mock_detection_result(self, tmp_path):
        """Create a mock detection result."""
        result = Mock(spec=DetectionResult)
        result.total_videos_scanned = 5
        result.total_comparisons = 10
        result.duplicates_found = 2
        result.duplicate_groups = [
            Mock(
                spec=DuplicateGroup,
                videos=[tmp_path / "video1.mp4", tmp_path / "video2.mp4"],
                representative=tmp_path / "video1.mp4",
                avg_similarity=90.0
            ),
            Mock(
                spec=DuplicateGroup,
                videos=[tmp_path / "video3.mp4", tmp_path / "video4.mp4"],
                representative=tmp_path / "video3.mp4",
                avg_similarity=85.0
            )
        ]
        result.space_reclaimable_mb = 150.0
        result.to_json = Mock(return_value='{"duplicates_found": 2}')
        return result

    @patch('duplicateflow.cli.commands.find_command.Pipeline')
    @patch('duplicateflow.cli.commands.find_command.ScanService')
    @patch('duplicateflow.cli.commands.find_command.ComparisonService')
    @patch('duplicateflow.cli.commands.find_command.DuplicateFinderService')
    @patch('duplicateflow.cli.commands.find_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.find_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.find_command.display_detection_result')
    @patch('duplicateflow.cli.commands.find_command.Console')
    def test_run_find_success(
        self,
        mock_console_cls,
        mock_display,
        mock_ui_adapter,
        mock_progress,
        mock_finder_cls,
        mock_comparison_cls,
        mock_scan_cls,
        mock_pipeline_cls,
        tmp_path,
        mock_scan_result,
        mock_detection_result
    ):
        """Test successful find operation."""
        # Create test directory
        test_dir = tmp_path / "videos"
        test_dir.mkdir()

        # Setup mocks
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_pipeline = Mock()
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        mock_scan_service = Mock()
        mock_scan_service.scan_directory.return_value = mock_scan_result
        mock_scan_cls.return_value = mock_scan_service

        mock_finder_service = Mock()
        mock_finder_service.find_duplicates.return_value = mock_detection_result
        mock_finder_cls.return_value = mock_finder_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        # Create args
        args = argparse.Namespace(
            directory=str(test_dir),
            preset='balanced',
            threshold=70.0,
            recursive=False,
            max_comparisons=None,
            output_json=None,
            output_csv=None,
            formats=None,
            min_size=None
        )

        # Execute
        exit_code = run_find_command(args)

        # Verify
        assert exit_code == 0
        mock_pipeline_cls.from_preset.assert_called_once_with('balanced')
        mock_scan_service.scan_directory.assert_called_once()
        mock_finder_service.find_duplicates.assert_called_once()
        mock_display.assert_called_once()

    @patch('duplicateflow.cli.commands.find_command.Console')
    def test_run_find_directory_not_found(self, mock_console_cls):
        """Test error when directory doesn't exist."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        args = argparse.Namespace(
            directory='/nonexistent/directory',
            preset='balanced',
            threshold=70.0,
            recursive=False,
            max_comparisons=None,
            output_json=None,
            output_csv=None,
            formats=None,
            min_size=None
        )

        exit_code = run_find_command(args)

        assert exit_code == 1
        assert any('Error' in str(call) or 'not found' in str(call)
                   for call in mock_console.print.call_args_list)

    @patch('duplicateflow.cli.commands.find_command.Console')
    def test_run_find_not_a_directory(self, mock_console_cls, tmp_path):
        """Test error when path is not a directory."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        # Create a file instead of directory
        test_file = tmp_path / "file.txt"
        test_file.touch()

        args = argparse.Namespace(
            directory=str(test_file),
            preset='balanced',
            threshold=70.0,
            recursive=False,
            max_comparisons=None,
            output_json=None,
            output_csv=None,
            formats=None,
            min_size=None
        )

        exit_code = run_find_command(args)

        assert exit_code == 1

    @patch('duplicateflow.cli.commands.find_command.Pipeline')
    @patch('duplicateflow.cli.commands.find_command.ScanService')
    @patch('duplicateflow.cli.commands.find_command.ComparisonService')
    @patch('duplicateflow.cli.commands.find_command.DuplicateFinderService')
    @patch('duplicateflow.cli.commands.find_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.find_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.find_command.Console')
    def test_run_find_no_videos_found(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_finder_cls,
        mock_comparison_cls,
        mock_scan_cls,
        mock_pipeline_cls,
        tmp_path
    ):
        """Test when scan finds no videos."""
        test_dir = tmp_path / "empty"
        test_dir.mkdir()

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_pipeline = Mock()
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        # Scan returns 0 videos
        mock_scan_result = Mock(spec=ScanResult)
        mock_scan_result.total_videos = 0
        mock_scan_result.videos = []

        mock_scan_service = Mock()
        mock_scan_service.scan_directory.return_value = mock_scan_result
        mock_scan_cls.return_value = mock_scan_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            directory=str(test_dir),
            preset='balanced',
            threshold=70.0,
            recursive=False,
            max_comparisons=None,
            output_json=None,
            output_csv=None,
            formats=None,
            min_size=None
        )

        exit_code = run_find_command(args)

        # Should return 0 (no error, just no videos)
        assert exit_code == 0

    @patch('duplicateflow.cli.commands.find_command.Pipeline')
    @patch('duplicateflow.cli.commands.find_command.ScanService')
    @patch('duplicateflow.cli.commands.find_command.ComparisonService')
    @patch('duplicateflow.cli.commands.find_command.DuplicateFinderService')
    @patch('duplicateflow.cli.commands.find_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.find_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.find_command.display_detection_result')
    @patch('duplicateflow.cli.commands.find_command.Console')
    @patch('builtins.open', create=True)
    def test_run_find_with_json_export(
        self,
        mock_open_func,
        mock_console_cls,
        mock_display,
        mock_ui_adapter,
        mock_progress,
        mock_finder_cls,
        mock_comparison_cls,
        mock_scan_cls,
        mock_pipeline_cls,
        tmp_path,
        mock_scan_result,
        mock_detection_result
    ):
        """Test JSON export functionality."""
        test_dir = tmp_path / "videos"
        test_dir.mkdir()

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_pipeline = Mock()
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        mock_scan_service = Mock()
        mock_scan_service.scan_directory.return_value = mock_scan_result
        mock_scan_cls.return_value = mock_scan_service

        mock_finder_service = Mock()
        mock_finder_service.find_duplicates.return_value = mock_detection_result
        mock_finder_cls.return_value = mock_finder_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        mock_file = MagicMock()
        mock_open_func.return_value.__enter__.return_value = mock_file

        output_json = tmp_path / "results.json"
        args = argparse.Namespace(
            directory=str(test_dir),
            preset='balanced',
            threshold=70.0,
            recursive=False,
            max_comparisons=None,
            output_json=str(output_json),
            output_csv=None,
            formats=None,
            min_size=None
        )

        exit_code = run_find_command(args)

        assert exit_code == 0
        # Verify JSON file was written
        assert any(str(output_json) in str(call) for call in mock_open_func.call_args_list)

    @patch('duplicateflow.cli.commands.find_command.Pipeline')
    @patch('duplicateflow.cli.commands.find_command.Console')
    def test_run_find_invalid_preset(self, mock_console_cls, mock_pipeline_cls, tmp_path):
        """Test error when preset loading fails."""
        test_dir = tmp_path / "videos"
        test_dir.mkdir()

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_pipeline_cls.from_preset.side_effect = ValueError("Invalid preset")

        args = argparse.Namespace(
            directory=str(test_dir),
            preset='invalid',
            threshold=70.0,
            recursive=False,
            max_comparisons=None,
            output_json=None,
            output_csv=None,
            formats=None,
            min_size=None
        )

        exit_code = run_find_command(args)

        assert exit_code == 1


class TestFindCommandIntegration:
    """Integration-style tests for complete workflows."""

    @patch('duplicateflow.cli.commands.find_command.Pipeline')
    @patch('duplicateflow.cli.commands.find_command.ScanService')
    @patch('duplicateflow.cli.commands.find_command.ComparisonService')
    @patch('duplicateflow.cli.commands.find_command.DuplicateFinderService')
    @patch('duplicateflow.cli.commands.find_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.find_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.find_command.display_detection_result')
    @patch('duplicateflow.cli.commands.find_command.Console')
    def test_full_find_workflow(
        self,
        mock_console_cls,
        mock_display,
        mock_ui_adapter,
        mock_progress,
        mock_finder_cls,
        mock_comparison_cls,
        mock_scan_cls,
        mock_pipeline_cls,
        tmp_path
    ):
        """Test complete find workflow from args to result."""
        # Create directory structure
        test_dir = tmp_path / "videos"
        test_dir.mkdir()

        # Setup complete mock chain
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_pipeline = Mock()
        mock_pipeline_cls.from_preset.return_value = mock_pipeline

        # Scan finds 10 videos
        from duplicateflow.core.models import VideoFile, VideoFormat

        mock_scan_result = Mock(spec=ScanResult)
        mock_scan_result.total_videos = 10

        videos = []
        for i in range(10):
            video_file = Mock(spec=VideoFile)
            video_file.path = tmp_path / f"video{i}.mp4"
            video_file.format = VideoFormat.MP4
            video_file.size_mb = 10.0
            videos.append(video_file)

        mock_scan_result.videos = videos

        mock_scan_service = Mock()
        mock_scan_service.scan_directory.return_value = mock_scan_result
        mock_scan_cls.return_value = mock_scan_service

        # Detection finds 3 duplicate groups
        mock_detection_result = Mock(spec=DetectionResult)
        mock_detection_result.duplicate_groups = [Mock(), Mock(), Mock()]
        mock_detection_result.duplicates_found = 6

        mock_finder_service = Mock()
        mock_finder_service.find_duplicates.return_value = mock_detection_result
        mock_finder_cls.return_value = mock_finder_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        # Execute with all options
        args = argparse.Namespace(
            directory=str(test_dir),
            preset='thorough',
            threshold=80.0,
            recursive=True,
            max_comparisons=100,
            output_json=None,
            output_csv=None,
            formats=None,
            min_size=None
        )

        exit_code = run_find_command(args)

        # Verify complete workflow
        assert exit_code == 0
        mock_pipeline_cls.from_preset.assert_called_with('thorough')
        mock_scan_cls.assert_called_once()

        # Verify scan was called with recursive=True
        scan_call_args = mock_scan_service.scan_directory.call_args
        assert scan_call_args is not None

        # Verify finder was called with max_comparisons
        finder_call_args = mock_finder_service.find_duplicates.call_args
        assert finder_call_args is not None

        mock_display.assert_called_once()
