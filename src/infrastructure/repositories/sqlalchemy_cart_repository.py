"""
SQLAlchemy implementation of CartRepository
"""

import logging
from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from src.domain.repositories.cart_repository import CartRepository
from src.domain.value_objects.product_id import ProductId
from src.domain.value_objects.telegram_id import TelegramId
from src.infrastructure.database.models import Cart as SQLCart
from src.infrastructure.database.models import Product as SQLProduct
from src.infrastructure.repositories.session_handler import managed_session

logger = logging.getLogger(__name__)


class SQLAlchemyCartRepository(CartRepository):
    """SQLAlchemy implementation of cart repository"""

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    async def get_cart_items(self, telegram_id: TelegramId) -> dict[str, Any] | None:
        """Get cart items for a user"""
        self._logger.info("🔍 GET CART: Fetching cart for user %s", telegram_id.value)
        with managed_session() as session:
            cart = (
                session.query(SQLCart)
                .filter(SQLCart.telegram_id == telegram_id.value)
                .first()
            )

            if not cart:
                self._logger.info(
                    "📭 NO CART: User %s has no cart", telegram_id.value
                )
                return None

            self._logger.info(
                "📦 CART FOUND: User %s has %d raw items",
                telegram_id.value,
                len(cart.items or []),
            )

            # Convert cart items to detailed format with product information
            detailed_items = []
            for i, item in enumerate(cart.items or []):
                product_id = item.get("product_id")
                self._logger.debug(
                    "📋 PROCESSING ITEM %d: product_id=%s, item=%s",
                    i,
                    product_id,
                    item,
                )

                product = (
                    session.query(SQLProduct)
                    .filter(SQLProduct.id == product_id)
                    .first()
                )

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
        """Add item to cart"""
        self._logger.info(
            "➕ ADD ITEM: User %s, Product %s, Qty %d, Options %s",
            telegram_id.value,
            product_id.value,
            quantity,
            options,
        )
        with managed_session() as session:
            # Get or create cart
            cart = (
                session.query(SQLCart)
                .filter(SQLCart.telegram_id == telegram_id.value)
                .first()
            )

            if not cart:
                self._logger.info(
                    "🆕 CREATING CART: New cart for user %s", telegram_id.value
                )
                cart = SQLCart(telegram_id=telegram_id.value, items=[])
                session.add(cart)
            else:
                self._logger.info(
                    "📦 EXISTING CART: Found cart with %d items",
                    len(cart.items or []),
                )

            # Get current items as a new list (important for SQLAlchemy change detection)
            items = list(cart.items or [])
            self._logger.debug("📋 CURRENT ITEMS: %s", items)

            # Check if item already exists in cart
            existing_item = None
            for i, item in enumerate(items):
                if (
                    item.get("product_id") == product_id.value
                    and item.get("options", {}) == options
                ):
                    existing_item = i
                    self._logger.info(
                        "🔄 UPDATING EXISTING: Item %d already exists, updating quantity",
                        i,
                    )
                    break

            if existing_item is not None:
                # Update quantity for existing item
                old_qty = items[existing_item]["quantity"]
                items[existing_item]["quantity"] += quantity
                self._logger.info(
                    "📈 QUANTITY UPDATE: %d → %d",
                    old_qty,
                    items[existing_item]["quantity"],
                )
            else:
                # Add new item
                new_item = {
                    "product_id": product_id.value,
                    "quantity": quantity,
                    "options": options,
                }
                items.append(new_item)
                self._logger.info("✨ NEW ITEM ADDED: %s", new_item)

            # CRITICAL: Assign the entire list to trigger SQLAlchemy change detection
            cart.items = items

            # Force SQLAlchemy to detect the change
            flag_modified(cart, "items")

            self._logger.info("💾 COMMITTING: %d items to database", len(items))

            # Verify the save by re-querying
            session.flush()  # Use flush to send changes without ending transaction
            session.refresh(cart)
            actual_items = len(cart.items or [])
            self._logger.info(
                "✅ CART UPDATED: User %s now has %d items (verified)",
                telegram_id.value,
                actual_items,
            )

            return True

    async def update_cart(
        self,
        telegram_id: TelegramId,
        items: list[dict[str, Any]],
        delivery_method: str | None = None,
        delivery_address: str | None = None,
    ) -> bool:
        """Update entire cart"""
        self._logger.info(
            "🔄 UPDATE CART: User %s, %d items, delivery=%s",
            telegram_id.value,
            len(items),
            delivery_method,
        )

        with managed_session() as session:
            # Get or create cart
            cart = (
                session.query(SQLCart)
                .filter(SQLCart.telegram_id == telegram_id.value)
                .first()
            )

            if not cart:
                self._logger.info(
                    "🆕 CREATING CART: New cart for user %s", telegram_id.value
                )
                cart = SQLCart(telegram_id=telegram_id.value)
                session.add(cart)

            # Update cart attributes
            cart.items = items
            if delivery_method is not None:
                cart.delivery_method = delivery_method
            if delivery_address is not None:
                cart.delivery_address = delivery_address

            # Force SQLAlchemy to detect changes in the JSON field
            flag_modified(cart, "items")

            self._logger.info("💾 COMMITTING cart update for user %s", telegram_id.value)
            return True

    async def clear_cart(self, telegram_id: TelegramId) -> bool:
        """Clear all items from a user's cart"""
        self._logger.info("🗑️ CLEAR CART: Clearing cart for user %s", telegram_id.value)

        with managed_session() as session:
            cart = (
                session.query(SQLCart)
                .filter(SQLCart.telegram_id == telegram_id.value)
                .first()
            )

            if cart:
                # Clear the items list
                cart.items = []

                # Force SQLAlchemy to detect the change
                flag_modified(cart, "items")

                self._logger.info(
                    "💾 COMMITTING cleared cart for user %s", telegram_id.value
                )

            else:
                self._logger.info(
                    "📭 NO CART TO CLEAR: User %s has no cart", telegram_id.value
                )
            return True

    async def get_or_create_cart(
        self, telegram_id: TelegramId
    ) -> dict[str, Any] | None:
        """Get or create a cart for a user and return it."""
        self._logger.info(
            "🛒 GET/CREATE CART: For user %s",
            telegram_id.value,
        )
        with managed_session() as session:
            cart = (
                session.query(SQLCart)
                .filter(SQLCart.telegram_id == telegram_id.value)
                .first()
            )

            if not cart:
                self._logger.info("🆕 CREATING new cart for user %s", telegram_id.value)
                cart = SQLCart(telegram_id=telegram_id.value, items=[])
                session.add(cart)
                session.flush()  # Ensure cart is in the session to be refreshed
                session.refresh(cart)
            else:
                self._logger.info("📦 EXISTING cart found for user %s", telegram_id.value)

            return {
                "telegram_id": cart.telegram_id,
                "items": cart.items,
                "delivery_method": cart.delivery_method,
                "delivery_address": cart.delivery_address,
            }
