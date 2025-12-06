"""
Multi-resolution audio comparison for early rejection.

Compares audio fingerprints progressively:
1. Coarse (30s sample) - Reject if similarity < 60%
2. Medium (120s sample) - Reject if similarity < 65%
3. Fine (full audio) - Final comparison

Provides 2-3x speedup by rejecting non-matches early.
"""
import numpy as np
from typing import Optional, Tuple
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.MultiResolution')


class MultiResolutionComparator:
    """
    Progressive audio comparison with early rejection.

    Uses increasingly longer audio samples to filter out non-matches quickly.

    Example:
        ```python
        comparator = MultiResolutionComparator(
            coarse_duration=30,
            coarse_threshold=60.0,
            medium_duration=120,
            medium_threshold=65.0
        )

        similarity = comparator.compare(
            fingerprint1, fingerprint2,
            full_threshold=70.0
        )

        if similarity is None:
            # Rejected in early phase
            pass
        else:
            # Passed all phases, similarity is final result
            pass
        ```
    """

    def __init__(
        self,
        coarse_duration: int = 30,
        coarse_threshold: float = 60.0,
        medium_duration: int = 120,
        medium_threshold: float = 65.0
    ):
        """
        Initialize multi-resolution comparator.

        Args:
            coarse_duration: Duration in seconds for coarse test
            coarse_threshold: Minimum similarity for coarse test (%)
            medium_duration: Duration in seconds for medium test
            medium_threshold: Minimum similarity for medium test (%)
        """
        self.coarse_duration = coarse_duration
        self.coarse_threshold = coarse_threshold
        self.medium_duration = medium_duration
        self.medium_threshold = medium_threshold

        # Assume typical audio sampling rate for chromaprint
        # Chromaprint typically generates ~3 hashes per second
        self.hashes_per_second = 3

        self.stats = {
            'total_comparisons': 0,
            'rejected_coarse': 0,
            'rejected_medium': 0,
            'passed_all': 0
        }

        logger.info(f"Multi-resolution comparator initialized: "
                   f"coarse={coarse_duration}s@{coarse_threshold}%, "
                   f"medium={medium_duration}s@{medium_threshold}%")

    def _extract_sample(
        self,
        fingerprint: np.ndarray,
        duration_seconds: int
    ) -> np.ndarray:
        """
        Extract a time-limited sample from fingerprint.

        Args:
            fingerprint: Full audio fingerprint
            duration_seconds: Duration to extract in seconds

        Returns:
            Sample of fingerprint
        """
        max_hashes = duration_seconds * self.hashes_per_second
        return fingerprint[:max_hashes]

    def _compare_fingerprints(
        self,
        fp1: np.ndarray,
        fp2: np.ndarray
    ) -> float:
        """
        Compare two audio fingerprints and return similarity percentage.

        Uses Hamming distance for integer fingerprints.

        Args:
            fp1: First fingerprint
            fp2: Second fingerprint

        Returns:
            Similarity percentage (0-100)
        """
        if len(fp1) == 0 or len(fp2) == 0:
            return 0.0

        # Align fingerprints to same length
        min_len = min(len(fp1), len(fp2))
        fp1_aligned = fp1[:min_len]
        fp2_aligned = fp2[:min_len]

        # Calculate hamming distance (bit differences)
        # For int32 fingerprints, count matching values
        matches = np.sum(fp1_aligned == fp2_aligned)
        similarity = (matches / min_len) * 100.0

        return similarity

    def compare(
        self,
        fingerprint1: np.ndarray,
        fingerprint2: np.ndarray,
        full_threshold: float = 70.0
    ) -> Optional[float]:
        """
        Compare two fingerprints with progressive resolution.

        Args:
            fingerprint1: First audio fingerprint
            fingerprint2: Second audio fingerprint
            full_threshold: Final threshold for full comparison

        Returns:
            Final similarity if passed all phases, None if rejected
        """
        self.stats['total_comparisons'] += 1

        # Phase 1: Coarse comparison (fastest)
        coarse1 = self._extract_sample(fingerprint1, self.coarse_duration)
        coarse2 = self._extract_sample(fingerprint2, self.coarse_duration)
        coarse_sim = self._compare_fingerprints(coarse1, coarse2)

        if coarse_sim < self.coarse_threshold:
            self.stats['rejected_coarse'] += 1
            return None  # Rejected in coarse phase

        # Phase 2: Medium comparison (moderate)
        medium1 = self._extract_sample(fingerprint1, self.medium_duration)
        medium2 = self._extract_sample(fingerprint2, self.medium_duration)
        medium_sim = self._compare_fingerprints(medium1, medium2)

        if medium_sim < self.medium_threshold:
            self.stats['rejected_medium'] += 1
            return None  # Rejected in medium phase

        # Phase 3: Full comparison (most expensive)
        full_sim = self._compare_fingerprints(fingerprint1, fingerprint2)

        if full_sim < full_threshold:
            return None  # Rejected in final phase

        self.stats['passed_all'] += 1
        return full_sim

    def get_stats(self) -> dict:
        """
        Get comparison statistics.

        Returns:
            Dictionary with statistics
        """
        total = self.stats['total_comparisons']
        if total == 0:
            return self.stats

        return {
            'total_comparisons': total,
            'rejected_coarse': self.stats['rejected_coarse'],
            'rejected_coarse_pct': (self.stats['rejected_coarse'] / total) * 100,
            'rejected_medium': self.stats['rejected_medium'],
            'rejected_medium_pct': (self.stats['rejected_medium'] / total) * 100,
            'passed_all': self.stats['passed_all'],
            'passed_all_pct': (self.stats['passed_all'] / total) * 100
        }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self.stats = {
            'total_comparisons': 0,
            'rejected_coarse': 0,
            'rejected_medium': 0,
            'passed_all': 0
        }
        logger.info("Multi-resolution statistics reset")
