"""
Admin Handler for the Telegram bot.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

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
AWAITING_ORDER_ID, AWAITING_STATUS_UPDATE, AWAITING_PRODUCT_DETAILS, AWAITING_PRODUCT_UPDATE, AWAITING_PRODUCT_DELETE_CONFIRM = range(5)

# Import the new states from states.py
from src.states import (
    AWAITING_PRODUCT_NAME,
    AWAITING_PRODUCT_DESCRIPTION,
    AWAITING_PRODUCT_CATEGORY,
    AWAITING_PRODUCT_PRICE,
    AWAITING_PRODUCT_CONFIRMATION,
    END
)

# Category management states
AWAITING_CATEGORY_NAME = 10
AWAITING_CATEGORY_NAME_EDIT = 11

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
        elif data == "admin_menu_management":
            await self._show_menu_management_dashboard(query)
        elif data == "admin_products_management":
            await self._show_products_management(query)
        elif data == "admin_view_products":
            await self._show_all_products(query)
        elif data == "admin_add_product":
            return await self._start_add_product(query)
        elif data == "admin_remove_products":
            await self._show_remove_products_list(query)
        
        elif data.startswith("admin_quick_"):
            await self._handle_quick_action(query, data)
        elif data.startswith("admin_product_"):
            await self._handle_product_callback(query, data)
        elif data == "admin_category_management":
            await self._show_category_management(query)
        elif data == "admin_view_categories":
            await self._show_all_categories(query)
        elif data == "admin_add_category":
            return await self._start_add_category(query)
        elif data.startswith("admin_edit_category_"):
            category = data.replace("admin_edit_category_", "")
            await self._show_edit_category(query, category)
        elif data.startswith("admin_edit_category_name_"):
            category = data.replace("admin_edit_category_name_", "")
            return await self._start_edit_category_name(query, category)
        elif data.startswith("admin_delete_category_confirm_"):
            # Extract category name from "admin_delete_category_confirm_CATEGORY_NAME"
            # The category name is everything after "admin_delete_category_confirm_"
            category = data.replace("admin_delete_category_confirm_", "")
            await self._delete_category_confirmed(query, category)
        elif data.startswith("admin_delete_category_"):
            category = data.replace("admin_delete_category_", "")
            await self._show_delete_category_confirmation(query, category)
        elif data.startswith("admin_category_"):
            category = data.replace("admin_category_", "")
            await self._show_products_in_category(query, category)
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
                [
                    InlineKeyboardButton(i18n.get_text("ADMIN_MENU_MANAGEMENT", user_id=user_id), callback_data="admin_menu_management")
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

    # Menu Management Methods
    async def _show_menu_management_dashboard(self, query: CallbackQuery) -> None:
        """Show menu management dashboard"""
        try:
            user_id = query.from_user.id
            
            # Get product statistics
            products = await self.admin_service.get_all_products_for_admin()
            total_products = len(products)
            active_products = len([p for p in products if p["is_active"]])
            inactive_products = total_products - active_products
            categories = await self.admin_service.get_product_categories_list()
            
            text = (
                i18n.get_text("ADMIN_MENU_MANAGEMENT_TITLE", user_id=user_id) + "\n\n" +
                i18n.get_text("ADMIN_MENU_MANAGEMENT_SUMMARY", user_id=user_id).format(
                    total=total_products,
                    active=active_products,
                    inactive=inactive_products,
                    categories=len(categories)
                ) + "\n\n" +
                i18n.get_text("ADMIN_MENU_MANAGEMENT_ACTIONS", user_id=user_id)
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCTS_MANAGEMENT", user_id=user_id),
                        callback_data="admin_products_management"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_CATEGORY_MANAGEMENT", user_id=user_id),
                        callback_data="admin_category_management"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_MENU_MANAGEMENT_BACK", user_id=user_id),
                        callback_data="admin_back"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing menu management dashboard: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _show_products_management(self, query: CallbackQuery) -> None:
        """Show products management dashboard"""
        try:
            user_id = query.from_user.id
            products = await self.admin_service.get_all_products_for_admin()
            
            text = (
                i18n.get_text("ADMIN_PRODUCTS_MANAGEMENT_TITLE", user_id=user_id) + "\n\n" +
                i18n.get_text("ADMIN_PRODUCTS_MANAGEMENT_SUMMARY", user_id=user_id).format(
                    total=len(products),
                    active=len([p for p in products if p["is_active"]]),
                    inactive=len([p for p in products if not p["is_active"]])
                ) + "\n\n" +
                i18n.get_text("ADMIN_PRODUCTS_MANAGEMENT_ACTIONS", user_id=user_id)
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCTS_MANAGEMENT_VIEW", user_id=user_id),
                        callback_data="admin_view_products"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCTS_MANAGEMENT_ADD", user_id=user_id),
                        callback_data="admin_add_product"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCTS_MANAGEMENT_BACK", user_id=user_id),
                        callback_data="admin_menu_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing products management: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _show_all_products(self, query: CallbackQuery) -> None:
        """Show all products for admin management"""
        try:
            user_id = query.from_user.id
            products = await self.admin_service.get_all_products_for_admin()
            
            if not products:
                text = i18n.get_text("ADMIN_NO_PRODUCTS", user_id=user_id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_PRODUCT_BACK_TO_MANAGEMENT", user_id=user_id),
                            callback_data="admin_products_management"
                        )
                    ]
                ]
            else:
                # Build text with product count
                text = i18n.get_text("ADMIN_PRODUCTS_TITLE", user_id=user_id) + f"\n\n{i18n.get_text('ADMIN_PRODUCT_TOTAL_COUNT', user_id=user_id).format(count=len(products))}"
                
                keyboard = []
                
                # Add product list
                for product in products:
                    status_text = i18n.get_text("ADMIN_PRODUCT_ACTIVE", user_id=user_id) if product["is_active"] else i18n.get_text("ADMIN_PRODUCT_INACTIVE", user_id=user_id)
                    product_text = i18n.get_text("ADMIN_PRODUCT_BUTTON_FORMAT", user_id=user_id).format(
                        name=product["name"],
                        category=product["category"],
                        price=product["price"],
                        status=status_text
                    )
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            product_text,
                            callback_data=f"admin_product_details_{product['id']}"
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_BACK_TO_PRODUCTS", user_id=user_id),
                        callback_data="admin_products_management"
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            except Exception as edit_error:
                if "Message is not modified" in str(edit_error):
                    # Message content is identical, just answer the callback
                    await query.answer()
                else:
                    # Re-raise other errors
                    raise edit_error
            
        except Exception as e:
            self.logger.error("Error showing all products: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _show_product_categories(self, query: CallbackQuery) -> None:
        """Show product categories for admin management"""
        try:
            user_id = query.from_user.id
            categories = await self.admin_service.get_product_categories_list()
            
            if not categories:
                text = i18n.get_text("ADMIN_NO_CATEGORIES", user_id=user_id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_PRODUCT_BACK_TO_MANAGEMENT", user_id=user_id),
                            callback_data="admin_menu_management"
                        )
                    ]
                ]
            else:
                # Build text with category count
                text = i18n.get_text("ADMIN_CATEGORIES_TITLE", user_id=user_id) + f"\n\n{i18n.get_text('ADMIN_CATEGORY_TOTAL_COUNT', user_id=user_id).format(count=len(categories))}"
                
                keyboard = []
                
                # Add category list
                for category in categories:
                    # Translate category name based on user's language
                    from src.utils.i18n import translate_category_name
                    translated_category = translate_category_name(category, user_id=user_id)
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            f"📂 {translated_category}",
                            callback_data=f"admin_category_{category}"
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_BACK_TO_MANAGEMENT", user_id=user_id),
                        callback_data="admin_menu_management"
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            except Exception as edit_error:
                if "Message is not modified" in str(edit_error):
                    # Message content is identical, just answer the callback
                    await query.answer()
                else:
                    # Re-raise other errors
                    raise edit_error
            
        except Exception as e:
            self.logger.error("Error showing product categories: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _show_products_in_category(self, query: CallbackQuery, category: str) -> None:
        """Show products within a specific category for admin management"""
        try:
            user_id = query.from_user.id
            products = await self.admin_service.get_products_by_category_admin(category)
            
            if not products:
                text = i18n.get_text("ADMIN_NO_PRODUCTS_IN_CATEGORY", user_id=user_id).format(category=category)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_PRODUCT_BACK_TO_CATEGORIES", user_id=user_id),
                            callback_data="admin_view_products"
                        )
                    ]
                ]
            else:
                # Build text with category name and product count
                # Translate category name based on user's language
                from src.utils.i18n import translate_category_name
                translated_category = translate_category_name(category, user_id=user_id)
                
                text = f"📂 <b>{translated_category}</b>\n\n{i18n.get_text('ADMIN_PRODUCTS_IN_CATEGORY_TITLE', user_id=user_id).format(category=translated_category, count=len(products))}"
                
                keyboard = []
                
                # Add product list
                for product in products:
                    status_text = i18n.get_text("ADMIN_PRODUCT_ACTIVE", user_id=user_id) if product["is_active"] else i18n.get_text("ADMIN_PRODUCT_INACTIVE", user_id=user_id)
                    product_text = i18n.get_text("ADMIN_PRODUCT_BUTTON_FORMAT", user_id=user_id).format(
                        name=product["name"],
                        category=product["category"],
                        price=product["price"],
                        status=status_text
                    )
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            product_text,
                            callback_data=f"admin_product_details_{product['id']}"
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_BACK_TO_CATEGORIES", user_id=user_id),
                        callback_data="admin_view_products"
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            except Exception as edit_error:
                if "Message is not modified" in str(edit_error):
                    # Message content is identical, just answer the callback
                    await query.answer()
                else:
                    # Re-raise other errors
                    raise edit_error
            
        except Exception as e:
            self.logger.error("Error showing products in category: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _show_category_management(self, query: CallbackQuery) -> None:
        """Show category management dashboard"""
        try:
            user_id = query.from_user.id
            categories = await self.admin_service.get_product_categories_list()
            
            # Get total products count for summary
            products = await self.admin_service.get_all_products_for_admin()
            total_products = len(products)
            
            text = (
                i18n.get_text("ADMIN_CATEGORY_MANAGEMENT_TITLE", user_id=user_id) + "\n\n" +
                i18n.get_text("ADMIN_CATEGORY_MANAGEMENT_SUMMARY", user_id=user_id).format(
                    total=len(categories),
                    products=total_products
                ) + "\n\n" +
                i18n.get_text("ADMIN_CATEGORY_MANAGEMENT_ACTIONS", user_id=user_id)
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_CATEGORY_MANAGEMENT_VIEW", user_id=user_id),
                        callback_data="admin_view_categories"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_CATEGORY_MANAGEMENT_ADD", user_id=user_id),
                        callback_data="admin_add_category"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_CATEGORY_MANAGEMENT_BACK", user_id=user_id),
                        callback_data="admin_menu_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing category management: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _show_all_categories(self, query: CallbackQuery) -> None:
        """Show all categories for admin management"""
        try:
            user_id = query.from_user.id
            categories = await self.admin_service.get_product_categories_list()
            
            if not categories:
                text = i18n.get_text("ADMIN_NO_CATEGORIES", user_id=user_id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_CATEGORY_BACK_TO_MANAGEMENT", user_id=user_id),
                            callback_data="admin_category_management"
                        )
                    ]
                ]
            else:
                # Build text with category count
                text = i18n.get_text("ADMIN_CATEGORIES_TITLE", user_id=user_id) + f"\n\n{i18n.get_text('ADMIN_CATEGORY_TOTAL_COUNT', user_id=user_id).format(count=len(categories))}"
                
                keyboard = []
                
                # Add category list with product counts
                for category in categories:
                    # Get all products in category (including inactive ones) for accurate count
                    from src.db.operations import get_all_products_by_category
                    products = get_all_products_by_category(category)
                    product_count = len(products)
                    
                    # Translate category name based on user's language
                    from src.utils.i18n import translate_category_name
                    translated_category = translate_category_name(category, user_id=user_id)
                    
                    category_text = i18n.get_text("ADMIN_CATEGORY_BUTTON_FORMAT", user_id=user_id).format(
                        name=translated_category,
                        count=product_count
                    )
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            category_text,
                            callback_data=f"admin_edit_category_{category}"
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_CATEGORY_BACK_TO_MANAGEMENT", user_id=user_id),
                        callback_data="admin_category_management"
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            except Exception as edit_error:
                if "Message is not modified" in str(edit_error):
                    # Message content is identical, just answer the callback
                    await query.answer()
                else:
                    # Re-raise other errors
                    raise edit_error
            
        except Exception as e:
            self.logger.error("Error showing all categories: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _show_edit_category(self, query: CallbackQuery, category: str) -> None:
        """Show category edit options"""
        try:
            user_id = query.from_user.id
            # Get all products in category (including inactive ones) for accurate count
            from src.db.operations import get_all_products_by_category
            products = get_all_products_by_category(category)
            product_count = len(products)
            
            # Translate category name based on user's language
            from src.utils.i18n import translate_category_name
            translated_category = translate_category_name(category, user_id=user_id)
            
            text = i18n.get_text("ADMIN_CATEGORY_EDIT_TITLE", user_id=user_id).format(category=translated_category, count=product_count)
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_CATEGORY_EDIT_NAME", user_id=user_id),
                        callback_data=f"admin_edit_category_name_{category}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_CATEGORY_DELETE", user_id=user_id),
                        callback_data=f"admin_delete_category_{category}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_CATEGORY_BACK_TO_LIST", user_id=user_id),
                        callback_data="admin_view_categories"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing edit category: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _start_add_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the add category conversation"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            self.logger.info(f"🔧 Starting add category conversation for user {user_id}")
            text = i18n.get_text("ADMIN_CATEGORY_ADD_PROMPT", user_id=user_id)
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_category_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_CATEGORY_NAME
            
        except Exception as e:
            self.logger.error("Error starting add category: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_category_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category name input"""
        try:
            user_id = update.effective_user.id
            category_name = update.message.text.strip()
            if len(category_name) < 2:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_CATEGORY_NAME_TOO_SHORT", user_id=user_id)
                )
                return AWAITING_CATEGORY_NAME
            # Check if category already exists
            existing_categories = await self.admin_service.get_product_categories_list()
            if category_name.lower() in [cat.lower() for cat in existing_categories]:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_CATEGORY_ALREADY_EXISTS", user_id=user_id).format(category=category_name)
                )
                return AWAITING_CATEGORY_NAME
            # Create the category
            result = await self.admin_service.create_category(category_name)
            if result["success"]:
                # Show the updated category list
                class FakeQuery:
                    def __init__(self, message, from_user):
                        self.message = message
                        self.from_user = from_user
                        self.edit_message_text = message.reply_text
                fake_query = FakeQuery(update.message, update.effective_user)
                await self._show_all_categories(fake_query)
                return ConversationHandler.END
            else:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_CATEGORY_ADD_ERROR", user_id=user_id).format(error=result["error"])
                )
            return ConversationHandler.END
        except Exception as e:
            self.logger.error("Error handling category name input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _start_edit_category_name(self, query: CallbackQuery, category: str) -> int:
        """Start the edit category name conversation"""
        try:
            user_id = query.from_user.id
            text = i18n.get_text("ADMIN_CATEGORY_EDIT_NAME_PROMPT", user_id=user_id).format(category=category)
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data=f"admin_edit_category_{category}"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            # Store the old category name in context
            context = query.from_user.id
            context.user_data["old_category_name"] = category
            
            return AWAITING_CATEGORY_NAME_EDIT
            
        except Exception as e:
            self.logger.error("Error starting edit category name: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_category_name_edit_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category name edit input"""
        try:
            user_id = update.effective_user.id
            new_category_name = update.message.text.strip()
            old_category_name = context.user_data.get("old_category_name")
            
            if len(new_category_name) < 2:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_CATEGORY_NAME_TOO_SHORT", user_id=user_id)
                )
                return AWAITING_CATEGORY_NAME_EDIT
            
            # Check if new category name already exists
            existing_categories = await self.admin_service.get_product_categories_list()
            if new_category_name.lower() in [cat.lower() for cat in existing_categories if cat != old_category_name]:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_CATEGORY_ALREADY_EXISTS", user_id=user_id).format(category=new_category_name)
                )
                return AWAITING_CATEGORY_NAME_EDIT
            
            # Update the category (this would need to be implemented in the service)
            result = await self.admin_service.update_category(old_category_name, new_category_name)
            
            if result["success"]:
                success_text = i18n.get_text("ADMIN_CATEGORY_UPDATE_SUCCESS", user_id=user_id).format(
                    old_category=old_category_name, new_category=new_category_name
                )
                
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_CATEGORY_BACK_TO_LIST", user_id=user_id),
                            callback_data="admin_view_categories"
                        )
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(success_text, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_CATEGORY_UPDATE_ERROR", user_id=user_id).format(error=result["error"])
                )
            
            return ConversationHandler.END
            
        except Exception as e:
            self.logger.error("Error handling category name edit input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _show_delete_category_confirmation(self, query: CallbackQuery, category: str) -> None:
        """Show category deletion confirmation"""
        try:
            user_id = query.from_user.id
            self.logger.info(f"Showing delete confirmation for category: '{category}'")
            
            # Get all products in category (including inactive ones) for accurate count
            from src.db.operations import get_all_products_by_category
            products = get_all_products_by_category(category)
            product_count = len(products)
            
            self.logger.info(f"Found {product_count} products in category '{category}'")
            
            # Translate category name based on user's language
            from src.utils.i18n import translate_category_name
            translated_category = translate_category_name(category, user_id=user_id)
            
            if product_count > 0:
                text = i18n.get_text("ADMIN_CATEGORY_DELETE_WITH_PRODUCTS", user_id=user_id).format(
                    category=translated_category, count=product_count
                )
            else:
                text = i18n.get_text("ADMIN_CATEGORY_DELETE_CONFIRM", user_id=user_id).format(category=translated_category)
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_CATEGORY_DELETE_YES", user_id=user_id),
                        callback_data=f"admin_delete_category_confirm_{category}"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_CATEGORY_DELETE_NO", user_id=user_id),
                        callback_data=f"admin_edit_category_{category}"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing delete category confirmation: %s", e, exc_info=True)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _delete_category_confirmed(self, query: CallbackQuery, category: str) -> None:
        """Handle confirmed category deletion"""
        try:
            user_id = query.from_user.id
            self.logger.info(f"Deleting category: '{category}' for user {user_id}")
            
            # Delete the category (this would need to be implemented in the service)
            result = await self.admin_service.delete_category(category)
            
            if result["success"]:
                success_text = i18n.get_text("ADMIN_CATEGORY_DELETE_SUCCESS", user_id=user_id).format(category=category)
                
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_CATEGORY_BACK_TO_LIST", user_id=user_id),
                            callback_data="admin_view_categories"
                        )
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(success_text, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await query.edit_message_text(
                    i18n.get_text("ADMIN_CATEGORY_DELETE_ERROR", user_id=user_id).format(error=result["error"])
                )
            
        except Exception as e:
            self.logger.error("Error deleting category: %s", e, exc_info=True)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _start_add_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the step-by-step add product conversation"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            self.logger.info(f"🚀 Starting step-by-step product creation for user {user_id}")
            self.logger.info(f"🚀 Setting conversation state to AWAITING_PRODUCT_NAME ({AWAITING_PRODUCT_NAME})")
            text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_NAME", user_id=user_id)
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_menu_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_PRODUCT_NAME
            
        except Exception as e:
            self.logger.error("Error starting add product: %s", e)
            await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=update.callback_query.from_user.id))
            return ConversationHandler.END

    async def _handle_add_product_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle product details input for adding new product"""
        try:
            user_id = update.effective_user.id
            text = update.message.text
            # Parse product details from text
            product_data = self._parse_product_input(text)
            if not product_data:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_PRODUCT_INVALID_INPUT", user_id=user_id)
                )
                return AWAITING_PRODUCT_DETAILS
            # Create product
            result = await self.admin_service.create_new_product(
                name=product_data["name"],
                description=product_data["description"],
                category=product_data["category"],
                price=product_data["price"]
            )
            if result["success"]:
                # Show the updated product list
                # Use a fake CallbackQuery for compatibility
                class FakeQuery:
                    def __init__(self, message, from_user):
                        self.message = message
                        self.from_user = from_user
                        self.edit_message_text = message.reply_text
                fake_query = FakeQuery(update.message, update.effective_user)
                await self._show_all_products(fake_query)
                return ConversationHandler.END
            else:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_ADD_PRODUCT_ERROR", user_id=user_id).format(error=result["error"])
                )
            return ConversationHandler.END
        except Exception as e:
            self.logger.error("Error handling add product input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    # Step-by-step product creation handlers
    async def _handle_product_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle product name input"""
        try:
            user_id = update.effective_user.id
            name = update.message.text.strip()
            
            self.logger.info(f"🔍 Handling product name input: '{name}' for user {user_id}")
            self.logger.info(f"🔍 Current conversation state: {context.user_data.get('conversation_state', 'None')}")
            
            if len(name) < 2:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_ADD_PRODUCT_NAME_TOO_SHORT", user_id=user_id)
                )
                return AWAITING_PRODUCT_NAME
            
            # Store name in context
            context.user_data["product_name"] = name
            
            # Ask for description
            text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_DESCRIPTION", user_id=user_id).format(name=name)
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_menu_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_PRODUCT_DESCRIPTION
            
        except Exception as e:
            self.logger.error("Error handling product name input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_product_description_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle product description input"""
        try:
            user_id = update.effective_user.id
            description = update.message.text.strip()
            
            if len(description) < 5:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_ADD_PRODUCT_DESCRIPTION_TOO_SHORT", user_id=user_id)
                )
                return AWAITING_PRODUCT_DESCRIPTION
            
            # Store description in context
            context.user_data["product_description"] = description
            name = context.user_data["product_name"]
            
            # Ask for category
            text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_CATEGORY", user_id=user_id).format(
                name=name, description=description
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_ADD_PRODUCT_CATEGORY_BREAD", user_id=user_id),
                        callback_data="admin_add_product_category_bread"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_ADD_PRODUCT_CATEGORY_SPICE", user_id=user_id),
                        callback_data="admin_add_product_category_spice"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_ADD_PRODUCT_CATEGORY_SPREAD", user_id=user_id),
                        callback_data="admin_add_product_category_spread"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_ADD_PRODUCT_CATEGORY_BEVERAGE", user_id=user_id),
                        callback_data="admin_add_product_category_beverage"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_ADD_PRODUCT_CATEGORY_OTHER", user_id=user_id),
                        callback_data="admin_add_product_category_other"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_menu_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_PRODUCT_CATEGORY
            
        except Exception as e:
            self.logger.error("Error handling product description input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_product_category_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle product category selection"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            data = query.data
            
            # Extract category from callback data
            category_map = {
                "admin_add_product_category_bread": "bread",
                "admin_add_product_category_spice": "spice", 
                "admin_add_product_category_spread": "spread",
                "admin_add_product_category_beverage": "beverage",
                "admin_add_product_category_other": "other"
            }
            
            category = category_map.get(data)
            if not category:
                await query.answer("Invalid category selection")
                return AWAITING_PRODUCT_CATEGORY
            
            # Store category in context
            context.user_data["product_category"] = category
            name = context.user_data["product_name"]
            description = context.user_data["product_description"]
            
            # Ask for price
            text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_PRICE", user_id=user_id).format(
                name=name, description=description, category=category
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_menu_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_PRODUCT_PRICE
            
        except Exception as e:
            self.logger.error("Error handling product category selection: %s", e)
            await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=update.callback_query.from_user.id))
            return ConversationHandler.END

    async def _handle_product_price_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle product price input"""
        try:
            user_id = update.effective_user.id
            price_text = update.message.text.strip()
            
            # Validate price
            try:
                price = float(price_text)
                if price <= 0:
                    await update.message.reply_text(
                        i18n.get_text("ADMIN_ADD_PRODUCT_PRICE_TOO_LOW", user_id=user_id)
                    )
                    return AWAITING_PRODUCT_PRICE
            except ValueError:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_ADD_PRODUCT_PRICE_INVALID", user_id=user_id)
                )
                return AWAITING_PRODUCT_PRICE
            
            # Store price in context
            context.user_data["product_price"] = price
            name = context.user_data["product_name"]
            description = context.user_data["product_description"]
            category = context.user_data["product_category"]
            
            # Show confirmation
            text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_CONFIRM", user_id=user_id).format(
                name=name, description=description, category=category, price=f"{price:.2f}"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_ADD_PRODUCT_CONFIRM_YES", user_id=user_id),
                        callback_data="admin_add_product_confirm_yes"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_ADD_PRODUCT_CONFIRM_NO", user_id=user_id),
                        callback_data="admin_add_product_confirm_no"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_PRODUCT_CONFIRMATION
            
        except Exception as e:
            self.logger.error("Error handling product price input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_product_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle product creation confirmation"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            data = query.data
            
            if data == "admin_add_product_confirm_yes":
                # Create the product
                name = context.user_data["product_name"]
                description = context.user_data["product_description"]
                category = context.user_data["product_category"]
                price = context.user_data["product_price"]
                
                result = await self.admin_service.create_new_product(
                    name=name,
                    description=description,
                    category=category,
                    price=price
                )
                
                if result["success"]:
                    product = result["product"]
                    success_text = i18n.get_text("ADMIN_ADD_PRODUCT_SUCCESS", user_id=user_id).format(
                        name=product["name"],
                        description=product["description"],
                        category=product["category"],
                        price=product["price"]
                    )
                    
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                i18n.get_text("ADMIN_PRODUCT_BACK_TO_MANAGEMENT", user_id=user_id),
                                callback_data="admin_menu_management"
                            )
                        ]
                    ]
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(success_text, parse_mode="HTML", reply_markup=reply_markup)
                else:
                    await query.edit_message_text(
                        i18n.get_text("ADMIN_ADD_PRODUCT_ERROR", user_id=user_id).format(error=result["error"])
                    )
                
                # Clear context data
                context.user_data.clear()
                return ConversationHandler.END
                
            elif data == "admin_add_product_confirm_no":
                # Start over
                context.user_data.clear()
                return await self._start_add_product(update, context)
            
        except Exception as e:
            self.logger.error("Error handling product confirmation: %s", e)
            await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=update.callback_query.from_user.id))
            return ConversationHandler.END



    async def _handle_product_callback(self, query: CallbackQuery, data: str) -> None:
        """Handle product-related callbacks"""
        try:
            user_id = query.from_user.id
            
            if data.startswith("admin_product_details_"):
                product_id = int(data.split("_")[-1])
                await self._show_product_details(query, product_id)
            elif data.startswith("admin_product_edit_"):
                product_id = int(data.split("_")[-1])
                return await self._start_edit_product(query, product_id)
            elif data.startswith("admin_product_delete_"):
                product_id = int(data.split("_")[-1])
                await self._show_delete_product_confirmation(query, product_id)
            elif data.startswith("admin_product_toggle_"):
                product_id = int(data.split("_")[-1])
                await self._toggle_product_status(query, product_id)
            elif data.startswith("admin_remove_product_"):
                product_id = int(data.split("_")[-1])
                await self._show_remove_product_confirmation(query, product_id)
            elif data == "admin_product_back_to_list":
                await self._show_all_products(query)
            elif data == "admin_product_back_to_management":
                await self._show_products_management(query)
            elif data.startswith("admin_product_yes_delete_"):
                # Handle delete confirmation
                product_id = int(data.split("_")[-1])
                await self._delete_product(query, product_id)
            elif data == "admin_product_no_delete":
                await self._show_all_products(query)
            elif data.startswith("admin_remove_yes_"):
                product_id = int(data.split("_")[-1])
                await self._remove_product_confirmed(query, product_id)
            elif data == "admin_remove_no":
                await self._show_remove_products_list(query)
            elif data.startswith("admin_add_product_category_"):
                # Handle category selection in step-by-step product creation
                return await self._handle_product_category_selection(query, None)
            elif data.startswith("admin_add_product_confirm_"):
                # Handle product confirmation in step-by-step product creation
                return await self._handle_product_confirmation(query, None)
                
        except Exception as e:
            self.logger.error("Error handling product callback: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _show_product_details(self, query: CallbackQuery, product_id: int) -> None:
        """Show detailed product information"""
        try:
            user_id = query.from_user.id
            products = await self.admin_service.get_all_products_for_admin()
            product = next((p for p in products if p["id"] == product_id), None)
            
            if not product:
                await query.message.reply_text(i18n.get_text("ADMIN_PRODUCT_NOT_FOUND", user_id=user_id))
                return
            
            status_text = i18n.get_text("ADMIN_PRODUCT_ACTIVE", user_id=user_id) if product["is_active"] else i18n.get_text("ADMIN_PRODUCT_INACTIVE", user_id=user_id)
            
            # Translate category name based on user's language
            from src.utils.i18n import translate_category_name
            translated_category = translate_category_name(product["category"], user_id=user_id)
            
            text = (
                i18n.get_text("ADMIN_PRODUCT_DETAILS", user_id=user_id) + "\n\n" +
                i18n.get_text("ADMIN_PRODUCT_NAME", user_id=user_id).format(name=product["name"]) + "\n" +
                i18n.get_text("ADMIN_PRODUCT_DESCRIPTION", user_id=user_id).format(description=product["description"]) + "\n" +
                i18n.get_text("ADMIN_PRODUCT_CATEGORY", user_id=user_id).format(category=translated_category) + "\n" +
                i18n.get_text("ADMIN_PRODUCT_PRICE", user_id=user_id).format(price=product["price"]) + "\n" +
                i18n.get_text("ADMIN_PRODUCT_STATUS", user_id=user_id).format(status=status_text) + "\n" +
                i18n.get_text("ADMIN_PRODUCT_CREATED", user_id=user_id).format(created_at=product["created_at"].strftime("%Y-%m-%d %H:%M"))
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_EDIT", user_id=user_id),
                        callback_data=f"admin_product_edit_{product_id}"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_DELETE", user_id=user_id),
                        callback_data=f"admin_product_delete_{product_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_TOGGLE_STATUS", user_id=user_id),
                        callback_data=f"admin_product_toggle_{product_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_BACK_TO_LIST", user_id=user_id),
                        callback_data="admin_product_back_to_list"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing product details: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _start_edit_product(self, query: CallbackQuery, product_id: int):
        """Start the edit product conversation"""
        try:
            user_id = query.from_user.id
            products = await self.admin_service.get_all_products_for_admin()
            product = next((p for p in products if p["id"] == product_id), None)
            
            if not product:
                await query.message.reply_text(i18n.get_text("ADMIN_PRODUCT_NOT_FOUND", user_id=user_id))
                return ConversationHandler.END
            
            text = (
                i18n.get_text("ADMIN_EDIT_PRODUCT_TITLE", user_id=user_id) + "\n\n" +
                i18n.get_text("ADMIN_EDIT_PRODUCT_INSTRUCTIONS", user_id=user_id) + "\n\n" +
                f"<b>Current Product:</b>\n" +
                f"Name: {product['name']}\n" +
                f"Description: {product['description']}\n" +
                f"Category: {product['category']}\n" +
                f"Price: ₪{product['price']:.2f}\n" +
                f"Status: {'active' if product['is_active'] else 'inactive'}"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data=f"admin_product_details_{product_id}"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            # Store product_id in context for the conversation
            context = query.data.split("_")[-1] if "_" in query.data else str(product_id)
            
            return AWAITING_PRODUCT_UPDATE
            
        except Exception as e:
            self.logger.error("Error starting edit product: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _show_remove_product_confirmation(self, query: CallbackQuery, product_id: int) -> None:
        """Show remove product confirmation"""
        try:
            user_id = query.from_user.id
            products = await self.admin_service.get_all_products_for_admin()
            product = next((p for p in products if p["id"] == product_id), None)
            
            if not product:
                await query.message.reply_text(i18n.get_text("ADMIN_PRODUCT_NOT_FOUND", user_id=user_id))
                return
            
            text = i18n.get_text("ADMIN_REMOVE_PRODUCT_CONFIRM", user_id=user_id).format(
                name=product["name"],
                category=product["category"],
                price=product["price"]
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_YES_DELETE", user_id=user_id),
                        callback_data=f"admin_remove_yes_{product_id}"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_NO_DELETE", user_id=user_id),
                        callback_data="admin_remove_no"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing remove confirmation: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _show_delete_product_confirmation(self, query: CallbackQuery, product_id: int) -> None:
        """Show delete product confirmation"""
        try:
            user_id = query.from_user.id
            products = await self.admin_service.get_all_products_for_admin()
            product = next((p for p in products if p["id"] == product_id), None)
            
            if not product:
                await query.message.reply_text(i18n.get_text("ADMIN_PRODUCT_NOT_FOUND", user_id=user_id))
                return
            
            text = i18n.get_text("ADMIN_DELETE_PRODUCT_CONFIRM", user_id=user_id).format(
                name=product["name"],
                category=product["category"],
                price=product["price"]
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_YES_DELETE", user_id=user_id),
                        callback_data=f"admin_product_yes_delete_{product_id}"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_NO_DELETE", user_id=user_id),
                        callback_data="admin_product_no_delete"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing delete confirmation: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _toggle_product_status(self, query: CallbackQuery, product_id: int) -> None:
        """Toggle product active/inactive status"""
        try:
            user_id = query.from_user.id
            products = await self.admin_service.get_all_products_for_admin()
            product = next((p for p in products if p["id"] == product_id), None)
            
            if not product:
                await query.message.reply_text(i18n.get_text("ADMIN_PRODUCT_NOT_FOUND", user_id=user_id))
                return
            
            # Toggle status
            new_status = not product["is_active"]
            result = await self.admin_service.update_existing_product(product_id, is_active=new_status)
            
            if result["success"]:
                status_text = "activated" if new_status else "deactivated"
                await query.answer(f"Product {status_text} successfully!")
                await self._show_product_details(query, product_id)
            else:
                await query.message.reply_text(
                    i18n.get_text("ADMIN_PRODUCT_STATUS_TOGGLE_ERROR", user_id=user_id).format(error=result["error"])
                )
                
        except Exception as e:
            self.logger.error("Error toggling product status: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _remove_product_confirmed(self, query: CallbackQuery, product_id: int) -> None:
        """Handle confirmed product removal"""
        try:
            user_id = query.from_user.id
            result = await self.admin_service.delete_existing_product(product_id)
            
            if result["success"]:
                await query.answer(result["message"])
                await self._show_remove_products_list(query)
            else:
                await query.message.reply_text(
                    i18n.get_text("ADMIN_REMOVE_PRODUCT_ERROR", user_id=user_id).format(error=result["error"])
                )
                
        except Exception as e:
            self.logger.error("Error removing product: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _delete_product(self, query: CallbackQuery, product_id: int) -> None:
        """Delete (deactivate) a product"""
        try:
            user_id = query.from_user.id
            result = await self.admin_service.delete_existing_product(product_id)
            
            if result["success"]:
                await query.answer(result["message"])
                await self._show_all_products(query)
            else:
                await query.message.reply_text(
                    i18n.get_text("ADMIN_DELETE_PRODUCT_ERROR", user_id=user_id).format(error=result["error"])
                )
                
        except Exception as e:
            self.logger.error("Error deleting product: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _show_remove_products_list(self, query: CallbackQuery) -> None:
        """Show list of products for removal"""
        try:
            user_id = query.from_user.id
            products = await self.admin_service.get_all_products_for_admin()
            
            if not products:
                text = i18n.get_text("ADMIN_NO_PRODUCTS", user_id=user_id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_PRODUCT_BACK_TO_MANAGEMENT", user_id=user_id),
                            callback_data="admin_menu_management"
                        )
                    ]
                ]
            else:
                text = i18n.get_text("ADMIN_REMOVE_PRODUCTS_TITLE", user_id=user_id) + f"\n\n{i18n.get_text('ADMIN_PRODUCT_TOTAL_COUNT', user_id=user_id).format(count=len(products))}"
                
                keyboard = []
                for product in products:
                    status_text = i18n.get_text("ADMIN_PRODUCT_ACTIVE", user_id=user_id) if product["is_active"] else i18n.get_text("ADMIN_PRODUCT_INACTIVE", user_id=user_id)
                    product_text = i18n.get_text("ADMIN_PRODUCT_BUTTON_FORMAT", user_id=user_id).format(
                        name=product["name"],
                        category=product["category"],
                        price=product["price"],
                        status=status_text
                    )
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            product_text,
                            callback_data=f"admin_remove_product_{product['id']}"
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_BACK_TO_MANAGEMENT", user_id=user_id),
                        callback_data="admin_menu_management"
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            except Exception as edit_error:
                if "Message is not modified" in str(edit_error):
                    # Message content is identical, just answer the callback
                    await query.answer()
                else:
                    # Re-raise other errors
                    raise edit_error
            
        except Exception as e:
            self.logger.error("Error showing remove products list: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))



    async def _handle_quick_action(self, query: CallbackQuery, data: str) -> None:
        """Handle quick actions for products"""
        try:
            user_id = query.from_user.id
            
            if data.startswith("admin_quick_toggle_"):
                product_id = int(data.replace("admin_quick_toggle_", ""))
                result = await self.admin_service.toggle_product_status(product_id)
                
                if result["success"]:
                    status = "✅ Active" if result["new_status"] else "❌ Inactive"
                    await query.answer(
                        i18n.get_text("ADMIN_QUICK_TOGGLE_SUCCESS", user_id=user_id).format(status=status),
                        show_alert=False
                    )
                else:
                    await query.answer(
                        i18n.get_text("ADMIN_QUICK_TOGGLE_ERROR", user_id=user_id).format(error=result["error"]),
                        show_alert=True
                    )
                    
            elif data.startswith("admin_quick_delete_"):
                product_id = int(data.replace("admin_quick_delete_", ""))
                result = await self.admin_service.delete_existing_product(product_id)
                
                if result["success"]:
                    await query.answer(
                        i18n.get_text("ADMIN_QUICK_DELETE_SUCCESS", user_id=user_id),
                        show_alert=False
                    )
                    # Refresh the product list
                    await self._show_all_products(query)
                else:
                    await query.answer(
                        i18n.get_text("ADMIN_QUICK_DELETE_ERROR", user_id=user_id).format(error=result["error"]),
                        show_alert=True
                    )
                    
        except Exception as e:
            self.logger.error("Error handling quick action: %s", e)
            await query.answer(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id), show_alert=True)

    async def _start_add_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the step-by-step add product conversation"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            self.logger.info(f"🚀 Starting step-by-step product creation for user {user_id}")
            self.logger.info(f"🚀 Setting conversation state to AWAITING_PRODUCT_NAME ({AWAITING_PRODUCT_NAME})")
            text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_NAME", user_id=user_id)
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_menu_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_PRODUCT_NAME
            
        except Exception as e:
            self.logger.error("Error starting add product: %s", e)
            await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=update.callback_query.from_user.id))
            return ConversationHandler.END

    def _parse_product_input(self, text: str) -> Optional[Dict]:
        """Parse product details from text input"""
        try:
            lines = text.strip().split('\n')
            product_data = {}
            
            for line in lines:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == 'name':
                        product_data['name'] = value
                    elif key == 'description':
                        product_data['description'] = value
                    elif key == 'category':
                        product_data['category'] = value
                    elif key == 'price':
                        try:
                            product_data['price'] = float(value)
                        except ValueError:
                            return None
            
            # Validate required fields
            if not all(key in product_data for key in ['name', 'description', 'category', 'price']):
                return None
            
            return product_data
            
        except Exception:
            return None


def register_admin_handlers(application: Application):
    """Register admin handlers"""
    handler = AdminHandler()

    # Admin command handler
    application.add_handler(CommandHandler("admin", handler.handle_admin_command))

    # Admin callback handlers (excluding conversation patterns)
    application.add_handler(
        CallbackQueryHandler(handler.handle_admin_callback, pattern="^admin_(?!add_product_category_|add_product_confirm_|add_product$|add_category$|edit_category_name_)")
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
        per_message=False,
    )

    application.add_handler(conv_handler)

    # Admin conversation handler for adding products (step-by-step)
    add_product_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handler._start_add_product, pattern="^admin_add_product$")
        ],
        states={
            AWAITING_PRODUCT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_product_name_input)
            ],
            AWAITING_PRODUCT_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_product_description_input)
            ],
            AWAITING_PRODUCT_CATEGORY: [
                CallbackQueryHandler(handler._handle_product_category_selection, pattern="^admin_add_product_category_")
            ],
            AWAITING_PRODUCT_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_product_price_input)
            ],
            AWAITING_PRODUCT_CONFIRMATION: [
                CallbackQueryHandler(handler._handle_product_confirmation, pattern="^admin_add_product_confirm_")
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda u, c: ConversationHandler.END),
            CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^admin_menu_management$")
        ],
        name="add_product_conversation",
        persistent=False,
        per_message=False,
    )
    
    # Add debug logging to the conversation handler
    handler.logger.info("🔧 Registering add_product_conversation handler")
    application.add_handler(add_product_handler)
    handler.logger.info("✅ add_product_conversation handler registered successfully")



    # Admin conversation handler for adding categories
    add_category_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handler._start_add_category, pattern="^admin_add_category$")
        ],
        states={
            AWAITING_CATEGORY_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_category_name_input)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda u, c: ConversationHandler.END),
            CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^admin_category_management$")
        ],
        name="add_category_conversation",
        persistent=False,
        per_message=False,
    )

    # Add debug logging to the conversation handler
    handler.logger.info("🔧 Registering add_category_conversation handler")
    application.add_handler(add_category_handler)
    handler.logger.info("✅ add_category_conversation handler registered successfully")

    # Admin conversation handler for editing category names
    edit_category_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handler._start_edit_category_name, pattern="^admin_edit_category_name_")
        ],
        states={
            AWAITING_CATEGORY_NAME_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_category_name_edit_input)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda u, c: ConversationHandler.END),
            CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^admin_category_management$")
        ],
        name="edit_category_conversation",
        persistent=False,
        per_message=False,
    )

    application.add_handler(edit_category_handler)

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
