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
from src.handlers.menu import MenuHandler
from src.handlers.cart import CartHandler
from src.handlers.admin import register_admin_handlers
from src.utils.logger import ProductionLogger
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

def setup_bot():
    """Setup and configure the bot application"""
    try:
        # Setup logging
        ProductionLogger.setup_logging()
        logger = logging.getLogger(__name__)
        
        # Get config
        config = get_config()
        logger.info("Configuration loaded successfully")

        # Initialize database with retry logic
        logger.info("Initializing database...")
        try:
            init_db()
            # init_default_products() is now called within init_db()
            logger.info("Database initialization completed")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            logger.warning("Bot will start with limited functionality - database features may not work")
            # Continue with bot startup even if database fails
    except Exception as e:
        logger.error(f"Failed to setup bot: {e}")
        raise

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
    
    # Customer order tracking handlers
    application.add_handler(CallbackQueryHandler(onboarding_handler.handle_main_page_callback, pattern="^customer_order_"))
    
    # Menu handlers
    menu_handler_instance = MenuHandler()
    application.add_handler(CallbackQueryHandler(menu_handler_instance.handle_menu_callback, pattern="^menu_"))
    
    # Dynamic menu handlers (for new product system)
    application.add_handler(CallbackQueryHandler(menu_handler_instance.handle_menu_callback, pattern="^category_"))
    application.add_handler(CallbackQueryHandler(menu_handler_instance.handle_menu_callback, pattern="^product_"))
    
    # Cart handlers
    cart_handler = CartHandler()
    application.add_handler(CallbackQueryHandler(cart_handler.handle_add_to_cart, pattern="^add_"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_add_to_cart, pattern="^add_product_"))
    # Register all product option callbacks
    application.add_handler(CallbackQueryHandler(cart_handler.handle_add_to_cart, pattern="^(kubaneh_|samneh_|red_bisbas_|hilbeh_|hawaij_coffee_spice|white_coffee)"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_view_cart, pattern="^cart_view"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_clear_cart_confirmation, pattern="^cart_clear_confirm"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_clear_cart, pattern="^cart_clear_yes"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_checkout, pattern="^cart_checkout"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_delivery_address_choice, pattern="^delivery_address_"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_delivery_method, pattern="^delivery_"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_confirm_order, pattern="^confirm_order"))
    
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
        try:
            application.run_polling()
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
        except Exception as polling_error:
            logging.getLogger(__name__).error(f"Error during polling: {polling_error}")
            raise
        
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
            if not webhook_url:
                # Try to construct webhook URL from Render environment
                render_url = os.getenv("RENDER_EXTERNAL_URL")
                if render_url:
                    webhook_url = render_url
                    logger.info(f"Using RENDER_EXTERNAL_URL for webhook: {webhook_url}")
                else:
                    logger.warning("WEBHOOK_URL not set! Bot will not receive updates.")
            
            if webhook_url:
                try:
                    webhook_endpoint = f"{webhook_url}/webhook"
                    await application.bot.set_webhook(url=webhook_endpoint)
                    logger.info(f"Webhook set to: {webhook_endpoint}")
                except Exception as webhook_error:
                    logger.error(f"Failed to set webhook: {webhook_error}")
                    # Continue without webhook - bot will still work
            
            logger.info("Bot started successfully!")
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        nonlocal application
        if application:
            try:
                await application.stop()
                await application.shutdown()
                logger.info("Bot shutdown completed")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")

    @app.get("/health")
    async def health_check(background_tasks: BackgroundTasks):
        """Health check endpoint"""
        try:
            # Add health check to background tasks
            background_tasks.add_task(log_health_check)
            
            if application and application.bot:
                return {
                    "status": "healthy",
                    "bot": "running",
                    "timestamp": asyncio.get_event_loop().time()
                }
            else:
                return {
                    "status": "unhealthy",
                    "bot": "not_initialized",
                    "timestamp": asyncio.get_event_loop().time()
                }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=500, detail="Health check failed")

    async def log_health_check():
        """Log health check for monitoring"""
        logger.info("Health check performed")

    @app.post("/webhook")
    async def webhook_handler(request: Request):
        """Handle incoming webhook updates"""
        try:
            # Get the update from the request
            update_data = await request.json()
            update = Update.de_json(update_data, application.bot)
            
            # Process the update
            await application.process_update(update)
            
            return JSONResponse(content={"status": "ok"})
        except Exception as e:
            logger.error(f"Webhook handler error: {e}")
            raise HTTPException(status_code=500, detail="Webhook processing failed")

    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "Samna Salta Bot API",
            "status": "running",
            "version": "1.0.0"
        }

    # Run the FastAPI app
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting FastAPI server on port {port}")
    try:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        logger.error(f"Failed to start FastAPI server: {e}")
        raise

def main():
    """Main entry point"""
    print("🚀 Starting Samna Salta Bot...")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"Webhook Mode: {os.getenv('WEBHOOK_MODE', 'false')}")
    print(f"Port: {os.getenv('PORT', '8000')}")
    
    # Check if we should run in webhook mode
    if os.getenv("WEBHOOK_MODE", "false").lower() == "true":
        run_webhook()
    else:
        run_polling()

if __name__ == "__main__":
    main() 