"""
Pytest configuration and fixtures for DuplicateFlow tests.

This module provides common fixtures and configuration for all tests.
"""

import pytest
import sys
from pathlib import Path
from rich.console import Console
from io import StringIO

# Add duplicateflow to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def console():
    """
    Fixture that provides a Rich Console for testing.

    Uses a StringIO buffer to capture output instead of writing to stdout.
    """
    string_io = StringIO()
    return Console(file=string_io, force_terminal=True, width=120)


@pytest.fixture
def null_console():
    """
    Fixture that provides a Rich Console with no output.

    Useful for tests that don't need to verify output.
    """
    return Console(file=StringIO(), quiet=True)


@pytest.fixture
def sample_video_files():
    """
    Fixture that provides sample video file paths for testing.

    Returns:
        List of Path objects representing sample video files
    """
    return [
        Path("/videos/movie1.mp4"),
        Path("/videos/movie2.mkv"),
        Path("/videos/series/episode1.avi"),
    ]


@pytest.fixture
def sample_table_data():
    """
    Fixture that provides sample table data for testing.

    Returns:
        Tuple of (headers, rows) for table display
    """
    headers = ["File", "Size", "Duration"]
    rows = [
        ["movie1.mp4", "1.2 GB", "01:45:30"],
        ["movie2.mkv", "890 MB", "00:42:15"],
        ["episode1.avi", "350 MB", "00:21:45"],
    ]
    return headers, rows
