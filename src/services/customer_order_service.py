"""
Customer Order Service for tracking customer orders
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from src.db.operations import get_all_orders
from src.db.models import Order

logger = logging.getLogger(__name__)

class CustomerOrderService:
    """Service for customer order tracking"""

    def get_customer_active_orders(self, customer_telegram_id: int) -> List[Dict]:
        """Get active orders for a specific customer"""
        try:
            orders = get_all_orders()
            active_statuses = ["pending", "confirmed", "preparing", "ready"]
            
            customer_orders = [
                order for order in orders 
                if order.customer and order.customer.telegram_id == customer_telegram_id 
                and order.status in active_statuses
            ]
            
            # Convert to dict format
            result = []
            for order in customer_orders:
                result.append({
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "total": order.total,
                    "status": order.status,
                    "delivery_method": order.delivery_method,
                    "delivery_address": order.delivery_address,
                    "created_at": order.created_at,
                    "items": []
                })
                
                # Add order items if available
                if hasattr(order, 'order_items') and order.order_items:
                    for item in order.order_items:
                        result[-1]["items"].append({
                            "product_name": item.product_name,
                            "quantity": item.quantity,
                            "total_price": item.total_price,
                            "unit_price": item.unit_price
                        })
            
            logger.info("Retrieved %d active orders for customer %d", len(result), customer_telegram_id)
            return result
        except Exception as e:
            logger.error("Error getting customer active orders: %s", e)
            return []

    def get_customer_completed_orders(self, customer_telegram_id: int) -> List[Dict]:
        """Get completed orders for a specific customer"""
        try:
            orders = get_all_orders()
            completed_statuses = ["delivered", "completed"]
            
            customer_orders = [
                order for order in orders 
                if order.customer and order.customer.telegram_id == customer_telegram_id 
                and order.status in completed_statuses
            ]
            
            # Convert to dict format
            result = []
            for order in customer_orders:
                result.append({
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "total": order.total,
                    "status": order.status,
                    "delivery_method": order.delivery_method,
                    "delivery_address": order.delivery_address,
                    "created_at": order.created_at,
                    "items": []
                })
                
                # Add order items if available
                if hasattr(order, 'order_items') and order.order_items:
                    for item in order.order_items:
                        result[-1]["items"].append({
                            "product_name": item.product_name,
                            "quantity": item.quantity,
                            "total_price": item.total_price,
                            "unit_price": item.unit_price
                        })
            
            logger.info("Retrieved %d completed orders for customer %d", len(result), customer_telegram_id)
            return result
        except Exception as e:
            logger.error("Error getting customer completed orders: %s", e)
            return []

    def get_customer_order_by_id(self, order_id: int, customer_telegram_id: int) -> Optional[Dict]:
        """Get specific order details for a customer"""
        try:
            orders = get_all_orders()
            order = next((o for o in orders if o.id == order_id), None)
            
            if not order or not order.customer or order.customer.telegram_id != customer_telegram_id:
                return None
            
            # Convert to dict format
            result = {
                "order_id": order.id,
                "order_number": order.order_number,
                "total": order.total,
                "status": order.status,
                "delivery_method": order.delivery_method,
                "delivery_address": order.delivery_address,
                "created_at": order.created_at,
                "items": []
            }
            
            # Add order items if available
            if hasattr(order, 'order_items') and order.order_items:
                for item in order.order_items:
                    result["items"].append({
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "total_price": item.total_price,
                        "unit_price": item.unit_price
                    })
            
            logger.info("Retrieved order details for order #%s for customer %d", order.order_number, customer_telegram_id)
            return result
        except Exception as e:
            logger.error("Error getting customer order by ID %d: %s", order_id, e)
            return None 