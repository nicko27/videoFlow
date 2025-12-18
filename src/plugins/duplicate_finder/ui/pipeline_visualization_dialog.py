"""
Pipeline Visualization Dialog - Visualisation graphique d'un pipeline
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QWidget, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPalette

from src.core.logger import Logger
from ..verification_pipeline import VerificationPipeline
from ..infrastructure.i18n import I18n
from ..integration import get_all_algorithms_dict

logger = Logger.get_logger('DuplicateFinder.PipelineVisualization')


class PipelineVisualizationDialog(QDialog):
    """
    Dialogue de visualisation graphique d'un pipeline.

    Affiche le pipeline sous forme de diagramme avec:
    - Flux de décision
    - Méthodes dans l'ordre
    - Paramètres de chaque méthode
    - Mode de combinaison
    """

    def __init__(self, pipeline_data: dict, parent=None):
        """
        Args:
            pipeline_data: Données du pipeline à visualiser
            parent: Widget parent
        """
        super().__init__(parent)
        self.pipeline_data = pipeline_data

        self.setWindowTitle(f"🔍 {I18n.t('pipeline_visual_title', name=pipeline_data['name'])}")
        self.setMinimumSize(800, 600)

        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"🔍 {self.pipeline_data['name']}")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(header)

        # Description
        desc = QLabel(self.pipeline_data.get('description', I18n.t("no_description")))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; padding: 5px; font-style: italic;")
        layout.addWidget(desc)

        # Mode info
        mode_info = self._get_mode_description(self.pipeline_data['mode'])
        mode_label = QLabel(f"<b>{I18n.t('mode')}:</b> {self.pipeline_data['mode'].upper()}")
        mode_label.setStyleSheet("padding: 10px; background-color: #E3F2FD; border-radius: 5px;")
        layout.addWidget(mode_label)

        mode_desc = QLabel(mode_info)
        mode_desc.setWordWrap(True)
        mode_desc.setStyleSheet("padding: 5px 10px; color: #555;")
        layout.addWidget(mode_desc)

        # Scroll area for pipeline flow
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        flow_widget = QWidget()
        flow_layout = QVBoxLayout(flow_widget)
        flow_layout.setSpacing(10)

        # Start node
        start_node = self._create_node("🎬 " + I18n.t("viz_start"), "#4CAF50", is_start=True)
        flow_layout.addWidget(start_node)

        # Add arrow
        flow_layout.addWidget(self._create_arrow())

        # Method nodes
        enabled_methods = [m for m in self.pipeline_data['methods'] if m.get('enabled', True)]

        for idx, method in enumerate(enabled_methods, 1):
            method_node = self._create_method_node(method, idx, len(enabled_methods))
            flow_layout.addWidget(method_node)

            if idx < len(enabled_methods):
                flow_layout.addWidget(self._create_arrow())

        # Add arrow
        flow_layout.addWidget(self._create_arrow())

        # Decision node based on mode
        if self.pipeline_data['mode'] == 'filtering':
            decision_text = I18n.t("viz_decision_filtering")
        elif self.pipeline_data['mode'] == 'weighting':
            decision_text = I18n.t("viz_decision_weighting")
        else:  # hybrid
            decision_text = I18n.t("viz_decision_hybrid")

        decision_node = self._create_node(f"❓ {decision_text}", "#FF9800")
        flow_layout.addWidget(decision_node)

        # Result branches
        result_layout = QHBoxLayout()

        # Accept branch
        accept_layout = QVBoxLayout()
        accept_layout.addWidget(self._create_arrow("→ " + I18n.t("viz_yes")))
        accept_node = self._create_node("✅ " + I18n.t("viz_accepted"), "#4CAF50")
        accept_layout.addWidget(accept_node)
        result_layout.addLayout(accept_layout)

        # Reject branch
        reject_layout = QVBoxLayout()
        reject_layout.addWidget(self._create_arrow("→ " + I18n.t("viz_no")))
        reject_node = self._create_node("❌ " + I18n.t("viz_rejected"), "#F44336")
        reject_layout.addWidget(reject_node)
        result_layout.addLayout(reject_layout)

        flow_layout.addLayout(result_layout)

        flow_layout.addStretch()

        scroll.setWidget(flow_widget)
        layout.addWidget(scroll)

        # Close button
        close_btn = QPushButton("✖ " + I18n.t("close"))
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _get_mode_description(self, mode: str) -> str:
        """Retourne la description du mode."""
        descriptions = {
            'filtering': I18n.t("mode_help_filtering"),
            'weighting': I18n.t("mode_help_weighting"),
            'hybrid': I18n.t("mode_help_hybrid")
        }
        return descriptions.get(mode, I18n.t("unknown_mode"))

    def _create_node(self, text: str, color: str, is_start: bool = False) -> QFrame:
        """Crée un nœud du diagramme."""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.Box)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border: 3px solid {self._darken_color(color)};
                border-radius: 10px;
                padding: 15px;
            }}
        """)

        layout = QVBoxLayout(frame)
        label = QLabel(text)
        label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        label.setStyleSheet("color: white; border: none;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        return frame

    def _create_method_node(self, method: dict, index: int, total: int) -> QFrame:
        """Crée un nœud pour une méthode."""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.Box)
        frame.setStyleSheet("""
            QFrame {
                background-color: #2196F3;
                border: 3px solid #1976D2;
                border-radius: 10px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout(frame)

        available_methods = get_all_algorithms_dict()
        meta = available_methods.get(method.get('name'), {})

        # Method name
        display_name = meta.get("display_name", method.get("name"))
        name_label = QLabel(f"#{index} - {display_name}")
        name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        name_label.setStyleSheet("color: white; border: none;")
        layout.addWidget(name_label)

        # Short description / use case
        short_desc = meta.get("description", "")
        use_case = meta.get("use_case", "")
        speed = meta.get("speed", "")
        if short_desc or use_case:
            info_label = QLabel(f"{short_desc}<br><i>{use_case}</i> — {speed}")
            info_label.setStyleSheet("color: #E3F2FD; border: none;")
            info_label.setWordWrap(True)
            layout.addWidget(info_label)

        # Weight (if applicable)
        if 'weight' in method and self.pipeline_data['mode'] in ['weighting', 'hybrid']:
            weight_label = QLabel(f"{I18n.t('weight')}: {method['weight']}")
            weight_label.setStyleSheet("color: #E3F2FD; border: none;")
            layout.addWidget(weight_label)

        # Parameters
        params = method.get('parameters', {})
        if params:
            params_text = "<br>".join([f"• {k}: <b>{v}</b>" for k, v in params.items()])
            params_label = QLabel(params_text)
            params_label.setStyleSheet("color: white; border: none; font-size: 10pt;")
            params_label.setWordWrap(True)
            layout.addWidget(params_label)

        return frame

    def _create_arrow(self, label: str = "") -> QLabel:
        """Crée une flèche entre deux nœuds."""
        arrow = QLabel("⬇" if not label else label)
        arrow.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        arrow.setStyleSheet("color: #666;")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setFixedHeight(30)
        return arrow

    def _darken_color(self, hex_color: str) -> str:
        """Assombrit une couleur hexadécimale."""
        # Simple darkening by reducing each RGB component
        if hex_color.startswith('#'):
            hex_color = hex_color[1:]

        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        r = max(0, r - 30)
        g = max(0, g - 30)
        b = max(0, b - 30)

        return f"#{r:02x}{g:02x}{b:02x}"

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when dialog is closed.

        Ensures proper cleanup of resources and signals.
        """
        # All signals are internal and auto-cleaned by Qt
        # Added for consistency with other dialogs
        super().closeEvent(event)
