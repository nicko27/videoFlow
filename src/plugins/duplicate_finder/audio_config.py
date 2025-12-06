"""
Configuration manager for audio-first duplicate detection.

This module centralizes all configuration parameters for the audio-first
detection pipeline including audio fingerprinting, LSH, multi-resolution
comparison, metadata filtering, and selective video hashing.
"""
from dataclasses import dataclass
from typing import Optional
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.AudioConfig')


@dataclass
class AudioFingerprintConfig:
    """Configuration for audio fingerprinting."""
    enabled: bool = True
    threshold: float = 70.0  # Similarity threshold (50-95%)
    precision_mode: str = 'fast'  # 'fast', 'balanced', 'maximum'
    workers: int = 4  # Number of parallel workers
    cache_size: int = 1000  # Max items in memory cache
    fallback_enabled: bool = True  # Enable fallback for no-audio videos


@dataclass
class LSHConfig:
    """Configuration for Locality Sensitive Hashing."""
    enabled: bool = True
    bands: int = 20  # Number of LSH bands (10-50)
    rows_per_band: int = 5  # Rows per band (3-10)
    use_for_no_audio: bool = True  # Apply LSH to no-audio videos


@dataclass
class MultiResolutionConfig:
    """Configuration for multi-resolution audio comparison."""
    enabled: bool = True
    coarse_duration: int = 30  # Seconds for coarse test (10-60)
    coarse_threshold: float = 60.0  # Threshold for coarse test (50-80%)
    medium_duration: int = 120  # Seconds for medium test (60-300)
    medium_threshold: float = 65.0  # Threshold for medium test (55-85%)


@dataclass
class MetadataFilterConfig:
    """Configuration for optional metadata filtering."""
    enabled: bool = False  # Disabled by default (can create false negatives)
    duration_tolerance: float = 0.05  # 5% tolerance
    min_size_ratio: float = 0.90  # 90% minimum size ratio


@dataclass
class VideoHashConfig:
    """Configuration for selective video hashing."""
    method: str = 'pHash'  # 'pHash', 'dHash', 'aHash'
    workers: int = 4
    timeout: int = 120  # seconds
    cache_size: int = 2000


@dataclass
class VideoComparisonConfig:
    """Configuration for video comparison."""
    threshold: float = 90.0  # Similarity threshold (70-99%)
    flip_detection: bool = True  # Detect horizontal flips
    workers: int = 8
    batch_size: int = 100
    timeout: int = 30  # seconds
    cache_size: int = 10000


@dataclass
class AudioFirstConfig:
    """Complete configuration for audio-first pipeline."""
    audio: AudioFingerprintConfig
    lsh: LSHConfig
    multi_resolution: MultiResolutionConfig
    metadata: MetadataFilterConfig
    video_hash: VideoHashConfig
    video_comparison: VideoComparisonConfig

    @classmethod
    def from_ui_widgets(cls, params_tab) -> 'AudioFirstConfig':
        """
        Create configuration from UI parameter widgets.

        Args:
            params_tab: The parameters tab widget containing all spinboxes/checkboxes.

        Returns:
            Complete AudioFirstConfig instance.
        """
        # Audio fingerprinting
        audio = AudioFingerprintConfig(
            enabled=True,  # Always enabled for audio-first approach
            threshold=params_tab.audio_threshold_spin.value(),
            precision_mode=params_tab.audio_precision_combo.currentData(),
            workers=params_tab.audio_workers_spin.value(),
            cache_size=params_tab.audio_cache_size_spin.value(),
            fallback_enabled=params_tab.enable_no_audio_fallback.isChecked()
        )

        # LSH
        lsh = LSHConfig(
            enabled=params_tab.enable_lsh_check.isChecked(),
            bands=params_tab.lsh_bands_spin.value(),
            rows_per_band=params_tab.lsh_rows_spin.value(),
            use_for_no_audio=params_tab.enable_lsh_no_audio.isChecked()
        )

        # Multi-resolution
        multi_resolution = MultiResolutionConfig(
            enabled=params_tab.enable_mr_check.isChecked(),
            coarse_duration=params_tab.mr_coarse_duration_spin.value(),
            coarse_threshold=params_tab.mr_coarse_threshold_spin.value(),
            medium_duration=params_tab.mr_medium_duration_spin.value(),
            medium_threshold=params_tab.mr_medium_threshold_spin.value()
        )

        # Metadata filter
        metadata = MetadataFilterConfig(
            enabled=params_tab.enable_metadata_check.isChecked(),
            duration_tolerance=params_tab.metadata_duration_tolerance_spin.value(),
            min_size_ratio=params_tab.metadata_size_ratio_spin.value()
        )

        # Video hashing
        video_hash = VideoHashConfig(
            method=params_tab.hash_method_combo.currentData(),
            workers=params_tab.hash_workers_spin.value(),
            timeout=params_tab.hash_timeout_spin.value(),
            cache_size=params_tab.video_cache_size_spin.value()
        )

        # Video comparison
        video_comparison = VideoComparisonConfig(
            threshold=params_tab.video_threshold_spin.value(),
            flip_detection=params_tab.enable_flip_detection.isChecked(),
            workers=params_tab.comparison_workers_spin.value(),
            batch_size=params_tab.batch_size_spin.value(),
            timeout=params_tab.comparison_timeout_spin.value(),
            cache_size=params_tab.comparison_cache_size_spin.value()
        )

        config = cls(
            audio=audio,
            lsh=lsh,
            multi_resolution=multi_resolution,
            metadata=metadata,
            video_hash=video_hash,
            video_comparison=video_comparison
        )

        logger.info("Audio-first configuration loaded from UI")
        logger.debug(f"Audio threshold: {audio.threshold}%, "
                    f"LSH: {lsh.enabled}, "
                    f"Multi-res: {multi_resolution.enabled}, "
                    f"Metadata: {metadata.enabled}")

        return config

    def to_dict(self) -> dict:
        """Convert configuration to dictionary for logging/debugging."""
        return {
            'audio': {
                'threshold': self.audio.threshold,
                'precision': self.audio.precision_mode,
                'workers': self.audio.workers
            },
            'lsh': {
                'enabled': self.lsh.enabled,
                'bands': self.lsh.bands,
                'rows': self.lsh.rows_per_band
            },
            'multi_resolution': {
                'enabled': self.multi_resolution.enabled,
                'coarse_threshold': self.multi_resolution.coarse_threshold
            },
            'video': {
                'method': self.video_hash.method,
                'threshold': self.video_comparison.threshold,
                'flip_detection': self.video_comparison.flip_detection
            }
        }
