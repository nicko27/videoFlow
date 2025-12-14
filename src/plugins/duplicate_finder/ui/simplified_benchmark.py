"""
Simplified Benchmark System - Proposition 2
Interface d'exécution simple + Dashboard séparé
"""
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QGroupBox, QProgressBar, QListWidget, QListWidgetItem,
    QDialog, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from src.core.logger import Logger
from ..services.benchmark_manager import BenchmarkManager, BenchmarkRunner
from ..services.test_set_manager import TestSetManager
from ..orchestration.pipeline_manager import PipelineManager
from .test_set_wizard import TestSetWizard
from .monitoring_dashboard import MonitoringDashboard

logger = Logger.get_logger('DuplicateFinder.SimplifiedBenchmark')


class SimplifiedBenchmarkWidget(QWidget):
    """
    Interface d'exécution simplifiée pour les benchmarks.

    Focus sur le workflow principal:
    1. Choisir test set et pipeline
    2. Lancer
    3. Voir les derniers résultats

    Le dashboard détaillé est dans une fenêtre séparée.
    """

    benchmark_finished = pyqtSignal(int)  # run_id

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
        self._dashboard_window: Optional['BenchmarkDashboardWindow'] = None

        self._init_ui()
        self._load_test_sets()
        self._load_pipelines()
        self._load_recent_results()

    def _init_ui(self):
        """Initialize the simplified UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Header
        header = QLabel("🚀 <b>Benchmark - Exécution</b>")
        header.setStyleSheet("font-size: 16px; padding: 10px;")
        layout.addWidget(header)

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
        wizard_btn.setToolTip("Créer un nouveau test set")
        ts_layout.addWidget(wizard_btn)
        config_layout.addLayout(ts_layout)

        # Pipeline selector
        pipe_layout = QHBoxLayout()
        pipe_layout.addWidget(QLabel("Pipeline:"))
        self.pipeline_combo = QComboBox()
        pipe_layout.addWidget(self.pipeline_combo, stretch=1)

        new_pipe_btn = QPushButton("🔧 Nouveau")
        new_pipe_btn.clicked.connect(self._on_new_pipeline)
        new_pipe_btn.setToolTip("Créer un nouveau pipeline")
        pipe_layout.addWidget(new_pipe_btn)
        config_layout.addLayout(pipe_layout)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Start button
        self.start_btn = QPushButton("▶️  DÉMARRER LE BENCHMARK")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
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

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumHeight(30)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Prêt")
        self.status_label.setStyleSheet("padding: 5px; color: #666;")
        progress_layout.addWidget(self.status_label)

        self.eta_label = QLabel("")
        self.eta_label.setStyleSheet("padding: 5px; color: #888; font-style: italic;")
        progress_layout.addWidget(self.eta_label)

        progress_group.setLayout(progress_layout)
        progress_group.setVisible(False)  # Hidden by default
        self.progress_group = progress_group
        layout.addWidget(progress_group)

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

        # Recent results section
        results_group = QGroupBox("📊 Derniers Résultats")
        results_layout = QVBoxLayout()

        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(150)
        self.results_list.setStyleSheet("""
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        results_layout.addWidget(self.results_list)

        view_more_btn = QPushButton("📜 Voir Plus →")
        view_more_btn.clicked.connect(self._open_dashboard)
        results_layout.addWidget(view_more_btn)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        # Dashboard button
        dashboard_btn = QPushButton("📊 OUVRIR LE DASHBOARD")
        dashboard_btn.setMinimumHeight(45)
        dashboard_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 15px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        dashboard_btn.clicked.connect(self._open_dashboard)
        layout.addWidget(dashboard_btn)

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
        """Load available pipelines."""
        self.pipeline_combo.clear()
        pipelines = self.pipeline_manager.list_pipelines()
        for pipeline in pipelines:
            name = pipeline['name']
            method_count = len(pipeline.get('methods', []))
            self.pipeline_combo.addItem(f"{name} ({method_count} methods)", userData=pipeline)

    def _load_recent_results(self):
        """Load recent benchmark results."""
        self.results_list.clear()
        runs = self.benchmark_manager.list_benchmark_runs(limit=5)

        if not runs:
            item = QListWidgetItem("Aucun résultat disponible")
            item.setForeground(Qt.GlobalColor.gray)
            self.results_list.addItem(item)
            return

        for run in runs:
            # Get results for this run
            results = self.benchmark_manager.get_benchmark_results(run['id'])
            if results:
                avg_precision = sum(r.get('precision', 0) for r in results) / len(results) * 100
                avg_recall = sum(r.get('recall', 0) for r in results) / len(results) * 100

                text = f"Run #{run['id']} - P:{avg_precision:.1f}% R:{avg_recall:.1f}% ({run['test_set_name']})"
            else:
                text = f"Run #{run['id']} - {run['test_set_name']} (no results)"

            item = QListWidgetItem(text)
            self.results_list.addItem(item)

    def _on_open_wizard(self):
        """Open test set creation wizard."""
        current_files = []
        if self.file_list_widget:
            current_files = self.file_list_widget.get_files()

        wizard = TestSetWizard(self.test_set_manager, preset_file_list=current_files, parent=self)
        wizard.test_set_created.connect(lambda name: self._load_test_sets())
        wizard.exec()

    def _on_new_pipeline(self):
        """Create new pipeline."""
        # TODO: Open pipeline editor dialog
        logger.info("New pipeline creation - to be implemented")

    def _cleanup_previous_benchmark(self):
        """
        CORRECTION BUG #18: Cleanup previous benchmark to prevent memory leaks.

        Disconnects all signals and deletes previous runner object.
        """
        if self.runner:
            # Disconnect all runner signals
            try:
                self.runner.pipeline_progress.disconnect()
                self.runner.finished.disconnect()
                self.runner.error.disconnect()
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

        logger.debug("Previous benchmark resources cleaned up (SimplifiedBenchmarkWidget)")

    def _on_start_benchmark(self):
        """Start benchmark execution."""
        # CORRECTION BUG #18: Cleanup previous benchmark before starting new one
        self._cleanup_previous_benchmark()

        if not self.test_set_combo.currentData():
            logger.warning("No test set selected")
            return

        if not self.pipeline_combo.currentData():
            logger.warning("No pipeline selected")
            return

        # Get test set pairs
        test_set = self.test_set_combo.currentData()
        test_pairs = self.test_set_manager.get_test_set(test_set['name'])

        # Get pipeline config
        pipeline = self.pipeline_combo.currentData()

        # Create runner
        self.runner = BenchmarkRunner(
            self.db_manager,
            test_pairs,
            [pipeline],
            f"Run {test_set['name']} with {pipeline['name']}"
        )

        # Connect signals
        self.runner.pipeline_progress.connect(self._on_pipeline_progress)
        self.runner.finished.connect(self._on_benchmark_finished)
        self.runner.error.connect(self._on_benchmark_error)

        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setVisible(True)
        self.progress_group.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Démarrage...")

        # Start
        self.runner.start()
        logger.info(f"Benchmark started: {test_set['name']} with {pipeline['name']}")

    def _on_stop_benchmark(self):
        """Stop benchmark execution."""
        if self.runner:
            self.runner.stop()
            self.status_label.setText("Arrêt en cours...")
            logger.info("Benchmark stop requested")

    def _on_pipeline_progress(self, current, total, name):
        """Update progress."""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"Pipeline {current}/{total}: {name}")
        logger.debug(f"Progress: {current}/{total} - {name}")

    def _on_benchmark_finished(self, run_id):
        """Handle benchmark completion."""
        self.progress_bar.setValue(100)
        self.status_label.setText(f"✅ Terminé! Run #{run_id}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setVisible(False)

        # Reload results
        self._load_recent_results()

        self.benchmark_finished.emit(run_id)
        logger.info(f"Benchmark completed: run #{run_id}")

    def _on_benchmark_error(self, error_msg):
        """Handle benchmark error."""
        self.status_label.setText(f"❌ Erreur: {error_msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setVisible(False)
        self.progress_group.setVisible(False)
        logger.error(f"Benchmark error: {error_msg}")

    def _open_dashboard(self):
        """Open dashboard in separate window."""
        if not self._dashboard_window:
            self._dashboard_window = BenchmarkDashboardWindow(
                self.benchmark_manager,
                parent=self
            )

        self._dashboard_window.show()
        self._dashboard_window.raise_()
        self._dashboard_window.activateWindow()
        logger.info("Dashboard window opened")

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when widget is closed.

        Ensures proper memory cleanup when the widget is destroyed.
        """
        # Cleanup benchmark runner
        self._cleanup_previous_benchmark()

        # Close and cleanup dashboard window if open
        if self._dashboard_window:
            self._dashboard_window.close()
            self._dashboard_window.deleteLater()
            self._dashboard_window = None

        super().closeEvent(event)


class BenchmarkDashboardWindow(QDialog):
    """Fenêtre séparée pour le dashboard et l'analyse détaillée."""

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

        # Tabs for different views
        tabs = QTabWidget()

        # Tab 1: Monitoring Dashboard (métriques, graphiques)
        dashboard_tab = MonitoringDashboard(self.benchmark_manager, alert_system=None)
        tabs.addTab(dashboard_tab, "📈 Métriques & Graphiques")

        # Tab 2: History (historique détaillé)
        history_tab = self._create_history_tab()
        tabs.addTab(history_tab, "📜 Historique Détaillé")

        # Tab 3: Comparisons (comparaisons de runs)
        comparison_tab = self._create_comparison_tab()
        tabs.addTab(comparison_tab, "⚖️ Comparaisons")

        layout.addWidget(tabs)

    def _create_history_tab(self):
        """Create history tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # History table
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Run ID", "Test Set", "Pipelines", "Status", "Date", "Actions"
        ])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Load runs
        runs = self.benchmark_manager.list_benchmark_runs(limit=50)
        table.setRowCount(len(runs))

        for i, run in enumerate(runs):
            table.setItem(i, 0, QTableWidgetItem(str(run['id'])))
            table.setItem(i, 1, QTableWidgetItem(run['test_set_name']))
            table.setItem(i, 2, QTableWidgetItem(str(run['pipelines_count'])))
            table.setItem(i, 3, QTableWidgetItem(run.get('status', 'completed')))
            table.setItem(i, 4, QTableWidgetItem(run.get('created_at', 'N/A')))

        layout.addWidget(table)

        return widget

    def _create_comparison_tab(self):
        """Create comparison tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info_label = QLabel("Fonctionnalité de comparaison à implémenter")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #888; font-style: italic; padding: 50px;")
        layout.addWidget(info_label)

        return widget
