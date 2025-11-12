"""Dialogs module for Video Editor."""

from .video_merger_dialog import VideoMergeWorker, VideoMergerDialog
from .transition_dialog import TransitionDialog, QuickTransitionButton
from .preferences_dialog import PreferencesDialog
from .text_editor_dialog import TextEditorDialog
from .export_dialog import ExportDialog, ExportWorker

__all__ = [
    'VideoMergeWorker',
    'VideoMergerDialog',
    'TransitionDialog',
    'QuickTransitionButton',
    'PreferencesDialog',
    'TextEditorDialog',
    'ExportDialog',
    'ExportWorker'
]
