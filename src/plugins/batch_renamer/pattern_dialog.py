"""Pattern Management Dialog for Batch Renamer."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QCheckBox, QGroupBox, QMessageBox, QTextEdit,
    QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from src.core.logger import Logger
from .pattern_manager import PatternManager, PatternPosition

logger = Logger.get_logger('BatchRenamer.PatternDialog')


class PatternManagementDialog(QDialog):
    """
    Dialog for managing removal patterns.

    Features:
    - View all patterns
    - Add new patterns
    - Enable/disable patterns
    - Delete patterns
    - Detect patterns from current files
    - Import/export patterns
    """

    def __init__(self, pattern_manager: PatternManager, current_files: list = None, parent=None):
        """
        Initialize pattern management dialog.

        Args:
            pattern_manager: PatternManager instance
            current_files: Optional list of current filenames for pattern detection
            parent: Parent widget
        """
        super().__init__(parent)
        self.pattern_manager = pattern_manager
        self.current_files = current_files or []

        self.setWindowTitle("🏷️ Pattern Management")
        self.setMinimumSize(900, 600)
        self.setModal(True)

        self.init_ui()
        self.load_patterns_to_table()

    def init_ui(self):
        """Initialize user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Pattern Management")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Tabs for different functions
        tabs = QTabWidget()

        # Tab 1: Manage Patterns
        manage_tab = QWidget()
        manage_layout = QVBoxLayout(manage_tab)

        # Patterns table
        self.patterns_table = QTableWidget()
        self.patterns_table.setColumnCount(5)
        self.patterns_table.setHorizontalHeaderLabels([
            "Enabled", "Pattern", "Position", "Description", "Actions"
        ])
        self.patterns_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.patterns_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.patterns_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.patterns_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.patterns_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        manage_layout.addWidget(self.patterns_table)

        # Add pattern section
        add_group = QGroupBox("Add New Pattern")
        add_layout = QVBoxLayout()

        # Pattern input
        pattern_input_layout = QHBoxLayout()
        pattern_input_layout.addWidget(QLabel("Pattern:"))
        self.new_pattern_input = QLineEdit()
        self.new_pattern_input.setPlaceholderText("e.g., x264, YIFY, BluRay")
        pattern_input_layout.addWidget(self.new_pattern_input)
        add_layout.addLayout(pattern_input_layout)

        # Position and options
        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel("Position:"))

        self.position_combo = QComboBox()
        self.position_combo.addItems(["Anywhere", "Start of name", "End of name"])
        options_layout.addWidget(self.position_combo)

        self.regex_check = QCheckBox("Regex Pattern")
        options_layout.addWidget(self.regex_check)

        options_layout.addStretch()
        add_layout.addLayout(options_layout)

        # Description
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Optional description")
        desc_layout.addWidget(self.description_input)
        add_layout.addLayout(desc_layout)

        # Add button
        add_btn = QPushButton("➕ Add Pattern")
        add_btn.clicked.connect(self.add_pattern)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 8px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        add_layout.addWidget(add_btn)

        add_group.setLayout(add_layout)
        manage_layout.addWidget(add_group)

        tabs.addTab(manage_tab, "📋 Manage Patterns")

        # Tab 2: Auto-Detect Patterns
        detect_tab = QWidget()
        detect_layout = QVBoxLayout(detect_tab)

        detect_info = QLabel(
            "Analyze your current files to detect common patterns that could be removed.\n"
            "Patterns found in multiple files will be suggested for addition."
        )
        detect_info.setWordWrap(True)
        detect_info.setStyleSheet("color: gray; font-style: italic;")
        detect_layout.addWidget(detect_info)

        # Detection parameters
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("Minimum occurrences:"))

        self.min_freq_input = QLineEdit("3")
        self.min_freq_input.setMaximumWidth(50)
        params_layout.addWidget(self.min_freq_input)

        params_layout.addWidget(QLabel("Minimum pattern length:"))
        self.min_length_input = QLineEdit("3")
        self.min_length_input.setMaximumWidth(50)
        params_layout.addWidget(self.min_length_input)

        detect_btn = QPushButton("🔍 Detect Patterns")
        detect_btn.clicked.connect(self.detect_patterns)
        params_layout.addWidget(detect_btn)

        params_layout.addStretch()
        detect_layout.addLayout(params_layout)

        # Detected patterns table
        self.detected_table = QTableWidget()
        self.detected_table.setColumnCount(5)
        self.detected_table.setHorizontalHeaderLabels([
            "Pattern", "Found in # files", "Position", "Example", "Add"
        ])
        self.detected_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.detected_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.detected_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.detected_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.detected_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        detect_layout.addWidget(self.detected_table)

        tabs.addTab(detect_tab, "🔍 Auto-Detect")

        # Tab 3: Statistics
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)

        stats_info = QLabel(
            "See which patterns would affect your current files and how many files would be changed."
        )
        stats_info.setWordWrap(True)
        stats_info.setStyleSheet("color: gray; font-style: italic;")
        stats_layout.addWidget(stats_info)

        refresh_stats_btn = QPushButton("🔄 Refresh Statistics")
        refresh_stats_btn.clicked.connect(self.refresh_statistics)
        stats_layout.addWidget(refresh_stats_btn)

        self.stats_display = QTextEdit()
        self.stats_display.setReadOnly(True)
        stats_layout.addWidget(self.stats_display)

        tabs.addTab(stats_tab, "📊 Statistics")

        layout.addWidget(tabs)

        # Bottom buttons
        button_layout = QHBoxLayout()

        save_btn = QPushButton("💾 Save & Close")
        save_btn.clicked.connect(self.accept)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def load_patterns_to_table(self):
        """Load all patterns into the table."""
        self.patterns_table.setRowCount(0)

        for pattern_dict in self.pattern_manager.patterns:
            row = self.patterns_table.rowCount()
            self.patterns_table.insertRow(row)

            # Enabled checkbox
            enabled_check = QCheckBox()
            enabled_check.setChecked(pattern_dict.get('enabled', True))
            enabled_check.stateChanged.connect(
                lambda state, p=pattern_dict['pattern']: self.toggle_pattern(p)
            )
            self.patterns_table.setCellWidget(row, 0, enabled_check)

            # Pattern
            self.patterns_table.setItem(row, 1, QTableWidgetItem(pattern_dict['pattern']))

            # Position
            position = pattern_dict.get('position', PatternPosition.ANYWHERE)
            position_display = {
                PatternPosition.ANYWHERE: "Anywhere",
                PatternPosition.START: "Start",
                PatternPosition.END: "End"
            }.get(position, position)
            self.patterns_table.setItem(row, 2, QTableWidgetItem(position_display))

            # Description
            description = pattern_dict.get('description', '')
            if pattern_dict.get('is_regex'):
                description = f"[REGEX] {description}"
            self.patterns_table.setItem(row, 3, QTableWidgetItem(description))

            # Delete button
            delete_btn = QPushButton("🗑️")
            delete_btn.setMaximumWidth(40)
            delete_btn.clicked.connect(lambda _, p=pattern_dict['pattern']: self.delete_pattern(p))
            self.patterns_table.setCellWidget(row, 4, delete_btn)

    def add_pattern(self):
        """Add a new pattern."""
        pattern = self.new_pattern_input.text().strip()
        if not pattern:
            QMessageBox.warning(self, "Empty Pattern", "Please enter a pattern")
            return

        # Get position
        position_map = {
            0: PatternPosition.ANYWHERE,
            1: PatternPosition.START,
            2: PatternPosition.END
        }
        position = position_map[self.position_combo.currentIndex()]

        # Get description
        description = self.description_input.text().strip()

        # Add to manager
        if self.pattern_manager.add_pattern(
            pattern,
            position,
            description,
            is_regex=self.regex_check.isChecked()
        ):
            # Reload table
            self.load_patterns_to_table()

            # Clear inputs
            self.new_pattern_input.clear()
            self.description_input.clear()
            self.regex_check.setChecked(False)

            QMessageBox.information(self, "Success", f"Pattern '{pattern}' added successfully")
        else:
            QMessageBox.warning(self, "Duplicate", f"Pattern '{pattern}' already exists")

    def delete_pattern(self, pattern: str):
        """Delete a pattern."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete pattern '{pattern}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.pattern_manager.remove_pattern(pattern):
                self.load_patterns_to_table()
                QMessageBox.information(self, "Success", f"Pattern '{pattern}' deleted")

    def toggle_pattern(self, pattern: str):
        """Toggle pattern enabled state."""
        self.pattern_manager.toggle_pattern(pattern)

    def detect_patterns(self):
        """Detect patterns from current files."""
        if not self.current_files:
            QMessageBox.information(
                self,
                "No Files",
                "No files loaded. Add files to the batch renamer first."
            )
            return

        try:
            min_freq = int(self.min_freq_input.text())
            min_length = int(self.min_length_input.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers")
            return

        # Detect patterns
        detected = self.pattern_manager.detect_patterns(
            self.current_files,
            min_frequency=min_freq,
            min_length=min_length
        )

        # Display in table
        self.detected_table.setRowCount(0)

        if not detected:
            QMessageBox.information(
                self,
                "No Patterns Found",
                f"No new patterns found with minimum {min_freq} occurrences and {min_length} characters length."
            )
            return

        for pattern_data in detected:
            # Handle both old format (3 items) and new format (4 items with example)
            if len(pattern_data) == 4:
                pattern, count, position, example = pattern_data
            else:
                pattern, count, position = pattern_data
                example = ""

            row = self.detected_table.rowCount()
            self.detected_table.insertRow(row)

            # Pattern
            pattern_item = QTableWidgetItem(pattern)
            pattern_item.setFont(QFont("Courier", 10, QFont.Weight.Bold))
            self.detected_table.setItem(row, 0, pattern_item)

            # Count
            count_item = QTableWidgetItem(str(count))
            self.detected_table.setItem(row, 1, count_item)

            # Position
            position_display = {
                PatternPosition.ANYWHERE: "Anywhere",
                PatternPosition.START: "Start",
                PatternPosition.END: "End"
            }.get(position, position)
            self.detected_table.setItem(row, 2, QTableWidgetItem(position_display))

            # Example (truncate if too long)
            if example:
                example_display = example if len(example) <= 50 else example[:47] + "..."
                example_item = QTableWidgetItem(example_display)
                example_item.setToolTip(f"Full example: {example}")
                example_item.setForeground(QColor(100, 100, 100))
                self.detected_table.setItem(row, 3, example_item)

            # Add button
            add_btn = QPushButton("➕ Add")
            add_btn.clicked.connect(
                lambda _, p=pattern, pos=position: self.add_detected_pattern(p, pos)
            )
            add_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            self.detected_table.setCellWidget(row, 4, add_btn)

        QMessageBox.information(
            self,
            "Patterns Detected",
            f"Found {len(detected)} potential patterns. Review and add the ones you want to use."
        )

    def add_detected_pattern(self, pattern: str, position: str):
        """Add a detected pattern to the main list."""
        if self.pattern_manager.add_pattern(
            pattern,
            position,
            description=f"Auto-detected pattern (found in multiple files)"
        ):
            self.load_patterns_to_table()
            QMessageBox.information(self, "Success", f"Pattern '{pattern}' added")

            # Refresh detected table to remove added pattern
            self.detect_patterns()

    def refresh_statistics(self):
        """Refresh statistics about patterns."""
        if not self.current_files:
            self.stats_display.setPlainText("No files loaded. Add files to see statistics.")
            return

        stats = self.pattern_manager.get_pattern_stats(self.current_files)

        if not stats:
            self.stats_display.setPlainText(
                "No patterns would affect your current files.\n\n"
                "This could mean:\n"
                "- Your files don't contain the configured patterns\n"
                "- All patterns are disabled\n"
                "- Try detecting patterns from your files (Auto-Detect tab)"
            )
            return

        # Format statistics
        text = f"Statistics for {len(self.current_files)} files:\n\n"
        text += "Patterns that would affect your files:\n"
        text += "=" * 60 + "\n\n"

        # Sort by count (descending)
        sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)

        for pattern, count in sorted_stats:
            percentage = (count / len(self.current_files)) * 100
            text += f"• {pattern:<20} → {count:>4} files ({percentage:.1f}%)\n"

        text += "\n" + "=" * 60 + "\n"
        text += f"Total enabled patterns: {len(self.pattern_manager.get_enabled_patterns())}\n"
        text += f"Total patterns in library: {len(self.pattern_manager.patterns)}\n"

        self.stats_display.setPlainText(text)
