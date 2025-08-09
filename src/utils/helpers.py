"""
Utility functions for the Samna Salta bot
"""

import logging
import threading
import time
from datetime import datetime
from functools import wraps
from threading import Lock
from typing import Any, Dict, Generic, Optional, TypeVar, Union

from src.config import get_config
from src.utils.constants import CacheSettings
from src.utils.constants_manager import get_product_option_name, get_product_size_name
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

T = TypeVar("T")

class CacheEntry(Generic[T]):
    """Cache entry with timestamp and value"""

    def __init__(self, value: T, ttl: int):
        self.value = value
        self.expires_at = time.time() + ttl
        self.created_at = time.time()

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() > self.expires_at

class SimpleCache:
    """Simple in-memory cache with TTL support"""

    _instance = None
    _lock = Lock()

    def __new__(cls) -> "SimpleCache":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SimpleCache, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        self.cache: Dict[str, CacheEntry[Any]] = {}
        self.lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if entry.is_expired():
                    del self.cache[key]
                    return None
                return entry.value
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        if ttl is None:
            ttl = CacheSettings.GENERAL_CACHE_TTL_SECONDS

        with self.lock:
            self.cache[key] = CacheEntry(value, ttl)

    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()

def cached(ttl: Optional[int] = None):
    """Cache decorator with optional TTL"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = SimpleCache()
            
            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # If not in cache, call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator

# Helper functions

@cached(ttl=300)  # Cache for 5 minutes
def is_hilbeh_available() -> bool:
    """Check if Hilbeh is available today"""
    try:
        config = get_config()
        today = datetime.now().strftime("%A").lower()
        return today in config.hilbeh_available_days
    except Exception:
        # Return False on any error
        return False

@cached(ttl=3600)  # Cache for 1 hour
def translate_product_name(product_name: str, options: Optional[dict] = None, user_id: Optional[int] = None) -> str:
    """Translate a product name from database format to localized display name"""
    from src.utils.i18n import i18n
    from src.utils.language_manager import language_manager
    
    # Handle None or empty input
    if not product_name:
        return ""
    
    # Get user language
    user_language = language_manager.get_user_language(user_id) if user_id else "en"
    
    product_name_lower = product_name.lower()
    
    # Handle Kubaneh with type options
    if "kubaneh" in product_name_lower:
        if options and "type" in options:
            kubaneh_type = options["type"]
            try:
                type_display = get_product_option_name("kubaneh", kubaneh_type, user_id)
                base_name = i18n.get_text("PRODUCT_KUBANEH", user_id=user_id) if user_language == "he" else "Kubaneh"
                return f"{base_name} ({type_display})"
            except:
                # Fallback if translation key doesn't exist
                base_name = i18n.get_text("PRODUCT_KUBANEH", user_id=user_id) if user_language == "he" else "Kubaneh"
                return f"{base_name} ({kubaneh_type.title()})"
        return i18n.get_text("PRODUCT_KUBANEH", user_id=user_id) if user_language == "he" else "Kubaneh"
    
    # Handle Samneh with type options
    elif "samneh" in product_name_lower:
        if options and "type" in options:
            samneh_type = options["type"]
            try:
                type_display = get_product_option_name("samneh", samneh_type, user_id)
                base_name = i18n.get_text("PRODUCT_SAMNEH", user_id=user_id) if user_language == "he" else "Samneh"
                return f"{base_name} ({type_display})"
            except:
                # Fallback if translation key doesn't exist
                base_name = i18n.get_text("PRODUCT_SAMNEH", user_id=user_id) if user_language == "he" else "Samneh"
                return f"{base_name} ({samneh_type.title()})"
        return i18n.get_text("PRODUCT_SAMNEH", user_id=user_id) if user_language == "he" else "Samneh"
    
    # Handle Red Bisbas with size options
    elif "red bisbas" in product_name_lower or "bisbas" in product_name_lower:
        if options and "size" in options:
            size = options["size"]
            try:
                size_display = get_product_size_name(size, user_id)
                base_name = i18n.get_text("PRODUCT_RED_BISBAS", user_id=user_id) if user_language == "he" else "Red Bisbas"
                return f"{base_name} ({size_display})"
            except:
                # Fallback if translation key doesn't exist
                base_name = i18n.get_text("PRODUCT_RED_BISBAS", user_id=user_id) if user_language == "he" else "Red Bisbas"
                return f"{base_name} ({size.title()})"
        return i18n.get_text("PRODUCT_RED_BISBAS", user_id=user_id) if user_language == "he" else "Red Bisbas"
    
    # Handle Hilbeh with type options
    elif "hilbeh" in product_name_lower:
        if options and "type" in options:
            hilbeh_type = options["type"]
            try:
                type_display = get_product_option_name("hilbeh", hilbeh_type, user_id)
                base_name = i18n.get_text("PRODUCT_HILBEH", user_id=user_id) if user_language == "he" else "Hilbeh"
                return f"{base_name} ({type_display})"
            except:
                # Fallback if translation key doesn't exist
                base_name = i18n.get_text("PRODUCT_HILBEH", user_id=user_id) if user_language == "he" else "Hilbeh"
                return f"{base_name} ({hilbeh_type.title()})"
        return i18n.get_text("PRODUCT_HILBEH", user_id=user_id) if user_language == "he" else "Hilbeh"
    
    # Handle Hawaij products specifically
    elif "hawaij soup spice" in product_name_lower:
        return i18n.get_text("PRODUCT_HAWAIIJ_SOUP", user_id=user_id) if user_language == "he" else "Hawaij for Soup"
    
    elif "hawaij coffee spice" in product_name_lower:
        return i18n.get_text("PRODUCT_HAWAIIJ_COFFEE", user_id=user_id) if user_language == "he" else "Hawaij for Coffee"
    
    # Handle White Coffee
    elif "white coffee" in product_name_lower:
        return i18n.get_text("PRODUCT_WHITE_COFFEE", user_id=user_id) if user_language == "he" else "White Coffee"
    
    # Handle Burekas
    elif "burekas" in product_name_lower or "בורקס" in product_name:
        return i18n.get_text("PRODUCT_BUREKAS_CHEESE", user_id=user_id) if user_language == "he" else "Cheese Burekas"
    
    # Handle Jachnun
    elif "jachnun" in product_name_lower:
        return i18n.get_text("PRODUCT_JACHNUN", user_id=user_id) if user_language == "he" else "Jachnun"
    
    # Handle other products
    else:
        # Final fallback to original name
        return product_name


def translate_category_name(category_name: str, user_id: Optional[int] = None) -> str:
    """Translate category name from database format to localized display name using multilingual system"""
    from src.utils.i18n import i18n
    from src.db.operations import get_category_by_name, get_localized_category_name
    from src.utils.language_manager import language_manager
    
    # Handle None or empty input
    if not category_name:
        return ""
    
    # First, try to get the category from database with multilingual support
    try:
        category_obj = get_category_by_name(category_name)
        if category_obj:
            user_language = language_manager.get_user_language(user_id) if user_id else "en"
            localized_name = get_localized_category_name(category_obj, user_language)
            if localized_name:
                return localized_name
    except Exception as e:
        # Log error but continue with fallback
        logger.debug(f"Error getting localized category name for '{category_name}': {e}")
    
    # Fallback to old mapping system for backward compatibility
    category_mapping = {
        "bread": "CATEGORY_BREAD",
        "spice": "CATEGORY_SPICE", 
        "spread": "CATEGORY_SPREAD",
        "beverage": "CATEGORY_BEVERAGE",
        "desserts": "CATEGORY_DESSERTS",
        "other": "CATEGORY_OTHER"
    }
    
    # Get translation key for category
    translation_key = category_mapping.get(category_name.lower(), "CATEGORY_OTHER")
    
    try:
        return i18n.get_text(translation_key, user_id=user_id)
    except:
        # Fallback to capitalized category name if translation not found
        return category_name.title()

@cached(ttl=300)  # Cache for 5 minutes
def get_dynamic_welcome_message(user_id: Optional[int] = None) -> str:
    """Get dynamic welcome message based on business settings"""
    from src.utils.i18n import i18n
    from src.db.operations import get_business_settings_dict
    
    try:
        # Get business settings
        settings = get_business_settings_dict()
        business_name = settings.get('business_name', 'Samna Salta')
        
        # Get the welcome message template from i18n
        welcome_template = i18n.get_text("WELCOME_NEW_USER", user_id=user_id)
        
        # Format the template with the business name
        welcome_message = welcome_template.format(business_name=business_name)
        
        # Note: Removed business_info addition to avoid showing email/phone in welcome message
        
        return welcome_message
        
    except Exception as e:
        # Fallback to default welcome message if there's an error
        logger.error(f"Error getting dynamic welcome message: {e}")
        try:
            return i18n.get_text("WELCOME_NEW_USER", user_id=user_id).format(business_name="Samna Salta")
        except:
            return "Welcome to Samna Salta!"

@cached(ttl=300)  # Cache for 5 minutes
def get_dynamic_welcome_for_returning_users(user_id: Optional[int] = None) -> str:
    """Get dynamic welcome message for returning users based on business settings"""
    from src.utils.i18n import i18n
    from src.db.operations import get_business_settings_dict
    
    try:
        # Get business settings
        settings = get_business_settings_dict()
        business_name = settings.get('business_name', 'Samna Salta')
        
        # Use the simple header-only template
        welcome_template = i18n.get_text("WELCOME_NEW_USER", user_id=user_id)
        
        # Format the template with the business name
        welcome_message = welcome_template.format(business_name=business_name)
        
        # Note: Removed business_info addition to avoid showing email/phone in welcome message
        
        return welcome_message
        
    except Exception as e:
        # Fallback to default welcome message if there's an error
        logger.error(f"Error getting dynamic welcome for returning users: {e}")
        try:
            return i18n.get_text("WELCOME", user_id=user_id).format(business_name="Samna Salta")
        except:
            return "Welcome to Samna Salta!"

@cached(ttl=300)  # Cache for 5 minutes
def get_business_info_for_customers(user_id: Optional[int] = None, compact: bool = False) -> str:
    """Get formatted business information for display to customers"""
    from src.utils.i18n import i18n
    from src.db.operations import get_business_settings_dict
    
    try:
        # Get business settings
        settings = get_business_settings_dict()
        
        if not settings:
            return ""
        
        # Build business info text
        info_parts = []
        
        # Business description
        if settings.get('business_description'):
            info_parts.append(f"📝 {settings['business_description']}")
        
        # Contact information
        contact_parts = []
        if settings.get('business_phone'):
            contact_parts.append(f"📞 {settings['business_phone']}")
        if settings.get('business_email'):
            contact_parts.append(f"📧 {settings['business_email']}")
        
        if contact_parts:
            if compact:
                info_parts.append(" • ".join(contact_parts))
            else:
                info_parts.extend(contact_parts)
        
        # Address (only in full version)
        if not compact and settings.get('business_address'):
            info_parts.append(f"📍 {settings['business_address']}")
        
        # Business hours (only in full version)
        if not compact and settings.get('business_hours'):
            info_parts.append(f"🕒 {settings['business_hours']}")
        
        # Website (only in full version)
        if not compact and settings.get('business_website'):
            info_parts.append(f"🌐 {settings['business_website']}")
        
        return "\n".join(info_parts) if info_parts else ""
        
    except Exception as e:
        logger.error(f"Error getting business info for customers: {e}")
        return ""

def format_price(price: float, user_id: Optional[int] = None) -> str:
    """Format price with proper RTL support for Hebrew users"""
    from src.utils.language_manager import language_manager
    
    # Get user language
    user_language = language_manager.get_user_language(user_id) if user_id else "en"
    
    # Format the price
    formatted_price = f"₪{price:.2f}"
    
    # For Hebrew users, add a left-to-right mark to ensure proper display
    if user_language == "he":
        return f"\u200E{formatted_price}"
    
    return formatted_price


def format_quantity(quantity: int, user_id: Optional[int] = None) -> str:
    """Format quantity with proper RTL support for Hebrew users"""
    from src.utils.language_manager import language_manager
    
    # Get user language
    user_language = language_manager.get_user_language(user_id) if user_id else "en"
    
    # Format the quantity
    formatted_quantity = str(quantity)
    
    # For Hebrew users, add a left-to-right mark to ensure proper display
    if user_language == "he":
        return f"\u200E{formatted_quantity}"
    
    return formatted_quantity


def to_single_column_markup(markup: Optional[InlineKeyboardMarkup]) -> Optional[InlineKeyboardMarkup]:
    """Ensure any inline keyboard renders one button per row.
    If markup is None, returns None.
    """
    if markup is None:
        return None
    try:
        rows = getattr(markup, "inline_keyboard", []) or []
        # Flatten to buttons
        buttons: list[InlineKeyboardButton] = []
        for row in rows:
            for btn in row:
                buttons.append(btn)
        # Rebuild as single-column
        single_rows = [[btn] for btn in buttons]
        return InlineKeyboardMarkup(single_rows)
    except Exception:
        return markup
