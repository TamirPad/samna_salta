"""
SQLAlchemy implementation of CustomerRepository
"""

import logging
from contextlib import contextmanager

from src.domain.entities.customer_entity import Customer as DomainCustomer
from src.domain.repositories.customer_repository import CustomerRepository
from src.domain.value_objects.customer_id import CustomerId
from src.domain.value_objects.customer_name import CustomerName
from src.domain.value_objects.delivery_address import DeliveryAddress
from src.domain.value_objects.phone_number import PhoneNumber
from src.domain.value_objects.telegram_id import TelegramId
from src.infrastructure.database.models import Customer as SQLCustomer
from src.infrastructure.database.operations import (  # compatibility for tests
    get_session,
)

logger = logging.getLogger(__name__)


@contextmanager
def managed_session():  # type: ignore
    """Local session context to cooperate with tests' monkeypatching.

    Mirrors the behaviour of the global managed_session but relies on the *local*
    get_session symbol so that pytest's @patch decorator in repository tests can
    intercept DB access and assert commit/close calls.
    """
    session = get_session()
    try:
        yield session
    finally:
        session.close()


class SQLAlchemyCustomerRepository(CustomerRepository):
    """SQLAlchemy implementation of customer repository"""

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    async def find_by_telegram_id(
        self, telegram_id: TelegramId
    ) -> DomainCustomer | None:
        """Find customer by Telegram ID"""
        with managed_session() as session:
            sql_customer = (
                session.query(SQLCustomer)
                .filter(SQLCustomer.telegram_id == telegram_id.value)
                .first()
            )

            if not sql_customer:
                return None

            # Guard against invalid or empty full_name that would violate domain validation.
            if not sql_customer.full_name or not str(sql_customer.full_name).strip():
                # Treat as not found / incomplete record.
                self._logger.warning(
                    "Customer record with telegram_id %s has empty full_name; ignoring.",
                    telegram_id.value,
                )
                return None

            return self._map_to_domain(sql_customer)

    async def find_by_phone_number(
        self, phone_number: PhoneNumber
    ) -> DomainCustomer | None:
        """Find customer by phone number"""
        with managed_session() as session:
            sql_customer = (
                session.query(SQLCustomer)
                .filter(SQLCustomer.phone_number == phone_number.value)
                .first()
            )

            if not sql_customer:
                return None

            if not sql_customer.full_name or not str(sql_customer.full_name).strip():
                self._logger.warning(
                    "Customer record with phone_number %s has empty full_name; ignoring.",
                    phone_number.value,
                )
                return None

            return self._map_to_domain(sql_customer)

    async def save(self, customer: DomainCustomer) -> DomainCustomer:
        """Save customer to database"""
        with managed_session() as session:
            if customer.id is None:
                # If a record with the same telegram_id already exists (likely created with empty full_name),
                # update it instead of inserting a new one to avoid UNIQUE constraint errors.
                sql_customer = (
                    session.query(SQLCustomer)
                    .filter(SQLCustomer.telegram_id == customer.telegram_id.value)
                    .first()
                )

                if sql_customer is None:
                    # Create new customer
                    sql_customer = SQLCustomer(
                        telegram_id=customer.telegram_id.value,
                        full_name=customer.full_name.value,
                        phone_number=customer.phone_number.value,
                        delivery_address=customer.delivery_address.value
                        if customer.delivery_address
                        else None,
                    )
                    session.add(sql_customer)
                else:
                    # Update existing placeholder row
                    sql_customer.full_name = customer.full_name.value
                    sql_customer.phone_number = customer.phone_number.value
                    sql_customer.delivery_address = (
                        customer.delivery_address.value if customer.delivery_address else None
                    )

                session.commit()
                session.refresh(sql_customer)

                # Return updated domain entity with ID
                return self._map_to_domain(sql_customer)
            # Update existing customer
            sql_customer = (
                session.query(SQLCustomer)
                .filter(SQLCustomer.id == customer.id.value)
                .first()
            )

            if not sql_customer:
                raise ValueError(f"Customer with ID {customer.id.value} not found")

            sql_customer.telegram_id = customer.telegram_id.value
            sql_customer.full_name = customer.full_name.value
            sql_customer.phone_number = customer.phone_number.value
            sql_customer.delivery_address = (
                customer.delivery_address.value if customer.delivery_address else None
            )
            session.commit()
            session.refresh(sql_customer)

            return self._map_to_domain(sql_customer)

    async def delete(self, customer_id: CustomerId) -> bool:
        """Delete customer by ID"""
        with managed_session() as session:
            sql_customer = (
                session.query(SQLCustomer)
                .filter(SQLCustomer.id == customer_id.value)
                .first()
            )

            if not sql_customer:
                return False

            session.delete(sql_customer)
            session.commit()
            return True

    async def find_by_id(self, customer_id: CustomerId) -> DomainCustomer | None:
        """Find customer by ID"""
        with managed_session() as session:
            sql_customer = (
                session.query(SQLCustomer)
                .filter(SQLCustomer.id == customer_id.value)
                .first()
            )

            if not sql_customer:
                return None

            return self._map_to_domain(sql_customer)

    async def find_all(self) -> list[DomainCustomer]:
        """Find all customers"""
        with managed_session() as session:
            sql_customers = session.query(SQLCustomer).all()
            return [self._map_to_domain(customer) for customer in sql_customers]

    async def get_all_customers(self) -> list[DomainCustomer]:
        """Get all customers (alias for find_all for compatibility)"""
        return await self.find_all()

    async def exists_by_telegram_id(self, telegram_id: TelegramId) -> bool:
        """Check if customer exists by Telegram ID"""
        with managed_session() as session:
            exists = (
                session.query(SQLCustomer.id)
                .filter(SQLCustomer.telegram_id == telegram_id.value)
                .first()
                is not None
            )
            return exists

    async def exists_by_phone_number(self, phone_number: PhoneNumber) -> bool:
        """Check if customer exists by phone number"""
        with managed_session() as session:
            exists = (
                session.query(SQLCustomer.id)
                .filter(SQLCustomer.phone_number == phone_number.value)
                .first()
                is not None
            )
            return exists

    def _map_to_domain(self, sql_customer: SQLCustomer) -> DomainCustomer:
        """Map SQLAlchemy Customer to domain Customer"""
        # Debug logging to see what values we're getting
        self._logger.debug(f"Mapping customer: id={sql_customer.id}, telegram_id={sql_customer.telegram_id}, type={type(sql_customer.telegram_id)}")
        
        return DomainCustomer(
            id=CustomerId(sql_customer.id),
            telegram_id=TelegramId(sql_customer.telegram_id),
            full_name=CustomerName(sql_customer.full_name),
            phone_number=PhoneNumber(sql_customer.phone_number),
            delivery_address=DeliveryAddress(sql_customer.delivery_address)
            if sql_customer.delivery_address
            else None,
            created_at=sql_customer.created_at,
            updated_at=sql_customer.updated_at,
        )
