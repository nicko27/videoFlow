"""
Worker for audio fingerprint comparison with LSH and multi-resolution.

Compares audio fingerprints efficiently using:
1. LSH to reduce pair candidates (O(N²) → O(N·k))
2. Metadata filtering (optional)
3. Multi-resolution comparison (coarse → medium → fine)
"""
from PyQt6.QtCore import QThread, pyqtSignal
from typing import List, Dict, Set, Tuple
import numpy as np
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.AudioComparisonWorker')


class AudioComparisonWorker(QThread):
    """
    Background worker for audio fingerprint comparison.

    Signals:
        progress: (current, total) - Emitted for each comparison
        candidate_found: (video1, video2, similarity) - Emitted for each match
        finished: (matches_list) - Emitted when comparison is complete
        error: (error_message) - Emitted on error
    """

    progress = pyqtSignal(int, int)  # current, total
    candidate_found = pyqtSignal(str, str, float)  # video1, video2, similarity
    finished = pyqtSignal(list)  # [(video1, video2, similarity), ...]
    error = pyqtSignal(str)

    def __init__(
        self,
        fingerprints: Dict[str, np.ndarray],
        lsh_index,  # LSHIndex instance
        multi_res_comparator,  # MultiResolutionComparator instance
        metadata_filter,  # MetadataFilter instance or None
        audio_threshold: float = 70.0,
        use_lsh: bool = True,
        use_multi_res: bool = True,
        use_metadata: bool = False
    ):
        """
        Initialize audio comparison worker.

        Args:
            fingerprints: Dictionary of {video_path: fingerprint}
            lsh_index: LSH index (pre-populated)
            multi_res_comparator: Multi-resolution comparator
            metadata_filter: Metadata filter or None
            audio_threshold: Minimum similarity threshold (%)
            use_lsh: Whether to use LSH filtering
            use_multi_res: Whether to use multi-resolution comparison
            use_metadata: Whether to use metadata filtering
        """
        super().__init__()
        self.fingerprints = fingerprints
        self.lsh_index = lsh_index
        self.multi_res_comparator = multi_res_comparator
        self.metadata_filter = metadata_filter
        self.audio_threshold = audio_threshold
        self.use_lsh = use_lsh
        self.use_multi_res = use_multi_res
        self.use_metadata = use_metadata
        self._stop_flag = False

        logger.info(f"Audio comparison worker initialized: {len(fingerprints)} videos, "
                   f"threshold={audio_threshold}%, LSH={use_lsh}, "
                   f"multi-res={use_multi_res}, metadata={use_metadata}")

    def run(self):
        """Compare audio fingerprints."""
        try:
            matches = []
            video_paths = list(self.fingerprints.keys())

            # Generate candidate pairs
            if self.use_lsh:
                logger.info("Using LSH to generate candidate pairs...")
                pairs = self.lsh_index.get_candidate_pairs()
            else:
                logger.info("Generating all possible pairs (no LSH)...")
                pairs = set()
                for i in range(len(video_paths)):
                    for j in range(i + 1, len(video_paths)):
                        pair = tuple(sorted([video_paths[i], video_paths[j]]))
                        pairs.add(pair)

            total_pairs = len(pairs)
            logger.info(f"Comparing {total_pairs} audio pairs...")

            # Apply metadata filter if enabled
            if self.use_metadata and self.metadata_filter:
                logger.info("Applying metadata filter...")
                # Get metadata for all videos
                metadata_cache = {}
                for video_path in video_paths:
                    metadata_cache[video_path] = self.metadata_filter.get_metadata(video_path)

                pairs = self.metadata_filter.filter_pairs(pairs, metadata_cache)
                logger.info(f"After metadata filter: {len(pairs)} pairs")

            # Compare pairs
            processed = 0
            for video1, video2 in pairs:
                if self._stop_flag:
                    logger.info("Audio comparison stopped by user")
                    return

                processed += 1

                fp1 = self.fingerprints.get(video1)
                fp2 = self.fingerprints.get(video2)

                if fp1 is None or fp2 is None:
                    continue

                # Compare with multi-resolution if enabled
                if self.use_multi_res:
                    similarity = self.multi_res_comparator.compare(
                        fp1, fp2,
                        full_threshold=self.audio_threshold
                    )
                else:
                    # Direct comparison
                    similarity = self._compare_fingerprints(fp1, fp2)
                    if similarity < self.audio_threshold:
                        similarity = None

                # Emit progress
                self.progress.emit(processed, len(pairs))

                # If match found, emit and store
                if similarity is not None:
                    self.candidate_found.emit(video1, video2, similarity)
                    matches.append((video1, video2, similarity))

            logger.info(f"Audio comparison complete: {len(matches)} matches found")
            self.finished.emit(matches)

        except Exception as e:
            error_msg = f"Error in audio comparison worker: {e}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)

    def _compare_fingerprints(self, fp1: np.ndarray, fp2: np.ndarray) -> float:
        """
        Simple fingerprint comparison.

        Args:
            fp1: First fingerprint
            fp2: Second fingerprint

        Returns:
            Similarity percentage (0-100)
        """
        if len(fp1) == 0 or len(fp2) == 0:
            return 0.0

        min_len = min(len(fp1), len(fp2))
        fp1_aligned = fp1[:min_len]
        fp2_aligned = fp2[:min_len]

        matches = np.sum(fp1_aligned == fp2_aligned)
        similarity = (matches / min_len) * 100.0

        return similarity

    def stop(self):
        """Stop the worker."""
        logger.info("Stopping audio comparison worker...")
        self._stop_flag = True
