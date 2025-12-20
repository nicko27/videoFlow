"""
Unit tests for IUIAdapter interface and NullUIAdapter.

Tests verify that the null implementation follows the interface contract
and stores data for inspection during tests.
"""

import pytest
from duplicateflow.core.interfaces import IUIAdapter, MessageType, NullUIAdapter


class TestNullUIAdapter:
    """Tests for NullUIAdapter."""

    def test_null_ui_adapter_instantiation(self):
        """Test that NullUIAdapter can be instantiated."""
        adapter = NullUIAdapter()
        assert isinstance(adapter, IUIAdapter)
        assert isinstance(adapter, NullUIAdapter)
        assert adapter.messages == []
        assert adapter.tables == []

    def test_null_ui_adapter_display_message_info(self):
        """Test display_message stores info messages."""
        adapter = NullUIAdapter()

        adapter.display_message("Test message", MessageType.INFO)

        assert len(adapter.messages) == 1
        assert adapter.messages[0]['message'] == "Test message"
        assert adapter.messages[0]['type'] == MessageType.INFO

    def test_null_ui_adapter_display_message_success(self):
        """Test display_message stores success messages."""
        adapter = NullUIAdapter()

        adapter.display_message("Operation succeeded!", MessageType.SUCCESS)

        assert len(adapter.messages) == 1
        assert adapter.messages[0]['type'] == MessageType.SUCCESS

    def test_null_ui_adapter_display_message_warning(self):
        """Test display_message stores warning messages."""
        adapter = NullUIAdapter()

        adapter.display_message("Warning!", MessageType.WARNING)

        assert len(adapter.messages) == 1
        assert adapter.messages[0]['type'] == MessageType.WARNING

    def test_null_ui_adapter_display_message_error(self):
        """Test display_message stores error messages."""
        adapter = NullUIAdapter()

        adapter.display_message("Error occurred", MessageType.ERROR)

        assert len(adapter.messages) == 1
        assert adapter.messages[0]['type'] == MessageType.ERROR

    def test_null_ui_adapter_display_message_default_type(self):
        """Test display_message uses INFO as default type."""
        adapter = NullUIAdapter()

        adapter.display_message("Default message")

        assert len(adapter.messages) == 1
        assert adapter.messages[0]['type'] == MessageType.INFO

    def test_null_ui_adapter_message_storage(self):
        """Test that multiple messages are stored correctly."""
        adapter = NullUIAdapter()

        adapter.display_message("Message 1", MessageType.INFO)
        adapter.display_message("Message 2", MessageType.SUCCESS)
        adapter.display_message("Message 3", MessageType.ERROR)

        assert len(adapter.messages) == 3
        assert adapter.messages[0]['message'] == "Message 1"
        assert adapter.messages[1]['message'] == "Message 2"
        assert adapter.messages[2]['message'] == "Message 3"

    def test_null_ui_adapter_display_table(self):
        """Test display_table stores table data."""
        adapter = NullUIAdapter()

        headers = ["Name", "Size", "Type"]
        rows = [
            ["video1.mp4", "1.2 GB", "MP4"],
            ["video2.mkv", "890 MB", "MKV"],
        ]

        adapter.display_table("Video List", headers, rows)

        assert len(adapter.tables) == 1
        assert adapter.tables[0]['title'] == "Video List"
        assert adapter.tables[0]['headers'] == headers
        assert adapter.tables[0]['rows'] == rows

    def test_null_ui_adapter_table_storage(self):
        """Test that multiple tables are stored correctly."""
        adapter = NullUIAdapter()

        adapter.display_table("Table 1", ["Col1"], [["Data1"]])
        adapter.display_table("Table 2", ["Col2"], [["Data2"]])

        assert len(adapter.tables) == 2
        assert adapter.tables[0]['title'] == "Table 1"
        assert adapter.tables[1]['title'] == "Table 2"

    def test_null_ui_adapter_ask_question_with_default(self):
        """Test ask_question returns default value."""
        adapter = NullUIAdapter()

        answer = adapter.ask_question("Choose option", default="default_value")

        assert answer == "default_value"

    def test_null_ui_adapter_ask_question_with_choices(self):
        """Test ask_question returns first choice when no default."""
        adapter = NullUIAdapter()

        answer = adapter.ask_question(
            "Choose option",
            choices=["fast", "balanced", "thorough"]
        )

        assert answer == "fast"

    def test_null_ui_adapter_ask_question_default_over_choices(self):
        """Test ask_question prefers default over first choice."""
        adapter = NullUIAdapter()

        answer = adapter.ask_question(
            "Choose option",
            choices=["fast", "balanced"],
            default="balanced"
        )

        assert answer == "balanced"

    def test_null_ui_adapter_ask_question_no_choices_no_default(self):
        """Test ask_question returns empty string when no choices/default."""
        adapter = NullUIAdapter()

        answer = adapter.ask_question("Enter name")

        assert answer == ""

    def test_null_ui_adapter_confirm_default_false(self):
        """Test confirm returns False by default."""
        adapter = NullUIAdapter()

        result = adapter.confirm("Delete files?")

        assert result is False

    def test_null_ui_adapter_confirm_default_true(self):
        """Test confirm returns default value."""
        adapter = NullUIAdapter()

        result = adapter.confirm("Continue?", default=True)

        assert result is True

    def test_null_ui_adapter_full_workflow(self):
        """Test a complete workflow using the adapter."""
        adapter = NullUIAdapter()

        # Display welcome message
        adapter.display_message("Welcome to DuplicateFlow", MessageType.INFO)

        # Ask for pipeline choice
        pipeline = adapter.ask_question(
            "Choose pipeline",
            choices=["fast", "balanced", "thorough"],
            default="balanced"
        )

        # Display progress
        adapter.display_message("Scanning files...", MessageType.INFO)
        adapter.display_message("Found duplicates!", MessageType.SUCCESS)

        # Display results table
        headers = ["File 1", "File 2", "Similarity"]
        rows = [["video1.mp4", "video2.mp4", "95%"]]
        adapter.display_table("Duplicates Found", headers, rows)

        # Ask for confirmation
        should_delete = adapter.confirm("Delete duplicates?", default=False)

        # Verify stored data
        assert len(adapter.messages) == 3
        assert len(adapter.tables) == 1
        assert pipeline == "balanced"
        assert should_delete is False

    def test_null_ui_adapter_empty_table(self):
        """Test display_table with empty rows."""
        adapter = NullUIAdapter()

        adapter.display_table("Empty Table", ["Col1", "Col2"], [])

        assert len(adapter.tables) == 1
        assert adapter.tables[0]['rows'] == []

    def test_null_ui_adapter_empty_choices(self):
        """Test ask_question with empty choices list."""
        adapter = NullUIAdapter()

        answer = adapter.ask_question("Question", choices=[])

        # Should return empty string when choices is empty list
        assert answer == ""
