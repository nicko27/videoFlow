#!/usr/bin/env python3
"""
Patch panels.py pour utiliser i18n (fonction t()) au lieu de textes en dur.
"""

# Liste des replacements à faire
REPLACEMENTS = [
    # Pipeline section - tooltip
    ('combo.setToolTip(f"Sélectionnez un pipeline pour la détection de {pipeline_type}")',
     'combo.setToolTip(t(f"duplicate_finder.ui.pipeline.select_tooltip_{pipeline_type}"))'),

    # Pipeline section - label
    ('selection_layout.addWidget(QLabel("Pipeline:"), 0)',
     'selection_layout.addWidget(QLabel(t("duplicate_finder.ui.pipeline.label")), 0)'),

    # Edit button tooltip
    ('edit_btn.setToolTip("Modifier le pipeline sélectionné")',
     'edit_btn.setToolTip(t("duplicate_finder.ui.pipeline.edit_tooltip"))'),

    # New button tooltip
    ('new_btn.setToolTip("Créer un nouveau pipeline")',
     'new_btn.setToolTip(t("duplicate_finder.ui.pipeline.new_tooltip"))'),

    # Description - no description
    ("desc = pipeline_data.get('description', 'Aucune description')",
     "desc = pipeline_data.get('description', t('duplicate_finder.ui.pipeline.desc_no_description'))"),

    # Description - algorithm names
    ("algo_str = ', '.join(algo_names) if algo_names else 'Aucun'",
     "algo_str = ', '.join(algo_names) if algo_names else t('duplicate_finder.ui.pipeline.desc_no_algorithms')"),

    # Description - more algorithms
    ("algo_str = ', '.join(algo_names) + f', +{len(methods)-3} autres'",
     "algo_str = ', '.join(algo_names) + ', ' + t('duplicate_finder.ui.pipeline.desc_algos_more', count=len(methods)-3)"),

    # Validation OFF
    ('val_str = "OFF"',
     'val_str = t("duplicate_finder.ui.pipeline.desc_validation_off")'),

    # Validation ON
    ('val_str = " / ".join(parts) if parts else "ON"',
     'val_str = " / ".join(parts) if parts else t("duplicate_finder.ui.pipeline.desc_validation_on")'),

    # Partial OFF
    ('partial_str = "OFF (analyse complète)"',
     'partial_str = t("duplicate_finder.ui.pipeline.desc_partial_off")'),

    # Partial from start
    ('from_where = "début" if df_config.get(\'analyze_from_start\', True) else "fin"',
     'from_where = "start" if df_config.get(\'analyze_from_start\', True) else "end"'),

    ('partial_str = f"{dur:.0f}s depuis {from_where}"',
     'partial_str = t(f"duplicate_finder.ui.pipeline.desc_partial_from_{from_where}", duration=dur)'),

    # Description HTML labels
    ('<p style=\'margin: 5px 0;\'><b>📝 Description:</b>',
     f"<p style='margin: 5px 0;'><b>📝 {t('duplicate_finder.ui.pipeline.desc_description')}</b>"),

    ('<p style=\'margin: 5px 0;\'><b>🔧 Config:</b>',
     f"<p style='margin: 5px 0;'><b>🔧 {t('duplicate_finder.ui.pipeline.desc_config')}</b>"),

    ('<p style=\'margin: 5px 0;\'><b>⚡ Optimisations:</b>',
     f"<p style='margin: 5px 0;'><b>⚡ {t('duplicate_finder.ui.pipeline.desc_optimizations')}</b>"),

    # LSH section - title (already done in previous edit)
    # LSH - enable checkbox
    ('enable_check = QCheckBox("Activer LSH")',
     'enable_check = QCheckBox(t("duplicate_finder.ui.lsh.enable"))'),

    # LSH - threshold label
    ('threshold_label = QLabel("Seuil d\'activation:")',
     'threshold_label = QLabel(t("duplicate_finder.ui.lsh.threshold_label"))'),

    # LSH - threshold tooltip (multiline - need special handling)

    # LSH - threshold value
    ('threshold_value.setText(f"{v} vidéos")',
     'threshold_value.setText(t("duplicate_finder.ui.lsh.threshold_value", value=v))'),

    # LSH - perm header
    ('perm_header = QLabel("<b>Permutations MinHash:</b>")',
     'perm_header = QLabel(f"<b>{t(\'duplicate_finder.ui.lsh.perm_header\')}</b>")'),

    # LSH - perm value 64
    ('perm_value.setText("64 (rapide, ~95% taux détection)")',
     'perm_value.setText(t("duplicate_finder.ui.lsh.perm_value_64"))'),

    # LSH - perm value 128
    ('perm_value.setText("128 (recommandé, ~99% taux détection)")',
     'perm_value.setText(t("duplicate_finder.ui.lsh.perm_value_128"))'),

    # LSH - perm value 256
    ('perm_value.setText("256 (très précis, ~99.9% taux détection)")',
     'perm_value.setText(t("duplicate_finder.ui.lsh.perm_value_256"))'),

    # LSH - bands header
    ('bands_header = QLabel("<b>Bandes LSH:</b>")',
     'bands_header = QLabel(f"<b>{t(\'duplicate_finder.ui.lsh.bands_header\')}</b>")'),

    # LSH - bands values
    ('bands_value.setText(f"{v} (rapide, moins sensible)")',
     'bands_value.setText(t("duplicate_finder.ui.lsh.bands_value_low", value=v))'),

    ('bands_value.setText("16 (équilibré, recommandé)")',
     'bands_value.setText(t("duplicate_finder.ui.lsh.bands_value_balanced"))'),

    ('bands_value.setText(f"{v} (très sensible, plus de vérifications)")',
     'bands_value.setText(t("duplicate_finder.ui.lsh.bands_value_high", value=v))'),
]

# Multiline replacements
MULTILINE_REPLACEMENTS = [
    # LSH header
    ('''header_label = QLabel(
        "<b>LSH</b> (Locality-Sensitive Hashing) réduit les comparaisons de <b>O(N²)</b> à <b>O(N·k)</b><br>"
        "en groupant les vidéos similaires dans des buckets.<br>"
        "<i>S'active automatiquement quand le nombre de vidéos dépasse le seuil.</i>"
    )''',
     'header_label = QLabel(t("duplicate_finder.ui.lsh.header"))'),

    # LSH perm explain
    ('''perm_explain = QLabel(
        "Nombre de hash utilisés pour créer la signature de chaque vidéo.<br>"
        "<b>Plus = plus précis</b> (détecte mieux les similarités) mais <b>plus lent</b>."
    )''',
     'perm_explain = QLabel(t("duplicate_finder.ui.lsh.perm_explain"))'),

    # LSH bands explain
    ('''bands_explain = QLabel(
        "Nombre de groupes (buckets) pour regrouper les vidéos similaires.<br>"
        "<b>Plus = plus sensible</b> (trouve plus de candidats) mais <b>plus de faux positifs</b>."
    )''',
     'bands_explain = QLabel(t("duplicate_finder.ui.lsh.bands_explain"))'),

    # LSH threshold tooltip
    ('''perm_slider.setToolTip(
        "Nombre minimum de vidéos pour activer LSH automatiquement\\n"
        "100 vidéos = recommandé\\n"
        "Plus bas = LSH activé plus tôt (utile pour tests)"
    )''',
     'threshold_slider.setToolTip(t("duplicate_finder.ui.lsh.threshold_tooltip"))'),

    # LSH info inactive
    ('''info_label.setText(
                f"<b>ℹ️ LSH non actif</b> ({video_count} vidéos < seuil de {threshold})"
            )''',
     'info_label.setText(t("duplicate_finder.ui.lsh.info_inactive", video_count=video_count, threshold=threshold))'),

    # LSH info active
    ('''info_label.setText(
                f"<b>ℹ️ Impact avec {video_count} vidéos:</b><br>"
                f"Comparaisons: {total_pairs:,} → ~{estimated_pairs:,} "
                f"(<b>{reduction_pct:.0f}% réduction</b>)"
            )''',
     'info_label.setText(t("duplicate_finder.ui.lsh.info_active", video_count=video_count, total_pairs=total_pairs, estimated_pairs=estimated_pairs, reduction_pct=reduction_pct))'),
]

def patch_file():
    """Applique les patchs au fichier panels.py."""
    filepath = 'src/plugins/duplicate_finder/ui/panels.py'

    # Lire le fichier
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Appliquer les replacements simples
    for old, new in REPLACEMENTS:
        if old in content:
            content = content.replace(old, new)
            print(f"  ✅ {old[:60]}...")
        else:
            print(f"  ⚠️  Not found: {old[:60]}...")

    # Appliquer les replacements multilignes
    for old, new in MULTILINE_REPLACEMENTS:
        if old in content:
            content = content.replace(old, new)
            print(f"  ✅ [multiline] {old[:60]}...")
        else:
            print(f"  ⚠️  Not found [multiline]: {old[:60]}...")

    if content != original_content:
        # Sauvegarder
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    else:
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("PATCH DE PANELS.PY POUR I18N")
    print("=" * 70)

    updated = patch_file()

    print("\n" + "=" * 70)
    if updated:
        print("✅ panels.py patché avec succès")
    else:
        print("⚠️  Aucune modification appliquée")
    print("=" * 70)
