"""
Unified notification service for admin and customer notifications.
"""

import logging
from typing import Dict, List, Optional

from src.config import get_config
from src.utils.i18n import i18n

logger = logging.getLogger(__name__)

class NotificationService:
    """Unified service for handling all notifications"""

    def __init__(self):
        self.config = get_config()
        self.admin_chat_id = self.config.admin_chat_id
        self.bot_token = self.config.bot_token

    async def send_admin_notification(self, message: str, order_id: Optional[int] = None) -> bool:
        """Send notification to admin"""
        try:
            if not self.admin_chat_id:
                logger.warning("Admin chat ID not configured, skipping admin notification")
                return False
                
            if order_id:
                message = f"🆕 New Order #{order_id}\n\n{message}"
            
            # Get bot instance from container
            from src.container import get_container
            container = get_container()
            bot = container.get_bot()
            
            if bot:
                await bot.send_message(
                    chat_id=self.admin_chat_id,
                    text=message,
                    parse_mode="HTML"
                )
                logger.info("Admin notification sent to %s", self.admin_chat_id)
                return True
            else:
                logger.error("Bot instance not available for admin notification")
                return False
                
        except Exception as e:
            logger.error("Failed to send admin notification: %s", e)
            return False

    async def send_customer_notification(self, chat_id: int, message: str) -> bool:
        """Send notification to customer"""
        try:
            # Get bot instance from container
            from src.container import get_container
            container = get_container()
            bot = container.get_bot()
            
            if bot:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML"
                )
                logger.info("Customer notification sent to %d", chat_id)
                return True
            else:
                logger.error("Bot instance not available for customer notification")
                return False
                
        except Exception as e:
            logger.error("Failed to send customer notification: %s", e)
            return False

    async def notify_new_order(self, order_data: Dict) -> bool:
        """Notify admin about new order"""
        message = self._format_order_notification(order_data)
        return await self.send_admin_notification(message)

    async def notify_order_status_update(self, order_id: str, new_status: str, customer_chat_id: int, delivery_method: str = "pickup") -> bool:
        """Notify customer about order status update"""
        # Create user-friendly status messages using i18n with customer's language
        status_messages = {
            "confirmed": i18n.get_text("ORDER_STATUS_CONFIRMED", user_id=customer_chat_id) + "\n\n" + i18n.get_text("ORDER_STATUS_CONFIRMED_FOLLOWUP", user_id=customer_chat_id),
            "preparing": i18n.get_text("ORDER_STATUS_PREPARING", user_id=customer_chat_id),
            "missing": i18n.get_text("ORDER_STATUS_MISSING_ITEMS", user_id=customer_chat_id),
            "ready": i18n.get_text("ORDER_STATUS_READY", user_id=customer_chat_id),
            "delivered": i18n.get_text("ORDER_STATUS_DELIVERED", user_id=customer_chat_id),
            "cancelled": i18n.get_text("ORDER_STATUS_CANCELLED", user_id=customer_chat_id)
        }
        
        # Get the appropriate message for the status
        message = status_messages.get(new_status.lower(), i18n.get_text("ORDER_STATUS_UNKNOWN", user_id=customer_chat_id).format(status=new_status))
        # Clarify that "missing" means order continues, items need replacement/adjustment
        if new_status.lower() == "missing":
            message += "\n\n" + i18n.get_text("ORDER_STATUS_MISSING_ITEMS", user_id=customer_chat_id)
        
        # Add delivery-specific information for ready orders
        if new_status.lower() == "ready":
            if delivery_method.lower() == "delivery":
                message += "\n\n" + i18n.get_text("DELIVERY_READY_INFO", user_id=customer_chat_id)
            else:
                message += "\n\n" + i18n.get_text("PICKUP_READY_INFO", user_id=customer_chat_id)
        
        # Always display database order id (not the human-readable number)
        full_message = f"{i18n.get_text('CUSTOMER_ORDER_UPDATE_HEADER', user_id=customer_chat_id)}\n\n📋 <b>{i18n.get_text('ORDER_ID_LABEL', user_id=customer_chat_id)} #{order_id}</b>\n\n{message}"
        
        return await self.send_customer_notification(customer_chat_id, full_message)

    def _format_order_notification(self, order_data: Dict) -> str:
        """Format order data for notification"""
        # Get user_id for translations (admin notifications are always in English)
        user_id = order_data.get('customer_telegram_id')
        
        items_text = ""
        items = order_data.get('items', []) or []
        for i, item in enumerate(items, 1):
            item_total = item.get("unit_price", 0) * item.get("quantity", 1)
            
            # Use the new localization system
            from src.utils.language_manager import language_manager
            from src.db.operations import get_product_by_id, get_localized_name
            
            # Get localized product name
            product_id = item.get('product_id')
            if product_id:
                product = get_product_by_id(product_id)
                if product:
                    user_language = language_manager.get_user_language(user_id) if user_id else "en"
                    localized_product_name = get_localized_name(product, user_language)
                else:
                    localized_product_name = item.get('product_name', 'Unknown')
            else:
                # Fallback to old translation system for legacy data
                from src.utils.helpers import translate_product_name
                localized_product_name = translate_product_name(item.get('product_name', 'Unknown'), item.get('options', {}), user_id)
            
            items_text += f"{i}. {localized_product_name} x{item.get('quantity', 1)} - 💰 ₪{item_total:.2f}\n"

        # Add delivery as a line item for admin if applicable
        try:
            delivery_method = (order_data.get('delivery_method') or '').lower()
            delivery_charge = float(order_data.get('delivery_charge') or 0)
        except Exception:
            delivery_method = (order_data.get('delivery_method') or '').lower()
            delivery_charge = 0.0

        if delivery_method == 'delivery' and delivery_charge > 0:
            next_index = len(items) + 1
            items_text += f"{next_index}. {i18n.get_text('DELIVERY_ITEM_NAME', user_id=user_id)} x1 - 💰 ₪{delivery_charge:.2f}\n"
        
        # Format delivery info
        delivery_method = order_data.get('delivery_method', 'Unknown').title()
        delivery_info = i18n.get_text("ADMIN_DELIVERY_INFO", user_id=user_id).format(delivery_method=delivery_method)
        
        # Add delivery address if it's delivery
        if order_data.get('delivery_method') == 'delivery' and order_data.get('delivery_address'):
            delivery_info += f"\n{i18n.get_text('ADMIN_DELIVERY_ADDRESS', user_id=user_id).format(address=order_data.get('delivery_address'))}"
        
        return f"""
{i18n.get_text("ADMIN_NEW_ORDER_TITLE", user_id=user_id)}

{i18n.get_text("ADMIN_ORDER_NUMBER", user_id=user_id).format(order_number=order_data.get('order_id', order_data.get('order_number', 'Unknown')))}
{i18n.get_text("ADMIN_CUSTOMER_INFO", user_id=user_id).format(customer_name=order_data.get('customer_name', 'Unknown'), customer_phone=order_data.get('customer_phone', 'Unknown'))}
{delivery_info}

{i18n.get_text("ADMIN_ITEMS_HEADER", user_id=user_id)}
{items_text}{i18n.get_text("ADMIN_ORDER_TOTAL", user_id=user_id).format(total=order_data.get('total', 0))}

{i18n.get_text("ADMIN_ORDER_TIME", user_id=user_id).format(created_at=order_data.get('created_at', 'Unknown time'))}
        """.strip()

# Global instance
notification_service = NotificationService() 