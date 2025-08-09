"""
Image handling utilities for product images
"""

import logging
import os
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ImageHandler:
    """Handles product image operations"""
    
    # Default image URLs for different product categories
    DEFAULT_IMAGES = {
        "bread": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=300&fit=crop",
        "spice": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=300&fit=crop",
        "spread": "https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=400&h=300&fit=crop",
        "beverage": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=400&h=300&fit=crop",
        "other": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=300&fit=crop"
    }
    
    @staticmethod
    def validate_image_url(url: str) -> bool:
        """Validate if URL is a valid image URL"""
        if not url:
            return False
            
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc])
        except Exception:
            return False
    
    @staticmethod
    def get_default_image_for_category(category: str) -> str:
        """Get default image URL for a category"""
        return ImageHandler.DEFAULT_IMAGES.get(category.lower(), ImageHandler.DEFAULT_IMAGES["other"])
    
    @staticmethod
    def format_image_url(url: str, width: int = 400, height: int = 300) -> str:
        """Format image URL with size parameters (for services that support it)"""
        if not url:
            return ""
            
        # Add size parameters for supported services
        if "unsplash.com" in url:
            # Check if URL already has size parameters
            if "w=" in url and "h=" in url:
                # URL already has size parameters, return as is
                return url
            elif "?" in url:
                return f"{url}&w={width}&h={height}&fit=crop"
            else:
                return f"{url}?w={width}&h={height}&fit=crop"
        
        return url
    
    @staticmethod
    def get_product_image_url(product_image_url: Optional[str], category: str) -> str:
        """Get image URL for a product, with fallback to category default"""
        if product_image_url and ImageHandler.validate_image_url(product_image_url):
            return ImageHandler.format_image_url(product_image_url)
        
        return ImageHandler.get_default_image_for_category(category)


# Convenience functions
def get_product_image(product_image_url: Optional[str], category: str) -> str:
    """Get image URL for a product"""
    return ImageHandler.get_product_image_url(product_image_url, category)


def validate_image_url(url: str) -> bool:
    """Validate image URL"""
    return ImageHandler.validate_image_url(url)


def get_default_category_image(category: str) -> str:
    """Get default image for a category"""
    return ImageHandler.get_default_image_for_category(category) 


# Step-level illustrative images for key interaction steps.
# Replace these with your own branded assets/CDN if available.
STEP_IMAGES = {
    "welcome": "https://images.unsplash.com/photo-1541976076758-347942db197a",
    "language": "https://images.unsplash.com/photo-1520975916090-3105956dac38",
    "onboarding_choice": "https://images.unsplash.com/photo-1512428559087-560fa5ceab42",
    "enter_name": "https://images.unsplash.com/photo-1544006659-f0b21884ce1d",
    "enter_phone": "https://images.unsplash.com/photo-1512496015851-a90fb38ba796",
    "enter_address": "https://images.unsplash.com/photo-1501183638710-841dd1904471",
    "registration_complete": "https://images.unsplash.com/photo-1444065381814-865dc9da92c0",
    "main_page": "https://images.unsplash.com/photo-1498579150354-977475b7ea0b",
    "menu": "https://images.unsplash.com/photo-1559056199-641a0ac8b55e",
    "my_info": "https://images.unsplash.com/photo-1502989642968-94fbdc9eace4",
    "view_cart": "https://images.unsplash.com/photo-1542838132-92c53300491e",
    "add_success": "https://images.unsplash.com/photo-1478147427282-58a87a120781",
    "clear_cart_confirm": "https://images.unsplash.com/photo-1557821552-17105176677c",
    "cart_cleared": "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f",
    "checkout": "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4",
    "delivery_method": "https://images.unsplash.com/photo-1597074866927-3b1b8e55b8d1",
    "delivery_address_choice": "https://images.unsplash.com/photo-1462332420958-a05d1e002413",
    "confirm_order": "https://images.unsplash.com/photo-1440404653325-ab127d49abc1",
    "order_confirmed": "https://images.unsplash.com/photo-1461360370896-922624d12aa1",
    "contact_us": "https://images.unsplash.com/photo-1520975916090-3105956dac38",
    "track_orders": "https://images.unsplash.com/photo-1536148935331-408321065b18",
}


def get_step_image(step_key: str, width: int = 900, height: int = 600) -> str:
    """Return a formatted illustrative image URL for a given interaction step.
    Checks DB overrides in business settings (app_images) before falling back.
    Includes alias support so a generic 'welcome' override can be used for
    early customer views like the main page and registration complete.
    """
    # Try DB overrides
    try:
        from src.db.operations import get_business_settings_dict  # lazy import to avoid cycles
        settings = get_business_settings_dict() or {}
        overrides = settings.get("app_images")
        # Parse JSON string if needed
        if isinstance(overrides, str):
            import json
            try:
                overrides = json.loads(overrides)
            except Exception:
                overrides = None
        if isinstance(overrides, dict):
            # 1) Exact key override
            override_url = overrides.get(step_key)
            if override_url and ImageHandler.validate_image_url(override_url):
                return ImageHandler.format_image_url(override_url, width, height)

            # 2) Alias fallbacks: allow 'welcome' to drive certain early steps
            alias_map = {
                "main_page": ["welcome"],
                "registration_complete": ["welcome"],
            }
            for alias in alias_map.get(step_key, []):
                alias_url = overrides.get(alias)
                if alias_url and ImageHandler.validate_image_url(alias_url):
                    return ImageHandler.format_image_url(alias_url, width, height)
    except Exception:
        # Silently ignore override errors and fall back to defaults
        pass

    url = STEP_IMAGES.get(step_key)
    return ImageHandler.format_image_url(url, width, height) if url else ""


def list_step_image_keys() -> list[str]:
    """Return list of available step image keys for admin UI."""
    try:
        return list(STEP_IMAGES.keys())
    except Exception:
        return []