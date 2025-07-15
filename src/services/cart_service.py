"""
Cart management service
"""

import logging
from typing import List, Dict, Optional

from src.db.operations import (
    add_to_cart,
    get_cart_items,
    update_cart,
    clear_cart,
    remove_from_cart,
    get_customer_by_telegram_id,
    get_or_create_customer,
)
from src.db.models import Customer

logger = logging.getLogger(__name__)


class CartService:
    """Service for cart management operations"""

    def validate_customer_data(self, full_name: str, phone: str) -> Dict[str, any]:
        """Validate customer data"""
        errors = []
        
        # Validate name
        if not full_name or len(full_name.strip()) < 2:
            errors.append("Name must be at least 2 characters long")
        
        # Validate phone (basic validation)
        if not phone or len(phone.strip()) < 8:
            errors.append("Phone number must be at least 8 digits")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def register_customer(self, telegram_id: int, full_name: str, phone: str) -> Dict[str, any]:
        """Register a new customer or update existing one"""
        try:
            # Check if customer already exists
            existing_customer = get_customer_by_telegram_id(telegram_id)
            
            if existing_customer:
                # Update existing customer
                existing_customer.full_name = full_name
                existing_customer.phone_number = phone
                # Note: In a real implementation, you'd need to save the updated customer
                return {
                    "success": True,
                    "customer": existing_customer,
                    "is_returning": True
                }
            else:
                # Create new customer
                customer = get_or_create_customer(telegram_id, full_name, phone)
                if customer:
                    return {
                        "success": True,
                        "customer": customer,
                        "is_returning": False
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to create customer"
                    }
                    
        except Exception as e:
            logger.error("Exception registering customer: %s", e)
            return {
                "success": False,
                "error": str(e)
            }

    def add_item(
        self, telegram_id: int, product_id: int, quantity: int = 1, options: Optional[Dict] = None
    ) -> bool:
        """Add item to cart"""
        try:
            logger.info("Adding item to cart: telegram_id=%s, product_id=%s, quantity=%s", 
                       telegram_id, product_id, quantity)
            success = add_to_cart(telegram_id, product_id, quantity, options or {})
            if success:
                logger.info("Successfully added item to cart for user %s", telegram_id)
            else:
                logger.error("Failed to add item to cart for user %s", telegram_id)
            return success
        except Exception as e:
            logger.error("Exception adding item to cart: %s", e)
            return False

    def get_items(self, telegram_id: int) -> List[Dict]:
        """Get cart items for user"""
        try:
            items = get_cart_items(telegram_id)
            logger.info("Retrieved %d items from cart for user %s", len(items), telegram_id)
            return items
        except Exception as e:
            logger.error("Exception getting cart items: %s", e)
            return []

    def calculate_total(self, items: List[Dict]) -> float:
        """Calculate total price of cart items"""
        try:
            total = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
            logger.info("Calculated cart total: %.2f", total)
            return total
        except Exception as e:
            logger.error("Exception calculating cart total: %s", e)
            return 0.0

    def clear_cart(self, telegram_id: int) -> bool:
        """Clear all items from cart"""
        try:
            success = clear_cart(telegram_id)
            if success:
                logger.info("Successfully cleared cart for user %s", telegram_id)
            else:
                logger.error("Failed to clear cart for user %s", telegram_id)
            return success
        except Exception as e:
            logger.error("Exception clearing cart: %s", e)
            return False

    def remove_item(self, telegram_id: int, product_id: int) -> bool:
        """Remove item from cart"""
        try:
            success = remove_from_cart(telegram_id, product_id)
            if success:
                logger.info("Successfully removed item from cart for user %s", telegram_id)
            else:
                logger.error("Failed to remove item from cart for user %s", telegram_id)
            return success
        except Exception as e:
            logger.error("Exception removing item from cart: %s", e)
            return False

    def get_customer(self, telegram_id: int) -> Optional[Customer]:
        """Get customer by telegram ID"""
        try:
            return get_customer_by_telegram_id(telegram_id)
        except Exception as e:
            logger.error("Exception getting customer: %s", e)
            return None

    def update_cart(
        self,
        telegram_id: int,
        items: List[Dict],
        delivery_method: Optional[str] = None,
        delivery_address: Optional[str] = None,
    ) -> bool:
        """Update cart with new items and delivery info"""
        try:
            success = update_cart(telegram_id, items, delivery_method, delivery_address)
            if success:
                logger.info("Successfully updated cart for user %s", telegram_id)
            else:
                logger.error("Failed to update cart for user %s", telegram_id)
            return success
        except Exception as e:
            logger.error("Exception updating cart: %s", e)
            return False 