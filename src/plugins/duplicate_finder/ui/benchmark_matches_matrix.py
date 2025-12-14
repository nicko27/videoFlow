"""
Benchmark Matches Matrix Dialog - Affichage matriciel des résultats
"""
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.BenchmarkMatchesMatrix')


class BenchmarkMatchesMatrixDialog(QDialog):
    """
    Dialogue affichant une matrice des matches entre vidéos.

    Lignes: Vidéos courtes (video1)
    Colonnes: Vidéos longues (video2)
    Cellules: Pipeline + Score si match trouvé
    """

    def __init__(self, results: list, parent=None):
        """
        Args:
            results: Liste des résultats de benchmark
            parent: Widget parent
        """
        super().__init__(parent)
        self.results = results
        self.show_all_pairs = True  # Par défaut, afficher toutes les paires
        self.show_only_errors = False
        self.pipeline_filter = None
        self.show_details = False

        self.setWindowTitle("📊 Matrice des Matches - Résultats Benchmark")
        self.setMinimumSize(1200, 800)

        self._setup_ui()
        self._populate_matrix()

    def _setup_ui(self):
        """Configure l'interface."""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("📊 Matrice des Matches")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Filtres
        self.show_all_checkbox = QCheckBox("Afficher toutes les paires testées")
        self.show_all_checkbox.setChecked(self.show_all_pairs)
        self.show_all_checkbox.stateChanged.connect(self._on_show_all_changed)
        header_layout.addWidget(self.show_all_checkbox)

        self.show_errors_checkbox = QCheckBox("Seulement erreurs (FP/FN)")
        self.show_errors_checkbox.setChecked(self.show_only_errors)
        self.show_errors_checkbox.stateChanged.connect(self._on_show_errors_changed)
        header_layout.addWidget(self.show_errors_checkbox)

        self.details_checkbox = QCheckBox("Détails (par méthode)")
        self.details_checkbox.setChecked(self.show_details)
        self.details_checkbox.stateChanged.connect(self._on_show_details_changed)
        header_layout.addWidget(self.details_checkbox)

        self.pipeline_combo = QComboBox()
        self.pipeline_combo.addItem("Tous les pipelines", None)
        self._populate_pipeline_filter()
        self.pipeline_combo.currentIndexChanged.connect(self._on_pipeline_changed)
        header_layout.addWidget(QLabel("Pipeline:"))
        header_layout.addWidget(self.pipeline_combo)

        # Close button
        close_btn = QPushButton("✖ Fermer")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        header_layout.addWidget(close_btn)

        layout.addLayout(header_layout)

        # Legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Légende:"))

        # Color samples par statut
        for label, color in [
            ("TP", "#C8E6C9"),
            ("TN", "#E0E0E0"),
            ("FP", "#FFCDD2"),
            ("FN", "#FFE0B2"),
            ("UNK", "#BBDEFB"),
        ]:
            color_label = QLabel(f"  {label}  ")
            color_label.setStyleSheet(f"background-color: {color}; border: 1px solid #ccc; padding: 2px 8px;")
            legend_layout.addWidget(color_label)

        legend_layout.addStretch()
        layout.addLayout(legend_layout)

        # Matrix table
        self.matrix_table = QTableWidget()
        self.matrix_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                gridline-color: #ddd;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.matrix_table)

        # Footer with stats
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("font-style: italic; color: #666; padding: 8px;")
        layout.addWidget(self.stats_label)

    def _on_show_all_changed(self, state):
        """Callback quand la checkbox change."""
        self.show_all_pairs = (state == Qt.CheckState.Checked.value)
        self._populate_matrix()

    def _on_show_errors_changed(self, state):
        """Afficher uniquement FP/FN si coché."""
        self.show_only_errors = (state == Qt.CheckState.Checked.value)
        self._populate_matrix()

    def _on_show_details_changed(self, state):
        """Afficher ou masquer les détails par méthode."""
        self.show_details = (state == Qt.CheckState.Checked.value)
        self._populate_matrix()

    def _on_pipeline_changed(self, _idx):
        """Filtre pipeline."""
        self.pipeline_filter = self.pipeline_combo.currentData()
        self._populate_matrix()

    def _populate_pipeline_filter(self):
        """Remplit la liste des pipelines disponibles."""
        names = set()
        for result in self.results:
            names.add(result.get('pipeline_name'))
        for name in sorted(names):
            self.pipeline_combo.addItem(name, name)

    def _populate_matrix(self):
        """Remplit la matrice avec les résultats."""
        # Collecter toutes les paires et leurs résultats
        pairs_data = {}  # (video1, video2) -> [(pipeline, score, accepted, status, expected, confirmation)]
        all_video1 = set()
        all_video2 = set()

        for result in self.results:
            pipeline_name = result['pipeline_name']
            if self.pipeline_filter and pipeline_name != self.pipeline_filter:
                continue
            per_pair_results = result.get('per_pair_results', [])

            for pair_result in per_pair_results:
                video1 = pair_result.get('video1', pair_result.get('video1_path', ''))
                video2 = pair_result.get('video2', pair_result.get('video2_path', ''))
                accepted = pair_result.get('accepted', pair_result.get('is_match', False))
                score = pair_result.get('weighted_score', pair_result.get('similarity', 0))
                expected = pair_result.get('expected', 'unknown')

                status = self._compute_status(expected, accepted)

                # Filter based on show_all_pairs / errors only
                if not self.show_all_pairs and not accepted:
                    continue
                if self.show_only_errors and status not in ("FP", "FN"):
                    continue

                video1_name = os.path.basename(video1)
                video2_name = os.path.basename(video2)

                all_video1.add(video1_name)
                all_video2.add(video2_name)

                key = (video1_name, video2_name)
                if key not in pairs_data:
                    pairs_data[key] = []

                pairs_data[key].append({
                    'pipeline': pipeline_name,
                    'score': score,
                    'accepted': accepted,
                    'status': status,
                    'expected': expected,
                    'confirmation': pair_result.get('confirmation')
                })

        # Trier les vidéos par nom
        sorted_video1 = sorted(all_video1)
        sorted_video2 = sorted(all_video2)

        # Setup table
        self.matrix_table.clear()
        self.matrix_table.setRowCount(len(sorted_video1))
        self.matrix_table.setColumnCount(len(sorted_video2))

        # Headers with counts
        self.matrix_table.setHorizontalHeaderLabels(sorted_video2)
        self.matrix_table.setVerticalHeaderLabels(sorted_video1)

        # Fill cells
        match_count = 0
        total_pairs = 0
        fp_count = fn_count = tp_count = tn_count = 0

        for row, video1_name in enumerate(sorted_video1):
            for col, video2_name in enumerate(sorted_video2):
                key = (video1_name, video2_name)

                if key in pairs_data:
                    total_pairs += 1
                    matches = pairs_data[key]

                    # Format: pipeline(s) + statut
                    cell_text_parts = []
                    statuses = set()
                    has_accept = False
                    has_reject = False

                    for match in matches:
                        status = match.get('status', 'UNK')
                        statuses.add(status)
                        if match.get('accepted'):
                            match_count += 1
                            has_accept = True
                        else:
                            has_reject = True
                        if status == "FP":
                            fp_count += 1
                        elif status == "FN":
                            fn_count += 1
                        elif status == "TP":
                            tp_count += 1
                        elif status == "TN":
                            tn_count += 1

                        pipeline = match['pipeline']
                        if len(pipeline) > 20:
                            pipeline = pipeline[:17] + "..."

                        conf = match.get('confirmation') or {}
                        conf_txt = ""
                        if conf:
                            sim = conf.get('phash_similarity_rate')
                            if sim is not None:
                                conf_txt = f" | pHash={sim:.2f}"
                            if conf.get('phash_best_offset') is not None:
                                conf_txt += f" @ {conf.get('phash_best_offset'):.2f}s"
                        if match.get('dct_score') is not None:
                            conf_txt += f" | DCT={float(match.get('dct_score')):.2f}"

                        score_val = match.get('score')
                        if score_val is None:
                            score_str = "N/A"
                        else:
                            try:
                                score_str = f"{float(score_val):.2f}"
                            except Exception:
                                score_str = str(score_val)

                        cell_text_parts.append(f"{status} {pipeline}: {score_str}{conf_txt}")

                        if self.show_details:
                            # Détails par méthode (ticks)
                            method_results = match.get('pipeline_results') or []
                            if method_results:
                                for mr in method_results:
                                    symb = "✓" if mr.get('accepted') else "✗"
                                    mname = mr.get('method_name', mr.get('method', '?'))
                                    # Try to pick a score field
                                    mscore = None
                                    for k, v in mr.items():
                                        if k.endswith('_score') and isinstance(v, (int, float)):
                                            mscore = v
                                            break
                                    if mscore is None and isinstance(mr.get('similarity'), (int, float)):
                                        mscore = mr.get('similarity')
                                    if mscore is None and isinstance(mr.get('match_percentage'), (int, float)):
                                        mscore = mr.get('match_percentage')
                                    mscore_txt = f"{mscore:.2f}" if mscore is not None else ""
                                    reason = mr.get('rejection_reason')
                                    detail_line = f"  {symb} {mname}"
                                    if mscore_txt:
                                        detail_line += f" ({mscore_txt})"
                                    if reason and not mr.get('accepted'):
                                        detail_line += f" → {reason}"
                                    cell_text_parts.append(detail_line)

                            # Rejet global
                            if match.get('rejection_method'):
                                cell_text_parts.append(f"  ✗ arrêté sur {match.get('rejection_method')}")

                    cell_text = "\n".join(cell_text_parts)

                    item = QTableWidgetItem(cell_text)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                    # Color code by status severity (et accepte/rejet pour UNK)
                    color = self._status_to_color(statuses, has_accept, has_reject)
                    item.setBackground(QColor(color))

                    # Tooltip with details
                    tooltip = "\n".join(cell_text_parts)
                    item.setToolTip(tooltip)

                    self.matrix_table.setItem(row, col, item)
                else:
                    # No test for this pair
                    item = QTableWidgetItem("")
                    item.setBackground(QColor("#FAFAFA"))  # Very light gray
                    self.matrix_table.setItem(row, col, item)

        # Auto-resize
        self.matrix_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.matrix_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        # Update stats
        stats_text = (
            f"📊 {len(sorted_video1)} vidéos courtes × {len(sorted_video2)} vidéos longues | "
            f"{total_pairs} paires affichées | {match_count} matches acceptés | "
            f"TP={tp_count} FP={fp_count} TN={tn_count} FN={fn_count}"
        )
        self.stats_label.setText(stats_text)

        logger.info(f"Matrix populated: {len(sorted_video1)} × {len(sorted_video2)} = {len(sorted_video1) * len(sorted_video2)} cells")

    def _compute_status(self, expected: str, accepted: bool) -> str:
        """Détermine TP/FP/TN/FN/UNK selon expected/accepted."""
        expected = (expected or "unknown").lower()
        if expected in ("positive", "duplicate"):
            return "TP" if accepted else "FN"
        if expected in ("negative", "not_duplicate"):
            return "FP" if accepted else "TN"
        return "UNK"

    def _status_to_color(self, statuses: set, has_accept: bool = False, has_reject: bool = False) -> str:
        """Couleur selon la gravité (FP/FN > TP > TN > UNK, avec nuance accept/rejet si UNK)."""
        if "FP" in statuses or "FN" in statuses:
            return "#FFCDD2"  # rouge clair
        if "TP" in statuses:
            return "#C8E6C9"  # vert clair
        if "TN" in statuses:
            return "#E0E0E0"  # gris
        # UNK: distinguer accept/rejet
        if has_accept and not has_reject:
            return "#C8E6C9"  # vert clair (accepté sans label)
        if has_reject and not has_accept:
            return "#ECEFF1"  # gris bleuté
        if has_accept and has_reject:
            return "#FFF9C4"  # jaune pâle (mélange)
        return "#BBDEFB"  # bleu clair

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when widget is closed.

        Ensures proper cleanup of resources and signals.
        """
        # All signals are internal and auto-cleaned by Qt
        # Added for consistency with other widgets
        super().closeEvent(event)
