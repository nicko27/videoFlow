"""
Unit tests for IProgressReporter interface and NullProgressReporter.

Tests verify that the null implementation follows the interface contract.
"""

import pytest
from duplicateflow.core.interfaces import IProgressReporter, NullProgressReporter


class TestNullProgressReporter:
    """Tests for NullProgressReporter."""

    def test_null_progress_reporter_instantiation(self):
        """Test that NullProgressReporter can be instantiated."""
        reporter = NullProgressReporter()
        assert isinstance(reporter, IProgressReporter)
        assert isinstance(reporter, NullProgressReporter)

    def test_null_progress_reporter_start_phase(self):
        """Test start_phase does nothing and doesn't raise errors."""
        reporter = NullProgressReporter()

        # Should not raise any errors
        reporter.start_phase("discovery", total=100)
        reporter.start_phase("discovery", total=100, message="Finding videos")

    def test_null_progress_reporter_update(self):
        """Test update does nothing and doesn't raise errors."""
        reporter = NullProgressReporter()

        # Should not raise any errors
        reporter.update("discovery", current=50)
        reporter.update("discovery", current=50, message="Found 50 videos")

    def test_null_progress_reporter_finish_phase(self):
        """Test finish_phase does nothing and doesn't raise errors."""
        reporter = NullProgressReporter()

        # Should not raise any errors
        reporter.finish_phase("discovery")
        reporter.finish_phase("discovery", message="Complete")

    def test_null_progress_reporter_elapsed_time(self):
        """Test elapsed_time returns 0.0."""
        reporter = NullProgressReporter()

        elapsed = reporter.elapsed_time()
        assert elapsed == 0.0
        assert isinstance(elapsed, float)

    def test_null_progress_reporter_full_workflow(self):
        """Test a complete workflow of start -> update -> finish."""
        reporter = NullProgressReporter()

        # Start phase
        reporter.start_phase("hashing", total=10, message="Hashing videos")

        # Update multiple times
        for i in range(10):
            reporter.update("hashing", current=i + 1, message=f"Hashing video {i+1}")

        # Finish phase
        reporter.finish_phase("hashing", message="Hashing complete")

        # Verify elapsed time
        assert reporter.elapsed_time() == 0.0

    def test_null_progress_reporter_multiple_phases(self):
        """Test handling multiple phases."""
        reporter = NullProgressReporter()

        # Phase 1: Discovery
        reporter.start_phase("discovery", total=100)
        reporter.update("discovery", current=100)
        reporter.finish_phase("discovery")

        # Phase 2: Hashing
        reporter.start_phase("hashing", total=50)
        reporter.update("hashing", current=50)
        reporter.finish_phase("hashing")

        # Phase 3: Comparison
        reporter.start_phase("comparison", total=25)
        reporter.update("comparison", current=25)
        reporter.finish_phase("comparison")

        # Should still work fine
        assert reporter.elapsed_time() == 0.0

    def test_null_progress_reporter_no_message(self):
        """Test that message parameter is optional."""
        reporter = NullProgressReporter()

        # All calls should work without message parameter
        reporter.start_phase("test", total=1)
        reporter.update("test", current=1)
        reporter.finish_phase("test")

    def test_null_progress_reporter_empty_message(self):
        """Test that empty messages are handled."""
        reporter = NullProgressReporter()

        reporter.start_phase("test", total=1, message="")
        reporter.update("test", current=1, message="")
        reporter.finish_phase("test", message="")
