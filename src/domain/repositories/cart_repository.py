"""
Cart repository interface

Defines the contract for cart data access operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from ..value_objects.telegram_id import TelegramId
from ..value_objects.product_id import ProductId


class CartRepository(ABC):
    """Repository interface for cart operations"""
    
    @abstractmethod
    async def get_cart_items(self, telegram_id: TelegramId) -> Optional[Dict[str, Any]]:
        """Get cart items for a user"""
        pass
    
    @abstractmethod
    async def add_item(self, telegram_id: TelegramId, product_id: ProductId, 
                      quantity: int, options: Dict[str, Any]) -> bool:
        """Add item to cart"""
        pass
    
    @abstractmethod
    async def update_cart(self, telegram_id: TelegramId, items: List[Dict[str, Any]], 
                         delivery_method: Optional[str] = None, 
                         delivery_address: Optional[str] = None) -> bool:
        """Update entire cart"""
        pass
    
    @abstractmethod
    async def clear_cart(self, telegram_id: TelegramId) -> bool:
        """Clear cart for user"""
        pass
    
    @abstractmethod
    async def get_or_create_cart(self, telegram_id: TelegramId) -> Optional[Dict[str, Any]]:
        """Get or create cart for user"""
        pass 