"""Segments panel widget for Video Editor."""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QTableWidget, QTableWidgetItem,
                            QHeaderView, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from src.core.logger import Logger
from src.core.i18n import t

logger = Logger.get_logger('VideoEditor.SegmentsPanel')


class SegmentsPanel(QWidget):
    """Panel for managing video segments."""

    # Signals
    segment_selected = pyqtSignal(list)  # List of selected row indices
    add_segment_clicked = pyqtSignal()
    delete_segments_clicked = pyqtSignal()
    cut_at_cursor_clicked = pyqtSignal()
    merge_segments_clicked = pyqtSignal()
    copy_segments_clicked = pyqtSignal()
    paste_segments_clicked = pyqtSignal()
    transition_clicked = pyqtSignal(int)  # Row index for transition config
    text_overlay_clicked = pyqtSignal(int)  # Row index for text overlay config

    def __init__(self, parent=None):
        """Initialize segments panel."""
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Title
        title_layout = QHBoxLayout()
        title = QLabel(t("video_editor.segments_panel.title", "📋 Segments"))
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_layout.addWidget(title)

        self.count_label = QLabel("(0)")
        self.count_label.setStyleSheet("color: gray;")
        title_layout.addWidget(self.count_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # Segments table
        self.segments_table = QTableWidget()
        self.segments_table.setColumnCount(4)
        self.segments_table.setHorizontalHeaderLabels([
            "#",
            t("video_editor.segments_panel.start", "Start"),
            t("video_editor.segments_panel.end", "End"),
            t("video_editor.segments_panel.name", "Name")
        ])

        # Configure columns
        header = self.segments_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        # Enable selection
        self.segments_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.segments_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.segments_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.segments_table.customContextMenuRequested.connect(self._show_context_menu)
        self.segments_table.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self.segments_table)

        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(5)

        # Row 1
        row1 = QHBoxLayout()

        add_btn = QPushButton("➕")
        add_btn.setToolTip(t("video_editor.segments_panel.add_tooltip", "Add segment (I → O → C)"))
        add_btn.setMaximumWidth(40)
        add_btn.clicked.connect(self.add_segment_clicked.emit)
        row1.addWidget(add_btn)

        delete_btn = QPushButton("🗑️")
        delete_btn.setToolTip(t("video_editor.segments_panel.delete_tooltip", "Delete selection (Delete)"))
        delete_btn.setMaximumWidth(40)
        delete_btn.clicked.connect(self.delete_segments_clicked.emit)
        row1.addWidget(delete_btn)

        row1.addStretch()

        cut_btn = QPushButton("✂️")
        cut_btn.setToolTip(t("video_editor.segments_panel.cut_tooltip", "Cut at cursor (S)"))
        cut_btn.setMaximumWidth(40)
        cut_btn.clicked.connect(self.cut_at_cursor_clicked.emit)
        row1.addWidget(cut_btn)

        merge_btn = QPushButton("🔗")
        merge_btn.setToolTip(t("video_editor.segments_panel.merge_tooltip", "Merge selection (Ctrl+M)"))
        merge_btn.setMaximumWidth(40)
        merge_btn.clicked.connect(self.merge_segments_clicked.emit)
        row1.addWidget(merge_btn)

        buttons_layout.addLayout(row1)

        # Row 2
        row2 = QHBoxLayout()

        copy_btn = QPushButton(t("video_editor.segments_panel.copy", "📋 Copy"))
        copy_btn.setToolTip(t("video_editor.segments_panel.copy_tooltip", "Copy selection (Ctrl+C)"))
        copy_btn.clicked.connect(self.copy_segments_clicked.emit)
        row2.addWidget(copy_btn)

        paste_btn = QPushButton(t("video_editor.segments_panel.paste", "📄 Paste"))
        paste_btn.setToolTip(t("video_editor.segments_panel.paste_tooltip", "Paste (Ctrl+V)"))
        paste_btn.clicked.connect(self.paste_segments_clicked.emit)
        row2.addWidget(paste_btn)

        # Add transition button
        row2.addWidget(QLabel("|"))

        transition_btn = QPushButton(t("video_editor.segments_panel.transition", "⚡ Transition"))
        transition_btn.setToolTip(t("video_editor.segments_panel.transition_tooltip", "Configure transition for selected segment"))
        transition_btn.clicked.connect(self._on_transition_button_clicked)
        row2.addWidget(transition_btn)

        # Add text overlay button
        text_overlay_btn = QPushButton(t("video_editor.segments_panel.text", "📝 Text"))
        text_overlay_btn.setToolTip(t("video_editor.segments_panel.text_tooltip", "Add text/title to selected segment"))
        text_overlay_btn.clicked.connect(self._on_text_overlay_button_clicked)
        row2.addWidget(text_overlay_btn)

        layout.addLayout(buttons_layout)
        layout.addLayout(row2)

    def add_segment(self, index: int, start_time: str, end_time: str, name: str):
        """Add segment to table."""
        row = self.segments_table.rowCount()
        self.segments_table.insertRow(row)

        # Index
        item = QTableWidgetItem(str(index))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.segments_table.setItem(row, 0, item)

        # Start time
        item = QTableWidgetItem(start_time)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.segments_table.setItem(row, 1, item)

        # End time
        item = QTableWidgetItem(end_time)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.segments_table.setItem(row, 2, item)

        # Name
        item = QTableWidgetItem(name)
        self.segments_table.setItem(row, 3, item)

        self._update_count()

    def clear_segments(self):
        """Clear all segments."""
        self.segments_table.setRowCount(0)
        self._update_count()

    def remove_selected(self):
        """Remove selected segments."""
        selected_rows = sorted([index.row() for index in self.segments_table.selectedIndexes()], reverse=True)
        for row in set(selected_rows):
            self.segments_table.removeRow(row)
        self._update_count()

    def get_selected_rows(self):
        """Get list of selected row indices."""
        return sorted(set(index.row() for index in self.segments_table.selectedIndexes()))

    def _update_count(self):
        """Update segment count label."""
        count = self.segments_table.rowCount()
        self.count_label.setText(f"({count})")

    def _on_selection_changed(self):
        """Handle selection change."""
        selected = self.get_selected_rows()
        self.segment_selected.emit(selected)

    def _show_context_menu(self, position):
        """Show context menu."""
        menu = QMenu()

        selected = self.get_selected_rows()
        if not selected:
            return

        if len(selected) == 1:
            rename_action = menu.addAction(t("video_editor.segments_panel.rename", "✏️ Rename"))
            rename_action.triggered.connect(lambda: self._rename_segment(selected[0]))

            transition_action = menu.addAction(t("video_editor.segments_panel.configure_transition", "⚡ Configure Transition"))
            transition_action.triggered.connect(lambda: self.transition_clicked.emit(selected[0]))

            text_overlay_action = menu.addAction(t("video_editor.segments_panel.add_text", "📝 Add Text/Title"))
            text_overlay_action.triggered.connect(lambda: self.text_overlay_clicked.emit(selected[0]))

            menu.addSeparator()

        if len(selected) >= 2:
            merge_action = menu.addAction(t("video_editor.segments_panel.merge", "🔗 Merge"))
            merge_action.triggered.connect(self.merge_segments_clicked.emit)
            menu.addSeparator()

        delete_action = menu.addAction(t("video_editor.segments_panel.delete", "🗑️ Delete"))
        delete_action.triggered.connect(self.delete_segments_clicked.emit)

        copy_action = menu.addAction(t("video_editor.segments_panel.copy_menu", "📋 Copy"))
        copy_action.triggered.connect(self.copy_segments_clicked.emit)

        menu.exec(self.segments_table.mapToGlobal(position))

    def _rename_segment(self, row):
        """Enable inline editing for segment name."""
        self.segments_table.editItem(self.segments_table.item(row, 3))

    def set_segment_name(self, row: int, name: str):
        """Set segment name."""
        if 0 <= row < self.segments_table.rowCount():
            item = self.segments_table.item(row, 3)
            if item:
                item.setText(name)

    def get_segment_name(self, row: int) -> str:
        """Get segment name."""
        if 0 <= row < self.segments_table.rowCount():
            item = self.segments_table.item(row, 3)
            if item:
                return item.text()
        return ""

    def _on_transition_button_clicked(self):
        """Handle transition button click."""
        selected = self.get_selected_rows()
        if len(selected) == 1:
            self.transition_clicked.emit(selected[0])
        elif len(selected) == 0:
            # Show info message
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                t("video_editor.segments_panel.no_selection", "No Selection"),
                t("video_editor.segments_panel.select_segment_transition", "Please select a segment to configure its transition.")
            )
        else:
            # Multiple selection
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                t("video_editor.segments_panel.multiple_selection", "Multiple Selection"),
                t("video_editor.segments_panel.select_single_transition", "Please select a single segment to configure its transition.")
            )

    def _on_text_overlay_button_clicked(self):
        """Handle text overlay button click."""
        selected = self.get_selected_rows()
        if len(selected) == 1:
            self.text_overlay_clicked.emit(selected[0])
        elif len(selected) == 0:
            # Show info message
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                t("video_editor.segments_panel.no_selection", "No Selection"),
                t("video_editor.segments_panel.select_segment_text", "Please select a segment to add text.")
            )
        else:
            # Multiple selection
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                t("video_editor.segments_panel.multiple_selection", "Multiple Selection"),
                t("video_editor.segments_panel.select_single_text", "Please select a single segment to add text.")
            )
