"""Interface simplifiée pour utilisateurs débutants."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox,
    QLabel, QSpinBox, QPushButton, QFormLayout, QSlider,
    QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from src.core.logger import Logger
from src.core.i18n import t

logger = Logger.get_logger('VideoConverter.SimpleView')


class SimpleCompressorView(QWidget):
    """
    Interface simplifiée type "Video Compressor" original.

    3 modes simples:
    - Target Quality (CRF fixe)
    - Target Size (compression itérative)
    - Balanced (CRF auto selon résolution)
    """

    settings_changed = pyqtSignal()  # Signal de modification

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Configure l'interface simple."""
        layout = QVBoxLayout(self)

        # === En-tête ===
        header_label = QLabel(t("simple_view.header", "🎬 Simple Video Compression"))
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(header_label)

        # === Stratégie de Compression ===
        strategy_group = QGroupBox(t("simple_view.strategy.title", "Compression Strategy"))
        strategy_layout = QVBoxLayout()

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            t("simple_view.strategy.quality", "🎯 Target Quality (Fixed quality)"),
            t("simple_view.strategy.size", "💾 Target Size (Target size)"),
            t("simple_view.strategy.balanced", "⚖️ Balanced (Auto)")
        ])
        self.strategy_combo.setCurrentIndex(2)  # Balanced par défaut
        self.strategy_combo.currentIndexChanged.connect(self.on_strategy_changed)
        strategy_layout.addWidget(self.strategy_combo)

        # Description de la stratégie
        self.strategy_description = QLabel()
        self.strategy_description.setWordWrap(True)
        self.strategy_description.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        strategy_layout.addWidget(self.strategy_description)

        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)

        # === Paramètres de Qualité (Target Quality) ===
        self.quality_group = QGroupBox(t("simple_view.quality.title", "Quality Settings"))
        quality_layout = QFormLayout()

        # CRF Slider
        crf_widget = QWidget()
        crf_layout = QHBoxLayout(crf_widget)

        self.crf_slider = QSlider(Qt.Orientation.Horizontal)
        self.crf_slider.setRange(18, 35)
        self.crf_slider.setValue(23)
        self.crf_slider.valueChanged.connect(self.update_crf_label)
        crf_layout.addWidget(self.crf_slider)

        self.crf_label = QLabel("23")
        self.crf_label.setStyleSheet("font-weight: bold; min-width: 30px;")
        crf_layout.addWidget(self.crf_label)

        quality_layout.addRow(t("simple_view.quality.crf", "CRF (Quality):"), crf_widget)

        # Info qualité
        quality_info = QLabel(t("simple_view.quality.info", "18 = High quality, 35 = High compression"))
        quality_info.setStyleSheet("color: #666; font-size: 11px;")
        quality_layout.addRow("", quality_info)

        self.quality_group.setLayout(quality_layout)
        layout.addWidget(self.quality_group)

        # === Paramètres de Taille (Target Size) ===
        self.size_group = QGroupBox(t("simple_view.size.title", "Target Size Settings"))
        size_layout = QFormLayout()

        # Taille cible
        self.target_size_spin = QSpinBox()
        self.target_size_spin.setRange(10, 10000)
        self.target_size_spin.setValue(300)
        self.target_size_spin.setSuffix(" MB")
        size_layout.addRow(t("simple_view.size.target", "Target size:"), self.target_size_spin)

        # Max tentatives
        self.max_attempts_spin = QSpinBox()
        self.max_attempts_spin.setRange(1, 10)
        self.max_attempts_spin.setValue(5)
        size_layout.addRow(t("simple_view.size.max_attempts", "Max attempts:"), self.max_attempts_spin)

        self.size_group.setLayout(size_layout)
        layout.addWidget(self.size_group)

        # === Paramètres Balanced (Auto) ===
        self.balanced_group = QGroupBox(t("simple_view.balanced.title", "Balanced Settings"))
        balanced_layout = QFormLayout()

        # Facteur qualité
        quality_factor_widget = QWidget()
        qf_layout = QHBoxLayout(quality_factor_widget)

        self.quality_factor_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_factor_slider.setRange(50, 200)  # 0.5x à 2.0x
        self.quality_factor_slider.setValue(100)  # 1.0x
        self.quality_factor_slider.valueChanged.connect(self.update_quality_factor_label)
        qf_layout.addWidget(self.quality_factor_slider)

        self.quality_factor_label = QLabel("1.0x")
        self.quality_factor_label.setStyleSheet("font-weight: bold; min-width: 50px;")
        qf_layout.addWidget(self.quality_factor_label)

        balanced_layout.addRow(t("simple_view.balanced.factor", "Quality factor:"), quality_factor_widget)

        # Info
        balanced_info = QLabel(
            t(
                "simple_view.balanced.info",
                "< 1.0 = Better quality\n"
                "1.0 = Balanced\n"
                "> 1.0 = More compression"
            )
        )
        balanced_info.setStyleSheet("color: #666; font-size: 11px;")
        balanced_layout.addRow("", balanced_info)

        self.balanced_group.setLayout(balanced_layout)
        layout.addWidget(self.balanced_group)

        # === Paramètres Communs ===
        common_group = QGroupBox(t("simple_view.common.title", "Common Settings"))
        common_layout = QFormLayout()

        # Preset
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "ultrafast", "superfast", "veryfast", "faster",
            "fast", "medium", "slow", "slower", "veryslow"
        ])
        self.preset_combo.setCurrentText("medium")
        common_layout.addRow(t("simple_view.common.preset", "Encoding speed:"), self.preset_combo)

        # Audio copy
        self.audio_copy_check = QCheckBox(t("simple_view.common.audio_copy", "Copy audio without re-encoding"))
        self.audio_copy_check.setChecked(True)
        common_layout.addRow("", self.audio_copy_check)

        common_group.setLayout(common_layout)
        layout.addWidget(common_group)

        # === Bouton Appliquer ===
        apply_layout = QHBoxLayout()
        apply_layout.addStretch()

        apply_btn = QPushButton(t("simple_view.apply", "✅ Apply Settings"))
        apply_btn.clicked.connect(self.apply_settings)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        apply_layout.addWidget(apply_btn)

        layout.addLayout(apply_layout)

        # Initialiser visibilité
        self.on_strategy_changed(2)  # Balanced par défaut

        layout.addStretch()

    def on_strategy_changed(self, index):
        """Callback changement de stratégie."""
        strategies = {
            0: {  # Target Quality
                'quality': True,
                'size': False,
                'balanced': False,
                'description': t(
                    "simple_view.strategy.desc.quality",
                    "Compress with a constant CRF (fixed quality). Output size will vary."
                )
            },
            1: {  # Target Size
                'quality': False,
                'size': True,
                'balanced': False,
                'description': t(
                    "simple_view.strategy.desc.size",
                    "Iterative compression until the output file is below the chosen target size."
                )
            },
            2: {  # Balanced
                'quality': False,
                'size': False,
                'balanced': True,
                'description': t(
                    "simple_view.strategy.desc.balanced",
                    "Auto-choose a CRF based on video resolution for a balanced result."
                )
            }
        }

        config = strategies[index]

        # Afficher/masquer groupes
        self.quality_group.setVisible(config['quality'])
        self.size_group.setVisible(config['size'])
        self.balanced_group.setVisible(config['balanced'])

        # Mettre à jour description
        self.strategy_description.setText(config['description'])

    def update_crf_label(self, value):
        """Met à jour le label CRF."""
        self.crf_label.setText(str(value))

    def update_quality_factor_label(self, value):
        """Met à jour le label facteur qualité."""
        factor = value / 100.0
        self.quality_factor_label.setText(f"{factor:.1f}x")

    def load_settings(self):
        """Charge les paramètres depuis settings."""
        # Stratégie
        strategy_map = {
            'quality': 0,
            'size': 1,
            'balanced': 2
        }
        simple_strategy = getattr(self.settings, 'simple_strategy', 'balanced')
        strategy_index = strategy_map.get(simple_strategy, 2)
        self.strategy_combo.setCurrentIndex(strategy_index)

        # Qualité
        self.crf_slider.setValue(self.settings.crf)

        # Taille
        target_mb = int(getattr(self.settings, 'target_size', 300 * 1024 * 1024) / (1024 * 1024))
        self.target_size_spin.setValue(target_mb)
        max_attempts = getattr(self.settings, 'max_compression_attempts', 5)
        self.max_attempts_spin.setValue(max_attempts)

        # Balanced
        quality_factor = getattr(self.settings, 'balanced_quality_factor', 1.0)
        factor_percent = int(quality_factor * 100)
        self.quality_factor_slider.setValue(factor_percent)

        # Commun
        self.preset_combo.setCurrentText(self.settings.preset)
        audio_copy = getattr(self.settings, 'audio_copy', True)
        self.audio_copy_check.setChecked(audio_copy)

    def apply_settings(self):
        """Applique les paramètres au settings."""
        # Stratégie
        strategy_map = {0: 'quality', 1: 'size', 2: 'balanced'}
        strategy = strategy_map[self.strategy_combo.currentIndex()]

        self.settings.simple_mode = True
        self.settings.simple_strategy = strategy

        # Selon la stratégie, configurer les bons paramètres
        if strategy == 'quality':
            # CRF fixe → manual_mode
            self.settings.manual_mode = True
            self.settings.crf = self.crf_slider.value()
            self.settings.use_target_size = False

        elif strategy == 'size':
            # Taille cible → mode itératif
            self.settings.manual_mode = False
            self.settings.use_target_size = True
            self.settings.target_size = self.target_size_spin.value() * 1024 * 1024
            self.settings.max_compression_attempts = self.max_attempts_spin.value()

        elif strategy == 'balanced':
            # CRF auto → sera calculé dans converter.py
            self.settings.manual_mode = True
            self.settings.balanced_auto_crf = True
            self.settings.balanced_quality_factor = self.quality_factor_slider.value() / 100.0
            self.settings.use_target_size = False

        # Commun
        self.settings.preset = self.preset_combo.currentText()
        self.settings.audio_copy = self.audio_copy_check.isChecked()

        # Sauvegarder
        from ..settings import SettingsManager
        SettingsManager.save_settings(self.settings)

        # Signal
        self.settings_changed.emit()

        logger.info(f"Paramètres simple appliqués: {strategy}")
