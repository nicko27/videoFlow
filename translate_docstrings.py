#!/usr/bin/env python3
"""
Docstring Translation Script for VideoFlow

This script translates French docstrings and comments to English.
"""

import re
from pathlib import Path
from typing import List, Tuple

# Docstring translation patterns
DOCSTRING_TRANSLATIONS = {
    # Common docstring starts
    "Constructeur": "Constructor",
    "Retourne": "Returns",
    "Définit": "Sets",
    "Ajoute": "Adds",
    "Supprime": "Removes",
    "Gestion": "Handling",
    "Dessine": "Draws",
    "Calcule": "Calculates",
    "Convertit": "Converts",
    "Vérifie": "Checks",
    "Charge": "Loads",
    "Sauvegarde": "Saves",
    "Annule": "Cancels",
    "Termine": "Finishes",
    "Ouvre": "Opens",
    "Ferme": "Closes",

    # Objects and concepts
    "de base pour tous les plugins": "base class for all plugins",
    "le plugin": "the plugin",
    "la liste": "the list",
    "la position": "the position",
    "le nombre": "the number",
    "le numéro": "the number",
    "la frame": "the frame",
    "les frames": "the frames",
    "la timeline": "the timeline",
    "le segment": "the segment",
    "les segments": "the segments",
    "la vidéo": "the video",
    "les vidéos": "the videos",
    "la window": "the window",
    "la boîte de dialogue": "the dialog box",
    "le marqueur": "the marker",
    "les marqueurs": "the markers",

    # Actions
    "du clic souris": "of mouse click",
    "du mouvement souris": "of mouse movement",
    "en pixels": "in pixels",
    "en numéro": "into number",
    "en position": "into position",
    "pour sélectionner": "to select",
    "pour tous": "for all",
    "de la": "of the",
    "pour la": "for the",
    "avec": "with",
    "dans": "in",
    "sur": "on",

    # States
    "in progress": "in progress",
    "courante": "current",
    "spécifiée": "specified",
    "total de": "total",
    "principale de": "main",

    # Window titles and UI
    "Éditeur de Vidéos": "Video Editor",
    "Convertisseur de Vidéos": "Video Converter",
    "Recherche de Doublons": "Duplicate Finder",
    "Fusion de Vidéos": "Video Merger",
    "Gestionnaire de Copie": "Copy Manager",

    # Errors
    "Error lors de": "Error during",
    "Error lors du": "Error during",
    "Error lors de la": "Error during",
    "Error lors de l'": "Error during",
}

# Multi-word phrase translations
PHRASE_PATTERNS = [
    (r"Constructeur de base pour tous les plugins", "Base constructor for all plugins"),
    (r"Configure le plugin", "Configures the plugin"),
    (r"Représente un segment de la timeline", "Represents a timeline segment"),
    (r"Widget de timeline pour l'éditeur vidéo", "Timeline widget for the video editor"),
    (r"Définit le nombre total de frames", "Sets the total number of frames"),
    (r"Définit la frame courante", "Sets the current frame"),
    (r"Ajoute un marqueur à la position spécifiée", "Adds a marker at the specified position"),
    (r"Termine le segment in progress", "Finishes the segment in progress"),
    (r"Annule le segment in progress", "Cancels the segment in progress"),
    (r"Retourne la liste des segments", "Returns the list of segments"),
    (r"Gestion du clic souris", "Mouse click handling"),
    (r"Gestion du mouvement souris", "Mouse movement handling"),
    (r"Convertit une position en pixels en numéro de frame", "Converts a position in pixels to frame number"),
    (r"Convertit un numéro de frame en position en pixels", "Converts a frame number to position in pixels"),
    (r"Dessine la timeline", "Draws the timeline"),
    (r"Module de la window principale", "Main window module"),
    (r"Window principale de", "Main window for"),
    (r"Ouvre une boîte de dialogue pour sélectionner", "Opens a dialog to select"),
    (r"Error lors de l'ouverture de la vidéo", "Error opening video"),
]


def translate_file_content(content: str) -> Tuple[str, int]:
    """
    Translate French docstrings and comments in content.

    Args:
        content: File content to translate

    Returns:
        Tuple of (translated_content, num_changes)
    """
    original_content = content
    changes = 0

    # Apply phrase patterns first
    for french_pattern, english in PHRASE_PATTERNS:
        if re.search(french_pattern, content):
            content = re.sub(french_pattern, english, content)
            changes += 1

    # Apply word/phrase translations
    for french, english in DOCSTRING_TRANSLATIONS.items():
        if french in content:
            count = content.count(french)
            content = content.replace(french, english)
            changes += count

    return content, changes


def process_file(file_path: Path) -> Tuple[bool, int]:
    """
    Process a single Python file.

    Args:
        file_path: Path to file to process

    Returns:
        Tuple of (was_modified, num_changes)
    """
    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Translate
        new_content, changes = translate_file_content(content)

        # Write if changed
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True, changes

        return False, 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0


def main():
    """Main function."""
    print("VideoFlow - Docstring Translation")
    print("=" * 50)

    src_dir = Path("src")
    if not src_dir.exists():
        print(f"Error: {src_dir} not found")
        return

    # Find all Python files
    python_files = list(src_dir.rglob("*.py"))
    print(f"Found {len(python_files)} Python files\n")

    total_modified = 0
    total_changes = 0

    # Process each file
    for file_path in sorted(python_files):
        modified, changes = process_file(file_path)

        if modified:
            total_modified += 1
            total_changes += changes
            relative_path = file_path.relative_to(src_dir)
            print(f"✓ {relative_path}: {changes} translations")

    print()
    print("=" * 50)
    print(f"Files modified: {total_modified}")
    print(f"Total translations: {total_changes}")
    print("=" * 50)
    print("\nDocstring translation complete!")


if __name__ == "__main__":
    main()
