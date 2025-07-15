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
from src.utils.constants import CacheSettings, SecurityPatterns

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
    if not sanitized.startswith(SecurityPatterns.ISRAELI_PHONE_PREFIX) or len(sanitized) != SecurityPatterns.ISRAELI_PHONE_LENGTH:
        return False

    # Check for valid Israeli mobile prefixes
    mobile_part = sanitized[4:6]
    return mobile_part in SecurityPatterns.ISRAELI_MOBILE_PREFIXES

@cached(ttl=3600)  # Cache for 1 hour
def translate_product_name(product_name: str, options: dict = None) -> str:
    """Translate a product name from database format to localized display name"""
    from src.utils.i18n import tr
    
    product_name_lower = product_name.lower()
    
    if "kubaneh" in product_name_lower:
        if options and "type" in options:
            kubaneh_type = options["type"]
            type_key = f"KUBANEH_{kubaneh_type.upper()}"
            type_display = tr(type_key)
            return tr("KUBANEH_DISPLAY_NAME").format(type=type_display)
        return tr("PRODUCT_KUBANEH_CLASSIC")
    
    elif "samneh" in product_name_lower:
        if options and "smoking" in options:
            smoking_type = options["smoking"].replace(" ", "_")
            type_key = f"SAMNEH_{smoking_type.upper()}"
            type_display = tr(type_key)
            return tr("SAMNEH_DISPLAY_NAME").format(type=type_display)
        return tr("PRODUCT_SAMNEH_SMOKED")
    
    elif "red bisbas" in product_name_lower or "bisbas" in product_name_lower:
        if options and "size" in options:
            size = options["size"]
            size_key = f"SIZE_{size.upper()}"
            size_display = tr(size_key)
            return tr("RED_BISBAS_DISPLAY_NAME").format(size=size_display)
        return tr("PRODUCT_RED_BISBAS")
    
    elif "hilbeh" in product_name_lower:
        return tr("PRODUCT_HILBEH")
    
    elif "hawaij" in product_name_lower and "soup" in product_name_lower:
        return tr("PRODUCT_HAWAIJ_SOUP")
    
    elif "hawaij" in product_name_lower and "coffee" in product_name_lower:
        return tr("PRODUCT_HAWAIJ_COFFEE")
    
    elif "white coffee" in product_name_lower:
        return tr("PRODUCT_WHITE_COFFEE")
    
    return product_name
