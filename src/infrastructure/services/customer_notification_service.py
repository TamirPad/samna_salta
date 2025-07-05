"""
Customer Notification Service

Handles sending notifications to customers about order status updates.
"""

import logging

from telegram import Bot
from telegram.error import TelegramError

from src.application.dtos.order_dtos import OrderInfo
from src.domain.entities.customer_entity import Customer as DomainCustomer
from src.domain.repositories.customer_repository import CustomerRepository
from src.infrastructure.services.notification_utils import (
    format_order_details,
    send_telegram_message,
)
from src.infrastructure.utilities.i18n import tr


class CustomerNotificationService:
    """Service for sending notifications to customers"""

    def __init__(self, bot: Bot, customer_repository: CustomerRepository):
        self._bot = bot
        self._customer_repository = customer_repository
        self._logger = logging.getLogger(self.__class__.__name__)

    async def notify_order_status_update(self, order_info: OrderInfo) -> None:
        """Send order status update notification to customer"""
        self._logger.info(
            "📨 SENDING CUSTOMER NOTIFICATION: Order #%s", order_info.order_number
        )

        try:
            # Get customer by phone to find telegram ID
            customer = await self._get_customer_by_phone(order_info.customer_phone)
            if not customer:
                self._logger.warning(
                    "⚠️ CUSTOMER NOT FOUND: Phone %s", order_info.customer_phone
                )
                return

            # Create notification message
            message = self._format_status_update_message(order_info)

            # Send to customer
            await self._bot.send_message(
                chat_id=customer.telegram_id.value, text=message, parse_mode="HTML"
            )
            self._logger.info(
                "✅ CUSTOMER NOTIFICATION SENT: %s", customer.telegram_id.value
            )
        except TelegramError as e:
            self._logger.error(
                "❌ CUSTOMER NOTIFICATION FAILED: %s, Error: %s",
                customer.telegram_id.value,
                e,
            )
        except RuntimeError as e:
            self._logger.error("💥 CUSTOMER NOTIFICATION ERROR: %s", e, exc_info=True)

    async def notify_order_ready_for_pickup(self, order_info: OrderInfo) -> None:
        """Send special notification when order is ready for pickup"""
        self._logger.info(
            "📦 SENDING PICKUP NOTIFICATION: Order #%s", order_info.order_number
        )

        try:
            customer = await self._get_customer_by_phone(order_info.customer_phone)
            if not customer:
                return

            message = self._format_pickup_ready_message(order_info)
            await send_telegram_message(
                self._bot,
                customer.telegram_id.value,
                message,
                self._logger,
            )

        except RuntimeError as e:
            self._logger.error("💥 PICKUP NOTIFICATION ERROR: %s", e, exc_info=True)

    async def _get_customer_by_phone(self, phone_number: str) -> DomainCustomer | None:
        """Get customer by phone number"""
        try:
            # This is a simplified approach
            customers = await self._customer_repository.get_all_customers()
            for customer in customers:
                if customer.phone_number.value == phone_number:
                    return customer
            return None

        except RuntimeError as e:
            self._logger.error("💥 CUSTOMER LOOKUP ERROR: %s", e)
            return None

    def _format_status_update_message(self, order_info: OrderInfo) -> str:
        """Format order status update message for customer"""
        header = tr("CUSTOMER_ORDER_UPDATE_HEADER")
        return format_order_details(order_info, header)

    def _format_pickup_ready_message(self, order_info: OrderInfo) -> str:
        """Format special pickup ready message"""
        header = tr("CUSTOMER_ORDER_READY_HEADER")
        details = format_order_details(order_info, header)
        pickup_info = (
            "\n\n" + tr("CUSTOMER_PICKUP_DETAILS") + "\n" +
            tr("CUSTOMER_PICKUP_AVAILABLE") + "\n" +
            tr("CUSTOMER_PICKUP_LOCATION") + "\n" +
            tr("CUSTOMER_PICKUP_HOURS")
        )
        return details + pickup_info
