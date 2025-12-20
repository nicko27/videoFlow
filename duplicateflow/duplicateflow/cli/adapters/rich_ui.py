"""
Rich implementation of IUIAdapter for CLI.

This adapter implements UI interactions using Rich library
for beautiful terminal output.
"""

from typing import Any, List, Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from duplicateflow.core.interfaces.i_ui_adapter import IUIAdapter, MessageType


class RichUIAdapter(IUIAdapter):
    """
    Rich-based UI adapter for CLI.

    Uses Rich library to display messages, tables, and prompts
    with beautiful formatting in the terminal.
    """

    def __init__(self, console: Console):
        """
        Initialize Rich UI adapter.

        Args:
            console: Rich Console instance
        """
        self.console = console

    def display_message(
        self,
        message: str,
        message_type: MessageType = MessageType.INFO
    ) -> None:
        """
        Display a message with appropriate styling.

        Args:
            message: Message text
            message_type: Type of message (determines color/icon)
        """
        # Style mapping
        styles = {
            MessageType.INFO: ("[cyan]ℹ[/cyan]", "cyan"),
            MessageType.SUCCESS: ("[green]✓[/green]", "green"),
            MessageType.WARNING: ("[yellow]⚠[/yellow]", "yellow"),
            MessageType.ERROR: ("[red]✗[/red]", "red"),
        }

        icon, color = styles.get(message_type, ("[cyan]ℹ[/cyan]", "cyan"))

        self.console.print(f"{icon} {message}", style=color)

    def display_table(
        self,
        title: str,
        headers: List[str],
        rows: List[List[Any]]
    ) -> None:
        """
        Display data in a Rich table.

        Args:
            title: Table title
            headers: Column headers
            rows: Data rows
        """
        table = Table(title=title, show_header=True, header_style="bold cyan")

        # Add columns
        for header in headers:
            table.add_column(header)

        # Add rows
        for row in rows:
            # Convert all values to strings
            str_row = [str(cell) for cell in row]
            table.add_row(*str_row)

        self.console.print(table)

    def ask_question(
        self,
        question: str,
        choices: Optional[List[str]] = None,
        default: Optional[str] = None
    ) -> str:
        """
        Ask a question and get user input.

        Args:
            question: Question text
            choices: Optional list of valid choices
            default: Optional default value

        Returns:
            User's answer
        """
        return Prompt.ask(
            f"[yellow]{question}[/yellow]",
            choices=choices,
            default=default
        )

    def confirm(self, question: str, default: bool = False) -> bool:
        """
        Ask a yes/no question.

        Args:
            question: Question text
            default: Default answer

        Returns:
            True for yes, False for no
        """
        return Confirm.ask(
            f"[yellow]{question}[/yellow]",
            default=default
        )

    def display_panel(
        self,
        content: str,
        title: str = "",
        border_style: str = "cyan"
    ) -> None:
        """
        Display content in a panel.

        Args:
            content: Panel content
            title: Optional panel title
            border_style: Border color/style
        """
        panel = Panel(
            content,
            title=title if title else None,
            border_style=border_style
        )
        self.console.print(panel)
