"""
Batch Queue Widget for Duplicate Finder plugin.

Provides UI for viewing and managing batch analysis jobs.
"""

from typing import Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMenu, QFileDialog, QInputDialog,
    QMessageBox, QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from ..controllers.batch_controller import (
    BatchController, BatchJob, JobStatus, JobType, get_batch_controller
)
from ..managers.unified_config_manager import UnifiedConfigManager
from src.core.logger import Logger

logger = Logger.get_logger(__name__)


class BatchQueueWidget(QWidget):
    """
    Widget for managing batch analysis jobs.

    Features:
    - Job table with status, progress, and actions
    - Queue controls (start, pause, stop, clear)
    - Add jobs from folders or files
    - Auto-refresh on job updates
    - Context menu for job operations
    """

    # Signals
    execute_job_requested = pyqtSignal(str)  # job_id - Request to execute a job

    def __init__(self, batch_controller: Optional[BatchController] = None,
                 config_manager: Optional[UnifiedConfigManager] = None,
                 parent=None):
        super().__init__(parent)

        self.batch_controller = batch_controller or get_batch_controller()
        self.config_manager = config_manager

        self._setup_ui()
        self._connect_signals()
        self._update_table()

        logger.info("BatchQueueWidget initialized")

    def _setup_ui(self):
        """Create the UI layout."""
        layout = QVBoxLayout(self)

        # ===== Header =====
        header_layout = QHBoxLayout()
        header_label = QLabel("📋 Batch Queue")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        # Queue stats
        self.stats_label = QLabel()
        self._update_stats_label()
        header_layout.addWidget(self.stats_label)

        layout.addLayout(header_layout)

        # ===== Controls =====
        controls_layout = QHBoxLayout()

        # Add job buttons
        self.add_folder_btn = QPushButton("➕ Add Folder")
        self.add_folder_btn.clicked.connect(self._add_folder_job)
        controls_layout.addWidget(self.add_folder_btn)

        self.add_files_btn = QPushButton("➕ Add Files")
        self.add_files_btn.clicked.connect(self._add_files_job)
        controls_layout.addWidget(self.add_files_btn)

        controls_layout.addStretch()

        # Queue control buttons
        self.start_btn = QPushButton("▶ Start")
        self.start_btn.clicked.connect(self._start_queue)
        controls_layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.clicked.connect(self._pause_queue)
        self.pause_btn.setEnabled(False)
        controls_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self._stop_queue)
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)

        controls_layout.addStretch()

        # Clear buttons
        self.clear_completed_btn = QPushButton("🗑 Clear Completed")
        self.clear_completed_btn.clicked.connect(self._clear_completed)
        controls_layout.addWidget(self.clear_completed_btn)

        self.clear_all_btn = QPushButton("🗑 Clear All")
        self.clear_all_btn.clicked.connect(self._clear_all)
        controls_layout.addWidget(self.clear_all_btn)

        layout.addLayout(controls_layout)

        # ===== Job Table =====
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Status", "Job Name", "Type", "Target", "Progress", "Duration", "Actions"
        ])

        # Column sizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Job Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Target
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Progress
        header.setMinimumSectionSize(120)
        self.table.setColumnWidth(4, 150)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Duration
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Actions

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.table)

    def _connect_signals(self):
        """Connect batch controller signals."""
        self.batch_controller.job_added.connect(self._on_job_changed)
        self.batch_controller.job_removed.connect(self._on_job_changed)
        self.batch_controller.job_started.connect(self._on_job_changed)
        self.batch_controller.job_progress.connect(self._on_job_progress)
        self.batch_controller.job_completed.connect(self._on_job_changed)
        self.batch_controller.job_failed.connect(self._on_job_changed)
        self.batch_controller.job_cancelled.connect(self._on_job_changed)
        self.batch_controller.queue_started.connect(self._on_queue_state_changed)
        self.batch_controller.queue_paused.connect(self._on_queue_state_changed)
        self.batch_controller.queue_completed.connect(self._on_queue_state_changed)
        self.batch_controller.queue_cleared.connect(self._on_job_changed)

    # ==================== UI Updates ====================

    def _update_table(self):
        """Update the job table."""
        jobs = self.batch_controller.get_all_jobs()

        self.table.setRowCount(len(jobs))

        for row, job in enumerate(jobs):
            # Status icon
            status_item = QTableWidgetItem(self._get_status_icon(job.status))
            status_item.setData(Qt.ItemDataRole.UserRole, job.job_id)
            status_item.setBackground(QColor(self._get_status_color(job.status)))
            self.table.setItem(row, 0, status_item)

            # Job name
            name_item = QTableWidgetItem(job.name)
            self.table.setItem(row, 1, name_item)

            # Type
            type_item = QTableWidgetItem(job.job_type.value.replace('_', ' ').title())
            self.table.setItem(row, 2, type_item)

            # Target
            target_item = QTableWidgetItem(job.target_display)
            self.table.setItem(row, 3, target_item)

            # Progress
            if job.status == JobStatus.RUNNING or job.progress > 0:
                progress_bar = QProgressBar()
                progress_bar.setMinimum(0)
                progress_bar.setMaximum(100)
                progress_bar.setValue(int(job.progress))
                progress_bar.setFormat(f"{int(job.progress)}% - {job.progress_message}")
                self.table.setCellWidget(row, 4, progress_bar)
            else:
                progress_item = QTableWidgetItem("-")
                self.table.setItem(row, 4, progress_item)

            # Duration
            duration_text = self._format_duration(job.duration_seconds)
            duration_item = QTableWidgetItem(duration_text)
            self.table.setItem(row, 5, duration_item)

            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)

            if job.status == JobStatus.RUNNING:
                cancel_btn = QPushButton("✖ Cancel")
                cancel_btn.clicked.connect(lambda checked, jid=job.job_id: self._cancel_job(jid))
                actions_layout.addWidget(cancel_btn)
            elif job.status == JobStatus.PENDING:
                cancel_btn = QPushButton("✖ Cancel")
                cancel_btn.clicked.connect(lambda checked, jid=job.job_id: self._cancel_job(jid))
                actions_layout.addWidget(cancel_btn)
            elif job.is_terminal:
                remove_btn = QPushButton("🗑 Remove")
                remove_btn.clicked.connect(lambda checked, jid=job.job_id: self._remove_job(jid))
                actions_layout.addWidget(remove_btn)

            self.table.setCellWidget(row, 6, actions_widget)

        self._update_stats_label()

    def _update_stats_label(self):
        """Update queue statistics label."""
        stats = self.batch_controller.get_stats()
        text = (f"Total: {stats['total']} | "
                f"Pending: {stats['pending']} | "
                f"Running: {stats['running']} | "
                f"Completed: {stats['completed']} | "
                f"Failed: {stats['failed']}")
        self.stats_label.setText(text)

    # ==================== Job Management ====================

    def _add_folder_job(self):
        """Add a folder analysis job."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder for Batch Analysis"
        )

        if not folder:
            return

        # Ask for job name
        name, ok = QInputDialog.getText(
            self, "Job Name",
            "Enter a name for this job:",
            text=f"Analysis: {Path(folder).name}"
        )

        if not ok or not name:
            return

        # Ask for job type
        job_types = [
            ("Standard Analysis", JobType.STANDARD_ANALYSIS),
            ("Audio-First Analysis", JobType.AUDIO_FIRST_ANALYSIS),
            ("Subsequence Detection", JobType.SUBSEQUENCE_DETECTION),
        ]

        type_names = [t[0] for t in job_types]
        type_name, ok = QInputDialog.getItem(
            self, "Job Type",
            "Select analysis type:",
            type_names,
            0,
            False
        )

        if not ok:
            return

        # Get corresponding JobType
        job_type = next(t[1] for t in job_types if t[0] == type_name)

        # Get current config
        config = None
        if self.config_manager:
            config = self.config_manager.get_current_config()

        # Add job
        from pathlib import Path
        job_id = self.batch_controller.add_job(
            job_type=job_type,
            name=name,
            target_type='folder',
            target=Path(folder),
            config=config
        )

        logger.info(f"Added folder job: {name} ({folder})")

    def _add_files_job(self):
        """Add a files analysis job."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files for Batch Analysis",
            "", "Video Files (*.mp4 *.avi *.mkv *.mov *.flv *.wmv);;All Files (*)"
        )

        if not files:
            return

        # Ask for job name
        name, ok = QInputDialog.getText(
            self, "Job Name",
            "Enter a name for this job:",
            text=f"Analysis: {len(files)} files"
        )

        if not ok or not name:
            return

        # Ask for job type
        job_types = [
            ("Standard Analysis", JobType.STANDARD_ANALYSIS),
            ("Audio-First Analysis", JobType.AUDIO_FIRST_ANALYSIS),
            ("Subsequence Detection", JobType.SUBSEQUENCE_DETECTION),
        ]

        type_names = [t[0] for t in job_types]
        type_name, ok = QInputDialog.getItem(
            self, "Job Type",
            "Select analysis type:",
            type_names,
            0,
            False
        )

        if not ok:
            return

        # Get corresponding JobType
        job_type = next(t[1] for t in job_types if t[0] == type_name)

        # Get current config
        config = None
        if self.config_manager:
            config = self.config_manager.get_current_config()

        # Add job
        from pathlib import Path
        file_paths = [Path(f) for f in files]
        job_id = self.batch_controller.add_job(
            job_type=job_type,
            name=name,
            target_type='files',
            target=file_paths,
            config=config
        )

        logger.info(f"Added files job: {name} ({len(files)} files)")

    def _cancel_job(self, job_id: str):
        """Cancel a job."""
        success = self.batch_controller.cancel_job(job_id)
        if success:
            logger.info(f"Cancelled job: {job_id}")

    def _remove_job(self, job_id: str):
        """Remove a job."""
        success = self.batch_controller.remove_job(job_id)
        if success:
            logger.info(f"Removed job: {job_id}")

    # ==================== Queue Control ====================

    def _start_queue(self):
        """Start queue processing."""
        self.batch_controller.start_queue()

    def _pause_queue(self):
        """Pause queue processing."""
        self.batch_controller.pause_queue()

    def _stop_queue(self):
        """Stop queue processing."""
        reply = QMessageBox.question(
            self, "Stop Queue",
            "Are you sure you want to stop the queue? The current job will be cancelled.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.batch_controller.stop_queue()

    def _clear_completed(self):
        """Clear completed jobs."""
        # Only clear completed (not failed or cancelled)
        jobs_to_remove = [
            job.job_id for job in self.batch_controller.get_all_jobs()
            if job.status == JobStatus.COMPLETED
        ]

        for job_id in jobs_to_remove:
            self.batch_controller.remove_job(job_id)

        logger.info(f"Cleared {len(jobs_to_remove)} completed jobs")

    def _clear_all(self):
        """Clear all jobs."""
        reply = QMessageBox.question(
            self, "Clear All Jobs",
            "Are you sure you want to clear all jobs? This will remove all pending, completed, failed, and cancelled jobs. Running jobs cannot be cleared.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            count = self.batch_controller.clear_queue(clear_terminal=True)
            logger.info(f"Cleared {count} jobs")

    # ==================== Context Menu ====================

    def _show_context_menu(self, position):
        """Show context menu for job."""
        row = self.table.rowAt(position.y())
        if row < 0:
            return

        # Get job_id from status item
        status_item = self.table.item(row, 0)
        if not status_item:
            return

        job_id = status_item.data(Qt.ItemDataRole.UserRole)
        job = self.batch_controller.get_job(job_id)
        if not job:
            return

        # Create context menu
        menu = QMenu(self)

        if job.status == JobStatus.PENDING:
            cancel_action = menu.addAction("✖ Cancel Job")
            cancel_action.triggered.connect(lambda: self._cancel_job(job_id))

            move_up_action = menu.addAction("⬆ Move Up")
            move_up_action.triggered.connect(lambda: self._move_job_up(job_id))

            move_down_action = menu.addAction("⬇ Move Down")
            move_down_action.triggered.connect(lambda: self._move_job_down(job_id))

        elif job.status == JobStatus.RUNNING:
            cancel_action = menu.addAction("✖ Cancel Job")
            cancel_action.triggered.connect(lambda: self._cancel_job(job_id))

        elif job.is_terminal:
            remove_action = menu.addAction("🗑 Remove Job")
            remove_action.triggered.connect(lambda: self._remove_job(job_id))

            if job.status == JobStatus.FAILED:
                retry_action = menu.addAction("🔄 Retry Job")
                retry_action.triggered.connect(lambda: self._retry_job(job_id))

        menu.addSeparator()

        details_action = menu.addAction("ℹ View Details")
        details_action.triggered.connect(lambda: self._show_job_details(job_id))

        menu.exec(self.table.viewport().mapToGlobal(position))

    def _move_job_up(self, job_id: str):
        """Move job up in queue."""
        jobs = self.batch_controller.get_all_jobs()
        current_index = next((i for i, j in enumerate(jobs) if j.job_id == job_id), None)

        if current_index is not None and current_index > 0:
            self.batch_controller.reorder_job(job_id, current_index - 1)
            self._update_table()

    def _move_job_down(self, job_id: str):
        """Move job down in queue."""
        jobs = self.batch_controller.get_all_jobs()
        current_index = next((i for i, j in enumerate(jobs) if j.job_id == job_id), None)

        if current_index is not None and current_index < len(jobs) - 1:
            self.batch_controller.reorder_job(job_id, current_index + 1)
            self._update_table()

    def _retry_job(self, job_id: str):
        """Retry a failed job."""
        job = self.batch_controller.get_job(job_id)
        if not job:
            return

        # Create new job with same parameters
        new_job_id = self.batch_controller.add_job(
            job_type=job.job_type,
            name=f"{job.name} (Retry)",
            target_type=job.target_type,
            target=job.target,
            config=job.config
        )

        logger.info(f"Retrying failed job {job_id} as {new_job_id}")

    def _show_job_details(self, job_id: str):
        """Show detailed job information."""
        job = self.batch_controller.get_job(job_id)
        if not job:
            return

        details = f"""
Job Details
===========

ID: {job.job_id}
Name: {job.name}
Type: {job.job_type.value.replace('_', ' ').title()}
Status: {job.status.value.upper()}

Target Type: {job.target_type}
Target: {job.target_display}

Created: {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}
Started: {job.started_at.strftime('%Y-%m-%d %H:%M:%S') if job.started_at else 'N/A'}
Completed: {job.completed_at.strftime('%Y-%m-%d %H:%M:%S') if job.completed_at else 'N/A'}
Duration: {self._format_duration(job.duration_seconds)}

Progress: {job.progress:.1f}%
Progress Message: {job.progress_message or 'N/A'}

Error: {job.error_message or 'N/A'}

Result: {job.result if job.result else 'N/A'}
        """

        QMessageBox.information(self, "Job Details", details)

    # ==================== Signal Handlers ====================

    def _on_job_changed(self, *args):
        """Handle job changes."""
        self._update_table()

    def _on_job_progress(self, job_id: str, progress: float, message: str):
        """Handle job progress updates."""
        # Find row with this job_id
        for row in range(self.table.rowCount()):
            status_item = self.table.item(row, 0)
            if status_item and status_item.data(Qt.ItemDataRole.UserRole) == job_id:
                # Update progress bar
                progress_bar = self.table.cellWidget(row, 4)
                if isinstance(progress_bar, QProgressBar):
                    progress_bar.setValue(int(progress))
                    progress_bar.setFormat(f"{int(progress)}% - {message}")
                break

    def _on_queue_state_changed(self):
        """Handle queue state changes."""
        is_running = self.batch_controller.is_running
        is_paused = self.batch_controller.is_paused

        self.start_btn.setEnabled(not is_running or is_paused)
        self.pause_btn.setEnabled(is_running and not is_paused)
        self.stop_btn.setEnabled(is_running)

        self._update_table()

    # ==================== Helpers ====================

    def _get_status_icon(self, status: JobStatus) -> str:
        """Get icon for job status."""
        icons = {
            JobStatus.PENDING: "⏳",
            JobStatus.RUNNING: "▶",
            JobStatus.COMPLETED: "✅",
            JobStatus.FAILED: "❌",
            JobStatus.CANCELLED: "🚫",
            JobStatus.PAUSED: "⏸",
        }
        return icons.get(status, "❓")

    def _get_status_color(self, status: JobStatus) -> str:
        """Get background color for job status."""
        colors = {
            JobStatus.PENDING: "#E8E8E8",
            JobStatus.RUNNING: "#CCE5FF",
            JobStatus.COMPLETED: "#D4EDDA",
            JobStatus.FAILED: "#F8D7DA",
            JobStatus.CANCELLED: "#FFF3CD",
            JobStatus.PAUSED: "#E8E8E8",
        }
        return colors.get(status, "#FFFFFF")

    def _format_duration(self, seconds: Optional[float]) -> str:
        """Format duration in human-readable form."""
        if seconds is None:
            return "-"

        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
