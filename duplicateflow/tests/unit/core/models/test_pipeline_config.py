"""
Unit tests for pipeline configuration models.

Tests AlgorithmConfig and PipelineConfig classes including:
- Creation and validation
- Serialization (to_dict, from_dict, to_yaml, from_yaml, to_json, from_json)
- File I/O (save, load)
- Helper methods (get_enabled_algorithms, normalize_weights, validate)
"""

import pytest
import json
import yaml
from pathlib import Path
from datetime import datetime

from duplicateflow.core.models.pipeline_config import AlgorithmConfig, PipelineConfig


class TestAlgorithmConfig:
    """Tests for AlgorithmConfig model."""

    def test_algorithm_config_creation(self):
        """Test basic AlgorithmConfig creation."""
        config = AlgorithmConfig(
            name="frame_hash",
            weight=0.5,
            threshold=75.0,
            enabled=True,
            params={"hash_size": 16}
        )

        assert config.name == "frame_hash"
        assert config.weight == 0.5
        assert config.threshold == 75.0
        assert config.enabled is True
        assert config.params == {"hash_size": 16}

    def test_algorithm_config_defaults(self):
        """Test AlgorithmConfig with default values."""
        config = AlgorithmConfig(name="ssim")

        assert config.name == "ssim"
        assert config.weight == 1.0
        assert config.threshold == 70.0
        assert config.enabled is True
        assert config.params == {}

    def test_algorithm_config_invalid_weight(self):
        """Test AlgorithmConfig rejects invalid weight."""
        with pytest.raises(ValueError, match="Weight must be between 0.0 and 1.0"):
            AlgorithmConfig(name="test", weight=1.5)

        with pytest.raises(ValueError, match="Weight must be between 0.0 and 1.0"):
            AlgorithmConfig(name="test", weight=-0.1)

    def test_algorithm_config_invalid_threshold(self):
        """Test AlgorithmConfig rejects invalid threshold."""
        with pytest.raises(ValueError, match="Threshold must be between 0.0 and 100.0"):
            AlgorithmConfig(name="test", threshold=150.0)

        with pytest.raises(ValueError, match="Threshold must be between 0.0 and 100.0"):
            AlgorithmConfig(name="test", threshold=-10.0)

    def test_algorithm_config_empty_name(self):
        """Test AlgorithmConfig rejects empty name."""
        with pytest.raises(ValueError, match="Algorithm name cannot be empty"):
            AlgorithmConfig(name="")

    def test_algorithm_config_to_dict(self):
        """Test AlgorithmConfig serialization to dict."""
        config = AlgorithmConfig(
            name="frame_hash",
            weight=0.333,
            threshold=75.5,
            enabled=True,
            params={"hash_size": 16}
        )

        data = config.to_dict()

        assert data == {
            'name': 'frame_hash',
            'weight': 0.333,
            'threshold': 75.5,
            'enabled': True,
            'params': {'hash_size': 16}
        }

    def test_algorithm_config_from_dict(self):
        """Test AlgorithmConfig deserialization from dict."""
        data = {
            'name': 'ssim',
            'weight': 0.6,
            'threshold': 80.0,
            'enabled': False,
            'params': {'window_size': 11}
        }

        config = AlgorithmConfig.from_dict(data)

        assert config.name == 'ssim'
        assert config.weight == 0.6
        assert config.threshold == 80.0
        assert config.enabled is False
        assert config.params == {'window_size': 11}

    def test_algorithm_config_from_dict_minimal(self):
        """Test AlgorithmConfig from dict with minimal fields."""
        data = {'name': 'frame_hash'}

        config = AlgorithmConfig.from_dict(data)

        assert config.name == 'frame_hash'
        assert config.weight == 1.0
        assert config.threshold == 70.0
        assert config.enabled is True
        assert config.params == {}


class TestPipelineConfig:
    """Tests for PipelineConfig model."""

    @pytest.fixture
    def sample_algorithms(self):
        """Sample algorithm configurations for testing."""
        return [
            AlgorithmConfig("frame_hash", weight=0.4, threshold=70.0),
            AlgorithmConfig("ssim", weight=0.3, threshold=75.0),
            AlgorithmConfig("optical_flow", weight=0.3, threshold=80.0)
        ]

    @pytest.fixture
    def sample_pipeline(self, sample_algorithms):
        """Sample pipeline configuration for testing."""
        return PipelineConfig(
            name="test_preset",
            description="Test pipeline for unit tests",
            algorithms=sample_algorithms,
            global_threshold=72.0
        )

    def test_pipeline_config_creation(self, sample_algorithms):
        """Test basic PipelineConfig creation."""
        config = PipelineConfig(
            name="my_preset",
            description="Custom preset",
            algorithms=sample_algorithms,
            global_threshold=75.0,
            validators={'length': {'min_duration': 10}},
            metadata={'author': 'test_user'}
        )

        assert config.name == "my_preset"
        assert config.description == "Custom preset"
        assert len(config.algorithms) == 3
        assert config.global_threshold == 75.0
        assert config.validators == {'length': {'min_duration': 10}}
        assert 'author' in config.metadata
        assert 'created_at' in config.metadata  # Auto-added

    def test_pipeline_config_empty_name(self, sample_algorithms):
        """Test PipelineConfig rejects empty name."""
        with pytest.raises(ValueError, match="Pipeline name cannot be empty"):
            PipelineConfig(
                name="",
                description="Test",
                algorithms=sample_algorithms
            )

    def test_pipeline_config_no_algorithms(self):
        """Test PipelineConfig rejects empty algorithm list."""
        with pytest.raises(ValueError, match="Pipeline must have at least one algorithm"):
            PipelineConfig(
                name="test",
                description="Test",
                algorithms=[]
            )

    def test_pipeline_config_invalid_threshold(self, sample_algorithms):
        """Test PipelineConfig rejects invalid global threshold."""
        with pytest.raises(ValueError, match="Global threshold must be between 0.0 and 100.0"):
            PipelineConfig(
                name="test",
                description="Test",
                algorithms=sample_algorithms,
                global_threshold=150.0
            )

    def test_pipeline_config_duplicate_algorithm_names(self):
        """Test PipelineConfig rejects duplicate algorithm names."""
        algorithms = [
            AlgorithmConfig("frame_hash", weight=0.5),
            AlgorithmConfig("frame_hash", weight=0.5)  # Duplicate
        ]

        with pytest.raises(ValueError, match="Algorithm names must be unique"):
            PipelineConfig(
                name="test",
                description="Test",
                algorithms=algorithms
            )

    def test_pipeline_config_to_dict(self, sample_pipeline):
        """Test PipelineConfig serialization to dict."""
        data = sample_pipeline.to_dict()

        assert data['name'] == "test_preset"
        assert data['description'] == "Test pipeline for unit tests"
        assert data['global_threshold'] == 72.0
        assert len(data['algorithms']) == 3
        assert data['algorithms'][0]['name'] == 'frame_hash'
        assert 'created_at' in data['metadata']

    def test_pipeline_config_from_dict(self):
        """Test PipelineConfig deserialization from dict."""
        data = {
            'name': 'imported_preset',
            'description': 'Imported pipeline',
            'algorithms': [
                {'name': 'frame_hash', 'weight': 0.5, 'threshold': 70.0, 'enabled': True, 'params': {}},
                {'name': 'ssim', 'weight': 0.5, 'threshold': 75.0, 'enabled': True, 'params': {}}
            ],
            'global_threshold': 73.0,
            'validators': {},
            'metadata': {'version': '1.0'}
        }

        config = PipelineConfig.from_dict(data)

        assert config.name == 'imported_preset'
        assert config.description == 'Imported pipeline'
        assert len(config.algorithms) == 2
        assert config.global_threshold == 73.0
        assert config.algorithms[0].name == 'frame_hash'
        assert config.algorithms[1].weight == 0.5

    def test_pipeline_config_to_yaml(self, sample_pipeline):
        """Test PipelineConfig serialization to YAML."""
        yaml_str = sample_pipeline.to_yaml()

        # Parse YAML to verify structure
        data = yaml.safe_load(yaml_str)

        assert data['name'] == 'test_preset'
        assert data['description'] == 'Test pipeline for unit tests'
        assert len(data['algorithms']) == 3
        assert 'created_at' in data['metadata']

    def test_pipeline_config_from_yaml(self, sample_pipeline):
        """Test PipelineConfig deserialization from YAML."""
        yaml_str = sample_pipeline.to_yaml()
        config = PipelineConfig.from_yaml(yaml_str)

        assert config.name == sample_pipeline.name
        assert config.description == sample_pipeline.description
        assert len(config.algorithms) == len(sample_pipeline.algorithms)
        assert config.global_threshold == sample_pipeline.global_threshold

    def test_pipeline_config_from_yaml_invalid(self):
        """Test PipelineConfig rejects invalid YAML."""
        invalid_yaml = "name: test\nalgorithms: ["  # Unclosed bracket

        with pytest.raises(ValueError, match="Invalid YAML"):
            PipelineConfig.from_yaml(invalid_yaml)

    def test_pipeline_config_to_json(self, sample_pipeline):
        """Test PipelineConfig serialization to JSON."""
        json_str = sample_pipeline.to_json()

        # Parse JSON to verify structure
        data = json.loads(json_str)

        assert data['name'] == 'test_preset'
        assert data['description'] == 'Test pipeline for unit tests'
        assert len(data['algorithms']) == 3
        assert 'created_at' in data['metadata']

    def test_pipeline_config_from_json(self, sample_pipeline):
        """Test PipelineConfig deserialization from JSON."""
        json_str = sample_pipeline.to_json()
        config = PipelineConfig.from_json(json_str)

        assert config.name == sample_pipeline.name
        assert config.description == sample_pipeline.description
        assert len(config.algorithms) == len(sample_pipeline.algorithms)
        assert config.global_threshold == sample_pipeline.global_threshold

    def test_pipeline_config_from_json_invalid(self):
        """Test PipelineConfig rejects invalid JSON."""
        invalid_json = '{"name": "test", "algorithms": ['  # Unclosed bracket

        with pytest.raises(ValueError, match="Invalid JSON"):
            PipelineConfig.from_json(invalid_json)

    def test_pipeline_config_save_yaml(self, sample_pipeline, tmp_path):
        """Test saving PipelineConfig to YAML file."""
        file_path = tmp_path / "test_preset.yaml"

        sample_pipeline.save(file_path, format='yaml')

        assert file_path.exists()

        # Verify content
        content = file_path.read_text()
        assert 'name: test_preset' in content
        assert 'description:' in content

    def test_pipeline_config_save_json(self, sample_pipeline, tmp_path):
        """Test saving PipelineConfig to JSON file."""
        file_path = tmp_path / "test_preset.json"

        sample_pipeline.save(file_path, format='json')

        assert file_path.exists()

        # Verify content
        content = file_path.read_text()
        data = json.loads(content)
        assert data['name'] == 'test_preset'

    def test_pipeline_config_save_invalid_format(self, sample_pipeline, tmp_path):
        """Test save rejects unsupported format."""
        file_path = tmp_path / "test.xml"

        with pytest.raises(ValueError, match="Unsupported format"):
            sample_pipeline.save(file_path, format='xml')

    def test_pipeline_config_load_yaml(self, sample_pipeline, tmp_path):
        """Test loading PipelineConfig from YAML file."""
        file_path = tmp_path / "test_preset.yaml"
        sample_pipeline.save(file_path, format='yaml')

        loaded = PipelineConfig.load(file_path)

        assert loaded.name == sample_pipeline.name
        assert loaded.description == sample_pipeline.description
        assert len(loaded.algorithms) == len(sample_pipeline.algorithms)

    def test_pipeline_config_load_json(self, sample_pipeline, tmp_path):
        """Test loading PipelineConfig from JSON file."""
        file_path = tmp_path / "test_preset.json"
        sample_pipeline.save(file_path, format='json')

        loaded = PipelineConfig.load(file_path)

        assert loaded.name == sample_pipeline.name
        assert loaded.description == sample_pipeline.description
        assert len(loaded.algorithms) == len(sample_pipeline.algorithms)

    def test_pipeline_config_load_not_found(self, tmp_path):
        """Test load raises FileNotFoundError for missing file."""
        file_path = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            PipelineConfig.load(file_path)

    def test_pipeline_config_load_unsupported_extension(self, tmp_path):
        """Test load rejects unsupported file extension."""
        file_path = tmp_path / "test.xml"
        file_path.write_text("<xml></xml>")

        with pytest.raises(ValueError, match="Unsupported file extension"):
            PipelineConfig.load(file_path)

    def test_get_enabled_algorithms(self, sample_algorithms):
        """Test getting only enabled algorithms."""
        # Disable one algorithm
        sample_algorithms[1].enabled = False

        config = PipelineConfig(
            name="test",
            description="Test",
            algorithms=sample_algorithms
        )

        enabled = config.get_enabled_algorithms()

        assert len(enabled) == 2
        assert enabled[0].name == 'frame_hash'
        assert enabled[1].name == 'optical_flow'

    def test_get_algorithm(self, sample_pipeline):
        """Test getting algorithm by name."""
        algo = sample_pipeline.get_algorithm('ssim')

        assert algo is not None
        assert algo.name == 'ssim'
        assert algo.weight == 0.3

    def test_get_algorithm_not_found(self, sample_pipeline):
        """Test get_algorithm returns None for missing algorithm."""
        algo = sample_pipeline.get_algorithm('nonexistent')

        assert algo is None

    def test_get_total_weight(self, sample_pipeline):
        """Test calculating total weight of enabled algorithms."""
        total = sample_pipeline.get_total_weight()

        # 0.4 + 0.3 + 0.3 = 1.0
        assert total == pytest.approx(1.0, abs=0.01)

    def test_get_total_weight_with_disabled(self, sample_algorithms):
        """Test total weight excludes disabled algorithms."""
        sample_algorithms[2].enabled = False  # Disable optical_flow (0.3)

        config = PipelineConfig(
            name="test",
            description="Test",
            algorithms=sample_algorithms
        )

        total = config.get_total_weight()

        # Only frame_hash (0.4) + ssim (0.3) = 0.7
        assert total == pytest.approx(0.7, abs=0.01)

    def test_normalize_weights(self):
        """Test normalizing algorithm weights to sum to 1.0."""
        # Use weights that are valid (0-1) but not normalized
        algorithms = [
            AlgorithmConfig("algo1", weight=0.2),
            AlgorithmConfig("algo2", weight=0.3),
            AlgorithmConfig("algo3", weight=0.1)
        ]

        config = PipelineConfig(
            name="test",
            description="Test",
            algorithms=algorithms
        )

        # Total weight = 0.6
        assert config.get_total_weight() == pytest.approx(0.6)

        config.normalize_weights()

        # After normalization: 0.2/0.6, 0.3/0.6, 0.1/0.6 -> 1/3, 1/2, 1/6
        assert config.get_total_weight() == pytest.approx(1.0, abs=0.01)
        assert algorithms[0].weight == pytest.approx(0.2/0.6, abs=0.01)  # ~0.333
        assert algorithms[1].weight == pytest.approx(0.3/0.6, abs=0.01)  # ~0.5
        assert algorithms[2].weight == pytest.approx(0.1/0.6, abs=0.01)  # ~0.167

    def test_normalize_weights_with_disabled(self):
        """Test normalize_weights only affects enabled algorithms."""
        # Use weights that are valid (0-1)
        algorithms = [
            AlgorithmConfig("algo1", weight=0.2, enabled=True),
            AlgorithmConfig("algo2", weight=0.9, enabled=False),  # Disabled
            AlgorithmConfig("algo3", weight=0.5, enabled=True)
        ]

        config = PipelineConfig(
            name="test",
            description="Test",
            algorithms=algorithms
        )

        config.normalize_weights()

        # Only algo1 and algo3 normalized: 0.2/(0.2+0.5) and 0.5/(0.2+0.5)
        assert algorithms[0].weight == pytest.approx(0.2/0.7, abs=0.01)  # ~0.286
        assert algorithms[1].weight == 0.9  # Unchanged (disabled)
        assert algorithms[2].weight == pytest.approx(0.5/0.7, abs=0.01)  # ~0.714

    def test_normalize_weights_all_zero(self):
        """Test normalize_weights handles all zero weights."""
        algorithms = [
            AlgorithmConfig("algo1", weight=0.0),
            AlgorithmConfig("algo2", weight=0.0),
            AlgorithmConfig("algo3", weight=0.0)
        ]

        config = PipelineConfig(
            name="test",
            description="Test",
            algorithms=algorithms
        )

        config.normalize_weights()

        # Equal weights: 1/3 each
        for algo in config.algorithms:
            assert algo.weight == pytest.approx(1.0/3.0)

    def test_validate_success(self, sample_pipeline):
        """Test validate returns empty list for valid config."""
        errors = sample_pipeline.validate()

        assert errors == []

    def test_validate_empty_name_raises(self, sample_algorithms):
        """Test that empty name raises ValueError in __post_init__."""
        # Empty name should raise ValueError in __post_init__
        with pytest.raises(ValueError, match="Pipeline name cannot be empty"):
            PipelineConfig(
                name="",
                description="Test",
                algorithms=sample_algorithms
            )

    def test_validate_no_enabled_algorithms(self, sample_algorithms):
        """Test validate detects no enabled algorithms."""
        # Disable all
        for algo in sample_algorithms:
            algo.enabled = False

        config = PipelineConfig(
            name="test",
            description="Test",
            algorithms=sample_algorithms
        )

        errors = config.validate()

        assert any('at least one enabled algorithm' in e for e in errors)

    def test_validate_weight_not_normalized(self):
        """Test validate detects non-normalized weights."""
        algorithms = [
            AlgorithmConfig("algo1", weight=0.3),
            AlgorithmConfig("algo2", weight=0.3)
        ]

        config = PipelineConfig(
            name="test",
            description="Test",
            algorithms=algorithms
        )

        errors = config.validate()

        # Total weight = 0.6, not ~1.0
        assert any('Total weight' in e or 'not normalized' in e or 'normalize_weights' in e for e in errors)

    def test_validate_invalid_algo_threshold_raises(self):
        """Test that invalid algorithm threshold raises ValueError."""
        # Invalid threshold should raise ValueError in AlgorithmConfig.__post_init__
        with pytest.raises(ValueError, match="Threshold must be between 0.0 and 100.0"):
            algorithms = [
                AlgorithmConfig("algo1", weight=0.5, threshold=150.0),  # Invalid
                AlgorithmConfig("algo2", weight=0.5, threshold=70.0)
            ]
