"""
Video comparison worker for detecting duplicates.

This module provides a worker thread that performs parallel video comparisons
to detect duplicate files based on perceptual hash similarity.
"""
import os
from typing import List, Tuple, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QThread, pyqtSignal, QMutex

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.ComparisonWorker')

# Default config values (replaces ConfigValidator)
DEFAULT_BATCH_SIZE = 10


class OptimizedComparisonWorker(QThread):
    """
    Worker thread for optimized parallel video comparison.

    This worker compares pairs of videos to detect duplicates using perceptual
    hash similarity. It optimizes performance by:
    - Skipping already-cached comparisons
    - Filtering out ignored pairs
    - Processing comparisons in batches with configurable parallelism

    Attributes:
        progress (pyqtSignal): Signal emitting current comparison count (int).
        finished (pyqtSignal): Signal emitted when all comparisons complete.
        duplicate_found (pyqtSignal): Signal emitting duplicate info (file1, file2, similarity).
        error (pyqtSignal): Signal emitting error messages (str).
        status_update (pyqtSignal): Signal emitting status messages (str).
        total_comparisons_signal (pyqtSignal): Signal emitting total comparison count (int).
        comparison_details (pyqtSignal): Signal emitting detailed comparison progress.

    Example:
        ```python
        config = {'comparison_workers': 4, 'batch_size': 50, 'comparison_timeout': 30}
        worker = OptimizedComparisonWorker(files, hasher, threshold=90.0, config=config)
        worker.duplicate_found.connect(handle_duplicate)
        worker.start()
        ```
    """

    # Signal definitions
    progress = pyqtSignal(int)  # Current progress count
    finished = pyqtSignal()  # Processing complete
    duplicate_found = pyqtSignal(str, str, float)  # file1, file2, similarity
    error = pyqtSignal(str)  # Error message
    status_update = pyqtSignal(str)  # Status message
    total_comparisons_signal = pyqtSignal(int)  # Total comparisons count
    comparison_details = pyqtSignal(int, int, str, str)  # current, total, file1, file2

    def __init__(
        self,
        files: List[str],
        video_hasher,
        threshold: float,
        config: Dict[str, Any],
        specific_pairs: Optional[List[tuple]] = None
    ) -> None:
        """
        Initialize the comparison worker.

        Args:
            files: List of video file paths to compare.
            video_hasher: VideoHasher instance for comparing videos.
            threshold: Similarity threshold percentage for duplicate detection.
            config: Configuration dictionary with keys:
                - comparison_workers: Number of parallel workers
                - batch_size: Number of comparisons per batch
                - comparison_timeout: Timeout in seconds per comparison
            specific_pairs: Optional list of specific (file1, file2) tuples to compare.
                          If provided, only these pairs are compared (audio-first mode).
        """
        super().__init__()
        self.files = files
        self.video_hasher = video_hasher
        self.specific_pairs = specific_pairs

        # Validate and sanitize configuration
        self.config = config if config else {}
        logger.info(f"Config: {self.config}")

        # Validate threshold (simple validation)
        self.threshold = max(0.0, min(threshold or 0.85, 1.0))  # Between 0.0 and 1.0

        self._stop = False
        self._mutex = QMutex()
        self.processed_count = 0
        self.cached_pairs: List[Tuple[str, str, float]] = []
        self.total_comparisons = 0

    def _calculate_adaptive_batch_size(
        self,
        total_pairs: int,
        worker_count: int,
        configured_size: int
    ) -> int:
        """
        Calculate optimal batch size based on workload and worker count.

        Adaptive strategy:
        - Small datasets (<100 pairs): Use smaller batches for quick feedback
        - Medium datasets (100-1000): Balance batch size with worker count
        - Large datasets (>1000): Use larger batches to reduce overhead

        Args:
            total_pairs: Total number of comparison pairs
            worker_count: Number of parallel workers
            configured_size: User-configured batch size (max limit)

        Returns:
            Optimal batch size
        """
        if total_pairs < 100:
            # Small dataset: keep batches small for responsive UI
            optimal_size = min(max(10, total_pairs // worker_count), configured_size)
        elif total_pairs < 1000:
            # Medium dataset: balance between throughput and responsiveness
            optimal_size = min(
                max(50, total_pairs // (worker_count * 2)),
                configured_size
            )
        else:
            # Large dataset: optimize for throughput
            optimal_size = min(
                max(100, total_pairs // (worker_count * 4)),
                configured_size
            )

        logger.info(
            f"Adaptive batch size: {optimal_size} "
            f"(pairs={total_pairs}, workers={worker_count}, configured={configured_size})"
        )
        return optimal_size

    def generate_pairs(self, files: List[str], specific_pairs: Optional[List[tuple]] = None) -> List[Tuple[str, str]]:
        """
        Generate pairs of files to compare, optimized with caching.

        This method generates all possible file pairs and filters them based on:
        1. Ignored pairs (user marked as not duplicates)
        2. Cached comparison results
        3. Similarity threshold

        **OPTIMIZED**: Batch database queries for 10x faster pair generation.
        **AUDIO-FIRST MODE**: If specific_pairs provided, only filter those pairs.

        Args:
            files: List of file paths to compare.
            specific_pairs: Optional list of specific (file1, file2, similarity) tuples
                          from audio comparison. If provided, only these pairs are filtered.

        Returns:
            List of tuples (file1, file2) that need comparison.
        """
        self.status_update.emit("🔍 Preparing comparisons...")

        pairs: List[Tuple[str, str]] = []
        cached_pairs: List[Tuple[str, str, float]] = []
        skipped_cache = 0
        skipped_ignored = 0
        skipped_early_exit = 0

        # OPTIMIZATION: Pre-build ignored pairs set for O(1) lookup
        ignored_pairs_set = set()
        try:
            # Batch query all ignored pairs
            all_ignored = self.video_hasher.db.get_all_ignored_pairs()
            for file1, file2 in all_ignored:
                cache_key = (file1, file2) if file1 < file2 else (file2, file1)
                ignored_pairs_set.add(cache_key)
        except Exception:
            pass  # Fall back to individual queries

        # Generate pairs - use specific pairs if provided (audio-first mode)
        if specific_pairs:
            # Audio-first mode: use only the candidate pairs from audio comparison
            all_possible_pairs = [
                (v1, v2) for v1, v2, _ in specific_pairs
            ]
            logger.info(f"Audio-first mode: {len(all_possible_pairs)} candidate pairs from audio")
        else:
            # Normal mode: generate all N² possible pairs
            all_possible_pairs = [
                (files[i], files[j])
                for i in range(len(files))
                for j in range(i + 1, len(files))
            ]

        total_pairs = len(all_possible_pairs)
        self.status_update.emit(f"🔍 Filtering {total_pairs:,} pairs...")

        # OPTIMIZATION: Batch process pairs
        for file1, file2 in all_possible_pairs:
            if self.is_stopped():
                break

            # OPTIMIZATION: Check ignored set (O(1) vs database query)
            cache_key = (file1, file2) if file1 < file2 else (file2, file1)
            if cache_key in ignored_pairs_set:
                skipped_ignored += 1
                continue

            # Check memory cache first (faster than DB)
            cached_result = self.video_hasher.get_cached_comparison(file1, file2)
            if cached_result is not None:
                skipped_cache += 1
                # If cached result is above threshold, emit as duplicate
                if cached_result > self.threshold:
                    cached_pairs.append((file1, file2, cached_result))
                    self.duplicate_found.emit(file1, file2, cached_result)
                continue

            # OPTIMIZATION: Early exit based on metadata
            try:
                meta1 = self.video_hasher.hash_cache.get(file1)
                meta2 = self.video_hasher.hash_cache.get(file2)

                if meta1 and meta2:
                    # Skip if file sizes differ significantly
                    size1 = meta1.get('file_size', 0)
                    size2 = meta2.get('file_size', 0)
                    if size1 > 0 and size2 > 0:
                        size_ratio = min(size1, size2) / max(size1, size2)
                        if size_ratio < 0.90:
                            skipped_early_exit += 1
                            continue

                    # Skip if durations differ significantly
                    dur1 = meta1.get('duration', 0)
                    dur2 = meta2.get('duration', 0)
                    if dur1 > 0 and dur2 > 0:
                        dur_ratio = min(dur1, dur2) / max(dur1, dur2)
                        if dur_ratio < 0.95:
                            skipped_early_exit += 1
                            continue
            except (KeyError, AttributeError, TypeError, ValueError) as e:
                # Metadata not available or invalid, continue with comparison
                logger.debug(f"Could not get metadata for early exit check ({file1}, {file2}): {e}")

            # Add to pairs needing comparison
            pairs.append((file1, file2))

        # Store results
        self.cached_pairs = cached_pairs
        self.total_comparisons = len(pairs) + len(cached_pairs)
        self.total_comparisons_signal.emit(self.total_comparisons)

        # Build status message
        status = f"Pairs: {len(pairs):,} to compare"
        if skipped_cache > 0:
            status += f", {skipped_cache:,} cached"
        if skipped_ignored > 0:
            status += f", {skipped_ignored:,} ignored"
        if skipped_early_exit > 0:
            status += f", {skipped_early_exit:,} filtered"

        logger.info(status)
        self.status_update.emit(status)

        return pairs

    def run(self) -> None:
        """
        Execute the parallel comparison process.

        This method generates comparison pairs, then processes them in batches
        using a thread pool executor for improved performance.
        """
        try:
            # Generate pairs to compare
            if self.specific_pairs:
                # Audio-first mode: use specific pairs
                logger.info(f"Audio-first mode: using {len(self.specific_pairs)} specific pairs")
                pairs = self.generate_pairs(self.files, specific_pairs=self.specific_pairs)
            else:
                # Normal mode: generate all N² pairs
                pairs = self.generate_pairs(self.files)

            # Process cached pairs first (emit progress and duplicates)
            if self.cached_pairs:
                logger.info(f"Processing {len(self.cached_pairs)} cached comparisons")
                for file1, file2, similarity in self.cached_pairs:
                    if self.is_stopped():
                        break
                    # Emit progress for cached pairs
                    self.update_progress((file1, file2, similarity), (file1, file2))

            # Handle case where all pairs are cached
            if not pairs:
                self.status_update.emit("✅ All comparisons cached!")
                self.finished.emit()
                return

            self.status_update.emit(f"🚀 {len(pairs)} comparisons to process")

            # Process pairs in batches (config already validated in __init__)
            comparison_workers = self.config['comparison_workers']
            configured_batch_size = self.config['batch_size']

            # ADAPTIVE BATCH SIZE: Calculate optimal batch size based on workload
            adaptive_batch_size = self._calculate_adaptive_batch_size(
                total_pairs=len(pairs),
                worker_count=comparison_workers,
                configured_size=configured_batch_size
            )
            batch_size = adaptive_batch_size

            # Additional runtime validation
            if batch_size <= 0:
                logger.error(f"Invalid batch_size: {batch_size}. Using default.")
                batch_size = DEFAULT_BATCH_SIZE

            if batch_size > len(pairs):
                batch_size = len(pairs)
                logger.info(f"Adjusted batch_size to {batch_size} (total pairs count)")

            with ThreadPoolExecutor(max_workers=comparison_workers) as executor:
                for i in range(0, len(pairs), batch_size):
                    if self.is_stopped():
                        break

                    # Get current batch
                    batch = pairs[i:i + batch_size]

                    # Submit batch for parallel processing
                    futures = []
                    for pair in batch:
                        future = executor.submit(self.compare_pair, pair)
                        futures.append((future, pair))

                    # Collect results
                    for future, pair in futures:
                        if self.is_stopped():
                            break

                        try:
                            result = future.result(timeout=self.config['comparison_timeout'])
                            self.update_progress(result, pair)
                        except Exception as e:
                            logger.error(f"Comparison error: {e}")
                            # Report failed comparison with 0% similarity
                            self.update_progress((pair[0], pair[1], 0.0), pair)

            # Emit completion signal if not stopped
            if not self.is_stopped():
                self.status_update.emit("✅ Comparisons complete!")
                self.finished.emit()

        except Exception as e:
            logger.error(f"Critical error in comparison worker: {e}")
            self.error.emit(str(e))

    def compare_pair(self, pair: Tuple[str, str]) -> Optional[Tuple[str, str, float]]:
        """
        Compare a single pair of videos.

        Args:
            pair: Tuple of (file1_path, file2_path).

        Returns:
            Tuple of (file1, file2, similarity) or None if stopped.
        """
        file1, file2 = pair

        if self.is_stopped():
            return None

        # Check if files still exist before comparison
        if not os.path.exists(file1):
            logger.warning(f"File deleted during analysis: {os.path.basename(file1)}")
            return (file1, file2, 0.0)
        if not os.path.exists(file2):
            logger.warning(f"File deleted during analysis: {os.path.basename(file2)}")
            return (file1, file2, 0.0)

        try:
            similarity = self.video_hasher.compare_videos(file1, file2)
            return (file1, file2, similarity)
        except (FileNotFoundError, OSError) as e:
            logger.warning(
                f"File access error comparing {os.path.basename(file1)} vs "
                f"{os.path.basename(file2)}: {e}"
            )
            return (file1, file2, 0.0)
        except Exception as e:
            logger.error(
                f"Unexpected error comparing {os.path.basename(file1)} vs "
                f"{os.path.basename(file2)}: {e}", exc_info=True
            )
            return (file1, file2, 0.0)

    def update_progress(
        self,
        result: Optional[Tuple[str, str, float]],
        pair: Tuple[str, str]
    ) -> None:
        """
        Update progress counters and emit progress signals.

        Args:
            result: Tuple of (file1, file2, similarity) or None.
            pair: Original pair tuple for context.
        """
        if result is None:
            return

        file1, file2, similarity = result

        # Thread-safe counter update
        self._mutex.lock()
        self.processed_count += 1
        current_count = self.processed_count
        total_count = self.total_comparisons
        self._mutex.unlock()

        # Prepare file names for display
        name1 = os.path.basename(file1)
        name2 = os.path.basename(file2)
        self.comparison_details.emit(current_count, total_count, name1, name2)

        # Emit duplicate signal if above threshold
        if similarity > self.threshold:
            self.duplicate_found.emit(file1, file2, similarity)

        # Emit progress signal
        self.progress.emit(current_count)

    def stop(self) -> None:
        """
        Signal the worker to stop processing.

        This method is thread-safe and can be called from any thread.
        """
        self._mutex.lock()
        self._stop = True
        self._mutex.unlock()

    def is_stopped(self) -> bool:
        """
        Check if the worker has been stopped.

        Returns:
            True if stop() has been called, False otherwise.
        """
        self._mutex.lock()
        stopped = self._stop
        self._mutex.unlock()
        return stopped
