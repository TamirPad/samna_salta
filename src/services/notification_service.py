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
        return await self.send_admin_notification(message, order_data.get("id"))

    async def notify_order_status_update(self, order_id: str, new_status: str, customer_chat_id: int, delivery_method: str = "pickup") -> bool:
        """Notify customer about order status update"""
        # Create user-friendly status messages using i18n
        status_messages = {
            "confirmed": i18n.get_text("ORDER_STATUS_CONFIRMED"),
            "preparing": i18n.get_text("ORDER_STATUS_PREPARING"),
            "ready": i18n.get_text("ORDER_STATUS_READY"),
            "delivered": i18n.get_text("ORDER_STATUS_DELIVERED"),
            "cancelled": i18n.get_text("ORDER_STATUS_CANCELLED")
        }
        
        # Get the appropriate message for the status
        message = status_messages.get(new_status.lower(), i18n.get_text("ORDER_STATUS_UNKNOWN").format(status=new_status))
        
        # Add delivery-specific information for ready orders
        if new_status.lower() == "ready":
            if delivery_method.lower() == "delivery":
                message += "\n\n" + i18n.get_text("DELIVERY_READY_INFO")
            else:
                message += "\n\n" + i18n.get_text("PICKUP_READY_INFO")
        
        # Add order number to the message
        full_message = f"{i18n.get_text('CUSTOMER_ORDER_UPDATE_HEADER')}\n\n📋 **{i18n.get_text('ORDER_NUMBER_LABEL')} #{order_id}**\n\n{message}"
        
        return await self.send_customer_notification(customer_chat_id, full_message)

    def _format_order_notification(self, order_data: Dict) -> str:
        """Format order data for notification"""
        items_text = ""
        for i, item in enumerate(order_data.get('items', []), 1):
            item_total = item.get("price", 0) * item.get("quantity", 1)
            items_text += f"{i}. {item.get('product_name', 'Unknown')} x{item.get('quantity', 1)} - ₪{item_total:.2f}\n"
        
        # Format delivery info
        delivery_method = order_data.get('delivery_method', 'Unknown').title()
        delivery_info = f"🚚 <b>Delivery:</b> {delivery_method}"
        
        # Add delivery address if it's delivery
        if order_data.get('delivery_method') == 'delivery' and order_data.get('delivery_address'):
            delivery_info += f"\n📍 <b>Address:</b> {order_data.get('delivery_address')}"
        
        return f"""
🆕 <b>NEW ORDER RECEIVED!</b>

📋 <b>Order #{order_data.get('order_number', 'Unknown')}</b>
👤 <b>Customer:</b> {order_data.get('customer_name', 'Unknown')}
📞 <b>Phone:</b> {order_data.get('customer_phone', 'Unknown')}
{delivery_info}

📦 <b>Items:</b>
{items_text}
💰 <b>Total:</b> ₪{order_data.get('total', 0):.2f}

<i>Order placed at {order_data.get('created_at', 'Unknown time')}</i>
        """.strip()

# Global instance
notification_service = NotificationService() 