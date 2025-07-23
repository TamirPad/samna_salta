"""
Order-related keyboards for the Samna Salta bot
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.utils.i18n import i18n
from src.utils.constants_manager import get_delivery_method_name


def get_order_confirmation_keyboard():
    """Get order confirmation keyboard"""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("CONFIRM_ORDER"), callback_data="order_confirm")],
        [InlineKeyboardButton(i18n.get_text("CANCEL_ORDER"), callback_data="order_cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_delivery_method_keyboard(user_id: int = None):
    """Get delivery method selection keyboard"""
    keyboard = [
        [InlineKeyboardButton(get_delivery_method_name("pickup", user_id), callback_data="delivery_pickup")],
        [InlineKeyboardButton(get_delivery_method_name("delivery", user_id), callback_data="delivery_delivery")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_delivery_address_choice_keyboard():
    """Get delivery address choice keyboard"""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("USE_SAVED_ADDRESS"), callback_data="delivery_use_saved")],
        [InlineKeyboardButton(i18n.get_text("ENTER_NEW_ADDRESS"), callback_data="delivery_new_address")],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_delivery_address_required_keyboard():
    """Get delivery address required keyboard"""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("ENTER_DELIVERY_ADDRESS"), callback_data="delivery_enter_address")],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_order_status_keyboard(order_id: int):
    """Get order status keyboard"""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("VIEW_ORDER_STATUS"), callback_data=f"order_status_{order_id}")],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard) 