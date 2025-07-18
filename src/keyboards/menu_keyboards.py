"""
Menu keyboards for the Samna Salta bot
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.utils.helpers import is_hilbeh_available
from src.utils.i18n import i18n
from src.keyboards.order_keyboards import get_delivery_method_keyboard
from src.db.operations import get_all_products, get_products_by_category


def get_dynamic_main_menu_keyboard(user_id: int = None):
    """Get dynamic main menu keyboard that shows categories first."""
    try:
        # Get all active products from database
        products = get_all_products()
        
        if not products:
            # Fallback to static menu if no products found
            return get_main_menu_keyboard(user_id)
        
        # Group products by category
        categories = {}
        for product in products:
            category = product.category or "other"
            if category not in categories:
                categories[category] = []
            categories[category].append(product)
        
        # Build keyboard with only category buttons
        keyboard = []
        
        # Add category buttons (max 2 per row)
        row = []
        for category, category_products in categories.items():
            # Create category button with product count
            button_text = f"📂 {category.title()} ({len(category_products)})"
            callback_data = f"category_{category}"
            
            row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            
            # Add row when we have 2 categories or it's the last category
            if len(row) == 2 or category == list(categories.keys())[-1]:
                keyboard.append(row)
                row = []
        
        # Add standard action buttons
        keyboard.append([InlineKeyboardButton(i18n.get_text("BUTTON_VIEW_CART", user_id=user_id), callback_data="cart_view")])
        keyboard.append([InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="main_page")])
        
        return InlineKeyboardMarkup(keyboard)
        
    except Exception as e:
        # Fallback to static menu if there's an error
        print(f"Error creating dynamic menu: {e}")
        return get_main_menu_keyboard(user_id)


def get_category_menu_keyboard(category: str, user_id: int = None):
    """Get menu keyboard for a specific category."""
    try:
        products = get_products_by_category(category)
        
        if not products:
            # Return to main menu if no products in category
            keyboard = [
                [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")]
            ]
            return InlineKeyboardMarkup(keyboard)
        
        keyboard = []
        
        # Add category header (text only, not clickable)
        # Note: We can't add plain text to keyboard, so we'll skip the header
        # The category name will be shown in the message text instead
        
        # Add product buttons (max 2 per row)
        row = []
        for product in products:
            # Cleaner product button format
            button_text = f"{product.name}\n₪{product.price:.2f}"
            callback_data = f"product_{product.id}"
            
            row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            
            if len(row) == 2 or product == products[-1]:
                keyboard.append(row)
                row = []
        
        # Add action buttons
        keyboard.append([InlineKeyboardButton(i18n.get_text("BUTTON_VIEW_CART", user_id=user_id), callback_data="cart_view")])
        keyboard.append([InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")])
        
        return InlineKeyboardMarkup(keyboard)
        
    except Exception as e:
        print(f"Error creating category menu: {e}")
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")]
        ]
        return InlineKeyboardMarkup(keyboard)


def get_main_menu_keyboard(user_id: int = None):
    """Get main menu keyboard (translated)."""
    keyboard = [
        [
            InlineKeyboardButton(i18n.get_text("BUTTON_KUBANEH", user_id=user_id), callback_data="menu_kubaneh"),
            InlineKeyboardButton(i18n.get_text("BUTTON_SAMNEH", user_id=user_id), callback_data="menu_samneh"),
        ],
        [
            InlineKeyboardButton(i18n.get_text("BUTTON_RED_BISBAS", user_id=user_id), callback_data="menu_red_bisbas"),
            InlineKeyboardButton(i18n.get_text("BUTTON_HAWAIIJ_SOUP", user_id=user_id), callback_data="menu_hawaij_soup"),
        ],
        [
            InlineKeyboardButton(i18n.get_text("BUTTON_HAWAIIJ_COFFEE", user_id=user_id), callback_data="menu_hawaij_coffee"),
            InlineKeyboardButton(i18n.get_text("BUTTON_WHITE_COFFEE", user_id=user_id), callback_data="menu_white_coffee"),
        ],
        [InlineKeyboardButton(i18n.get_text("BUTTON_HILBEH", user_id=user_id), callback_data="menu_hilbeh")],
        [InlineKeyboardButton(i18n.get_text("BUTTON_VIEW_CART", user_id=user_id), callback_data="cart_view")],
        [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="main_page")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_kubaneh_menu_keyboard(user_id: int = None):
    """Get Kubaneh sub-menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(i18n.get_text("KUBANEH_CLASSIC", user_id=user_id), callback_data="kubaneh_classic"),
            InlineKeyboardButton(i18n.get_text("KUBANEH_SEEDED", user_id=user_id), callback_data="kubaneh_seeded"),
        ],
        [
            InlineKeyboardButton(i18n.get_text("KUBANEH_HERB", user_id=user_id), callback_data="kubaneh_herb"),
            InlineKeyboardButton(i18n.get_text("KUBANEH_AROMATIC", user_id=user_id), callback_data="kubaneh_aromatic"),
        ],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_kubaneh_oil_keyboard(kubaneh_type: str, user_id: int = None):
    """Get Kubaneh oil selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                i18n.get_text("OIL_OLIVE", user_id=user_id), callback_data=f"kubaneh_{kubaneh_type}_olive_oil"
            ),
            InlineKeyboardButton(
                i18n.get_text("OIL_SAMNEH", user_id=user_id), callback_data=f"kubaneh_{kubaneh_type}_samneh"
            ),
        ],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_kubaneh")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_samneh_menu_keyboard(user_id: int = None):
    """Get Samneh sub-menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(i18n.get_text("SAMNEH_SMOKED", user_id=user_id), callback_data="samneh_smoked"),
            InlineKeyboardButton(i18n.get_text("SAMNEH_NOT_SMOKED", user_id=user_id), callback_data="samneh_not_smoked"),
        ],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_samneh_size_keyboard(smoking_type: str, user_id: int = None):
    """Get Samneh size selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(i18n.get_text("SIZE_SMALL", user_id=user_id), callback_data=f"samneh_{smoking_type}_small"),
            InlineKeyboardButton(i18n.get_text("SIZE_LARGE", user_id=user_id), callback_data=f"samneh_{smoking_type}_large"),
        ],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_samneh")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_red_bisbas_menu_keyboard(user_id: int = None):
    """Get Red Bisbas menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(i18n.get_text("SIZE_SMALL", user_id=user_id), callback_data="red_bisbas_small"),
            InlineKeyboardButton(i18n.get_text("SIZE_LARGE", user_id=user_id), callback_data="red_bisbas_large"),
        ],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_direct_add_keyboard(product_name: str, include_info: bool = True, user_id: int = None):
    """Get direct add-to-cart keyboard."""
    add_button = InlineKeyboardButton(
        i18n.get_text("ADD_TO_CART", user_id=user_id),
        callback_data=f"add_{product_name.lower().replace(' ', '_')}",
    )

    rows = [[add_button]]

    if include_info:
        info_button = InlineKeyboardButton(
            i18n.get_text("INFO", user_id=user_id),
            callback_data=f"info_{product_name.lower().replace(' ', '_')}",
        )
        rows.append([info_button])

    rows.append([InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")])

    return InlineKeyboardMarkup(rows)


def get_hilbeh_menu_keyboard(user_id: int = None):
    """Get Hilbeh menu keyboard (with availability check)"""
    if is_hilbeh_available():
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("ADD_TO_CART", user_id=user_id), callback_data="add_hilbeh")],
            [InlineKeyboardButton(i18n.get_text("INFO", user_id=user_id), callback_data="info_hilbeh")],
            [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")],
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton(
                    i18n.get_text("HILBEH_UNAVAILABLE", user_id=user_id),
                    callback_data="hilbeh_unavailable",
                )
            ],
            [InlineKeyboardButton(i18n.get_text("INFO", user_id=user_id), callback_data="info_hilbeh")],
            [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_cart_keyboard(user_id: int = None):
    """Get cart view keyboard"""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("CHANGE_DELIVERY", user_id=user_id), callback_data="cart_change_delivery")],
        [InlineKeyboardButton(i18n.get_text("SEND_ORDER", user_id=user_id), callback_data="cart_send_order")],
        [
            InlineKeyboardButton(i18n.get_text("CLEAR_CART", user_id=user_id), callback_data="cart_clear_confirm"),
            InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_cart_delivery_method_keyboard(user_id: int = None):
    """Get delivery method selection keyboard for cart"""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("DELIVERY_PICKUP", user_id=user_id), callback_data="cart_delivery_pickup")],
        [InlineKeyboardButton(i18n.get_text("DELIVERY_DELIVERY", user_id=user_id), callback_data="cart_delivery_delivery")],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="cart_view")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_clear_cart_confirmation_keyboard(user_id: int = None):
    """Get clear cart confirmation keyboard"""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("CLEAR_CART_YES", user_id=user_id), callback_data="cart_clear_yes")],
        [InlineKeyboardButton(i18n.get_text("CLEAR_CART_NO", user_id=user_id), callback_data="cart_view")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_back_to_cart_keyboard(user_id: int = None):
    """Get back to cart keyboard"""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("BACK_TO_CART", user_id=user_id), callback_data="cart_view")],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")],
    ]

    return InlineKeyboardMarkup(keyboard)
