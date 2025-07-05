"""
Admin Handler

Handles admin-specific operations including order management, status updates, and analytics.
"""

import logging
from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.application.dtos.order_dtos import OrderInfo
from src.infrastructure.container.dependency_injection import get_container
from src.infrastructure.utilities.exceptions import (
    BusinessLogicError,
    OrderNotFoundError,
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
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /admin command - show admin dashboard"""
        user_id = update.effective_user.id
        self._logger.info(f"👑 ADMIN DASHBOARD: User {user_id}")

        # Check if user is admin
        if not await self._is_admin_user(user_id):
            await update.message.reply_text(
                "⛔ Access denied. Admin privileges required."
            )
            return

        # Show admin dashboard
        await self._show_admin_dashboard(update, context)

    @error_handler("admin_dashboard")
    async def handle_admin_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle admin dashboard callbacks"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        if not await self._is_admin_user(user_id):
            await query.message.reply_text("⛔ Access denied.")
            return

        data = query.data
        self._logger.info(f"👑 ADMIN CALLBACK: {data} by User {user_id}")

        if data == "admin_pending_orders":
            await self._show_pending_orders(query)
        elif data == "admin_active_orders":
            await self._show_active_orders(query)
        elif data == "admin_all_orders":
            await self._show_all_orders(query)
        elif data == "admin_update_status":
            await self._start_status_update(query, context)
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
            await self._show_admin_dashboard(update, context)

    async def _show_admin_dashboard(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
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
                raise Exception("Order status management system not available")
            
            self._logger.info("✅ ORDER STATUS USE CASE OBTAINED")
            
            pending_orders = await order_status_use_case.get_pending_orders()
            active_orders = await order_status_use_case.get_active_orders()
            
            self._logger.info(f"📊 STATS: {len(pending_orders)} pending, {len(active_orders)} active")

            dashboard_text = f"""
👑 <b>ADMIN DASHBOARD</b>

📊 <b>Order Statistics:</b>
⏳ Pending Orders: {len(pending_orders)}
🔄 Active Orders: {len(active_orders)}
📋 Total Today: {len(pending_orders) + len(active_orders)}

🛠️ <b>Quick Actions:</b>
"""

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
                [InlineKeyboardButton("📊 Analytics", callback_data="admin_analytics")],
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

        except Exception as e:
            self._logger.error(f"💥 DASHBOARD ERROR: {e}", exc_info=True)
            try:
                if update.callback_query:
                    await update.callback_query.message.reply_text(
                        "Error loading dashboard. Please try again."
                    )
                elif update.message:
                    await update.message.reply_text(
                        "Error loading dashboard. Please try again."
                    )
                else:
                    # Fallback - try to get the message from the update
                    message = getattr(update, 'message', None) or getattr(update, 'effective_message', None)
                    if message:
                        await message.reply_text(
                            "Error loading dashboard. Please try again."
                        )
            except Exception as reply_error:
                self._logger.error(f"💥 ERROR SENDING ERROR MESSAGE: {reply_error}")

    async def _show_analytics(self, query) -> None:
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

        except Exception as e:
            self._logger.error(f"💥 ANALYTICS ERROR: {e}", exc_info=True)
            await query.message.reply_text("Error generating analytics report.")

    async def _show_pending_orders(self, query) -> None:
        """Show pending orders"""
        try:
            order_status_use_case = (
                self._container.get_order_status_management_use_case()
            )
            orders = await order_status_use_case.get_pending_orders()

            if not orders:
                text = """
⏳ <b>PENDING ORDERS</b>

✅ No pending orders! All caught up.
"""
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🔙 Back to Dashboard", callback_data="admin_back"
                        )
                    ]
                ]
            else:
                text = f"""
⏳ <b>PENDING ORDERS ({len(orders)})</b>

📋 <b>Orders requiring attention:</b>
"""

                keyboard = []
                for order in orders[:10]:  # Show max 10 orders
                    order_summary = f"#{order.order_number} - {order.customer_name} - ₪{order.total:.2f}"
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
                text=text, parse_mode="HTML", reply_markup=reply_markup
            )

        except Exception as e:
            self._logger.error(f"💥 PENDING ORDERS ERROR: {e}", exc_info=True)
            await query.message.reply_text("Error loading pending orders.")

    async def _show_active_orders(self, query) -> None:
        """Show active orders (confirmed, preparing, ready)"""
        try:
            order_status_use_case = (
                self._container.get_order_status_management_use_case()
            )
            orders = await order_status_use_case.get_active_orders()

            if not orders:
                text = """
🔄 <b>ACTIVE ORDERS</b>

✅ No active orders at the moment.
"""
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🔙 Back to Dashboard", callback_data="admin_back"
                        )
                    ]
                ]
            else:
                text = f"""
🔄 <b>ACTIVE ORDERS ({len(orders)})</b>

📋 <b>Orders in progress:</b>
"""

                keyboard = []
                for order in orders[:10]:
                    status_emoji = {
                        "confirmed": "✅",
                        "preparing": "👨‍🍳",
                        "ready": "🛍️",
                    }.get(order.status, "📋")
                    order_summary = (
                        f"{status_emoji} #{order.order_number} - {order.customer_name}"
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
                text=text, parse_mode="HTML", reply_markup=reply_markup
            )

        except Exception as e:
            self._logger.error(f"💥 ACTIVE ORDERS ERROR: {e}", exc_info=True)
            await query.message.reply_text("Error loading active orders.")

    async def _show_all_orders(self, query) -> None:
        """Show all orders"""
        try:
            order_repository = self._container.get_order_repository()
            all_orders_data = await order_repository.get_all_orders()

            text = f"""
📋 <b>ALL ORDERS ({len(all_orders_data)})</b>

📊 <b>Recent orders:</b>
"""

            keyboard = []
            # Show last 10 orders
            for order_data in all_orders_data[-10:]:
                status_emoji = {
                    "pending": "⏳",
                    "confirmed": "✅",
                    "preparing": "👨‍🍳",
                    "ready": "🛍️",
                    "completed": "✅",
                    "cancelled": "❌",
                }.get(order_data.get("status"), "📋")

                order_summary = f"{status_emoji} #{order_data['order_number']} - ₪{order_data.get('total', 0):.2f}"
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            order_summary,
                            callback_data=f"admin_order_{order_data['id']}",
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
                text=text, parse_mode="HTML", reply_markup=reply_markup
            )

        except Exception as e:
            self._logger.error(f"💥 ALL ORDERS ERROR: {e}", exc_info=True)
            await query.message.reply_text("Error loading orders.")

    async def _show_order_details(self, query, order_id: int) -> None:
        """Show detailed order information with status update options"""
        try:
            order_repository = self._container.get_order_repository()
            customer_repository = self._container.get_customer_repository()

            order_data = await order_repository.get_order_by_id(order_id)
            if not order_data:
                await query.message.reply_text("Order not found.")
                return

            customer = await customer_repository.find_by_id(order_data["customer_id"])
            if not customer:
                await query.message.reply_text("Customer not found for this order.")
                return

            # Format order details
            status_emoji = {
                "pending": "⏳",
                "confirmed": "✅",
                "preparing": "👨‍🍳",
                "ready": "🛍️",
                "completed": "✅",
                "cancelled": "❌",
            }.get(order_data.get("status"), "📋")

            delivery_emoji = (
                "🚚" if order_data.get("delivery_method") == "delivery" else "🏪"
            )

            text = f"""
📋 <b>ORDER DETAILS</b>

🔢 Order #: <code>{order_data['order_number']}</code>
{status_emoji} Status: <b>{order_data.get('status', 'pending').title()}</b>
📅 Date: {order_data.get('created_at', 'Unknown').strftime('%d/%m/%Y %H:%M') if order_data.get('created_at') else 'Unknown'}

👤 <b>Customer:</b>
👨‍💼 Name: <b>{customer.full_name.value}</b>
📞 Phone: <code>{customer.phone_number.value}</code>

🛒 <b>Items:</b>"""

            for item in order_data.get("items", []):
                options_text = ""
                if item.get("options"):
                    options_list = [f"{k}: {v}" for k, v in item["options"].items()]
                    options_text = f" ({', '.join(options_list)})"

                text += f"\n• {item['quantity']}x {item['product_name']}{options_text} - ₪{item['total_price']:.2f}"

            text += f"""

{delivery_emoji} <b>Delivery:</b>
📦 Method: <b>{order_data.get('delivery_method', 'pickup').title()}</b>"""

            if order_data.get("delivery_address"):
                text += f"\n📍 Address: {order_data['delivery_address']}"

            text += f"""

💰 <b>Payment:</b>
💵 Subtotal: ₪{order_data.get('subtotal', 0):.2f}
🚚 Delivery: ₪{order_data.get('delivery_charge', 0):.2f}
💳 <b>Total: ₪{order_data.get('total', 0):.2f}</b>
"""

            # Create status update buttons based on current status
            keyboard = []
            current_status = order_data.get("status", "pending")

            status_transitions = {
                "pending": [("✅ Confirm", "confirmed"), ("❌ Cancel", "cancelled")],
                "confirmed": [
                    ("👨‍🍳 Start Preparing", "preparing"),
                    ("❌ Cancel", "cancelled"),
                ],
                "preparing": [("🛍️ Ready", "ready"), ("❌ Cancel", "cancelled")],
                "ready": [("✅ Complete", "completed")],
                "completed": [],
                "cancelled": [],
            }

            available_transitions = status_transitions.get(current_status, [])
            if available_transitions:
                text += "\n🔄 <b>Status Actions:</b>"
                for button_text, new_status in available_transitions:
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                button_text,
                                callback_data=f"admin_status_{order_id}_{new_status}",
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
                text=text, parse_mode="HTML", reply_markup=reply_markup
            )

        except Exception as e:
            self._logger.error(f"💥 ORDER DETAILS ERROR: {e}", exc_info=True)
            await query.message.reply_text("Error loading order details.")

    async def _update_order_status(
        self, query, order_id: int, new_status: str, admin_telegram_id: int
    ) -> None:
        """Update order status"""
        try:
            order_status_use_case = (
                self._container.get_order_status_management_use_case()
            )

            updated_order = await order_status_use_case.update_order_status(
                order_id=order_id,
                new_status=new_status,
                admin_telegram_id=admin_telegram_id,
            )

            status_emoji = {
                "pending": "⏳",
                "confirmed": "✅",
                "preparing": "👨‍🍳",
                "ready": "🛍️",
                "completed": "✅",
                "cancelled": "❌",
            }.get(new_status, "📋")

            await query.message.reply_text(
                f"{status_emoji} <b>Status Updated!</b>\n\n"
                f"Order #{updated_order.order_number} has been updated to: <b>{new_status.title()}</b>\n"
                f"Customer: {updated_order.customer_name}\n"
                f"Total: ₪{updated_order.total:.2f}",
                parse_mode="HTML",
            )

            # Return to dashboard
            await self._show_admin_dashboard(query, None)

        except BusinessLogicError as e:
            await query.message.reply_text(f"❌ Error: {e.user_message}")
        except Exception as e:
            self._logger.error(f"💥 STATUS UPDATE ERROR: {e}", exc_info=True)
            await query.message.reply_text(
                "Error updating order status. Please try again."
            )

    async def _start_status_update(
        self, query, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Start status update conversation"""
        await query.edit_message_text(
            "🔄 <b>UPDATE ORDER STATUS</b>\n\n"
            "Please enter the Order ID you want to update:",
            parse_mode="HTML",
        )
        return AWAITING_ORDER_ID

    async def _is_admin_user(self, telegram_id: int) -> bool:
        """Check if user has admin privileges"""
        try:
            self._logger.info(f"🔐 CHECKING ADMIN STATUS: User {telegram_id}")
            
            customer_repository = self._container.get_customer_repository()
            if not customer_repository:
                self._logger.error("❌ CUSTOMER REPOSITORY NOT FOUND")
                return False
                
            from src.domain.value_objects.telegram_id import TelegramId

            customer = await customer_repository.find_by_telegram_id(
                TelegramId(telegram_id)
            )
            
            is_admin = customer and customer.is_admin
            self._logger.info(f"🔐 ADMIN CHECK RESULT: User {telegram_id} - Admin: {is_admin}")
            
            return is_admin

        except Exception as e:
            self._logger.error(f"💥 ADMIN CHECK ERROR: User {telegram_id}, Error: {e}", exc_info=True)
            return False


def register_admin_handlers(application):
    """Register admin handlers with the application"""
    admin_handler = AdminHandler()

    # Register command handlers
    application.add_handler(CommandHandler("admin", admin_handler.handle_admin_command))

    # Register callback query handlers for admin operations
    application.add_handler(
        CallbackQueryHandler(admin_handler.handle_admin_callback, pattern="^admin_")
    )
