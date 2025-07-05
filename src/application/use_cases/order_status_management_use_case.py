"""
Order Status Management Use Case

Handles the business logic for updating order statuses and notifications.
"""

import logging
import inspect

from src.application.dtos.order_dtos import OrderInfo, OrderItemInfo
from src.domain.repositories.customer_repository import CustomerRepository
from src.domain.repositories.order_repository import OrderRepository
from src.domain.value_objects.customer_id import CustomerId
from src.infrastructure.services.admin_notification_service import (
    AdminNotificationService,
)
from src.infrastructure.services.customer_notification_service import (
    CustomerNotificationService,
)
from src.infrastructure.utilities.exceptions import (
    BusinessLogicError,
    OrderNotFoundError,
)


class OrderStatusManagementUseCase:
    """Use case for managing order status transitions"""

    # Valid status transitions
    STATUS_TRANSITIONS = {
        "pending": ["confirmed", "cancelled"],
        "confirmed": ["preparing", "cancelled"],
        "preparing": ["ready", "cancelled"],
        "ready": ["completed", "cancelled"],
        "completed": [],  # Terminal state
        "cancelled": [],  # Terminal state
    }

    STATUS_EMOJIS = {
        "pending": "⏳",
        "confirmed": "✅",
        "preparing": "👨‍🍳",
        "ready": "🛍️",
        "completed": "✅",
        "cancelled": "❌",
    }

    def __init__(
        self,
        order_repository: OrderRepository,
        customer_repository: CustomerRepository,
        admin_notification_service: AdminNotificationService | None = None,
        customer_notification_service: CustomerNotificationService | None = None,
    ):
        self._order_repository = order_repository
        self._customer_repository = customer_repository
        self._admin_notification_service = admin_notification_service
        self._customer_notification_service = customer_notification_service
        self._logger = logging.getLogger(self.__class__.__name__)

    async def update_order_status(
        self, order_id: int, new_status: str, admin_telegram_id: int
    ) -> OrderInfo:
        """Update order status with validation and notifications"""
        self._logger.info(
            "📝 STATUS UPDATE: Order %s → %s by Admin %s",
            order_id,
            new_status,
            admin_telegram_id,
        )

        try:
            # Get order
            order_data = await self._order_repository.get_order_by_id(order_id)
            if not order_data:
                raise OrderNotFoundError(f"Order {order_id} not found")

            old_status = order_data.get("status", "pending")

            # Validate status transition
            if not self._is_valid_status_transition(old_status, new_status):
                raise BusinessLogicError(
                    f"Invalid status transition: {old_status} → {new_status}. "
                    f"Valid transitions from {old_status}: "
                    f"{', '.join(self.STATUS_TRANSITIONS.get(old_status, []))}"
                )

            # Update status
            success = await self._order_repository.update_order_status(
                order_id, new_status
            )
            if not success:
                raise BusinessLogicError("Failed to update order status")

            # Get updated order data
            updated_order = await self._order_repository.get_order_by_id(order_id)
            if not updated_order:
                raise BusinessLogicError("Failed to retrieve updated order")

            # Get customer info
            customer = await self._customer_repository.find_by_id(
                CustomerId(updated_order["customer_id"])
            )
            if not customer:
                raise BusinessLogicError("Customer not found for order")

            # Create order info
            order_info = self._create_order_info(updated_order, customer)

            self._logger.info(
                "✅ STATUS UPDATED: Order #%s %s → %s",
                order_info.order_number,
                old_status,
                new_status,
            )

            # Send notifications
            await self._send_status_notifications(order_info, old_status)

            return order_info

        except (BusinessLogicError, OrderNotFoundError) as e:
            self._logger.error(
                "💥 STATUS UPDATE ERROR: Order %s, %s", order_id, e, exc_info=True
            )
            raise
        except (ValueError, TypeError) as e:
            self._logger.error(
                "💥 UNEXPECTED STATUS UPDATE ERROR: Order %s, %s",
                order_id,
                e,
                exc_info=True,
            )
            raise BusinessLogicError(
                "An unexpected error occurred while updating the order."
            ) from e

    async def get_orders_by_status(self, status: str) -> list[OrderInfo]:
        """Get all orders with a specific status"""
        self._logger.info("📋 GETTING ORDERS BY STATUS: %s", status)

        try:
            # This would require a new repository method
            # For now, we'll get all orders and filter
            all_orders = await self._order_repository.get_all_orders()
            filtered_orders = [
                order for order in all_orders if order.get("status") == status
            ]

            order_infos = []
            for order_data in filtered_orders:
                customer = await self._customer_repository.find_by_id(
                    CustomerId(order_data["customer_id"])
                )
                if customer:
                    order_info = self._create_order_info(order_data, customer)
                    order_infos.append(order_info)

            self._logger.info(
                "📊 FOUND %d ORDERS with status %s", len(order_infos), status
            )
            return order_infos

        except (ValueError, TypeError) as e:
            self._logger.error("💥 GET ORDERS BY STATUS ERROR: %s", e, exc_info=True)
            raise

    async def get_pending_orders(self) -> list[OrderInfo]:
        """Get all pending orders that need attention"""
        return await self.get_orders_by_status("pending")

    async def get_active_orders(self) -> list[OrderInfo]:
        """Get all active orders (confirmed, preparing, ready)"""
        active_statuses = ["confirmed", "preparing", "ready"]
        all_orders = await self._order_repository.get_all_orders()

        order_infos = []
        for order_data in all_orders:
            if order_data.get("status") in active_statuses:
                customer = await self._customer_repository.find_by_id(
                    CustomerId(order_data["customer_id"])
                )
                if customer:
                    order_info = self._create_order_info(order_data, customer)
                    order_infos.append(order_info)

        return order_infos

    def _is_valid_status_transition(self, current_status: str, new_status: str) -> bool:
        """Check if status transition is valid"""
        if current_status == new_status:
            return False  # No point in updating to same status

        valid_transitions = self.STATUS_TRANSITIONS.get(current_status, [])
        return new_status in valid_transitions

    def _create_order_info(self, order_data: dict, customer) -> OrderInfo:
        """Create OrderInfo from order data and customer"""
        # Convert items to OrderItemInfo objects
        order_items = [
            OrderItemInfo(
                product_name=item["product_name"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                total_price=item["total_price"],
                options=item.get("options", {}),
            )
            for item in order_data["items"]
        ]

        return OrderInfo(
            order_id=order_data["id"],
            order_number=order_data["order_number"],
            customer_name=customer.full_name.value,
            customer_phone=customer.phone_number.value,
            items=order_items,
            delivery_method=order_data["delivery_method"],
            delivery_address=order_data.get("delivery_address"),
            subtotal=order_data["subtotal"],
            delivery_charge=order_data["delivery_charge"],
            total=order_data["total"],
            status=order_data["status"],
            created_at=order_data["created_at"],
            notes=order_data.get("notes"),
        )

    async def _send_status_notifications(self, order_info: OrderInfo, old_status: str):
        """Send notifications for status update"""
        # Notify customer
        if self._customer_notification_service:
            res = self._customer_notification_service.notify_order_status_update(order_info)
            if inspect.iscoroutine(res):
                await res

        # Notify admins
        if self._admin_notification_service:
            res2 = self._admin_notification_service.notify_order_status_update(order_info, old_status)
            if inspect.iscoroutine(res2):
                await res2
