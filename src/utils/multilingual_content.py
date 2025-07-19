"""
Multilingual content management utilities for user-generated content.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from src.utils.i18n import i18n
from src.utils.language_manager import language_manager


class MultilingualContentManager:
    """Manages multilingual content for user-generated items like menu products and categories"""
    
    def __init__(self):
        self.supported_languages = ["en", "he"]
        self.default_language = "en"
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of input text.
        Returns 'he' for Hebrew, 'en' for English, or 'unknown'.
        """
        if not text:
            return "unknown"
        
        # Hebrew detection - look for Hebrew characters
        hebrew_pattern = re.compile(r'[\u0590-\u05FF\uFB1D-\uFB4F]')
        if hebrew_pattern.search(text):
            return "he"
        
        # English detection - look for Latin characters
        english_pattern = re.compile(r'[a-zA-Z]')
        if english_pattern.search(text):
            return "en"
        
        # If no clear language indicators, assume English
        return "en"
    
    def validate_multilingual_input(self, content: Dict[str, str], user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Validate multilingual content input from admin.
        
        Args:
            content: Dict with keys like 'name_en', 'name_he', 'description_en', 'description_he'
            user_id: User ID for language preferences
            
        Returns:
            Dict with validation results and processed content
        """
        result = {
            "valid": True,
            "errors": [],
            "processed_content": {},
            "detected_language": None
        }
        
        # Get user's preferred language
        user_language = language_manager.get_user_language(user_id) if user_id else "en"
        
        # Check if we have at least one name
        names = {lang: content.get(f"name_{lang}", "").strip() for lang in self.supported_languages}
        descriptions = {lang: content.get(f"description_{lang}", "").strip() for lang in self.supported_languages}
        
        # Validate names
        valid_names = {lang: name for lang, name in names.items() if len(name) >= 2}
        if not valid_names:
            result["valid"] = False
            result["errors"].append("At least one name is required (minimum 2 characters)")
            return result
        
        # Detect primary language from the first valid name
        first_valid_name = next(iter(valid_names.values()))
        detected_language = self.detect_language(first_valid_name)
        result["detected_language"] = detected_language
        
        # Validate descriptions (optional but if provided, should be meaningful)
        for lang, desc in descriptions.items():
            if desc and len(desc) < 5:
                result["errors"].append(f"Description in {lang} is too short (minimum 5 characters)")
        
        # Process content
        result["processed_content"] = {
            "name": names.get(detected_language, first_valid_name),  # Primary name
            "name_en": names.get("en", ""),
            "name_he": names.get("he", ""),
            "description": descriptions.get(detected_language, ""),  # Primary description
            "description_en": descriptions.get("en", ""),
            "description_he": descriptions.get("he", ""),
        }
        
        # If user provided content in their preferred language, use it as primary
        if user_language in valid_names:
            result["processed_content"]["name"] = names[user_language]
            if descriptions[user_language]:
                result["processed_content"]["description"] = descriptions[user_language]
        
        return result
    
    def get_localized_display_name(self, item, user_id: Optional[int] = None, language: Optional[str] = None) -> str:
        """
        Get the best localized name for display.
        
        Args:
            item: Product or Category object with get_localized_name method
            user_id: User ID for language preference
            language: Override language
            
        Returns:
            Localized name string
        """
        if not item:
            return ""
        
        # Determine language
        if language:
            display_language = language
        elif user_id:
            display_language = language_manager.get_user_language(user_id)
        else:
            display_language = "en"
        
        # Try to get localized name
        if hasattr(item, 'get_localized_name'):
            localized_name = item.get_localized_name(display_language)
            if localized_name:
                return localized_name
        
        # Fallback to default name
        return getattr(item, 'name', str(item))
    
    def get_localized_display_description(self, item, user_id: Optional[int] = None, language: Optional[str] = None) -> str:
        """
        Get the best localized description for display.
        
        Args:
            item: Product or Category object with get_localized_description method
            user_id: User ID for language preference
            language: Override language
            
        Returns:
            Localized description string
        """
        if not item:
            return ""
        
        # Determine language
        if language:
            display_language = language
        elif user_id:
            display_language = language_manager.get_user_language(user_id)
        else:
            display_language = "en"
        
        # Try to get localized description
        if hasattr(item, 'get_localized_description'):
            localized_desc = item.get_localized_description(display_language)
            if localized_desc:
                return localized_desc
        
        # Fallback to default description
        return getattr(item, 'description', "")
    
    def create_multilingual_input_prompt(self, field_type: str, user_id: int) -> str:
        """
        Create a multilingual input prompt for admin users.
        
        Args:
            field_type: 'name' or 'description'
            user_id: Admin user ID
            
        Returns:
            Formatted prompt string
        """
        user_language = language_manager.get_user_language(user_id)
        
        if field_type == "name":
            prompt_key = "ADMIN_MULTILINGUAL_NAME_PROMPT"
        elif field_type == "description":
            prompt_key = "ADMIN_MULTILINGUAL_DESCRIPTION_PROMPT"
        else:
            prompt_key = "ADMIN_MULTILINGUAL_GENERIC_PROMPT"
        
        base_prompt = i18n.get_text(prompt_key, user_id=user_id)
        
        # Add language-specific instructions
        if user_language == "he":
            instructions = i18n.get_text("ADMIN_MULTILINGUAL_HEBREW_INSTRUCTIONS", user_id=user_id)
        else:
            instructions = i18n.get_text("ADMIN_MULTILINGUAL_ENGLISH_INSTRUCTIONS", user_id=user_id)
        
        return f"{base_prompt}\n\n{instructions}"
    
    def parse_multilingual_input(self, text: str, user_id: int) -> Dict[str, str]:
        """
        Parse multilingual input from admin user.
        
        Args:
            text: Raw input text from user
            user_id: Admin user ID
            
        Returns:
            Dict with parsed content for each language
        """
        user_language = language_manager.get_user_language(user_id)
        
        # Simple parsing - assume the input is in the user's preferred language
        # For more complex parsing, you could implement pattern matching
        detected_language = self.detect_language(text)
        
        result = {
            "name": text,
            "name_en": "",
            "name_he": "",
            "description": "",
            "description_en": "",
            "description_he": ""
        }
        
        # Set the content in the detected language
        if detected_language == "he":
            result["name_he"] = text
        else:
            result["name_en"] = text
        
        # Also set as primary name
        result["name"] = text
        
        return result


# Global instance
multilingual_manager = MultilingualContentManager() 