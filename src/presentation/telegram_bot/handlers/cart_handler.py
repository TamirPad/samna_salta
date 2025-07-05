"""
Cart Handler

Handles shopping cart operations using Clean Architecture patterns.
"""

import logging
from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from src.application.dtos.cart_dtos import (
    AddToCartRequest,
    CartItemInfo,
    GetCartResponse,
)
from src.application.dtos.order_dtos import CreateOrderRequest
from src.infrastructure.container.dependency_injection import get_container
from src.infrastructure.utilities.exceptions import BusinessLogicError, error_handler
from src.infrastructure.utilities.helpers import format_price
from src.presentation.telegram_bot.keyboards.menu import (
    get_cart_keyboard,
    get_main_menu_keyboard,
)

logger = logging.getLogger(__name__)


class CartHandler:
    """Handler for cart operations"""

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._container = get_container()

    @error_handler("add_to_cart")
    async def handle_add_to_cart(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle adding items to cart"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        callback_data = query.data

        self._logger.info(f"🛒 ADD TO CART: User {user_id} clicked: {callback_data}")

        try:
            # Parse callback data to extract product information
            product_info = self._parse_callback_data(callback_data)

            if not product_info:
                self._logger.error(
                    f"❌ INVALID CALLBACK: Could not parse {callback_data}"
                )
                await query.edit_message_text(
                    "❌ Invalid product selection. Please try again."
                )
                return

            self._logger.info(f"📦 PARSED PRODUCT: {product_info}")

            # Get cart management use case
            cart_use_case = self._container.get_cart_management_use_case()

            # Create add to cart request
            add_request = AddToCartRequest(
                telegram_id=user_id,
                product_id=product_info["product_id"],
                quantity=1,
                options=product_info.get("options", {}),
            )

            self._logger.info(f"📝 ADD REQUEST: {add_request}")

            # Add to cart
            response = await cart_use_case.add_to_cart(add_request)

            if response.success:
                cart_summary = response.cart_summary
                item_count = len(cart_summary.items) if cart_summary else 0
                cart_total = cart_summary.total if cart_summary else 0.0

                self._logger.info(
                    f"✅ ADD SUCCESS: {product_info['display_name']} added. Cart: {item_count} items, ₪{cart_total:.2f}"
                )

                await query.edit_message_text(
                    f"✅ <b>{product_info['display_name']} added to cart!</b>\n\n"
                    f"🛒 Cart total: ₪{cart_total:.2f}\n"
                    f"📦 Items in cart: {item_count}",
                    parse_mode="HTML",
                    reply_markup=self._get_post_add_keyboard(),
                )
            else:
                self._logger.error(f"❌ ADD FAILED: {response.error_message}")
                await query.edit_message_text(
                    f"❌ Failed to add {product_info['display_name']} to cart\n\n"
                    f"Error: {response.error_message}",
                    reply_markup=self._get_back_to_menu_keyboard(),
                )

        except Exception as e:
            self._logger.error(
                f"💥 ADD TO CART ERROR: User {user_id}, Callback: {callback_data}, Error: {e}",
                exc_info=True,
            )
            await query.edit_message_text(
                "❌ An error occurred while adding to cart. Please try again.",
                reply_markup=self._get_back_to_menu_keyboard(),
            )

    def _parse_callback_data(self, callback_data: str) -> dict:
        """Parse callback data to extract product information"""
        self._logger.debug(f"🔍 PARSING CALLBACK: {callback_data}")

        # Direct add patterns (add_product_name)
        if callback_data.startswith("add_"):
            product_name = callback_data[4:]  # Remove "add_" prefix
            return self._get_product_info_by_name(product_name)

        # Product selection patterns (kubaneh_classic, samneh_smoked, etc.)
        parts = callback_data.split("_")

        if len(parts) >= 2:
            product_type = parts[0]

            # Kubaneh patterns: kubaneh_classic, kubaneh_seeded, etc.
            if product_type == "kubaneh":
                kubaneh_type = parts[1] if len(parts) > 1 else "classic"

                return {
                    "product_id": 1,  # Kubaneh product ID
                    "display_name": f"Kubaneh ({kubaneh_type.title()})",
                    "options": {"type": kubaneh_type},
                }

            # Samneh patterns: samneh_smoked, samneh_not_smoked
            elif product_type == "samneh":
                smoking = "smoked" if parts[1] == "smoked" else "not_smoked"

                return {
                    "product_id": 2,  # Samneh product ID
                    "display_name": f"Samneh ({smoking.replace('_', ' ').title()})",
                    "options": {"smoking": smoking.replace("_", " ")},
                }

            # Red Bisbas patterns: red_bisbas_small, red_bisbas_large
            elif product_type == "red" and len(parts) > 1 and parts[1] == "bisbas":
                size = parts[2] if len(parts) > 2 else "small"

                return {
                    "product_id": 3,  # Red Bisbas product ID
                    "display_name": f"Red Bisbas ({size.title()})",
                    "options": {"size": size},
                }

        self._logger.warning(f"⚠️ UNKNOWN CALLBACK PATTERN: {callback_data}")
        return None

    def _get_product_info_by_name(self, product_name: str) -> dict:
        """Get product info by name"""
        self._logger.debug(f"🔍 PRODUCT NAME LOOKUP: {product_name}")

        # Product mapping with proper IDs
        product_map = {
            "hilbeh": {
                "product_id": 7,  # Hilbeh product ID
                "display_name": "Hilbeh",
                "options": {},
            },
            "hawaij_soup": {
                "product_id": 4,  # Hawaij soup spice product ID
                "display_name": "Hawaij Soup Spice",
                "options": {},
            },
            "hawaij_soup_spice": {
                "product_id": 4,  # Hawaij soup spice product ID
                "display_name": "Hawaij Soup Spice",
                "options": {},
            },
            "hawaij_coffee": {
                "product_id": 5,  # Hawaij coffee spice product ID
                "display_name": "Hawaij Coffee Spice",
                "options": {},
            },
            "hawaij_coffee_spice": {
                "product_id": 5,  # Hawaij coffee spice product ID
                "display_name": "Hawaij Coffee Spice",
                "options": {},
            },
            "white_coffee": {
                "product_id": 6,  # White coffee product ID
                "display_name": "White Coffee",
                "options": {},
            },
        }

        result = product_map.get(product_name)
        if result:
            self._logger.debug(f"✅ PRODUCT FOUND: {result}")
        else:
            self._logger.warning(f"⚠️ PRODUCT NOT FOUND: {product_name}")

        return result

    def _get_post_add_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard shown after adding item to cart"""
        keyboard = [
            [InlineKeyboardButton("🛒 View Cart", callback_data="cart_view")],
            [InlineKeyboardButton("🍞 Continue Shopping", callback_data="menu_main")],
            [InlineKeyboardButton("📤 Send Order", callback_data="cart_send_order")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @error_handler("cart_view")
    async def handle_view_cart(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle viewing cart contents"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        self._logger.info(f"🛒 VIEW CART: User {user_id}")

        try:
            # Get cart management use case
            cart_use_case = self._container.get_cart_management_use_case()

            # Get cart contents using the correct method
            cart_response = await cart_use_case.get_cart(user_id)

            if not cart_response.success:
                await query.edit_message_text(
                    text=cart_response.error_message,
                    reply_markup=self._get_back_to_menu_keyboard(),
                )
                return

            # Convert to GetCartResponse format
            cart_summary = cart_response.cart_summary
            get_cart_response = GetCartResponse(
                success=True,
                cart_items=[
                    CartItemInfo(
                        product_id=item.product_id,
                        product_name=item.product_name,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        total_price=item.total_price,
                        options=item.options,
                    )
                    for item in cart_summary.items
                ]
                if cart_summary
                else [],
                delivery_method=cart_summary.delivery_method if cart_summary else None,
                delivery_address=cart_summary.delivery_address
                if cart_summary
                else None,
            )

            # Display cart contents
            await self._display_cart_contents(query, get_cart_response)

        except Exception as e:
            self._logger.error(f"💥 VIEW CART ERROR: {e}", exc_info=True)
            await query.edit_message_text(
                text="❌ Error loading cart. Please try again.",
                reply_markup=self._get_back_to_menu_keyboard(),
            )

    @error_handler("send_order")
    async def handle_send_order(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle sending order from cart"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        self._logger.info(f"📝🚀 SEND ORDER INITIATED: User {user_id}")

        try:
            # STEP 1: Get order creation use case
            self._logger.info("📝 STEP 1: Getting order creation use case...")
            order_creation_use_case = self._container.get_order_creation_use_case()
            if not order_creation_use_case:
                self._logger.error("💥 ORDER CREATION USE CASE NOT FOUND!")
                await query.edit_message_text(
                    "❌ Order system not available. Please try again later."
                )
                return
            self._logger.info("✅ STEP 1: Order creation use case obtained")

            # STEP 2: Check cart contents first
            self._logger.info("📝 STEP 2: Checking cart contents...")
            cart_use_case = self._container.get_cart_management_use_case()
            cart_response = await cart_use_case.get_cart(user_id)

            if not cart_response.success:
                self._logger.error(
                    f"❌ STEP 2: Cart check failed: {cart_response.error_message}"
                )
                await query.edit_message_text(
                    text=f"❌ Cart Error: {cart_response.error_message}",
                    reply_markup=self._get_back_to_menu_keyboard(),
                )
                return

            if not cart_response.cart_summary or not cart_response.cart_summary.items:
                self._logger.error("❌ STEP 2: Cart is empty!")
                await query.edit_message_text(
                    text="🛒 Your cart is empty. Please add some items first!",
                    reply_markup=self._get_back_to_menu_keyboard(),
                )
                return

            self._logger.info(
                f"✅ STEP 2: Cart has {len(cart_response.cart_summary.items)} items"
            )

            # STEP 3: Create order request
            self._logger.info("📝 STEP 3: Creating order request...")
            cart_summary = cart_response.cart_summary
            order_request = CreateOrderRequest(
                telegram_id=user_id,
                delivery_method=cart_summary.delivery_method or "pickup",
                delivery_address=cart_summary.delivery_address,
            )
            self._logger.info(
                f"✅ STEP 3: Order request created - Method: {order_request.delivery_method}"
            )

            # STEP 4: Create the order
            self._logger.info("📝 STEP 4: Creating order via use case...")
            order_response = await order_creation_use_case.create_order(order_request)

            if not order_response.success:
                self._logger.error(
                    f"❌ STEP 4: Order creation failed: {order_response.error_message}"
                )
                await query.edit_message_text(
                    text=f"❌ Order Failed: {order_response.error_message}",
                    reply_markup=self._get_back_to_menu_keyboard(),
                )
                return

            self._logger.info(
                f"✅ STEP 4: Order created successfully - Order #{order_response.order_info.order_number}"
            )

            # STEP 5: Check admin notification service
            self._logger.info("📝 STEP 5: Checking admin notification service...")
            admin_service = self._container.get_admin_notification_service()
            if admin_service:
                self._logger.info("✅ STEP 5: Admin notification service is available")
            else:
                self._logger.warning(
                    "⚠️ STEP 5: Admin notification service NOT available"
                )

            # STEP 6: Display success message
            self._logger.info("📝 STEP 6: Displaying success message...")
            success_message = self._format_order_confirmation(order_response.order_info)

            await query.edit_message_text(
                text=success_message,
                parse_mode="HTML",
                reply_markup=self._get_back_to_menu_keyboard(),
            )

            self._logger.info(
                f"🎉 ORDER COMPLETED: Order #{order_response.order_info.order_number} for User {user_id}"
            )

        except Exception as e:
            self._logger.error(
                f"💥 SEND ORDER ERROR: User {user_id}, Error: {e}", exc_info=True
            )
            await query.edit_message_text(
                text="❌ An error occurred while processing your order. Please try again.",
                reply_markup=self._get_back_to_menu_keyboard(),
            )

    def _format_order_confirmation(self, order_info) -> str:
        """Format order confirmation message"""
        self._logger.info(
            f"📄 FORMATTING ORDER CONFIRMATION: Order #{order_info.order_number}"
        )

        delivery_emoji = "🚚" if order_info.delivery_method == "delivery" else "🏪"

        message = """
🎉 <b>ORDER CONFIRMED!</b>

📋 <b>Order Details:</b>
🔢 Order #: <code>{order_info.order_number}</code>
⏳ Status: <b>{order_info.status.title()}</b>
📅 Date: {order_info.created_at.strftime('%d/%m/%Y %H:%M')}

👤 <b>Customer:</b>
👨‍💼 Name: <b>{order_info.customer_name}</b>
📞 Phone: <code>{order_info.customer_phone}</code>

🛒 <b>Your Items:</b>"""

        for item in order_info.items:
            options_text = ""
            if item.options:
                options_list = [f"{k}: {v}" for k, v in item.options.items()]
                options_text = f" ({', '.join(options_list)})"

            message += f"\n• {item.quantity}x {item.product_name}{options_text} - ₪{item.total_price:.2f}"

        message += """

{delivery_emoji} <b>Delivery:</b>
📦 Method: <b>{order_info.delivery_method.title()}</b>"""

        if order_info.delivery_address:
            message += f"\n📍 Address: {order_info.delivery_address}"

        message += """

💰 <b>Payment Summary:</b>
💵 Subtotal: ₪{order_info.subtotal:.2f}
🚚 Delivery: ₪{order_info.delivery_charge:.2f}
💳 <b>Total: ₪{order_info.total:.2f}</b>

✅ Your order has been received and will be processed shortly!
🕒 We'll keep you updated on the status.

Thank you for choosing Samna Salta! 🥧✨
"""
        return message

    async def _display_cart_contents(
        self, query, cart_response: GetCartResponse
    ) -> None:
        """Display cart contents with options"""
        if not cart_response.cart_items:
            message = """
🛒 <b>Your Cart</b>

Your cart is empty!
Browse our delicious menu to add some items.
"""
            keyboard = [
                [InlineKeyboardButton("🍞 Browse Menu", callback_data="menu_main")],
                [InlineKeyboardButton("🔙 Back", callback_data="menu_main")],
            ]
        else:
            # Calculate totals
            subtotal = sum(item.total_price for item in cart_response.cart_items)
            delivery_charge = (
                5.0 if cart_response.delivery_method == "delivery" else 0.0
            )
            total = subtotal + delivery_charge

            delivery_emoji = "🚚" if cart_response.delivery_method == "delivery" else "🏪"

            message = """
🛒 <b>Your Cart ({len(cart_response.cart_items)} items)</b>

<b>Items:</b>"""

            for item in cart_response.cart_items:
                options_text = ""
                if item.options:
                    options_list = [f"{k}: {v}" for k, v in item.options.items()]
                    options_text = f" ({', '.join(options_list)})"

                message += f"\n• {item.quantity}x {item.product_name}{options_text} - ₪{item.total_price:.2f}"

            delivery_method_display = (
                cart_response.delivery_method or "pickup"
            ).title()
            message += """

{delivery_emoji} <b>Delivery:</b> {delivery_method_display}"""

            if cart_response.delivery_address:
                message += f"\n📍 Address: {cart_response.delivery_address}"

            message += """

💰 <b>Summary:</b>
💵 Subtotal: ₪{subtotal:.2f}
🚚 Delivery: ₪{delivery_charge:.2f}
💳 <b>Total: ₪{total:.2f}</b>
"""

            keyboard = [
                [InlineKeyboardButton("📤 Send Order", callback_data="cart_send_order")],
                [InlineKeyboardButton("🍞 Add More Items", callback_data="menu_main")],
                [InlineKeyboardButton("🗑️ Clear Cart", callback_data="cart_clear")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")],
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=message, parse_mode="HTML", reply_markup=reply_markup
        )

    def _get_back_to_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard to go back to main menu"""
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]]
        return InlineKeyboardMarkup(keyboard)


def register_cart_handlers(application):
    """Register cart handlers with the application"""
    cart_handler = CartHandler()

    # Register callback query handlers for cart operations
    application.add_handler(
        CallbackQueryHandler(cart_handler.handle_view_cart, pattern="^cart_view$")
    )

    application.add_handler(
        CallbackQueryHandler(
            cart_handler.handle_send_order, pattern="^cart_send_order$"
        )
    )

    # Register add to cart handlers for direct add patterns
    application.add_handler(
        CallbackQueryHandler(cart_handler.handle_add_to_cart, pattern="^add_")
    )

    # Register add to cart handlers for product selection patterns
    application.add_handler(
        CallbackQueryHandler(
            cart_handler.handle_add_to_cart, pattern="^(kubaneh_|samneh_|red_bisbas_)"
        )
    )

    logger.info("✅ Cart handlers registered successfully")
