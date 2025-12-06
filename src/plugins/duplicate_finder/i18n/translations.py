"""
Internationalization (i18n) module for Duplicate Finder.

This module provides translation support for the application UI.
It uses a dictionary-based approach for simple and efficient translations.

Usage:
    from i18n.translations import tr, set_language

    # Set language (default is 'en')
    set_language('fr')

    # Translate strings
    text = tr('Select video files')
    # Returns: 'Sélectionner des fichiers vidéo' (if French)

Supported Languages:
    - English (en) - Default
    - French (fr) - Complete
    - More languages can be added easily

Adding New Translations:
    1. Add entry to TRANSLATIONS dict below
    2. Add translations for each supported language
    3. Use tr() function in code instead of hardcoded strings

Example:
    # Before (hardcoded):
    button.setText("Start Analysis")

    # After (i18n):
    button.setText(tr("Start Analysis"))
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger('DuplicateFinder.i18n')

# Current language (default: English)
_current_language = 'en'

# Translation dictionary
# Format: {english_key: {language_code: translated_string}}
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # File operations
    "Select video files": {
        "fr": "Sélectionner des fichiers vidéo",
        "en": "Select video files"
    },
    "Select folder": {
        "fr": "Sélectionner un dossier",
        "en": "Select folder"
    },
    "Add files": {
        "fr": "Ajouter des fichiers",
        "en": "Add files"
    },
    "Add folder": {
        "fr": "Ajouter un dossier",
        "en": "Add folder"
    },
    "Clear list": {
        "fr": "Effacer la liste",
        "en": "Clear list"
    },
    "Reload last folder": {
        "fr": "Recharger le dernier dossier",
        "en": "Reload last folder"
    },
    "Reset folder": {
        "fr": "Réinitialiser le dossier",
        "en": "Reset folder"
    },

    # Analysis operations
    "Start Analysis": {
        "fr": "Démarrer l'analyse",
        "en": "Start Analysis"
    },
    "Stop Analysis": {
        "fr": "Arrêter l'analyse",
        "en": "Stop Analysis"
    },
    "Analyzing...": {
        "fr": "Analyse en cours...",
        "en": "Analyzing..."
    },
    "Ready to analyze": {
        "fr": "Prêt à analyser",
        "en": "Ready to analyze"
    },
    "Analysis complete": {
        "fr": "Analyse terminée",
        "en": "Analysis complete"
    },
    "Analysis cancelled": {
        "fr": "Analyse annulée",
        "en": "Analysis cancelled"
    },

    # Status messages
    "Processing": {
        "fr": "Traitement",
        "en": "Processing"
    },
    "Complete": {
        "fr": "Terminé",
        "en": "Complete"
    },
    "Cached": {
        "fr": "En cache",
        "en": "Cached"
    },
    "Error": {
        "fr": "Erreur",
        "en": "Error"
    },
    "Warning": {
        "fr": "Avertissement",
        "en": "Warning"
    },

    # Progress indicators
    "Hashing videos": {
        "fr": "Calcul des hashes",
        "en": "Hashing videos"
    },
    "Comparing videos": {
        "fr": "Comparaison des vidéos",
        "en": "Comparing videos"
    },
    "Extracting audio": {
        "fr": "Extraction audio",
        "en": "Extracting audio"
    },
    "Detecting scenes": {
        "fr": "Détection de scènes",
        "en": "Detecting scenes"
    },

    # Comparison dialog
    "Video Comparison": {
        "fr": "Comparaison de Vidéos",
        "en": "Video Comparison"
    },
    "Similarity": {
        "fr": "Similarité",
        "en": "Similarity"
    },
    "Keep first": {
        "fr": "Conserver le premier",
        "en": "Keep first"
    },
    "Keep second": {
        "fr": "Conserver le second",
        "en": "Keep second"
    },
    "Keep both": {
        "fr": "Conserver les deux",
        "en": "Keep both"
    },
    "Close": {
        "fr": "Fermer",
        "en": "Close"
    },

    # Settings
    "Settings": {
        "fr": "Paramètres",
        "en": "Settings"
    },
    "Settings saved": {
        "fr": "Paramètres sauvegardés",
        "en": "Settings saved"
    },
    "Threshold": {
        "fr": "Seuil",
        "en": "Threshold"
    },
    "Workers": {
        "fr": "Threads",
        "en": "Workers"
    },
    "Cache": {
        "fr": "Cache",
        "en": "Cache"
    },

    # File filters
    "Videos": {
        "fr": "Vidéos",
        "en": "Videos"
    },
    "All files": {
        "fr": "Tous les fichiers",
        "en": "All files"
    },

    # Error messages
    "Folder not found": {
        "fr": "Dossier introuvable",
        "en": "Folder not found"
    },
    "File not found": {
        "fr": "Fichier introuvable",
        "en": "File not found"
    },
    "Invalid file": {
        "fr": "Fichier invalide",
        "en": "Invalid file"
    },
    "No files selected": {
        "fr": "Aucun fichier sélectionné",
        "en": "No files selected"
    },
    "No duplicates found": {
        "fr": "Aucun duplicata trouvé",
        "en": "No duplicates found"
    },

    # Tooltips and help
    "Select one or more video files to analyze": {
        "fr": "Sélectionner un ou plusieurs fichiers vidéo à analyser",
        "en": "Select one or more video files to analyze"
    },
    "Select a folder to scan for videos": {
        "fr": "Sélectionner un dossier à scanner pour les vidéos",
        "en": "Select a folder to scan for videos"
    },
    "Remove all files from the list": {
        "fr": "Retirer tous les fichiers de la liste",
        "en": "Remove all files from the list"
    },

    # Analysis modes
    "Simple Mode": {
        "fr": "Mode Simple",
        "en": "Simple Mode"
    },
    "Audio-First Mode": {
        "fr": "Mode Audio d'abord",
        "en": "Audio-First Mode"
    },
    "Advanced Mode": {
        "fr": "Mode Avancé",
        "en": "Advanced Mode"
    },
    "Scene Detection": {
        "fr": "Détection de Scènes",
        "en": "Scene Detection"
    },

    # Results
    "duplicates found": {
        "fr": "duplicatas trouvés",
        "en": "duplicates found"
    },
    "scenes found": {
        "fr": "scènes trouvées",
        "en": "scenes found"
    },
    "files processed": {
        "fr": "fichiers traités",
        "en": "files processed"
    },

    # Time indicators
    "Time elapsed": {
        "fr": "Temps écoulé",
        "en": "Time elapsed"
    },
    "Time remaining": {
        "fr": "Temps restant",
        "en": "Time remaining"
    },
    "Estimated": {
        "fr": "Estimé",
        "en": "Estimated"
    },

    # Units
    "second": {
        "fr": "seconde",
        "en": "second"
    },
    "seconds": {
        "fr": "secondes",
        "en": "seconds"
    },
    "minute": {
        "fr": "minute",
        "en": "minute"
    },
    "minutes": {
        "fr": "minutes",
        "en": "minutes"
    },
    "hour": {
        "fr": "heure",
        "en": "hour"
    },
    "hours": {
        "fr": "heures",
        "en": "hours"
    },

    # Common UI elements
    "OK": {
        "fr": "OK",
        "en": "OK"
    },
    "Cancel": {
        "fr": "Annuler",
        "en": "Cancel"
    },
    "Apply": {
        "fr": "Appliquer",
        "en": "Apply"
    },
    "Yes": {
        "fr": "Oui",
        "en": "Yes"
    },
    "No": {
        "fr": "Non",
        "en": "No"
    },
}


def set_language(language_code: str) -> bool:
    """
    Set the current language for translations.

    Args:
        language_code: Two-letter language code ('en', 'fr', etc.)

    Returns:
        True if language was set successfully, False if language not supported

    Example:
        >>> set_language('fr')
        True
        >>> set_language('de')  # Not supported yet
        False
    """
    global _current_language

    supported_languages = get_supported_languages()

    if language_code not in supported_languages:
        logger.warning(
            f"Language '{language_code}' not supported. "
            f"Available: {', '.join(supported_languages)}"
        )
        return False

    _current_language = language_code
    logger.info(f"Language set to: {language_code}")
    return True


def get_language() -> str:
    """
    Get the current language code.

    Returns:
        Two-letter language code ('en', 'fr', etc.)

    Example:
        >>> get_language()
        'en'
    """
    return _current_language


def get_supported_languages() -> list:
    """
    Get list of supported language codes.

    Returns:
        List of two-letter language codes

    Example:
        >>> get_supported_languages()
        ['en', 'fr']
    """
    # Extract all unique language codes from translations
    languages = {'en'}  # English is always supported (default)

    for translations in TRANSLATIONS.values():
        languages.update(translations.keys())

    return sorted(list(languages))


def tr(text: str, language: Optional[str] = None) -> str:
    """
    Translate text to the current or specified language.

    Args:
        text: English text to translate (dictionary key)
        language: Optional language code. If None, uses current language.

    Returns:
        Translated text, or original text if translation not found

    Example:
        >>> set_language('fr')
        >>> tr('Select video files')
        'Sélectionner des fichiers vidéo'

        >>> tr('Select video files', language='en')
        'Select video files'

        >>> tr('Untranslated text')
        'Untranslated text'  # Returns original if not found
    """
    lang = language or _current_language

    # If English requested, return original
    if lang == 'en':
        return text

    # Look up translation
    if text in TRANSLATIONS:
        translations = TRANSLATIONS[text]
        if lang in translations:
            return translations[lang]

    # Translation not found - return original and log warning
    # Only log once per missing translation to avoid spam
    if not hasattr(tr, '_warned'):
        tr._warned = set()

    warning_key = (text, lang)
    if warning_key not in tr._warned:
        logger.debug(f"Translation not found: '{text}' [{lang}]")
        tr._warned.add(warning_key)

    return text


def add_translation(english_text: str, translations_dict: Dict[str, str]) -> None:
    """
    Add a new translation entry dynamically.

    This allows plugins or extensions to add their own translations.

    Args:
        english_text: English text (dictionary key)
        translations_dict: Dictionary of {language_code: translated_text}

    Example:
        >>> add_translation('New Feature', {
        ...     'fr': 'Nouvelle Fonctionnalité',
        ...     'es': 'Nueva Característica'
        ... })
        >>> tr('New Feature')
        'Nouvelle Fonctionnalité'  # If language is 'fr'
    """
    if english_text not in TRANSLATIONS:
        TRANSLATIONS[english_text] = {}

    TRANSLATIONS[english_text].update(translations_dict)
    logger.debug(f"Translation added: '{english_text}'")


def get_translation_coverage() -> Dict[str, float]:
    """
    Get translation coverage statistics for each language.

    Returns:
        Dictionary of {language_code: coverage_percentage}

    Example:
        >>> get_translation_coverage()
        {'en': 100.0, 'fr': 85.5}
    """
    coverage = {}
    total_strings = len(TRANSLATIONS)

    if total_strings == 0:
        return coverage

    for lang in get_supported_languages():
        translated_count = sum(
            1 for trans in TRANSLATIONS.values()
            if lang in trans
        )
        coverage[lang] = (translated_count / total_strings) * 100

    return coverage


def get_missing_translations(language: str) -> list:
    """
    Get list of English strings that don't have translations for a language.

    Args:
        language: Two-letter language code

    Returns:
        List of English strings missing translations

    Example:
        >>> missing = get_missing_translations('fr')
        >>> print(missing)
        ['Some untranslated text', 'Another string']
    """
    missing = []

    for english_text, translations in TRANSLATIONS.items():
        if language not in translations:
            missing.append(english_text)

    return missing


# Convenience function for formatted strings
def tr_format(text: str, **kwargs) -> str:
    """
    Translate text and format with arguments.

    Args:
        text: English text to translate (should contain {placeholders})
        **kwargs: Values to substitute in placeholders

    Returns:
        Translated and formatted text

    Example:
        >>> TRANSLATIONS['Found {count} duplicates'] = {
        ...     'fr': 'Trouvé {count} duplicatas'
        ... }
        >>> set_language('fr')
        >>> tr_format('Found {count} duplicates', count=5)
        'Trouvé 5 duplicatas'
    """
    translated = tr(text)
    try:
        return translated.format(**kwargs)
    except KeyError as e:
        logger.error(f"Missing placeholder in translation: {e}")
        return translated
