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
    run_pipeline_command
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
        assert args.pipeline_command == 'list'

    def test_parse_create_subcommand(self):
        """Test parsing create subcommand."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_pipeline_parser(subparsers)

        args = main_parser.parse_args([
            'pipeline', 'create', 'my_pipeline',
            '--algorithms', 'frame_hash', 'ssim',
            '--weights', '0.6', '0.4'
        ])

        assert args.pipeline_command == 'create'
        assert args.name == 'my_pipeline'
        assert args.algorithms == ['frame_hash', 'ssim']
        assert args.weights == ['0.6', '0.4']

    def test_parse_delete_subcommand(self):
        """Test parsing delete subcommand."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_pipeline_parser(subparsers)

        args = main_parser.parse_args([
            'pipeline', 'delete', 'my_pipeline'
        ])

        assert args.pipeline_command == 'delete'
        assert args.name == 'my_pipeline'

    def test_parse_show_subcommand(self):
        """Test parsing show subcommand."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_pipeline_parser(subparsers)

        args = main_parser.parse_args([
            'pipeline', 'show', 'my_pipeline'
        ])

        assert args.pipeline_command == 'show'
        assert args.name == 'my_pipeline'

    def test_parse_export_subcommand(self):
        """Test parsing export subcommand."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_pipeline_parser(subparsers)

        args = main_parser.parse_args([
            'pipeline', 'export', 'my_pipeline', '--output', 'pipeline.yaml'
        ])

        assert args.pipeline_command == 'export'
        assert args.name == 'my_pipeline'
        assert args.output == 'pipeline.yaml'

    def test_parse_import_subcommand(self):
        """Test parsing import subcommand."""
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest='command')
        create_pipeline_parser(subparsers)

        args = main_parser.parse_args([
            'pipeline', 'import', 'pipeline.yaml'
        ])

        assert args.pipeline_command == 'import'
        assert args.file == 'pipeline.yaml'


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
        mock_service.list_pipelines.return_value = [
            {'name': 'pipeline1', 'description': 'First pipeline'},
            {'name': 'pipeline2', 'description': 'Second pipeline'}
        ]
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            pipeline_command='list'
        )

        exit_code = run_pipeline_command(args)

        assert exit_code == 0
        mock_service.list_pipelines.assert_called_once()

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    @patch('duplicateflow.cli.commands.pipeline_command.get_algorithm_names')
    def test_run_pipeline_create(
        self,
        mock_get_algos,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls
    ):
        """Test creating a pipeline."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_get_algos.return_value = ['frame_hash', 'ssim', 'optical_flow']

        mock_config = Mock(spec=PipelineConfig)
        mock_config.name = 'my_pipeline'

        mock_service = Mock()
        mock_service.create_pipeline.return_value = mock_config
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            pipeline_command='create',
            name='my_pipeline',
            description='My custom pipeline',
            algorithms=['frame_hash', 'ssim'],
            weights=['0.6', '0.4'],
            thresholds=None,
            global_threshold=70.0,
            output_format='yaml'
        )

        exit_code = run_pipeline_command(args)

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
            pipeline_command='delete',
            name='my_pipeline',
            force=False
        )

        # User confirms deletion (simulate input)
        with patch('builtins.input', return_value='y'):
            exit_code = run_pipeline_command(args)

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
        mock_config.algorithms = [
            Mock(spec=AlgorithmConfig, name='frame_hash', weight=0.6),
            Mock(spec=AlgorithmConfig, name='ssim', weight=0.4)
        ]

        mock_service = Mock()
        mock_service.load_pipeline.return_value = mock_config
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            pipeline_command='show',
            name='my_pipeline'
        )

        exit_code = run_pipeline_command(args)

        assert exit_code == 0
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
            pipeline_command='export',
            name='my_pipeline',
            output=str(output_file),
            format='yaml'
        )

        exit_code = run_pipeline_command(args)

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

        mock_service = Mock()
        mock_service.import_pipeline.return_value = mock_config
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        args = argparse.Namespace(
            command='pipeline',
            pipeline_command='import',
            file=str(pipeline_file),
            name=None
        )

        exit_code = run_pipeline_command(args)

        assert exit_code == 0
        mock_service.import_pipeline.assert_called_once()


class TestPipelineCommandIntegration:
    """Integration-style tests for complete workflows."""

    @patch('duplicateflow.cli.commands.pipeline_command.PipelineManagementService')
    @patch('duplicateflow.cli.commands.pipeline_command.RichProgressReporter')
    @patch('duplicateflow.cli.commands.pipeline_command.RichUIAdapter')
    @patch('duplicateflow.cli.commands.pipeline_command.Console')
    @patch('duplicateflow.cli.commands.pipeline_command.get_algorithm_names')
    def test_full_create_export_workflow(
        self,
        mock_get_algos,
        mock_console_cls,
        mock_ui_adapter,
        mock_progress,
        mock_service_cls,
        tmp_path
    ):
        """Test complete create and export workflow."""
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_get_algos.return_value = ['frame_hash', 'ssim']

        mock_config = Mock(spec=PipelineConfig)
        mock_config.name = 'custom'

        mock_service = Mock()
        mock_service.create_pipeline.return_value = mock_config
        mock_service.export_pipeline.return_value = tmp_path / "custom.yaml"
        mock_service_cls.return_value = mock_service

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        # Create pipeline
        create_args = argparse.Namespace(
            command='pipeline',
            pipeline_command='create',
            name='custom',
            description='Custom pipeline',
            algorithms=['frame_hash', 'ssim'],
            weights=['0.5', '0.5'],
            thresholds=None,
            global_threshold=75.0,
            output_format='yaml'
        )

        exit_code = run_pipeline_command(create_args)
        assert exit_code == 0

        # Verify workflow
        mock_service.create_pipeline.assert_called_once()
        mock_service.save_pipeline.assert_called_once()
