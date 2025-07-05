"""
Order Analytics Use Case

Provides business insights and analytics for order management.
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from src.domain.repositories.customer_repository import CustomerRepository
from src.domain.repositories.order_repository import OrderRepository
from src.infrastructure.utilities.i18n import tr
from src.infrastructure.utilities.helpers import translate_product_name


class OrderAnalyticsUseCase:
    """Use case for order analytics and business insights"""

    def __init__(
        self, order_repository: OrderRepository, customer_repository: CustomerRepository
    ):
        self._order_repository = order_repository
        self._customer_repository = customer_repository
        self._logger = logging.getLogger(self.__class__.__name__)

    async def get_daily_summary(self, date: datetime | None = None) -> dict[str, Any]:
        """Get daily order summary"""
        if not date:
            date = datetime.now()

        self._logger.info("📊 GENERATING DAILY SUMMARY: %s", date.strftime("%Y-%m-%d"))

        try:
            # Get all orders (in a real system, you'd filter by date)
            all_orders = await self._order_repository.get_all_orders()

            # Filter orders for today (simplified - would use date filtering in real implementation)
            today_orders = [
                order
                for order in all_orders
                if (
                    order.get("created_at")
                    and order["created_at"].date() == date.date()
                )
            ]  # noqa: E501

            # Calculate metrics
            total_orders = len(today_orders)
            total_revenue = sum(order.get("total", 0) for order in today_orders)

            # Status breakdown
            status_counts = Counter(
                order.get("status", "pending") for order in today_orders
            )

            # Delivery method breakdown
            delivery_counts = Counter(
                order.get("delivery_method", "pickup") for order in today_orders
            )

            # Average order value
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

            summary = {
                "date": date.strftime("%Y-%m-%d"),
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "average_order_value": avg_order_value,
                "status_breakdown": dict(status_counts),
                "delivery_breakdown": dict(delivery_counts),
                "orders": today_orders,
            }

            self._logger.info(
                "📈 DAILY SUMMARY: %d orders, ₪%.2f revenue",
                total_orders,
                total_revenue,
            )
            return summary

        except (TypeError, ValueError, ZeroDivisionError) as e:
            self._logger.error("💥 DAILY SUMMARY ERROR: %s", e, exc_info=True)
            raise

    async def get_weekly_trends(self) -> dict[str, Any]:
        """Get weekly ordering trends"""
        self._logger.info("📊 GENERATING WEEKLY TRENDS")

        try:
            all_orders = await self._order_repository.get_all_orders()

            # Get last 7 days
            today = datetime.now()
            week_data = {}

            for i in range(7):
                day = today - timedelta(days=i)
                day_orders = [
                    order
                    for order in all_orders
                    if order.get("created_at")
                    and order["created_at"].date() == day.date()
                ]

                week_data[day.strftime("%Y-%m-%d")] = {
                    "orders": len(day_orders),
                    "revenue": sum(order.get("total", 0) for order in day_orders),
                    "day_name": day.strftime("%A"),
                }

            # Calculate trends
            total_weekly_orders = sum(data["orders"] for data in week_data.values())
            total_weekly_revenue = sum(data["revenue"] for data in week_data.values())

            trends = {
                "week_data": week_data,
                "total_weekly_orders": total_weekly_orders,
                "total_weekly_revenue": total_weekly_revenue,
                "daily_average_orders": total_weekly_orders / 7,
                "daily_average_revenue": total_weekly_revenue / 7,
            }

            self._logger.info(
                "📈 WEEKLY TRENDS: %d orders, ₪%.2f",
                total_weekly_orders,
                total_weekly_revenue,
            )
            return trends

        except (TypeError, ValueError) as e:
            self._logger.error("💥 WEEKLY TRENDS ERROR: %s", e, exc_info=True)
            raise

    async def get_popular_products(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most popular products by order frequency"""
        self._logger.info("📊 ANALYZING POPULAR PRODUCTS (top %d)", limit)

        try:
            all_orders = await self._order_repository.get_all_orders()

            # Count product occurrences
            product_stats = defaultdict(
                lambda: {"count": 0, "total_quantity": 0, "revenue": 0}
            )

            for order in all_orders:
                for item in order.get("items", []):
                    product_name = item["product_name"]
                    quantity = item["quantity"]
                    revenue = item["total_price"]

                    product_stats[product_name]["count"] += 1
                    product_stats[product_name]["total_quantity"] += quantity
                    product_stats[product_name]["revenue"] += revenue

            # Sort by count and limit
            popular_products = sorted(
                [
                    {
                        "product_name": name,
                        "order_count": stats["count"],
                        "total_quantity": stats["total_quantity"],
                        "total_revenue": stats["revenue"],
                        "avg_quantity_per_order": (
                            stats["total_quantity"] / stats["count"]
                        ),  # noqa: E501
                    }
                    for name, stats in product_stats.items()
                ],
                key=lambda x: x["order_count"],
                reverse=True,
            )[:limit]

            self._logger.info(
                "📈 TOP PRODUCTS: %d products analyzed", len(popular_products)
            )
            return popular_products

        except (TypeError, ValueError) as e:
            self._logger.error("💥 POPULAR PRODUCTS ERROR: %s", e, exc_info=True)
            raise

    async def get_customer_insights(self) -> dict[str, Any]:
        """Get customer behavior insights"""
        self._logger.info("📊 ANALYZING CUSTOMER INSIGHTS")

        try:
            all_orders = await self._order_repository.get_all_orders()
            all_customers = await self._customer_repository.get_all_customers()

            # Customer order frequency
            customer_orders = defaultdict(list)
            for order in all_orders:
                customer_id = order["customer_id"]
                customer_orders[customer_id].append(order)

            # Calculate metrics
            total_customers = len(all_customers)
            active_customers = len(customer_orders)
            repeat_customers = len(
                [cid for cid, orders in customer_orders.items() if len(orders) > 1]
            )
            avg_orders_per_customer = (
                len(all_orders) / active_customers if active_customers > 0 else 0
            )

            # Customer lifetime value
            customer_values = self._calculate_customer_lifetime_value(customer_orders)
            avg_customer_value = (
                sum(customer_values.values()) / len(customer_values)
                if customer_values
                else 0
            )

            insights = {
                "total_customers": total_customers,
                "active_customers": active_customers,
                "repeat_customers": repeat_customers,
                "repeat_customer_rate": (repeat_customers / active_customers * 100)
                if active_customers > 0
                else 0,
                "avg_orders_per_customer": avg_orders_per_customer,
                "avg_customer_lifetime_value": avg_customer_value,
                "top_customers": sorted(
                    [
                        {
                            "customer_id": cid,
                            "total_value": value,
                            "order_count": len(customer_orders[cid]),
                        }
                        for cid, value in customer_values.items()
                    ],
                    key=lambda x: x["total_value"],
                    reverse=True,
                )[:5],
            }

            self._logger.info(
                "📈 CUSTOMER INSIGHTS: %d active, %d repeat",
                active_customers,
                repeat_customers,
            )
            return insights

        except (TypeError, ValueError, ZeroDivisionError) as e:
            self._logger.error("💥 CUSTOMER INSIGHTS ERROR: %s", e, exc_info=True)
            raise

    def _calculate_customer_lifetime_value(
        self, customer_orders: dict[int, list]
    ) -> dict[int, float]:
        """Calculate the lifetime value for each customer."""
        customer_values = {}
        for customer_id, orders in customer_orders.items():
            total_value = sum(order.get("total", 0) for order in orders)
            customer_values[customer_id] = total_value
        return customer_values

    async def get_business_overview(self) -> dict[str, Any]:
        """Get comprehensive business overview"""
        self._logger.info("📊 GENERATING BUSINESS OVERVIEW")

        try:
            # Get component data
            daily_summary = await self.get_daily_summary()
            weekly_trends = await self.get_weekly_trends()
            popular_products = await self.get_popular_products(5)
            customer_insights = await self.get_customer_insights()

            # Get all orders for additional metrics
            all_orders = await self._order_repository.get_all_orders()

            # Calculate additional metrics
            total_lifetime_orders = len(all_orders)
            total_lifetime_revenue = sum(order.get("total", 0) for order in all_orders)

            # Status distribution
            status_distribution = Counter(
                order.get("status", "pending") for order in all_orders
            )

            overview = {
                "generated_at": datetime.now().isoformat(),
                "total_lifetime_orders": total_lifetime_orders,
                "total_lifetime_revenue": total_lifetime_revenue,
                "daily_summary": daily_summary,
                "weekly_trends": weekly_trends,
                "popular_products": popular_products,
                "customer_insights": customer_insights,
                "status_distribution": dict(status_distribution),
            }

            self._logger.info(
                "📈 BUSINESS OVERVIEW: %d total orders, ₪%.2f",
                total_lifetime_orders,
                total_lifetime_revenue,
            )
            return overview

        except (TypeError, ValueError, ZeroDivisionError) as e:
            self._logger.error("💥 BUSINESS OVERVIEW ERROR: %s", e, exc_info=True)
            raise

    def format_analytics_report(self, overview: dict[str, Any]) -> str:
        """Format a comprehensive analytics report into a readable string"""
        self._logger.info("📄 FORMATTING ANALYTICS REPORT")

        try:
            # Daily Summary
            daily = overview["daily_summary"]
            report_lines = [tr("ANALYTICS_REPORT_TITLE")]
            report_lines.append(
                tr("ANALYTICS_GENERATED").format(
                    datetime=datetime.now().strftime('%d/%m/%Y %H:%M')
                )
            )
            report_lines.append(f"\n{tr('ANALYTICS_TODAY_PERFORMANCE')}")
            report_lines.append(tr("ANALYTICS_ORDERS").format(count=daily['total_orders']))
            report_lines.append(tr("ANALYTICS_REVENUE").format(amount=daily['total_revenue']))
            report_lines.append(tr("ANALYTICS_AVG_ORDER").format(amount=daily['average_order_value']))

            # Weekly Trends
            weekly = overview["weekly_trends"]
            report_lines.append(f"\n{tr('ANALYTICS_WEEKLY_TRENDS')}")
            report_lines.append(tr("ANALYTICS_TOTAL_ORDERS").format(count=weekly['total_weekly_orders']))
            report_lines.append(tr("ANALYTICS_TOTAL_REVENUE").format(amount=weekly['total_weekly_revenue']))
            report_lines.append(tr("ANALYTICS_DAILY_AVERAGE").format(avg=weekly['daily_average_orders']))

            # Popular Products
            products = overview["popular_products"]
            report_lines.append(f"\n{tr('ANALYTICS_TOP_PRODUCTS')}")
            for i, product in enumerate(products[:3], 1):
                # Translate product name
                translated_name = translate_product_name(product['product_name'])
                report_lines.append(
                    tr("ANALYTICS_PRODUCT_LINE").format(
                        rank=i, 
                        name=translated_name, 
                        count=product['order_count']
                    )
                )

            # Customer Insights
            customers = overview["customer_insights"]
            report_lines.append(f"\n{tr('ANALYTICS_CUSTOMER_INSIGHTS')}")
            report_lines.append(tr("ANALYTICS_TOTAL_CUSTOMERS").format(count=customers['total_customers']))
            report_lines.append(tr("ANALYTICS_REPEAT_RATE").format(rate=customers['repeat_customer_rate']))
            report_lines.append(tr("ANALYTICS_AVG_CUSTOMER_VALUE").format(amount=customers['avg_customer_lifetime_value']))

            # Lifetime Totals
            report_lines.append(f"\n{tr('ANALYTICS_LIFETIME_TOTALS')}")
            report_lines.append(tr("ANALYTICS_LIFETIME_ORDERS").format(count=overview['total_lifetime_orders']))
            report_lines.append(tr("ANALYTICS_LIFETIME_REVENUE").format(amount=overview['total_lifetime_revenue']))
            report_lines.append(tr("ANALYTICS_AVG_LTV").format(amount=overview['customer_insights']['avg_customer_lifetime_value']))

            return "\n".join(report_lines)

        except (KeyError, TypeError) as e:
            self._logger.error("💥 REPORT FORMATTING ERROR: %s", e, exc_info=True)
            return tr("ANALYTICS_ERROR_REPORT")
