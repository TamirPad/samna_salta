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