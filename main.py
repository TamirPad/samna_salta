#!/usr/bin/env python3
"""
Main entry point for the Samna Salta Telegram Bot
"""

import logging
import sys
from pathlib import Path

# Add current directory to Python path for deployment
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from telegram.ext import Application, ContextTypes

from src.infrastructure.configuration.config import get_config
from src.infrastructure.container.dependency_injection import initialize_container
from src.infrastructure.database.operations import init_db
from src.infrastructure.logging.logging_config import ProductionLogger
from src.presentation.telegram_bot.handlers import register_handlers

# Load environment variables
load_dotenv()


def main():
    """Main function to run the bot"""
    # Setup production logging
    ProductionLogger.setup_logging()
    logger = logging.getLogger(__name__)

    # Log Python version for debugging
    python_version = sys.version_info
    logger.info(
        f"Starting bot with Python {python_version.major}.{python_version.minor}.{python_version.micro}"
    )

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

        # Add error handler for application-level errors
        async def error_handler(
            update: object, context: ContextTypes.DEFAULT_TYPE
        ) -> None:
            """Central error handler – logs and tries to notify the user."""
            logger.error("Exception while handling an update: %s", context.error, exc_info=True)

            # Ignore polling conflicts gracefully
            if "Conflict: terminated by other getUpdates request" in str(context.error):
                logger.warning("Bot conflict detected – another instance may be running")
                return

            # Determine the Telegram user (Update or CallbackQuery)
            tg_user = None
            if update is not None:
                if hasattr(update, "effective_user") and update.effective_user:
                    tg_user = update.effective_user
                elif hasattr(update, "from_user") and update.from_user:  # CallbackQuery
                    tg_user = update.from_user

            # Attempt to notify the user
            if tg_user is not None:
                try:
                    if hasattr(update, "message") and update.message:
                        await update.message.reply_text(
                            "Sorry, something went wrong. Please try again."
                        )
                    elif hasattr(update, "callback_query") and update.callback_query:
                        await update.callback_query.message.reply_text(
                            "Sorry, something went wrong. Please try again."
                        )
                    elif hasattr(update, "answer"):
                        # Fallback for bare CallbackQuery objects passed erroneously
                        await update.answer(text="An error occurred. Please try again.")
                except Exception as send_err:  # pragma: no cover
                    logger.error("Failed to send error message to user: %s", send_err)

        # Register the error handler
        application.add_error_handler(error_handler)

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

        # Run polling with error handling and retry logic
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                logger.info(
                    f"Starting polling (attempt {retry_count + 1}/{max_retries})..."
                )
                application.run_polling(
                    allowed_updates=["message", "callback_query"],
                    drop_pending_updates=True,
                )
                break  # If successful, exit the retry loop

            except Exception as e:
                retry_count += 1
                if "Conflict: terminated by other getUpdates request" in str(e):
                    logger.warning(
                        f"Bot conflict detected on attempt {retry_count}. Waiting 30 seconds before retry..."
                    )
                    if retry_count < max_retries:
                        import time

                        time.sleep(30)  # Wait 30 seconds before retrying
                    else:
                        logger.error(
                            "Max retries reached. Bot conflict could not be resolved."
                        )
                        raise
                else:
                    logger.error(f"Unexpected error on attempt {retry_count}: {e}")
                    if retry_count >= max_retries:
                        raise

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
