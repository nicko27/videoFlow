"""
Unit tests for PipelineManagementService.

Tests the pipeline configuration management service that provides
CRUD operations for custom pipelines.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from duplicateflow.core.services import PipelineManagementService
from duplicateflow.core.models import PipelineConfig, AlgorithmConfig
from duplicateflow.core.interfaces import NullProgressReporter, NullUIAdapter


class TestPipelineManagementServiceInstantiation:
    """Test service instantiation."""

    def test_init_default_directory(self):
        """Test initialization with default pipelines directory."""
        service = PipelineManagementService(
            NullProgressReporter(),
            NullUIAdapter()
        )
        assert service.pipelines_dir == PipelineManagementService.DEFAULT_PIPELINES_DIR
        assert service.pipelines_dir.exists()

    def test_init_custom_directory(self, tmp_path):
        """Test initialization with custom pipelines directory."""
        custom_dir = tmp_path / "custom_pipelines"
        service = PipelineManagementService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipelines_dir=custom_dir
        )
        assert service.pipelines_dir == custom_dir
        assert custom_dir.exists()

    def test_dependency_injection(self, tmp_path):
        """Test that progress and ui adapters are properly injected."""
        progress = NullProgressReporter()
        ui = NullUIAdapter()

        service = PipelineManagementService(
            progress,
            ui,
            pipelines_dir=tmp_path / "pipelines"
        )

        assert service.progress is progress
        assert service.ui is ui


@patch('duplicateflow.core.services.pipeline_management_service.get_algorithm_names',
       return_value=['frame_hash', 'ssim', 'optical_flow', 'color_histogram'])
class TestPipelineManagementServiceCreatePipeline:
    """Test create_pipeline method."""

    @pytest.fixture
    def service(self, tmp_path):
        """Service with temporary pipeline directory."""
        return PipelineManagementService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipelines_dir=tmp_path / "pipelines"
        )

    def test_create_pipeline_success(self, mock_get_names, service):
        """Test creating a valid pipeline."""
        algorithms = [
            AlgorithmConfig("frame_hash", weight=0.6, threshold=70.0),
            AlgorithmConfig("ssim", weight=0.4, threshold=75.0)
        ]

        config = service.create_pipeline(
            name="test_pipeline",
            description="Test pipeline",
            algorithms=algorithms,
            global_threshold=72.0
        )

        assert config.name == "test_pipeline"
        assert config.description == "Test pipeline"
        assert len(config.algorithms) == 2
        assert config.global_threshold == 72.0

    def test_create_pipeline_auto_normalize(self, mock_get_names, service):
        """Test auto-normalization of weights."""
        algorithms = [
            AlgorithmConfig("frame_hash", weight=0.3, threshold=70.0),
            AlgorithmConfig("ssim", weight=0.2, threshold=75.0)
        ]

        config = service.create_pipeline(
            name="test",
            description="Test",
            algorithms=algorithms,
            auto_normalize=True
        )

        # Weights should be normalized to sum to 1.0
        total_weight = sum(algo.weight for algo in config.algorithms)
        assert total_weight == pytest.approx(1.0, abs=0.01)

    def test_create_pipeline_no_normalize(self, mock_get_names, service):
        """Test creating pipeline without auto-normalization."""
        algorithms = [
            AlgorithmConfig("frame_hash", weight=0.3, threshold=70.0),
            AlgorithmConfig("ssim", weight=0.2, threshold=75.0)
        ]

        config = service.create_pipeline(
            name="test",
            description="Test",
            algorithms=algorithms,
            auto_normalize=False
        )

        # Weights should remain unnormalized
        total_weight = sum(algo.weight for algo in config.algorithms)
        assert total_weight == pytest.approx(0.5, abs=0.01)

    def test_create_pipeline_invalid_algorithm(self, mock_get_names, service):
        """Test creating pipeline with non-existent algorithm."""
        algorithms = [
            AlgorithmConfig("nonexistent_algo", weight=1.0, threshold=70.0)
        ]

        with pytest.raises(ValueError, match="not found in registry"):
            service.create_pipeline(
                name="test",
                description="Test",
                algorithms=algorithms
            )

    def test_create_pipeline_empty_name(self, mock_get_names, service):
        """Test creating pipeline with empty name fails."""
        algorithms = [AlgorithmConfig("frame_hash", weight=1.0)]

        with pytest.raises(ValueError, match="Pipeline name cannot be empty"):
            service.create_pipeline(
                name="",
                description="Test",
                algorithms=algorithms
            )

    def test_create_pipeline_ui_messages(self, mock_get_names, tmp_path):
        """Test UI messages during pipeline creation."""
        ui = NullUIAdapter()
        service = PipelineManagementService(
            NullProgressReporter(),
            ui,
            pipelines_dir=tmp_path / "pipelines"
        )

        algorithms = [AlgorithmConfig("frame_hash", weight=1.0)]
        service.create_pipeline(
            name="test",
            description="Test",
            algorithms=algorithms
        )

        # Verify messages were sent
        assert len(ui.messages) > 0
        messages_text = [m['message'] for m in ui.messages]
        assert any("Creating pipeline" in msg for msg in messages_text)
        assert any("Pipeline created successfully" in msg for msg in messages_text)


class TestPipelineManagementServiceSavePipeline:
    """Test save_pipeline method."""

    @pytest.fixture
    def service(self, tmp_path):
        return PipelineManagementService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipelines_dir=tmp_path / "pipelines"
        )

    @pytest.fixture
    def sample_config(self):
        return PipelineConfig(
            name="sample",
            description="Sample pipeline",
            algorithms=[
                AlgorithmConfig("frame_hash", weight=1.0, threshold=70.0)
            ]
        )

    def test_save_pipeline_yaml(self, service, sample_config):
        """Test saving pipeline as YAML."""
        path = service.save_pipeline(sample_config, format='yaml')

        assert path.exists()
        assert path.suffix == '.yaml'
        assert path.name == 'sample.yaml'

    def test_save_pipeline_json(self, service, sample_config):
        """Test saving pipeline as JSON."""
        path = service.save_pipeline(sample_config, format='json')

        assert path.exists()
        assert path.suffix == '.json'
        assert path.name == 'sample.json'

    def test_save_pipeline_overwrite_false(self, service, sample_config):
        """Test saving fails when file exists and overwrite=False."""
        # Save once
        service.save_pipeline(sample_config, format='yaml')

        # Try to save again without overwrite
        with pytest.raises(FileExistsError):
            service.save_pipeline(sample_config, format='yaml', overwrite=False)

    def test_save_pipeline_overwrite_true(self, service, sample_config):
        """Test overwriting existing pipeline."""
        # Save once
        path1 = service.save_pipeline(sample_config, format='yaml')

        # Save again with overwrite
        path2 = service.save_pipeline(sample_config, format='yaml', overwrite=True)

        assert path1 == path2
        assert path2.exists()

    def test_save_pipeline_ui_messages(self, tmp_path):
        """Test UI messages during save."""
        ui = NullUIAdapter()
        service = PipelineManagementService(
            NullProgressReporter(),
            ui,
            pipelines_dir=tmp_path / "pipelines"
        )

        config = PipelineConfig(
            name="test",
            description="Test",
            algorithms=[AlgorithmConfig("frame_hash", weight=1.0)]
        )

        service.save_pipeline(config, format='yaml')

        # Verify messages were sent
        assert len(ui.messages) > 0
        messages_text = [m['message'] for m in ui.messages]
        assert any("Saving pipeline" in msg for msg in messages_text)
        assert any("Pipeline saved" in msg for msg in messages_text)


class TestPipelineManagementServiceLoadPipeline:
    """Test load_pipeline method."""

    @pytest.fixture
    def service_with_saved_pipeline(self, tmp_path):
        service = PipelineManagementService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipelines_dir=tmp_path / "pipelines"
        )

        # Save a sample pipeline
        config = PipelineConfig(
            name="sample",
            description="Sample",
            algorithms=[AlgorithmConfig("frame_hash", weight=1.0)]
        )
        service.save_pipeline(config, format='yaml')

        return service

    def test_load_pipeline_yaml(self, service_with_saved_pipeline):
        """Test loading pipeline from YAML."""
        config = service_with_saved_pipeline.load_pipeline("sample")

        assert config.name == "sample"
        assert config.description == "Sample"
        assert len(config.algorithms) == 1

    def test_load_pipeline_json(self, tmp_path):
        """Test loading pipeline from JSON."""
        service = PipelineManagementService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipelines_dir=tmp_path / "pipelines"
        )

        # Save as JSON
        config = PipelineConfig(
            name="json_test",
            description="JSON test",
            algorithms=[AlgorithmConfig("frame_hash", weight=1.0)]
        )
        service.save_pipeline(config, format='json')

        # Load it back
        loaded = service.load_pipeline("json_test")
        assert loaded.name == "json_test"

    def test_load_pipeline_not_found(self, service_with_saved_pipeline):
        """Test loading non-existent pipeline."""
        with pytest.raises(FileNotFoundError, match="Pipeline not found"):
            service_with_saved_pipeline.load_pipeline("nonexistent")

    def test_load_pipeline_ui_messages(self, tmp_path):
        """Test UI messages during load."""
        ui = NullUIAdapter()
        service = PipelineManagementService(
            NullProgressReporter(),
            ui,
            pipelines_dir=tmp_path / "pipelines"
        )

        # Save a pipeline
        config = PipelineConfig(
            name="test",
            description="Test",
            algorithms=[AlgorithmConfig("frame_hash", weight=1.0)]
        )
        service.save_pipeline(config, format='yaml')

        # Clear messages
        ui.messages.clear()

        # Load it
        service.load_pipeline("test")

        # Verify messages
        assert len(ui.messages) > 0
        messages_text = [m['message'] for m in ui.messages]
        assert any("Loading pipeline" in msg for msg in messages_text)


class TestPipelineManagementServiceListPipelines:
    """Test list_pipelines method."""

    @pytest.fixture
    def service_with_multiple_pipelines(self, tmp_path):
        service = PipelineManagementService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipelines_dir=tmp_path / "pipelines"
        )

        # Create 3 pipelines
        for i in range(3):
            config = PipelineConfig(
                name=f"pipeline{i}",
                description=f"Pipeline {i}",
                algorithms=[AlgorithmConfig("frame_hash", weight=1.0)]
            )
            service.save_pipeline(config, format='yaml')

        return service

    def test_list_pipelines(self, service_with_multiple_pipelines):
        """Test listing all pipelines."""
        pipelines = service_with_multiple_pipelines.list_pipelines()

        assert len(pipelines) == 3
        assert all('name' in p for p in pipelines)
        assert all('description' in p for p in pipelines)
        assert all('algorithms_count' in p for p in pipelines)

    def test_list_pipelines_empty(self, tmp_path):
        """Test listing when no pipelines exist."""
        service = PipelineManagementService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipelines_dir=tmp_path / "pipelines"
        )

        pipelines = service.list_pipelines()
        assert len(pipelines) == 0

    def test_list_pipelines_mixed_formats(self, tmp_path):
        """Test listing pipelines in different formats."""
        service = PipelineManagementService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipelines_dir=tmp_path / "pipelines"
        )

        # Create YAML pipeline
        config1 = PipelineConfig(
            name="yaml_pipeline",
            description="YAML",
            algorithms=[AlgorithmConfig("frame_hash", weight=1.0)]
        )
        service.save_pipeline(config1, format='yaml')

        # Create JSON pipeline
        config2 = PipelineConfig(
            name="json_pipeline",
            description="JSON",
            algorithms=[AlgorithmConfig("ssim", weight=1.0)]
        )
        service.save_pipeline(config2, format='json')

        pipelines = service.list_pipelines()
        assert len(pipelines) == 2

        # Check formats
        formats = {p['name']: p['format'] for p in pipelines}
        assert formats['yaml_pipeline'] == 'yaml'
        assert formats['json_pipeline'] == 'json'


class TestPipelineManagementServiceDeletePipeline:
    """Test delete_pipeline method."""

    @pytest.fixture
    def service_with_pipeline(self, tmp_path):
        service = PipelineManagementService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipelines_dir=tmp_path / "pipelines"
        )

        config = PipelineConfig(
            name="to_delete",
            description="Will be deleted",
            algorithms=[AlgorithmConfig("frame_hash", weight=1.0)]
        )
        service.save_pipeline(config, format='yaml')

        return service

    def test_delete_pipeline_success(self, service_with_pipeline):
        """Test deleting existing pipeline."""
        service_with_pipeline.delete_pipeline("to_delete")

        # Verify file is gone
        with pytest.raises(FileNotFoundError):
            service_with_pipeline.load_pipeline("to_delete")

    def test_delete_pipeline_not_found(self, service_with_pipeline):
        """Test deleting non-existent pipeline."""
        with pytest.raises(FileNotFoundError, match="Pipeline not found"):
            service_with_pipeline.delete_pipeline("nonexistent")

    def test_delete_pipeline_ui_messages(self, tmp_path):
        """Test UI messages during delete."""
        ui = NullUIAdapter()
        service = PipelineManagementService(
            NullProgressReporter(),
            ui,
            pipelines_dir=tmp_path / "pipelines"
        )

        # Create and save a pipeline
        config = PipelineConfig(
            name="test",
            description="Test",
            algorithms=[AlgorithmConfig("frame_hash", weight=1.0)]
        )
        service.save_pipeline(config, format='yaml')

        # Clear messages
        ui.messages.clear()

        # Delete it
        service.delete_pipeline("test")

        # Verify messages
        assert len(ui.messages) > 0
        messages_text = [m['message'] for m in ui.messages]
        assert any("Deleting pipeline" in msg for msg in messages_text)
        assert any("Pipeline deleted" in msg for msg in messages_text)


class TestPipelineManagementServiceValidation:
    """Test validation methods."""

    @pytest.fixture
    def service(self, tmp_path):
        return PipelineManagementService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipelines_dir=tmp_path / "pipelines"
        )

    @patch('duplicateflow.core.services.pipeline_management_service.get_algorithm_names')
    def test_validate_pipeline_valid(self, mock_get_names, service):
        """Test validating a valid pipeline."""
        # Mock registry to have frame_hash available
        mock_get_names.return_value = ['frame_hash', 'ssim', 'optical_flow']

        config = PipelineConfig(
            name="valid",
            description="Valid pipeline",
            algorithms=[AlgorithmConfig("frame_hash", weight=1.0)]
        )

        errors = service.validate_pipeline(config)
        assert len(errors) == 0

    @patch('duplicateflow.core.services.pipeline_management_service.get_algorithm_names')
    def test_validate_algorithms_all_valid(self, mock_get_names, service):
        """Test validating algorithms when all exist in registry."""
        # Mock registry to have both algorithms available
        mock_get_names.return_value = ['frame_hash', 'ssim', 'optical_flow']

        config = PipelineConfig(
            name="test",
            description="Test",
            algorithms=[
                AlgorithmConfig("frame_hash", weight=0.5),
                AlgorithmConfig("ssim", weight=0.5)
            ]
        )

        errors = service.validate_algorithms(config)
        assert len(errors) == 0

    @patch('duplicateflow.core.services.pipeline_management_service.get_algorithm_names')
    def test_validate_algorithms_invalid(self, mock_get_names, service):
        """Test validating algorithms with non-existent algorithm."""
        # Mock registry without the 'nonexistent' algorithm
        mock_get_names.return_value = ['frame_hash', 'ssim', 'optical_flow']

        config = PipelineConfig(
            name="test",
            description="Test",
            algorithms=[AlgorithmConfig("nonexistent", weight=1.0)]
        )

        errors = service.validate_algorithms(config)
        assert len(errors) > 0
        assert any("not found in registry" in e for e in errors)

    @patch('duplicateflow.core.services.pipeline_management_service.get_algorithm_names')
    def test_validate_pipeline_unnormalized_weights(self, mock_get_names, service):
        """Test validation detects unnormalized weights."""
        # Mock registry to have algorithms available
        mock_get_names.return_value = ['frame_hash', 'ssim', 'optical_flow']

        config = PipelineConfig(
            name="test",
            description="Test",
            algorithms=[
                AlgorithmConfig("frame_hash", weight=0.3),
                AlgorithmConfig("ssim", weight=0.2)
            ]
        )

        errors = service.validate_pipeline(config)
        # Should have error about unnormalized weights
        assert any('Total weight' in e or 'normalize_weights' in e for e in errors)


class TestPipelineManagementServiceImportExport:
    """Test import and export methods."""

    @pytest.fixture
    def service(self, tmp_path):
        return PipelineManagementService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipelines_dir=tmp_path / "pipelines"
        )

    def test_export_pipeline(self, service, tmp_path):
        """Test exporting pipeline to external location."""
        # Create and save a pipeline
        config = PipelineConfig(
            name="export_test",
            description="Export test",
            algorithms=[AlgorithmConfig("frame_hash", weight=1.0)]
        )
        service.save_pipeline(config, format='yaml')

        # Export to external location
        export_path = tmp_path / "exported.yaml"
        result_path = service.export_pipeline("export_test", export_path, format='yaml')

        assert result_path == export_path
        assert export_path.exists()

    def test_import_pipeline(self, service, tmp_path):
        """Test importing pipeline from external file."""
        # Create external pipeline file
        config = PipelineConfig(
            name="external",
            description="External pipeline",
            algorithms=[AlgorithmConfig("frame_hash", weight=1.0)]
        )
        external_path = tmp_path / "external.yaml"
        config.save(external_path, format='yaml')

        # Import it
        imported = service.import_pipeline(external_path)

        assert imported.name == "external"

        # Verify it's now in pipelines directory
        loaded = service.load_pipeline("external")
        assert loaded.name == "external"

    def test_import_pipeline_rename(self, service, tmp_path):
        """Test importing pipeline with new name."""
        config = PipelineConfig(
            name="original",
            description="Original",
            algorithms=[AlgorithmConfig("frame_hash", weight=1.0)]
        )
        external_path = tmp_path / "original.yaml"
        config.save(external_path, format='yaml')

        # Import with new name
        imported = service.import_pipeline(external_path, new_name="renamed")

        assert imported.name == "renamed"
        loaded = service.load_pipeline("renamed")
        assert loaded.name == "renamed"

    def test_import_pipeline_invalid(self, service, tmp_path):
        """Test importing invalid pipeline."""
        # Create pipeline with invalid algorithm
        config = PipelineConfig(
            name="invalid",
            description="Invalid",
            algorithms=[AlgorithmConfig("nonexistent_algo", weight=1.0)]
        )
        external_path = tmp_path / "invalid.yaml"
        config.save(external_path, format='yaml')

        # Import should fail validation
        with pytest.raises(ValueError, match="not found in registry"):
            service.import_pipeline(external_path)


class TestPipelineManagementServiceGetInfo:
    """Test get_pipeline_info method."""

    def test_get_pipeline_info(self, tmp_path):
        """Test getting detailed pipeline information."""
        service = PipelineManagementService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipelines_dir=tmp_path / "pipelines"
        )

        config = PipelineConfig(
            name="info_test",
            description="Info test",
            algorithms=[
                AlgorithmConfig("frame_hash", weight=0.6, threshold=70.0),
                AlgorithmConfig("ssim", weight=0.4, threshold=75.0)
            ]
        )
        service.save_pipeline(config, format='yaml')

        info = service.get_pipeline_info("info_test")

        assert info['name'] == "info_test"
        assert info['algorithms_total'] == 2
        assert info['algorithms_enabled'] == 2
        assert 'validation_errors' in info
        assert 'global_threshold' in info
        assert 'total_weight' in info

    def test_get_pipeline_info_with_disabled_algorithms(self, tmp_path):
        """Test get_pipeline_info with some disabled algorithms."""
        service = PipelineManagementService(
            NullProgressReporter(),
            NullUIAdapter(),
            pipelines_dir=tmp_path / "pipelines"
        )

        config = PipelineConfig(
            name="mixed_test",
            description="Mixed enabled/disabled",
            algorithms=[
                AlgorithmConfig("frame_hash", weight=0.5, enabled=True),
                AlgorithmConfig("ssim", weight=0.3, enabled=False),
                AlgorithmConfig("optical_flow", weight=0.2, enabled=True)
            ]
        )
        service.save_pipeline(config, format='yaml')

        info = service.get_pipeline_info("mixed_test")

        assert info['algorithms_total'] == 3
        assert info['algorithms_enabled'] == 2  # Only 2 enabled
