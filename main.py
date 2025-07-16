#!/usr/bin/env python3
"""
Unified entry point for Samna Salta Bot
Supports both local development (polling) and production deployment (webhook)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_config
from src.db.operations import init_db, init_default_products
from src.container import get_container
from src.handlers.start import start_handler, OnboardingHandler, register_start_handlers
from src.handlers.menu import menu_handler
from src.handlers.cart import CartHandler
from src.handlers.admin import register_admin_handlers
from src.utils.logger import ProductionLogger
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

def setup_bot():
    """Setup and configure the bot application"""
    # Setup logging
    ProductionLogger.setup_logging()
    logger = logging.getLogger(__name__)
    
    # Get config
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
    
    # Register onboarding conversation handler (includes /start command)
    register_start_handlers(application)
    
    # Ping command
    application.add_handler(CommandHandler("ping", ping_handler))
    
    # Main page handlers (My Info, Menu navigation)
    onboarding_handler = OnboardingHandler()
    application.add_handler(CallbackQueryHandler(onboarding_handler.handle_main_page_callback, pattern="^main_"))
    
    # Language selection handlers
    application.add_handler(CallbackQueryHandler(onboarding_handler.handle_main_page_callback, pattern="^language_"))
    
    # Menu handlers
    application.add_handler(CallbackQueryHandler(menu_handler, pattern="^menu_"))
    
    # Cart handlers
    cart_handler = CartHandler()
    application.add_handler(CallbackQueryHandler(cart_handler.handle_add_to_cart, pattern="^add_"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_add_to_cart, pattern="^(kubaneh_|samneh_|red_bisbas_|hawaij_coffee_spice|white_coffee)"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_view_cart, pattern="^cart_view"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_clear_cart_confirmation, pattern="^cart_clear_confirm"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_clear_cart, pattern="^cart_clear_yes"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_checkout, pattern="^cart_checkout"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_delivery_address_choice, pattern="^delivery_address_"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_delivery_method, pattern="^delivery_"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_confirm_order, pattern="^confirm_order"))
    
    # Text message handler for delivery address input
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cart_handler.handle_delivery_address_input))
    
    # Register admin handlers
    register_admin_handlers(application)
    
    return application

async def ping_handler(update, context):
    """Simple ping handler"""
    await update.message.reply_text('pong')

def run_polling():
    """Run bot in polling mode for local development"""
    print("🚀 Starting Samna Salta Bot in LOCAL DEVELOPMENT mode (polling)...")
    
    try:
        application = setup_bot()
        
        print("✅ Bot started successfully!")
        print("📱 Send /start to your bot in Telegram to test it!")
        print("🛑 Press Ctrl+C to stop the bot")
        
        # Start polling (this will run until interrupted)
        application.run_polling()
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to start bot: {e}")
        raise

def run_webhook():
    """Run bot in webhook mode for production deployment"""
    from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
    from fastapi.responses import JSONResponse
    from telegram import Update
    import uvicorn
    
    print("🚀 Starting Samna Salta Bot in PRODUCTION mode (webhook)...")
    
    # Initialize FastAPI app
    app = FastAPI(title="Samna Salta Bot")
    logger = logging.getLogger(__name__)
    
    # Global application instance
    application: Application = None

    @app.on_event("startup")
    async def startup_event():
        """Initialize the bot on startup"""
        nonlocal application
        
        try:
            application = setup_bot()
            
            # Initialize the application
            await application.initialize()
            await application.start()
            
            # Set webhook (webhook mode only)
            webhook_url = os.getenv("WEBHOOK_URL")
            if webhook_url:
                await application.bot.set_webhook(url=f"{webhook_url}/webhook")
                logger.info(f"Webhook set to: {webhook_url}/webhook")
            else:
                logger.warning("WEBHOOK_URL not set! Bot will not receive updates.")
            
            logger.info("Bot started successfully!")
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        nonlocal application
        if application:
            logger.info("Shutting down bot...")
            await application.stop()
            await application.shutdown()

    @app.get("/health")
    async def health_check(background_tasks: BackgroundTasks):
        """Health check endpoint for Render"""
        return {"status": "ok", "message": "Bot is running"}

    @app.post("/webhook")
    async def webhook_handler(request: Request):
        """Handle incoming webhook updates from Telegram"""
        nonlocal application
        
        if not application:
            raise HTTPException(status_code=503, detail="Bot not initialized")
        
        try:
            # Get the update data
            update_data = await request.json()
            update = Update.de_json(update_data, application.bot)
            
            # Process the update
            await application.process_update(update)
            
            return JSONResponse(content={"status": "ok"})
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.get("/")
    async def root():
        """Root endpoint"""
        return {"message": "Samna Salta Bot is running", "status": "active"}

    # Run the FastAPI app
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

def main():
    """Main entry point - determines mode based on environment"""
    # Check if we should run in webhook mode
    webhook_url = os.getenv("WEBHOOK_URL")
    port = os.getenv("PORT")
    
    # If WEBHOOK_URL or PORT is set, run in webhook mode (production)
    if webhook_url or port:
        run_webhook()
    else:
        # Otherwise run in polling mode (local development)
        run_polling()

if __name__ == "__main__":
    main() 