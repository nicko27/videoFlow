"""
Adapter layer for integrating duplicateFlow into duplicate_finder.

This package provides the bridge between duplicate_finder's PyQt6 GUI
and duplicateFlow's backend algorithms and pipelines.

Modules:
    - duplicateflow_adapter: Main adapter for duplicateFlow API
    - progress_bridge: Bridge Qt signals ← duplicateFlow callbacks
    - results_transformer: Transform duplicateFlow results to GUI format
"""

from .duplicateflow_adapter import DuplicateFlowAdapter
from .progress_bridge import ProgressBridge
from .results_transformer import ResultsTransformer

__all__ = [
    'DuplicateFlowAdapter',
    'ProgressBridge',
    'ResultsTransformer',
]
