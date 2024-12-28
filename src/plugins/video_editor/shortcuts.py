"""Raccourcis clavier pour le plugin Video Editor"""

from PyQt6.QtGui import QKeySequence
from PyQt6.QtCore import Qt

SHORTCUTS = {
    'open': QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_O),
    'save': QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_S),
    'play_pause': QKeySequence(Qt.Key.Key_Space),
    'cut': QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_X),
    'next_frame': QKeySequence(Qt.Key.Key_Right),
    'prev_frame': QKeySequence(Qt.Key.Key_Left),
    'next_frame_10': QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_Right),
    'prev_frame_10': QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_Left),
    'add_marker': QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_M),
    'detect_scenes': QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_D),
    'delete_segment': QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Delete),
    'zoom_in': QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Plus),
    'zoom_out': QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Minus),
}
