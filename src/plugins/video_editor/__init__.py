"""Video Editor plugin for VideoFlow.

This plugin provides comprehensive video editing capabilities including trimming,
cutting, scene detection, and video export with customizable quality settings.

Features:
    - Trim and cut video segments
    - Scene detection with configurable sensitivity
    - Frame-accurate editing with preview
    - Multiple video codec support (H.264, H.265, VP9)
    - Audio codec selection (AAC, MP3, Opus)
    - Quality presets (high, medium, low)
    - Timeline visualization with waveform display
    - Export with custom encoding parameters

The plugin uses MoviePy and OpenCV for video processing and PyQt6 for the
user interface.

Example:
    The plugin is automatically loaded by the PluginManager::

        from src.plugins.video_editor.plugin import VideoEditorPlugin

        plugin = VideoEditorPlugin()
        plugin.setup(main_window)
        plugin.show_window()
"""

# TODO: Remove l'import 'VideoEditorPlugin'

__all__ = ['VideoEditorPlugin']
