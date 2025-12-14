"""
Advanced Visualization Widgets

Collection of sophisticated visualization widgets for benchmark analysis:
- Precision-Recall Curve
- Similarity Distribution Histogram
- Pipeline Comparison Chart
- Time Series Metrics Trend
- Pair Analysis Scatter Plot
"""

from typing import List, Dict, Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from PyQt6.QtCore import Qt

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.AdvancedVisualizations')

# Matplotlib imports
try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("Matplotlib not available - advanced visualizations disabled")


class PrecisionRecallCurveWidget(QWidget):
    """
    Precision-Recall Curve visualization.

    Shows the trade-off between precision and recall at different thresholds.
    Useful for comparing pipeline performance and finding optimal thresholds.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.results = []
        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("📐 <b>Precision-Recall Curve</b>")
        title.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(title)

        if not MATPLOTLIB_AVAILABLE:
            warning = QLabel("⚠️ Matplotlib non disponible")
            warning.setStyleSheet("color: #FF5722; padding: 20px;")
            layout.addWidget(warning)
            return

        # Matplotlib canvas
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        layout.addWidget(self.canvas)

        self._plot_empty()

    def set_results(self, results: List[Dict]):
        """Set benchmark results and plot curve."""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.results = results
        if not results:
            self._plot_empty()
            return

        self._plot_curve()

    def _plot_empty(self):
        """Plot empty placeholder."""
        self.ax.clear()
        self.ax.set_xlabel('Recall', fontsize=11)
        self.ax.set_ylabel('Precision', fontsize=11)
        self.ax.set_title('Precision-Recall Curve', fontsize=13, fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        self.ax.text(0.5, 0.5, 'No data', ha='center', va='center',
                    transform=self.ax.transAxes, fontsize=14, color='gray')
        self.figure.tight_layout()
        self.canvas.draw()

    def _plot_curve(self):
        """Plot precision-recall curve."""
        self.ax.clear()

        # Extract similarities and ground truth
        similarities = [r.get('similarity', 0) for r in self.results]
        ground_truth = [1 if r['expected'] == 'duplicate' else 0 for r in self.results]

        # Get unique thresholds
        thresholds = sorted(set(similarities), reverse=True)

        # Calculate precision and recall at each threshold
        precisions = []
        recalls = []

        total_positives = sum(ground_truth)

        for threshold in thresholds:
            tp = fp = fn = 0

            for sim, truth in zip(similarities, ground_truth):
                if sim >= threshold:
                    if truth == 1:
                        tp += 1
                    else:
                        fp += 1
                elif truth == 1:
                    fn += 1

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / total_positives if total_positives > 0 else 0

            precisions.append(precision)
            recalls.append(recall)

        # Calculate AP (Average Precision)
        ap = 0
        for i in range(1, len(recalls)):
            ap += precisions[i] * (recalls[i] - recalls[i-1])

        # Plot curve
        self.ax.plot(recalls, precisions, 'b-', linewidth=2,
                    label=f'PR Curve (AP={ap:.3f})')

        # Plot baseline (random classifier)
        pos_ratio = total_positives / len(ground_truth) if ground_truth else 0
        self.ax.axhline(y=pos_ratio, color='k', linestyle='--', linewidth=1,
                       alpha=0.5, label=f'Random (P={pos_ratio:.2f})')

        # Styling
        self.ax.set_xlim([0.0, 1.0])
        self.ax.set_ylim([0.0, 1.05])
        self.ax.set_xlabel('Recall (TPR)', fontsize=11)
        self.ax.set_ylabel('Precision', fontsize=11)
        self.ax.set_title('Precision-Recall Curve', fontsize=13, fontweight='bold')
        self.ax.legend(loc='best', fontsize=9)
        self.ax.grid(True, alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw()


class SimilarityDistributionWidget(QWidget):
    """
    Similarity score distribution histogram.

    Shows distribution of similarity scores for duplicates vs non-duplicates.
    Helps identify optimal threshold and visualize class separation.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.results = []
        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("📊 <b>Distribution des Scores de Similarité</b>")
        title.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(title)

        if not MATPLOTLIB_AVAILABLE:
            warning = QLabel("⚠️ Matplotlib non disponible")
            warning.setStyleSheet("color: #FF5722; padding: 20px;")
            layout.addWidget(warning)
            return

        # Matplotlib canvas
        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        layout.addWidget(self.canvas)

        self._plot_empty()

    def set_results(self, results: List[Dict]):
        """Set results and plot distribution."""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.results = results
        if not results:
            self._plot_empty()
            return

        self._plot_distribution()

    def _plot_empty(self):
        """Plot empty placeholder."""
        self.ax.clear()
        self.ax.set_xlabel('Similarity Score', fontsize=11)
        self.ax.set_ylabel('Count', fontsize=11)
        self.ax.set_title('Similarity Distribution', fontsize=13, fontweight='bold')
        self.ax.grid(axis='y', alpha=0.3)
        self.figure.tight_layout()
        self.canvas.draw()

    def _plot_distribution(self):
        """Plot similarity distribution histogram."""
        self.ax.clear()

        # Separate duplicates and non-duplicates
        dup_sims = [r.get('similarity', 0) for r in self.results
                   if r['expected'] == 'duplicate']
        non_dup_sims = [r.get('similarity', 0) for r in self.results
                       if r['expected'] == 'not_duplicate']

        # Create bins
        bins = np.linspace(0, 1, 21)  # 20 bins

        # Plot histograms
        self.ax.hist(dup_sims, bins=bins, alpha=0.6, color='#4CAF50',
                    label=f'Duplicates (n={len(dup_sims)})', edgecolor='black')
        self.ax.hist(non_dup_sims, bins=bins, alpha=0.6, color='#F44336',
                    label=f'Non-duplicates (n={len(non_dup_sims)})', edgecolor='black')

        # Add median lines
        if dup_sims:
            dup_median = np.median(dup_sims)
            self.ax.axvline(dup_median, color='#4CAF50', linestyle='--',
                          linewidth=2, label=f'Dup median: {dup_median:.2f}')

        if non_dup_sims:
            non_dup_median = np.median(non_dup_sims)
            self.ax.axvline(non_dup_median, color='#F44336', linestyle='--',
                          linewidth=2, label=f'Non-dup median: {non_dup_median:.2f}')

        # Styling
        self.ax.set_xlabel('Similarity Score', fontsize=11)
        self.ax.set_ylabel('Frequency', fontsize=11)
        self.ax.set_title('Similarity Distribution by Class', fontsize=13, fontweight='bold')
        self.ax.legend(loc='best', fontsize=9)
        self.ax.grid(axis='y', alpha=0.3)
        self.ax.set_xlim([0, 1])

        self.figure.tight_layout()
        self.canvas.draw()


class PipelineComparisonWidget(QWidget):
    """
    Pipeline comparison bar chart.

    Compares multiple pipelines across key metrics (F1, Precision, Recall).
    Useful for selecting the best pipeline configuration.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pipeline_metrics = {}
        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("⚖️ <b>Comparaison des Pipelines</b>")
        title.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(title)

        if not MATPLOTLIB_AVAILABLE:
            warning = QLabel("⚠️ Matplotlib non disponible")
            warning.setStyleSheet("color: #FF5722; padding: 20px;")
            layout.addWidget(warning)
            return

        # Matplotlib canvas
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        layout.addWidget(self.canvas)

        self._plot_empty()

    def set_pipeline_metrics(self, pipeline_metrics: Dict[str, Dict]):
        """
        Set pipeline metrics and plot comparison.

        Args:
            pipeline_metrics: Dict mapping pipeline names to metrics dict
        """
        if not MATPLOTLIB_AVAILABLE:
            return

        self.pipeline_metrics = pipeline_metrics
        if not pipeline_metrics:
            self._plot_empty()
            return

        self._plot_comparison()

    def _plot_empty(self):
        """Plot empty placeholder."""
        self.ax.clear()
        self.ax.set_title('Pipeline Comparison', fontsize=13, fontweight='bold')
        self.ax.text(0.5, 0.5, 'No data', ha='center', va='center',
                    transform=self.ax.transAxes, fontsize=14, color='gray')
        self.figure.tight_layout()
        self.canvas.draw()

    def _plot_comparison(self):
        """Plot pipeline comparison chart."""
        self.ax.clear()

        # Extract data
        pipeline_names = list(self.pipeline_metrics.keys())
        f1_scores = [m.get('f1', 0) for m in self.pipeline_metrics.values()]
        precisions = [m.get('precision', 0) for m in self.pipeline_metrics.values()]
        recalls = [m.get('recall', 0) for m in self.pipeline_metrics.values()]

        # Set up bar positions
        x = np.arange(len(pipeline_names))
        width = 0.25

        # Create bars
        bars1 = self.ax.bar(x - width, f1_scores, width, label='F1 Score',
                           color='#2196F3', alpha=0.8)
        bars2 = self.ax.bar(x, precisions, width, label='Precision',
                           color='#4CAF50', alpha=0.8)
        bars3 = self.ax.bar(x + width, recalls, width, label='Recall',
                           color='#FF9800', alpha=0.8)

        # Add value labels on bars
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                height = bar.get_height()
                self.ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.2f}',
                           ha='center', va='bottom', fontsize=8)

        # Styling
        self.ax.set_ylabel('Score', fontsize=11)
        self.ax.set_title('Pipeline Performance Comparison', fontsize=13, fontweight='bold')
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(pipeline_names, rotation=45, ha='right')
        self.ax.legend(loc='best', fontsize=9)
        self.ax.set_ylim([0, 1.0])
        self.ax.grid(axis='y', alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw()


class MetricsTrendWidget(QWidget):
    """
    Time series metrics trend chart.

    Shows how metrics evolve over multiple benchmark runs.
    Useful for tracking improvements or detecting regressions.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.runs_history = []
        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)

        # Header with controls
        header_layout = QHBoxLayout()

        title = QLabel("📈 <b>Tendance des Métriques</b>")
        title.setStyleSheet("font-size: 14px; padding: 10px;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Metric selector
        if MATPLOTLIB_AVAILABLE:
            header_layout.addWidget(QLabel("Métrique:"))
            self.metric_combo = QComboBox()
            self.metric_combo.addItems(['F1 Score', 'Precision', 'Recall', 'Accuracy'])
            self.metric_combo.currentTextChanged.connect(self._on_metric_changed)
            header_layout.addWidget(self.metric_combo)

        layout.addLayout(header_layout)

        if not MATPLOTLIB_AVAILABLE:
            warning = QLabel("⚠️ Matplotlib non disponible")
            warning.setStyleSheet("color: #FF5722; padding: 20px;")
            layout.addWidget(warning)
            return

        # Matplotlib canvas
        self.figure = Figure(figsize=(10, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        layout.addWidget(self.canvas)

        self._plot_empty()

    def set_runs_history(self, runs_history: List[Dict]):
        """
        Set historical run data.

        Args:
            runs_history: List of run dicts with timestamp and metrics
        """
        if not MATPLOTLIB_AVAILABLE:
            return

        self.runs_history = runs_history
        if not runs_history:
            self._plot_empty()
            return

        self._plot_trend()

    def _plot_empty(self):
        """Plot empty placeholder."""
        self.ax.clear()
        self.ax.set_xlabel('Run Number', fontsize=11)
        self.ax.set_ylabel('Score', fontsize=11)
        self.ax.set_title('Metrics Trend Over Time', fontsize=13, fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        self.figure.tight_layout()
        self.canvas.draw()

    def _on_metric_changed(self, metric_name: str):
        """Handle metric selection change."""
        if self.runs_history:
            self._plot_trend()

    def _plot_trend(self):
        """Plot metrics trend."""
        self.ax.clear()

        if not self.runs_history:
            self._plot_empty()
            return

        # Get selected metric
        metric_display = self.metric_combo.currentText()
        metric_key = metric_display.lower().replace(' ', '_')

        # Extract data
        run_numbers = list(range(1, len(self.runs_history) + 1))
        values = [run['metrics'].get(metric_key, 0) for run in self.runs_history]

        # Plot line
        self.ax.plot(run_numbers, values, 'o-', linewidth=2, markersize=8,
                    color='#2196F3', label=metric_display)

        # Add trend line (linear regression)
        if len(values) > 2:
            z = np.polyfit(run_numbers, values, 1)
            p = np.poly1d(z)
            self.ax.plot(run_numbers, p(run_numbers), '--', linewidth=1.5,
                        color='red', alpha=0.7, label='Trend')

            # Show trend direction
            trend_direction = "↗" if z[0] > 0 else "↘"
            trend_text = f"Trend: {trend_direction} {abs(z[0]):.4f}/run"
            self.ax.text(0.02, 0.98, trend_text, transform=self.ax.transAxes,
                        fontsize=10, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # Styling
        self.ax.set_xlabel('Run Number', fontsize=11)
        self.ax.set_ylabel('Score', fontsize=11)
        self.ax.set_title(f'{metric_display} Trend Over Time',
                         fontsize=13, fontweight='bold')
        self.ax.legend(loc='best', fontsize=9)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_ylim([0, 1.05])

        self.figure.tight_layout()
        self.canvas.draw()


class PairAnalysisScatterWidget(QWidget):
    """
    Scatter plot for pair-level analysis.

    Shows individual pairs plotted by similarity vs expected label.
    Helps identify specific problematic pairs.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.results = []
        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("🔍 <b>Analyse par Paire</b>")
        title.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(title)

        if not MATPLOTLIB_AVAILABLE:
            warning = QLabel("⚠️ Matplotlib non disponible")
            warning.setStyleSheet("color: #FF5722; padding: 20px;")
            layout.addWidget(warning)
            return

        # Matplotlib canvas
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        layout.addWidget(self.canvas)

        self._plot_empty()

    def set_results(self, results: List[Dict]):
        """Set results and plot scatter."""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.results = results
        if not results:
            self._plot_empty()
            return

        self._plot_scatter()

    def _plot_empty(self):
        """Plot empty placeholder."""
        self.ax.clear()
        self.ax.set_xlabel('Pair Index', fontsize=11)
        self.ax.set_ylabel('Similarity Score', fontsize=11)
        self.ax.set_title('Pair-Level Analysis', fontsize=13, fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        self.figure.tight_layout()
        self.canvas.draw()

    def _plot_scatter(self):
        """Plot pair analysis scatter."""
        self.ax.clear()

        # Categorize pairs
        tp_x, tp_y = [], []
        fp_x, fp_y = [], []
        tn_x, tn_y = [], []
        fn_x, fn_y = [], []

        for i, result in enumerate(self.results):
            similarity = result.get('similarity', 0)
            expected = result['expected']
            predicted = 'duplicate' if result['is_match'] else 'not_duplicate'

            if expected == 'duplicate' and predicted == 'duplicate':
                tp_x.append(i)
                tp_y.append(similarity)
            elif expected == 'not_duplicate' and predicted == 'duplicate':
                fp_x.append(i)
                fp_y.append(similarity)
            elif expected == 'not_duplicate' and predicted == 'not_duplicate':
                tn_x.append(i)
                tn_y.append(similarity)
            elif expected == 'duplicate' and predicted == 'not_duplicate':
                fn_x.append(i)
                fn_y.append(similarity)

        # Plot each category
        if tp_x:
            self.ax.scatter(tp_x, tp_y, c='#4CAF50', marker='o', s=50,
                          alpha=0.6, label=f'TP ({len(tp_x)})')
        if fp_x:
            self.ax.scatter(fp_x, fp_y, c='#FF9800', marker='s', s=50,
                          alpha=0.6, label=f'FP ({len(fp_x)})')
        if tn_x:
            self.ax.scatter(tn_x, tn_y, c='#8BC34A', marker='o', s=50,
                          alpha=0.6, label=f'TN ({len(tn_x)})')
        if fn_x:
            self.ax.scatter(fn_x, fn_y, c='#F44336', marker='X', s=80,
                          alpha=0.8, label=f'FN ({len(fn_x)})')

        # Add threshold line (assume 0.5 for visualization)
        self.ax.axhline(y=0.5, color='black', linestyle='--', linewidth=1,
                       alpha=0.5, label='Threshold (0.5)')

        # Styling
        self.ax.set_xlabel('Pair Index', fontsize=11)
        self.ax.set_ylabel('Similarity Score', fontsize=11)
        self.ax.set_title('Pair-Level Classification Results', fontsize=13, fontweight='bold')
        self.ax.legend(loc='best', fontsize=9)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_ylim([0, 1])

        self.figure.tight_layout()
        self.canvas.draw()

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when widget is closed.

        Ensures proper cleanup of resources and signals.
        """
        # All signals are internal and auto-cleaned by Qt
        # Added for consistency with other widgets
        super().closeEvent(event)
