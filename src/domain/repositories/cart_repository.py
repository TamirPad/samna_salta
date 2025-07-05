"""
Cart repository interface

Defines the contract for cart data access operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.domain.value_objects.product_id import ProductId
from src.domain.value_objects.telegram_id import TelegramId


class CartRepository(ABC):
    """Repository interface for cart operations"""

    @abstractmethod
    async def get_cart_items(self, telegram_id: TelegramId) -> Optional[Dict[str, Any]]:
        """Get cart items for a user"""

    @abstractmethod
    async def add_item(
        self,
        telegram_id: TelegramId,
        product_id: ProductId,
        quantity: int,
        options: Dict[str, Any],
    ) -> bool:
        """Add item to cart"""

    @abstractmethod
    async def update_cart(
        self,
        telegram_id: TelegramId,
        items: List[Dict[str, Any]],
        delivery_method: Optional[str] = None,
        delivery_address: Optional[str] = None,
    ) -> bool:
        """Update entire cart"""

    @abstractmethod
    async def clear_cart(self, telegram_id: TelegramId) -> bool:
        """Clear cart for user"""

    @abstractmethod
    async def get_or_create_cart(
        self, telegram_id: TelegramId
    ) -> Optional[Dict[str, Any]]:
        """Get or create cart for user"""
