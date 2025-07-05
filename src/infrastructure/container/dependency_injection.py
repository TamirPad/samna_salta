"""
Dependency Injection Container

Manages the instantiation and lifecycle of dependencies for Clean Architecture.
"""

import logging
from typing import Any, Dict

from telegram import Bot

from ...application.use_cases.cart_management_use_case import CartManagementUseCase
from ...application.use_cases.customer_registration_use_case import (
    CustomerRegistrationUseCase,
)
from ...application.use_cases.order_analytics_use_case import OrderAnalyticsUseCase
from ...application.use_cases.order_creation_use_case import OrderCreationUseCase
from ...application.use_cases.order_status_management_use_case import (
    OrderStatusManagementUseCase,
)
from ...application.use_cases.product_catalog_use_case import ProductCatalogUseCase
from ...domain.repositories.cart_repository import CartRepository
from ...domain.repositories.customer_repository import CustomerRepository
from ...domain.repositories.order_repository import OrderRepository
from ...domain.repositories.product_repository import ProductRepository
from ..repositories.sqlalchemy_cart_repository import SQLAlchemyCartRepository
from ..repositories.sqlalchemy_customer_repository import SQLAlchemyCustomerRepository
from ..repositories.sqlalchemy_order_repository import SQLAlchemyOrderRepository
from ..repositories.sqlalchemy_product_repository import SQLAlchemyProductRepository
from ..services.admin_notification_service import AdminNotificationService
from ..services.customer_notification_service import CustomerNotificationService

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Dependency injection container for Clean Architecture

    Manages the instantiation and lifecycle of:
    - Repositories (Infrastructure layer)
    - Use Cases (Application layer)
    - Services and dependencies
    """

    def __init__(self, bot: Bot = None):
        self._instances: Dict[str, Any] = {}
        self._logger = logging.getLogger(self.__class__.__name__)
        self._bot = bot
        self._setup_dependencies()

    def _setup_dependencies(self):
        """Setup all dependencies and their relationships"""
        self._logger.info("Setting up dependency injection container...")

        # Infrastructure Layer - Repositories
        self._register_repositories()

        # Infrastructure Layer - Services
        self._register_services()

        # Application Layer - Use Cases
        self._register_use_cases()

        self._logger.info("Dependency injection container setup complete")

    def _register_repositories(self):
        """Register repository implementations"""
        self._instances["customer_repository"] = SQLAlchemyCustomerRepository()
        self._instances["product_repository"] = SQLAlchemyProductRepository()
        self._instances["cart_repository"] = SQLAlchemyCartRepository()
        self._instances["order_repository"] = SQLAlchemyOrderRepository()

        self._logger.debug("Repositories registered successfully")

    def _register_services(self):
        """Register service implementations"""
        if self._bot:
            self._instances["admin_notification_service"] = AdminNotificationService(
                bot=self._bot, customer_repository=self.get_customer_repository()
            )

            self._instances[
                "customer_notification_service"
            ] = CustomerNotificationService(
                bot=self._bot, customer_repository=self.get_customer_repository()
            )

            self._logger.debug("Services registered successfully")
        else:
            self._logger.warning(
                "Bot not provided, notification services not registered"
            )

    def _register_use_cases(self):
        """Register use case implementations with their dependencies"""
        # Customer Registration Use Case
        self._instances["customer_registration_use_case"] = CustomerRegistrationUseCase(
            customer_repository=self.get_customer_repository()
        )

        # Product Catalog Use Case
        self._instances["product_catalog_use_case"] = ProductCatalogUseCase(
            product_repository=self.get_product_repository()
        )

        # Cart Management Use Case
        self._instances["cart_management_use_case"] = CartManagementUseCase(
            cart_repository=self.get_cart_repository(),
            product_repository=self.get_product_repository(),
        )

        # Order Creation Use Case
        order_creation_kwargs = {
            "cart_repository": self.get_cart_repository(),
            "customer_repository": self.get_customer_repository(),
            "order_repository": self.get_order_repository(),
        }

        # Add admin notification service if available
        if "admin_notification_service" in self._instances:
            order_creation_kwargs[
                "admin_notification_service"
            ] = self.get_admin_notification_service()

        self._instances["order_creation_use_case"] = OrderCreationUseCase(
            **order_creation_kwargs
        )

        # Order Status Management Use Case
        status_management_kwargs = {
            "order_repository": self.get_order_repository(),
            "customer_repository": self.get_customer_repository(),
        }

        # Add notification services if available
        if "admin_notification_service" in self._instances:
            status_management_kwargs[
                "admin_notification_service"
            ] = self.get_admin_notification_service()
        if "customer_notification_service" in self._instances:
            status_management_kwargs[
                "customer_notification_service"
            ] = self.get_customer_notification_service()

        self._instances[
            "order_status_management_use_case"
        ] = OrderStatusManagementUseCase(**status_management_kwargs)

        # Order Analytics Use Case
        self._instances["order_analytics_use_case"] = OrderAnalyticsUseCase(
            order_repository=self.get_order_repository(),
            customer_repository=self.get_customer_repository(),
        )

        self._logger.debug("Use cases registered successfully")

    # Repository getters
    def get_customer_repository(self) -> CustomerRepository:
        """Get customer repository instance"""
        return self._instances["customer_repository"]

    def get_product_repository(self) -> ProductRepository:
        """Get product repository instance"""
        return self._instances["product_repository"]

    def get_cart_repository(self) -> CartRepository:
        """Get cart repository instance"""
        return self._instances["cart_repository"]

    def get_order_repository(self) -> OrderRepository:
        """Get order repository instance"""
        return self._instances["order_repository"]

    # Service getters
    def get_admin_notification_service(self) -> AdminNotificationService:
        """Get admin notification service instance"""
        return self._instances.get("admin_notification_service")

    def get_customer_notification_service(self) -> CustomerNotificationService:
        """Get customer notification service instance"""
        return self._instances.get("customer_notification_service")

    # Use Case getters
    def get_customer_registration_use_case(self) -> CustomerRegistrationUseCase:
        """Get customer registration use case instance"""
        return self._instances["customer_registration_use_case"]

    def get_product_catalog_use_case(self) -> ProductCatalogUseCase:
        """Get product catalog use case instance"""
        return self._instances["product_catalog_use_case"]

    def get_cart_management_use_case(self) -> CartManagementUseCase:
        """Get cart management use case instance"""
        return self._instances["cart_management_use_case"]

    def get_order_creation_use_case(self) -> OrderCreationUseCase:
        """Get order creation use case instance"""
        return self._instances["order_creation_use_case"]

    def get_order_status_management_use_case(self) -> OrderStatusManagementUseCase:
        """Get order status management use case instance"""
        return self._instances["order_status_management_use_case"]

    def get_order_analytics_use_case(self) -> OrderAnalyticsUseCase:
        """Get order analytics use case instance"""
        return self._instances["order_analytics_use_case"]

    def cleanup(self):
        """Cleanup resources when shutting down"""
        self._logger.info("Cleaning up dependency container...")
        # Add any cleanup logic here if needed
        self._instances.clear()


# Global container instance
_container: DependencyContainer = None


def get_container() -> DependencyContainer:
    """Get the global dependency container instance"""
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container


def initialize_container(bot: Bot = None) -> DependencyContainer:
    """Initialize the global dependency container with bot instance"""
    global _container
    if _container:
        _container.cleanup()
    _container = DependencyContainer(bot=bot)
    return _container


def reset_container():
    """Reset the global container (useful for testing)"""
    global _container
    if _container:
        _container.cleanup()
    _container = None
