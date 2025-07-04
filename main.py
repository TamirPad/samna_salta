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

def main():
    """Main function to run the bot"""
    # Setup production logging
    ProductionLogger.setup_logging()
    logger = logging.getLogger(__name__)
    
    # Log Python version for debugging
    python_version = sys.version_info
    logger.info(f"Starting bot with Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    try:
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