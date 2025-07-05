"""
Order Status Management Use Case

Handles the business logic for updating order statuses and notifications.
"""

import logging
from datetime import datetime
from typing import List, Optional

from ...domain.repositories.customer_repository import CustomerRepository
from ...domain.repositories.order_repository import OrderRepository
from ...domain.value_objects.customer_id import CustomerId
from ...infrastructure.services.admin_notification_service import (
    AdminNotificationService,
)
from ...infrastructure.services.customer_notification_service import (
    CustomerNotificationService,
)
from ...infrastructure.utilities.exceptions import (
    BusinessLogicError,
    OrderNotFoundError,
)
from ..dtos.order_dtos import OrderInfo, OrderItemInfo


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
        admin_notification_service: Optional[AdminNotificationService] = None,
        customer_notification_service: Optional[CustomerNotificationService] = None,
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
            f"📝 STATUS UPDATE: Order {order_id} → {new_status} by Admin {admin_telegram_id}"
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
                    f"Valid transitions from {old_status}: {', '.join(self.STATUS_TRANSITIONS.get(old_status, []))}"
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
                f"✅ STATUS UPDATED: Order #{order_info.order_number} {old_status} → {new_status}"
            )

            # Send notifications
            await self._send_status_notifications(order_info, old_status)

            return order_info

        except Exception as e:
            self._logger.error(
                f"💥 STATUS UPDATE ERROR: Order {order_id}, {e}", exc_info=True
            )
            raise

    async def get_orders_by_status(self, status: str) -> List[OrderInfo]:
        """Get all orders with a specific status"""
        self._logger.info(f"📋 GETTING ORDERS BY STATUS: {status}")

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

            self._logger.info(f"📊 FOUND {len(order_infos)} ORDERS with status {status}")
            return order_infos

        except Exception as e:
            self._logger.error(f"💥 GET ORDERS BY STATUS ERROR: {e}", exc_info=True)
            raise

    async def get_pending_orders(self) -> List[OrderInfo]:
        """Get all pending orders that need attention"""
        return await self.get_orders_by_status("pending")

    async def get_active_orders(self) -> List[OrderInfo]:
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
        order_items = []
        for item_data in order_data.get("items", []):
            order_item = OrderItemInfo(
                product_name=item_data["product_name"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                total_price=item_data["total_price"],
                options=item_data.get("options", {}),
            )
            order_items.append(order_item)

        return OrderInfo(
            order_id=order_data["id"],
            order_number=order_data["order_number"],
            customer_name=customer.full_name.value,
            customer_phone=customer.phone_number.value,
            items=order_items,
            delivery_method=order_data.get("delivery_method", "pickup"),
            delivery_address=order_data.get("delivery_address"),
            subtotal=order_data.get("subtotal", 0.0),
            delivery_charge=order_data.get("delivery_charge", 0.0),
            total=order_data.get("total", 0.0),
            status=order_data.get("status", "pending"),
            created_at=order_data.get("created_at", datetime.utcnow()),
        )

    async def _send_status_notifications(self, order_info: OrderInfo, old_status: str):
        """Send notifications for status updates"""
        try:
            # Send admin notification
            if self._admin_notification_service:
                await self._admin_notification_service.notify_order_status_update(
                    order_info, old_status
                )
                self._logger.info(
                    f"📨 ADMIN STATUS NOTIFICATION SENT: Order #{order_info.order_number}"
                )

            # Send customer notification
            if self._customer_notification_service:
                await self._customer_notification_service.notify_order_status_update(
                    order_info, old_status
                )
                self._logger.info(
                    f"📨 CUSTOMER STATUS NOTIFICATION SENT: Order #{order_info.order_number}"
                )

        except Exception as e:
            self._logger.error(f"⚠️ NOTIFICATION ERROR: {e}")
            # Don't fail status update if notifications fail
