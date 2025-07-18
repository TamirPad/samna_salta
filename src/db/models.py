# pylint: disable=too-few-public-methods
"""
SQLAlchemy database models for the Samna Salta bot

Properly defined models with correct Base class and type annotations.
"""

from datetime import datetime
from typing import Any, List, Optional, Type

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import (
    DeclarativeMeta,
    Mapped,
    declarative_base,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func
from sqlalchemy.ext.mutable import MutableList  # local import to avoid circular deps

# Create declarative base with proper type annotation
_Base = declarative_base()

# Type alias for mypy
Base: Type[DeclarativeMeta] = _Base


class Customer(Base):
    """Customer model"""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    delivery_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_admin: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="customer")
    carts: Mapped[List["Cart"]] = relationship(
        "Cart",
        back_populates="customer",
        foreign_keys="Cart.customer_id",
    )

    @property
    def full_name(self) -> str:
        """Backward compatibility property for name"""
        return self.name

    @property
    def phone_number(self) -> Optional[str]:
        """Backward compatibility property for phone"""
        return self.phone


class MenuCategory(Base):
    """Menu category model"""

    __tablename__ = "menu_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    display_order: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    products: Mapped[List["Product"]] = relationship("Product", back_populates="category_rel")


class Product(Base):
    """Product model"""

    __tablename__ = "menu_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("menu_categories.id"), nullable=True
    )
    price: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    preparation_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, default=15, nullable=True)
    allergens: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=[], nullable=True)
    nutritional_info: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default={}, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    category_rel: Mapped[Optional["MenuCategory"]] = relationship("MenuCategory", back_populates="products")
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="product"
    )

    @property
    def price_display(self) -> str:
        """Display price with currency"""
        return f"{self.price:.2f} ILS"

    @property
    def category(self) -> Optional[str]:
        """Get category name for backward compatibility"""
        return self.category_rel.name if self.category_rel else None


class Cart(Base):
    """Shopping cart model"""

    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=True, unique=True
    )
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True, unique=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    delivery_method: Mapped[Optional[str]] = mapped_column(
        String(20), default="pickup", nullable=True
    )
    delivery_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        back_populates="carts",
        foreign_keys=[customer_id],
    )
    cart_items: Mapped[List["CartItem"]] = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    """Cart item model"""

    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("carts.id"), nullable=True
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("menu_products.id"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    special_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    product_options: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True, server_default="{}"
    )

    # Relationships
    cart: Mapped[Optional["Cart"]] = relationship("Cart", back_populates="cart_items")
    product: Mapped[Optional["Product"]] = relationship("Product")

    @property
    def total_price(self) -> float:
        """Calculate total price for this item"""
        return self.unit_price * self.quantity


class Order(Base):
    """Order model"""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=True
    )
    status: Mapped[Optional[str]] = mapped_column(String(50), default="pending", nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    delivery_fee: Mapped[Optional[float]] = mapped_column(Float, default=0, nullable=True)
    delivery_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivery_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order_type: Mapped[Optional[str]] = mapped_column(String(20), default="delivery", nullable=True)
    payment_method: Mapped[Optional[str]] = mapped_column(String(20), default="cash", nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    order_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, server_default="TEMP")
    subtotal: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    delivery_charge: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    delivery_method: Mapped[str] = mapped_column(String(20), default="pickup", nullable=False)
    total: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")

    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="orders")
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    """Order item model"""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("menu_products.id"), nullable=False
    )
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    product_options: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True, default={}
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="order_items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")


class CoreBusiness(Base):
    """Core business configuration model"""

    __tablename__ = "core_business"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, server_default="1")
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    coordinates: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # PostgreSQL point type
    delivery_radius_km: Mapped[Optional[float]] = mapped_column(Float, default=5.0, nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True)
    settings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default={}, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )


class AnalyticsDailySales(Base):
    """Daily sales analytics model"""

    __tablename__ = "analytics_daily_sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, unique=True)
    total_orders: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    total_revenue: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)
    total_items_sold: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    average_order_value: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )


class AnalyticsProductPerformance(Base):
    """Product performance analytics model"""

    __tablename__ = "analytics_product_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("menu_products.id"), nullable=True
    )
    total_orders: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    total_quantity_sold: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    total_revenue: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)
    last_updated: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )

    # Relationships
    product: Mapped[Optional["Product"]] = relationship("Product")
