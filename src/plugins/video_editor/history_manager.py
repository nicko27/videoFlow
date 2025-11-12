"""History manager for undo/redo functionality."""

from dataclasses import dataclass
from typing import List, Any, Callable, Optional
from src.core.logger import Logger

logger = Logger.get_logger('VideoEditor.HistoryManager')


@dataclass
class HistoryAction:
    """Represents an undoable action."""
    name: str
    undo_callback: Callable
    redo_callback: Callable
    data: Any = None


class HistoryManager:
    """Manages undo/redo history."""

    def __init__(self, max_history: int = 50):
        """
        Initialize history manager.

        Args:
            max_history: Maximum number of actions to keep in history
        """
        self.max_history = max_history
        self.undo_stack: List[HistoryAction] = []
        self.redo_stack: List[HistoryAction] = []

    def push(self, action: HistoryAction):
        """
        Add action to history.

        Args:
            action: Action to add
        """
        self.undo_stack.append(action)

        # Limit stack size
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)

        # Clear redo stack when new action is performed
        self.redo_stack.clear()

        logger.debug(f"Action added: {action.name}")

    def undo(self) -> bool:
        """
        Undo last action.

        Returns:
            True if action was undone, False otherwise
        """
        if not self.undo_stack:
            logger.debug("Nothing to undo")
            return False

        action = self.undo_stack.pop()

        try:
            action.undo_callback()
            self.redo_stack.append(action)
            logger.info(f"Undo: {action.name}")
            return True
        except Exception as e:
            logger.error(f"Error undoing action: {e}")
            return False

    def redo(self) -> bool:
        """
        Redo last undone action.

        Returns:
            True if action was redone, False otherwise
        """
        if not self.redo_stack:
            logger.debug("Nothing to redo")
            return False

        action = self.redo_stack.pop()

        try:
            action.redo_callback()
            self.undo_stack.append(action)
            logger.info(f"Redo: {action.name}")
            return True
        except Exception as e:
            logger.error(f"Error redoing action: {e}")
            return False

    def clear(self):
        """Clear all history."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        logger.debug("History cleared")

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self.redo_stack) > 0

    def get_undo_description(self) -> Optional[str]:
        """Get description of next undo action."""
        if self.undo_stack:
            return self.undo_stack[-1].name
        return None

    def get_redo_description(self) -> Optional[str]:
        """Get description of next redo action."""
        if self.redo_stack:
            return self.redo_stack[-1].name
        return None
