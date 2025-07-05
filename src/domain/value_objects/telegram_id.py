"""
Telegram ID value object
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramId:
    """Telegram user identifier value object"""

    value: int

    def __post_init__(self):
        """Validate telegram ID"""
        if not isinstance(self.value, int) or self.value <= 0:
            raise ValueError("Telegram ID must be a positive integer")

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return self.value
