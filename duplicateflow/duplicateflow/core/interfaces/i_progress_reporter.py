"""
Progress reporter interface for Clean Architecture.

This interface allows core services to report progress
without depending on CLI or GUI implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional


class IProgressReporter(ABC):
    """
    Interface for reporting progress (CLI, GUI, API, tests).

    Core services use this interface to report progress.
    CLI implements with Rich, GUI with Qt/Tkinter, tests with Null.
    """

    @abstractmethod
    def start_phase(self, phase_name: str, total: int, message: str = "") -> None:
        """
        Start a new phase with a known number of steps.

        Args:
            phase_name: Unique identifier for this phase
            total: Total number of steps in this phase
            message: Optional description message
        """
        pass

    @abstractmethod
    def update(self, phase_name: str, current: int, message: str = "") -> None:
        """
        Update progress for a phase.

        Args:
            phase_name: Phase identifier (from start_phase)
            current: Current step number (0 to total)
            message: Optional status message
        """
        pass

    @abstractmethod
    def finish_phase(self, phase_name: str, message: str = "") -> None:
        """
        Mark a phase as complete.

        Args:
            phase_name: Phase identifier
            message: Optional completion message
        """
        pass

    @abstractmethod
    def elapsed_time(self) -> float:
        """
        Get elapsed time since reporter was created.

        Returns:
            Elapsed time in seconds
        """
        pass


class NullProgressReporter(IProgressReporter):
    """
    Null implementation of IProgressReporter (for tests).

    Does nothing - useful for unit tests where we don't
    need actual progress reporting.
    """

    def start_phase(self, phase_name: str, total: int, message: str = "") -> None:
        """Do nothing."""
        pass

    def update(self, phase_name: str, current: int, message: str = "") -> None:
        """Do nothing."""
        pass

    def finish_phase(self, phase_name: str, message: str = "") -> None:
        """Do nothing."""
        pass

    def elapsed_time(self) -> float:
        """Return 0.0."""
        return 0.0
