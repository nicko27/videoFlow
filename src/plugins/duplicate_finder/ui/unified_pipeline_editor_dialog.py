"""
Éditeur unifié de pipelines (version guidée).

Objectifs :
- Interface plus pédagogique (fiches méthodes, conseils, paramètres typés).
- Un seul flux de création/édition pour tous les boutons "Nouveau Pipeline".
- S'appuie sur PipelineManager.save_pipeline / update_pipeline avec le schéma actuel.
"""

from typing import Dict, List, Optional
from copy import deepcopy

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QCheckBox,
    QDoubleSpinBox,
    QWidget,
    QFormLayout,
    QSplitter,
    QFrame,
    QSpinBox,
)
from PyQt6.QtCore import Qt

from src.core.logger import Logger
from ..verification import VerificationPipeline
from ..orchestration.pipeline_manager import PipelineManager
from ..infrastructure.i18n import I18n

logger = Logger.get_logger("DuplicateFinder.UnifiedPipelineEditor")


def _auto_cast(value: str):
    """Tente de convertir une chaîne en int ou float, sinon retourne la chaîne."""
    try:
        if value.strip() == "":
            return value
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


class MethodEditorDialog(QDialog):
    """Dialogue d'édition d'une méthode avec explications et paramètres typés."""

    # Courte aide par paramètre (description + conseils)
    PARAM_HELP = {
        "color_histogram": {
            "threshold": "param_help.color_histogram.threshold",
            "bins": "param_help.color_histogram.bins"
        },
        "motion_analysis": {
            "correlation_threshold": "param_help.motion_analysis.correlation_threshold",
            "sample_interval": "param_help.motion_analysis.sample_interval",
            "min_variance": "param_help.motion_analysis.min_variance"
        },
        "dct_coefficients": {
            "threshold": "param_help.dct.threshold",
            "num_coeffs": "param_help.dct.num_coeffs",
            "block_size": "param_help.dct.block_size",
            "sample_interval": "param_help.dct.sample_interval",
            "num_samples": "param_help.dct.num_samples"
        },
        "ssim": {
            "threshold": "param_help.ssim.threshold",
            "window_size": "param_help.ssim.window_size",
            "sample_interval": "param_help.ssim.sample_interval",
            "num_samples": "param_help.ssim.num_samples",
            "resize": "param_help.ssim.resize"
        },
        "edge_pattern": {
            "threshold": "param_help.edge.threshold",
            "canny_low": "param_help.edge.canny_low",
            "canny_high": "param_help.edge.canny_high",
            "grid_size": "param_help.edge.grid_size"
        },
        "feature_matching": {
            "threshold": "param_help.feature.threshold",
            "detector": "param_help.feature.detector",
            "max_features": "param_help.feature.max_features",
            "min_matches": "param_help.feature.min_matches",
            "ratio_test": "param_help.feature.ratio_test"
        },
        "optical_flow": {
            "threshold": "param_help.optical_flow.threshold",
            "max_frames": "param_help.optical_flow.max_frames",
            "frame_step": "param_help.optical_flow.frame_step",
            "min_variance": "param_help.optical_flow.min_variance"
        },
        "frame_hash": {
            "hash_size": "param_help.framehash.hash_size",
            "threshold": "param_help.framehash.threshold",
            "sample_rate": "param_help.framehash.sample_rate",
            "max_samples": "param_help.framehash.max_samples"
        },
        "strategy3": {
            "scene_threshold": "param_help.strategy3.scene_threshold",
            "dct_threshold": "param_help.strategy3.dct_threshold",
            "sequence_threshold": "param_help.strategy3.sequence_threshold",
            "num_samples": "param_help.strategy3.num_samples",
            "warmup_seconds": "param_help.strategy3.warmup_seconds",
            "max_workers": "param_help.strategy3.max_workers"
        }
    }

    def __init__(self, method: Optional[Dict] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(I18n.t("method_editor_title"))
        self.resize(620, 520)
        self._method = deepcopy(method) if method else None
        self.param_fields: Dict[str, QLineEdit] = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # En-tête
        header = QLabel(I18n.t("method_editor_header"))
        header.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(header)

        form = QFormLayout()

        self.name_combo = QComboBox()
        for name, meta in VerificationPipeline.AVAILABLE_METHODS.items():
            self.name_combo.addItem(meta.get("display_name", name), userData=name)
        form.addRow(I18n.t("field_method"), self.name_combo)

        self.enabled_chk = QCheckBox(I18n.t("enabled"))
        self.enabled_chk.setChecked(True)
        form.addRow("", self.enabled_chk)

        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0.0, 10.0)
        self.weight_spin.setSingleStep(0.1)
        self.weight_spin.setValue(1.0)
        form.addRow(I18n.t("weight"), self.weight_spin)

        layout.addLayout(form)

        # Fiche d'explication
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("background:#f5f5f5; border-radius:6px; padding:8px;")
        layout.addWidget(self.info_label)

        # Paramètres (champs typés)
        params_container = QWidget()
        self.params_form = QFormLayout(params_container)
        self.params_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(params_container)

        # Boutons
        btns = QHBoxLayout()
        btns.addStretch()
        save_btn = QPushButton(I18n.t("save"))
        save_btn.clicked.connect(self._on_accept)
        cancel_btn = QPushButton(I18n.t("cancel"))
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

        # Charger les valeurs si fournies
        if self._method:
            self.name_combo.setCurrentIndex(self.name_combo.findData(self._method.get("name", "")))
            self.enabled_chk.setChecked(self._method.get("enabled", True))
            self.weight_spin.setValue(float(self._method.get("weight", 1.0)))
        self.name_combo.currentIndexChanged.connect(self._on_method_changed)
        self._rebuild_params()

    def _rebuild_params(self):
        """Reconstruit le formulaire de paramètres pour la méthode sélectionnée."""
        # Clear previous
        while self.params_form.count():
            item = self.params_form.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()
        self.param_fields.clear()

        method_key = self.name_combo.currentData()
        meta = VerificationPipeline.AVAILABLE_METHODS.get(method_key, {})
        default_params = deepcopy(meta.get("default_params", {}))
        current_params = deepcopy(self._method.get("parameters", {})) if self._method else {}

        # Metadonnées pour la fiche
        desc = meta.get("description", "")
        long_desc = meta.get("detailed_explanation", "")
        use_case = meta.get("use_case", "")
        speed = meta.get("speed", "")
        self.info_label.setText(
            f"<b>{meta.get('display_name', method_key)}</b><br>"
            f"{desc}<br><br>"
            f"<i>{long_desc}</i><br><br>"
            f"{I18n.t('use_case')}: {use_case} | {I18n.t('speed')}: {speed}"
        )

        # Construire un champ par paramètre
        params = default_params.keys()
        for key in params:
            field = QLineEdit()
            value = current_params.get(key, default_params.get(key, ""))
            field.setText(str(value))
            field.setPlaceholderText(f"{default_params.get(key, '')}")
            help_key = self.PARAM_HELP.get(method_key, {}).get(key, "")
            help_text = I18n.t(help_key) if help_key else ""
            default_txt = f" (défaut: {default_params.get(key, '')})"
            if help_text:
                label = QLabel(f"{key} — {help_text}{default_txt}")
                label.setStyleSheet("color:#555;")
            else:
                label = QLabel(f"{key}{default_txt}")
            field.setToolTip((help_text + default_txt) if help_text else f"{key}{default_txt}")
            self.params_form.addRow(label, field)
            self.param_fields[key] = field

    def _on_method_changed(self, _idx: int):
        """Recharge la fiche et les paramètres par défaut pour la méthode sélectionnée."""
        # Réinitialiser les paramètres aux defaults de la nouvelle méthode
        self._method = {
            "name": self.name_combo.currentData(),
            "enabled": True,
            "weight": 1.0,
            "parameters": {}
        }
        self.weight_spin.setValue(1.0)
        self.enabled_chk.setChecked(True)
        self._rebuild_params()

    def _on_accept(self):
        """Valide et renvoie la méthode."""
        parameters = {}
        for key, field in self.param_fields.items():
            parameters[key] = _auto_cast(field.text())

        self._method = {
            "name": self.name_combo.currentData(),
            "enabled": self.enabled_chk.isChecked(),
            "weight": float(self.weight_spin.value()),
            "parameters": parameters,
        }
        self.accept()

    def get_method(self) -> Dict:
        return self._method or {}


class UnifiedPipelineEditorDialog(QDialog):
    """Dialogue principal unifié de création/édition de pipeline."""

    def __init__(
        self,
        pipeline_manager: PipelineManager,
        db_manager,
        pipeline_data: Optional[Dict] = None,
        is_copy: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.pipeline_manager = pipeline_manager
        self.db_manager = db_manager
        self.pipeline_data = pipeline_data or {}
        self.is_copy = is_copy
        self.is_new = pipeline_data is None or is_copy
        self.methods: List[Dict] = []

        title = I18n.t("new_pipeline_title") if self.is_new else f"{I18n.t('edit')} {self.pipeline_data.get('name', '')}"
        self.setWindowTitle(f"🔧 {title}")
        self.resize(960, 680)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header
        header = QLabel(I18n.t("pipeline_editor_header"))
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        sub = QLabel(I18n.t("pipeline_editor_subtitle"))
        sub.setStyleSheet("color: #666;")
        layout.addWidget(sub)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Colonne gauche : infos générales + presets + liste pipeline
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(0, 0, 0, 0)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["filtering", "weighting", "hybrid"])

        self.global_threshold_spin = QDoubleSpinBox()
        self.global_threshold_spin.setRange(50.0, 99.0)
        self.global_threshold_spin.setSingleStep(1.0)
        self.global_threshold_spin.setValue(80.0)
        self.global_threshold_spin.setSuffix(" %")
        self.global_threshold_spin.setToolTip(I18n.t("global_threshold_help"))

        self.preset_combo = QComboBox()
        self.preset_combo.addItem(I18n.t("preset_none"), None)
        for pid, cfg in PipelineManager.DEFAULT_PROTOCOLS.items():
            self.preset_combo.addItem(cfg["name"], pid)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)

        form.addRow(I18n.t("name"), self.name_edit)
        form.addRow(I18n.t("description"), self.desc_edit)
        form.addRow(I18n.t("mode"), self.mode_combo)
        form.addRow(I18n.t("global_threshold"), self.global_threshold_spin)
        form.addRow(I18n.t("preset"), self.preset_combo)
        left_layout.addLayout(form)

        # Confirmation visuelle (pHash)
        confirm_group = QFrame()
        confirm_group.setFrameShape(QFrame.Shape.StyledPanel)
        confirm_group.setStyleSheet("background:#f8f8f8; border:1px solid #e0e0e0; border-radius:6px;")
        confirm_layout = QFormLayout(confirm_group)
        self.confirm_enabled = QCheckBox(I18n.t("confirm_enable_label"))
        confirm_layout.addRow(self.confirm_enabled)

        self.confirm_phash_threshold = QSpinBox()
        self.confirm_phash_threshold.setRange(1, 64)
        self.confirm_phash_threshold.setValue(10)
        confirm_layout.addRow(I18n.t("confirm_phash_threshold"), self.confirm_phash_threshold)

        self.confirm_frame_rate = QDoubleSpinBox()
        self.confirm_frame_rate.setRange(0.0, 1.0)
        self.confirm_frame_rate.setSingleStep(0.05)
        self.confirm_frame_rate.setValue(0.8)
        confirm_layout.addRow(I18n.t("confirm_frame_rate"), self.confirm_frame_rate)

        self.confirm_n_frames = QSpinBox()
        self.confirm_n_frames.setRange(2, 50)
        self.confirm_n_frames.setValue(10)
        confirm_layout.addRow(I18n.t("confirm_n_frames"), self.confirm_n_frames)

        self.confirm_search_window = QCheckBox(I18n.t("confirm_search_window"))
        self.confirm_search_window.setChecked(True)
        confirm_layout.addRow(self.confirm_search_window)

        self.confirm_step_seconds = QDoubleSpinBox()
        self.confirm_step_seconds.setRange(0.1, 5.0)
        self.confirm_step_seconds.setSingleStep(0.1)
        self.confirm_step_seconds.setValue(1.0)
        confirm_layout.addRow(I18n.t("confirm_step_seconds"), self.confirm_step_seconds)

        confirm_hint = QLabel(I18n.t("confirm_help"))
        confirm_hint.setStyleSheet("color:#666;")
        confirm_hint.setWordWrap(True)
        confirm_layout.addRow(confirm_hint)

        left_layout.addWidget(confirm_group)

        methods_header = QLabel(I18n.t("pipeline_methods"))
        methods_header.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(methods_header)

        self.methods_list = QListWidget()
        left_layout.addWidget(self.methods_list, stretch=1)

        btns = QHBoxLayout()
        add_btn = QPushButton("➕ " + I18n.t("add"))
        add_btn.clicked.connect(self._on_add_method)
        edit_btn = QPushButton("✏️ " + I18n.t("edit"))
        edit_btn.clicked.connect(self._on_edit_method)
        del_btn = QPushButton("🗑️ " + I18n.t("delete"))
        del_btn.clicked.connect(self._on_delete_method)
        up_btn = QPushButton("⬆️")
        up_btn.clicked.connect(lambda: self._move_method(-1))
        down_btn = QPushButton("⬇️")
        down_btn.clicked.connect(lambda: self._move_method(1))
        btns.addWidget(add_btn)
        btns.addWidget(edit_btn)
        btns.addWidget(del_btn)
        btns.addWidget(up_btn)
        btns.addWidget(down_btn)
        left_layout.addLayout(btns)

        left_layout.addStretch()
        splitter.addWidget(left)

        # Colonne droite : fiches d'explication + aperçu
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(8)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Panneau d'explication sur les modes
        mode_card = QFrame()
        mode_card.setFrameShape(QFrame.Shape.StyledPanel)
        mode_card.setStyleSheet("background:#f5f8ff; border-radius:6px; border:1px solid #dce6ff;")
        mode_layout = QVBoxLayout(mode_card)
        mode_layout.addWidget(QLabel(I18n.t("mode_help_filtering")))
        mode_layout.addWidget(QLabel(I18n.t("mode_help_weighting")))
        mode_layout.addWidget(QLabel(I18n.t("mode_help_hybrid")))
        right_layout.addWidget(mode_card)

        # Aperçu synthétique
        preview_label = QLabel(I18n.t("preview"))
        preview_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(preview_label)

        self.preview_edit = QTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setStyleSheet("font-family: monospace;")
        right_layout.addWidget(self.preview_edit, stretch=1)

        splitter.addWidget(right)
        splitter.setSizes([540, 420])

        # Boutons d’action
        actions = QHBoxLayout()
        actions.addStretch()
        cancel_btn = QPushButton(I18n.t("cancel"))
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("💾 " + I18n.t("save"))
        save_btn.clicked.connect(self._on_save)
        actions.addWidget(cancel_btn)
        actions.addWidget(save_btn)
        layout.addLayout(actions)

    def _load_data(self):
        """Charge les données du pipeline actuel ou démarre vide."""
        if self.pipeline_data:
            name = self.pipeline_data.get("name", "")
            if self.is_copy:
                name = f"{name} (copie)"
            self.name_edit.setText(name)
            self.desc_edit.setText(self.pipeline_data.get("description", ""))
            self.mode_combo.setCurrentText(self.pipeline_data.get("mode", "filtering"))
            gt_val = self.pipeline_data.get("global_threshold", 80.0)
            try:
                self.global_threshold_spin.setValue(float(gt_val if gt_val is not None else 80.0))
            except (TypeError, ValueError):
                self.global_threshold_spin.setValue(80.0)
            self.methods = deepcopy(self.pipeline_data.get("methods", []))
            confirmation = self.pipeline_data.get("confirmation") or {}
            self.confirm_enabled.setChecked(bool(confirmation.get("enabled", False)))
            params = confirmation.get("parameters", {})
            self.confirm_phash_threshold.setValue(int(params.get("phash_threshold", 10)))
            self.confirm_frame_rate.setValue(float(params.get("frame_rate_threshold", 0.8)))
            self.confirm_n_frames.setValue(int(params.get("n_frames", 10)))
            self.confirm_search_window.setChecked(bool(params.get("search_window", True)))
            self.confirm_step_seconds.setValue(float(params.get("step_seconds", 1.0)))
        else:
            self.methods = []
            self.confirm_enabled.setChecked(False)

        self._refresh_methods_list()
        self._update_preview()

    def _refresh_methods_list(self):
        self.methods_list.clear()
        for method in self.methods:
            status = "✅" if method.get("enabled", True) else "⏸️"
            weight = method.get("weight", 1.0)
            params = method.get("parameters", {})
            display_name = VerificationPipeline.AVAILABLE_METHODS.get(method.get("name"), {}).get("display_name", method.get("name"))
            item = QListWidgetItem(f"{status} {display_name} (w={weight}) – {list(params.keys())}")
            item.setData(Qt.ItemDataRole.UserRole, method)
            self.methods_list.addItem(item)

    def _on_preset_selected(self, _idx: int):
        preset_id = self.preset_combo.currentData()
        if not preset_id:
            return
        preset = PipelineManager.DEFAULT_PROTOCOLS.get(preset_id)
        if not preset:
            return
        self.mode_combo.setCurrentText(preset.get("mode", "filtering"))
        self.methods = deepcopy(preset.get("methods", []))
        self._refresh_methods_list()
        self._update_preview()

    def _on_add_method(self):
        dlg = MethodEditorDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.methods.append(dlg.get_method())
            self._refresh_methods_list()
            self._update_preview()

    def _on_edit_method(self):
        current = self.methods_list.currentItem()
        if not current:
            return
        method = current.data(Qt.ItemDataRole.UserRole)
        dlg = MethodEditorDialog(method, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            idx = self.methods_list.currentRow()
            self.methods[idx] = dlg.get_method()
            self._refresh_methods_list()
            self._update_preview()

    def _on_delete_method(self):
        idx = self.methods_list.currentRow()
        if idx < 0:
            return
        del self.methods[idx]
        self._refresh_methods_list()
        self._update_preview()

    def _move_method(self, delta: int):
        idx = self.methods_list.currentRow()
        if idx < 0:
            return
        new_idx = idx + delta
        if not (0 <= new_idx < len(self.methods)):
            return
        self.methods[idx], self.methods[new_idx] = self.methods[new_idx], self.methods[idx]
        self._refresh_methods_list()
        self.methods_list.setCurrentRow(new_idx)
        self._update_preview()

    def _build_config(self) -> Dict:
        confirmation = {
            "enabled": bool(self.confirm_enabled.isChecked()),
            "parameters": {
                "phash_threshold": int(self.confirm_phash_threshold.value()),
                "frame_rate_threshold": float(self.confirm_frame_rate.value()),
                "n_frames": int(self.confirm_n_frames.value()),
                "search_window": bool(self.confirm_search_window.isChecked()),
                "step_seconds": float(self.confirm_step_seconds.value())
            }
        }
        return {
            "mode": self.mode_combo.currentText(),
            "methods": deepcopy(self.methods),
            "confirmation": confirmation,
            "global_threshold": float(self.global_threshold_spin.value())
        }

    def _update_preview(self):
        cfg = self._build_config()
        lines = [
            f"{I18n.t('name')}: {self.name_edit.text().strip() or '<...>'}",
            f"{I18n.t('mode')}: {cfg['mode']}",
            f"{I18n.t('global_threshold')}: {cfg.get('global_threshold', 80.0):.0f}%",
            "",
            I18n.t("pipeline_methods") + ":"
        ]
        for idx, m in enumerate(cfg["methods"], 1):
            disp = VerificationPipeline.AVAILABLE_METHODS.get(m["name"], {}).get("display_name", m["name"])
            params = ", ".join([f"{k}={v}" for k, v in m.get("parameters", {}).items()])
            lines.append(f"  {idx}. {disp} (w={m.get('weight',1.0)}, on={m.get('enabled', True)}) [{params}]")
        if cfg.get("confirmation"):
            c = cfg["confirmation"]["parameters"]
            status = "ON" if cfg["confirmation"].get("enabled") else "OFF"
            lines.append("")
            lines.append(f"{I18n.t('confirm_section')} ({status})")
            lines.append(
                f"  phash_threshold={c['phash_threshold']}, frame_rate={c['frame_rate_threshold']}, "
                f"n_frames={c['n_frames']}, search_window={c.get('search_window', True)}, "
                f"step={c.get('step_seconds', 1.0)}s"
            )
        self.preview_edit.setText("\n".join(lines))

    def _validate(self) -> Optional[str]:
        name = self.name_edit.text().strip()
        if not name:
            return I18n.t("error_name_required")
        if not self.methods:
            return I18n.t("error_methods_required")
        existing = self.pipeline_manager.get_pipeline_by_name(name)
        if self.is_new and existing:
            return I18n.t("error_name_exists", name=name)
        return None

    def _on_save(self):
        error = self._validate()
        if error:
            QMessageBox.warning(self, I18n.t("validation"), error)
            return

        name = self.name_edit.text().strip()
        description = self.desc_edit.toPlainText().strip()
        cfg = self._build_config()

        try:
            if self.is_new:
                pipeline_id = self.pipeline_manager.save_pipeline(
                    name=name,
                    description=description,
                    mode=cfg["mode"],
                    methods=cfg["methods"],
                    confirmation=cfg.get("confirmation"),
                    global_threshold=cfg.get("global_threshold")
                )
                logger.info(f"Pipeline créé: {name} (id={pipeline_id})")
            else:
                pipeline_id = self.pipeline_data.get("id")
                if not pipeline_id:
                    raise ValueError("ID du pipeline manquant pour la mise à jour.")
                self.pipeline_manager.update_pipeline(
                    pipeline_id=pipeline_id,
                    name=name,
                    description=description,
                    mode=cfg["mode"],
                    methods=cfg["methods"],
                    confirmation=cfg.get("confirmation"),
                    global_threshold=cfg.get("global_threshold")
                )
                logger.info(f"Pipeline mis à jour: {name} (id={pipeline_id})")

            QMessageBox.information(self, I18n.t("success"), I18n.t("pipeline_saved", name=name))
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, I18n.t("error"), f"{I18n.t('save_failed')}\n{e}")
            logger.error(f"Erreur sauvegarde pipeline: {e}", exc_info=True)

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when dialog is closed.

        Ensures proper cleanup of resources and signals.
        """
        # All signals are internal and auto-cleaned by Qt
        # Added for consistency with other dialogs
        super().closeEvent(event)
