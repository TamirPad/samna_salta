"""
Customer Repository interface

Defines the contract for customer data access operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.customer_entity import Customer
from ..value_objects.customer_id import CustomerId
from ..value_objects.telegram_id import TelegramId
from ..value_objects.phone_number import PhoneNumber


class CustomerRepository(ABC):
    """
    Abstract repository interface for Customer entities
    
    Follows the Repository pattern and Dependency Inversion principle.
    Infrastructure layer provides concrete implementations.
    """
    
    @abstractmethod
    async def save(self, customer: Customer) -> Customer:
        """
        Save or update a customer
        
        Args:
            customer: The customer entity to save
            
        Returns:
            The saved customer with updated fields (e.g., ID, timestamps)
        """
        pass
    
    @abstractmethod
    async def find_by_id(self, customer_id: CustomerId) -> Optional[Customer]:
        """
        Find a customer by their ID
        
        Args:
            customer_id: The customer's unique identifier
            
        Returns:
            The customer if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_telegram_id(self, telegram_id: TelegramId) -> Optional[Customer]:
        """
        Find a customer by their Telegram ID
        
        Args:
            telegram_id: The customer's Telegram identifier
            
        Returns:
            The customer if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_phone_number(self, phone_number: PhoneNumber) -> Optional[Customer]:
        """
        Find a customer by their phone number
        
        Args:
            phone_number: The customer's phone number
            
        Returns:
            The customer if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_all(self) -> List[Customer]:
        """
        Find all customers
        
        Returns:
            List of all customers
        """
        pass
    
    @abstractmethod
    async def delete(self, customer_id: CustomerId) -> bool:
        """
        Delete a customer
        
        Args:
            customer_id: The ID of the customer to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def exists_by_telegram_id(self, telegram_id: TelegramId) -> bool:
        """
        Check if a customer exists by Telegram ID
        
        Args:
            telegram_id: The Telegram ID to check
            
        Returns:
            True if customer exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def exists_by_phone_number(self, phone_number: PhoneNumber) -> bool:
        """
        Check if a customer exists by phone number
        
        Args:
            phone_number: The phone number to check
            
        Returns:
            True if customer exists, False otherwise
        """
        pass 