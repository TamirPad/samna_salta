"""
Main entrypoint for the Telegram bot application.
Web service for Render deployment with webhook support.
"""

import logging
import os
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update

from src.handlers.start import start_handler, OnboardingHandler
from src.handlers.menu import menu_handler
from src.handlers.cart import CartHandler
from src.handlers.admin import register_admin_handlers
from src.config import get_config
from src.utils.logger import ProductionLogger
from src.db.operations import init_db, init_default_products
from src.container import get_container

# Initialize FastAPI app
app = FastAPI(title="Samna Salta Bot")
logger = logging.getLogger(__name__)

# Global application instance
application: Application = None

@app.on_event("startup")
async def startup_event():
    """Initialize the bot on startup"""
    global application
    
    try:
        logger.info("Starting Samna Salta Bot...")
        
        # Setup logging
        ProductionLogger.setup_logging()
        
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
        
        # Start command
        application.add_handler(CommandHandler("start", start_handler))
        application.add_handler(CommandHandler("ping", ping_handler))
        
        # Main page handlers (My Info, Menu navigation)
        onboarding_handler = OnboardingHandler()
        application.add_handler(CallbackQueryHandler(onboarding_handler.handle_main_page_callback, pattern="^main_"))
        
        # Menu handlers
        application.add_handler(CallbackQueryHandler(menu_handler, pattern="^menu_"))
        
        # Cart handlers
        cart_handler = CartHandler()
        application.add_handler(CallbackQueryHandler(cart_handler.handle_add_to_cart, pattern="^add_"))
        application.add_handler(CallbackQueryHandler(cart_handler.handle_add_to_cart, pattern="^(kubaneh_|samneh_|red_bisbas_|hawaij_coffee_spice|white_coffee)"))
        application.add_handler(CallbackQueryHandler(cart_handler.handle_view_cart, pattern="^cart_view"))
        application.add_handler(CallbackQueryHandler(cart_handler.handle_clear_cart, pattern="^cart_clear"))
        application.add_handler(CallbackQueryHandler(cart_handler.handle_checkout, pattern="^cart_checkout"))
        application.add_handler(CallbackQueryHandler(cart_handler.handle_delivery_address_choice, pattern="^delivery_address_"))
        application.add_handler(CallbackQueryHandler(cart_handler.handle_delivery_method, pattern="^delivery_"))
        application.add_handler(CallbackQueryHandler(cart_handler.handle_confirm_order, pattern="^confirm_order"))
        
        # Text message handler for delivery address input
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cart_handler.handle_delivery_address_input))
        
        # Register admin handlers
        register_admin_handlers(application)
        
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
    global application
    if application:
        logger.info("Shutting down bot...")
        await application.stop()
        await application.shutdown()

async def ping_handler(update, context):
    """Simple ping handler"""
    await update.message.reply_text('pong')

@app.get("/health")
async def health_check(background_tasks: BackgroundTasks):
    """Health check endpoint for Render"""
    return {"status": "ok", "message": "Bot is running"}

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handle incoming webhook updates from Telegram"""
    global application
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000))) 