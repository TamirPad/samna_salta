"""
Clean Architecture Telegram Bot Handlers

Central registration point for all Clean Architecture handlers.
"""

from telegram.ext import Application

from .admin_handler import register_admin_handlers
from .cart_handler import register_cart_handlers
from .menu_handler import register_menu_handlers
from .onboarding_handler import register_onboarding_handlers


def register_handlers(application: Application):
    """Register all Clean Architecture bot handlers"""
    register_onboarding_handlers(application)
    register_menu_handlers(application)
    register_cart_handlers(application)
    register_admin_handlers(application)
