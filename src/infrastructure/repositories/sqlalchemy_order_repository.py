"""
SQLAlchemy Order Repository

Concrete implementation of OrderRepository using SQLAlchemy ORM.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from ...domain.repositories.order_repository import OrderRepository
from ...domain.value_objects.customer_id import CustomerId
from ...domain.value_objects.order_id import OrderId
from ...domain.value_objects.telegram_id import TelegramId
from ..database.models import Customer, Order, OrderItem
from ..database.operations import get_session


class SQLAlchemyOrderRepository(OrderRepository):
    """SQLAlchemy implementation of OrderRepository"""

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    async def create_order(
        self, order_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a new order"""
        self._logger.info(f"📝 CREATE ORDER: Customer {order_data.get('customer_id')}")

        try:
            session = get_session()
            try:
                # Generate order number
                order_number = self._generate_order_number()

                # Create order
                order = Order(
                    customer_id=order_data["customer_id"],
                    order_number=order_number,
                    delivery_method=order_data.get("delivery_method", "pickup"),
                    delivery_address=order_data.get("delivery_address"),
                    delivery_charge=order_data.get("delivery_charge", 0.0),
                    subtotal=order_data["subtotal"],
                    total=order_data["total"],
                    status="pending",
                )
                session.add(order)
                session.flush()  # Get order ID

                self._logger.info(f"🆕 ORDER CREATED: #{order_number}, ID={order.id}")

                # Create order items
                for item_data in order_data.get("items", []):
                    order_item = OrderItem(
                        order_id=order.id,
                        product_name=item_data["product_name"],
                        product_options=item_data.get("options", {}),
                        quantity=item_data["quantity"],
                        unit_price=item_data["unit_price"],
                        total_price=item_data["total_price"],
                    )
                    session.add(order_item)

                session.commit()
                session.refresh(order)

                # Return order data
                result = {
                    "id": order.id,
                    "order_number": order.order_number,
                    "customer_id": order.customer_id,
                    "delivery_method": order.delivery_method,
                    "delivery_address": order.delivery_address,
                    "delivery_charge": order.delivery_charge,
                    "subtotal": order.subtotal,
                    "total": order.total,
                    "status": order.status,
                    "created_at": order.created_at,
                    "updated_at": order.updated_at,
                }

                self._logger.info(f"✅ ORDER CREATION SUCCESS: #{order_number}")
                return result

            finally:
                session.close()

        except SQLAlchemyError as e:
            self._logger.error(f"💥 DATABASE ERROR creating order: {e}")
            raise
        except Exception as e:
            self._logger.error(f"💥 UNEXPECTED ERROR creating order: {e}")
            raise

    async def get_order_by_id(self, order_id: OrderId) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        self._logger.info(f"🔍 GET ORDER BY ID: {order_id.value}")

        try:
            session = get_session()
            try:
                order = session.query(Order).filter(Order.id == order_id.value).first()

                if not order:
                    self._logger.info(f"📭 ORDER NOT FOUND: ID {order_id.value}")
                    return None

                # Get order items
                items = (
                    session.query(OrderItem)
                    .filter(OrderItem.order_id == order.id)
                    .all()
                )

                result = {
                    "id": order.id,
                    "order_number": order.order_number,
                    "customer_id": order.customer_id,
                    "delivery_method": order.delivery_method,
                    "delivery_address": order.delivery_address,
                    "delivery_charge": order.delivery_charge,
                    "subtotal": order.subtotal,
                    "total": order.total,
                    "status": order.status,
                    "created_at": order.created_at,
                    "updated_at": order.updated_at,
                    "items": [
                        {
                            "product_name": item.product_name,
                            "quantity": item.quantity,
                            "unit_price": item.unit_price,
                            "total_price": item.total_price,
                            "options": item.product_options or {},
                        }
                        for item in items
                    ],
                }

                self._logger.info(f"✅ ORDER FOUND: #{order.order_number}")
                return result

            finally:
                session.close()

        except SQLAlchemyError as e:
            self._logger.error(f"💥 DATABASE ERROR getting order by ID: {e}")
            raise
        except Exception as e:
            self._logger.error(f"💥 UNEXPECTED ERROR getting order by ID: {e}")
            raise

    async def get_orders_by_customer(
        self, customer_id: CustomerId
    ) -> List[Dict[str, Any]]:
        """Get orders by customer ID"""
        self._logger.info(f"📋 GET ORDERS BY CUSTOMER: {customer_id.value}")

        try:
            session = get_session()
            try:
                orders = (
                    session.query(Order)
                    .filter(Order.customer_id == customer_id.value)
                    .order_by(Order.created_at.desc())
                    .all()
                )

                result = []
                for order in orders:
                    items = (
                        session.query(OrderItem)
                        .filter(OrderItem.order_id == order.id)
                        .all()
                    )

                    order_data = {
                        "id": order.id,
                        "order_number": order.order_number,
                        "customer_id": order.customer_id,
                        "delivery_method": order.delivery_method,
                        "delivery_address": order.delivery_address,
                        "delivery_charge": order.delivery_charge,
                        "subtotal": order.subtotal,
                        "total": order.total,
                        "status": order.status,
                        "created_at": order.created_at,
                        "updated_at": order.updated_at,
                        "items": [
                            {
                                "product_name": item.product_name,
                                "quantity": item.quantity,
                                "unit_price": item.unit_price,
                                "total_price": item.total_price,
                                "options": item.product_options or {},
                            }
                            for item in items
                        ],
                    }
                    result.append(order_data)

                self._logger.info(
                    f"✅ FOUND {len(result)} ORDERS for customer {customer_id.value}"
                )
                return result

            finally:
                session.close()

        except SQLAlchemyError as e:
            self._logger.error(f"💥 DATABASE ERROR getting orders by customer: {e}")
            raise
        except Exception as e:
            self._logger.error(f"💥 UNEXPECTED ERROR getting orders by customer: {e}")
            raise

    async def get_orders_by_telegram_id(
        self, telegram_id: TelegramId
    ) -> List[Dict[str, Any]]:
        """Get orders by telegram ID"""
        self._logger.info(f"📋 GET ORDERS BY TELEGRAM ID: {telegram_id.value}")

        try:
            session = get_session()
            try:
                # Get customer first
                customer = (
                    session.query(Customer)
                    .filter(Customer.telegram_id == telegram_id.value)
                    .first()
                )

                if not customer:
                    self._logger.info(
                        f"📭 CUSTOMER NOT FOUND: Telegram ID {telegram_id.value}"
                    )
                    return []

                # Get orders for this customer
                customer_id = CustomerId(customer.id)
                return await self.get_orders_by_customer(customer_id)

            finally:
                session.close()

        except SQLAlchemyError as e:
            self._logger.error(f"💥 DATABASE ERROR getting orders by telegram ID: {e}")
            raise
        except Exception as e:
            self._logger.error(f"💥 UNEXPECTED ERROR getting orders by telegram ID: {e}")
            raise

    async def update_order_status(self, order_id: OrderId, status: str) -> bool:
        """Update order status"""
        self._logger.info(f"🔄 UPDATE ORDER STATUS: ID {order_id.value} -> {status}")

        try:
            session = get_session()
            try:
                order = session.query(Order).filter(Order.id == order_id.value).first()

                if not order:
                    self._logger.warning(f"⚠️ ORDER NOT FOUND: ID {order_id.value}")
                    return False

                old_status = order.status
                order.status = status
                order.updated_at = datetime.utcnow()

                session.commit()

                self._logger.info(
                    f"✅ STATUS UPDATED: Order #{order.order_number} {old_status} -> {status}"
                )
                return True

            finally:
                session.close()

        except SQLAlchemyError as e:
            self._logger.error(f"💥 DATABASE ERROR updating order status: {e}")
            raise
        except Exception as e:
            self._logger.error(f"💥 UNEXPECTED ERROR updating order status: {e}")
            raise

    async def get_all_orders(
        self, limit: int = 100, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all orders with optional filtering"""
        self._logger.info(f"📋 GET ALL ORDERS: limit={limit}, status={status}")

        try:
            session = get_session()
            try:
                query = session.query(Order)

                if status:
                    query = query.filter(Order.status == status)

                orders = query.order_by(Order.created_at.desc()).limit(limit).all()

                result = []
                for order in orders:
                    items = (
                        session.query(OrderItem)
                        .filter(OrderItem.order_id == order.id)
                        .all()
                    )

                    order_data = {
                        "id": order.id,
                        "order_number": order.order_number,
                        "customer_id": order.customer_id,
                        "delivery_method": order.delivery_method,
                        "delivery_address": order.delivery_address,
                        "delivery_charge": order.delivery_charge,
                        "subtotal": order.subtotal,
                        "total": order.total,
                        "status": order.status,
                        "created_at": order.created_at,
                        "updated_at": order.updated_at,
                        "items": [
                            {
                                "product_name": item.product_name,
                                "quantity": item.quantity,
                                "unit_price": item.unit_price,
                                "total_price": item.total_price,
                                "options": item.product_options or {},
                            }
                            for item in items
                        ],
                    }
                    result.append(order_data)

                self._logger.info(f"✅ FOUND {len(result)} ORDERS")
                return result

            finally:
                session.close()

        except SQLAlchemyError as e:
            self._logger.error(f"💥 DATABASE ERROR getting all orders: {e}")
            raise
        except Exception as e:
            self._logger.error(f"💥 UNEXPECTED ERROR getting all orders: {e}")
            raise

    async def delete_order(self, order_id: OrderId) -> bool:
        """Delete an order"""
        self._logger.info(f"🗑️ DELETE ORDER: ID {order_id.value}")

        try:
            session = get_session()
            try:
                order = session.query(Order).filter(Order.id == order_id.value).first()

                if not order:
                    self._logger.warning(f"⚠️ ORDER NOT FOUND: ID {order_id.value}")
                    return False

                # Delete order items first
                session.query(OrderItem).filter(
                    OrderItem.order_id == order_id.value
                ).delete()

                # Delete order
                session.delete(order)
                session.commit()

                self._logger.info(f"✅ ORDER DELETED: #{order.order_number}")
                return True

            finally:
                session.close()

        except SQLAlchemyError as e:
            self._logger.error(f"💥 DATABASE ERROR deleting order: {e}")
            raise
        except Exception as e:
            self._logger.error(f"💥 UNEXPECTED ERROR deleting order: {e}")
            raise

    def _generate_order_number(self) -> str:
        """Generate unique order number"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"SS{timestamp}"
