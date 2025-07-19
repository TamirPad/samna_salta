"""
Language management utilities for user language preferences.
"""

import logging
from typing import Dict, Optional

from src.db.operations import get_customer_by_telegram_id, update_customer_language

logger = logging.getLogger(__name__)

class LanguageManager:
    """Manages user language preferences with database persistence"""
    
    _instance = None
    _user_languages: Dict[int, str] = {}  # Cache for performance
    
    def __new__(cls) -> "LanguageManager":
        if cls._instance is None:
            cls._instance = super(LanguageManager, cls).__new__(cls)
        return cls._instance
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's preferred language from database or cache"""
        # Check cache first
        if user_id in self._user_languages:
            return self._user_languages[user_id]
        
        # Get from database
        try:
            customer = get_customer_by_telegram_id(user_id)
            if customer and customer.language:
                # Cache the result
                self._user_languages[user_id] = customer.language
                return customer.language
        except Exception as e:
            logger.error("Error getting user language from database: %s", e)
        
        # Default to English
        return "en"
    
    def set_user_language(self, user_id: int, language: str) -> bool:
        """Set user's preferred language in database and cache"""
        if language in ["en", "he"]:
            try:
                # Update in database
                success = update_customer_language(user_id, language)
                if success:
                    # Update cache
                    self._user_languages[user_id] = language
                    logger.info("User %s language set to %s", user_id, language)
                    return True
                else:
                    logger.error("Failed to update language in database for user %s", user_id)
                    return False
            except Exception as e:
                logger.error("Error setting user language in database: %s", e)
                return False
        else:
            logger.warning("Invalid language %s for user %s", language, user_id)
            return False
    
    def clear_user_language(self, user_id: int) -> None:
        """Clear user's language preference from cache"""
        if user_id in self._user_languages:
            del self._user_languages[user_id]
            logger.info("Cleared language preference from cache for user %s", user_id)
    
    def clear_cache(self) -> None:
        """Clear all cached language preferences"""
        self._user_languages.clear()
        logger.info("Cleared all language preferences from cache")

# Global instance
language_manager = LanguageManager() 