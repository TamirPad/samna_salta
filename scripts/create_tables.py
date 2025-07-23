#!/usr/bin/env python3
"""
Simple script to create database tables for the Samna Salta bot.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine
from db.models import Base
from config import get_config

def create_tables():
    """Create all database tables"""
    print("🗄️ Creating database tables...")
    
    try:
        config = get_config()
        engine = create_engine(config.database_url)
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        print("✅ Database tables created successfully!")
        print(f"📊 Database URL: {config.database_url}")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

if __name__ == "__main__":
    create_tables() 