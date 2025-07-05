"""
Menu keyboards for the Samna Salta bot
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.infrastructure.utilities.helpers import is_hilbeh_available
from src.infrastructure.utilities.i18n import tr


def get_main_menu_keyboard(lang: str | None = None):
    """Get main menu keyboard (translated)."""
    keyboard = [
        [
            InlineKeyboardButton(tr("BUTTON_KUBANEH", lang), callback_data="menu_kubaneh"),
            InlineKeyboardButton(tr("BUTTON_SAMNEH", lang), callback_data="menu_samneh"),
        ],
        [
            InlineKeyboardButton(tr("BUTTON_RED_BISBAS", lang), callback_data="menu_red_bisbas"),
            InlineKeyboardButton(tr("BUTTON_HAWAIIJ_SOUP", lang), callback_data="menu_hawaij_soup"),
        ],
        [
            InlineKeyboardButton(tr("BUTTON_HAWAIIJ_COFFEE", lang), callback_data="menu_hawaij_coffee"),
            InlineKeyboardButton(tr("BUTTON_WHITE_COFFEE", lang), callback_data="menu_white_coffee"),
        ],
        [InlineKeyboardButton(tr("BUTTON_HILBEH", lang), callback_data="menu_hilbeh")],
        [InlineKeyboardButton(tr("BUTTON_VIEW_CART", lang), callback_data="cart_view")],
    ]

    keyboard.append([InlineKeyboardButton(tr("BACK_MAIN_MENU"), callback_data="menu_main")])

    return InlineKeyboardMarkup(keyboard)


def get_kubaneh_menu_keyboard():
    """Get Kubaneh sub-menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(tr("KUBANEH_CLASSIC"), callback_data="kubaneh_classic"),
            InlineKeyboardButton(tr("KUBANEH_SEEDED"), callback_data="kubaneh_seeded"),
        ],
        [
            InlineKeyboardButton(tr("KUBANEH_HERB"), callback_data="kubaneh_herb"),
            InlineKeyboardButton(tr("KUBANEH_AROMATIC"), callback_data="kubaneh_aromatic"),
        ],
        [InlineKeyboardButton(tr("BACK_MAIN_MENU"), callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_kubaneh_oil_keyboard(kubaneh_type: str):
    """Get Kubaneh oil selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                tr("OIL_OLIVE"), callback_data=f"kubaneh_{kubaneh_type}_olive_oil"
            ),
            InlineKeyboardButton(
                tr("OIL_SAMNEH"), callback_data=f"kubaneh_{kubaneh_type}_samneh"
            ),
        ],
        [InlineKeyboardButton(tr("BACK_MAIN_MENU"), callback_data="menu_kubaneh")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_samneh_menu_keyboard():
    """Get Samneh sub-menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(tr("SAMNEH_SMOKED"), callback_data="samneh_smoked"),
            InlineKeyboardButton(tr("SAMNEH_NOT_SMOKED"), callback_data="samneh_not_smoked"),
        ],
        [InlineKeyboardButton(tr("BACK_MAIN_MENU"), callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_samneh_size_keyboard(smoking_type: str):
    """Get Samneh size selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(tr("SIZE_SMALL"), callback_data=f"samneh_{smoking_type}_small"),
            InlineKeyboardButton(tr("SIZE_LARGE"), callback_data=f"samneh_{smoking_type}_large"),
        ],
        [InlineKeyboardButton(tr("BACK_MAIN_MENU"), callback_data="menu_samneh")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_red_bisbas_menu_keyboard():
    """Get Red Bisbas menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(tr("SIZE_SMALL"), callback_data="red_bisbas_small"),
            InlineKeyboardButton(tr("SIZE_LARGE"), callback_data="red_bisbas_large"),
        ],
        [InlineKeyboardButton(tr("BACK_MAIN_MENU"), callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_direct_add_keyboard(product_name: str, include_info: bool = True):
    """Get direct add-to-cart keyboard.

    If *include_info* is False, the ℹ️ Info button is omitted. This is currently
    used for coffee products where an info popup is unnecessary.
    """

    add_button = InlineKeyboardButton(
        tr("ADD_TO_CART"),
        callback_data=f"add_{product_name.lower().replace(' ', '_')}",
    )

    rows = [[add_button]]

    if include_info:
        info_button = InlineKeyboardButton(
            tr("INFO"),
            callback_data=f"info_{product_name.lower().replace(' ', '_')}",
        )
        rows.append([info_button])

    rows.append([InlineKeyboardButton(tr("BACK_MAIN_MENU"), callback_data="menu_main")])

    return InlineKeyboardMarkup(rows)


def get_hilbeh_menu_keyboard():
    """Get Hilbeh menu keyboard (with availability check)"""
    if is_hilbeh_available():
        keyboard = [
            [InlineKeyboardButton(tr("ADD_TO_CART"), callback_data="add_hilbeh")],
            [InlineKeyboardButton(tr("INFO"), callback_data="info_hilbeh")],
            [InlineKeyboardButton(tr("BACK_MAIN_MENU"), callback_data="menu_main")],
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton(
                    tr("HILBEH_UNAVAILABLE"),
                    callback_data="hilbeh_unavailable",
                )
            ],
            [InlineKeyboardButton(tr("INFO"), callback_data="info_hilbeh")],
            [InlineKeyboardButton(tr("BACK_MAIN_MENU"), callback_data="menu_main")],
        ]

    return InlineKeyboardMarkup(keyboard)


def get_delivery_method_keyboard():
    """Get delivery method selection keyboard"""
    keyboard = [
        [InlineKeyboardButton(tr("DELIVERY_PICKUP"), callback_data="delivery_pickup")],
        [
            InlineKeyboardButton(
                tr("DELIVERY_DELIVERY"), callback_data="delivery_delivery"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_cart_keyboard():
    """Get cart view keyboard"""
    keyboard = [
        [InlineKeyboardButton(tr("CHANGE_DELIVERY"), callback_data="cart_change_delivery")],
        [InlineKeyboardButton(tr("SEND_ORDER"), callback_data="cart_send_order")],
        [
            InlineKeyboardButton(tr("CLEAR_CART"), callback_data="cart_clear_confirm"),
            InlineKeyboardButton(tr("BACK_MAIN_MENU"), callback_data="menu_main"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_cart_delivery_method_keyboard():
    """Get delivery method selection keyboard for cart"""
    keyboard = [
        [InlineKeyboardButton(tr("DELIVERY_PICKUP"), callback_data="cart_delivery_pickup")],
        [InlineKeyboardButton(tr("DELIVERY_DELIVERY"), callback_data="cart_delivery_delivery")],
        [InlineKeyboardButton(tr("BACK_MAIN_MENU"), callback_data="cart_view")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_clear_cart_confirmation_keyboard():
    """Get clear cart confirmation keyboard"""
    keyboard = [
        [InlineKeyboardButton(tr("CLEAR_CART_YES"), callback_data="cart_clear_yes")],
        [InlineKeyboardButton(tr("CLEAR_CART_NO"), callback_data="cart_view")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_order_confirmation_keyboard():
    """Get order confirmation keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                tr("ORDER_CONFIRM_YES"), callback_data="order_confirm_yes"
            )
        ],
        [
            InlineKeyboardButton(
                tr("ORDER_CONFIRM_NO"), callback_data="order_confirm_no"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)
