"""
SQLAlchemy implementation of ProductRepository
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ...domain.repositories.product_repository import ProductRepository
from ...domain.value_objects.product_id import ProductId
from ...domain.value_objects.product_name import ProductName
from ..database.models import Product as SQLProduct
from ..database.operations import get_session


logger = logging.getLogger(__name__)


class SQLAlchemyProductRepository(ProductRepository):
    """SQLAlchemy implementation of product repository"""
    
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def find_by_id(self, product_id: ProductId) -> Optional[SQLProduct]:
        """Find product by ID"""
        try:
            session = get_session()
            try:
                return session.query(SQLProduct).filter(
                    SQLProduct.id == product_id.value
                ).first()
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding product by ID {product_id.value}: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error finding product by ID {product_id.value}: {e}")
            raise
    
    async def find_by_name(self, name: ProductName) -> Optional[SQLProduct]:
        """Find product by name"""
        try:
            session = get_session()
            try:
                return session.query(SQLProduct).filter(
                    SQLProduct.name == name.value
                ).first()
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding product by name {name.value}: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error finding product by name {name.value}: {e}")
            raise
    
    async def find_by_category(self, category: str) -> List[SQLProduct]:
        """Find products by category"""
        try:
            session = get_session()
            try:
                return session.query(SQLProduct).filter(
                    SQLProduct.category == category
                ).all()
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding products by category {category}: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error finding products by category {category}: {e}")
            raise
    
    async def find_all_active(self) -> List[SQLProduct]:
        """Find all active products"""
        try:
            session = get_session()
            try:
                return session.query(SQLProduct).filter(
                    SQLProduct.is_active == True
                ).all()
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding all active products: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error finding all active products: {e}")
            raise
    
    async def save(self, product: SQLProduct) -> SQLProduct:
        """Save product to database"""
        try:
            session = get_session()
            try:
                session.add(product)
                session.commit()
                session.refresh(product)
                return product
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error saving product: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error saving product: {e}")
            raise
    
    async def delete(self, product_id: ProductId) -> bool:
        """Delete product by ID"""
        try:
            session = get_session()
            try:
                product = session.query(SQLProduct).filter(
                    SQLProduct.id == product_id.value
                ).first()
                
                if not product:
                    return False
                
                session.delete(product)
                session.commit()
                return True
                
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            self._logger.error(f"Database error deleting product {product_id.value}: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error deleting product {product_id.value}: {e}")
            raise 