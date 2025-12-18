"""
Stage Editor Dialog for Staged Pipelines.

Allows users to configure multi-stage pipelines with:
- Stage 1 (Localization): Fast algorithms to find offset
- Stage 2+ (Verification): Discriminant algorithms in windowed region
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox, QMessageBox,
    QLineEdit, QFrame, QWidget
)
from PyQt6.QtCore import Qt
from typing import Dict, List, Any, Optional
from copy import deepcopy

from src.plugins.duplicate_finder.verification_pipeline import VerificationPipeline
from src.plugins.duplicate_finder.integration import get_all_algorithms_dict
from src.core.i18n import I18n


class StageEditorDialog(QDialog):
    """
    Dialog for editing a single stage in a staged pipeline.

    A stage contains:
    - Name and type (localization or verification)
    - List of algorithms with weights and parameters
    - Window configuration (for verification stages)
    """

    def __init__(self, stage_data: Optional[Dict[str, Any]] = None, parent=None):
        """
        Initialize stage editor.

        Args:
            stage_data: Existing stage configuration to edit, or None for new stage
            parent: Parent widget
        """
        super().__init__(parent)
        self.stage_data = deepcopy(stage_data) if stage_data else {}
        self.algorithms = []  # List of algorithm configs in this stage

        self.setWindowTitle("Éditeur de Stage")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Stage name and type
        header_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Ex: fast_localization, discriminant_verification")
        header_layout.addRow("Nom du stage:", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["localization", "verification"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        header_layout.addRow("Type:", self.type_combo)

        layout.addLayout(header_layout)

        # Window configuration (for verification stages only)
        self.window_group = QGroupBox("Configuration de la fenêtre temporelle")
        window_layout = QFormLayout()

        self.use_window_combo = QComboBox()
        self.use_window_combo.addItems(["<Aucun>"])  # Will be populated with stage names
        self.use_window_combo.setToolTip("Stage dont utiliser l'offset pour créer la fenêtre temporelle")
        window_layout.addRow("Utiliser fenêtre du stage:", self.use_window_combo)

        self.margin_before_spin = QSpinBox()
        self.margin_before_spin.setRange(0, 300)
        self.margin_before_spin.setValue(30)
        self.margin_before_spin.setSuffix(" s")
        self.margin_before_spin.setToolTip("Marge avant l'offset détecté")
        window_layout.addRow("Marge avant:", self.margin_before_spin)

        self.margin_after_spin = QSpinBox()
        self.margin_after_spin.setRange(0, 300)
        self.margin_after_spin.setValue(30)
        self.margin_after_spin.setSuffix(" s")
        self.margin_after_spin.setToolTip("Marge après l'offset + durée vidéo courte")
        window_layout.addRow("Marge après:", self.margin_after_spin)

        self.min_window_spin = QSpinBox()
        self.min_window_spin.setRange(1, 600)
        self.min_window_spin.setValue(10)
        self.min_window_spin.setSuffix(" s")
        self.min_window_spin.setToolTip("Taille minimale de la fenêtre")
        window_layout.addRow("Fenêtre min:", self.min_window_spin)

        self.max_window_spin = QSpinBox()
        self.max_window_spin.setRange(10, 3600)
        self.max_window_spin.setValue(120)
        self.max_window_spin.setSuffix(" s")
        self.max_window_spin.setToolTip("Taille maximale de la fenêtre")
        window_layout.addRow("Fenêtre max:", self.max_window_spin)

        self.fallback_checkbox = QCheckBox("Scan complet si offset non trouvé")
        self.fallback_checkbox.setChecked(True)
        window_layout.addRow(self.fallback_checkbox)

        self.window_group.setLayout(window_layout)
        layout.addWidget(self.window_group)

        # Algorithms list
        algo_label = QLabel("Algorithmes du stage:")
        algo_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(algo_label)

        self.algo_list = QListWidget()
        layout.addWidget(self.algo_list, stretch=1)

        # Algorithm buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Ajouter")
        add_btn.clicked.connect(self._on_add_algorithm)
        edit_btn = QPushButton("✏️ Modifier")
        edit_btn.clicked.connect(self._on_edit_algorithm)
        remove_btn = QPushButton("🗑️ Supprimer")
        remove_btn.clicked.connect(self._on_remove_algorithm)
        up_btn = QPushButton("⬆️")
        up_btn.clicked.connect(lambda: self._move_algorithm(-1))
        down_btn = QPushButton("⬇️")
        down_btn.clicked.connect(lambda: self._move_algorithm(1))

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addWidget(up_btn)
        btn_layout.addWidget(down_btn)
        layout.addLayout(btn_layout)

        # Dialog buttons
        dialog_btns = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        dialog_btns.addStretch()
        dialog_btns.addWidget(ok_btn)
        dialog_btns.addWidget(cancel_btn)
        layout.addLayout(dialog_btns)

    def _load_data(self):
        """Load existing stage data into UI."""
        if not self.stage_data:
            return

        # Basic info
        self.name_edit.setText(self.stage_data.get('name', ''))

        stage_type = self.stage_data.get('type', 'localization')
        index = self.type_combo.findText(stage_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)

        # Window config
        window_config = self.stage_data.get('window_config', {})
        self.margin_before_spin.setValue(window_config.get('margin_before', 30))
        self.margin_after_spin.setValue(window_config.get('margin_after', 30))
        self.min_window_spin.setValue(window_config.get('min_window', 10))
        self.max_window_spin.setValue(window_config.get('max_window', 120))
        self.fallback_checkbox.setChecked(window_config.get('fallback_full_scan', True))

        # Use window from stage
        use_window_from = self.stage_data.get('use_window_from_stage')
        if use_window_from:
            index = self.use_window_combo.findText(use_window_from)
            if index >= 0:
                self.use_window_combo.setCurrentIndex(index)

        # Algorithms
        self.algorithms = self.stage_data.get('algorithms', [])
        self._refresh_algorithm_list()

    def _on_type_changed(self, stage_type: str):
        """Handle stage type change."""
        # Show/hide window configuration based on type
        is_verification = (stage_type == 'verification')
        self.window_group.setVisible(is_verification)

    def _on_add_algorithm(self):
        """Add new algorithm to stage."""
        # Import here to avoid circular dependency
        from src.plugins.duplicate_finder.ui.method_editor_dialog import MethodEditorDialog

        dialog = MethodEditorDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            method = dialog.get_method()
            self.algorithms.append(method)
            self._refresh_algorithm_list()

    def _on_edit_algorithm(self):
        """Edit selected algorithm."""
        current = self.algo_list.currentItem()
        if not current:
            return

        from src.plugins.duplicate_finder.ui.method_editor_dialog import MethodEditorDialog

        idx = self.algo_list.currentRow()
        dialog = MethodEditorDialog(self.algorithms[idx], parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.algorithms[idx] = dialog.get_method()
            self._refresh_algorithm_list()

    def _on_remove_algorithm(self):
        """Remove selected algorithm."""
        idx = self.algo_list.currentRow()
        if idx >= 0:
            del self.algorithms[idx]
            self._refresh_algorithm_list()

    def _move_algorithm(self, delta: int):
        """Move algorithm up or down in list."""
        idx = self.algo_list.currentRow()
        if idx < 0:
            return

        new_idx = idx + delta
        if not (0 <= new_idx < len(self.algorithms)):
            return

        self.algorithms[idx], self.algorithms[new_idx] = \
            self.algorithms[new_idx], self.algorithms[idx]
        self._refresh_algorithm_list()
        self.algo_list.setCurrentRow(new_idx)

    def _refresh_algorithm_list(self):
        """Refresh the algorithm list display."""
        self.algo_list.clear()

        available_methods = get_all_algorithms_dict()
        for algo in self.algorithms:
            name = algo.get('name', 'unknown')
            if name.startswith('df_'):
                name = name[3:]

            display_name = available_methods.get(
                algo.get('name', ''), {}
            ).get('display_name', name)

            weight = algo.get('weight', 1.0)
            enabled = algo.get('enabled', True)
            threshold = algo.get('parameters', {}).get('threshold', 70.0)

            item_text = f"{display_name} (w={weight:.2f}, t={threshold:.0f}%, {'ON' if enabled else 'OFF'})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, algo)
            self.algo_list.addItem(item)

    def set_available_stages(self, stage_names: List[str]):
        """
        Set the list of available stages for windowing reference.

        Args:
            stage_names: List of stage names that can be referenced
        """
        current = self.use_window_combo.currentText()
        self.use_window_combo.clear()
        self.use_window_combo.addItem("<Aucun>")
        self.use_window_combo.addItems(stage_names)

        # Restore selection if possible
        index = self.use_window_combo.findText(current)
        if index >= 0:
            self.use_window_combo.setCurrentIndex(index)

    def get_stage(self) -> Dict[str, Any]:
        """
        Get the configured stage data.

        Returns:
            Stage configuration dictionary
        """
        stage = {
            'name': self.name_edit.text().strip(),
            'type': self.type_combo.currentText(),
            'algorithms': deepcopy(self.algorithms)
        }

        # Add window config for verification stages
        if stage['type'] == 'verification':
            use_window_from = self.use_window_combo.currentText()
            if use_window_from and use_window_from != "<Aucun>":
                stage['use_window_from_stage'] = use_window_from

            stage['window_config'] = {
                'margin_before': self.margin_before_spin.value(),
                'margin_after': self.margin_after_spin.value(),
                'min_window': self.min_window_spin.value(),
                'max_window': self.max_window_spin.value(),
                'fallback_full_scan': self.fallback_checkbox.isChecked()
            }

        return stage

    def accept(self):
        """Validate and accept dialog."""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Le nom du stage est requis")
            return

        if not self.algorithms:
            QMessageBox.warning(self, "Validation", "Au moins un algorithme est requis")
            return

        super().accept()
