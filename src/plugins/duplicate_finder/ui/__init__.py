"""
UI components module for duplicate finder.

This module contains UI panel and widget creation utilities.
"""

from .panels import UIPanels
from .widget_registry import WidgetRegistry, get_widget_registry
from .settings_dialog import SettingsDialog
from .dashboard_view import DashboardView
from .cluster_view_dialog import ClusterViewDialog
from .smart_filters import SmartFiltersWidget
from .report_dialog import ReportDialog
from .themes import Theme, ThemeType

__all__ = ['UIPanels', 'WidgetRegistry', 'get_widget_registry', 'SettingsDialog', 'DashboardView', 'ClusterViewDialog', 'SmartFiltersWidget', 'ReportDialog', 'Theme', 'ThemeType']
