"""
Product service for enhanced product operations with new schema fields.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.db.models import Product, MenuCategory
from src.db.operations import (
    get_all_products,
    get_product_by_name,
    get_product_by_id,
    get_products_by_category,
    create_product,
    update_product,
    delete_product,
)

logger = logging.getLogger(__name__)

class ProductService:
    """Enhanced service for product operations with new schema fields"""

    def get_all_products_with_details(self) -> List[Dict[str, Any]]:
        """Get all products with enhanced details including new schema fields"""
        try:
            products = get_all_products()
            enhanced_products = []
            
            for product in products:
                product_data = {
                    "id": product.id,
                    "name": product.name,
                    "description": product.description,
                    "price": float(product.price),
                    "price_display": product.price_display,
                    "category": product.category,
                    "category_id": product.category_id,
                    "is_active": product.is_active,
                    "image_url": product.image_url,
                    "preparation_time_minutes": product.preparation_time_minutes,
                    "allergens": product.allergens or [],
                    "nutritional_info": product.nutritional_info or {},
                    "created_at": product.created_at.isoformat() if product.created_at else None,
                    "updated_at": product.updated_at.isoformat() if product.updated_at else None
                }
                enhanced_products.append(product_data)
            
            logger.info("Retrieved %d products with enhanced details", len(enhanced_products))
            return enhanced_products
            
        except Exception as e:
            logger.error("Failed to get products with details: %s", e)
            return []

    def get_products_by_category_with_details(self, category: str) -> List[Dict[str, Any]]:
        """Get products by category with enhanced details"""
        try:
            products = get_products_by_category(category)
            enhanced_products = []
            
            for product in products:
                product_data = {
                    "id": product.id,
                    "name": product.name,
                    "description": product.description,
                    "price": float(product.price),
                    "price_display": product.price_display,
                    "category": product.category,
                    "category_id": product.category_id,
                    "is_active": product.is_active,
                    "image_url": product.image_url,
                    "preparation_time_minutes": product.preparation_time_minutes,
                    "allergens": product.allergens or [],
                    "nutritional_info": product.nutritional_info or {},
                    "created_at": product.created_at.isoformat() if product.created_at else None,
                    "updated_at": product.updated_at.isoformat() if product.updated_at else None
                }
                enhanced_products.append(product_data)
            
            logger.info("Retrieved %d products for category '%s' with enhanced details", 
                       len(enhanced_products), category)
            return enhanced_products
            
        except Exception as e:
            logger.error("Failed to get products by category with details: %s", e)
            return []

    def get_product_details(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed product information including new schema fields"""
        try:
            product = get_product_by_id(product_id)
            if not product:
                logger.warning("Product with ID %d not found", product_id)
                return None
            
            product_data = {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "price": float(product.price),
                "price_display": product.price_display,
                "category": product.category,
                "category_id": product.category_id,
                "is_active": product.is_active,
                "image_url": product.image_url,
                "preparation_time_minutes": product.preparation_time_minutes,
                "allergens": product.allergens or [],
                "nutritional_info": product.nutritional_info or {},
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None
            }
            
            logger.info("Retrieved detailed product information for product %d", product_id)
            return product_data
            
        except Exception as e:
            logger.error("Failed to get product details: %s", e)
            return None

    def create_product_with_details(
        self,
        name: str,
        description: str,
        category: str,
        price: float,
        image_url: Optional[str] = None,
        preparation_time_minutes: Optional[int] = None,
        allergens: Optional[List[str]] = None,
        nutritional_info: Optional[Dict[str, Any]] = None,
        is_active: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Create a new product with enhanced details"""
        try:
            # Create the product using existing function
            product = create_product(name, description, category, price)
            if not product:
                logger.error("Failed to create product: %s", name)
                return None
            
            # Update with additional details
            update_data = {
                "image_url": image_url,
                "preparation_time_minutes": preparation_time_minutes,
                "allergens": allergens or [],
                "nutritional_info": nutritional_info or {},
                "is_active": is_active
            }
            
            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}
            
            if update_data:
                success = update_product(product.id, **update_data)
                if success:
                    # Get the updated product
                    updated_product = get_product_by_id(product.id)
                    if updated_product:
                        return self.get_product_details(updated_product.id)
            
            return self.get_product_details(product.id)
            
        except Exception as e:
            logger.error("Failed to create product with details: %s", e)
            return None

    def update_product_details(
        self,
        product_id: int,
        **kwargs
    ) -> bool:
        """Update product with enhanced details"""
        try:
            # Validate allowed fields
            allowed_fields = {
                'name', 'description', 'category', 'price', 'image_url',
                'preparation_time_minutes', 'allergens', 'nutritional_info', 'is_active'
            }
            
            update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
            
            if not update_data:
                logger.warning("No valid fields provided for product update")
                return False
            
            success = update_product(product_id, **update_data)
            if success:
                logger.info("Successfully updated product %d with details", product_id)
            else:
                logger.error("Failed to update product %d", product_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to update product details: %s", e)
            return False

    def get_products_by_allergen(self, allergen: str) -> List[Dict[str, Any]]:
        """Get products that contain a specific allergen"""
        try:
            products = get_all_products()
            filtered_products = []
            
            for product in products:
                if product.allergens and allergen.lower() in [a.lower() for a in product.allergens]:
                    product_data = self.get_product_details(product.id)
                    if product_data:
                        filtered_products.append(product_data)
            
            logger.info("Found %d products containing allergen '%s'", len(filtered_products), allergen)
            return filtered_products
            
        except Exception as e:
            logger.error("Failed to get products by allergen: %s", e)
            return []

    def get_products_by_preparation_time(self, max_minutes: int) -> List[Dict[str, Any]]:
        """Get products that can be prepared within specified time"""
        try:
            products = get_all_products()
            filtered_products = []
            
            for product in products:
                prep_time = product.preparation_time_minutes or 15  # Default to 15 minutes
                if prep_time <= max_minutes:
                    product_data = self.get_product_details(product.id)
                    if product_data:
                        filtered_products.append(product_data)
            
            logger.info("Found %d products with preparation time <= %d minutes", 
                       len(filtered_products), max_minutes)
            return filtered_products
            
        except Exception as e:
            logger.error("Failed to get products by preparation time: %s", e)
            return []

    def get_products_with_images(self) -> List[Dict[str, Any]]:
        """Get products that have image URLs"""
        try:
            products = get_all_products()
            products_with_images = []
            
            for product in products:
                if product.image_url:
                    product_data = self.get_product_details(product.id)
                    if product_data:
                        products_with_images.append(product_data)
            
            logger.info("Found %d products with images", len(products_with_images))
            return products_with_images
            
        except Exception as e:
            logger.error("Failed to get products with images: %s", e)
            return []

    def get_nutritional_summary(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get nutritional information summary for a product"""
        try:
            product = get_product_by_id(product_id)
            if not product or not product.nutritional_info:
                return None
            
            nutritional_info = product.nutritional_info
            
            # Create a summary with common nutritional fields
            summary = {
                "product_name": product.name,
                "calories": nutritional_info.get("calories"),
                "protein": nutritional_info.get("protein"),
                "carbohydrates": nutritional_info.get("carbohydrates"),
                "fat": nutritional_info.get("fat"),
                "fiber": nutritional_info.get("fiber"),
                "sugar": nutritional_info.get("sugar"),
                "sodium": nutritional_info.get("sodium"),
                "allergens": product.allergens or []
            }
            
            logger.info("Retrieved nutritional summary for product %d", product_id)
            return summary
            
        except Exception as e:
            logger.error("Failed to get nutritional summary: %s", e)
            return None 