"""
Cart management use case

Handles shopping cart operations for customers.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.application.dtos.order_dtos import OrderItemInfo
from src.domain.repositories.cart_repository import CartRepository
from src.domain.repositories.product_repository import ProductRepository
from src.domain.value_objects.product_id import ProductId
from src.domain.value_objects.telegram_id import TelegramId

logger = logging.getLogger(__name__)


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
class CartSummary:
    """Cart summary information"""

    items: List[OrderItemInfo]
    subtotal: float
    delivery_charge: float
    total: float
    delivery_method: Optional[str] = None
    delivery_address: Optional[str] = None


@dataclass
class CartOperationResponse:
    """Response for cart operations"""

    success: bool
    cart_summary: Optional[CartSummary] = None
    error_message: Optional[str] = None


class CartManagementUseCase:
    """
    Use case for cart management operations

    Handles:
    1. Adding items to cart
    2. Removing items from cart
    3. Updating cart quantities
    4. Getting cart summary
    5. Clearing cart
    """

    def __init__(
        self, cart_repository: CartRepository, product_repository: ProductRepository
    ):
        self._cart_repository = cart_repository
        self._product_repository = product_repository
        self._logger = logging.getLogger(self.__class__.__name__)

    async def add_to_cart(self, request: AddToCartRequest) -> CartOperationResponse:
        """Add item to customer's cart"""
        self._logger.info(
            "🛒 CART USE CASE: Adding to cart - User: %s, Product: %s, Qty: %s",
            request.telegram_id,
            request.product_id,
            request.quantity,
        )

        try:
            telegram_id, product = await self._validate_add_to_cart_request(request)

            # Add to cart
            success = await self._cart_repository.add_item(
                telegram_id=telegram_id,
                product_id=product.id,
                quantity=request.quantity,
                options=request.options or {},
            )

            if not success:
                self._logger.error(
                    "💥 CART REPOSITORY FAILED: Could not add item to cart"
                )
                return CartOperationResponse(
                    success=False, error_message="Failed to add item to cart"
                )

            self._logger.info("✅ CART REPOSITORY SUCCESS: Item added to cart")

            # Get updated cart summary
            cart_summary = await self._get_cart_summary(telegram_id)
            self._logger.info(
                "📊 CART SUMMARY: %d items, total: %s",
                len(cart_summary.items),
                cart_summary.total,
            )

            return CartOperationResponse(success=True, cart_summary=cart_summary)

        except ValueError as e:
            self._logger.error("💥 VALIDATION ERROR adding to cart: %s", e)
            return CartOperationResponse(
                success=False, error_message="Invalid request data"
            )
        except (TypeError, AttributeError) as e:
            self._logger.error("💥 UNEXPECTED ERROR adding to cart: %s", e, exc_info=True)
            return CartOperationResponse(
                success=False, error_message="Failed to add item to cart"
            )

    async def _validate_add_to_cart_request(self, request: AddToCartRequest):
        """Validate the add to cart request"""
        telegram_id = TelegramId(request.telegram_id)
        product_id = ProductId(request.product_id)
        product = await self._product_repository.find_by_id(product_id)

        if not product:
            raise ValueError("Product not found")

        if not product.is_active:
            raise ValueError("Product is currently unavailable")

        if request.quantity <= 0:
            raise ValueError("Quantity must be greater than 0")

        return telegram_id, product

    async def get_cart(self, telegram_id: int) -> CartOperationResponse:
        """Get customer's cart summary"""
        self._logger.info(
            "👀 GET CART USE CASE: Retrieving cart for user %s", telegram_id
        )

        try:
            telegram_id_vo = TelegramId(telegram_id)
            self._logger.debug("✅ TELEGRAM ID VALIDATED: %s", telegram_id_vo.value)

            cart_summary = await self._get_cart_summary(telegram_id_vo)

            self._logger.info(
                "📊 GET CART SUCCESS: %d items, total: %s",
                len(cart_summary.items),
                cart_summary.total,
            )

            return CartOperationResponse(success=True, cart_summary=cart_summary)

        except (ValueError, TypeError) as e:
            self._logger.error(
                "💥 GET CART ERROR for user %s: %s", telegram_id, e, exc_info=True
            )
            return CartOperationResponse(
                success=False, error_message="Failed to retrieve cart"
            )

    async def update_cart(self, request: UpdateCartRequest) -> CartOperationResponse:
        """Update cart with new items and delivery information"""
        self._logger.info(
            "🔄 UPDATE CART USE CASE: User %s, %d items",
            request.telegram_id,
            len(request.items),
        )

        try:
            telegram_id = TelegramId(request.telegram_id)

            # Update cart
            success = await self._cart_repository.update_cart(
                telegram_id=telegram_id,
                items=request.items,
                delivery_method=request.delivery_method,
                delivery_address=request.delivery_address,
            )

            if not success:
                self._logger.error("💥 UPDATE CART FAILED: Repository returned false")
                return CartOperationResponse(
                    success=False, error_message="Failed to update cart"
                )

            # Get updated cart summary
            cart_summary = await self._get_cart_summary(telegram_id)

            self._logger.info(
                "✅ UPDATE CART SUCCESS: %d items, total: %s",
                len(cart_summary.items),
                cart_summary.total,
            )

            return CartOperationResponse(success=True, cart_summary=cart_summary)

        except (ValueError, TypeError) as e:
            self._logger.error("💥 UPDATE CART ERROR: %s", e, exc_info=True)
            return CartOperationResponse(
                success=False, error_message="Failed to update cart"
            )

    async def clear_cart(self, telegram_id: int) -> CartOperationResponse:
        """Clear customer's cart"""
        self._logger.info("🗑️ CLEAR CART USE CASE: User %s", telegram_id)

        try:
            telegram_id_vo = TelegramId(telegram_id)

            success = await self._cart_repository.clear_cart(telegram_id_vo)

            if not success:
                self._logger.error("💥 CLEAR CART FAILED: Repository returned false")
                return CartOperationResponse(
                    success=False, error_message="Failed to clear cart"
                )

            self._logger.info("✅ CART CLEARED: User %s", telegram_id)

            return CartOperationResponse(success=True, cart_summary=None)

        except (ValueError, TypeError) as e:
            self._logger.error("💥 CLEAR CART ERROR: %s", e, exc_info=True)
            return CartOperationResponse(
                success=False, error_message="Failed to clear cart"
            )

    async def _get_cart_summary(self, telegram_id: TelegramId) -> CartSummary:
        """Get cart summary from repository and calculate totals"""
        self._logger.info("📊 CALCULATING CART SUMMARY: User %s", telegram_id.value)

        cart_data = await self._cart_repository.get_cart_items(telegram_id)
        if not cart_data or not cart_data.get("items"):
            self._logger.info("  -> Empty cart, returning default summary")
            return CartSummary(items=[], subtotal=0, delivery_charge=0, total=0)

        cart_items = cart_data["items"]
        self._logger.info("  -> Found %d items in cart", len(cart_items))

        summary_items: List[OrderItemInfo] = []
        subtotal = 0.0

        for item_data in cart_items:
            item_total = item_data["quantity"] * item_data["unit_price"]
            subtotal += item_total
            summary_items.append(
                OrderItemInfo.from_dict(item_data, total_price=item_total)
            )

        delivery_method = cart_data.get("delivery_method", "pickup")
        delivery_charge = 5.0 if delivery_method == "delivery" else 0.0
        total = subtotal + delivery_charge

        self._logger.info(
            "  -> Summary: Subtotal=%.2f, Delivery=%.2f, Total=%.2f",
            subtotal,
            delivery_charge,
            total,
        )

        return CartSummary(
            items=summary_items,
            subtotal=subtotal,
            delivery_charge=delivery_charge,
            total=total,
            delivery_method=delivery_method,
            delivery_address=cart_data.get("delivery_address"),
        )
