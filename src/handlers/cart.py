"""
Cart handler for managing shopping cart operations
"""

import logging
from typing import Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, filters, Application

from src.container import get_container
from src.utils.i18n import i18n
from src.utils.error_handler import handle_error

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

                # Send success message
                from src.utils.helpers import translate_product_name
                translated_product_name = translate_product_name(product_info['display_name'], product_info.get('options', {}), user_id)
                message = i18n.get_text("CART_SUCCESS_MESSAGE", user_id=user_id).format(
                    product_name=translated_product_name,
                    item_count=item_count,
                    cart_total=cart_total
                )

                await query.edit_message_text(
                    message,
                    parse_mode="HTML",
                    reply_markup=self._get_cart_success_keyboard(user_id),
                )
            else:
                self.logger.error("❌ ADD FAILED: User %s, Product: %s", user_id, product_info["display_name"])
                await query.edit_message_text(
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
                await query.edit_message_text(
                    i18n.get_text("CART_EMPTY_READY", user_id=user_id),
                    parse_mode="HTML",
                    reply_markup=self._get_empty_cart_keyboard(user_id),
                )
                return

            # Calculate total
            cart_total = cart_service.calculate_total(cart_items)

            # Build cart display
            message = i18n.get_text("CART_VIEW_TITLE", user_id=user_id) + "\n\n"
            
            for i, item in enumerate(cart_items, 1):
                item_total = item.get("unit_price", 0) * item.get("quantity", 1)
                # Translate product name
                from src.utils.helpers import translate_product_name
                translated_product_name = translate_product_name(item.get('product_name', 'Unknown Product'), item.get('options', {}), user_id)
                message += i18n.get_text("CART_ITEM_FORMAT", user_id=user_id).format(
                    index=i,
                    product_name=translated_product_name,
                    quantity=item.get('quantity', 1),
                    price=item.get('unit_price', 0),
                    item_total=item_total
                ) + "\n\n"

            message += i18n.get_text("CART_TOTAL", user_id=user_id).format(total=cart_total) + "\n\n"
            message += i18n.get_text("CART_WHAT_NEXT", user_id=user_id)

            await query.edit_message_text(
                message,
                parse_mode="HTML",
                reply_markup=self._get_cart_actions_keyboard(user_id),
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
                    reply_markup=self._get_empty_cart_keyboard(user_id),
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
                    reply_markup=self._get_empty_cart_keyboard(user_id),
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
                translated_product_name = translate_product_name(item.get('product_name', 'Unknown Product'), item.get('options', {}), user_id)
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
                error_msg = order_result.get("error", "Unknown error occurred")
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
        """Get keyboard for successful cart addition"""
        keyboard = [
            [
                InlineKeyboardButton(i18n.get_text("VIEW_CART", user_id=user_id), callback_data="cart_view"),
                InlineKeyboardButton(i18n.get_text("ADD_MORE", user_id=user_id), callback_data="menu_main"),
            ],
            [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="menu_main")],
        ]
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

    def _get_empty_cart_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Get keyboard for empty cart"""
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="menu_main")],
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
                InlineKeyboardButton(i18n.get_text("DELIVERY_PICKUP", user_id=user_id), callback_data="delivery_pickup"),
                InlineKeyboardButton(i18n.get_text("DELIVERY_DELIVERY", user_id=user_id), callback_data="delivery_delivery"),
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
            
            message += "\n"
            
            for i, item in enumerate(cart_items, 1):
                item_total = item.get("unit_price", 0) * item.get("quantity", 1)
                # Translate product name
                from src.utils.helpers import translate_product_name
                translated_product_name = translate_product_name(item.get('product_name', 'Unknown Product'), item.get('options', {}), user_id)
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
                confirmation_message += i18n.get_text("CART_ITEM_FORMAT", user_id=user_id).format(
                    index=i,
                    product_name=item.get('product_name', 'Unknown Product'),
                    quantity=item.get('quantity', 1),
                    price=item.get('unit_price', 0),
                    item_total=item_total
                ) + "\n\n"

            confirmation_message += i18n.get_text("CART_TOTAL", user_id=user_id).format(total=cart_total) + "\n\n"
            confirmation_message += i18n.get_text("CONFIRM_ORDER_PROMPT", user_id=user_id)

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
