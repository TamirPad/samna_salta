#!/usr/bin/env python3
"""
Database seeding script for constants that were previously hardcoded in locale files.

This script populates the new database tables with default values for:
- Product Options (Kubaneh types, Samneh types, etc.)
- Product Sizes (Small, Medium, Large, XL)
- Order Statuses (Pending, Confirmed, Preparing, etc.)
- Delivery Methods (Pickup, Delivery)
- Payment Methods (Cash, etc.)
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import (
    ProductOption, ProductSize, OrderStatus, DeliveryMethod, PaymentMethod,
    Base
)
from config import get_database_url

def create_session():
    """Create database session"""
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session()

def seed_product_options(session):
    """Seed product options table"""
    print("Seeding product options...")
    
    options_data = [
        # Kubaneh types
        {
            "name": "classic",
            "display_name": "Classic",
            "option_type": "kubaneh_type",
            "price_modifier": 0.0,
            "display_order": 1,
            "name_en": "Classic",
            "name_he": "קלאסית",
            "display_name_en": "Classic",
            "display_name_he": "קלאסית",
            "description_en": "Traditional Yemeni kubaneh",
            "description_he": "קובנה תימני מסורתי"
        },
        {
            "name": "seeded",
            "display_name": "Seeded",
            "option_type": "kubaneh_type",
            "price_modifier": 3.0,
            "display_order": 2,
            "name_en": "Seeded",
            "name_he": "עם זרעים",
            "display_name_en": "Seeded",
            "display_name_he": "עם זרעים",
            "description_en": "Kubaneh with sesame and cumin seeds",
            "description_he": "קובנה עם זרעי שומשום וכמון"
        },
        {
            "name": "herb",
            "display_name": "Herb",
            "option_type": "kubaneh_type",
            "price_modifier": 5.0,
            "display_order": 3,
            "name_en": "Herb",
            "name_he": "עשבי תיבול",
            "display_name_en": "Herb",
            "display_name_he": "עשבי תיבול",
            "description_en": "Kubaneh with aromatic herbs",
            "description_he": "קובנה עם עשבי תיבול ארומטיים"
        },
        {
            "name": "aromatic",
            "display_name": "Aromatic",
            "option_type": "kubaneh_type",
            "price_modifier": 7.0,
            "display_order": 4,
            "name_en": "Aromatic",
            "name_he": "ארומטי",
            "display_name_en": "Aromatic",
            "display_name_he": "ארומטי",
            "description_en": "Kubaneh with special spices",
            "description_he": "קובנה עם תבלינים מיוחדים"
        },
        
        # Samneh types
        {
            "name": "classic",
            "display_name": "Classic",
            "option_type": "samneh_type",
            "price_modifier": 0.0,
            "display_order": 1,
            "name_en": "Classic",
            "name_he": "קלאסי",
            "display_name_en": "Classic",
            "display_name_he": "קלאסי",
            "description_en": "Traditional Yemeni clarified butter",
            "description_he": "חמאה מובהרת תימנית מסורתית"
        },
        {
            "name": "spicy",
            "display_name": "Spicy",
            "option_type": "samneh_type",
            "price_modifier": 3.0,
            "display_order": 2,
            "name_en": "Spicy",
            "name_he": "חריף",
            "display_name_en": "Spicy",
            "display_name_he": "חריף",
            "description_en": "Spicy clarified butter",
            "description_he": "חמאה מובהרת חריפה"
        },
        {
            "name": "herb",
            "display_name": "Herb",
            "option_type": "samneh_type",
            "price_modifier": 5.0,
            "display_order": 3,
            "name_en": "Herb",
            "name_he": "עשבי תיבול",
            "display_name_en": "Herb",
            "display_name_he": "עשבי תיבול",
            "description_en": "Herb-infused clarified butter",
            "description_he": "חמאה מובהרת עם עשבי תיבול"
        },
        {
            "name": "honey",
            "display_name": "Honey",
            "option_type": "samneh_type",
            "price_modifier": 7.0,
            "display_order": 4,
            "name_en": "Honey",
            "name_he": "דבש",
            "display_name_en": "Honey",
            "display_name_he": "דבש",
            "description_en": "Honey-infused clarified butter",
            "description_he": "חמאה מובהרת עם דבש"
        },
        {
            "name": "smoked",
            "display_name": "Smoked",
            "option_type": "samneh_type",
            "price_modifier": 3.0,
            "display_order": 5,
            "name_en": "Smoked",
            "name_he": "מעושן",
            "display_name_en": "Smoked",
            "display_name_he": "מעושן",
            "description_en": "Smoked clarified butter",
            "description_he": "חמאה מובהרת מעושנת"
        },
        {
            "name": "not_smoked",
            "display_name": "Not Smoked",
            "option_type": "samneh_type",
            "price_modifier": 0.0,
            "display_order": 6,
            "name_en": "Not Smoked",
            "name_he": "לא מעושן",
            "display_name_en": "Not Smoked",
            "display_name_he": "לא מעושן",
            "description_en": "Pure and natural clarified butter",
            "description_he": "חמאה מובהרת טהורה וטבעית"
        },
        
        # Hilbeh types
        {
            "name": "classic",
            "display_name": "Classic",
            "option_type": "hilbeh_type",
            "price_modifier": 0.0,
            "display_order": 1,
            "name_en": "Classic",
            "name_he": "קלאסי",
            "display_name_en": "Classic",
            "display_name_he": "קלאסי",
            "description_en": "Traditional Yemeni hilbeh",
            "description_he": "חילבה תימנית מסורתית"
        },
        {
            "name": "spicy",
            "display_name": "Spicy",
            "option_type": "hilbeh_type",
            "price_modifier": 2.0,
            "display_order": 2,
            "name_en": "Spicy",
            "name_he": "חריף",
            "display_name_en": "Spicy",
            "display_name_he": "חריף",
            "description_en": "Spicy hilbeh",
            "description_he": "חילבה חריפה"
        },
        {
            "name": "sweet",
            "display_name": "Sweet",
            "option_type": "hilbeh_type",
            "price_modifier": 4.0,
            "display_order": 3,
            "name_en": "Sweet",
            "name_he": "מתוק",
            "display_name_en": "Sweet",
            "display_name_he": "מתוק",
            "description_en": "Sweet hilbeh",
            "description_he": "חילבה מתוקה"
        },
        {
            "name": "premium",
            "display_name": "Premium",
            "option_type": "hilbeh_type",
            "price_modifier": 6.0,
            "display_order": 4,
            "name_en": "Premium",
            "name_he": "פרימיום",
            "display_name_en": "Premium",
            "display_name_he": "פרימיום",
            "description_en": "Premium hilbeh",
            "description_he": "חילבה פרימיום"
        }
    ]
    
    for option_data in options_data:
        existing = session.query(ProductOption).filter_by(
            name=option_data["name"], 
            option_type=option_data["option_type"]
        ).first()
        
        if not existing:
            option = ProductOption(**option_data)
            session.add(option)
            print(f"  Added {option_data['option_type']}: {option_data['name']}")
        else:
            print(f"  Skipped {option_data['option_type']}: {option_data['name']} (already exists)")
    
    session.commit()

def seed_product_sizes(session):
    """Seed product sizes table"""
    print("Seeding product sizes...")
    
    sizes_data = [
        {
            "name": "small",
            "display_name": "Small",
            "price_modifier": 0.0,
            "display_order": 1,
            "name_en": "Small",
            "name_he": "קטן",
            "display_name_en": "Small",
            "display_name_he": "קטן"
        },
        {
            "name": "medium",
            "display_name": "Medium",
            "price_modifier": 3.0,
            "display_order": 2,
            "name_en": "Medium",
            "name_he": "בינוני",
            "display_name_en": "Medium",
            "display_name_he": "בינוני"
        },
        {
            "name": "large",
            "display_name": "Large",
            "price_modifier": 6.0,
            "display_order": 3,
            "name_en": "Large",
            "name_he": "גדול",
            "display_name_en": "Large",
            "display_name_he": "גדול"
        },
        {
            "name": "xl",
            "display_name": "Extra Large",
            "price_modifier": 10.0,
            "display_order": 4,
            "name_en": "Extra Large",
            "name_he": "גדול מאוד",
            "display_name_en": "Extra Large",
            "display_name_he": "גדול מאוד"
        }
    ]
    
    for size_data in sizes_data:
        existing = session.query(ProductSize).filter_by(name=size_data["name"]).first()
        
        if not existing:
            size = ProductSize(**size_data)
            session.add(size)
            print(f"  Added size: {size_data['name']}")
        else:
            print(f"  Skipped size: {size_data['name']} (already exists)")
    
    session.commit()

def seed_order_statuses(session):
    """Seed order statuses table"""
    print("Seeding order statuses...")
    
    statuses_data = [
        {
            "name": "pending",
            "display_name": "Pending",
            "description": "Order is pending confirmation",
            "color": "yellow",
            "icon": "⏳",
            "display_order": 1,
            "name_en": "Pending",
            "name_he": "ממתין",
            "display_name_en": "Pending",
            "display_name_he": "ממתין",
            "description_en": "Order is pending confirmation",
            "description_he": "ההזמנה ממתינה לאישור"
        },
        {
            "name": "confirmed",
            "display_name": "Confirmed",
            "description": "Order has been confirmed",
            "color": "blue",
            "icon": "✅",
            "display_order": 2,
            "name_en": "Confirmed",
            "name_he": "אושר",
            "display_name_en": "Confirmed",
            "display_name_he": "אושר",
            "description_en": "Order has been confirmed and is being prepared",
            "description_he": "ההזמנה אושרה ונמצאת בהכנה"
        },
        {
            "name": "preparing",
            "display_name": "Preparing",
            "description": "Order is being prepared",
            "color": "orange",
            "icon": "👨‍🍳",
            "display_order": 3,
            "name_en": "Preparing",
            "name_he": "בהכנה",
            "display_name_en": "Preparing",
            "display_name_he": "בהכנה",
            "description_en": "Order is being prepared in the kitchen",
            "description_he": "ההזמנה מוכנה במטבח"
        },
        {
            "name": "ready",
            "display_name": "Ready",
            "description": "Order is ready for pickup/delivery",
            "color": "green",
            "icon": "🎉",
            "display_order": 4,
            "name_en": "Ready",
            "name_he": "מוכן",
            "display_name_en": "Ready",
            "display_name_he": "מוכן",
            "description_en": "Order is ready for pickup or delivery",
            "description_he": "ההזמנה מוכנה לאיסוף או משלוח"
        },
        {
            "name": "delivered",
            "display_name": "Delivered",
            "description": "Order has been delivered",
            "color": "green",
            "icon": "🚚",
            "display_order": 5,
            "name_en": "Delivered",
            "name_he": "נמסר",
            "display_name_en": "Delivered",
            "display_name_he": "נמסר",
            "description_en": "Order has been delivered successfully",
            "description_he": "ההזמנה נמסרה בהצלחה"
        },
        {
            "name": "cancelled",
            "display_name": "Cancelled",
            "description": "Order has been cancelled",
            "color": "red",
            "icon": "❌",
            "display_order": 6,
            "name_en": "Cancelled",
            "name_he": "בוטל",
            "display_name_en": "Cancelled",
            "display_name_he": "בוטל",
            "description_en": "Order has been cancelled",
            "description_he": "ההזמנה בוטלה"
        }
    ]
    
    for status_data in statuses_data:
        existing = session.query(OrderStatus).filter_by(name=status_data["name"]).first()
        
        if not existing:
            status = OrderStatus(**status_data)
            session.add(status)
            print(f"  Added status: {status_data['name']}")
        else:
            print(f"  Skipped status: {status_data['name']} (already exists)")
    
    session.commit()

def seed_delivery_methods(session):
    """Seed delivery methods table"""
    print("Seeding delivery methods...")
    
    methods_data = [
        {
            "name": "pickup",
            "display_name": "Pickup",
            "description": "Customer picks up the order",
            "charge": 0.0,
            "display_order": 1,
            "name_en": "Pickup",
            "name_he": "איסוף עצמי",
            "display_name_en": "Pickup (Free)",
            "display_name_he": "איסוף עצמי (חינם)",
            "description_en": "Customer picks up the order from our location",
            "description_he": "הלקוח אוסף את ההזמנה מהמיקום שלנו"
        },
        {
            "name": "delivery",
            "display_name": "Delivery",
            "description": "Order is delivered to customer",
            "charge": 5.0,
            "display_order": 2,
            "name_en": "Delivery",
            "name_he": "משלוח",
            "display_name_en": "Delivery (+5 ₪)",
            "display_name_he": "משלוח (+5 ₪)",
            "description_en": "Order is delivered to customer's address",
            "description_he": "ההזמנה נמסרת לכתובת הלקוח"
        }
    ]
    
    for method_data in methods_data:
        existing = session.query(DeliveryMethod).filter_by(name=method_data["name"]).first()
        
        if not existing:
            method = DeliveryMethod(**method_data)
            session.add(method)
            print(f"  Added delivery method: {method_data['name']}")
        else:
            print(f"  Skipped delivery method: {method_data['name']} (already exists)")
    
    session.commit()

def seed_payment_methods(session):
    """Seed payment methods table"""
    print("Seeding payment methods...")
    
    methods_data = [
        {
            "name": "cash",
            "display_name": "Cash",
            "description": "Cash on delivery/pickup",
            "display_order": 1,
            "name_en": "Cash",
            "name_he": "מזומן",
            "display_name_en": "Cash",
            "display_name_he": "מזומן",
            "description_en": "Cash payment on delivery or pickup",
            "description_he": "תשלום במזומן במשלוח או איסוף"
        }
    ]
    
    for method_data in methods_data:
        existing = session.query(PaymentMethod).filter_by(name=method_data["name"]).first()
        
        if not existing:
            method = PaymentMethod(**method_data)
            session.add(method)
            print(f"  Added payment method: {method_data['name']}")
        else:
            print(f"  Skipped payment method: {method_data['name']} (already exists)")
    
    session.commit()

def main():
    """Main seeding function"""
    print("Starting database seeding for constants...")
    
    try:
        session = create_session()
        
        # Seed all tables
        seed_product_options(session)
        seed_product_sizes(session)
        seed_order_statuses(session)
        seed_delivery_methods(session)
        seed_payment_methods(session)
        
        print("\n✅ Database seeding completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main() 