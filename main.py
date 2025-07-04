#!/usr/bin/env python3
"""
Main entry point for the Samna Salta Telegram Bot
"""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram.ext import Application

from src.bot.handlers import register_handlers
from src.database.operations import init_db
from src.utils.config import get_config
from src.utils.helpers import setup_logging

# Load environment variables
load_dotenv()

def main():
    """Main function to run the bot"""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
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
        
        # Register handlers
        logger.info("Registering handlers...")
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