"""
Simplified dependency injection container for the bot.
"""

import logging
from typing import Any, Optional

from telegram import Bot

from src.services.cart_service import CartService
from src.services.order_service import OrderService
from src.services.admin_service import AdminService
from src.services.delivery_service import DeliveryService
from src.services.notification_service import NotificationService
from src.services.customer_order_service import CustomerOrderService
from src.config import get_config

logger = logging.getLogger(__name__)

class Container:
    """Simple dependency injection container"""

    _instance: Optional['Container'] = None
    _bot: Optional[Bot] = None

    def __new__(cls) -> 'Container':
        if cls._instance is None:
            cls._instance = super(Container, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the container"""
        self.config = get_config()
        self.services = {}

    def set_bot(self, bot: Bot) -> None:
        """Set the bot instance"""
        Container._bot = bot

    def get_bot(self) -> Optional[Bot]:
        """Get the bot instance"""
        return Container._bot

    def get_cart_service(self) -> CartService:
        """Get cart service instance"""
        try:
            if 'cart_service' not in self.services:
                self.services['cart_service'] = CartService()
            return self.services['cart_service']
        except Exception as e:
            logger.error(f"Error getting cart service: {e}")
            raise

    def get_order_service(self) -> OrderService:
        """Get order service instance for customer operations"""
        try:
            if 'order_service' not in self.services:
                self.services['order_service'] = OrderService()
            return self.services['order_service']
        except Exception as e:
            logger.error(f"Error getting order service: {e}")
            raise

    def get_admin_service(self) -> AdminService:
        """Get admin service instance for admin operations"""
        try:
            if 'admin_service' not in self.services:
                self.services['admin_service'] = AdminService()
            return self.services['admin_service']
        except Exception as e:
            logger.error(f"Error getting admin service: {e}")
            raise

    def get_delivery_service(self) -> DeliveryService:
        """Get delivery service instance"""
        try:
            if 'delivery_service' not in self.services:
                self.services['delivery_service'] = DeliveryService()
            return self.services['delivery_service']
        except Exception as e:
            logger.error(f"Error getting delivery service: {e}")
            raise

    def get_notification_service(self) -> NotificationService:
        """Get notification service instance"""
        try:
            if 'notification_service' not in self.services:
                self.services['notification_service'] = NotificationService()
            return self.services['notification_service']
        except Exception as e:
            logger.error(f"Error getting notification service: {e}")
            raise

    def get_customer_order_service(self) -> CustomerOrderService:
        """Get customer order service instance"""
        try:
            if 'customer_order_service' not in self.services:
                self.services['customer_order_service'] = CustomerOrderService()
            return self.services['customer_order_service']
        except Exception as e:
            logger.error(f"Error getting customer order service: {e}")
            raise

    def get_config(self) -> Any:
        """Get configuration"""
        try:
            return self.config
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            raise

# Global container instance
container = Container()

def get_container() -> Container:
    """Get the global container instance"""
    try:
        return container
    except Exception as e:
        logger.error(f"Error getting container: {e}")
        raise

def initialize_container(bot: Bot) -> None:
    """Initialize the container with bot instance"""
    try:
        container.set_bot(bot)
        logger.info("Container initialized with bot instance")
    except Exception as e:
        logger.error(f"Error initializing container: {e}")
        raise 