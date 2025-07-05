"""
Database operations for the Samna Salta bot
"""

import logging
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import flag_modified

from src.infrastructure.configuration.config import get_config
from src.infrastructure.database.models import Base, Cart, Customer, Order, OrderItem, Product

logger = logging.getLogger(__name__)

# Database engine and session
class DatabaseSingleton:
    """Singleton for the database engine and session"""

    _ENGINE: Optional[Engine] = None
    _session_factory: Optional[Callable[[], Session]] = None

    @classmethod
    def get_engine(cls) -> Engine:
        """Get database engine"""
        if cls._ENGINE is None:
            config = get_config()
            cls._ENGINE = create_engine(config.database_url)
        return cls._ENGINE

    @classmethod
    def get_session(cls) -> Session:
        """Get database session"""
        if cls._session_factory is None:
            cls._session_factory = sessionmaker(
                autocommit=False, autoflush=False, bind=cls.get_engine()
            )
        return cls._session_factory()  # pylint: disable=not-callable


def get_engine():
    """Get database engine"""
    return DatabaseSingleton.get_engine()


def get_session() -> Session:
    """Get database session"""
    return DatabaseSingleton.get_session()


def init_db():
    """Initialize database tables"""
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

        # Initialize default products
        init_default_products()

    except SQLAlchemyError as e:
        logger.error("Failed to initialize database: %s", e)
        raise


def init_default_products():
    """Initialize default products in the database"""
    session = get_session()
    try:
        # Check if products already exist
        if session.query(Product).count() > 0:
            logger.info("Products already exist, skipping initialization")
            return

        # Default products configuration
        products = [
            {
                "name": "Kubaneh",
                "category": "bread",
                "description": "Traditional Yemenite bread",
                "base_price": 25.00,
                "options": {
                    "type": ["Classic", "Seeded", "Herb", "Aromatic"],
                    "oil": ["Olive oil", "Samneh"],
                },
            },
            {
                "name": "Samneh",
                "category": "spread",
                "description": "Traditional clarified butter",
                "base_price": 15.00,
                "options": {
                    "smoking": ["Smoked", "Not smoked"],
                    "size": ["Small", "Large"],
                },
            },
            {
                "name": "Red Bisbas",
                "category": "spice",
                "description": "Traditional Yemenite spice blend",
                "base_price": 12.00,
                "options": {"size": ["Small", "Large"]},
            },
            {
                "name": "Hawaij soup spice",
                "category": "spice",
                "description": "Traditional soup spice blend",
                "base_price": 8.00,
                "options": {},
            },
            {
                "name": "Hawaij coffee spice",
                "category": "spice",
                "description": "Traditional coffee spice blend",
                "base_price": 8.00,
                "options": {},
            },
            {
                "name": "White coffee",
                "category": "beverage",
                "description": "Traditional Yemenite white coffee",
                "base_price": 10.00,
                "options": {},
            },
            {
                "name": "Hilbeh",
                "category": "spread",
                "description": "Traditional fenugreek spread (available Wed-Fri only)",
                "base_price": 18.00,
                "options": {},
            },
        ]

        for product_data in products:
            product = Product(**product_data)
            session.add(product)

        session.commit()
        logger.info("Initialized %d default products", len(products))

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to initialize products: %s", e)
        raise
    finally:
        session.close()


# Customer operations
def get_or_create_customer(
    telegram_id: int, full_name: str, phone_number: str
) -> Customer:
    """Get existing customer or create new one"""
    session = get_session()
    try:
        customer = (
            session.query(Customer)
            .filter(Customer.phone_number == phone_number)
            .first()
        )

        if customer:
            # Update telegram_id if it changed
            if customer.telegram_id != telegram_id:
                customer.telegram_id = telegram_id
                customer.updated_at = datetime.utcnow()
                session.commit()
            return customer

        # Create new customer
        customer = Customer(
            telegram_id=telegram_id, full_name=full_name, phone_number=phone_number
        )
        session.add(customer)
        session.commit()
        session.refresh(customer)
        return customer

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to get/create customer: %s", e)
        raise
    finally:
        session.close()


def get_customer_by_telegram_id(telegram_id: int) -> Customer | None:
    """Get customer by telegram ID"""
    session = get_session()
    try:
        return (
            session.query(Customer).filter(Customer.telegram_id == telegram_id).first()
        )
    finally:
        session.close()


# Product operations
def get_all_products() -> list[Product]:
    """Get all active products"""
    session = get_session()
    try:
        return session.query(Product).filter(Product.is_active).all()
    finally:
        session.close()


def get_product_by_name(name: str) -> Product | None:
    """Get product by name"""
    session = get_session()
    try:
        return session.query(Product).filter(Product.name == name).first()
    finally:
        session.close()


def get_product_by_id(product_id: int) -> Product | None:
    """Get product by ID"""
    session = get_session()
    try:
        return session.query(Product).filter(Product.id == product_id).first()
    finally:
        session.close()


# Cart operations
def get_or_create_cart(telegram_id: int) -> Cart:
    """Get existing cart or create new one"""
    session = get_session()
    try:
        cart = session.query(Cart).filter(Cart.telegram_id == telegram_id).first()

        if not cart:
            cart = Cart(telegram_id=telegram_id, items=[])
            session.add(cart)
            session.commit()
            session.refresh(cart)

        return cart

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to get/create cart: %s", e)
        raise
    finally:
        session.close()


def add_to_cart(
    telegram_id: int, product_id: int, quantity: int = 1, options: dict | None = None
) -> bool:
    """Add item to cart or update quantity if it exists"""
    session = get_session()
    try:
        cart = get_or_create_cart(telegram_id)
        product = get_product_by_id(product_id)

        if not product:
            logger.warning("Product with ID %d not found", product_id)
            return False

        # Create a unique key for the item based on product_id and options
        options_key = tuple(sorted(options.items())) if options else ()
        
        # Check if item with the same product_id and options already exists
        existing_item = next(
            (
                item
                for item in cart.items
                if item.get("product_id") == product_id
                and tuple(sorted(item.get("options", {}).items())) == options_key
            ),
            None,
        )

        if existing_item:
            # Update quantity if item exists
            existing_item["quantity"] += quantity
        else:
            # Add new item to cart
            new_item = {
                "product_id": product_id,
                "quantity": quantity,
                "options": options,
                "price": product.base_price,  # Store price at time of adding
            }
            cart.items.append(new_item)

        # Mark 'items' field as modified for JSON mutation tracking
        flag_modified(cart, "items")

        session.commit()
        return True

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to add to cart: %s", e)
        return False
    finally:
        session.close()


def get_cart_items(telegram_id: int) -> list[dict]:
    """Get cart items for user"""
    session = get_session()
    try:
        cart = session.query(Cart).filter(Cart.telegram_id == telegram_id).first()
        if cart and cart.items:
            # Convert to cart item objects for compatibility
            cart_items = []
            for item in cart.items:
                cart_item = type(
                    "CartItem",
                    (),
                    {"product_id": item["product_id"], "quantity": item["quantity"]},
                )()
                cart_items.append(cart_item)
            return cart_items
        return []
    finally:
        session.close()


def update_cart(
    telegram_id: int,
    items: list[dict],
    delivery_method: str | None = None,
    delivery_address: str | None = None,
) -> bool:
    """Update cart with new items and delivery info"""
    session = get_session()
    try:
        cart = get_or_create_cart(telegram_id)

        # Update cart items
        cart.items = items

        # Update delivery info
        if delivery_method:
            cart.delivery_method = delivery_method
        if delivery_address:
            cart.delivery_address = delivery_address

        # Mark 'items' field as modified for JSON mutation tracking
        flag_modified(cart, "items")

        session.commit()
        return True

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to update cart: %s", e)
        return False
    finally:
        session.close()


def clear_cart(telegram_id: int) -> bool:
    """Clear all items from a cart"""
    session = get_session()
    try:
        cart = session.query(Cart).filter(Cart.telegram_id == telegram_id).first()
        if cart:
            session.delete(cart)
            session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to clear cart: %s", e)
        return False
    finally:
        session.close()


def remove_from_cart(telegram_id: int, product_id: int) -> bool:
    """Remove item from cart"""
    session = get_session()
    try:
        cart = session.query(Cart).filter(Cart.telegram_id == telegram_id).first()
        if not cart:
            return False

        # Find and remove item from cart
        cart.items = [
            item for item in cart.items if item.get("product_id") != product_id
        ]

        # Mark 'items' field as modified for JSON mutation tracking
        flag_modified(cart, "items")

        session.commit()
        return True

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to remove from cart: %s", e)
        raise
    finally:
        session.close()


# Order operations
def create_order(
    customer_id: int,
    total_amount: float,
    delivery_method: str = "pickup",
    delivery_address: str | None = None,
) -> Order | None:
    """Create new order with items"""
    session = get_session()
    try:
        # Generate order number
        order_number = generate_order_number()

        # Calculate delivery charge
        delivery_charge = 5.0 if delivery_method == "delivery" else 0.0
        subtotal = total_amount - delivery_charge

        # Create order
        order = Order(
            customer_id=customer_id,
            order_number=order_number,
            delivery_method=delivery_method,
            delivery_address=delivery_address,
            delivery_charge=delivery_charge,
            subtotal=subtotal,
            total=total_amount,
        )
        session.add(order)
        session.flush()  # Get the order ID

        # Get customer's cart to create order items
        customer = session.query(Customer).filter(Customer.id == customer_id).first()
        if customer:
            cart = (
                session.query(Cart)
                .filter(Cart.telegram_id == customer.telegram_id)
                .first()
            )
            if cart and cart.items:
                for item_data in cart.items:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_name=item_data["product_name"],
                        product_options=item_data.get("options"),
                        quantity=item_data["quantity"],
                        unit_price=item_data["unit_price"],
                        total_price=item_data["unit_price"] * item_data["quantity"],
                    )
                    session.add(order_item)

        session.commit()
        session.refresh(order)
        return order

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to create order: %s", e)
        return None
    finally:
        session.close()


def generate_order_number() -> str:
    """Generate unique order number"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"SS{timestamp}"


def get_all_customers() -> list[Customer]:
    """Get all customers"""
    session = get_session()
    try:
        return session.query(Customer).all()
    finally:
        session.close()


def get_all_orders() -> list[Order]:
    """Get all orders"""
    session = get_session()
    try:
        return session.query(Order).order_by(Order.created_at.desc()).all()
    finally:
        session.close()
