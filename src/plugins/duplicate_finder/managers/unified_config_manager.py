"""
Unified Configuration Manager for Duplicate Finder.

This module provides a unified configuration system that replaces the fragmented
approach (SettingsManager + AudioFirstConfig + PipelineConfig) with a single,
coherent dataclass-based configuration.

Created: 2025-12-07 (Phase 2)
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from PyQt6.QtCore import QSettings
import json
from pathlib import Path


@dataclass
class VideoHashingConfig:
    """Configuration for video hashing."""
    hash_method: str = 'pHash'  # pHash, dHash, aHash
    threshold: float = 85.0  # Similarity threshold (0-100%)
    hash_workers: int = 4  # Parallel workers
    hash_timeout: int = 120  # Timeout per video (seconds)
    sample_interval: int = 500  # Frame sampling interval (ms)


@dataclass
class ComparisonConfig:
    """Configuration for video comparison."""
    algorithm: str = 'optimized'  # optimized, standard
    workers: int = 2  # Parallel comparison workers
    batch_size: int = 50  # Batch size for comparisons
    timeout: int = 300  # Timeout per comparison (seconds)
    early_exit: bool = True  # Early exit on metadata mismatch


@dataclass
class AudioFirstConfig:
    """Configuration for audio-first workflow."""
    enabled: bool = False
    threshold: float = 80.0  # Audio similarity threshold
    precision: str = 'medium'  # low, medium, high
    workers: int = 2
    cache_size_mb: int = 500

    # LSH Configuration
    lsh_enabled: bool = True
    lsh_bands: int = 20
    lsh_rows: int = 5
    lsh_no_audio_fallback: bool = True

    # Multi-Resolution Configuration
    mr_enabled: bool = True
    mr_coarse_duration: float = 10.0  # seconds
    mr_coarse_threshold: float = 70.0  # %
    mr_medium_duration: float = 3.0  # seconds
    mr_medium_threshold: float = 80.0  # %

    # Metadata Filters
    metadata_check: bool = True
    metadata_duration_tolerance: float = 5.0  # seconds
    metadata_size_ratio: float = 0.9  # 90% minimum

    # Detection Options
    flip_detection: bool = False


@dataclass
class CacheConfig:
    """Configuration for caching system."""
    video_cache_size: int = 2000  # Number of video hashes in memory
    comparison_cache_size: int = 10000  # Number of cached comparisons
    frame_cache_size: int = 100  # Number of videos with cached frames
    audio_cache_mb: int = 500  # Audio fingerprint cache (MB)
    dense_hash_cache_mb: int = 500  # Dense hash cache for subsequences (MB)


@dataclass
class SubsequenceConfig:
    """Configuration for subsequence detection."""
    enabled: bool = False
    phase1_method: str = 'dense_hash'  # dense_hash, signature_adaptive, fast_scan
    phase2_enabled: bool = True
    phase2_method: str = 'motion_analysis'  # motion_analysis, dct_only, frame_diff, multipoint
    sample_interval: float = 0.75  # seconds
    min_match_ratio: float = 0.70  # 70% minimum match
    temporal_window: int = 5  # frames
    dct_threshold: float = 75.0  # %
    sequence_threshold: float = 95.0  # %
    workers: int = 2


@dataclass
class UnifiedConfig:
    """Complete unified configuration for Duplicate Finder."""
    video_hashing: VideoHashingConfig = field(default_factory=VideoHashingConfig)
    comparison: ComparisonConfig = field(default_factory=ComparisonConfig)
    audio_first: AudioFirstConfig = field(default_factory=AudioFirstConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    subsequence: SubsequenceConfig = field(default_factory=SubsequenceConfig)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary with all configuration values
        """
        return {
            'video_hashing': asdict(self.video_hashing),
            'comparison': asdict(self.comparison),
            'audio_first': asdict(self.audio_first),
            'cache': asdict(self.cache),
            'subsequence': asdict(self.subsequence),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedConfig':
        """
        Create configuration from dictionary.

        Args:
            data: Dictionary with configuration values

        Returns:
            UnifiedConfig instance
        """
        return cls(
            video_hashing=VideoHashingConfig(**data.get('video_hashing', {})),
            comparison=ComparisonConfig(**data.get('comparison', {})),
            audio_first=AudioFirstConfig(**data.get('audio_first', {})),
            cache=CacheConfig(**data.get('cache', {})),
            subsequence=SubsequenceConfig(**data.get('subsequence', {})),
        )

    def save_to_qsettings(self, settings: QSettings):
        """
        Save configuration to QSettings (persistent).

        Args:
            settings: QSettings instance
        """
        for category, config_obj in [
            ('video_hashing', self.video_hashing),
            ('comparison', self.comparison),
            ('audio_first', self.audio_first),
            ('cache', self.cache),
            ('subsequence', self.subsequence),
        ]:
            settings.beginGroup(category)
            for key, value in asdict(config_obj).items():
                settings.setValue(key, value)
            settings.endGroup()

    @classmethod
    def load_from_qsettings(cls, settings: QSettings) -> 'UnifiedConfig':
        """
        Load configuration from QSettings.

        Args:
            settings: QSettings instance

        Returns:
            UnifiedConfig instance
        """
        config = cls()

        for category, config_obj in [
            ('video_hashing', config.video_hashing),
            ('comparison', config.comparison),
            ('audio_first', config.audio_first),
            ('cache', config.cache),
            ('subsequence', config.subsequence),
        ]:
            settings.beginGroup(category)
            for key in asdict(config_obj).keys():
                value = settings.value(key)
                if value is not None:
                    # Type conversion based on current value type
                    current = getattr(config_obj, key)
                    if isinstance(current, bool):
                        value = value in ['true', 'True', True, 1, '1']
                    elif isinstance(current, int):
                        value = int(value)
                    elif isinstance(current, float):
                        value = float(value)
                    setattr(config_obj, key, value)
            settings.endGroup()

        return config

    def export_to_json(self, file_path: str):
        """
        Export configuration to JSON file.

        Args:
            file_path: Path to JSON file
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def import_from_json(cls, file_path: str) -> 'UnifiedConfig':
        """
        Import configuration from JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            UnifiedConfig instance
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


class UnifiedConfigManager:
    """
    Manages unified configuration with persistence and UI synchronization.

    This manager provides:
    - Load/save from UI widgets
    - Apply configuration to UI
    - Persistence via QSettings
    - Import/export to JSON
    """

    def __init__(self, settings_manager):
        """
        Initialize configuration manager.

        Args:
            settings_manager: Legacy SettingsManager instance (for compatibility)
        """
        self.settings_manager = settings_manager
        self.config = UnifiedConfig()

    def load_from_ui(self, main_window) -> UnifiedConfig:
        """
        Extract configuration from UI widgets.

        Args:
            main_window: DuplicateFinderWindow instance

        Returns:
            Updated UnifiedConfig
        """
        # Video Hashing
        if main_window.hash_method_combo:
            self.config.video_hashing.hash_method = main_window.hash_method_combo.currentData() or 'pHash'
        if main_window.threshold_spin:
            self.config.video_hashing.threshold = main_window.threshold_spin.value()
        if main_window.hash_workers_spin:
            self.config.video_hashing.hash_workers = main_window.hash_workers_spin.value()
        if main_window.hash_timeout_spin:
            self.config.video_hashing.hash_timeout = main_window.hash_timeout_spin.value()

        # Comparison
        if main_window.comparison_workers_spin:
            self.config.comparison.workers = main_window.comparison_workers_spin.value()
        if main_window.batch_size_spin:
            self.config.comparison.batch_size = main_window.batch_size_spin.value()
        if main_window.comparison_timeout_spin:
            self.config.comparison.timeout = main_window.comparison_timeout_spin.value()

        # Audio-First
        if hasattr(main_window, 'audio_threshold_spin') and main_window.audio_threshold_spin:
            self.config.audio_first.threshold = main_window.audio_threshold_spin.value()
        if hasattr(main_window, 'audio_precision_combo') and main_window.audio_precision_combo:
            self.config.audio_first.precision = main_window.audio_precision_combo.currentData() or 'medium'
        if hasattr(main_window, 'audio_workers_spin') and main_window.audio_workers_spin:
            self.config.audio_first.workers = main_window.audio_workers_spin.value()
        if hasattr(main_window, 'audio_cache_size_spin') and main_window.audio_cache_size_spin:
            self.config.audio_first.cache_size_mb = main_window.audio_cache_size_spin.value()

        # LSH
        if hasattr(main_window, 'enable_lsh_check') and main_window.enable_lsh_check:
            self.config.audio_first.lsh_enabled = main_window.enable_lsh_check.isChecked()
        if hasattr(main_window, 'lsh_bands_spin') and main_window.lsh_bands_spin:
            self.config.audio_first.lsh_bands = main_window.lsh_bands_spin.value()
        if hasattr(main_window, 'lsh_rows_spin') and main_window.lsh_rows_spin:
            self.config.audio_first.lsh_rows = main_window.lsh_rows_spin.value()

        # Multi-Resolution
        if hasattr(main_window, 'enable_mr_check') and main_window.enable_mr_check:
            self.config.audio_first.mr_enabled = main_window.enable_mr_check.isChecked()
        if hasattr(main_window, 'mr_coarse_duration_spin') and main_window.mr_coarse_duration_spin:
            self.config.audio_first.mr_coarse_duration = main_window.mr_coarse_duration_spin.value()
        if hasattr(main_window, 'mr_coarse_threshold_spin') and main_window.mr_coarse_threshold_spin:
            self.config.audio_first.mr_coarse_threshold = main_window.mr_coarse_threshold_spin.value()

        # Metadata
        if hasattr(main_window, 'enable_metadata_check') and main_window.enable_metadata_check:
            self.config.audio_first.metadata_check = main_window.enable_metadata_check.isChecked()
        if hasattr(main_window, 'metadata_duration_tolerance_spin') and main_window.metadata_duration_tolerance_spin:
            self.config.audio_first.metadata_duration_tolerance = main_window.metadata_duration_tolerance_spin.value()
        if hasattr(main_window, 'metadata_size_ratio_spin') and main_window.metadata_size_ratio_spin:
            self.config.audio_first.metadata_size_ratio = main_window.metadata_size_ratio_spin.value()

        # Cache
        if hasattr(main_window, 'video_cache_size_spin') and main_window.video_cache_size_spin:
            self.config.cache.video_cache_size = main_window.video_cache_size_spin.value()
        if hasattr(main_window, 'comparison_cache_size_spin') and main_window.comparison_cache_size_spin:
            self.config.cache.comparison_cache_size = main_window.comparison_cache_size_spin.value()

        # Detection options
        if hasattr(main_window, 'enable_flip_detection') and main_window.enable_flip_detection:
            self.config.audio_first.flip_detection = main_window.enable_flip_detection.isChecked()

        return self.config

    def apply_to_ui(self, main_window):
        """
        Apply configuration to UI widgets.

        Args:
            main_window: DuplicateFinderWindow instance
        """
        # Video Hashing
        if main_window.hash_method_combo:
            index = main_window.hash_method_combo.findData(self.config.video_hashing.hash_method)
            if index >= 0:
                main_window.hash_method_combo.setCurrentIndex(index)
        if main_window.threshold_spin:
            main_window.threshold_spin.setValue(self.config.video_hashing.threshold)
        if main_window.hash_workers_spin:
            main_window.hash_workers_spin.setValue(self.config.video_hashing.hash_workers)
        if main_window.hash_timeout_spin:
            main_window.hash_timeout_spin.setValue(self.config.video_hashing.hash_timeout)

        # Comparison
        if main_window.comparison_workers_spin:
            main_window.comparison_workers_spin.setValue(self.config.comparison.workers)
        if main_window.batch_size_spin:
            main_window.batch_size_spin.setValue(self.config.comparison.batch_size)
        if main_window.comparison_timeout_spin:
            main_window.comparison_timeout_spin.setValue(self.config.comparison.timeout)

        # Audio-First (with safety checks)
        if hasattr(main_window, 'audio_threshold_spin') and main_window.audio_threshold_spin:
            main_window.audio_threshold_spin.setValue(self.config.audio_first.threshold)
        if hasattr(main_window, 'audio_workers_spin') and main_window.audio_workers_spin:
            main_window.audio_workers_spin.setValue(self.config.audio_first.workers)
        if hasattr(main_window, 'audio_cache_size_spin') and main_window.audio_cache_size_spin:
            main_window.audio_cache_size_spin.setValue(self.config.audio_first.cache_size_mb)

        # LSH
        if hasattr(main_window, 'enable_lsh_check') and main_window.enable_lsh_check:
            main_window.enable_lsh_check.setChecked(self.config.audio_first.lsh_enabled)
        if hasattr(main_window, 'lsh_bands_spin') and main_window.lsh_bands_spin:
            main_window.lsh_bands_spin.setValue(self.config.audio_first.lsh_bands)
        if hasattr(main_window, 'lsh_rows_spin') and main_window.lsh_rows_spin:
            main_window.lsh_rows_spin.setValue(self.config.audio_first.lsh_rows)

        # Multi-Resolution
        if hasattr(main_window, 'enable_mr_check') and main_window.enable_mr_check:
            main_window.enable_mr_check.setChecked(self.config.audio_first.mr_enabled)
        if hasattr(main_window, 'mr_coarse_duration_spin') and main_window.mr_coarse_duration_spin:
            main_window.mr_coarse_duration_spin.setValue(self.config.audio_first.mr_coarse_duration)
        if hasattr(main_window, 'mr_coarse_threshold_spin') and main_window.mr_coarse_threshold_spin:
            main_window.mr_coarse_threshold_spin.setValue(self.config.audio_first.mr_coarse_threshold)

        # Metadata
        if hasattr(main_window, 'enable_metadata_check') and main_window.enable_metadata_check:
            main_window.enable_metadata_check.setChecked(self.config.audio_first.metadata_check)
        if hasattr(main_window, 'metadata_duration_tolerance_spin') and main_window.metadata_duration_tolerance_spin:
            main_window.metadata_duration_tolerance_spin.setValue(self.config.audio_first.metadata_duration_tolerance)
        if hasattr(main_window, 'metadata_size_ratio_spin') and main_window.metadata_size_ratio_spin:
            main_window.metadata_size_ratio_spin.setValue(self.config.audio_first.metadata_size_ratio)

        # Cache
        if hasattr(main_window, 'video_cache_size_spin') and main_window.video_cache_size_spin:
            main_window.video_cache_size_spin.setValue(self.config.cache.video_cache_size)
        if hasattr(main_window, 'comparison_cache_size_spin') and main_window.comparison_cache_size_spin:
            main_window.comparison_cache_size_spin.setValue(self.config.cache.comparison_cache_size)

        # Detection options
        if hasattr(main_window, 'enable_flip_detection') and main_window.enable_flip_detection:
            main_window.enable_flip_detection.setChecked(self.config.audio_first.flip_detection)

    def save(self):
        """Save configuration to persistent storage (QSettings)."""
        self.config.save_to_qsettings(self.settings_manager.settings)

    def load(self):
        """Load configuration from persistent storage (QSettings)."""
        self.config = UnifiedConfig.load_from_qsettings(self.settings_manager.settings)

    def export_json(self, file_path: str):
        """
        Export configuration to JSON file.

        Args:
            file_path: Path to JSON file
        """
        self.config.export_to_json(file_path)

    def import_json(self, file_path: str):
        """
        Import configuration from JSON file.

        Args:
            file_path: Path to JSON file
        """
        self.config = UnifiedConfig.import_from_json(file_path)

    def get_audio_first_config(self):
        """
        Get AudioFirstConfig compatible object for audio_first_handler.

        Returns:
            AudioFirstConfig from audio_config module (backward compatible)
        """
        from ..audio_config import AudioFirstConfig as LegacyAudioFirstConfig

        # Convert our dataclass to legacy config
        return LegacyAudioFirstConfig(
            enabled=self.config.audio_first.enabled,
            threshold=self.config.audio_first.threshold,
            precision_mode=self.config.audio_first.precision,
            # Map other fields as needed
        )

    def migrate_from_qsettings(self, settings):
        """
        Migrate settings from old QSettings format to UnifiedConfig.

        This method imports settings from the legacy SettingsManager
        format (QSettings) and converts them to UnifiedConfig.

        Args:
            settings: QSettings object or SettingsManager instance

        Returns:
            UnifiedConfig with migrated settings

        Example:
            from PyQt6.QtCore import QSettings
            settings = QSettings('MyOrg', 'DuplicateFinder')
            config = manager.migrate_from_qsettings(settings)
        """
        logger.info("Migrating settings from QSettings format")

        try:
            # Helper to safely get value from QSettings
            def get_value(key, default, value_type=None):
                value = settings.value(key, default)
                if value_type and value is not None:
                    try:
                        return value_type(value)
                    except (ValueError, TypeError):
                        logger.warning(f"Failed to convert {key}={value} to {value_type}, using default")
                        return default
                return value

            # Migrate hashing settings
            hashing = VideoHashingConfig(
                hash_method=get_value('hash_method', 'pHash', str),
                hash_workers=get_value('hash_workers', 4, int),
                hash_timeout=get_value('hash_timeout', 60, int),
                frame_sampling_rate=get_value('frame_sampling_rate', 5, int)
            )

            # Migrate comparison settings
            comparison = ComparisonConfig(
                threshold=get_value('threshold', 0.85, float),
                comparison_workers=get_value('comparison_workers', 4, int),
                batch_size=get_value('batch_size', 100, int),
                comparison_timeout=get_value('comparison_timeout', 30, int),
                enable_metadata_filter=get_value('enable_metadata_filter', False, bool),
                enable_flip_detection=get_value('enable_flip_detection', False, bool)
            )

            # Migrate audio-first settings
            audio_first = AudioFirstConfig(
                enabled=get_value('audio_first_enabled', False, bool),
                audio_threshold=get_value('audio_threshold', 0.85, float),
                precision_mode=get_value('audio_precision_mode', 'balanced', str),
                audio_workers=get_value('audio_workers', 4, int),
                enable_no_audio_fallback=get_value('enable_no_audio_fallback', True, bool)
            )

            # Migrate cache settings
            cache = CacheConfig(
                frame_cache_size=get_value('frame_cache_size', 1000, int),
                video_cache_size=get_value('video_cache_size', 100, int),
                audio_cache_size=get_value('audio_cache_size', 100, int),
                comparison_cache_size=get_value('comparison_cache_size', 1000, int)
            )

            # Migrate subsequence settings
            subsequence = SubsequenceConfig(
                enabled=get_value('subsequence_enabled', False, bool),
                min_length=get_value('min_subsequence_length', 10, int),
                threshold=get_value('subsequence_threshold', 0.85, float),
                max_gap=get_value('max_gap', 5, int)
            )

            migrated_config = UnifiedConfig(
                hashing=hashing,
                comparison=comparison,
                audio_first=audio_first,
                cache=cache,
                subsequence=subsequence
            )

            logger.info("Settings migration completed successfully")
            return migrated_config

        except Exception as e:
            logger.error(f"Error migrating settings: {e}")
            logger.warning("Returning default configuration")
            return UnifiedConfig()

    def auto_migrate_and_save(self):
        """
        Automatically migrate from QSettings if available and save to new format.

        This is a convenience method that:
        1. Checks if old QSettings exist
        2. Migrates them to UnifiedConfig
        3. Saves the new configuration
        4. Returns the migrated config

        Returns:
            UnifiedConfig (migrated or default)
        """
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings('DuplicateFinder', 'DuplicateFinder')

            # Check if old settings exist
            if settings.contains('hash_method'):
                logger.info("Found old QSettings, performing automatic migration")
                migrated = self.migrate_from_qsettings(settings)
                self.save(migrated)
                logger.info("Migration saved successfully")
                return migrated
            else:
                logger.info("No old settings found, using defaults")
                return self.config

        except Exception as e:
            logger.error(f"Error during auto-migration: {e}")
            return self.config
