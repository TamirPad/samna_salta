"""
Error handling utilities for the Samna Salta bot
"""

import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Dict, Optional, Callable

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import time

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""

    BUSINESS_LOGIC = "business_logic"
    DATABASE = "database"
    TELEGRAM_API = "telegram_api"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"


@dataclass
class ApplicationError(Exception):
    """Base application error with enhanced context"""

    message: str
    error_code: str = "UNKNOWN"
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.SYSTEM
    context: Optional[Dict[str, Any]] = field(default_factory=dict)
    original_error: Optional[Exception] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BusinessLogicError(ApplicationError):
    """Business logic specific errors"""

    error_code: str = "BUSINESS_ERROR"
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.BUSINESS_LOGIC


@dataclass
class DatabaseError(ApplicationError):
    """Database operation errors"""

    error_code: str = "DB_ERROR"
    severity: ErrorSeverity = ErrorSeverity.HIGH
    category: ErrorCategory = ErrorCategory.DATABASE


@dataclass
class DatabaseConnectionError(DatabaseError):
    """Database connection errors"""

    error_code: str = "DB_CONNECTION_ERROR"
    severity: ErrorSeverity = ErrorSeverity.CRITICAL
    category: ErrorCategory = ErrorCategory.DATABASE


@dataclass
class DatabaseOperationError(DatabaseError):
    """Database operation errors"""

    error_code: str = "DB_OPERATION_ERROR"
    severity: ErrorSeverity = ErrorSeverity.HIGH
    category: ErrorCategory = ErrorCategory.DATABASE


@dataclass
class TelegramAPIError(ApplicationError):
    """Telegram API related errors"""

    error_code: str = "TELEGRAM_ERROR"
    severity: ErrorSeverity = ErrorSeverity.HIGH
    category: ErrorCategory = ErrorCategory.TELEGRAM_API


@dataclass
class ValidationError(ApplicationError):
    """Input validation errors"""

    error_code: str = "VALIDATION_ERROR"
    severity: ErrorSeverity = ErrorSeverity.LOW
    category: ErrorCategory = ErrorCategory.VALIDATION


@dataclass
class ErrorReport:
    """Dataclass for error reports"""

    error: Exception
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    update: Optional[Update] = None
    context_types: Optional[ContextTypes.DEFAULT_TYPE] = None


class ErrorReporter:
    """Enhanced error reporting with metrics and alerts"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_metrics = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recent_errors": [],
        }

    def report_error(self, *args, **kwargs) -> str:
        """Flexible error reporting.

        Legacy tests call `report_error(error, user_id="x")` directly.  Accept either an
        `ErrorReport` instance or a bare Exception plus kwargs.
        """

        if len(args) == 1 and isinstance(args[0], ErrorReport):
            report: ErrorReport = args[0]
        else:
            # Build ErrorReport from positional/keyword params
            error = args[0] if args else kwargs.get("error")
            user_id = kwargs.get("user_id")
            context = kwargs.get("context")
            report = ErrorReport(error=error, user_id=user_id, context=context)

        # ---- original implementation below (slightly refactored to use `report`) ----
        error_obj = report.error
        # Generate unique error ID
        error_id = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(error_obj)}"

        # Extract error details
        if isinstance(error_obj, ApplicationError):
            error_details = {
                "error_id": error_id,
                "error_message": error_obj.message,
                "error_code": error_obj.error_code,
                "severity": error_obj.severity.value,
                "category": error_obj.category.value,
                "context": error_obj.context,
                "timestamp": error_obj.timestamp.isoformat(),
                "user_id": report.user_id,
                "additional_context": report.context,
            }
        else:
            error_details = {
                "error_id": error_id,
                "error_message": str(error_obj),
                "error_code": "UNKNOWN",
                "severity": ErrorSeverity.MEDIUM.value,
                "category": ErrorCategory.SYSTEM.value,
                "context": report.context or {},
                "timestamp": datetime.now().isoformat(),
                "user_id": report.user_id,
                "traceback": traceback.format_exc(),
            }

        # Update metrics
        self._update_metrics(error_details)

        # Log error based on severity
        self._log_error(error_details)

        # Check for critical errors that need immediate attention
        if error_details.get("severity") == ErrorSeverity.CRITICAL.value:
            self._handle_critical_error(error_details)

        return error_id

    def _update_metrics(self, error_details: Dict[str, Any]):
        """Update error metrics"""
        self.error_metrics["total_errors"] += 1

        category = error_details.get("category", "unknown")
        severity = error_details.get("severity", "unknown")

        # Update category metrics
        if category not in self.error_metrics["errors_by_category"]:
            self.error_metrics["errors_by_category"][category] = 0
        self.error_metrics["errors_by_category"][category] += 1

        # Update severity metrics
        if severity not in self.error_metrics["errors_by_severity"]:
            self.error_metrics["errors_by_severity"][severity] = 0
        self.error_metrics["errors_by_severity"][severity] += 1

        # Keep track of recent errors (last 50)
        self.error_metrics["recent_errors"].append(error_details)
        if len(self.error_metrics["recent_errors"]) > 50:
            self.error_metrics["recent_errors"].pop(0)

    def _log_error(self, error_details: Dict[str, Any]):
        """Log error with appropriate level"""
        severity = error_details.get("severity", "medium")

        log_message = (
            "ERROR [%(error_id)s] %(error_message)s "
            "(Code: %(error_code)s, Category: %(category)s, User: %(user_id)s)"
        )

        if severity == ErrorSeverity.CRITICAL.value:
            self.logger.critical(log_message, error_details)
        elif severity == ErrorSeverity.HIGH.value:
            self.logger.error(log_message, error_details)
        elif severity == ErrorSeverity.MEDIUM.value:
            self.logger.warning(log_message, error_details)
        else:
            self.logger.info(log_message, error_details)

    def _handle_critical_error(self, error_details: Dict[str, Any]):
        """Handle critical errors that need immediate attention"""
        self.logger.critical("🚨 CRITICAL ERROR DETECTED: %(error_id)s 🚨", error_details)

        # Here you could add integrations with:
        # - Slack/Discord notifications
        # - Email alerts
        # - PagerDuty
        # - Sentry
        # - Custom monitoring systems

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        return {
            "total_errors": self.error_metrics["total_errors"],
            "errors_by_category": self.error_metrics["errors_by_category"],
            "errors_by_severity": self.error_metrics["errors_by_severity"],
            "recent_error_count": len(self.error_metrics["recent_errors"]),
            "critical_errors_last_24h": len(
                [
                    e
                    for e in self.error_metrics["recent_errors"]
                    if e.get("severity") == ErrorSeverity.CRITICAL.value
                ]
            ),
        }


class ErrorHandler:
    """Global error handler with recovery strategies"""

    def __init__(self):
        self.reporter = ErrorReporter()
        self.logger = logging.getLogger(__name__)
        self.recovery_strategies = {
            ErrorCategory.DATABASE: self._recover_database_error,
            ErrorCategory.TELEGRAM_API: self._recover_telegram_error,
            ErrorCategory.BUSINESS_LOGIC: self._recover_business_error,
        }

    async def handle_error(self, report: ErrorReport) -> bool:
        """Handle an error, report it, and attempt recovery"""

        # Report the error
        self.reporter.report_error(report)

        # Attempt recovery if possible
        recovered = False
        if isinstance(report.error, ApplicationError):
            if report.error.category in self.recovery_strategies:
                recovered = await self.recovery_strategies[report.error.category](
                    report.error, report.update, report.context_types
                )

        # Send a user-friendly message if not recovered
        if not recovered and report.update:
            await self._send_user_error_message(report.error, report.update)

        return recovered

    def __repr__(self):
        return f"ErrorHandler(reporter={self.reporter})"

    async def _recover_database_error(
        self,
        _error: ApplicationError,
        _update: Optional[Update],
        _context: Optional[ContextTypes.DEFAULT_TYPE],
    ):
        """Recovery strategy for database errors"""
        # Placeholder for recovery logic, e.g., retry mechanism
        return False

    async def _recover_telegram_error(
        self,
        _error: ApplicationError,
        _update: Optional[Update],
        _context: Optional[ContextTypes.DEFAULT_TYPE],
    ):
        """Recovery strategy for Telegram API errors"""
        # Placeholder for recovery logic, e.g., exponential backoff
        return False

    async def _recover_business_error(
        self,
        _error: ApplicationError,
        _update: Optional[Update],
        _context: Optional[ContextTypes.DEFAULT_TYPE],
    ):
        """Recovery strategy for business logic errors"""
        # Placeholder for recovery logic, e.g., alternative data source
        return False

    async def _send_user_error_message(
        self,
        error: Exception,
        update: Update,
    ):
        """Send a user-friendly error message"""
        user_message = "Something went wrong. Please try again later."
        if isinstance(error, ApplicationError):
            user_message = error.message

        try:
            if update.callback_query:
                await update.callback_query.answer(user_message, show_alert=True)
            elif update.message:
                await update.message.reply_text(user_message)
        except (IOError, OSError) as e:
            self.logger.error("Failed to send error message to user: %s", e)


def handle_errors(
    error_category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
):
    """Decorator to handle errors in functions"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (
                ApplicationError,
                BusinessLogicError,
                DatabaseError,
                TelegramAPIError,
                ValidationError,
            ) as e:
                # Find update and context from args
                update = next((arg for arg in args if isinstance(arg, Update)), None)
                context_types = next(
                    (arg for arg in args if isinstance(arg, ContextTypes.DEFAULT_TYPE)),
                    None,
                )
                user_id = (
                    str(update.effective_user.id)
                    if update and update.effective_user
                    else "unknown"
                )

                # Create an ApplicationError
                app_error = ApplicationError(
                    message=str(e),
                    severity=severity,
                    category=error_category,
                    original_error=e,
                    context={"function": func.__name__},
                )

                # Handle the error
                error_handler_instance = ErrorHandler()
                report = ErrorReport(
                    error=app_error,
                    context={"function": func.__name__},
                    user_id=user_id,
                    update=update,
                    context_types=context_types,
                )
                await error_handler_instance.handle_error(report)
                return None

        return wrapper

    return decorator


def get_error_statistics() -> Dict[str, Any]:
    """Get global error statistics"""
    # This is a placeholder. In a real app, you would have a central
    # error handler instance to get stats from.
    return {}


# --- Additional business/domain error subclasses from exceptions.py ---

@dataclass
class OrderError(BusinessLogicError):
    """Order-related business logic errors"""
    pass

@dataclass
class OrderNotFoundError(OrderError):
    order_id: int = -1
    def __post_init__(self):
        self.message = f"Order with ID {self.order_id} not found"
        self.user_message = f"Order with ID {self.order_id} not found"

@dataclass
class OrderStatusError(OrderError):
    pass

@dataclass
class CartError(BusinessLogicError):
    pass

@dataclass
class ProductError(BusinessLogicError):
    pass

@dataclass
class CustomerError(BusinessLogicError):
    pass

@dataclass
class AuthenticationError(ApplicationError):
    error_code: str = "AUTH_ERROR"
    severity: ErrorSeverity = ErrorSeverity.HIGH
    category: ErrorCategory = ErrorCategory.AUTHENTICATION

@dataclass
class RateLimitExceededError(ApplicationError):
    reason: Optional[str] = None
    error_code: str = "RATE_LIMIT_ERROR"
    severity: ErrorSeverity = ErrorSeverity.LOW
    category: ErrorCategory = ErrorCategory.SYSTEM
    def __post_init__(self):
        self.message = f"Rate limit exceeded: {self.reason}" if self.reason else "Rate limit exceeded"
        self.user_message = "Please wait before trying again."

@dataclass
class ConfigurationError(ApplicationError):
    error_code: str = "CONFIG_ERROR"
    severity: ErrorSeverity = ErrorSeverity.HIGH
    category: ErrorCategory = ErrorCategory.SYSTEM

@dataclass
class ExternalServiceError(ApplicationError):
    error_code: str = "EXTERNAL_SERVICE_ERROR"
    severity: ErrorSeverity = ErrorSeverity.HIGH
    category: ErrorCategory = ErrorCategory.EXTERNAL_SERVICE

@dataclass
class TelegramError(ExternalServiceError):
    error_code: str = "TELEGRAM_ERROR"
    category: ErrorCategory = ErrorCategory.TELEGRAM_API

@dataclass
class ProductNotFoundError(ProductError):
    product_name: str = ""
    def __post_init__(self):
        self.message = f"Product not found: {self.product_name}"
        self.user_message = f"Sorry, {self.product_name} is not available right now."

@dataclass
class CartEmptyError(CartError):
    def __post_init__(self):
        self.message = "Cart is empty"
        self.user_message = "Your cart is empty. Please add some items first."

@dataclass
class CustomerNotFoundError(CustomerError):
    user_id: int = -1
    def __post_init__(self):
        self.message = f"Customer not found: {self.user_id}"
        self.user_message = "Customer information not found. Please start again with /start"

@dataclass
class OrderCreationError(DatabaseError):
    reason: str = ""
    def __post_init__(self):
        self.message = f"Order creation failed: {self.reason}"
        self.user_message = "Sorry, we couldn't process your order. Please try again."

@dataclass
class HilbehNotAvailableError(BusinessLogicError):
    def __post_init__(self):
        self.message = "Hilbeh not available today"
        self.user_message = "Hilbeh is only available Wednesday through Friday."

@dataclass
class DatabaseRetryExhaustedError(DatabaseError):
    """Raised when database retry attempts are exhausted"""
    error_code: str = "DB_RETRY_EXHAUSTED"
    severity: ErrorSeverity = ErrorSeverity.CRITICAL
    category: ErrorCategory = ErrorCategory.DATABASE

@dataclass
class DatabaseTimeoutError(DatabaseError):
    """Raised when a database operation times out"""
    error_code: str = "DB_TIMEOUT_ERROR"
    severity: ErrorSeverity = ErrorSeverity.HIGH
    category: ErrorCategory = ErrorCategory.DATABASE

# --- CircuitBreaker from exceptions.py ---

class CircuitBreaker:
    """Simple circuit breaker for external services"""
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    def call(self, func, *args, **kwargs):
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

def retry_on_database_error(max_retries: int = 3, delay: float = 0.5, allowed_exceptions: tuple = (DatabaseError,)):
    """Retry decorator for database operations, DRY and robust."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as exc:
                    last_exc = exc
                    logging.getLogger(__name__).warning(
                        f"DB retry {attempt}/{max_retries} for {func.__name__} due to: {exc}"
                    )
                    time.sleep(delay)
            # If we get here, all retries failed
            raise DatabaseRetryExhaustedError(message=f"All retries failed for {func.__name__}", original_error=last_exc)
        return wrapper
    return decorator

# --- Unified handle_error and error_handler decorator ---

async def handle_error(update: Update, error: Exception, operation: str = "unknown"):
    """Handle errors and send user-friendly messages"""
    try:
        # Get user ID safely
        user_id = "unknown"
        if hasattr(update, 'effective_user') and update.effective_user:
            user_id = update.effective_user.id
        elif hasattr(update, 'callback_query') and update.callback_query:
            user_id = update.callback_query.from_user.id
        elif hasattr(update, 'message') and update.message:
            user_id = update.message.from_user.id

        # Log the error
        logger = logging.getLogger(__name__)
        logger.error(
            "Error in %s for user %s: %s", 
            operation, 
            user_id, 
            str(error)
        )

        # Send user-friendly error message with helpful guidance
        error_message = "❌ Something went wrong. Please try again or contact support if the problem persists."
        
        if hasattr(update, 'callback_query') and update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    error_message,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Back to Menu", callback_data="menu_main")
                    ]])
                )
            except Exception as edit_error:
                logger.error("Failed to edit message: %s", edit_error)
                # Try to send a new message instead
                if hasattr(update.callback_query, 'message') and update.callback_query.message:
                    await update.callback_query.message.reply_text(
                        error_message,
                        parse_mode="HTML"
                    )
        elif hasattr(update, 'message') and update.message:
            await update.message.reply_text(
                error_message,
                parse_mode="HTML"
            )

    except Exception as handler_error:
        logger.error("Error in error handler: %s", handler_error)

def error_handler(operation: str = "unknown"):
    def decorator(func):
        async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            try:
                return await func(update, context, *args, **kwargs)
            except Exception as error:
                await handle_error(update, error, operation=operation)
        return wrapper
    return decorator
