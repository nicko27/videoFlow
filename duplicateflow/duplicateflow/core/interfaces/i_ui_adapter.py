"""
UI adapter interface for Clean Architecture.

This interface allows core services to interact with UI
without depending on CLI or GUI implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class MessageType(Enum):
    """Types of messages that can be displayed."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class IUIAdapter(ABC):
    """
    Interface for UI interactions (CLI, GUI, API).

    Core services use this interface to display information,
    ask questions, and interact with users.
    """

    @abstractmethod
    def display_message(
        self,
        message: str,
        message_type: MessageType = MessageType.INFO
    ) -> None:
        """
        Display a message to the user.

        Args:
            message: Message text
            message_type: Type of message (info, success, warning, error)
        """
        pass

    @abstractmethod
    def display_table(
        self,
        title: str,
        headers: List[str],
        rows: List[List[Any]]
    ) -> None:
        """
        Display data in table format.

        Args:
            title: Table title
            headers: Column headers
            rows: Data rows
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def confirm(self, question: str, default: bool = False) -> bool:
        """
        Ask a yes/no question.

        Args:
            question: Question text
            default: Default answer if user just presses Enter

        Returns:
            True for yes, False for no
        """
        pass


class NullUIAdapter(IUIAdapter):
    """
    Null implementation of IUIAdapter (for tests).

    Returns default values for all questions,
    stores messages for later inspection.
    """

    def __init__(self):
        """Initialize null adapter."""
        self.messages: List[Dict[str, Any]] = []
        self.tables: List[Dict[str, Any]] = []

    def display_message(
        self,
        message: str,
        message_type: MessageType = MessageType.INFO
    ) -> None:
        """Store message."""
        self.messages.append({
            'message': message,
            'type': message_type
        })

    def display_table(
        self,
        title: str,
        headers: List[str],
        rows: List[List[Any]]
    ) -> None:
        """Store table."""
        self.tables.append({
            'title': title,
            'headers': headers,
            'rows': rows
        })

    def ask_question(
        self,
        question: str,
        choices: Optional[List[str]] = None,
        default: Optional[str] = None
    ) -> str:
        """Return default or first choice."""
        if default:
            return default
        if choices:
            return choices[0]
        return ""

    def confirm(self, question: str, default: bool = False) -> bool:
        """Return default."""
        return default
