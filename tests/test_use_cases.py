"""
Application Use Cases Tests
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.use_cases.cart_management_use_case import (
    AddToCartRequest,
    CartManagementUseCase,
)
from src.application.use_cases.customer_registration_use_case import (
    CustomerRegistrationRequest,
    CustomerRegistrationUseCase,
)
from src.application.use_cases.product_catalog_use_case import (
    ProductCatalogRequest,
    ProductCatalogUseCase,
)
from src.domain.value_objects.customer_name import CustomerName
from src.domain.value_objects.phone_number import PhoneNumber
from src.domain.value_objects.telegram_id import TelegramId


class TestCustomerRegistrationUseCase:
    """Test customer registration use case"""

    @pytest.mark.asyncio
    async def test_register_new_customer_success(self):
        """Test successful new customer registration"""
        mock_repo = MagicMock()
        mock_repo.find_by_phone_number = AsyncMock(return_value=None)
        mock_repo.find_by_telegram_id = AsyncMock(return_value=None)

        # Create a mock customer to return from save
        mock_customer = MagicMock()
        mock_customer.id = 1
        mock_repo.save = AsyncMock(return_value=mock_customer)

        use_case = CustomerRegistrationUseCase(mock_repo)

        request = CustomerRegistrationRequest(
            telegram_id=123456789,
            full_name="John Doe",
            phone_number="+972501234567",
            delivery_address="Tel Aviv, Israel",
        )

        response = await use_case.execute(request)

        assert response.success is True
        assert response.customer is not None
        assert response.is_returning_customer is False
        mock_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_returning_customer(self):
        """Test returning customer recognition"""
        existing_customer = MagicMock()
        existing_customer.telegram_id.value = 987654321

        mock_repo = MagicMock()
        mock_repo.find_by_phone_number = AsyncMock(return_value=existing_customer)
        mock_repo.find_by_telegram_id = AsyncMock(return_value=None)
        mock_repo.save = AsyncMock(return_value=existing_customer)

        use_case = CustomerRegistrationUseCase(mock_repo)

        request = CustomerRegistrationRequest(
            telegram_id=123456789, full_name="John Doe", phone_number="+972501234567"
        )

        response = await use_case.execute(request)

        assert response.success is True
        assert response.is_returning_customer is True

    @pytest.mark.asyncio
    async def test_register_invalid_data(self):
        """Test registration with invalid data"""
        mock_repo = MagicMock()
        use_case = CustomerRegistrationUseCase(mock_repo)

        # Invalid telegram ID
        request = CustomerRegistrationRequest(
            telegram_id=0, full_name="John Doe", phone_number="+972501234567"
        )

        response = await use_case.execute(request)
        assert response.success is False
        assert "Invalid Telegram ID" in response.error_message


class TestProductCatalogUseCase:
    """Test product catalog use case"""

    @pytest.mark.asyncio
    async def test_get_products_by_category_success(self):
        """Test getting products by category"""
        # Create a mock object with attributes instead of a dictionary
        mock_product = MagicMock()
        mock_product.id = 1
        mock_product.name = "Kubaneh"
        mock_product.price = 25.0
        mock_product.category = "bread"
        mock_product.is_active = True

        mock_repo = MagicMock()
        mock_repo.find_by_category = AsyncMock(return_value=[mock_product])

        use_case = ProductCatalogUseCase(mock_repo)

        request = ProductCatalogRequest(category="bread")
        response = await use_case.get_products_by_category(request)

        assert response.success is True
        assert len(response.products) == 1

    @pytest.mark.asyncio
    async def test_get_products_empty_category(self):
        """Test getting products with no category specified"""
        mock_repo = MagicMock()
        use_case = ProductCatalogUseCase(mock_repo)

        request = ProductCatalogRequest(category=None)
        response = await use_case.get_products_by_category(request)

        assert response.success is False
        assert "Category is required" in response.error_message

    @pytest.mark.asyncio
    async def test_get_all_active_products(self):
        """Test getting all active products"""
        # Create mock objects with attributes
        mock_product1 = MagicMock()
        mock_product1.id = 1
        mock_product1.name = "Kubaneh"
        mock_product1.price = 25.0
        mock_product1.category = "bread"

        mock_product2 = MagicMock()
        mock_product2.id = 2
        mock_product2.name = "Hilbeh"
        mock_product2.price = 30.0
        mock_product2.category = "hilbeh"

        mock_repo = MagicMock()
        mock_repo.find_all_active = AsyncMock(
            return_value=[mock_product1, mock_product2]
        )

        use_case = ProductCatalogUseCase(mock_repo)
        response = await use_case.get_all_active_products()

        assert response.success is True
        assert len(response.products) == 2


class TestCartManagementUseCase:
    """Test cart management use case"""

    @pytest.mark.asyncio
    async def test_add_to_cart_new_cart(self):
        """Test adding item to new cart"""
        # Create mock object with attributes
        mock_product = MagicMock()
        mock_product.id = 1
        mock_product.name = "Kubaneh"
        mock_product.price = 25.0
        mock_product.is_active = True

        mock_cart_repo = MagicMock()
        mock_cart_repo.find_by_telegram_id = AsyncMock(return_value=None)
        mock_cart_repo.save = AsyncMock(return_value=True)
        mock_cart_repo.add_item = AsyncMock(return_value=True)
        mock_cart_repo.get_cart_items = AsyncMock(return_value=[])

        mock_product_repo = MagicMock()
        mock_product_repo.find_by_id = AsyncMock(return_value=mock_product)

        mock_customer_repo = MagicMock()
        use_case = CartManagementUseCase(mock_cart_repo, mock_product_repo, mock_customer_repo)

        request = AddToCartRequest(telegram_id=123456789, product_id=1, quantity=2)

        response = await use_case.add_to_cart(request)

        assert response.success is True
        mock_cart_repo.add_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_to_cart_product_not_found(self):
        """Test adding non-existent product to cart"""
        mock_cart_repo = MagicMock()
        mock_product_repo = MagicMock()
        mock_product_repo.find_by_id = AsyncMock(return_value=None)

        mock_customer_repo = MagicMock()
        use_case = CartManagementUseCase(mock_cart_repo, mock_product_repo, mock_customer_repo)

        request = AddToCartRequest(telegram_id=123456789, product_id=999, quantity=1)

        response = await use_case.add_to_cart(request)

        assert response.success is False
        assert "Product not found" in response.error_message

    @pytest.mark.asyncio
    async def test_add_to_cart_inactive_product(self):
        """Test adding inactive product to cart"""
        # Create mock object with attributes
        mock_product = MagicMock()
        mock_product.id = 1
        mock_product.name = "Inactive Product"
        mock_product.price = 25.0
        mock_product.is_active = False

        mock_cart_repo = MagicMock()
        mock_product_repo = MagicMock()
        mock_product_repo.find_by_id = AsyncMock(return_value=mock_product)

        mock_customer_repo = MagicMock()
        use_case = CartManagementUseCase(mock_cart_repo, mock_product_repo, mock_customer_repo)

        request = AddToCartRequest(telegram_id=123456789, product_id=1, quantity=1)

        response = await use_case.add_to_cart(request)

        assert response.success is False
        assert "unavailable" in response.error_message.lower()
