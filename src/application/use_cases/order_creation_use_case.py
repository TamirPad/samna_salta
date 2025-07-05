"""
Order Creation Use Case

Handles the business logic for creating orders from cart items.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ...domain.repositories.cart_repository import CartRepository
from ...domain.repositories.customer_repository import CustomerRepository
from ...domain.repositories.order_repository import OrderRepository
from ...domain.value_objects.customer_id import CustomerId
from ...domain.value_objects.money import Money
from ...domain.value_objects.telegram_id import TelegramId
from ...infrastructure.services.admin_notification_service import (
    AdminNotificationService,
)
from ...infrastructure.utilities.exceptions import (
    BusinessLogicError,
    OrderCreationError,
)
from ..dtos.order_dtos import (
    CreateOrderRequest,
    OrderCreationResponse,
    OrderInfo,
    OrderItemInfo,
)


class OrderCreationUseCase:
    """Use case for creating orders from cart items"""

    def __init__(
        self,
        cart_repository: CartRepository,
        customer_repository: CustomerRepository,
        order_repository: OrderRepository,
        admin_notification_service: Optional[AdminNotificationService] = None,
    ):
        self._cart_repository = cart_repository
        self._customer_repository = customer_repository
        self._order_repository = order_repository
        self._admin_notification_service = admin_notification_service
        self._logger = logging.getLogger(self.__class__.__name__)

        # Log initialization details
        self._logger.info("🏗️ ORDER USE CASE INITIALIZED")
        self._logger.info(
            f"  📁 Cart Repository: {type(self._cart_repository).__name__}"
        )
        self._logger.info(
            f"  👤 Customer Repository: {type(self._customer_repository).__name__}"
        )
        self._logger.info(
            f"  📋 Order Repository: {type(self._order_repository).__name__}"
        )
        if self._admin_notification_service:
            self._logger.info(
                f"  📨 Admin Notification Service: {type(self._admin_notification_service).__name__}"
            )
        else:
            self._logger.warning("  ⚠️ Admin Notification Service: NOT AVAILABLE")

    async def create_order(self, request: CreateOrderRequest) -> OrderCreationResponse:
        """Create order from user's cart"""
        self._logger.info("📝 ===== ORDER CREATION STARTED =====")
        self._logger.info(f"📝 ORDER CREATION: User {request.telegram_id}")
        self._logger.info(f"📝 Request Details: {request}")

        try:
            telegram_id = TelegramId(request.telegram_id)
            self._logger.info(f"📱 TELEGRAM ID CREATED: {telegram_id.value}")

            # Get customer
            self._logger.info("👤 STEP A: Finding customer by telegram ID...")
            customer = await self._customer_repository.find_by_telegram_id(telegram_id)
            if not customer:
                self._logger.error(f"❌ CUSTOMER NOT FOUND: User {request.telegram_id}")
                return OrderCreationResponse(
                    success=False,
                    error_message="Customer not found. Please complete registration first.",
                )

            self._logger.info(
                f"✅ CUSTOMER FOUND: ID={customer.id.value}, Name={customer.full_name.value}, Admin={customer.is_admin}"
            )

            # Get cart items
            self._logger.info("🛒 STEP B: Getting cart items...")
            cart_data = await self._cart_repository.get_cart_items(telegram_id)
            if not cart_data or not cart_data.get("items"):
                self._logger.error(f"❌ EMPTY CART: User {request.telegram_id}")
                return OrderCreationResponse(
                    success=False,
                    error_message="Your cart is empty. Add items before placing an order.",
                )

            self._logger.info(f"✅ CART RETRIEVED: {len(cart_data['items'])} items")
            for i, item in enumerate(cart_data["items"]):
                self._logger.info(
                    f"  📦 Item {i+1}: {item['quantity']}x {item['product_name']} - ₪{item['unit_price']:.2f}"
                )

            # Calculate totals
            self._logger.info("💰 STEP C: Calculating totals...")
            subtotal = 0.0
            order_items = []

            for item_data in cart_data["items"]:
                item_total = item_data["quantity"] * item_data["unit_price"]
                subtotal += item_total

                order_item = OrderItemInfo(
                    product_name=item_data["product_name"],
                    quantity=item_data["quantity"],
                    unit_price=item_data["unit_price"],
                    total_price=item_total,
                    options=item_data.get("options", {}),
                )
                order_items.append(order_item)

            # Calculate delivery charge
            delivery_method = (
                request.delivery_method or cart_data.get("delivery_method") or "pickup"
            )
            delivery_charge = 5.0 if delivery_method == "delivery" else 0.0
            delivery_address = request.delivery_address or cart_data.get(
                "delivery_address"
            )

            # Validate delivery address if needed
            if delivery_method == "delivery" and not delivery_address:
                self._logger.error(
                    f"❌ MISSING DELIVERY ADDRESS: User {request.telegram_id}"
                )
                return OrderCreationResponse(
                    success=False,
                    error_message="Delivery address is required for delivery orders.",
                )

            total = subtotal + delivery_charge

            self._logger.info("💰 ORDER TOTALS CALCULATED:")
            self._logger.info(f"  💵 Subtotal: ₪{subtotal:.2f}")
            self._logger.info(f"  🚚 Delivery: ₪{delivery_charge:.2f}")
            self._logger.info(f"  💳 Total: ₪{total:.2f}")
            self._logger.info(f"  📦 Method: {delivery_method}")
            if delivery_address:
                self._logger.info(f"  📍 Address: {delivery_address}")

            # Create order
            self._logger.info("📋 STEP D: Creating order in database...")
            order_data = {
                "customer_id": customer.id.value,
                "items": [
                    {
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "total_price": item.total_price,
                        "options": item.options,
                    }
                    for item in order_items
                ],
                "delivery_method": delivery_method,
                "delivery_address": delivery_address,
                "subtotal": subtotal,
                "delivery_charge": delivery_charge,
                "total": total,
            }

            self._logger.info(
                f"📋 ORDER DATA PREPARED: {len(order_data['items'])} items for customer {customer.id.value}"
            )

            order = await self._order_repository.create_order(order_data)
            if not order:
                self._logger.error("💥 ORDER CREATION FAILED: Repository returned None")
                return OrderCreationResponse(
                    success=False,
                    error_message="Failed to create order. Please try again.",
                )

            self._logger.info("✅ ORDER CREATED IN DATABASE:")
            self._logger.info(f"  🆔 Order ID: {order['id']}")
            self._logger.info(f"  🔢 Order Number: {order['order_number']}")
            self._logger.info(f"  ⏳ Status: {order.get('status', 'pending')}")

            # Clear cart after successful order creation
            self._logger.info("🧹 STEP E: Clearing cart...")
            await self._cart_repository.clear_cart(telegram_id)
            self._logger.info("✅ CART CLEARED")

            # Create order info response
            self._logger.info("📄 STEP F: Creating order info response...")
            order_info = OrderInfo(
                order_id=order["id"],
                order_number=order["order_number"],
                customer_name=customer.full_name.value,
                customer_phone=customer.phone_number.value,
                items=order_items,
                delivery_method=delivery_method,
                delivery_address=delivery_address,
                subtotal=subtotal,
                delivery_charge=delivery_charge,
                total=total,
                status=order.get("status", "pending"),
                created_at=order.get("created_at", datetime.utcnow()),
            )

            self._logger.info(
                f"✅ ORDER INFO CREATED: Order #{order['order_number']}, Total=₪{total:.2f}"
            )

            # Send admin notification if service is available
            self._logger.info("📨 STEP G: Handling admin notifications...")
            if self._admin_notification_service:
                self._logger.info(
                    "📨 ADMIN SERVICE AVAILABLE: Attempting to send notification..."
                )
                try:
                    await self._admin_notification_service.notify_new_order(order_info)
                    self._logger.info(
                        f"✅ ADMIN NOTIFICATION SENT: Order #{order['order_number']}"
                    )
                except Exception as e:
                    self._logger.error(
                        f"💥 ADMIN NOTIFICATION FAILED: {e}", exc_info=True
                    )
                    # Don't fail the order if notification fails
            else:
                self._logger.warning(
                    "⚠️ ADMIN NOTIFICATION SKIPPED: Service not available"
                )

            self._logger.info("🎉 ===== ORDER CREATION COMPLETED =====")
            self._logger.info(
                f"🎉 Order #{order['order_number']} successfully created for {customer.full_name.value}"
            )

            return OrderCreationResponse(success=True, order_info=order_info)

        except BusinessLogicError as e:
            self._logger.error(f"💥 VALIDATION ERROR: {e}")
            return OrderCreationResponse(success=False, error_message=str(e))
        except Exception as e:
            self._logger.error(f"💥 ORDER CREATION ERROR: {e}", exc_info=True)
            return OrderCreationResponse(
                success=False,
                error_message="An error occurred while creating your order. Please try again.",
            )
