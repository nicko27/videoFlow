"""
Advanced 3-level analysis progress dialog.

This module provides a comprehensive progress dialog for the advanced duplicate
detection pipeline, showing real-time progress for each of the 3 levels.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QGroupBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont
from src.core.logger import Logger
from src.core.i18n import t

logger = Logger.get_logger('DuplicateFinder.AdvancedProgressDialog')


class AdvancedAnalysisThread(QThread):
    """
    Background thread for running advanced 3-level analysis.

    Signals:
        progress_update: Emitted on progress (phase, current, total, message)
        analysis_complete: Emitted when analysis finishes (report dict)
        analysis_error: Emitted on error (error message)
    """

    progress_update = pyqtSignal(str, int, int, str)
    analysis_complete = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)

    def __init__(self, pipeline, video_paths, parent=None):
        """
        Initialize analysis thread.

        Args:
            pipeline: AdvancedDuplicatePipeline instance
            video_paths: List of video paths to analyze
            parent: Parent QObject
        """
        super().__init__(parent)
        self.pipeline = pipeline
        self.video_paths = video_paths

    def run(self):
        """Run the analysis pipeline in background thread."""
        try:
            logger.info(f"Analysis thread starting with {len(self.video_paths)} videos")

            # Run pipeline with progress callback
            report = self.pipeline.run_complete_analysis(self.video_paths)

            if report is None:
                # Analysis was stopped
                logger.info("Analysis was stopped by user")
                return

            # Emit completion signal
            self.analysis_complete.emit(report)
            logger.info("Analysis thread completed successfully")

        except Exception as e:
            logger.error(f"Analysis thread error: {e}", exc_info=True)
            self.analysis_error.emit(str(e))

    def stop(self):
        """Request pipeline to stop."""
        logger.info("Stopping analysis thread...")
        self.pipeline.stop()


class AdvancedProgressDialog(QDialog):
    """
    Progress dialog for advanced 3-level duplicate detection.

    Shows real-time progress for each level with separate progress bars,
    status messages, and statistics.
    """

    def __init__(self, parent=None):
        """
        Initialize progress dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle(
            t("duplicate_finder.progress.title", "🎬 Détection de Scènes - Analyse en cours")
        )
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.setModal(True)

        # State
        self.analysis_thread = None
        self.start_time = None

        # Setup UI
        self.setup_ui()

        logger.debug("AdvancedProgressDialog initialized")

    def setup_ui(self):
        """Configure the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel(t("duplicate_finder.progress.header", "🎬 Détection de Scènes"))
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Description
        desc = QLabel(t(
            "duplicate_finder.progress.desc",
            "Analyse en 3 niveaux : Audio + Visual + Confirmation"
        ))
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #6C757D; font-size: 11px;")
        layout.addWidget(desc)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Level 1 Group
        self.level1_group = self.create_level_group(
            t("duplicate_finder.progress.level1", "🔍 Niveau 1 - Audio Court"),
            t("duplicate_finder.progress.level1_desc", "Filtrage rapide (30s)")
        )
        layout.addWidget(self.level1_group)

        # Level 2 Group
        self.level2_group = self.create_level_group(
            t("duplicate_finder.progress.level2", "🎵 Niveau 2 - Audio Long"),
            t("duplicate_finder.progress.level2_desc", "Analyse approfondie (120s)")
        )
        layout.addWidget(self.level2_group)

        # Level 3 Group
        self.level3_group = self.create_level_group(
            t("duplicate_finder.progress.level3", "👁️ Niveau 3 - Visuel"),
            t("duplicate_finder.progress.level3_desc", "Confirmation par images")
        )
        layout.addWidget(self.level3_group)

        # Overall stats
        stats_group = QGroupBox(t("duplicate_finder.progress.stats", "📊 Statistiques"))
        stats_layout = QVBoxLayout(stats_group)

        self.stats_label = QLabel(t("duplicate_finder.progress.waiting", "En attente..."))
        self.stats_label.setStyleSheet("font-family: 'Courier New'; font-size: 10px;")
        stats_layout.addWidget(self.stats_label)

        layout.addWidget(stats_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton(t("duplicate_finder.progress.stop", "⏹️ Stop"))
        self.cancel_button.setMinimumWidth(120)
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C82333;
            }
        """)
        self.cancel_button.clicked.connect(self.on_cancel)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def create_level_group(self, title: str, description: str) -> QGroupBox:
        """
        Create a progress group for one level.

        Args:
            title: Group title (e.g., "Niveau 1 - LSH Audio")
            description: Short description

        Returns:
            QGroupBox configured for the level
        """
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #6C757D; font-size: 10px;")
        layout.addWidget(desc_label)

        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("%v / %m")
        layout.addWidget(progress_bar)

        # Status label
        status_label = QLabel(t("duplicate_finder.progress.waiting", "En attente..."))
        status_label.setStyleSheet("color: #495057; font-size: 10px; font-style: italic;")
        layout.addWidget(status_label)

        # Store references
        group.progress_bar = progress_bar
        group.status_label = status_label

        return group

    def update_progress(self, phase: str, current: int, total: int, message: str):
        """
        Update progress for a specific phase.

        Args:
            phase: Phase name ("Level 1", "Level 2", "Level 3")
            current: Current item number
            total: Total items
            message: Status message
        """
        # Determine which level
        if "Level 1" in phase or "Niveau 1" in phase:
            group = self.level1_group
        elif "Level 2" in phase or "Niveau 2" in phase:
            group = self.level2_group
        elif "Level 3" in phase or "Niveau 3" in phase:
            group = self.level3_group
        else:
            return

        # Update progress bar
        group.progress_bar.setMaximum(total)
        group.progress_bar.setValue(current)

        # Update status
        group.status_label.setText(message)

        # Update overall stats
        self.update_stats()

    def update_stats(self):
        """Update overall statistics display."""
        import time

        if self.start_time is None:
            self.start_time = time.time()

        elapsed = time.time() - self.start_time

        # Get current values
        l1_current = self.level1_group.progress_bar.value()
        l1_total = self.level1_group.progress_bar.maximum()
        l2_current = self.level2_group.progress_bar.value()
        l2_total = self.level2_group.progress_bar.maximum()
        l3_current = self.level3_group.progress_bar.value()
        l3_total = self.level3_group.progress_bar.maximum()

        # Calculate overall progress
        total_items = l1_total + l2_total + l3_total
        completed_items = l1_current + l2_current + l3_current
        overall_pct = (completed_items / total_items * 100) if total_items > 0 else 0

        # Format stats
        stats_text = t(
            "duplicate_finder.progress.stats_summary",
            f"Progression globale: {overall_pct:.1f}%\n"
            f"Temps écoulé: {elapsed:.1f}s\n"
            f"Niveau 1: {l1_current}/{l1_total}\n"
            f"Niveau 2: {l2_current}/{l2_total}\n"
            f"Niveau 3: {l3_current}/{l3_total}",
            overall=f"{overall_pct:.1f}%",
            elapsed=f"{elapsed:.1f}s",
            l1=f"{l1_current}/{l1_total}",
            l2=f"{l2_current}/{l2_total}",
            l3=f"{l3_current}/{l3_total}"
        )

        self.stats_label.setText(stats_text)

    def start_analysis(self, pipeline, video_paths):
        """
        Start the analysis in background thread.

        Args:
            pipeline: AdvancedDuplicatePipeline instance
            video_paths: List of video paths to analyze
        """
        import time
        self.start_time = time.time()

        # Create and configure thread
        self.analysis_thread = AdvancedAnalysisThread(pipeline, video_paths, self)

        # Connect signals
        self.analysis_thread.progress_update.connect(self.update_progress)
        self.analysis_thread.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_thread.analysis_error.connect(self.on_analysis_error)
        self.analysis_thread.finished.connect(self.on_thread_finished)

        # Connect progress callback in pipeline
        pipeline.progress_callback = self.analysis_thread.progress_update.emit

        # Start thread
        logger.info("Starting analysis thread...")
        self.analysis_thread.start()

    def on_cancel(self):
        """Handle cancel button click."""
        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            t("duplicate_finder.progress.cancel_title", "Confirmation"),
            t(
                "duplicate_finder.progress.cancel_body",
                "Voulez-vous vraiment annuler l'analyse en cours ?\n\nLes résultats partiels seront perdus."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            logger.info("User requested cancellation")

            if self.analysis_thread and self.analysis_thread.isRunning():
                self.analysis_thread.stop()
                self.cancel_button.setEnabled(False)
                self.cancel_button.setText(
                    t("duplicate_finder.progress.cancelling", "⏳ Annulation...")
                )
                self.stats_label.setText(
                    t("duplicate_finder.progress.stopping", "Arrêt en cours...")
                )

    def on_analysis_complete(self, report: dict):
        """
        Handle analysis completion.

        Args:
            report: Analysis report dictionary
        """
        logger.info("Analysis completed successfully")

        # Show completion
        self.stats_label.setText(
            t(
                "duplicate_finder.progress.complete_summary",
                f"✅ ANALYSE TERMINÉE\n\n"
                f"Duplicates confirmés: {report['confirmed_duplicates']}\n"
                f"Temps total: {report['total_time']:.1f}s\n"
                f"Confiance haute: {report['confidence_high']}\n"
                f"Confiance moyenne: {report['confidence_medium']}\n"
                f"Confiance basse: {report['confidence_low']}",
                confirmed=report.get('confirmed_duplicates', 0),
                total_time=f"{report.get('total_time', 0):.1f}s",
                high=report.get('confidence_high', 0),
                medium=report.get('confidence_medium', 0),
                low=report.get('confidence_low', 0)
            )
        )

        # Update button
        self.cancel_button.setText(t("duplicate_finder.progress.close", "Close"))
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.accept)

    def on_analysis_error(self, error_message: str):
        """
        Handle analysis error.

        Args:
            error_message: Error message
        """
        from PyQt6.QtWidgets import QMessageBox

        logger.error(f"Analysis error: {error_message}")

        QMessageBox.critical(
            self,
            t("duplicate_finder.progress.error_title", "Erreur d'Analyse"),
            t(
                "duplicate_finder.progress.error_body",
                f"Une erreur s'est produite pendant l'analyse :\n\n{error_message}",
                error=error_message
            )
        )

        self.reject()

    def on_thread_finished(self):
        """Handle thread finishing."""
        logger.info("Analysis thread finished")

    def closeEvent(self, event):
        """Handle dialog close event."""
        if self.analysis_thread and self.analysis_thread.isRunning():
            event.ignore()
            self.on_cancel()
        else:
            event.accept()
