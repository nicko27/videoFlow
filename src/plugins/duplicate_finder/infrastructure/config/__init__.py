"""Configuration module for duplicate_finder plugin.

This module exports configuration constants, settings, and design system.
"""

from .constants import (
    Paths,
    VideoComparison,
    Strategy3Verification,
    AudioFingerprinting,
    Performance,
    Timeouts,
)
from .design_system import Colors, Spacing, Typography, Styles, SimpleTheme, get_current_theme, get_status_colors
from .audio_config import AudioFirstConfig
from .layouts import LayoutManager, LayoutType
from .keyboard_shortcuts import KeyboardShortcuts
from .settings_manager import SettingsManager
from .profile_manager import ProfileManager, ConfigProfile, get_profile_manager

__all__ = [
    'Paths',
    'VideoComparison',
    'Strategy3Verification',
    'AudioFingerprinting',
    'Performance',
    'Timeouts',
    'Colors',
    'Spacing',
    'Typography',
    'Styles',
    'SimpleTheme',
    'get_current_theme',
    'get_status_colors',
    'AudioFirstConfig',
    'LayoutManager',
    'LayoutType',
    'KeyboardShortcuts',
    'SettingsManager',
    'ProfileManager',
    'ConfigProfile',
    'get_profile_manager',
]
