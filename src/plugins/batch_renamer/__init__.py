"""Batch Renamer Plugin - Rename multiple video files using patterns."""

from src.core.plugin_interface import PluginInterface


class BatchRenamerPlugin(PluginInterface):
    """
    Batch Renamer plugin for VideoFlow.

    Allows users to rename multiple video files using:
    - Pattern-based naming with variables ({name}, {date}, {resolution}, etc.)
    - Find/replace operations (with regex support)
    - Case conversion
    - Preview before/after
    - Undo support
    """

    def __init__(self):
        """Initialize the Batch Renamer plugin."""
        super().__init__()
        self.name = "Batch Renamer"
        self.version = "1.0.0"
        self.description = "Rename multiple videos using patterns and metadata"
        self.icon = "🏷️"

    def create_window(self):
        """
        Create and return the Batch Renamer window.

        Returns:
            BatchRenamerWindow: The plugin window instance.
        """
        from .window import BatchRenamerWindow
        return BatchRenamerWindow()

    def get_menu_actions(self):
        """
        Get menu actions for this plugin.

        Returns:
            list: Empty list (no additional menu actions).
        """
        return []

    def cleanup(self):
        """Clean up plugin resources."""
        pass
