"""
Customer ID value object
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CustomerId:
    """Customer identifier value object"""
    
    value: int
    
    def __post_init__(self):
        """Validate customer ID"""
        if not isinstance(self.value, int) or self.value <= 0:
            raise ValueError("Customer ID must be a positive integer")
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __int__(self) -> int:
        return self.value 