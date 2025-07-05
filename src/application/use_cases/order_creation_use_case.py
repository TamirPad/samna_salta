"""
Order Creation Use Case

Handles the business logic for creating orders from cart items.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.application.dtos.order_dtos import (
    CreateOrderRequest,
    OrderCreationResponse,
    OrderInfo,
    OrderItemInfo,
)
from src.domain.repositories.cart_repository import CartRepository
from src.domain.repositories.customer_repository import CustomerRepository
from src.domain.repositories.order_repository import OrderRepository
from src.domain.value_objects.telegram_id import TelegramId
from src.infrastructure.services.admin_notification_service import (
    AdminNotificationService,
)
from src.infrastructure.utilities.exceptions import BusinessLogicError


@dataclass
class OrderDetails:
    """A data class to hold order details for creation."""

    customer: Any
    order_items: list[OrderItemInfo]
    delivery_method: str
    delivery_address: str | None
    subtotal: float
    delivery_charge: float
    total: float


class OrderCreationUseCase:
    """Use case for creating orders from cart items"""

    def __init__(
        self,
        cart_repository: CartRepository,
        customer_repository: CustomerRepository,
        order_repository: OrderRepository,
        admin_notification_service: AdminNotificationService | None = None,
    ):
        self._cart_repository = cart_repository
        self._customer_repository = customer_repository
        self._order_repository = order_repository
        self._admin_notification_service = admin_notification_service
        self._logger = logging.getLogger(self.__class__.__name__)

        # Log initialization details
        self._logger.info("🏗️ ORDER USE CASE INITIALIZED")
        self._logger.info(
            "  📁 Cart Repository: %s", type(self._cart_repository).__name__
        )
        self._logger.info(
            "  👤 Customer Repository: %s", type(self._customer_repository).__name__
        )
        self._logger.info(
            "  📋 Order Repository: %s", type(self._order_repository).__name__
        )
        if self._admin_notification_service:
            self._logger.info(
                "  📨 Admin Notification Service: %s",
                type(self._admin_notification_service).__name__,
            )
        else:
            self._logger.warning("  ⚠️ Admin Notification Service: NOT AVAILABLE")

    async def create_order(self, request: CreateOrderRequest) -> OrderCreationResponse:
        """Create order from user's cart"""
        self._logger.info("📝 ===== ORDER CREATION STARTED =====")
        self._logger.info("📝 ORDER CREATION: User %s", request.telegram_id)
        self._logger.info("📝 Request Details: %s", request)

        try:
            telegram_id = TelegramId(request.telegram_id)
            customer = await self._get_customer(telegram_id)
            cart_data = await self._get_cart_data(telegram_id)
            (
                order_items,
                subtotal,
                total,
                delivery_method,
                delivery_charge,
                delivery_address,
            ) = self._calculate_totals(request, cart_data)

            order_details = OrderDetails(
                customer=customer,
                order_items=order_items,
                delivery_method=delivery_method,
                delivery_address=delivery_address,
                subtotal=subtotal,
                delivery_charge=delivery_charge,
                total=total,
            )

            order = await self._create_order_in_database(order_details)

            await self._cart_repository.clear_cart(telegram_id)

            order_info = self._create_order_info(order, order_details)

            await self._send_admin_notification(order_info)

            self._logger.info("🎉 ===== ORDER CREATION COMPLETED =====")
            return OrderCreationResponse(success=True, order_info=order_info)

        except BusinessLogicError as e:
            self._logger.error("💥 VALIDATION ERROR: %s", e)
            return OrderCreationResponse(success=False, error_message=str(e))
        except (ValueError, TypeError, KeyError) as e:
            self._logger.error("💥 ORDER CREATION ERROR: %s", e, exc_info=True)
            return OrderCreationResponse(
                success=False,
                error_message=(
                    "An error occurred while creating your order. " "Please try again."
                ),
            )

    async def get_order_preview(
        self, request: CreateOrderRequest
    ) -> OrderCreationResponse:
        """Get a preview of the order without creating it"""
        try:
            telegram_id = TelegramId(request.telegram_id)
            customer = await self._get_customer(telegram_id)
            cart_data = await self._get_cart_data(telegram_id)
            (
                order_items,
                subtotal,
                total,
                delivery_method,
                delivery_charge,
                delivery_address,
            ) = self._calculate_totals(request, cart_data)

            order_info = OrderInfo(
                order_id=None,
                order_number=None,
                customer_name=customer.full_name.value,
                customer_phone=customer.phone_number.value,
                items=order_items,
                delivery_method=delivery_method,
                delivery_address=delivery_address,
                subtotal=subtotal,
                delivery_charge=delivery_charge,
                total=total,
                status="preview",
                created_at=datetime.utcnow(),
            )
            return OrderCreationResponse(success=True, order_info=order_info)

        except BusinessLogicError as e:
            return OrderCreationResponse(success=False, error_message=str(e))

    async def _get_customer(self, telegram_id: TelegramId):
        customer = await self._customer_repository.find_by_telegram_id(telegram_id)
        if not customer:
            raise BusinessLogicError(
                "Customer not found. Please complete registration first."
            )
        return customer

    async def _get_cart_data(self, telegram_id: TelegramId):
        cart_data = await self._cart_repository.get_cart_items(telegram_id)
        if not cart_data or not cart_data.get("items"):
            raise BusinessLogicError(
                "Your cart is empty. Add items before placing an order."
            )
        return cart_data

    def _calculate_totals(self, request: CreateOrderRequest, cart_data: dict):
        subtotal = 0.0
        order_items = []
        for item_data in cart_data["items"]:
            item_total = item_data["quantity"] * item_data["unit_price"]
            subtotal += item_total
            order_items.append(
                OrderItemInfo.from_dict(item_data, total_price=item_total)
            )

        delivery_method = (
            request.delivery_method or cart_data.get("delivery_method") or "pickup"
        )
        delivery_charge = 5.0 if delivery_method == "delivery" else 0.0
        delivery_address = request.delivery_address or cart_data.get("delivery_address")
        if delivery_method == "delivery" and not delivery_address:
            raise BusinessLogicError(
                "Delivery address is required for delivery orders."
            )

        total = subtotal + delivery_charge
        return (
            order_items,
            subtotal,
            total,
            delivery_method,
            delivery_charge,
            delivery_address,
        )

    async def _create_order_in_database(self, order_details: OrderDetails):
        order_data = {
            "customer_id": order_details.customer.id.value,
            "items": [item.dict() for item in order_details.order_items],
            "delivery_method": order_details.delivery_method,
            "delivery_address": order_details.delivery_address,
            "subtotal": order_details.subtotal,
            "delivery_charge": order_details.delivery_charge,
            "total": order_details.total,
        }
        order = await self._order_repository.create_order(order_data)
        if not order:
            raise BusinessLogicError("Failed to create order. Please try again.")
        return order

    def _create_order_info(self, order, order_details: OrderDetails):
        return OrderInfo(
            order_id=order["id"],
            order_number=order["order_number"],
            customer_name=order_details.customer.full_name.value,
            customer_phone=order_details.customer.phone_number.value,
            items=order_details.order_items,
            delivery_method=order_details.delivery_method,
            delivery_address=order_details.delivery_address,
            subtotal=order_details.subtotal,
            delivery_charge=order_details.delivery_charge,
            total=order_details.total,
            status=order.get("status", "pending"),
            created_at=order.get("created_at", datetime.utcnow()),
        )

    async def _send_admin_notification(self, order_info: OrderInfo):
        if self._admin_notification_service:
            try:
                await self._admin_notification_service.notify_new_order(order_info)
            except RuntimeError as e:
                self._logger.error("💥 ADMIN NOTIFICATION FAILED: %s", e, exc_info=True)
