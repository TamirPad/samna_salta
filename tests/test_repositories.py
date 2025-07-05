"""
Tests for SQLAlchemy Repositories - Customer, Order, Product, Cart
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.domain.entities.customer_entity import Customer
from src.domain.value_objects.customer_id import CustomerId
from src.domain.value_objects.customer_name import CustomerName
from src.domain.value_objects.delivery_address import DeliveryAddress
from src.domain.value_objects.order_id import OrderId
from src.domain.value_objects.phone_number import PhoneNumber
from src.domain.value_objects.price import Price
from src.domain.value_objects.product_id import ProductId
from src.domain.value_objects.product_name import ProductName
from src.domain.value_objects.telegram_id import TelegramId
from src.infrastructure.database.models import Customer as SQLCustomer
from src.infrastructure.database.models import Product as SQLProduct
from src.infrastructure.repositories.sqlalchemy_cart_repository import (
    SQLAlchemyCartRepository,
)
from src.infrastructure.repositories.sqlalchemy_customer_repository import (
    SQLAlchemyCustomerRepository,
)
from src.infrastructure.repositories.sqlalchemy_order_repository import (
    SQLAlchemyOrderRepository,
)
from src.infrastructure.repositories.sqlalchemy_product_repository import (
    SQLAlchemyProductRepository,
)


class TestSQLAlchemyCustomerRepository:
    """Test SQLAlchemy customer repository"""

    @pytest.fixture
    def customer_repository(self):
        """Create customer repository instance"""
        return SQLAlchemyCustomerRepository()

    @pytest.fixture
    def sample_customer(self):
        """Create sample customer entity"""
        return Customer(
            id=CustomerId(1),
            telegram_id=TelegramId(123456789),
            full_name=CustomerName("Ahmed Al-Yemeni"),
            phone_number=PhoneNumber("+972501234567"),
            delivery_address=DeliveryAddress("Tel Aviv, Israel"),
            is_admin=False,
        )

    @pytest.fixture
    def sample_sql_customer(self):
        """Create sample SQL customer model"""
        sql_customer = MagicMock(spec=SQLCustomer)
        sql_customer.id = 1
        sql_customer.telegram_id = 123456789
        sql_customer.full_name = "Ahmed Al-Yemeni"
        sql_customer.phone_number = "+972501234567"
        sql_customer.delivery_address = "Tel Aviv, Israel"
        sql_customer.is_admin = False
        return sql_customer

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_find_by_telegram_id_success(
        self, mock_get_session, customer_repository, sample_sql_customer
    ):
        """Test successful find by telegram ID"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = sample_sql_customer

        # Execute
        telegram_id = TelegramId(123456789)
        result = await customer_repository.find_by_telegram_id(telegram_id)

        # Verify
        assert result is not None
        assert result.telegram_id.value == 123456789
        assert result.full_name.value == "Ahmed Al-Yemeni"
        mock_session.query.assert_called_once_with(SQLCustomer)
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_find_by_telegram_id_not_found(
        self, mock_get_session, customer_repository
    ):
        """Test find by telegram ID when customer not found"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None

        # Execute
        telegram_id = TelegramId(999999999)
        result = await customer_repository.find_by_telegram_id(telegram_id)

        # Verify
        assert result is None
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_find_by_telegram_id_database_error(
        self, mock_get_session, customer_repository
    ):
        """Test find by telegram ID with database error"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.query.side_effect = SQLAlchemyError("Database error")

        # Execute and verify
        telegram_id = TelegramId(123456789)
        with pytest.raises(SQLAlchemyError):
            await customer_repository.find_by_telegram_id(telegram_id)

        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_find_by_phone_number_success(
        self, mock_get_session, customer_repository, sample_sql_customer
    ):
        """Test successful find by phone number"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = sample_sql_customer

        # Execute
        phone_number = PhoneNumber("+972501234567")
        result = await customer_repository.find_by_phone_number(phone_number)

        # Verify
        assert result is not None
        assert result.phone_number.value == "+972501234567"
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_find_by_phone_number_not_found(
        self, mock_get_session, customer_repository
    ):
        """Test find by phone number when customer not found"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None

        # Execute
        phone_number = PhoneNumber("+972507777777")
        result = await customer_repository.find_by_phone_number(phone_number)

        # Verify
        assert result is None

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_save_new_customer_success(
        self, mock_get_session, customer_repository, sample_sql_customer
    ):
        """Test saving new customer"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Create customer without ID
        customer = Customer(
            id=None,
            telegram_id=TelegramId(123456789),
            full_name=CustomerName("Ahmed Al-Yemeni"),
            phone_number=PhoneNumber("+972501234567"),
            delivery_address=DeliveryAddress("Tel Aviv, Israel"),
            is_admin=False,
        )

        # Mock session refresh to set ID
        def mock_refresh(obj):
            obj.id = 1

        mock_session.refresh.side_effect = mock_refresh

        # Execute
        with patch(
            "src.infrastructure.repositories.sqlalchemy_customer_repository.SQLCustomer"
        ) as mock_sql_customer_class:
            mock_sql_customer_class.return_value = sample_sql_customer
            result = await customer_repository.save(customer)

        # Verify
        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_save_existing_customer_success(
        self,
        mock_get_session,
        customer_repository,
        sample_customer,
        sample_sql_customer,
    ):
        """Test saving existing customer"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = sample_sql_customer

        # Execute
        result = await customer_repository.save(sample_customer)

        # Verify
        assert result is not None
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_save_existing_customer_not_found(
        self, mock_get_session, customer_repository, sample_customer
    ):
        """Test saving existing customer when customer not found in database"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None

        # Execute and verify
        with pytest.raises(ValueError):
            await customer_repository.save(sample_customer)

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_delete_customer_success(
        self, mock_get_session, customer_repository, sample_sql_customer
    ):
        """Test successful customer deletion"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = sample_sql_customer

        # Execute
        customer_id = CustomerId(1)
        result = await customer_repository.delete(customer_id)

        # Verify
        assert result is True
        mock_session.delete.assert_called_once_with(sample_sql_customer)
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_delete_customer_not_found(
        self, mock_get_session, customer_repository
    ):
        """Test customer deletion when customer not found"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None

        # Execute
        customer_id = CustomerId(999)
        result = await customer_repository.delete(customer_id)

        # Verify
        assert result is False
        mock_session.delete.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_find_by_id_success(
        self, mock_get_session, customer_repository, sample_sql_customer
    ):
        """Test successful find by ID"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = sample_sql_customer

        # Execute
        customer_id = CustomerId(1)
        result = await customer_repository.find_by_id(customer_id)

        # Verify
        assert result is not None
        assert result.id.value == 1

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_find_all_success(
        self, mock_get_session, customer_repository, sample_sql_customer
    ):
        """Test successful find all customers"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_query.all.return_value = [sample_sql_customer, sample_sql_customer]

        # Execute
        result = await customer_repository.find_all()

        # Verify
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_exists_by_telegram_id_true(
        self, mock_get_session, customer_repository, sample_sql_customer
    ):
        """Test exists by telegram ID returns True"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = sample_sql_customer

        # Execute
        telegram_id = TelegramId(123456789)
        result = await customer_repository.exists_by_telegram_id(telegram_id)

        # Verify
        assert result is True

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_exists_by_telegram_id_false(
        self, mock_get_session, customer_repository
    ):
        """Test exists by telegram ID returns False"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None

        # Execute
        telegram_id = TelegramId(999999999)
        result = await customer_repository.exists_by_telegram_id(telegram_id)

        # Verify
        assert result is False

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_exists_by_phone_number_true(
        self, mock_get_session, customer_repository, sample_sql_customer
    ):
        """Test exists by phone number returns True"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = sample_sql_customer

        # Execute
        phone_number = PhoneNumber("+972501234567")
        result = await customer_repository.exists_by_phone_number(phone_number)

        # Verify
        assert result is True

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_customer_repository.get_session")
    async def test_exists_by_phone_number_false(
        self, mock_get_session, customer_repository
    ):
        """Test exists by phone number returns False"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None

        # Execute
        phone_number = PhoneNumber("+972507777777")
        result = await customer_repository.exists_by_phone_number(phone_number)

        # Verify
        assert result is False

    def test_map_to_domain_success(self, customer_repository, sample_sql_customer):
        """Test mapping SQL model to domain entity"""
        result = customer_repository._map_to_domain(sample_sql_customer)

        assert isinstance(result, Customer)
        assert result.id.value == 1
        assert result.telegram_id.value == 123456789
        assert result.full_name.value == "Ahmed Al-Yemeni"
        assert result.phone_number.value == "+972501234567"
        assert result.delivery_address.value == "Tel Aviv, Israel"
        assert result.is_admin is False

    def test_map_to_domain_no_address(self, customer_repository):
        """Test mapping SQL model to domain entity without delivery address"""
        sql_customer = MagicMock(spec=SQLCustomer)
        sql_customer.id = 1
        sql_customer.telegram_id = 123456789
        sql_customer.full_name = "Ahmed Al-Yemeni"
        sql_customer.phone_number = "+972501234567"
        sql_customer.delivery_address = None
        sql_customer.is_admin = False

        result = customer_repository._map_to_domain(sql_customer)

        assert result.delivery_address is None


class TestSQLAlchemyProductRepository:
    """Test SQLAlchemy product repository"""

    @pytest.fixture
    def product_repository(self):
        """Create product repository instance"""
        return SQLAlchemyProductRepository()

    @pytest.fixture
    def sample_sql_product(self):
        """Create sample SQL product model"""
        sql_product = MagicMock(spec=SQLProduct)
        sql_product.id = 1
        sql_product.name = "Kubaneh"
        sql_product.description = "Traditional Yemenite bread"
        sql_product.price = 25.0
        sql_product.category = "bread"
        sql_product.is_active = True
        return sql_product

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_product_repository.get_session")
    async def test_find_by_id_success(
        self, mock_get_session, product_repository, sample_sql_product
    ):
        """Test successful find by ID"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = sample_sql_product

        # Execute
        product_id = ProductId(1)
        result = await product_repository.find_by_id(product_id)

        # Verify
        assert result is not None
        assert result.id == 1
        assert result.name == "Kubaneh"
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_product_repository.get_session")
    async def test_find_by_id_not_found(self, mock_get_session, product_repository):
        """Test find by ID when product not found"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None

        # Execute
        product_id = ProductId(999)
        result = await product_repository.find_by_id(product_id)

        # Verify
        assert result is None

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_product_repository.get_session")
    async def test_find_by_category_success(
        self, mock_get_session, product_repository, sample_sql_product
    ):
        """Test successful find by category"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.all.return_value = [sample_sql_product]

        # Execute
        result = await product_repository.find_by_category("bread")

        # Verify
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].category == "bread"

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_product_repository.get_session")
    async def test_find_all_active_success(
        self, mock_get_session, product_repository, sample_sql_product
    ):
        """Test successful find all active products"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.all.return_value = [sample_sql_product]

        # Execute
        result = await product_repository.find_all_active()

        # Verify
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].is_active is True

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_product_repository.get_session")
    async def test_database_error_handling(self, mock_get_session, product_repository):
        """Test database error handling"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.query.side_effect = SQLAlchemyError("Database error")

        # Execute and verify
        product_id = ProductId(1)
        with pytest.raises(SQLAlchemyError):
            await product_repository.find_by_id(product_id)


class TestSQLAlchemyCartRepository:
    """Test SQLAlchemy cart repository"""

    @pytest.fixture
    def cart_repository(self):
        """Create cart repository instance"""
        return SQLAlchemyCartRepository()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_cart_repository.get_session")
    async def test_get_or_create_cart_success(self, mock_get_session, cart_repository):
        """Test successful get or create cart"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_cart = MagicMock()
        mock_cart.items = []
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_cart

        # Execute
        telegram_id = TelegramId(123456789)
        result = await cart_repository.get_or_create_cart(telegram_id)

        # Verify
        assert result is not None
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_cart_repository.get_session")
    async def test_add_item_success(self, mock_get_session, cart_repository):
        """Test successful add item to cart"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Execute
        telegram_id = TelegramId(123456789)
        product_id = ProductId(1)
        result = await cart_repository.add_item(telegram_id, product_id, 2, {})

        # Verify
        assert result is True
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_cart_repository.get_session")
    async def test_get_cart_items_success(self, mock_get_session, cart_repository):
        """Test successful get cart items"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_cart_item = MagicMock()
        mock_cart_item.product_id = 1
        mock_cart_item.quantity = 2
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.all.return_value = [mock_cart_item]

        # Execute
        telegram_id = TelegramId(123456789)
        result = await cart_repository.get_cart_items(telegram_id)

        # Verify
        assert result is not None
        assert "items" in result
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_cart_repository.get_session")
    async def test_clear_cart_success(self, mock_get_session, cart_repository):
        """Test successful clear cart"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Execute
        telegram_id = TelegramId(123456789)
        result = await cart_repository.clear_cart(telegram_id)

        # Verify
        assert result is True
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


class TestSQLAlchemyOrderRepository:
    """Test SQLAlchemy order repository"""

    @pytest.fixture
    def order_repository(self):
        """Create order repository instance"""
        return SQLAlchemyOrderRepository()

    @pytest.fixture
    def sample_order_data(self):
        """Create sample order data"""
        return {
            "customer_id": 1,
            "items": [
                {
                    "product_name": "Kubaneh",
                    "quantity": 2,
                    "unit_price": 25.0,
                    "total_price": 50.0,
                    "options": {},
                }
            ],
            "subtotal": 50.0,
            "total": 50.0,
            "delivery_method": "pickup",
            "delivery_charge": 0.0,
        }

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_order_repository.get_session")
    async def test_create_order_success(
        self, mock_get_session, order_repository, sample_order_data
    ):
        """Test successful order creation"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_order = MagicMock()
        mock_order.id = 1
        mock_order.order_number = "ORD-001"

        # Execute
        result = await order_repository.create_order(sample_order_data)

        # Verify
        assert result is not None
        assert mock_session.add.call_count == 2  # Order + OrderItem
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_order_repository.get_session")
    async def test_get_order_by_id_success(self, mock_get_session, order_repository):
        """Test successful get order by ID"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_order = MagicMock()
        mock_order.id = 1
        mock_order.order_number = "ORD-001"
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_order

        # Execute
        order_id = OrderId(1)
        result = await order_repository.get_order_by_id(order_id)

        # Verify
        assert result is not None
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_order_repository.get_session")
    async def test_update_order_status_success(
        self, mock_get_session, order_repository
    ):
        """Test successful order status update"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_order = MagicMock()
        mock_order.status = "pending"
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_order

        # Execute
        order_id = OrderId(1)
        result = await order_repository.update_order_status(order_id, "confirmed")

        # Verify
        assert result is True
        assert mock_order.status == "confirmed"
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_order_repository.get_session")
    async def test_get_all_orders_success(self, mock_get_session, order_repository):
        """Test successful get all orders"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Execute
        result = await order_repository.get_all_orders()

        # Verify
        assert isinstance(result, list)
        mock_session.query.assert_called()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.repositories.sqlalchemy_order_repository.get_session")
    async def test_order_repository_error_handling(
        self, mock_get_session, order_repository
    ):
        """Test order repository error handling"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.query.side_effect = SQLAlchemyError("Database error")

        # Execute and verify
        order_id = OrderId(1)
        with pytest.raises(SQLAlchemyError):
            await order_repository.get_order_by_id(order_id)
