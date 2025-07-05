"""
Custom exceptions for the Samna Salta bot

Provides comprehensive error handling with proper type annotations.
"""

import logging
import time
import traceback
from typing import Optional

from telegram import MaybeInaccessibleMessage, Message, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class SamnaSaltaError(Exception):
    """Base exception for all Samna Salta errors"""

    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.user_message = user_message or "An error occurred. Please try again."
        self.error_code = error_code


class DatabaseError(SamnaSaltaError):
    """Database-related errors"""

    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(message)
        self.operation = operation


class DatabaseOperationError(DatabaseError):
    """Specific database operation errors"""

    pass


class DatabaseConnectionError(DatabaseError):
    """Database connection errors"""

    pass


class DatabaseTimeoutError(DatabaseError):
    """Database timeout errors"""

    pass


class DatabaseRetryExhaustedError(DatabaseError):
    """Error when database retries are exhausted"""

    pass


class ValidationError(SamnaSaltaError):
    """Input validation errors"""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field


class BusinessLogicError(SamnaSaltaError):
    """Business logic validation errors"""

    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(message, user_message)


class OrderError(BusinessLogicError):
    """Order-related business logic errors"""

    pass


class OrderNotFoundError(OrderError):
    """Order not found error"""

    def __init__(self, order_id: int):
        super().__init__(f"Order with ID {order_id} not found")
        self.order_id = order_id


class OrderStatusError(OrderError):
    """Invalid order status transition error"""

    pass


class CartError(BusinessLogicError):
    """Cart-related errors"""

    pass


class ProductError(BusinessLogicError):
    """Product-related errors"""

    pass


class CustomerError(BusinessLogicError):
    """Customer-related errors"""

    pass


class AuthenticationError(SamnaSaltaError):
    """Authentication and authorization errors"""

    pass


class RateLimitExceededError(SamnaSaltaError):
    """Rate limit exceeded error"""

    def __init__(self, reason: Optional[str] = None):
        message = f"Rate limit exceeded: {reason}" if reason else "Rate limit exceeded"
        super().__init__(message, "Please wait before trying again.")
        self.reason = reason


class ConfigurationError(SamnaSaltaError):
    """Configuration-related errors"""

    pass


class ExternalServiceError(SamnaSaltaError):
    """External service errors (Telegram API, etc.)"""

    pass


class TelegramError(ExternalServiceError):
    """Telegram-specific errors"""

    pass


class ProductNotFoundError(BusinessLogicError):
    """Product not found"""

    def __init__(self, product_name: str):
        super().__init__(
            f"Product not found: {product_name}",
            f"Sorry, {product_name} is not available right now.",
        )


class CartEmptyError(BusinessLogicError):
    """Cart is empty when operation requires items"""

    def __init__(self):
        super().__init__(
            "Cart is empty", "Your cart is empty. Please add some items first."
        )


class CustomerNotFoundError(BusinessLogicError):
    """Customer not found"""

    def __init__(self, user_id: int):
        super().__init__(
            f"Customer not found: {user_id}",
            "Customer information not found. Please start again with /start",
        )


class OrderCreationError(DatabaseError):
    """Order creation failed"""

    def __init__(self, reason: str = None):
        super().__init__(
            f"Order creation failed: {reason}",
            "Sorry, we couldn't process your order. Please try again.",
        )


class HilbehNotAvailableError(BusinessLogicError):
    """Hilbeh not available today"""

    def __init__(self):
        super().__init__(
            "Hilbeh not available today",
            "Hilbeh is only available Wednesday through Friday.",
        )


async def handle_error(
    update: Update,
    error: Exception,
    operation: str = "unknown",
) -> None:
    """
    Central error handler for all bot operations
    """
    user_id = update.effective_user.id if update.effective_user else "unknown"

    # Log the error with context
    error_context = {
        "operation": operation,
        "user_id": user_id,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }

    if isinstance(error, SamnaSaltaError):
        # Handle our custom exceptions
        logger.warning(
            "Business error in %s: %s", operation, error, extra=error_context
        )

        try:
            if update.message:
                await update.message.reply_text(error.user_message)
            elif update.callback_query:
                await update.callback_query.message.reply_text(error.user_message)
        except (IOError, OSError) as reply_error:
            logger.error("Failed to send error message: %s", reply_error)

    else:
        # Handle unexpected exceptions
        logger.error(
            "Unexpected error in %s: %s",
            operation,
            error,
            extra=error_context,
            exc_info=True,
        )

        try:
            error_message = (
                "Sorry, something went wrong. Our team has been notified. "
                "Please try again in a few minutes."
            )

            if update.message:
                await update.message.reply_text(error_message)
            elif update.callback_query:
                await update.callback_query.message.reply_text(error_message)
        except (IOError, OSError) as reply_error:
            logger.error("Failed to send error message: %s", reply_error)


def error_handler(operation: str = "unknown"):
    """
    Decorator for handling errors in bot handlers
    """

    def decorator(func):
        async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            try:
                return await func(update, context, *args, **kwargs)
            except SamnaSaltaError as e:
                await handle_error(update, e, operation)
                return None

        return wrapper

    return decorator


# pylint: disable=too-few-public-methods
class ErrorReporter:
    """Enhanced error reporting with proper type checking"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def report_error(
        self,
        error: Exception,
        update: Optional[Update] = None,
        context=None,
        user_message: Optional[str] = None,
    ) -> None:
        """Report error with proper context"""
        # Log the error
        self.logger.error(
            f"Error occurred: {error}",
            exc_info=True,
            extra={
                "error_type": type(error).__name__,
                "user_id": update.effective_user.id
                if update and update.effective_user
                else None,
                "update_type": type(update).__name__ if update else None,
            },
        )

        # Send user-friendly message
        if update:
            error_text = user_message or getattr(
                error, "user_message", "An error occurred. Please try again."
            )

            # For callback queries
            if update.callback_query:
                await send_callback_error_message(update.callback_query, error_text)
            # For regular messages
            elif update.effective_message:
                await send_error_message(update, update.effective_message, error_text)


# Global error reporter instance
error_reporter = ErrorReporter()


async def send_error_message(
    update: Update, message: Optional[Message], error_text: str
) -> None:
    """Send error message safely to user"""
    try:
        if message and hasattr(message, "reply_text"):
            await message.reply_text(error_text)
        elif update.effective_message and hasattr(
            update.effective_message, "reply_text"
        ):
            await update.effective_message.reply_text(error_text)
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")


async def send_callback_error_message(query, error_text: str) -> None:
    """Send error message for callback queries safely"""
    try:
        if query and hasattr(query, "message"):
            message = query.message
            if message and hasattr(message, "reply_text"):
                await message.reply_text(error_text)
    except Exception as e:
        logger.error(f"Failed to send callback error message: {e}")


def validate_and_raise(condition: bool, error_class: type, *args, **kwargs):
    """Helper function to validate condition and raise specific error"""
    if not condition:
        raise error_class(*args, **kwargs)


class CircuitBreaker:
    """Simple circuit breaker for external services"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise DatabaseError("Service temporarily unavailable")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"

            raise e
