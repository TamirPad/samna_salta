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
    options: Dict[str, Any]


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
