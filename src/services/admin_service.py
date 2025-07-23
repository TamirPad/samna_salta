"""
Admin service for admin operations and order management.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta
from collections import defaultdict, Counter
from dataclasses import dataclass

from src.db.operations import (
    get_all_orders, 
    update_order_status, 
    get_all_products_admin,
    create_product,
    update_product,
    delete_product,
    get_product_categories,
    get_products_by_category,
    get_product_by_id
)
from src.db.models import Order
from src.utils.multilingual_content import MultilingualContentManager

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsPeriod:
    """Represents a time period for analytics"""
    start_date: date
    end_date: date
    label: str


@dataclass
class ProductAnalytics:
    """Product performance analytics"""
    product_name: str
    total_orders: int
    total_quantity: int
    total_revenue: float
    avg_order_value: float
    popularity_rank: int


@dataclass
class CustomerAnalytics:
    """Customer behavior analytics"""
    customer_id: int
    customer_name: str
    total_orders: int
    total_spent: float
    avg_order_value: float
    last_order_date: Optional[datetime]
    favorite_products: List[str]


@dataclass
class RevenueAnalytics:
    """Revenue and financial analytics"""
    total_revenue: float
    avg_order_value: float
    total_orders: int
    delivery_revenue: float
    pickup_revenue: float
    delivery_orders: int
    pickup_orders: int
    revenue_by_day: Dict[str, float]
    revenue_by_week: Dict[str, float]


@dataclass
class OrderAnalytics:
    """Order processing analytics"""
    total_orders: int
    pending_orders: int
    active_orders: int
    completed_orders: int
    cancelled_orders: int
    avg_processing_time: Optional[float]
    status_distribution: Dict[str, int]
    orders_by_day: Dict[str, int]


class AnalyticsService:
    """Enhanced analytics service for business intelligence"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _get_orders_in_period(self, start_date: date, end_date: date) -> List[Order]:
        """Get orders within a specific date range"""
        try:
            all_orders = get_all_orders()
            return [
                order for order in all_orders
                if order.created_at and start_date <= order.created_at.date() <= end_date
            ]
        except Exception as e:
            self.logger.error("Error getting orders in period: %s", e)
            return []
    
    def _calculate_processing_time(self, order: Order) -> Optional[float]:
        """Calculate order processing time in hours"""
        if not order.updated_at or order.status not in ['delivered', 'cancelled']:
            return None
        
        processing_time = order.updated_at - order.created_at
        return processing_time.total_seconds() / 3600  # Convert to hours
    
    async def get_comprehensive_analytics(self, period_days: int = 30) -> Dict:
        """Get comprehensive business analytics for the specified period"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=period_days)
            
            orders = self._get_orders_in_period(start_date, end_date)
            
            # Revenue analytics
            revenue_analytics = self._calculate_revenue_analytics(orders, start_date, end_date)
            
            # Order analytics
            order_analytics = self._calculate_order_analytics(orders, start_date, end_date)
            
            # Product analytics
            product_analytics = self._calculate_product_analytics(orders)
            
            # Customer analytics
            customer_analytics = self._calculate_customer_analytics(orders)
            
            # Time-based trends
            trends = self._calculate_trends(orders, start_date, end_date)
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": period_days
                },
                "revenue": revenue_analytics.__dict__,
                "orders": order_analytics.__dict__,
                "products": [p.__dict__ for p in product_analytics],
                "customers": [c.__dict__ for c in customer_analytics],
                "trends": trends,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Error getting comprehensive analytics: %s", e)
            return {}
    
    def _calculate_revenue_analytics(self, orders: List[Order], start_date: date, end_date: date) -> RevenueAnalytics:
        """Calculate revenue and financial metrics"""
        total_revenue = sum(order.total for order in orders)
        total_orders = len(orders)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Delivery vs pickup analysis
        delivery_orders = [o for o in orders if o.delivery_method == 'delivery']
        pickup_orders = [o for o in orders if o.delivery_method == 'pickup']
        
        delivery_revenue = sum(o.total for o in delivery_orders)
        pickup_revenue = sum(o.total for o in pickup_orders)
        
        # Daily revenue breakdown
        revenue_by_day = defaultdict(float)
        for order in orders:
            day_key = order.created_at.strftime('%Y-%m-%d')
            revenue_by_day[day_key] += order.total
        
        # Weekly revenue breakdown
        revenue_by_week = defaultdict(float)
        for order in orders:
            week_key = order.created_at.strftime('%Y-W%U')
            revenue_by_week[week_key] += order.total
        
        return RevenueAnalytics(
            total_revenue=total_revenue,
            avg_order_value=avg_order_value,
            total_orders=total_orders,
            delivery_revenue=delivery_revenue,
            pickup_revenue=pickup_revenue,
            delivery_orders=len(delivery_orders),
            pickup_orders=len(pickup_orders),
            revenue_by_day=dict(revenue_by_day),
            revenue_by_week=dict(revenue_by_week)
        )
    
    def _calculate_order_analytics(self, orders: List[Order], start_date: date, end_date: date) -> OrderAnalytics:
        """Calculate order processing metrics"""
        total_orders = len(orders)
        
        # Status distribution
        status_counts = Counter(order.status for order in orders)
        
        # Processing time analysis
        processing_times = []
        for order in orders:
            processing_time = self._calculate_processing_time(order)
            if processing_time is not None:
                processing_times.append(processing_time)
        
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else None
        
        # Daily order breakdown
        orders_by_day = defaultdict(int)
        for order in orders:
            day_key = order.created_at.strftime('%Y-%m-%d')
            orders_by_day[day_key] += 1
        
        return OrderAnalytics(
            total_orders=total_orders,
            pending_orders=status_counts.get('pending', 0),
            active_orders=status_counts.get('confirmed', 0) + status_counts.get('preparing', 0) + status_counts.get('ready', 0),
            completed_orders=status_counts.get('delivered', 0),
            cancelled_orders=status_counts.get('cancelled', 0),
            avg_processing_time=avg_processing_time,
            status_distribution=dict(status_counts),
            orders_by_day=dict(orders_by_day)
        )
    
    def _calculate_product_analytics(self, orders: List[Order]) -> List[ProductAnalytics]:
        """Calculate product performance metrics"""
        product_stats = defaultdict(lambda: {
            'total_orders': 0,
            'total_quantity': 0,
            'total_revenue': 0.0,
            'order_count': 0
        })
        
        # Aggregate product data from order items
        for order in orders:
            if hasattr(order, 'order_items') and order.order_items:
                for item in order.order_items:
                    product_name = item.product_name
                    product_stats[product_name]['total_orders'] += 1
                    product_stats[product_name]['total_quantity'] += item.quantity
                    product_stats[product_name]['total_revenue'] += item.total_price
                    product_stats[product_name]['order_count'] += 1
        
        # Convert to ProductAnalytics objects
        products = []
        for product_name, stats in product_stats.items():
            avg_order_value = stats['total_revenue'] / stats['order_count'] if stats['order_count'] > 0 else 0
            products.append(ProductAnalytics(
                product_name=product_name,
                total_orders=stats['total_orders'],
                total_quantity=stats['total_quantity'],
                total_revenue=stats['total_revenue'],
                avg_order_value=avg_order_value,
                popularity_rank=0  # Will be set below
            ))
        
        # Sort by total revenue and assign popularity rank
        products.sort(key=lambda x: x.total_revenue, reverse=True)
        for i, product in enumerate(products):
            product.popularity_rank = i + 1
        
        return products
    
    def _calculate_customer_analytics(self, orders: List[Order]) -> List[CustomerAnalytics]:
        """Calculate customer behavior metrics"""
        customer_stats = defaultdict(lambda: {
            'orders': [],
            'total_spent': 0.0,
            'favorite_products': Counter()
        })
        
        # Aggregate customer data
        for order in orders:
            if order.customer:
                customer_id = order.customer.id
                customer_stats[customer_id]['orders'].append(order)
                customer_stats[customer_id]['total_spent'] += order.total
                
                # Track favorite products
                if hasattr(order, 'order_items') and order.order_items:
                    for item in order.order_items:
                        customer_stats[customer_id]['favorite_products'][item.product_name] += item.quantity
        
        # Convert to CustomerAnalytics objects
        customers = []
        for customer_id, stats in customer_stats.items():
            orders_list = stats['orders']
            total_orders = len(orders_list)
            avg_order_value = stats['total_spent'] / total_orders if total_orders > 0 else 0
            last_order_date = max(o.created_at for o in orders_list) if orders_list else None
            
            # Get top 3 favorite products
            favorite_products = [product for product, _ in stats['favorite_products'].most_common(3)]
            
            # Get customer name from first order
            customer_name = orders_list[0].customer.full_name if orders_list else "Unknown"
            
            customers.append(CustomerAnalytics(
                customer_id=customer_id,
                customer_name=customer_name,
                total_orders=total_orders,
                total_spent=stats['total_spent'],
                avg_order_value=avg_order_value,
                last_order_date=last_order_date,
                favorite_products=favorite_products
            ))
        
        # Sort by total spent
        customers.sort(key=lambda x: x.total_spent, reverse=True)
        return customers
    
    def _calculate_trends(self, orders: List[Order], start_date: date, end_date: date) -> Dict:
        """Calculate business trends"""
        if not orders:
            return {}
        
        # Revenue trend
        daily_revenue = defaultdict(float)
        for order in orders:
            day_key = order.created_at.strftime('%Y-%m-%d')
            daily_revenue[day_key] += order.total
        
        # Order volume trend
        daily_orders = defaultdict(int)
        for order in orders:
            day_key = order.created_at.strftime('%Y-%m-%d')
            daily_orders[day_key] += 1
        
        # Average order value trend
        daily_avg = {}
        for day in daily_revenue:
            if daily_orders[day] > 0:
                daily_avg[day] = daily_revenue[day] / daily_orders[day]
        
        return {
            "daily_revenue": dict(daily_revenue),
            "daily_orders": dict(daily_orders),
            "daily_avg_order_value": daily_avg
        }
    
    async def get_quick_analytics(self) -> Dict:
        """Get quick analytics for dashboard overview"""
        try:
            all_orders = get_all_orders()
            
            # Current status counts
            status_counts = Counter(order.status for order in all_orders)
            
            # Today's metrics
            today = date.today()
            today_orders = [o for o in all_orders if o.created_at and o.created_at.date() == today]
            today_revenue = sum(o.total for o in today_orders)
            
            # This week's metrics
            week_start = today - timedelta(days=today.weekday())
            week_orders = [o for o in all_orders if o.created_at and o.created_at.date() >= week_start]
            week_revenue = sum(o.total for o in week_orders)
            
            # This month's metrics
            month_start = today.replace(day=1)
            month_orders = [o for o in all_orders if o.created_at and o.created_at.date() >= month_start]
            month_revenue = sum(o.total for o in month_orders)
            
            return {
                "current_status": dict(status_counts),
                "today": {
                    "orders": len(today_orders),
                    "revenue": today_revenue
                },
                "this_week": {
                    "orders": len(week_orders),
                    "revenue": week_revenue
                },
                "this_month": {
                    "orders": len(month_orders),
                    "revenue": month_revenue
                },
                "total": {
                    "orders": len(all_orders),
                    "revenue": sum(o.total for o in all_orders)
                }
            }
            
        except Exception as e:
            self.logger.error("Error getting quick analytics: %s", e)
            return {}


class AdminService:
    """Service for admin operations and order management"""

    def __init__(self):
        self.analytics_service = AnalyticsService()

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
                    "customer_name": order.customer.name if order.customer else "Unknown",
                    "customer_phone": order.customer.phone if order.customer else "Unknown",
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
                    "customer_name": order.customer.name if order.customer else "Unknown",
                    "customer_phone": order.customer.phone if order.customer else "Unknown",
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
                    "customer_name": order.customer.name if order.customer else "Unknown",
                    "customer_phone": order.customer.phone if order.customer else "Unknown",
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
                "customer_name": order.customer.name if order.customer else "Unknown",
                "customer_phone": order.customer.phone if order.customer else "Unknown",
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
                    
                    # Get order with customer information to find customer's telegram_id
                    from src.db.operations import get_all_orders
                    orders = get_all_orders()
                    order = next((o for o in orders if o.id == order_id), None)
                    
                    if order and order.customer:
                        customer_telegram_id = order.customer.telegram_id
                        order_number = order.order_number
                        delivery_method = order.delivery_method
                        
                        # Send actual notification to customer
                        await notification_service.notify_order_status_update(
                            order_id=order_number,
                            new_status=new_status,
                            customer_chat_id=customer_telegram_id,
                            delivery_method=delivery_method
                        )
                        
                        logger.info("Customer notification sent: Order #%s status updated to %s for customer %d", 
                                  order_number, new_status, customer_telegram_id)
                    else:
                        logger.warning("Could not find order or customer for notification: order_id=%d", order_id)
                        
                except Exception as e:
                    logger.error("Failed to send customer notification: %s", e)
                
                return True
            else:
                logger.error("Failed to update order %d status to %s", order_id, new_status)
                return False
        except Exception as e:
            logger.error("Error updating order status: %s", e)
            return False

    async def delete_order(self, order_id: int, admin_telegram_id: int) -> bool:
        """Delete an order by admin"""
        try:
            from src.db.operations import delete_order as db_delete_order
            
            # Get order details before deletion for logging
            order_info = await self.get_order_by_id(order_id)
            if not order_info:
                logger.warning("Order %d not found for deletion by admin %d", order_id, admin_telegram_id)
                return False
            
            # Perform the deletion
            success = db_delete_order(order_id)
            if success:
                logger.info(
                    "Order %d deleted by admin %d: order_number=%s, customer=%s, total=%.2f",
                    order_id, admin_telegram_id, order_info.get("order_number"), 
                    order_info.get("customer_name"), order_info.get("total", 0)
                )
                
                # Send notification to customer about order cancellation
                try:
                    from src.container import get_container
                    container = get_container()
                    notification_service = container.get_notification_service()
                    
                    # Get customer telegram_id from order info
                    from src.db.operations import get_all_orders
                    orders = get_all_orders()
                    order = next((o for o in orders if o.id == order_id), None)
                    
                    if order and order.customer:
                        customer_telegram_id = order.customer.telegram_id
                        order_number = order.order_number
                        
                        # Send notification to customer about order cancellation
                        await notification_service.notify_order_cancelled(
                            order_id=order_number,
                            customer_chat_id=customer_telegram_id
                        )
                        
                        logger.info("Customer notification sent: Order #%s cancelled for customer %d", 
                                  order_number, customer_telegram_id)
                    else:
                        logger.warning("Could not find order or customer for cancellation notification: order_id=%d", order_id)
                        
                except Exception as e:
                    logger.error("Failed to send customer cancellation notification: %s", e)
                
                return True
            else:
                logger.error("Failed to delete order %d by admin %d", order_id, admin_telegram_id)
                return False
        except Exception as e:
            logger.error("Error deleting order %d: %s", order_id, e)
            return False

    async def get_business_analytics(self) -> Dict:
        """Get enhanced business analytics for admin dashboard"""
        try:
            # Get comprehensive analytics for last 30 days
            analytics = await self.analytics_service.get_comprehensive_analytics(period_days=30)
            
            # Also get quick analytics for current overview
            quick_analytics = await self.analytics_service.get_quick_analytics()
            
            # Combine both for a complete picture
            result = {
                **analytics,
                "quick_overview": quick_analytics,
                "generated_at": datetime.now()
            }
            
            logger.info("Generated comprehensive business analytics")
            return result
        except Exception as e:
            logger.error("Error getting business analytics: %s", e)
            return {}

    async def get_today_orders(self) -> List[Dict]:
        """Get orders created today"""
        try:
            from datetime import datetime, date
            orders = get_all_orders()
            today = date.today()
            
            today_orders = [
                order for order in orders 
                if order.created_at and order.created_at.date() == today
            ]
            
            # Convert to dict format
            result = []
            for order in today_orders:
                result.append({
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "customer_name": order.customer.name if order.customer else "Unknown",
                    "customer_phone": order.customer.phone if order.customer else "Unknown",
                    "total": order.total,
                    "status": order.status,
                    "created_at": order.created_at
                })
            
            logger.info("Retrieved %d orders from today", len(result))
            return result
        except Exception as e:
            logger.error("Error getting today's orders: %s", e)
            return []

    async def get_completed_orders(self) -> List[Dict]:
        """Get all completed (delivered) orders for admin dashboard"""
        try:
            orders = get_all_orders()
            completed_orders = [order for order in orders if order.status == "delivered"]
            # Convert to dict format expected by admin handler
            result = []
            for order in completed_orders:
                result.append({
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "customer_name": order.customer.name if order.customer else "Unknown",
                    "customer_phone": order.customer.phone if order.customer else "Unknown",
                    "total": order.total,
                    "status": order.status,
                    "created_at": order.created_at
                })
            logger.info("Retrieved %d completed orders", len(result))
            return result
        except Exception as e:
            logger.error("Error getting completed orders: %s", e)
            return []

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

    async def get_all_customers(self) -> List[Dict]:
        """Get all customers for admin dashboard"""
        try:
            from src.db.operations import get_all_customers
            customers = get_all_customers()
            
            # Convert to dict format expected by admin handler
            result = []
            for customer in customers:
                result.append({
                    "customer_id": customer.id,
                    "telegram_id": customer.telegram_id,
                    "full_name": customer.name,
                    "phone_number": customer.phone,
                    "delivery_address": customer.delivery_address,
                    "language": customer.language,
                    "created_at": customer.created_at,
                    "total_orders": 0,  # Will be calculated below
                    "total_spent": 0.0  # Will be calculated below
                })
            
            # Calculate order statistics for each customer
            orders = get_all_orders()
            for customer in result:
                customer_orders = [order for order in orders if order.customer_id == customer["customer_id"]]
                customer["total_orders"] = len(customer_orders)
                customer["total_spent"] = sum(order.total for order in customer_orders)
            
            # Sort by total spent (most valuable customers first)
            result.sort(key=lambda x: x["total_spent"], reverse=True)
            
            logger.info("Retrieved %d customers", len(result))
            return result
        except Exception as e:
            logger.error("Error getting all customers: %s", e)
            return []

    # Menu Management Methods
    async def get_all_products_for_admin(self) -> List[Dict]:
        """Get all products (including inactive) for admin management"""
        try:
            products = get_all_products_admin()
            
            # The database function now returns dictionaries directly
            result = []
            for product in products:
                result.append({
                    "id": product["id"],
                    "name": product["name"],
                    "description": product["description"] or "",
                    "category": product["category"] or "Uncategorized",
                    "price": product["price"],
                    "is_active": product["is_active"],
                    "created_at": product["created_at"],
                    "updated_at": product["updated_at"]
                })
            
            logger.info("Retrieved %d products for admin", len(result))
            return result
        except Exception as e:
            logger.error("Error getting products for admin: %s", e)
            return []

    async def create_new_product(self, name: str, description: str, category: str, price: float, image_url: Optional[str] = None) -> Dict:
        """Create a new product with multilingual support"""
        try:
            # Initialize multilingual content manager
            ml_manager = MultilingualContentManager()
            
            # Validate inputs
            if not name or len(name.strip()) < 2:
                return {"success": False, "error": "Product name must be at least 2 characters long"}
            
            if price <= 0:
                return {"success": False, "error": "Price must be greater than 0"}
            
            if not category or len(category.strip()) < 2:
                return {"success": False, "error": "Category must be at least 2 characters long"}
            
            # Validate image URL if provided
            if image_url:
                from src.utils.image_handler import validate_image_url
                if not validate_image_url(image_url):
                    return {"success": False, "error": "Invalid image URL format"}
            
            # Detect language and prepare multilingual content
            detected_lang = ml_manager.detect_language(name)
            name_en = name.strip() if detected_lang == "en" else None
            name_he = name.strip() if detected_lang == "he" else None
            
            detected_desc_lang = ml_manager.detect_language(description)
            description_en = description.strip() if detected_desc_lang == "en" else None
            description_he = description.strip() if detected_desc_lang == "he" else None
            
            # Create product with multilingual support
            product = create_product(
                name=name.strip(),
                description=description.strip(),
                category=category.strip(),
                price=price,
                image_url=image_url,
                name_en=name_en,
                name_he=name_he,
                description_en=description_en,
                description_he=description_he
            )
            
            if product:
                logger.info("Successfully created product: %s", name)
                return {
                    "success": True,
                    "product": {
                        "id": product.id,
                        "name": product.name,
                        "description": product.description,
                        "category": category,  # Use the category name passed to the function
                        "price": product.price,
                        "is_active": product.is_active,
                        "image_url": product.image_url
                    }
                }
            else:
                return {"success": False, "error": "Product with this name already exists"}
                
        except Exception as e:
            logger.error("Error creating product: %s", e)
            return {"success": False, "error": f"Failed to create product: {str(e)}"}

    async def update_existing_product(self, product_id: int, **kwargs) -> Dict:
        """Update an existing product with multilingual support"""
        try:
            # Initialize multilingual content manager
            ml_manager = MultilingualContentManager()
            
            # Validate product exists
            product = get_product_by_id(product_id)
            if not product:
                return {"success": False, "error": "Product not found"}
            
            # Validate inputs
            if "name" in kwargs and (not kwargs["name"] or len(kwargs["name"].strip()) < 2):
                return {"success": False, "error": "Product name must be at least 2 characters long"}
            
            if "price" in kwargs and kwargs["price"] <= 0:
                return {"success": False, "error": "Price must be greater than 0"}
            
            if "category" in kwargs and (not kwargs["category"] or len(kwargs["category"].strip()) < 2):
                return {"success": False, "error": "Category must be at least 2 characters long"}
            
            # Clean up string inputs and handle multilingual content
            if "name" in kwargs:
                name = kwargs["name"].strip()
                detected_lang = ml_manager.detect_language(name)
                if detected_lang == "en":
                    kwargs["name_en"] = name
                elif detected_lang == "he":
                    kwargs["name_he"] = name
                kwargs["name"] = name
                
            if "description" in kwargs:
                description = kwargs["description"].strip()
                detected_desc_lang = ml_manager.detect_language(description)
                if detected_desc_lang == "en":
                    kwargs["description_en"] = description
                elif detected_desc_lang == "he":
                    kwargs["description_he"] = description
                kwargs["description"] = description
                
            if "category" in kwargs:
                kwargs["category"] = kwargs["category"].strip()
            
            # Update product
            success = update_product(product_id, **kwargs)
            
            if success:
                # Get updated product as dictionary
                from src.db.operations import get_product_dict_by_id
                updated_product = get_product_dict_by_id(product_id)
                if updated_product:
                    logger.info("Successfully updated product ID %d", product_id)
                    return {
                        "success": True,
                        "product": updated_product
                    }
                else:
                    return {"success": False, "error": "Failed to retrieve updated product"}
            else:
                return {"success": False, "error": "Failed to update product"}
                
        except Exception as e:
            logger.error("Error updating product ID %d: %s", product_id, e)
            return {"success": False, "error": f"Failed to update product: {str(e)}"}

    async def deactivate_product(self, product_id: int) -> Dict:
        """Soft delete a product (set is_active to False)"""
        try:
            # Validate product exists
            product = get_product_by_id(product_id)
            if not product:
                return {"success": False, "error": "Product not found"}
            
            # Soft delete product
            from src.db.operations import deactivate_product
            success = deactivate_product(product_id)
            
            if success:
                logger.info("Successfully deactivated product ID %d: %s", product_id, product.name)
                return {
                    "success": True,
                    "message": f"Product '{product.name}' has been deactivated"
                }
            else:
                return {"success": False, "error": "Failed to deactivate product"}
                
        except Exception as e:
            logger.error("Error deactivating product ID %d: %s", product_id, e)
            return {"success": False, "error": f"Failed to deactivate product: {str(e)}"}

    async def hard_delete_product(self, product_id: int) -> Dict:
        """Hard delete a product (remove from database)"""
        try:
            # Validate product exists
            product = get_product_by_id(product_id)
            if not product:
                return {"success": False, "error": "Product not found"}
            
            # Hard delete product
            from src.db.operations import hard_delete_product
            success = hard_delete_product(product_id)
            
            if success:
                logger.info("Successfully hard deleted product ID %d: %s", product_id, product.name)
                return {
                    "success": True,
                    "message": f"Product '{product.name}' has been permanently deleted"
                }
            else:
                return {"success": False, "error": "Failed to delete product. It may be referenced in orders or carts."}
                
        except Exception as e:
            logger.error("Error hard deleting product ID %d: %s", product_id, e)
            return {"success": False, "error": f"Failed to delete product: {str(e)}"}

    # Keep backward compatibility
    async def delete_existing_product(self, product_id: int) -> Dict:
        """Soft delete a product (set is_active to False) - deprecated, use deactivate_product"""
        return await self.deactivate_product(product_id)

    async def get_product_categories_list(self) -> List[str]:
        """Get all unique product categories (including empty ones for admin)"""
        try:
            from src.db.operations import get_all_categories
            categories = get_all_categories()
            logger.info("Retrieved %d product categories", len(categories))
            return categories
        except Exception as e:
            logger.error("Error getting product categories: %s", e)
            return []



    async def get_products_by_category_admin(self, category: str) -> List[Dict]:
        """Get all products in a specific category"""
        try:
            products = get_products_by_category(category)
            
            result = []
            for product in products:
                # Get category name safely
                category_name = "Uncategorized"
                if hasattr(product, 'category_rel') and product.category_rel:
                    category_name = product.category_rel.name
                elif hasattr(product, 'category'):
                    category_name = product.category or "Uncategorized"
                
                result.append({
                    "id": product.id,
                    "name": product.name,
                    "description": product.description or "",
                    "category": category_name,
                    "price": product.price,
                    "is_active": product.is_active
                })
            
            logger.info("Retrieved %d products in category '%s'", len(result), category)
            return result
        except Exception as e:
            logger.error("Error getting products by category: %s", e)
            return []



    async def toggle_product_status(self, product_id: int) -> Dict:
        """Toggle product active/inactive status"""
        try:
            from src.db.operations import get_product_by_id, update_product
            
            product = get_product_by_id(product_id)
            if not product:
                return {"success": False, "error": "Product not found"}
            
            new_status = not product.is_active
            success = update_product(product_id, is_active=new_status)
            
            if success:
                logger.info("Toggled product %d status to %s", product_id, new_status)
                return {"success": True, "new_status": new_status}
            else:
                return {"success": False, "error": "Failed to update product status"}
                
        except Exception as e:
            logger.error("Error toggling product status: %s", e)
            return {"success": False, "error": str(e)}

    # Category Management Methods
    async def create_category(self, category_name: str) -> Dict:
        """Create a new category"""
        try:
            # Validate input
            if not category_name or len(category_name.strip()) < 2:
                return {"success": False, "error": "Category name must be at least 2 characters long"}
            
            # Check if category already exists
            existing_categories = get_product_categories()
            if category_name.lower() in [cat.lower() for cat in existing_categories]:
                return {"success": False, "error": f"Category '{category_name}' already exists"}
            
            # Create category directly using the new function
            from src.db.operations import create_category
            category = create_category(
                name=category_name.strip(),
                description=f"Category for {category_name}",
                display_order=len(existing_categories) + 1
            )
            
            if category:
                logger.info("Successfully created category: %s", category_name)
                return {
                    "success": True,
                    "category": category_name.strip(),
                    "message": f"Category '{category_name}' created successfully"
                }
            else:
                return {"success": False, "error": "Failed to create category"}
                
        except Exception as e:
            logger.error("Error creating category: %s", e)
            return {"success": False, "error": f"Failed to create category: {str(e)}"}

    async def create_category_multilingual(self, name: str, name_en: str = None, name_he: str = None, description: str = None) -> Dict:
        """Create a new category with multilingual support"""
        try:
            # Validate input
            if not name or len(name.strip()) < 2:
                return {"success": False, "error": "Category name must be at least 2 characters long"}
            
            # Check if category already exists
            existing_categories = get_product_categories()
            if name.lower() in [cat.lower() for cat in existing_categories]:
                return {"success": False, "error": f"Category '{name}' already exists"}
            
            # Create category with multilingual support
            from src.db.operations import create_category
            category = create_category(
                name=name.strip(),
                description=description or f"Category for {name}",
                display_order=len(existing_categories) + 1,
                name_en=name_en,
                name_he=name_he
            )
            
            if category:
                logger.info("Successfully created multilingual category: %s", name)
                return {
                    "success": True,
                    "category": {
                        "name": category.name,
                        "name_en": category.name_en,
                        "name_he": category.name_he,
                        "description": category.description
                    },
                    "message": f"Category '{name}' created successfully with multilingual support"
                }
            else:
                return {"success": False, "error": "Failed to create category"}
                
        except Exception as e:
            logger.error("Error creating multilingual category: %s", e)
            return {"success": False, "error": f"Failed to create category: {str(e)}"}

    async def update_category(self, old_category: str, new_category: str) -> Dict:
        """Update a category name"""
        try:
            # Validate inputs
            if not new_category or len(new_category.strip()) < 2:
                return {"success": False, "error": "Category name must be at least 2 characters long"}
            
            # Check if new category name already exists
            existing_categories = get_product_categories()
            if new_category.lower() in [cat.lower() for cat in existing_categories if cat != old_category]:
                return {"success": False, "error": f"Category '{new_category}' already exists"}
            
            # Get all products in the old category (including inactive ones)
            from src.db.operations import get_all_products_by_category
            products = get_all_products_by_category(old_category)
            
            if not products:
                return {"success": False, "error": f"No products found in category '{old_category}'"}
            
            # Update the category name directly in the MenuCategory table
            from src.db.operations import get_db_session
            from src.db.models import MenuCategory
            
            session = get_db_session()
            try:
                # Find the category to update
                category_obj = session.query(MenuCategory).filter(MenuCategory.name == old_category).first()
                if not category_obj:
                    return {"success": False, "error": f"Category '{old_category}' not found"}
                
                # Update the category name
                category_obj.name = new_category.strip()
                category_obj.updated_at = datetime.utcnow()
                session.commit()
                
                logger.info("Successfully updated category from '%s' to '%s' (%d products)", 
                          old_category, new_category, len(products))
                
                # Clear cache after updating category
                try:
                    from src.utils.helpers import SimpleCache
                    cache = SimpleCache()
                    cache.clear()  # Clear all cache entries to ensure fresh data
                    logger.info("Cleared cache after updating category from '%s' to '%s'", old_category, new_category)
                except Exception as cache_error:
                    logger.warning("Failed to clear cache after updating category: %s", cache_error)
                
                return {
                    "success": True,
                    "old_category": old_category,
                    "new_category": new_category.strip(),
                    "updated_products": len(products),
                    "message": f"Category updated from '{old_category}' to '{new_category}' ({len(products)} products)"
                }
                
            except Exception as e:
                session.rollback()
                logger.error("Database error updating category: %s", e)
                return {"success": False, "error": f"Database error: {str(e)}"}
            finally:
                session.close()
                
        except Exception as e:
            logger.error("Error updating category from '%s' to '%s': %s", old_category, new_category, e)
            return {"success": False, "error": f"Failed to update category: {str(e)}"}

    async def delete_category(self, category: str) -> Dict:
        """Delete a category and all its products"""
        try:
            # Use the new delete_category function
            from src.db.operations import delete_category
            success = delete_category(category)
            
            if success:
                logger.info("Successfully deleted category: %s", category)
                return {
                    "success": True,
                    "category": category,
                    "message": f"Category '{category}' deleted successfully"
                }
            else:
                return {"success": False, "error": f"Failed to delete category '{category}'"}
                
        except Exception as e:
            logger.error("Error deleting category '%s': %s", category, e)
            return {"success": False, "error": f"Failed to delete category: {str(e)}"}

    async def get_business_settings(self) -> Dict:
        """Get current business settings"""
        try:
            from src.db.operations import get_business_settings_dict
            settings = get_business_settings_dict()
            
            if settings:
                logger.info("Retrieved business settings successfully")
                return {
                    "success": True,
                    "settings": settings
                }
            else:
                return {"success": False, "error": "No business settings found"}
                
        except Exception as e:
            logger.error("Error getting business settings: %s", e)
            return {"success": False, "error": f"Failed to get business settings: {str(e)}"}

    async def update_business_settings(self, **kwargs) -> Dict:
        """Update business settings"""
        try:
            from src.db.operations import update_business_settings
            
            # Convert numeric fields
            if "delivery_charge" in kwargs:
                try:
                    kwargs["delivery_charge"] = float(kwargs["delivery_charge"])
                except (ValueError, TypeError):
                    return {"success": False, "error": "Invalid delivery charge format"}
            
            # Validate required fields
            if "business_name" in kwargs and (not kwargs["business_name"] or len(kwargs["business_name"].strip()) < 2):
                return {"success": False, "error": "Business name must be at least 2 characters long"}
            
            if "delivery_charge" in kwargs and kwargs["delivery_charge"] < 0:
                return {"success": False, "error": "Delivery charge cannot be negative"}
            
            if "currency" in kwargs and len(kwargs["currency"].strip()) < 2:
                return {"success": False, "error": "Currency must be at least 2 characters long"}
            
            # Clean up string inputs
            for key, value in kwargs.items():
                if isinstance(value, str):
                    kwargs[key] = value.strip()
            
            # Update settings
            success = update_business_settings(**kwargs)
            
            if success:
                # Get updated settings
                updated_settings = await self.get_business_settings()
                logger.info("Successfully updated business settings: %s", list(kwargs.keys()))
                return {
                    "success": True,
                    "message": f"Business settings updated successfully",
                    "updated_fields": list(kwargs.keys()),
                    "settings": updated_settings.get("settings", {})
                }
            else:
                return {"success": False, "error": "Failed to update business settings"}
                
        except Exception as e:
            logger.error("Error updating business settings: %s", e)
            return {"success": False, "error": f"Failed to update business settings: {str(e)}"}