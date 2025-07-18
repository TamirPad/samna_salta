"""
Data Transfer Objects (DTOs)

All data-transfer objects for the application, including:
- Cart operations
- Order operations
- Customer registration
- Product catalog
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Customer Registration DTOs
# ---------------------------------------------------------------------------


@dataclass
class CustomerRegistrationRequest:
    telegram_id: int
    full_name: str
    phone_number: str
    delivery_address: Optional[str] = None


@dataclass
class CustomerRegistrationResponse:
    success: bool
    customer: Optional[Dict[str, Any]] = None
    is_returning_customer: bool = False
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Product Catalog DTOs
# ---------------------------------------------------------------------------


@dataclass
class ProductCatalogRequest:
    category: Optional[str] = None


@dataclass
class ProductCatalogResponse:
    success: bool
    products: List[Dict[str, Any]]
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Cart DTOs
# ---------------------------------------------------------------------------


@dataclass
class AddToCartRequest:
    telegram_id: int
    product_id: int
    quantity: int = 1
    options: Optional[Dict[str, Any]] = None


@dataclass
class UpdateCartRequest:
    telegram_id: int
    items: List[Dict[str, Any]]
    delivery_method: Optional[str] = None
    delivery_address: Optional[str] = None


@dataclass
class CartItemInfo:
    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    total_price: float
    options: Optional[Dict[str, Any]] = None


@dataclass
class GetCartResponse:
    success: bool
    cart_items: List[CartItemInfo] | None = None
    delivery_method: Optional[str] = None
    delivery_address: Optional[str] = None
    cart_total: float = 0.0
    error_message: Optional[str] = None


@dataclass
class CartSummary:
    items: List[CartItemInfo]
    subtotal: float
    delivery_charge: float
    total: float
    delivery_method: Optional[str] = None
    delivery_address: Optional[str] = None


@dataclass
class CartOperationResponse:
    success: bool
    cart_summary: Optional[CartSummary] = None
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Order DTOs
# ---------------------------------------------------------------------------


@dataclass
class CreateOrderRequest:
    telegram_id: int
    delivery_method: Optional[str] = None  # 'pickup' | 'delivery'
    delivery_address: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class OrderItemInfo:
    product_name: str
    quantity: int
    unit_price: float
    total_price: float
    product_id: int | None = None
    options: Dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], total_price: float) -> "OrderItemInfo":
        return cls(
            product_name=data["product_name"],
            quantity=data["quantity"],
            unit_price=data["unit_price"],
            total_price=total_price,
            product_id=data.get("product_id"),
            options=data.get("options", {}),
        )

    def dict(self) -> Dict[str, Any]:  # pragma: no cover
        return {
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "product_id": self.product_id,
            "options": self.options,
        }


@dataclass
class OrderInfo:
    order_id: int
    order_number: str
    customer_name: str
    customer_phone: str
    items: List[OrderItemInfo]
    delivery_method: str
    delivery_address: Optional[str]
    subtotal: float
    delivery_charge: float
    total: float
    status: str
    created_at: datetime
    notes: Optional[str] = None


@dataclass
class OrderCreationResponse:
    success: bool
    order_info: Optional[OrderInfo] = None
    error_message: Optional[str] = None


@dataclass
class OrderSummaryRequest:
    telegram_id: int


@dataclass
class OrderListRequest:
    customer_id: Optional[int] = None
    telegram_id: Optional[int] = None
    status: Optional[str] = None
    limit: int = 10


@dataclass
class OrderListResponse:
    success: bool
    orders: List[OrderInfo]
    total_count: int
    error_message: Optional[str] = None 