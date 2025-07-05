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
    get_cart_delivery_method_keyboard,
    get_clear_cart_confirmation_keyboard,
    get_delivery_address_choice_keyboard,
    get_back_to_cart_keyboard,
    get_delivery_address_required_keyboard,
    get_order_confirmation_keyboard,
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
                    tr("INVALID_PRODUCT_SELECTION"),
                    parse_mode="HTML"
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
                    parse_mode="HTML",
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
                parse_mode="HTML",
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
                    parse_mode="HTML",
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
        """Handle showing order confirmation preview"""
        query = update.callback_query
        await query.answer()

        # CallbackQuery objects don't expose `effective_user`; use `from_user`.
        try:
            user_id = query.effective_user.id  # type: ignore[attr-defined]
        except AttributeError:
            user_id = query.from_user.id  # type: ignore[attr-defined]
        self._logger.info("📤 SEND ORDER PREVIEW: User %s", user_id)

        try:
            # Get cart use case
            cart_use_case = self._container.get_cart_management_use_case()

            # Get cart to ensure it exists and is not empty
            cart_response = await cart_use_case.get_cart(user_id)

            if not cart_response.success or not cart_response.cart_summary.items:
                self._logger.warning(
                    "⚠️ SEND ORDER: Cart empty or invalid for User %s", user_id
                )
                await query.edit_message_text(
                    tr("CART_EMPTY_ORDER"),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_menu_keyboard(),
                )
                return

            # Check if delivery address is required
            cart_summary = cart_response.cart_summary
            if cart_summary.delivery_method == "delivery" and not cart_summary.delivery_address:
                self._logger.warning(
                    "⚠️ DELIVERY ADDRESS MISSING: User %s trying to order with delivery but no address", 
                    user_id
                )
                await query.edit_message_text(
                    tr("DELIVERY_ADDRESS_REQUIRED"),
                    parse_mode="HTML",
                    reply_markup=get_delivery_address_required_keyboard(),
                )
                return

            # Show order confirmation preview
            order_preview_text = self._format_order_preview(cart_summary)

            self._logger.info("📋 SHOWING ORDER PREVIEW for User %s", user_id)

            await query.edit_message_text(
                order_preview_text,
                parse_mode="HTML",
                reply_markup=get_order_confirmation_keyboard(),
            )

        except BusinessLogicError as e:
            self._logger.error(
                "💥 SEND ORDER PREVIEW ERROR: User %s, Error: %s", user_id, e, exc_info=True
            )
            await query.edit_message_text(
                tr("ORDER_CREATE_ERROR").format(error=e),
                parse_mode="HTML",
                reply_markup=get_cart_keyboard(),
            )
        except Exception as e:
            self._logger.critical(
                "💥 UNEXPECTED SEND ORDER PREVIEW ERROR: User %s, Error: %s",
                user_id,
                e,
                exc_info=True,
            )
            await query.edit_message_text(
                tr("UNEXPECTED_ERROR"),
                parse_mode="HTML",
                reply_markup=self._get_back_to_menu_keyboard(),
            )

    @error_handler("confirm_order")
    async def handle_confirm_order(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle final order confirmation and creation"""
        query = update.callback_query
        await query.answer()

        # CallbackQuery objects don't expose `effective_user`; use `from_user`.
        try:
            user_id = query.effective_user.id  # type: ignore[attr-defined]
        except AttributeError:
            user_id = query.from_user.id  # type: ignore[attr-defined]
        self._logger.info("✅ CONFIRM ORDER: User %s", user_id)

        try:
            # Get cart use case
            cart_use_case = self._container.get_cart_management_use_case()

            # Get order use case
            order_use_case = self._container.get_order_creation_use_case()

            # Get cart to ensure it exists and is not empty
            cart_response = await cart_use_case.get_cart(user_id)

            if not cart_response.success or not cart_response.cart_summary.items:
                self._logger.warning(
                    "⚠️ CONFIRM ORDER: Cart empty or invalid for User %s", user_id
                )
                await query.edit_message_text(
                    tr("CART_EMPTY_ORDER"),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_menu_keyboard(),
                )
                return

            self._logger.info("📝 CREATING ORDER from cart for User %s...", user_id)

            # Create order request from cart summary
            cart_summary = cart_response.cart_summary
            order_request = CreateOrderRequest(
                telegram_id=user_id,
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
                    "❌ CONFIRM ORDER FAILED for User %s: %s",
                    user_id,
                    order_response.error_message,
                )
                await query.edit_message_text(
                    tr("ORDER_SEND_PROBLEM"),
                    parse_mode="HTML",
                    reply_markup=get_cart_keyboard(),
                )

        except BusinessLogicError as e:
            self._logger.error(
                "💥 CONFIRM ORDER ERROR: User %s, Error: %s", user_id, e, exc_info=True
            )
            await query.edit_message_text(
                tr("ORDER_CREATE_ERROR").format(error=e),
                parse_mode="HTML",
                reply_markup=get_cart_keyboard(),
            )
        except Exception as e:
            self._logger.critical(
                "💥 UNEXPECTED CONFIRM ORDER ERROR: User %s, Error: %s",
                user_id,
                e,
                exc_info=True,
            )
            await query.edit_message_text(
                tr("UNEXPECTED_ERROR"),
                parse_mode="HTML",
                reply_markup=self._get_back_to_menu_keyboard(),
            )

    def _format_order_preview(self, cart_summary) -> str:
        """Formats the order preview message with delivery details."""
        items_text = "\n".join(
            [
                f"  - {item.quantity}x {translate_product_name(item.product_name, item.options)} @ {format_price(item.unit_price)} = {format_price(item.total_price)}"
                for item in cart_summary.items
            ]
        )
        
        # Format delivery method
        delivery_method_text = tr("PICKUP_FREE") if cart_summary.delivery_method == "pickup" else tr("DELIVERY_PAID")
        
        # Format delivery address (only show if delivery method is delivery)
        address_text = ""
        if cart_summary.delivery_method == "delivery" and cart_summary.delivery_address:
            address_text = f"\n{tr('DELIVERY_ADDRESS_LABEL')}: {cart_summary.delivery_address}"
        
        return (
            tr("ORDER_PREVIEW_TITLE") + "\n\n" +
            tr("ORDER_ITEMS_LABEL") + "\n" +
            f"{items_text}\n\n" +
            tr("ORDER_DELIVERY_METHOD_LABEL") + ": " + delivery_method_text + 
            address_text + "\n\n" +
            tr("ORDER_TOTAL_LABEL").format(total=format_price(cart_summary.total)) + "\n\n" +
            tr("ORDER_PREVIEW_CONFIRM_PROMPT")
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
                    tr("CART_CLEARED_SUCCESS"),
                    parse_mode="HTML",
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
                parse_mode="HTML",
                reply_markup=self._get_back_to_menu_keyboard(),
            )

    @error_handler("clear_cart_confirm")
    async def handle_clear_cart_confirm(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle clear cart confirmation prompt"""
        query = update.callback_query
        await query.answer()

        self._logger.info("🗑️ CLEAR CART CONFIRM: User %s", query.from_user.id)

        await query.edit_message_text(
            tr("CONFIRM_CLEAR_CART"),
            parse_mode="HTML",
            reply_markup=get_clear_cart_confirmation_keyboard(),
        )

    @error_handler("change_delivery")
    async def handle_change_delivery(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle delivery method change"""
        query = update.callback_query
        await query.answer()

        self._logger.info("🚚 CHANGE DELIVERY: User %s", query.from_user.id)

        await query.edit_message_text(
            tr("DELIVERY_METHOD_TITLE") + "\n\n" + tr("DELIVERY_METHOD_PROMPT"),
            parse_mode="HTML",
            reply_markup=get_cart_delivery_method_keyboard(),
        )

    @error_handler("delivery_method_update")
    async def handle_delivery_method_update(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle delivery method update"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        callback_data = query.data

        self._logger.info("🚚 DELIVERY UPDATE: User %s, Method: %s", user_id, callback_data)

        try:
            # Parse delivery method from callback data
            if callback_data == "cart_delivery_pickup":
                delivery_method = "pickup"
            elif callback_data == "cart_delivery_delivery":
                delivery_method = "delivery"
            else:
                await query.edit_message_text(
                    tr("DELIVERY_UPDATE_ERROR").format(error="Invalid delivery method"),
                    reply_markup=get_cart_keyboard(),
                )
                return

            # Get cart management use case
            cart_use_case = self._container.get_cart_management_use_case()

            # If delivery method is "delivery", check for delivery address
            if delivery_method == "delivery":
                # Check if customer has a delivery address
                customer_address = await cart_use_case.get_customer_delivery_address(user_id)
                
                if customer_address:
                    # Customer has an address, show option to use it or enter new one
                    self._logger.info("📍 CUSTOMER HAS ADDRESS: User %s", user_id)
                    await query.edit_message_text(
                        tr("DELIVERY_ADDRESS_CURRENT").format(address=customer_address),
                        parse_mode="HTML",
                        reply_markup=get_delivery_address_choice_keyboard(),
                    )
                    return
                else:
                    # Customer doesn't have an address, prompt for one
                    self._logger.info("📍 CUSTOMER NEEDS ADDRESS: User %s", user_id)
                    await query.edit_message_text(
                        tr("DELIVERY_ADDRESS_REQUIRED"),
                        parse_mode="HTML",
                        reply_markup=get_delivery_address_required_keyboard(),
                    )
                    return

            # For pickup method, just update it directly
            update_response = await cart_use_case.update_delivery_method(user_id, delivery_method)

            if update_response.success:
                self._logger.info("✅ DELIVERY UPDATED for User %s to %s", user_id, delivery_method)
                await query.edit_message_text(
                    tr("DELIVERY_UPDATED"),
                    reply_markup=self._get_back_to_cart_keyboard(),
                )
            else:
                self._logger.error(
                    "❌ DELIVERY UPDATE FAILED for User %s: %s",
                    user_id,
                    update_response.error_message,
                )
                await query.edit_message_text(
                    tr("DELIVERY_UPDATE_ERROR").format(error=update_response.error_message),
                    reply_markup=get_cart_keyboard(),
                )

        except BusinessLogicError as e:
            await query.edit_message_text(
                tr("DELIVERY_UPDATE_ERROR").format(error=e),
                reply_markup=get_cart_keyboard(),
            )
        except Exception as e:
            self._logger.critical(
                "💥 UNEXPECTED DELIVERY UPDATE ERROR: User %s, Error: %s",
                user_id,
                e,
                exc_info=True,
            )
            await query.edit_message_text(
                tr("UNEXPECTED_ERROR"),
                parse_mode="HTML",
                reply_markup=self._get_back_to_menu_keyboard(),
            )

    def _get_back_to_cart_keyboard(self) -> InlineKeyboardMarkup:
        """Get a keyboard with a 'Back to Cart' button"""
        keyboard = [
            [InlineKeyboardButton(tr("VIEW_CART"), callback_data="cart_view")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @error_handler("delivery_address_use_current")
    async def handle_use_current_address(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle using current delivery address"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        self._logger.info("📍 USE CURRENT ADDRESS: User %s", user_id)

        try:
            # Get cart management use case
            cart_use_case = self._container.get_cart_management_use_case()

            # Get customer's current address
            customer_address = await cart_use_case.get_customer_delivery_address(user_id)
            
            if not customer_address:
                await query.edit_message_text(
                    tr("DELIVERY_UPDATE_ERROR").format(error="No current address found"),
                    reply_markup=get_cart_keyboard(),
                )
                return

            # Update cart with delivery method and address
            address_response = await cart_use_case.update_delivery_address(user_id, customer_address)

            if address_response.success:
                self._logger.info("✅ CURRENT ADDRESS USED: User %s", user_id)
                await query.edit_message_text(
                    tr("DELIVERY_ADDRESS_SAVED_CART"),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_cart_keyboard(),
                )
            else:
                self._logger.error(
                    "❌ USE CURRENT ADDRESS FAILED: User %s, Error: %s",
                    user_id,
                    address_response.error_message,
                )
                await query.edit_message_text(
                    tr("DELIVERY_UPDATE_ERROR").format(error=address_response.error_message),
                    reply_markup=get_cart_keyboard(),
                )

        except Exception as e:
            self._logger.critical(
                "💥 UNEXPECTED USE CURRENT ADDRESS ERROR: User %s, Error: %s",
                user_id,
                e,
                exc_info=True,
            )
            await query.edit_message_text(
                tr("UNEXPECTED_ERROR"),
                parse_mode="HTML",
                reply_markup=self._get_back_to_menu_keyboard(),
            )

    @error_handler("delivery_address_enter_new")
    async def handle_enter_new_address(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle entering new delivery address"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        self._logger.info("📍 ENTER NEW ADDRESS: User %s", user_id)

        # Store user ID in context for later use
        context.user_data["awaiting_delivery_address"] = True
        context.user_data["user_id"] = user_id

        await query.edit_message_text(
            tr("DELIVERY_ADDRESS_PROMPT"),
            parse_mode="HTML",
            reply_markup=get_back_to_cart_keyboard(),
        )

        # Import here to avoid circular imports
        from src.presentation.telegram_bot.states import CART_DELIVERY_ADDRESS_INPUT
        return CART_DELIVERY_ADDRESS_INPUT

    @error_handler("delivery_address_input")
    async def handle_delivery_address_input(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle delivery address text input"""
        user_id = update.effective_user.id
        address = update.message.text.strip()

        self._logger.info("📍 ADDRESS INPUT: User %s, Length: %d", user_id, len(address))

        try:
            # Validate address length
            if len(address) < 10:
                await update.message.reply_text(
                    tr("ADDRESS_TOO_SHORT"),
                    parse_mode="HTML",
                )
                return CART_DELIVERY_ADDRESS_INPUT

            # Get cart management use case
            cart_use_case = self._container.get_cart_management_use_case()

            # Update delivery address
            address_response = await cart_use_case.update_delivery_address(user_id, address)

            if address_response.success:
                self._logger.info("✅ NEW ADDRESS SAVED: User %s", user_id)
                await update.message.reply_text(
                    tr("DELIVERY_ADDRESS_UPDATED").format(address=address),
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_cart_keyboard(),
                )
                
                # Clear context
                context.user_data.pop("awaiting_delivery_address", None)
                context.user_data.pop("user_id", None)
                
                # Import here to avoid circular imports
                from src.presentation.telegram_bot.states import END
                return END
            else:
                self._logger.error(
                    "❌ NEW ADDRESS SAVE FAILED: User %s, Error: %s",
                    user_id,
                    address_response.error_message,
                )
                await update.message.reply_text(
                    tr("DELIVERY_UPDATE_ERROR").format(error=address_response.error_message),
                    parse_mode="HTML",
                )
                return CART_DELIVERY_ADDRESS_INPUT

        except Exception as e:
            self._logger.critical(
                "💥 UNEXPECTED ADDRESS INPUT ERROR: User %s, Error: %s",
                user_id,
                e,
                exc_info=True,
            )
            await update.message.reply_text(
                tr("UNEXPECTED_ERROR"),
                parse_mode="HTML",
                reply_markup=self._get_back_to_menu_keyboard(),
            )
            
            # Clear context
            context.user_data.pop("awaiting_delivery_address", None)
            context.user_data.pop("user_id", None)
            
            # Import here to avoid circular imports
            from src.presentation.telegram_bot.states import END
            return END


def register_cart_handlers(application: Application):
    """Register all cart-related handlers"""
    from telegram.ext import ConversationHandler, MessageHandler, filters
    from src.presentation.telegram_bot.states import CART_DELIVERY_ADDRESS_INPUT, END
    
    cart_handler = CartHandler()

    # Delivery address conversation handler
    delivery_address_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                cart_handler.handle_enter_new_address, 
                pattern="^delivery_address_enter_new$"
            )
        ],
        states={
            CART_DELIVERY_ADDRESS_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, 
                    cart_handler.handle_delivery_address_input
                )
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cart_handler.handle_view_cart, pattern="^cart_view$")
        ],
        map_to_parent={
            END: -1,  # End conversation if it was started from another handler
        },
    )

    # Add conversation handler first
    application.add_handler(delivery_address_conv)

    # Callback query handlers for cart actions
    application.add_handler(
        CallbackQueryHandler(cart_handler.handle_view_cart, pattern="^cart_view$")
    )
    application.add_handler(
        CallbackQueryHandler(cart_handler.handle_clear_cart_confirm, pattern="^cart_clear_confirm$")
    )
    application.add_handler(
        CallbackQueryHandler(cart_handler.handle_clear_cart, pattern="^cart_clear_yes$")
    )
    application.add_handler(
        CallbackQueryHandler(cart_handler.handle_change_delivery, pattern="^cart_change_delivery$")
    )
    application.add_handler(
        CallbackQueryHandler(cart_handler.handle_delivery_method_update, pattern="^cart_delivery_")
    )
    
    # Delivery address handlers
    application.add_handler(
        CallbackQueryHandler(
            cart_handler.handle_use_current_address, 
            pattern="^delivery_address_use_current$"
        )
    )
    
    application.add_handler(
        CallbackQueryHandler(
            cart_handler.handle_send_order, pattern="^cart_send_order$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            cart_handler.handle_confirm_order, pattern="^order_confirm_yes$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            cart_handler.handle_view_cart, pattern="^order_confirm_no$"
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
