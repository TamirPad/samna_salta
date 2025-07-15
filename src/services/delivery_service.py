"""
Delivery service for managing delivery operations.
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging

from src.db.models import Order
from src.db.operations import get_all_orders

logger = logging.getLogger(__name__)

class DeliveryService:
    """Service for managing delivery operations"""

    DELIVERY_METHODS = ["pickup", "delivery"]
    DELIVERY_STATUSES = ["pending", "in_progress", "completed", "cancelled"]

    @staticmethod
    def validate_delivery_method(method: str) -> bool:
        """Validate delivery method"""
        return method in DeliveryService.DELIVERY_METHODS

    @staticmethod
    def validate_delivery_address(address: str) -> bool:
        """Validate delivery address"""
        return bool(address and len(address.strip()) > 0)

    @staticmethod
    def get_delivery_orders() -> List[Order]:
        """Get all delivery orders"""
        return [order for order in get_all_orders() if order.delivery_method == "delivery"]

    @staticmethod
    def get_pickup_orders() -> List[Order]:
        """Get all pickup orders"""
        return [order for order in get_all_orders() if order.delivery_method == "pickup"]

    @staticmethod
    def calculate_delivery_charge(address: str) -> float:
        """Calculate delivery charge based on address"""
        # Simple implementation - could be enhanced with distance calculation
        base_charge = 20.0  # Base delivery charge
        return base_charge

    @staticmethod
    def update_delivery_status(order_id: int, status: str) -> bool:
        """Update delivery status"""
        if status not in DeliveryService.DELIVERY_STATUSES:
            return False

        orders = get_all_orders()
        for order in orders:
            if order.id == order_id:
                order.status = status
                order.updated_at = datetime.now()
                return True
        return False

    @staticmethod
    def get_delivery_stats() -> Dict:
        """Get delivery statistics"""
        orders = get_all_orders()
        delivery_orders = [order for order in orders if order.delivery_method == "delivery"]
        pickup_orders = [order for order in orders if order.delivery_method == "pickup"]

        return {
            "total_deliveries": len(delivery_orders),
            "total_pickups": len(pickup_orders),
            "delivery_revenue": sum(order.delivery_charge for order in delivery_orders),
            "status_breakdown": {
                status: len([order for order in delivery_orders if order.status == status])
                for status in DeliveryService.DELIVERY_STATUSES
            }
        } 