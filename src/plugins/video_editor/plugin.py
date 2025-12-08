"""Video Editor plugin implementation.

This module contains the plugin interface implementation for the Video Editor,
which provides comprehensive video editing capabilities including trimming,
cutting, and scene detection.
"""

from PyQt6.QtGui import QAction
from src.core.plugin_interface import PluginInterface
from src.core.logger import Logger
from src.core.i18n import t

logger = Logger.get_logger('VideoEditor.Plugin')

class VideoEditorPlugin(PluginInterface):
    """Video Editor plugin for VideoFlow.

    Provides comprehensive video editing capabilities including trimming,
    cutting, scene detection, and export with customizable quality settings.

    Attributes:
        name (str): Display name of the plugin.
        description (str): Short description of plugin functionality.
        version (str): Plugin version number.
        window (VideoEditorWindow): The plugin's main window instance.
        main_window (QMainWindow): Reference to the application's main window.
        action (QAction): Menu action for launching the plugin.
    """

    def __init__(self):
        """Initialize the Video Editor plugin.

        Sets up the plugin's basic properties and prepares it for integration
        with the main application.
        """
        super().__init__()
        self.name = t("plugin.video_editor.name", "Video Editor")
        self.description = t("plugin.video_editor.description", "Édite et découpe des vidéos")
        self.version = "1.0.0"
        self.window = None
        logger.debug("Plugin VideoEditor initialisé")
    
    def setup(self, main_window):
        """Configure the plugin and integrate it with the main window.

        Creates a menu action and adds it to the main window's plugin menu.

        Args:
            main_window (QMainWindow): The application's main window instance.
        """
        self.main_window = main_window
        
        # Créer l'action in le menu
        self.action = QAction(self.name, self.main_window)
        self.action.triggered.connect(self.show_window)
        
        # Add au menu Plugins
        self.main_window.plugins_menu.addAction(self.action)
        logger.debug("Plugin VideoEditor configuré")
    
    def show_window(self):
        """Display the plugin window.

        Creates the Video Editor window if it doesn't exist and displays it.
        Uses lazy loading to only create the window when first needed.
        """
        if not self.window:
            from .window import VideoEditorWindow
            self.window = VideoEditorWindow()
        self.window.show()
        logger.debug("Window VideoEditor affichée")
