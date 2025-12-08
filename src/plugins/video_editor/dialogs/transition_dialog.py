"""Dialog for configuring transitions between video segments."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QPushButton, QGroupBox, QGridLayout,
    QWidget, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from ..transitions import Transition, TransitionType, TransitionPreset
from src.core.i18n import t


class TransitionDialog(QDialog):
    """Dialog for configuring transition effects.

    Allows users to select transition type, duration, and preview the effect.

    Signals:
        transition_selected: Emitted when a transition is configured (Transition)
    """

    transition_selected = pyqtSignal(object)

    def __init__(self, parent=None, current_transition: Transition = None):
        """Initialize the transition dialog.

        Args:
            parent: Parent widget
            current_transition: Existing transition to edit (if any)
        """
        super().__init__(parent)
        self.current_transition = current_transition or Transition()
        self.setup_ui()
        self.load_current_transition()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(t("video_editor.dialog.transition.title", "Configure Transition"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)

        # Preset section
        preset_group = QGroupBox(t("video_editor.dialog.transition.quick_presets", "Quick Presets"))
        preset_layout = QVBoxLayout()

        self.preset_combo = QComboBox()
        self.preset_combo.addItem(t("video_editor.dialog.transition.select_preset", "-- Select Preset --"), None)
        for preset_name in TransitionPreset.get_preset_names():
            self.preset_combo.addItem(preset_name, preset_name)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_selected)
        preset_layout.addWidget(self.preset_combo)

        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        # Custom transition section
        custom_group = QGroupBox(t("video_editor.dialog.transition.custom_transition", "Custom Transition"))
        custom_layout = QGridLayout()

        # Transition type
        custom_layout.addWidget(QLabel(t("video_editor.dialog.transition.type", "Type:")), 0, 0)
        self.type_combo = QComboBox()
        for trans_type in TransitionType:
            display_name = trans_type.value.replace('_', ' ').title()
            self.type_combo.addItem(display_name, trans_type)
        self.type_combo.currentIndexChanged.connect(self.on_custom_changed)
        custom_layout.addWidget(self.type_combo, 0, 1)

        # Duration
        custom_layout.addWidget(QLabel(t("video_editor.dialog.transition.duration", "Duration (seconds):")), 1, 0)
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 5.0)
        self.duration_spin.setSingleStep(0.1)
        self.duration_spin.setValue(1.0)
        self.duration_spin.setDecimals(1)
        self.duration_spin.valueChanged.connect(self.on_custom_changed)
        custom_layout.addWidget(self.duration_spin, 1, 1)

        # Easing
        custom_layout.addWidget(QLabel(t("video_editor.dialog.transition.easing", "Easing:")), 2, 0)
        self.easing_combo = QComboBox()
        self.easing_combo.addItems(["linear", "ease-in", "ease-out", "ease-in-out"])
        self.easing_combo.currentIndexChanged.connect(self.on_custom_changed)
        custom_layout.addWidget(self.easing_combo, 2, 1)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        # Preview section
        preview_group = QGroupBox(t("video_editor.dialog.transition.preview", "Preview"))
        preview_layout = QVBoxLayout()

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(100)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                color: white;
                border: 2px solid #555;
                border-radius: 4px;
                padding: 20px;
            }
        """)
        preview_layout.addWidget(self.preview_label)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Description
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.description_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.clear_btn = QPushButton(t("video_editor.dialog.transition.no_transition", "No Transition"))
        self.clear_btn.clicked.connect(self.on_clear)
        button_layout.addWidget(self.clear_btn)

        self.cancel_btn = QPushButton(t("video_editor.dialog.transition.cancel", "Cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.apply_btn = QPushButton(t("video_editor.dialog.transition.apply", "Apply"))
        self.apply_btn.setDefault(True)
        self.apply_btn.clicked.connect(self.on_apply)
        button_layout.addWidget(self.apply_btn)

        layout.addLayout(button_layout)

        # Update preview
        self.update_preview()

    def load_current_transition(self):
        """Load the current transition into the UI."""
        if self.current_transition:
            # Find and select the transition type
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == self.current_transition.type:
                    self.type_combo.setCurrentIndex(i)
                    break

            self.duration_spin.setValue(self.current_transition.duration)

            # Set easing
            easing_index = self.easing_combo.findText(self.current_transition.easing)
            if easing_index >= 0:
                self.easing_combo.setCurrentIndex(easing_index)

            self.update_preview()

    def on_preset_selected(self, index):
        """Handle preset selection."""
        preset_name = self.preset_combo.itemData(index)
        if preset_name:
            preset = TransitionPreset.get_preset(preset_name)
            if preset:
                # Update custom controls
                for i in range(self.type_combo.count()):
                    if self.type_combo.itemData(i) == preset.type:
                        self.type_combo.setCurrentIndex(i)
                        break

                self.duration_spin.setValue(preset.duration)

                easing_index = self.easing_combo.findText(preset.easing)
                if easing_index >= 0:
                    self.easing_combo.setCurrentIndex(easing_index)

                self.update_preview()

    def on_custom_changed(self):
        """Handle custom transition changes."""
        # Reset preset combo
        self.preset_combo.setCurrentIndex(0)
        self.update_preview()

    def on_clear(self):
        """Clear the transition (set to NONE)."""
        self.type_combo.setCurrentIndex(0)  # NONE
        self.update_preview()
        self.accept()

    def on_apply(self):
        """Apply the transition."""
        transition = self.get_current_transition()
        self.transition_selected.emit(transition)
        self.accept()

    def get_current_transition(self) -> Transition:
        """Get the currently configured transition."""
        trans_type = self.type_combo.currentData()
        duration = self.duration_spin.value()
        easing = self.easing_combo.currentText()

        return Transition(
            type=trans_type,
            duration=duration,
            easing=easing
        )

    def update_preview(self):
        """Update the preview visualization."""
        transition = self.get_current_transition()

        # Create visual preview
        if transition.type == TransitionType.NONE:
            preview_text = t("video_editor.dialog.transition.preview_none",
                "┌─────┐  ┌─────┐\n│  A  │  │  B  │\n└─────┘  └─────┘\n\nNo transition - direct cut")
        elif transition.type == TransitionType.FADE:
            preview_text = t("video_editor.dialog.transition.preview_fade",
                "┌─────┐     ┌─────┐\n│  A  │ ▓▒░ │  B  │\n└─────┘     └─────┘\n\nFade ({duration}s)",
                duration=transition.duration)
        elif "WIPE" in transition.type.value.upper():
            direction = transition.type.value.split('_')[1]
            arrow = {"left": "←", "right": "→", "up": "↑", "down": "↓"}.get(direction, "→")
            preview_text = t("video_editor.dialog.transition.preview_wipe",
                "┌─────┐ {arrow}  ┌─────┐\n│  A  │ {arrow}  │  B  │\n└─────┘ {arrow}  └─────┘\n\nWipe {direction} ({duration}s)",
                arrow=arrow, direction=direction.title(), duration=transition.duration)
        elif "SLIDE" in transition.type.value.upper():
            direction = transition.type.value.split('_')[1]
            preview_text = t("video_editor.dialog.transition.preview_slide",
                "┌─────┐═══→┌─────┐\n│  A  │    │  B  │\n└─────┘    └─────┘\n\nSlide {direction} ({duration}s)",
                direction=direction.title(), duration=transition.duration)
        elif "ZOOM" in transition.type.value.upper():
            zoom_type = "in" if "IN" in transition.type.value.upper() else "out"
            symbol = "⊕" if zoom_type == "in" else "⊖"
            preview_text = t("video_editor.dialog.transition.preview_zoom",
                "┌─────┐  {symbol}  ┌─────┐\n│  A  │     │  B  │\n└─────┘     └─────┘\n\nZoom {type} ({duration}s)",
                symbol=symbol, type=zoom_type.title(), duration=transition.duration)
        else:
            preview_text = f"┌─────┐ ≈≈≈ ┌─────┐\n│  A  │     │  B  │\n└─────┘     └─────┘\n\n{transition}"

        self.preview_label.setText(preview_text)

        # Update description
        descriptions = {
            TransitionType.NONE: t("video_editor.dialog.transition.desc_none", "No transition effect. Direct cut between segments."),
            TransitionType.FADE: t("video_editor.dialog.transition.desc_fade", "Smooth cross-fade between segments. Classic and professional."),
            TransitionType.WIPE_LEFT: t("video_editor.dialog.transition.desc_wipe_left", "Second segment wipes in from right to left."),
            TransitionType.WIPE_RIGHT: t("video_editor.dialog.transition.desc_wipe_right", "Second segment wipes in from left to right."),
            TransitionType.WIPE_UP: t("video_editor.dialog.transition.desc_wipe_up", "Second segment wipes in from bottom to top."),
            TransitionType.WIPE_DOWN: t("video_editor.dialog.transition.desc_wipe_down", "Second segment wipes in from top to bottom."),
            TransitionType.SLIDE_LEFT: t("video_editor.dialog.transition.desc_slide_left", "Second segment slides in from right, pushing first segment left."),
            TransitionType.SLIDE_RIGHT: t("video_editor.dialog.transition.desc_slide_right", "Second segment slides in from left, pushing first segment right."),
            TransitionType.ZOOM_IN: t("video_editor.dialog.transition.desc_zoom_in", "Fade transition with zoom in effect."),
            TransitionType.ZOOM_OUT: t("video_editor.dialog.transition.desc_zoom_out", "Fade transition with zoom out effect."),
            TransitionType.DISSOLVE: t("video_editor.dialog.transition.desc_dissolve", "Smooth dissolve between segments.")
        }

        desc = descriptions.get(transition.type, "")
        self.description_label.setText(desc)


class QuickTransitionButton(QPushButton):
    """Quick button for applying common transitions."""

    transition_selected = pyqtSignal(object)

    def __init__(self, transition_name: str, parent=None):
        """Initialize quick transition button.

        Args:
            transition_name: Name of the preset transition
            parent: Parent widget
        """
        super().__init__(parent)
        self.transition_name = transition_name
        self.transition = TransitionPreset.get_preset(transition_name)

        # Set button text and tooltip
        self.setText(transition_name)
        if self.transition:
            self.setToolTip(f"{transition_name}: {self.transition.duration}s")

        self.clicked.connect(self.on_clicked)

    def on_clicked(self):
        """Handle button click."""
        if self.transition:
            self.transition_selected.emit(self.transition)
