"""
Production-ready logging configuration with enhanced QA monitoring
"""

import json
import logging
import logging.handlers
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from ..configuration.config import get_config


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        # Create log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in [
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                ]:
                    log_entry[key] = value

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class QAEnhancedFormatter(logging.Formatter):
    """Enhanced formatter for QA analysis with additional context"""

    def format(self, record: logging.LogRecord) -> str:
        # Create enhanced log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process,
            "created": record.created,
        }

        # Add QA-specific fields
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "operation_time"):
            log_entry["operation_time"] = record.operation_time
        if hasattr(record, "memory_usage"):
            log_entry["memory_usage"] = record.memory_usage
        if hasattr(record, "query_count"):
            log_entry["query_count"] = record.query_count
        if hasattr(record, "cache_hit"):
            log_entry["cache_hit"] = record.cache_hit
        if hasattr(record, "response_size"):
            log_entry["response_size"] = record.response_size

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            exc_info = record.exc_info[0]
            if exc_info:
                log_entry["exception_type"] = exc_info.__name__

        # Add extra fields
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in [
                    "name", "msg", "args", "levelname", "levelno",
                    "pathname", "filename", "module", "lineno",
                    "funcName", "created", "msecs", "relativeCreated",
                    "thread", "threadName", "processName", "process",
                    "exc_info", "exc_text", "stack_info", "user_id",
                    "operation_time", "memory_usage", "query_count",
                    "cache_hit", "response_size"
                ]:
                    if not key.startswith('_'):
                        log_entry[key] = value

        return json.dumps(log_entry, default=str, ensure_ascii=False)


@dataclass
class ProductionLogger:
    """Production logging setup with file rotation and structured logging"""

    @staticmethod
    def setup_logging():
        """Setup production logging configuration"""
        config = get_config()

        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(config.log_level.upper())  # pylint: disable=no-member

        # Clear existing handlers
        root_logger.handlers.clear()

        # Console handler for development
        if config.environment == "development":
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.DEBUG)
            root_logger.addHandler(console_handler)

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "samna_salta.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(QAEnhancedFormatter())
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)

        # Error file handler
        error_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "errors.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding="utf-8",
        )
        error_handler.setFormatter(QAEnhancedFormatter())
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)

        # Security events handler
        security_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "security.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=10,
            encoding="utf-8",
        )
        security_handler.setFormatter(QAEnhancedFormatter())
        security_handler.setLevel(logging.WARNING)

        # Add filter for security events
        @dataclass
        class SecurityFilter(logging.Filter):
            """Filter for security events"""
            def filter(self, record):
                return "SECURITY EVENT" in record.getMessage()

            def __repr__(self):
                return "SecurityFilter()"

        security_handler.addFilter(SecurityFilter())
        root_logger.addHandler(security_handler)

        # Performance handler for slow operations
        performance_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "performance.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,
            encoding="utf-8",
        )
        performance_handler.setFormatter(QAEnhancedFormatter())
        performance_handler.setLevel(logging.INFO)

        # Add filter for performance events
        @dataclass
        class PerformanceFilter(logging.Filter):
            """Filter for performance events"""
            def filter(self, record):
                return (
                    hasattr(record, "operation_time")
                    or "performance" in record.getMessage().lower()
                    or hasattr(record, "memory_usage")
                    or hasattr(record, "query_count")
                )

            def __repr__(self):
                return "PerformanceFilter()"

        performance_handler.addFilter(PerformanceFilter())
        root_logger.addHandler(performance_handler)

        # QA-specific handler for detailed analysis
        qa_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "qa_analysis.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,
            encoding="utf-8",
        )
        qa_handler.setFormatter(QAEnhancedFormatter())
        qa_handler.setLevel(logging.DEBUG)

        # Add filter for QA events
        @dataclass
        class QAFilter(logging.Filter):
            """Filter for QA events"""
            def filter(self, record):
                return (
                    hasattr(record, "user_id")
                    or hasattr(record, "operation_time")
                    or "handler" in record.getMessage().lower()
                    or "use_case" in record.getMessage().lower()
                    or "repository" in record.getMessage().lower()
                )

            def __repr__(self):
                return "QAFilter()"

        qa_handler.addFilter(QAFilter())
        root_logger.addHandler(qa_handler)

        # Configure specific loggers
        ProductionLogger._configure_specific_loggers()

        logger = logging.getLogger(__name__)
        logger.info(
            "Enhanced QA logging configured successfully",
            extra={
                "environment": config.environment,
                "log_level": config.log_level,
                "qa_enhanced": True
            },
        )

    @staticmethod
    def _configure_specific_loggers():
        """Configure specific loggers for different components"""

        # Telegram bot logger
        telegram_logger = logging.getLogger("telegram")
        telegram_logger.setLevel(logging.INFO)

        # Database logger
        db_logger = logging.getLogger("sqlalchemy")
        db_logger.setLevel(logging.WARNING)

        # Application-specific loggers
        logging.getLogger("app.use_cases").setLevel(logging.DEBUG)
        logging.getLogger("app.repositories").setLevel(logging.DEBUG)
        logging.getLogger("app.handlers").setLevel(logging.DEBUG)


@dataclass
class PerformanceLogger:
    """Context manager for logging performance of code blocks"""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.logger = logging.getLogger("performance")

    def __enter__(self):
        self.start_time = datetime.utcnow()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.utcnow() - self.start_time).total_seconds()
            self.logger.info(
                "Performance metric",
                extra={
                    "operation_name": self.operation_name,
                    "duration_seconds": duration,
                    "success": exc_type is None,
                },
            )


@dataclass
class AuditLogger:
    """Logger for critical audit events"""

    @staticmethod
    def log_customer_registration(telegram_id: int, phone_number: str):
        """Log customer registration event"""
        logger = logging.getLogger("security")
        logger.warning(
            "SECURITY EVENT: New customer registered",
            extra={"telegram_id": telegram_id, "phone_number": phone_number},
        )

    @staticmethod
    def log_order_placed(order_id: int, customer_id: int, total_amount: float):
        """Log order placement event"""
        logger = logging.getLogger("security")
        logger.warning(
            "SECURITY EVENT: New order placed",
            extra={
                "order_id": order_id,
                "customer_id": customer_id,
                "total_amount": total_amount,
            },
        )

    @staticmethod
    def log_admin_action(admin_id: int,
                         action: str,
                         details: Dict[str, Any] = None):
        """Log administrative action"""
        logger = logging.getLogger("security")
        logger.warning(
            "SECURITY EVENT: Admin action - %s",
            action,
            extra={"admin_id": admin_id, "details": details or {}},
        )


@dataclass
class QALogger:
    """Logger for detailed QA and business process analysis"""

    @staticmethod
    def log_user_action(user_id: int,
                        action: str,
                        details: Dict[str, Any] = None):
        """Log a specific user action for QA analysis"""
        logger = logging.getLogger("qa_analysis")
        logger.info(
            "User action: %s",
            action,
            extra={"user_id": user_id, "action": action,
                   "details": details or {}},
        )

    @staticmethod
    def log_performance_metric(operation: str,
                               duration: float,
                               details: Dict[str, Any] = None):
        """Log a performance metric for QA analysis"""
        logger = logging.getLogger("qa_analysis")
        logger.debug(
            "Performance: %s took %.4fs",
            operation,
            duration,
            extra={
                "operation": operation,
                "duration": duration,
                "details": details or {},
            },
        )

    @staticmethod
    def log_business_event(event_type: str, details: Dict[str, Any] = None):
        """Log a significant business event"""
        logger = logging.getLogger("qa_analysis")
        logger.info(
            "Business event: %s",
            event_type,
            extra={"event_type": event_type, "details": details or {}},
        )

    @staticmethod
    def log_error_context(error: Exception, context: Dict[str, Any] = None):
        """Log detailed context for an error"""
        logger = logging.getLogger("qa_analysis")
        logger.error(
            "Error context: %s",
            error,
            extra={"error": str(error), "context": context or {}},
            exc_info=True,
        )
