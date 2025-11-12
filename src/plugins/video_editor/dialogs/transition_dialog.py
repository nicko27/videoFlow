"""Dialog for configuring transitions between video segments."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QPushButton, QGroupBox, QGridLayout,
    QWidget, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from ..transitions import Transition, TransitionType, TransitionPreset


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
        self.setWindowTitle("Configure Transition")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)

        # Preset section
        preset_group = QGroupBox("Quick Presets")
        preset_layout = QVBoxLayout()

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("-- Select Preset --", None)
        for preset_name in TransitionPreset.get_preset_names():
            self.preset_combo.addItem(preset_name, preset_name)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_selected)
        preset_layout.addWidget(self.preset_combo)

        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        # Custom transition section
        custom_group = QGroupBox("Custom Transition")
        custom_layout = QGridLayout()

        # Transition type
        custom_layout.addWidget(QLabel("Type:"), 0, 0)
        self.type_combo = QComboBox()
        for trans_type in TransitionType:
            display_name = trans_type.value.replace('_', ' ').title()
            self.type_combo.addItem(display_name, trans_type)
        self.type_combo.currentIndexChanged.connect(self.on_custom_changed)
        custom_layout.addWidget(self.type_combo, 0, 1)

        # Duration
        custom_layout.addWidget(QLabel("Duration (seconds):"), 1, 0)
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 5.0)
        self.duration_spin.setSingleStep(0.1)
        self.duration_spin.setValue(1.0)
        self.duration_spin.setDecimals(1)
        self.duration_spin.valueChanged.connect(self.on_custom_changed)
        custom_layout.addWidget(self.duration_spin, 1, 1)

        # Easing
        custom_layout.addWidget(QLabel("Easing:"), 2, 0)
        self.easing_combo = QComboBox()
        self.easing_combo.addItems(["linear", "ease-in", "ease-out", "ease-in-out"])
        self.easing_combo.currentIndexChanged.connect(self.on_custom_changed)
        custom_layout.addWidget(self.easing_combo, 2, 1)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        # Preview section
        preview_group = QGroupBox("Preview")
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

        self.clear_btn = QPushButton("No Transition")
        self.clear_btn.clicked.connect(self.on_clear)
        button_layout.addWidget(self.clear_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.apply_btn = QPushButton("Apply")
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
            preview_text = "┌─────┐  ┌─────┐\n│  A  │  │  B  │\n└─────┘  └─────┘\n\nNo transition - direct cut"
        elif transition.type == TransitionType.FADE:
            preview_text = f"┌─────┐     ┌─────┐\n│  A  │ ▓▒░ │  B  │\n└─────┘     └─────┘\n\nFade ({transition.duration}s)"
        elif "WIPE" in transition.type.value.upper():
            direction = transition.type.value.split('_')[1]
            arrow = {"left": "←", "right": "→", "up": "↑", "down": "↓"}.get(direction, "→")
            preview_text = f"┌─────┐ {arrow}  ┌─────┐\n│  A  │ {arrow}  │  B  │\n└─────┘ {arrow}  └─────┘\n\nWipe {direction.title()} ({transition.duration}s)"
        elif "SLIDE" in transition.type.value.upper():
            direction = transition.type.value.split('_')[1]
            preview_text = f"┌─────┐═══→┌─────┐\n│  A  │    │  B  │\n└─────┘    └─────┘\n\nSlide {direction.title()} ({transition.duration}s)"
        elif "ZOOM" in transition.type.value.upper():
            zoom_type = "in" if "IN" in transition.type.value.upper() else "out"
            symbol = "⊕" if zoom_type == "in" else "⊖"
            preview_text = f"┌─────┐  {symbol}  ┌─────┐\n│  A  │     │  B  │\n└─────┘     └─────┘\n\nZoom {zoom_type.title()} ({transition.duration}s)"
        else:
            preview_text = f"┌─────┐ ≈≈≈ ┌─────┐\n│  A  │     │  B  │\n└─────┘     └─────┘\n\n{transition}"

        self.preview_label.setText(preview_text)

        # Update description
        descriptions = {
            TransitionType.NONE: "No transition effect. Direct cut between segments.",
            TransitionType.FADE: "Smooth cross-fade between segments. Classic and professional.",
            TransitionType.WIPE_LEFT: "Second segment wipes in from right to left.",
            TransitionType.WIPE_RIGHT: "Second segment wipes in from left to right.",
            TransitionType.WIPE_UP: "Second segment wipes in from bottom to top.",
            TransitionType.WIPE_DOWN: "Second segment wipes in from top to bottom.",
            TransitionType.SLIDE_LEFT: "Second segment slides in from right, pushing first segment left.",
            TransitionType.SLIDE_RIGHT: "Second segment slides in from left, pushing first segment right.",
            TransitionType.ZOOM_IN: "Fade transition with zoom in effect.",
            TransitionType.ZOOM_OUT: "Fade transition with zoom out effect.",
            TransitionType.DISSOLVE: "Smooth dissolve between segments."
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
