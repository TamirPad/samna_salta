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
    
    # Text message handler for delivery address input (temporarily disabled)
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cart_handler.handle_delivery_address_input))
    
    # Simple text handler to debug conversation issues
    async def debug_text_handler(update, context):
        try:
            print(f"🔍 DEBUG: Received text message: '{update.message.text}' from user {update.effective_user.id}")
            print(f"🔍 DEBUG: Context user_data: {context.user_data}")
            print(f"🔍 DEBUG: Conversation state: {context.user_data.get('conversation_state', 'None')}")
        except Exception as e:
            logger.error(f"Error in debug handler: {e}")
        return
    
    # Add debug handler with lower priority (after conversation handlers)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, debug_text_handler))
    
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
            if webhook_url:
                try:
                    await application.bot.set_webhook(url=f"{webhook_url}/webhook")
                    logger.info(f"Webhook set to: {webhook_url}/webhook")
                except Exception as webhook_error:
                    logger.error(f"Failed to set webhook: {webhook_error}")
                    # Continue without webhook - bot will still work
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
            try:
                logger.info("Shutting down bot...")
                await application.stop()
                await application.shutdown()
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
                # Continue with shutdown even if there are errors

    @app.get("/health")
    async def health_check(background_tasks: BackgroundTasks):
        """Health check endpoint for Render"""
        try:
            from src.db.operations import get_database_status
            
            db_status = get_database_status()
            
            if db_status["connected"]:
                return {
                    "status": "ok", 
                    "message": "Bot is running",
                    "database": "connected",
                    "database_type": db_status["database_type"]
                }
            else:
                return {
                    "status": "degraded", 
                    "message": "Bot is running but database is unavailable",
                    "database": "disconnected",
                    "database_error": db_status["error"]
                }
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return {
                "status": "error",
                "message": "Health check failed",
                "error": str(e)
            }

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
            
        except ValueError as e:
            logger.error(f"Invalid JSON in webhook: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.get("/")
    async def root():
        """Root endpoint"""
        try:
            return {"message": "Samna Salta Bot is running", "status": "active"}
        except Exception as e:
            logger.error(f"Error in root endpoint: {e}")
            return {"message": "Bot is running", "status": "error"}

    # Run the FastAPI app
    try:
        port = int(os.getenv("PORT", 8000))
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        logger.error(f"Failed to start webhook server: {e}")
        raise

def main():
    """Main entry point - determines mode based on environment"""
    try:
        # Check if we should run in webhook mode
        webhook_url = os.getenv("WEBHOOK_URL")
        port = os.getenv("PORT")
        
        # If WEBHOOK_URL or PORT is set, run in webhook mode (production)
        if webhook_url or port:
            run_webhook()
        else:
            # Otherwise run in polling mode (local development)
            run_polling()
    except Exception as e:
        logging.getLogger(__name__).error(f"Fatal error in main: {e}")
        raise

if __name__ == "__main__":
    main() 