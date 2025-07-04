"""
Cart management use case

Handles shopping cart operations for customers.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ...domain.value_objects.telegram_id import TelegramId
from ...domain.value_objects.product_id import ProductId
from ...domain.value_objects.money import Money
from ...domain.repositories.cart_repository import CartRepository
from ...domain.repositories.product_repository import ProductRepository


logger = logging.getLogger(__name__)


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
    items: List[CartItemInfo]
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
    
    def __init__(self, cart_repository: CartRepository, product_repository: ProductRepository):
        self._cart_repository = cart_repository
        self._product_repository = product_repository
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def add_to_cart(self, request: AddToCartRequest) -> CartOperationResponse:
        """Add item to customer's cart"""
        self._logger.info(f"🛒 CART USE CASE: Adding to cart - User: {request.telegram_id}, Product: {request.product_id}, Qty: {request.quantity}")
        
        try:
            # Validate telegram ID
            telegram_id = TelegramId(request.telegram_id)
            self._logger.debug(f"✅ TELEGRAM ID VALIDATED: {telegram_id.value}")
            
            # Validate product exists and is active
            product_id = ProductId(request.product_id)
            self._logger.debug(f"🔍 LOOKING UP PRODUCT: {product_id.value}")
            
            product = await self._product_repository.find_by_id(product_id)
            
            if not product:
                self._logger.warning(f"❌ PRODUCT NOT FOUND: {product_id.value}")
                return CartOperationResponse(
                    success=False,
                    error_message="Product not found"
                )
            
            self._logger.info(f"📦 PRODUCT FOUND: {product.name} (ID: {product.id}, Active: {product.is_active})")
            
            if not product.is_active:
                self._logger.warning(f"⚠️ PRODUCT INACTIVE: {product.name} is not available")
                return CartOperationResponse(
                    success=False,
                    error_message="Product is currently unavailable"
                )
            
            # Validate quantity
            if request.quantity <= 0:
                self._logger.warning(f"❌ INVALID QUANTITY: {request.quantity}")
                return CartOperationResponse(
                    success=False,
                    error_message="Quantity must be greater than 0"
                )
            
            self._logger.info(f"✅ VALIDATION PASSED: Adding {request.quantity} x {product.name}")
            
            # Add to cart
            success = await self._cart_repository.add_item(
                telegram_id=telegram_id,
                product_id=product_id,
                quantity=request.quantity,
                options=request.options or {}
            )
            
            if not success:
                self._logger.error(f"💥 CART REPOSITORY FAILED: Could not add item to cart")
                return CartOperationResponse(
                    success=False,
                    error_message="Failed to add item to cart"
                )
            
            self._logger.info(f"✅ CART REPOSITORY SUCCESS: Item added to cart")
            
            # Get updated cart summary
            cart_summary = await self._get_cart_summary(telegram_id)
            self._logger.info(f"📊 CART SUMMARY: {len(cart_summary.items)} items, total: {cart_summary.total}")
            
            return CartOperationResponse(
                success=True,
                cart_summary=cart_summary
            )
            
        except ValueError as e:
            self._logger.error(f"💥 VALIDATION ERROR adding to cart: {e}")
            return CartOperationResponse(
                success=False,
                error_message="Invalid request data"
            )
        except Exception as e:
            self._logger.error(f"💥 UNEXPECTED ERROR adding to cart: {e}", exc_info=True)
            return CartOperationResponse(
                success=False,
                error_message="Failed to add item to cart"
            )
    
    async def get_cart(self, telegram_id: int) -> CartOperationResponse:
        """Get customer's cart summary"""
        self._logger.info(f"👀 GET CART USE CASE: Retrieving cart for user {telegram_id}")
        
        try:
            telegram_id_vo = TelegramId(telegram_id)
            self._logger.debug(f"✅ TELEGRAM ID VALIDATED: {telegram_id_vo.value}")
            
            cart_summary = await self._get_cart_summary(telegram_id_vo)
            
            self._logger.info(f"📊 GET CART SUCCESS: {len(cart_summary.items)} items, total: {cart_summary.total}")
            
            return CartOperationResponse(
                success=True,
                cart_summary=cart_summary
            )
            
        except Exception as e:
            self._logger.error(f"💥 GET CART ERROR for user {telegram_id}: {e}", exc_info=True)
            return CartOperationResponse(
                success=False,
                error_message="Failed to retrieve cart"
            )
    
    async def update_cart(self, request: UpdateCartRequest) -> CartOperationResponse:
        """Update cart with new items and delivery information"""
        self._logger.info(f"🔄 UPDATE CART USE CASE: User {request.telegram_id}, {len(request.items)} items")
        
        try:
            telegram_id = TelegramId(request.telegram_id)
            
            # Update cart
            success = await self._cart_repository.update_cart(
                telegram_id=telegram_id,
                items=request.items,
                delivery_method=request.delivery_method,
                delivery_address=request.delivery_address
            )
            
            if not success:
                self._logger.error(f"💥 UPDATE CART FAILED: Repository returned false")
                return CartOperationResponse(
                    success=False,
                    error_message="Failed to update cart"
                )
            
            # Get updated cart summary
            cart_summary = await self._get_cart_summary(telegram_id)
            
            self._logger.info(f"✅ UPDATE CART SUCCESS: {len(cart_summary.items)} items, total: {cart_summary.total}")
            
            return CartOperationResponse(
                success=True,
                cart_summary=cart_summary
            )
            
        except Exception as e:
            self._logger.error(f"💥 UPDATE CART ERROR: {e}", exc_info=True)
            return CartOperationResponse(
                success=False,
                error_message="Failed to update cart"
            )
    
    async def clear_cart(self, telegram_id: int) -> CartOperationResponse:
        """Clear customer's cart"""
        self._logger.info(f"🗑️ CLEAR CART USE CASE: User {telegram_id}")
        
        try:
            telegram_id_vo = TelegramId(telegram_id)
            
            success = await self._cart_repository.clear_cart(telegram_id_vo)
            
            if not success:
                self._logger.error(f"💥 CLEAR CART FAILED: Repository returned false")
                return CartOperationResponse(
                    success=False,
                    error_message="Failed to clear cart"
                )
            
            self._logger.info(f"✅ CLEAR CART SUCCESS: User {telegram_id}")
            
            return CartOperationResponse(
                success=True,
                cart_summary=CartSummary(
                    items=[],
                    subtotal=0.0,
                    delivery_charge=0.0,
                    total=0.0
                )
            )
            
        except Exception as e:
            self._logger.error(f"💥 CLEAR CART ERROR: {e}", exc_info=True)
            return CartOperationResponse(
                success=False,
                error_message="Failed to clear cart"
            )
    
    async def _get_cart_summary(self, telegram_id: TelegramId) -> CartSummary:
        """Get cart summary with calculations"""
        self._logger.debug(f"📊 CALCULATING CART SUMMARY: User {telegram_id.value}")
        
        cart_data = await self._cart_repository.get_cart_items(telegram_id)
        
        if not cart_data:
            self._logger.debug(f"📭 EMPTY CART SUMMARY: User {telegram_id.value} has no cart data")
            return CartSummary(
                items=[],
                subtotal=0.0,
                delivery_charge=0.0,
                total=0.0
            )
        
        # Calculate totals
        subtotal = 0.0
        cart_items = []
        
        self._logger.debug(f"📋 PROCESSING {len(cart_data.get('items', []))} cart items")
        
        for i, item_data in enumerate(cart_data.get('items', [])):
            item_total = item_data['quantity'] * item_data['unit_price']
            subtotal += item_total
            
            cart_item = CartItemInfo(
                product_id=item_data['product_id'],
                product_name=item_data['product_name'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                total_price=item_total,
                options=item_data.get('options', {})
            )
            cart_items.append(cart_item)
            
            self._logger.debug(f"💰 ITEM {i}: {cart_item.product_name} x{cart_item.quantity} = {item_total}")
        
        # Calculate delivery charge
        delivery_charge = 0.0
        delivery_method = cart_data.get('delivery_method')
        if delivery_method == 'delivery':
            delivery_charge = 5.0  # 5 ILS delivery charge
            self._logger.debug(f"🚚 DELIVERY CHARGE: {delivery_charge}")
        
        total = subtotal + delivery_charge
        
        summary = CartSummary(
            items=cart_items,
            subtotal=subtotal,
            delivery_charge=delivery_charge,
            total=total,
            delivery_method=delivery_method,
            delivery_address=cart_data.get('delivery_address')
        )
        
        self._logger.info(f"📊 CART SUMMARY COMPLETE: {len(cart_items)} items, subtotal={subtotal}, delivery={delivery_charge}, total={total}")
        
        return summary 