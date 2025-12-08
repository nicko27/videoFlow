"""
Batch Controller for Duplicate Finder plugin.

Manages batch analysis jobs, allowing multiple folders/files to be analyzed
sequentially in a queue. Provides pause/resume functionality and progress tracking.
"""

import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from ..managers.unified_config_manager import UnifiedConfig
from src.core.logger import Logger

logger = Logger.get_logger(__name__)


class JobStatus(Enum):
    """Status of a batch job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class JobType(Enum):
    """Type of batch job."""
    STANDARD_ANALYSIS = "standard_analysis"
    AUDIO_FIRST_ANALYSIS = "audio_first_analysis"
    SUBSEQUENCE_DETECTION = "subsequence_detection"
    CUSTOM = "custom"


@dataclass
class BatchJob:
    """
    Represents a single batch analysis job.

    Attributes:
        job_id: Unique identifier for the job
        job_type: Type of analysis to perform
        name: Human-readable job name
        target_type: 'folder' or 'files'
        target: Path to folder or list of file paths
        config: Configuration to use for this job
        status: Current job status
        created_at: When the job was created
        started_at: When the job started executing
        completed_at: When the job finished
        progress: Progress percentage (0-100)
        progress_message: Current progress message
        result: Job results (duplicates found, errors, etc.)
        error_message: Error message if failed
    """
    job_id: str
    job_type: JobType
    name: str
    target_type: str  # 'folder' or 'files'
    target: Any  # Path or List[Path]
    config: Optional[UnifiedConfig] = None
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    progress_message: str = ""
    result: Optional[Dict[str, Any]] = None
    error_message: str = ""

    def to_dict(self) -> Dict:
        """Convert job to dictionary for serialization."""
        data = asdict(self)
        # Convert enums to strings
        data['job_type'] = self.job_type.value
        data['status'] = self.status.value
        # Convert datetimes to ISO format
        data['created_at'] = self.created_at.isoformat()
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        # Convert Path objects
        if isinstance(self.target, Path):
            data['target'] = str(self.target)
        elif isinstance(self.target, list):
            data['target'] = [str(p) for p in self.target]
        return data

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return None

    @property
    def is_terminal(self) -> bool:
        """Check if job is in a terminal state (completed, failed, or cancelled)."""
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]

    @property
    def target_display(self) -> str:
        """Get display string for target."""
        if self.target_type == 'folder':
            return str(self.target)
        else:
            count = len(self.target) if isinstance(self.target, list) else 1
            return f"{count} file(s)"


class BatchController(QObject):
    """
    Manages batch analysis jobs.

    Provides:
    - Job queue management (add, remove, clear)
    - Sequential job execution
    - Pause/resume functionality
    - Job status tracking and updates
    - Integration with analysis workflows

    Signals:
    - job_added(job_id): Job added to queue
    - job_removed(job_id): Job removed from queue
    - job_started(job_id): Job started executing
    - job_progress(job_id, progress, message): Job progress updated
    - job_completed(job_id, result): Job completed successfully
    - job_failed(job_id, error): Job failed with error
    - job_cancelled(job_id): Job was cancelled
    - queue_started(): Queue processing started
    - queue_paused(): Queue processing paused
    - queue_completed(): All jobs completed
    - queue_cleared(): Queue was cleared
    """

    # Signals
    job_added = pyqtSignal(str)  # job_id
    job_removed = pyqtSignal(str)  # job_id
    job_started = pyqtSignal(str)  # job_id
    job_progress = pyqtSignal(str, float, str)  # job_id, progress, message
    job_completed = pyqtSignal(str, dict)  # job_id, result
    job_failed = pyqtSignal(str, str)  # job_id, error
    job_cancelled = pyqtSignal(str)  # job_id
    queue_started = pyqtSignal()
    queue_paused = pyqtSignal()
    queue_completed = pyqtSignal()
    queue_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Job storage
        self.jobs: Dict[str, BatchJob] = {}  # job_id -> BatchJob
        self.job_order: List[str] = []  # Ordered list of job IDs

        # Queue state
        self.is_running = False
        self.is_paused = False
        self.current_job_id: Optional[str] = None

        # Processing timer (for checking job completion)
        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self._process_next_job)
        self.process_timer.setInterval(500)  # Check every 500ms

        logger.info("BatchController initialized")

    # ==================== Queue Management ====================

    def add_job(self, job_type: JobType, name: str, target_type: str,
                target: Any, config: Optional[UnifiedConfig] = None) -> str:
        """
        Add a new job to the queue.

        Args:
            job_type: Type of analysis job
            name: Human-readable job name
            target_type: 'folder' or 'files'
            target: Path to folder or list of file paths
            config: Optional configuration (uses current if None)

        Returns:
            job_id: Unique identifier for the job
        """
        job_id = str(uuid.uuid4())

        job = BatchJob(
            job_id=job_id,
            job_type=job_type,
            name=name,
            target_type=target_type,
            target=target,
            config=config
        )

        self.jobs[job_id] = job
        self.job_order.append(job_id)

        logger.info(f"Added job {job_id}: {name} ({job_type.value})")
        self.job_added.emit(job_id)

        # Auto-start queue if not running
        if not self.is_running and not self.is_paused:
            self.start_queue()

        return job_id

    def remove_job(self, job_id: str) -> bool:
        """
        Remove a job from the queue.

        Args:
            job_id: Job identifier

        Returns:
            True if removed successfully
        """
        if job_id not in self.jobs:
            logger.warning(f"Job not found: {job_id}")
            return False

        job = self.jobs[job_id]

        # Can only remove pending or terminal jobs
        if job.status == JobStatus.RUNNING:
            logger.warning(f"Cannot remove running job: {job_id}")
            return False

        # Remove from storage
        del self.jobs[job_id]
        self.job_order.remove(job_id)

        logger.info(f"Removed job {job_id}: {job.name}")
        self.job_removed.emit(job_id)
        return True

    def clear_queue(self, clear_terminal: bool = True) -> int:
        """
        Clear all jobs from the queue.

        Args:
            clear_terminal: If True, also clear completed/failed/cancelled jobs

        Returns:
            Number of jobs cleared
        """
        jobs_to_remove = []

        for job_id, job in self.jobs.items():
            # Skip running job
            if job.status == JobStatus.RUNNING:
                continue

            # Skip terminal jobs if requested
            if not clear_terminal and job.is_terminal:
                continue

            jobs_to_remove.append(job_id)

        # Remove jobs
        for job_id in jobs_to_remove:
            del self.jobs[job_id]
            self.job_order.remove(job_id)

        logger.info(f"Cleared {len(jobs_to_remove)} jobs from queue")
        self.queue_cleared.emit()
        return len(jobs_to_remove)

    def reorder_job(self, job_id: str, new_position: int) -> bool:
        """
        Reorder a job in the queue.

        Args:
            job_id: Job identifier
            new_position: New position in queue (0-based)

        Returns:
            True if reordered successfully
        """
        if job_id not in self.jobs:
            return False

        job = self.jobs[job_id]

        # Can only reorder pending jobs
        if job.status != JobStatus.PENDING:
            logger.warning(f"Cannot reorder non-pending job: {job_id}")
            return False

        # Remove and reinsert
        self.job_order.remove(job_id)
        new_position = max(0, min(new_position, len(self.job_order)))
        self.job_order.insert(new_position, job_id)

        logger.info(f"Reordered job {job_id} to position {new_position}")
        return True

    # ==================== Queue Control ====================

    def start_queue(self):
        """Start processing the queue."""
        if self.is_running:
            logger.warning("Queue already running")
            return

        self.is_running = True
        self.is_paused = False

        logger.info("Queue started")
        self.queue_started.emit()

        # Start processing
        self._process_next_job()

    def pause_queue(self):
        """Pause queue processing (current job continues)."""
        if not self.is_running:
            logger.warning("Queue not running")
            return

        self.is_paused = True
        self.process_timer.stop()

        logger.info("Queue paused")
        self.queue_paused.emit()

    def resume_queue(self):
        """Resume queue processing."""
        if not self.is_running or not self.is_paused:
            logger.warning("Queue not paused")
            return

        self.is_paused = False

        logger.info("Queue resumed")
        self.queue_started.emit()

        # Resume processing
        self._process_next_job()

    def stop_queue(self):
        """Stop queue processing and cancel current job."""
        if not self.is_running:
            return

        # Cancel current job if any
        if self.current_job_id:
            self.cancel_job(self.current_job_id)

        self.is_running = False
        self.is_paused = False
        self.process_timer.stop()

        logger.info("Queue stopped")

    # ==================== Job Control ====================

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancelled successfully
        """
        if job_id not in self.jobs:
            return False

        job = self.jobs[job_id]

        # Can only cancel pending or running jobs
        if job.is_terminal:
            logger.warning(f"Cannot cancel terminal job: {job_id}")
            return False

        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now()

        logger.info(f"Cancelled job {job_id}: {job.name}")
        self.job_cancelled.emit(job_id)

        # If this was the current job, move to next
        if self.current_job_id == job_id:
            self.current_job_id = None
            if self.is_running and not self.is_paused:
                self._process_next_job()

        return True

    def update_job_progress(self, job_id: str, progress: float, message: str = ""):
        """
        Update job progress.

        Args:
            job_id: Job identifier
            progress: Progress percentage (0-100)
            message: Progress message
        """
        if job_id not in self.jobs:
            return

        job = self.jobs[job_id]
        job.progress = progress
        job.progress_message = message

        self.job_progress.emit(job_id, progress, message)

    def complete_job(self, job_id: str, result: Dict[str, Any]):
        """
        Mark job as completed.

        Args:
            job_id: Job identifier
            result: Job results
        """
        if job_id not in self.jobs:
            return

        job = self.jobs[job_id]
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now()
        job.progress = 100.0
        job.result = result

        logger.info(f"Job completed {job_id}: {job.name} (duration: {job.duration_seconds:.1f}s)")
        self.job_completed.emit(job_id, result)

        # Move to next job
        self.current_job_id = None
        if self.is_running and not self.is_paused:
            self._process_next_job()

    def fail_job(self, job_id: str, error: str):
        """
        Mark job as failed.

        Args:
            job_id: Job identifier
            error: Error message
        """
        if job_id not in self.jobs:
            return

        job = self.jobs[job_id]
        job.status = JobStatus.FAILED
        job.completed_at = datetime.now()
        job.error_message = error

        logger.error(f"Job failed {job_id}: {job.name} - {error}")
        self.job_failed.emit(job_id, error)

        # Move to next job
        self.current_job_id = None
        if self.is_running and not self.is_paused:
            self._process_next_job()

    # ==================== Internal Processing ====================

    def _process_next_job(self):
        """Process the next pending job in the queue."""
        # Don't process if paused or already processing
        if self.is_paused or self.current_job_id is not None:
            return

        # Find next pending job
        next_job_id = None
        for job_id in self.job_order:
            job = self.jobs[job_id]
            if job.status == JobStatus.PENDING:
                next_job_id = job_id
                break

        # No more pending jobs
        if next_job_id is None:
            self.is_running = False
            self.process_timer.stop()
            logger.info("Queue completed - no more pending jobs")
            self.queue_completed.emit()
            return

        # Start job
        self._start_job(next_job_id)

    def _start_job(self, job_id: str):
        """
        Start executing a job.

        Args:
            job_id: Job identifier
        """
        job = self.jobs[job_id]
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now()
        job.progress = 0.0

        self.current_job_id = job_id

        logger.info(f"Starting job {job_id}: {job.name}")
        self.job_started.emit(job_id)

        # NOTE: Actual job execution is handled by the caller
        # They should connect to job_started signal and execute the job
        # Then call complete_job() or fail_job() when done

    # ==================== Queries ====================

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get job by ID."""
        return self.jobs.get(job_id)

    def get_all_jobs(self) -> List[BatchJob]:
        """Get all jobs in order."""
        return [self.jobs[job_id] for job_id in self.job_order if job_id in self.jobs]

    def get_pending_jobs(self) -> List[BatchJob]:
        """Get all pending jobs."""
        return [job for job in self.get_all_jobs() if job.status == JobStatus.PENDING]

    def get_running_job(self) -> Optional[BatchJob]:
        """Get currently running job."""
        if self.current_job_id:
            return self.jobs.get(self.current_job_id)
        return None

    def get_completed_jobs(self) -> List[BatchJob]:
        """Get all completed jobs."""
        return [job for job in self.get_all_jobs() if job.status == JobStatus.COMPLETED]

    def get_failed_jobs(self) -> List[BatchJob]:
        """Get all failed jobs."""
        return [job for job in self.get_all_jobs() if job.status == JobStatus.FAILED]

    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        jobs = self.get_all_jobs()
        return {
            'total': len(jobs),
            'pending': len([j for j in jobs if j.status == JobStatus.PENDING]),
            'running': len([j for j in jobs if j.status == JobStatus.RUNNING]),
            'completed': len([j for j in jobs if j.status == JobStatus.COMPLETED]),
            'failed': len([j for j in jobs if j.status == JobStatus.FAILED]),
            'cancelled': len([j for j in jobs if j.status == JobStatus.CANCELLED]),
        }


# Global instance
_batch_controller_instance: Optional[BatchController] = None


def get_batch_controller() -> BatchController:
    """Get global BatchController instance."""
    global _batch_controller_instance
    if _batch_controller_instance is None:
        _batch_controller_instance = BatchController()
        logger.info("Created global BatchController instance")
    return _batch_controller_instance
