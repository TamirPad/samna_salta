"""
Admin Notification Service

Handles sending notifications to admin users for important events like new orders.
"""

import logging
from typing import Any, Dict, List, Optional

from telegram import Bot
from telegram.error import TelegramError

from ...application.dtos.order_dtos import OrderInfo
from ...domain.repositories.customer_repository import CustomerRepository
from ...domain.value_objects.telegram_id import TelegramId


class AdminNotificationService:
    """Service for sending notifications to admin users"""

    def __init__(self, bot: Bot, customer_repository: CustomerRepository):
        self._bot = bot
        self._customer_repository = customer_repository
        self._logger = logging.getLogger(self.__class__.__name__)

        # Log initialization
        self._logger.info("🏗️ ADMIN NOTIFICATION SERVICE INITIALIZED")
        self._logger.info(f"  🤖 Bot: {type(self._bot).__name__}")
        self._logger.info(
            f"  👤 Customer Repository: {type(self._customer_repository).__name__}"
        )

    async def notify_new_order(self, order_info: OrderInfo) -> None:
        """Send new order notification to all admin users"""
        self._logger.info("📨 ===== ADMIN NOTIFICATION STARTED =====")
        self._logger.info(
            f"📨 SENDING ADMIN NOTIFICATION: Order #{order_info.order_number}"
        )
        self._logger.info(
            f"📨 Order Details: Customer={order_info.customer_name}, Total=₪{order_info.total:.2f}"
        )

        try:
            # Get admin users
            self._logger.info("👑 STEP 1: Finding admin users...")
            admin_users = await self._get_admin_users()
            if not admin_users:
                self._logger.warning(
                    "⚠️ NO ADMIN USERS FOUND - Cannot send notifications!"
                )
                return

            self._logger.info(f"✅ FOUND {len(admin_users)} ADMIN USERS: {admin_users}")

            # Create notification message
            self._logger.info("📝 STEP 2: Creating notification message...")
            message = self._format_new_order_message(order_info)
            self._logger.info(f"✅ MESSAGE CREATED: {len(message)} characters")
            self._logger.debug(f"📄 MESSAGE CONTENT:\n{message}")

            # Send to each admin
            self._logger.info("📤 STEP 3: Sending notifications to admins...")
            successful_sends = 0
            failed_sends = 0

            for admin_telegram_id in admin_users:
                self._logger.info(f"📤 SENDING TO ADMIN: {admin_telegram_id}")
                try:
                    result = await self._bot.send_message(
                        chat_id=admin_telegram_id, text=message, parse_mode="HTML"
                    )
                    self._logger.info(
                        f"✅ NOTIFICATION SENT SUCCESSFULLY: Admin {admin_telegram_id}, Message ID: {result.message_id}"
                    )
                    successful_sends += 1
                except TelegramError as e:
                    self._logger.error(
                        f"❌ TELEGRAM ERROR: Admin {admin_telegram_id}, Error: {e}"
                    )
                    failed_sends += 1
                except Exception as e:
                    self._logger.error(
                        f"💥 NOTIFICATION FAILED: Admin {admin_telegram_id}, Error: {e}",
                        exc_info=True,
                    )
                    failed_sends += 1

            self._logger.info("📊 NOTIFICATION SUMMARY:")
            self._logger.info(f"  ✅ Successful: {successful_sends}")
            self._logger.info(f"  ❌ Failed: {failed_sends}")
            self._logger.info("📨 ===== ADMIN NOTIFICATION COMPLETED =====")

        except Exception as e:
            self._logger.error(f"💥 ADMIN NOTIFICATION ERROR: {e}", exc_info=True)
            raise

    async def notify_order_status_update(
        self, order_info: OrderInfo, old_status: str
    ) -> None:
        """Send order status update notification to admin users"""
        self._logger.info(
            f"📨 SENDING STATUS UPDATE NOTIFICATION: Order #{order_info.order_number}"
        )

        try:
            admin_users = await self._get_admin_users()
            if not admin_users:
                return

            message = self._format_status_update_message(order_info, old_status)

            for admin_telegram_id in admin_users:
                try:
                    await self._bot.send_message(
                        chat_id=admin_telegram_id, text=message, parse_mode="HTML"
                    )
                except TelegramError as e:
                    self._logger.error(
                        f"❌ STATUS NOTIFICATION FAILED: Admin {admin_telegram_id}, Error: {e}"
                    )

        except Exception as e:
            self._logger.error(f"💥 STATUS NOTIFICATION ERROR: {e}", exc_info=True)

    async def _get_admin_users(self) -> List[int]:
        """Get list of admin user telegram IDs"""
        self._logger.info("👑 SEARCHING FOR ADMIN USERS...")
        try:
            # Get all customers who are admin users
            customers = await self._customer_repository.get_all_customers()
            self._logger.info(f"👥 FOUND {len(customers)} TOTAL CUSTOMERS")

            admin_users = []

            for i, customer in enumerate(customers):
                self._logger.info(
                    f"👤 Customer {i+1}: ID={customer.id.value}, Name={customer.full_name.value}, TelegramID={customer.telegram_id.value}, Admin={customer.is_admin}"
                )

                if customer.is_admin:
                    admin_users.append(customer.telegram_id.value)
                    self._logger.info(
                        f"  👑 ADMIN FOUND: {customer.full_name.value} (TelegramID: {customer.telegram_id.value})"
                    )

            self._logger.info(
                f"👑 ADMIN SEARCH COMPLETE: Found {len(admin_users)} admin users"
            )
            if admin_users:
                self._logger.info(f"👑 ADMIN TELEGRAM IDS: {admin_users}")
            else:
                self._logger.warning("⚠️ NO ADMIN USERS FOUND!")

            return admin_users

        except Exception as e:
            self._logger.error(f"💥 ADMIN USER LOOKUP ERROR: {e}", exc_info=True)
            return []

    def _format_new_order_message(self, order_info: OrderInfo) -> str:
        """Format new order notification message"""
        status_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "preparing": "👨‍🍳",
            "ready": "🛍️",
            "completed": "✅",
            "cancelled": "❌",
        }

        delivery_emoji = "🚚" if order_info.delivery_method == "delivery" else "🏪"

        message = """
🔔 <b>NEW ORDER RECEIVED!</b>

📋 <b>Order Details:</b>
🔢 Order #: <code>{order_info.order_number}</code>
{status_emoji.get(order_info.status, '📋')} Status: <b>{order_info.status.title()}</b>
📅 Date: {order_info.created_at.strftime('%d/%m/%Y %H:%M')}

👤 <b>Customer Info:</b>
👨‍💼 Name: <b>{order_info.customer_name}</b>
📞 Phone: <code>{order_info.customer_phone}</code>

🛒 <b>Items:</b>"""

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

Please process this order promptly! 🚀
"""
        return message

    def _format_status_update_message(
        self, order_info: OrderInfo, old_status: str
    ) -> str:
        """Format order status update notification message"""
        status_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "preparing": "👨‍🍳",
            "ready": "🛍️",
            "completed": "✅",
            "cancelled": "❌",
        }

        message = """
🔄 <b>ORDER STATUS UPDATE</b>

📋 Order #: <code>{order_info.order_number}</code>
👤 Customer: <b>{order_info.customer_name}</b>

📈 Status Changed:
{status_emoji.get(old_status, '📋')} <s>{old_status.title()}</s> → {status_emoji.get(order_info.status, '📋')} <b>{order_info.status.title()}</b>

💳 Total: ₪{order_info.total:.2f}
📦 Method: {order_info.delivery_method.title()}
"""
        return message
