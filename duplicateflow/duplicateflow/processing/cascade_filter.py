"""
Cascade filter for fast elimination of non-matching windows.

Three-stage filtering eliminates 95-99% of windows quickly:
- Stage 1: Ultra-fast hash (3 frames) - 1ms per window
- Stage 2: Quick histogram (5 frames) - 10ms per window
- Stage 3: Full algorithm on survivors
"""

import logging
from typing import List, Tuple, Dict, Any
import numpy as np
import cv2
from tqdm import tqdm

logger = logging.getLogger('duplicateflow.processing.cascade_filter')


class CascadeFilter:
    """
    Three-stage cascade filter for rapid window elimination.

    Progressively filters windows using increasingly accurate (but slower) methods.

    Example:
        >>> filter = CascadeFilter()
        >>> candidates = filter.filter_windows(
        ...     windows, short_video, long_video,
        ...     stage1_threshold=40, stage2_threshold=55
        ... )
        >>> # Only 1-5% of windows remain for full analysis
    """

    def __init__(self):
        """Initialize cascade filter."""
        self.stats = {
            'total_windows': 0,
            'stage1_survivors': 0,
            'stage2_survivors': 0,
            'stage1_time': 0.0,
            'stage2_time': 0.0
        }

    def filter_windows(
        self,
        windows: List[float],
        short_video: str,
        long_video: str,
        short_duration: float,
        stage1_threshold: float = 40.0,
        stage2_threshold: float = 55.0,
        show_progress: bool = True
    ) -> List[float]:
        """
        Filter windows through cascade stages.

        Args:
            windows: List of window start times
            short_video: Short video path
            long_video: Long video path
            short_duration: Duration of short video
            stage1_threshold: Threshold for stage 1 (low to avoid false negatives)
            stage2_threshold: Threshold for stage 2
            show_progress: Show progress bars

        Returns:
            List of candidate window positions that passed all filters
        """
        import time

        self.stats['total_windows'] = len(windows)

        logger.info(f"Cascade filter: {len(windows)} windows to process")

        # Stage 1: Ultra-fast hash filter
        logger.info("Stage 1: Quick hash filter (3 frames)")
        start = time.time()

        stage1_candidates = self._stage1_hash_filter(
            windows,
            short_video,
            long_video,
            short_duration,
            stage1_threshold,
            show_progress
        )

        self.stats['stage1_time'] = time.time() - start
        self.stats['stage1_survivors'] = len(stage1_candidates)

        elimination_rate = (1 - len(stage1_candidates) / len(windows)) * 100
        logger.info(
            f"Stage 1 complete: {len(stage1_candidates)}/{len(windows)} survivors "
            f"({elimination_rate:.1f}% eliminated) "
            f"in {self.stats['stage1_time']:.2f}s"
        )

        if not stage1_candidates:
            return []

        # Stage 2: Histogram filter
        logger.info("Stage 2: Histogram filter (5 frames)")
        start = time.time()

        stage2_candidates = self._stage2_histogram_filter(
            stage1_candidates,
            short_video,
            long_video,
            short_duration,
            stage2_threshold,
            show_progress
        )

        self.stats['stage2_time'] = time.time() - start
        self.stats['stage2_survivors'] = len(stage2_candidates)

        elimination_rate = (1 - len(stage2_candidates) / len(stage1_candidates)) * 100
        logger.info(
            f"Stage 2 complete: {len(stage2_candidates)}/{len(stage1_candidates)} survivors "
            f"({elimination_rate:.1f}% eliminated) "
            f"in {self.stats['stage2_time']:.2f}s"
        )

        total_elimination = (1 - len(stage2_candidates) / len(windows)) * 100
        logger.info(
            f"Cascade complete: {len(stage2_candidates)}/{len(windows)} final candidates "
            f"({total_elimination:.1f}% total elimination)"
        )

        return stage2_candidates

    def _stage1_hash_filter(
        self,
        windows: List[float],
        short_video: str,
        long_video: str,
        duration: float,
        threshold: float,
        show_progress: bool
    ) -> List[float]:
        """
        Stage 1: Quick hash comparison using only 3 frames.

        Samples start, middle, end frames and compares perceptual hashes.
        Very fast (~1ms per window) but less accurate.
        """
        from duplicateflow.algorithms.base.video_loader import VideoLoader

        # Extract reference frames from short video
        reference_hashes = self._extract_quick_hashes(short_video, num_frames=3)

        if not reference_hashes:
            logger.warning("Could not extract reference hashes")
            return windows

        candidates = []

        iterator = windows
        if show_progress:
            iterator = tqdm(windows, desc="Stage 1: Hash filter")

        with VideoLoader(long_video) as loader:
            for window_start in iterator:
                # Sample 3 frames from window
                offsets = [
                    window_start,
                    window_start + duration / 2,
                    window_start + duration * 0.99
                ]

                window_hashes = []
                for offset in offsets:
                    frame = loader.get_frame(offset)
                    if frame is not None:
                        hash_val = self._compute_perceptual_hash(frame)
                        window_hashes.append(hash_val)

                if len(window_hashes) == 3:
                    # Compare hashes
                    score = self._compare_hashes(reference_hashes, window_hashes)

                    if score >= threshold:
                        candidates.append(window_start)

        return candidates

    def _stage2_histogram_filter(
        self,
        windows: List[float],
        short_video: str,
        long_video: str,
        duration: float,
        threshold: float,
        show_progress: bool
    ) -> List[float]:
        """
        Stage 2: Histogram comparison using 5 frames.

        More accurate than hashes but still fast (~10ms per window).
        """
        from duplicateflow.algorithms.base.video_loader import VideoLoader

        # Extract reference histograms from short video
        reference_hists = self._extract_histograms(short_video, num_frames=5)

        if not reference_hists:
            logger.warning("Could not extract reference histograms")
            return windows

        candidates = []

        iterator = windows
        if show_progress:
            iterator = tqdm(windows, desc="Stage 2: Histogram filter")

        with VideoLoader(long_video) as loader:
            for window_start in iterator:
                # Sample 5 frames uniformly from window
                window_hists = []

                for i in range(5):
                    offset = window_start + (duration * i / 4)
                    frame = loader.get_frame(offset)

                    if frame is not None:
                        hist = self._compute_histogram(frame)
                        window_hists.append(hist)

                if len(window_hists) == 5:
                    # Compare histograms
                    score = self._compare_histograms(reference_hists, window_hists)

                    if score >= threshold:
                        candidates.append(window_start)

        return candidates

    def _extract_quick_hashes(self, video_path: str, num_frames: int = 3) -> List[int]:
        """Extract perceptual hashes from video."""
        from duplicateflow.algorithms.base.video_loader import VideoLoader

        hashes = []

        with VideoLoader(video_path) as loader:
            duration = loader.duration

            for i in range(num_frames):
                offset = duration * i / (num_frames - 1 if num_frames > 1 else 1)
                frame = loader.get_frame(offset)

                if frame is not None:
                    hash_val = self._compute_perceptual_hash(frame)
                    hashes.append(hash_val)

        return hashes

    def _extract_histograms(self, video_path: str, num_frames: int = 5) -> List[np.ndarray]:
        """Extract color histograms from video."""
        from duplicateflow.algorithms.base.video_loader import VideoLoader

        histograms = []

        with VideoLoader(video_path) as loader:
            duration = loader.duration

            for i in range(num_frames):
                offset = duration * i / (num_frames - 1 if num_frames > 1 else 1)
                frame = loader.get_frame(offset)

                if frame is not None:
                    hist = self._compute_histogram(frame)
                    histograms.append(hist)

        return histograms

    def _compute_perceptual_hash(self, frame: np.ndarray) -> int:
        """
        Compute simple perceptual hash (average hash).

        Fast and reasonable accuracy for filtering.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Resize to 8x8
        resized = cv2.resize(gray, (8, 8), interpolation=cv2.INTER_AREA)

        # Compute average
        avg = resized.mean()

        # Create hash
        diff = resized > avg
        hash_val = sum([2**i for (i, v) in enumerate(diff.flatten()) if v])

        return hash_val

    def _compute_histogram(self, frame: np.ndarray) -> np.ndarray:
        """Compute normalized HSV color histogram."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Compute histogram
        hist = cv2.calcHist(
            [hsv], [0, 1, 2], None,
            [8, 8, 8],
            [0, 180, 0, 256, 0, 256]
        )

        # Normalize
        hist = cv2.normalize(hist, hist).flatten()

        return hist

    def _compare_hashes(self, hashes1: List[int], hashes2: List[int]) -> float:
        """
        Compare two lists of hashes using Hamming distance.

        Returns similarity score 0-100.
        """
        if len(hashes1) != len(hashes2):
            return 0.0

        total_similarity = 0.0

        for h1, h2 in zip(hashes1, hashes2):
            # XOR to find differing bits
            xor = h1 ^ h2

            # Count differing bits (Hamming distance)
            hamming_dist = bin(xor).count('1')

            # Convert to similarity (max 64 bits for 8x8 hash)
            similarity = (64 - hamming_dist) / 64.0 * 100.0
            total_similarity += similarity

        return total_similarity / len(hashes1)

    def _compare_histograms(
        self,
        hists1: List[np.ndarray],
        hists2: List[np.ndarray]
    ) -> float:
        """
        Compare two lists of histograms using correlation.

        Returns similarity score 0-100.
        """
        if len(hists1) != len(hists2):
            return 0.0

        total_similarity = 0.0

        for h1, h2 in zip(hists1, hists2):
            # Use correlation method
            correlation = cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL)

            # Convert to 0-100 scale (correlation is -1 to 1, but typically 0-1)
            similarity = max(0.0, correlation) * 100.0
            total_similarity += similarity

        return total_similarity / len(hists1)

    def get_stats(self) -> Dict[str, Any]:
        """Get filter statistics."""
        total = self.stats['total_windows']
        if total == 0:
            return self.stats

        return {
            **self.stats,
            'stage1_elimination_rate': (1 - self.stats['stage1_survivors'] / total) * 100,
            'stage2_elimination_rate': (
                (1 - self.stats['stage2_survivors'] / self.stats['stage1_survivors']) * 100
                if self.stats['stage1_survivors'] > 0 else 0
            ),
            'total_elimination_rate': (1 - self.stats['stage2_survivors'] / total) * 100,
            'avg_stage1_time_per_window_ms': (
                self.stats['stage1_time'] / total * 1000 if total > 0 else 0
            ),
            'avg_stage2_time_per_window_ms': (
                self.stats['stage2_time'] / self.stats['stage1_survivors'] * 1000
                if self.stats['stage1_survivors'] > 0 else 0
            )
        }
