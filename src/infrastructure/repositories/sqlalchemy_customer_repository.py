"""
SQLAlchemy implementation of CustomerRepository
"""

import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ...domain.repositories.customer_repository import CustomerRepository
from ...domain.entities.customer_entity import Customer as DomainCustomer
from ...domain.value_objects.telegram_id import TelegramId
from ...domain.value_objects.phone_number import PhoneNumber
from ...domain.value_objects.customer_name import CustomerName
from ...domain.value_objects.customer_id import CustomerId
from ...domain.value_objects.delivery_address import DeliveryAddress
from ..database.models import Customer as SQLCustomer
from ..database.operations import get_session


logger = logging.getLogger(__name__)


class SQLAlchemyCustomerRepository(CustomerRepository):
    """SQLAlchemy implementation of customer repository"""
    
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def find_by_telegram_id(self, telegram_id: TelegramId) -> Optional[DomainCustomer]:
        """Find customer by Telegram ID"""
        try:
            session = get_session()
            try:
                sql_customer = session.query(SQLCustomer).filter(
                    SQLCustomer.telegram_id == telegram_id.value
                ).first()
                
                if not sql_customer:
                    return None
                
                return self._map_to_domain(sql_customer)
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding customer by telegram ID {telegram_id.value}: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error finding customer by telegram ID {telegram_id.value}: {e}")
            raise
    
    async def find_by_phone_number(self, phone_number: PhoneNumber) -> Optional[DomainCustomer]:
        """Find customer by phone number"""
        try:
            session = get_session()
            try:
                sql_customer = session.query(SQLCustomer).filter(
                    SQLCustomer.phone_number == phone_number.value
                ).first()
                
                if not sql_customer:
                    return None
                
                return self._map_to_domain(sql_customer)
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding customer by phone {phone_number.value}: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error finding customer by phone {phone_number.value}: {e}")
            raise
    
    async def save(self, customer: DomainCustomer) -> DomainCustomer:
        """Save customer to database"""
        try:
            session = get_session()
            try:
                if customer.id is None:
                    # Create new customer
                    sql_customer = SQLCustomer(
                        telegram_id=customer.telegram_id.value,
                        full_name=customer.full_name.value,
                        phone_number=customer.phone_number.value,
                        delivery_address=customer.delivery_address.value if customer.delivery_address else None
                    )
                    session.add(sql_customer)
                    session.commit()
                    session.refresh(sql_customer)
                    
                    # Return updated domain entity with ID
                    return self._map_to_domain(sql_customer)
                else:
                    # Update existing customer
                    sql_customer = session.query(SQLCustomer).filter(
                        SQLCustomer.id == customer.id.value
                    ).first()
                    
                    if not sql_customer:
                        raise ValueError(f"Customer with ID {customer.id.value} not found")
                    
                    sql_customer.telegram_id = customer.telegram_id.value
                    sql_customer.full_name = customer.full_name.value
                    sql_customer.phone_number = customer.phone_number.value
                    sql_customer.delivery_address = customer.delivery_address.value if customer.delivery_address else None
                    
                    session.commit()
                    session.refresh(sql_customer)
                    
                    return self._map_to_domain(sql_customer)
                    
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error saving customer: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error saving customer: {e}")
            raise
    
    async def delete(self, customer_id: CustomerId) -> bool:
        """Delete customer by ID"""
        try:
            session = get_session()
            try:
                sql_customer = session.query(SQLCustomer).filter(
                    SQLCustomer.id == customer_id.value
                ).first()
                
                if not sql_customer:
                    return False
                
                session.delete(sql_customer)
                session.commit()
                return True
                
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error deleting customer {customer_id.value}: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error deleting customer {customer_id.value}: {e}")
            raise
    
    async def find_by_id(self, customer_id: CustomerId) -> Optional[DomainCustomer]:
        """Find customer by ID"""
        try:
            session = get_session()
            try:
                sql_customer = session.query(SQLCustomer).filter(
                    SQLCustomer.id == customer_id.value
                ).first()
                
                if not sql_customer:
                    return None
                
                return self._map_to_domain(sql_customer)
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding customer by ID {customer_id.value}: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error finding customer by ID {customer_id.value}: {e}")
            raise
    
    async def find_all(self) -> List[DomainCustomer]:
        """Find all customers"""
        try:
            session = get_session()
            try:
                sql_customers = session.query(SQLCustomer).all()
                return [self._map_to_domain(customer) for customer in sql_customers]
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding all customers: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error finding all customers: {e}")
            raise
    
    async def get_all_customers(self) -> List[DomainCustomer]:
        """Get all customers (alias for find_all for compatibility)"""
        return await self.find_all()
    
    async def exists_by_telegram_id(self, telegram_id: TelegramId) -> bool:
        """Check if customer exists by Telegram ID"""
        try:
            session = get_session()
            try:
                exists = session.query(SQLCustomer).filter(
                    SQLCustomer.telegram_id == telegram_id.value
                ).first() is not None
                return exists
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error checking telegram ID {telegram_id.value}: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error checking telegram ID {telegram_id.value}: {e}")
            raise
    
    async def exists_by_phone_number(self, phone_number: PhoneNumber) -> bool:
        """Check if customer exists by phone number"""
        try:
            session = get_session()
            try:
                exists = session.query(SQLCustomer).filter(
                    SQLCustomer.phone_number == phone_number.value
                ).first() is not None
                return exists
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error checking phone number {phone_number.value}: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error checking phone number {phone_number.value}: {e}")
            raise
    
    def _map_to_domain(self, sql_customer: SQLCustomer) -> DomainCustomer:
        """Map SQLAlchemy model to domain entity"""
        return DomainCustomer(
            id=CustomerId(sql_customer.id) if sql_customer.id else None,
            telegram_id=TelegramId(sql_customer.telegram_id),
            full_name=CustomerName(sql_customer.full_name),
            phone_number=PhoneNumber(sql_customer.phone_number),
            delivery_address=DeliveryAddress(sql_customer.delivery_address) if sql_customer.delivery_address else None,
            is_admin=bool(sql_customer.is_admin)
        ) 