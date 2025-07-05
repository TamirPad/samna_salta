"""
Rate limiting and security enhancements
"""

import logging
import re
import threading
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

    def __repr__(self) -> str:
        return f"TokenBucket(capacity={self.capacity}, tokens={self.tokens:.2f})"


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
            "Rate limit exceeded for user %s on endpoint %s. "
            "Requests: %d/%d in %ds window",
            user_id,
            endpoint,
            len(user_requests),
            rate_limit.max_requests,
            rate_limit.time_window,
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
                    "Malicious pattern detected in input: %s...", text[:100]
                )
                return False, "Invalid input detected"

        # Check for excessive special characters (potential obfuscation)
        special_char_ratio = (
            sum(1 for c in text if not c.isalnum() and not c.isspace()) / len(text)
        )
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
        """Log a security event and check for suspicious patterns"""
        event = {
            "timestamp": time.time(),
            "type": event_type,
            "user_id": user_id,
            "details": details,
        }
        self.security_events.append(event)
        self._logger.warning(
            "SECURITY EVENT: [%s] User %s - Details: %s",
            event_type,
            user_id,
            details,
        )
        self._check_user_blocking(user_id)

    def _check_user_blocking(self, user_id: str):
        """Check if a user should be temporarily blocked"""
        now = time.time()
        user_events = [
            e
            for e in self.security_events
            if e["user_id"] == user_id and now - e["timestamp"] < 3600
        ]

        # Example blocking logic: block for 5 mins if > 5 invalid inputs in an hour
        if len(user_events) > 5:
            block_until = now + 300  # Block for 5 minutes
            self.blocked_users[user_id] = block_until
            self._logger.critical(
                "User %s temporarily blocked until %s due to suspicious activity",
                user_id,
                time.ctime(block_until),
            )

    def is_user_blocked(self, user_id: str) -> Tuple[bool, Optional[int]]:
        """Check if a user is currently blocked"""
        block_until = self.blocked_users.get(user_id)
        if block_until and time.time() < block_until:
            retry_after = int(block_until - time.time())
            return True, retry_after
        return False, None

    def get_security_stats(self) -> Dict[str, Any]:
        """Get security monitoring statistics"""
        now = time.time()
        recent_events = [e for e in self.security_events if now - e["timestamp"] < 3600]
        event_types = defaultdict(int)
        for event in recent_events:
            event_types[event["type"]] += 1

        return {
            "total_events_logged": len(self.security_events),
            "events_last_hour": event_types,
            "currently_blocked_users": len(
                [
                    u
                    for u, t in self.blocked_users.items()
                    if t > now
                ]
            ),
        }


class BotSecurityManager:
    """Comprehensive security manager for the bot"""

    _instance: Optional["BotSecurityManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        # Rate limits configuration
        rate_limits = {
            "start": RateLimit(5, 60, "Start command"),
            "menu": RateLimit(10, 60, "Menu interaction"),
            "cart": RateLimit(20, 60, "Cart operations"),
            "order": RateLimit(5, 300, "Order creation"),
            "general": RateLimit(30, 60, "General messages"),
        }
        self.rate_limiter = SlidingWindowRateLimiter(rate_limits)
        self.validator = SecurityValidator()
        self.monitor = SecurityMonitor()

    @classmethod
    def get_instance(cls) -> "BotSecurityManager":
        """Get the singleton instance of the security manager"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    logger.info("Initializing BotSecurityManager singleton...")
                    cls._instance = BotSecurityManager()
        return cls._instance

    def check_request_allowed(
        self, user_id: int, endpoint: str
    ) -> Tuple[bool, Optional[str]]:
        """Check rate limits and if user is blocked"""
        # Check blocking first
        is_blocked, retry_after_block = self.monitor.is_user_blocked(str(user_id))
        if is_blocked:
            return False, f"You are temporarily blocked. Please try again in {retry_after_block}s."

        # Check rate limiting
        is_allowed, retry_after_limit = self.rate_limiter.is_allowed(
            str(user_id), endpoint
        )
        if not is_allowed:
            return False, f"Rate limit exceeded. Please try again in {retry_after_limit}s."

        return True, None

    def validate_message(
        self, user_id: int, message: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate incoming user message"""
        # Suspicious ID check
        if self.validator.is_suspicious_telegram_id(user_id):
            self.monitor.log_security_event(
                "suspicious_telegram_id", str(user_id), {"id": user_id}
            )
            return False, "Invalid user ID."

        # Input validation
        is_valid, error = self.validator.validate_user_input(message)
        if not is_valid:
            self.monitor.log_security_event(
                "invalid_input", str(user_id), {"message": message[:100]}
            )
            return False, error

        return True, None

    def sanitize_message(self, message: str) -> str:
        """Sanitize a user message"""
        return self.validator.sanitize_input(message)

    def get_security_report(self) -> Dict[str, Any]:
        """Get combined security report"""
        rate_limit_stats = {}
        for user_id in self.rate_limiter.user_requests:
            rate_limit_stats[user_id] = self.rate_limiter.get_user_stats(user_id)

        return {
            "security_monitor_stats": self.monitor.get_security_stats(),
            "rate_limit_stats": rate_limit_stats,
        }


def get_security_manager() -> "BotSecurityManager":
    """Get the singleton instance of the security manager"""
    return BotSecurityManager.get_instance()


def security_check(endpoint: str = "general"):
    """
    Decorator for rate limiting and security checks on Telegram handlers.
    """

    def decorator(func):
        """Decorator function"""

        async def wrapper(update, context, *args, **kwargs):
            """Wrapper that performs security checks"""
            if not update or not update.effective_user:
                return await func(update, context, *args, **kwargs)

            user_id = update.effective_user.id
            manager = get_security_manager()

            # Check rate limiting and blocking
            is_allowed, error_msg = manager.check_request_allowed(user_id, endpoint)
            if not is_allowed and error_msg:
                await update.message.reply_text(error_msg)
                return

            # Validate message content if available
            if update.message and update.message.text:
                is_valid, error_msg = manager.validate_message(
                    user_id, update.message.text
                )
                if not is_valid and error_msg:
                    await update.message.reply_text(error_msg)
                    return

            return await func(update, context, *args, **kwargs)

        return wrapper

    return decorator
