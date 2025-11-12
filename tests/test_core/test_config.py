"""
Tests for Configuration Module

Tests the Config class and configuration management.
"""

import pytest
from pathlib import Path
from src.core.config import Config


class TestConfig:
    """Test suite for Config class."""

    def test_app_metadata(self):
        """Test application metadata is properly set."""
        assert Config.APP_NAME == "VideoFlow"
        assert Config.APP_VERSION is not None
        assert Config.APP_AUTHOR is not None
        assert len(Config.APP_VERSION) > 0

    def test_directory_paths(self):
        """Test that all directory paths are defined."""
        assert Config.BASE_DIR.exists()
        assert Config.SRC_DIR.exists()
        assert Config.DATA_DIR is not None
        assert Config.LOGS_DIR is not None
        assert Config.PLUGINS_DIR.exists()

    def test_ensure_directories(self):
        """Test that ensure_directories creates necessary directories."""
        Config.ensure_directories()

        assert Config.DATA_DIR.exists()
        assert Config.LOGS_DIR.exists()
        assert Config.RESOURCES_DIR.exists()

    def test_plugin_configurations(self):
        """Test that plugin configurations are properly defined."""
        # Test duplicate finder config
        dup_config = Config.DUPLICATE_FINDER
        assert 'default_hash_method' in dup_config
        assert 'frame_positions' in dup_config
        assert isinstance(dup_config['frame_positions'], list)
        assert len(dup_config['frame_positions']) > 0

        # Test video converter config
        conv_config = Config.VIDEO_CONVERTER
        assert 'codecs' in conv_config
        assert 'default_codec' in conv_config
        assert conv_config['default_codec'] in conv_config['codecs']

    def test_get_plugin_config(self):
        """Test retrieving plugin configuration."""
        # Valid plugin
        config = Config.get_plugin_config('duplicate_finder')
        assert config is not None
        assert isinstance(config, dict)
        assert len(config) > 0

        # Invalid plugin
        config = Config.get_plugin_config('nonexistent_plugin')
        assert config == {}

    def test_get_data_path(self):
        """Test data path generation."""
        path = Config.get_data_path('test_plugin', 'test_file.json')

        assert isinstance(path, Path)
        assert path.parent.exists()  # Parent should be created
        assert 'test_plugin' in str(path)
        assert 'test_file.json' in str(path)

    def test_video_configuration(self):
        """Test video processing configuration."""
        video_config = Config.VIDEO
        assert 'supported_extensions' in video_config
        assert isinstance(video_config['supported_extensions'], list)
        assert '.mp4' in video_config['supported_extensions']

    def test_performance_settings(self):
        """Test performance configuration."""
        perf_config = Config.PERFORMANCE
        assert 'max_worker_threads' in perf_config
        assert perf_config['max_worker_threads'] > 0

    def test_ffmpeg_settings(self):
        """Test FFmpeg configuration."""
        ffmpeg_config = Config.FFMPEG
        assert 'allowed_codecs' in ffmpeg_config
        assert 'allowed_presets' in ffmpeg_config
        assert 'command_timeout' in ffmpeg_config

    def test_security_settings(self):
        """Test security configuration."""
        security_config = Config.SECURITY
        assert 'validate_paths' in security_config
        assert 'sanitize_ffmpeg_params' in security_config
        assert 'use_json_over_pickle' in security_config

    def test_database_settings(self):
        """Test database configuration."""
        db_config = Config.DATABASE
        assert 'journal_mode' in db_config
        assert 'cache_size' in db_config

    def test_colors_defined(self):
        """Test that UI colors are defined."""
        colors = Config.COLORS
        assert 'background' in colors
        assert 'text' in colors
        assert 'duplicate_finder' in colors

        # All colors should be valid hex colors
        for color in colors.values():
            assert color.startswith('#')
            assert len(color) == 7  # #RRGGBB


class TestConfigUserSettings:
    """Test suite for user configuration management."""

    def test_save_and_load_user_config(self, temp_dir):
        """Test saving and loading user configuration."""
        config_file = temp_dir / 'test_config.json'

        # Save config
        test_data = {
            'setting1': 'value1',
            'setting2': 42,
            'setting3': True
        }

        # Temporarily override DATA_DIR
        original_data_dir = Config.DATA_DIR
        Config.DATA_DIR = temp_dir

        try:
            success = Config.save_user_config(test_data, 'test_config.json')
            assert success is True

            # Load config
            loaded = Config.load_user_config('test_config.json')
            assert loaded == test_data

        finally:
            Config.DATA_DIR = original_data_dir

    def test_load_nonexistent_config(self):
        """Test loading nonexistent configuration returns empty dict."""
        loaded = Config.load_user_config('nonexistent_file.json')
        assert loaded == {}

    def test_save_invalid_config(self, temp_dir):
        """Test saving invalid data."""
        # Temporarily override DATA_DIR to non-writable location
        original_data_dir = Config.DATA_DIR
        Config.DATA_DIR = Path('/invalid/path/that/does/not/exist')

        try:
            success = Config.save_user_config({'key': 'value'})
            assert success is False
        finally:
            Config.DATA_DIR = original_data_dir
