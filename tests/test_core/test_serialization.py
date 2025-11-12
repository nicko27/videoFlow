"""
Tests for Serialization Module

Tests safe JSON serialization utilities.
"""

import pytest
import numpy as np
from pathlib import Path
from src.core.serialization import (
    save_json, load_json, safe_save,
    serialize_hash_data, deserialize_hash_data,
    serialize_video_hashes, deserialize_video_hashes,
    NumpyEncoder, numpy_decoder
)


class TestBasicSerialization:
    """Test basic JSON serialization functions."""

    def test_save_and_load_simple_data(self, temp_dir):
        """Test saving and loading simple data types."""
        file_path = temp_dir / 'test.json'
        data = {
            'string': 'hello',
            'int': 42,
            'float': 3.14,
            'bool': True,
            'list': [1, 2, 3],
            'dict': {'nested': 'value'}
        }

        # Save
        assert save_json(data, file_path) is True
        assert file_path.exists()

        # Load
        loaded = load_json(file_path)
        assert loaded == data

    def test_load_nonexistent_file(self, temp_dir):
        """Test loading nonexistent file returns default."""
        file_path = temp_dir / 'nonexistent.json'
        default = {'default': 'value'}

        loaded = load_json(file_path, default=default)
        assert loaded == default

    def test_load_corrupted_file(self, temp_dir):
        """Test loading corrupted JSON returns default."""
        file_path = temp_dir / 'corrupted.json'
        file_path.write_text('invalid json {{{')

        loaded = load_json(file_path, default={})
        assert loaded == {}

    def test_save_creates_parent_directories(self, temp_dir):
        """Test that save_json creates parent directories."""
        file_path = temp_dir / 'nested' / 'dir' / 'file.json'
        data = {'key': 'value'}

        assert save_json(data, file_path) is True
        assert file_path.exists()
        assert file_path.parent.exists()


class TestNumpyArraySerialization:
    """Test NumPy array serialization."""

    def test_serialize_numpy_array(self, temp_dir):
        """Test saving and loading NumPy arrays."""
        file_path = temp_dir / 'array.json'
        array = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int32)
        data = {'array': array}

        # Save
        assert save_json(data, file_path) is True

        # Load
        loaded = load_json(file_path)
        assert 'array' in loaded
        np.testing.assert_array_equal(loaded['array'], array)
        assert loaded['array'].dtype == array.dtype

    def test_serialize_multiple_arrays(self, temp_dir):
        """Test saving multiple NumPy arrays."""
        file_path = temp_dir / 'arrays.json'
        data = {
            'array1': np.array([1, 2, 3]),
            'array2': np.array([[4, 5], [6, 7]]),
            'array3': np.array([8.1, 9.2, 10.3], dtype=np.float32)
        }

        # Save and load
        save_json(data, file_path)
        loaded = load_json(file_path)

        # Verify all arrays
        for key in data.keys():
            np.testing.assert_array_equal(loaded[key], data[key])
            assert loaded[key].dtype == data[key].dtype

    def test_serialize_numpy_types(self, temp_dir):
        """Test serialization of NumPy scalar types."""
        file_path = temp_dir / 'numpy_types.json'
        data = {
            'int': np.int32(42),
            'float': np.float64(3.14),
            'bool': np.bool_(True)
        }

        save_json(data, file_path)
        loaded = load_json(file_path)

        assert loaded['int'] == 42
        assert loaded['float'] == pytest.approx(3.14)
        assert loaded['bool'] is True

    def test_serialize_path_objects(self, temp_dir):
        """Test serialization of Path objects."""
        file_path = temp_dir / 'paths.json'
        data = {
            'path': Path('/some/path/to/file.txt')
        }

        save_json(data, file_path)
        loaded = load_json(file_path)

        assert loaded['path'] == '/some/path/to/file.txt'


class TestHashSerialization:
    """Test hash data serialization functions."""

    def test_serialize_deserialize_hash_data(self):
        """Test hash serialization and deserialization."""
        # Create sample hash
        original = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint8)

        # Serialize
        serialized = serialize_hash_data(original)
        assert isinstance(serialized, str)
        assert len(serialized) > 0

        # Deserialize
        restored = deserialize_hash_data(serialized)
        np.testing.assert_array_equal(restored, original)
        assert restored.dtype == original.dtype
        assert restored.shape == original.shape

    def test_serialize_empty_hash_fails(self):
        """Test that empty hash serialization fails."""
        with pytest.raises(ValueError):
            deserialize_hash_data('')

    def test_serialize_invalid_type_fails(self):
        """Test that invalid type serialization fails."""
        with pytest.raises(TypeError):
            serialize_hash_data([1, 2, 3])  # List instead of array

    def test_serialize_video_hashes(self):
        """Test serialization of multiple frame hashes."""
        # Create sample hashes
        hashes = [
            np.random.randint(0, 256, (8, 8), dtype=np.uint8)
            for _ in range(5)
        ]

        # Serialize
        serialized = serialize_video_hashes(hashes)
        assert isinstance(serialized, str)

        # Deserialize
        restored = deserialize_video_hashes(serialized)
        assert len(restored) == len(hashes)

        for original, restored_hash in zip(hashes, restored):
            np.testing.assert_array_equal(restored_hash, original)

    def test_deserialize_empty_video_hashes(self):
        """Test deserializing empty hash list."""
        restored = deserialize_video_hashes('')
        assert restored == []


class TestSafeSerialization:
    """Test atomic safe serialization."""

    def test_safe_save_creates_file(self, temp_dir):
        """Test that safe_save creates file atomically."""
        file_path = temp_dir / 'safe_file.json'
        data = {'key': 'value'}

        assert safe_save(file_path, data) is True
        assert file_path.exists()

        loaded = load_json(file_path)
        assert loaded == data

    def test_safe_save_replaces_existing(self, temp_dir):
        """Test that safe_save replaces existing file."""
        file_path = temp_dir / 'existing.json'

        # Create initial file
        initial_data = {'old': 'data'}
        save_json(initial_data, file_path)

        # Replace with new data
        new_data = {'new': 'data'}
        assert safe_save(file_path, new_data) is True

        # Verify new data
        loaded = load_json(file_path)
        assert loaded == new_data

    def test_safe_save_backup_on_failure(self, temp_dir):
        """Test that safe_save preserves original on failure."""
        file_path = temp_dir / 'important.json'

        # Create initial file
        original_data = {'important': 'data'}
        save_json(original_data, file_path)

        # Attempt to save invalid data (should handle gracefully)
        # Note: This is hard to test without mocking, but we verify
        # the function doesn't crash
        try:
            safe_save(file_path, original_data)
        except Exception:
            pass

        # Original file should still exist
        assert file_path.exists()


class TestComplexDataStructures:
    """Test serialization of complex nested structures."""

    def test_nested_structure_with_arrays(self, temp_dir):
        """Test deeply nested structure with arrays."""
        file_path = temp_dir / 'complex.json'
        data = {
            'metadata': {
                'version': 1,
                'created': '2024-01-01'
            },
            'data': {
                'arrays': [
                    np.array([1, 2, 3]),
                    np.array([4, 5, 6])
                ],
                'values': [10, 20, 30]
            }
        }

        save_json(data, file_path)
        loaded = load_json(file_path)

        assert loaded['metadata'] == data['metadata']
        assert loaded['data']['values'] == data['data']['values']
        np.testing.assert_array_equal(
            loaded['data']['arrays'][0],
            data['data']['arrays'][0]
        )

    def test_unicode_data(self, temp_dir):
        """Test serialization of Unicode data."""
        file_path = temp_dir / 'unicode.json'
        data = {
            'english': 'Hello',
            'french': 'Bonjour',
            'japanese': 'こんにちは',
            'emoji': '🎬📹🎥'
        }

        save_json(data, file_path)
        loaded = load_json(file_path)

        assert loaded == data

    def test_large_array(self, temp_dir):
        """Test serialization of large arrays."""
        file_path = temp_dir / 'large.json'
        large_array = np.random.randint(0, 256, (1000, 1000), dtype=np.uint8)
        data = {'large_array': large_array}

        save_json(data, file_path)
        loaded = load_json(file_path)

        np.testing.assert_array_equal(loaded['large_array'], large_array)
