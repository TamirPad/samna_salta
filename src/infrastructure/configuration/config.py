"""
Configuration management for the Samna Salta bot
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Bot configuration
    bot_token: str = Field(..., env="BOT_TOKEN")
    admin_chat_id: int = Field(..., env="ADMIN_CHAT_ID")
    
    # Database configuration
    database_url: str = Field("sqlite:///data/samna_salta.db", env="DATABASE_URL")
    
    # Application settings
    log_level: str = Field("INFO", env="LOG_LEVEL")
    environment: str = Field("development", env="ENVIRONMENT")
    
    # Delivery settings
    delivery_charge: float = Field(5.00, env="DELIVERY_CHARGE")
    currency: str = Field("ILS", env="CURRENCY")
    
    # Business hours for Hilbeh
    hilbeh_available_days: List[str] = Field(
        default=["wednesday", "thursday", "friday"]
    )
    hilbeh_available_hours: str = Field("09:00-18:00", env="HILBEH_AVAILABLE_HOURS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
_settings = None


def get_config() -> Settings:
    """Get the global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 