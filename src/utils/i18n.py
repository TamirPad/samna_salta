"""
Internationalization and translation utilities.
"""

import json
import os
from typing import Dict, Optional

import logging

logger = logging.getLogger(__name__)

# Default translations
DEFAULT_LANGUAGE = "he"
FALLBACK_LANGUAGE = "he"

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
        """Load all translation files safely into a temp cache.
        Only swap into the live cache if at least one language loaded successfully.
        """
        # Point to root level locales directory
        locales_dir = os.path.join(os.path.dirname(__file__), "..", "..", "locales")
        
        if not os.path.exists(locales_dir):
            logger.warning("Locales directory not found at %s", locales_dir)
            return

        temp_cache: Dict[str, Dict] = {}
        for filename in os.listdir(locales_dir):
            if filename.endswith(".json"):
                language = filename[:-5]  # Remove .json extension
                file_path = os.path.join(locales_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        temp_cache[language] = json.load(f)
                    logger.info("Loaded translations for %s", language)
                except Exception as e:
                    logger.error("Failed to load translations for %s: %s", language, e)
        if temp_cache:
            # Merge languages that loaded successfully; keep any previously
            # loaded languages that failed to reload this time.
            self._translations.update(temp_cache)
            logger.info(
                "Translations cache updated. Languages now available: %s",
                ", ".join(sorted(self._translations.keys())),
            )
        else:
            logger.error("No translation files were loaded. Keeping previous cache with %d languages.", len(self._translations))

    def reload(self) -> None:
        """Public method to reload locale files at runtime."""
        try:
            self._load_translations()
            logger.info("Translations reloaded successfully")
        except Exception as e:
            logger.error("Failed to reload translations: %s", e)

    def get_text(self, key: str, language: Optional[str] = None, user_id: Optional[int] = None) -> str:
        """Get translated text for a key"""
        # If no language specified, try to get from user preferences
        if language is None and user_id is not None:
            language = language_manager.get_user_language(user_id)
        
        language = language or DEFAULT_LANGUAGE

        # Try requested language (first attempt)
        if language in self._translations and key in self._translations[language]:
            return self._translations[language][key]

        # If translations seem empty or language missing, try a one-time reload
        if not self._translations or language not in self._translations:
            self.reload()
            if language in self._translations and key in self._translations[language]:
                return self._translations[language][key]

        # Try fallback language (Hebrew)
        if FALLBACK_LANGUAGE in self._translations and key in self._translations[FALLBACK_LANGUAGE]:
            return self._translations[FALLBACK_LANGUAGE][key]

        # Secondary fallback to English if available
        if "en" in self._translations and key in self._translations["en"]:
            return self._translations["en"][key]

        # Last-resort: try any available language to avoid showing raw keys
        for lang, mapping in self._translations.items():
            if key in mapping:
                return mapping[key]

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

def translate_category_name(category_name: str, user_id: Optional[int] = None, language: Optional[str] = None) -> str:
    """Translate category name based on user's language preference"""
    # Map English category names to translation keys
    category_mapping = {
        "bread": "CATEGORY_BREAD",
        "spice": "CATEGORY_SPICE", 
        "beverage": "CATEGORY_BEVERAGE",
        "other": "CATEGORY_OTHER",
        "spread": "CATEGORY_SPREAD"
    }
    
    # Get the translation key for this category
    translation_key = category_mapping.get(category_name.lower())
    if translation_key:
        return i18n.get_text(translation_key, language=language, user_id=user_id)
    
    # If no mapping found, return the original name
    return category_name 