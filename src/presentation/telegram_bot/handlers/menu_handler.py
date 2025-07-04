"""
Clean Architecture Menu Handler

Handles menu browsing using use cases and dependency injection.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from ..keyboards.menu import (
    get_main_menu_keyboard,
    get_kubaneh_menu_keyboard,
    get_samneh_menu_keyboard,
    get_red_bisbas_menu_keyboard,
    get_direct_add_keyboard,
    get_hilbeh_menu_keyboard
)
from ....infrastructure.container.dependency_injection import get_container
from ....application.use_cases.product_catalog_use_case import ProductCatalogRequest


logger = logging.getLogger(__name__)


class MenuHandler:
    """Clean Architecture menu handler"""
    
    def __init__(self):
        self._container = get_container()
        self._product_catalog_use_case = self._container.get_product_catalog_use_case()
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def handle_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle menu-related callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        username = update.effective_user.username or "unknown"
        
        self._logger.info(f"🎯 MENU CALLBACK: User {user_id} ({username}) clicked: {data}")
        
        try:
            if data == "menu_main":
                await self._show_main_menu(query)
            elif data == "menu_kubaneh":
                await self._show_kubaneh_menu(query)
            elif data == "menu_samneh":
                await self._show_samneh_menu(query)
            elif data == "menu_red_bisbas":
                await self._show_red_bisbas_menu(query)
            elif data == "menu_hilbeh":
                await self._show_hilbeh_menu(query)
            elif data == "menu_hawaij_soup":
                await self._show_hawaij_soup_menu(query)
            elif data == "menu_hawaij_coffee":
                await self._show_hawaij_coffee_menu(query)
            elif data == "menu_white_coffee":
                await self._show_white_coffee_menu(query)
            else:
                self._logger.warning(f"⚠️ UNKNOWN MENU CALLBACK: {data}")
                await query.edit_message_text("Menu functionality available!")
                
        except Exception as e:
            self._logger.error(f"💥 MENU CALLBACK ERROR: User {user_id}, Data: {data}, Error: {e}", exc_info=True)
            await query.edit_message_text("An error occurred. Please try again.")
    
    async def _show_main_menu(self, query):
        """Show the main menu"""
        self._logger.debug("📋 SHOWING: Main menu")
        await query.edit_message_text(
            "What would you like to order today?",
            reply_markup=get_main_menu_keyboard()
        )
    
    async def _show_kubaneh_menu(self, query):
        """Show Kubaneh sub-menu"""
        self._logger.debug("📋 SHOWING: Kubaneh menu")
        text = (
            "🍞 **Kubaneh Selection**\n\n"
            "Choose your preferred Kubaneh type:\n\n"
            "• **Classic** - Traditional plain Kubaneh\n"
            "• **Seeded** - With various seeds\n"
            "• **Herb** - Infused with herbs\n"
            "• **Aromatic** - Special spice blend\n\n"
            "*Price: 25 ILS per Kubaneh*"
        )
        await query.edit_message_text(
            text,
            reply_markup=get_kubaneh_menu_keyboard(),
            parse_mode='Markdown'
        )
    
    async def _show_samneh_menu(self, query):
        """Show Samneh sub-menu"""
        self._logger.debug("📋 SHOWING: Samneh menu")
        text = (
            "🧈 **Samneh Selection**\n\n"
            "Choose your preferred Samneh type:\n\n"
            "• **Smoked** - Traditional smoked butter\n"
            "• **Not smoked** - Pure clarified butter\n\n"
            "*Price: 15 ILS*"
        )
        await query.edit_message_text(
            text,
            reply_markup=get_samneh_menu_keyboard(),
            parse_mode='Markdown'
        )
    
    async def _show_red_bisbas_menu(self, query):
        """Show Red Bisbas menu"""
        self._logger.debug("📋 SHOWING: Red Bisbas menu")
        text = (
            "🌶️ **Red Bisbas (Schug)**\n\n"
            "Traditional Yemenite hot sauce\n\n"
            "*Price: 12 ILS*"
        )
        await query.edit_message_text(
            text,
            reply_markup=get_red_bisbas_menu_keyboard(),
            parse_mode='Markdown'
        )
    
    async def _show_hilbeh_menu(self, query):
        """Show Hilbeh menu with availability check"""
        self._logger.debug("📋 SHOWING: Hilbeh menu")
        try:
            # Check availability using use case
            request = ProductCatalogRequest(product_name="Hilbeh")
            response = await self._product_catalog_use_case.check_availability(request)
            
            if not response.success:
                await query.edit_message_text(
                    f"❌ {response.error_message}",
                    reply_markup=get_main_menu_keyboard()
                )
                return
            
            text = (
                "🌿 **Hilbeh**\n\n"
                "Traditional Yemenite fenugreek paste\n\n"
                "Available today! ✅\n\n"
                "*Price: 18 ILS*"
            )
            await query.edit_message_text(
                text,
                reply_markup=get_hilbeh_menu_keyboard(),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self._logger.error(f"💥 Error checking Hilbeh availability: {e}")
            await query.edit_message_text(
                "Error checking availability. Please try again.",
                reply_markup=get_main_menu_keyboard()
            )
    
    async def _show_hawaij_soup_menu(self, query):
        """Show Hawaij soup spice menu"""
        self._logger.debug("📋 SHOWING: Hawaij soup menu")
        text = (
            "🥘 **Hawaij Soup Spice**\n\n"
            "Traditional Yemenite soup spice blend\n"
            "Perfect for hearty soups and stews\n\n"
            "*Price: 8 ILS*"
        )
        await query.edit_message_text(
            text,
            reply_markup=get_direct_add_keyboard("Hawaij soup spice"),
            parse_mode='Markdown'
        )
    
    async def _show_hawaij_coffee_menu(self, query):
        """Show Hawaij coffee spice menu"""
        self._logger.debug("📋 SHOWING: Hawaij coffee menu")
        text = (
            "☕ **Hawaij Coffee Spice**\n\n"
            "Traditional Yemenite coffee spice blend\n"
            "Adds warmth and depth to your coffee\n\n"
            "*Price: 8 ILS*"
        )
        await query.edit_message_text(
            text,
            reply_markup=get_direct_add_keyboard("Hawaij coffee spice"),
            parse_mode='Markdown'
        )
    
    async def _show_white_coffee_menu(self, query):
        """Show White coffee menu"""
        self._logger.debug("📋 SHOWING: White coffee menu")
        text = (
            "☕ **White Coffee**\n\n"
            "Traditional Yemenite white coffee\n"
            "Caffeine-free, aromatic beverage\n\n"
            "*Price: 10 ILS*"
        )
        await query.edit_message_text(
            text,
            reply_markup=get_direct_add_keyboard("White coffee"),
            parse_mode='Markdown'
        )


def register_menu_handlers(application):
    """Register menu handlers"""
    handler = MenuHandler()
    
    application.add_handler(CallbackQueryHandler(
        handler.handle_menu_callback, 
        pattern="^menu_"
    )) 