"""
Pipeline management service for DuplicateFlow.

This service provides CRUD operations for custom pipeline configurations,
including creation, storage, loading, validation, and export/import.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import shutil
from datetime import datetime

from duplicateflow.core.models.pipeline_config import PipelineConfig, AlgorithmConfig
from duplicateflow.core.interfaces import IProgressReporter, IUIAdapter, MessageType
from duplicateflow.pipeline.registry import ALGORITHM_REGISTRY


class PipelineManagementService:
    """
    Service for managing pipeline configurations.

    Provides operations for creating, saving, loading, listing, and validating
    custom pipeline configurations. Handles storage in user's home directory.

    Attributes:
        progress: Progress reporter for long operations
        ui: UI adapter for user messages
        pipelines_dir: Directory for storing pipeline configurations
    """

    DEFAULT_PIPELINES_DIR = Path.home() / ".duplicateflow" / "pipelines"

    def __init__(
        self,
        progress: IProgressReporter,
        ui: IUIAdapter,
        pipelines_dir: Optional[Path] = None
    ):
        """
        Initialize pipeline management service.

        Args:
            progress: Progress reporter for operations
            ui: UI adapter for messages
            pipelines_dir: Custom directory for pipelines (default: ~/.duplicateflow/pipelines)

        Example:
            >>> from duplicateflow.core.interfaces import NullProgressReporter, NullUIAdapter
            >>> service = PipelineManagementService(
            ...     NullProgressReporter(),
            ...     NullUIAdapter()
            ... )
        """
        self.progress = progress
        self.ui = ui
        self.pipelines_dir = pipelines_dir or self.DEFAULT_PIPELINES_DIR

        # Ensure directory exists
        self.pipelines_dir.mkdir(parents=True, exist_ok=True)

    def create_pipeline(
        self,
        name: str,
        description: str,
        algorithms: List[AlgorithmConfig],
        global_threshold: float = 70.0,
        validators: Optional[Dict[str, Any]] = None,
        auto_normalize: bool = True
    ) -> PipelineConfig:
        """
        Create a new pipeline configuration.

        Args:
            name: Pipeline identifier
            description: Human-readable description
            algorithms: List of algorithm configurations
            global_threshold: Global similarity threshold (0-100)
            validators: Validator configuration
            auto_normalize: Automatically normalize algorithm weights to sum to 1.0

        Returns:
            Created PipelineConfig instance

        Raises:
            ValueError: If validation fails

        Example:
            >>> algorithms = [
            ...     AlgorithmConfig("frame_hash", weight=0.5, threshold=70.0),
            ...     AlgorithmConfig("ssim", weight=0.5, threshold=75.0)
            ... ]
            >>> config = service.create_pipeline(
            ...     name="my_preset",
            ...     description="Custom balanced preset",
            ...     algorithms=algorithms
            ... )
        """
        self.ui.display_message(f"Creating pipeline: {name}", MessageType.INFO)

        # Create config
        config = PipelineConfig(
            name=name,
            description=description,
            algorithms=algorithms,
            global_threshold=global_threshold,
            validators=validators or {},
            metadata={
                'created_at': datetime.now().isoformat(),
                'version': '1.0'
            }
        )

        # Normalize weights if requested
        if auto_normalize:
            config.normalize_weights()

        # Validate
        errors = config.validate()
        if errors:
            error_msg = "Pipeline validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            self.ui.display_message(error_msg, MessageType.ERROR)
            raise ValueError(error_msg)

        # Validate algorithms exist in registry
        validation_errors = self.validate_algorithms(config)
        if validation_errors:
            error_msg = "Algorithm validation failed:\n" + "\n".join(f"  - {e}" for e in validation_errors)
            self.ui.display_message(error_msg, MessageType.ERROR)
            raise ValueError(error_msg)

        self.ui.display_message(f"Pipeline created successfully: {name}", MessageType.SUCCESS)

        return config

    def save_pipeline(
        self,
        config: PipelineConfig,
        format: str = 'yaml',
        overwrite: bool = False
    ) -> Path:
        """
        Save pipeline configuration to disk.

        Args:
            config: Pipeline configuration to save
            format: File format ('yaml' or 'json')
            overwrite: Allow overwriting existing file

        Returns:
            Path to saved file

        Raises:
            FileExistsError: If file exists and overwrite=False
            ValueError: If format is invalid

        Example:
            >>> path = service.save_pipeline(config, format='yaml')
            >>> print(f"Saved to {path}")
        """
        self.ui.display_message(f"Saving pipeline: {config.name}", MessageType.INFO)

        # Determine file path
        extension = 'yaml' if format == 'yaml' else 'json'
        file_path = self.pipelines_dir / f"{config.name}.{extension}"

        # Check for existing file
        if file_path.exists() and not overwrite:
            raise FileExistsError(
                f"Pipeline already exists: {file_path}. Use overwrite=True to replace."
            )

        # Save
        config.save(file_path, format=format)

        self.ui.display_message(f"Pipeline saved: {file_path}", MessageType.SUCCESS)

        return file_path

    def load_pipeline(self, name: str) -> PipelineConfig:
        """
        Load pipeline configuration from disk.

        Tries to load from YAML first, then JSON if not found.

        Args:
            name: Pipeline name (without extension)

        Returns:
            Loaded PipelineConfig instance

        Raises:
            FileNotFoundError: If pipeline file not found

        Example:
            >>> config = service.load_pipeline("my_preset")
            >>> print(config.description)
        """
        self.ui.display_message(f"Loading pipeline: {name}", MessageType.INFO)

        # Try YAML first
        yaml_path = self.pipelines_dir / f"{name}.yaml"
        if yaml_path.exists():
            config = PipelineConfig.load(yaml_path)
            self.ui.display_message(f"Pipeline loaded from {yaml_path}", MessageType.SUCCESS)
            return config

        # Try JSON
        json_path = self.pipelines_dir / f"{name}.json"
        if json_path.exists():
            config = PipelineConfig.load(json_path)
            self.ui.display_message(f"Pipeline loaded from {json_path}", MessageType.SUCCESS)
            return config

        # Not found
        raise FileNotFoundError(
            f"Pipeline not found: {name}. Searched in {self.pipelines_dir}"
        )

    def list_pipelines(self) -> List[Dict[str, Any]]:
        """
        List all saved pipeline configurations.

        Returns:
            List of dictionaries with pipeline metadata (name, description, algorithms count, path)

        Example:
            >>> pipelines = service.list_pipelines()
            >>> for p in pipelines:
            ...     print(f"{p['name']}: {p['description']}")
        """
        self.ui.display_message("Listing pipelines...", MessageType.INFO)

        pipelines = []

        # Find all YAML and JSON files
        for path in self.pipelines_dir.glob("*.yaml"):
            try:
                config = PipelineConfig.load(path)
                pipelines.append({
                    'name': config.name,
                    'description': config.description,
                    'algorithms_count': len(config.get_enabled_algorithms()),
                    'path': str(path),
                    'format': 'yaml',
                    'created_at': config.metadata.get('created_at', 'unknown')
                })
            except Exception as e:
                self.ui.display_message(
                    f"Warning: Failed to load {path.name}: {str(e)}",
                    MessageType.WARNING
                )

        for path in self.pipelines_dir.glob("*.json"):
            try:
                config = PipelineConfig.load(path)
                pipelines.append({
                    'name': config.name,
                    'description': config.description,
                    'algorithms_count': len(config.get_enabled_algorithms()),
                    'path': str(path),
                    'format': 'json',
                    'created_at': config.metadata.get('created_at', 'unknown')
                })
            except Exception as e:
                self.ui.display_message(
                    f"Warning: Failed to load {path.name}: {str(e)}",
                    MessageType.WARNING
                )

        # Sort by name
        pipelines.sort(key=lambda p: p['name'])

        self.ui.display_message(f"Found {len(pipelines)} pipeline(s)", MessageType.INFO)

        return pipelines

    def delete_pipeline(self, name: str) -> None:
        """
        Delete a pipeline configuration.

        Args:
            name: Pipeline name (without extension)

        Raises:
            FileNotFoundError: If pipeline not found

        Example:
            >>> service.delete_pipeline("my_preset")
        """
        self.ui.display_message(f"Deleting pipeline: {name}", MessageType.INFO)

        deleted = False

        # Try YAML
        yaml_path = self.pipelines_dir / f"{name}.yaml"
        if yaml_path.exists():
            yaml_path.unlink()
            deleted = True

        # Try JSON
        json_path = self.pipelines_dir / f"{name}.json"
        if json_path.exists():
            json_path.unlink()
            deleted = True

        if not deleted:
            raise FileNotFoundError(f"Pipeline not found: {name}")

        self.ui.display_message(f"Pipeline deleted: {name}", MessageType.SUCCESS)

    def validate_pipeline(self, config: PipelineConfig) -> List[str]:
        """
        Validate a pipeline configuration comprehensively.

        Checks:
        - Basic configuration validity (thresholds, weights)
        - Algorithm existence in registry
        - Weight normalization
        - Validator configuration

        Args:
            config: Pipeline configuration to validate

        Returns:
            List of validation error messages (empty if valid)

        Example:
            >>> errors = service.validate_pipeline(config)
            >>> if errors:
            ...     print("Validation errors:", errors)
        """
        errors = []

        # Basic validation from PipelineConfig
        errors.extend(config.validate())

        # Algorithm registry validation
        errors.extend(self.validate_algorithms(config))

        return errors

    def validate_algorithms(self, config: PipelineConfig) -> List[str]:
        """
        Validate that all algorithms in config exist in registry.

        Args:
            config: Pipeline configuration

        Returns:
            List of error messages for missing algorithms

        Example:
            >>> errors = service.validate_algorithms(config)
            >>> if errors:
            ...     print("Missing algorithms:", errors)
        """
        errors = []

        for algo in config.algorithms:
            if algo.name not in ALGORITHM_REGISTRY:
                errors.append(
                    f"Algorithm '{algo.name}' not found in registry. "
                    f"Available: {', '.join(sorted(ALGORITHM_REGISTRY.keys()))}"
                )

        return errors

    def export_pipeline(
        self,
        name: str,
        destination: Path,
        format: str = 'yaml'
    ) -> Path:
        """
        Export pipeline to a different location.

        Args:
            name: Pipeline name to export
            destination: Destination file path
            format: Export format ('yaml' or 'json')

        Returns:
            Path to exported file

        Example:
            >>> service.export_pipeline("my_preset", Path("/tmp/backup.yaml"))
        """
        self.ui.display_message(f"Exporting pipeline: {name}", MessageType.INFO)

        # Load pipeline
        config = self.load_pipeline(name)

        # Ensure destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Save to destination
        config.save(destination, format=format)

        self.ui.display_message(f"Pipeline exported to {destination}", MessageType.SUCCESS)

        return destination

    def import_pipeline(
        self,
        source: Path,
        new_name: Optional[str] = None,
        overwrite: bool = False
    ) -> PipelineConfig:
        """
        Import pipeline from external file.

        Args:
            source: Source file path
            new_name: Optional new name for imported pipeline
            overwrite: Allow overwriting existing pipeline

        Returns:
            Imported PipelineConfig instance

        Raises:
            FileNotFoundError: If source file doesn't exist
            FileExistsError: If pipeline exists and overwrite=False

        Example:
            >>> config = service.import_pipeline(
            ...     Path("/tmp/custom.yaml"),
            ...     new_name="imported_preset"
            ... )
        """
        self.ui.display_message(f"Importing pipeline from {source}", MessageType.INFO)

        # Load from source
        config = PipelineConfig.load(source)

        # Rename if requested
        if new_name:
            # Create new config with updated name
            config = PipelineConfig(
                name=new_name,
                description=config.description,
                algorithms=config.algorithms,
                global_threshold=config.global_threshold,
                validators=config.validators,
                metadata={
                    **config.metadata,
                    'imported_from': str(source),
                    'imported_at': datetime.now().isoformat()
                }
            )

        # Validate
        errors = self.validate_pipeline(config)
        if errors:
            error_msg = "Import validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            self.ui.display_message(error_msg, MessageType.ERROR)
            raise ValueError(error_msg)

        # Determine format from source extension
        format = 'yaml' if source.suffix in ('.yaml', '.yml') else 'json'

        # Save to pipelines directory
        self.save_pipeline(config, format=format, overwrite=overwrite)

        self.ui.display_message(f"Pipeline imported successfully: {config.name}", MessageType.SUCCESS)

        return config

    def get_pipeline_info(self, name: str) -> Dict[str, Any]:
        """
        Get detailed information about a pipeline.

        Args:
            name: Pipeline name

        Returns:
            Dictionary with comprehensive pipeline information

        Example:
            >>> info = service.get_pipeline_info("my_preset")
            >>> print(info['algorithms_count'])
            4
        """
        config = self.load_pipeline(name)

        enabled = config.get_enabled_algorithms()
        total_weight = config.get_total_weight()

        return {
            'name': config.name,
            'description': config.description,
            'global_threshold': config.global_threshold,
            'algorithms_total': len(config.algorithms),
            'algorithms_enabled': len(enabled),
            'algorithms': [
                {
                    'name': algo.name,
                    'weight': algo.weight,
                    'threshold': algo.threshold,
                    'enabled': algo.enabled,
                    'params_count': len(algo.params)
                }
                for algo in config.algorithms
            ],
            'total_weight': total_weight,
            'weight_normalized': abs(total_weight - 1.0) < 0.01,
            'validators': config.validators,
            'metadata': config.metadata,
            'validation_errors': self.validate_pipeline(config)
        }
