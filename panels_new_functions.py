"""
Nouvelles fonctions pour l'interface Paramètres modernisée.
À intégrer dans panels.py
"""

from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QSlider, QCheckBox
)
from PyQt6.QtCore import Qt


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
        exclude_keywords = ['scene', 'intro', 'credit']
        return [
            p for p in pipelines
            if not any(kw in p['name'].lower() for kw in exclude_keywords)
        ]

    elif pipeline_type == "scenes":
        # PREFER scene-specific pipelines first, then others
        scene_keywords = ['scene', 'intro', 'credit']
        scene_specific = [
            p for p in pipelines
            if any(kw in p['name'].lower() for kw in scene_keywords)
        ]
        others = [
            p for p in pipelines
            if p not in scene_specific
        ]
        return scene_specific + others

    return pipelines


def _create_pipeline_section_new(title, pipeline_type, pipeline_manager, default_pipeline=None):
    """
    Create a pipeline selection section with enriched description.

    Args:
        title: Section title (e.g., "🔍 Pipeline DUPLICATES")
        pipeline_type: "duplicates" or "scenes" (for filtering)
        pipeline_manager: PipelineManager instance
        default_pipeline: Default pipeline name to select

    Returns:
        (group_widget, widgets_dict)
    """
    from ..ui.panels import UIPanels

    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    layout.setSpacing(10)

    # Selection row
    selection_layout = QHBoxLayout()

    combo = QComboBox()
    combo.setMinimumHeight(35)
    combo.setObjectName(f"{pipeline_type}_pipeline_combo")
    combo.setToolTip(f"Sélectionnez un pipeline pour la détection de {pipeline_type}")

    # Load and FILTER pipelines
    default_index = 0
    if pipeline_manager:
        all_pipelines = pipeline_manager.list_pipelines(include_defaults=True)
        filtered_pipelines = _filter_pipelines_by_type(all_pipelines, pipeline_type)

        for i, pipeline in enumerate(filtered_pipelines):
            display_name = pipeline['name']
            if pipeline.get('is_default'):
                display_name = f"⭐ {display_name}"

            combo.addItem(display_name, userData=pipeline)

            # Set default
            if default_pipeline and pipeline['name'] == default_pipeline:
                default_index = i

        if combo.count() > 0:
            combo.setCurrentIndex(default_index)

    selection_layout.addWidget(QLabel("Pipeline:"), 0)
    selection_layout.addWidget(combo, 1)

    # Edit button
    edit_btn = QPushButton("✏️")
    edit_btn.setMinimumHeight(35)
    edit_btn.setMaximumWidth(45)
    edit_btn.setStyleSheet(UIPanels._get_button_style("#007BFF", "#0056B3"))
    edit_btn.setToolTip("Modifier le pipeline sélectionné")
    edit_btn.setObjectName(f"{pipeline_type}_edit_btn")
    selection_layout.addWidget(edit_btn)

    # New button
    new_btn = QPushButton("➕")
    new_btn.setMinimumHeight(35)
    new_btn.setMaximumWidth(45)
    new_btn.setStyleSheet(UIPanels._get_button_style("#28A745", "#1E7E34"))
    new_btn.setToolTip("Créer un nouveau pipeline")
    new_btn.setObjectName(f"{pipeline_type}_new_btn")
    selection_layout.addWidget(new_btn)

    layout.addLayout(selection_layout)

    # Description card (rich HTML)
    desc_label = QLabel()
    desc_label.setWordWrap(True)
    desc_label.setTextFormat(Qt.TextFormat.RichText)
    desc_label.setStyleSheet("""
        QLabel {
            padding: 12px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            font-size: 13px;
        }
    """)
    desc_label.setObjectName(f"{pipeline_type}_desc_label")

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
                <div style='font-family: -apple-system, system-ui;'>
                    <p style='margin: 5px 0;'><b>📝 Description:</b> {desc}</p>
                    <p style='margin: 5px 0;'><b>🔧 Config:</b> {mode} | {len(methods)} algos ({algo_str})</p>
                    <p style='margin: 5px 0;'><b>⚡ Optimisations:</b> Validation {val_str} | Partielle {partial_str}</p>
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


def _create_lsh_section_new():
    """
    Create LSH acceleration section with detailed explanations.

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

    # Header explanation
    header_label = QLabel(
        "<b>LSH</b> (Locality-Sensitive Hashing) réduit les comparaisons de <b>O(N²)</b> à <b>O(N·k)</b><br>"
        "en groupant les vidéos similaires dans des buckets.<br>"
        "<i>S'active automatiquement quand le nombre de vidéos dépasse le seuil.</i>"
    )
    header_label.setWordWrap(True)
    header_label.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
    layout.addWidget(header_label)

    # Enable checkbox
    enable_check = QCheckBox("Activer LSH")
    enable_check.setChecked(True)
    enable_check.setStyleSheet("font-weight: bold;")
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
        "100 vidéos = recommandé\n"
        "Plus bas = LSH activé plus tôt (utile pour tests)"
    )

    threshold_layout.addWidget(threshold_label)
    threshold_layout.addWidget(threshold_slider, 1)
    threshold_layout.addWidget(threshold_value)
    layout.addLayout(threshold_layout)

    # Num perm slider with detailed explanation
    perm_layout = QVBoxLayout()
    perm_header = QLabel("<b>Permutations MinHash:</b>")
    perm_layout.addWidget(perm_header)

    perm_explain = QLabel(
        "Nombre de hash utilisés pour créer la signature de chaque vidéo.<br>"
        "<b>Plus = plus précis</b> (détecte mieux les similarités) mais <b>plus lent</b>."
    )
    perm_explain.setWordWrap(True)
    perm_explain.setStyleSheet("color: #666; font-size: 11px; margin-left: 10px;")
    perm_layout.addWidget(perm_explain)

    perm_slider_layout = QHBoxLayout()
    perm_slider = QSlider(Qt.Orientation.Horizontal)
    perm_slider.setMinimum(64)
    perm_slider.setMaximum(256)
    perm_slider.setValue(128)
    perm_slider.setSingleStep(64)
    perm_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
    perm_slider.setTickInterval(64)
    perm_value = QLabel("128 (recommandé)")

    def update_perm_label(v):
        if v == 64:
            perm_value.setText("64 (rapide, ~95% taux détection)")
        elif v == 128:
            perm_value.setText("128 (recommandé, ~99% taux détection)")
        else:
            perm_value.setText("256 (très précis, ~99.9% taux détection)")

    perm_slider.valueChanged.connect(update_perm_label)

    perm_slider_layout.addWidget(perm_slider, 1)
    perm_slider_layout.addWidget(perm_value)
    perm_layout.addLayout(perm_slider_layout)
    layout.addLayout(perm_layout)

    # Num bands slider with detailed explanation
    bands_layout = QVBoxLayout()
    bands_header = QLabel("<b>Bandes LSH:</b>")
    bands_layout.addWidget(bands_header)

    bands_explain = QLabel(
        "Nombre de groupes (buckets) pour regrouper les vidéos similaires.<br>"
        "<b>Plus = plus sensible</b> (trouve plus de candidats) mais <b>plus de faux positifs</b>."
    )
    bands_explain.setWordWrap(True)
    bands_explain.setStyleSheet("color: #666; font-size: 11px; margin-left: 10px;")
    bands_layout.addWidget(bands_explain)

    bands_slider_layout = QHBoxLayout()
    bands_slider = QSlider(Qt.Orientation.Horizontal)
    bands_slider.setMinimum(4)
    bands_slider.setMaximum(32)
    bands_slider.setValue(16)
    bands_slider.setSingleStep(4)
    bands_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
    bands_slider.setTickInterval(4)
    bands_value = QLabel("16 (équilibré)")

    def update_bands_label(v):
        if v <= 8:
            bands_value.setText(f"{v} (rapide, moins sensible)")
        elif v == 16:
            bands_value.setText("16 (équilibré, recommandé)")
        else:
            bands_value.setText(f"{v} (très sensible, plus de vérifications)")

    bands_slider.valueChanged.connect(update_bands_label)

    bands_slider_layout.addWidget(bands_slider, 1)
    bands_slider_layout.addWidget(bands_value)
    bands_layout.addLayout(bands_slider_layout)
    layout.addLayout(bands_layout)

    # Info label (dynamic)
    info_label = QLabel()
    info_label.setWordWrap(True)
    info_label.setStyleSheet(
        "color: #495057; font-size: 12px; padding: 8px; "
        "background: #e9ecef; border-radius: 4px; margin-top: 5px;"
    )

    def update_info():
        threshold = threshold_slider.value()
        video_count = 1000  # Example (peut être récupéré du file_handler)

        if video_count < threshold:
            info_label.setText(
                f"<b>ℹ️ LSH non actif</b> ({video_count} vidéos < seuil de {threshold})"
            )
        else:
            total_pairs = (video_count * (video_count - 1)) // 2
            num_bands = bands_slider.value()
            # Approximation de la réduction (formule simplifiée)
            reduction_factor = num_bands / 100
            estimated_pairs = int(total_pairs * reduction_factor)
            reduction_pct = ((total_pairs - estimated_pairs) / total_pairs) * 100

            info_label.setText(
                f"<b>ℹ️ Impact avec {video_count} vidéos:</b><br>"
                f"Comparaisons: {total_pairs:,} → ~{estimated_pairs:,} "
                f"(<b>{reduction_pct:.0f}% réduction</b>)"
            )

    threshold_slider.valueChanged.connect(update_info)
    bands_slider.valueChanged.connect(update_info)
    enable_check.toggled.connect(update_info)
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
