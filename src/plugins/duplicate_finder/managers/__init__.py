"""
Managers module for duplicate finder.

This module contains manager classes for handling application state and settings.
"""

from .settings_manager import SettingsManager
from .unified_config_manager import UnifiedConfigManager, UnifiedConfig
from .pipeline_manager import PipelineManager
from .test_set_manager import TestSetManager
from .benchmark_manager import BenchmarkManager, BenchmarkRunner
from .progress_manager import ProgressManager, ProgressState, get_progress_manager
from .profile_manager import ProfileManager, ConfigProfile, get_profile_manager
from .filter_manager import FilterManager, FilterCriteria, get_filter_manager

__all__ = [
    'SettingsManager',
    'UnifiedConfigManager',
    'UnifiedConfig',
    'PipelineManager',
    'TestSetManager',
    'BenchmarkManager',
    'BenchmarkRunner',
    'ProgressManager',
    'ProgressState',
    'get_progress_manager',
    'ProfileManager',
    'ConfigProfile',
    'get_profile_manager',
    'FilterManager',
    'FilterCriteria',
    'get_filter_manager'
]
