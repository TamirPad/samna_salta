"""
Application constants for the Samna Salta bot

Centralizes all magic numbers and hard-coded values to improve maintainability
and follow the "Avoid magic numbers and hard-coded strings" principle.
"""

from typing import Final


# Application retry and timeout settings
class RetrySettings:
    """Configuration for retry logic and timeouts"""

    MAX_RETRIES: Final[int] = 3
    RETRY_DELAY_SECONDS: Final[int] = 30
    CONFLICT_RETRY_DELAY_SECONDS: Final[int] = 30
    CONNECTION_TIMEOUT_SECONDS: Final[int] = 60


# Database configuration constants
class DatabaseSettings:
    """Database connection and pool configuration"""

    DEFAULT_POOL_SIZE: Final[int] = 10
    MAX_POOL_OVERFLOW: Final[int] = 20
    POOL_RECYCLE_SECONDS: Final[int] = 3600  # 1 hour

    # Production settings
    PRODUCTION_POOL_SIZE: Final[int] = 20
    PRODUCTION_MAX_OVERFLOW: Final[int] = 30

    # Development settings
    DEVELOPMENT_POOL_SIZE: Final[int] = 5
    DEVELOPMENT_MAX_OVERFLOW: Final[int] = 10


# Logging configuration constants
class LoggingSettings:
    """Logging file sizes and rotation settings"""

    MAX_LOG_FILE_SIZE: Final[int] = 10 * 1024 * 1024  # 10MB
    SECURITY_LOG_FILE_SIZE: Final[int] = 5 * 1024 * 1024  # 5MB
    PERFORMANCE_LOG_FILE_SIZE: Final[int] = 5 * 1024 * 1024  # 5MB
    QA_LOG_FILE_SIZE: Final[int] = 5 * 1024 * 1024  # 5MB

    # Backup counts
    MAIN_LOG_BACKUP_COUNT: Final[int] = 10
    ERROR_LOG_BACKUP_COUNT: Final[int] = 10
    SECURITY_LOG_BACKUP_COUNT: Final[int] = 10
    PERFORMANCE_LOG_BACKUP_COUNT: Final[int] = 5
    QA_LOG_BACKUP_COUNT: Final[int] = 5


# Cache configuration constants
class CacheSettings:
    """Cache TTL and timeout settings"""

    PRODUCTS_CACHE_TTL_SECONDS: Final[int] = 600  # 10 minutes
    CUSTOMERS_CACHE_TTL_SECONDS: Final[int] = 300  # 5 minutes
    ORDERS_CACHE_TTL_SECONDS: Final[int] = 180  # 3 minutes
    GENERAL_CACHE_TTL_SECONDS: Final[int] = 300  # 5 minutes


# Performance monitoring constants
class PerformanceSettings:
    """Performance thresholds and monitoring settings"""

    SLOW_QUERY_THRESHOLD_MS: Final[int] = 1000
    MEMORY_WARNING_THRESHOLD_MB: Final[int] = 100
    HIGH_EXAMINATION_RATIO_THRESHOLD: Final[int] = 10

    # Query optimization thresholds
    PERFORMANCE_IMPROVEMENT_LOW: Final[str] = "10-30% performance improvement"
    PERFORMANCE_IMPROVEMENT_MEDIUM: Final[str] = "20-50% performance improvement"
    PERFORMANCE_IMPROVEMENT_HIGH: Final[str] = "30-70% performance improvement"


# Error codes and messages
class ErrorCodes:
    """Standardized error codes and messages"""

    GENERAL_ERROR: Final[str] = "GENERAL_ERROR"
    DATABASE_ERROR: Final[str] = "DATABASE_ERROR"
    VALIDATION_ERROR: Final[str] = "VALIDATION_ERROR"
    BUSINESS_ERROR: Final[str] = "BUSINESS_ERROR"
    AUTHENTICATION_ERROR: Final[str] = "AUTHENTICATION_ERROR"
    RATE_LIMIT_ERROR: Final[str] = "RATE_LIMIT_ERROR"

    # User-friendly messages
    GENERIC_ERROR_MESSAGE: Final[str] = "Something went wrong. Please try again."
    DATABASE_ERROR_MESSAGE: Final[
        str
    ] = "Sorry, there was a problem with our system. Please try again in a moment."
    VALIDATION_ERROR_MESSAGE: Final[str] = "Please check your input and try again."
    RATE_LIMIT_MESSAGE: Final[str] = "Please wait a moment before trying again."


# File and directory constants
class FileSettings:
    """File paths and directory settings"""

    LOGS_DIRECTORY: Final[str] = "logs"
    DATA_DIRECTORY: Final[str] = "data"
    DEFAULT_DATABASE_PATH: Final[str] = "postgresql://postgres:password@localhost:5432/samna_salta"

    # Log file names
    MAIN_LOG_FILE: Final[str] = "app.log"
    ERROR_LOG_FILE: Final[str] = "errors.log"
    SECURITY_LOG_FILE: Final[str] = "security.log"
    PERFORMANCE_LOG_FILE: Final[str] = "performance.log"
    QA_ANALYSIS_LOG_FILE: Final[str] = "qa_analysis.log"


# Telegram bot constants
class TelegramSettings:
    """Telegram bot specific constants"""

    MAX_MESSAGE_LENGTH: Final[int] = 4096
    MAX_CAPTION_LENGTH: Final[int] = 1024
    CALLBACK_DATA_MAX_LENGTH: Final[int] = 64

    # Update types
    ALLOWED_UPDATE_TYPES: Final[list] = ["message", "callback_query"]

    # Inline keyboard limits
    MAX_BUTTONS_PER_ROW: Final[int] = 8
    MAX_ROWS_PER_KEYBOARD: Final[int] = 100




# Callback data patterns for menu interactions
class CallbackPatterns:
    """Callback data patterns for menu interactions"""
    
    # Menu patterns
    MENU_PATTERNS: Final[dict[str, str]] = {
        "main": "menu_main",
        "kubaneh": "menu_kubaneh",
        "samneh": "menu_samneh",
        "red_bisbas": "menu_red_bisbas",
        "hilbeh": "menu_hilbeh",
        "hawaij_soup": "menu_hawaij_soup",
        "hawaij_coffee": "menu_hawaij_coffee",
        "white_coffee": "menu_white_coffee",
    }
    
    # Add to cart patterns
    ADD_PREFIX: Final[str] = "add_"
    
    # Product type patterns
    KUBANEH_PREFIX: Final[str] = "kubaneh_"
    SAMNEH_PREFIX: Final[str] = "samneh_"
    RED_BISBAS_PREFIX: Final[str] = "red_bisbas_"
    
    # Delivery patterns
    DELIVERY_PREFIX: Final[str] = "delivery_"


# Configuration validation constants
class ConfigValidation:
    """Configuration validation constants"""
    
    # Environment types
    VALID_ENVIRONMENTS: Final[list[str]] = ["development", "staging", "production"]
    
    # Currency types
    VALID_CURRENCIES: Final[list[str]] = ["ILS", "USD", "EUR"]
    
    # Bot token validation
    MIN_BOT_TOKEN_LENGTH: Final[int] = 40
    
    # Database validation
    POSTGRESQL_PREFIX: Final[str] = "postgresql://"
    
    # File permissions
    SECURE_FILE_PERMISSIONS: Final[int] = 0o600


# Logging-related constants
class LoggingConstants:
    """Logging-related constants"""
    
    # Log levels
    VALID_LOG_LEVELS: Final[list[str]] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    # Log file names
    MAIN_LOG_FILE: Final[str] = "logs/main.log"
    ERROR_LOG_FILE: Final[str] = "logs/errors.log"
    SECURITY_LOG_FILE: Final[str] = "logs/security.log"
    PERFORMANCE_LOG_FILE: Final[str] = "logs/performance.log"
    
    # Log rotation
    MAX_LOG_SIZE: Final[int] = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: Final[int] = 5


# Standardized error messages
class ErrorMessages:
    """Standardized error messages"""
    
    # Validation errors
    INVALID_NAME_FORMAT: Final[str] = "Please enter a valid name with letters only"
    NAME_TOO_SHORT: Final[str] = "Name must be at least 2 characters long"
    NAME_TOO_LONG: Final[str] = "Name is too long (maximum 100 characters)"
    NAME_MUST_CONTAIN_LETTERS: Final[str] = "Name must contain letters"
    INVALID_ADDRESS_FORMAT: Final[str] = "Please enter a valid address"
    ADDRESS_TOO_SHORT: Final[str] = "Please provide a complete address (at least 10 characters)"
    ADDRESS_TOO_LONG: Final[str] = "Address is too long (maximum 500 characters)"
    INVALID_PHONE_FORMAT: Final[str] = "Please enter a valid Israeli phone number (e.g., 050-1234567)"
    
    # Session errors
    SESSION_EXPIRED: Final[str] = "Your session has expired. Please start again with /start"
    
    # General errors
    ERROR_TRY_START_AGAIN: Final[str] = "Something went wrong. Please try starting again with /start"
    MENU_FUNCTIONALITY_AVAILABLE: Final[str] = "Menu functionality is working perfectly!"
    MENU_ERROR_OCCURRED: Final[str] = "An error occurred while processing your request. Please try again."
    VALIDATION_ERROR: Final[str] = "Please check your input: {error}"
    PLEASE_TRY_AGAIN: Final[str] = "Please try again"
