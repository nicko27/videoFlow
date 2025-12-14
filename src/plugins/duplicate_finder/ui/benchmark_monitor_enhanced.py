"""
Enhanced Benchmark Monitor Dialog - Interface améliorée avec toutes les infos sur une seule page

Cette fenêtre affiche une vue complète de l'exécution des benchmarks avec :
① Progression globale (barre totale + boutons contrôle)
② Progression des hashes (SHA-256, Frame Hash, DCT, SSIM, etc.)
③ Progression des pipelines (une barre par pipeline avec stats)
④ Métriques en temps réel (F1/Precision/Recall/Accuracy + confusion matrix)
⑤ Performance temps réel (breakdown du temps)
⑥ Temps par méthode (table des méthodes appelées)
⑦ Logs en temps réel (console auto-scroll)
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QWidget, QFrame, QScrollArea, QGridLayout, QPushButton,
    QTextEdit, QGroupBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtGui import QFont, QColor
from typing import Dict, List, Optional
import time
from datetime import datetime


class MetricCard(QFrame):
    """Carte pour afficher une métrique (F1, Precision, etc.)."""

    def __init__(self, title: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.title = title
        self.icon = icon

        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            MetricCard {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # Titre
        title_label = QLabel(f"{icon} {title}")
        title_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #495057;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Valeur principale
        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #212529;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)

        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #e9ecef;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Pourcentage
        self.percent_label = QLabel("0%")
        self.percent_label.setStyleSheet("font-size: 12px; color: #6c757d;")
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.percent_label)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

    def update_metric(self, value: float, threshold: float = 0.8):
        """Met à jour la métrique avec code couleur selon seuil."""
        self.value_label.setText(f"{value:.2f}")

        percent = int(value * 100)
        self.progress_bar.setValue(percent)
        self.percent_label.setText(f"{percent}%")

        # Code couleur selon seuil
        if value >= threshold:
            status_text = "🟢 PASS"
            status_color = "#28a745"
            chunk_color = "#28a745"
        elif value >= threshold * 0.9:
            status_text = "🟡 WARN"
            status_color = "#ffc107"
            chunk_color = "#ffc107"
        else:
            status_text = "🔴 FAIL"
            status_color = "#dc3545"
            chunk_color = "#dc3545"

        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {status_color};")

        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: #e9ecef;
            }}
            QProgressBar::chunk {{
                background-color: {chunk_color};
                border-radius: 4px;
            }}
        """)


class HashProgressWidget(QFrame):
    """Widget pour afficher la progression de tous les types de hash."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hash_bars = {}

        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            HashProgressWidget {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
            }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(6)

        # Titre
        title = QLabel("② PROGRESSION DES HASHES")
        title.setStyleSheet("font-weight: bold; font-size: 12px; color: #495057; padding-bottom: 5px;")
        self.layout.addWidget(title)

    def add_hash_type(self, hash_name: str):
        """Ajoute un type de hash à suivre."""
        if hash_name in self.hash_bars:
            return

        # Container pour cette ligne
        container = QWidget()
        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(8)

        # Label du nom
        label = QLabel(hash_name + ":")
        label.setFixedWidth(180)
        label.setStyleSheet("font-size: 11px; color: #495057;")
        h_layout.addWidget(label)

        # Barre de progression
        progress = QProgressBar()
        progress.setMaximum(100)
        progress.setValue(0)
        progress.setTextVisible(True)
        progress.setFormat("%p% (%v/%m)")
        progress.setFixedHeight(20)
        progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: #f8f9fa;
                text-align: center;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 3px;
            }
        """)
        h_layout.addWidget(progress)

        self.hash_bars[hash_name] = progress
        self.layout.addWidget(container)

    def update_hash(self, hash_name: str, current: int, total: int):
        """Met à jour la progression d'un type de hash."""
        if hash_name not in self.hash_bars:
            self.add_hash_type(hash_name)

        progress = self.hash_bars[hash_name]
        progress.setMaximum(max(1, total))
        progress.setValue(current)


class PipelineProgressCard(QFrame):
    """Carte pour afficher la progression d'un pipeline."""

    def __init__(self, pipeline_name: str, parent=None):
        super().__init__(parent)
        self.pipeline_name = pipeline_name

        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            PipelineProgressCard {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 8px;
                margin: 2px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # Header: nom + progression
        header_layout = QHBoxLayout()

        self.name_label = QLabel(f'Pipeline "{pipeline_name}":')
        self.name_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #212529;")
        header_layout.addWidget(self.name_label)

        header_layout.addStretch()

        self.progress_text = QLabel("0% (0/0)")
        self.progress_text.setStyleSheet("font-size: 10px; color: #6c757d;")
        header_layout.addWidget(self.progress_text)

        layout.addLayout(header_layout)

        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Stats: Accepted/Rejected/Errors
        stats_layout = QHBoxLayout()

        self.stats_label = QLabel("├─ Accepted: 0  Rejected: 0  Errors: 0")
        self.stats_label.setStyleSheet("font-size: 10px; color: #6c757d; padding-left: 5px;")
        stats_layout.addWidget(self.stats_label)

        layout.addLayout(stats_layout)

        # Current pair
        self.current_label = QLabel("└─ Waiting...")
        self.current_label.setStyleSheet("font-size: 10px; color: #6c757d; padding-left: 5px;")
        layout.addWidget(self.current_label)

    def update_progress(self, processed: int, total: int, accepted: int = 0, rejected: int = 0, errors: int = 0, current_pair: str = ""):
        """Met à jour la progression du pipeline."""
        # Progress bar
        self.progress_bar.setMaximum(max(1, total))
        self.progress_bar.setValue(processed)

        # Progress text
        percent = int((processed / max(1, total)) * 100)
        self.progress_text.setText(f"{percent}% ({processed}/{total})")

        # Stats
        self.stats_label.setText(f"├─ Accepted: {accepted}  Rejected: {rejected}  Errors: {errors}")

        # Current pair
        if current_pair:
            self.current_label.setText(f"└─ Current: {current_pair}")
        elif processed == total and total > 0:
            self.current_label.setText("└─ ✅ Completed")
        elif processed == 0:
            self.current_label.setText("└─ Waiting...")

        # Update icon in name
        if processed == total and total > 0:
            icon = "✅"
            chunk_color = "#28a745"
        elif processed > 0:
            icon = "▶️"
            chunk_color = "#007bff"
        else:
            icon = "⏳"
            chunk_color = "#6c757d"

        self.name_label.setText(f'{icon} Pipeline "{self.pipeline_name}":')

        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: #f8f9fa;
            }}
            QProgressBar::chunk {{
                background-color: {chunk_color};
                border-radius: 3px;
            }}
        """)


class EnhancedBenchmarkMonitor(QDialog):
    """
    Moniteur de benchmark amélioré - Tout sur une seule page.

    Structure:
    ① Progression globale
    ② Progression des hashes
    ③ Progression des pipelines
    ④ Métriques temps réel (F1/Precision/Recall/Accuracy)
    ⑤ Performance temps réel
    ⑥ Temps par méthode
    ⑦ Logs temps réel
    """

    # Signaux
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Benchmark Monitor - Enhanced")
        self.resize(1200, 900)

        self.start_time = None
        self.pipeline_cards = {}
        self.method_stats = {}  # {method_name: {'calls': 0, 'total_time': 0}}

        self.init_ui()

        # Timer pour mise à jour ETA
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_elapsed_time)
        self.update_timer.start(1000)  # Update every second

    def init_ui(self):
        """Initialise l'interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header = QLabel("BENCHMARK MONITOR")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #212529; padding: 5px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)

        # Scroll area pour tout le contenu
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #f8f9fa; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)

        # ① PROGRESSION GLOBALE
        scroll_layout.addWidget(self.create_global_progress_section())

        # ② PROGRESSION DES HASHES
        self.hash_widget = HashProgressWidget()
        scroll_layout.addWidget(self.hash_widget)

        # ③ PROGRESSION DES PIPELINES
        self.pipelines_section = self.create_pipelines_section()
        scroll_layout.addWidget(self.pipelines_section)

        # ④ MÉTRIQUES TEMPS RÉEL
        scroll_layout.addWidget(self.create_metrics_section())

        # ⑤ PERFORMANCE TEMPS RÉEL
        scroll_layout.addWidget(self.create_performance_section())

        # ⑥ TEMPS PAR MÉTHODE
        scroll_layout.addWidget(self.create_methods_section())

        # ⑦ LOGS TEMPS RÉEL
        scroll_layout.addWidget(self.create_logs_section())

        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def create_global_progress_section(self) -> QFrame:
        """Crée la section ① Progression globale."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 2px solid #007bff;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(8)

        # Titre
        title = QLabel("① PROGRESSION GLOBALE")
        title.setStyleSheet("font-weight: bold; font-size: 13px; color: #007bff;")
        layout.addWidget(title)

        # Barre de progression
        self.global_progress = QProgressBar()
        self.global_progress.setMaximum(100)
        self.global_progress.setValue(0)
        self.global_progress.setTextVisible(True)
        self.global_progress.setFormat("Overall Progress: %p% (%v/%m)")
        self.global_progress.setFixedHeight(35)
        self.global_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #007bff;
                border-radius: 6px;
                background-color: #e9ecef;
                text-align: center;
                font-size: 12px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #28a745, stop:1 #007bff);
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.global_progress)

        # Stats: Elapsed / ETA / Speed / Status
        stats_layout = QHBoxLayout()

        self.elapsed_label = QLabel("Elapsed: --")
        self.elapsed_label.setStyleSheet("font-size: 11px; color: #495057;")
        stats_layout.addWidget(self.elapsed_label)

        stats_layout.addWidget(QLabel("|"))

        self.eta_label = QLabel("ETA: --")
        self.eta_label.setStyleSheet("font-size: 11px; color: #495057;")
        stats_layout.addWidget(self.eta_label)

        stats_layout.addWidget(QLabel("|"))

        self.speed_label = QLabel("Speed: -- pairs/sec")
        self.speed_label.setStyleSheet("font-size: 11px; color: #495057;")
        stats_layout.addWidget(self.speed_label)

        stats_layout.addWidget(QLabel("|"))

        self.status_label = QLabel("Status: ⏸️ Ready")
        self.status_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #495057;")
        stats_layout.addWidget(self.status_label)

        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        # Boutons de contrôle
        buttons_layout = QHBoxLayout()

        self.start_btn = QPushButton("▶ Start")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.start_btn.setEnabled(False)  # Disabled by default
        buttons_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        buttons_layout.addWidget(self.stop_btn)

        self.reset_btn = QPushButton("↻ Reset")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.reset_btn.setEnabled(False)
        buttons_layout.addWidget(self.reset_btn)

        self.export_btn = QPushButton("💾 Export Results")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.export_btn.setEnabled(False)
        buttons_layout.addWidget(self.export_btn)

        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

        return frame

    def create_pipelines_section(self) -> QFrame:
        """Crée la section ③ Progression des pipelines."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(6)

        # Titre
        title = QLabel("③ PROGRESSION DES PIPELINES")
        title.setStyleSheet("font-weight: bold; font-size: 12px; color: #495057; padding-bottom: 5px;")
        layout.addWidget(title)

        # Container pour les cartes de pipelines
        self.pipelines_container = QVBoxLayout()
        self.pipelines_container.setSpacing(6)
        layout.addLayout(self.pipelines_container)

        return frame

    def create_metrics_section(self) -> QFrame:
        """Crée la section ④ Métriques temps réel."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(8)

        # Titre
        title = QLabel("④ MÉTRIQUES EN TEMPS RÉEL")
        title.setStyleSheet("font-weight: bold; font-size: 12px; color: #495057; padding-bottom: 5px;")
        layout.addWidget(title)

        # Cartes de métriques
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        self.f1_card = MetricCard("F1 SCORE", "🎯")
        cards_layout.addWidget(self.f1_card)

        self.precision_card = MetricCard("PRECISION", "✓")
        cards_layout.addWidget(self.precision_card)

        self.recall_card = MetricCard("RECALL", "📊")
        cards_layout.addWidget(self.recall_card)

        self.accuracy_card = MetricCard("ACCURACY", "⚡")
        cards_layout.addWidget(self.accuracy_card)

        layout.addLayout(cards_layout)

        # Confusion matrix
        confusion_frame = QFrame()
        confusion_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        confusion_layout = QHBoxLayout(confusion_frame)

        self.tp_label = QLabel("TP: 0")
        self.tp_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #28a745;")
        confusion_layout.addWidget(self.tp_label)

        confusion_layout.addWidget(QLabel("|"))

        self.fp_label = QLabel("FP: 0")
        self.fp_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #dc3545;")
        confusion_layout.addWidget(self.fp_label)

        confusion_layout.addWidget(QLabel("|"))

        self.tn_label = QLabel("TN: 0")
        self.tn_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #28a745;")
        confusion_layout.addWidget(self.tn_label)

        confusion_layout.addWidget(QLabel("|"))

        self.fn_label = QLabel("FN: 0")
        self.fn_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #dc3545;")
        confusion_layout.addWidget(self.fn_label)

        confusion_layout.addWidget(QLabel("|"))

        self.total_label = QLabel("Total: 0")
        self.total_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #495057;")
        confusion_layout.addWidget(self.total_label)

        confusion_layout.addStretch()

        layout.addWidget(confusion_frame)

        return frame

    def create_performance_section(self) -> QFrame:
        """Crée la section ⑤ Performance temps réel."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(6)

        # Titre
        title = QLabel("⑤ PERFORMANCE TEMPS RÉEL")
        title.setStyleSheet("font-weight: bold; font-size: 12px; color: #495057; padding-bottom: 5px;")
        layout.addWidget(title)

        # Total time
        self.total_time_label = QLabel("Total Time: --")
        self.total_time_label.setStyleSheet("font-size: 11px; color: #495057; padding-bottom: 5px;")
        layout.addWidget(self.total_time_label)

        # Progress bars pour breakdown
        # Hash precompute
        hash_container = QWidget()
        hash_layout = QHBoxLayout(hash_container)
        hash_layout.setContentsMargins(0, 0, 0, 0)
        hash_layout.setSpacing(8)

        hash_label = QLabel("Hash precompute:")
        hash_label.setFixedWidth(150)
        hash_label.setStyleSheet("font-size: 10px; color: #495057;")
        hash_layout.addWidget(hash_label)

        self.hash_perf_bar = QProgressBar()
        self.hash_perf_bar.setMaximum(100)
        self.hash_perf_bar.setValue(0)
        self.hash_perf_bar.setTextVisible(True)
        self.hash_perf_bar.setFormat("0s (0%)")
        self.hash_perf_bar.setFixedHeight(18)
        self.hash_perf_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 3px;
                background-color: #f8f9fa;
                text-align: center;
                font-size: 9px;
            }
            QProgressBar::chunk {
                background-color: #ff9800;
                border-radius: 2px;
            }
        """)
        hash_layout.addWidget(self.hash_perf_bar)

        layout.addWidget(hash_container)

        # Pipeline execution
        pipeline_container = QWidget()
        pipeline_layout = QHBoxLayout(pipeline_container)
        pipeline_layout.setContentsMargins(0, 0, 0, 0)
        pipeline_layout.setSpacing(8)

        pipeline_label = QLabel("Pipeline execution:")
        pipeline_label.setFixedWidth(150)
        pipeline_label.setStyleSheet("font-size: 10px; color: #495057;")
        pipeline_layout.addWidget(pipeline_label)

        self.pipeline_perf_bar = QProgressBar()
        self.pipeline_perf_bar.setMaximum(100)
        self.pipeline_perf_bar.setValue(0)
        self.pipeline_perf_bar.setTextVisible(True)
        self.pipeline_perf_bar.setFormat("0s (0%)")
        self.pipeline_perf_bar.setFixedHeight(18)
        self.pipeline_perf_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 3px;
                background-color: #f8f9fa;
                text-align: center;
                font-size: 9px;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 2px;
            }
        """)
        pipeline_layout.addWidget(self.pipeline_perf_bar)

        layout.addWidget(pipeline_container)

        # Results processing
        results_container = QWidget()
        results_layout = QHBoxLayout(results_container)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(8)

        results_label = QLabel("Results processing:")
        results_label.setFixedWidth(150)
        results_label.setStyleSheet("font-size: 10px; color: #495057;")
        results_layout.addWidget(results_label)

        self.results_perf_bar = QProgressBar()
        self.results_perf_bar.setMaximum(100)
        self.results_perf_bar.setValue(0)
        self.results_perf_bar.setTextVisible(True)
        self.results_perf_bar.setFormat("0s (0%)")
        self.results_perf_bar.setFixedHeight(18)
        self.results_perf_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 3px;
                background-color: #f8f9fa;
                text-align: center;
                font-size: 9px;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 2px;
            }
        """)
        results_layout.addWidget(self.results_perf_bar)

        layout.addWidget(results_container)

        # Stats
        self.perf_stats_label = QLabel("Average per pair: --  |  Fastest: --  |  Slowest: --")
        self.perf_stats_label.setStyleSheet("font-size: 10px; color: #6c757d; padding-top: 5px;")
        layout.addWidget(self.perf_stats_label)

        self.cache_stats_label = QLabel("Cache hit rate: -- (--%)  |  Saved time: ~--")
        self.cache_stats_label.setStyleSheet("font-size: 10px; color: #6c757d;")
        layout.addWidget(self.cache_stats_label)

        return frame

    def create_methods_section(self) -> QFrame:
        """Crée la section ⑥ Temps par méthode."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(6)

        # Titre
        title = QLabel("⑥ TEMPS PAR MÉTHODE")
        title.setStyleSheet("font-weight: bold; font-size: 12px; color: #495057; padding-bottom: 5px;")
        layout.addWidget(title)

        # Table des méthodes (scrollable)
        self.methods_text = QTextEdit()
        self.methods_text.setReadOnly(True)
        self.methods_text.setFixedHeight(150)
        self.methods_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
                color: #212529;
                padding: 5px;
            }
        """)
        self.methods_text.setPlainText("Method                  Calls  Avg Time  Total   % of Total\n" +
                                       "─" * 70 + "\n" +
                                       "No data yet...")
        layout.addWidget(self.methods_text)

        return frame

    def create_logs_section(self) -> QFrame:
        """Crée la section ⑦ Logs temps réel."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(6)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("⑦ LOGS EN TEMPS RÉEL")
        title.setStyleSheet("font-weight: bold; font-size: 12px; color: #495057;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        clear_btn = QPushButton("Clear Logs")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 12px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        clear_btn.clicked.connect(self.clear_logs)
        header_layout.addWidget(clear_btn)

        export_logs_btn = QPushButton("💾 Export Logs")
        export_logs_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 12px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        header_layout.addWidget(export_logs_btn)

        layout.addLayout(header_layout)

        # Console de logs
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFixedHeight(200)
        self.logs_text.setStyleSheet("""
            QTextEdit {
                background-color: #212529;
                border: 1px solid #495057;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
                color: #f8f9fa;
                padding: 5px;
            }
        """)
        layout.addWidget(self.logs_text)

        return frame

    # ============= SLOTS PUBLICS =============

    @pyqtSlot(int, int, str)
    def update_hash_progress(self, current: int, total: int, pipeline_name: str):
        """Met à jour la progression d'un type de hash."""
        # Extract hash type from pipeline emissions
        # Pour l'instant, on utilise un hash générique "SHA-256"
        # TODO: détecter le vrai type de hash depuis les émissions
        self.hash_widget.update_hash("SHA-256", current, total)
        self.add_log("INFO", f"Hash progress: {current}/{total} for {pipeline_name}")

    @pyqtSlot(int, int, str)
    def update_pipeline_progress(self, current: int, total: int, pipeline_name: str):
        """
        Met à jour la progression d'un pipeline.

        Signal signature: (int current, int total, str pipeline_name)
        """
        if pipeline_name not in self.pipeline_cards:
            card = PipelineProgressCard(pipeline_name)
            self.pipeline_cards[pipeline_name] = card
            self.pipelines_container.addWidget(card)

        card = self.pipeline_cards[pipeline_name]

        # On n'a pas les stats accepted/rejected dans ce signal
        # On les mettra à jour via update_metrics
        card.update_progress(current, total, 0, 0, 0, "")

        # Update global progress
        self.update_global_progress()

    @pyqtSlot(str, dict)
    def update_metrics(self, pipeline_name: str, metrics: dict):
        """
        Met à jour les métriques (F1, Precision, Recall, etc.).

        Signal signature: (str pipeline_name, dict metrics)
        """
        tp = metrics.get('tp', 0)
        fp = metrics.get('fp', 0)
        tn = metrics.get('tn', 0)
        fn = metrics.get('fn', 0)

        # Update confusion matrix labels
        self.tp_label.setText(f"TP: {tp}")
        self.fp_label.setText(f"FP: {fp}")
        self.tn_label.setText(f"TN: {tn}")
        self.fn_label.setText(f"FN: {fn}")
        self.total_label.setText(f"Total: {tp + fp + tn + fn}")

        # Calculate metrics
        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        accuracy = ((tp + tn) / (tp + fp + tn + fn)) if (tp + fp + tn + fn) > 0 else 0.0

        # Update metric cards
        self.f1_card.update_metric(f1, threshold=0.8)
        self.precision_card.update_metric(precision, threshold=0.7)
        self.recall_card.update_metric(recall, threshold=0.7)
        self.accuracy_card.update_metric(accuracy, threshold=0.75)

        # Update pipeline card stats (accepted/rejected from metrics)
        if pipeline_name in self.pipeline_cards:
            card = self.pipeline_cards[pipeline_name]
            accepted = metrics.get('accepted', 0)
            rejected = metrics.get('rejected', 0)
            errors = 0  # TODO: ajouter dans metrics

            # Keep current progress values
            current = card.progress_bar.value()
            total = card.progress_bar.maximum()

            card.update_progress(current, total, accepted, rejected, errors, "")

    def update_global_progress(self):
        """Met à jour la barre de progression globale."""
        # Calculer progression totale de tous les pipelines
        total_pairs = 0
        processed_pairs = 0

        for card in self.pipeline_cards.values():
            total_pairs += card.progress_bar.maximum()
            processed_pairs += card.progress_bar.value()

        if total_pairs > 0:
            self.global_progress.setMaximum(total_pairs)
            self.global_progress.setValue(processed_pairs)

            # Update ETA
            if processed_pairs > 0 and self.start_time:
                elapsed = time.time() - self.start_time
                speed = processed_pairs / elapsed
                remaining = total_pairs - processed_pairs
                eta_seconds = remaining / speed if speed > 0 else 0

                self.speed_label.setText(f"Speed: {speed:.2f} pairs/sec")

                eta_minutes = int(eta_seconds // 60)
                eta_secs = int(eta_seconds % 60)
                self.eta_label.setText(f"ETA: {eta_minutes}m {eta_secs}s")

    def update_elapsed_time(self):
        """Met à jour le temps écoulé (appelé par timer)."""
        if self.start_time:
            elapsed = time.time() - self.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.elapsed_label.setText(f"Elapsed: {minutes}m {seconds}s")
            self.total_time_label.setText(f"Total Time: {elapsed:.1f}s")

    def add_log(self, level: str, message: str):
        """Ajoute une ligne de log avec timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Color code par niveau
        if level == "ERROR":
            color = "#dc3545"
            icon = "❌"
        elif level == "WARN":
            color = "#ffc107"
            icon = "⚠️"
        elif level == "INFO":
            color = "#28a745"
            icon = "✅"
        else:
            color = "#6c757d"
            icon = "ℹ️"

        log_line = f'<span style="color: #6c757d;">[{timestamp}]</span> <span style="color: {color}; font-weight: bold;">{level}</span> {icon} {message}'

        self.logs_text.append(log_line)

        # Auto-scroll to bottom
        scrollbar = self.logs_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_logs(self):
        """Efface les logs."""
        self.logs_text.clear()
        self.add_log("INFO", "Logs cleared")

    def on_stop_clicked(self):
        """Gère le clic sur Stop."""
        self.add_log("WARN", "Stop requested by user")
        self.status_label.setText("Status: 🛑 Stopping...")
        self.stop_requested.emit()

    def start_benchmark(self):
        """Démarre le benchmark (appelé de l'extérieur)."""
        self.start_time = time.time()
        self.status_label.setText("Status: ● Running")
        self.status_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #28a745;")
        self.add_log("INFO", "Benchmark started")

    def finish_benchmark(self):
        """Termine le benchmark (appelé de l'extérieur)."""
        self.status_label.setText("Status: ✅ Completed")
        self.status_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #007bff;")
        self.export_btn.setEnabled(True)

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when dialog is closed.

        Stops timer and ensures proper memory cleanup.
        """
        # Stop and disconnect timer
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
            try:
                self.update_timer.timeout.disconnect()
            except (RuntimeError, TypeError):
                pass

        super().closeEvent(event)
