# pylint: disable=too-few-public-methods
"""
Database models for the Samna Salta bot
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Customer(Base):
    """Customer model"""

    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    delivery_address = Column(Text, nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    orders = relationship("Order", back_populates="customer")


class Product(Base):
    """Product model"""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    base_price = Column(Float, nullable=False)
    options = Column(JSON, nullable=True)  # Store available options
    image_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def price(self) -> float:
        """Compatibility property for base_price"""
        return self.base_price

    @price.setter
    def price(self, value: float) -> None:
        """Compatibility setter for base_price"""
        self.base_price = value


class Order(Base):
    """Order model"""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_number = Column(String(20), unique=True, nullable=False)
    delivery_method = Column(String(20), nullable=False)  # 'pickup' or 'delivery'
    delivery_address = Column(Text, nullable=True)
    delivery_charge = Column(Float, default=0.0)
    subtotal = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    status = Column(
        String(20), default="pending"
    )  # pending, confirmed, completed, cancelled
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    """Order item model"""

    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_name = Column(String(100), nullable=False)
    product_options = Column(JSON, nullable=True)  # Store selected options
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="items")


class Cart(Base):
    """Shopping cart model (temporary storage)"""

    __tablename__ = "carts"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    items = Column(JSON, nullable=False, default=list)  # Store cart items as JSON
    delivery_method = Column(String(20), nullable=True)
    delivery_address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
