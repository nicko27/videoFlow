"""
Parallel window search for massive performance improvements.

Uses ThreadPoolExecutor to process multiple windows simultaneously.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from tqdm import tqdm

logger = logging.getLogger('duplicateflow.processing.parallel_search')


class ParallelWindowSearch:
    """
    Parallel window-based search using multi-threading.

    Processes multiple windows simultaneously for 4-8x speedup on modern CPUs.

    Example:
        >>> searcher = ParallelWindowSearch(num_workers=8)
        >>> result = searcher.search(short_video, long_video, algorithm='frame_hash')
        >>> print(f"Best match at {result['offset']}s with score {result['score']:.2f}%")
    """

    def __init__(self, num_workers: Optional[int] = None):
        """
        Initialize parallel searcher.

        Args:
            num_workers: Number of worker threads (default: CPU count)
        """
        self.num_workers = num_workers or os.cpu_count() or 4
        logger.info(f"Initialized parallel search with {self.num_workers} workers")

    def search(
        self,
        short_video: str,
        long_video: str,
        algorithm: str,
        algorithm_instance: Any,
        step_size: float = 5.0,
        start_time: float = 0.0,
        end_time: Optional[float] = None,
        show_progress: bool = True,
        early_stop_threshold: float = 95.0
    ) -> Dict[str, Any]:
        """
        Search for short video in long video using parallel window processing.

        Args:
            short_video: Path to short video
            long_video: Path to long video
            algorithm: Algorithm name
            algorithm_instance: Configured algorithm instance
            step_size: Step size between windows in seconds
            start_time: Start time in long video
            end_time: End time in long video (None = full video)
            show_progress: Show progress bar
            early_stop_threshold: Stop if score exceeds this threshold

        Returns:
            Dictionary with best match results
        """
        from duplicateflow.algorithms.base.video_loader import get_video_duration

        # Get short video duration
        short_duration = get_video_duration(short_video)

        # Get search range
        long_duration = get_video_duration(long_video)
        if end_time is None:
            end_time = long_duration

        # Generate window positions
        windows = self._generate_windows(
            start_time, end_time, short_duration, step_size
        )

        logger.info(
            f"Searching {len(windows)} windows with {self.num_workers} workers"
        )

        # Process windows in parallel
        results = self._process_windows_parallel(
            windows,
            short_video,
            long_video,
            short_duration,
            algorithm,
            algorithm_instance,
            show_progress,
            early_stop_threshold
        )

        # Find best result
        if not results:
            return {
                'offset': 0.0,
                'score': 0.0,
                'accepted': False,
                'windows_tested': len(windows),
                'algorithm': algorithm
            }

        best_window, best_score = max(results, key=lambda x: x[1])

        return {
            'offset': best_window,
            'score': best_score,
            'accepted': best_score >= algorithm_instance.threshold,
            'windows_tested': len(results),
            'algorithm': algorithm,
            'total_windows': len(windows)
        }

    def _generate_windows(
        self,
        start_time: float,
        end_time: float,
        window_duration: float,
        step_size: float
    ) -> List[float]:
        """Generate list of window start positions."""
        windows = []
        current = start_time

        while current + window_duration <= end_time:
            windows.append(current)
            current += step_size

        return windows

    def _process_windows_parallel(
        self,
        windows: List[float],
        short_video: str,
        long_video: str,
        duration: float,
        algorithm: str,
        algorithm_instance: Any,
        show_progress: bool,
        early_stop_threshold: float
    ) -> List[Tuple[float, float]]:
        """Process windows in parallel using thread pool."""
        results = []
        best_score_so_far = 0.0

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit all tasks
            future_to_window = {}
            for window_start in windows:
                future = executor.submit(
                    self._process_single_window,
                    short_video,
                    long_video,
                    window_start,
                    duration,
                    algorithm_instance
                )
                future_to_window[future] = window_start

            # Collect results as they complete
            iterator = as_completed(future_to_window)
            if show_progress:
                iterator = tqdm(
                    iterator,
                    total=len(windows),
                    desc=f"Searching with {algorithm}"
                )

            for future in iterator:
                window_start = future_to_window[future]

                try:
                    score = future.result()
                    results.append((window_start, score))

                    # Update best score
                    if score > best_score_so_far:
                        best_score_so_far = score
                        if show_progress:
                            iterator.set_postfix(best_score=f"{best_score_so_far:.1f}%")

                    # Early stopping
                    if score >= early_stop_threshold:
                        logger.info(
                            f"Early stop: found excellent match "
                            f"(score={score:.2f}%) at {window_start:.1f}s"
                        )
                        # Cancel remaining tasks
                        for f in future_to_window:
                            f.cancel()
                        break

                except Exception as e:
                    logger.warning(f"Error processing window at {window_start}s: {e}")

        return results

    def _process_single_window(
        self,
        short_video: str,
        long_video: str,
        window_start: float,
        duration: float,
        algorithm_instance: Any
    ) -> float:
        """Process a single window and return similarity score."""
        try:
            # Use algorithm to compare this window
            result = algorithm_instance.compare(
                short_video=short_video,
                long_video=long_video,
                start_time=window_start,
                duration=duration
            )

            # Extract similarity score
            similarity = result.get('similarity', 0.0)

            # Convert to 0-100 scale if needed
            if similarity <= 1.0:
                similarity = similarity * 100.0

            return float(similarity)

        except Exception as e:
            logger.debug(f"Error in window at {window_start}s: {e}")
            return 0.0

    def search_batch(
        self,
        short_videos: List[str],
        long_video: str,
        algorithm: str,
        algorithm_instance: Any,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search for multiple short videos in one long video.

        Args:
            short_videos: List of short video paths
            long_video: Long video path
            algorithm: Algorithm name
            algorithm_instance: Configured algorithm instance
            **kwargs: Additional arguments for search()

        Returns:
            List of results for each short video
        """
        results = []

        for short_video in tqdm(short_videos, desc="Processing videos"):
            result = self.search(
                short_video,
                long_video,
                algorithm,
                algorithm_instance,
                show_progress=False,
                **kwargs
            )
            result['short_video'] = short_video
            results.append(result)

        return results


class AdaptiveStepSearch:
    """
    Adaptive step size search that adjusts based on score trends.

    Uses larger steps in low-score regions and smaller steps near matches.
    """

    def __init__(self, num_workers: Optional[int] = None):
        """Initialize adaptive search."""
        self.parallel_searcher = ParallelWindowSearch(num_workers)

    def search(
        self,
        short_video: str,
        long_video: str,
        algorithm: str,
        algorithm_instance: Any,
        initial_step: float = 30.0,
        fine_step: float = 2.0,
        coarse_threshold: float = 40.0,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Search with adaptive step size.

        Args:
            short_video: Path to short video
            long_video: Path to long video
            algorithm: Algorithm name
            algorithm_instance: Configured algorithm instance
            initial_step: Initial coarse step size
            fine_step: Fine step size for high-score regions
            coarse_threshold: Score threshold to trigger fine search
            show_progress: Show progress bar

        Returns:
            Best match results
        """
        from duplicateflow.algorithms.base.video_loader import get_video_duration

        short_duration = get_video_duration(short_video)
        long_duration = get_video_duration(long_video)

        logger.info("Phase 1: Coarse search with large steps")

        # Phase 1: Coarse search
        coarse_result = self.parallel_searcher.search(
            short_video,
            long_video,
            algorithm,
            algorithm_instance,
            step_size=initial_step,
            show_progress=show_progress
        )

        best_offset = coarse_result['offset']
        best_score = coarse_result['score']

        # If score is high, do fine search around best region
        if best_score >= coarse_threshold:
            logger.info(
                f"Phase 2: Fine search around {best_offset:.1f}s "
                f"(coarse score: {best_score:.2f}%)"
            )

            # Define fine search region (±2 minutes around best offset)
            fine_start = max(0, best_offset - 120)
            fine_end = min(long_duration - short_duration, best_offset + 120)

            fine_result = self.parallel_searcher.search(
                short_video,
                long_video,
                algorithm,
                algorithm_instance,
                step_size=fine_step,
                start_time=fine_start,
                end_time=fine_end,
                show_progress=show_progress
            )

            if fine_result['score'] > best_score:
                return fine_result

        return coarse_result
