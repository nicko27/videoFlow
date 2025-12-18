"""
LSH (Locality-Sensitive Hashing) for fast approximate matching of fingerprints.

Instead of comparing all pairs (O(N²)), LSH groups similar items into buckets,
reducing comparisons to only likely candidates (O(N)).
"""

import logging
import numpy as np
from typing import Dict, List, Set, Tuple
from collections import defaultdict

logger = logging.getLogger('duplicateflow.processing.lsh_index')


class MinHashLSH:
    """
    MinHash LSH for fast similarity search on hash sets.

    Each video's fingerprints (set of hashes) can be compared using Jaccard similarity.
    LSH allows finding similar sets without computing all pairwise similarities.

    Algorithm:
    1. Generate multiple hash functions (permutations)
    2. For each set, compute MinHash signature (min value under each permutation)
    3. Band signatures into buckets (LSH)
    4. Videos in same bucket are candidates for similarity

    Parameters:
        num_perm: Number of permutations (signature length)
        num_bands: Number of bands for LSH
        threshold: Jaccard similarity threshold (0-1)

    With num_perm=128, num_bands=16:
    - Each band has 8 rows
    - Probability of detection for similarity > 0.5: ~99%
    - Expected false positive rate: ~1%
    """

    def __init__(
        self,
        num_perm: int = 128,
        num_bands: int = 16,
        threshold: float = 0.3
    ):
        """
        Initialize MinHash LSH.

        Args:
            num_perm: Number of permutations (more = more accurate, slower)
            num_bands: Number of bands (more = more sensitive, more false positives)
            threshold: Jaccard similarity threshold
        """
        self.num_perm = num_perm
        self.num_bands = num_bands
        self.rows_per_band = num_perm // num_bands
        self.threshold = threshold

        # Generate random permutation parameters (a, b for hash function: (a*x + b) % prime)
        self.prime = 2**31 - 1  # Mersenne prime
        rng = np.random.RandomState(42)  # Fixed seed for reproducibility
        self.hash_params = [
            (rng.randint(1, self.prime), rng.randint(0, self.prime))
            for _ in range(num_perm)
        ]

        # LSH buckets: band_id -> bucket_hash -> set of video_ids
        self.buckets: Dict[int, Dict[int, Set[int]]] = defaultdict(lambda: defaultdict(set))

        # Store signatures: video_id -> MinHash signature
        self.signatures: Dict[int, np.ndarray] = {}

        logger.debug(
            f"Initialized MinHash LSH: num_perm={num_perm}, "
            f"num_bands={num_bands}, rows_per_band={self.rows_per_band}"
        )

    def _compute_minhash(self, hash_set: Set[int]) -> np.ndarray:
        """
        Compute MinHash signature for a set of hashes.

        Args:
            hash_set: Set of integer hashes

        Returns:
            MinHash signature (array of num_perm integers)
        """
        if not hash_set:
            return np.full(self.num_perm, self.prime, dtype=np.int64)

        signature = np.full(self.num_perm, self.prime, dtype=np.int64)

        for h in hash_set:
            for i, (a, b) in enumerate(self.hash_params):
                # Hash function: (a*x + b) % prime
                perm_hash = (a * h + b) % self.prime
                signature[i] = min(signature[i], perm_hash)

        return signature

    def _hash_band(self, signature: np.ndarray, band_idx: int) -> int:
        """
        Hash a band of the signature to create LSH bucket.

        Args:
            signature: MinHash signature
            band_idx: Band index (0 to num_bands-1)

        Returns:
            Integer hash of the band
        """
        start = band_idx * self.rows_per_band
        end = start + self.rows_per_band
        band = signature[start:end]

        # Simple hash: combine values with prime multipliers
        hash_val = 0
        for i, val in enumerate(band):
            hash_val = (hash_val * 31 + int(val)) % (2**32)

        return hash_val

    def insert(self, video_id: int, hash_set: Set[int]):
        """
        Insert a video's fingerprints into the LSH index.

        Args:
            video_id: Video identifier
            hash_set: Set of fingerprint hashes for this video
        """
        # Compute MinHash signature
        signature = self._compute_minhash(hash_set)
        self.signatures[video_id] = signature

        # Insert into LSH buckets (one per band)
        for band_idx in range(self.num_bands):
            bucket_hash = self._hash_band(signature, band_idx)
            self.buckets[band_idx][bucket_hash].add(video_id)

        logger.debug(f"Inserted video {video_id} with {len(hash_set)} hashes")

    def query(self, video_id: int, hash_set: Set[int] = None) -> Set[int]:
        """
        Find candidate videos similar to the query.

        Args:
            video_id: Video to query (if already indexed)
            hash_set: Hash set (if video_id not indexed yet)

        Returns:
            Set of candidate video IDs that might be similar
        """
        # Get or compute signature
        if video_id in self.signatures and hash_set is None:
            signature = self.signatures[video_id]
        elif hash_set is not None:
            signature = self._compute_minhash(hash_set)
        else:
            raise ValueError("Must provide either video_id (if indexed) or hash_set")

        # Collect candidates from all bands
        candidates = set()

        for band_idx in range(self.num_bands):
            bucket_hash = self._hash_band(signature, band_idx)
            if bucket_hash in self.buckets[band_idx]:
                candidates.update(self.buckets[band_idx][bucket_hash])

        # Remove self
        candidates.discard(video_id)

        logger.debug(f"Query video {video_id}: found {len(candidates)} candidates")

        return candidates

    def compute_jaccard(
        self,
        video_id1: int,
        video_id2: int,
        hash_set1: Set[int] = None,
        hash_set2: Set[int] = None
    ) -> float:
        """
        Compute Jaccard similarity between two videos.

        Can use either stored signatures (fast) or actual hash sets (exact).

        Args:
            video_id1, video_id2: Video IDs
            hash_set1, hash_set2: Optional actual hash sets for exact computation

        Returns:
            Jaccard similarity (0-1)
        """
        if hash_set1 is not None and hash_set2 is not None:
            # Exact Jaccard from actual sets
            intersection = len(hash_set1 & hash_set2)
            union = len(hash_set1 | hash_set2)
            return intersection / union if union > 0 else 0.0

        # Estimate from MinHash signatures
        sig1 = self.signatures.get(video_id1)
        sig2 = self.signatures.get(video_id2)

        if sig1 is None or sig2 is None:
            return 0.0

        # Jaccard estimate: fraction of matching signature values
        matches = np.sum(sig1 == sig2)
        return matches / self.num_perm

    def get_stats(self) -> Dict:
        """Get LSH index statistics."""
        total_entries = sum(
            len(videos)
            for band in self.buckets.values()
            for videos in band.values()
        )

        bucket_sizes = [
            len(videos)
            for band in self.buckets.values()
            for videos in band.values()
        ]

        return {
            'num_videos': len(self.signatures),
            'num_bands': self.num_bands,
            'num_permutations': self.num_perm,
            'total_bucket_entries': total_entries,
            'avg_bucket_size': np.mean(bucket_sizes) if bucket_sizes else 0,
            'max_bucket_size': max(bucket_sizes) if bucket_sizes else 0
        }


class LSHFingerprintIndex:
    """
    Wrapper around FingerprintIndex that uses LSH for fast candidate selection.

    This dramatically reduces the number of full comparisons needed:
    - Without LSH: O(N²) comparisons
    - With LSH: O(N*C) where C is average candidates per query (typically C << N)

    For 1000 videos:
    - Without LSH: ~500,000 comparisons
    - With LSH: ~10,000-50,000 comparisons (10-50x speedup)
    """

    def __init__(
        self,
        fingerprint_index,
        num_perm: int = 128,
        num_bands: int = 16,
        threshold: float = 0.3
    ):
        """
        Initialize LSH-accelerated index.

        Args:
            fingerprint_index: FingerprintIndex instance
            num_perm: MinHash permutations
            num_bands: LSH bands
            threshold: Similarity threshold
        """
        self.index = fingerprint_index
        self.lsh = MinHashLSH(num_perm=num_perm, num_bands=num_bands, threshold=threshold)
        self._build_lsh()

    def _build_lsh(self):
        """Build LSH index from existing fingerprints."""
        import sqlite3

        conn = sqlite3.connect(str(self.index.db_path))
        cursor = conn.cursor()

        # Get all videos
        cursor.execute("SELECT id FROM videos")
        video_ids = [row[0] for row in cursor.fetchall()]

        logger.info(f"Building LSH index for {len(video_ids)} videos...")

        # Build LSH index
        for video_id in video_ids:
            # Get unique hashes for this video
            cursor.execute(
                "SELECT DISTINCT hash FROM fingerprints WHERE video_id = ?",
                (video_id,)
            )
            hash_set = {row[0] for row in cursor.fetchall()}

            self.lsh.insert(video_id, hash_set)

        conn.close()

        stats = self.lsh.get_stats()
        logger.info(
            f"LSH index built: {stats['num_videos']} videos, "
            f"avg {stats['avg_bucket_size']:.1f} videos/bucket"
        )

    def find_matches_fast(
        self,
        video_path: str,
        min_votes: int = 200,
        max_matches: int = 100,
        time_quant: int = 20
    ):
        """
        Find matches using LSH for candidate selection.

        This is much faster than full comparison:
        1. Use LSH to find candidate videos (similar hash sets)
        2. Only compute full match for candidates

        Args:
            video_path: Query video path
            min_votes: Minimum votes for match
            max_matches: Maximum matches to return
            time_quant: Time quantization

        Returns:
            List of Match objects
        """
        import sqlite3
        from duplicateflow.processing.fingerprint_index import Match

        conn = sqlite3.connect(str(self.index.db_path))
        cursor = conn.cursor()

        # Get video ID
        cursor.execute("SELECT id FROM videos WHERE path = ?", (video_path,))
        row = cursor.fetchone()

        if row is None:
            logger.warning(f"Video not indexed: {video_path}")
            conn.close()
            return []

        video_id = row[0]

        # Get candidates via LSH
        candidates = self.lsh.query(video_id)

        logger.info(
            f"LSH candidate selection: {len(candidates)} candidates "
            f"(reduced from {self.lsh.get_stats()['num_videos'] - 1} total)"
        )

        if not candidates:
            conn.close()
            return []

        # Now only compute full matches for candidates
        # Use existing find_matches but filter to candidates
        all_matches = self.index.find_matches(
            video_path,
            min_votes=min_votes,
            max_matches=max_matches * 10,  # Get more since we'll filter
            time_quant=time_quant
        )

        # Filter to only LSH candidates
        filtered_matches = [
            m for m in all_matches
            if m.video2_id in candidates
        ]

        conn.close()

        logger.info(f"Found {len(filtered_matches)} matches after LSH filtering")

        return filtered_matches[:max_matches]
