"""
Menu keyboards for the Samna Salta bot
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.utils.helpers import is_hilbeh_available
from src.utils.i18n import i18n
from src.keyboards.order_keyboards import get_delivery_method_keyboard


def get_main_menu_keyboard(lang: str | None = None):
    """Get main menu keyboard (translated)."""
    keyboard = [
        [
            InlineKeyboardButton(i18n.get_text("BUTTON_KUBANEH", lang), callback_data="menu_kubaneh"),
            InlineKeyboardButton(i18n.get_text("BUTTON_SAMNEH", lang), callback_data="menu_samneh"),
        ],
        [
            InlineKeyboardButton(i18n.get_text("BUTTON_RED_BISBAS", lang), callback_data="menu_red_bisbas"),
            InlineKeyboardButton(i18n.get_text("BUTTON_HAWAIIJ_SOUP", lang), callback_data="menu_hawaij_soup"),
        ],
        [
            InlineKeyboardButton(i18n.get_text("BUTTON_HAWAIIJ_COFFEE", lang), callback_data="menu_hawaij_coffee"),
            InlineKeyboardButton(i18n.get_text("BUTTON_WHITE_COFFEE", lang), callback_data="menu_white_coffee"),
        ],
        [InlineKeyboardButton(i18n.get_text("BUTTON_HILBEH", lang), callback_data="menu_hilbeh")],
        [InlineKeyboardButton(i18n.get_text("BUTTON_VIEW_CART", lang), callback_data="cart_view")],
    ]

    keyboard.append([InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="menu_main")])

    return InlineKeyboardMarkup(keyboard)


def get_kubaneh_menu_keyboard():
    """Get Kubaneh sub-menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(i18n.get_text("KUBANEH_CLASSIC"), callback_data="kubaneh_classic"),
            InlineKeyboardButton(i18n.get_text("KUBANEH_SEEDED"), callback_data="kubaneh_seeded"),
        ],
        [
            InlineKeyboardButton(i18n.get_text("KUBANEH_HERB"), callback_data="kubaneh_herb"),
            InlineKeyboardButton(i18n.get_text("KUBANEH_AROMATIC"), callback_data="kubaneh_aromatic"),
        ],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_kubaneh_oil_keyboard(kubaneh_type: str):
    """Get Kubaneh oil selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                i18n.get_text("OIL_OLIVE"), callback_data=f"kubaneh_{kubaneh_type}_olive_oil"
            ),
            InlineKeyboardButton(
                i18n.get_text("OIL_SAMNEH"), callback_data=f"kubaneh_{kubaneh_type}_samneh"
            ),
        ],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="menu_kubaneh")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_samneh_menu_keyboard():
    """Get Samneh sub-menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(i18n.get_text("SAMNEH_SMOKED"), callback_data="samneh_smoked"),
            InlineKeyboardButton(i18n.get_text("SAMNEH_NOT_SMOKED"), callback_data="samneh_not_smoked"),
        ],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_samneh_size_keyboard(smoking_type: str):
    """Get Samneh size selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(i18n.get_text("SIZE_SMALL"), callback_data=f"samneh_{smoking_type}_small"),
            InlineKeyboardButton(i18n.get_text("SIZE_LARGE"), callback_data=f"samneh_{smoking_type}_large"),
        ],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="menu_samneh")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_red_bisbas_menu_keyboard():
    """Get Red Bisbas menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(i18n.get_text("SIZE_SMALL"), callback_data="red_bisbas_small"),
            InlineKeyboardButton(i18n.get_text("SIZE_LARGE"), callback_data="red_bisbas_large"),
        ],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_direct_add_keyboard(product_name: str, include_info: bool = True):
    """Get direct add-to-cart keyboard."""
    add_button = InlineKeyboardButton(
        i18n.get_text("ADD_TO_CART"),
        callback_data=f"add_{product_name.lower().replace(' ', '_')}",
    )

    rows = [[add_button]]

    if include_info:
        info_button = InlineKeyboardButton(
            i18n.get_text("INFO"),
            callback_data=f"info_{product_name.lower().replace(' ', '_')}",
        )
        rows.append([info_button])

    rows.append([InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="menu_main")])

    return InlineKeyboardMarkup(rows)


def get_hilbeh_menu_keyboard():
    """Get Hilbeh menu keyboard (with availability check)"""
    if is_hilbeh_available():
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("ADD_TO_CART"), callback_data="add_hilbeh")],
            [InlineKeyboardButton(i18n.get_text("INFO"), callback_data="info_hilbeh")],
            [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="menu_main")],
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton(
                    i18n.get_text("HILBEH_UNAVAILABLE"),
                    callback_data="hilbeh_unavailable",
                )
            ],
            [InlineKeyboardButton(i18n.get_text("INFO"), callback_data="info_hilbeh")],
            [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_cart_keyboard():
    """Get cart view keyboard"""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("CHANGE_DELIVERY"), callback_data="cart_change_delivery")],
        [InlineKeyboardButton(i18n.get_text("SEND_ORDER"), callback_data="cart_send_order")],
        [
            InlineKeyboardButton(i18n.get_text("CLEAR_CART"), callback_data="cart_clear_confirm"),
            InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="menu_main"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_cart_delivery_method_keyboard():
    """Get delivery method selection keyboard for cart"""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("DELIVERY_PICKUP"), callback_data="cart_delivery_pickup")],
        [InlineKeyboardButton(i18n.get_text("DELIVERY_DELIVERY"), callback_data="cart_delivery_delivery")],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="cart_view")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_clear_cart_confirmation_keyboard():
    """Get clear cart confirmation keyboard"""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("CLEAR_CART_YES"), callback_data="cart_clear_yes")],
        [InlineKeyboardButton(i18n.get_text("CLEAR_CART_NO"), callback_data="cart_view")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_back_to_cart_keyboard():
    """Get back to cart keyboard"""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("BACK_TO_CART"), callback_data="cart_view")],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU"), callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)
