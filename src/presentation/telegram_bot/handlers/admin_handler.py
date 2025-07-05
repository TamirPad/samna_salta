"""
Admin Handler

Handles admin-specific operations including order management, status updates, and analytics.
"""

import logging

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
from src.infrastructure.utilities.exceptions import (
    BusinessLogicError,
    error_handler,
)

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
                "⛔ Access denied. Admin privileges required."
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
            await query.message.reply_text("⛔ Access denied.")
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
            await self._start_status_update(query)
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
                "👑 <b>ADMIN DASHBOARD</b>\n\n"
                "📊 <b>Order Statistics:</b>\n"
                f"⏳ Pending Orders: {len(pending_orders)}\n"
                f"🔄 Active Orders: {len(active_orders)}\n"
                f"📋 Total Today: {len(pending_orders) + len(active_orders)}\n\n"
                "🛠️ <b>Quick Actions:</b>"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏳ Pending Orders", callback_data="admin_pending_orders"
                    ),
                    InlineKeyboardButton(
                        "🔄 Active Orders", callback_data="admin_active_orders"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "📋 All Orders", callback_data="admin_all_orders"
                    ),
                    InlineKeyboardButton(
                        "🔄 Update Status", callback_data="admin_update_status"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "📊 Analytics", callback_data="admin_analytics"
                    )
                ],
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
                    "An error occurred. Please try again or contact support."
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
            self._logger.error("💥 ANALYTICS ERROR: %s", e, exc_info=True)
            await query.message.reply_text("Error generating analytics report.")
        except Exception as e:
            self._logger.critical("💥 UNHANDLED ANALYTICS ERROR: %s", e, exc_info=True)
            await query.message.reply_text("A critical error occurred.")

    async def _show_pending_orders(self, query: CallbackQuery) -> None:
        """Show pending orders"""
        try:
            order_status_use_case = (
                self._container.get_order_status_management_use_case()
            )
            orders = await order_status_use_case.get_pending_orders()

            if not orders:
                text = (
                    "⏳ <b>PENDING ORDERS</b>\n\n"
                    "✅ No pending orders! All caught up."
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
                for order in orders[:10]:  # Show max 10 orders
                    order_summary = (
                        f"#{order.order_number} - {order.customer_name} - "
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
            self._logger.error("💥 PENDING ORDERS ERROR: %s", e, exc_info=True)
            await query.message.reply_text("Error loading pending orders.")

    async def _show_active_orders(self, query: CallbackQuery) -> None:
        """Show active orders"""
        try:
            order_status_use_case = (
                self._container.get_order_status_management_use_case()
            )
            orders = await order_status_use_case.get_active_orders()

            if not orders:
                text = (
                    "🔄 <b>ACTIVE ORDERS</b>\n\n"
                    "✅ No active orders at the moment."
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
                    f"🔄 <b>ACTIVE ORDERS ({len(orders)})</b>\n\n"
                    "📋 <b>Current active orders:</b>"
                )
                keyboard = []
                for order in orders[:10]:  # Show max 10 orders
                    order_summary = (
                        f"#{order.order_number} - {order.customer_name} - "
                        f"{order.status.value}"
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
            self._logger.error("💥 ACTIVE ORDERS ERROR: %s", e, exc_info=True)
            await query.message.reply_text("Error loading active orders.")

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
                        f"#{order.order_number} - {order.customer_name} - "
                        f"{order.status.value}"
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
            self._logger.error("💥 ALL ORDERS ERROR: %s", e, exc_info=True)
            await query.message.reply_text("Error loading all orders.")

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
            self._logger.error("💥 ORDER DETAILS ERROR: %s", e, exc_info=True)
            await query.message.reply_text("Error loading order details.")

    async def _get_formatted_order_details(self, order_id: int) -> str | None:
        """Helper to get and format order details."""
        order_use_case = self._container.get_order_status_management_use_case()
        order_info = await order_use_case.get_order_by_id(CustomerId(order_id))

        if not order_info:
            return None

        details = [
            f"📦 <b>Order #{order_info.order_number}</b>",
            f"👤 <b>Customer:</b> {order_info.customer_name}",
            f"📞 <b>Phone:</b> {order_info.customer_phone}",
            f" STATUS: {order_info.status.value}",
            f"💰 <b>Total:</b> ₪{order_info.total:.2f}",
            f"📅 <b>Created:</b> {order_info.created_at.strftime('%Y-%m-%d %H:%M')}",
        ]
        if order_info.items:
            details.append("\n🛒 <b>Items:</b>")
            for item in order_info.items:
                details.append(
                    f"- {item.product_name} (x{item.quantity}) - ₪{item.price:.2f}"
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
        self, query: CallbackQuery, order_id: int, new_status: str, admin_telegram_id: int
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
        await query.message.reply_text("Please enter the Order ID to update:")
        return AWAITING_ORDER_ID

    async def show_order_details_for_status_update(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Show order details and prompt for status update."""
        order_id_str = update.message.text
        try:
            order_id = int(order_id_str)
            await self._show_order_details(update.callback_query, order_id)
            context.user_data["order_id_for_status_update"] = order_id
            return AWAITING_STATUS_UPDATE
        except (ValueError, AttributeError):
            await update.message.reply_text("Invalid Order ID. Please enter a number.")
            return AWAITING_ORDER_ID

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

    application.add_handler(
        CommandHandler("admin", admin_handler.handle_admin_command)
    )
    application.add_handler(
        CallbackQueryHandler(admin_handler.handle_admin_callback, pattern="^admin_")
    )
    application.add_handler(conversation_handler)

RESTART = "admin_dashboard"
END = ConversationHandler.END
