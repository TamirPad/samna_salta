"""Product ID value object"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductId:
    """Product identifier value object"""
    
    value: int
    
    def __post_init__(self):
        if not isinstance(self.value, int) or self.value <= 0:
            raise ValueError("Product ID must be a positive integer")
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __int__(self) -> int:
        return self.value 