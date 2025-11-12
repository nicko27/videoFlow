"""File table management for VideoConverter UI.

This module handles the creation, updating, and rendering of the file
table widget showing conversion status and progress.
"""

from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QProgressBar, QWidget, QHBoxLayout, QVBoxLayout, QPushButton
)
from PyQt6.QtCore import Qt, QMutexLocker, QTimer
from PyQt6.QtGui import QColor
from pathlib import Path
from typing import TYPE_CHECKING

from ..utils import format_size
from src.core.logger import Logger

if TYPE_CHECKING:
    from ..window import VideoConverterWindow

logger = Logger.get_logger('VideoConverter.TableWidget')


class FileTableManager:
    """Manages the file table widget for the VideoConverter UI.

    Handles rendering, updating, and user interactions with the file table
    displaying conversion status and progress.
    """

    def __init__(self, window: 'VideoConverterWindow'):
        """Initialize the file table manager.

        Args:
            window: Parent VideoConverterWindow instance.
        """
        self.window = window

    def create_table(self, layout: QVBoxLayout) -> QTableWidget:
        """Create and configure the file table widget.

        Args:
            layout: Parent layout to add table to.

        Returns:
            Configured QTableWidget instance.
        """
        table = QTableWidget()
        table.setColumnCount(5)

        headers = ["", "File", "State", "Size", "Actions"]
        table.setHorizontalHeaderLabels(headers)

        # Configure column sizing
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)

        table.setColumnWidth(0, 30)   # Checkbox
        table.setColumnWidth(2, 280)  # State - wider for progress bars
        table.setColumnWidth(4, 60)   # Actions

        # Table styling
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setWordWrap(True)

        layout.addWidget(table)
        return table

    def refresh_table(self) -> None:
        """Refresh the entire table with current file data."""
        with QMutexLocker(self.window.files_mutex):
            files_copy = dict(self.window.files_to_convert)

        self.window.files_table.setRowCount(len(files_copy))

        total_selected = 0
        total_size = 0

        for row, (path, info) in enumerate(files_copy.items()):
            self._render_row(row, path, info)

            # Track statistics
            if info.get('selected', True):
                total_selected += 1
                total_size += info.get('size', 0)

        self._update_labels(files_copy, total_selected, total_size)

    def _render_row(self, row: int, path: Path, info: dict) -> None:
        """Render a single table row.

        Args:
            row: Row index.
            path: File path.
            info: File information dictionary.
        """
        # Checkbox
        self._render_checkbox(row, path, info)

        # File name
        self._render_filename(row, path, info)

        # State/Progress
        self._render_state(row, path, info)

        # Size
        self._render_size(row, info)

        # Actions
        self._render_actions(row, path, info)

    def _render_checkbox(self, row: int, path: Path, info: dict) -> None:
        """Render the selection checkbox.

        Args:
            row: Row index.
            path: File path.
            info: File information dictionary.
        """
        checkbox = QCheckBox()
        checkbox.setChecked(info.get('selected', True))
        checkbox.stateChanged.connect(
            lambda state, p=path: self.window.update_selection(p, state)
        )
        self.window.files_table.setCellWidget(row, 0, checkbox)

    def _render_filename(self, row: int, path: Path, info: dict) -> None:
        """Render the filename with color coding.

        Args:
            row: Row index.
            path: File path.
            info: File information dictionary.
        """
        name_item = QTableWidgetItem(path.name)
        name_item.setToolTip(str(path))

        state = info['state']
        is_converted = info.get('is_converted', False)

        # Color coding based on state
        if 'Error' in state or 'Failed' in state:
            name_item.setForeground(QColor('#d32f2f'))  # Red
            name_item.setText(f"❌ {path.name}")
        elif 'Completed' in state or 'Success' in state:
            name_item.setForeground(QColor('#388e3c'))  # Green
            name_item.setText(f"✅ {path.name}")
        elif 'In progress' in state or info.get('worker'):
            name_item.setForeground(QColor('#1976d2'))  # Blue
            name_item.setText(f"⚙️ {path.name}")
        elif is_converted:
            name_item.setForeground(QColor('#FF9800'))  # Orange
            name_item.setText(f"🔄 {path.name}")

        self.window.files_table.setItem(row, 1, name_item)

    def _render_state(self, row: int, path: Path, info: dict) -> None:
        """Render the state column (text or progress bar).

        Args:
            row: Row index.
            path: File path.
            info: File information dictionary.
        """
        progress = info.get('progress', 0)
        attempt = info.get('attempt', 1)
        worker = info.get('worker')

        # Show progress bar if worker is active and progress is valid
        if worker and progress >= 0 and progress != -1:
            self._render_progress_bar(row, progress, attempt)
        else:
            self._render_state_text(row, info)

    def _render_progress_bar(self, row: int, progress: int, attempt: int) -> None:
        """Render a progress bar for active conversion.

        Args:
            row: Row index.
            progress: Progress percentage (0-100).
            attempt: Attempt number.
        """
        progress_widget = QWidget()
        progress_layout = QHBoxLayout(progress_widget)
        progress_layout.setContentsMargins(2, 2, 2, 2)

        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(max(0, min(100, progress)))
        progress_bar.setTextVisible(True)

        # Progress text
        if progress == 0:
            progress_text = f"Attempt {attempt} - Starting..."
        elif progress >= 100:
            progress_text = f"Attempt {attempt} - Finalizing..."
        else:
            progress_text = f"Attempt {attempt} - {progress}%"

        progress_bar.setFormat(progress_text)

        # Color based on attempt
        if attempt == 1:
            color = "#4CAF50"  # Green
        elif attempt == 2:
            color = "#FF9800"  # Orange
        else:
            color = "#f44336"  # Red

        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
                font-size: 11px;
                font-weight: bold;
                height: 22px;
                min-width: 220px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)

        progress_layout.addWidget(progress_bar)
        self.window.files_table.setCellWidget(row, 2, progress_widget)

    def _render_state_text(self, row: int, info: dict) -> None:
        """Render state as text.

        Args:
            row: Row index.
            info: File information dictionary.
        """
        state = info['state']
        is_converted = info.get('is_converted', False)
        state_item = QTableWidgetItem(state)

        # Enhanced display for results
        if 'Completed:' in state:
            result_msg = state.replace('Completed:', '').strip()
            state_item.setForeground(QColor('#388e3c'))  # Green
            state_item.setText(f"✅ {result_msg}")
        elif 'Failed:' in state or 'Error' in state:
            error_msg = state.replace('Failed:', '').replace('Error:', '').strip()
            state_item.setForeground(QColor('#d32f2f'))  # Red
            state_item.setText(f"❌ {error_msg}")
        elif 'Pending' in state:
            if is_converted:
                state_item.setText("⏳ Pending (converted)")
                state_item.setForeground(QColor('#FF9800'))
            else:
                state_item.setText("⏳ Pending")
                state_item.setForeground(QColor('#666'))
        elif 'Stopped' in state:
            state_item.setText("⏹️ Stopped")
            state_item.setForeground(QColor('#666'))

        self.window.files_table.setItem(row, 2, state_item)

    def _render_size(self, row: int, info: dict) -> None:
        """Render the file size.

        Args:
            row: Row index.
            info: File information dictionary.
        """
        size = info.get('size', 0)
        size_item = QTableWidgetItem(format_size(size))
        size_item.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.window.files_table.setItem(row, 3, size_item)

    def _render_actions(self, row: int, path: Path, info: dict) -> None:
        """Render the actions column.

        Args:
            row: Row index.
            path: File path.
            info: File information dictionary.
        """
        worker = info.get('worker')

        if not worker:
            # Delete button for inactive files
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)

            delete_btn = QPushButton("🗑️")
            delete_btn.setMaximumSize(25, 25)
            delete_btn.setToolTip("Remove from list")
            delete_btn.clicked.connect(
                lambda checked, p=path: self.window.remove_file(p)
            )
            action_layout.addWidget(delete_btn)

            self.window.files_table.setCellWidget(row, 4, action_widget)
        else:
            # Active conversion indicator
            attempt = info.get('attempt', 1)
            action_item = QTableWidgetItem("⚙️")
            action_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            action_item.setToolTip(f"Conversion in progress (attempt {attempt})")
            self.window.files_table.setItem(row, 4, action_item)

    def _update_labels(
        self,
        files_copy: dict,
        total_selected: int,
        total_size: int
    ) -> None:
        """Update file count and selection labels.

        Args:
            files_copy: Dictionary of files.
            total_selected: Number of selected files.
            total_size: Total size of selected files.
        """
        converted_count = sum(
            1 for info in files_copy.values()
            if info.get('is_converted', False)
        )

        label_text = (
            f"{len(files_copy)} files "
            f"({total_selected} selected, {format_size(total_size)})"
        )
        if converted_count > 0:
            label_text += f" - {converted_count} already converted"

        if hasattr(self.window, 'file_count_label'):
            self.window.file_count_label.setText(label_text)

        # Update select all button text
        if files_copy and hasattr(self.window, 'select_all_btn'):
            all_selected = all(
                info.get('selected', True) for info in files_copy.values()
            )
            self.window.select_all_btn.setText(
                "☑️ Deselect All" if all_selected else "☑️ Select All"
            )
