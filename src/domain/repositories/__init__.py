"""
Domain repository interfaces

Contains abstract repository interfaces that define contracts for data access.
These follow the Repository pattern and Dependency Inversion principle.
"""

from .customer_repository import CustomerRepository

__all__ = [
    'CustomerRepository'
] 