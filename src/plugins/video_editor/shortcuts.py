"""Keyboard shortcuts for the plugin Video Editor"""

from PyQt6.QtGui import QKeySequence
from PyQt6.QtCore import Qt

SHORTCUTS = {
    'open': QKeySequence(Qt.Modify.CTRL | Qt.Key.Key_O),
    'save': QKeySequence(Qt.Modify.CTRL | Qt.Key.Key_S),
    'play_pause': QKeySequence(Qt.Key.Key_Space),
    'cut': QKeySequence(Qt.Modify.CTRL | Qt.Key.Key_X),
    'next_frame': QKeySequence(Qt.Key.Key_Right),
    'prev_frame': QKeySequence(Qt.Key.Key_Left),
    'next_frame_10': QKeySequence(Qt.Modify.SHIFT | Qt.Key.Key_Right),
    'prev_frame_10': QKeySequence(Qt.Modify.SHIFT | Qt.Key.Key_Left),
    'add_marker': QKeySequence(Qt.Modify.CTRL | Qt.Key.Key_M),
    'detect_scenes': QKeySequence(Qt.Modify.CTRL | Qt.Modify.SHIFT | Qt.Key.Key_D),
    'delete_segment': QKeySequence(Qt.Modify.CTRL | Qt.Key.Key_Delete),
    'zoom_in': QKeySequence(Qt.Modify.CTRL | Qt.Key.Key_Plus),
    'zoom_out': QKeySequence(Qt.Modify.CTRL | Qt.Key.Key_Minus),
}