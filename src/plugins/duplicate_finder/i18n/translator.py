"""
Translation manager for duplicate finder.

Provides i18n support with automatic language detection and fallback.
"""
import json
import os
from typing import Dict, Optional
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.i18n')

# Global translator instance
_translator_instance: Optional['Translator'] = None


class Translator:
    """
    Translation manager with language support.

    Supports multiple languages with automatic fallback to English.
    Translations are loaded from JSON files in the translations/ directory.

    Example:
        ```python
        t = Translator()
        t.set_language('fr')
        print(t.tr('ui.presets.speed'))  # "Vitesse maximale"
        ```
    """

    def __init__(self, default_language: str = 'en'):
        """
        Initialize translator.

        Args:
            default_language: Default language code (default: 'en')
        """
        self.translations: Dict[str, Dict] = {}
        self.current_language = default_language
        self.fallback_language = 'en'

        # Load all available translations
        self._load_translations()

        logger.info(f"Translator initialized with language: {default_language}")

    def _load_translations(self):
        """Load all translation files from the translations directory."""
        translations_dir = os.path.join(os.path.dirname(__file__), 'translations')

        if not os.path.exists(translations_dir):
            logger.warning(f"Translations directory not found: {translations_dir}")
            return

        # Load all .json files
        for filename in os.listdir(translations_dir):
            if filename.endswith('.json'):
                lang_code = filename[:-5]  # Remove .json extension
                filepath = os.path.join(translations_dir, filename)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                    logger.info(f"Loaded translations for language: {lang_code}")
                except Exception as e:
                    logger.error(f"Failed to load translations for {lang_code}: {e}")

    def set_language(self, language: str) -> bool:
        """
        Set the current language.

        Args:
            language: Language code (e.g., 'en', 'fr')

        Returns:
            True if language was set successfully, False otherwise
        """
        if language in self.translations:
            self.current_language = language
            logger.info(f"Language changed to: {language}")
            return True
        else:
            logger.warning(f"Language not available: {language}")
            return False

    def get_language(self) -> str:
        """Get the current language code."""
        return self.current_language

    def get_available_languages(self) -> Dict[str, str]:
        """
        Get available languages with their display names.

        Returns:
            Dictionary mapping language codes to display names
        """
        languages = {}
        for lang_code in self.translations:
            try:
                display_name = self.translations[lang_code].get('language_name', lang_code)
                languages[lang_code] = display_name
            except Exception as e:
                logger.debug(f"Cannot get language name for {lang_code}: {e}")
                languages[lang_code] = lang_code

        return languages

    def tr(self, key: str, **kwargs) -> str:
        """
        Translate a key to the current language.

        Supports nested keys using dot notation (e.g., 'ui.presets.speed').
        Supports string formatting with kwargs.
        Falls back to English if translation not found.

        Args:
            key: Translation key (dot-separated path)
            **kwargs: Optional formatting arguments

        Returns:
            Translated string, or the key itself if not found

        Example:
            ```python
            t.tr('ui.audio.threshold')
            t.tr('ui.info.videos_processed', count=100)
            ```
        """
        # Try current language
        translation = self._get_translation(key, self.current_language)

        # Fallback to English
        if translation is None and self.current_language != self.fallback_language:
            translation = self._get_translation(key, self.fallback_language)

        # If still not found, return the key
        if translation is None:
            logger.debug(f"Translation not found: {key}")
            return key

        # Format with kwargs if provided
        if kwargs:
            try:
                return translation.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing format argument for key {key}: {e}")
                return translation

        return translation

    def _get_translation(self, key: str, language: str) -> Optional[str]:
        """
        Get translation for a specific language.

        Args:
            key: Translation key (dot-separated)
            language: Language code

        Returns:
            Translation string or None if not found
        """
        if language not in self.translations:
            return None

        # Navigate through nested dictionary using dot notation
        parts = key.split('.')
        current = self.translations[language]

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current if isinstance(current, str) else None


def get_translator() -> Translator:
    """
    Get the global translator instance.

    Creates a new instance if it doesn't exist.

    Returns:
        Global Translator instance
    """
    global _translator_instance

    if _translator_instance is None:
        _translator_instance = Translator()

    return _translator_instance


def set_language(language: str) -> bool:
    """
    Set the language for the global translator.

    Args:
        language: Language code

    Returns:
        True if successful
    """
    return get_translator().set_language(language)


def get_available_languages() -> Dict[str, str]:
    """
    Get available languages.

    Returns:
        Dictionary of language codes to display names
    """
    return get_translator().get_available_languages()
