"""
Pipeline Library Dialog - Gestion et visualisation des pipelines
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QTextEdit, QSplitter, QGroupBox, QMessageBox,
    QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.PipelineLibrary')


class PipelineLibraryDialog(QDialog):
    """
    Dialogue de gestion de la bibliothèque de pipelines.

    Fonctionnalités:
    - Visualiser tous les pipelines (par défaut + utilisateur)
    - Voir les détails (méthodes, paramètres, ordre)
    - Copier un pipeline
    - Modifier un pipeline (ou copier pour les pipelines par défaut)
    - Supprimer un pipeline utilisateur
    """

    def __init__(self, pipeline_manager, db_manager, parent=None):
        """
        Args:
            pipeline_manager: Instance PipelineManager
            db_manager: Instance DatabaseManager
            parent: Widget parent
        """
        super().__init__(parent)
        self.pipeline_manager = pipeline_manager
        self.db_manager = db_manager
        self.parent_window = parent

        self.setWindowTitle("📚 Bibliothèque des Pipelines")
        self.setMinimumSize(1000, 700)

        self._setup_ui()
        self._load_pipelines()

    def _setup_ui(self):
        """Configure l'interface."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("📚 Bibliothèque des Pipelines")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(header)

        # Splitter for list and details
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Pipeline list
        left_panel = QGroupBox("Pipelines Disponibles")
        left_layout = QVBoxLayout(left_panel)

        self.pipeline_list = QListWidget()
        self.pipeline_list.currentItemChanged.connect(self._on_pipeline_selected)
        left_layout.addWidget(self.pipeline_list)

        splitter.addWidget(left_panel)

        # Right panel: Details and actions
        right_panel = QGroupBox("Détails du Pipeline")
        right_layout = QVBoxLayout(right_panel)

        # Pipeline details display
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Courier", 10))
        right_layout.addWidget(self.details_text)

        # Action buttons
        actions_layout = QHBoxLayout()

        self.new_btn = QPushButton("➕ Nouveau")
        self.new_btn.clicked.connect(self._on_new_pipeline)
        self.new_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        actions_layout.addWidget(self.new_btn)

        self.view_btn = QPushButton("🔍 Visualiser")
        self.view_btn.clicked.connect(self._on_view_pipeline)
        self.view_btn.setEnabled(False)
        actions_layout.addWidget(self.view_btn)

        self.copy_btn = QPushButton("📋 Copier")
        self.copy_btn.clicked.connect(self._on_copy_pipeline)
        self.copy_btn.setEnabled(False)
        actions_layout.addWidget(self.copy_btn)

        self.edit_btn = QPushButton("✏️ Modifier")
        self.edit_btn.clicked.connect(self._on_edit_pipeline)
        self.edit_btn.setEnabled(False)
        actions_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑️ Supprimer")
        self.delete_btn.clicked.connect(self._on_delete_pipeline)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        actions_layout.addWidget(self.delete_btn)

        right_layout.addLayout(actions_layout)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        close_btn = QPushButton("✖ Fermer")
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
        bottom_layout.addWidget(close_btn)

        layout.addLayout(bottom_layout)

    def _load_pipelines(self):
        """Charge tous les pipelines (par défaut + utilisateur)."""
        self.pipeline_list.clear()

        # Load default pipelines from PipelineManager class variable
        from ..orchestration.pipeline_manager import PipelineManager
        default_protocols = PipelineManager.DEFAULT_PROTOCOLS
        for protocol_id, protocol in default_protocols.items():
            item = QListWidgetItem(f"📦 [Défaut] {protocol['name']}")
            item.setData(Qt.ItemDataRole.UserRole, {
                'type': 'default',
                'id': protocol_id,
                'data': protocol
            })
            item.setToolTip(protocol.get('description', ''))
            self.pipeline_list.addItem(item)

        # Load user pipelines uniquement (on évite les doublons avec les defaults déjà listés)
        user_pipelines = self.pipeline_manager.list_pipelines(include_defaults=False)
        for pipeline in user_pipelines:
            item = QListWidgetItem(f"👤 [Utilisateur] {pipeline['name']}")
            item.setData(Qt.ItemDataRole.UserRole, {
                'type': 'user',
                'id': pipeline['id'],
                'data': pipeline
            })
            item.setToolTip(pipeline.get('description', ''))
            item.setForeground(QColor("#2196F3"))  # Blue for user pipelines
            self.pipeline_list.addItem(item)

        logger.info(f"Loaded {len(default_protocols)} default + {len(user_pipelines)} user pipelines")

    def _on_pipeline_selected(self, current, previous):
        """Callback quand un pipeline est sélectionné."""
        if not current:
            self.details_text.clear()
            self.view_btn.setEnabled(False)
            self.copy_btn.setEnabled(False)
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return

        pipeline_info = current.data(Qt.ItemDataRole.UserRole)
        pipeline_data = pipeline_info['data']
        is_default = pipeline_info['type'] == 'default'

        # Display details
        details = self._format_pipeline_details(pipeline_data, is_default)
        self.details_text.setHtml(details)

        # Enable buttons
        self.view_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.edit_btn.setEnabled(True)

        # Only allow deletion for user pipelines
        self.delete_btn.setEnabled(not is_default)

        # Change edit button text for default pipelines
        if is_default:
            self.edit_btn.setText("✏️ Copier & Modifier")
        else:
            self.edit_btn.setText("✏️ Modifier")

    def _format_pipeline_details(self, pipeline: dict, is_default: bool) -> str:
        """Formate les détails d'un pipeline en HTML."""
        html = f"<h2>{pipeline['name']}</h2>"

        if is_default:
            html += "<p><b>Type:</b> <span style='color: #FF9800;'>Pipeline par Défaut</span></p>"
        else:
            html += "<p><b>Type:</b> <span style='color: #2196F3;'>Pipeline Utilisateur</span></p>"

        html += f"<p><b>Description:</b> {pipeline.get('description', 'Aucune description')}</p>"
        html += f"<p><b>Mode:</b> <code>{pipeline['mode']}</code></p>"

        # Methods
        html += "<h3>Méthodes (dans l'ordre d'exécution):</h3>"
        html += "<ol>"

        for idx, method in enumerate(pipeline['methods'], 1):
            if not method.get('enabled', True):
                continue

            method_name = method['name']
            weight = method.get('weight', 1.0)
            params = method.get('parameters', {})

            html += f"<li><b>{method_name}</b>"

            if pipeline['mode'] in ['weighting', 'hybrid']:
                html += f" (poids: {weight})"

            if params:
                html += "<ul>"
                for key, value in params.items():
                    html += f"<li>{key}: <code>{value}</code></li>"
                html += "</ul>"

            html += "</li>"

        html += "</ol>"

        return html

    def _on_new_pipeline(self):
        """Crée un nouveau pipeline."""
        from .unified_pipeline_editor_dialog import UnifiedPipelineEditorDialog
        dialog = UnifiedPipelineEditorDialog(
            self.pipeline_manager,
            self.db_manager,
            pipeline_data=None,
            is_copy=False,
            parent=self
        )

        if dialog.exec():
            # Reload list if saved
            self._load_pipelines()

    def _on_view_pipeline(self):
        """Visualise le pipeline de manière détaillée."""
        current = self.pipeline_list.currentItem()
        if not current:
            return

        pipeline_info = current.data(Qt.ItemDataRole.UserRole)
        pipeline_data = pipeline_info['data']

        # Create visualization dialog
        from .pipeline_visualization_dialog import PipelineVisualizationDialog
        dialog = PipelineVisualizationDialog(pipeline_data, self)
        dialog.exec()

    def _on_copy_pipeline(self):
        """Copie le pipeline sélectionné."""
        current = self.pipeline_list.currentItem()
        if not current:
            return

        pipeline_info = current.data(Qt.ItemDataRole.UserRole)
        pipeline_data = pipeline_info['data']

        # Open editor dialog in copy mode
        from .unified_pipeline_editor_dialog import UnifiedPipelineEditorDialog
        dialog = UnifiedPipelineEditorDialog(
            self.pipeline_manager,
            self.db_manager,
            pipeline_data=pipeline_data,
            is_copy=True,
            parent=self
        )

        if dialog.exec():
            # Reload list if saved
            self._load_pipelines()

    def _on_edit_pipeline(self):
        """Modifie le pipeline ou le copie si c'est un pipeline par défaut."""
        current = self.pipeline_list.currentItem()
        if not current:
            return

        pipeline_info = current.data(Qt.ItemDataRole.UserRole)
        pipeline_data = pipeline_info['data']
        is_default = pipeline_info['type'] == 'default'

        if is_default:
            # For default pipelines, ask to create a copy
            reply = QMessageBox.question(
                self,
                "Modifier un Pipeline par Défaut",
                f"Les pipelines par défaut ne peuvent pas être modifiés directement.\n\n"
                f"Voulez-vous créer une copie modifiable de '{pipeline_data['name']}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                return

        # Open editor dialog (copy if default, edit if user)
        from .unified_pipeline_editor_dialog import UnifiedPipelineEditorDialog
        dialog = UnifiedPipelineEditorDialog(
            self.pipeline_manager,
            self.db_manager,
            pipeline_data=pipeline_data,
            is_copy=is_default,
            parent=self
        )

        if dialog.exec():
            # Reload list if saved
            self._load_pipelines()

    def _on_delete_pipeline(self):
        """Supprime le pipeline utilisateur sélectionné."""
        current = self.pipeline_list.currentItem()
        if not current:
            return

        pipeline_info = current.data(Qt.ItemDataRole.UserRole)

        if pipeline_info['type'] == 'default':
            QMessageBox.warning(
                self,
                "Action Impossible",
                "Les pipelines par défaut ne peuvent pas être supprimés."
            )
            return

        pipeline_data = pipeline_info['data']
        pipeline_id = pipeline_info['id']

        reply = QMessageBox.question(
            self,
            "Confirmer la Suppression",
            f"Êtes-vous sûr de vouloir supprimer le pipeline:\n\n'{pipeline_data['name']}'?\n\n"
            f"Cette action est irréversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        try:
            self.pipeline_manager.delete_pipeline(pipeline_id)
            QMessageBox.information(
                self,
                "Succès",
                f"✅ Pipeline '{pipeline_data['name']}' supprimé avec succès!"
            )

            # Reload list
            self._load_pipelines()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"❌ Erreur lors de la suppression:\n{e}"
            )

    def closeEvent(self, event):
        """
        CORRECTION BUG #18: Cleanup resources when dialog is closed.

        Ensures proper cleanup of resources and signals.
        """
        # All signals are internal and auto-cleaned by Qt
        # Added for consistency with other dialogs
        super().closeEvent(event)
