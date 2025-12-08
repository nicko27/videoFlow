"""Lightweight i18n helper for VideoFlow.

Provides a minimal translation layer backed by JSON catalogs located in
``resources/i18n/<lang>.json``. Usage:

    from src.core.i18n import t
    label.setText(t("ui.window.title", "Video Converter"))

Translations fall back to the provided default string, then to the key itself.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

_DEFAULT_LANG = "en"
_ENV_VARS = ("VIDEOFLOW_LANG", "LANG", "LC_ALL", "LC_MESSAGES")


def _detect_language() -> str:
    """Detect language from environment, fallback to default."""
    for var in _ENV_VARS:
        value = os.getenv(var, "")
        if value:
            # Normalize values like "fr_FR.UTF-8" → "fr"
            normalized = value.split(".")[0].split("_")[0].strip().lower()
            if normalized:
                return normalized
    return _DEFAULT_LANG


class _I18n:
    """Simple translation store."""

    def __init__(self):
        self._lang = _detect_language()

    @property
    def lang(self) -> str:
        return self._lang

    def set_language(self, lang: str):
        """Override current language."""
        self._lang = (lang or _DEFAULT_LANG).lower()

    @lru_cache(maxsize=8)
    def _load_catalog(self, lang: str) -> Dict[str, str]:
        base_dir = Path(__file__).resolve().parent.parent.parent / "resources" / "i18n"
        catalog_path = base_dir / f"{lang}.json"
        if not catalog_path.exists():
            return {}
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def translate(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """Translate a key, interpolate optional kwargs."""
        catalog = self._load_catalog(self._lang)
        fallback = default if default is not None else key
        text = catalog.get(key, fallback)
        try:
            return text.format(**kwargs) if kwargs else text
        except Exception:
            return text


_instance = _I18n()


def set_language(lang: str):
    """Set current language code (e.g., 'fr', 'en')."""
    _instance.set_language(lang)


def get_language() -> str:
    """Return current language code."""
    return _instance.lang


def t(key: str, default: Optional[str] = None, **kwargs) -> str:
    """Translate helper."""
    return _instance.translate(key, default, **kwargs)
