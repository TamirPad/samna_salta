"""
Tests for database operations module
"""

import pytest
import time
from unittest.mock import MagicMock, patch, Mock
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from datetime import datetime

from src.db.operations import (
    init_db,
    init_default_products,
    get_or_create_customer,
    get_customer_by_telegram_id,
    get_all_products,
    get_product_by_id,
    create_product,
    update_product,
    delete_product,
    get_product_categories,
    get_products_by_category,
    add_to_cart,
    get_cart_items,
    clear_cart,
    remove_from_cart,
    create_order,
    update_order_status,
    get_all_customers,
    get_all_orders,
    check_database_connection,
    get_database_status,
    get_db_manager,
    get_db_session
)
from src.db.models import Customer, Product, Cart, CartItem, Order, OrderItem, MenuCategory


class TestDatabaseInitialization:
    """Test database initialization functions"""

    def test_init_db_success(self, db_session, patch_config):
        """Test successful database initialization"""
        with patch("src.db.operations.get_db_session", return_value=db_session):
            result = init_db()
            assert result is None  # Function doesn't return a value

    def test_init_db_failure(self, db_session, patch_config):
        """Test database initialization failure"""
        with patch("src.db.operations.get_db_session", side_effect=Exception("DB Error")):
            with pytest.raises(Exception, match="DB Error"):
                init_db()

    def test_init_default_products_success(self, db_session, patch_config):
        """Test successful default products initialization"""
        with patch("src.db.operations.get_db_session", return_value=db_session):
            result = init_default_products()
            assert result is None  # Function doesn't return a value

    def test_init_default_products_failure(self, db_session, patch_config):
        """Test default products initialization failure"""
        with patch("src.db.operations.get_db_session", side_effect=Exception("DB Error")):
            with pytest.raises(Exception, match="DB Error"):
                init_default_products()


class TestCustomerOperations:
    """Test customer-related operations"""

    def test_get_or_create_customer_new(self, sample_customer):
        """Test creating a new customer"""
        with patch('src.db.operations.get_db_session') as mock_session:
            mock_session.return_value.query.return_value.filter.return_value.first.return_value = None
            mock_session.return_value.query.return_value.filter.return_value.first.return_value = None  # For phone check
            mock_session.return_value.add = MagicMock()
            mock_session.return_value.commit = MagicMock()
            mock_session.return_value.refresh = MagicMock()
            
            customer = get_or_create_customer(
                telegram_id=123456789,
                full_name="Test User",
                phone_number="+1234567890",
                language="en"
            )
            
            assert customer is not None
            mock_session.return_value.add.assert_called_once()

    def test_get_or_create_customer_existing(self, sample_customer):
        """Test getting existing customer"""
        with patch('src.db.operations.get_db_session') as mock_session:
            mock_session.return_value.query.return_value.filter.return_value.first.return_value = sample_customer
            mock_session.return_value.commit = MagicMock()
            mock_session.return_value.refresh = MagicMock()
            
            customer = get_or_create_customer(
                telegram_id=123456789,
                full_name="Updated Name",
                phone_number="+1234567890",
                language="he"
            )
            
            assert customer is not None
            assert customer.name == "Updated Name"
            assert customer.language == "he"

    def test_get_customer_by_telegram_id_found(self, db_session, sample_customer):
        """Test getting customer by telegram ID - found"""
        db_session.add(sample_customer)
        db_session.commit()
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            customer = get_customer_by_telegram_id(sample_customer.telegram_id)
            
            assert customer is not None
            assert customer.telegram_id == sample_customer.telegram_id
            assert customer.name == sample_customer.name

    def test_get_customer_by_telegram_id_not_found(self, db_session):
        """Test getting customer by telegram ID - not found"""
        with patch("src.db.operations.get_db_session", return_value=db_session):
            customer = get_customer_by_telegram_id(999999999)
            
            assert customer is None


class TestProductOperations:
    """Test product-related operations"""

    def test_get_all_products(self, db_session, sample_products):
        """Test getting all products"""
        db_session.add_all(sample_products)
        db_session.commit()
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            products = get_all_products()
            
            assert len(products) == 3
            assert products[0].name == "Kubaneh"
            assert products[1].name == "Hilbeh"  # Fixed to match actual data
            assert products[2].name == "Za'atar"

    def test_get_product_by_id_found(self, db_session, sample_products):
        """Test getting product by ID - found"""
        db_session.add(sample_products[0])
        db_session.commit()
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            product = get_product_by_id(sample_products[0].id)
            
            assert product is not None
            assert product.id == sample_products[0].id
            assert product.name == "Kubaneh"

    def test_get_product_by_id_not_found(self, db_session):
        """Test getting product by ID - not found"""
        with patch("src.db.operations.get_db_session", return_value=db_session):
            product = get_product_by_id(999)
            
            assert product is None

    def test_create_product_success(self, sample_product_data):
        """Test successful product creation"""
        # Use a unique name to avoid conflicts
        unique_product_data = sample_product_data.copy()
        unique_product_data["name"] = f"Test Product {int(time.time())}"
        
        with patch("src.db.operations.get_db_session") as mock_session:
            mock_session.return_value.query.return_value.filter.return_value.first.return_value = None  # No existing product
            mock_session.return_value.query.return_value.filter.return_value.first.side_effect = [
                None,  # No existing product
                MagicMock(id=1, name="Bread")  # Category exists
            ]
            
            product = create_product(**unique_product_data)
            
            assert product is not None
            mock_session.return_value.add.assert_called_once()
            mock_session.return_value.commit.assert_called_once()

    def test_create_product_failure(self, sample_product_data):
        """Test product creation failure"""
        with patch('src.db.operations.get_db_session') as mock_session:
            mock_session.return_value.query.return_value.filter.return_value.first.return_value = MagicMock()  # Existing product
            mock_session.return_value.rollback = MagicMock()
            
            product = create_product(
                name="Test Product",
                description="Test Description",
                category="Bread",
                price=10.00
            )
            
            assert product is None

    def test_update_product_success(self, db_session, sample_products):
        """Test successful product update"""
        db_session.add_all(sample_products)
        db_session.commit()
        
        # Store the product ID before the session issue
        product_id = sample_products[0].id
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            success = update_product(
                product_id=product_id,
                name="Updated Kubaneh",
                price=30.00
            )
            
            assert success is True
            
            # Get the updated product directly from the session
            updated_product = db_session.query(Product).filter(Product.id == product_id).first()
            assert updated_product.name == "Updated Kubaneh"
            assert updated_product.price == 30.00

    def test_update_product_not_found(self, db_session):
        """Test product update - product not found"""
        with patch("src.db.operations.get_db_session", return_value=db_session):
            success = update_product(product_id=999, name="Updated")
            
            assert success is False

    def test_delete_product_success(self, db_session, sample_products):
        """Test successful product deletion (soft delete)"""
        db_session.add_all(sample_products)
        db_session.commit()
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            success = delete_product(product_id=sample_products[0].id)
            
            assert success is True
            
            # Product should still exist but be inactive (soft delete)
            product = get_product_by_id(sample_products[0].id)
            assert product is not None
            assert product.is_active is False

    def test_delete_product_not_found(self, db_session):
        """Test product deletion - product not found"""
        with patch("src.db.operations.get_db_session", return_value=db_session):
            success = delete_product(999)
            
            assert success is False

    def test_get_product_categories(self, db_session, sample_products):
        """Test getting product categories"""
        # Add categories to the database
        bread_category = MenuCategory(id=1, name="bread", description="Traditional breads")
        spread_category = MenuCategory(id=2, name="spread", description="Spreads and condiments")
        spice_category = MenuCategory(id=3, name="spice", description="Spices and seasonings")
        
        db_session.add_all([bread_category, spread_category, spice_category])
        db_session.add_all(sample_products)
        db_session.commit()
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            categories = get_product_categories()
            
            assert len(categories) == 3
            assert "bread" in categories
            assert "spread" in categories
            assert "spice" in categories

    def test_get_products_by_category(self, db_session, sample_products):
        """Test getting products by category"""
        # Add category to the database
        bread_category = MenuCategory(id=1, name="bread", description="Traditional breads")
        db_session.add(bread_category)
        db_session.add_all(sample_products)
        db_session.commit()
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            bread_products = get_products_by_category("bread")
            
            assert len(bread_products) == 1
            assert bread_products[0].name == "Kubaneh"


class TestCartOperations:
    """Test cart-related operations"""

    def test_add_to_cart_success(self, db_session, sample_customer, sample_products):
        """Test successful cart addition"""
        db_session.add(sample_customer)
        db_session.add_all(sample_products)
        db_session.commit()
        
        with patch("src.db.operations.get_db_manager") as mock_db_manager:
            mock_db_manager.return_value.get_session_context.return_value.__enter__.return_value = db_session
            mock_db_manager.return_value.get_session_context.return_value.__exit__.return_value = None
            
            success = add_to_cart(
                telegram_id=sample_customer.telegram_id,
                product_id=sample_products[0].id,
                quantity=2
            )
            
            assert success is True
            
            # Get cart items using the session context manager
            with patch("src.db.operations.get_db_manager") as mock_db_manager:
                mock_db_manager.return_value.get_session_context.return_value.__enter__.return_value = db_session
                mock_db_manager.return_value.get_session_context.return_value.__exit__.return_value = None
                
                items = get_cart_items(sample_customer.telegram_id)
                assert len(items) == 1
                assert items[0]["quantity"] == 2

    def test_add_to_cart_customer_not_found(self, db_session, sample_products):
        """Test add to cart - customer not found"""
        db_session.add(sample_products[0])
        db_session.commit()
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            success = add_to_cart(
                telegram_id=999999999,
                product_id=sample_products[0].id,
                quantity=1
            )
            
            assert success is False

    def test_add_to_cart_product_not_found(self, db_session, sample_customer):
        """Test add to cart - product not found"""
        db_session.add(sample_customer)
        db_session.commit()
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            success = add_to_cart(
                telegram_id=sample_customer.telegram_id,
                product_id=999,
                quantity=1
            )
            
            assert success is False

    def test_get_cart_items(self, db_session, sample_customer, sample_cart, sample_cart_items):
        """Test getting cart items"""
        # Clear any existing carts first to avoid unique constraint issues
        db_session.query(Cart).delete()
        db_session.query(CartItem).delete()
        db_session.query(Product).delete()
        
        # Set up the cart properly with unique is_active value
        sample_cart.is_active = True
        db_session.add(sample_customer)
        db_session.add(sample_cart)
        
        # Add products first (needed for the JOIN in get_cart_items)
        products = [
            Product(id=1, name="Kubaneh", description="Traditional Yemenite bread", category_id=1, price=25.00),
            Product(id=2, name="Hilbeh", description="Fenugreek spread", category_id=2, price=15.00)
        ]
        db_session.add_all(products)
        
        # Update cart items to reference the products
        sample_cart_items[0].product_id = 1
        sample_cart_items[1].product_id = 2
        
        db_session.add_all(sample_cart_items)
        db_session.commit()
        
        with patch("src.db.operations.get_db_manager") as mock_db_manager:
            mock_db_manager.return_value.get_session_context.return_value.__enter__.return_value = db_session
            mock_db_manager.return_value.get_session_context.return_value.__exit__.return_value = None
            
            items = get_cart_items(sample_customer.telegram_id)
            
            assert len(items) == 2
            assert items[0]["product_id"] == sample_cart_items[0].product_id
            assert items[1]["product_id"] == sample_cart_items[1].product_id

    def test_get_cart_items_empty_cart(self, db_session, sample_customer):
        """Test getting cart items from empty cart"""
        db_session.add(sample_customer)
        db_session.commit()
        
        with patch("src.db.operations.get_db_manager") as mock_db_manager:
            mock_db_manager.return_value.get_session_context.return_value.__enter__.return_value = db_session
            mock_db_manager.return_value.get_session_context.return_value.__exit__.return_value = None
            
            items = get_cart_items(sample_customer.telegram_id)
            
            assert len(items) == 0

    def test_clear_cart_success(self, db_session, sample_customer, sample_cart, sample_cart_items):
        """Test successful cart clearing"""
        db_session.add(sample_customer)
        db_session.add(sample_cart)
        db_session.add_all(sample_cart_items)
        db_session.commit()
        
        # Store the telegram_id before the session is closed
        telegram_id = sample_customer.telegram_id
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            success = clear_cart(telegram_id=telegram_id)
            
            assert success is True
            
            # Get cart items using the session context manager
            with patch("src.db.operations.get_db_manager") as mock_db_manager:
                mock_db_manager.return_value.get_session_context.return_value.__enter__.return_value = db_session
                mock_db_manager.return_value.get_session_context.return_value.__exit__.return_value = None
                
                items = get_cart_items(telegram_id)
                assert len(items) == 0

    def test_remove_from_cart_success(self, db_session, sample_customer, sample_cart, sample_cart_items, sample_products):
        """Test successful item removal from cart"""
        # Add all required data to the database
        db_session.add(sample_customer)
        db_session.add_all(sample_products)  # Add products first
        db_session.add(sample_cart)
        db_session.add_all(sample_cart_items)
        db_session.commit()
        
        # Store the telegram_id and product_id before the session is closed
        telegram_id = sample_customer.telegram_id
        product_id = sample_cart_items[0].product_id
        
        # Use get_db_session patching for remove_from_cart
        with patch("src.db.operations.get_db_session", return_value=db_session):
            success = remove_from_cart(
                telegram_id=telegram_id,
                product_id=product_id
            )
            
            assert success is True
        
        # Use get_db_manager patching for get_cart_items
        with patch("src.db.operations.get_db_manager") as mock_db_manager:
            mock_db_manager.return_value.get_session_context.return_value.__enter__.return_value = db_session
            mock_db_manager.return_value.get_session_context.return_value.__exit__.return_value = None
            
            items = get_cart_items(telegram_id)
            assert len(items) == 1  # Should have one item remaining


class TestOrderOperations:
    """Test order-related operations"""

    def test_create_order_success(self, sample_customer):
        """Test successful order creation"""
        with patch('src.db.operations.get_db_manager') as mock_manager:
            mock_session = MagicMock()
            mock_manager.return_value.get_session_context.return_value.__enter__.return_value = mock_session
            mock_session.add = MagicMock()
            mock_session.commit = MagicMock()
            mock_session.refresh = MagicMock()
            
            order = create_order(
                customer_id=sample_customer.id,
                total_amount=25.00,
                delivery_method="pickup"
            )
            
            assert order is not None
            mock_session.add.assert_called_once()

    def test_update_order_status_success(self, db_session, sample_customer, sample_order):
        """Test successful order status update"""
        db_session.add(sample_customer)
        db_session.add(sample_order)
        db_session.commit()
        
        with patch("src.db.operations.get_db_manager") as mock_db_manager:
            mock_db_manager.return_value.get_session_context.return_value.__enter__.return_value = db_session
            mock_db_manager.return_value.get_session_context.return_value.__exit__.return_value = None
            
            success = update_order_status(
                order_id=sample_order.id,
                new_status="completed"
            )
            
            assert success is True
            
            # Verify status update
            db_session.refresh(sample_order)
            assert sample_order.status == "completed"

    def test_update_order_status_not_found(self, db_session):
        """Test order status update - order not found"""
        with patch("src.db.operations.get_db_session", return_value=db_session):
            success = update_order_status(order_id=999, new_status="completed")
            
            assert success is False

    def test_get_all_orders(self, db_session, sample_customer, sample_order):
        """Test getting all orders"""
        db_session.add(sample_customer)
        db_session.add(sample_order)
        db_session.commit()
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            orders = get_all_orders()
            
            assert len(orders) == 1
            assert orders[0].order_number == "ORD-000001"
            assert orders[0].status == "pending"

    def test_get_all_customers(self, db_session, sample_customer, sample_admin_customer):
        """Test getting all customers"""
        db_session.add(sample_customer)
        db_session.add(sample_admin_customer)
        db_session.commit()
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            customers = get_all_customers()
            
            assert len(customers) == 2
            assert customers[0].name == "Test Customer"  # Fixed to match actual data
            assert customers[1].name == "Admin User"


class TestDatabaseConnection:
    """Test database connection functions"""

    def test_check_database_connection_success(self, db_session):
        """Test successful database connection check"""
        with patch("src.db.operations.get_db_session", return_value=db_session):
            result = check_database_connection()
            
            assert result is True

    def test_check_database_connection_failure(self):
        """Test database connection check failure"""
        with patch("src.db.operations.get_db_manager") as mock_db_manager:
            mock_engine = MagicMock()
            mock_engine.connect.side_effect = Exception("Connection failed")
            mock_db_manager.return_value.get_engine.return_value = mock_engine
            
            result = check_database_connection()
            
            assert result is False

    def test_get_database_status(self, db_session):
        """Test getting database status"""
        with patch("src.db.operations.get_db_session", return_value=db_session):
            status = get_database_status()
            
            assert isinstance(status, dict)
            assert "connected" in status  # Fixed to match actual return format
            assert "database_type" in status


class TestDatabaseErrorHandling:
    """Test database error handling"""

    def test_operational_error_handling(self, sample_product_data):
        """Test handling of operational errors"""
        with patch("src.db.operations.get_db_session", side_effect=OperationalError("Connection lost", None, None)):
            from src.utils.error_handler import DatabaseRetryExhaustedError
            with pytest.raises(DatabaseRetryExhaustedError):
                create_product(**sample_product_data)

    def test_sqlalchemy_error_handling(self, sample_product_data):
        """Test handling of SQLAlchemy errors"""
        with patch("src.db.operations.get_db_session", side_effect=SQLAlchemyError("Database error")):
            from src.utils.error_handler import DatabaseOperationError
            with pytest.raises(DatabaseOperationError):
                create_product(**sample_product_data)

    def test_general_exception_handling(self, sample_product_data):
        """Test handling of general exceptions"""
        with patch("src.db.operations.get_db_session", side_effect=Exception("Unexpected error")):
            with pytest.raises(Exception, match="Unexpected error"):
                create_product(**sample_product_data)


class TestDatabasePerformance:
    """Test database performance"""

    def test_bulk_operations_performance(self, db_session, performance_timer):
        """Test bulk operations performance"""
        # Create test data
        customers = []
        for i in range(100):
            customer = Customer(
                telegram_id=400000000 + i,
                name=f"Customer {i}"
            )
            customers.append(customer)
        
        db_session.add_all(customers)
        db_session.commit()
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            # Test bulk query performance
            all_customers = get_all_customers()
            assert len(all_customers) == 100

    def test_complex_query_performance(self, db_session, performance_timer):
        """Test complex query performance"""
        # Create test data with relationships
        customer = Customer(telegram_id=500000000, name="Test Customer")
        db_session.add(customer)
        
        # Add categories
        categories = []
        for i in range(5):
            category = MenuCategory(
                id=i+1,
                name=f"category_{i}",
                description=f"Category {i}",
                is_active=True
            )
            categories.append(category)
        
        db_session.add_all(categories)
        db_session.commit()
        
        products = []
        for i in range(20):
            product = Product(
                name=f"Product {i}",
                description=f"Description {i}",
                category_id=(i % 5) + 1,  # Assign to categories
                price=10.00 + i
            )
            products.append(product)
        
        db_session.add_all(products)
        db_session.commit()
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            # Test complex query performance
            all_products = get_all_products()
            categories_result = get_product_categories()
            
            assert len(all_products) == 20
            assert len(categories_result) == 5


class TestDatabaseIntegration:
    """Integration tests for database operations"""

    def test_full_order_workflow(self, db_session, sample_customer, sample_products):
        """Test complete order workflow"""
        db_session.add(sample_customer)
        db_session.add(sample_products[0])
        db_session.commit()
        
        with patch("src.db.operations.get_db_manager") as mock_db_manager:
            mock_db_manager.return_value.get_session_context.return_value.__enter__.return_value = db_session
            mock_db_manager.return_value.get_session_context.return_value.__exit__.return_value = None
            
            # Create order with unique order number
            order = create_order(
                customer_id=sample_customer.id,
                total_amount=25.00,
                delivery_method="pickup"
            )
            
            assert order is not None
            assert order.customer_id == sample_customer.id
            assert order.delivery_method == "pickup"

    def test_customer_product_workflow(self, db_session, sample_customer, sample_products):
        """Test customer and product workflow"""
        db_session.add(sample_customer)
        db_session.add(sample_products[0])
        db_session.commit()
        
        with patch("src.db.operations.get_db_session", return_value=db_session):
            # Get or create customer
            customer = get_or_create_customer(
                telegram_id=123456789,
                full_name="Test User",
                phone_number="+1234567890",
                language="en"
            )
            
            assert customer is not None
            assert customer.telegram_id == 123456789 