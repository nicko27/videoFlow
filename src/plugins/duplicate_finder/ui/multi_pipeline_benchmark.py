"""
Multi-Pipeline Benchmark Interface
Permet de tester plusieurs pipelines simultanément et comparer les résultats
"""
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QGroupBox, QProgressBar, QCheckBox,
    QDialog, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from src.core.logger import Logger
from ..services.benchmark_manager import BenchmarkManager, BenchmarkRunner
from ..services.test_set_manager import TestSetManager
from ..orchestration.pipeline_manager import PipelineManager
from .test_set_wizard import TestSetWizard
from .monitoring_dashboard import MonitoringDashboard
from .benchmark_monitor_dialog import BenchmarkMonitorDialog
from .benchmark_monitor_enhanced import EnhancedBenchmarkMonitor
from ..infrastructure.i18n import I18n

logger = Logger.get_logger('DuplicateFinder.MultiPipelineBenchmark')


class MultiPipelineBenchmarkWidget(QWidget):
    """
    Interface de benchmark permettant de tester plusieurs pipelines simultanément.

    Workflow:
    1. Sélectionner UN test set
    2. Sélectionner PLUSIEURS pipelines à tester
    3. Lancer le benchmark
    4. Voir tableau comparatif des résultats
    """

    benchmark_finished = pyqtSignal(int)  # run_id
    benchmark_results_ready = pyqtSignal(list)  # results data for right panel display

    def __init__(
        self,
        benchmark_manager: BenchmarkManager,
        pipeline_manager: PipelineManager,
        test_set_manager: TestSetManager,
        db_manager,
        file_list_widget=None
    ):
        super().__init__()
        self.benchmark_manager = benchmark_manager
        self.pipeline_manager = pipeline_manager
        self.test_set_manager = test_set_manager
        self.db_manager = db_manager
        self.file_list_widget = file_list_widget
        self.runner: Optional[BenchmarkRunner] = None
        self.monitor_dialog: Optional[BenchmarkMonitorDialog] = None

        self.pipeline_checkboxes: Dict[str, QCheckBox] = {}

        self._init_ui()
        self._load_test_sets()
        self._load_pipelines()

    def _init_ui(self):
        """Initialize the multi-pipeline benchmark UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Header
        header = QLabel("🚀 <b>Benchmark Multi-Pipeline</b>")
        header.setStyleSheet("font-size: 16px; padding: 10px; background-color: #E3F2FD; border-radius: 5px;")
        layout.addWidget(header)

        # Description
        desc = QLabel(
            "Testez plusieurs pipelines simultanément sur le même test set et comparez les résultats"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(desc)

        # Configuration section
        config_group = QGroupBox("⚙️ Configuration")
        config_layout = QVBoxLayout()

        # Test Set selector
        ts_layout = QHBoxLayout()
        ts_layout.addWidget(QLabel("Test Set:"))
        self.test_set_combo = QComboBox()
        ts_layout.addWidget(self.test_set_combo, stretch=1)

        wizard_btn = QPushButton("🧙 Wizard")
        wizard_btn.clicked.connect(self._on_open_wizard)
        wizard_btn.setToolTip("Créer un nouveau test set avec les fichiers chargés")
        ts_layout.addWidget(wizard_btn)

        manage_btn = QPushButton("⚙️ Gérer")
        manage_btn.clicked.connect(self._on_manage_test_sets)
        manage_btn.setToolTip("Modifier et supprimer les test sets")
        ts_layout.addWidget(manage_btn)

        config_layout.addLayout(ts_layout)

        # Pipelines selection (checkboxes!)
        pipe_label = QLabel("<b>Pipelines à Tester:</b> (Sélectionnez plusieurs)")
        config_layout.addWidget(pipe_label)

        # Scrollable area for pipeline checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(300)  # Increased height for better visibility
        scroll.setMinimumHeight(150)  # Minimum height

        # Always show vertical scrollbar for clarity
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.pipeline_container = QWidget()
        self.pipeline_layout = QVBoxLayout(self.pipeline_container)
        self.pipeline_layout.setContentsMargins(10, 10, 10, 10)
        self.pipeline_layout.setSpacing(5)
        scroll.setWidget(self.pipeline_container)
        config_layout.addWidget(scroll)

        # Pipeline management buttons
        pipe_btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("✅ Tout Sélectionner")
        select_all_btn.clicked.connect(self._select_all_pipelines)
        pipe_btn_layout.addWidget(select_all_btn)

        select_none_btn = QPushButton("⬜ Tout Désélectionner")
        select_none_btn.clicked.connect(self._deselect_all_pipelines)
        pipe_btn_layout.addWidget(select_none_btn)

        new_pipe_btn = QPushButton("➕ Nouveau Pipeline")
        new_pipe_btn.clicked.connect(self._on_new_pipeline)
        new_pipe_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        pipe_btn_layout.addWidget(new_pipe_btn)

        pipe_btn_layout.addStretch()
        config_layout.addLayout(pipe_btn_layout)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Start button
        self.start_btn = QPushButton("▶️  LANCER LE BENCHMARK")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.start_btn.clicked.connect(self._on_start_benchmark)
        layout.addWidget(self.start_btn)

        # Progress section
        progress_group = QGroupBox("📈 Progression")
        progress_layout = QVBoxLayout()

        # Global progress label
        global_label = QLabel("<b>Progression Globale:</b>")
        progress_layout.addWidget(global_label)

        # Global progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setFormat("%p% (%v/%m paires)")  # Format: "50% (45/90 paires)"
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Prêt")
        self.status_label.setStyleSheet("padding: 5px; color: #666;")
        progress_layout.addWidget(self.status_label)

        # Separator
        separator1 = QLabel()
        separator1.setFixedHeight(10)
        progress_layout.addWidget(separator1)

        # Per-pipeline progress section
        pipeline_progress_label = QLabel("<b>Détail par Pipeline:</b>")
        progress_layout.addWidget(pipeline_progress_label)

        # Container for pipeline progress bars (created dynamically)
        self.pipeline_progress_container = QWidget()
        self.pipeline_progress_layout = QVBoxLayout(self.pipeline_progress_container)
        self.pipeline_progress_layout.setContentsMargins(0, 0, 0, 0)
        self.pipeline_progress_layout.setSpacing(8)
        progress_layout.addWidget(self.pipeline_progress_container)

        # Current pair being processed
        self.pair_status_label = QLabel("")
        self.pair_status_label.setStyleSheet("padding: 5px; color: #888; font-style: italic;")
        self.pair_status_label.setWordWrap(True)
        progress_layout.addWidget(self.pair_status_label)

        progress_group.setLayout(progress_layout)
        progress_group.setVisible(False)  # Hidden by default
        self.progress_group = progress_group
        layout.addWidget(progress_group)

        # Dictionary to track pipeline progress bars
        self.pipeline_progress_bars: Dict[str, tuple] = {}  # name -> (label, progressbar)

        # Stop button
        self.stop_btn = QPushButton("⏹️  ARRÊTER")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.stop_btn.clicked.connect(self._on_stop_benchmark)
        self.stop_btn.setVisible(False)
        layout.addWidget(self.stop_btn)

        # Note: Results comparison table is now displayed in the right panel
        # No need for results table in this tab anymore

        # Pipeline library button
        library_btn = QPushButton("📚 Gérer les Pipelines")
        library_btn.setMinimumHeight(40)
        library_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
        """)
        library_btn.clicked.connect(self._open_pipeline_library)
        layout.addWidget(library_btn)

        layout.addStretch()

    def _load_test_sets(self):
        """Load available test sets."""
        self.test_set_combo.clear()
        test_sets = self.test_set_manager.list_test_sets()
        for test_set in test_sets:
            name = test_set['name']
            pair_count = test_set.get('pair_count', 0)
            self.test_set_combo.addItem(f"{name} ({pair_count} pairs)", userData=test_set)

    def _load_pipelines(self):
        """Load available pipelines as checkboxes."""
        # Clear existing checkboxes
        for checkbox in self.pipeline_checkboxes.values():
            checkbox.deleteLater()
        self.pipeline_checkboxes.clear()

        # Load pipelines
        pipelines = self.pipeline_manager.list_pipelines()

        if not pipelines:
            no_pipe_label = QLabel("⚠️ Aucun pipeline disponible. Créez-en un!")
            no_pipe_label.setStyleSheet("color: #ff9800; padding: 10px;")
            self.pipeline_layout.addWidget(no_pipe_label)
            return

        for pipeline in pipelines:
            name = pipeline['name']
            method_count = len(pipeline.get('methods', []))

            checkbox = QCheckBox(f"{name} ({method_count} méthodes)")
            checkbox.setProperty('pipeline_data', pipeline)
            checkbox.setStyleSheet("padding: 5px;")

            self.pipeline_checkboxes[name] = checkbox
            self.pipeline_layout.addWidget(checkbox)

        self.pipeline_layout.addStretch()

    def _select_all_pipelines(self):
        """Select all pipeline checkboxes."""
        for checkbox in self.pipeline_checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all_pipelines(self):
        """Deselect all pipeline checkboxes."""
        for checkbox in self.pipeline_checkboxes.values():
            checkbox.setChecked(False)

    def _get_selected_pipelines(self) -> List[Dict]:
        """Get list of selected pipeline configs."""
        selected = []
        for name, checkbox in self.pipeline_checkboxes.items():
            if checkbox.isChecked():
                pipeline_data = checkbox.property('pipeline_data')
                selected.append(pipeline_data)
        return selected

    def _on_open_wizard(self):
        """Open test set creation/edit wizard."""
        current_files = []
        if self.file_list_widget:
            current_files = self.file_list_widget.get_files()

        # Get currently selected test set (if any)
        current_test_set = self.test_set_combo.currentText() if self.test_set_combo.count() > 0 else None

        wizard = TestSetWizard(
            self.test_set_manager,
            preset_file_list=current_files,
            existing_test_set=current_test_set,
            parent=self
        )
        wizard.test_set_created.connect(lambda name: self._load_test_sets())
        wizard.exec()

    def _on_manage_test_sets(self):
        """Open test set management dialog."""
        from .benchmark_widgets import TestSetEditorWidget

        # Create a dialog to host the TestSetEditorWidget
        dialog = QDialog(self)
        dialog.setWindowTitle("Gestion des Test Sets")
        dialog.setMinimumSize(900, 600)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)

        # Add the TestSetEditorWidget
        test_set_widget = TestSetEditorWidget(self.test_set_manager)
        test_set_widget.test_set_changed.connect(lambda name: self._load_test_sets())
        layout.addWidget(test_set_widget)

        # Close button
        from PyQt6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.exec()

        # Reload test sets when dialog closes
        self._load_test_sets()

    def _on_new_pipeline(self):
        """Créer un pipeline via l'éditeur unifié."""
        from .unified_pipeline_editor_dialog import UnifiedPipelineEditorDialog

        dialog = UnifiedPipelineEditorDialog(
            pipeline_manager=self.pipeline_manager,
            db_manager=self.db_manager,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_pipelines()
            logger.info("Pipeline créé via l'éditeur unifié")

    def _cleanup_previous_benchmark(self):
        """
        CORRECTION BUG #18: Cleanup previous benchmark to prevent memory leaks.

        Disconnects all signals and deletes previous runner/dialog objects.
        """
        if self.runner:
            # Disconnect all runner signals
            try:
                self.runner.pipeline_progress.disconnect()
                self.runner.pair_progress.disconnect()
                self.runner.pipeline_metrics_updated.disconnect()
                self.runner.pipeline_completed.disconnect()
                self.runner.finished.disconnect()
                self.runner.error.disconnect()
                self.runner.hashing_progress.disconnect()
            except (RuntimeError, TypeError):
                # Signals may already be disconnected
                pass

            # Stop and wait for thread if still running
            if self.runner.isRunning():
                self.runner.stop()
                self.runner.wait(2000)  # Wait max 2 seconds

            # Delete runner
            self.runner.deleteLater()
            self.runner = None

        # Cleanup monitor dialog
        if self.monitor_dialog:
            try:
                # Disconnect stop_requested signal if connected
                self.monitor_dialog.stop_requested.disconnect()
            except (RuntimeError, TypeError):
                pass

            # Close and delete dialog
            self.monitor_dialog.close()
            self.monitor_dialog.deleteLater()
            self.monitor_dialog = None

        logger.debug("Previous benchmark resources cleaned up")

    def _on_start_benchmark(self):
        """Start multi-pipeline benchmark."""
        # CORRECTION BUG #18: Cleanup previous benchmark before starting new one
        self._cleanup_previous_benchmark()

        # Validate
        if not self.test_set_combo.currentData():
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un test set")
            return

        selected_pipelines = self._get_selected_pipelines()
        if not selected_pipelines:
            QMessageBox.warning(
                self,
                "Erreur",
                "Veuillez sélectionner au moins un pipeline à tester"
            )
            return

        # Get test set pairs
        test_set = self.test_set_combo.currentData()
        test_pairs = self.test_set_manager.get_test_set(test_set['name'])

        if not test_pairs:
            QMessageBox.warning(
                self,
                "Erreur",
                f"Le test set '{test_set['name']}' ne contient aucune paire"
            )
            return

        # Create runner
        run_label = f"Benchmark: {test_set['name']} with {len(selected_pipelines)} pipelines"
        self.runner = BenchmarkRunner(
            self.db_manager,
            test_pairs,
            selected_pipelines,
            run_label,
            max_pipeline_workers=min(len(selected_pipelines), 3),  # Max 3 pipelines en parallèle
            max_pair_workers=4  # 4 paires en parallèle par pipeline
        )

        # Connect signals
        self.runner.pipeline_progress.connect(self._on_pipeline_progress)
        self.runner.pair_progress.connect(self._on_pair_progress)
        self.runner.pipeline_metrics_updated.connect(self._on_pipeline_metrics_updated)
        self.runner.pipeline_completed.connect(self._on_pipeline_completed)
        self.runner.finished.connect(self._on_benchmark_finished)
        self.runner.error.connect(self._on_benchmark_error)

        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setVisible(True)
        # Hide the progress group - everything is now in the popup
        self.progress_group.setVisible(False)
        # Note: Results are now displayed in the right panel, no local results_group

        # Create progress bars for each pipeline (still needed for internal tracking)
        self._create_pipeline_progress_bars(selected_pipelines)

        # Create and show ENHANCED monitor dialog (popup window)
        self.monitor_dialog = EnhancedBenchmarkMonitor(parent=self)

        # Connect runner signals to monitor dialog
        self.runner.hashing_progress.connect(self.monitor_dialog.update_hash_progress)
        self.runner.pipeline_progress.connect(self.monitor_dialog.update_pipeline_progress)
        self.runner.pipeline_metrics_updated.connect(self.monitor_dialog.update_metrics)

        # Connect stop button from monitor to benchmark
        self.monitor_dialog.stop_requested.connect(self.stop_benchmark)

        # Start the benchmark timer
        self.monitor_dialog.start_benchmark()

        # Show the monitor dialog
        self.monitor_dialog.show()

        # Start
        self.runner.start()
        logger.info(f"Multi-pipeline benchmark started: {len(selected_pipelines)} pipelines on {test_set['name']}")

    def _on_stop_benchmark(self):
        """Stop benchmark execution."""
        self.stop_benchmark()

    def stop_benchmark(self):
        """
        Stop benchmark execution (méthode publique).

        Cette méthode peut être appelée depuis l'extérieur (par exemple par le main window)
        pour arrêter un benchmark en cours.
        """
        if self.runner and self.runner.isRunning():
            logger.info("🛑 Arrêt du benchmark demandé...")
            self.runner.stop()
            self.status_label.setText("Arrêt en cours...")

            # Attendre maximum 5 secondes pour arrêt propre
            if not self.runner.wait(5000):
                logger.warning("⚠️ Le benchmark n'a pas stop proprement, forçage de l'arrêt...")
                self.runner.terminate()

            logger.info("✅ Benchmark arrêté")

    def _create_pipeline_progress_bars(self, pipelines: List[Dict]):
        """Create progress bars for each pipeline to be tested with detailed metrics."""
        # Clear existing progress bars
        while self.pipeline_progress_layout.count():
            item = self.pipeline_progress_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.pipeline_progress_bars.clear()

        # Create progress bar for each pipeline
        for pipeline in pipelines:
            name = pipeline['name']

            # Container for this pipeline's progress (with border for visibility)
            pipeline_widget = QWidget()
            pipeline_widget.setStyleSheet("""
                QWidget {
                    background-color: #f9f9f9;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 5px;
                }
            """)
            pipeline_layout = QVBoxLayout(pipeline_widget)
            pipeline_layout.setContentsMargins(8, 8, 8, 8)
            pipeline_layout.setSpacing(4)

            # Header: Pipeline name
            name_label = QLabel(f"⏳ {name}")
            name_label.setStyleSheet("font-weight: bold; color: #555; font-size: 13px;")
            pipeline_layout.addWidget(name_label)

            # Progress bar
            progress_bar = QProgressBar()
            progress_bar.setTextVisible(True)
            progress_bar.setMinimumHeight(22)
            progress_bar.setValue(0)
            progress_bar.setFormat("%p% (%v/%m)")
            progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #4CAF50;
                }
            """)
            pipeline_layout.addWidget(progress_bar)

            # Metrics row: TP/FP/TN/FN
            metrics_layout = QHBoxLayout()
            metrics_layout.setSpacing(10)

            tp_label = QLabel("✅ TP: 0")
            tp_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            fp_label = QLabel("❌ FP: 0")
            fp_label.setStyleSheet("color: #F44336; font-size: 11px;")
            tn_label = QLabel("✅ TN: 0")
            tn_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            fn_label = QLabel("❌ FN: 0")
            fn_label.setStyleSheet("color: #F44336; font-size: 11px;")

            metrics_layout.addWidget(tp_label)
            metrics_layout.addWidget(fp_label)
            metrics_layout.addWidget(tn_label)
            metrics_layout.addWidget(fn_label)
            metrics_layout.addStretch()
            pipeline_layout.addLayout(metrics_layout)

            # Performance metrics: P/R/F1
            performance_label = QLabel("📊 P: 0.0% | R: 0.0% | F1: 0.0%")
            performance_label.setStyleSheet("color: #666; font-size: 11px; font-weight: bold;")
            pipeline_layout.addWidget(performance_label)

            # Speed and ETA
            speed_label = QLabel("⏱️ Vitesse: -- | ⏳ ETA: --")
            speed_label.setStyleSheet("color: #888; font-size: 10px;")
            pipeline_layout.addWidget(speed_label)

            self.pipeline_progress_layout.addWidget(pipeline_widget)

            # Store all widgets for this pipeline
            self.pipeline_progress_bars[name] = {
                'name_label': name_label,
                'progress_bar': progress_bar,
                'tp_label': tp_label,
                'fp_label': fp_label,
                'tn_label': tn_label,
                'fn_label': fn_label,
                'performance_label': performance_label,
                'speed_label': speed_label
            }

    def _on_pipeline_progress(self, current, total, name):
        """Update global progress when switching to a new pipeline."""
        # Calculer la progression globale de TOUS les pipelines
        total_pairs_all_pipelines = 0
        completed_pairs_all_pipelines = 0

        for pipe_name, widgets in self.pipeline_progress_bars.items():
            progress_bar = widgets['progress_bar']
            total_pairs_all_pipelines += progress_bar.maximum()
            completed_pairs_all_pipelines += progress_bar.value()

        # Mettre à jour la barre globale avec le vrai nombre de paires
        if total_pairs_all_pipelines > 0:
            self.progress_bar.setMaximum(total_pairs_all_pipelines)
            self.progress_bar.setValue(completed_pairs_all_pipelines)
            progress_pct = int((completed_pairs_all_pipelines / total_pairs_all_pipelines) * 100)
            self.status_label.setText(f"Pipeline {name}: {current}/{total} paires ({progress_pct}% total)")
        else:
            self.progress_bar.setValue(0)
            self.status_label.setText(f"Pipeline {name}: {current}/{total} paires")

        logger.debug(f"Progress: {current}/{total} - {name} (Global: {completed_pairs_all_pipelines}/{total_pairs_all_pipelines})")

        # Mark current pipeline as active
        for pipe_name, widgets in self.pipeline_progress_bars.items():
            label = widgets['name_label']
            if pipe_name == name:
                label.setText(f"▶️ {pipe_name} (en cours...)")
                label.setStyleSheet("font-weight: bold; color: #2196F3; font-size: 13px;")
            elif label.text().startswith("✅"):
                # Already completed - keep as is
                pass
            else:
                # Not yet started
                label.setText(f"⏳ {pipe_name}")
                label.setStyleSheet("font-weight: bold; color: #888; font-size: 13px;")

    def _on_pair_progress(self, current_pair, total_pairs, video1, video2):
        """Update detailed progress for current pipeline pair processing."""
        # Find the currently active pipeline
        current_pipeline = None
        for pipe_name, widgets in self.pipeline_progress_bars.items():
            if widgets['name_label'].text().startswith("▶️"):
                current_pipeline = pipe_name
                # Update this pipeline's progress bar
                widgets['progress_bar'].setMaximum(total_pairs)
                widgets['progress_bar'].setValue(current_pair)
                break

        # Update pair status label
        video1_short = video1.split('/')[-1] if '/' in video1 else video1
        video2_short = video2.split('/')[-1] if '/' in video2 else video2
        self.pair_status_label.setText(
            f"🔍 Traitement paire {current_pair}/{total_pairs}: {video1_short} ↔ {video2_short}"
        )

    def _on_pipeline_metrics_updated(self, pipeline_name: str, metrics: dict):
        """Update pipeline metrics in real-time (TP/FP/TN/FN, P/R/F1, speed, ETA)."""
        if pipeline_name not in self.pipeline_progress_bars:
            return

        widgets = self.pipeline_progress_bars[pipeline_name]

        # Update TP/FP/TN/FN
        widgets['tp_label'].setText(f"✅ TP: {metrics['tp']}")
        widgets['fp_label'].setText(f"❌ FP: {metrics['fp']}")
        widgets['tn_label'].setText(f"✅ TN: {metrics['tn']}")
        widgets['fn_label'].setText(f"❌ FN: {metrics['fn']}")

        # Update P/R/F1 with color coding
        precision = metrics['precision']
        recall = metrics['recall']
        f1 = metrics['f1']

        # Color for F1 score
        if f1 >= 90:
            color = "#4CAF50"  # Green
        elif f1 >= 75:
            color = "#FFC107"  # Amber
        else:
            color = "#F44336"  # Red

        widgets['performance_label'].setText(f"📊 P: {precision:.1f}% | R: {recall:.1f}% | F1: {f1:.1f}%")
        widgets['performance_label'].setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")

        # Update speed and ETA
        speed = metrics['speed']
        eta = metrics['eta']

        # Format speed
        speed_text = f"{speed:.2f}s/paire" if speed < 60 else f"{speed/60:.1f}min/paire"

        # Format ETA
        if eta < 60:
            eta_text = f"{eta:.0f}s"
        elif eta < 3600:
            eta_text = f"{eta/60:.1f}min"
        else:
            eta_text = f"{eta/3600:.1f}h"

        widgets['speed_label'].setText(f"⏱️ Vitesse: {speed_text} | ⏳ ETA: {eta_text}")

    def _on_pipeline_completed(self, name, results):
        """Mark pipeline as completed."""
        if name in self.pipeline_progress_bars:
            widgets = self.pipeline_progress_bars[name]
            widgets['name_label'].setText(f"✅ {name} (terminé)")
            widgets['name_label'].setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 13px;")
            widgets['progress_bar'].setValue(widgets['progress_bar'].maximum())  # Set to 100%
            logger.info(f"Pipeline '{name}' completed")

    def _on_benchmark_finished(self, run_id):
        """Handle benchmark completion and show comparison table."""
        self.progress_bar.setValue(100)
        self.status_label.setText(f"✅ Benchmark terminé! Run #{run_id}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setVisible(False)

        # Notify enhanced monitor that benchmark is finished
        if self.monitor_dialog:
            self.monitor_dialog.finish_benchmark()

        # Load results
        results = self.benchmark_manager.get_benchmark_results(run_id)

        # Emit signal for right panel display
        # Note: Results are now displayed in the right panel, not in the benchmark tab
        if results:
            self.benchmark_results_ready.emit(results)

        self.benchmark_finished.emit(run_id)
        logger.info(f"Multi-pipeline benchmark completed: run #{run_id}")

    def _display_comparison_results(self, run_id):
        """
        DEPRECATED: Display comparison table of results.

        This method is no longer used as results are now displayed in the right panel
        of the main window via the benchmark_results_ready signal.
        Kept for backward compatibility but does nothing.
        """
        logger.debug(f"_display_comparison_results() called for run #{run_id} (deprecated, no-op)")

    def _on_benchmark_error(self, error_msg):
        """Handle benchmark error."""
        self.status_label.setText(f"❌ Erreur: {error_msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setVisible(False)
        self.progress_group.setVisible(False)
        QMessageBox.critical(self, "Erreur Benchmark", f"Une erreur est survenue:\n\n{error_msg}")
        logger.error(f"Benchmark error: {error_msg}")

    def _open_pipeline_library(self):
        """Open the pipeline library dialog."""
        from .pipeline_library_dialog import PipelineLibraryDialog

        dialog = PipelineLibraryDialog(
            self.pipeline_manager,
            self.db_manager,
            parent=self.parent()  # Pass main window as parent
        )
        dialog.exec()

        # Reload pipelines after dialog closes (in case user added/modified)
        self._load_pipelines()

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when widget is closed.

        Ensures proper memory cleanup when the widget is destroyed.
        """
        self._cleanup_previous_benchmark()
        super().closeEvent(event)


class BenchmarkHistoryWidget(QWidget):
    """Widget pour afficher l'historique détaillé des benchmarks."""

    def __init__(self, benchmark_manager: BenchmarkManager):
        super().__init__()
        self.benchmark_manager = benchmark_manager
        self._init_ui()
        self._load_history()

    def _init_ui(self):
        """Initialize history UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        header = QLabel("<b>📜 Historique des Benchmarks</b>")
        header.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(header)

        header_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self._load_history)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "Run ID", "Date", "Test Set", "Pipelines", "Paires", "F1 Moyen", "Actions"
        ])
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.history_table)

        # Details section
        details_group = QGroupBox("📊 Détails du Run Sélectionné")
        details_layout = QVBoxLayout()

        self.details_text = QLabel("Sélectionnez un run pour voir les détails")
        self.details_text.setWordWrap(True)
        self.details_text.setStyleSheet("padding: 10px; background-color: #f9f9f9; border-radius: 5px;")
        details_layout.addWidget(self.details_text)

        # Results table for selected run
        self.results_table = QTableWidget()
        self.results_table.setMaximumHeight(200)
        self.results_table.setVisible(False)
        details_layout.addWidget(self.results_table)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # Connect selection signal
        self.history_table.itemSelectionChanged.connect(self._on_selection_changed)

    def _load_history(self):
        """Load benchmark history."""
        runs = self.benchmark_manager.list_benchmark_runs(limit=100)

        self.history_table.setRowCount(len(runs))

        for row, run in enumerate(runs):
            # Run ID
            id_item = QTableWidgetItem(str(run['id']))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_table.setItem(row, 0, id_item)

            # Date
            date_str = run.get('created_at', 'N/A')
            if date_str and date_str != 'N/A':
                # Format: YYYY-MM-DD HH:MM:SS -> DD/MM/YY HH:MM
                try:
                    from datetime import datetime
                    dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    date_str = dt.strftime('%d/%m/%y %H:%M')
                except Exception as parse_err:
                    logger.debug(f"Impossible de parser la date {date_str}: {parse_err}")
            date_item = QTableWidgetItem(date_str)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_table.setItem(row, 1, date_item)

            # Test Set
            ts_item = QTableWidgetItem(run.get('test_set_name', 'N/A'))
            self.history_table.setItem(row, 2, ts_item)

            # Number of pipelines
            pipe_count = run.get('pipelines_count', 0)
            pipe_item = QTableWidgetItem(str(pipe_count))
            pipe_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_table.setItem(row, 3, pipe_item)

            # Number of pairs
            pairs_count = run.get('pairs_count', 'N/A')
            pairs_item = QTableWidgetItem(str(pairs_count))
            pairs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_table.setItem(row, 4, pairs_item)

            # Average F1 (or acceptance rate for unlabeled sets)
            results = self.benchmark_manager.get_benchmark_results(run['id'])
            if results:
                # Check if this is a labeled or unlabeled test set
                is_labeled = results[0].get('is_labeled', True) if results else True

                if is_labeled:
                    # Standard F1 score for labeled sets
                    f1_values = [r.get('f1_score', 0) for r in results]
                    avg_f1 = sum(f1_values) / len(f1_values) if f1_values else 0
                    f1_str = f"{avg_f1:.1f}%"

                    f1_item = QTableWidgetItem(f1_str)
                    f1_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    # Color code
                    if avg_f1 >= 90.0:
                        f1_item.setBackground(QColor("#C8E6C9"))
                    elif avg_f1 >= 75.0:
                        f1_item.setBackground(QColor("#FFF9C4"))
                    else:
                        f1_item.setBackground(QColor("#FFCDD2"))
                else:
                    # Show average acceptance rate for unlabeled sets
                    acceptance_rates = []
                    for r in results:
                        accepted = r.get('accepted', 0)
                        rejected = r.get('rejected', 0)
                        total = accepted + rejected
                        if total > 0:
                            acceptance_rates.append((accepted / total) * 100)

                    avg_acceptance = sum(acceptance_rates) / len(acceptance_rates) if acceptance_rates else 0
                    f1_str = f"{avg_acceptance:.1f}% acc"

                    f1_item = QTableWidgetItem(f1_str)
                    f1_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    # Color code (gray for unlabeled)
                    f1_item.setBackground(QColor("#E0E0E0"))
            else:
                f1_item = QTableWidgetItem("--")
                f1_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.history_table.setItem(row, 5, f1_item)

            # Actions (placeholder for now)
            action_item = QTableWidgetItem("📊 Détails")
            action_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_table.setItem(row, 6, action_item)

        logger.info(f"Loaded {len(runs)} benchmark runs in history")

    def _on_selection_changed(self):
        """Handle row selection to show details."""
        selected_rows = self.history_table.selectedItems()
        if not selected_rows:
            self.details_text.setText("Sélectionnez un run pour voir les détails")
            self.results_table.setVisible(False)
            return

        # Get run ID from first column of selected row
        row = selected_rows[0].row()
        run_id = int(self.history_table.item(row, 0).text())

        # Get run details
        runs = self.benchmark_manager.list_benchmark_runs(limit=100)
        run = next((r for r in runs if r['id'] == run_id), None)

        if not run:
            return

        # Display details
        details_html = f"""
        <b>Run #{run_id}</b><br>
        <b>Test Set:</b> {run.get('test_set_name', 'N/A')}<br>
        <b>Date:</b> {run.get('created_at', 'N/A')}<br>
        <b>Pipelines testés:</b> {run.get('pipelines_count', 0)}<br>
        <b>Paires de test:</b> {run.get('pairs_count', 'N/A')}<br>
        """
        self.details_text.setText(details_html)

        # Load and display results
        self._display_run_results(run_id)

    def _display_run_results(self, run_id: int):
        """Display detailed results for a specific run."""
        results = self.benchmark_manager.get_benchmark_results(run_id)

        if not results:
            self.results_table.setVisible(False)
            return

        # Setup table
        self.results_table.setVisible(True)
        self.results_table.setRowCount(len(results))
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Pipeline", "Precision", "Recall", "F1-Score", "TP", "FP"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for row, result in enumerate(results):
            # Pipeline name
            name_item = QTableWidgetItem(result['pipeline_name'])
            self.results_table.setItem(row, 0, name_item)

            # Metrics
            metrics = [
                ('precision', result.get('precision', 0)),
                ('recall', result.get('recall', 0)),
                ('f1_score', result.get('f1_score', 0)),
            ]

            for col, (key, value) in enumerate(metrics, start=1):
                item = QTableWidgetItem(f"{value:.1%}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Color code
                if value >= 0.9:
                    item.setBackground(QColor("#C8E6C9"))
                elif value >= 0.75:
                    item.setBackground(QColor("#FFF9C4"))
                elif value < 0.6:
                    item.setBackground(QColor("#FFCDD2"))

                self.results_table.setItem(row, col, item)

            # TP and FP
            tp_item = QTableWidgetItem(str(result.get('true_positives', 0)))
            tp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 4, tp_item)

            fp_item = QTableWidgetItem(str(result.get('false_positives', 0)))
            fp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 5, fp_item)


class BenchmarkDashboardWindow(QDialog):
    """Fenêtre séparée pour le dashboard détaillé."""

    def __init__(self, benchmark_manager: BenchmarkManager, parent=None):
        super().__init__(parent)
        self.benchmark_manager = benchmark_manager
        self.setWindowTitle("📊 Benchmark Dashboard")
        self.resize(1200, 800)
        self._init_ui()

    def _init_ui(self):
        """Initialize dashboard UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()

        # Tab 1: Monitoring Dashboard
        dashboard_tab = MonitoringDashboard(self.benchmark_manager, alert_system=None)
        tabs.addTab(dashboard_tab, "📈 Métriques & Graphiques")

        # Tab 2: History
        history_tab = BenchmarkHistoryWidget(self.benchmark_manager)
        tabs.addTab(history_tab, "📜 Historique")

        layout.addWidget(tabs)
