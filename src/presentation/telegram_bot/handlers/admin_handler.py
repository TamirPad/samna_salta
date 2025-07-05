"""
Admin Handler

Handles admin-specific operations including order management, status updates, and analytics.
"""

import logging
from datetime import datetime

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.domain.value_objects.customer_id import CustomerId
from src.domain.value_objects.telegram_id import TelegramId
from src.infrastructure.container.dependency_injection import get_container
from src.infrastructure.utilities.exceptions import BusinessLogicError, error_handler
from src.infrastructure.utilities.i18n import tr

# Conversation states
AWAITING_ORDER_ID, AWAITING_STATUS_UPDATE = range(2)

logger = logging.getLogger(__name__)


class AdminHandler:
    """Handler for admin operations"""

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._container = get_container()

    @error_handler("admin_dashboard")
    async def handle_admin_command(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /admin command - show admin dashboard"""
        user_id = update.effective_user.id
        self._logger.debug("👑 ADMIN DASHBOARD: User %s", user_id)

        # Check if user is admin
        if not await self._is_admin_user(user_id):
            await update.message.reply_text(
                tr("ADMIN_ACCESS_DENIED")
            )
            return

        # Show admin dashboard
        await self._show_admin_dashboard(update, None)

    @error_handler("admin_dashboard")
    async def handle_admin_callback(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle admin dashboard callbacks"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        if not await self._is_admin_user(user_id):
            await query.message.reply_text(tr("ADMIN_ACCESS_DENIED"))
            return

        data = query.data
        self._logger.info("👑 ADMIN CALLBACK: %s by User %s", data, user_id)

        if data == "admin_pending_orders":
            await self._show_pending_orders(query)
        elif data == "admin_active_orders":
            await self._show_active_orders(query)
        elif data == "admin_all_orders":
            await self._show_all_orders(query)
        elif data == "admin_update_status":
            return await self._start_status_update(query)
        elif data == "admin_analytics":
            await self._show_analytics(query)
        elif data.startswith("admin_order_"):
            order_id = int(data.split("_")[-1])
            await self._show_order_details(query, order_id)
        elif data.startswith("admin_status_"):
            # Format: admin_status_{order_id}_{new_status}
            parts = data.split("_")
            order_id = int(parts[2])
            new_status = parts[3]
            await self._update_order_status(query, order_id, new_status, user_id)
        elif data == "admin_back":
            await self._show_admin_dashboard(update, None)

    async def _show_admin_dashboard(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE | None
    ) -> None:
        """Show main admin dashboard"""
        try:
            self._logger.info("📊 LOADING ADMIN DASHBOARD")

            # Get order statistics
            order_status_use_case = (
                self._container.get_order_status_management_use_case()
            )

            if not order_status_use_case:
                self._logger.error("❌ ORDER STATUS USE CASE NOT FOUND")
                raise RuntimeError("Order status management system not available")

            self._logger.info("✅ ORDER STATUS USE CASE OBTAINED")

            pending_orders = await order_status_use_case.get_pending_orders()
            active_orders = await order_status_use_case.get_active_orders()

            self._logger.info(
                "📊 STATS: %s pending, %s active",
                len(pending_orders),
                len(active_orders),
            )

            dashboard_text = (
                tr("ADMIN_DASHBOARD_TITLE") + "\n\n" +
                tr("ADMIN_ORDER_STATS") + "\n" +
                tr("ADMIN_PENDING_COUNT").format(count=len(pending_orders)) + "\n" +
                tr("ADMIN_ACTIVE_COUNT").format(count=len(active_orders)) + "\n" +
                tr("ADMIN_TOTAL_TODAY").format(count=len(pending_orders) + len(active_orders)) + "\n\n" +
                tr("ADMIN_QUICK_ACTIONS")
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        tr("ADMIN_PENDING_ORDERS"), callback_data="admin_pending_orders"
                    ),
                    InlineKeyboardButton(
                        tr("ADMIN_ACTIVE_ORDERS"), callback_data="admin_active_orders"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        tr("ADMIN_ALL_ORDERS"), callback_data="admin_all_orders"
                    ),
                    InlineKeyboardButton(
                        tr("ADMIN_UPDATE_STATUS"), callback_data="admin_update_status"
                    ),
                ],
                [InlineKeyboardButton(tr("ADMIN_ANALYTICS"), callback_data="admin_analytics")],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=dashboard_text, parse_mode="HTML", reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    text=dashboard_text, parse_mode="HTML", reply_markup=reply_markup
                )

        except (BusinessLogicError, RuntimeError) as e:
            self._logger.error("💥 DASHBOARD ERROR: %s", e, exc_info=True)
            await self._send_error_to_user(update)
        except Exception as e:
            self._logger.critical("💥 UNHANDLED DASHBOARD ERROR: %s", e, exc_info=True)
            await self._send_error_to_user(update)

    async def _send_error_to_user(self, update: Update):
        """Sends a generic error message to the user."""
        message_sender = None
        if update.callback_query:
            message_sender = update.callback_query.message
        elif update.message:
            message_sender = update.message

        if message_sender:
            try:
                await message_sender.reply_text(
                    tr("ADMIN_ERROR_MESSAGE")
                )
            except Exception as e:
                self._logger.error(
                    "💥 CRITICAL: Failed to send error message to user %s: %s",
                    update.effective_user.id,
                    e,
                    exc_info=True,
                )

    async def _show_analytics(self, query: CallbackQuery) -> None:
        """Show business analytics report"""
        try:
            self._logger.info("📊 GENERATING ANALYTICS REPORT")

            # Get analytics data
            analytics_use_case = self._container.get_order_analytics_use_case()
            overview = await analytics_use_case.get_business_overview()

            # Format the report
            report = analytics_use_case.format_analytics_report(overview)

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔙 Back to Dashboard", callback_data="admin_back"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=report, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self._logger.error("💥 ANALYTICS ERROR: %s", e)
            await query.message.reply_text(tr("ANALYTICS_ERROR"))
        except Exception as e:
            self._logger.critical("💥 CRITICAL ANALYTICS ERROR: %s", e, exc_info=True)
            await query.message.reply_text(tr("ANALYTICS_CRITICAL_ERROR"))

    async def _show_pending_orders(self, query: CallbackQuery) -> None:
        """Show pending orders"""
        try:
            order_status_use_case = (
                self._container.get_order_status_management_use_case()
            )
            orders = await order_status_use_case.get_pending_orders()

            if not orders:
                text = (
                    "⏳ <b>PENDING ORDERS</b>\n\n" "✅ No pending orders! All caught up."
                )
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🔙 Back to Dashboard", callback_data="admin_back"
                        )
                    ]
                ]
            else:
                text = (
                    f"⏳ <b>PENDING ORDERS ({len(orders)})</b>\n\n"
                    "📋 <b>Orders requiring attention:</b>"
                )

                keyboard = []
                for order in orders:  # Show all pending orders
                    order_summary = (
                        f"#{order.order_number} (ID {order.order_id}) - {order.customer_name} - "
                        f"₪{order.total:.2f}"
                    )
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order.order_id}",
                            )
                        ]
                    )

                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "🔙 Back to Dashboard", callback_data="admin_back"
                        )
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self._logger.error("💥 PENDING ORDERS ERROR: %s", e)
            await query.message.reply_text(tr("PENDING_ORDERS_ERROR"))

    async def _show_active_orders(self, query: CallbackQuery) -> None:
        """Show active orders"""
        try:
            order_status_use_case = (
                self._container.get_order_status_management_use_case()
            )
            orders = await order_status_use_case.get_active_orders()

            if not orders:
                text = "🔄 <b>ACTIVE ORDERS</b>\n\n" "✅ No active orders at the moment."
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🔙 Back to Dashboard", callback_data="admin_back"
                        )
                    ]
                ]
            else:
                text = (
                    f"🔄 <b>ACTIVE ORDERS ({len(orders)})</b>\n\n"
                    "📋 <b>Current active orders:</b>"
                )
                keyboard = []
                for order in orders[:10]:  # Show max 10 orders
                    order_summary = (
                        f"#{order.order_number} (ID {order.order_id}) - {order.customer_name} - "
                        f"{getattr(order.status, 'value', str(order.status)).capitalize()}"
                    )
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order.order_id}",
                            )
                        ]
                    )
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "🔙 Back to Dashboard", callback_data="admin_back"
                        )
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self._logger.error("💥 ACTIVE ORDERS ERROR: %s", e)
            await query.message.reply_text(tr("ACTIVE_ORDERS_ERROR"))

    async def _show_all_orders(self, query: CallbackQuery) -> None:
        """Show all orders"""
        try:
            order_status_use_case = (
                self._container.get_order_status_management_use_case()
            )
            orders = await order_status_use_case.get_all_orders()

            if not orders:
                text = "📋 <b>ALL ORDERS</b>\n\n✅ No orders found."
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🔙 Back to Dashboard", callback_data="admin_back"
                        )
                    ]
                ]
            else:
                text = f"📋 <b>ALL ORDERS ({len(orders)})</b>"
                keyboard = []
                for order in orders[:15]:  # Show max 15
                    order_summary = (
                        f"#{order.order_number} (ID {order.order_id}) - {order.customer_name} - "
                        f"{getattr(order.status, 'value', str(order.status)).capitalize()}"
                    )
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order.order_id}",
                            )
                        ]
                    )
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "🔙 Back to Dashboard", callback_data="admin_back"
                        )
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self._logger.error("💥 ALL ORDERS ERROR: %s", e)
            await query.message.reply_text(tr("ALL_ORDERS_ERROR"))

    async def _show_order_details(self, query: CallbackQuery, order_id: int) -> None:
        """Show details for a specific order."""
        try:
            self._logger.info("📊 SHOWING ORDER DETAILS FOR #%s", order_id)
            order_details = await self._get_formatted_order_details(order_id)

            if not order_details:
                await query.edit_message_text("❌ Order not found.")
                return

            keyboard = self._create_order_details_keyboard(order_id)
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                order_details, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self._logger.error("💥 ORDER DETAILS ERROR: %s", e)
            await query.message.reply_text(tr("ORDER_DETAILS_ERROR"))

    async def _get_formatted_order_details(self, order_id: int) -> str | None:
        """Helper to get and format order details."""
        order_use_case = self._container.get_order_status_management_use_case()
        order_info = await order_use_case.get_order_by_id(order_id)

        if not order_info:
            return None

        details = [
            f"📦 <b>Order #{order_info.order_number}</b> (ID {order_info.order_id})",
            f"👤 <b>Customer:</b> {order_info.customer_name}",
            f"📞 <b>Phone:</b> {order_info.customer_phone}",
            f" STATUS: {getattr(order_info.status, 'value', str(order_info.status)).capitalize()}",
            f"💰 <b>Total:</b> ₪{order_info.total:.2f}",
            f"📅 <b>Created:</b> "
            f"{(order_info.created_at or datetime.utcnow()).strftime('%Y-%m-%d %H:%M')}",
        ]
        if order_info.items:
            details.append("\n🛒 <b>Items:</b>")
            for item in order_info.items:
                price = getattr(item, 'total_price', getattr(item, 'price', None))
                if price is None:
                    # Fallback to unit_price * quantity if total not provided
                    price = getattr(item, 'unit_price', 0.0) * getattr(item, 'quantity', 1)
                details.append(
                    f"- {item.product_name} (x{item.quantity}) - ₪{price:.2f}"
                )
        return "\n".join(details)

    def _create_order_details_keyboard(
        self, order_id: int
    ) -> list[list[InlineKeyboardButton]]:
        """Creates the keyboard for the order details view."""
        statuses = ["pending", "confirmed", "preparing", "ready", "delivered"]
        keyboard = [
            [
                InlineKeyboardButton(
                    f"Set to {status.capitalize()}",
                    callback_data=f"admin_status_{order_id}_{status}",
                )
            ]
            for status in statuses
        ]
        keyboard.append(
            [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_back")]
        )
        return keyboard

    async def _update_order_status(
        self,
        query: CallbackQuery,
        order_id: int,
        new_status: str,
        admin_telegram_id: int,
    ) -> None:
        """Update the status of an order."""
        try:
            self._logger.info(
                "🔄 UPDATING STATUS for order #%s to %s by admin %s",
                order_id,
                new_status,
                admin_telegram_id,
            )

            order_use_case = self._container.get_order_status_management_use_case()
            await order_use_case.update_order_status(
                order_id=order_id,
                new_status=new_status,
                admin_telegram_id=TelegramId(admin_telegram_id),
            )

            await query.answer(f"✅ Status updated to {new_status}")
            await self._show_order_details(query, order_id)

        except (BusinessLogicError, ValueError) as e:
            self._logger.error("💥 STATUS UPDATE ERROR: %s", e, exc_info=True)
            await query.message.reply_text(f"❌ Error updating status: {e}")

    async def _start_status_update(self, query: CallbackQuery) -> int:
        """Start conversation to update an order's status."""
        await query.message.reply_text(
            "Please enter the Order ID to update (the small number inside the \"ID ...\" parentheses).\n"
            "For example, if the line reads '#ORD-20250705... (ID 20) - John', you should send 20."
        )
        return AWAITING_ORDER_ID

    async def show_order_details_for_status_update(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Show order details and prompt for status update."""
        order_id_input = update.message.text.strip()

        # First, try numeric conversion for standard IDs
        order_id: int | None = None
        if order_id_input.isdigit():
            try:
                order_id = int(order_id_input)
            except OverflowError:
                order_id = None

        # Fallback: maybe user pasted the long order number like ORD-20250705...
        if order_id is None:
            order_status_use_case = self._container.get_order_status_management_use_case()
            all_orders = await order_status_use_case.get_all_orders()
            matching = next(
                (
                    o for o in all_orders
                    if o.order_number == order_id_input or o.order_number.lstrip("#") == order_id_input
                ),
                None,
            )
            if matching:
                order_id = matching.order_id

        if order_id is None:
            await update.message.reply_text("❌ Order not found. Make sure to send the numeric ID shown in the list.")
            return AWAITING_ORDER_ID

        # Fetch formatted details and send as a regular message with inline keyboard
        order_details = await self._get_formatted_order_details(order_id)
        if not order_details:
            await update.message.reply_text("❌ Order not found. Try another ID.")
            return AWAITING_ORDER_ID

        keyboard = self._create_order_details_keyboard(order_id)
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            order_details, parse_mode="HTML", reply_markup=reply_markup
        )

        context.user_data["order_id_for_status_update"] = order_id
        return AWAITING_STATUS_UPDATE

    async def _is_admin_user(self, telegram_id: int) -> bool:
        """Check if a user is an admin."""
        security_manager = self._container.get_security_manager()
        return security_manager.is_admin(TelegramId(telegram_id))


def register_admin_handlers(application: Application):
    """Register all admin command and callback handlers."""
    admin_handler = AdminHandler()

    conversation_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                admin_handler.handle_admin_callback, pattern="^admin_update_status$"
            )
        ],
        states={
            AWAITING_ORDER_ID: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    admin_handler.show_order_details_for_status_update,
                )
            ],
            AWAITING_STATUS_UPDATE: [
                CallbackQueryHandler(
                    admin_handler.handle_admin_callback, pattern="^admin_status_"
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", admin_handler.handle_admin_command)],
        map_to_parent={
            # End of conversation
            END: END,
            # Restart admin flow
            RESTART: "admin_dashboard",
        },
    )

    # The conversation handler must be registered BEFORE the generic admin callback handler
    # so that its entry point (admin_update_status) is not intercepted by the broader pattern.
    application.add_handler(CommandHandler("admin", admin_handler.handle_admin_command))
    application.add_handler(conversation_handler)
    application.add_handler(
        CallbackQueryHandler(admin_handler.handle_admin_callback, pattern="^admin_")
    )


RESTART = "admin_dashboard"
END = ConversationHandler.END
