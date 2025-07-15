"""
Main entrypoint for the Telegram bot application.
"""

import logging
from fastapi import FastAPI, BackgroundTasks
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from src.handlers.start import start_handler
from src.handlers.menu import menu_handler
from src.handlers.cart import cart_handler
from src.handlers.admin import admin_handler
from src.config import get_config
from src.utils.logger import setup_logging

# Initialize FastAPI app
app = FastAPI(title="Samna Salta Bot")
logger = logging.getLogger(__name__)

@app.get("/health")
async def health_check(background_tasks: BackgroundTasks):
    """Health check endpoint"""
    return {"status": "ok", "message": "Bot is running"}

async def init_bot():
    """Initialize and start the bot"""
    # Setup logging
    setup_logging()
    
    # Get config
    config = get_config()
    
    # Create application
    application = Application.builder().token(config.telegram_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    application.add_handler(MessageHandler(filters.COMMAND, cart_handler))
    
    # Add admin handlers if admin features enabled
    if config.admin_features_enabled:
        application.add_handler(CommandHandler("admin", admin_handler))
    
    # Start the bot
    await application.initialize()
    await application.start()
    await application.run_polling()

def main():
    """Main entry point"""
    try:
        import asyncio
        asyncio.run(init_bot())
    except Exception as e:
        logger.error("Failed to start bot: %s", e)
        raise

if __name__ == "__main__":
    main() 