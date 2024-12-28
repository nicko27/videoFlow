"""Styles pour le plugin Video Editor"""

MAIN_STYLE = """
QMainWindow {
    background-color: #1e1e1e;
    color: #ffffff;
}

QWidget {
    color: #ffffff;
}

QPushButton {
    background-color: #2d2d2d;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    color: #ffffff;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #3d3d3d;
}

QPushButton:pressed {
    background-color: #4d4d4d;
}

QPushButton:disabled {
    background-color: #2d2d2d;
    color: #666666;
}

QTableWidget {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    gridline-color: #3d3d3d;
}

QTableWidget::item {
    padding: 4px;
    color: #ffffff;
}

QTableWidget::item:selected {
    background-color: #0078d4;
}

QHeaderView::section {
    background-color: #2d2d2d;
    color: #ffffff;
    padding: 4px;
    border: 1px solid #3d3d3d;
}

QSlider::groove:horizontal {
    border: 1px solid #3d3d3d;
    height: 8px;
    background: #2d2d2d;
    margin: 2px 0;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: #0078d4;
    border: 1px solid #0078d4;
    width: 18px;
    margin: -2px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #1084d8;
}

QProgressBar {
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    text-align: center;
    background-color: #2d2d2d;
}

QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 3px;
}

QLabel {
    color: #ffffff;
}

QMessageBox {
    background-color: #1e1e1e;
}

QMessageBox QPushButton {
    min-width: 80px;
}

QInputDialog {
    background-color: #1e1e1e;
}

QInputDialog QLineEdit {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 4px;
    color: #ffffff;
}
"""

# Style pour les boutons d'action dans la table
ACTION_BUTTON_STYLE = """
QPushButton {
    background-color: transparent;
    border: none;
    border-radius: 2px;
    padding: 4px;
    font-size: 16px;
}

QPushButton:hover {
    background-color: #3d3d3d;
}
"""

# Style pour la barre d'outils
TOOLBAR_STYLE = """
QToolBar {
    background-color: #2d2d2d;
    border: none;
    spacing: 4px;
    padding: 4px;
}

QToolBar QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 4px;
}

QToolBar QToolButton:hover {
    background-color: #3d3d3d;
}

QToolBar QToolButton:pressed {
    background-color: #4d4d4d;
}
"""

# Style pour le widget de forme d'onde
WAVEFORM_STYLE = """
WaveformWidget {
    background-color: #1a1a1a;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
}
"""

# Couleurs pour les segments
SEGMENT_COLORS = [
    "#0078D4",  # Bleu
    "#107C10",  # Vert
    "#D83B01",  # Orange
    "#E81123",  # Rouge
    "#744DA9",  # Violet
    "#FF8C00",  # Orange foncé
    "#018574",  # Turquoise
    "#C239B3",  # Rose
]
