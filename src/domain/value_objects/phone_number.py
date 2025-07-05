"""
Phone Number value object

Represents a validated phone number in the system.
"""

import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class PhoneNumber:
    """
    Phone number value object with Israeli phone number validation
    """

    value: str

    # Israeli phone number patterns
    ISRAELI_MOBILE_PATTERN: ClassVar[str] = r"^\+972[5][0-9]{8}$"
    ISRAELI_LANDLINE_PATTERN: ClassVar[str] = r"^\+972[2-4,8-9][0-9]{7}$"

    def __post_init__(self):
        """Validate phone number on creation"""
        if not self.value:
            raise ValueError("Phone number cannot be empty")

        normalized = self._normalize_phone_number(self.value)
        if not self._is_valid_israeli_number(normalized):
            raise ValueError(f"Invalid Israeli phone number: {self.value}")

        # Use object.__setattr__ because the class is frozen
        object.__setattr__(self, "value", normalized)

    @staticmethod
    def _normalize_phone_number(phone: str) -> str:
        """Normalize phone number to standard format"""
        # Remove all non-digit characters except +
        cleaned = re.sub(r"[^\d+]", "", phone)

        # Handle different Israeli phone number formats
        if cleaned.startswith("972"):
            return f"+{cleaned}"
        if cleaned.startswith("0"):
            return f"+972{cleaned[1:]}"
        if cleaned.startswith("+972"):
            return cleaned
        if len(cleaned) == 9 and cleaned.startswith("5"):
            return f"+972{cleaned}"
        if len(cleaned) == 10 and cleaned.startswith("05"):
            return f"+972{cleaned[1:]}"
        return cleaned

    def _is_valid_israeli_number(self, phone: str) -> bool:
        """Validate Israeli phone number format"""
        return re.match(self.ISRAELI_MOBILE_PATTERN, phone) or re.match(
            self.ISRAELI_LANDLINE_PATTERN, phone
        )

    @classmethod
    def create(cls, phone_str: str) -> "PhoneNumber":
        """Factory method to create phone number with validation"""
        return cls(phone_str)

    def is_mobile(self) -> bool:
        """Check if this is a mobile number"""
        return re.match(self.ISRAELI_MOBILE_PATTERN, self.value) is not None

    def is_landline(self) -> bool:
        """Check if this is a landline number"""
        return re.match(self.ISRAELI_LANDLINE_PATTERN, self.value) is not None

    def display_format(self) -> str:
        """Return phone number in display format"""
        if self.is_mobile():
            # +972501234567 -> 050-123-4567
            without_prefix = self.value[4:]  # Remove +972
            return f"0{without_prefix[:2]}-{without_prefix[2:5]}-{without_prefix[5:]}"
        return self.value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"PhoneNumber('{self.value}')"
