"""
Rich implementation of IProgressReporter for CLI.

This adapter implements progress reporting using Rich library
for beautiful terminal output.
"""

import time
from typing import Dict
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TaskID
)
from rich.console import Console

from duplicateflow.core.interfaces.i_progress_reporter import IProgressReporter


class RichProgressReporter(IProgressReporter):
    """
    Rich-based progress reporter for CLI.

    Uses Rich Progress to display beautiful progress bars
    in the terminal.
    """

    def __init__(self, console: Console):
        """
        Initialize Rich progress reporter.

        Args:
            console: Rich Console instance
        """
        self.console = console
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        )
        self.tasks: Dict[str, TaskID] = {}
        self.start_time = time.time()
        self.progress.start()

    def start_phase(self, phase_name: str, total: int, message: str = "") -> None:
        """
        Start a new progress phase.

        Args:
            phase_name: Unique identifier for this phase
            total: Total number of steps
            message: Description message
        """
        description = message or phase_name.replace('_', ' ').title()
        task_id = self.progress.add_task(description, total=total)
        self.tasks[phase_name] = task_id

    def update(self, phase_name: str, current: int, message: str = "") -> None:
        """
        Update progress for a phase.

        Args:
            phase_name: Phase identifier
            current: Current step number
            message: Optional status message
        """
        if phase_name not in self.tasks:
            return

        task_id = self.tasks[phase_name]

        if message:
            self.progress.update(task_id, completed=current, description=message)
        else:
            self.progress.update(task_id, completed=current)

    def finish_phase(self, phase_name: str, message: str = "") -> None:
        """
        Mark a phase as complete.

        Args:
            phase_name: Phase identifier
            message: Optional completion message
        """
        if phase_name not in self.tasks:
            return

        task_id = self.tasks[phase_name]
        self.progress.remove_task(task_id)
        del self.tasks[phase_name]

        if message:
            self.console.print(f"[green]✓[/green] {message}")

    def elapsed_time(self) -> float:
        """
        Get elapsed time since start.

        Returns:
            Elapsed time in seconds
        """
        return time.time() - self.start_time

    def stop(self) -> None:
        """Stop the progress display."""
        self.progress.stop()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop progress."""
        self.stop()
