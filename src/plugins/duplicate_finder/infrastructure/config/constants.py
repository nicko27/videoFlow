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

    Storage Architecture:
    - Database: ./video_duplicates.db (project root) - Managed by DatabaseConfig
    - Cache: ~/.duplicate_finder/cache/ - File-based persistent cache
    - Logs: ~/.duplicate_finder/logs/ - Application logs
    """

    # Base directories
    DATA_DIR: ClassVar[Path] = Path.home() / '.duplicate_finder'
    CACHE_DIR: ClassVar[Path] = DATA_DIR / 'cache'
    LOG_DIR: ClassVar[Path] = DATA_DIR / 'logs'

    # Database (NOTE: Actual path managed by DatabaseConfig)
    # Default: project_root/video_duplicates.db
    DB_PATH: ClassVar[Path] = DATA_DIR / 'duplicates.db'  # Legacy, use DatabaseConfig instead

    # Cache subdirectories
    AUDIO_CACHE_DIR: ClassVar[Path] = CACHE_DIR / 'audio'
    VIDEO_CACHE_DIR: ClassVar[Path] = CACHE_DIR / 'video'
    HASH_CACHE_DIR: ClassVar[Path] = CACHE_DIR / 'hashes'
    VERIFICATION_CACHE_DIR: ClassVar[Path] = CACHE_DIR / 'verification'

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


# OBSOLETE: AudioFingerprinting class removed - was never used (legacy Shazam/MFCC system deleted)
# Audio fingerprinting now uses DuplicateFlow algorithms


@dataclass
class Performance:
    """Performance and optimization parameters.

    These control parallelization, caching, and resource usage.
    """

    # Threading
    DEFAULT_HASH_WORKERS: ClassVar[int] = 4
    """Default number of parallel hash workers (CPU cores)"""

    DEFAULT_COMPARISON_WORKERS: ClassVar[int] = 8
    """Default number of parallel comparison workers"""

    MAX_WORKERS: ClassVar[int] = 16
    """Maximum number of workers allowed"""

    # Caching
    HASH_CACHE_SIZE: ClassVar[int] = 1000
    """LRU cache size for video hashes (in-memory)"""

    FRAME_CACHE_SIZE: ClassVar[int] = 100
    """LRU cache size for extracted frames"""

    AUDIO_CACHE_SIZE: ClassVar[int] = 500
    """LRU cache size for audio fingerprints"""

    # Database
    DB_POOL_SIZE: ClassVar[int] = 10
    """Database connection pool size"""

    DB_CACHE_SIZE: ClassVar[int] = 10000
    """SQLite page cache size (KB)"""

    # Memory limits
    MAX_VIDEO_SIZE_MB: ClassVar[int] = 10240
    """Maximum video file size (10 GB)"""

    MAX_AUDIO_SIZE_MB: ClassVar[int] = 1024
    """Maximum audio file size (1 GB)"""


@dataclass
class Timeouts:
    """Timeout values for long-running operations.

    Prevents hanging on corrupted/malformed files.
    All values in seconds.
    """

    # Video operations
    HASH_TIMEOUT: ClassVar[int] = 120
    """Timeout for video hash computation (2 minutes)"""

    COMPARISON_TIMEOUT: ClassVar[int] = 60
    """Timeout for single video comparison (1 minute)"""

    FRAME_EXTRACTION_TIMEOUT: ClassVar[int] = 30
    """Timeout for frame extraction (30 seconds)"""

    # Audio operations
    AUDIO_EXTRACTION_TIMEOUT: ClassVar[int] = 60
    """Timeout for audio extraction via ffmpeg (1 minute)"""

    FINGERPRINT_TIMEOUT: ClassVar[int] = 120
    """Timeout for audio fingerprint computation (2 minutes)"""

    # Scene detection
    SCENE_DETECTION_TIMEOUT: ClassVar[int] = 300
    """Timeout for scene detection (5 minutes)"""

    VERIFICATION_TIMEOUT: ClassVar[int] = 180
    """Timeout for Strategy 3 verification (3 minutes)"""

    # Database
    DB_QUERY_TIMEOUT: ClassVar[int] = 30
    """Timeout for database queries (30 seconds)"""

    # Worker shutdown
    WORKER_SHUTDOWN_TIMEOUT: ClassVar[int] = 5
    """Timeout for graceful worker shutdown (5 seconds)"""


@dataclass
class LSHIndexing:
    """LSH (Locality-Sensitive Hashing) indexing parameters.

    Used in Level 1 of advanced pipeline for fast O(N) filtering.
    """

    # MinHash parameters
    NUM_PERM: ClassVar[int] = 128
    """Number of permutations for MinHash (more = better accuracy)"""

    # LSH parameters
    THRESHOLD: ClassVar[float] = 0.80
    """Jaccard similarity threshold for LSH candidates (80%)"""

    NUM_BANDS: ClassVar[int] = 16
    """Number of bands for LSH banding (from num_perm)"""

    # Performance
    BATCH_SIZE: ClassVar[int] = 1000
    """Batch size for LSH indexing"""


# Export all constants as module-level variables for backward compatibility
# This allows: from constants import HASH_TIMEOUT instead of Timeouts.HASH_TIMEOUT

# Paths
DATA_DIR = Paths.DATA_DIR
CACHE_DIR = Paths.CACHE_DIR
LOG_DIR = Paths.LOG_DIR
DB_PATH = Paths.DB_PATH
AUDIO_CACHE_DIR = Paths.AUDIO_CACHE_DIR

# Video Comparison
DEFAULT_THRESHOLD = VideoComparison.DEFAULT_THRESHOLD
DURATION_TOLERANCE = VideoComparison.DURATION_TOLERANCE
FRAME_EXTRACTION_COUNT = VideoComparison.FRAME_EXTRACTION_COUNT

# OBSOLETE: Audio fingerprinting exports removed - AudioFingerprinting class deleted
# FAST_HOP_LENGTH, BALANCED_HOP_LENGTH, MAXIMUM_HOP_LENGTH no longer available

# Performance
DEFAULT_HASH_WORKERS = Performance.DEFAULT_HASH_WORKERS
HASH_CACHE_SIZE = Performance.HASH_CACHE_SIZE

# Timeouts
HASH_TIMEOUT = Timeouts.HASH_TIMEOUT
AUDIO_EXTRACTION_TIMEOUT = Timeouts.AUDIO_EXTRACTION_TIMEOUT
SCENE_DETECTION_TIMEOUT = Timeouts.SCENE_DETECTION_TIMEOUT
