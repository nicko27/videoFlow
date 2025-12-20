# Plan Interface Finale - Onglet Paramètres

**Date**: 2025-12-19
**Objectif**: Interface avec 2 pipelines séparés (Duplicates/Scenes) + LSH

---

## 🎯 Architecture Actuelle Comprise

### 1. Modes de Détection
L'application a **2 modes distincts**:

#### A. Détection de Duplicates (`start_analysis()`)
- **Fonction**: main_window.py ligne 1043
- **Workflow**: Comparaison complète entre toutes les vidéos
- **Algorithmes**: DuplicateFlow avec pipelines configurables
- **Use case**: Trouver des copies identiques ou similaires

#### B. Détection de Scènes (`start_scene_detection_mode()`)
- **Fonction**: main_window.py ligne 1164
- **Workflow**: SubsequenceDetector avec Strategy 3
- **Algorithmes**: DCT coefficients + Scene Cuts
- **Use case**: Trouver des extraits/scènes communes entre vidéos

### 2. LSH dans DuplicateFlow
**Fichier**: duplicateflow/processing/lsh_index.py

**Paramètres**:
```python
use_lsh: bool = True  # Activer/désactiver
lsh_threshold: int = 100  # Nombre min de vidéos pour activer
lsh_num_perm: int = 128  # Nombre de permutations MinHash
lsh_num_bands: int = 16  # Nombre de bandes LSH
```

**Mode**: FINGERPRINT uniquement (detection.py ligne 201)

**Effet**: Réduit comparaisons de O(N²) à O(N·k)
- 1000 vidéos: 499,500 → ~40,000 pairs (92% réduction)

---

## 🎨 Nouvelle Interface Proposée

### Maquette Visuelle

```
┌─────────────────────────────────────────────────────────────────────┐
│ ⚙️ PARAMÈTRES                                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 🔍 Pipeline DUPLICATES                                          │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │                                                                 │ │
│ │  Pipeline: [⭐ fast (DuplicateFlow)          ▼] [✏️] [➕]      │ │
│ │                                                                 │ │
│ │  ┌──────────────────────────────────────────────────────────┐  │ │
│ │  │ 📝 Description: Détection rapide de duplicatas           │  │ │
│ │  │ 🔧 Config: weighting | 3 algos (frame_hash, ...)        │  │ │
│ │  │ ⚡ Optimisations: Validation OFF | Analyse partielle OFF │  │ │
│ │  └──────────────────────────────────────────────────────────┘  │ │
│ │                                                                 │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 🎬 Pipeline SCÈNES                                              │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │                                                                 │ │
│ │  Pipeline: [⭐ accurate_scenes (DuplicateFlow) ▼] [✏️] [➕]    │ │
│ │                                                                 │ │
│ │  ┌──────────────────────────────────────────────────────────┐  │ │
│ │  │ 📝 Description: Détection précise de scènes communes     │  │ │
│ │  │ 🔧 Config: weighting | 3 algos (dct_coeff, ...)         │  │ │
│ │  │ ⚡ Optimisations: Validation ±5% | Analyse complète      │  │ │
│ │  └──────────────────────────────────────────────────────────┘  │ │
│ │                                                                 │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ ⚡ LSH Acceleration (Mode Fingerprint)                          │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │                                                                 │ │
│ │  ☑ Activer LSH (s'active auto si ≥100 vidéos)                  │ │
│ │                                                                 │ │
│ │  Seuil d'activation: [●─────────────] 100 vidéos               │ │
│ │                                                                 │ │
│ │  Permutations MinHash: [●─────────────] 128 (recommandé)       │ │
│ │                                                                 │ │
│ │  Bandes LSH: [●─────────────] 16 (équilibré)                   │ │
│ │                                                                 │ │
│ │  ℹ️ Avec 1000 vidéos: 499,500 → ~40,000 comparaisons (92% ↓)  │ │
│ │                                                                 │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Sections Détaillées

### 1. 🔍 Pipeline DUPLICATES
**Hauteur**: ~230px

**Contenu**:
```python
- Combo box avec pipelines FILTRÉS pour duplicates
- Boutons Éditer / Nouveau
- Carte de description enrichie (HTML)
```

**Pipelines recommandés**:
- ⭐ `fast (DuplicateFlow)` - Détection rapide
- ⭐ `balanced (DuplicateFlow)` - Équilibré
- ⭐ `thorough (DuplicateFlow)` - Détection approfondie
- ⭐ `fast_duplicates (DuplicateFlow)` - Optimisé duplicates
- `AudioShazam` - Audio uniquement

**Filtrage**:
Exclure les pipelines spécifiques scènes:
- ❌ `accurate_scenes`
- ❌ `intro_detector`
- ❌ `credits_detector`

**Action**: Lance `start_analysis()` avec le pipeline sélectionné

---

### 2. 🎬 Pipeline SCÈNES
**Hauteur**: ~230px

**Contenu**:
```python
- Combo box avec pipelines FILTRÉS pour scènes
- Boutons Éditer / Nouveau
- Carte de description enrichie (HTML)
```

**Pipelines recommandés**:
- ⭐ `accurate_scenes (DuplicateFlow)` - Détection scènes précise
- ⭐ `intro_detector (DuplicateFlow)` - Détection intros
- ⭐ `credits_detector (DuplicateFlow)` - Détection génériques
- ⭐ `balanced (DuplicateFlow)` - Usage général

**Filtrage**:
Favoriser les pipelines avec:
- ✅ Validation de longueur (pour scènes de durée similaire)
- ✅ Analyse complète (pas partielle)

**Action**: Lance `start_scene_detection_mode()` avec le pipeline sélectionné

---

### 3. ⚡ LSH Acceleration
**Hauteur**: ~200px
**Repliable**: Oui (▼/▲)

**Contenu**:

#### A. Checkbox "Activer LSH"
```python
enable_lsh = QCheckBox("Activer LSH (s'active auto si ≥100 vidéos)")
enable_lsh.setChecked(True)  # Activé par défaut
enable_lsh.setToolTip(
    "LSH (Locality-Sensitive Hashing) réduit les comparaisons de O(N²) à O(N·k)\n"
    "S'active automatiquement quand le nombre de vidéos dépasse le seuil\n"
    "Mode FINGERPRINT uniquement"
)
```

#### B. Slider "Seuil d'activation"
```python
lsh_threshold_slider = QSlider(Qt.Orientation.Horizontal)
lsh_threshold_slider.setMinimum(10)
lsh_threshold_slider.setMaximum(500)
lsh_threshold_slider.setValue(100)
lsh_threshold_slider.setToolTip(
    "Nombre minimum de vidéos pour activer LSH automatiquement\n"
    "Valeur recommandée: 100\n"
    "Plus bas = LSH activé plus tôt (utile pour tests)"
)
```

#### C. Slider "Permutations MinHash"
```python
lsh_num_perm_slider = QSlider(Qt.Orientation.Horizontal)
lsh_num_perm_slider.setMinimum(64)
lsh_num_perm_slider.setMaximum(256)
lsh_num_perm_slider.setValue(128)
lsh_num_perm_slider.setSingleStep(64)
lsh_num_perm_slider.setToolTip(
    "Nombre de permutations pour signature MinHash\n"
    "Plus = plus précis mais plus lent\n"
    "128 = optimal (99% taux de détection)\n"
    "64 = rapide (95% taux)\n"
    "256 = très précis (99.9% taux)"
)
```

#### D. Slider "Bandes LSH"
```python
lsh_num_bands_slider = QSlider(Qt.Orientation.Horizontal)
lsh_num_bands_slider.setMinimum(4)
lsh_num_bands_slider.setMaximum(32)
lsh_num_bands_slider.setValue(16)
lsh_num_bands_slider.setSingleStep(4)
lsh_num_bands_slider.setToolTip(
    "Nombre de bandes pour l'index LSH\n"
    "Plus = plus sensible mais plus de faux positifs\n"
    "16 = équilibré (recommandé)\n"
    "8 = rapide, moins sensible\n"
    "32 = très sensible, plus de vérifications"
)
```

#### E. Label Info Dynamique
```python
# Calcule et affiche l'impact estimé
def update_lsh_info():
    video_count = 1000  # Exemple ou récupérer du file_handler

    if video_count < lsh_threshold:
        info_text = f"⚠️ LSH non actif ({video_count} < {lsh_threshold} vidéos)"
    else:
        total_pairs = (video_count * (video_count - 1)) // 2

        # Estimation approximative
        reduction_factor = lsh_num_bands / 100
        estimated_pairs = int(total_pairs * reduction_factor)
        reduction_pct = ((total_pairs - estimated_pairs) / total_pairs) * 100

        info_text = (
            f"ℹ️ Avec {video_count} vidéos: "
            f"{total_pairs:,} → ~{estimated_pairs:,} comparaisons "
            f"({reduction_pct:.0f}% réduction)"
        )

    lsh_info_label.setText(info_text)
```

**Style**:
```python
lsh_group.setStyleSheet("""
    QGroupBox {
        border: 1px solid #ffc107;
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 15px;
        background: #fffef5;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
        color: #ff8c00;
        font-weight: bold;
    }
""")
```

---

## 🗑️ Sections à SUPPRIMER

### 1. ❌ Quick Presets
**Lignes**: 340-369
**Raison**: Remplacés par sélection directe de pipeline (plus flexible)

### 2. ❌ Multi-resolution Comparison
**Lignes**: ~515-702
**Raison**: Géré par algorithmes DuplicateFlow

### 3. ❌ Video Hashing & Comparison
**Lignes**: ~705-755
**Raison**: Géré par frame_hash

### 4. ❌ Flip Detection
**Lignes**: ~758-826
**Raison**: Géré par paramètres des algorithmes

### 5. ❌ Audio Fingerprint Filtering
**Lignes**: ~829-1353
**Raison**: Remplacé par df_audio_fingerprint

### 6. ⚠️ LSH Section Actuelle (à remplacer)
**Lignes**: 465-512
**Raison**: Remplacée par la nouvelle version détaillée

---

## 💻 Code Structure

```python
def _create_parameters_tab(callbacks, db_manager=None, pipeline_manager=None):
    """
    Create simplified parameters tab with:
    1. Pipeline DUPLICATES
    2. Pipeline SCÈNES
    3. LSH Acceleration
    """
    tab = QWidget()
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)

    content_widget = QWidget()
    layout = QVBoxLayout(content_widget)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(15)

    # ══════════════════════════════════════════════════════
    # 1. PIPELINE DUPLICATES
    # ══════════════════════════════════════════════════════
    duplicates_group, duplicates_widgets = _create_pipeline_section(
        title="🔍 Pipeline DUPLICATES",
        pipeline_type="duplicates",
        pipeline_manager=pipeline_manager,
        default_pipeline="fast_duplicates (DuplicateFlow)"
    )
    layout.addWidget(duplicates_group)

    # Store references
    tab.duplicates_pipeline_combo = duplicates_widgets['combo']
    tab.duplicates_edit_btn = duplicates_widgets['edit_btn']
    tab.duplicates_new_btn = duplicates_widgets['new_btn']

    # ══════════════════════════════════════════════════════
    # 2. PIPELINE SCÈNES
    # ══════════════════════════════════════════════════════
    scenes_group, scenes_widgets = _create_pipeline_section(
        title="🎬 Pipeline SCÈNES",
        pipeline_type="scenes",
        pipeline_manager=pipeline_manager,
        default_pipeline="accurate_scenes (DuplicateFlow)"
    )
    layout.addWidget(scenes_group)

    # Store references
    tab.scenes_pipeline_combo = scenes_widgets['combo']
    tab.scenes_edit_btn = scenes_widgets['edit_btn']
    tab.scenes_new_btn = scenes_widgets['new_btn']

    # ══════════════════════════════════════════════════════
    # 3. LSH ACCELERATION
    # ══════════════════════════════════════════════════════
    lsh_group, lsh_widgets = _create_lsh_section()
    layout.addWidget(lsh_group)

    # Store references
    tab.enable_lsh = lsh_widgets['enable']
    tab.lsh_threshold = lsh_widgets['threshold']
    tab.lsh_num_perm = lsh_widgets['num_perm']
    tab.lsh_num_bands = lsh_widgets['num_bands']

    # Spacer
    layout.addStretch()

    scroll_area.setWidget(content_widget)
    tab_layout = QVBoxLayout(tab)
    tab_layout.setContentsMargins(0, 0, 0, 0)
    tab_layout.addWidget(scroll_area)

    return tab


def _create_pipeline_section(title, pipeline_type, pipeline_manager, default_pipeline):
    """
    Create a pipeline selection section.

    Args:
        title: Section title (e.g., "🔍 Pipeline DUPLICATES")
        pipeline_type: "duplicates" or "scenes" (for filtering)
        pipeline_manager: PipelineManager instance
        default_pipeline: Default pipeline name to select

    Returns:
        (group_widget, widgets_dict)
    """
    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    layout.setSpacing(10)

    # Selection row
    selection_layout = QHBoxLayout()

    combo = QComboBox()
    combo.setMinimumHeight(35)
    combo.setObjectName(f"{pipeline_type}_pipeline_combo")

    # Load and FILTER pipelines
    if pipeline_manager:
        all_pipelines = pipeline_manager.list_pipelines(include_defaults=True)

        # Filter based on type
        filtered_pipelines = _filter_pipelines_by_type(all_pipelines, pipeline_type)

        default_index = 0
        for i, pipeline in enumerate(filtered_pipelines):
            display_name = pipeline['name']
            if pipeline.get('is_default'):
                display_name = f"⭐ {display_name}"

            combo.addItem(display_name, userData=pipeline)

            # Set default
            if pipeline['name'] == default_pipeline:
                default_index = i

        combo.setCurrentIndex(default_index)

    selection_layout.addWidget(QLabel("Pipeline:"), 0)
    selection_layout.addWidget(combo, 1)

    # Edit button
    edit_btn = QPushButton("✏️")
    edit_btn.setMinimumHeight(35)
    edit_btn.setMaximumWidth(45)
    edit_btn.setStyleSheet(_get_button_style("#007BFF", "#0056B3"))
    edit_btn.setToolTip("Modifier le pipeline")
    selection_layout.addWidget(edit_btn)

    # New button
    new_btn = QPushButton("➕")
    new_btn.setMinimumHeight(35)
    new_btn.setMaximumWidth(45)
    new_btn.setStyleSheet(_get_button_style("#28A745", "#1E7E34"))
    new_btn.setToolTip("Créer un nouveau pipeline")
    selection_layout.addWidget(new_btn)

    layout.addLayout(selection_layout)

    # Description card (rich HTML)
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

    def update_description(index):
        if index >= 0:
            pipeline_data = combo.itemData(index)
            if pipeline_data:
                desc = pipeline_data.get('description', 'Aucune description')
                mode = pipeline_data.get('mode', 'unknown')
                methods = pipeline_data.get('methods', [])

                # Algorithm names (first 3)
                algo_names = [m.get('name', '?') for m in methods[:3]]
                if len(methods) > 3:
                    algo_str = ', '.join(algo_names) + f', +{len(methods)-3} autres'
                else:
                    algo_str = ', '.join(algo_names) if algo_names else 'Aucun'

                # DuplicateFlow config
                df_config = pipeline_data.get('duplicateflow_config') or {}

                # Validation
                val_str = "OFF"
                if df_config.get('pre_validators'):
                    val = df_config['pre_validators'][0]
                    val_config = val.get('config', {})
                    parts = []
                    if val_config.get('tolerance_percent'):
                        parts.append(f"±{val_config['tolerance_percent']}%")
                    if val_config.get('tolerance_seconds'):
                        parts.append(f"±{val_config['tolerance_seconds']}s")
                    val_str = ' / '.join(parts) if parts else "ON"

                # Partial analysis
                partial_str = "OFF (analyse complète)"
                if df_config.get('analyze_duration'):
                    dur = df_config['analyze_duration']
                    from_where = "début" if df_config.get('analyze_from_start', True) else "fin"
                    partial_str = f"{dur:.0f}s depuis {from_where}"

                # Build HTML
                html = f"""
                <div style='font-family: system-ui;'>
                    <p style='margin: 5px 0;'><b>📝 Description:</b> {desc}</p>
                    <p style='margin: 5px 0;'><b>🔧 Config:</b> {mode} | {len(methods)} algos ({algo_str})</p>
                    <p style='margin: 5px 0;'><b>⚡ Optimisations:</b> Validation {val_str} | Analyse partielle {partial_str}</p>
                </div>
                """

                desc_label.setText(html)

    combo.currentIndexChanged.connect(update_description)
    if combo.count() > 0:
        update_description(combo.currentIndex())

    layout.addWidget(desc_label)

    widgets = {
        'combo': combo,
        'edit_btn': edit_btn,
        'new_btn': new_btn,
        'desc_label': desc_label
    }

    return group, widgets


def _filter_pipelines_by_type(pipelines, pipeline_type):
    """
    Filter pipelines based on their intended use.

    Args:
        pipelines: List of all pipelines
        pipeline_type: "duplicates" or "scenes"

    Returns:
        Filtered list of pipelines
    """
    if pipeline_type == "duplicates":
        # EXCLUDE scene-specific pipelines
        exclude_names = [
            'accurate_scenes',
            'intro_detector',
            'credits_detector'
        ]
        return [
            p for p in pipelines
            if not any(ex in p['name'].lower() for ex in exclude_names)
        ]

    elif pipeline_type == "scenes":
        # PREFER scene-specific pipelines, but allow all
        # (Scenes peuvent utiliser n'importe quel pipeline)
        # Tri: scene-specific d'abord
        scene_specific = [
            p for p in pipelines
            if any(kw in p['name'].lower() for kw in ['scene', 'intro', 'credit'])
        ]
        others = [
            p for p in pipelines
            if p not in scene_specific
        ]
        return scene_specific + others

    return pipelines


def _create_lsh_section():
    """
    Create LSH acceleration section.

    Returns:
        (group_widget, widgets_dict)
    """
    group = QGroupBox("⚡ LSH Acceleration (Mode Fingerprint)")
    group.setCheckable(True)
    group.setChecked(True)  # Expanded by default
    group.setStyleSheet("""
        QGroupBox {
            border: 1px solid #ffc107;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 15px;
            background: #fffef5;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #ff8c00;
            font-weight: bold;
        }
    """)

    layout = QVBoxLayout(group)
    layout.setSpacing(15)

    # Enable checkbox
    enable_check = QCheckBox("Activer LSH (s'active auto si ≥ seuil vidéos)")
    enable_check.setChecked(True)
    enable_check.setToolTip(
        "LSH (Locality-Sensitive Hashing) réduit les comparaisons de O(N²) à O(N·k)\n"
        "S'active automatiquement quand le nombre de vidéos dépasse le seuil\n"
        "Mode FINGERPRINT uniquement"
    )
    layout.addWidget(enable_check)

    # Threshold slider
    threshold_layout = QHBoxLayout()
    threshold_label = QLabel("Seuil d'activation:")
    threshold_slider = QSlider(Qt.Orientation.Horizontal)
    threshold_slider.setMinimum(10)
    threshold_slider.setMaximum(500)
    threshold_slider.setValue(100)
    threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
    threshold_slider.setTickInterval(50)
    threshold_value = QLabel("100 vidéos")
    threshold_slider.valueChanged.connect(
        lambda v: threshold_value.setText(f"{v} vidéos")
    )
    threshold_slider.setToolTip(
        "Nombre minimum de vidéos pour activer LSH automatiquement\n"
        "Recommandé: 100"
    )

    threshold_layout.addWidget(threshold_label)
    threshold_layout.addWidget(threshold_slider, 1)
    threshold_layout.addWidget(threshold_value)
    layout.addLayout(threshold_layout)

    # Num perm slider
    perm_layout = QHBoxLayout()
    perm_label = QLabel("Permutations MinHash:")
    perm_slider = QSlider(Qt.Orientation.Horizontal)
    perm_slider.setMinimum(64)
    perm_slider.setMaximum(256)
    perm_slider.setValue(128)
    perm_slider.setSingleStep(64)
    perm_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
    perm_slider.setTickInterval(64)
    perm_value = QLabel("128 (recommandé)")
    perm_slider.valueChanged.connect(
        lambda v: perm_value.setText(
            f"{v} " + ("(rapide)" if v == 64 else "(recommandé)" if v == 128 else "(très précis)")
        )
    )
    perm_slider.setToolTip(
        "Nombre de permutations pour signature MinHash\n"
        "64 = rapide (95% taux)\n"
        "128 = optimal (99% taux)\n"
        "256 = très précis (99.9% taux)"
    )

    perm_layout.addWidget(perm_label)
    perm_layout.addWidget(perm_slider, 1)
    perm_layout.addWidget(perm_value)
    layout.addLayout(perm_layout)

    # Num bands slider
    bands_layout = QHBoxLayout()
    bands_label = QLabel("Bandes LSH:")
    bands_slider = QSlider(Qt.Orientation.Horizontal)
    bands_slider.setMinimum(4)
    bands_slider.setMaximum(32)
    bands_slider.setValue(16)
    bands_slider.setSingleStep(4)
    bands_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
    bands_slider.setTickInterval(4)
    bands_value = QLabel("16 (équilibré)")
    bands_slider.valueChanged.connect(
        lambda v: bands_value.setText(
            f"{v} " + ("(rapide)" if v <= 8 else "(équilibré)" if v == 16 else "(sensible)")
        )
    )
    bands_slider.setToolTip(
        "Nombre de bandes pour l'index LSH\n"
        "8 = rapide, moins sensible\n"
        "16 = équilibré (recommandé)\n"
        "32 = très sensible, plus de faux positifs"
    )

    bands_layout.addWidget(bands_label)
    bands_layout.addWidget(bands_slider, 1)
    bands_layout.addWidget(bands_value)
    layout.addLayout(bands_layout)

    # Info label (dynamic)
    info_label = QLabel()
    info_label.setWordWrap(True)
    info_label.setStyleSheet("color: #666; font-style: italic;")

    def update_info():
        threshold = threshold_slider.value()
        video_count = 1000  # Example (récupérer de file_handler si disponible)

        if video_count < threshold:
            info_label.setText(
                f"ℹ️ LSH non actif ({video_count} < {threshold} vidéos)"
            )
        else:
            total_pairs = (video_count * (video_count - 1)) // 2
            num_bands = bands_slider.value()
            reduction_factor = num_bands / 100  # Approximation
            estimated_pairs = int(total_pairs * reduction_factor)
            reduction_pct = ((total_pairs - estimated_pairs) / total_pairs) * 100

            info_label.setText(
                f"ℹ️ Avec {video_count} vidéos: "
                f"{total_pairs:,} → ~{estimated_pairs:,} comparaisons "
                f"({reduction_pct:.0f}% réduction)"
            )

    threshold_slider.valueChanged.connect(update_info)
    bands_slider.valueChanged.connect(update_info)
    update_info()

    layout.addWidget(info_label)

    widgets = {
        'enable': enable_check,
        'threshold': threshold_slider,
        'num_perm': perm_slider,
        'num_bands': bands_slider,
        'info_label': info_label
    }

    return group, widgets
```

---

## 🔄 Workflow Utilisateur

### Scénario 1: Détection de Duplicates
```
1. Utilisateur charge des fichiers
2. Va dans Paramètres
3. Section "🔍 Pipeline DUPLICATES"
4. Sélectionne "⭐ fast_duplicates (DuplicateFlow)"
5. Voit: "3 algos (frame_hash, color_histogram, color_moments)"
6. Active LSH si > 100 vidéos
7. Lance analyse → appelle start_analysis()
```

### Scénario 2: Détection de Scènes
```
1. Utilisateur charge des fichiers
2. Va dans Paramètres
3. Section "🎬 Pipeline SCÈNES"
4. Sélectionne "⭐ accurate_scenes (DuplicateFlow)"
5. Voit: "Validation ±5% | Analyse complète"
6. Lance analyse → appelle start_scene_detection_mode()
```

### Scénario 3: Création Pipeline Personnalisé
```
1. Utilisateur clique "➕" dans section DUPLICATES
2. UnifiedPipelineEditorDialog s'ouvre
3. Configure algorithmes, validateurs, analyse partielle
4. Sauvegarde
5. Pipeline apparaît dans liste DUPLICATES
6. Peut l'utiliser immédiatement
```

---

## 📊 Comparaison Avant/Après

| Métrique | Avant | Après | Changement |
|----------|-------|-------|------------|
| Lignes de code | ~1200 | ~600 | **-50%** |
| Sections | 8 | 3 | **-62%** |
| Quick Presets | Oui | Non | Supprimés |
| Pipelines | 1 sélecteur | 2 sélecteurs | Séparés |
| LSH | Basic (4 params) | Avancé (4 params + info) | Amélioré |
| Redondances | Nombreuses | Aucune | Éliminées |

---

## ✅ Checklist Implémentation

### Phase 1: Backup
- [ ] `cp panels.py panels.py.backup_20251219`

### Phase 2: Suppression
- [ ] Supprimer Quick Presets (lignes 340-369)
- [ ] Supprimer LSH actuel (lignes 465-512)
- [ ] Supprimer Multi-resolution (lignes 515-702)
- [ ] Supprimer Video Hashing (lignes 705-755)
- [ ] Supprimer Flip Detection (lignes 758-826)
- [ ] Supprimer Audio Fingerprint (lignes 829-1353)

### Phase 3: Ajout
- [ ] Implémenter `_create_pipeline_section()`
- [ ] Implémenter `_filter_pipelines_by_type()`
- [ ] Implémenter `_create_lsh_section()`
- [ ] Modifier `_create_parameters_tab()`

### Phase 4: Intégration main_window
- [ ] Extraire `duplicates_pipeline_combo`
- [ ] Extraire `scenes_pipeline_combo`
- [ ] Extraire widgets LSH
- [ ] Connecter callbacks Edit/New pour duplicates
- [ ] Connecter callbacks Edit/New pour scenes
- [ ] Modifier `start_analysis()` pour utiliser duplicates pipeline
- [ ] Modifier `start_scene_detection_mode()` pour utiliser scenes pipeline

### Phase 5: Tests
- [ ] Test sélection pipeline duplicates
- [ ] Test sélection pipeline scenes
- [ ] Test filtrage des pipelines
- [ ] Test LSH sliders
- [ ] Test création nouveau pipeline
- [ ] Test édition pipeline
- [ ] Test lancement analyse duplicates
- [ ] Test lancement analyse scenes

---

## 🎯 Estimation

**Temps**: 2-3 heures
**Complexité**: Moyenne
**Risque**: Faible (backup + tests)

---

*Plan créé le 2025-12-19 - Interface finale 100% DuplicateFlow avec 2 pipelines séparés*
