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
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Bot configuration
    bot_token: str = Field(description="Telegram bot token")
    admin_chat_id: int = Field(description="Admin chat ID for notifications")

    # Database configuration
    database_url: str = Field(
        default="sqlite:///data/samna_salta.db", 
        description="Database connection URL"
    )

    # Application settings
    log_level: str = Field(
        default="INFO", 
        description="Logging level"
    )
    environment: str = Field(
        default="development", 
        description="Application environment"
    )

    # Delivery settings
    delivery_charge: float = Field(
        default=5.00, 
        description="Delivery charge amount"
    )
    currency: str = Field(
        default="ILS", 
        description="Currency code"
    )

    # Business hours for Hilbeh
    hilbeh_available_days: List[str] = Field(
        default=["wednesday", "thursday", "friday"], 
        description="Days when Hilbeh is available"
    )
    hilbeh_available_hours: str = Field(
        default="09:00-18:00", 
        description="Hours when Hilbeh is available"
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
