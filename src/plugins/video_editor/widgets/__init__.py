"""Widgets module for Video Editor."""

from .preview_widget import PreviewWidget
from .segments_panel import SegmentsPanel
from .detection_panel import DetectionPanel
from .audio_panel import AudioPanel
from .dashboard import DashboardWidget
from .modern_toolbar import ModernToolbar, StatusBar
from .media_browser import MediaBrowser
from .inspector_panel import InspectorPanel

__all__ = [
    'PreviewWidget',
    'SegmentsPanel',
    'DetectionPanel',
    'AudioPanel',
    'DashboardWidget',
    'ModernToolbar',
    'StatusBar',
    'MediaBrowser',
    'InspectorPanel',
]
