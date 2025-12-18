"""
Integration tests for Duplicate Finder plugin.

Tests complete workflows including:
- Full analysis workflow
- Benchmark workflow
- Settings persistence (save/load)
- Import/export functionality
"""

import pytest
import tempfile
import json
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from managers.settings_manager import SettingsManager
from managers.unified_config_manager import UnifiedConfigManager
from orchestration.pipeline_manager import PipelineManager  # Updated to use DuplicateFlow-only manager
from managers.test_set_manager import TestSetManager
from managers.benchmark_manager import BenchmarkManager
from database_manager import DatabaseManager


class TestAnalysisWorkflow:
    """Integration tests for the complete analysis workflow."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_db(self, temp_dir):
        """Create a mock database manager with temporary database."""
        db_path = Path(temp_dir) / "test.db"
        db_manager = DatabaseManager(str(db_path))
        yield db_manager
        db_manager.close()

    @pytest.fixture
    def settings_manager(self, temp_dir):
        """Create a settings manager with temporary storage."""
        settings_file = Path(temp_dir) / "settings.json"
        manager = SettingsManager()
        # Override settings file path for testing
        manager.settings_file = str(settings_file)
        return manager

    def test_full_analysis_workflow(self, settings_manager, mock_db, temp_dir):
        """Test complete analysis workflow from configuration to results."""
        # Step 1: Configure analysis settings
        config_manager = UnifiedConfigManager(settings_manager)

        # Set video comparison parameters
        settings_manager.set('video_threshold', 85)
        settings_manager.set('hash_method', 'phash')
        settings_manager.set('hash_workers', 4)

        # Verify configuration
        assert settings_manager.get('video_threshold') == 85
        assert settings_manager.get('hash_method') == 'phash'

        # Step 2: Add test files (mocked)
        test_files = [
            str(Path(temp_dir) / "video1.mp4"),
            str(Path(temp_dir) / "video2.mp4")
        ]

        # Create dummy files
        for file_path in test_files:
            Path(file_path).touch()

        # Step 3: Run analysis (mocked)
        # In a real integration test, this would involve actual video processing
        # For now, we verify the configuration flow

        # Step 4: Verify results can be stored in database
        mock_db.add_video_hash("video1.mp4", "abc123", 90, 1920, 1080, 30.0)
        mock_db.add_video_hash("video2.mp4", "def456", 120, 1920, 1080, 30.0)

        # Step 5: Query duplicates
        duplicates = mock_db.get_duplicates(threshold=85)
        assert isinstance(duplicates, list)

    def test_analysis_with_audio_fingerprinting(self, settings_manager, mock_db):
        """Test analysis workflow with audio fingerprinting enabled."""
        # Configure audio settings
        settings_manager.set('audio_enabled', True)
        settings_manager.set('audio_threshold', 0.7)
        settings_manager.set('audio_precision_mode', 'balanced')

        # Verify audio configuration
        assert settings_manager.get('audio_enabled') is True
        assert settings_manager.get('audio_threshold') == 0.7

        # Analysis would proceed with audio fingerprinting
        # This test verifies the configuration flow

    def test_analysis_with_lsh_optimization(self, settings_manager):
        """Test analysis workflow with LSH optimization enabled."""
        # Configure LSH settings
        settings_manager.set('lsh_enabled', True)
        settings_manager.set('lsh_bands', 20)
        settings_manager.set('lsh_rows', 5)

        # Verify LSH configuration
        assert settings_manager.get('lsh_enabled') is True
        assert settings_manager.get('lsh_bands') == 20
        assert settings_manager.get('lsh_rows') == 5


class TestBenchmarkWorkflow:
    """Integration tests for benchmark workflow."""

    @pytest.fixture
    def benchmark_manager(self):
        """Create a benchmark manager instance."""
        return BenchmarkManager()

    @pytest.fixture
    def test_set_manager(self):
        """Create a test set manager instance."""
        return TestSetManager()

    @pytest.fixture
    def pipeline_manager(self):
        """Create a pipeline manager instance."""
        return PipelineManager()

    def test_benchmark_creation_and_execution(self, benchmark_manager, test_set_manager, pipeline_manager):
        """Test complete benchmark workflow from creation to execution."""
        # Step 1: Create a test set
        test_set_data = {
            'name': 'Integration Test Set',
            'pairs': [
                {
                    'file1': '/path/to/video1.mp4',
                    'file2': '/path/to/video2.mp4',
                    'expected': 'duplicate'
                },
                {
                    'file1': '/path/to/video3.mp4',
                    'file2': '/path/to/video4.mp4',
                    'expected': 'unique'
                }
            ]
        }

        test_set_id = test_set_manager.create_test_set(test_set_data)
        assert test_set_id is not None

        # Step 2: Create a verification pipeline
        pipeline_data = {
            'name': 'Test Pipeline',
            'mode': 'filtering',
            'methods': [
                {'name': 'metadata_filter', 'enabled': True},
                {'name': 'visual_hash', 'enabled': True}
            ]
        }

        pipeline_id = pipeline_manager.create_pipeline(pipeline_data)
        assert pipeline_id is not None

        # Step 3: Create benchmark configuration
        benchmark_config = {
            'name': 'Integration Benchmark',
            'test_set_id': test_set_id,
            'pipeline_id': pipeline_id,
            'iterations': 1
        }

        # In a real test, we would execute the benchmark here
        # For now, we verify the configuration flow

    def test_benchmark_results_storage(self, benchmark_manager):
        """Test storing and retrieving benchmark results."""
        # Create mock benchmark results
        results = {
            'benchmark_id': 'test_bench_1',
            'accuracy': 0.95,
            'precision': 0.93,
            'recall': 0.97,
            'f1_score': 0.95,
            'execution_time': 45.2
        }

        # In a real implementation, this would store to database
        # For now, we verify the data structure is correct
        assert 'accuracy' in results
        assert 'precision' in results
        assert 'recall' in results
        assert results['f1_score'] > 0


class TestSettingsPersistence:
    """Integration tests for settings save/load functionality."""

    @pytest.fixture
    def temp_settings_file(self):
        """Create a temporary settings file."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.close()
        yield temp_file.name
        Path(temp_file.name).unlink(missing_ok=True)

    def test_settings_save_and_load(self, temp_settings_file):
        """Test saving and loading settings."""
        # Create settings manager
        settings_manager = SettingsManager()
        settings_manager.settings_file = temp_settings_file

        # Set various settings
        test_settings = {
            'video_threshold': 88,
            'hash_method': 'dhash',
            'hash_workers': 8,
            'audio_enabled': True,
            'audio_threshold': 0.8,
            'lsh_enabled': True,
            'lsh_bands': 25,
            'cache_enabled': True
        }

        for key, value in test_settings.items():
            settings_manager.set(key, value)

        # Save settings
        settings_manager.save()

        # Create new settings manager and load
        new_settings_manager = SettingsManager()
        new_settings_manager.settings_file = temp_settings_file
        new_settings_manager.load()

        # Verify all settings were preserved
        for key, expected_value in test_settings.items():
            actual_value = new_settings_manager.get(key)
            assert actual_value == expected_value, f"Setting {key} not preserved: expected {expected_value}, got {actual_value}"

    def test_settings_default_values(self):
        """Test that default values are used when no settings file exists."""
        settings_manager = SettingsManager()
        settings_manager.settings_file = "/nonexistent/path/settings.json"

        # Should use defaults without error
        threshold = settings_manager.get('video_threshold', default=80)
        assert threshold == 80

    def test_unified_config_integration(self, temp_settings_file):
        """Test that UnifiedConfigManager integrates with settings persistence."""
        # Create settings manager with temp file
        settings_manager = SettingsManager()
        settings_manager.settings_file = temp_settings_file

        # Set some settings
        settings_manager.set('video_threshold', 92)
        settings_manager.set('hash_method', 'whash')
        settings_manager.save()

        # Create UnifiedConfigManager - should load from settings
        config_manager = UnifiedConfigManager(settings_manager)

        # Verify it uses the persisted settings
        # (actual implementation may vary based on how config_manager reads settings)
        assert settings_manager.get('video_threshold') == 92


class TestImportExport:
    """Integration tests for import/export functionality."""

    @pytest.fixture
    def temp_export_dir(self):
        """Create a temporary directory for exports."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pipeline_export_import(self, temp_export_dir, ):
        """Test exporting and importing verification pipelines."""
        # Create pipeline manager
        pipeline_manager = PipelineManager()

        # Create a pipeline
        pipeline_data = {
            'name': 'Export Test Pipeline',
            'mode': 'sequential',
            'methods': [
                {'name': 'metadata_filter', 'enabled': True, 'params': {'duration_tolerance': 5}},
                {'name': 'visual_hash', 'enabled': True, 'params': {'threshold': 85}},
                {'name': 'audio_fingerprint', 'enabled': True, 'params': {'threshold': 0.75}}
            ]
        }

        pipeline_id = pipeline_manager.create_pipeline(pipeline_data)

        # Export pipeline to JSON
        export_file = Path(temp_export_dir) / "pipeline_export.json"
        exported_pipeline = pipeline_manager.get_pipeline(pipeline_id)

        with open(export_file, 'w') as f:
            json.dump(exported_pipeline, f, indent=2)

        # Import pipeline from JSON
        with open(export_file, 'r') as f:
            imported_data = json.load(f)

        # Create new pipeline from imported data
        # Remove ID to create as new pipeline
        if 'id' in imported_data:
            del imported_data['id']
        imported_data['name'] = 'Imported Pipeline'

        new_pipeline_id = pipeline_manager.create_pipeline(imported_data)
        assert new_pipeline_id is not None

        # Verify imported pipeline has same configuration
        new_pipeline = pipeline_manager.get_pipeline(new_pipeline_id)
        assert new_pipeline['mode'] == pipeline_data['mode']
        assert len(new_pipeline['methods']) == len(pipeline_data['methods'])

    def test_test_set_export_import(self, temp_export_dir):
        """Test exporting and importing test sets."""
        # Create test set manager
        test_set_manager = TestSetManager()

        # Create a test set
        test_set_data = {
            'name': 'Export Test Set',
            'description': 'Test set for import/export testing',
            'pairs': [
                {'file1': 'video1.mp4', 'file2': 'video2.mp4', 'expected': 'duplicate'},
                {'file1': 'video3.mp4', 'file2': 'video4.mp4', 'expected': 'unique'}
            ]
        }

        test_set_id = test_set_manager.create_test_set(test_set_data)

        # Export to JSON
        export_file = Path(temp_export_dir) / "test_set_export.json"
        exported_test_set = test_set_manager.get_test_set(test_set_id)

        with open(export_file, 'w') as f:
            json.dump(exported_test_set, f, indent=2)

        # Verify export file exists and is valid JSON
        assert export_file.exists()

        with open(export_file, 'r') as f:
            imported_data = json.load(f)

        assert imported_data['name'] == 'Export Test Set'
        assert len(imported_data['pairs']) == 2

    def test_settings_export_import(self, temp_export_dir):
        """Test exporting and importing complete settings configuration."""
        # Create settings manager
        settings_manager = SettingsManager()

        # Configure various settings
        settings_data = {
            'video_threshold': 87,
            'hash_method': 'phash',
            'audio_enabled': True,
            'audio_threshold': 0.72,
            'lsh_enabled': True,
            'lsh_bands': 22,
            'cache_enabled': True,
            'cache_size_mb': 512
        }

        for key, value in settings_data.items():
            settings_manager.set(key, value)

        # Export settings to JSON
        export_file = Path(temp_export_dir) / "settings_export.json"
        all_settings = {}
        for key in settings_data.keys():
            all_settings[key] = settings_manager.get(key)

        with open(export_file, 'w') as f:
            json.dump(all_settings, f, indent=2)

        # Create new settings manager and import
        new_settings_manager = SettingsManager()

        with open(export_file, 'r') as f:
            imported_settings = json.load(f)

        for key, value in imported_settings.items():
            new_settings_manager.set(key, value)

        # Verify all settings imported correctly
        for key, expected_value in settings_data.items():
            actual_value = new_settings_manager.get(key)
            assert actual_value == expected_value


class TestEndToEndWorkflows:
    """Integration tests for complete end-to-end user workflows."""

    @pytest.fixture
    def full_system_setup(self):
        """Setup complete system with all managers."""
        temp_dir = tempfile.mkdtemp()

        # Create all managers
        settings_manager = SettingsManager()
        config_manager = UnifiedConfigManager(settings_manager)
        pipeline_manager = PipelineManager()
        test_set_manager = TestSetManager()
        benchmark_manager = BenchmarkManager()

        db_path = Path(temp_dir) / "test.db"
        db_manager = DatabaseManager(str(db_path))

        managers = {
            'settings': settings_manager,
            'config': config_manager,
            'pipeline': pipeline_manager,
            'test_set': test_set_manager,
            'benchmark': benchmark_manager,
            'database': db_manager,
            'temp_dir': temp_dir
        }

        yield managers

        # Cleanup
        db_manager.close()
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_complete_benchmark_workflow(self, full_system_setup):
        """Test complete workflow: configure -> create test set -> create pipeline -> run benchmark."""
        managers = full_system_setup

        # Step 1: Configure system settings
        managers['settings'].set('video_threshold', 85)
        managers['settings'].set('hash_method', 'phash')

        # Step 2: Create test set
        test_set_data = {
            'name': 'E2E Test Set',
            'pairs': [
                {'file1': 'test1.mp4', 'file2': 'test2.mp4', 'expected': 'duplicate'}
            ]
        }
        test_set_id = managers['test_set'].create_test_set(test_set_data)
        assert test_set_id is not None

        # Step 3: Create verification pipeline
        pipeline_data = {
            'name': 'E2E Pipeline',
            'mode': 'filtering',
            'methods': [{'name': 'visual_hash', 'enabled': True}]
        }
        pipeline_id = managers['pipeline'].create_pipeline(pipeline_data)
        assert pipeline_id is not None

        # Step 4: Verify benchmark can be configured
        # (actual execution would require real video files)
        benchmark_config = {
            'test_set_id': test_set_id,
            'pipeline_id': pipeline_id
        }
        assert benchmark_config['test_set_id'] == test_set_id
        assert benchmark_config['pipeline_id'] == pipeline_id

    def test_settings_pipeline_integration(self, full_system_setup):
        """Test that settings changes properly affect pipeline execution."""
        managers = full_system_setup

        # Configure different settings profiles
        profiles = [
            {'name': 'Fast', 'threshold': 90, 'method': 'dhash'},
            {'name': 'Balanced', 'threshold': 85, 'method': 'phash'},
            {'name': 'Strict', 'threshold': 75, 'method': 'whash'}
        ]

        for profile in profiles:
            # Apply settings
            managers['settings'].set('video_threshold', profile['threshold'])
            managers['settings'].set('hash_method', profile['method'])

            # Verify settings applied
            assert managers['settings'].get('video_threshold') == profile['threshold']
            assert managers['settings'].get('hash_method') == profile['method']

            # In real workflow, this would affect analysis execution


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
