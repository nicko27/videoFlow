"""
Core detection engine providing unified interface for all detection modes.

This module replaces the need for GUI to implement its own detection logic.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class DetectionMode(Enum):
    """Detection mode selection."""
    FINGERPRINT = "fingerprint"      # Audio fingerprinting (N-to-N, scalable millions)
    ALGORITHM = "algorithm"          # Single algorithm (N-to-N pairwise)
    PIPELINE = "pipeline"            # Multi-algorithm weighted (N-to-N pairwise)
    ONE_TO_ONE = "one_to_one"       # 1-to-1 comparison (for GUI preview)


@dataclass
class MatchResult:
    """Represents a match between two videos."""
    video1_path: str
    video2_path: str
    similarity: float          # 0-100 scale
    confidence: float          # 0-100 scale
    match_type: str           # DUPLICATE, SCENE, EXTRACT, UNCERTAIN
    offset_seconds: float     # Time offset (0 if not applicable)
    votes: int                # Vote count (0 if not applicable)
    metadata: Dict[str, Any]  # Algorithm-specific metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        return {
            'video1': self.video1_path,
            'video2': self.video2_path,
            'similarity': round(self.similarity, 2),
            'confidence': round(self.confidence, 2),
            'match_type': self.match_type,
            'offset_seconds': round(self.offset_seconds, 2),
            'votes': self.votes,
            'metadata': self.metadata
        }


@dataclass
class DetectionResult:
    """Complete detection result with statistics."""
    matches: List[MatchResult]
    total_videos: int
    total_comparisons: int
    processing_time: float
    mode: DetectionMode
    config: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        return {
            'matches': [m.to_dict() for m in self.matches],
            'total_videos': self.total_videos,
            'total_comparisons': self.total_comparisons,
            'processing_time': round(self.processing_time, 2),
            'mode': self.mode.value,
            'config': self.config,
            'statistics': self.get_statistics()
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get match statistics."""
        return {
            'total_matches': len(self.matches),
            'by_type': {
                'DUPLICATE': sum(1 for m in self.matches if m.match_type == 'DUPLICATE'),
                'SCENE': sum(1 for m in self.matches if m.match_type == 'SCENE'),
                'EXTRACT': sum(1 for m in self.matches if m.match_type == 'EXTRACT'),
                'UNCERTAIN': sum(1 for m in self.matches if m.match_type == 'UNCERTAIN')
            },
            'by_confidence': {
                'high': sum(1 for m in self.matches if m.confidence >= 80),
                'medium': sum(1 for m in self.matches if 60 <= m.confidence < 80),
                'low': sum(1 for m in self.matches if m.confidence < 60)
            }
        }


class DetectionEngine:
    """
    Unified detection engine supporting all modes.

    This class provides a clean API for both CLI and GUI applications.

    Example usage:
        # N-to-N fingerprint detection
        engine = DetectionEngine(mode=DetectionMode.FINGERPRINT)
        result = engine.find_duplicates(
            directory="/path/to/videos",
            recursive=True,
            workers=8,
            min_confidence=15.0
        )

        # N-to-N pipeline detection
        engine = DetectionEngine(mode=DetectionMode.PIPELINE, pipeline='balanced')
        result = engine.find_duplicates(
            directory="/path/to/videos",
            workers=4,
            min_confidence=60.0
        )

        # 1-to-1 comparison for GUI
        engine = DetectionEngine(mode=DetectionMode.ONE_TO_ONE, pipeline='thorough')
        result = engine.compare_videos(
            video1="/path/to/short.mp4",
            video2="/path/to/long.mp4"
        )
    """

    def __init__(
        self,
        mode: DetectionMode = DetectionMode.FINGERPRINT,
        algorithm: Optional[str] = None,
        pipeline: Optional[str] = None,
        db_path: Optional[str] = None,
        use_cache: bool = True,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        """
        Initialize detection engine.

        Args:
            mode: Detection mode (FINGERPRINT, ALGORITHM, PIPELINE, ONE_TO_ONE)
            algorithm: Algorithm name (required if mode=ALGORITHM)
            pipeline: Pipeline preset (required if mode=PIPELINE or ONE_TO_ONE)
            db_path: Database path for fingerprint mode
            use_cache: Enable result caching
            progress_callback: Optional callback for progress updates (message, progress 0-100)
        """
        self.mode = mode
        self.algorithm = algorithm
        self.pipeline = pipeline
        self.db_path = db_path or str(Path.home() / '.duplicateflow' / 'fingerprints.db')
        self.use_cache = use_cache
        self.progress_callback = progress_callback

        # Validate configuration
        if mode == DetectionMode.ALGORITHM and not algorithm:
            raise ValueError("Algorithm name required for ALGORITHM mode")
        if mode in (DetectionMode.PIPELINE, DetectionMode.ONE_TO_ONE) and not pipeline:
            raise ValueError("Pipeline preset required for PIPELINE/ONE_TO_ONE mode")

        logger.info(f"DetectionEngine initialized: mode={mode.value}, algorithm={algorithm}, pipeline={pipeline}")

    def _report_progress(self, message: str, progress: float):
        """Report progress to callback if provided."""
        if self.progress_callback:
            self.progress_callback(message, progress)

    def find_duplicates(
        self,
        directory: str,
        recursive: bool = True,
        workers: int = 4,
        min_confidence: float = 15.0,
        min_votes: int = 200,
        max_pairs: int = 10000,
        threshold: Optional[float] = None,
        use_lsh: bool = True,
        lsh_threshold: int = 100
    ) -> DetectionResult:
        """
        Find all duplicates in a directory (N-to-N detection).

        Args:
            directory: Directory to scan
            recursive: Scan subdirectories
            workers: Number of parallel workers
            min_confidence: Minimum confidence percentage
            min_votes: Minimum votes (fingerprint mode only)
            max_pairs: Maximum pairs to return
            threshold: Detection threshold (algorithm-specific)
            use_lsh: Use LSH acceleration (fingerprint mode only)
            lsh_threshold: LSH activation threshold (fingerprint mode only)

        Returns:
            DetectionResult with all matches and statistics
        """
        import time
        start_time = time.time()

        self._report_progress("Starting detection", 0)

        # Dispatch to appropriate implementation
        if self.mode == DetectionMode.FINGERPRINT:
            matches = self._find_duplicates_fingerprint(
                directory, recursive, workers, min_votes, min_confidence,
                max_pairs, use_lsh, lsh_threshold
            )
        elif self.mode == DetectionMode.ALGORITHM:
            matches = self._find_duplicates_algorithm(
                directory, recursive, workers, min_confidence, max_pairs, threshold
            )
        elif self.mode == DetectionMode.PIPELINE:
            matches = self._find_duplicates_pipeline(
                directory, recursive, workers, min_confidence, max_pairs, threshold
            )
        else:
            raise ValueError(f"find_duplicates not supported for mode={self.mode}")

        processing_time = time.time() - start_time
        self._report_progress("Detection complete", 100)

        # Count unique videos
        video_paths = set()
        for m in matches:
            video_paths.add(m.video1_path)
            video_paths.add(m.video2_path)

        return DetectionResult(
            matches=matches,
            total_videos=len(video_paths),
            total_comparisons=self._count_comparisons(len(video_paths)),
            processing_time=processing_time,
            mode=self.mode,
            config={
                'directory': directory,
                'recursive': recursive,
                'workers': workers,
                'min_confidence': min_confidence,
                'algorithm': self.algorithm,
                'pipeline': self.pipeline
            }
        )

    def compare_videos(
        self,
        video1: str,
        video2: str,
        strategy: str = "adaptive",
        workers: int = 4
    ) -> MatchResult:
        """
        Compare two videos (1-to-1 comparison for GUI).

        Args:
            video1: Path to first video (usually shorter)
            video2: Path to second video (usually longer)
            strategy: Search strategy (linear, parallel, cascade, adaptive)
            workers: Number of parallel workers

        Returns:
            Single MatchResult
        """
        if self.mode != DetectionMode.ONE_TO_ONE:
            raise ValueError("compare_videos requires ONE_TO_ONE mode")

        from duplicateflow.core.pipeline import Pipeline
        from duplicateflow.core.storage import StorageManager

        self._report_progress(f"Comparing {Path(video1).name} vs {Path(video2).name}", 0)

        # Create pipeline
        storage = StorageManager() if self.use_cache else None
        pipeline = Pipeline.from_preset(self.pipeline, storage=storage)

        # Run comparison
        result = pipeline.compare(video1, video2, use_cache=self.use_cache)

        similarity = result['global_score']

        # Classify match type
        if similarity >= 80.0:
            match_type = "DUPLICATE"
        elif similarity >= 60.0:
            match_type = "SCENE"
        elif similarity >= 15.0:
            match_type = "EXTRACT"
        else:
            match_type = "UNCERTAIN"

        self._report_progress("Comparison complete", 100)

        return MatchResult(
            video1_path=video1,
            video2_path=video2,
            similarity=similarity,
            confidence=similarity,
            match_type=match_type,
            offset_seconds=result.get('offset', 0),
            votes=0,
            metadata=result.get('metadata', {})
        )

    def _find_duplicates_fingerprint(self, directory, recursive, workers,
                                     min_votes, min_confidence, max_pairs,
                                     use_lsh, lsh_threshold) -> List[MatchResult]:
        """Fingerprint mode implementation."""
        from duplicateflow.processing.fingerprint_index import FingerprintIndex
        from duplicateflow.algorithms import get_algorithm

        self._report_progress("Initializing fingerprint index", 10)

        # Initialize index
        index = FingerprintIndex(db_path=self.db_path)

        # Get algorithm
        AlgoClass = get_algorithm('audio_fingerprint')
        algo = AlgoClass()
        algo.configure()

        # Index directory
        self._report_progress("Indexing videos", 30)
        index.index_directory(
            directory=directory,
            algorithm=algo,
            recursive=recursive,
            workers=workers,
            force=False
        )

        # Find matches
        self._report_progress("Finding matches", 60)

        stats = index.get_stats()
        enable_lsh = use_lsh and stats['video_count'] >= lsh_threshold

        if enable_lsh:
            from duplicateflow.processing.lsh_index import LSHFingerprintIndex
            import sqlite3

            lsh_index = LSHFingerprintIndex(index, num_perm=128, num_bands=16)

            all_matches = []
            conn = sqlite3.connect(str(index.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT id, path FROM videos")
            videos = cursor.fetchall()
            conn.close()

            for i, (video_id, video_path) in enumerate(videos):
                self._report_progress(
                    f"Processing video {i+1}/{len(videos)}",
                    60 + (i / len(videos)) * 30
                )
                matches = lsh_index.find_matches_fast(
                    video_path,
                    min_votes=min_votes,
                    max_matches=max_pairs
                )
                all_matches.extend(matches)

            # Deduplicate
            seen = set()
            matches = []
            for m in all_matches:
                key = tuple(sorted([m.video1_path, m.video2_path]))
                if key not in seen:
                    seen.add(key)
                    matches.append(m)
        else:
            matches = index.find_all_matches(min_votes=min_votes, max_pairs=max_pairs)

        # Filter by confidence
        matches = [m for m in matches if m.confidence >= min_confidence]

        # Convert to MatchResult
        return [
            MatchResult(
                video1_path=m.video1_path,
                video2_path=m.video2_path,
                similarity=m.confidence,
                confidence=m.confidence,
                match_type=m.match_type,
                offset_seconds=m.offset_seconds,
                votes=m.votes,
                metadata={}
            )
            for m in matches
        ]

    def _find_duplicates_algorithm(self, directory, recursive, workers,
                                   min_confidence, max_pairs, threshold) -> List[MatchResult]:
        """Algorithm mode implementation."""
        from glob import glob
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from duplicateflow.algorithms import get_algorithm
        from duplicateflow.core.storage import StorageManager

        self._report_progress("Collecting videos", 10)

        # Collect videos
        if recursive:
            pattern = str(Path(directory) / "**" / "*")
        else:
            pattern = str(Path(directory) / "*")

        extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.m4v')
        all_files = glob(pattern, recursive=recursive)
        videos = [f for f in all_files if f.lower().endswith(extensions)]

        if len(videos) < 2:
            return []

        # Get algorithm
        AlgoClass = get_algorithm(self.algorithm)
        algo = AlgoClass()

        if threshold is not None:
            algo.configure(threshold=threshold)
        else:
            algo.configure()

        storage = StorageManager() if self.use_cache else None

        # Compare all pairs
        self._report_progress("Comparing pairs", 30)

        total_pairs = len(videos) * (len(videos) - 1) // 2
        matches = []
        completed = 0

        def compare_pair(i, j):
            """Compare a single pair."""
            video1 = videos[i]
            video2 = videos[j]

            try:
                result = None
                if storage and self.use_cache:
                    config = algo.get_config()
                    result = storage.get_cached_result(video1, video2, self.algorithm, config)

                if result is None:
                    result = algo.compare(video1, video2)

                    if storage and self.use_cache:
                        config = algo.get_config()
                        storage.store_result(video1, video2, self.algorithm, config, result)

                similarity = result['similarity']
                if similarity <= 1.0:
                    similarity = similarity * 100.0

                if similarity >= 80.0:
                    match_type = "DUPLICATE"
                elif similarity >= 60.0:
                    match_type = "SCENE"
                elif similarity >= 15.0:
                    match_type = "EXTRACT"
                else:
                    match_type = "UNCERTAIN"

                return MatchResult(
                    video1_path=video1,
                    video2_path=video2,
                    similarity=similarity,
                    confidence=similarity,
                    match_type=match_type,
                    offset_seconds=0,
                    votes=0,
                    metadata=result.get('metadata', {})
                )
            except Exception as e:
                logger.error(f"Error comparing {Path(video1).name} vs {Path(video2).name}: {e}")
                return None

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for i in range(len(videos)):
                for j in range(i + 1, len(videos)):
                    futures.append(executor.submit(compare_pair, i, j))

            for future in as_completed(futures):
                match = future.result()
                if match and match.confidence >= min_confidence:
                    matches.append(match)

                completed += 1
                self._report_progress(
                    f"Comparing pairs ({completed}/{total_pairs})",
                    30 + (completed / total_pairs) * 60
                )

        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)

        return matches[:max_pairs]

    def _find_duplicates_pipeline(self, directory, recursive, workers,
                                  min_confidence, max_pairs, threshold) -> List[MatchResult]:
        """Pipeline mode implementation."""
        from glob import glob
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from duplicateflow.core.pipeline import Pipeline
        from duplicateflow.core.storage import StorageManager

        self._report_progress("Collecting videos", 10)

        # Collect videos
        if recursive:
            pattern = str(Path(directory) / "**" / "*")
        else:
            pattern = str(Path(directory) / "*")

        extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.m4v')
        all_files = glob(pattern, recursive=recursive)
        videos = [f for f in all_files if f.lower().endswith(extensions)]

        if len(videos) < 2:
            return []

        # Create pipeline
        storage = StorageManager() if self.use_cache else None
        pipeline = Pipeline.from_preset(self.pipeline, storage=storage)

        if threshold is not None:
            pipeline.global_threshold = threshold

        # Compare all pairs
        self._report_progress("Comparing pairs", 30)

        total_pairs = len(videos) * (len(videos) - 1) // 2
        matches = []
        completed = 0

        def compare_pair(i, j):
            """Compare a single pair."""
            video1 = videos[i]
            video2 = videos[j]

            try:
                result = pipeline.compare(video1, video2, use_cache=self.use_cache)

                similarity = result['global_score']

                if similarity >= 80.0:
                    match_type = "DUPLICATE"
                elif similarity >= 60.0:
                    match_type = "SCENE"
                elif similarity >= 15.0:
                    match_type = "EXTRACT"
                else:
                    match_type = "UNCERTAIN"

                return MatchResult(
                    video1_path=video1,
                    video2_path=video2,
                    similarity=similarity,
                    confidence=similarity,
                    match_type=match_type,
                    offset_seconds=result.get('offset', 0),
                    votes=0,
                    metadata=result.get('metadata', {})
                )
            except Exception as e:
                logger.error(f"Error comparing {Path(video1).name} vs {Path(video2).name}: {e}")
                return None

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for i in range(len(videos)):
                for j in range(i + 1, len(videos)):
                    futures.append(executor.submit(compare_pair, i, j))

            for future in as_completed(futures):
                match = future.result()
                if match and match.confidence >= min_confidence:
                    matches.append(match)

                completed += 1
                self._report_progress(
                    f"Comparing pairs ({completed}/{total_pairs})",
                    30 + (completed / total_pairs) * 60
                )

        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)

        return matches[:max_pairs]

    def _count_comparisons(self, n: int) -> int:
        """Count total comparisons for N videos."""
        if self.mode == DetectionMode.FINGERPRINT:
            # Approximate: N × avg_hashes
            return n * 500  # Rough estimate
        else:
            # Pairwise: N × (N-1) / 2
            return n * (n - 1) // 2
