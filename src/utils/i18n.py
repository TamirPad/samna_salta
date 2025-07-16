"""
Internationalization and translation utilities.
"""

import json
import os
from typing import Dict, Optional

import logging

logger = logging.getLogger(__name__)

# Default translations
DEFAULT_LANGUAGE = "en"
FALLBACK_LANGUAGE = "en"

# Import language manager
from src.utils.language_manager import language_manager

class I18nManager:
    """Manages translations and internationalization"""

    _instance = None
    _translations: Dict[str, Dict] = {}

    def __new__(cls) -> "I18nManager":
        if cls._instance is None:
            cls._instance = super(I18nManager, cls).__new__(cls)
            cls._instance._load_translations()
        return cls._instance

    def _load_translations(self) -> None:
        """Load all translation files"""
        # Point to root level locales directory
        locales_dir = os.path.join(os.path.dirname(__file__), "..", "..", "locales")
        
        if not os.path.exists(locales_dir):
            logger.warning("Locales directory not found at %s", locales_dir)
            return

        for filename in os.listdir(locales_dir):
            if filename.endswith(".json"):
                language = filename[:-5]  # Remove .json extension
                file_path = os.path.join(locales_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self._translations[language] = json.load(f)
                    logger.info("Loaded translations for %s", language)
                except Exception as e:
                    logger.error("Failed to load translations for %s: %s", language, e)

    def get_text(self, key: str, language: Optional[str] = None, user_id: Optional[int] = None) -> str:
        """Get translated text for a key"""
        # If no language specified, try to get from user preferences
        if language is None and user_id is not None:
            language = language_manager.get_user_language(user_id)
        
        language = language or DEFAULT_LANGUAGE

        # Try requested language
        if language in self._translations and key in self._translations[language]:
            return self._translations[language][key]

        # Try fallback language
        if FALLBACK_LANGUAGE in self._translations and key in self._translations[FALLBACK_LANGUAGE]:
            return self._translations[FALLBACK_LANGUAGE][key]

        # Return key if no translation found
        logger.warning("No translation found for key: %s", key)
        return key

    def get_available_languages(self) -> list[str]:
        """Get list of available languages"""
        return list(self._translations.keys())

# Global instance
i18n = I18nManager()

def _(key: str, language: Optional[str] = None, user_id: Optional[int] = None) -> str:
    """Shorthand function to get translated text"""
    return i18n.get_text(key, language, user_id)

def tr(key: str, language: Optional[str] = None, user_id: Optional[int] = None) -> str:
    """Translation function alias for backward compatibility"""
    return i18n.get_text(key, language, user_id) 