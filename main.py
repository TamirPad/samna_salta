#!/usr/bin/env python3
"""
Samna Salta - Traditional Yemenite Food Bot
Main application entry point
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from telegram import Update

from src.config import get_config
from src.db.operations import init_db, init_default_products
from src.container import get_container
from src.handlers.start import start_handler
from src.handlers.menu import menu_handler
from src.handlers.cart import CartHandler
from src.handlers.admin import register_admin_handlers
from src.utils.logger import ProductionLogger

# Load environment variables
load_dotenv()

# Setup logging
ProductionLogger.setup_logging()
logger = logging.getLogger(__name__)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Received shutdown signal, stopping bot...")
    sys.exit(0)


async def ping_handler(update, context):
    await update.message.reply_text('pong')


def main():
    """Main application function"""
    try:
        logger.info("Starting Samna Salta Bot...")
        
        # Load configuration
        config = get_config()
        logger.info("Configuration loaded successfully")

        # Initialize database
        logger.info("Initializing database...")
        init_db()
        init_default_products()
        logger.info("Database initialized successfully")

        # Create application
        logger.info("Creating Telegram application...")
        application = Application.builder().token(config.bot_token).build()

        # Initialize container
        container = get_container()
        container.set_bot(application.bot)
        logger.info("Dependency container initialized")
        
        # Register handlers
        logger.info("Registering handlers...")
        
        # Start command
        application.add_handler(CommandHandler("start", start_handler))
        application.add_handler(CommandHandler("ping", ping_handler))
        
        # Menu handlers
        application.add_handler(CallbackQueryHandler(menu_handler, pattern="^menu_"))
        
        # Cart handlers
        cart_handler = CartHandler()
        application.add_handler(CallbackQueryHandler(cart_handler.handle_add_to_cart, pattern="^add_"))
        application.add_handler(CallbackQueryHandler(cart_handler.handle_add_to_cart, pattern="^(kubaneh_|samneh_|red_bisbas_|hawaij_coffee_spice|white_coffee)"))
        application.add_handler(CallbackQueryHandler(cart_handler.handle_view_cart, pattern="^cart_view"))
        application.add_handler(CallbackQueryHandler(cart_handler.handle_clear_cart, pattern="^cart_clear"))
        application.add_handler(CallbackQueryHandler(cart_handler.handle_checkout, pattern="^cart_checkout"))
        application.add_handler(CallbackQueryHandler(cart_handler.handle_delivery_method, pattern="^delivery_"))
        application.add_handler(CallbackQueryHandler(cart_handler.handle_confirm_order, pattern="^confirm_order"))
        
        # Register admin handlers
        register_admin_handlers(application)
        
        # Start polling (blocking call)
        logger.info("Starting bot polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Bot started successfully! Ready to receive messages.")

    except Exception as e:
        logger.error("Failed to start bot: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()
