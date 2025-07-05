"""Order Number value object"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class OrderNumber:
    """Order number value object"""

    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Order number cannot be empty")

        # Validate order number format (SS + timestamp)
        if not re.match(r"^SS\d{14}$", self.value):
            raise ValueError("Order number must follow format SS + 14 digits")

    def __str__(self) -> str:
        return self.value
