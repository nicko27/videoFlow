"""
Smart Test Set Generator Dialog

UI for intelligent test set generation with preview and configuration.
"""

from typing import List, Optional, Dict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QProgressDialog, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QColor

from src.core.logger import Logger
from ..services.smart_test_set_generator import SmartTestSetGenerator

logger = Logger.get_logger('DuplicateFinder.SmartTestSetDialog')


class GeneratorThread(QThread):
    """Background thread for test set generation."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, generator: SmartTestSetGenerator, video_files: List[str],
                 target_size: int, strategy: str, threshold: float, seed: Optional[int] = None):
        super().__init__()
        self.generator = generator
        self.video_files = video_files
        self.target_size = target_size
        self.strategy = strategy
        self.threshold = threshold
        self.seed = seed

    def run(self):
        """Run generation in background."""
        try:
            result = self.generator.generate_test_set(
                self.video_files,
                self.target_size,
                self.strategy,
                self.threshold,
                self.seed
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SmartTestSetGeneratorDialog(QDialog):
    """
    Dialog for smart test set generation.

    Features:
        - Strategy selection with descriptions
        - Target size configuration
        - Threshold adjustment
        - Seed for reproducibility
        - Preview generated pairs
        - Statistics display
        - One-click generation
    """

    test_set_generated = pyqtSignal(dict)  # Emits generated test set config

    def __init__(self, video_files: List[str], parent=None):
        super().__init__(parent)
        self.video_files = video_files
        self.generator = SmartTestSetGenerator()
        self.generated_result = None
        self.generator_thread = None

        self.setWindowTitle("🤖 Smart Test Set Generator")
        self.setMinimumSize(900, 700)
        self.resize(1000, 750)

        self._init_ui()
        self._update_preview()

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header = QLabel("🤖 <b>Smart Test Set Generator</b>")
        header.setStyleSheet("""
            font-size: 18px;
            padding: 15px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #667EEA, stop:1 #764BA2);
            color: white;
            border-radius: 8px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Description
        desc = QLabel(
            "Génère automatiquement des test sets équilibrés et intelligents. "
            "Choisissez une stratégie d'échantillonnage adaptée à vos besoins."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(desc)

        # Configuration section
        config_group = QGroupBox("⚙️ Configuration")
        config_layout = QVBoxLayout(config_group)

        # Source info
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel(f"📁 Fichiers sources:"))
        source_label = QLabel(f"<b>{len(self.video_files)} fichiers</b>")
        source_layout.addWidget(source_label)
        source_layout.addStretch()

        # Max pairs calculation
        max_pairs = len(self.video_files) * (len(self.video_files) - 1) // 2
        max_label = QLabel(f"📊 Paires possibles: <b>{max_pairs}</b>")
        source_layout.addWidget(max_label)

        config_layout.addLayout(source_layout)

        # Strategy selection
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("🎯 Stratégie:"))

        self.strategy_combo = QComboBox()
        strategies = SmartTestSetGenerator.get_available_strategies()
        for strategy in strategies:
            self.strategy_combo.addItem(f"{strategy['icon']} {strategy['name']}", strategy['id'])
        self.strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)
        strategy_layout.addWidget(self.strategy_combo, stretch=2)

        config_layout.addLayout(strategy_layout)

        # Strategy description
        self.strategy_desc = QLabel()
        self.strategy_desc.setWordWrap(True)
        self.strategy_desc.setStyleSheet("""
            background-color: #F0F4FF;
            padding: 10px;
            border-radius: 5px;
            border-left: 4px solid #667EEA;
        """)
        config_layout.addWidget(self.strategy_desc)

        # Target size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("📏 Nombre de paires:"))

        self.size_spin = QSpinBox()
        self.size_spin.setMinimum(1)
        self.size_spin.setMaximum(max_pairs)
        self.size_spin.setValue(min(50, max_pairs))
        self.size_spin.setSuffix(" paires")
        self.size_spin.valueChanged.connect(self._update_preview)
        size_layout.addWidget(self.size_spin, stretch=1)

        # Quick size buttons
        quick_btn_layout = QHBoxLayout()
        for label, value in [("10", 10), ("50", 50), ("100", 100), ("Max", max_pairs)]:
            btn = QPushButton(label)
            btn.setMaximumWidth(60)
            if value <= max_pairs:
                btn.clicked.connect(lambda checked, v=value: self.size_spin.setValue(v))
            else:
                btn.setEnabled(False)
            quick_btn_layout.addWidget(btn)

        size_layout.addLayout(quick_btn_layout)
        size_layout.addStretch()

        config_layout.addLayout(size_layout)

        # Threshold
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("🎚️ Seuil de classification:"))

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setMinimum(0.0)
        self.threshold_spin.setMaximum(1.0)
        self.threshold_spin.setValue(0.5)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.valueChanged.connect(self._update_preview)
        threshold_layout.addWidget(self.threshold_spin)

        threshold_layout.addWidget(QLabel("<i>(sépare duplicates/non-duplicates)</i>"))
        threshold_layout.addStretch()

        config_layout.addLayout(threshold_layout)

        # Seed for reproducibility
        seed_layout = QHBoxLayout()
        seed_layout.addWidget(QLabel("🌱 Seed (optionnel):"))

        self.seed_spin = QSpinBox()
        self.seed_spin.setMinimum(-1)
        self.seed_spin.setMaximum(999999)
        self.seed_spin.setValue(-1)
        self.seed_spin.setSpecialValueText("Aléatoire")
        seed_layout.addWidget(self.seed_spin)

        seed_layout.addWidget(QLabel("<i>(pour reproductibilité)</i>"))
        seed_layout.addStretch()

        config_layout.addLayout(seed_layout)

        layout.addWidget(config_group)

        # Preview section
        preview_group = QGroupBox("👁️ Aperçu et Statistiques")
        preview_layout = QVBoxLayout(preview_group)

        # Statistics display
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(150)
        self.stats_text.setStyleSheet("""
            QTextEdit {
                background-color: #F9F9F9;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                font-family: monospace;
            }
        """)
        preview_layout.addWidget(self.stats_text)

        layout.addWidget(preview_group)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        preview_btn = QPushButton("👁️ Prévisualiser")
        preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        preview_btn.clicked.connect(self._generate_preview)
        button_layout.addWidget(preview_btn)

        generate_btn = QPushButton("✨ Générer Test Set")
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        generate_btn.clicked.connect(self._generate_and_save)
        button_layout.addWidget(generate_btn)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        # Initialize strategy description
        self._on_strategy_changed(0)

    def _on_strategy_changed(self, index: int):
        """Handle strategy selection change."""
        strategy_id = self.strategy_combo.currentData()
        strategies = SmartTestSetGenerator.get_available_strategies()

        for strategy in strategies:
            if strategy['id'] == strategy_id:
                self.strategy_desc.setText(
                    f"<b>{strategy['name']}</b><br>"
                    f"{strategy['description']}<br>"
                    f"<i>Cas d'usage: {strategy['use_case']}</i>"
                )
                break

        self._update_preview()

    def _update_preview(self):
        """Update preview statistics without generating."""
        target_size = self.size_spin.value()
        threshold = self.threshold_spin.value()
        strategy_id = self.strategy_combo.currentData()

        # Find strategy name
        strategy_name = "Unknown"
        for strategy in SmartTestSetGenerator.get_available_strategies():
            if strategy['id'] == strategy_id:
                strategy_name = strategy['name']
                break

        # Estimate time
        estimated_seconds = target_size * 0.4
        if estimated_seconds < 60:
            time_str = f"~{int(estimated_seconds)}s"
        elif estimated_seconds < 3600:
            time_str = f"~{estimated_seconds / 60:.1f}min"
        else:
            time_str = f"~{estimated_seconds / 3600:.1f}h"

        preview_text = f"""
📊 Configuration actuelle:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Stratégie:         {strategy_name}
  Nombre de paires:  {target_size}
  Seuil:             {threshold:.2f}
  Fichiers sources:  {len(self.video_files)}

⏱️  Temps de génération estimé: {time_str}

💡 Cliquez sur "Prévisualiser" pour voir les statistiques détaillées
"""
        self.stats_text.setPlainText(preview_text)

    def _generate_preview(self):
        """Generate and show preview."""
        self._generate(preview_only=True)

    def _generate_and_save(self):
        """Generate and emit for saving."""
        self._generate(preview_only=False)

    def _generate(self, preview_only: bool = True):
        """Generate test set in background."""
        # Get parameters
        strategy_id = self.strategy_combo.currentData()
        target_size = self.size_spin.value()
        threshold = self.threshold_spin.value()
        seed = self.seed_spin.value() if self.seed_spin.value() >= 0 else None

        # Show progress dialog
        progress = QProgressDialog(
            "Génération du test set en cours...",
            "Annuler",
            0,
            0,
            self
        )
        progress.setWindowTitle("Génération")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)  # Cannot cancel
        progress.show()

        # Create and start generator thread
        self.generator_thread = GeneratorThread(
            self.generator,
            self.video_files,
            target_size,
            strategy_id,
            threshold,
            seed
        )
        self.generator_thread.finished.connect(lambda result: self._on_generation_finished(result, preview_only, progress))
        self.generator_thread.error.connect(lambda error: self._on_generation_error(error, progress))
        self.generator_thread.start()

    def _on_generation_finished(self, result: Dict, preview_only: bool, progress: QProgressDialog):
        """Handle generation completion."""
        progress.close()
        self.generated_result = result
        stats = result['stats']

        # Display statistics
        stats_text = f"""
✅ Test Set généré avec succès!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Statistiques:

  Nom:               {result['name']}
  Stratégie:         {result['strategy']}
  Nombre de paires:  {stats['total_pairs']}

  ✓ Duplicates:      {stats['duplicates']} ({stats['duplicates']/stats['total_pairs']*100:.1f}%)
  ✗ Non-duplicates:  {stats['non_duplicates']} ({stats['non_duplicates']/stats['total_pairs']*100:.1f}%)

  📈 Balance ratio:  {stats['balance_ratio']:.2f}
  📊 Similarité moy: {stats['avg_similarity']:.3f}

  Seuil utilisé:     {result['threshold']:.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Distribution par range de similarité:
"""

        for range_name, count in stats['range_distribution'].items():
            percentage = (count / stats['total_pairs'] * 100) if stats['total_pairs'] > 0 else 0
            stats_text += f"  {range_name:15s}: {count:3d} paires ({percentage:5.1f}%)\n"

        self.stats_text.setPlainText(stats_text)

        if not preview_only:
            # Emit signal with result
            self.test_set_generated.emit(result)
            self.accept()
        else:
            QMessageBox.information(
                self,
                "Prévisualisation",
                f"Prévisualisation terminée!\n\n"
                f"Le test set contiendrait {stats['total_pairs']} paires:\n"
                f"  • {stats['duplicates']} duplicates\n"
                f"  • {stats['non_duplicates']} non-duplicates\n\n"
                f"Cliquez sur 'Générer Test Set' pour créer le test set."
            )

    def _on_generation_error(self, error: str, progress: QProgressDialog):
        """Handle generation error."""
        progress.close()
        QMessageBox.critical(
            self,
            "Erreur",
            f"Erreur lors de la génération:\n\n{error}"
        )
        logger.error(f"Generation error: {error}")

    def get_result(self) -> Optional[Dict]:
        """Get generated test set result."""
        return self.generated_result

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when dialog is closed.

        Ensures proper cleanup of generator thread.
        """
        # Stop and cleanup generator thread if running
        if self.generator_thread:
            try:
                # Disconnect signals
                self.generator_thread.finished.disconnect()
                self.generator_thread.error.disconnect()
            except (RuntimeError, TypeError):
                # Signals may already be disconnected
                pass

            # Wait for thread to finish
            if self.generator_thread.isRunning():
                self.generator_thread.wait(2000)  # Wait max 2 seconds

            # Delete thread
            self.generator_thread.deleteLater()
            self.generator_thread = None

        super().closeEvent(event)
