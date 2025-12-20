"""
Duplicate finder service for detecting duplicate videos in a collection.
"""
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

from duplicateflow.core.interfaces.i_progress_reporter import IProgressReporter
from duplicateflow.core.interfaces.i_ui_adapter import IUIAdapter, MessageType
from duplicateflow.core.models.detection import DetectionResult, DuplicateGroup
from duplicateflow.core.models.comparison import ComparisonResult
from .comparison_service import ComparisonService


class UnionFind:
    """
    Union-Find (Disjoint Set Union) data structure for clustering.

    Used to group videos into duplicate clusters based on pairwise comparisons.
    """

    def __init__(self, n: int):
        """
        Initialize Union-Find structure.

        Args:
            n: Number of elements
        """
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        """
        Find root of element x with path compression.

        Args:
            x: Element index

        Returns:
            Root index
        """
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> None:
        """
        Unite sets containing x and y.

        Args:
            x: First element index
            y: Second element index
        """
        px, py = self.find(x), self.find(y)
        if px == py:
            return

        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1

    def get_groups(self) -> Dict[int, List[int]]:
        """
        Get all groups of connected elements.

        Returns:
            Dictionary mapping root index to list of element indices
        """
        groups = {}
        for i in range(len(self.parent)):
            root = self.find(i)
            if root not in groups:
                groups[root] = []
            groups[root].append(i)
        return groups


class DuplicateFinderService:
    """
    Service for finding duplicate videos in a collection.

    Performs N-to-N comparisons and groups duplicates into clusters.

    Example:
        >>> from duplicateflow.core.interfaces.i_progress_reporter import NullProgressReporter
        >>> from duplicateflow.core.interfaces.i_ui_adapter import NullUIAdapter
        >>> from pathlib import Path
        >>>
        >>> service = DuplicateFinderService(
        ...     progress=NullProgressReporter(),
        ...     ui=NullUIAdapter()
        ... )
        >>>
        >>> videos = [Path("/v1.mp4"), Path("/v2.mp4"), Path("/v3.mp4")]
        >>> result = service.find_duplicates(
        ...     videos,
        ...     threshold=70.0
        ... )
        >>> print(f"Found {len(result.duplicate_groups)} duplicate groups")
    """

    def __init__(
        self,
        progress: IProgressReporter,
        ui: IUIAdapter,
        comparison_service: Optional[ComparisonService] = None
    ):
        """
        Initialize duplicate finder service.

        Args:
            progress: Progress reporter for tracking execution
            ui: UI adapter for displaying messages
            comparison_service: Optional ComparisonService instance

        Example:
            >>> service = DuplicateFinderService(progress, ui)
        """
        self.progress = progress
        self.ui = ui
        self.comparison_service = comparison_service or ComparisonService(progress, ui)

    def find_duplicates(
        self,
        video_paths: List[Path],
        threshold: float = 70.0,
        max_comparisons: Optional[int] = None
    ) -> DetectionResult:
        """
        Find duplicate videos in a collection.

        Performs pairwise comparisons and groups duplicates using clustering.

        Args:
            video_paths: List of video file paths to analyze
            threshold: Similarity threshold for duplicate detection (0-100)
            max_comparisons: Optional limit on total comparisons (for large sets)

        Returns:
            DetectionResult with duplicate groups and statistics

        Raises:
            ValueError: If fewer than 2 videos provided or invalid threshold

        Example:
            >>> videos = [Path("/v1.mp4"), Path("/v2.mp4"), Path("/v3.mp4")]
            >>> result = service.find_duplicates(videos, threshold=75.0)
            >>> print(f"Space reclaimable: {result.space_reclaimable_mb:.2f} MB")
        """
        # Validation
        if len(video_paths) < 2:
            raise ValueError("Need at least 2 videos to detect duplicates")
        if not (0 <= threshold <= 100):
            raise ValueError(f"Threshold must be between 0 and 100, got {threshold}")

        # Calculate total comparisons needed
        n = len(video_paths)
        total_comparisons = n * (n - 1) // 2

        # Check if limiting comparisons
        if max_comparisons and total_comparisons > max_comparisons:
            self.ui.display_message(
                f"Warning: {total_comparisons} comparisons needed, limiting to {max_comparisons}",
                MessageType.WARNING
            )
            total_comparisons = max_comparisons

        # Display info
        self.ui.display_message(
            f"Starting duplicate detection: {n} videos, {total_comparisons} comparisons",
            MessageType.INFO
        )

        # Start progress tracking
        start_time = time.time()
        self.progress.start_phase(
            "detection",
            total=total_comparisons,
            message=f"Comparing {n} videos..."
        )

        # Perform pairwise comparisons
        comparisons = []
        duplicate_pairs = []
        count = 0

        for i in range(n):
            for j in range(i + 1, n):
                if max_comparisons and count >= max_comparisons:
                    break

                # Update progress
                self.progress.update(
                    "detection",
                    current=count + 1,
                    message=f"{video_paths[i].name} vs {video_paths[j].name}"
                )

                # Compare videos
                try:
                    result = self.comparison_service.compare_videos(
                        video_paths[i],
                        video_paths[j],
                        threshold
                    )

                    comparisons.append(result)

                    # Track duplicate pairs
                    if result.is_duplicate:
                        duplicate_pairs.append((i, j, result.similarity_score))

                except Exception as e:
                    self.ui.display_message(
                        f"Error comparing {video_paths[i].name} vs {video_paths[j].name}: {str(e)}",
                        MessageType.WARNING
                    )

                count += 1

            if max_comparisons and count >= max_comparisons:
                break

        # Build duplicate groups using Union-Find
        groups = self._build_duplicate_groups(duplicate_pairs, video_paths)

        # Calculate statistics
        space_reclaimable = self._calculate_reclaimable_space(groups)

        # Calculate execution time
        execution_time_seconds = time.time() - start_time

        # Finish progress
        self.progress.finish_phase(
            "detection",
            message=f"Found {len(groups)} duplicate groups in {execution_time_seconds:.1f}s"
        )

        # Display summary
        self.ui.display_message(
            f"Detection complete: {len(groups)} groups, {sum(len(g.videos) - 1 for g in groups)} duplicates found",
            MessageType.SUCCESS
        )

        return DetectionResult(
            duplicate_groups=groups,
            total_videos_scanned=n,
            total_comparisons=count,
            duplicates_found=sum(len(g.videos) - 1 for g in groups),
            space_reclaimable_mb=space_reclaimable,
            execution_time_seconds=execution_time_seconds,
            timestamp=datetime.now(),
            pipeline_used=self.comparison_service._get_pipeline_name()
        )

    def _build_duplicate_groups(
        self,
        duplicate_pairs: List[tuple],
        all_videos: List[Path]
    ) -> List[DuplicateGroup]:
        """
        Build duplicate groups from pairwise comparisons using Union-Find.

        Args:
            duplicate_pairs: List of (index1, index2, similarity) tuples
            all_videos: List of all video paths

        Returns:
            List of DuplicateGroup objects

        Example:
            >>> pairs = [(0, 1, 85.0), (1, 2, 90.0)]
            >>> videos = [Path("/v1.mp4"), Path("/v2.mp4"), Path("/v3.mp4")]
            >>> groups = service._build_duplicate_groups(pairs, videos)
            >>> len(groups)
            1
        """
        n = len(all_videos)
        uf = UnionFind(n)

        # Build similarity matrix for average calculation
        similarity_matrix = {}

        # Unite duplicate pairs
        for i, j, similarity in duplicate_pairs:
            uf.union(i, j)
            similarity_matrix[(i, j)] = similarity

        # Get groups from Union-Find
        group_indices = uf.get_groups()

        # Convert to DuplicateGroup objects (only groups with 2+ videos)
        duplicate_groups = []

        for root, indices in group_indices.items():
            if len(indices) < 2:
                continue  # Skip singles

            # Get video paths for this group
            videos = [all_videos[i] for i in indices]

            # Calculate average similarity for this group
            avg_similarity = self._calculate_avg_similarity(indices, similarity_matrix)

            # Calculate total size
            total_size_mb = sum(
                v.stat().st_size / (1024 * 1024) for v in videos if v.exists()
            )

            # Choose representative (largest file)
            representative = max(
                videos,
                key=lambda v: v.stat().st_size if v.exists() else 0
            )

            duplicate_groups.append(
                DuplicateGroup(
                    videos=videos,
                    representative=representative,
                    avg_similarity=avg_similarity,
                    total_size_mb=total_size_mb
                )
            )

        return duplicate_groups

    def _calculate_avg_similarity(
        self,
        indices: List[int],
        similarity_matrix: Dict[tuple, float]
    ) -> float:
        """
        Calculate average similarity within a group.

        Args:
            indices: Indices of videos in the group
            similarity_matrix: Matrix of pairwise similarities

        Returns:
            Average similarity score

        Example:
            >>> indices = [0, 1, 2]
            >>> matrix = {(0, 1): 85.0, (1, 2): 90.0}
            >>> avg = service._calculate_avg_similarity(indices, matrix)
            >>> 85.0 <= avg <= 90.0
            True
        """
        if len(indices) < 2:
            return 100.0

        similarities = []

        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                idx1, idx2 = indices[i], indices[j]
                # Try both orderings (matrix may not be symmetric in keys)
                key1 = (idx1, idx2)
                key2 = (idx2, idx1)
                if key1 in similarity_matrix:
                    similarities.append(similarity_matrix[key1])
                elif key2 in similarity_matrix:
                    similarities.append(similarity_matrix[key2])

        if not similarities:
            return 100.0  # Assume high similarity if no data

        return sum(similarities) / len(similarities)

    def _calculate_reclaimable_space(self, groups: List[DuplicateGroup]) -> float:
        """
        Calculate total reclaimable space from duplicate groups.

        Space reclaimable = sum of all duplicates (keeping representative).

        Args:
            groups: List of duplicate groups

        Returns:
            Reclaimable space in MB

        Example:
            >>> groups = [
            ...     DuplicateGroup(
            ...         videos=[Path("/v1.mp4"), Path("/v2.mp4")],
            ...         representative=Path("/v1.mp4"),
            ...         avg_similarity=85.0,
            ...         total_size_mb=300.0
            ...     )
            ... ]
            >>> space = service._calculate_reclaimable_space(groups)
            >>> space >= 0
            True
        """
        total_reclaimable = 0.0

        for group in groups:
            # Calculate size of duplicates (all except representative)
            for video in group.videos:
                if video != group.representative and video.exists():
                    size_mb = video.stat().st_size / (1024 * 1024)
                    total_reclaimable += size_mb

        return total_reclaimable
