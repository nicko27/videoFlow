"""Classic Layout Builder for Video Editor.

This module builds a traditional video editor layout
with tabs and classic controls.

NOTE: This is a simplified version. Full implementation will be
completed in a future refactoring step.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from .base_layout_builder import BaseLayoutBuilder
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.ClassicLayoutBuilder')


class ClassicLayoutBuilder(BaseLayoutBuilder):
    """Builder for classic traditional layout.

    Features:
    - Tab-based interface
    - Single timeline
    - Classic toolbar
    - Simple preview
    """

    def build(self) -> QWidget:
        """Build the classic layout.

        Returns:
            Main widget containing the layout
        """
        logger.info("Building Classic layout (placeholder)")

        # TODO: Full implementation
        # For now, return a placeholder widget
        widget = QWidget(self.parent)
        layout = QVBoxLayout(widget)

        placeholder = QLabel("Classic Layout - Full implementation pending")
        placeholder.setStyleSheet("font-size: 14px; padding: 20px;")
        layout.addWidget(placeholder)

        return widget
