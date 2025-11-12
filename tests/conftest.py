"""
Pytest Configuration and Fixtures

This module provides shared fixtures and configuration for all tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator
import numpy as np
import cv2
from PyQt6.QtWidgets import QApplication

# Ensure QApplication exists for Qt tests
_app = None


@pytest.fixture(scope='session')
def qapp():
    """
    Create QApplication for Qt tests.

    Yields:
        QApplication instance
    """
    global _app
    if _app is None:
        _app = QApplication([])
    yield _app


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for tests.

    Yields:
        Path to temporary directory

    Cleanup:
        Directory is removed after test
    """
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        if temp_path.exists():
            shutil.rmtree(temp_path)


@pytest.fixture
def temp_file(temp_dir: Path) -> Generator[Path, None, None]:
    """
    Create a temporary file for tests.

    Args:
        temp_dir: Temporary directory fixture

    Yields:
        Path to temporary file
    """
    temp_path = temp_dir / "test_file.txt"
    temp_path.write_text("test content")
    yield temp_path


@pytest.fixture
def sample_video(temp_dir: Path) -> Generator[Path, None, None]:
    """
    Create a sample video file for testing.

    Creates a 5-second video with 30 FPS (150 frames).

    Args:
        temp_dir: Temporary directory fixture

    Yields:
        Path to video file
    """
    video_path = temp_dir / "sample_video.mp4"

    # Video properties
    width, height = 640, 480
    fps = 30
    duration = 5  # seconds
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    # Create video writer
    writer = cv2.VideoWriter(
        str(video_path),
        fourcc,
        fps,
        (width, height)
    )

    try:
        # Generate frames
        num_frames = fps * duration
        for i in range(num_frames):
            # Create frame with changing color
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            # Color changes over time
            frame[:, :, 0] = int((i / num_frames) * 255)  # Blue channel
            frame[:, :, 1] = 128  # Green channel
            frame[:, :, 2] = 255 - int((i / num_frames) * 255)  # Red channel

            # Add frame number as text
            cv2.putText(
                frame,
                f"Frame {i}",
                (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2
            )

            writer.write(frame)
    finally:
        writer.release()

    yield video_path


@pytest.fixture
def multiple_videos(temp_dir: Path) -> Generator[list[Path], None, None]:
    """
    Create multiple sample video files for testing.

    Args:
        temp_dir: Temporary directory fixture

    Yields:
        List of video file paths
    """
    videos = []

    for i in range(3):
        video_path = temp_dir / f"video_{i}.mp4"

        # Create small video
        width, height = 320, 240
        fps = 30
        duration = 2
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        writer = cv2.VideoWriter(
            str(video_path),
            fourcc,
            fps,
            (width, height)
        )

        try:
            # Generate unique frames for each video
            for frame_num in range(fps * duration):
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                # Each video has different base color
                frame[:, :, i % 3] = 200
                writer.write(frame)
        finally:
            writer.release()

        videos.append(video_path)

    yield videos


@pytest.fixture
def sample_database(temp_dir: Path) -> Generator[Path, None, None]:
    """
    Create a sample SQLite database for testing.

    Args:
        temp_dir: Temporary directory fixture

    Yields:
        Path to database file
    """
    import sqlite3

    db_path = temp_dir / "test_database.db"

    # Create database with sample schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            value INTEGER
        )
    ''')

    # Insert sample data
    cursor.executemany(
        'INSERT INTO test_table (name, value) VALUES (?, ?)',
        [
            ('item1', 100),
            ('item2', 200),
            ('item3', 300),
        ]
    )

    conn.commit()
    conn.close()

    yield db_path


@pytest.fixture
def sample_json_data() -> dict:
    """
    Create sample JSON data for testing.

    Returns:
        Dictionary with sample data
    """
    return {
        'string_value': 'test',
        'int_value': 42,
        'float_value': 3.14,
        'bool_value': True,
        'list_value': [1, 2, 3],
        'dict_value': {'key': 'value'},
        'nested': {
            'level1': {
                'level2': 'deep'
            }
        }
    }


@pytest.fixture
def sample_numpy_array() -> np.ndarray:
    """
    Create sample NumPy array for testing.

    Returns:
        NumPy array
    """
    return np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.int32)


@pytest.fixture
def sample_hash_data() -> list[np.ndarray]:
    """
    Create sample hash data for testing duplicate finder.

    Returns:
        List of NumPy arrays representing frame hashes
    """
    hashes = []
    for i in range(8):
        # Create 8x8 hash matrix
        hash_matrix = np.random.randint(0, 256, (8, 8), dtype=np.uint8)
        hashes.append(hash_matrix)
    return hashes


@pytest.fixture
def mock_config(monkeypatch):
    """
    Create a mock configuration for testing.

    This fixture can be used to override Config values during tests.
    """
    from src.core.config import Config

    # Store original values
    original_data_dir = Config.DATA_DIR

    # Create temporary data directory
    temp_data = Path(tempfile.mkdtemp())
    monkeypatch.setattr(Config, 'DATA_DIR', temp_data)

    yield Config

    # Cleanup
    if temp_data.exists():
        shutil.rmtree(temp_data)


@pytest.fixture
def mock_logger(monkeypatch):
    """
    Create a mock logger for testing.

    This prevents log output during tests.
    """
    import logging

    class MockLogger:
        def debug(self, *args, **kwargs):
            pass

        def info(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            pass

        def critical(self, *args, **kwargs):
            pass

    return MockLogger()


@pytest.fixture
def video_files_structure(temp_dir: Path) -> Generator[Path, None, None]:
    """
    Create a directory structure with video files for testing.

    Structure:
        temp_dir/
            videos/
                category1/
                    video1.mp4
                    video2.mp4
                category2/
                    video3.mp4
                video4.mp4

    Args:
        temp_dir: Temporary directory fixture

    Yields:
        Path to root directory
    """
    root = temp_dir / "videos"
    root.mkdir()

    # Create directory structure
    cat1 = root / "category1"
    cat1.mkdir()

    cat2 = root / "category2"
    cat2.mkdir()

    # Create dummy video files
    (cat1 / "video1.mp4").write_bytes(b"fake video 1")
    (cat1 / "video2.mp4").write_bytes(b"fake video 2")
    (cat2 / "video3.mp4").write_bytes(b"fake video 3")
    (root / "video4.mp4").write_bytes(b"fake video 4")

    # Create some non-video files
    (cat1 / "readme.txt").write_text("readme")
    (root / "image.jpg").write_bytes(b"fake image")

    yield root


# Pytest hooks for custom behavior

def pytest_configure(config):
    """
    Configure pytest with custom settings.
    """
    # Ensure test data directory exists
    test_data_dir = Path(__file__).parent / "test_data"
    test_data_dir.mkdir(exist_ok=True)


def pytest_collection_modifyitems(config, items):
    """
    Modify test items during collection.

    Automatically mark tests based on their location and requirements.
    """
    for item in items:
        # Mark tests in test_plugins as integration tests
        if "test_plugins" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Mark tests requiring Qt
        if "Window" in item.name or "window" in item.name:
            item.add_marker(pytest.mark.qt)

        # Mark tests requiring video files
        if "video" in item.name.lower():
            item.add_marker(pytest.mark.video)


# Helper functions for tests

def assert_video_valid(video_path: Path) -> bool:
    """
    Assert that a video file is valid and can be opened.

    Args:
        video_path: Path to video file

    Returns:
        True if valid

    Raises:
        AssertionError: If video is invalid
    """
    assert video_path.exists(), f"Video file does not exist: {video_path}"
    assert video_path.suffix in ['.mp4', '.avi', '.mov', '.mkv'], \
        f"Invalid video extension: {video_path.suffix}"

    cap = cv2.VideoCapture(str(video_path))
    is_opened = cap.isOpened()
    cap.release()

    assert is_opened, f"Cannot open video file: {video_path}"
    return True


def create_test_video(path: Path, duration: int = 1, fps: int = 30,
                     width: int = 320, height: int = 240) -> Path:
    """
    Create a test video file.

    Args:
        path: Output path
        duration: Duration in seconds
        fps: Frames per second
        width: Video width
        height: Video height

    Returns:
        Path to created video
    """
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))

    try:
        for i in range(fps * duration):
            frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()

    return path
