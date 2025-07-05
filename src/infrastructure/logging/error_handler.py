"""
Enhanced Error Handling System

Provides comprehensive error handling, logging, and monitoring capabilities
for the Samna Salta bot application.
"""

import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Dict, Optional

from telegram import Update
from telegram.ext import ContextTypes


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

    def report_error(self, report: ErrorReport) -> str:
        """Report an error with full context and metrics"""

        # Generate unique error ID
        error_id = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(report.error)}"

        # Extract error details
        if isinstance(report.error, ApplicationError):
            error_details = {
                "error_id": error_id,
                "error_message": report.error.message,
                "error_code": report.error.error_code,
                "severity": report.error.severity.value,
                "category": report.error.category.value,
                "context": report.error.context,
                "timestamp": report.error.timestamp.isoformat(),
                "user_id": report.user_id,
                "additional_context": report.context,
            }
        else:
            error_details = {
                "error_id": error_id,
                "error_message": str(report.error),
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
        user_message = "An unexpected error occurred. Please try again later."
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


# Final newline
