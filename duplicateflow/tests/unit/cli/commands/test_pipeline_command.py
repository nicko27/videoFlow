"""
Unit tests for pipeline command.

Tests the CLI command that manages custom pipeline configurations.
"""

import argparse
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from duplicateflow.cli.commands.pipeline_command import (
    create_pipeline_parser,
    run_pipeline_command,
    run_list_command,
    run_create_command,
    run_delete_command,
    run_show_command,
    run_export_command,
    run_import_command,
    run_validate_command
)
from duplicateflow.core.models import PipelineConfig, AlgorithmConfig


class TestPipelineCommandParser:
    """Test argument parser creation and parsing."""

    def test_parser_creation(self):
        """Test parser is created successfully."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers()
        parser = create_pipeline_parser(subparsers)

        assert parser is not None
        assert parser.prog.endswith('pipeline')

    def test_parse_list_subcommand(self):
        """Test parsing list subcommand."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_pipeline_parser(subparsers)

        args = main_parser.parse_args(['pipeline', 'list'])

        assert args.command == 'pipeline'
        assert args.subcommand == 'list'

    def test_parse_create_subcommand(self):
        """Test parsing create subcommand."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_pipeline_parser(subparsers)

        args = main_parser.parse_args([
            'pipeline', 'create', 'my_pipeline',
            '--description', 'My pipeline',
            '--algorithms', 'frame_hash', 'ssim',
            '--weights', '0.6', '0.4'
        ])

        assert args.subcommand == 'create'
        assert args.name == 'my_pipeline'
        assert args.description == 'My pipeline'
        assert args.algorithms == ['frame_hash', 'ssim']
        assert args.weights == [0.6, 0.4]

    def test_parse_delete_subcommand(self):
        """Test parsing delete subcommand."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_pipeline_parser(subparsers)

        args = main_parser.parse_args([
            'pipeline', 'delete', 'my_pipeline'
        ])

        assert args.subcommand == 'delete'
        assert args.name == 'my_pipeline'

    def test_parse_show_subcommand(self):
        """Test parsing show subcommand."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_pipeline_parser(subparsers)

        args = main_parser.parse_args([
            'pipeline', 'show', 'my_pipeline'
        ])

        assert args.subcommand == 'show'
        assert args.name == 'my_pipeline'

    def test_parse_export_subcommand(self):
        """Test parsing export subcommand."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_pipeline_parser(subparsers)

        args = main_parser.parse_args([
            'pipeline', 'export', 'my_pipeline', 'pipeline.yaml'
        ])

        assert args.subcommand == 'export'
        assert args.name == 'my_pipeline'
        assert args.destination == 'pipeline.yaml'

    def test_parse_import_subcommand(self):
        """Test parsing import subcommand."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_pipeline_parser(subparsers)

        args = main_parser.parse_args([
            'pipeline', 'import', 'pipeline.yaml'
        ])

        assert args.subcommand == 'import'
        assert args.source == 'pipeline.yaml'


class TestPipelineCommandExecution:
    """Test command execution logic."""

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_run_pipeline_list(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test listing pipelines."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_service = Mock()
        mock_service.pipelines_dir = Path('/tmp/pipelines')
        mock_service.list_pipelines.return_value = [
            {
                'name': 'pipeline1',
                'description': 'First pipeline',
                'algorithms_count': 2,
                'format': 'yaml',
                'created_at': '2025-01-01T00:00:00'
            },
            {
                'name': 'pipeline2',
                'description': 'Second pipeline',
                'algorithms_count': 3,
                'format': 'yaml',
                'created_at': '2025-01-01T00:00:00'
            }
        ]
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='list'
        )

        exit_code = run_list_command(args)

        assert exit_code == 0
        mock_service.list_pipelines.assert_called_once()

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_run_pipeline_create(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test creating a pipeline."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_config = Mock(spec=PipelineConfig)
        mock_config.name = 'my_pipeline'
        mock_config.algorithms = [
            Mock(name='frame_hash', weight=0.6, threshold=70.0),
            Mock(name='ssim', weight=0.4, threshold=70.0)
        ]

        mock_service = Mock()
        mock_service.create_pipeline.return_value = mock_config
        mock_service.save_pipeline.return_value = Path('/tmp/my_pipeline.yaml')
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='create',
            name='my_pipeline',
            description='My custom pipeline',
            algorithms=['frame_hash', 'ssim'],
            weights=[0.6, 0.4],
            thresholds=None,
            global_threshold=70.0,
            format='yaml',
            no_normalize=False
        )

        exit_code = run_create_command(args)

        assert exit_code == 0
        mock_service.create_pipeline.assert_called_once()
        mock_service.save_pipeline.assert_called_once()

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_run_pipeline_delete(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test deleting a pipeline."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='delete',
            name='my_pipeline',
            yes=False
        )

        # User confirms deletion (simulate input)
        with patch('builtins.input', return_value='y'):
            exit_code = run_delete_command(args)

        assert exit_code == 0
        mock_service.delete_pipeline.assert_called_once_with('my_pipeline')

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_run_pipeline_show(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test showing pipeline details."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_config = Mock(spec=PipelineConfig)
        mock_config.name = 'my_pipeline'
        mock_config.description = 'Custom pipeline'
        mock_config.to_yaml.return_value = "name: my_pipeline"
        mock_config.algorithms = [
            Mock(spec=AlgorithmConfig, name='frame_hash', weight=0.6),
            Mock(spec=AlgorithmConfig, name='ssim', weight=0.4)
        ]

        mock_info = {
            'name': 'my_pipeline',
            'description': 'Custom pipeline',
            'global_threshold': 70.0,
            'algorithms_enabled': 2,
            'algorithms_total': 2,
            'total_weight': 1.0,
            'weight_normalized': True,
            'algorithms': [
                {'name': 'frame_hash', 'weight': 0.6, 'threshold': 70.0, 'enabled': True, 'params_count': 0},
                {'name': 'ssim', 'weight': 0.4, 'threshold': 70.0, 'enabled': True, 'params_count': 0}
            ],
            'validation_errors': []
        }

        mock_service = Mock()
        mock_service.get_pipeline_info.return_value = mock_info
        mock_service.load_pipeline.return_value = mock_config
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='show',
            name='my_pipeline',
            format='yaml'
        )

        exit_code = run_show_command(args)

        assert exit_code == 0
        mock_service.get_pipeline_info.assert_called_once_with('my_pipeline')
        mock_service.load_pipeline.assert_called_once_with('my_pipeline')

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_run_pipeline_export(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls,
        tmp_path
    ):
        """Test exporting a pipeline."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        output_file = tmp_path / "pipeline.yaml"

        mock_service = Mock()
        mock_service.export_pipeline.return_value = output_file
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='export',
            name='my_pipeline',
            destination=str(output_file),
            format='yaml'
        )

        exit_code = run_export_command(args)

        assert exit_code == 0
        mock_service.export_pipeline.assert_called_once()

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_run_pipeline_import(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls,
        tmp_path
    ):
        """Test importing a pipeline."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        pipeline_file = tmp_path / "pipeline.yaml"
        pipeline_file.write_text('name: imported\nalgorithms: []')

        mock_config = Mock(spec=PipelineConfig)
        mock_config.name = 'imported'
        mock_config.get_enabled_algorithms.return_value = [Mock(), Mock()]

        mock_service = Mock()
        mock_service.import_pipeline.return_value = mock_config
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='import',
            source=str(pipeline_file),
            name=None,
            overwrite=False
        )

        exit_code = run_import_command(args)

        assert exit_code == 0
        mock_service.import_pipeline.assert_called_once()


class TestPipelineCommandIntegration:
    """Integration-style tests for complete workflows."""

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_full_create_export_workflow(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls,
        tmp_path
    ):
        """Test complete create and export workflow."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_config = Mock(spec=PipelineConfig)
        mock_config.name = 'custom'
        mock_config.algorithms = [
            Mock(name='frame_hash', weight=0.5, threshold=75.0),
            Mock(name='ssim', weight=0.5, threshold=75.0)
        ]

        mock_service = Mock()
        mock_service.create_pipeline.return_value = mock_config
        mock_service.save_pipeline.return_value = tmp_path / "custom.yaml"
        mock_service.export_pipeline.return_value = tmp_path / "custom.yaml"
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        # Create pipeline
        create_args = argparse.Namespace(
            command='pipeline',
            subcommand='create',
            name='custom',
            description='Custom pipeline',
            algorithms=['frame_hash', 'ssim'],
            weights=[0.5, 0.5],
            thresholds=None,
            global_threshold=75.0,
            format='yaml',
            no_normalize=False
        )

        exit_code = run_create_command(create_args)
        assert exit_code == 0

        # Verify workflow
        mock_service.create_pipeline.assert_called_once()
        mock_service.save_pipeline.assert_called_once()


class TestPipelineCommandValidate:
    """Test validate subcommand."""

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_validate_success(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test validating a valid pipeline."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_config = Mock(spec=PipelineConfig)
        mock_config.name = 'test_pipeline'
        mock_config.global_threshold = 70.0
        mock_config.get_enabled_algorithms.return_value = [Mock(), Mock()]
        mock_config.get_total_weight.return_value = 1.0

        mock_service = Mock()
        mock_service.load_pipeline.return_value = mock_config
        mock_service.validate_pipeline.return_value = []  # No errors
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='validate',
            name='test_pipeline'
        )

        exit_code = run_validate_command(args)

        assert exit_code == 0
        mock_service.load_pipeline.assert_called_once_with('test_pipeline')
        mock_service.validate_pipeline.assert_called_once()

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_validate_with_errors(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test validating a pipeline with errors."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_config = Mock(spec=PipelineConfig)
        mock_config.name = 'invalid_pipeline'

        mock_service = Mock()
        mock_service.load_pipeline.return_value = mock_config
        mock_service.validate_pipeline.return_value = [
            "Weight sum is not 1.0",
            "Unknown algorithm: invalid_algo"
        ]
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='validate',
            name='invalid_pipeline'
        )

        exit_code = run_validate_command(args)

        assert exit_code == 1
        mock_service.load_pipeline.assert_called_once_with('invalid_pipeline')
        mock_service.validate_pipeline.assert_called_once()

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_validate_pipeline_not_found(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test validating a non-existent pipeline."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_service = Mock()
        mock_service.load_pipeline.side_effect = FileNotFoundError("Pipeline not found")
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='validate',
            name='nonexistent'
        )

        exit_code = run_validate_command(args)

        assert exit_code == 1


class TestPipelineCommandErrors:
    """Test error handling."""

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_show_error_handling(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test exception handling in show command."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_service = Mock()
        mock_service.get_pipeline_info.side_effect = Exception("Unexpected error")
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='show',
            name='test',
            format='yaml'
        )

        exit_code = run_show_command(args)

        assert exit_code == 1

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_create_error_handling(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test exception handling in create command."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_service = Mock()
        mock_service.create_pipeline.side_effect = ValueError("Invalid algorithm")
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='create',
            name='test',
            description='Test',
            algorithms=['invalid'],
            weights=[1.0],
            thresholds=None,
            global_threshold=70.0,
            format='yaml',
            no_normalize=False
        )

        exit_code = run_create_command(args)

        assert exit_code == 1

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_create_file_exists_error(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test file exists error in create command."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_config = Mock(spec=PipelineConfig)
        mock_service = Mock()
        mock_service.create_pipeline.return_value = mock_config
        mock_service.save_pipeline.side_effect = FileExistsError("Pipeline already exists")
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='create',
            name='existing',
            description='Test',
            algorithms=['frame_hash'],
            weights=[1.0],
            thresholds=None,
            global_threshold=70.0,
            format='yaml',
            no_normalize=False
        )

        exit_code = run_create_command(args)

        assert exit_code == 1

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_create_exception_handling(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test general exception handling in create command."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_service = Mock()
        mock_service.create_pipeline.side_effect = Exception("Unexpected error")
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='create',
            name='test',
            description='Test',
            algorithms=['frame_hash'],
            weights=[1.0],
            thresholds=None,
            global_threshold=70.0,
            format='yaml',
            no_normalize=False
        )

        exit_code = run_create_command(args)

        assert exit_code == 1

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_export_error_handling(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test exception handling in export command."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_service = Mock()
        mock_service.export_pipeline.side_effect = Exception("Export failed")
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='export',
            name='test',
            destination='/tmp/test.yaml',
            format='yaml'
        )

        exit_code = run_export_command(args)

        assert exit_code == 1

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_import_error_handling(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test exception handling in import command."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_service = Mock()
        mock_service.import_pipeline.side_effect = FileNotFoundError("File not found")
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='import',
            source='/tmp/nonexistent.yaml',
            name=None,
            overwrite=False
        )

        exit_code = run_import_command(args)

        assert exit_code == 1

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_import_file_exists_error(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test file exists error in import command."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_service = Mock()
        mock_service.import_pipeline.side_effect = FileExistsError("Pipeline already exists")
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='import',
            source='/tmp/test.yaml',
            name=None,
            overwrite=False
        )

        exit_code = run_import_command(args)

        assert exit_code == 1

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_import_value_error(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test value error in import command."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_service = Mock()
        mock_service.import_pipeline.side_effect = ValueError("Invalid pipeline format")
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='import',
            source='/tmp/invalid.yaml',
            name=None,
            overwrite=False
        )

        exit_code = run_import_command(args)

        assert exit_code == 1

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_import_exception_handling(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test general exception handling in import command."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_service = Mock()
        mock_service.import_pipeline.side_effect = Exception("Unexpected error")
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='import',
            source='/tmp/test.yaml',
            name=None,
            overwrite=False
        )

        exit_code = run_import_command(args)

        assert exit_code == 1

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_validate_exception_handling(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test general exception handling in validate command."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_service = Mock()
        mock_service.load_pipeline.side_effect = Exception("Unexpected error")
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            subcommand='validate',
            name='test'
        )

        exit_code = run_validate_command(args)

        assert exit_code == 1

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    def test_delete_exception_handling(
        self,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test general exception handling in delete command."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_service = Mock()
        mock_service.delete_pipeline.side_effect = Exception("Unexpected error")
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        # Use --yes flag to skip confirmation
        args = argparse.Namespace(
            command='pipeline',
            subcommand='delete',
            name='test',
            yes=True
        )

        exit_code = run_delete_command(args)

        assert exit_code == 1
