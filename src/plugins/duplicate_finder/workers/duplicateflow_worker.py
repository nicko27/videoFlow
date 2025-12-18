"""
DuplicateFlow comparison worker for advanced duplicate detection.

This worker uses the duplicateFlow backend with 19 algorithms and 6 presets
to provide more accurate duplicate detection compared to simple hash-based
comparison.
"""
import time
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal, QMutex

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.DuplicateFlowWorker')


class DuplicateFlowWorker(QThread):
    """
    Worker thread for duplicateFlow-based video comparison.

    This worker uses the DuplicateFlowAdapter to compare videos using
    advanced algorithms (19 total) organized in 6 preset pipelines.

    Features:
    - Multi-algorithm comparison (3-5 algorithms per preset)
    - Multi-stage progress tracking
    - Cancellation support
    - Detailed result metadata

    Signals:
        progress (int): Current comparison count
        finished (): Processing complete
        duplicate_found (str, str, float, dict): file1, file2, similarity, metadata
        error (str): Error message
        status_update (str): Status message
        comparison_details (int, int, str, str): current, total, file1, file2
        stage_update (str): Current processing stage

    Example:
        >>> worker = DuplicateFlowWorker(
        ...     files=['video1.mp4', 'video2.mp4'],
        ...     preset='balanced',
        ...     threshold=70.0
        ... )
        >>> worker.duplicate_found.connect(handle_duplicate)
        >>> worker.progress.connect(update_progress_bar)
        >>> worker.start()
    """

    # Signal definitions
    progress = pyqtSignal(int)  # Current progress count
    finished = pyqtSignal()  # Processing complete
    duplicate_found = pyqtSignal(str, str, float, dict)  # file1, file2, similarity, metadata
    error = pyqtSignal(str)  # Error message
    status_update = pyqtSignal(str)  # Status message
    comparison_details = pyqtSignal(int, int, str, str)  # current, total, file1, file2
    stage_update = pyqtSignal(str)  # Current stage (hashing, comparing, etc.)

    def __init__(
        self,
        files: List[str],
        preset: str = 'balanced',
        threshold: float = 70.0,
        specific_pairs: Optional[List[Tuple[str, str]]] = None,
        pipeline_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize the duplicateFlow worker.

        Args:
            files: List of video file paths to compare
            preset: DuplicateFlow preset name (fast, balanced, thorough, multimodal, structural, hybrid)
                   Ignored if pipeline_config is provided
            threshold: Similarity threshold percentage (0-100)
            specific_pairs: Optional list of specific (file1, file2) pairs to compare
            pipeline_config: Optional custom pipeline configuration from database.
                            If provided, overrides preset parameter.
        """
        super().__init__()
        self.files = files
        self.preset = preset
        self.threshold = threshold
        self.specific_pairs = specific_pairs
        self.pipeline_config = pipeline_config  # NEW: Support custom pipelines

        self._stop = False
        self._mutex = QMutex()
        self.processed_count = 0
        self.total_comparisons = 0

        # Initialize adapter and progress bridge
        self.adapter = None
        self.bridge = None

        if pipeline_config:
            mode = pipeline_config.get('mode', 'custom')
            logger.info(
                f"DuplicateFlowWorker initialized: "
                f"{len(files)} files, custom pipeline (mode={mode}), threshold={threshold}"
            )
        else:
            logger.info(
                f"DuplicateFlowWorker initialized: "
                f"{len(files)} files, preset='{preset}', threshold={threshold}"
            )

    def run(self) -> None:
        """
        Execute the comparison workflow.

        This method runs in a separate thread and performs:
        1. Initialize adapter and check availability
        2. Generate comparison pairs
        3. Compare each pair using duplicateFlow
        4. Emit signals for duplicates found
        5. Handle errors gracefully
        """
        try:
            # Import adapter modules (adapter handles duplicateFlow path resolution)
            try:
                from ..adapters.duplicateflow_adapter import DuplicateFlowAdapter, DUPLICATEFLOW_AVAILABLE, IMPORT_ERROR
                from ..adapters.progress_bridge import ProgressBridge
            except ImportError:
                # Fallback for standalone execution
                from adapters.duplicateflow_adapter import DuplicateFlowAdapter, DUPLICATEFLOW_AVAILABLE, IMPORT_ERROR
                from adapters.progress_bridge import ProgressBridge

            # Early check if duplicateFlow is available
            if not DUPLICATEFLOW_AVAILABLE:
                error_msg = f"duplicateFlow not available: {IMPORT_ERROR}"
                logger.error(error_msg)
                self.error.emit(error_msg)
                return

            # Initialize adapter
            self.adapter = DuplicateFlowAdapter()
            self.bridge = ProgressBridge()

            # Verify adapter initialization
            status = self.adapter.check_availability()
            if not status['available']:
                error_msg = f"duplicateFlow adapter initialization failed: {status.get('error', 'Unknown error')}"
                logger.error(error_msg)
                self.error.emit(error_msg)
                return

            logger.info(f"duplicateFlow available: version {status.get('version', 'unknown')}")

            # Connect progress bridge signals to worker signals
            self.bridge.progress.connect(self._on_bridge_progress)
            self.bridge.stage_changed.connect(self._on_stage_changed)
            self.bridge.message.connect(self._on_message)
            self.bridge.error.connect(self._on_bridge_error)

            # Generate pairs to compare
            pairs = self._generate_pairs()
            self.total_comparisons = len(pairs)

            if self.total_comparisons == 0:
                logger.info("No pairs to compare")
                self.status_update.emit("No video pairs to compare")
                self.finished.emit()
                return

            logger.info(f"Starting comparison of {self.total_comparisons} pairs using preset '{self.preset}'")
            self.status_update.emit(
                f"Comparing {self.total_comparisons} pairs using {self.preset} preset..."
            )

            # Compare each pair
            start_time = time.time()

            for i, (file1, file2) in enumerate(pairs):
                # Check for cancellation
                if self._stop:
                    logger.info("Comparison cancelled by user")
                    self.status_update.emit("Comparison cancelled")
                    break

                # Emit comparison details
                self.comparison_details.emit(
                    i + 1,
                    self.total_comparisons,
                    Path(file1).name,
                    Path(file2).name
                )

                # Reset bridge for new comparison
                self.bridge.reset()

                # Compare videos using adapter
                try:
                    # Use custom pipeline if provided, otherwise use preset
                    if self.pipeline_config:
                        result = self.adapter.compare_videos_with_pipeline(
                            file1,
                            file2,
                            pipeline_config=self.pipeline_config,
                            progress_callback=self.bridge.callback
                        )
                    else:
                        result = self.adapter.compare_videos(
                            file1,
                            file2,
                            preset=self.preset,
                            progress_callback=self.bridge.callback
                        )

                    # Update processed count
                    self.processed_count += 1
                    self.progress.emit(self.processed_count)

                    # Check if it's a duplicate
                    if result['accepted'] and result['similarity'] >= self.threshold:
                        logger.info(
                            f"Duplicate found: {Path(file1).name} <-> {Path(file2).name} "
                            f"(similarity: {result['similarity']:.1f}%)"
                        )

                        # Emit duplicate found signal
                        self.duplicate_found.emit(
                            file1,
                            file2,
                            result['similarity'],
                            result.get('metadata', {})
                        )

                    else:
                        logger.debug(
                            f"Not a duplicate: {Path(file1).name} <-> {Path(file2).name} "
                            f"(similarity: {result['similarity']:.1f}%)"
                        )

                except Exception as e:
                    logger.error(f"Comparison failed for {Path(file1).name} <-> {Path(file2).name}: {e}")
                    # Continue with next pair instead of stopping

            # Calculate elapsed time
            elapsed = time.time() - start_time
            avg_time = elapsed / max(self.processed_count, 1)

            logger.info(
                f"Comparison complete: {self.processed_count}/{self.total_comparisons} pairs "
                f"in {elapsed:.1f}s (avg: {avg_time:.1f}s/pair)"
            )

            self.status_update.emit(
                f"Comparison complete: {self.processed_count} pairs analyzed in {elapsed:.1f}s"
            )

        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            self.error.emit(f"Comparison error: {str(e)}")

        finally:
            self.finished.emit()

    def _generate_pairs(self) -> List[Tuple[str, str]]:
        """
        Generate pairs of files to compare.

        If specific_pairs is provided, use those. Otherwise, generate
        all possible pairs (N choose 2).

        Returns:
            List of (file1, file2) tuples to compare
        """
        if self.specific_pairs:
            logger.info(f"Using {len(self.specific_pairs)} specific pairs")
            return self.specific_pairs

        # Generate all pairs
        pairs = []
        for i in range(len(self.files)):
            for j in range(i + 1, len(self.files)):
                pairs.append((self.files[i], self.files[j]))

        logger.info(f"Generated {len(pairs)} pairs from {len(self.files)} files")
        return pairs

    def _on_bridge_progress(self, stage: str, current: int, total: int) -> None:
        """
        Handle progress updates from ProgressBridge.

        Args:
            stage: Current processing stage
            current: Current progress count
            total: Total items to process
        """
        # We mainly use this for logging, actual progress is tracked per-comparison
        if total > 0:
            pct = (current / total) * 100
            logger.debug(f"Stage '{stage}': {current}/{total} ({pct:.0f}%)")

    def _on_stage_changed(self, stage: str) -> None:
        """
        Handle stage change from ProgressBridge.

        Args:
            stage: New stage name
        """
        logger.debug(f"Stage changed: {stage}")
        self.stage_update.emit(stage)

    def _on_message(self, message: str) -> None:
        """
        Handle informational messages from ProgressBridge.

        Args:
            message: Message to display
        """
        logger.debug(f"Bridge message: {message}")
        self.status_update.emit(message)

    def _on_bridge_error(self, error: str) -> None:
        """
        Handle errors from ProgressBridge.

        Args:
            error: Error message
        """
        logger.error(f"Bridge error: {error}")
        self.error.emit(error)

    def stop(self) -> None:
        """
        Request worker to stop gracefully.

        This sets a flag that will be checked between comparisons.
        The worker will finish the current comparison before stopping.
        """
        self._mutex.lock()
        self._stop = True
        self._mutex.unlock()

        # Cancel progress bridge if active
        if self.bridge:
            self.bridge.cancel()

        logger.info("Stop requested")

    def is_stopped(self) -> bool:
        """
        Check if worker has been requested to stop.

        Returns:
            True if stop was requested, False otherwise
        """
        self._mutex.lock()
        stopped = self._stop
        self._mutex.unlock()
        return stopped


# Test code
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    def on_duplicate(file1, file2, similarity, metadata):
        print(f"Duplicate: {Path(file1).name} <-> {Path(file2).name} ({similarity:.1f}%)")
        print(f"  Methods: {metadata.get('methods_used', [])}")

    def on_progress(count):
        print(f"Progress: {count} comparisons completed")

    def on_status(msg):
        print(f"Status: {msg}")

    def on_finished():
        print("Finished!")
        app.quit()

    # Test worker (needs actual video files)
    worker = DuplicateFlowWorker(
        files=['test1.mp4', 'test2.mp4'],
        preset='fast',
        threshold=70.0
    )

    worker.duplicate_found.connect(on_duplicate)
    worker.progress.connect(on_progress)
    worker.status_update.connect(on_status)
    worker.finished.connect(on_finished)

    print("Starting worker test...")
    worker.start()

    sys.exit(app.exec())
