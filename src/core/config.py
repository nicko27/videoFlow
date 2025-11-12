"""
VideoFlow Configuration Module

This module provides centralized configuration management for all VideoFlow components.
All hardcoded values have been extracted here for easy maintenance and customization.
"""

import os
from pathlib import Path
from typing import Dict, Any
import json


class Config:
    """
    Central configuration class for VideoFlow application.

    Provides access to all configuration settings including:
    - Application metadata
    - File paths and directories
    - Performance tuning parameters
    - UI settings
    - Plugin-specific configurations
    """

    # ==================== APPLICATION METADATA ====================
    APP_NAME = "VideoFlow"
    APP_VERSION = "1.0.0"
    APP_AUTHOR = "VideoFlow Team"
    APP_DESCRIPTION = "Professional video file management and processing suite"

    # ==================== PATHS ====================
    # Base directory (project root)
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    # Source code directory
    SRC_DIR = BASE_DIR / "src"

    # Data storage directory
    DATA_DIR = BASE_DIR / "data"

    # Logs directory
    LOGS_DIR = BASE_DIR / "logs"

    # Resources directory
    RESOURCES_DIR = BASE_DIR / "resources"

    # Plugins directory
    PLUGINS_DIR = SRC_DIR / "plugins"

    # Enone directories exist
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist."""
        for directory in [cls.DATA_DIR, cls.LOGS_DIR, cls.RESOURCES_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

    # ==================== LOGGING CONFIGURATION ====================
    LOG_LEVEL_CONSOLE = "DEBUG"
    LOG_LEVEL_FILE = "DEBUG"
    LOG_MAX_BYTES = 100 * 1024 * 1024  # 100MB
    LOG_BACKUP_COUNT = 5
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    # ==================== MAIN WINDOW UI SETTINGS ====================
    MAIN_WINDOW_TITLE = "VideoFlow - Professional Video Management Suite"
    MAIN_WINDOW_MIN_WIDTH = 900
    MAIN_WINDOW_MIN_HEIGHT = 700

    # Plugin grid layout
    PLUGIN_GRID_COLUMNS = 3
    PLUGIN_BUTTON_MIN_WIDTH = 250
    PLUGIN_BUTTON_MIN_HEIGHT = 120
    PLUGIN_BUTTON_MAX_HEIGHT = 150

    # UI Colors
    COLORS = {
        'background': '#1e1e1e',
        'card_background': '#2d2d2d',
        'text': '#ffffff',
        'text_secondary': '#cccccc',
        'border': '#404040',
        'hover': '#3d3d3d',
        'pressed': '#1a1a1a',

        # Plugin-specific colors
        'duplicate_finder': '#e74c3c',
        'copy_manager': '#3498db',
        'video_converter': '#2ecc71',
        'video_editor': '#f39c12',
        'video_merger': '#9b59b6',
    }

    # ==================== DUPLICATE FINDER CONFIGURATION ====================
    DUPLICATE_FINDER = {
        # Hash computation
        'default_hash_method': 'pHash',  # Options: pHash, dHash, aHash
        'hash_size': 8,  # Hash matrix size (8x8 = 64 bits, 32x32 = 1024 bits)
        'high_freq_factor': 4,  # For advanced hash computation

        # Frame extraction positions (absolute frame numbers)
        'frame_positions': [30, 150, 300, 600, 900, 1500, 2100, 3000],

        # Performance settings
        'default_hash_workers': 4,
        'max_hash_workers': 8,
        'default_comparison_workers': 4,
        'max_comparison_workers': 8,

        # Timeouts (seconds)
        'hash_timeout': 120,
        'comparison_timeout': 30,

        # Similarity thresholds
        'similarity_threshold': 85.0,  # Minimum similarity to consider duplicate (%)
        'high_similarity_threshold': 95.0,  # Very likely duplicate

        # Batch processing
        'comparison_batch_size': 50,
        'cache_preload_batch_size': 1000,

        # Database
        'db_name': 'video_duplicates.db',
        'cache_size': 10000,  # Maximum cache entries in memory

        # UI
        'thumbnail_width': 400,
        'thumbnail_height': 300,
        'preview_update_interval_ms': 100,
    }

    # ==================== COPY MANAGER CONFIGURATION ====================
    COPY_MANAGER = {
        # Default options
        'default_copy_files': True,
        'default_copy_metadata': True,
        'default_ignore_hidden': True,
        'default_delete_after_copy': False,

        # File conflict handling
        'conflict_suffix_format': ' ({})',  # e.g., "file (1).txt"
        'max_conflict_attempts': 1000,

        # Settings file
        'settings_file': 'copy_manager/settings.json',
    }

    # ==================== VIDEO CONVERTER CONFIGURATION ====================
    VIDEO_CONVERTER = {
        # Codec options
        'codecs': ['libx264', 'libx265', 'libvpx-vp9', 'libaom-av1'],
        'default_codec': 'libx264',

        # Quality settings (CRF - lower is better)
        'quality_presets': {
            'high': 18,
            'medium': 23,
            'low': 28,
            'very_low': 32,
        },
        'default_quality': 23,

        # Speed presets
        'speed_presets': ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast',
                         'medium', 'slow', 'slower', 'veryslow'],
        'default_speed': 'medium',

        # Audio settings
        'audio_codecs': ['aac', 'mp3', 'libopus'],
        'default_audio_codec': 'aac',
        'default_audio_bitrate': '128k',

        # Resolution presets
        'resolution_presets': ['Original', '3840x2160', '1920x1080', '1280x720', '854x480'],
        'default_resolution': 'Original',

        # FPS options
        'fps_options': ['Original', '60', '30', '24'],
        'default_fps': 'Original',

        # Conversion settings
        'max_conversion_attempts': 3,
        'size_threshold_mb': 10,  # Skip files smaller than this
        'converted_suffix': '_cvt',

        # Temporary file handling
        'temp_suffix': '.tmp',

        # Settings files
        'settings_file': 'video_converter/settings.json',
        'metadata_file': 'video_converter/metadata.json',
        'stats_file': 'video_converter/stats.json',
    }

    # ==================== VIDEO EDITOR CONFIGURATION ====================
    VIDEO_EDITOR = {
        # Timeline settings
        'timeline_height': 100,
        'timeline_margin': 10,
        'segment_colors': {
            'default': '#3498db',
            'selected': '#e74c3c',
            'cut_marker': '#f39c12',
        },

        # Playback
        'default_fps': 30,
        'seek_step_frames': 1,
        'seek_step_seconds': 5,

        # Thumbnail strip
        'thumbnail_count': 10,
        'thumbnail_height': 60,

        # Export settings
        'default_export_codec': 'copy',  # No re-encoding by default
        'export_suffix': '_edited',

        # Project files
        'project_file_extension': '.vfproj',
    }

    # ==================== VIDEO MERGER CONFIGURATION ====================
    VIDEO_MERGER = {
        # Merge method
        'prefer_concat_demuxer': True,  # Fast, no re-encoding
        'fallback_to_moviepy': True,  # For incompatible videos

        # Output naming
        'default_output_name': 'merged_video',
        'default_output_extension': '.mp4',

        # Options
        'default_delete_source': False,

        # Temporary files
        'concat_list_filename': 'concat_list.txt',
    }

    # ==================== VIDEO PROCESSING SETTINGS ====================
    VIDEO = {
        # Supported formats
        'supported_extensions': [
            '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv',
            '.m4v', '.mpg', '.mpeg', '.3gp', '.webm'
        ],

        # Frame extraction
        'opencv_backend': None,  # Auto-select
        'frame_read_timeout': 5,  # seconds

        # Video info extraction
        'info_timeout': 10,  # seconds

        # Preview generation
        'preview_max_width': 800,
        'preview_max_height': 600,
    }

    # ==================== PERFORMANCE SETTINGS ====================
    PERFORMANCE = {
        # Threading
        'max_worker_threads': os.cpu_count() or 4,
        'thread_pool_timeout': 300,  # seconds

        # Memory management
        'max_cache_memory_mb': 500,
        'cache_cleanup_threshold': 0.8,  # Start cleanup at 80% full

        # Progress updates
        'progress_update_interval_ms': 100,
        'batch_progress_update': 10,  # Update every N items
    }

    # ==================== FFMPEG SETTINGS ====================
    FFMPEG = {
        # Command timeout
        'command_timeout': 3600,  # 1 hour for large files

        # Progress parsing
        'progress_pattern': r'time=(\d+):(\d+):(\d+\.\d+)',

        # Error handling
        'max_retries': 3,
        'retry_delay': 2,  # seconds

        # Validation
        'allowed_codecs': [
            'libx264', 'libx265', 'libvpx-vp9', 'libaom-av1',
            'aac', 'mp3', 'libopus', 'copy'
        ],
        'allowed_presets': [
            'ultrafast', 'superfast', 'veryfast', 'faster', 'fast',
            'medium', 'slow', 'slower', 'veryslow'
        ],
    }

    # ==================== DATABASE SETTINGS ====================
    DATABASE = {
        # SQLite settings
        'journal_mode': 'WAL',  # Write-Ahead Logging for better concurrency
        'synchronous': 'NORMAL',  # Balance between safety and speed
        'cache_size': -64000,  # 64MB cache (negative = KB)
        'temp_store': 'MEMORY',

        # Connection pooling
        'pool_size': 5,
        'max_overflow': 10,
        'pool_timeout': 30,

        # Migration settings
        'migration_backup': True,
    }

    # ==================== SECURITY SETTINGS ====================
    SECURITY = {
        # File operations
        'validate_paths': True,
        'allow_symlinks': False,
        'max_path_length': 4096,

        # Command execution
        'sanitize_ffmpeg_params': True,
        'allowed_param_chars': r'[a-zA-Z0-9\-_.:,=/]',

        # Serialization
        'use_json_over_pickle': True,  # Safer serialization
    }

    # ==================== METHODS ====================
    @classmethod
    def get_plugin_config(cls, plugin_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific plugin.

        Args:
            plugin_name: Name of the plugin (e.g., 'duplicate_finder')

        Returns:
            Dictionary containing plugin configuration
        """
        config_map = {
            'duplicate_finder': cls.DUPLICATE_FINDER,
            'copy_manager': cls.COPY_MANAGER,
            'video_converter': cls.VIDEO_CONVERTER,
            'video_editor': cls.VIDEO_EDITOR,
            'video_merger': cls.VIDEO_MERGER,
        }
        return config_map.get(plugin_name, {})

    @classmethod
    def get_data_path(cls, *parts: str) -> Path:
        """
        Get a path within the data directory.

        Args:
            *parts: Path components to join

        Returns:
            Path object
        """
        path = cls.DATA_DIR.joinpath(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def load_user_config(cls, config_file: str = 'user_config.json') -> Dict[str, Any]:
        """
        Load user-specific configuration overrides.

        Args:
            config_file: Name of the config file

        Returns:
            Dictionary of user configuration
        """
        config_path = cls.DATA_DIR / config_file
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load user config: {e}")
        return {}

    @classmethod
    def save_user_config(cls, config: Dict[str, Any], config_file: str = 'user_config.json') -> bool:
        """
        Save user-specific configuration.

        Args:
            config: Configuration dictionary to save
            config_file: Name of the config file

        Returns:
            True if successful, False otherwise
        """
        config_path = cls.DATA_DIR / config_file
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Failed to save user config: {e}")
            return False


# Initialize directories on module import
Config.ensure_directories()
