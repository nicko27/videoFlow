"""
Pipeline configuration models for DuplicateFlow.

This module provides models for defining and managing custom pipeline configurations,
including algorithm selection, weights, thresholds, and validators.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
import json
from datetime import datetime


@dataclass
class AlgorithmConfig:
    """
    Configuration for a single algorithm in a pipeline.

    Attributes:
        name: Algorithm identifier (must match registered algorithm)
        weight: Contribution weight in final score (0.0-1.0)
        threshold: Individual acceptance threshold (0.0-100.0)
        enabled: Whether algorithm is active
        params: Algorithm-specific parameters

    Example:
        >>> config = AlgorithmConfig(
        ...     name="frame_hash",
        ...     weight=0.3,
        ...     threshold=70.0,
        ...     enabled=True,
        ...     params={"hash_size": 16}
        ... )
    """
    name: str
    weight: float = 1.0
    threshold: float = 70.0
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate algorithm configuration on creation."""
        if not self.name:
            raise ValueError("Algorithm name cannot be empty")

        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {self.weight}")

        if not 0.0 <= self.threshold <= 100.0:
            raise ValueError(f"Threshold must be between 0.0 and 100.0, got {self.threshold}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with all configuration values

        Example:
            >>> config.to_dict()
            {'name': 'frame_hash', 'weight': 0.3, 'threshold': 70.0, ...}
        """
        return {
            'name': self.name,
            'weight': round(self.weight, 3),
            'threshold': round(self.threshold, 2),
            'enabled': self.enabled,
            'params': self.params
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlgorithmConfig':
        """
        Create AlgorithmConfig from dictionary.

        Args:
            data: Dictionary with configuration values

        Returns:
            AlgorithmConfig instance

        Example:
            >>> data = {'name': 'frame_hash', 'weight': 0.3}
            >>> config = AlgorithmConfig.from_dict(data)
        """
        return cls(
            name=data['name'],
            weight=data.get('weight', 1.0),
            threshold=data.get('threshold', 70.0),
            enabled=data.get('enabled', True),
            params=data.get('params', {})
        )


@dataclass
class PipelineConfig:
    """
    Complete pipeline configuration.

    Attributes:
        name: Pipeline identifier
        description: Human-readable description
        algorithms: List of algorithm configurations
        global_threshold: Global similarity threshold (0.0-100.0)
        validators: Pre/post validators configuration
        metadata: Additional metadata (author, created_at, etc.)

    Example:
        >>> config = PipelineConfig(
        ...     name="my_preset",
        ...     description="Custom fast preset",
        ...     algorithms=[
        ...         AlgorithmConfig("frame_hash", weight=0.5),
        ...         AlgorithmConfig("ssim", weight=0.5)
        ...     ],
        ...     global_threshold=75.0
        ... )
    """
    name: str
    description: str
    algorithms: List[AlgorithmConfig]
    global_threshold: float = 70.0
    validators: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate pipeline configuration on creation."""
        if not self.name:
            raise ValueError("Pipeline name cannot be empty")

        if not self.algorithms:
            raise ValueError("Pipeline must have at least one algorithm")

        if not 0.0 <= self.global_threshold <= 100.0:
            raise ValueError(f"Global threshold must be between 0.0 and 100.0, got {self.global_threshold}")

        # Validate algorithm names are unique
        names = [algo.name for algo in self.algorithms]
        if len(names) != len(set(names)):
            raise ValueError("Algorithm names must be unique in pipeline")

        # Auto-add creation metadata if not present
        if 'created_at' not in self.metadata:
            self.metadata['created_at'] = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with complete pipeline configuration

        Example:
            >>> config.to_dict()
            {'name': 'my_preset', 'description': '...', 'algorithms': [...]}
        """
        return {
            'name': self.name,
            'description': self.description,
            'algorithms': [algo.to_dict() for algo in self.algorithms],
            'global_threshold': round(self.global_threshold, 2),
            'validators': self.validators,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PipelineConfig':
        """
        Create PipelineConfig from dictionary.

        Args:
            data: Dictionary with pipeline configuration

        Returns:
            PipelineConfig instance

        Raises:
            ValueError: If required fields are missing or invalid

        Example:
            >>> data = {'name': 'preset1', 'algorithms': [...]}
            >>> config = PipelineConfig.from_dict(data)
        """
        algorithms = [
            AlgorithmConfig.from_dict(algo_data)
            for algo_data in data['algorithms']
        ]

        return cls(
            name=data['name'],
            description=data.get('description', ''),
            algorithms=algorithms,
            global_threshold=data.get('global_threshold', 70.0),
            validators=data.get('validators', {}),
            metadata=data.get('metadata', {})
        )

    def to_yaml(self, indent: int = 2) -> str:
        """
        Serialize to YAML string.

        Args:
            indent: Indentation level (default: 2 spaces)

        Returns:
            YAML string representation

        Example:
            >>> yaml_str = config.to_yaml()
            >>> print(yaml_str)
            name: my_preset
            description: Custom preset
            algorithms:
              - name: frame_hash
                weight: 0.5
        """
        return yaml.dump(
            self.to_dict(),
            default_flow_style=False,
            sort_keys=False,
            indent=indent
        )

    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'PipelineConfig':
        """
        Deserialize from YAML string.

        Args:
            yaml_str: YAML string with pipeline configuration

        Returns:
            PipelineConfig instance

        Raises:
            ValueError: If YAML is invalid or missing required fields

        Example:
            >>> yaml_str = "name: preset1\\nalgorithms: [...]"
            >>> config = PipelineConfig.from_yaml(yaml_str)
        """
        try:
            data = yaml.safe_load(yaml_str)
            return cls.from_dict(data)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {str(e)}")

    def to_json(self, indent: int = 2) -> str:
        """
        Serialize to JSON string.

        Args:
            indent: Indentation level (default: 2 spaces)

        Returns:
            JSON string representation

        Example:
            >>> json_str = config.to_json()
            >>> print(json_str)
            {
              "name": "my_preset",
              "algorithms": [...]
            }
        """
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> 'PipelineConfig':
        """
        Deserialize from JSON string.

        Args:
            json_str: JSON string with pipeline configuration

        Returns:
            PipelineConfig instance

        Raises:
            ValueError: If JSON is invalid or missing required fields

        Example:
            >>> json_str = '{"name": "preset1", "algorithms": [...]}'
            >>> config = PipelineConfig.from_json(json_str)
        """
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")

    def save(self, path: Path, format: str = 'yaml') -> None:
        """
        Save configuration to file.

        Args:
            path: File path to save to
            format: File format ('yaml' or 'json')

        Raises:
            ValueError: If format is not supported

        Example:
            >>> config.save(Path("~/.duplicateflow/pipelines/my_preset.yaml"))
        """
        if format not in ('yaml', 'json'):
            raise ValueError(f"Unsupported format: {format}. Use 'yaml' or 'json'")

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize and write
        content = self.to_yaml() if format == 'yaml' else self.to_json()
        path.write_text(content, encoding='utf-8')

    @classmethod
    def load(cls, path: Path) -> 'PipelineConfig':
        """
        Load configuration from file.

        Auto-detects format from file extension (.yaml/.yml or .json).

        Args:
            path: File path to load from

        Returns:
            PipelineConfig instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is unsupported or content is invalid

        Example:
            >>> config = PipelineConfig.load(Path("my_preset.yaml"))
        """
        if not path.exists():
            raise FileNotFoundError(f"Pipeline config not found: {path}")

        content = path.read_text(encoding='utf-8')
        suffix = path.suffix.lower()

        if suffix in ('.yaml', '.yml'):
            return cls.from_yaml(content)
        elif suffix == '.json':
            return cls.from_json(content)
        else:
            raise ValueError(f"Unsupported file extension: {suffix}. Use .yaml, .yml, or .json")

    def get_enabled_algorithms(self) -> List[AlgorithmConfig]:
        """
        Get list of enabled algorithms only.

        Returns:
            List of AlgorithmConfig instances where enabled=True

        Example:
            >>> enabled = config.get_enabled_algorithms()
            >>> len(enabled)
            3
        """
        return [algo for algo in self.algorithms if algo.enabled]

    def get_algorithm(self, name: str) -> Optional[AlgorithmConfig]:
        """
        Get algorithm configuration by name.

        Args:
            name: Algorithm identifier

        Returns:
            AlgorithmConfig if found, None otherwise

        Example:
            >>> algo = config.get_algorithm("frame_hash")
            >>> algo.weight
            0.5
        """
        for algo in self.algorithms:
            if algo.name == name:
                return algo
        return None

    def get_total_weight(self) -> float:
        """
        Calculate total weight of all enabled algorithms.

        Returns:
            Sum of weights for enabled algorithms

        Example:
            >>> config.get_total_weight()
            1.0
        """
        return sum(algo.weight for algo in self.get_enabled_algorithms())

    def normalize_weights(self) -> None:
        """
        Normalize algorithm weights to sum to 1.0.

        Only affects enabled algorithms. Modifies weights in-place.

        Example:
            >>> config.normalize_weights()
            >>> config.get_total_weight()
            1.0
        """
        enabled = self.get_enabled_algorithms()
        if not enabled:
            return

        total = sum(algo.weight for algo in enabled)
        if total == 0:
            # Equal weights if all are zero
            for algo in enabled:
                algo.weight = 1.0 / len(enabled)
        else:
            # Normalize to sum to 1.0
            for algo in enabled:
                algo.weight = algo.weight / total

    def validate(self) -> List[str]:
        """
        Validate pipeline configuration.

        Returns:
            List of validation error messages (empty if valid)

        Example:
            >>> errors = config.validate()
            >>> if errors:
            ...     print("Validation failed:", errors)
        """
        errors = []

        # Check basic requirements
        if not self.name:
            errors.append("Pipeline name is required")

        if not self.algorithms:
            errors.append("Pipeline must have at least one algorithm")

        # Check at least one enabled algorithm
        enabled = self.get_enabled_algorithms()
        if not enabled:
            errors.append("Pipeline must have at least one enabled algorithm")

        # Check weight normalization
        total_weight = self.get_total_weight()
        if enabled and abs(total_weight - 1.0) > 0.01:
            errors.append(
                f"Total weight of enabled algorithms should be ~1.0, got {total_weight:.3f}. "
                "Consider calling normalize_weights()"
            )

        # Check threshold ranges
        if not 0.0 <= self.global_threshold <= 100.0:
            errors.append(f"Global threshold must be 0-100, got {self.global_threshold}")

        for algo in self.algorithms:
            if not 0.0 <= algo.threshold <= 100.0:
                errors.append(f"Algorithm '{algo.name}' threshold must be 0-100, got {algo.threshold}")

            if not 0.0 <= algo.weight <= 1.0:
                errors.append(f"Algorithm '{algo.name}' weight must be 0-1, got {algo.weight}")

        return errors
