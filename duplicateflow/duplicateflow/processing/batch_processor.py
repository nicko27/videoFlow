"""
Batch processing for comparing multiple videos efficiently.

Handles large-scale video comparison with parallel processing,
error recovery, and progress tracking.
"""

import logging
import json
import csv
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
import pickle

from tqdm import tqdm

logger = logging.getLogger('duplicateflow.processing.batch_processor')


@dataclass
class BatchResult:
    """Result of a single video comparison in batch."""
    short_video: str
    long_video: str
    offset: float
    score: float
    accepted: bool
    algorithm: str
    duration: float
    error: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class BatchProcessor:
    """
    Process multiple video comparisons in parallel with error handling.

    Features:
    - Parallel processing with configurable workers
    - Automatic error recovery and retry
    - Progress tracking and estimation
    - Resume from checkpoint
    - Export results to CSV/JSON

    Example:
        >>> processor = BatchProcessor(num_workers=8)
        >>> results = processor.process_batch(
        ...     short_videos=short_list,
        ...     long_video='reference.mp4',
        ...     algorithm='frame_hash',
        ...     output_file='results.csv'
        ... )
    """

    def __init__(
        self,
        num_workers: int = 4,
        checkpoint_interval: int = 10,
        max_retries: int = 2
    ):
        """
        Initialize batch processor.

        Args:
            num_workers: Number of parallel workers
            checkpoint_interval: Save checkpoint every N videos
            max_retries: Maximum retry attempts per video
        """
        self.num_workers = num_workers
        self.checkpoint_interval = checkpoint_interval
        self.max_retries = max_retries

        self.results: List[BatchResult] = []
        self.failed_videos: List[Dict[str, Any]] = []

    def process_batch(
        self,
        short_videos: List[str],
        long_video: str,
        algorithm: str,
        algorithm_params: Dict[str, Any] = None,
        strategy: str = 'parallel',
        step_size: float = 5.0,
        output_file: Optional[str] = None,
        checkpoint_file: Optional[str] = None,
        show_progress: bool = True
    ) -> List[BatchResult]:
        """
        Process batch of short videos against one long video.

        Args:
            short_videos: List of short video paths
            long_video: Long video path
            algorithm: Algorithm to use
            algorithm_params: Algorithm configuration
            strategy: Search strategy ('parallel', 'cascade', 'adaptive')
            step_size: Step size for window search
            output_file: Output file path (.csv or .json)
            checkpoint_file: Checkpoint file for resume
            show_progress: Show progress bar

        Returns:
            List of BatchResult objects
        """
        algorithm_params = algorithm_params or {}

        # Load checkpoint if exists
        processed_videos, start_index = self._load_checkpoint(checkpoint_file)

        logger.info(
            f"Processing {len(short_videos)} videos with {self.num_workers} workers"
        )

        if start_index > 0:
            logger.info(f"Resuming from video {start_index}")
            short_videos = short_videos[start_index:]

        # Process videos in parallel
        results = self._process_parallel(
            short_videos,
            long_video,
            algorithm,
            algorithm_params,
            strategy,
            step_size,
            show_progress,
            checkpoint_file,
            start_index
        )

        # Export results if output file specified
        if output_file:
            self._export_results(results, output_file)

        return results

    def process_matrix(
        self,
        video_list: List[str],
        algorithm: str,
        algorithm_params: Dict[str, Any] = None,
        output_file: Optional[str] = None,
        show_progress: bool = True
    ) -> List[List[float]]:
        """
        Process N-to-N comparison matrix.

        Compares each video against all others.

        Args:
            video_list: List of video paths
            algorithm: Algorithm to use
            algorithm_params: Algorithm configuration
            output_file: Output CSV file path
            show_progress: Show progress bar

        Returns:
            2D list of similarity scores
        """
        algorithm_params = algorithm_params or {}
        n = len(video_list)

        logger.info(f"Computing {n}x{n} comparison matrix")

        # Initialize matrix
        matrix = [[0.0 for _ in range(n)] for _ in range(n)]

        # Prepare pairs (only upper triangle, matrix is symmetric)
        pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                pairs.append((i, j, video_list[i], video_list[j]))

        logger.info(f"Total comparisons: {len(pairs)}")

        # Process pairs in parallel
        results = []

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = {}

            for i, j, video1, video2 in pairs:
                future = executor.submit(
                    self._compare_videos,
                    video1, video2, algorithm, algorithm_params
                )
                futures[future] = (i, j)

            # Collect results
            iterator = as_completed(futures)
            if show_progress:
                iterator = tqdm(
                    iterator,
                    total=len(pairs),
                    desc="Computing matrix"
                )

            for future in iterator:
                i, j = futures[future]

                try:
                    result = future.result()
                    score = result['score']

                    # Fill symmetric matrix
                    matrix[i][j] = score
                    matrix[j][i] = score

                except Exception as e:
                    logger.error(f"Error comparing {i},{j}: {e}")
                    matrix[i][j] = 0.0
                    matrix[j][i] = 0.0

        # Diagonal is 100% (video compared to itself)
        for i in range(n):
            matrix[i][i] = 100.0

        # Export matrix if output file specified
        if output_file:
            self._export_matrix(matrix, video_list, output_file)

        return matrix

    def _process_parallel(
        self,
        short_videos: List[str],
        long_video: str,
        algorithm: str,
        algorithm_params: Dict[str, Any],
        strategy: str,
        step_size: float,
        show_progress: bool,
        checkpoint_file: Optional[str],
        start_index: int
    ) -> List[BatchResult]:
        """Process videos in parallel with error handling."""
        results = []

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit all tasks
            futures = {}
            for idx, short_video in enumerate(short_videos, start=start_index):
                future = executor.submit(
                    self._process_single_video,
                    short_video,
                    long_video,
                    algorithm,
                    algorithm_params,
                    strategy,
                    step_size
                )
                futures[future] = (idx, short_video)

            # Collect results
            iterator = as_completed(futures)
            if show_progress:
                iterator = tqdm(
                    iterator,
                    total=len(short_videos),
                    desc="Processing videos"
                )

            for future in iterator:
                idx, short_video = futures[future]

                try:
                    result = future.result()
                    results.append(result)

                    # Save checkpoint periodically
                    if checkpoint_file and len(results) % self.checkpoint_interval == 0:
                        self._save_checkpoint(checkpoint_file, results, idx + 1)

                except Exception as e:
                    logger.error(f"Error processing {short_video}: {e}")
                    error_result = BatchResult(
                        short_video=short_video,
                        long_video=long_video,
                        offset=0.0,
                        score=0.0,
                        accepted=False,
                        algorithm=algorithm,
                        duration=0.0,
                        error=str(e)
                    )
                    results.append(error_result)

        # Final checkpoint
        if checkpoint_file:
            self._save_checkpoint(checkpoint_file, results, start_index + len(short_videos))

        return results

    def _process_single_video(
        self,
        short_video: str,
        long_video: str,
        algorithm: str,
        algorithm_params: Dict[str, Any],
        strategy: str,
        step_size: float
    ) -> BatchResult:
        """Process a single video comparison."""
        from duplicateflow.core import get_algorithm
        from duplicateflow.processing import ParallelWindowSearch

        start_time = time.time()

        try:
            # Get algorithm
            AlgoClass = get_algorithm(algorithm)
            algo = AlgoClass()
            algo.configure(**algorithm_params)

            # Run search
            if strategy == 'parallel':
                searcher = ParallelWindowSearch(num_workers=1)  # Single worker per video
                result = searcher.search(
                    short_video, long_video, algorithm, algo,
                    step_size=step_size, show_progress=False
                )
            else:
                # Use standard compare
                result = algo.compare(
                    short_video=short_video,
                    long_video=long_video
                )

                # Extract relevant fields
                similarity = result.get('similarity', 0.0)
                if similarity <= 1.0:
                    similarity *= 100.0

                result = {
                    'offset': result.get('metadata', {}).get('best_offset_seconds', 0.0),
                    'score': similarity,
                    'accepted': result.get('accepted', False)
                }

            duration = time.time() - start_time

            return BatchResult(
                short_video=short_video,
                long_video=long_video,
                offset=result['offset'],
                score=result['score'],
                accepted=result['accepted'],
                algorithm=algorithm,
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            raise Exception(f"Failed to process {short_video}: {e}")

    def _compare_videos(
        self,
        video1: str,
        video2: str,
        algorithm: str,
        algorithm_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare two videos for matrix computation."""
        from duplicateflow.core import get_algorithm

        AlgoClass = get_algorithm(algorithm)
        algo = AlgoClass()
        algo.configure(**algorithm_params)

        result = algo.compare(short_video=video1, long_video=video2)

        similarity = result.get('similarity', 0.0)
        if similarity <= 1.0:
            similarity *= 100.0

        return {
            'score': similarity,
            'accepted': result.get('accepted', False)
        }

    def _load_checkpoint(
        self,
        checkpoint_file: Optional[str]
    ) -> tuple[List[BatchResult], int]:
        """Load checkpoint if exists."""
        if not checkpoint_file:
            return [], 0

        checkpoint_path = Path(checkpoint_file)
        if not checkpoint_path.exists():
            return [], 0

        try:
            with open(checkpoint_path, 'rb') as f:
                data = pickle.load(f)

            results = data['results']
            next_index = data['next_index']

            logger.info(f"Loaded checkpoint: {len(results)} results, next index {next_index}")
            return results, next_index

        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return [], 0

    def _save_checkpoint(
        self,
        checkpoint_file: str,
        results: List[BatchResult],
        next_index: int
    ):
        """Save checkpoint."""
        checkpoint_path = Path(checkpoint_file)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(checkpoint_path, 'wb') as f:
                pickle.dump({
                    'results': results,
                    'next_index': next_index,
                    'timestamp': datetime.now().isoformat()
                }, f)

            logger.debug(f"Checkpoint saved: {len(results)} results")

        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")

    def _export_results(self, results: List[BatchResult], output_file: str):
        """Export results to CSV or JSON."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix == '.csv':
            self._export_csv(results, output_path)
        elif output_path.suffix == '.json':
            self._export_json(results, output_path)
        else:
            logger.warning(f"Unknown output format: {output_path.suffix}")

    def _export_csv(self, results: List[BatchResult], output_path: Path):
        """Export results to CSV."""
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    'short_video', 'long_video', 'offset', 'score',
                    'accepted', 'algorithm', 'duration', 'error', 'timestamp'
                ]
            )

            writer.writeheader()
            for result in results:
                writer.writerow(asdict(result))

        logger.info(f"Results exported to CSV: {output_path}")

    def _export_json(self, results: List[BatchResult], output_path: Path):
        """Export results to JSON."""
        data = [asdict(result) for result in results]

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Results exported to JSON: {output_path}")

    def _export_matrix(
        self,
        matrix: List[List[float]],
        video_list: List[str],
        output_file: str
    ):
        """Export similarity matrix to CSV."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header row
            writer.writerow([''] + [Path(v).name for v in video_list])

            # Data rows
            for i, video in enumerate(video_list):
                row = [Path(video).name] + [f"{score:.2f}" for score in matrix[i]]
                writer.writerow(row)

        logger.info(f"Matrix exported to CSV: {output_path}")

    def get_stats(self, results: List[BatchResult]) -> Dict[str, Any]:
        """Get statistics from batch results."""
        if not results:
            return {}

        successful = [r for r in results if r.error is None]
        failed = [r for r in results if r.error is not None]
        accepted = [r for r in successful if r.accepted]

        total_duration = sum(r.duration for r in successful)
        avg_duration = total_duration / len(successful) if successful else 0

        scores = [r.score for r in successful]
        avg_score = sum(scores) / len(scores) if scores else 0

        return {
            'total_videos': len(results),
            'successful': len(successful),
            'failed': len(failed),
            'accepted': len(accepted),
            'acceptance_rate': len(accepted) / len(successful) * 100 if successful else 0,
            'total_duration': total_duration,
            'avg_duration': avg_duration,
            'avg_score': avg_score,
            'min_score': min(scores) if scores else 0,
            'max_score': max(scores) if scores else 0
        }
