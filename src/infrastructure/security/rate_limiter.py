"""
Rate limiting functionality for the Samna Salta bot with circuit breaker pattern

Uses constants for thresholds and proper type annotations for better maintainability.
"""

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import DefaultDict, Deque, Dict, Optional, Tuple

from src.infrastructure.logging.logging_config import SecurityLogger
from src.infrastructure.utilities.constants import SecuritySettings
from src.infrastructure.utilities.exceptions import RateLimitExceededError

logger = logging.getLogger(__name__)
security_logger = SecurityLogger()


class CircuitBreakerState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""

    max_requests: int = SecuritySettings.DEFAULT_RATE_LIMIT_REQUESTS
    window_seconds: int = SecuritySettings.DEFAULT_RATE_LIMIT_WINDOW_SECONDS
    block_duration_seconds: int = SecuritySettings.DEFAULT_RATE_LIMIT_WINDOW_SECONDS


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""

    failure_threshold: int = SecuritySettings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
    timeout_seconds: int = SecuritySettings.CIRCUIT_BREAKER_TIMEOUT_SECONDS
    half_open_max_calls: int = 5


@dataclass
class UserRateLimit:
    """Rate limit data for a user"""

    requests: Deque[float] = field(default_factory=deque)
    blocked_until: Optional[float] = None
    violation_count: int = 0


@dataclass
class CircuitBreakerData:
    """Circuit breaker data for a user"""

    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    half_open_calls: int = 0


class RateLimiter:
    """Rate limiter with circuit breaker functionality"""

    def __init__(
        self,
        default_config: Optional[RateLimitConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    ):
        self.default_config = default_config or RateLimitConfig()
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        self.user_limits: DefaultDict[int, UserRateLimit] = defaultdict(UserRateLimit)
        self.circuit_breakers: DefaultDict[int, CircuitBreakerData] = defaultdict(
            CircuitBreakerData
        )
        self.endpoint_configs: Dict[str, RateLimitConfig] = {}

    def configure_endpoint(self, endpoint: str, config: RateLimitConfig) -> None:
        """Configure rate limiting for specific endpoint"""
        self.endpoint_configs[endpoint] = config
        logger.info(f"Rate limit configured for endpoint {endpoint}: {config}")

    def configure_endpoints_from_constants(self) -> None:
        """Configure endpoints using predefined constants"""
        self.endpoint_configs.update(
            {
                "menu": RateLimitConfig(
                    max_requests=SecuritySettings.MENU_RATE_LIMIT,
                    window_seconds=SecuritySettings.DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
                ),
                "cart": RateLimitConfig(
                    max_requests=SecuritySettings.CART_RATE_LIMIT,
                    window_seconds=SecuritySettings.DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
                ),
                "order": RateLimitConfig(
                    max_requests=SecuritySettings.ORDER_RATE_LIMIT,
                    window_seconds=SecuritySettings.DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
                ),
                "admin": RateLimitConfig(
                    max_requests=SecuritySettings.ADMIN_RATE_LIMIT,
                    window_seconds=SecuritySettings.DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
                ),
            }
        )

    def is_allowed(
        self, user_id: int, endpoint: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Check if user is allowed to make request"""
        current_time = time.time()

        # Check circuit breaker
        if not self._is_circuit_breaker_allowed(user_id, current_time):
            security_logger.log_suspicious_activity(
                user_id,
                "circuit_breaker_blocked",
                {"endpoint": endpoint, "timestamp": current_time},
            )
            return False, "Service temporarily unavailable. Please try again later."

        # Get appropriate config
        config = self.endpoint_configs.get(endpoint, self.default_config)
        user_limit = self.user_limits[user_id]

        # Check if user is currently blocked
        if user_limit.blocked_until and current_time < user_limit.blocked_until:
            remaining_time = int(user_limit.blocked_until - current_time)
            return False, f"Rate limit exceeded. Try again in {remaining_time} seconds."

        # Clean up old requests
        cutoff_time = current_time - config.window_seconds
        while user_limit.requests and user_limit.requests[0] <= cutoff_time:
            user_limit.requests.popleft()

        # Check rate limit
        if len(user_limit.requests) >= config.max_requests:
            # Block user
            user_limit.blocked_until = current_time + config.block_duration_seconds
            user_limit.violation_count += 1

            # Log security event
            security_logger.log_rate_limit_exceeded(
                user_id,
                endpoint or "unknown",
                {
                    "violation_count": user_limit.violation_count,
                    "blocked_until": user_limit.blocked_until,
                    "requests_in_window": len(user_limit.requests),
                },
            )

            logger.warning(
                f"Rate limit exceeded for user {user_id} on endpoint {endpoint}",
                extra={
                    "user_id": user_id,
                    "endpoint": endpoint,
                    "violation_count": user_limit.violation_count,
                    "requests_in_window": len(user_limit.requests),
                },
            )

            return False, "Rate limit exceeded. Please slow down."

        # Add current request
        user_limit.requests.append(current_time)
        return True, None

    def record_success(self, user_id: int) -> None:
        """Record successful request for circuit breaker"""
        circuit_breaker = self.circuit_breakers[user_id]

        if circuit_breaker.state == CircuitBreakerState.HALF_OPEN:
            circuit_breaker.half_open_calls += 1
            if (
                circuit_breaker.half_open_calls
                >= self.circuit_breaker_config.half_open_max_calls
            ):
                circuit_breaker.state = CircuitBreakerState.CLOSED
                circuit_breaker.failure_count = 0
                circuit_breaker.half_open_calls = 0
                logger.info(f"Circuit breaker closed for user {user_id}")
        elif circuit_breaker.state == CircuitBreakerState.CLOSED:
            circuit_breaker.failure_count = 0

    def record_failure(self, user_id: int) -> None:
        """Record failed request for circuit breaker"""
        circuit_breaker = self.circuit_breakers[user_id]
        current_time = time.time()

        circuit_breaker.failure_count += 1
        circuit_breaker.last_failure_time = current_time

        if (
            circuit_breaker.failure_count
            >= self.circuit_breaker_config.failure_threshold
        ):
            circuit_breaker.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker opened for user {user_id}")

            security_logger.log_suspicious_activity(
                user_id,
                "circuit_breaker_opened",
                {
                    "failure_count": circuit_breaker.failure_count,
                    "threshold": self.circuit_breaker_config.failure_threshold,
                },
            )

    def _is_circuit_breaker_allowed(self, user_id: int, current_time: float) -> bool:
        """Check if circuit breaker allows request"""
        circuit_breaker = self.circuit_breakers[user_id]

        if circuit_breaker.state == CircuitBreakerState.CLOSED:
            return True
        elif circuit_breaker.state == CircuitBreakerState.OPEN:
            if (
                circuit_breaker.last_failure_time
                and current_time - circuit_breaker.last_failure_time
                > self.circuit_breaker_config.timeout_seconds
            ):
                circuit_breaker.state = CircuitBreakerState.HALF_OPEN
                circuit_breaker.half_open_calls = 0
                logger.info(f"Circuit breaker half-open for user {user_id}")
                return True
            return False
        elif circuit_breaker.state == CircuitBreakerState.HALF_OPEN:
            return (
                circuit_breaker.half_open_calls
                < self.circuit_breaker_config.half_open_max_calls
            )

        return False

    def get_user_status(self, user_id: int) -> Dict[str, any]:
        """Get rate limit status for user"""
        current_time = time.time()
        user_limit = self.user_limits[user_id]
        circuit_breaker = self.circuit_breakers[user_id]

        # Clean up old requests
        cutoff_time = current_time - self.default_config.window_seconds
        while user_limit.requests and user_limit.requests[0] <= cutoff_time:
            user_limit.requests.popleft()

        return {
            "user_id": user_id,
            "requests_in_window": len(user_limit.requests),
            "max_requests": self.default_config.max_requests,
            "window_seconds": self.default_config.window_seconds,
            "is_blocked": user_limit.blocked_until is not None
            and current_time < user_limit.blocked_until,
            "blocked_until": user_limit.blocked_until,
            "violation_count": user_limit.violation_count,
            "circuit_breaker_state": circuit_breaker.state.value,
            "circuit_breaker_failures": circuit_breaker.failure_count,
        }

    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics"""
        current_time = time.time()

        total_users = len(self.user_limits)
        blocked_users = sum(
            1
            for user_limit in self.user_limits.values()
            if user_limit.blocked_until and current_time < user_limit.blocked_until
        )

        circuit_breaker_stats = {"open": 0, "half_open": 0, "closed": 0}

        for cb in self.circuit_breakers.values():
            circuit_breaker_stats[cb.state.value] += 1

        return {
            "total_users": total_users,
            "blocked_users": blocked_users,
            "circuit_breakers": circuit_breaker_stats,
            "endpoint_configs": {
                endpoint: {
                    "max_requests": config.max_requests,
                    "window_seconds": config.window_seconds,
                }
                for endpoint, config in self.endpoint_configs.items()
            },
        }

    def cleanup_expired(self) -> int:
        """Clean up expired rate limit data"""
        current_time = time.time()
        cleaned_count = 0

        # Clean up expired blocks
        for user_limit in self.user_limits.values():
            if user_limit.blocked_until and current_time >= user_limit.blocked_until:
                user_limit.blocked_until = None
                cleaned_count += 1

        # Clean up old requests
        cutoff_time = current_time - self.default_config.window_seconds
        for user_limit in self.user_limits.values():
            old_count = len(user_limit.requests)
            while user_limit.requests and user_limit.requests[0] <= cutoff_time:
                user_limit.requests.popleft()
            cleaned_count += old_count - len(user_limit.requests)

        return cleaned_count

    def reset_user(self, user_id: int) -> None:
        """Reset rate limit data for a user"""
        if user_id in self.user_limits:
            del self.user_limits[user_id]
        if user_id in self.circuit_breakers:
            del self.circuit_breakers[user_id]
        logger.info(f"Reset rate limit data for user {user_id}")


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
        _rate_limiter.configure_endpoints_from_constants()
    return _rate_limiter


def rate_limit_check(user_id: int, endpoint: Optional[str] = None) -> None:
    """Check rate limit and raise exception if exceeded"""
    allowed, message = get_rate_limiter().is_allowed(user_id, endpoint)
    if not allowed:
        raise RateLimitExceededError(message or "Rate limit exceeded")


def record_request_success(user_id: int) -> None:
    """Record successful request"""
    get_rate_limiter().record_success(user_id)


def record_request_failure(user_id: int) -> None:
    """Record failed request for global rate limiter"""
    _rate_limiter.record_failure(user_id)


# Legacy aliases and additional classes for backward compatibility
class BotSecurityManager:
    """Security manager for the bot - wrapper around RateLimiter"""

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter or get_rate_limiter()

    def check_rate_limit(self, user_id: int, endpoint: Optional[str] = None) -> bool:
        """Check if user is within rate limits"""
        allowed, _ = self.rate_limiter.is_allowed(user_id, endpoint)
        return allowed

    def record_success(self, user_id: int) -> None:
        """Record successful request"""
        self.rate_limiter.record_success(user_id)

    def record_failure(self, user_id: int) -> None:
        """Record failed request"""
        self.rate_limiter.record_failure(user_id)

    # ------------------------------------------------------------------
    # Back-compatibility helpers expected by tests
    # ------------------------------------------------------------------

    def check_request_allowed(self, user_id: int, endpoint: str | None = None):
        """Return (is_allowed, error_msg) tuple, matching older API used in tests."""
        return self.rate_limiter.is_allowed(user_id, endpoint)

    def validate_message(self, user_id: int, message: str):
        """Very simple message validation placeholder.

        Marks messages containing obvious XSS/script patterns as invalid. Otherwise allowed.
        """
        lowered = message.lower()
        forbidden_substrings = ["<script", "javascript:", "onerror=", "onclick="]
        if any(sub in lowered for sub in forbidden_substrings):
            return False, "Invalid message content"
        # also apply rate limiter so spammers can be blocked
        allowed, err = self.rate_limiter.is_allowed(user_id, "message")
        if not allowed:
            return False, err or "Rate limited"
        return True, None

    def get_security_report(self):
        """Get security statistics and report"""
        return {"security_stats": self.rate_limiter.get_stats(), "rate_limiter_active_users": len(self.rate_limiter.user_limits)}

    def is_admin(self, telegram_id):
        """Check if a user is an admin based on their telegram_id
        
        Args:
            telegram_id: TelegramId or int value of the user's Telegram ID
        
        Returns:
            bool: True if the user is an admin, False otherwise
        """
        # Get the numeric value if it's a TelegramId object
        user_id = telegram_id.value if hasattr(telegram_id, 'value') else telegram_id
        
        # Admin IDs may come from configuration (.env / config.yaml)
        try:
            from src.infrastructure.configuration.config import get_config  # local import to avoid heavy import chains

            cfg = get_config()
            admin_ids_cfg = [cfg.admin_chat_id] if getattr(cfg, "admin_chat_id", None) else []
        except Exception:  # pragma: no cover – config not yet initialised in some tests
            admin_ids_cfg = []

        # Fallback hard-coded ID(s) to keep backward compatibility
        legacy_ids = [598829473]

        admin_ids = set(admin_ids_cfg + legacy_ids)

        return user_id in admin_ids


class RateLimit:
    """Rate limit decorator and utility"""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def __call__(self, func):
        """Decorator to apply rate limiting"""

        def wrapper(*args, **kwargs):
            # This would need to be implemented based on the specific use case
            return func(*args, **kwargs)

        return wrapper


class SecurityValidator:
    """Security validation utilities"""

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter or get_rate_limiter()

    def validate_user_request(
        self, user_id: int, endpoint: Optional[str] = None
    ) -> bool:
        """Validate user request"""
        allowed, _ = self.rate_limiter.is_allowed(user_id, endpoint)
        return allowed

    def is_user_blocked(self, user_id: int) -> bool:
        """Check if user is currently blocked"""
        user_limit = self.rate_limiter.user_limits[user_id]
        return (
            user_limit.blocked_until is not None
            and time.time() < user_limit.blocked_until
        )

    # ------------------------------------------------------------------
    # Compatibility helpers expected by tests
    # ------------------------------------------------------------------

    def validate_user_input(self, text: str, max_length: int = 1000):
        """Basic validation: length and simple XSS patterns."""
        if not text or len(text) > max_length:
            return False, "Invalid length"

        lowered = text.lower()
        forbidden_substrings = [
            "<script",
            "javascript:",
            "onerror=",
            "onclick=",
            "eval(",
            "exec(",
            "..",  # directory traversal
            "file://",
            "etc/passwd",
        ]
        if any(sub in lowered for sub in forbidden_substrings):
            return False, "Invalid content"

        return True, None

    def validate_phone_number(self, phone: str):
        """Very lightweight phone validation for tests – checks digits length."""
        import re

        digits = re.sub(r"\D", "", phone)
        if 7 <= len(digits) <= 15:
            return True, None
        return False, "Invalid phone number"


def get_security_manager() -> BotSecurityManager:
    """Get global security manager instance"""
    return BotSecurityManager()


def security_check(user_id: int, endpoint: Optional[str] = None) -> bool:
    """Perform security check for user and endpoint"""
    manager = get_security_manager()
    return manager.check_rate_limit(user_id, endpoint)
