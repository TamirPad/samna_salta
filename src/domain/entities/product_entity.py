# pylint: disable=too-many-instance-attributes
"""
Product Entity - Core business logic for products
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.domain.value_objects.price import Price
from src.domain.value_objects.product_id import ProductId
from src.domain.value_objects.product_name import ProductName


@dataclass
class ProductData:
    """Data class for creating a product."""

    name: str
    description: str
    price: Decimal
    category: str
    image_url: str | None = None


@dataclass
class Product:
    """Product domain entity"""

    id: ProductId | None
    name: ProductName
    description: str
    price: Price
    category: str
    is_active: bool = True
    image_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self):
        """Validate the product after initialization"""
        if not self.name or not self.name.value:
            raise ValueError("Product name cannot be empty")

        if not self.category:
            raise ValueError("Product category cannot be empty")

        if self.price.amount <= 0:
            raise ValueError("Product price must be positive")

    def activate(self):
        """Activate the product"""
        self.is_active = True
        self.updated_at = datetime.now()

    def deactivate(self):
        """Deactivate the product"""
        self.is_active = False
        self.updated_at = datetime.now()

    def update_price(self, new_price: Price):
        """Update product price"""
        if new_price.amount <= 0:
            raise ValueError("Price must be positive")
        self.price = new_price
        self.updated_at = datetime.now()

    def update_description(self, new_description: str):
        """Update product description"""
        if not new_description:
            raise ValueError("Description cannot be empty")
        self.description = new_description
        self.updated_at = datetime.now()

    @classmethod
    def create(cls, data: ProductData) -> "Product":
        """Create a new product"""
        return cls(
            id=None,
            name=ProductName(data.name),
            description=data.description,
            price=Price(data.price),
            category=data.category,
            image_url=data.image_url,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation"""
        return {
            "id": self.id.value if self.id else None,
            "name": self.name.value,
            "description": self.description,
            "price": float(self.price.amount),
            "category": self.category,
            "is_active": self.is_active,
            "image_url": self.image_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
