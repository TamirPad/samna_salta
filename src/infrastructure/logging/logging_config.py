"""
Advanced logging configuration for the Samna Salta bot

Provides comprehensive logging with structured output, performance tracking,
security monitoring, and QA analysis capabilities.
"""

import logging
import logging.handlers
import os
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from pythonjsonlogger import jsonlogger

from src.infrastructure.configuration.config import get_config
from src.infrastructure.utilities.constants import LoggingSettings, FileSettings


@dataclass
class ProductionLogger:
    """Production-ready logging configuration with enhanced QA capabilities"""

    @staticmethod
    def setup_logging():
        """
        Setup comprehensive logging for production use

        Features:
        - Structured JSON logging
        - Performance monitoring
        - Security event tracking
        - QA analysis support
        - Multiple output formats
        """
        config = get_config()

        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, config.log_level.upper()))

        # Clear existing handlers
        root_logger.handlers.clear()

        # Console handler with colored output for development
        if config.environment != "production":
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)

        # Main application log with JSON formatting
        app_handler = logging.handlers.RotatingFileHandler(
            logs_dir / FileSettings.MAIN_LOG_FILE,
            maxBytes=LoggingSettings.MAX_LOG_FILE_SIZE,
            backupCount=LoggingSettings.MAIN_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        app_handler.setFormatter(QAEnhancedFormatter())
        app_handler.setLevel(logging.INFO)
        root_logger.addHandler(app_handler)

        # Error-only log for critical issues
        error_handler = logging.handlers.RotatingFileHandler(
            logs_dir / FileSettings.ERROR_LOG_FILE,
            maxBytes=LoggingSettings.MAX_LOG_FILE_SIZE,
            backupCount=LoggingSettings.ERROR_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        error_handler.setFormatter(QAEnhancedFormatter())
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)

        # Security events handler
        security_handler = logging.handlers.RotatingFileHandler(
            logs_dir / FileSettings.SECURITY_LOG_FILE,
            maxBytes=LoggingSettings.SECURITY_LOG_FILE_SIZE,
            backupCount=LoggingSettings.SECURITY_LOG_BACKUP_COUNT,
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
            logs_dir / FileSettings.PERFORMANCE_LOG_FILE,
            maxBytes=LoggingSettings.PERFORMANCE_LOG_FILE_SIZE,
            backupCount=LoggingSettings.PERFORMANCE_LOG_BACKUP_COUNT,
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
            logs_dir / FileSettings.QA_ANALYSIS_LOG_FILE,
            maxBytes=LoggingSettings.QA_LOG_FILE_SIZE,
            backupCount=LoggingSettings.QA_LOG_BACKUP_COUNT,
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
                "qa_enhanced": True,
            },
        )

    @staticmethod
    def _configure_specific_loggers():
        """Configure specific loggers for different components"""
        # SQLAlchemy logging for database monitoring
        db_logger = logging.getLogger("sqlalchemy.engine")
        db_logger.setLevel(logging.WARNING)

        # Telegram bot library logging
        tg_logger = logging.getLogger("telegram")
        tg_logger.setLevel(logging.WARNING)

        # HTTP requests logging
        http_logger = logging.getLogger("urllib3")
        http_logger.setLevel(logging.WARNING)


class QAEnhancedFormatter(jsonlogger.JsonFormatter):
    """Enhanced JSON formatter with QA-specific fields"""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record["timestamp"] = datetime.utcnow().isoformat()

        # Add level name
        log_record["level"] = record.levelname

        # Add logger name
        log_record["logger"] = record.name

        # Add thread info for debugging
        log_record["thread_id"] = threading.current_thread().ident
        log_record["thread_name"] = threading.current_thread().name

        # Add process info
        log_record["process_id"] = os.getpid()

        # QA-specific enhancements
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id

        if hasattr(record, "operation_time"):
            log_record["operation_time_ms"] = record.operation_time

        if hasattr(record, "memory_usage"):
            log_record["memory_usage_mb"] = record.memory_usage

        if hasattr(record, "query_count"):
            log_record["db_query_count"] = record.query_count


# Context managers for enhanced logging
class PerformanceLogger:
    """Context manager for performance logging"""

    def __init__(self, operation_name: str, logger: Optional[logging.Logger] = None, details: Optional[Dict[str, Any]] = None):
        self.operation_name = operation_name
        self.logger = logger or logging.getLogger(__name__)
        self.details = details or {}
        self.start_time = 0

    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(
            f"Starting operation: {self.operation_name}",
            extra={"operation": self.operation_name, **self.details},
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000  # Convert to milliseconds
        
        if exc_type is None:
            self.logger.info(
                f"Completed operation: {self.operation_name}",
                extra={
                    "operation": self.operation_name,
                    "operation_time": duration,
                    "success": True,
                    **self.details,
                },
            )
        else:
            self.logger.error(
                f"Failed operation: {self.operation_name}",
                extra={
                    "operation": self.operation_name,
                    "operation_time": duration,
                    "success": False,
                    "error_type": exc_type.__name__ if exc_type else None,
                    "error_message": str(exc_val) if exc_val else None,
                    **self.details,
                },
                exc_info=True,
            )


class SecurityLogger:
    """Enhanced security event logging"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def log_suspicious_activity(self, user_id: int, activity: str, details: Optional[Dict[str, Any]] = None):
        """Log suspicious user activity"""
        self.logger.warning(
            f"SECURITY EVENT: Suspicious activity detected",
            extra={
                "user_id": user_id,
                "activity": activity,
                "security_event": True,
                **(details or {}),
            },
        )

    def log_access_attempt(self, user_id: int, resource: str, success: bool, context: Optional[Dict[str, Any]] = None):
        """Log access attempts to protected resources"""
        level = logging.INFO if success else logging.WARNING
        message = f"SECURITY EVENT: Access {'granted' if success else 'denied'} to {resource}"
        
        self.logger.log(
            level,
            message,
            extra={
                "user_id": user_id,
                "resource": resource,
                "access_granted": success,
                "security_event": True,
                **(context or {}),
            },
        )

    def log_rate_limit_exceeded(self, user_id: int, endpoint: str, context: Optional[Dict[str, Any]] = None):
        """Log rate limit violations"""
        self.logger.warning(
            f"SECURITY EVENT: Rate limit exceeded for {endpoint}",
            extra={
                "user_id": user_id,
                "endpoint": endpoint,
                "rate_limit_exceeded": True,
                "security_event": True,
                **(context or {}),
            },
        )


# Global instances for easy access
performance_logger = PerformanceLogger
security_logger = SecurityLogger()
