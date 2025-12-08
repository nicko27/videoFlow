"""
Advanced analysis modules for the duplicate finder.

This package contains specialized analyzers for the 3-level advanced mode:
- Level 1: LSH audio fingerprinting (lsh_audio.py)
- Level 2: Long-period audio comparison (long_audio.py)
- Level 3: pHash visual confirmation (phash_visual.py)
- Pipeline: Orchestrator that chains all 3 levels (advanced_pipeline.py)
- Cluster Detection: Graph-based clustering of similar videos (cluster_detector.py)
"""

from .phash_visual import PHashComparator
from .long_audio import LongAudioComparator
from .lsh_audio import LSHAudioAnalyzer
from .advanced_pipeline import AdvancedDuplicatePipeline
from .cluster_detector import ClusterDetector, VideoNode, Cluster, detect_clusters_from_db

__all__ = [
    'PHashComparator',
    'LongAudioComparator',
    'LSHAudioAnalyzer',
    'AdvancedDuplicatePipeline',
    'ClusterDetector',
    'VideoNode',
    'Cluster',
    'detect_clusters_from_db'
]
