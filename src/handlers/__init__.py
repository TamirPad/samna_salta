"""
Telegram Bot Handlers

Central registration point for all bot handlers.
"""

from telegram.ext import Application

from .start import register_start_handlers
from .menu import register_menu_handlers
# Cart handlers are now registered directly in main.py
from .admin import register_admin_handlers


def register_handlers(application: Application):
    """Register all bot handlers"""
    register_start_handlers(application)
    register_menu_handlers(application)
    # Cart handlers are registered directly in main.py
    register_admin_handlers(application)
