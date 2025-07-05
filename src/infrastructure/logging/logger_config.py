"""
Enhanced Logging Configuration

Provides structured logging with multiple handlers, performance monitoring,
and production-ready logging capabilities.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import json
import structlog


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        record.name = f"\033[94m{record.name}\033[0m"  # Blue
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter with enhanced context"""
    
    def format(self, record):
        """Format the record as JSON"""
        log_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'process_id': os.getpid(),
            'thread_id': record.thread,
        }
        
        # Add custom context if available
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        if hasattr(record, 'error_id'):
            log_record['error_id'] = record.error_id
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        
        return json.dumps(log_record)


class PerformanceLogger:
    """Performance monitoring logger"""
    
    def __init__(self, name: str = "performance"):
        self.logger = logging.getLogger(name)
        self.metrics = {
            'total_requests': 0,
            'slow_requests': 0,
            'error_requests': 0,
            'avg_response_time': 0.0
        }
    
    def log_request(
        self,
        method: str,
        endpoint: str,
        response_time: float,
        status: str = "success",
        user_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """Log a request with performance metrics"""
        
        # Update metrics
        self.metrics['total_requests'] += 1
        
        if response_time > 2.0:  # Slow request threshold
            self.metrics['slow_requests'] += 1
        
        if status != "success":
            self.metrics['error_requests'] += 1
        
        # Calculate running average
        current_avg = self.metrics['avg_response_time']
        total_requests = self.metrics['total_requests']
        self.metrics['avg_response_time'] = (
            (current_avg * (total_requests - 1) + response_time) / total_requests
        )
        
        # Log the request
        log_data = {
            'method': method,
            'endpoint': endpoint,
            'response_time': response_time,
            'status': status,
            'user_id': user_id,
            **(extra_data or {})
        }
        
        if response_time > 2.0:
            self.logger.warning(
                f"Slow request: {method} {endpoint} took {response_time:.2f}s",
                extra=log_data
            )
        else:
            self.logger.info(
                f"Request: {method} {endpoint} ({response_time:.2f}s)",
                extra=log_data
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            **self.metrics,
            'slow_request_ratio': (
                self.metrics['slow_requests'] / max(1, self.metrics['total_requests'])
            ),
            'error_rate': (
                self.metrics['error_requests'] / max(1, self.metrics['total_requests'])
            )
        }


class LoggingConfig:
    """Enhanced logging configuration"""
    
    def __init__(
        self,
        log_level: str = "INFO",
        log_dir: str = "logs",
        enable_console: bool = True,
        enable_file: bool = True,
        enable_json: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        self.log_level = log_level
        self.log_dir = Path(log_dir)
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_json = enable_json
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        
        # Create log directory
        self.log_dir.mkdir(exist_ok=True)
        
        # Configure structlog
        self._configure_structlog()
    
    def _configure_structlog(self):
        """Configure structlog for structured logging"""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    def setup_logging(self):
        """Setup comprehensive logging configuration"""
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.log_level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.log_level.upper()))
            
            console_formatter = ColoredFormatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # File handlers
        if self.enable_file:
            # Main application log
            app_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / 'samna_salta.log',
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            app_handler.setLevel(logging.INFO)
            app_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            app_handler.setFormatter(app_formatter)
            root_logger.addHandler(app_handler)
            
            # Error log
            error_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / 'errors.log',
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(app_formatter)
            root_logger.addHandler(error_handler)
            
            # Performance log
            performance_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / 'performance.log',
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            performance_handler.setLevel(logging.INFO)
            performance_logger = logging.getLogger('performance')
            performance_logger.addHandler(performance_handler)
            performance_logger.setLevel(logging.INFO)
            
            # Security log
            security_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / 'security.log',
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            security_handler.setLevel(logging.WARNING)
            security_logger = logging.getLogger('security')
            security_logger.addHandler(security_handler)
            security_logger.setLevel(logging.WARNING)
        
        # JSON structured log
        if self.enable_json:
            json_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / 'samna_salta.json',
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            json_handler.setLevel(logging.INFO)
            json_formatter = StructuredFormatter(
                fmt='%(timestamp)s %(level)s %(logger)s %(message)s'
            )
            json_handler.setFormatter(json_formatter)
            root_logger.addHandler(json_handler)
        
        # Set specific logger levels
        self._configure_external_loggers()
        
        # Log configuration success
        logger = logging.getLogger(__name__)
        logger.info(
            f"✅ Logging configured successfully - Level: {self.log_level}, "
            f"Console: {self.enable_console}, File: {self.enable_file}, "
            f"JSON: {self.enable_json}"
        )
    
    def _configure_external_loggers(self):
        """Configure external library loggers"""
        # Reduce verbosity of external libraries
        logging.getLogger('telegram').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)


# Global instances
performance_logger = PerformanceLogger()


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_json: bool = True
):
    """Setup application logging"""
    config = LoggingConfig(
        log_level=log_level,
        log_dir=log_dir,
        enable_console=enable_console,
        enable_file=enable_file,
        enable_json=enable_json
    )
    config.setup_logging()
    return config


def get_performance_metrics() -> Dict[str, Any]:
    """Get current performance metrics"""
    return performance_logger.get_metrics()


def log_performance(
    method: str,
    endpoint: str,
    response_time: float,
    status: str = "success",
    user_id: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
):
    """Log performance metrics"""
    performance_logger.log_request(
        method=method,
        endpoint=endpoint,
        response_time=response_time,
        status=status,
        user_id=user_id,
        extra_data=extra_data
    )


def get_structured_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name) 