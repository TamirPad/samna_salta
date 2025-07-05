"""
Admin Notification Service

Handles sending notifications to admin users for important events like new orders.
"""

import logging

from telegram import Bot
from telegram.error import TelegramError

from src.application.dtos.order_dtos import OrderInfo
from src.domain.repositories.customer_repository import CustomerRepository
from src.infrastructure.services.notification_utils import format_order_details
from src.infrastructure.utilities.i18n import tr


class AdminNotificationService:
    """Service for sending notifications to admin users.

    The list of admin Telegram-IDs can come from two sources:
    1. `config_admin_ids` – passed in via the DI container (owner IDs that are
       **not** customers).
    2. Customers stored in the DB with `is_admin = True`.
    Both sources are merged so either mechanism continues to work.
    """

    def __init__(
        self,
        bot: Bot,
        customer_repository: CustomerRepository,
        *,
        config_admin_ids: list[int] | None = None,
    ):
        self._bot = bot
        self._customer_repository = customer_repository
        self._config_admin_ids: list[int] = config_admin_ids or []
        self._logger = logging.getLogger(self.__class__.__name__)

        # Log initialization
        self._logger.info("🏗️ ADMIN NOTIFICATION SERVICE INITIALIZED")
        self._logger.info("  🤖 Bot: %s", type(self._bot).__name__)
        self._logger.info(
            "  👤 Customer Repository: %s", type(self._customer_repository).__name__
        )
        if self._config_admin_ids:
            self._logger.info("  👑 Config admin IDs: %s", self._config_admin_ids)

    async def notify_new_order(self, order_info: OrderInfo) -> None:
        """Send new order notification to all admin users"""
        self._logger.info("📨 ===== ADMIN NOTIFICATION STARTED =====")
        self._logger.info(
            "📨 SENDING ADMIN NOTIFICATION: Order #%s", order_info.order_number
        )
        self._logger.info(
            "📨 Order Details: Customer=%s, Total=₪%.2f",
            order_info.customer_name,
            order_info.total,
        )

        try:
            # Get admin users
            self._logger.info("👑 SEARCHING FOR ADMIN USERS...")
            admin_users = await self._get_admin_users()
            if not admin_users:
                self._logger.warning(
                    "⚠️ NO ADMIN USERS FOUND - Cannot send notifications!"
                )
                return

            self._logger.info(
                "✅ FOUND %d ADMIN USERS: %s", len(admin_users), admin_users
            )

            # Create notification message
            self._logger.info("📝 STEP 2: Creating notification message...")
            message = self._format_new_order_message(order_info)
            self._logger.info("✅ MESSAGE CREATED: %d characters", len(message))
            self._logger.debug("📄 MESSAGE CONTENT:\n%s", message)

            # Send to each admin
            self._logger.info("📤 STEP 3: Sending notifications to admins...")
            successful_sends = 0
            failed_sends = 0

            for admin_telegram_id in admin_users:
                self._logger.info("📤 SENDING TO ADMIN: %s", admin_telegram_id)
                try:
                    result = await self._bot.send_message(
                        chat_id=admin_telegram_id, text=message, parse_mode="HTML"
                    )
                    self._logger.info(
                        "✅ NOTIFICATION SENT: Admin %s, Msg ID: %s",
                        admin_telegram_id,
                        result.message_id,
                    )
                    successful_sends += 1
                except TelegramError as e:
                    self._logger.error(
                        "❌ TELEGRAM ERROR: Admin %s, Error: %s", admin_telegram_id, e
                    )
                    failed_sends += 1
                except RuntimeError as e:
                    self._logger.error(
                        "💥 NOTIFICATION FAILED: Admin %s, Error: %s",
                        admin_telegram_id,
                        e,
                    )
                    failed_sends += 1

            self._logger.info("📊 NOTIFICATION SUMMARY:")
            self._logger.info("  ✅ Successful: %d", successful_sends)
            self._logger.info("  ❌ Failed: %d", failed_sends)
            self._logger.info("📨 ===== ADMIN NOTIFICATION COMPLETED =====")

        except RuntimeError as e:
            self._logger.error("💥 ADMIN NOTIFICATION ERROR: %s", e, exc_info=True)
            raise

    async def notify_order_status_update(
        self, order_info: OrderInfo, old_status: str
    ) -> None:
        """Send order status update notification to admin users"""
        self._logger.info("📨 SENDING STATUS UPDATE: Order #%s", order_info.order_number)

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
                        "❌ STATUS NOTIFICATION FAILED: Admin %s, Error: %s",
                        admin_telegram_id,
                        e,
                    )

        except RuntimeError as e:
            self._logger.error("💥 STATUS NOTIFICATION ERROR: %s", e, exc_info=True)

    async def _get_admin_users(self) -> list[int]:
        """Get list of admin user telegram IDs"""
        self._logger.info("👑 SEARCHING FOR ADMIN USERS...")
        try:
            # 1. Admin IDs provided via configuration --------------------------------
            admin_ids: set[int] = set(self._config_admin_ids)

            if self._config_admin_ids:
                self._logger.info(
                    "👑 %d admin IDs supplied from config", len(self._config_admin_ids)
                )

            # 2. Admin customers stored in DB ----------------------------------------
            customers = await self._customer_repository.get_all_customers()
            self._logger.info("👥 FOUND %d TOTAL CUSTOMERS", len(customers))

            for i, customer in enumerate(customers):
                self._logger.info(
                    "👤 Customer %d: ID=%s, Name=%s, TelegramID=%s, Admin=%s",
                    i + 1,
                    customer.id.value,
                    customer.full_name.value,
                    customer.telegram_id.value,
                    customer.is_admin,
                )

                if customer.is_admin:
                    admin_ids.add(customer.telegram_id.value)

            admin_users = sorted(list(admin_ids))

            self._logger.info(
                "👑 ADMIN SEARCH COMPLETE: Found %d unique admin users", len(admin_users)
            )
            if admin_users:
                self._logger.info("👑 ADMIN TELEGRAM IDS: %s", admin_users)
            else:
                self._logger.warning("⚠️ NO ADMIN USERS FOUND!")

            return admin_users

        except RuntimeError as e:
            self._logger.error("💥 ADMIN USER LOOKUP ERROR: %s", e, exc_info=True)
            return []

    def _format_new_order_message(self, order_info: OrderInfo) -> str:
        """Format new order notification message"""
        header = tr("ADMIN_NEW_ORDER_HEADER")
        return format_order_details(order_info, header)

    def _format_status_update_message(
        self, order_info: OrderInfo, old_status: str
    ) -> str:
        """Format order status update message"""
        header = tr("ADMIN_ORDER_STATUS_UPDATE_HEADER")
        return format_order_details(order_info, header)
