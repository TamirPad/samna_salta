"""
Admin Handler for the Telegram bot.
"""

import logging
from datetime import datetime
from typing import Dict

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.container import get_container
from src.utils.error_handler import BusinessLogicError, error_handler
from src.utils.i18n import i18n

# Conversation states
AWAITING_ORDER_ID, AWAITING_STATUS_UPDATE = range(2)

logger = logging.getLogger(__name__)


class AdminHandler:
    """Handler for admin operations"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.container = get_container()
        self.admin_service = self.container.get_admin_service()
        self.notification_service = self.container.get_notification_service()

    @error_handler("admin_dashboard")
    async def handle_admin_command(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /admin command - show admin dashboard"""
        user_id = update.effective_user.id
        self.logger.debug("👑 ADMIN DASHBOARD: User %s", user_id)

        # Check if user is admin
        if not await self._is_admin_user(user_id):
            await update.message.reply_text(
                i18n.get_text("ADMIN_ACCESS_DENIED", user_id=user_id)
            )
            return

        # Show admin dashboard
        await self._show_admin_dashboard(update, None)

    @error_handler("admin_dashboard")
    async def handle_admin_callback(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle admin dashboard callbacks"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        if not await self._is_admin_user(user_id):
            await query.message.reply_text(i18n.get_text("ADMIN_ACCESS_DENIED", user_id=user_id))
            return

        data = query.data
        self.logger.info("👑 ADMIN CALLBACK: %s by User %s", data, user_id)

        if data == "admin_pending_orders":
            await self._show_pending_orders(query)
        elif data == "admin_active_orders":
            await self._show_active_orders(query)
        elif data == "admin_all_orders":
            await self._show_all_orders(query)
        elif data == "admin_completed_orders":
            await self._show_completed_orders(query)
        elif data == "admin_customers":
            await self._show_customers(query)
        elif data == "admin_update_status":
            return await self._start_status_update(query)
        elif data == "admin_analytics":
            await self._show_analytics(query)
        elif data.startswith("analytics_"):
            await self._handle_analytics_callback(update, None)
        elif data.startswith("admin_order_"):
            order_id = int(data.split("_")[-1])
            await self._show_order_details(query, order_id)
        elif data.startswith("admin_customer_"):
            customer_id = int(data.split("_")[-1])
            await self._show_customer_details(query, customer_id)
        elif data.startswith("admin_status_"):
            # Format: admin_status_{order_id}_{new_status}
            parts = data.split("_")
            order_id = int(parts[2])
            new_status = parts[3]
            await self._update_order_status(query, order_id, new_status, user_id)
        elif data == "admin_back":
            await self._show_admin_dashboard(update, None)

    async def _show_admin_dashboard(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE | None
    ) -> None:
        """Show main admin dashboard"""
        try:
            self.logger.info("📊 LOADING ADMIN DASHBOARD")
            
            # Get user_id from update
            user_id = update.effective_user.id

            # Get order statistics
            pending_orders = await self.admin_service.get_pending_orders()
            active_orders = await self.admin_service.get_active_orders()
            completed_orders = await self.admin_service.get_completed_orders()
            today_orders = await self.admin_service.get_today_orders()

            self.logger.info(
                "📊 STATS: %s pending, %s active, %s completed, %s today",
                len(pending_orders),
                len(active_orders),
                len(completed_orders),
                len(today_orders),
            )

            dashboard_text = (
                i18n.get_text("ADMIN_DASHBOARD_TITLE", user_id=user_id) + "\n\n" +
                i18n.get_text("ADMIN_ORDER_STATS", user_id=user_id) + "\n" +
                i18n.get_text("ADMIN_PENDING_COUNT", user_id=user_id).format(count=len(pending_orders)) + "\n" +
                i18n.get_text("ADMIN_ACTIVE_COUNT", user_id=user_id).format(count=len(active_orders)) + "\n" +
                i18n.get_text("ADMIN_COMPLETED_COUNT", user_id=user_id).format(count=len(completed_orders)) + "\n" +
                i18n.get_text("ADMIN_TOTAL_TODAY", user_id=user_id).format(count=len(today_orders)) + "\n\n" +
                i18n.get_text("ADMIN_QUICK_ACTIONS", user_id=user_id)
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PENDING_ORDERS", user_id=user_id), callback_data="admin_pending_orders"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_ACTIVE_ORDERS", user_id=user_id), callback_data="admin_active_orders"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_ALL_ORDERS", user_id=user_id), callback_data="admin_all_orders"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_COMPLETED_ORDERS", user_id=user_id), callback_data="admin_completed_orders"
                    ),
                ],
                [
                    InlineKeyboardButton(i18n.get_text("ADMIN_ANALYTICS", user_id=user_id), callback_data="admin_analytics"),
                    InlineKeyboardButton(i18n.get_text("ADMIN_CUSTOMERS", user_id=user_id), callback_data="admin_customers")
                ],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=dashboard_text, parse_mode="HTML", reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    text=dashboard_text, parse_mode="HTML", reply_markup=reply_markup
                )

        except (BusinessLogicError, RuntimeError) as e:
            self.logger.error("💥 DASHBOARD ERROR: %s", e, exc_info=True)
            await self._send_error_to_user(update)
        except Exception as e:
            self.logger.critical("💥 UNHANDLED DASHBOARD ERROR: %s", e, exc_info=True)
            await self._send_error_to_user(update)

    async def _send_error_to_user(self, update: Update):
        """Sends a generic error message to the user."""
        message_sender = None
        if update.callback_query:
            message_sender = update.callback_query.message
        elif update.message:
            message_sender = update.message

        if message_sender:
            try:
                            await message_sender.reply_text(
                i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=update.effective_user.id)
            )
            except Exception as e:
                self.logger.error(
                    "💥 CRITICAL: Failed to send error message to user %s: %s",
                    update.effective_user.id,
                    e,
                    exc_info=True,
                )

    async def _show_analytics(self, query: CallbackQuery) -> None:
        """Show enhanced business analytics report"""
        try:
            self.logger.info("📊 GENERATING ENHANCED ANALYTICS REPORT")
            user_id = query.from_user.id

            # Get comprehensive analytics data
            analytics_data = await self.admin_service.get_business_analytics()
            
            if not analytics_data:
                await query.message.reply_text(i18n.get_text("ANALYTICS_ERROR", user_id=user_id))
                return

            # Create analytics dashboard with multiple views
            await self._show_analytics_main_menu(query, analytics_data)

        except BusinessLogicError as e:
            self.logger.error("💥 ANALYTICS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("ANALYTICS_ERROR", user_id=query.from_user.id))
        except Exception as e:
            self.logger.critical("💥 CRITICAL ANALYTICS ERROR: %s", e, exc_info=True)
            await query.message.reply_text(i18n.get_text("ANALYTICS_CRITICAL_ERROR", user_id=query.from_user.id))

    async def _show_analytics_main_menu(self, query: CallbackQuery, analytics_data: Dict) -> None:
        """Show analytics main menu with different report options"""
        user_id = query.from_user.id
        
        # Get quick overview data
        quick_overview = analytics_data.get('quick_overview', {})
        
        # Format the main analytics menu
        menu_text = f"""
{i18n.get_text("ANALYTICS_DASHBOARD_TITLE", user_id=user_id)}

{i18n.get_text("ANALYTICS_QUICK_OVERVIEW", user_id=user_id)}
• {i18n.get_text("ANALYTICS_LABEL_TODAY", user_id=user_id)}: {quick_overview.get('today', {}).get('orders', 0)} {i18n.get_text("ANALYTICS_LABEL_ORDERS", user_id=user_id).lower()}, ₪{quick_overview.get('today', {}).get('revenue', 0):.2f}
• {i18n.get_text("ANALYTICS_LABEL_THIS_WEEK", user_id=user_id)}: {quick_overview.get('this_week', {}).get('orders', 0)} {i18n.get_text("ANALYTICS_LABEL_ORDERS", user_id=user_id).lower()}, ₪{quick_overview.get('this_week', {}).get('revenue', 0):.2f}
• {i18n.get_text("ANALYTICS_LABEL_THIS_MONTH", user_id=user_id)}: {quick_overview.get('this_month', {}).get('orders', 0)} {i18n.get_text("ANALYTICS_LABEL_ORDERS", user_id=user_id).lower()}, ₪{quick_overview.get('this_month', {}).get('revenue', 0):.2f}

{i18n.get_text("ANALYTICS_SELECT_REPORT", user_id=user_id)}
        """.strip()

        keyboard = [
            [
                InlineKeyboardButton(i18n.get_text("ANALYTICS_REVENUE_REPORT", user_id=user_id), callback_data="analytics_revenue"),
                InlineKeyboardButton(i18n.get_text("ANALYTICS_ORDER_REPORT", user_id=user_id), callback_data="analytics_orders")
            ],
            [
                InlineKeyboardButton(i18n.get_text("ANALYTICS_PRODUCT_REPORT", user_id=user_id), callback_data="analytics_products"),
                InlineKeyboardButton(i18n.get_text("ANALYTICS_CUSTOMER_REPORT", user_id=user_id), callback_data="analytics_customers")
            ],
            [
                InlineKeyboardButton(i18n.get_text("ANALYTICS_TRENDS_REPORT", user_id=user_id), callback_data="analytics_trends"),
                InlineKeyboardButton(i18n.get_text("ANALYTICS_FULL_REPORT", user_id=user_id), callback_data="analytics_full")
            ],
            [
                InlineKeyboardButton(i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=user_id), callback_data="admin_back")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=menu_text, parse_mode="HTML", reply_markup=reply_markup
        )

    async def _handle_analytics_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        data = query.data
        user_id = query.from_user.id
        
        try:
            analytics_data = await self.admin_service.get_business_analytics()
            
            if data == "analytics_revenue":
                await self._show_revenue_report(query, analytics_data)
            elif data == "analytics_orders":
                await self._show_order_report(query, analytics_data)
            elif data == "analytics_products":
                await self._show_product_report(query, analytics_data)
            elif data == "analytics_customers":
                await self._show_customer_report(query, analytics_data)
            elif data == "analytics_trends":
                await self._show_trends_report(query, analytics_data)
            elif data == "analytics_full":
                await self._show_full_report(query, analytics_data)
            elif data == "analytics_back":
                await self._show_analytics_main_menu(query, analytics_data)
                
        except Exception as e:
            self.logger.error("Error handling analytics callback: %s", e)
            await query.message.reply_text(i18n.get_text("ANALYTICS_ERROR", user_id=user_id))

    async def _show_revenue_report(self, query: CallbackQuery, analytics_data: Dict) -> None:
        user_id = query.from_user.id
        revenue_data = analytics_data.get('revenue', {})
        quick_overview = analytics_data.get('quick_overview', {})

        def fmt(val, fmtstr=".2f", na="N/A"):
            if val is None:
                return na
            try:
                return f"{val:{fmtstr}}"
            except Exception:
                return na

        report_text = f"""
{i18n.get_text('ANALYTICS_REVENUE_TITLE', user_id=user_id)}

{i18n.get_text('ANALYTICS_OVERALL_PERFORMANCE', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_TOTAL_REVENUE', user_id=user_id)}: ₪{fmt(revenue_data.get('total_revenue'))}
• {i18n.get_text('ANALYTICS_LABEL_TOTAL_ORDERS', user_id=user_id)}: {revenue_data.get('total_orders', 0)}
• {i18n.get_text('ANALYTICS_LABEL_AVG_VALUE', user_id=user_id)}: ₪{fmt(revenue_data.get('avg_order_value'))}

{i18n.get_text('ANALYTICS_DELIVERY_ANALYSIS', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_DELIVERY_ORDERS', user_id=user_id)}: {revenue_data.get('delivery_orders', 0)} (₪{fmt(revenue_data.get('delivery_revenue'))})
• {i18n.get_text('ANALYTICS_LABEL_PICKUP_ORDERS', user_id=user_id)}: {revenue_data.get('pickup_orders', 0)} (₪{fmt(revenue_data.get('pickup_revenue'))})
• Delivery %: {fmt((revenue_data.get('delivery_orders', 0) / revenue_data.get('total_orders', 1) * 100) if revenue_data.get('total_orders', 1) else 0, '.1f', 'N/A')}%

{i18n.get_text('ANALYTICS_RECENT_PERFORMANCE', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_TODAY', user_id=user_id)}: ₪{fmt(quick_overview.get('today', {}).get('revenue'))}
• {i18n.get_text('ANALYTICS_LABEL_THIS_WEEK', user_id=user_id)}: ₪{fmt(quick_overview.get('this_week', {}).get('revenue'))}
• {i18n.get_text('ANALYTICS_LABEL_THIS_MONTH', user_id=user_id)}: ₪{fmt(quick_overview.get('this_month', {}).get('revenue'))}

<i>{i18n.get_text('ANALYTICS_REPORT_PERIOD', user_id=user_id).format(days=analytics_data.get('period', {}).get('days', 30))}</i>
        """.strip()
        
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("ANALYTICS_BACK_TO_ANALYTICS", user_id=user_id), callback_data="analytics_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=report_text, parse_mode="HTML", reply_markup=reply_markup
        )

    async def _show_order_report(self, query: CallbackQuery, analytics_data: Dict) -> None:
        user_id = query.from_user.id
        order_data = analytics_data.get('orders', {})
        quick_overview = analytics_data.get('quick_overview', {})

        def fmt(val, fmtstr=".1f", na="N/A"):
            if val is None:
                return na
            try:
                return f"{val:{fmtstr}}"
            except Exception:
                return na

        total_processed = order_data.get('completed_orders', 0) + order_data.get('cancelled_orders', 0)
        completion_rate = (order_data.get('completed_orders', 0) / total_processed * 100) if total_processed > 0 else None
        avg_processing_time = order_data.get('avg_processing_time')

        report_text = f"""
{i18n.get_text('ANALYTICS_ORDER_TITLE', user_id=user_id)}

{i18n.get_text('ANALYTICS_ORDER_STATUS', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_PENDING', user_id=user_id)}: {order_data.get('pending_orders', 0)}
• {i18n.get_text('ANALYTICS_LABEL_ACTIVE', user_id=user_id)}: {order_data.get('active_orders', 0)}
• {i18n.get_text('ANALYTICS_LABEL_COMPLETED', user_id=user_id)}: {order_data.get('completed_orders', 0)}
• {i18n.get_text('ANALYTICS_LABEL_CANCELLED', user_id=user_id)}: {order_data.get('cancelled_orders', 0)}

{i18n.get_text('ANALYTICS_PROCESSING_METRICS', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_COMPLETION_RATE', user_id=user_id)}: {fmt(completion_rate, '.1f')}%
• {i18n.get_text('ANALYTICS_LABEL_AVG_PROCESSING_TIME', user_id=user_id)}: {fmt(avg_processing_time, '.1f')} hours
• {i18n.get_text('ANALYTICS_LABEL_TOTAL_ORDERS', user_id=user_id)}: {order_data.get('total_orders', 0)}

{i18n.get_text('ANALYTICS_RECENT_ACTIVITY', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_TODAY', user_id=user_id)}: {quick_overview.get('today', {}).get('orders', 0)} {i18n.get_text('ANALYTICS_LABEL_ORDERS', user_id=user_id).lower()}
• {i18n.get_text('ANALYTICS_LABEL_THIS_WEEK', user_id=user_id)}: {quick_overview.get('this_week', {}).get('orders', 0)} {i18n.get_text('ANALYTICS_LABEL_ORDERS', user_id=user_id).lower()}
• {i18n.get_text('ANALYTICS_LABEL_THIS_MONTH', user_id=user_id)}: {quick_overview.get('this_month', {}).get('orders', 0)} {i18n.get_text('ANALYTICS_LABEL_ORDERS', user_id=user_id).lower()}

<i>{i18n.get_text('ANALYTICS_REPORT_PERIOD', user_id=user_id).format(days=analytics_data.get('period', {}).get('days', 30))}</i>
        """.strip()
        
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("ANALYTICS_BACK_TO_ANALYTICS", user_id=user_id), callback_data="analytics_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=report_text, parse_mode="HTML", reply_markup=reply_markup
        )

    async def _show_product_report(self, query: CallbackQuery, analytics_data: Dict) -> None:
        user_id = query.from_user.id
        products = analytics_data.get('products', [])

        def fmt(val, fmtstr=".2f", na="N/A"):
            if val is None:
                return na
            try:
                return f"{val:{fmtstr}}"
            except Exception:
                return na

        if not products:
            report_text = f"""
{i18n.get_text('ANALYTICS_PRODUCT_TITLE', user_id=user_id)}

{i18n.get_text('ANALYTICS_PRODUCT_PERFORMANCE', user_id=user_id)}
{i18n.get_text('ANALYTICS_NO_DATA', user_id=user_id)}
            """.strip()
        else:
            top_products = products[:5]
            product_lines = []
            for i, product in enumerate(top_products, 1):
                from src.utils.helpers import translate_product_name
                translated_product_name = translate_product_name(product['product_name'], product.get('options', {}), user_id)
                product_lines.append(
                    f"{i}. {translated_product_name}\n"
                    f"   • {i18n.get_text('ANALYTICS_LABEL_ORDERS', user_id=user_id)}: {product.get('total_orders', 0)}\n"
                    f"   • {i18n.get_text('ANALYTICS_LABEL_REVENUE', user_id=user_id)}: ₪{fmt(product.get('total_revenue'))}\n"
                    f"   • {i18n.get_text('ANALYTICS_LABEL_AVG_VALUE', user_id=user_id)}: ₪{fmt(product.get('avg_order_value'))}"
                )
            report_text = f"""
{i18n.get_text('ANALYTICS_PRODUCT_TITLE', user_id=user_id)}

{i18n.get_text('ANALYTICS_TOP_PRODUCTS', user_id=user_id)}

{chr(10).join(product_lines)}

{i18n.get_text('ANALYTICS_PRODUCT_SUMMARY', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_TOTAL_PRODUCTS', user_id=user_id)}: {len(products)}
• {i18n.get_text('ANALYTICS_LABEL_TOTAL_PRODUCT_REVENUE', user_id=user_id)}: ₪{fmt(sum(p.get('total_revenue', 0) or 0 for p in products))}
• {i18n.get_text('ANALYTICS_LABEL_MOST_POPULAR', user_id=user_id)}: {translate_product_name(products[0]['product_name'], products[0].get('options', {}), user_id) if products else 'N/A'}

<i>{i18n.get_text('ANALYTICS_REPORT_PERIOD', user_id=user_id).format(days=analytics_data.get('period', {}).get('days', 30))}</i>
            """.strip()
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("ANALYTICS_BACK_TO_ANALYTICS", user_id=user_id), callback_data="analytics_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=report_text, parse_mode="HTML", reply_markup=reply_markup
        )

    async def _show_customer_report(self, query: CallbackQuery, analytics_data: Dict) -> None:
        user_id = query.from_user.id
        customers = analytics_data.get('customers', [])

        def fmt(val, fmtstr=".2f", na="N/A"):
            if val is None:
                return na
            try:
                return f"{val:{fmtstr}}"
            except Exception:
                return na

        if not customers:
            report_text = f"""
{i18n.get_text('ANALYTICS_CUSTOMER_TITLE', user_id=user_id)}

{i18n.get_text('ANALYTICS_CUSTOMER_BEHAVIOR', user_id=user_id)}
{i18n.get_text('ANALYTICS_NO_DATA', user_id=user_id)}
            """.strip()
        else:
            top_customers = customers[:5]
            customer_lines = []
            for i, customer in enumerate(top_customers, 1):
                customer_lines.append(
                    f"{i}. {customer['customer_name']}\n"
                    f"   • {i18n.get_text('ANALYTICS_LABEL_ORDERS', user_id=user_id)}: {customer.get('total_orders', 0)}\n"
                    f"   • {i18n.get_text('ANALYTICS_LABEL_TOTAL_SPENT', user_id=user_id)}: ₪{fmt(customer.get('total_spent'))}\n"
                    f"   • {i18n.get_text('ANALYTICS_LABEL_AVG_ORDER', user_id=user_id)}: ₪{fmt(customer.get('avg_order_value'))}"
                )
            total_customers = len(customers)
            total_customer_revenue = sum(c.get('total_spent', 0) or 0 for c in customers)
            avg_customer_value = total_customer_revenue / total_customers if total_customers > 0 else None
            report_text = f"""
{i18n.get_text('ANALYTICS_CUSTOMER_TITLE', user_id=user_id)}

{i18n.get_text('ANALYTICS_TOP_CUSTOMERS', user_id=user_id)}

{chr(10).join(customer_lines)}

{i18n.get_text('ANALYTICS_CUSTOMER_METRICS', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_TOTAL_CUSTOMERS', user_id=user_id)}: {total_customers}
• {i18n.get_text('ANALYTICS_LABEL_TOTAL_CUSTOMER_REVENUE', user_id=user_id)}: ₪{fmt(total_customer_revenue)}
• {i18n.get_text('ANALYTICS_LABEL_AVERAGE_CUSTOMER_VALUE', user_id=user_id)}: ₪{fmt(avg_customer_value)}
• {i18n.get_text('ANALYTICS_LABEL_BEST_CUSTOMER', user_id=user_id)}: {customers[0]['customer_name'] if customers else 'N/A'}

<i>{i18n.get_text('ANALYTICS_REPORT_PERIOD', user_id=user_id).format(days=analytics_data.get('period', {}).get('days', 30))}</i>
            """.strip()
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("ANALYTICS_BACK_TO_ANALYTICS", user_id=user_id), callback_data="analytics_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=report_text, parse_mode="HTML", reply_markup=reply_markup
        )

    async def _show_trends_report(self, query: CallbackQuery, analytics_data: Dict) -> None:
        user_id = query.from_user.id
        trends = analytics_data.get('trends', {})
        daily_revenue = trends.get('daily_revenue', {})
        daily_orders = trends.get('daily_orders', {})
        recent_days = sorted(daily_revenue.keys())[-7:] if daily_revenue else []
        if recent_days:
            recent_revenue = [daily_revenue.get(day, 0) for day in recent_days]
            recent_orders = [daily_orders.get(day, 0) for day in recent_days]
            revenue_trend = i18n.get_text('ANALYTICS_GROWING_TREND', user_id=user_id) if len(recent_revenue) > 1 and recent_revenue[-1] > recent_revenue[0] else i18n.get_text('ANALYTICS_DECLINING_TREND', user_id=user_id)
            order_trend = i18n.get_text('ANALYTICS_GROWING_TREND', user_id=user_id) if len(recent_orders) > 1 and recent_orders[-1] > recent_orders[0] else i18n.get_text('ANALYTICS_DECLINING_TREND', user_id=user_id)
            recent_summary = []
            for day in recent_days[-3:]:
                revenue = daily_revenue.get(day, 0)
                orders = daily_orders.get(day, 0)
                recent_summary.append(f"• {day}: {orders} orders, ₪{revenue:.2f}")
        else:
            revenue_trend = i18n.get_text('ANALYTICS_NO_DATA_TREND', user_id=user_id)
            order_trend = i18n.get_text('ANALYTICS_NO_DATA_TREND', user_id=user_id)
            recent_summary = [i18n.get_text('ANALYTICS_NO_RECENT_DATA', user_id=user_id)]
        report_text = f"""
{i18n.get_text('ANALYTICS_TRENDS_TITLE', user_id=user_id)}

{i18n.get_text('ANALYTICS_TREND_ANALYSIS', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_REVENUE_TREND', user_id=user_id)}: {revenue_trend}
• {i18n.get_text('ANALYTICS_LABEL_ORDER_VOLUME_TREND', user_id=user_id)}: {order_trend}

{i18n.get_text('ANALYTICS_RECENT_TRENDS', user_id=user_id)}
{chr(10).join(recent_summary)}

{i18n.get_text('ANALYTICS_TREND_INSIGHTS', user_id=user_id)}
• {i18n.get_text('ANALYTICS_INSIGHT_DAILY_REVENUE', user_id=user_id)}
• {i18n.get_text('ANALYTICS_INSIGHT_ORDER_VOLUME', user_id=user_id)}
• {i18n.get_text('ANALYTICS_INSIGHT_COMPARE_PERIODS', user_id=user_id)}

<i>{i18n.get_text('ANALYTICS_REPORT_PERIOD', user_id=user_id).format(days=analytics_data.get('period', {}).get('days', 30))}</i>
        """.strip()
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("ANALYTICS_BACK_TO_ANALYTICS", user_id=user_id), callback_data="analytics_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=report_text, parse_mode="HTML", reply_markup=reply_markup
        )

    async def _show_full_report(self, query: CallbackQuery, analytics_data: Dict) -> None:
        user_id = query.from_user.id
        revenue_data = analytics_data.get('revenue', {})
        order_data = analytics_data.get('orders', {})
        products = analytics_data.get('products', [])
        customers = analytics_data.get('customers', [])
        quick_overview = analytics_data.get('quick_overview', {})

        def fmt(val, fmtstr=".2f", na="N/A"):
            if val is None:
                return na
            try:
                return f"{val:{fmtstr}}"
            except Exception:
                return na

        total_revenue = revenue_data.get('total_revenue')
        total_orders = order_data.get('total_orders', 0)
        avg_order_value = revenue_data.get('avg_order_value')
        completion_rate = (order_data.get('completed_orders', 0) / total_orders * 100) if total_orders > 0 else None
        report_text = f"""
{i18n.get_text('ANALYTICS_FULL_TITLE', user_id=user_id)}

{i18n.get_text('ANALYTICS_FINANCIAL_SUMMARY', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_TOTAL_REVENUE', user_id=user_id)}: ₪{fmt(total_revenue)}
• {i18n.get_text('ANALYTICS_LABEL_TOTAL_ORDERS', user_id=user_id)}: {total_orders}
• {i18n.get_text('ANALYTICS_LABEL_AVG_VALUE', user_id=user_id)}: ₪{fmt(avg_order_value)}
• {i18n.get_text('ANALYTICS_LABEL_COMPLETION_RATE', user_id=user_id)}: {fmt(completion_rate, '.1f')}%

📦 <b>Order Status:</b>
• {i18n.get_text('ANALYTICS_LABEL_PENDING', user_id=user_id)}: {order_data.get('pending_orders', 0)}
• {i18n.get_text('ANALYTICS_LABEL_ACTIVE', user_id=user_id)}: {order_data.get('active_orders', 0)}
• {i18n.get_text('ANALYTICS_LABEL_COMPLETED', user_id=user_id)}: {order_data.get('completed_orders', 0)}
• {i18n.get_text('ANALYTICS_LABEL_CANCELLED', user_id=user_id)}: {order_data.get('cancelled_orders', 0)}

{i18n.get_text('ANALYTICS_DELIVERY_MIX', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_DELIVERY_ORDERS', user_id=user_id)}: {revenue_data.get('delivery_orders', 0)} {i18n.get_text('ANALYTICS_LABEL_ORDERS', user_id=user_id).lower()} (₪{fmt(revenue_data.get('delivery_revenue'))})
• {i18n.get_text('ANALYTICS_LABEL_PICKUP_ORDERS', user_id=user_id)}: {revenue_data.get('pickup_orders', 0)} {i18n.get_text('ANALYTICS_LABEL_ORDERS', user_id=user_id).lower()} (₪{fmt(revenue_data.get('pickup_revenue'))})

{i18n.get_text('ANALYTICS_PRODUCT_PERFORMANCE_SUMMARY', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_TOTAL_PRODUCTS', user_id=user_id)}: {len(products)}
• {i18n.get_text('ANALYTICS_LABEL_MOST_POPULAR', user_id=user_id)}: {products[0]['product_name'] if products else 'N/A'}
• {i18n.get_text('ANALYTICS_LABEL_PRODUCT_REVENUE', user_id=user_id)}: ₪{fmt(sum(p.get('total_revenue', 0) or 0 for p in products))}

{i18n.get_text('ANALYTICS_CUSTOMER_INSIGHTS', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_TOTAL_CUSTOMERS', user_id=user_id)}: {len(customers)}
• {i18n.get_text('ANALYTICS_LABEL_BEST_CUSTOMER', user_id=user_id)}: {customers[0]['customer_name'] if customers else 'N/A'}
• {i18n.get_text('ANALYTICS_LABEL_CUSTOMER_REVENUE', user_id=user_id)}: ₪{fmt(sum(c.get('total_spent', 0) or 0 for c in customers))}

{i18n.get_text('ANALYTICS_RECENT_PERFORMANCE', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_TODAY', user_id=user_id)}: {quick_overview.get('today', {}).get('orders', 0)} {i18n.get_text('ANALYTICS_LABEL_ORDERS', user_id=user_id).lower()}, ₪{fmt(quick_overview.get('today', {}).get('revenue'))}
• {i18n.get_text('ANALYTICS_LABEL_THIS_WEEK', user_id=user_id)}: {quick_overview.get('this_week', {}).get('orders', 0)} {i18n.get_text('ANALYTICS_LABEL_ORDERS', user_id=user_id).lower()}, ₪{fmt(quick_overview.get('this_week', {}).get('revenue'))}
• {i18n.get_text('ANALYTICS_LABEL_THIS_MONTH', user_id=user_id)}: {quick_overview.get('this_month', {}).get('orders', 0)} {i18n.get_text('ANALYTICS_LABEL_ORDERS', user_id=user_id).lower()}, ₪{fmt(quick_overview.get('this_month', {}).get('revenue'))}

<i>{i18n.get_text('ANALYTICS_REPORT_PERIOD', user_id=user_id).format(days=analytics_data.get('period', {}).get('days', 30))}</i>
<i>{i18n.get_text('ANALYTICS_GENERATED_AT', user_id=user_id).format(datetime=analytics_data.get('generated_at', ''))}</i>
        """.strip()
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("ANALYTICS_BACK_TO_ANALYTICS", user_id=user_id), callback_data="analytics_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=report_text, parse_mode="HTML", reply_markup=reply_markup
        )

    async def _show_pending_orders(self, query: CallbackQuery) -> None:
        """Show pending orders"""
        try:
            orders = await self.admin_service.get_pending_orders()

            if not orders:
                text = (
                    i18n.get_text("ADMIN_PENDING_ORDERS_TITLE", user_id=query.from_user.id) + "\n\n" + i18n.get_text("ADMIN_NO_PENDING_ORDERS", user_id=query.from_user.id)
                )
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                ]
            else:
                text = (
                    f"{i18n.get_text('ADMIN_PENDING_ORDERS_TITLE', user_id=query.from_user.id)} ({len(orders)})\n\n"
                    f"{i18n.get_text('ADMIN_PENDING_ORDERS_LIST', user_id=query.from_user.id)}"
                )

                keyboard = []
                for order in orders:  # Show all pending orders
                    order_summary = (
                        f"#{order['order_id']} - {order['customer_name']} - "
                        f"₪{order['total']:.2f}"
                    )
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order['order_id']}",
                            )
                        ]
                    )

                keyboard.append(
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 PENDING ORDERS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("PENDING_ORDERS_ERROR"))

    async def _show_active_orders(self, query: CallbackQuery) -> None:
        """Show active orders"""
        try:
            orders = await self.admin_service.get_active_orders()

            if not orders:
                text = i18n.get_text("ADMIN_ACTIVE_ORDERS_TITLE", user_id=query.from_user.id) + "\n\n" + i18n.get_text("ADMIN_NO_ACTIVE_ORDERS", user_id=query.from_user.id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                ]
            else:
                text = (
                    f"{i18n.get_text('ADMIN_ACTIVE_ORDERS_TITLE', user_id=query.from_user.id)} ({len(orders)})\n\n"
                    f"{i18n.get_text('ADMIN_ACTIVE_ORDERS_LIST', user_id=query.from_user.id)}"
                )
                keyboard = []
                for order in orders[:10]:  # Show max 10 orders
                    order_summary = (
                        f"#{order['order_id']} - {order['customer_name']} - "
                        f"{order['status'].capitalize()}"
                    )
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order['order_id']}",
                            )
                        ]
                    )
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 ACTIVE ORDERS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("ACTIVE_ORDERS_ERROR"))

    async def _show_all_orders(self, query: CallbackQuery) -> None:
        """Show all orders"""
        try:
            orders = await self.admin_service.get_all_orders()

            if not orders:
                text = i18n.get_text("ADMIN_ALL_ORDERS_TITLE", user_id=query.from_user.id) + "\n\n" + i18n.get_text("ADMIN_NO_ORDERS_FOUND", user_id=query.from_user.id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                ]
            else:
                text = f"{i18n.get_text('ADMIN_ALL_ORDERS_TITLE', user_id=query.from_user.id)} ({len(orders)})"
                keyboard = []
                for order in orders[:15]:  # Show max 15
                    order_summary = (
                        f"#{order['order_id']} - {order['customer_name']} - "
                        f"{order['status'].capitalize()}"
                    )
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order['order_id']}",
                            )
                        ]
                    )
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 ALL ORDERS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("ALL_ORDERS_ERROR"))

    async def _show_completed_orders(self, query: CallbackQuery) -> None:
        """Show completed (delivered) orders"""
        try:
            orders = await self.admin_service.get_completed_orders()

            if not orders:
                text = i18n.get_text("ADMIN_COMPLETED_ORDERS_TITLE", user_id=query.from_user.id) + "\n\n" + i18n.get_text("ADMIN_NO_COMPLETED_ORDERS", user_id=query.from_user.id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                ]
            else:
                text = f"{i18n.get_text('ADMIN_COMPLETED_ORDERS_TITLE', user_id=query.from_user.id)} ({len(orders)})"
                keyboard = []
                for order in orders[:15]:  # Show max 15
                    order_summary = (
                        f"#{order['order_id']} - {order['customer_name']} - "
                        f"₪{order['total']:.2f}"
                    )
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order['order_id']}",
                            )
                        ]
                    )
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 COMPLETED ORDERS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("ALL_ORDERS_ERROR"))

    async def _show_customers(self, query: CallbackQuery) -> None:
        """Show all customers"""
        try:
            customers = await self.admin_service.get_all_customers()

            if not customers:
                text = i18n.get_text("ADMIN_CUSTOMERS_TITLE", user_id=query.from_user.id) + "\n\n" + i18n.get_text("ADMIN_NO_CUSTOMERS", user_id=query.from_user.id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                ]
            else:
                text = f"{i18n.get_text('ADMIN_CUSTOMERS_TITLE', user_id=query.from_user.id)} ({len(customers)})"
                keyboard = []
                for customer in customers[:15]:  # Show max 15
                    customer_summary = f"👤 {customer['full_name']} (ID: {customer['customer_id']})"
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                customer_summary,
                                callback_data=f"admin_customer_{customer['customer_id']}",
                            )
                        ]
                    )
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=query.from_user.id), callback_data="admin_back"
                        )
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 CUSTOMERS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("CUSTOMERS_ERROR"))

    async def _show_customer_details(self, query: CallbackQuery, customer_id: int) -> None:
        """Show details for a specific customer."""
        try:
            self.logger.info("📊 SHOWING CUSTOMER DETAILS FOR #%s", customer_id)
            user_id = query.from_user.id
            
            # Get all customers and find the specific one
            customers = await self.admin_service.get_all_customers()
            customer = next((c for c in customers if c['customer_id'] == customer_id), None)
            
            if not customer:
                await query.edit_message_text(i18n.get_text("ADMIN_CUSTOMER_NOT_FOUND", user_id=user_id))
                return

            # Format customer details
            details = [
                i18n.get_text("ADMIN_CUSTOMER_DETAILS_TITLE", user_id=user_id).format(name=customer['full_name'], id=customer['customer_id']),
                i18n.get_text("ADMIN_CUSTOMER_TELEGRAM_ID", user_id=user_id).format(telegram_id=customer['telegram_id']),
                i18n.get_text("ADMIN_CUSTOMER_PHONE", user_id=user_id).format(phone=customer['phone_number']),
                i18n.get_text("ADMIN_CUSTOMER_LANGUAGE", user_id=user_id).format(language=customer['language'].upper() if customer['language'] else 'EN'),
                i18n.get_text("ADMIN_CUSTOMER_JOINED", user_id=user_id).format(
                    date=customer['created_at'].strftime('%Y-%m-%d %H:%M') if customer['created_at'] else "Unknown"
                ),
            ]
            
            if customer.get('delivery_address'):
                details.append(i18n.get_text("ADMIN_CUSTOMER_ADDRESS", user_id=user_id).format(address=customer['delivery_address']))
            
            details.extend([
                "",
                i18n.get_text("ADMIN_CUSTOMER_STATS", user_id=user_id),
                i18n.get_text("ADMIN_CUSTOMER_TOTAL_ORDERS", user_id=user_id).format(orders=customer['total_orders']),
                i18n.get_text("ADMIN_CUSTOMER_TOTAL_SPENT", user_id=user_id).format(amount=customer['total_spent']),
            ])
            
            if customer['total_orders'] > 0:
                avg_order = customer['total_spent'] / customer['total_orders']
                details.append(i18n.get_text("ADMIN_CUSTOMER_AVG_ORDER", user_id=user_id).format(avg=avg_order))
            
            customer_text = "\n".join(details)
            
            # Create keyboard with back button
            keyboard = [
                [InlineKeyboardButton(i18n.get_text("ADMIN_BACK_TO_CUSTOMERS", user_id=user_id), callback_data="admin_customers")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                customer_text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 CUSTOMER DETAILS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("CUSTOMER_DETAILS_ERROR"))

    async def _show_order_details(self, query: CallbackQuery, order_id: int) -> None:
        """Show details for a specific order."""
        try:
            self.logger.info("📊 SHOWING ORDER DETAILS FOR #%s", order_id)
            user_id = query.from_user.id
            order_details = await self._get_formatted_order_details(order_id, user_id)

            if not order_details:
                await query.edit_message_text(i18n.get_text("ADMIN_ORDER_NOT_FOUND", user_id=user_id))
                return

            keyboard = self._create_order_details_keyboard(order_id, user_id)
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                order_details, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 ORDER DETAILS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("ORDER_DETAILS_ERROR"))

    async def _get_formatted_order_details(self, order_id: int, user_id: int = None) -> str | None:
        """Helper to get and format order details."""
        order_info = await self.admin_service.get_order_by_id(order_id)

        if not order_info:
            return None

        details = [
            i18n.get_text("ADMIN_ORDER_DETAILS_TITLE", user_id=user_id).format(number=order_info["order_number"], id=order_info["order_id"]),
            i18n.get_text("ADMIN_CUSTOMER_LABEL", user_id=user_id).format(name=order_info["customer_name"]),
            i18n.get_text("ADMIN_PHONE_LABEL", user_id=user_id).format(phone=order_info["customer_phone"]),
            i18n.get_text("ADMIN_STATUS_LABEL", user_id=user_id).format(status=order_info["status"].capitalize()),
            i18n.get_text("ADMIN_TOTAL_LABEL", user_id=user_id).format(amount=order_info["total"]),
            i18n.get_text("ADMIN_CREATED_LABEL", user_id=user_id).format(
                datetime=(order_info["created_at"] or datetime.utcnow()).strftime('%Y-%m-%d %H:%M')
            ),
        ]
        if order_info.get("items"):
            details.append(f"\n{i18n.get_text('ADMIN_ITEMS_LABEL', user_id=user_id)}")
            for item in order_info["items"]:
                price = item.get('total_price', item.get('price', 0))
                from src.utils.helpers import translate_product_name
                translated_name = translate_product_name(item["product_name"], item.get("options", {}), user_id)
                details.append(
                    i18n.get_text("ADMIN_ITEM_LINE", user_id=user_id).format(
                        name=translated_name,
                        quantity=item["quantity"],
                        price=price
                    )
                )
        return "\n".join(details)

    def _create_order_details_keyboard(
        self, order_id: int, user_id: int = None
    ) -> list[list[InlineKeyboardButton]]:
        """Creates the keyboard for the order details view."""
        statuses = ["pending", "confirmed", "preparing", "ready", "delivered"]
        keyboard = [
            [
                InlineKeyboardButton(
                    i18n.get_text("ADMIN_SET_STATUS", user_id=user_id).format(status=status.capitalize()),
                    callback_data=f"admin_status_{order_id}_{status}",
                )
            ]
            for status in statuses
        ]
        keyboard.append(
            [InlineKeyboardButton(i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=user_id), callback_data="admin_back")]
        )
        return keyboard

    async def _update_order_status(
        self,
        query: CallbackQuery,
        order_id: int,
        new_status: str,
        admin_telegram_id: int,
    ) -> None:
        """Update the status of an order."""
        try:
            self.logger.info(
                "🔄 UPDATING STATUS for order #%s to %s by admin %s",
                order_id,
                new_status,
                admin_telegram_id,
            )

            success = await self.admin_service.update_order_status(
                order_id=order_id,
                new_status=new_status,
                admin_telegram_id=admin_telegram_id,
            )

            if success:
                await query.answer(i18n.get_text("ADMIN_STATUS_UPDATED", user_id=admin_telegram_id).format(status=new_status))
                await self._show_order_details(query, order_id)
            else:
                await query.message.reply_text(i18n.get_text("ADMIN_STATUS_UPDATE_ERROR", user_id=admin_telegram_id).format(error="Failed to update status"))

        except (BusinessLogicError, ValueError) as e:
            self.logger.error("💥 STATUS UPDATE ERROR: %s", e, exc_info=True)
            await query.message.reply_text(i18n.get_text("ADMIN_STATUS_UPDATE_ERROR", user_id=admin_telegram_id).format(error=e))

    async def _start_status_update(self, query: CallbackQuery) -> int:
        """Start conversation to update an order's status."""
        await query.message.reply_text(i18n.get_text("ADMIN_ORDER_ID_PROMPT", user_id=query.from_user.id))
        return AWAITING_ORDER_ID

    async def show_order_details_for_status_update(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Show order details and prompt for status update."""
        order_id_input = update.message.text.strip()

        # First, try numeric conversion for standard IDs
        order_id: int | None = None
        if order_id_input.isdigit():
            try:
                order_id = int(order_id_input)
            except OverflowError:
                order_id = None

        # Fallback: maybe user pasted the long order number like ORD-20250705...
        if order_id is None:
            all_orders = await self.admin_service.get_all_orders()
            matching = next(
                (
                    o for o in all_orders
                    if o["order_number"] == order_id_input or o["order_number"].lstrip("#") == order_id_input
                ),
                None,
            )
            if matching:
                order_id = matching["order_id"]

        if order_id is None:
            await update.message.reply_text(i18n.get_text("ADMIN_ORDER_ID_NOT_FOUND", user_id=update.effective_user.id))
            return AWAITING_ORDER_ID

        # Fetch formatted details and send as a regular message with inline keyboard
        order_details = await self._get_formatted_order_details(order_id, update.effective_user.id)
        if not order_details:
            await update.message.reply_text(i18n.get_text("ADMIN_ORDER_ID_TRY_ANOTHER", user_id=update.effective_user.id))
            return AWAITING_ORDER_ID

        keyboard = self._create_order_details_keyboard(order_id, update.effective_user.id)
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            order_details, parse_mode="HTML", reply_markup=reply_markup
        )

        context.user_data["order_id_for_status_update"] = order_id
        return AWAITING_STATUS_UPDATE

    async def _is_admin_user(self, telegram_id: int) -> bool:
        """Check if a user is an admin."""
        # Simple admin check - compare with configured admin chat ID
        config = self.container.get_config()
        admin_chat_id = getattr(config, 'admin', {}).get('chat_id', None)
        
        if admin_chat_id:
            # Convert to int if it's a string
            try:
                admin_id = int(admin_chat_id)
                return telegram_id == admin_id
            except (ValueError, TypeError):
                pass
        
        # Fallback: check if user ID matches common admin patterns
        # This is a simple fallback - in production you'd want a proper admin system
        return str(telegram_id) in ['598829473']  # Add your admin user IDs here


def register_admin_handlers(application: Application):
    """Register admin handlers"""
    handler = AdminHandler()

    # Admin command handler
    application.add_handler(CommandHandler("admin", handler.handle_admin_command))

    # Admin callback handlers
    application.add_handler(
        CallbackQueryHandler(handler.handle_admin_callback, pattern="^admin_")
    )

    # Admin conversation handler for status updates
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handler._start_status_update, pattern="^admin_update_status$")
        ],
        states={
            AWAITING_ORDER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler.show_order_details_for_status_update)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda u, c: ConversationHandler.END)
            ],
    )

    application.add_handler(conv_handler)

    # Analytics callback handlers
    application.add_handler(
        CallbackQueryHandler(handler._handle_analytics_callback, pattern="^analytics_")
    )


# Simple handler function for compatibility
async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple admin handler for compatibility"""
    handler = AdminHandler()
    
    if update.message and update.message.text == "/admin":
        return await handler.handle_admin_command(update, context)
    elif update.callback_query and update.callback_query.data.startswith("admin_"):
        return await handler.handle_admin_callback(update, context)
    
    return None


RESTART = "admin_dashboard"
END = ConversationHandler.END
