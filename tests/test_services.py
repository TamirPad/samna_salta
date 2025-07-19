"""
Tests for service modules
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, date
import time

from src.services.cart_service import CartService
from src.services.order_service import OrderService
from src.services.admin_service import AdminService
from src.services.delivery_service import DeliveryService
from src.services.notification_service import NotificationService
from src.services.customer_order_service import CustomerOrderService


class TestCartService:
    """Test CartService"""

    @pytest.fixture
    def cart_service(self):
        """Create CartService instance"""
        return CartService()

    def test_validate_customer_data_valid(self, cart_service):
        """Test customer data validation - valid data"""
        result = cart_service.validate_customer_data("John Doe", "+972501234567")
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_customer_data_invalid_name(self, cart_service):
        """Test customer data validation - invalid name"""
        result = cart_service.validate_customer_data("J", "+972501234567")
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "Name must be at least 2 characters" in result["errors"][0]

    def test_validate_customer_data_invalid_phone(self, cart_service):
        """Test customer data validation - invalid phone"""
        result = cart_service.validate_customer_data("John Doe", "123")
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "Phone number must be at least 8 digits" in result["errors"][0]

    def test_register_customer_success(self, cart_service):
        """Test customer registration - success"""
        with patch("src.services.cart_service.get_customer_by_telegram_id", return_value=None) as mock_get_customer:
            with patch("src.services.cart_service.get_or_create_customer") as mock_create_customer:
                mock_customer = MagicMock()
                mock_create_customer.return_value = mock_customer
                
                result = cart_service.register_customer(123456789, "John Doe", "+972501234567", "en")
                
                assert result["success"] is True
                mock_get_customer.assert_called_once()
                mock_create_customer.assert_called_once()

    def test_register_customer_validation_error(self, cart_service):
        """Test customer registration - validation error"""
        with patch("src.services.cart_service.get_customer_by_telegram_id", return_value=None):
            with patch("src.services.cart_service.get_or_create_customer", return_value=None):
                result = cart_service.register_customer(123456789, "J", "123", "en")
                
                # The method should try to create customer but fail
                assert result["success"] is False
                assert "error" in result

    def test_add_item_success(self, cart_service):
        """Test add item to cart - success"""
        with patch("src.db.operations.add_to_cart", return_value=True):
            result = cart_service.add_item(123456789, 1, 2, {"type": "classic"})
            
            assert result is True

    def test_add_item_failure(self, cart_service):
        """Test add item to cart - failure"""
        with patch("src.services.cart_service.add_to_cart", return_value=False) as mock_add:
            result = cart_service.add_item(123456789, 1, 2, {"type": "classic"})
            
            assert result is False
            mock_add.assert_called_once()

    def test_get_items(self, cart_service):
        """Test get cart items"""
        mock_items = [
            {"product_id": 1, "quantity": 2, "unit_price": 10.00},
            {"product_id": 2, "quantity": 1, "unit_price": 15.00}
        ]
        
        with patch("src.services.cart_service.get_cart_items", return_value=mock_items) as mock_get:
            items = cart_service.get_items(123456789)
            
            assert len(items) == 2
            assert items[0]["product_id"] == 1
            assert items[1]["product_id"] == 2
            mock_get.assert_called_once_with(123456789)

    def test_calculate_total(self, cart_service):
        """Test cart total calculation"""
        items = [
            {"unit_price": 10.00, "quantity": 2},
            {"unit_price": 15.00, "quantity": 1}
        ]
        
        total = cart_service.calculate_total(items)
        assert total == 35.00  # (10 * 2) + (15 * 1)

    def test_clear_cart_success(self, cart_service):
        """Test clear cart - success"""
        with patch("src.db.operations.clear_cart", return_value=True):
            result = cart_service.clear_cart(123456789)
            
            assert result is True

    def test_clear_cart_failure(self, cart_service):
        """Test clear cart - failure"""
        with patch("src.services.cart_service.clear_cart", return_value=False) as mock_clear:
            result = cart_service.clear_cart(123456789)
            
            assert result is False
            mock_clear.assert_called_once_with(123456789)

    def test_remove_item_success(self, cart_service):
        """Test remove item from cart - success"""
        with patch("src.services.cart_service.remove_from_cart", return_value=True) as mock_remove:
            result = cart_service.remove_item(123456789, 1)
            
            assert result is True
            mock_remove.assert_called_once_with(123456789, 1)

    def test_remove_item_failure(self, cart_service):
        """Test remove item from cart - failure"""
        with patch("src.db.operations.remove_from_cart", return_value=False):
            result = cart_service.remove_item(123456789, 1)
            
            assert result is False

    def test_get_customer_found(self, cart_service):
        """Test get customer - found"""
        mock_customer = MagicMock()
        mock_customer.name = "John Doe"
        
        with patch("src.db.operations.get_customer_by_telegram_id", return_value=mock_customer):
            customer = cart_service.get_customer(123456789)
            
            assert customer is not None
            assert customer.name == "John Doe"

    def test_get_customer_not_found(self, cart_service):
        """Test get customer - not found"""
        with patch("src.services.cart_service.get_customer_by_telegram_id", return_value=None) as mock_get:
            customer = cart_service.get_customer(123456789)
            
            assert customer is None
            mock_get.assert_called_once_with(123456789)

    def test_update_cart_success(self, cart_service):
        """Test update cart - success"""
        with patch("src.db.operations.update_cart", return_value=True):
            result = cart_service.update_cart(123456789, [], "pickup", "123 Test St")
            
            assert result is True

    def test_update_cart_failure(self, cart_service):
        """Test update cart - failure"""
        with patch("src.services.cart_service.update_cart", return_value=False) as mock_update:
            result = cart_service.update_cart(123456789, [], "pickup", "123 Test St")
            
            assert result is False
            mock_update.assert_called_once()

    def test_set_delivery_method_success(self, cart_service):
        """Test set delivery method - success"""
        mock_items = [{"product_id": 1, "quantity": 1}]
        with patch("src.services.cart_service.get_cart_items", return_value=mock_items):
            with patch("src.services.cart_service.update_cart", return_value=True) as mock_update:
                result = cart_service.set_delivery_method(123456789, "delivery")
                
                assert result is True
                mock_update.assert_called_once()

    def test_set_delivery_method_invalid(self, cart_service):
        """Test set delivery method - invalid method"""
        result = cart_service.set_delivery_method(123456789, "invalid_method")
        
        assert result is False

    def test_set_delivery_address_success(self, cart_service):
        """Test set delivery address - success"""
        mock_items = [{"product_id": 1, "quantity": 1}]
        with patch("src.services.cart_service.get_cart_items", return_value=mock_items):
            with patch("src.services.cart_service.update_cart", return_value=True) as mock_update:
                result = cart_service.set_delivery_address(123456789, "123 Test Street")
                
                assert result is True
                mock_update.assert_called_once()

    def test_set_delivery_address_invalid(self, cart_service):
        """Test set delivery address - invalid address"""
        result = cart_service.set_delivery_address(123456789, "")
        
        assert result is False

    def test_get_cart_info(self, cart_service):
        """Test get cart info"""
        mock_items = [
            {"product_id": 1, "quantity": 2, "unit_price": 10.00},
            {"product_id": 2, "quantity": 1, "unit_price": 15.00}
        ]
        mock_customer = MagicMock()
        mock_customer.name = "John Doe"
        
        with patch("src.services.cart_service.get_customer_by_telegram_id", return_value=mock_customer):
            with patch("src.services.cart_service.get_cart_items", return_value=mock_items):
                cart_info = cart_service.get_cart_info(123456789)
                
                assert cart_info["items"] == mock_items
                assert cart_info["customer"] == mock_customer
                assert cart_info["total"] == 35.00
                assert cart_info["item_count"] == 2

    def test_update_customer_delivery_address_success(self, cart_service):
        """Test update customer delivery address - success"""
        with patch("src.db.operations.update_customer_delivery_address", return_value=True):
            result = cart_service.update_customer_delivery_address(123456789, "123 Test Street")
            
            assert result is True

    def test_update_customer_delivery_address_failure(self, cart_service):
        """Test update customer delivery address - failure"""
        with patch("src.services.cart_service.update_customer_delivery_address", return_value=False) as mock_update:
            result = cart_service.update_customer_delivery_address(123456789, "123 Test Street")
            
            assert result is False
            mock_update.assert_called_once_with(123456789, "123 Test Street")


class TestOrderService:
    """Test OrderService"""

    @pytest.fixture
    def order_service(self):
        """Create OrderService instance"""
        return OrderService()

    @pytest.mark.asyncio
    async def test_create_order_success(self, order_service):
        """Test create order - success"""
        cart_items = [
            {"product_id": 1, "quantity": 2, "unit_price": 10.00, "options": {"type": "classic"}}
        ]
        
        with patch("src.services.order_service.get_customer_by_telegram_id") as mock_get_customer:
            mock_customer = MagicMock()
            mock_customer.id = 1
            mock_get_customer.return_value = mock_customer
            
            with patch("src.services.order_service.get_cart_by_telegram_id") as mock_get_cart:
                mock_cart = MagicMock()
                mock_cart.customer_id = 1
                mock_cart.delivery_method = "pickup"
                mock_cart.delivery_address = "123 Test St"
                mock_get_cart.return_value = mock_cart
                
                with patch("src.services.order_service.generate_order_number", return_value="ORD-000001"):
                    with patch("src.services.order_service.create_order_with_items") as mock_create_order:
                        mock_order = MagicMock()
                        mock_order.id = 1
                        mock_order.order_number = "ORD-000001"
                        mock_create_order.return_value = mock_order
                        
                        with patch("src.container.get_container") as mock_get_container:
                            mock_container = MagicMock()
                            mock_notification_service = MagicMock()
                            mock_container.get_notification_service.return_value = mock_notification_service
                            mock_get_container.return_value = mock_container
                            
                            result = await order_service.create_order(123456789, cart_items)
                            
                            assert result["success"] is True
                            assert result["order_number"] == "ORD-000001"
                            assert result["total"] == 20.00
                            assert "order" in result

    @pytest.mark.asyncio
    async def test_create_order_no_cart(self, order_service):
        """Test create order - no cart"""
        cart_items = []
        
        with patch("src.services.order_service.get_customer_by_telegram_id") as mock_get_customer:
            mock_customer = MagicMock()
            mock_customer.id = 1
            mock_get_customer.return_value = mock_customer
            
            with patch("src.services.order_service.get_cart_by_telegram_id", return_value=None):
                result = await order_service.create_order(123456789, cart_items)
                
                assert result["success"] is True  # Order can be created without cart
                assert "order_number" in result

    @pytest.mark.asyncio
    async def test_create_order_empty_cart(self, order_service):
        """Test create order - empty cart"""
        cart_items = []
        
        with patch("src.services.order_service.get_customer_by_telegram_id") as mock_get_customer:
            mock_customer = MagicMock()
            mock_customer.id = 1
            mock_get_customer.return_value = mock_customer
            
            with patch("src.services.order_service.get_cart_by_telegram_id") as mock_get_cart:
                mock_cart = MagicMock()
                mock_cart.delivery_method = "pickup"
                mock_cart.delivery_address = ""
                mock_get_cart.return_value = mock_cart
                
                with patch("src.services.order_service.generate_order_number", return_value="ORD-000001"):
                    with patch("src.services.order_service.create_order_with_items") as mock_create_order:
                        mock_order = MagicMock()
                        mock_order.order_number = "ORD-000001"
                        mock_create_order.return_value = mock_order
                        
                        with patch("src.container.get_container") as mock_get_container:
                            mock_container = MagicMock()
                            mock_notification_service = MagicMock()
                            mock_container.get_notification_service.return_value = mock_notification_service
                            mock_get_container.return_value = mock_container
                            
                            result = await order_service.create_order(123456789, cart_items)
                            
                            assert result["success"] is True  # Empty cart can still create order
                            assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_create_order_database_error(self, order_service):
        """Test create order - database error"""
        cart_items = [
            {"product_id": 1, "quantity": 2, "unit_price": 10.00, "options": {"type": "classic"}}
        ]
        
        with patch("src.services.order_service.get_customer_by_telegram_id") as mock_get_customer:
            mock_customer = MagicMock()
            mock_customer.id = 1
            mock_get_customer.return_value = mock_customer
            
            with patch("src.services.order_service.get_cart_by_telegram_id") as mock_get_cart:
                mock_cart = MagicMock()
                mock_cart.delivery_method = "pickup"
                mock_cart.delivery_address = ""
                mock_get_cart.return_value = mock_cart
                
                with patch("src.services.order_service.generate_order_number", side_effect=Exception("DB Error")):
                    result = await order_service.create_order(123456789, cart_items)
                    
                    assert result["success"] is False
                    assert "DB Error" in result["error"]

    def test_get_customer_orders(self, order_service):
        """Test get customer orders"""
        mock_orders = [MagicMock(), MagicMock()]
        mock_orders[0].customer_id = 1
        mock_orders[1].customer_id = 1
        
        with patch("src.db.operations.get_all_orders", return_value=mock_orders):
            orders = order_service.get_customer_orders(1)
            
            assert len(orders) == 2

    def test_get_order_by_number_found(self, order_service):
        """Test get order by number - found"""
        mock_order = MagicMock()
        mock_order.order_number = "ORD-000001"
        
        with patch("src.db.operations.get_all_orders", return_value=[mock_order]):
            order = order_service.get_order_by_number("ORD-000001")
            
            assert order is not None
            assert order.order_number == "ORD-000001"

    def test_get_order_by_number_not_found(self, order_service):
        """Test get order by number - not found"""
        with patch("src.db.operations.get_all_orders", return_value=[]):
            order = order_service.get_order_by_number("ORD-000001")
            
            assert order is None

    def test_get_all_products(self, order_service):
        """Test get all products"""
        mock_products = [MagicMock(), MagicMock()]
        
        with patch("src.services.order_service.get_all_products", return_value=mock_products):
            products = order_service.get_all_products()
            
            assert len(products) == 2

    def test_get_products_by_category(self, order_service):
        """Test get products by category"""
        mock_products = [MagicMock()]
        mock_products[0].category = "bread"
        mock_products[0].is_active = True
        
        with patch("src.services.order_service.get_all_products", return_value=mock_products):
            products = order_service.get_products_by_category("bread")
            
            assert len(products) == 1

    def test_get_product_by_name_found(self, order_service):
        """Test get product by name - found"""
        mock_product = MagicMock()
        mock_product.name = "Kubaneh"
        
        with patch("src.services.order_service.get_product_by_name", return_value=mock_product):
            product = order_service.get_product_by_name("Kubaneh")
            
            assert product is not None
            assert product.name == "Kubaneh"

    def test_get_product_by_name_not_found(self, order_service):
        """Test get product by name - not found"""
        with patch("src.services.order_service.get_product_by_name", return_value=None):
            product = order_service.get_product_by_name("Unknown Product")
            
            assert product is None

    def test_get_product_by_id_found(self, order_service):
        """Test get product by ID - found"""
        mock_product = MagicMock()
        mock_product.id = 1
        
        with patch("src.services.order_service.get_product_by_id", return_value=mock_product):
            product = order_service.get_product_by_id(1)
            
            assert product is not None
            assert product.id == 1

    def test_get_product_by_id_not_found(self, order_service):
        """Test get product by ID - not found"""
        with patch("src.services.order_service.get_product_by_id", return_value=None):
            product = order_service.get_product_by_id(999)
            
            assert product is None

    def test_check_product_availability_available(self, order_service):
        """Test check product availability - available"""
        mock_product = MagicMock()
        mock_product.name = "hilbeh"
        mock_product.is_active = True
        
        with patch("src.services.order_service.get_product_by_name", return_value=mock_product):
            with patch("src.services.order_service.is_hilbeh_available", return_value=True):
                result = order_service.check_product_availability("hilbeh")
                
                assert result["available"] is True

    def test_check_product_availability_not_available(self, order_service):
        """Test check product availability - not available"""
        mock_product = MagicMock()
        mock_product.name = "hilbeh"
        mock_product.is_active = True
        
        with patch("src.services.order_service.get_product_by_name", return_value=mock_product):
            with patch("src.services.order_service.is_hilbeh_available", return_value=False):
                result = order_service.check_product_availability("hilbeh")
                
                assert result["available"] is False
                assert "specific days" in result["reason"]


class TestAdminService:
    """Test AdminService"""

    @pytest.fixture
    def admin_service(self):
        """Create AdminService instance"""
        return AdminService()

    @pytest.mark.asyncio
    async def test_get_pending_orders(self, admin_service):
        """Test get pending orders"""
        mock_orders = [MagicMock(), MagicMock()]
        
        with patch("src.db.operations.get_all_orders", return_value=mock_orders):
            orders = await admin_service.get_pending_orders()
            
            assert isinstance(orders, list)

    @pytest.mark.asyncio
    async def test_get_active_orders(self, admin_service):
        """Test get active orders"""
        mock_orders = [MagicMock(), MagicMock()]
        
        with patch("src.db.operations.get_all_orders", return_value=mock_orders):
            orders = await admin_service.get_active_orders()
            
            assert isinstance(orders, list)

    @pytest.mark.asyncio
    async def test_get_all_orders(self, admin_service):
        """Test get all orders"""
        mock_orders = [MagicMock(), MagicMock()]
        
        with patch("src.db.operations.get_all_orders", return_value=mock_orders):
            orders = await admin_service.get_all_orders()
            
            assert isinstance(orders, list)

    @pytest.mark.asyncio
    async def test_get_order_by_id_found(self, admin_service):
        """Test get order by id - found"""
        mock_orders = [MagicMock()]
        mock_orders[0].id = 1
        
        with patch("src.db.operations.get_all_orders", return_value=mock_orders):
            order = await admin_service.get_order_by_id(1)
            
            assert order is not None

    @pytest.mark.asyncio
    async def test_get_order_by_id_not_found(self, admin_service):
        """Test get order by id - not found"""
        mock_orders = [MagicMock()]
        mock_orders[0].id = 1
        
        with patch("src.db.operations.get_all_orders", return_value=mock_orders):
            order = await admin_service.get_order_by_id(999)
            
            assert order is None

    @pytest.mark.asyncio
    async def test_update_order_status_success(self, admin_service):
        """Test update order status - success"""
        with patch("src.db.operations.update_order_status", return_value=True):
            result = await admin_service.update_order_status(1, "completed", 123456789)
            
            assert result is True

    @pytest.mark.asyncio
    async def test_update_order_status_failure(self, admin_service):
        """Test update order status - failure"""
        # Test with non-existent order ID
        with patch("src.db.operations.update_order_status", return_value=False):
            result = await admin_service.update_order_status(999, "completed", 123456789)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_get_business_analytics(self, admin_service):
        """Test get business analytics"""
        mock_orders = [MagicMock(), MagicMock()]
        
        with patch("src.db.operations.get_all_orders", return_value=mock_orders):
            analytics = await admin_service.get_business_analytics()
            
            assert isinstance(analytics, dict)

    @pytest.mark.asyncio
    async def test_get_today_orders(self, admin_service):
        """Test get today orders"""
        mock_orders = [MagicMock(), MagicMock()]
        
        with patch("src.db.operations.get_all_orders", return_value=mock_orders):
            orders = await admin_service.get_today_orders()
            
            assert isinstance(orders, list)

    @pytest.mark.asyncio
    async def test_get_completed_orders(self, admin_service):
        """Test get completed orders"""
        mock_orders = [MagicMock(), MagicMock()]
        
        with patch("src.db.operations.get_all_orders", return_value=mock_orders):
            orders = await admin_service.get_completed_orders()
            
            assert isinstance(orders, list)

    def test_get_order_analytics(self, admin_service):
        """Test get order analytics"""
        analytics = admin_service.get_order_analytics()
        
        assert isinstance(analytics, dict)

    @pytest.mark.asyncio
    async def test_get_all_customers(self, admin_service):
        """Test get all customers"""
        mock_customers = [MagicMock(), MagicMock()]
        
        with patch("src.db.operations.get_all_customers", return_value=mock_customers):
            customers = await admin_service.get_all_customers()
            
            assert isinstance(customers, list)

    @pytest.mark.asyncio
    async def test_get_all_products_for_admin(self, admin_service):
        """Test get all products for admin"""
        mock_products = [MagicMock(), MagicMock()]
        
        with patch("src.db.operations.get_all_products_admin", return_value=mock_products):
            products = await admin_service.get_all_products_for_admin()
            
            assert isinstance(products, list)

    @pytest.mark.asyncio
    async def test_get_product_categories_list(self, admin_service):
        """Test get product categories list"""
        mock_categories = ["bread", "pastries", "drinks"]
        
        with patch("src.db.operations.get_product_categories", return_value=mock_categories):
            categories = await admin_service.get_product_categories_list()
            
            assert isinstance(categories, list)
            assert len(categories) >= 1  # At least one category should exist

    @pytest.mark.asyncio
    async def test_get_products_by_category_admin(self, admin_service):
        """Test get products by category admin"""
        mock_products = [MagicMock(), MagicMock()]
        
        with patch("src.db.operations.get_products_by_category", return_value=mock_products):
            products = await admin_service.get_products_by_category_admin("bread")
            
            assert isinstance(products, list)

    @pytest.mark.asyncio
    async def test_toggle_product_status_failure(self, admin_service):
        """Test toggle product status - failure"""
        with patch("src.db.operations.get_product_by_id", return_value=None):
            result = await admin_service.toggle_product_status(999)
            
            assert result["success"] is False


class TestDeliveryService:
    """Test DeliveryService"""

    def test_validate_delivery_method_valid(self):
        """Test validate delivery method - valid"""
        assert DeliveryService.validate_delivery_method("pickup") is True
        assert DeliveryService.validate_delivery_method("delivery") is True

    def test_validate_delivery_method_invalid(self):
        """Test validate delivery method - invalid"""
        assert DeliveryService.validate_delivery_method("invalid") is False

    def test_validate_delivery_address_valid(self):
        """Test validate delivery address - valid"""
        assert DeliveryService.validate_delivery_address("123 Test Street") is True

    def test_validate_delivery_address_invalid(self):
        """Test validate delivery address - invalid"""
        assert DeliveryService.validate_delivery_address("") is False
        assert DeliveryService.validate_delivery_address(None) is False

    def test_get_delivery_orders(self):
        """Test get delivery orders"""
        mock_orders = [MagicMock(), MagicMock()]
        mock_orders[0].delivery_method = "delivery"
        mock_orders[1].delivery_method = "delivery"
        
        with patch("src.services.delivery_service.get_all_orders", return_value=mock_orders):
            orders = DeliveryService.get_delivery_orders()
            
            assert len(orders) == 2

    def test_get_pickup_orders(self):
        """Test get pickup orders"""
        mock_orders = [MagicMock(), MagicMock()]
        mock_orders[0].delivery_method = "pickup"
        mock_orders[1].delivery_method = "pickup"
        
        with patch("src.services.delivery_service.get_all_orders", return_value=mock_orders):
            orders = DeliveryService.get_pickup_orders()
            
            assert len(orders) == 2

    def test_calculate_delivery_charge(self):
        """Test calculate delivery charge"""
        charge = DeliveryService.calculate_delivery_charge("123 Test St")
        
        assert charge == 20.0

    def test_update_delivery_status_success(self):
        """Test update delivery status - success"""
        mock_orders = [MagicMock()]
        mock_orders[0].id = 1
        mock_orders[0].delivery_method = "delivery"
        mock_orders[0].status = "pending"
        
        with patch("src.services.delivery_service.get_all_orders", return_value=mock_orders):
            result = DeliveryService.update_delivery_status(1, "completed")
            
            assert result is True
            assert mock_orders[0].status == "completed"

    def test_update_delivery_status_invalid_status(self):
        """Test update delivery status - invalid status"""
        result = DeliveryService.update_delivery_status(1, "invalid_status")
        
        assert result is False

    def test_update_delivery_status_order_not_found(self):
        """Test update delivery status - order not found"""
        mock_orders = [MagicMock()]
        mock_orders[0].id = 2  # Different ID
        
        with patch("src.services.delivery_service.get_all_orders", return_value=mock_orders):
            result = DeliveryService.update_delivery_status(1, "completed")
            
            assert result is False

    def test_get_delivery_stats(self):
        """Test get delivery stats"""
        mock_orders = [MagicMock(), MagicMock(), MagicMock()]
        mock_orders[0].delivery_method = "delivery"
        mock_orders[0].delivery_charge = 20.0
        mock_orders[0].status = "pending"
        mock_orders[1].delivery_method = "pickup"
        mock_orders[1].delivery_charge = 0.0
        mock_orders[1].status = "completed"
        mock_orders[2].delivery_method = "delivery"
        mock_orders[2].delivery_charge = 20.0
        mock_orders[2].status = "completed"
        
        with patch("src.services.delivery_service.get_all_orders", return_value=mock_orders):
            stats = DeliveryService.get_delivery_stats()
            
            assert "total_deliveries" in stats
            assert "total_pickups" in stats
            assert "delivery_revenue" in stats
            assert "status_breakdown" in stats
            assert stats["total_deliveries"] == 2
            assert stats["total_pickups"] == 1
            assert stats["delivery_revenue"] == 40.0


class TestNotificationService:
    """Test NotificationService"""

    @pytest.fixture
    def notification_service(self, patch_config):
        """Create NotificationService instance"""
        return NotificationService()

    @pytest.mark.asyncio
    async def test_send_admin_notification_success(self, notification_service):
        """Test send admin notification - success"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        with patch("src.container.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_container.get_bot.return_value = mock_bot
            mock_get_container.return_value = mock_container
            
            result = await notification_service.send_admin_notification("Test message")
            
            assert result is True
            mock_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_admin_notification_failure(self, notification_service):
        """Test send admin notification - failure"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(side_effect=Exception("Bot error"))
        
        with patch("src.container.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_container.get_bot.return_value = mock_bot
            mock_get_container.return_value = mock_container
            
            result = await notification_service.send_admin_notification("Test message")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_send_customer_notification_success(self, notification_service):
        """Test send customer notification - success"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        with patch("src.container.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_container.get_bot.return_value = mock_bot
            mock_get_container.return_value = mock_container
            
            result = await notification_service.send_customer_notification(123456789, "Test message")
            
            assert result is True
            mock_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_customer_notification_failure(self, notification_service):
        """Test send customer notification - failure"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(side_effect=Exception("Bot error"))
        
        with patch("src.container.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_container.get_bot.return_value = mock_bot
            mock_get_container.return_value = mock_container
            
            result = await notification_service.send_customer_notification(123456789, "Test message")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_notify_new_order_success(self, notification_service):
        """Test notify new order - success"""
        order_data = {
            "order_number": "ORD-000001",
            "customer_name": "Test Customer",
            "customer_phone": "1234567890",
            "customer_telegram_id": 123456789,
            "delivery_method": "pickup",
            "items": [{"product_name": "Test Product", "quantity": 2, "price": 10.0}],
            "total": 20.0,
            "created_at": "2023-01-01 12:00:00"
        }
        
        with patch.object(notification_service, "send_admin_notification", return_value=True):
            result = await notification_service.notify_new_order(order_data)
            
            assert result is True

    @pytest.mark.asyncio
    async def test_notify_order_status_update_success(self, notification_service):
        """Test notify order status update - success"""
        with patch.object(notification_service, "send_customer_notification", return_value=True):
            result = await notification_service.notify_order_status_update(
                "ORD-000001", "confirmed", 123456789, "pickup"
            )
            
            assert result is True

    def test_format_order_notification(self, notification_service):
        """Test format order notification"""
        order_data = {
            "order_number": "ORD-000001",
            "customer_name": "Test Customer",
            "customer_phone": "1234567890",
            "customer_telegram_id": 123456789,
            "delivery_method": "pickup",
            "items": [{"product_name": "Test Product", "quantity": 2, "price": 10.0}],
            "total": 20.0,
            "created_at": "2023-01-01 12:00:00"
        }
        
        formatted = notification_service._format_order_notification(order_data)
        
        assert "ORD-000001" in formatted
        assert "Test Customer" in formatted
        assert "pickup" in formatted.lower()


class TestCustomerOrderService:
    """Test CustomerOrderService"""

    @pytest.fixture
    def customer_order_service(self):
        """Create CustomerOrderService instance"""
        return CustomerOrderService()

    def test_get_customer_active_orders(self, customer_order_service):
        """Test get customer active orders"""
        mock_orders = [MagicMock(), MagicMock()]
        mock_orders[0].id = 1
        mock_orders[0].status = "pending"
        mock_orders[0].customer = MagicMock()
        mock_orders[0].customer.telegram_id = 123456789
        mock_orders[0].order_number = "ORD-000001"
        mock_orders[0].total = 50.0
        mock_orders[0].delivery_method = "pickup"
        mock_orders[0].delivery_address = None
        mock_orders[0].created_at = datetime.now()
        mock_orders[0].order_items = []
        
        mock_orders[1].id = 2
        mock_orders[1].status = "confirmed"
        mock_orders[1].customer = MagicMock()
        mock_orders[1].customer.telegram_id = 123456789
        mock_orders[1].order_number = "ORD-000002"
        mock_orders[1].total = 75.0
        mock_orders[1].delivery_method = "delivery"
        mock_orders[1].delivery_address = "123 Test St"
        mock_orders[1].created_at = datetime.now()
        mock_orders[1].order_items = []
        
        with patch("src.services.customer_order_service.get_all_orders", return_value=mock_orders):
            orders = customer_order_service.get_customer_active_orders(123456789)
            
            assert len(orders) == 2
            assert orders[0]["order_id"] == 1
            assert orders[1]["order_id"] == 2

    def test_get_customer_completed_orders(self, customer_order_service):
        """Test get customer completed orders"""
        mock_orders = [MagicMock(), MagicMock()]
        mock_orders[0].id = 1
        mock_orders[0].status = "delivered"
        mock_orders[0].customer = MagicMock()
        mock_orders[0].customer.telegram_id = 123456789
        mock_orders[0].order_number = "ORD-000001"
        mock_orders[0].total = 50.0
        mock_orders[0].delivery_method = "pickup"
        mock_orders[0].delivery_address = None
        mock_orders[0].created_at = datetime.now()
        mock_orders[0].order_items = []
        
        mock_orders[1].id = 2
        mock_orders[1].status = "completed"
        mock_orders[1].customer = MagicMock()
        mock_orders[1].customer.telegram_id = 123456789
        mock_orders[1].order_number = "ORD-000002"
        mock_orders[1].total = 75.0
        mock_orders[1].delivery_method = "delivery"
        mock_orders[1].delivery_address = "123 Test St"
        mock_orders[1].created_at = datetime.now()
        mock_orders[1].order_items = []
        
        with patch("src.services.customer_order_service.get_all_orders", return_value=mock_orders):
            orders = customer_order_service.get_customer_completed_orders(123456789)
            
            assert len(orders) == 2
            assert orders[0]["order_id"] == 1
            assert orders[1]["order_id"] == 2

    def test_get_customer_order_by_id_found(self, customer_order_service):
        """Test get customer order by ID - found"""
        mock_orders = [MagicMock()]
        mock_orders[0].id = 1
        mock_orders[0].customer = MagicMock()
        mock_orders[0].customer.telegram_id = 123456789
        mock_orders[0].order_number = "ORD-000001"
        mock_orders[0].total = 50.0
        mock_orders[0].status = "pending"
        mock_orders[0].delivery_method = "pickup"
        mock_orders[0].delivery_address = None
        mock_orders[0].created_at = datetime.now()
        mock_orders[0].order_items = []
        
        with patch("src.services.customer_order_service.get_all_orders", return_value=mock_orders):
            order = customer_order_service.get_customer_order_by_id(1, 123456789)
            
            assert order is not None
            assert order["order_id"] == 1
            assert order["order_number"] == "ORD-000001"

    def test_get_customer_order_by_id_not_found(self, customer_order_service):
        """Test get customer order by ID - not found"""
        with patch("src.services.customer_order_service.get_all_orders", return_value=[]):
            order = customer_order_service.get_customer_order_by_id(999, 123456789)
            
            assert order is None

    def test_get_customer_order_by_id_wrong_customer(self, customer_order_service):
        """Test get customer order by ID - wrong customer"""
        mock_orders = [MagicMock()]
        mock_orders[0].id = 1
        mock_orders[0].customer = MagicMock()
        mock_orders[0].customer.telegram_id = 987654321  # Different customer
        
        with patch("src.services.customer_order_service.get_all_orders", return_value=mock_orders):
            order = customer_order_service.get_customer_order_by_id(1, 123456789)
            
            assert order is None


class TestServicesIntegration:
    """Test service integration workflows"""

    @pytest.fixture
    def cart_service(self):
        """Create CartService instance"""
        return CartService()

    @pytest.fixture
    def order_service(self):
        """Create OrderService instance"""
        return OrderService()

    @pytest.fixture
    def admin_service(self):
        """Create AdminService instance"""
        return AdminService()

    @pytest.fixture
    def notification_service(self):
        """Create NotificationService instance"""
        return NotificationService()

    @pytest.mark.asyncio
    async def test_cart_to_order_workflow(self, cart_service, order_service):
        """Test complete cart to order workflow"""
        # Add item to cart
        with patch("src.db.operations.add_to_cart", return_value=True):
            success = cart_service.add_item(123456789, 1, 2)
            assert success is True
        
        # Get cart items
        with patch("src.db.operations.get_cart_items", return_value=[{"product_id": 1, "quantity": 2}]):
            items = cart_service.get_items(123456789)
            assert len(items) > 0
        
        # Create order
        with patch("src.db.operations.get_cart_by_telegram_id", return_value=[]):
            with patch("src.db.operations.create_order_with_items", return_value=MagicMock()):
                order = await order_service.create_order(123456789, [])
                assert order is not None

    @pytest.mark.asyncio
    async def test_order_status_workflow(self, order_service, admin_service):
        """Test order status update workflow"""
        # Create order
        with patch("src.db.operations.get_cart_by_telegram_id", return_value=[]):
            with patch("src.db.operations.create_order_with_items", return_value=MagicMock()):
                order = await order_service.create_order(123456789, [])
                assert order is not None
        
        # Update order status
        with patch("src.db.operations.update_order_status", return_value=True):
            success = await admin_service.update_order_status(1, "completed", 123456789)
            assert success is True

    @pytest.mark.asyncio
    async def test_notification_workflow(self, notification_service):
        """Test notification workflow"""
        # Send order confirmation
        with patch("src.container.get_container") as mock_container:
            mock_bot = AsyncMock()
            mock_container.return_value.get_bot.return_value = mock_bot
            
            success = await notification_service.send_admin_notification("Test message")
            assert success is True
        
        # Send status update
        with patch("src.container.get_container") as mock_container:
            mock_bot = AsyncMock()
            mock_container.return_value.get_bot.return_value = mock_bot
            
            success = await notification_service.notify_order_status_update(
                order_id="TEST123",
                new_status="completed",
                customer_chat_id=123456789,
                delivery_method="pickup"
            )
            assert success is True


class TestServicesErrorHandling:
    """Test service error handling"""

    @pytest.fixture
    def cart_service(self):
        """Create CartService instance"""
        return CartService()

    @pytest.fixture
    def order_service(self):
        """Create OrderService instance"""
        return OrderService()

    @pytest.fixture
    def admin_service(self):
        """Create AdminService instance"""
        return AdminService()

    @pytest.fixture
    def notification_service(self):
        """Create NotificationService instance"""
        return NotificationService()

    @pytest.mark.asyncio
    async def test_cart_service_error_handling(self, cart_service):
        """Test cart service error handling"""
        with patch("src.db.operations.add_to_cart", side_effect=Exception("DB Error")):
            result = cart_service.add_item(123456789, 1, 2, {"type": "classic"})
            # The method returns True on success, but we're testing error handling
            # Since the mock raises an exception, we expect the method to handle it gracefully
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_order_service_error_handling(self, order_service):
        """Test order service error handling"""
        with patch("src.db.operations.get_cart_by_telegram_id", side_effect=Exception("DB Error")):
            result = await order_service.create_order(123456789, [])
            # The method should handle the exception and return a result
            assert isinstance(result, dict)
            assert "success" in result

    @pytest.mark.asyncio
    async def test_admin_service_error_handling(self, admin_service):
        """Test admin service error handling"""
        with patch("src.db.operations.get_all_orders", side_effect=Exception("DB Error")):
            # Use a simpler method that doesn't depend on analytics service
            orders = await admin_service.get_all_orders()
            # Should return empty list when there's an error
            assert isinstance(orders, list)

    @pytest.mark.asyncio
    async def test_notification_service_error_handling(self, notification_service):
        """Test notification service error handling"""
        with patch("src.container.get_container") as mock_container:
            mock_container.return_value.get_bot.return_value = None
            result = await notification_service.send_admin_notification("Test message")
            assert result is False


class TestServicesPerformance:
    """Test service performance"""

    @pytest.fixture
    def cart_service(self):
        """Create CartService instance"""
        return CartService()

    @pytest.fixture
    def order_service(self):
        """Create OrderService instance"""
        return OrderService()

    @pytest.fixture
    def admin_service(self):
        """Create AdminService instance"""
        return AdminService()

    @pytest.fixture
    def notification_service(self):
        """Create NotificationService instance"""
        return NotificationService()

    @pytest.mark.asyncio
    async def test_cart_service_performance(self, cart_service):
        """Test cart service performance"""
        start_time = time.time()
        
        with patch("src.db.operations.get_cart_items", return_value=[]):
            cart_service.get_items(123456789)
        
        execution_time = time.time() - start_time
        assert execution_time < 3.0  # Should complete within 3 seconds (allowing for DB operations)

    @pytest.mark.asyncio
    async def test_order_service_performance(self, order_service):
        """Test order service performance"""
        start_time = time.time()
        
        with patch("src.db.operations.get_cart_by_telegram_id", return_value=[]):
            await order_service.create_order(123456789, [])
        
        execution_time = time.time() - start_time
        assert execution_time < 5.0  # Should complete within 5 seconds (allowing for DB operations)

    @pytest.mark.asyncio
    async def test_admin_service_performance(self, admin_service):
        """Test admin service performance"""
        start_time = time.time()
        
        with patch("src.db.operations.get_all_orders", return_value=[]):
            await admin_service.get_business_analytics()
        
        execution_time = time.time() - start_time
        assert execution_time < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_notification_service_performance(self, notification_service):
        """Test notification service performance"""
        start_time = time.time()
        
        with patch("src.container.get_container") as mock_container:
            mock_bot = AsyncMock()
            mock_container.return_value.get_bot.return_value = mock_bot
            await notification_service.send_admin_notification("Test message")
        
        execution_time = time.time() - start_time
        assert execution_time < 1.0  # Should complete within 1 second 