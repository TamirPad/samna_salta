"""
Customer Notification Service

Handles sending notifications to customers about order status updates.
"""

import logging
from typing import Dict, Any, Optional
from telegram import Bot
from telegram.error import TelegramError

from ...application.dtos.order_dtos import OrderInfo
from ...domain.repositories.customer_repository import CustomerRepository


class CustomerNotificationService:
    """Service for sending notifications to customers"""
    
    def __init__(self, bot: Bot, customer_repository: CustomerRepository):
        self._bot = bot
        self._customer_repository = customer_repository
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def notify_order_status_update(self, order_info: OrderInfo, old_status: str) -> None:
        """Send order status update notification to customer"""
        self._logger.info(f"📨 SENDING CUSTOMER NOTIFICATION: Order #{order_info.order_number}")
        
        try:
            # Get customer by phone to find telegram ID
            customer = await self._get_customer_by_phone(order_info.customer_phone)
            if not customer:
                self._logger.warning(f"⚠️ CUSTOMER NOT FOUND: Phone {order_info.customer_phone}")
                return
            
            # Create notification message
            message = self._format_status_update_message(order_info, old_status)
            
            # Send to customer
            try:
                await self._bot.send_message(
                    chat_id=customer.telegram_id.value,
                    text=message,
                    parse_mode='HTML'
                )
                self._logger.info(f"✅ CUSTOMER NOTIFICATION SENT: {customer.telegram_id.value}")
            except TelegramError as e:
                self._logger.error(f"❌ CUSTOMER NOTIFICATION FAILED: {customer.telegram_id.value}, Error: {e}")
                    
        except Exception as e:
            self._logger.error(f"💥 CUSTOMER NOTIFICATION ERROR: {e}", exc_info=True)
    
    async def notify_order_ready_for_pickup(self, order_info: OrderInfo) -> None:
        """Send special notification when order is ready for pickup"""
        self._logger.info(f"📦 SENDING PICKUP NOTIFICATION: Order #{order_info.order_number}")
        
        try:
            customer = await self._get_customer_by_phone(order_info.customer_phone)
            if not customer:
                return
            
            message = self._format_pickup_ready_message(order_info)
            
            try:
                await self._bot.send_message(
                    chat_id=customer.telegram_id.value,
                    text=message,
                    parse_mode='HTML'
                )
                self._logger.info(f"✅ PICKUP NOTIFICATION SENT: {customer.telegram_id.value}")
            except TelegramError as e:
                self._logger.error(f"❌ PICKUP NOTIFICATION FAILED: {customer.telegram_id.value}, Error: {e}")
                
        except Exception as e:
            self._logger.error(f"💥 PICKUP NOTIFICATION ERROR: {e}", exc_info=True)
    
    async def _get_customer_by_phone(self, phone_number: str):
        """Get customer by phone number"""
        try:
            # This is a simplified approach - in a real system you'd have a proper lookup
            customers = await self._customer_repository.get_all_customers()
            for customer in customers:
                if customer.phone_number.value == phone_number:
                    return customer
            return None
            
        except Exception as e:
            self._logger.error(f"💥 CUSTOMER LOOKUP ERROR: {e}")
            return None
    
    def _format_status_update_message(self, order_info: OrderInfo, old_status: str) -> str:
        """Format order status update message for customer"""
        status_emoji = {
            'pending': '⏳',
            'confirmed': '✅',
            'preparing': '👨‍🍳',
            'ready': '🛍️',
            'completed': '✅',
            'cancelled': '❌'
        }
        
        status_messages = {
            'confirmed': '✅ Your order has been confirmed! We\'re preparing it now.',
            'preparing': '👨‍🍳 Your order is being prepared with love!',
            'ready': '🛍️ Your order is ready! Please come pick it up.',
            'completed': '✅ Thank you! Your order has been completed.',
            'cancelled': '❌ Your order has been cancelled. Please contact us if you have questions.'
        }
        
        delivery_emoji = '🚚' if order_info.delivery_method == 'delivery' else '🏪'
        
        message = f"""
🔔 <b>ORDER UPDATE</b>

📋 Order #: <code>{order_info.order_number}</code>
{status_emoji.get(order_info.status, '📋')} <b>{status_messages.get(order_info.status, f'Status updated to: {order_info.status.title()}')}</b>

🛒 <b>Your Items:</b>"""

        for item in order_info.items:
            options_text = ""
            if item.options:
                options_list = [f"{k}: {v}" for k, v in item.options.items()]
                options_text = f" ({', '.join(options_list)})"
            
            message += f"\n• {item.quantity}x {item.product_name}{options_text}"

        message += f"""

{delivery_emoji} <b>Delivery:</b> {order_info.delivery_method.title()}"""

        if order_info.delivery_address:
            message += f"\n📍 Address: {order_info.delivery_address}"

        message += f"""
💳 <b>Total:</b> ₪{order_info.total:.2f}

Thank you for choosing Samna Salta! 🥧✨
"""
        
        # Add specific instructions based on status
        if order_info.status == 'ready' and order_info.delivery_method == 'pickup':
            message += "\n🏪 <b>Please come to pick up your order at your convenience!</b>"
        elif order_info.status == 'ready' and order_info.delivery_method == 'delivery':
            message += "\n🚚 <b>Your order will be delivered shortly!</b>"
        
        return message
    
    def _format_pickup_ready_message(self, order_info: OrderInfo) -> str:
        """Format special pickup ready message"""
        message = f"""
🎉 <b>YOUR ORDER IS READY!</b>

📋 Order #: <code>{order_info.order_number}</code>
🛍️ Status: <b>Ready for Pickup</b>

🏪 <b>Pickup Details:</b>
📅 Available: Now
📍 Location: [Your Store Address]
⏰ Hours: [Your Store Hours]

🛒 <b>Your Items:</b>"""

        for item in order_info.items:
            options_text = ""
            if item.options:
                options_list = [f"{k}: {v}" for k, v in item.options.items()]
                options_text = f" ({', '.join(options_list)})"
            
            message += f"\n• {item.quantity}x {item.product_name}{options_text}"

        message += f"""

💳 <b>Total:</b> ₪{order_info.total:.2f}

Please bring this message when picking up your order! 🥧✨
"""
        return message 