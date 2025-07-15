"""
Unified notification service for admin and customer notifications.
"""

import logging
from typing import Dict, List, Optional

from src.config import get_config

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
            if order_id:
                message = f"🆕 New Order #{order_id}\n\n{message}"
            
            # In a real implementation, this would use the Telegram API
            logger.info("Admin notification: %s", message)
            return True
        except Exception as e:
            logger.error("Failed to send admin notification: %s", e)
            return False

    async def send_customer_notification(self, chat_id: int, message: str) -> bool:
        """Send notification to customer"""
        try:
            # In a real implementation, this would use the Telegram API
            logger.info("Customer notification to %d: %s", chat_id, message)
            return True
        except Exception as e:
            logger.error("Failed to send customer notification: %s", e)
            return False

    async def notify_new_order(self, order_data: Dict) -> bool:
        """Notify admin about new order"""
        message = self._format_order_notification(order_data)
        return await self.send_admin_notification(message, order_data.get("id"))

    async def notify_order_status_update(self, order_id: int, new_status: str, customer_chat_id: int) -> bool:
        """Notify customer about order status update"""
        message = f"Your order #{order_id} status has been updated to: {new_status}"
        return await self.send_customer_notification(customer_chat_id, message)

    def _format_order_notification(self, order_data: Dict) -> str:
        """Format order data for notification"""
        return f"""
📦 New Order Details:
Customer: {order_data.get('customer_name', 'Unknown')}
Items: {len(order_data.get('items', []))} items
Total: {order_data.get('total', 0):.2f} ILS
Delivery: {order_data.get('delivery_method', 'Unknown')}
        """.strip()

# Global instance
notification_service = NotificationService() 