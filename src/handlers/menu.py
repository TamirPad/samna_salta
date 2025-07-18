"""
Menu Handler for the Telegram bot.
"""

import logging

from telegram import CallbackQuery, Update, InlineKeyboardButton, InlineKeyboardMarkup
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
    get_dynamic_main_menu_keyboard,
    get_category_menu_keyboard,
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
            elif data.startswith("category_"):
                # Handle category menu
                category = data.replace("category_", "")
                await self._show_category_menu(query, category)
            elif data.startswith("product_"):
                # Handle product selection
                product_id = int(data.replace("product_", ""))
                await self._show_product_details(query, product_id)
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
        user_id = query.from_user.id
        await query.edit_message_text(
            i18n.get_text("MENU_PROMPT", user_id=user_id), 
            reply_markup=get_dynamic_main_menu_keyboard(user_id), 
            parse_mode="HTML"
        )

    async def _show_kubaneh_menu(self, query: CallbackQuery):
        """Show Kubaneh sub-menu"""
        self.logger.debug("📋 SHOWING: Kubaneh menu")
        user_id = query.from_user.id
        text = i18n.get_text("KUBANEH_DESC", user_id=user_id)
        await query.edit_message_text(
            text, reply_markup=get_kubaneh_menu_keyboard(user_id), parse_mode="HTML"
        )

    async def _show_samneh_menu(self, query: CallbackQuery):
        """Show Samneh sub-menu"""
        self.logger.debug("📋 SHOWING: Samneh menu")
        user_id = query.from_user.id
        text = i18n.get_text("SAMNEH_DESC", user_id=user_id)
        await query.edit_message_text(
            text, reply_markup=get_samneh_menu_keyboard(user_id), parse_mode="HTML"
        )

    async def _show_red_bisbas_menu(self, query: CallbackQuery):
        """Show Red Bisbas menu"""
        self.logger.debug("📋 SHOWING: Red Bisbas menu")
        user_id = query.from_user.id
        text = i18n.get_text("RED_BISBAS_DESC", user_id=user_id)
        await query.edit_message_text(
            text, reply_markup=get_red_bisbas_menu_keyboard(user_id), parse_mode="HTML"
        )

    async def _show_hilbeh_menu(self, query: CallbackQuery):
        """Show Hilbeh menu with availability check"""
        self.logger.debug("📋 SHOWING: Hilbeh menu")
        user_id = query.from_user.id
        try:
            # Check availability using order service
            availability = self.order_service.check_product_availability("Hilbeh")

            if not availability["available"]:
                await query.edit_message_text(
                    i18n.get_text("AVAILABILITY_CHECK_ERROR", user_id=user_id).format(error=availability["reason"]), 
                    reply_markup=get_main_menu_keyboard(user_id),
                    parse_mode="HTML"
                )
                return

            text = i18n.get_text("HILBEH_DESC_AVAILABLE", user_id=user_id)
            await query.edit_message_text(
                text, reply_markup=get_hilbeh_menu_keyboard(user_id), parse_mode="HTML"
            )

        except Exception as e:
            self.logger.error("💥 Error checking Hilbeh availability: %s", e)
            await query.edit_message_text(
                i18n.get_text("AVAILABILITY_CHECK_ERROR_GENERIC", user_id=user_id),
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode="HTML"
            )

    async def _show_hawaij_soup_menu(self, query: CallbackQuery):
        """Show Hawaij soup spice menu"""
        self.logger.debug("📋 SHOWING: Hawaij soup menu")
        user_id = query.from_user.id
        text = i18n.get_text("HAWAIJ_SOUP_DESC", user_id=user_id)
        await query.edit_message_text(
            text,
            reply_markup=get_direct_add_keyboard("Hawaij soup spice", include_info=False, user_id=user_id),
            parse_mode="HTML",
        )

    async def _show_hawaij_coffee_menu(self, query: CallbackQuery):
        """Show Hawaij coffee spice menu"""
        self.logger.debug("📋 SHOWING: Hawaij coffee menu")
        user_id = query.from_user.id
        text = i18n.get_text("HAWAIJ_COFFEE_DESC", user_id=user_id)
        await query.edit_message_text(
            text,
            reply_markup=get_direct_add_keyboard("Hawaij coffee spice", include_info=False, user_id=user_id),
            parse_mode="HTML",
        )

    async def _show_white_coffee_menu(self, query: CallbackQuery):
        """Show White coffee menu"""
        self.logger.debug("📋 SHOWING: White coffee menu")
        user_id = query.from_user.id
        text = i18n.get_text("WHITE_COFFEE_DESC", user_id=user_id)
        await query.edit_message_text(
            text,
            reply_markup=get_direct_add_keyboard("White coffee", include_info=False, user_id=user_id),
            parse_mode="HTML",
        )

    async def _show_category_menu(self, query: CallbackQuery, category: str):
        """Show menu for a specific category"""
        self.logger.debug("📋 SHOWING: Category menu for %s", category)
        user_id = query.from_user.id
        text = f"📂 <b>{category.title()}</b>\n\n{i18n.get_text('MENU_PROMPT', user_id=user_id)}"
        await query.edit_message_text(
            text,
            reply_markup=get_category_menu_keyboard(category, user_id),
            parse_mode="HTML"
        )

    async def _show_product_details(self, query: CallbackQuery, product_id: int):
        """Show product details and add to cart option"""
        self.logger.debug("📋 SHOWING: Product details for ID %d", product_id)
        user_id = query.from_user.id
        
        try:
            # Get product from database
            from src.db.operations import get_product_by_id
            product = get_product_by_id(product_id)
            
            if not product:
                await query.edit_message_text(
                    "❌ Product not found",
                    reply_markup=get_dynamic_main_menu_keyboard(user_id)
                )
                return
            
            # Create product details text
            text = f"<b>{product.name}</b>\n\n"
            if product.description:
                text += f"{product.description}\n\n"
            text += f"💰 Price: ₪{product.price:.2f}\n"
            if product.category:
                text += f"📂 Category: {product.category.title()}\n"
            
            # Create keyboard with add to cart button
            keyboard = [
                [InlineKeyboardButton(
                    f"🛒 Add to Cart - ₪{product.price:.2f}",
                    callback_data=f"add_product_{product_id}"
                )],
                [InlineKeyboardButton(
                    i18n.get_text("BACK_MAIN_MENU", user_id=user_id),
                    callback_data="menu_main"
                )]
            ]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            
        except Exception as e:
            self.logger.error("Error showing product details: %s", e)
            await query.edit_message_text(
                "❌ Error loading product details",
                reply_markup=get_dynamic_main_menu_keyboard(user_id)
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
