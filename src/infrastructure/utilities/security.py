"""
Security utilities for the Samna Salta bot
"""

import time
import hashlib
import logging
from typing import Dict, Optional, Set
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from ..configuration.config import get_config

logger = logging.getLogger(__name__)

# Rate limiting storage (in production, use Redis)
_rate_limit_storage: Dict[int, Dict[str, float]] = {}
_blocked_users: Set[int] = set()

class SecurityError(Exception):
    """Custom security exception"""
    pass


def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """Rate limiting decorator for bot handlers"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            current_time = time.time()
            
            # Check if user is blocked
            if user_id in _blocked_users:
                logger.warning(f"Blocked user {user_id} attempted access")
                await update.message.reply_text(
                    "Access temporarily restricted. Please contact support."
                )
                return
            
            # Initialize user rate limit data
            if user_id not in _rate_limit_storage:
                _rate_limit_storage[user_id] = {}
            
            # Clean old requests
            user_requests = _rate_limit_storage[user_id]
            user_requests = {
                timestamp: count for timestamp, count in user_requests.items()
                if current_time - timestamp < window_seconds
            }
            _rate_limit_storage[user_id] = user_requests
            
            # Count current requests
            total_requests = sum(user_requests.values())
            
            if total_requests >= max_requests:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                await update.message.reply_text(
                    "Too many requests. Please wait a moment before trying again."
                )
                return
            
            # Record this request
            user_requests[current_time] = user_requests.get(current_time, 0) + 1
            
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(func):
    """Decorator to require admin privileges"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        config = get_config()
        
        if user_id != config.admin_chat_id:
            logger.warning(f"Unauthorized admin access attempt by user {user_id}")
            await update.message.reply_text(
                "❌ You don't have permission to access this feature."
            )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper


def validate_input(input_text: str, max_length: int = 500, allow_special_chars: bool = True) -> bool:
    """Validate user input for security"""
    if not input_text or len(input_text.strip()) == 0:
        return False
    
    if len(input_text) > max_length:
        return False
    
    # Check for suspicious patterns
    suspicious_patterns = [
        'javascript:', 'data:', 'vbscript:', '<script', '</script>',
        'onload=', 'onerror=', 'onclick=', 'drop table', 'delete from',
        'update set', 'insert into', 'union select'
    ]
    
    input_lower = input_text.lower()
    for pattern in suspicious_patterns:
        if pattern in input_lower:
            logger.warning(f"Suspicious input detected: {pattern}")
            return False
    
    return True





def sanitize_text(text: str) -> str:
    """Sanitize text input"""
    if not text:
        return ""
    
    # Remove control characters
    sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    
    # Limit length
    return sanitized[:500]


def log_security_event(event_type: str, user_id: int, details: str = ""):
    """Log security-related events"""
    logger.warning(
        f"SECURITY EVENT: {event_type} | User: {user_id} | Details: {details}",
        extra={
            'event_type': event_type,
            'user_id': user_id,
            'details': details,
            'timestamp': time.time()
        }
    )


def block_user(user_id: int, reason: str = "Security violation"):
    """Block a user temporarily"""
    _blocked_users.add(user_id)
    log_security_event("USER_BLOCKED", user_id, reason)


def unblock_user(user_id: int):
    """Unblock a user"""
    _blocked_users.discard(user_id)
    log_security_event("USER_UNBLOCKED", user_id)


class InputValidator:
    """Input validation class following Single Responsibility Principle"""
    
    @staticmethod
    def validate_name(name: str) -> tuple[bool, str]:
        """Validate customer name"""
        if not validate_input(name, max_length=100):
            return False, "Invalid name format"
        
        name = sanitize_text(name).strip()
        if len(name) < 2:
            return False, "Name must be at least 2 characters"
        
        if len(name) > 100:
            return False, "Name is too long"
        
        # Check for reasonable name pattern
        if not any(c.isalpha() for c in name):
            return False, "Name must contain letters"
        
        return True, name
    
    @staticmethod
    def validate_address(address: str) -> tuple[bool, str]:
        """Validate delivery address"""
        if not validate_input(address, max_length=500):
            return False, "Invalid address format"
        
        address = sanitize_text(address).strip()
        if len(address) < 10:
            return False, "Please provide a complete address"
        
        if len(address) > 500:
            return False, "Address is too long"
        
        return True, address
    
    @staticmethod
    def validate_phone(phone: str) -> tuple[bool, str]:
        """Validate phone number"""
        from .helpers import validate_phone_number, sanitize_phone_number
        
        if not validate_phone_number(phone):
            return False, "Please enter a valid Israeli phone number"
        
        sanitized = sanitize_phone_number(phone)
        return True, sanitized 