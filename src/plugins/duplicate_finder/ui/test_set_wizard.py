"""
Test Set Wizard - Assistant pour créer des test sets de plusieurs façons.

Fournit 4 méthodes pour créer des test sets:
1. From file list - Sélectionner des fichiers et générer toutes les paires
2. Manual pairs - Ajouter manuellement des paires vidéo par vidéo
3. Import JSON - Importer depuis un fichier pairs.json existant
4. From results - Créer un test set à partir de résultats d'analyse existants
"""
import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QListWidget, QListWidgetItem, QFileDialog,
    QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QSpinBox, QMessageBox, QCheckBox, QGroupBox,
    QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from src.core.logger import Logger
from ..managers import TestSetManager

logger = Logger.get_logger('DuplicateFinder.TestSetWizard')


class TestSetWizard(QDialog):
    """
    Assistant pour créer des test sets avec 4 méthodes différentes.

    Signals:
        test_set_created(str): Émis quand un test set est créé (nom du test set)
    """

    test_set_created = pyqtSignal(str)

    def __init__(self, test_set_manager: TestSetManager, parent=None):
        super().__init__(parent)
        self.test_set_manager = test_set_manager
        self.setWindowTitle("Assistant Test Set")
        self.setMinimumSize(800, 600)
        self._init_ui()

    def _init_ui(self):
        """Initialize the wizard UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("🧙 <b>Assistant de Création de Test Set</b>")
        header.setStyleSheet("font-size: 16px; padding: 10px; background-color: #E3F2FD; border-radius: 5px;")
        layout.addWidget(header)

        # Description
        desc = QLabel(
            "Cet assistant vous aide à créer un test set pour valider vos pipelines de détection. "
            "Choisissez la méthode qui vous convient :"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("padding: 10px; color: #555;")
        layout.addWidget(desc)

        # Tabs for different methods
        self.tabs = QTabWidget()

        # Tab 1: From file list
        self.file_list_tab = self._create_file_list_tab()
        self.tabs.addTab(self.file_list_tab, "📁 Liste de Fichiers")

        # Tab 2: Manual pairs
        self.manual_tab = self._create_manual_tab()
        self.tabs.addTab(self.manual_tab, "✍️ Paires Manuelles")

        # Tab 3: Import JSON
        self.import_tab = self._create_import_tab()
        self.tabs.addTab(self.import_tab, "📥 Import JSON")

        # Tab 4: From results
        self.results_tab = self._create_results_tab()
        self.tabs.addTab(self.results_tab, "📊 Depuis Résultats")

        layout.addWidget(self.tabs)

        # Test set name (common to all methods)
        name_group = QGroupBox("Nom du Test Set")
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nom:"))
        self.test_set_name = QLineEdit()
        self.test_set_name.setPlaceholderText("Ex: validation_set_2025")
        name_layout.addWidget(self.test_set_name)
        name_group.setLayout(name_layout)
        layout.addWidget(name_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Annuler")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.create_btn = QPushButton("✅ Créer Test Set")
        self.create_btn.clicked.connect(self._on_create)
        self.create_btn.setStyleSheet("font-weight: bold; padding: 8px 20px;")
        btn_layout.addWidget(self.create_btn)

        layout.addLayout(btn_layout)

    def _create_file_list_tab(self) -> QWidget:
        """Create tab for generating pairs from file list."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Instructions
        instructions = QLabel(
            "📁 <b>Générer des paires depuis une liste de fichiers</b><br>"
            "Sélectionnez des fichiers vidéo, puis choisissez comment générer les paires de test."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # File list
        list_layout = QHBoxLayout()

        file_list_container = QVBoxLayout()
        file_list_container.addWidget(QLabel("Fichiers vidéo:"))
        self.file_list = QListWidget()
        file_list_container.addWidget(self.file_list)

        # File buttons
        file_btn_layout = QVBoxLayout()
        add_files_btn = QPushButton("➕ Ajouter Fichiers")
        add_files_btn.clicked.connect(self._on_add_files)
        file_btn_layout.addWidget(add_files_btn)

        add_folder_btn = QPushButton("📂 Ajouter Dossier")
        add_folder_btn.clicked.connect(self._on_add_folder)
        file_btn_layout.addWidget(add_folder_btn)

        remove_btn = QPushButton("🗑️ Retirer")
        remove_btn.clicked.connect(self._on_remove_file)
        file_btn_layout.addWidget(remove_btn)

        clear_btn = QPushButton("🧹 Tout Effacer")
        clear_btn.clicked.connect(self.file_list.clear)
        file_btn_layout.addWidget(clear_btn)

        file_btn_layout.addStretch()

        list_layout.addLayout(file_list_container, stretch=3)
        list_layout.addLayout(file_btn_layout)
        layout.addLayout(list_layout)

        # Generation strategy
        strategy_group = QGroupBox("Stratégie de Génération")
        strategy_layout = QVBoxLayout()

        self.gen_strategy_group = QButtonGroup(self)

        self.all_pairs_radio = QRadioButton("Toutes les paires possibles (N×(N-1)/2 paires)")
        self.all_pairs_radio.setChecked(True)
        self.gen_strategy_group.addButton(self.all_pairs_radio)
        strategy_layout.addWidget(self.all_pairs_radio)

        self.sequential_radio = QRadioButton("Paires séquentielles (comparer chaque fichier avec le suivant)")
        self.gen_strategy_group.addButton(self.sequential_radio)
        strategy_layout.addWidget(self.sequential_radio)

        self.random_radio = QRadioButton("Paires aléatoires (nombre spécifique)")
        self.gen_strategy_group.addButton(self.random_radio)
        strategy_layout.addWidget(self.random_radio)

        random_count_layout = QHBoxLayout()
        random_count_layout.addWidget(QLabel("   Nombre de paires:"))
        self.random_count = QSpinBox()
        self.random_count.setRange(1, 10000)
        self.random_count.setValue(50)
        self.random_count.setEnabled(False)
        random_count_layout.addWidget(self.random_count)
        random_count_layout.addStretch()
        strategy_layout.addLayout(random_count_layout)

        self.random_radio.toggled.connect(lambda checked: self.random_count.setEnabled(checked))

        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)

        # Expected result
        expected_group = QGroupBox("Résultat Attendu par Défaut")
        expected_layout = QHBoxLayout()

        self.expected_combo = QComboBox()
        self.expected_combo.addItems(["duplicate", "not_duplicate", "unknown"])
        self.expected_combo.setCurrentText("unknown")
        expected_layout.addWidget(QLabel("Par défaut:"))
        expected_layout.addWidget(self.expected_combo)
        expected_layout.addStretch()

        expected_group.setLayout(expected_layout)
        layout.addWidget(expected_group)

        # Stats
        self.file_list_stats = QLabel("Fichiers: 0 | Paires estimées: 0")
        self.file_list_stats.setStyleSheet("background-color: #F0F0F0; padding: 5px; border-radius: 3px;")
        layout.addWidget(self.file_list_stats)

        self.file_list.itemSelectionChanged.connect(self._update_file_stats)

        return tab

    def _create_manual_tab(self) -> QWidget:
        """Create tab for manually adding pairs."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Instructions
        instructions = QLabel(
            "✍️ <b>Ajouter des paires manuellement</b><br>"
            "Créez des paires de test en sélectionnant deux vidéos et en spécifiant le résultat attendu."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Pair input
        input_group = QGroupBox("Ajouter une Paire")
        input_layout = QVBoxLayout()

        # Video 1
        video1_layout = QHBoxLayout()
        video1_layout.addWidget(QLabel("Vidéo 1:"))
        self.video1_input = QLineEdit()
        self.video1_input.setPlaceholderText("Chemin vers la première vidéo")
        video1_layout.addWidget(self.video1_input)
        self.browse1_btn = QPushButton("📂 Parcourir")
        self.browse1_btn.clicked.connect(lambda: self._browse_video(self.video1_input))
        video1_layout.addWidget(self.browse1_btn)
        input_layout.addLayout(video1_layout)

        # Video 2
        video2_layout = QHBoxLayout()
        video2_layout.addWidget(QLabel("Vidéo 2:"))
        self.video2_input = QLineEdit()
        self.video2_input.setPlaceholderText("Chemin vers la deuxième vidéo")
        video2_layout.addWidget(self.video2_input)
        self.browse2_btn = QPushButton("📂 Parcourir")
        self.browse2_btn.clicked.connect(lambda: self._browse_video(self.video2_input))
        video2_layout.addWidget(self.browse2_btn)
        input_layout.addLayout(video2_layout)

        # Expected result
        expected_layout = QHBoxLayout()
        expected_layout.addWidget(QLabel("Résultat attendu:"))
        self.manual_expected_combo = QComboBox()
        self.manual_expected_combo.addItems(["duplicate", "not_duplicate", "unknown"])
        expected_layout.addWidget(self.manual_expected_combo)

        expected_layout.addWidget(QLabel("Notes:"))
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Notes optionnelles")
        expected_layout.addWidget(self.notes_input)
        input_layout.addLayout(expected_layout)

        # Add button
        add_pair_btn = QPushButton("➕ Ajouter cette paire")
        add_pair_btn.clicked.connect(self._on_add_manual_pair)
        input_layout.addWidget(add_pair_btn)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Pairs table
        layout.addWidget(QLabel("Paires ajoutées:"))
        self.manual_pairs_table = QTableWidget()
        self.manual_pairs_table.setColumnCount(5)
        self.manual_pairs_table.setHorizontalHeaderLabels(["Vidéo 1", "Vidéo 2", "Attendu", "Notes", ""])
        self.manual_pairs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.manual_pairs_table.setColumnWidth(4, 60)
        layout.addWidget(self.manual_pairs_table)

        # Stats
        self.manual_stats = QLabel("Paires: 0")
        self.manual_stats.setStyleSheet("background-color: #F0F0F0; padding: 5px; border-radius: 3px;")
        layout.addWidget(self.manual_stats)

        return tab

    def _create_import_tab(self) -> QWidget:
        """Create tab for importing from JSON."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Instructions
        instructions = QLabel(
            "📥 <b>Importer depuis un fichier JSON</b><br>"
            "Importez un fichier pairs.json existant pour créer rapidement un test set."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # File selection
        file_group = QGroupBox("Fichier JSON")
        file_layout = QHBoxLayout()

        self.json_file_input = QLineEdit()
        self.json_file_input.setPlaceholderText("Sélectionnez un fichier pairs.json")
        file_layout.addWidget(self.json_file_input)

        browse_json_btn = QPushButton("📂 Parcourir")
        browse_json_btn.clicked.connect(self._on_browse_json)
        file_layout.addWidget(browse_json_btn)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Preview
        layout.addWidget(QLabel("Aperçu du contenu:"))
        self.json_preview = QTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setMaximumHeight(300)
        layout.addWidget(self.json_preview)

        # Stats
        self.import_stats = QLabel("Aucun fichier sélectionné")
        self.import_stats.setStyleSheet("background-color: #F0F0F0; padding: 5px; border-radius: 3px;")
        layout.addWidget(self.import_stats)

        layout.addStretch()

        return tab

    def _create_results_tab(self) -> QWidget:
        """Create tab for creating test set from analysis results."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Instructions
        instructions = QLabel(
            "📊 <b>Créer depuis des résultats d'analyse</b><br>"
            "Créez un test set basé sur les résultats d'une analyse précédente. "
            "Utile pour valider que les détections sont reproductibles."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        self.include_duplicates = QCheckBox("Inclure les paires détectées comme duplicata (résultat = duplicate)")
        self.include_duplicates.setChecked(True)
        options_layout.addWidget(self.include_duplicates)

        self.include_non_duplicates = QCheckBox("Inclure un échantillon de paires non-duplicata (résultat = not_duplicate)")
        self.include_non_duplicates.setChecked(True)
        options_layout.addWidget(self.include_non_duplicates)

        sample_layout = QHBoxLayout()
        sample_layout.addWidget(QLabel("   Nombre max de non-duplicata:"))
        self.non_dup_sample = QSpinBox()
        self.non_dup_sample.setRange(10, 1000)
        self.non_dup_sample.setValue(100)
        sample_layout.addWidget(self.non_dup_sample)
        sample_layout.addStretch()
        options_layout.addLayout(sample_layout)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Database query info
        info_label = QLabel(
            "ℹ️ Cette méthode nécessite une analyse complétée avec des résultats dans la base de données. "
            "Elle créera un test set basé sur les comparaisons stockées."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("background-color: #FFF9C4; padding: 10px; border-radius: 5px; color: #666;")
        layout.addWidget(info_label)

        # Stats
        self.results_stats = QLabel("Prêt à créer le test set depuis la base de données")
        self.results_stats.setStyleSheet("background-color: #F0F0F0; padding: 5px; border-radius: 3px;")
        layout.addWidget(self.results_stats)

        layout.addStretch()

        return tab

    # Event handlers

    def _on_add_files(self):
        """Add video files to the list."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Sélectionner des fichiers vidéo", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.flv *.wmv *.webm);;All Files (*)"
        )

        for file in files:
            if not self._file_exists_in_list(file):
                self.file_list.addItem(file)

        self._update_file_stats()

    def _on_add_folder(self):
        """Add all videos from a folder."""
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier")

        if folder:
            video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm'}
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if Path(file).suffix.lower() in video_extensions:
                        full_path = os.path.join(root, file)
                        if not self._file_exists_in_list(full_path):
                            self.file_list.addItem(full_path)

        self._update_file_stats()

    def _on_remove_file(self):
        """Remove selected file from list."""
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

        self._update_file_stats()

    def _file_exists_in_list(self, file_path: str) -> bool:
        """Check if file already in list."""
        for i in range(self.file_list.count()):
            if self.file_list.item(i).text() == file_path:
                return True
        return False

    def _update_file_stats(self):
        """Update file list statistics."""
        count = self.file_list.count()

        if self.all_pairs_radio.isChecked():
            pairs = count * (count - 1) // 2 if count > 1 else 0
        elif self.sequential_radio.isChecked():
            pairs = count - 1 if count > 1 else 0
        else:  # random
            max_pairs = count * (count - 1) // 2 if count > 1 else 0
            pairs = min(self.random_count.value(), max_pairs)

        self.file_list_stats.setText(f"Fichiers: {count} | Paires estimées: {pairs}")

    def _browse_video(self, line_edit: QLineEdit):
        """Browse for a video file."""
        file, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner une vidéo", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.flv *.wmv *.webm);;All Files (*)"
        )

        if file:
            line_edit.setText(file)

    def _on_add_manual_pair(self):
        """Add a manual pair to the table."""
        video1 = self.video1_input.text().strip()
        video2 = self.video2_input.text().strip()

        if not video1 or not video2:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner les deux vidéos")
            return

        if video1 == video2:
            QMessageBox.warning(self, "Erreur", "Les deux vidéos doivent être différentes")
            return

        # Add row to table
        row = self.manual_pairs_table.rowCount()
        self.manual_pairs_table.insertRow(row)

        self.manual_pairs_table.setItem(row, 0, QTableWidgetItem(os.path.basename(video1)))
        self.manual_pairs_table.setItem(row, 1, QTableWidgetItem(os.path.basename(video2)))
        self.manual_pairs_table.setItem(row, 2, QTableWidgetItem(self.manual_expected_combo.currentText()))
        self.manual_pairs_table.setItem(row, 3, QTableWidgetItem(self.notes_input.text()))

        # Store full paths in item data
        self.manual_pairs_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, video1)
        self.manual_pairs_table.item(row, 1).setData(Qt.ItemDataRole.UserRole, video2)

        # Remove button
        remove_btn = QPushButton("🗑️")
        remove_btn.clicked.connect(lambda: self._remove_manual_pair(row))
        self.manual_pairs_table.setCellWidget(row, 4, remove_btn)

        # Clear inputs
        self.video1_input.clear()
        self.video2_input.clear()
        self.notes_input.clear()

        self.manual_stats.setText(f"Paires: {self.manual_pairs_table.rowCount()}")

    def _remove_manual_pair(self, row: int):
        """Remove a manual pair from the table."""
        self.manual_pairs_table.removeRow(row)
        self.manual_stats.setText(f"Paires: {self.manual_pairs_table.rowCount()}")

    def _on_browse_json(self):
        """Browse for JSON file."""
        file, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner pairs.json", "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file:
            self.json_file_input.setText(file)
            self._preview_json(file)

    def _preview_json(self, file_path: str):
        """Preview JSON file content."""
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'pairs' in data:
                pairs = data['pairs']
                preview_text = f"Fichier: {os.path.basename(file_path)}\n"
                preview_text += f"Paires: {len(pairs)}\n\n"
                preview_text += "Aperçu (5 premières paires):\n"

                for i, pair in enumerate(pairs[:5]):
                    preview_text += f"\n{i+1}. {os.path.basename(pair.get('video1', 'N/A'))} ↔ {os.path.basename(pair.get('video2', 'N/A'))}\n"
                    preview_text += f"   Attendu: {pair.get('expected', 'unknown')}\n"
                    if pair.get('notes'):
                        preview_text += f"   Notes: {pair['notes']}\n"

                self.json_preview.setText(preview_text)

                # Count by expected result
                duplicates = sum(1 for p in pairs if p.get('expected') == 'duplicate')
                non_duplicates = sum(1 for p in pairs if p.get('expected') == 'not_duplicate')
                unknowns = sum(1 for p in pairs if p.get('expected') == 'unknown')

                self.import_stats.setText(
                    f"Total: {len(pairs)} paires | "
                    f"✅ Duplicata: {duplicates} | "
                    f"❌ Non-duplicata: {non_duplicates} | "
                    f"❓ Inconnu: {unknowns}"
                )
            else:
                self.json_preview.setText("Format JSON invalide: clé 'pairs' manquante")
                self.import_stats.setText("Erreur: format invalide")

        except Exception as e:
            self.json_preview.setText(f"Erreur lors de la lecture du fichier:\n{str(e)}")
            self.import_stats.setText(f"Erreur: {str(e)}")

    def _on_create(self):
        """Create the test set based on current tab."""
        test_set_name = self.test_set_name.text().strip()

        if not test_set_name:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer un nom pour le test set")
            return

        current_tab = self.tabs.currentIndex()

        try:
            if current_tab == 0:  # File list
                self._create_from_file_list(test_set_name)
            elif current_tab == 1:  # Manual
                self._create_from_manual(test_set_name)
            elif current_tab == 2:  # Import
                self._create_from_import(test_set_name)
            elif current_tab == 3:  # Results
                self._create_from_results(test_set_name)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la création du test set:\n{str(e)}")
            logger.error(f"Test set creation error: {e}", exc_info=True)

    def _create_from_file_list(self, test_set_name: str):
        """Create test set from file list."""
        file_count = self.file_list.count()

        if file_count < 2:
            QMessageBox.warning(self, "Erreur", "Il faut au moins 2 fichiers pour créer des paires")
            return

        # Get all files
        files = [self.file_list.item(i).text() for i in range(file_count)]

        # Generate pairs based on strategy
        pairs = []
        expected = self.expected_combo.currentText()

        if self.all_pairs_radio.isChecked():
            # All possible pairs
            for i in range(len(files)):
                for j in range(i + 1, len(files)):
                    pairs.append((files[i], files[j], expected, ""))

        elif self.sequential_radio.isChecked():
            # Sequential pairs
            for i in range(len(files) - 1):
                pairs.append((files[i], files[i + 1], expected, ""))

        else:  # Random pairs
            import random
            max_pairs = len(files) * (len(files) - 1) // 2
            num_pairs = min(self.random_count.value(), max_pairs)

            all_pairs = [(i, j) for i in range(len(files)) for j in range(i + 1, len(files))]
            selected_pairs = random.sample(all_pairs, num_pairs)

            for i, j in selected_pairs:
                pairs.append((files[i], files[j], expected, ""))

        # Save to database
        count = self._save_pairs(test_set_name, pairs)

        QMessageBox.information(self, "Succès", f"Test set '{test_set_name}' créé avec {count} paires")
        self.test_set_created.emit(test_set_name)
        self.accept()

    def _create_from_manual(self, test_set_name: str):
        """Create test set from manual pairs."""
        if self.manual_pairs_table.rowCount() == 0:
            QMessageBox.warning(self, "Erreur", "Aucune paire ajoutée")
            return

        pairs = []
        for row in range(self.manual_pairs_table.rowCount()):
            video1 = self.manual_pairs_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            video2 = self.manual_pairs_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
            expected = self.manual_pairs_table.item(row, 2).text()
            notes = self.manual_pairs_table.item(row, 3).text()

            pairs.append((video1, video2, expected, notes))

        count = self._save_pairs(test_set_name, pairs)

        QMessageBox.information(self, "Succès", f"Test set '{test_set_name}' créé avec {count} paires")
        self.test_set_created.emit(test_set_name)
        self.accept()

    def _create_from_import(self, test_set_name: str):
        """Create test set from imported JSON."""
        json_file = self.json_file_input.text().strip()

        if not json_file or not os.path.exists(json_file):
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un fichier JSON valide")
            return

        count = self.test_set_manager.import_from_pairs_json(json_file, test_set_name)

        QMessageBox.information(self, "Succès", f"Test set '{test_set_name}' créé avec {count} paires importées")
        self.test_set_created.emit(test_set_name)
        self.accept()

    def _create_from_results(self, test_set_name: str):
        """Create test set from analysis results."""
        # Query database for comparisons
        db = self.test_set_manager.db_manager

        pairs = []

        # Get duplicates
        if self.include_duplicates.isChecked():
            cursor = db.conn.execute("""
                SELECT c.video1_path, c.video2_path, c.similarity
                FROM video_comparisons c
                WHERE c.is_duplicate = 1
                ORDER BY c.similarity DESC
                LIMIT 500
            """)

            for video1, video2, similarity in cursor.fetchall():
                pairs.append((video1, video2, 'duplicate', f'Similarity: {similarity:.2f}%'))

        # Get non-duplicates (sample)
        if self.include_non_duplicates.isChecked():
            cursor = db.conn.execute(f"""
                SELECT c.video1_path, c.video2_path, c.similarity
                FROM video_comparisons c
                WHERE c.is_duplicate = 0
                ORDER BY RANDOM()
                LIMIT {self.non_dup_sample.value()}
            """)

            for video1, video2, similarity in cursor.fetchall():
                pairs.append((video1, video2, 'not_duplicate', f'Similarity: {similarity:.2f}%'))

        if not pairs:
            QMessageBox.warning(self, "Erreur", "Aucune comparaison trouvée dans la base de données")
            return

        count = self._save_pairs(test_set_name, pairs)

        QMessageBox.information(self, "Succès", f"Test set '{test_set_name}' créé avec {count} paires depuis les résultats")
        self.test_set_created.emit(test_set_name)
        self.accept()

    def _save_pairs(self, test_set_name: str, pairs: List[Tuple[str, str, str, str]]) -> int:
        """
        Save pairs to database.

        Args:
            test_set_name: Name of the test set
            pairs: List of (video1, video2, expected, notes) tuples

        Returns:
            Number of pairs saved
        """
        db = self.test_set_manager.db_manager
        cursor = db.conn.cursor()

        for video1, video2, expected, notes in pairs:
            cursor.execute("""
                INSERT INTO test_pairs (test_set_name, video1_path, video2_path, expected, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (test_set_name, video1, video2, expected, notes))

        db.conn.commit()
        logger.info(f"Created test set '{test_set_name}' with {len(pairs)} pairs")

        return len(pairs)
