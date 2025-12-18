"""
Système d'internationalisation pour le Duplicate Finder
Support: FR, EN
"""
from typing import Dict
from enum import Enum


class Language(Enum):
    """Langues supportées."""
    FR = "fr"
    EN = "en"


class I18n:
    """Gestionnaire de traductions."""

    # Langue par défaut
    _current_language = Language.FR

    # Dictionnaire de traductions
    _translations: Dict[str, Dict[str, str]] = {
        # ===== BENCHMARK UI =====
        "benchmark_title": {
            "fr": "Benchmark Multi-Pipeline",
            "en": "Multi-Pipeline Benchmark"
        },
        "benchmark_description": {
            "fr": "Testez plusieurs pipelines simultanément sur le même test set et comparez les résultats",
            "en": "Test multiple pipelines simultaneously on the same test set and compare results"
        },
        "test_set": {
            "fr": "Test Set",
            "en": "Test Set"
        },
        "wizard": {
            "fr": "Wizard",
            "en": "Wizard"
        },
        "wizard_tooltip": {
            "fr": "Créer un nouveau test set avec les fichiers chargés",
            "en": "Create a new test set with loaded files"
        },
        "pipelines_to_test": {
            "fr": "Pipelines à Tester",
            "en": "Pipelines to Test"
        },
        "select_multiple": {
            "fr": "(Sélectionnez plusieurs)",
            "en": "(Select multiple)"
        },
        "new_pipeline": {
            "fr": "Nouveau",
            "en": "New"
        },
        "new_pipeline_tooltip": {
            "fr": "Créer un nouveau pipeline",
            "en": "Create a new pipeline"
        },
        "start_benchmark": {
            "fr": "DÉMARRER LE BENCHMARK",
            "en": "START BENCHMARK"
        },
        "stop": {
            "fr": "ARRÊTER",
            "en": "STOP"
        },

        # ===== PROGRESS =====
        "progress": {
            "fr": "Progression",
            "en": "Progress"
        },
        "global_progress": {
            "fr": "Progression Globale",
            "en": "Global Progress"
        },
        "detail_per_pipeline": {
            "fr": "Détail par Pipeline",
            "en": "Detail per Pipeline"
        },
        "ready": {
            "fr": "Prêt",
            "en": "Ready"
        },
        "starting": {
            "fr": "Démarrage...",
            "en": "Starting..."
        },
        "stopping": {
            "fr": "Arrêt en cours...",
            "en": "Stopping..."
        },
        "completed": {
            "fr": "Terminé",
            "en": "Completed"
        },
        "pipeline_x_of_y": {
            "fr": "Pipeline {current}/{total}: {name}",
            "en": "Pipeline {current}/{total}: {name}"
        },
        "processing_pair": {
            "fr": "Traitement paire {current}/{total}: {video1} ↔ {video2}",
            "en": "Processing pair {current}/{total}: {video1} ↔ {video2}"
        },

        # ===== RESULTS =====
        "comparative_results": {
            "fr": "Résultats Comparatifs",
            "en": "Comparative Results"
        },
        "metric": {
            "fr": "Métrique",
            "en": "Metric"
        },
        "precision": {
            "fr": "Precision",
            "en": "Precision"
        },
        "recall": {
            "fr": "Recall",
            "en": "Recall"
        },
        "f1_score": {
            "fr": "F1-Score",
            "en": "F1-Score"
        },
        "true_positives": {
            "fr": "True Positives",
            "en": "True Positives"
        },
        "false_positives": {
            "fr": "False Positives",
            "en": "False Positives"
        },
        "false_negatives": {
            "fr": "False Negatives",
            "en": "False Negatives"
        },

        # ===== DASHBOARD =====
        "open_detailed_dashboard": {
            "fr": "Ouvrir le Dashboard Détaillé",
            "en": "Open Detailed Dashboard"
        },
        "dashboard_title": {
            "fr": "Benchmark Dashboard",
            "en": "Benchmark Dashboard"
        },
        "metrics_and_graphs": {
            "fr": "Métriques & Graphiques",
            "en": "Metrics & Charts"
        },
        "history": {
            "fr": "Historique",
            "en": "History"
        },
        "benchmark_history": {
            "fr": "Historique des Benchmarks",
            "en": "Benchmark History"
        },
        "refresh": {
            "fr": "Actualiser",
            "en": "Refresh"
        },
        "run_id": {
            "fr": "Run ID",
            "en": "Run ID"
        },
        "date": {
            "fr": "Date",
            "en": "Date"
        },
        "pipelines": {
            "fr": "Pipelines",
            "en": "Pipelines"
        },
        "pairs": {
            "fr": "Paires",
            "en": "Pairs"
        },
        "avg_f1": {
            "fr": "F1 Moyen",
            "en": "Avg F1"
        },
        "actions": {
            "fr": "Actions",
            "en": "Actions"
        },
        "details": {
            "fr": "Détails",
            "en": "Details"
        },
        "select_run_for_details": {
            "fr": "Sélectionnez un run pour voir les détails",
            "en": "Select a run to view details"
        },
        "selected_run_details": {
            "fr": "Détails du Run Sélectionné",
            "en": "Selected Run Details"
        },
        "no_results_available": {
            "fr": "Aucun résultat disponible",
            "en": "No results available"
        },
        "pipeline": {
            "fr": "Pipeline",
            "en": "Pipeline"
        },

        # ===== ERRORS =====
        "error": {
            "fr": "Erreur",
            "en": "Error"
        },
        "select_test_set": {
            "fr": "Veuillez sélectionner un test set",
            "en": "Please select a test set"
        },
        "select_at_least_one_pipeline": {
            "fr": "Veuillez sélectionner au moins un pipeline à tester",
            "en": "Please select at least one pipeline to test"
        },
        "test_set_empty": {
            "fr": "Le test set '{name}' ne contient aucune paire",
            "en": "Test set '{name}' contains no pairs"
        },
        "benchmark_error": {
            "fr": "Erreur Benchmark",
            "en": "Benchmark Error"
        },
        "error_occurred": {
            "fr": "Une erreur est survenue:\\n\\n{error}",
            "en": "An error occurred:\\n\\n{error}"
        },

        # ===== TEST PAIR LABELS =====
        "scene_found": {
            "fr": "Scène trouvée",
            "en": "Scene found"
        },
        "scene_not_found": {
            "fr": "Scène non trouvée",
            "en": "Scene not found"
        },
        "duplicate": {
            "fr": "Duplicata",
            "en": "Duplicate"
        },
        "not_duplicate": {
            "fr": "Non-duplicata",
            "en": "Not duplicate"
        },
        "unknown": {
            "fr": "Inconnu",
            "en": "Unknown"
        },
        "positive": {
            "fr": "Positif",
            "en": "Positive"
        },
        "negative": {
            "fr": "Négatif",
            "en": "Negative"
        },

        # ===== TEST SET UI =====
        "scenes_found": {
            "fr": "Scènes trouvées",
            "en": "Scenes found"
        },
        "scenes_not_found": {
            "fr": "Scènes non trouvées",
            "en": "Scenes not found"
        },
        "test_set_wizard": {
            "fr": "Assistant Test Set",
            "en": "Test Set Wizard"
        },
        "expected_result": {
            "fr": "Résultat attendu",
            "en": "Expected result"
        },
        "default_expected": {
            "fr": "Par défaut",
            "en": "Default"
        },
        "include_sample_not_found": {
            "fr": "Inclure un échantillon de paires scènes non trouvées (résultat = scene_not_found)",
            "en": "Include a sample of scene not found pairs (result = scene_not_found)"
        },
        "max_not_found_count": {
            "fr": "Nombre max de scènes non trouvées",
            "en": "Max count of scenes not found"
        },
        "name_label": {
            "fr": "Nom:",
            "en": "Name:"
        },
        "name_placeholder": {
            "fr": "Ex: validation_set_2025",
            "en": "e.g.: validation_set_2025"
        },
        "cancel": {
            "fr": "Annuler",
            "en": "Cancel"
        },
        "video_files": {
            "fr": "Fichiers vidéo:",
            "en": "Video files:"
        },
        "files_pairs_stats": {
            "fr": "Fichiers: {count} | Paires estimées: {pairs}",
            "en": "Files: {count} | Estimated pairs: {pairs}"
        },
        "video_1": {
            "fr": "Vidéo 1:",
            "en": "Video 1:"
        },
        "video_1_placeholder": {
            "fr": "Chemin vers la première vidéo",
            "en": "Path to first video"
        },
        "video_2": {
            "fr": "Vidéo 2:",
            "en": "Video 2:"
        },
        "video_2_placeholder": {
            "fr": "Chemin vers la deuxième vidéo",
            "en": "Path to second video"
        },
        "notes": {
            "fr": "Notes:",
            "en": "Notes:"
        },
        "notes_placeholder": {
            "fr": "Notes optionnelles",
            "en": "Optional notes"
        },
        "pairs_added": {
            "fr": "Paires ajoutées:",
            "en": "Added pairs:"
        },
        "pairs_count": {
            "fr": "Paires: {count}",
            "en": "Pairs: {count}"
        },
        "json_file_placeholder": {
            "fr": "Sélectionnez un fichier pairs.json",
            "en": "Select a pairs.json file"
        },
        "content_preview": {
            "fr": "Aperçu du contenu:",
            "en": "Content preview:"
        },
        "no_file_selected": {
            "fr": "Aucun fichier sélectionné",
            "en": "No file selected"
        },
        "ready_to_create_from_db": {
            "fr": "Prêt à créer le test set depuis la base de données",
            "en": "Ready to create test set from database"
        },
        "error": {
            "fr": "Erreur",
            "en": "Error"
        },
        "success": {
            "fr": "Succès",
            "en": "Success"
        },
        "select_both_videos": {
            "fr": "Veuillez sélectionner les deux vidéos",
            "en": "Please select both videos"
        },
        "videos_must_differ": {
            "fr": "Les deux vidéos doivent être différentes",
            "en": "Both videos must be different"
        },
        "enter_test_set_name": {
            "fr": "Veuillez entrer un nom pour le test set",
            "en": "Please enter a name for the test set"
        },
        "test_set_creation_error": {
            "fr": "Erreur lors de la création du test set:\\n{error}",
            "en": "Error creating test set:\\n{error}"
        },
        "need_at_least_2_files": {
            "fr": "Il faut au moins 2 fichiers pour créer des paires",
            "en": "At least 2 files are needed to create pairs"
        },
        "test_set_created_pairs": {
            "fr": "Test set '{name}' créé avec {count} paires",
            "en": "Test set '{name}' created with {count} pairs"
        },
        "no_pairs_added": {
            "fr": "Aucune paire ajoutée",
            "en": "No pairs added"
        },
        "select_valid_json": {
            "fr": "Veuillez sélectionner un fichier JSON valide",
            "en": "Please select a valid JSON file"
        },
        "test_set_imported_pairs": {
            "fr": "Test set '{name}' créé avec {count} paires importées",
            "en": "Test set '{name}' created with {count} imported pairs"
        },
        "no_comparisons_in_db": {
            "fr": "Aucune comparaison trouvée dans la base de données",
            "en": "No comparisons found in database"
        },
        "test_set_created_from_results": {
            "fr": "Test set '{name}' créé avec {count} paires depuis les résultats",
            "en": "Test set '{name}' created with {count} pairs from results"
        },
        "invalid_json_format_missing_pairs": {
            "fr": "Format JSON invalide: clé 'pairs' manquante",
            "en": "Invalid JSON format: missing 'pairs' key"
        },
        "json_read_error": {
            "fr": "Erreur lors de la lecture du fichier:\\n{error}",
            "en": "Error reading file:\\n{error}"
        },
        "error_prefix": {
            "fr": "Erreur: {error}",
            "en": "Error: {error}"
        },
        "file_stats_with_time": {
            "fr": "📊 {count} fichiers → {pairs} paires | ⏱️ Temps estimé: {time}",
            "en": "📊 {count} files → {pairs} pairs | ⏱️ Estimated time: {time}"
        },
        "wizard_header": {
            "fr": "🧙 <b>Assistant de Création de Test Set</b>",
            "en": "🧙 <b>Test Set Creation Wizard</b>"
        },
        "wizard_description": {
            "fr": "Cet assistant vous aide à créer un test set pour valider vos pipelines de détection. Choisissez la méthode qui vous convient :",
            "en": "This wizard helps you create a test set to validate your detection pipelines. Choose the method that suits you:"
        },
        "test_set_name_group": {
            "fr": "Nom du Test Set",
            "en": "Test Set Name"
        },
        "create_test_set": {
            "fr": "✅ Créer Test Set",
            "en": "✅ Create Test Set"
        },
        "tab_file_list": {
            "fr": "📁 Liste de Fichiers",
            "en": "📁 File List"
        },
        "tab_manual_pairs": {
            "fr": "✍️ Paires Manuelles",
            "en": "✍️ Manual Pairs"
        },
        "tab_import_json": {
            "fr": "📥 Import JSON",
            "en": "📥 Import JSON"
        },
        "tab_from_results": {
            "fr": "📊 Depuis Résultats",
            "en": "📊 From Results"
        },
        "file_list_instructions": {
            "fr": "📁 <b>Générer des paires depuis une liste de fichiers</b><br>Sélectionnez des fichiers vidéo, puis choisissez comment générer les paires de test.",
            "en": "📁 <b>Generate pairs from a file list</b><br>Select video files, then choose how to generate test pairs."
        },
        "use_current_files": {
            "fr": "✅ Utiliser les Fichiers Actuels",
            "en": "✅ Use Current Files"
        },
        "add_files": {
            "fr": "➕ Ajouter Fichiers",
            "en": "➕ Add Files"
        },
        "add_folder": {
            "fr": "📂 Ajouter Dossier",
            "en": "📂 Add Folder"
        },
        "remove": {
            "fr": "🗑️ Retirer",
            "en": "🗑️ Remove"
        },
        "clear_all": {
            "fr": "🧹 Tout Effacer",
            "en": "🧹 Clear All"
        },
        "generation_strategy": {
            "fr": "Stratégie de Génération",
            "en": "Generation Strategy"
        },
        "all_possible_pairs": {
            "fr": "Toutes les paires possibles (N×(N-1)/2 paires)",
            "en": "All possible pairs (N×(N-1)/2 pairs)"
        },
        "sequential_pairs": {
            "fr": "Paires séquentielles (comparer chaque fichier avec le suivant)",
            "en": "Sequential pairs (compare each file with the next)"
        },
        "random_pairs": {
            "fr": "Paires aléatoires (nombre spécifique)",
            "en": "Random pairs (specific number)"
        },
        "number_of_pairs": {
            "fr": "   Nombre de paires:",
            "en": "   Number of pairs:"
        },
        "manual_instructions": {
            "fr": "✍️ <b>Ajouter des paires manuellement</b><br>Créez des paires de test en sélectionnant deux vidéos et en spécifiant le résultat attendu.",
            "en": "✍️ <b>Add pairs manually</b><br>Create test pairs by selecting two videos and specifying the expected result."
        },
        "add_pair_group": {
            "fr": "Ajouter une Paire",
            "en": "Add a Pair"
        },
        "browse": {
            "fr": "📂 Parcourir",
            "en": "📂 Browse"
        },
        "add_this_pair": {
            "fr": "➕ Ajouter cette paire",
            "en": "➕ Add this pair"
        },
        "table_header_video1": {
            "fr": "Vidéo 1",
            "en": "Video 1"
        },
        "table_header_video2": {
            "fr": "Vidéo 2",
            "en": "Video 2"
        },
        "table_header_expected": {
            "fr": "Attendu",
            "en": "Expected"
        },
        "import_instructions": {
            "fr": "📥 <b>Importer depuis un fichier JSON</b><br>Importez un fichier pairs.json existant pour créer rapidement un test set.",
            "en": "📥 <b>Import from a JSON file</b><br>Import an existing pairs.json file to quickly create a test set."
        },
        "json_file_group": {
            "fr": "Fichier JSON",
            "en": "JSON File"
        },
        "results_instructions": {
            "fr": "📊 <b>Créer depuis des résultats d'analyse</b><br>Créez un test set basé sur les résultats d'une analyse précédente. Utile pour valider que les détections sont reproductibles.",
            "en": "📊 <b>Create from analysis results</b><br>Create a test set based on previous analysis results. Useful for validating that detections are reproducible."
        },
        "options": {
            "fr": "Options",
            "en": "Options"
        },
        "include_duplicates": {
            "fr": "Inclure les paires détectées comme duplicata (résultat = duplicate)",
            "en": "Include pairs detected as duplicates (result = duplicate)"
        },
        "db_query_info": {
            "fr": "ℹ️ Cette méthode nécessite une analyse complétée avec des résultats dans la base de données. Elle créera un test set basé sur les comparaisons stockées.",
            "en": "ℹ️ This method requires a completed analysis with results in the database. It will create a test set based on stored comparisons."
        },
        "files_loaded_title": {
            "fr": "Fichiers Chargés",
            "en": "Files Loaded"
        },
        "files_loaded_message": {
            "fr": "✅ {count} fichiers chargés depuis l'onglet Files",
            "en": "✅ {count} files loaded from Files tab"
        },
        "select_video_files": {
            "fr": "Sélectionner des fichiers vidéo",
            "en": "Select video files"
        },
        "video_files_filter": {
            "fr": "Video Files (*.mp4 *.avi *.mkv *.mov *.flv *.wmv *.webm);;All Files (*)",
            "en": "Video Files (*.mp4 *.avi *.mkv *.mov *.flv *.wmv *.webm);;All Files (*)"
        },
        "select_folder": {
            "fr": "Sélectionner un dossier",
            "en": "Select a folder"
        },
        "select_video": {
            "fr": "Sélectionner une vidéo",
            "en": "Select a video"
        },
        "select_pairs_json": {
            "fr": "Sélectionner pairs.json",
            "en": "Select pairs.json"
        },
        "json_files_filter": {
            "fr": "JSON Files (*.json);;All Files (*)",
            "en": "JSON Files (*.json);;All Files (*)"
        },
        "json_preview_file": {
            "fr": "Fichier: {filename}",
            "en": "File: {filename}"
        },
        "json_preview_pairs_count": {
            "fr": "Paires: {count}",
            "en": "Pairs: {count}"
        },
        "json_preview_header": {
            "fr": "Aperçu (5 premières paires):",
            "en": "Preview (first 5 pairs):"
        },
        "json_preview_pair": {
            "fr": "• {short} ↔ {long}",
            "en": "• {short} ↔ {long}"
        },
        "json_preview_expected": {
            "fr": "   Attendu: {expected}",
            "en": "   Expected: {expected}"
        },
        "files_loaded_tooltip": {
            "fr": "{count} fichiers déjà chargés dans l'onglet Files",
            "en": "{count} files already loaded in Files tab"
        },

        # ===== PIPELINE CREATION =====
        "new_pipeline_title": {
            "fr": "Nouveau Pipeline",
            "en": "New Pipeline"
        },
        "name": {
            "fr": "Nom",
            "en": "Name"
        },
        "description": {
            "fr": "Description",
            "en": "Description"
        },
        "global_threshold": {
            "fr": "Seuil global",
            "en": "Global threshold"
        },
        "global_threshold_help": {
            "fr": "Score minimum (en %) que le pipeline doit atteindre en mode Pondération/Hybride. 80% = équilibré, 90% = strict, 70% = permissif.",
            "en": "Minimum score (%) the pipeline must reach in weighting/hybrid mode. 80% balanced, 90% strict, 70% permissive."
        },
        "pipeline_default_config_info": {
            "fr": "Un pipeline sera créé avec une configuration par défaut.\\nVous pourrez le modifier plus tard dans le Dashboard.",
            "en": "A pipeline will be created with default configuration.\\nYou can modify it later in the Dashboard."
        },
        "create": {
            "fr": "Créer",
            "en": "Create"
        },
        "cancel": {
            "fr": "Annuler",
            "en": "Cancel"
        },
        "pipeline_created": {
            "fr": "Pipeline créé",
            "en": "Pipeline created"
        },
        "pipeline_created_success": {
            "fr": "Pipeline '{name}' créé avec succès!",
            "en": "Pipeline '{name}' created successfully!"
        },

        # ===== STATUS =====
        "in_progress": {
            "fr": "en cours...",
            "en": "in progress..."
        },
        "waiting": {
            "fr": "en attente",
            "en": "waiting"
        },

        # ===== MISC =====
        "methods": {
            "fr": "méthodes",
            "en": "methods"
        },
        "tested_pipelines": {
            "fr": "Pipelines testés",
            "en": "Tested pipelines"
        },
        "test_pairs": {
            "fr": "Paires de test",
            "en": "Test pairs"
        },

        # ===== PIPELINE EDITOR (UNIFIED) =====
        "pipeline_editor_header": {
            "fr": "Éditeur de pipeline",
            "en": "Pipeline editor"
        },
        "pipeline_editor_subtitle": {
            "fr": "Choisissez un preset, ajustez les méthodes et leurs paramètres. Filtering = arrêt au premier rejet, Weighting = moyenne pondérée, Hybrid = mix des deux.",
            "en": "Pick a preset, tune methods and parameters. Filtering = stop on first reject, Weighting = weighted average, Hybrid = mix of both."
        },
        "method_editor_title": {
            "fr": "Méthode du pipeline",
            "en": "Pipeline method"
        },
        "method_editor_header": {
            "fr": "Configurer la méthode : paramètres et conseils",
            "en": "Configure method: parameters and tips"
        },
        "field_method": {
            "fr": "Méthode",
            "en": "Method"
        },
        "enabled": {
            "fr": "Activé",
            "en": "Enabled"
        },
        "weight": {
            "fr": "Poids",
            "en": "Weight"
        },
        "use_case": {
            "fr": "Cas d'usage",
            "en": "Use case"
        },
        "speed": {
            "fr": "Vitesse",
            "en": "Speed"
        },
        "preset": {
            "fr": "Preset",
            "en": "Preset"
        },
        "preset_none": {
            "fr": "Aucun preset",
            "en": "No preset"
        },
        "pipeline_methods": {
            "fr": "Méthodes du pipeline",
            "en": "Pipeline methods"
        },
        "add": {
            "fr": "Ajouter",
            "en": "Add"
        },
        "edit": {
            "fr": "Éditer",
            "en": "Edit"
        },
        "delete": {
            "fr": "Supprimer",
            "en": "Delete"
        },
        "save": {
            "fr": "Sauvegarder",
            "en": "Save"
        },
        "success": {
            "fr": "Succès",
            "en": "Success"
        },
        "pipeline_saved": {
            "fr": "Pipeline '{name}' sauvegardé.",
            "en": "Pipeline '{name}' saved."
        },
        "save_failed": {
            "fr": "Impossible de sauvegarder le pipeline.",
            "en": "Failed to save pipeline."
        },
        "validation": {
            "fr": "Validation",
            "en": "Validation"
        },
        "error_name_required": {
            "fr": "Le nom est requis.",
            "en": "Name is required."
        },
        "error_methods_required": {
            "fr": "Ajoutez au moins une méthode.",
            "en": "Add at least one method."
        },
        "error_name_exists": {
            "fr": "Un pipeline nommé '{name}' existe déjà.",
            "en": "A pipeline named '{name}' already exists."
        },
        "preview": {
            "fr": "Aperçu",
            "en": "Preview"
        },
        "mode_help_filtering": {
            "fr": "Filtering : exécute les méthodes en séquence, arrêt au premier rejet.",
            "en": "Filtering: run methods in sequence, stop on first reject."
        },
        "mode_help_weighting": {
            "fr": "Weighting : calcule une moyenne pondérée des scores et compare à un seuil global.",
            "en": "Weighting: compute weighted average of scores and compare to a global threshold."
        },
        "mode_help_hybrid": {
            "fr": "Hybrid : moyenne pondérée + seuils individuels pour éviter les faux positifs.",
            "en": "Hybrid: weighted average plus per-method thresholds to avoid false positives."
        },
        "unknown_mode": {
            "fr": "Mode inconnu",
            "en": "Unknown mode"
        },
        "confirm_enable_label": {
            "fr": "Activer la confirmation visuelle (pHash)",
            "en": "Enable visual confirmation (pHash)"
        },
        "confirm_phash_threshold": {
            "fr": "Seuil pHash (bits)",
            "en": "pHash threshold (bits)"
        },
        "confirm_frame_rate": {
            "fr": "Taux de frames similaires requis (0-1)",
            "en": "Required similar frame rate (0-1)"
        },
        "confirm_n_frames": {
            "fr": "Nombre de frames échantillonnées",
            "en": "Number of sampled frames"
        },
        "confirm_search_window": {
            "fr": "Balayage de la longue vidéo (sliding window)",
            "en": "Search along the full long video (sliding window)"
        },
        "confirm_step_seconds": {
            "fr": "Pas de balayage (secondes)",
            "en": "Sliding step (seconds)"
        },
        "confirm_help": {
            "fr": "Après acceptation du pipeline, une vérification visuelle pHash confirme ou rejette le doublon.",
            "en": "After the pipeline accepts, a pHash visual check confirms or rejects the duplicate."
        },
        "confirm_section": {
            "fr": "Confirmation visuelle (pHash)",
            "en": "Visual confirmation (pHash)"
        },

        # ===== PARAM HELP =====
        "param_help.color_histogram.threshold": {
            "fr": "Seuil de similarité (0-100). Plus haut = moins de faux positifs.",
            "en": "Similarity threshold (0-100). Higher = fewer false positives."
        },
        "param_help.color_histogram.bins": {
            "fr": "Taille d'histogramme par canal (H,S,V). Plus grand = plus précis, plus lent.",
            "en": "Histogram bin size per channel (H,S,V). Larger = more precise, slower."
        },
        "param_help.motion_analysis.correlation_threshold": {
            "fr": "Seuil de corrélation des vecteurs de mouvement (0-100).",
            "en": "Motion vector correlation threshold (0-100)."
        },
        "param_help.motion_analysis.sample_interval": {
            "fr": "Espacement des frames échantillonnées. Plus petit = plus précis, plus lent.",
            "en": "Frame sampling interval. Smaller = more precise, slower."
        },
        "param_help.motion_analysis.min_variance": {
            "fr": "Variance minimale des mouvements avant de considérer la vidéo comme statique.",
            "en": "Minimum motion variance before treating the video as static."
        },
        "param_help.dct.threshold": {
            "fr": "Seuil de similarité fréquentielle (0-100).",
            "en": "Frequency similarity threshold (0-100)."
        },
        "param_help.dct.num_coeffs": {
            "fr": "Nombre de coefficients DCT utilisés. Plus haut = plus robuste, plus lent.",
            "en": "Number of DCT coefficients. Higher = more robust, slower."
        },
        "param_help.dct.block_size": {
            "fr": "Taille de bloc DCT (par défaut 8).",
            "en": "DCT block size (default 8)."
        },
        "param_help.dct.sample_interval": {
            "fr": "Intervalle d'échantillonnage des frames (secondes). Plus petit = plus précis, plus lent.",
            "en": "Frame sampling interval (seconds). Smaller = more precise, slower."
        },
        "param_help.dct.num_samples": {
            "fr": "Nombre minimal de frames échantillonnées. Plus haut = plus précis, plus lent.",
            "en": "Minimum number of sampled frames. Higher = more precise, slower."
        },
        "param_help.ssim.threshold": {
            "fr": "Seuil SSIM (0-1).",
            "en": "SSIM threshold (0-1)."
        },
        "param_help.ssim.window_size": {
            "fr": "Taille de fenêtre (généralement 7 ou 11).",
            "en": "Window size (typically 7 or 11)."
        },
        "param_help.ssim.sample_interval": {
            "fr": "Intervalle d'échantillonnage des frames (secondes). Plus petit = plus précis, plus lent.",
            "en": "Frame sampling interval (seconds). Smaller = more precise, slower."
        },
        "param_help.ssim.num_samples": {
            "fr": "Nombre minimal de frames SSIM. Plus haut = plus précis, plus lent.",
            "en": "Minimum number of SSIM sampled frames. Higher = more precise, slower."
        },
        "param_help.ssim.resize": {
            "fr": "Redimensionnement des frames avant SSIM (ex: 320x180) pour accélérer.",
            "en": "Resize frames before SSIM (e.g., 320x180) to speed up."
        },
        "param_help.edge.threshold": {
            "fr": "Seuil de densité de bords (0-100).",
            "en": "Edge density threshold (0-100)."
        },
        "param_help.edge.canny_low": {
            "fr": "Seuil bas de Canny.",
            "en": "Canny low threshold."
        },
        "param_help.edge.canny_high": {
            "fr": "Seuil haut de Canny.",
            "en": "Canny high threshold."
        },
        "param_help.edge.grid_size": {
            "fr": "Taille de grille pour l'analyse spatiale (ex: 4x4).",
            "en": "Grid size for spatial analysis (e.g., 4x4)."
        },
        "param_help.feature.threshold": {
            "fr": "Seuil de score de matching (0-100).",
            "en": "Matching score threshold (0-100)."
        },
        "param_help.feature.detector": {
            "fr": "Type de détecteur (ORB/SIFT/AKAZE).",
            "en": "Detector type (ORB/SIFT/AKAZE)."
        },
        "param_help.feature.max_features": {
            "fr": "Nombre max de points clés. Plus haut = plus précis, plus lent.",
            "en": "Max keypoints. Higher = more precise, slower."
        },
        "param_help.feature.min_matches": {
            "fr": "Nombre minimal de correspondances pour accepter le match.",
            "en": "Minimum number of matches required to accept."
        },
        "param_help.feature.ratio_test": {
            "fr": "Ratio test de Lowe (0-1). Plus petit = plus strict.",
            "en": "Lowe ratio test (0-1). Smaller = stricter."
        },
        "param_help.strategy3.scene_threshold": {
            "fr": "Seuil de détection de scènes (plus haut = moins de splits).",
            "en": "Scene detection threshold (higher = fewer splits)."
        },
        "param_help.strategy3.dct_threshold": {
            "fr": "Seuil DCT utilisé en vérification.",
            "en": "DCT threshold used in verification."
        },
        "param_help.strategy3.sequence_threshold": {
            "fr": "Seuil global séquence (0-100).",
            "en": "Global sequence threshold (0-100)."
        },
        "param_help.strategy3.num_samples": {
            "fr": "Nombre d'échantillons dans la séquence.",
            "en": "Number of samples in the sequence."
        },
        "param_help.strategy3.warmup_seconds": {
            "fr": "Temps ignoré en début de vidéo.",
            "en": "Time ignored at start of video."
        },
        "param_help.strategy3.max_workers": {
            "fr": "Workers parallèles pour cette méthode.",
            "en": "Parallel workers for this method."
        },
        "param_help.optical_flow.threshold": {
            "fr": "Seuil de similarité du flux optique (0-100).",
            "en": "Optical flow similarity threshold (0-100)."
        },
        "param_help.optical_flow.max_frames": {
            "fr": "Nombre max de frames échantillonnées pour le flux.",
            "en": "Maximum sampled frames for flow."
        },
        "param_help.optical_flow.frame_step": {
            "fr": "Pas entre frames échantillonnées (plus petit = plus précis, plus lent).",
            "en": "Step between sampled frames (smaller = more precise, slower)."
        },
        "param_help.optical_flow.min_variance": {
            "fr": "Variance minimale du flux (0 = très permissif). En dessous, on considère la scène comme statique.",
            "en": "Minimum flow variance (0 = very permissive). Below this, treat scene as static."
        },
        "param_help.optical_flow.resize": {
            "fr": "Redimensionnement des frames avant flux optique (ex: 320x180) pour accélérer.",
            "en": "Resize frames before optical flow (e.g., 320x180) to speed up."
        },
        "param_help.optical_flow.min_variance": {
            "fr": "Variance minimale de flux avant de considérer la scène comme statique.",
            "en": "Minimum flow variance before treating the scene as static."
        },
        "param_help.framehash.hash_size": {
            "fr": "Taille du hash (hash_size x hash_size).",
            "en": "Hash size (hash_size x hash_size)."
        },
        "param_help.framehash.threshold": {
            "fr": "Seuil de similarité du hash (0-100).",
            "en": "Hash similarity threshold (0-100)."
        },
        "param_help.framehash.sample_rate": {
            "fr": "Pas d'échantillonnage des frames (toutes les N frames).",
            "en": "Frame sampling step (every N frames)."
        },
        "param_help.framehash.max_samples": {
            "fr": "Nombre maximum de frames échantillonnées (limite de sécurité).",
            "en": "Maximum number of sampled frames (safety limit)."
        },

        # ===== VISUALIZER =====
        "pipeline_visual_title": {
            "fr": "Visualisation: {name}",
            "en": "Visualization: {name}"
        },
        "viz_start": {
            "fr": "DÉBUT",
            "en": "START"
        },
        "viz_decision_filtering": {
            "fr": "Toutes les méthodes acceptent ?",
            "en": "Do all methods accept?"
        },
        "viz_decision_weighting": {
            "fr": "Score pondéré ≥ seuil ?",
            "en": "Weighted score ≥ threshold?"
        },
        "viz_decision_hybrid": {
            "fr": "Seuils individuels OK ET score pondéré ≥ seuil ?",
            "en": "Per-method thresholds OK AND weighted score ≥ threshold?"
        },
        "viz_accepted": {
            "fr": "ACCEPTÉ",
            "en": "ACCEPTED"
        },
        "viz_rejected": {
            "fr": "REJETÉ",
            "en": "REJECTED"
        },
        "viz_yes": {
            "fr": "OUI",
            "en": "YES"
        },
        "viz_no": {
            "fr": "NON",
            "en": "NO"
        },
        "no_description": {
            "fr": "Aucune description",
            "en": "No description"
        },
    }

    @classmethod
    def set_language(cls, language: Language):
        """Change la langue courante."""
        cls._current_language = language

    @classmethod
    def get_language(cls) -> Language:
        """Retourne la langue courante."""
        return cls._current_language

    @classmethod
    def t(cls, key: str, **kwargs) -> str:
        """
        Traduit une clé dans la langue courante.

        Args:
            key: Clé de traduction
            **kwargs: Variables à interpoler dans la traduction

        Returns:
            Texte traduit

        Example:
            >>> I18n.t("pipeline_x_of_y", current=2, total=5, name="Test")
            "Pipeline 2/5: Test"
        """
        translations = cls._translations.get(key)
        if not translations:
            return f"[MISSING: {key}]"

        lang = cls._current_language.value
        text = translations.get(lang, translations.get("en", key))

        # Interpoler les variables
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError as e:
                return f"[ERROR: {key} - missing variable {e}]"

        return text

    @classmethod
    def tr(cls, key: str, **kwargs) -> str:
        """Alias court pour t()."""
        return cls.t(key, **kwargs)
