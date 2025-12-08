"""
Cluster Detector for Duplicate Finder plugin.

Uses graph theory (connected components) to group similar videos into clusters.
Each cluster represents a group of videos that are similar to each other.
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict, deque

from src.core.logger import Logger

logger = Logger.get_logger(__name__)


@dataclass
class VideoNode:
    """
    Represents a video node in the similarity graph.

    Attributes:
        video_id: Unique identifier for the video
        path: File path to the video
        size: File size in bytes
        duration: Video duration in seconds
        connections: Set of connected video_ids
        similarity_scores: Dict mapping connected video_id to similarity score
    """
    video_id: int
    path: str
    size: int = 0
    duration: float = 0.0
    connections: Set[int] = field(default_factory=set)
    similarity_scores: Dict[int, float] = field(default_factory=dict)

    @property
    def degree(self) -> int:
        """Number of connections (edges) this node has."""
        return len(self.connections)

    @property
    def average_similarity(self) -> float:
        """Average similarity score with connected videos."""
        if not self.similarity_scores:
            return 0.0
        return sum(self.similarity_scores.values()) / len(self.similarity_scores)


@dataclass
class Cluster:
    """
    Represents a cluster of similar videos.

    Attributes:
        cluster_id: Unique identifier for the cluster
        video_ids: Set of video IDs in this cluster
        representative_id: ID of the "best" video to represent the cluster
        total_size: Total size of all videos in cluster
        avg_similarity: Average similarity between videos in cluster
    """
    cluster_id: int
    video_ids: Set[int] = field(default_factory=set)
    representative_id: Optional[int] = None
    total_size: int = 0
    avg_similarity: float = 0.0

    @property
    def size(self) -> int:
        """Number of videos in this cluster."""
        return len(self.video_ids)

    @property
    def duplicate_size(self) -> int:
        """Total size that could be saved by keeping only the representative."""
        return self.total_size if self.representative_id else 0


class ClusterDetector:
    """
    Detects clusters of similar videos using graph theory.

    Uses connected components algorithm to find groups of similar videos.
    Each cluster represents videos that are transitively similar to each other.

    Algorithm:
    1. Build graph: videos = nodes, duplicate pairs = edges
    2. Find connected components using DFS
    3. Compute cluster statistics
    4. Identify representative video for each cluster

    Example:
        detector = ClusterDetector()
        detector.add_duplicate_pair(video1_id, video2_id, similarity=0.95)
        detector.add_duplicate_pair(video2_id, video3_id, similarity=0.93)
        clusters = detector.detect_clusters()
        # Result: One cluster with [video1, video2, video3]
    """

    def __init__(self, min_similarity: float = 0.85):
        """
        Initialize cluster detector.

        Args:
            min_similarity: Minimum similarity threshold for considering videos as connected
        """
        self.min_similarity = min_similarity
        self.nodes: Dict[int, VideoNode] = {}
        self.clusters: List[Cluster] = []

        logger.info(f"ClusterDetector initialized (min_similarity={min_similarity})")

    # ==================== Graph Construction ====================

    def add_video(self, video_id: int, path: str, size: int = 0, duration: float = 0.0):
        """
        Add a video node to the graph.

        Args:
            video_id: Unique video identifier
            path: File path
            size: File size in bytes
            duration: Video duration in seconds
        """
        if video_id not in self.nodes:
            self.nodes[video_id] = VideoNode(
                video_id=video_id,
                path=path,
                size=size,
                duration=duration
            )
            logger.debug(f"Added video node {video_id}: {Path(path).name}")

    def add_duplicate_pair(self, video1_id: int, video2_id: int, similarity: float):
        """
        Add an edge between two videos if they are similar enough.

        Args:
            video1_id: First video ID
            video2_id: Second video ID
            similarity: Similarity score (0.0 to 1.0)
        """
        # Only add edge if similarity meets threshold
        if similarity < self.min_similarity:
            return

        # Ensure both videos exist as nodes
        if video1_id not in self.nodes:
            logger.warning(f"Video {video1_id} not added as node before adding edge")
            self.add_video(video1_id, f"unknown_{video1_id}")

        if video2_id not in self.nodes:
            logger.warning(f"Video {video2_id} not added as node before adding edge")
            self.add_video(video2_id, f"unknown_{video2_id}")

        # Add bidirectional edge
        self.nodes[video1_id].connections.add(video2_id)
        self.nodes[video1_id].similarity_scores[video2_id] = similarity

        self.nodes[video2_id].connections.add(video1_id)
        self.nodes[video2_id].similarity_scores[video1_id] = similarity

        logger.debug(f"Added edge: {video1_id} <-> {video2_id} (similarity={similarity:.2f})")

    def load_from_database(self, db_manager, similarity_threshold: Optional[float] = None):
        """
        Load duplicate pairs from database.

        Args:
            db_manager: VideoDatabase instance
            similarity_threshold: Override min_similarity for this load
        """
        threshold = similarity_threshold if similarity_threshold is not None else self.min_similarity

        try:
            # Load all videos
            videos = db_manager.get_all_video_info()
            for video in videos:
                self.add_video(
                    video_id=video['id'],
                    path=video['path'],
                    size=video.get('size', 0),
                    duration=video.get('duration', 0.0)
                )

            # Load duplicate pairs
            duplicates = db_manager.get_all_duplicates()
            for dup in duplicates:
                similarity = dup.get('similarity', 1.0)
                if similarity >= threshold:
                    self.add_duplicate_pair(
                        video1_id=dup['video1_id'],
                        video2_id=dup['video2_id'],
                        similarity=similarity
                    )

            logger.info(f"Loaded {len(self.nodes)} videos and {sum(n.degree for n in self.nodes.values()) // 2} duplicate pairs")

        except Exception as e:
            logger.error(f"Error loading from database: {e}")

    # ==================== Cluster Detection ====================

    def detect_clusters(self) -> List[Cluster]:
        """
        Detect clusters using connected components algorithm (DFS).

        Returns:
            List of Cluster objects, sorted by size (largest first)
        """
        visited: Set[int] = set()
        self.clusters = []
        cluster_id = 0

        # Find all connected components
        for video_id in self.nodes:
            if video_id not in visited:
                # Start DFS from this node
                cluster_videos = self._dfs_component(video_id, visited)

                if cluster_videos:
                    cluster = self._create_cluster(cluster_id, cluster_videos)
                    self.clusters.append(cluster)
                    cluster_id += 1

        # Sort clusters by size (largest first)
        self.clusters.sort(key=lambda c: c.size, reverse=True)

        logger.info(f"Detected {len(self.clusters)} clusters")
        return self.clusters

    def _dfs_component(self, start_id: int, visited: Set[int]) -> Set[int]:
        """
        Find all nodes in the connected component containing start_id using DFS.

        Args:
            start_id: Starting node ID
            visited: Set of already visited nodes (modified in-place)

        Returns:
            Set of all video IDs in this component
        """
        component = set()
        stack = [start_id]

        while stack:
            video_id = stack.pop()

            if video_id in visited:
                continue

            visited.add(video_id)
            component.add(video_id)

            # Add all unvisited neighbors to stack
            if video_id in self.nodes:
                for neighbor_id in self.nodes[video_id].connections:
                    if neighbor_id not in visited:
                        stack.append(neighbor_id)

        return component

    def _create_cluster(self, cluster_id: int, video_ids: Set[int]) -> Cluster:
        """
        Create a Cluster object from a set of video IDs.

        Args:
            cluster_id: Unique cluster identifier
            video_ids: Set of video IDs in this cluster

        Returns:
            Cluster object with computed statistics
        """
        cluster = Cluster(cluster_id=cluster_id, video_ids=video_ids)

        # Compute total size
        cluster.total_size = sum(
            self.nodes[vid].size for vid in video_ids if vid in self.nodes
        )

        # Compute average similarity within cluster
        similarities = []
        for vid in video_ids:
            if vid in self.nodes:
                node = self.nodes[vid]
                # Get similarities with other videos in this cluster
                for other_vid in video_ids:
                    if other_vid in node.similarity_scores:
                        similarities.append(node.similarity_scores[other_vid])

        cluster.avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

        # Find representative video (highest degree = most connections)
        cluster.representative_id = self._find_representative(video_ids)

        return cluster

    def _find_representative(self, video_ids: Set[int]) -> Optional[int]:
        """
        Find the "best" representative video for a cluster.

        Selection criteria (in order of priority):
        1. Highest degree (most connections)
        2. Highest average similarity
        3. Largest file size (assuming higher quality)

        Args:
            video_ids: Set of video IDs in cluster

        Returns:
            ID of representative video, or None if cluster is empty
        """
        if not video_ids:
            return None

        def score_video(vid: int) -> Tuple[int, float, int]:
            """Return tuple for sorting: (degree, avg_similarity, size)."""
            if vid not in self.nodes:
                return (0, 0.0, 0)

            node = self.nodes[vid]
            return (node.degree, node.average_similarity, node.size)

        # Find video with highest score
        representative = max(video_ids, key=score_video)
        return representative

    # ==================== Cluster Queries ====================

    def get_cluster_by_id(self, cluster_id: int) -> Optional[Cluster]:
        """Get cluster by its ID."""
        for cluster in self.clusters:
            if cluster.cluster_id == cluster_id:
                return cluster
        return None

    def get_cluster_for_video(self, video_id: int) -> Optional[Cluster]:
        """Get the cluster containing a specific video."""
        for cluster in self.clusters:
            if video_id in cluster.video_ids:
                return cluster
        return None

    def get_large_clusters(self, min_size: int = 3) -> List[Cluster]:
        """Get clusters with at least min_size videos."""
        return [c for c in self.clusters if c.size >= min_size]

    def get_cluster_videos(self, cluster_id: int) -> List[VideoNode]:
        """Get all video nodes in a cluster."""
        cluster = self.get_cluster_by_id(cluster_id)
        if not cluster:
            return []

        return [self.nodes[vid] for vid in cluster.video_ids if vid in self.nodes]

    def get_videos_to_delete(self, cluster_id: int) -> List[int]:
        """
        Get list of video IDs that could be deleted from a cluster.

        Keeps only the representative video, suggests deleting all others.

        Args:
            cluster_id: Cluster ID

        Returns:
            List of video IDs to potentially delete
        """
        cluster = self.get_cluster_by_id(cluster_id)
        if not cluster or not cluster.representative_id:
            return []

        # All videos except representative
        to_delete = [vid for vid in cluster.video_ids if vid != cluster.representative_id]
        return to_delete

    # ==================== Statistics ====================

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cluster detection statistics.

        Returns:
            Dictionary with statistics
        """
        if not self.clusters:
            self.detect_clusters()

        total_videos = len(self.nodes)
        clustered_videos = sum(c.size for c in self.clusters)
        singleton_videos = total_videos - clustered_videos

        total_duplicate_size = sum(c.duplicate_size for c in self.clusters)

        return {
            'total_videos': total_videos,
            'total_clusters': len(self.clusters),
            'clustered_videos': clustered_videos,
            'singleton_videos': singleton_videos,
            'largest_cluster_size': max((c.size for c in self.clusters), default=0),
            'average_cluster_size': clustered_videos / len(self.clusters) if self.clusters else 0.0,
            'total_duplicate_size_bytes': total_duplicate_size,
            'clusters_by_size': self._count_clusters_by_size(),
        }

    def _count_clusters_by_size(self) -> Dict[str, int]:
        """Count how many clusters fall into different size categories."""
        counts = {
            'pairs': 0,      # Size 2
            'small': 0,      # Size 3-5
            'medium': 0,     # Size 6-10
            'large': 0,      # Size 11-20
            'xlarge': 0,     # Size 21+
        }

        for cluster in self.clusters:
            size = cluster.size
            if size == 2:
                counts['pairs'] += 1
            elif size <= 5:
                counts['small'] += 1
            elif size <= 10:
                counts['medium'] += 1
            elif size <= 20:
                counts['large'] += 1
            else:
                counts['xlarge'] += 1

        return counts

    def export_clusters(self) -> List[Dict[str, Any]]:
        """
        Export clusters as a list of dictionaries for JSON serialization.

        Returns:
            List of cluster dictionaries
        """
        if not self.clusters:
            self.detect_clusters()

        result = []
        for cluster in self.clusters:
            videos = []
            for vid in cluster.video_ids:
                if vid in self.nodes:
                    node = self.nodes[vid]
                    videos.append({
                        'id': node.video_id,
                        'path': node.path,
                        'size': node.size,
                        'duration': node.duration,
                        'is_representative': vid == cluster.representative_id
                    })

            result.append({
                'cluster_id': cluster.cluster_id,
                'size': cluster.size,
                'total_size': cluster.total_size,
                'avg_similarity': cluster.avg_similarity,
                'representative_id': cluster.representative_id,
                'videos': videos
            })

        return result

    # ==================== Utilities ====================

    def clear(self):
        """Clear all nodes and clusters."""
        self.nodes.clear()
        self.clusters.clear()
        logger.info("Cleared all clusters")

    def __repr__(self) -> str:
        return f"ClusterDetector(nodes={len(self.nodes)}, clusters={len(self.clusters)})"


# Utility function
def detect_clusters_from_db(db_manager, min_similarity: float = 0.85) -> ClusterDetector:
    """
    Convenience function to detect clusters from a database.

    Args:
        db_manager: VideoDatabase instance
        min_similarity: Minimum similarity threshold

    Returns:
        ClusterDetector with detected clusters
    """
    detector = ClusterDetector(min_similarity=min_similarity)
    detector.load_from_database(db_manager, similarity_threshold=min_similarity)
    detector.detect_clusters()
    return detector
