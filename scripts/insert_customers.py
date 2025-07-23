#!/usr/bin/env python3
"""
Script to insert 1000 test customers into the Samna Salta database.

This script generates realistic customer data and inserts it into the database
using the existing database operations.
"""

import sys
import os
import logging
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from faker import Faker
from src.db.models import Customer
from src.db.operations import get_db_manager
from src.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Faker with both English and Hebrew locales for realistic data
fake_en = Faker('en_US')
fake_he = Faker('he_IL')

def generate_phone_number():
    """Generate a realistic Israeli phone number"""
    # Israeli mobile numbers start with 05 followed by 8 digits
    return f"+972{fake_en.random_int(min=50, max=59)}{fake_en.random_int(min=1000000, max=9999999)}"

def generate_customer_data(telegram_id: int) -> dict:
    """Generate realistic customer data"""
    # Randomly choose language (70% Hebrew, 30% English)
    import random
    language = random.choices(['he', 'en'], weights=[70, 30])[0]
    
    if language == 'he':
        # Use Hebrew names for Hebrew language customers
        first_name = fake_he.first_name()
        last_name = fake_he.last_name()
        name = f"{first_name} {last_name}"
        # Hebrew addresses
        delivery_address = f"{fake_he.street_address()}, {fake_he.city()}"
    else:
        # Use English names for English language customers
        name = fake_en.name()
        # English addresses but still in Israel
        delivery_address = f"{fake_en.street_address()}, {fake_en.city()}"
    
    phone = generate_phone_number()
    
    # 5% chance of being admin (50 out of 1000)
    is_admin = random.choices([True, False], weights=[5, 95])[0]
    
    return {
        'telegram_id': telegram_id,
        'name': name,
        'phone': phone,
        'language': language,
        'delivery_address': delivery_address,
        'is_admin': is_admin
    }

def insert_customers(num_customers: int = 1000):
    """Insert the specified number of customers into the database"""
    logger.info(f"Starting to insert {num_customers} customers...")
    
    try:
        # Get database manager
        db_manager = get_db_manager()
        
        # Generate unique telegram IDs starting from a high number to avoid conflicts
        start_telegram_id = 9000000000  # Start from 9 billion to avoid real telegram IDs
        
        customers_data = []
        for i in range(num_customers):
            telegram_id = start_telegram_id + i
            customer_data = generate_customer_data(telegram_id)
            customers_data.append(customer_data)
        
        logger.info(f"Generated data for {len(customers_data)} customers")
        
        # Insert customers in batches for better performance
        batch_size = 100
        total_inserted = 0
        
        with db_manager.get_session_context() as session:
            for i in range(0, len(customers_data), batch_size):
                batch = customers_data[i:i + batch_size]
                
                # Create Customer objects
                customers = []
                for data in batch:
                    customer = Customer(
                        telegram_id=data['telegram_id'],
                        name=data['name'],
                        phone=data['phone'],
                        language=data['language'],
                        delivery_address=data['delivery_address'],
                        is_admin=data['is_admin']
                    )
                    customers.append(customer)
                
                # Add batch to session
                session.add_all(customers)
                session.flush()  # Flush to get IDs without committing
                
                total_inserted += len(customers)
                logger.info(f"Inserted batch {i//batch_size + 1}: {total_inserted}/{num_customers} customers")
            
            # Commit all changes
            session.commit()
            logger.info(f"Successfully inserted all {total_inserted} customers!")
            
    except Exception as e:
        logger.error(f"Error inserting customers: {e}")
        raise

def main():
    """Main function"""
    try:
        # Validate configuration
        config = get_config()
        logger.info(f"Using database: {config.database_url[:50]}...")
        
        # Insert customers
        insert_customers(1000)
        
        logger.info("Script completed successfully!")
        
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 