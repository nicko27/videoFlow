"""Abstract plugin interface for VideoFlow.

This module defines the PluginInterface abstract base class that all plugins
must implement to integrate with the VideoFlow application.
"""

from abc import ABC, abstractmethod

class PluginInterface(ABC):
    """Abstract base class that all VideoFlow plugins must implement.

    Defines the contract that plugins must follow to be loaded and managed
    by the PluginManager. All plugins must inherit from this class and
    implement its abstract methods.

    Attributes:
        name (str): Display name of the plugin.
        description (str): Short description of plugin functionality.
        version (str): Plugin version number (e.g., "1.0.0").
        window: Reference to the plugin's main window (if any).
        main_window: Reference to the application's main window.
    """

    @abstractmethod
    def __init__(self):
        """Initialize the plugin.

        Must set up the basic plugin attributes: name, description, version.
        Should not perform heavy initialization here.
        """
        self.name = ""
        self.description = ""
        self.version = ""
        self.window = None
        self.main_window = None
    
    @abstractmethod
    def setup(self, main_window):
        """Configure the plugin and integrate it with the main window.

        Called by the PluginManager after the plugin is instantiated.
        Plugins should create menu actions and connect to the main window here.

        Args:
            main_window (QMainWindow): The application's main window instance.
        """
        pass
