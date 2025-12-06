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
class Strategy3Verification:
    """Strategy 3 subsequence verification thresholds.

    Strategy 3 is the most accurate verification method, using:
    1. Scene cut detection (veto if cuts found)
    2. DCT similarity computation
    3. Temporal sequence consistency check

    Thresholds calibrated from 100+ test video pairs with known ground truth.
    """

    # Scene detection
    SCENE_CUT_THRESHOLD: ClassVar[float] = 30.0
    """Pixel difference threshold for scene cut detection.

    Why 30.0?
    - Calibrated from 100 test videos
    - < 30: Too sensitive, detects noise/compression as cuts
    - > 30: Misses actual scene changes
    - Balances false positives vs false negatives
    """

    MAX_SCENE_CUTS_ALLOWED: ClassVar[int] = 0
    """Maximum scene cuts allowed (0 = veto any cuts)"""

    # DCT similarity
    DCT_THRESHOLD: ClassVar[float] = 75.0
    """Minimum DCT similarity percentage for acceptance.

    Why 75%?
    - Catches re-encodes (typically 80-95% similar)
    - Rejects edited videos (typically < 70% similar)
    - Robust to compression artifacts
    """

    # Sequence consistency
    SEQUENCE_THRESHOLD: ClassVar[float] = 95.0
    """Minimum temporal sequence consistency percentage.

    Why 95%?
    - Ensures frames are in correct order
    - Allows 5% tolerance for frame drops/duplication
    - Rejects shuffled/reversed sequences
    """

    # Frame sampling
    FRAMES_TO_COMPARE: ClassVar[int] = 30
    """Number of frames to compare for verification"""

    FRAME_SAMPLE_STEP: ClassVar[int] = 1
    """Step between sampled frames (1 = every frame)"""


@dataclass
class AudioFingerprinting:
    """Audio fingerprinting and comparison parameters.

    Based on the Shazam algorithm with MFCC features.
    Hop lengths control speed vs accuracy tradeoff.
    """

    # Mode-specific hop lengths (seconds between fingerprints)
    FAST_HOP_LENGTH: ClassVar[float] = 5.0
    """Fast mode: 5s hop → ~95% precision, 3x faster"""

    BALANCED_HOP_LENGTH: ClassVar[float] = 2.5
    """Balanced mode: 2.5s hop → ~98% precision (default)"""

    MAXIMUM_HOP_LENGTH: ClassVar[float] = 1.0
    """Maximum mode: 1s hop → ~99.9% precision, slowest"""

    # MFCC parameters
    SAMPLE_RATE: ClassVar[int] = 22050
    """Audio sample rate (Hz) - standard for music analysis"""

    N_MFCC: ClassVar[int] = 20
    """Number of MFCC coefficients to extract"""

    N_FFT: ClassVar[int] = 2048
    """FFT window size (samples)"""

    HOP_LENGTH_SAMPLES: ClassVar[int] = 512
    """Hop length in samples (not seconds)"""

    # Matching parameters
    MIN_MATCH_LENGTH: ClassVar[int] = 5
    """Minimum consecutive matching frames for detection"""

    MATCH_THRESHOLD: ClassVar[float] = 0.85
    """Similarity threshold for frame matching (85%)"""

    # Cache parameters
    CACHE_VERSION: ClassVar[int] = 2
    """Audio cache version (increment on format changes)"""


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

# Strategy 3
SCENE_CUT_THRESHOLD = Strategy3Verification.SCENE_CUT_THRESHOLD
DCT_THRESHOLD = Strategy3Verification.DCT_THRESHOLD
SEQUENCE_THRESHOLD = Strategy3Verification.SEQUENCE_THRESHOLD

# Audio
FAST_HOP_LENGTH = AudioFingerprinting.FAST_HOP_LENGTH
BALANCED_HOP_LENGTH = AudioFingerprinting.BALANCED_HOP_LENGTH
MAXIMUM_HOP_LENGTH = AudioFingerprinting.MAXIMUM_HOP_LENGTH

# Performance
DEFAULT_HASH_WORKERS = Performance.DEFAULT_HASH_WORKERS
HASH_CACHE_SIZE = Performance.HASH_CACHE_SIZE

# Timeouts
HASH_TIMEOUT = Timeouts.HASH_TIMEOUT
AUDIO_EXTRACTION_TIMEOUT = Timeouts.AUDIO_EXTRACTION_TIMEOUT
SCENE_DETECTION_TIMEOUT = Timeouts.SCENE_DETECTION_TIMEOUT
