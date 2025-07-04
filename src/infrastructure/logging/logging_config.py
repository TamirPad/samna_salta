"""
Production-ready logging configuration
"""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from ..configuration.config import get_config


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Create log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                              'pathname', 'filename', 'module', 'lineno', 
                              'funcName', 'created', 'msecs', 'relativeCreated',
                              'thread', 'threadName', 'processName', 'process',
                              'exc_info', 'exc_text', 'stack_info']:
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
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.INFO)
            root_logger.addHandler(console_handler)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "samna_salta.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(JSONFormatter())
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        
        # Error file handler
        error_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "errors.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        error_handler.setFormatter(JSONFormatter())
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)
        
        # Security events handler
        security_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "security.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=10,
            encoding='utf-8'
        )
        security_handler.setFormatter(JSONFormatter())
        security_handler.setLevel(logging.WARNING)
        
        # Add filter for security events
        class SecurityFilter(logging.Filter):
            def filter(self, record):
                return 'SECURITY EVENT' in record.getMessage()
        
        security_handler.addFilter(SecurityFilter())
        root_logger.addHandler(security_handler)
        
        # Performance handler for slow operations
        performance_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "performance.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        performance_handler.setFormatter(JSONFormatter())
        performance_handler.setLevel(logging.INFO)
        
        # Add filter for performance events
        class PerformanceFilter(logging.Filter):
            def filter(self, record):
                return hasattr(record, 'operation_time') or 'performance' in record.getMessage().lower()
        
        performance_handler.addFilter(PerformanceFilter())
        root_logger.addHandler(performance_handler)
        
        # Configure specific loggers
        ProductionLogger._configure_specific_loggers()
        
        logging.info("Logging configured successfully", extra={
            'environment': config.environment,
            'log_level': config.log_level
        })
    
    @staticmethod
    def _configure_specific_loggers():
        """Configure specific loggers for different components"""
        
        # Telegram bot logger
        telegram_logger = logging.getLogger('telegram')
        telegram_logger.setLevel(logging.WARNING)  # Reduce telegram library noise
        
        # HTTP requests logger
        httpx_logger = logging.getLogger('httpx')
        httpx_logger.setLevel(logging.WARNING)
        
        # Database logger
        db_logger = logging.getLogger('sqlalchemy.engine')
        db_logger.setLevel(logging.WARNING)  # Only show warnings and errors
        
        # Application loggers
        app_logger = logging.getLogger('src')
        app_logger.setLevel(logging.INFO)


class PerformanceLogger:
    """Performance monitoring logger"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.logger = logging.getLogger(f"performance.{operation_name}")
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
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
                    'operation_name': self.operation_name,
                    'operation_time': duration,
                    'performance_category': 'slow' if duration > 5.0 else 'normal'
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
                'event_type': 'customer_registration',
                'telegram_id': telegram_id,
                'phone_hash': hash(phone_number) % 10000  # Anonymized phone
            }
        )
    
    @staticmethod
    def log_order_placed(order_id: int, customer_id: int, total_amount: float):
        """Log order placement event"""
        logging.info(
            "Order placed",
            extra={
                'event_type': 'order_placed',
                'order_id': order_id,
                'customer_id': customer_id,
                'total_amount': total_amount
            }
        )
    
    @staticmethod
    def log_admin_action(admin_id: int, action: str, details: Dict[str, Any] = None):
        """Log admin actions"""
        logging.info(
            f"Admin action: {action}",
            extra={
                'event_type': 'admin_action',
                'admin_id': admin_id,
                'action': action,
                'details': details or {}
            }
        ) 