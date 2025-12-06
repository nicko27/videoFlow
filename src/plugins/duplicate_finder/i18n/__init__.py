"""
Internationalization (i18n) module for duplicate finder.

Provides translation support for multiple languages.
"""
from .translator import Translator, get_translator, set_language, get_available_languages

__all__ = ['Translator', 'get_translator', 'set_language', 'get_available_languages']
