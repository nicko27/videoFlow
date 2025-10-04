# ============================================================================
# __init__.py - Point d'entrée du module window
# ============================================================================

"""
Module window pour le détecteur de doublons vidéo
Structure modulaire avec séparation des responsabilités
"""

from .video_preview_widget import VideoPreviewWidget
from .comparison_dialog import ComparisonDialog
from .progress_widgets import ModernProgressWidget, FileListWidget, StatusIndicator
from .main_window import DuplicateFinderWindow, ParallelHashWorker, OptimizedComparisonWorker

__all__ = [
    'VideoPreviewWidget',
    'ComparisonDialog', 
    'CompactVideoCard',
    'SimilarityIndicator',
    'NavigationControls',
    'ModernProgressWidget',
    'FileListWidget', 
    'StatusIndicator',
    'DuplicateFinderWindow',
    'ParallelHashWorker',
    'OptimizedComparisonWorker'
]