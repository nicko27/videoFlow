"""
Progress Manager - Centralized progress tracking and widget management.

Provides a unified interface for managing progress widgets throughout the application,
reducing code duplication and ensuring consistent behavior.
"""
from typing import Dict, Optional, Any
from enum import Enum
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, pyqtSignal

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.ProgressManager')


class ProgressState(Enum):
    """Progress widget states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class ProgressManager(QObject):
    """
    Centralized manager for progress widgets.

    Manages multiple progress widgets, ensuring only one is active at a time
    and providing a consistent API for progress updates.

    Signals:
        progress_started(str): Emitted when progress starts (widget_id)
        progress_updated(str, int, int): Emitted on progress update (widget_id, current, total)
        progress_completed(str): Emitted when progress completes (widget_id)
        progress_error(str, str): Emitted on error (widget_id, error_message)
        all_hidden(): Emitted when all progress widgets are hidden
    """

    progress_started = pyqtSignal(str)
    progress_updated = pyqtSignal(str, int, int)
    progress_completed = pyqtSignal(str)
    progress_error = pyqtSignal(str, str)
    all_hidden = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._widgets: Dict[str, QWidget] = {}
        self._states: Dict[str, ProgressState] = {}
        self._active_widget: Optional[str] = None

    def register_widget(self, widget_id: str, widget: QWidget, initial_state: ProgressState = ProgressState.IDLE):
        """
        Register a progress widget.

        Args:
            widget_id: Unique identifier for the widget
            widget: The progress widget instance
            initial_state: Initial state (default: IDLE)
        """
        if widget_id in self._widgets:
            logger.warning(f"Widget '{widget_id}' already registered, replacing")

        self._widgets[widget_id] = widget
        self._states[widget_id] = initial_state

        # Ensure widget is hidden initially
        if initial_state == ProgressState.IDLE:
            widget.setVisible(False)

        logger.debug(f"Registered progress widget: {widget_id}")

    def unregister_widget(self, widget_id: str):
        """
        Unregister a progress widget.

        Args:
            widget_id: Widget identifier to unregister
        """
        if widget_id in self._widgets:
            del self._widgets[widget_id]
            del self._states[widget_id]

            if self._active_widget == widget_id:
                self._active_widget = None

            logger.debug(f"Unregistered progress widget: {widget_id}")

    def start(self, widget_id: str, title: Optional[str] = None):
        """
        Start progress tracking for a widget.

        Args:
            widget_id: Widget identifier
            title: Optional title to set on the widget

        Raises:
            ValueError: If widget_id not registered
        """
        if widget_id not in self._widgets:
            raise ValueError(f"Widget '{widget_id}' not registered")

        widget = self._widgets[widget_id]

        # Hide currently active widget if different
        if self._active_widget and self._active_widget != widget_id:
            self._hide_widget(self._active_widget)

        # Show and configure widget
        widget.setVisible(True)
        if title and hasattr(widget, 'set_title'):
            widget.set_title(title)

        # Update state
        self._states[widget_id] = ProgressState.RUNNING
        self._active_widget = widget_id

        self.progress_started.emit(widget_id)
        logger.info(f"Progress started: {widget_id}" + (f" - {title}" if title else ""))

    def update(self, widget_id: str, current: int, total: int, message: Optional[str] = None):
        """
        Update progress for a widget.

        Args:
            widget_id: Widget identifier
            current: Current progress value
            total: Total progress value
            message: Optional status message

        Raises:
            ValueError: If widget_id not registered or not running
        """
        if widget_id not in self._widgets:
            raise ValueError(f"Widget '{widget_id}' not registered")

        if self._states[widget_id] != ProgressState.RUNNING:
            logger.warning(f"Attempt to update non-running widget: {widget_id}")
            return

        widget = self._widgets[widget_id]

        # Update progress
        if hasattr(widget, 'update_progress'):
            widget.update_progress(current, total)
        elif hasattr(widget, 'setValue') and hasattr(widget, 'setMaximum'):
            widget.setMaximum(total)
            widget.setValue(current)

        # Update message if provided
        if message and hasattr(widget, 'set_status'):
            widget.set_status(message)

        self.progress_updated.emit(widget_id, current, total)

    def finish(self, widget_id: str, hide: bool = True):
        """
        Complete progress tracking for a widget.

        Args:
            widget_id: Widget identifier
            hide: Whether to hide the widget (default: True)

        Raises:
            ValueError: If widget_id not registered
        """
        if widget_id not in self._widgets:
            raise ValueError(f"Widget '{widget_id}' not registered")

        widget = self._widgets[widget_id]

        # Mark as completed
        if hasattr(widget, 'set_completed'):
            widget.set_completed()

        # Update state
        self._states[widget_id] = ProgressState.COMPLETED

        if hide:
            widget.setVisible(False)

        if self._active_widget == widget_id:
            self._active_widget = None

        self.progress_completed.emit(widget_id)
        logger.info(f"Progress completed: {widget_id}")

    def error(self, widget_id: str, error_message: str, hide: bool = False):
        """
        Mark progress as error state.

        Args:
            widget_id: Widget identifier
            error_message: Error description
            hide: Whether to hide the widget (default: False)

        Raises:
            ValueError: If widget_id not registered
        """
        if widget_id not in self._widgets:
            raise ValueError(f"Widget '{widget_id}' not registered")

        widget = self._widgets[widget_id]

        # Show error state
        if hasattr(widget, 'set_error'):
            widget.set_error(error_message)

        # Update state
        self._states[widget_id] = ProgressState.ERROR

        if hide:
            widget.setVisible(False)

        if self._active_widget == widget_id:
            self._active_widget = None

        self.progress_error.emit(widget_id, error_message)
        logger.error(f"Progress error: {widget_id} - {error_message}")

    def hide_all(self):
        """Hide all registered progress widgets."""
        for widget_id in self._widgets:
            self._hide_widget(widget_id)

        self._active_widget = None
        self.all_hidden.emit()
        logger.debug("All progress widgets hidden")

    def _hide_widget(self, widget_id: str):
        """Internal method to hide a specific widget."""
        if widget_id in self._widgets:
            widget = self._widgets[widget_id]
            widget.setVisible(False)

            if self._states[widget_id] not in (ProgressState.COMPLETED, ProgressState.ERROR):
                self._states[widget_id] = ProgressState.IDLE

    def is_running(self, widget_id: Optional[str] = None) -> bool:
        """
        Check if a widget (or any widget) is running.

        Args:
            widget_id: Specific widget to check, or None to check any

        Returns:
            True if the widget (or any widget) is running
        """
        if widget_id:
            return self._states.get(widget_id) == ProgressState.RUNNING

        # Check if any widget is running
        return any(state == ProgressState.RUNNING for state in self._states.values())

    def get_active_widget(self) -> Optional[str]:
        """
        Get the currently active widget ID.

        Returns:
            Active widget ID or None
        """
        return self._active_widget

    def get_state(self, widget_id: str) -> Optional[ProgressState]:
        """
        Get the current state of a widget.

        Args:
            widget_id: Widget identifier

        Returns:
            Current state or None if not registered
        """
        return self._states.get(widget_id)

    def get_all_states(self) -> Dict[str, ProgressState]:
        """
        Get all widget states.

        Returns:
            Dictionary of widget_id -> state
        """
        return self._states.copy()

    def reset(self, widget_id: str):
        """
        Reset a widget to idle state.

        Args:
            widget_id: Widget identifier

        Raises:
            ValueError: If widget_id not registered
        """
        if widget_id not in self._widgets:
            raise ValueError(f"Widget '{widget_id}' not registered")

        self._hide_widget(widget_id)
        self._states[widget_id] = ProgressState.IDLE

        if self._active_widget == widget_id:
            self._active_widget = None

        logger.debug(f"Reset progress widget: {widget_id}")

    def reset_all(self):
        """Reset all widgets to idle state."""
        for widget_id in list(self._widgets.keys()):
            self.reset(widget_id)

        logger.debug("All progress widgets reset")


# Global instance for convenience
_global_progress_manager: Optional[ProgressManager] = None


def get_progress_manager() -> ProgressManager:
    """
    Get the global progress manager instance.

    Returns:
        Global ProgressManager instance
    """
    global _global_progress_manager

    if _global_progress_manager is None:
        _global_progress_manager = ProgressManager()
        logger.info("Created global ProgressManager instance")

    return _global_progress_manager


def reset_progress_manager():
    """Reset the global progress manager (mainly for testing)."""
    global _global_progress_manager
    _global_progress_manager = None
