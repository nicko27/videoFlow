"""
Éditeur d'expressions régulières avec prévisualisation en temps réel
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QCheckBox, QGroupBox,
    QPushButton, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
import re

class RegexEditorDialog(QWidget):
    """Éditeur d'expressions régulières avec validation et prévisualisation"""
    
    pattern_changed = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_pattern = None

    def setup_ui(self):
        """Configuration de l'interface utilisateur"""
        # Style global
        self.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                margin-top: 1em;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #1976d2;
                font-weight: bold;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #2196f3;
            }
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
                padding: 5px;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #bdbdbd;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #2196f3;
                border-color: #2196f3;
            }
            QCheckBox::indicator:hover {
                border-color: #1976d2;
            }
            QLabel {
                color: #424242;
            }
            QLabel[help="true"] {
                color: #757575;
                font-style: italic;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Groupe : Pattern
        pattern_group = QGroupBox("Expression régulière")
        pattern_layout = QVBoxLayout(pattern_group)
        pattern_layout.setSpacing(10)
        
        # Ligne de pattern
        pattern_input_layout = QHBoxLayout()
        pattern_label = QLabel("Pattern :")
        pattern_label.setMinimumWidth(80)
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("Entrez votre expression régulière...")
        self.pattern_input.textChanged.connect(self.validate_pattern)
        
        pattern_input_layout.addWidget(pattern_label)
        pattern_input_layout.addWidget(self.pattern_input)
        
        # Options avec icônes
        options_layout = QHBoxLayout()
        
        self.case_sensitive = QCheckBox("Sensible à la casse")
        self.case_sensitive.setChecked(True)
        self.case_sensitive.stateChanged.connect(self.validate_pattern)
        
        self.dot_matches_all = QCheckBox("Le point correspond à tout")
        self.dot_matches_all.stateChanged.connect(self.validate_pattern)
        
        options_layout.addWidget(self.case_sensitive)
        options_layout.addWidget(self.dot_matches_all)
        options_layout.addStretch()
        
        pattern_layout.addLayout(pattern_input_layout)
        pattern_layout.addLayout(options_layout)
        
        # Groupe : Remplacement
        replace_group = QGroupBox("Remplacement")
        replace_layout = QVBoxLayout(replace_group)
        replace_layout.setSpacing(10)
        
        replace_label = QLabel("Remplacer par :")
        replace_label.setMinimumWidth(80)
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Texte de remplacement...")
        self.replace_input.textChanged.connect(self.validate_pattern)
        
        replace_help = QLabel(
            "\\1, \\2, etc. : groupes capturés | \\L : minuscules | \\U : majuscules"
        )
        replace_help.setProperty("help", "true")
        
        replace_layout.addWidget(replace_label)
        replace_layout.addWidget(self.replace_input)
        replace_layout.addWidget(replace_help)
        
        # Groupe : Test
        test_group = QGroupBox("Test en direct")
        test_layout = QVBoxLayout(test_group)
        test_layout.setSpacing(10)
        
        test_label = QLabel("Texte de test :")
        self.test_input = QLineEdit()
        self.test_input.setPlaceholderText("Entrez un texte de test...")
        self.test_input.textChanged.connect(self.update_test)
        
        result_label = QLabel("Résultat :")
        self.test_result = QTextEdit()
        self.test_result.setReadOnly(True)
        self.test_result.setMaximumHeight(100)
        self.test_result.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                font-family: monospace;
            }
        """)
        
        test_layout.addWidget(test_label)
        test_layout.addWidget(self.test_input)
        test_layout.addWidget(result_label)
        test_layout.addWidget(self.test_result)
        
        # Assemblage final
        layout.addWidget(pattern_group)
        layout.addWidget(replace_group)
        layout.addWidget(test_group)
        layout.addStretch()

    def validate_pattern(self):
        """Valider le pattern et émettre le signal si valide"""
        pattern = self.pattern_input.text()
        if not pattern:
            self.pattern_changed.emit(None)
            return
        
        try:
            # Construction des flags
            flags = 0
            if not self.case_sensitive.isChecked():
                flags |= re.IGNORECASE
            if self.dot_matches_all.isChecked():
                flags |= re.DOTALL
            
            # Compilation du pattern
            regex = re.compile(pattern, flags)
            
            # Création d'un objet pattern avec toutes les infos
            pattern_obj = {
                'regex': regex,
                'pattern': pattern,
                'replace': self.replace_input.text(),
                'flags': flags
            }
            
            self.current_pattern = pattern_obj
            self.pattern_changed.emit(pattern_obj)
            self.update_test()
            
            # Style normal
            self.pattern_input.setStyleSheet("")
            
        except re.error:
            # Style d'erreur
            self.pattern_input.setStyleSheet("background-color: #ffebee;")
            self.pattern_changed.emit(None)

    def update_test(self):
        """Mettre à jour le résultat du test"""
        if not self.current_pattern:
            self.test_result.setText("Pattern invalide")
            return
        
        test_text = self.test_input.text()
        if not test_text:
            self.test_result.setText("Entrez un texte de test")
            return
        
        try:
            # Test de la correspondance
            regex = self.current_pattern['regex']
            replace = self.current_pattern['replace']
            
            # Afficher les groupes capturés
            matches = regex.finditer(test_text)
            result = []
            
            for match in matches:
                result.append(f"Trouvé : {match.group(0)}")
                for i, group in enumerate(match.groups(), 1):
                    result.append(f"  Groupe {i}: {group}")
            
            # Afficher le résultat du remplacement
            if replace:
                final = regex.sub(replace, test_text)
                result.append("\nRemplacement :")
                result.append(final)
            
            self.test_result.setText("\n".join(result) if result else "Aucune correspondance")
            
        except Exception as e:
            self.test_result.setText(f"Erreur : {str(e)}")

    def set_pattern(self, pattern_obj):
        """Définir un pattern existant"""
        if not pattern_obj:
            return
            
        self.pattern_input.setText(pattern_obj['pattern'])
        self.replace_input.setText(pattern_obj.get('replace', ''))
        
        # Configuration des flags
        flags = pattern_obj.get('flags', 0)
        self.case_sensitive.setChecked(not bool(flags & re.IGNORECASE))
        self.dot_matches_all.setChecked(bool(flags & re.DOTALL))
