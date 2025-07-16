#!/usr/bin/env python3
"""
Database migration script to add language column to customers table.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.db.operations import get_db_manager
import logging

logger = logging.getLogger(__name__)

def add_language_column():
    """Add language column to customers table"""
    try:
        db_manager = get_db_manager()
        engine = db_manager.get_engine()
        
        with engine.connect() as connection:
            # Check if language column already exists
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'customers' AND column_name = 'language'
            """))
            
            if result.fetchone():
                logger.info("Language column already exists in customers table")
                return True
            
            # Add language column with default value 'en'
            connection.execute(text("""
                ALTER TABLE customers 
                ADD COLUMN language VARCHAR(10) NOT NULL DEFAULT 'en'
            """))
            
            connection.commit()
            logger.info("Successfully added language column to customers table")
            return True
            
    except Exception as e:
        logger.error("Error adding language column: %s", e)
        return False

if __name__ == "__main__":
    logger.info("Starting language column migration...")
    success = add_language_column()
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
        sys.exit(1) 