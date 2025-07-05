"""
Simple i18n helper for translating UI strings.

Usage
-----
from src.infrastructure.utilities.i18n import tr
text = tr("WELCOME", lang)  # returns Hebrew / English string

Strings are stored in JSON files under src/infrastructure/locales/<lang>.json
Missing keys gracefully fall back to English, then to the key name.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from functools import lru_cache
from typing import Dict

_LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
_DEFAULT_LANG = os.getenv("BOT_DEFAULT_LANG", "he")


@lru_cache(maxsize=None)
def _load_locale(lang: str) -> Dict[str, str]:
    """Load language JSON and cache the result."""
    file_path = _LOCALES_DIR / f"{lang}.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Unknown language – return empty dict so we fall back to English
        return {}


def tr(key: str, lang: str | None = None) -> str:
    """Translate *key* for *lang* (default = env/BOT_DEFAULT_LANG).

    Falls back to English, then to the key itself if not found.
    """
    lang = lang or _DEFAULT_LANG

    # Primary language lookup
    primary = _load_locale(lang)
    if key in primary:
        return primary[key]

    # English fallback
    if lang != "en":
        en_data = _load_locale("en")
        if key in en_data:
            return en_data[key]

    # Last resort: return the key name
    return key 