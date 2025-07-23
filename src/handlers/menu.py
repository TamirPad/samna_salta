"""
Menu Handler for the Telegram bot.
"""

import logging

from telegram import CallbackQuery, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import BadRequest

from src.container import get_container
from src.utils.error_handler import BusinessLogicError
from src.keyboards.menu_keyboards import (
    get_direct_add_keyboard,
    get_hilbeh_menu_keyboard,
    get_kubaneh_menu_keyboard,
    get_red_bisbas_menu_keyboard,
    get_samneh_menu_keyboard,
    get_dynamic_main_menu_keyboard,
    get_category_menu_keyboard,
)
from src.utils.i18n import i18n
from src.utils.helpers import translate_category_name
from src.utils.constants import ErrorMessages
from src.utils.language_manager import language_manager
from src.db.operations import get_localized_name, get_localized_description, get_localized_category_name

logger = logging.getLogger(__name__)


class MenuHandler:
    """Menu handler for product browsing"""

    def __init__(self):
        self.container = get_container()
        self.order_service = self.container.get_order_service()
        self.logger = logging.getLogger(self.__class__.__name__)

    async def _safe_edit_message(self, query: CallbackQuery, text: str, reply_markup=None, parse_mode="HTML"):
        """Safely edit a message, handling both text and photo messages"""
        try:
            # Check if the current message is a photo message
            if query.message.photo:
                # For photo messages, we need to delete and send a new text message
                await query.message.delete()
                await query.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            else:
                # For text messages, we can edit normally
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
        except BadRequest as e:
            if "There is no text in the message to edit" in str(e):
                # Fallback: delete and send new message
                try:
                    await query.message.delete()
                except:
                    pass  # Message might already be deleted
                await query.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            else:
                raise e

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
            elif data.startswith("quick_add_"):
                # Handle quick add to cart
                product_id = int(data.replace("quick_add_", ""))
                await self._quick_add_to_cart(query, product_id)
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
            error_text = ErrorMessages.MENU_ERROR_OCCURRED
            await self._safe_edit_message(query, error_text)



    async def _quick_add_to_cart(self, query: CallbackQuery, product_id: int):
        """Quick add product to cart without showing details with multilingual support"""
        try:
            user_id = query.from_user.id
            user_language = language_manager.get_user_language(user_id)
            
            # Get product details
            from src.db.operations import get_product_by_id
            product = get_product_by_id(product_id)
            
            if not product:
                await query.answer(i18n.get_text("PRODUCT_NOT_FOUND", user_id=user_id), show_alert=True)
                return
            
            # Get localized product name
            localized_name = get_localized_name(product, user_language)
            
            # Add to cart
            cart_service = self.container.get_cart_service()
            success = cart_service.add_item(user_id, product_id, 1)
            
            if success:
                await query.answer(
                    i18n.get_text("QUICK_ADD_SUCCESS", user_id=user_id).format(name=localized_name),
                    show_alert=False
                )
            else:
                await query.answer(
                    i18n.get_text("QUICK_ADD_ERROR", user_id=user_id).format(error=i18n.get_text("ERROR_FAILED_ADD_TO_CART", user_id=user_id)),
                    show_alert=True
                )
                
        except Exception as e:
            self.logger.error("Error in quick add to cart: %s", e)
            await query.answer(i18n.get_text("QUICK_ADD_ERROR", user_id=user_id).format(error=i18n.get_text("ERROR_UNKNOWN", user_id=user_id)), show_alert=True)

    async def _show_main_menu(self, query: CallbackQuery):
        """Show the main menu"""
        self.logger.debug("📋 SHOWING: Main menu")
        user_id = query.from_user.id
        text = i18n.get_text("MENU_PROMPT", user_id=user_id)
        reply_markup = get_dynamic_main_menu_keyboard(user_id)
        await self._safe_edit_message(query, text, reply_markup, "HTML")

    async def _show_category_menu(self, query: CallbackQuery, category: str):
        """Show products in a specific category with multilingual support"""
        try:
            user_id = query.from_user.id
            user_language = language_manager.get_user_language(user_id)
            
            from src.db.operations import get_products_by_category, get_category_by_name
            from src.db.models import MenuCategory
            
            products = get_products_by_category(category)
            
            # Get localized category name
            category_obj = get_category_by_name(category)
            if category_obj:
                category_display_name = get_localized_category_name(category_obj, user_language)
            else:
                category_display_name = translate_category_name(category, user_id)
            
            if not products:
                text = i18n.get_text("CATEGORY_EMPTY", user_id=user_id).format(category=category_display_name)
                keyboard = [
                    [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await self._safe_edit_message(query, text, reply_markup, "HTML")
                return
            
            text = i18n.get_text("CATEGORY_TITLE", user_id=user_id).format(
                category=category_display_name, count=len(products)
            )
            reply_markup = get_category_menu_keyboard(category, user_id)
            await self._safe_edit_message(query, text, reply_markup, "HTML")
            
        except Exception as e:
            self.logger.error("Error showing category menu: %s", e)
            error_text = i18n.get_text("MENU_ERROR_OCCURRED", user_id=user_id)
            await self._safe_edit_message(query, error_text)

    async def _show_product_details(self, query: CallbackQuery, product_id: int):
        """Show detailed product information with image"""
        try:
            user_id = query.from_user.id
            from src.db.operations import get_product_by_id
            from src.utils.image_handler import get_product_image
            
            product = get_product_by_id(product_id)
            
            if not product:
                text = i18n.get_text("PRODUCT_NOT_FOUND", user_id=user_id)
                keyboard = [
                    [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await self._safe_edit_message(query, text, reply_markup, "HTML")
                return
            
            # Get product image URL
            category_name = product.category or "other"
            image_url = get_product_image(product.image_url, category_name)
            
            # Format product details with better spacing
            text = i18n.get_text("PRODUCT_DETAILS_TITLE", user_id=user_id).format(name=product.name)
            text += f"\n\n📄 <b>{i18n.get_text('PRODUCT_DESCRIPTION', user_id=user_id)}:</b>\n{product.description or i18n.get_text('NO_DESCRIPTION', user_id=user_id)}"
            text += f"\n\n💰 <b>{i18n.get_text('PRODUCT_PRICE', user_id=user_id)}:</b> ₪{product.price:.2f}"
            text += f"\n📂 <b>{i18n.get_text('PRODUCT_CATEGORY', user_id=user_id)}:</b> {translate_category_name(product.category, user_id) if product.category else i18n.get_text('UNCATEGORIZED', user_id=user_id)}"
            
            # Create keyboard with add to cart and back options
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADD_TO_CART", user_id=user_id),
                        callback_data=f"add_product_{product_id}"
                    )
                ]
            ]
            
            # Add back to category button if product has a category
            if product.category:
                keyboard.append([
                    InlineKeyboardButton(
                        i18n.get_text("BACK_TO_CATEGORY", user_id=user_id).format(category=translate_category_name(product.category, user_id)),
                        callback_data=f"category_{product.category}"
                    )
                ])
            
            # Always add back to main menu option
            keyboard.append([
                InlineKeyboardButton(
                    i18n.get_text("BACK_MAIN_MENU", user_id=user_id),
                    callback_data="menu_main"
                )
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send photo with caption if image URL exists, otherwise send text
            if image_url and image_url != get_product_image(None, category_name):
                try:
                    await query.message.delete()  # Delete the previous text message
                    await query.message.reply_photo(
                        photo=image_url,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                except Exception as photo_error:
                    self.logger.warning("Failed to send photo, falling back to text: %s", photo_error)
                    await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing product details: %s", e)
            error_text = i18n.get_text("MENU_ERROR_OCCURRED", user_id=user_id)
            await self._safe_edit_message(query, error_text)

    async def _show_kubaneh_menu(self, query: CallbackQuery):
        """Show Kubaneh sub-menu"""
        self.logger.debug("📋 SHOWING: Kubaneh menu")
        user_id = query.from_user.id
        text = i18n.get_text("KUBANEH_DESC", user_id=user_id)
        reply_markup = get_kubaneh_menu_keyboard(user_id)
        await self._safe_edit_message(query, text, reply_markup, "HTML")

    async def _show_samneh_menu(self, query: CallbackQuery):
        """Show Samneh sub-menu"""
        self.logger.debug("📋 SHOWING: Samneh menu")
        user_id = query.from_user.id
        text = i18n.get_text("SAMNEH_DESC", user_id=user_id)
        reply_markup = get_samneh_menu_keyboard(user_id)
        await self._safe_edit_message(query, text, reply_markup, "HTML")

    async def _show_red_bisbas_menu(self, query: CallbackQuery):
        """Show Red Bisbas menu"""
        self.logger.debug("📋 SHOWING: Red Bisbas menu")
        user_id = query.from_user.id
        text = i18n.get_text("RED_BISBAS_DESC", user_id=user_id)
        reply_markup = get_red_bisbas_menu_keyboard(user_id)
        await self._safe_edit_message(query, text, reply_markup, "HTML")

    async def _show_hilbeh_menu(self, query: CallbackQuery):
        """Show Hilbeh menu"""
        self.logger.debug("📋 SHOWING: Hilbeh menu")
        user_id = query.from_user.id
        text = i18n.get_text("HILBEH_DESC", user_id=user_id)
        reply_markup = get_hilbeh_menu_keyboard(user_id)
        await self._safe_edit_message(query, text, reply_markup, "HTML")

    async def _show_hawaij_soup_menu(self, query: CallbackQuery):
        """Show Hawaij for Soup menu"""
        self.logger.debug("📋 SHOWING: Hawaij for Soup menu")
        user_id = query.from_user.id
        text = i18n.get_text("HAWAIIJ_SOUP_DESC", user_id=user_id)
        reply_markup = get_direct_add_keyboard("hawaij_soup", user_id)
        await self._safe_edit_message(query, text, reply_markup, "HTML")

    async def _show_hawaij_coffee_menu(self, query: CallbackQuery):
        """Show Hawaij for Coffee menu"""
        self.logger.debug("📋 SHOWING: Hawaij for Coffee menu")
        user_id = query.from_user.id
        text = i18n.get_text("HAWAIIJ_COFFEE_DESC", user_id=user_id)
        reply_markup = get_direct_add_keyboard("hawaij_coffee_spice", user_id)
        await self._safe_edit_message(query, text, reply_markup, "HTML")

    async def _show_white_coffee_menu(self, query: CallbackQuery):
        """Show White Coffee menu"""
        self.logger.debug("📋 SHOWING: White Coffee menu")
        user_id = query.from_user.id
        text = i18n.get_text("WHITE_COFFEE_DESC", user_id=user_id)
        reply_markup = get_direct_add_keyboard("white_coffee", user_id)
        await self._safe_edit_message(query, text, reply_markup, "HTML")


def register_menu_handlers(application: Application):
    """Register menu handlers"""
    handler = MenuHandler()

    application.add_handler(
        CallbackQueryHandler(handler.handle_menu_callback, pattern="^menu_")
    )
