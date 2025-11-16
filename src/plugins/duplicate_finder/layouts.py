"""
Layout system for different UI arrangements.

This module provides multiple layout options for the duplicate finder:
1. Classic (default) - Left panel with settings, right panel with files
2. Vertical Compact - Everything stacked vertically
3. Dashboard - Card-based layout with real-time stats
4. Simplified - Minimal UI with focus on essential actions
"""

from enum import Enum
from typing import Dict, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame,
    QPushButton, QLabel, QGridLayout, QGroupBox, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


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
        Dashboard layout: Card-based grid with stats.

        [Header (optional)          ]
        [Quick Actions | Stats Card ]
        [File List    | File List   ]
        [Progress     | Progress    ]
        """
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # Add header if provided
        if header:
            main_layout.addWidget(header)

        # Top row: Quick actions and stats in cards
        top_row = QHBoxLayout()
        top_row.setSpacing(15)

        # Quick actions card (from left panel)
        actions_card = self._create_card("Quick Actions", left_panel)
        actions_card.setMaximumHeight(200)
        top_row.addWidget(actions_card, stretch=1)

        # Stats card placeholder
        stats_card = self._create_stats_card()
        stats_card.setMaximumHeight(200)
        top_row.addWidget(stats_card, stretch=1)

        main_layout.addLayout(top_row)

        # Bottom: File list and progress (full width)
        main_layout.addWidget(right_panel, stretch=1)

        return container

    def _create_simplified_layout(
        self,
        left_panel: QWidget,
        right_panel: QWidget,
        header: QWidget = None
    ) -> QWidget:
        """
        Simplified layout: Minimal UI with large buttons.

        [Header (optional)    ]
        [Large Action Buttons]
        [File List           ]
        [Progress (minimal)  ]
        """
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Add header if provided
        if header:
            main_layout.addWidget(header)

        # Extract action buttons from left panel and make them large
        # For now, hide the complex settings
        simplified_actions = self._create_simplified_actions()
        main_layout.addWidget(simplified_actions)

        # Show advanced settings as collapsible
        advanced_group = QGroupBox("⚙️ Advanced Settings (click to expand)")
        advanced_group.setCheckable(True)
        advanced_group.setChecked(False)  # Collapsed by default
        advanced_group.setFlat(True)

        advanced_layout = QVBoxLayout()
        left_panel.setMaximumHeight(300)
        advanced_layout.addWidget(left_panel)
        advanced_group.setLayout(advanced_layout)

        main_layout.addWidget(advanced_group)

        # File list takes most space
        main_layout.addWidget(right_panel, stretch=1)

        return container

    def _create_card(self, title: str, content: QWidget) -> QFrame:
        """Create a card-style container."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # Content
        layout.addWidget(content, stretch=1)

        return card

    def _create_stats_card(self) -> QFrame:
        """Create a statistics card."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border: 2px solid #2196F3;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Title
        title = QLabel("📊 Session Stats")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # Stats grid
        stats_grid = QGridLayout()
        stats_grid.setSpacing(10)

        # Placeholder stats (will be updated dynamically)
        stats_grid.addWidget(QLabel("Files:"), 0, 0)
        files_label = QLabel("0")
        files_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        files_label.setStyleSheet("color: #2196F3;")
        stats_grid.addWidget(files_label, 0, 1)

        stats_grid.addWidget(QLabel("Analyzed:"), 1, 0)
        analyzed_label = QLabel("0")
        analyzed_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        analyzed_label.setStyleSheet("color: #4CAF50;")
        stats_grid.addWidget(analyzed_label, 1, 1)

        stats_grid.addWidget(QLabel("Duplicates:"), 2, 0)
        dup_label = QLabel("0")
        dup_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        dup_label.setStyleSheet("color: #FF9800;")
        stats_grid.addWidget(dup_label, 2, 1)

        layout.addLayout(stats_grid)
        layout.addStretch()

        return card

    def _create_simplified_actions(self) -> QWidget:
        """Create large, simplified action buttons."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(15)

        # Large buttons
        btn_style = """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """

        add_btn = QPushButton("📁 Add Files")
        add_btn.setMinimumHeight(80)
        add_btn.setStyleSheet(btn_style)
        layout.addWidget(add_btn)

        analyze_btn = QPushButton("🔍 Analyze")
        analyze_btn.setMinimumHeight(80)
        analyze_btn.setStyleSheet(btn_style.replace("#2196F3", "#4CAF50")
                                             .replace("#1976D2", "#388E3C")
                                             .replace("#0D47A1", "#2E7D32"))
        layout.addWidget(analyze_btn)

        results_btn = QPushButton("📊 View Results")
        results_btn.setMinimumHeight(80)
        results_btn.setStyleSheet(btn_style.replace("#2196F3", "#FF9800")
                                            .replace("#1976D2", "#F57C00")
                                            .replace("#0D47A1", "#E65100"))
        layout.addWidget(results_btn)

        return widget
