"""
SQLAlchemy implementation of ProductRepository
"""

import logging

from src.domain.repositories.product_repository import ProductRepository
from src.domain.value_objects.product_id import ProductId
from src.domain.value_objects.product_name import ProductName
from src.infrastructure.database.models import Product as SQLProduct
from src.infrastructure.repositories.session_handler import managed_session

logger = logging.getLogger(__name__)


class SQLAlchemyProductRepository(ProductRepository):
    """SQLAlchemy implementation of product repository"""

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    async def find_by_id(self, product_id: ProductId) -> SQLProduct | None:
        """Find product by ID"""
        with managed_session() as session:
            return (
                session.query(SQLProduct)
                .filter(SQLProduct.id == product_id.value)
                .first()
            )

    async def find_by_name(self, name: ProductName) -> SQLProduct | None:
        """Find product by name"""
        with managed_session() as session:
            return (
                session.query(SQLProduct).filter(SQLProduct.name == name.value).first()
            )

    async def find_by_category(self, category: str) -> list[SQLProduct]:
        """Find products by category"""
        with managed_session() as session:
            return (
                session.query(SQLProduct).filter(SQLProduct.category == category).all()
            )

    async def find_all_active(self) -> list[SQLProduct]:
        """Find all active products"""
        with managed_session() as session:
            return session.query(SQLProduct).filter(SQLProduct.is_active).all()

    async def save(self, product: SQLProduct) -> SQLProduct:
        """Save product to database"""
        with managed_session() as session:
            session.add(product)
            session.flush()
            session.refresh(product)
            return product

    async def delete(self, product_id: ProductId) -> bool:
        """Delete product by ID"""
        with managed_session() as session:
            product = (
                session.query(SQLProduct)
                .filter(SQLProduct.id == product_id.value)
                .first()
            )

            if not product:
                return False

            session.delete(product)
            return True
