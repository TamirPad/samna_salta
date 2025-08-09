# pylint: disable=too-few-public-methods
"""
SQLAlchemy database models for the Samna Salta bot

Properly defined models with correct Base class and type annotations.
"""

from datetime import datetime
from typing import Any, List, Optional, Type

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, BigInteger, String, Text, Index
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
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
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
        """Get phone number for backward compatibility"""
        return self.phone

    def __str__(self) -> str:
        return f"<Customer(id={self.id}, telegram_id={self.telegram_id}, name='{self.name}')>"


class MenuCategory(Base):
    """Menu category model"""

    __tablename__ = "menu_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
    
    # Multilingual support
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)  # Make required
    name_he: Mapped[str] = mapped_column(String(100), nullable=False)  # Make required
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_he: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    products: Mapped[List["Product"]] = relationship("Product", back_populates="category_rel")
    
    @property
    def display_name(self) -> str:
        """Get display name for the category"""
        return self.name_en.title()  # Use English as default

    def get_localized_name(self, language: str = "en") -> str:
        """Get localized name for the category"""
        if language == "he" and self.name_he:
            return self.name_he
        elif language == "en" and self.name_en:
            return self.name_en
        # Fallback to English if Hebrew is not available
        return self.name_en or "Uncategorized"

    def get_localized_description(self, language: str = "en") -> str:
        """Get localized description for the category"""
        if language == "he" and self.description_he:
            return self.description_he
        elif language == "en" and self.description_en:
            return self.description_en
        return self.description or ""  # Fallback to default description

    def __str__(self) -> str:
        return f"<MenuCategory(id={self.id}, name_en='{self.name_en}', name_he='{self.name_he}')>"


class ProductOption(Base):
    """Product option/variant model (e.g., Kubaneh Classic, Samneh Smoked)"""

    __tablename__ = "product_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    option_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'kubaneh_type', 'samneh_type'
    price_modifier: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    
    # Multilingual support
    name_en: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    name_he: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    display_name_en: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    display_name_he: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_he: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def get_localized_name(self, language: str = "en") -> str:
        """Get localized name for the option"""
        if language == "he" and self.name_he:
            return self.name_he
        elif language == "en" and self.name_en:
            return self.name_en
        return self.name_en or self.name  # Fallback to English name, then old name

    def get_localized_display_name(self, language: str = "en") -> str:
        """Get localized display name for the option"""
        if language == "he" and self.display_name_he:
            return self.display_name_he
        elif language == "en" and self.display_name_en:
            return self.display_name_en
        return self.display_name or self.name

    def get_localized_description(self, language: str = "en") -> str:
        """Get localized description for the option"""
        if language == "he" and self.description_he:
            return self.description_he
        elif language == "en" and self.description_en:
            return self.description_en
        return self.description or ""

    def __str__(self) -> str:
        return f"<ProductOption(id={self.id}, name='{self.name}', type='{self.option_type}')>"


class ProductSize(Base):
    """Product size model (e.g., Small, Medium, Large, XL)"""

    __tablename__ = "product_sizes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    price_modifier: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    
    # Multilingual support
    name_en: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    name_he: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_name_en: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_name_he: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    def get_localized_name(self, language: str = "en") -> str:
        """Get localized name for the size"""
        if language == "he" and self.name_he:
            return self.name_he
        elif language == "en" and self.name_en:
            return self.name_en
        return self.name_en or self.name  # Fallback to English name, then old name

    def get_localized_display_name(self, language: str = "en") -> str:
        """Get localized display name for the size"""
        if language == "he" and self.display_name_he:
            return self.display_name_he
        elif language == "en" and self.display_name_en:
            return self.display_name_en
        return self.display_name or self.name

    def __str__(self) -> str:
        return f"<ProductSize(id={self.id}, name='{self.name}')>"


class OrderStatus(Base):
    """Order status model"""

    __tablename__ = "order_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # For UI display
    icon: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Emoji or icon
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    
    # Multilingual support
    name_en: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    name_he: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_name_en: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_name_he: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_he: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def get_localized_name(self, language: str = "en") -> str:
        """Get localized name for the status"""
        if language == "he" and self.name_he:
            return self.name_he
        elif language == "en" and self.name_en:
            return self.name_en
        return self.name_en or self.name  # Fallback to English name, then old name

    def get_localized_display_name(self, language: str = "en") -> str:
        """Get localized display name for the status"""
        if language == "he" and self.display_name_he:
            return self.display_name_he
        elif language == "en" and self.display_name_en:
            return self.display_name_en
        return self.display_name or self.name

    def get_localized_description(self, language: str = "en") -> str:
        """Get localized description for the status"""
        if language == "he" and self.description_he:
            return self.description_he
        elif language == "en" and self.description_en:
            return self.description_en
        return self.description or ""

    def __str__(self) -> str:
        return f"<OrderStatus(id={self.id}, name='{self.name}')>"


class DeliveryMethod(Base):
    """Delivery method model"""

    __tablename__ = "delivery_methods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    charge: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    
    # Multilingual support
    name_en: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    name_he: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_name_en: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_name_he: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_he: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def get_localized_name(self, language: str = "en") -> str:
        """Get localized name for the delivery method"""
        if language == "he" and self.name_he:
            return self.name_he
        elif language == "en" and self.name_en:
            return self.name_en
        return self.name_en or self.name  # Fallback to English name, then old name

    def get_localized_display_name(self, language: str = "en") -> str:
        """Get localized display name for the delivery method"""
        if language == "he" and self.display_name_he:
            return self.display_name_he
        elif language == "en" and self.display_name_en:
            return self.display_name_en
        return self.display_name or self.name

    def get_localized_description(self, language: str = "en") -> str:
        """Get localized description for the delivery method"""
        if language == "he" and self.description_he:
            return self.description_he
        elif language == "en" and self.description_en:
            return self.description_en
        return self.description or ""

    def __str__(self) -> str:
        return f"<DeliveryMethod(id={self.id}, name='{self.name}')>"


class DeliveryArea(Base):
    """Delivery area model (admin-defined areas for delivery selection)"""

    __tablename__ = "delivery_areas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_he: Mapped[str] = mapped_column(String(100), nullable=False)
    charge: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def get_localized_name(self, language: str = "he") -> str:
        if language == "he":
            return self.name_he or self.name_en
        return self.name_en or self.name_he

    def __str__(self) -> str:
        return f"<DeliveryArea(id={self.id}, name_he='{self.name_he}', charge={self.charge})>"

class PaymentMethod(Base):
    """Payment method model"""

    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    
    # Multilingual support
    name_en: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    name_he: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_name_en: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_name_he: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_he: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def get_localized_name(self, language: str = "en") -> str:
        """Get localized name for the payment method"""
        if language == "he" and self.name_he:
            return self.name_he
        elif language == "en" and self.name_en:
            return self.name_en
        return self.name_en or self.name  # Fallback to English name, then old name

    def get_localized_display_name(self, language: str = "en") -> str:
        """Get localized display name for the payment method"""
        if language == "he" and self.display_name_he:
            return self.display_name_he
        elif language == "en" and self.display_name_en:
            return self.display_name_en
        return self.display_name or self.name

    def get_localized_description(self, language: str = "en") -> str:
        """Get localized description for the payment method"""
        if language == "he" and self.description_he:
            return self.description_he
        elif language == "en" and self.description_en:
            return self.description_en
        return self.description or ""

    def __str__(self) -> str:
        return f"<PaymentMethod(id={self.id}, name='{self.name}')>"


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
    
    # Multilingual support
    name_en: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    name_he: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_he: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
        if self.category_rel:
            # Use English name as the default category name for backward compatibility
            return self.category_rel.name_en
        return None
    
    @category.setter
    def category(self, value: Optional[str]):
        """Set category name for backward compatibility"""
        # This is a read-only property for backward compatibility
        # To set category, use category_rel relationship directly
        pass

    def get_localized_name(self, language: str = "en") -> str:
        """Get localized name for the product"""
        if language == "he" and self.name_he:
            return self.name_he
        elif language == "en" and self.name_en:
            return self.name_en
        return self.name  # Fallback to default name

    def get_localized_description(self, language: str = "en") -> str:
        """Get localized description for the product"""
        if language == "he" and self.description_he:
            return self.description_he
        elif language == "en" and self.description_en:
            return self.description_en
        return self.description or ""  # Fallback to default description

    def __str__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}')>"


class Cart(Base):
    """Shopping cart model"""

    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=True, unique=True
    )
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True)
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
    delivery_area_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("delivery_areas.id"), nullable=True)

    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        back_populates="carts",
        foreign_keys=[customer_id],
    )
    cart_items: Mapped[List["CartItem"]] = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")
    delivery_area: Mapped[Optional["DeliveryArea"]] = relationship("DeliveryArea")

    def __str__(self) -> str:
        return f"<Cart(id={self.id}, customer_id={self.customer_id})>"


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

    def __str__(self) -> str:
        return f"<CartItem(id={self.id}, cart_id={self.cart_id}, product_id={self.product_id}, quantity={self.quantity})>"


class Order(Base):
    """Order model"""

    __tablename__ = "orders"
    __table_args__ = (
        # Match provided DB schema indexes
        Index("idx_orders_customer", "customer_id"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=True
    )
    status: Mapped[Optional[str]] = mapped_column(String(50), default="pending", nullable=True)
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
    delivery_area_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("delivery_areas.id"), nullable=True)
    total: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")

    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="orders")
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    delivery_area: Mapped[Optional["DeliveryArea"]] = relationship("DeliveryArea")

    def __str__(self) -> str:
        return f"<Order(id={self.id}, customer_id={self.customer_id}, order_number='{self.order_number}')>"


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

    def __str__(self) -> str:
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, product_id={self.product_id}, quantity={self.quantity})>"


class BusinessSettings(Base):
    """Business settings model for storing editable business details"""

    __tablename__ = "business_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    business_name: Mapped[str] = mapped_column(String(200), nullable=False, default="Samna Salta")
    business_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    business_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    business_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    business_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    business_website: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    business_hours: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivery_charge: Mapped[float] = mapped_column(Float, nullable=False, default=5.00)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="ILS")
    hilbeh_available_days: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    hilbeh_available_hours: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    welcome_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    about_us: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON map of app-level images (step_key -> URL)
    app_images: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    def __str__(self) -> str:
        return f"<BusinessSettings(id={self.id}, name='{self.business_name}')>"

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "business_name": self.business_name,
            "business_description": self.business_description,
            "business_address": self.business_address,
            "business_phone": self.business_phone,
            "business_email": self.business_email,
            "business_website": self.business_website,
            "business_hours": self.business_hours,
            "delivery_charge": self.delivery_charge,
            "currency": self.currency,
            "hilbeh_available_days": self.hilbeh_available_days,
            "hilbeh_available_hours": self.hilbeh_available_hours,
            "welcome_message": self.welcome_message,
            "about_us": self.about_us,
            "contact_info": self.contact_info,
            "app_images": self.app_images,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
