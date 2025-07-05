"""
Custom exceptions and error handling for the Samna Salta bot
"""

import logging
import time
import traceback

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class SamnaSaltaError(Exception):
    """Base exception for Samna Salta bot"""

    def __init__(self, message: str, user_message: str = None, error_code: str = None):
        super().__init__(message)
        self.user_message = user_message or "An error occurred. Please try again."
        self.error_code = error_code or "GENERAL_ERROR"


class DatabaseError(SamnaSaltaError):
    """Database-related errors"""

    def __init__(self, message: str, operation: str = None):
        super().__init__(
            message,
            "Sorry, there was a problem with our system. Please try again in a moment.",
            "DATABASE_ERROR",
        )
        self.operation = operation


class ValidationError(SamnaSaltaError):
    """Input validation errors"""

    def __init__(self, message: str, field: str = None):
        super().__init__(
            message, message, "VALIDATION_ERROR"  # Validation errors are user-friendly
        )
        self.field = field


class BusinessLogicError(SamnaSaltaError):
    """Business rule violations"""

    def __init__(self, message: str, user_message: str = None):
        super().__init__(message, user_message or message, "BUSINESS_ERROR")


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


class OrderNotFoundError(BusinessLogicError):
    """Order not found"""

    def __init__(self, order_id: int):
        super().__init__(
            f"Order not found: {order_id}", f"Order #{order_id} not found."
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
        logger.warning("Business error in %s: %s", operation, error, extra=error_context)

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
    """Error reporting and monitoring class"""

    @staticmethod
    def report_critical_error(error: Exception):
        """Report critical errors to monitoring system"""
        # In production, integrate with monitoring services like Sentry
        logger.critical(
            "CRITICAL ERROR: %s",
            error,
            extra={
                "error_type": type(error).__name__,
                "traceback": traceback.format_exc(),
            },
        )

    @staticmethod
    def report_business_error(error: BusinessLogicError, user_id: int):
        """Report business logic errors for analysis"""
        logger.info(
            "Business error: %s - %s",
            error.error_code,
            error,
            extra={
                "error_code": error.error_code,
                "user_id": user_id,
                "error_type": type(error).__name__,
            },
        )


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
