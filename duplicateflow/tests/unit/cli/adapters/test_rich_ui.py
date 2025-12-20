"""
Unit tests for RichUIAdapter.

Tests verify that the Rich implementation correctly implements
the IUIAdapter interface.
"""

import pytest
from duplicateflow.core.interfaces import IUIAdapter, MessageType
from duplicateflow.cli.adapters import RichUIAdapter


class TestRichUIAdapter:
    """Tests for RichUIAdapter."""

    def test_rich_ui_adapter_instantiation(self, console):
        """Test that RichUIAdapter can be instantiated."""
        adapter = RichUIAdapter(console)
        assert isinstance(adapter, IUIAdapter)
        assert isinstance(adapter, RichUIAdapter)
        assert adapter.console is console

    def test_rich_ui_adapter_display_message_info(self, console):
        """Test display_message with INFO type."""
        adapter = RichUIAdapter(console)

        # Should not raise any errors
        adapter.display_message("Information message", MessageType.INFO)

    def test_rich_ui_adapter_display_message_success(self, console):
        """Test display_message with SUCCESS type."""
        adapter = RichUIAdapter(console)

        adapter.display_message("Operation succeeded!", MessageType.SUCCESS)

    def test_rich_ui_adapter_display_message_warning(self, console):
        """Test display_message with WARNING type."""
        adapter = RichUIAdapter(console)

        adapter.display_message("Warning message", MessageType.WARNING)

    def test_rich_ui_adapter_display_message_error(self, console):
        """Test display_message with ERROR type."""
        adapter = RichUIAdapter(console)

        adapter.display_message("Error occurred", MessageType.ERROR)

    def test_rich_ui_adapter_display_message_default_type(self, console):
        """Test display_message uses INFO as default."""
        adapter = RichUIAdapter(console)

        # Should default to INFO
        adapter.display_message("Default message")

    def test_rich_ui_adapter_message_types(self, console):
        """Test all message types display correctly."""
        adapter = RichUIAdapter(console)

        # Test all message types
        for msg_type in MessageType:
            adapter.display_message(f"Test {msg_type.value}", msg_type)

    def test_rich_ui_adapter_display_table(self, console):
        """Test display_table creates Rich table."""
        adapter = RichUIAdapter(console)

        headers = ["File", "Size", "Type"]
        rows = [
            ["video1.mp4", "1.2 GB", "MP4"],
            ["video2.mkv", "890 MB", "MKV"],
            ["video3.avi", "450 MB", "AVI"],
        ]

        # Should not raise any errors
        adapter.display_table("Video List", headers, rows)

    def test_rich_ui_adapter_display_table_empty_rows(self, console):
        """Test display_table with empty rows."""
        adapter = RichUIAdapter(console)

        adapter.display_table("Empty Table", ["Col1", "Col2"], [])

    def test_rich_ui_adapter_display_table_single_column(self, console):
        """Test display_table with single column."""
        adapter = RichUIAdapter(console)

        headers = ["Name"]
        rows = [["Item 1"], ["Item 2"]]

        adapter.display_table("Single Column", headers, rows)

    def test_rich_ui_adapter_display_table_many_columns(self, console):
        """Test display_table with many columns."""
        adapter = RichUIAdapter(console)

        headers = ["Col1", "Col2", "Col3", "Col4", "Col5"]
        rows = [
            ["A", "B", "C", "D", "E"],
            ["F", "G", "H", "I", "J"],
        ]

        adapter.display_table("Many Columns", headers, rows)

    def test_rich_ui_adapter_display_panel(self, console):
        """Test display_panel creates Rich panel."""
        adapter = RichUIAdapter(console)

        # Should not raise any errors
        adapter.display_panel("Panel content", title="Test Panel")

    def test_rich_ui_adapter_display_panel_no_title(self, console):
        """Test display_panel without title."""
        adapter = RichUIAdapter(console)

        adapter.display_panel("Panel without title")

    def test_rich_ui_adapter_display_panel_custom_border(self, console):
        """Test display_panel with custom border style."""
        adapter = RichUIAdapter(console)

        adapter.display_panel(
            "Content",
            title="Custom",
            border_style="red"
        )

    def test_rich_ui_adapter_multiple_messages(self, console):
        """Test displaying multiple messages."""
        adapter = RichUIAdapter(console)

        adapter.display_message("Message 1", MessageType.INFO)
        adapter.display_message("Message 2", MessageType.SUCCESS)
        adapter.display_message("Message 3", MessageType.WARNING)
        adapter.display_message("Message 4", MessageType.ERROR)

    def test_rich_ui_adapter_multiple_tables(self, console):
        """Test displaying multiple tables."""
        adapter = RichUIAdapter(console)

        adapter.display_table("Table 1", ["A"], [["1"]])
        adapter.display_table("Table 2", ["B"], [["2"]])
        adapter.display_table("Table 3", ["C"], [["3"]])

    def test_rich_ui_adapter_mixed_output(self, console):
        """Test mixed messages, tables, and panels."""
        adapter = RichUIAdapter(console)

        adapter.display_message("Starting process", MessageType.INFO)
        adapter.display_panel("Configuration loaded", title="Config")
        adapter.display_table("Results", ["Item"], [["Value"]])
        adapter.display_message("Complete", MessageType.SUCCESS)

    def test_rich_ui_adapter_long_message(self, console):
        """Test displaying very long message."""
        adapter = RichUIAdapter(console)

        long_message = "Lorem ipsum " * 100
        adapter.display_message(long_message, MessageType.INFO)

    def test_rich_ui_adapter_special_characters(self, console):
        """Test messages with special characters."""
        adapter = RichUIAdapter(console)

        adapter.display_message("Message with émojis 🎬 📹 🎥")
        adapter.display_message("Message with symbols: @#$%^&*()")
        adapter.display_message("Message with newlines:\nLine 2\nLine 3")

    def test_rich_ui_adapter_unicode_in_table(self, console):
        """Test table with unicode characters."""
        adapter = RichUIAdapter(console)

        headers = ["Fichier", "Taille"]
        rows = [
            ["vidéo1.mp4", "1,2 GB"],
            ["vidéo2.mkv", "890 MB"],
        ]

        adapter.display_table("Liste de Vidéos", headers, rows)

    def test_rich_ui_adapter_table_with_numbers(self, console):
        """Test table converts numbers to strings."""
        adapter = RichUIAdapter(console)

        headers = ["Name", "Count", "Size"]
        rows = [
            ["video1", 10, 1024],
            ["video2", 20, 2048],
        ]

        # Should convert numbers to strings automatically
        adapter.display_table("Statistics", headers, rows)

    def test_rich_ui_adapter_full_workflow(self, console):
        """Test a complete UI workflow."""
        adapter = RichUIAdapter(console)

        # Welcome
        adapter.display_panel(
            "Welcome to DuplicateFlow CLI",
            title="Welcome",
            border_style="cyan"
        )

        # Progress messages
        adapter.display_message("Scanning directories...", MessageType.INFO)
        adapter.display_message("Found 1,247 videos", MessageType.SUCCESS)

        # Results table
        headers = ["File 1", "File 2", "Similarity"]
        rows = [
            ["video1.mp4", "video1_copy.mp4", "100%"],
            ["movie.mkv", "movie_backup.mkv", "98%"],
        ]
        adapter.display_table("Duplicate Groups", headers, rows)

        # Warning
        adapter.display_message(
            "Some files could not be processed",
            MessageType.WARNING
        )

        # Success
        adapter.display_message(
            "Analysis complete!",
            MessageType.SUCCESS
        )
