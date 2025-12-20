"""
Nouvelles méthodes de callback pour les 2 pipelines séparés
À remplacer dans main_window.py (lignes 953-1012)
"""

NEW_METHODS = '''
    # ══════════════════════════════════════════════════════════
    # DUPLICATES PIPELINE CALLBACKS
    # ══════════════════════════════════════════════════════════

    def _on_edit_duplicates_pipeline(self) -> None:
        """Open pipeline editor for the selected DUPLICATES pipeline."""
        if not self.duplicates_pipeline_combo or not self.pipeline_manager:
            return
        current_index = self.duplicates_pipeline_combo.currentIndex()
        if current_index < 0:
            return
        pipeline_data = self.duplicates_pipeline_combo.itemData(current_index)
        if not pipeline_data:
            return
        if pipeline_data.get('is_default', False):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Pipeline par défaut",
                f"Le pipeline '{pipeline_data['name']}' est un pipeline par défaut et ne peut pas être modifié.\\n\\n"
                "Vous pouvez créer une copie en cliquant sur 'Nouveau'.")
            return
        from .ui.unified_pipeline_editor_dialog import UnifiedPipelineEditorDialog
        dialog = UnifiedPipelineEditorDialog(
            pipeline_manager=self.pipeline_manager, db_manager=self.db,
            pipeline_data=pipeline_data, is_copy=False, parent=self)
        if dialog.exec():
            self._reload_duplicates_pipeline_combo()
            logger.info(f"Pipeline DUPLICATES '{pipeline_data['name']}' modifié")

    def _on_new_duplicates_pipeline(self) -> None:
        """Open pipeline editor to create a new DUPLICATES pipeline."""
        if not self.pipeline_manager:
            return
        from .ui.unified_pipeline_editor_dialog import UnifiedPipelineEditorDialog
        dialog = UnifiedPipelineEditorDialog(
            pipeline_manager=self.pipeline_manager, db_manager=self.db,
            pipeline_data=None, is_copy=False, parent=self)
        if dialog.exec():
            self._reload_duplicates_pipeline_combo()
            if self.duplicates_pipeline_combo:
                self.duplicates_pipeline_combo.setCurrentIndex(self.duplicates_pipeline_combo.count() - 1)
            logger.info("Nouveau pipeline DUPLICATES créé")

    def _reload_duplicates_pipeline_combo(self) -> None:
        """Reload the DUPLICATES pipeline combo box with current pipelines."""
        if not self.duplicates_pipeline_combo or not self.pipeline_manager:
            return
        from .ui.panels import UIPanels

        current_name = None
        current_index = self.duplicates_pipeline_combo.currentIndex()
        if current_index >= 0:
            current_data = self.duplicates_pipeline_combo.itemData(current_index)
            if current_data:
                current_name = current_data.get('name')

        self.duplicates_pipeline_combo.clear()
        all_pipelines = self.pipeline_manager.list_pipelines(include_defaults=True)
        # Filter for duplicates
        filtered_pipelines = UIPanels._filter_pipelines_by_type(all_pipelines, "duplicates")

        new_index = 0
        for i, pipeline in enumerate(filtered_pipelines):
            display_name = pipeline['name']
            if pipeline.get('is_default'):
                display_name = f"⭐ {display_name}"
            self.duplicates_pipeline_combo.addItem(display_name, userData=pipeline)
            if current_name and pipeline['name'] == current_name:
                new_index = i

        if self.duplicates_pipeline_combo.count() > 0:
            self.duplicates_pipeline_combo.setCurrentIndex(new_index)

    # ══════════════════════════════════════════════════════════
    # SCÈNES PIPELINE CALLBACKS
    # ══════════════════════════════════════════════════════════

    def _on_edit_scenes_pipeline(self) -> None:
        """Open pipeline editor for the selected SCÈNES pipeline."""
        if not self.scenes_pipeline_combo or not self.pipeline_manager:
            return
        current_index = self.scenes_pipeline_combo.currentIndex()
        if current_index < 0:
            return
        pipeline_data = self.scenes_pipeline_combo.itemData(current_index)
        if not pipeline_data:
            return
        if pipeline_data.get('is_default', False):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Pipeline par défaut",
                f"Le pipeline '{pipeline_data['name']}' est un pipeline par défaut et ne peut pas être modifié.\\n\\n"
                "Vous pouvez créer une copie en cliquant sur 'Nouveau'.")
            return
        from .ui.unified_pipeline_editor_dialog import UnifiedPipelineEditorDialog
        dialog = UnifiedPipelineEditorDialog(
            pipeline_manager=self.pipeline_manager, db_manager=self.db,
            pipeline_data=pipeline_data, is_copy=False, parent=self)
        if dialog.exec():
            self._reload_scenes_pipeline_combo()
            logger.info(f"Pipeline SCÈNES '{pipeline_data['name']}' modifié")

    def _on_new_scenes_pipeline(self) -> None:
        """Open pipeline editor to create a new SCÈNES pipeline."""
        if not self.pipeline_manager:
            return
        from .ui.unified_pipeline_editor_dialog import UnifiedPipelineEditorDialog
        dialog = UnifiedPipelineEditorDialog(
            pipeline_manager=self.pipeline_manager, db_manager=self.db,
            pipeline_data=None, is_copy=False, parent=self)
        if dialog.exec():
            self._reload_scenes_pipeline_combo()
            if self.scenes_pipeline_combo:
                self.scenes_pipeline_combo.setCurrentIndex(self.scenes_pipeline_combo.count() - 1)
            logger.info("Nouveau pipeline SCÈNES créé")

    def _reload_scenes_pipeline_combo(self) -> None:
        """Reload the SCÈNES pipeline combo box with current pipelines."""
        if not self.scenes_pipeline_combo or not self.pipeline_manager:
            return
        from .ui.panels import UIPanels

        current_name = None
        current_index = self.scenes_pipeline_combo.currentIndex()
        if current_index >= 0:
            current_data = self.scenes_pipeline_combo.itemData(current_index)
            if current_data:
                current_name = current_data.get('name')

        self.scenes_pipeline_combo.clear()
        all_pipelines = self.pipeline_manager.list_pipelines(include_defaults=True)
        # Filter for scenes
        filtered_pipelines = UIPanels._filter_pipelines_by_type(all_pipelines, "scenes")

        new_index = 0
        for i, pipeline in enumerate(filtered_pipelines):
            display_name = pipeline['name']
            if pipeline.get('is_default'):
                display_name = f"⭐ {display_name}"
            self.scenes_pipeline_combo.addItem(display_name, userData=pipeline)
            if current_name and pipeline['name'] == current_name:
                new_index = i

        if self.scenes_pipeline_combo.count() > 0:
            self.scenes_pipeline_combo.setCurrentIndex(new_index)
'''

# Read main_window.py
with open('/Users/nico/Documents/videoFlow/src/plugins/duplicate_finder/ui/main_window.py', 'r') as f:
    lines = f.readlines()

# Replace lines 953-1012 (0-indexed: 952-1011)
new_lines = lines[:952] + [NEW_METHODS + '\n'] + lines[1012:]

# Write back
with open('/Users/nico/Documents/videoFlow/src/plugins/duplicate_finder/ui/main_window.py', 'w') as f:
    f.writelines(new_lines)

print("✅ Méthodes de callback remplacées dans main_window.py")
print(f"   - Anciennes méthodes (3): _on_edit_pipeline, _on_new_pipeline, _reload_pipeline_combo")
print(f"   - Nouvelles méthodes (6): 3 pour DUPLICATES + 3 pour SCÈNES")
print(f"   - Lignes 953-1012 remplacées")
