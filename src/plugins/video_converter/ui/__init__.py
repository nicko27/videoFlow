"""UI components for VideoConverter plugin.

This package contains modular UI components for the VideoConverter window.
"""

from .button_panels import ButtonPanelManager
from .table_widget import FileTableManager
from .dialogs import DialogManager
from .simple_view import SimpleCompressorView

__all__ = ['ButtonPanelManager', 'FileTableManager', 'DialogManager', 'SimpleCompressorView']
