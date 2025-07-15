"""
Admin service for admin operations and order management.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from src.db.operations import get_all_orders, update_order_status
from src.db.models import Order

logger = logging.getLogger(__name__)

class AdminService:
    """Service for admin operations and order management"""

    async def get_pending_orders(self) -> List[Dict]:
        """Get all pending orders for admin dashboard"""
        try:
            orders = get_all_orders()
            pending_orders = [order for order in orders if order.status == "pending"]
            
            # Convert to dict format expected by admin handler
            result = []
            for order in pending_orders:
                result.append({
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "customer_name": order.customer.full_name if order.customer else "Unknown",
                    "customer_phone": order.customer.phone_number if order.customer else "Unknown",
                    "total": order.total,
                    "status": order.status,
                    "created_at": order.created_at
                })
            
            logger.info("Retrieved %d pending orders", len(result))
            return result
        except Exception as e:
            logger.error("Error getting pending orders: %s", e)
            return []

    async def get_active_orders(self) -> List[Dict]:
        """Get all active orders (confirmed, preparing, ready) for admin dashboard"""
        try:
            orders = get_all_orders()
            active_statuses = ["confirmed", "preparing", "ready"]
            active_orders = [order for order in orders if order.status in active_statuses]
            
            # Convert to dict format expected by admin handler
            result = []
            for order in active_orders:
                result.append({
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "customer_name": order.customer.full_name if order.customer else "Unknown",
                    "customer_phone": order.customer.phone_number if order.customer else "Unknown",
                    "total": order.total,
                    "status": order.status,
                    "created_at": order.created_at
                })
            
            logger.info("Retrieved %d active orders", len(result))
            return result
        except Exception as e:
            logger.error("Error getting active orders: %s", e)
            return []

    async def get_all_orders(self) -> List[Dict]:
        """Get all orders for admin dashboard"""
        try:
            orders = get_all_orders()
            
            # Convert to dict format expected by admin handler
            result = []
            for order in orders:
                result.append({
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "customer_name": order.customer.full_name if order.customer else "Unknown",
                    "customer_phone": order.customer.phone_number if order.customer else "Unknown",
                    "total": order.total,
                    "status": order.status,
                    "created_at": order.created_at
                })
            
            logger.info("Retrieved %d total orders", len(result))
            return result
        except Exception as e:
            logger.error("Error getting all orders: %s", e)
            return []

    async def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """Get order details by ID for admin view"""
        try:
            orders = get_all_orders()
            order = next((o for o in orders if o.id == order_id), None)
            
            if not order:
                return None
            
            # Convert to dict format expected by admin handler
            result = {
                "order_id": order.id,
                "order_number": order.order_number,
                "customer_name": order.customer.full_name if order.customer else "Unknown",
                "customer_phone": order.customer.phone_number if order.customer else "Unknown",
                "total": order.total,
                "status": order.status,
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
            
            logger.info("Retrieved order details for order #%s", order.order_number)
            return result
        except Exception as e:
            logger.error("Error getting order by ID %d: %s", order_id, e)
            return None

    async def update_order_status(self, order_id: int, new_status: str, admin_telegram_id: int) -> bool:
        """Update order status by admin"""
        try:
            success = update_order_status(order_id, new_status)
            if success:
                logger.info("Order %d status updated to %s by admin %d", order_id, new_status, admin_telegram_id)
                
                # Send notification to customer about status update
                try:
                    from src.container import get_container
                    container = get_container()
                    notification_service = container.get_notification_service()
                    
                    # Get order to find customer
                    order_details = await self.get_order_by_id(order_id)
                    if order_details:
                        # In a real implementation, you'd get the customer's telegram_id
                        # For now, we'll just log the notification
                        logger.info("Customer notification: Order #%s status updated to %s", 
                                  order_details.get("order_number"), new_status)
                        
                except Exception as e:
                    logger.error("Failed to send customer notification: %s", e)
                
                return True
            else:
                logger.error("Failed to update order %d status to %s", order_id, new_status)
                return False
        except Exception as e:
            logger.error("Error updating order status: %s", e)
            return False

    async def get_business_analytics(self) -> Dict:
        """Get business analytics for admin dashboard"""
        try:
            orders = get_all_orders()
            
            # Calculate basic analytics
            total_orders = len(orders)
            total_revenue = sum(order.total for order in orders)
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
            
            # Status breakdown
            status_counts = {}
            for order in orders:
                status_counts[order.status] = status_counts.get(order.status, 0) + 1
            
            # Get pending and active counts
            pending_orders = await self.get_pending_orders()
            active_orders = await self.get_active_orders()
            
            return {
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "avg_order_value": avg_order_value,
                "pending_orders": len(pending_orders),
                "active_orders": len(active_orders),
                "status_breakdown": status_counts,
                "generated_at": datetime.now()
            }
        except Exception as e:
            logger.error("Error getting business analytics: %s", e)
            return {}

    def get_order_analytics(self) -> Dict:
        """Get order analytics for admin reports"""
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