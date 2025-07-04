"""
Telegram bot handlers
"""

from telegram.ext import Application

from .onboarding import register_onboarding_handlers
from .menu import register_menu_handlers
from .cart import register_cart_handlers
from .admin import register_admin_handlers


def register_handlers(application: Application):
    """Register all bot handlers"""
    register_onboarding_handlers(application)
    register_menu_handlers(application)
    register_cart_handlers(application)
    register_admin_handlers(application) 