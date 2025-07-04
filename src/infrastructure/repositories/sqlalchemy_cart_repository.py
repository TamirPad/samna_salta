"""
SQLAlchemy implementation of CartRepository
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.attributes import flag_modified

from ...domain.repositories.cart_repository import CartRepository
from ...domain.value_objects.telegram_id import TelegramId
from ...domain.value_objects.product_id import ProductId
from ..database.models import Cart as SQLCart, Product as SQLProduct
from ..database.operations import get_session


logger = logging.getLogger(__name__)


class SQLAlchemyCartRepository(CartRepository):
    """SQLAlchemy implementation of cart repository"""
    
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def get_cart_items(self, telegram_id: TelegramId) -> Optional[Dict[str, Any]]:
        """Get cart items for a user"""
        self._logger.info(f"🔍 GET CART: Fetching cart for user {telegram_id.value}")
        
        try:
            session = get_session()
            try:
                cart = session.query(SQLCart).filter(
                    SQLCart.telegram_id == telegram_id.value
                ).first()
                
                if not cart:
                    self._logger.info(f"📭 NO CART: User {telegram_id.value} has no cart")
                    return None
                
                self._logger.info(f"📦 CART FOUND: User {telegram_id.value} has {len(cart.items or [])} raw items")
                
                # Convert cart items to detailed format with product information
                detailed_items = []
                for i, item in enumerate(cart.items or []):
                    product_id = item.get('product_id')
                    self._logger.debug(f"📋 PROCESSING ITEM {i}: product_id={product_id}, item={item}")
                    
                    product = session.query(SQLProduct).filter(
                        SQLProduct.id == product_id
                    ).first()
                    
                    if product:
                        detailed_item = {
                            'product_id': product.id,
                            'product_name': product.name,
                            'quantity': item.get('quantity', 1),
                            'unit_price': product.base_price,
                            'options': item.get('options', {})
                        }
                        detailed_items.append(detailed_item)
                        self._logger.debug(f"✅ ITEM PROCESSED: {detailed_item}")
                    else:
                        self._logger.warning(f"⚠️ PRODUCT NOT FOUND: product_id={product_id} for cart item")
                
                result = {
                    'items': detailed_items,
                    'delivery_method': cart.delivery_method,
                    'delivery_address': cart.delivery_address
                }
                
                self._logger.info(f"📊 CART RESULT: {len(detailed_items)} valid items, delivery={cart.delivery_method}")
                return result
                
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"💥 DATABASE ERROR getting cart items for user {telegram_id.value}: {e}")
            raise
        except Exception as e:
            self._logger.error(f"💥 UNEXPECTED ERROR getting cart items for user {telegram_id.value}: {e}")
            raise
    
    async def add_item(self, telegram_id: TelegramId, product_id: ProductId, 
                      quantity: int, options: Dict[str, Any]) -> bool:
        """Add item to cart"""
        self._logger.info(f"➕ ADD ITEM: User {telegram_id.value}, Product {product_id.value}, Qty {quantity}, Options {options}")
        
        try:
            session = get_session()
            try:
                # Get or create cart
                cart = session.query(SQLCart).filter(
                    SQLCart.telegram_id == telegram_id.value
                ).first()
                
                if not cart:
                    self._logger.info(f"🆕 CREATING CART: New cart for user {telegram_id.value}")
                    cart = SQLCart(
                        telegram_id=telegram_id.value,
                        items=[]
                    )
                    session.add(cart)
                else:
                    self._logger.info(f"📦 EXISTING CART: Found cart with {len(cart.items or [])} items")
                
                # Get current items as a new list (important for SQLAlchemy change detection)
                items = list(cart.items or [])
                self._logger.debug(f"📋 CURRENT ITEMS: {items}")
                
                # Check if item already exists in cart
                existing_item = None
                for i, item in enumerate(items):
                    if (item.get('product_id') == product_id.value and 
                        item.get('options', {}) == options):
                        existing_item = i
                        self._logger.info(f"🔄 UPDATING EXISTING: Item {i} already exists, updating quantity")
                        break
                
                if existing_item is not None:
                    # Update quantity for existing item
                    old_qty = items[existing_item]['quantity']
                    items[existing_item]['quantity'] += quantity
                    self._logger.info(f"📈 QUANTITY UPDATE: {old_qty} → {items[existing_item]['quantity']}")
                else:
                    # Add new item
                    new_item = {
                        'product_id': product_id.value,
                        'quantity': quantity,
                        'options': options
                    }
                    items.append(new_item)
                    self._logger.info(f"✨ NEW ITEM ADDED: {new_item}")
                
                # CRITICAL: Assign the entire list to trigger SQLAlchemy change detection
                cart.items = items
                
                # Force SQLAlchemy to detect the change
                flag_modified(cart, 'items')
                
                self._logger.info(f"💾 COMMITTING: {len(items)} items to database")
                session.commit()
                
                # Verify the save by re-querying
                session.refresh(cart)
                actual_items = len(cart.items or [])
                self._logger.info(f"✅ CART UPDATED: User {telegram_id.value} now has {actual_items} items (verified)")
                
                return True
                
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"💥 DATABASE ERROR adding item to cart: User {telegram_id.value}, Product {product_id.value}, Error: {e}")
            raise
        except Exception as e:
            self._logger.error(f"💥 UNEXPECTED ERROR adding item to cart: User {telegram_id.value}, Product {product_id.value}, Error: {e}")
            raise
    
    async def update_cart(self, telegram_id: TelegramId, items: List[Dict[str, Any]], 
                         delivery_method: Optional[str] = None, 
                         delivery_address: Optional[str] = None) -> bool:
        """Update entire cart"""
        self._logger.info(f"🔄 UPDATE CART: User {telegram_id.value}, {len(items)} items, delivery={delivery_method}")
        
        try:
            session = get_session()
            try:
                # Get or create cart
                cart = session.query(SQLCart).filter(
                    SQLCart.telegram_id == telegram_id.value
                ).first()
                
                if not cart:
                    self._logger.info(f"🆕 CREATING CART: New cart for user {telegram_id.value}")
                    cart = SQLCart(telegram_id=telegram_id.value)
                    session.add(cart)
                else:
                    self._logger.info(f"📦 EXISTING CART: Found cart with {len(cart.items or [])} items")
                
                # Update cart data - create new list for SQLAlchemy change detection
                cart.items = list(items)
                if delivery_method is not None:
                    cart.delivery_method = delivery_method
                if delivery_address is not None:
                    cart.delivery_address = delivery_address
                
                # Force SQLAlchemy to detect the change
                flag_modified(cart, 'items')
                
                self._logger.info(f"💾 COMMITTING: {len(items)} items, delivery={cart.delivery_method}")
                session.commit()
                
                # Verify the save
                session.refresh(cart)
                actual_items = len(cart.items or [])
                self._logger.info(f"✅ CART UPDATED: User {telegram_id.value} now has {actual_items} items (verified)")
                
                return True
                
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"💥 DATABASE ERROR updating cart: User {telegram_id.value}, Error: {e}")
            raise
        except Exception as e:
            self._logger.error(f"💥 UNEXPECTED ERROR updating cart: User {telegram_id.value}, Error: {e}")
            raise
    
    async def clear_cart(self, telegram_id: TelegramId) -> bool:
        """Clear cart for user"""
        self._logger.info(f"🗑️ CLEAR CART: User {telegram_id.value}")
        
        try:
            session = get_session()
            try:
                cart = session.query(SQLCart).filter(
                    SQLCart.telegram_id == telegram_id.value
                ).first()
                
                if cart:
                    self._logger.info(f"📦 FOUND CART: User {telegram_id.value} had {len(cart.items or [])} items")
                    
                    # Clear cart data
                    cart.items = []
                    cart.delivery_method = None
                    cart.delivery_address = None
                    
                    # Force SQLAlchemy to detect the change
                    flag_modified(cart, 'items')
                    
                    self._logger.info(f"💾 COMMITTING: Cleared cart for user {telegram_id.value}")
                    session.commit()
                    
                    # Verify the clear
                    session.refresh(cart)
                    actual_items = len(cart.items or [])
                    self._logger.info(f"✅ CART CLEARED: User {telegram_id.value} now has {actual_items} items (verified)")
                else:
                    self._logger.info(f"📭 NO CART: User {telegram_id.value} had no cart to clear")
                
                return True
                
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"💥 DATABASE ERROR clearing cart: User {telegram_id.value}, Error: {e}")
            raise
        except Exception as e:
            self._logger.error(f"💥 UNEXPECTED ERROR clearing cart: User {telegram_id.value}, Error: {e}")
            raise
    
    async def get_or_create_cart(self, telegram_id: TelegramId) -> Optional[Dict[str, Any]]:
        """Get or create cart for user"""
        try:
            session = get_session()
            try:
                cart = session.query(SQLCart).filter(
                    SQLCart.telegram_id == telegram_id.value
                ).first()
                
                if not cart:
                    cart = SQLCart(
                        telegram_id=telegram_id.value,
                        items=[]
                    )
                    session.add(cart)
                    session.commit()
                
                return {
                    'items': cart.items or [],
                    'delivery_method': cart.delivery_method,
                    'delivery_address': cart.delivery_address
                }
                
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error getting/creating cart: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error getting/creating cart: {e}")
            raise 