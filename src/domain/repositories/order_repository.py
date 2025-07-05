"""
Order repository interface

Defines the contract for order data access operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..value_objects.customer_id import CustomerId
from ..value_objects.order_id import OrderId
from ..value_objects.telegram_id import TelegramId


class OrderRepository(ABC):
    """Repository interface for order operations"""

    @abstractmethod
    async def create_order(
        self, order_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a new order"""
        pass

    @abstractmethod
    async def get_order_by_id(self, order_id: OrderId) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        pass

    @abstractmethod
    async def get_orders_by_customer(
        self, customer_id: CustomerId
    ) -> List[Dict[str, Any]]:
        """Get orders by customer ID"""
        pass

    @abstractmethod
    async def get_orders_by_telegram_id(
        self, telegram_id: TelegramId
    ) -> List[Dict[str, Any]]:
        """Get orders by telegram ID"""
        pass

    @abstractmethod
    async def update_order_status(self, order_id: OrderId, status: str) -> bool:
        """Update order status"""
        pass

    @abstractmethod
    async def get_all_orders(
        self, limit: int = 100, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all orders with optional filtering"""
        pass

    @abstractmethod
    async def delete_order(self, order_id: OrderId) -> bool:
        """Delete an order"""
        pass
