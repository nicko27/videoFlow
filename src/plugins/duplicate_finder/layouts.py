"""
Layout system for different UI arrangements.

This module provides multiple layout options for the duplicate finder:
1. Classic (default) - Left panel with settings, right panel with files
2. Vertical Compact - Everything stacked vertically
3. Dashboard - Card-based layout with real-time stats
4. Simplified - Minimal UI with focus on essential actions
"""

from enum import Enum
from typing import Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox
)
from PyQt6.QtCore import Qt


class LayoutType(Enum):
    """Available layout types."""
    CLASSIC = "classic"
    VERTICAL = "vertical"
    DASHBOARD = "dashboard"
    SIMPLIFIED = "simplified"


class LayoutManager:
    """Manages different UI layout configurations."""

    def __init__(self):
        self.current_layout = LayoutType.CLASSIC

    def get_layout_names(self) -> Dict[str, str]:
        """Get display names for all layouts."""
        return {
            LayoutType.CLASSIC.value: "Classic (Split Panel)",
            LayoutType.VERTICAL.value: "Vertical Compact",
            LayoutType.DASHBOARD.value: "Dashboard View",
            LayoutType.SIMPLIFIED.value: "Simplified"
        }

    def create_layout(
        self,
        layout_type: LayoutType,
        left_panel: QWidget,
        right_panel: QWidget,
        header: QWidget = None
    ) -> QWidget:
        """
        Create a layout with the given panels.

        Args:
            layout_type: The type of layout to create
            left_panel: Panel with settings/controls
            right_panel: Panel with file list and progress
            header: Optional header widget

        Returns:
            QWidget containing the arranged panels
        """
        if layout_type == LayoutType.CLASSIC:
            return self._create_classic_layout(left_panel, right_panel, header)
        elif layout_type == LayoutType.VERTICAL:
            return self._create_vertical_layout(left_panel, right_panel, header)
        elif layout_type == LayoutType.DASHBOARD:
            return self._create_dashboard_layout(left_panel, right_panel, header)
        elif layout_type == LayoutType.SIMPLIFIED:
            return self._create_simplified_layout(left_panel, right_panel, header)
        else:
            # Fallback to classic
            return self._create_classic_layout(left_panel, right_panel, header)

    def _create_classic_layout(
        self,
        left_panel: QWidget,
        right_panel: QWidget,
        header: QWidget = None
    ) -> QWidget:
        """
        Classic layout: Left panel (settings) | Right panel (files).

        [Header (optional)        ]
        [Left Panel | Right Panel ]
        """
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Add header if provided
        if header:
            main_layout.addWidget(header)

        # Horizontal splitter for left and right panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)  # Left panel
        splitter.setStretchFactor(1, 2)  # Right panel gets more space
        splitter.setSizes([350, 650])

        main_layout.addWidget(splitter)

        return container

    def _create_vertical_layout(
        self,
        left_panel: QWidget,
        right_panel: QWidget,
        header: QWidget = None
    ) -> QWidget:
        """
        Vertical layout: Everything stacked vertically.

        [Header (optional)  ]
        [Controls (compact) ]
        [File List         ]
        [Progress          ]
        """
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Add header if provided
        if header:
            main_layout.addWidget(header)

        # Make left panel more compact for vertical layout
        left_panel.setMaximumHeight(250)
        main_layout.addWidget(left_panel)

        # File list and progress take remaining space
        main_layout.addWidget(right_panel, stretch=1)

        return container

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

        main_layout.addWidget(splitter)

        return container

    def _create_simplified_layout(
        self,
        left_panel: QWidget,
        right_panel: QWidget,
        header: QWidget = None
    ) -> QWidget:
        """
        Simplified layout: Settings in collapsible group, file list emphasized.

        [Header (optional)           ]
        [⚙️ Settings (collapsible)   ]
        [File List (expanded)        ]
        [Progress                    ]

        This layout de-emphasizes settings and focuses on the file list.
        """
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Add header if provided
        if header:
            main_layout.addWidget(header)

        # Settings in a collapsible group box
        settings_group = QGroupBox("⚙️ Settings")
        settings_group.setCheckable(True)
        settings_group.setChecked(False)  # Collapsed by default
        settings_group.setFlat(False)

        settings_layout = QVBoxLayout()
        left_panel.setMaximumHeight(400)
        settings_layout.addWidget(left_panel)
        settings_layout.addStretch()
        settings_group.setLayout(settings_layout)

        main_layout.addWidget(settings_group)

        # File list and progress take most space
        main_layout.addWidget(right_panel, stretch=1)

        return container
