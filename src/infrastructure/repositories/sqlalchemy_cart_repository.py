"""
SQLAlchemy Cart Repository

Concrete implementation of CartRepository using SQLAlchemy ORM.
"""

import logging
from contextlib import contextmanager
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from src.domain.repositories.cart_repository import CartRepository
from src.domain.value_objects.product_id import ProductId
from src.domain.value_objects.telegram_id import TelegramId
from src.infrastructure.database.models import Cart as SQLCart
from src.infrastructure.database.models import Product as SQLProduct
from src.infrastructure.database.operations import (  # compatibility for tests
    get_session,
)


@contextmanager
def managed_session():  # type: ignore
    session = get_session()
    try:
        yield session
    finally:
        session.close()


class SQLAlchemyCartRepository(CartRepository):
    """SQLAlchemy implementation of cart repository"""

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    async def get_cart_items(self, telegram_id: TelegramId) -> dict[str, Any] | None:
        """Get cart items for a user - OPTIMIZED VERSION"""
        self._logger.info("🔍 GET CART: Fetching cart for user %s", telegram_id.value)
        with managed_session() as session:
            cart = (
                session.query(SQLCart)
                .filter(SQLCart.telegram_id == telegram_id.value)
                .first()
            )

            if not cart:
                self._logger.info("📭 NO CART: User %s has no cart", telegram_id.value)
                return None

            cart_items = cart.items or []
            self._logger.info(
                "📦 CART FOUND: User %s has %d raw items",
                telegram_id.value,
                len(cart_items),
            )

            if not cart_items:
                return {
                    "items": [],
                    "delivery_method": cart.delivery_method,
                    "delivery_address": cart.delivery_address,
                }

            # OPTIMIZATION: Batch load all products in one query
            product_ids = [item.get("product_id") for item in cart_items if item.get("product_id")]
            
            if not product_ids:
                self._logger.warning("⚠️ NO VALID PRODUCT IDs found in cart items")
                return {
                    "items": [],
                    "delivery_method": cart.delivery_method,
                    "delivery_address": cart.delivery_address,
                }

            # Single query to get all products
            products = (
                session.query(SQLProduct)
                .filter(SQLProduct.id.in_(product_ids))
                .all()
            )
            
            # Create product lookup dictionary for O(1) access
            products_by_id = {product.id: product for product in products}
            
            self._logger.info("📋 BATCH LOADED %d products for cart", len(products))

            # Convert cart items to detailed format with product information
            detailed_items = []
            for i, item in enumerate(cart_items):
                product_id = item.get("product_id")
                self._logger.debug(
                    "📋 PROCESSING ITEM %d: product_id=%s, item=%s",
                    i,
                    product_id,
                    item,
                )

                product = products_by_id.get(product_id)
                if product:
                    detailed_item = {
                        "product_id": product.id,
                        "product_name": product.name,
                        "quantity": item.get("quantity", 1),
                        "unit_price": product.base_price,
                        "options": item.get("options", {}),
                    }
                    detailed_items.append(detailed_item)
                    self._logger.debug("✅ ITEM PROCESSED: %s", detailed_item)
                else:
                    self._logger.warning(
                        "⚠️ PRODUCT NOT FOUND: product_id=%s for cart item",
                        product_id,
                    )

            result = {
                "items": detailed_items,
                "delivery_method": cart.delivery_method,
                "delivery_address": cart.delivery_address,
            }

            self._logger.info(
                "📊 CART RESULT: %d valid items, delivery=%s",
                len(detailed_items),
                cart.delivery_method,
            )
            return result

    async def add_item(
        self,
        telegram_id: TelegramId,
        product_id: ProductId,
        quantity: int,
        options: dict[str, Any],
    ) -> bool:
        """Add item to cart with options (required by abstract class)"""
        self._logger.info(
            "➕ ADD ITEM: User %s, Product %s, Qty %d, Options %s",
            telegram_id.value,
            product_id.value,
            quantity,
            options,
        )

        try:
            with managed_session() as session:
                # Get or create cart
                cart = (
                    session.query(SQLCart)
                    .filter(SQLCart.telegram_id == telegram_id.value)
                    .first()
                )

                if not cart:
                    cart = SQLCart(
                        telegram_id=telegram_id.value,
                        items=[],
                        delivery_method="pickup",
                    )
                    session.add(cart)
                    self._logger.info("🆕 CART CREATED for user %s", telegram_id.value)

                # Add or update item with options
                items = cart.items or []
                item_found = False

                for item in items:
                    if (item.get("product_id") == product_id.value and 
                        item.get("options", {}) == options):
                        item["quantity"] = item.get("quantity", 0) + quantity
                        item_found = True
                        self._logger.info(
                            "🔄 ITEM UPDATED: Product %s, New quantity %d",
                            product_id.value,
                            item["quantity"],
                        )
                        break

                if not item_found:
                    items.append({
                        "product_id": product_id.value, 
                        "quantity": quantity,
                        "options": options
                    })
                    self._logger.info(
                        "🆕 ITEM ADDED: Product %s, Quantity %d, Options %s",
                        product_id.value,
                        quantity,
                        options,
                    )

                cart.items = items
                session.commit()

                self._logger.info("✅ CART UPDATE SUCCESS")
                return True

        except SQLAlchemyError as e:
            self._logger.error("💥 DATABASE ERROR adding item to cart: %s", e)
            raise
        except Exception as e:
            self._logger.error("💥 UNEXPECTED ERROR adding item to cart: %s", e)
            raise

    async def add_to_cart(
        self, telegram_id: TelegramId, product_id: ProductId | int, quantity: int = 1
    ) -> bool:
        """Add item to cart without options (convenience method)"""
        # Handle both ProductId objects and plain integers
        if isinstance(product_id, ProductId):
            product_id_obj = product_id
        else:
            product_id_obj = ProductId(product_id)

        # Call the required abstract method with empty options
        return await self.add_item(telegram_id, product_id_obj, quantity, {})

    async def update_cart(
        self,
        telegram_id: TelegramId,
        items: list[dict[str, Any]],
        delivery_method: str | None = None,
        delivery_address: str | None = None,
    ) -> bool:
        """Update entire cart (required by abstract class)"""
        self._logger.info(
            "🔄 UPDATE CART: User %s, %d items, delivery=%s",
            telegram_id.value,
            len(items),
            delivery_method,
        )

        try:
            with managed_session() as session:
                # Get or create cart
                cart = (
                    session.query(SQLCart)
                    .filter(SQLCart.telegram_id == telegram_id.value)
                    .first()
                )

                if not cart:
                    cart = SQLCart(
                        telegram_id=telegram_id.value,
                        items=items,
                        delivery_method=delivery_method or "pickup",
                        delivery_address=delivery_address,
                    )
                    session.add(cart)
                    self._logger.info("🆕 CART CREATED for user %s", telegram_id.value)
                else:
                    # Update cart attributes
                    cart.items = items
                    if delivery_method is not None:
                        cart.delivery_method = delivery_method
                    if delivery_address is not None:
                        cart.delivery_address = delivery_address
                    self._logger.info("🔄 CART UPDATED for user %s", telegram_id.value)

                session.commit()

                self._logger.info("✅ CART UPDATE SUCCESS")
                return True

        except SQLAlchemyError as e:
            self._logger.error("💥 DATABASE ERROR updating cart: %s", e)
            raise
        except Exception as e:
            self._logger.error("💥 UNEXPECTED ERROR updating cart: %s", e)
            raise

    async def get_or_create_cart(
        self, telegram_id: TelegramId
    ) -> dict[str, Any] | None:
        """Get or create cart for user (required by abstract class)"""
        self._logger.info("🛒 GET/CREATE CART: For user %s", telegram_id.value)
        
        try:
            with managed_session() as session:
                cart = (
                    session.query(SQLCart)
                    .filter(SQLCart.telegram_id == telegram_id.value)
                    .first()
                )

                if not cart:
                    self._logger.info("🆕 CREATING new cart for user %s", telegram_id.value)
                    cart = SQLCart(
                        telegram_id=telegram_id.value, 
                        items=[],
                        delivery_method="pickup"
                    )
                    session.add(cart)
                    session.commit()
                    session.refresh(cart)
                else:
                    self._logger.info("📦 EXISTING cart found for user %s", telegram_id.value)

                return {
                    "telegram_id": cart.telegram_id,
                    "items": cart.items or [],
                    "delivery_method": cart.delivery_method,
                    "delivery_address": cart.delivery_address,
                }

        except SQLAlchemyError as e:
            self._logger.error("💥 DATABASE ERROR getting/creating cart: %s", e)
            raise
        except Exception as e:
            self._logger.error("💥 UNEXPECTED ERROR getting/creating cart: %s", e)
            raise

    async def remove_from_cart(
        self, telegram_id: TelegramId, product_id: ProductId | int
    ) -> bool:
        """Remove item from cart"""
        # Handle both ProductId objects and plain integers
        if isinstance(product_id, ProductId):
            product_id_value = product_id.value
        else:
            product_id_value = product_id

        self._logger.info(
            "➖ REMOVE FROM CART: User %s, Product %s",
            telegram_id.value,
            product_id_value,
        )

        try:
            with managed_session() as session:
                cart = (
                    session.query(SQLCart)
                    .filter(SQLCart.telegram_id == telegram_id.value)
                    .first()
                )

                if not cart:
                    self._logger.info("📭 NO CART: User %s has no cart", telegram_id.value)
                    return False

                # Remove item
                items = cart.items or []
                original_count = len(items)
                items = [
                    item
                    for item in items
                    if item.get("product_id") != product_id_value
                ]

                if len(items) < original_count:
                    cart.items = items
                    session.commit()
                    self._logger.info("✅ ITEM REMOVED from cart")
                    return True
                else:
                    self._logger.info("📭 ITEM NOT FOUND in cart")
                    return False

        except SQLAlchemyError as e:
            self._logger.error("💥 DATABASE ERROR removing from cart: %s", e)
            raise
        except Exception as e:
            self._logger.error("💥 UNEXPECTED ERROR removing from cart: %s", e)
            raise

    async def clear_cart(self, telegram_id: TelegramId) -> bool:
        """Clear all items from cart"""
        self._logger.info("🗑️ CLEAR CART: User %s", telegram_id.value)

        try:
            with managed_session() as session:
                cart = (
                    session.query(SQLCart)
                    .filter(SQLCart.telegram_id == telegram_id.value)
                    .first()
                )

                if not cart:
                    self._logger.info("📭 NO CART: User %s has no cart", telegram_id.value)
                    return True

                cart.items = []
                session.commit()

                self._logger.info("✅ CART CLEARED")
                return True

        except SQLAlchemyError as e:
            self._logger.error("💥 DATABASE ERROR clearing cart: %s", e)
            raise
        except Exception as e:
            self._logger.error("💥 UNEXPECTED ERROR clearing cart: %s", e)
            raise

    async def update_delivery_info(
        self, telegram_id: TelegramId, delivery_method: str, delivery_address: str | None = None
    ) -> bool:
        """Update delivery information for cart"""
        self._logger.info(
            "🚚 UPDATE DELIVERY: User %s, Method %s",
            telegram_id.value,
            delivery_method,
        )

        try:
            with managed_session() as session:
                cart = (
                    session.query(SQLCart)
                    .filter(SQLCart.telegram_id == telegram_id.value)
                    .first()
                )

                if not cart:
                    # Create cart if it doesn't exist
                    cart = SQLCart(
                        telegram_id=telegram_id.value,
                        items=[],
                        delivery_method=delivery_method,
                        delivery_address=delivery_address,
                    )
                    session.add(cart)
                    self._logger.info("🆕 CART CREATED with delivery info")
                else:
                    cart.delivery_method = delivery_method
                    cart.delivery_address = delivery_address
                    self._logger.info("🔄 DELIVERY INFO UPDATED")

                session.commit()

                self._logger.info("✅ DELIVERY UPDATE SUCCESS")
                return True

        except SQLAlchemyError as e:
            self._logger.error("💥 DATABASE ERROR updating delivery info: %s", e)
            raise
        except Exception as e:
            self._logger.error("💥 UNEXPECTED ERROR updating delivery info: %s", e)
            raise
