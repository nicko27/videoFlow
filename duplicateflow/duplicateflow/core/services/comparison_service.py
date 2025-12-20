"""
Comparison service for comparing two videos using detection algorithms.
"""
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from duplicateflow.core.interfaces.i_progress_reporter import IProgressReporter
from duplicateflow.core.interfaces.i_ui_adapter import IUIAdapter, MessageType
from duplicateflow.core.models.comparison import ComparisonResult
from duplicateflow.core.models.algorithm_result import AlgorithmResult
from duplicateflow.pipeline.pipeline import Pipeline


class ComparisonService:
    """
    Service for comparing two videos for similarity.

    Uses the Pipeline system to orchestrate multiple algorithms and
    produces a ComparisonResult with detailed information.

    Example:
        >>> from duplicateflow.core.interfaces.i_progress_reporter import NullProgressReporter
        >>> from duplicateflow.core.interfaces.i_ui_adapter import NullUIAdapter
        >>> from pathlib import Path
        >>>
        >>> service = ComparisonService(
        ...     progress=NullProgressReporter(),
        ...     ui=NullUIAdapter()
        ... )
        >>>
        >>> result = service.compare_videos(
        ...     Path("/videos/movie1.mp4"),
        ...     Path("/videos/movie2.mp4"),
        ...     threshold=70.0
        ... )
        >>> print(f"Similarity: {result.similarity_score:.2f}%")
        >>> print(f"Is duplicate: {result.is_duplicate}")
    """

    def __init__(
        self,
        progress: IProgressReporter,
        ui: IUIAdapter,
        pipeline: Optional[Pipeline] = None
    ):
        """
        Initialize comparison service.

        Args:
            progress: Progress reporter for tracking execution
            ui: UI adapter for displaying messages
            pipeline: Optional Pipeline instance (defaults to 'balanced' preset)

        Example:
            >>> from duplicateflow.pipeline.pipeline import Pipeline
            >>> custom_pipeline = Pipeline.from_preset('thorough')
            >>> service = ComparisonService(progress, ui, pipeline=custom_pipeline)
        """
        self.progress = progress
        self.ui = ui
        self.pipeline = pipeline or Pipeline.from_preset('balanced')

    def compare_videos(
        self,
        video1: Path,
        video2: Path,
        threshold: float = 70.0
    ) -> ComparisonResult:
        """
        Compare two videos for similarity.

        Args:
            video1: Path to first video
            video2: Path to second video
            threshold: Similarity threshold for duplicate detection (0-100)

        Returns:
            ComparisonResult with detailed comparison information

        Raises:
            FileNotFoundError: If either video file doesn't exist
            ValueError: If threshold is not in valid range

        Example:
            >>> result = service.compare_videos(
            ...     Path("/videos/movie1.mp4"),
            ...     Path("/videos/movie2.mp4"),
            ...     threshold=75.0
            ... )
            >>> if result.is_duplicate:
            ...     print(f"Duplicate found with {result.similarity_score:.1f}% similarity")
        """
        # Validation
        if not video1.exists():
            raise FileNotFoundError(f"Video 1 not found: {video1}")
        if not video2.exists():
            raise FileNotFoundError(f"Video 2 not found: {video2}")
        if not (0 <= threshold <= 100):
            raise ValueError(f"Threshold must be between 0 and 100, got {threshold}")

        # Start progress tracking
        self.progress.start_phase(
            "comparison",
            total=1,
            message=f"Comparing {video1.name} vs {video2.name}"
        )

        # Display info message
        self.ui.display_message(
            f"Comparing videos: {video1.name} vs {video2.name}",
            MessageType.INFO
        )

        # Record start time
        start_time = time.time()

        # Execute pipeline comparison
        try:
            pipeline_result = self.pipeline.compare(
                str(video1),
                str(video2),
                use_cache=True
            )
        except Exception as e:
            self.ui.display_message(
                f"Error during comparison: {str(e)}",
                MessageType.ERROR
            )
            raise

        # Calculate execution time
        execution_time_ms = (time.time() - start_time) * 1000

        # Convert pipeline results to AlgorithmResult objects
        algorithm_results = self._convert_algorithm_results(
            pipeline_result.get('individual_results', [])
        )

        # Create ComparisonResult
        comparison = ComparisonResult(
            video1_path=video1,
            video2_path=video2,
            similarity_score=pipeline_result['global_score'],
            is_duplicate=pipeline_result['global_score'] >= threshold,
            algorithm_results=algorithm_results,
            pipeline_name=self._get_pipeline_name(),
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now(),
            metadata=pipeline_result.get('metadata', {})
        )

        # Finish progress tracking
        self.progress.finish_phase(
            "comparison",
            message=f"Score: {comparison.similarity_score:.1f}% | " +
                    ("✓ DUPLICATE" if comparison.is_duplicate else "✗ NOT DUPLICATE")
        )

        # Display result message
        result_type = MessageType.SUCCESS if comparison.is_duplicate else MessageType.INFO
        self.ui.display_message(
            f"Comparison complete: {comparison.similarity_score:.2f}% similarity",
            result_type
        )

        return comparison

    def _convert_algorithm_results(self, individual_results: list) -> list:
        """
        Convert pipeline individual results to AlgorithmResult objects.

        Args:
            individual_results: List of algorithm result dicts from pipeline

        Returns:
            List of AlgorithmResult objects

        Example:
            >>> pipeline_results = [
            ...     {'algorithm': 'frame_hash', 'similarity': 85.0, 'accepted': True,
            ...      'weight': 0.4, 'metadata': {}}
            ... ]
            >>> results = service._convert_algorithm_results(pipeline_results)
            >>> results[0].algorithm_name
            'frame_hash'
        """
        algorithm_results = []

        for result in individual_results:
            # Note: execution_time_ms not provided by pipeline individual results
            # We use 0.0 as placeholder (pipeline provides total time only)
            algorithm_results.append(
                AlgorithmResult(
                    algorithm_name=result['algorithm'],
                    similarity=result['similarity'],
                    accepted=result['accepted'],
                    weight=result['weight'],
                    execution_time_ms=0.0,  # Not available from pipeline
                    metadata=result.get('metadata', {})
                )
            )

        return algorithm_results

    def _get_pipeline_name(self) -> str:
        """
        Get a human-readable name for the pipeline.

        Returns:
            Pipeline name (preset name or "custom")

        Example:
            >>> service._get_pipeline_name()
            'balanced'
        """
        # Try to infer preset name from pipeline config
        # For now, return "custom" - could be enhanced to detect preset
        # TODO: Add name field to Pipeline class or detect from config
        return "custom"
