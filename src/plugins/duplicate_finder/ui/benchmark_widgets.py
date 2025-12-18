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
from ..orchestration.pipeline_manager import PipelineManager
from ..services.test_set_manager import TestSetManager
from ..services.benchmark_manager import BenchmarkManager, BenchmarkRunner
from .widgets.progress_widgets import ModernProgressWidget
from .test_set_wizard import TestSetWizard

# Matplotlib for visualizations
try:
    import matplotlib
    # CORRECTION BUG #19: Utiliser QtAgg (universel PyQt5/PyQt6) au lieu de Qt5Agg
    matplotlib.use('QtAgg')
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    FigureCanvas = None

logger = Logger.get_logger('DuplicateFinder.BenchmarkWidgets')
if not MATPLOTLIB_AVAILABLE:
    logger.warning("Matplotlib not available - benchmark visualizations disabled")


class ConfusionMatrixWidget(QWidget):
    """
    Interactive confusion matrix visualization.

    Features:
        - 2x2 matrix display (TP, FP, TN, FN)
        - Clickable cells to view specific pairs
        - Color-coded cells (green for correct, red for errors)
        - Percentages and absolute values
        - Hover tooltips with details

    Signals:
        cell_clicked(str, list): Emitted when cell clicked (cell_type, pairs_list)
    """

    cell_clicked = pyqtSignal(str, list)  # (cell_type, pairs)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.confusion_data = {'TP': 0, 'FP': 0, 'TN': 0, 'FN': 0}
        self.results = []
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("📊 <b>Matrice de Confusion</b>")
        title.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(title)

        # Matrix grid
        grid_widget = QWidget()
        grid_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        grid_layout = QVBoxLayout(grid_widget)
        grid_layout.setSpacing(2)
        grid_layout.setContentsMargins(20, 20, 20, 20)

        # Header row
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel(""))  # Top-left empty
        header_layout.addWidget(self._create_header_label("Prédit: Duplicate"))
        header_layout.addWidget(self._create_header_label("Prédit: Not Duplicate"))
        grid_layout.addLayout(header_layout)

        # Row 1: Actual Duplicate
        row1_layout = QHBoxLayout()
        row1_layout.addWidget(self._create_header_label("Réel: Duplicate"))

        self.tp_cell = self._create_matrix_cell("TP", "True Positives", "#4CAF50")
        row1_layout.addWidget(self.tp_cell)

        self.fn_cell = self._create_matrix_cell("FN", "False Negatives", "#F44336")
        row1_layout.addWidget(self.fn_cell)

        grid_layout.addLayout(row1_layout)

        # Row 2: Actual Not Duplicate
        row2_layout = QHBoxLayout()
        row2_layout.addWidget(self._create_header_label("Réel: Not Duplicate"))

        self.fp_cell = self._create_matrix_cell("FP", "False Positives", "#FF9800")
        row2_layout.addWidget(self.fp_cell)

        self.tn_cell = self._create_matrix_cell("TN", "True Negatives", "#8BC34A")
        row2_layout.addWidget(self.tn_cell)

        grid_layout.addLayout(row2_layout)

        layout.addWidget(grid_widget)

        # Metrics summary
        metrics_layout = QHBoxLayout()

        self.accuracy_label = QLabel("Accuracy: --")
        self.accuracy_label.setStyleSheet("font-weight: bold; padding: 5px;")
        metrics_layout.addWidget(self.accuracy_label)

        self.precision_label = QLabel("Precision: --")
        self.precision_label.setStyleSheet("font-weight: bold; padding: 5px;")
        metrics_layout.addWidget(self.precision_label)

        self.recall_label = QLabel("Recall: --")
        self.recall_label.setStyleSheet("font-weight: bold; padding: 5px;")
        metrics_layout.addWidget(self.recall_label)

        self.f1_label = QLabel("F1: --")
        self.f1_label.setStyleSheet("font-weight: bold; padding: 5px;")
        metrics_layout.addWidget(self.f1_label)

        layout.addLayout(metrics_layout)

    def _create_header_label(self, text: str) -> QLabel:
        """Create a header label for the matrix."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: bold;
                color: #666;
                padding: 8px;
                min-width: 150px;
            }
        """)
        return label

    def _create_matrix_cell(self, cell_type: str, tooltip: str, color: str) -> QPushButton:
        """Create a clickable matrix cell."""
        cell = QPushButton("0\n(0.0%)")
        cell.setMinimumSize(150, 100)
        cell.setToolTip(f"{tooltip}\nCliquez pour voir les paires")
        cell.setProperty("cell_type", cell_type)

        cell.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-size: 20px;
                font-weight: bold;
                border: 2px solid white;
                border-radius: 8px;
                padding: 10px;
            }}
            QPushButton:hover {{
                border-color: #2196F3;
                border-width: 3px;
            }}
            QPushButton:pressed {{
                background-color: #1976D2;
            }}
        """)

        cell.clicked.connect(lambda: self._on_cell_clicked(cell_type))

        return cell

    def set_results(self, results: List[Dict]):
        """
        Update matrix with benchmark results.

        Args:
            results: List of result dicts with 'expected' and 'is_match' keys
        """
        self.results = results

        # Calculate confusion matrix
        tp = fp = tn = fn = 0

        for result in results:
            expected = result.get('expected')
            predicted = 'duplicate' if result.get('is_match') else 'not_duplicate'

            if expected == 'duplicate' and predicted == 'duplicate':
                tp += 1
            elif expected == 'not_duplicate' and predicted == 'duplicate':
                fp += 1
            elif expected == 'not_duplicate' and predicted == 'not_duplicate':
                tn += 1
            elif expected == 'duplicate' and predicted == 'not_duplicate':
                fn += 1

        self.confusion_data = {'TP': tp, 'FP': fp, 'TN': tn, 'FN': fn}

        # Update display
        self._update_display()

    def _update_display(self):
        """Update matrix cells and metrics."""
        total = sum(self.confusion_data.values())

        if total == 0:
            return

        # Update cells
        for cell_type, cell in [('TP', self.tp_cell), ('FP', self.fp_cell),
                                 ('TN', self.tn_cell), ('FN', self.fn_cell)]:
            count = self.confusion_data[cell_type]
            percentage = (count / total * 100) if total > 0 else 0
            cell.setText(f"{count}\n({percentage:.1f}%)")

        # Calculate metrics
        tp = self.confusion_data['TP']
        fp = self.confusion_data['FP']
        tn = self.confusion_data['TN']
        fn = self.confusion_data['FN']

        accuracy = (tp + tn) / total if total > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        # Update metrics labels
        self.accuracy_label.setText(f"Accuracy: {accuracy:.3f}")
        self.precision_label.setText(f"Precision: {precision:.3f}")
        self.recall_label.setText(f"Recall: {recall:.3f}")
        self.f1_label.setText(f"F1 Score: {f1:.3f}")

    def _on_cell_clicked(self, cell_type: str):
        """Handle cell click - show pairs for this category."""
        pairs = self._get_pairs_for_cell(cell_type)

        if not pairs:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Info", f"Aucune paire dans la catégorie {cell_type}")
            return

        self.cell_clicked.emit(cell_type, pairs)

        # Show dialog with pairs
        self._show_pairs_dialog(cell_type, pairs)

    def _get_pairs_for_cell(self, cell_type: str) -> List[Dict]:
        """Get pairs belonging to a specific cell."""
        pairs = []

        for result in self.results:
            expected = result.get('expected')
            predicted = 'duplicate' if result.get('is_match') else 'not_duplicate'

            match = False
            if cell_type == 'TP' and expected == 'duplicate' and predicted == 'duplicate':
                match = True
            elif cell_type == 'FP' and expected == 'not_duplicate' and predicted == 'duplicate':
                match = True
            elif cell_type == 'TN' and expected == 'not_duplicate' and predicted == 'not_duplicate':
                match = True
            elif cell_type == 'FN' and expected == 'duplicate' and predicted == 'not_duplicate':
                match = True

            if match:
                pairs.append(result)

        return pairs

    def _show_pairs_dialog(self, cell_type: str, pairs: List[Dict]):
        """Show dialog with pairs from clicked cell."""
        from pathlib import Path

        dialog = QDialog(self)
        dialog.setWindowTitle(f"{cell_type} - {len(pairs)} paires")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)

        # Description
        descriptions = {
            'TP': "✅ Vrais Positifs - Correctement identifiés comme duplicata",
            'FP': "❌ Faux Positifs - Incorrectement identifiés comme duplicata",
            'TN': "✅ Vrais Négatifs - Correctement identifiés comme non-duplicata",
            'FN': "❌ Faux Négatifs - Incorrectement identifiés comme non-duplicata"
        }

        desc_label = QLabel(descriptions.get(cell_type, ""))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-weight: bold; padding: 10px; background-color: #F5F5F5;")
        layout.addWidget(desc_label)

        # Table
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Vidéo 1", "Vidéo 2", "Similarité"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for pair in pairs:
            row = table.rowCount()
            table.insertRow(row)

            v1 = Path(pair.get('video1_path', '')).name
            v2 = Path(pair.get('video2_path', '')).name
            sim = pair.get('similarity', 0)

            table.setItem(row, 0, QTableWidgetItem(v1))
            table.setItem(row, 1, QTableWidgetItem(v2))
            table.setItem(row, 2, QTableWidgetItem(f"{sim:.2f}%"))

        layout.addWidget(table)

        # Close button
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()


class ROCCurveWidget(QWidget):
    """
    Interactive ROC Curve visualization with adjustable threshold.

    Features:
        - ROC curve plot with matplotlib
        - Interactive threshold slider (0.0 - 1.0)
        - Real-time metrics update (TPR, FPR, Precision, Recall, F1)
        - AUC score display
        - Current threshold point highlighted on curve
        - Optimal threshold suggestion (max F1)

    Signals:
        threshold_changed(float): Emitted when threshold slider changes
    """

    threshold_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.results = []
        self.current_threshold = 0.5
        self.roc_points = []  # List of (threshold, fpr, tpr) tuples
        self.optimal_threshold = 0.5
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("📈 <b>Courbe ROC Interactive</b>")
        title.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(title)

        # Check if matplotlib is available
        if not MATPLOTLIB_AVAILABLE:
            warning = QLabel("⚠️ Matplotlib non disponible - visualisation désactivée")
            warning.setStyleSheet("color: #FF5722; padding: 20px; font-size: 12px;")
            layout.addWidget(warning)
            return

        # Main content
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)

        # Left side: ROC Curve plot
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        plot_layout.setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(figsize=(6, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        plot_layout.addWidget(self.canvas)

        content_layout.addWidget(plot_widget, stretch=2)

        # Right side: Controls and metrics
        controls_widget = QWidget()
        controls_widget.setStyleSheet("""
            QWidget {
                background-color: #F5F5F5;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        controls_widget.setMaximumWidth(300)
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setSpacing(15)

        # AUC Score
        self.auc_label = QLabel("AUC: --")
        self.auc_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1976D2;
            padding: 10px;
            background-color: white;
            border-radius: 5px;
        """)
        self.auc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_layout.addWidget(self.auc_label)

        # Threshold slider section
        slider_group = QGroupBox("🎯 Seuil de Similarité")
        slider_layout = QVBoxLayout(slider_group)

        # Threshold value display
        threshold_display_layout = QHBoxLayout()
        threshold_display_layout.addWidget(QLabel("Seuil actuel:"))
        self.threshold_value_label = QLabel("0.50")
        self.threshold_value_label.setStyleSheet("font-weight: bold; color: #1976D2;")
        threshold_display_layout.addWidget(self.threshold_value_label)
        threshold_display_layout.addStretch()
        slider_layout.addLayout(threshold_display_layout)

        # Slider
        from PyQt6.QtWidgets import QSlider
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(50)
        self.threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.threshold_slider.setTickInterval(10)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        slider_layout.addWidget(self.threshold_slider)

        # Min/Max labels
        minmax_layout = QHBoxLayout()
        minmax_layout.addWidget(QLabel("0.0"))
        minmax_layout.addStretch()
        minmax_layout.addWidget(QLabel("1.0"))
        slider_layout.addLayout(minmax_layout)

        # Optimal threshold button
        self.optimal_btn = QPushButton("✨ Utiliser Seuil Optimal")
        self.optimal_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.optimal_btn.clicked.connect(self._set_optimal_threshold)
        self.optimal_btn.setEnabled(False)
        slider_layout.addWidget(self.optimal_btn)

        controls_layout.addWidget(slider_group)

        # Metrics display
        metrics_group = QGroupBox("📊 Métriques au Seuil Actuel")
        metrics_layout = QVBoxLayout(metrics_group)
        metrics_layout.setSpacing(8)

        self.tpr_label = self._create_metric_label("TPR (Recall):", "--")
        self.fpr_label = self._create_metric_label("FPR:", "--")
        self.precision_label = self._create_metric_label("Precision:", "--")
        self.f1_label = self._create_metric_label("F1 Score:", "--")

        metrics_layout.addWidget(self.tpr_label)
        metrics_layout.addWidget(self.fpr_label)
        metrics_layout.addWidget(self.precision_label)
        metrics_layout.addWidget(self.f1_label)

        controls_layout.addWidget(metrics_group)

        controls_layout.addStretch()

        content_layout.addWidget(controls_widget, stretch=1)

        layout.addWidget(content_widget)

        # Initial plot
        self._plot_empty_curve()

    def _create_metric_label(self, text: str, value: str) -> QLabel:
        """Create a metric label."""
        label = QLabel(f"{text} <b>{value}</b>")
        label.setStyleSheet("padding: 5px; background-color: white; border-radius: 3px;")
        return label

    def set_results(self, results: List[Dict]):
        """
        Set benchmark results and calculate ROC curve.

        Args:
            results: List of benchmark result dicts with 'similarity', 'expected', 'is_match'
        """
        if not MATPLOTLIB_AVAILABLE:
            return

        self.results = results

        if not results:
            self._plot_empty_curve()
            return

        # Calculate ROC curve points
        self._calculate_roc_curve()

        # Find optimal threshold (max F1)
        self._find_optimal_threshold()

        # Plot curve
        self._plot_roc_curve()

        # Update metrics for current threshold
        self._update_metrics()

        # Enable optimal button
        self.optimal_btn.setEnabled(True)

    def _calculate_roc_curve(self):
        """Calculate ROC curve points for different thresholds."""
        # Extract similarities and ground truth
        similarities = []
        ground_truth = []

        for result in self.results:
            similarities.append(result.get('similarity', 0))
            expected = result['expected']
            ground_truth.append(1 if expected == 'duplicate' else 0)

        # Sort by similarity (descending)
        sorted_indices = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)

        # Calculate TP, FP for different thresholds
        self.roc_points = []
        thresholds = sorted(set(similarities), reverse=True)

        # Add endpoints
        if 1.0 not in thresholds:
            thresholds.insert(0, 1.0)
        if 0.0 not in thresholds:
            thresholds.append(0.0)

        total_positives = sum(ground_truth)
        total_negatives = len(ground_truth) - total_positives

        for threshold in thresholds:
            tp = fp = 0

            for i, sim in enumerate(similarities):
                if sim >= threshold:
                    if ground_truth[i] == 1:
                        tp += 1
                    else:
                        fp += 1

            tpr = tp / total_positives if total_positives > 0 else 0
            fpr = fp / total_negatives if total_negatives > 0 else 0

            self.roc_points.append((threshold, fpr, tpr))

        # Calculate AUC using trapezoidal rule
        auc = 0.0
        for i in range(len(self.roc_points) - 1):
            x1, y1 = self.roc_points[i][1], self.roc_points[i][2]
            x2, y2 = self.roc_points[i + 1][1], self.roc_points[i + 1][2]
            auc += (x2 - x1) * (y1 + y2) / 2

        self.auc_label.setText(f"AUC: {auc:.3f}")

    def _find_optimal_threshold(self):
        """Find threshold that maximizes F1 score."""
        best_f1 = 0
        best_threshold = 0.5

        for threshold, _, _ in self.roc_points:
            metrics = self._calculate_metrics_at_threshold(threshold)
            if metrics['f1'] > best_f1:
                best_f1 = metrics['f1']
                best_threshold = threshold

        self.optimal_threshold = best_threshold
        self.optimal_btn.setText(f"✨ Optimal: {best_threshold:.2f} (F1={best_f1:.3f})")

    def _calculate_metrics_at_threshold(self, threshold: float) -> Dict:
        """Calculate all metrics at a given threshold."""
        tp = fp = tn = fn = 0

        for result in self.results:
            similarity = result.get('similarity', 0)
            expected = result['expected']
            predicted = 'duplicate' if similarity >= threshold else 'not_duplicate'

            if expected == 'duplicate' and predicted == 'duplicate':
                tp += 1
            elif expected == 'not_duplicate' and predicted == 'duplicate':
                fp += 1
            elif expected == 'not_duplicate' and predicted == 'not_duplicate':
                tn += 1
            elif expected == 'duplicate' and predicted == 'not_duplicate':
                fn += 1

        total_positives = tp + fn
        total_negatives = tn + fp

        tpr = tp / total_positives if total_positives > 0 else 0
        fpr = fp / total_negatives if total_negatives > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tpr
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        return {
            'tpr': tpr,
            'fpr': fpr,
            'precision': precision,
            'recall': recall,
            'f1': f1
        }

    def _plot_empty_curve(self):
        """Plot empty ROC curve placeholder."""
        self.ax.clear()
        self.ax.plot([0, 1], [0, 1], 'k--', lw=2, label='Random (AUC=0.50)')
        self.ax.set_xlim([0.0, 1.0])
        self.ax.set_ylim([0.0, 1.05])
        self.ax.set_xlabel('False Positive Rate', fontsize=10)
        self.ax.set_ylabel('True Positive Rate', fontsize=10)
        self.ax.set_title('ROC Curve', fontsize=12, fontweight='bold')
        self.ax.legend(loc="lower right", fontsize=9)
        self.ax.grid(True, alpha=0.3)
        self.figure.tight_layout()
        self.canvas.draw()

    def _plot_roc_curve(self):
        """Plot the ROC curve with current threshold highlighted."""
        self.ax.clear()

        # Extract FPR and TPR
        fpr_values = [point[1] for point in self.roc_points]
        tpr_values = [point[2] for point in self.roc_points]

        # Plot ROC curve
        self.ax.plot(fpr_values, tpr_values, 'b-', lw=2, label=f'ROC Curve')

        # Plot random baseline
        self.ax.plot([0, 1], [0, 1], 'k--', lw=1, alpha=0.5, label='Random (AUC=0.50)')

        # Highlight current threshold point
        metrics = self._calculate_metrics_at_threshold(self.current_threshold)
        self.ax.plot(metrics['fpr'], metrics['tpr'], 'ro', markersize=10,
                    label=f'Seuil actuel: {self.current_threshold:.2f}')

        # Highlight optimal threshold
        opt_metrics = self._calculate_metrics_at_threshold(self.optimal_threshold)
        self.ax.plot(opt_metrics['fpr'], opt_metrics['tpr'], 'g*', markersize=15,
                    label=f'Optimal: {self.optimal_threshold:.2f}')

        self.ax.set_xlim([0.0, 1.0])
        self.ax.set_ylim([0.0, 1.05])
        self.ax.set_xlabel('False Positive Rate (FPR)', fontsize=10)
        self.ax.set_ylabel('True Positive Rate (TPR)', fontsize=10)
        self.ax.set_title('ROC Curve - Receiver Operating Characteristic', fontsize=11, fontweight='bold')
        self.ax.legend(loc="lower right", fontsize=8)
        self.ax.grid(True, alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw()

    def _update_metrics(self):
        """Update metrics display for current threshold."""
        metrics = self._calculate_metrics_at_threshold(self.current_threshold)

        self.tpr_label.setText(f"TPR (Recall): <b>{metrics['tpr']:.3f}</b>")
        self.fpr_label.setText(f"FPR: <b>{metrics['fpr']:.3f}</b>")
        self.precision_label.setText(f"Precision: <b>{metrics['precision']:.3f}</b>")
        self.f1_label.setText(f"F1 Score: <b>{metrics['f1']:.3f}</b>")

        # Color code F1 score
        if metrics['f1'] >= 0.8:
            f1_color = "#4CAF50"  # Green
        elif metrics['f1'] >= 0.6:
            f1_color = "#FF9800"  # Orange
        else:
            f1_color = "#F44336"  # Red

        self.f1_label.setStyleSheet(f"padding: 5px; background-color: white; border-radius: 3px; border-left: 4px solid {f1_color};")

    def _on_threshold_changed(self, value: int):
        """Handle threshold slider change."""
        # Convert 0-100 to 0.0-1.0
        self.current_threshold = value / 100.0
        self.threshold_value_label.setText(f"{self.current_threshold:.2f}")

        # Update plot and metrics
        if self.results:
            self._plot_roc_curve()
            self._update_metrics()

        # Emit signal
        self.threshold_changed.emit(self.current_threshold)

    def _set_optimal_threshold(self):
        """Set threshold to optimal value."""
        slider_value = int(self.optimal_threshold * 100)
        self.threshold_slider.setValue(slider_value)


class BenchmarkPresets:
    """
    Predefined benchmark modes for quick testing.

    Modes:
        QUICK: Fast validation (~30s) - 10 pairs, 1 pipeline
        STANDARD: Balanced testing (~5min) - 50 pairs, 2 pipelines
        DEEP: Thorough testing (~30min) - 200 pairs, 5 pipelines
        STRESS: Comprehensive test (~2h+) - All pairs, all pipelines
    """

    QUICK = {
        'name': '⚡ Quick',
        'description': 'Fast validation test (~30 seconds)',
        'max_pairs': 10,
        'pipelines': ['quick'],
        'sample_strategy': 'random',
        'estimated_time': '30s',
        'icon': '⚡',
        'color': '#2196F3'
    }

    STANDARD = {
        'name': '⚖️ Standard',
        'description': 'Balanced testing (~5 minutes)',
        'max_pairs': 50,
        'pipelines': ['quick', 'balanced'],
        'sample_strategy': 'stratified',
        'estimated_time': '5min',
        'icon': '⚖️',
        'color': '#4CAF50'
    }

    DEEP = {
        'name': '🔬 Deep',
        'description': 'Thorough validation (~30 minutes)',
        'max_pairs': 200,
        'pipelines': ['quick', 'balanced', 'accurate', 'paranoid', 'comprehensive'],
        'sample_strategy': 'comprehensive',
        'estimated_time': '30min',
        'icon': '🔬',
        'color': '#FF9800'
    }

    STRESS = {
        'name': '🚀 Stress',
        'description': 'Exhaustive test (2h+)',
        'max_pairs': -1,  # All pairs
        'pipelines': 'all',  # All available pipelines
        'sample_strategy': 'exhaustive',
        'estimated_time': '2h+',
        'icon': '🚀',
        'color': '#F44336'
    }

    @classmethod
    def get_all_modes(cls):
        """Get all available benchmark modes."""
        return [cls.QUICK, cls.STANDARD, cls.DEEP, cls.STRESS]

    @classmethod
    def get_mode_by_name(cls, name: str):
        """Get a specific mode by name."""
        for mode in cls.get_all_modes():
            if mode['name'] == name or name in mode['name']:
                return mode
        return None

    @classmethod
    def estimate_duration(cls, num_pairs: int, num_pipelines: int) -> str:
        """
        Estimate benchmark duration.

        Args:
            num_pairs: Number of video pairs to test
            num_pipelines: Number of pipelines to run

        Returns:
            Human-readable duration estimate
        """
        # Assume ~0.4s per pair per pipeline
        total_seconds = num_pairs * num_pipelines * 0.4

        if total_seconds < 60:
            return f"~{int(total_seconds)}s"
        elif total_seconds < 3600:
            return f"~{int(total_seconds / 60)}min"
        else:
            return f"~{total_seconds / 3600:.1f}h"


class BenchmarkDashboardWidget(QWidget):
    """
    Unified dashboard for quick benchmark overview and actions.

    Features:
        - Last run summary with key metrics
        - Quick Start button for immediate benchmark execution
        - Top 3 recent pipelines with performance metrics
        - Quick access to common operations
        - At-a-glance health indicators

    Signals:
        quick_run_clicked: Emitted when Quick Start Run button clicked
        create_pipeline_clicked: Emitted when Create Pipeline clicked
        create_test_set_clicked: Emitted when Create Test Set clicked
    """

    quick_run_clicked = pyqtSignal()
    create_pipeline_clicked = pyqtSignal()
    create_test_set_clicked = pyqtSignal()

    def __init__(self, benchmark_manager: BenchmarkManager, pipeline_manager: PipelineManager,
                 test_set_manager: TestSetManager):
        super().__init__()
        self.benchmark_manager = benchmark_manager
        self.pipeline_manager = pipeline_manager
        self.test_set_manager = test_set_manager
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """Initialize the dashboard UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("📊 <b>Benchmark Dashboard</b>")
        header.setStyleSheet("font-size: 18px; padding: 10px; color: #2196F3;")
        layout.addWidget(header)

        # Quick Actions Section
        actions_group = QGroupBox("⚡ Quick Actions")
        actions_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        actions_layout = QHBoxLayout()

        quick_run_btn = QPushButton("▶️ Quick Start Run")
        quick_run_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 15px 30px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        quick_run_btn.setToolTip("Lance un benchmark avec les paramètres par défaut")
        quick_run_btn.clicked.connect(self.quick_run_clicked.emit)
        actions_layout.addWidget(quick_run_btn)

        new_pipeline_btn = QPushButton("🔧 New Pipeline")
        new_pipeline_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                font-size: 12px;
                padding: 12px 20px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        new_pipeline_btn.clicked.connect(self.create_pipeline_clicked.emit)
        actions_layout.addWidget(new_pipeline_btn)

        new_test_set_btn = QPushButton("📋 New Test Set")
        new_test_set_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFC107;
                color: #333;
                font-size: 12px;
                padding: 12px 20px;
                border-radius: 5px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FFB300;
            }
        """)
        new_test_set_btn.clicked.connect(self.create_test_set_clicked.emit)
        actions_layout.addWidget(new_test_set_btn)

        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        # Stats Cards Section
        stats_layout = QHBoxLayout()

        # Last Run Card
        self.last_run_card = self._create_stat_card(
            "📅 Last Run",
            "No runs yet",
            "Never",
            "#E3F2FD"
        )
        stats_layout.addWidget(self.last_run_card)

        # Total Runs Card
        self.total_runs_card = self._create_stat_card(
            "🔢 Total Runs",
            "0",
            "All time",
            "#F3E5F5"
        )
        stats_layout.addWidget(self.total_runs_card)

        # Best F1 Score Card
        self.best_f1_card = self._create_stat_card(
            "🏆 Best F1 Score",
            "N/A",
            "No data",
            "#E8F5E9"
        )
        stats_layout.addWidget(self.best_f1_card)

        layout.addLayout(stats_layout)

        # Top Pipelines Section
        pipelines_group = QGroupBox("🔝 Top 3 Recent Pipelines")
        pipelines_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        pipelines_layout = QVBoxLayout()

        self.pipelines_table = QTableWidget()
        self.pipelines_table.setColumnCount(4)
        self.pipelines_table.setHorizontalHeaderLabels(["Pipeline", "F1 Score", "Last Run", "Status"])
        self.pipelines_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pipelines_table.setMaximumHeight(150)
        self.pipelines_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        pipelines_layout.addWidget(self.pipelines_table)
        pipelines_group.setLayout(pipelines_layout)
        layout.addWidget(pipelines_group)

        # Info Section
        info_label = QLabel(
            "ℹ️ <i>Use Quick Start Run to test the default pipeline, "
            "or create custom pipelines and test sets for detailed validation.</i>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()

    def _create_stat_card(self, title: str, value: str, subtitle: str, bg_color: str) -> QGroupBox:
        """Create a statistics card widget."""
        card = QGroupBox()
        card.setStyleSheet(f"""
            QGroupBox {{
                background-color: {bg_color};
                border-radius: 8px;
                padding: 15px;
                border: 1px solid #DDDDDD;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 11px; color: #666; font-weight: bold;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        value_label.setObjectName("value_label")  # For easy updating
        layout.addWidget(value_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("font-size: 10px; color: #999;")
        subtitle_label.setObjectName("subtitle_label")
        layout.addWidget(subtitle_label)

        return card

    def _load_data(self):
        """Load and display dashboard data."""
        try:
            # Get last run info
            runs = self.benchmark_manager.get_run_history(limit=1)
            if runs:
                last_run = runs[0]
                self._update_card(self.last_run_card,
                                last_run['pipeline_name'][:20],
                                f"{last_run['timestamp'][:10]}")

            # Get total runs count
            all_runs = self.benchmark_manager.get_run_history(limit=1000)
            self._update_card(self.total_runs_card,
                            str(len(all_runs)),
                            "Benchmarks completed")

            # Get best F1 score
            if all_runs:
                best_run = max(all_runs, key=lambda r: r.get('f1_score', 0))
                f1_score = best_run.get('f1_score', 0)
                self._update_card(self.best_f1_card,
                                f"{f1_score:.3f}",
                                f"{best_run['pipeline_name'][:15]}")

            # Load top 3 pipelines
            self._load_top_pipelines()

        except Exception as e:
            logger.error(f"Error loading dashboard data: {e}", exc_info=True)

    def _update_card(self, card: QGroupBox, value: str, subtitle: str):
        """Update a stat card's values."""
        value_label = card.findChild(QLabel, "value_label")
        subtitle_label = card.findChild(QLabel, "subtitle_label")

        if value_label:
            value_label.setText(value)
        if subtitle_label:
            subtitle_label.setText(subtitle)

    def _load_top_pipelines(self):
        """Load top 3 recent pipelines into table."""
        self.pipelines_table.setRowCount(0)

        try:
            # Get recent benchmark runs
            runs = self.benchmark_manager.get_run_history(limit=10)

            # Group by pipeline and get latest for each
            pipeline_runs = {}
            for run in runs:
                pipeline_name = run['pipeline_name']
                if pipeline_name not in pipeline_runs:
                    pipeline_runs[pipeline_name] = run

            # Take top 3
            top_3 = list(pipeline_runs.values())[:3]

            for run in top_3:
                row = self.pipelines_table.rowCount()
                self.pipelines_table.insertRow(row)

                # Pipeline name
                self.pipelines_table.setItem(row, 0, QTableWidgetItem(run['pipeline_name']))

                # F1 Score
                f1_score = run.get('f1_score', 0)
                f1_item = QTableWidgetItem(f"{f1_score:.3f}" if f1_score else "N/A")
                self.pipelines_table.setItem(row, 1, f1_item)

                # Last run date
                timestamp = run['timestamp'][:10] if run.get('timestamp') else "Unknown"
                self.pipelines_table.setItem(row, 2, QTableWidgetItem(timestamp))

                # Status indicator
                status = "✅ Good" if f1_score > 0.8 else "⚠️ OK" if f1_score > 0.5 else "❌ Poor"
                status_item = QTableWidgetItem(status)
                self.pipelines_table.setItem(row, 3, status_item)

        except Exception as e:
            logger.error(f"Error loading top pipelines: {e}", exc_info=True)

    def refresh(self):
        """Refresh dashboard data."""
        self._load_data()


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
        # Sauvegarde via éditeur unifié, mais pour cohérence UI on bloque le bouton pour les défauts
        self.save_btn.setEnabled(not is_default)
        self.delete_btn.setEnabled(not is_default)

    def _on_new_pipeline(self):
        """Créer un pipeline via l'éditeur unifié."""
        from .unified_pipeline_editor_dialog import UnifiedPipelineEditorDialog

        dialog = UnifiedPipelineEditorDialog(
            pipeline_manager=self.pipeline_manager,
            db_manager=None,
            pipeline_data=None,
            is_copy=False,
            parent=self,
        )
        if dialog.exec():
            self._load_pipelines()
            self.pipeline_saved.emit(dialog.name_edit.text().strip())

    def _on_duplicate_pipeline(self):
        """Dupliquer un pipeline via l'éditeur unifié."""
        current = self.pipeline_list.currentItem()
        if not current:
            return

        pipeline = current.data(Qt.ItemDataRole.UserRole)

        from .unified_pipeline_editor_dialog import UnifiedPipelineEditorDialog
        dialog = UnifiedPipelineEditorDialog(
            pipeline_manager=self.pipeline_manager,
            db_manager=None,
            pipeline_data=pipeline,
            is_copy=True,
            parent=self,
        )
        if dialog.exec():
            self._load_pipelines()
            self.pipeline_saved.emit(dialog.name_edit.text().strip())

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
        """Ouvre l'éditeur unifié pour créer/éditer le pipeline sélectionné."""
        current = self.pipeline_list.currentItem()
        pipeline = current.data(Qt.ItemDataRole.UserRole) if current else None

        # Si pipeline par défaut, on force la copie (pas d'édition en place)
        is_default = pipeline.get('is_default', False) if pipeline else False

        from .unified_pipeline_editor_dialog import UnifiedPipelineEditorDialog
        dialog = UnifiedPipelineEditorDialog(
            pipeline_manager=self.pipeline_manager,
            db_manager=None,
            pipeline_data=pipeline,
            is_copy=is_default or (pipeline is None and True),
            parent=self,
        )
        if dialog.exec():
            self._load_pipelines()
            self.pipeline_saved.emit(dialog.name_edit.text().strip())


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

        self.wizard_btn = QPushButton("🧙 Créer / Modifier")
        self.wizard_btn.clicked.connect(self._on_open_wizard)
        self.wizard_btn.setToolTip("Créer un nouveau test set ou modifier le test set sélectionné")
        self.wizard_btn.setStyleSheet("font-weight: bold;")
        selector_layout.addWidget(self.wizard_btn)

        self.delete_set_btn = QPushButton("🗑️ Supprimer")
        self.delete_set_btn.clicked.connect(self._on_delete_test_set)
        self.delete_set_btn.setToolTip("Supprimer le test set sélectionné et toutes ses paires")
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

        self.expand_btn = QPushButton("🔄 Enrichir (Toutes les paires)")
        self.expand_btn.clicked.connect(self._on_expand_test_set)
        self.expand_btn.setToolTip("Ajouter toutes les paires possibles manquantes pour une validation exhaustive")
        import_layout.addWidget(self.expand_btn)

        self.enrich_negatives_btn = QPushButton("➖ Enrichir (Non-duplicatas)")
        self.enrich_negatives_btn.clicked.connect(self._on_enrich_negatives)
        self.enrich_negatives_btn.setToolTip("Ajouter des paires de vidéos différentes (non-duplicatas) pour valider les faux positifs")
        import_layout.addWidget(self.enrich_negatives_btn)

        import_layout.addStretch()
        layout.addLayout(import_layout)

        # Stats
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("background-color: #F0F0F0; padding: 8px; border-radius: 4px;")
        layout.addWidget(self.stats_label)

        # Pairs table
        self.pairs_table = QTableWidget()
        self.pairs_table.setColumnCount(7)
        self.pairs_table.setHorizontalHeaderLabels(["ID", "Vidéo 1", "Vidéo 2", "Type", "Changer Type", "Notes", "Actions"])
        self.pairs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.pairs_table.horizontalHeader().setStretchLastSection(False)
        self.pairs_table.setColumnWidth(4, 250)  # Change type buttons column width
        self.pairs_table.setColumnWidth(6, 80)  # Actions column width
        layout.addWidget(self.pairs_table)

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

            # Quick type change buttons
            type_widget = QWidget()
            type_layout = QHBoxLayout(type_widget)
            type_layout.setContentsMargins(2, 2, 2, 2)
            type_layout.setSpacing(2)

            # Define type buttons with emojis and labels
            type_buttons = [
                ("✅ Positif", "positive", "#4CAF50"),
                ("❌ Négatif", "negative", "#F44336"),
                ("❓ Inconnu", "unknown", "#FF9800"),
            ]

            for label, type_value, color in type_buttons:
                btn = QPushButton(label)
                btn.setMaximumHeight(25)
                # Highlight current type
                if pair['expected'] == type_value or \
                   (type_value == 'positive' and pair['expected'] in ['scene_found', 'duplicate']) or \
                   (type_value == 'negative' and pair['expected'] in ['scene_not_found', 'not_duplicate']):
                    btn.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold;")
                else:
                    btn.setStyleSheet("background-color: #E0E0E0;")
                btn.setToolTip(f"Changer en {label}")
                btn.clicked.connect(lambda checked, p=pair, t=type_value: self._change_pair_type_direct(p, t))
                type_layout.addWidget(btn)

            self.pairs_table.setCellWidget(row, 4, type_widget)

            self.pairs_table.setItem(row, 5, QTableWidgetItem(pair['notes'] or ''))

            # Actions buttons (only delete now)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(2)

            delete_btn = QPushButton("🗑️")
            delete_btn.setMaximumWidth(30)
            delete_btn.setToolTip("Supprimer cette paire")
            delete_btn.clicked.connect(lambda checked, p=pair: self._on_delete_pair_direct(p))
            actions_layout.addWidget(delete_btn)

            self.pairs_table.setCellWidget(row, 6, actions_widget)

        # Update stats
        stats = self.test_set_manager.get_stats(test_set_name)
        self.stats_label.setText(
            f"Total: {stats['total']} paires | "
            f"✅ Positives: {stats['positives']} | "
            f"❌ Négatives: {stats['negatives']} | "
            f"❓ Inconnues: {stats['unknowns']}"
        )

        self.test_set_changed.emit(test_set_name)

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

    def _on_expand_test_set(self):
        """Expand test set with all possible pairs."""
        test_set_name = self.test_set_combo.currentText()
        if not test_set_name:
            return

        # Confirm action
        reply = QMessageBox.question(
            self, "Enrichir le Test Set",
            f"Voulez-vous enrichir '{test_set_name}' avec TOUTES les paires possibles ?\n\n"
            "Cela ajoutera toutes les combinaisons manquantes entre les vidéos du test set "
            "avec le label 'unknown', permettant de détecter si le pipeline trouve des "
            "matches non prévus.\n\n"
            "Note: Les paires existantes ne seront pas modifiées.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                result = self.test_set_manager.expand_test_set_with_all_pairs(test_set_name)

                QMessageBox.information(
                    self, "Enrichissement Terminé",
                    f"✅ Test set '{test_set_name}' enrichi avec succès !\n\n"
                    f"• Paires existantes: {result['existing_pairs']}\n"
                    f"• Nouvelles paires ajoutées: {result['new_pairs']}\n"
                    f"• Total: {result['total_pairs']} paires\n\n"
                    "Les nouvelles paires ont le label 'unknown' et peuvent maintenant "
                    "être testées par le pipeline."
                )

                # Refresh the table
                self._on_test_set_changed(test_set_name)

            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'enrichissement:\n{str(e)}")
                logger.error(f"Test set expansion error: {e}", exc_info=True)

    def _on_enrich_negatives(self):
        """Enrichit le test set avec des paires de non-duplicatas."""
        test_set_name = self.test_set_combo.currentText()
        if not test_set_name:
            return

        # Confirm action
        reply = QMessageBox.question(
            self, "Enrichir avec Non-Duplicatas",
            f"Voulez-vous enrichir '{test_set_name}' avec des paires de NON-DUPLICATAS ?\n\n"
            "Cela ajoutera des paires de vidéos différentes (fichiers distincts sans relation) "
            "avec le label 'negative', permettant de valider que le pipeline ne génère pas de "
            "faux positifs (détection incorrecte de duplicatas).\n\n"
            "Recommandé pour un test set équilibré.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Add non-duplicate pairs (different videos, labeled as 'negative')
                result = self.test_set_manager.expand_test_set_with_all_pairs(test_set_name, default_expected='negative')

                QMessageBox.information(
                    self, "Enrichissement Terminé",
                    f"✅ Test set '{test_set_name}' enrichi avec des non-duplicatas !\n\n"
                    f"• Paires existantes: {result['existing_pairs']}\n"
                    f"• Nouvelles paires (negative): {result['new_pairs']}\n"
                    f"• Total: {result['total_pairs']} paires\n\n"
                    "Ces paires permettront de détecter les faux positifs."
                )

                # Refresh the table
                self._on_test_set_changed(test_set_name)

            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'enrichissement:\n{str(e)}")
                logger.error(f"Test set negatives enrichment error: {e}", exc_info=True)

    def _change_pair_type_direct(self, pair: dict, new_type: str):
        """Change pair type directly without confirmation."""
        success = self.test_set_manager.update_test_pair(
            pair_id=pair['id'],
            expected=new_type
        )

        if success:
            # Refresh the table
            test_set_name = self.test_set_combo.currentText()
            self._on_test_set_changed(test_set_name)
            logger.info(f"Pair {pair['id']} type changed to {new_type}")
        else:
            QMessageBox.warning(self, "Erreur", "Échec de la modification")

    def _on_delete_pair_direct(self, pair: dict):
        """Delete a specific pair directly without confirmation."""
        success = self.test_set_manager.delete_test_pair(pair['id'])
        if success:
            # Refresh the table
            test_set_name = self.test_set_combo.currentText()
            self._on_test_set_changed(test_set_name)
            logger.info(f"Pair {pair['id']} deleted")
        else:
            QMessageBox.warning(self, "Erreur", "Échec de la suppression")

    def _on_delete_pair(self, pair: dict):
        """Delete a specific pair (old method with confirmation - kept for compatibility)."""
        reply = QMessageBox.question(
            self, "Confirmation",
            f"Supprimer la paire:\n{os.path.basename(pair['video1_path'])} ↔ {os.path.basename(pair['video2_path'])} ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self.test_set_manager.delete_test_pair(pair['id'])
            if success:
                QMessageBox.information(self, "Succès", "Paire supprimée")
                # Refresh the table
                test_set_name = self.test_set_combo.currentText()
                self._on_test_set_changed(test_set_name)
            else:
                QMessageBox.warning(self, "Erreur", "Échec de la suppression")

    def _on_edit_pair(self, pair: dict):
        """Edit a specific pair."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox

        # Create edit dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Modifier la paire")
        dialog.setMinimumWidth(500)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        # Video paths (read-only)
        video1_label = QLabel(pair['video1_path'])
        video1_label.setWordWrap(True)
        form.addRow("Vidéo 1:", video1_label)

        video2_label = QLabel(pair['video2_path'])
        video2_label.setWordWrap(True)
        form.addRow("Vidéo 2:", video2_label)

        # Expected result (editable)
        expected_combo = QComboBox()
        expected_combo.addItem("Scène trouvée", "scene_found")
        expected_combo.addItem("Scène non trouvée", "scene_not_found")
        expected_combo.addItem("Inconnu", "unknown")
        expected_combo.addItem("Duplicata", "duplicate")
        expected_combo.addItem("Non-duplicata", "not_duplicate")
        expected_combo.addItem("Positif", "positive")
        expected_combo.addItem("Négatif", "negative")

        # Set current value
        for i in range(expected_combo.count()):
            if expected_combo.itemData(i) == pair['expected']:
                expected_combo.setCurrentIndex(i)
                break

        form.addRow("Résultat attendu:", expected_combo)

        # Notes (editable)
        notes_input = QLineEdit(pair['notes'] or '')
        form.addRow("Notes:", notes_input)

        layout.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update the pair
            success = self.test_set_manager.update_test_pair(
                pair_id=pair['id'],
                expected=expected_combo.currentData(),
                notes=notes_input.text()
            )

            if success:
                QMessageBox.information(self, "Succès", "Paire modifiée")
                # Refresh the table
                test_set_name = self.test_set_combo.currentText()
                self._on_test_set_changed(test_set_name)
            else:
                QMessageBox.warning(self, "Erreur", "Échec de la modification")

    def _on_open_wizard(self):
        """Open the test set creation/edit wizard."""
        # Get currently selected test set (if any)
        current_test_set = self.test_set_combo.currentText() if self.test_set_combo.count() > 0 else None

        # TestSetEditorWidget doesn't have access to main file list
        # User can add files manually in the wizard
        wizard = TestSetWizard(
            self.test_set_manager,
            preset_file_list=None,
            existing_test_set=current_test_set,
            parent=self
        )
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

    def _cleanup_previous_benchmark(self):
        """
        CORRECTION BUG #18: Cleanup previous benchmark to prevent memory leaks.

        Disconnects all signals and deletes previous runner object.
        """
        if self.runner:
            # Disconnect all runner signals
            try:
                self.runner.pipeline_progress.disconnect()
                self.runner.pair_progress.disconnect()
                self.runner.pipeline_completed.disconnect()
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

        logger.debug("Previous benchmark resources cleaned up (BenchmarkBatchWidget)")

    def _on_start_benchmark(self):
        """Start benchmark."""
        # CORRECTION BUG #18: Cleanup previous benchmark before starting new one
        self._cleanup_previous_benchmark()

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

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when widget is closed.

        Ensures proper memory cleanup when the widget is destroyed.
        """
        self._cleanup_previous_benchmark()
        super().closeEvent(event)


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

    def __init__(self, db_manager, file_list_widget=None):
        super().__init__()
        self.db_manager = db_manager
        self.file_list_widget = file_list_widget

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

        # Create tab widget (SIMPLIFIED TO 2 TABS - TASK 3)
        self.tabs = QTabWidget()

        # TAB 1: "📊 Dashboard" - Unified overview + management
        # Consolidates: Test Sets, Pipelines, Dashboard, Monitoring
        dashboard_tab = self._create_unified_dashboard_tab()
        self.tabs.addTab(dashboard_tab, "📊 Dashboard")

        # TAB 2: "🚀 Benchmark" - Execution + Results + History
        # Consolidates: Exécution, Résultats, Historique
        benchmark_tab = self._create_unified_benchmark_tab()
        self.tabs.addTab(benchmark_tab, "🚀 Benchmark")

        layout.addWidget(self.tabs)

        # Connect signals
        self.benchmark_widget.benchmark_finished.connect(self._on_benchmark_finished)
        self.pipeline_widget.pipeline_saved.connect(self._on_pipeline_saved)
        self.test_set_widget.test_set_changed.connect(self._on_test_set_changed)

    def _create_unified_dashboard_tab(self) -> QWidget:
        """
        Create unified dashboard tab (replaces Test Sets + Pipelines + Dashboard).

        Provides:
        - Dashboard overview with key metrics
        - Quick access to test set management
        - Quick access to pipeline management
        - System monitoring
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # Dashboard widget (from Phase 1)
        from .monitoring_dashboard import MonitoringDashboard
        self.dashboard_widget = MonitoringDashboard(
            self.benchmark_manager,
            alert_system=None  # Can add alert system if available
        )
        layout.addWidget(self.dashboard_widget, stretch=2)

        # Management section (collapsible)
        management_group = QGroupBox("⚙️ Gestion (Test Sets & Pipelines)")
        management_group.setCheckable(True)
        management_group.setChecked(True)  # Expanded by default for easy access
        management_layout = QVBoxLayout(management_group)

        # Sub-tabs for Test Sets and Pipelines
        management_tabs = QTabWidget()

        self.test_set_widget = TestSetEditorWidget(self.test_set_manager)
        management_tabs.addTab(self.test_set_widget, "📋 Test Sets")

        self.pipeline_widget = PipelineEditorWidget(self.pipeline_manager)
        management_tabs.addTab(self.pipeline_widget, "🔧 Pipelines")

        management_layout.addWidget(management_tabs)
        layout.addWidget(management_group, stretch=1)

        return tab

    def _create_unified_benchmark_tab(self) -> QWidget:
        """
        Create unified benchmark tab (replaces Exécution + Résultats + Historique).

        Provides:
        - Benchmark execution (with wizard option)
        - Results viewing
        - History tracking
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        # Top section: Execution controls
        execution_section = QGroupBox("▶️ Exécution")
        execution_layout = QVBoxLayout(execution_section)

        self.benchmark_widget = BenchmarkBatchWidget(
            self.benchmark_manager,
            self.pipeline_manager,
            self.test_set_manager,
            self.db_manager,
            self.file_list_widget
        )
        execution_layout.addWidget(self.benchmark_widget)

        layout.addWidget(execution_section, stretch=1)

        # Bottom section: Results & History (tabbed)
        results_tabs = QTabWidget()

        self.results_widget = BenchmarkResultsWidget(self.benchmark_manager)
        results_tabs.addTab(self.results_widget, "📊 Résultats")

        self.history_widget = BenchmarkHistoryWidget(self.benchmark_manager)
        results_tabs.addTab(self.history_widget, "📜 Historique")

        layout.addWidget(results_tabs, stretch=2)

        return tab

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
        # Go to Dashboard tab (index 0), expand management section, select test sets
        self.tabs.setCurrentIndex(0)
        self.test_set_widget._on_new_test_set()

    def _quick_new_pipeline(self):
        """Quick action: create new pipeline."""
        # Go to Dashboard tab (index 0), expand management section, select pipelines
        self.tabs.setCurrentIndex(0)
        self.pipeline_widget._on_new_pipeline()

    def _quick_run_benchmark(self):
        """Quick action: go to benchmark tab."""
        # Go to Benchmark tab (index 1)
        self.tabs.setCurrentIndex(1)

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when widget is closed.

        Disconnects signals from child widgets to prevent memory leaks.
        """
        # Disconnect all signal connections
        try:
            self.benchmark_widget.benchmark_finished.disconnect()
            self.pipeline_widget.pipeline_saved.disconnect()
            self.test_set_widget.test_set_changed.disconnect()
        except (RuntimeError, TypeError):
            # Signals may already be disconnected
            pass

        super().closeEvent(event)
