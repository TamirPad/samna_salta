"""
Domain Layer Tests - Value Objects and Entities
"""

import pytest
from src.domain.entities.customer_entity import Customer
from src.domain.value_objects.telegram_id import TelegramId
from src.domain.value_objects.customer_name import CustomerName
from src.domain.value_objects.phone_number import PhoneNumber
from src.domain.value_objects.delivery_address import DeliveryAddress


class TestValueObjects:
    """Test domain value objects validation and behavior"""

    def test_telegram_id_valid(self):
        """Test valid TelegramId creation"""
        tid = TelegramId(123456789)
        assert tid.value == 123456789
        assert str(tid) == "123456789"
        assert tid == TelegramId(123456789)

    def test_telegram_id_invalid(self):
        """Test invalid TelegramId values"""
        invalid_values = [0, -1, None, "abc"]
        for value in invalid_values:
            with pytest.raises(ValueError):
                TelegramId(value)

    def test_customer_name_valid(self):
        """Test valid CustomerName creation"""
        names = ["John Doe", "יוסף כהן", "أحمد محمد"]
        for name in names:
            cn = CustomerName(name)
            assert cn.value == name

    def test_customer_name_invalid(self):
        """Test invalid CustomerName values"""
        invalid_names = ["", "A", "A" * 101, "123456"]
        for name in invalid_names:
            with pytest.raises(ValueError):
                CustomerName(name)

    def test_phone_number_normalization(self):
        """Test phone number normalization"""
        test_cases = [
            ("0501234567", "+972501234567"),
            ("050-123-4567", "+972501234567"),
            ("+972501234567", "+972501234567"),
        ]
        for input_phone, expected in test_cases:
            phone = PhoneNumber(input_phone)
            assert phone.value == expected

    def test_phone_number_invalid(self):
        """Test invalid phone numbers"""
        invalid_phones = ["", "123", "abcdef", "+1234567890123"]
        for phone in invalid_phones:
            with pytest.raises(ValueError):
                PhoneNumber(phone)

    def test_delivery_address_valid(self):
        """Test valid DeliveryAddress creation"""
        addresses = [
            "123 Main St, Tel Aviv, Israel",
            "רחוב הרצל 45, תל אביב",
            "Apartment 5B, Building 12, Ramat Gan"
        ]
        for address in addresses:
            da = DeliveryAddress(address)
            assert da.value == address

    def test_delivery_address_invalid(self):
        """Test invalid DeliveryAddress values"""
        invalid_addresses = ["", "   ", "123", "A" * 501]
        for address in invalid_addresses:
            with pytest.raises(ValueError):
                DeliveryAddress(address)


class TestCustomerEntity:
    """Test Customer entity"""

    def test_customer_creation(self):
        """Test Customer entity creation"""
        telegram_id = TelegramId(123456789)
        name = CustomerName("John Doe")
        phone = PhoneNumber("+972501234567")
        address = DeliveryAddress("123 Main St, Tel Aviv")
        
        customer = Customer(
            id=None,
            telegram_id=telegram_id,
            full_name=name,
            phone_number=phone,
            delivery_address=address
        )
        
        assert customer.telegram_id == telegram_id
        assert customer.full_name == name
        assert customer.phone_number == phone
        assert customer.delivery_address == address
        assert customer.is_admin is False
        assert customer.created_at is not None
        assert customer.updated_at is not None

    def test_customer_without_address(self):
        """Test Customer entity creation without address"""
        telegram_id = TelegramId(123456789)
        name = CustomerName("John Doe")
        phone = PhoneNumber("+972501234567")
        
        customer = Customer(
            id=None,
            telegram_id=telegram_id,
            full_name=name,
            phone_number=phone
        )
        
        assert customer.delivery_address is None

    def test_customer_methods(self):
        """Test Customer entity methods"""
        telegram_id = TelegramId(123456789)
        name = CustomerName("John Doe")
        phone = PhoneNumber("+972501234567")
        
        customer = Customer(
            id=None,
            telegram_id=telegram_id,
            full_name=name,
            phone_number=phone
        )
        
        # Test can_place_order
        assert customer.can_place_order() is True
        
        # Test requires_delivery_address
        assert customer.requires_delivery_address() is True
        
        # Test update methods
        new_name = CustomerName("Jane Doe")
        new_phone = PhoneNumber("+972521234567")
        original_updated_at = customer.updated_at
        
        customer.update_contact_info(new_name, new_phone)
        assert customer.full_name == new_name
        assert customer.phone_number == new_phone
        assert customer.updated_at > original_updated_at
        
        # Test admin status
        customer.set_admin_status(True)
        assert customer.is_admin is True 