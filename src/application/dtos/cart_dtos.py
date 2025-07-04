"""
Cart DTOs

Data Transfer Objects for cart-related operations.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class AddToCartRequest:
    """Request to add item to cart"""
    telegram_id: int
    product_id: int
    quantity: int = 1
    options: Optional[Dict[str, Any]] = None


@dataclass
class UpdateCartRequest:
    """Request to update cart"""
    telegram_id: int
    items: List[Dict[str, Any]]
    delivery_method: Optional[str] = None
    delivery_address: Optional[str] = None


@dataclass
class CartItemInfo:
    """Cart item information"""
    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    total_price: float
    options: Optional[Dict[str, Any]] = None


@dataclass
class GetCartResponse:
    """Response for getting cart contents"""
    success: bool
    cart_items: List[CartItemInfo] = None
    delivery_method: Optional[str] = None
    delivery_address: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class CartOperationResponse:
    """Response for cart operations"""
    success: bool
    cart_summary: Optional['CartSummary'] = None
    error_message: Optional[str] = None


@dataclass
class CartSummary:
    """Cart summary information"""
    items: List[CartItemInfo]
    subtotal: float
    delivery_charge: float
    total: float
    delivery_method: Optional[str] = None
    delivery_address: Optional[str] = None 