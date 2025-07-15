"""
Order service for customer order operations.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from src.db.models import Order, Customer, Product
from src.db.operations import (
    create_order_with_items,
    get_customer_by_telegram_id,
    generate_order_number,
    get_all_products,
    get_product_by_name,
    get_product_by_id,
)
from src.utils.helpers import is_hilbeh_available

logger = logging.getLogger(__name__)

class OrderService:
    """Service for customer order operations"""

    async def create_order(self, telegram_id: int, cart_items: List[Dict]) -> Dict:
        """Create a new order from cart items"""
        try:
            # Get customer
            customer = get_customer_by_telegram_id(telegram_id)
            if not customer:
                return {
                    "success": False,
                    "error": "Customer not found. Please register first."
                }
            
            # Calculate total
            total = sum(item.get("price", 0) * item.get("quantity", 1) for item in cart_items)
            
            # Generate order number
            order_number = generate_order_number()
            
            # Create order with items
            order = create_order_with_items(
                customer_id=customer.id,
                order_number=order_number,
                total_amount=total,
                items=cart_items
            )
            
            if order:
                logger.info("Successfully created order #%s for customer %s", order_number, customer.id)
                
                # Send admin notification
                try:
                    from src.container import get_container
                    container = get_container()
                    notification_service = container.get_notification_service()
                    
                    # Prepare order data for notification
                    order_data = {
                        "id": order.id,
                        "order_number": order_number,
                        "customer_name": customer.full_name,
                        "customer_phone": customer.phone_number,
                        "items": cart_items,
                        "total": total,
                        "delivery_method": order.delivery_method,
                        "delivery_address": order.delivery_address,
                        "customer_telegram_id": telegram_id
                    }
                    
                    # Send admin notification
                    await notification_service.notify_new_order(order_data)
                    logger.info("Admin notification sent for order #%s", order_number)
                    
                except Exception as e:
                    logger.error("Failed to send admin notification: %s", e)
                    # Don't fail the order creation if notification fails
                
                return {
                    "success": True,
                    "order_number": order_number,
                    "total": total,
                    "order": order
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create order"
                }
                
        except Exception as e:
            logger.error("Exception creating order: %s", e)
            return {
                "success": False,
                "error": str(e)
            }

    def get_customer_orders(self, customer_id: int) -> List[Order]:
        """Get orders for a specific customer"""
        from src.db.operations import get_all_orders
        orders = get_all_orders()
        return [order for order in orders if order.customer_id == customer_id]

    def get_order_by_number(self, order_number: str) -> Optional[Order]:
        """Get order by order number"""
        from src.db.operations import get_all_orders
        orders = get_all_orders()
        return next((order for order in orders if order.order_number == order_number), None)

    # Product catalog methods
    def get_all_products(self) -> List[Product]:
        """Get all active products"""
        return get_all_products()

    def get_products_by_category(self, category: str) -> List[Product]:
        """Get products by category"""
        products = get_all_products()
        return [p for p in products if p.category == category and p.is_active]

    def get_product_by_name(self, name: str) -> Optional[Product]:
        """Get product by name"""
        return get_product_by_name(name)

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        return get_product_by_id(product_id)

    def check_product_availability(self, product_name: str) -> Dict:
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