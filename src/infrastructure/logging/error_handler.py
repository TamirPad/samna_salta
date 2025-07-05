"""
Enhanced Error Handling System

Provides comprehensive error handling, logging, and monitoring capabilities
for the Samna Salta bot application.
"""

import logging
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, List
from functools import wraps

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


class ApplicationError(Exception):
    """Base application error with enhanced context"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.category = category
        self.context = context or {}
        self.original_error = original_error
        self.timestamp = datetime.now()


class BusinessLogicError(ApplicationError):
    """Business logic specific errors"""
    
    def __init__(self, message: str, error_code: str = "BUSINESS_ERROR", **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.BUSINESS_LOGIC,
            **kwargs
        )


class DatabaseError(ApplicationError):
    """Database operation errors"""
    
    def __init__(self, message: str, error_code: str = "DB_ERROR", **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATABASE,
            **kwargs
        )


class TelegramAPIError(ApplicationError):
    """Telegram API related errors"""
    
    def __init__(self, message: str, error_code: str = "TELEGRAM_ERROR", **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.TELEGRAM_API,
            **kwargs
        )


class ValidationError(ApplicationError):
    """Input validation errors"""
    
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR", **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            **kwargs
        )


class ErrorReporter:
    """Enhanced error reporting with metrics and alerts"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_metrics = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recent_errors": []
        }
    
    def report_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Report an error with full context and metrics"""
        
        # Generate unique error ID
        error_id = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(error)}"
        
        # Extract error details
        if isinstance(error, ApplicationError):
            error_details = {
                "error_id": error_id,
                "error_message": error.message,
                "error_code": error.error_code,
                "severity": error.severity.value,
                "category": error.category.value,
                "context": error.context,
                "timestamp": error.timestamp.isoformat(),
                "user_id": user_id,
                "additional_context": context
            }
        else:
            error_details = {
                "error_id": error_id,
                "error_message": str(error),
                "error_code": "UNKNOWN",
                "severity": ErrorSeverity.MEDIUM.value,
                "category": ErrorCategory.SYSTEM.value,
                "context": context or {},
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "traceback": traceback.format_exc()
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
            f"ERROR [{error_details['error_id']}] "
            f"{error_details['error_message']} "
            f"(Code: {error_details['error_code']}, "
            f"Category: {error_details['category']}, "
            f"User: {error_details.get('user_id', 'N/A')})"
        )
        
        if severity == ErrorSeverity.CRITICAL.value:
            self.logger.critical(log_message, extra=error_details)
        elif severity == ErrorSeverity.HIGH.value:
            self.logger.error(log_message, extra=error_details)
        elif severity == ErrorSeverity.MEDIUM.value:
            self.logger.warning(log_message, extra=error_details)
        else:
            self.logger.info(log_message, extra=error_details)
    
    def _handle_critical_error(self, error_details: Dict[str, Any]):
        """Handle critical errors that need immediate attention"""
        self.logger.critical(
            f"🚨 CRITICAL ERROR DETECTED: {error_details['error_id']} 🚨",
            extra=error_details
        )
        
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
            "critical_errors_last_24h": len([
                e for e in self.error_metrics["recent_errors"]
                if e.get("severity") == ErrorSeverity.CRITICAL.value
            ])
        }


class ErrorHandler:
    """Global error handler with recovery strategies"""
    
    def __init__(self):
        self.reporter = ErrorReporter()
        self.recovery_strategies = {
            ErrorCategory.DATABASE: self._recover_database_error,
            ErrorCategory.TELEGRAM_API: self._recover_telegram_error,
            ErrorCategory.BUSINESS_LOGIC: self._recover_business_error,
        }
    
    async def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        update: Optional[Update] = None,
        context_types: Optional[ContextTypes.DEFAULT_TYPE] = None
    ) -> bool:
        """Handle error with recovery strategies"""
        
        # Report the error
        error_id = self.reporter.report_error(error, context, user_id)
        
        # Try recovery strategies
        if isinstance(error, ApplicationError):
            recovery_strategy = self.recovery_strategies.get(error.category)
            if recovery_strategy:
                try:
                    await recovery_strategy(error, update, context_types)
                    return True
                except Exception as recovery_error:
                    self.reporter.report_error(
                        recovery_error,
                        {"original_error_id": error_id},
                        user_id
                    )
        
        # Default user-facing error message
        if update and context_types:
            await self._send_user_error_message(error, update, context_types)
        
        return False
    
    async def _recover_database_error(
        self,
        error: ApplicationError,
        update: Optional[Update],
        context: Optional[ContextTypes.DEFAULT_TYPE]
    ):
        """Attempt to recover from database errors"""
        # Could implement database reconnection, retry logic, etc.
        pass
    
    async def _recover_telegram_error(
        self,
        error: ApplicationError,
        update: Optional[Update],
        context: Optional[ContextTypes.DEFAULT_TYPE]
    ):
        """Attempt to recover from Telegram API errors"""
        # Could implement retry with exponential backoff
        pass
    
    async def _recover_business_error(
        self,
        error: ApplicationError,
        update: Optional[Update],
        context: Optional[ContextTypes.DEFAULT_TYPE]
    ):
        """Attempt to recover from business logic errors"""
        # Could implement fallback business logic
        pass
    
    async def _send_user_error_message(
        self,
        error: Exception,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Send user-friendly error message"""
        if isinstance(error, ApplicationError):
            if error.severity == ErrorSeverity.LOW:
                message = f"⚠️ {error.message}"
            elif error.severity in [ErrorSeverity.MEDIUM, ErrorSeverity.HIGH]:
                message = "😔 משהו השתבש. אנא נסה שוב או פנה לתמיכה."
            else:
                message = "🚨 שגיאה קריטית. אנא פנה לתמיכה מיידית."
        else:
            message = "😔 משהו השתבש. אנא נסה שוב."
        
        try:
            if update.message:
                await update.message.reply_text(message)
            elif update.callback_query:
                await update.callback_query.answer(message, show_alert=True)
        except Exception:
            # Error sending error message - log it
            pass


# Global error handler instance
error_handler = ErrorHandler()


def handle_errors(
    error_category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
):
    """Decorator for automatic error handling"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Try to extract Update and Context from args
                update = None
                context = None
                user_id = None
                
                for arg in args:
                    if isinstance(arg, Update):
                        update = arg
                        if hasattr(arg, 'effective_user') and arg.effective_user:
                            user_id = str(arg.effective_user.id)
                    elif hasattr(arg, 'bot'):  # ContextTypes
                        context = arg
                
                # Convert to ApplicationError if needed
                if not isinstance(e, ApplicationError):
                    e = ApplicationError(
                        message=str(e),
                        error_code="HANDLER_ERROR",
                        severity=severity,
                        category=error_category,
                        original_error=e
                    )
                
                await error_handler.handle_error(
                    e,
                    context={"function": func.__name__},
                    user_id=user_id,
                    update=update,
                    context_types=context
                )
                
                raise  # Re-raise the error
        return wrapper
    return decorator


def get_error_statistics() -> Dict[str, Any]:
    """Get current error statistics"""
    return error_handler.reporter.get_error_statistics() 