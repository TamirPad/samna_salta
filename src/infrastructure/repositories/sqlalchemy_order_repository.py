"""
SQLAlchemy Order Repository

Concrete implementation of OrderRepository using SQLAlchemy ORM.
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from src.domain.repositories.order_repository import OrderRepository
from src.domain.value_objects.customer_id import CustomerId
from src.domain.value_objects.order_id import OrderId
from src.domain.value_objects.telegram_id import TelegramId
from src.infrastructure.database.models import Customer, Order, OrderItem
from src.infrastructure.database.operations import (  # compatibility for tests
    get_session,
)


@contextmanager
def managed_session():  # type: ignore
    session = get_session()
    try:
        yield session
    finally:
        session.close()


class SQLAlchemyOrderRepository(OrderRepository):
    """SQLAlchemy implementation of OrderRepository"""

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    async def create_order(self, order_data: dict[str, Any]) -> dict[str, Any] | None:
        """Create a new order"""
        self._logger.info("📝 CREATE ORDER: Customer %s", order_data.get("customer_id"))

        try:
            with managed_session() as session:
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
                    
                    # Set items field if it exists in the model but might be missing in database
                    if "items" in order_data and hasattr(order, "items"):
                        try:
                            order.items = order_data.get("items", [])
                        except Exception as e:
                            self._logger.warning("Could not set items field: %s", e)
                    
                    session.add(order)
                    session.flush()  # Get order ID

                    self._logger.info(
                        "🆕 ORDER CREATED: #%s, ID=%s", order_number, order.id
                    )

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
                        # Add product_id if available in the item data
                        if "product_id" in item_data and item_data["product_id"] is not None:
                            order_item.product_id = item_data["product_id"]
                        
                        session.add(order_item)

                    session.commit()
                    # Try to refresh but don't fail if columns are missing
                    try:
                        session.refresh(order)
                    except Exception as e:
                        self._logger.warning("Could not refresh order: %s", e)
                        # Continue without refresh

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

                    self._logger.info("✅ ORDER CREATION SUCCESS: #%s", order_number)
                    return result

                except SQLAlchemyError as e:
                    self._logger.error("💥 DATABASE ERROR creating order: %s", e)
                    raise
                except Exception as e:
                    self._logger.error("💥 UNEXPECTED ERROR creating order: %s", e)
                    raise

        except Exception as e:
            self._logger.error("💥 UNEXPECTED ERROR creating order: %s", e)
            raise

    async def get_order_by_id(self, order_id: OrderId) -> dict[str, Any] | None:
        """Get order by ID with optimized loading"""
        self._logger.info("🔍 GET ORDER BY ID: %s", order_id.value)

        try:
            with managed_session() as session:
                # Use joinedload to fetch order with customer and items in one query
                order = (
                    session.query(Order)
                    .options(joinedload(Order.customer))
                    .filter(Order.id == order_id.value)
                    .first()
                )

                if not order:
                    self._logger.info("📭 ORDER NOT FOUND: ID %s", order_id.value)
                    return None

                # Get order items in a separate optimized query
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

                self._logger.info("✅ ORDER FOUND: #%s", order.order_number)
                return result

        except SQLAlchemyError as e:
            self._logger.error("💥 DATABASE ERROR getting order by ID: %s", e)
            raise
        except Exception as e:
            self._logger.error("💥 UNEXPECTED ERROR getting order by ID: %s", e)
            raise

    async def get_orders_by_customer(
        self, customer_id: CustomerId
    ) -> list[dict[str, Any]]:
        """Get orders by customer ID with optimized loading"""
        self._logger.info("📋 GET ORDERS BY CUSTOMER: %s", customer_id.value)

        try:
            with managed_session() as session:
                # Fetch orders with customer data in one query
                orders = (
                    session.query(Order)
                    .options(joinedload(Order.customer))
                    .filter(Order.customer_id == customer_id.value)
                    .order_by(Order.created_at.desc())
                    .all()
                )

                if not orders:
                    self._logger.info("📭 NO ORDERS FOUND for customer %s", customer_id.value)
                    return []

                # Get all order IDs for batch loading items
                order_ids = [order.id for order in orders]
                
                # Batch load all order items
                all_items = (
                    session.query(OrderItem)
                    .filter(OrderItem.order_id.in_(order_ids))
                    .all()
                )
                
                # Group items by order_id for efficient lookup
                items_by_order = {}
                for item in all_items:
                    if item.order_id not in items_by_order:
                        items_by_order[item.order_id] = []
                    items_by_order[item.order_id].append(item)

                result = []
                for order in orders:
                    items = items_by_order.get(order.id, [])

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
                    "✅ FOUND %d ORDERS for customer %s", len(result), customer_id.value
                )
                return result

        except SQLAlchemyError as e:
            self._logger.error("💥 DATABASE ERROR getting orders by customer: %s", e)
            raise
        except Exception as e:
            self._logger.error("💥 UNEXPECTED ERROR getting orders by customer: %s", e)
            raise

    async def get_orders_by_telegram_id(
        self, telegram_id: TelegramId
    ) -> list[dict[str, Any]]:
        """Get orders by telegram ID"""
        self._logger.info("📋 GET ORDERS BY TELEGRAM ID: %s", telegram_id.value)

        try:
            with managed_session() as session:
                # Get customer first
                customer = (
                    session.query(Customer)
                    .filter(Customer.telegram_id == telegram_id.value)
                    .first()
                )

                if not customer:
                    self._logger.info(
                        "📭 CUSTOMER NOT FOUND: Telegram ID %s", telegram_id.value
                    )
                    return []

                # Get orders for this customer
                customer_id = CustomerId(customer.id)
                return await self.get_orders_by_customer(customer_id)

        except SQLAlchemyError as e:
            self._logger.error("💥 DATABASE ERROR getting orders by telegram ID: %s", e)
            raise
        except Exception as e:
            self._logger.error(
                "💥 UNEXPECTED ERROR getting orders by telegram ID: %s", e
            )
            raise

    async def update_order_status(self, order_id: OrderId, status: str) -> bool:
        """Update order status"""
        self._logger.info("🔄 UPDATE ORDER STATUS: ID %s -> %s", order_id.value, status)

        try:
            with managed_session() as session:
                order = session.query(Order).filter(Order.id == order_id.value).first()

                if not order:
                    self._logger.warning("📭 ORDER NOT FOUND: ID %s", order_id.value)
                    return False

                order.status = status
                order.updated_at = datetime.utcnow()
                session.commit()

                self._logger.info(
                    "✅ ORDER STATUS UPDATED: #%s -> %s", order.order_number, status
                )
                return True

        except SQLAlchemyError as e:
            self._logger.error("💥 DATABASE ERROR updating order status: %s", e)
            raise
        except Exception as e:
            self._logger.error("💥 UNEXPECTED ERROR updating order status: %s", e)
            raise

    async def get_all_orders(
        self, limit: int = 100, status: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get all orders with optional status filter - OPTIMIZED VERSION
        
        This method fixes the N+1 query problem by:
        1. Using a single query with joins to get orders and customers
        2. Batch loading all order items in one query
        3. Grouping items by order for efficient lookup
        """
        if status:
            self._logger.info("📋 GET ALL ORDERS (limit=%d, status=%s)", limit, status)
        else:
            self._logger.info("📋 GET ALL ORDERS (limit=%d)", limit)

        try:
            with managed_session() as session:
                # OPTIMIZATION 1: Single query with join to get orders and customers
                query = (
                    session.query(Order, Customer)
                    .join(Customer, Order.customer_id == Customer.id)
                    .order_by(Order.created_at.desc())
                )

                if status:
                    query = query.filter(Order.status == status)

                order_customer_pairs = query.limit(limit).all()
                
                if not order_customer_pairs:
                    self._logger.info("📭 NO ORDERS FOUND")
                    return []

                # Extract orders and create customer lookup
                orders = [pair[0] for pair in order_customer_pairs]
                customers_by_id = {pair[1].id: pair[1] for pair in order_customer_pairs}
                order_ids = [order.id for order in orders]

                # OPTIMIZATION 2: Batch load all order items in one query
                all_items = (
                    session.query(OrderItem)
                    .filter(OrderItem.order_id.in_(order_ids))
                    .all()
                )

                # OPTIMIZATION 3: Group items by order_id for O(1) lookup
                items_by_order = {}
                for item in all_items:
                    if item.order_id not in items_by_order:
                        items_by_order[item.order_id] = []
                    items_by_order[item.order_id].append(item)

                # Build result with no additional queries
                result = []
                for order in orders:
                    customer = customers_by_id[order.customer_id]
                    items = items_by_order.get(order.id, [])

                    order_data = {
                        "id": order.id,
                        "order_number": order.order_number,
                        "customer_id": order.customer_id,
                        "customer_name": customer.full_name,
                        "customer_phone": customer.phone_number,
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

                self._logger.info("✅ FOUND %d ORDERS", len(result))
                return result

        except SQLAlchemyError as e:
            self._logger.error("💥 DATABASE ERROR getting all orders: %s", e)
            raise
        except Exception as e:
            self._logger.error("💥 UNEXPECTED ERROR getting all orders: %s", e)
            raise

    async def delete_order(self, order_id: OrderId) -> bool:
        """Delete an order and its items"""
        self._logger.info("🗑️ DELETE ORDER: ID %s", order_id.value)

        try:
            with managed_session() as session:
                # First, delete order items
                session.query(OrderItem).filter(
                    OrderItem.order_id == order_id.value
                ).delete(synchronize_session=False)

                # Then, delete the order
                order = session.query(Order).filter(Order.id == order_id.value).first()
                if order:
                    session.delete(order)
                    session.commit()
                    self._logger.info("✅ ORDER DELETED: ID %s", order_id.value)
                    return True
                self._logger.warning(
                    "📭 ORDER NOT FOUND for deletion: %s", order_id.value
                )
                return False

        except SQLAlchemyError as e:
            self._logger.error("💥 DATABASE ERROR deleting order: %s", e)
            raise
        except Exception as e:
            self._logger.error("💥 UNEXPECTED ERROR deleting order: %s", e)
            raise

    def _generate_order_number(self) -> str:
        """Generate a unique order number"""
        return f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
