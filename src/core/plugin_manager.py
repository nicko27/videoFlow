"""Plugin management system for VideoFlow.

This module provides the PluginManager class which handles automatic discovery,
loading, and lifecycle management of all plugins in the application.
"""

import os
import sys
import inspect
import importlib
import importlib.util
import traceback
from typing import List
from src.core.plugin_interface import PluginInterface
from src.core.logger import Logger

logger = Logger.get_logger('PluginManager')

class PluginManager:
    """Manages plugin discovery, loading, and lifecycle.

    Automatically discovers and loads all valid plugins from the plugins directory.
    Each plugin must have a plugin.py file with a class that inherits from
    PluginInterface.

    Attributes:
        plugins (List[PluginInterface]): List of successfully loaded plugin instances.
        plugins_dir (str): Path to the plugins directory.

    Example:
        manager = PluginManager()
        plugins = manager.get_plugins()
        for plugin in plugins:
            plugin.setup(main_window)
    """

    def __init__(self):
        """Initialize the PluginManager.

        Sets up the plugins directory path, ensures it's in PYTHONPATH,
        and automatically loads all available plugins.
        """
        self.plugins = []
        self.plugins_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plugins')

        # Add root directory to PYTHONPATH
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
            logger.debug(f"Adding {root_dir} to PYTHONPATH")
        
        self.load_plugins()

    def load_plugins(self) -> List[PluginInterface]:
        """Load all available plugins from the plugins directory.

        Scans the plugins directory for valid plugin folders (containing both
        __init__.py and plugin.py files), loads the plugin modules, and
        instantiates plugin classes that inherit from PluginInterface.

        Returns:
            List[PluginInterface]: List of successfully loaded plugin instances.

        Note:
            Plugins must:
            - Be in a subdirectory of the plugins folder
            - Contain both __init__.py and plugin.py files
            - Have a class that inherits from PluginInterface
            - Not start with underscore (private folders are ignored)
        """
        logger.debug("Loading plugins...")
        logger.debug(f"Plugins directory: {self.plugins_dir}")

        if not os.path.exists(self.plugins_dir):
            logger.error(f"Plugins directory does not exist: {self.plugins_dir}")
            return self.plugins

        # Browse all folders in plugins/
        for plugin_folder in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, plugin_folder)
            logger.debug(f"Checking directory: {plugin_path}")

            # Ignore files and folders starting with _
            if not os.path.isdir(plugin_path) or plugin_folder.startswith('_'):
                continue

            # Check for required files
            plugin_file = os.path.join(plugin_path, 'plugin.py')
            init_file = os.path.join(plugin_path, '__init__.py')

            if not os.path.exists(plugin_file) or not os.path.exists(init_file):
                logger.warning(f"Invalid plugin structure in {plugin_folder}")
                continue

            try:
                logger.debug(f"Attempting to load plugin: {plugin_folder}")

                # Load plugin.py module
                spec = importlib.util.spec_from_file_location(
                    f"src.plugins.{plugin_folder}.plugin",
                    plugin_file
                )
                if not spec or not spec.loader:
                    logger.error(f"Unable to create spec for {plugin_file}")
                    continue

                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
                logger.debug(f"Module loaded: {module}")

                # Look for a class that inherits from PluginInterface
                for name, obj in inspect.getmembers(module):
                    logger.debug(f"Inspecting {name}")
                    if (inspect.isclass(obj) and
                        issubclass(obj, PluginInterface) and
                        obj != PluginInterface):
                        try:
                            plugin = obj()
                            self.plugins.append(plugin)
                            logger.info(f"Plugin loaded: {plugin.name}")
                        except Exception as e:
                            logger.error(f"Error instantiating plugin {name}: {str(e)}")
                            logger.error(traceback.format_exc())

            except Exception as e:
                logger.error(f"Error loading plugin {plugin_folder}: {str(e)}")
                logger.error(traceback.format_exc())

        logger.info(f"{len(self.plugins)} plugins loaded")
        return self.plugins

    def setup_plugins(self, main_window):
        """Configure all loaded plugins.

        Calls the setup method on each loaded plugin, passing the main window
        reference. This allows plugins to integrate with the application UI.

        Args:
            main_window (QMainWindow): The application's main window instance.

        Note:
            If a plugin's setup method fails, the error is logged but doesn't
            prevent other plugins from being configured.
        """
        for plugin in self.plugins:
            try:
                plugin.setup(main_window)
                logger.debug(f"Plugin configured: {plugin.name}")
            except Exception as e:
                logger.error(f"Error configuring plugin {plugin.name}: {str(e)}")
                logger.error(traceback.format_exc())

    def get_plugins(self) -> List[PluginInterface]:
        """Get the list of loaded plugins.

        Returns:
            List[PluginInterface]: List of all successfully loaded plugin instances.
        """
        return self.plugins
