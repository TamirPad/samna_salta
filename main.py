#!/usr/bin/env python3
"""
Main entry point for the Samna Salta Telegram Bot
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from telegram.ext import Application

from src.presentation.telegram_bot.handlers import register_handlers
from src.infrastructure.database.operations import init_db
from src.infrastructure.configuration.config import get_config
from src.infrastructure.logging.logging_config import ProductionLogger
from src.infrastructure.container.dependency_injection import initialize_container

# Load environment variables
load_dotenv()

def check_python_compatibility():
    """Check Python version compatibility and apply workarounds if needed"""
    python_version = sys.version_info
    if python_version.major == 3 and python_version.minor >= 13:
        # Python 3.13+ compatibility workaround for python-telegram-bot
        try:
            import telegram.ext._updater
            
            # Try to add the missing attribute using setattr to handle read-only attributes
            if not hasattr(telegram.ext._updater.Updater, '_Updater__polling_cleanup_cb'):
                try:
                    # First try direct assignment
                    telegram.ext._updater.Updater._Updater__polling_cleanup_cb = None
                except (AttributeError, TypeError):
                    # If that fails, use object.__setattr__ to bypass read-only protection
                    object.__setattr__(telegram.ext._updater.Updater, '_Updater__polling_cleanup_cb', None)
                
                print(f"Applied Python {python_version.major}.{python_version.minor} compatibility workaround")
            
            # Alternative approach: monkey patch the Updater class
            original_init = telegram.ext._updater.Updater.__init__
            
            def patched_init(self, *args, **kwargs):
                result = original_init(self, *args, **kwargs)
                if not hasattr(self, '_Updater__polling_cleanup_cb'):
                    object.__setattr__(self, '_Updater__polling_cleanup_cb', None)
                return result
            
            telegram.ext._updater.Updater.__init__ = patched_init
            
        except Exception as e:
            print(f"Warning: Could not apply Python 3.13 compatibility workaround: {e}")
            print("Bot may still work, attempting to continue...")

def main():
    """Main function to run the bot"""
    # Setup production logging
    ProductionLogger.setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Check Python compatibility and apply workarounds
        check_python_compatibility()
        
        # Load configuration
        logger.info("Loading configuration...")
        config = get_config()
        
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Create application
        logger.info("Creating Telegram application...")
        application = Application.builder().token(config.bot_token).build()
        
        # Initialize dependency container with bot instance
        logger.info("Initializing dependency container...")
        initialize_container(bot=application.bot)
        
        # Register Clean Architecture handlers
        logger.info("Registering Clean Architecture handlers...")
        register_handlers(application)
        
        # Start the bot
        logger.info("Starting bot...")
        logger.info(f"Bot token: {config.bot_token[:10]}...")
        logger.info(f"Admin chat ID: {config.admin_chat_id}")
        
        # Run polling
        application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    # Run the bot
    try:
        main()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Error: {e}") 