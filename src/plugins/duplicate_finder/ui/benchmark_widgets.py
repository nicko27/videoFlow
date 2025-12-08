"""
Benchmark UI Widgets - Interface pour le système de benchmark
"""
import os
from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QComboBox, QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QTabWidget, QScrollArea, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from src.core.logger import Logger
from ..managers import PipelineManager, TestSetManager, BenchmarkManager, BenchmarkRunner
from ..progress_widgets import ModernProgressWidget
from .test_set_wizard import TestSetWizard

# Matplotlib for visualizations
try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    FigureCanvas = None

logger = Logger.get_logger('DuplicateFinder.BenchmarkWidgets')
if not MATPLOTLIB_AVAILABLE:
    logger.warning("Matplotlib not available - benchmark visualizations disabled")


class PipelineEditorWidget(QWidget):
    """Widget pour créer et éditer des pipelines."""

    pipeline_saved = pyqtSignal(str)  # pipeline_name

    def __init__(self, pipeline_manager: PipelineManager):
        super().__init__()
        self.pipeline_manager = pipeline_manager
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("🔧 Gestion des Pipelines")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Pipeline list
        list_group = QGroupBox("Pipelines Disponibles")
        list_layout = QVBoxLayout()

        self.pipeline_list = QListWidget()
        self.pipeline_list.currentItemChanged.connect(self._on_pipeline_selected)
        list_layout.addWidget(self.pipeline_list)

        # Buttons
        btn_layout = QHBoxLayout()
        self.new_btn = QPushButton("➕ Nouveau")
        self.new_btn.clicked.connect(self._on_new_pipeline)
        self.duplicate_btn = QPushButton("📋 Dupliquer")
        self.duplicate_btn.clicked.connect(self._on_duplicate_pipeline)
        self.delete_btn = QPushButton("🗑️ Supprimer")
        self.delete_btn.clicked.connect(self._on_delete_pipeline)

        btn_layout.addWidget(self.new_btn)
        btn_layout.addWidget(self.duplicate_btn)
        btn_layout.addWidget(self.delete_btn)
        list_layout.addLayout(btn_layout)

        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        # Editor group
        editor_group = QGroupBox("Détails du Pipeline")
        editor_layout = QVBoxLayout()

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nom:"))
        self.name_input = QLineEdit()
        name_layout.addWidget(self.name_input)
        editor_layout.addLayout(name_layout)

        # Description
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(60)
        desc_layout.addWidget(self.desc_input)
        editor_layout.addLayout(desc_layout)

        # Mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["filtering", "weighting", "hybrid"])
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        editor_layout.addLayout(mode_layout)

        # Preset loader
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Charger un preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "-- Sélectionner --",
            "quick", "balanced", "accurate", "paranoid",
            "reencoded_basic", "reencoded_advanced",
            "lsh_only", "multi_resolution", "metadata_filter", "comprehensive"
        ])
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        editor_layout.addLayout(preset_layout)

        editor_group.setLayout(editor_layout)
        layout.addWidget(editor_group)

        # Methods configuration group
        methods_group = QGroupBox("Configuration des Méthodes de Vérification")
        methods_layout = QVBoxLayout()

        methods_info = QLabel(
            "ℹ️ Sélectionnez les méthodes à inclure dans le pipeline. "
            "L'ordre détermine la séquence d'exécution."
        )
        methods_info.setWordWrap(True)
        methods_info.setStyleSheet("color: #666; font-size: 11px;")
        methods_layout.addWidget(methods_info)

        # Methods checklist
        self.methods_table = QTableWidget()
        self.methods_table.setColumnCount(4)
        self.methods_table.setHorizontalHeaderLabels(["✓", "Méthode", "Description", "Ordre"])
        self.methods_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.methods_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.methods_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.methods_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.methods_table.setColumnWidth(0, 40)
        self.methods_table.setColumnWidth(3, 60)
        self.methods_table.setMaximumHeight(250)

        # Available methods
        self.available_methods = [
            ("color_histogram", "Histogramme couleur", "Compare la distribution des couleurs"),
            ("edge_pattern", "Détection contours", "Analyse les contours et formes"),
            ("motion_analysis", "Analyse mouvement", "Détecte les différences de mouvement"),
            ("dct_coefficients", "Coefficients DCT", "Transformée en cosinus discrète"),
            ("ssim", "SSIM", "Similarité structurelle d'image"),
            ("feature_matching", "Correspondance features", "Points d'intérêt SIFT/ORB"),
            ("strategy3", "Strategy 3 (Avancé)", "Stratégie avancée multi-critères")
        ]

        for row, (method, name, desc) in enumerate(self.available_methods):
            self.methods_table.insertRow(row)

            # Checkbox
            checkbox = QCheckBox()
            checkbox.setProperty("method_name", method)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.methods_table.setCellWidget(row, 0, checkbox_widget)

            # Method name
            self.methods_table.setItem(row, 1, QTableWidgetItem(name))

            # Description
            self.methods_table.setItem(row, 2, QTableWidgetItem(desc))

            # Order spinner
            order_spin = QSpinBox()
            order_spin.setRange(1, 10)
            order_spin.setValue(row + 1)
            order_spin.setEnabled(False)
            checkbox.toggled.connect(lambda checked, s=order_spin: s.setEnabled(checked))
            self.methods_table.setCellWidget(row, 3, order_spin)

        methods_layout.addWidget(self.methods_table)

        # Selection buttons
        select_btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("☑️ Tout sélectionner")
        select_all_btn.clicked.connect(self._select_all_methods)
        select_btn_layout.addWidget(select_all_btn)

        clear_all_btn = QPushButton("☐ Tout désélectionner")
        clear_all_btn.clicked.connect(self._clear_all_methods)
        select_btn_layout.addWidget(clear_all_btn)

        select_btn_layout.addStretch()
        methods_layout.addLayout(select_btn_layout)

        # Validation label
        self.validation_label = QLabel()
        self.validation_label.setStyleSheet("padding: 5px; border-radius: 3px;")
        methods_layout.addWidget(self.validation_label)

        methods_group.setLayout(methods_layout)
        layout.addWidget(methods_group)

        # Save button
        self.save_btn = QPushButton("💾 Sauvegarder Pipeline")
        self.save_btn.clicked.connect(self._on_save_pipeline)
        self.save_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        layout.addWidget(self.save_btn)

        # Load pipelines
        self._load_pipelines()

    def _load_pipelines(self):
        """Load available pipelines."""
        self.pipeline_list.clear()
        pipelines = self.pipeline_manager.list_pipelines(include_defaults=True)

        for pipeline in pipelines:
            item = QListWidgetItem()
            if pipeline['is_default']:
                item.setText(f"⭐ {pipeline['name']} (défaut)")
                item.setData(Qt.ItemDataRole.UserRole, pipeline)
                item.setForeground(QColor("#0066CC"))
            else:
                item.setText(f"👤 {pipeline['name']}")
                item.setData(Qt.ItemDataRole.UserRole, pipeline)

            self.pipeline_list.addItem(item)

    def _on_pipeline_selected(self, current, previous):
        """Handle pipeline selection."""
        if not current:
            return

        pipeline = current.data(Qt.ItemDataRole.UserRole)
        self.name_input.setText(pipeline['name'])
        self.desc_input.setText(pipeline['description'])
        self.mode_combo.setCurrentText(pipeline['mode'])

        # Disable editing for default pipelines
        is_default = pipeline['is_default']
        self.name_input.setEnabled(not is_default)
        self.desc_input.setEnabled(not is_default)
        self.mode_combo.setEnabled(not is_default)
        self.save_btn.setEnabled(not is_default)
        self.delete_btn.setEnabled(not is_default)

    def _on_new_pipeline(self):
        """Create new pipeline."""
        self.name_input.clear()
        self.desc_input.clear()
        self.mode_combo.setCurrentText("filtering")
        self.name_input.setEnabled(True)
        self.desc_input.setEnabled(True)
        self.mode_combo.setEnabled(True)
        self.save_btn.setEnabled(True)

    def _on_duplicate_pipeline(self):
        """Duplicate current pipeline."""
        current = self.pipeline_list.currentItem()
        if not current:
            return

        pipeline = current.data(Qt.ItemDataRole.UserRole)
        self.name_input.setText(f"{pipeline['name']} (copie)")
        self.desc_input.setText(pipeline['description'])
        self.mode_combo.setCurrentText(pipeline['mode'])
        self.name_input.setEnabled(True)
        self.desc_input.setEnabled(True)
        self.mode_combo.setEnabled(True)
        self.save_btn.setEnabled(True)

    def _on_delete_pipeline(self):
        """Delete current pipeline."""
        current = self.pipeline_list.currentItem()
        if not current:
            return

        pipeline = current.data(Qt.ItemDataRole.UserRole)
        if pipeline['is_default']:
            QMessageBox.warning(self, "Erreur", "Impossible de supprimer un pipeline par défaut")
            return

        reply = QMessageBox.question(
            self, "Confirmation",
            f"Supprimer le pipeline '{pipeline['name']}' ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.pipeline_manager.delete_pipeline(pipeline['id'])
            self._load_pipelines()

    def _on_preset_selected(self, preset_name: str):
        """Load a preset configuration."""
        if preset_name == "-- Sélectionner --":
            return

        config = self.pipeline_manager.get_protocol_config(preset_name)
        if not config:
            logger.warning(f"Preset '{preset_name}' not found")
            return

        # Update mode
        self.mode_combo.setCurrentText(config['mode'])

        # Update description
        if not self.desc_input.toPlainText() or "preset:" in self.desc_input.toPlainText():
            self.desc_input.setText(f"Basé sur preset: {preset_name}")

        # Update methods
        preset_methods = config.get('methods', [])
        self._clear_all_methods()

        for i, method_info in enumerate(preset_methods):
            method_name = method_info['method']

            # Find and check the corresponding checkbox
            for row in range(self.methods_table.rowCount()):
                checkbox_widget = self.methods_table.cellWidget(row, 0)
                checkbox = checkbox_widget.findChild(QCheckBox)

                if checkbox.property("method_name") == method_name:
                    checkbox.setChecked(True)

                    # Set order
                    order_spin = self.methods_table.cellWidget(row, 3)
                    if isinstance(order_spin, QSpinBox):
                        order_spin.setValue(i + 1)
                    break

        self._validate_pipeline()
        logger.info(f"Loaded preset '{preset_name}' with {len(preset_methods)} methods")

    def _select_all_methods(self):
        """Select all methods."""
        for row in range(self.methods_table.rowCount()):
            checkbox_widget = self.methods_table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            checkbox.setChecked(True)
        self._validate_pipeline()

    def _clear_all_methods(self):
        """Clear all method selections."""
        for row in range(self.methods_table.rowCount()):
            checkbox_widget = self.methods_table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            checkbox.setChecked(False)
        self._validate_pipeline()

    def _validate_pipeline(self):
        """Validate the current pipeline configuration."""
        selected_count = 0

        for row in range(self.methods_table.rowCount()):
            checkbox_widget = self.methods_table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox.isChecked():
                selected_count += 1

        if selected_count == 0:
            self.validation_label.setText("⚠️ Aucune méthode sélectionnée")
            self.validation_label.setStyleSheet("background-color: #FFEBEE; color: #C62828; padding: 5px; border-radius: 3px;")
            return False
        else:
            self.validation_label.setText(f"✅ Pipeline valide - {selected_count} méthode(s) configurée(s)")
            self.validation_label.setStyleSheet("background-color: #C8E6C9; color: #2E7D32; padding: 5px; border-radius: 3px;")
            return True

    def _get_selected_methods(self):
        """Get the list of selected methods with their configuration."""
        methods = []

        for row in range(self.methods_table.rowCount()):
            checkbox_widget = self.methods_table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)

            if checkbox.isChecked():
                method_name = checkbox.property("method_name")
                order_spin = self.methods_table.cellWidget(row, 3)
                order = order_spin.value() if isinstance(order_spin, QSpinBox) else row + 1

                methods.append({
                    'method': method_name,
                    'order': order,
                    'threshold': 70.0,  # Default threshold
                    'weight': 1.0  # Default weight
                })

        # Sort by order
        methods.sort(key=lambda x: x['order'])
        return methods

    def _on_save_pipeline(self):
        """Save pipeline."""
        name = self.name_input.text().strip()
        description = self.desc_input.toPlainText().strip()
        mode = self.mode_combo.currentText()

        if not name:
            QMessageBox.warning(self, "Erreur", "Le nom du pipeline est requis")
            return

        # Validate and get methods
        if not self._validate_pipeline():
            QMessageBox.warning(
                self, "Erreur",
                "Veuillez sélectionner au moins une méthode de vérification"
            )
            return

        methods = self._get_selected_methods()

        try:
            pipeline_id = self.pipeline_manager.save_pipeline(name, description, mode, methods)
            QMessageBox.information(
                self, "Succès",
                f"Pipeline '{name}' sauvegardé avec {len(methods)} méthode(s)\nID: {pipeline_id}"
            )
            self._load_pipelines()
            self.pipeline_saved.emit(name)

            # Reset preset selector
            self.preset_combo.setCurrentText("-- Sélectionner --")

        except ValueError as e:
            QMessageBox.warning(self, "Erreur", str(e))


class TestSetEditorWidget(QWidget):
    """Widget pour gérer les test sets."""

    test_set_changed = pyqtSignal(str)  # test_set_name

    def __init__(self, test_set_manager: TestSetManager):
        super().__init__()
        self.test_set_manager = test_set_manager
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("📋 Gestion des Test Sets")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Test set selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Test Set:"))
        self.test_set_combo = QComboBox()
        self.test_set_combo.currentTextChanged.connect(self._on_test_set_changed)
        selector_layout.addWidget(self.test_set_combo)

        self.wizard_btn = QPushButton("🧙 Assistant")
        self.wizard_btn.clicked.connect(self._on_open_wizard)
        self.wizard_btn.setToolTip("Ouvrir l'assistant de création de test set")
        self.wizard_btn.setStyleSheet("font-weight: bold;")
        selector_layout.addWidget(self.wizard_btn)

        self.new_set_btn = QPushButton("➕ Nouveau")
        self.new_set_btn.clicked.connect(self._on_new_test_set)
        selector_layout.addWidget(self.new_set_btn)

        self.delete_set_btn = QPushButton("🗑️ Supprimer")
        self.delete_set_btn.clicked.connect(self._on_delete_test_set)
        selector_layout.addWidget(self.delete_set_btn)

        layout.addLayout(selector_layout)

        # Import/Export buttons
        import_layout = QHBoxLayout()
        self.import_json_btn = QPushButton("📥 Importer JSON")
        self.import_json_btn.clicked.connect(self._on_import_json)
        import_layout.addWidget(self.import_json_btn)

        self.export_json_btn = QPushButton("📤 Exporter JSON")
        self.export_json_btn.clicked.connect(self._on_export_json)
        import_layout.addWidget(self.export_json_btn)

        import_layout.addStretch()
        layout.addLayout(import_layout)

        # Stats
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("background-color: #F0F0F0; padding: 8px; border-radius: 4px;")
        layout.addWidget(self.stats_label)

        # Pairs table
        self.pairs_table = QTableWidget()
        self.pairs_table.setColumnCount(5)
        self.pairs_table.setHorizontalHeaderLabels(["ID", "Vidéo 1", "Vidéo 2", "Attendu", "Notes"])
        self.pairs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.pairs_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.pairs_table)

        # Add pair button
        self.add_pair_btn = QPushButton("➕ Ajouter une paire")
        self.add_pair_btn.clicked.connect(self._on_add_pair)
        layout.addWidget(self.add_pair_btn)

        # Load test sets
        self._load_test_sets()

    def _load_test_sets(self):
        """Load available test sets."""
        self.test_set_combo.clear()
        test_sets = self.test_set_manager.list_test_sets()

        if not test_sets:
            self.test_set_combo.addItem("default")
        else:
            for ts in test_sets:
                self.test_set_combo.addItem(ts['name'])

    def _on_test_set_changed(self, test_set_name):
        """Handle test set change."""
        if not test_set_name:
            return

        # Load pairs
        pairs = self.test_set_manager.get_test_set(test_set_name)
        self.pairs_table.setRowCount(len(pairs))

        for row, pair in enumerate(pairs):
            self.pairs_table.setItem(row, 0, QTableWidgetItem(str(pair['id'])))
            self.pairs_table.setItem(row, 1, QTableWidgetItem(os.path.basename(pair['video1_path'])))
            self.pairs_table.setItem(row, 2, QTableWidgetItem(os.path.basename(pair['video2_path'])))
            self.pairs_table.setItem(row, 3, QTableWidgetItem(pair['expected']))
            self.pairs_table.setItem(row, 4, QTableWidgetItem(pair['notes'] or ''))

        # Update stats
        stats = self.test_set_manager.get_stats(test_set_name)
        self.stats_label.setText(
            f"Total: {stats['total']} paires | "
            f"✅ Positives: {stats['positives']} | "
            f"❌ Négatives: {stats['negatives']} | "
            f"❓ Inconnues: {stats['unknowns']}"
        )

        self.test_set_changed.emit(test_set_name)

    def _on_new_test_set(self):
        """Create new test set."""
        name, ok = QInputDialog.getText(self, "Nouveau Test Set", "Nom du test set:")
        if ok and name:
            self.test_set_combo.addItem(name)
            self.test_set_combo.setCurrentText(name)

    def _on_delete_test_set(self):
        """Delete current test set."""
        test_set_name = self.test_set_combo.currentText()
        if not test_set_name:
            return

        reply = QMessageBox.question(
            self, "Confirmation",
            f"Supprimer le test set '{test_set_name}' et toutes ses paires ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            count = self.test_set_manager.delete_test_set(test_set_name)
            QMessageBox.information(self, "Succès", f"{count} paires supprimées")
            self._load_test_sets()

    def _on_import_json(self):
        """Import from pairs.json."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Importer pairs.json", "", "JSON Files (*.json)"
        )

        if file_path:
            test_set_name = self.test_set_combo.currentText()
            count = self.test_set_manager.import_from_pairs_json(file_path, test_set_name)
            QMessageBox.information(self, "Succès", f"{count} paires importées")
            self._on_test_set_changed(test_set_name)

    def _on_export_json(self):
        """Export to pairs.json."""
        test_set_name = self.test_set_combo.currentText()
        if not test_set_name:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter vers JSON", f"{test_set_name}.json", "JSON Files (*.json)"
        )

        if file_path:
            self.test_set_manager.export_to_pairs_json(test_set_name, file_path)
            QMessageBox.information(self, "Succès", "Export réussi")

    def _on_add_pair(self):
        """Add a new pair."""
        QMessageBox.information(self, "Info", "Fonctionnalité à implémenter: dialogue d'ajout de paire")

    def _on_open_wizard(self):
        """Open the test set creation wizard."""
        wizard = TestSetWizard(self.test_set_manager, self)
        wizard.test_set_created.connect(self._on_wizard_completed)
        wizard.exec()

    def _on_wizard_completed(self, test_set_name: str):
        """Handle wizard completion."""
        self._load_test_sets()
        self.test_set_combo.setCurrentText(test_set_name)
        logger.info(f"Test set '{test_set_name}' created via wizard")


class BenchmarkBatchWidget(QWidget):
    """Widget pour exécuter des benchmarks batch."""

    benchmark_finished = pyqtSignal(int)  # run_id

    def __init__(
        self,
        benchmark_manager: BenchmarkManager,
        pipeline_manager: PipelineManager,
        test_set_manager: TestSetManager,
        db_manager
    ):
        super().__init__()
        self.benchmark_manager = benchmark_manager
        self.pipeline_manager = pipeline_manager
        self.test_set_manager = test_set_manager
        self.db_manager = db_manager
        self.runner: Optional[BenchmarkRunner] = None
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("🧪 Benchmark Batch")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Configuration group
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()

        # Test set selector
        ts_layout = QHBoxLayout()
        ts_layout.addWidget(QLabel("Test Set:"))
        self.test_set_combo = QComboBox()
        ts_layout.addWidget(self.test_set_combo)
        config_layout.addLayout(ts_layout)

        # Run label
        label_layout = QHBoxLayout()
        label_layout.addWidget(QLabel("Label du run:"))
        self.run_label_input = QLineEdit()
        self.run_label_input.setPlaceholderText("Ex: Test comparative v1.0")
        label_layout.addWidget(self.run_label_input)
        config_layout.addLayout(label_layout)

        # Pipeline selection
        config_layout.addWidget(QLabel("Pipelines à tester:"))
        self.pipeline_list = QListWidget()
        self.pipeline_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        config_layout.addWidget(self.pipeline_list)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Progress group
        progress_group = QGroupBox("Progression")
        progress_layout = QVBoxLayout()

        self.pipeline_progress = ModernProgressWidget("🔧 Pipeline progress")
        self.pipeline_progress.setVisible(False)
        progress_layout.addWidget(self.pipeline_progress)

        self.pair_progress = ModernProgressWidget("📹 Test pairs progress")
        self.pair_progress.setVisible(False)
        progress_layout.addWidget(self.pair_progress)

        self.status_label = QLabel()
        progress_layout.addWidget(self.status_label)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Control buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶️ Démarrer")
        self.start_btn.clicked.connect(self._on_start_benchmark)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹️ Arrêter")
        self.stop_btn.clicked.connect(self._on_stop_benchmark)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)

        # Load data
        self._load_test_sets()
        self._load_pipelines()

    def _load_test_sets(self):
        """Load test sets."""
        self.test_set_combo.clear()
        test_sets = self.test_set_manager.list_test_sets()
        for ts in test_sets:
            self.test_set_combo.addItem(ts['name'])

    def _load_pipelines(self):
        """Load pipelines."""
        self.pipeline_list.clear()
        pipelines = self.pipeline_manager.list_pipelines(include_defaults=True)
        for pipeline in pipelines:
            item = QListWidgetItem(pipeline['name'])
            item.setData(Qt.ItemDataRole.UserRole, pipeline)
            self.pipeline_list.addItem(item)

    def _on_start_benchmark(self):
        """Start benchmark."""
        # Validation
        test_set_name = self.test_set_combo.currentText()
        if not test_set_name:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un test set")
            return

        selected_items = self.pipeline_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Erreur", "Sélectionnez au moins un pipeline")
            return

        run_label = self.run_label_input.text().strip()
        if not run_label:
            QMessageBox.warning(self, "Erreur", "Entrez un label pour le run")
            return

        # Get test pairs
        test_pairs = self.test_set_manager.get_test_set(test_set_name)
        if not test_pairs:
            QMessageBox.warning(self, "Erreur", "Aucune paire dans ce test set")
            return

        # Get pipeline configs
        pipeline_configs = []
        for item in selected_items:
            pipeline = item.data(Qt.ItemDataRole.UserRole)
            pipeline_configs.append(pipeline)

        # Create runner
        self.runner = BenchmarkRunner(
            self.db_manager,
            test_pairs,
            pipeline_configs,
            run_label
        )

        # Connect signals
        self.runner.pipeline_progress.connect(self._on_pipeline_progress)
        self.runner.pair_progress.connect(self._on_pair_progress)
        self.runner.pipeline_completed.connect(self._on_pipeline_completed)
        self.runner.finished.connect(self._on_benchmark_finished)
        self.runner.error.connect(self._on_benchmark_error)

        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pipeline_progress.setVisible(True)
        self.pair_progress.setVisible(True)

        # Start
        self.runner.start()
        logger.info(f"Benchmark démarré: {len(pipeline_configs)} pipelines, {len(test_pairs)} paires")

    def _on_stop_benchmark(self):
        """Stop benchmark."""
        if self.runner:
            self.runner.stop()
            self.status_label.setText("⏹️ Arrêt en cours...")

    def _on_pipeline_progress(self, current, total, name):
        """Update pipeline progress."""
        self.pipeline_progress.update_progress(current, total)
        self.status_label.setText(f"Pipeline {current}/{total}: {name}")

    def _on_pair_progress(self, current, total, video1, video2):
        """Update pair progress."""
        self.pair_progress.update_progress(current, total)

    def _on_pipeline_completed(self, name, results):
        """Handle pipeline completion."""
        logger.info(f"Pipeline '{name}' terminé: F1={results['f1_score']:.2f}%")

    def _on_benchmark_finished(self, run_id):
        """Handle benchmark completion."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pipeline_progress.setVisible(False)
        self.pair_progress.setVisible(False)
        self.status_label.setText(f"✅ Benchmark terminé (Run ID: {run_id})")

        QMessageBox.information(self, "Succès", f"Benchmark terminé!\nRun ID: {run_id}")
        self.benchmark_finished.emit(run_id)

    def _on_benchmark_error(self, error_msg):
        """Handle benchmark error."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pipeline_progress.setVisible(False)
        self.pair_progress.setVisible(False)
        self.status_label.setText(f"❌ Erreur: {error_msg}")

        QMessageBox.critical(self, "Erreur", f"Erreur durant le benchmark:\n{error_msg}")


class BenchmarkResultsWidget(QWidget):
    """Widget pour afficher les résultats comparatifs."""

    def __init__(self, benchmark_manager: BenchmarkManager):
        super().__init__()
        self.benchmark_manager = benchmark_manager
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("📊 Résultats Comparatifs")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Run selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Benchmark Run:"))
        self.run_combo = QComboBox()
        self.run_combo.currentIndexChanged.connect(self._on_run_changed)
        selector_layout.addWidget(self.run_combo)

        self.refresh_btn = QPushButton("🔄 Actualiser")
        self.refresh_btn.clicked.connect(self._load_runs)
        selector_layout.addWidget(self.refresh_btn)

        # View toggle
        self.show_charts_btn = QPushButton("📊 Graphiques")
        self.show_charts_btn.setCheckable(True)
        self.show_charts_btn.setChecked(MATPLOTLIB_AVAILABLE)
        self.show_charts_btn.toggled.connect(self._toggle_charts)
        self.show_charts_btn.setEnabled(MATPLOTLIB_AVAILABLE)
        if not MATPLOTLIB_AVAILABLE:
            self.show_charts_btn.setToolTip("Matplotlib non disponible")
        selector_layout.addWidget(self.show_charts_btn)

        # Export menu
        export_btn = QPushButton("📤 Exporter")
        export_menu = QComboBox()
        export_menu.addItems(["-- Format --", "CSV", "JSON", "PDF (si disponible)"])
        export_menu.currentTextChanged.connect(self._on_export_selected)
        selector_layout.addWidget(QLabel("Export:"))
        selector_layout.addWidget(export_menu)

        selector_layout.addStretch()
        layout.addLayout(selector_layout)

        # Store current results for export
        self.current_results = []
        self.current_run_info = None

        # Create tab widget for table and charts
        self.view_tabs = QTabWidget()

        # Table view
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(9)
        self.results_table.setHorizontalHeaderLabels([
            "Pipeline", "TP", "FP", "TN", "FN", "Précision %", "Rappel %", "F1 %", "Temps (s)"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        table_layout.addWidget(self.results_table)
        self.view_tabs.addTab(table_widget, "📋 Tableau")

        # Charts view
        if MATPLOTLIB_AVAILABLE:
            charts_widget = QWidget()
            charts_layout = QVBoxLayout(charts_widget)

            # Create 2x2 grid for charts
            top_charts = QHBoxLayout()
            bottom_charts = QHBoxLayout()

            # Precision chart
            self.precision_canvas = self._create_chart_canvas()
            top_charts.addWidget(self.precision_canvas)

            # Recall chart
            self.recall_canvas = self._create_chart_canvas()
            top_charts.addWidget(self.recall_canvas)

            charts_layout.addLayout(top_charts)

            # F1 chart
            self.f1_canvas = self._create_chart_canvas()
            bottom_charts.addWidget(self.f1_canvas)

            # Time chart
            self.time_canvas = self._create_chart_canvas()
            bottom_charts.addWidget(self.time_canvas)

            charts_layout.addLayout(bottom_charts)
            self.view_tabs.addTab(charts_widget, "📊 Graphiques")

        layout.addWidget(self.view_tabs)

        # Load runs
        self._load_runs()

    def _load_runs(self):
        """Load benchmark runs."""
        self.run_combo.clear()
        runs = self.benchmark_manager.list_benchmark_runs(limit=50)

        for run in runs:
            label = f"{run['run_label']} - {run['created_at'][:10]} ({run['pipelines_count']} pipelines)"
            self.run_combo.addItem(label, run['id'])

    def _on_run_changed(self, index):
        """Handle run selection change."""
        if index < 0:
            return

        run_id = self.run_combo.itemData(index)
        self._load_results(run_id)

    def _load_results(self, run_id: int):
        """Load results for a run."""
        results = self.benchmark_manager.get_benchmark_results(run_id)

        # Store for export
        self.current_results = results
        self.current_run_info = {
            'id': run_id,
            'label': self.run_combo.currentText()
        }

        self.results_table.setRowCount(len(results))

        for row, result in enumerate(results):
            self.results_table.setItem(row, 0, QTableWidgetItem(result['pipeline_name']))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(result['tp'])))
            self.results_table.setItem(row, 2, QTableWidgetItem(str(result['fp'])))
            self.results_table.setItem(row, 3, QTableWidgetItem(str(result['tn'])))
            self.results_table.setItem(row, 4, QTableWidgetItem(str(result['fn'])))
            self.results_table.setItem(row, 5, QTableWidgetItem(f"{result['precision']:.2f}"))
            self.results_table.setItem(row, 6, QTableWidgetItem(f"{result['recall']:.2f}"))
            self.results_table.setItem(row, 7, QTableWidgetItem(f"{result['f1_score']:.2f}"))
            self.results_table.setItem(row, 8, QTableWidgetItem(f"{result['total_time']:.1f}"))

            # Highlight best F1 score
            if row == 0:  # Results are ordered by F1 DESC
                for col in range(9):
                    item = self.results_table.item(row, col)
                    if item:
                        item.setBackground(QColor("#C8E6C9"))  # Light green

        # Update charts if available
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'precision_canvas'):
            self._update_charts(results)

    def _create_chart_canvas(self):
        """Create a matplotlib canvas for charts."""
        if not MATPLOTLIB_AVAILABLE:
            return QLabel("Matplotlib non disponible")

        fig = Figure(figsize=(5, 4), dpi=100)
        canvas = FigureCanvas(fig)
        return canvas

    def _toggle_charts(self, checked):
        """Toggle between table and charts view."""
        if checked and MATPLOTLIB_AVAILABLE:
            self.view_tabs.setCurrentIndex(1)  # Charts tab
        else:
            self.view_tabs.setCurrentIndex(0)  # Table tab

    def _update_charts(self, results: List[Dict]):
        """Update all charts with benchmark results."""
        if not results or not MATPLOTLIB_AVAILABLE:
            return

        # Extract data
        pipeline_names = [r['pipeline_name'] for r in results]
        precisions = [r['precision'] for r in results]
        recalls = [r['recall'] for r in results]
        f1_scores = [r['f1_score'] for r in results]
        times = [r['total_time'] for r in results]

        # Truncate long names
        display_names = [name[:15] + '...' if len(name) > 15 else name for name in pipeline_names]

        # Update precision chart
        self._update_bar_chart(
            self.precision_canvas,
            display_names,
            precisions,
            "Précision (%)",
            "#4CAF50",  # Green
            "Précision par Pipeline"
        )

        # Update recall chart
        self._update_bar_chart(
            self.recall_canvas,
            display_names,
            recalls,
            "Rappel (%)",
            "#2196F3",  # Blue
            "Rappel par Pipeline"
        )

        # Update F1 chart
        self._update_bar_chart(
            self.f1_canvas,
            display_names,
            f1_scores,
            "Score F1 (%)",
            "#FF9800",  # Orange
            "Score F1 par Pipeline"
        )

        # Update time chart
        self._update_bar_chart(
            self.time_canvas,
            display_names,
            times,
            "Temps (s)",
            "#9C27B0",  # Purple
            "Temps d'Exécution par Pipeline"
        )

    def _update_bar_chart(self, canvas, labels, values, ylabel, color, title):
        """Update a bar chart with new data."""
        if not MATPLOTLIB_AVAILABLE:
            return

        # Clear previous plot
        canvas.figure.clear()

        # Create subplot
        ax = canvas.figure.add_subplot(111)

        # Create bar chart
        bars = ax.bar(range(len(labels)), values, color=color, alpha=0.7, edgecolor='black')

        # Highlight best value
        if values:
            best_idx = values.index(max(values))
            bars[best_idx].set_color('#FFC107')  # Amber for best
            bars[best_idx].set_edgecolor('red')
            bars[best_idx].set_linewidth(2)

        # Customize
        ax.set_xlabel('Pipeline')
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontweight='bold')
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        # Add value labels on bars
        for i, (bar, value) in enumerate(zip(bars, values)):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.,
                height,
                f'{value:.1f}',
                ha='center',
                va='bottom',
                fontsize=9
            )

        # Tight layout
        canvas.figure.tight_layout()

        # Refresh canvas
        canvas.draw()

    def _on_export_selected(self, format_name: str):
        """Handle export format selection."""
        if format_name == "-- Format --":
            return

        if not self.current_results:
            QMessageBox.warning(self, "Erreur", "Aucun résultat à exporter. Sélectionnez d'abord un benchmark run.")
            return

        # Get file path
        if format_name == "CSV":
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Exporter en CSV",
                f"benchmark_results_{self.current_run_info['id']}.csv",
                "CSV Files (*.csv)"
            )
            if file_path:
                self._export_csv(file_path)

        elif format_name == "JSON":
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Exporter en JSON",
                f"benchmark_results_{self.current_run_info['id']}.json",
                "JSON Files (*.json)"
            )
            if file_path:
                self._export_json(file_path)

        elif format_name == "PDF (si disponible)":
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Exporter en PDF",
                f"benchmark_report_{self.current_run_info['id']}.pdf",
                "PDF Files (*.pdf)"
            )
            if file_path:
                self._export_pdf(file_path)

    def _export_csv(self, file_path: str):
        """Export results to CSV."""
        try:
            import csv

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow([
                    "Pipeline", "TP", "FP", "TN", "FN",
                    "Precision (%)", "Recall (%)", "F1 Score (%)", "Time (s)"
                ])

                # Data
                for result in self.current_results:
                    writer.writerow([
                        result['pipeline_name'],
                        result['tp'],
                        result['fp'],
                        result['tn'],
                        result['fn'],
                        f"{result['precision']:.2f}",
                        f"{result['recall']:.2f}",
                        f"{result['f1_score']:.2f}",
                        f"{result['total_time']:.2f}"
                    ])

            QMessageBox.information(self, "Succès", f"Résultats exportés vers:\n{file_path}")
            logger.info(f"Exported {len(self.current_results)} results to CSV: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export CSV:\n{str(e)}")
            logger.error(f"CSV export error: {e}", exc_info=True)

    def _export_json(self, file_path: str):
        """Export results to JSON."""
        try:
            import json
            from datetime import datetime

            export_data = {
                'metadata': {
                    'run_id': self.current_run_info['id'],
                    'run_label': self.current_run_info['label'],
                    'export_date': datetime.now().isoformat(),
                    'total_pipelines': len(self.current_results)
                },
                'results': []
            }

            for result in self.current_results:
                export_data['results'].append({
                    'pipeline_name': result['pipeline_name'],
                    'confusion_matrix': {
                        'true_positives': result['tp'],
                        'false_positives': result['fp'],
                        'true_negatives': result['tn'],
                        'false_negatives': result['fn']
                    },
                    'metrics': {
                        'precision': round(result['precision'], 2),
                        'recall': round(result['recall'], 2),
                        'f1_score': round(result['f1_score'], 2)
                    },
                    'performance': {
                        'total_time_seconds': round(result['total_time'], 2)
                    }
                })

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            QMessageBox.information(self, "Succès", f"Résultats exportés vers:\n{file_path}")
            logger.info(f"Exported {len(self.current_results)} results to JSON: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export JSON:\n{str(e)}")
            logger.error(f"JSON export error: {e}", exc_info=True)

    def _export_pdf(self, file_path: str):
        """Export results to PDF report."""
        try:
            # Try to use reportlab if available
            try:
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import letter, A4
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.lib.units import inch
                from datetime import datetime

                # Create PDF
                doc = SimpleDocTemplate(file_path, pagesize=A4)
                elements = []
                styles = getSampleStyleSheet()

                # Title
                title = Paragraph(
                    f"<b>Benchmark Report</b><br/>{self.current_run_info['label']}",
                    styles['Title']
                )
                elements.append(title)
                elements.append(Spacer(1, 0.3*inch))

                # Metadata
                meta_text = f"<b>Export Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
                meta_text += f"<b>Run ID:</b> {self.current_run_info['id']}<br/>"
                meta_text += f"<b>Total Pipelines:</b> {len(self.current_results)}"
                meta = Paragraph(meta_text, styles['Normal'])
                elements.append(meta)
                elements.append(Spacer(1, 0.3*inch))

                # Results table
                table_data = [
                    ['Pipeline', 'TP', 'FP', 'TN', 'FN', 'Prec%', 'Rec%', 'F1%', 'Time(s)']
                ]

                for result in self.current_results:
                    table_data.append([
                        result['pipeline_name'][:20],
                        str(result['tp']),
                        str(result['fp']),
                        str(result['tn']),
                        str(result['fn']),
                        f"{result['precision']:.1f}",
                        f"{result['recall']:.1f}",
                        f"{result['f1_score']:.1f}",
                        f"{result['total_time']:.1f}"
                    ])

                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                ]))

                # Highlight best F1 score
                if self.current_results:
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgreen),
                    ]))

                elements.append(table)

                # Build PDF
                doc.build(elements)

                QMessageBox.information(self, "Succès", f"Rapport PDF généré:\n{file_path}")
                logger.info(f"Exported {len(self.current_results)} results to PDF: {file_path}")

            except ImportError:
                # Fallback: Simple text-based PDF using matplotlib
                if MATPLOTLIB_AVAILABLE:
                    self._export_pdf_matplotlib(file_path)
                else:
                    QMessageBox.warning(
                        self, "Module manquant",
                        "L'export PDF nécessite 'reportlab' ou 'matplotlib'.\n"
                        "Installez avec: pip install reportlab"
                    )

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export PDF:\n{str(e)}")
            logger.error(f"PDF export error: {e}", exc_info=True)

    def _export_pdf_matplotlib(self, file_path: str):
        """Fallback PDF export using matplotlib."""
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        from datetime import datetime

        with PdfPages(file_path) as pdf:
            # Page 1: Table
            fig, ax = plt.subplots(figsize=(11, 8))
            ax.axis('tight')
            ax.axis('off')

            # Title
            fig.suptitle(
                f"Benchmark Report\n{self.current_run_info['label']}\n"
                f"Export: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                fontsize=14, fontweight='bold'
            )

            # Table data
            table_data = [['Pipeline', 'TP', 'FP', 'TN', 'FN', 'Prec%', 'Rec%', 'F1%', 'Time(s)']]
            for result in self.current_results:
                table_data.append([
                    result['pipeline_name'][:20],
                    result['tp'],
                    result['fp'],
                    result['tn'],
                    result['fn'],
                    f"{result['precision']:.1f}",
                    f"{result['recall']:.1f}",
                    f"{result['f1_score']:.1f}",
                    f"{result['total_time']:.1f}"
                ])

            table = ax.table(cellText=table_data, cellLoc='center', loc='center')
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1, 2)

            # Style header
            for i in range(len(table_data[0])):
                table[(0, i)].set_facecolor('#CCCCCC')
                table[(0, i)].set_text_props(weight='bold')

            pdf.savefig(fig, bbox_inches='tight')
            plt.close()

        QMessageBox.information(self, "Succès", f"Rapport PDF généré:\n{file_path}")
        logger.info(f"Exported {len(self.current_results)} results to PDF (matplotlib): {file_path}")


class BenchmarkHistoryWidget(QWidget):
    """Widget pour l'historique et la comparaison de benchmarks."""

    def __init__(self, benchmark_manager: BenchmarkManager):
        super().__init__()
        self.benchmark_manager = benchmark_manager
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("📜 Historique des Benchmarks")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Toolbar
        toolbar_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("🔄 Actualiser")
        self.refresh_btn.clicked.connect(self._load_history)
        toolbar_layout.addWidget(self.refresh_btn)

        self.compare_btn = QPushButton("📊 Comparer Sélectionnés")
        self.compare_btn.clicked.connect(self._on_compare_runs)
        toolbar_layout.addWidget(self.compare_btn)

        self.delete_btn = QPushButton("🗑️ Supprimer")
        self.delete_btn.clicked.connect(self._on_delete_run)
        toolbar_layout.addWidget(self.delete_btn)

        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)

        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "ID", "Label", "Date", "Pipelines", "Test Set", "Meilleur F1 %"
        ])
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.history_table)

        # Stats label
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("background-color: #F0F0F0; padding: 8px; border-radius: 4px;")
        layout.addWidget(self.stats_label)

        # Load history
        self._load_history()

    def _load_history(self):
        """Load benchmark history."""
        runs = self.benchmark_manager.list_benchmark_runs(limit=100)
        self.history_table.setRowCount(len(runs))

        for row, run in enumerate(runs):
            self.history_table.setItem(row, 0, QTableWidgetItem(str(run['id'])))
            self.history_table.setItem(row, 1, QTableWidgetItem(run['run_label']))
            self.history_table.setItem(row, 2, QTableWidgetItem(run['created_at'][:19]))
            self.history_table.setItem(row, 3, QTableWidgetItem(str(run['pipelines_count'])))
            self.history_table.setItem(row, 4, QTableWidgetItem(run.get('test_set_name', 'N/A')))

            # Get best F1 score for this run
            results = self.benchmark_manager.get_benchmark_results(run['id'])
            best_f1 = max([r['f1_score'] for r in results]) if results else 0.0
            self.history_table.setItem(row, 5, QTableWidgetItem(f"{best_f1:.2f}"))

        self.stats_label.setText(f"Total: {len(runs)} benchmark runs")

    def _on_compare_runs(self):
        """Compare selected runs."""
        selected_rows = set(item.row() for item in self.history_table.selectedItems())

        if len(selected_rows) < 2:
            QMessageBox.warning(self, "Erreur", "Sélectionnez au moins 2 runs à comparer")
            return

        run_ids = [int(self.history_table.item(row, 0).text()) for row in selected_rows]

        # Create comparison dialog
        msg = f"Comparaison de {len(run_ids)} runs:\n"
        for run_id in run_ids:
            results = self.benchmark_manager.get_benchmark_results(run_id)
            if results:
                best_f1 = max([r['f1_score'] for r in results])
                avg_f1 = sum([r['f1_score'] for r in results]) / len(results)
                msg += f"\nRun {run_id}: Best F1={best_f1:.2f}%, Avg F1={avg_f1:.2f}%"

        QMessageBox.information(self, "Comparaison", msg)

    def _on_delete_run(self):
        """Delete selected run."""
        selected_rows = set(item.row() for item in self.history_table.selectedItems())

        if not selected_rows:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un run à supprimer")
            return

        reply = QMessageBox.question(
            self, "Confirmation",
            f"Supprimer {len(selected_rows)} run(s) ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for row in selected_rows:
                run_id = int(self.history_table.item(row, 0).text())
                self.benchmark_manager.delete_benchmark_run(run_id)

            self._load_history()
            QMessageBox.information(self, "Succès", f"{len(selected_rows)} run(s) supprimé(s)")


class BenchmarkTabWidget(QWidget):
    """Widget principal contenant tous les widgets de benchmark dans des onglets."""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager

        # Create managers
        self.pipeline_manager = PipelineManager(db_manager)
        self.test_set_manager = TestSetManager(db_manager)
        self.benchmark_manager = BenchmarkManager(db_manager)

        self._init_ui()

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar with quick actions
        toolbar = QWidget()
        toolbar.setStyleSheet("background-color: #F5F5F5; border-bottom: 1px solid #DDDDDD;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)

        toolbar_label = QLabel("🧪 <b>Système de Benchmark</b>")
        toolbar_layout.addWidget(toolbar_label)

        toolbar_layout.addStretch()

        # Quick action buttons
        quick_new_test_btn = QPushButton("➕ Nouveau Test Set")
        quick_new_test_btn.clicked.connect(self._quick_new_test_set)
        quick_new_test_btn.setToolTip("Créer rapidement un nouveau test set")
        toolbar_layout.addWidget(quick_new_test_btn)

        quick_new_pipeline_btn = QPushButton("🔧 Nouveau Pipeline")
        quick_new_pipeline_btn.clicked.connect(self._quick_new_pipeline)
        quick_new_pipeline_btn.setToolTip("Créer rapidement un nouveau pipeline")
        toolbar_layout.addWidget(quick_new_pipeline_btn)

        quick_run_btn = QPushButton("▶️ Lancer Benchmark")
        quick_run_btn.clicked.connect(self._quick_run_benchmark)
        quick_run_btn.setToolTip("Aller directement à l'onglet Benchmark")
        toolbar_layout.addWidget(quick_run_btn)

        layout.addWidget(toolbar)

        # Create tab widget
        self.tabs = QTabWidget()

        # REORDERED TABS - Test Sets first as per TASK 3.1
        # Tab 1: Test sets (PRIMARY - users need data first)
        self.test_set_widget = TestSetEditorWidget(self.test_set_manager)
        self.tabs.addTab(self.test_set_widget, "📋 Test Sets")

        # Tab 2: Pipelines (SECONDARY - configure what to test)
        self.pipeline_widget = PipelineEditorWidget(self.pipeline_manager)
        self.tabs.addTab(self.pipeline_widget, "🔧 Pipelines")

        # Tab 3: Benchmark batch (ACTION - run the tests)
        self.benchmark_widget = BenchmarkBatchWidget(
            self.benchmark_manager,
            self.pipeline_manager,
            self.test_set_manager,
            self.db_manager
        )
        self.tabs.addTab(self.benchmark_widget, "🧪 Exécution")

        # Tab 4: Results (RESULTS - view current results)
        self.results_widget = BenchmarkResultsWidget(self.benchmark_manager)
        self.tabs.addTab(self.results_widget, "📊 Résultats")

        # Tab 5: History (NEW - compare past runs)
        self.history_widget = BenchmarkHistoryWidget(self.benchmark_manager)
        self.tabs.addTab(self.history_widget, "📜 Historique")

        layout.addWidget(self.tabs)

        # Connect signals
        self.benchmark_widget.benchmark_finished.connect(self._on_benchmark_finished)
        self.pipeline_widget.pipeline_saved.connect(self._on_pipeline_saved)
        self.test_set_widget.test_set_changed.connect(self._on_test_set_changed)

    def _on_benchmark_finished(self, run_id):
        """Handle benchmark completion."""
        self.results_widget._load_runs()
        self.history_widget._load_history()
        logger.info(f"Benchmark run {run_id} finished and results updated")

    def _on_pipeline_saved(self, pipeline_name):
        """Handle pipeline save."""
        self.benchmark_widget._load_pipelines()
        logger.info(f"Pipeline '{pipeline_name}' saved and benchmark list updated")

    def _on_test_set_changed(self, test_set_name):
        """Handle test set change."""
        self.benchmark_widget._load_test_sets()
        logger.info(f"Test set '{test_set_name}' changed")

    def _quick_new_test_set(self):
        """Quick action: create new test set."""
        self.tabs.setCurrentWidget(self.test_set_widget)
        self.test_set_widget._on_new_test_set()

    def _quick_new_pipeline(self):
        """Quick action: create new pipeline."""
        self.tabs.setCurrentWidget(self.pipeline_widget)
        self.pipeline_widget._on_new_pipeline()

    def _quick_run_benchmark(self):
        """Quick action: go to benchmark tab."""
        self.tabs.setCurrentWidget(self.benchmark_widget)
