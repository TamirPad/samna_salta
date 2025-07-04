"""
Domain value objects package

Contains immutable value objects that represent concepts in the business domain.
"""

from .customer_id import CustomerId
from .telegram_id import TelegramId
from .phone_number import PhoneNumber
from .customer_name import CustomerName
from .delivery_address import DeliveryAddress
from .product_id import ProductId
from .product_name import ProductName
from .price import Price
from .money import Money
from .order_id import OrderId
from .order_number import OrderNumber

__all__ = [
    'CustomerId',
    'TelegramId',
    'PhoneNumber',
    'CustomerName',
    'DeliveryAddress',
    'ProductId',
    'ProductName',
    'Price',
    'Money',
    'OrderId',
    'OrderNumber'
] 