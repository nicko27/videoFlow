"""Preferences dialog for Video Editor settings.

This dialog allows users to configure various settings including
themes, timeline height, font size, and accent colors.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QGridLayout, QSpinBox, QColorDialog,
    QSlider, QTabWidget, QWidget, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from ..themes import ThemePresets, Theme
from ..theme_manager import ThemeManager


class PreferencesDialog(QDialog):
    """Dialog for configuring Video Editor preferences.

    Allows configuration of:
    - Theme selection
    - Timeline height
    - Font size
    - Accent color

    Signals:
        theme_changed: Emitted when theme is changed (Theme)
        timeline_height_changed: Emitted when timeline height changes (int)
        font_size_changed: Emitted when font size changes (int)
        accent_color_changed: Emitted when accent color changes (str)
    """

    theme_changed = pyqtSignal(object)  # Theme
    timeline_height_changed = pyqtSignal(int)
    font_size_changed = pyqtSignal(int)
    accent_color_changed = pyqtSignal(str)

    def __init__(self, theme_manager: ThemeManager, parent=None):
        """Initialize preferences dialog.

        Args:
            theme_manager: ThemeManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.current_theme = theme_manager.get_current_theme()

        self.setup_ui()
        self.load_current_settings()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Préférences - Video Editor")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        layout = QVBoxLayout(self)

        # Tab widget for different preference categories
        tabs = QTabWidget()

        # Appearance tab
        appearance_tab = self._create_appearance_tab()
        tabs.addTab(appearance_tab, "🎨 Apparence")

        # Editor tab
        editor_tab = self._create_editor_tab()
        tabs.addTab(editor_tab, "✏️ Éditeur")

        layout.addWidget(tabs)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        reset_btn = QPushButton("Réinitialiser")
        reset_btn.setToolTip("Réinitialiser aux paramètres par défaut")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("Appliquer")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_btn)

        layout.addLayout(button_layout)

    def _create_appearance_tab(self) -> QWidget:
        """Create appearance settings tab.

        Returns:
            Widget with appearance settings
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Theme selection group
        theme_group = QGroupBox("Thème")
        theme_layout = QGridLayout()

        theme_layout.addWidget(QLabel("Sélectionner un thème:"), 0, 0)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(ThemePresets.get_preset_names())
        self.theme_combo.currentTextChanged.connect(self.on_theme_preview)
        theme_layout.addWidget(self.theme_combo, 0, 1)

        # Theme preview
        self.theme_preview = QLabel()
        self.theme_preview.setMinimumHeight(100)
        self.theme_preview.setStyleSheet("""
            QLabel {
                border: 2px solid #555;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        theme_layout.addWidget(self.theme_preview, 1, 0, 1, 2)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # Customization group
        custom_group = QGroupBox("Personnalisation")
        custom_layout = QGridLayout()

        # Accent color
        custom_layout.addWidget(QLabel("Couleur d'accent:"), 0, 0)

        self.accent_color_btn = QPushButton("Choisir couleur...")
        self.accent_color_btn.clicked.connect(self.choose_accent_color)
        custom_layout.addWidget(self.accent_color_btn, 0, 1)

        self.accent_color_preview = QLabel("  ")
        self.accent_color_preview.setFixedSize(50, 30)
        self.accent_color_preview.setStyleSheet("border: 1px solid #555; border-radius: 4px;")
        custom_layout.addWidget(self.accent_color_preview, 0, 2)

        # Font size
        custom_layout.addWidget(QLabel("Taille de police:"), 1, 0)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 16)
        self.font_size_spin.setSuffix(" pt")
        custom_layout.addWidget(self.font_size_spin, 1, 1)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        layout.addStretch()

        return widget

    def _create_editor_tab(self) -> QWidget:
        """Create editor settings tab.

        Returns:
            Widget with editor settings
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Timeline group
        timeline_group = QGroupBox("Timeline")
        timeline_layout = QGridLayout()

        timeline_layout.addWidget(QLabel("Hauteur de la timeline:"), 0, 0)

        self.timeline_height_spin = QSpinBox()
        self.timeline_height_spin.setRange(50, 200)
        self.timeline_height_spin.setSuffix(" px")
        self.timeline_height_spin.setValue(80)
        timeline_layout.addWidget(self.timeline_height_spin, 0, 1)

        self.timeline_height_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_height_slider.setRange(50, 200)
        self.timeline_height_slider.setValue(80)
        timeline_layout.addWidget(self.timeline_height_slider, 1, 0, 1, 2)

        # Connect slider and spinbox
        self.timeline_height_spin.valueChanged.connect(self.timeline_height_slider.setValue)
        self.timeline_height_slider.valueChanged.connect(self.timeline_height_spin.setValue)

        timeline_group.setLayout(timeline_layout)
        layout.addWidget(timeline_group)

        # Editor options group
        options_group = QGroupBox("Options de l'éditeur")
        options_layout = QVBoxLayout()

        self.auto_save_check = QCheckBox("Sauvegarde automatique du projet")
        self.auto_save_check.setChecked(True)
        options_layout.addWidget(self.auto_save_check)

        self.show_waveform_check = QCheckBox("Afficher les formes d'onde audio")
        self.show_waveform_check.setChecked(False)
        options_layout.addWidget(self.show_waveform_check)

        self.snap_to_marker_check = QCheckBox("Aimanter aux marqueurs")
        self.snap_to_marker_check.setChecked(True)
        options_layout.addWidget(self.snap_to_marker_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        layout.addStretch()

        return widget

    def load_current_settings(self):
        """Load current settings from theme manager."""
        if not self.current_theme:
            return

        # Find and select current theme
        theme_name = self.current_theme.name
        index = self.theme_combo.findText(theme_name)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

        # Load other settings
        self.font_size_spin.setValue(self.current_theme.font_size)
        self.timeline_height_spin.setValue(self.current_theme.timeline_height)

        # Set accent color preview
        self.update_accent_color_preview(self.current_theme.colors.primary)

        # Update theme preview
        self.on_theme_preview(theme_name)

    def on_theme_preview(self, theme_name: str):
        """Update theme preview when theme selection changes.

        Args:
            theme_name: Name of selected theme
        """
        presets = ThemePresets.get_all_presets()
        theme = presets.get(theme_name)

        if theme:
            preview_text = f"""
            <h3>{theme.name}</h3>
            <p><i>{theme.description}</i></p>
            <p style='color: {theme.colors.primary};'><b>Couleur primaire</b></p>
            <p style='color: {theme.colors.foreground};'>Texte normal</p>
            <p style='color: {theme.colors.foreground_alt};'>Texte secondaire</p>
            """
            self.theme_preview.setText(preview_text)

            # Update preview background
            self.theme_preview.setStyleSheet(f"""
                QLabel {{
                    background-color: {theme.colors.background};
                    color: {theme.colors.foreground};
                    border: 2px solid {theme.colors.border};
                    border-radius: 4px;
                    padding: 10px;
                }}
            """)

    def choose_accent_color(self):
        """Open color picker for accent color."""
        current_color = QColor(self.current_theme.colors.primary if self.current_theme else "#007acc")

        color = QColorDialog.getColor(
            current_color,
            self,
            "Choisir couleur d'accent"
        )

        if color.isValid():
            color_hex = color.name()
            self.update_accent_color_preview(color_hex)

    def update_accent_color_preview(self, color_hex: str):
        """Update accent color preview.

        Args:
            color_hex: Hex color string
        """
        self.accent_color_preview.setStyleSheet(f"""
            background-color: {color_hex};
            border: 1px solid #555;
            border-radius: 4px;
        """)
        self.accent_color_preview.setProperty("color_value", color_hex)

    def apply_settings(self):
        """Apply all settings."""
        # Get selected theme
        theme_name = self.theme_combo.currentText()
        presets = ThemePresets.get_all_presets()
        theme = presets.get(theme_name)

        if theme:
            # Update theme with custom settings
            theme.font_size = self.font_size_spin.value()
            theme.timeline_height = self.timeline_height_spin.value()

            # Update accent color if changed
            accent_color = self.accent_color_preview.property("color_value")
            if accent_color:
                theme.colors.primary = accent_color
                theme.colors.button_bg = accent_color

            # Emit signals
            self.theme_changed.emit(theme)
            self.timeline_height_changed.emit(theme.timeline_height)
            self.font_size_changed.emit(theme.font_size)

            if accent_color:
                self.accent_color_changed.emit(accent_color)

        self.accept()

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        # Reset to dark theme
        self.theme_combo.setCurrentText("Dark Mode")
        self.font_size_spin.setValue(10)
        self.timeline_height_spin.setValue(80)
        self.update_accent_color_preview("#007acc")

        # Reset editor options
        self.auto_save_check.setChecked(True)
        self.show_waveform_check.setChecked(False)
        self.snap_to_marker_check.setChecked(True)
