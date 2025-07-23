#!/usr/bin/env python3
"""
Script to create database tables for the new constant models.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine
from db.models import Base

# Database URL
DATABASE_URL = "sqlite:///test.db"

def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        print("✅ Database tables created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

if __name__ == "__main__":
    create_tables() 