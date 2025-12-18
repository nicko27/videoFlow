"""
Advanced analysis modules for the duplicate finder.

This package contains specialized analyzers:
- Cluster Detection: Graph-based clustering of similar videos (cluster_detector.py)

Note: The 3-level advanced pipeline (LSH audio, long audio, pHash visual) has been
replaced by DuplicateFlow algorithms. See adapters/advanced_pipeline_adapter.py.
"""

from .cluster_detector import ClusterDetector, VideoNode, Cluster, detect_clusters_from_db

__all__ = [
    'ClusterDetector',
    'VideoNode',
    'Cluster',
    'detect_clusters_from_db'
]
