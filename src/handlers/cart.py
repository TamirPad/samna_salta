"""
Cart handler for managing shopping cart operations
"""

import logging
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.container import get_container
from src.utils.i18n import i18n
from src.utils.error_handler import handle_error

logger = logging.getLogger(__name__)


class CartHandler:
    """Handler for cart-related operations"""

    def __init__(self):
        self.container = get_container()
        self.logger = logger

    async def handle_add_to_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle adding items to cart"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            callback_data = query.data

            # Parse product info from callback data
            product_info = self._parse_product_from_callback(callback_data)
            if not product_info:
                await query.edit_message_text(
                    "❌ Invalid product selection. Please try again.",
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_menu_keyboard(),
                )
                return

            self.logger.info("🛒 ADD TO CART: User %s clicked: %s", user_id, callback_data)
            self.logger.info("📦 PARSED PRODUCT: %s", product_info)

            # Get cart service
            cart_service = self.container.get_cart_service()

            # Add to cart using the service
            success = cart_service.add_item(
                telegram_id=user_id,
                product_id=product_info["product_id"],
                quantity=1,
                options=product_info.get("options", {}),
            )

            if success:
                # Get updated cart for summary
                cart_items = cart_service.get_items(user_id)
                cart_total = cart_service.calculate_total(cart_items)
                item_count = len(cart_items)

                self.logger.info(
                    "✅ ADD SUCCESS: %s added. Cart: %d items, ₪%.2f",
                    product_info["display_name"],
                    item_count,
                    cart_total,
                )

                # Send success message
                message = f"✅ **{product_info['display_name']}** added to cart!\n\n"
                message += f"🛒 **Cart Summary:**\n"
                message += f"• Items: {item_count}\n"
                message += f"• Total: ₪{cart_total:.2f}\n\n"
                message += "What would you like to do next?"

                await query.edit_message_text(
                    message,
                    parse_mode="HTML",
                    reply_markup=self._get_cart_success_keyboard(),
                )
            else:
                self.logger.error("❌ ADD FAILED: User %s, Product: %s", user_id, product_info["display_name"])
                await query.edit_message_text(
                    "❌ Failed to add item to cart. Please try again.",
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_menu_keyboard(),
                )

        except Exception as e:
            self.logger.error("Exception in handle_add_to_cart: %s", e)
            await handle_error(update, e, "adding item to cart")

    async def handle_view_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle viewing cart contents"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            self.logger.info("🛒 VIEW CART: User %s", user_id)

            # Get cart service
            cart_service = self.container.get_cart_service()
            cart_items = cart_service.get_items(user_id)

            if not cart_items:
                await query.edit_message_text(
                    "🛒 **Your cart is empty**\n\nBrowse our menu to add some delicious items!",
                    parse_mode="HTML",
                    reply_markup=self._get_empty_cart_keyboard(),
                )
                return

            # Calculate total
            cart_total = cart_service.calculate_total(cart_items)

            # Build cart display
            message = "🛒 **Your Cart**\n\n"
            
            for i, item in enumerate(cart_items, 1):
                item_total = item.get("price", 0) * item.get("quantity", 1)
                message += f"{i}. **{item.get('product_name', 'Unknown Product')}**\n"
                message += f"   • Quantity: {item.get('quantity', 1)}\n"
                message += f"   • Price: ₪{item.get('price', 0):.2f}\n"
                message += f"   • Total: ₪{item_total:.2f}\n\n"

            message += f"💰 **Total: ₪{cart_total:.2f}**\n\n"
            message += "What would you like to do?"

            await query.edit_message_text(
                message,
                parse_mode="HTML",
                reply_markup=self._get_cart_actions_keyboard(),
            )

        except Exception as e:
            self.logger.error("Exception in handle_view_cart: %s", e)
            await handle_error(update, e, "viewing cart")

    async def handle_clear_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle clearing cart"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = query.from_user.id
            self.logger.info("🗑️ CLEAR CART: User %s", user_id)

            # Get cart service
            cart_service = self.container.get_cart_service()
            success = cart_service.clear_cart(user_id)

            if success:
                self.logger.info("✅ CART CLEARED: User %s", user_id)
                await query.edit_message_text(
                    "🗑️ **Cart cleared successfully!**\n\nYour cart is now empty.",
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_menu_keyboard(),
                )
            else:
                self.logger.error("❌ CART CLEAR FAILED: User %s", user_id)
                await query.edit_message_text(
                    "❌ Failed to clear cart. Please try again.",
                    parse_mode="HTML",
                    reply_markup=self._get_back_to_menu_keyboard(),
                )

        except Exception as e:
            self.logger.error("Exception in handle_clear_cart: %s", e)
            await handle_error(update, e, "clearing cart")

    def _parse_product_from_callback(self, callback_data: str) -> Dict[str, Any]:
        """Parse product information from callback data"""
        try:
            # Handle different callback patterns
            if callback_data.startswith("add_"):
                # Extract product info from callback data
                parts = callback_data.split("_")
                if len(parts) >= 3:
                    product_type = parts[1]
                    variant = parts[2] if len(parts) > 2 else "default"
                    
                    # Map callback data to product info
                    product_mapping = {
                        "kubaneh": {"product_id": 1, "display_name": "Kubaneh (Classic)", "options": {"type": "classic"}},
                        "red": {"product_id": 3, "display_name": "Red Bisbas (Small)", "options": {"size": "small"}},
                        "hawaij": {"product_id": 4, "display_name": "Hawaij for Soup", "options": {}},
                        "hawaij": {"product_id": 5, "display_name": "Hawaij for Coffee", "options": {}},
                        "white": {"product_id": 6, "display_name": "White Coffee", "options": {}},
                        "hilbeh": {"product_id": 7, "display_name": "Hilbeh", "options": {}},
                    }
                    
                    if product_type in product_mapping:
                        return product_mapping[product_type]
            
            # Handle direct product option patterns (from sub-menus)
            elif callback_data in [
                "kubaneh_classic", "kubaneh_seeded", "kubaneh_herb", "kubaneh_aromatic",
                "samneh_smoked", "samneh_not_smoked",
                "red_bisbas_small", "red_bisbas_large",
                "hawaij_coffee_spice", "white_coffee"
            ]:
                # Map specific product options to product info
                product_mapping = {
                    # Kubaneh options
                    "kubaneh_classic": {"product_id": 1, "display_name": "Kubaneh (Classic)", "options": {"type": "classic"}},
                    "kubaneh_seeded": {"product_id": 1, "display_name": "Kubaneh (Seeded)", "options": {"type": "seeded"}},
                    "kubaneh_herb": {"product_id": 1, "display_name": "Kubaneh (Herb)", "options": {"type": "herb"}},
                    "kubaneh_aromatic": {"product_id": 1, "display_name": "Kubaneh (Aromatic)", "options": {"type": "aromatic"}},
                    
                    # Samneh options
                    "samneh_smoked": {"product_id": 2, "display_name": "Samneh (Smoked)", "options": {"type": "smoked"}},
                    "samneh_not_smoked": {"product_id": 2, "display_name": "Samneh (Not Smoked)", "options": {"type": "not_smoked"}},
                    
                    # Red Bisbas options
                    "red_bisbas_small": {"product_id": 3, "display_name": "Red Bisbas (Small)", "options": {"size": "small"}},
                    "red_bisbas_large": {"product_id": 3, "display_name": "Red Bisbas (Large)", "options": {"size": "large"}},
                    
                    # Direct add products
                    "hawaij_coffee_spice": {"product_id": 5, "display_name": "Hawaij for Coffee", "options": {}},
                    "white_coffee": {"product_id": 6, "display_name": "White Coffee", "options": {}},
                }
                
                return product_mapping.get(callback_data)
            
            return None
        except Exception as e:
            self.logger.error("Error parsing product from callback: %s", e)
            return None

    def _get_cart_success_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for successful add to cart"""
        keyboard = [
            [
                InlineKeyboardButton("🛒 View Cart", callback_data="view_cart"),
                InlineKeyboardButton("➕ Add More", callback_data="menu_main"),
            ],
            [
                InlineKeyboardButton("📋 Checkout", callback_data="checkout"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_cart_actions_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for cart actions"""
        keyboard = [
            [
                InlineKeyboardButton("🗑️ Clear Cart", callback_data="clear_cart"),
                InlineKeyboardButton("📋 Checkout", callback_data="checkout"),
            ],
            [
                InlineKeyboardButton("➕ Add More", callback_data="menu_main"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_empty_cart_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for empty cart"""
        keyboard = [
            [
                InlineKeyboardButton("🍽️ Browse Menu", callback_data="menu_main"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_back_to_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard to go back to menu"""
        keyboard = [
            [
                InlineKeyboardButton("🏠 Back to Menu", callback_data="menu_main"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)
