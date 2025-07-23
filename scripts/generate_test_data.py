#!/usr/bin/env python3
"""
Comprehensive test data generation script for performance testing.

This script will generate:
- 100,000 customers with realistic data
- 50,000 orders with various statuses
- Order items with different products and options
- Realistic order patterns and distributions
"""

import sys
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from faker import Faker
from db.models import (
    Customer, Order, OrderItem, ProductOption, ProductSize, 
    OrderStatus, DeliveryMethod, PaymentMethod, Base
)
from config import get_config

# Initialize Faker with Hebrew locale for realistic Israeli data
fake = Faker(['he_IL', 'en_US'])

# Configuration
CUSTOMER_COUNT = 100000
ORDER_COUNT = 50000
BATCH_SIZE = 1000  # Process in batches for memory efficiency

def create_session():
    """Create database session"""
    config = get_config()
    engine = create_engine(config.database_url)
    Session = sessionmaker(bind=engine)
    return Session()

def generate_customer_data() -> Dict[str, Any]:
    """Generate realistic customer data"""
    # Generate Hebrew and English names
    hebrew_name = fake.name()
    english_name = fake.name()
    
    # Generate Israeli phone number
    phone = fake.phone_number()
    if not phone.startswith('0'):
        phone = '0' + phone[-9:]  # Ensure Israeli format
    
    # Generate Israeli address
    address = fake.address()
    
    return {
        'name': hebrew_name,
        'phone': phone,
        'address': address,
        'language': random.choice(['he', 'en']),
        'created_at': fake.date_time_between(
            start_date='-2 years', 
            end_date='now'
        ),
        'is_active': random.choices([True, False], weights=[0.9, 0.1])[0]
    }

def generate_order_data(customer_id: int, order_date: datetime) -> Dict[str, Any]:
    """Generate realistic order data"""
    # Random order status with realistic distribution
    status_weights = {
        'pending': 0.1,
        'confirmed': 0.2,
        'preparing': 0.3,
        'ready': 0.2,
        'delivered': 0.15,
        'cancelled': 0.05
    }
    
    status = random.choices(list(status_weights.keys()), 
                          weights=list(status_weights.values()))[0]
    
    # Delivery method
    delivery_method = random.choice(['pickup', 'delivery'])
    
    # Payment method
    payment_method = 'cash'  # Only cash for now
    
    # Calculate delivery charge
    delivery_charge = 5.0 if delivery_method == 'delivery' else 0.0
    
    # Generate order items (1-5 items per order)
    item_count = random.choices([1, 2, 3, 4, 5], weights=[0.3, 0.3, 0.2, 0.15, 0.05])[0]
    
    return {
        'customer_id': customer_id,
        'status': status,
        'delivery_method': delivery_method,
        'payment_method': payment_method,
        'delivery_charge': delivery_charge,
        'total_amount': 0.0,  # Will be calculated after items
        'notes': fake.text(max_nb_chars=200) if random.random() < 0.3 else None,
        'created_at': order_date,
        'updated_at': order_date,
        'item_count': item_count
    }

def generate_order_item_data(order_id: int) -> Dict[str, Any]:
    """Generate realistic order item data"""
    # Product types and their options
    products = {
        'kubaneh': {
            'base_price': 25.0,
            'options': ['classic', 'seeded', 'herb', 'aromatic'],
            'sizes': ['small', 'medium', 'large', 'xl']
        },
        'samneh': {
            'base_price': 15.0,
            'options': ['classic', 'spicy', 'herb', 'honey', 'smoked', 'not_smoked'],
            'sizes': ['small', 'medium', 'large']
        },
        'red_bisbas': {
            'base_price': 20.0,
            'options': ['classic', 'spicy', 'mild'],
            'sizes': ['small', 'medium', 'large']
        },
        'hilbeh': {
            'base_price': 18.0,
            'options': ['classic', 'spicy', 'sweet', 'premium'],
            'sizes': ['small', 'medium', 'large']
        },
        'hawaij_soup': {
            'base_price': 22.0,
            'options': ['classic', 'spicy', 'mild'],
            'sizes': ['small', 'medium', 'large']
        },
        'hawaij_coffee': {
            'base_price': 12.0,
            'options': ['classic', 'strong', 'mild'],
            'sizes': ['small', 'medium']
        },
        'white_coffee': {
            'base_price': 10.0,
            'options': ['classic', 'sweet', 'mild'],
            'sizes': ['small', 'medium']
        }
    }
    
    # Select random product
    product_name = random.choice(list(products.keys()))
    product_config = products[product_name]
    
    # Select random options and size
    option = random.choice(product_config['options'])
    size = random.choice(product_config['sizes'])
    
    # Calculate price with modifiers
    base_price = product_config['base_price']
    option_modifier = random.uniform(0, 8)  # Random price modifier
    size_modifier = random.uniform(0, 10)    # Random size modifier
    
    unit_price = base_price + option_modifier + size_modifier
    quantity = random.choices([1, 2, 3, 4, 5], weights=[0.6, 0.25, 0.1, 0.03, 0.02])[0]
    
    return {
        'order_id': order_id,
        'product_name': product_name,
        'product_option': option,
        'product_size': size,
        'quantity': quantity,
        'unit_price': round(unit_price, 2),
        'total_price': round(unit_price * quantity, 2)
    }

def generate_customers_batch(session, batch_size: int) -> List[int]:
    """Generate a batch of customers and return their IDs"""
    print(f"  Generating {batch_size} customers...")
    
    customers = []
    for _ in range(batch_size):
        customer_data = generate_customer_data()
        customer = Customer(**customer_data)
        customers.append(customer)
    
    session.add_all(customers)
    session.commit()
    
    # Return customer IDs for order generation
    customer_ids = [c.id for c in customers]
    print(f"  ✅ Generated {len(customer_ids)} customers")
    return customer_ids

def generate_orders_batch(session, customer_ids: List[int], batch_size: int) -> List[int]:
    """Generate a batch of orders and return their IDs"""
    print(f"  Generating {batch_size} orders...")
    
    orders = []
    order_items = []
    
    for _ in range(batch_size):
        # Select random customer
        customer_id = random.choice(customer_ids)
        
        # Generate order date (last 2 years)
        order_date = fake.date_time_between(
            start_date='-2 years', 
            end_date='now'
        )
        
        order_data = generate_order_data(customer_id, order_date)
        item_count = order_data.pop('item_count')
        
        order = Order(**order_data)
        orders.append(order)
    
    session.add_all(orders)
    session.commit()
    
    # Generate order items for each order
    order_ids = [o.id for o in orders]
    total_amount = 0.0
    
    for order_id in order_ids:
        # Get the order to update total amount
        order = session.query(Order).filter_by(id=order_id).first()
        
        # Generate items for this order
        for _ in range(random.randint(1, 5)):
            item_data = generate_order_item_data(order_id)
            item = OrderItem(**item_data)
            order_items.append(item)
            total_amount += item_data['total_price']
        
        # Update order total
        order.total_amount = round(total_amount + order.delivery_charge, 2)
        total_amount = 0.0
    
    session.add_all(order_items)
    session.commit()
    
    print(f"  ✅ Generated {len(order_ids)} orders with {len(order_items)} items")
    return order_ids

def main():
    """Main data generation function"""
    print("🚀 Starting comprehensive test data generation...")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        session = create_session()
        
        # Check if data already exists
        existing_customers = session.query(Customer).count()
        existing_orders = session.query(Order).count()
        
        if existing_customers > 0 or existing_orders > 0:
            print(f"⚠️  Database already contains {existing_customers} customers and {existing_orders} orders")
            response = input("Do you want to continue and add more data? (y/N): ")
            if response.lower() != 'y':
                print("❌ Data generation cancelled")
                return
        
        print(f"📊 Target: {CUSTOMER_COUNT:,} customers, {ORDER_COUNT:,} orders")
        print(f"⚙️  Batch size: {BATCH_SIZE:,}")
        print()
        
        # Generate customers in batches
        print("👥 Generating customers...")
        all_customer_ids = []
        customer_batches = (CUSTOMER_COUNT + BATCH_SIZE - 1) // BATCH_SIZE
        
        for i in range(customer_batches):
            batch_size = min(BATCH_SIZE, CUSTOMER_COUNT - i * BATCH_SIZE)
            print(f"  Batch {i+1}/{customer_batches}")
            customer_ids = generate_customers_batch(session, batch_size)
            all_customer_ids.extend(customer_ids)
        
        print(f"✅ Total customers generated: {len(all_customer_ids):,}")
        print()
        
        # Generate orders in batches
        print("📦 Generating orders...")
        order_batches = (ORDER_COUNT + BATCH_SIZE - 1) // BATCH_SIZE
        
        for i in range(order_batches):
            batch_size = min(BATCH_SIZE, ORDER_COUNT - i * BATCH_SIZE)
            print(f"  Batch {i+1}/{order_batches}")
            generate_orders_batch(session, all_customer_ids, batch_size)
        
        # Final statistics
        final_customers = session.query(Customer).count()
        final_orders = session.query(Order).count()
        final_items = session.query(OrderItem).count()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print()
        print("=" * 60)
        print("🎉 Data generation completed successfully!")
        print(f"📊 Final statistics:")
        print(f"   👥 Customers: {final_customers:,}")
        print(f"   📦 Orders: {final_orders:,}")
        print(f"   🛍️  Order Items: {final_items:,}")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"🚀 Performance: {final_customers/duration:.0f} customers/second, {final_orders/duration:.0f} orders/second")
        
    except Exception as e:
        print(f"\n❌ Error during data generation: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main() 