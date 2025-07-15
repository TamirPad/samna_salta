"""
Security utilities for the Samna Salta bot
"""

import logging
import time
from abc import ABC, abstractmethod
from functools import wraps
from typing import Dict, Set

from telegram import Update
from telegram.ext import ContextTypes

from src.config import get_config
from .helpers import sanitize_phone_number, validate_phone_number
from .constants import SecurityPatterns, ErrorMessages

logger = logging.getLogger(__name__)


class RateLimitBackend(ABC):
    """Abstract base class for rate limiting backends"""
    
    @abstractmethod
    def is_rate_limited(self, user_id: int, max_requests: int, window_seconds: int) -> bool:
        """Check if user is rate limited"""
        pass
    
    @abstractmethod
    def record_request(self, user_id: int) -> None:
        """Record a request for the user"""
        pass
    
    @abstractmethod
    def is_blocked(self, user_id: int) -> bool:
        """Check if user is blocked"""
        pass
    
    @abstractmethod
    def block_user(self, user_id: int) -> None:
        """Block a user"""
        pass
    
    @abstractmethod
    def unblock_user(self, user_id: int) -> None:
        """Unblock a user"""
        pass


class InMemoryRateLimitBackend(RateLimitBackend):
    """In-memory rate limiting backend for development/testing"""
    
    def __init__(self):
        self._rate_limit_storage: Dict[int, Dict[str, float]] = {}
        self._blocked_users: Set[int] = set()
    
    def is_rate_limited(self, user_id: int, max_requests: int, window_seconds: int) -> bool:
        """Check if user is rate limited"""
        current_time = time.time()
        
        # Initialize user rate limit data
        if user_id not in self._rate_limit_storage:
            self._rate_limit_storage[user_id] = {}
        
        # Clean old requests
        user_requests = self._rate_limit_storage[user_id]
        user_requests = {
            timestamp: count
            for timestamp, count in user_requests.items()
            if current_time - timestamp < window_seconds
        }
        self._rate_limit_storage[user_id] = user_requests
        
        # Count current requests
        total_requests = sum(user_requests.values())
        return total_requests >= max_requests
    
    def record_request(self, user_id: int) -> None:
        """Record a request for the user"""
        current_time = time.time()
        if user_id not in self._rate_limit_storage:
            self._rate_limit_storage[user_id] = {}
        
        user_requests = self._rate_limit_storage[user_id]
        user_requests[current_time] = user_requests.get(current_time, 0) + 1
    
    def is_blocked(self, user_id: int) -> bool:
        """Check if user is blocked"""
        return user_id in self._blocked_users
    
    def block_user(self, user_id: int) -> None:
        """Block a user"""
        self._blocked_users.add(user_id)
    
    def unblock_user(self, user_id: int) -> None:
        """Unblock a user"""
        self._blocked_users.discard(user_id)


class RedisRateLimitBackend(RateLimitBackend):
    """Redis-based rate limiting backend for production"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        try:
            import redis
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()  # Test connection
            logger.info("Redis rate limiting backend initialized")
        except ImportError:
            logger.error("Redis not available. Install with: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def is_rate_limited(self, user_id: int, max_requests: int, window_seconds: int) -> bool:
        """Check if user is rate limited using Redis"""
        current_time = int(time.time())
        key = f"rate_limit:{user_id}"
        
        # Get current count
        count = self.redis_client.zcount(key, current_time - window_seconds, current_time)
        return count >= max_requests
    
    def record_request(self, user_id: int) -> None:
        """Record a request for the user using Redis"""
        current_time = int(time.time())
        key = f"rate_limit:{user_id}"
        
        # Add current timestamp to sorted set
        self.redis_client.zadd(key, {str(current_time): current_time})
        # Set expiry to clean up old data
        self.redis_client.expire(key, 3600)  # 1 hour
    
    def is_blocked(self, user_id: int) -> bool:
        """Check if user is blocked using Redis"""
        return self.redis_client.sismember("blocked_users", user_id)
    
    def block_user(self, user_id: int) -> None:
        """Block a user using Redis"""
        self.redis_client.sadd("blocked_users", user_id)
    
    def unblock_user(self, user_id: int) -> None:
        """Unblock a user using Redis"""
        self.redis_client.srem("blocked_users", user_id)


# Global rate limiting backend instance
_rate_limit_backend: RateLimitBackend | None = None


def get_rate_limit_backend() -> RateLimitBackend:
    """Get the rate limiting backend instance"""
    global _rate_limit_backend
    
    if _rate_limit_backend is None:
        config = get_config()
        
        # Use Redis in production, in-memory in development
        if config.environment == "production":
            try:
                redis_url = getattr(config, 'redis_url', 'redis://localhost:6379')
                _rate_limit_backend = RedisRateLimitBackend(redis_url)
            except Exception as e:
                logger.warning(f"Failed to initialize Redis backend: {e}. Falling back to in-memory.")
                _rate_limit_backend = InMemoryRateLimitBackend()
        else:
            _rate_limit_backend = InMemoryRateLimitBackend()
    
    return _rate_limit_backend


class SecurityError(Exception):
    """Custom security exception"""


def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """Rate limiting decorator for bot handlers"""

    def decorator(func):
        @wraps(func)
        async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            user_id = update.effective_user.id
            backend = get_rate_limit_backend()

            # Check if user is blocked
            if backend.is_blocked(user_id):
                logger.warning("Blocked user %s attempted access", user_id)
                await update.message.reply_text(
                    "Access temporarily restricted. Please contact support."
                )
                return

            # Check rate limit
            if backend.is_rate_limited(user_id, max_requests, window_seconds):
                logger.warning("Rate limit exceeded for user %s", user_id)
                await update.message.reply_text(
                    "Too many requests. Please wait a moment before trying again."
                )
                return

            # Record this request
            backend.record_request(user_id)

            return await func(update, context, *args, **kwargs)

        return wrapper

    return decorator


def admin_required(func):
    """Decorator to require admin privileges"""

    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        user_id = update.effective_user.id
        config = get_config()

        if user_id != config.admin_chat_id:
            logger.warning("Unauthorized admin access attempt by user %s", user_id)
            await update.message.reply_text(
                "❌ You don't have permission to access this feature."
            )
            return

        return await func(update, context, *args, **kwargs)

    return wrapper


def validate_input(input_text: str, max_length: int = 500) -> bool:
    """Validate user input for security"""
    if not input_text or len(input_text.strip()) == 0:
        return False

    if len(input_text) > max_length:
        return False

    # Check for suspicious patterns
    input_lower = input_text.lower()
    for pattern in SecurityPatterns.SUSPICIOUS_PATTERNS:
        if pattern in input_lower:
            logger.warning("Suspicious input detected: %s", pattern)
            return False

    return True


def sanitize_text(text: str) -> str:
    """Sanitize text input"""
    if not text:
        return ""

    # Remove control characters
    sanitized = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")

    # Limit length
    return sanitized[:500]


def log_security_event(event_type: str, user_id: int, details: str = ""):
    """Log security-related events"""
    logger.warning(
        "SECURITY EVENT: %s | User: %s | Details: %s",
        event_type,
        user_id,
        details,
        extra={
            "event_type": event_type,
            "user_id": user_id,
            "details": details,
            "timestamp": time.time(),
        },
    )


def block_user(user_id: int, reason: str = "Security violation"):
    """Block a user temporarily"""
    backend = get_rate_limit_backend()
    backend.block_user(user_id)
    log_security_event("USER_BLOCKED", user_id, reason)


def unblock_user(user_id: int):
    """Unblock a user"""
    backend = get_rate_limit_backend()
    backend.unblock_user(user_id)
    log_security_event("USER_UNBLOCKED", user_id)


class InputValidator:
    """Input validation class following Single Responsibility Principle"""

    @staticmethod
    def validate_name(name: str) -> tuple[bool, str]:
        """Validate customer name"""
        if not validate_input(name, max_length=100):
            return False, ErrorMessages.INVALID_NAME_FORMAT

        name = sanitize_text(name).strip()
        if len(name) < 2:
            return False, ErrorMessages.NAME_TOO_SHORT

        if len(name) > 100:
            return False, ErrorMessages.NAME_TOO_LONG

        # Check for reasonable name pattern
        if not any(c.isalpha() for c in name):
            return False, ErrorMessages.NAME_MUST_CONTAIN_LETTERS

        return True, name

    @staticmethod
    def validate_address(address: str) -> tuple[bool, str]:
        """Validate delivery address"""
        if not validate_input(address, max_length=500):
            return False, ErrorMessages.INVALID_ADDRESS_FORMAT

        address = sanitize_text(address).strip()
        if len(address) < 10:
            return False, ErrorMessages.ADDRESS_TOO_SHORT

        if len(address) > 500:
            return False, ErrorMessages.ADDRESS_TOO_LONG

        return True, address

    @staticmethod
    def validate_phone(phone: str) -> tuple[bool, str]:
        """Validate phone number"""
        if not validate_phone_number(phone):
            return False, ErrorMessages.INVALID_PHONE_FORMAT

        sanitized = sanitize_phone_number(phone)
        return True, sanitized
