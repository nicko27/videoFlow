"""
pytest configuration and shared fixtures for DuplicateFinder tests.

This module provides shared fixtures for testing the DuplicateFinder plugin,
including temporary databases, mock objects, and sample data.

Reference: /docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md
"""

import os
import sys
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest

# Add src to Python path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def duplicate_finder_root():
    """Return the duplicate_finder plugin directory."""
    return PROJECT_ROOT / "src" / "plugins" / "duplicate_finder"


@pytest.fixture
def temp_database():
    """Create a temporary SQLite database for testing.

    Yields a path to a temporary database file that is cleaned up after the test.

    Example:
        def test_database(temp_database):
            from src.plugins.duplicate_finder.database_manager import VideoDatabase
            db = VideoDatabase(temp_database)
            assert db is not None
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        yield db_path
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture
def temp_database_with_schema(temp_database):
    """Create a temporary database with VideoDatabase schema initialized.

    Returns a path to a database with the full schema ready for use.
    """
    from src.plugins.duplicate_finder.database_manager import VideoDatabase

    db = VideoDatabase(temp_database)
    # Schema is created in __init__, just verify it's ready
    db.close()

    return temp_database


@pytest.fixture
def mock_pipeline_manager():
    """Mock PipelineManager with 12 DuplicateFlow presets.

    Returns a mock that simulates the behavior of PipelineManager,
    including the 12 presets from DuplicateFlow.

    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (12 Presets)
    """
    mock = Mock()

    # Mock the 12 presets from DuplicateFlow
    presets = [
        "fast",
        "balanced",
        "thorough",
        "multimodal",
        "structural",
        "hybrid",
        "audio_advanced",
        "motion_intense",
        "fast_duplicates",
        "accurate_scenes",
        "intro_detector",
        "credits_detector"
    ]

    mock.list_pipelines.return_value = presets
    mock.get_pipeline.return_value = {
        'steps': [
            {'algorithm': 'frame_hash', 'weight': 0.6, 'threshold': 80},
            {'algorithm': 'color_histogram', 'weight': 0.4, 'threshold': 75}
        ],
        'global_threshold': 75.0,
        'early_termination': True
    }

    return mock


@pytest.fixture
def sample_video_paths(tmp_path):
    """Create dummy video file paths for testing.

    Returns a dict with paths to simulated video files.
    Note: These are NOT real video files, just valid paths for testing.
    """
    videos_dir = tmp_path / "videos"
    videos_dir.mkdir()

    paths = {
        'video1': str(videos_dir / "video1.mp4"),
        'video2': str(videos_dir / "video2.mp4"),
        'short': str(videos_dir / "short.mp4"),
        'long': str(videos_dir / "long.mp4"),
    }

    # Create empty files
    for path in paths.values():
        Path(path).touch()

    return paths


@pytest.fixture
def mock_video_database():
    """Mock VideoDatabase for testing without actual database.

    Returns a mock with common VideoDatabase methods configured.

    CRITICAL: This mock uses has_video(), NOT has_hash()
    Reference: CRITICAL ERROR #2 - has_hash() is obsolete
    """
    mock = Mock()

    # IMPORTANT: has_video() is the NEW method (replaces has_hash)
    mock.has_video.return_value = False
    mock.get_video_hash.return_value = None
    mock.store_video_hash.return_value = True

    # Ensure obsolete methods are NOT present
    # These should raise AttributeError if accessed
    del mock.has_hash
    del mock.compute_hash

    return mock


@pytest.fixture
def mock_qt_widget():
    """Mock Qt widget for UI testing without Qt dependency.

    Returns a mock QWidget that can be used in UI tests without
    requiring actual Qt initialization.
    """
    mock = MagicMock()
    mock.addItem = Mock()
    mock.clear = Mock()
    mock.count.return_value = 0
    mock.item.return_value = None

    return mock


@pytest.fixture
def duplicateflow_config_basic():
    """Basic DuplicateFlow pipeline configuration.

    Returns a minimal valid pipeline configuration matching
    DuplicateFlow's format.

    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Pipeline section)
    """
    return {
        'steps': [
            {
                'algorithm': 'frame_hash',
                'weight': 0.6,
                'threshold': 80,
                'params': {'hash_method': 'pHash', 'num_samples': 8}
            },
            {
                'algorithm': 'color_histogram',
                'weight': 0.4,
                'threshold': 75,
                'params': {'num_samples': 5, 'bins': (32, 32, 32)}
            }
        ],
        'global_threshold': 75.0,
        'early_termination': True,
        'early_termination_margin': 10.0
    }


@pytest.fixture
def duplicateflow_config_with_validators():
    """DuplicateFlow pipeline config with validators and partial analysis.

    Returns a configuration matching the fast_duplicates preset with
    validators and partial analysis enabled.

    Reference: docs/duplicateflow/DUPLICATEFLOW_QUICK_REFERENCE.md (Preset #9)
    """
    return {
        'steps': [
            {'algorithm': 'frame_hash', 'weight': 0.6, 'threshold': 80},
            {'algorithm': 'color_histogram', 'weight': 0.4, 'threshold': 75}
        ],
        'global_threshold': 75.0,
        'early_termination': True,
        # Validators
        'pre_validators': [
            {
                'type': 'LengthValidator',
                'config': {
                    'tolerance_percent': 5.0,
                    'tolerance_seconds': 30.0,
                    'require_both': False
                }
            }
        ],
        # Partial Analysis
        'analyze_duration': 60.0,
        'analyze_from_start': True
    }


@pytest.fixture(autouse=True)
def reset_sys_path():
    """Automatically reset sys.path after each test to prevent pollution."""
    original_path = sys.path.copy()
    yield
    sys.path = original_path


# Markers for test categorization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "critical: marks tests for critical errors (blocking bugs)"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "ui: marks tests that involve UI components"
    )
    config.addinivalue_line(
        "markers", "database: marks tests that require database access"
    )
