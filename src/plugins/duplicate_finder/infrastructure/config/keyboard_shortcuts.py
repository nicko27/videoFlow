"""
Keyboard shortcuts configuration for the duplicate finder plugin.

This module centralizes all keyboard shortcuts to ensure consistency
and easy discoverability across the application.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence


class KeyboardShortcuts:
    """Centralized keyboard shortcuts configuration."""

    # Comparison dialog shortcuts
    COMPARISON_KEEP_LEFT = Qt.Key.Key_1
    COMPARISON_KEEP_RIGHT = Qt.Key.Key_2
    COMPARISON_KEEP_BOTH = Qt.Key.Key_3
    COMPARISON_SKIP = Qt.Key.Key_S
    COMPARISON_IGNORE = Qt.Key.Key_I
    COMPARISON_QUIT = Qt.Key.Key_Escape

    # Navigation shortcuts
    NAV_START = Qt.Key.Key_Home
    NAV_END = Qt.Key.Key_End
    NAV_PREV = Qt.Key.Key_Left
    NAV_NEXT = Qt.Key.Key_Right
    NAV_QUARTER = Qt.Key.Key_Q
    NAV_HALF = Qt.Key.Key_H
    NAV_THREE_QUARTERS = Qt.Key.Key_T

    # Space for play/pause (future feature)
    NAV_PLAY_PAUSE = Qt.Key.Key_Space

    # Video synchronization shortcuts
    SYNC_PLAY_BOTH = Qt.Key.Key_P
    SYNC_PAUSE_BOTH = Qt.Key.Key_Pause
    SYNC_RESYNC = Qt.Key.Key_R

    @staticmethod
    def get_comparison_shortcuts_help() -> str:
        """Get help text for comparison dialog shortcuts.

        Returns:
            Formatted help text with all shortcuts
        """
        return """
KEYBOARD SHORTCUTS:

Actions:
  1 - Keep Video A (left)
  2 - Keep Video B (right)
  3 - Keep Both Videos
  S - Skip this pair
  I - Ignore permanently
  Esc - Quit comparison

Navigation:
  Home - Go to start (0%)
  End - Go to end (100%)
  Q - Go to 25%
  H - Go to 50%
  T - Go to 75%
  ← - Previous position
  → - Next position
        """.strip()

    @staticmethod
    def get_subsequence_shortcuts_help() -> str:
        """Get help text for subsequence comparison dialog shortcuts.

        Returns:
            Formatted help text with all shortcuts
        """
        return """
KEYBOARD SHORTCUTS:

Actions:
  1 - Keep Short Video
  2 - Keep Long Video
  3 - Keep Both Videos
  Esc - Skip this pair

Navigation:
  Home - Go to start (0%)
  End - Go to end (100%)
  Q - Go to 25%
  H - Go to 50%
  T - Go to 75%
  ← - Previous position
  → - Next position
        """.strip()

    @staticmethod
    def format_shortcut_display(key: Qt.Key, description: str) -> str:
        """Format a shortcut for display.

        Args:
            key: Qt keyboard key
            description: Description of the shortcut action

        Returns:
            Formatted string for display
        """
        # Map Qt keys to display names
        key_names = {
            Qt.Key.Key_1: "1",
            Qt.Key.Key_2: "2",
            Qt.Key.Key_3: "3",
            Qt.Key.Key_S: "S",
            Qt.Key.Key_I: "I",
            Qt.Key.Key_Escape: "Esc",
            Qt.Key.Key_Home: "Home",
            Qt.Key.Key_End: "End",
            Qt.Key.Key_Left: "←",
            Qt.Key.Key_Right: "→",
            Qt.Key.Key_Q: "Q",
            Qt.Key.Key_H: "H",
            Qt.Key.Key_T: "T",
            Qt.Key.Key_Space: "Space"
        }

        key_name = key_names.get(key, str(key))
        return f"{key_name} - {description}"
