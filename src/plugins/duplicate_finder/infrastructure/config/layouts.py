"""
Layout system - Dashboard View only.

This module provides the Dashboard layout for the duplicate finder.
"""

from enum import Enum
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter
)
from PyQt6.QtCore import Qt


class LayoutType(Enum):
    """Available layout types."""
    DASHBOARD = "dashboard"


class LayoutManager:
    """Manages UI layout configuration."""

    def __init__(self):
        self.current_layout = LayoutType.DASHBOARD

    def create_layout(
        self,
        layout_type: LayoutType,
        left_panel: QWidget,
        right_panel: QWidget,
        header: QWidget = None
    ) -> QWidget:
        """
        Create the Dashboard layout with the given panels.

        Args:
            layout_type: The type of layout to create (only DASHBOARD supported)
            left_panel: Panel with settings/controls
            right_panel: Panel with file list and progress
            header: Optional header widget (unused, kept for compatibility)

        Returns:
            QWidget containing the arranged panels
        """
        return self._create_dashboard_layout(left_panel, right_panel, header)

    def _create_dashboard_layout(
        self,
        left_panel: QWidget,
        right_panel: QWidget,
        header: QWidget = None
    ) -> QWidget:
        """
        Dashboard layout: Balanced view with adjustable panels.

        [Header (optional)            ]
        [Left Panel (50%) | Right Panel (50%)]

        This layout provides balanced space for both configuration controls
        and progress widgets. Users can adjust the splitter manually.
        The left panel has a minimum width of 500px for readability.
        """
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Add header if provided
        if header:
            main_layout.addWidget(header)

        # Horizontal splitter with different proportions
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Set minimum width for left panel (instead of maximum)
        # This allows the panel to grow with larger screens
        left_panel.setMinimumWidth(500)  # At least 500px for readability

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        # Set proportions: 50-50 by default (user can adjust via splitter)
        # This gives much more space for tabs, buttons, and controls
        splitter.setSizes([600, 600])
        splitter.setStretchFactor(0, 2)  # Left panel can stretch
        splitter.setStretchFactor(1, 3)  # Right panel stretches a bit more

        main_layout.addWidget(splitter, stretch=1)

        return container
