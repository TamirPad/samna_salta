"""
Production-ready logging configuration with enhanced QA monitoring
"""

import json
import logging
import logging.handlers
import sys
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
            log_entry["exception_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None

        # Add extra fields
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in [
                    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
                    "module", "lineno", "funcName", "created", "msecs", "relativeCreated",
                    "thread", "threadName", "processName", "process", "exc_info", "exc_text",
                    "stack_info", "user_id", "operation_time", "memory_usage", "query_count",
                    "cache_hit", "response_size"
                ]:
                    if not key.startswith('_'):
                        log_entry[key] = value

        return json.dumps(log_entry, default=str, ensure_ascii=False)


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
        root_logger.setLevel(getattr(logging, config.log_level.upper()))

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
        class SecurityFilter(logging.Filter):
            def filter(self, record):
                return "SECURITY EVENT" in record.getMessage()

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
        class PerformanceFilter(logging.Filter):
            def filter(self, record):
                return (
                    hasattr(record, "operation_time")
                    or "performance" in record.getMessage().lower()
                    or hasattr(record, "memory_usage")
                    or hasattr(record, "query_count")
                )

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
        class QAFilter(logging.Filter):
            def filter(self, record):
                return (
                    hasattr(record, "user_id")
                    or hasattr(record, "operation_time")
                    or "handler" in record.getMessage().lower()
                    or "use_case" in record.getMessage().lower()
                    or "repository" in record.getMessage().lower()
                )

        qa_handler.addFilter(QAFilter())
        root_logger.addHandler(qa_handler)

        # Configure specific loggers
        ProductionLogger._configure_specific_loggers()

        logging.info(
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
        telegram_logger.setLevel(logging.INFO)  # More verbose for QA

        # HTTP requests logger
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.INFO)  # More verbose for QA

        # Database logger
        db_logger = logging.getLogger("sqlalchemy.engine")
        db_logger.setLevel(logging.INFO)  # More verbose for QA

        # Application loggers
        app_logger = logging.getLogger("src")
        app_logger.setLevel(logging.DEBUG)  # Most verbose for QA


class PerformanceLogger:
    """Performance monitoring logger with enhanced QA metrics"""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.logger = logging.getLogger(f"performance.{operation_name}")

    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.info(f"Starting operation: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.utcnow() - self.start_time).total_seconds()

            log_level = logging.INFO
            if duration > 5.0:  # Slow operation
                log_level = logging.WARNING

            self.logger.log(
                log_level,
                f"Operation completed: {self.operation_name}",
                extra={
                    "operation_time": duration,
                    "slow_operation": duration > 5.0,
                    "operation_name": self.operation_name,
                    "success": exc_type is None,
                    "exception_type": exc_type.__name__ if exc_type else None
                }
            )


class AuditLogger:
    """Audit logger for tracking important business events"""

    @staticmethod
    def log_customer_registration(telegram_id: int, phone_number: str):
        """Log customer registration event"""
        logging.info(
            "Customer registered",
            extra={
                "event_type": "customer_registration",
                "telegram_id": telegram_id,
                "phone_hash": hash(phone_number) % 10000,  # Anonymized phone
            },
        )

    @staticmethod
    def log_order_placed(order_id: int, customer_id: int, total_amount: float):
        """Log order placement event"""
        logging.info(
            "Order placed",
            extra={
                "event_type": "order_placed",
                "order_id": order_id,
                "customer_id": customer_id,
                "total_amount": total_amount,
            },
        )

    @staticmethod
    def log_admin_action(admin_id: int, action: str, details: Dict[str, Any] = None):
        """Log admin actions"""
        logging.info(
            f"Admin action: {action}",
            extra={
                "event_type": "admin_action",
                "admin_id": admin_id,
                "action": action,
                "details": details or {},
            },
        )


class QALogger:
    """QA-specific logging utilities"""

    @staticmethod
    def log_user_action(user_id: int, action: str, details: Dict[str, Any] = None):
        """Log user actions for QA analysis"""
        logger = logging.getLogger("qa.user_actions")
        logger.info(
            f"User action: {action}",
            extra={
                "user_id": user_id,
                "action": action,
                "details": details or {},
                "qa_event": "user_action"
            }
        )

    @staticmethod
    def log_performance_metric(operation: str, duration: float, details: Dict[str, Any] = None):
        """Log performance metrics for QA analysis"""
        logger = logging.getLogger("qa.performance")
        logger.info(
            f"Performance metric: {operation}",
            extra={
                "operation": operation,
                "operation_time": duration,
                "details": details or {},
                "qa_event": "performance_metric"
            }
        )

    @staticmethod
    def log_business_event(event_type: str, details: Dict[str, Any] = None):
        """Log business events for QA analysis"""
        logger = logging.getLogger("qa.business")
        logger.info(
            f"Business event: {event_type}",
            extra={
                "event_type": event_type,
                "details": details or {},
                "qa_event": "business_event"
            }
        )

    @staticmethod
    def log_error_context(error: Exception, context: Dict[str, Any] = None):
        """Log error context for QA analysis"""
        logger = logging.getLogger("qa.errors")
        logger.error(
            f"Error occurred: {str(error)}",
            extra={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {},
                "qa_event": "error_context"
            },
            exc_info=True
        )
