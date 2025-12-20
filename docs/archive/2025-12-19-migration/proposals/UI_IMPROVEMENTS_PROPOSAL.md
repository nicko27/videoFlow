# Propositions d'Améliorations UI - DuplicateFinder

**Date** : 2025-12-18
**Objectif** : Intégrer les nouvelles fonctionnalités DuplicateFlow dans l'UI existante

---

## 🎯 Nouvelles Fonctionnalités à Intégrer

1. ✅ **Validateurs** (LengthValidator)
2. ✅ **Analyse Partielle** (analyze_duration, analyze_from_start)
3. ✅ **Presets avec Validateurs** (fast_duplicates, accurate_scenes, etc.)
4. ✅ **PipelineStore** (save/load pipelines personnalisés)

---

## 📊 Analyse UI Existante

### Fichiers Clés Identifiés

| Fichier | Fonction | Priorité |
|---------|----------|----------|
| `unified_pipeline_editor_dialog.py` | Éditeur de pipeline principal | 🔴 Haute |
| `pipeline_config_widget.py` | Configuration pipeline inline | 🔴 Haute |
| `pipeline_library_dialog.py` | Bibliothèque pipelines | 🟡 Moyenne |
| `settings_dialog.py` | Paramètres généraux | 🟢 Basse |
| `panels.py` | Panneaux de résultats | 🟡 Moyenne |

### Architecture Actuelle

```
Interface Utilisateur
├── unified_pipeline_editor_dialog.py
│   └── Édition complète de pipeline
│       ├── Sélection algorithmes
│       ├── Configuration paramètres
│       └── Poids et ordre
│
├── pipeline_library_dialog.py
│   └── Bibliothèque de pipelines sauvegardés
│
└── main_window.py
    └── Interface principale
        ├── Onglets de configuration
        └── Résultats
```

---

## 🎨 Propositions d'Amélioration

### 1. Améliorer `unified_pipeline_editor_dialog.py`

#### A. Ajouter Section "Validation"

**Emplacement** : Après la section "Algorithmes"

**UI Proposée** :

```
┌─────────────────────────────────────────────────────────┐
│ 📋 Étape 1 : Algorithmes                     [...]      │
├─────────────────────────────────────────────────────────┤
│ ✅ Étape 2 : Validation (Nouveau!)                      │
│                                                          │
│ Les validateurs filtrent les vidéos AVANT la comparaison│
│ pour économiser du temps de calcul.                     │
│                                                          │
│ ┌─ Validation de Longueur ──────────────────────────┐   │
│ │ ☑ Activer la validation de longueur              │   │
│ │                                                    │   │
│ │ Tolérance en pourcentage: [5.0] %                 │   │
│ │ Tolérance en secondes:    [30.0] s                │   │
│ │                                                    │   │
│ │ Logique: ◉ OU (l'une ou l'autre)                 │   │
│ │          ○ ET (les deux doivent passer)           │   │
│ │                                                    │   │
│ │ Exemples testés :                                 │   │
│ │ • Vidéos 100s vs 103s → ✓ PASS (3s, 3%)         │   │
│ │ • Vidéos 100s vs 140s → ✗ FAIL (40s, 40%)       │   │
│ │ • Vidéos 600s vs 625s → ✓ PASS (25s, 4.2%)      │   │
│ └────────────────────────────────────────────────────┘   │
│                                                          │
│ [ + Ajouter autre validateur ]                          │
└─────────────────────────────────────────────────────────┘
```

**Code à Ajouter** :

```python
class ValidatorConfigWidget(QWidget):
    """Widget de configuration des validateurs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # En-tête
        header = QLabel("✅ Validation")
        header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(header)

        info = QLabel(
            "Les validateurs filtrent les paires de vidéos AVANT la comparaison.\n"
            "Cela économise du temps en évitant des calculs inutiles."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #6C757D; font-size: 10px;")
        layout.addWidget(info)

        # Groupe Length Validator
        length_group = QGroupBox("Validation de Longueur")
        length_layout = QVBoxLayout()

        # Enable checkbox
        self.length_enabled = QCheckBox("Activer la validation de longueur")
        self.length_enabled.setChecked(False)
        self.length_enabled.toggled.connect(self._on_length_toggled)
        length_layout.addWidget(self.length_enabled)

        # Configuration
        config_widget = QWidget()
        config_layout = QFormLayout(config_widget)

        self.tolerance_percent = QDoubleSpinBox()
        self.tolerance_percent.setRange(0.0, 100.0)
        self.tolerance_percent.setValue(5.0)
        self.tolerance_percent.setSuffix(" %")
        self.tolerance_percent.setToolTip(
            "Différence maximale acceptable en pourcentage.\n"
            "Ex: 5% → vidéos de 100s et 105s sont acceptées."
        )
        config_layout.addRow("Tolérance %:", self.tolerance_percent)

        self.tolerance_seconds = QDoubleSpinBox()
        self.tolerance_seconds.setRange(0.0, 3600.0)
        self.tolerance_seconds.setValue(30.0)
        self.tolerance_seconds.setSuffix(" s")
        self.tolerance_seconds.setToolTip(
            "Différence maximale acceptable en secondes.\n"
            "Ex: 30s → vidéos de 100s et 130s sont acceptées."
        )
        config_layout.addRow("Tolérance s:", self.tolerance_seconds)

        # Logic selector
        logic_widget = QWidget()
        logic_layout = QHBoxLayout(logic_widget)
        logic_layout.setContentsMargins(0, 0, 0, 0)

        self.logic_or = QRadioButton("OU (l'une ou l'autre)")
        self.logic_and = QRadioButton("ET (les deux)")
        self.logic_or.setChecked(True)
        self.logic_or.setToolTip("Accepter si l'une OU l'autre tolérance est respectée")
        self.logic_and.setToolTip("Accepter si les DEUX tolérances sont respectées")

        logic_layout.addWidget(self.logic_or)
        logic_layout.addWidget(self.logic_and)
        config_layout.addRow("Logique:", logic_widget)

        # Examples
        examples = QLabel(
            "<b>Exemples testés :</b><br>"
            "• 100s vs 103s → <span style='color:green'>✓ PASS</span> (3s, 3%)<br>"
            "• 100s vs 140s → <span style='color:red'>✗ FAIL</span> (40s, 40%)<br>"
            "• 600s vs 625s → <span style='color:green'>✓ PASS</span> (25s, 4.2%)"
        )
        examples.setWordWrap(True)
        examples.setStyleSheet("color: #6C757D; font-size: 9px; padding: 5px;")
        config_layout.addRow("", examples)

        config_widget.setEnabled(False)
        self.config_widget = config_widget

        length_layout.addWidget(config_widget)
        length_group.setLayout(length_layout)
        layout.addWidget(length_group)

        # Bouton ajouter autre validateur (pour futur)
        add_btn = QPushButton("+ Ajouter autre validateur")
        add_btn.setEnabled(False)
        add_btn.setToolTip("Fonctionnalité à venir")
        layout.addWidget(add_btn)

    def _on_length_toggled(self, checked):
        """Enable/disable config when checkbox toggled."""
        self.config_widget.setEnabled(checked)

    def get_validators_config(self):
        """Get validators configuration for pipeline."""
        validators = []

        if self.length_enabled.isChecked():
            validators.append({
                'type': 'LengthValidator',
                'config': {
                    'tolerance_percent': self.tolerance_percent.value(),
                    'tolerance_seconds': self.tolerance_seconds.value(),
                    'require_both': self.logic_and.isChecked()
                }
            })

        return validators

    def set_validators_config(self, validators):
        """Load validators from config."""
        for validator in validators:
            if validator['type'] == 'LengthValidator':
                self.length_enabled.setChecked(True)
                config = validator.get('config', {})
                self.tolerance_percent.setValue(config.get('tolerance_percent', 5.0))
                self.tolerance_seconds.setValue(config.get('tolerance_seconds', 30.0))
                self.logic_and.setChecked(config.get('require_both', False))
                self.logic_or.setChecked(not config.get('require_both', False))
```

---

#### B. Ajouter Section "Analyse Partielle"

**UI Proposée** :

```
┌─────────────────────────────────────────────────────────┐
│ ⚡ Étape 3 : Optimisation (Nouveau!)                    │
│                                                          │
│ L'analyse partielle permet de comparer seulement une    │
│ partie des vidéos au lieu de la vidéo complète.         │
│                                                          │
│ ┌─ Analyse Partielle ───────────────────────────────┐   │
│ │ ☑ Activer l'analyse partielle                     │   │
│ │                                                    │   │
│ │ Durée à analyser: [60] secondes                   │   │
│ │                                                    │   │
│ │ Position:  ◉ Début de la vidéo                    │   │
│ │            ○ Fin de la vidéo                       │   │
│ │                                                    │   │
│ │ 💡 Gain de performance estimé :                   │   │
│ │    Vidéo 10 min : ~90% plus rapide                │   │
│ │    Vidéo 1 heure : ~98% plus rapide               │   │
│ │                                                    │   │
│ │ ⚠️ À utiliser pour :                              │   │
│ │   ✓ Détection de duplicatas complets              │   │
│ │   ✓ Détection d'intros/génériques                 │   │
│ │   ✗ Détection de scènes (analyser tout)           │   │
│ └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Code à Ajouter** :

```python
class PartialAnalysisWidget(QWidget):
    """Widget de configuration analyse partielle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # En-tête
        header = QLabel("⚡ Optimisation")
        header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(header)

        info = QLabel(
            "L'analyse partielle permet d'analyser seulement une portion de chaque vidéo.\n"
            "Gain de performance : 90-98% pour les vidéos longues !"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #6C757D; font-size: 10px;")
        layout.addWidget(info)

        # Groupe Partial Analysis
        partial_group = QGroupBox("Analyse Partielle")
        partial_layout = QVBoxLayout()

        # Enable checkbox
        self.partial_enabled = QCheckBox("Activer l'analyse partielle")
        self.partial_enabled.setChecked(False)
        self.partial_enabled.toggled.connect(self._on_partial_toggled)
        partial_layout.addWidget(self.partial_enabled)

        # Configuration
        config_widget = QWidget()
        config_layout = QFormLayout(config_widget)

        self.duration = QDoubleSpinBox()
        self.duration.setRange(1.0, 3600.0)
        self.duration.setValue(60.0)
        self.duration.setSuffix(" s")
        self.duration.setToolTip(
            "Durée à analyser (en secondes).\n"
            "Ex: 60 → analyser seulement 60 premières secondes"
        )
        config_layout.addRow("Durée:", self.duration)

        # Position selector
        position_widget = QWidget()
        position_layout = QVBoxLayout(position_widget)
        position_layout.setContentsMargins(0, 0, 0, 0)

        self.pos_start = QRadioButton("Début de la vidéo")
        self.pos_end = QRadioButton("Fin de la vidéo")
        self.pos_start.setChecked(True)
        self.pos_start.setToolTip("Analyser depuis le début (pour duplicatas/intros)")
        self.pos_end.setToolTip("Analyser depuis la fin (pour génériques)")

        position_layout.addWidget(self.pos_start)
        position_layout.addWidget(self.pos_end)
        config_layout.addRow("Position:", position_widget)

        # Performance info
        perf = QLabel(
            "<b>💡 Gain de performance estimé :</b><br>"
            "• Vidéo 10 min : ~90% plus rapide<br>"
            "• Vidéo 1 heure : ~98% plus rapide"
        )
        perf.setWordWrap(True)
        perf.setStyleSheet("color: #28A745; font-size: 9px; padding: 5px;")
        config_layout.addRow("", perf)

        # Warnings
        warning = QLabel(
            "<b>⚠️ À utiliser pour :</b><br>"
            "<span style='color:green'>✓ Détection de duplicatas complets</span><br>"
            "<span style='color:green'>✓ Détection d'intros/génériques</span><br>"
            "<span style='color:red'>✗ Détection de scènes (analyser tout)</span>"
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("font-size: 9px; padding: 5px;")
        config_layout.addRow("", warning)

        config_widget.setEnabled(False)
        self.config_widget = config_widget

        partial_layout.addWidget(config_widget)
        partial_group.setLayout(partial_layout)
        layout.addWidget(partial_group)

    def _on_partial_toggled(self, checked):
        """Enable/disable config when checkbox toggled."""
        self.config_widget.setEnabled(checked)

    def get_partial_config(self):
        """Get partial analysis configuration."""
        if not self.partial_enabled.isChecked():
            return {
                'analyze_duration': None,
                'analyze_from_start': True
            }

        return {
            'analyze_duration': self.duration.value(),
            'analyze_from_start': self.pos_start.isChecked()
        }

    def set_partial_config(self, config):
        """Load partial analysis from config."""
        analyze_duration = config.get('analyze_duration')

        if analyze_duration is not None:
            self.partial_enabled.setChecked(True)
            self.duration.setValue(analyze_duration)
            analyze_from_start = config.get('analyze_from_start', True)
            self.pos_start.setChecked(analyze_from_start)
            self.pos_end.setChecked(not analyze_from_start)
        else:
            self.partial_enabled.setChecked(False)
```

---

### 2. Améliorer `pipeline_library_dialog.py`

#### Intégrer PipelineStore

**Objectif** : Remplacer ou compléter le système actuel avec PipelineStore

**Modifications** :

```python
from duplicateflow.storage import PipelineStore

class PipelineLibraryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Ajouter PipelineStore
        self.pipeline_store = PipelineStore()
        self._init_ui()

    def _load_pipelines(self):
        """Load pipelines from both sources."""
        # 1. Charger depuis PipelineStore (DuplicateFlow)
        df_pipelines = self.pipeline_store.list()

        # 2. Charger depuis système existant (duplicate_finder)
        local_pipelines = self._load_local_pipelines()

        # 3. Merger et afficher
        all_pipelines = df_pipelines + local_pipelines
        self._display_pipelines(all_pipelines)

    def _display_pipelines(self, pipelines):
        """Display with badges to show source."""
        for pipeline in pipelines:
            item = QListWidgetItem()

            # Badge selon la source
            if 'source' in pipeline and pipeline['source'] == 'duplicateflow':
                badge = "🔷 DF"  # DuplicateFlow
            else:
                badge = "📁 Local"

            # Badge pour nouveaux presets
            if pipeline.get('category') == 'preset_new':
                badge += " ✨ Nouveau"

            item.setText(f"{badge} {pipeline['name']}")
            item.setData(Qt.ItemDataRole.UserRole, pipeline)
            self.pipeline_list.addItem(item)
```

---

### 3. Ajouter Presets Raccourcis

**UI Proposée** : Boutons rapides dans l'interface principale

```
┌─────────────────────────────────────────────────────────┐
│ 🚀 Presets Rapides (Nouveau!)                           │
│                                                          │
│ [⚡ Duplicatas Rapides] [🎬 Scènes Précises]            │
│ [🎵 Intros]             [🎬 Génériques]                  │
│                                                          │
│ 💡 Ces presets utilisent les dernières optimisations!   │
└─────────────────────────────────────────────────────────┘
```

**Code** :

```python
class PresetsQuickPanel(QWidget):
    """Panel with quick access to new presets."""

    preset_selected = pyqtSignal(str)  # Emit preset name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("🚀 Presets Rapides")
        header.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        layout.addWidget(header)

        info = QLabel("Ces presets utilisent les dernières optimisations!")
        info.setStyleSheet("color: #6C757D; font-size: 9px;")
        layout.addWidget(info)

        # Grid de boutons
        grid = QGridLayout()

        presets = [
            ("⚡ Duplicatas Rapides", "fast_duplicates", "Validation + 60s analyse"),
            ("🎬 Scènes Précises", "accurate_scenes", "Validation stricte + analyse complète"),
            ("🎵 Intros", "intro_detector", "Analyse 45 premières secondes"),
            ("🎬 Génériques", "credits_detector", "Analyse 30 dernières secondes"),
        ]

        for i, (label, preset_name, tooltip) in enumerate(presets):
            btn = QPushButton(label)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda checked, p=preset_name: self.preset_selected.emit(p))
            grid.addWidget(btn, i // 2, i % 2)

        layout.addLayout(grid)
```

---

### 4. Affichage Résultats avec Métadonnées Validation

**Objectif** : Montrer si une paire a été rejetée par validation

**UI Proposée** :

```
┌─────────────────────────────────────────────────────────┐
│ Résultat Comparaison                                     │
│                                                          │
│ ❌ REJETÉ PAR VALIDATION                                │
│                                                          │
│ Validateur : LengthValidator                             │
│ Raison : Exceeded both tolerances                        │
│                                                          │
│ Détails :                                                │
│ • Durée vidéo 1 : 120.5 s                               │
│ • Durée vidéo 2 : 180.0 s                               │
│ • Différence : 59.5 s (49.5%)                           │
│ • Tolérance : ±5% OU ±30s                               │
│                                                          │
│ 💡 Ces vidéos ont été filtrées AVANT la comparaison     │
│    pour économiser du temps de calcul.                   │
└─────────────────────────────────────────────────────────┘
```

**Code** :

```python
def display_result(self, result):
    """Display result with validation info."""

    # Check for pre-validation failure
    if result.get('metadata', {}).get('pre_validation_failed'):
        self._display_validation_rejection(result)
        return

    # Normal result display
    self._display_normal_result(result)

def _display_validation_rejection(self, result):
    """Display validation rejection info."""
    validation_results = result['metadata']['pre_validation_results']

    text = "❌ REJETÉ PAR VALIDATION\n\n"

    for val_result in validation_results:
        if not val_result['passed']:
            text += f"Validateur : {val_result['validator']}\n"

            meta = val_result['metadata']
            text += f"Raison : {meta.get('reason', 'N/A')}\n\n"

            if 'length_diff_seconds' in meta:
                text += "Détails :\n"
                text += f"• Durée vidéo 1 : {meta['duration1']:.1f} s\n"
                text += f"• Durée vidéo 2 : {meta['duration2']:.1f} s\n"
                text += f"• Différence : {meta['length_diff_seconds']:.1f} s ({meta['length_diff_percent']:.1f}%)\n"
                text += f"• Tolérance : ±{meta['tolerance_percent']}% "

                if meta['require_both']:
                    text += f"ET ±{meta['tolerance_seconds']}s\n"
                else:
                    text += f"OU ±{meta['tolerance_seconds']}s\n"

    text += "\n💡 Ces vidéos ont été filtrées AVANT la comparaison\n"
    text += "   pour économiser du temps de calcul."

    self.result_text.setText(text)
```

---

## 📋 Plan d'Implémentation

### Phase 1 : Modifications Minimales (1-2 jours)
1. ✅ Ajouter ValidatorConfigWidget
2. ✅ Ajouter PartialAnalysisWidget
3. ✅ Intégrer dans unified_pipeline_editor_dialog
4. ✅ Afficher métadonnées validation dans résultats

### Phase 2 : Intégration PipelineStore (2-3 jours)
1. Modifier pipeline_library_dialog pour utiliser PipelineStore
2. Ajouter boutons import/export
3. Ajouter statistiques d'utilisation

### Phase 3 : Presets Rapides (1 jour)
1. Créer PresetsQuickPanel
2. Intégrer dans main_window
3. Connecter aux presets DuplicateFlow

### Phase 4 : Tests & Polish (1-2 jours)
1. Tests manuels avec vidéos réelles
2. Ajustements UI/UX
3. Documentation utilisateur

**Total Estimé** : 5-8 jours

---

## 🎯 Bénéfices Utilisateur

### Avant
- Configuration manuelle complexe
- Pas de filtrage pré-comparaison
- Analyse toujours complète (lent)
- Pipelines perdus entre sessions

### Après
- ✅ Presets rapides en 1 clic
- ✅ Validation automatique (économie 20%+ de temps)
- ✅ Analyse partielle (90%+ plus rapide)
- ✅ Pipelines sauvegardés et réutilisables
- ✅ Feedback visuel sur rejets validation

---

## 📝 Fichiers à Modifier

### Nouveaux Fichiers
1. `ui/widgets/validator_config_widget.py` (ValidatorConfigWidget)
2. `ui/widgets/partial_analysis_widget.py` (PartialAnalysisWidget)
3. `ui/widgets/presets_quick_panel.py` (PresetsQuickPanel)

### Fichiers à Modifier
1. `ui/unified_pipeline_editor_dialog.py` (+100 lignes)
2. `ui/pipeline_library_dialog.py` (+50 lignes)
3. `ui/panels.py` (+50 lignes - affichage résultats)
4. `ui/main_window.py` (+30 lignes - presets panel)

**Total** : ~400 lignes de code UI

---

## 🚀 Recommandations Prioritaires

### MUST HAVE (Phase 1)
1. **ValidatorConfigWidget** : Essentiel pour utiliser LengthValidator
2. **PartialAnalysisWidget** : Gain de performance majeur
3. **Affichage validation** : UX clarity

### SHOULD HAVE (Phase 2-3)
4. **PipelineStore integration** : Réutilisabilité
5. **Presets rapides** : Accessibilité

### NICE TO HAVE (Phase 4)
6. **Statistiques d'utilisation** : Analytics
7. **Import/Export JSON** : Partage

---

## 💡 Notes d'Implémentation

### Compatibilité
- ✅ Rétrocompatible avec pipelines existants
- ✅ Widgets optionnels (peuvent être désactivés)
- ✅ Pas de breaking changes

### Performance
- ✅ Pas d'impact sur performance existante
- ✅ Gains importants avec nouvelles fonctionnalités
- ✅ UI réactive (widgets légers)

### Maintenabilité
- ✅ Code modulaire (widgets séparés)
- ✅ Documentation inline
- ✅ Tests unitaires possibles

---

**Date** : 2025-12-18
**Prêt pour implémentation** : ✅ OUI
