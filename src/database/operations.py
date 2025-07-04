"""
Database operations for the Samna Salta bot
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from src.database.models import Base, Customer, Product, Order, OrderItem, Cart
from src.utils.config import get_config

logger = logging.getLogger(__name__)

# Database engine and session
_engine = None
_SessionLocal = None


def get_engine():
    """Get database engine"""
    global _engine
    if _engine is None:
        config = get_config()
        _engine = create_engine(config.database_url)
    return _engine


def get_session() -> Session:
    """Get database session"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal()


def init_db():
    """Initialize database tables"""
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Initialize default products
        init_default_products()
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {e}")
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
                    "oil": ["Olive oil", "Samneh"]
                }
            },
            {
                "name": "Samneh",
                "category": "spread",
                "description": "Traditional clarified butter",
                "base_price": 15.00,
                "options": {
                    "smoking": ["Smoked", "Not smoked"],
                    "size": ["Small", "Large"]
                }
            },
            {
                "name": "Red Bisbas",
                "category": "spice",
                "description": "Traditional Yemenite spice blend",
                "base_price": 12.00,
                "options": {
                    "size": ["Small", "Large"]
                }
            },
            {
                "name": "Hawaij soup spice",
                "category": "spice",
                "description": "Traditional soup spice blend",
                "base_price": 8.00,
                "options": {}
            },
            {
                "name": "Hawaij coffee spice",
                "category": "spice",
                "description": "Traditional coffee spice blend",
                "base_price": 8.00,
                "options": {}
            },
            {
                "name": "White coffee",
                "category": "beverage",
                "description": "Traditional Yemenite white coffee",
                "base_price": 10.00,
                "options": {}
            },
            {
                "name": "Hilbeh",
                "category": "spread",
                "description": "Traditional fenugreek spread (available Wed-Fri only)",
                "base_price": 18.00,
                "options": {}
            }
        ]
        
        for product_data in products:
            product = Product(**product_data)
            session.add(product)
        
        session.commit()
        logger.info(f"Initialized {len(products)} default products")
        
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Failed to initialize products: {e}")
        raise
    finally:
        session.close()


# Customer operations
def get_or_create_customer(telegram_id: int, full_name: str, phone_number: str) -> Customer:
    """Get existing customer or create new one"""
    session = get_session()
    try:
        customer = session.query(Customer).filter(
            Customer.phone_number == phone_number
        ).first()
        
        if customer:
            # Update telegram_id if it changed
            if customer.telegram_id != telegram_id:
                customer.telegram_id = telegram_id
                customer.updated_at = datetime.utcnow()
                session.commit()
            return customer
        
        # Create new customer
        customer = Customer(
            telegram_id=telegram_id,
            full_name=full_name,
            phone_number=phone_number
        )
        session.add(customer)
        session.commit()
        session.refresh(customer)
        return customer
        
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Failed to get/create customer: {e}")
        raise
    finally:
        session.close()


def get_customer_by_telegram_id(telegram_id: int) -> Optional[Customer]:
    """Get customer by telegram ID"""
    session = get_session()
    try:
        return session.query(Customer).filter(
            Customer.telegram_id == telegram_id
        ).first()
    finally:
        session.close()


# Product operations
def get_all_products() -> List[Product]:
    """Get all active products"""
    session = get_session()
    try:
        return session.query(Product).filter(Product.is_active == True).all()
    finally:
        session.close()


def get_product_by_name(name: str) -> Optional[Product]:
    """Get product by name"""
    session = get_session()
    try:
        return session.query(Product).filter(Product.name == name).first()
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
        logger.error(f"Failed to get/create cart: {e}")
        raise
    finally:
        session.close()


def update_cart(telegram_id: int, items: List[Dict], delivery_method: str = None, delivery_address: str = None):
    """Update cart items and delivery info"""
    session = get_session()
    try:
        cart = session.query(Cart).filter(Cart.telegram_id == telegram_id).first()
        
        if cart:
            cart.items = items
            cart.delivery_method = delivery_method
            cart.delivery_address = delivery_address
            cart.updated_at = datetime.utcnow()
        else:
            cart = Cart(
                telegram_id=telegram_id,
                items=items,
                delivery_method=delivery_method,
                delivery_address=delivery_address
            )
            session.add(cart)
        
        session.commit()
        
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Failed to update cart: {e}")
        raise
    finally:
        session.close()


def clear_cart(telegram_id: int):
    """Clear cart for user"""
    session = get_session()
    try:
        cart = session.query(Cart).filter(Cart.telegram_id == telegram_id).first()
        if cart:
            session.delete(cart)
            session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Failed to clear cart: {e}")
        raise
    finally:
        session.close()


# Order operations
def create_order(customer_id: int, order_number: str, delivery_method: str, 
                delivery_address: str, delivery_charge: float, subtotal: float, 
                total: float, items: List[Dict]) -> Order:
    """Create new order with items"""
    session = get_session()
    try:
        # Create order
        order = Order(
            customer_id=customer_id,
            order_number=order_number,
            delivery_method=delivery_method,
            delivery_address=delivery_address,
            delivery_charge=delivery_charge,
            subtotal=subtotal,
            total=total
        )
        session.add(order)
        session.flush()  # Get the order ID
        
        # Create order items
        for item_data in items:
            order_item = OrderItem(
                order_id=order.id,
                product_name=item_data["name"],
                product_options=item_data.get("options"),
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                total_price=item_data["total_price"]
            )
            session.add(order_item)
        
        session.commit()
        session.refresh(order)
        return order
        
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Failed to create order: {e}")
        raise
    finally:
        session.close()


def generate_order_number() -> str:
    """Generate unique order number"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"SS{timestamp}" 