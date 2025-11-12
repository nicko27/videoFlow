"""Base Layout Builder for Video Editor UI.

This module provides the base class for building different UI layouts.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from PyQt6.QtWidgets import QWidget
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.BaseLayoutBuilder')


class BaseLayoutBuilder(ABC):
    """Abstract base class for building UI layouts.

    Subclasses must implement the build() method to create
    their specific layout.
    """

    def __init__(self, parent: QWidget):
        """Initialize the layout builder.

        Args:
            parent: Parent widget
        """
        self.parent = parent
        self.widgets: Dict[str, Any] = {}

    @abstractmethod
    def build(self) -> QWidget:
        """Build and return the main layout widget.

        Returns:
            The main widget containing the layout

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement build()")

    def get_widget(self, name: str) -> Any:
        """Get a widget by name.

        Args:
            name: Name of the widget

        Returns:
            The widget, or None if not found
        """
        return self.widgets.get(name)

    def set_widget(self, name: str, widget: Any):
        """Store a widget by name for later access.

        Args:
            name: Name to store the widget under
            widget: The widget to store
        """
        self.widgets[name] = widget

    def get_all_widgets(self) -> Dict[str, Any]:
        """Get all stored widgets.

        Returns:
            Dictionary of all widgets
        """
        return self.widgets.copy()
