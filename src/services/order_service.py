"""
Order service for managing order operations and product catalog.
"""

from datetime import datetime
from typing import Dict, List, Optional

from src.db.models import Order, Customer, Product
from src.db.operations import (
    create_order,
    get_all_orders,
    generate_order_number,
    get_all_products,
    get_product_by_name,
    get_product_by_id,
)
import logging
from src.utils.helpers import is_hilbeh_available

logger = logging.getLogger(__name__)

class OrderService:
    """Service for managing order operations and product catalog"""

    @staticmethod
    def create_order(
        customer_id: int,
        total_amount: float,
        delivery_method: str = "pickup",
        delivery_address: Optional[str] = None,
    ) -> Optional[Order]:
        """Create a new order"""
        return create_order(
            customer_id=customer_id,
            total_amount=total_amount,
            delivery_method=delivery_method,
            delivery_address=delivery_address,
        )

    @staticmethod
    def get_all_orders() -> List[Order]:
        """Get all orders"""
        return get_all_orders()

    @staticmethod
    def get_customer_orders(customer_id: int) -> List[Order]:
        """Get orders for a specific customer"""
        return [order for order in get_all_orders() if order.customer_id == customer_id]

    @staticmethod
    def get_orders_by_status(status: str) -> List[Order]:
        """Get orders by status"""
        return [order for order in get_all_orders() if order.status == status]

    @staticmethod
    def update_order_status(order_id: int, new_status: str) -> bool:
        """Update order status"""
        orders = get_all_orders()
        for order in orders:
            if order.id == order_id:
                order.status = new_status
                order.updated_at = datetime.now()
                return True
        return False

    @staticmethod
    def get_order_analytics() -> Dict:
        """Get order analytics"""
        orders = get_all_orders()
        total_orders = len(orders)
        total_revenue = sum(order.total for order in orders)
        status_counts = {}
        for order in orders:
            status_counts[order.status] = status_counts.get(order.status, 0) + 1

        return {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "status_breakdown": status_counts,
        }

    @staticmethod
    def generate_order_number() -> str:
        """Generate a unique order number"""
        return generate_order_number()

    # Product catalog methods
    @staticmethod
    def get_all_products() -> List[Product]:
        """Get all active products"""
        return get_all_products()

    @staticmethod
    def get_products_by_category(category: str) -> List[Product]:
        """Get products by category"""
        products = get_all_products()
        return [p for p in products if p.category == category and p.is_active]

    @staticmethod
    def get_product_by_name(name: str) -> Optional[Product]:
        """Get product by name"""
        return get_product_by_name(name)

    @staticmethod
    def get_product_by_id(product_id: int) -> Optional[Product]:
        """Get product by ID"""
        return get_product_by_id(product_id)

    @staticmethod
    def check_product_availability(product_name: str) -> Dict:
        """Check if a product is available"""
        product = get_product_by_name(product_name)
        
        if not product:
            return {"available": False, "reason": "Product not found"}

        if not product.is_active:
            return {"available": False, "reason": "Product is currently unavailable"}

        # Special handling for time-sensitive products
        if product.name.lower() == "hilbeh":
            if not is_hilbeh_available():
                return {"available": False, "reason": "Hilbeh is only available on specific days"}

        return {"available": True, "product": product} 