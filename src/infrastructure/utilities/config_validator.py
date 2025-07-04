"""
Configuration validation for production deployment
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..configuration.config import get_config, Settings
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates configuration for production readiness"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.config: Optional[Settings] = None
    
    def validate_all(self) -> bool:
        """Validate all configuration aspects"""
        try:
            self.config = get_config()
        except Exception as e:
            self.errors.append(f"Failed to load configuration: {e}")
            return False
        
        # Run all validation checks
        self._validate_bot_configuration()
        self._validate_database_configuration()
        self._validate_environment_settings()
        self._validate_business_rules()
        self._validate_file_permissions()
        self._validate_security_settings()
        
        # Log results
        self._log_validation_results()
        
        return len(self.errors) == 0
    
    def _validate_bot_configuration(self):
        """Validate Telegram bot configuration"""
        if not self.config.bot_token:
            self.errors.append("BOT_TOKEN is required")
        elif not self.config.bot_token.startswith(('bot', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
            self.errors.append("BOT_TOKEN appears to be invalid format")
        elif len(self.config.bot_token) < 40:
            self.errors.append("BOT_TOKEN appears too short")
        
        if not self.config.admin_chat_id:
            self.errors.append("ADMIN_CHAT_ID is required")
        elif self.config.admin_chat_id <= 0:
            self.errors.append("ADMIN_CHAT_ID must be a positive integer")
        
        # Check if bot token works (optional test)
        self._test_bot_token()
    
    def _test_bot_token(self):
        """Test if bot token is valid by making a simple API call"""
        try:
            import httpx
            response = httpx.get(
                f"https://api.telegram.org/bot{self.config.bot_token}/getMe",
                timeout=10
            )
            if response.status_code != 200:
                self.warnings.append("Bot token may be invalid - API test failed")
            else:
                bot_info = response.json()
                if bot_info.get('ok'):
                    self.warnings.append(f"Bot validated: @{bot_info['result']['username']}")
                else:
                    self.warnings.append("Bot token validation failed")
        except Exception as e:
            self.warnings.append(f"Could not validate bot token: {e}")
    
    def _validate_database_configuration(self):
        """Validate database configuration"""
        if not self.config.database_url:
            self.errors.append("DATABASE_URL is required")
        
        # Check if database file exists for SQLite
        if self.config.database_url.startswith('sqlite:'):
            db_path = self.config.database_url.replace('sqlite:///', '')
            if not Path(db_path).parent.exists():
                self.errors.append(f"Database directory does not exist: {Path(db_path).parent}")
            
            if not Path(db_path).exists():
                self.warnings.append(f"Database file does not exist (will be created): {db_path}")
        
        # Test database connection
        self._test_database_connection()
    
    def _test_database_connection(self):
        """Test database connection"""
        try:
            from ..database.operations import get_engine
            from sqlalchemy import text
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.warnings.append("Database connection successful")
        except Exception as e:
            self.errors.append(f"Database connection failed: {e}")
    
    def _validate_environment_settings(self):
        """Validate environment and deployment settings"""
        if self.config.environment not in ['development', 'staging', 'production']:
            self.warnings.append(f"Unknown environment: {self.config.environment}")
        
        if self.config.environment == 'production':
            # Production-specific validations
            if self.config.log_level.upper() == 'DEBUG':
                self.warnings.append("DEBUG logging in production may impact performance")
            
            if self.config.database_url.startswith('sqlite:'):
                self.warnings.append("SQLite database in production - consider PostgreSQL for better performance")
        
        # Check required directories
        required_dirs = ['data', 'logs']
        for dir_name in required_dirs:
            if not Path(dir_name).exists():
                try:
                    Path(dir_name).mkdir(exist_ok=True)
                    self.warnings.append(f"Created missing directory: {dir_name}")
                except Exception as e:
                    self.errors.append(f"Cannot create required directory {dir_name}: {e}")
    
    def _validate_business_rules(self):
        """Validate business logic configuration"""
        if self.config.delivery_charge < 0:
            self.errors.append("Delivery charge cannot be negative")
        
        if not self.config.currency:
            self.errors.append("Currency is required")
        elif self.config.currency not in ['ILS', 'USD', 'EUR']:
            self.warnings.append(f"Unusual currency: {self.config.currency}")
        
        # Validate Hilbeh availability days
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in self.config.hilbeh_available_days:
            if day.lower() not in valid_days:
                self.errors.append(f"Invalid day in hilbeh_available_days: {day}")
        
        # Validate business hours format
        try:
            start, end = self.config.hilbeh_available_hours.split('-')
            for time_str in [start, end]:
                hours, minutes = time_str.split(':')
                if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
                    raise ValueError("Invalid time")
        except Exception:
            self.errors.append(f"Invalid hilbeh_available_hours format: {self.config.hilbeh_available_hours}")
    
    def _validate_file_permissions(self):
        """Validate file system permissions"""
        test_files = [
            ('data/test_write.tmp', 'data directory'),
            ('logs/test_write.tmp', 'logs directory')
        ]
        
        for file_path, description in test_files:
            try:
                Path(file_path).parent.mkdir(exist_ok=True)
                Path(file_path).write_text('test')
                Path(file_path).unlink()
                self.warnings.append(f"Write permission confirmed for {description}")
            except Exception as e:
                self.errors.append(f"No write permission for {description}: {e}")
    
    def _validate_security_settings(self):
        """Validate security configuration"""
        # Check if .env file has proper permissions (not readable by others)
        env_file = Path('.env')
        if env_file.exists():
            import stat
            permissions = oct(env_file.stat().st_mode)[-3:]
            if permissions != '600':
                self.warnings.append(f".env file has permissive permissions: {permissions} (should be 600)")
        
        # Check for development tokens in production
        if self.config.environment == 'production':
            if 'test' in self.config.bot_token.lower():
                self.warnings.append("Bot token contains 'test' - ensure this is a production token")
    
    def _log_validation_results(self):
        """Log validation results"""
        if self.errors:
            logger.error("Configuration validation failed", extra={
                'errors': self.errors,
                'warnings': self.warnings
            })
        elif self.warnings:
            logger.warning("Configuration validation passed with warnings", extra={
                'warnings': self.warnings
            })
        else:
            logger.info("Configuration validation passed successfully")
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get detailed validation report"""
        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'config_summary': {
                'environment': self.config.environment if self.config else None,
                'database_type': 'sqlite' if self.config and 'sqlite' in self.config.database_url else 'other',
                'bot_configured': bool(self.config and self.config.bot_token),
                'admin_configured': bool(self.config and self.config.admin_chat_id)
            }
        }


def validate_production_readiness() -> bool:
    """Main function to validate production readiness"""
    validator = ConfigValidator()
    is_valid = validator.validate_all()
    
    report = validator.get_validation_report()
    
    if not is_valid:
        print("❌ Configuration validation FAILED:")
        for error in report['errors']:
            print(f"  - {error}")
    
    if report['warnings']:
        print("⚠️  Configuration warnings:")
        for warning in report['warnings']:
            print(f"  - {warning}")
    
    if is_valid and not report['warnings']:
        print("✅ Configuration validation PASSED - Ready for production!")
    elif is_valid:
        print("✅ Configuration validation PASSED with warnings - Review before production")
    
    return is_valid


if __name__ == "__main__":
    validate_production_readiness() 