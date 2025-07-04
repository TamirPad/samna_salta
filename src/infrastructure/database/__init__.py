"""
Database Infrastructure

Contains SQLAlchemy models and repository implementations.
"""

from .models import Base, Customer as CustomerModel, Product as ProductModel
from .operations import (
    init_db,
    get_engine,
    get_session
)

__all__ = [
    'Base',
    'CustomerModel', 
    'ProductModel',
    'init_db',
    'get_engine',
    'get_session'
] 