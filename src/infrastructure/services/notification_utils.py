"""
Notification Utilities

Shared functions for sending notifications to admins and customers.
"""

import logging

from telegram import Bot
from telegram.error import TelegramError

from src.application.dtos.order_dtos import OrderInfo, OrderItemInfo

STATUS_EMOJI = {
    "pending": "⏳",
    "confirmed": "✅",
    "preparing": "👨‍🍳",
    "ready": "🛍️",
    "completed": "✅",
    "cancelled": "❌",
}


def format_item_options(item: OrderItemInfo) -> str:
    """Formats the options for a single order item into a string."""
    if not item.options:
        return ""
    options_str = ", ".join(
        f"{key.replace('_', ' ').title()}: {value}"
        for key, value in item.options.items()
    )
    return f" ({options_str})"


def format_order_details(order_info: OrderInfo, header: str) -> str:
    """Formats the details of an order into a string."""
    delivery_emoji = "🚚" if order_info.delivery_method == "delivery" else "🏪"
    status_emoji = STATUS_EMOJI.get(order_info.status, "📋")

    message = f"""
{header}

📋 <b>Order Details:</b>
🔢 Order #: <code>{order_info.order_number}</code>
{status_emoji} Status: <b>{order_info.status.title()}</b>
📅 Date: {(order_info.created_at or __import__('datetime').datetime.utcnow()).strftime('%d/%m/%Y %H:%M')}

👤 <b>Customer Info:</b>
👨‍💼 Name: <b>{order_info.customer_name}</b>
📞 Phone: <code>{order_info.customer_phone}</code>

🛒 <b>Items:</b>"""

    for item in order_info.items:
        options_text = format_item_options(item)
        price = f" - ₪{item.total_price:.2f}"
        message += f"\n• {item.quantity}x {item.product_name}{options_text}{price}"

    message += f"""

{delivery_emoji} <b>Delivery:</b> {order_info.delivery_method.title()}"""

    if order_info.delivery_address:
        message += f"\n📍 Address: {order_info.delivery_address}"

    message += f"""

💳 <b>Total:</b> ₪{order_info.total:.2f}
"""
    return message


async def send_telegram_message(
    bot: Bot, chat_id: int, text: str, logger: logging.Logger
) -> None:
    """Sends a message using the Telegram bot."""
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        logger.info("✅ Notification sent to %s", chat_id)
    except TelegramError as e:
        logger.error("❌ Notification failed for %s: %s", chat_id, e)
    except Exception as e:
        logger.critical(
            "💥 Unexpected error sending notification to %s: %s",
            chat_id,
            e,
            exc_info=True,
        )
