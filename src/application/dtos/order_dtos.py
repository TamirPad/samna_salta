"""
Order DTOs

Data Transfer Objects for order-related operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class CreateOrderRequest:
    """Request to create an order"""

    telegram_id: int
    delivery_method: Optional[str] = None  # 'pickup' or 'delivery'
    delivery_address: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class OrderItemInfo:
    """Order item information"""

    product_name: str
    quantity: int
    unit_price: float
    total_price: float
    product_id: int | None = None
    options: Dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], total_price: float) -> "OrderItemInfo":
        """Create OrderItemInfo from a dictionary."""
        return cls(
            product_name=data["product_name"],
            quantity=data["quantity"],
            unit_price=data["unit_price"],
            total_price=total_price,
            product_id=data.get("product_id"),
            options=data.get("options", {}),
        )

    # Compatibility helper so tests can call item.dict()
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
    """Complete order information"""

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
    """Response from order creation"""

    success: bool
    order_info: Optional[OrderInfo] = None
    error_message: Optional[str] = None


@dataclass
class OrderSummaryRequest:
    """Request to get order summary"""

    telegram_id: int


@dataclass
class OrderListRequest:
    """Request to list orders"""

    customer_id: Optional[int] = None
    telegram_id: Optional[int] = None
    status: Optional[str] = None
    limit: int = 10


@dataclass
class OrderListResponse:
    """Response with list of orders"""

    success: bool
    orders: List[OrderInfo]
    total_count: int
    error_message: Optional[str] = None
