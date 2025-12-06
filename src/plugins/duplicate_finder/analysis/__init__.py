"""
Advanced analysis modules for the duplicate finder.

This package contains specialized analyzers for the 3-level advanced mode:
- Level 1: LSH audio fingerprinting (lsh_audio.py)
- Level 2: Long-period audio comparison (long_audio.py)
- Level 3: pHash visual confirmation (phash_visual.py)
- Pipeline: Orchestrator that chains all 3 levels (advanced_pipeline.py)
"""

from .phash_visual import PHashComparator
from .long_audio import LongAudioComparator
from .lsh_audio import LSHAudioAnalyzer
from .advanced_pipeline import AdvancedDuplicatePipeline

__all__ = [
    'PHashComparator',
    'LongAudioComparator',
    'LSHAudioAnalyzer',
    'AdvancedDuplicatePipeline'
]
