"""Copy Manager plugin for VideoFlow.

This plugin provides functionality to copy folder structures with flexible options
for including or excluding files, preserving metadata, and handling hidden files.

Features:
    - Copy folder structures with or without files
    - Preserve macOS metadata (tags, colors, comments)
    - Include or exclude hidden files
    - Move source files to trash after copying
    - Progress tracking and logging
    - Automatic unique naming for duplicate files

The plugin uses PyQt6 for the user interface and provides real-time progress
updates during copy operations.

Example:
    The plugin is automatically loaded by the PluginManager::

        # Plugin is accessed through the main window's plugin menu
        # or programmatically:
        from src.plugins.copy_manager.plugin import CopyManagerPlugin

        plugin = CopyManagerPlugin()
        plugin.setup(main_window)
        plugin.show_window()
"""

# TODO: Remove l'import 'CopyManagerPlugin'

__all__ = ['CopyManagerPlugin']
