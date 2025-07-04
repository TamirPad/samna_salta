"""
Money value object

Represents monetary amounts with currency handling.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Union


@dataclass(frozen=True)
class Money:
    """
    Money value object that handles currency amounts properly
    """
    
    amount: Decimal
    currency: str = "ILS"
    
    def __post_init__(self):
        """Validate money object on creation"""
        if not isinstance(self.amount, Decimal):
            # Convert to Decimal for precise currency calculations
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))
        
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        
        if not self.currency or len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter code")
        
        # Round to 2 decimal places for currency
        rounded_amount = self.amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        object.__setattr__(self, 'amount', rounded_amount)
        object.__setattr__(self, 'currency', self.currency.upper())
    
    @classmethod
    def from_float(cls, amount: float, currency: str = "ILS") -> 'Money':
        """Create Money from float amount"""
        return cls(Decimal(str(amount)), currency)
    
    @classmethod
    def zero(cls, currency: str = "ILS") -> 'Money':
        """Create zero money amount"""
        return cls(Decimal('0'), currency)
    
    def add(self, other: 'Money') -> 'Money':
        """Add two money amounts"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def subtract(self, other: 'Money') -> 'Money':
        """Subtract two money amounts"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract different currencies: {self.currency} and {other.currency}")
        result_amount = self.amount - other.amount
        if result_amount < 0:
            raise ValueError("Cannot have negative money amount")
        return Money(result_amount, self.currency)
    
    def multiply(self, factor: Union[int, float, Decimal]) -> 'Money':
        """Multiply money by a factor"""
        if not isinstance(factor, Decimal):
            factor = Decimal(str(factor))
        if factor < 0:
            raise ValueError("Cannot multiply money by negative factor")
        return Money(self.amount * factor, self.currency)
    
    def is_zero(self) -> bool:
        """Check if amount is zero"""
        return self.amount == Decimal('0')
    
    def is_positive(self) -> bool:
        """Check if amount is positive"""
        return self.amount > Decimal('0')
    
    def to_float(self) -> float:
        """Convert to float (use with caution for display only)"""
        return float(self.amount)
    
    def format_display(self) -> str:
        """Format for display to users"""
        return f"{self.amount:.2f} {self.currency}"
    
    def __str__(self) -> str:
        return self.format_display()
    
    def __repr__(self) -> str:
        return f"Money(amount={self.amount}, currency='{self.currency}')"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency
    
    def __lt__(self, other: 'Money') -> bool:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount < other.amount
    
    def __le__(self, other: 'Money') -> bool:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount <= other.amount
    
    def __gt__(self, other: 'Money') -> bool:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount > other.amount
    
    def __ge__(self, other: 'Money') -> bool:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount >= other.amount
    
    def __add__(self, other: 'Money') -> 'Money':
        """Add two money amounts using + operator"""
        return self.add(other)
    
    def __sub__(self, other: 'Money') -> 'Money':
        """Subtract two money amounts using - operator"""
        return self.subtract(other)
    
    def __mul__(self, factor: Union[int, float, Decimal]) -> 'Money':
        """Multiply money by a factor using * operator"""
        return self.multiply(factor)
    
    def __rmul__(self, factor: Union[int, float, Decimal]) -> 'Money':
        """Reverse multiply for factor * money"""
        return self.multiply(factor) 