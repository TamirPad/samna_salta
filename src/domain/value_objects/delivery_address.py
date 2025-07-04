"""
Delivery Address value object
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryAddress:
    """Delivery address value object with validation"""
    
    value: str
    
    def __post_init__(self):
        """Validate delivery address"""
        if not self.value or not self.value.strip():
            raise ValueError("Delivery address cannot be empty")
        
        cleaned_address = self.value.strip()
        
        if len(cleaned_address) < 10:
            raise ValueError("Delivery address must be at least 10 characters")
        
        if len(cleaned_address) > 500:
            raise ValueError("Delivery address cannot exceed 500 characters")
        
        object.__setattr__(self, 'value', cleaned_address)
    
    def __str__(self) -> str:
        return self.value 