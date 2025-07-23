"""
Cart handler for managing shopping cart operations
"""

import logging
from typing import Dict, Any, Optional, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
        """Safely edit message text, falling back to reply if no text content"""
        try:
            if query.message and query.message.text:
                await query.edit_message_text(text, **kwargs)
            else:
                # If no text content, send a new message
                await query.message.reply_text(text, **kwargs)
        except Exception as e:
            self.logger.warning("Failed to edit message, sending new message: %s", e)
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
                await query.edit_message_text(
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
                from src.utils.helpers import translate_product_name
                translated_product_name = translate_product_name(product_info['display_name'], product_info.get('options', {}), user_id)
                
                message = f"""
✅ <b>{i18n.get_text("CART_SUCCESS_TITLE", user_id=user_id)}</b>

📦 <b>{translated_product_name}</b>
{i18n.get_text("CART_ADDED_SUCCESSFULLY", user_id=user_id)}

🛒 {i18n.get_text("CART_ITEMS_COUNT", user_id=user_id)}: {item_count}
💰 {i18n.get_text("CART_TOTAL", user_id=user_id).format(total=cart_total)}

🎯 {i18n.get_text("CART_WHAT_NEXT_QUESTION", user_id=user_id)}
                """.strip()

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
                empty_cart_message = f"""
🛒 <b>{i18n.get_text("CART_VIEW_TITLE", user_id=user_id)}</b>

🤷‍♀️ {i18n.get_text("CART_EMPTY_READY", user_id=user_id)}

🍽️ {i18n.get_text("BROWSE_MENU_SUGGESTION", user_id=user_id)}
                """.strip()

                await query.edit_message_text(
                    empty_cart_message,
                    parse_mode="HTML",
                    reply_markup=self._get_professional_empty_cart_keyboard(user_id),
                )
                return

            # Calculate total
            cart_total = cart_service.calculate_total(cart_items)

            # Build beautiful cart display with clean styling
            message = f"""
🛒 <b>{i18n.get_text("CART_VIEW_TITLE", user_id=user_id)}</b>

"""
            
            for i, item in enumerate(cart_items, 1):
                item_total = item.get("unit_price", 0) * item.get("quantity", 1)
                # Translate product name
                from src.utils.helpers import translate_product_name
                translated_product_name = translate_product_name(item.get('product_name', i18n.get_text('PRODUCT_UNKNOWN', user_id=user_id)), item.get('options', {}), user_id)
                
                message += f"""
<b>{i}.</b> 📦 <b>{translated_product_name}</b>
   🔢 {i18n.get_text("CART_QUANTITY_LABEL", user_id=user_id)}: {item.get('quantity', 1)}
   💰 {i18n.get_text("CART_PRICE_LABEL", user_id=user_id)}: ₪{item.get('unit_price', 0):.2f}
   💵 {i18n.get_text("CART_SUBTOTAL_LABEL", user_id=user_id)}: ₪{item_total:.2f}"""
                
                if i < len(cart_items):
                    message += "\n"

            message += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💸 <b>{i18n.get_text("CART_TOTAL", user_id=user_id).format(total=cart_total)}</b>

🤔 {i18n.get_text("CART_WHAT_NEXT", user_id=user_id)}"""

            await query.edit_message_text(
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
            await query.edit_message_text(
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
                await query.edit_message_text(
                    i18n.get_text("CART_CLEARED_SUCCESS", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_professional_empty_cart_keyboard(user_id),
                )
            else:
                self.logger.error("❌ CART CLEAR FAILED: User %s", user_id)
                await query.edit_message_text(
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
                await query.edit_message_text(
                    i18n.get_text("CART_EMPTY_CHECKOUT", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_professional_empty_cart_keyboard(user_id),
                )
                return

            # Calculate total
            cart_total = cart_service.calculate_total(cart_items)

            # Build checkout summary
            message = i18n.get_text("CHECKOUT_TITLE", user_id=user_id) + "\n\n"
            
            for i, item in enumerate(cart_items, 1):
                item_total = item.get("unit_price", 0) * item.get("quantity", 1)
                # Translate product name
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

            await query.edit_message_text(
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
            
            # Update cart with delivery method
            success = cart_service.set_delivery_method(user_id, delivery_method)
            
            if not success:
                await query.edit_message_text(
                    i18n.get_text("FAILED_SET_DELIVERY", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_cart_keyboard(user_id),
                )
                return

            if delivery_method == "delivery":
                # Check if customer has a delivery address
                customer = cart_service.get_customer(user_id)
                
                if customer and customer.delivery_address:
                    # Customer has a saved address - ask if they want to use it
                    message = i18n.get_text("DELIVERY_ADDRESS_CURRENT", user_id=user_id).format(address=customer.delivery_address)
                    await query.edit_message_text(
                        message,
                        parse_mode="HTML",
                        reply_markup=self._get_delivery_address_choice_keyboard(user_id),
                    )
                else:
                    # No saved address - ask for new address
                    await query.edit_message_text(
                        i18n.get_text("DELIVERY_ADDRESS_REQUIRED", user_id=user_id),
                        parse_mode="HTML",
                    )
                    # Set context to expect address input
                    context.user_data["expecting_delivery_address"] = True
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
                    await query.edit_message_text(
                        i18n.get_text("NO_SAVED_ADDRESS", user_id=user_id),
                        parse_mode="HTML",
                        reply_markup=self._get_back_to_cart_keyboard(user_id),
                    )
            elif choice == "new_address":
                # Ask for new address
                await query.edit_message_text(
                    i18n.get_text("DELIVERY_ADDRESS_PROMPT", user_id=user_id),
                    parse_mode="HTML",
                )
                # Set context to expect address input
                context.user_data["expecting_delivery_address"] = True
            else:
                await query.edit_message_text(
                    i18n.get_text("INVALID_CHOICE", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_cart_keyboard(user_id),
                )

        except Exception as e:
            self.logger.error("Exception in handle_delivery_address_choice: %s", e)
            await handle_error(update, e, "delivery address choice")

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
            
            # Get cart items
            cart_items = cart_service.get_items(user_id)
            if not cart_items:
                await query.edit_message_text(
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
                
                order_number = order_result.get("order_number")
                order_total = order_result.get("total")
                
                # Send success message to customer
                success_message = i18n.get_text("ORDER_CONFIRMED_SUCCESS", user_id=user_id).format(
                    order_number=order_number,
                    order_total=order_total
                )
                
                await query.edit_message_text(
                    success_message,
                    parse_mode="HTML",
                    reply_markup=self._get_order_success_keyboard(user_id)
                )
                
                self.logger.info("✅ ORDER CREATED: #%s for user %s", order_number, user_id)
                
            else:
                error_msg = order_result.get("error", i18n.get_text("ERROR_UNKNOWN_OCCURRED", user_id=user_id))
                self.logger.error("❌ ORDER CREATION FAILED: %s", error_msg)
                await query.edit_message_text(
                    i18n.get_text("ORDER_CREATION_FAILED", user_id=user_id).format(error_msg=error_msg),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_cart_keyboard(user_id)
                )
                
        except Exception as e:
            self.logger.error("❌ ORDER CREATION ERROR: %s", e)
            await query.edit_message_text(
                i18n.get_text("ORDER_CREATION_ERROR", user_id=user_id),
                parse_mode="HTML",
                reply_markup=self._get_back_to_cart_keyboard(user_id)
            )

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
                await query.edit_message_text(
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

            await query.edit_message_text(
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
                        "display_name": product.name,
                        "options": {}
                    }
            
            # Handle legacy product option patterns (from sub-menus)
            # These map to specific product variants with options
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
        """Get simplified cart keyboard with Edit Cart button"""
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("EDIT_CART", user_id=user_id), callback_data="cart_edit_mode")],
            [
                InlineKeyboardButton(i18n.get_text("CLEAR_CART", user_id=user_id), callback_data="cart_clear_confirm"),
                InlineKeyboardButton(i18n.get_text("CHECKOUT", user_id=user_id), callback_data="cart_checkout"),
            ],
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
        """Get keyboard for cart actions"""
        keyboard = [
            [
                InlineKeyboardButton(i18n.get_text("CLEAR_CART", user_id=user_id), callback_data="cart_clear_confirm"),
                InlineKeyboardButton(i18n.get_text("CHECKOUT", user_id=user_id), callback_data="cart_checkout"),
            ],
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
        """Get keyboard for delivery method selection"""
        keyboard = [
            [
                InlineKeyboardButton(get_delivery_method_name("pickup", user_id), callback_data="delivery_pickup"),
                InlineKeyboardButton(get_delivery_method_name("delivery", user_id), callback_data="delivery_delivery"),
            ],
            [InlineKeyboardButton(i18n.get_text("BACK_TO_CART", user_id=user_id), callback_data="cart_view")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_delivery_address_choice_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Get keyboard for delivery address choice (use saved or enter new)"""
        keyboard = [
            [
                InlineKeyboardButton(i18n.get_text("USE_SAVED_ADDRESS", user_id=user_id), callback_data="delivery_address_use_saved"),
                InlineKeyboardButton(i18n.get_text("ENTER_NEW_ADDRESS", user_id=user_id), callback_data="delivery_address_new_address"),
            ],
            [InlineKeyboardButton(i18n.get_text("BACK_TO_CART", user_id=user_id), callback_data="cart_view")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_order_confirmation_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Get keyboard for order confirmation"""
        keyboard = [
            [
                InlineKeyboardButton(i18n.get_text("CONFIRM_ORDER", user_id=user_id), callback_data="confirm_order"),
                InlineKeyboardButton(i18n.get_text("CANCEL", user_id=user_id), callback_data="cart_view"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_order_success_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Get keyboard for successful order"""
        keyboard = [
            [
                InlineKeyboardButton(i18n.get_text("NEW_ORDER", user_id=user_id), callback_data="menu_main"),
                InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="menu_main"),
            ],
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
            message += i18n.get_text("DELIVERY_METHOD_LABEL", user_id=user_id).format(
                method=cart_info.get('delivery_method', 'pickup').title()
            ) + "\n"
            
            if cart_info.get('delivery_method') == 'delivery' and cart_info.get('delivery_address'):
                message += i18n.get_text("DELIVERY_ADDRESS_LABEL", user_id=user_id).format(
                    address=cart_info.get('delivery_address')
                ) + "\n"
            
            message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for i, item in enumerate(cart_items, 1):
                item_total = item.get("unit_price", 0) * item.get("quantity", 1)
                # Translate product name
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
            message += i18n.get_text("CONFIRM_ORDER_PROMPT", user_id=user_id)

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
            confirmation_message += i18n.get_text("DELIVERY_METHOD_LABEL", user_id=user_id).format(
                method=cart_info.get('delivery_method', 'pickup').title()
            ) + "\n"
            
            if cart_info.get('delivery_method') == 'delivery' and cart_info.get('delivery_address'):
                confirmation_message += i18n.get_text("DELIVERY_ADDRESS_LABEL", user_id=user_id).format(
                    address=cart_info.get('delivery_address')
                ) + "\n"
            
            confirmation_message += "\n"
            
            for i, item in enumerate(cart_items, 1):
                item_total = item.get("unit_price", 0) * item.get("quantity", 1)
                confirmation_message += f"""
<b>{i}.</b> 📦 <b>{item.get('product_name', i18n.get_text('PRODUCT_UNKNOWN', user_id=user_id))}</b>
   🔢 {i18n.get_text("CART_QUANTITY_LABEL", user_id=user_id)}: {item.get('quantity', 1)}
   💰 {i18n.get_text("CART_PRICE_LABEL", user_id=user_id)}: ₪{item.get('unit_price', 0):.2f}
   💵 {i18n.get_text("CART_SUBTOTAL_LABEL", user_id=user_id)}: ₪{item_total:.2f}

"""

            confirmation_message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💸 <b>{i18n.get_text("CART_TOTAL", user_id=user_id).format(total=cart_total)}</b>

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
