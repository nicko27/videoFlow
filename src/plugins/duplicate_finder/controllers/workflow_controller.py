"""
Workflow Controller - State machine for managing analysis workflow.

Provides a centralized controller for managing workflow states and transitions,
ensuring consistent behavior and proper error handling.
"""
from typing import Optional, Dict, Any, Callable
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.WorkflowController')


class WorkflowState(Enum):
    """Workflow states for duplicate detection analysis."""
    IDLE = "idle"
    HASHING = "hashing"
    COMPARING = "comparing"
    PROCESSING_DUPLICATES = "processing_duplicates"
    DETECTING_SUBSEQUENCES = "detecting_subsequences"
    EXTRACTING_AUDIO = "extracting_audio"
    COMPARING_AUDIO = "comparing_audio"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


# Valid state transitions
VALID_TRANSITIONS = {
    WorkflowState.IDLE: {
        WorkflowState.HASHING,
        WorkflowState.EXTRACTING_AUDIO,
    },
    WorkflowState.HASHING: {
        WorkflowState.COMPARING,
        WorkflowState.ERROR,
        WorkflowState.CANCELLED,
    },
    WorkflowState.COMPARING: {
        WorkflowState.PROCESSING_DUPLICATES,
        WorkflowState.DETECTING_SUBSEQUENCES,
        WorkflowState.COMPLETED,
        WorkflowState.ERROR,
        WorkflowState.CANCELLED,
    },
    WorkflowState.PROCESSING_DUPLICATES: {
        WorkflowState.COMPLETED,
        WorkflowState.ERROR,
        WorkflowState.CANCELLED,
    },
    WorkflowState.DETECTING_SUBSEQUENCES: {
        WorkflowState.VERIFYING,
        WorkflowState.COMPLETED,
        WorkflowState.ERROR,
        WorkflowState.CANCELLED,
    },
    WorkflowState.EXTRACTING_AUDIO: {
        WorkflowState.COMPARING_AUDIO,
        WorkflowState.HASHING,  # Fallback to visual if no audio
        WorkflowState.ERROR,
        WorkflowState.CANCELLED,
    },
    WorkflowState.COMPARING_AUDIO: {
        WorkflowState.VERIFYING,
        WorkflowState.COMPLETED,
        WorkflowState.ERROR,
        WorkflowState.CANCELLED,
    },
    WorkflowState.VERIFYING: {
        WorkflowState.COMPLETED,
        WorkflowState.ERROR,
        WorkflowState.CANCELLED,
    },
    WorkflowState.COMPLETED: {
        WorkflowState.IDLE,
    },
    WorkflowState.ERROR: {
        WorkflowState.IDLE,
    },
    WorkflowState.CANCELLED: {
        WorkflowState.IDLE,
    },
}


class WorkflowController(QObject):
    """
    Controller for managing analysis workflow state machine.

    Manages state transitions, progress tracking, and error handling
    for the duplicate detection workflow.

    Signals:
        state_changed(WorkflowState, WorkflowState): Emitted on state change (old_state, new_state)
        progress_updated(int, int, str): Emitted on progress update (current, total, message)
        workflow_completed(): Emitted when workflow completes successfully
        workflow_error(str): Emitted when workflow encounters an error
        workflow_cancelled(): Emitted when workflow is cancelled
    """

    state_changed = pyqtSignal(object, object)  # old_state, new_state
    progress_updated = pyqtSignal(int, int, str)  # current, total, message
    workflow_completed = pyqtSignal()
    workflow_error = pyqtSignal(str)
    workflow_cancelled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._state: WorkflowState = WorkflowState.IDLE
        self._previous_state: Optional[WorkflowState] = None
        self._metadata: Dict[str, Any] = {}
        self._state_handlers: Dict[WorkflowState, Callable] = {}

    def get_state(self) -> WorkflowState:
        """
        Get the current workflow state.

        Returns:
            Current WorkflowState
        """
        return self._state

    def get_previous_state(self) -> Optional[WorkflowState]:
        """
        Get the previous workflow state.

        Returns:
            Previous WorkflowState or None
        """
        return self._previous_state

    def is_active(self) -> bool:
        """
        Check if workflow is currently active.

        Returns:
            True if workflow is in an active state (not idle/completed/error/cancelled)
        """
        return self._state not in {
            WorkflowState.IDLE,
            WorkflowState.COMPLETED,
            WorkflowState.ERROR,
            WorkflowState.CANCELLED,
        }

    def can_transition_to(self, new_state: WorkflowState) -> bool:
        """
        Check if transition to new state is valid.

        Args:
            new_state: State to transition to

        Returns:
            True if transition is valid
        """
        valid_next_states = VALID_TRANSITIONS.get(self._state, set())
        return new_state in valid_next_states

    def transition_to(self, new_state: WorkflowState, metadata: Optional[Dict[str, Any]] = None):
        """
        Transition to a new workflow state.

        Args:
            new_state: State to transition to
            metadata: Optional metadata about the transition

        Raises:
            ValueError: If transition is not valid
        """
        if not self.can_transition_to(new_state):
            error_msg = f"Invalid state transition: {self._state.value} -> {new_state.value}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        old_state = self._state
        self._previous_state = old_state
        self._state = new_state

        # Update metadata
        if metadata:
            self._metadata.update(metadata)

        # Emit signal
        self.state_changed.emit(old_state, new_state)
        logger.info(f"State transition: {old_state.value} -> {new_state.value}")

        # Call state handler if registered
        if new_state in self._state_handlers:
            try:
                self._state_handlers[new_state](metadata)
            except Exception as e:
                logger.error(f"Error in state handler for {new_state.value}: {e}")

        # Emit special signals for terminal states
        if new_state == WorkflowState.COMPLETED:
            self.workflow_completed.emit()
        elif new_state == WorkflowState.ERROR:
            error_msg = metadata.get('error_message', 'Unknown error') if metadata else 'Unknown error'
            self.workflow_error.emit(error_msg)
        elif new_state == WorkflowState.CANCELLED:
            self.workflow_cancelled.emit()

    def register_state_handler(self, state: WorkflowState, handler: Callable):
        """
        Register a handler to be called when entering a state.

        Args:
            state: WorkflowState to handle
            handler: Callable(metadata: Optional[Dict]) to call on state entry
        """
        self._state_handlers[state] = handler
        logger.debug(f"Registered handler for state: {state.value}")

    def unregister_state_handler(self, state: WorkflowState):
        """
        Unregister a state handler.

        Args:
            state: WorkflowState to unregister
        """
        if state in self._state_handlers:
            del self._state_handlers[state]
            logger.debug(f"Unregistered handler for state: {state.value}")

    def update_progress(self, current: int, total: int, message: str = ""):
        """
        Update workflow progress.

        Args:
            current: Current progress value
            total: Total progress value
            message: Optional progress message
        """
        self.progress_updated.emit(current, total, message)
        logger.debug(f"Progress: {current}/{total} - {message}")

    def error(self, error_message: str, error_data: Optional[Dict[str, Any]] = None):
        """
        Mark workflow as error state.

        Args:
            error_message: Error description
            error_data: Optional additional error data
        """
        metadata = {'error_message': error_message}
        if error_data:
            metadata.update(error_data)

        try:
            self.transition_to(WorkflowState.ERROR, metadata)
        except ValueError:
            # If transition not valid, force to error state
            logger.warning(f"Forced transition to ERROR from {self._state.value}")
            old_state = self._state
            self._previous_state = old_state
            self._state = WorkflowState.ERROR
            self._metadata.update(metadata)
            self.state_changed.emit(old_state, WorkflowState.ERROR)
            self.workflow_error.emit(error_message)

    def cancel(self):
        """Cancel the workflow."""
        try:
            self.transition_to(WorkflowState.CANCELLED)
        except ValueError:
            # If transition not valid, force to cancelled state
            logger.warning(f"Forced transition to CANCELLED from {self._state.value}")
            old_state = self._state
            self._previous_state = old_state
            self._state = WorkflowState.CANCELLED
            self.state_changed.emit(old_state, WorkflowState.CANCELLED)
            self.workflow_cancelled.emit()

    def reset(self):
        """Reset workflow to idle state."""
        if self._state != WorkflowState.IDLE:
            try:
                self.transition_to(WorkflowState.IDLE)
            except ValueError:
                # Force reset to idle
                logger.warning(f"Forced reset to IDLE from {self._state.value}")
                old_state = self._state
                self._previous_state = old_state
                self._state = WorkflowState.IDLE
                self._metadata.clear()
                self.state_changed.emit(old_state, WorkflowState.IDLE)

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata value.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self._metadata.get(key, default)

    def set_metadata(self, key: str, value: Any):
        """
        Set metadata value.

        Args:
            key: Metadata key
            value: Value to set
        """
        self._metadata[key] = value

    def clear_metadata(self):
        """Clear all metadata."""
        self._metadata.clear()

    def get_all_metadata(self) -> Dict[str, Any]:
        """
        Get all metadata.

        Returns:
            Dictionary of all metadata
        """
        return self._metadata.copy()

    def __repr__(self) -> str:
        """String representation of controller."""
        return f"WorkflowController(state={self._state.value}, active={self.is_active()})"


# Global instance for convenience
_global_workflow_controller: Optional[WorkflowController] = None


def get_workflow_controller() -> WorkflowController:
    """
    Get the global workflow controller instance.

    Returns:
        Global WorkflowController instance
    """
    global _global_workflow_controller

    if _global_workflow_controller is None:
        _global_workflow_controller = WorkflowController()
        logger.info("Created global WorkflowController instance")

    return _global_workflow_controller


def reset_workflow_controller():
    """Reset the global workflow controller (mainly for testing)."""
    global _global_workflow_controller
    _global_workflow_controller = None
