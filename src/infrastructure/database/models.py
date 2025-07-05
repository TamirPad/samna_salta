# pylint: disable=too-few-public-methods
"""
SQLAlchemy database models for the Samna Salta bot

Properly defined models with correct Base class and type annotations.
"""

from datetime import datetime
from typing import Any, List, Optional, Type

from sqlalchemy import Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, DeclarativeMeta, relationship, Mapped, mapped_column
from sqlalchemy.sql import func

# Create declarative base with proper type annotation
_Base = declarative_base()

# Type alias for mypy
Base: Type[DeclarativeMeta] = _Base


class Customer(Base):
    """Customer model"""
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    delivery_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        onupdate=func.now(),
        nullable=True
    )

    # Relationships
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="customer")
    carts: Mapped[List["Cart"]] = relationship(
        "Cart",
        back_populates="customer",
        foreign_keys="Cart.customer_id",
    )


class Product(Base):
    """Product model"""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        onupdate=func.now(),
        nullable=True
    )

    # Relationships  
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="product")

    @property
    def price_display(self) -> str:
        """Display price with currency"""
        return f"{self.price:.2f} ILS"

    # Compatibility attribute expected by older code/tests
    @property
    def base_price(self) -> float:  # pragma: no cover
        """Alias for price kept for backward-compatibility."""
        return self.price


class Cart(Base):
    """Shopping cart model"""
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("customers.id"), nullable=True)
    items: Mapped[Optional[List[Any]]] = mapped_column(JSON, default=list, nullable=True)
    delivery_method: Mapped[str] = mapped_column(String(20), default="pickup", nullable=False)
    delivery_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        onupdate=func.now(),
        nullable=True
    )

    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        back_populates="carts",
        foreign_keys=[customer_id],
    )


class Order(Base):
    """Order model"""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    items: Mapped[List[Any]] = mapped_column(JSON, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    delivery_charge: Mapped[float] = mapped_column(Float, nullable=False)
    total: Mapped[float] = mapped_column(Float, nullable=False)
    delivery_method: Mapped[str] = mapped_column(String(20), default="pickup", nullable=False)
    delivery_address: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        onupdate=func.now(),
        nullable=True
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    """Order item model"""
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    product_options: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default={})
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="order_items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")
