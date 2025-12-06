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
        Dashboard layout: Emphasizes file list with wider view.

        [Header (optional)            ]
        [Left Panel (30%) | Right Panel (70%)]

        This layout gives more space to the file list and progress widgets.
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

        # Make left panel more compact
        left_panel.setMaximumWidth(400)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        # Set proportions: left 30%, right 70%
        splitter.setSizes([300, 700])
        splitter.setStretchFactor(0, 0)  # Don't stretch left
        splitter.setStretchFactor(1, 1)  # Stretch right panel

        main_layout.addWidget(splitter, stretch=1)

        return container
