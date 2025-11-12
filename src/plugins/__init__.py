"""VideoFlow plugins package.

This package contains all available plugins for the VideoFlow application.
Each plugin provides specific video processing or management functionality.

Available plugins:
    - copy_manager: Copy folder structures with or without files
    - duplicate_finder: Find duplicate videos using perceptual hashing
    - video_converter: Convert videos between different formats
    - video_editor: Edit and trim video files
    - video_processor: Compress and merge videos with advanced options

Each plugin follows the PluginInterface contract and is automatically discovered
and loaded by the PluginManager at application startup.

Example:
    Plugins are automatically loaded by the PluginManager::

        from src.core.plugin_manager import PluginManager

        manager = PluginManager()
        plugins = manager.get_plugins()
        for plugin in plugins:
            print(f"Loaded: {plugin.name}")
"""

# Liste des plugins disponibles
__all__ = [
    'copy_manager',
    'duplicate_finder',
    'video_converter',
    'video_editor',
    'video_processor'
]
