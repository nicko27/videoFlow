"""
Secure Serialization Utilities

This module provides safe serialization/deserialization methods to replace
the unsafe usage of pickle throughout the codebase.
"""

import json
import base64
import numpy as np
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


class NumpyEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles NumPy arrays and other special types.

    This allows safe serialization of NumPy arrays to JSON format.
    """

    def default(self, obj):
        """
        Convert NumPy arrays and other special types to JSON-serializable format.

        Args:
            obj: Object to serialize

        Returns:
            JSON-serializable representation
        """
        if isinstance(obj, np.ndarray):
            return {
                '__numpy_array__': True,
                'dtype': str(obj.dtype),
                'shape': obj.shape,
                'data': base64.b64encode(obj.tobytes()).decode('utf-8')
            }
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, Path):
            return str(obj)
        return super().default(obj)


def numpy_decoder(dct: Dict[str, Any]) -> Union[Dict, np.ndarray]:
    """
    Custom JSON decoder that reconstructs NumPy arrays.

    Args:
        dct: Dictionary potentially containing NumPy array data

    Returns:
        Reconstructed NumPy array or original dictionary
    """
    if '__numpy_array__' in dct:
        data = base64.b64decode(dct['data'])
        arr = np.frombuffer(data, dtype=dct['dtype'])
        return arr.reshape(dct['shape'])
    return dct


def save_json(data: Any, file_path: Union[str, Path], indent: int = 2) -> bool:
    """
    Save data to JSON file with safe serialization.

    Args:
        data: Data to serialize
        file_path: Path to save file
        indent: JSON indentation level

    Returns:
        True if successful, False otherwise
    """
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, cls=NumpyEncoder, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving JSON to {file_path}: {e}")
        return False


def load_json(file_path: Union[str, Path], default: Any = None) -> Any:
    """
    Load data from JSON file with safe deserialization.

    Args:
        file_path: Path to JSON file
        default: Default value if file doesn't exist or fails to load

    Returns:
        Deserialized data or default value
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return default

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f, object_hook=numpy_decoder)
    except Exception as e:
        print(f"Error loading JSON from {file_path}: {e}")
        return default


def serialize_hash_data(hash_data: np.ndarray) -> str:
    """
    Serialize hash data (NumPy array) to base64 string.

    This is more efficient than full JSON serialization for binary data.

    Args:
        hash_data: NumPy array containing hash data

    Returns:
        Base64-encoded string
    """
    if not isinstance(hash_data, np.ndarray):
        raise TypeError(f"Expected np.ndarray, got {type(hash_data)}")

    # Create metadata
    metadata = {
        'dtype': str(hash_data.dtype),
        'shape': hash_data.shape
    }

    # Encode array data
    array_bytes = hash_data.tobytes()
    encoded_data = base64.b64encode(array_bytes).decode('utf-8')

    # Combine metadata and data
    result = {
        'metadata': metadata,
        'data': encoded_data
    }

    return json.dumps(result)


def deserialize_hash_data(serialized: str) -> np.ndarray:
    """
    Deserialize hash data from base64 string to NumPy array.

    Args:
        serialized: Base64-encoded string from serialize_hash_data

    Returns:
        Reconstructed NumPy array
    """
    if not serialized:
        raise ValueError("Empty serialized data")

    # Parse JSON
    data = json.loads(serialized)

    # Decode array data
    array_bytes = base64.b64decode(data['data'])

    # Reconstruct array
    arr = np.frombuffer(array_bytes, dtype=data['metadata']['dtype'])
    return arr.reshape(data['metadata']['shape'])


def serialize_video_hashes(hashes: List[np.ndarray]) -> str:
    """
    Serialize a list of video frame hashes.

    Args:
        hashes: List of NumPy arrays (one per frame)

    Returns:
        JSON string containing all hashes
    """
    serialized_hashes = []
    for hash_arr in hashes:
        serialized_hashes.append({
            'dtype': str(hash_arr.dtype),
            'shape': hash_arr.shape,
            'data': base64.b64encode(hash_arr.tobytes()).decode('utf-8')
        })

    return json.dumps({'hashes': serialized_hashes})


def deserialize_video_hashes(serialized: str) -> List[np.ndarray]:
    """
    Deserialize a list of video frame hashes.

    Args:
        serialized: JSON string from serialize_video_hashes

    Returns:
        List of reconstructed NumPy arrays
    """
    if not serialized:
        return []

    data = json.loads(serialized)
    hashes = []

    for hash_data in data['hashes']:
        array_bytes = base64.b64decode(hash_data['data'])
        arr = np.frombuffer(array_bytes, dtype=hash_data['dtype'])
        hashes.append(arr.reshape(hash_data['shape']))

    return hashes


def migrate_pickle_to_json(pickle_file: Union[str, Path], json_file: Union[str, Path]) -> bool:
    """
    Migrate data from pickle file to JSON file.

    WARNING: This function still uses pickle to read the old file,
    but only for migration purposes.

    Args:
        pickle_file: Path to existing pickle file
        json_file: Path to new JSON file

    Returns:
        True if successful, False otherwise
    """
    import pickle

    try:
        pickle_path = Path(pickle_file)
        if not pickle_path.exists():
            print(f"Pickle file not found: {pickle_path}")
            return False

        # Load from pickle
        with open(pickle_path, 'rb') as f:
            data = pickle.load(f)

        # Save to JSON
        success = save_json(data, json_file)

        if success:
            print(f"Successfully migrated {pickle_path} to {json_file}")

        return success

    except Exception as e:
        print(f"Error migrating pickle to JSON: {e}")
        return False


class SafeSerializer:
    """
    Context manager for safe file serialization with atomic writes.

    This ensures that files are only written if serialization succeeds,
    preventing corruption of existing files.
    """

    def __init__(self, file_path: Union[str, Path]):
        """
        Initialize serializer.

        Args:
            file_path: Path to file to write
        """
        self.file_path = Path(file_path)
        self.temp_path = self.file_path.with_suffix(self.file_path.suffix + '.tmp')
        self.backup_path = self.file_path.with_suffix(self.file_path.suffix + '.bak')

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context manager, handling cleanup.

        If no exception occurred, atomically replace the original file.
        """
        if exc_type is None:
            # Success - atomically replace file
            try:
                # Create backup of original if it exists
                if self.file_path.exists():
                    import shutil
                    shutil.copy2(self.file_path, self.backup_path)

                # Replace original with temp
                self.temp_path.replace(self.file_path)

                # Remove backup on success
                if self.backup_path.exists():
                    self.backup_path.unlink()

            except Exception as e:
                print(f"Error during atomic write: {e}")
                # Restore from backup if available
                if self.backup_path.exists():
                    self.backup_path.replace(self.file_path)
        else:
            # Error occurred - clean up temp file
            if self.temp_path.exists():
                self.temp_path.unlink()

    def write(self, data: Any, indent: int = 2):
        """
        Write data to temporary file.

        Args:
            data: Data to serialize
            indent: JSON indentation level
        """
        with open(self.temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, cls=NumpyEncoder, indent=indent, ensure_ascii=False)


# Convenience functions for backward compatibility
def serialize_numpy_to_json(obj: Any) -> str:
    """
    Serialize NumPy arrays and other objects to JSON string.

    This is a convenience wrapper for backward compatibility.

    Args:
        obj: Object to serialize (can be np.ndarray, list of arrays, dict, etc.)

    Returns:
        JSON string
    """
    return json.dumps(obj, cls=NumpyEncoder)


def deserialize_numpy_from_json(json_str: str) -> Any:
    """
    Deserialize JSON string back to original object with NumPy arrays.

    This is a convenience wrapper for backward compatibility.

    Args:
        json_str: JSON string to deserialize

    Returns:
        Deserialized object
    """
    if not json_str:
        return None
    return json.loads(json_str, object_hook=numpy_decoder)


def safe_save(file_path: Union[str, Path], data: Any, indent: int = 2) -> bool:
    """
    Safely save data to JSON file with atomic write.

    Args:
        file_path: Path to save file
        data: Data to serialize
        indent: JSON indentation level

    Returns:
        True if successful, False otherwise
    """
    try:
        with SafeSerializer(file_path) as serializer:
            serializer.write(data, indent=indent)
        return True
    except Exception as e:
        print(f"Error in safe_save: {e}")
        return False
