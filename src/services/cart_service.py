"""
Cart management service
"""

import logging
from typing import List, Dict, Optional, Any

from src.db.operations import (
    update_cart,
    get_customer_by_telegram_id,
    get_or_create_customer,
    get_cart_by_telegram_id,
    update_customer_delivery_address,
)
from src.db.operations import (
    add_to_cart,
    get_cart_items,
    clear_cart,
    remove_from_cart,
    ACIDComplianceChecker
)
from src.db.models import Customer

logger = logging.getLogger(__name__)


class CartService:
    """Service for cart management operations"""

    def validate_customer_data(self, full_name: str, phone: str) -> Dict[str, Any]:
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

    def register_customer(self, telegram_id: int, full_name: str, phone: str, language: str = "en") -> Dict[str, Any]:
        """Register a new customer or update existing one"""
        try:
            # Check if customer already exists
            existing_customer = get_customer_by_telegram_id(telegram_id)
            
            if existing_customer:
                # Update existing customer with new information and language
                from src.db.operations import update_customer_language
                existing_customer.name = full_name
                existing_customer.phone = phone
                # Update language in database
                update_customer_language(telegram_id, language)
                return {
                    "success": True,
                    "customer": existing_customer,
                    "is_returning": True
                }
            else:
                # Create new customer
                customer = get_or_create_customer(telegram_id, full_name, phone, language)
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
        """Add item to cart using ACID operations"""
        try:
            logger.info("Adding item to cart (ACID): telegram_id=%s, product_id=%s, quantity=%s", 
                       telegram_id, product_id, quantity)
            
            # Use atomic cart addition
            success = add_to_cart(telegram_id, product_id, quantity, options or {})
            
            if success:
                logger.info("Successfully added item to cart (ACID) for user %s", telegram_id)
                
                # Verify cart consistency after operation
                is_consistent, issues = ACIDComplianceChecker.check_cart_consistency(telegram_id)
                if not is_consistent:
                    logger.warning("Cart consistency issues detected after add: %s", issues)
                
            else:
                logger.error("Failed to add item to cart (ACID) for user %s", telegram_id)
            
            return success
            
        except Exception as e:
            logger.error("Exception adding item to cart (ACID): %s", e)
            return False

    def get_items(self, telegram_id: int) -> List[Dict]:
        """Get cart items for user using ACID operations"""
        try:
            items = get_cart_items(telegram_id)
            logger.info("Retrieved %d items from cart (ACID) for user %s", len(items), telegram_id)
            return items
        except Exception as e:
            logger.error("Exception getting cart items (ACID): %s", e)
            return []

    def calculate_total(self, items: List[Dict]) -> float:
        """Calculate total price of cart items"""
        try:
            total = sum(item.get("unit_price", 0) * item.get("quantity", 1) for item in items)
            logger.info("Calculated cart total: %.2f", total)
            return total
        except Exception as e:
            logger.error("Exception calculating cart total: %s", e)
            return 0.0

    def clear_cart(self, telegram_id: int) -> bool:
        """Clear all items from cart using ACID operations"""
        try:
            logger.info("Clearing cart (ACID) for user %s", telegram_id)
            
            # Use atomic cart clearing
            success = clear_cart(telegram_id)
            
            if success:
                logger.info("Successfully cleared cart (ACID) for user %s", telegram_id)
            else:
                logger.error("Failed to clear cart (ACID) for user %s", telegram_id)
            
            return success
            
        except Exception as e:
            logger.error("Exception clearing cart (ACID): %s", e)
            return False

    def remove_item(self, telegram_id: int, product_id: int) -> bool:
        """Remove item from cart using ACID operations"""
        try:
            logger.info("Removing item from cart (ACID): telegram_id=%s, product_id=%s", 
                       telegram_id, product_id)
            
            # Use atomic cart item removal
            success = remove_from_cart(telegram_id, product_id)
            
            if success:
                logger.info("Successfully removed item from cart (ACID) for user %s", telegram_id)
            else:
                logger.error("Failed to remove item from cart (ACID) for user %s", telegram_id)
            
            return success
            
        except Exception as e:
            logger.error("Exception removing item from cart (ACID): %s", e)
            return False

    def update_item_quantity(self, telegram_id: int, product_id: int, new_quantity: int) -> bool:
        """Update item quantity in cart using ACID operations"""
        try:
            logger.info("Updating item quantity (ACID): telegram_id=%s, product_id=%s, quantity=%s", 
                       telegram_id, product_id, new_quantity)
            
            if new_quantity <= 0:
                # If quantity is 0 or negative, remove the item
                return self.remove_item(telegram_id, product_id)
            
            # Get current cart items
            current_items = self.get_items(telegram_id)
            
            # Find the item to update
            updated_items = []
            item_found = False
            
            for item in current_items:
                if item.get("product_id") == product_id:
                    # Update the quantity
                    updated_item = item.copy()
                    updated_item["quantity"] = new_quantity
                    updated_item["total_price"] = item.get("unit_price", 0) * new_quantity
                    updated_items.append(updated_item)
                    item_found = True
                else:
                    updated_items.append(item)
            
            if not item_found:
                logger.warning("Item not found in cart for update: telegram_id=%s, product_id=%s", 
                             telegram_id, product_id)
                return False
            
            # Update the cart with new items
            success = self.update_cart(telegram_id, updated_items)
            
            if success:
                logger.info("Successfully updated item quantity (ACID) for user %s", telegram_id)
            else:
                logger.error("Failed to update item quantity (ACID) for user %s", telegram_id)
            
            return success
            
        except Exception as e:
            logger.error("Exception updating item quantity (ACID): %s", e)
            return False

    def get_item_by_id(self, telegram_id: int, product_id: int) -> Optional[Dict]:
        """Get specific item from cart by product ID"""
        try:
            items = self.get_items(telegram_id)
            for item in items:
                if item.get("product_id") == product_id:
                    return item
            return None
        except Exception as e:
            logger.error("Exception getting item by ID: %s", e)
            return None

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

    def set_delivery_method(self, telegram_id: int, delivery_method: str) -> bool:
        """Set delivery method for cart"""
        try:
            # Get current cart items
            current_items = self.get_items(telegram_id)
            if not current_items:
                logger.error("No items in cart for user %s", telegram_id)
                return False
            
            # Update cart with delivery method
            success = self.update_cart(telegram_id, current_items, delivery_method)
            if success:
                logger.info("Successfully set delivery method '%s' for user %s", delivery_method, telegram_id)
            else:
                logger.error("Failed to set delivery method for user %s", telegram_id)
            return success
        except Exception as e:
            logger.error("Exception setting delivery method: %s", e)
            return False

    def set_delivery_address(self, telegram_id: int, delivery_address: str) -> bool:
        """Set delivery address for cart"""
        try:
            # Get current cart items
            current_items = self.get_items(telegram_id)
            if not current_items:
                logger.error("No items in cart for user %s", telegram_id)
                return False
            
            # Update cart with delivery address
            success = self.update_cart(telegram_id, current_items, None, delivery_address)
            if success:
                logger.info("Successfully set delivery address for user %s", telegram_id)
            else:
                logger.error("Failed to set delivery address for user %s", telegram_id)
            return success
        except Exception as e:
            logger.error("Exception setting delivery address: %s", e)
            return False

    def get_cart_info(self, telegram_id: int) -> Dict:
        """Get cart information including customer, items, and totals"""
        try:
            customer = self.get_customer(telegram_id)
            items = self.get_items(telegram_id)
            total = self.calculate_total(items)
            
            return {
                "customer": customer,
                "items": items,
                "total": total,
                "item_count": len(items)
            }
        except Exception as e:
            logger.error("Exception getting cart info: %s", e)
            return {
                "customer": None,
                "items": [],
                "total": 0.0,
                "item_count": 0
            }

    def update_customer_delivery_address(self, telegram_id: int, delivery_address: str) -> bool:
        """Update customer's delivery address in database"""
        try:
            success = update_customer_delivery_address(telegram_id, delivery_address)
            if success:
                logger.info("Successfully updated customer delivery address for user %s", telegram_id)
            else:
                logger.error("Failed to update customer delivery address for user %s", telegram_id)
            return success
        except Exception as e:
            logger.error("Exception updating customer delivery address: %s", e)
            return False

    def check_cart_consistency(self, telegram_id: int) -> Dict[str, Any]:
        """
        Check cart consistency using ACID compliance checker
        
        Returns:
            Dictionary with consistency status and any issues found
        """
        try:
            is_consistent, issues = ACIDComplianceChecker.check_cart_consistency(telegram_id)
            
            return {
                "consistent": is_consistent,
                "issues": issues,
                "telegram_id": telegram_id
            }
            
        except Exception as e:
            logger.error("Exception checking cart consistency: %s", e)
            return {
                "consistent": False,
                "issues": [f"Error checking consistency: {e}"],
                "telegram_id": telegram_id
            } 