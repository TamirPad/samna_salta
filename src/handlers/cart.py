"""
Cart handler for managing shopping cart operations
"""

import logging
from typing import Dict, Any, Optional, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes, filters, Application

from src.container import get_container
from src.utils.i18n import i18n
from src.utils.error_handler import handle_error
from src.utils.constants_manager import get_delivery_method_name

logger = logging.getLogger(__name__)


def expecting_delivery_address_filter(update, context):
    return bool(context.user_data.get('expecting_delivery_address'))


def register_cart_handlers(application: Application):
    """Register cart handlers with the application"""
    cart_handler = CartHandler()
    
    # Register callback query handlers
    application.add_handler(
        filters.CallbackQuery("add_to_cart_", prefix=True),
        cart_handler.handle_add_to_cart
    )
    application.add_handler(
        filters.CallbackQuery("view_cart"),
        cart_handler.handle_view_cart
    )
    application.add_handler(
        filters.CallbackQuery("clear_cart_confirm"),
        cart_handler.handle_clear_cart_confirmation
    )
    application.add_handler(
        filters.CallbackQuery("clear_cart"),
        cart_handler.handle_clear_cart
    )
    application.add_handler(
        filters.CallbackQuery("checkout"),
        cart_handler.handle_checkout
    )
    application.add_handler(
        filters.CallbackQuery("cart_decrease_", prefix=True),
        cart_handler.handle_decrease_quantity
    )
    application.add_handler(
        filters.CallbackQuery("cart_increase_", prefix=True),
        cart_handler.handle_increase_quantity
    )
    application.add_handler(
        filters.CallbackQuery("cart_remove_", prefix=True),
        cart_handler.handle_remove_item
    )
    application.add_handler(
        filters.CallbackQuery("cart_edit_", prefix=True),
        cart_handler.handle_edit_quantity
    )
    application.add_handler(
        filters.CallbackQuery("cart_info_", prefix=True),
        cart_handler.handle_item_info
    )
    application.add_handler(
        filters.CallbackQuery("cart_separator"),
        cart_handler.handle_separator
    )
    application.add_handler(
        filters.CallbackQuery("delivery_method_", prefix=True),
        cart_handler.handle_delivery_method
    )
    application.add_handler(
        filters.CallbackQuery("delivery_address_", prefix=True),
        cart_handler.handle_delivery_address_choice
    )
    application.add_handler(
        filters.CallbackQuery("confirm_order"),
        cart_handler.handle_confirm_order
    )
    
    # Register message handler for delivery address input
    application.add_handler(
        filters.TEXT & filters.ChatType.PRIVATE & filters.CREATE,
        cart_handler.handle_delivery_address_input
    )


class CartHandler:
    """Handler for cart-related operations"""

    def __init__(self):
        self.container = get_container()
        self.logger = logger

    async def _safe_edit_message(self, query, text, **kwargs):
        """Safely update the existing message (text or caption); delete and send new message as last resort"""
        try:
            if query.message:
                # Prefer editing text messages
                if getattr(query.message, "text", None):
                    await query.edit_message_text(text, **kwargs)
                    return

                # If current message is media (photo/caption), replace it with a plain text message
                if getattr(query.message, "caption", None) is not None or getattr(query.message, "photo", None):
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                    await query.message.reply_text(text, **kwargs)
                    return

                # Fallback attempt to edit as text
                await query.edit_message_text(text, **kwargs)
                return
        except Exception as e:
            # If we cannot edit text/caption, try updating only the reply markup first
            self.logger.warning("Failed to edit message content, attempting to update keyboard: %s", e)
            try:
                if query.message and kwargs.get("reply_markup"):
                    await query.edit_message_reply_markup(reply_markup=kwargs.get("reply_markup"))
                    return
            except Exception:
                pass

        # Absolute last resort: delete the original message (to avoid duplicates) and send a new one
        try:
            if query.message:
                await query.message.delete()
        except Exception:
            pass
        await query.message.reply_text(text, **kwargs)

    async def handle_add_to_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle adding items to cart"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            callback_data = query.data

            # Parse product info from callback data
            product_info = self._parse_product_from_callback(callback_data)
            if not product_info:
                await self._safe_edit_message(
                    query,
                    "❌ Invalid product selection. Please try again.",
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_menu_keyboard(),
                )
                return

            self.logger.info("🛒 ADD TO CART: User %s clicked: %s", user_id, callback_data)
            self.logger.info("📦 PARSED PRODUCT: %s", product_info)

            # Get cart service
            cart_service = self.container.get_cart_service()

            # Add to cart using the service
            success = cart_service.add_item(
                telegram_id=user_id,
                product_id=product_info["product_id"],
                quantity=1,
                options=product_info.get("options", {}),
            )

            if success:
                # Get updated cart for summary
                cart_items = cart_service.get_items(user_id)
                cart_total = cart_service.calculate_total(cart_items)
                item_count = len(cart_items)

                self.logger.info(
                    "✅ ADD SUCCESS: %s added. Cart: %d items, ₪%.2f",
                    product_info["display_name"],
                    item_count,
                    cart_total,
                )

                # Send beautiful success message
                # Prefer multilingual fields from parsed product when available
                from src.utils.language_manager import language_manager
                user_lang = language_manager.get_user_language(user_id)
                if user_lang == "he" and product_info.get("name_he"):
                    localized_product_name = product_info["name_he"]
                elif user_lang == "en" and product_info.get("name_en"):
                    localized_product_name = product_info["name_en"]
                else:
                    localized_product_name = self._get_localized_product_name(
                        {"product_name": product_info["display_name"], "options": product_info.get('options', {})}, 
                        user_id
                    )
                
                # Format total with RTL support
                from src.utils.helpers import format_price, format_quantity
                formatted_total = format_price(cart_total, user_id)
                formatted_item_count = format_quantity(item_count, user_id)
                
                from src.utils.text_formatter import center_text
                
                from src.utils.text_formatter import format_title
                success_title = format_title(f'✅ {i18n.get_text("CART_SUCCESS_TITLE", user_id=user_id)}')
                product_name = f'📦 <b>{localized_product_name}</b>'
                added_success = i18n.get_text("CART_ADDED_SUCCESSFULLY", user_id=user_id)
                items_count = f'🛒 {i18n.get_text("CART_ITEMS_COUNT", user_id=user_id)}: {formatted_item_count}'
                total_text = f'💰 {i18n.get_text("CART_TOTAL", user_id=user_id).format(total=formatted_total)}'
                what_next = f'🎯 {i18n.get_text("CART_WHAT_NEXT_QUESTION", user_id=user_id)}'
                
                message = f"""{success_title}

{product_name}
{added_success}

{items_count}
{total_text}

{what_next}"""

                await self._safe_edit_message(
                    query,
                    message,
                    parse_mode="HTML",
                    reply_markup=self._get_cart_success_keyboard(user_id),
                )
            else:
                self.logger.error("❌ ADD FAILED: User %s, Product: %s", user_id, product_info["display_name"])
                await self._safe_edit_message(
                    query,
                    i18n.get_text("FAILED_ADD_TO_CART", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_menu_keyboard(user_id),
                )

        except Exception as e:
            self.logger.error("Exception in handle_add_to_cart: %s", e)
            await handle_error(update, e, "adding item to cart")

    async def handle_view_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle viewing cart contents"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            self.logger.info("🛒 VIEW CART: User %s", user_id)

            # Get cart service
            cart_service = self.container.get_cart_service()
            cart_items = cart_service.get_items(user_id)

            if not cart_items:
                from src.utils.text_formatter import center_text
                
                from src.utils.text_formatter import format_title
                cart_title = format_title(f'🛒 {i18n.get_text("CART_VIEW_TITLE", user_id=user_id)}')
                empty_ready = f'🤷‍♀️ {i18n.get_text("CART_EMPTY_READY", user_id=user_id)}'
                browse_suggestion = f'🍽️ {i18n.get_text("BROWSE_MENU_SUGGESTION", user_id=user_id)}'
                
                empty_cart_message = f"""{cart_title}

{empty_ready}

{browse_suggestion}"""

                await self._safe_edit_message(
                    query,
                    empty_cart_message,
                    parse_mode="HTML",
                    reply_markup=self._get_professional_empty_cart_keyboard(user_id),
                )
                return

            # Calculate total
            cart_total = cart_service.calculate_total(cart_items)

            from src.utils.text_formatter import format_title
            
            # Build beautiful cart display with centering
            message = format_title(f'🛒 {i18n.get_text("CART_VIEW_TITLE", user_id=user_id)}')
            message += "\n\n"
            
            for i, item in enumerate(cart_items, 1):
                item_total = item.get("unit_price", 0) * item.get("quantity", 1)
                # Get localized product name (prefer multilingual fields)
                name_he = item.get("name_he")
                name_en = item.get("name_en")
                from src.utils.language_manager import language_manager
                user_lang = language_manager.get_user_language(user_id)
                if user_lang == "he" and name_he:
                    localized_product_name = name_he
                elif user_lang == "en" and name_en:
                    localized_product_name = name_en
                else:
                    localized_product_name = self._get_localized_product_name(item, user_id)
                
                # Format prices and quantities with RTL support
                from src.utils.helpers import format_price, format_quantity
                formatted_unit_price = format_price(item.get('unit_price', 0), user_id)
                formatted_item_total = format_price(item_total, user_id)
                formatted_quantity = format_quantity(item.get('quantity', 1), user_id)
                
                item_text = f"""<b>{i}.</b> 📦 <b>{localized_product_name}</b>
🔢 {i18n.get_text("CART_QUANTITY_LABEL", user_id=user_id)}: {formatted_quantity}
💰 {i18n.get_text("CART_PRICE_LABEL", user_id=user_id)}: {formatted_unit_price}
💵 {i18n.get_text("CART_SUBTOTAL_LABEL", user_id=user_id)}: {formatted_item_total}"""
                message += f"\n{item_text}\n"
                
                if i < len(cart_items):
                    message += "\n"

            # Format total with RTL support
            from src.utils.helpers import format_price
            formatted_total = format_price(cart_total, user_id)
            
            from src.utils.text_formatter import format_title
            total_text = format_title(f'💸 {i18n.get_text("CART_TOTAL", user_id=user_id).format(total=formatted_total)}')
            what_next_text = f'🤔 {i18n.get_text("CART_WHAT_NEXT", user_id=user_id)}'
            message += f"\n\n{total_text}"
            message += f"\n\n{what_next_text}"

            await self._safe_edit_message(
                query,
                message,
                parse_mode="HTML",
                reply_markup=self._get_simplified_cart_keyboard(cart_items, user_id),
            )

        except Exception as e:
            self.logger.error("Exception in handle_view_cart: %s", e)
            await handle_error(update, e, "viewing cart")

    async def handle_clear_cart_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle clear cart confirmation dialog"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            self.logger.info("🗑️ CLEAR CART CONFIRMATION: User %s", user_id)

            # Show confirmation dialog
            await self._safe_edit_message(
                query,
                i18n.get_text("CLEAR_CART_CONFIRMATION", user_id=user_id),
                parse_mode="HTML",
                reply_markup=self._get_clear_cart_confirmation_keyboard(user_id),
            )

        except Exception as e:
            self.logger.error("Exception in handle_clear_cart_confirmation: %s", e)
            await handle_error(update, e, "clear cart confirmation")

    async def handle_clear_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle clearing cart after confirmation"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            self.logger.info("🗑️ CLEAR CART: User %s", user_id)

            # Get cart service
            cart_service = self.container.get_cart_service()
            success = cart_service.clear_cart(user_id)

            if success:
                self.logger.info("✅ CART CLEARED: User %s", user_id)
                await self._safe_edit_message(
                    query,
                    i18n.get_text("CART_CLEARED_SUCCESS", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_professional_empty_cart_keyboard(user_id),
                )
            else:
                self.logger.error("❌ CART CLEAR FAILED: User %s", user_id)
                await self._safe_edit_message(
                    query,
                    i18n.get_text("FAILED_CLEAR_CART", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_menu_keyboard(user_id),
                )

        except Exception as e:
            self.logger.error("Exception in handle_clear_cart: %s", e)
            await handle_error(update, e, "clearing cart")

    async def handle_checkout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle checkout process"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            self.logger.info("🛒 CHECKOUT: User %s", user_id)

            # Get cart service
            cart_service = self.container.get_cart_service()
            cart_items = cart_service.get_items(user_id)

            if not cart_items:
                await self._safe_edit_message(
                    query,
                    i18n.get_text("CART_EMPTY_CHECKOUT", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_professional_empty_cart_keyboard(user_id),
                )
                return

            # Gate: require minimal signup (phone) if guest before proceeding to delivery selection
            customer = cart_service.get_customer(user_id)
            if not (customer and getattr(customer, "phone", None) and len((customer.phone or "").strip()) >= 8):
                await self._safe_edit_message(
                    query,
                    i18n.get_text("SIGNUP_REQUIRED_TO_ORDER", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n.get_text("BUTTON_COMPLETE_SIGNUP", user_id=user_id), callback_data="quick_signup")]])
                )
                return

            # Calculate total
            cart_total = cart_service.calculate_total(cart_items)

            # Build checkout summary
            message = i18n.get_text("CHECKOUT_TITLE", user_id=user_id) + "\n\n"
            
            for i, item in enumerate(cart_items, 1):
                item_total = item.get("unit_price", 0) * item.get("quantity", 1)
                # Localize product name: prefer multilingual fields; fallback to translation helper
                name_he = item.get("name_he")
                name_en = item.get("name_en")
                from src.utils.language_manager import language_manager
                user_lang = language_manager.get_user_language(user_id)
                if user_lang == "he" and name_he:
                    translated_product_name = name_he
                elif user_lang == "en" and name_en:
                    translated_product_name = name_en
                else:
                    from src.utils.helpers import translate_product_name
                    translated_product_name = translate_product_name(item.get('product_name', i18n.get_text('PRODUCT_UNKNOWN', user_id=user_id)), item.get('options', {}), user_id)
                message += i18n.get_text("CART_ITEM_FORMAT", user_id=user_id).format(
                    index=i,
                    product_name=translated_product_name,
                    quantity=item.get('quantity', 1),
                    price=item.get('unit_price', 0),
                    item_total=item_total
                ) + "\n\n"

            message += i18n.get_text("CART_TOTAL", user_id=user_id).format(total=cart_total) + "\n\n"
            message += i18n.get_text("SELECT_DELIVERY_METHOD", user_id=user_id)

            await self._safe_edit_message(
                query,
                message,
                parse_mode="HTML",
                reply_markup=self._get_delivery_method_keyboard(user_id),
            )

        except Exception as e:
            self.logger.error("Exception in handle_checkout: %s", e)
            await handle_error(update, e, "checkout")

    async def handle_delivery_method(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle delivery method selection"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            delivery_method = query.data.replace("delivery_", "")
            self.logger.info("🚚 DELIVERY METHOD: User %s selected %s", user_id, delivery_method)

            # Get cart service
            cart_service = self.container.get_cart_service()
            # Gate for guest
            customer = cart_service.get_customer(user_id)
            if not (customer and getattr(customer, "phone", None) and len((customer.phone or "").strip()) >= 8):
                await self._safe_edit_message(
                    query,
                    i18n.get_text("SIGNUP_REQUIRED_TO_ORDER", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n.get_text("BUTTON_COMPLETE_SIGNUP", user_id=user_id), callback_data="quick_signup")]])
                )
                return
            
            # Update cart with delivery method
            success = cart_service.set_delivery_method(user_id, delivery_method)
            
            if not success:
                await self._safe_edit_message(
                    query,
                    i18n.get_text("FAILED_SET_DELIVERY", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_cart_keyboard(user_id),
                )
                return

            if delivery_method == "delivery":
                # First, prompt for delivery area (pre-step) before address
                from src.db.operations import get_active_delivery_areas
                areas = get_active_delivery_areas()
                if areas:
                    from src.utils.language_manager import language_manager
                    lang = language_manager.get_user_language(user_id)
                    buttons = []
                    for area in areas:
                        name = area.name_he if lang == "he" else area.name_en
                        buttons.append([InlineKeyboardButton(name, callback_data=f"delivery_area_{area.id}")])
                    # Add back button
                    buttons.append([InlineKeyboardButton(i18n.get_text("BACK_TO_CART", user_id=user_id), callback_data="cart_view")])
                    await self._safe_edit_message(
                        query,
                        i18n.get_text("SELECT_DELIVERY_AREA", user_id=user_id),
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(buttons),
                    )
                    return
                # Check if customer has a delivery address
                customer = cart_service.get_customer(user_id)
                
                if customer and customer.delivery_address:
                    # Customer has a saved address - ask if they want to use it
                    message = i18n.get_text("DELIVERY_ADDRESS_CURRENT", user_id=user_id).format(address=customer.delivery_address)
                    await self._safe_edit_message(
                        query,
                        message,
                        parse_mode="HTML",
                        reply_markup=self._get_delivery_address_choice_keyboard(user_id),
                    )
                else:
                    # No saved address - ask for new address
                    await self._safe_edit_message(
                        query,
                        i18n.get_text("DELIVERY_ADDRESS_REQUIRED", user_id=user_id),
                        parse_mode="HTML",
                    )
                    # Ask for address with a forced reply so the user knows to type it now
                    await query.message.reply_text(
                        i18n.get_text("DELIVERY_ADDRESS_PROMPT", user_id=user_id),
                        parse_mode="HTML",
                        reply_markup=ForceReply(selective=True),
                    )
                    # Set context to expect address input and use quick-signup input handler to capture it
                    context.user_data["expecting_delivery_address"] = True
                    context.user_data["qs_stage"] = "address"
                    return
            else:
                # Pickup - proceed to order confirmation
                await self._show_order_confirmation(query, cart_service, user_id)

        except Exception as e:
            self.logger.error("Exception in handle_delivery_method: %s", e)
            await handle_error(update, e, "delivery method selection")

    async def handle_delivery_address_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle delivery address choice (use saved or enter new)"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            choice = query.data.replace("delivery_address_", "")
            self.logger.info("📍 DELIVERY ADDRESS CHOICE: User %s selected %s", user_id, choice)

            cart_service = self.container.get_cart_service()
            customer = cart_service.get_customer(user_id)

            if choice == "use_saved":
                # Use saved address
                if customer and customer.delivery_address:
                    # Set delivery method back to "delivery" and update cart with saved address
                    cart_service.set_delivery_method(user_id, "delivery")
                    cart_service.set_delivery_address(user_id, customer.delivery_address)
                    await self._show_order_confirmation(query, cart_service, user_id)
                else:
                    await self._safe_edit_message(
                        query,
                        i18n.get_text("NO_SAVED_ADDRESS", user_id=user_id),
                        parse_mode="HTML",
                        reply_markup=self._get_back_to_cart_keyboard(user_id),
                    )
            elif choice == "new_address":
                # Ask for new address
                await self._safe_edit_message(
                    query,
                    i18n.get_text("DELIVERY_ADDRESS_PROMPT", user_id=user_id),
                    parse_mode="HTML",
                )
                # Send a forced reply to clearly request text input
                await query.message.reply_text(
                    i18n.get_text("DELIVERY_ADDRESS_PROMPT", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=ForceReply(selective=True),
                )
                # Set context to expect address input and route via quick-signup input handler
                context.user_data["expecting_delivery_address"] = True
                context.user_data["qs_stage"] = "address"
            else:
                await self._safe_edit_message(
                    query,
                    i18n.get_text("INVALID_CHOICE", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_cart_keyboard(user_id),
                )

        except Exception as e:
            self.logger.error("Exception in handle_delivery_address_choice: %s", e)
            await handle_error(update, e, "delivery address choice")

    async def handle_delivery_area_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle delivery area selection and set area + price accordingly"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            area_id = int(query.data.replace("delivery_area_", ""))

            # Persist area on cart and set delivery method
            cart_service = self.container.get_cart_service()
            items = cart_service.get_items(user_id)
            if not items:
                await self._safe_edit_message(
                    query,
                    i18n.get_text("CART_EMPTY", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_cart_keyboard(user_id),
                )
                return

            # Save area on cart
            cart_service.update_cart(
                user_id,
                items,
                delivery_method="delivery",
                delivery_area_id=area_id,
            )

            # After selecting area, resume the regular delivery flow:
            # if the customer has a saved address, offer to use it or enter a new one;
            # otherwise, prompt for a new address.
            customer = cart_service.get_customer(user_id)
            if customer and getattr(customer, "delivery_address", None):
                message = i18n.get_text("DELIVERY_ADDRESS_CURRENT", user_id=user_id).format(
                    address=customer.delivery_address
                )
                await self._safe_edit_message(
                    query,
                    message,
                    parse_mode="HTML",
                    reply_markup=self._get_delivery_address_choice_keyboard(user_id),
                )
            else:
                await self._safe_edit_message(
                    query,
                    i18n.get_text("DELIVERY_ADDRESS_REQUIRED", user_id=user_id),
                    parse_mode="HTML",
                )
                await query.message.reply_text(
                    i18n.get_text("DELIVERY_ADDRESS_PROMPT", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=ForceReply(selective=True),
                )
                context.user_data["expecting_delivery_address"] = True
                context.user_data["qs_stage"] = "address"
        except Exception as e:
            self.logger.error("Exception in handle_delivery_area_selection: %s", e)
            await handle_error(update, e, "delivery area selection")

    async def handle_delivery_address_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.logger.info(f"[DEBUG] handle_delivery_address_input called for user {update.effective_user.id} with text: {getattr(update.message, 'text', None)}")
        try:
            user_id = update.effective_user.id
            
            # Check if user is expecting delivery address input
            if not context.user_data.get("expecting_delivery_address"):
                # Not expecting address input, ignore this message
                return
            
            address = update.message.text.strip()
            
            if not address or len(address) < 5:
                await update.message.reply_text(
                    i18n.get_text("INVALID_ADDRESS", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_cart_keyboard(user_id),
                )
                return

            self.logger.info("📍 DELIVERY ADDRESS INPUT: User %s entered address", user_id)

            # Get cart service
            cart_service = self.container.get_cart_service()
            
            # Update cart with delivery address
            success = cart_service.set_delivery_address(user_id, address)
            
            if not success:
                await update.message.reply_text(
                    i18n.get_text("FAILED_SAVE_ADDRESS", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_cart_keyboard(user_id),
                )
                return

            # Update customer's delivery address in database
            customer = cart_service.get_customer(user_id)
            if customer:
                # Update customer's delivery address
                cart_service.update_customer_delivery_address(user_id, address)

            # Clear the expecting flag
            context.user_data.pop("expecting_delivery_address", None)

            # Show order confirmation
            await update.message.reply_text(
                i18n.get_text("DELIVERY_ADDRESS_SAVED", user_id=user_id).format(address=address),
                parse_mode="HTML",
            )
            
            # Show order confirmation
            await self._show_order_confirmation_text(update.message, cart_service, user_id)

        except Exception as e:
            self.logger.error("Exception in handle_delivery_address_input: %s", e)
            await handle_error(update, e, "delivery address input")

    async def handle_confirm_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle order confirmation"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        self.logger.info("✅ CONFIRM ORDER: User %s", user_id)
        
        try:
            # Get cart service
            cart_service = self.container.get_cart_service()
            
            # Gate: require minimal signup (phone) if guest
            customer = cart_service.get_customer(user_id)
            if not (customer and getattr(customer, "phone", None) and len((customer.phone or "").strip()) >= 8):
                # Redirect to quick signup
                await self._safe_edit_message(
                    query,
                    i18n.get_text("SIGNUP_REQUIRED_TO_ORDER", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n.get_text("BUTTON_COMPLETE_SIGNUP", user_id=user_id), callback_data="quick_signup")]])
                )
                return

            # Additional gate: if delivery selected but no address, prompt for address now
            try:
                from src.db.operations import get_cart_by_telegram_id
                cart = get_cart_by_telegram_id(user_id)
            except Exception:
                cart = None
            needs_address = False
            if cart and getattr(cart, "delivery_method", None) == "delivery":
                cart_address = getattr(cart, "delivery_address", None)
                customer_address = getattr(customer, "delivery_address", None) if customer else None
                needs_address = not (cart_address and cart_address.strip()) and not (customer_address and customer_address.strip())
            if needs_address:
                await self._safe_edit_message(
                    query,
                    i18n.get_text("DELIVERY_ADDRESS_REQUIRED", user_id=user_id),
                    parse_mode="HTML",
                )
                context.user_data["expecting_delivery_address"] = True
                context.user_data["qs_stage"] = "address"
                return

            # Get cart items
            cart_items = cart_service.get_items(user_id)
            if not cart_items:
                await self._safe_edit_message(
                    query,
                    i18n.get_text("CART_EMPTY_ORDER"),
                    parse_mode="HTML"
                )
                return
            
            # Create order using order service
            order_service = self.container.get_order_service()
            order_result = await order_service.create_order(user_id, cart_items)
            
            if order_result.get("success"):
                # Clear cart after successful order
                cart_service.clear_cart(user_id)
                
                order_obj = order_result.get("order")
                order_id = getattr(order_obj, "id", None)
                order_total = order_result.get("total")

                # Build order summary like admin, for customer-facing "received" message
                # Localize delivery method and address
                dm_name = getattr(order_obj, "delivery_method", "pickup") or "pickup"
                try:
                    from src.utils.language_manager import language_manager
                    from src.db.operations import get_delivery_method_by_name
                    user_lang = language_manager.get_user_language(user_id)
                    dm_info = get_delivery_method_by_name(dm_name, user_lang)
                    delivery_method_display = (dm_info.get("display_name") if dm_info else dm_name.title())
                except Exception:
                    delivery_method_display = dm_name.title()

                address_line = ""
                if dm_name == "delivery":
                    addr = getattr(order_obj, "delivery_address", None)
                    if not addr:
                        # fallback to customer's saved address
                        customer = cart_service.get_customer(user_id)
                        addr = getattr(customer, "delivery_address", None) if customer else None
                    if addr:
                        address_line = "\n" + i18n.get_text("CUSTOMER_ORDER_DELIVERY_ADDRESS", user_id=user_id).format(address=addr)

                # Compose items summary from cart_items we just placed
                items_summary = "\n" + i18n.get_text("CUSTOMER_ORDER_ITEMS", user_id=user_id) + "\n"
                try:
                    from src.utils.language_manager import language_manager
                    user_lang = language_manager.get_user_language(user_id)
                except Exception:
                    user_lang = "he"
                for idx, item in enumerate(cart_items, 1):
                    # Prefer multilingual fields from cart item, fallback to translation helper
                    name_he = item.get("name_he")
                    name_en = item.get("name_en")
                    if user_lang == "he" and name_he:
                        display_name = name_he
                    elif user_lang == "en" and name_en:
                        display_name = name_en
                    else:
                        from src.utils.helpers import translate_product_name
                        display_name = translate_product_name(
                            item.get("product_name", i18n.get_text("PRODUCT_UNKNOWN", user_id=user_id)),
                            item.get("options", {}),
                            user_id,
                        )
                    items_summary += i18n.get_text("CUSTOMER_ORDER_ITEM_LINE", user_id=user_id).format(
                        name=display_name,
                        quantity=item.get("quantity", 1),
                        price=item.get("unit_price", 0),
                    ) + "\n"

                # If delivery, add delivery as a line item
                try:
                    delivery_fee = float(getattr(order_obj, "delivery_charge", 0) or 0)
                except Exception:
                    delivery_fee = 0.0
                if dm_name == "delivery" and delivery_fee > 0:
                    items_summary += i18n.get_text("CUSTOMER_ORDER_ITEM_LINE", user_id=user_id).format(
                        name=i18n.get_text("DELIVERY_ITEM_NAME", user_id=user_id),
                        quantity=1,
                        price=delivery_fee,
                    ) + "\n"

                received_text = (
                    i18n.get_text("ORDER_RECEIVED_TITLE", user_id=user_id) + "\n\n" +
                    f"{i18n.get_text('CUSTOMER_ORDER_DETAILS_TITLE', user_id=user_id).format(number=order_id)}\n" +
                    i18n.get_text("CUSTOMER_ORDER_TOTAL", user_id=user_id).format(total=order_total) + "\n" +
                    i18n.get_text("CUSTOMER_ORDER_DELIVERY_METHOD", user_id=user_id).format(method=delivery_method_display) +
                    address_line + "\n" +
                    items_summary + "\n" +
                    i18n.get_text("ORDER_RECEIVED_AWAITING_CONFIRMATION", user_id=user_id)
                )

                await self._safe_edit_message(
                    query,
                    received_text,
                    parse_mode="HTML",
                    reply_markup=self._get_order_success_keyboard(user_id)
                )

                self.logger.info("✅ ORDER CREATED (received): id=%s for user %s", order_id, user_id)
                
            else:
                error_msg = order_result.get("error", i18n.get_text("ERROR_UNKNOWN_OCCURRED", user_id=user_id))
                self.logger.error("❌ ORDER CREATION FAILED: %s", error_msg)
                await self._safe_edit_message(
                    query,
                    i18n.get_text("ORDER_CREATION_FAILED", user_id=user_id).format(error_msg=error_msg),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_cart_keyboard(user_id)
                )
                
        except Exception as e:
            self.logger.error("❌ ORDER CREATION ERROR: %s", e)
            await self._safe_edit_message(
                query,
                i18n.get_text("ORDER_CREATION_ERROR", user_id=user_id),
                parse_mode="HTML",
                reply_markup=self._get_back_to_cart_keyboard(user_id)
            )

    async def handle_quick_signup_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the inline quick signup flow inside the cart flow"""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        # Start name collection
        context.user_data["qs_stage"] = "name"
        await self._safe_edit_message(
            query,
            i18n.get_text("PLEASE_ENTER_NAME", user_id=user_id),
            parse_mode="HTML",
        )

    async def handle_quick_signup_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle name/phone input for quick signup based on stage flags"""
        try:
            user_id = update.effective_user.id
            stage = context.user_data.get("qs_stage")
            if not stage:
                return  # Not in quick signup

            text = (update.message.text or "").strip()
            if stage == "name":
                if len(text) < 2:
                    await update.message.reply_text(
                        i18n.get_text("NAME_TOO_SHORT", user_id=user_id),
                        parse_mode="HTML",
                    )
                    return
                context.user_data["qs_name"] = text
                context.user_data["qs_stage"] = "phone"
                await update.message.reply_text(
                    i18n.get_text("PLEASE_SHARE_PHONE", user_id=user_id),
                    parse_mode="HTML",
                )
                return

            if stage == "phone":
                if len(text) < 8:
                    await update.message.reply_text(
                        i18n.get_text("ENTER_VALID_PHONE", user_id=user_id),
                        parse_mode="HTML",
                    )
                    return
                # Persist customer name+phone now
                from src.utils.language_manager import language_manager
                from src.db.operations import get_or_create_customer
                name = context.user_data.get("qs_name") or "Guest"
                lang = language_manager.get_user_language(user_id)
                get_or_create_customer(user_id, name, text, lang)

                # Ask for delivery address as part of signup (always collect)
                context.user_data["qs_stage"] = "address"
                await update.message.reply_text(
                    i18n.get_text("DELIVERY_ADDRESS_PROMPT", user_id=user_id),
                    parse_mode="HTML",
                )
                return

            if stage == "address":
                if len(text) < 5:
                    await update.message.reply_text(
                        i18n.get_text("ADDRESS_TOO_SHORT", user_id=user_id),
                        parse_mode="HTML",
                    )
                    return
                # Save address on customer and cart
                cart_service = self.container.get_cart_service()
                cart_service.update_customer_delivery_address(user_id, text)

                # Clear quick signup flags
                context.user_data.pop("qs_stage", None)
                context.user_data.pop("qs_name", None)

                await update.message.reply_text(
                    i18n.get_text("DELIVERY_ADDRESS_SAVED", user_id=user_id).format(address=text),
                    parse_mode="HTML",
                )

                # Show checkout summary and prompt delivery method
                cart_items = cart_service.get_items(user_id)
                if not cart_items:
                    await update.message.reply_text(
                        i18n.get_text("CART_EMPTY_CHECKOUT", user_id=user_id),
                        parse_mode="HTML",
                        reply_markup=self._get_professional_empty_cart_keyboard(user_id),
                    )
                    return
                cart_total = cart_service.calculate_total(cart_items)
                message = i18n.get_text("CHECKOUT_TITLE", user_id=user_id) + "\n\n"
                for i, item in enumerate(cart_items, 1):
                    item_total = item.get("unit_price", 0) * item.get("quantity", 1)
                    from src.utils.helpers import translate_product_name
                    translated_product_name = translate_product_name(item.get('product_name', i18n.get_text('PRODUCT_UNKNOWN', user_id=user_id)), item.get('options', {}), user_id)
                    message += i18n.get_text("CART_ITEM_FORMAT", user_id=user_id).format(
                        index=i,
                        product_name=translated_product_name,
                        quantity=item.get('quantity', 1),
                        price=item.get('unit_price', 0),
                        item_total=item_total
                    ) + "\n\n"
                message += i18n.get_text("CART_TOTAL", user_id=user_id).format(total=cart_total) + "\n\n"
                message += i18n.get_text("SELECT_DELIVERY_METHOD", user_id=user_id)
                await update.message.reply_text(
                    message,
                    parse_mode="HTML",
                    reply_markup=self._get_delivery_method_keyboard(user_id),
                )
                return
        except Exception as e:
            self.logger.error("Exception in handle_quick_signup_input: %s", e)

    async def handle_decrease_quantity(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle decreasing item quantity in cart"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            callback_data = query.data
            
            # Extract product ID from callback data
            product_id = int(callback_data.split("_")[-1])
            
            self.logger.info("🛒 DECREASE QUANTITY: User %s, Product %s", user_id, product_id)
            
            # Get cart service
            cart_service = self.container.get_cart_service()
            
            # Get current item
            current_item = cart_service.get_item_by_id(user_id, product_id)
            if not current_item:
                await query.answer(i18n.get_text("CART_ITEM_NOT_FOUND", user_id=user_id))
                return
            
            current_quantity = current_item.get("quantity", 1)
            
            # If quantity is already 1, remove the item instead
            if current_quantity <= 1:
                success = cart_service.remove_item(user_id, product_id)
                if success:
                    await query.answer(i18n.get_text("CART_ITEM_REMOVED", user_id=user_id))
                    # Refresh cart view
                    await self.handle_view_cart(update, context)
                else:
                    await query.answer(i18n.get_text("CART_REMOVE_ERROR", user_id=user_id))
                return
            
            new_quantity = current_quantity - 1
            
            # Update quantity
            success = cart_service.update_item_quantity(user_id, product_id, new_quantity)
            
            if success:
                await query.answer(i18n.get_text("CART_QUANTITY_UPDATED", user_id=user_id))
                # Refresh cart view
                await self.handle_view_cart(update, context)
            else:
                await query.answer(i18n.get_text("CART_UPDATE_ERROR", user_id=user_id))
                
        except Exception as e:
            self.logger.error("Exception in handle_decrease_quantity: %s", e)
            await handle_error(update, e, "decreasing quantity")

    async def handle_increase_quantity(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle increasing item quantity in cart"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            callback_data = query.data
            
            # Extract product ID from callback data
            product_id = int(callback_data.split("_")[-1])
            
            self.logger.info("🛒 INCREASE QUANTITY: User %s, Product %s", user_id, product_id)
            
            # Get cart service
            cart_service = self.container.get_cart_service()
            
            # Get current item
            current_item = cart_service.get_item_by_id(user_id, product_id)
            if not current_item:
                await query.answer(i18n.get_text("CART_ITEM_NOT_FOUND", user_id=user_id))
                return
            
            current_quantity = current_item.get("quantity", 1)
            new_quantity = current_quantity + 1
            
            # Update quantity
            success = cart_service.update_item_quantity(user_id, product_id, new_quantity)
            
            if success:
                await query.answer(i18n.get_text("CART_QUANTITY_UPDATED", user_id=user_id))
                # Refresh cart view
                await self.handle_view_cart(update, context)
            else:
                await query.answer(i18n.get_text("CART_UPDATE_ERROR", user_id=user_id))
                
        except Exception as e:
            self.logger.error("Exception in handle_increase_quantity: %s", e)
            await handle_error(update, e, "increasing quantity")

    async def handle_remove_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle removing item from cart"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            callback_data = query.data
            
            # Extract product ID from callback data
            product_id = int(callback_data.split("_")[-1])
            
            self.logger.info("🛒 REMOVE ITEM: User %s, Product %s", user_id, product_id)
            
            # Get cart service
            cart_service = self.container.get_cart_service()
            
            # Remove item
            success = cart_service.remove_item(user_id, product_id)
            
            if success:
                await query.answer(i18n.get_text("CART_ITEM_REMOVED", user_id=user_id))
                # Refresh cart view
                await self.handle_view_cart(update, context)
            else:
                await query.answer(i18n.get_text("CART_REMOVE_ERROR", user_id=user_id))
                
        except Exception as e:
            self.logger.error("Exception in handle_remove_item: %s", e)
            await handle_error(update, e, "removing item")

    async def handle_edit_quantity(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle editing item quantity (placeholder for future quantity input)"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            callback_data = query.data
            
            # Extract product ID from callback data
            product_id = int(callback_data.split("_")[-1])
            
            self.logger.info("🛒 EDIT QUANTITY: User %s, Product %s", user_id, product_id)
            
            # For now, just show a message that this feature is coming soon
            await query.answer(i18n.get_text("CART_EDIT_COMING_SOON", user_id=user_id))
                
        except Exception as e:
            self.logger.error("Exception in handle_edit_quantity: %s", e)
            await handle_error(update, e, "editing quantity")

    async def handle_item_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle item info button (shows product details)"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            callback_data = query.data
            
            # Extract product ID from callback data
            product_id = int(callback_data.split("_")[-1])
            
            self.logger.info("🛒 ITEM INFO: User %s, Product %s", user_id, product_id)
            
            # Get cart service
            cart_service = self.container.get_cart_service()
            
            # Get item details
            item = cart_service.get_item_by_id(user_id, product_id)
            if not item:
                await query.answer(i18n.get_text("CART_ITEM_NOT_FOUND", user_id=user_id))
                return
            
            # Show item details
            from src.utils.helpers import translate_product_name
            product_name = translate_product_name(item.get('product_name', i18n.get_text('PRODUCT_UNKNOWN', user_id=user_id)), item.get('options', {}), user_id)
            
            info_message = f"📦 <b>{product_name}</b>\n"
            info_message += f"💰 {i18n.get_text('CART_PRICE_LABEL', user_id=user_id)}: ₪{item.get('unit_price', 0):.2f}\n"
            info_message += f"📊 {i18n.get_text('CART_QUANTITY_LABEL', user_id=user_id)}: {item.get('quantity', 1)}\n"
            info_message += f"💵 {i18n.get_text('CART_SUBTOTAL_LABEL', user_id=user_id)}: ₪{item.get('unit_price', 0) * item.get('quantity', 1):.2f}"
            
            await query.answer(info_message, show_alert=True)
                
        except Exception as e:
            self.logger.error("Exception in handle_item_info: %s", e)
            await handle_error(update, e, "showing item info")

    async def handle_edit_cart_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle entering edit cart mode"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            self.logger.info("✏️ EDIT CART MODE: User %s", user_id)

            # Get cart service
            cart_service = self.container.get_cart_service()
            cart_items = cart_service.get_items(user_id)

            if not cart_items:
                await self._safe_edit_message(
                    query,
                    i18n.get_text("CART_EMPTY_READY", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_professional_empty_cart_keyboard(user_id),
                )
                return

            # Calculate total
            cart_total = cart_service.calculate_total(cart_items)

            # Build simplified edit mode display
            message = i18n.get_text("CART_EDIT_MODE_TITLE", user_id=user_id) + "\n\n"
            message += i18n.get_text("CART_EDIT_MODE_INSTRUCTIONS", user_id=user_id)

            await self._safe_edit_message(
                query,
                message,
                parse_mode="HTML",
                reply_markup=self._get_cart_items_keyboard_with_back(cart_items, user_id),
            )

        except Exception as e:
            self.logger.error("Exception in handle_edit_cart_mode: %s", e)
            await handle_error(update, e, "entering edit cart mode")

    async def handle_separator(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle separator button (does nothing, just for visual separation)"""
        try:
            query = update.callback_query
            await query.answer("")  # Silent answer for separator
        except Exception as e:
            self.logger.error("Exception in handle_separator: %s", e)

    def _parse_product_from_callback(self, callback_data: str) -> Optional[Dict[str, Any]]:
        """Parse product information from callback data"""
        try:
            # Handle new dynamic product pattern
            if callback_data.startswith("add_product_"):
                product_id = int(callback_data.replace("add_product_", ""))
                # Get product from database
                from src.db.operations import get_product_by_id
                product = get_product_by_id(product_id)
                if product:
                    return {
                        "product_id": product.id,
                        "display_name": product.name,  # This will be localized later in the process
                        "name_en": product.name_en,
                        "name_he": product.name_he,
                        "options": {}
                    }
            
            # Handle legacy product option patterns (from sub-menus)
            # These map to specific product variants with options
            # Note: display_name will be localized later in the process
            legacy_product_mapping = {
                # Kubaneh options - all map to product_id 1 with different types
                "kubaneh_classic": {"product_id": 1, "display_name": "Kubaneh", "options": {"type": "classic"}},
                "kubaneh_seeded": {"product_id": 1, "display_name": "Kubaneh", "options": {"type": "seeded"}},
                "kubaneh_herb": {"product_id": 1, "display_name": "Kubaneh", "options": {"type": "herb"}},
                "kubaneh_aromatic": {"product_id": 1, "display_name": "Kubaneh", "options": {"type": "aromatic"}},
                
                # Samneh options - all map to product_id 2 with different types
                "samneh_classic": {"product_id": 2, "display_name": "Samneh", "options": {"type": "classic"}},
                "samneh_spicy": {"product_id": 2, "display_name": "Samneh", "options": {"type": "spicy"}},
                "samneh_herb": {"product_id": 2, "display_name": "Samneh", "options": {"type": "herb"}},
                "samneh_honey": {"product_id": 2, "display_name": "Samneh", "options": {"type": "honey"}},
                "samneh_smoked": {"product_id": 2, "display_name": "Samneh", "options": {"type": "smoked"}},
                "samneh_not_smoked": {"product_id": 2, "display_name": "Samneh", "options": {"type": "not_smoked"}},
                
                # Red Bisbas options - all map to product_id 3 with different sizes
                "red_bisbas_small": {"product_id": 3, "display_name": "Red Bisbas", "options": {"size": "small"}},
                "red_bisbas_medium": {"product_id": 3, "display_name": "Red Bisbas", "options": {"size": "medium"}},
                "red_bisbas_large": {"product_id": 3, "display_name": "Red Bisbas", "options": {"size": "large"}},
                "red_bisbas_xl": {"product_id": 3, "display_name": "Red Bisbas", "options": {"size": "xl"}},
                
                # Hilbeh options - all map to product_id 7 with different types
                "hilbeh_classic": {"product_id": 7, "display_name": "Hilbeh", "options": {"type": "classic"}},
                "hilbeh_spicy": {"product_id": 7, "display_name": "Hilbeh", "options": {"type": "spicy"}},
                "hilbeh_sweet": {"product_id": 7, "display_name": "Hilbeh", "options": {"type": "sweet"}},
                "hilbeh_premium": {"product_id": 7, "display_name": "Hilbeh", "options": {"type": "premium"}},
                
                # Direct add products (no options)
                "hawaij_coffee_spice": {"product_id": 5, "display_name": "Hawaij for Coffee", "options": {}},
                "white_coffee": {"product_id": 6, "display_name": "White Coffee", "options": {}},
            }
            
            if callback_data in legacy_product_mapping:
                return legacy_product_mapping[callback_data]
            
            # Handle legacy add_ patterns (fallback for backward compatibility)
            if callback_data.startswith("add_"):
                parts = callback_data.split("_")
                if len(parts) >= 2:
                    product_type = parts[1]
                    
                    # Simple mapping for basic products without options
                    # Note: display_name will be localized later in the process
                    basic_product_mapping = {
                        "hawaij": {"product_id": 4, "display_name": "Hawaij for Soup", "options": {}},
                        "white": {"product_id": 6, "display_name": "White Coffee", "options": {}},
                        "hilbeh": {"product_id": 7, "display_name": "Hilbeh", "options": {}},
                    }
                    
                    if product_type in basic_product_mapping:
                        return basic_product_mapping[product_type]
            
            return None
        except Exception as e:
            self.logger.error("Error parsing product from callback: %s", e)
            return None

    def _get_cart_success_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Get professional keyboard for successful cart addition"""
        keyboard = [
            # Primary Actions
            [
                InlineKeyboardButton(
                    i18n.get_text('VIEW_CART', user_id=user_id), 
                    callback_data="cart_view"
                ),
                InlineKeyboardButton(
                    i18n.get_text('ADD_MORE', user_id=user_id), 
                    callback_data="menu_main"
                ),
            ],
            # Secondary Action
            [InlineKeyboardButton(
                i18n.get_text('BACK_TO_MAIN', user_id=user_id), 
                callback_data="main_page"
            )],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_cart_items_keyboard(self, cart_items: List[Dict], user_id: int = None) -> InlineKeyboardMarkup:
        """Get keyboard for cart items with individual controls"""
        keyboard = []
        
        # Add individual item controls
        for i, item in enumerate(cart_items, 1):
            product_id = item.get("product_id")
            quantity = item.get("quantity", 1)
            
            # Get product name for better identification
            from src.utils.helpers import translate_product_name
            product_name = translate_product_name(item.get('product_name', i18n.get_text('PRODUCT_UNKNOWN', user_id=user_id)), item.get('options', {}), user_id)
            short_name = product_name[:15] + "..." if len(product_name) > 15 else product_name
            
            # Item label row - shows which item these controls belong to
            label_row = [
                InlineKeyboardButton(f"📦 {short_name}", callback_data=f"cart_info_{product_id}")
            ]
            keyboard.append(label_row)
            
            # Item controls row
            item_row = []
            
            # Decrease quantity button (always show, removes item when quantity = 1)
            item_row.append(
                InlineKeyboardButton("➖", callback_data=f"cart_decrease_{product_id}")
            )
            
            # Quantity display with better formatting
            item_row.append(
                InlineKeyboardButton(f" {quantity} ", callback_data=f"cart_edit_{product_id}")
            )
            
            # Increase quantity button
            item_row.append(
                InlineKeyboardButton("➕", callback_data=f"cart_increase_{product_id}")
            )
            
            # Remove item button
            item_row.append(
                InlineKeyboardButton("🗑️", callback_data=f"cart_remove_{product_id}")
            )
            
            keyboard.append(item_row)
            
            # Add separator between items (except for last item)
            if i < len(cart_items):
                keyboard.append([InlineKeyboardButton("─" * 20, callback_data="cart_separator")])
        
        # Add main cart actions
        keyboard.append([
            InlineKeyboardButton(i18n.get_text("CLEAR_CART", user_id=user_id), callback_data="cart_clear_confirm"),
            InlineKeyboardButton(i18n.get_text("CHECKOUT", user_id=user_id), callback_data="cart_checkout"),
        ])
        
        keyboard.append([InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="menu_main")])
        
        return InlineKeyboardMarkup(keyboard)

    def _get_simplified_cart_keyboard(self, cart_items: List[Dict], user_id: int = None) -> InlineKeyboardMarkup:
        """Get simplified cart keyboard with Edit Cart button and each button on its own line"""
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("EDIT_CART", user_id=user_id), callback_data="cart_edit_mode")],
            [InlineKeyboardButton(i18n.get_text("CLEAR_CART", user_id=user_id), callback_data="cart_clear_confirm")],
            [InlineKeyboardButton(i18n.get_text("CHECKOUT", user_id=user_id), callback_data="cart_checkout")],
            [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="menu_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_cart_items_keyboard_with_back(self, cart_items: List[Dict], user_id: int = None) -> InlineKeyboardMarkup:
        """Get keyboard for cart items with individual controls and back button"""
        keyboard = []
        
        # Add individual item controls
        for i, item in enumerate(cart_items, 1):
            product_id = item.get("product_id")
            quantity = item.get("quantity", 1)
            
            # Get product name for better identification
            from src.utils.helpers import translate_product_name
            product_name = translate_product_name(item.get('product_name', i18n.get_text('PRODUCT_UNKNOWN', user_id=user_id)), item.get('options', {}), user_id)
            short_name = product_name[:15] + "..." if len(product_name) > 15 else product_name
            
            # Item label row - shows which item these controls belong to
            label_row = [
                InlineKeyboardButton(f"📦 {short_name}", callback_data=f"cart_info_{product_id}")
            ]
            keyboard.append(label_row)
            
            # Item controls row
            item_row = []
            
            # Decrease quantity button (always show, removes item when quantity = 1)
            item_row.append(
                InlineKeyboardButton("➖", callback_data=f"cart_decrease_{product_id}")
            )
            
            # Quantity display with better formatting
            item_row.append(
                InlineKeyboardButton(f" {quantity} ", callback_data=f"cart_edit_{product_id}")
            )
            
            # Increase quantity button
            item_row.append(
                InlineKeyboardButton("➕", callback_data=f"cart_increase_{product_id}")
            )
            
            # Remove item button
            item_row.append(
                InlineKeyboardButton("🗑️", callback_data=f"cart_remove_{product_id}")
            )
            
            keyboard.append(item_row)
            
            # Add separator between items (except for last item)
            if i < len(cart_items):
                keyboard.append([InlineKeyboardButton("─" * 20, callback_data="cart_separator")])
        
        # Add back button and main cart actions
        keyboard.append([InlineKeyboardButton(i18n.get_text("BACK_TO_CART_VIEW", user_id=user_id), callback_data="cart_view")])
        
        keyboard.append([
            InlineKeyboardButton(i18n.get_text("CLEAR_CART", user_id=user_id), callback_data="cart_clear_confirm"),
            InlineKeyboardButton(i18n.get_text("CHECKOUT", user_id=user_id), callback_data="cart_checkout"),
        ])
        
        keyboard.append([InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="menu_main")])
        
        return InlineKeyboardMarkup(keyboard)

    def _get_cart_actions_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Get keyboard for cart actions with each button on its own line"""
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("CLEAR_CART", user_id=user_id), callback_data="cart_clear_confirm")],
            [InlineKeyboardButton(i18n.get_text("CHECKOUT", user_id=user_id), callback_data="cart_checkout")],
            [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="menu_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_professional_empty_cart_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Get professional keyboard for empty cart with beautiful styling"""
        keyboard = [
            [InlineKeyboardButton(
                i18n.get_text('BROWSE_MENU', user_id=user_id), 
                callback_data="menu_main"
            )],
            [InlineKeyboardButton(
                i18n.get_text('BACK_TO_MAIN', user_id=user_id), 
                callback_data="main_page"
            )],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_back_to_menu_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Get keyboard to go back to main menu"""
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="menu_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_delivery_method_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Get keyboard for delivery method selection with each button on its own line"""
        keyboard = [
            [InlineKeyboardButton(get_delivery_method_name("pickup", user_id), callback_data="delivery_pickup")],
            [InlineKeyboardButton(get_delivery_method_name("delivery", user_id), callback_data="delivery_delivery")],
            [InlineKeyboardButton(i18n.get_text("BACK_TO_CART", user_id=user_id), callback_data="cart_view")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_delivery_address_choice_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Get keyboard for delivery address choice with each button on its own line"""
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("USE_SAVED_ADDRESS", user_id=user_id), callback_data="delivery_address_use_saved")],
            [InlineKeyboardButton(i18n.get_text("ENTER_NEW_ADDRESS", user_id=user_id), callback_data="delivery_address_new_address")],
            [InlineKeyboardButton(i18n.get_text("BACK_TO_CART", user_id=user_id), callback_data="cart_view")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_order_confirmation_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Get keyboard for order confirmation with each button on its own line"""
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("CONFIRM_ORDER", user_id=user_id), callback_data="confirm_order")],
            [InlineKeyboardButton(i18n.get_text("CANCEL", user_id=user_id), callback_data="cart_view")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_order_success_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Get keyboard for successful order with each button on its own line"""
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("NEW_ORDER", user_id=user_id), callback_data="menu_main")],
            [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="menu_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_back_to_cart_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Get keyboard to go back to cart"""
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("BACK_TO_CART", user_id=user_id), callback_data="cart_view")],
            [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="menu_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_clear_cart_confirmation_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Get clear cart confirmation keyboard"""
        from src.keyboards.menu_keyboards import get_clear_cart_confirmation_keyboard
        return get_clear_cart_confirmation_keyboard(user_id)

    async def _show_order_confirmation(self, query, cart_service, user_id):
        """Show order confirmation for callback queries"""
        try:
            # Get updated cart info
            cart_items = cart_service.get_items(user_id)
            cart_total = cart_service.calculate_total(cart_items)
            cart_info = cart_service.get_cart_info(user_id)

            # Build order confirmation
            message = i18n.get_text("ORDER_CONFIRMATION_TITLE", user_id=user_id) + "\n\n"
            # Ensure we read delivery method/address from the actual cart
            try:
                from src.db.operations import get_cart_by_telegram_id
                cart = get_cart_by_telegram_id(user_id)
            except Exception:
                cart = None
            # Localize delivery method display
            dm_name = (getattr(cart, "delivery_method", None) or "pickup")
            try:
                from src.utils.language_manager import language_manager
                from src.db.operations import get_delivery_method_by_name
                user_lang = language_manager.get_user_language(user_id)
                dm_info = get_delivery_method_by_name(dm_name, user_lang)
                delivery_method_display = (dm_info.get("display_name") if dm_info else dm_name.title())
            except Exception:
                delivery_method_display = dm_name.title()
            message += i18n.get_text("DELIVERY_METHOD_LABEL", user_id=user_id).format(
                method=delivery_method_display
            ) + "\n"
            if cart and getattr(cart, "delivery_method", None) == "delivery":
                addr = getattr(cart, "delivery_address", None)
                if addr:
                    message += i18n.get_text("DELIVERY_ADDRESS_LABEL", user_id=user_id).format(
                        address=addr
                    ) + "\n"
            
            
            for i, item in enumerate(cart_items, 1):
                item_total = item.get("unit_price", 0) * item.get("quantity", 1)
                # Get localized product name
                localized_product_name = self._get_localized_product_name(item, user_id)
                
                # Format prices and quantities with RTL support
                from src.utils.helpers import format_price, format_quantity
                formatted_unit_price = format_price(item.get('unit_price', 0), user_id)
                formatted_item_total = format_price(item_total, user_id)
                formatted_quantity = format_quantity(item.get('quantity', 1), user_id)
                
                message += f"""
<b>{i}.</b> 📦 <b>{localized_product_name}</b>
   🔢 {i18n.get_text("CART_QUANTITY_LABEL", user_id=user_id)}: {formatted_quantity}
   💰 {i18n.get_text("CART_PRICE_LABEL", user_id=user_id)}: {formatted_unit_price}
   💵 {i18n.get_text("CART_SUBTOTAL_LABEL", user_id=user_id)}: {formatted_item_total}

"""

            # Format totals and delivery fee
            from src.utils.helpers import format_price
            formatted_total = format_price(cart_total, user_id)
            delivery_charge_line = ""
            total_with_delivery_line = ""
            if cart and getattr(cart, "delivery_method", None) == "delivery":
                try:
                    from src.db.operations import get_current_delivery_charge
                    charge = get_current_delivery_charge()
                except Exception:
                    charge = 0.0
                formatted_charge = format_price(charge, user_id)
                delivery_charge_line = f"{i18n.get_text('DELIVERY_CHARGE_LABEL', user_id=user_id)}: {formatted_charge}\n"
                formatted_total_with_delivery = format_price(cart_total + charge, user_id)
                total_with_delivery_line = i18n.get_text('TOTAL_WITH_DELIVERY', user_id=user_id).format(total=cart_total + charge)

            message += f"""
{delivery_charge_line}💸 <b>{i18n.get_text("CART_TOTAL", user_id=user_id).format(total=formatted_total)}</b>
{total_with_delivery_line}

🤔 {i18n.get_text("CONFIRM_ORDER_PROMPT", user_id=user_id)}"""

            await query.edit_message_text(
                message,
                parse_mode="HTML",
                reply_markup=self._get_order_confirmation_keyboard(user_id),
            )

        except Exception as e:
            self.logger.error("Exception in _show_order_confirmation: %s", e)
            await query.edit_message_text(
                i18n.get_text("ERROR_SHOWING_CONFIRMATION", user_id=user_id),
                parse_mode="HTML",
                reply_markup=self._get_back_to_cart_keyboard(user_id),
            )

    async def _show_order_confirmation_text(self, message, cart_service, user_id):
        """Show order confirmation for text messages"""
        try:
            # Get updated cart info
            cart_items = cart_service.get_items(user_id)
            cart_total = cart_service.calculate_total(cart_items)
            cart_info = cart_service.get_cart_info(user_id)

            # Build order confirmation
            confirmation_message = i18n.get_text("ORDER_CONFIRMATION_TITLE", user_id=user_id) + "\n\n"
            # Ensure we read delivery method/address from the actual cart
            try:
                from src.db.operations import get_cart_by_telegram_id
                cart = get_cart_by_telegram_id(user_id)
            except Exception:
                cart = None
            # Localize delivery method display
            dm_name = (getattr(cart, "delivery_method", None) or "pickup")
            try:
                from src.utils.language_manager import language_manager
                from src.db.operations import get_delivery_method_by_name
                user_lang = language_manager.get_user_language(user_id)
                dm_info = get_delivery_method_by_name(dm_name, user_lang)
                delivery_method_display = (dm_info.get("display_name") if dm_info else dm_name.title())
            except Exception:
                delivery_method_display = dm_name.title()
            confirmation_message += i18n.get_text("DELIVERY_METHOD_LABEL", user_id=user_id).format(
                method=delivery_method_display
            ) + "\n"
            if cart and getattr(cart, "delivery_method", None) == "delivery":
                addr = getattr(cart, "delivery_address", None)
                if addr:
                    confirmation_message += i18n.get_text("DELIVERY_ADDRESS_LABEL", user_id=user_id).format(
                        address=addr
                    ) + "\n"
            
            confirmation_message += "\n"
            
            for i, item in enumerate(cart_items, 1):
                item_total = item.get("unit_price", 0) * item.get("quantity", 1)
                # Get localized product name
                localized_product_name = self._get_localized_product_name(item, user_id)
                
                # Format prices and quantities with RTL support
                from src.utils.helpers import format_price, format_quantity
                formatted_unit_price = format_price(item.get('unit_price', 0), user_id)
                formatted_item_total = format_price(item_total, user_id)
                formatted_quantity = format_quantity(item.get('quantity', 1), user_id)
                
                confirmation_message += f"""
<b>{i}.</b> 📦 <b>{localized_product_name}</b>
   🔢 {i18n.get_text("CART_QUANTITY_LABEL", user_id=user_id)}: {formatted_quantity}
   💰 {i18n.get_text("CART_PRICE_LABEL", user_id=user_id)}: {formatted_unit_price}
   💵 {i18n.get_text("CART_SUBTOTAL_LABEL", user_id=user_id)}: {formatted_item_total}

"""

            # Format totals and delivery fee
            from src.utils.helpers import format_price
            formatted_total = format_price(cart_total, user_id)
            delivery_charge_line = ""
            total_with_delivery_line = ""
            if cart and getattr(cart, "delivery_method", None) == "delivery":
                try:
                    from src.db.operations import get_current_delivery_charge
                    charge = get_current_delivery_charge()
                except Exception:
                    charge = 0.0
                formatted_charge = format_price(charge, user_id)
                delivery_charge_line = f"{i18n.get_text('DELIVERY_CHARGE_LABEL', user_id=user_id)}: {formatted_charge}\n"
                formatted_total_with_delivery = format_price(cart_total + charge, user_id)
                total_with_delivery_line = i18n.get_text('TOTAL_WITH_DELIVERY', user_id=user_id).format(total=cart_total + charge)
            
            confirmation_message += f"""

{delivery_charge_line}💸 <b>{i18n.get_text("CART_TOTAL", user_id=user_id).format(total=formatted_total)}</b>
{total_with_delivery_line}

🤔 {i18n.get_text("CONFIRM_ORDER_PROMPT", user_id=user_id)}"""

            await message.reply_text(
                confirmation_message,
                parse_mode="HTML",
                reply_markup=self._get_order_confirmation_keyboard(user_id),
            )

        except Exception as e:
            self.logger.error("Exception in _show_order_confirmation_text: %s", e)
            await message.reply_text(
                i18n.get_text("ERROR_SHOWING_CONFIRMATION", user_id=user_id),
                parse_mode="HTML",
                reply_markup=self._get_back_to_cart_keyboard(user_id),
            )

    def _get_localized_product_name(self, item: Dict, user_id: int) -> str:
        """Get localized product name for display"""
        try:
            # Get user language
            from src.utils.language_manager import language_manager
            user_language = language_manager.get_user_language(user_id)
            
            # If we have multilingual fields in the item, use them
            if user_language == "he" and item.get("name_he"):
                return item["name_he"]
            elif user_language == "en" and item.get("name_en"):
                return item["name_en"]
            
            # Fallback to the old translation system
            from src.utils.helpers import translate_product_name
            return translate_product_name(
                item.get('product_name', ''), 
                item.get('options', {}), 
                user_id
            )
        except Exception as e:
            self.logger.error("Error getting localized product name: %s", e)
            return item.get('product_name', 'Unknown Product')
