"""
Basic tests for the Samna Salta bot
"""

import pytest

from src.infrastructure.utilities.helpers import (
    format_price,
    sanitize_phone_number,
    validate_phone_number,
)


def test_format_price():
    """Test price formatting"""
    assert format_price(25.50) == "25.50 ILS"
    assert format_price(0.00) == "0.00 ILS"
    assert format_price(100.0) == "100.00 ILS"


def test_sanitize_phone_number():
    """Test phone number sanitization"""
    assert sanitize_phone_number("050-123-4567") == "+972501234567"
    assert sanitize_phone_number("+972501234567") == "+972501234567"
    assert sanitize_phone_number("0501234567") == "+972501234567"


def test_validate_phone_number():
    """Test phone number validation"""
    assert validate_phone_number("050-123-4567") == True
    assert validate_phone_number("+972501234567") == True
    assert validate_phone_number("123456789") == False
    assert validate_phone_number("invalid") == False


if __name__ == "__main__":
    pytest.main([__file__])
