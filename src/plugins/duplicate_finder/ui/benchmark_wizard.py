"""
Benchmark Wizard - Interactive assistant for creating and running benchmarks.

Guides users through a 4-step process with contextual help and smart defaults.
"""

from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QWidget, QComboBox, QListWidget, QListWidgetItem,
    QGroupBox, QRadioButton, QButtonGroup, QCheckBox, QSpinBox,
    QDoubleSpinBox, QTextEdit, QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from src.core.logger import Logger
from ..services.benchmark_manager import BenchmarkManager
from ..orchestration.pipeline_manager import PipelineManager
from ..services.test_set_manager import TestSetManager
from .benchmark_widgets import BenchmarkPresets

logger = Logger.get_logger('DuplicateFinder.BenchmarkWizard')


class BenchmarkWizard(QDialog):
    """
    Interactive wizard for creating and running benchmarks.

    4 Steps:
        1. Objective: What are you testing? (Quick test, Validation, Regression)
        2. Test Set: Select or create test data
        3. Pipelines: Choose which pipelines to test
        4. Advanced: Set thresholds and export options

    Features:
        - Smart defaults based on objective
        - Contextual help and tips
        - Estimated time display
        - Validation before proceeding
        - Progress indicator
    """

    benchmark_started = pyqtSignal(dict)  # Emits config when benchmark starts

    def __init__(self, benchmark_manager: BenchmarkManager,
                 pipeline_manager: PipelineManager,
                 test_set_manager: TestSetManager,
                 parent=None):
        super().__init__(parent)
        self.benchmark_manager = benchmark_manager
        self.pipeline_manager = pipeline_manager
        self.test_set_manager = test_set_manager

        self.current_step = 0
        self.config = {}

        self.setWindowTitle("🧙 Benchmark Wizard")
        self.setMinimumSize(700, 600)
        self._init_ui()

    def _init_ui(self):
        """Initialize wizard UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header = QLabel("🧙 <b>Benchmark Assistant</b>")
        header.setStyleSheet("""
            QLabel {
                font-size: 18px;
                padding: 15px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2196F3, stop:1 #1976D2);
                color: white;
                border-radius: 5px;
            }
        """)
        layout.addWidget(header)

        # Progress indicator
        progress_container = QWidget()
        progress_layout = QHBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)

        self.step_labels = []
        steps = ["1. Objectif", "2. Test Set", "3. Pipelines", "4. Avancé"]

        for i, step in enumerate(steps):
            step_label = QLabel(step)
            step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_label.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    background-color: #E0E0E0;
                    color: #666;
                    border-radius: 4px;
                    font-size: 11px;
                }
            """)
            self.step_labels.append(step_label)
            progress_layout.addWidget(step_label)

        layout.addWidget(progress_container)

        # Stacked widget for steps
        self.stacked_widget = QStackedWidget()

        # Create step pages
        self.stacked_widget.addWidget(self._create_step1_objective())
        self.stacked_widget.addWidget(self._create_step2_testset())
        self.stacked_widget.addWidget(self._create_step3_pipelines())
        self.stacked_widget.addWidget(self._create_step4_advanced())

        layout.addWidget(self.stacked_widget, stretch=1)

        # Navigation buttons
        nav_layout = QHBoxLayout()

        self.back_btn = QPushButton("⬅️ Précédent")
        self.back_btn.clicked.connect(self._on_back)
        self.back_btn.setEnabled(False)
        nav_layout.addWidget(self.back_btn)

        nav_layout.addStretch()

        # Estimated time label
        self.time_estimate_label = QLabel("Temps estimé: Calculer...")
        self.time_estimate_label.setStyleSheet("color: #666; font-size: 11px;")
        nav_layout.addWidget(self.time_estimate_label)

        nav_layout.addStretch()

        self.cancel_btn = QPushButton("❌ Annuler")
        self.cancel_btn.clicked.connect(self.reject)
        nav_layout.addWidget(self.cancel_btn)

        self.next_btn = QPushButton("Suivant ➡️")
        self.next_btn.clicked.connect(self._on_next)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        nav_layout.addWidget(self.next_btn)

        layout.addLayout(nav_layout)

        self._update_step_indicator()

    def _create_step1_objective(self) -> QWidget:
        """Step 1: Choose objective."""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("<b>Étape 1: Quel est votre objectif ?</b>")
        title.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(title)

        # Objective selection
        self.objective_group = QButtonGroup(self)

        objectives = [
            ("quick", "⚡ Test Rapide", "Validation rapide avec quelques paires (~30s)"),
            ("validation", "✅ Validation Complète", "Test approfondi de la précision (~30min)"),
            ("regression", "📊 Test de Régression", "Vérifier qu'il n'y a pas de dégradation (~5min)"),
            ("stress", "🚀 Test de Stress", "Test exhaustif de tous les scénarios (2h+)")
        ]

        for obj_id, name, description in objectives:
            radio = QRadioButton(name)
            radio.setProperty("objective_id", obj_id)
            self.objective_group.addButton(radio)

            container = QGroupBox()
            container.setStyleSheet("""
                QGroupBox {
                    border: 2px solid #E0E0E0;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding: 15px;
                }
                QGroupBox:hover {
                    border-color: #2196F3;
                }
            """)

            obj_layout = QVBoxLayout(container)
            obj_layout.addWidget(radio)

            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666; font-size: 11px; margin-left: 25px;")
            obj_layout.addWidget(desc_label)

            layout.addWidget(container)

        # Set default
        self.objective_group.buttons()[0].setChecked(True)

        layout.addStretch()

        return page

    def _create_step2_testset(self) -> QWidget:
        """Step 2: Select test set."""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("<b>Étape 2: Sélectionnez les données de test</b>")
        title.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(title)

        # Test set selection
        test_sets_group = QGroupBox("📋 Test Sets Disponibles")
        test_sets_layout = QVBoxLayout()

        self.test_set_list = QListWidget()
        self.test_set_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        test_sets_layout.addWidget(self.test_set_list)

        # Load test sets
        self._load_test_sets()

        # Buttons
        btn_layout = QHBoxLayout()
        create_btn = QPushButton("➕ Créer Nouveau Test Set")
        create_btn.clicked.connect(self._on_create_test_set)
        btn_layout.addWidget(create_btn)

        btn_layout.addStretch()

        test_sets_layout.addLayout(btn_layout)
        test_sets_group.setLayout(test_sets_layout)
        layout.addWidget(test_sets_group)

        # Info about selected test set
        self.test_set_info = QTextEdit()
        self.test_set_info.setReadOnly(True)
        self.test_set_info.setMaximumHeight(100)
        self.test_set_info.setPlaceholderText("Sélectionnez un test set pour voir les détails...")
        layout.addWidget(self.test_set_info)

        self.test_set_list.currentItemChanged.connect(self._on_test_set_selected)

        return page

    def _create_step3_pipelines(self) -> QWidget:
        """Step 3: Select pipelines."""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("<b>Étape 3: Choisissez les pipelines à tester</b>")
        title.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(title)

        # Quick preset selection
        preset_group = QGroupBox("🎯 Préréglages Rapides")
        preset_layout = QHBoxLayout()

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("-- Sélection manuelle --", None)
        for preset in BenchmarkPresets.get_all_modes():
            self.preset_combo.addItem(f"{preset['icon']} {preset['name']}", preset)

        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        preset_layout.addWidget(QLabel("Preset:"))
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()

        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        # Pipeline list
        pipelines_group = QGroupBox("🔧 Pipelines Disponibles")
        pipelines_layout = QVBoxLayout()

        self.pipeline_list = QListWidget()
        self.pipeline_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        pipelines_layout.addWidget(self.pipeline_list)

        # Load pipelines
        self._load_pipelines()

        pipelines_group.setLayout(pipelines_layout)
        layout.addWidget(pipelines_group)

        # Selected count
        self.pipeline_count_label = QLabel("Pipelines sélectionnés: 0")
        self.pipeline_count_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        layout.addWidget(self.pipeline_count_label)

        self.pipeline_list.itemSelectionChanged.connect(self._update_pipeline_count)

        return page

    def _create_step4_advanced(self) -> QWidget:
        """Step 4: Advanced options."""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("<b>Étape 4: Options Avancées (Optionnel)</b>")
        title.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(title)

        # Thresholds
        thresholds_group = QGroupBox("🎯 Seuils de Qualité")
        thresholds_layout = QVBoxLayout()

        # F1 threshold
        f1_layout = QHBoxLayout()
        f1_layout.addWidget(QLabel("F1 Score minimum:"))
        self.f1_threshold = QDoubleSpinBox()
        self.f1_threshold.setRange(0.0, 1.0)
        self.f1_threshold.setSingleStep(0.05)
        self.f1_threshold.setValue(0.80)
        self.f1_threshold.setDecimals(2)
        f1_layout.addWidget(self.f1_threshold)
        f1_layout.addStretch()
        thresholds_layout.addLayout(f1_layout)

        # Precision threshold
        prec_layout = QHBoxLayout()
        prec_layout.addWidget(QLabel("Précision minimum:"))
        self.precision_threshold = QDoubleSpinBox()
        self.precision_threshold.setRange(0.0, 1.0)
        self.precision_threshold.setSingleStep(0.05)
        self.precision_threshold.setValue(0.70)
        self.precision_threshold.setDecimals(2)
        prec_layout.addWidget(self.precision_threshold)
        prec_layout.addStretch()
        thresholds_layout.addLayout(prec_layout)

        thresholds_group.setLayout(thresholds_layout)
        layout.addWidget(thresholds_group)

        # Export options
        export_group = QGroupBox("💾 Options d'Export")
        export_layout = QVBoxLayout()

        self.export_json = QCheckBox("Exporter résultats en JSON (pour CI/CD)")
        self.export_json.setChecked(False)
        export_layout.addWidget(self.export_json)

        self.auto_open_results = QCheckBox("Ouvrir les résultats automatiquement")
        self.auto_open_results.setChecked(True)
        export_layout.addWidget(self.auto_open_results)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        layout.addStretch()

        # Summary
        summary_label = QLabel("✅ Prêt à lancer le benchmark !")
        summary_label.setStyleSheet("""
            QLabel {
                background-color: #E8F5E9;
                padding: 15px;
                border-radius: 5px;
                font-weight: bold;
                color: #2E7D32;
            }
        """)
        layout.addWidget(summary_label)

        return page

    def _load_test_sets(self):
        """Load available test sets."""
        try:
            test_sets = self.test_set_manager.get_all_test_sets()
            self.test_set_list.clear()

            for ts_name in test_sets:
                count = len(self.test_set_manager.get_test_set(ts_name))
                item = QListWidgetItem(f"{ts_name} ({count} paires)")
                item.setData(Qt.ItemDataRole.UserRole, ts_name)
                self.test_set_list.addItem(item)

            if self.test_set_list.count() > 0:
                self.test_set_list.setCurrentRow(0)

        except Exception as e:
            logger.error(f"Error loading test sets: {e}", exc_info=True)

    def _load_pipelines(self):
        """Load available pipelines."""
        try:
            pipelines = self.pipeline_manager.get_saved_pipelines()
            self.pipeline_list.clear()

            for pipeline_name in pipelines:
                item = QListWidgetItem(f"🔧 {pipeline_name}")
                item.setData(Qt.ItemDataRole.UserRole, pipeline_name)
                self.pipeline_list.addItem(item)

            # Select first by default
            if self.pipeline_list.count() > 0:
                self.pipeline_list.item(0).setSelected(True)

        except Exception as e:
            logger.error(f"Error loading pipelines: {e}", exc_info=True)

    def _on_test_set_selected(self, current, previous):
        """Update test set info when selection changes."""
        if current:
            ts_name = current.data(Qt.ItemDataRole.UserRole)
            try:
                pairs = self.test_set_manager.get_test_set(ts_name)
                dups = sum(1 for p in pairs if p.get('expected') == 'duplicate')
                non_dups = len(pairs) - dups

                info = f"<b>{ts_name}</b><br><br>"
                info += f"Total paires: {len(pairs)}<br>"
                info += f"Duplicata attendus: {dups}<br>"
                info += f"Non-duplicata: {non_dups}"

                self.test_set_info.setHtml(info)

            except Exception as e:
                self.test_set_info.setText(f"Erreur: {e}")

    def _on_preset_selected(self, index):
        """Apply preset pipeline selection."""
        preset_data = self.preset_combo.currentData()
        if preset_data:
            # Clear selection
            self.pipeline_list.clearSelection()

            # Select pipelines from preset
            preset_pipelines = preset_data.get('pipelines', [])
            if preset_pipelines == 'all':
                # Select all
                for i in range(self.pipeline_list.count()):
                    self.pipeline_list.item(i).setSelected(True)
            else:
                # Select specific pipelines
                for i in range(self.pipeline_list.count()):
                    item = self.pipeline_list.item(i)
                    pipeline_name = item.data(Qt.ItemDataRole.UserRole)
                    if pipeline_name in preset_pipelines:
                        item.setSelected(True)

    def _update_pipeline_count(self):
        """Update selected pipeline count."""
        count = len(self.pipeline_list.selectedItems())
        self.pipeline_count_label.setText(f"Pipelines sélectionnés: {count}")
        self._update_time_estimate()

    def _update_time_estimate(self):
        """Update estimated time display."""
        # Get selected test set pairs count
        current_item = self.test_set_list.currentItem()
        if not current_item:
            self.time_estimate_label.setText("Temps estimé: --")
            return

        ts_name = current_item.data(Qt.ItemDataRole.UserRole)
        try:
            pairs = self.test_set_manager.get_test_set(ts_name)
            num_pairs = len(pairs)
        except:
            num_pairs = 0

        # Get selected pipelines count
        num_pipelines = len(self.pipeline_list.selectedItems())

        if num_pairs > 0 and num_pipelines > 0:
            estimate = BenchmarkPresets.estimate_duration(num_pairs, num_pipelines)
            self.time_estimate_label.setText(f"⏱️ Temps estimé: {estimate}")
        else:
            self.time_estimate_label.setText("Temps estimé: --")

    def _on_create_test_set(self):
        """Open test set creation wizard."""
        from .test_set_wizard import TestSetWizard
        wizard = TestSetWizard(self.test_set_manager, parent=self)
        wizard.test_set_created.connect(lambda name: self._load_test_sets())
        wizard.exec()

    def _on_back(self):
        """Go to previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            self.stacked_widget.setCurrentIndex(self.current_step)
            self._update_step_indicator()
            self._update_navigation_buttons()

    def _on_next(self):
        """Go to next step or finish."""
        if self.current_step < 3:
            # Validate current step
            if not self._validate_current_step():
                return

            self.current_step += 1
            self.stacked_widget.setCurrentIndex(self.current_step)
            self._update_step_indicator()
            self._update_navigation_buttons()

            # Update time estimate when reaching step 3
            if self.current_step == 2:
                self._update_time_estimate()

        else:
            # Finish - start benchmark
            self._finish()

    def _validate_current_step(self) -> bool:
        """Validate current step before proceeding."""
        if self.current_step == 1:  # Test set selection
            if not self.test_set_list.currentItem():
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un test set")
                return False

        elif self.current_step == 2:  # Pipeline selection
            if len(self.pipeline_list.selectedItems()) == 0:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Erreur", "Veuillez sélectionner au moins un pipeline")
                return False

        return True

    def _update_step_indicator(self):
        """Update progress indicator styling."""
        for i, label in enumerate(self.step_labels):
            if i == self.current_step:
                label.setStyleSheet("""
                    QLabel {
                        padding: 8px;
                        background-color: #2196F3;
                        color: white;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                """)
            elif i < self.current_step:
                label.setStyleSheet("""
                    QLabel {
                        padding: 8px;
                        background-color: #4CAF50;
                        color: white;
                        border-radius: 4px;
                        font-size: 11px;
                    }
                """)
            else:
                label.setStyleSheet("""
                    QLabel {
                        padding: 8px;
                        background-color: #E0E0E0;
                        color: #666;
                        border-radius: 4px;
                        font-size: 11px;
                    }
                """)

    def _update_navigation_buttons(self):
        """Update navigation button states."""
        self.back_btn.setEnabled(self.current_step > 0)

        if self.current_step == 3:
            self.next_btn.setText("🚀 Lancer le Benchmark")
            self.next_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #388E3C;
                }
            """)
        else:
            self.next_btn.setText("Suivant ➡️")
            self.next_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)

    def _finish(self):
        """Build configuration and emit signal to start benchmark."""
        # Get selected objective
        objective_id = None
        for button in self.objective_group.buttons():
            if button.isChecked():
                objective_id = button.property("objective_id")
                break

        # Get selected test set
        test_set_item = self.test_set_list.currentItem()
        test_set_name = test_set_item.data(Qt.ItemDataRole.UserRole) if test_set_item else None

        # Get selected pipelines
        pipeline_names = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.pipeline_list.selectedItems()
        ]

        # Build configuration
        config = {
            'objective': objective_id,
            'test_set_name': test_set_name,
            'pipeline_names': pipeline_names,
            'thresholds': {
                'f1_min': self.f1_threshold.value(),
                'precision_min': self.precision_threshold.value()
            },
            'export_json': self.export_json.isChecked(),
            'auto_open_results': self.auto_open_results.isChecked()
        }

        self.config = config
        self.benchmark_started.emit(config)
        self.accept()

    def get_config(self) -> dict:
        """Get the configured benchmark settings."""
        return self.config
