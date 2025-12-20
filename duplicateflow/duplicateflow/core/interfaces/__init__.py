"""
Core interfaces for Clean Architecture.

These interfaces allow core services to interact with UI
without depending on specific CLI or GUI implementations.
"""

from .i_progress_reporter import IProgressReporter, NullProgressReporter
from .i_ui_adapter import IUIAdapter, MessageType, NullUIAdapter

__all__ = [
    "IProgressReporter",
    "NullProgressReporter",
    "IUIAdapter",
    "MessageType",
    "NullUIAdapter",
]
