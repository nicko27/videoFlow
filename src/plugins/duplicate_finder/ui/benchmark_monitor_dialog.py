"""
Benchmark Monitor Dialog - Fenêtre popup de monitoring des benchmarks en temps réel

Cette fenêtre affiche une vue détaillée de l'exécution des benchmarks avec :
- Dashboard global avec métriques agrégées
- Timeline chronologique de l'avancement
- Cartes détaillées par pipeline avec métriques en temps réel
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QWidget, QFrame, QScrollArea, QGridLayout, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont
from typing import Dict, List
import time


class DashboardTile(QFrame):
    """Tuile du dashboard global."""

    def __init__(self, icon: str, title: str, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        self.setStyleSheet("""
            DashboardTile {
                background-color: #f5f5f5;
                border: 2px solid #2196F3;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)

        # Header avec icône
        header = QLabel(f"{icon} {title}")
        header.setStyleSheet("font-weight: bold; font-size: 12px; color: #2196F3;")
        layout.addWidget(header)

        # Valeur principale
        self.main_value = QLabel("--")
        self.main_value.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        self.main_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.main_value)

        # Valeur secondaire
        self.sub_value = QLabel("")
        self.sub_value.setStyleSheet("font-size: 11px; color: #666;")
        self.sub_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sub_value)

        layout.addStretch()

    def update_values(self, main: str, sub: str = ""):
        """Met à jour les valeurs affichées."""
        self.main_value.setText(main)
        self.sub_value.setText(sub)


class TimelineWidget(QWidget):
    """Widget de timeline chronologique."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pipelines = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("⏰ TIMELINE CHRONOLOGIQUE")
        header.setStyleSheet("font-weight: bold; font-size: 13px; color: #2196F3; padding: 5px;")
        layout.addWidget(header)

        # Global timeline bar
        self.global_timeline = QProgressBar()
        self.global_timeline.setTextVisible(True)
        self.global_timeline.setFormat("%p% - %v/%m paires")
        self.global_timeline.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2196F3;
                border-radius: 5px;
                text-align: center;
                height: 30px;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #2196F3);
            }
        """)
        layout.addWidget(self.global_timeline)

        # Temps écoulé
        self.elapsed_label = QLabel("⏱️ Écoulé: --")
        self.elapsed_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(self.elapsed_label)

        # Barre de pré-calcul/hash
        self.hash_progress = QProgressBar()
        self.hash_progress.setTextVisible(True)
        self.hash_progress.setFormat("Pré-calcul des signatures: %p% (%v/%m)")
        self.hash_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bbb;
                border-radius: 4px;
                text-align: center;
                background-color: #fafafa;
                height: 16px;
            }
            QProgressBar::chunk { background-color: #FF9800; }
        """)
        self.hash_progress.setVisible(True)
        layout.addWidget(self.hash_progress)

        # Pipelines progress bars
        self.pipelines_area = QVBoxLayout()
        layout.addLayout(self.pipelines_area)

        layout.addStretch()

    def add_pipeline(self, name: str):
        """Ajoute une progress bar pour un pipeline."""
        # Container pour ce pipeline
        pipeline_container = QWidget()
        pipeline_layout = QVBoxLayout(pipeline_container)
        pipeline_layout.setContentsMargins(5, 5, 5, 5)
        pipeline_layout.setSpacing(2)

        # Nom du pipeline
        name_label = QLabel(f"⏳ {name}")
        name_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        pipeline_layout.addWidget(name_label)

        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("%v/%m paires")
        progress_bar.setMaximumHeight(18)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
                background-color: #f5f5f5;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
            }
        """)
        pipeline_layout.addWidget(progress_bar)

        self.pipelines[name] = {
            'name_label': name_label,
            'progress_bar': progress_bar,
            'container': pipeline_container
        }

        self.pipelines_area.addWidget(pipeline_container)

    def update_pipeline(self, name: str, processed: int, total: int, metrics: dict):
        """Met à jour la progress bar d'un pipeline."""
        if name not in self.pipelines:
            return

        p = self.pipelines[name]

        # Update progress bar
        p['progress_bar'].setMaximum(total)
        p['progress_bar'].setValue(processed)

        # Update status icon
        if processed == total:
            icon = "✅"
        elif processed > 0:
            icon = "▶️"
        else:
            icon = "⏳"

        p['name_label'].setText(f"{icon} {name}")

    def update_hash(self, current: int, total: int, _name: str):
        """Met à jour la barre de pré-calcul des signatures (hashs)."""
        self.hash_progress.setMaximum(total)
        self.hash_progress.setValue(current)


class PipelineDetailCard(QFrame):
    """Carte détaillée pour un pipeline."""

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        self.setStyleSheet("""
            PipelineDetailCard {
                background-color: white;
                border: 2px solid #2196F3;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }
        """)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Header: Name + Status
        header_layout = QHBoxLayout()
        self.name_label = QLabel(f"⏳ {self.name}")
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2196F3;")

        self.status_label = QLabel("0/0")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")

        header_layout.addWidget(self.name_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        layout.addLayout(header_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Métriques section
        metrics_group = QGroupBox("📊 Métriques")
        metrics_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        metrics_layout = QVBoxLayout(metrics_group)

        # F1, Precision, Recall
        self.f1_label = QLabel("F1-Score: --")
        self.precision_label = QLabel("Precision: --")
        self.recall_label = QLabel("Recall: --")

        perf_layout = QHBoxLayout()
        perf_layout.addWidget(self.f1_label)
        perf_layout.addWidget(self.precision_label)
        perf_layout.addWidget(self.recall_label)
        metrics_layout.addLayout(perf_layout)

        # TP/FP/TN/FN
        self.confusion_label = QLabel("✅ TP: 0   ❌ FP: 0   ✅ TN: 0   ❌ FN: 0")
        metrics_layout.addWidget(self.confusion_label)

        layout.addWidget(metrics_group)

        # Performance section
        perf_group = QGroupBox("⚡ Performance")
        perf_group.setStyleSheet(metrics_group.styleSheet())
        perf_layout = QVBoxLayout(perf_group)

        self.speed_label = QLabel("Vitesse: --")
        self.eta_label = QLabel("Temps restant: --")
        self.total_time_label = QLabel("Temps total estimé: --")

        perf_layout.addWidget(self.speed_label)
        perf_layout.addWidget(self.eta_label)
        perf_layout.addWidget(self.total_time_label)

        layout.addWidget(perf_group)

        # Last action
        self.last_action_label = QLabel("💬 Dernière action: --")
        self.last_action_label.setStyleSheet("font-size: 10px; color: #666; font-style: italic;")
        layout.addWidget(self.last_action_label)

    def update_metrics(self, processed: int, total: int, metrics: dict):
        """Met à jour les métriques de la carte."""
        # Update progress
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(processed)
        self.status_label.setText(f"{processed}/{total}")

        # Update status icon
        if processed == total:
            icon = "✅"
        elif processed > 0:
            icon = "▶️"
        else:
            icon = "⏳"

        self.name_label.setText(f"{icon} {self.name}")

        # Update metrics
        tp = metrics.get('tp', 0)
        fp = metrics.get('fp', 0)
        tn = metrics.get('tn', 0)
        fn = metrics.get('fn', 0)
        precision = metrics.get('precision', 0)
        recall = metrics.get('recall', 0)
        f1 = metrics.get('f1', 0)
        speed = metrics.get('speed', 0)
        eta = metrics.get('eta', 0)

        # F1 with color
        if f1 >= 90:
            f1_color = "#4CAF50"
            f1_icon = "🏆"
        elif f1 >= 75:
            f1_color = "#FFC107"
            f1_icon = ""
        else:
            f1_color = "#F44336"
            f1_icon = ""

        self.f1_label.setText(f"F1-Score: {f1:.1f}% {f1_icon}")
        self.f1_label.setStyleSheet(f"color: {f1_color}; font-weight: bold;")

        self.precision_label.setText(f"Precision: {precision:.1f}%")
        self.recall_label.setText(f"Recall: {recall:.1f}%")

        self.confusion_label.setText(f"✅ TP: {tp}   ❌ FP: {fp}   ✅ TN: {tn}   ❌ FN: {fn}")

        # Performance
        if speed > 0:
            pairs_per_min = 60 / speed
            self.speed_label.setText(f"Vitesse: {speed:.1f}s/paire  ({pairs_per_min:.0f} paires/min)")

        if eta < 60:
            eta_text = f"{eta:.0f}s"
        elif eta < 3600:
            eta_text = f"{eta/60:.1f}min"
        else:
            eta_text = f"{eta/3600:.1f}h"

        remaining = total - processed
        self.eta_label.setText(f"Temps restant: ~{eta_text}  ({remaining} paires à traiter)")

        if speed > 0:
            total_time = speed * total
            if total_time < 60:
                total_text = f"{total_time:.0f}s"
            elif total_time < 3600:
                total_text = f"{total_time/60:.1f}min"
            else:
                total_text = f"{total_time/3600:.1f}h"
            self.total_time_label.setText(f"Temps total estimé: ~{total_text}")


class BenchmarkMonitorDialog(QDialog):
    """
    Fenêtre popup de monitoring des benchmarks en temps réel.

    Affiche :
    - Dashboard global avec 4 tuiles
    - Timeline chronologique
    - Cartes détaillées par pipeline
    """

    def __init__(self, test_set_name: str, pipelines: List[Dict], parent=None):
        super().__init__(parent)
        self.test_set_name = test_set_name
        self.pipelines_config = pipelines
        self.pipeline_cards = {}
        self.start_time = time.time()
        self.completed_pipelines = set()  # Track completed pipelines

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"🚀 Benchmark Monitor - {self.test_set_name}")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("""
            QDialog {
                background-color: #fafafa;
            }
        """)

        # Main layout for the dialog
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        # Create scroll area for all content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #fafafa;
            }
        """)

        # Content widget
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Zone 1: Timeline (50% height)
        timeline_frame = QFrame()
        timeline_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        timeline_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #2196F3;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        timeline_layout = QVBoxLayout(timeline_frame)

        self.timeline = TimelineWidget()
        timeline_layout.addWidget(self.timeline)

        main_layout.addWidget(timeline_frame, stretch=1)

        # Ajouter les pipelines à la timeline
        for pipeline in self.pipelines_config:
            name = pipeline['name']
            self.timeline.add_pipeline(name)

        main_layout.addStretch()

        # Set content widget into the main scroll area
        scroll_area.setWidget(content_widget)

        # Add scroll area to dialog layout
        dialog_layout.addWidget(scroll_area)

    @pyqtSlot(int, int, str)
    def on_pipeline_progress(self, current: int, total: int, pipeline_name: str):
        """Slot pour la progression d'un pipeline."""
        # Update individual pipeline progress in timeline
        self.timeline.update_pipeline(pipeline_name, current, total, {})

    @pyqtSlot(int, int, str)
    def on_hash_progress(self, current: int, total: int, pipeline_name: str):
        """Slot pour la progression du pré-calcul (hash/signatures)."""
        self.timeline.update_hash(current, total, pipeline_name)

        # Update global timeline based on actual progress bars
        total_pairs = sum([
            p['progress_bar'].maximum()
            for p in self.timeline.pipelines.values()
            if 'progress_bar' in p and p['progress_bar'].maximum() > 0
        ])

        processed_pairs = sum([
            p['progress_bar'].value()
            for p in self.timeline.pipelines.values()
            if 'progress_bar' in p
        ])

        if total_pairs > 0:
            self.timeline.global_timeline.setMaximum(total_pairs)
            self.timeline.global_timeline.setValue(processed_pairs)

        # Update elapsed time
        elapsed = time.time() - self.start_time
        if elapsed < 60:
            elapsed_text = f"{elapsed:.0f}s"
        elif elapsed < 3600:
            elapsed_text = f"{elapsed/60:.1f}min"
        else:
            elapsed_text = f"{elapsed/3600:.1f}h"

        self.timeline.elapsed_label.setText(f"⏱️ Écoulé: {elapsed_text}")

    @pyqtSlot(str, dict)
    def on_pipeline_metrics_updated(self, pipeline_name: str, metrics: dict):
        """Slot pour la mise à jour des métriques d'un pipeline."""
        processed = metrics.get('processed', 0)
        total = metrics.get('total', 0)

        print(f"📊 [POPUP] Updating {pipeline_name}: {processed}/{total} pairs")

        # Update timeline
        self.timeline.update_pipeline(pipeline_name, processed, total, metrics)

        # Update global dashboard
        self._update_global_dashboard()

    @pyqtSlot(str, dict)
    def on_pipeline_completed(self, pipeline_name: str, results: dict):
        """Slot appelé quand un pipeline est complété."""
        self.completed_pipelines.add(pipeline_name)

        # Check if all pipelines are completed
        if len(self.completed_pipelines) == len(self.pipelines_config):
            # All pipelines completed - close dialog after 3 seconds
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(3000, self.accept)  # Close with accept status after 3 seconds

    def _update_global_dashboard(self):
        """Met à jour le dashboard global (vide maintenant que le dashboard est supprimé)."""
        # Dashboard tiles removed - this method is kept for compatibility
        pass

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when dialog is closed.

        Ensures proper cleanup of resources and signals.
        """
        # All signals are internal and auto-cleaned by Qt
        # Added for consistency with other dialogs
        super().closeEvent(event)
