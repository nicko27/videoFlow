#!/usr/bin/env python3
"""
Ajoute les clés i18n nécessaires pour la nouvelle interface Paramètres.
"""

import json

# Nouvelles clés i18n (FR)
NEW_KEYS_FR = {
    # Pipeline section titles
    "duplicate_finder.ui.pipeline.duplicates_title": "🔍 Pipeline DUPLICATES",
    "duplicate_finder.ui.pipeline.scenes_title": "🎬 Pipeline SCÈNES",

    # Pipeline section labels
    "duplicate_finder.ui.pipeline.label": "Pipeline:",
    "duplicate_finder.ui.pipeline.select_tooltip_duplicates": "Sélectionnez un pipeline pour la détection de duplicates",
    "duplicate_finder.ui.pipeline.select_tooltip_scenes": "Sélectionnez un pipeline pour la détection de scenes",

    # Buttons
    "duplicate_finder.ui.pipeline.edit_tooltip": "Modifier le pipeline sélectionné",
    "duplicate_finder.ui.pipeline.new_tooltip": "Créer un nouveau pipeline",

    # Description fields
    "duplicate_finder.ui.pipeline.desc_description": "Description:",
    "duplicate_finder.ui.pipeline.desc_config": "Config:",
    "duplicate_finder.ui.pipeline.desc_optimizations": "Optimisations:",
    "duplicate_finder.ui.pipeline.desc_no_description": "Aucune description",
    "duplicate_finder.ui.pipeline.desc_no_algorithms": "Aucun",
    "duplicate_finder.ui.pipeline.desc_algos_more": "{count} autres",
    "duplicate_finder.ui.pipeline.desc_validation_off": "OFF",
    "duplicate_finder.ui.pipeline.desc_validation_on": "ON",
    "duplicate_finder.ui.pipeline.desc_validation_tolerance": "±{percent}%",
    "duplicate_finder.ui.pipeline.desc_validation_seconds": "±{seconds}s",
    "duplicate_finder.ui.pipeline.desc_partial_off": "OFF (analyse complète)",
    "duplicate_finder.ui.pipeline.desc_partial_from_start": "{duration:.0f}s depuis début",
    "duplicate_finder.ui.pipeline.desc_partial_from_end": "{duration:.0f}s depuis fin",

    # LSH section
    "duplicate_finder.ui.lsh.title": "⚡ LSH Acceleration (Mode Fingerprint)",
    "duplicate_finder.ui.lsh.header": "<b>LSH</b> (Locality-Sensitive Hashing) réduit les comparaisons de <b>O(N²)</b> à <b>O(N·k)</b><br>en groupant les vidéos similaires dans des buckets.<br><i>S'active automatiquement quand le nombre de vidéos dépasse le seuil.</i>",
    "duplicate_finder.ui.lsh.enable": "Activer LSH",

    # LSH threshold
    "duplicate_finder.ui.lsh.threshold_label": "Seuil d'activation:",
    "duplicate_finder.ui.lsh.threshold_tooltip": "Nombre minimum de vidéos pour activer LSH automatiquement\n100 vidéos = recommandé\nPlus bas = LSH activé plus tôt (utile pour tests)",
    "duplicate_finder.ui.lsh.threshold_value": "{value} vidéos",

    # LSH permutations
    "duplicate_finder.ui.lsh.perm_header": "Permutations MinHash:",
    "duplicate_finder.ui.lsh.perm_explain": "Nombre de hash utilisés pour créer la signature de chaque vidéo.<br><b>Plus = plus précis</b> (détecte mieux les similarités) mais <b>plus lent</b>.",
    "duplicate_finder.ui.lsh.perm_value_64": "64 (rapide, ~95% taux détection)",
    "duplicate_finder.ui.lsh.perm_value_128": "128 (recommandé, ~99% taux détection)",
    "duplicate_finder.ui.lsh.perm_value_256": "256 (très précis, ~99.9% taux détection)",

    # LSH bands
    "duplicate_finder.ui.lsh.bands_header": "Bandes LSH:",
    "duplicate_finder.ui.lsh.bands_explain": "Nombre de groupes (buckets) pour regrouper les vidéos similaires.<br><b>Plus = plus sensible</b> (trouve plus de candidats) mais <b>plus de faux positifs</b>.",
    "duplicate_finder.ui.lsh.bands_value_low": "{value} (rapide, moins sensible)",
    "duplicate_finder.ui.lsh.bands_value_balanced": "16 (équilibré, recommandé)",
    "duplicate_finder.ui.lsh.bands_value_high": "{value} (très sensible, plus de vérifications)",

    # LSH info
    "duplicate_finder.ui.lsh.info_inactive": "<b>ℹ️ LSH non actif</b> ({video_count} vidéos < seuil de {threshold})",
    "duplicate_finder.ui.lsh.info_active": "<b>ℹ️ Impact avec {video_count} vidéos:</b><br>Comparaisons: {total_pairs:,} → ~{estimated_pairs:,} (<b>{reduction_pct:.0f}% réduction</b>)"
}

# Nouvelles clés i18n (EN)
NEW_KEYS_EN = {
    # Pipeline section titles
    "duplicate_finder.ui.pipeline.duplicates_title": "🔍 DUPLICATES Pipeline",
    "duplicate_finder.ui.pipeline.scenes_title": "🎬 SCENES Pipeline",

    # Pipeline section labels
    "duplicate_finder.ui.pipeline.label": "Pipeline:",
    "duplicate_finder.ui.pipeline.select_tooltip_duplicates": "Select a pipeline for duplicate detection",
    "duplicate_finder.ui.pipeline.select_tooltip_scenes": "Select a pipeline for scene detection",

    # Buttons
    "duplicate_finder.ui.pipeline.edit_tooltip": "Edit selected pipeline",
    "duplicate_finder.ui.pipeline.new_tooltip": "Create new pipeline",

    # Description fields
    "duplicate_finder.ui.pipeline.desc_description": "Description:",
    "duplicate_finder.ui.pipeline.desc_config": "Config:",
    "duplicate_finder.ui.pipeline.desc_optimizations": "Optimizations:",
    "duplicate_finder.ui.pipeline.desc_no_description": "No description",
    "duplicate_finder.ui.pipeline.desc_no_algorithms": "None",
    "duplicate_finder.ui.pipeline.desc_algos_more": "{count} more",
    "duplicate_finder.ui.pipeline.desc_validation_off": "OFF",
    "duplicate_finder.ui.pipeline.desc_validation_on": "ON",
    "duplicate_finder.ui.pipeline.desc_validation_tolerance": "±{percent}%",
    "duplicate_finder.ui.pipeline.desc_validation_seconds": "±{seconds}s",
    "duplicate_finder.ui.pipeline.desc_partial_off": "OFF (full analysis)",
    "duplicate_finder.ui.pipeline.desc_partial_from_start": "{duration:.0f}s from start",
    "duplicate_finder.ui.pipeline.desc_partial_from_end": "{duration:.0f}s from end",

    # LSH section
    "duplicate_finder.ui.lsh.title": "⚡ LSH Acceleration (Fingerprint Mode)",
    "duplicate_finder.ui.lsh.header": "<b>LSH</b> (Locality-Sensitive Hashing) reduces comparisons from <b>O(N²)</b> to <b>O(N·k)</b><br>by grouping similar videos into buckets.<br><i>Activates automatically when video count exceeds threshold.</i>",
    "duplicate_finder.ui.lsh.enable": "Enable LSH",

    # LSH threshold
    "duplicate_finder.ui.lsh.threshold_label": "Activation threshold:",
    "duplicate_finder.ui.lsh.threshold_tooltip": "Minimum number of videos to automatically activate LSH\n100 videos = recommended\nLower = LSH activates sooner (useful for testing)",
    "duplicate_finder.ui.lsh.threshold_value": "{value} videos",

    # LSH permutations
    "duplicate_finder.ui.lsh.perm_header": "MinHash Permutations:",
    "duplicate_finder.ui.lsh.perm_explain": "Number of hashes used to create each video's signature.<br><b>More = more accurate</b> (better similarity detection) but <b>slower</b>.",
    "duplicate_finder.ui.lsh.perm_value_64": "64 (fast, ~95% detection rate)",
    "duplicate_finder.ui.lsh.perm_value_128": "128 (recommended, ~99% detection rate)",
    "duplicate_finder.ui.lsh.perm_value_256": "256 (very accurate, ~99.9% detection rate)",

    # LSH bands
    "duplicate_finder.ui.lsh.bands_header": "LSH Bands:",
    "duplicate_finder.ui.lsh.bands_explain": "Number of groups (buckets) to group similar videos.<br><b>More = more sensitive</b> (finds more candidates) but <b>more false positives</b>.",
    "duplicate_finder.ui.lsh.bands_value_low": "{value} (fast, less sensitive)",
    "duplicate_finder.ui.lsh.bands_value_balanced": "16 (balanced, recommended)",
    "duplicate_finder.ui.lsh.bands_value_high": "{value} (very sensitive, more checks)",

    # LSH info
    "duplicate_finder.ui.lsh.info_inactive": "<b>ℹ️ LSH not active</b> ({video_count} videos < threshold of {threshold})",
    "duplicate_finder.ui.lsh.info_active": "<b>ℹ️ Impact with {video_count} videos:</b><br>Comparisons: {total_pairs:,} → ~{estimated_pairs:,} (<b>{reduction_pct:.0f}% reduction</b>)"
}

def add_keys_to_file(filepath, new_keys):
    """Ajoute les nouvelles clés au fichier JSON."""
    # Lire le fichier existant
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Ajouter les nouvelles clés (ne pas écraser si existe déjà)
    updated = False
    for key, value in new_keys.items():
        if key not in data:
            data[key] = value
            updated = True
            print(f"  + {key}")

    if updated:
        # Écrire le fichier mis à jour (formaté joliment)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    else:
        print("  (Toutes les clés existent déjà)")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("AJOUT DES CLÉS I18N POUR LA NOUVELLE INTERFACE")
    print("=" * 70)

    print("\n1. Ajout des clés FR (resources/i18n/fr.json)...")
    updated_fr = add_keys_to_file('resources/i18n/fr.json', NEW_KEYS_FR)

    print("\n2. Ajout des clés EN (resources/i18n/en.json)...")
    updated_en = add_keys_to_file('resources/i18n/en.json', NEW_KEYS_EN)

    print("\n" + "=" * 70)
    if updated_fr or updated_en:
        print("✅ Clés i18n ajoutées avec succès")
        print(f"   FR: {len(NEW_KEYS_FR)} clés")
        print(f"   EN: {len(NEW_KEYS_EN)} clés")
    else:
        print("ℹ️  Aucune nouvelle clé à ajouter")
    print("=" * 70)
