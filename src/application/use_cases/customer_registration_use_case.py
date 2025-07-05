"""
Customer Registration Use Case

Handles the business logic for customer registration through the Telegram bot.
"""

import logging
from dataclasses import dataclass

from src.domain.entities.customer_entity import Customer
from src.domain.repositories.customer_repository import CustomerRepository
from src.domain.value_objects.customer_name import CustomerName
from src.domain.value_objects.delivery_address import DeliveryAddress
from src.domain.value_objects.phone_number import PhoneNumber
from src.domain.value_objects.telegram_id import TelegramId

logger = logging.getLogger(__name__)


@dataclass
class CustomerRegistrationRequest:
    """Request object for customer registration"""

    telegram_id: int
    full_name: str
    phone_number: str
    delivery_address: str | None = None


@dataclass
class CustomerRegistrationResponse:
    """Response object for customer registration"""

    success: bool
    customer: Customer | None = None
    error_message: str | None = None
    is_returning_customer: bool = False


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

    async def execute(
        self, request: CustomerRegistrationRequest
    ) -> CustomerRegistrationResponse:
        """
        Execute customer registration use case

        Args:
            request: The registration request containing customer data

        Returns:
            CustomerRegistrationResponse with results
        """
        response: CustomerRegistrationResponse
        try:
            # Validate input data
            validation_result = self._validate_request(request)
            if not validation_result.success:
                response = validation_result
            else:
                # Create value objects with validation
                telegram_id = TelegramId(request.telegram_id)
                customer_name = CustomerName(request.full_name)
                phone_number = PhoneNumber(request.phone_number)
                delivery_address = (
                    DeliveryAddress(request.delivery_address)
                    if request.delivery_address
                    else None
                )

                # Check if customer already exists by phone number
                existing_customer = (
                    await self._customer_repository.find_by_phone_number(phone_number)
                )
                if existing_customer:
                    response = await self._handle_existing_customer(
                        existing_customer, telegram_id
                    )
                else:
                    # Check if someone else is using this Telegram ID
                    existing_telegram_user = (
                        await self._customer_repository.find_by_telegram_id(
                            telegram_id
                        )
                    )
                    if existing_telegram_user:
                        error_msg = (
                            "This Telegram account is already registered with a "
                            "different phone number"
                        )
                        self._logger.warning(
                            "Telegram ID %s already exists with different phone number",
                            telegram_id.value,
                        )
                        response = CustomerRegistrationResponse(
                            success=False, error_message=error_msg
                        )
                    else:
                        # Create new customer
                        new_customer = Customer(
                            id=None,  # Will be assigned by repository
                            telegram_id=telegram_id,
                            full_name=customer_name,
                            phone_number=phone_number,
                            delivery_address=delivery_address,
                        )

                        # Validate business rules
                        business_validation = self._validate_business_rules(
                            new_customer
                        )
                        if not business_validation.success:
                            response = business_validation
                        else:
                            # Save customer
                            saved_customer = await self._customer_repository.save(
                                new_customer
                            )

                            self._logger.info(
                                "New customer registered: %s", saved_customer.id
                            )
                            response = CustomerRegistrationResponse(
                                success=True,
                                customer=saved_customer,
                                is_returning_customer=False,
                            )

        except ValueError as e:
            self._logger.error("Validation error in customer registration: %s", e)
            response = CustomerRegistrationResponse(
                success=False, error_message=f"Invalid data: {str(e)}"
            )
        except (TypeError, AttributeError) as e:
            self._logger.error("Unexpected error in customer registration: %s", e)
            response = CustomerRegistrationResponse(
                success=False, error_message="Registration failed due to system error"
            )

        return response

    async def _handle_existing_customer(
        self, existing_customer: Customer, telegram_id: TelegramId
    ) -> CustomerRegistrationResponse:
        """Handle logic for existing customers."""
        if existing_customer.telegram_id.value != telegram_id.value:
            existing_customer.telegram_id = telegram_id
            updated_customer = await self._customer_repository.save(existing_customer)
            self._logger.info(
                "Updated telegram ID for existing customer %s",
                existing_customer.id,
            )
            return CustomerRegistrationResponse(
                success=True,
                customer=updated_customer,
                is_returning_customer=True,
            )

        self._logger.info("Returning customer recognized: %s", existing_customer.id)
        return CustomerRegistrationResponse(
            success=True, customer=existing_customer, is_returning_customer=True
        )

    def _validate_request(
        self, request: CustomerRegistrationRequest
    ) -> CustomerRegistrationResponse:
        """Validate the incoming request"""
        if not request.telegram_id or request.telegram_id <= 0:
            return CustomerRegistrationResponse(
                success=False, error_message="Invalid Telegram ID"
            )

        if not request.full_name or not request.full_name.strip():
            return CustomerRegistrationResponse(
                success=False, error_message="Full name is required"
            )

        if not request.phone_number or not request.phone_number.strip():
            return CustomerRegistrationResponse(
                success=False, error_message="Phone number is required"
            )

        return CustomerRegistrationResponse(success=True)

    def _validate_business_rules(
        self, customer: Customer
    ) -> CustomerRegistrationResponse:
        """Validate business rules for customer registration"""
        if not customer.can_place_order():
            return CustomerRegistrationResponse(
                success=False,
                error_message="Customer information incomplete for placing orders",
            )

        # Add any additional business rules here
        # e.g., age restrictions, geographic limitations, etc.

        return CustomerRegistrationResponse(success=True)

    async def find_customer_by_telegram_id(
        self, telegram_id: int
    ) -> Customer | None:
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
        except ValueError as e:
            self._logger.error(
                "Error finding customer by telegram ID %s: %s", telegram_id, e
            )
            return None
