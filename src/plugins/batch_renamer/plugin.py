"""Batch Renamer plugin registration."""

from PyQt6.QtGui import QAction
from src.core.plugin_interface import PluginInterface
from src.core.logger import Logger
from src.core.i18n import t

logger = Logger.get_logger('BatchRenamer.Plugin')


class BatchRenamerPlugin(PluginInterface):
    """Plugin for batch renaming video files."""

    def __init__(self):
        """Initialize the plugin with minimal loading."""
        super().__init__()
        self.name = t("plugin.batch_renamer.name", "Batch Renamer")
        self.description = t("plugin.batch_renamer.description", "Rename multiple videos using patterns and metadata")
        self.version = "1.0.0"
        self.window = None
        self.main_window = None

    def get_name(self) -> str:
        """Return the plugin name."""
        return self.name

    def setup(self, main_window):
        """Configure the plugin with lazy loading."""
        self.main_window = main_window

        # Create menu action
        self.action = QAction(self.name, self.main_window)
        self.action.triggered.connect(self.show_window)

        # Add to Plugins menu
        self.main_window.plugins_menu.addAction(self.action)
        logger.debug("Batch Renamer plugin configured")

    def show_window(self):
        """Show the window with lazy loading."""
        if not self.window:
            # Lazy import - only when needed
            from .window import BatchRenamerWindow
            self.window = BatchRenamerWindow()

        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        logger.debug("Batch Renamer window displayed")
