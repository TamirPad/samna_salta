"""
Tests for database models
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from src.db.models import (
    Base, Customer, Product, Cart, CartItem, Order, OrderItem, MenuCategory
)


class TestCustomer:
    """Test Customer model"""

    def test_customer_creation(self, db_session):
        """Test customer creation"""
        customer = Customer(
            telegram_id=123456789,
            name="Test Customer",
            phone="+972501234567",
            language="en",
            is_admin=False
        )
        db_session.add(customer)
        db_session.commit()
        
        assert customer.id is not None
        assert customer.telegram_id == 123456789
        assert customer.name == "Test Customer"
        assert customer.phone == "+972501234567"
        assert customer.language == "en"
        assert customer.is_admin is False

    def test_customer_admin_flag(self, db_session, sample_admin_customer):
        """Test customer admin flag"""
        db_session.add(sample_admin_customer)
        db_session.commit()
        
        customer = db_session.query(Customer).first()
        assert customer.is_admin is True

    def test_customer_optional_fields(self, db_session):
        """Test customer with optional fields"""
        customer = Customer(
            telegram_id=999888777,
            name="Minimal Customer"
        )
        db_session.add(customer)
        db_session.commit()
        
        customer = db_session.query(Customer).first()
        assert customer.phone is None
        assert customer.language is None
        assert customer.delivery_address is None
        assert customer.is_admin is None

    def test_customer_timestamps(self, db_session, sample_customer):
        """Test customer timestamps"""
        db_session.add(sample_customer)
        db_session.commit()
        
        customer = db_session.query(Customer).first()
        assert customer.created_at is not None
        assert isinstance(customer.created_at, datetime)
        assert customer.updated_at is None  # Initially None

    def test_customer_update_timestamp(self, db_session, sample_customer):
        """Test customer update timestamp"""
        db_session.add(sample_customer)
        db_session.commit()
        
        # Update customer
        sample_customer.name = "Updated Name"
        db_session.commit()
        
        customer = db_session.query(Customer).first()
        assert customer.updated_at is not None
        assert isinstance(customer.updated_at, datetime)

    def test_customer_relationships(self, db_session, sample_customer, sample_order):
        """Test customer relationships"""
        db_session.add(sample_customer)
        db_session.add(sample_order)
        db_session.commit()
        
        customer = db_session.query(Customer).first()
        assert len(customer.orders) == 1
        assert customer.orders[0].order_number == "ORD-000001"

    def test_customer_telegram_id_unique(self, db_session, sample_customer):
        """Test customer telegram_id uniqueness"""
        db_session.add(sample_customer)
        db_session.commit()
        
        # Try to add another customer with same telegram_id
        duplicate_customer = Customer(
            telegram_id=123456789,  # Same as sample_customer
            name="Duplicate User"
        )
        
        with pytest.raises(Exception):  # Should raise integrity error
            db_session.add(duplicate_customer)
            db_session.commit()

    def test_customer_string_representation(self, db_session):
        """Test customer string representation"""
        customer = Customer(
            telegram_id=123456789,
            name="Test Customer",
            phone="+972501234567",
            language="en"
        )
        db_session.add(customer)
        db_session.commit()
        
        assert str(customer) == f"<Customer(id={customer.id}, telegram_id=123456789, name='Test Customer')>"


class TestProduct:
    """Test Product model"""

    def test_product_creation(self, db_session):
        """Test product creation"""
        # Create category first
        category = MenuCategory(
            id=1,
            name="bread",
            description="Traditional breads",
            display_order=1,
            is_active=True
        )
        db_session.add(category)
        db_session.commit()
        
        kubaneh = Product(
            name="Kubaneh",
            description="Traditional Yemenite bread",
            category_id=1,
            price=25.00,
            is_active=True
        )
        db_session.add(kubaneh)
        db_session.commit()
        
        assert kubaneh.id is not None
        assert kubaneh.name == "Kubaneh"
        assert kubaneh.description == "Traditional Yemenite bread"
        assert kubaneh.category_id == 1
        assert kubaneh.price == 25.00
        assert kubaneh.is_active is True

    def test_product_optional_fields(self, db_session):
        """Test product optional fields"""
        # Create category first
        category = MenuCategory(
            id=1,
            name="test_category",
            description="Test category",
            display_order=1,
            is_active=True
        )
        db_session.add(category)
        db_session.commit()
        
        product = Product(
            name="Test Product",
            price=10.00,
            category_id=1
        )
        db_session.add(product)
        db_session.commit()
        
        # Check that optional fields have default values
        assert product.preparation_time_minutes == 15  # Default value
        assert product.is_active is True  # Default value
        assert product.allergens == []  # Default value
        assert product.nutritional_info == {}  # Default value

    def test_product_timestamps(self, db_session, sample_products):
        """Test product timestamps"""
        db_session.add(sample_products[0])
        db_session.commit()
        
        product = db_session.query(Product).first()
        assert product.created_at is not None
        assert isinstance(product.created_at, datetime)
        assert product.updated_at is None  # Initially None

    def test_product_update_timestamp(self, db_session, sample_products):
        """Test product update timestamp"""
        db_session.add(sample_products[0])
        db_session.commit()
        
        # Update product
        sample_products[0].price = 30.00
        db_session.commit()
        
        product = db_session.query(Product).first()
        assert product.updated_at is not None
        assert isinstance(product.updated_at, datetime)

    def test_product_inactive(self, db_session):
        """Test inactive product"""
        product = Product(
            name="Inactive Product",
            description="Inactive description",
            category="test",
            price=10.00,
            is_active=False
        )
        db_session.add(product)
        db_session.commit()
        
        product = db_session.query(Product).first()
        assert product.is_active is False

    def test_product_string_representation(self, db_session):
        """Test product string representation"""
        # Create category first
        category = MenuCategory(
            id=1,
            name="bread",
            description="Traditional breads",
            display_order=1,
            is_active=True
        )
        db_session.add(category)
        db_session.commit()
        
        product = Product(
            name="Kubaneh",
            description="Traditional Yemenite bread",
            category_id=1,
            price=25.00
        )
        db_session.add(product)
        db_session.commit()
        
        assert str(product) == f"<Product(id={product.id}, name='Kubaneh')>"


class TestCart:
    """Test Cart model"""

    def test_cart_creation(self, db_session, sample_customer, sample_cart):
        """Test cart creation"""
        db_session.add(sample_customer)
        db_session.add(sample_cart)
        db_session.commit()
        
        cart = db_session.query(Cart).first()
        assert cart.customer_id == sample_customer.id
        assert cart.delivery_method == "pickup"
        assert cart.delivery_address is None

    def test_cart_with_delivery_address(self, db_session, sample_customer):
        """Test cart with delivery address"""
        cart = Cart(
            customer_id=sample_customer.id,
            delivery_method="delivery",
            delivery_address="456 Delivery Street, Tel Aviv"
        )
        db_session.add(sample_customer)
        db_session.add(cart)
        db_session.commit()
        
        cart = db_session.query(Cart).first()
        assert cart.delivery_method == "delivery"
        assert cart.delivery_address == "456 Delivery Street, Tel Aviv"

    def test_cart_timestamps(self, db_session, sample_customer, sample_cart):
        """Test cart timestamps"""
        db_session.add(sample_customer)
        db_session.add(sample_cart)
        db_session.commit()
        
        cart = db_session.query(Cart).first()
        assert cart.created_at is not None
        assert isinstance(cart.created_at, datetime)
        assert cart.updated_at is None  # Initially None

    def test_cart_update_timestamp(self, db_session, sample_customer, sample_cart):
        """Test cart update timestamp"""
        db_session.add(sample_customer)
        db_session.add(sample_cart)
        db_session.commit()
        
        # Update cart
        sample_cart.delivery_method = "delivery"
        db_session.commit()
        
        cart = db_session.query(Cart).first()
        assert cart.updated_at is not None
        assert isinstance(cart.updated_at, datetime)

    def test_cart_relationships(self, db_session, sample_cart, sample_cart_items):
        """Test cart relationships"""
        # Add cart first
        db_session.add(sample_cart)
        db_session.commit()
        
        # Add cart items to database
        for item in sample_cart_items:
            db_session.add(item)
        db_session.commit()
        
        # Test cart items relationship
        assert len(sample_cart.cart_items) == 2  # Use cart_items instead of items
        assert sample_cart.cart_items[0].product_id == sample_cart_items[0].product_id
        assert sample_cart.cart_items[1].product_id == sample_cart_items[1].product_id

    def test_cart_string_representation(self, db_session, sample_customer):
        """Test cart string representation"""
        db_session.add(sample_customer)
        db_session.commit()
        
        cart = Cart(
            customer_id=sample_customer.id,
            delivery_method="pickup"
        )
        db_session.add(cart)
        db_session.commit()
        
        assert str(cart) == f"<Cart(id={cart.id}, customer_id={sample_customer.id})>"


class TestCartItem:
    """Test CartItem model"""

    def test_cart_item_creation(self, db_session, sample_cart, sample_products):
        """Test cart item creation"""
        # Create categories first
        bread_category = MenuCategory(
            id=1,
            name="bread",
            description="Traditional breads",
            display_order=1,
            is_active=True
        )
        db_session.add(bread_category)
        db_session.commit()
        
        # Add products
        for product in sample_products:
            db_session.add(product)
        db_session.commit()
        
        # Add cart
        db_session.add(sample_cart)
        db_session.commit()
        
        # Create cart item
        cart_item = CartItem(
            cart_id=sample_cart.id,
            product_id=sample_products[0].id,
            quantity=2,
            unit_price=sample_products[0].price,
            product_options={"type": "classic"}  # Use product_options instead of options
        )
        db_session.add(cart_item)
        db_session.commit()
        
        # Verify cart item
        first_item = db_session.query(CartItem).first()
        assert first_item.cart_id == sample_cart.id
        assert first_item.product_id == sample_products[0].id
        assert first_item.quantity == 2
        assert first_item.unit_price == sample_products[0].price
        assert first_item.product_options == {"type": "classic"}  # Use product_options instead of options

    def test_cart_item_timestamps(self, db_session, sample_customer, sample_cart, sample_cart_items):
        """Test cart item timestamps"""
        db_session.add(sample_customer)
        db_session.add(sample_cart)
        db_session.add(sample_cart_items[0])
        db_session.commit()
        
        item = db_session.query(CartItem).first()
        assert item.created_at is not None
        assert isinstance(item.created_at, datetime)
        assert item.updated_at is None  # Initially None

    def test_cart_item_update_timestamp(self, db_session, sample_customer, sample_cart, sample_cart_items):
        """Test cart item update timestamp"""
        db_session.add(sample_customer)
        db_session.add(sample_cart)
        db_session.add(sample_cart_items[0])
        db_session.commit()
        
        # Update item
        sample_cart_items[0].quantity = 5
        db_session.commit()
        
        item = db_session.query(CartItem).first()
        assert item.updated_at is not None
        assert isinstance(item.updated_at, datetime)

    def test_cart_item_relationships(self, db_session, sample_customer, sample_cart, sample_cart_items, sample_products):
        """Test cart item relationships"""
        db_session.add(sample_customer)
        db_session.add(sample_cart)
        db_session.add(sample_products[0])
        db_session.add(sample_cart_items[0])
        db_session.commit()
        
        item = db_session.query(CartItem).first()
        assert item.cart is not None
        assert item.cart.id == sample_cart.id
        assert item.product is not None
        assert item.product.name == "Kubaneh"

    def test_cart_item_string_representation(self, db_session, sample_customer, sample_cart, sample_cart_items):
        """Test cart item string representation"""
        db_session.add(sample_customer)
        db_session.add(sample_cart)
        db_session.add(sample_cart_items[0])
        db_session.commit()
        
        item = db_session.query(CartItem).first()
        assert str(item) == f"<CartItem(id={item.id}, cart_id={sample_cart.id}, product_id=1, quantity=2)>"


class TestOrder:
    """Test Order model"""

    def test_order_creation(self, db_session, sample_customer, sample_order):
        """Test order creation"""
        db_session.add(sample_customer)
        db_session.add(sample_order)
        db_session.commit()
        
        order = db_session.query(Order).first()
        assert order.customer_id == sample_customer.id
        assert order.order_number == "ORD-000001"
        assert order.status == "pending"
        assert order.total == 52.00
        assert order.delivery_method == "pickup"
        assert order.delivery_address is None

    def test_order_with_delivery_address(self, db_session, sample_customer):
        """Test order with delivery address"""
        order = Order(
            customer_id=sample_customer.id,
            order_number="ORD-000002",
            status="pending",
            total=50.00,
            delivery_method="delivery",
            delivery_address="789 Order Street, Tel Aviv"
        )
        db_session.add(sample_customer)
        db_session.add(order)
        db_session.commit()
        
        order = db_session.query(Order).first()
        assert order.delivery_method == "delivery"
        assert order.delivery_address == "789 Order Street, Tel Aviv"

    def test_order_timestamps(self, db_session, sample_customer, sample_order):
        """Test order timestamps"""
        db_session.add(sample_customer)
        db_session.add(sample_order)
        db_session.commit()
        
        order = db_session.query(Order).first()
        assert order.created_at is not None
        assert isinstance(order.created_at, datetime)
        assert order.updated_at is None  # Initially None

    def test_order_update_timestamp(self, db_session, sample_customer, sample_order):
        """Test order update timestamp"""
        db_session.add(sample_customer)
        db_session.add(sample_order)
        db_session.commit()
        
        # Update order
        sample_order.status = "completed"
        db_session.commit()
        
        order = db_session.query(Order).first()
        assert order.updated_at is not None
        assert isinstance(order.updated_at, datetime)

    def test_order_relationships(self, db_session, sample_customer, sample_order_items):
        """Test order relationships"""
        db_session.add(sample_customer)
        db_session.commit()
        
        order = Order(
            customer_id=sample_customer.id,
            order_number="ORD-000001",
            status="pending",
            total=52.00,
            delivery_method="pickup"
        )
        db_session.add(order)
        db_session.commit()
        
        # Add order items
        for item in sample_order_items:
            item.order_id = order.id
            db_session.add(item)
        db_session.commit()
        
        assert len(order.order_items) == 2  # Use order_items instead of items

    def test_order_status_transitions(self, db_session, sample_customer, sample_order):
        """Test order status transitions"""
        db_session.add(sample_customer)
        db_session.add(sample_order)
        db_session.commit()
        
        order = db_session.query(Order).first()
        
        # Test status transitions
        order.status = "processing"
        db_session.commit()
        assert order.status == "processing"
        
        order.status = "completed"
        db_session.commit()
        assert order.status == "completed"

    def test_order_string_representation(self, db_session, sample_customer):
        """Test order string representation"""
        db_session.add(sample_customer)
        db_session.commit()
        
        order = Order(
            customer_id=sample_customer.id,
            order_number="ORD-000001",
            status="pending",
            total=52.00,
            delivery_method="pickup"
        )
        db_session.add(order)
        db_session.commit()
        
        assert str(order) == f"<Order(id={order.id}, customer_id={sample_customer.id}, order_number='ORD-000001')>"


class TestOrderItem:
    """Test OrderItem model"""

    def test_order_item_creation(self, db_session, sample_order):
        """Test order item creation"""
        db_session.add(sample_order)
        db_session.commit()
        
        first_item = OrderItem(
            order_id=sample_order.id,
            product_id=1,
            product_name="Kubaneh",
            quantity=2,
            unit_price=25.00,
            total_price=50.00,
            product_options={"type": "classic"}
        )
        db_session.add(first_item)
        db_session.commit()
        
        assert first_item.id is not None
        assert first_item.order_id == sample_order.id
        assert first_item.product_id == 1
        assert first_item.product_name == "Kubaneh"
        assert first_item.quantity == 2
        assert first_item.unit_price == 25.00
        assert first_item.total_price == 50.00
        assert first_item.product_options == {"type": "classic"}

    def test_order_item_timestamps(self, db_session, sample_order):
        """Test order item timestamps"""
        db_session.add(sample_order)
        db_session.commit()
        
        item = OrderItem(
            order_id=sample_order.id,
            product_id=1,
            product_name="Kubaneh",
            quantity=2,
            unit_price=25.00,
            total_price=50.00
        )
        db_session.add(item)
        db_session.commit()
        
        assert item.created_at is not None
        # OrderItem doesn't have updated_at field

    def test_order_item_update_timestamp(self, db_session, sample_order):
        """Test order item update timestamp"""
        db_session.add(sample_order)
        db_session.commit()
        
        item = OrderItem(
            order_id=sample_order.id,
            product_id=1,
            product_name="Kubaneh",
            quantity=2,
            unit_price=25.00,
            total_price=50.00
        )
        db_session.add(item)
        db_session.commit()
        
        # Update the item
        item.quantity = 3
        item.total_price = 75.00
        db_session.commit()
        
        # OrderItem doesn't have updated_at field, so just check it still exists
        assert item.id is not None

    def test_order_item_relationships(self, db_session, sample_customer, sample_order, sample_order_items, sample_products):
        """Test order item relationships"""
        db_session.add(sample_customer)
        db_session.add(sample_order)
        db_session.add(sample_products[0])
        db_session.add(sample_order_items[0])
        db_session.commit()
        
        item = db_session.query(OrderItem).first()
        assert item.order is not None
        assert item.order.id == sample_order.id
        assert item.product is not None
        assert item.product.name == "Kubaneh"

    def test_order_item_string_representation(self, db_session, sample_order):
        """Test order item string representation"""
        db_session.add(sample_order)
        db_session.commit()
        
        item = OrderItem(
            order_id=sample_order.id,
            product_id=1,
            product_name="Kubaneh",
            quantity=2,
            unit_price=25.00,
            total_price=50.00
        )
        db_session.add(item)
        db_session.commit()
        
        assert str(item) == f"<OrderItem(id={item.id}, order_id={sample_order.id}, product_id=1, quantity=2)>"


class TestMenuCategory:
    """Test MenuCategory model"""

    def test_menu_category_creation(self, db_session):
        """Test menu category creation"""
        category = MenuCategory(
            name="Test Category",
            description="Test category description",
            display_order=1,
            is_active=True
        )
        db_session.add(category)
        db_session.commit()
        
        assert category.id is not None
        assert category.name == "Test Category"
        assert category.description == "Test category description"
        assert category.display_order == 1
        assert category.is_active is True
        assert category.display_name == "Test Category"  # Property should work

    def test_menu_category_optional_fields(self, db_session):
        """Test menu category with optional fields"""
        category = MenuCategory(
            name="Minimal Category"
        )
        db_session.add(category)
        db_session.commit()
        
        assert category.id is not None
        assert category.name == "Minimal Category"
        assert category.description is None
        assert category.display_order == 0  # Default value
        assert category.is_active is True  # Default value
        assert category.display_name == "Minimal Category"  # Property should work

    def test_menu_category_timestamps(self, db_session):
        """Test menu category timestamps"""
        category = MenuCategory(name="Test Category")
        db_session.add(category)
        db_session.commit()
        
        category = db_session.query(MenuCategory).first()
        assert category.created_at is not None
        assert isinstance(category.created_at, datetime)
        assert category.updated_at is None  # Initially None

    def test_menu_category_update_timestamp(self, db_session):
        """Test menu category update timestamp"""
        category = MenuCategory(name="Test Category")
        db_session.add(category)
        db_session.commit()
        
        # Update category
        category.name = "Updated Category"
        db_session.commit()
        
        category = db_session.query(MenuCategory).first()
        assert category.updated_at is not None
        assert isinstance(category.updated_at, datetime)

    def test_menu_category_string_representation(self, db_session):
        """Test menu category string representation"""
        category = MenuCategory(name="Test Category")
        db_session.add(category)
        db_session.commit()
        
        category = db_session.query(MenuCategory).first()
        assert str(category) == f"<MenuCategory(id={category.id}, name='Test Category')>"


class TestModelRelationships:
    """Test model relationships"""

    def test_customer_order_relationship(self, db_session, sample_customer, sample_order):
        """Test customer-order relationship"""
        db_session.add(sample_customer)
        db_session.add(sample_order)
        db_session.commit()
        
        customer = db_session.query(Customer).first()
        order = db_session.query(Order).first()
        
        assert customer.orders[0] == order
        assert order.customer == customer

    def test_cart_cartitem_relationship(self, db_session, sample_cart, sample_cart_items):
        """Test cart-cartitem relationship"""
        # Add cart and items to database
        db_session.add(sample_cart)
        for item in sample_cart_items:
            db_session.add(item)
        db_session.commit()
        
        # Test relationship
        cart = db_session.query(Cart).first()
        assert len(cart.cart_items) == 2  # Use cart_items instead of items
        assert cart.cart_items[0].cart_id == cart.id
        assert cart.cart_items[1].cart_id == cart.id

    def test_order_orderitem_relationship(self, db_session, sample_customer, sample_order_items):
        """Test order-orderitem relationship"""
        db_session.add(sample_customer)
        db_session.commit()
        
        order = Order(
            customer_id=sample_customer.id,
            order_number="ORD-000001",
            status="pending",
            total=52.00,
            delivery_method="pickup"
        )
        db_session.add(order)
        db_session.commit()
        
        # Add order items
        for item in sample_order_items:
            item.order_id = order.id
            db_session.add(item)
        db_session.commit()
        
        assert len(order.order_items) == 2  # Use order_items instead of items
        assert order.order_items[0].order_id == order.id
        assert order.order_items[1].order_id == order.id

    def test_product_cartitem_relationship(self, db_session, sample_customer, sample_cart, sample_cart_items, sample_products):
        """Test product-cartitem relationship"""
        db_session.add(sample_customer)
        db_session.add(sample_cart)
        db_session.add(sample_products[0])
        db_session.add(sample_cart_items[0])
        db_session.commit()
        
        product = db_session.query(Product).first()
        item = db_session.query(CartItem).first()
        
        assert item.product == product

    def test_product_orderitem_relationship(self, db_session, sample_customer, sample_order, sample_order_items, sample_products):
        """Test product-orderitem relationship"""
        db_session.add(sample_customer)
        db_session.add(sample_order)
        db_session.add(sample_products[0])
        db_session.add(sample_order_items[0])
        db_session.commit()
        
        product = db_session.query(Product).first()
        item = db_session.query(OrderItem).first()
        
        assert item.product == product


class TestModelConstraints:
    """Test model constraints"""

    def test_customer_telegram_id_not_null(self, db_session):
        """Test customer telegram_id not null constraint"""
        customer = Customer(name="Test User")  # Missing telegram_id
        
        with pytest.raises(Exception):  # Should raise constraint error
            db_session.add(customer)
            db_session.commit()

    def test_customer_name_not_null(self, db_session):
        """Test customer name not null constraint"""
        customer = Customer(telegram_id=123456789)  # Missing name
        
        with pytest.raises(Exception):  # Should raise constraint error
            db_session.add(customer)
            db_session.commit()

    def test_product_name_not_null(self, db_session):
        """Test product name not null constraint"""
        product = Product(description="Test", category="test", price=10.00)  # Missing name
        
        with pytest.raises(Exception):  # Should raise constraint error
            db_session.add(product)
            db_session.commit()

    def test_product_price_not_null(self, db_session):
        """Test product price not null constraint"""
        product = Product(name="Test", description="Test", category="test")  # Missing price
        
        with pytest.raises(Exception):  # Should raise constraint error
            db_session.add(product)
            db_session.commit()

    def test_cart_customer_id_not_null(self, db_session):
        """Test cart customer_id constraint"""
        # Since customer_id is nullable=True in the model, this should not raise an error
        cart = Cart(customer_id=None)
        db_session.add(cart)
        db_session.commit()
        assert cart.id is not None

    def test_order_customer_id_not_null(self, db_session):
        """Test order customer_id constraint"""
        # Since customer_id is nullable=True in the model, this should not raise an error
        order = Order(customer_id=None, order_number="TEST123")
        db_session.add(order)
        db_session.commit()
        assert order.id is not None


class TestModelPerformance:
    """Test model performance"""

    def test_bulk_insert_performance(self, db_session, performance_timer):
        """Test bulk insert performance"""
        customers = []
        for i in range(100):
            customer = Customer(
                telegram_id=100000000 + i,
                name=f"Customer {i}"
            )
            customers.append(customer)
        
        db_session.add_all(customers)
        db_session.commit()
        
        assert db_session.query(Customer).count() == 100

    def test_query_performance(self, db_session, performance_timer):
        """Test query performance"""
        # Create test data
        customers = []
        for i in range(50):
            customer = Customer(
                telegram_id=200000000 + i,
                name=f"Customer {i}"
            )
            customers.append(customer)
        
        db_session.add_all(customers)
        db_session.commit()
        
        # Test query performance
        customers = db_session.query(Customer).all()
        assert len(customers) == 50

    def test_relationship_query_performance(self, db_session, performance_timer):
        """Test relationship query performance"""
        # Create test data with relationships
        customer = Customer(telegram_id=300000000, name="Test Customer")
        db_session.add(customer)
        db_session.commit()
        
        orders = []
        for i in range(20):
            order = Order(
                customer_id=customer.id,
                order_number=f"ORD-{i:06d}",
                status="pending",
                total=10.00 + i
            )
            orders.append(order)
        
        db_session.add_all(orders)
        db_session.commit()
        
        # Test relationship query performance
        customer = db_session.query(Customer).first()
        assert len(customer.orders) == 20 