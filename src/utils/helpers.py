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
    
    # Handle None or empty input
    if not product_name:
        return ""
    
    product_name_lower = product_name.lower()
    
    # Handle Kubaneh with type options
    if "kubaneh" in product_name_lower:
        if options and "type" in options:
            kubaneh_type = options["type"]
            type_key = f"KUBANEH_{kubaneh_type.upper()}"
            try:
                type_display = i18n.get_text(type_key, user_id=user_id)
                return i18n.get_text("KUBANEH_DISPLAY_NAME", user_id=user_id).format(type=type_display)
            except:
                # Fallback if translation key doesn't exist
                return f"Kubaneh ({kubaneh_type.title()})"
        try:
            return i18n.get_text("PRODUCT_KUBANEH_CLASSIC", user_id=user_id)
        except:
            # Fallback to original name if translation fails
            return product_name
    
    # Handle Samneh with type options
    elif "samneh" in product_name_lower:
        if options and "type" in options:
            samneh_type = options["type"]
            type_key = f"SAMNEH_{samneh_type.upper()}"
            try:
                type_display = i18n.get_text(type_key, user_id=user_id)
                return i18n.get_text("SAMNEH_DISPLAY_NAME", user_id=user_id).format(type=type_display)
            except:
                # Fallback if translation key doesn't exist
                return f"Samneh ({samneh_type.title()})"
        try:
            return i18n.get_text("PRODUCT_SAMNEH_SMOKED", user_id=user_id)
        except:
            # Fallback to original name if translation fails
            return product_name
    
    # Handle Red Bisbas with size options
    elif "red bisbas" in product_name_lower or "bisbas" in product_name_lower:
        if options and "size" in options:
            size = options["size"]
            size_key = f"SIZE_{size.upper()}"
            try:
                size_display = i18n.get_text(size_key, user_id=user_id)
                return i18n.get_text("RED_BISBAS_DISPLAY_NAME", user_id=user_id).format(size=size_display)
            except:
                # Fallback if translation key doesn't exist
                return f"Red Bisbas ({size.title()})"
        try:
            return i18n.get_text("PRODUCT_RED_BISBAS", user_id=user_id)
        except:
            # Fallback to original name if translation fails
            return product_name
    
    # Handle Hilbeh with type options
    elif "hilbeh" in product_name_lower:
        if options and "type" in options:
            hilbeh_type = options["type"]
            type_key = f"HILBEH_{hilbeh_type.upper()}"
            try:
                type_display = i18n.get_text(type_key, user_id=user_id)
                return i18n.get_text("HILBEH_DISPLAY_NAME", user_id=user_id).format(type=type_display)
            except:
                # Fallback if translation key doesn't exist
                return f"Hilbeh ({hilbeh_type.title()})"
        try:
            return i18n.get_text("PRODUCT_HILBEH", user_id=user_id)
        except:
            # Fallback to original name if translation fails
            return product_name
    
    # Handle Hawaij products specifically
    elif "hawaij soup spice" in product_name_lower:
        try:
            return i18n.get_text("PRODUCT_HAWAIJ_SOUP", user_id=user_id)
        except:
            return product_name
    
    elif "hawaij coffee spice" in product_name_lower:
        try:
            return i18n.get_text("PRODUCT_HAWAIJ_COFFEE", user_id=user_id)
        except:
            return product_name
    
    # Handle White Coffee
    elif "white coffee" in product_name_lower:
        try:
            return i18n.get_text("PRODUCT_WHITE_COFFEE", user_id=user_id)
        except:
            return product_name
    
    # Handle other products
    else:
        # Try to find a direct product translation
        product_key = f"PRODUCT_{product_name.upper().replace(' ', '_')}"
        try:
            return i18n.get_text(product_key, user_id=user_id)
        except:
            # Try to find a generic unknown product translation
            try:
                return i18n.get_text("PRODUCT_UNKNOWN", user_id=user_id)
            except:
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
