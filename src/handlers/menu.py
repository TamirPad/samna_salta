"""
Menu Handler for the Telegram bot.
"""

import logging

from telegram import CallbackQuery, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from src.container import get_container
from src.utils.error_handler import BusinessLogicError
from src.keyboards.menu_keyboards import (
    get_direct_add_keyboard,
    get_hilbeh_menu_keyboard,
    get_kubaneh_menu_keyboard,
    get_main_menu_keyboard,
    get_red_bisbas_menu_keyboard,
    get_samneh_menu_keyboard,
)
from src.utils.i18n import i18n
from src.utils.constants import CallbackPatterns, ErrorMessages

logger = logging.getLogger(__name__)


class MenuHandler:
    """Menu handler for product browsing"""

    def __init__(self):
        self.container = get_container()
        self.order_service = self.container.get_order_service()
        self.logger = logging.getLogger(self.__class__.__name__)

    async def handle_menu_callback(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """Handle menu-related callbacks"""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = update.effective_user.id
        username = update.effective_user.username or "unknown"

        self.logger.info(
            "🎯 MENU CALLBACK: User %s (%s) clicked: %s", user_id, username, data
        )

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
                self.logger.warning("⚠️ UNKNOWN MENU CALLBACK: %s", data)
                await query.edit_message_text(ErrorMessages.MENU_FUNCTIONALITY_AVAILABLE)

        except BusinessLogicError as e:
            self.logger.error(
                "💥 MENU CALLBACK ERROR: User %s, Data: %s, Error: %s",
                user_id,
                data,
                e,
                exc_info=True,
            )
            await query.edit_message_text(ErrorMessages.MENU_ERROR_OCCURRED)

    async def _show_main_menu(self, query: CallbackQuery):
        """Show the main menu"""
        self.logger.debug("📋 SHOWING: Main menu")
        await query.edit_message_text(
            i18n.get_text("MENU_PROMPT"), reply_markup=get_main_menu_keyboard(), parse_mode="HTML"
        )

    async def _show_kubaneh_menu(self, query: CallbackQuery):
        """Show Kubaneh sub-menu"""
        self.logger.debug("📋 SHOWING: Kubaneh menu")
        text = i18n.get_text("KUBANEH_DESC")
        await query.edit_message_text(
            text, reply_markup=get_kubaneh_menu_keyboard(), parse_mode="HTML"
        )

    async def _show_samneh_menu(self, query: CallbackQuery):
        """Show Samneh sub-menu"""
        self.logger.debug("📋 SHOWING: Samneh menu")
        text = i18n.get_text("SAMNEH_DESC")
        await query.edit_message_text(
            text, reply_markup=get_samneh_menu_keyboard(), parse_mode="HTML"
        )

    async def _show_red_bisbas_menu(self, query: CallbackQuery):
        """Show Red Bisbas menu"""
        self.logger.debug("📋 SHOWING: Red Bisbas menu")
        text = i18n.get_text("RED_BISBAS_DESC")
        await query.edit_message_text(
            text, reply_markup=get_red_bisbas_menu_keyboard(), parse_mode="HTML"
        )

    async def _show_hilbeh_menu(self, query: CallbackQuery):
        """Show Hilbeh menu with availability check"""
        self.logger.debug("📋 SHOWING: Hilbeh menu")
        try:
            # Check availability using order service
            availability = self.order_service.check_product_availability("Hilbeh")

            if not availability["available"]:
                await query.edit_message_text(
                    i18n.get_text("AVAILABILITY_CHECK_ERROR").format(error=availability["reason"]), 
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="HTML"
                )
                return

            text = i18n.get_text("HILBEH_DESC_AVAILABLE")
            await query.edit_message_text(
                text, reply_markup=get_hilbeh_menu_keyboard(), parse_mode="HTML"
            )

        except Exception as e:
            self.logger.error("💥 Error checking Hilbeh availability: %s", e)
            await query.edit_message_text(
                i18n.get_text("AVAILABILITY_CHECK_ERROR_GENERIC"),
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )

    async def _show_hawaij_soup_menu(self, query: CallbackQuery):
        """Show Hawaij soup spice menu"""
        self.logger.debug("📋 SHOWING: Hawaij soup menu")
        text = i18n.get_text("HAWAIJ_SOUP_DESC")
        await query.edit_message_text(
            text,
            reply_markup=get_direct_add_keyboard("Hawaij soup spice", include_info=False),
            parse_mode="HTML",
        )

    async def _show_hawaij_coffee_menu(self, query: CallbackQuery):
        """Show Hawaij coffee spice menu"""
        self.logger.debug("📋 SHOWING: Hawaij coffee menu")
        text = i18n.get_text("HAWAIJ_COFFEE_DESC")
        await query.edit_message_text(
            text,
            reply_markup=get_direct_add_keyboard("Hawaij coffee spice", include_info=False),
            parse_mode="HTML",
        )

    async def _show_white_coffee_menu(self, query: CallbackQuery):
        """Show White coffee menu"""
        self.logger.debug("📋 SHOWING: White coffee menu")
        text = i18n.get_text("WHITE_COFFEE_DESC")
        await query.edit_message_text(
            text,
            reply_markup=get_direct_add_keyboard("White coffee", include_info=False),
            parse_mode="HTML",
        )


def register_menu_handlers(application: Application):
    """Register menu handlers"""
    handler = MenuHandler()

    application.add_handler(
        CallbackQueryHandler(handler.handle_menu_callback, pattern="^menu_")
    )


# Handler function for direct registration
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu handler for direct registration"""
    handler = MenuHandler()
    return await handler.handle_menu_callback(update, context)
