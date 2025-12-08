"""
Report Dialog for Duplicate Finder plugin.

Provides UI for generating reports in multiple formats.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QRadioButton, QLineEdit, QTextEdit, QFileDialog, QCheckBox,
    QSpinBox, QComboBox, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from ..reports.report_generator import ReportGenerator, ReportData, ReportFormat
from src.core.logger import Logger

logger = Logger.get_logger(__name__)


class ReportGenerationWorker(QThread):
    """Worker thread for generating reports in background."""

    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(str)  # status message

    def __init__(self, generator: ReportGenerator, data: ReportData,
                 output_path: str, report_format: ReportFormat):
        super().__init__()
        self.generator = generator
        self.data = data
        self.output_path = output_path
        self.report_format = report_format

    def run(self):
        """Generate report in background."""
        try:
            self.progress.emit(f"Generating {self.report_format.value.upper()} report...")
            success = self.generator.generate_report(
                self.data,
                self.output_path,
                self.report_format
            )

            if success:
                self.finished.emit(True, f"Report generated successfully: {self.output_path}")
            else:
                self.finished.emit(False, "Report generation failed")

        except Exception as e:
            logger.error(f"Report generation error: {e}")
            self.finished.emit(False, f"Error: {e}")


class ReportDialog(QDialog):
    """
    Dialog for generating duplicate detection reports.

    Features:
    - Choose report format (PDF/HTML/CSV)
    - Configure report options
    - Preview report data
    - Generate reports
    """

    def __init__(self, duplicate_data: Dict[str, Any], parent=None):
        super().__init__(parent)

        self.duplicate_data = duplicate_data
        self.generator = ReportGenerator()
        self.worker: Optional[ReportGenerationWorker] = None

        self.setWindowTitle("Generate Report")
        self.resize(700, 600)

        self._setup_ui()
        self._populate_summary()

        logger.info("ReportDialog initialized")

    def _setup_ui(self):
        """Create the UI layout."""
        layout = QVBoxLayout(self)

        # ===== Header =====
        header_label = QLabel("📄 Generate Duplicate Detection Report")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # ===== Format Selection =====
        format_group = QGroupBox("Report Format")
        format_layout = QVBoxLayout(format_group)

        self.pdf_radio = QRadioButton("PDF - Portable Document Format (requires reportlab)")
        self.html_radio = QRadioButton("HTML - Interactive Web Report (recommended)")
        self.csv_radio = QRadioButton("CSV - Comma-Separated Values (for Excel/analysis)")

        self.html_radio.setChecked(True)  # Default to HTML

        format_layout.addWidget(self.pdf_radio)
        format_layout.addWidget(self.html_radio)
        format_layout.addWidget(self.csv_radio)

        layout.addWidget(format_group)

        # ===== Output Path =====
        output_group = QGroupBox("Output Location")
        output_layout = QHBoxLayout(output_group)

        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Select output file path...")

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_output)

        output_layout.addWidget(QLabel("File:"))
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(self.browse_btn)

        layout.addWidget(output_group)

        # ===== Report Options =====
        options_group = QGroupBox("Report Options")
        options_layout = QVBoxLayout(options_group)

        self.include_metadata = QCheckBox("Include scan metadata")
        self.include_metadata.setChecked(True)

        self.include_filters = QCheckBox("Include applied filters")
        self.include_filters.setChecked(True)

        # Group limit
        limit_layout = QHBoxLayout()
        limit_layout.addWidget(QLabel("Max groups to include:"))
        self.group_limit_spin = QSpinBox()
        self.group_limit_spin.setRange(1, 10000)
        self.group_limit_spin.setValue(1000)
        self.group_limit_spin.setSuffix(" groups")
        limit_layout.addWidget(self.group_limit_spin)
        limit_layout.addStretch()

        options_layout.addWidget(self.include_metadata)
        options_layout.addWidget(self.include_filters)
        options_layout.addLayout(limit_layout)

        layout.addWidget(options_group)

        # ===== Summary Preview =====
        summary_group = QGroupBox("Report Summary Preview")
        summary_layout = QVBoxLayout(summary_group)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(150)

        summary_layout.addWidget(self.summary_text)

        layout.addWidget(summary_group)

        # ===== Actions =====
        actions_layout = QHBoxLayout()

        self.generate_btn = QPushButton("✓ Generate Report")
        self.generate_btn.clicked.connect(self._generate_report)
        self.generate_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        actions_layout.addStretch()
        actions_layout.addWidget(self.generate_btn)
        actions_layout.addWidget(self.cancel_btn)

        layout.addLayout(actions_layout)

    def _populate_summary(self):
        """Populate summary preview with current data."""
        total_files = self.duplicate_data.get('total_files_scanned', 0)
        total_duplicates = self.duplicate_data.get('total_duplicates_found', 0)
        total_groups = len(self.duplicate_data.get('duplicate_groups', []))
        space_wasted = self.duplicate_data.get('total_space_wasted', 0)

        summary = f"""<b>Report will include:</b><br>
        • Files Scanned: {total_files}<br>
        • Duplicates Found: {total_duplicates}<br>
        • Duplicate Groups: {total_groups}<br>
        • Space Wasted: {self._format_size(space_wasted)}<br>
        """

        self.summary_text.setHtml(summary)

    def _browse_output(self):
        """Browse for output file location."""
        # Determine file extension based on selected format
        if self.pdf_radio.isChecked():
            file_filter = "PDF Files (*.pdf)"
            default_ext = ".pdf"
        elif self.html_radio.isChecked():
            file_filter = "HTML Files (*.html)"
            default_ext = ".html"
        else:  # CSV
            file_filter = "CSV Files (*.csv)"
            default_ext = ".csv"

        default_filename = f"duplicate_report_{Path.home().name}"

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Report As",
            str(Path.home() / f"{default_filename}{default_ext}"),
            file_filter
        )

        if filename:
            self.output_path_edit.setText(filename)

    def _generate_report(self):
        """Generate the report."""
        # Validate output path
        output_path = self.output_path_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, "No Output Path", "Please select an output file path.")
            return

        # Determine format
        if self.pdf_radio.isChecked():
            report_format = ReportFormat.PDF
        elif self.html_radio.isChecked():
            report_format = ReportFormat.HTML
        else:
            report_format = ReportFormat.CSV

        # Build report data
        report_data = self._build_report_data()

        # Check for reportlab if PDF selected
        if report_format == ReportFormat.PDF:
            try:
                import reportlab
            except ImportError:
                reply = QMessageBox.question(
                    self, "reportlab Not Installed",
                    "PDF generation requires the 'reportlab' library which is not installed.\n\n"
                    "A text-based report will be generated instead. Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.No:
                    return

        # Generate report in background
        self.worker = ReportGenerationWorker(
            self.generator,
            report_data,
            output_path,
            report_format
        )

        self.worker.finished.connect(self._on_generation_finished)
        self.worker.progress.connect(self._on_generation_progress)

        # Show progress dialog
        self.progress_dialog = QProgressDialog(
            "Generating report...",
            "Cancel",
            0, 0,  # Indeterminate progress
            self
        )
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.canceled.connect(self._on_cancel_generation)
        self.progress_dialog.show()

        # Disable generate button
        self.generate_btn.setEnabled(False)

        # Start generation
        self.worker.start()

        logger.info(f"Started report generation: {report_format.value}")

    def _build_report_data(self) -> ReportData:
        """Build ReportData from duplicate_data."""
        from datetime import datetime

        # Limit groups if needed
        all_groups = self.duplicate_data.get('duplicate_groups', [])
        limit = self.group_limit_spin.value()
        groups_to_include = all_groups[:limit]

        # Build report data
        data = ReportData(
            title="Duplicate Detection Report",
            generated_at=datetime.now(),
            scan_duration=self.duplicate_data.get('scan_duration'),
            total_files_scanned=self.duplicate_data.get('total_files_scanned', 0),
            total_duplicates_found=self.duplicate_data.get('total_duplicates_found', 0),
            total_duplicate_groups=len(all_groups),
            total_space_wasted=self.duplicate_data.get('total_space_wasted', 0),
            potential_space_savings=self.duplicate_data.get('potential_space_savings', 0),
            duplicate_groups=groups_to_include,
            hash_method=self.duplicate_data.get('hash_method', 'Unknown'),
            similarity_threshold=self.duplicate_data.get('similarity_threshold', 85.0),
            filters_applied=self.duplicate_data.get('filters_applied') if self.include_filters.isChecked() else None
        )

        return data

    def _on_generation_progress(self, message: str):
        """Handle progress updates."""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.setLabelText(message)

    def _on_generation_finished(self, success: bool, message: str):
        """Handle generation completion."""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()

        self.generate_btn.setEnabled(True)

        if success:
            QMessageBox.information(self, "Success", message)
            self.accept()  # Close dialog
        else:
            QMessageBox.critical(self, "Error", message)

        logger.info(f"Report generation finished: success={success}")

    def _on_cancel_generation(self):
        """Handle generation cancellation."""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()

        self.generate_btn.setEnabled(True)
        logger.info("Report generation cancelled")

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable form."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
