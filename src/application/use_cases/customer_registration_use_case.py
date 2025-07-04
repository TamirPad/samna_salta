"""
Customer Registration Use Case

Handles the business logic for customer registration through the Telegram bot.
"""

import logging
from typing import Optional

from ...domain.entities.customer_entity import Customer
from ...domain.value_objects.telegram_id import TelegramId
from ...domain.value_objects.customer_name import CustomerName
from ...domain.value_objects.phone_number import PhoneNumber
from ...domain.value_objects.delivery_address import DeliveryAddress
from ...domain.repositories.customer_repository import CustomerRepository


logger = logging.getLogger(__name__)


class CustomerRegistrationRequest:
    """Request object for customer registration"""
    
    def __init__(
        self,
        telegram_id: int,
        full_name: str,
        phone_number: str,
        delivery_address: Optional[str] = None
    ):
        self.telegram_id = telegram_id
        self.full_name = full_name
        self.phone_number = phone_number
        self.delivery_address = delivery_address


class CustomerRegistrationResponse:
    """Response object for customer registration"""
    
    def __init__(
        self,
        success: bool,
        customer: Optional[Customer] = None,
        error_message: Optional[str] = None,
        is_returning_customer: bool = False
    ):
        self.success = success
        self.customer = customer
        self.error_message = error_message
        self.is_returning_customer = is_returning_customer


class CustomerRegistrationUseCase:
    """
    Use case for customer registration and authentication
    
    Handles:
    1. New customer registration
    2. Returning customer recognition
    3. Data validation
    4. Business rule enforcement
    """
    
    def __init__(self, customer_repository: CustomerRepository):
        self._customer_repository = customer_repository
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def execute(self, request: CustomerRegistrationRequest) -> CustomerRegistrationResponse:
        """
        Execute customer registration use case
        
        Args:
            request: The registration request containing customer data
            
        Returns:
            CustomerRegistrationResponse with results
        """
        try:
            # Validate input data
            validation_result = self._validate_request(request)
            if not validation_result.success:
                return validation_result
            
            # Create value objects with validation
            telegram_id = TelegramId(request.telegram_id)
            customer_name = CustomerName(request.full_name)
            phone_number = PhoneNumber(request.phone_number)
            delivery_address = None
            if request.delivery_address:
                delivery_address = DeliveryAddress(request.delivery_address)
            
            # Check if customer already exists by phone number
            existing_customer = await self._customer_repository.find_by_phone_number(phone_number)
            if existing_customer:
                # Update telegram ID if it changed
                if existing_customer.telegram_id.value != telegram_id.value:
                    existing_customer.telegram_id = telegram_id
                    updated_customer = await self._customer_repository.save(existing_customer)
                    self._logger.info(
                        f"Updated telegram ID for existing customer {existing_customer.id}"
                    )
                    return CustomerRegistrationResponse(
                        success=True,
                        customer=updated_customer,
                        is_returning_customer=True
                    )
                
                self._logger.info(f"Returning customer recognized: {existing_customer.id}")
                return CustomerRegistrationResponse(
                    success=True,
                    customer=existing_customer,
                    is_returning_customer=True
                )
            
            # Check if someone else is using this Telegram ID
            existing_telegram_user = await self._customer_repository.find_by_telegram_id(telegram_id)
            if existing_telegram_user:
                error_msg = "This Telegram account is already registered with a different phone number"
                self._logger.warning(
                    f"Telegram ID {telegram_id.value} already exists with different phone number"
                )
                return CustomerRegistrationResponse(
                    success=False,
                    error_message=error_msg
                )
            
            # Create new customer
            new_customer = Customer(
                id=None,  # Will be assigned by repository
                telegram_id=telegram_id,
                full_name=customer_name,
                phone_number=phone_number,
                delivery_address=delivery_address
            )
            
            # Validate business rules
            business_validation = self._validate_business_rules(new_customer)
            if not business_validation.success:
                return business_validation
            
            # Save customer
            saved_customer = await self._customer_repository.save(new_customer)
            
            self._logger.info(f"New customer registered: {saved_customer.id}")
            return CustomerRegistrationResponse(
                success=True,
                customer=saved_customer,
                is_returning_customer=False
            )
            
        except ValueError as e:
            self._logger.error(f"Validation error in customer registration: {e}")
            return CustomerRegistrationResponse(
                success=False,
                error_message=f"Invalid data: {str(e)}"
            )
        except Exception as e:
            self._logger.error(f"Unexpected error in customer registration: {e}")
            return CustomerRegistrationResponse(
                success=False,
                error_message="Registration failed due to system error"
            )
    
    def _validate_request(self, request: CustomerRegistrationRequest) -> CustomerRegistrationResponse:
        """Validate the incoming request"""
        if not request.telegram_id or request.telegram_id <= 0:
            return CustomerRegistrationResponse(
                success=False,
                error_message="Invalid Telegram ID"
            )
        
        if not request.full_name or not request.full_name.strip():
            return CustomerRegistrationResponse(
                success=False,
                error_message="Full name is required"
            )
        
        if not request.phone_number or not request.phone_number.strip():
            return CustomerRegistrationResponse(
                success=False,
                error_message="Phone number is required"
            )
        
        return CustomerRegistrationResponse(success=True)
    
    def _validate_business_rules(self, customer: Customer) -> CustomerRegistrationResponse:
        """Validate business rules for customer registration"""
        if not customer.can_place_order():
            return CustomerRegistrationResponse(
                success=False,
                error_message="Customer information incomplete for placing orders"
            )
        
        # Add any additional business rules here
        # e.g., age restrictions, geographic limitations, etc.
        
        return CustomerRegistrationResponse(success=True)
    
    async def find_customer_by_telegram_id(self, telegram_id: int) -> Optional[Customer]:
        """
        Find existing customer by Telegram ID
        
        Args:
            telegram_id: The Telegram user ID
            
        Returns:
            Customer if found, None otherwise
        """
        try:
            telegram_id_vo = TelegramId(telegram_id)
            return await self._customer_repository.find_by_telegram_id(telegram_id_vo)
        except Exception as e:
            self._logger.error(f"Error finding customer by telegram ID {telegram_id}: {e}")
            return None 