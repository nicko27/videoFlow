"""Pytest configuration and shared fixtures.

This module provides common fixtures and configuration for all tests.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest
import numpy as np

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files.

    Yields:
        Path to temporary directory

    Cleanup:
        Automatically removed after test
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_database(temp_dir):
    """Create a mock database for testing.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Mock database manager instance
    """
    from src.plugins.duplicate_finder.database_manager import DatabaseManager

    db_path = temp_dir / "test_duplicates.db"
    db = DatabaseManager(str(db_path))
    yield db
    # Cleanup handled by temp_dir


@pytest.fixture
def sample_hash() -> np.ndarray:
    """Create a sample perceptual hash for testing.

    Returns:
        64-element numpy array (simulating pHash output)
    """
    return np.random.randint(0, 2, size=64, dtype=np.uint8)


@pytest.fixture
def similar_hash(sample_hash) -> np.ndarray:
    """Create a hash similar to sample_hash (90% match).

    Args:
        sample_hash: The base hash to create a similar version of

    Returns:
        64-element numpy array with 90% similarity to sample_hash
    """
    similar = sample_hash.copy()
    # Flip 10% of bits (6-7 bits) to get ~90% similarity
    num_flips = 6
    flip_indices = np.random.choice(64, size=num_flips, replace=False)
    similar[flip_indices] = 1 - similar[flip_indices]
    return similar


@pytest.fixture
def different_hash() -> np.ndarray:
    """Create a hash completely different from sample_hash.

    Returns:
        64-element numpy array with low similarity to sample_hash
    """
    return np.random.randint(0, 2, size=64, dtype=np.uint8)


@pytest.fixture
def mock_video_path(temp_dir) -> str:
    """Create a mock video file path (file doesn't need to exist for some tests).

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        String path to mock video file
    """
    return str(temp_dir / "test_video.mp4")


@pytest.fixture
def sample_video_metadata() -> dict:
    """Create sample video metadata for testing.

    Returns:
        Dictionary with typical video metadata
    """
    return {
        'duration': 120.5,  # seconds
        'fps': 30.0,
        'width': 1920,
        'height': 1080,
        'codec': 'h264',
        'bitrate': 5000000,  # 5 Mbps
        'file_size': 75000000,  # ~75 MB
    }


@pytest.fixture
def sample_audio_fingerprint() -> np.ndarray:
    """Create a sample audio fingerprint for testing.

    Returns:
        2D numpy array (time x features) simulating MFCC fingerprints
    """
    # Simulate 100 time frames x 20 MFCC features
    return np.random.randn(100, 20).astype(np.float32)
