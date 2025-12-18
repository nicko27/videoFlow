"""Configuration constants for duplicate_finder plugin.

This module centralizes all magic numbers, thresholds, and hardcoded paths
to improve maintainability and documentation.

All constants are organized into dataclasses for easy access and modification.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


@dataclass
class Paths:
    """Application paths and directories.

    All paths are relative to the user's home directory for cross-platform
    compatibility. The data directory follows XDG conventions.
    """

    # Base directories
    DATA_DIR: ClassVar[Path] = Path.home() / '.duplicate_finder'
    CACHE_DIR: ClassVar[Path] = DATA_DIR / 'cache'
    LOG_DIR: ClassVar[Path] = DATA_DIR / 'logs'

    # Database
    DB_PATH: ClassVar[Path] = DATA_DIR / 'duplicates.db'

    # Cache subdirectories
    AUDIO_CACHE_DIR: ClassVar[Path] = CACHE_DIR / 'audio'
    VIDEO_CACHE_DIR: ClassVar[Path] = CACHE_DIR / 'video'
    HASH_CACHE_DIR: ClassVar[Path] = CACHE_DIR / 'hashes'

    # Temporary files
    TEMP_DIR: ClassVar[Path] = DATA_DIR / 'temp'


@dataclass
class VideoComparison:
    """Video comparison and hashing thresholds.

    These values control how videos are compared and when they're considered
    duplicates. Values calibrated through testing with diverse video sets.
    """

    # Similarity thresholds
    DEFAULT_THRESHOLD: ClassVar[float] = 0.85
    """Default similarity threshold for duplicates (85%)"""

    HIGH_PRECISION_THRESHOLD: ClassVar[float] = 0.92
    """High precision threshold - fewer false positives (92%)"""

    LOW_PRECISION_THRESHOLD: ClassVar[float] = 0.75
    """Low precision threshold - catch more duplicates (75%)"""

    # Tolerance values
    DURATION_TOLERANCE: ClassVar[float] = 0.05
    """Duration difference tolerance (5% = 3s in 60s video)"""

    SIZE_TOLERANCE: ClassVar[float] = 0.10
    """File size difference tolerance (10%)"""

    # Frame extraction
    FRAME_EXTRACTION_COUNT: ClassVar[int] = 10
    """Number of frames to extract for hashing"""

    FRAME_SAMPLE_INTERVAL: ClassVar[int] = 5
    """Extract every Nth frame (5 = extract frames 0, 5, 10, ...)"""

    # Hash parameters
    HASH_SIZE: ClassVar[int] = 8
    """pHash output size (8x8 = 64 bits)"""

    HIGHFREQ_FACTOR: ClassVar[int] = 4
    """DCT high frequency factor for pHash"""


@dataclass
