"""
Admin Handler for the Telegram bot.
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

from src.container import get_container
from src.utils.error_handler import BusinessLogicError, error_handler
from src.utils.i18n import i18n

# Conversation states
AWAITING_ORDER_ID, AWAITING_STATUS_UPDATE = range(2)

logger = logging.getLogger(__name__)


class AdminHandler:
    """Handler for admin operations"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.container = get_container()
        self.admin_service = self.container.get_admin_service()
        self.notification_service = self.container.get_notification_service()

    @error_handler("admin_dashboard")
    async def handle_admin_command(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /admin command - show admin dashboard"""
        user_id = update.effective_user.id
        self.logger.debug("👑 ADMIN DASHBOARD: User %s", user_id)

        # Check if user is admin
        if not await self._is_admin_user(user_id):
            await update.message.reply_text(
                i18n.get_text("ADMIN_ACCESS_DENIED", user_id=user_id)
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
            await query.message.reply_text(i18n.get_text("ADMIN_ACCESS_DENIED", user_id=user_id))
            return

        data = query.data
        self.logger.info("👑 ADMIN CALLBACK: %s by User %s", data, user_id)

        if data == "admin_pending_orders":
            await self._show_pending_orders(query)
        elif data == "admin_active_orders":
            await self._show_active_orders(query)
        elif data == "admin_all_orders":
            await self._show_all_orders(query)
        elif data == "admin_completed_orders":
            await self._show_completed_orders(query)
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
            self.logger.info("📊 LOADING ADMIN DASHBOARD")
            
            # Get user_id from update
            user_id = update.effective_user.id

            # Get order statistics
            pending_orders = await self.admin_service.get_pending_orders()
            active_orders = await self.admin_service.get_active_orders()
            completed_orders = await self.admin_service.get_completed_orders()
            today_orders = await self.admin_service.get_today_orders()

            self.logger.info(
                "📊 STATS: %s pending, %s active, %s completed, %s today",
                len(pending_orders),
                len(active_orders),
                len(completed_orders),
                len(today_orders),
            )

            dashboard_text = (
                i18n.get_text("ADMIN_DASHBOARD_TITLE", user_id=user_id) + "\n\n" +
                i18n.get_text("ADMIN_ORDER_STATS", user_id=user_id) + "\n" +
                i18n.get_text("ADMIN_PENDING_COUNT", user_id=user_id).format(count=len(pending_orders)) + "\n" +
                i18n.get_text("ADMIN_ACTIVE_COUNT", user_id=user_id).format(count=len(active_orders)) + "\n" +
                i18n.get_text("ADMIN_COMPLETED_COUNT", user_id=user_id).format(count=len(completed_orders)) + "\n" +
                i18n.get_text("ADMIN_TOTAL_TODAY", user_id=user_id).format(count=len(today_orders)) + "\n\n" +
                i18n.get_text("ADMIN_QUICK_ACTIONS", user_id=user_id)
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PENDING_ORDERS", user_id=user_id), callback_data="admin_pending_orders"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_ACTIVE_ORDERS", user_id=user_id), callback_data="admin_active_orders"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_ALL_ORDERS", user_id=user_id), callback_data="admin_all_orders"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_COMPLETED_ORDERS", user_id=user_id), callback_data="admin_completed_orders"
                    ),
                ],
                [InlineKeyboardButton(i18n.get_text("ADMIN_ANALYTICS", user_id=user_id), callback_data="admin_analytics")],
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
            self.logger.error("💥 DASHBOARD ERROR: %s", e, exc_info=True)
            await self._send_error_to_user(update)
        except Exception as e:
            self.logger.critical("💥 UNHANDLED DASHBOARD ERROR: %s", e, exc_info=True)
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
                i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=update.effective_user.id)
            )
            except Exception as e:
                self.logger.error(
                    "💥 CRITICAL: Failed to send error message to user %s: %s",
                    update.effective_user.id,
                    e,
                    exc_info=True,
                )

    async def _show_analytics(self, query: CallbackQuery) -> None:
        """Show business analytics report"""
        try:
            self.logger.info("📊 GENERATING ANALYTICS REPORT")

            # Get analytics data using admin service
            analytics_data = await self.admin_service.get_business_analytics()

            # Format the report
            report = f"""
📊 <b>Business Analytics Report</b>

📈 <b>Overview:</b>
• Total Orders: {analytics_data.get('total_orders', 0)}
• Total Revenue: ₪{analytics_data.get('total_revenue', 0):.2f}
• Average Order Value: ₪{analytics_data.get('avg_order_value', 0):.2f}

📋 <b>Current Status:</b>
• Pending Orders: {analytics_data.get('pending_orders', 0)}
• Active Orders: {analytics_data.get('active_orders', 0)}
• Completed Orders: {analytics_data.get('completed_orders', 0)}
• Orders Today: {analytics_data.get('today_orders', 0)}

<i>Report generated at {analytics_data.get('generated_at', datetime.now()).strftime('%Y-%m-%d %H:%M')}</i>
            """.strip()

            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=report, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 ANALYTICS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("ANALYTICS_ERROR"))
        except Exception as e:
            self.logger.critical("💥 CRITICAL ANALYTICS ERROR: %s", e, exc_info=True)
            await query.message.reply_text(i18n.get_text("ANALYTICS_CRITICAL_ERROR"))

    async def _show_pending_orders(self, query: CallbackQuery) -> None:
        """Show pending orders"""
        try:
            orders = await self.admin_service.get_pending_orders()

            if not orders:
                text = (
                    i18n.get_text("ADMIN_PENDING_ORDERS_TITLE", user_id=query.from_user.id) + "\n\n" + i18n.get_text("ADMIN_NO_PENDING_ORDERS", user_id=query.from_user.id)
                )
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                ]
            else:
                text = (
                    f"{i18n.get_text('ADMIN_PENDING_ORDERS_TITLE', user_id=query.from_user.id)} ({len(orders)})\n\n"
                    f"{i18n.get_text('ADMIN_PENDING_ORDERS_LIST', user_id=query.from_user.id)}"
                )

                keyboard = []
                for order in orders:  # Show all pending orders
                    order_summary = (
                        f"#{order['order_id']} - {order['customer_name']} - "
                        f"₪{order['total']:.2f}"
                    )
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order['order_id']}",
                            )
                        ]
                    )

                keyboard.append(
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 PENDING ORDERS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("PENDING_ORDERS_ERROR"))

    async def _show_active_orders(self, query: CallbackQuery) -> None:
        """Show active orders"""
        try:
            orders = await self.admin_service.get_active_orders()

            if not orders:
                text = i18n.get_text("ADMIN_ACTIVE_ORDERS_TITLE", user_id=query.from_user.id) + "\n\n" + i18n.get_text("ADMIN_NO_ACTIVE_ORDERS", user_id=query.from_user.id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                ]
            else:
                text = (
                    f"{i18n.get_text('ADMIN_ACTIVE_ORDERS_TITLE', user_id=query.from_user.id)} ({len(orders)})\n\n"
                    f"{i18n.get_text('ADMIN_ACTIVE_ORDERS_LIST', user_id=query.from_user.id)}"
                )
                keyboard = []
                for order in orders[:10]:  # Show max 10 orders
                    order_summary = (
                        f"#{order['order_id']} - {order['customer_name']} - "
                        f"{order['status'].capitalize()}"
                    )
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order['order_id']}",
                            )
                        ]
                    )
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 ACTIVE ORDERS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("ACTIVE_ORDERS_ERROR"))

    async def _show_all_orders(self, query: CallbackQuery) -> None:
        """Show all orders"""
        try:
            orders = await self.admin_service.get_all_orders()

            if not orders:
                text = i18n.get_text("ADMIN_ALL_ORDERS_TITLE", user_id=query.from_user.id) + "\n\n" + i18n.get_text("ADMIN_NO_ORDERS_FOUND", user_id=query.from_user.id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                ]
            else:
                text = f"{i18n.get_text('ADMIN_ALL_ORDERS_TITLE', user_id=query.from_user.id)} ({len(orders)})"
                keyboard = []
                for order in orders[:15]:  # Show max 15
                    order_summary = (
                        f"#{order['order_id']} - {order['customer_name']} - "
                        f"{order['status'].capitalize()}"
                    )
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order['order_id']}",
                            )
                        ]
                    )
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 ALL ORDERS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("ALL_ORDERS_ERROR"))

    async def _show_completed_orders(self, query: CallbackQuery) -> None:
        """Show completed (delivered) orders"""
        try:
            orders = await self.admin_service.get_completed_orders()

            if not orders:
                text = i18n.get_text("ADMIN_COMPLETED_ORDERS_TITLE", user_id=query.from_user.id) + "\n\n" + i18n.get_text("ADMIN_NO_COMPLETED_ORDERS", user_id=query.from_user.id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                ]
            else:
                text = f"{i18n.get_text('ADMIN_COMPLETED_ORDERS_TITLE', user_id=query.from_user.id)} ({len(orders)})"
                keyboard = []
                for order in orders[:15]:  # Show max 15
                    order_summary = (
                        f"#{order['order_id']} - {order['customer_name']} - "
                        f"₪{order['total']:.2f}"
                    )
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order['order_id']}",
                            )
                        ]
                    )
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 COMPLETED ORDERS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("ALL_ORDERS_ERROR"))

    async def _show_order_details(self, query: CallbackQuery, order_id: int) -> None:
        """Show details for a specific order."""
        try:
            self.logger.info("📊 SHOWING ORDER DETAILS FOR #%s", order_id)
            order_details = await self._get_formatted_order_details(order_id)

            if not order_details:
                await query.edit_message_text(i18n.get_text("ADMIN_ORDER_NOT_FOUND", user_id=query.from_user.id))
                return

            keyboard = self._create_order_details_keyboard(order_id)
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                order_details, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 ORDER DETAILS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("ORDER_DETAILS_ERROR"))

    async def _get_formatted_order_details(self, order_id: int, user_id: int = None) -> str | None:
        """Helper to get and format order details."""
        order_info = await self.admin_service.get_order_by_id(order_id)

        if not order_info:
            return None

        details = [
            i18n.get_text("ADMIN_ORDER_DETAILS_TITLE", user_id=user_id).format(number=order_info["order_number"], id=order_info["order_id"]),
            i18n.get_text("ADMIN_CUSTOMER_LABEL", user_id=user_id).format(name=order_info["customer_name"]),
            i18n.get_text("ADMIN_PHONE_LABEL", user_id=user_id).format(phone=order_info["customer_phone"]),
            i18n.get_text("ADMIN_STATUS_LABEL", user_id=user_id).format(status=order_info["status"].capitalize()),
            i18n.get_text("ADMIN_TOTAL_LABEL", user_id=user_id).format(amount=order_info["total"]),
            i18n.get_text("ADMIN_CREATED_LABEL", user_id=user_id).format(
                datetime=(order_info["created_at"] or datetime.utcnow()).strftime('%Y-%m-%d %H:%M')
            ),
        ]
        if order_info.get("items"):
            details.append(f"\n{i18n.get_text('ADMIN_ITEMS_LABEL', user_id=user_id)}")
            for item in order_info["items"]:
                price = item.get('total_price', item.get('price', 0))
                # Translate product name
                from src.utils.helpers import translate_product_name
                translated_name = translate_product_name(item["product_name"])
                details.append(
                    i18n.get_text("ADMIN_ITEM_LINE", user_id=user_id).format(
                        name=translated_name,
                        quantity=item["quantity"],
                        price=price
                    )
                )
        return "\n".join(details)

    def _create_order_details_keyboard(
        self, order_id: int, user_id: int = None
    ) -> list[list[InlineKeyboardButton]]:
        """Creates the keyboard for the order details view."""
        statuses = ["pending", "confirmed", "preparing", "ready", "delivered"]
        keyboard = [
            [
                InlineKeyboardButton(
                    i18n.get_text("ADMIN_SET_STATUS", user_id=user_id).format(status=status.capitalize()),
                    callback_data=f"admin_status_{order_id}_{status}",
                )
            ]
            for status in statuses
        ]
        keyboard.append(
            [InlineKeyboardButton(i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=user_id), callback_data="admin_back")]
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
            self.logger.info(
                "🔄 UPDATING STATUS for order #%s to %s by admin %s",
                order_id,
                new_status,
                admin_telegram_id,
            )

            success = await self.admin_service.update_order_status(
                order_id=order_id,
                new_status=new_status,
                admin_telegram_id=admin_telegram_id,
            )

            if success:
                await query.answer(i18n.get_text("ADMIN_STATUS_UPDATED", user_id=admin_telegram_id).format(status=new_status))
                await self._show_order_details(query, order_id)
            else:
                await query.message.reply_text(i18n.get_text("ADMIN_STATUS_UPDATE_ERROR", user_id=admin_telegram_id).format(error="Failed to update status"))

        except (BusinessLogicError, ValueError) as e:
            self.logger.error("💥 STATUS UPDATE ERROR: %s", e, exc_info=True)
            await query.message.reply_text(i18n.get_text("ADMIN_STATUS_UPDATE_ERROR", user_id=admin_telegram_id).format(error=e))

    async def _start_status_update(self, query: CallbackQuery) -> int:
        """Start conversation to update an order's status."""
        await query.message.reply_text(i18n.get_text("ADMIN_ORDER_ID_PROMPT", user_id=query.from_user.id))
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
            all_orders = await self.admin_service.get_all_orders()
            matching = next(
                (
                    o for o in all_orders
                    if o["order_number"] == order_id_input or o["order_number"].lstrip("#") == order_id_input
                ),
                None,
            )
            if matching:
                order_id = matching["order_id"]

        if order_id is None:
            await update.message.reply_text(i18n.get_text("ADMIN_ORDER_ID_NOT_FOUND", user_id=update.effective_user.id))
            return AWAITING_ORDER_ID

        # Fetch formatted details and send as a regular message with inline keyboard
        order_details = await self._get_formatted_order_details(order_id, update.effective_user.id)
        if not order_details:
            await update.message.reply_text(i18n.get_text("ADMIN_ORDER_ID_TRY_ANOTHER", user_id=update.effective_user.id))
            return AWAITING_ORDER_ID

        keyboard = self._create_order_details_keyboard(order_id, update.effective_user.id)
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            order_details, parse_mode="HTML", reply_markup=reply_markup
        )

        context.user_data["order_id_for_status_update"] = order_id
        return AWAITING_STATUS_UPDATE

    async def _is_admin_user(self, telegram_id: int) -> bool:
        """Check if a user is an admin."""
        # Simple admin check - compare with configured admin chat ID
        config = self.container.get_config()
        admin_chat_id = getattr(config, 'admin', {}).get('chat_id', None)
        
        if admin_chat_id:
            # Convert to int if it's a string
            try:
                admin_id = int(admin_chat_id)
                return telegram_id == admin_id
            except (ValueError, TypeError):
                pass
        
        # Fallback: check if user ID matches common admin patterns
        # This is a simple fallback - in production you'd want a proper admin system
        return str(telegram_id) in ['598829473']  # Add your admin user IDs here


def register_admin_handlers(application: Application):
    """Register admin handlers"""
    handler = AdminHandler()

    # Admin command handler
    application.add_handler(CommandHandler("admin", handler.handle_admin_command))

    # Admin callback handlers
    application.add_handler(
        CallbackQueryHandler(handler.handle_admin_callback, pattern="^admin_")
    )

    # Admin conversation handler for status updates
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handler._start_status_update, pattern="^admin_update_status$")
        ],
        states={
            AWAITING_ORDER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler.show_order_details_for_status_update)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda u, c: ConversationHandler.END)
            ],
    )

    application.add_handler(conv_handler)


# Simple handler function for compatibility
async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple admin handler for compatibility"""
    handler = AdminHandler()
    
    if update.message and update.message.text == "/admin":
        return await handler.handle_admin_command(update, context)
    elif update.callback_query and update.callback_query.data.startswith("admin_"):
        return await handler.handle_admin_callback(update, context)
    
    return None


RESTART = "admin_dashboard"
END = ConversationHandler.END
