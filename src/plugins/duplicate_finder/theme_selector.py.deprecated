"""
Theme selector widget for switching between UI themes.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

try:
    from .themes import get_theme_manager
    from .design_system import Colors, Spacing, Typography
except ImportError:
    from themes import get_theme_manager
    from design_system import Colors, Spacing, Typography


class ThemeSelector(QWidget):
    """Widget for selecting and switching UI themes."""

    theme_changed = pyqtSignal(str)  # Emits theme key when changed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        self.setup_ui()

    def setup_ui(self):
        """Setup the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Label
        label = QLabel("🎨 Thème:")
        label.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XS))
        label.setStyleSheet(f"color: {Colors.GRAY_700};")
        layout.addWidget(label)

        # Theme dropdown
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(150)
        self.theme_combo.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XS))
        self.theme_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Spacing.RADIUS_SM}px;
                padding: {Spacing.XS}px {Spacing.SM}px;
                background-color: {Colors.WHITE};
                color: {Colors.BLACK};
            }}
            QComboBox:hover {{
                border-color: {Colors.PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: {Spacing.XS}px;
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {Colors.BORDER_DEFAULT};
                background-color: {Colors.WHITE};
                selection-background-color: {Colors.PRIMARY_LIGHT};
                selection-color: {Colors.BLACK};
            }}
        """)

        # Populate themes
        for key, theme in self.theme_manager.THEMES.items():
            self.theme_combo.addItem(theme.name, key)

        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        layout.addWidget(self.theme_combo)

        # Apply button
        apply_btn = QPushButton("Appliquer")
        apply_btn.setFont(QFont(Typography.FONT_FAMILY, Typography.FONT_XS))
        apply_btn.setMaximumHeight(25)
        apply_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: {Spacing.RADIUS_SM}px;
                padding: {Spacing.XS}px {Spacing.MD}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_DARK};
            }}
            QPushButton:pressed {{
                background-color: {Colors.PRIMARY_DARKER};
            }}
        """)
        apply_btn.clicked.connect(self._apply_theme)
        layout.addWidget(apply_btn)

    def _on_theme_changed(self, index):
        """Handle theme selection change."""
        # Just update selection, don't apply yet
        pass

    def _apply_theme(self):
        """Apply the selected theme."""
        theme_key = self.theme_combo.currentData()
        if theme_key:
            self.theme_manager.set_theme(theme_key)
            self.theme_changed.emit(theme_key)

    def get_current_theme_key(self) -> str:
        """Get currently selected theme key."""
        return self.theme_combo.currentData()
