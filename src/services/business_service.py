"""
Business service for core business operations with new schema fields.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.db.models import CoreBusiness
from src.db.operations import get_db_session

logger = logging.getLogger(__name__)

class BusinessService:
    """Service for core business operations with new schema fields"""

    def get_business_info(self) -> Optional[Dict[str, Any]]:
        """Get complete business information including new schema fields"""
        try:
            session = get_db_session()
            try:
                business = session.query(CoreBusiness).first()
                if not business:
                    logger.warning("No business configuration found")
                    return None
                
                business_data = {
                    "id": business.id,
                    "name": business.name,
                    "description": business.description,
                    "logo_url": business.logo_url,
                    "banner_url": business.banner_url,
                    "contact_phone": business.contact_phone,
                    "contact_email": business.contact_email,
                    "address": business.address,
                    "coordinates": business.coordinates,
                    "delivery_radius_km": float(business.delivery_radius_km) if business.delivery_radius_km else None,
                    "is_active": business.is_active,
                    "settings": business.settings or {},
                    "created_at": business.created_at.isoformat() if business.created_at else None,
                    "updated_at": business.updated_at.isoformat() if business.updated_at else None
                }
                
                logger.info("Retrieved business information")
                return business_data
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error("Failed to get business info: %s", e)
            return None

    def update_business_info(self, **kwargs) -> bool:
        """Update business information with new schema fields"""
        try:
            session = get_db_session()
            try:
                business = session.query(CoreBusiness).first()
                if not business:
                    logger.error("No business configuration found to update")
                    return False
                
                # Validate allowed fields
                allowed_fields = {
                    'name', 'description', 'logo_url', 'banner_url', 'contact_phone',
                    'contact_email', 'address', 'coordinates', 'delivery_radius_km',
                    'is_active', 'settings'
                }
                
                update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
                
                if not update_data:
                    logger.warning("No valid fields provided for business update")
                    return False
                
                # Update fields
                for field, value in update_data.items():
                    setattr(business, field, value)
                
                business.updated_at = datetime.utcnow()
                session.commit()
                
                logger.info("Successfully updated business information")
                return True
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error("Failed to update business info: %s", e)
            return False

    def get_delivery_info(self) -> Dict[str, Any]:
        """Get delivery-related business information"""
        try:
            business_info = self.get_business_info()
            if not business_info:
                return {}
            
            delivery_info = {
                "delivery_radius_km": business_info.get("delivery_radius_km"),
                "delivery_address": business_info.get("address"),
                "coordinates": business_info.get("coordinates"),
                "contact_phone": business_info.get("contact_phone"),
                "business_name": business_info.get("name")
            }
            
            logger.info("Retrieved delivery information")
            return delivery_info
            
        except Exception as e:
            logger.error("Failed to get delivery info: %s", e)
            return {}

    def get_contact_info(self) -> Dict[str, Any]:
        """Get contact information"""
        try:
            business_info = self.get_business_info()
            if not business_info:
                return {}
            
            contact_info = {
                "business_name": business_info.get("name"),
                "contact_phone": business_info.get("contact_phone"),
                "contact_email": business_info.get("contact_email"),
                "address": business_info.get("address")
            }
            
            logger.info("Retrieved contact information")
            return contact_info
            
        except Exception as e:
            logger.error("Failed to get contact info: %s", e)
            return {}

    def get_business_settings(self) -> Dict[str, Any]:
        """Get business settings from the settings JSON field"""
        try:
            business_info = self.get_business_info()
            if not business_info:
                return {}
            
            settings = business_info.get("settings", {})
            logger.info("Retrieved business settings")
            return settings
            
        except Exception as e:
            logger.error("Failed to get business settings: %s", e)
            return {}

    def update_business_settings(self, settings: Dict[str, Any]) -> bool:
        """Update business settings"""
        try:
            success = self.update_business_info(settings=settings)
            if success:
                logger.info("Successfully updated business settings")
            return success
            
        except Exception as e:
            logger.error("Failed to update business settings: %s", e)
            return False

    def get_business_images(self) -> Dict[str, Optional[str]]:
        """Get business logo and banner URLs"""
        try:
            business_info = self.get_business_info()
            if not business_info:
                return {}
            
            images = {
                "logo_url": business_info.get("logo_url"),
                "banner_url": business_info.get("banner_url")
            }
            
            logger.info("Retrieved business images")
            return images
            
        except Exception as e:
            logger.error("Failed to get business images: %s", e)
            return {}

    def update_business_images(self, logo_url: Optional[str] = None, banner_url: Optional[str] = None) -> bool:
        """Update business logo and banner URLs"""
        try:
            update_data = {}
            if logo_url is not None:
                update_data["logo_url"] = logo_url
            if banner_url is not None:
                update_data["banner_url"] = banner_url
            
            if not update_data:
                logger.warning("No image URLs provided for update")
                return False
            
            success = self.update_business_info(**update_data)
            if success:
                logger.info("Successfully updated business images")
            return success
            
        except Exception as e:
            logger.error("Failed to update business images: %s", e)
            return False

    def is_within_delivery_radius(self, customer_coordinates: str) -> bool:
        """Check if customer coordinates are within delivery radius"""
        try:
            business_info = self.get_business_info()
            if not business_info or not business_info.get("coordinates"):
                logger.warning("Business coordinates not available")
                return False
            
            # This is a simplified check - in a real implementation,
            # you would calculate the actual distance between coordinates
            business_coords = business_info.get("coordinates")
            delivery_radius = business_info.get("delivery_radius_km", 5.0)
            
            # For now, return True if coordinates exist (simplified logic)
            # In production, implement proper distance calculation
            logger.info("Checking delivery radius for coordinates: %s", customer_coordinates)
            return True  # Simplified for now
            
        except Exception as e:
            logger.error("Failed to check delivery radius: %s", e)
            return False

    def get_business_status(self) -> Dict[str, Any]:
        """Get business status and operational information"""
        try:
            business_info = self.get_business_info()
            if not business_info:
                return {"is_active": False, "error": "No business configuration found"}
            
            status = {
                "is_active": business_info.get("is_active", False),
                "business_name": business_info.get("name"),
                "has_logo": bool(business_info.get("logo_url")),
                "has_banner": bool(business_info.get("banner_url")),
                "has_contact_info": bool(business_info.get("contact_phone") or business_info.get("contact_email")),
                "has_address": bool(business_info.get("address")),
                "delivery_radius_km": business_info.get("delivery_radius_km"),
                "last_updated": business_info.get("updated_at")
            }
            
            logger.info("Retrieved business status")
            return status
            
        except Exception as e:
            logger.error("Failed to get business status: %s", e)
            return {"is_active": False, "error": str(e)} 