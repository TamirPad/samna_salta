"""
Menu keyboards for the Samna Salta bot
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.utils.helpers import is_hilbeh_available
from src.utils.i18n import i18n
from src.utils.helpers import translate_category_name
from src.keyboards.order_keyboards import get_delivery_method_keyboard
from src.db.operations import get_all_products, get_products_by_category


def get_dynamic_main_menu_keyboard(user_id: int = None):
    """Get dynamic main menu keyboard that shows categories first."""
    try:
        from src.db.operations import get_db_manager
        
        # Use session context to ensure relationships are loaded properly
        with get_db_manager().get_session_context() as session:
            from src.db.models import Product
            
            # Get all active products with their categories loaded
            products = session.query(Product).filter(Product.is_active).all()
            
            if not products:
                # Fallback to static menu if no products found
                return get_main_menu_keyboard(user_id)
            
            # Group products by category
            categories = {}
            for product in products:
                # Access category name safely
                category_name = product.category or "other"
                if category_name not in categories:
                    categories[category_name] = []
                categories[category_name].append(product)
            
            # Build keyboard with only category buttons
            keyboard = []
            
            # Add category buttons (max 2 per row)
            row = []
            for category, category_products in categories.items():
                # Create category button with product count using translated category name
                translated_category = translate_category_name(category, user_id)
                button_text = f"📂 {translated_category} ({len(category_products)})"
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
        
        # Add product buttons (max 2 per row) - clicking these shows product details
        row = []
        for product in products:
            # Product button - clicking this shows product details
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
        # Fallback to simple back button
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
    """Get Kubaneh menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(i18n.get_text("KUBANEH_CLASSIC", user_id=user_id), callback_data="kubaneh_classic"),
            InlineKeyboardButton(i18n.get_text("KUBANEH_SEEDED", user_id=user_id), callback_data="kubaneh_seeded"),
        ],
        [
            InlineKeyboardButton(i18n.get_text("KUBANEH_HERB", user_id=user_id), callback_data="kubaneh_herb"),
            InlineKeyboardButton(i18n.get_text("KUBANEH_AROMATIC", user_id=user_id), callback_data="kubaneh_aromatic"),
        ],
        [InlineKeyboardButton(i18n.get_text("BUTTON_VIEW_CART", user_id=user_id), callback_data="cart_view")],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_samneh_menu_keyboard(user_id: int = None):
    """Get Samneh menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(i18n.get_text("SAMNEH_CLASSIC", user_id=user_id), callback_data="samneh_classic"),
            InlineKeyboardButton(i18n.get_text("SAMNEH_SPICY", user_id=user_id), callback_data="samneh_spicy"),
        ],
        [
            InlineKeyboardButton(i18n.get_text("SAMNEH_HERB", user_id=user_id), callback_data="samneh_herb"),
            InlineKeyboardButton(i18n.get_text("SAMNEH_HONEY", user_id=user_id), callback_data="samneh_honey"),
        ],
        [InlineKeyboardButton(i18n.get_text("BUTTON_VIEW_CART", user_id=user_id), callback_data="cart_view")],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_red_bisbas_menu_keyboard(user_id: int = None):
    """Get Red Bisbas menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(i18n.get_text("RED_BISBAS_SMALL", user_id=user_id), callback_data="red_bisbas_small"),
            InlineKeyboardButton(i18n.get_text("RED_BISBAS_MEDIUM", user_id=user_id), callback_data="red_bisbas_medium"),
        ],
        [
            InlineKeyboardButton(i18n.get_text("RED_BISBAS_LARGE", user_id=user_id), callback_data="red_bisbas_large"),
            InlineKeyboardButton(i18n.get_text("RED_BISBAS_XL", user_id=user_id), callback_data="red_bisbas_xl"),
        ],
        [InlineKeyboardButton(i18n.get_text("BUTTON_VIEW_CART", user_id=user_id), callback_data="cart_view")],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_hilbeh_menu_keyboard(user_id: int = None):
    """Get Hilbeh menu keyboard with availability check."""
    if is_hilbeh_available():
        keyboard = [
            [
                InlineKeyboardButton(i18n.get_text("HILBEH_CLASSIC", user_id=user_id), callback_data="hilbeh_classic"),
                InlineKeyboardButton(i18n.get_text("HILBEH_SPICY", user_id=user_id), callback_data="hilbeh_spicy"),
            ],
            [
                InlineKeyboardButton(i18n.get_text("HILBEH_SWEET", user_id=user_id), callback_data="hilbeh_sweet"),
                InlineKeyboardButton(i18n.get_text("HILBEH_PREMIUM", user_id=user_id), callback_data="hilbeh_premium"),
            ],
            [InlineKeyboardButton(i18n.get_text("BUTTON_VIEW_CART", user_id=user_id), callback_data="cart_view")],
            [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")],
        ]
    return InlineKeyboardMarkup(keyboard)


def get_direct_add_keyboard(product_type: str, user_id: int = None):
    """Get direct add to cart keyboard for simple products."""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("ADD_TO_CART", user_id=user_id), callback_data=f"add_{product_type}")],
        [InlineKeyboardButton(i18n.get_text("BUTTON_VIEW_CART", user_id=user_id), callback_data="cart_view")],
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
