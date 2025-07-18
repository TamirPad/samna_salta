"""
Utility functions for the Samna Salta bot
"""

import logging
import threading
import time
from datetime import datetime, time as dt_time
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

# Original helper functions

def format_price(price: float, currency: str = "ILS") -> str:
    """Format price with currency"""
    return f"{price:.2f} {currency}"

@cached(ttl=300)  # Cache for 5 minutes
def is_hilbeh_available() -> bool:
    """Check if Hilbeh is available today"""
    config = get_config()
    today = datetime.now().strftime("%A").lower()
    return today in config.hilbeh_available_days

def parse_time_range(time_range: str) -> tuple[dt_time, dt_time]:
    """Parse time range string (e.g., '09:00-18:00')"""
    start_str, end_str = time_range.split("-")
    start_time = datetime.strptime(start_str, "%H:%M").time()
    end_time = datetime.strptime(end_str, "%H:%M").time()
    return start_time, end_time

@cached(ttl=60)  # Cache for 1 minute
def is_within_business_hours() -> bool:
    """Check if current time is within business hours"""
    config = get_config()
    start_time, end_time = parse_time_range(config.hilbeh_available_hours)
    current_time = datetime.now().time()
    return start_time <= current_time <= end_time

def sanitize_phone_number(phone: str) -> str:
    """Sanitize phone number to standard format"""
    # Remove all non-digit characters
    digits_only = "".join(filter(str.isdigit, phone))

    # Handle Israeli phone numbers
    if digits_only.startswith("972"):
        return f"+{digits_only}"
    if digits_only.startswith("0"):
        return f"+972{digits_only[1:]}"
    if len(digits_only) == 9:
        return f"+972{digits_only}"
    return f"+{digits_only}"

def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    sanitized = sanitize_phone_number(phone)

    # Check basic Israeli format
    if not sanitized.startswith("+972") or len(sanitized) != 13:
        return False

    # Check for valid Israeli mobile prefixes
    mobile_part = sanitized[4:6]
    israeli_mobile_prefixes = ["50", "52", "53", "54", "55", "57", "58"]
    return mobile_part in israeli_mobile_prefixes

@cached(ttl=3600)  # Cache for 1 hour
def translate_product_name(product_name: str, options: Optional[dict] = None, user_id: Optional[int] = None) -> str:
    """Translate a product name from database format to localized display name"""
    from src.utils.i18n import i18n
    
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
        return i18n.get_text("PRODUCT_KUBANEH_CLASSIC", user_id=user_id)
    
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
        return i18n.get_text("PRODUCT_SAMNEH_SMOKED", user_id=user_id)
    
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
        return i18n.get_text("PRODUCT_RED_BISBAS", user_id=user_id)
    
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
        return i18n.get_text("PRODUCT_HILBEH", user_id=user_id)
    
    # Handle other products
    else:
        # Try to find a direct product translation
        product_key = f"PRODUCT_{product_name.upper().replace(' ', '_')}"
        try:
            return i18n.get_text(product_key, user_id=user_id)
        except:
            # Fallback to original name
            return product_name

def format_order_number(order_id: int) -> str:
    """Format order number for display"""
    return f"ORD-{order_id:06d}"

def format_datetime(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def format_date(dt: datetime) -> str:
    """Format date for display"""
    return dt.strftime("%Y-%m-%d")

def format_time(dt: datetime) -> str:
    """Format time for display"""
    return dt.strftime("%H:%M")

def calculate_total(items: list[dict]) -> float:
    """Calculate total price from items list"""
    return sum(item.get("total_price", 0) for item in items)

def calculate_subtotal(items: list[dict]) -> float:
    """Calculate subtotal from items list"""
    return sum(item.get("unit_price", 0) * item.get("quantity", 1) for item in items)

def calculate_delivery_charge(subtotal: float, delivery_method: str) -> float:
    """Calculate delivery charge based on subtotal and method"""
    if delivery_method.lower() == "delivery":
        return 5.0  # Fixed delivery charge
    return 0.0

def calculate_final_total(subtotal: float, delivery_charge: float) -> float:
    """Calculate final total including delivery charge"""
    return subtotal + delivery_charge

def translate_category_name(category_name: str, user_id: Optional[int] = None) -> str:
    """Translate category name from database format to localized display name"""
    from src.utils.i18n import i18n
    
    # Map database category names to translation keys
    category_mapping = {
        "bread": "CATEGORY_BREAD",
        "spice": "CATEGORY_SPICE", 
        "spread": "CATEGORY_SPREAD",
        "beverage": "CATEGORY_BEVERAGE",
        "other": "CATEGORY_OTHER"
    }
    
    # Get translation key for category
    translation_key = category_mapping.get(category_name.lower(), "CATEGORY_OTHER")
    
    try:
        return i18n.get_text(translation_key, user_id=user_id)
    except:
        # Fallback to capitalized category name if translation not found
        return category_name.title()
