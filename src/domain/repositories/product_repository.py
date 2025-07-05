"""
Product repository interface

Defines the contract for product data access operations.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

from ..value_objects.product_id import ProductId
from ..value_objects.product_name import ProductName

if TYPE_CHECKING:
    from ...infrastructure.database.models import Product


class ProductRepository(ABC):
    """Repository interface for product operations"""

    @abstractmethod
    async def find_by_id(self, product_id: ProductId) -> Optional["Product"]:
        """Find product by ID"""
        pass

    @abstractmethod
    async def find_by_name(self, name: ProductName) -> Optional["Product"]:
        """Find product by name"""
        pass

    @abstractmethod
    async def find_by_category(self, category: str) -> List["Product"]:
        """Find products by category"""
        pass

    @abstractmethod
    async def find_all_active(self) -> List["Product"]:
        """Find all active products"""
        pass

    @abstractmethod
    async def save(self, product: "Product") -> "Product":
        """Save product"""
        pass

    @abstractmethod
    async def delete(self, product_id: ProductId) -> bool:
        """Delete product"""
        pass
