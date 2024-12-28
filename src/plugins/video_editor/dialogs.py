"""Boîtes de dialogue personnalisées pour le plugin Video Editor"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                           QLabel, QComboBox, QSpinBox, QCheckBox, QGroupBox,
                           QFormLayout, QDialogButtonBox)
from PyQt6.QtCore import Qt
from .constants import VIDEO_CODECS, AUDIO_CODECS, QUALITY_PRESETS

class ExportDialog(QDialog):
    """Boîte de dialogue pour l'export de vidéo"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exporter la vidéo")
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout(self)
        
        # Préréglages
        preset_group = QGroupBox("Préréglage")
        preset_layout = QVBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Haute qualité", "Qualité moyenne", "Basse qualité"])
        preset_layout.addWidget(self.preset_combo)
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # Paramètres vidéo
        video_group = QGroupBox("Paramètres vidéo")
        video_layout = QFormLayout()
        
        self.video_codec_combo = QComboBox()
        for codec, desc in VIDEO_CODECS.items():
            self.video_codec_combo.addItem(desc, codec)
        video_layout.addRow("Codec :", self.video_codec_combo)
        
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(23)
        self.crf_spin.setToolTip("0 = sans perte, 51 = pire qualité")
        video_layout.addRow("Qualité (CRF) :", self.crf_spin)
        
        video_group.setLayout(video_layout)
        layout.addWidget(video_group)
        
        # Paramètres audio
        audio_group = QGroupBox("Paramètres audio")
        audio_layout = QFormLayout()
        
        self.audio_codec_combo = QComboBox()
        for codec, desc in AUDIO_CODECS.items():
            self.audio_codec_combo.addItem(desc, codec)
        audio_layout.addRow("Codec :", self.audio_codec_combo)
        
        self.audio_bitrate_combo = QComboBox()
        self.audio_bitrate_combo.addItems(["96k", "128k", "192k", "256k", "320k"])
        audio_layout.addRow("Bitrate :", self.audio_bitrate_combo)
        
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)
        
        # Options supplémentaires
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        self.delete_original_cb = QCheckBox("Supprimer les fichiers originaux")
        options_layout.addWidget(self.delete_original_cb)
        
        self.open_after_cb = QCheckBox("Ouvrir après l'export")
        options_layout.addWidget(self.open_after_cb)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Boutons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Connecter les signaux
        self.preset_combo.currentIndexChanged.connect(self.apply_preset)
        
        # Appliquer le préréglage initial
        self.apply_preset(0)
    
    def apply_preset(self, index):
        """Applique un préréglage de qualité"""
        presets = list(QUALITY_PRESETS.values())
        if 0 <= index < len(presets):
            preset = presets[index]
            
            # Trouver l'index du codec vidéo
            video_codec_index = self.video_codec_combo.findData(preset['video_codec'])
            if video_codec_index >= 0:
                self.video_codec_combo.setCurrentIndex(video_codec_index)
            
            # Trouver l'index du codec audio
            audio_codec_index = self.audio_codec_combo.findData(preset['audio_codec'])
            if audio_codec_index >= 0:
                self.audio_codec_combo.setCurrentIndex(audio_codec_index)
            
            # Définir le CRF
            self.crf_spin.setValue(preset['crf'])
            
            # Définir le bitrate audio
            audio_bitrate_index = self.audio_bitrate_combo.findText(
                preset['audio_bitrate']
            )
            if audio_bitrate_index >= 0:
                self.audio_bitrate_combo.setCurrentIndex(audio_bitrate_index)
    
    def get_settings(self):
        """Retourne les paramètres d'export"""
        return {
            'video_codec': self.video_codec_combo.currentData(),
            'crf': self.crf_spin.value(),
            'audio_codec': self.audio_codec_combo.currentData(),
            'audio_bitrate': self.audio_bitrate_combo.currentText(),
            'delete_original': self.delete_original_cb.isChecked(),
            'open_after': self.open_after_cb.isChecked()
        }

class SceneDetectionDialog(QDialog):
    """Boîte de dialogue pour la détection de scènes"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Détection de scènes")
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout(self)
        
        # Paramètres
        params_group = QGroupBox("Paramètres")
        params_layout = QFormLayout()
        
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 100)
        self.threshold_spin.setValue(30)
        self.threshold_spin.setToolTip("Plus la valeur est basse, plus la détection est sensible")
        params_layout.addRow("Sensibilité :", self.threshold_spin)
        
        self.min_length_spin = QSpinBox()
        self.min_length_spin.setRange(1, 100)
        self.min_length_spin.setValue(15)
        self.min_length_spin.setToolTip("Longueur minimale d'une scène en frames")
        params_layout.addRow("Longueur minimale :", self.min_length_spin)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        self.auto_name_cb = QCheckBox("Nommer automatiquement les scènes")
        self.auto_name_cb.setChecked(True)
        options_layout.addWidget(self.auto_name_cb)
        
        self.merge_short_cb = QCheckBox("Fusionner les scènes courtes")
        options_layout.addWidget(self.merge_short_cb)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Boutons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_settings(self):
        """Retourne les paramètres de détection"""
        return {
            'threshold': self.threshold_spin.value(),
            'min_length': self.min_length_spin.value(),
            'auto_name': self.auto_name_cb.isChecked(),
            'merge_short': self.merge_short_cb.isChecked()
        }
