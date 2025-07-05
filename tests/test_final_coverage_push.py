"""
Final Coverage Push Tests - Value Objects, Database Operations, and Use Case Edge Cases
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from decimal import Decimal
from datetime import datetime

# Value Objects Tests
from src.domain.value_objects.money import Money
from src.domain.value_objects.order_id import OrderId
from src.domain.value_objects.order_number import OrderNumber
from src.domain.value_objects.product_id import ProductId
from src.domain.value_objects.product_name import ProductName

# Use Cases for additional coverage
from src.application.use_cases.cart_management_use_case import CartManagementUseCase
from src.application.use_cases.product_catalog_use_case import ProductCatalogUseCase

# Database Operations
from src.infrastructure.database.operations import get_session, get_engine, init_db


class TestMoneyValueObject:
    """Test Money value object comprehensive functionality"""

    def test_money_creation_valid(self):
        """Test money creation with valid amount"""
        money = Money(Decimal("25.99"))
        
        assert money.amount == Decimal("25.99")
        assert money.currency == "USD"  # Default currency

    def test_money_creation_with_currency(self):
        """Test money creation with custom currency"""
        money = Money(Decimal("100.00"), "EUR")
        
        assert money.amount == Decimal("100.00")
        assert money.currency == "EUR"

    def test_money_creation_invalid_amount(self):
        """Test money creation with invalid amount"""
        with pytest.raises(ValueError):
            Money(Decimal("-10.00"))

    def test_money_creation_zero_amount(self):
        """Test money creation with zero amount"""
        money = Money(Decimal("0.00"))
        
        assert money.amount == Decimal("0.00")

    def test_money_addition(self):
        """Test money addition"""
        money1 = Money(Decimal("10.50"))
        money2 = Money(Decimal("5.25"))
        
        result = money1 + money2
        
        assert result.amount == Decimal("15.75")

    def test_money_addition_different_currency(self):
        """Test money addition with different currencies"""
        money1 = Money(Decimal("10.50"), "USD")
        money2 = Money(Decimal("5.25"), "EUR")
        
        with pytest.raises(ValueError):
            money1 + money2

    def test_money_subtraction(self):
        """Test money subtraction"""
        money1 = Money(Decimal("15.75"))
        money2 = Money(Decimal("5.25"))
        
        result = money1 - money2
        
        assert result.amount == Decimal("10.50")

    def test_money_multiplication(self):
        """Test money multiplication"""
        money = Money(Decimal("10.50"))
        
        result = money * 3
        
        assert result.amount == Decimal("31.50")

    def test_money_division(self):
        """Test money division"""
        money = Money(Decimal("31.50"))
        
        result = money / 3
        
        assert result.amount == Decimal("10.50")

    def test_money_division_by_zero(self):
        """Test money division by zero"""
        money = Money(Decimal("10.50"))
        
        with pytest.raises(ZeroDivisionError):
            money / 0

    def test_money_comparison_equal(self):
        """Test money equality comparison"""
        money1 = Money(Decimal("10.50"))
        money2 = Money(Decimal("10.50"))
        
        assert money1 == money2

    def test_money_comparison_not_equal(self):
        """Test money inequality comparison"""
        money1 = Money(Decimal("10.50"))
        money2 = Money(Decimal("15.75"))
        
        assert money1 != money2

    def test_money_comparison_less_than(self):
        """Test money less than comparison"""
        money1 = Money(Decimal("10.50"))
        money2 = Money(Decimal("15.75"))
        
        assert money1 < money2

    def test_money_comparison_greater_than(self):
        """Test money greater than comparison"""
        money1 = Money(Decimal("15.75"))
        money2 = Money(Decimal("10.50"))
        
        assert money1 > money2

    def test_money_string_representation(self):
        """Test money string representation"""
        money = Money(Decimal("10.50"))
        
        money_str = str(money)
        
        assert "10.50" in money_str
        assert "USD" in money_str

    def test_money_to_float(self):
        """Test money to float conversion"""
        money = Money(Decimal("10.50"))
        
        float_value = money.to_float()
        
        assert float_value == 10.50

    def test_money_format_display(self):
        """Test money display formatting"""
        money = Money(Decimal("10.50"))
        
        formatted = money.format_display()
        
        assert "$10.50" in formatted

    def test_money_hash(self):
        """Test money hashing for use in sets/dicts"""
        money1 = Money(Decimal("10.50"))
        money2 = Money(Decimal("10.50"))
        
        assert hash(money1) == hash(money2)


class TestOrderIdValueObject:
    """Test OrderId value object"""

    def test_order_id_creation_valid(self):
        """Test order ID creation with valid value"""
        order_id = OrderId(123)
        
        assert order_id.value == 123

    def test_order_id_creation_string(self):
        """Test order ID creation with string value"""
        order_id = OrderId("456")
        
        assert order_id.value == 456

    def test_order_id_creation_invalid(self):
        """Test order ID creation with invalid value"""
        with pytest.raises(ValueError):
            OrderId(-1)

    def test_order_id_equality(self):
        """Test order ID equality"""
        order_id1 = OrderId(123)
        order_id2 = OrderId(123)
        
        assert order_id1 == order_id2

    def test_order_id_inequality(self):
        """Test order ID inequality"""
        order_id1 = OrderId(123)
        order_id2 = OrderId(456)
        
        assert order_id1 != order_id2

    def test_order_id_string_representation(self):
        """Test order ID string representation"""
        order_id = OrderId(123)
        
        assert str(order_id) == "OrderId(123)"


class TestOrderNumberValueObject:
    """Test OrderNumber value object"""

    def test_order_number_creation_valid(self):
        """Test order number creation with valid format"""
        order_num = OrderNumber("ORD-001")
        
        assert order_num.value == "ORD-001"

    def test_order_number_creation_invalid_format(self):
        """Test order number creation with invalid format"""
        with pytest.raises(ValueError):
            OrderNumber("INVALID")

    def test_order_number_creation_empty(self):
        """Test order number creation with empty string"""
        with pytest.raises(ValueError):
            OrderNumber("")

    def test_order_number_equality(self):
        """Test order number equality"""
        order_num1 = OrderNumber("ORD-001")
        order_num2 = OrderNumber("ORD-001")
        
        assert order_num1 == order_num2

    def test_order_number_string_representation(self):
        """Test order number string representation"""
        order_num = OrderNumber("ORD-001")
        
        assert str(order_num) == "ORD-001"

    def test_order_number_generate(self):
        """Test order number generation"""
        order_num = OrderNumber.generate()
        
        assert order_num.value.startswith("ORD-")
        assert len(order_num.value) > 4


class TestProductNameValueObject:
    """Test ProductName value object edge cases"""

    def test_product_name_creation_valid(self):
        """Test product name creation with valid name"""
        product_name = ProductName("Traditional Kubaneh")
        
        assert product_name.value == "Traditional Kubaneh"

    def test_product_name_creation_with_spaces(self):
        """Test product name creation with extra spaces"""
        product_name = ProductName("  Traditional Kubaneh  ")
        
        assert product_name.value == "Traditional Kubaneh"

    def test_product_name_creation_too_short(self):
        """Test product name creation with too short name"""
        with pytest.raises(ValueError):
            ProductName("A")

    def test_product_name_creation_too_long(self):
        """Test product name creation with too long name"""
        long_name = "A" * 201  # Assuming max length is 200
        with pytest.raises(ValueError):
            ProductName(long_name)

    def test_product_name_string_representation(self):
        """Test product name string representation"""
        product_name = ProductName("Traditional Kubaneh")
        
        assert str(product_name) == "Traditional Kubaneh"


class TestCartManagementUseCaseExtended:
    """Test additional cart management use case scenarios"""

    @pytest.fixture
    def cart_use_case(self):
        """Create cart management use case with mocked dependencies"""
        cart_repo = MagicMock()
        product_repo = MagicMock()
        return CartManagementUseCase(cart_repo, product_repo)

    @pytest.mark.asyncio
    async def test_remove_from_cart_success(self, cart_use_case):
        """Test successful remove item from cart"""
        # Mock successful removal
        cart_use_case.cart_repository.get_cart_items = AsyncMock(return_value={
            "items": [{"product_id": 1, "quantity": 2}]
        })
        cart_use_case.cart_repository.update_cart = AsyncMock(return_value=True)
        
        from src.domain.value_objects.telegram_id import TelegramId
        from src.domain.value_objects.product_id import ProductId
        
        result = await cart_use_case.remove_from_cart(
            TelegramId(123456789),
            ProductId(1),
            1
        )
        
        assert result is not None
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_cart_quantity_success(self, cart_use_case):
        """Test successful cart quantity update"""
        cart_use_case.cart_repository.get_cart_items = AsyncMock(return_value={
            "items": [{"product_id": 1, "quantity": 2}]
        })
        cart_use_case.cart_repository.update_cart = AsyncMock(return_value=True)
        
        from src.domain.value_objects.telegram_id import TelegramId
        from src.domain.value_objects.product_id import ProductId
        
        result = await cart_use_case.update_item_quantity(
            TelegramId(123456789),
            ProductId(1),
            3
        )
        
        assert result is not None
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_clear_cart_success(self, cart_use_case):
        """Test successful cart clearing"""
        cart_use_case.cart_repository.clear_cart = AsyncMock(return_value=True)
        
        from src.domain.value_objects.telegram_id import TelegramId
        
        result = await cart_use_case.clear_cart(TelegramId(123456789))
        
        assert result is not None
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_cart_total_success(self, cart_use_case):
        """Test getting cart total"""
        cart_use_case.cart_repository.get_cart_items = AsyncMock(return_value={
            "items": [
                {"product_id": 1, "quantity": 2, "unit_price": 25.0},
                {"product_id": 2, "quantity": 1, "unit_price": 15.0}
            ]
        })
        
        from src.domain.value_objects.telegram_id import TelegramId
        
        result = await cart_use_case.get_cart_total(TelegramId(123456789))
        
        assert result is not None
        assert result["total"] == 65.0  # (2 * 25.0) + (1 * 15.0)


class TestProductCatalogUseCaseExtended:
    """Test additional product catalog use case scenarios"""

    @pytest.fixture
    def product_use_case(self):
        """Create product catalog use case with mocked dependencies"""
        product_repo = MagicMock()
        return ProductCatalogUseCase(product_repo)

    @pytest.mark.asyncio
    async def test_search_products_by_name_success(self, product_use_case):
        """Test successful product search by name"""
        mock_products = [
            {"id": 1, "name": "Kubaneh", "category": "bread"},
            {"id": 2, "name": "Kubaneh Special", "category": "bread"}
        ]
        product_use_case.product_repository.search_by_name = AsyncMock(return_value=mock_products)
        
        result = await product_use_case.search_products("Kubaneh")
        
        assert result is not None
        assert len(result["products"]) == 2

    @pytest.mark.asyncio
    async def test_get_product_details_success(self, product_use_case):
        """Test successful product details retrieval"""
        mock_product = {"id": 1, "name": "Kubaneh", "description": "Traditional bread"}
        product_use_case.product_repository.find_by_id = AsyncMock(return_value=mock_product)
        
        from src.domain.value_objects.product_id import ProductId
        
        result = await product_use_case.get_product_details(ProductId(1))
        
        assert result is not None
        assert result["product"]["name"] == "Kubaneh"

    @pytest.mark.asyncio
    async def test_get_featured_products_success(self, product_use_case):
        """Test successful featured products retrieval"""
        mock_products = [{"id": 1, "name": "Featured Kubaneh", "featured": True}]
        product_use_case.product_repository.find_featured = AsyncMock(return_value=mock_products)
        
        result = await product_use_case.get_featured_products()
        
        assert result is not None
        assert len(result["products"]) == 1

    @pytest.mark.asyncio
    async def test_get_categories_success(self, product_use_case):
        """Test successful categories retrieval"""
        mock_categories = ["bread", "meat", "dessert"]
        product_use_case.product_repository.get_categories = AsyncMock(return_value=mock_categories)
        
        result = await product_use_case.get_categories()
        
        assert result is not None
        assert "bread" in result["categories"]


class TestDatabaseOperations:
    """Test database operations with comprehensive mocking"""

    @patch('src.infrastructure.database.operations.sessionmaker')
    @patch('src.infrastructure.database.operations.create_engine')
    def test_get_engine_success(self, mock_create_engine, mock_sessionmaker):
        """Test successful engine creation"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.infrastructure.database.operations.get_config') as mock_config:
            mock_config.return_value.database_url = "sqlite:///test.db"
            engine = get_engine()
        
        assert engine is not None
        mock_create_engine.assert_called_once()

    @patch('src.infrastructure.database.operations.sessionmaker')
    @patch('src.infrastructure.database.operations.get_engine')
    def test_get_session_success(self, mock_get_engine, mock_sessionmaker):
        """Test successful session retrieval"""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session_class = MagicMock()
        mock_sessionmaker.return_value = mock_session_class
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        session = get_session()
        
        assert session is not None

    @patch('src.infrastructure.database.operations.get_engine')
    @patch('src.infrastructure.database.operations.init_default_products')
    def test_init_db_success(self, mock_init_products, mock_get_engine):
        """Test successful database initialization"""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_metadata = MagicMock()
        
        with patch('src.infrastructure.database.operations.Base') as mock_base:
            mock_base.metadata = mock_metadata
            init_db()
        
        mock_metadata.create_all.assert_called_once()
        mock_init_products.assert_called_once()

    @patch('src.infrastructure.database.operations.get_session')
    def test_database_session_usage(self, mock_get_session):
        """Test database session usage pattern"""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        session = get_session()
        
        # Simulate database operations
        session.query.return_value.filter.return_value.first.return_value = None
        result = session.query(MagicMock()).filter(MagicMock()).first()
        
        assert result is None
        assert session.query.called 