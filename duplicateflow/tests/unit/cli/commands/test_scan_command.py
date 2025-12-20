"""
Tests for CLI scan command.

Tests argument parsing, validation, display functions, and command execution.
"""

import argparse
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

import pytest
from rich.console import Console

from duplicateflow.cli.commands.scan_command import (
    create_scan_parser,
    validate_arguments,
    display_results_table,
    display_statistics,
    run_scan_command,
)
from duplicateflow.core.models.scan import VideoFile, ScanResult, VideoFormat


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def arg_parser():
    """Create main parser with scan subcommand."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')
    create_scan_parser(subparsers)
    return parser


@pytest.fixture
def mock_console():
    """Create mock Rich console."""
    console = Mock(spec=Console)
    console.print = Mock()
    return console


@pytest.fixture
def sample_videos():
    """Create sample VideoFile objects for testing."""
    return [
        VideoFile(
            path=Path("/videos/movie1.mp4"),
            size_bytes=100 * 1024 * 1024,  # 100 MB
            format=VideoFormat.MP4,
            created_at=datetime(2023, 1, 1),
            modified_at=datetime(2023, 1, 1),
        ),
        VideoFile(
            path=Path("/videos/movie2.mkv"),
            size_bytes=200 * 1024 * 1024,  # 200 MB
            format=VideoFormat.MKV,
            created_at=datetime(2023, 1, 2),
            modified_at=datetime(2023, 1, 2),
        ),
        VideoFile(
            path=Path("/videos/movie3.avi"),
            size_bytes=150 * 1024 * 1024,  # 150 MB
            format=VideoFormat.AVI,
            created_at=datetime(2023, 1, 3),
            modified_at=datetime(2023, 1, 3),
        ),
    ]


@pytest.fixture
def sample_scan_result(sample_videos):
    """Create sample ScanResult for testing."""
    return ScanResult(
        videos=sample_videos,
        directories_scanned=2,
        total_files_checked=10,
        scan_duration_seconds=5.5,
        timestamp=datetime(2023, 1, 1),
        root_path=Path("/videos"),
        errors=[],
    )


# ============================================================================
# Tests: create_scan_parser
# ============================================================================


class TestCreateScanParser:
    """Tests for create_scan_parser function."""

    def test_parser_created_successfully(self, arg_parser):
        """Test that parser is created with scan command."""
        args = arg_parser.parse_args(['scan', '/path/to/videos'])
        assert args.command == 'scan'
        assert args.directory == '/path/to/videos'

    def test_parser_default_values(self, arg_parser):
        """Test default values for optional arguments."""
        args = arg_parser.parse_args(['scan', '.'])
        assert args.recursive is True
        assert args.follow_symlinks is False
        assert args.show_stats is True
        assert args.formats is None
        assert args.min_size is None
        assert args.max_size is None

    def test_parser_recursive_flags(self, arg_parser):
        """Test recursive and no-recursive flags."""
        # Default recursive=True
        args1 = arg_parser.parse_args(['scan', '.'])
        assert args1.recursive is True

        # Explicit --recursive
        args2 = arg_parser.parse_args(['scan', '.', '--recursive'])
        assert args2.recursive is True

        # --no-recursive
        args3 = arg_parser.parse_args(['scan', '.', '--no-recursive'])
        assert args3.recursive is False

    def test_parser_stats_flags(self, arg_parser):
        """Test show-stats and no-stats flags."""
        # Default show_stats=True
        args1 = arg_parser.parse_args(['scan', '.'])
        assert args1.show_stats is True

        # --no-stats
        args2 = arg_parser.parse_args(['scan', '.', '--no-stats'])
        assert args2.show_stats is False

    def test_parser_follow_symlinks(self, arg_parser):
        """Test follow-symlinks flag."""
        args = arg_parser.parse_args(['scan', '.', '--follow-symlinks'])
        assert args.follow_symlinks is True

    def test_parser_formats_single(self, arg_parser):
        """Test formats argument with single format."""
        args = arg_parser.parse_args(['scan', '.', '--formats', 'mp4'])
        assert args.formats == ['mp4']

    def test_parser_formats_multiple(self, arg_parser):
        """Test formats argument with multiple formats."""
        args = arg_parser.parse_args(['scan', '.', '--formats', 'mp4', 'mkv', 'avi'])
        assert args.formats == ['mp4', 'mkv', 'avi']

    def test_parser_size_filters(self, arg_parser):
        """Test size filter arguments."""
        args = arg_parser.parse_args([
            'scan', '.', '--min-size', '100', '--max-size', '5000'
        ])
        assert args.min_size == 100.0
        assert args.max_size == 5000.0

    def test_parser_all_options(self, arg_parser):
        """Test parser with all options combined."""
        args = arg_parser.parse_args([
            'scan', '/videos',
            '--no-recursive',
            '--follow-symlinks',
            '--formats', 'mp4', 'mkv',
            '--min-size', '50',
            '--max-size', '2000',
            '--no-stats',
        ])
        assert args.directory == '/videos'
        assert args.recursive is False
        assert args.follow_symlinks is True
        assert args.formats == ['mp4', 'mkv']
        assert args.min_size == 50.0
        assert args.max_size == 2000.0
        assert args.show_stats is False


# ============================================================================
# Tests: validate_arguments
# ============================================================================


class TestValidateArguments:
    """Tests for validate_arguments function."""

    def test_validate_valid_directory(self, tmp_path, mock_console):
        """Test validation with valid directory."""
        args = argparse.Namespace(
            directory=str(tmp_path),
            min_size=None,
            max_size=None,
            formats=None,
        )
        assert validate_arguments(args, mock_console) is True
        mock_console.print.assert_not_called()

    def test_validate_nonexistent_directory(self, mock_console):
        """Test validation with nonexistent directory."""
        args = argparse.Namespace(
            directory="/nonexistent/path",
            min_size=None,
            max_size=None,
            formats=None,
        )
        assert validate_arguments(args, mock_console) is False
        # Should print error message
        assert mock_console.print.call_count >= 1
        error_msg = str(mock_console.print.call_args_list[0])
        assert "does not exist" in error_msg

    def test_validate_file_instead_of_directory(self, tmp_path, mock_console):
        """Test validation with file path instead of directory."""
        # Create a file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        args = argparse.Namespace(
            directory=str(test_file),
            min_size=None,
            max_size=None,
            formats=None,
        )
        assert validate_arguments(args, mock_console) is False
        error_msg = str(mock_console.print.call_args_list[0])
        assert "Not a directory" in error_msg

    def test_validate_negative_min_size(self, tmp_path, mock_console):
        """Test validation with negative min_size."""
        args = argparse.Namespace(
            directory=str(tmp_path),
            min_size=-100,
            max_size=None,
            formats=None,
        )
        assert validate_arguments(args, mock_console) is False
        error_msg = str(mock_console.print.call_args_list[0])
        assert "cannot be negative" in error_msg

    def test_validate_negative_max_size(self, tmp_path, mock_console):
        """Test validation with negative max_size."""
        args = argparse.Namespace(
            directory=str(tmp_path),
            min_size=None,
            max_size=-500,
            formats=None,
        )
        assert validate_arguments(args, mock_console) is False
        error_msg = str(mock_console.print.call_args_list[0])
        assert "cannot be negative" in error_msg

    def test_validate_min_greater_than_max(self, tmp_path, mock_console):
        """Test validation with min_size > max_size."""
        args = argparse.Namespace(
            directory=str(tmp_path),
            min_size=1000,
            max_size=500,
            formats=None,
        )
        assert validate_arguments(args, mock_console) is False
        error_msg = str(mock_console.print.call_args_list[0])
        assert "cannot be greater than" in error_msg

    def test_validate_valid_formats(self, tmp_path, mock_console):
        """Test validation with valid formats."""
        args = argparse.Namespace(
            directory=str(tmp_path),
            min_size=None,
            max_size=None,
            formats=['mp4', 'mkv', 'avi'],
        )
        assert validate_arguments(args, mock_console) is True

    def test_validate_invalid_formats(self, tmp_path, mock_console):
        """Test validation with invalid formats."""
        args = argparse.Namespace(
            directory=str(tmp_path),
            min_size=None,
            max_size=None,
            formats=['mp4', 'invalid', 'badformat'],
        )
        assert validate_arguments(args, mock_console) is False
        error_msg = str(mock_console.print.call_args_list[0])
        assert "Invalid video formats" in error_msg

    def test_validate_case_insensitive_formats(self, tmp_path, mock_console):
        """Test that format validation is case-insensitive."""
        args = argparse.Namespace(
            directory=str(tmp_path),
            min_size=None,
            max_size=None,
            formats=['MP4', 'MKV', 'AVI'],
        )
        assert validate_arguments(args, mock_console) is True


# ============================================================================
# Tests: display_results_table
# ============================================================================


class TestDisplayResultsTable:
    """Tests for display_results_table function."""

    def test_display_basic_table(self, mock_console, sample_scan_result):
        """Test basic table display without filters."""
        mock_service = Mock()
        args = argparse.Namespace(
            formats=None,
            min_size=None,
            max_size=None,
        )

        display_results_table(mock_console, mock_service, sample_scan_result, args)

        # Console should print a table
        assert mock_console.print.called
        # Table should be created with correct title
        table_arg = mock_console.print.call_args[0][0]
        assert hasattr(table_arg, 'title')

    def test_display_with_format_filter(self, mock_console, sample_scan_result):
        """Test table display with format filter."""
        mock_service = Mock()
        mock_service.filter_by_format.return_value = [sample_scan_result.videos[0]]

        args = argparse.Namespace(
            formats=['mp4'],
            min_size=None,
            max_size=None,
        )

        display_results_table(mock_console, mock_service, sample_scan_result, args)

        # Service filter should be called
        assert mock_service.filter_by_format.called

    def test_display_with_size_filter(self, mock_console, sample_scan_result):
        """Test table display with size filter."""
        mock_service = Mock()
        mock_service.filter_by_size.return_value = sample_scan_result.videos

        args = argparse.Namespace(
            formats=None,
            min_size=50,
            max_size=300,
        )

        display_results_table(mock_console, mock_service, sample_scan_result, args)

        # Service filter should be called with correct args
        mock_service.filter_by_size.assert_called_once_with(sample_scan_result, 50, 300)

    def test_display_with_many_videos_shows_limit_message(self, mock_console):
        """Test that display shows 'and X more' when > 20 videos."""
        # Create 25 videos
        videos = []
        for i in range(25):
            videos.append(VideoFile(
                path=Path(f"/videos/movie{i}.mp4"),
                size_bytes=100 * 1024 * 1024,
                format=VideoFormat.MP4,
                created_at=datetime(2023, 1, 1),
                modified_at=datetime(2023, 1, 1),
            ))

        result = ScanResult(
            videos=videos,
            directories_scanned=1,
            total_files_checked=25,
            scan_duration_seconds=1.0,
            timestamp=datetime(2023, 1, 1),
            root_path=Path("/videos"),
            errors=[],
        )

        mock_service = Mock()
        args = argparse.Namespace(
            formats=None,
            min_size=None,
            max_size=None,
        )

        display_results_table(mock_console, mock_service, result, args)

        # Should call print
        assert mock_console.print.called


# ============================================================================
# Tests: display_statistics
# ============================================================================


class TestDisplayStatistics:
    """Tests for display_statistics function."""

    def test_display_statistics_basic(self, mock_console, sample_scan_result):
        """Test basic statistics display."""
        mock_service = Mock()
        mock_service.get_statistics.return_value = {
            'total_videos': 3,
            'total_size_mb': 450.0,
            'total_size_gb': 0.44,
            'directories_scanned': 2,
            'files_checked': 10,
            'scan_duration_seconds': 5.5,
            'errors': 0,
            'format_counts': {'mp4': 1, 'mkv': 1, 'avi': 1},
        }

        display_statistics(mock_console, mock_service, sample_scan_result)

        # Should call get_statistics
        mock_service.get_statistics.assert_called_once_with(sample_scan_result)

        # Should print a panel
        assert mock_console.print.called
        panel_arg = mock_console.print.call_args[0][0]
        assert hasattr(panel_arg, 'renderable')  # It's a Panel

    def test_display_statistics_with_errors(self, mock_console):
        """Test statistics display with errors."""
        result = ScanResult(
            videos=[],
            directories_scanned=1,
            total_files_checked=5,
            scan_duration_seconds=2.0,
            timestamp=datetime(2023, 1, 1),
            root_path=Path("/videos"),
            errors=["Error 1", "Error 2"],
        )

        mock_service = Mock()
        mock_service.get_statistics.return_value = {
            'total_videos': 0,
            'total_size_mb': 0.0,
            'total_size_gb': 0.0,
            'directories_scanned': 1,
            'files_checked': 5,
            'scan_duration_seconds': 2.0,
            'errors': 2,
            'format_counts': {},
        }

        display_statistics(mock_console, mock_service, result)

        assert mock_console.print.called


# ============================================================================
# Tests: run_scan_command
# ============================================================================


class TestRunScanCommand:
    """Tests for run_scan_command function."""

    @patch('duplicateflow.cli.commands.scan_command.Console')
    @patch('duplicateflow.cli.commands.scan_command.ScanService')
    @patch('duplicateflow.cli.commands.scan_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.scan_command.RichUIAdapter')
    def test_run_scan_success(
        self,
        mock_ui_adapter,
        mock_progress,
        mock_service_class,
        mock_console_class,
        tmp_path,
        sample_scan_result,
    ):
        """Test successful scan command execution."""
        # Setup mocks
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        mock_ui_instance = Mock()
        mock_ui_adapter.return_value = mock_ui_instance

        mock_service = Mock()
        mock_service.scan_directory.return_value = sample_scan_result
        mock_service.get_statistics.return_value = {
            'total_videos': 3,
            'total_size_mb': 450.0,
            'total_size_gb': 0.44,
            'directories_scanned': 2,
            'files_checked': 10,
            'scan_duration_seconds': 5.5,
            'errors': 0,
            'format_counts': {'mp4': 1, 'mkv': 1, 'avi': 1},
        }
        mock_service_class.return_value = mock_service

        # Create args
        args = argparse.Namespace(
            directory=str(tmp_path),
            recursive=True,
            follow_symlinks=False,
            formats=None,
            min_size=None,
            max_size=None,
            show_stats=True,
            output_json=None,
            output_csv=None,
        )

        # Run command
        exit_code = run_scan_command(args)

        # Assertions
        assert exit_code == 0
        mock_service.scan_directory.assert_called_once()
        assert mock_console.print.called  # Should print results

    @patch('duplicateflow.cli.commands.scan_command.Console')
    def test_run_scan_invalid_directory(self, mock_console_class):
        """Test scan command with invalid directory."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        args = argparse.Namespace(
            directory="/nonexistent/path",
            recursive=True,
            follow_symlinks=False,
            formats=None,
            min_size=None,
            max_size=None,
            show_stats=True,
            output_json=None,
            output_csv=None,
        )

        exit_code = run_scan_command(args)

        # Should return error exit code
        assert exit_code == 1

    @patch('duplicateflow.cli.commands.scan_command.Console')
    @patch('duplicateflow.cli.commands.scan_command.ScanService')
    @patch('duplicateflow.cli.commands.scan_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.scan_command.RichUIAdapter')
    def test_run_scan_keyboard_interrupt(
        self,
        mock_ui_adapter,
        mock_progress,
        mock_service_class,
        mock_console_class,
        tmp_path,
    ):
        """Test scan command handles KeyboardInterrupt."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        mock_service = Mock()
        mock_service.scan_directory.side_effect = KeyboardInterrupt()
        mock_service_class.return_value = mock_service

        args = argparse.Namespace(
            directory=str(tmp_path),
            recursive=True,
            follow_symlinks=False,
            formats=None,
            min_size=None,
            max_size=None,
            show_stats=True,
            output_json=None,
            output_csv=None,
        )

        exit_code = run_scan_command(args)

        # Should return SIGINT exit code
        assert exit_code == 130

    @patch('duplicateflow.cli.commands.scan_command.Console')
    @patch('duplicateflow.cli.commands.scan_command.ScanService')
    @patch('duplicateflow.cli.commands.scan_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.scan_command.RichUIAdapter')
    def test_run_scan_exception(
        self,
        mock_ui_adapter,
        mock_progress,
        mock_service_class,
        mock_console_class,
        tmp_path,
    ):
        """Test scan command handles exceptions."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        mock_service = Mock()
        mock_service.scan_directory.side_effect = RuntimeError("Test error")
        mock_service_class.return_value = mock_service

        args = argparse.Namespace(
            directory=str(tmp_path),
            recursive=True,
            follow_symlinks=False,
            formats=None,
            min_size=None,
            max_size=None,
            show_stats=True,
            output_json=None,
            output_csv=None,
        )

        exit_code = run_scan_command(args)

        # Should return error exit code
        assert exit_code == 1

    @patch('duplicateflow.cli.commands.scan_command.Console')
    @patch('duplicateflow.cli.commands.scan_command.ScanService')
    @patch('duplicateflow.cli.commands.scan_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.scan_command.RichUIAdapter')
    def test_run_scan_with_errors_in_result(
        self,
        mock_ui_adapter,
        mock_progress,
        mock_service_class,
        mock_console_class,
        tmp_path,
    ):
        """Test scan command displays errors from scan result."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        # Create result with errors
        result_with_errors = ScanResult(
            videos=[],
            directories_scanned=1,
            total_files_checked=5,
            scan_duration_seconds=1.0,
            timestamp=datetime(2023, 1, 1),
            root_path=Path("/videos"),
            errors=["Error 1", "Error 2", "Error 3"],
        )

        mock_service = Mock()
        mock_service.scan_directory.return_value = result_with_errors
        mock_service.get_statistics.return_value = {
            'total_videos': 0,
            'total_size_mb': 0.0,
            'total_size_gb': 0.0,
            'directories_scanned': 1,
            'files_checked': 5,
            'scan_duration_seconds': 1.0,
            'errors': 3,
            'format_counts': {},
        }
        mock_service_class.return_value = mock_service

        args = argparse.Namespace(
            directory=str(tmp_path),
            recursive=True,
            follow_symlinks=False,
            formats=None,
            min_size=None,
            max_size=None,
            show_stats=True,
            output_json=None,
            output_csv=None,
        )

        exit_code = run_scan_command(args)

        # Should still succeed but print warnings
        assert exit_code == 0
        # Should print error warning
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        warning_found = any("Warning" in str(call) or "errors occurred" in str(call)
                          for call in print_calls)
        assert warning_found

    @patch('duplicateflow.cli.commands.scan_command.Console')
    @patch('duplicateflow.cli.commands.scan_command.ScanService')
    @patch('duplicateflow.cli.commands.scan_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.scan_command.RichUIAdapter')
    def test_run_scan_no_stats(
        self,
        mock_ui_adapter,
        mock_progress,
        mock_service_class,
        mock_console_class,
        tmp_path,
        sample_scan_result,
    ):
        """Test scan command with --no-stats option."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        mock_service = Mock()
        mock_service.scan_directory.return_value = sample_scan_result
        mock_service_class.return_value = mock_service

        args = argparse.Namespace(
            directory=str(tmp_path),
            recursive=True,
            follow_symlinks=False,
            formats=None,
            min_size=None,
            max_size=None,
            show_stats=False,  # No stats
            output_json=None,
            output_csv=None,
        )

        exit_code = run_scan_command(args)

        assert exit_code == 0
        # get_statistics should NOT be called
        mock_service.get_statistics.assert_not_called()
