"""
Menu keyboards for the Samna Salta bot
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.utils.helpers import is_hilbeh_available
from src.utils.i18n import i18n
from src.utils.helpers import translate_category_name
from src.keyboards.order_keyboards import get_delivery_method_keyboard
from src.db.operations import get_all_products, get_products_by_category, get_localized_name
from src.utils.language_manager import language_manager
from src.utils.constants_manager import get_product_option_name, get_product_size_name, get_delivery_method_name


def get_dynamic_main_menu_keyboard(user_id: int = None):
    """Get dynamic main menu keyboard that shows categories first."""
    try:
        from src.db.operations import get_db_manager
        from src.utils.language_manager import language_manager
        
        # Get user language for localization
        user_language = language_manager.get_user_language(user_id) if user_id else "en"
        
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
                # Get category name based on user language
                if product.category_rel:
                    if user_language == "he":
                        category_name = product.category_rel.name_he
                    else:
                        category_name = product.category_rel.name_en
                else:
                    category_name = "other"
                
                if category_name not in categories:
                    categories[category_name] = []
                categories[category_name].append(product)
            
            # Build keyboard with only category buttons
            keyboard = []
            
            # Add category buttons (each on its own line)
            for category, category_products in categories.items():
                # Create professional category button with beautiful icons and product count
                translated_category = translate_category_name(category, user_id)
                category_emoji = {
                    'kubaneh': '🥖',
                    'samneh': '🧈', 
                    'red_bisbas': '🌶️',
                    'hawaij_soup': '🍲',
                    'hawaij_coffee': '☕',
                    'white_coffee': '🤍',
                    'hilbeh': '🫘',
                    'other': '📂'
                }.get(category.lower(), '')
                
                button_text = f"{category_emoji} {translated_category} ({len(category_products)})"
                callback_data = f"category_{category}"
                
                # Add each category button on its own line
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            # Add professional action buttons with beautiful styling
            keyboard.append([InlineKeyboardButton(
                i18n.get_text('BUTTON_VIEW_CART', user_id=user_id), 
                callback_data="cart_view"
            )])
            keyboard.append([InlineKeyboardButton(
                i18n.get_text('BACK_TO_MAIN', user_id=user_id), 
                callback_data="main_page"
            )])
            
            return InlineKeyboardMarkup(keyboard)
        
    except Exception as e:
        print(f"Error creating dynamic menu: {e}")
        return get_main_menu_keyboard(user_id)


def get_category_menu_keyboard(category: str, user_id: int = None):
    """Get menu keyboard for a specific category with multilingual support."""
    try:
        products = get_products_by_category(category)
        
        if not products:
            # Return to main menu if no products in category
            keyboard = [
                [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")]
            ]
            return InlineKeyboardMarkup(keyboard)
        
        keyboard = []
        
        # Get user language for localization
        user_language = language_manager.get_user_language(user_id) if user_id else "en"
        
        # Add product buttons (each on its own line) - clicking these shows product details
        for product in products:
            # Get localized product name
            localized_name = get_localized_name(product, user_language)
            
            # Product button - clicking this shows product details
            button_text = f"{localized_name}\n - ₪{product.price:.2f} 💰"
            callback_data = f"product_{product.id}"
            
            # Add each product button on its own line
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
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
    """Get main menu keyboard (translated) with each button on its own line."""
    keyboard = [
        [InlineKeyboardButton(i18n.get_text("BUTTON_KUBANEH", user_id=user_id), callback_data="menu_kubaneh")],
        [InlineKeyboardButton(i18n.get_text("BUTTON_SAMNEH", user_id=user_id), callback_data="menu_samneh")],
        [InlineKeyboardButton(i18n.get_text("BUTTON_RED_BISBAS", user_id=user_id), callback_data="menu_red_bisbas")],
        [InlineKeyboardButton(i18n.get_text("BUTTON_HAWAIIJ_SOUP", user_id=user_id), callback_data="menu_hawaij_soup")],
        [InlineKeyboardButton(i18n.get_text("BUTTON_HAWAIIJ_COFFEE", user_id=user_id), callback_data="menu_hawaij_coffee")],
        [InlineKeyboardButton(i18n.get_text("BUTTON_WHITE_COFFEE", user_id=user_id), callback_data="menu_white_coffee")],
        [InlineKeyboardButton(i18n.get_text("BUTTON_HILBEH", user_id=user_id), callback_data="menu_hilbeh")],
        [InlineKeyboardButton(i18n.get_text("BUTTON_VIEW_CART", user_id=user_id), callback_data="cart_view")],
        [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="main_page")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_kubaneh_menu_keyboard(user_id: int = None):
    """Get Kubaneh menu keyboard with each button on its own line."""
    keyboard = [
        [InlineKeyboardButton(get_product_option_name("kubaneh", "classic", user_id), callback_data="kubaneh_classic")],
        [InlineKeyboardButton(get_product_option_name("kubaneh", "seeded", user_id), callback_data="kubaneh_seeded")],
        [InlineKeyboardButton(get_product_option_name("kubaneh", "herb", user_id), callback_data="kubaneh_herb")],
        [InlineKeyboardButton(get_product_option_name("kubaneh", "aromatic", user_id), callback_data="kubaneh_aromatic")],
        [InlineKeyboardButton(i18n.get_text("BUTTON_VIEW_CART", user_id=user_id), callback_data="cart_view")],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_samneh_menu_keyboard(user_id: int = None):
    """Get Samneh menu keyboard with each button on its own line."""
    keyboard = [
        [InlineKeyboardButton(get_product_option_name("samneh", "classic", user_id), callback_data="samneh_classic")],
        [InlineKeyboardButton(get_product_option_name("samneh", "spicy", user_id), callback_data="samneh_spicy")],
        [InlineKeyboardButton(get_product_option_name("samneh", "herb", user_id), callback_data="samneh_herb")],
        [InlineKeyboardButton(get_product_option_name("samneh", "honey", user_id), callback_data="samneh_honey")],
        [InlineKeyboardButton(i18n.get_text("BUTTON_VIEW_CART", user_id=user_id), callback_data="cart_view")],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_red_bisbas_menu_keyboard(user_id: int = None):
    """Get Red Bisbas menu keyboard with each button on its own line."""
    keyboard = [
        [InlineKeyboardButton(get_product_size_name("small", user_id), callback_data="red_bisbas_small")],
        [InlineKeyboardButton(get_product_size_name("medium", user_id), callback_data="red_bisbas_medium")],
        [InlineKeyboardButton(get_product_size_name("large", user_id), callback_data="red_bisbas_large")],
        [InlineKeyboardButton(get_product_size_name("xl", user_id), callback_data="red_bisbas_xl")],
        [InlineKeyboardButton(i18n.get_text("BUTTON_VIEW_CART", user_id=user_id), callback_data="cart_view")],
        [InlineKeyboardButton(i18n.get_text("BACK_MAIN_MENU", user_id=user_id), callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_hilbeh_menu_keyboard(user_id: int = None):
    """Get Hilbeh menu keyboard with availability check and each button on its own line."""
    if is_hilbeh_available():
        keyboard = [
            [InlineKeyboardButton(get_product_option_name("hilbeh", "classic", user_id), callback_data="hilbeh_classic")],
            [InlineKeyboardButton(get_product_option_name("hilbeh", "spicy", user_id), callback_data="hilbeh_spicy")],
            [InlineKeyboardButton(get_product_option_name("hilbeh", "sweet", user_id), callback_data="hilbeh_sweet")],
            [InlineKeyboardButton(get_product_option_name("hilbeh", "premium", user_id), callback_data="hilbeh_premium")],
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
    """Get professional cart view keyboard with each button on its own line"""
    keyboard = [
        # Primary Action
        [InlineKeyboardButton(
            i18n.get_text('SEND_ORDER', user_id=user_id), 
            callback_data="cart_send_order"
        )],
        # Secondary Actions
        [InlineKeyboardButton(
            i18n.get_text('CHANGE_DELIVERY', user_id=user_id), 
            callback_data="cart_change_delivery"
        )],
        # Bottom Actions
        [InlineKeyboardButton(
            i18n.get_text('CLEAR_CART', user_id=user_id), 
            callback_data="cart_clear_confirm"
        )],
        [InlineKeyboardButton(
            i18n.get_text('BACK_MAIN_MENU', user_id=user_id), 
            callback_data="menu_main"
        )],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_cart_delivery_method_keyboard(user_id: int = None):
    """Get delivery method selection keyboard for cart"""
    keyboard = [
        [InlineKeyboardButton(get_delivery_method_name("pickup", user_id), callback_data="cart_delivery_pickup")],
        [InlineKeyboardButton(get_delivery_method_name("delivery", user_id), callback_data="cart_delivery_delivery")],
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
