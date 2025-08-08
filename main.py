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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_config
from src.db.operations import init_db, init_default_products
from src.container import get_container
from src.handlers.start import start_handler, OnboardingHandler, register_start_handlers
from src.handlers.menu import MenuHandler
from src.handlers.cart import CartHandler
from src.handlers.admin import register_admin_handlers, AdminHandler
from src.utils.logger import ProductionLogger
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update

def setup_bot():
    """Setup and configure the bot application"""
    try:
        # Setup logging
        ProductionLogger.setup_logging()
        logger = logging.getLogger(__name__)
        
        # Get config
        config = get_config()
        logger.info("Configuration loaded successfully")
        
        # Production readiness validation
        if config.environment == 'production':
            from src.utils.production_checks import (
                ensure_production_readiness, 
                setup_error_monitoring,
                validate_database_connection
            )
            
            # Validate production readiness
            if not ensure_production_readiness():
                logger.critical("Production readiness validation failed - stopping startup")
                raise RuntimeError("Production environment not properly configured")
            
            # Setup error monitoring
            setup_error_monitoring()
            
            # Setup metrics collection
            from src.utils.metrics import setup_metrics_collection
            setup_metrics_collection()
            
            logger.info("Production environment validated and monitoring enabled")

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
    
    # My ID command for admin setup
    admin_handler_instance = AdminHandler()
    application.add_handler(CommandHandler("myid", admin_handler_instance.handle_myid_command))
    
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
    application.add_handler(CallbackQueryHandler(cart_handler.handle_quick_signup_start, pattern="^quick_signup$"))
    
    # Cart editing handlers
    application.add_handler(CallbackQueryHandler(cart_handler.handle_edit_cart_mode, pattern="^cart_edit_mode"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_decrease_quantity, pattern="^cart_decrease_"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_increase_quantity, pattern="^cart_increase_"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_remove_item, pattern="^cart_remove_"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_edit_quantity, pattern="^cart_edit_"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_item_info, pattern="^cart_info_"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_separator, pattern="^cart_separator"))
    
    application.add_handler(CallbackQueryHandler(cart_handler.handle_delivery_address_choice, pattern="^delivery_address_"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_delivery_method, pattern="^delivery_"))
    application.add_handler(CallbackQueryHandler(cart_handler.handle_confirm_order, pattern="^confirm_order"))
    # Capture quick signup text inputs globally
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cart_handler.handle_quick_signup_input))
    
    # Register admin handlers
    register_admin_handlers(application)
    
    return application

async def cleanup_webhook(bot):
    """Clean up any existing webhook to prevent conflicts"""
    try:
        await bot.delete_webhook()
        logger = logging.getLogger(__name__)
        logger.info("Cleaned up existing webhook")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to cleanup webhook: {e}")

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
            # Use asyncio.run() for proper event loop handling in Python 3.11
            async def run_bot():
                await application.initialize()
                await application.start()
                await application.updater.start_polling()
                try:
                    # Keep the bot running
                    await asyncio.Event().wait()
                except KeyboardInterrupt:
                    print("\n🛑 Bot stopped by user")
                finally:
                    await application.updater.stop()
                    await application.stop()
                    await application.shutdown()
            
            asyncio.run(run_bot())
            
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
    from contextlib import asynccontextmanager
    
    print("🚀 Starting Samna Salta Bot in PRODUCTION mode (webhook)...")
    
    # Global application instance
    application: Application = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Lifespan context manager for FastAPI app"""
        nonlocal application
        
        # Startup
        try:
            application = setup_bot()
            
            # Initialize the application
            await application.initialize()
            await application.start()
            
            # Clean up any existing webhook first
            await cleanup_webhook(application.bot)
            
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
        
        yield
        
        # Shutdown
        if application:
            try:
                await application.stop()
                await application.shutdown()
                logger.info("Bot shutdown completed")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")

    # Initialize FastAPI app with lifespan
    app = FastAPI(title="Samna Salta Bot", lifespan=lifespan)
    logger = logging.getLogger(__name__)

    @app.get("/health")
    async def health_check(background_tasks: BackgroundTasks):
        """Comprehensive health check endpoint with metrics"""
        try:
            # Add health check to background tasks
            background_tasks.add_task(log_health_check)
            
            # Import metrics here to avoid circular imports
            from src.utils.metrics import get_health_monitor, get_metrics
            
            health_monitor = get_health_monitor()
            metrics = get_metrics()
            
            # Run comprehensive health checks
            health_results = health_monitor.run_health_checks()
            
            # Add basic application status
            app_status = {
                "bot_initialized": application and application.bot is not None,
                "uptime_seconds": metrics.get_summary()['uptime_seconds'],
                "total_requests": metrics.counters.get('http_requests_total', 0),
                "error_count": metrics.counters.get('http_errors_total', 0)
            }
            
            # Combine results
            result = {
                **health_results,
                "application": app_status,
                "metrics_summary": {
                    "counters": dict(list(metrics.counters.items())[:5]),  # Top 5 counters
                    "gauges": dict(list(metrics.gauges.items())[:5])       # Top 5 gauges
                }
            }
            
            # Record health check metric
            metrics.increment('health_checks_total')
            
            return result
            
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

    @app.get("/metrics")
    async def metrics_endpoint():
        """Metrics endpoint for monitoring systems"""
        try:
            from src.utils.metrics import get_metrics
            
            metrics = get_metrics()
            format_type = 'json'  # Could be made configurable
            
            if format_type == 'json':
                return metrics.get_summary()
            else:
                # Return Prometheus format
                from fastapi.responses import PlainTextResponse
                return PlainTextResponse(
                    content=metrics.export_metrics('prometheus'),
                    media_type='text/plain'
                )
                
        except Exception as e:
            logger.error(f"Metrics endpoint failed: {e}")
            raise HTTPException(status_code=500, detail="Metrics unavailable")

    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "Samna Salta Bot API",
            "status": "running",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "metrics": "/metrics",
                "webhook": "/webhook"
            }
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
    print(f"RENDER_EXTERNAL_URL: {os.getenv('RENDER_EXTERNAL_URL', 'Not set')}")
    
    # Ensure required environment variables are set
    required_vars = ['BOT_TOKEN', 'ADMIN_CHAT_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        print("Please set these variables in your Render environment settings.")
        return 1
    
    # Determine if we should run in webhook mode
    # Force webhook mode if:
    # 1. WEBHOOK_MODE is explicitly set to "true"
    # 2. We're on Render (RENDER_EXTERNAL_URL is set)
    # 3. PORT is set (indicating web service deployment)
    should_use_webhook = (
        os.getenv("WEBHOOK_MODE", "false").lower() == "true" or
        os.getenv("RENDER_EXTERNAL_URL") is not None or
        os.getenv("PORT") is not None
    )
    
    if should_use_webhook:
        print("🌐 Running in WEBHOOK mode (production deployment)")
        if not os.getenv("WEBHOOK_MODE"):
            print("⚠️  WEBHOOK_MODE not set, but detected Render environment - forcing webhook mode")
    else:
        print("🔄 Running in POLLING mode (local development)")
    
    try:
        # Check if we should run in webhook mode
        if should_use_webhook:
            run_webhook()
        else:
            run_polling()
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    main() 