#!/usr/bin/env python3
"""
Batch Translation Script for VideoFlow

This script translates all French text to English in the VideoFlow codebase.
It performs systematic string replacement while preserving code structure.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Translation mappings
TRANSLATIONS = {
    # Common UI elements
    "Fichier": "File",
    "fichier": "file",
    "fichiers": "files",
    "Dossier": "Folder",
    "dossier": "folder",
    "dossiers": "folders",
    "Ajouter": "Add",
    "ajouter": "add",
    "Supprimer": "Remove",
    "supprimer": "remove",
    "Modifier": "Modify",
    "modifier": "modify",
    "Charger": "Load",
    "charger": "load",
    "Sauvegarder": "Save",
    "sauvegarder": "save",
    "Analyser": "Analyze",
    "analyser": "analyze",
    "Démarrer": "Start",
    "démarrer": "start",
    "Arrêter": "Stop",
    "arrêter": "stop",
    "Reprendre": "Resume",
    "reprendre": "resume",
    "Annuler": "Cancel",
    "annuler": "cancel",
    "Fermer": "Close",
    "fermer": "close",
    "Quitter": "Quit",
    "quitter": "quit",

    # Status and states
    "En cours": "In progress",
    "en cours": "in progress",
    "En attente": "Pending",
    "en attente": "pending",
    "Terminé": "Completed",
    "terminé": "completed",
    "Prêt": "Ready",
    "prêt": "ready",
    "Échec": "Failed",
    "échec": "failed",
    "Erreur": "Error",
    "erreur": "error",
    "Succès": "Success",
    "succès": "success",
    "Réussi": "Successful",
    "réussi": "successful",
    "Échoué": "Failed",
    "échoué": "failed",

    # Actions and operations
    "Traitement": "Processing",
    "traitement": "processing",
    "Initialisation": "Initialization",
    "initialisation": "initialization",
    "Configuration": "Configuration",
    "configuration": "configuration",
    "Copie": "Copy",
    "copie": "copy",
    "Conversion": "Conversion",
    "conversion": "conversion",
    "Analyse": "Analysis",
    "analyse": "analysis",
    "Recherche": "Search",
    "recherche": "search",
    "Comparaison": "Comparison",
    "comparaison": "comparison",

    # Messages
    "Impossible de": "Cannot",
    "impossible de": "cannot",
    "Voulez-vous": "Do you want",
    "voulez-vous": "do you want",
    "Êtes-vous sûr": "Are you sure",
    "êtes-vous sûr": "are you sure",
    "Veuillez": "Please",
    "veuillez": "please",

    # Time and progress
    "Temps": "Time",
    "temps": "time",
    "restant": "remaining",
    "écoulé": "elapsed",
    "Durée": "Duration",
    "durée": "duration",
    "Vitesse": "Speed",
    "vitesse": "speed",

    # File operations
    "Taille": "Size",
    "taille": "size",
    "Nom": "Name",
    "nom": "name",
    "Chemin": "Path",
    "chemin": "path",
    "Type": "Type",
    "type": "type",
    "Date": "Date",
    "date": "date",

    # Results and statistics
    "Trouvé": "Found",
    "trouvé": "found",
    "Trouvés": "Found",
    "trouvés": "found",
    "Total": "Total",
    "total": "total",
    "Nombre": "Number",
    "nombre": "number",
    "Taux": "Rate",
    "taux": "rate",

    # Specific phrases
    "Erreur lors de": "Error during",
    "erreur lors de": "error during",
    "Impossible d'ouvrir": "Cannot open",
    "Aucun fichier": "No file",
    "aucun fichier": "no file",
    "Sélectionner un": "Select a",
    "sélectionner un": "select a",
    "Choisir un": "Choose a",
    "choisir un": "choose a",

    # Window and UI
    "Fenêtre": "Window",
    "fenêtre": "window",
    "Afficher": "Show",
    "afficher": "show",
    "Masquer": "Hide",
    "masquer": "hide",
    "Ouvrir": "Open",
    "ouvrir": "open",

    # Settings
    "Paramètres": "Settings",
    "paramètres": "settings",
    "Options": "Options",
    "options": "options",
    "Préférences": "Preferences",
    "préférences": "preferences",

    # Help
    "Aide": "Help",
    "aide": "help",
    "À propos": "About",
    "à propos": "about",

    # Numbers and count
    "premier": "first",
    "dernier": "last",
    "suivant": "next",
    "précédent": "previous",

    # Colors and markers
    "Vert": "Green",
    "Rouge": "Red",
    "Jaune": "Yellow",
    "Bleu": "Blue",

    # Other common terms
    "Détails": "Details",
    "détails": "details",
    "Informations": "Information",
    "informations": "information",
    "Statistiques": "Statistics",
    "statistiques": "statistics",
    "Résultats": "Results",
    "résultats": "results",
    "Aperçu": "Preview",
    "aperçu": "preview",
}

# Phrase-level translations (order matters - check longest phrases first)
PHRASE_TRANSLATIONS = [
    ("Voulez-vous vraiment", "Do you really want"),
    ("Êtes-vous sûr de vouloir", "Are you sure you want"),
    ("Impossible d'ouvrir le fichier", "Cannot open file"),
    ("Erreur lors de la lecture", "Error reading"),
    ("Erreur lors de l'écriture", "Error writing"),
    ("Erreur lors du chargement", "Error loading"),
    ("Erreur lors de la sauvegarde", "Error saving"),
    ("Aucun fichier sélectionné", "No file selected"),
    ("Sélectionner un fichier", "Select a file"),
    ("Sélectionner un dossier", "Select a folder"),
    ("Choisir un fichier", "Choose a file"),
    ("Choisir un dossier", "Choose a folder"),
    ("Démarrer l'analyse", "Start analysis"),
    ("Arrêter l'analyse", "Stop analysis"),
    ("En cours d'analyse", "Analyzing"),
    ("Analyse terminée", "Analysis completed"),
    ("Conversion en cours", "Converting"),
    ("Conversion terminée", "Conversion completed"),
    ("Traitement en cours", "Processing"),
    ("Traitement terminé", "Processing completed"),
]


def translate_file(file_path: Path) -> Tuple[int, int]:
    """
    Translate a single Python file.

    Args:
        file_path: Path to the file to translate

    Returns:
        Tuple of (lines_changed, replacements_made)
    """
    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        replacements = 0

        # Apply phrase-level translations first
        for french, english in PHRASE_TRANSLATIONS:
            if french in content:
                count = content.count(french)
                content = content.replace(french, english)
                replacements += count

        # Apply word-level translations
        for french, english in TRANSLATIONS.items():
            # Use word boundary matching for whole words only
            pattern = r'\b' + re.escape(french) + r'\b'
            matches = len(re.findall(pattern, content))
            if matches > 0:
                content = re.sub(pattern, english, content)
                replacements += matches

        # Count changed lines
        original_lines = original_content.splitlines()
        new_lines = content.splitlines()
        lines_changed = sum(1 for old, new in zip(original_lines, new_lines) if old != new)

        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return lines_changed, replacements

        return 0, 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0, 0


def find_python_files(directory: Path) -> List[Path]:
    """
    Find all Python files in directory.

    Args:
        directory: Directory to search

    Returns:
        List of Python file paths
    """
    return list(directory.rglob("*.py"))


def main():
    """Main translation function."""
    print("VideoFlow - French to English Translation")
    print("=" * 50)

    # Find project root
    script_dir = Path(__file__).parent
    src_dir = script_dir / "src"

    if not src_dir.exists():
        print(f"Error: src directory not found at {src_dir}")
        return

    # Find all Python files
    python_files = find_python_files(src_dir)
    print(f"Found {len(python_files)} Python files")
    print()

    total_files_changed = 0
    total_lines_changed = 0
    total_replacements = 0

    # Process each file
    for file_path in sorted(python_files):
        lines_changed, replacements = translate_file(file_path)

        if replacements > 0:
            total_files_changed += 1
            total_lines_changed += lines_changed
            total_replacements += replacements
            relative_path = file_path.relative_to(src_dir)
            print(f"✓ {relative_path}: {replacements} replacements, {lines_changed} lines changed")

    print()
    print("=" * 50)
    print("Translation Summary:")
    print(f"  Files processed: {len(python_files)}")
    print(f"  Files changed: {total_files_changed}")
    print(f"  Lines changed: {total_lines_changed}")
    print(f"  Total replacements: {total_replacements}")
    print("=" * 50)
    print()
    print("Translation complete!")


if __name__ == "__main__":
    main()
