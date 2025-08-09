"""
Configuration management for the Samna Salta bot
"""


import threading
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Bot configuration
    bot_token: str = Field(description="Telegram bot token", min_length=1)
    admin_chat_id: int = Field(description="Admin chat ID for notifications", gt=0)

    # Database configuration
    database_url: str = Field(
        default="postgresql://postgres:your_password_here@localhost:5432/samna_salta", description="Database connection URL"
    )
    supabase_connection_string: str = Field(
        default="", description="Supabase PostgreSQL connection string"
    )

    # Redis configuration (for rate limiting in production)
    redis_url: str = Field(
        default="redis://localhost:6379", description="Redis connection URL for rate limiting"
    )

    # Application settings
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(
        default="development", description="Application environment"
    )

    # Feature flags
    enable_product_options: bool = Field(
        default=True, description="Enable product options selection and pricing"
    )

    # Delivery settings
    delivery_charge: float = Field(default=5.00, description="Delivery charge amount")
    currency: str = Field(default="ILS", description="Currency code")

    # Business hours for Hilbeh
    hilbeh_available_days: List[str] = Field(
        default=["wednesday", "thursday", "friday"],
        description="Days when Hilbeh is available",
    )
    hilbeh_available_hours: str = Field(
        default="09:00-18:00", description="Hours when Hilbeh is available"
    )


_settings_instance: Settings | None = None
_settings_lock = threading.Lock()


def get_config() -> Settings:
    """Get the global settings instance, ensuring thread safety."""
    global _settings_instance
    if _settings_instance is None:
        with _settings_lock:
            if _settings_instance is None:
                _settings_instance = Settings()
    return _settings_instance


# ---------------------------------------------------------------------------
# Configuration validation (moved from utilities/config_validator.py)
# ---------------------------------------------------------------------------

import logging
from pathlib import Path
from sqlalchemy import exc, text  # type: ignore
from src.utils.constants import ConfigValidation, LoggingConstants

# Import httpx conditionally to avoid dependency issues
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None


logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates configuration for production readiness"""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.config: Settings | None = None

    # ---------------------------- public API ----------------------------
    def validate_all(self) -> bool:  # noqa: C901 (long method)
        """Run all validation checks and collect results"""
        try:
            self.config = get_config()
        except (ValueError, TypeError) as exc:  # pragma: no cover – unlikely
            self.errors.append(f"Failed to load configuration: {exc}")
            return False

        self._validate_bot_configuration()
        self._validate_database_configuration()
        self._validate_environment_settings()
        self._validate_business_rules()
        self._validate_file_permissions()
        self._validate_security_settings()

        self._log_validation_results()
        return not self.errors

    def get_validation_report(self) -> dict[str, object]:
        """Return detailed report after running `validate_all()`."""
        return {
            "valid": not self.errors,
            "errors": self.errors,
            "warnings": self.warnings,
            "config_summary": {
                "environment": self.config.environment if self.config else None,
                "database_type": (
                    "sqlite"
                    if self.config and "sqlite" in self.config.database_url
                    else "other"
                ),
                "bot_configured": bool(self.config and self.config.bot_token),
                "admin_configured": bool(self.config and self.config.admin_chat_id),
            },
        }

    # --------------------- individual validation helpers ---------------------

    def _validate_bot_configuration(self):
        if not self.config:
            self.errors.append("Configuration not loaded")
            return
            
        if not self.config.bot_token:
            self.errors.append("BOT_TOKEN is required")
        elif len(self.config.bot_token) < ConfigValidation.MIN_BOT_TOKEN_LENGTH:
            self.errors.append("BOT_TOKEN appears too short")

        if not self.config.admin_chat_id:
            self.errors.append("ADMIN_CHAT_ID is required")
        elif self.config.admin_chat_id <= 0:
            self.errors.append("ADMIN_CHAT_ID must be positive")

        # Optional: live test token
        if HTTPX_AVAILABLE and httpx:
            try:
                response = httpx.get(
                    f"https://api.telegram.org/bot{self.config.bot_token}/getMe", timeout=10
                )
                if response.status_code != 200:
                    self.warnings.append("Bot token verification failed (non-200 response)")
            except httpx.RequestError as exc:
                self.warnings.append(f"Could not verify bot token: {exc}")
        else:
            self.warnings.append("httpx not available - skipping bot token verification")

    def _validate_database_configuration(self):
        if not self.config:
            self.errors.append("Configuration not loaded")
            return
            
        # Check for Supabase connection string first
        if self.config.supabase_connection_string:
            database_url = self.config.supabase_connection_string
            self.warnings.append("Using Supabase PostgreSQL connection")
        elif self.config.database_url:
            database_url = self.config.database_url
        else:
            self.errors.append("Either DATABASE_URL or SUPABASE_CONNECTION_STRING is required")
            return
            
        if database_url.startswith(ConfigValidation.SQLITE_PREFIX):
            db_path = database_url.replace(ConfigValidation.SQLITE_PREFIX, "")
            if not Path(db_path).parent.exists():
                self.errors.append(f"Database directory does not exist: {Path(db_path).parent}")
            if not Path(db_path).exists():
                self.warnings.append(f"Database file will be created: {db_path}")
        elif database_url.startswith("postgresql://"):
            self.warnings.append("Using PostgreSQL database")
        else:
            self.warnings.append(f"Unknown database type: {database_url.split('://')[0]}")
            
        # Attempt connection
        try:
            # Import here to avoid circular import
            from sqlalchemy import create_engine
            engine = create_engine(database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.warnings.append("Database connection successful")
        except exc.SQLAlchemyError as err:
            self.errors.append(f"Database connection failed: {err}")

    def _validate_environment_settings(self):
        if not self.config:
            self.errors.append("Configuration not loaded")
            return
            
        if self.config.environment not in ConfigValidation.VALID_ENVIRONMENTS:
            self.warnings.append(f"Unknown environment: {self.config.environment}")
        if self.config.environment == "production":
            if self.config.log_level.upper() == "DEBUG":
                self.warnings.append("DEBUG logging in production may impact performance")

    def _validate_business_rules(self):
        if not self.config:
            self.errors.append("Configuration not loaded")
            return
            
        if self.config.delivery_charge < 0:
            self.errors.append("Delivery charge cannot be negative")
        if self.config.currency not in ConfigValidation.VALID_CURRENCIES:
            self.warnings.append(f"Unusual currency: {self.config.currency}")

    def _validate_file_permissions(self):
        for dir_name in ["data", "logs"]:
            Path(dir_name).mkdir(exist_ok=True)
            test_file = Path(dir_name) / "__test_write.tmp"
            try:
                test_file.write_text("test", encoding="utf-8")
                test_file.unlink()
            except (IOError, OSError) as exc:
                self.errors.append(f"No write permission for {dir_name}: {exc}")

    def _validate_security_settings(self):
        env_file = Path(".env")
        if env_file.exists():
            if env_file.stat().st_mode & ConfigValidation.SECURE_FILE_PERMISSIONS:
                self.warnings.append(".env file may have insecure permissions")

    # ----------------------------- logging helper -----------------------------

    def _log_validation_results(self):
        if self.errors:
            logger.error("Configuration validation failed", extra={"errors": self.errors, "warnings": self.warnings})
        elif self.warnings:
            logger.warning("Configuration validation passed with warnings", extra={"warnings": self.warnings})
        else:
            logger.info("Configuration validation passed successfully")


# Convenience function

def validate_production_readiness() -> bool:
    """Validate production readiness and print summary to console."""
    validator = ConfigValidator()
    is_valid = validator.validate_all()
    report = validator.get_validation_report()

    if not is_valid:
        print("❌ Configuration validation FAILED:")
        for err in report["errors"]:
            print(f"  - {err}")
    elif report["warnings"]:
        print("⚠️  Configuration validation passed with warnings:")
        for warn in report["warnings"]:
            print(f"  - {warn}")
    else:
        print("✅ Configuration validation PASSED without warnings")
    return is_valid
