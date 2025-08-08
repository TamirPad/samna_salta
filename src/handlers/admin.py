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
from src.utils.multilingual_content import MultilingualContentManager
from src.utils.language_manager import language_manager

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
AWAITING_CATEGORY_NAME = 30
AWAITING_CATEGORY_NAME_EDIT = 31

# Product edit wizard states
AWAITING_PRODUCT_EDIT_FIELD = 40
AWAITING_PRODUCT_EDIT_VALUE = 41
AWAITING_PRODUCT_EDIT_CONFIRM = 42
AWAITING_BUSINESS_FIELD_INPUT = 43

# Add new conversation states for multilingual product creation
AWAITING_PRODUCT_NAME_EN = 50
AWAITING_PRODUCT_NAME_HE = 51
AWAITING_PRODUCT_DESCRIPTION_EN = 52
AWAITING_PRODUCT_DESCRIPTION_HE = 53
AWAITING_PRODUCT_IMAGE_URL = 54

# Add new states for category wizard
AWAITING_CATEGORY_NAME_EN = 32
AWAITING_CATEGORY_NAME_HE = 33

# Delivery area wizard states
AWAITING_DELIVERY_AREA_NAME_EN = 60
AWAITING_DELIVERY_AREA_NAME_HE = 61
AWAITING_DELIVERY_AREA_CHARGE = 62

logger = logging.getLogger(__name__)


class AdminHandler:
    """Handler for admin operations"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.container = get_container()
        self.admin_service = self.container.get_admin_service()
        self.notification_service = self.container.get_notification_service()
        self.admin_conversations = {}  # Initialize admin conversations storage

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

    async def handle_myid_command(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /myid command - show user ID for admin setup"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "Unknown"
        
        message = f"🔍 <b>Your User Information:</b>\n\n"
        message += f"👤 <b>Name:</b> {user_name}\n"
        message += f"🆔 <b>User ID:</b> <code>{user_id}</code>\n\n"
        message += f"💡 <b>To set up admin access:</b>\n"
        message += f"1. Add your user ID to the admin list\n"
        message += f"2. Or set ADMIN_CHAT_ID in your .env file\n"
        message += f"3. Current admin IDs: 598829473"
        
        await update.message.reply_text(message, parse_mode="HTML")

    @error_handler("admin_dashboard")
    async def handle_admin_callback(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle admin dashboard callbacks"""
        query = update.callback_query

        user_id = update.effective_user.id
        if not await self._is_admin_user(user_id):
            await query.answer()
            await query.message.reply_text(i18n.get_text("ADMIN_ACCESS_DENIED", user_id=user_id))
            return

        data = query.data
        self.logger.info("👑 ADMIN CALLBACK: %s by User %s", data, user_id)
        
        # Check if user is admin first
        is_admin = await self._is_admin_user(user_id)
        self.logger.info(f"🔍 User {user_id} is admin: {is_admin}")
        
        if not is_admin:
            await query.answer()
            await query.message.reply_text(i18n.get_text("ADMIN_ACCESS_DENIED", user_id=user_id))
            return

        if data == "admin_orders":
            await self._show_orders_submenu(query)
        elif data == "admin_pending_orders":
            await self._show_pending_orders(query)
        elif data == "admin_active_orders":
            await self._show_active_orders(query)
        elif data == "admin_all_orders":
            await self._show_all_orders(query)
        elif data == "admin_completed_orders":
            await self._show_completed_orders(query)
        elif data == "admin_customers":
            await self._show_customers(query)
        elif data.startswith("admin_customers_"):
            if "_size_" in data and "_page_" in data:
                # New format: admin_customers_size_20_page_0
                parts = data.split("_")
                size_idx = parts.index("size") + 1
                page_idx = parts.index("page") + 1
                page_size = int(parts[size_idx])
                page = int(parts[page_idx])
            elif "_page_" in data:
                # Old format: admin_customers_page_0
                page = int(data.split("_")[-1])
                page_size = 5  # default
            else:
                return
            await self._show_customers(query, page, page_size)
        elif data.startswith("admin_all_orders_"):
            if "_size_" in data and "_page_" in data:
                parts = data.split("_")
                size_idx = parts.index("size") + 1
                page_idx = parts.index("page") + 1
                page_size = int(parts[size_idx])
                page = int(parts[page_idx])
            elif "_page_" in data:
                page = int(data.split("_")[-1])
                page_size = 5  # default
            else:
                return
            await self._show_all_orders(query, page, page_size)
        elif data.startswith("admin_active_orders_"):
            if "_size_" in data and "_page_" in data:
                parts = data.split("_")
                size_idx = parts.index("size") + 1
                page_idx = parts.index("page") + 1
                page_size = int(parts[size_idx])
                page = int(parts[page_idx])
            elif "_page_" in data:
                page = int(data.split("_")[-1])
                page_size = 5  # default
            else:
                return
            await self._show_active_orders(query, page, page_size)
        elif data.startswith("admin_completed_orders_"):
            if "_size_" in data and "_page_" in data:
                parts = data.split("_")
                size_idx = parts.index("size") + 1
                page_idx = parts.index("page") + 1
                page_size = int(parts[size_idx])
                page = int(parts[page_idx])
            elif "_page_" in data:
                page = int(data.split("_")[-1])
                page_size = 5  # default
            else:
                return
            await self._show_completed_orders(query, page, page_size)
        elif data.startswith("admin_pending_orders_"):
            if "_size_" in data and "_page_" in data:
                parts = data.split("_")
                size_idx = parts.index("size") + 1
                page_idx = parts.index("page") + 1
                page_size = int(parts[size_idx])
                page = int(parts[page_idx])
            elif "_page_" in data:
                page = int(data.split("_")[-1])
                page_size = 5  # default
            else:
                return
            await self._show_pending_orders(query, page, page_size)
        elif data == "admin_products_management":
            self.logger.info(f"🔍 Products management callback received for user {query.from_user.id}")
            await self._show_products_management(query)
        elif data.startswith("admin_products_"):
            if "_size_" in data and "_page_" in data:
                parts = data.split("_")
                size_idx = parts.index("size") + 1
                page_idx = parts.index("page") + 1
                page_size = int(parts[size_idx])
                page = int(parts[page_idx])
            elif "_page_" in data:
                page = int(data.split("_")[-1])
                page_size = 5  # default
            else:
                return
            await self._show_all_products(query, page, page_size)
        elif data.startswith("analytics_customers_"):
            if "_size_" in data and "_page_" in data:
                parts = data.split("_")
                size_idx = parts.index("size") + 1
                page_idx = parts.index("page") + 1
                page_size = int(parts[size_idx])
                page = int(parts[page_idx])
            elif "_page_" in data:
                page = int(data.split("_")[-1])
                page_size = 5  # default
            else:
                return
            analytics_data = await self.admin_service.get_business_analytics()
            await self._show_customer_report(query, analytics_data, page, page_size)
        elif data == "pagination_info":
            # Just a display button, answer the callback without doing anything
            await query.answer()
        elif data == "admin_update_status":
            await self._start_status_update(query)
        elif data == "admin_analytics":
            await self._show_analytics(query)
        elif data.startswith("analytics_"):
            await self._handle_analytics_callback(update, None)
        elif data.startswith("admin_order_"):
            order_id = int(data.split("_")[-1])
            await self._show_order_details(query, order_id)
        elif data.startswith("admin_invoice_pdf_"):
            order_id = int(data.split("_")[-1])
            await self._send_order_invoice_pdf(query, order_id, receipt=False)
        elif data.startswith("admin_receipt_pdf_"):
            order_id = int(data.split("_")[-1])
            await self._send_order_invoice_pdf(query, order_id, receipt=True)
        elif data.startswith("admin_customer_orders_"):
            customer_id = int(data.split("_")[-1])
            await self._show_customer_orders(query, customer_id)
        elif data.startswith("admin_customer_"):
            customer_id = int(data.split("_")[-1])
            await self._show_customer_details(query, customer_id)
        elif data.startswith("admin_status_"):
            # Format: admin_status_{order_id}_{new_status}
            parts = data.split("_")
            order_id = int(parts[2])
            new_status = parts[3]
            await self._update_order_status(query, order_id, new_status, user_id)
        elif data.startswith("admin_delete_order_"):
            # Format: admin_delete_order_{order_id}
            order_id = int(data.split("_")[-1])
            await self._show_delete_order_confirmation(query, order_id)
        elif data.startswith("admin_confirm_delete_order_"):
            # Format: admin_confirm_delete_order_{order_id}
            order_id = int(data.split("_")[-1])
            await self._confirm_delete_order(query, order_id)
        elif data == "admin_menu_management":
            self.logger.info(f"🔍 Menu management callback received for user {query.from_user.id}")
            await self._show_menu_management_dashboard(query)
        elif data == "admin_deliveries":
            await self._show_deliveries_dashboard(query)
        elif data == "admin_view_products":
            await self._show_all_products(query)
        # Note: admin_add_product is handled by the conversation handler
        # elif data == "admin_add_product":
        #     return await self._start_add_product(update, _)
        elif data == "admin_remove_products":
            await self._show_remove_products_list(query)
        
        elif data.startswith("admin_quick_"):
            await self._handle_quick_action(query, data)
        elif data.startswith("admin_product_deactivate_"):
            product_id = int(data.split("_")[-1])
            await self._show_deactivate_product_confirmation(query, product_id)
        elif data.startswith("admin_product_hard_delete_"):
            product_id = int(data.split("_")[-1])
            await self._show_hard_delete_product_confirmation(query, product_id)
        elif data.startswith("admin_product_yes_deactivate_"):
            product_id = int(data.split("_")[-1])
            await self._deactivate_product(query, product_id)
        elif data.startswith("admin_product_yes_hard_delete_"):
            product_id = int(data.split("_")[-1])
            await self._hard_delete_product(query, product_id)
        elif data in ["admin_product_no_deactivate", "admin_product_no_hard_delete"]:
            # Go back to product details
            product_id = int(query.data.split("_")[-2]) if query.data.split("_")[-2].isdigit() else None
            if product_id:
                await self._show_product_details(query, product_id)
            else:
                await self._show_all_products(query)
        elif data.startswith("admin_product_"):
            await self._handle_product_callback(query, data)
        
        elif data == "admin_category_management":
            await self._show_category_management(query)
        elif data == "admin_business_settings":
            await self._show_business_settings(query)
        elif data == "admin_deliveries":
            await self._show_deliveries_dashboard(query)
        elif data == "admin_delivery_areas":
            await self._show_delivery_areas(query)
        elif data == "admin_add_delivery_area":
            await self._start_add_delivery_area(update, _)
        elif data == "admin_edit_business_settings":
            await self._start_edit_business_settings(query)
        elif (data.startswith("admin_edit_business_") or 
              data == "admin_edit_currency" or 
              data == "admin_edit_delivery_charge"):
            await self._handle_business_settings_edit(update, None)
        elif data == "admin_cancel_business_edit":
            await self._cancel_business_edit(query)

        elif data == "admin_view_categories":
            await self._show_all_categories(query)
        elif data == "admin_add_category":
            await self._start_add_category(update, None)
        elif data.startswith("admin_edit_category_"):
            category = data.replace("admin_edit_category_", "")
            await self._show_edit_category(query, category)
        elif data.startswith("admin_edit_category_name_"):
            category = data.replace("admin_edit_category_name_", "")
            await self._start_edit_category_name(update, _)
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
        elif data == "admin_business_info":
            await self._show_business_settings(query)
        elif data == "admin_language_selection":
            await self._handle_admin_language_selection(query)
        elif data.startswith("admin_language_"):
            await self._handle_admin_language_change(query)
        elif data == "admin_back":
            await self._show_admin_dashboard_from_callback(query)
            await query.answer()
        elif data == "admin_back_to_orders":
            await self._show_orders_submenu(query)
            await query.answer()
        elif data == "admin_dashboard":
            await self._show_admin_dashboard_from_callback(query)
            await query.answer()

    def _create_professional_admin_keyboard(self, user_id: int) -> list:
        """Create a professional admin dashboard keyboard with beautiful styling"""
        return [
            # 📋 Orders Section
            [
                InlineKeyboardButton(
                    i18n.get_text('ADMIN_ORDERS', user_id=user_id), 
                    callback_data="admin_orders"
                ),
            ],
            # 👥 Customers Section
            [
                InlineKeyboardButton(
                    i18n.get_text('ADMIN_CUSTOMERS', user_id=user_id), 
                    callback_data="admin_customers"
                )
            ],
            # 🍽️ Menu Management Section
            [
                InlineKeyboardButton(
                    i18n.get_text('ADMIN_MENU_MANAGEMENT', user_id=user_id), 
                    callback_data="admin_menu_management"
                )
            ],
            # 🚚 Deliveries Section
            [
                InlineKeyboardButton(
                    i18n.get_text('ADMIN_DELIVERIES', user_id=user_id), 
                    callback_data="admin_deliveries"
                )
            ],
            # ⚙️ Business Settings Section
            [
                InlineKeyboardButton(
                    i18n.get_text('ADMIN_BUSINESS_SETTINGS', user_id=user_id), 
                    callback_data="admin_business_settings"
                )
            ],
            # 📊 Analytics Section
            [
                InlineKeyboardButton(
                    i18n.get_text('ADMIN_ANALYTICS', user_id=user_id), 
                    callback_data="admin_analytics"
                ),
            ],
        ]

    async def _show_admin_dashboard_from_callback(self, query: CallbackQuery) -> None:
        """Show admin dashboard from callback query"""
        try:
            # Ensure latest translations are loaded (avoids placeholders if locales changed)
            try:
                from src.utils.i18n import i18n
                i18n.reload()
            except Exception:
                pass
            self.logger.info("📊 LOADING ADMIN DASHBOARD FROM CALLBACK")
            
            # Get user_id from query
            user_id = query.from_user.id

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

            # Create professional dashboard with clean formatting
            dashboard_text = f"""
🏢 <b>{i18n.get_text("ADMIN_DASHBOARD_TITLE", user_id=user_id)}</b>

📊 <b>{i18n.get_text("ADMIN_ORDER_STATS", user_id=user_id)}</b>
🟡 {i18n.get_text("ADMIN_PENDING_COUNT", user_id=user_id).format(count=len(pending_orders))}
🔵 {i18n.get_text("ADMIN_ACTIVE_COUNT", user_id=user_id).format(count=len(active_orders))}
🟢 {i18n.get_text("ADMIN_COMPLETED_COUNT", user_id=user_id).format(count=len(completed_orders))}
📅 {i18n.get_text("ADMIN_TOTAL_TODAY", user_id=user_id).format(count=len(today_orders))}

🚀 <b>{i18n.get_text("ADMIN_QUICK_ACTIONS", user_id=user_id)}</b>
            """.strip()

            keyboard = self._create_professional_admin_keyboard(user_id)

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=dashboard_text, parse_mode="HTML", reply_markup=reply_markup
            )

        except (BusinessLogicError, RuntimeError) as e:
            self.logger.error("💥 DASHBOARD ERROR: %s", e, exc_info=True)
            await query.answer(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
        except Exception as e:
            self.logger.critical("💥 UNHANDLED DASHBOARD ERROR: %s", e, exc_info=True)
            await query.answer(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _show_deliveries_dashboard(self, query: CallbackQuery) -> None:
        """Show deliveries dashboard"""
        try:
            user_id = query.from_user.id
            text = i18n.get_text("ADMIN_DELIVERIES_TITLE", user_id=user_id)
            keyboard = [
                [InlineKeyboardButton(i18n.get_text("ADMIN_DELIVERY_AREAS", user_id=user_id), callback_data="admin_delivery_areas")],
                [InlineKeyboardButton(i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=user_id), callback_data="admin_dashboard")],
            ]
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            self.logger.error("Error showing deliveries dashboard: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _show_delivery_areas(self, query: CallbackQuery) -> None:
        """List all active delivery areas"""
        try:
            user_id = query.from_user.id
            from src.db.operations import get_active_delivery_areas
            areas = get_active_delivery_areas()
            if not areas:
                text = i18n.get_text("ADMIN_NO_DELIVERY_AREAS", user_id=user_id)
            else:
                lines = [i18n.get_text("ADMIN_DELIVERY_AREAS_TITLE", user_id=user_id), ""]
                for i, area in enumerate(areas, start=1):
                    charge = area.charge if area.charge is not None else "-"
                    lines.append(f"{i}. {area.name_he} / {area.name_en} — {i18n.get_text('ADMIN_DELIVERY_CHARGE', user_id=user_id)}: {charge}")
                text = "\n".join(lines)
            keyboard = [
                [InlineKeyboardButton(i18n.get_text("ADMIN_ADD_DELIVERY_AREA", user_id=user_id), callback_data="admin_add_delivery_area")],
                [InlineKeyboardButton(i18n.get_text("ADMIN_BACK", user_id=user_id), callback_data="admin_deliveries")],
            ]
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            self.logger.error("Error showing delivery areas: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _handle_delivery_area_name_en(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            user_id = update.effective_user.id
            name_en = update.message.text.strip()
            if len(name_en) < 2:
                await update.message.reply_text(i18n.get_text("ADMIN_DELIVERY_AREA_NAME_EN_TOO_SHORT", user_id=user_id))
                return AWAITING_DELIVERY_AREA_NAME_EN
            context.user_data["delivery_area_name_en"] = name_en
            text = i18n.get_text("ADMIN_DELIVERY_AREA_STEP_NAME_HE", user_id=user_id).format(name_en=name_en)
            await update.message.reply_text(text)
            return AWAITING_DELIVERY_AREA_NAME_HE
        except Exception as e:
            self.logger.error("Error handling delivery area name EN: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_delivery_area_name_he(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            user_id = update.effective_user.id
            name_he = update.message.text.strip()
            if len(name_he) < 2:
                await update.message.reply_text(i18n.get_text("ADMIN_DELIVERY_AREA_NAME_HE_TOO_SHORT", user_id=user_id))
                return AWAITING_DELIVERY_AREA_NAME_HE
            context.user_data["delivery_area_name_he"] = name_he
            text = i18n.get_text("ADMIN_DELIVERY_AREA_STEP_CHARGE", user_id=user_id)
            await update.message.reply_text(text)
            return AWAITING_DELIVERY_AREA_CHARGE
        except Exception as e:
            self.logger.error("Error handling delivery area name HE: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_delivery_area_charge(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            user_id = update.effective_user.id
            raw = update.message.text.strip()
            charge = None
            if raw:
                try:
                    charge = float(raw)
                    if charge < 0:
                        await update.message.reply_text(i18n.get_text("ADMIN_DELIVERY_AREA_CHARGE_NEGATIVE", user_id=user_id))
                        return AWAITING_DELIVERY_AREA_CHARGE
                except ValueError:
                    await update.message.reply_text(i18n.get_text("ADMIN_DELIVERY_AREA_CHARGE_INVALID", user_id=user_id))
                    return AWAITING_DELIVERY_AREA_CHARGE
            name_en = context.user_data.get("delivery_area_name_en")
            name_he = context.user_data.get("delivery_area_name_he")
            # Persist
            from src.db.operations import create_delivery_area
            ok = create_delivery_area(name_en=name_en, name_he=name_he, charge=charge)
            if ok:
                await update.message.reply_text(i18n.get_text("ADMIN_DELIVERY_AREA_CREATED", user_id=user_id))
            else:
                await update.message.reply_text(i18n.get_text("ADMIN_DELIVERY_AREA_CREATE_ERROR", user_id=user_id))
            context.user_data.clear()
            return ConversationHandler.END
        except Exception as e:
            self.logger.error("Error handling delivery area charge: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END
    async def _start_add_delivery_area(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start delivery area wizard: ask for English name"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            if context and hasattr(context, 'user_data'):
                context.user_data.clear()
            text = i18n.get_text("ADMIN_DELIVERY_AREA_STEP_NAME_EN", user_id=user_id)
            keyboard = [[InlineKeyboardButton(i18n.get_text("ADMIN_BACK", user_id=user_id), callback_data="admin_delivery_areas")]]
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            return AWAITING_DELIVERY_AREA_NAME_EN
        except Exception as e:
            self.logger.error("Error starting add delivery area: %s", e)
            await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=update.callback_query.from_user.id))
            return ConversationHandler.END

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

            # Create professional dashboard with clean formatting
            dashboard_text = f"""
🏢 <b>{i18n.get_text("ADMIN_DASHBOARD_TITLE", user_id=user_id)}</b>

📊 <b>{i18n.get_text("ADMIN_ORDER_STATS", user_id=user_id)}</b>
🟡 {i18n.get_text("ADMIN_PENDING_COUNT", user_id=user_id).format(count=len(pending_orders))}
🔵 {i18n.get_text("ADMIN_ACTIVE_COUNT", user_id=user_id).format(count=len(active_orders))}
🟢 {i18n.get_text("ADMIN_COMPLETED_COUNT", user_id=user_id).format(count=len(completed_orders))}
📅 {i18n.get_text("ADMIN_TOTAL_TODAY", user_id=user_id).format(count=len(today_orders))}

🚀 <b>{i18n.get_text("ADMIN_QUICK_ACTIONS", user_id=user_id)}</b>
            """.strip()

            keyboard = self._create_professional_admin_keyboard(user_id)

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

    async def _show_orders_submenu(self, query: CallbackQuery) -> None:
        """Show orders submenu with all order-related options"""
        try:
            self.logger.info("📋 LOADING ORDERS SUBMENU")
            user_id = query.from_user.id
            
            # Get order statistics for the submenu
            pending_orders = await self.admin_service.get_pending_orders()
            active_orders = await self.admin_service.get_active_orders()
            completed_orders = await self.admin_service.get_completed_orders()
            today_orders = await self.admin_service.get_today_orders()
            
            text = f"""
📋 <b>{i18n.get_text("ADMIN_ORDERS", user_id=user_id)}</b>

📊 <b>{i18n.get_text("ADMIN_ORDER_STATS", user_id=user_id)}</b>
🟡 {i18n.get_text("ADMIN_PENDING_COUNT", user_id=user_id).format(count=len(pending_orders))}
🔵 {i18n.get_text("ADMIN_ACTIVE_COUNT", user_id=user_id).format(count=len(active_orders))}
🟢 {i18n.get_text("ADMIN_COMPLETED_COUNT", user_id=user_id).format(count=len(completed_orders))}
📅 {i18n.get_text("ADMIN_TOTAL_TODAY", user_id=user_id).format(count=len(today_orders))}

{i18n.get_text("ADMIN_QUICK_ACTIONS", user_id=user_id)}
            """.strip()
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text('ADMIN_PENDING_ORDERS', user_id=user_id), 
                        callback_data="admin_pending_orders"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text('ADMIN_ACTIVE_ORDERS', user_id=user_id), 
                        callback_data="admin_active_orders"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text('ADMIN_ALL_ORDERS', user_id=user_id), 
                        callback_data="admin_all_orders"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text('ADMIN_COMPLETED_ORDERS', user_id=user_id), 
                        callback_data="admin_completed_orders"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=user_id), 
                        callback_data="admin_back"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=text, parse_mode="HTML", reply_markup=reply_markup
            )
            
        except Exception as e:
            self.logger.error("💥 ORDERS SUBMENU ERROR: %s", e, exc_info=True)
            await query.answer(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

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

    async def _show_customer_report(self, query: CallbackQuery, analytics_data: Dict, page: int = 0, page_size: int = 5) -> None:
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
            keyboard = [
                [InlineKeyboardButton(i18n.get_text("ANALYTICS_BACK_TO_ANALYTICS", user_id=user_id), callback_data="analytics_back")]
            ]
        else:
            # Use pagination for large customer lists
            customers_per_page = page_size
            total_customers = len(customers)
            total_pages = (total_customers + customers_per_page - 1) // customers_per_page if total_customers > 0 else 1
            
            # Ensure page is within bounds
            page = max(0, min(page, total_pages - 1))
            
            # Get customers for current page
            start_idx = page * customers_per_page
            end_idx = start_idx + customers_per_page
            page_customers = customers[start_idx:end_idx]
            
            customer_lines = []
            for i, customer in enumerate(page_customers, start_idx + 1):
                customer_lines.append(
                    f"{i}. {customer['customer_name']}\n"
                    f"   • {i18n.get_text('ANALYTICS_LABEL_ORDERS', user_id=user_id)}: {customer.get('total_orders', 0)}\n"
                    f"   • {i18n.get_text('ANALYTICS_LABEL_TOTAL_SPENT', user_id=user_id)}: ₪{fmt(customer.get('total_spent'))}\n"
                    f"   • {i18n.get_text('ANALYTICS_LABEL_AVG_ORDER', user_id=user_id)}: ₪{fmt(customer.get('avg_order_value'))}"
                )
            
            total_customer_revenue = sum(c.get('total_spent', 0) or 0 for c in customers)
            avg_customer_value = total_customer_revenue / total_customers if total_customers > 0 else None
            
            report_text = f"""
{i18n.get_text('ANALYTICS_CUSTOMER_TITLE', user_id=user_id)}

{i18n.get_text('ANALYTICS_TOP_CUSTOMERS', user_id=user_id)}
📄 {i18n.get_text('ADMIN_SHOWING_ITEMS', user_id=user_id).format(start=start_idx + 1, end=min(end_idx, total_customers), total=total_customers)}

{chr(10).join(customer_lines)}

{i18n.get_text('ANALYTICS_CUSTOMER_METRICS', user_id=user_id)}
• {i18n.get_text('ANALYTICS_LABEL_TOTAL_CUSTOMERS', user_id=user_id)}: {total_customers}
• {i18n.get_text('ANALYTICS_LABEL_TOTAL_CUSTOMER_REVENUE', user_id=user_id)}: ₪{fmt(total_customer_revenue)}
• {i18n.get_text('ANALYTICS_LABEL_AVERAGE_CUSTOMER_VALUE', user_id=user_id)}: ₪{fmt(avg_customer_value)}
• {i18n.get_text('ANALYTICS_LABEL_BEST_CUSTOMER', user_id=user_id)}: {customers[0]['customer_name'] if customers else 'N/A'}

<i>{i18n.get_text('ANALYTICS_REPORT_PERIOD', user_id=user_id).format(days=analytics_data.get('period', {}).get('days', 30))}</i>
            """.strip()
            
            # Create pagination keyboard for analytics
            keyboard = []
            
            # Add page size options
            page_size_row = []
            page_sizes = [5, 10, 15]
            
            for size in page_sizes:
                if size != page_size and size <= total_customers:
                    page_size_row.append(
                        InlineKeyboardButton(
                            f"{size}/page",
                            callback_data=f"analytics_customers_size_{size}_page_0"
                        )
                    )
                elif size == page_size:
                    page_size_row.append(
                        InlineKeyboardButton(
                            f"✅{size}/page",
                            callback_data="pagination_info"
                        )
                    )
            
            if page_size_row:
                keyboard.append(page_size_row)
            
            # Add pagination controls if multiple pages
            if total_pages > 1:
                pagination_row = []
                
                # Previous page button
                if page > 0:
                    pagination_row.append(
                        InlineKeyboardButton("⬅️", callback_data=f"analytics_customers_size_{page_size}_page_{page - 1}")
                    )
                
                # Page indicator
                pagination_row.append(
                    InlineKeyboardButton(
                        f"📄 {page + 1}/{total_pages}", 
                        callback_data="pagination_info"
                    )
                )
                
                # Next page button
                if page < total_pages - 1:
                    pagination_row.append(
                        InlineKeyboardButton("➡️", callback_data=f"analytics_customers_size_{page_size}_page_{page + 1}")
                    )
                
                keyboard.append(pagination_row)
            
            keyboard.append([
                InlineKeyboardButton(i18n.get_text("ANALYTICS_BACK_TO_ANALYTICS", user_id=user_id), callback_data="analytics_back")
            ])
            
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

    async def _show_pending_orders(self, query: CallbackQuery, page: int = 0, page_size: int = 5) -> None:
        """Show pending orders with pagination"""
        try:
            orders = await self.admin_service.get_pending_orders()
            user_id = query.from_user.id

            if not orders:
                text = (
                    i18n.get_text("ADMIN_PENDING_ORDERS_TITLE", user_id=user_id) + "\n\n" + i18n.get_text("ADMIN_NO_PENDING_ORDERS", user_id=user_id)
                )
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_ORDERS", user_id=user_id), callback_data="admin_back_to_orders"
                        )
                    ]
                ]
            else:
                # Use pagination helper
                extra_buttons = []
                pagination_keyboard, page_info = self._create_pagination_keyboard(
                    orders, page, page_size, "admin_pending_orders", user_id, extra_buttons
                )
                
                text = (
                    f"{i18n.get_text('ADMIN_PENDING_ORDERS_TITLE', user_id=user_id)} ({page_info['total_items']})\n"
                    f"📄 {i18n.get_text('ADMIN_SHOWING_ITEMS', user_id=user_id).format(start=page_info['start_idx'] + 1, end=page_info['end_idx'], total=page_info['total_items'])}\n\n"
                    f"{i18n.get_text('ADMIN_PENDING_ORDERS_LIST', user_id=user_id)}"
                )

                # Add order buttons for current page
                for order in page_info['page_items']:
                    order_summary = (
                        f"#{order['order_id']} - {order['customer_name']} - "
                        f"₪{order['total']:.2f}"
                    )
                    pagination_keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order['order_id']}",
                            )
                        ]
                    )

                # Add back button
                pagination_keyboard.append(
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=user_id), callback_data="admin_back"
                        )
                    ]
                )
                
                keyboard = pagination_keyboard

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 PENDING ORDERS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("PENDING_ORDERS_ERROR"))

    async def _show_active_orders(self, query: CallbackQuery, page: int = 0, page_size: int = 5) -> None:
        """Show active orders with pagination"""
        try:
            orders = await self.admin_service.get_active_orders()
            user_id = query.from_user.id

            if not orders:
                text = i18n.get_text("ADMIN_ACTIVE_ORDERS_TITLE", user_id=user_id) + "\n\n" + i18n.get_text("ADMIN_NO_ACTIVE_ORDERS", user_id=user_id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_ORDERS", user_id=user_id), callback_data="admin_back_to_orders"
                        )
                    ]
                ]
            else:
                # Use pagination helper
                extra_buttons = []
                pagination_keyboard, page_info = self._create_pagination_keyboard(
                    orders, page, page_size, "admin_active_orders", user_id, extra_buttons
                )
                
                text = (
                    f"{i18n.get_text('ADMIN_ACTIVE_ORDERS_TITLE', user_id=user_id)} ({page_info['total_items']})\n"
                    f"📄 {i18n.get_text('ADMIN_SHOWING_ITEMS', user_id=user_id).format(start=page_info['start_idx'] + 1, end=page_info['end_idx'], total=page_info['total_items'])}\n\n"
                    f"{i18n.get_text('ADMIN_ACTIVE_ORDERS_LIST', user_id=user_id)}"
                )
                
                # Add order buttons for current page
                for order in page_info['page_items']:
                    order_summary = (
                        f"#{order['order_id']} - {order['customer_name']} - "
                        f"{order['status'].capitalize()}"
                    )
                    pagination_keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order['order_id']}",
                            )
                        ]
                    )
                
                # Add back button
                pagination_keyboard.append(
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_ORDERS", user_id=user_id), callback_data="admin_back_to_orders"
                        )
                    ]
                )
                
                keyboard = pagination_keyboard

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 ACTIVE ORDERS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("ACTIVE_ORDERS_ERROR"))

    async def _show_all_orders(self, query: CallbackQuery, page: int = 0, page_size: int = 5) -> None:
        """Show all orders with pagination"""
        try:
            orders = await self.admin_service.get_all_orders()
            user_id = query.from_user.id

            if not orders:
                text = i18n.get_text("ADMIN_ALL_ORDERS_TITLE", user_id=user_id) + "\n\n" + i18n.get_text("ADMIN_NO_ORDERS_FOUND", user_id=user_id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_ORDERS", user_id=user_id), callback_data="admin_back_to_orders"
                        )
                    ]
                ]
            else:
                # Use pagination helper
                extra_buttons = []
                pagination_keyboard, page_info = self._create_pagination_keyboard(
                    orders, page, page_size, "admin_all_orders", user_id, extra_buttons
                )
                
                text = (
                    f"{i18n.get_text('ADMIN_ALL_ORDERS_TITLE', user_id=user_id)} ({page_info['total_items']})\n"
                    f"📄 {i18n.get_text('ADMIN_SHOWING_ITEMS', user_id=user_id).format(start=page_info['start_idx'] + 1, end=page_info['end_idx'], total=page_info['total_items'])}"
                )
                
                # Add order buttons for current page
                for order in page_info['page_items']:
                    order_summary = (
                        f"#{order['order_id']} - {order['customer_name']} - "
                        f"{order['status'].capitalize()}"
                    )
                    pagination_keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order['order_id']}",
                            )
                        ]
                    )
                
                # Add back button
                pagination_keyboard.append(
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_ORDERS", user_id=user_id), callback_data="admin_back_to_orders"
                        )
                    ]
                )
                
                keyboard = pagination_keyboard

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 ALL ORDERS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("ALL_ORDERS_ERROR"))

    async def _show_completed_orders(self, query: CallbackQuery, page: int = 0, page_size: int = 5) -> None:
        """Show completed (delivered) orders with pagination"""
        try:
            orders = await self.admin_service.get_completed_orders()
            user_id = query.from_user.id

            if not orders:
                text = i18n.get_text("ADMIN_COMPLETED_ORDERS_TITLE", user_id=user_id) + "\n\n" + i18n.get_text("ADMIN_NO_COMPLETED_ORDERS", user_id=user_id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_ORDERS", user_id=user_id), callback_data="admin_back_to_orders"
                        )
                    ]
                ]
            else:
                # Use pagination helper
                extra_buttons = []
                pagination_keyboard, page_info = self._create_pagination_keyboard(
                    orders, page, page_size, "admin_completed_orders", user_id, extra_buttons
                )
                
                text = (
                    f"{i18n.get_text('ADMIN_COMPLETED_ORDERS_TITLE', user_id=user_id)} ({page_info['total_items']})\n"
                    f"📄 {i18n.get_text('ADMIN_SHOWING_ITEMS', user_id=user_id).format(start=page_info['start_idx'] + 1, end=page_info['end_idx'], total=page_info['total_items'])}"
                )
                
                # Add order buttons for current page
                for order in page_info['page_items']:
                    order_summary = (
                        f"#{order['order_id']} - {order['customer_name']} - "
                        f"₪{order['total']:.2f}"
                    )
                    pagination_keyboard.append(
                        [
                            InlineKeyboardButton(
                                order_summary,
                                callback_data=f"admin_order_{order['order_id']}",
                            )
                        ]
                    )
                
                # Add back button
                pagination_keyboard.append(
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_ORDERS", user_id=user_id), callback_data="admin_back_to_orders"
                        )
                    ]
                )
                
                keyboard = pagination_keyboard

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 COMPLETED ORDERS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("ALL_ORDERS_ERROR"))

    def _create_pagination_keyboard(
        self, 
        items: list, 
        page: int, 
        items_per_page: int, 
        callback_prefix: str, 
        user_id: int, 
        extra_buttons: list = None, 
        show_page_size_options: bool = True
    ) -> tuple[list, dict]:
        """
        Create pagination keyboard and get page info
        
        Returns:
            tuple: (keyboard, page_info)
                - keyboard: List of keyboard rows
                - page_info: Dict with pagination details
        """
        total_items = len(items)
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
        
        # Ensure page is within bounds
        page = max(0, min(page, total_pages - 1))
        
        # Get items for current page
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_items = items[start_idx:end_idx]
        
        keyboard = []
        
        # Add extra buttons at the top if provided
        if extra_buttons:
            keyboard.extend(extra_buttons)
        
        # Add page size options if enabled and there are items
        if show_page_size_options and total_items > 0:
            page_size_row = []
            page_sizes = [5, 10, 15]
            
            for size in page_sizes:
                if size != items_per_page and size <= total_items:
                    page_size_row.append(
                        InlineKeyboardButton(
                            f"{size}/page",
                            callback_data=f"{callback_prefix}_size_{size}_page_0"
                        )
                    )
                elif size == items_per_page:
                    page_size_row.append(
                        InlineKeyboardButton(
                            f"✅{size}/page",
                            callback_data="pagination_info"
                        )
                    )
            
            if page_size_row:
                keyboard.append(page_size_row)
        
        # Add pagination controls if multiple pages
        if total_pages > 1:
            pagination_row = []
            
            # First page button
            if page > 1:
                pagination_row.append(
                    InlineKeyboardButton("⏪", callback_data=f"{callback_prefix}_size_{items_per_page}_page_0")
                )
            
            # Previous page button
            if page > 0:
                pagination_row.append(
                    InlineKeyboardButton("⬅️", callback_data=f"{callback_prefix}_size_{items_per_page}_page_{page - 1}")
                )
            
            # Page indicator
            pagination_row.append(
                InlineKeyboardButton(
                    f"📄 {page + 1}/{total_pages}", 
                    callback_data="pagination_info"  # Non-functional, just for display
                )
            )
            
            # Next page button
            if page < total_pages - 1:
                pagination_row.append(
                    InlineKeyboardButton("➡️", callback_data=f"{callback_prefix}_size_{items_per_page}_page_{page + 1}")
                )
            
            # Last page button
            if page < total_pages - 2:
                pagination_row.append(
                    InlineKeyboardButton("⏩", callback_data=f"{callback_prefix}_size_{items_per_page}_page_{total_pages - 1}")
                )
            
            keyboard.append(pagination_row)
        
        page_info = {
            'page_items': page_items,
            'current_page': page + 1,
            'total_pages': total_pages,
            'total_items': total_items,
            'start_idx': start_idx,
            'end_idx': min(end_idx, total_items)
        }
        
        return keyboard, page_info

    async def _show_customers(self, query: CallbackQuery, page: int = 0, page_size: int = 5) -> None:
        """Show customers with pagination"""
        try:
            customers = await self.admin_service.get_all_customers()
            user_id = query.from_user.id

            if not customers:
                text = i18n.get_text("ADMIN_CUSTOMERS_TITLE", user_id=user_id) + "\n\n" + i18n.get_text("ADMIN_NO_CUSTOMERS", user_id=user_id)
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=user_id), callback_data="admin_back"
                        )
                    ]
                ]
            else:
                # Use pagination helper
                extra_buttons = []
                pagination_keyboard, page_info = self._create_pagination_keyboard(
                    customers, page, page_size, "admin_customers", user_id, extra_buttons
                )
                
                text = (
                    f"{i18n.get_text('ADMIN_CUSTOMERS_TITLE', user_id=user_id)} ({page_info['total_items']})\n"
                    f"📄 {i18n.get_text('ADMIN_SHOWING_ITEMS', user_id=user_id).format(start=page_info['start_idx'] + 1, end=page_info['end_idx'], total=page_info['total_items'])}"
                )
                
                # Add customer buttons for current page
                for customer in page_info['page_items']:
                    customer_summary = f"👤 {customer['full_name']} (ID: {customer['customer_id']})"
                    pagination_keyboard.append(
                        [
                            InlineKeyboardButton(
                                customer_summary,
                                callback_data=f"admin_customer_{customer['customer_id']}",
                            )
                        ]
                    )
                
                # Add back button
                pagination_keyboard.append(
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=user_id), callback_data="admin_back"
                        )
                    ]
                )
                
                keyboard = pagination_keyboard

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
                i18n.get_text("ADMIN_CUSTOMER_PHONE", user_id=user_id).format(phone=customer['phone_number']),
                i18n.get_text("ADMIN_CUSTOMER_LANGUAGE", user_id=user_id).format(language=customer['language'].upper() if customer['language'] else 'EN'),
                i18n.get_text("ADMIN_CUSTOMER_JOINED", user_id=user_id).format(
                    date=customer['created_at'].strftime('%Y-%m-%d %H:%M') if customer['created_at'] else i18n.get_text("UNKNOWN_DATE", user_id=user_id)
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
            
            # Create keyboard with back button and order history
            keyboard = [
                [InlineKeyboardButton(i18n.get_text("ADMIN_BACK_TO_CUSTOMERS", user_id=user_id), callback_data="admin_customers")],
                [InlineKeyboardButton(i18n.get_text("CUSTOMER_ORDER_HISTORY", user_id=user_id), callback_data=f"admin_customer_orders_{customer_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                customer_text, parse_mode="HTML", reply_markup=reply_markup
            )

        except BusinessLogicError as e:
            self.logger.error("💥 CUSTOMER DETAILS ERROR: %s", e)
            await query.message.reply_text(i18n.get_text("CUSTOMER_DETAILS_ERROR"))

    async def _show_customer_orders(self, query: CallbackQuery, customer_id: int) -> None:
        """Show order history for a specific customer."""
        try:
            user_id = query.from_user.id
            from src.db.operations import get_all_orders
            orders = get_all_orders()
            customer_orders = [o for o in orders if o.customer_id == customer_id]
            if not customer_orders:
                await query.edit_message_text(i18n.get_text("ADMIN_NO_ORDERS_FOUND", user_id=user_id), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n.get_text("ADMIN_BACK_TO_CUSTOMERS", user_id=user_id), callback_data="admin_customers")]]))
                return
            # Build a simple list with IDs, totals and dates
            lines = [i18n.get_text("ADMIN_COMPLETED_ORDERS_TITLE", user_id=user_id)]
            for o in sorted(customer_orders, key=lambda x: x.created_at or datetime.utcnow(), reverse=True):
                created = o.created_at.strftime('%Y-%m-%d %H:%M') if o.created_at else '—'
                lines.append(f"#{o.id} • ₪{o.total:.2f} • {created} • {o.status}")
            text = "\n".join(lines)
            kb = [[InlineKeyboardButton(i18n.get_text("ADMIN_BACK_TO_CUSTOMERS", user_id=user_id), callback_data="admin_customers")]]
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            self.logger.error("💥 CUSTOMER ORDERS ERROR: %s", e)
            await query.answer(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id), show_alert=True)

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

    async def _send_order_invoice_pdf(self, query: CallbackQuery, order_id: int, receipt: bool = False) -> None:
        """Generate invoice/receipt PDF and send it back to the admin chat."""
        try:
            await query.answer()
            user_id = query.from_user.id
            # Fetch full order information
            order_info = await self.admin_service.get_order_by_id(order_id)
            if not order_info:
                await query.edit_message_text(i18n.get_text("ADMIN_ORDER_NOT_FOUND", user_id=user_id))
                return
            # Prepare order dict for invoice service
            from src.db.operations import get_business_settings_dict
            business = get_business_settings_dict()
            # Enrich items with unit_price if missing
            items = []
            # Exclude synthetic Delivery pseudo-line from items to avoid double counting
            delivery_label = i18n.get_text("DELIVERY_ITEM_NAME", user_id=user_id)
            for it in order_info.get("items", []):
                if (it.get("product_name") or "").strip() == delivery_label:
                    # handled via delivery_charge totals section
                    continue
                unit = it.get("unit_price")
                if unit is None:
                    qty = it.get("quantity", 1)
                    total_price = float(it.get("total_price", 0))
                    unit = total_price / qty if qty else total_price
                items.append({
                    "product_name": it.get("product_name"),
                    "quantity": it.get("quantity", 1),
                    "unit_price": unit,
                    "total_price": it.get("total_price", unit * it.get("quantity", 1))
                })
            order_payload = {
                "order_id": order_info.get("order_id"),
                "order_number": order_info.get("order_number"),
                "customer_name": order_info.get("customer_name"),
                "customer_phone": order_info.get("customer_phone"),
                "delivery_method": order_info.get("delivery_method"),
                "delivery_address": order_info.get("delivery_address"),
                "delivery_instructions": order_info.get("delivery_instructions"),
                "items": items,
                "subtotal": float(order_info.get("subtotal", 0) or (float(order_info.get("total", 0)) - float(order_info.get("delivery_charge", 0) or 0))),
                "delivery_charge": float(order_info.get("delivery_charge", 0) or 0),
                "total": float(order_info.get("total", 0)),
                "created_at": order_info.get("created_at"),
            }
            from src.services.invoice_service import build_invoice_pdf
            result = await build_invoice_pdf(order_payload, business, receipt=receipt, user_id=user_id)
            pdf_bytes = result.get("pdf")
            html = result.get("html")
            from src.container import get_container
            container = get_container()
            bot = container.get_bot()
            if pdf_bytes:
                await bot.send_document(
                    chat_id=query.message.chat_id,
                    document=pdf_bytes,
                    filename=f"invoice_{order_id}.pdf" if not receipt else f"receipt_{order_id}.pdf",
                    caption=f"Order #{order_id} invoice" if not receipt else f"Order #{order_id} receipt"
                )
            else:
                # Fallback: send HTML as a file or message
                await bot.send_message(chat_id=query.message.chat_id, text="PDF not available; sending printable HTML below.", parse_mode="HTML")
                await bot.send_message(chat_id=query.message.chat_id, text=html)
        except Exception as e:
            self.logger.error("💥 INVOICE PDF ERROR: %s", e)
            await query.answer(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id), show_alert=True)

    async def _get_formatted_order_details(self, order_id: int, user_id: int = None) -> str | None:
        """Helper to get and format order details."""
        order_info = await self.admin_service.get_order_by_id(order_id)

        if not order_info:
            return None

        details = [
            i18n.get_text("ADMIN_ORDER_DETAILS_TITLE", user_id=user_id).format(id=order_info["order_id"]),
            i18n.get_text("ADMIN_CUSTOMER_LABEL", user_id=user_id).format(name=order_info["customer_name"]),
            i18n.get_text("ADMIN_PHONE_LABEL", user_id=user_id).format(phone=order_info["customer_phone"]),
            i18n.get_text("ADMIN_STATUS_LABEL", user_id=user_id).format(status=order_info["status"].capitalize()),
            i18n.get_text("ADMIN_DELIVERY_METHOD_LABEL", user_id=user_id).format(method=(order_info.get("delivery_method") or "Unknown").capitalize()),
            i18n.get_text("ADMIN_TOTAL_LABEL", user_id=user_id).format(amount=order_info["total"]),
            i18n.get_text("ADMIN_CREATED_LABEL", user_id=user_id).format(
                datetime=(order_info["created_at"] or datetime.utcnow()).strftime('%Y-%m-%d %H:%M')
            ),
        ]
        # Show address only for delivery
        if (order_info.get("delivery_method") or "").lower() == "delivery":
            address = order_info.get("delivery_address") or i18n.get_text("UNKNOWN_ADDRESS", user_id=user_id) if hasattr(i18n, 'get_text') else (order_info.get("delivery_address") or "Unknown")
            details.insert(5, i18n.get_text("ADMIN_DELIVERY_ADDRESS_LABEL_OPT", user_id=user_id).format(address=address))
            # Append delivery instructions if present
            if order_info.get("delivery_instructions"):
                details.insert(6, f"{i18n.get_text('DELIVERY_INSTRUCTIONS_LABEL', user_id=user_id)}: {order_info.get('delivery_instructions')}")
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
        # Add delivery as a line item if delivery method and charge present
        try:
            if (order_info.get("delivery_method") or "").lower() == "delivery":
                delivery_charge = float(order_info.get("delivery_charge") or 0)
                if delivery_charge > 0:
                    details.append(
                        i18n.get_text("ADMIN_ITEM_LINE", user_id=user_id).format(
                            name=i18n.get_text("DELIVERY_ITEM_NAME", user_id=user_id),
                            quantity=1,
                            price=delivery_charge,
                        )
                    )
        except Exception:
            pass
        return "\n".join(details)

    def _create_order_details_keyboard(
        self, order_id: int, user_id: int = None
    ) -> list[list[InlineKeyboardButton]]:
        """Creates the keyboard for the order details view."""
        statuses = [
            "pending",
            "confirmed",
            "preparing",
            # "missing" here indicates some items are unavailable; order remains active
            "missing",
            "ready",
            "delivered",
        ]
        keyboard = [
            [
                InlineKeyboardButton(
                    i18n.get_text("ADMIN_SET_STATUS", user_id=user_id).format(status=status.capitalize()),
                    callback_data=f"admin_status_{order_id}_{status}",
                )
            ]
            for status in statuses
        ]
        
        # Add invoice/receipt actions
        keyboard.append([
            InlineKeyboardButton("📄 Invoice (PDF)", callback_data=f"admin_invoice_pdf_{order_id}"),
            InlineKeyboardButton("🧾 Receipt 58mm", callback_data=f"admin_receipt_pdf_{order_id}")
        ])

        # Add delete order button
        keyboard.append([
            InlineKeyboardButton(
                i18n.get_text("ADMIN_DELETE_ORDER", user_id=user_id),
                callback_data=f"admin_delete_order_{order_id}"
            )
        ])
        
        keyboard.append(
            [InlineKeyboardButton(i18n.get_text("ADMIN_BACK_TO_ORDERS", user_id=user_id), callback_data="admin_back_to_orders")]
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

    async def _show_delete_order_confirmation(self, query: CallbackQuery, order_id: int) -> None:
        """Show confirmation dialog for order deletion"""
        try:
            user_id = query.from_user.id
            self.logger.info("🗑️ SHOWING DELETE CONFIRMATION for order #%s by admin %s", order_id, user_id)
            
            # Get order details for confirmation
            order_info = await self.admin_service.get_order_by_id(order_id)
            if not order_info:
                await query.answer(i18n.get_text("ADMIN_ORDER_NOT_FOUND", user_id=user_id))
                return
            
            # Create confirmation message
            text = i18n.get_text("ADMIN_DELETE_ORDER_CONFIRMATION", user_id=user_id).format(
                order_number=order_info.get("order_number", f"#{order_id}"),
                customer_name=order_info.get("customer_name", i18n.get_text("UNKNOWN_CUSTOMER", user_id=user_id)),
                total=order_info.get("total", 0),
                status=order_info.get("status", i18n.get_text("UNKNOWN_STATUS", user_id=user_id))
            )
            
            # Create confirmation keyboard
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_CONFIRM_DELETE", user_id=user_id),
                        callback_data=f"admin_confirm_delete_order_{order_id}"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data=f"admin_order_{order_id}"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("💥 DELETE CONFIRMATION ERROR: %s", e, exc_info=True)
            await query.answer(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _confirm_delete_order(self, query: CallbackQuery, order_id: int) -> None:
        """Confirm and execute order deletion"""
        try:
            user_id = query.from_user.id
            self.logger.info("🗑️ CONFIRMING DELETE for order #%s by admin %s", order_id, user_id)
            
            # Perform the deletion
            success = await self.admin_service.delete_order(order_id, user_id)
            
            if success:
                # Show success message
                text = i18n.get_text("ADMIN_ORDER_DELETED_SUCCESS", user_id=user_id).format(
                    order_id=order_id
                )
                
                keyboard = [
                    [InlineKeyboardButton(
                        i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=user_id),
                        callback_data="admin_back"
                    )]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
                
                await query.answer(i18n.get_text("ADMIN_ORDER_DELETED", user_id=user_id))
            else:
                await query.answer(i18n.get_text("ADMIN_ORDER_DELETE_ERROR", user_id=user_id))
                
        except Exception as e:
            self.logger.error("💥 ORDER DELETE ERROR: %s", e, exc_info=True)
            await query.answer(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

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
        
        self.logger.info(f"🔍 Admin check for user {telegram_id}, admin_chat_id: {admin_chat_id}")
        
        if admin_chat_id:
            # Convert to int if it's a string
            try:
                admin_id = int(admin_chat_id)
                is_admin = telegram_id == admin_id
                self.logger.info(f"🔍 User {telegram_id} admin check result: {is_admin}")
                return is_admin
            except (ValueError, TypeError):
                pass
        
        # Fallback: check if user ID matches common admin patterns
        # This is a simple fallback - in production you'd want a proper admin system
        is_admin = str(telegram_id) in ['598829473','6547315774','5940190001']  # Add your admin user IDs here
        self.logger.info(f"🔍 User {telegram_id} fallback admin check result: {is_admin}")
        return is_admin

    # Menu Management Methods
    async def _show_menu_management_dashboard(self, query: CallbackQuery) -> None:
        """Show menu management dashboard"""
        try:
            user_id = query.from_user.id
            
            # Get product statistics
            products = await self.admin_service.get_all_products_for_admin(user_id)
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
            self.logger.info(f"🔍 Starting _show_products_management for user {query.from_user.id}")
            user_id = query.from_user.id
            products = await self.admin_service.get_all_products_for_admin(user_id)
            self.logger.info(f"🔍 Retrieved {len(products)} products for products management")
            
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
            self.logger.info(f"🔍 About to edit message for products management")
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            self.logger.info(f"🔍 Successfully edited message for products management")
            
        except Exception as e:
            self.logger.error("Error showing products management: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _show_all_products(self, query: CallbackQuery, page: int = 0, page_size: int = 5) -> None:
        """Show all products for admin management with pagination"""
        try:
            user_id = query.from_user.id
            products = await self.admin_service.get_all_products_for_admin(user_id)
            
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
                # Use pagination helper
                extra_buttons = []
                pagination_keyboard, page_info = self._create_pagination_keyboard(
                    products, page, page_size, "admin_products", user_id, extra_buttons
                )
                
                text = (
                    f"{i18n.get_text('ADMIN_PRODUCTS_TITLE', user_id=user_id)} ({page_info['total_items']})\n"
                    f"📄 {i18n.get_text('ADMIN_SHOWING_ITEMS', user_id=user_id).format(start=page_info['start_idx'] + 1, end=page_info['end_idx'], total=page_info['total_items'])}"
                )
                
                # Add product list for current page
                for product in page_info['page_items']:
                    status_text = i18n.get_text("ADMIN_PRODUCT_ACTIVE", user_id=user_id) if product["is_active"] else i18n.get_text("ADMIN_PRODUCT_INACTIVE", user_id=user_id)
                    product_text = i18n.get_text("ADMIN_PRODUCT_BUTTON_FORMAT", user_id=user_id).format(
                        name=product["name"],
                        category=product["category"],
                        price=product["price"],
                        status=status_text
                    )
                    
                    pagination_keyboard.append([
                        InlineKeyboardButton(
                            product_text,
                            callback_data=f"admin_product_details_{product['id']}"
                        )
                    ])
                
                # Add back button
                pagination_keyboard.append([
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_BACK_TO_PRODUCTS", user_id=user_id),
                        callback_data="admin_products_management"
                    )
                ])
                
                keyboard = pagination_keyboard
            
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
            products = await self.admin_service.get_all_products_for_admin(user_id)
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
            categories = await self.admin_service.get_product_categories_multilingual(user_id)
            
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
                    products = get_all_products_by_category(category["english_name"])  # Use English name for lookup
                    product_count = len(products)
                    
                    category_text = i18n.get_text("ADMIN_CATEGORY_BUTTON_FORMAT", user_id=user_id).format(
                        name=category["name"],  # Use multilingual display name
                        count=product_count
                    )
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            category_text,
                            callback_data=f"admin_edit_category_{category['english_name']}"  # Use English name for callback
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
        """Start the multilingual add category conversation"""
        try:
            user_id = update.effective_user.id
            self.logger.info(f"🚀 Starting category creation for user {user_id}")
            if context is None:
                self.logger.error("Context is None in _start_add_category")
                if update.callback_query:
                    await update.callback_query.answer("Error: Context not available")
                return ConversationHandler.END
            if hasattr(context, 'user_data'):
                context.user_data.clear()
                self.logger.info(f"✅ Context user_data cleared for user {user_id}")
            else:
                self.logger.error("Context has no user_data attribute")
                if update.callback_query:
                    await update.callback_query.answer("Error: Context not properly initialized")
                return ConversationHandler.END
            # Use a placeholder for English name
            text = i18n.get_text("ADMIN_CATEGORY_ADD_STEP_NAME_EN", user_id=user_id)
            placeholder = i18n.get_text("ADMIN_CATEGORY_NAME_EN_PLACEHOLDER", user_id=user_id)
            keyboard = [[
                InlineKeyboardButton(
                    i18n.get_text("CANCEL", user_id=user_id),
                    callback_data="admin_category_management"
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if update.callback_query:
                await update.callback_query.edit_message_text(f"{text}\n\n<code>{placeholder}</code>", parse_mode="HTML", reply_markup=reply_markup)
            else:
                await update.message.reply_text(f"{text}\n\n<code>{placeholder}</code>", parse_mode="HTML", reply_markup=reply_markup)
            return AWAITING_CATEGORY_NAME_EN
        except Exception as e:
            self.logger.error("Error starting add category: %s", e)
            if update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_category_name_en_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle English category name input"""
        try:
            user_id = update.effective_user.id
            if context is None or not hasattr(context, 'user_data'):
                self.logger.error("Context is not properly initialized in _handle_category_name_en_input")
                await update.message.reply_text("Error: Context not available. Please try again.")
                return ConversationHandler.END
            name_en = update.message.text.strip()
            if len(name_en) < 2:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_CATEGORY_NAME_TOO_SHORT", user_id=user_id)
                )
                return AWAITING_CATEGORY_NAME_EN
            context.user_data["category_name_en"] = name_en
            # Use a placeholder for Hebrew name
            text = i18n.get_text("ADMIN_CATEGORY_ADD_STEP_NAME_HE", user_id=user_id).format(name_en=name_en)
            placeholder = i18n.get_text("ADMIN_CATEGORY_NAME_HE_PLACEHOLDER", user_id=user_id)
            keyboard = [
                [InlineKeyboardButton(i18n.get_text("ADMIN_SKIP_HEBREW", user_id=user_id), callback_data="admin_skip_hebrew_category_name")],
                [InlineKeyboardButton(i18n.get_text("CANCEL", user_id=user_id), callback_data="admin_category_management")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(f"{text}\n\n<code>{placeholder}</code>", parse_mode="HTML", reply_markup=reply_markup)
            return AWAITING_CATEGORY_NAME_HE
        except Exception as e:
            self.logger.error("Error handling English category name input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_category_name_he_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Hebrew category name input"""
        try:
            user_id = update.effective_user.id
            if context is None or not hasattr(context, 'user_data'):
                self.logger.error("Context is not properly initialized in _handle_category_name_he_input")
                await update.message.reply_text("Error: Context not available. Please try again.")
                return ConversationHandler.END
            name_he = update.message.text.strip()
            if len(name_he) < 2:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_CATEGORY_NAME_TOO_SHORT", user_id=user_id)
                )
                return AWAITING_CATEGORY_NAME_HE
            context.user_data["category_name_he"] = name_he
            return await self._finalize_category_creation(update, context)
        except Exception as e:
            self.logger.error("Error handling Hebrew category name input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_skip_hebrew_category_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle skipping Hebrew category name input"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            context.user_data["category_name_he"] = ""
            return await self._finalize_category_creation(update, context)
        except Exception as e:
            self.logger.error("Error handling skip Hebrew category name: %s", e)
            await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _finalize_category_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Finalize category creation after collecting multilingual names"""
        try:
            user_id = update.effective_user.id if update.effective_user else None
            name_en = context.user_data.get("category_name_en", "")
            name_he = context.user_data.get("category_name_he", "")
            # Check if category already exists
            existing_categories = await self.admin_service.get_product_categories_list()
            if name_en.lower() in [cat.lower() for cat in existing_categories] or (name_he and name_he.lower() in [cat.lower() for cat in existing_categories]):
                text = i18n.get_text("ADMIN_CATEGORY_ALREADY_EXISTS", user_id=user_id).format(category=name_en or name_he)
                if update.callback_query:
                    try:
                        await update.callback_query.edit_message_text(text, parse_mode="HTML")
                    except Exception:
                        await update.callback_query.message.reply_text(text, parse_mode="HTML")
                else:
                    await update.message.reply_text(text, parse_mode="HTML")
                return AWAITING_CATEGORY_NAME_EN
            result = await self.admin_service.create_category_multilingual(
                name=name_en or name_he,
                name_en=name_en,
                name_he=name_he
            )
            if result["success"]:
                # Improved confirmation rendering
                if name_he and name_en:
                    category_display = f"{name_he} ({name_en})"
                elif name_he:
                    category_display = name_he
                else:
                    category_display = name_en
                success_text = i18n.get_text("ADMIN_CATEGORY_ADD_SUCCESS", user_id=user_id).format(category=category_display)
                keyboard = [[InlineKeyboardButton(i18n.get_text("ADMIN_CATEGORY_BACK_TO_LIST", user_id=user_id), callback_data="admin_view_categories")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                if update.callback_query:
                    try:
                        await update.callback_query.edit_message_text(success_text, parse_mode="HTML", reply_markup=reply_markup)
                    except Exception:
                        await update.callback_query.message.reply_text(success_text, parse_mode="HTML", reply_markup=reply_markup)
                else:
                    await update.message.reply_text(success_text, parse_mode="HTML", reply_markup=reply_markup)
                return ConversationHandler.END
            else:
                error_text = i18n.get_text("ADMIN_CATEGORY_ADD_ERROR", user_id=user_id).format(error=result["error"])
                if update.callback_query:
                    try:
                        await update.callback_query.edit_message_text(error_text, parse_mode="HTML")
                    except Exception:
                        await update.callback_query.message.reply_text(error_text, parse_mode="HTML")
                else:
                    await update.message.reply_text(error_text, parse_mode="HTML")
            return ConversationHandler.END
        except Exception as e:
            self.logger.error("Error finalizing category creation: %s", e)
            fallback_text = i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id)
            if update.callback_query:
                try:
                    await update.callback_query.edit_message_text(fallback_text, parse_mode="HTML")
                except Exception:
                    await update.callback_query.message.reply_text(fallback_text, parse_mode="HTML")
            else:
                await update.message.reply_text(fallback_text)
            return ConversationHandler.END

    async def _start_edit_category_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the edit category name conversation"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            
            # Extract category name from callback data
            category = query.data.replace("admin_edit_category_name_", "")
            
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
            context.user_data["old_category_name"] = category
            
            return AWAITING_CATEGORY_NAME_EDIT
            
        except Exception as e:
            self.logger.error("Error starting edit category name: %s", e)
            if update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
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
        """Start the multilingual product creation process"""
        try:
            user_id = update.effective_user.id
            self.logger.info(f"🚀 Starting product creation for user {user_id}")
            
            # Ensure context is properly initialized
            if context is None:
                self.logger.error("Context is None in _start_add_product")
                if update.callback_query:
                    await update.callback_query.answer("Error: Context not available")
                return ConversationHandler.END
            
            # Clear any existing context data
            if hasattr(context, 'user_data'):
                context.user_data.clear()
                self.logger.info(f"✅ Context user_data cleared for user {user_id}")
            else:
                self.logger.error("Context has no user_data attribute")
                if update.callback_query:
                    await update.callback_query.answer("Error: Context not properly initialized")
                return ConversationHandler.END
            
            # Ask for English name first
            text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_NAME_EN", user_id=user_id)
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_products_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_PRODUCT_NAME_EN
            
        except Exception as e:
            self.logger.error("Error starting product creation: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_product_name_en_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle English product name input"""
        try:
            user_id = update.effective_user.id
            
            # Ensure context is properly initialized
            if context is None or not hasattr(context, 'user_data'):
                self.logger.error("Context is not properly initialized in _handle_product_name_en_input")
                await update.message.reply_text("Error: Context not available. Please try again.")
                return ConversationHandler.END
            
            name_en = update.message.text.strip()
            
            if len(name_en) < 2:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_ADD_PRODUCT_NAME_TOO_SHORT", user_id=user_id)
                )
                return AWAITING_PRODUCT_NAME_EN
            
            # Store English name
            context.user_data["product_name_en"] = name_en
            
            # Ask for Hebrew name
            text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_NAME_HE", user_id=user_id).format(name_en=name_en)
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_SKIP_HEBREW", user_id=user_id),
                        callback_data="admin_skip_hebrew_name"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_products_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_PRODUCT_NAME_HE
            
        except Exception as e:
            self.logger.error("Error handling English name input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_product_name_he_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Hebrew product name input"""
        try:
            user_id = update.effective_user.id
            name_he = update.message.text.strip()
            
            if len(name_he) < 2:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_ADD_PRODUCT_NAME_HE_TOO_SHORT", user_id=user_id)
                )
                return AWAITING_PRODUCT_NAME_HE
            
            # Store Hebrew name
            context.user_data["product_name_he"] = name_he
            name_en = context.user_data["product_name_en"]
            
            # Ask for English description
            text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_DESCRIPTION_EN", user_id=user_id).format(
                name_en=name_en, name_he=name_he
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_products_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_PRODUCT_DESCRIPTION_EN
            
        except Exception as e:
            self.logger.error("Error handling Hebrew name input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_product_description_en_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle English product description input"""
        try:
            user_id = update.effective_user.id
            description_en = update.message.text.strip()
            
            if len(description_en) < 5:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_ADD_PRODUCT_DESCRIPTION_TOO_SHORT", user_id=user_id)
                )
                return AWAITING_PRODUCT_DESCRIPTION_EN
            
            # Store English description
            context.user_data["product_description_en"] = description_en
            
            # Ask for Hebrew description
            text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_DESCRIPTION_HE", user_id=user_id).format(
                description_en=description_en
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_SKIP_HEBREW", user_id=user_id),
                        callback_data="admin_skip_hebrew_description"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_products_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_PRODUCT_DESCRIPTION_HE
            
        except Exception as e:
            self.logger.error("Error handling English description input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_product_description_he_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Hebrew product description input"""
        try:
            user_id = update.effective_user.id
            description_he = update.message.text.strip()
            
            if len(description_he) < 5:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_ADD_PRODUCT_DESCRIPTION_HE_TOO_SHORT", user_id=user_id)
                )
                return AWAITING_PRODUCT_DESCRIPTION_HE
            
            # Store Hebrew description
            context.user_data["product_description_he"] = description_he
            
            # Ask for image URL (optional)
            text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_IMAGE_URL", user_id=user_id)
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_SKIP_IMAGE", user_id=user_id),
                        callback_data="admin_skip_image_url"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_products_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_PRODUCT_IMAGE_URL
            
        except Exception as e:
            self.logger.error("Error handling Hebrew description input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_product_image_url_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle product image URL input"""
        try:
            user_id = update.effective_user.id
            image_url = update.message.text.strip()
            
            # Basic URL validation
            if image_url and not (image_url.startswith('http://') or image_url.startswith('https://')):
                await update.message.reply_text(
                    i18n.get_text("ADMIN_ADD_PRODUCT_INVALID_URL", user_id=user_id)
                )
                return AWAITING_PRODUCT_IMAGE_URL
            

            
            # Store image URL
            context.user_data["product_image_url"] = image_url if image_url else None
            
            # Show category selection
            return await self._show_category_selection_for_new_product(update, context)
            
        except Exception as e:
            self.logger.error("Error handling image URL input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _show_category_selection_for_new_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show category selection for new product"""
        try:
            user_id = update.effective_user.id
            
            self.logger.info(f"📋 Starting category selection for user {user_id}")
            
            # Get available categories
            categories = await self.admin_service.get_product_categories_list()
            
            text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_CATEGORY", user_id=user_id).format(
                name_en=context.user_data["product_name_en"],
                name_he=context.user_data.get("product_name_he", ""),
                description_en=context.user_data["product_description_en"],
                description_he=context.user_data.get("product_description_he", "")
            )
            
            # Create category buttons
            keyboard = []
            for category in categories:
                keyboard.append([
                    InlineKeyboardButton(
                        category.title(),
                        callback_data=f"admin_add_product_category_{category}"
                    )
                ])
            
            # Add cancel button
            keyboard.append([
                InlineKeyboardButton(
                    i18n.get_text("CANCEL", user_id=user_id),
                    callback_data="admin_products_management"
                )
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Handle both callback queries and regular messages
            if update.callback_query:
                await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
                self.logger.info(f"✅ Category selection shown via callback for user {user_id}")
            else:
                await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
                self.logger.info(f"✅ Category selection shown via message for user {user_id}")
            
            return AWAITING_PRODUCT_CATEGORY
            
        except Exception as e:
            self.logger.error("Error showing category selection: %s", e)
            if update.callback_query:
                await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            else:
                await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_product_category_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle product category selection"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            data = query.data
            
            if data.startswith("admin_add_product_category_"):
                category = data.replace("admin_add_product_category_", "")
                context.user_data["product_category"] = category
                
                # Ask for price
                text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_PRICE", user_id=user_id).format(
                    name_en=context.user_data["product_name_en"],
                    category=category.title()
                )
                
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("CANCEL", user_id=user_id),
                            callback_data="admin_products_management"
                        )
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
                
                return AWAITING_PRODUCT_PRICE
                
        except Exception as e:
            self.logger.error("Error handling category selection: %s", e)
            await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
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
                        i18n.get_text("ADMIN_ADD_PRODUCT_INVALID_PRICE", user_id=user_id)
                    )
                    return AWAITING_PRODUCT_PRICE
            except ValueError:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_ADD_PRODUCT_INVALID_PRICE", user_id=user_id)
                )
                return AWAITING_PRODUCT_PRICE
            
            # Store price
            context.user_data["product_price"] = price
            
            # Show confirmation
            return await self._show_product_confirmation(update, context)
            
        except Exception as e:
            self.logger.error("Error handling price input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _show_product_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show product creation confirmation"""
        try:
            user_id = update.effective_user.id
            
            # Prepare confirmation text
            name_en = context.user_data["product_name_en"]
            name_he = context.user_data.get("product_name_he", "")
            description_en = context.user_data["product_description_en"]
            description_he = context.user_data.get("product_description_he", "")
            category = context.user_data["product_category"]
            price = context.user_data["product_price"]
            image_url = context.user_data.get("product_image_url")
            
            text = i18n.get_text("ADMIN_ADD_PRODUCT_CONFIRMATION", user_id=user_id).format(
                name_en=name_en,
                name_he=name_he if name_he else "N/A",
                description_en=description_en,
                description_he=description_he if description_he else "N/A",
                category=category.title(),
                price=price,
                image_url=image_url if image_url else "N/A"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_CONFIRM_YES", user_id=user_id),
                        callback_data="admin_add_product_confirm_yes"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_CONFIRM_NO", user_id=user_id),
                        callback_data="admin_add_product_confirm_no"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Handle both callback queries and regular messages
            if update.callback_query:
                await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_PRODUCT_CONFIRMATION
            
        except Exception as e:
            self.logger.error("Error showing product confirmation: %s", e)
            if update.callback_query:
                await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            else:
                await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_product_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle product creation confirmation"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            data = query.data
            
            if data == "admin_add_product_confirm_yes":
                # Create the product with multilingual support
                name_en = context.user_data["product_name_en"]
                name_he = context.user_data.get("product_name_he", "")
                description_en = context.user_data["product_description_en"]
                description_he = context.user_data.get("product_description_he", "")
                category = context.user_data["product_category"]
                price = context.user_data["product_price"]
                image_url = context.user_data.get("product_image_url")
                
                # Use the primary name as the main name
                primary_name = name_en if name_en else name_he
                primary_description = description_en if description_en else description_he
                
                result = await self.admin_service.create_new_product_multilingual(
                    name=primary_name,
                    description=primary_description,
                    category=category,
                    price=price,
                    image_url=image_url,
                    name_en=name_en,
                    name_he=name_he,
                    description_en=description_en,
                    description_he=description_he
                )
                
                if result["success"]:
                    product = result["product"]
                    success_text = i18n.get_text("ADMIN_ADD_PRODUCT_SUCCESS_MULTILINGUAL", user_id=user_id).format(
                        name_en=product.get("name_en", product["name"]),
                        name_he=product.get("name_he", "N/A"),
                        category=product["category"],
                        price=product["price"]
                    )
                    
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                i18n.get_text("ADMIN_PRODUCT_BACK_TO_MANAGEMENT", user_id=user_id),
                                callback_data="admin_products_management"
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
            if update.callback_query:
                await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=update.callback_query.from_user.id))
            else:
                await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=update.effective_user.id))
            return ConversationHandler.END

    async def _handle_skip_hebrew_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle skipping Hebrew name input"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            
            # Set Hebrew name to empty
            context.user_data["product_name_he"] = ""
            name_en = context.user_data["product_name_en"]
            
            # Ask for English description
            text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_DESCRIPTION_EN", user_id=user_id).format(
                name_en=name_en, name_he=""
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_products_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_PRODUCT_DESCRIPTION_EN
            
        except Exception as e:
            self.logger.error("Error handling skip Hebrew name: %s", e)
            await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_skip_hebrew_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle skipping Hebrew description input"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            
            # Set Hebrew description to empty
            context.user_data["product_description_he"] = ""
            
            # Ask for image URL
            text = i18n.get_text("ADMIN_ADD_PRODUCT_STEP_IMAGE_URL", user_id=user_id)
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_SKIP_IMAGE", user_id=user_id),
                        callback_data="admin_skip_image_url"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_products_management"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            return AWAITING_PRODUCT_IMAGE_URL
            
        except Exception as e:
            self.logger.error("Error handling skip Hebrew description: %s", e)
            await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_skip_image_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle skipping image URL input"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            
            self.logger.info(f"🔄 Skipping image URL for user {user_id}")
            self.logger.info(f"🔍 Current context user_data: {context.user_data}")
            
            # Set image URL to None
            context.user_data["product_image_url"] = None
            
            # Show category selection
            self.logger.info(f"📋 Showing category selection for user {user_id}")
            return await self._show_category_selection_for_new_product(update, context)
            
        except Exception as e:
            self.logger.error("Error handling skip image URL: %s", e)
            if update.callback_query:
                await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            else:
                await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_product_callback(self, query: CallbackQuery, data: str) -> None:
        """Handle product-related callbacks"""
        try:
            user_id = query.from_user.id
            
            if data.startswith("admin_product_details_"):
                product_id = int(data.split("_")[-1])
                await self._show_product_details(query, product_id)
            elif data.startswith("admin_product_edit_"):
                # This is now handled by the conversation handler
                # The conversation handler will call _start_edit_product with proper parameters
                pass
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
            products = await self.admin_service.get_all_products_for_admin(user_id)
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
                        i18n.get_text("ADMIN_PRODUCT_TOGGLE_STATUS", user_id=user_id),
                        callback_data=f"admin_product_toggle_{product_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_DEACTIVATE", user_id=user_id),
                        callback_data=f"admin_product_deactivate_{product_id}"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_HARD_DELETE", user_id=user_id),
                        callback_data=f"admin_product_hard_delete_{product_id}"
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

    async def _start_edit_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the edit product wizard conversation"""
        try:
            # Extract query from update
            query = update.callback_query
            user_id = query.from_user.id
            
            self.logger.info("🎯 Starting edit product wizard for user %s, callback: %s", user_id, query.data)
            
            # Extract product_id from callback data: admin_product_edit_{product_id}
            product_id = int(query.data.split("_")[-1])
            
            products = await self.admin_service.get_all_products_for_admin(user_id)
            product = next((p for p in products if p["id"] == product_id), None)
            
            if not product:
                await query.message.reply_text(i18n.get_text("ADMIN_PRODUCT_NOT_FOUND", user_id=user_id))
                return ConversationHandler.END
            
            # Store product info in context for editing
            context.user_data["editing_product"] = product
            context.user_data["editing_product_id"] = product_id
            
            self.logger.info("📝 Showing edit options for product: %s (ID: %s)", product["name"], product_id)
            
            # Show edit options
            await self._show_edit_product_options(query, product)
            
            return AWAITING_PRODUCT_EDIT_FIELD
            
        except Exception as e:
            self.logger.error("Error starting edit product: %s", e)
            await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _start_edit_product_with_context(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the edit product wizard conversation (with context)"""
        try:
            # Extract query from update
            query = update.callback_query
            user_id = query.from_user.id
            
            self.logger.info("🎯 Starting edit product wizard for user %s, callback: %s", user_id, query.data)
            
            # Extract product_id from callback data: admin_product_edit_{product_id}
            product_id = int(query.data.split("_")[-1])
            
            products = await self.admin_service.get_all_products_for_admin(user_id)
            product = next((p for p in products if p["id"] == product_id), None)
            
            if not product:
                await query.message.reply_text(i18n.get_text("ADMIN_PRODUCT_NOT_FOUND", user_id=user_id))
                return ConversationHandler.END
            
            # Store product info in context for editing
            context.user_data["editing_product"] = product
            context.user_data["editing_product_id"] = product_id
            
            self.logger.info("📝 Showing edit options for product: %s (ID: %s)", product["name"], product_id)
            
            # Show edit options
            await self._show_edit_product_options(query, product)
            
            return AWAITING_PRODUCT_EDIT_FIELD
            
        except Exception as e:
            self.logger.error("Error starting edit product: %s", e)
            await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _show_edit_product_options(self, query: CallbackQuery, product: Dict) -> None:
        """Show product edit options"""
        try:
            user_id = query.from_user.id
            
            # Translate category name
            from src.utils.i18n import translate_category_name
            translated_category = translate_category_name(product["category"], user_id=user_id)
            
            text = (
                i18n.get_text("ADMIN_EDIT_PRODUCT_WIZARD_TITLE", user_id=user_id) + "\n\n" +
                i18n.get_text("ADMIN_EDIT_PRODUCT_CURRENT_VALUES", user_id=user_id) + "\n" +
                i18n.get_text("ADMIN_PRODUCT_NAME", user_id=user_id).format(name=product["name"]) + "\n" +
                i18n.get_text("ADMIN_PRODUCT_DESCRIPTION", user_id=user_id).format(description=product["description"]) + "\n" +
                i18n.get_text("ADMIN_PRODUCT_CATEGORY", user_id=user_id).format(category=translated_category) + "\n" +
                i18n.get_text("ADMIN_PRODUCT_PRICE", user_id=user_id).format(price=product["price"]) + "\n\n" +
                i18n.get_text("ADMIN_EDIT_PRODUCT_SELECT_FIELD", user_id=user_id)
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_PRODUCT_FIELD_NAME", user_id=user_id),
                        callback_data=f"admin_edit_product_field_name_{product['id']}"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_PRODUCT_FIELD_DESCRIPTION", user_id=user_id),
                        callback_data=f"admin_edit_product_field_description_{product['id']}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_PRODUCT_FIELD_CATEGORY", user_id=user_id),
                        callback_data=f"admin_edit_product_field_category_{product['id']}"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_PRODUCT_FIELD_PRICE", user_id=user_id),
                        callback_data=f"admin_edit_product_field_price_{product['id']}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_PRODUCT_FIELD_STATUS", user_id=user_id),
                        callback_data=f"admin_edit_product_field_status_{product['id']}"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_PRODUCT_FIELD_IMAGE", user_id=user_id),
                        callback_data=f"admin_edit_product_field_image_url_{product['id']}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_product_back_to_list"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing edit product options: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _handle_edit_product_field_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle edit product field selection"""
        try:
            # Extract query from update
            query = update.callback_query
            user_id = query.from_user.id
            data = query.data
            
            # Parse field from callback data: admin_edit_product_field_{field}_{product_id}
            parts = data.split("_")
            
            # Handle special case for image_url field which has 7 parts: admin_edit_product_field_image_url_{product_id}
            if len(parts) == 7 and parts[4] == "image" and parts[5] == "url":
                field = "image_url"
                product_id = int(parts[6])
            else:
                field = parts[4]  # name, description, category, price, status
                product_id = int(parts[5])
            
            # Store field info in context
            context.user_data["editing_field"] = field
            context.user_data["editing_product_id"] = product_id
            
            # Get current product info and store in context
            products = await self.admin_service.get_all_products_for_admin(user_id)
            product = next((p for p in products if p["id"] == product_id), None)
            
            if not product:
                await query.message.reply_text(i18n.get_text("ADMIN_PRODUCT_NOT_FOUND", user_id=user_id))
                return ConversationHandler.END
            
            # Store product info in context for editing
            context.user_data["editing_product"] = product
            
            # Show field-specific input prompt
            await self._show_field_input_prompt(query, product, field)
            
            return AWAITING_PRODUCT_EDIT_VALUE
            
        except Exception as e:
            self.logger.error("Error handling edit product field selection: %s", e)
            await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _show_field_input_prompt(self, query: CallbackQuery, product: Dict, field: str) -> None:
        """Show field-specific input prompt"""
        try:
            user_id = query.from_user.id
            
            # Get current value
            current_value = product.get(field, "")
            
            # Special handling for category field - show category buttons
            if field == "category":
                await self._show_category_selection(query, product, current_value)
                return
            
            # Get field-specific prompt for other fields
            if field == "name":
                text = i18n.get_text("ADMIN_EDIT_PRODUCT_NAME_PROMPT", user_id=user_id).format(
                    current=current_value
                )
            elif field == "description":
                text = i18n.get_text("ADMIN_EDIT_PRODUCT_DESCRIPTION_PROMPT", user_id=user_id).format(
                    current=current_value
                )
            elif field == "price":
                text = i18n.get_text("ADMIN_EDIT_PRODUCT_PRICE_PROMPT", user_id=user_id).format(
                    current=current_value
                )
            elif field == "status":
                text = i18n.get_text("ADMIN_EDIT_PRODUCT_STATUS_PROMPT", user_id=user_id).format(
                    current="Active" if product.get("is_active", True) else "Inactive"
                )
            elif field == "image_url":
                text = i18n.get_text("ADMIN_EDIT_PRODUCT_IMAGE_PROMPT", user_id=user_id).format(
                    current=current_value if current_value else "No image set"
                )
            else:
                text = i18n.get_text("ADMIN_EDIT_PRODUCT_GENERIC_PROMPT", user_id=user_id).format(
                    field=field, current=current_value
                )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_edit_product_cancel"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing field input prompt: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=query.from_user.id))

    async def _show_category_selection(self, query: CallbackQuery, product: Dict, current_category: str) -> None:
        """Show category selection buttons"""
        try:
            user_id = query.from_user.id
            
            # Get all available categories
            categories = await self.admin_service.get_product_categories_list()
            
            if not categories:
                await query.edit_message_text(
                    i18n.get_text("ADMIN_NO_CATEGORIES", user_id=user_id),
                    parse_mode="HTML"
                )
                return
            
            text = i18n.get_text("ADMIN_EDIT_PRODUCT_CATEGORY_SELECTION", user_id=user_id).format(
                current=current_category
            )
            
            # Create category buttons (2 per row)
            keyboard = []
            row = []
            for category in categories:
                # Use consistent emoji - all categories get 📂, current gets highlighted with ✅
                if category == current_category:
                    button_text = f"✅ {category}"
                else:
                    button_text = f"📂 {category}"
                
                row.append(InlineKeyboardButton(
                    button_text,
                    callback_data=f"admin_edit_product_category_{category}"
                ))
                
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            
            # Add remaining buttons
            if row:
                keyboard.append(row)
            
            # Add cancel button
            keyboard.append([
                InlineKeyboardButton(
                    i18n.get_text("CANCEL", user_id=user_id),
                    callback_data="admin_edit_product_cancel"
                )
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing category selection: %s", e)
            await query.edit_message_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))


    async def _handle_category_selection_for_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle category selection for edit product wizard"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            
            # Extract category from callback data
            data = query.data
            selected_category = data.replace("admin_edit_product_category_", "")
            self.logger.info("🎯 Category selected for edit: %s by user %s", selected_category, user_id)
            
            # Store the selected category in context
            context.user_data["new_value"] = selected_category
            
            # Show confirmation screen
            await self._show_edit_confirmation(update, context)
            
            return AWAITING_PRODUCT_EDIT_CONFIRM
            
        except Exception as e:
            self.logger.error("Error handling category selection for edit: %s", e)
            await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_edit_product_value_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle edit product value input"""
        try:
            user_id = update.effective_user.id
            new_value = update.message.text.strip()
            field = context.user_data.get("editing_field")
            product_id = context.user_data.get("editing_product_id")
            
            if not field or not product_id:
                await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
                return ConversationHandler.END
            
            # Validate input based on field
            validation_result = await self._validate_edit_input(field, new_value, user_id)
            if not validation_result["valid"]:
                await update.message.reply_text(validation_result["error"])
                return AWAITING_PRODUCT_EDIT_VALUE
            

            
            # Store new value in context
            context.user_data["new_value"] = new_value
            
            # Show confirmation screen
            await self._show_edit_confirmation(update, context)
            
            return AWAITING_PRODUCT_EDIT_CONFIRM
            
        except Exception as e:
            self.logger.error("Error handling edit product value input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _validate_edit_input(self, field: str, value: str, user_id: int) -> Dict:
        """Validate edit input based on field"""
        try:
            if field == "name":
                if len(value) < 2:
                    return {
                        "valid": False,
                        "error": i18n.get_text("ADMIN_EDIT_PRODUCT_NAME_TOO_SHORT", user_id=user_id)
                    }
            elif field == "description":
                if len(value) < 5:
                    return {
                        "valid": False,
                        "error": i18n.get_text("ADMIN_EDIT_PRODUCT_DESCRIPTION_TOO_SHORT", user_id=user_id)
                    }
            elif field == "category":
                if len(value) < 2:
                    return {
                        "valid": False,
                        "error": i18n.get_text("ADMIN_EDIT_PRODUCT_CATEGORY_TOO_SHORT", user_id=user_id)
                    }
            elif field == "price":
                try:
                    price = float(value)
                    if price <= 0:
                        return {
                            "valid": False,
                            "error": i18n.get_text("ADMIN_EDIT_PRODUCT_PRICE_TOO_LOW", user_id=user_id)
                        }
                except ValueError:
                    return {
                        "valid": False,
                        "error": i18n.get_text("ADMIN_EDIT_PRODUCT_PRICE_INVALID", user_id=user_id)
                    }
            elif field == "status":
                if value.lower() not in ["active", "inactive", "true", "false", "1", "0"]:
                    return {
                        "valid": False,
                        "error": i18n.get_text("ADMIN_EDIT_PRODUCT_STATUS_INVALID", user_id=user_id)
                    }
            elif field == "image_url":
                # Allow empty image URL (to remove image)
                if value.strip() == "":
                    return {"valid": True}
                # Basic URL validation
                if not value.startswith(("http://", "https://")):
                    return {
                        "valid": False,
                        "error": i18n.get_text("ADMIN_EDIT_PRODUCT_IMAGE_INVALID", user_id=user_id)
                    }

            
            return {"valid": True}
            
        except Exception as e:
            self.logger.error("Error validating edit input: %s", e)
            return {
                "valid": False,
                "error": i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id)
            }

    async def _show_edit_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show edit confirmation screen"""
        try:
            user_id = update.effective_user.id
            field = context.user_data.get("editing_field")
            new_value = context.user_data.get("new_value")
            product_id = context.user_data.get("editing_product_id")
            
            # Get current product info
            products = await self.admin_service.get_all_products_for_admin(user_id)
            product = next((p for p in products if p["id"] == product_id), None)
            
            if not product:
                # Handle both message and callback_query cases
                if update.callback_query:
                    await update.callback_query.edit_message_text(i18n.get_text("ADMIN_PRODUCT_NOT_FOUND", user_id=user_id))
                else:
                    await update.message.reply_text(i18n.get_text("ADMIN_PRODUCT_NOT_FOUND", user_id=user_id))
                return
            
            # Get current value
            current_value = product.get(field, "")
            if field == "status":
                current_value = "Active" if product.get("is_active", True) else "Inactive"
            
            # Format new value for display
            display_new_value = new_value
            if field == "price":
                try:
                    display_new_value = f"₪{float(new_value):.2f}"
                except:
                    display_new_value = new_value
            elif field == "status":
                if new_value.lower() in ["active", "true", "1"]:
                    display_new_value = "Active"
                else:
                    display_new_value = "Inactive"
            
            text = i18n.get_text("ADMIN_EDIT_PRODUCT_CONFIRM_TITLE", user_id=user_id) + "\n\n" + \
                   i18n.get_text("ADMIN_EDIT_PRODUCT_CONFIRM_DETAILS", user_id=user_id).format(
                       field=i18n.get_text(f"ADMIN_EDIT_PRODUCT_FIELD_{field.upper()}", user_id=user_id),
                       current=current_value,
                       new=display_new_value
                   )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_PRODUCT_CONFIRM_YES", user_id=user_id),
                        callback_data="admin_edit_product_confirm_yes"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_PRODUCT_CONFIRM_NO", user_id=user_id),
                        callback_data="admin_edit_product_confirm_no"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Handle both message and callback_query cases
            if update.callback_query:
                await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing edit confirmation: %s", e)
            # Handle both message and callback_query cases for error
            if update.callback_query:
                await update.callback_query.edit_message_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            else:
                await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _handle_edit_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle edit confirmation"""
        try:
            # Extract query from update
            query = update.callback_query
            user_id = query.from_user.id
            data = query.data
            
            self.logger.info("🎯 Handling edit confirmation: %s for user %s", data, user_id)
            self.logger.info("📝 Context data: %s", context.user_data)
            
            if data == "admin_edit_product_confirm_yes":
                # Apply the edit
                result = await self._apply_product_edit(context)
                
                self.logger.info("📊 Edit result: %s", result)
                
                if result["success"]:
                    # Get field name for display
                    editing_field = context.user_data.get('editing_field', '')
                    field_display_name = editing_field.capitalize()
                    
                    # Try to get localized field name, fallback to capitalized field name
                    try:
                        field_display_name = i18n.get_text(f"ADMIN_EDIT_PRODUCT_FIELD_{editing_field.upper()}", user_id=user_id)
                    except Exception as e:
                        self.logger.warning("Could not get localized field name for %s: %s", editing_field, e)
                    
                    success_text = i18n.get_text("ADMIN_EDIT_PRODUCT_WIZARD_SUCCESS", user_id=user_id).format(
                        field=field_display_name,
                        value=context.user_data.get("new_value", "")
                    )
                    
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                i18n.get_text("ADMIN_EDIT_PRODUCT_CONTINUE_EDITING", user_id=user_id),
                                callback_data=f"admin_product_details_{context.user_data.get('editing_product_id')}"
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
                    await query.edit_message_text(success_text, parse_mode="HTML", reply_markup=reply_markup)
                else:
                    await query.edit_message_text(
                        i18n.get_text("ADMIN_EDIT_PRODUCT_ERROR", user_id=user_id).format(error=result["error"])
                    )
                
                # Clear context
                context.user_data.clear()
                return ConversationHandler.END
                
            elif data == "admin_edit_product_confirm_no":
                # Go back to edit options
                product_id = context.user_data.get("editing_product_id")
                products = await self.admin_service.get_all_products_for_admin(user_id)
                product = next((p for p in products if p["id"] == product_id), None)
                
                if product:
                    await self._show_edit_product_options(query, product)
                    return AWAITING_PRODUCT_EDIT_FIELD
                else:
                    await query.edit_message_text(i18n.get_text("ADMIN_PRODUCT_NOT_FOUND", user_id=user_id))
                    return ConversationHandler.END
            
        except Exception as e:
            self.logger.error("Error handling edit confirmation: %s", e)
            await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _apply_product_edit(self, context: ContextTypes.DEFAULT_TYPE) -> Dict:
        """Apply the product edit"""
        try:
            field = context.user_data.get("editing_field")
            new_value = context.user_data.get("new_value")
            product_id = context.user_data.get("editing_product_id")
            
            self.logger.info("🔧 Applying product edit: field=%s, value=%s, product_id=%s", field, new_value, product_id)
            
            # Prepare update data
            update_data = {}
            
            if field == "name":
                update_data["name"] = new_value
            elif field == "description":
                update_data["description"] = new_value
            elif field == "category":
                update_data["category"] = new_value
            elif field == "price":
                update_data["price"] = float(new_value)
            elif field == "status":
                update_data["is_active"] = new_value.lower() in ["active", "true", "1"]
            elif field == "image_url":
                update_data["image_url"] = new_value.strip() if new_value.strip() else None
            
            self.logger.info("📝 Update data: %s", update_data)
            
            # Apply the update
            result = await self.admin_service.update_existing_product(product_id, **update_data)
            
            self.logger.info("📊 Update result: %s", result)
            
            return result
            
        except Exception as e:
            self.logger.error("Error applying product edit: %s", e)
            return {"success": False, "error": str(e)}

    async def _show_remove_product_confirmation(self, query: CallbackQuery, product_id: int) -> None:
        """Show remove product confirmation"""
        try:
            user_id = query.from_user.id
            products = await self.admin_service.get_all_products_for_admin(user_id)
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

    async def _show_deactivate_product_confirmation(self, query: CallbackQuery, product_id: int) -> None:
        """Show deactivate product confirmation"""
        try:
            user_id = query.from_user.id
            products = await self.admin_service.get_all_products_for_admin(user_id)
            product = next((p for p in products if p["id"] == product_id), None)
            
            if not product:
                await query.message.reply_text(i18n.get_text("ADMIN_PRODUCT_NOT_FOUND", user_id=user_id))
                return
            
            text = i18n.get_text("ADMIN_DEACTIVATE_PRODUCT_CONFIRM", user_id=user_id).format(
                name=product["name"],
                category=product["category"],
                price=product["price"]
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_YES_DEACTIVATE", user_id=user_id),
                        callback_data=f"admin_product_yes_deactivate_{product_id}"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_NO_DEACTIVATE", user_id=user_id),
                        callback_data="admin_product_no_deactivate"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing deactivate confirmation: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _show_hard_delete_product_confirmation(self, query: CallbackQuery, product_id: int) -> None:
        """Show hard delete product confirmation with warning"""
        try:
            user_id = query.from_user.id
            self.logger.info("🔍 Showing hard delete confirmation for product ID %d", product_id)
            
            products = await self.admin_service.get_all_products_for_admin(user_id)
            product = next((p for p in products if p["id"] == product_id), None)
            
            if not product:
                self.logger.warning("Product ID %d not found", product_id)
                await query.message.reply_text(i18n.get_text("ADMIN_PRODUCT_NOT_FOUND", user_id=user_id))
                return
            
            self.logger.info("Found product: %s", product["name"])
            
            text = i18n.get_text("ADMIN_HARD_DELETE_PRODUCT_CONFIRM", user_id=user_id).format(
                name=product["name"],
                category=product["category"],
                price=product["price"]
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_YES_HARD_DELETE", user_id=user_id),
                        callback_data=f"admin_product_yes_hard_delete_{product_id}"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_PRODUCT_NO_HARD_DELETE", user_id=user_id),
                        callback_data="admin_product_no_hard_delete"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            self.logger.info("Sending hard delete confirmation message")
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error showing hard delete confirmation: %s", e, exc_info=True)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _show_delete_product_confirmation(self, query: CallbackQuery, product_id: int) -> None:
        """Show delete product confirmation (deprecated, use _show_deactivate_product_confirmation)"""
        await self._show_deactivate_product_confirmation(query, product_id)

    async def _toggle_product_status(self, query: CallbackQuery, product_id: int) -> None:
        """Toggle product active/inactive status"""
        try:
            user_id = query.from_user.id
            products = await self.admin_service.get_all_products_for_admin(user_id)
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

    async def _deactivate_product(self, query: CallbackQuery, product_id: int) -> None:
        """Deactivate a product (soft delete)"""
        try:
            user_id = query.from_user.id
            result = await self.admin_service.deactivate_product(product_id)
            
            if result["success"]:
                await query.answer(result["message"])
                await self._show_all_products(query)
            else:
                await query.message.reply_text(
                    i18n.get_text("ADMIN_DEACTIVATE_PRODUCT_ERROR", user_id=user_id).format(error=result["error"])
                )
                
        except Exception as e:
            self.logger.error("Error deactivating product: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _hard_delete_product(self, query: CallbackQuery, product_id: int) -> None:
        """Hard delete a product (permanent removal)"""
        try:
            user_id = query.from_user.id
            result = await self.admin_service.hard_delete_product(product_id)
            
            if result["success"]:
                await query.answer(result["message"])
                await self._show_all_products(query)
            else:
                await query.message.reply_text(
                    i18n.get_text("ADMIN_HARD_DELETE_PRODUCT_ERROR", user_id=user_id).format(error=result["error"])
                )
                
        except Exception as e:
            self.logger.error("Error hard deleting product: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    # Keep backward compatibility
    async def _delete_product(self, query: CallbackQuery, product_id: int) -> None:
        """Delete (deactivate) a product (deprecated, use _deactivate_product)"""
        await self._deactivate_product(query, product_id)



    async def _handle_admin_language_selection(self, query: CallbackQuery) -> None:
        """Handle language selection from business info"""
        try:
            user_id = query.from_user.id
            
            # Show language selection keyboard
            await query.edit_message_text(
                i18n.get_text("SELECT_LANGUAGE_PROMPT", user_id=user_id),
                reply_markup=self._get_admin_language_selection_keyboard(),
                parse_mode="HTML"
            )
                
        except Exception as e:
            self.logger.error("Error handling admin language selection: %s", e)
            await query.answer(i18n.get_text("LANGUAGE_SELECTION_ERROR", user_id=user_id))

    def _get_admin_language_selection_keyboard(self):
        """Get language selection keyboard for admin"""
        keyboard = [
            [
                InlineKeyboardButton("🇺🇸 English", callback_data="admin_language_en"),
                InlineKeyboardButton("🇮🇱 עברית", callback_data="admin_language_he")
            ],
            [InlineKeyboardButton(i18n.get_text("BACK_TO_BUSINESS_SETTINGS", user_id=None), callback_data="admin_business_settings")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _handle_admin_language_change(self, query: CallbackQuery) -> None:
        """Handle language change for admin"""
        try:
            user_id = query.from_user.id
            data = query.data
            
            if data.startswith("admin_language_"):
                # Handle language change
                language = data.split("_")[-1]  # admin_language_en -> en
                language_manager.set_user_language(user_id, language)
                
                # Show success message in new language and return to business settings
                await query.answer(i18n.get_text("LANGUAGE_CHANGED", user_id=user_id))
                await self._show_business_settings(query)
                
        except Exception as e:
            self.logger.error("Error handling admin language change: %s", e)
            await query.answer(i18n.get_text("LANGUAGE_CHANGE_ERROR", user_id=user_id))

    async def _show_remove_products_list(self, query: CallbackQuery) -> None:
        """Show list of products for removal"""
        try:
            user_id = query.from_user.id
            products = await self.admin_service.get_all_products_for_admin(user_id)
            
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

    async def _show_business_settings(self, query: CallbackQuery) -> None:
        """Show current business settings and info"""
        try:
            user_id = query.from_user.id
            result = await self.admin_service.get_business_settings()
            
            if result["success"]:
                settings = result["settings"]
                
                # Get config for additional info
                from src.config import get_config
                config = get_config()
                
                text = i18n.get_text("ADMIN_BUSINESS_SETTINGS_TITLE", user_id=user_id)
                text += "\n\n"
                
                # Display current settings
                text += f"🏪 <b>{i18n.get_text('ADMIN_BUSINESS_NAME', user_id=user_id)}:</b> {settings.get('business_name', 'N/A')}\n"
                text += f"📝 <b>{i18n.get_text('ADMIN_BUSINESS_DESCRIPTION', user_id=user_id)}:</b> {settings.get('business_description', 'N/A')}\n"
                text += f"📍 <b>{i18n.get_text('ADMIN_BUSINESS_ADDRESS', user_id=user_id)}:</b> {settings.get('business_address', 'N/A')}\n"
                text += f"📞 <b>{i18n.get_text('ADMIN_BUSINESS_PHONE', user_id=user_id)}:</b> {settings.get('business_phone', 'N/A')}\n"
                text += f"📧 <b>{i18n.get_text('ADMIN_BUSINESS_EMAIL', user_id=user_id)}:</b> {settings.get('business_email', 'N/A')}\n"
                text += f"🌐 <b>{i18n.get_text('ADMIN_BUSINESS_WEBSITE', user_id=user_id)}:</b> {settings.get('business_website', 'N/A')}\n"
                text += f"🕒 <b>{i18n.get_text('ADMIN_BUSINESS_HOURS', user_id=user_id)}:</b> {settings.get('business_hours', 'N/A')}\n"
                # Keep showing default delivery charge for transparency, but clarify it's a default
                text += f"🚚 <b>{i18n.get_text('ADMIN_DEFAULT_DELIVERY_CHARGE', user_id=user_id)}:</b> {settings.get('delivery_charge', 0)} {settings.get('currency', 'ILS')}\n"
                text += f"💰 <b>{i18n.get_text('ADMIN_CURRENCY', user_id=user_id)}:</b> {settings.get('currency', 'ILS')}\n"
                text += f"🏢 <b>{i18n.get_text('BUSINESS_TYPE', user_id=user_id)}:</b> Restaurant\n"
                
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_EDIT_BUSINESS_SETTINGS", user_id=user_id),
                            callback_data="admin_edit_business_settings"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            i18n.get_text("LANGUAGE_BUTTON", user_id=user_id), 
                            callback_data="admin_language_selection"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_DASHBOARD", user_id=user_id),
                            callback_data="admin_dashboard"
                        )
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await query.edit_message_text(
                    i18n.get_text("ADMIN_BUSINESS_SETTINGS_ERROR", user_id=user_id).format(error=result["error"])
                )
                
        except Exception as e:
            self.logger.error("Error showing business settings: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _start_edit_business_settings(self, query: CallbackQuery) -> None:
        """Start editing business settings"""
        try:
            user_id = query.from_user.id
            
            text = i18n.get_text("ADMIN_EDIT_BUSINESS_SETTINGS_TITLE", user_id=user_id)
            text += "\n\n"
            text += i18n.get_text("ADMIN_EDIT_BUSINESS_SETTINGS_INSTRUCTIONS", user_id=user_id)
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_BUSINESS_NAME", user_id=user_id),
                        callback_data="admin_edit_business_name"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_BUSINESS_DESCRIPTION", user_id=user_id),
                        callback_data="admin_edit_business_description"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_BUSINESS_ADDRESS", user_id=user_id),
                        callback_data="admin_edit_business_address"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_BUSINESS_PHONE", user_id=user_id),
                        callback_data="admin_edit_business_phone"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_BUSINESS_EMAIL", user_id=user_id),
                        callback_data="admin_edit_business_email"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_BUSINESS_WEBSITE", user_id=user_id),
                        callback_data="admin_edit_business_website"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_BUSINESS_HOURS", user_id=user_id),
                        callback_data="admin_edit_business_hours"
                    ),
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_DELIVERY_CHARGE", user_id=user_id),
                        callback_data="admin_edit_delivery_charge"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_EDIT_CURRENCY", user_id=user_id),
                        callback_data="admin_edit_currency"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.get_text("ADMIN_BACK_TO_BUSINESS_SETTINGS", user_id=user_id),
                        callback_data="admin_business_settings"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error("Error starting business settings edit: %s", e)
            await query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _handle_business_settings_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle business settings field editing"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            
            # Clear any existing conversation state first
            self._clear_business_conversation(user_id)
            
            # Extract field from callback data
            callback_data = query.data
            field = None
            
            # Special case: exclude admin_edit_business_settings
            if callback_data == "admin_edit_business_settings":
                await query.answer(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
                return ConversationHandler.END
            
            if callback_data == "admin_edit_currency":
                field = "currency"
            elif callback_data == "admin_edit_delivery_charge":
                field = "delivery_charge"
            elif callback_data.startswith("admin_edit_business_"):
                # Extract the full field name (e.g., "admin_edit_business_name" -> "business_name")
                field = callback_data.replace("admin_edit_", "")
            
            if not field:
                await query.answer(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
                return ConversationHandler.END
            
            # Get current value from database
            from src.db.operations import get_business_settings
            settings = get_business_settings()
            current_value = ""
            
            if settings:
                current_value = getattr(settings, field, "")
            
            # Store the field being edited
            self.admin_conversations[user_id] = {
                "state": "editing_business_field",
                "field": field,
                "current_value": current_value
            }
            
            field_names = {
                "business_name": i18n.get_text("ADMIN_BUSINESS_NAME", user_id=user_id),
                "business_description": i18n.get_text("ADMIN_BUSINESS_DESCRIPTION", user_id=user_id),
                "business_address": i18n.get_text("ADMIN_BUSINESS_ADDRESS", user_id=user_id),
                "business_phone": i18n.get_text("ADMIN_BUSINESS_PHONE", user_id=user_id),
                "business_email": i18n.get_text("ADMIN_BUSINESS_EMAIL", user_id=user_id),
                "business_website": i18n.get_text("ADMIN_BUSINESS_WEBSITE", user_id=user_id),
                "business_hours": i18n.get_text("ADMIN_BUSINESS_HOURS", user_id=user_id),
                "delivery_charge": i18n.get_text("ADMIN_DEFAULT_DELIVERY_CHARGE", user_id=user_id),
                "currency": i18n.get_text("ADMIN_CURRENCY", user_id=user_id)
            }
            
            field_name = field_names.get(field, field)
            
            text = i18n.get_text("ADMIN_EDIT_BUSINESS_FIELD_PROMPT", user_id=user_id).format(
                field=field_name
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        i18n.get_text("CANCEL", user_id=user_id),
                        callback_data="admin_cancel_business_edit"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            self.logger.info("Started business settings edit for user %d, field: %s", user_id, field)
            return AWAITING_BUSINESS_FIELD_INPUT
            
        except Exception as e:
            self.logger.error("Error handling business settings edit: %s", e)
            if update.callback_query:
                await update.callback_query.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            return ConversationHandler.END

    async def _handle_business_settings_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle business settings input from user"""
        try:
            user_id = update.effective_user.id
            
            if user_id not in self.admin_conversations:
                await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
                return ConversationHandler.END
            
            conversation = self.admin_conversations[user_id]
            field = conversation.get("field")
            value = update.message.text.strip()
            
            # Validate input based on field
            validation_result = self._validate_business_field(field, value, user_id)
            if not validation_result["valid"]:
                await update.message.reply_text(validation_result["error"])
                return AWAITING_BUSINESS_FIELD_INPUT
            
            # Update business settings
            result = await self.admin_service.update_business_settings(**{field: value})
            
            if result["success"]:
                success_text = i18n.get_text("ADMIN_BUSINESS_SETTINGS_UPDATE_SUCCESS", user_id=user_id).format(
                    field=field.replace("_", " ").title(),
                    value=value
                )
                
                keyboard = [
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_CONTINUE_EDITING", user_id=user_id),
                            callback_data="admin_edit_business_settings"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            i18n.get_text("ADMIN_BACK_TO_BUSINESS_SETTINGS", user_id=user_id),
                            callback_data="admin_business_settings"
                        )
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(success_text, parse_mode="HTML", reply_markup=reply_markup)
                
                # Clear conversation state
                self._clear_business_conversation(user_id)
                return ConversationHandler.END
            else:
                await update.message.reply_text(
                    i18n.get_text("ADMIN_BUSINESS_SETTINGS_UPDATE_ERROR", user_id=user_id).format(error=result["error"])
                )
                return AWAITING_BUSINESS_FIELD_INPUT
                
        except Exception as e:
            self.logger.error("Error handling business settings input: %s", e)
            await update.message.reply_text(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))
            self._clear_business_conversation(user_id)
            return ConversationHandler.END

    def _clear_business_conversation(self, user_id: int) -> None:
        """Clear business settings conversation state for a user"""
        if user_id in self.admin_conversations:
            del self.admin_conversations[user_id]
            self.logger.info("Cleared business conversation state for user %d", user_id)

    async def _cancel_business_edit(self, query: CallbackQuery) -> None:
        """Cancel business settings edit and return to business settings"""
        try:
            user_id = query.from_user.id
            await query.answer("✅ Edit cancelled")
            
            # Clear conversation state
            self._clear_business_conversation(user_id)
            
            # Return to business settings view
            await self._show_business_settings(query)
            
        except Exception as e:
            self.logger.error("Error cancelling business edit: %s", e)
            await query.answer(i18n.get_text("ADMIN_ERROR_MESSAGE", user_id=user_id))

    async def _handle_business_conversation_fallback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle business settings conversation fallback - clear state and end conversation"""
        try:
            user_id = update.effective_user.id
            
            # Log the fallback first
            self.logger.info("Business conversation fallback triggered for user %d", user_id)
            
            # Clear conversation state FIRST to prevent re-entry issues
            self._clear_business_conversation(user_id)
            
            # Always answer the callback query first
            if update.callback_query:
                await update.callback_query.answer("✅ Edit cancelled")
                
                callback_data = update.callback_query.data
                
                # If it's the cancel button or business settings callback, show the business settings screen
                if callback_data in ["admin_cancel_business_edit", "admin_business_settings"]:
                    await self._show_business_settings(update.callback_query)
                elif callback_data == "admin_dashboard":
                    await self._show_admin_dashboard_from_callback(update.callback_query)
                else:
                    # For any other callback during fallback, go back to business settings
                    await self._show_business_settings(update.callback_query)
            elif update.message:
                # Handle /cancel command
                await update.message.reply_text(
                    "✅ Business settings edit cancelled",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "🏢 Business Settings", 
                            callback_data="admin_business_settings"
                        )
                    ]])
                )
            
            return ConversationHandler.END
            
        except Exception as e:
            self.logger.error("Error in business conversation fallback: %s", e)
            # Always answer callback query even on error
            if update.callback_query:
                try:
                    await update.callback_query.answer("✅ Edit cancelled")
                except:
                    pass
            return ConversationHandler.END

    def _validate_business_field(self, field: str, value: str, user_id: int) -> dict:
        """Validate business field input"""
        if field == "business_name":
            if len(value) < 2:
                return {
                    "valid": False,
                    "error": i18n.get_text("ADMIN_BUSINESS_NAME_TOO_SHORT", user_id=user_id)
                }
        elif field == "business_description":
            if len(value) < 10:
                return {
                    "valid": False,
                    "error": i18n.get_text("ADMIN_BUSINESS_DESCRIPTION_TOO_SHORT", user_id=user_id)
                }
        elif field == "business_email":
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                return {
                    "valid": False,
                    "error": i18n.get_text("ADMIN_BUSINESS_EMAIL_INVALID", user_id=user_id)
                }
        elif field == "business_phone":
            if len(value) < 7:
                return {
                    "valid": False,
                    "error": i18n.get_text("ADMIN_BUSINESS_PHONE_TOO_SHORT", user_id=user_id)
                }
        elif field == "delivery_charge":
            try:
                charge = float(value)
                if charge < 0:
                    return {
                        "valid": False,
                        "error": i18n.get_text("ADMIN_DELIVERY_CHARGE_NEGATIVE", user_id=user_id)
                    }
            except ValueError:
                return {
                    "valid": False,
                    "error": i18n.get_text("ADMIN_DELIVERY_CHARGE_INVALID", user_id=user_id)
                }
        elif field == "currency":
            if len(value) < 2 or len(value) > 5:
                return {
                    "valid": False,
                    "error": i18n.get_text("ADMIN_CURRENCY_INVALID", user_id=user_id)
                }
        
        return {"valid": True}

    async def _reset_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Reset conversation state and clear user data"""
        try:
            user_id = update.effective_user.id if update.effective_user else None
            
            # Clear conversation data
            if context and hasattr(context, 'user_data'):
                context.user_data.clear()
            
            # Log the reset
            self.logger.info(f"🔄 Conversation reset for user {user_id}")
            
            # Send confirmation message and show appropriate menu
            if update.callback_query:
                # Always answer the callback query first to prevent retries
                await update.callback_query.answer("✅ Conversation cancelled")
                
                # Show the appropriate menu based on the callback data
                data = update.callback_query.data
                try:
                    if data == "admin_menu_management":
                        await self._show_menu_management_dashboard(update.callback_query)
                    elif data == "admin_products_management":
                        await self._show_products_management(update.callback_query)
                    elif data == "admin_category_management":
                        await self._show_category_management(update.callback_query)
                    elif data == "admin_dashboard":
                        await self._show_admin_dashboard_from_callback(update.callback_query)
                    else:
                        # Default fallback to admin dashboard
                        await self._show_admin_dashboard_from_callback(update.callback_query)
                except Exception as menu_error:
                    self.logger.error(f"Error showing menu after conversation reset: {menu_error}")
                    # If menu showing fails, at least we answered the callback
            elif update.message:
                await update.message.reply_text("✅ Conversation cancelled")
            
            return ConversationHandler.END
            
        except Exception as e:
            self.logger.error(f"Error resetting conversation: {e}")
            # Even if there's an error, try to answer the callback query to prevent retries
            if update.callback_query:
                try:
                    await update.callback_query.answer("✅ Conversation reset")
                except:
                    pass
            return ConversationHandler.END


    async def _handle_conversation_timeout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle conversation timeout by clearing state and returning to dashboard"""
        try:
            user_id = update.effective_user.id if update.effective_user else None
            if context and hasattr(context, 'user_data'):
                context.user_data.clear()
            self.logger.info(f"⏰ Conversation timed out for user {user_id}")
            # Try to gracefully inform and show a safe screen
            if update.callback_query:
                try:
                    await update.callback_query.answer("⏰ Timed out")
                except Exception:
                    pass
                try:
                    await self._show_admin_dashboard_from_callback(update.callback_query)
                except Exception:
                    pass
            elif update.message:
                try:
                    await update.message.reply_text("⏰ Session timed out. Returning to admin dashboard…")
                except Exception:
                    pass
            return ConversationHandler.END
        except Exception as e:
            self.logger.error(f"Error handling conversation timeout: {e}")
            return ConversationHandler.END


def register_admin_handlers(application: Application):
    """Register admin handlers"""
    handler = AdminHandler()

    # Admin command handler
    application.add_handler(CommandHandler("admin", handler.handle_admin_command))
    
    # Emergency conversation reset command
    application.add_handler(CommandHandler("reset", handler._reset_conversation))

    # (Moved) Admin callback handler is registered AFTER all conversation handlers below

    # Admin conversation handler for status updates
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handler._start_status_update, pattern="^admin_update_status$")
        ],
        states={
            AWAITING_ORDER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler.show_order_details_for_status_update)
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, handler._handle_conversation_timeout)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handler._reset_conversation),
            MessageHandler(filters.COMMAND, handler._reset_conversation),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_"),
            ],
        per_message=False,
        per_chat=False,
        per_user=True,
        allow_reentry=True,
        conversation_timeout=180,
    )

    application.add_handler(conv_handler)

    # Admin conversation handler for adding products (multilingual step-by-step)
    add_product_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handler._start_add_product, pattern="^admin_add_product$")
        ],
        states={
            AWAITING_PRODUCT_NAME_EN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_product_name_en_input)
            ],
            AWAITING_PRODUCT_NAME_HE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_product_name_he_input),
                CallbackQueryHandler(handler._handle_skip_hebrew_name, pattern="^admin_skip_hebrew_name$")
            ],
            AWAITING_PRODUCT_DESCRIPTION_EN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_product_description_en_input)
            ],
            AWAITING_PRODUCT_DESCRIPTION_HE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_product_description_he_input),
                CallbackQueryHandler(handler._handle_skip_hebrew_description, pattern="^admin_skip_hebrew_description$")
            ],
            AWAITING_PRODUCT_IMAGE_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_product_image_url_input),
                CallbackQueryHandler(handler._handle_skip_image_url, pattern="^admin_skip_image_url$")
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
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, handler._handle_conversation_timeout)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handler._reset_conversation),
            MessageHandler(filters.COMMAND, handler._reset_conversation),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_dashboard$"),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_back$"),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_products_management$"),
            CallbackQueryHandler(handler._start_add_product, pattern="^admin_add_product$"),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_"),
        ],
        name="add_product_conversation",
        persistent=False,
        per_message=False,
        per_chat=False,
        per_user=True,
        allow_reentry=True,
        conversation_timeout=300,
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
            AWAITING_CATEGORY_NAME_EN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_category_name_en_input)
            ],
            AWAITING_CATEGORY_NAME_HE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_category_name_he_input),
                CallbackQueryHandler(handler._handle_skip_hebrew_category_name, pattern="^admin_skip_hebrew_category_name$")
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, handler._handle_conversation_timeout)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handler._reset_conversation),
            MessageHandler(filters.COMMAND, handler._reset_conversation),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_dashboard$"),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_back$"),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_"),
        ],
        name="add_category_conversation",
        persistent=False,
        per_message=False,
        per_chat=False,
        per_user=True,
        allow_reentry=True,
        conversation_timeout=300,
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
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, handler._handle_conversation_timeout)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handler._reset_conversation),
            MessageHandler(filters.COMMAND, handler._reset_conversation),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_dashboard$"),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_back$"),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_"),
        ],
        name="edit_category_conversation",
        persistent=False,
        per_message=False,
        per_chat=False,
        per_user=True,
        allow_reentry=True,
        conversation_timeout=300,
    )

    application.add_handler(edit_category_handler)

    # Admin conversation handler for editing products (wizard)
    edit_product_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handler._start_edit_product, pattern="^admin_product_edit_")
        ],
        states={
            AWAITING_PRODUCT_EDIT_FIELD: [
                CallbackQueryHandler(handler._handle_edit_product_field_selection, pattern="^admin_edit_product_field_")
            ],
            AWAITING_PRODUCT_EDIT_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_edit_product_value_input),
                CallbackQueryHandler(handler._handle_category_selection_for_edit, pattern="^admin_edit_product_category_")
            ],
            AWAITING_PRODUCT_EDIT_CONFIRM: [
                CallbackQueryHandler(handler._handle_edit_confirmation, pattern="^admin_edit_product_confirm_")
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, handler._handle_conversation_timeout)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handler._reset_conversation),
            MessageHandler(filters.COMMAND, handler._reset_conversation),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_product_back_to_list$"),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_edit_product_cancel$"),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_"),
        ],
        name="edit_product_conversation",
        persistent=False,
        per_message=False,
        per_chat=False,
        per_user=True,
        allow_reentry=True,
        conversation_timeout=300,
    )

    # Add debug logging to the conversation handler
    handler.logger.info("🔧 Registering edit_product_conversation handler")
    application.add_handler(edit_product_handler)
    handler.logger.info("✅ edit_product_conversation handler registered successfully")

    # Admin conversation handler for business settings
    business_settings_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                handler._handle_business_settings_edit,
                pattern="^(admin_edit_business_name|admin_edit_business_description|admin_edit_business_address|admin_edit_business_phone|admin_edit_business_email|admin_edit_business_website|admin_edit_business_hours|admin_edit_currency|admin_edit_delivery_charge)$"
            )
        ],
        states={
            AWAITING_BUSINESS_FIELD_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_business_settings_input)
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, handler._handle_conversation_timeout)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handler._handle_business_conversation_fallback),
            CallbackQueryHandler(handler._handle_business_conversation_fallback, pattern="^admin_cancel_business_edit$"),
            CallbackQueryHandler(handler._handle_business_conversation_fallback, pattern="^admin_business_settings$"),
            CallbackQueryHandler(handler._handle_business_conversation_fallback, pattern="^admin_dashboard$"),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_")
        ],
        name="business_settings_conversation",
        persistent=False,
        per_message=False,
        per_chat=False,
        per_user=True,
        allow_reentry=True,
        conversation_timeout=300,
    )

    # Add debug logging to the conversation handler
    handler.logger.info("🔧 Registering business_settings_conversation handler")
    application.add_handler(business_settings_handler)
    # Delivery area creation wizard
    add_delivery_area_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handler._start_add_delivery_area, pattern="^admin_add_delivery_area$")
        ],
        states={
            AWAITING_DELIVERY_AREA_NAME_EN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_delivery_area_name_en)
            ],
            AWAITING_DELIVERY_AREA_NAME_HE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_delivery_area_name_he)
            ],
            AWAITING_DELIVERY_AREA_CHARGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler._handle_delivery_area_charge)
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, handler._handle_conversation_timeout)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handler._reset_conversation),
            MessageHandler(filters.COMMAND, handler._reset_conversation),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_deliveries$"),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_dashboard$"),
            CallbackQueryHandler(handler._reset_conversation, pattern="^admin_")
        ],
        name="add_delivery_area_conversation",
        persistent=False,
        per_message=False,
        per_chat=False,
        per_user=True,
        allow_reentry=True,
        conversation_timeout=300,
    )
    application.add_handler(add_delivery_area_handler)
    handler.logger.info("✅ add_delivery_area_conversation handler registered successfully")
    # Finally, register the general admin callback handler so conversation patterns take precedence
    application.add_handler(
        CallbackQueryHandler(
            handler.handle_admin_callback,
            pattern="^admin_(?!add_product$|add_product_category_|add_product_confirm_|add_category$|edit_category_name_|edit_product_field_|edit_product_confirm_|edit_product_category_|product_edit_|edit_business_name$|edit_business_description$|edit_business_address$|edit_business_phone$|edit_business_email$|edit_business_website$|edit_business_hours$|edit_currency$|edit_delivery_charge$|cancel_business_edit$|skip_hebrew_name$|skip_hebrew_description$|skip_image_url$|skip_hebrew_category_name$)"
        )
    )
    handler.logger.info("✅ business_settings_conversation handler registered successfully")

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
