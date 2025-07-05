"""
Menu keyboards for the Samna Salta bot
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.infrastructure.utilities.helpers import is_hilbeh_available


def get_main_menu_keyboard():
    """Get main menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🍞 Kubaneh", callback_data="menu_kubaneh"),
            InlineKeyboardButton("🧈 Samneh", callback_data="menu_samneh"),
        ],
        [
            InlineKeyboardButton("🌶️ Red Bisbas", callback_data="menu_red_bisbas"),
            InlineKeyboardButton(
                "🥘 Hawaij soup spice", callback_data="menu_hawaij_soup"
            ),
        ],
        [
            InlineKeyboardButton(
                "☕ Hawaij coffee spice", callback_data="menu_hawaij_coffee"
            ),
            InlineKeyboardButton("☕ White coffee", callback_data="menu_white_coffee"),
        ],
        [InlineKeyboardButton("🌿 Hilbeh", callback_data="menu_hilbeh")],
        [InlineKeyboardButton("🛒 View cart / Finish order", callback_data="cart_view")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_kubaneh_menu_keyboard():
    """Get Kubaneh sub-menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("Classic", callback_data="kubaneh_classic"),
            InlineKeyboardButton("Seeded", callback_data="kubaneh_seeded"),
        ],
        [
            InlineKeyboardButton("Herb", callback_data="kubaneh_herb"),
            InlineKeyboardButton("Aromatic", callback_data="kubaneh_aromatic"),
        ],
        [InlineKeyboardButton("⬅️ Back to main menu", callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_kubaneh_oil_keyboard(kubaneh_type: str):
    """Get Kubaneh oil selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                "Olive oil", callback_data=f"kubaneh_{kubaneh_type}_olive_oil"
            ),
            InlineKeyboardButton(
                "Samneh", callback_data=f"kubaneh_{kubaneh_type}_samneh"
            ),
        ],
        [InlineKeyboardButton("⬅️ Back to Kubaneh menu", callback_data="menu_kubaneh")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_samneh_menu_keyboard():
    """Get Samneh sub-menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("Smoked", callback_data="samneh_smoked"),
            InlineKeyboardButton("Not smoked", callback_data="samneh_not_smoked"),
        ],
        [InlineKeyboardButton("⬅️ Back to main menu", callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_samneh_size_keyboard(smoking_type: str):
    """Get Samneh size selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("Small", callback_data=f"samneh_{smoking_type}_small"),
            InlineKeyboardButton("Large", callback_data=f"samneh_{smoking_type}_large"),
        ],
        [InlineKeyboardButton("⬅️ Back to Samneh menu", callback_data="menu_samneh")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_red_bisbas_menu_keyboard():
    """Get Red Bisbas menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("Small", callback_data="red_bisbas_small"),
            InlineKeyboardButton("Large", callback_data="red_bisbas_large"),
        ],
        [InlineKeyboardButton("⬅️ Back to main menu", callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_direct_add_keyboard(product_name: str):
    """Get direct add to cart keyboard for simple products"""
    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Add to cart",
                callback_data=f"add_{product_name.lower().replace(' ', '_')}",
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ Info",
                callback_data=f"info_{product_name.lower().replace(' ', '_')}",
            )
        ],
        [InlineKeyboardButton("⬅️ Back to main menu", callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_hilbeh_menu_keyboard():
    """Get Hilbeh menu keyboard (with availability check)"""
    if is_hilbeh_available():
        keyboard = [
            [InlineKeyboardButton("➕ Add to cart", callback_data="add_hilbeh")],
            [InlineKeyboardButton("ℹ️ Info", callback_data="info_hilbeh")],
            [InlineKeyboardButton("⬅️ Back to main menu", callback_data="menu_main")],
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton(
                    "❌ Not available today (Wed-Fri only)",
                    callback_data="hilbeh_unavailable",
                )
            ],
            [InlineKeyboardButton("ℹ️ Info", callback_data="info_hilbeh")],
            [InlineKeyboardButton("⬅️ Back to main menu", callback_data="menu_main")],
        ]

    return InlineKeyboardMarkup(keyboard)


def get_delivery_method_keyboard():
    """Get delivery method selection keyboard"""
    keyboard = [
        [InlineKeyboardButton("🚶 Self-pickup", callback_data="delivery_pickup")],
        [
            InlineKeyboardButton(
                "🚚 Delivery (+5 ILS)", callback_data="delivery_delivery"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_cart_keyboard():
    """Get cart view keyboard"""
    keyboard = [
        [InlineKeyboardButton("📝 Send order", callback_data="cart_send_order")],
        [InlineKeyboardButton("⬅️ Back to menu", callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_order_confirmation_keyboard():
    """Get order confirmation keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                "👍 Yes, details are correct", callback_data="order_confirm_yes"
            )
        ],
        [
            InlineKeyboardButton(
                "✏️ No, I want to edit", callback_data="order_confirm_no"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)
