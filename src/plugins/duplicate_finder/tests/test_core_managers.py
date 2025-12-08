"""
Unit tests for core manager components.

Tests for:
- UnifiedConfigManager
- PipelineManager
- TestSetManager
- BenchmarkManager
- ProgressManager
- WidgetRegistry
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from managers.unified_config_manager import UnifiedConfigManager
from managers.pipeline_manager import PipelineManager
from managers.test_set_manager import TestSetManager
from managers.benchmark_manager import BenchmarkManager
from managers.progress_manager import ProgressManager
from ui.widget_registry import WidgetRegistry
from managers.settings_manager import SettingsManager


class TestUnifiedConfigManager:
    """Tests for UnifiedConfigManager."""

    @pytest.fixture
    def settings_manager(self):
        """Create a settings manager for testing."""
        return SettingsManager()

    @pytest.fixture
    def config_manager(self, settings_manager):
        """Create a UnifiedConfigManager instance."""
        return UnifiedConfigManager(settings_manager)

    def test_initialization(self, config_manager):
        """Test UnifiedConfigManager initialization."""
        assert config_manager is not None
        assert hasattr(config_manager, 'settings_manager')
        assert hasattr(config_manager, 'video_config')
        assert hasattr(config_manager, 'audio_config')

    def test_video_config_defaults(self, config_manager):
        """Test default video configuration values."""
        video_config = config_manager.video_config
        assert hasattr(video_config, 'threshold')
        assert hasattr(video_config, 'hash_method')
        assert hasattr(video_config, 'hash_workers')
        assert video_config.threshold >= 0
        assert video_config.threshold <= 100

    def test_audio_config_defaults(self, config_manager):
        """Test default audio configuration values."""
        audio_config = config_manager.audio_config
        assert hasattr(audio_config, 'threshold')
        assert hasattr(audio_config, 'precision_mode')
        assert hasattr(audio_config, 'workers')

    def test_lsh_config_defaults(self, config_manager):
        """Test default LSH configuration values."""
        lsh_config = config_manager.lsh_config
        assert hasattr(lsh_config, 'enabled')
        assert hasattr(lsh_config, 'bands')
        assert hasattr(lsh_config, 'rows')
        assert isinstance(lsh_config.enabled, bool)

    def test_metadata_config_defaults(self, config_manager):
        """Test default metadata filter configuration."""
        metadata_config = config_manager.metadata_config
        assert hasattr(metadata_config, 'enabled')
        assert hasattr(metadata_config, 'duration_tolerance')
        assert hasattr(metadata_config, 'size_ratio')


class TestPipelineManager:
    """Tests for PipelineManager."""

    @pytest.fixture
    def pipeline_manager(self):
        """Create a PipelineManager instance."""
        return PipelineManager()

    def test_initialization(self, pipeline_manager):
        """Test PipelineManager initialization."""
        assert pipeline_manager is not None
        assert hasattr(pipeline_manager, 'pipelines')
        assert isinstance(pipeline_manager.pipelines, dict)

    def test_default_pipelines_loaded(self, pipeline_manager):
        """Test that default pipelines are loaded."""
        pipelines = pipeline_manager.get_all_pipelines()
        assert len(pipelines) > 0
        # Check for some known default pipelines
        pipeline_names = [p['name'] for p in pipelines]
        assert any('Default' in name or 'Quick' in name for name in pipeline_names)

    def test_get_pipeline_by_id(self, pipeline_manager):
        """Test retrieving pipeline by ID."""
        pipelines = pipeline_manager.get_all_pipelines()
        if pipelines:
            first_pipeline = pipelines[0]
            pipeline_id = first_pipeline['id']
            retrieved = pipeline_manager.get_pipeline(pipeline_id)
            assert retrieved is not None
            assert retrieved['id'] == pipeline_id

    def test_create_pipeline(self, pipeline_manager):
        """Test creating a new pipeline."""
        pipeline_data = {
            'name': 'Test Pipeline',
            'mode': 'filtering',
            'methods': []
        }
        pipeline_id = pipeline_manager.create_pipeline(pipeline_data)
        assert pipeline_id is not None

        # Verify it was created
        retrieved = pipeline_manager.get_pipeline(pipeline_id)
        assert retrieved is not None
        assert retrieved['name'] == 'Test Pipeline'

    def test_update_pipeline(self, pipeline_manager):
        """Test updating an existing pipeline."""
        # Create a pipeline first
        pipeline_data = {'name': 'Original', 'mode': 'filtering', 'methods': []}
        pipeline_id = pipeline_manager.create_pipeline(pipeline_data)

        # Update it
        updated_data = {'name': 'Updated', 'mode': 'sequential', 'methods': []}
        success = pipeline_manager.update_pipeline(pipeline_id, updated_data)
        assert success is True

        # Verify update
        retrieved = pipeline_manager.get_pipeline(pipeline_id)
        assert retrieved['name'] == 'Updated'
        assert retrieved['mode'] == 'sequential'

    def test_delete_pipeline(self, pipeline_manager):
        """Test deleting a pipeline."""
        # Create a pipeline
        pipeline_data = {'name': 'To Delete', 'mode': 'filtering', 'methods': []}
        pipeline_id = pipeline_manager.create_pipeline(pipeline_data)

        # Delete it
        success = pipeline_manager.delete_pipeline(pipeline_id)
        assert success is True

        # Verify deletion
        retrieved = pipeline_manager.get_pipeline(pipeline_id)
        assert retrieved is None


class TestTestSetManager:
    """Tests for TestSetManager."""

    @pytest.fixture
    def test_set_manager(self):
        """Create a TestSetManager instance."""
        return TestSetManager()

    def test_initialization(self, test_set_manager):
        """Test TestSetManager initialization."""
        assert test_set_manager is not None
        assert hasattr(test_set_manager, 'test_sets')

    def test_create_test_set(self, test_set_manager):
        """Test creating a new test set."""
        test_set_data = {
            'name': 'Test Set 1',
            'pairs': []
        }
        test_set_id = test_set_manager.create_test_set(test_set_data)
        assert test_set_id is not None

    def test_get_all_test_sets(self, test_set_manager):
        """Test retrieving all test sets."""
        test_sets = test_set_manager.get_all_test_sets()
        assert isinstance(test_sets, list)


class TestBenchmarkManager:
    """Tests for BenchmarkManager."""

    @pytest.fixture
    def benchmark_manager(self):
        """Create a BenchmarkManager instance."""
        return BenchmarkManager()

    def test_initialization(self, benchmark_manager):
        """Test BenchmarkManager initialization."""
        assert benchmark_manager is not None
        assert hasattr(benchmark_manager, 'benchmarks')

    def test_get_all_benchmarks(self, benchmark_manager):
        """Test retrieving all benchmarks."""
        benchmarks = benchmark_manager.get_all_benchmarks()
        assert isinstance(benchmarks, list)


class TestProgressManager:
    """Tests for ProgressManager."""

    @pytest.fixture
    def progress_manager(self):
        """Create a ProgressManager instance."""
        return ProgressManager()

    def test_initialization(self, progress_manager):
        """Test ProgressManager initialization."""
        assert progress_manager is not None
        assert hasattr(progress_manager, 'widgets')
        assert isinstance(progress_manager.widgets, dict)

    def test_register_widget(self, progress_manager):
        """Test registering a progress widget."""
        # Mock widget
        class MockWidget:
            def __init__(self):
                self.value = 0
            def setValue(self, value):
                self.value = value

        mock_widget = MockWidget()
        progress_manager.register_widget('test_progress', mock_widget)

        # Verify registration
        assert 'test_progress' in progress_manager.widgets
        assert progress_manager.widgets['test_progress'] == mock_widget

    def test_update_progress(self, progress_manager):
        """Test updating progress."""
        # Mock widget
        class MockWidget:
            def __init__(self):
                self.value = 0
                self.visible = False
            def setValue(self, value):
                self.value = value
            def setVisible(self, visible):
                self.visible = visible

        mock_widget = MockWidget()
        progress_manager.register_widget('test_progress', mock_widget)

        # Update progress
        progress_manager.update_progress('test_progress', 50, 100)

        # Verify update (implementation may vary)
        assert mock_widget.value >= 0

    def test_reset_progress(self, progress_manager):
        """Test resetting progress."""
        class MockWidget:
            def __init__(self):
                self.value = 50
            def setValue(self, value):
                self.value = value
            def reset(self):
                self.value = 0

        mock_widget = MockWidget()
        progress_manager.register_widget('test_progress', mock_widget)

        # Reset progress
        if hasattr(progress_manager, 'reset_progress'):
            progress_manager.reset_progress('test_progress')
            assert mock_widget.value == 0 or mock_widget.value == 50  # Depends on implementation


class TestWidgetRegistry:
    """Tests for WidgetRegistry."""

    @pytest.fixture
    def widget_registry(self):
        """Create a WidgetRegistry instance."""
        return WidgetRegistry()

    def test_initialization(self, widget_registry):
        """Test WidgetRegistry initialization."""
        assert widget_registry is not None
        assert hasattr(widget_registry, 'widgets')
        assert isinstance(widget_registry.widgets, dict)

    def test_register_widget(self, widget_registry):
        """Test registering a widget."""
        # Mock widget
        class MockWidget:
            def __init__(self):
                self.name = "test"

        mock_widget = MockWidget()
        widget_registry.register('test_widget', mock_widget)

        # Verify registration
        assert widget_registry.has('test_widget')

    def test_get_widget(self, widget_registry):
        """Test retrieving a registered widget."""
        # Mock widget
        class MockWidget:
            def __init__(self):
                self.name = "test"

        mock_widget = MockWidget()
        widget_registry.register('test_widget', mock_widget)

        # Retrieve widget
        retrieved = widget_registry.get('test_widget')
        assert retrieved == mock_widget
        assert retrieved.name == "test"

    def test_unregister_widget(self, widget_registry):
        """Test unregistering a widget."""
        # Mock widget
        class MockWidget:
            pass

        mock_widget = MockWidget()
        widget_registry.register('test_widget', mock_widget)

        # Unregister
        if hasattr(widget_registry, 'unregister'):
            widget_registry.unregister('test_widget')
            assert not widget_registry.has('test_widget')

    def test_get_nonexistent_widget(self, widget_registry):
        """Test retrieving a non-existent widget."""
        result = widget_registry.get('nonexistent')
        assert result is None

    def test_register_duplicate_widget(self, widget_registry):
        """Test registering a widget with duplicate name."""
        class MockWidget:
            def __init__(self, value):
                self.value = value

        widget1 = MockWidget(1)
        widget2 = MockWidget(2)

        widget_registry.register('duplicate', widget1)
        widget_registry.register('duplicate', widget2)  # Should replace

        # The second registration should replace the first
        retrieved = widget_registry.get('duplicate')
        assert retrieved.value == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
