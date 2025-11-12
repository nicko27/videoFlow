"""Audio mixer widget for Video Editor.

Provides visual audio mixing controls for segments and tracks.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QCheckBox, QPushButton, QGroupBox,
    QComboBox, QSpinBox, QDoubleSpinBox, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Optional
from .audio_mixing import (
    AudioMixingConfig, AudioFade, AudioFadeType,
    AudioEqualizer, AudioDucking, AudioFilter, AudioMixer
)


class VolumeSlider(QWidget):
    """Professional volume slider with dB markings."""

    value_changed = pyqtSignal(float)  # volume (0.0-1.0)

    def __init__(self, parent=None):
        """Initialize volume slider.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Set up slider UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        # Label
        self.label = QLabel("Volume")
        self.label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(self.label)

        # Slider (0-100)
        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setValue(100)
        self.slider.setTickPosition(QSlider.TickPosition.TicksLeft)
        self.slider.setTickInterval(20)
        self.slider.setStyleSheet("""
            QSlider::groove:vertical {
                background: #3a3a3a;
                width: 10px;
                border-radius: 5px;
            }
            QSlider::handle:vertical {
                background: #0078d4;
                height: 20px;
                margin: -5px 0;
                border-radius: 10px;
            }
            QSlider::sub-page:vertical {
                background: #0078d4;
                border-radius: 5px;
            }
        """)
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider, 1)

        # Value label
        self.value_label = QLabel("100%")
        self.value_label.setStyleSheet("color: #ccc; font-size: 11px;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)

        # dB label
        self.db_label = QLabel("0.0 dB")
        self.db_label.setStyleSheet("color: #888; font-size: 10px;")
        self.db_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.db_label)

    def _on_slider_changed(self, value: int):
        """Handle slider value change."""
        volume = value / 100.0
        self.value_changed.emit(volume)

        # Update labels
        self.value_label.setText(f"{value}%")

        # Calculate dB (20 * log10(volume))
        if volume > 0:
            import math
            db = 20 * math.log10(volume)
            self.db_label.setText(f"{db:.1f} dB")
        else:
            self.db_label.setText("-∞ dB")

    def set_volume(self, volume: float):
        """Set volume value.

        Args:
            volume: Volume (0.0-1.0)
        """
        self.slider.setValue(int(volume * 100))

    def get_volume(self) -> float:
        """Get current volume.

        Returns:
            Volume (0.0-1.0)
        """
        return self.slider.value() / 100.0


class FadeControls(QGroupBox):
    """Fade in/out controls."""

    fade_changed = pyqtSignal()

    def __init__(self, title: str = "Fade", parent=None):
        """Initialize fade controls.

        Args:
            title: Group box title
            parent: Parent widget
        """
        super().__init__(title, parent)
        self.setup_ui()

    def setup_ui(self):
        """Set up fade controls UI."""
        layout = QVBoxLayout(self)

        # Enable checkbox
        self.enable_checkbox = QCheckBox("Enable")
        self.enable_checkbox.stateChanged.connect(self.fade_changed.emit)
        layout.addWidget(self.enable_checkbox)

        # Duration
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration:"))

        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setMinimum(0.1)
        self.duration_spin.setMaximum(10.0)
        self.duration_spin.setValue(1.0)
        self.duration_spin.setSuffix(" s")
        self.duration_spin.valueChanged.connect(self.fade_changed.emit)
        duration_layout.addWidget(self.duration_spin)

        layout.addLayout(duration_layout)

        # Curve type
        curve_layout = QHBoxLayout()
        curve_layout.addWidget(QLabel("Curve:"))

        self.curve_combo = QComboBox()
        self.curve_combo.addItem("Linear", AudioFadeType.LINEAR)
        self.curve_combo.addItem("Exponential", AudioFadeType.EXPONENTIAL)
        self.curve_combo.addItem("Logarithmic", AudioFadeType.LOGARITHMIC)
        self.curve_combo.addItem("S-Curve", AudioFadeType.S_CURVE)
        self.curve_combo.currentIndexChanged.connect(self.fade_changed.emit)
        curve_layout.addWidget(self.curve_combo)

        layout.addLayout(curve_layout)

    def get_fade(self, fade_type: str) -> Optional[AudioFade]:
        """Get fade configuration.

        Args:
            fade_type: "in" or "out"

        Returns:
            AudioFade if enabled, None otherwise
        """
        if not self.enable_checkbox.isChecked():
            return None

        return AudioFade(
            fade_type=fade_type,
            duration=self.duration_spin.value(),
            curve=self.curve_combo.currentData()
        )

    def set_fade(self, fade: Optional[AudioFade]):
        """Set fade configuration.

        Args:
            fade: Fade configuration or None
        """
        if fade is None:
            self.enable_checkbox.setChecked(False)
            return

        self.enable_checkbox.setChecked(True)
        self.duration_spin.setValue(fade.duration)

        # Find curve index
        for i in range(self.curve_combo.count()):
            if self.curve_combo.itemData(i) == fade.curve:
                self.curve_combo.setCurrentIndex(i)
                break


class EqualizerControls(QGroupBox):
    """3-band equalizer controls."""

    eq_changed = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize equalizer controls.

        Args:
            parent: Parent widget
        """
        super().__init__("Equalizer", parent)
        self.setup_ui()

    def setup_ui(self):
        """Set up EQ controls UI."""
        layout = QVBoxLayout(self)

        # Enable checkbox
        self.enable_checkbox = QCheckBox("Enable")
        self.enable_checkbox.stateChanged.connect(self.eq_changed.emit)
        layout.addWidget(self.enable_checkbox)

        # Low band
        low_layout = QHBoxLayout()
        low_layout.addWidget(QLabel("Low (100Hz):"))

        self.low_spin = QDoubleSpinBox()
        self.low_spin.setMinimum(-20.0)
        self.low_spin.setMaximum(20.0)
        self.low_spin.setValue(0.0)
        self.low_spin.setSuffix(" dB")
        self.low_spin.valueChanged.connect(self.eq_changed.emit)
        low_layout.addWidget(self.low_spin)

        layout.addLayout(low_layout)

        # Mid band
        mid_layout = QHBoxLayout()
        mid_layout.addWidget(QLabel("Mid (1kHz):"))

        self.mid_spin = QDoubleSpinBox()
        self.mid_spin.setMinimum(-20.0)
        self.mid_spin.setMaximum(20.0)
        self.mid_spin.setValue(0.0)
        self.mid_spin.setSuffix(" dB")
        self.mid_spin.valueChanged.connect(self.eq_changed.emit)
        mid_layout.addWidget(self.mid_spin)

        layout.addLayout(mid_layout)

        # High band
        high_layout = QHBoxLayout()
        high_layout.addWidget(QLabel("High (8kHz):"))

        self.high_spin = QDoubleSpinBox()
        self.high_spin.setMinimum(-20.0)
        self.high_spin.setMaximum(20.0)
        self.high_spin.setValue(0.0)
        self.high_spin.setSuffix(" dB")
        self.high_spin.valueChanged.connect(self.eq_changed.emit)
        high_layout.addWidget(self.high_spin)

        layout.addLayout(high_layout)

    def get_equalizer(self) -> Optional[AudioEqualizer]:
        """Get equalizer configuration.

        Returns:
            AudioEqualizer if enabled, None otherwise
        """
        if not self.enable_checkbox.isChecked():
            return None

        return AudioEqualizer(
            enabled=True,
            low_gain=self.low_spin.value(),
            mid_gain=self.mid_spin.value(),
            high_gain=self.high_spin.value()
        )

    def set_equalizer(self, eq: Optional[AudioEqualizer]):
        """Set equalizer configuration.

        Args:
            eq: Equalizer configuration or None
        """
        if eq is None or not eq.enabled:
            self.enable_checkbox.setChecked(False)
            return

        self.enable_checkbox.setChecked(True)
        self.low_spin.setValue(eq.low_gain)
        self.mid_spin.setValue(eq.mid_gain)
        self.high_spin.setValue(eq.high_gain)


class AudioMixerWidget(QWidget):
    """Complete audio mixer widget for segment."""

    config_changed = pyqtSignal(AudioMixingConfig)

    def __init__(self, parent=None):
        """Initialize audio mixer widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.config = AudioMixingConfig()
        self.setup_ui()

    def setup_ui(self):
        """Set up mixer UI."""
        main_layout = QHBoxLayout(self)

        # Left side: Volume fader
        self.volume_slider = VolumeSlider()
        self.volume_slider.value_changed.connect(self._on_volume_changed)
        main_layout.addWidget(self.volume_slider)

        # Right side: Tabs with controls
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                background-color: #2a2a2a;
                border: 1px solid #444;
            }
            QTabBar::tab {
                background-color: #3a3a3a;
                color: white;
                padding: 8px 16px;
                border: 1px solid #444;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
            }
        """)

        # Basic tab
        basic_tab = self._create_basic_tab()
        tabs.addTab(basic_tab, "Basic")

        # Fade tab
        fade_tab = self._create_fade_tab()
        tabs.addTab(fade_tab, "Fade")

        # EQ tab
        eq_tab = self._create_eq_tab()
        tabs.addTab(eq_tab, "EQ")

        # Effects tab
        effects_tab = self._create_effects_tab()
        tabs.addTab(effects_tab, "Effects")

        main_layout.addWidget(tabs, 1)

    def _create_basic_tab(self) -> QWidget:
        """Create basic controls tab.

        Returns:
            Tab widget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Mute checkbox
        self.mute_checkbox = QCheckBox("Mute")
        self.mute_checkbox.stateChanged.connect(self._emit_config_changed)
        layout.addWidget(self.mute_checkbox)

        # Normalize checkbox
        self.normalize_checkbox = QCheckBox("Normalize Audio")
        self.normalize_checkbox.stateChanged.connect(self._emit_config_changed)
        layout.addWidget(self.normalize_checkbox)

        # Presets
        presets_group = QGroupBox("Presets")
        presets_layout = QVBoxLayout(presets_group)

        music_btn = QPushButton("Background Music")
        music_btn.clicked.connect(lambda: self.set_config(AudioMixer.create_standard_music_mix()))
        presets_layout.addWidget(music_btn)

        dialogue_btn = QPushButton("Dialogue")
        dialogue_btn.clicked.connect(lambda: self.set_config(AudioMixer.create_dialogue_mix()))
        presets_layout.addWidget(dialogue_btn)

        sfx_btn = QPushButton("Sound Effects")
        sfx_btn.clicked.connect(lambda: self.set_config(AudioMixer.create_sfx_mix()))
        presets_layout.addWidget(sfx_btn)

        layout.addWidget(presets_group)

        layout.addStretch()
        return widget

    def _create_fade_tab(self) -> QWidget:
        """Create fade controls tab.

        Returns:
            Tab widget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Fade in
        self.fade_in_controls = FadeControls("Fade In")
        self.fade_in_controls.fade_changed.connect(self._emit_config_changed)
        layout.addWidget(self.fade_in_controls)

        # Fade out
        self.fade_out_controls = FadeControls("Fade Out")
        self.fade_out_controls.fade_changed.connect(self._emit_config_changed)
        layout.addWidget(self.fade_out_controls)

        layout.addStretch()
        return widget

    def _create_eq_tab(self) -> QWidget:
        """Create equalizer tab.

        Returns:
            Tab widget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.eq_controls = EqualizerControls()
        self.eq_controls.eq_changed.connect(self._emit_config_changed)
        layout.addWidget(self.eq_controls)

        layout.addStretch()
        return widget

    def _create_effects_tab(self) -> QWidget:
        """Create effects tab.

        Returns:
            Tab widget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        effects_group = QGroupBox("Audio Effects")
        effects_layout = QVBoxLayout(effects_group)

        # Compressor
        self.compressor_checkbox = QCheckBox("Compressor")
        self.compressor_checkbox.stateChanged.connect(self._emit_config_changed)
        effects_layout.addWidget(self.compressor_checkbox)

        # Noise reduction
        self.noise_reduction_checkbox = QCheckBox("Noise Reduction")
        self.noise_reduction_checkbox.stateChanged.connect(self._emit_config_changed)
        effects_layout.addWidget(self.noise_reduction_checkbox)

        # High-pass filter
        self.highpass_checkbox = QCheckBox("High-Pass Filter (80Hz)")
        self.highpass_checkbox.stateChanged.connect(self._emit_config_changed)
        effects_layout.addWidget(self.highpass_checkbox)

        # Low-pass filter
        self.lowpass_checkbox = QCheckBox("Low-Pass Filter (10kHz)")
        self.lowpass_checkbox.stateChanged.connect(self._emit_config_changed)
        effects_layout.addWidget(self.lowpass_checkbox)

        layout.addWidget(effects_group)
        layout.addStretch()
        return widget

    def _on_volume_changed(self, volume: float):
        """Handle volume change."""
        self.config.volume = volume
        self._emit_config_changed()

    def _emit_config_changed(self):
        """Update config and emit signal."""
        # Update config from UI
        self.config.volume = self.volume_slider.get_volume()
        self.config.muted = self.mute_checkbox.isChecked()
        self.config.normalize = self.normalize_checkbox.isChecked()

        self.config.fade_in = self.fade_in_controls.get_fade("in")
        self.config.fade_out = self.fade_out_controls.get_fade("out")

        self.config.equalizer = self.eq_controls.get_equalizer()

        # Collect filters
        self.config.filters = []
        if self.compressor_checkbox.isChecked():
            self.config.filters.append(AudioFilter.COMPRESSOR)
        if self.noise_reduction_checkbox.isChecked():
            self.config.filters.append(AudioFilter.NOISE_REDUCTION)
        if self.highpass_checkbox.isChecked():
            self.config.filters.append(AudioFilter.HIGHPASS)
        if self.lowpass_checkbox.isChecked():
            self.config.filters.append(AudioFilter.LOWPASS)

        self.config_changed.emit(self.config)

    def get_config(self) -> AudioMixingConfig:
        """Get current audio mixing configuration.

        Returns:
            AudioMixingConfig
        """
        return self.config

    def set_config(self, config: AudioMixingConfig):
        """Set audio mixing configuration.

        Args:
            config: Audio mixing configuration
        """
        self.config = config

        # Update UI
        self.volume_slider.set_volume(config.volume)
        self.mute_checkbox.setChecked(config.muted)
        self.normalize_checkbox.setChecked(config.normalize)

        self.fade_in_controls.set_fade(config.fade_in)
        self.fade_out_controls.set_fade(config.fade_out)

        self.eq_controls.set_equalizer(config.equalizer)

        # Update effects checkboxes
        self.compressor_checkbox.setChecked(AudioFilter.COMPRESSOR in config.filters)
        self.noise_reduction_checkbox.setChecked(AudioFilter.NOISE_REDUCTION in config.filters)
        self.highpass_checkbox.setChecked(AudioFilter.HIGHPASS in config.filters)
        self.lowpass_checkbox.setChecked(AudioFilter.LOWPASS in config.filters)
