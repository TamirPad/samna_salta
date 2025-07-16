"""
Language selection keyboards for the Samna Salta bot
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.utils.i18n import i18n


def get_language_selection_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    """Get language selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                i18n.get_text("LANGUAGE_ENGLISH", user_id=user_id),
                callback_data="language_en"
            ),
            InlineKeyboardButton(
                i18n.get_text("LANGUAGE_HEBREW", user_id=user_id),
                callback_data="language_he"
            ),
        ],
        [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="main_page")],
    ]
    
    return InlineKeyboardMarkup(keyboard)


def get_back_to_info_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    """Get back to main page keyboard"""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="main_page")],
    ]
    
    return InlineKeyboardMarkup(keyboard) 