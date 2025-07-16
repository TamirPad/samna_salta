#!/usr/bin/env python3
"""
Setup script for fresh Supabase PostgreSQL initialization
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from src.config import get_config
from src.db.models import Base
from src.db.operations import init_default_products

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_supabase():
    """Setup fresh Supabase PostgreSQL database"""
    
    config = get_config()
    
    # Check if Supabase connection string is available
    if not config.supabase_connection_string:
        logger.error("SUPABASE_CONNECTION_STRING not found in environment")
        logger.info("Please add your Supabase connection string to .env file")
        return False
    
    try:
        # Create engine
        logger.info("🔧 Creating Supabase database connection...")
        engine = create_engine(config.supabase_connection_string)
        
        # Test connection
        logger.info("🔌 Testing connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"✅ Connected to PostgreSQL: {version}")
        
        # Create tables
        logger.info("📋 Creating database tables...")
        Base.metadata.create_all(engine)
        logger.info("✅ Tables created successfully")
        
        # Initialize default products
        logger.info("🛍️ Initializing default products...")
        init_default_products()
        logger.info("✅ Default products initialized")
        
        logger.info("🎉 Supabase setup completed successfully!")
        logger.info("Your bot is ready to use Supabase PostgreSQL!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        logger.info("\n🔧 Troubleshooting tips:")
        logger.info("1. Check your connection string format")
        logger.info("2. Verify database credentials")
        logger.info("3. Ensure database is accessible from your IP")
        logger.info("4. Try adding ?sslmode=require to connection string")
        return False


def verify_setup():
    """Verify that Supabase setup was successful"""
    config = get_config()
    
    if not config.supabase_connection_string:
        logger.error("SUPABASE_CONNECTION_STRING not found")
        return False
    
    try:
        engine = create_engine(config.supabase_connection_string)
        
        with engine.connect() as conn:
            # Check if tables exist
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('customers', 'products', 'carts', 'orders', 'order_items')
            """))
            tables = [row[0] for row in result.fetchall()]
            
            logger.info("📊 Setup verification results:")
            logger.info(f"   Tables found: {', '.join(tables)}")
            
            # Check product count
            result = conn.execute(text("SELECT COUNT(*) FROM products"))
            product_count = result.scalar()
            logger.info(f"   Default products: {product_count}")
            
            if len(tables) >= 5 and product_count > 0:
                logger.info("✅ Supabase setup verification successful!")
                return True
            else:
                logger.warning("⚠️ Some tables or products are missing")
                return False
                
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup fresh Supabase PostgreSQL database")
    parser.add_argument("--verify", action="store_true", help="Verify setup instead of running it")
    
    args = parser.parse_args()
    
    if args.verify:
        success = verify_setup()
    else:
        success = setup_supabase()
    
    sys.exit(0 if success else 1) 