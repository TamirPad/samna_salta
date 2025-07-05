# pylint: disable=too-many-instance-attributes
"""
Customer domain entity

Represents a customer in the Samna Salta business domain.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from src.domain.value_objects.customer_id import CustomerId
from src.domain.value_objects.customer_name import CustomerName
from src.domain.value_objects.delivery_address import DeliveryAddress
from src.domain.value_objects.phone_number import PhoneNumber
from src.domain.value_objects.telegram_id import TelegramId


@dataclass
class Customer:
    """
    Customer domain entity

    Represents a customer who can place orders through the Telegram bot.
    """

    id: Optional[CustomerId]
    telegram_id: TelegramId
    full_name: CustomerName
    phone_number: PhoneNumber
    delivery_address: Optional[DeliveryAddress] = None
    is_admin: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Initialize timestamps if not provided"""
        now = datetime.now(UTC)
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now

    def update_contact_info(self, name: CustomerName, phone: PhoneNumber) -> None:
        """Update customer contact information"""
        self.full_name = name
        self.phone_number = phone
        self.updated_at = datetime.now(UTC)

    def update_delivery_address(self, address: Optional[DeliveryAddress]) -> None:
        """Update customer delivery address"""
        self.delivery_address = address
        self.updated_at = datetime.now(UTC)

    def set_admin_status(self, is_admin: bool) -> None:
        """Set admin status for the customer"""
        self.is_admin = is_admin
        self.updated_at = datetime.now(UTC)

    def can_place_order(self) -> bool:
        """Check if customer can place an order"""
        return (
            self.full_name is not None
            and self.phone_number is not None
            and self.telegram_id is not None
        )

    def requires_delivery_address(self) -> bool:
        """Check if customer needs delivery address for delivery orders"""
        return self.delivery_address is None

    def __str__(self) -> str:
        admin_str = " (Admin)" if self.is_admin else ""
        return (
            f"Customer(id={self.id}, name={self.full_name}, "
            f"phone={self.phone_number}{admin_str})"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, Customer):
            return False
        return self.id == other.id if self.id and other.id else False
