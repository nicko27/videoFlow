# Proposition Nouvelle Interface - Onglet Paramètres

**Date**: 2025-12-19
**Objectif**: Interface moderne, épurée, 100% DuplicateFlow

---

## 🎨 Maquette Visuelle

```
┌─────────────────────────────────────────────────────────────────────┐
│ ⚙️ PARAMÈTRES                                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 🚀 Quick Presets                                                │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │                                                                 │ │
│ │  [⚡ Maximum Speed]    [⚖️ Balanced (Recommended)]              │ │
│ │                                                                 │ │
│ │  [🎯 Maximum Quality]                                           │ │
│ │                                                                 │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 🎯 Pipeline DuplicateFlow                                       │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │                                                                 │ │
│ │  Pipeline: [⭐ fast (DuplicateFlow)          ▼] [✏️] [➕]      │ │
│ │                                                                 │ │
│ │  ┌──────────────────────────────────────────────────────────┐  │ │
│ │  │ 📝 Description: Détection rapide de duplicatas           │  │ │
│ │  │                                                          │  │ │
│ │  │ 🔧 Configuration:                                        │  │ │
│ │  │  • Mode: weighting                                       │  │ │
│ │  │  • Algorithmes: 3 (frame_hash, color_histogram, ...)    │  │ │
│ │  │                                                          │  │ │
│ │  │ ⚡ Optimisations:                                        │  │ │
│ │  │  • Validation longueur: OFF                              │  │ │
│ │  │  • Analyse partielle: OFF (analyse complète)             │  │ │
│ │  └──────────────────────────────────────────────────────────┘  │ │
│ │                                                                 │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ ⚙️ Options Avancées                              [▼ Replier]    │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │                                                                 │ │
│ │  ☐ Activer le mode debug (logs détaillés)                      │ │
│ │                                                                 │ │
│ │  Nombre de threads: [●─────────────] Auto (10 threads)         │ │
│ │                                                                 │ │
│ │  Cache vidéo: [●─────────────] 1000 MB                         │ │
│ │                                                                 │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│                                                                     │
│                                                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Sections (De haut en bas)

### 1. 🚀 Quick Presets
**Hauteur**: ~120px
**Contenu**:
```python
- ⚡ Maximum Speed
- ⚖️ Balanced (Recommended)
- 🎯 Maximum Quality
```

**Fonction**: Application rapide de configurations prédéfinies

**Statut**: ✅ **GARDER** - Très utile pour débutants

---

### 2. 🎯 Pipeline DuplicateFlow
**Hauteur**: ~250px
**Contenu**:

#### A. Ligne de sélection (40px)
```
Pipeline: [ComboBox avec tous pipelines ▼] [✏️ Éditer] [➕ Nouveau]
```

#### B. Carte de description (200px)
**Design moderne avec sections visuelles**:

```
┌────────────────────────────────────────────────┐
│ 📝 Description: Détection rapide de duplicatas │
│                                                │
│ 🔧 Configuration:                              │
│  • Mode: weighting                             │
│  • Algorithmes: 3 (frame_hash, color_...)     │
│                                                │
│ ⚡ Optimisations:                              │
│  • Validation longueur: OFF                    │
│  • Analyse partielle: OFF (analyse complète)   │
└────────────────────────────────────────────────┘
```

**Améliorations par rapport à l'actuel**:
1. **Icônes visuelles**: 📝 🔧 ⚡ pour structure claire
2. **Sections séparées**: Description / Configuration / Optimisations
3. **Info complète**: Montre mode + nombre d'algos + optimisations
4. **Couleur de fond**: Légèrement grisée (#f8f9fa) pour contraste

**Code Update Nécessaire**:
```python
def update_description(index):
    if index >= 0:
        pipeline_data = pipeline_combo.itemData(index)
        if pipeline_data:
            desc = pipeline_data.get('description', 'Aucune description')
            mode = pipeline_data.get('mode', 'unknown')
            methods = pipeline_data.get('methods', [])
            methods_count = len(methods)

            # Liste des noms d'algorithmes (premiers 3 si > 3)
            algo_names = [m.get('name', '?') for m in methods[:3]]
            if methods_count > 3:
                algo_names_str = ', '.join(algo_names) + f', +{methods_count-3} autres'
            else:
                algo_names_str = ', '.join(algo_names)

            # DuplicateFlow config
            df_config = pipeline_data.get('duplicateflow_config') or {}
            features = []

            # Validation
            if df_config.get('pre_validators'):
                val = df_config['pre_validators'][0]
                val_config = val.get('config', {})
                tol_pct = val_config.get('tolerance_percent')
                tol_sec = val_config.get('tolerance_seconds')
                parts = []
                if tol_pct: parts.append(f"±{tol_pct}%")
                if tol_sec: parts.append(f"±{tol_sec}s")
                features.append(f"✓ Validation longueur: {' / '.join(parts)}")
            else:
                features.append("✓ Validation longueur: OFF")

            # Analyse partielle
            if df_config.get('analyze_duration'):
                duration = df_config['analyze_duration']
                from_where = "début" if df_config.get('analyze_from_start', True) else "fin"
                features.append(f"⚡ Analyse partielle: {duration:.0f}s depuis {from_where}")
            else:
                features.append("⚡ Analyse partielle: OFF (analyse complète)")

            # Construire le texte enrichi
            info_html = f"""
            <div style='padding: 10px; background: #f8f9fa; border-radius: 6px;'>
                <p style='margin: 5px 0;'><b>📝 Description:</b> {desc}</p>

                <p style='margin: 10px 0 5px 0;'><b>🔧 Configuration:</b></p>
                <ul style='margin: 0; padding-left: 25px;'>
                    <li><b>Mode:</b> {mode}</li>
                    <li><b>Algorithmes:</b> {methods_count} ({algo_names_str})</li>
                </ul>

                <p style='margin: 10px 0 5px 0;'><b>⚡ Optimisations:</b></p>
                <ul style='margin: 0; padding-left: 25px;'>
                    <li>{features[0]}</li>
                    <li>{features[1]}</li>
                </ul>
            </div>
            """

            pipeline_desc_label.setText(info_html)
```

**Statut**: ✅ **GARDER ET AMÉLIORER** - Essentiel

---

### 3. ⚙️ Options Avancées (Repliable)
**Hauteur**: ~150px (replié: 35px)
**Contenu**:

```python
☐ Activer le mode debug (logs détaillés)

Nombre de threads: [Slider] Auto (10 threads)

Cache vidéo: [Slider] 1000 MB
```

**Nouvelles options proposées**:
1. **Mode debug**: Active logs verbeux dans console
2. **Nombre de threads**: Contrôle parallélisation (auto = CPU count)
3. **Cache vidéo**: Limite mémoire cache (défaut: 1000 MB)

**Design**:
- Section **repliable** par défaut (icône ▼/▲)
- Bordure pointillée pour indiquer "avancé"
- Tooltip sur chaque option

**Statut**: ✅ **NOUVEAU** - Options générales utiles

---

## ❌ Sections à SUPPRIMER

### 1. ~~Language Selector~~
**Lignes**: 333-339
**Raison**: Commenté comme "managed globally", pas utilisé

### 2. ~~LSH (DuplicateFlow Fingerprint Mode)~~
**Lignes**: 465-512
**Raison**:
- DuplicateFlow ne l'utilise pas dans ses presets
- Pas de support LSH dans les algorithmes DuplicateFlow
- Complexité inutile pour l'utilisateur

### 3. ~~Multi-resolution Comparison~~
**Lignes**: ~515-702
**Raison**: Géré automatiquement par algorithmes DuplicateFlow (color_histogram, etc.)

### 4. ~~Video Hashing & Comparison~~
**Lignes**: ~705-755
**Raison**: Géré par `frame_hash` de DuplicateFlow

### 5. ~~Flip Detection~~
**Lignes**: ~758-826
**Raison**:
- `frame_hash` a son propre paramètre de flip dans `params`
- Pas besoin d'option globale

### 6. ~~Audio Fingerprint Filtering~~
**Lignes**: ~829-1353
**Raison**: Remplacé par `df_audio_fingerprint` dans pipelines

---

## 📊 Comparaison Avant/Après

| Métrique | Avant | Après | Réduction |
|----------|-------|-------|-----------|
| Lignes de code | ~1200 | ~350 | **-70%** |
| Sections | 8 | 3 | **-62%** |
| Widgets | ~45 | ~12 | **-73%** |
| Hauteur scroll | ~2500px | ~600px | **-76%** |

---

## 🎨 Palette de Couleurs

```python
# Presets buttons
SPEED_COLOR = "#DC3545"      # Rouge
BALANCED_COLOR = "#007BFF"   # Bleu
QUALITY_COLOR = "#28A745"    # Vert

# Pipeline section
PIPELINE_BG = "#FFFFFF"      # Blanc
DESCRIPTION_BG = "#F8F9FA"   # Gris très clair
BORDER_COLOR = "#DEE2E6"     # Gris bordure

# Advanced section
ADVANCED_BG = "#FFFBF0"      # Jaune très pâle
ADVANCED_BORDER = "#E0D0B0"  # Beige (pointillé)

# Icons colors
ICON_DESCRIPTION = "#6C757D" # Gris moyen
ICON_CONFIG = "#007BFF"      # Bleu
ICON_OPTIM = "#FFC107"       # Jaune/Orange
```

---

## 💻 Code Structure Proposé

```python
def _create_parameters_tab(callbacks, db_manager=None, pipeline_manager=None):
    tab = QWidget()
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)

    content_widget = QWidget()
    layout = QVBoxLayout(content_widget)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(15)

    # ══════════════════════════════════════════════════════
    # 1. QUICK PRESETS
    # ══════════════════════════════════════════════════════
    presets_group = _create_quick_presets_section(callbacks)
    layout.addWidget(presets_group)

    # ══════════════════════════════════════════════════════
    # 2. PIPELINE DUPLICATEFLOW
    # ══════════════════════════════════════════════════════
    pipeline_group, pipeline_widgets = _create_pipeline_section(pipeline_manager)
    layout.addWidget(pipeline_group)

    # Store references
    tab.pipeline_combo = pipeline_widgets['combo']
    tab.edit_pipeline_btn = pipeline_widgets['edit_btn']
    tab.new_pipeline_btn = pipeline_widgets['new_btn']
    tab.pipeline_desc_label = pipeline_widgets['desc_label']

    # ══════════════════════════════════════════════════════
    # 3. ADVANCED OPTIONS (Collapsible)
    # ══════════════════════════════════════════════════════
    advanced_group, advanced_widgets = _create_advanced_section()
    layout.addWidget(advanced_group)

    # Store advanced references
    tab.debug_mode_checkbox = advanced_widgets['debug_checkbox']
    tab.thread_count_slider = advanced_widgets['thread_slider']
    tab.cache_size_slider = advanced_widgets['cache_slider']

    # Spacer to push everything to top
    layout.addStretch()

    scroll_area.setWidget(content_widget)

    # Tab layout
    tab_layout = QVBoxLayout(tab)
    tab_layout.setContentsMargins(0, 0, 0, 0)
    tab_layout.addWidget(scroll_area)

    return tab

def _create_quick_presets_section(callbacks):
    """Create the quick presets section."""
    group = QGroupBox("🚀 Quick Presets")
    layout = QGridLayout(group)
    layout.setSpacing(10)

    # Speed button
    speed_btn = QPushButton("⚡ Maximum Speed")
    speed_btn.setMinimumHeight(35)
    speed_btn.setStyleSheet(_get_button_style("#DC3545", "#A71E2A"))
    speed_btn.clicked.connect(lambda: callbacks['apply_preset']("maximum_speed"))
    speed_btn.setToolTip("Toutes les optimisations activées, vitesse maximale")

    # Balanced button
    balanced_btn = QPushButton("⚖️ Balanced (Recommended)")
    balanced_btn.setMinimumHeight(35)
    balanced_btn.setStyleSheet(_get_button_style("#007BFF", "#0056B3"))
    balanced_btn.clicked.connect(lambda: callbacks['apply_preset']("balanced"))
    balanced_btn.setToolTip("Meilleur équilibre vitesse/précision (Recommandé)")

    # Quality button
    quality_btn = QPushButton("🎯 Maximum Quality")
    quality_btn.setMinimumHeight(35)
    quality_btn.setStyleSheet(_get_button_style("#28A745", "#1E7E34"))
    quality_btn.clicked.connect(lambda: callbacks['apply_preset']("maximum_quality"))
    quality_btn.setToolTip("Toutes les comparaisons, précision maximale")

    layout.addWidget(speed_btn, 0, 0)
    layout.addWidget(balanced_btn, 0, 1)
    layout.addWidget(quality_btn, 1, 0, 1, 2)

    return group

def _create_pipeline_section(pipeline_manager):
    """Create the DuplicateFlow pipeline section."""
    group = QGroupBox("🎯 Pipeline DuplicateFlow")
    layout = QVBoxLayout(group)
    layout.setSpacing(10)

    # Selection row
    selection_layout = QHBoxLayout()

    combo = QComboBox()
    combo.setMinimumHeight(35)
    combo.setObjectName("pipeline_combo")
    combo.setToolTip("Sélectionnez un pipeline de détection DuplicateFlow")

    # Load pipelines
    if pipeline_manager:
        pipelines = pipeline_manager.list_pipelines(include_defaults=True)
        for pipeline in pipelines:
            display_name = pipeline['name']
            if pipeline.get('is_default'):
                display_name = f"⭐ {display_name}"
            combo.addItem(display_name, userData=pipeline)

    selection_layout.addWidget(QLabel("Pipeline:"), 0)
    selection_layout.addWidget(combo, 1)

    # Edit button
    edit_btn = QPushButton("✏️")
    edit_btn.setMinimumHeight(35)
    edit_btn.setMaximumWidth(45)
    edit_btn.setStyleSheet(_get_button_style("#007BFF", "#0056B3"))
    edit_btn.setToolTip("Modifier le pipeline sélectionné")
    selection_layout.addWidget(edit_btn)

    # New button
    new_btn = QPushButton("➕")
    new_btn.setMinimumHeight(35)
    new_btn.setMaximumWidth(45)
    new_btn.setStyleSheet(_get_button_style("#28A745", "#1E7E34"))
    new_btn.setToolTip("Créer un nouveau pipeline")
    selection_layout.addWidget(new_btn)

    layout.addLayout(selection_layout)

    # Description label (rich HTML)
    desc_label = QLabel()
    desc_label.setWordWrap(True)
    desc_label.setTextFormat(Qt.TextFormat.RichText)
    desc_label.setStyleSheet("""
        QLabel {
            padding: 10px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
        }
    """)

    # Update function (NEW - enriched version)
    def update_description(index):
        if index >= 0:
            pipeline_data = combo.itemData(index)
            if pipeline_data:
                desc = pipeline_data.get('description', 'Aucune description')
                mode = pipeline_data.get('mode', 'unknown')
                methods = pipeline_data.get('methods', [])
                methods_count = len(methods)

                # Algorithm names
                algo_names = [m.get('name', '?') for m in methods[:3]]
                if methods_count > 3:
                    algo_names_str = ', '.join(algo_names) + f', +{methods_count-3} autres'
                else:
                    algo_names_str = ', '.join(algo_names) if algo_names else 'Aucun'

                # DuplicateFlow config
                df_config = pipeline_data.get('duplicateflow_config') or {}
                features = []

                # Validation
                if df_config.get('pre_validators'):
                    val = df_config['pre_validators'][0]
                    val_config = val.get('config', {})
                    tol_pct = val_config.get('tolerance_percent')
                    tol_sec = val_config.get('tolerance_seconds')
                    parts = []
                    if tol_pct: parts.append(f"±{tol_pct}%")
                    if tol_sec: parts.append(f"±{tol_sec}s")
                    features.append(f"✓ Validation longueur: {' / '.join(parts)}")
                else:
                    features.append("✓ Validation longueur: OFF")

                # Partial analysis
                if df_config.get('analyze_duration'):
                    duration = df_config['analyze_duration']
                    from_where = "début" if df_config.get('analyze_from_start', True) else "fin"
                    features.append(f"⚡ Analyse partielle: {duration:.0f}s depuis {from_where}")
                else:
                    features.append("⚡ Analyse partielle: OFF (analyse complète)")

                # Build rich HTML
                info_html = f"""
                <div style='font-family: system-ui;'>
                    <p style='margin: 5px 0;'><b>📝 Description:</b> {desc}</p>

                    <p style='margin: 10px 0 5px 0;'><b>🔧 Configuration:</b></p>
                    <ul style='margin: 0; padding-left: 25px; color: #495057;'>
                        <li><b>Mode:</b> {mode}</li>
                        <li><b>Algorithmes:</b> {methods_count} ({algo_names_str})</li>
                    </ul>

                    <p style='margin: 10px 0 5px 0;'><b>⚡ Optimisations:</b></p>
                    <ul style='margin: 0; padding-left: 25px; color: #495057;'>
                        <li>{features[0]}</li>
                        <li>{features[1]}</li>
                    </ul>
                </div>
                """

                desc_label.setText(info_html)

    combo.currentIndexChanged.connect(update_description)
    if combo.count() > 0:
        update_description(0)

    layout.addWidget(desc_label)

    widgets = {
        'combo': combo,
        'edit_btn': edit_btn,
        'new_btn': new_btn,
        'desc_label': desc_label
    }

    return group, widgets

def _create_advanced_section():
    """Create collapsible advanced options section."""
    group = QGroupBox("⚙️ Options Avancées")
    group.setCheckable(True)
    group.setChecked(False)  # Collapsed by default
    group.setStyleSheet("""
        QGroupBox {
            border: 2px dashed #dee2e6;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 15px;
            background: #fffbf0;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
    """)

    layout = QVBoxLayout(group)
    layout.setSpacing(15)

    # Debug mode checkbox
    debug_checkbox = QCheckBox("Activer le mode debug (logs détaillés)")
    debug_checkbox.setToolTip("Active les logs verbeux dans la console pour diagnostic")
    layout.addWidget(debug_checkbox)

    # Thread count slider
    thread_layout = QHBoxLayout()
    thread_label = QLabel("Nombre de threads:")
    thread_slider = QSlider(Qt.Orientation.Horizontal)
    thread_slider.setMinimum(1)
    thread_slider.setMaximum(32)
    import multiprocessing
    auto_threads = multiprocessing.cpu_count()
    thread_slider.setValue(auto_threads)
    thread_value_label = QLabel(f"Auto ({auto_threads} threads)")
    thread_slider.valueChanged.connect(
        lambda v: thread_value_label.setText(f"{v} threads")
    )
    thread_slider.setToolTip("Contrôle le nombre de processus parallèles")

    thread_layout.addWidget(thread_label)
    thread_layout.addWidget(thread_slider, 1)
    thread_layout.addWidget(thread_value_label)
    layout.addLayout(thread_layout)

    # Cache size slider
    cache_layout = QHBoxLayout()
    cache_label = QLabel("Cache vidéo:")
    cache_slider = QSlider(Qt.Orientation.Horizontal)
    cache_slider.setMinimum(100)
    cache_slider.setMaximum(5000)
    cache_slider.setValue(1000)
    cache_value_label = QLabel("1000 MB")
    cache_slider.valueChanged.connect(
        lambda v: cache_value_label.setText(f"{v} MB")
    )
    cache_slider.setToolTip("Limite de mémoire pour le cache vidéo")

    cache_layout.addWidget(cache_label)
    cache_layout.addWidget(cache_slider, 1)
    cache_layout.addWidget(cache_value_label)
    layout.addLayout(cache_layout)

    widgets = {
        'debug_checkbox': debug_checkbox,
        'thread_slider': thread_slider,
        'cache_slider': cache_slider
    }

    return group, widgets
```

---

## 🚀 Avantages de cette Nouvelle Interface

### 1. Simplicité
- **Moins de choix** = moins de confusion
- **Focus sur DuplicateFlow** = cohérence totale
- **3 sections claires** vs 8 sections complexes

### 2. Modernité
- **Rich HTML** dans description = meilleure lisibilité
- **Icônes visuelles** = reconnaissance rapide
- **Section repliable** = interface propre

### 3. Performance
- **-70% de code** = moins de bugs potentiels
- **Moins de widgets** = UI plus réactive
- **Scroll réduit** = tout visible en un coup d'œil

### 4. Maintenabilité
- **Code modulaire** = fonctions séparées
- **Moins de dépendances** = moins de maintenance
- **100% DuplicateFlow** = pas de code legacy

---

## 📝 Migration Plan

### Phase 1: Backup
```bash
cp src/plugins/duplicate_finder/ui/panels.py src/plugins/duplicate_finder/ui/panels.py.backup
```

### Phase 2: Nettoyage
1. Supprimer lignes 465-1353 (LSH jusqu'à Audio Fingerprint)
2. Garder lignes 333-464 (Language comment + Presets + Pipeline)

### Phase 3: Amélioration
1. Remplacer la fonction `update_description` par la version enrichie
2. Ajouter la section "Advanced Options"
3. Mettre à jour les styles CSS

### Phase 4: Test
1. Lancer `python3 test_ui_automation.py`
2. Vérifier visuellement l'interface
3. Tester création/édition de pipeline

---

## ✅ Checklist d'Implémentation

- [ ] Backup du fichier panels.py
- [ ] Supprimer les sections obsolètes
- [ ] Implémenter update_description enrichi
- [ ] Ajouter section Advanced Options
- [ ] Connecter les sliders aux settings
- [ ] Tester l'interface
- [ ] Mettre à jour les tests automatisés
- [ ] Documentation utilisateur

---

*Proposition créée le 2025-12-19 - Interface moderne 100% DuplicateFlow*
