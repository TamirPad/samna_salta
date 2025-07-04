"""
Admin handlers for the Samna Salta bot
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

logger = logging.getLogger(__name__)


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    # Placeholder - will be expanded with full admin logic
    await update.message.reply_text("Admin functionality coming soon!")


def register_admin_handlers(application):
    """Register admin handlers"""
    application.add_handler(CommandHandler("admin", admin_command)) 