"""
Unit tests for RichProgressReporter.

Tests verify that the Rich implementation correctly implements
the IProgressReporter interface.
"""

import pytest
import time
from duplicateflow.core.interfaces import IProgressReporter
from duplicateflow.cli.adapters import RichProgressReporter


class TestRichProgressReporter:
    """Tests for RichProgressReporter."""

    def test_rich_progress_reporter_instantiation(self, console):
        """Test that RichProgressReporter can be instantiated."""
        reporter = RichProgressReporter(console)
        assert isinstance(reporter, IProgressReporter)
        assert isinstance(reporter, RichProgressReporter)
        assert reporter.console is console
        assert reporter.tasks == {}

    def test_rich_progress_reporter_start_phase(self, console):
        """Test start_phase creates a new task."""
        reporter = RichProgressReporter(console)

        reporter.start_phase("discovery", total=100, message="Finding videos")

        assert "discovery" in reporter.tasks
        assert len(reporter.tasks) == 1

    def test_rich_progress_reporter_start_phase_no_message(self, console):
        """Test start_phase uses phase name as description when no message."""
        reporter = RichProgressReporter(console)

        reporter.start_phase("video_hashing", total=50)

        # Should create task with formatted phase name
        assert "video_hashing" in reporter.tasks

    def test_rich_progress_reporter_update(self, console):
        """Test update changes task progress."""
        reporter = RichProgressReporter(console)

        reporter.start_phase("hashing", total=10)
        reporter.update("hashing", current=5)

        # Task should still exist
        assert "hashing" in reporter.tasks

    def test_rich_progress_reporter_update_with_message(self, console):
        """Test update with custom message."""
        reporter = RichProgressReporter(console)

        reporter.start_phase("comparison", total=100)
        reporter.update("comparison", current=50, message="Comparing videos...")

        assert "comparison" in reporter.tasks

    def test_rich_progress_reporter_update_nonexistent_phase(self, console):
        """Test update for non-existent phase doesn't crash."""
        reporter = RichProgressReporter(console)

        # Should not raise any errors
        reporter.update("nonexistent", current=50)

    def test_rich_progress_reporter_finish_phase(self, console):
        """Test finish_phase removes task."""
        reporter = RichProgressReporter(console)

        reporter.start_phase("scan", total=100)
        assert "scan" in reporter.tasks

        reporter.finish_phase("scan", message="Scan complete")

        # Task should be removed
        assert "scan" not in reporter.tasks

    def test_rich_progress_reporter_finish_phase_no_message(self, console):
        """Test finish_phase without message."""
        reporter = RichProgressReporter(console)

        reporter.start_phase("test", total=1)
        reporter.finish_phase("test")

        assert "test" not in reporter.tasks

    def test_rich_progress_reporter_finish_nonexistent_phase(self, console):
        """Test finish_phase for non-existent phase doesn't crash."""
        reporter = RichProgressReporter(console)

        # Should not raise any errors
        reporter.finish_phase("nonexistent")

    def test_rich_progress_reporter_elapsed_time(self, console):
        """Test elapsed_time returns positive value."""
        reporter = RichProgressReporter(console)

        # Wait a tiny bit
        time.sleep(0.01)

        elapsed = reporter.elapsed_time()
        assert elapsed > 0
        assert isinstance(elapsed, float)

    def test_rich_progress_reporter_elapsed_time_increases(self, console):
        """Test elapsed_time increases over time."""
        reporter = RichProgressReporter(console)

        first_time = reporter.elapsed_time()
        time.sleep(0.02)
        second_time = reporter.elapsed_time()

        assert second_time > first_time

    def test_rich_progress_reporter_context_manager(self, console):
        """Test RichProgressReporter as context manager."""
        with RichProgressReporter(console) as reporter:
            assert isinstance(reporter, RichProgressReporter)
            reporter.start_phase("test", total=10)
            reporter.update("test", current=5)
            reporter.finish_phase("test")

        # Context manager should have called stop()
        # Progress should be stopped (hard to test without output inspection)

    def test_rich_progress_reporter_multiple_phases(self, console):
        """Test handling multiple concurrent phases."""
        reporter = RichProgressReporter(console)

        # Start multiple phases
        reporter.start_phase("discovery", total=100)
        reporter.start_phase("hashing", total=50)
        reporter.start_phase("comparison", total=25)

        assert len(reporter.tasks) == 3

        # Update all phases
        reporter.update("discovery", current=50)
        reporter.update("hashing", current=25)
        reporter.update("comparison", current=10)

        # Finish in different order
        reporter.finish_phase("hashing")
        assert len(reporter.tasks) == 2

        reporter.finish_phase("discovery")
        assert len(reporter.tasks) == 1

        reporter.finish_phase("comparison")
        assert len(reporter.tasks) == 0

    def test_rich_progress_reporter_full_workflow(self, console):
        """Test a complete workflow."""
        reporter = RichProgressReporter(console)

        # Phase 1: Discovery
        reporter.start_phase("discovery", total=100, message="Discovering videos")
        for i in range(0, 101, 20):
            reporter.update("discovery", current=i)
        reporter.finish_phase("discovery", message="Found 1247 videos")

        # Phase 2: Hashing
        reporter.start_phase("hashing", total=1247, message="Hashing videos")
        reporter.update("hashing", current=623)
        reporter.update("hashing", current=1247)
        reporter.finish_phase("hashing", message="Hashing complete")

        # Verify all phases finished
        assert len(reporter.tasks) == 0
        assert reporter.elapsed_time() > 0

    def test_rich_progress_reporter_stop(self, console):
        """Test stop method."""
        reporter = RichProgressReporter(console)

        reporter.start_phase("test", total=100)
        reporter.stop()

        # Progress should be stopped
        # (Output verification would require mocking Rich internals)

    def test_rich_progress_reporter_phase_override(self, console):
        """Test starting same phase twice (should create new task)."""
        reporter = RichProgressReporter(console)

        reporter.start_phase("test", total=100)
        first_task_id = reporter.tasks["test"]

        # Start again with same name
        reporter.start_phase("test", total=50)
        second_task_id = reporter.tasks["test"]

        # Should have replaced the task
        assert first_task_id != second_task_id

    def test_rich_progress_reporter_zero_total(self, console):
        """Test phase with zero total."""
        reporter = RichProgressReporter(console)

        reporter.start_phase("empty", total=0)
        reporter.update("empty", current=0)
        reporter.finish_phase("empty")

        assert "empty" not in reporter.tasks
