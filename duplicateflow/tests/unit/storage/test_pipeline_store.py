"""
Unit tests for PipelineStore.

Tests the persistent pipeline configuration storage system that saves
and loads custom pipeline configurations using SQLite.
"""

import pytest
import json
from pathlib import Path
import sqlite3

from duplicateflow.storage.pipeline_store import PipelineStore


class TestPipelineStoreInit:
    """Test PipelineStore initialization."""

    def test_init_default_path(self):
        """Test initialization with default database path."""
        store = PipelineStore()

        assert store.db_path.exists()
        assert store.db_path.name == "pipelines.db"

    def test_init_custom_path(self, tmp_path):
        """Test initialization with custom database path."""
        db_path = tmp_path / "custom" / "pipelines.db"
        store = PipelineStore(str(db_path))

        assert store.db_path == db_path
        assert db_path.exists()
        assert db_path.parent.exists()

    def test_init_creates_schema(self, tmp_path):
        """Test that initialization creates database schema."""
        db_path = tmp_path / "test.db"
        store = PipelineStore(str(db_path))

        # Verify schema exists
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Check table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pipelines'")
            assert cursor.fetchone() is not None

            # Check indices exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indices = [row[0] for row in cursor.fetchall()]
            assert 'idx_name' in indices
            assert 'idx_category' in indices
            assert 'idx_hash' in indices


class TestPipelineStoreComputeHash:
    """Test configuration hash computation."""

    def test_compute_hash_deterministic(self, tmp_path):
        """Test that same config produces same hash."""
        store = PipelineStore(str(tmp_path / "test.db"))

        config = {'steps': [{'algorithm': 'frame_hash', 'weight': 1.0}]}
        hash1 = store._compute_hash(config)
        hash2 = store._compute_hash(config)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 16  # SHA256 truncated to 16 chars

    def test_compute_hash_order_independent(self, tmp_path):
        """Test that parameter order doesn't affect hash."""
        store = PipelineStore(str(tmp_path / "test.db"))

        config1 = {'global_threshold': 75.0, 'steps': []}
        config2 = {'steps': [], 'global_threshold': 75.0}

        hash1 = store._compute_hash(config1)
        hash2 = store._compute_hash(config2)

        assert hash1 == hash2

    def test_compute_hash_different_configs(self, tmp_path):
        """Test that different configs produce different hashes."""
        store = PipelineStore(str(tmp_path / "test.db"))

        config1 = {'steps': [{'algorithm': 'frame_hash'}]}
        config2 = {'steps': [{'algorithm': 'ssim'}]}

        hash1 = store._compute_hash(config1)
        hash2 = store._compute_hash(config2)

        assert hash1 != hash2


class TestPipelineStoreSave:
    """Test save method."""

    @pytest.fixture
    def store(self, tmp_path):
        return PipelineStore(str(tmp_path / "test.db"))

    @pytest.fixture
    def sample_config(self):
        return {
            'steps': [
                {'algorithm': 'frame_hash', 'weight': 0.6, 'threshold': 80},
                {'algorithm': 'color_histogram', 'weight': 0.4, 'threshold': 75}
            ],
            'global_threshold': 75.0,
            'analyze_duration': 60.0
        }

    def test_save_simple_pipeline(self, store, sample_config):
        """Test saving a simple pipeline."""
        pipeline_id = store.save(
            name="test_pipeline",
            config=sample_config,
            description="Test pipeline"
        )

        assert isinstance(pipeline_id, int)
        assert pipeline_id > 0

        # Verify stored in database
        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM pipelines')
            assert cursor.fetchone()[0] == 1

    def test_save_with_category(self, store, sample_config):
        """Test saving pipeline with custom category."""
        store.save(
            name="duplicate_detector",
            config=sample_config,
            category="duplicates"
        )

        # Verify category
        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT category FROM pipelines WHERE name = ?', ("duplicate_detector",))
            assert cursor.fetchone()[0] == "duplicates"

    def test_save_duplicate_name_fails(self, store, sample_config):
        """Test that saving with duplicate name fails without overwrite."""
        store.save("pipeline1", sample_config)

        # Try to save again with same name
        with pytest.raises(ValueError, match="already exists"):
            store.save("pipeline1", sample_config)

    def test_save_with_overwrite(self, store, sample_config):
        """Test saving with overwrite=True updates existing pipeline."""
        # Save initial
        store.save("pipeline1", sample_config, description="Original")

        # Update with overwrite
        new_config = {'steps': [{'algorithm': 'ssim', 'weight': 1.0}]}
        store.save("pipeline1", new_config, description="Updated", overwrite=True)

        # Should have only 1 entry
        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM pipelines')
            assert cursor.fetchone()[0] == 1

            # Verify config updated
            cursor.execute('SELECT description FROM pipelines WHERE name = ?', ("pipeline1",))
            assert cursor.fetchone()[0] == "Updated"

    def test_save_complex_config(self, store):
        """Test saving complex configuration with validators."""
        complex_config = {
            'steps': [
                {'algorithm': 'frame_hash', 'weight': 0.6, 'threshold': 80}
            ],
            'global_threshold': 75.0,
            'pre_validators': [
                {
                    'type': 'LengthValidator',
                    'config': {
                        'tolerance_percent': 5.0,
                        'tolerance_seconds': 30.0
                    }
                }
            ],
            'analyze_duration': 60.0,
            'analyze_from_start': True
        }

        pipeline_id = store.save("complex", complex_config)
        assert pipeline_id > 0

        # Verify round-trip
        loaded = store.load("complex")
        assert loaded == complex_config


class TestPipelineStoreLoad:
    """Test load method."""

    @pytest.fixture
    def store_with_pipeline(self, tmp_path):
        store = PipelineStore(str(tmp_path / "test.db"))
        config = {'steps': [{'algorithm': 'frame_hash', 'weight': 1.0}]}
        store.save("test_pipeline", config, "Test")
        return store

    def test_load_existing_pipeline(self, store_with_pipeline):
        """Test loading existing pipeline."""
        config = store_with_pipeline.load("test_pipeline")

        assert config is not None
        assert 'steps' in config
        assert len(config['steps']) == 1

    def test_load_nonexistent_pipeline(self, store_with_pipeline):
        """Test loading non-existent pipeline returns None."""
        config = store_with_pipeline.load("nonexistent")

        assert config is None

    def test_load_updates_usage_stats(self, store_with_pipeline):
        """Test that load increments usage_count."""
        # Load twice
        store_with_pipeline.load("test_pipeline")
        store_with_pipeline.load("test_pipeline")

        # Verify usage count
        with sqlite3.connect(store_with_pipeline.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT usage_count FROM pipelines WHERE name = ?', ("test_pipeline",))
            usage_count = cursor.fetchone()[0]
            assert usage_count == 2

    def test_load_inactive_pipeline_returns_none(self, tmp_path):
        """Test that loading inactive pipeline returns None."""
        store = PipelineStore(str(tmp_path / "test.db"))
        config = {'steps': []}
        store.save("inactive", config)

        # Mark as inactive
        store.delete("inactive", soft=True)

        # Load should return None
        loaded = store.load("inactive")
        assert loaded is None


class TestPipelineStoreList:
    """Test list method."""

    @pytest.fixture
    def store_with_pipelines(self, tmp_path):
        store = PipelineStore(str(tmp_path / "test.db"))

        # Create multiple pipelines
        store.save("dup1", {'steps': []}, "Duplicate detector 1", category="duplicates")
        store.save("dup2", {'steps': []}, "Duplicate detector 2", category="duplicates")
        store.save("scene1", {'steps': []}, "Scene detector", category="scenes")

        return store

    def test_list_all_pipelines(self, store_with_pipelines):
        """Test listing all pipelines."""
        pipelines = store_with_pipelines.list()

        assert len(pipelines) == 3
        assert all('name' in p for p in pipelines)
        assert all('description' in p for p in pipelines)
        assert all('category' in p for p in pipelines)

    def test_list_by_category(self, store_with_pipelines):
        """Test listing pipelines filtered by category."""
        duplicates = store_with_pipelines.list(category="duplicates")

        assert len(duplicates) == 2
        assert all(p['category'] == "duplicates" for p in duplicates)

    def test_list_includes_metadata(self, store_with_pipelines):
        """Test that list includes metadata fields."""
        pipelines = store_with_pipelines.list()

        for p in pipelines:
            assert 'created_at' in p
            assert 'updated_at' in p
            assert 'usage_count' in p

    def test_list_excludes_inactive(self, tmp_path):
        """Test that list excludes inactive pipelines by default."""
        store = PipelineStore(str(tmp_path / "test.db"))

        store.save("active", {'steps': []})
        store.save("inactive", {'steps': []})
        store.delete("inactive", soft=True)

        pipelines = store.list(active_only=True)

        assert len(pipelines) == 1
        assert pipelines[0]['name'] == "active"

    def test_list_includes_inactive_when_requested(self, tmp_path):
        """Test that list can include inactive pipelines."""
        store = PipelineStore(str(tmp_path / "test.db"))

        store.save("active", {'steps': []})
        store.save("inactive", {'steps': []})
        store.delete("inactive", soft=True)

        pipelines = store.list(active_only=False)

        assert len(pipelines) == 2

    def test_list_ordered_by_usage(self, tmp_path):
        """Test that list is ordered by usage count."""
        store = PipelineStore(str(tmp_path / "test.db"))

        store.save("low_use", {'steps': []})
        store.save("high_use", {'steps': []})

        # Use high_use multiple times
        for _ in range(5):
            store.load("high_use")

        pipelines = store.list()

        # high_use should be first (highest usage)
        assert pipelines[0]['name'] == "high_use"
        assert pipelines[0]['usage_count'] == 5


class TestPipelineStoreDelete:
    """Test delete method."""

    @pytest.fixture
    def store(self, tmp_path):
        store = PipelineStore(str(tmp_path / "test.db"))
        store.save("pipeline1", {'steps': []})
        return store

    def test_delete_soft(self, store):
        """Test soft delete marks as inactive."""
        store.delete("pipeline1", soft=True)

        # Verify still in database but inactive
        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_active FROM pipelines WHERE name = ?', ("pipeline1",))
            is_active = cursor.fetchone()[0]
            assert is_active == 0

    def test_delete_hard(self, store):
        """Test hard delete removes from database."""
        store.delete("pipeline1", soft=False)

        # Verify removed from database
        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM pipelines WHERE name = ?', ("pipeline1",))
            count = cursor.fetchone()[0]
            assert count == 0


class TestPipelineStoreGetStats:
    """Test get_stats method."""

    @pytest.fixture
    def store(self, tmp_path):
        store = PipelineStore(str(tmp_path / "test.db"))
        store.save("pipeline1", {'steps': []}, "Test pipeline", category="duplicates")

        # Use it a few times
        for _ in range(3):
            store.load("pipeline1")

        return store

    def test_get_stats_existing_pipeline(self, store):
        """Test getting stats for existing pipeline."""
        stats = store.get_stats("pipeline1")

        assert stats is not None
        assert stats['name'] == "pipeline1"
        assert stats['category'] == "duplicates"
        assert stats['description'] == "Test pipeline"
        assert stats['usage_count'] == 3
        assert 'created_at' in stats
        assert 'updated_at' in stats

    def test_get_stats_nonexistent_pipeline(self, store):
        """Test getting stats for non-existent pipeline returns None."""
        stats = store.get_stats("nonexistent")

        assert stats is None

    def test_get_stats_inactive_pipeline(self, store):
        """Test getting stats for inactive pipeline returns None."""
        store.delete("pipeline1", soft=True)

        stats = store.get_stats("pipeline1")

        assert stats is None


class TestPipelineStoreExportPreset:
    """Test export_preset method."""

    @pytest.fixture
    def store(self, tmp_path):
        store = PipelineStore(str(tmp_path / "test.db"))
        config = {
            'steps': [
                {'algorithm': 'frame_hash', 'weight': 1.0}
            ],
            'global_threshold': 75.0
        }
        store.save("export_test", config)
        return store

    def test_export_preset_creates_file(self, store, tmp_path):
        """Test that export creates JSON file."""
        output_path = tmp_path / "exported.json"
        store.export_preset("export_test", str(output_path))

        assert output_path.exists()

    def test_export_preset_content(self, store, tmp_path):
        """Test that exported content is valid JSON."""
        output_path = tmp_path / "exported.json"
        store.export_preset("export_test", str(output_path))

        # Load and verify
        with open(output_path) as f:
            exported = json.load(f)

        assert 'steps' in exported
        assert 'global_threshold' in exported
        assert exported['global_threshold'] == 75.0

    def test_export_preset_nonexistent(self, store, tmp_path):
        """Test that exporting non-existent pipeline raises error."""
        output_path = tmp_path / "exported.json"

        with pytest.raises(ValueError, match="not found"):
            store.export_preset("nonexistent", str(output_path))

    def test_export_preset_creates_parent_dirs(self, store, tmp_path):
        """Test that export creates parent directories."""
        output_path = tmp_path / "nested" / "path" / "exported.json"
        store.export_preset("export_test", str(output_path))

        assert output_path.exists()
        assert output_path.parent.exists()


class TestPipelineStoreImportPreset:
    """Test import_preset method."""

    @pytest.fixture
    def preset_file(self, tmp_path):
        """Create a sample preset file."""
        preset_path = tmp_path / "preset.json"
        config = {
            'steps': [
                {'algorithm': 'ssim', 'weight': 1.0}
            ],
            'global_threshold': 80.0
        }

        with open(preset_path, 'w') as f:
            json.dump(config, f)

        return preset_path

    def test_import_preset_default_name(self, tmp_path, preset_file):
        """Test importing with default name (filename)."""
        store = PipelineStore(str(tmp_path / "test.db"))
        store.import_preset(str(preset_file))

        # Should use filename as name
        loaded = store.load("preset")
        assert loaded is not None
        assert loaded['global_threshold'] == 80.0

    def test_import_preset_custom_name(self, tmp_path, preset_file):
        """Test importing with custom name."""
        store = PipelineStore(str(tmp_path / "test.db"))
        store.import_preset(str(preset_file), name="custom_name")

        loaded = store.load("custom_name")
        assert loaded is not None

    def test_import_preset_preserves_config(self, tmp_path, preset_file):
        """Test that import preserves exact configuration."""
        store = PipelineStore(str(tmp_path / "test.db"))

        # Load original
        with open(preset_file) as f:
            original = json.load(f)

        # Import and reload
        store.import_preset(str(preset_file))
        loaded = store.load("preset")

        assert loaded == original


class TestPipelineStoreIntegration:
    """Integration tests for complete workflows."""

    def test_save_load_roundtrip(self, tmp_path):
        """Test complete save/load roundtrip."""
        store = PipelineStore(str(tmp_path / "test.db"))

        original_config = {
            'steps': [
                {'algorithm': 'frame_hash', 'weight': 0.5, 'threshold': 80},
                {'algorithm': 'ssim', 'weight': 0.5, 'threshold': 75}
            ],
            'global_threshold': 77.0,
            'pre_validators': [
                {'type': 'LengthValidator', 'config': {'tolerance_percent': 10.0}}
            ],
            'analyze_duration': 120.0
        }

        # Save
        store.save("roundtrip", original_config, "Roundtrip test")

        # Load
        loaded_config = store.load("roundtrip")

        # Verify exact match
        assert loaded_config == original_config

    def test_export_import_roundtrip(self, tmp_path):
        """Test export/import roundtrip."""
        store = PipelineStore(str(tmp_path / "test.db"))

        config = {'steps': [{'algorithm': 'frame_hash', 'weight': 1.0}]}
        store.save("original", config)

        # Export
        export_path = tmp_path / "exported.json"
        store.export_preset("original", str(export_path))

        # Import with new name
        store.import_preset(str(export_path), name="imported")

        # Verify both have same config
        original_loaded = store.load("original")
        imported_loaded = store.load("imported")

        assert original_loaded == imported_loaded
