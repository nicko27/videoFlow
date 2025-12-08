"""
Smart Filters Widget for Duplicate Finder plugin.

Provides UI for filtering duplicate results with multiple criteria.
"""

from typing import Optional, Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QSlider,
    QSpinBox, QDoubleSpinBox, QLineEdit, QCheckBox, QPushButton,
    QComboBox, QMessageBox, QInputDialog, QFormLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal

from ..managers.filter_manager import FilterManager, FilterCriteria, get_filter_manager
from src.core.logger import Logger

logger = Logger.get_logger(__name__)


class SmartFiltersWidget(QWidget):
    """
    Widget for smart filtering of duplicate results.

    Features:
    - Similarity range slider
    - Size difference filters (absolute and percentage)
    - Duration difference filters (absolute and percentage)
    - Path pattern filters (regex with include/exclude)
    - Preset management (save/load/delete)
    - Enable/disable toggle

    Emits filter_changed signal when criteria changes.
    """

    # Signals
    filter_changed = pyqtSignal(FilterCriteria)  # Emitted when filter changes

    def __init__(self, filter_manager: Optional[FilterManager] = None, parent=None):
        super().__init__(parent)

        self.filter_manager = filter_manager or get_filter_manager()
        self.criteria = FilterCriteria()

        self._setup_ui()
        self._load_current_filter()

        logger.info("SmartFiltersWidget initialized")

    def _setup_ui(self):
        """Create the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # ===== Header with Enable/Preset =====
        header_layout = QHBoxLayout()

        self.enable_check = QCheckBox("Enable Filters")
        self.enable_check.setChecked(True)
        self.enable_check.stateChanged.connect(self._on_filter_changed)
        header_layout.addWidget(self.enable_check)

        header_layout.addStretch()

        # Preset selector
        preset_label = QLabel("Preset:")
        header_layout.addWidget(preset_label)

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(200)
        self.preset_combo.addItem("-- Custom --")
        self._load_presets()
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        header_layout.addWidget(self.preset_combo)

        self.save_preset_btn = QPushButton("💾 Save")
        self.save_preset_btn.setToolTip("Save current filter as preset")
        self.save_preset_btn.clicked.connect(self._save_preset)
        header_layout.addWidget(self.save_preset_btn)

        self.delete_preset_btn = QPushButton("🗑 Delete")
        self.delete_preset_btn.setToolTip("Delete selected preset")
        self.delete_preset_btn.clicked.connect(self._delete_preset)
        header_layout.addWidget(self.delete_preset_btn)

        layout.addLayout(header_layout)

        # ===== Similarity Filter =====
        similarity_group = self._create_similarity_group()
        layout.addWidget(similarity_group)

        # ===== Size Difference Filter =====
        size_group = self._create_size_group()
        layout.addWidget(size_group)

        # ===== Duration Difference Filter =====
        duration_group = self._create_duration_group()
        layout.addWidget(duration_group)

        # ===== Path Pattern Filter =====
        path_group = self._create_path_group()
        layout.addWidget(path_group)

        # ===== Actions =====
        actions_layout = QHBoxLayout()

        self.apply_btn = QPushButton("✓ Apply Filter")
        self.apply_btn.clicked.connect(self._apply_filter)
        self.apply_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        actions_layout.addWidget(self.apply_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._reset_filter)
        actions_layout.addWidget(self.reset_btn)

        actions_layout.addStretch()

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-size: 10px;")
        actions_layout.addWidget(self.status_label)

        layout.addLayout(actions_layout)

        # Add stretch at bottom
        layout.addStretch()

    def _create_similarity_group(self) -> QGroupBox:
        """Create similarity filter group."""
        group = QGroupBox("Similarity Range")
        layout = QVBoxLayout(group)

        # Range slider (we'll simulate with two sliders)
        range_layout = QHBoxLayout()

        # Min similarity
        min_layout = QVBoxLayout()
        min_label = QLabel("Min:")
        self.min_sim_slider = QSlider(Qt.Orientation.Horizontal)
        self.min_sim_slider.setRange(0, 100)
        self.min_sim_slider.setValue(0)
        self.min_sim_slider.valueChanged.connect(self._on_similarity_changed)

        self.min_sim_spin = QSpinBox()
        self.min_sim_spin.setRange(0, 100)
        self.min_sim_spin.setSuffix("%")
        self.min_sim_spin.setValue(0)
        self.min_sim_spin.valueChanged.connect(self.min_sim_slider.setValue)
        self.min_sim_slider.valueChanged.connect(self.min_sim_spin.setValue)

        min_layout.addWidget(min_label)
        min_layout.addWidget(self.min_sim_slider)
        min_layout.addWidget(self.min_sim_spin)

        # Max similarity
        max_layout = QVBoxLayout()
        max_label = QLabel("Max:")
        self.max_sim_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_sim_slider.setRange(0, 100)
        self.max_sim_slider.setValue(100)
        self.max_sim_slider.valueChanged.connect(self._on_similarity_changed)

        self.max_sim_spin = QSpinBox()
        self.max_sim_spin.setRange(0, 100)
        self.max_sim_spin.setSuffix("%")
        self.max_sim_spin.setValue(100)
        self.max_sim_spin.valueChanged.connect(self.max_sim_slider.setValue)
        self.max_sim_slider.valueChanged.connect(self.max_sim_spin.setValue)

        max_layout.addWidget(max_label)
        max_layout.addWidget(self.max_sim_slider)
        max_layout.addWidget(self.max_sim_spin)

        range_layout.addLayout(min_layout)
        range_layout.addLayout(max_layout)

        layout.addLayout(range_layout)

        return group

    def _create_size_group(self) -> QGroupBox:
        """Create size difference filter group."""
        group = QGroupBox("Size Difference")
        form = QFormLayout(group)

        # Absolute difference
        abs_layout = QHBoxLayout()
        self.min_size_check = QCheckBox("Min:")
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setRange(0, 1000000000)  # 1GB
        self.min_size_spin.setSuffix(" bytes")
        self.min_size_spin.setEnabled(False)
        self.min_size_check.stateChanged.connect(lambda: self.min_size_spin.setEnabled(self.min_size_check.isChecked()))
        self.min_size_check.stateChanged.connect(self._on_filter_changed)
        self.min_size_spin.valueChanged.connect(self._on_filter_changed)
        abs_layout.addWidget(self.min_size_check)
        abs_layout.addWidget(self.min_size_spin)

        self.max_size_check = QCheckBox("Max:")
        self.max_size_spin = QSpinBox()
        self.max_size_spin.setRange(0, 1000000000)
        self.max_size_spin.setSuffix(" bytes")
        self.max_size_spin.setEnabled(False)
        self.max_size_check.stateChanged.connect(lambda: self.max_size_spin.setEnabled(self.max_size_check.isChecked()))
        self.max_size_check.stateChanged.connect(self._on_filter_changed)
        self.max_size_spin.valueChanged.connect(self._on_filter_changed)
        abs_layout.addWidget(self.max_size_check)
        abs_layout.addWidget(self.max_size_spin)

        form.addRow("Absolute:", abs_layout)

        # Percentage difference
        pct_layout = QHBoxLayout()
        self.size_pct_check = QCheckBox("Max %:")
        self.size_pct_spin = QDoubleSpinBox()
        self.size_pct_spin.setRange(0, 100)
        self.size_pct_spin.setSuffix("%")
        self.size_pct_spin.setDecimals(1)
        self.size_pct_spin.setEnabled(False)
        self.size_pct_check.stateChanged.connect(lambda: self.size_pct_spin.setEnabled(self.size_pct_check.isChecked()))
        self.size_pct_check.stateChanged.connect(self._on_filter_changed)
        self.size_pct_spin.valueChanged.connect(self._on_filter_changed)
        pct_layout.addWidget(self.size_pct_check)
        pct_layout.addWidget(self.size_pct_spin)
        pct_layout.addStretch()

        form.addRow("Percentage:", pct_layout)

        return group

    def _create_duration_group(self) -> QGroupBox:
        """Create duration difference filter group."""
        group = QGroupBox("Duration Difference")
        form = QFormLayout(group)

        # Absolute difference
        abs_layout = QHBoxLayout()
        self.min_dur_check = QCheckBox("Min:")
        self.min_dur_spin = QDoubleSpinBox()
        self.min_dur_spin.setRange(0, 86400)  # 24 hours
        self.min_dur_spin.setSuffix(" sec")
        self.min_dur_spin.setDecimals(1)
        self.min_dur_spin.setEnabled(False)
        self.min_dur_check.stateChanged.connect(lambda: self.min_dur_spin.setEnabled(self.min_dur_check.isChecked()))
        self.min_dur_check.stateChanged.connect(self._on_filter_changed)
        self.min_dur_spin.valueChanged.connect(self._on_filter_changed)
        abs_layout.addWidget(self.min_dur_check)
        abs_layout.addWidget(self.min_dur_spin)

        self.max_dur_check = QCheckBox("Max:")
        self.max_dur_spin = QDoubleSpinBox()
        self.max_dur_spin.setRange(0, 86400)
        self.max_dur_spin.setSuffix(" sec")
        self.max_dur_spin.setDecimals(1)
        self.max_dur_spin.setEnabled(False)
        self.max_dur_check.stateChanged.connect(lambda: self.max_dur_spin.setEnabled(self.max_dur_check.isChecked()))
        self.max_dur_check.stateChanged.connect(self._on_filter_changed)
        self.max_dur_spin.valueChanged.connect(self._on_filter_changed)
        abs_layout.addWidget(self.max_dur_check)
        abs_layout.addWidget(self.max_dur_spin)

        form.addRow("Absolute:", abs_layout)

        # Percentage difference
        pct_layout = QHBoxLayout()
        self.dur_pct_check = QCheckBox("Max %:")
        self.dur_pct_spin = QDoubleSpinBox()
        self.dur_pct_spin.setRange(0, 100)
        self.dur_pct_spin.setSuffix("%")
        self.dur_pct_spin.setDecimals(1)
        self.dur_pct_spin.setEnabled(False)
        self.dur_pct_check.stateChanged.connect(lambda: self.dur_pct_spin.setEnabled(self.dur_pct_check.isChecked()))
        self.dur_pct_check.stateChanged.connect(self._on_filter_changed)
        self.dur_pct_spin.valueChanged.connect(self._on_filter_changed)
        pct_layout.addWidget(self.dur_pct_check)
        pct_layout.addWidget(self.dur_pct_spin)
        pct_layout.addStretch()

        form.addRow("Percentage:", pct_layout)

        return group

    def _create_path_group(self) -> QGroupBox:
        """Create path pattern filter group."""
        group = QGroupBox("Path Patterns (Regex)")
        form = QFormLayout(group)

        # Include pattern
        self.include_pattern = QLineEdit()
        self.include_pattern.setPlaceholderText("e.g., .*video.*\\.mp4")
        self.include_pattern.textChanged.connect(self._on_filter_changed)
        form.addRow("Include:", self.include_pattern)

        # Exclude pattern
        self.exclude_pattern = QLineEdit()
        self.exclude_pattern.setPlaceholderText("e.g., .*/backup/.*")
        self.exclude_pattern.textChanged.connect(self._on_filter_changed)
        form.addRow("Exclude:", self.exclude_pattern)

        # Case sensitive
        self.case_sensitive = QCheckBox("Case sensitive")
        self.case_sensitive.stateChanged.connect(self._on_filter_changed)
        form.addRow("", self.case_sensitive)

        return group

    def _on_similarity_changed(self):
        """Handle similarity slider changes."""
        # Ensure min <= max
        if self.min_sim_slider.value() > self.max_sim_slider.value():
            self.max_sim_slider.setValue(self.min_sim_slider.value())

        self._on_filter_changed()

    def _on_filter_changed(self):
        """Handle any filter change - update status."""
        self.status_label.setText("Filter modified (click Apply)")
        self.status_label.setStyleSheet("color: #FF9800; font-size: 10px;")
        self.preset_combo.setCurrentText("-- Custom --")

    def _apply_filter(self):
        """Apply current filter criteria."""
        # Build criteria from UI
        self.criteria = FilterCriteria(
            enabled=self.enable_check.isChecked(),
            min_similarity=self.min_sim_slider.value(),
            max_similarity=self.max_sim_slider.value(),
            min_size_diff=self.min_size_spin.value() if self.min_size_check.isChecked() else None,
            max_size_diff=self.max_size_spin.value() if self.max_size_check.isChecked() else None,
            size_diff_percent=self.size_pct_spin.value() if self.size_pct_check.isChecked() else None,
            min_duration_diff=self.min_dur_spin.value() if self.min_dur_check.isChecked() else None,
            max_duration_diff=self.max_dur_spin.value() if self.max_dur_check.isChecked() else None,
            duration_diff_percent=self.dur_pct_spin.value() if self.dur_pct_check.isChecked() else None,
            path_pattern=self.include_pattern.text() or None,
            exclude_pattern=self.exclude_pattern.text() or None,
            case_sensitive=self.case_sensitive.isChecked()
        )

        self.filter_manager.set_current_filter(self.criteria)
        self.filter_changed.emit(self.criteria)

        self.status_label.setText("Filter applied ✓")
        self.status_label.setStyleSheet("color: #4CAF50; font-size: 10px;")

        logger.info(f"Filter applied: {self._describe_filter()}")

    def _reset_filter(self):
        """Reset filter to default."""
        self.criteria = FilterCriteria()
        self._load_filter_to_ui(self.criteria)
        self.filter_manager.reset_filter()

        self.status_label.setText("Filter reset")
        self.status_label.setStyleSheet("color: #666; font-size: 10px;")

        logger.info("Filter reset to default")

    def _save_preset(self):
        """Save current filter as preset."""
        name, ok = QInputDialog.getText(
            self, "Save Preset",
            "Enter preset name:",
            QLineEdit.EchoMode.Normal
        )

        if ok and name:
            # Build current criteria
            self._apply_filter()  # Ensure criteria is up-to-date
            self.filter_manager.save_preset(name, self.criteria)
            self._load_presets()
            self.preset_combo.setCurrentText(name)

            QMessageBox.information(self, "Success", f"Preset '{name}' saved")

    def _delete_preset(self):
        """Delete selected preset."""
        preset_name = self.preset_combo.currentText()
        if preset_name == "-- Custom --":
            QMessageBox.warning(self, "Error", "Cannot delete custom filter")
            return

        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Delete preset '{preset_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.filter_manager.delete_preset(preset_name):
                self._load_presets()
                self.preset_combo.setCurrentText("-- Custom --")
                QMessageBox.information(self, "Success", f"Preset '{preset_name}' deleted")

    def _on_preset_selected(self, preset_name: str):
        """Handle preset selection."""
        if preset_name == "-- Custom --":
            return

        criteria = self.filter_manager.load_preset(preset_name)
        if criteria:
            self._load_filter_to_ui(criteria)
            self.status_label.setText(f"Loaded preset: {preset_name}")
            self.status_label.setStyleSheet("color: #2196F3; font-size: 10px;")

    def _load_presets(self):
        """Load preset names into combo box."""
        current = self.preset_combo.currentText()
        self.preset_combo.clear()
        self.preset_combo.addItem("-- Custom --")

        for name in self.filter_manager.get_preset_names():
            self.preset_combo.addItem(name)

        # Restore selection if still exists
        idx = self.preset_combo.findText(current)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)

    def _load_current_filter(self):
        """Load current filter from manager."""
        self._load_filter_to_ui(self.filter_manager.current_filter)

    def _load_filter_to_ui(self, criteria: FilterCriteria):
        """Load filter criteria into UI widgets."""
        # Block signals during loading
        widgets = [
            self.enable_check, self.min_sim_slider, self.max_sim_slider,
            self.min_size_check, self.min_size_spin, self.max_size_check, self.max_size_spin,
            self.size_pct_check, self.size_pct_spin, self.min_dur_check, self.min_dur_spin,
            self.max_dur_check, self.max_dur_spin, self.dur_pct_check, self.dur_pct_spin,
            self.include_pattern, self.exclude_pattern, self.case_sensitive
        ]

        for widget in widgets:
            widget.blockSignals(True)

        # Load values
        self.enable_check.setChecked(criteria.enabled)
        self.min_sim_slider.setValue(int(criteria.min_similarity))
        self.max_sim_slider.setValue(int(criteria.max_similarity))

        self.min_size_check.setChecked(criteria.min_size_diff is not None)
        if criteria.min_size_diff is not None:
            self.min_size_spin.setValue(criteria.min_size_diff)
            self.min_size_spin.setEnabled(True)

        self.max_size_check.setChecked(criteria.max_size_diff is not None)
        if criteria.max_size_diff is not None:
            self.max_size_spin.setValue(criteria.max_size_diff)
            self.max_size_spin.setEnabled(True)

        self.size_pct_check.setChecked(criteria.size_diff_percent is not None)
        if criteria.size_diff_percent is not None:
            self.size_pct_spin.setValue(criteria.size_diff_percent)
            self.size_pct_spin.setEnabled(True)

        self.min_dur_check.setChecked(criteria.min_duration_diff is not None)
        if criteria.min_duration_diff is not None:
            self.min_dur_spin.setValue(criteria.min_duration_diff)
            self.min_dur_spin.setEnabled(True)

        self.max_dur_check.setChecked(criteria.max_duration_diff is not None)
        if criteria.max_duration_diff is not None:
            self.max_dur_spin.setValue(criteria.max_duration_diff)
            self.max_dur_spin.setEnabled(True)

        self.dur_pct_check.setChecked(criteria.duration_diff_percent is not None)
        if criteria.duration_diff_percent is not None:
            self.dur_pct_spin.setValue(criteria.duration_diff_percent)
            self.dur_pct_spin.setEnabled(True)

        self.include_pattern.setText(criteria.path_pattern or "")
        self.exclude_pattern.setText(criteria.exclude_pattern or "")
        self.case_sensitive.setChecked(criteria.case_sensitive)

        # Unblock signals
        for widget in widgets:
            widget.blockSignals(False)

        self.criteria = criteria
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: #666; font-size: 10px;")

    def _describe_filter(self) -> str:
        """Generate human-readable filter description."""
        parts = []

        if not self.criteria.enabled:
            return "Disabled"

        parts.append(f"Similarity: {self.criteria.min_similarity:.0f}%-{self.criteria.max_similarity:.0f}%")

        if self.criteria.min_size_diff or self.criteria.max_size_diff:
            size_str = f"Size: {self.criteria.min_size_diff or 0}-{self.criteria.max_size_diff or '∞'} bytes"
            parts.append(size_str)

        if self.criteria.size_diff_percent:
            parts.append(f"Size %: <{self.criteria.size_diff_percent:.1f}%")

        if self.criteria.min_duration_diff or self.criteria.max_duration_diff:
            dur_str = f"Duration: {self.criteria.min_duration_diff or 0}-{self.criteria.max_duration_diff or '∞'}s"
            parts.append(dur_str)

        if self.criteria.duration_diff_percent:
            parts.append(f"Duration %: <{self.criteria.duration_diff_percent:.1f}%")

        if self.criteria.path_pattern:
            parts.append(f"Include: {self.criteria.path_pattern}")

        if self.criteria.exclude_pattern:
            parts.append(f"Exclude: {self.criteria.exclude_pattern}")

        return ", ".join(parts)

    def get_current_criteria(self) -> FilterCriteria:
        """Get current filter criteria."""
        return self.criteria
