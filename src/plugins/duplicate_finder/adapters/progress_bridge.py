"""
Bridge between duplicateFlow callbacks and Qt signals.

duplicateFlow uses Python callbacks for progress updates:
    callback(stage: str, current: int, total: int)

PyQt6 uses signals for thread-safe communication:
    signal.emit(stage, current, total)

This module bridges the two paradigms, allowing duplicateFlow to
communicate progress to the GUI thread safely.
"""

from PyQt6.QtCore import QObject, pyqtSignal
from typing import Callable, Optional
import logging

logger = logging.getLogger('DuplicateFinder.ProgressBridge')


class ProgressBridge(QObject):
    """
    Bridge duplicateFlow progress callbacks to Qt signals.

    This class acts as a translator between duplicateFlow's callback-based
    progress system and PyQt6's signal-based system. It ensures thread-safe
    communication from worker threads to the GUI thread.

    Signals:
        progress(str, int, int): Progress update (stage, current, total)
        stage_changed(str): Stage name changed
        message(str): Informational message
        finished(): Operation completed successfully
        error(str): Error occurred

    Example:
        >>> bridge = ProgressBridge()
        >>> bridge.progress.connect(lambda s, c, t: print(f"{s}: {c}/{t}"))
        >>> bridge.stage_changed.connect(lambda s: print(f"Stage: {s}"))
        >>>
        >>> # Use as callback for duplicateFlow
        >>> adapter.compare_videos(v1, v2, progress_callback=bridge.callback)
    """

    # Signals (thread-safe communication to GUI)
    progress = pyqtSignal(str, int, int)  # (stage, current, total)
    stage_changed = pyqtSignal(str)       # (stage_name)
    message = pyqtSignal(str)             # (message)
    finished = pyqtSignal()               # No args
    error = pyqtSignal(str)               # (error_message)

    def __init__(self):
        """Initialize progress bridge."""
        super().__init__()
        self._current_stage = None
        self._is_cancelled = False
        self._total_progress = 0
        self._last_message = None

    def callback(self, stage: str, current: int, total: int):
        """
        Main callback for duplicateFlow.

        This method is called by duplicateFlow to report progress.
        It translates the callback to Qt signals.

        Args:
            stage: Stage name ('hashing', 'comparing', 'fingerprinting', etc.)
            current: Current progress count
            total: Total items to process

        Raises:
            InterruptedError: If operation was cancelled by user
        """
        # Check cancellation
        if self._is_cancelled:
            logger.info(f"Operation cancelled at stage '{stage}'")
            raise InterruptedError("Operation cancelled by user")

        # Emit stage change if different
        if stage != self._current_stage:
            old_stage = self._current_stage
            self._current_stage = stage
            self.stage_changed.emit(stage)

            # Emit informational message
            stage_message = self._get_stage_message(stage)
            if stage_message:
                self.message.emit(stage_message)

            logger.debug(f"Stage changed: {old_stage} → {stage}")

        # Emit progress update
        self.progress.emit(stage, current, total)

        # Update total progress tracker
        self._total_progress = current

        # Log significant progress milestones
        if total > 0:
            progress_pct = (current / total) * 100
            if progress_pct % 25 == 0 and progress_pct > 0:  # 25%, 50%, 75%, 100%
                logger.info(f"Progress: {stage} {progress_pct:.0f}% ({current}/{total})")

    def _get_stage_message(self, stage: str) -> Optional[str]:
        """
        Get user-friendly message for stage.

        Args:
            stage: Stage name

        Returns:
            User-friendly message, or None
        """
        stage_messages = {
            'hashing': 'Calcul des hash vidéo...',
            'comparing': 'Comparaison des vidéos...',
            'fingerprinting': 'Extraction des empreintes audio...',
            'indexing': 'Indexation des empreintes...',
            'matching': 'Recherche de correspondances...',
            'verifying': 'Vérification des résultats...',
            'analyzing': 'Analyse en cours...',
            'loading': 'Chargement des données...',
            'processing': 'Traitement...',
            'finalizing': 'Finalisation...'
        }

        return stage_messages.get(stage)

    def cancel(self):
        """
        Cancel the current operation.

        This sets a flag that will cause the next callback invocation
        to raise InterruptedError, stopping the operation.
        """
        if not self._is_cancelled:
            self._is_cancelled = True
            logger.info("Cancellation requested")
            self.message.emit("Annulation en cours...")

    def reset(self):
        """
        Reset bridge state.

        Call this before starting a new operation to clear any
        previous state.
        """
        self._current_stage = None
        self._is_cancelled = False
        self._total_progress = 0
        self._last_message = None
        logger.debug("Progress bridge reset")

    def mark_finished(self):
        """Mark operation as finished successfully."""
        self.finished.emit()
        logger.info(f"Operation completed (total progress: {self._total_progress})")

    def mark_error(self, error_message: str):
        """
        Mark operation as failed.

        Args:
            error_message: Error description
        """
        self.error.emit(error_message)
        logger.error(f"Operation failed: {error_message}")

    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._is_cancelled

    @property
    def current_stage(self) -> Optional[str]:
        """Get current stage name."""
        return self._current_stage

    @property
    def total_progress(self) -> int:
        """Get total progress count."""
        return self._total_progress


class MultiProgressBridge:
    """
    Manage multiple progress bridges for concurrent operations.

    Use this when running multiple operations in parallel and need
    to track their progress independently.

    Example:
        >>> multi = MultiProgressBridge()
        >>> bridge1 = multi.create_bridge('video1')
        >>> bridge2 = multi.create_bridge('video2')
        >>>
        >>> # Each bridge can be used independently
        >>> adapter.compare_videos(v1, v2, progress_callback=bridge1.callback)
        >>> adapter.compare_videos(v3, v4, progress_callback=bridge2.callback)
    """

    def __init__(self):
        """Initialize multi-bridge manager."""
        self.bridges: dict[str, ProgressBridge] = {}
        self._global_progress = 0
        logger.debug("MultiProgressBridge initialized")

    def create_bridge(self, name: str) -> ProgressBridge:
        """
        Create and register a new bridge.

        Args:
            name: Unique name for this bridge

        Returns:
            New ProgressBridge instance
        """
        if name in self.bridges:
            logger.warning(f"Bridge '{name}' already exists, returning existing")
            return self.bridges[name]

        bridge = ProgressBridge()
        self.bridges[name] = bridge

        # Connect to track global progress
        bridge.progress.connect(
            lambda s, c, t: self._update_global_progress(name, c, t)
        )

        logger.debug(f"Created bridge '{name}'")
        return bridge

    def get_bridge(self, name: str) -> Optional[ProgressBridge]:
        """Get bridge by name."""
        return self.bridges.get(name)

    def remove_bridge(self, name: str):
        """Remove bridge by name."""
        if name in self.bridges:
            del self.bridges[name]
            logger.debug(f"Removed bridge '{name}'")

    def reset_all(self):
        """Reset all bridges."""
        for bridge in self.bridges.values():
            bridge.reset()
        self._global_progress = 0
        logger.debug("All bridges reset")

    def cancel_all(self):
        """Cancel all operations."""
        for bridge in self.bridges.values():
            bridge.cancel()
        logger.info("All operations cancelled")

    def _update_global_progress(self, name: str, current: int, total: int):
        """Update global progress tracker."""
        # Simple aggregation: sum of all current progress
        self._global_progress = sum(
            bridge.total_progress for bridge in self.bridges.values()
        )

    @property
    def global_progress(self) -> int:
        """Get aggregated progress from all bridges."""
        return self._global_progress


if __name__ == "__main__":
    # Quick test
    print("Testing ProgressBridge...")

    bridge = ProgressBridge()

    # Connect signals
    bridge.progress.connect(
        lambda s, c, t: print(f"Progress: {s} {c}/{t}")
    )
    bridge.stage_changed.connect(
        lambda s: print(f"Stage changed: {s}")
    )
    bridge.message.connect(
        lambda m: print(f"Message: {m}")
    )

    # Simulate progress
    print("\nSimulating progress...")
    try:
        bridge.callback('hashing', 0, 10)
        bridge.callback('hashing', 5, 10)
        bridge.callback('hashing', 10, 10)
        bridge.callback('comparing', 0, 5)
        bridge.callback('comparing', 5, 5)
        bridge.mark_finished()
        print("\n✅ Test passed")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
