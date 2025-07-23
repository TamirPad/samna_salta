"""
Constants Manager for handling database-driven constants

This module provides utilities to replace hardcoded constants in locale files
with database-driven values that support multilingual content.
"""

import logging
from typing import Optional, Dict, List, Any
from src.db.operations import (
    get_product_options,
    get_product_sizes,
    get_order_statuses,
    get_delivery_methods,
    get_payment_methods,
    get_localized_constant,
    get_delivery_charge
)

logger = logging.getLogger(__name__)


class ConstantsManager:
    """Manager for database-driven constants"""
    
    def __init__(self):
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes cache
    
    def get_product_option_display_name(self, option_name: str, option_type: str, language: str = "en") -> str:
        """Get localized display name for a product option"""
        try:
            # Try to get from database first
            option = get_localized_constant("product_option", option_name, language)
            if option:
                return option
            
            # Fallback to hardcoded values if database lookup fails
            fallback_values = {
                "kubaneh_type": {
                    "classic": {"en": "Classic", "he": "קלאסית"},
                    "seeded": {"en": "Seeded", "he": "עם זרעים"},
                    "herb": {"en": "Herb", "he": "עשבי תיבול"},
                    "aromatic": {"en": "Aromatic", "he": "ארומטי"}
                },
                "samneh_type": {
                    "classic": {"en": "Classic", "he": "קלאסי"},
                    "spicy": {"en": "Spicy", "he": "חריף"},
                    "herb": {"en": "Herb", "he": "עשבי תיבול"},
                    "honey": {"en": "Honey", "he": "דבש"},
                    "smoked": {"en": "Smoked", "he": "מעושן"},
                    "not_smoked": {"en": "Not Smoked", "he": "לא מעושן"}
                },
                "hilbeh_type": {
                    "classic": {"en": "Classic", "he": "קלאסי"},
                    "spicy": {"en": "Spicy", "he": "חריף"},
                    "sweet": {"en": "Sweet", "he": "מתוק"},
                    "premium": {"en": "Premium", "he": "פרימיום"}
                }
            }
            
            if option_type in fallback_values and option_name in fallback_values[option_type]:
                return fallback_values[option_type][option_name].get(language, option_name)
            
            return option_name
            
        except Exception as e:
            logger.error(f"Error getting product option display name: {e}")
            return option_name
    
    def get_product_size_display_name(self, size_name: str, language: str = "en") -> str:
        """Get localized display name for a product size"""
        try:
            # Try to get from database first
            size = get_localized_constant("product_size", size_name, language)
            if size:
                return size
            
            # Fallback to hardcoded values
            fallback_values = {
                "small": {"en": "Small", "he": "קטן"},
                "medium": {"en": "Medium", "he": "בינוני"},
                "large": {"en": "Large", "he": "גדול"},
                "xl": {"en": "Extra Large", "he": "גדול מאוד"}
            }
            
            if size_name in fallback_values:
                return fallback_values[size_name].get(language, size_name)
            
            return size_name
            
        except Exception as e:
            logger.error(f"Error getting product size display name: {e}")
            return size_name
    
    def get_order_status_display_name(self, status_name: str, language: str = "en") -> str:
        """Get localized display name for an order status"""
        try:
            # Try to get from database first
            status = get_localized_constant("order_status", status_name, language)
            if status:
                return status
            
            # Fallback to hardcoded values
            fallback_values = {
                "pending": {"en": "Pending", "he": "ממתין"},
                "confirmed": {"en": "Confirmed", "he": "אושר"},
                "preparing": {"en": "Preparing", "he": "בהכנה"},
                "ready": {"en": "Ready", "he": "מוכן"},
                "delivered": {"en": "Delivered", "he": "נמסר"},
                "cancelled": {"en": "Cancelled", "he": "בוטל"}
            }
            
            if status_name in fallback_values:
                return fallback_values[status_name].get(language, status_name)
            
            return status_name
            
        except Exception as e:
            logger.error(f"Error getting order status display name: {e}")
            return status_name
    
    def get_delivery_method_display_name(self, method_name: str, language: str = "en") -> str:
        """Get localized display name for a delivery method"""
        try:
            # Try to get from database first
            method = get_localized_constant("delivery_method", method_name, language)
            if method:
                return method
            
            # Fallback to hardcoded values
            fallback_values = {
                "pickup": {"en": "Pickup (Free)", "he": "איסוף עצמי (חינם)"},
                "delivery": {"en": "Delivery (+5 ₪)", "he": "משלוח (+5 ₪)"}
            }
            
            if method_name in fallback_values:
                return fallback_values[method_name].get(language, method_name)
            
            return method_name
            
        except Exception as e:
            logger.error(f"Error getting delivery method display name: {e}")
            return method_name
    
    def get_payment_method_display_name(self, method_name: str, language: str = "en") -> str:
        """Get localized display name for a payment method"""
        try:
            # Try to get from database first
            method = get_localized_constant("payment_method", method_name, language)
            if method:
                return method
            
            # Fallback to hardcoded values
            fallback_values = {
                "cash": {"en": "Cash", "he": "מזומן"}
            }
            
            if method_name in fallback_values:
                return fallback_values[method_name].get(language, method_name)
            
            return method_name
            
        except Exception as e:
            logger.error(f"Error getting payment method display name: {e}")
            return method_name
    
    def get_delivery_charge_amount(self, method_name: str) -> float:
        """Get delivery charge amount for a method"""
        try:
            return get_delivery_charge(method_name)
        except Exception as e:
            logger.error(f"Error getting delivery charge: {e}")
            # Fallback to hardcoded values
            fallback_charges = {
                "pickup": 0.0,
                "delivery": 5.0
            }
            return fallback_charges.get(method_name, 0.0)
    
    def format_product_display_name(self, product_name: str, options: Dict[str, str] = None, language: str = "en") -> str:
        """Format product display name with options"""
        if not options:
            return product_name
        
        option_parts = []
        
        # Handle different product types
        if "kubaneh_type" in options:
            option_name = self.get_product_option_display_name(options["kubaneh_type"], "kubaneh_type", language)
            option_parts.append(option_name)
        
        if "samneh_type" in options:
            option_name = self.get_product_option_display_name(options["samneh_type"], "samneh_type", language)
            option_parts.append(option_name)
        
        if "hilbeh_type" in options:
            option_name = self.get_product_option_display_name(options["hilbeh_type"], "hilbeh_type", language)
            option_parts.append(option_name)
        
        if "size" in options:
            size_name = self.get_product_size_display_name(options["size"], language)
            option_parts.append(size_name)
        
        if option_parts:
            return f"{product_name} ({', '.join(option_parts)})"
        
        return product_name
    
    def get_all_product_options(self, option_type: Optional[str] = None, language: str = "en") -> List[Dict]:
        """Get all product options"""
        try:
            return get_product_options(option_type, language)
        except Exception as e:
            logger.error(f"Error getting product options: {e}")
            return []
    
    def get_all_product_sizes(self, language: str = "en") -> List[Dict]:
        """Get all product sizes"""
        try:
            return get_product_sizes(language)
        except Exception as e:
            logger.error(f"Error getting product sizes: {e}")
            return []
    
    def get_all_order_statuses(self, language: str = "en") -> List[Dict]:
        """Get all order statuses"""
        try:
            return get_order_statuses(language)
        except Exception as e:
            logger.error(f"Error getting order statuses: {e}")
            return []
    
    def get_all_delivery_methods(self, language: str = "en") -> List[Dict]:
        """Get all delivery methods"""
        try:
            return get_delivery_methods(language)
        except Exception as e:
            logger.error(f"Error getting delivery methods: {e}")
            return []
    
    def get_all_payment_methods(self, language: str = "en") -> List[Dict]:
        """Get all payment methods"""
        try:
            return get_payment_methods(language)
        except Exception as e:
            logger.error(f"Error getting payment methods: {e}")
            return []


# Global instance
constants_manager = ConstantsManager()


# Convenience functions for backward compatibility
def get_product_option_name(option_name: str, option_type: str, user_id: Optional[int] = None) -> str:
    """Get product option display name"""
    language = "en"
    if user_id:
        from src.utils.language_manager import language_manager
        language = language_manager.get_user_language(user_id)
    return constants_manager.get_product_option_display_name(option_name, option_type, language)


def get_product_size_name(size_name: str, user_id: Optional[int] = None) -> str:
    """Get product size display name"""
    language = "en"
    if user_id:
        from src.utils.language_manager import language_manager
        language = language_manager.get_user_language(user_id)
    return constants_manager.get_product_size_display_name(size_name, language)


def get_order_status_name(status_name: str, user_id: Optional[int] = None) -> str:
    """Get order status display name"""
    language = "en"
    if user_id:
        from src.utils.language_manager import language_manager
        language = language_manager.get_user_language(user_id)
    return constants_manager.get_order_status_display_name(status_name, language)


def get_delivery_method_name(method_name: str, user_id: Optional[int] = None) -> str:
    """Get delivery method display name"""
    language = "en"
    if user_id:
        from src.utils.language_manager import language_manager
        language = language_manager.get_user_language(user_id)
    return constants_manager.get_delivery_method_display_name(method_name, language)


def get_payment_method_name(method_name: str, user_id: Optional[int] = None) -> str:
    """Get payment method display name"""
    language = "en"
    if user_id:
        from src.utils.language_manager import language_manager
        language = language_manager.get_user_language(user_id)
    return constants_manager.get_payment_method_display_name(method_name, language)


def get_delivery_charge_for_method(method_name: str) -> float:
    """Get delivery charge for method"""
    return constants_manager.get_delivery_charge_amount(method_name)


def format_product_name_with_options(product_name: str, options: Dict[str, str] = None, language: str = "en") -> str:
    """Format product name with options"""
    return constants_manager.format_product_display_name(product_name, options, language) 