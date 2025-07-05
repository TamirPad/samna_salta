"""
Cart Handler

Handles shopping cart operations using Clean Architecture patterns.
"""

import logging

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from src.application.dtos.cart_dtos import (
    AddToCartRequest,
    CartItemInfo,
    GetCartResponse,
)
from src.application.dtos.order_dtos import CreateOrderRequest
from src.infrastructure.container.dependency_injection import get_container
from src.infrastructure.utilities.exceptions import BusinessLogicError, error_handler
from src.infrastructure.utilities.helpers import format_price, translate_product_name
from src.presentation.telegram_bot.keyboards.menu import (
    get_cart_keyboard,
    get_main_menu_keyboard,
)
from src.infrastructure.utilities.i18n import tr

logger = logging.getLogger(__name__)


class CartHandler:
    """Handler for cart operations"""

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._container = get_container()

    @error_handler("add_to_cart")
    async def handle_add_to_cart(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle adding items to cart"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        callback_data = query.data

        self._logger.info("🛒 ADD TO CART: User %s clicked: %s", user_id, callback_data)

        try:
            # Parse callback data to extract product information
            product_info = self._parse_callback_data(callback_data)

            if not product_info:
                self._logger.error(
                    "❌ INVALID CALLBACK: Could not parse %s", callback_data
                )
                await query.edit_message_text(
                    tr("INVALID_PRODUCT_SELECTION")
                )
                return

            self._logger.info("📦 PARSED PRODUCT: %s", product_info)

            # Get cart management use case
            cart_use_case = self._container.get_cart_management_use_case()

            # Create add to cart request
            add_request = AddToCartRequest(
                telegram_id=user_id,
                product_id=product_info["product_id"],
                quantity=1,
                options=product_info.get("options", {}),
            )

            self._logger.info("📝 ADD REQUEST: %s", add_request)

            # Add to cart
            response = await cart_use_case.add_to_cart(add_request)

            if response.success:
                cart_summary = response.cart_summary
                item_count = len(cart_summary.items) if cart_summary else 0
                cart_total = cart_summary.total if cart_summary else 0.0

                self._logger.info(
                    "✅ ADD SUCCESS: %s added. Cart: %d items, ₪%.2f",
                    product_info["display_name"],
                    item_count,
                    cart_total,
                )

                await query.edit_message_text(
                    tr("ADD_SUCCESS").format(
                        item=product_info["display_name"],
                        total=cart_total,
                        count=item_count,
                    ),
                    parse_mode="HTML",
                    reply_markup=self._get_post_add_keyboard(),
                )
            else:
                self._logger.error("❌ ADD FAILED: %s", response.error_message)
                await query.edit_message_text(
                    tr("ADD_FAILURE").format(
                        item=product_info["display_name"],
                        error=response.error_message,
                    ),
                    reply_markup=self._get_back_to_menu_keyboard(),
                )

        except BusinessLogicError as e:
            self._logger.error(
                "💥 ADD TO CART ERROR: User %s, Callback: %s, Error: %s",
                user_id,
                callback_data,
                e,
                exc_info=True,
            )
            await query.edit_message_text(
                tr("ADD_ERROR"),
                reply_markup=self._get_back_to_menu_keyboard(),
            )

    def _parse_callback_data(self, callback_data: str) -> dict | None:
        """Parse callback data to extract product information"""
        self._logger.debug("🔍 PARSING CALLBACK: %s", callback_data)

        # Direct add patterns (add_product_name)
        if callback_data.startswith("add_"):
            product_name = callback_data[4:]  # Remove "add_" prefix
            return self._get_product_info_by_name(product_name)

        # Product selection patterns (kubaneh_classic, samneh_smoked, etc.)
        parts = callback_data.split("_")

        if len(parts) < 2:
            self._logger.warning("⚠️ UNKNOWN CALLBACK PATTERN: %s", callback_data)
            return None

        product_type = parts[0]

        # Kubaneh patterns: kubaneh_classic, kubaneh_seeded, etc.
        if product_type == "kubaneh":
            kubaneh_type = parts[1] if len(parts) > 1 else "classic"
            
            # Get the Hebrew translation for the kubaneh type
            type_key = f"KUBANEH_{kubaneh_type.upper()}"
            type_display = tr(type_key)

            return {
                "product_id": 1,  # Kubaneh product ID
                "display_name": tr("KUBANEH_DISPLAY_NAME").format(type=type_display),
                "options": {"type": kubaneh_type},
            }

        # Samneh patterns: samneh_smoked, samneh_not_smoked
        if product_type == "samneh":
            smoking = "smoked" if parts[1] == "smoked" else "not_smoked"
            
            # Get the Hebrew translation for the samneh type
            type_key = f"SAMNEH_{smoking.upper()}"
            type_display = tr(type_key)

            return {
                "product_id": 2,  # Samneh product ID
                "display_name": tr("SAMNEH_DISPLAY_NAME").format(type=type_display),
                "options": {"smoking": smoking.replace("_", " ")},
            }

        # Red Bisbas patterns: red_bisbas_small, red_bisbas_large
        if product_type == "red" and len(parts) > 1 and parts[1] == "bisbas":
            size = parts[2] if len(parts) > 2 else "small"
            
            # Get the Hebrew translation for the size
            size_key = f"SIZE_{size.upper()}"
            size_display = tr(size_key)

            return {
                "product_id": 3,  # Red Bisbas product ID
                "display_name": tr("RED_BISBAS_DISPLAY_NAME").format(size=size_display),
                "options": {"size": size},
            }

        self._logger.warning("⚠️ UNKNOWN CALLBACK PATTERN: %s", callback_data)
        return None

    def _get_product_info_by_name(self, product_name: str) -> dict | None:
        """Get product info by name"""
        self._logger.debug("🔍 PRODUCT NAME LOOKUP: %s", product_name)

        # Product mapping with proper IDs
        product_map = {
            "hilbeh": {
                "product_id": 7,  # Hilbeh product ID
                "display_name": tr("PRODUCT_HILBEH"),
                "options": {},
            },
            "hawaij_soup": {
                "product_id": 4,  # Hawaij soup spice product ID
                "display_name": tr("PRODUCT_HAWAIJ_SOUP"),
                "options": {},
            },
            "hawaij_soup_spice": {
                "product_id": 4,  # Hawaij soup spice product ID
                "display_name": tr("PRODUCT_HAWAIJ_SOUP"),
                "options": {},
            },
            "hawaij_coffee": {
                "product_id": 5,  # Hawaij coffee spice product ID
                "display_name": tr("PRODUCT_HAWAIJ_COFFEE"),
                "options": {},
            },
            "hawaij_coffee_spice": {
                "product_id": 5,  # Hawaij coffee spice product ID
                "display_name": tr("PRODUCT_HAWAIJ_COFFEE"),
                "options": {},
            },
            "white_coffee": {
                "product_id": 6,  # White coffee product ID
                "display_name": tr("PRODUCT_WHITE_COFFEE"),
                "options": {},
            },
        }

        result = product_map.get(product_name)
        if result:
            self._logger.debug("✅ PRODUCT FOUND: %s", result)
        else:
            self._logger.warning("⚠️ PRODUCT NOT FOUND: %s", product_name)

        return result

    def _get_post_add_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard shown after adding item to cart"""
        keyboard = [
            [InlineKeyboardButton(tr("VIEW_CART"), callback_data="cart_view")],
            [InlineKeyboardButton(tr("CONTINUE_SHOPPING"), callback_data="menu_main")],
            [InlineKeyboardButton(tr("SEND_ORDER"), callback_data="cart_send_order")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @error_handler("cart_view")
    async def handle_view_cart(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle viewing cart contents"""
        query = update.callback_query
        await query.answer()

        # CallbackQuery objects don't expose `effective_user`; use `from_user`.
        try:
            user_id = query.effective_user.id  # type: ignore[attr-defined]
        except AttributeError:
            user_id = query.from_user.id  # type: ignore[attr-defined]
        self._logger.info("🛒 VIEW CART: User %s", user_id)

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
                delivery_address=cart_summary.delivery_address if cart_summary else None,
                cart_total=cart_summary.total if cart_summary else 0.0,
            )

            # Display cart contents
            await self._display_cart_contents(query, get_cart_response)

        except BusinessLogicError as e:
            self._logger.warning("VIEW CART ERROR: User %s, Error: %s", user_id, e)
            await query.edit_message_text(
                tr("CART_EMPTY_OR_ERROR"),
                reply_markup=self._get_back_to_menu_keyboard(),
            )

    @error_handler("send_order")
    async def handle_send_order(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle sending the order"""
        query = update.callback_query
        await query.answer()

        # CallbackQuery objects don't expose `effective_user`; use `from_user`.
        try:
            user_id = query.effective_user.id  # type: ignore[attr-defined]
        except AttributeError:
            user_id = query.from_user.id  # type: ignore[attr-defined]
        self._logger.info("📤 SEND ORDER: User %s", user_id)

        try:
            # Get cart use case
            cart_use_case = self._container.get_cart_management_use_case()

            # Get order use case
            order_use_case = self._container.get_order_creation_use_case()

            # Get cart to ensure it exists and is not empty
            cart_response = await cart_use_case.get_cart(user_id)

            if not cart_response.success or not cart_response.cart_summary.items:
                self._logger.warning(
                    "⚠️ SEND ORDER: Cart empty or invalid for User %s", user_id
                )
                await query.edit_message_text(
                    tr("CART_EMPTY_ORDER"),
                    reply_markup=self._get_back_to_menu_keyboard(),
                )
                return

            self._logger.info("📝 CREATING ORDER from cart for User %s...", user_id)

            # Create order request from cart summary
            cart_summary = cart_response.cart_summary
            # CreateOrderRequest only accepts telegram_id, delivery_method, delivery_address, and notes
            order_request = CreateOrderRequest(
                telegram_id=user_id,
                # Use default delivery method and address from cart if available
                delivery_method=cart_summary.delivery_method,
                delivery_address=cart_summary.delivery_address,
            )

            # Create order
            order_response = await order_use_case.create_order(order_request)

            if order_response.success:
                order_info = order_response.order_info
                order_confirmation_text = self._format_order_confirmation(order_info)

                self._logger.info(
                    "✅ ORDER SENT: User %s, Order #%s", user_id, order_info.order_number
                )

                await query.edit_message_text(
                    order_confirmation_text,
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_menu_keyboard(),
                )

                # Clear the cart after sending the order
                await cart_use_case.clear_cart(user_id)
                self._logger.info("🛒 CART CLEARED for User %s", user_id)
            else:
                self._logger.error(
                    "❌ SEND ORDER FAILED for User %s: %s",
                    user_id,
                    order_response.error_message,
                )
                await query.edit_message_text(
                    tr("ORDER_SEND_PROBLEM"),
                    reply_markup=get_cart_keyboard(),
                )

        except BusinessLogicError as e:
            self._logger.error(
                "💥 SEND ORDER ERROR: User %s, Error: %s", user_id, e, exc_info=True
            )
            await query.edit_message_text(
                tr("ORDER_CREATE_ERROR").format(error=e),
                reply_markup=get_cart_keyboard(),
            )
        except Exception as e:
            self._logger.critical(
                "💥 UNEXPECTED SEND ORDER ERROR: User %s, Error: %s",
                user_id,
                e,
                exc_info=True,
            )
            await query.edit_message_text(
                tr("UNEXPECTED_ERROR"),
                reply_markup=self._get_back_to_menu_keyboard(),
            )

    def _format_order_confirmation(self, order_info) -> str:
        """Formats the order confirmation message."""
        items_text = "\n".join(
            [
                f"  - {item.quantity}x {translate_product_name(item.product_name, item.options)} @ {format_price(item.unit_price)}"
                for item in order_info.items
            ]
        )
        return (
            tr("ORDER_CONFIRMATION_HEADER") + "\n\n" +
            tr("ORDER_CONFIRMATION_THANKS") + "\n\n" +
            tr("ORDER_SUMMARY_TITLE") + "\n" +
            tr("ORDER_NUMBER_LABEL").format(number=order_info.order_number) + "\n" +
            tr("ORDER_TOTAL_LABEL").format(total=format_price(order_info.total)) + "\n\n" +
            tr("ORDER_ITEMS_LABEL") + "\n" +
            f"{items_text}"
        )

    async def _display_cart_contents(
        self, query: CallbackQuery, cart_response: GetCartResponse
    ) -> None:
        """Display cart contents and action buttons"""
        # CallbackQuery objects don't expose `effective_user`; use `from_user`.
        try:
            user_id = query.effective_user.id  # type: ignore[attr-defined]
        except AttributeError:
            user_id = query.from_user.id  # type: ignore[attr-defined]

        if not cart_response.success or not cart_response.cart_items:
            self._logger.info("🛒 CART is empty for User %s", user_id)
            await query.edit_message_text(
                text=tr("CART_EMPTY_TITLE") + "\n\n" + tr("CART_EMPTY_MESSAGE"),
                parse_mode="HTML",
                reply_markup=self._get_back_to_menu_keyboard(),
            )
            return

        self._logger.info("🛒 DISPLAYING cart for User %s", user_id)

        items_text = [
            f"<b>{translate_product_name(item.product_name, item.options)}</b> x{item.quantity} @ {format_price(item.unit_price)} = {format_price(item.total_price)}"
            for item in cart_response.cart_items
        ]

        cart_text = (
            tr("CART_TITLE") + "\n\n" + "\n".join(items_text) + "\n\n" +
            tr("CART_TOTAL").format(total=format_price(cart_response.cart_total))
        )

        await query.edit_message_text(
            text=cart_text,
            parse_mode="HTML",
            reply_markup=get_cart_keyboard(),
        )

    def _get_back_to_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Get a keyboard with a 'Back to Menu' button"""
        keyboard = [
            [InlineKeyboardButton(tr("BACK_MAIN_MENU"), callback_data="menu_main")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @error_handler("clear_cart")
    async def handle_clear_cart(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle clearing the cart"""
        query = update.callback_query
        await query.answer()

        # CallbackQuery objects don't expose `effective_user`; use `from_user`.
        try:
            user_id = query.effective_user.id  # type: ignore[attr-defined]
        except AttributeError:
            user_id = query.from_user.id  # type: ignore[attr-defined]
        self._logger.info("🗑️ CLEAR CART: User %s", user_id)

        try:
            # Get cart management use case
            cart_use_case = self._container.get_cart_management_use_case()

            # Clear cart
            clear_response = await cart_use_case.clear_cart(user_id)

            if clear_response.success:
                self._logger.info("✅ CART CLEARED for User %s", user_id)
                await query.edit_message_text(
                    tr("CART_CLEARED"),
                    reply_markup=self._get_back_to_menu_keyboard(),
                )
            else:
                self._logger.error(
                    "❌ CLEAR CART FAILED for User %s: %s",
                    user_id,
                    clear_response.error_message,
                )
                await query.edit_message_text(
                    tr("CART_CLEAR_FAILED").format(error=clear_response.error_message),
                    reply_markup=get_cart_keyboard(),
                )

        except BusinessLogicError as e:
            await query.edit_message_text(
                tr("CART_CLEAR_ERROR").format(error=e),
                reply_markup=self._get_back_to_menu_keyboard(),
            )
        except Exception as e:
            self._logger.critical(
                "💥 UNEXPECTED CLEAR CART ERROR: User %s, Error: %s",
                user_id,
                e,
                exc_info=True,
            )
            await query.edit_message_text(
                tr("UNEXPECTED_ERROR"),
                reply_markup=self._get_back_to_menu_keyboard(),
            )


def register_cart_handlers(application: Application):
    """Register all cart-related handlers"""
    cart_handler = CartHandler()

    # Callback query handlers for cart actions
    application.add_handler(
        CallbackQueryHandler(cart_handler.handle_view_cart, pattern="^cart_view$")
    )
    application.add_handler(
        CallbackQueryHandler(cart_handler.handle_clear_cart, pattern="^cart_clear$")
    )
    application.add_handler(
        CallbackQueryHandler(
            cart_handler.handle_send_order, pattern="^cart_send_order$"
        )
    )

    # General product add handler
    application.add_handler(
        CallbackQueryHandler(cart_handler.handle_add_to_cart, pattern="^add_")
    )

    # Specific product add handlers (for items with options)
    application.add_handler(
        CallbackQueryHandler(cart_handler.handle_add_to_cart, pattern="^kubaneh_")
    )
    application.add_handler(
        CallbackQueryHandler(cart_handler.handle_add_to_cart, pattern="^samneh_")
    )
    application.add_handler(
        CallbackQueryHandler(cart_handler.handle_add_to_cart, pattern="^red_bisbas_")
    )
    logger.info("🛒 Cart handlers registered")
