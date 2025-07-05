"""
Clean Architecture Menu Handler

Handles menu browsing using use cases and dependency injection.
"""

import logging

from telegram import CallbackQuery, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from src.application.use_cases.product_catalog_use_case import ProductCatalogRequest
from src.infrastructure.container.dependency_injection import get_container
from src.infrastructure.utilities.exceptions import BusinessLogicError
from src.presentation.telegram_bot.keyboards.menu import (
    get_direct_add_keyboard,
    get_hilbeh_menu_keyboard,
    get_kubaneh_menu_keyboard,
    get_main_menu_keyboard,
    get_red_bisbas_menu_keyboard,
    get_samneh_menu_keyboard,
)
from src.infrastructure.utilities.i18n import tr

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class MenuHandler:
    """Clean Architecture menu handler"""

    def __init__(self):
        self._container = get_container()
        self._product_catalog_use_case = self._container.get_product_catalog_use_case()
        self._logger = logging.getLogger(self.__class__.__name__)

    async def handle_menu_callback(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """Handle menu-related callbacks"""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = update.effective_user.id
        username = update.effective_user.username or "unknown"

        self._logger.info(
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
                self._logger.warning("⚠️ UNKNOWN MENU CALLBACK: %s", data)
                await query.edit_message_text(tr("MENU_FUNCTIONALITY_AVAILABLE"))

        except BusinessLogicError as e:
            self._logger.error(
                "💥 MENU CALLBACK ERROR: User %s, Data: %s, Error: %s",
                user_id,
                data,
                e,
                exc_info=True,
            )
            await query.edit_message_text(tr("MENU_ERROR_OCCURRED"))

    async def _show_main_menu(self, query: CallbackQuery):
        """Show the main menu"""
        self._logger.debug("📋 SHOWING: Main menu")
        await query.edit_message_text(
            tr("MENU_PROMPT"), reply_markup=get_main_menu_keyboard()
        )

    async def _show_kubaneh_menu(self, query: CallbackQuery):
        """Show Kubaneh sub-menu"""
        self._logger.debug("📋 SHOWING: Kubaneh menu")
        text = tr("KUBANEH_DESC")
        await query.edit_message_text(
            text, reply_markup=get_kubaneh_menu_keyboard(), parse_mode="Markdown"
        )

    async def _show_samneh_menu(self, query: CallbackQuery):
        """Show Samneh sub-menu"""
        self._logger.debug("📋 SHOWING: Samneh menu")
        text = tr("SAMNEH_DESC")
        await query.edit_message_text(
            text, reply_markup=get_samneh_menu_keyboard(), parse_mode="Markdown"
        )

    async def _show_red_bisbas_menu(self, query: CallbackQuery):
        """Show Red Bisbas menu"""
        self._logger.debug("📋 SHOWING: Red Bisbas menu")
        text = tr("RED_BISBAS_DESC")
        await query.edit_message_text(
            text, reply_markup=get_red_bisbas_menu_keyboard(), parse_mode="Markdown"
        )

    async def _show_hilbeh_menu(self, query: CallbackQuery):
        """Show Hilbeh menu with availability check"""
        self._logger.debug("📋 SHOWING: Hilbeh menu")
        try:
            # Check availability using use case
            request = ProductCatalogRequest(product_name="Hilbeh")
            response = await self._product_catalog_use_case.check_availability(request)

            if not response.success:
                await query.edit_message_text(
                    tr("AVAILABILITY_CHECK_ERROR").format(error=response.error_message), reply_markup=get_main_menu_keyboard()
                )
                return

            text = tr("HILBEH_DESC_AVAILABLE")
            await query.edit_message_text(
                text, reply_markup=get_hilbeh_menu_keyboard(), parse_mode="Markdown"
            )

        except BusinessLogicError as e:
            self._logger.error("💥 Error checking Hilbeh availability: %s", e)
            await query.edit_message_text(
                tr("AVAILABILITY_CHECK_ERROR_GENERIC"),
                reply_markup=get_main_menu_keyboard(),
            )

    async def _show_hawaij_soup_menu(self, query: CallbackQuery):
        """Show Hawaij soup spice menu"""
        self._logger.debug("📋 SHOWING: Hawaij soup menu")
        text = tr("HAWAIJ_SOUP_DESC")
        await query.edit_message_text(
            text,
            reply_markup=get_direct_add_keyboard("Hawaij soup spice"),
            parse_mode="Markdown",
        )

    async def _show_hawaij_coffee_menu(self, query: CallbackQuery):
        """Show Hawaij coffee spice menu"""
        self._logger.debug("📋 SHOWING: Hawaij coffee menu")
        text = tr("HAWAIJ_COFFEE_DESC")
        await query.edit_message_text(
            text,
            reply_markup=get_direct_add_keyboard("Hawaij coffee spice", include_info=False),
            parse_mode="Markdown",
        )

    async def _show_white_coffee_menu(self, query: CallbackQuery):
        """Show White coffee menu"""
        self._logger.debug("📋 SHOWING: White coffee menu")
        text = tr("WHITE_COFFEE_DESC")
        await query.edit_message_text(
            text,
            reply_markup=get_direct_add_keyboard("White coffee", include_info=False),
            parse_mode="Markdown",
        )


def register_menu_handlers(application: Application):
    """Register menu handlers"""
    handler = MenuHandler()

    application.add_handler(
        CallbackQueryHandler(handler.handle_menu_callback, pattern="^menu_")
    )
