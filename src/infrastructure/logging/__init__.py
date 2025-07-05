"""
Logging Infrastructure

Enhanced logging system with structured logging, error handling, and performance monitoring.
"""

from .error_handler import (
    ApplicationError,
    BusinessLogicError,
    DatabaseError,
    ErrorCategory,
    ErrorSeverity,
    TelegramAPIError,
    ValidationError,
    error_handler,
    get_error_statistics,
    handle_errors,
)
from .logger_config import (
    get_performance_metrics,
    get_structured_logger,
    log_performance,
    setup_logging,
)

__all__ = [
    "ApplicationError",
    "BusinessLogicError",
    "DatabaseError",
    "ErrorCategory",
    "ErrorSeverity",
    "TelegramAPIError",
    "ValidationError",
    "error_handler",
    "get_error_statistics",
    "handle_errors",
    "get_performance_metrics",
    "get_structured_logger",
    "log_performance",
    "setup_logging",
]
