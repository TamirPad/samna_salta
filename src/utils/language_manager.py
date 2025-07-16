"""
Language management utilities for user language preferences.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class LanguageManager:
    """Manages user language preferences in memory"""
    
    _instance = None
    _user_languages: Dict[int, str] = {}
    
    def __new__(cls) -> "LanguageManager":
        if cls._instance is None:
            cls._instance = super(LanguageManager, cls).__new__(cls)
        return cls._instance
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's preferred language"""
        return self._user_languages.get(user_id, "en")
    
    def set_user_language(self, user_id: int, language: str) -> None:
        """Set user's preferred language"""
        if language in ["en", "he"]:
            self._user_languages[user_id] = language
            logger.info("User %s language set to %s", user_id, language)
        else:
            logger.warning("Invalid language %s for user %s", language, user_id)
    
    def clear_user_language(self, user_id: int) -> None:
        """Clear user's language preference"""
        if user_id in self._user_languages:
            del self._user_languages[user_id]
            logger.info("Cleared language preference for user %s", user_id)

# Global instance
language_manager = LanguageManager() 