"""
Rate limiting and security enhancements
"""

import hashlib
import logging
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RateLimit:
    """Rate limit configuration"""

    max_requests: int
    time_window: int  # seconds
    description: str


class TokenBucket:
    """Token bucket algorithm for rate limiting"""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket"""
        now = time.time()

        # Refill tokens based on time elapsed
        time_passed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + time_passed * self.refill_rate)
        self.last_refill = now

        # Check if enough tokens available
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class SlidingWindowRateLimiter:
    """Sliding window rate limiter with per-user tracking"""

    def __init__(self, rate_limits: Dict[str, RateLimit]):
        self.rate_limits = rate_limits
        self.user_requests: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: defaultdict(deque)
        )
        self._logger = logging.getLogger(self.__class__.__name__)

    def is_allowed(self, user_id: str, endpoint: str) -> Tuple[bool, Optional[int]]:
        """
        Check if request is allowed

        Returns:
            (is_allowed, retry_after_seconds)
        """
        if endpoint not in self.rate_limits:
            return True, None

        rate_limit = self.rate_limits[endpoint]
        now = time.time()

        # Get user's request history for this endpoint
        user_requests = self.user_requests[user_id][endpoint]

        # Remove old requests outside the time window
        cutoff_time = now - rate_limit.time_window
        while user_requests and user_requests[0] < cutoff_time:
            user_requests.popleft()

        # Check if under limit
        if len(user_requests) < rate_limit.max_requests:
            user_requests.append(now)
            return True, None

        # Calculate retry after time
        oldest_request = user_requests[0]
        retry_after = int(oldest_request + rate_limit.time_window - now) + 1

        self._logger.warning(
            f"Rate limit exceeded for user {user_id} on endpoint {endpoint}. "
            f"Requests: {len(user_requests)}/{rate_limit.max_requests} "
            f"in {rate_limit.time_window}s window"
        )

        return False, retry_after

    def get_user_stats(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Get rate limiting stats for a user"""
        stats = {}
        for endpoint, requests in self.user_requests[user_id].items():
            if endpoint in self.rate_limits:
                rate_limit = self.rate_limits[endpoint]
                now = time.time()

                # Count requests in current window
                cutoff_time = now - rate_limit.time_window
                current_requests = sum(
                    1 for req_time in requests if req_time > cutoff_time
                )

                stats[endpoint] = {
                    "current_requests": current_requests,
                    "max_requests": rate_limit.max_requests,
                    "time_window": rate_limit.time_window,
                    "remaining": max(0, rate_limit.max_requests - current_requests),
                }

        return stats


class SecurityValidator:
    """Input validation and security checks"""

    # Malicious patterns to detect
    MALICIOUS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # XSS
        r"javascript:",  # JavaScript URLs
        r"on\w+\s*=",  # Event handlers
        r"SELECT.*FROM",  # SQL injection
        r"UNION.*SELECT",  # SQL injection
        r"DROP.*TABLE",  # SQL injection
        r"INSERT.*INTO",  # SQL injection
        r"UPDATE.*SET",  # SQL injection
        r"DELETE.*FROM",  # SQL injection
        r"exec\s*\(",  # Code execution
        r"eval\s*\(",  # Code execution
        r"\.\./.*\.\.",  # Path traversal
        r"file://",  # File access
        r"http://.*\.onion",  # Tor links
    ]

    def __init__(self):
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.MALICIOUS_PATTERNS
        ]
        self._logger = logging.getLogger(self.__class__.__name__)

    def validate_user_input(
        self, text: str, max_length: int = 1000
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate user input for security threats

        Returns:
            (is_valid, error_message)
        """
        if not text:
            return True, None

        # Check length
        if len(text) > max_length:
            return False, f"Input too long (max {max_length} characters)"

        # Check for malicious patterns
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                self._logger.warning(
                    f"Malicious pattern detected in input: {text[:100]}..."
                )
                return False, "Invalid input detected"

        # Check for excessive special characters (potential obfuscation)
        special_char_ratio = sum(
            1 for c in text if not c.isalnum() and not c.isspace()
        ) / len(text)
        if special_char_ratio > 0.5:
            return False, "Input contains too many special characters"

        return True, None

    def sanitize_input(self, text: str) -> str:
        """Sanitize user input"""
        if not text:
            return ""

        # Remove null bytes
        text = text.replace("\x00", "")

        # Remove control characters except common whitespace
        text = "".join(char for char in text if ord(char) >= 32 or char in "\t\n\r")

        # Normalize whitespace
        text = " ".join(text.split())

        return text.strip()

    def is_suspicious_telegram_id(self, telegram_id: int) -> bool:
        """Check if Telegram ID looks suspicious"""
        # Check for obviously fake IDs
        if telegram_id <= 0 or telegram_id > 10**10:
            return True

        # Check for test bot IDs
        test_bot_patterns = [12345, 123456789, 987654321]
        if telegram_id in test_bot_patterns:
            return True

        return False

    def validate_phone_number(self, phone: str) -> Tuple[bool, Optional[str]]:
        """Validate phone number format"""
        if not phone:
            return False, "Phone number is required"

        # Remove all non-digit characters except +
        cleaned = re.sub(r"[^\d+]", "", phone)

        # Israeli phone number patterns
        israeli_patterns = [
            r"^\+972[2-9]\d{7,8}$",  # Landline
            r"^\+9725[0-9]\d{7}$",  # Mobile
            r"^0[2-9]\d{7,8}$",  # Local landline
            r"^05[0-9]\d{7}$",  # Local mobile
        ]

        for pattern in israeli_patterns:
            if re.match(pattern, cleaned):
                return True, None

        return False, "Invalid Israeli phone number format"


class SecurityMonitor:
    """Security event monitoring and alerting"""

    def __init__(self):
        self.security_events = deque(maxlen=1000)  # Keep last 1000 events
        self.blocked_users = {}  # user_id -> block_until_timestamp
        self._logger = logging.getLogger(self.__class__.__name__)

    def log_security_event(
        self, event_type: str, user_id: str, details: Dict[str, Any]
    ):
        """Log a security event"""
        event = {
            "timestamp": time.time(),
            "type": event_type,
            "user_id": user_id,
            "details": details,
        }

        self.security_events.append(event)

        # Log to security logger
        self._logger.warning(
            f"SECURITY EVENT: {event_type} - User: {user_id} - Details: {details}"
        )

        # Check if user should be temporarily blocked
        self._check_user_blocking(user_id, event_type)

    def _check_user_blocking(self, user_id: str, event_type: str):
        """Check if user should be temporarily blocked"""
        now = time.time()
        recent_events = [
            event
            for event in self.security_events
            if event["user_id"] == user_id
            and now - event["timestamp"] < 300  # Last 5 minutes
        ]

        # Block user if too many security events
        if len(recent_events) >= 5:
            block_duration = 3600  # 1 hour
            self.blocked_users[user_id] = now + block_duration

            self._logger.error(
                f"User {user_id} temporarily blocked for {block_duration}s due to "
                f"{len(recent_events)} security events in 5 minutes"
            )

    def is_user_blocked(self, user_id: str) -> Tuple[bool, Optional[int]]:
        """Check if user is blocked"""
        if user_id in self.blocked_users:
            block_until = self.blocked_users[user_id]
            if time.time() < block_until:
                remaining = int(block_until - time.time())
                return True, remaining
            else:
                # Block expired
                del self.blocked_users[user_id]

        return False, None

    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        now = time.time()

        # Events in last hour
        recent_events = [
            event for event in self.security_events if now - event["timestamp"] < 3600
        ]

        # Group by event type
        event_types = defaultdict(int)
        for event in recent_events:
            event_types[event["type"]] += 1

        return {
            "total_events_last_hour": len(recent_events),
            "events_by_type": dict(event_types),
            "blocked_users": len(self.blocked_users),
            "total_events_recorded": len(self.security_events),
        }


class BotSecurityManager:
    """Main security manager for the bot"""

    def __init__(self):
        # Rate limits configuration
        rate_limits = {
            "start": RateLimit(5, 60, "Start command"),
            "menu": RateLimit(20, 60, "Menu browsing"),
            "cart": RateLimit(15, 60, "Cart operations"),
            "order": RateLimit(3, 300, "Order creation"),
            "admin": RateLimit(10, 60, "Admin operations"),
            "general": RateLimit(30, 60, "General bot interactions"),
        }

        self.rate_limiter = SlidingWindowRateLimiter(rate_limits)
        self.validator = SecurityValidator()
        self.monitor = SecurityMonitor()
        self._logger = logging.getLogger(self.__class__.__name__)

    def check_request_allowed(
        self, user_id: int, endpoint: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if request is allowed (rate limiting + security)

        Returns:
            (is_allowed, error_message)
        """
        user_str = str(user_id)

        # Check if user is blocked
        is_blocked, block_remaining = self.monitor.is_user_blocked(user_str)
        if is_blocked:
            return (
                False,
                f"You are temporarily blocked. Try again in {block_remaining} seconds.",
            )

        # Check rate limiting
        is_allowed, retry_after = self.rate_limiter.is_allowed(user_str, endpoint)
        if not is_allowed:
            self.monitor.log_security_event(
                "rate_limit_exceeded",
                user_str,
                {"endpoint": endpoint, "retry_after": retry_after},
            )
            return False, f"Too many requests. Try again in {retry_after} seconds."

        return True, None

    def validate_message(
        self, user_id: int, message: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate user message"""
        user_str = str(user_id)

        # Check Telegram ID
        if self.validator.is_suspicious_telegram_id(user_id):
            self.monitor.log_security_event(
                "suspicious_telegram_id", user_str, {"telegram_id": user_id}
            )
            return False, "Invalid user ID"

        # Validate message content
        is_valid, error = self.validator.validate_user_input(message, max_length=2000)
        if not is_valid:
            self.monitor.log_security_event(
                "malicious_input", user_str, {"message": message[:100], "error": error}
            )
            return False, error

        return True, None

    def sanitize_message(self, message: str) -> str:
        """Sanitize user message"""
        return self.validator.sanitize_input(message)

    def get_security_report(self) -> Dict[str, Any]:
        """Get comprehensive security report"""
        return {
            "security_stats": self.monitor.get_security_stats(),
            "rate_limiter_active_users": len(self.rate_limiter.user_requests),
        }


# Global security manager instance
_security_manager: Optional[BotSecurityManager] = None


def get_security_manager() -> BotSecurityManager:
    """Get the global security manager instance"""
    global _security_manager
    if _security_manager is None:
        _security_manager = BotSecurityManager()
    return _security_manager


def security_check(endpoint: str = "general"):
    """
    Decorator for adding security checks to handlers

    Args:
        endpoint: The endpoint name for rate limiting
    """

    def decorator(func):
        async def wrapper(update, context, *args, **kwargs):
            user_id = update.effective_user.id
            security_manager = get_security_manager()

            # Check if request is allowed
            is_allowed, error_msg = security_manager.check_request_allowed(
                user_id, endpoint
            )
            if not is_allowed:
                await update.message.reply_text(f"⚠️ {error_msg}")
                return

            # Validate message if present
            if update.message and update.message.text:
                is_valid, error_msg = security_manager.validate_message(
                    user_id, update.message.text
                )
                if not is_valid:
                    await update.message.reply_text(f"⚠️ {error_msg}")
                    return

            # Call original function
            return await func(update, context, *args, **kwargs)

        return wrapper

    return decorator
