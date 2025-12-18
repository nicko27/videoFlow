"""
Analysis orchestration handler for the duplicate finder.

This module handles the coordination of hash computation and video comparison
operations, managing worker threads and progress tracking.
"""
import time
from typing import List, Optional, Dict, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from ..workers.duplicateflow_worker import DuplicateFlowWorker
from src.core.logger import Logger

# OBSOLETE: ParallelHashWorker import removed - was never used

logger = Logger.get_logger('DuplicateFinder.AnalysisHandler')


class AnalysisHandler(QObject):
    """
    Handler for orchestrating video analysis operations.

    This class manages the analysis workflow, coordinating hash computation
    and video comparison workers. It provides a high-level interface for
    starting, stopping, and monitoring analysis operations.

    Attributes:
        hash_progress (pyqtSignal): Signal emitting hash computation progress (int).
        hash_finished (pyqtSignal): Signal emitted when hash computation completes.
        comparison_progress (pyqtSignal): Signal emitting comparison progress (int).
        comparison_finished (pyqtSignal): Signal emitted when comparisons complete.
        analysis_error (pyqtSignal): Signal emitting error messages (str).
        status_update (pyqtSignal): Signal emitting status updates (str).

    Example:
        ```python
        handler = AnalysisHandler(video_hasher)
        handler.hash_finished.connect(on_hash_complete)
        handler.start_analysis(files, config)
        ```
    """

    # Signals
    hash_progress = pyqtSignal(int)
    hash_finished = pyqtSignal()
    comparison_progress = pyqtSignal(int)
    comparison_finished = pyqtSignal()
    analysis_error = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, db_manager) -> None:
        """
        Initialize the analysis handler.

        Args:
            db_manager: DatabaseManager instance for database access.
        """
        super().__init__()
        self.db = db_manager

        self.comparison_worker: Optional[DuplicateFlowWorker] = None
        self.start_time: Optional[float] = None
        self.failed_files: List[str] = []
        logger.info("Analysis handler initialized (using DuplicateFlow for comparisons)")

    # OBSOLETE: start_hash_analysis() removed - was never called, used legacy VideoHasher
    # Hash computation now happens inside DuplicateFlow algorithms

    def start_comparison_analysis(
        self,
        files: List[str],
        config: Dict[str, Any],
        duplicate_callback: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None,
        status_callback: Optional[Callable] = None,
        total_comparisons_callback: Optional[Callable] = None,
        comparison_details_callback: Optional[Callable] = None,
        specific_pairs: Optional[List[tuple]] = None
    ) -> None:
        """
        Start video comparison analysis.

        Args:
            files: List of file paths to compare.
            config: Configuration dictionary with analysis parameters.
            duplicate_callback: Optional callback when duplicates are found.
            progress_callback: Optional callback for progress updates.
            status_callback: Optional callback for status updates.
            total_comparisons_callback: Optional callback for total count.
            comparison_details_callback: Optional callback for detailed progress.
            specific_pairs: Optional list of specific (file1, file2) pairs to compare.
                          If provided, only these pairs are compared (audio-first workflow).
        """
        # Get preset from config, default to 'balanced'
        preset = config.get('preset', 'balanced')
        threshold = config.get('threshold', 70.0)

        # Create and configure DuplicateFlow worker
        self.comparison_worker = DuplicateFlowWorker(
            files=files,
            preset=preset,
            threshold=threshold,
            specific_pairs=specific_pairs
        )

        # Connect signals
        self.comparison_worker.progress.connect(self._on_comparison_progress)
        self.comparison_worker.finished.connect(self._on_comparison_finished)
        self.comparison_worker.error.connect(self._on_comparison_error)

        if duplicate_callback:
            # DuplicateFlowWorker signal: duplicate_found(file1, file2, similarity, metadata)
            # Legacy expects: duplicate_found(file1, file2, similarity)
            # Use lambda to adapt the signature
            self.comparison_worker.duplicate_found.connect(
                lambda f1, f2, sim, meta: duplicate_callback(f1, f2, sim)
            )
        if progress_callback:
            self.comparison_worker.progress.connect(progress_callback)
        if status_callback:
            self.comparison_worker.status_update.connect(status_callback)
        if comparison_details_callback:
            self.comparison_worker.comparison_details.connect(comparison_details_callback)

        # Note: DuplicateFlowWorker doesn't have total_comparisons_signal
        # It's computed internally - emit it manually after worker creation
        if total_comparisons_callback and hasattr(self.comparison_worker, 'total_comparisons'):
            total_comparisons_callback(self.comparison_worker.total_comparisons)

        logger.info(f"Starting DuplicateFlow comparison: {len(files)} files, preset={preset}")
        self.comparison_worker.start()

    def stop_analysis(self) -> None:
        """
        Stop all running analysis operations.

        This method gracefully stops comparison workers
        and waits for them to finish with timeout protection.
        """
        if self.comparison_worker and self.comparison_worker.isRunning():
            logger.info("Stopping comparison worker...")
            self.comparison_worker.stop()
            # Wait with 5 second timeout to prevent indefinite blocking
            if not self.comparison_worker.wait(5000):
                logger.warning("Comparison worker did not stop gracefully, forcing termination")
                self.comparison_worker.terminate()
            self.comparison_worker = None

        logger.info("Analysis stopped")

    def is_analyzing(self) -> bool:
        """
        Check if any analysis operation is currently running.

        Returns:
            True if comparison worker is running, False otherwise.
        """
        comparison_running = self.comparison_worker and self.comparison_worker.isRunning()
        return comparison_running

    def get_elapsed_time(self) -> float:
        """
        Get elapsed time since analysis started.

        Returns:
            Elapsed time in seconds, or 0 if not started.
        """
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def get_failed_files(self) -> List[str]:
        """
        Get list of files that failed processing.

        Returns:
            List of file paths that failed.
        """
        return self.failed_files.copy()

    # OBSOLETE: _on_hash_* methods removed - were never called (start_hash_analysis removed)
    # hash_progress and hash_finished signals are still used by main_window.py for other purposes

    def _on_comparison_progress(self, current: int) -> None:
        """
        Handle comparison progress updates.

        Args:
            current: Current progress count.
        """
        self.comparison_progress.emit(current)

    def _on_comparison_finished(self) -> None:
        """
        Handle comparison completion.
        """
        elapsed = self.get_elapsed_time()
        logger.info(f"Comparison finished in {elapsed:.1f} seconds")
        self.comparison_finished.emit()

    def _on_comparison_error(self, error_msg: str) -> None:
        """
        Handle comparison errors.

        Args:
            error_msg: Error message.
        """
        logger.error(f"Comparison error: {error_msg}")
        self.analysis_error.emit(error_msg)

    def cleanup(self) -> None:
        """
        Clean up resources and stop all workers.
        """
        self.stop_analysis()
        logger.info("Analysis handler cleaned up")
