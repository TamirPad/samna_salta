"""
Utility functions for the Samna Salta bot
"""

import logging
import structlog
from datetime import datetime, time
from typing import Optional


def setup_logging():
    """Setup structured logging"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def format_price(price: float, currency: str = "ILS") -> str:
    """Format price with currency"""
    return f"{price:.2f} {currency}"


def is_hilbeh_available() -> bool:
    """Check if Hilbeh is available today"""
    from src.utils.config import get_config
    
    config = get_config()
    today = datetime.now().strftime("%A").lower()
    
    return today in config.hilbeh_available_days


def parse_time_range(time_range: str) -> tuple[time, time]:
    """Parse time range string (e.g., '09:00-18:00')"""
    start_str, end_str = time_range.split("-")
    start_time = datetime.strptime(start_str, "%H:%M").time()
    end_time = datetime.strptime(end_str, "%H:%M").time()
    return start_time, end_time


def is_within_business_hours() -> bool:
    """Check if current time is within business hours"""
    from src.utils.config import get_config
    
    config = get_config()
    start_time, end_time = parse_time_range(config.hilbeh_available_hours)
    current_time = datetime.now().time()
    
    return start_time <= current_time <= end_time


def sanitize_phone_number(phone: str) -> str:
    """Sanitize phone number to standard format"""
    # Remove all non-digit characters
    digits_only = ''.join(filter(str.isdigit, phone))
    
    # Handle Israeli phone numbers
    if digits_only.startswith('972'):
        return f"+{digits_only}"
    elif digits_only.startswith('0'):
        return f"+972{digits_only[1:]}"
    elif len(digits_only) == 9:
        return f"+972{digits_only}"
    else:
        return f"+{digits_only}"


def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    sanitized = sanitize_phone_number(phone)
    # Basic validation for Israeli numbers
    return sanitized.startswith('+972') and len(sanitized) == 13 