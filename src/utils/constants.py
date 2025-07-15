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


# Security and rate limiting constants
class SecuritySettings:
    """Security thresholds and rate limiting"""

    DEFAULT_RATE_LIMIT_REQUESTS: Final[int] = 10
    DEFAULT_RATE_LIMIT_WINDOW_SECONDS: Final[int] = 60
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: Final[int] = 5
    CIRCUIT_BREAKER_TIMEOUT_SECONDS: Final[int] = 60

    # Rate limits by endpoint type
    MENU_RATE_LIMIT: Final[int] = 10
    CART_RATE_LIMIT: Final[int] = 20
    ORDER_RATE_LIMIT: Final[int] = 5
    ADMIN_RATE_LIMIT: Final[int] = 30


# Validation constants
class ValidationSettings:
    """Input validation limits and constraints"""

    MIN_CUSTOMER_NAME_LENGTH: Final[int] = 2
    MAX_CUSTOMER_NAME_LENGTH: Final[int] = 100
    MIN_PRODUCT_NAME_LENGTH: Final[int] = 1
    MAX_PRODUCT_NAME_LENGTH: Final[int] = 100
    MAX_CART_ITEM_QUANTITY: Final[int] = 99
    MIN_CART_ITEM_QUANTITY: Final[int] = 1


# Business logic constants
class BusinessSettings:
    """Business rules and default values"""

    DEFAULT_DELIVERY_CHARGE: Final[float] = 5.00
    DEFAULT_DELIVERY_METHOD: Final[str] = "pickup"
    DEFAULT_CURRENCY: Final[str] = "ILS"
    DEFAULT_HILBEH_DAYS: Final[list] = ["wednesday", "thursday", "friday"]
    DEFAULT_HILBEH_HOURS: Final[str] = "09:00-18:00"

    # Product pricing
    KUBANEH_BASE_PRICE: Final[float] = 25.00
    SAMNEH_BASE_PRICE: Final[float] = 15.00
    RED_BISBAS_BASE_PRICE: Final[float] = 12.00
    HILBEH_BASE_PRICE: Final[float] = 18.00
    HAWAIJ_SOUP_PRICE: Final[float] = 8.00
    HAWAIJ_COFFEE_PRICE: Final[float] = 8.00
    WHITE_COFFEE_PRICE: Final[float] = 10.00


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
    GENERIC_ERROR_MESSAGE: Final[str] = "An error occurred. Please try again."
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
    DEFAULT_DATABASE_PATH: Final[str] = "sqlite:///data/samna_salta.db"

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

# Security validation patterns
class SecurityPatterns:
    """Security validation patterns for input sanitization"""
    
    # XSS and injection patterns
    SUSPICIOUS_PATTERNS: Final[list[str]] = [
        "javascript:",
        "data:",
        "vbscript:",
        "<script",
        "</script>",
        "onload=",
        "onerror=",
        "onclick=",
        "drop table",
        "delete from",
        "update set",
        "insert into",
        "union select",
    ]
    
    # Israeli mobile prefixes
    ISRAELI_MOBILE_PREFIXES: Final[list[str]] = ["50", "52", "53", "54", "55", "57", "58"]
    
    # Phone number format
    ISRAELI_PHONE_PREFIX: Final[str] = "+972"
    ISRAELI_PHONE_LENGTH: Final[int] = 13

# Product mapping constants
class ProductConstants:
    """Product-related constants and mappings"""
    
    # Product IDs
    KUBANEH_PRODUCT_ID: Final[int] = 1
    SAMNEH_PRODUCT_ID: Final[int] = 2
    RED_BISBAS_PRODUCT_ID: Final[int] = 3
    HAWAIJ_SOUP_PRODUCT_ID: Final[int] = 4
    HAWAIJ_COFFEE_PRODUCT_ID: Final[int] = 5
    WHITE_COFFEE_PRODUCT_ID: Final[int] = 6
    HILBEH_PRODUCT_ID: Final[int] = 7
    
    # Product type mappings
    PRODUCT_NAME_MAP: Final[dict[str, dict]] = {
        "hilbeh": {
            "product_id": HILBEH_PRODUCT_ID,
            "display_name_key": "PRODUCT_HILBEH",
            "options": {},
        },
        "hawaij_soup": {
            "product_id": HAWAIJ_SOUP_PRODUCT_ID,
            "display_name_key": "PRODUCT_HAWAIJ_SOUP",
            "options": {},
        },
        "hawaij_soup_spice": {
            "product_id": HAWAIJ_SOUP_PRODUCT_ID,
            "display_name_key": "PRODUCT_HAWAIJ_SOUP",
            "options": {},
        },
        "hawaij_coffee": {
            "product_id": HAWAIJ_COFFEE_PRODUCT_ID,
            "display_name_key": "PRODUCT_HAWAIJ_COFFEE",
            "options": {},
        },
        "hawaij_coffee_spice": {
            "product_id": HAWAIJ_COFFEE_PRODUCT_ID,
            "display_name_key": "PRODUCT_HAWAIJ_COFFEE",
            "options": {},
        },
        "white_coffee": {
            "product_id": WHITE_COFFEE_PRODUCT_ID,
            "display_name_key": "PRODUCT_WHITE_COFFEE",
            "options": {},
        },
    }

# Callback data patterns
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
    SQLITE_PREFIX: Final[str] = "sqlite:///"
    
    # File permissions
    SECURE_FILE_PERMISSIONS: Final[int] = 0o600

# Logging constants
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

# Performance monitoring constants
class PerformanceConstants:
    """Performance monitoring constants"""
    
    # Monitoring intervals
    DEFAULT_MONITORING_INTERVAL: Final[float] = 5.0
    
    # Thresholds
    SLOW_QUERY_THRESHOLD: Final[float] = 1.0  # seconds
    HIGH_MEMORY_THRESHOLD: Final[float] = 80.0  # percentage
    HIGH_CPU_THRESHOLD: Final[float] = 80.0  # percentage
    
    # Cache TTL
    DEFAULT_CACHE_TTL: Final[int] = 3600  # 1 hour

# Error messages
class ErrorMessages:
    """Standardized error messages"""
    
    # Validation errors
    INVALID_NAME_FORMAT: Final[str] = "Invalid name format"
    NAME_TOO_SHORT: Final[str] = "Name must be at least 2 characters"
    NAME_TOO_LONG: Final[str] = "Name is too long"
    NAME_MUST_CONTAIN_LETTERS: Final[str] = "Name must contain letters"
    INVALID_ADDRESS_FORMAT: Final[str] = "Invalid address format"
    ADDRESS_TOO_SHORT: Final[str] = "Please provide a complete address"
    ADDRESS_TOO_LONG: Final[str] = "Address is too long"
    INVALID_PHONE_FORMAT: Final[str] = "Please enter a valid Israeli phone number"
    
    # Session errors
    SESSION_EXPIRED: Final[str] = "Session expired. Please start again with /start"
    
    # General errors
    ERROR_TRY_START_AGAIN: Final[str] = "An error occurred. Please try starting again with /start"
    MENU_FUNCTIONALITY_AVAILABLE: Final[str] = "This menu functionality is available"
    MENU_ERROR_OCCURRED: Final[str] = "An error occurred while processing your request"
    VALIDATION_ERROR: Final[str] = "Validation error: {error}"
    PLEASE_TRY_AGAIN: Final[str] = "Please try again"
